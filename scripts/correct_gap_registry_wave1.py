#!/usr/bin/env python3
"""Owner decision G: separate what a gap IS from what we guessed and then measured.

A registry entry is a hypothesis about causation until someone measures it. Several of the
original hypotheses were wrong, and two prescribed remedies were disproven -- so leaving
them in place would send Wave 3 to acquire material we already hold.

Adds four fields to every entry Wave 1 measured:

  observed_gap    what is actually missing or wrong, stated without a theory of why
  suspected_cause the original hypothesis, kept verbatim so the correction is legible
  measured_cause  what measurement established, with the figure
  closure_method  what actually closes it, replacing any disproven prescription

The original `root_cause` text is preserved in `suspected_cause` rather than overwritten.
A campaign that quietly rewrites its own wrong guesses loses the ability to learn which
kinds of guess it gets wrong -- and this one got the same kind wrong four times: it assumed
absence at the source where the defect was in our own addressing.
"""

from __future__ import annotations

import json
import pathlib

REGISTRY = pathlib.Path("data/gap_registry.json")

CORRECTIONS: dict[str, dict[str, str]] = {
    "GAP-AUDIO-002": {
        "observed_gap": (
            "1,159 of 5,839 Atharvavedic verses had no catalogued recitation. Of those, 495 "
            "were recorded text_mismatch, 420 no_source_verse and 244 source_has_no_audio."
        ),
        "measured_cause": (
            "A coordinate-system mismatch, not a text problem. VedSearch divides the "
            "Atharvaveda into 754 suktas where our Berlin (Roth and Whitney 1856) division "
            "has 731 -- the 23 extra sitting in kandas 7, 9, 11, 12 and 13, verified against "
            "our side at 118, 10, 10, 5 and 4. Keys were mapped straight through, so past "
            "the first split within a kanda the coordinate addressed the wrong verse, and in "
            "the paryaya books a verse offset of up to +61 rides along with it. The text "
            "refusals were correct; the address was wrong. 494 of the 495 are this one "
            "cause, and no_source_verse was the same defect rather than a different one."
        ),
        "closure_method": (
            "Per-verse re-establishment against the source's own division: 607 rows by "
            "unique letter identity across all 5,916 source rows, 9 by position "
            "disambiguation, 109 as orthographic variants adjacent to a letter-identical "
            "anchor. 740 of 915 refusals closed, taking the Atharvaveda from 80.1% to 93.2%. "
            "A further 197 are reachable but blocked on a record-model decision: each has a "
            "contiguous run of 2-3 Vedavani files whose concatenation is letter-identical to "
            "the mantra, and the model permits one media_url per record."
        ),
        "disproven_prescription": (
            "The original entry prescribed re-running with accent- and sandhi-insensitive "
            "matching. skeleton() already was both, and re-running changed 1 of 495. The "
            "entry also claimed the 420 no_source_verse needed another source; 385 were in "
            "VedSearch all along. Both are withdrawn."
        ),
    },
    "GAP-AUDIO-003": {
        "observed_gap": (
            "223 of 1,975 Madhyandina verses had no catalogued recitation: 190 "
            "found-with-no-audio, 33 found-and-rejected-on-text, 0 never searched, 0 absent "
            "at source."
        ),
        "measured_cause": (
            "For the 33, our own comparator. difflib's autojunk heuristic discarded nearly "
            "the whole alphabet on any skeleton over 200 characters -- 17 of 18 distinct "
            "letters on a measured 285-character case -- and a visarga typed as an ASCII "
            "colon was dropped as a non-letter while the Devanagari sign survived as 'h'. "
            "For 30 of the 33 the coordinate-aligned row was already the global best match. "
            "For the 190, the source publishes no verse-level audio."
        ),
        "closure_method": (
            "Comparator fixed at commit 30ba692 with four regression tests, closing 25 of "
            "the 33 with no acquisition. The remaining 8 are source-side text defects and "
            "need a listener. The 190 are BLOCKED_RIGHTS_AND_GRANULARITY rather than "
            "source-unavailable: IGNCA publishes Madhyandina per adhyaya at "
            "Shukla_Yajurveda_Madhyandin_MP3/SYMS_CHAP_NN.mp4, verified answering 206 for "
            "adhyayas 1-40 and 404 at 41. The remedy is a permission request plus verified "
            "segmentation, not commissioning a reciter."
        ),
    },
    "GAP-AUDIO-004": {
        "observed_gap": (
            "150 of 10,552 Rigvedic verses had no catalogued recitation: 70 where the "
            "source's own row carries audio.sanskrit false, and 80 being RV 8.49.1-8.59.7, "
            "the Valakhilya. Zero text_mismatch."
        ),
        "measured_cause": (
            "A source dependency. The incumbent source publishes the 1,017-hymn "
            "presentation -- 10,472 verses, Mandala 8 stopping at hymn 92 -- so the "
            "transform's target 8.93 has never existed there. Re-probed live: sukta 93 "
            "returns total_shloks 0 while sukta 92 returns rows. The 70 are a shared "
            "lacuna rather than a harvest failure: an independent Archive parayana set by a "
            "different uploader marks its own tracks incomplete at the same places, "
            "covering 66 of the 70."
        ),
        "closure_method": (
            "All 150 from VedaWeb's per-stanza Kirchheiner recitation, measured at 10,552 of "
            "10,552 over one contiguous range, so no segmentation was needed and no "
            "timestamp is asserted. The Valakhilya mapping was tested acoustically as well "
            "as textually: duration against syllable count correlates at 0.871 as mapped "
            "and 0.088 under the Griffith eleven-hymn shift."
        ),
        "disproven_prescription": (
            "The original entry stated the Griffith permutation 'was never applied' and set "
            "source_dependency to NONE. Both halves are wrong. The permutation IS applied -- "
            "vedsearch_coordinates routes through griffith_page, it is stated on all 16,834 "
            "catalogue rows, and the audit shows our 8.60 mapping to source 8.49 "
            "text-confirmed. And it was a source dependency throughout. Withdrawn."
        ),
    },
    "GAP-TRANSLATION-003": {
        "observed_gap": "72 of 1,975 Madhyandina mantras had no translation.",
        "measured_cause": (
            "39 of the 72 were never missing. The stage file's own gap labels decompose as "
            "39 LABEL_NOT_PRINTED, 21 spine divergence and 12 printed omission, and "
            "re-parsing the pinned snapshots shows the 39 are digit-confusion OCR of the "
            "printed verse label -- '22 23 24 23 26' for 25, '84 S5 85 87' for 84/85/86 -- "
            "with the translated text present throughout. Adhyaya 23.20-31 is by contrast a "
            "true omission: Griffith printed a row of ellipsis dots."
        ),
        "closure_method": (
            "Recovery by forced interpolation between bindings the shipped pipeline already "
            "made, controlled against all 1,889 existing EXACT bindings with zero "
            "regressions. A first attempt recovered 60 while silently re-binding 53 verses "
            "of adhyaya 12 by one place; the regression guard caught it, which is the only "
            "reason the figure is trustworthy. Owner decision C then ruled the 31 rows "
            "lacking independent content control ineligible, so accepted recovery is 19."
        ),
    },
    "GAP-TRANSLATION-002": {
        "observed_gap": (
            "961 of 5,839 Saunaka mantras had no translation, 958 of them the whole of "
            "kanda 20 plus exactly three strays at AVS 3.9.4, 5.12.11 and 10.8.30."
        ),
        "measured_cause": (
            "Both incumbent Atharvavedic sources omit kanda 20 for the same "
            "Whitney-related reason, so it was a single source dependency rather than 961 "
            "separate absences."
        ),
        "closure_method": (
            "944 of 961 from Griffith's Hymns of the Atharvaveda via the Internet Archive "
            "Wayback Machine, sacred-texts.com being 403 behind a Cloudflare bot challenge "
            "rather than merely unreachable. 923 direct including all three strays, and 21 "
            "by the permitted cross-corpus route at surface identity of exactly 1.0 citing "
            "both keys."
        ),
    },
    "GAP-TRANSLATION-004": {
        "observed_gap": "50 of 10,552 Sakala mantras had no translation.",
        "measured_cause": (
            "30 of the 50 are not a source gap. They are the unbound halves of RV 1.65-1.70, "
            "where Griffith renders each pair of our verses as one merged unit -- so no "
            "printed unit addresses them individually, and the 25 units that ARE bound in "
            "that span sit on the wrong verses. The gap was the visible symptom of a "
            "misalignment, which is why reading it as a gap hid the defect. See "
            "GAP-TRANSLATION-006."
        ),
        "closure_method": (
            "13 closed conventionally. The 30 are barred from import until the coordinate "
            "repair is verified, per owner decision A: filling the span first would leave "
            "every verse carrying text and 25 carrying the wrong text."
        ),
    },
    "GAP-AUDIO-001": {
        "observed_gap": (
            "0 of 1,844 Kauthuma arcika verses have catalogued audio. Re-confirmed as a "
            "VERIFIED ZERO over an assessed population of 1,844, not an unknown."
        ),
        "measured_cause": (
            "Not an absence of Samavedic recording, but an absence of arcika *verse* "
            "recording. 475 licence-clean Ogg files exist on Wikimedia Commons -- 459 CC "
            "BY-SA 4.0, 16 CC0 -- and all 475 are now fetched and checksummed at "
            "808,529,118 bytes over 19.1 hours. But every one is PAGE_LEVEL, only 6 of 475 "
            "touch arcika pages at all, and they are gana performances rather than arcika "
            "recitation. The source-provided cue index is real and legible but handwritten "
            "with no text layer, and it anchors rather than segments: one page carries six "
            "cues for seven ganas, another five ganas and one cue."
        ),
        "closure_method": (
            "Not closable as arcika verse audio from present material. What the 475 files "
            "support is a gana performance layer at container scope, staged as 3 rows with "
            "start_seconds null -- never at a verse. The open route is the LOAR deposit: 224 "
            "cassettes, four Vedas, six oral traditions, named reciters including two "
            "Samavedic. Owner decision D makes it a priority investigation and forbids "
            "claiming any coverage from it until each item is classified."
        ),
        "disproven_prescription": (
            "Wave 0 partly rested this gap on every candidate having an unnamed reciter. "
            "The LOAR deposit names its reciters, so that reasoning is withdrawn -- without "
            "any claim that the material is arcika, which is not established."
        ),
    },
}


