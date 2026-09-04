"""Configuration-driven, offline, reproducible corpus builds."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

import orjson
from pydantic import BaseModel

from vedagraph.compare.text import VersionReading, compare_readings
from vedagraph.config.registry import (
    load_build_config,
    load_source_artifacts,
    load_sources,
    load_text_versions,
    load_works,
)
from vedagraph.identity import (
    VEDAGRAPH_NAMESPACE_UUID,
    rv_mandala_identity,
    rv_mantra_identity,
    rv_sukta_identity,
    uuid_for_urn,
)
from vedagraph.ingest.adapters import (
    GRETILAdapter,
    VedaWebAdapter,
    VHPAdapter,
    WikisourceTranslationAdapter,
)
from vedagraph.models import (
    AudioRecording,
    Citation,
    CorpusBuildConfig,
    Passage,
    QAIssue,
    SourceAssertion,
    StagingTextRecord,
    StagingTranslationRecord,
    SuktaDiscoveryRecord,
    TextVersion,
    TraditionalMetadataAssertion,
    Translation,
    VHPMetadataStagingRecord,
)
from vedagraph.models.core import MetadataScope
from vedagraph.models.enums import (
    AlignmentLevel,
    AssertionStatus,
    AudioType,
    EntityType,
    MetadataPredicate,
    PassageStatus,
    QASeverity,
    QualityStatus,
    RightsStatus,
    ScopeType,
    StoragePolicy,
    TextComparisonCategory,
    TextForm,
    TranslationAlignment,
)
from vedagraph.normalize import normalize_nfc
from vedagraph.qa import CorpusRecords, qa_status, validate_corpus, write_qa_json
from vedagraph.reconcile import canonical_mantra_count
from vedagraph.storage import write_jsonl
from vedagraph.storage.manifest import build_manifest, file_sha256

#: Comparison categories that represent a known, harmless representation difference
#: between the primary and a parallel Sanskrit text version (same lineage, different
#: notation). See docs task PRIMARY_PARALLEL_TEXT_DIVERGENCE: these never raise a QA issue.
_DIVERGENCE_PASS_CATEGORIES = frozenset(
    {
        TextComparisonCategory.IDENTICAL,
        TextComparisonCategory.UNICODE_ONLY,
        TextComparisonCategory.ACCENT_ONLY,
        TextComparisonCategory.ORTHOGRAPHIC,
    }
)
#: Structural misalignment: a missing verse or a reading that is not the same passage.
_DIVERGENCE_ERROR_CATEGORIES = frozenset(
    {TextComparisonCategory.MISSING, TextComparisonCategory.STRUCTURAL_VARIANT}
)


@dataclass(frozen=True)
class ConfigBuildResult:
    output_dir: Path
    staged_dir: Path
    sukta_count: int
    mantra_count: int
    text_count: int
    parallel_text_count: int
    translation_count: int
    qa_issue_count: int
    manifest_path: Path
    report_path: Path


@dataclass(frozen=True)
class StagingBuildResult:
    staged_dir: Path
    text_count: int
    parallel_text_count: int
    translation_count: int
    metadata_count: int
    discovery_count: int
    assertion_count: int
    translation_failures: tuple[str, ...] = ()


@dataclass(frozen=True)
class LoadedStaging:
    """Everything parsed from declared snapshots, before reconciliation."""

    texts: list[StagingTextRecord]
    parallel_texts: list[StagingTextRecord]
    translations: list[StagingTranslationRecord]
    metadata: list[VHPMetadataStagingRecord]
    discoveries: list[SuktaDiscoveryRecord]
    translation_failures: list[str] = field(default_factory=list)
    gretil_full_mantra_count: int | None = None


def _derived_uuid(kind: str, *parts: object) -> UUID:
    component = ":".join(str(part) for part in parts)
    return uuid_for_urn(f"urn:vedagraph:{kind}:{component}")


def _qa_issue(
    check_id: str, severity: QASeverity, message: str, entity_id: str | None = None, **details: Any
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


def _assertion(
    subject: str,
    predicate: str,
    value: Any,
    source_id: str,
    locator: str,
    *,
    artifact_id: str | None = None,
    evidence: str | None = None,
) -> SourceAssertion:
    value_digest = sha256(orjson.dumps(value, option=orjson.OPT_SORT_KEYS)).hexdigest()
    return SourceAssertion(
        assertion_id=_derived_uuid(
            "source-assertion", subject, predicate, source_id, artifact_id or "", value_digest
        ),
        subject_id=subject,
        predicate=predicate,
        value=value,
        source_id=source_id,
        source_artifact_id=artifact_id,
        source_locator=locator,
        status=AssertionStatus.UNREVIEWED,
        evidence=evidence,
    )


def _revision_map(path: Path) -> dict[str, tuple[int | None, int | None, datetime | None]]:
    payload = orjson.loads(path.read_bytes())
    pages = payload.get("query", {}).get("pages", [])
    if isinstance(pages, dict):
        pages = list(pages.values())
    result: dict[str, tuple[int | None, int | None, datetime | None]] = {}
    for page in pages:
        revisions = page.get("revisions") or []
        revision = revisions[0] if revisions else {}
        timestamp = revision.get("timestamp")
        result[str(page.get("title", ""))] = (
            page.get("pageid") if isinstance(page.get("pageid"), int) else None,
            revision.get("revid") if isinstance(revision.get("revid"), int) else None,
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if isinstance(timestamp, str)
            else None,
        )
    return result


def _wikisource_title(scope: str) -> str:
    _, mandala, sukta = scope.split(".")
    return f"The Hymns of the Rigveda/Book {int(mandala)}/Hymn {int(sukta)}"


def _verify_inputs(config: CorpusBuildConfig) -> None:
    for source_input in config.sources:
        if not source_input.snapshot_path.exists():
            raise FileNotFoundError(source_input.snapshot_path)
        actual = file_sha256(source_input.snapshot_path)
        if actual != source_input.snapshot_sha256:
            raise ValueError(
                f"snapshot hash mismatch for {source_input.snapshot_path}: "
                f"expected {source_input.snapshot_sha256}, got {actual}"
            )


def _passage_sort_key(passage: Passage) -> tuple[int, int, int, int]:
    rank = {EntityType.SECTION: 0, EntityType.HYMN: 1, EntityType.MANTRA: 2}
    return (
        int(passage.hierarchy.get("mandala", 0)),
        int(passage.hierarchy.get("sukta", 0)),
        int(passage.hierarchy.get("mantra", 0)),
        rank.get(passage.entity_type, 9),
    )


def _parallel_sanskrit_versions(config: CorpusBuildConfig) -> dict[str, str]:
    """Map a VedaWeb ``source_version_key`` (e.g. ``aufrecht``) to the registry
    ``text_version_id`` for every VedaWeb version this build config declares as parallel.

    Driven entirely by ``config.parallel_sanskrit`` and the text-version registry, so
    adding a second parallel VedaWeb layer later needs no code change here.
    """
    registry = {
        version.text_version_id: version.source_version_key for version in load_text_versions()
    }
    return {
        registry[selection.text_version]: selection.text_version
        for selection in config.parallel_sanskrit
        if selection.text_version in registry
    }


def _load_staging(config: CorpusBuildConfig) -> LoadedStaging:
    selected = set(config.selected_suktas)
    texts: list[StagingTextRecord] = []
    parallel_texts: list[StagingTextRecord] = []
    translations: list[StagingTranslationRecord] = []
    metadata: list[VHPMetadataStagingRecord] = []
    discoveries: list[SuktaDiscoveryRecord] = []
    translation_failures: list[str] = []
    gretil_full_mantra_count: int | None = None
    revision_by_scope: dict[str, tuple[int | None, int | None, datetime | None]] = {}
    parallel_version_ids = _parallel_sanskrit_versions(config)
    parallel_roles = {
        selection.text_version: selection.role for selection in config.parallel_sanskrit
    }

    for item in config.sources:
        if item.role == "translation_revision" and item.scope:
            mapping = _revision_map(item.snapshot_path)
            revision_by_scope[item.scope] = mapping.get(
                _wikisource_title(item.scope), next(iter(mapping.values()), (None, None, None))
            )

    for item in config.sources:
        if item.role == "sanskrit":
            adapter = GRETILAdapter(
                text_selection_policy=config.text_selection_policy,
                source_artifact_id=item.source_artifact_id or "GRETIL.RV.AUFRECHT.TEI.2019",
            )
            # Parse the single GRETIL file once.  Discovery and canonical staging reuse
            # these records instead of rescanning the source two more times.
            all_texts = adapter.parse(item.snapshot_path, snapshot_id=item.snapshot_id)
            gretil_full_mantra_count = len(all_texts)
            parsed_texts = [
                record for record in all_texts if record.hierarchy["mandala"] == config.mandala
            ]
            if config.primary_sanskrit is not None:
                for text_record in parsed_texts:
                    text_record.text_version_id = config.primary_sanskrit.text_version
                    text_record.text_role = config.primary_sanskrit.role
            texts.extend(
                text_record
                for text_record in parsed_texts
                if text_record.hierarchy["mandala"] == config.mandala
                and text_record.hierarchy["sukta"] in selected
            )
            discoveries.extend(
                adapter.discover_suktas_from_records(
                    parsed_texts, snapshot_id=item.snapshot_id, mandala=config.mandala
                )
            )
        elif (
            item.role == "sanskrit_parallel"
            and item.source_id == "VEDAWEB"
            and parallel_version_ids
        ):
            vedaweb_adapter = VedaWebAdapter(
                source_artifact_id=item.source_artifact_id or "VEDAWEB.RV.BOOK01.TEI.D3EB8AF",
                versions=tuple(parallel_version_ids),
            )
            parsed_parallel = vedaweb_adapter.parse_versions(
                item.snapshot_path, snapshot_id=item.snapshot_id, suktas=frozenset(selected)
            )
            for record in parsed_parallel:
                source_key = (record.text_version_id or "").rsplit("#", 1)[-1]
                canonical_id = parallel_version_ids.get(source_key)
                if canonical_id is not None:
                    record.text_version_id = canonical_id
                    record.text_role = parallel_roles[canonical_id]
            parallel_texts.extend(parsed_parallel)
            discoveries.extend(
                vedaweb_adapter.discover_suktas_from_records(
                    parsed_parallel, snapshot_id=item.snapshot_id, mandala=config.mandala
                )
            )
        elif item.role == "discovery" and item.source_id == "VHP":
            discoveries.extend(
                VHPAdapter().discover_suktas(
                    item.snapshot_path, snapshot_id=item.snapshot_id, mandala=config.mandala
                )
            )
        elif item.role == "translation" and item.scope:
            _, mandala, sukta = item.scope.split(".")
            page_id, revision_id, revision_timestamp = revision_by_scope.get(
                item.scope, (None, None, None)
            )
            try:
                parsed_translations = WikisourceTranslationAdapter(
                    source_artifact_id=item.source_artifact_id or "GRIFFITH.RV.1896.WIKISOURCE"
                ).parse_translations(
                    item.snapshot_path,
                    snapshot_id=item.snapshot_id,
                    mandala=int(mandala),
                    sukta=int(sukta),
                    revision_timestamp=revision_timestamp,
                )
            except ValueError:
                translation_failures.append(item.scope)
                continue
            for translation_record in parsed_translations:
                if translation_record.page_id is None:
                    translation_record.page_id = page_id
                if translation_record.revision_id is None:
                    translation_record.revision_id = revision_id
            translations.extend(parsed_translations)
        elif item.role == "metadata" and item.source_id == "VHP":
            metadata.append(
                VHPAdapter().parse_metadata(item.snapshot_path, snapshot_id=item.snapshot_id)
            )

    return LoadedStaging(
        texts=sorted(
            texts,
            key=lambda record: tuple(
                int(record.hierarchy[name]) for name in ("mandala", "sukta", "mantra")
            ),
        ),
        parallel_texts=sorted(
            parallel_texts,
            key=lambda record: (
                *(int(record.hierarchy[name]) for name in ("mandala", "sukta", "mantra")),
                record.text_version_id or "",
            ),
        ),
        translations=sorted(
            translations,
            key=lambda record: tuple(
                int(record.hierarchy[name]) for name in ("mandala", "sukta", "mantra")
            ),
        ),
        metadata=sorted(metadata, key=lambda record: int(record.hierarchy["sukta"])),
        discoveries=sorted(discoveries, key=lambda record: (record.sukta_number, record.source_id)),
        translation_failures=sorted(translation_failures),
        gretil_full_mantra_count=gretil_full_mantra_count,
    )


def _persist_staging(
    staged_dir: Path, staging: LoadedStaging, assertions: list[SourceAssertion]
) -> None:
    write_jsonl(staged_dir / "gretil_texts.jsonl", staging.texts)
    write_jsonl(staged_dir / "vedaweb_parallel_texts.jsonl", staging.parallel_texts)
    write_jsonl(staged_dir / "wikisource_translations.jsonl", staging.translations)
    write_jsonl(staged_dir / "vhp_metadata.jsonl", staging.metadata)
    write_jsonl(staged_dir / "discovery.jsonl", staging.discoveries)
    write_jsonl(staged_dir / "source_assertions.jsonl", assertions)


def stage_from_config(config_path: Path) -> StagingBuildResult:
    """Persist source-specific staging and assertions without canonical reconciliation."""
    config = load_build_config(config_path)
    _verify_inputs(config)
    staging = _load_staging(config)
    assertions = _build_assertions(config, staging)
    staged_dir = config.staging_location or Path("data/staged") / config.dataset_id
    _persist_staging(staged_dir, staging, assertions)
    return StagingBuildResult(
        staged_dir=staged_dir,
        text_count=len(staging.texts),
        parallel_text_count=len(staging.parallel_texts),
        translation_count=len(staging.translations),
        metadata_count=len(staging.metadata),
        discovery_count=len(staging.discoveries),
        assertion_count=len(assertions),
        translation_failures=tuple(staging.translation_failures),
    )


def _build_assertions(config: CorpusBuildConfig, staging: LoadedStaging) -> list[SourceAssertion]:
    assertions: list[SourceAssertion] = []
    for text_record in staging.texts:
        mandala, sukta, mantra = (
            int(text_record.hierarchy[name]) for name in ("mandala", "sukta", "mantra")
        )
        key, _, _ = rv_mantra_identity(mandala, sukta, mantra)
        assertions.append(
            _assertion(
                key,
                "SANSKRIT_TEXT",
                text_record.text_original,
                text_record.source_id,
                text_record.source_locator,
                artifact_id=text_record.source_artifact_id,
                evidence=f"TEI selection policy: {text_record.text_selection_policy}",
            )
        )
    for translation_record in staging.translations:
        mandala, sukta, mantra = (
            int(translation_record.hierarchy[name]) for name in ("mandala", "sukta", "mantra")
        )
        key, _, _ = rv_mantra_identity(mandala, sukta, mantra)
        assertions.append(
            _assertion(
                key,
                "ENGLISH_TRANSLATION",
                translation_record.text_original,
                translation_record.source_id,
                translation_record.source_locator,
                artifact_id=translation_record.source_artifact_id,
                evidence=(
                    f"MediaWiki revision {translation_record.revision_id}; "
                    f"alignment {translation_record.alignment}"
                ),
            )
        )
    for metadata_record in staging.metadata:
        mandala = int(metadata_record.hierarchy["mandala"])
        sukta = int(metadata_record.hierarchy["sukta"])
        key, _, _ = rv_sukta_identity(mandala, sukta)
        for predicate, values in (
            ("HAS_RISHI", metadata_record.rishis),
            ("HAS_DEVATA", metadata_record.devatas),
            ("HAS_CHANDAS", metadata_record.chandas),
        ):
            for value in values:
                assertions.append(
                    _assertion(key, predicate, value, "VHP", metadata_record.source_locator)
                )
        if metadata_record.reported_mantra_count is not None:
            assertions.append(
                _assertion(
                    key,
                    "REPORTED_MANTRA_COUNT",
                    metadata_record.reported_mantra_count,
                    "VHP",
                    metadata_record.source_locator,
                )
            )
    for source_id in sorted({record.source_id for record in staging.discoveries}):
        source_records = [record for record in staging.discoveries if record.source_id == source_id]
        assertions.append(
            _assertion(
                f"VG:RV:SAK:M{config.mandala:02d}",
                "REPORTED_SUKTA_COUNT",
                len({record.sukta_number for record in source_records}),
                source_id,
                source_records[0].discovery_source,
                artifact_id=source_records[0].source_artifact_id,
            )
        )
    gretil_discovery = [record for record in staging.discoveries if record.source_id == "GRETIL"]
    if gretil_discovery:
        assertions.append(
            _assertion(
                f"VG:RV:SAK:M{config.mandala:02d}",
                "REPORTED_MANTRA_COUNT",
                sum(record.known_mantra_count or 0 for record in gretil_discovery),
                "GRETIL",
                "TEI lg count within Mandala",
                artifact_id=gretil_discovery[0].source_artifact_id,
            )
        )
        selected = set(config.selected_suktas)
        for discovery in gretil_discovery:
            if discovery.sukta_number in selected:
                assertions.append(
                    _assertion(
                        discovery.canonical_sukta_key,
                        "REPORTED_MANTRA_COUNT",
                        discovery.known_mantra_count,
                        "GRETIL",
                        discovery.source_locator,
                        artifact_id=discovery.source_artifact_id,
                    )
                )
        full_rigveda_count = staging.gretil_full_mantra_count or sum(
            record.known_mantra_count or 0 for record in gretil_discovery
        )
        assertions.append(
            _assertion(
                config.work_id,
                "REPORTED_MANTRA_COUNT",
                full_rigveda_count,
                "GRETIL",
                "TEI total lg count",
                artifact_id=gretil_discovery[0].source_artifact_id,
            )
        )
    return sorted(
        assertions,
        key=lambda item: (item.subject_id, item.predicate, item.source_id, str(item.assertion_id)),
    )


def _primary_parallel_divergence_issues(
    passages: list[Passage],
    texts: list[TextVersion],
    primary_version_id: str,
    parallel_version_id: str,
) -> list[QAIssue]:
    """QA policy PRIMARY_PARALLEL_TEXT_DIVERGENCE: classify every aligned primary/parallel
    reading pair. A known representation-only difference (accent notation, Unicode form,
    whitespace/punctuation) passes silently; an unresolved textual difference is a WARNING;
    a missing or structurally different reading is an ERROR. Both texts trace to the same
    Aufrecht lineage, so anything beyond notation deserves a human look.
    """
    by_passage: dict[UUID, dict[str, TextVersion]] = {}
    for text in texts:
        if text.text_version_id in (primary_version_id, parallel_version_id):
            by_passage.setdefault(text.passage_id, {})[text.text_version_id] = text
    issues: list[QAIssue] = []
    for passage in passages:
        if passage.entity_type != EntityType.MANTRA:
            continue
        versions = by_passage.get(passage.entity_id, {})
        primary = versions.get(primary_version_id)
        parallel = versions.get(parallel_version_id)
        if primary is None or parallel is None:
            missing = primary_version_id if primary is None else parallel_version_id
            issues.append(
                _qa_issue(
                    "primary_parallel_text_divergence",
                    QASeverity.ERROR,
                    f"{missing} is missing at {passage.canonical_citation}",
                    str(passage.entity_id),
                    category=str(TextComparisonCategory.MISSING),
                    missing_version=missing,
                )
            )
            continue
        result = compare_readings(
            passage_key=passage.canonical_key,
            citation=passage.canonical_citation,
            left=VersionReading(primary_version_id, primary.text_original, primary.text_role),
            right=VersionReading(parallel_version_id, parallel.text_original, parallel.text_role),
        )
        if result.category in _DIVERGENCE_PASS_CATEGORIES:
            continue
        severity = (
            QASeverity.ERROR
            if result.category in _DIVERGENCE_ERROR_CATEGORIES
            else QASeverity.WARNING
        )
        issues.append(
            _qa_issue(
                "primary_parallel_text_divergence",
                severity,
                f"{primary_version_id} vs {parallel_version_id} differ "
                f"({result.category}) at {passage.canonical_citation}",
                str(passage.entity_id),
                category=str(result.category),
                similarity=result.similarity,
                classification_basis=result.classification_basis,
            )
        )
    return sorted(issues, key=lambda issue: (issue.severity, str(issue.entity_id)))


def _report(
    config: CorpusBuildConfig,
    passages: list[Passage],
    texts: list[TextVersion],
    translations: list[Translation],
    metadata: list[TraditionalMetadataAssertion],
    audio: list[AudioRecording],
    discoveries: list[SuktaDiscoveryRecord],
    issues: Sequence[BaseModel],
) -> str:
    mantras = canonical_mantra_count(passages)
    suktas = sum(passage.entity_type == EntityType.HYMN for passage in passages)
    discovered = len({item.sukta_number for item in discoveries})
    expected_mantras = sum(
        item.known_mantra_count or 0 for item in discoveries if item.source_id == "GRETIL"
    )
    metadata_suktas = {item.scope.passage_id for item in metadata}
    warnings = sum(getattr(issue, "severity", None) == QASeverity.WARNING for issue in issues)
    errors = sum(getattr(issue, "severity", None) == QASeverity.ERROR for issue in issues)
    primary_texts = [
        text
        for text in texts
        if config.primary_sanskrit is not None
        and text.text_version_id == config.primary_sanskrit.text_version
    ]
    primary_coverage = f"{len(primary_texts) / mantras:.1%}" if mantras else "n/a"
    parallel_selections = [s for s in config.parallel_sanskrit if s.role == "PARALLEL_TEXT"]
    parallel_coverage_lines = [
        f"- `{selection.text_version}`: "
        f"{sum(1 for t in texts if t.text_version_id == selection.text_version)}/{mantras}"
        for selection in parallel_selections
    ]
    rishi = sum(1 for item in metadata if item.predicate == MetadataPredicate.HAS_RISHI)
    devata = sum(1 for item in metadata if item.predicate == MetadataPredicate.HAS_DEVATA)
    chandas = sum(1 for item in metadata if item.predicate == MetadataPredicate.HAS_CHANDAS)
    return f"""# Rigveda Mandala {config.mandala} Build Report

