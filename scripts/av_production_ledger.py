"""Account for all 478 leaves of the 1856 Atharvaveda scan, read or not.

A transcription run that reports only what it managed to read is unfalsifiable:
a leaf that was never assigned looks exactly like a leaf that has no text on it.
This ledger enumerates every canvas in the artifact, says what the ink on it
suggests it is, and then says what the run has actually done with it. A leaf can
be unread, but it cannot be missing.

Leaf classification here is measured, not read: it comes from ink density and the
number of printed lines the line-finder locates, which is enough to separate a
page of type from a blank verso or a title page, and is deliberately not enough
to say anything about the text. Deciding what a leaf *says* is a reader's job.

Usage:
    python scripts/av_production_ledger.py            # write the ledger
    python scripts/av_production_ledger.py --telemetry-only
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

from crop_atharvaveda_leaf import SCAN_DIR, find_text_block, leaf_path
from crop_atharvaveda_line import find_lines
from PIL import Image

_REPO = pathlib.Path(__file__).resolve().parents[1]
AV_ROOT = _REPO / "data" / "transcriptions" / "atharvaveda_bsb_1856" / "v2"
LEDGER = AV_ROOT / "production_ledger.json"

ARTIFACT = "BSB.AV.SAUNAKA.ROTH_WHITNEY.1856.SCAN"
BSB_ID = "bsb10219750"

#: The samhita text runs from this canvas to this one inclusive, read off the
#: running heads in an earlier pass over all 478 leaves and recorded in
#: `data/source_registry/atharvaveda_1856_structure_summary.json`. Outside it lie
#: the fourteen front-matter leaves and six back-matter leaves: a publisher's
#: advertisement is a page of type, so ink alone cannot tell it from a page of
#: Atharvaveda, and counting it as outstanding transcription work would overstate
#: the job by twenty leaves.
STRUCTURE_SUMMARY = _REPO / "data" / "source_registry" / "atharvaveda_1856_structure_summary.json"

#: A leaf whose text block holds at least this many located lines is carrying a
#: page of type rather than a title, a plate, or a blank.
TEXT_LINE_FLOOR = 6
#: Share of dark pixels in the text block below which the leaf is effectively
#: blank. Paper grain and foxing alone land well under this.
INK_FLOOR = 0.005

OUT_OF_RANGE = "OUTSIDE_SAMHITA_TEXT_RANGE"
TEXT_CANDIDATE = "TEXT_CANDIDATE"
SPARSE = "SPARSE_OR_FRONT_MATTER"
EMPTY = "EFFECTIVELY_BLANK"

#: Share of the text block's width, centred, over which printed lines are located.
#: `find_text_block` keeps the binding gutter on many versos, and that striped
#: shadow inks every row, merging all the printed lines into a single run and
#: making a dense page of type look like a title page. Type sits in the middle of
#: the leaf, so profiling the middle skips the gutter and the marginal numerals
#: both. Measured across the affected leaves, 0.7 recovers them (canvas 200: 1
#: line -> 26) and leaves already-correct leaves unchanged; 0.6 starts splitting
#: single lines in two. `find_text_block` itself is deliberately left alone,
#: because the accent pipeline is calibrated against it.
LINE_PROFILE_WIDTH = 0.7


def count_printed_lines(body: Image.Image) -> int:
    """Printed lines in a text block, ignoring what sits in its margins."""
    margin = round(body.width * (1 - LINE_PROFILE_WIDTH) / 2)
    centre = body.crop((margin, 0, body.width - margin, body.height))
    return len(find_lines(centre))


def text_range() -> tuple[int, int]:
    """The first and last canvas carrying samhita text, per the structure summary."""
    summary = json.loads(STRUCTURE_SUMMARY.read_text(encoding="utf-8"))
    return int(summary["text_first_canvas"]), int(summary["text_last_canvas"])


def measure(canvas: int, first_text: int, last_text: int) -> dict[str, Any]:
    """What the ink on one leaf says about whether it is a page of type."""
    path = leaf_path(canvas)
    with Image.open(path) as handle:
        image = handle.convert("L")
    block = find_text_block(image)
    body = image.crop(block)
    # Downsample before counting: the stored leaf is an upscale, so counting at
    # 4000px counts interpolated pixels and overstates the ink.
    small = body.resize(
        (max(1, body.width // 4), max(1, body.height // 4)), Image.Resampling.LANCZOS
    )
    dark = sum(1 for value in small.convert("L").tobytes() if value < 128)
    ink = dark / (small.width * small.height)
    lines = count_printed_lines(body) if ink >= INK_FLOOR else 0

    if not first_text <= canvas <= last_text:
        classification = OUT_OF_RANGE
    elif ink < INK_FLOOR:
        classification = EMPTY
    elif lines >= TEXT_LINE_FLOOR:
        classification = TEXT_CANDIDATE
    else:
        classification = SPARSE

    return {
        "canvas_index": canvas,
        "mdz_image_id": f"{BSB_ID}_{canvas:05d}",
        "leaf_size": list(image.size),
        "text_block": list(block),
        "ink_share": round(ink, 5),
        "located_lines": lines,
        "classification": classification,
    }


def read_state(canvas: int) -> dict[str, Any]:
    """What the run has done with one leaf so far."""
    name = f"leaf_{canvas:05d}.jsonl"

    def count(directory: str) -> int | None:
        path = AV_ROOT / directory / name
        if not path.exists():
            return None
        return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())

    r1, r2 = count("R1"), count("R2")
    reconciled = count("reconciled")
    released = 0
    path = AV_ROOT / "reconciled" / name
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip() and json.loads(line).get("release_eligible"):
                released += 1
    return {
        "r1_units": r1,
        "r2_units": r2,
        "reconciled_units": reconciled,
        "release_eligible_units": released,
        "first_read": r1 is not None,
        "second_read": r2 is not None,
        "reconciled": reconciled is not None,
    }


def build(measured: dict[int, dict[str, Any]] | None = None) -> dict[str, Any]:
    leaves = sorted(int(path.stem.split("_")[-1]) for path in SCAN_DIR.glob(f"{BSB_ID}_*.jpg"))
    first_text, last_text = text_range()
    rows = []
    for canvas in leaves:
        row = (
            dict(measured[canvas])
            if measured and canvas in measured
            else measure(canvas, first_text, last_text)
        )
        row.update(read_state(canvas))
        rows.append(row)

    text_leaves = [row for row in rows if row["classification"] == TEXT_CANDIDATE]
    return {
        "artifact_id": ARTIFACT,
        "bsb_id": BSB_ID,
        "leaves_available": len(rows),
        "samhita_text_canvas_range": [first_text, last_text],
        "leaves_by_classification": {
            key: sum(1 for row in rows if row["classification"] == key)
            for key in (TEXT_CANDIDATE, SPARSE, EMPTY, OUT_OF_RANGE)
        },
        "text_candidate_leaves": len(text_leaves),
        "leaves_first_read": sum(1 for row in rows if row["first_read"]),
        "leaves_second_read": sum(1 for row in rows if row["second_read"]),
        "leaves_reconciled": sum(1 for row in rows if row["reconciled"]),
        "leaves_with_any_release_eligible_unit": sum(
            1 for row in rows if row["release_eligible_units"]
        ),
        "text_leaves_unread": sorted(
            row["canvas_index"] for row in text_leaves if not row["first_read"]
        ),
        "text_leaves_read_once_only": sorted(
            row["canvas_index"]
            for row in text_leaves
            if row["first_read"] and not row["second_read"]
        ),
        "units_first_read": sum(row["r1_units"] or 0 for row in rows),
        "units_second_read": sum(row["r2_units"] or 0 for row in rows),
        "units_reconciled": sum(row["reconciled_units"] or 0 for row in rows),
        "units_release_eligible": sum(row["release_eligible_units"] for row in rows),
        "classification_note": (
            "Measured from ink density and located line count, never from a reading. "
            f"{TEXT_CANDIDATE}: at least {TEXT_LINE_FLOOR} located lines. {EMPTY}: ink "
            f"share below {INK_FLOOR}. {SPARSE} is everything between, which is title "
            f"pages, part titles and near-blank leaves. {OUT_OF_RANGE} is front and "
            "back matter, which carries type but not Atharvaveda."
        ),
        "coverage_note": (
            "leaves_available is every canvas in the artifact. A leaf absent from "
            "text_leaves_unread and present in leaves_first_read has been worked; any "
            "other text-candidate leaf is explicitly outstanding, never silently gone."
        ),
        "leaves": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--telemetry-only",
        action="store_true",
        help="reuse the leaf measurements already in the ledger instead of remeasuring",
    )
    args = parser.parse_args()

    measured = None
    if args.telemetry_only and LEDGER.exists():
        previous = json.loads(LEDGER.read_text(encoding="utf-8"))
        measured = {row["canvas_index"]: row for row in previous["leaves"]}
    elif args.telemetry_only:
        sys.exit(f"no ledger at {LEDGER} to reuse measurements from")

    ledger = build(measured)
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    summary = {key: value for key, value in ledger.items() if key != "leaves"}
    summary.pop("text_leaves_unread", None)
    summary.pop("text_leaves_read_once_only", None)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
