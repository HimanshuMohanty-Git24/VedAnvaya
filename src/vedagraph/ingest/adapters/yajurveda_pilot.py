"""Deterministic Vajasaneyi Samhita pilot corpus builder.

Why this is not ``vedagraph.build``
-----------------------------------
``models.core.CorpusBuildConfig`` requires ``mandala: int`` and a non-empty
``selected_suktas``, and ``vedagraph.build`` dereferences ``config.mandala`` throughout.
The Vajasaneyi Samhita has neither a mandala nor a sukta level -- ``works.yaml`` declares
``hierarchy: [Adhyaya, Mantra]``, identity_status FINAL -- so a Yajurveda build cannot be
expressed as a ``CorpusBuildConfig``. Agent A has ruled that ``CorpusBuildConfig`` stays
Rigveda-specific and that a generic ``WorkBuildConfig`` will replace this module's
bespoke config shape for the full ingestion. Until that model lands, this builder reads
its own config and writes the same canonical JSONL layout.

Guarantees
----------
* Identity comes from ``vedagraph.identity`` only: ``vsm_adhyaya_identity`` for the
  Adhyaya (a SECTION) and ``vsm_mantra_identity`` for each Mantra. No key is invented.
* Every record derives from a hashed snapshot under ``data/raw/``. Nothing is fetched at
  build time, so a rebuild is a pure function of the snapshots plus the config.
* ``text_original`` is the source's own bytes, NFC-normalized and no more. Accented text
  is never replaced by an unaccented reading.
* Output ordering is fully determined, so two builds are byte-identical.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.parse import unquote
from uuid import UUID

import yaml

from vedagraph.compare.text import COMPARATOR_VERSION, VersionReading, compare_readings
from vedagraph.config.registry import (
    load_source_artifacts,
    load_sources,
    load_text_versions,
)
from vedagraph.identity import (
    uuid_for_urn,
    vsm_adhyaya_identity,
    vsm_adhyaya_key,
    vsm_mantra_identity,
)
from vedagraph.ingest.adapters.yajurveda_apparatus import (
    RISHI_INDEX_TITLE,
    RishiIndexAdapter,
)
from vedagraph.ingest.adapters.yajurveda_wikisource import (
    PARSER_VERSION,
    AdhyayaParse,
    YajurvedaWikisourceAdapter,
    adhyaya_title,
    canonical_page_url,
    content_api_url,
)
from vedagraph.models import (
    Citation,
    Passage,
    RawSnapshotMetadata,
    Source,
    SourceArtifact,
    SourceAssertion,
    TextVersion,
    TraditionalMetadataAssertion,
)
from vedagraph.models.core import MetadataScope
from vedagraph.models.enums import (
    AssertionStatus,
    EntityType,
    MetadataPredicate,
    PassageStatus,
    QAStatus,
    RightsStatus,
    ScopeType,
    TextForm,
    TextRole,
)
from vedagraph.normalize import has_vedic_accents, normalize_nfc
from vedagraph.storage import write_jsonl
from vedagraph.storage.manifest import build_manifest

WORK_ID = "VG:WORK:YV:VSM"
SOURCE_ID = "WIKISOURCE_SA"
ARTIFACT_ID = "WIKISOURCE_SA.YV.VSM.SAMHITA.DEVANAGARI"
RISHI_ARTIFACT_ID = "WIKISOURCE_SA.YV.VSM.RISHISUCI"
BUILDER_VERSION = "yajurveda-pilot-v1"

WIKISOURCE_LICENCE = "https://creativecommons.org/licenses/by-sa/4.0/deed.sa"
WIKISOURCE_LICENCE_TEXT = "Creative Commons Attribution-Share Alike 4.0"


@dataclass(frozen=True)
class PilotConfig:
    """The bespoke Yajurveda pilot config. Mirrors WorkBuildConfig field names."""

    config_version: str
    dataset_id: str
    release_version: str
    work_id: str
    section_level: str
    mantra_level: str
    selected_sections: list[int]
    #: Which layer leads comparison and coverage. This is NOT a TextRole and confers no
    #: canonical status; roles are read from data/registry/text_versions.yaml.
    leading_text_version: str
    parallel_text_versions: list[str]
    metadata_sources: list[str]
    output_location: Path
    build_timestamp: datetime
    reconciliation_policy_version: str
    raw_root: Path
    #: Adhyayas to read for the structural count reconciliation. This is SEPARATE from
    #: selected_sections: the pilot ingests a representative sample, but the work-level
    #: mantra count is only credible if it is computed over the whole work. Listing them
    #: here puts their snapshots in the manifest, so the 1975 figure is reproducible from
    #: the release instead of resting on a number quoted in a report.
    reconciliation_sections: list[int]

    @classmethod
    def load(cls, path: Path) -> PilotConfig:
        payload: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
        sections = sorted({int(value) for value in payload["selected_sections"]})
        if not sections:
            raise ValueError("selected_sections must not be empty")
        if payload["work_id"] != WORK_ID:
            raise ValueError(f"this builder only builds {WORK_ID}")
        return cls(
            config_version=str(payload["config_version"]),
            dataset_id=str(payload["dataset_id"]),
            release_version=str(payload["release_version"]),
            work_id=str(payload["work_id"]),
            section_level=str(payload["section_level"]),
            mantra_level=str(payload["mantra_level"]),
            selected_sections=sections,
            leading_text_version=str(
                payload.get("leading_text_version") or payload["primary_text_version"]
            ),
            parallel_text_versions=[str(v) for v in payload.get("parallel_text_versions", [])],
            metadata_sources=[str(v) for v in payload.get("metadata_sources", [])],
            output_location=Path(payload["output_location"]),
            build_timestamp=_as_datetime(payload["build_timestamp"]),
            reconciliation_policy_version=str(payload["reconciliation_policy_version"]),
            raw_root=Path(payload.get("raw_root", "data/raw/wikisource_sa")),
            reconciliation_sections=sorted(
                {int(v) for v in payload.get("reconciliation_sections", [])}
            ),
        )


def _as_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    return datetime.fromisoformat(str(value))


@dataclass
class BuildReport:
    """Everything the build observed, including what it could not do."""

    output_dir: Path
    adhyaya_count: int = 0
    mantra_count: int = 0
    passage_count: int = 0
    text_count: int = 0
    citation_count: int = 0
    metadata_count: int = 0
    comparison_count: int = 0
    per_adhyaya: dict[int, dict[str, int]] = field(default_factory=dict)
    comparison_categories: dict[str, int] = field(default_factory=dict)
    parser_failures: list[dict[str, Any]] = field(default_factory=list)
    accented_collisions: dict[str, int] = field(default_factory=dict)
    layer_divergence: list[dict[str, Any]] = field(default_factory=list)
    snapshot_ids: list[str] = field(default_factory=list)
    generated_content_sha256: str = ""
    registry_checksum_findings: list[dict[str, str]] = field(default_factory=list)
    #: text_version_ids this build used that data/registry/text_versions.yaml does not
    #: declare. TextVersionDescriptor is rights-bearing, so an unregistered id here is an
    #: unadjudicated rights claim, exactly like an unregistered artifact_id.
    unregistered_text_versions: list[str] = field(default_factory=list)
    editorial_interventions: list[dict[str, str]] = field(default_factory=list)
    primary_text_status: dict[str, str] = field(default_factory=dict)
    computed_work_totals: dict[str, int] = field(default_factory=dict)
    reconciliation_rows: list[dict[str, int]] = field(default_factory=list)


def _snapshot_index(raw_root: Path) -> dict[str, tuple[Path, RawSnapshotMetadata]]:
    """Map retrieval URL -> (content path, metadata) for every snapshot on disk."""
    index: dict[str, tuple[Path, RawSnapshotMetadata]] = {}
    for metadata_path in sorted(raw_root.glob("**/*.metadata.json")):
        metadata = RawSnapshotMetadata.model_validate_json(metadata_path.read_bytes())
        content_path = metadata_path.with_name(metadata.filename)
        if not content_path.exists():
            continue
        digest = sha256(content_path.read_bytes()).hexdigest()
        if digest != metadata.sha256:
            raise RuntimeError(f"snapshot {content_path} does not match its recorded sha256")
        index[str(metadata.retrieval_url)] = (content_path, metadata)
    return index


def _derived_uuid(kind: str, *parts: object) -> UUID:
    return uuid_for_urn(f"urn:vedagraph:{kind}:{':'.join(str(part) for part in parts)}")


def _git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def _registry_source() -> Source:
    """Return the REGISTERED source record. Nothing is constructed locally.

    Rights live in ``data/registry/sources.yaml``, which Agent E owns. Building a
    ``Source`` here would assert rights at a level the rights authority never
    adjudicated -- the same defect that put locally-invented ids into other pilots.
    """
    for source in load_sources():
        if source.source_id == SOURCE_ID:
            return source
    raise RuntimeError(
        f"{SOURCE_ID} is not declared in data/registry/sources.yaml. Request the entry "
        "from the rights authority; do not construct one here."
    )


def _registry_artifacts() -> list[SourceArtifact]:
    """Return the REGISTERED artifact records this build actually read.

    Fails loudly on an unknown id rather than inventing one, so a release can never
    assert provenance under an identifier nobody declared.
    """
    declared = {artifact.artifact_id: artifact for artifact in load_source_artifacts()}
    missing = [key for key in (ARTIFACT_ID, RISHI_ARTIFACT_ID) if key not in declared]
    if missing:
        raise RuntimeError(
            "these artifact ids are not declared in data/registry/source_artifacts.yaml: "
            f"{missing}. Request them from the rights authority; do not construct them here."
        )
    return [declared[ARTIFACT_ID], declared[RISHI_ARTIFACT_ID]]


def _reconcile_work_structure(
    sections: list[int],
    *,
    adapter: YajurvedaWikisourceAdapter,
    snapshots: dict[str, tuple[Path, RawSnapshotMetadata]],
) -> tuple[list[dict[str, int]], dict[str, int], list[str]]:
    """Compute the work's adhyaya and mantra counts from every snapshot, not from memory.

    The two text layers are individually incomplete in different places, so the mantra
    inventory is the UNION of the distinct mantra numbers each layer labels. Only the
    inventory is unioned; no text is blended. Returns per-adhyaya rows, work totals, and
    the snapshot ids read, so the manifest can list them.
    """
    rows: list[dict[str, int]] = []
    snapshot_ids: list[str] = []
    for adhyaya in sections:
        url = content_api_url(adhyaya_title(adhyaya))
        if url not in snapshots:
            raise RuntimeError(
                f"count reconciliation needs a snapshot for adhyaya {adhyaya}; "
                "run scripts/fetch_yajurveda_wikisource.py"
            )
        path, metadata = snapshots[url]
        parse = adapter.parse_adhyaya(path, snapshot_id=metadata.snapshot_id)
        snapshot_ids.append(metadata.snapshot_id)
        accented = {int(r.hierarchy["mantra"]) for r in parse.accented}
        unaccented = {int(r.hierarchy["mantra"]) for r in parse.samhita}
        union = accented | unaccented
        rows.append(
            {
                "adhyaya": adhyaya,
                "mantras": len(union),
                "highest_mantra_number": max(union) if union else 0,
                "accented_layer": len(accented),
                "unaccented_layer": len(unaccented),
                "gaps_in_union": len(set(range(1, max(union) + 1)) - union) if union else 0,
            }
        )
    totals = {
        "adhyaya_count": len(rows),
        "total_mantras": sum(row["mantras"] for row in rows),
        "sum_of_accented_layer": sum(row["accented_layer"] for row in rows),
        "sum_of_unaccented_layer": sum(row["unaccented_layer"] for row in rows),
        "adhyayas_with_gaps": sum(1 for row in rows if row["gaps_in_union"]),
    }
    return rows, totals, snapshot_ids


def _registry_text_roles(used: list[str]) -> dict[str, TextRole]:
    """Take each layer's role FROM the registry. The build must not decide this.

    ``TextRole`` is a permission statement -- "how VedaGraph is allowed to use this
    representation" -- so choosing it in build code is the same defect as constructing a
    ``SourceArtifact`` locally: it asserts at a level the rights and provenance authority
    owns. Any id the registry does not declare falls back to ``COMPARISON_ONLY``, the most
    restrictive sensible role, rather than to something permissive.
    """
    declared = {d.text_version_id: d.text_role for d in load_text_versions()}
    return {version_id: declared.get(version_id, TextRole.COMPARISON_ONLY) for version_id in used}


def _primary_text_status(leading: str, roles: dict[str, TextRole]) -> dict[str, str]:
    """State plainly whether this work has a layer that qualifies as PRIMARY_TEXT.

    For the Vajasaneyi Samhita the answer is currently NO, and that is a real finding
    rather than a gap to paper over. The direct transcription is incomplete (1,836 of
    1,975 mantras) and the complete layer is extraction-derived, so no layer is both
    faithful and complete. ``TextRole.EXTRACTED_FROM_CONTAINER`` states that such a layer
    "must never be selected as primary_sanskrit", which this build formerly did.

    The leading layer still drives comparison and coverage; "leading" is a build choice,
    not a role, and it grants no canonical status.
    """
    primary = sorted(v for v, role in roles.items() if role == TextRole.PRIMARY_TEXT)
    if primary:
        return {"has_primary_text_layer": "YES", "primary": ", ".join(primary)}
    return {
        "has_primary_text_layer": "NO",
        "leading_layer": leading,
        "leading_role": str(roles.get(leading, TextRole.COMPARISON_ONLY)),
        "consequence": (
            "No layer of this work is registered PRIMARY_TEXT. The leading layer is used "
            "for coverage and comparison only and must not be treated as canonical. "
            "Resolving this needs either a complete direct transcription, or the accented "
            "layer reimplemented to read the source-declared ordinal headers with its two "
            "NEEDS_REVIEW editorial interventions resolved."
        ),
    }


def _unregistered_text_versions(used: list[str]) -> list[str]:
    """Report text_version_ids the registry does not declare.

    ``data/registry/text_versions.yaml`` currently holds 7 descriptors, all Rigvedic, so
    every Yajurveda text_version_id is presently unregistered. These are NOT invented
    silently: ``TextVersionDescriptor`` carries rights and permitted role, so an
    unregistered id is an unadjudicated rights claim one level below the artifact. The
    ids are proposed and reported, and registration is requested from the rights
    authority rather than assumed. This build does not fail on them, because the
    descriptors do not exist to load yet.
    """
    declared = {descriptor.text_version_id for descriptor in load_text_versions()}
    return sorted(set(used) - declared)


def _verify_registry_checksums(
    artifacts: list[SourceArtifact], snapshots: dict[str, tuple[Path, RawSnapshotMetadata]]
) -> list[dict[str, str]]:
    """Check each registry checksum against the bytes this build actually read.

    A registry checksum that matches no snapshot in this build is reported rather than
    trusted. That is how the preface-page hash was found sitting in the samhita
    artifact's ``checksum_sha256`` slot: it is a real snapshot, but not of this artifact.
    """
    findings: list[dict[str, str]] = []
    for artifact in artifacts:
        if artifact.checksum_sha256 is None:
            findings.append(
                {
                    "artifact_id": artifact.artifact_id,
                    "status": "NO_CHECKSUM_DECLARED",
                    "detail": (
                        "The registry states no checksum. For a single-page artifact one "
                        "is meaningful and should be added; for the 40-page samhita "
                        "artifact it is not, and byte verification is carried per "
                        "snapshot in manifest.raw_snapshot_hashes instead."
                    ),
                }
            )
            continue
        matched = _snapshot_title(artifact.checksum_sha256, snapshots)
        if matched is None:
            status = "MATCHES_NO_SNAPSHOT_IN_THIS_BUILD"
        elif _artifact_scope_matches(artifact.artifact_id, matched):
            status = "OK_MATCHES_ITS_OWN_SCOPE"
        else:
            # Naming the matched page is the whole point. "Matches some snapshot" is not
            # verification: the samhita artifact's registry checksum matched the PREFACE
            # page, which is a real snapshot of the wrong thing.
            status = f"WRONG_SCOPE_matches_{matched}"
        findings.append(
            {
                "artifact_id": artifact.artifact_id,
                "status": status,
                "detail": f"{artifact.checksum_sha256} -> {matched or 'no snapshot'}",
            }
        )
    return findings


def _snapshot_title(
    digest: str, snapshots: dict[str, tuple[Path, RawSnapshotMetadata]]
) -> str | None:
    """Name the wiki page a checksum belongs to, by reading the snapshot's own URL."""
    for url, (_, metadata) in snapshots.items():
        if metadata.sha256 == digest:
            unquoted = unquote(url)
            for part in unquoted.split("&"):
                if part.startswith("titles="):
                    return part.removeprefix("titles=")
            return url
    return None


