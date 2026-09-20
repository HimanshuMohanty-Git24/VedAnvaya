#!/usr/bin/env python3
"""Correct the 39 withheld reasons Gate C disproved -- by overlay, not in place.

WHAT GATE C FOUND. 708 Samavedic verses are withheld from the notation release. Each one
carries a reason, and two of those reasons make a falsifiable claim about the witness:

    NO_NEAR_LINE_PROBABLE_ABSENCE (109 rows)
        "No line on the accented page comes within 0.90 similarity; the accented witness
         plausibly does not carry this verse at all."

    NEAR_LINE_EXISTS_WITNESS_DISAGREEMENT (599 rows)
        "A near line exists at ratio >= 0.90, so this is a witness disagreement (sandhi,
         pluti or an inline editorial bracket), not an absence -- it needs philological
         adjudication, not another source."

For **39** of them both claims are false, and this repository is enough to show it: the
verse's exact normalised text is RELEASED, with notation, on a coreferent twin elsewhere in
the corpus. The witness demonstrably carries that text. It is neither absent from the page
nor philologically different from ours.

THE MECHANISM, MEASURED RATHER THAN GUESSED. 202 canonical texts repeat, and in 153 of those
groups EVERY member is released -- so the witness does print a repeated verse more than once
and the harvest does find both lines. Where only one member is released, the single
order-consistent occurrence was assigned to the earlier verse and the later one had no line
left to claim. That is line exhaustion on a coreferent repeat, which is a third kind of
withholding and needs its own name.

WHAT THIS DOES NOT DO. No row moves from withheld to released, and no notation value is
invented. A twin's marks belong to the coordinate the witness printed them at; copying them
onto another verse because the consonants agree would be manufacturing source-explicit data,
which is the one thing the owner decision forbids outright. All 39 stay withheld. Only the
stated reason changes, and the original is preserved on every corrected row.

WHY AN OVERLAY AND NOT AN EDIT. ``data/staging/samaveda_music/`` is a tracked, sealed
artifact: ``manifest.json`` carries a sha256 per file and Gate A's ``manifest.file_checksums``
check verifies all twelve. The generator that produced it is not in this repository, so an
in-place edit could not be re-derived and would destroy the witness record it replaced. This
project has settled that question once already -- fix by overlay outside the seal, never in
place.

Usage:
    python data/staging/samaveda_music_002_final/build_withheld_reason_overlay.py
"""

from __future__ import annotations

import collections
import datetime
import hashlib
import json
import pathlib
import re
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parents[3]
STAGING = ROOT / "data" / "staging" / "samaveda_music"
CANONICAL = ROOT / "data" / "canonical" / "samaveda_arcika_v1"
OUT = ROOT / "data" / "staging" / "samaveda_music_002_final" / "withheld_reason_overlay.json"

ORIGINAL_CLASSES = {
    True: "NEAR_LINE_EXISTS_WITNESS_DISAGREEMENT",
    False: "NO_NEAR_LINE_PROBABLE_ABSENCE",
}
CORRECTED_CLASS = "WITNESS_OCCURRENCE_CONSUMED_BY_A_COREFERENT_REPEAT"
CORRECTED_REASON = (
    "The accented witness DOES carry this verse's text -- it is released, with notation, on "
    "a coreferent twin at another coordinate in this corpus. What it does not carry is a "
    "second order-consistent occurrence for this coordinate: the one available line was "
    "assigned to the twin. Withheld because notation belongs to the coordinate the source "
    "printed it at, and copying the twin's marks here would be inventing source-explicit "
    "data. This is not an absence from the witness and not a philological disagreement."
)

# The independent normalisation, identical in effect to Gate C's segmentation-invariant
# reading. Kept local rather than imported from the gate so this file can be read on its own.
DEVANAGARI_EXTENDED = range(0xA8E0, 0xA900)
VEDIC_EXTENSIONS = range(0x1CD0, 0x1D00)
SPACING_CANDRABINDU = frozenset({"ꣲ", "ꣳ"})
ANUSVARA = "ं"
# RUF001 is suppressed deliberately: the class is MEANT to hold the real Devanagari danda,
# digits and curly quotes, because those are the characters the witness prints.
DROPPED = re.compile(
    r"[\s।॥\d०-९\.\,\;\:\-–—"  # noqa: RUF001
    r"\(\)\[\]\{\}\'\"‘’“”\|/\*\?\!]"  # noqa: RUF001
)


def is_tone(char: str) -> bool:
    codepoint = ord(char)
    if codepoint == 0x0301:
        return False
    if codepoint not in DEVANAGARI_EXTENDED and codepoint not in VEDIC_EXTENSIONS:
        return False
    return unicodedata.category(char) == "Mn"


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = "".join(ANUSVARA if c in SPACING_CANDRABINDU else c for c in text)
    text = "".join(c for c in text if not is_tone(c))
    text = text.replace("म्", ANUSVARA).replace("न्", ANUSVARA)
    return unicodedata.normalize("NFC", DROPPED.sub("", text))


