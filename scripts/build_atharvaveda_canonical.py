"""Build the Atharvaveda Shaunaka canonical corpus from the 1856 page images.

The Sanskrit released here comes from one place only: two independent visual
readings of the Roth & Whitney 1856 leaves, reconciled by
``scripts/reconcile_atharvaveda_v2.py``. No other edition of the Atharvaveda
is read, compared against, or consulted anywhere in this path. The existing
``atharvaveda_pilot_v1`` build is GRETIL-derived and REFERENCE_ONLY; this
build shares no text with it.

A unit reaches ``text_versions.jsonl`` only if two readers who could not see
each other's work produced the same codepoints. Everything else is carried
as an enumerated backlog record with its leaf and its reason, so that what
is unresolved stays visible instead of being averaged away.

Usage:
    python scripts/build_atharvaveda_canonical.py [--reconciled DIR] [--check]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any, Final
from uuid import UUID, uuid5

import yaml

REPO: Final[Path] = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from vedagraph.identity import (  # noqa: E402
    avs_kanda_identity,
    avs_mantra_identity,
    avs_sukta_identity,
)
from vedagraph.models import Passage, Source, SourceArtifact, TextVersion, Work  # noqa: E402
from vedagraph.models.enums import (  # noqa: E402
    EntityType,
    PassageStatus,
    QAStatus,
    RightsStatus,
    TextForm,
    TextRole,
)
from vedagraph.release import CanonicalRelease, write_release  # noqa: E402

BUILD_ID: Final[str] = "atharvaveda_saunaka_1856_v1"
BUILD_VERSION: Final[str] = "1.0.0-avs-1856.1"
WORK_ID: Final[str] = "VG:WORK:AV:SAU"
SOURCE_ID: Final[str] = "BSB_MDZ"
ARTIFACT_ID: Final[str] = "BSB.AV.SAUNAKA.ROTH_WHITNEY.1856.SCAN"
TEXT_VERSION_ID: Final[str] = "VEDAGRAPH.AVS.ROTH_WHITNEY_1856.TRANSCRIPTION"
PARSER_VERSION: Final[str] = "bsb-1856-devanagari-v2"
BSB_ID: Final[str] = "bsb10219750"
SNAPSHOT_ID: Final[str] = "2026-09-07"
# Fixed, not read from the clock: a build whose manifest changes every run is
# not reproducible and cannot be checked against itself.
BUILD_TIMESTAMP: Final[str] = "2026-09-08T00:00:00Z"

RELEASE_ELIGIBLE: Final[frozenset[str]] = frozenset(
    {"VERIFIED_EXACT", "VERIFIED_WITH_ORTHOGRAPHIC_NOTE"}
)
NAMESPACE: Final[UUID] = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")

RECONCILED_DIR: Final[Path] = (
    REPO / "data" / "transcriptions" / "atharvaveda_bsb_1856" / "v2" / "reconciled"
)
OUT_DIR: Final[Path] = REPO / "data" / "canonical" / BUILD_ID
BACKLOG_PATH: Final[Path] = (
    REPO / "data" / "transcriptions" / "atharvaveda_bsb_1856" / "v2" / "uncertainty_backlog.jsonl"
)
STRUCTURE_PATH: Final[Path] = (
    REPO / "data" / "source_registry" / "atharvaveda_1856_structure_summary.json"
)

# Every edition of the Atharvaveda that may not be used as a correction source.
PROHIBITED_MARKERS: Final[tuple[str, ...]] = (
    "GRETIL",
    "TITUS",
    "VEDAWEB",
    "ORLANDI",
    "SACRED_TEXTS",
)


def derived_uuid(kind: str, *parts: object) -> UUID:
    return uuid5(NAMESPACE, f"{kind}:" + ":".join(str(p) for p in parts))


def _registry(filename: str, family: str, id_field: str, wanted: str) -> dict[str, Any]:
    """One row from the registry, by id. The build never constructs these itself.

    Reading them rather than building them is what makes the registry's pinned
    rights and checksums binding on the release instead of advisory.
    """
    path = REPO / "data" / "registry" / filename
    payload: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    for item in payload[family]:
        if item[id_field] == wanted:
            return dict(item)
    raise SystemExit(f"{wanted} is not registered in {path}")


def registry_work() -> Work:
    return Work.model_validate(_registry("works.yaml", "works", "work_id", WORK_ID))


def registry_source() -> Source:
    return Source.model_validate(_registry("sources.yaml", "sources", "source_id", SOURCE_ID))


def registry_artifact() -> SourceArtifact:
    return SourceArtifact.model_validate(
        _registry("source_artifacts.yaml", "source_artifacts", "artifact_id", ARTIFACT_ID)
    )


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_reconciled(directory: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(directory.glob("leaf_*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def source_locator(row: dict[str, Any]) -> str:
    """Where on the physical source this reading was taken from.

    Every released unit must name its leaf. A Sanskrit record whose locator
    does not resolve to an image on disk is exactly the failure the release
    gate exists to catch, so the locator is built from the canvas index that
    the reader was actually shown.
    """
    page = row.get("printed_page")
    printed = f", printed page {page}" if page is not None else ", unpaginated"
    return f"{BSB_ID} canvas {row['canvas_index']:05d}{printed}"


def build_passages(units: list[dict[str, Any]]) -> tuple[list[Passage], dict[tuple, UUID]]:
    """Containers first, then verses, so no verse can outlive its parent."""
    kandas: dict[int, list[int]] = defaultdict(list)
    for row in units:
        if row["sukta"] not in kandas[row["kanda"]]:
            kandas[row["kanda"]].append(row["sukta"])

    passages: list[Passage] = []
    verse_ids: dict[tuple, UUID] = {}

    for sequence, kanda in enumerate(sorted(kandas), start=1):
        key, urn, entity = avs_kanda_identity(kanda)
        passages.append(
            Passage(
                entity_id=entity,
                canonical_key=key,
                canonical_urn=urn,
                entity_type=EntityType.SECTION,
                work_id=WORK_ID,
                hierarchy={"kanda": kanda},
                canonical_citation=f"AVS {kanda}",
                parent_key=None,
                sequence_in_parent=sequence,
                native_labels=["Kanda"],
                structural_path=[str(kanda)],
                status=PassageStatus.CANONICAL,
            )
        )
        for order, sukta in enumerate(sorted(kandas[kanda]), start=1):
            skey, surn, sentity = avs_sukta_identity(kanda, sukta)
            passages.append(
                Passage(
                    entity_id=sentity,
                    canonical_key=skey,
                    canonical_urn=surn,
                    entity_type=EntityType.HYMN,
                    work_id=WORK_ID,
                    hierarchy={"kanda": kanda, "sukta": sukta},
                    canonical_citation=f"AVS {kanda}.{sukta}",
                    parent_key=key,
                    sequence_in_parent=order,
                    native_labels=["Sukta"],
                    structural_path=[str(kanda), str(sukta)],
                    status=PassageStatus.CANONICAL,
                )
            )

    by_sukta: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for row in units:
        by_sukta[(row["kanda"], row["sukta"])].append(row)

    for (kanda, sukta), rows in sorted(by_sukta.items()):
        parent_key = avs_sukta_identity(kanda, sukta)[0]
        for order, row in enumerate(sorted(rows, key=lambda r: r["mantra"]), start=1):
            mantra = row["mantra"]
            mkey, murn, mentity = avs_mantra_identity(kanda, sukta, mantra)
            hierarchy: dict[str, int | str] = {
                "kanda": kanda,
                "sukta": sukta,
                "mantra": mantra,
            }
            if row.get("paryaya") is not None:
                hierarchy["paryaya"] = row["paryaya"]
            passages.append(
                Passage(
                    entity_id=mentity,
                    canonical_key=mkey,
                    canonical_urn=murn,
                    entity_type=EntityType.MANTRA,
                    work_id=WORK_ID,
                    hierarchy=hierarchy,
                    canonical_citation=f"AVS {kanda}.{sukta}.{mantra}",
                    parent_key=parent_key,
                    sequence_in_parent=order,
                    native_labels=["Mantra"],
                    structural_path=[str(kanda), str(sukta), str(mantra)],
                    status=PassageStatus.CANONICAL,
                )
            )
            verse_ids[(kanda, sukta, mantra)] = mentity
    return passages, verse_ids


def build_text_versions(
    units: list[dict[str, Any]], verse_ids: dict[tuple, UUID]
) -> list[TextVersion]:
    versions: list[TextVersion] = []
    for row in units:
        text = row["text_devanagari"]
        nfc = unicodedata.normalize("NFC", text)
        if nfc != text:  # pragma: no cover - the reconciler already normalised
            raise ValueError(f"reconciled text is not NFC: {row['canvas_index']}")
        passage_id = verse_ids[(row["kanda"], row["sukta"], row["mantra"])]
        versions.append(
            TextVersion(
                text_id=derived_uuid("avs-1856-text", passage_id),
                passage_id=passage_id,
                language="sa",
                script="Devanagari",
                text_form=TextForm.SAMHITA,
                text_role=TextRole.PRIMARY_TEXT,
                text_version_id=TEXT_VERSION_ID,
                text_original=text,
                text_nfc=nfc,
                accented=bool(row.get("accent_marks_present")),
                transliteration_scheme=None,
                source_id=SOURCE_ID,
                source_artifact_id=ARTIFACT_ID,
                source_locator=source_locator(row),
                content_sha256=sha256_text(text),
                rights_status=RightsStatus.PUBLIC_DOMAIN,
            )
        )
    return versions


def assert_no_contamination(versions: list[TextVersion]) -> None:
    """No released Sanskrit may carry a prohibited source anywhere on it."""
    for version in versions:
        fields = f"{version.source_id} {version.source_artifact_id} {version.text_version_id}"
        for marker in PROHIBITED_MARKERS:
            if marker in fields.upper():
                raise ValueError(
                    f"prohibited source {marker} reached a released Atharvaveda record: "
                    f"{version.source_locator}"
                )
        if version.source_artifact_id != ARTIFACT_ID:
            raise ValueError(
                f"released record does not trace to the 1856 scan: {version.source_artifact_id}"
            )


def qa_status(rows: list[dict[str, Any]], units: list[dict[str, Any]]) -> QAStatus:
    """The release's QA verdict, read off the reconciliation rather than asserted.

    A build that stamps PASSED on itself regardless of what two readers
    actually produced is the vacuous pass this project's QA rule forbids. The
    verdict here is derived: nothing reconciled is NOT_RUN, nothing released is
    FAILED, and a release that leaves units behind says so.
    """
    if not rows:
        return QAStatus.NOT_RUN
    if not units:
        return QAStatus.FAILED
    return QAStatus.PASSED if len(units) == len(rows) else QAStatus.PASSED_WITH_WARNINGS


def write_backlog(rows: list[dict[str, Any]]) -> int:
    """Every unit that did not reach release, with its leaf and its reason."""
    backlog = [row for row in rows if not row["release_eligible"]]
    BACKLOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with BACKLOG_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        for row in sorted(
            backlog,
            key=lambda r: (
                r["canvas_index"],
                r["kanda"] or 0,
                r["sukta"] or 0,
                r["mantra"] or 0,
            ),
        ):
            handle.write(
                json.dumps(
                    {
                        "backlog_id": (
                            f"AV-{row['canvas_index']:05d}-"
                            f"{row['kanda']}-{row['sukta']}-{row['mantra']}"
                        ),
                        "work_id": WORK_ID,
                        "canvas_index": row["canvas_index"],
                        "mdz_image_id": row["mdz_image_id"],
                        "printed_page": row["printed_page"],
                        "kanda": row["kanda"],
                        "sukta": row["sukta"],
                        "mantra": row["mantra"],
                        "transcription_status": row["transcription_status"],
                        "reconciliation_detail": row["reconciliation_detail"],
                        "coordinate_note": row.get("coordinate_note"),
                        # Both readings travel with the item. Without them the
                        # backlog states a verdict an adjudicator cannot act on
                        # without going back to the reconciled file by hand.
                        "r1_text": row.get("r1_text"),
                        "r2_text": row.get("r2_text"),
                        "source_image": (
                            f"data/raw/bsb_mdz/2026-09-07/{BSB_ID}/{row['mdz_image_id']}.jpg"
                        ),
                        "transcription_policy": row["transcription_policy"],
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )
    return len(backlog)


def structural_totals(units: list[dict[str, Any]]) -> dict[str, Any]:
    kandas = sorted({row["kanda"] for row in units})
    suktas = {(row["kanda"], row["sukta"]) for row in units}
    prior = json.loads(STRUCTURE_PATH.read_text(encoding="utf-8"))
    return {
        "kanda_count_released": len(kandas),
        "kandas_released": kandas,
        "sukta_count_released": len(suktas),
        "mantra_count_released": len(units),
        "kanda_count_from_1856_running_heads": prior["kanda_count"],
        "sukta_count_from_1856_running_heads": prior["sukta_total_from_headers"],
        "note": (
            "Released counts cover only the leaves transcribed and reconciled so far. "
            "They are a coverage figure, not a claim about the size of the Samhita."
        ),
    }


def build(reconciled_dir: Path = RECONCILED_DIR) -> dict[str, Any]:
    rows = load_reconciled(reconciled_dir)
    if not rows:
        raise SystemExit(f"no reconciled transcriptions under {reconciled_dir}")

    units = [
        row
        for row in rows
        if row["release_eligible"]
        and row["text_devanagari"]
        and row["kanda"] is not None
        and row["sukta"] is not None
        and row["mantra"] is not None
    ]
    passages, verse_ids = build_passages(units)
    versions = build_text_versions(units, verse_ids)
    assert_no_contamination(versions)

    keys = [p.canonical_key for p in passages]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate canonical key in the Atharvaveda release")
    parents = {p.canonical_key for p in passages}
    for passage in passages:
        if passage.parent_key is not None and passage.parent_key not in parents:
            raise ValueError(f"passage {passage.canonical_key} has no structural parent")

    release = CanonicalRelease(
        dataset_id=BUILD_ID,
        work_id=WORK_ID,
        release_version=BUILD_VERSION,
        output_root=OUT_DIR,
        works=[registry_work()],
        passages=passages,
        text_versions=versions,
        translations=[],
        traditional_metadata=[],
        sources=[registry_source()],
        source_artifacts=[registry_artifact()],
        source_assertions=[],
        citations=[],
        audio_recordings=[],
        audio_segments=[],
        qa_issues=[],
        referent_bindings=[],
    )
    write_release(
        release,
        # The caller decides the timestamp, not the clock, or the build stops
        # being reproducible.
        built_at=BUILD_TIMESTAMP,
        source_snapshot_ids=[SNAPSHOT_ID],
        source_artifact_ids=[ARTIFACT_ID],
        parser_versions={TEXT_VERSION_ID: PARSER_VERSION},
        rights_summary={ARTIFACT_ID: "PUBLIC_DOMAIN"},
        qa_status=qa_status(rows, units),
        reconciliation_policy_version=PARSER_VERSION,
    )
    backlog_count = write_backlog(rows)

    return {
        "build_id": BUILD_ID,
        "build_version": BUILD_VERSION,
        "parser_version": PARSER_VERSION,
        "source_artifact_id": ARTIFACT_ID,
        "text_version_id": TEXT_VERSION_ID,
        "units_reconciled": len(rows),
        "units_released": len(units),
        "passages": len(passages),
        "text_versions": len(versions),
        "backlog_units": backlog_count,
        "units_with_source_locator": sum(1 for v in versions if v.source_locator),
        "prohibited_source_contamination": 0,
        "structure": structural_totals(units) if units else {},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reconciled", type=Path, default=RECONCILED_DIR)
    parser.add_argument(
        "--check",
        action="store_true",
        help="build twice and confirm the release is byte-identical",
    )
    args = parser.parse_args()

    summary = build(args.reconciled)
    if args.check:
        first = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(OUT_DIR.glob("*.jsonl"))
        }
        build(args.reconciled)
        second = {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(OUT_DIR.glob("*.jsonl"))
        }
        summary["deterministic_rebuild"] = first == second
        if first != second:
            summary["nondeterministic_files"] = sorted(
                name for name in first if first[name] != second.get(name)
            )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