def main() -> int:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    by_id = {g["gap_id"]: g for g in registry["gaps"]}

    missing = [gid for gid in CORRECTIONS if gid not in by_id]
    if missing:
        print(f"REFUSING: unknown gap ids {missing}")
        return 1

    for gid, fields in CORRECTIONS.items():
        gap = by_id[gid]
        gap["observed_gap"] = fields["observed_gap"]
        # Preserve the original hypothesis verbatim rather than overwriting it.
        gap["suspected_cause"] = gap.get("root_cause", "")
        gap["measured_cause"] = fields["measured_cause"]
        gap["closure_method"] = fields["closure_method"]
        if "disproven_prescription" in fields:
            gap["disproven_prescription"] = fields["disproven_prescription"]
        gap["causation_status"] = "MEASURED"

    for gap in registry["gaps"]:
        gap.setdefault("causation_status", "SUSPECTED_NOT_YET_MEASURED")

    registry["gaps"].sort(key=lambda g: str(g["gap_id"]))
    REGISTRY.write_text(
        json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )

    measured = sum(1 for g in registry["gaps"] if g["causation_status"] == "MEASURED")
    withdrawn = sum(1 for g in registry["gaps"] if "disproven_prescription" in g)
    print(f"corrected {len(CORRECTIONS)} entries")
    print(f"causation MEASURED: {measured} of {len(registry['gaps'])}")
    print(f"disproven prescriptions withdrawn: {withdrawn}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