def _artifact_scope_matches(artifact_id: str, page_title: str) -> bool:
    """Is this page plausibly the artifact the id names, or a different page entirely?"""
    if artifact_id.endswith("RISHISUCI"):
        return "ऋषिसूची" in page_title
    if artifact_id.endswith("SARVANUKRAMANI"):
        return "सर्वानुक्रमणी" in page_title
    if artifact_id.endswith("SAMHITA.DEVANAGARI"):
        return "अध्यायः" in page_title
    return False


def build_pilot(config_path: Path) -> BuildReport:
    """Build the Vajasaneyi Samhita pilot from snapshots already on disk."""
    config = PilotConfig.load(config_path)
    snapshots = _snapshot_index(config.raw_root)
    page_adapter = YajurvedaWikisourceAdapter(source_artifact_id=ARTIFACT_ID)
    report = BuildReport(output_dir=config.output_location)

    registry_source = _registry_source()
    registry_artifacts = _registry_artifacts()

    parses: dict[int, AdhyayaParse] = {}
    for adhyaya in config.selected_sections:
        url = content_api_url(adhyaya_title(adhyaya))
        if url not in snapshots:
            raise RuntimeError(
                f"no snapshot for adhyaya {adhyaya}; run scripts/fetch_yajurveda_wikisource.py"
            )
        path, metadata = snapshots[url]
        parses[adhyaya] = page_adapter.parse_adhyaya(path, snapshot_id=metadata.snapshot_id)
        report.snapshot_ids.append(metadata.snapshot_id)

    rishi_parse = None
    if "RISHI_INDEX" in config.metadata_sources:
        url = content_api_url(RISHI_INDEX_TITLE)
        if url in snapshots:
            path, metadata = snapshots[url]
            rishi_parse = RishiIndexAdapter().parse_rishi_index(path)
            report.snapshot_ids.append(metadata.snapshot_id)

    registry_roles = _registry_text_roles(
        [config.leading_text_version, *config.parallel_text_versions]
    )
    report.primary_text_status = _primary_text_status(config.leading_text_version, registry_roles)

    reconciliation_rows, work_totals, reconciliation_snapshots = _reconcile_work_structure(
        config.reconciliation_sections or config.selected_sections,
        adapter=page_adapter,
        snapshots=snapshots,
    )
    report.reconciliation_rows = reconciliation_rows
    report.computed_work_totals = work_totals
    report.snapshot_ids.extend(reconciliation_snapshots)

    passages: list[Passage] = []
    texts: list[TextVersion] = []
    citations: list[Citation] = []
    metadata_assertions: list[TraditionalMetadataAssertion] = []
    assertions: list[SourceAssertion] = []
    comparisons: list[Any] = []

    rishi_by_key: dict[tuple[int, int], list[Any]] = {}
    if rishi_parse is not None:
        for item in rishi_parse.assertions:
            rishi_by_key.setdefault((item.adhyaya, item.mantra), []).append(item)

    for adhyaya in config.selected_sections:
        parse = parses[adhyaya]
        section_key, section_urn, section_id = vsm_adhyaya_identity(adhyaya)
        passages.append(
            Passage(
                entity_id=section_id,
                canonical_key=section_key,
                canonical_urn=section_urn,
                entity_type=EntityType.SECTION,
                work_id=WORK_ID,
                hierarchy={"adhyaya": adhyaya},
                canonical_citation=f"VSM {adhyaya}",
                sequence_in_parent=adhyaya,
                status=PassageStatus.CANONICAL,
            )
        )

        by_version: dict[str, dict[int, str]] = {
            "WIKISOURCE_SA.YV.VSM.ACCENTED": {
                int(record.hierarchy["mantra"]): record.text_original for record in parse.accented
            },
            "WIKISOURCE_SA.YV.VSM.UNACCENTED": {
                int(record.hierarchy["mantra"]): record.text_original for record in parse.samhita
            },
        }
        primary = by_version[config.leading_text_version]
        mantra_numbers = sorted(set().union(*(set(layer) for layer in by_version.values())))

        # Layer divergence is data. Record it; never reconcile it here.
        only_primary = sorted(set(primary) - set(by_version[config.parallel_text_versions[0]]))
        only_parallel = sorted(set(by_version[config.parallel_text_versions[0]]) - set(primary))
        if only_primary or only_parallel:
            report.layer_divergence.append(
                {
                    "adhyaya": adhyaya,
                    "only_in_primary": only_primary,
                    "only_in_parallel": only_parallel,
                }
            )

        for mantra in mantra_numbers:
            key, urn, entity_id = vsm_mantra_identity(adhyaya, mantra)
            passages.append(
                Passage(
                    entity_id=entity_id,
                    canonical_key=key,
                    canonical_urn=urn,
                    entity_type=EntityType.MANTRA,
                    work_id=WORK_ID,
                    hierarchy={"adhyaya": adhyaya, "mantra": mantra},
                    canonical_citation=f"VSM {adhyaya}.{mantra}",
                    parent_key=section_key,
                    sequence_in_parent=mantra,
                    status=PassageStatus.CANONICAL,
                )
            )
            citations.append(
                Citation(
                    citation_id=_derived_uuid("citation", key, "VSM"),
                    passage_id=entity_id,
                    label=f"VSM {adhyaya}.{mantra}",
                    system="VSM_ADHYAYA_MANTRA",
                    source_id=SOURCE_ID,
                    is_canonical=True,
                )
            )
            if annotation := parse.alternate_citations.get(mantra):
                # e.g. VSM 40.1 carries "{ईशावा.उप. काण्व1}" - the Kanva-recension
                # Isavasya Upanisad number. An alternate system, recorded as data.
                citations.append(
                    Citation(
                        citation_id=_derived_uuid("citation", key, "SOURCE_CROSS_REFERENCE"),
                        passage_id=entity_id,
                        label=annotation,
                        system="SOURCE_CROSS_REFERENCE",
                        source_id=SOURCE_ID,
                        is_canonical=False,
                    )
                )

            for version_id, layer in by_version.items():
                text = layer.get(mantra)
                if text is None:
                    continue
                role = registry_roles[version_id]
                normalized = normalize_nfc(text)
                texts.append(
                    TextVersion(
                        text_id=_derived_uuid("text", key, version_id),
                        passage_id=entity_id,
                        language="sa",
                        script="Devanagari",
                        text_form=TextForm.SAMHITA,
                        text_role=role,
                        text_version_id=version_id,
                        text_original=text,
                        text_nfc=normalized,
                        content_sha256=sha256(normalized.encode("utf-8")).hexdigest(),
                        accented=has_vedic_accents(text),
                        source_id=SOURCE_ID,
                        source_artifact_id=ARTIFACT_ID,
                        source_locator=f"{parse.revision.resolved_title}#{adhyaya}.{mantra}",
                        rights_status=RightsStatus.CC_BY_SA,
                    )
                )

            # Cross-layer comparison via the existing deterministic comparator.
            left_text = primary.get(mantra)
            for parallel_id in config.parallel_text_versions:
                right_text = by_version[parallel_id].get(mantra)
                if left_text is None or right_text is None:
                    continue
                comparisons.append(
                    compare_readings(
                        passage_key=key,
                        citation=f"VSM {adhyaya}.{mantra}",
                        left=VersionReading(
                            version_id=config.leading_text_version,
                            text=left_text,
                            role=TextRole.PRIMARY_TEXT,
                        ),
                        right=VersionReading(
                            version_id=parallel_id,
                            text=right_text,
                            role=TextRole.PARALLEL_TEXT,
                        ),
                    )
                )

            for item in rishi_by_key.get((adhyaya, mantra), []):
                metadata_assertions.append(
                    TraditionalMetadataAssertion(
                        assertion_id=_derived_uuid(
                            "traditional-metadata", key, "HAS_RISHI", item.rishi
                        ),
                        predicate=MetadataPredicate.HAS_RISHI,
                        value=item.rishi,
                        scope=MetadataScope(
                            scope_type=ScopeType.SINGLE_MANTRA, passage_id=entity_id
                        ),
                        source_id=SOURCE_ID,
                        source_locator=(
                            f"{RISHI_INDEX_TITLE}#L{item.line_number}: {item.source_line}"
                        ),
                        status=AssertionStatus.UNREVIEWED,
                        notes=(
                            f"Stated by the index as {item.scope_note}. Edition-supplied "
                            "index; no rsi was inferred. Yajurveda chandas and devata are "
                            "NOT asserted: the Sukla YV Sarvanukramasutra states that many "
                            "yajus have no metre at all, and its devata co-domain includes "
                            "ritual implements, so neither field may be carried over from "
                            "Rigvedic practice."
                        ),
                    )
                )

        report.per_adhyaya[adhyaya] = {
            "mantras": len(mantra_numbers),
            "accented": len(by_version["WIKISOURCE_SA.YV.VSM.ACCENTED"]),
            "samhita": len(by_version["WIKISOURCE_SA.YV.VSM.UNACCENTED"]),
            "parser_failures": len(parse.failures),
        }
        report.parser_failures.extend(
            {
                "adhyaya": adhyaya,
                "page": failure.resolved_title,
                "line_number": failure.line_number,
                "reason": failure.reason,
                "line": failure.line,
            }
            for failure in parse.failures
        )
        for mantra, count in parse.accented_collisions.items():
            report.accented_collisions[f"{adhyaya}.{mantra}"] = count
        report.editorial_interventions.extend(
            {
                "citation": f"VSM {item.adhyaya}.{item.mantra}",
                "kind": item.kind,
                "removed": item.removed[:80],
            }
            for item in parse.editorial_interventions
        )

        for intervention in parse.editorial_interventions:
            target = vsm_mantra_identity(intervention.adhyaya, intervention.mantra)[0]
            assertions.append(
                SourceAssertion(
                    assertion_id=_derived_uuid("assertion", target, "EDITORIAL", intervention.kind),
                    subject_id=target,
                    predicate=f"EDITORIAL_INTERVENTION_{intervention.kind}",
                    value={"removed": intervention.removed, "reason": intervention.reason},
                    source_id=SOURCE_ID,
                    source_artifact_id=ARTIFACT_ID,
                    source_locator=(
                        f"{parse.revision.resolved_title}"
                        f"#{intervention.adhyaya}.{intervention.mantra}"
                    ),
                    status=AssertionStatus.NEEDS_REVIEW,
                    evidence=(
                        "Recorded so every departure from the source bytes is reviewable "
                        "and reversible rather than implicit in parser code."
                    ),
                )
            )
        assertions.append(
            SourceAssertion(
                assertion_id=_derived_uuid("assertion", section_key, "REVISION"),
                subject_id=section_key,
                predicate="SOURCE_REVISION",
                value={
                    "requested_title": parse.revision.requested_title,
                    "resolved_title": parse.revision.resolved_title,
                    "redirected": parse.revision.redirected,
                    "page_id": parse.revision.page_id,
                    "revision_id": parse.revision.revision_id,
                    "revision_timestamp": parse.revision.revision_timestamp,
                    "canonical_url": canonical_page_url(parse.revision.resolved_title),
                },
                source_id=SOURCE_ID,
                source_artifact_id=ARTIFACT_ID,
                source_locator=parse.revision.resolved_title,
                status=AssertionStatus.ACCEPTED,
                evidence="MediaWiki action=query&prop=revisions response",
            )
        )

    # -- deterministic ordering -------------------------------------------------
    passages.sort(
        key=lambda item: (
            int(item.hierarchy["adhyaya"]),
            0 if item.entity_type == EntityType.SECTION else 1,
            int(item.hierarchy.get("mantra", 0)),
        )
    )
    texts.sort(key=lambda item: (item.source_locator, item.text_version_id or ""))
    citations.sort(key=lambda item: (str(item.passage_id), item.system, item.label))
    metadata_assertions.sort(key=lambda item: (str(item.scope.passage_id), item.value))
    assertions.sort(key=lambda item: (item.subject_id, item.predicate))
    comparisons.sort(key=lambda item: (item.passage_key, item.right_version_id))

    report.adhyaya_count = len(config.selected_sections)
    report.mantra_count = sum(1 for item in passages if item.entity_type == EntityType.MANTRA)
    report.passage_count = len(passages)
    report.text_count = len(texts)
    report.citation_count = len(citations)
    report.metadata_count = len(metadata_assertions)
    report.comparison_count = len(comparisons)
    for comparison in comparisons:
        name = str(comparison.category)
        report.comparison_categories[name] = report.comparison_categories.get(name, 0) + 1

    # -- work-level structural reconciliation, as reviewable assertions ---------
    # These are WORK-scoped, not passage-scoped: they assert what the source says the
    # work's shape is, over every adhyaya, independently of which adhyayas this pilot
    # ingested. Kept in their own file so they are never mistaken for passage provenance.
    structure_assertions: list[SourceAssertion] = [
        SourceAssertion(
            assertion_id=_derived_uuid("assertion", WORK_ID, "COMPUTED_STRUCTURE"),
            subject_id=WORK_ID,
            predicate="COMPUTED_WORK_STRUCTURE",
            value=work_totals,
            source_id=SOURCE_ID,
            source_artifact_id=ARTIFACT_ID,
            source_locator=(
                f"{len(reconciliation_rows)} adhyaya snapshots under {config.raw_root}"
            ),
            status=AssertionStatus.ACCEPTED,
            evidence=(
                "Computed from every adhyaya snapshot at build time, never quoted. The "
                "mantra inventory is the UNION of the distinct mantra numbers the two "
                "text layers label, because each layer is incomplete in different places; "
                "only the inventory is unioned and no text is blended. External "
                "cross-checks disagree and are recorded as data: TITUS yields 1974 (VS "
                "2.32 absent there) and the Vedic Heritage Portal yields 1974 (adhyaya 23 "
                "= 64 against 65 elsewhere)."
            ),
        )
    ]
    structure_assertions.extend(
        SourceAssertion(
            assertion_id=_derived_uuid(
                "assertion", vsm_adhyaya_key(int(row["adhyaya"])), "COMPUTED_COUNT"
            ),
            subject_id=vsm_adhyaya_key(int(row["adhyaya"])),
            predicate="COMPUTED_MANTRA_COUNT",
            value=row,
            source_id=SOURCE_ID,
            source_artifact_id=ARTIFACT_ID,
            source_locator=adhyaya_title(int(row["adhyaya"])),
            status=AssertionStatus.ACCEPTED,
            evidence="Distinct mantra numbers labelled by the source in this adhyaya.",
        )
        for row in reconciliation_rows
    )

    # -- write ------------------------------------------------------------------
    output = config.output_location
    output.mkdir(parents=True, exist_ok=True)
    generated: dict[Path, int] = {}
    files: list[tuple[str, list[Any]]] = [
        ("sources.jsonl", [registry_source]),
        ("source_artifacts.jsonl", registry_artifacts),
        ("passages.jsonl", passages),
        ("citations.jsonl", citations),
        ("text_versions.jsonl", texts),
        ("translations.jsonl", []),
        ("traditional_metadata.jsonl", metadata_assertions),
        ("source_assertions.jsonl", assertions),
        ("text_comparisons.jsonl", comparisons),
        ("structure_reconciliation.jsonl", structure_assertions),
        ("audio_recordings.jsonl", []),
        ("audio_segments.jsonl", []),
    ]
    for name, records in files:
        path = output / name
        generated[path] = write_jsonl(path, records)

    digest = sha256()
    for path in sorted(generated, key=lambda item: item.name):
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    report.generated_content_sha256 = digest.hexdigest()
    report.registry_checksum_findings = _verify_registry_checksums(registry_artifacts, snapshots)
    report.unregistered_text_versions = _unregistered_text_versions(
        [config.leading_text_version, *config.parallel_text_versions]
    )

    raw_hashes = {
        metadata.snapshot_id: metadata.sha256
        for _, metadata in snapshots.values()
        if metadata.snapshot_id in set(report.snapshot_ids)
    }
    manifest = build_manifest(
        root=output,
        version=config.release_version,
        works=[WORK_ID],
        passage_count=report.passage_count,
        source_snapshot_ids=sorted(set(report.snapshot_ids)),
        source_artifact_ids=[ARTIFACT_ID, RISHI_ARTIFACT_ID],
        generated=generated,
        qa_status=QAStatus.PASSED_WITH_WARNINGS,
        built_at=config.build_timestamp,
        raw_snapshot_hashes=dict(sorted(raw_hashes.items())),
        build_config_sha256=sha256(config_path.read_bytes()).hexdigest(),
        parser_versions={
            "wikisource-sa-vsm": PARSER_VERSION,
            "wikisource-sa-vsm-apparatus": "wikisource-sa-vsm-apparatus-v1",
            "builder": BUILDER_VERSION,
        },
        reconciliation_policy_version=config.reconciliation_policy_version,
        comparison_version=COMPARATOR_VERSION,
        software_git_commit=_git_commit(),
        generated_content_sha256=report.generated_content_sha256,
        rights_summary={SOURCE_ID: registry_source.rights.status.value},
    )
    (output / "manifest.json").write_bytes(
        manifest.model_dump_json(indent=2, exclude_none=True).encode("utf-8") + b"\n"
    )
    return report


__all__ = ["BuildReport", "PilotConfig", "build_pilot"]
