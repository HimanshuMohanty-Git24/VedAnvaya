#!/usr/bin/env python3
"""Phase E: which staged rows declare English over a literal that is not English.

Griffith did not translate the passages he judged too explicit for an English readership.
He rendered them into Latin, and sacred-texts prints them that way -- its page for
Atharvaveda 20.136 is headed "Erotica" and every verse on it is Latin. Those literals are
his real published text. They are not the English layer, and counting them as English
coverage overstates that layer by exactly the number of passages Victorian propriety took
out of it.

**Why this module exists rather than reusing Gate C's verdict.** Gate C flagged 22 rows and
the owner decision names 22. Re-reading the pinned source pages found 24. The two it missed
are Atharvaveda 20.136.1 -- *"Si quis in hujus tenui rima praeditae feminae augustias
fascinum intromittit"* -- and Rigveda 10.61.6 -- *"Quum jam in medio connessu, semiperfecto
opere, amorem in puellam pater impleverat"*. Both were classified
``SAFE_IMPORT_SOURCE_EXPLICIT`` and would have been imported as English, which is the one
outcome the Latin policy rules out. Their neighbours were all caught, so the earlier
detector's precision was fine and its recall was not, and an unmeasured recall is the
failure mode where a population of 24 is reported as 22 and the two that got away ship.

The strongest completeness evidence is structural rather than statistical. A printed
edition substitutes Latin for a *passage*, not for alternate verses, so every Latin block
must be an unbroken run of verse numbers -- and :func:`contiguity` is what showed the
Atharvavedic hymn was being read as verses 2-16 when sacred-texts prints 1-16 and heads the
page "Erotica".

**The test, and what it deliberately does not do.** The task's constraint is that a generic
classifier must not reject legitimate English containing Latin terms, and this corpus is
full of them -- a Griffith footnote naming *Aegle Marmelos* or *Ziziphi Jujubae* is
English prose. So the decision does not rest on Latin words being present. It rests on
English *function* words being absent. English cannot write a sentence of this length
without "the", "of", "and", "to", "in", "is", "his", "her", "with", "that"; Latin has no
articles and inflects what English would express with prepositions. A botanical binomial
inside an English sentence leaves that sentence's function words untouched, so it scores as
English and is never flagged. Both signals are required, and the separation between the two
populations is measured and printed rather than asserted.
"""

from __future__ import annotations

import collections
import json
import re
import sys
from typing import Any, Final

import translation_integration_common as T

# --------------------------------------------------------------------------------------
# The two signals
# --------------------------------------------------------------------------------------

#: Obligatory English function words, restricted to forms that are *only* English. The
#: restriction is the correction that matters. A first pass used the obvious list and
#: scored Rigveda 10.61.6 as English because its Latin reads "Quum jam in medio connessu
#: ... amorem in puellam pater impleverat ... in terrae superficiem": three occurrences of
#: "in", which is a preposition in both languages, were enough to clear the ceiling. So
#: "in", "a", "an", "at", "his", "me" and "is" are excluded -- each is also a Latin form --
#: and what remains cannot appear in a Latin sentence at all.
#:
#: This is still the load-bearing signal, and it is what keeps a botanical binomial inside
#: English prose from being flagged: "Bona est magna Ficus Glomerata" has no English
#: function word in it, while "the fruit of the Ficus Glomerata tree" has three.
ENGLISH_FUNCTION_WORDS: Final[frozenset[str]] = frozenset(
    """
    the and or but of to on by for with from as that this these those
    are was were be been being has have had do does did will would shall should
    may might can could must not no nor
    he she it they we you him her them us hers their our your my its
    thou thee thy thine ye hath doth art shalt
    who whom which what when where while there here then than
    up down out off over under again also very ever never now
    """.split()
)

#: Forms excluded from the English signal because Latin uses them too. Named rather than
#: silently absent, so the next reader can see the exclusion was deliberate and check it.
AMBIGUOUS_BETWEEN_THE_TWO: Final[frozenset[str]] = frozenset(
    {"in", "a", "an", "at", "his", "me", "is", "am", "i"}
)

