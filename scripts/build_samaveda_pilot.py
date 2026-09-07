"""Build the Samaveda Kauthuma pilot corpus from a pinned GRETIL snapshot.

Deterministic by construction: the only inputs are the build config, the hash-verified
raw snapshot, and the registries. Nothing is fetched, nothing is timestamped from the
clock, and no defect is repaired. Run it twice and the JSONL must be byte-identical.

    ./.venv/Scripts/python.exe scripts/build_samaveda_pilot.py data/builds/samaveda_pilot_v1.yaml
"""

from __future__ import annotations

import sys
from collections import defaultdict
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml

from vedagraph.identity import (
    sv_container_identity,
    sv_mantra_identity,
    uuid_for_urn,
)
from vedagraph.ingest.adapters.samaveda_gretil import (
    NATIVE_LABELS,
    PARSER_VERSION,
    SamavedaGRETILAdapter,
    SamavedaVerse,
)
from vedagraph.models import (
    Citation,
    Passage,
    Source,
    SourceArtifact,
    SourceAssertion,
    TextVersion,
    Work,
)
from vedagraph.models.enums import (
    AssertionStatus,
    EntityType,
    QAStatus,
    RightsStatus,
    TextForm,
    TextRole,
)
from vedagraph.normalize import has_vedic_accents, normalize_nfc
from vedagraph.storage.jsonl import write_jsonl
from vedagraph.storage.manifest import build_manifest, file_sha256

# Container level names, outermost first, matching identity.SV_CONTAINER_LEVELS.
CONTAINER_LEVELS = ("arcika", "prapathaka", "ardha", "dasati")
# Bookkeeping label for the top of the passage tree. Never written to a record: a
# depth-1 passage carries parent_key None, as the Rigveda's Mandalas do.
_ROOT = "\x00ROOT"
# Passage gained native_labels/structural_path during the four-Veda work; populate them
# only if this build is running against a model version that has them.
PASSAGE_FIELDS = set(Passage.model_fields)