- Dataset: `{config.dataset_id}`

## Textual structure

- Suktas discovered: {discovered}
- Suktas ingested: {suktas}
- Mantras ingested: {mantras}

## Primary Sanskrit ({config.primary_sanskrit.text_version if config.primary_sanskrit else "none"})

- Coverage: {len(primary_texts)}/{mantras} ({primary_coverage})

## Parallel Sanskrit

{chr(10).join(parallel_coverage_lines) or "- none configured"}

## English translation

- Coverage: {len(translations)}/{mantras} ({len(translations) / mantras:.1%})

## Traditional metadata (VHP, partial by design; see docs/STATUS.md)

- Suktas with any traditional metadata: {len(metadata_suktas)}/{suktas}
- Rishi assertions: {rishi}
- Devata assertions: {devata}
- Chandas assertions: {chandas}

## Audio/media references

- Suktas with an external audio reference: {len({item.target_id for item in audio})}/{suktas}

## Source expectation versus actual

- Expected Sukta count: 191 (GRETIL TEI and VHP navigation assertions)
- Discovered: {discovered}
- Canonical ingested: {suktas}
- Expected Mandala mantra count: {expected_mantras} (GRETIL TEI assertion)
- Canonical ingested: {mantras}
- Mantra coverage: {mantras / expected_mantras:.1%}