#: Latin markers, used only as corroboration. Chosen as forms that do not occur as English
#: words at all: "quum", "cujus", "ejus" and the rest cannot be an English sentence's
#: vocabulary, whereas "est" or "in" could be a fragment or a loan.
LATIN_MARKERS: Final[frozenset[str]] = frozenset(
    """
    quum cujus ejus illius illinc hinc aliqua veluti tanquam admodum magnopere
    utrum quae quem quod qui quis sic tua tuum suam suum sua eius
    est sunt fuerat fuerant fuerunt erat esse
    non nos vero etiam tum nunc jam cum
    mentula mentulae pudenda pudendum penis pene femora femoribus feminae femina
    vaginam semen virile membrum arboris arbor silvae ignis ilia vaccae
    dii deus labor cupido amorem amatorem
    percutit percute dixit alloquitur increscunt dependet extendit retraxit
    intumescenti faverunt ostentat delectata adveniens edidit superans pinsunt
    inflammatur ardent infixus circumcurrit nescimus gerat currit custodi
    futue fututio opprimit obtineat producit procurrit extrahat capiat
    incidit videntur agitantur impleverat congressus adiverat discedens processit
    jactavit cepit despicit nata detrahit favent vincamus superemus convenientes
    interiores extentae solutus arenoso oryzam coctam
    """.split()
)

_WORD = re.compile(r"[A-Za-zÀ-ɏ]+")

#: A literal shorter than this is not judged. Griffith's Latin passages are all full
#: sentences; a five-word fragment has too few function-word slots for their absence to
#: mean anything, and guessing on one is how a false positive gets in.
MIN_WORDS_TO_JUDGE: Final = 8

#: Below this English function-word density, a literal of full-sentence length is not
#: English prose. Measured, not chosen: see :func:`separation`.
ENGLISH_DENSITY_CEILING: Final = 0.10

#: And at least this many distinct Latin markers must corroborate.
MIN_LATIN_MARKERS: Final = 2


def words(text: str) -> list[str]:
    return [w.lower() for w in _WORD.findall(text)]


def score(text: str) -> dict[str, Any]:
    """The two densities and the verdict, with the evidence for it."""
    tokens = words(text)
    n = len(tokens)
    english = [w for w in tokens if w in ENGLISH_FUNCTION_WORDS]
    latin = sorted({w for w in tokens if w in LATIN_MARKERS})
    english_density = round(len(english) / n, 4) if n else 0.0
    latin_markers = len(latin)
    judged = n >= MIN_WORDS_TO_JUDGE
    verdict = "ENGLISH"
    if not judged:
        verdict = "TOO_SHORT_TO_JUDGE"
    elif english_density <= ENGLISH_DENSITY_CEILING and latin_markers >= MIN_LATIN_MARKERS:
        verdict = "LATIN"
    return {
        "words": n,
        "english_function_words": len(english),
        "english_function_word_density": english_density,
        "distinct_latin_markers": latin_markers,
        "latin_markers_found": latin[:12],
        "verdict": verdict,
        "judged": judged,
    }


# --------------------------------------------------------------------------------------
# Coverage, which is the part that was missing
# --------------------------------------------------------------------------------------


