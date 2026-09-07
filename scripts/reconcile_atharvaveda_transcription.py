"""Reconcile two independent readings of the same 1856 leaf into a verified record.

The point of two stages is that neither reader may certify itself. Stage 1 and stage 2
each read the page image without seeing the other's output; this script is the only thing
that assigns ``VERIFIED_EXACT``, and it does so purely from agreement.

Statuses, and what each one actually proves
===========================================

``VERIFIED_EXACT``
    Two independent readings are identical after NFC. This is the only status that
    supports releasing the unit as primary text without a caveat.
``VERIFIED_WITH_ORTHOGRAPHIC_NOTE``
    The readings agree on the letters but not byte for byte -- either they differ only in
    Vedic accent, or they differ in editorial marks, punctuation, numerals or spacing.
    The two cases carry different ``reconciliation_detail`` text and are not conflated:
    "equal under the accent-stripped comparison surface" would ALSO be true of two
    readings that differ in punctuation, so reporting that as an accent difference asserts
    a cause the comparison never measured.
``SOURCE_AMBIGUOUS``
    Either reader judged the page itself defective or illegible at that unit.
``TRANSCRIPTION_UNCERTAIN``
    Either reading carries ``[?]``, or the two disagree beyond accentuation. Needs
    stage 3.
``PHILOLOGICAL_REVIEW_REQUIRED``
    A structural disagreement: one reader saw a unit the other did not. That is not a
    character-level problem and cannot be adjudicated by re-reading one akṣara.

What the first doubly-read leaf actually showed
===============================================

Leaf n36, 22 units read independently twice: ``VERIFIED_EXACT`` **0**. Sixteen units agreed
on the letters and differed in punctuation or spacing; six differed in the letters
themselves. Separately, BOTH readers recorded **zero** Vedic accent marks on a page that
prints them throughout, so accent reproduction failed completely and did so *in agreement*
-- which is the failure mode a two-reader check cannot see, because agreement is its only
signal. ``accent_fidelity_gap`` in the summary exists to make that visible.

What this script must never do
==============================

It must never *merge* two disagreeing readings into a third text, and it must never pick
a winner by any rule other than agreement. Under RIGHTS-13 a synthesised reading is a
reading from nowhere, which is precisely the untraceable channel the firewall exists to
close. Disagreements are preserved with both readings attached.
"""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from vedagraph.normalize import (  # noqa: E402
    ComparisonForm,
    comparison_form,
    has_vedic_accents,
    strip_vedic_accents,
)

ROOT = REPO / "data" / "transcriptions" / "atharvaveda_bsb_1856"
STAGE1 = ROOT / "stage1"
STAGE2 = ROOT / "stage2"
STAGE3 = ROOT / "stage3"
OUT = ROOT / "reconciled"
SUMMARY = ROOT / "reconciliation_summary.json"

UNCLEAR = "[?]"

RELEASE_ELIGIBLE = frozenset({"VERIFIED_EXACT", "VERIFIED_WITH_ORTHOGRAPHIC_NOTE"})

#: The 1856 edition marks accent throughout, so a unit carrying none has lost a real
#: feature of the page. Status alone cannot catch that: two readers who BOTH drop accent
#: agree, and agreement is the only signal the status vocabulary has. Release eligibility
#: therefore requires the status AND the accent, because a rights/QA review found 16 units
#: flagged release_eligible whose readings carried zero accent marks -- eligible by a rule
#: that was measuring the wrong thing.
REQUIRE_ACCENT_FOR_RELEASE = True


@dataclass(frozen=True)
class Coordinate:
    kanda: int
    sukta: int
    mantra: int

    def as_tuple(self) -> tuple[int, int, int]:
        return (self.kanda, self.sukta, self.mantra)


