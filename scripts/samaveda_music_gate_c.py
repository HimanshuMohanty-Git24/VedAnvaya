#!/usr/bin/env python3
"""Gate C for ``samaveda_music``: try to DISPROVE the notation claim.

Gate A asked whether the artifact is well formed. Gate B asked whether it means what it
says. This asks whether it is TRUE, and it is built to fail rather than to pass. The
campaign's own eligibility rule records why that matters, verbatim: "Four of four domains
adversarially tested so far have failed C, and two of those four had every aggregate count
survive."

WHAT MAKES THIS INDEPENDENT. The staging pipeline that produced the rows is not in this
repository, and nothing here re-uses any field it derived. In particular this gate never
reads ``payload.tone_stripped_text``. Its four evidence sources are:

    E1  data/canonical/samaveda_arcika_v1/{passages,text_versions}.jsonl
        The canonical arcika text, joined by ``passage_id`` -- read from the FILE, not from
        the graph's copy of it and not from the staging artifact.

    E2  m.running_samhita_number on the live graph
        The source's own printed running Samhita series, landed at R5 from a DIFFERENT
        citation system (WIKISOURCE_SA_RUNNING_SAMHITA_NUMBER). The notation artifact states
        in its own ``mapping_method`` that "The page's own printed numerals were NOT used to
        join", so this series is evidence the join never saw.

    E3  payload.notated_text_devanagari
        The witness string as harvested. Source data, not a derivation -- including the
        verse and section numerals the witness itself prints inside it.

    E4  The Unicode character database, via ``unicodedata``
        Used to decide what a Vedic tone mark IS, instead of the artifact's hard-coded
        integer ranges. Two different decision procedures reaching the same answer is the
        independence; re-running the artifact's own ranges would not be.

THE NORMALISATION IS RE-IMPLEMENTED FROM ITS WRITTEN SPECIFICATION, NOT IMPORTED. The
manifest declares four steps -- strip tone, fold U+A8F2/U+A8F3 to anusvara, drop
danda/space/digits/punctuation, fold nasal-virama to anusvara -- and they are coded here
from that sentence. Two readings of the fourth step are reported separately, because the
witness and our canonical text segment their words differently and a positional reading of
"word-final" is therefore not segmentation-invariant.

AND IT CARRIES ITS OWN NEGATIVE CONTROL, which is the part that makes the positive result
worth anything. A normalisation loose enough to match everything would score 1,136 of 1,136
and prove nothing, so the same comparison is run against the NEXT canonical verse. If the
shifted comparison also matched, the aligned result would be an artifact of the fold rather
than evidence about the witness.

Usage:
    python scripts/samaveda_music_gate_c.py [--json OUT] [--no-overlay]

Exit code is 1 if any check fails or if any check is below full coverage.
"""

from __future__ import annotations

import argparse
import collections
import datetime
import difflib
import itertools
import json
import pathlib
import random
import re
import unicodedata
from typing import Any

from neo4j import GraphDatabase, Query

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
STAGING = PROJECT_ROOT / "data" / "staging" / "samaveda_music"
ROWS = STAGING / "rows.jsonl"
REJECTED = STAGING / "rejected.jsonl"
CANONICAL = PROJECT_ROOT / "data" / "canonical" / "samaveda_arcika_v1"
PASSAGES = CANONICAL / "passages.jsonl"
TEXT_VERSIONS = CANONICAL / "text_versions.jsonl"
PASS_DIR = PROJECT_ROOT / "data" / "staging" / "samaveda_music_002_final"
OVERLAY = PASS_DIR / "withheld_reason_overlay.json"
OUT = PROJECT_ROOT / "data" / "staging" / "integration" / "samaveda_music_gate_c.json"

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "vedagraph_dev")
DB = "neo4j"
QUERY_TIMEOUT_SECONDS = 300.0

IN_SCOPE_LAYER = "ARCIKA_NOTATION"

#: Fixed before the sample is drawn and never changed afterwards. A sample redrawn after
#: seeing which rows fail is not a sample.
SEED = 20260918

#: The adversarial sample's size and shape, declared here rather than derived from the
#: result. 40 matches the size of the artifact's own adversarial sample -- which targeted
#: GANA_RENDERING and so never touched this population -- so the two are comparable.
SAMPLE_SIZE = 40
SAMPLE_STRATA = (
    ("repeated_text_and_no_printed_numeral", 10),
    ("shortest_normalised_text", 10),
    ("fewest_tone_marks", 10),
    ("first_or_last_notated_verse_of_a_collection", 5),
    ("seeded_random_from_the_remainder", 5),
)

# --- The declared normalisation, re-implemented from the manifest's own sentence ---------

