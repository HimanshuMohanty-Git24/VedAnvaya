"""Freeze the AV accent-binder calibration set.

Selects roughly 75 lines from the 478-leaf corpus, stratified to cover early,
middle, and late kāṇḍas; light, moderate, and dense accent lines; section
boundaries; and line positions within leaves. The set is frozen BEFORE any
calibration metrics are run — choosing lines after seeing results invalidates
the calibration.

The selection is deterministic (no randomness): given the same 1856 scan it
always produces the same set. Lines are described by (canvas_index, line_index)
pairs. The extractor has already been verified correct on canvas 32 lines 12
and 19, which are included as mandatory reference lines.

Output:
    data/transcriptions/atharvaveda_bsb_1856/v2/calibration_set.json

Usage:
    python scripts/build_av_calibration_set.py [--verify]
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from crop_atharvaveda_leaf import leaf_path
from extract_atharvaveda_accents import extract

REPO = pathlib.Path(__file__).resolve().parents[1]
OUT_PATH = REPO / "data/transcriptions/atharvaveda_bsb_1856/v2/calibration_set.json"

# ── Mandatory reference lines (verified by multi-reader gold) ──────────────
MANDATORY = [
    {
        "canvas_index": 32,
        "line_index": 0,
        "stratum": "running_head",
        "note": "line 0 always unaccented - baseline check",
    },
    {
        "canvas_index": 32,
        "line_index": 12,
        "stratum": "gold_verified",
        "note": "P1/P2/P3 three-reader gold: 7 anudatta 3 svarita",
    },
    {
        "canvas_index": 32,
        "line_index": 19,
        "stratum": "gold_verified",
        "note": "Q1/Q2 two-reader gold: 7 anudatta 4 svarita",
    },
]

# ── Stratified sample: 25 leaves x 3 lines each = 75 lines ─────────────────
#
# The 478 IIIF canvases span ~20 kāṇḍas. Canvases 1-14 are front matter;
# canvases 15-492 hold the printed text. Sampling every 18th canvas from
# leaf 15 onward gives 25 evenly spaced leaves across the corpus. For each
# leaf, three lines are selected at roughly the start, middle, and end of
# the text area (lines 2, 9, 17 where available) to cover different verse
# positions and avoid systematically picking the densest or the sparest area.
#
# Stratum tags are assigned by leaf number to approximate kāṇḍa coverage;
# exact kāṇḍa boundaries will be established when reader transcriptions exist.
# The strata are: early (leaves 15-109), middle (110-260), late (261-390),
# kanda19_area (391-440), kanda20_area (441-478), kanda20_late (over 460).
# This is an approximation; it will be corrected once structural data exists.


def _stratum(canvas: int) -> str:
    if canvas <= 109:
        return "early_kandas"
    if canvas <= 260:
        return "middle_kandas"
    if canvas <= 390:
        return "late_kandas"
    if canvas <= 440:
        return "kanda19_area"
    return "kanda20_area"


# Sampled leaf indices (25 leaves, spaced ~18 canvases apart starting at 15)
_SAMPLE_CANVASES = [15 + 18 * i for i in range(25)]
# Lines to select within each leaf
_SAMPLE_LINES = [2, 9, 17]

# Extra deliberately-difficult lines (section boundaries, unusual typography)
_EXTRA = [
    {
        "canvas_index": 15,
        "line_index": 0,
        "stratum": "running_head",
        "note": "first content leaf running head",
    },
    {
        "canvas_index": 430,
        "line_index": 5,
        "stratum": "kanda20_area",
        "note": "leaf 430 was in v2 calib B1 set",
    },
    {
        "canvas_index": 430,
        "line_index": 12,
        "stratum": "kanda20_area",
        "note": "leaf 430 middle area",
    },
]


def build_candidate_lines() -> list[dict]:
    """Return the full frozen selection with deduplication."""
    seen: set[tuple[int, int]] = set()
    lines: list[dict] = []

    def _add(entry: dict) -> None:
        key = (entry["canvas_index"], entry["line_index"])
        if key not in seen:
            seen.add(key)
            lines.append(entry)

    for entry in MANDATORY:
        _add(entry)

    for canvas in _SAMPLE_CANVASES:
        stratum = _stratum(canvas)
        for li in _SAMPLE_LINES:
            _add(
                {
                    "canvas_index": canvas,
                    "line_index": li,
                    "stratum": stratum,
                    "note": "stratified_sample",
                }
            )

    for entry in _EXTRA:
        _add(entry)

    return lines


def verify_line(entry: dict, scan_present: bool) -> dict:
    """Run the extractor on one line and record counts."""
    canvas, li = entry["canvas_index"], entry["line_index"]
    if not scan_present:
        return {**entry, "verified": False, "reason": "scan not on disk"}
    try:
        result = extract(canvas, li)
        ln = result["lines"][0]
        return {
            **entry,
            "verified": True,
            "anudatta_count": ln["anudatta_count"],
            "svarita_count": ln["svarita_count"],
            "word_spans_count": len(ln["word_spans"]),
            "line_pitch": result["line_pitch"],
        }
    except Exception as exc:
        return {**entry, "verified": False, "reason": str(exc)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="run extractor on every line")
    args = parser.parse_args()

    lines = build_candidate_lines()

    results = []
    for entry in lines:
        if args.verify:
            canvas = entry["canvas_index"]
            if not leaf_path(canvas).exists():
                results.append({**entry, "verified": False, "reason": "leaf not on disk"})
            else:
                results.append(verify_line(entry, True))
        else:
            results.append(entry)

    strata: dict[str, int] = {}
    for r in results:
        s = r["stratum"]
        strata[s] = strata.get(s, 0) + 1

    output = {
        "schema_version": "1.0.0",
        "source": "BSB_MDZ_bsb10219750",
        "policy": "FROZEN_BEFORE_CALIBRATION — this list was committed before any "
        "calibration metrics were computed; changing it afterwards would "
        "invalidate the calibration.",
        "mandatory_reference_lines": 3,
        "total_lines": len(results),
        "strata": strata,
        "lines": results,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"Written {OUT_PATH} ({len(results)} lines)")
    for stratum, count in sorted(strata.items()):
        print(f"  {stratum}: {count}")


if __name__ == "__main__":
    main()
