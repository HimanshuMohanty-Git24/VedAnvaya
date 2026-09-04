"""Deterministic knowledge build: pinned Anukramaṇī artifacts → resolved edges.

The build is offline and reproducible. Every output record names the source assertion,
pinned artifact and snapshot it came from, and every unresolved label is reported rather
than guessed at. No language model, embedding or classifier is involved.

Predicate whitelist: ``HAS_RISHI``, ``HAS_DEVATA``, ``HAS_CHANDAS``. Nothing else.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID

from vedagraph.identity import uuid_for_urn
from vedagraph.ingest.adapters.anukramani import PARSER_VERSION, WSC2023AnukramaniAdapter
from vedagraph.knowledge.normalize import (
    NORMALIZATION_POLICY_VERSION,
    ascii_key,
    normalize_label,
)
from vedagraph.knowledge.registry import (
    RESOLUTION_POLICY_VERSION,
    EntityResolver,
    load_resolvers,
)
from vedagraph.models import AnukramaniStagingRecord, Passage, QAIssue
from vedagraph.models.enums import (
    AnukramaniField,
    AnukramaniParseStatus,
    EntityType,
    KnowledgeEntityType,
    MetadataPredicate,
    ProvenanceClass,
    QASeverity,
    QAStatus,
    ResolutionStatus,
    ScopeOrigin,
    ScopeType,
)
from vedagraph.models.knowledge import (
    FIELD_PREDICATE,
    PREDICATE_ENTITY_TYPE,
    KnowledgeAssertion,
    KnowledgeEntity,
    MetadataSourceAssertion,
    UnresolvedLabel,
)
from vedagraph.storage.jsonl import read_jsonl

QA_POLICY_VERSION = "rigveda-deterministic-knowledge-qa-v1"
KNOWLEDGE_LAYER_VERSION = "vedagraph-rigveda-knowledge-deterministic-1.0.0-rc1"
PREDICATE_WHITELIST: tuple[MetadataPredicate, ...] = (
    MetadataPredicate.HAS_RISHI,
    MetadataPredicate.HAS_DEVATA,
    MetadataPredicate.HAS_CHANDAS,
)

SCOPE_TYPES: dict[ScopeOrigin, ScopeType] = {
    ScopeOrigin.SUKTA_WIDE: ScopeType.WHOLE_PASSAGE,
    ScopeOrigin.SINGLE_MANTRA: ScopeType.SINGLE_MANTRA,
    ScopeOrigin.MANTRA_RANGE: ScopeType.MANTRA_RANGE,
}


@dataclass(frozen=True)
class CorpusIndex:
    """The mantra and sūkta identities of the corpus this layer enriches."""

    mantra_ids: dict[tuple[int, int, int], UUID]
    mantra_keys: dict[tuple[int, int, int], str]
    sukta_keys: dict[tuple[int, int], str]
    sukta_ids: dict[tuple[int, int], UUID]
    mantra_counts: dict[tuple[int, int], int]
    citations: dict[tuple[int, int, int], str]

    @property
    def total_mantras(self) -> int:
        return len(self.mantra_ids)

    @property
    def total_suktas(self) -> int:
        return len(self.sukta_keys)


@dataclass
class AlignmentReport:
    dataset_rows: int = 0
    aligned_rows: int = 0
    unaligned_rows: list[str] = field(default_factory=list)
    duplicate_rows: list[str] = field(default_factory=list)
    verse_count_mismatches: list[str] = field(default_factory=list)
    missing_corpus_suktas: list[str] = field(default_factory=list)


@dataclass
class _UnresolvedAccumulator:
    """Running tally for one unregistered label."""

    status: ResolutionStatus
    reason: str
    candidates: list[str]
    raw_labels: set[str] = field(default_factory=set)
    occurrences: int = 0
    mantras: int = 0
    examples: list[str] = field(default_factory=list)


@dataclass
class KnowledgeBuildResult:
    staging: list[AnukramaniStagingRecord]
    source_assertions: list[MetadataSourceAssertion]
    assertions: list[KnowledgeAssertion]
    entities: dict[KnowledgeEntityType, list[KnowledgeEntity]]
    unresolved: list[UnresolvedLabel]
    qa_issues: list[QAIssue]
    alignment: AlignmentReport
    corpus: CorpusIndex

    @property
    def qa_status(self) -> QAStatus:
        severities = {issue.severity for issue in self.qa_issues}
        if QASeverity.ERROR in severities:
            return QAStatus.FAILED
        if QASeverity.WARNING in severities:
            return QAStatus.PASSED_WITH_WARNINGS
        return QAStatus.PASSED


def load_corpus_index(corpus_dir: Path) -> CorpusIndex:
    mantra_ids: dict[tuple[int, int, int], UUID] = {}
    mantra_keys: dict[tuple[int, int, int], str] = {}
    sukta_keys: dict[tuple[int, int], str] = {}
    sukta_ids: dict[tuple[int, int], UUID] = {}
    counts: dict[tuple[int, int], int] = defaultdict(int)
    citations: dict[tuple[int, int, int], str] = {}
    for passage in read_jsonl(corpus_dir / "passages.jsonl", Passage):
        hierarchy = passage.hierarchy
        if passage.entity_type is EntityType.HYMN:
            address = (int(hierarchy["mandala"]), int(hierarchy["sukta"]))
            sukta_keys[address] = passage.canonical_key
            sukta_ids[address] = passage.entity_id
        elif passage.entity_type is EntityType.MANTRA:
            mantra = (
                int(hierarchy["mandala"]),
                int(hierarchy["sukta"]),
                int(hierarchy["mantra"]),
            )
            mantra_ids[mantra] = passage.entity_id
            mantra_keys[mantra] = passage.canonical_key
            citations[mantra] = passage.canonical_citation
            counts[mantra[:2]] += 1
    return CorpusIndex(mantra_ids, mantra_keys, sukta_keys, sukta_ids, dict(counts), citations)


def parse_artifacts(artifacts: list[dict[str, object]]) -> list[AnukramaniStagingRecord]:
    adapter = WSC2023AnukramaniAdapter()
    records: list[AnukramaniStagingRecord] = []
    for artifact in sorted(artifacts, key=lambda item: int(str(item["mandala"]))):
        records.extend(
            adapter.parse_anukramani(
                Path(str(artifact["snapshot_path"])),
                snapshot_id=str(artifact["snapshot_id"]),
                source_artifact_id=str(artifact["artifact_id"]),
                mandala=int(str(artifact["mandala"])),
            )
        )
    return records


def _issue(check: str, severity: QASeverity, message: str, entity: str | None = None) -> QAIssue:
    urn = f"urn:vedagraph:qa:knowledge:{check}:{entity or ''}:{message}"
    return QAIssue(
        issue_id=uuid_for_urn(urn),
        check_id=check,
        severity=severity,
        message=message,
        entity_id=entity,
    )


def build_knowledge(
    *,
    corpus_dir: Path,
    artifacts: list[dict[str, object]],
    registry_root: Path = Path("data/registry"),
) -> KnowledgeBuildResult:
    corpus = load_corpus_index(corpus_dir)
    resolvers = load_resolvers(registry_root)
    staging = parse_artifacts(artifacts)
    qa_issues: list[QAIssue] = []
    alignment = AlignmentReport(dataset_rows=len(staging))

    source_assertions = _stage_source_assertions(staging, corpus, alignment, qa_issues)
    assertions, unresolved, entity_labels, entity_counts = _resolve(
        source_assertions, corpus, resolvers, qa_issues
    )
    entities = {
        entity_type: resolver.build_entities(entity_labels[entity_type], entity_counts[entity_type])
        for entity_type, resolver in resolvers.items()
    }
    qa_issues.extend(_coverage_issues(assertions, corpus))
    qa_issues.extend(_reference_issues(assertions, corpus, entities))
    qa_issues.sort(key=lambda issue: (issue.check_id, issue.entity_id or "", issue.message))
    return KnowledgeBuildResult(
        staging=staging,
        source_assertions=source_assertions,
        assertions=assertions,
        entities=entities,
        unresolved=unresolved,
        qa_issues=qa_issues,
        alignment=alignment,
        corpus=corpus,
    )


def _stage_source_assertions(
    staging: list[AnukramaniStagingRecord],
    corpus: CorpusIndex,
    alignment: AlignmentReport,
    qa_issues: list[QAIssue],
) -> list[MetadataSourceAssertion]:
    assertions: list[MetadataSourceAssertion] = []
    seen: dict[tuple[int, int], str] = {}
    for record in staging:
        address = (record.mandala, record.sukta)
        citation = f"RV {record.mandala}.{record.sukta}"
        if record.parse_status is AnukramaniParseStatus.INVALID:
            alignment.unaligned_rows.append(record.source_locator)
            qa_issues.append(
                _issue(
                    "anukramani_row_invalid",
                    QASeverity.ERROR,
                    f"{record.source_locator}: {'; '.join(record.parse_notes)}",
                    citation,
                )
            )
            continue
        sukta_key = corpus.sukta_keys.get(address)
        if sukta_key is None:
            alignment.unaligned_rows.append(record.source_locator)
            alignment.missing_corpus_suktas.append(citation)
            qa_issues.append(
                _issue(
                    "anukramani_row_unaligned",
                    QASeverity.ERROR,
                    f"{record.source_locator} names {citation}, which is not in the corpus",
                    citation,
                )
            )
            continue
        if address in seen:
            alignment.duplicate_rows.append(record.source_locator)
            qa_issues.append(
                _issue(
                    "anukramani_duplicate_row",
                    QASeverity.ERROR,
                    f"{record.source_locator} repeats {citation}, already at {seen[address]}",
                    citation,
                )
            )
            continue
        seen[address] = record.source_locator
        corpus_count = corpus.mantra_counts.get(address, 0)
        if record.declared_verse_count != corpus_count:
            alignment.verse_count_mismatches.append(citation)
            qa_issues.append(
                _issue(
                    "anukramani_verse_count_mismatch",
                    QASeverity.ERROR,
                    f"{citation}: source declares {record.declared_verse_count} verses, "
                    f"corpus has {corpus_count}",
                    citation,
                )
            )
            continue
        alignment.aligned_rows += 1
        if record.parse_status is AnukramaniParseStatus.PARTIALLY_PARSED:
            qa_issues.append(
                _issue(
                    "anukramani_row_partially_parsed",
                    QASeverity.WARNING,
                    f"{record.source_locator}: {'; '.join(record.parse_notes)}",
                    citation,
                )
            )
        for ordinal, segment in enumerate(record.segments, start=1):
            predicate = FIELD_PREDICATE[AnukramaniField(segment.field)]
            urn = f"urn:vedagraph:assertion:wsc2023:{record.source_locator}:{ordinal}"
            assertions.append(
                MetadataSourceAssertion(
                    assertion_id=uuid_for_urn(urn),
                    subject_key=sukta_key,
                    scope_type=SCOPE_TYPES[segment.scope_origin],
                    scope_origin=segment.scope_origin,
                    start_mantra=segment.start_mantra,
                    end_mantra=segment.end_mantra,
                    predicate=predicate,
                    raw_value=segment.raw_value,
                    normalized_value=normalize_label(segment.raw_value),
                    raw_segment=segment.raw_segment,
                    raw_line=record.raw_line,
                    source_id=record.source_id,
                    source_artifact_id=record.source_artifact_id,
                    snapshot_id=record.snapshot_id,
                    source_locator=record.source_locator,
                    citation=citation,
                    parser_version=record.parser_version,
                )
            )
    assertions.sort(key=lambda item: (item.source_locator, str(item.assertion_id)))
    return assertions


def _resolve(
    source_assertions: list[MetadataSourceAssertion],
    corpus: CorpusIndex,
    resolvers: dict[KnowledgeEntityType, EntityResolver],
    qa_issues: list[QAIssue],
) -> tuple[
    list[KnowledgeAssertion],
    list[UnresolvedLabel],
    dict[KnowledgeEntityType, dict[str, list[str]]],
    dict[KnowledgeEntityType, dict[str, int]],
]:
    assertions: list[KnowledgeAssertion] = []
    entity_labels: dict[KnowledgeEntityType, dict[str, list[str]]] = {
        entity_type: defaultdict(list) for entity_type in KnowledgeEntityType
    }
    entity_counts: dict[KnowledgeEntityType, dict[str, int]] = {
        entity_type: defaultdict(int) for entity_type in KnowledgeEntityType
    }
    unresolved: dict[tuple[KnowledgeEntityType, str], _UnresolvedAccumulator] = {}

    for assertion in source_assertions:
        entity_type = PREDICATE_ENTITY_TYPE[assertion.predicate]
        resolution = resolvers[entity_type].resolve(assertion.raw_value)
        mandala, sukta = _address(assertion.subject_key)
        if assertion.scope_origin is ScopeOrigin.SUKTA_WIDE:
            mantras = list(range(1, corpus.mantra_counts[(mandala, sukta)] + 1))
        else:
            mantras = list(range(assertion.start_mantra or 1, (assertion.end_mantra or 0) + 1))
        if resolution.entity_key is None:
            record = unresolved.setdefault(
                (entity_type, resolution.normalized_label),
                _UnresolvedAccumulator(
                    status=resolution.status,
                    reason=resolution.reason,
                    candidates=resolvers[entity_type].candidates(resolution.normalized_label),
                ),
            )
            record.raw_labels.add(assertion.raw_value)
            record.occurrences += 1
            record.mantras += len(mantras)
            if len(record.examples) < 5:
                record.examples.append(assertion.citation)
            continue
        entity_labels[entity_type][resolution.entity_key].append(assertion.raw_value)
        provenance = (
            ProvenanceClass.SOURCE_EXPLICIT
            if assertion.scope_origin is not ScopeOrigin.SUKTA_WIDE
            else ProvenanceClass.SOURCE_DERIVED_SCOPE
        )
        for mantra in mantras:
            address = (mandala, sukta, mantra)
            subject_id = corpus.mantra_ids.get(address)
            if subject_id is None:
                qa_issues.append(
                    _issue(
                        "knowledge_broken_passage_reference",
                        QASeverity.ERROR,
                        f"{assertion.citation}.{mantra} is not a corpus mantra",
                        assertion.citation,
                    )
                )
                continue
            slug = resolution.entity_key.split(":")[-1]
            object_urn = f"urn:vedagraph:entity:{entity_type.value.lower()}:{slug.lower()}"
            urn = (
                f"urn:vedagraph:knowledge:{assertion.predicate.value}:"
                f"{corpus.mantra_keys[address]}:{resolution.entity_key}:{assertion.assertion_id}"
            )
            entity_counts[entity_type][resolution.entity_key] += 1
            assertions.append(
                KnowledgeAssertion(
                    assertion_id=uuid_for_urn(urn),
                    subject_key=corpus.mantra_keys[address],
                    subject_id=subject_id,
                    predicate=assertion.predicate,
                    object_key=resolution.entity_key,
                    object_id=uuid_for_urn(object_urn),
                    source_label=assertion.raw_value,
                    source_assertion_id=assertion.assertion_id,
                    provenance_class=provenance,
                    scope_origin=assertion.scope_origin,
                    resolution_method=resolution.status,
                    source_id=assertion.source_id,
                    source_artifact_id=assertion.source_artifact_id,
                    citation=corpus.citations[address],
                )
            )

    reports: list[UnresolvedLabel] = []
    for (entity_type, label), record in sorted(unresolved.items()):
        predicate = next(
            key for key, value in PREDICATE_ENTITY_TYPE.items() if value is entity_type
        )
        reports.append(
            UnresolvedLabel(
                normalized_label=label,
                raw_labels=sorted(record.raw_labels),
                entity_type=entity_type,
                predicate=predicate,
                resolution_status=record.status,
                reason=record.reason,
                ascii_key=ascii_key(label),
                occurrence_count=record.occurrences,
                mantra_count=record.mantras,
                example_subject_keys=list(record.examples),
                candidate_entity_keys=list(record.candidates),
            )
        )
        qa_issues.append(
            _issue(
                "knowledge_unresolved_label",
                QASeverity.WARNING,
                f"{entity_type.value} label {label!r} is not registered "
                f"({record.occurrences} occurrences)",
                label,
            )
        )
    assertions.sort(
        key=lambda item: (item.subject_key, item.predicate, item.object_key, str(item.assertion_id))
    )
    return assertions, reports, entity_labels, entity_counts


def _address(sukta_key: str) -> tuple[int, int]:
    _, _, _, mandala, sukta = sukta_key.split(":")
    return int(mandala[1:]), int(sukta[1:])


def _coverage_issues(assertions: list[KnowledgeAssertion], corpus: CorpusIndex) -> list[QAIssue]:
    covered: dict[MetadataPredicate, set[str]] = {
        predicate: set() for predicate in PREDICATE_WHITELIST
    }
    for assertion in assertions:
        covered[assertion.predicate].add(assertion.subject_key)
    issues: list[QAIssue] = []
    for predicate in PREDICATE_WHITELIST:
        missing = len(corpus.mantra_ids) - len(covered[predicate])
        if missing:
            issues.append(
                _issue(
                    "knowledge_predicate_coverage_incomplete",
                    QASeverity.WARNING,
                    f"{missing} of {len(corpus.mantra_ids)} mantras carry no resolved "
                    f"{predicate.value} assertion",
                    predicate.value,
                )
            )
    return issues


def _reference_issues(
    assertions: list[KnowledgeAssertion],
    corpus: CorpusIndex,
    entities: dict[KnowledgeEntityType, list[KnowledgeEntity]],
) -> list[QAIssue]:
    known_entities = {
        entity.entity_key: entity.entity_id for records in entities.values() for entity in records
    }
    known_passages = set(corpus.mantra_keys.values())
    issues: list[QAIssue] = []
    for assertion in assertions:
        if assertion.subject_key not in known_passages:
            issues.append(
                _issue(
                    "knowledge_broken_passage_reference",
                    QASeverity.ERROR,
                    f"{assertion.subject_key} is not a corpus mantra",
                    assertion.subject_key,
                )
            )
        expected = known_entities.get(assertion.object_key)
        if expected is None:
            issues.append(
                _issue(
                    "knowledge_broken_entity_reference",
                    QASeverity.ERROR,
                    f"{assertion.object_key} is not a registered entity",
                    assertion.object_key,
                )
            )
        elif expected != assertion.object_id:
            issues.append(
                _issue(
                    "knowledge_entity_id_mismatch",
                    QASeverity.ERROR,
                    f"{assertion.object_key} has an inconsistent entity id",
                    assertion.object_key,
                )
            )
    return issues


def load_artifact_index(path: Path) -> list[dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"{path} must contain a list of pinned artifacts")
    return [dict(item) for item in payload]


POLICY_VERSIONS = {
    "normalization_policy_version": NORMALIZATION_POLICY_VERSION,
    "resolution_policy_version": RESOLUTION_POLICY_VERSION,
    "parser_version": PARSER_VERSION,
    "qa_policy_version": QA_POLICY_VERSION,
}
