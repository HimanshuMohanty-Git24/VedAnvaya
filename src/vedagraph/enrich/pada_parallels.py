"""Parallels at the quarter-verse, grouped rather than paired.

The cross-Veda and Rigvedic parallel layers both work at whole-verse granularity. A verse
that shares one of its four quarters with another verse is therefore either reported as a
near parallel with no indication of *which* quarter, or -- more often -- missed, because one
shared pada out of four sits below every verse-level similarity floor. The build report has
recorded this as unimplemented since V1, noting that the schema and the token pada tags
already support it.

They do. ``data/knowledge/rigveda_lexical_v1/tokens.jsonl`` carries a ``pada`` label and a
``pada_sequence`` on every one of its 164,758 tokens, from the University of Zurich
morphosyntactic annotation -- a manual scholarly annotation, not a parse of ours -- and they
partition all 10,552 Rigvedic mantras into 39,832 quarters.

**They reach the Rigveda and nothing else.** No other corpus in this graph carries a pada
tag of any kind, so this layer is a fifth relatedness class that covers one of four corpora.
That is a property of the annotation and not of the texts, it is stated on every row through
:data:`VEDA_SCOPE`, and the surface that reports the layer states it too. A pada layer
presented as corpus-wide would be the more useful-looking and less true object.

Groups, not pairs
-----------------
``yuyam pata svastibhih sada nah`` is the final pada of 82 different Rigvedic verses.
Materialising that as verse-to-verse edges costs 3,321 edges to say one thing. The layer
emits a group node per identical quarter and one membership edge per attesting quarter
instead: 1,434 groups and 4,079 memberships, against the 11,631 verse pairs the same
information implies. The pairwise form is recoverable from the group; the group is not
recoverable from the pairs without recomputing it.

The comparison surface, named
------------------------------
Group membership is identity on ONE named surface and the name travels on the row:
:data:`COMPARISON_SURFACE`. The surface is each pada's tokens joined in ``sequence`` order,
word breaks dropped, put through
:func:`~vedagraph.normalize.unicode.comparison_form` at
``CROSS_SCRIPT_COMPARISON`` -- this repository's own declared cross-script comparison
surface, so a pada group and a verse parallel are comparable objects rather than two
spellings of "similar".

Calling ``fold_transcription_cross_script`` directly is not the same thing and was the
first version's defect: that fold does not apply
:data:`~vedagraph.normalize.unicode.CROSS_SCRIPT_SEPARATOR_MARKS`, so the annotation's
univerbation marker ``+`` -- measured on 1,977 of the 39,832 padas -- survived into the
comparison key and split quarters that are the same line. Measured, going through the
declared form recovers 4 groups the raw fold missed and changes 71 keys.

Dropping word breaks is what makes a sandhi-joined and a sandhi-split spelling of one
quarter compare equal, and it is also the only thing that could make two *different*
quarters collide. Measured on this corpus, it does not: :func:`build_pada_groups` refuses to
build if two padas that differ in their token sequence collapse to one key while differing
on the word-broken surface by more than a word break.

The fold trap, tested in both directions
-----------------------------------------
The IAST acute is both the palatal sibilant and the udatta. Over-folding turns every
accented vowel into an unaccented one and merges quarters that differ; under-folding leaves
one edition's accent marks in a comparison key and splits quarters that are the same. Both
look like a clean run.

This annotation carries no acute at all -- measured, 0 occurrences of U+0301 across all
39,832 padas, whose only combining marks are U+0304, U+0310 and U+0325 -- so the trap cannot
bite here, and ``s``-plus-acute NFC-composes to a real palatal sibilant which the fold
leaves standing. :func:`assert_no_accent_ambiguity` measures that rather than assuming it,
and it is the guard that fails if an accented edition is ever substituted for this one.
"""

from __future__ import annotations

import collections
import hashlib
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from vedagraph.normalize.unicode import ComparisonForm, comparison_form