def _load_stage(directory: Path) -> dict[tuple[int, int, int], dict[str, object]]:
    """Load one stage, joining a mantra that the print splits across a page break.

    A coordinate legitimately appears on TWO leaves when the edition sets a mantra's first
    hemistich as the last line of a page and its second as the first line of the next; the
    readers record each fragment on the leaf that prints it, with a continuation note.
    Treating a repeated coordinate as an error rejected the whole stage. Treating it as an
    overwrite would silently keep one hemistich and drop the other, which is worse.

    The fragments are concatenated in CANVAS ORDER, which is the order the page prints
    them, and the unit records every leaf it spans. This is a join, not a merge of two
    competing readings: the fragments are disjoint parts of one mantra, not two accounts
    of the same text, so nothing is being adjudicated here.
    """
    fragments: dict[tuple[int, int, int], list[dict[str, object]]] = {}
    if not directory.exists():
        return {}
    for path in sorted(directory.glob("leaf_*.jsonl")):
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON at {path}:{line_number}") from exc
            key = (int(row["kanda"]), int(row["sukta"]), int(row["mantra"]))
            fragments.setdefault(key, []).append(row)

    records: dict[tuple[int, int, int], dict[str, object]] = {}
    for key, parts in fragments.items():
        parts.sort(key=lambda item: int(str(item["canvas_index"])))
        if len(parts) == 1:
            records[key] = parts[0]
            continue
        joined = dict(parts[0])
        joined["text_devanagari"] = " ".join(str(part["text_devanagari"]).strip() for part in parts)
        joined["spans_canvases"] = [int(str(part["canvas_index"])) for part in parts]
        records[key] = joined
    return records


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def _classify(left: dict[str, object] | None, right: dict[str, object] | None) -> tuple[str, str]:
    """Return ``(status, detail)`` for one coordinate seen by one or both readers."""
    if left is None or right is None:
        seen = "stage2 only" if left is None else "stage1 only"
        return (
            "PHILOLOGICAL_REVIEW_REQUIRED",
            f"structural disagreement: the unit was read by {seen}, so the two readers "
            "do not agree on how many units the page prints",
        )

    left_text, right_text = str(left["text_devanagari"]), str(right["text_devanagari"])

    if UNCLEAR in left_text or UNCLEAR in right_text:
        return (
            "TRANSCRIPTION_UNCERTAIN",
            f"unclear akṣara marked by "
            f"{'both readers' if UNCLEAR in left_text and UNCLEAR in right_text else 'one reader'}",
        )

    if "SOURCE_AMBIGUOUS" in {left.get("transcription_status"), right.get("transcription_status")}:
        return "SOURCE_AMBIGUOUS", "a reader judged the printed page itself defective here"

    if _nfc(left_text) == _nfc(right_text):
        return "VERIFIED_EXACT", "two independent readings agree after NFC"

    # Two separate questions, and collapsing them mislabels the corpus.
    #
    # ACCENT_STRIPPED_COMPARISON removes Vedic accents AND editorial marks -- dandas,
    # digits, brackets, whitespace. So "equal under that surface" does NOT mean "differ
    # only in accent". Measured on the first doubly-read leaf, BOTH readers recorded zero
    # accent marks, so every difference there was punctuation or spacing; a status line
    # saying they "differ only in accent marking" would have asserted a cause that was not
    # merely unverified but false. Accent equality is therefore tested FIRST and on its
    # own, and the broader surface is reported as what it is.
    if strip_vedic_accents(_nfc(left_text)) == strip_vedic_accents(_nfc(right_text)):
        return (
            "VERIFIED_WITH_ORTHOGRAPHIC_NOTE",
            "the two readings are identical once Vedic accents are removed, so they agree "
            "on the reading and differ only in accentuation",
        )

    left_bare = comparison_form(left_text, ComparisonForm.ACCENT_STRIPPED_COMPARISON)
    right_bare = comparison_form(right_text, ComparisonForm.ACCENT_STRIPPED_COMPARISON)
    if left_bare == right_bare:
        return (
            "VERIFIED_WITH_ORTHOGRAPHIC_NOTE",
            "the two readings agree on the letters but differ in editorial marks, "
            "punctuation, numerals or spacing; which of those it is has not been "
            "attributed, so the note says only what was measured",
        )

    return (
        "TRANSCRIPTION_UNCERTAIN",
        "the two independent readings differ beyond accentuation; both are preserved "
        "and neither is selected",
    )