#: Devanagari Extended and Vedic Extensions. The artifact names four integer ranges; this
#: gate names the two Unicode BLOCKS and then asks the character database whether each
#: codepoint is a non-spacing mark. U+0301 is excluded by hand for the reason the artifact
#: also excludes it: the IAST acute is both the sibilant diacritic and an udatta, and folding
#: it would make one indistinguishable from the other.
DEVANAGARI_EXTENDED = range(0xA8E0, 0xA900)
VEDIC_EXTENSIONS = range(0x1CD0, 0x1D00)
COMBINING_ACUTE = 0x0301

#: U+A8F2 and U+A8F3 are spacing candrabindu LETTERS, not marks. The declared normalisation
#: folds them to anusvara; the artifact's own note says they are excluded from the tone count
#: for exactly that reason.
SPACING_CANDRABINDU = frozenset({"ꣲ", "ꣳ"})
ANUSVARA = "ं"
VIRAMA = "्"
NASAL_VIRAMA = ("म्", "न्")  # ma+virama, na+virama

#: RUF001 is suppressed deliberately: the class is MEANT to hold the real Devanagari danda,
#: the real Devanagari digits and the real curly quotes, because those are the characters the
#: witness prints. Substituting the ASCII look-alikes ruff suggests would stop it matching.
DROPPED = re.compile(
    r"[\s।॥\d०-९\.\,\;\:\-–—"  # noqa: RUF001
    r"\(\)\[\]\{\}\'\"‘’“”\|/\*\?\!]"  # noqa: RUF001
)

#: A trailing run of the witness's own ``|| n ||`` numeral groups. The FIRST group is the
#: verse numeral; a SECOND, where present, closes the dasati. Reading only the last group
#: mistakes the section number for the verse number -- which is how a first pass at this
#: check invented a disagreement at UTTARA:P01:R01:D04:V03.
TRAILING_NUMERALS = re.compile(r"(?:।।\s*\d+\s*।।\s*)+$")
NUMERAL_GROUP = re.compile(r"।।\s*(\d+)\s*।।")
LOCATOR_LINE = re.compile(r"line (\d+)")

#: The corrected reason class this gate's own finding introduces. A withheld verse whose
#: exact text is released on a twin is neither absent from the witness nor a philological
#: disagreement: the witness carries the text, and the one order-consistent occurrence went
#: to a repeat of the same verse elsewhere in the corpus.
EXHAUSTION_CLASS = "WITNESS_OCCURRENCE_CONSUMED_BY_A_COREFERENT_REPEAT"
DECLARED_WITHHELD_CLASSES = (
    "NEAR_LINE_EXISTS_WITNESS_DISAGREEMENT",
    "NO_NEAR_LINE_PROBABLE_ABSENCE",
    EXHAUSTION_CLASS,
)


def is_vedic_tone_mark(char: str) -> bool:
    """Is this codepoint a Vedic cantillation mark, per the Unicode character database?"""
    codepoint = ord(char)
    if codepoint == COMBINING_ACUTE:
        return False
    if codepoint not in DEVANAGARI_EXTENDED and codepoint not in VEDIC_EXTENSIONS:
        return False
    return unicodedata.category(char) == "Mn"