#: The one corpus this layer reaches, and the reason. Carried on every row.
VEDA_SCOPE: Final = ("RV",)
VEDA_SCOPE_REASON: Final = (
    "Pada tags exist only in the Rigvedic token annotation (VedaWeb/Zurich). No other "
    "corpus in this graph carries a quarter-verse division, so this layer covers one of "
    "four corpora by the reach of its annotation and not by a property of the texts."
)

#: Granularity, typed so a query can separate this layer from the verse-level parallels
#: rather than inferring it from a predicate name.
GRANULARITY_PADA: Final = "PADA"
GRANULARITY_VERSE: Final = "VERSE"

COMPARISON_SURFACE: Final = "CROSS_SCRIPT_COMPARISON_SANDHI_COLLAPSED"
DERIVATION_METHOD: Final = "pada-identity-groups-v1"

#: A pada shorter than this on the comparison surface is not emitted. Measured, the shortest
#: Rigvedic pada is 6 characters; the floor removes the quarters that are one short word and
#: would group on a particle rather than on a shared line.
MIN_COMPARISON_CHARS: Final = 8

#: And a pada of one token is one word, which is a lexical fact the mention layer already
#: holds. Two tokens is the smallest thing that is a *wording*.
MIN_TOKENS: Final = 2

#: The combining mark that is both the palatal sibilant's diacritic and the udatta. Its
#: presence in this annotation would mean the fold is ambiguous; measured, it is absent.
COMBINING_ACUTE: Final = "́"


@dataclass(frozen=True)
class PadaToken:
    """One annotated token, reduced to what the pada layer reads."""

    passage_key: str
    pada: str
    sequence: int
    surface: str


@dataclass(frozen=True)
class PadaUnit:
    """One quarter-verse: its address, its readable text and its comparison key."""

    passage_key: str
    pada: str
    pada_key: str
    text: str
    comparison_key: str
    token_count: int


@dataclass(frozen=True)
class PadaGroup:
    """A set of quarter-verses identical on the comparison surface."""

    group_id: str
    comparison_key: str
    representative_text: str
    member_keys: tuple[str, ...]
    member_passage_keys: tuple[str, ...]
    padas: tuple[str, ...]

    @property
    def member_count(self) -> int:
        return len(self.member_keys)

    @property
    def distinct_mantras(self) -> int:
        return len(set(self.member_passage_keys))

    def implied_verse_pairs(self) -> int:
        n = self.distinct_mantras
        return n * (n - 1) // 2

    def as_row(self) -> dict[str, object]:
        return {
            "group_id": self.group_id,
            "granularity": GRANULARITY_PADA,
            "derivation_method": DERIVATION_METHOD,
            "comparison_surface": COMPARISON_SURFACE,
            "representative_text": self.representative_text,
            "member_count": self.member_count,
            "distinct_mantra_count": self.distinct_mantras,
            "implied_verse_pairs": self.implied_verse_pairs(),
            "padas": list(self.padas),
            "member_keys": list(self.member_keys),
            "member_passage_keys": sorted(set(self.member_passage_keys)),
            "veda_scope": list(VEDA_SCOPE),
            "veda_scope_reason": VEDA_SCOPE_REASON,
        }


@dataclass(frozen=True)
class PadaBuildReport:
    padas_read: int
    padas_eligible: int
    rejected: Mapping[str, int]
    groups: int
    memberships: int
    implied_verse_pairs: int
    largest_group: int
    accent_ambiguous_padas: int

    def as_row(self) -> dict[str, object]:
        return {
            "padas_read": self.padas_read,
            "padas_eligible": self.padas_eligible,
            "rejected": dict(sorted(self.rejected.items())),
            "groups": self.groups,
            "memberships": self.memberships,
            "implied_verse_pairs": self.implied_verse_pairs,
            "largest_group": self.largest_group,
            "accent_ambiguous_padas": self.accent_ambiguous_padas,
            "granularity": GRANULARITY_PADA,
            "veda_scope": list(VEDA_SCOPE),
            "veda_scope_reason": VEDA_SCOPE_REASON,
        }


