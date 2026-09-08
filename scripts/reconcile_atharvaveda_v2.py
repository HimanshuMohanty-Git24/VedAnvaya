"""Reconcile two independent readings of the 1856 Atharvaveda leaves.

Two readers transcribe the same page image without seeing each other's work.
This script aligns their units and grades each one. It never merges two
disagreeing readings into a third text: a merged reading is not something any
reader saw on the page, so it has no traceable source.

Usage:
    python scripts/reconcile_atharvaveda_v2.py <r1_dir> <r2_dir> <out_dir>
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import unicodedata
from typing import Any

#: One reader's record of one printed unit, as it comes off the JSONL.
Row = dict[str, Any]
#: A unit's identity: the canvas it is printed on, then the structural
#: coordinates the page states. A coordinate the page does not print is None,
#: which is why the last three are optional rather than merely unknown.
UnitKey = tuple[int, int | None, int | None, int | None]

POLICY = "bsb-1856-devanagari-v2"

# The 1856 print marks anudatta below (U+0952) and svarita above (U+0951);
# udatta is unmarked.
ACCENT_MARKS = {"॑", "॒"}
# Vedic Extensions, in case a reader reached for one of those instead.
ACCENT_RANGE = range(0x1CD0, 0x1D00)

RELEASE_ELIGIBLE = {"VERIFIED_EXACT", "VERIFIED_WITH_ORTHOGRAPHIC_NOTE"}
UNREADABLE = "[?]"

# Provenance vocabulary. A reading is evidence about the page only if the record
# says who looked at it, and a model that looked at a scan is not a human who
# reviewed one. Calling a model read HUMAN would make every downstream rights and
# reliability claim false, so the two are separate tokens and neither implies the
# other.
MODEL_VISUAL_READ = "MODEL_VISUAL_READ"
HUMAN_VISUAL_READ = "HUMAN_VISUAL_READ"
HUMAN_REVIEWED = "HUMAN_REVIEWED"
READER_KINDS = frozenset({MODEL_VISUAL_READ, HUMAN_VISUAL_READ, HUMAN_REVIEWED})

#: Every reading must state these. `reader_identity` carries the model or person
#: identity, `run_id` ties the reading to the batch that produced it, so a later
#: audit can ask which run a given released character came out of.
PROVENANCE_FIELDS = ("reader", "reader_kind", "reader_identity", "run_id")


def provenance_of(row: Row) -> dict[str, str] | None:
    """The reading's provenance, or None if it is incomplete or not truthful.

    Returning None is what makes a unit ineligible for release: it is better to
    hold a correct reading back than to publish one whose origin is unstated.
    """
    values = {field: row.get(field) for field in PROVENANCE_FIELDS}
    if any(not isinstance(value, str) or not value.strip() for value in values.values()):
        return None
    if values["reader_kind"] not in READER_KINDS:
        return None
    return {field: str(value) for field, value in values.items()}


def is_accent(char: str) -> bool:
    return char in ACCENT_MARKS or ord(char) in ACCENT_RANGE


def skeleton(text: str) -> str:
    """The reading with its accent layer removed."""
    return "".join(c for c in unicodedata.normalize("NFC", text) if not is_accent(c))


def accent_signature(text: str) -> list[tuple[int, str]]:
    """Accent marks paired with their offset in the accent-free skeleton."""
    signature: list[tuple[int, str]] = []
    position = 0
    for char in unicodedata.normalize("NFC", text):
        if is_accent(char):
            signature.append((position, char))
        else:
            position += 1
    return signature


def edit_distance(a: str, b: str) -> int:
    if a == b:
        return 0
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb)))
        previous = current
    return previous[-1]


COORDINATE_NAMES = ("canvas_index", "kanda", "sukta", "mantra")


def unit_key(row: Row) -> UnitKey:
    return (row["canvas_index"], row.get("kanda"), row.get("sukta"), row.get("mantra"))


def sort_key(key: UnitKey) -> tuple[int, ...]:
    return tuple(-1 if part is None else part for part in key)


def keys_compatible(a: UnitKey, b: UnitKey) -> bool:
    """True when two keys differ only where one reader left a coordinate unstated.

    A leaf that prints no running head leaves a reader nothing to read the
    kanda off, and the brief tells them to record `null`. A second reader who
    carries the kanda over from the previous leaf writes the number. Both are
    honest readings of the same unit, so a null must not by itself split them.

    Two readers who each state a coordinate and state it *differently* are a
    real structural disagreement and stay incompatible.
    """
    return all(x == y or x is None or y is None for x, y in zip(a, b, strict=True))


def merge_keys(a: UnitKey, b: UnitKey) -> UnitKey:
    """The key carrying whichever coordinate the readers actually stated."""
    canvas = a[0] if a[0] is not None else b[0]
    kanda, sukta, mantra = (x if x is not None else y for x, y in zip(a[1:], b[1:], strict=True))
    return canvas, kanda, sukta, mantra


def coordinate_note(a: UnitKey, b: UnitKey) -> str | None:
    unstated = [
        name
        for name, x, y in zip(COORDINATE_NAMES, a, b, strict=True)
        if (x is None) != (y is None)
    ]
    if not unstated:
        return None
    return (
        "aligned across an unstated coordinate (" + ", ".join(unstated) + "): one reader read "
        "it off the page and the other recorded that the page does not print it. The unit is "
        "the same unit; the coordinate is carried from the reader who stated it."
    )


def align(
    r1: dict[UnitKey, Row], r2: dict[UnitKey, Row]
) -> list[tuple[UnitKey, Row | None, Row | None, str | None]]:
    """Pair the two readers' units.

    Exact key matches first. A leftover pair is rescued only when the keys
    differ solely where one reader left a coordinate unstated *and* the match
    is unique from both sides. Anything ambiguous stays unpaired, so it
    surfaces as a structural disagreement instead of becoming a guess.
    """
    aligned: list[tuple[UnitKey, Row | None, Row | None, str | None]] = []
    matched_1: set[UnitKey] = set()
    matched_2: set[UnitKey] = set()

    for key in r1:
        if key in r2:
            aligned.append((key, r1[key], r2[key], None))
            matched_1.add(key)
            matched_2.add(key)

    for key1 in [k for k in r1 if k not in matched_1]:
        candidates = [k for k in r2 if k not in matched_2 and keys_compatible(key1, k)]
        if len(candidates) != 1:
            continue
        key2 = candidates[0]
        rematch = [k for k in r1 if k not in matched_1 and keys_compatible(k, key2)]
        if len(rematch) != 1:
            continue
        matched_1.add(key1)
        matched_2.add(key2)
        aligned.append((merge_keys(key1, key2), r1[key1], r2[key2], coordinate_note(key1, key2)))

    aligned.extend((key, r1[key], None, None) for key in r1 if key not in matched_1)
    aligned.extend((key, None, r2[key], None) for key in r2 if key not in matched_2)
    return sorted(aligned, key=lambda item: sort_key(item[0]))


def load_reader(directory: pathlib.Path) -> dict[UnitKey, Row]:
    rows: dict[UnitKey, Row] = {}
    for path in sorted(directory.glob("leaf_*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            rows[unit_key(row)] = row
    return rows


def grade(left: Row | None, right: Row | None) -> tuple[str, str]:
    """Return (status, detail) for one aligned unit."""
    if left is None or right is None:
        seen = "R2" if left is None else "R1"
        return (
            "STRUCTURAL_REVIEW_REQUIRED",
            f"read by {seen} only: the readers do not agree on how many units this "
            "page prints, or on how they are numbered",
        )

    a = unicodedata.normalize("NFC", left["text_devanagari"])
    b = unicodedata.normalize("NFC", right["text_devanagari"])
    if a == b:
        if not accent_signature(a):
            return (
                "VERIFIED_WITH_ORTHOGRAPHIC_NOTE",
                "readings identical, but neither carries an accent mark; the 1856 "
                "page accents nearly every line, so this is recorded as an accent "
                "layer not reproduced, not as an unaccented line",
            )
        return "VERIFIED_EXACT", "readings identical codepoint for codepoint"

    if UNREADABLE in a or UNREADABLE in b:
        return "CHARACTER_UNCERTAIN", "at least one reader could not resolve a character"

    skeleton_a, skeleton_b = skeleton(a), skeleton(b)
    if skeleton_a == skeleton_b:
        marks_a, marks_b = len(accent_signature(a)), len(accent_signature(b))
        if not marks_a or not marks_b:
            return (
                "ACCENT_UNCERTAIN",
                f"syllables agree; one reader recorded {marks_a} accent marks and "
                f"the other {marks_b}, so one of them dropped the accent layer",
            )
        return (
            "ACCENT_UNCERTAIN",
            f"syllables agree; accent marks differ ({marks_a} vs {marks_b} marks)",
        )

    distance = edit_distance(skeleton_a, skeleton_b)
    longest = max(len(skeleton_a), len(skeleton_b), 1)
    if distance / longest > 0.25:
        return (
            "BOUNDARY_UNCERTAIN",
            f"readings differ over {distance} of {longest} skeleton characters; that "
            "is too much to be a character misreading and is more likely a "
            "disagreement about where the unit begins or ends",
        )
    return (
        "CHARACTER_UNCERTAIN",
        f"syllables differ in {distance} of {longest} skeleton characters",
    )


def reconcile(r1_dir: pathlib.Path, r2_dir: pathlib.Path, out_dir: pathlib.Path) -> dict[str, Any]:
    r1, r2 = load_reader(r1_dir), load_reader(r2_dir)
    aligned = align(r1, r2)

    out_dir.mkdir(parents=True, exist_ok=True)
    by_leaf: dict[int, list[Row]] = collections.defaultdict(list)

    status_counts: collections.Counter[str] = collections.Counter()
    both = char_disagree = accent_disagree = boundary_disagree = 0
    skeleton_chars = skeleton_edits = 0
    accent_bearing = rescued = 0
    complete = withheld_for_provenance = 0

    for key, left, right, note in aligned:
        status, detail = grade(left, right)
        if note is not None:
            rescued += 1
        status_counts[status] += 1
        source = left or right
        assert source is not None

        if left is not None and right is not None:
            both += 1
            a = unicodedata.normalize("NFC", left["text_devanagari"])
            b = unicodedata.normalize("NFC", right["text_devanagari"])
            skeleton_a, skeleton_b = skeleton(a), skeleton(b)
            skeleton_chars += max(len(skeleton_a), len(skeleton_b))
            skeleton_edits += edit_distance(skeleton_a, skeleton_b)
            if status == "BOUNDARY_UNCERTAIN":
                boundary_disagree += 1
            elif skeleton_a != skeleton_b:
                char_disagree += 1
            signature_a, signature_b = accent_signature(a), accent_signature(b)
            if signature_a or signature_b:
                accent_bearing += 1
                if signature_a != signature_b:
                    accent_disagree += 1

        r1_provenance = provenance_of(left) if left is not None else None
        r2_provenance = provenance_of(right) if right is not None else None
        provenance_complete = r1_provenance is not None and r2_provenance is not None
        if provenance_complete:
            complete += 1
        agreed = (
            left is not None
            and right is not None
            and status in RELEASE_ELIGIBLE
            and provenance_complete
        )
        if left is not None and right is not None and status in RELEASE_ELIGIBLE and not agreed:
            withheld_for_provenance += 1
        record = {
            "canvas_index": key[0],
            "mdz_image_id": source["mdz_image_id"],
            "printed_page": source.get("printed_page"),
            "kanda": key[1],
            "sukta": key[2],
            "mantra": key[3],
            "paryaya": source.get("paryaya"),
            "text_devanagari": (
                unicodedata.normalize("NFC", left["text_devanagari"])
                if agreed and left is not None
                else None
            ),
            "r1_text": left["text_devanagari"] if left else None,
            "r2_text": right["text_devanagari"] if right else None,
            "transcription_status": status,
            "reconciliation_detail": detail,
            "coordinate_note": note,
            "release_eligible": agreed,
            "r1_provenance": r1_provenance,
            "r2_provenance": r2_provenance,
            "provenance_complete": provenance_complete,
            "accent_marks_present": bool(accent_signature(source["text_devanagari"])),
            "spans_canvases": source.get("spans_canvases"),
            "structural_marker": source.get("structural_marker"),
            "unclear_count": source.get("unclear_count", 0),
            "transcription_policy": POLICY,
            "schema_version": "2.0.0",
        }
        by_leaf[key[0]].append(record)

    for canvas, records in by_leaf.items():
        path = out_dir / f"leaf_{canvas:05d}.jsonl"
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            for record in records:
                handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    every = [record for records in by_leaf.values() for record in records]
    accent_reproduced = sum(1 for record in every if record["accent_marks_present"])
    total = len(aligned)
    return {
        "policy": POLICY,
        "leaves": len(by_leaf),
        "units_total": total,
        "units_read_by_both": both,
        "units_read_by_one_only": total - both,
        "units_aligned_across_an_unstated_coordinate": rescued,
        "unstated_coordinate_note": (
            "Pairs the readers agreed on as units, but where one of them recorded a "
            "structural coordinate the page does not print. Counted here so the "
            "alignment is never silent; the coordinate disagreement is not evidence "
            "about the text and is graded only on the text."
        ),
        "status_counts": dict(sorted(status_counts.items())),
        "release_eligible_units": sum(1 for record in every if record["release_eligible"]),
        "units_with_complete_provenance": complete,
        "units_withheld_for_incomplete_provenance": withheld_for_provenance,
        "reader_kinds_seen": sorted(
            {
                provenance["reader_kind"]
                for record in every
                for provenance in (record["r1_provenance"], record["r2_provenance"])
                if provenance is not None
            }
        ),
        "provenance_policy": (
            "A reading performed by a model is recorded as MODEL_VISUAL_READ. "
            "HUMAN_REVIEWED is reserved for material an actual human reviewed and "
            "is never inferred from a model reading. A unit whose two readings do "
            "not both carry complete provenance is withheld from release even when "
            "the readings agree."
        ),
        "exact_agreement_rate_over_units_read_by_both": (
            round(status_counts["VERIFIED_EXACT"] / both, 4) if both else None
        ),
        # VERIFIED_EXACT means identical *and* accent-bearing, so on a skeleton run
        # -- where readers are told to leave the accent layer to the geometric
        # pipeline -- it is 0 by construction and the rate above reads as total
        # disagreement. This is the number that actually answers "did the two
        # readers produce the same codepoints".
        "codepoint_identical_rate_over_units_read_by_both": (
            round(
                (status_counts["VERIFIED_EXACT"] + status_counts["VERIFIED_WITH_ORTHOGRAPHIC_NOTE"])
                / both,
                4,
            )
            if both
            else None
        ),
        "codepoint_identical_units": (
            status_counts["VERIFIED_EXACT"] + status_counts["VERIFIED_WITH_ORTHOGRAPHIC_NOTE"]
        ),
        "character_disagreement_rate_over_units": (
            round(char_disagree / both, 4) if both else None
        ),
        "character_disagreement_rate_over_skeleton_chars": (
            round(skeleton_edits / skeleton_chars, 4) if skeleton_chars else None
        ),
        "accent_disagreement_rate_over_accent_bearing_units": (
            round(accent_disagree / accent_bearing, 4) if accent_bearing else None
        ),
        "accent_bearing_units_read_by_both": accent_bearing,
        "boundary_disagreement_rate_over_units": (
            round(boundary_disagree / both, 4) if both else None
        ),
        "units_carrying_any_vedic_accent": accent_reproduced,
        "accent_reproduction_gap": total - accent_reproduced,
        "accent_reproduction_gap_note": (
            "The printed source marks accent throughout. A unit carrying none has "
            "dropped a real feature of the page, which two agreeing readers cannot "
            "detect between them."
        ),
        "merge_policy": (
            "No reading is synthesised from two disagreeing ones; a merged reading "
            "has no traceable source."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("r1_dir", type=pathlib.Path)
    parser.add_argument("r2_dir", type=pathlib.Path)
    parser.add_argument("out_dir", type=pathlib.Path)
    args = parser.parse_args()
    summary = reconcile(args.r1_dir, args.r2_dir, args.out_dir)
    path = args.out_dir.parent / f"{args.out_dir.name}_summary.json"
    path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
