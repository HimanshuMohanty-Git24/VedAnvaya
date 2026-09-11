"""Post-synthesis check that the prose's numbers agree with the packet's numbers.

The citation audit next door proves that an answer *pointed at* real evidence. It cannot
prove the answer read it. Observed live, graded MISLEADING:

    "the hotṛ appears in hundreds of verses in each corpus, and the sacrifice in
     hundreds as well [E7, E8]"

E7 said 18 verses in the Atharvaveda, 195 in the Rigveda, 38 in the Samaveda and 49 in
the Yajurveda. Retrieval was right, the packet was right, the citation was right, and the
sentence overstated three of four corpora by five to ten times while wearing a citation to
the very rows that refute it. Nothing in the pipeline could see it, because every stage
before this one checks *provenance* and none checks *arithmetic*.

So this module is deliberately not a natural-language entailment engine. It is six named
rules over integers that were already printed in the evidence packet, and its single
contract is:

    a model may not contradict a number it was handed and still be returned as fully
    grounded.

**Scope is per sentence, and only cited sentences are checked.** A claim is tested against
the numbers in the evidence items *that sentence cites* -- not the whole packet, which
would let an unrelated figure three items away manufacture a contradiction. An uncited
sentence is skipped here on purpose: it is already unsupported under the citation
contract, and the answer-level caveat says so. The sentence this module exists for is the
dangerous one -- a wrong number carrying a correct-looking citation.

**Every rule fails closed toward silence.** Where a rule cannot find the figures it would
need, it reports nothing rather than guessing. A validator that invents findings is worse
than no validator: it trains its reader to ignore it, and the one real finding then goes
out with the noise.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Final

from vedagraph.api.ask.citation import extract_cited_ids
from vedagraph.api.ask.evidence import EvidencePacket
from vedagraph.api.ask.models import EvidenceItem


class QuantitativeRule(StrEnum):
    """Which check a finding came from. Named so a report can be read without the code."""

    EXACT_COUNT = "EXACT_COUNT"
    """A figure stated with a unit that the cited rows do not carry for that unit."""

    MAGNITUDE = "MAGNITUDE"
    """"hundreds" under 100, "thousands" under 1000. The Q60 failure."""

    UNIVERSAL = "UNIVERSAL"
    """"each"/"every"/"all" asserted where at least one group does not satisfy it."""

    MAJORITY = "MAJORITY"
    """"most" against a ratio at or below one half."""

    COMPARISON = "COMPARISON"
    """An ordering -- more/less/largest/smallest -- that the supplied counts invert."""

    ABSENCE = "ABSENCE"
    """A hard zero asserted over a status that never established one."""


@dataclass(frozen=True)
class NumericFact:
    """One integer lifted out of an evidence item, with the label and unit beside it.

    ``group`` is whatever the item printed before the colon -- "AV via MENTIONS_ENTITY",
    "RV", "Books 1-9". It is not parsed into a taxonomy, because the packet's own wording
    is the only label the model saw and therefore the only one a comparison may use.
    """

    evidence_id: str
    value: int
    group: str | None = None
    unit: str | None = None


@dataclass(frozen=True)
class QuantitativeFinding:
    rule: QuantitativeRule
    claim: str
    """The sentence as written, trimmed. Quoted back so a reader can judge the call."""
    detail: str
    """Why it failed, in figures."""
    evidence_ids: list[str] = field(default_factory=list)


@dataclass
class QuantitativeAudit:
    findings: list[QuantitativeFinding] = field(default_factory=list)
    sentences_checked: int = 0
    quantitative_sentences: int = 0
    """Cited sentences that carried at least one quantitative claim shape."""

    @property
    def ok(self) -> bool:
        return not self.findings

    def summary(self) -> str:
        """One human sentence for a caveat. Never names a rule or an evidence id."""
        return (
            "One quantitative statement in the generated summary could not be verified "
            "against VedaGraph's retrieved metrics."
            if len(self.findings) == 1
            else (
                f"{len(self.findings)} quantitative statements in the generated summary "
                "could not be verified against VedaGraph's retrieved metrics."
            )
        )


# ---------------------------------------------------------------------------
# Lifting numbers out of the packet
# ---------------------------------------------------------------------------

#: Where an item's figures live. Only fields the packet actually renders into the prompt
#: are read: a number the model never saw cannot be a number it contradicted.
_NUMERIC_FIELDS: Final = ("fact", "claim_text")

#: Segment separators inside a fact string. CORPUS_DISTRIBUTION joins per-corpus rows with
#: "; " and LEXICAL_PRESENCE does the same, so splitting here keeps each figure with the
#: label that introduced it instead of pooling every integer in the item.
_SEGMENT_SPLIT: Final = re.compile(r"[;—]|(?<=[a-z0-9])\. (?=[A-Z])")

_INT: Final = re.compile(r"(?<![\d.])(\d{1,9})(?![\d.])")

#: A group label is whatever preceded the colon, once the sentence lead-in is dropped.
_GROUP_LABEL: Final = re.compile(r"^\s*(?:[^:]*?\bfor\b\s*)?(?P<label>[^:]{1,60}?)\s*:")

#: Letters a noun may contain. Not ASCII, because this product's own prose is full of
#: diacritics -- "Samhitas" is written Saṃhitās and "hotr" hotṛ -- and a
#: word class that stops at the first mark stops checking the sentences actually
#: written. Observed: "all four Saṃhitās" was skipped by the counted-universal
#: rule entirely, because the noun after "four" did not match. It happened to be a true
#: claim; the rule had no way to know that.
_LETTER: Final = (
    "A-Za-z\u0101\u012b\u016b\u1e5b\u1e5d\u1e37\u1e39\u1e45\u00f1"
    "\u1e47\u1e43\u1e41\u1e6d\u1e0d\u1e25\u015b\u1e63\u0113\u014d"
)

_NOUN: Final = f"[{_LETTER}][{_LETTER}-]{{2,24}}"

_UNIT_AFTER: Final = re.compile(rf"\d+\s+(?P<unit>{_NOUN})")


def _singular(word: str) -> str:
    """Crude stemming, used only to line a claim's unit up with the evidence's.

    Both sides pass through here, so consistency matters more than being right about
    English. "ses" is deliberately not an -es ending: "verses" is verse+s, and treating
    it as vers+es silently renamed the one unit this product counts in.
    """
    low = word.lower()
    if low.endswith("ies") and len(low) > 4:
        return low[:-3] + "y"
    if low.endswith(("ches", "shes", "xes", "zes", "sses")):
        return low[:-2]
    if low.endswith("s") and not low.endswith("ss"):
        return low[:-1]
    return low


#: A METRIC item renders its figures as a JSON object -- ``DEVATA_STRUCTURAL_SPREAD:
#: {"1": 493, "8": 862, ...}`` -- so the enumeration the model read is a set of keys, not
#: a run of "label: value" clauses. Read as prose it collapses into one group holding
#: eighteen integers, which loses exactly the thing a universal claim is checked against:
#: how many groups there were. Indra's spread has nine keys and no mandala 9, and an
#: answer saying "all ten mandalas" is wrong in a way only the key count can show.
_JSON_OBJECT: Final = re.compile(r"\{[^{}]{0,4000}\}")
_JSON_PAIR: Final = re.compile(r'"(?P<key>[^"]{1,60})"\s*:\s*(?P<value>-?\d{1,9})')


def _json_facts(item_id: str, segment: str) -> list[NumericFact] | None:
    """Per-key facts when the segment carries a flat JSON object of integers."""
    obj = _JSON_OBJECT.search(segment)
    if obj is None:
        return None
    pairs = list(_JSON_PAIR.finditer(obj.group(0)))
    if not pairs:
        return None
    prefix = _GROUP_LABEL.search(segment)
    qualifier = prefix.group("label").strip() if prefix else None
    return [
        NumericFact(
            evidence_id=item_id,
            value=int(m.group("value")),
            group=f"{qualifier} {m.group('key')}" if qualifier else m.group("key"),
            unit=None,
        )
        for m in pairs
    ]


def numeric_facts(item: EvidenceItem) -> list[NumericFact]:
    """Every labelled integer an item printed, in order."""
    out: list[NumericFact] = []
    for field_name in _NUMERIC_FIELDS:
        text = getattr(item, field_name, None)
        if not text:
            continue
        for segment in _SEGMENT_SPLIT.split(str(text)):
            if not segment or not segment.strip():
                continue
            from_json = _json_facts(item.id, segment)
            if from_json is not None:
                out.extend(from_json)
                continue
            label_match = _GROUP_LABEL.search(segment)
            group = label_match.group("label").strip() if label_match else None
            units = {m.start(): _singular(m.group("unit")) for m in _UNIT_AFTER.finditer(segment)}
            for m in _INT.finditer(segment):
                out.append(
                    NumericFact(
                        evidence_id=item.id,
                        value=int(m.group(1)),
                        group=group,
                        unit=units.get(m.start()),
                    )
                )
    return out


# ---------------------------------------------------------------------------
# Reading the prose
# ---------------------------------------------------------------------------

#: Sentence split. Deliberately crude: a missed boundary widens one claim's scope by a
#: clause, which costs recall, while an over-eager one would sever a figure from the
#: citation that licenses it and manufacture a finding.
_SENTENCE_SPLIT: Final = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'“])")

_UNIVERSAL_WORDS: Final = re.compile(
    r"\b(each|every|all (?:four|of the)?|both|throughout (?:all|every))\b", re.IGNORECASE
)

_MAGNITUDES: Final[dict[str, int]] = {
    "hundreds": 100,
    "thousands": 1_000,
    "millions": 1_000_000,
}
_MAGNITUDE_RE: Final = re.compile(
    rf"\b(?P<word>hundreds|thousands|millions)\b(?:\s+of\s+(?P<unit>{_NOUN}))?",
    re.IGNORECASE,
)

#: "more than 100", "fewer than 12", "at least 30". The bound travels with its direction.
_NUM_COMPARISON: Final = re.compile(
    r"\b(?P<op>more than|greater than|over|at least|fewer than|less than|under|at most)\s+"
    r"(?P<n>\d{1,9})\b",
    re.IGNORECASE,
)

_SUPERLATIVE: Final = re.compile(
    r"\b(?P<op>largest|smallest|highest|lowest|most|fewest)\b", re.IGNORECASE
)

#: A ratio the evidence stated: "3 of 10", "3 out of 10", "3/10".
_RATIO: Final = re.compile(r"\b(?P<part>\d{1,9})\s*(?:/|of|out of)\s*(?P<whole>\d{1,9})\b")

_MAJORITY: Final = re.compile(r"\bmost\b", re.IGNORECASE)

#: "most" that is a superlative or an adverb, not a claim about more than half.
_MAJORITY_EXCLUSIONS: Final = re.compile(
    r"\bmost\s+(?:likely|often|commonly|frequently|notably|importantly|of all|"
    r"[a-z]+ly\b)",
    re.IGNORECASE,
)

_ABSENCE: Final = re.compile(
    r"\b(?:zero|none|no occurrences?|not attested|does not (?:occur|appear)|"
    r"never (?:occurs|appears)|absent from|nowhere in)\b",
    re.IGNORECASE,
)

#: Statuses that have not established a zero. A claim of "none" over any of these is
#: reporting an unmeasured gap as a measured absence -- the defect this project names
#: "absence must be typed in the row".
_UNESTABLISHED_STATUSES: Final[frozenset[str]] = frozenset(
    {"UNKNOWN", "NO_LEXICAL_MATCH", "INSUFFICIENT_EVIDENCE", "NOT_BUILT"}
)

#: Figures that are never quantities: the id inside a citation marker, and the numbers of
#: a passage locus. Both are matched and blanked before any rule reads the sentence, so
#: "AVS 1.11.1 [E1]" cannot be mistaken for a count of one.
_NOT_A_QUANTITY: Final = re.compile(
    r"\[[^\]]{0,120}\]|\b[A-Z]{2,4}(?:\s+[A-Z]{4,12})?\s*\d+(?:\.\d+)+",
)


#: A thousands separator between digit groups: "1,359", "1 359", "1 359" (thin space).
#: Joined before any rule reads the sentence, because reading "1,359 verses" as the
#: figure 359 is how a correct answer gets flagged. Six of the sixty already-graded
#: answers write their figures this way, and every one of them was a false positive until
#: this ran first. Exactly three trailing digits are required, so "mandalas 1, 8 and 10"
#: stays three numbers.
_DIGIT_GROUPING: Final = re.compile(r"(?<=\d)[,\u00a0\u202f\u2009 ](?=\d{3}\b)")


def _maskable(sentence: str) -> str:
    return _DIGIT_GROUPING.sub("", _NOT_A_QUANTITY.sub(" ", sentence))


def _values(facts: list[NumericFact], unit: str | None) -> list[int]:
    """Values to test a claim against, narrowed to the claim's unit when that is possible.

    A claim about verses is checked against verse counts. Where the unit does not appear
    in the cited rows the whole set is used instead, because a wrong narrowing would
    silently disable the rule and a validator that quietly stops checking is the failure
    mode this module is here to prevent.
    """
    if unit:
        singular = _singular(unit)
        matched = [f.value for f in facts if f.unit == singular]
        if matched:
            return matched
    return [f.value for f in facts]


# ---------------------------------------------------------------------------
# The rules
# ---------------------------------------------------------------------------


#: A figure written with the noun it counts: "18 verses", "3 hymns". The unit is what
#: makes the check possible -- it says which cited rows the figure claims to restate.
_COUNTED_NOUN: Final = re.compile(rf"\b(?P<n>\d{{1,9}})\s+(?P<unit>{_NOUN})")


#: A figure the sentence does not claim to be exact. "about 20", "roughly 100", "nearly
#: 40" -- a hedge is a refusal to state a precise count, so holding it to one would flag
#: the very caution the product asks for.
_HEDGE: Final = re.compile(
    r"\b(?:about|around|roughly|approximately|nearly|almost|some|up to|circa|c\.)\s+\d{1,9}\b",
    re.IGNORECASE,
)


def _bounded_spans(sentence: str) -> list[tuple[int, int]]:
    """Character ranges holding a figure that is a bound or a hedge, not a count.

    "more than 100 verses" states a threshold and is the comparison rule's business; read
    as a restated count it is a figure in no row, and EXACT_COUNT flagged it. The two
    rules must not both claim the same number.
    """
    return [m.span() for pattern in (_NUM_COMPARISON, _HEDGE) for m in pattern.finditer(sentence)]


def _check_exact_count(
    sentence: str, facts: list[NumericFact], ids: list[str]
) -> QuantitativeFinding | None:
    """A figure restated with a unit the cited rows carry, at a value they do not.

    Only fires where the unit is one the cited rows actually count in, and only where
    the figure appears under *no* unit in those rows. Both guards matter: an answer
    totalling two rows writes a number that is in neither of them, and flagging that
    would be a false positive about arithmetic the evidence supports.
    """
    if not facts:
        return None
    all_values = {f.value for f in facts}
    bounded = _bounded_spans(sentence)
    for m in _COUNTED_NOUN.finditer(sentence):
        if any(start <= m.start("n") < end for start, end in bounded):
            continue
        unit = _singular(m.group("unit"))
        same_unit = [f.value for f in facts if f.unit == unit]
        if not same_unit:
            continue
        claimed = int(m.group("n"))
        if claimed in all_values:
            continue
        # A plausible sum or difference of the cited figures is arithmetic over the
        # evidence, not a contradiction of it.
        if any(a + b == claimed for a in same_unit for b in same_unit):
            continue
        if sum(same_unit) == claimed:
            continue
        return QuantitativeFinding(
            rule=QuantitativeRule.EXACT_COUNT,
            claim=sentence.strip(),
            detail=(
                f"'{claimed} {m.group('unit')}' appears in none of the cited rows, which "
                f"give {', '.join(str(v) for v in sorted(set(same_unit))[:8])}."
            ),
            evidence_ids=ids,
        )
    return None


def _check_magnitude(
    sentence: str, facts: list[NumericFact], ids: list[str]
) -> QuantitativeFinding | None:
    for m in _MAGNITUDE_RE.finditer(sentence):
        threshold = _MAGNITUDES[m.group("word").lower()]
        values = _values(facts, m.group("unit"))
        if not values:
            continue
        universal = bool(_UNIVERSAL_WORDS.search(sentence))
        # Universal reading: every group must clear the bar. Otherwise the generous
        # reading is enough -- one figure of that size makes "hundreds" defensible.
        failing = [v for v in values if v < threshold] if universal else []
        if universal and failing:
            return QuantitativeFinding(
                rule=QuantitativeRule.UNIVERSAL,
                claim=sentence.strip(),
                detail=(
                    f"'{m.group('word')}' is asserted of every group, but the cited rows "
                    f"include {', '.join(str(v) for v in sorted(set(failing))[:6])} "
                    f"-- below {threshold}."
                ),
                evidence_ids=ids,
            )
        if not universal and max(values) < threshold:
            return QuantitativeFinding(
                rule=QuantitativeRule.MAGNITUDE,
                claim=sentence.strip(),
                detail=(
                    f"'{m.group('word')}' implies at least {threshold}; the largest "
                    f"cited figure is {max(values)}."
                ),
                evidence_ids=ids,
            )
    return None


#: "all ten mandalas", "every one of the four corpora". The numeral is the whole point:
#: a bare "all corpora" says nothing checkable, while "all ten" states how many groups
#: the writer believes the evidence enumerated and can therefore be compared with how
#: many it did.
_NUMBER_WORDS: Final[dict[str, int]] = {
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}
_COUNTED_UNIVERSAL: Final = re.compile(
    r"\b(?:all|every one of the|each of the)\s+(?:the\s+)?"
    r"(?P<count>\d{1,2}|" + "|".join(_NUMBER_WORDS) + r")\s+"
    rf"(?P<noun>{_NOUN})",
    re.IGNORECASE,
)

#: The largest enumeration this rule will judge. Beyond it a claim of "all 40" is not
#: counting the rows in front of the writer, and the group count stops being the right
#: comparison.
_MAX_ENUMERATION: Final = 20


def _check_counted_universal(
    sentence: str, facts: list[NumericFact], ids: list[str]
) -> QuantitativeFinding | None:
    """ "all N <things>" against how many groups the cited rows actually enumerate.

    Fires in one direction only: when the evidence enumerates *fewer* groups than the
    claim asserts. More rows than groups is the normal case and never a contradiction --
    a per-corpus item carries two rows per corpus, so "all four corpora" legitimately
    meets eight rows.
    """
    m = _COUNTED_UNIVERSAL.search(sentence)
    if m is None:
        return None
    raw = m.group("count").lower()
    claimed = int(raw) if raw.isdigit() else _NUMBER_WORDS[raw]
    if not 2 <= claimed <= _MAX_ENUMERATION:
        return None
    groups = {f.group for f in facts if f.group}
    # Two groups is the floor for calling something an enumeration. One group is an
    # item that happens to carry a label, and judging a universal against it would flag
    # every answer that summarised a single row.
    if len(groups) < 2 or len(groups) >= claimed:
        return None
    return QuantitativeFinding(
        rule=QuantitativeRule.UNIVERSAL,
        claim=sentence.strip(),
        detail=(
            f"'all {raw} {m.group('noun')}' asserts {claimed} groups; the cited rows "
            f"enumerate {len(groups)}: {', '.join(sorted(groups)[:12])}."
        ),
        evidence_ids=ids,
    )


def _check_numeric_comparison(
    sentence: str, facts: list[NumericFact], ids: list[str]
) -> QuantitativeFinding | None:
    universal = bool(_UNIVERSAL_WORDS.search(sentence))
    for m in _NUM_COMPARISON.finditer(sentence):
        op = m.group("op").lower()
        bound = int(m.group("n"))
        values = _values(facts, None)
        if not values:
            continue
        upward = op in {"more than", "greater than", "over", "at least"}

        def holds(v: int, *, up: bool = upward, b: int = bound, o: str = op) -> bool:
            if up:
                return v >= b if o == "at least" else v > b
            return v <= b if o == "at most" else v < b

        failing = [v for v in values if not holds(v)]
        if universal and failing:
            return QuantitativeFinding(
                rule=QuantitativeRule.UNIVERSAL,
                claim=sentence.strip(),
                detail=(
                    f"'{op} {bound}' is asserted of every group, but the cited rows "
                    f"include {', '.join(str(v) for v in sorted(set(failing))[:6])}."
                ),
                evidence_ids=ids,
            )
        if not universal and not any(holds(v) for v in values):
            return QuantitativeFinding(
                rule=QuantitativeRule.COMPARISON,
                claim=sentence.strip(),
                detail=(
                    f"'{op} {bound}' holds for none of the cited figures "
                    f"({', '.join(str(v) for v in sorted(set(values))[:6])})."
                ),
                evidence_ids=ids,
            )
    return None


def _group_position(sentence: str, group: str) -> int:
    """Where a packet's own group label is named in the sentence, or -1.

    Matched on the label's alphanumeric tokens rather than the label verbatim, because
    the packet writes "AV via MENTIONS_ENTITY" and prose writes "the Atharvaveda (AV)".
    The longest token is used: it is the one that carries the identity.

    A token of one or two characters is matched case-sensitively. Folding case for those
    turns a group label "A" into every indefinite article in the sentence, and the
    ordering rule would then compare two positions that have nothing to do with the
    groups. Corpus codes are written "RV", "AV" in both the packet and the prose, so the
    stricter match costs nothing where it matters.
    """
    tokens = sorted(
        re.findall(rf"[{_LETTER}][{_LETTER}0-9_]{{0,30}}", group), key=len, reverse=True
    )
    for token in tokens:
        flags = re.IGNORECASE if len(token) > 2 else re.NOFLAG
        m = re.search(rf"\b{re.escape(token)}\b", sentence, flags)
        if m:
            return m.start()
    return -1


_RELATIVE: Final = re.compile(
    r"\b(?P<op>more than|greater than|fewer than|less than)\b(?!\s+\d)", re.IGNORECASE
)


def _check_group_ordering(
    sentence: str, facts: list[NumericFact], ids: list[str]
) -> QuantitativeFinding | None:
    """ "A has more than B", checked by looking up A and B in the cited rows."""
    m = _RELATIVE.search(sentence)
    if m is None:
        return None
    by_group: dict[str, int] = {}
    for fact in facts:
        if fact.group:
            by_group[fact.group] = max(by_group.get(fact.group, 0), fact.value)
    if len(by_group) < 2:
        return None

    left: tuple[str, int] | None = None
    right: tuple[str, int] | None = None
    for group, value in by_group.items():
        pos = _group_position(sentence, group)
        if pos < 0:
            continue
        if pos < m.start():
            if left is None or pos > _group_position(sentence, left[0]):
                left = (group, value)
        elif right is None:
            right = (group, value)
    if left is None or right is None or left[0] == right[0]:
        return None

    upward = m.group("op").lower() in {"more than", "greater than"}
    holds = left[1] > right[1] if upward else left[1] < right[1]
    if holds:
        return None
    return QuantitativeFinding(
        rule=QuantitativeRule.COMPARISON,
        claim=sentence.strip(),
        detail=(
            f"'{left[0]} {m.group('op')} {right[0]}' is contradicted by the cited "
            f"figures: {left[0]}={left[1]}, {right[0]}={right[1]}."
        ),
        evidence_ids=ids,
    )


def _check_superlative(
    sentence: str, facts: list[NumericFact], ids: list[str]
) -> QuantitativeFinding | None:
    """ "X is the largest" checked against which cited group actually holds the maximum."""
    m = _SUPERLATIVE.search(sentence)
    if m is None or m.group("op").lower() in {"most", "fewest"}:
        return None
    by_group: dict[str, int] = {}
    for fact in facts:
        if fact.group:
            by_group[fact.group] = max(by_group.get(fact.group, 0), fact.value)
    if len(by_group) < 2:
        return None

    wants_max = m.group("op").lower() in {"largest", "highest"}
    winner = max(by_group.items(), key=lambda kv: kv[1] if wants_max else -kv[1])
    named = [g for g in by_group if 0 <= _group_position(sentence, g) < m.start()]
    if len(named) != 1:
        return None
    claimed = named[0]
    if by_group[claimed] == winner[1]:
        return None
    return QuantitativeFinding(
        rule=QuantitativeRule.COMPARISON,
        claim=sentence.strip(),
        detail=(
            f"'{claimed}' is called the {m.group('op')}, but the cited figures give "
            f"{claimed}={by_group[claimed]} against {winner[0]}={winner[1]}."
        ),
        evidence_ids=ids,
    )


def _check_majority(
    sentence: str, facts: list[NumericFact], ids: list[str], raw_evidence: str
) -> QuantitativeFinding | None:
    if not _MAJORITY.search(sentence) or _MAJORITY_EXCLUSIONS.search(sentence):
        return None
    ratios = [
        (int(m.group("part")), int(m.group("whole")))
        for m in _RATIO.finditer(raw_evidence)
        if int(m.group("whole")) > 0
    ]
    ratios = [(p, w) for p, w in ratios if p <= w]
    if not ratios:
        return None
    # The most favourable ratio in the cited rows. If even that is not a majority, the
    # word cannot be defended under any reading of which figures it meant.
    part, whole = max(ratios, key=lambda pw: pw[0] / pw[1])
    if part / whole > 0.5:
        return None
    return QuantitativeFinding(
        rule=QuantitativeRule.MAJORITY,
        claim=sentence.strip(),
        detail=(
            f"'most' requires more than half; the best ratio in the cited rows is "
            f"{part} of {whole}."
        ),
        evidence_ids=ids,
    )


def _check_absence(
    sentence: str, items: list[EvidenceItem], ids: list[str]
) -> QuantitativeFinding | None:
    if not _ABSENCE.search(sentence):
        return None
    unestablished = [
        item.id
        for item in items
        if (item.knowledge_status or "").upper() in _UNESTABLISHED_STATUSES
    ]
    if not unestablished:
        return None
    statuses = sorted(
        {(item.knowledge_status or "").upper() for item in items if item.id in set(unestablished)}
    )
    return QuantitativeFinding(
        rule=QuantitativeRule.ABSENCE,
        claim=sentence.strip(),
        detail=(
            "A zero is asserted over evidence graded "
            f"{', '.join(statuses)}, which records an unmeasured gap rather than a "
            "measured absence."
        ),
        evidence_ids=unestablished,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def validate(answer: str, packet: EvidencePacket) -> QuantitativeAudit:
    """Check every cited sentence's arithmetic against the rows it cites."""
    audit = QuantitativeAudit()
    if not answer.strip() or not packet.items:
        return audit

    by_id = packet.by_id()
    seen: set[tuple[str, str]] = set()

    for raw_sentence in _SENTENCE_SPLIT.split(answer):
        sentence = raw_sentence.strip()
        if not sentence:
            continue
        audit.sentences_checked += 1
        ids = [cid for cid in extract_cited_ids(sentence) if cid in by_id]
        if not ids:
            continue

        items = [by_id[cid] for cid in ids]
        facts = [fact for item in items for fact in numeric_facts(item)]
        masked = _maskable(sentence)
        raw_evidence = " ; ".join(
            str(getattr(item, name, "") or "") for item in items for name in _NUMERIC_FIELDS
        )

        carries_claim = bool(
            _MAGNITUDE_RE.search(masked)
            or _COUNTED_UNIVERSAL.search(masked)
            or _NUM_COMPARISON.search(masked)
            or _RELATIVE.search(masked)
            or _SUPERLATIVE.search(masked)
            or _ABSENCE.search(masked)
            or _INT.search(masked)
        )
        if carries_claim:
            audit.quantitative_sentences += 1

        for finding in (
            _check_magnitude(masked, facts, ids),
            _check_counted_universal(masked, facts, ids),
            _check_exact_count(masked, facts, ids),
            _check_numeric_comparison(masked, facts, ids),
            _check_group_ordering(masked, facts, ids),
            _check_superlative(masked, facts, ids),
            _check_majority(masked, facts, ids, raw_evidence),
            _check_absence(masked, items, ids),
        ):
            if finding is None:
                continue
            key = (finding.rule.value, finding.claim)
            if key in seen:
                continue
            seen.add(key)
            audit.findings.append(finding)

    return audit


#: Handed back to the provider when a first draft fails. Generic on purpose: naming the
#: offending figure would teach the model to patch one sentence, and naming the question
#: would make this a per-question fix, which is the thing the contract forbids.
REPAIR_INSTRUCTION: Final = (
    "The generated answer contains a quantitative claim not supported by the retrieved "
    "metrics. Rewrite using only the supplied numeric evidence. State per-group figures "
    "exactly as the evidence gives them, and do not summarise them into a magnitude, a "
    "universal ('each', 'every', 'all'), a majority or an ordering that the figures do "
    "not bear out."
)
