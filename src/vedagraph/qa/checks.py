"""Cross-record corpus QA checks."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid5

from vedagraph.identity import VEDAGRAPH_NAMESPACE_UUID
from vedagraph.models import (
    AudioRecording,
    AudioSegment,
    Citation,
    Passage,
    QAIssue,
    Source,
    SourceAssertion,
    SuktaDiscoveryRecord,
    TextVersion,
    TraditionalMetadataAssertion,
    Translation,
)
from vedagraph.models.enums import EntityType, QASeverity, ScopeType


@dataclass(frozen=True)
class CorpusRecords:
    passages: list[Passage]
    texts: list[TextVersion]
    translations: list[Translation]
    metadata: list[TraditionalMetadataAssertion]
    sources: list[Source]
    citations: list[Citation]
    audio_recordings: list[AudioRecording]
    audio_segments: list[AudioSegment]
    source_assertions: list[SourceAssertion]
    discoveries: list[SuktaDiscoveryRecord] = field(default_factory=list)


def _issue(
    check_id: str,
    severity: QASeverity,
    message: str,
    entity_id: str | None = None,
    **details: Any,
) -> QAIssue:
    stable = f"{check_id}|{entity_id or ''}|{message}"
    return QAIssue(
        issue_id=uuid5(VEDAGRAPH_NAMESPACE_UUID, stable),
        check_id=check_id,
        severity=severity,
        message=message,
        entity_id=entity_id,
        details=details,
    )


RANGE_MARKER = re.compile(r"[०-९0-9]")  # noqa: RUF001


def _duplicates(values: list[str]) -> set[str]:
    return {value for value, count in Counter(values).items() if count > 1}


def validate_corpus(records: CorpusRecords) -> list[QAIssue]:
    issues: list[QAIssue] = []
    passage_ids = {passage.entity_id for passage in records.passages}
    passage_by_id = {passage.entity_id: passage for passage in records.passages}
    passage_by_key = {passage.canonical_key: passage for passage in records.passages}
    passage_keys = {passage.canonical_key for passage in records.passages}
    source_ids = {source.source_id for source in records.sources}
    audio_ids = {audio.audio_id for audio in records.audio_recordings}

    for key in _duplicates([passage.canonical_key for passage in records.passages]):
        issues.append(
            _issue("unique_canonical_keys", QASeverity.ERROR, f"duplicate key: {key}", key)
        )
    for identifier in _duplicates([str(passage.entity_id) for passage in records.passages]):
        issues.append(
            _issue(
                "unique_uuids",
                QASeverity.ERROR,
                f"duplicate passage UUID: {identifier}",
                identifier,
            )
        )
    for duplicate_citation in _duplicates(
        [passage.canonical_citation for passage in records.passages]
    ):
        issues.append(
            _issue(
                "unique_canonical_citations",
                QASeverity.ERROR,
                f"duplicate canonical citation: {duplicate_citation}",
                duplicate_citation,
            )
        )
    for passage in records.passages:
        if passage.parent_key and passage.parent_key not in passage_keys:
            issues.append(
                _issue(
                    "valid_parents",
                    QASeverity.ERROR,
                    f"missing parent: {passage.parent_key}",
                    str(passage.entity_id),
                )
            )
        if any(isinstance(value, int) and value < 1 for value in passage.hierarchy.values()):
            issues.append(
                _issue(
                    "valid_hierarchy",
                    QASeverity.ERROR,
                    "non-positive hierarchy value",
                    str(passage.entity_id),
                )
            )
        parent = passage_by_key.get(passage.parent_key) if passage.parent_key else None
        if parent is not None and parent.work_id != passage.work_id:
            issues.append(
                _issue(
                    "valid_parents",
                    QASeverity.ERROR,
                    "parent belongs to a different work",
                    str(passage.entity_id),
                )
            )
        if passage.entity_type == EntityType.MANTRA and (
            parent is None or parent.entity_type != EntityType.HYMN
        ):
            issues.append(
                _issue(
                    "valid_parents",
                    QASeverity.ERROR,
                    "mantra must be attached to a Sukta/HYMN parent",
                    str(passage.entity_id),
                )
            )
        if passage.entity_type == EntityType.HYMN and (
            parent is None or parent.entity_type != EntityType.SECTION
        ):
            issues.append(
                _issue(
                    "valid_parents",
                    QASeverity.ERROR,
                    "Sukta/HYMN must be attached to a Mandala/SECTION parent",
                    str(passage.entity_id),
                )
            )

    children: dict[str, list[Passage]] = {}
    for passage in records.passages:
        if passage.parent_key:
            children.setdefault(passage.parent_key, []).append(passage)
    for parent_key, child_records in children.items():
        for sequence in _duplicates([str(child.sequence_in_parent) for child in child_records]):
            issues.append(
                _issue(
                    "unique_sequences_in_parent",
                    QASeverity.ERROR,
                    f"duplicate sequence {sequence} under {parent_key}",
                    parent_key,
                )
            )
        sequences = sorted(child.sequence_in_parent for child in child_records)
        expected = set(range(sequences[0], sequences[-1] + 1))
        missing = sorted(expected - set(sequences))
        partial_discovery_sample = bool(records.discoveries) and all(
            child.entity_type == EntityType.HYMN for child in child_records
        )
        if missing and not partial_discovery_sample:
            issues.append(
                _issue(
                    "sequence_gaps",
                    QASeverity.WARNING,
                    f"sequence gaps under {parent_key}; textual numbering may be legitimate",
                    parent_key,
                    missing=missing,
                )
            )

    discoveries_by_source: dict[tuple[int, str], set[int]] = {}
    for discovery in records.discoveries:
        discoveries_by_source.setdefault(
            (discovery.mandala_number, discovery.source_id), set()
        ).add(discovery.sukta_number)
    for (mandala, source_id), numbers in discoveries_by_source.items():
        missing = sorted(set(range(min(numbers), max(numbers) + 1)) - numbers)
        if missing:
            issues.append(
                _issue(
                    "discovery_sequence_gaps",
                    QASeverity.WARNING,
                    f"{source_id} discovery has Sukta gaps in Mandala {mandala}",
                    f"RV.{mandala}",
                    missing=missing,
                )
            )
    for mandala in sorted({item.mandala_number for item in records.discoveries}):
        discovered = {
            item.sukta_number for item in records.discoveries if item.mandala_number == mandala
        }
        ingested = {
            int(item.hierarchy["sukta"])
            for item in records.passages
            if item.entity_type == EntityType.HYMN and item.hierarchy.get("mandala") == mandala
        }
        if discovered != ingested:
            issues.append(
                _issue(
                    "discovery_ingestion_coverage",
                    QASeverity.INFO,
                    f"Mandala {mandala} is partially ingested",
                    f"RV.{mandala}",
                    discovered=len(discovered),
                    ingested=len(ingested),
                    not_ingested=sorted(discovered - ingested),
                    not_discovered=sorted(ingested - discovered),
                )
            )

    # Expected-vs-canonical mantra count (task: stop and investigate on mismatch, never
    # force the canonical count to match a source total). Only Suktas GRETIL discovered
    # *and* this build actually ingested are checked, so a deliberate partial-sample build
    # never triggers this; a full-Mandala build effectively checks the whole 2,006 total.
    gretil_known_mantras = {
        (item.mandala_number, item.sukta_number): item.known_mantra_count
        for item in records.discoveries
        if item.source_id == "GRETIL" and item.known_mantra_count is not None
    }
    ingested_mantra_counts: dict[tuple[int, int], int] = {}
    for passage in records.passages:
        if passage.entity_type != EntityType.MANTRA:
            continue
        mantra_sukta_key = (int(passage.hierarchy["mandala"]), int(passage.hierarchy["sukta"]))
        ingested_mantra_counts[mantra_sukta_key] = (
            ingested_mantra_counts.get(mantra_sukta_key, 0) + 1
        )
    for (mandala, sukta), expected_count in sorted(gretil_known_mantras.items()):
        actual_count = ingested_mantra_counts.get((mandala, sukta))
        if actual_count is not None and actual_count != expected_count:
            issues.append(
                _issue(
                    "expected_vs_canonical_mantra_count",
                    QASeverity.ERROR,
                    f"RV {mandala}.{sukta}: GRETIL discovery reports {expected_count} mantras "
                    f"but {actual_count} were canonically ingested",
                    f"RV.{mandala}.{sukta}",
                    expected=expected_count,
                    actual=actual_count,
                )
            )

    metadata_predicates = {"HAS_RISHI", "HAS_DEVATA", "HAS_CHANDAS"}
    canonical_metadata = {
        (str(item.scope.passage_id), str(item.predicate), item.value) for item in records.metadata
    }
    metadata_passage_by_key = {item.canonical_key: item for item in records.passages}
    for source_assertion in records.source_assertions:
        if source_assertion.predicate not in metadata_predicates:
            continue
        if not RANGE_MARKER.search(str(source_assertion.value)):
            continue
        scoped = metadata_passage_by_key.get(source_assertion.subject_id)
        if scoped is None:
            continue
        claim = (str(scoped.entity_id), source_assertion.predicate, source_assertion.value)
        if claim in canonical_metadata:
            continue
        issues.append(
            _issue(
                "deferred_metadata_range",
                QASeverity.WARNING,
                f"{source_assertion.predicate} for {source_assertion.subject_id} is a "
                "per-mantra range kept as a source assertion only; "
                "no canonical scope was claimed",
                source_assertion.subject_id,
                predicate=source_assertion.predicate,
                source_id=source_assertion.source_id,
                value=str(source_assertion.value),
            )
        )

    sanskrit_targets: set[object] = set()
    for text in records.texts:
        if text.passage_id not in passage_ids:
            issues.append(
                _issue(
                    "broken_references",
                    QASeverity.ERROR,
                    "text target is missing",
                    str(text.text_id),
                )
            )
        if text.source_id not in source_ids:
            issues.append(
                _issue(
                    "valid_referenced_sources",
                    QASeverity.ERROR,
                    "text source is missing",
                    str(text.text_id),
                )
            )
        if text.language == "sa":
            sanskrit_targets.add(text.passage_id)
            if not text.text_nfc.strip():
                issues.append(
                    _issue(
                        "non_empty_sanskrit",
                        QASeverity.ERROR,
                        "empty Sanskrit text",
                        str(text.text_id),
                    )
                )
        try:
            text.text_original.encode("utf-8", errors="strict")
        except UnicodeError:
            issues.append(
                _issue("valid_unicode", QASeverity.ERROR, "invalid Unicode", str(text.text_id))
            )

    for passage in records.passages:
        if passage.entity_type == EntityType.MANTRA and passage.entity_id not in sanskrit_targets:
            issues.append(
                _issue(
                    "non_empty_sanskrit",
                    QASeverity.ERROR,
                    "canonical mantra has no Sanskrit text",
                    str(passage.entity_id),
                )
            )

    for translation in records.translations:
        if translation.passage_id not in passage_ids:
            issues.append(
                _issue(
                    "valid_translation_targets",
                    QASeverity.ERROR,
                    "translation target is missing",
                    str(translation.translation_id),
                )
            )
        if translation.source_id not in source_ids:
            issues.append(
                _issue(
                    "source_provenance_present",
                    QASeverity.ERROR,
                    "translation source is missing",
                    str(translation.translation_id),
                )
            )
    # Two translations from the *same* source landing on the same passage is not two
    # intended readings; it is almost always a stanza-numbering artifact (e.g. a legacy
    # page's verse regex assigning one sequence number twice), and it can silently mask
    # a different mantra in the same Sukta having no translation at all.
    translation_source_pairs = [
        f"{translation.passage_id}|{translation.source_id}" for translation in records.translations
    ]
    for pair in _duplicates(translation_source_pairs):
        passage_id, source_id = pair.split("|", 1)
        issues.append(
            _issue(
                "duplicate_translation_for_passage",
                QASeverity.WARNING,
                f"{source_id} supplies more than one translation for the same passage",
                passage_id,
            )
        )

    for assertion in records.metadata:
        if assertion.scope.passage_id not in passage_ids:
            issues.append(
                _issue(
                    "valid_metadata_scope",
                    QASeverity.ERROR,
                    "metadata scope target is missing",
                    str(assertion.assertion_id),
                )
            )
        if assertion.source_id not in source_ids:
            issues.append(
                _issue(
                    "source_provenance_present",
                    QASeverity.ERROR,
                    "metadata source is missing",
                    str(assertion.assertion_id),
                )
            )
        target = passage_by_id.get(assertion.scope.passage_id)
        if (
            target is not None
            and assertion.scope.scope_type == ScopeType.SINGLE_MANTRA
            and target.entity_type != EntityType.MANTRA
        ):
            issues.append(
                _issue(
                    "valid_metadata_scope",
                    QASeverity.ERROR,
                    "SINGLE_MANTRA scope must target a mantra",
                    str(assertion.assertion_id),
                )
            )
        if target is not None and assertion.scope.scope_type == ScopeType.MANTRA_RANGE:
            child_sequences = [
                passage.sequence_in_parent
                for passage in records.passages
                if passage.parent_key == target.canonical_key
                and passage.entity_type == EntityType.MANTRA
            ]
            if (
                not child_sequences
                or assertion.scope.end_sequence is None
                or assertion.scope.end_sequence > max(child_sequences)
            ):
                issues.append(
                    _issue(
                        "valid_metadata_scope",
                        QASeverity.ERROR,
                        "MANTRA_RANGE exceeds the target passage's mantra children",
                        str(assertion.assertion_id),
                    )
                )

    for audio in records.audio_recordings:
        if audio.target_id not in passage_ids:
            issues.append(
                _issue(
                    "valid_audio_targets",
                    QASeverity.ERROR,
                    "audio target is missing",
                    str(audio.audio_id),
                )
            )
        if audio.source_id not in source_ids:
            issues.append(
                _issue(
                    "source_provenance_present",
                    QASeverity.ERROR,
                    "audio source is missing",
                    str(audio.audio_id),
                )
            )
    for segment in records.audio_segments:
        if segment.audio_id not in audio_ids or segment.passage_id not in passage_ids:
            issues.append(
                _issue(
                    "broken_references",
                    QASeverity.ERROR,
                    "audio segment reference is missing",
                    str(segment.segment_id),
                )
            )

    citation_pairs = [f"{citation.system}|{citation.label}" for citation in records.citations]
    for pair in _duplicates(citation_pairs):
        issues.append(
            _issue("duplicate_citations", QASeverity.ERROR, f"duplicate citation: {pair}", pair)
        )
    for citation in records.citations:
        if citation.passage_id not in passage_ids:
            issues.append(
                _issue(
                    "broken_references",
                    QASeverity.ERROR,
                    "citation target is missing",
                    str(citation.citation_id),
                )
            )
    for source_assertion in records.source_assertions:
        if source_assertion.source_id not in source_ids:
            issues.append(
                _issue(
                    "source_provenance_present",
                    QASeverity.ERROR,
                    "source assertion source is missing",
                    str(source_assertion.assertion_id),
                )
            )
    return sorted(issues, key=lambda issue: (issue.severity, issue.check_id, str(issue.issue_id)))