def _load_config(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a mapping")
    return payload


def _verify_snapshot(primary: dict[str, Any]) -> Path:
    snapshot_path = Path(primary["snapshot_path"])
    if not snapshot_path.exists():
        raise FileNotFoundError(snapshot_path)
    actual = file_sha256(snapshot_path)
    if actual != primary["snapshot_sha256"]:
        raise ValueError(
            f"snapshot hash mismatch for {snapshot_path}: "
            f"expected {primary['snapshot_sha256']}, got {actual}"
        )
    return snapshot_path


def _passage(**kwargs: Any) -> Passage:
    """Construct a Passage, dropping fields this model version does not declare."""
    return Passage(**{key: value for key, value in kwargs.items() if key in PASSAGE_FIELDS})


def _container_chain(verse: SamavedaVerse) -> list[tuple[str, tuple[int, ...]]]:
    """The containers that actually exist for one verse, outermost first.

    A level whose value the source writes as ``0`` does not exist in that arcika and
    gets no container node; the verse's parent is therefore the deepest level that does
    exist. This is what variable depth means concretely.
    """
    chain: list[tuple[str, tuple[int, ...]]] = []
    coordinates = (verse.arcika, verse.prapathaka, verse.ardha, verse.dasati)
    for depth, level in enumerate(CONTAINER_LEVELS, start=1):
        if coordinates[depth - 1] == 0:
            continue
        chain.append((level, coordinates[:depth]))
    return chain


def _container_identity(coordinates: tuple[int, ...]) -> tuple[str, str, Any]:
    """Identity for a container, passing 0 through for source-absent middle levels."""
    padded = list(coordinates) + [None] * (4 - len(coordinates))
    return sv_container_identity(*padded)


def build(config_path: Path) -> dict[str, Any]:
    config = _load_config(config_path)
    primary = config["primary_sanskrit"]
    snapshot_path = _verify_snapshot(primary)
    snapshot_id = primary["snapshot_id"]
    work_id = config["work_id"]
    rights = RightsStatus(primary["rights_status"])
    output_root = Path(config["output_location"])

    adapter = SamavedaGRETILAdapter(
        source_artifact_id=primary["artifact_id"],
        text_version_id=primary["text_version_id"],
    )
    parsed = adapter.parse_structure(snapshot_path)

    # Sequence-in-parent is computed over the WHOLE corpus, not over the sample, so a
    # sampled build reports true source positions and its gaps are honest.
    #
    # A depth-1 container (an arcika) has parent_key None, matching the Rigveda's
    # depth-1 Mandalas. The work is not a Passage, so pointing at its work_id would
    # dangle. ``_ROOT`` is only a bookkeeping label for counting top-level siblings and
    # is never written to a record.
    sequence: dict[tuple[str, str], int] = {}
    seen: dict[str, int] = defaultdict(int)
    for verse in parsed.verses:
        chain = _container_chain(verse)
        for index, (_, coordinates) in enumerate(chain):
            key = _container_identity(coordinates)[0]
            parent = _container_identity(chain[index - 1][1])[0] if index else _ROOT
            if (parent, key) not in sequence:
                seen[parent] += 1
                sequence[(parent, key)] = seen[parent]
        if verse.has_canonical_identity:
            parent = _container_identity(chain[-1][1])[0] if chain else _ROOT
            key = sv_mantra_identity(*verse.coordinates)[0]
            if (parent, key) not in sequence:
                seen[parent] += 1
                sequence[(parent, key)] = seen[parent]

    selected_units = {tuple(entry["unit"]) for entry in config["sample_units"]}
    region_of = {tuple(entry["unit"]): entry["region"] for entry in config["sample_units"]}

    passages: dict[str, Passage] = {}
    text_versions: list[TextVersion] = []
    citations: list[Citation] = []
    assertions: list[SourceAssertion] = []
    rejected: list[SamavedaVerse] = []
    sampled: list[SamavedaVerse] = []

    for verse in parsed.verses:
        if verse.unit not in selected_units:
            continue
        sampled.append(verse)
        if not verse.has_canonical_identity:
            rejected.append(verse)
            assertions.append(
                SourceAssertion(
                    assertion_id=uuid_for_urn(
                        f"urn:vedagraph:assertion:sv-identity-refused:{verse.verse_key}"
                    ),
                    subject_id=verse.verse_key,
                    predicate="CANONICAL_IDENTITY_REFUSED",
                    value={
                        "reason": "verse index is 0; sv_mantra_identity fails closed",
                        "coordinates": list(verse.coordinates),
                        "source_lines": [line.raw_line for line in verse.lines],
                    },
                    source_id=adapter.source_id,
                    source_artifact_id=adapter.source_artifact_id,
                    source_locator=verse.citation,
                    status=AssertionStatus.NEEDS_REVIEW,
                    evidence="; ".join(line.raw_line for line in verse.lines),
                )
            )
            continue

        chain = _container_chain(verse)
        for index, (_level, coordinates) in enumerate(chain):
            key, urn, entity_id = _container_identity(coordinates)
            if key in passages:
                continue
            parent = _container_identity(chain[index - 1][1])[0] if index else _ROOT
            passages[key] = _passage(
                entity_id=entity_id,
                canonical_key=key,
                canonical_urn=urn,
                entity_type=EntityType.STRUCTURAL_CONTAINER
                if hasattr(EntityType, "STRUCTURAL_CONTAINER")
                else EntityType.SECTION,
                work_id=work_id,
                hierarchy=dict(zip(CONTAINER_LEVELS, coordinates, strict=False)),
                canonical_citation="SV " + ".".join(str(value) for value in coordinates),
                parent_key=None if parent == _ROOT else parent,
                sequence_in_parent=sequence[(parent, key)],
                native_labels=list(NATIVE_LABELS[: len(coordinates)]),
                structural_path=list(verse.structural_path[: len(coordinates)]),
            )

        key, urn, entity_id = sv_mantra_identity(*verse.coordinates)
        parent = _container_identity(chain[-1][1])[0] if chain else _ROOT
        passages[key] = _passage(
            entity_id=entity_id,
            canonical_key=key,
            canonical_urn=urn,
            entity_type=EntityType.MANTRA,
            work_id=work_id,
            hierarchy=verse.hierarchy,
            canonical_citation=verse.citation,
            parent_key=None if parent == _ROOT else parent,
            sequence_in_parent=sequence[(parent, key)],
            native_labels=list(NATIVE_LABELS),
            structural_path=verse.structural_path,
        )

        text = adapter.verse_text(verse)
        text_versions.append(
            TextVersion(
                text_id=uuid_for_urn(f"{urn}:text:{primary['text_version_id']}"),
                passage_id=entity_id,
                language="sa",
                script=primary["script"],
                text_form=TextForm.SAMHITA,
                text_role=TextRole.PRIMARY_TEXT,
                text_version_id=primary["text_version_id"],
                text_original=text,
                text_nfc=normalize_nfc(text),
                accented=has_vedic_accents(text),
                transliteration_scheme=primary["transliteration_scheme"],
                source_id=adapter.source_id,
                source_artifact_id=adapter.source_artifact_id,
                source_locator=verse.citation,
                content_sha256=sha256(text.encode("utf-8")).hexdigest(),
                rights_status=rights,
            )
        )

        citations.append(
            Citation(
                citation_id=uuid_for_urn(f"{urn}:citation:SV_KAUTHUMA_STRUCTURAL"),
                passage_id=entity_id,
                label=verse.citation,
                system="SV_KAUTHUMA_STRUCTURAL",
                source_id=adapter.source_id,
                is_canonical=True,
            )
        )
        for running in sorted(set(verse.running_numbers)):
            citations.append(
                Citation(
                    citation_id=uuid_for_urn(f"{urn}:citation:SV_RUNNING_VERSE:{running}"),
                    passage_id=entity_id,
                    label=str(running),
                    system="SV_RUNNING_VERSE",
                    source_id=adapter.source_id,
                    is_canonical=False,
                )
            )
        for line in verse.lines:
            assertions.append(
                SourceAssertion(
                    assertion_id=uuid_for_urn(f"{urn}:source-line:{line.line_label}"),
                    subject_id=key,
                    predicate="SOURCE_LINE_VERBATIM",
                    value={
                        "line_label": line.line_label,
                        "label_notation": line.label_notation,
                        "raw_line": line.raw_line,
                    },
                    source_id=adapter.source_id,
                    source_artifact_id=adapter.source_artifact_id,
                    source_locator=f"{verse.citation}{line.line_label}",
                    status=AssertionStatus.ACCEPTED,
                    evidence=line.raw_line,
                )
            )

    # Parse defects that fall inside the sampled units, recorded not repaired.
    sampled_keys = {verse.verse_key for verse in sampled}
    for index, defect in enumerate(parsed.defects):
        if defect.verse_key is not None and defect.verse_key not in sampled_keys:
            continue
        assertions.append(
            SourceAssertion(
                assertion_id=uuid_for_urn(
                    f"urn:vedagraph:assertion:sv-parse-defect:{index}:{defect.defect_code}"
                ),
                subject_id=defect.verse_key or f"paragraph:{defect.paragraph_index}",
                predicate="PARSE_DEFECT",
                value={
                    "defect_code": defect.defect_code,
                    "detail": defect.detail,
                    "paragraph_index": defect.paragraph_index,
                },
                source_id=adapter.source_id,
                source_artifact_id=adapter.source_artifact_id,
                source_locator=defect.verse_key or f"paragraph {defect.paragraph_index}",
                status=AssertionStatus.NEEDS_REVIEW,
                evidence=defect.raw_line,
            )
        )

    # The structural facts this build computed, as provenanced assertions rather than as
    # a silent edit to the registry (which this agent does not own).
    stated = config["source_stated_counts"]
    assertions.append(
        SourceAssertion(
            assertion_id=uuid_for_urn("urn:vedagraph:assertion:sv-computed-structure:v1"),
            subject_id=work_id,
            predicate="COMPUTED_STRUCTURE",
            value={
                "declared_reference_system": parsed.declared_reference_system,
                "source_stated_total_verses": stated["terminal_running_verse_number"],
                "computed_distinct_verse_keys": len(parsed.verses),
                "computed_verse_lines": parsed.verse_line_count,
                "label_notation_counts": parsed.notation_counts,
                "verses_per_arcika": {
                    str(arcika): sum(1 for v in parsed.verses if v.arcika == arcika)
                    for arcika in sorted({v.arcika for v in parsed.verses})
                },
                "unreconciled_verse_count": stated["terminal_running_verse_number"]
                - len(parsed.verses),
                "defect_counts": {
                    code: sum(1 for d in parsed.defects if d.defect_code == code)
                    for code in sorted({d.defect_code for d in parsed.defects})
                },
                "covers_gana_collections": False,
            },
            source_id=adapter.source_id,
            source_artifact_id=adapter.source_artifact_id,
            source_locator="whole artifact",
            status=AssertionStatus.UNREVIEWED,
            evidence=parsed.declared_reference_system,
        )
    )

    works = [work for work in _load_works() if work.work_id == work_id]

    # Every source_id and artifact_id a record in this build points at must resolve
    # inside the build itself, or the provenance pointer dangles. These are read from
    # the registries (which Agent E owns) and never synthesised here.
    referenced_artifacts = {primary["artifact_id"]}
    artifacts = [
        artifact
        for artifact in _load_source_artifacts()
        if artifact.artifact_id in referenced_artifacts
    ]
    missing_artifacts = referenced_artifacts - {artifact.artifact_id for artifact in artifacts}
    if missing_artifacts:
        raise ValueError(f"artifacts not in the registry: {sorted(missing_artifacts)}")

    referenced_sources = {adapter.source_id} | {artifact.source_id for artifact in artifacts}
    sources = [source for source in _load_sources() if source.source_id in referenced_sources]
    missing_sources = referenced_sources - {source.source_id for source in sources}
    if missing_sources:
        raise ValueError(f"sources not in the registry: {sorted(missing_sources)}")

    ordered_passages = sorted(passages.values(), key=lambda item: item.canonical_key)
    generated: dict[Path, int] = {}
    output_root.mkdir(parents=True, exist_ok=True)
    for name, records in (
        ("works.jsonl", works),
        ("sources.jsonl", sorted(sources, key=lambda r: r.source_id)),
        ("source_artifacts.jsonl", sorted(artifacts, key=lambda r: r.artifact_id)),
        ("passages.jsonl", ordered_passages),
        ("text_versions.jsonl", sorted(text_versions, key=lambda r: r.source_locator)),
        (
            "citations.jsonl",
            sorted(citations, key=lambda r: (str(r.passage_id), r.system, r.label)),
        ),
        (
            "source_assertions.jsonl",
            sorted(assertions, key=lambda r: (r.predicate, r.source_locator, str(r.assertion_id))),
        ),
        ("translations.jsonl", []),
    ):
        path = output_root / name
        generated[path] = write_jsonl(path, records)

    manifest = build_manifest(
        root=output_root,
        version=config["release_version"],
        works=[work_id],
        passage_count=sum(
            1 for passage in ordered_passages if passage.entity_type == EntityType.MANTRA
        ),
        source_snapshot_ids=[snapshot_id],
        generated=generated,
        qa_status=QAStatus.NOT_RUN,
        built_at=datetime.fromisoformat(config["build_timestamp"]),
        source_artifact_ids=[primary["artifact_id"]],
        raw_snapshot_hashes={snapshot_id: primary["snapshot_sha256"]},
        build_config_sha256=file_sha256(config_path),
        parser_versions={adapter.source_id: PARSER_VERSION},
        qa_policy_version=config["qa_policy_version"],
        rights_summary={primary["artifact_id"]: rights.value},
    )
    manifest_path = Path(config["manifest_path"])
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_bytes(
        manifest.model_dump_json(indent=2, exclude_none=True).encode("utf-8") + b"\n"
    )

    mantras = [p for p in ordered_passages if p.entity_type == EntityType.MANTRA]
    return {
        "mantra_passages": len(mantras),
        "container_passages": len(ordered_passages) - len(mantras),
        "text_versions": len(text_versions),
        "citations": len(citations),
        "assertions": len(assertions),
        "identity_refused": len(rejected),
        "regions": sorted({region_of[verse.unit] for verse in sampled}),
        "output_root": str(output_root),
        "manifest_path": str(manifest_path),
    }


def _load_works() -> list[Work]:
    from vedagraph.config.registry import load_works

    return load_works()


def _load_sources() -> list[Source]:
    from vedagraph.config.registry import load_sources

    return load_sources()


def _load_source_artifacts() -> list[SourceArtifact]:
    from vedagraph.config.registry import load_source_artifacts

    return load_source_artifacts()


if __name__ == "__main__":
    summary = build(Path(sys.argv[1]))
    for name, value in summary.items():
        print(f"{name}: {value}")
