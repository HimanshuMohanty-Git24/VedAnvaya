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

POLICY = "bsb-1856-devanagari-v2"

# The 1856 print marks anudatta below (U+0952) and svarita above (U+0951);
# udatta is unmarked.
ACCENT_MARKS = {"॑", "॒"}
# Vedic Extensions, in case a reader reached for one of those instead.
ACCENT_RANGE = range(0x1CD0, 0x1D00)

RELEASE_ELIGIBLE = {"VERIFIED_EXACT", "VERIFIED_WITH_ORTHOGRAPHIC_NOTE"}
UNREADABLE = "[?]"


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


def unit_key(row: dict) -> tuple:
    return (row["canvas_index"], row.get("kanda"), row.get("sukta"), row.get("mantra"))


def sort_key(key: tuple) -> tuple:
    return tuple(-1 if part is None else part for part in key)


def load_reader(directory: pathlib.Path) -> dict[tuple, dict]:
    rows: dict[tuple, dict] = {}
    for path in sorted(directory.glob("leaf_*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            rows[unit_key(row)] = row
    return rows


def grade(left: dict | None, right: dict | None) -> tuple[str, str]:
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


def reconcile(r1_dir: pathlib.Path, r2_dir: pathlib.Path, out_dir: pathlib.Path) -> dict:
    r1, r2 = load_reader(r1_dir), load_reader(r2_dir)
    keys = sorted(set(r1) | set(r2), key=sort_key)

    out_dir.mkdir(parents=True, exist_ok=True)
    by_leaf: dict[int, list[dict]] = collections.defaultdict(list)

    status_counts: collections.Counter[str] = collections.Counter()
    both = char_disagree = accent_disagree = boundary_disagree = 0
    skeleton_chars = skeleton_edits = 0
    accent_bearing = 0

    for key in keys:
        left, right = r1.get(key), r2.get(key)
        status, detail = grade(left, right)
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

        agreed = left is not None and right is not None and status in RELEASE_ELIGIBLE
        record = {
            "canvas_index": key[0],
            "mdz_image_id": source["mdz_image_id"],
            "printed_page": source.get("printed_page"),
            "kanda": key[1],
            "sukta": key[2],
            "mantra": key[3],
            "paryaya": source.get("paryaya"),
            "text_devanagari": (
                unicodedata.normalize("NFC", left["text_devanagari"]) if agreed else None
            ),
            "r1_text": left["text_devanagari"] if left else None,
            "r2_text": right["text_devanagari"] if right else None,
            "transcription_status": status,
            "reconciliation_detail": detail,
            "release_eligible": agreed,
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
    total = len(keys)
    return {
        "policy": POLICY,
        "leaves": len(by_leaf),
        "units_total": total,
        "units_read_by_both": both,
        "units_read_by_one_only": total - both,
        "status_counts": dict(sorted(status_counts.items())),
        "release_eligible_units": sum(1 for record in every if record["release_eligible"]),
        "exact_agreement_rate_over_units_read_by_both": (
            round(status_counts["VERIFIED_EXACT"] / both, 4) if both else None
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