def load(path: pathlib.Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> None:
    passage_key = {
        r["entity_id"]: r["canonical_key"]
        for r in load(CANONICAL / "passages.jsonl")
        if r["entity_type"] == "MANTRA"
    }
    canonical = {}
    for record in load(CANONICAL / "text_versions.jsonl"):
        key = passage_key.get(record["passage_id"])
        if key:
            canonical[key] = normalise(record["text_nfc"])

    notation = [
        r for r in load(STAGING / "rows.jsonl") if r["payload"]["layer"] == "ARCIKA_NOTATION"
    ]
    released = {r["canonical_key"] for r in notation}
    withheld = {
        r["canonical_key"]: r
        for r in load(STAGING / "rejected.jsonl")
        if r["disposition"] == "UNRESOLVED" and r["kind"] == "ARCIKA_NOTATION"
    }

    groups: dict[str, list[str]] = collections.defaultdict(list)
    for key, text in canonical.items():
        groups[text].append(key)

    corrections = []
    for key in sorted(withheld):
        row = withheld[key]
        twins = [k for k in groups[canonical[key]] if k != key and k in released]
        if not twins:
            continue
        original = ORIGINAL_CLASSES[row["nearest_accented_line_similarity_at_least_0_90"]]
        corrections.append(
            {
                "canonical_key": key,
                "disposition": "WITHHELD",
                "disposition_unchanged": True,
                "original_class": original,
                "original_reason_verbatim": row["reason"],
                "corrected_class": CORRECTED_CLASS,
                "corrected_reason": CORRECTED_REASON,
                "released_coreferent_twins": sorted(twins),
                "evidence": (
                    "The normalised canonical text of this verse is byte-identical to that "
                    f"of {sorted(twins)[0]}, which is released with source-supplied "
                    "notation. Normalisation re-derived independently of the staging "
                    "pipeline from the manifest's declared spec."
                ),
            }
        )

    artifact = {
        "artifact": "SAMAVEDA_NOTATION_WITHHELD_REASON_OVERLAY",
        "at": datetime.datetime.now(datetime.UTC).isoformat(),
        "found_by": "scripts/samaveda_music_gate_c.py check "
        "independent.the_withheld_reason_survives_its_own_falsification",
        "first_failing_run": (
            "data/staging/samaveda_music_002_final/gate_c_run1.json (39 defects)"
        ),
        "why": (
            "39 of the 708 withheld verses stated a reason this repository disproves: their "
            "exact text is released, with notation, on a coreferent twin, so the witness "
            "does carry it. The true mechanism is line exhaustion on a repeat. Corrected by "
            "overlay because the staging directory is a tracked, checksum-sealed artifact "
            "whose generator is not in this repository."
        ),
        "seals_respected": {
            "staging_directory_untouched": True,
            "manifest_checksums_still_valid": True,
            "original_reason_preserved_on_every_corrected_row": True,
        },
        "what_did_not_change": {
            "rows_moving_from_withheld_to_released": 0,
            "notation_values_invented": 0,
            "released_population": len(released),
            "withheld_population": len(withheld),
        },
        "declared_class_vocabulary": [
            "NEAR_LINE_EXISTS_WITNESS_DISAGREEMENT",
            "NO_NEAR_LINE_PROBABLE_ABSENCE",
            CORRECTED_CLASS,
        ],
        "corrections": corrections,
        "counts": {
            "corrected": len(corrections),
            "by_original_class": dict(
                collections.Counter(c["original_class"] for c in corrections)
            ),
            "withheld_after_correction": {
                "NEAR_LINE_EXISTS_WITNESS_DISAGREEMENT": sum(
                    1
                    for k, r in withheld.items()
                    if r["nearest_accented_line_similarity_at_least_0_90"]
                    and k not in {c["canonical_key"] for c in corrections}
                ),
                "NO_NEAR_LINE_PROBABLE_ABSENCE": sum(
                    1
                    for k, r in withheld.items()
                    if not r["nearest_accented_line_similarity_at_least_0_90"]
                    and k not in {c["canonical_key"] for c in corrections}
                ),
                CORRECTED_CLASS: len(corrections),
            },
        },
    }

    body = json.dumps(artifact, indent=2, ensure_ascii=False)
    OUT.write_text(body + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"  corrections           {len(corrections)}")
    print(f"  by original class     {artifact['counts']['by_original_class']}")
    print(f"  after correction      {artifact['counts']['withheld_after_correction']}")
    print(f"  sha256                {hashlib.sha256(body.encode('utf-8')).hexdigest()}")


if __name__ == "__main__":
    main()
