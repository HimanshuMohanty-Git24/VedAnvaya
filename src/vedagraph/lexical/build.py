"""Orchestrate the deterministic lexical and cross-mantra build.

Inputs, all pinned and all offline:

* the canonical corpus (passages, and the ``GRETIL.RV.AUFRECHT`` primary Sanskrit),
* the finished traditional knowledge layer (canonical entities and ``HAS_*`` edges),
* the pinned VedaWeb book TEI artifacts carrying the Zurich morphology,
* the reviewed lexical alias and Devatā component registries.

The canonical Sanskrit is read, never written. The morphology is an annotation layer
referencing mantras; it does not become the text. No language model, embedding,
classifier or network call is involved at any point.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID

from vedagraph.identity import uuid_for_urn
from vedagraph.lexical.aliases import (
    LexicalMatcher,
    load_lexical_aliases,
    propose_alias_candidates,
)
from vedagraph.lexical.analytics import build_lexical_stats
from vedagraph.lexical.components import load_component_assertions
from vedagraph.lexical.mentions import build_mentions
from vedagraph.lexical.morphology import (
    MorphologyArtifact,
    MorphologyParseReport,
    parse_morphology,
)
from vedagraph.lexical.parallels import MantraText, ParallelRunReport, build_parallels
from vedagraph.models import Passage, QAIssue, TextVersion
from vedagraph.models.enums import EntityType, KnowledgeEntityType, QASeverity, QAStatus
from vedagraph.models.knowledge import KnowledgeAssertion, KnowledgeEntity
from vedagraph.models.lexical import (
    AmbiguousMention,
    ComponentAssertion,
    EntityCoOccurrence,
    ExactParallelGroup,
    LemmaRecord,
    LexicalAlias,
    LexicalAliasCandidate,
    LexicalStats,
    MantraParallel,
    MentionAssertion,
    MorphologyToken,
    ParallelCandidate,
)
from vedagraph.storage.jsonl import read_jsonl

LEXICAL_LAYER_VERSION = "vedagraph-rigveda-knowledge-deterministic-lexical-1.0.0-rc1"
LEXICAL_QA_POLICY_VERSION = "rigveda-deterministic-lexical-qa-v1"
TOKEN_ID_POLICY_VERSION = "vedaweb-zurich-token-identity-v1"
CANONICAL_TEXT_VERSION_ID = "GRETIL.RV.AUFRECHT"


def _issue(check: str, severity: QASeverity, message: str) -> QAIssue:
    """QA issues are identified by their content, so two runs produce the same ids."""
    urn = f"urn:vedagraph:qa:lexical:{check}:{message}"
    return QAIssue(issue_id=uuid_for_urn(urn), check_id=check, severity=severity, message=message)


ENTITY_FILES = {
    KnowledgeEntityType.DEVATA: "entities_devatas.jsonl",
    KnowledgeEntityType.RISHI: "entities_rishis.jsonl",
    KnowledgeEntityType.CHANDAS: "entities_chandas.jsonl",
}


@dataclass
class AlignmentReport:
    """How the annotation layer lined up with the canonical corpus."""

    mantras_expected: int = 0
    mantras_with_morphology: int = 0
    unaligned_records: list[str] = field(default_factory=list)
    duplicate_token_keys: list[str] = field(default_factory=list)
    passage_mismatches: list[str] = field(default_factory=list)
    tokens: int = 0


@dataclass
class LexicalBuildResult:
    tokens: list[MorphologyToken]
    lemmas: list[LemmaRecord]
    aliases: list[LexicalAlias]
    alias_candidates: list[LexicalAliasCandidate]
    mentions: list[MentionAssertion]
    ambiguous: list[AmbiguousMention]
    components: list[ComponentAssertion]
    parallels: list[MantraParallel]
    parallel_candidates: list[ParallelCandidate]
    exact_groups: list[ExactParallelGroup]
    co_occurrences: list[EntityCoOccurrence]
    stats: LexicalStats
    qa_issues: list[QAIssue]
    qa_status: QAStatus
    alignment: AlignmentReport
    parse_report: MorphologyParseReport
    parallel_report: ParallelRunReport
    timings: dict[str, float]
    entities: dict[str, KnowledgeEntity]


@dataclass(frozen=True)
class CorpusView:
    """The parts of the canonical corpus this layer reads. Nothing is written back."""

    passage_ids: dict[str, UUID]
    citations: dict[str, str]
    primary_text: dict[str, str]

    @property
    def total_mantras(self) -> int:
        return len(self.passage_ids)


def load_corpus_view(corpus_dir: Path) -> CorpusView:
    passage_ids: dict[str, UUID] = {}
    citations: dict[str, str] = {}
    for passage in read_jsonl(corpus_dir / "passages.jsonl", Passage):
        if passage.entity_type is not EntityType.MANTRA:
            continue
        passage_ids[passage.canonical_key] = passage.entity_id
        citations[passage.canonical_key] = passage.canonical_citation
    by_id = {value: key for key, value in passage_ids.items()}
    primary: dict[str, str] = {}
    for version in read_jsonl(corpus_dir / "text_versions.jsonl", TextVersion):
        if version.text_version_id != CANONICAL_TEXT_VERSION_ID:
            continue
        key = by_id.get(version.passage_id)
        if key is not None:
            primary[key] = version.text_original
    return CorpusView(passage_ids=passage_ids, citations=citations, primary_text=primary)


def load_entities(knowledge_dir: Path) -> dict[str, KnowledgeEntity]:
    entities: dict[str, KnowledgeEntity] = {}
    for filename in ENTITY_FILES.values():
        for entity in read_jsonl(knowledge_dir / filename, KnowledgeEntity):
            entities[entity.entity_key] = entity
    return entities


def load_knowledge_assertions(knowledge_dir: Path) -> list[KnowledgeAssertion]:
    return list(read_jsonl(knowledge_dir / "knowledge_assertions.jsonl", KnowledgeAssertion))


def build_lexical_layer(
    *,
    corpus_dir: Path,
    knowledge_dir: Path,
    artifacts: list[MorphologyArtifact],
    registry_root: Path = Path("data/registry"),
) -> LexicalBuildResult:
    timings: dict[str, float] = {}
    corpus = load_corpus_view(corpus_dir)
    entities = load_entities(knowledge_dir)
    knowledge_assertions = load_knowledge_assertions(knowledge_dir)

    started = time.perf_counter()
    parse_report = MorphologyParseReport()
    tokens: list[MorphologyToken] = []
    for artifact in artifacts:
        tokens.extend(parse_morphology(artifact, report=parse_report))
    timings["morphology_parse"] = time.perf_counter() - started

    started = time.perf_counter()
    alignment, qa_issues = _align(tokens, corpus)
    lemmas = _lemma_inventory(tokens)
    timings["token_build"] = time.perf_counter() - started

    started = time.perf_counter()
    aliases = load_lexical_aliases(registry_root, entities=entities)
    matcher = LexicalMatcher(aliases)
    mentions, ambiguous = build_mentions(
        tokens,
        matcher,
        entities,
        citations=corpus.citations,
        passage_ids=corpus.passage_ids,
    )
    alias_candidates = propose_alias_candidates(tokens, entities, existing=aliases)
    timings["mention_extraction"] = time.perf_counter() - started

    started = time.perf_counter()
    components = load_component_assertions(registry_root, entities=entities)
    timings["components"] = time.perf_counter() - started

    started = time.perf_counter()
    texts = _mantra_texts(corpus, tokens)
    parallel_report = ParallelRunReport()
    parallels, parallel_candidates, exact_groups = build_parallels(texts, report=parallel_report)
    timings["parallels"] = time.perf_counter() - started

    started = time.perf_counter()
    stats, co_occurrences = build_lexical_stats(
        tokens=tokens,
        entities=entities,
        aliases=aliases,
        alias_candidates=alias_candidates,
        mentions=mentions,
        ambiguous_count=len(ambiguous),
        knowledge_assertions=knowledge_assertions,
        parallels=parallels,
        parallel_candidates=parallel_candidates,
        exact_groups=exact_groups,
        component_count=len(components),
        total_mantras=corpus.total_mantras,
    )
    timings["analytics"] = time.perf_counter() - started

    qa_issues.extend(_qa(tokens, mentions, parse_report, aliases))
    qa_status = (
        QAStatus.FAILED
        if any(issue.severity is QASeverity.ERROR for issue in qa_issues)
        else QAStatus.PASSED_WITH_WARNINGS
        if qa_issues
        else QAStatus.PASSED
    )
    timings["total"] = sum(value for key, value in timings.items() if key != "total")

    return LexicalBuildResult(
        tokens=tokens,
        lemmas=lemmas,
        aliases=aliases,
        alias_candidates=alias_candidates,
        mentions=mentions,
        ambiguous=ambiguous,
        components=components,
        parallels=parallels,
        parallel_candidates=parallel_candidates,
        exact_groups=exact_groups,
        co_occurrences=co_occurrences,
        stats=stats,
        qa_issues=sorted(qa_issues, key=lambda issue: (issue.check_id, issue.message)),
        qa_status=qa_status,
        alignment=alignment,
        parse_report=parse_report,
        parallel_report=parallel_report,
        timings=timings,
        entities=entities,
    )


def _align(
    tokens: list[MorphologyToken], corpus: CorpusView
) -> tuple[AlignmentReport, list[QAIssue]]:
    """Check every token reaches a real mantra. Alignment is by citation, never by text."""
    report = AlignmentReport(mantras_expected=corpus.total_mantras, tokens=len(tokens))
    issues: list[QAIssue] = []
    seen: set[str] = set()
    covered: set[str] = set()
    for token in tokens:
        if token.token_key in seen:
            report.duplicate_token_keys.append(token.token_key)
        seen.add(token.token_key)
        expected = corpus.passage_ids.get(token.passage_key)
        if expected is None:
            report.unaligned_records.append(token.source_locator)
            continue
        if expected != token.passage_id:
            report.passage_mismatches.append(token.token_key)
        covered.add(token.passage_key)
    report.mantras_with_morphology = len(covered)

    if report.unaligned_records:
        issues.append(
            _issue(
                "LEXICAL_TOKEN_UNALIGNED",
                QASeverity.ERROR,
                f"{len(report.unaligned_records)} annotated tokens cite a mantra that is "
                "not in the canonical corpus",
            )
        )
    if report.duplicate_token_keys:
        issues.append(
            _issue(
                "LEXICAL_TOKEN_DUPLICATE_ID",
                QASeverity.ERROR,
                f"{len(report.duplicate_token_keys)} duplicate token keys",
            )
        )
    if report.passage_mismatches:
        issues.append(
            _issue(
                "LEXICAL_TOKEN_PASSAGE_MISMATCH",
                QASeverity.ERROR,
                f"{len(report.passage_mismatches)} tokens disagree with the passage uuid",
            )
        )
    missing = corpus.total_mantras - report.mantras_with_morphology
    if missing:
        issues.append(
            _issue(
                "LEXICAL_MORPHOLOGY_COVERAGE",
                QASeverity.WARNING,
                f"{missing} canonical mantras carry no morphological annotation",
            )
        )
    return report, issues


@dataclass
class _LemmaAccumulator:
    normalized: str
    lemma_ids: set[str] = field(default_factory=set)
    parts_of_speech: set[str] = field(default_factory=set)
    token_count: int = 0
    mantras: set[str] = field(default_factory=set)


def _lemma_inventory(tokens: list[MorphologyToken]) -> list[LemmaRecord]:
    """The distinct lemmas the annotation layer actually uses, with where they occur."""
    grouped: dict[str, _LemmaAccumulator] = {}
    for token in tokens:
        entry = grouped.setdefault(token.lemma, _LemmaAccumulator(token.normalized_lemma))
        entry.token_count += 1
        entry.lemma_ids.update(token.lemma_ids)
        if token.part_of_speech:
            entry.parts_of_speech.add(token.part_of_speech)
        entry.mantras.add(token.passage_key)
    return sorted(
        (
            LemmaRecord(
                lemma=lemma,
                normalized_lemma=entry.normalized,
                lemma_ids=sorted(entry.lemma_ids),
                parts_of_speech=sorted(entry.parts_of_speech),
                token_count=entry.token_count,
                mantra_count=len(entry.mantras),
                example_passage_keys=sorted(entry.mantras)[:3],
            )
            for lemma, entry in grouped.items()
        ),
        key=lambda record: record.lemma,
    )


def _mantra_texts(corpus: CorpusView, tokens: list[MorphologyToken]) -> list[MantraText]:
    by_passage: dict[str, list[MorphologyToken]] = defaultdict(list)
    for token in tokens:
        by_passage[token.passage_key].append(token)
    texts: list[MantraText] = []
    for passage_key, passage_id in sorted(corpus.passage_ids.items()):
        annotated = sorted(by_passage.get(passage_key, []), key=lambda item: item.sequence)
        texts.append(
            MantraText(
                passage_key=passage_key,
                passage_id=passage_id,
                citation=corpus.citations[passage_key],
                mandala=int(passage_key.split(":")[3][1:]),
                source_text=corpus.primary_text.get(passage_key, ""),
                tokens=tuple(token.normalized_surface for token in annotated),
                lemmas=tuple(token.normalized_lemma for token in annotated),
            )
        )
    return texts


def _qa(
    tokens: list[MorphologyToken],
    mentions: list[MentionAssertion],
    parse_report: MorphologyParseReport,
    aliases: list[LexicalAlias],
) -> list[QAIssue]:
    issues: list[QAIssue] = []
    if parse_report.tokens_without_lemma:
        issues.append(
            _issue(
                "LEXICAL_TOKEN_NO_LEMMA",
                QASeverity.WARNING,
                f"{len(parse_report.tokens_without_lemma)} annotated tokens carry no lemma "
                "and were reported rather than given one",
            )
        )
    if parse_report.unparsable_token_ids:
        issues.append(
            _issue(
                "LEXICAL_TOKEN_UNPARSABLE_ID",
                QASeverity.WARNING,
                f"{len(parse_report.unparsable_token_ids)} annotation ids did not parse",
            )
        )

    by_passage: dict[str, set[int]] = defaultdict(set)
    for token in tokens:
        by_passage[token.passage_key].add(token.sequence)
    broken = [
        key
        for key, sequences in by_passage.items()
        if sorted(sequences) != list(range(1, len(sequences) + 1))
    ]
    if broken:
        issues.append(
            _issue(
                "LEXICAL_TOKEN_SEQUENCE_GAP",
                QASeverity.ERROR,
                f"{len(broken)} mantras have non-contiguous token sequences",
            )
        )

    token_keys = {token.token_key for token in tokens}
    orphaned = [
        item.token_key
        for mention in mentions
        for item in mention.evidence
        if item.token_key not in token_keys
    ]
    if orphaned:
        issues.append(
            _issue(
                "LEXICAL_MENTION_ORPHAN_EVIDENCE",
                QASeverity.ERROR,
                f"{len(orphaned)} mention evidence tokens do not exist",
            )
        )

    pending = sum(1 for alias in aliases if not alias.may_produce_mention)
    if pending:
        issues.append(
            _issue(
                "LEXICAL_ALIAS_UNREVIEWED",
                QASeverity.INFO,
                f"{pending} registered lexical aliases are not ACCEPTED and deliberately "
                "produce no mentions",
            )
        )
    return issues