## Sources

- GRETIL `sa_Rgveda-edAufrecht.xml`: primary Sanskrit text, ORIGINAL policy, CC BY-NC-SA 4.0.
- VedaWeb Book 1 TEI (commit-pinned): parallel Sanskrit text where configured.
- VHP: verification-only hierarchy, traditional metadata, and external media references.
- Wikisource Griffith 1896: public-domain translation with page/revision provenance.

## QA

- Errors: {errors}
- Warnings: {warnings}
- Informational findings: {len(issues) - errors - warnings}
"""


def build_from_config(config_path: Path) -> ConfigBuildResult:
    """Build entirely from declared local snapshots; never performs network retrieval."""
    config = load_build_config(config_path)
    _verify_inputs(config)
    staging = _load_staging(config)
    assertions = _build_assertions(config, staging)
    staged_dir = config.staging_location or Path("data/staged") / config.dataset_id
    _persist_staging(staged_dir, staging, assertions)

    mandala_key, mandala_urn, mandala_id = rv_mandala_identity(config.mandala)
    passages = [
        Passage(
            entity_id=mandala_id,
            canonical_key=mandala_key,
            canonical_urn=mandala_urn,
            entity_type=EntityType.SECTION,
            work_id=config.work_id,
            hierarchy={"mandala": config.mandala},
            canonical_citation=f"RV {config.mandala}",
            sequence_in_parent=config.mandala,
            status=PassageStatus.CANONICAL,
        )
    ]
    sukta_ids: dict[int, UUID] = {}
    sukta_keys: dict[int, str] = {}
    for sukta in config.selected_suktas:
        key, urn, identifier = rv_sukta_identity(config.mandala, sukta)
        sukta_ids[sukta] = identifier
        sukta_keys[sukta] = key
        passages.append(
            Passage(
                entity_id=identifier,
                canonical_key=key,
                canonical_urn=urn,
                entity_type=EntityType.HYMN,
                work_id=config.work_id,
                hierarchy={"mandala": config.mandala, "sukta": sukta},
                canonical_citation=f"RV {config.mandala}.{sukta}",
                parent_key=mandala_key,
                sequence_in_parent=sukta,
            )
        )
    texts: list[TextVersion] = []
    translations: list[Translation] = []
    citations: list[Citation] = []
    mantra_ids: dict[tuple[int, int], UUID] = {}
    for staged_text in staging.texts:
        sukta = int(staged_text.hierarchy["sukta"])
        mantra = int(staged_text.hierarchy["mantra"])
        key, urn, identifier = rv_mantra_identity(config.mandala, sukta, mantra)
        mantra_ids[(sukta, mantra)] = identifier
        passages.append(
            Passage(
                entity_id=identifier,
                canonical_key=key,
                canonical_urn=urn,
                entity_type=EntityType.MANTRA,
                work_id=config.work_id,
                hierarchy={"mandala": config.mandala, "sukta": sukta, "mantra": mantra},
                canonical_citation=f"RV {config.mandala}.{sukta}.{mantra}",
                parent_key=sukta_keys[sukta],
                sequence_in_parent=mantra,
            )
        )
        normalized = normalize_nfc(staged_text.text_original)
        texts.append(
            TextVersion(
                text_id=_derived_uuid(
                    "text",
                    identifier,
                    staged_text.source_artifact_id,
                    config.text_selection_policy,
                ),
                passage_id=identifier,
                language="sa",
                script="Latin",
                text_form=TextForm.SAMHITA,
                text_role=staged_text.text_role,
                text_version_id=staged_text.text_version_id,
                text_original=staged_text.text_original,
                text_nfc=normalized,
                accented=staged_text.accented,
                source_id=staged_text.source_id,
                source_artifact_id=staged_text.source_artifact_id,
                source_locator=staged_text.source_locator,
                content_sha256=sha256(normalized.encode("utf-8")).hexdigest(),
                rights_status=RightsStatus.CC_BY_NC_SA,
            )
        )
        citations.append(
            Citation(
                citation_id=_derived_uuid("citation", identifier, "rv-standard"),
                passage_id=identifier,
                label=f"RV {config.mandala}.{sukta}.{mantra}",
                system="RV_STANDARD",
                is_canonical=True,
            )
        )

    rights_by_version = {
        version.text_version_id: version.normalized_rights for version in load_text_versions()
    }
    for staged_parallel in staging.parallel_texts:
        sukta = int(staged_parallel.hierarchy["sukta"])
        mantra = int(staged_parallel.hierarchy["mantra"])
        parallel_target = mantra_ids.get((sukta, mantra))
        if parallel_target is None:
            continue
        normalized = normalize_nfc(staged_parallel.text_original)
        texts.append(
            TextVersion(
                text_id=_derived_uuid(
                    "text",
                    parallel_target,
                    staged_parallel.source_artifact_id,
                    staged_parallel.text_version_id,
                ),
                passage_id=parallel_target,
                language="sa",
                script=staged_parallel.script,
                text_form=TextForm.SAMHITA,
                text_role=staged_parallel.text_role,
                text_version_id=staged_parallel.text_version_id,
                text_original=staged_parallel.text_original,
                text_nfc=normalized,
                accented=staged_parallel.accented,
                source_id=staged_parallel.source_id,
                source_artifact_id=staged_parallel.source_artifact_id,
                source_locator=staged_parallel.source_locator,
                content_sha256=sha256(normalized.encode("utf-8")).hexdigest(),
                rights_status=rights_by_version.get(
                    staged_parallel.text_version_id or "", RightsStatus.UNKNOWN
                ),
            )
        )

    for staged_translation in staging.translations:
        sukta = int(staged_translation.hierarchy["sukta"])
        mantra = int(staged_translation.hierarchy["mantra"])
        target = mantra_ids.get((sukta, mantra))
        if target is None:
            continue
        translations.append(
            Translation(
                translation_id=_derived_uuid(
                    "translation",
                    target,
                    staged_translation.source_artifact_id,
                    staged_translation.revision_id,
                ),
                passage_id=target,
                language="en",
                translator=staged_translation.translator,
                work_edition=staged_translation.work_edition,
                year=staged_translation.year,
                text=normalize_nfc(staged_translation.text_original),
                source_id=staged_translation.source_id,
                source_artifact_id=staged_translation.source_artifact_id,
                rights_status=RightsStatus.PUBLIC_DOMAIN,
                alignment_level=(
                    AlignmentLevel.MANTRA
                    if staged_translation.alignment == TranslationAlignment.EXACT_MANTRA_ALIGNMENT
                    else AlignmentLevel.HYMN
                ),
                alignment=staged_translation.alignment,
                quality_status=QualityStatus.MACHINE_ALIGNED,
                source_page_title=staged_translation.page_title,
                source_page_id=staged_translation.page_id,
                source_revision_id=staged_translation.revision_id,
                source_revision_timestamp=staged_translation.revision_timestamp,
                canonical_page_url=staged_translation.canonical_page_url,
            )
        )

    traditional_metadata: list[TraditionalMetadataAssertion] = []
    audio: list[AudioRecording] = []
    predicate_map = {
        MetadataPredicate.HAS_RISHI: "rishis",
        MetadataPredicate.HAS_DEVATA: "devatas",
        MetadataPredicate.HAS_CHANDAS: "chandas",
    }
    for staged_metadata_record in staging.metadata:
        sukta = int(staged_metadata_record.hierarchy["sukta"])
        target = sukta_ids.get(sukta)
        if target is None:
            continue
        for predicate, attribute in predicate_map.items():
            for value in getattr(staged_metadata_record, attribute):
                if re.search(r"[०-९0-9]", value):  # noqa: RUF001
                    # Preserve source-range strings as generic assertions until a reviewed
                    # range parser can assign exact MetadataScope values.
                    continue
                traditional_metadata.append(
                    TraditionalMetadataAssertion(
                        assertion_id=_derived_uuid("assertion", target, predicate, value, "VHP"),
                        predicate=predicate,
                        value=value,
                        scope=MetadataScope(scope_type=ScopeType.WHOLE_PASSAGE, passage_id=target),
                        source_id="VHP",
                        source_locator=staged_metadata_record.source_locator,
                        status=AssertionStatus.UNREVIEWED,
                    )
                )
        for media_url in staged_metadata_record.media_urls:
            media_id = Path(str(media_url)).stem
            audio.append(
                AudioRecording(
                    audio_id=_derived_uuid("audio", target, "VHP", media_id),
                    target_id=target,
                    language="sa",
                    audio_type=AudioType.VEDIC_RECITATION,
                    recension="Shakala",
                    source_id="VHP",
                    source_media_id=media_id,
                    source_url=media_url,
                    storage_policy=StoragePolicy.EXTERNAL_REFERENCE,
                    rights_status=RightsStatus.PERMISSION_REQUIRED,
                    mime_type="video/mp4",
                )
            )

    passages.sort(key=_passage_sort_key)
    passage_order = {passage.entity_id: index for index, passage in enumerate(passages)}
    texts.sort(key=lambda item: (passage_order[item.passage_id], str(item.text_id)))
    translations.sort(key=lambda item: (passage_order[item.passage_id], str(item.translation_id)))
    citations.sort(key=lambda item: (passage_order[item.passage_id], item.system, item.label))
    traditional_metadata.sort(
        key=lambda item: (passage_order[item.scope.passage_id], item.predicate, item.value)
    )
    audio.sort(key=lambda item: (passage_order[item.target_id], item.source_media_id or ""))

    sources = sorted(load_sources(), key=lambda item: item.source_id)
    artifacts = sorted(load_source_artifacts(), key=lambda item: item.artifact_id)
    works = [work for work in load_works() if work.work_id == config.work_id]
    corpus_records = CorpusRecords(
        passages=passages,
        texts=texts,
        translations=translations,
        metadata=traditional_metadata,
        sources=sources,
        citations=citations,
        audio_recordings=audio,
        audio_segments=[],
        source_assertions=assertions,
        discoveries=staging.discoveries,
    )
    issues = list(validate_corpus(corpus_records))

    parallel_selection = next(
        (selection for selection in config.parallel_sanskrit if selection.role == "PARALLEL_TEXT"),
        None,
    )
    if config.primary_sanskrit is not None and parallel_selection is not None:
        issues.extend(
            _primary_parallel_divergence_issues(
                passages,
                texts,
                config.primary_sanskrit.text_version,
                parallel_selection.text_version,
            )
        )
    for scope in staging.translation_failures:
        issues.append(
            _qa_issue(
                "translation_page_parse_failed",
                QASeverity.WARNING,
                f"no Wikisource poem stanzas could be parsed for {scope}; "
                "translation coverage for this Sukta is missing, not fabricated",
                scope,
            )
        )
    uncertain_suktas: dict[int, int] = {}
    for staged_translation in staging.translations:
        if staged_translation.alignment == TranslationAlignment.UNCERTAIN_ALIGNMENT:
            sukta = int(staged_translation.hierarchy["sukta"])
            uncertain_suktas[sukta] = uncertain_suktas.get(sukta, 0) + 1
    for sukta, stanza_count in sorted(uncertain_suktas.items()):
        issues.append(
            _qa_issue(
                "translation_alignment_uncertain",
                QASeverity.WARNING,
                f"RV {config.mandala}.{sukta}: {stanza_count} Wikisource stanza(s) parsed "
                "without a confirmed 1..N verse-number match; some mantras may be missing "
                "or misnumbered rather than mantra-exact",
                f"RV.{config.mandala}.{sukta}",
                stanza_count=stanza_count,
            )
        )
    # A page can parse with internally consistent 1..N stanza numbering (EXACT_MANTRA_ALIGNMENT)
    # while still supplying fewer stanzas than the Sukta actually has mantras — "exact" only
    # means self-consistent, not complete. Cross-check against the real canonical mantra count.
    sukta_by_mantra_id = {identifier: sukta for (sukta, _mantra), identifier in mantra_ids.items()}
    mantra_count_by_sukta: dict[int, int] = {}
    for sukta, _mantra in mantra_ids:
        mantra_count_by_sukta[sukta] = mantra_count_by_sukta.get(sukta, 0) + 1
    # Deliberately a set of distinct translated passages, not a running total: two
    # translations landing on the same mantra (see duplicate_translation_for_passage QA)
    # must not silently paper over a different mantra in the same Sukta having none.
    translated_targets_by_sukta: dict[int, set[UUID]] = {}
    for translation in translations:
        translated_sukta = sukta_by_mantra_id.get(translation.passage_id)
        if translated_sukta is not None:
            translated_targets_by_sukta.setdefault(translated_sukta, set()).add(
                translation.passage_id
            )
    already_flagged_suktas = {
        int(scope.rsplit(".", 1)[-1]) for scope in staging.translation_failures
    }
    for sukta, expected_total in sorted(mantra_count_by_sukta.items()):
        if sukta in already_flagged_suktas:
            continue
        translated = len(translated_targets_by_sukta.get(sukta, set()))
        if translated < expected_total:
            issues.append(
                _qa_issue(
                    "translation_coverage_incomplete",
                    QASeverity.WARNING,
                    f"RV {config.mandala}.{sukta}: {translated}/{expected_total} mantras have "
                    "a Griffith translation; the remainder have no parsed stanza at that "
                    "position, which is missing rather than fabricated",
                    f"RV.{config.mandala}.{sukta}",
                    translated=translated,
                    expected=expected_total,
                )
            )
    issues.sort(key=lambda issue: (issue.severity, issue.check_id, str(issue.issue_id)))

    output_dir = config.output_location
    collections: dict[str, Sequence[BaseModel]] = {
        "works.jsonl": works,
        "passages.jsonl": passages,
        "text_versions.jsonl": texts,
        "translations.jsonl": translations,
        "traditional_metadata.jsonl": traditional_metadata,
        "sources.jsonl": sources,
        "source_artifacts.jsonl": artifacts,
        "source_assertions.jsonl": assertions,
        "discoveries.jsonl": staging.discoveries,
        "citations.jsonl": citations,
        "audio_recordings.jsonl": audio,
        "audio_segments.jsonl": [],
        "qa_issues.jsonl": issues,
    }
    generated: dict[Path, int] = {}
    for name, values in collections.items():
        path = output_dir / name
        generated[path] = write_jsonl(path, values)
    qa_path = Path("data/qa") / f"{config.dataset_id}.json"
    write_qa_json(qa_path, issues)
    report_path = output_dir / "REPORT.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        _report(
            config,
            passages,
            texts,
            translations,
            traditional_metadata,
            audio,
            staging.discoveries,
            issues,
        ),
        encoding="utf-8",
        newline="\n",
    )
    generated[report_path] = 1

    config_hash = file_sha256(config_path)
    manifest = build_manifest(
        root=output_dir.parents[1],
        version=config.release_version,
        works=[config.work_id],
        passage_count=canonical_mantra_count(passages),
        source_snapshot_ids=sorted({item.snapshot_id for item in config.sources}),
        source_artifact_ids=sorted(
            {item.source_artifact_id for item in config.sources if item.source_artifact_id}
        ),
        raw_snapshot_hashes={item.snapshot_id: item.snapshot_sha256 for item in config.sources},
        build_config_sha256=config_hash,
        parser_versions={
            f"{item.source_id}:{item.role}": item.parser_version for item in config.sources
        },
        reconciliation_policy_version=config.reconciliation_policy_version,
        qa_policy_version=config.qa_policy_version,
        generated=generated,
        qa_status=qa_status(issues),
        built_at=config.build_timestamp,
    )
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_bytes(
        orjson.dumps(
            manifest.model_dump(mode="json", exclude_none=True),
            option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS,
        )
        + b"\n"
    )
    return ConfigBuildResult(
        output_dir=output_dir,
        staged_dir=staged_dir,
        sukta_count=len(config.selected_suktas),
        mantra_count=canonical_mantra_count(passages),
        text_count=len(texts) - len(staging.parallel_texts),
        parallel_text_count=len(staging.parallel_texts),
        translation_count=len(translations),
        qa_issue_count=len(issues),
        manifest_path=manifest_path,
        report_path=report_path,
    )