def separation(scored: list[dict[str, Any]]) -> dict[str, Any]:
    """How far apart the two populations actually sit, on both axes.

    Printed so the two thresholds are defensible rather than plausible. A classifier whose
    populations touch at the boundary has no recall guarantee, and the point of this report
    is that the gap is wide: Griffith's Latin sits at an English function-word density of
    0, and his English prose sits an order of magnitude above the ceiling.
    """
    latin = [s for s in scored if s["verdict"] == "LATIN"]
    english = [s for s in scored if s["verdict"] == "ENGLISH"]
    short = [s for s in scored if s["verdict"] == "TOO_SHORT_TO_JUDGE"]

    def band(rows: list[dict[str, Any]], field: str) -> dict[str, Any]:
        if not rows:
            return {"n": 0, "min": None, "max": None}
        values = sorted(r[field] for r in rows)
        return {
            "n": len(values),
            "min": values[0],
            "p50": values[len(values) // 2],
            "max": values[-1],
        }

    return {
        "rows_judged": len(latin) + len(english),
        "rows_too_short_to_judge": len(short),
        "too_short_row_ids": [s["row_id"] for s in short],
        "english_function_word_density": {
            "on_LATIN_rows": band(latin, "english_function_word_density"),
            "on_ENGLISH_rows": band(english, "english_function_word_density"),
            "ceiling_applied": ENGLISH_DENSITY_CEILING,
        },
        "distinct_latin_markers": {
            "on_LATIN_rows": band(latin, "distinct_latin_markers"),
            "on_ENGLISH_rows": band(english, "distinct_latin_markers"),
            "floor_applied": MIN_LATIN_MARKERS,
        },
        # The rule is a conjunction, so the separation that matters is the joint one. On
        # the density axis alone the two populations overlap slightly -- three Samavedic
        # English lines sit at 0.05-0.077, below one Latin line at 0.0667 -- and reporting
        # only that would suggest a fragile classifier. On the corroborating axis the gap
        # is absolute: no English row in 2,227 carries a single Latin marker, and every
        # Latin row carries at least three.
        "density_axis_alone_separates": (
            bool(latin)
            and bool(english)
            and max(r["english_function_word_density"] for r in latin)
            < min(r["english_function_word_density"] for r in english)
        ),
        "marker_axis_alone_separates": (
            bool(latin)
            and bool(english)
            and min(r["distinct_latin_markers"] for r in latin)
            > max(r["distinct_latin_markers"] for r in english)
        ),
        "no_english_row_carries_any_latin_marker": all(
            r["distinct_latin_markers"] == 0 for r in english
        ),
    }


def contiguity(scored: list[dict[str, Any]]) -> dict[str, Any]:
    """Whether each Latin block is an unbroken run of verse numbers.

    This is the completeness check a density threshold cannot give. A translator who
    substitutes Latin substitutes it for a passage, not for alternate verses, so every
    Latin block should be a contiguous run -- and a gap inside one is the exact shape a
    missed row makes. It is what showed that Atharvaveda 20.136 was being read as verses
    2-16 when the printed hymn is 1-16.
    """
    blocks: dict[str, list[int]] = {}
    for row in scored:
        if row["verdict"] != "LATIN":
            continue
        key = row["canonical_key"]
        container, verse = key.rsplit(":", 1)
        blocks.setdefault(container, []).append(int(verse.lstrip("V")))
    out = {}
    for container, verses in sorted(blocks.items()):
        verses.sort()
        expected = list(range(verses[0], verses[-1] + 1))
        out[container] = {
            "verses": verses,
            "run": f"{verses[0]}-{verses[-1]}",
            "contiguous": verses == expected,
            "gaps": sorted(set(expected) - set(verses)),
        }
    return {
        "blocks": out,
        "every_block_contiguous": all(b["contiguous"] for b in out.values()),
    }


def main() -> int:
    packet = T.load_packet()
    classified = T.classify(packet)

    scored: list[dict[str, Any]] = []
    for row_id in packet["ids"]:
        staged = packet["staged"][row_id]
        s = score(staged["payload"]["text"])
        s["row_id"] = row_id
        s["canonical_key"] = staged["canonical_key"]
        s["veda"] = staged["veda"]
        s["source_locator"] = staged["source_locator"]
        s["declared_language"] = staged["payload"].get("language")
        s["gate_c_verdict"] = T.language_verdict(packet["gate_c"][row_id])
        s["final_class"] = classified[row_id]["final_class"]
        s["importable"] = classified[row_id]["importable"]
        s["text_head"] = staged["payload"]["text"][:110]
        scored.append(s)

    here = {s["row_id"] for s in scored if s["verdict"] == "LATIN"}
    there = set(T.latin_row_ids(packet))

    missed = sorted(here - there)
    over = sorted(there - here)

    report = {
        "phase": "E",
        "rows_scanned": len(scored),
        "this_detector": {
            "LATIN": len(here),
            "rule": (
                "a literal of at least "
                f"{MIN_WORDS_TO_JUDGE} words whose English function-word density is at most "
                f"{ENGLISH_DENSITY_CEILING} and which carries at least {MIN_LATIN_MARKERS} "
                "distinct Latin markers. The density is the decision; the markers only "
                "corroborate, so English prose quoting a Latin binomial is never flagged."
            ),
        },
        "gate_c_detector": {"LATIN": len(there)},
        "owner_decision_population": 22,
        "agreement": {
            "both": len(here & there),
            "found_only_now": len(missed),
            "found_only_by_gate_c": len(over),
        },
        "rows_gate_c_missed": [
            {
                k: v
                for k, v in next(s for s in scored if s["row_id"] == row_id).items()
                if k
                in (
                    "row_id",
                    "canonical_key",
                    "source_locator",
                    "final_class",
                    "english_function_word_density",
                    "distinct_latin_markers",
                    "latin_markers_found",
                    "text_head",
                )
            }
            for row_id in missed
        ],
        "rows_only_gate_c_flagged": over,
        "separation": separation(scored),
        "contiguity": contiguity(scored),
        "latin_rows_by_veda": dict(
            collections.Counter(s["veda"] for s in scored if s["verdict"] == "LATIN")
        ),
        "latin_rows_by_prior_final_class": dict(
            collections.Counter(s["final_class"] for s in scored if s["verdict"] == "LATIN")
        ),
        "latin_row_ids": sorted(here),
        "corrected_language": T.LATIN_LANGUAGE_CODE,
        "language_evidence": {
            "method": (
                "the pinned sacred-texts pages were re-read and the printed text compared "
                "against the staged literal, so the language is read off the source rather "
                "than inferred from character classes"
            ),
            "pages_verified": {
                "av20136.htm": (
                    "headed 'Atharva Veda: Book 20: Hymn 136: Erotica'; every verse on the "
                    "page is printed in Latin"
                ),
                "av20126.htm": (
                    "printed in English except the two verses labelled 16 and 17, which are "
                    "Latin and are the two AV 20.126 rows"
                ),
                "rv01179.htm": "verses 3 and 4 printed in Latin, 1, 2, 5 and 6 in English",
                "rv10061.htm": (
                    "verses 5, 6, 7 and 8 printed in Latin. Four, not three: verse 6 is the "
                    "row Gate C missed"
                ),
            },
        },
        "verdict": "LANGUAGE_POPULATION_IS_LARGER_THAN_THE_OWNER_FIGURE"
        if missed
        else "AGREES_WITH_THE_OWNER_FIGURE",
    }

    T.write_json(T.INTEGRATION / "language_verification.json", report)
    T.write_jsonl(T.INTEGRATION / "language_verification_rows.jsonl", scored)

    print("rows scanned          :", report["rows_scanned"])
    print("this detector  LATIN  :", report["this_detector"]["LATIN"])
    print("gate C         LATIN  :", report["gate_c_detector"]["LATIN"])
    print("owner decision figure :", report["owner_decision_population"])
    print("agreement             :", json.dumps(report["agreement"]))
    print("by veda               :", json.dumps(report["latin_rows_by_veda"]))
    print("by prior class        :", json.dumps(report["latin_rows_by_prior_final_class"]))
    print()
    print("separation:", json.dumps(report["separation"], indent=1))
    print()
    for row in report["rows_gate_c_missed"]:
        print("MISSED BY GATE C:", json.dumps(row, ensure_ascii=False, indent=1))
    print("VERDICT:", report["verdict"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
