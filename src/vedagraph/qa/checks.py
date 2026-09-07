"""Cross-record corpus QA checks."""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse
from uuid import uuid5

import orjson

from vedagraph.config.registry import (
    load_source_artifacts,
    load_text_versions,
    load_works,
)
from vedagraph.identity import VEDAGRAPH_NAMESPACE_UUID, uuid_for_urn
from vedagraph.models import (
    AudioRecording,
    AudioSegment,
    Citation,
    Passage,
    QAIssue,
    Source,
    SourceArtifact,
    SourceAssertion,
    SuktaDiscoveryRecord,
    TextVersion,
    TextVersionDescriptor,
    TraditionalMetadataAssertion,
    Translation,
    Work,
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


def declared_levels(works: list[Work]) -> dict[str, list[str]]:
    """Map each declared work to its lower-cased hierarchy level names, in order.

    The registry is the single declaration of how deep a work is. Deriving the legal
    structural shape from it is what makes these checks work-agnostic: Rigveda declares
    three levels, Vajasaneyi Samhita two, and Samaveda more, and none of that is
    hardcoded here.
    """
    return {work.work_id: [level.lower() for level in work.hierarchy] for work in works}


def _check_structural_position(
    passage: Passage,
    parent: Passage | None,
    levels: list[str],
    issues: list[QAIssue],
) -> None:
    """Validate one passage's depth and parent link against its work's declared levels.

    This replaces a hardcoded MANTRA->HYMN->SECTION chain, which was a Rigveda
    assumption: a two-level work has no hymn level at all, so every one of its mantras
    was previously reported as wrongly parented.

    A level whose value is ``0`` is treated as *declared absent* rather than missing, so
    a work whose middle levels do not exist in some divisions still presents a complete
    key set. ``valid_hierarchy`` reports that as INFO; it is never silent.
    """
    entity = str(passage.entity_id)
    keys = set(passage.hierarchy)
    depth = len(keys)
    if depth == 0 or depth > len(levels) or keys != set(levels[:depth]):
        issues.append(
            _issue(
                "declared_work_hierarchy",
                QASeverity.ERROR,
                f"hierarchy keys {sorted(keys)} are not the first {depth} declared "
                f"level(s) of {passage.work_id}",
                entity,
                declared=levels,
                present=sorted(keys),
            )
        )
        return
    is_leaf = depth == len(levels)
    if is_leaf and passage.entity_type != EntityType.MANTRA:
        issues.append(
            _issue(
                "declared_work_hierarchy",
                QASeverity.ERROR,
                f"leaf level {levels[-1]!r} must carry entity type MANTRA, "
                f"not {passage.entity_type}",
                entity,
            )
        )
    if not is_leaf and passage.entity_type == EntityType.MANTRA:
        issues.append(
            _issue(
                "declared_work_hierarchy",
                QASeverity.ERROR,
                f"MANTRA at hierarchy depth {depth} but {passage.work_id} declares "
                f"{len(levels)} levels",
                entity,
            )
        )
    if depth == 1:
        if passage.parent_key is not None:
            issues.append(
                _issue(
                    "valid_parents",
                    QASeverity.ERROR,
                    "a top-level passage must not declare a parent",
                    entity,
                )
            )
        return
    if parent is None:
        issues.append(
            _issue(
                "valid_parents",
                QASeverity.ERROR,
                f"a depth-{depth} passage requires a parent at depth {depth - 1}",
                entity,
            )
        )
        return
    # A parent normally sits exactly one level up. It may sit further up when every level
    # in between is declared absent (value 0) for this division: the Samaveda Aranya and
    # Mahanamnya arcikas have no prapathaka, ardha or dasati, so their verses hang directly
    # off the arcika and there is no intervening container to point at. Requiring depth-1
    # unconditionally reported 11 of the 102 verses in the Samaveda pilot as broken when
    # they were correct, so the skipped run is checked instead of the depth alone.
    parent_depth = len(parent.hierarchy)
    skipped = levels[parent_depth : depth - 1]
    if parent_depth >= depth or (
        skipped and not all(passage.hierarchy.get(level) == 0 for level in skipped)
    ):
        issues.append(
            _issue(
                "valid_parents",
                QASeverity.ERROR,
                f"parent sits at hierarchy depth {parent_depth}; a depth-{depth} passage in "
                f"{passage.work_id} requires a depth-{depth - 1} parent, or a parent higher up "
                f"with only declared-absent levels in between",
                entity,
                skipped_levels=skipped,
                skipped_values=[str(passage.hierarchy.get(level)) for level in skipped],
            )
        )
        return
    shared = {level: passage.hierarchy[level] for level in levels[:parent_depth]}
    if dict(parent.hierarchy) != shared:
        issues.append(
            _issue(
                "valid_parents",
                QASeverity.ERROR,
                "parent hierarchy is not this passage's hierarchy prefix",
                entity,
                parent_hierarchy={key: str(value) for key, value in parent.hierarchy.items()},
                expected={key: str(value) for key, value in shared.items()},
            )
        )


def validate_corpus(records: CorpusRecords, *, works: list[Work] | None = None) -> list[QAIssue]:
    issues: list[QAIssue] = []
    declared = declared_levels(works if works is not None else load_works())
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
        negative = sorted(
            level
            for level, value in passage.hierarchy.items()
            if isinstance(value, int) and value < 0
        )
        if negative:
            issues.append(
                _issue(
                    "valid_hierarchy",
                    QASeverity.ERROR,
                    f"negative hierarchy value at level(s) {negative}",
                    str(passage.entity_id),
                    levels=negative,
                )
            )
        # A zero states that this division has no such level (e.g. a Samaveda arcika with
        # no prapathaka). That is a real reading of the source, so it is surfaced rather
        # than rejected -- and surfaced rather than silently accepted.
        absent = sorted(
            level
            for level, value in passage.hierarchy.items()
            if isinstance(value, int) and value == 0
        )
        if absent:
            issues.append(
                _issue(
                    "valid_hierarchy",
                    QASeverity.INFO,
                    f"hierarchy level(s) {absent} are declared absent (value 0) by the source",
                    str(passage.entity_id),
                    levels=absent,
                )
            )
        recomputed = str(uuid_for_urn(passage.canonical_urn))
        if recomputed != str(passage.entity_id):
            issues.append(
                _issue(
                    "stable_uuid_deterministic",
                    QASeverity.ERROR,
                    "stored entity_id is not uuid5(VedaGraph namespace, canonical_urn)",
                    str(passage.entity_id),
                    canonical_urn=passage.canonical_urn,
                    recomputed=recomputed,
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
        levels = declared.get(passage.work_id)
        if levels is None:
            issues.append(
                _issue(
                    "declared_work_hierarchy",
                    QASeverity.WARNING,
                    f"work {passage.work_id} is not declared in the work registry; "
                    "depth and parent-chain checks were skipped for this passage",
                    str(passage.entity_id),
                )
            )
        else:
            _check_structural_position(passage, parent, levels, issues)

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
            if item.entity_type == EntityType.HYMN
            and item.hierarchy.get("mandala") == mandala
            and "sukta" in item.hierarchy
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
        # Reconciliation against GRETIL Sukta discovery is Rigveda-shaped by construction
        # (SuktaDiscoveryRecord carries mandala_number/sukta_number). Without this guard the
        # unguarded hierarchy["mandala"] lookup below raised KeyError on every non-Rigveda
        # mantra, so validate_corpus crashed instead of reporting for YV/SV/AV.
        if not {"mandala", "sukta"} <= set(passage.hierarchy):
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


CONTENT_ADDRESSED_NAME = re.compile(r"^[a-f0-9]{64}$")


def _content_addressed_index(raw_root: Path) -> dict[str, Path]:
    """Map sha256 -> path for every raw snapshot that is named after its own content."""
    if not raw_root.exists():
        return {}
    return {
        path.stem: path
        for path in raw_root.rglob("*")
        if path.is_file() and CONTENT_ADDRESSED_NAME.match(path.stem)
    }


def verify_registry_checksums(
    release_artifacts: list[SourceArtifact],
    registry_artifacts: list[SourceArtifact] | None = None,
    raw_root: Path | None = None,
) -> list[QAIssue]:
    """Cross-check a release's artifact checksums against the source registry.

    The registry is the authority on what an artifact IS and what rights attach to it; a
    release is the authority on which bytes it actually read. Where both state a checksum
    they must agree, and every artifact a release claims must be one the registry knows.

    Without this, a registry edit that repointed an artifact at different bytes would
    produce a release whose provenance is a fiction while every structural gate still
    passed: the identity checks, the parent checks and the Unicode checks are all blind to
    whether the text came from the file the rights statement describes. Suggested by
    Agent D after adding the equivalent check inside the Atharvaveda build.

    Three legs, and none of them subsumes another. Agent E made the distinction that
    matters: verifying that bytes match their OWN recorded digest passes happily on a
    snapshot that is internally consistent but which the registry points at wrongly. So
    this checks the registry's CLAIM about the bytes, and — when ``raw_root`` is given and
    the snapshot is content-addressed — that those exact bytes are still on disk and
    intact. A snapshot that is simply not retained locally is reported as unverifiable
    rather than as a failure, because not retaining it is a legitimate choice.
    """
    issues: list[QAIssue] = []
    on_disk = _content_addressed_index(raw_root) if raw_root is not None else {}
    registry = {
        artifact.artifact_id: artifact
        for artifact in (
            registry_artifacts if registry_artifacts is not None else load_source_artifacts()
        )
    }
    for artifact in release_artifacts:
        declared = registry.get(artifact.artifact_id)
        if declared is None:
            issues.append(
                _issue(
                    "registry_artifact_declared",
                    QASeverity.ERROR,
                    f"release claims artifact {artifact.artifact_id}, which the source "
                    "registry does not declare; its rights and provenance are unverifiable",
                    artifact.artifact_id,
                    source_id=artifact.source_id,
                )
            )
            continue
        if artifact.checksum_sha256 and declared.checksum_sha256:
            if artifact.checksum_sha256 != declared.checksum_sha256:
                issues.append(
                    _issue(
                        "registry_checksum_agreement",
                        QASeverity.ERROR,
                        f"{artifact.artifact_id}: the release read bytes whose sha256 is not "
                        "the one the registry pins for this artifact",
                        artifact.artifact_id,
                        release_checksum=artifact.checksum_sha256,
                        registry_checksum=declared.checksum_sha256,
                    )
                )
            elif raw_root is not None:
                path = on_disk.get(artifact.checksum_sha256)
                if path is None:
                    issues.append(
                        _issue(
                            "registry_checksum_bytes_present",
                            QASeverity.INFO,
                            f"{artifact.artifact_id}: the pinned bytes are not retained as a "
                            "content-addressed snapshot locally, so agreement is asserted "
                            "but not re-verified from bytes",
                            artifact.artifact_id,
                            checksum=artifact.checksum_sha256,
                        )
                    )
                else:
                    actual = hashlib.sha256(path.read_bytes()).hexdigest()
                    if actual != artifact.checksum_sha256:
                        issues.append(
                            _issue(
                                "registry_checksum_bytes_present",
                                QASeverity.ERROR,
                                f"{artifact.artifact_id}: the retained snapshot at "
                                f"{path.as_posix()} does not hash to the pinned checksum",
                                artifact.artifact_id,
                                pinned=artifact.checksum_sha256,
                                actual=actual,
                            )
                        )
        elif not artifact.checksum_sha256 and not declared.checksum_sha256:
            # Reported, not waived: an artifact with no checksum anywhere cannot be
            # verified to be the file its rights statement describes.
            issues.append(
                _issue(
                    "registry_checksum_agreement",
                    QASeverity.WARNING,
                    f"{artifact.artifact_id} declares no checksum in either the release or "
                    "the registry, so the bytes it names cannot be verified",
                    artifact.artifact_id,
                )
            )
        else:
            # Exactly one side states a checksum. There are no such artifacts today, but
            # leaving this branch implicit would let a future one-sided checksum pass
            # silently, which is the failure mode this whole check exists to prevent.
            stated, silent = (
                ("release", "registry") if artifact.checksum_sha256 else ("registry", "release")
            )
            issues.append(
                _issue(
                    "registry_checksum_agreement",
                    QASeverity.WARNING,
                    f"{artifact.artifact_id}: only the {stated} states a checksum; the "
                    f"{silent} states none, so the two cannot be reconciled",
                    artifact.artifact_id,
                )
            )
    return issues


def verify_content_addressed_snapshots(root: Path) -> list[QAIssue]:
    """Verify that every content-addressed raw snapshot still hashes to its own filename.

    Independent of any registry: where a fetcher names a file after the sha256 of its
    content, the name is a self-describing claim and silent corruption or a truncated
    re-fetch breaks it. Files not named after a hash are skipped, not guessed about.
    """
    issues: list[QAIssue] = []
    if not root.exists():
        return issues
    for path in sorted(root.rglob("*")):
        if not path.is_file() or not CONTENT_ADDRESSED_NAME.match(path.stem):
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != path.stem:
            issues.append(
                _issue(
                    "content_addressed_snapshot_intact",
                    QASeverity.ERROR,
                    f"{path.as_posix()} no longer hashes to the filename that names it",
                    path.name,
                    expected=path.stem,
                    actual=actual,
                )
            )
    return issues


SNAPSHOT_NAMESPACE_PREDICATE = "SNAPSHOT_NAMESPACE_RESOLVES_TO_SOURCE"


def verify_snapshot_namespaces(
    source_assertions: list[SourceAssertion],
    sources: list[Source],
    raw_root: Path | None = None,
) -> list[QAIssue]:
    """Resolve a raw-storage namespace to a registered source, exactly rather than loosely.

    ``ingest/fetcher/http.py`` derives three different things from one argument — the raw
    directory, the ``snapshot_id`` prefix and the ``source_id`` written into the metadata
    sidecar — so a build that wants a per-Veda raw directory cannot get one without also
    changing the recorded provenance and the manifest's snapshot ids. Agent D hit this and
    kept ``data/raw/gretil_avs/`` with ``snapshot_id`` prefix ``GRETIL_AVS`` while the
    records correctly say ``GRETIL``.

    Rather than assert bare equality (which fails on a legitimate namespace) or tolerate a
    suffix (which would also accept a typo), this resolves the join through the build's own
    machine-readable ``SNAPSHOT_NAMESPACE_RESOLVES_TO_SOURCE`` assertions and then requires
    the resolved target to be a source the release actually declares. An undeclared
    namespace is an error; a declared one that resolves to an unknown source is an error.
    """
    issues: list[QAIssue] = []
    known_sources = {source.source_id for source in sources}
    for assertion in source_assertions:
        if assertion.predicate != SNAPSHOT_NAMESPACE_PREDICATE:
            continue
        value = assertion.value if isinstance(assertion.value, dict) else {}
        target = value.get("registered_source_id")
        if not target:
            issues.append(
                _issue(
                    "snapshot_namespace_resolves",
                    QASeverity.ERROR,
                    f"namespace {assertion.subject_id} declares no registered_source_id",
                    assertion.subject_id,
                )
            )
            continue
        if target not in known_sources:
            issues.append(
                _issue(
                    "snapshot_namespace_resolves",
                    QASeverity.ERROR,
                    f"namespace {assertion.subject_id} resolves to source {target}, which "
                    "this release does not declare",
                    assertion.subject_id,
                    resolved_to=str(target),
                )
            )
            continue
        directory = value.get("raw_directory")
        if raw_root is not None and directory:
            path = Path(str(directory))
            if not path.exists():
                issues.append(
                    _issue(
                        "snapshot_namespace_resolves",
                        QASeverity.WARNING,
                        f"namespace {assertion.subject_id} names raw directory "
                        f"{directory}, which does not exist",
                        assertion.subject_id,
                    )
                )
    return issues


SNAPSHOT_ID = re.compile(r"^(?P<namespace>[A-Z][A-Z0-9_]*):(?P<digest>[a-f0-9]{64})$")


def verify_manifest_snapshots(
    manifest: dict[str, Any],
    raw_root: Path,
    namespace_to_source: dict[str, str] | None = None,
) -> list[QAIssue]:
    """Reconcile a manifest's recorded snapshots against the raw tree, both directions.

    Suggested and scoped by Agent D after hitting the failure it detects: a build whose
    ``source_snapshot_ids`` listed only 2 of the 25 snapshots it had actually read. Every
    gate passed, including Agent D's own, because nothing compared the manifest against the
    tree. 23 of 25 snapshots -- 92 percent -- were invisible to a manifest-level audit.

    Two directions, because only one of them is obvious:

    * forward -- every snapshot the manifest names must exist on disk and, where the id
      carries a digest, hash to it. A manifest naming bytes that are not there is a
      provenance claim that cannot be checked.
    * reverse -- for each namespace the manifest uses, the raw directory may contain MORE
      content-addressed snapshots than the manifest lists. This is the direction that catches
      under-reporting, and it is a WARNING and not an ERROR for a reason Agent C proved
      rather than assumed: ``data/raw/wikisource_sa/`` holds 47 snapshots of which 3 are
      Agent B's Samaveda fetches, because Samaveda and Yajurveda share the source id
      ``WIKISOURCE_SA``. A raw directory is genuinely shared, so **no single manifest can ever
      reach parity with it** and this leg cannot distinguish under-reporting from another
      build's traffic on its own.

      What it can do is show its working, so it reports the retrieval URL of every unlisted
      snapshot where a sidecar exists. That is what makes attribution possible without
      guessing -- a Samaveda page URL under a Yajurveda build is visibly cross-traffic, not a
      missing record.
    """
    issues: list[QAIssue] = []
    listed = manifest.get("source_snapshot_ids") or []
    on_disk = _content_addressed_index(raw_root)
    per_namespace: dict[str, set[str]] = {}

    for snapshot_id in listed:
        match = SNAPSHOT_ID.match(str(snapshot_id))
        if match is None:
            issues.append(
                _issue(
                    "manifest_snapshots_reconcile",
                    QASeverity.WARNING,
                    f"snapshot id {snapshot_id!r} is not <NAMESPACE>:<sha256>, so it cannot "
                    "be reconciled against the raw tree",
                    str(snapshot_id),
                )
            )
            continue
        namespace, digest = match.group("namespace"), match.group("digest")
        per_namespace.setdefault(namespace, set()).add(digest)
        if digest not in on_disk:
            issues.append(
                _issue(
                    "manifest_snapshots_reconcile",
                    QASeverity.ERROR,
                    f"manifest names snapshot {snapshot_id} but no content-addressed file "
                    f"with that digest exists under {raw_root.as_posix()}",
                    str(snapshot_id),
                )
            )

    # Recorded hashes must agree with the bytes, where the manifest states them.
    for key, value in (manifest.get("raw_snapshot_hashes") or {}).items():
        digest = str(value)
        if not CONTENT_ADDRESSED_NAME.match(digest):
            continue
        path = on_disk.get(digest)
        if path is None:
            issues.append(
                _issue(
                    "manifest_snapshots_reconcile",
                    QASeverity.ERROR,
                    f"manifest records hash {digest} for {key} but no file with that digest "
                    "is retained",
                    str(key),
                )
            )
        elif hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            issues.append(
                _issue(
                    "manifest_snapshots_reconcile",
                    QASeverity.ERROR,
                    f"{path.as_posix()} does not hash to the value the manifest records for {key}",
                    str(key),
                )
            )

    # Reverse direction: the under-reporting case.
    for namespace, digests in sorted(per_namespace.items()):
        directory = raw_root / namespace.lower()
        if not directory.exists():
            continue
        present = {
            path.stem
            for path in directory.rglob("*")
            if path.is_file() and CONTENT_ADDRESSED_NAME.match(path.stem)
        }
        missed = sorted(present - digests)
        if missed:
            # Show the retrieval URL of each unlisted snapshot so a reader can attribute it
            # to a build rather than assume it is missing. A shared raw directory makes
            # parity unreachable, so evidence beats a bare count here.
            attributed: list[str] = []
            for digest in missed:
                path = on_disk.get(digest)
                sidecar = path.parent / f"{path.stem}.metadata.json" if path is not None else None
                if sidecar is not None and sidecar.exists():
                    url = str(orjson.loads(sidecar.read_bytes()).get("retrieval_url") or "")
                    attributed.append(f"{digest[:12]} {url[:120]}")
                else:
                    attributed.append(f"{digest[:12]} (no sidecar)")
            issues.append(
                _issue(
                    "manifest_snapshots_reconcile",
                    QASeverity.WARNING,
                    f"{directory.as_posix()} holds {len(present)} content-addressed "
                    f"snapshots but the manifest lists {len(digests)} for namespace "
                    f"{namespace}; {len(missed)} are unlisted. A raw directory is shared "
                    "storage, so this is not necessarily under-reporting -- see the "
                    "retrieval URLs to attribute each one",
                    namespace,
                    unlisted_count=len(missed),
                    unlisted=attributed[:10],
                )
            )
    return issues


def verify_text_version_registration(
    texts: list[TextVersion],
    descriptors: list[TextVersionDescriptor] | None = None,
) -> list[QAIssue]:
    """Every ``text_version_id`` a release uses must be declared in the version registry.

    One level below the artifact check, and rights-bearing for the same reason:
    ``TextVersionDescriptor``'s own docstring states that rights, lineage and permitted
    VedaGraph role attach to the version descriptor, not to the host repository or the
    enclosing file. So a release naming an undeclared ``text_version_id`` is asserting a
    reading whose rights nobody adjudicated -- the same defect as an undeclared artifact id,
    one layer down.

    Found by Agent C, and it is the fourth appearance of one shared assumption:
    ``data/registry/text_versions.yaml`` declares 7 descriptors and all 7 are Rigvedic, so
    every version id in all three new-Veda pilots is unregistered.

    A record with ``text_version_id`` unset is skipped rather than guessed about: not every
    text is a distinguishable *version*, and inventing an id here would be the same mistake
    in the opposite direction.
    """
    issues: list[QAIssue] = []
    declared = {
        descriptor.text_version_id
        for descriptor in (descriptors if descriptors is not None else load_text_versions())
    }
    seen: dict[str, int] = {}
    for text in texts:
        if not text.text_version_id:
            continue
        seen[text.text_version_id] = seen.get(text.text_version_id, 0) + 1
    for version_id, count in sorted(seen.items()):
        if version_id in declared:
            continue
        issues.append(
            _issue(
                "text_version_registered",
                QASeverity.ERROR,
                f"{count} record(s) declare text_version_id {version_id}, which "
                "data/registry/text_versions.yaml does not declare; its rights and lineage "
                "are unadjudicated",
                version_id,
                record_count=count,
            )
        )
    return issues


def _wiki_page_identity(url: str) -> str | None:
    """Reduce a MediaWiki URL to the page it names, however it was fetched.

    The same page can be pinned as a human URL (``/wiki/Title``) or fetched through
    ``api.php?...&page=Title`` / ``&titles=Title``. Those are the same scope and must not be
    reported as a mismatch. Returns ``None`` for anything that is not recognisably MediaWiki,
    so a non-wiki URL falls back to exact comparison rather than being guessed at.
    """
    parsed = urlparse(url)
    if "wikisource.org" not in parsed.netloc and "wikipedia.org" not in parsed.netloc:
        return None
    if parsed.path.startswith("/wiki/"):
        title = unquote(parsed.path[len("/wiki/") :])
    else:
        query = parse_qs(parsed.query)
        # Both spellings occur: action=parse uses "page", action=query uses "titles".
        values = query.get("page") or query.get("titles")
        if not values:
            return None
        title = unquote(values[0])
    return title.replace("_", " ").strip()


def verify_checksum_scope(
    release_artifacts: list[SourceArtifact],
    raw_root: Path,
    registry_artifacts: list[SourceArtifact] | None = None,
) -> list[QAIssue]:
    """Check that a pinned checksum names a snapshot of the RIGHT thing.

    Agent C's point, and it is the sharpest critique this gate received: matching *some*
    snapshot is not verification. The registry pinned
    ``WIKISOURCE_SA.YV.VSM.SAMHITA.DEVANAGARI`` to the sha256 of the work's PREFACE AND TABLE
    OF CONTENTS rather than its samhita text. Those bytes exist, they are intact, and they
    hash correctly -- so every byte-level leg passes while verifying nothing about scope.

    Resolved here by comparing the artifact's declared URL against the ``retrieval_url`` in
    the snapshot's own metadata sidecar, reduced to page identity so that a human wiki URL
    and its ``api.php`` equivalent for the same page are treated as equal. Measured over the
    real tree: 26 artifacts agree, 1 is the genuine preface-page mispin, and 1 is a
    same-page-different-access case that this reduction correctly does not flag.

    Every artifact this check could NOT verify is reported as INFO rather than passed over.
    That matters more than it sounds: when the wrong-scope checksum was later *removed*
    instead of corrected, the check lost its input and the gate went green. A caller must be
    able to tell "verified correct" from "nothing to verify".
    """
    issues: list[QAIssue] = []
    on_disk = _content_addressed_index(raw_root)
    registry = {
        artifact.artifact_id: artifact
        for artifact in (
            registry_artifacts if registry_artifacts is not None else load_source_artifacts()
        )
    }
    for artifact in release_artifacts:
        declared = registry.get(artifact.artifact_id)
        checksum = artifact.checksum_sha256 or (declared.checksum_sha256 if declared else None)
        if not checksum:
            # Reported, not skipped. When the wrong-scope checksum on the Vajasaneyi samhita
            # artifact was REMOVED rather than corrected, this check silently stopped having
            # anything to compare and the gate went green -- a skip wearing a pass. An
            # unverifiable claim has to look different from a verified one.
            issues.append(
                _issue(
                    "checksum_scope_agreement",
                    QASeverity.INFO,
                    f"{artifact.artifact_id}: no checksum on either side, so the scope of "
                    "the bytes it names was NOT verified",
                    artifact.artifact_id,
                )
            )
            continue
        path = on_disk.get(checksum)
        if path is None:
            issues.append(
                _issue(
                    "checksum_scope_agreement",
                    QASeverity.INFO,
                    f"{artifact.artifact_id}: the pinned bytes are not retained locally, so "
                    "their scope was NOT verified",
                    artifact.artifact_id,
                    checksum=checksum,
                )
            )
            continue
        sidecar = path.parent / f"{path.stem}.metadata.json"
        if not sidecar.exists():
            issues.append(
                _issue(
                    "checksum_scope_agreement",
                    QASeverity.INFO,
                    f"{artifact.artifact_id}: the pinned snapshot has no metadata sidecar, so "
                    "the scope of the bytes cannot be confirmed",
                    artifact.artifact_id,
                )
            )
            continue
        recorded = str(orjson.loads(sidecar.read_bytes()).get("retrieval_url") or "")
        wanted = str(artifact.url)
        if not recorded:
            continue
        left, right = _wiki_page_identity(wanted), _wiki_page_identity(recorded)
        if left is not None and right is not None:
            if left != right:
                issues.append(
                    _issue(
                        "checksum_scope_agreement",
                        QASeverity.ERROR,
                        f"{artifact.artifact_id}: the pinned bytes are a snapshot of "
                        f"{right!r}, not of the declared {left!r}; the checksum matches a "
                        "real snapshot of the wrong thing",
                        artifact.artifact_id,
                        declared_page=left,
                        snapshot_page=right,
                    )
                )
        elif recorded.rstrip("/") != wanted.rstrip("/"):
            issues.append(
                _issue(
                    "checksum_scope_agreement",
                    QASeverity.WARNING,
                    f"{artifact.artifact_id}: the pinned snapshot was retrieved from a "
                    "different URL than the artifact declares, and neither is a recognisable "
                    "wiki page so the scope cannot be reduced for comparison",
                    artifact.artifact_id,
                    declared_url=wanted,
                    snapshot_url=recorded,
                )
            )
    return issues


def verify_text_role_matches_registry(
    texts: list[TextVersion],
    descriptors: list[TextVersionDescriptor] | None = None,
) -> list[QAIssue]:
    """A record's ``text_role`` must equal the registry's role for that version id.

    ``TextRole`` is a permission statement, not a description: it says what VedaGraph is
    allowed to do with a reading. Choosing one in build code is therefore the same class of
    defect as constructing a ``SourceArtifact`` locally -- it asserts a permission the rights
    authority never granted. Agent E raised the live case, where a pilot emitted
    ``PRIMARY_TEXT`` for a layer the registry had deliberately registered as
    ``EXTRACTED_FROM_CONTAINER``.

    Kept as a standing check even though it currently finds nothing. That is a deliberate
    distinction from the ``SectionDiscoveryRecord`` reconciliation left unwired elsewhere in
    this module: this check has real inputs -- 21,936 text records against 13 registered
    descriptors -- so a green result is a measurement rather than a vacuous pass, and it
    guards a regression that has already happened once.

    A version id absent from the registry is not reported here; that is
    ``verify_text_version_registration``'s job, and duplicating it would double-count one
    defect.
    """
    issues: list[QAIssue] = []
    declared = {
        descriptor.text_version_id: descriptor
        for descriptor in (descriptors if descriptors is not None else load_text_versions())
    }
    seen: dict[tuple[str, str], int] = {}
    for text in texts:
        if not text.text_version_id:
            continue
        key = (text.text_version_id, str(text.text_role))
        seen[key] = seen.get(key, 0) + 1
    for (version_id, role), count in sorted(seen.items()):
        descriptor = declared.get(version_id)
        if descriptor is None or str(descriptor.text_role) == role:
            continue
        issues.append(
            _issue(
                "text_role_matches_registry",
                QASeverity.ERROR,
                f"{count} record(s) declare text_role {role} for {version_id}, but the "
                f"registry registers it as {descriptor.text_role}; TextRole is a permission "
                "statement and is not the build's to choose",
                version_id,
                emitted_role=role,
                registry_role=str(descriptor.text_role),
                record_count=count,
            )
        )
    return issues