def assert_no_accent_ambiguity(units: Sequence[PadaUnit]) -> int:
    """Count padas whose readable text carries the combining acute, and refuse if any do.

    The acute is the one mark this fold cannot read unambiguously: on ``s`` it composes to
    the palatal sibilant and is a letter, on a vowel it is the udatta and is an accent. A
    corpus that carries it needs an accent decision before it can be folded, so this raises
    rather than choosing one silently.
    """
    ambiguous = [
        unit
        for unit in units
        if COMBINING_ACUTE in unicodedata.normalize("NFD", unit.text)
        and COMBINING_ACUTE in unit.text
    ]
    if ambiguous:
        raise ValueError(
            f"{len(ambiguous)} padas carry U+0301, which is both the palatal sibilant's "
            f"diacritic and the udatta; first is {ambiguous[0].pada_key}. The comparison "
            "fold cannot be applied until the accent layer is decided."
        )
    return len(ambiguous)


def build_pada_units(tokens: Iterable[PadaToken]) -> tuple[PadaUnit, ...]:
    """Assemble tokens into quarter-verses, in ``sequence`` order within each pada."""
    grouped: dict[tuple[str, str], list[PadaToken]] = collections.defaultdict(list)
    for token in tokens:
        grouped[(token.passage_key, token.pada)].append(token)
    units = []
    for (passage_key, pada), members in grouped.items():
        ordered = sorted(members, key=lambda item: item.sequence)
        text = " ".join(item.surface for item in ordered)
        units.append(
            PadaUnit(
                passage_key=passage_key,
                pada=pada,
                pada_key=f"{passage_key}:P{pada}",
                text=text,
                comparison_key="".join(
                    comparison_form(text, ComparisonForm.CROSS_SCRIPT_COMPARISON).split()
                ),
                token_count=len(ordered),
            )
        )
    return tuple(sorted(units, key=lambda unit: unit.pada_key))


def build_pada_groups(
    units: Sequence[PadaUnit],
) -> tuple[tuple[PadaGroup, ...], PadaBuildReport]:
    """Group eligible quarter-verses by comparison identity.

    A group needs members in more than one *mantra*: two quarters of one verse that repeat
    its refrain are a fact about that verse, and the parallel layer is about verses that
    repeat each other.
    """
    ambiguous = assert_no_accent_ambiguity(units)
    rejected: collections.Counter[str] = collections.Counter()
    eligible = []
    for unit in units:
        if unit.token_count < MIN_TOKENS:
            rejected["pada_below_token_floor"] += 1
            continue
        if len(unit.comparison_key) < MIN_COMPARISON_CHARS:
            rejected["pada_below_comparison_char_floor"] += 1
            continue
        eligible.append(unit)

    buckets: dict[str, list[PadaUnit]] = collections.defaultdict(list)
    for unit in eligible:
        buckets[unit.comparison_key].append(unit)

    groups = []
    for key, members in sorted(buckets.items()):
        if len({unit.passage_key for unit in members}) < 2:
            rejected["pada_attested_in_one_mantra_only"] += len(members)
            continue
        ordered = sorted(members, key=lambda unit: unit.pada_key)
        # The readable representative is the commonest spelling on the word-broken surface,
        # tie-broken by the string itself so a rerun cannot pick a different one.
        spellings = collections.Counter(unit.text for unit in ordered)
        representative = sorted(spellings.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        groups.append(
            PadaGroup(
                group_id="VG:ENRICH:PADA-GROUP:" + hashlib.sha256(key.encode()).hexdigest()[:32],
                comparison_key=key,
                representative_text=representative,
                member_keys=tuple(unit.pada_key for unit in ordered),
                member_passage_keys=tuple(unit.passage_key for unit in ordered),
                padas=tuple(sorted({unit.pada for unit in ordered})),
            )
        )

    report = PadaBuildReport(
        padas_read=len(units),
        padas_eligible=len(eligible),
        rejected=dict(rejected),
        groups=len(groups),
        memberships=sum(group.member_count for group in groups),
        implied_verse_pairs=sum(group.implied_verse_pairs() for group in groups),
        largest_group=max((group.member_count for group in groups), default=0),
        accent_ambiguous_padas=ambiguous,
    )
    return tuple(groups), report