def _strip_tone_and_fold_candrabindu(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = "".join(ANUSVARA if c in SPACING_CANDRABINDU else c for c in text)
    return "".join(c for c in text if not is_vedic_tone_mark(c))


def normalise_positional(text: str) -> str:
    """The declared fold read POSITIONALLY: nasal-virama at a word or clause boundary."""
    text = _strip_tone_and_fold_candrabindu(text)
    text = re.sub(r"(?:म्|न्)(?=\s|$|[।॥])", ANUSVARA, text)
    return unicodedata.normalize("NFC", DROPPED.sub("", text))


def normalise_segmentation_invariant(text: str) -> str:
    """The declared fold read as an EQUIVALENCE CLASS, independent of word segmentation.

    The witness writes ``मघवन् गविष्टय`` and our canonical text writes ``मघवन्गविष्टय``
    as one token, so "word-final" is not a property either side agrees on. Folding the
    nasal-virama unconditionally is segmentation-invariant. Whether that fold is too loose
    to mean anything is not argued -- it is measured, by the negative control.
    """
    text = _strip_tone_and_fold_candrabindu(text)
    for nasal in NASAL_VIRAMA:
        text = text.replace(nasal, ANUSVARA)
    return unicodedata.normalize("NFC", DROPPED.sub("", text))


class Check:
    def __init__(self, name: str, attack: str, fatal_if: str) -> None:
        self.name = name
        self.attack = attack
        self.fatal_if = fatal_if
        self.eligible = 0
        self.evaluated = 0
        self.failures: list[dict[str, Any]] = []
        self.observed: dict[str, Any] = {}
        self._count = 0

    def fail(self, **detail: Any) -> None:
        if len(self.failures) < 45:
            self.failures.append(detail)
        self._count += 1

    @property
    def failure_count(self) -> int:
        return self._count

    def as_dict(self) -> dict[str, Any]:
        coverage = (self.evaluated / self.eligible) if self.eligible else 1.0
        return {
            "name": self.name,
            "attack": self.attack,
            "fatal_if": self.fatal_if,
            "eligible": self.eligible,
            "evaluated": self.evaluated,
            "coverage": round(coverage, 6),
            "at_full_coverage": self.evaluated == self.eligible,
            "failures": self._count,
            "failure_detail": self.failures,
            "observed": self.observed,
            "status": (
                "SURVIVED"
                if self._count == 0 and self.evaluated == self.eligible
                else "DEFECT_FOUND"
            ),
        }


def load_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def printed_numerals(row: dict[str, Any]) -> list[int]:
    text = row["payload"]["notated_text_devanagari"].strip()
    match = TRAILING_NUMERALS.search(text)
    if not match:
        return []
    return [int(n) for n in NUMERAL_GROUP.findall(text[match.start() :])]


def verse_index(canonical_key: str) -> int:
    return int(canonical_key.rsplit(":V", 1)[1])


def witness_line(row: dict[str, Any]) -> int:
    """The witness line a row cites. Raises rather than defaulting: a locator this cannot
    read is a row whose position on the page is unknown, and 0 would sort it to the front."""
    match = LOCATOR_LINE.search(row["source_locator"])
    if match is None:
        raise ValueError(f"unreadable source_locator: {row['source_locator']!r}")
    return int(match.group(1))


def build_sample(
    notation: list[dict[str, Any]],
    normalised: dict[str, str],
    repeated: set[str],
) -> dict[str, Any]:
    """Draw the adversarial sample from its declared strata, hardest first."""
    by_key = {r["canonical_key"]: r for r in notation}
    chosen: list[str] = []
    provenance: dict[str, str] = {}

    def take(stratum: str, candidates: list[str], want: int) -> int:
        taken = 0
        for key in candidates:
            if taken >= want:
                break
            if key in provenance:
                continue
            provenance[key] = stratum
            chosen.append(key)
            taken += 1
        return taken

    ambiguous = sorted(
        k for k in by_key if k in repeated and not printed_numerals(by_key[k])
    )
    shortest = sorted(by_key, key=lambda k: (len(normalised[k]), k))
    fewest = sorted(by_key, key=lambda k: (by_key[k]["payload"]["tone_mark_count"], k))
    edges: list[str] = []
    by_collection: dict[str, list[str]] = collections.defaultdict(list)
    for key in sorted(by_key):
        by_collection[key.split(":")[3]].append(key)
    for keys in by_collection.values():
        edges.extend([keys[0], keys[-1]])
    edges = sorted(set(edges))

    shortfalls: dict[str, int] = {}
    plan = {
        "repeated_text_and_no_printed_numeral": ambiguous,
        "shortest_normalised_text": shortest,
        "fewest_tone_marks": fewest,
        "first_or_last_notated_verse_of_a_collection": edges,
    }
    for stratum, want in SAMPLE_STRATA:
        if stratum == "seeded_random_from_the_remainder":
            continue
        got = take(stratum, plan[stratum], want)
        if got < want:
            shortfalls[stratum] = want - got

    rng = random.Random(SEED)
    remainder = sorted(k for k in by_key if k not in provenance)
    rng.shuffle(remainder)
    want_random = SAMPLE_SIZE - len(chosen)
    take("seeded_random_from_the_remainder", remainder, want_random)

    return {
        "size": len(chosen),
        "declared_size": SAMPLE_SIZE,
        "seed": SEED,
        "strata_declared": {name: want for name, want in SAMPLE_STRATA},
        "strata_drawn": dict(collections.Counter(provenance.values())),
        "strata_short_and_topped_up_from_the_seeded_remainder": shortfalls,
        "keys": chosen,
        "provenance": provenance,
        "selection_rule": (
            "Hardest strata first, in the fixed order above, de-duplicated, with any "
            "shortfall topped up from a seed-20260918 shuffle of whatever no stratum "
            "claimed. The strata are the rows where a wrong answer is HARDEST to see: a "
            "repeated text with no printed numeral is pinned by nothing but order, a short "
            "text is likeliest to match by accident, and a row with few marks carries the "
            "least information to be wrong about."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", default=str(OUT))
    parser.add_argument(
        "--no-overlay",
        action="store_true",
        help="ignore the withheld-reason overlay and adjudicate the sealed artifact alone",
    )
    args = parser.parse_args()

    notation = [
        r for r in load_jsonl(ROWS) if r["payload"]["layer"] == IN_SCOPE_LAYER
    ]
    withheld = [
        r
        for r in load_jsonl(REJECTED)
        if r["disposition"] == "UNRESOLVED" and r["kind"] == IN_SCOPE_LAYER
    ]

    overlay: dict[str, str] = {}
    overlay_meta: dict[str, Any] = {"applied": False, "path": None, "rows": 0}
    if OVERLAY.exists() and not args.no_overlay:
        blob = json.loads(OVERLAY.read_text(encoding="utf-8"))
        overlay = {c["canonical_key"]: c["corrected_class"] for c in blob["corrections"]}
        overlay_meta = {
            "applied": True,
            "path": str(OVERLAY.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "rows": len(overlay),
            "why": blob["why"],
        }

    # E1: the canonical text, out of the file.
    passage_key = {
        r["entity_id"]: r["canonical_key"]
        for r in load_jsonl(PASSAGES)
        if r["entity_type"] == "MANTRA"
    }
    canonical: dict[str, str] = {}
    for record in load_jsonl(TEXT_VERSIONS):
        key = passage_key.get(record["passage_id"])
        if key:
            canonical[key] = record["text_nfc"]

    # E2: the running series, off the live graph.
    driver = GraphDatabase.driver(URI, auth=AUTH)
    with driver.session(database=DB) as session:
        running = {
            r["k"]: r["n"]
            for r in session.run(
                Query(
                    "MATCH (m:Mantra {veda:'SV'}) "
                    "RETURN m.canonical_key AS k, m.running_samhita_number AS n",
                    timeout=QUERY_TIMEOUT_SECONDS,
                )
            ).data()
        }
    driver.close()

    invariant = {k: normalise_segmentation_invariant(v) for k, v in canonical.items()}
    positional = {k: normalise_positional(v) for k, v in canonical.items()}
    order = sorted(canonical)
    rank = {k: i for i, k in enumerate(order)}
    text_groups: dict[str, list[str]] = collections.defaultdict(list)
    for key, text in invariant.items():
        text_groups[text].append(key)
    repeated = {k for k, t in invariant.items() if len(text_groups[t]) > 1}
    released = {r["canonical_key"] for r in notation}

    sample = build_sample(notation, invariant, repeated)
    sample_keys = set(sample["keys"])
    sample_defects: list[dict[str, Any]] = []

    checks: list[Check] = []

    # -- C1 -----------------------------------------------------------------------------
    c = Check(
        "independent.an_independent_strip_rederives_the_canonical_text",
        "Re-implement the declared normalisation from its written sentence, using the "
        "Unicode character database instead of the artifact's integer ranges, and apply it "
        "to the RAW witness string. Compare against the canonical FILE, never the "
        "artifact's own tone_stripped_text and never the graph's copy.",
        "Any row whose witness text does not reduce to the canonical text at its own key.",
    )
    c.eligible = len(notation)
    positional_diffs: list[str] = []
    diff_chars: collections.Counter[str] = collections.Counter()
    for row in notation:
        c.evaluated += 1
        key = row["canonical_key"]
        witness = row["payload"]["notated_text_devanagari"]
        if normalise_segmentation_invariant(witness) != invariant[key]:
            c.fail(
                key=key,
                witness=normalise_segmentation_invariant(witness)[:80],
                canonical=invariant[key][:80],
            )
            continue
        got, want = normalise_positional(witness), positional[key]
        if got != want:
            positional_diffs.append(key)
            for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, got, want).get_opcodes():
                if tag != "equal":
                    diff_chars.update(got[i1:i2])
                    diff_chars.update(want[j1:j2])
    c.observed = {
        "segmentation_invariant_reading_agrees": len(notation) - c.failure_count,
        "positional_reading_agrees": len(notation) - len(positional_diffs),
        "positional_reading_disagrees": len(positional_diffs),
        "characters_involved_in_every_positional_disagreement": {
            unicodedata.name(ch, f"U+{ord(ch):04X}"): n for ch, n in diff_chars.items()
        },
        "why_two_readings": (
            "The witness and our canonical text segment their words differently -- the "
            "witness prints 'maghavan gavistaya' as two tokens where the canonical prints "
            "one -- so 'word-final' is not a position both sides agree on. Every one of the "
            "disagreements under the positional reading is confined to ANUSVARA, NA and "
            "VIRAMA: the declared nasal fold and nothing else. No row differs in a "
            "consonant, a vowel or a vowel sign under either reading."
        ),
        "read_from": [
            "data/canonical/samaveda_arcika_v1/text_versions.jsonl",
            "payload.notated_text_devanagari",
        ],
        "never_read": ["payload.tone_stripped_text", "the graph's stored SV text"],
    }
    checks.append(c)

    # -- C2 NEGATIVE CONTROL -------------------------------------------------------------
    c = Check(
        "independent.the_comparison_has_discriminating_power",
        "NEGATIVE CONTROL. Run C1 again against the NEXT canonical verse in order. A "
        "normalisation loose enough to match anything would score 1,136 of 1,136 above and "
        "mean nothing.",
        "The shifted comparison matching at any material rate. The aligned result is only "
        "evidence to the extent this one is near zero.",
    )
    c.eligible = len(notation)
    shifted_invariant = shifted_positional = 0
    for row in notation:
        c.evaluated += 1
        index = rank[row["canonical_key"]] + 1
        if index >= len(order):
            continue
        neighbour = order[index]
        witness = row["payload"]["notated_text_devanagari"]
        if normalise_segmentation_invariant(witness) == invariant[neighbour]:
            shifted_invariant += 1
            c.fail(key=row["canonical_key"], also_matches=neighbour)
        if normalise_positional(witness) == positional[neighbour]:
            shifted_positional += 1
    c.observed = {
        "aligned_agreement_invariant": len(notation) - checks[0].failure_count,
        "shifted_by_one_agreement_invariant": shifted_invariant,
        "shifted_by_one_agreement_positional": shifted_positional,
        "discrimination": (
            f"{len(notation) - checks[0].failure_count} aligned vs {shifted_invariant} "
            f"shifted, over the same {len(notation)} rows and the same fold"
        ),
    }
    checks.append(c)

    # -- C3 -----------------------------------------------------------------------------
    c = Check(
        "independent.no_undeclared_character_was_removed",
        "The over-normalisation attack. Census every character the independent strip "
        "removes and classify each one. Removing an ordinary vowel sign would manufacture "
        "the match in C1 while looking like a clean run.",
        "Any removed character that is not a Vedic tone mark, a declared punctuation or "
        "digit, a folded spacing candrabindu, or part of the declared nasal fold.",
    )
    c.eligible = len(notation)
    removed: collections.Counter[str] = collections.Counter()
    for row in notation:
        c.evaluated += 1
        source = unicodedata.normalize("NFC", row["payload"]["notated_text_devanagari"])
        kept = collections.Counter(normalise_segmentation_invariant(source))
        for char, count in (collections.Counter(source) - kept).items():
            removed[char] += count

    def classify(char: str) -> str:
        if is_vedic_tone_mark(char):
            return "VEDIC_TONE_MARK"
        if char in SPACING_CANDRABINDU:
            return "SPACING_CANDRABINDU_FOLDED_TO_ANUSVARA"
        if DROPPED.match(char):
            return "WHITESPACE_DIGIT_OR_PUNCTUATION"
        if char in ("म", "न", VIRAMA):
            return "DECLARED_NASAL_FOLD"
        return "UNDECLARED"

    by_class: collections.Counter[str] = collections.Counter()
    for char, count in removed.items():
        by_class[classify(char)] += count
        if classify(char) == "UNDECLARED":
            c.fail(
                codepoint=f"U+{ord(char):04X}",
                name=unicodedata.name(char, "?"),
                occurrences=count,
            )
    c.observed = {
        "removed_characters_by_class": dict(by_class),
        "distinct_codepoints_removed": len(removed),
        "tone_codepoints_removed": sorted(
            {f"U+{ord(ch):04X}" for ch in removed if is_vedic_tone_mark(ch)}
        ),
        "undeclared_removals": c.failure_count,
    }
    checks.append(c)

    # -- C4 -----------------------------------------------------------------------------
    c = Check(
        "independent.the_witness_own_printed_numeral_agrees",
        "The witness prints its own numerals, and the artifact states the join did not use "
        "them. Each one must equal either the verse index inside its dasati or the running "
        "Samhita number the graph carries from a different citation system.",
        "Any printed numeral matching neither series. Only the running series can detect a "
        "whole-decade shift, so its match count is reported separately rather than folded "
        "into one total.",
    )
    eligible_rows = [r for r in notation if printed_numerals(r)]
    c.eligible = len(eligible_rows)
    tally: collections.Counter[str] = collections.Counter()
    for row in eligible_rows:
        c.evaluated += 1
        key = row["canonical_key"]
        numerals = printed_numerals(row)
        first = numerals[0]
        matches_verse = first == verse_index(key)
        matches_running = first == running.get(key)
        if matches_verse and matches_running:
            tally["both_series"] += 1
        elif matches_running:
            tally["running_samhita_series"] += 1
        elif matches_verse:
            tally["verse_index_within_the_dasati"] += 1
        else:
            tally["NEITHER"] += 1
            c.fail(
                key=key,
                printed=numerals,
                verse_index=verse_index(key),
                running_samhita_number=running.get(key),
            )
    c.observed = {
        "rows_carrying_a_printed_numeral": len(eligible_rows),
        "rows_carrying_none": len(notation) - len(eligible_rows),
        "agreement_by_series": dict(tally),
        "decisive_rows_the_running_series_pins": tally["running_samhita_series"]
        + tally["both_series"],
        "running_series_provenance": (
            "m.running_samhita_number, landed at R5 from citations.jsonl system "
            "WIKISOURCE_SA_RUNNING_SAMHITA_NUMBER. The notation artifact's own "
            "mapping_method states the page's printed numerals were NOT used to join, so "
            "this is evidence the join never saw."
        ),
        "parse_note": (
            "A trailing run of numeral groups is read FIRST-group-first. Reading the last "
            "group instead mistakes the dasati-closing numeral for the verse numeral, and "
            "invented a disagreement at UTTARA:P01:R01:D04:V03 on a first attempt."
        ),
    }
    checks.append(c)

    # -- C5 -----------------------------------------------------------------------------
    c = Check(
        "independent.rows_pinned_only_by_order_sit_between_pinned_anchors",
        "405 of the 1,844 canonical verses do not have a unique normalised text, so a whole "
        "alignment shift would be INVISIBLE to C1 there. For each row on a repeated text "
        "that also carries no printed numeral, nothing but order pins it -- so it must fall "
        "strictly between two independently pinned rows in BOTH the witness's line order "
        "and the canonical order.",
        "Any order-only row with no pinned anchor on one side, or one whose canonical "
        "position does not lie between its anchors'.",
    )
    by_line = sorted(notation, key=witness_line)

    def pinned(row: dict[str, Any]) -> bool:
        return row["canonical_key"] not in repeated or bool(printed_numerals(row))

    order_only = [r for r in by_line if not pinned(r)]
    c.eligible = len(order_only)
    for position, row in enumerate(by_line):
        if pinned(row):
            continue
        c.evaluated += 1
        before = next((by_line[j] for j in range(position - 1, -1, -1) if pinned(by_line[j])), None)
        after = next(
            (by_line[j] for j in range(position + 1, len(by_line)) if pinned(by_line[j])),
            None,
        )
        if not before or not after:
            c.fail(key=row["canonical_key"], why="no_pinned_anchor_on_one_side")
            continue
        low, mid, high = (
            rank[before["canonical_key"]],
            rank[row["canonical_key"]],
            rank[after["canonical_key"]],
        )
        if not low < mid < high:
            c.fail(
                key=row["canonical_key"],
                why="canonical_position_not_between_its_anchors",
                anchors=[before["canonical_key"], after["canonical_key"]],
            )
    c.observed = {
        "canonical_verses_whose_normalised_text_is_not_unique": len(repeated),
        "repeated_text_groups": sum(1 for keys in text_groups.values() if len(keys) > 1),
        "notation_rows_on_a_repeated_text": sum(
            1 for r in notation if r["canonical_key"] in repeated
        ),
        "of_those_with_no_printed_numeral_either": len(order_only),
        "unbracketed": c.failure_count,
        "witness_lines_strictly_increase_with_canonical_order": all(
            rank[a["canonical_key"]] < rank[b["canonical_key"]]
            for a, b in itertools.pairwise(by_line)
        ),
    }
    checks.append(c)

    # -- C6 -----------------------------------------------------------------------------
    c = Check(
        "independent.the_marking_is_not_array_order_generated",
        "If the marks had been generated rather than read off a page, they would betray it: "
        "one signature repeated, a constant count, or a count that moves monotonically with "
        "position in the file.",
        "A single mark signature covering a large share of the rows, a constant mark count, "
        "or a mark count monotone in file order.",
    )
    c.eligible = len(notation)
    signatures: collections.Counter[str] = collections.Counter()
    counts: list[int] = []
    for row in notation:
        c.evaluated += 1
        signatures[
            json.dumps(row["payload"]["tone_marks_by_codepoint"], sort_keys=True)
        ] += 1
        counts.append(row["payload"]["tone_mark_count"])
    top_share = signatures.most_common(1)[0][1] / len(notation)
    monotone = all(b >= a for a, b in itertools.pairwise(counts)) or all(
        b <= a for a, b in itertools.pairwise(counts)
    )
    if len(set(counts)) == 1:
        c.fail(why="every_row_carries_the_same_number_of_marks")
    if monotone:
        c.fail(why="mark_count_is_monotone_in_file_order")
    if top_share > 0.25:
        c.fail(why="one_signature_dominates", share=round(top_share, 4))
    c.observed = {
        "distinct_mark_signatures": len(signatures),
        "most_common_signature_share": round(top_share, 4),
        "distinct_mark_counts": len(set(counts)),
        "mark_count_range": [min(counts), max(counts)],
        "monotone_in_file_order": monotone,
    }
    checks.append(c)

    # -- C7 -----------------------------------------------------------------------------
    c = Check(
        "independent.the_withheld_reason_survives_its_own_falsification",
        "Attack the WITHHOLDING, not just the release. 109 verses are withheld saying the "
        "witness 'plausibly does not carry this verse at all', and 599 saying the difference "
        "needs philological adjudication. Both claims are falsifiable in this repository: if "
        "a withheld verse's exact normalised text is RELEASED on a coreferent twin, then the "
        "witness demonstrably carries the text and neither reason is the true mechanism.",
        "Any withheld verse whose exact text is released elsewhere while its row still "
        "blames the witness for not carrying it, or blames a philological difference that "
        "the released twin shows is not there.",
    )
    c.eligible = len(withheld)
    misattributed: collections.Counter[str] = collections.Counter()
    for row in sorted(withheld, key=lambda r: r["canonical_key"]):
        c.evaluated += 1
        key = row["canonical_key"]
        stated = overlay.get(
            key,
            DECLARED_WITHHELD_CLASSES[0]
            if row["nearest_accented_line_similarity_at_least_0_90"]
            else DECLARED_WITHHELD_CLASSES[1],
        )
        if stated not in DECLARED_WITHHELD_CLASSES:
            c.fail(key=key, why="reason_class_outside_the_declared_set", stated=stated)
            continue
        twins = [k for k in text_groups[invariant[key]] if k != key and k in released]
        if twins and stated != EXHAUSTION_CLASS:
            misattributed[stated] += 1
            c.fail(
                key=key,
                stated_class=stated,
                why="exact_text_is_released_on_a_coreferent_twin",
                released_twin=twins[0],
                twins=len(twins),
            )
    c.observed = {
        "withheld_rows": len(withheld),
        "withheld_with_a_released_coreferent_twin": sum(
            1
            for r in withheld
            if [
                k
                for k in text_groups[invariant[r["canonical_key"]]]
                if k != r["canonical_key"] and k in released
            ]
        ),
        "misattributed_by_stated_class": dict(misattributed),
        "overlay": overlay_meta,
        "repeated_groups_where_every_member_is_released": sum(
            1
            for keys in text_groups.values()
            if len(keys) > 1 and all(k in released for k in keys)
        ),
        "repeated_groups_where_some_member_is_withheld": sum(
            1
            for keys in text_groups.values()
            if len(keys) > 1 and any(k not in released for k in keys)
        ),
        "mechanism": (
            "153 of the 202 repeated-text groups have EVERY member released, so the witness "
            "does print a repeated verse more than once and the harvest does find both "
            "lines. Where only one member is released, the single order-consistent "
            "occurrence went to the earlier verse and the later one had no line left. That "
            "is line exhaustion on a coreferent repeat -- not an absence from the witness, "
            "and not a philological disagreement."
        ),
        "what_this_does_not_change": (
            "No row moves from withheld to released. The notated string belongs to the "
            "coordinate the witness printed it at; copying a twin's marks onto another "
            "verse would be inventing notation. Only the stated reason changes."
        ),
    }
    checks.append(c)

    # -- C8 the declared adversarial sample ---------------------------------------------
    c = Check(
        "adversarial_sample_40.every_check_re_applied_row_by_row",
        "Re-run C1, C3, C4 and C5 over the 40 declared hardest rows individually, so a "
        "defect concentrated in one stratum cannot hide inside an aggregate. The sample was "
        "fixed before it was run and is not redrawn.",
        "Any defect on any sampled row.",
    )
    c.eligible = len(sample_keys)
    by_key = {r["canonical_key"]: r for r in notation}
    by_line_position = {r["canonical_key"]: i for i, r in enumerate(by_line)}
    for key in sample["keys"]:
        c.evaluated += 1
        row = by_key[key]
        witness = row["payload"]["notated_text_devanagari"]
        # Assertions and observations are kept apart. "on_a_repeated_text" is a FACT about
        # the row, not a claim about it: folding a descriptive boolean into the pass list
        # made 26 of these 40 rows read as defects on a first run.
        assertions: dict[str, bool] = {
            "independent_strip_rederives_canonical": normalise_segmentation_invariant(witness)
            == invariant[key],
            "shifted_comparison_fails_as_it_must": (
                rank[key] + 1 >= len(order)
                or normalise_segmentation_invariant(witness) != invariant[order[rank[key] + 1]]
            ),
        }
        if printed_numerals(row):
            assertions["printed_numeral_agrees_with_a_real_series"] = printed_numerals(row)[
                0
            ] in {verse_index(key), running.get(key)}
        if key in repeated and not printed_numerals(row):
            position = by_line_position[key]
            before = next(
                (by_line[j] for j in range(position - 1, -1, -1) if pinned(by_line[j])), None
            )
            after = next(
                (by_line[j] for j in range(position + 1, len(by_line)) if pinned(by_line[j])),
                None,
            )
            assertions["bracketed_by_pinned_anchors"] = bool(
                before
                and after
                and rank[before["canonical_key"]] < rank[key] < rank[after["canonical_key"]]
            )
        observations = {
            "stratum": sample["provenance"][key],
            "printed_numerals": printed_numerals(row),
            "on_a_repeated_text": key in repeated,
            "tone_marks": row["payload"]["tone_mark_count"],
            "normalised_length": len(invariant[key]),
        }
        bad = [name for name, value in assertions.items() if not value]
        if bad:
            sample_defects.append(
                {
                    "key": key,
                    "failed": bad,
                    "assertions": assertions,
                    "observations": observations,
                }
            )
            c.fail(key=key, failed=bad)
    c.observed = {
        "sample": {k: v for k, v in sample.items() if k != "provenance"},
        "defects": len(sample_defects),
        "defect_detail": sample_defects,
        "pre_existing_sample_in_the_artifact": {
            "name": "gana_rendering.adversarial_shortest_40",
            "size": 40,
            "defects": 0,
            "population": "GANA_RENDERING",
            "kept_not_replaced": True,
            "why_it_is_not_this_gate": (
                "It targets the 332 gana-rendering rows, never the 1,136 notation rows, and "
                "it was run by the same pass that produced them. It is recorded here and is "
                "not discarded; it is simply not evidence about this population."
            ),
        },
    }
    checks.append(c)

    defective = [c for c in checks if c.failure_count]
    under_covered = [c for c in checks if c.evaluated != c.eligible]
    verdict = "SURVIVED" if not defective and not under_covered else "DEFECT_FOUND"

    artifact = {
        "artifact": "SAMAVEDA_MUSIC_GATE_C",
        "gate": "C",
        "gate_definition": (
            "ADVERSARIAL -- headline survived an independent falsification attempt "
            "(data/staging/integration/wave3_eligibility.json)"
        ),
        "domain": "samaveda_music",
        "at": datetime.datetime.now(datetime.UTC).isoformat(),
        "headline_under_attack": (
            "1,136 of the 1,844 Kauthuma arcika verses carry source-supplied Kauthuma "
            "numeric svara notation, aligned to this corpus's own canonical coordinates; "
            "708 are withheld with a typed reason."
        ),
        "independence": {
            "the_staging_pipeline_is_not_in_this_repository": True,
            "fields_this_gate_refuses_to_read": [
                "payload.tone_stripped_text",
                "proofs/qa-report.json",
                "the graph's stored SV primary text",
            ],
            "evidence_sources": {
                "E1_canonical_files": [
                    "data/canonical/samaveda_arcika_v1/passages.jsonl",
                    "data/canonical/samaveda_arcika_v1/text_versions.jsonl",
                ],
                "E2_graph_running_series": (
                    "m.running_samhita_number (R5, a different citation system)"
                ),
                "E3_witness_raw_string": (
                    "payload.notated_text_devanagari, including its own printed numerals"
                ),
                "E4_unicode_character_database": (
                    "unicodedata.category, in place of the artifact's integer ranges"
                ),
            },
            "normalisation_reimplemented_from": (
                "data/staging/samaveda_music/manifest.json config.normalisation, as prose"
            ),
        },
        "pass_condition": (
            "Every attack fails to land AND every check covers its whole eligible "
            "population. A check below full coverage fails the gate."
        ),
        "checks": [c.as_dict() for c in checks],
        "summary": {
            "attacks_run": len(checks),
            "attacks_that_landed": len({c.name for c in defective}),
            "checks_below_full_coverage": [c.name for c in under_covered],
            "total_defects": sum(c.failure_count for c in checks),
            "rows_evaluated_across_all_checks": sum(c.evaluated for c in checks),
        },
        "verdict": verdict,
    }

    path = pathlib.Path(args.json)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(artifact, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    print(f"GATE C  samaveda_music  {IN_SCOPE_LAYER}  {len(notation):,} rows")
    print(f"  overlay applied: {overlay_meta['applied']} ({overlay_meta['rows']} row(s))")
    print()
    for check in checks:
        d = check.as_dict()
        flag = "OK  " if d["status"] == "SURVIVED" else "DFCT"
        print(
            f"  [{flag}] {d['name']:<66} "
            f"{d['evaluated']}/{d['eligible']}, {d['failures']} defect(s)"
        )
    print()
    try:
        shown = path.resolve().relative_to(PROJECT_ROOT)
    except ValueError:
        shown = path
    print(f"  {verdict}. report: {shown}")
    return 0 if verdict == "SURVIVED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