def reconcile() -> dict[str, object]:
    stage1 = _load_stage(STAGE1)
    stage2 = _load_stage(STAGE2)
    stage3 = _load_stage(STAGE3)

    coordinates = sorted(set(stage1) | set(stage2))
    rows: list[dict[str, object]] = []
    status_counts: Counter[str] = Counter()

    for key in coordinates:
        left, right = stage1.get(key), stage2.get(key)
        status, detail = _classify(left, right)

        adjudication = stage3.get(key)
        if adjudication is not None:
            status = str(adjudication["transcription_status"])
            detail = f"stage 3 adjudication: {adjudication.get('notes') or 'no note recorded'}"

        anchor = adjudication or left or right
        assert anchor is not None

        # When two readings disagree and nothing has adjudicated them, there is no agreed
        # text -- so the field that would carry one is NULL. It previously held stage 1's
        # reading while the row's own detail said "neither is selected", which silently
        # elected stage 1 by position. Both readings stay available in stage1_text and
        # stage2_text; what is absent is any claim that one of them is the reading.
        unresolved = status == "TRANSCRIPTION_UNCERTAIN" and adjudication is None
        text = "" if unresolved else str(anchor["text_devanagari"])

        row: dict[str, object] = {
            "schema_version": "1.0.0",
            "transcription_policy": "bsb-1856-devanagari-v1",
            "mdz_image_id": anchor["mdz_image_id"],
            "canvas_index": anchor["canvas_index"],
            "printed_page": anchor.get("printed_page"),
            "kanda": key[0],
            "sukta": key[1],
            "mantra": key[2],
            "paryaya": anchor.get("paryaya"),
            "unclear_count": text.count(UNCLEAR),
            "structural_marker": anchor.get("structural_marker"),
            "spans_canvases": anchor.get("spans_canvases"),
            "transcription_status": status,
            "reconciliation_detail": detail,
            "text_devanagari": None if unresolved else text,
            "release_eligible": (
                status in RELEASE_ELIGIBLE
                and not unresolved
                and (has_vedic_accents(text) or not REQUIRE_ACCENT_FOR_RELEASE)
            ),
            "stage1_text": None if left is None else left["text_devanagari"],
            "stage2_text": None if right is None else right["text_devanagari"],
            "stage3_text": None if adjudication is None else adjudication["text_devanagari"],
            "transcriber": None if left is None else left.get("transcriber"),
            "verifier": None if right is None else right.get("transcriber"),
            "adjudicator": None if adjudication is None else adjudication.get("adjudicator"),
        }
        rows.append(row)
        status_counts[status] += 1

    OUT.mkdir(parents=True, exist_ok=True)
    for existing in OUT.glob("leaf_*.jsonl"):
        existing.unlink()
    by_leaf: dict[int, list[dict[str, object]]] = {}
    for row in rows:
        by_leaf.setdefault(int(str(row["canvas_index"])), []).append(row)
    for canvas, leaf_rows in sorted(by_leaf.items()):
        path = OUT / f"leaf_{canvas:05d}.jsonl"
        leaf_rows.sort(key=lambda item: (item["kanda"], item["sukta"], item["mantra"]))
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            for row in leaf_rows:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
                handle.write("\n")

    # The 1856 edition IS accented, so a reading carrying no accent mark at all has lost
    # a real feature of the source even when two readers agree. That is invisible to the
    # per-unit statuses -- agreement on an unaccented reading still reads as agreement --
    # so it is measured separately here and reported as a fidelity gap.
    accented_units = sum(1 for row in rows if has_vedic_accents(str(row["text_devanagari"] or "")))

    agreed = status_counts["VERIFIED_EXACT"]
    both_read = sum(1 for key in coordinates if key in stage1 and key in stage2)
    summary: dict[str, object] = {
        "policy": "bsb-1856-devanagari-v1",
        "leaves_stage1": len({row["canvas_index"] for row in stage1.values()}),
        "leaves_stage2": len({row["canvas_index"] for row in stage2.values()}),
        "leaves_reconciled": len(by_leaf),
        "units_stage1": len(stage1),
        "units_stage2": len(stage2),
        "units_total": len(coordinates),
        "units_read_by_both": both_read,
        "units_read_by_one_only": len(coordinates) - both_read,
        "exact_agreement_rate_over_units_read_by_both": (
            round(agreed / both_read, 4) if both_read else None
        ),
        "status_counts": dict(sorted(status_counts.items())),
        "release_eligible_units": sum(1 for row in rows if row["release_eligible"]),
        "kandas_present": sorted({int(str(row["kanda"])) for row in rows}),
        "unclear_marks_total": sum(int(str(row["unclear_count"])) for row in rows),
        "units_carrying_any_vedic_accent": accented_units,
        "accent_fidelity_gap": len(rows) - accented_units,
        "accent_fidelity_note": (
            "The printed source marks accent throughout. Units carrying none have dropped "
            "a real feature of the page, which two agreeing readers cannot detect between "
            "them. This figure is the accent-reproduction gap and is NOT covered by "
            "VERIFIED_EXACT."
        ),
        "note": (
            "VERIFIED_EXACT is assigned only by agreement between two independent readings "
            "of the same page image. No reading is ever synthesised from two disagreeing "
            "ones: under RIGHTS-13 a merged reading has no traceable source."
        ),
    }
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    with SUMMARY.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
        handle.write("\n")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    summary = reconcile()
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
