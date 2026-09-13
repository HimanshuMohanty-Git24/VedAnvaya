"""Nested formula n-grams, grouped back into the phraseology they came from.

:mod:`vedagraph.enrich.formulas` promotes a repeated Sanskrit phrase to a hub node so that
a refrain shared by 236 mantras costs N edges instead of N-squared. It works, and it leaves
one thing undone. Its maximality rule collapses a sub-formula into its container only when
the two occur in *exactly* the same verses, which is the safe rule -- a sub-span attested
somewhere its container is not is a separate fact about the corpus and must survive. The
consequence is that one piece of phraseology arrives as a fan of overlapping nodes:

=============================================  =======  ==============
node                                           mantras  Vedas
=============================================  =======  ==============
``yo smān dveṣṭi``                                  63  YV, AV
``yo smān dveṣṭi yaṃ``                              61  YV, AV
``vayaṃ dviṣmaḥ``                                   52  YV, AV
``yo smān dveṣṭi yaṃ vayaṃ``                        51  AV
``yaṃ vayaṃ dviṣmaḥ``                               46  YV, AV
``yo smān dveṣṭi yaṃ vayaṃ dviṣmaḥ``                45  YV, AV
=============================================  =======  ==============

Eleven nodes and 326 ``USES_FORMULA`` edges, for the single imprecation *"whoever hates us
and whom we hate"*. Asked "what are the ten most widely-shared formulae in the corpus", the
Formula layer answers with ten rows that are five phrases; asked "which formulae spread
across three or four Vedas" it answers with 1,603 rows in which ``viśvā bhuvanā``,
``viśvā bhuvanāni`` and ``bhuvanāni viśvā`` occupy three of the top ten. The facts are all
correct. The answer is unusable, because a reader cannot tell a core formula from an
expansion of it.

This module adds the missing layer: it groups the surviving Formula nodes into families,
names one member of each family as its core, and lifts cross-Veda spread from the member to
the family -- since "which families cross three or four Vedas" is the question the layer
exists to answer and it cannot be answered from a member alone.

Re-measured: the figure depends on the surface, and the identity surface is the one
-----------------------------------------------------------------------------------
The V1 report put the nesting at 1,103 of 4,825 formulas. A later audit re-ran it, got
1,039 and 984, and recorded the V1 number as "not reproducible ... 6.2% high". Both
measurements are right about their own surface and the disagreement is the whole point:

===================  =====================  =====
surface measured     strict substrings      share
===================  =====================  =====
``normalized``                       1,039  21.5%
``display_form``                       984  20.4%
collapsed identity                   1,103  22.9%
===================  =====================  =====

``normalized`` carries word breaks and ``display_form`` is one edition's spelling. Neither
is the formula's identity: :mod:`~vedagraph.enrich.formulas` derives ``formula_id`` from the
*sandhi-collapsed* folded form precisely because two word divisions of the same letters are
one formula, and its maximality rule tests containment on that same collapsed form. Measured
there, V1's 1,103 reproduces exactly. The audit did not find a wrong number; it measured a
different surface and, because the number it got was smaller, read the difference as
inflation. So this module runs containment on the collapsed form, and says which surface it
measured every time it reports a count.

What makes a family: containment alone, because the shared-occurrence condition is entailed
-------------------------------------------------------------------------------------------
The obvious worry about grouping by containment alone is that a frequent short formula sits
inside longer ones it has nothing to do with, chaining unrelated phrases into one blob. So
the design question was whether containment needs a shared-occurrence condition bolted on.
It does not, and the reason is provable rather than a matter of preference.

Detection in the Formula layer is substring search on the sandhi-collapsed surface. If
formula *A* is a strict substring of formula *B*, then every mantra whose text contains *B*
contains *A*, so ``occ(B)`` must be a subset of ``occ(A)``. Measured over every containment
pair in the artifact: **1,593 of 1,593 pairs satisfy it, with no exceptions.** A
shared-occurrence condition is therefore not an independent test of anything -- containment
already implies the strongest form of it -- and adding one only re-expresses the frequency
ratio of the two members. Measured, that ratio cuts real phraseology:

==================================  =====  ========  =======  ==========
rule                                pairs  families  members  unfamilied
==================================  =====  ========  =======  ==========
containment alone                    1593       720     2037        2788
containment + occurrence coverage    1591       720     2036        2789
   >= 0.05
containment + coverage >= 0.10        1544       721     2021        2804
containment + coverage >= 0.20        1471       735     1988        2837
containment + coverage >= 0.50        1146       692     1714        3111
==================================  =====  ========  =======  ==========

A coverage floor buys at most 15 extra families and costs up to 323 members, and the first
links it cuts are the corpus's commonest refrain: ``pāta svastibhiḥ sadā naḥ`` occurs in 93
mantras and ``me yūyam pāta svastibhiḥ sadā naḥ`` in 3, a coverage of 0.032, and they are
the same refrain with one more word in front of it. The blob never materialises either --
measured, the largest containment component has 14 members (``viśvā bhuvanā`` and its
expansions, which is exactly one piece of phraseology) and 2,788 of 4,825 formulas are in no
containment relation at all. Containment alone it is.

Picking the representative without depending on input order
-----------------------------------------------------------
The core is defined as the shortest form that recurs *independently*, and the monotonicity
above turns that into a computation with no free parameters. Because ``occ`` only shrinks as
a string grows, the member with the largest distinct-mantra count is always a *minimal*
element of the family's containment order -- if some shorter member *A* were contained in
the argmax *M*, then ``|occ(A)| >= |occ(M)|``, so ``occ(A) = occ(M)``, and maximality would
already have collapsed *A* into *M*. The rule is therefore just:

    largest distinct-mantra count, then shortest collapsed form, then the collapsed form
    itself

and the last component is the member's own identity, so no two members can swap places
between runs. :func:`_pick_representative` asserts the minimality it derives rather than
trusting it, and the run report counts violations; on this artifact the count is 0.

Roles: containment classifies every member, and a family may have more than one core
------------------------------------------------------------------------------------
The first version of this module defined ``EXPANSION`` as "strictly contains the
*representative*" and swept everything else into ``VARIANT`` under a similarity floor. That
was wrong, and measurably so: 188 of the 241 members it called variants turned out to be
strict substrings of some *non-core* member, so their membership was justified by exact
containment and the floor was throwing away the strongest evidence in the layer. What the
structure actually supports is this, and it needs no threshold at all:

``CORE``
    A minimal element: it strictly contains no other member. Measured, 918 of the 2,037
    members.
``EXPANSION``
    Strictly contains at least one member, and therefore -- by transitivity -- at least one
    core. Measured, the remaining 1,119.

Every member is one or the other, and the count of members that are neither is **0 of
2,037**, which is checked on every run rather than assumed. The consequence worth stating
plainly is that a family can have several cores: 157 of 720 families do, because two
independently-recurring short forms meet inside one longer attested phrase --
``tasya devasya`` (26 mantras) and ``ya evaṃ vidvāṃsaṃ`` both sit inside
``tasya devasya kruddhasyaitad āgo ya evaṃ vidvāṃsaṃ``. That is a fact about the corpus and
not redundancy, so it is reported rather than resolved: 208 expansions contain more than one
core, so there is no non-arbitrary way to split such a family, and inventing one would make
membership depend on a tie-break.

The similarity threshold survives, doing a much smaller and much better-defined job:

``VARIANT``
    A minimal element that is *not* the representative and whose similarity to a core
    already in the family reaches the floor -- that is, a second spelling of a core rather
    than a second core. ``vayaṃ dviṣmas`` beside ``vayaṃ dviṣmaḥ`` is one; neither contains
    the other, because they differ in their last character.

The metric is the cross-Veda layer's own blend, ``0.5 * ngram_jaccard + 0.5 * lcs_ratio``,
imported rather than restated, and the floor is
:data:`~vedagraph.enrich.guards.NEAR_PARALLEL_FLOOR`, already this repository's answer to
"below this, two texts are not related, only in the same register". The surface is named on
every member row and it is ``SANDHI_INSENSITIVE``, because that is the surface containment
ran on. Measured, the floor separates **4** variants from **194** secondary cores, and the
gap it separates them across is real: the four variants score 0.763 to 0.858 while the
secondary cores have a median similarity of 0.565 to the nearest core. A layer that needed
this role for hundreds of members would be a clustering layer wearing a containment
layer's name; needing it for four is the honest size of the orthographic residual that
:mod:`~vedagraph.enrich.formulas` documents one level down.

Nothing is rejected on similarity. A member below the floor becomes a secondary core, which
is a weaker claim about the same membership, not an exclusion -- and no formula is ever
dropped, because dropping a row from a written artifact is not this layer's decision. The
one exclusion the layer does make is structural: a formula in no containment relation at all
is left *unfamilied* and counted, and that is 2,788 of 4,825.

``occurrence``, the fourth thing the brief names, is deliberately not a role here: one
passage using one member is already a ``USES_FORMULA`` row, and re-emitting it would
duplicate 22,686 edges to say nothing new. Families carry the *aggregate* instead -- the
distinct mantras and per-Veda counts of the union of their members -- and that aggregate is
the thing no member row can answer.

Cross-Veda spread is a family property, and it is checked against the parallel layer
------------------------------------------------------------------------------------
``veda_counts`` on a family is the union of its members' mantras bucketed by Veda, not the
sum of its members' counts: the members overlap heavily by construction, so summing would
inflate every family by roughly its member count. Where a family claims two or more Vedas,
``parallel_corroborated`` records whether the cross-Veda parallel layer independently
connects two of the family's own mantras across a Veda boundary. That is a second opinion
from a different derivation, and a family claiming cross-Veda spread with no corroborating
parallel is the shape a spurious claim would have.

Determinism
-----------
Every intermediate is sorted before it can reach the output, no set or dict iteration order
is observable, and the union-find always attaches the larger identity to the smaller, so the
component representative does not depend on the order pairs were discovered in.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Final

from vedagraph.enrich.corpus import VEDAS
from vedagraph.enrich.crossveda import (
    LCS_WEIGHT,
    NGRAM_WEIGHT,
    character_ngrams,
    jaccard,
    lcs_length,
)
from vedagraph.enrich.guards import (
    MAX_FORMULA_CORPUS_SHARE,
    MIN_FORMULA_WORDS,
    NEAR_PARALLEL_FLOOR,
)
from vedagraph.enrich.provenance import (
    AssertionState,
    EvidenceSpan,
    Provenance,
    RunReport,
    TrustClass,
    run_id,
    stable_id,
)
from vedagraph.enrich.surfaces import MatchLevel

STAGE: Final = "formula-families"

#: Named on every FormulaFamily node. Both halves matter: a family found by grouping
#: containment components is not comparable with one found by clustering similarity.
DERIVATION_METHOD: Final = "collapsed-containment-components-v1"

#: One method name per role, because a membership justified by containment and one
#: justified by a similarity measurement are different kinds of claim, and
#: :class:`~vedagraph.enrich.provenance.Provenance` scores are only comparable within a
#: method.
MEMBERSHIP_METHOD_CORE: Final = "formula-family-core-v1"
MEMBERSHIP_METHOD_EXPANSION: Final = "formula-family-expansion-by-containment-v1"
MEMBERSHIP_METHOD_VARIANT: Final = "formula-family-variant-by-similarity-v1"

#: The surface containment and variant similarity are both measured on. Stored on every
#: member row: a reader must never have to guess which surface a family was built on.
FAMILY_MATCH_LEVEL: Final = MatchLevel.SANDHI_INSENSITIVE

#: Members a family needs to exist. A component of one is not a family, it is a formula, and
#: calling it a family of one would put 2,788 of 4,825 formulas into single-member families
#: and make every family count meaningless. Those 2,788 are reported as unfamilied instead.
MIN_FAMILY_MEMBERS: Final = 2

#: Similarity a ``VARIANT`` member needs against its nearest family member. Imported, not
#: chosen: this is the cross-Veda layer's floor for "related at all rather than merely in the
#: same register", and a variant is exactly a claim of relatedness without containment.
VARIANT_SIMILARITY_FLOOR: Final = NEAR_PARALLEL_FLOOR

#: Membership confidence for the two roles containment justifies outright. Containment on the
#: identity surface is not a similarity estimate, so these are asserted at 1.0 and the gap
#: between them and a variant's measured similarity is the honest difference in evidence.
CONTAINMENT_CONFIDENCE: Final = 1.0

#: Evidence spans stored on a family. Filled across distinct Vedas first, so a family
#: claiming cross-Veda spread proves it from the node alone.
MAX_FAMILY_EVIDENCE_SPANS: Final = 4

#: Separator used to fast-reject containment candidates in one pass. Formula surfaces are
#: single-line by construction; :func:`_containment_pairs` asserts it rather than assuming.
_JOIN_SEPARATOR: Final = "\n"

#: Tokens whose per-Veda document frequency exceeds ``MAX_FORMULA_CORPUS_SHARE`` -- the share
#: at which :mod:`~vedagraph.enrich.guards` already declares a span to be a Veda's grammar
#: rather than its phraseology. Measured over the 20,210-mantra corpus, the whole set is nine
#: tokens, so this is an enumeration produced by measurement rather than a hand-written
#: stoplist:
#:
#: ===========  =====  ==============================================
#: token        share  class
#: ===========  =====  ==============================================
#: ``ā``        .1821  preverb
#: ``na``       .1647  negation / comparative particle
#: ``te``       .1490  enclitic pronoun
#: ``tvā``      .1246  enclitic pronoun
#: ``ca``       .1202  conjunction
#: ``no``       .1075  enclitic pronoun
#: ``indra``    .0896  **theonym -- deliberately excluded, see below**
#: ``pra``      .0861  preverb
#: ``sa``       .0827  pronoun
#: ===========  =====  ==============================================
#:
#: ``indra`` is the one content word above the line and it is left out, because its pairs are
#: attested vocative formulae rather than a word plus its grammar: ``maghavann indra`` stands
#: in 19 mantras of all four Vedas and ``sakhāya indra`` in 20. Including it would take the
#: recommendation from 59 formulas to 97 and 50 cross-Veda claims to 83, so the count is
#: reported both ways in the report and the exclusion is stated rather than buried.
CLOSED_CLASS_ABOVE_GRAMMAR_LINE: Final[frozenset[str]] = frozenset(
    {"ā", "na", "te", "tvā", "ca", "no", "pra", "sa"}
)

#: Word count at which a formula carries one content word at most. Equal to the mining floor,
#: because that is the only length at which a single grammar token can be half the formula.
_SHORT_FORMULA_WORDS: Final = MIN_FORMULA_WORDS


class MemberRole(StrEnum):
    """What one formula is to its family.

    Listed in the order roles are assigned, which is also the order members are written in.
    """

    #: A minimal element: strictly contains no other member, so it recurs independently of
    #: every longer form in the family. One core per family is the *representative*; the rest
    #: are secondary cores, and the family row counts them.
    CORE = "CORE"
    #: Strictly contains at least one member and therefore at least one core. Justified by
    #: containment alone, so no similarity is consulted.
    EXPANSION = "EXPANSION"
    #: A minimal element close enough to a core to be a second spelling of it rather than a
    #: second core. The only role whose assignment rests on a similarity measurement.
    VARIANT = "VARIANT"


@dataclass(frozen=True)
class _Member:
    """One Formula artifact row, reduced to what family construction reads.

    ``identity`` is the collapsed form: ``normalized`` with its word breaks removed. That is
    the readable image of the string ``formula_id`` was derived from, and containment on it
    is exactly containment on the folded form, because
    :mod:`~vedagraph.enrich.formulas` renders the four comparison sentinels through an
    injective per-character map and no folded string contains their targets. A per-character
    bijection preserves the substring relation in both directions, so nothing is lost by
    working on the readable side -- and :func:`_index_members` refuses to proceed if two
    formulas ever collapse to one identity, which is the only way that argument could fail.
    """

    formula_id: str
    identity: str
    normalized: str
    display_form: str
    word_count: int
    mantras: frozenset[str]
    veda_counts: Mapping[str, int]

    @property
    def mantra_count(self) -> int:
        return len(self.mantras)


@dataclass(frozen=True)
class FormulaFamilyRow:
    """One piece of phraseology, and the formulas that are versions of it."""

    family_id: str
    representative_formula_id: str
    #: The core's readable comparison form and one attested spelling of it, carried on the
    #: family so that naming a family costs no traversal.
    representative_normalized: str
    representative_display_form: str
    member_count: int
    core_count: int
    #: Cores beyond the representative: distinct short forms that recur independently and
    #: meet inside a longer member. Non-zero on 157 of 720 families, and the reason this
    #: layer does not claim one family is one phrase.
    secondary_core_count: int
    expansion_count: int
    variant_count: int
    min_word_count: int
    max_word_count: int
    #: Longest chain of strict containments inside the family. 1 means every non-core member
    #: sits directly on the core.
    containment_depth: int
    #: Distinct mantras using *any* member. The union, not the sum: members overlap by
    #: construction and summing would inflate a family by roughly its member count.
    mantra_count: int
    #: ``USES_FORMULA`` rows the family covers. Larger than ``mantra_count`` by exactly the
    #: double-counting the family layer exists to resolve.
    occurrence_count: int
    vedas: tuple[str, ...]
    veda_counts: Mapping[str, int]
    veda_span: int
    cross_veda: bool
    #: Share of the family's mantras the core alone accounts for. 1.0 for a pure containment
    #: tree; below 1.0 exactly when a variant is attested where the core is not.
    representative_coverage: float
    #: True when the cross-Veda parallel layer independently connects two of this family's
    #: own mantras across a Veda boundary. Always false for a single-Veda family.
    parallel_corroborated: bool
    derivation_method: str
    provenance: Provenance

    def as_row(self) -> dict[str, Any]:
        return {
            "family_id": self.family_id,
            "representative_formula_id": self.representative_formula_id,
            "representative_normalized": self.representative_normalized,
            "representative_display_form": self.representative_display_form,
            "member_count": self.member_count,
            "core_count": self.core_count,
            "secondary_core_count": self.secondary_core_count,
            "expansion_count": self.expansion_count,
            "variant_count": self.variant_count,
            "min_word_count": self.min_word_count,
            "max_word_count": self.max_word_count,
            "containment_depth": self.containment_depth,
            "mantra_count": self.mantra_count,
            "occurrence_count": self.occurrence_count,
            "vedas": list(self.vedas),
            "veda_counts": dict(sorted(self.veda_counts.items())),
            "veda_span": self.veda_span,
            "cross_veda": self.cross_veda,
            "representative_coverage": round(self.representative_coverage, 6),
            "parallel_corroborated": self.parallel_corroborated,
            "derivation_method": self.derivation_method,
            **self.provenance.as_dict(),
        }


@dataclass(frozen=True)
class FormulaFamilyMemberRow:
    """One formula's membership of one family."""

    family_id: str
    formula_id: str
    role: str
    normalized: str
    display_form: str
    word_count: int
    mantra_count: int
    #: The family member this membership is measured against: the core for a ``CORE`` or
    #: ``EXPANSION`` row, the nearest member for a ``VARIANT`` row.
    linked_formula_id: str
    #: 1.0 where containment justifies the membership, the measured blend for a variant.
    similarity: float
    #: The surface ``similarity`` and the containment test were both computed on.
    match_level: str
    provenance: Provenance

    def as_row(self) -> dict[str, Any]:
        return {
            "membership_id": stable_id("formula-family-member", self.family_id, self.formula_id),
            "family_id": self.family_id,
            "formula_id": self.formula_id,
            "role": self.role,
            "normalized": self.normalized,
            "display_form": self.display_form,
            "word_count": self.word_count,
            "mantra_count": self.mantra_count,
            "linked_formula_id": self.linked_formula_id,
            "similarity": round(self.similarity, 6),
            "match_level": self.match_level,
            **self.provenance.as_dict(),
        }


@dataclass(frozen=True)
class RemovalRecommendation:
    """One formula this layer would drop, and the measurement that says so.

    Emitted as a recommendation and never acted on. Deleting a row from a sealed source
    artifact is not this module's decision, and a recommendation carrying its own evidence is
    reviewable in a way a silent drop is not.
    """

    formula_id: str
    normalized: str
    rule: str
    grammar_token: str
    grammar_token_share: float
    mantra_count: int
    occurrence_count: int
    vedas: tuple[str, ...]
    cross_veda: bool

    def as_row(self) -> dict[str, Any]:
        return {
            "formula_id": self.formula_id,
            "normalized": self.normalized,
            "rule": self.rule,
            "grammar_token": self.grammar_token,
            "grammar_token_share": round(self.grammar_token_share, 6),
            "mantra_count": self.mantra_count,
            "occurrence_count": self.occurrence_count,
            "vedas": list(self.vedas),
            "cross_veda": self.cross_veda,
        }


@dataclass
class _Family:
    """A containment component, before roles and rows."""

    members: tuple[_Member, ...]
    representative: _Member
    roles: Mapping[str, MemberRole]
    links: Mapping[str, tuple[str, float]]
    depth: int
    mantras: frozenset[str] = field(default_factory=frozenset)


def _identity(normalized: str) -> str:
    """The collapsed identity form of a formula, from its ``normalized`` property.

    Word breaks are the only difference between the two, and dropping them is what makes
    ``devīr abhiṣṭaye`` and whatever the Samaveda prints one string rather than two.
    """
    return "".join(normalized.split())


def _index_members(
    formulas: Sequence[Mapping[str, Any]],
    occurrences: Sequence[Mapping[str, Any]],
) -> tuple[tuple[_Member, ...], dict[str, int]]:
    """Reduce the two source artifacts to members, and count occurrence rows per formula.

    Occurrence *rows* are counted separately from mantras because they are different facts:
    ``mantra_count`` on a family is the union of its members' passages, while the occurrence
    count is how many ``USES_FORMULA`` rows the family covers, and the difference between
    them is the double-counting this layer resolves.

    Raises if two formulas collapse to one identity. Nothing downstream would notice --
    containment would simply behave as if the two were the same string -- and the whole
    argument for working on the readable surface rests on that never happening.
    """
    mantras: dict[str, set[str]] = {}
    occurrence_counts: dict[str, int] = {}
    for row in occurrences:
        formula_id = str(row["formula_id"])
        mantras.setdefault(formula_id, set()).add(str(row["passage_key"]))
        occurrence_counts[formula_id] = occurrence_counts.get(formula_id, 0) + 1

    members: list[_Member] = []
    seen: dict[str, str] = {}
    for row in formulas:
        formula_id = str(row["formula_id"])
        normalized = str(row["normalized"])
        identity = _identity(normalized)
        collision = seen.setdefault(identity, formula_id)
        if collision != formula_id:
            raise ValueError(
                f"two formulas share the collapsed identity {identity!r}: "
                f"{collision} and {formula_id}"
            )
        counts = row.get("veda_counts") or {}
        members.append(
            _Member(
                formula_id=formula_id,
                identity=identity,
                normalized=normalized,
                display_form=str(row["display_form"]),
                word_count=int(row["word_count"]),
                mantras=frozenset(mantras.get(formula_id, ())),
                veda_counts={str(key): int(value) for key, value in counts.items()},
            )
        )
    members.sort(key=lambda member: member.identity)
    return tuple(members), occurrence_counts


def _containment_pairs(members: Sequence[_Member]) -> tuple[tuple[str, str], ...]:
    """Every ``(contained, container)`` pair of identities, shortest first.

    The naive form is 11.6 million ``in`` tests. The same trick :func:`~vedagraph.enrich.
    formulas._scan_sandhi` uses applies here: a candidate can only be contained in a
    *strictly longer* string, so joining all longer identities into one text and testing
    membership of that text once rejects the overwhelming majority of candidates before any
    pair is examined. Measured on the artifact, 4,825 identities yield 1,593 pairs.

    Equal-length strings are never compared, which is correct rather than an optimisation:
    strict containment between two strings of the same length would require them to be
    equal, and :func:`_index_members` has already established that they are not.
    """
    assert all(_JOIN_SEPARATOR not in member.identity for member in members), (
        "a formula identity contains the join separator"
    )
    by_length: dict[int, list[str]] = {}
    for member in members:
        by_length.setdefault(len(member.identity), []).append(member.identity)
    lengths = sorted(by_length)
    pairs: list[tuple[str, str]] = []
    for position, length in enumerate(lengths):
        longer = [
            identity for later in lengths[position + 1 :] for identity in sorted(by_length[later])
        ]
        if not longer:
            continue
        haystack = _JOIN_SEPARATOR.join(longer)
        for contained in sorted(by_length[length]):
            if contained not in haystack:
                continue
            pairs.extend((contained, container) for container in longer if contained in container)
    pairs.sort()
    return tuple(pairs)


def _components(
    identities: Sequence[str], pairs: Iterable[tuple[str, str]]
) -> dict[str, tuple[str, ...]]:
    """Connected components of the containment graph, keyed by their smallest identity.

    Union-find with the larger identity attached to the smaller, so the key of a component
    is a property of its contents rather than of the order the pairs arrived in.
    """
    parent = {identity: identity for identity in identities}

    def find(node: str) -> str:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for left, right in pairs:
        roots = sorted((find(left), find(right)))
        if roots[0] != roots[1]:
            parent[roots[1]] = roots[0]
    grouped: dict[str, list[str]] = {}
    for identity in sorted(identities):
        grouped.setdefault(find(identity), []).append(identity)
    return {key: tuple(sorted(value)) for key, value in sorted(grouped.items())}


def _pick_representative(members: Sequence[_Member], report: RunReport) -> _Member:
    """The family's core: widest recurrence, then shortest form, then its own identity.

    The minimality this rule is supposed to deliver is derived in the module docstring, and
    checked here rather than trusted: nothing in the artifact guarantees that the Formula
    layer's maximality rule ran, and if it had not, the argmax could sit above a shorter
    member with an identical occurrence set. A violation is counted and the choice stands,
    because a wrong role label is recoverable and a crashed stage is not.
    """
    representative = min(
        members,
        key=lambda member: (-member.mantra_count, len(member.identity), member.identity),
    )
    for member in members:
        if member.identity == representative.identity:
            continue
        if member.identity in representative.identity:
            report.reject("member_contained_in_representative")
    return representative


def _similarity(left: str, right: str) -> float:
    """The cross-Veda layer's blend, on two formula identities.

    Imported rather than restated so that "how similar" means the same thing in this layer
    as it does in the layer whose floor is being reused.
    """
    longest = max(len(left), len(right))
    if not longest:
        return 0.0
    ngram = jaccard(character_ngrams(left), character_ngrams(right))
    return NGRAM_WEIGHT * ngram + LCS_WEIGHT * (lcs_length(left, right) / longest)


def _containment_depth(identities: Sequence[str], pairs: Sequence[tuple[str, str]]) -> int:
    """Longest chain of strict containments inside one family.

    Reported because a depth of 1 and a depth of 4 are different findings about the same
    member count: the first is a core with parallel expansions, the second is an expansion of
    an expansion, which is what the corpus does with its longest refrains.
    """
    inside = set(identities)
    successors: dict[str, list[str]] = {}
    for contained, container in pairs:
        if contained in inside and container in inside:
            successors.setdefault(contained, []).append(container)
    memo: dict[str, int] = {}

    def longest(identity: str) -> int:
        cached = memo.get(identity)
        if cached is not None:
            return cached
        memo[identity] = 1 + max((longest(nxt) for nxt in successors.get(identity, ())), default=0)
        return memo[identity]

    return max((longest(identity) for identity in sorted(inside)), default=1)


def _assign_roles(
    members: Sequence[_Member], representative: _Member, report: RunReport
) -> tuple[dict[str, MemberRole], dict[str, tuple[str, float]]]:
    """Label every member, and link it to the member its membership is measured against.

    Two passes, because the second depends on the first. Containment settles every
    ``EXPANSION`` outright, and each expansion is linked to its *immediate* parent -- the
    longest member it strictly contains -- so the member rows reconstruct the family's
    containment tree rather than a star around the core.

    The minimal elements are then walked in a fixed order, representative first and the rest
    by the same rank key, and each is a ``VARIANT`` of an already-assigned core if it reaches
    :data:`VARIANT_SIMILARITY_FLOOR` against one and a secondary ``CORE`` if it does not. The
    walk is greedy, which would matter if the order were not fixed; it is fixed, and the
    ordering key ends in the member's own identity, so the assignment is a function of the
    family's contents alone.
    """
    inside = {member.identity for member in members}
    roles: dict[str, MemberRole] = {}
    links: dict[str, tuple[str, float]] = {}
    minimal: list[_Member] = []
    for member in members:
        contained = sorted(
            (other for other in inside if other != member.identity and other in member.identity),
            key=lambda identity: (-len(identity), identity),
        )
        if not contained:
            minimal.append(member)
            continue
        parent = next(other for other in members if other.identity == contained[0])
        roles[member.formula_id] = MemberRole.EXPANSION
        links[member.formula_id] = (parent.formula_id, CONTAINMENT_CONFIDENCE)

    ordered = sorted(
        minimal,
        key=lambda member: (
            member.identity != representative.identity,
            -member.mantra_count,
            len(member.identity),
            member.identity,
        ),
    )
    cores: list[_Member] = []
    for member in ordered:
        score, nearest = max(
            ((_similarity(member.identity, core.identity), core.formula_id) for core in cores),
            default=(0.0, member.formula_id),
        )
        if cores and score >= VARIANT_SIMILARITY_FLOOR:
            roles[member.formula_id] = MemberRole.VARIANT
            links[member.formula_id] = (nearest, score)
            continue
        roles[member.formula_id] = MemberRole.CORE
        links[member.formula_id] = (
            (member.formula_id, CONTAINMENT_CONFIDENCE) if not cores else (nearest, score)
        )
        if cores:
            report.reject("secondary_core_below_variant_similarity_floor")
        cores.append(member)

    unlabelled = [member for member in members if member.formula_id not in roles]
    if unlabelled:
        report.reject("member_unclassified_by_containment", len(unlabelled))
        for member in unlabelled:
            roles[member.formula_id] = MemberRole.CORE
            links[member.formula_id] = (member.formula_id, CONTAINMENT_CONFIDENCE)
    return roles, links


def _veda_of(passage_key: str) -> str:
    """The Veda a canonical passage key belongs to.

    Keys are ``VG:<VEDA>:...``. Read from the key rather than joined back to the occurrence
    rows because a family's mantra set is a union over members and the join would have to be
    repeated per member for a fact the key already states.
    """
    parts = passage_key.split(":")
    return parts[1] if len(parts) > 2 else ""


def _parallel_index(parallels: Sequence[Mapping[str, Any]]) -> dict[str, frozenset[str]]:
    """Cross-Veda parallel partners per mantra, both directions.

    Both directions, because 1,684 of the 6,271 parallel rows are directed
    ``REUSES_TEXT_FROM`` mirrors and a family corroborated only in the mirrored direction is
    corroborated.
    """
    grouped: dict[str, set[str]] = {}
    for row in parallels:
        subject = str(row["subject_key"])
        obj = str(row["object_key"])
        grouped.setdefault(subject, set()).add(obj)
        grouped.setdefault(obj, set()).add(subject)
    return {key: frozenset(value) for key, value in sorted(grouped.items())}


def _corroborated(mantras: frozenset[str], index: Mapping[str, frozenset[str]]) -> bool:
    """True when a parallel connects two of these mantras across a Veda boundary."""
    for mantra in sorted(mantras):
        veda = _veda_of(mantra)
        for partner in index.get(mantra, frozenset()):
            if partner in mantras and _veda_of(partner) != veda:
                return True
    return False


def _family_evidence(
    family: _Family, occurrence_index: Mapping[str, tuple[tuple[str, str, str], ...]]
) -> tuple[EvidenceSpan, ...]:
    """One quoted occurrence per Veda the family claims, then fill in order.

    Quotes come from the members' own ``USES_FORMULA`` rows, which already hold an attested
    span and the surface it was matched on, so the family's evidence is the Formula layer's
    evidence rather than a fresh derivation that could disagree with it.

    Drawn from *every* member and not only from the core, which is the whole point and was
    got wrong first time round. A family's Veda set is the union over its members, so a
    family can claim four Vedas while its core reaches three -- ``agnir mūrdhā divaḥ`` is one
    -- and evidence taken from the core alone then fails to prove the node's own headline
    property. ``tests/enrich/test_formula_families.py`` asserts the coverage rather than
    trusting it. Within a Veda the core's occurrence is preferred, so a reader still sees the
    phrase the family is named after wherever that is possible.
    """
    candidates: list[tuple[str, bool, tuple[str, str, str]]] = []
    for member in family.members:
        is_core = member.formula_id == family.representative.formula_id
        for entry in occurrence_index.get(member.formula_id, ()):
            candidates.append((_veda_of(entry[0]), not is_core, entry))
    if not candidates:
        return (
            EvidenceSpan(
                locator=family.representative.formula_id,
                surface=str(FAMILY_MATCH_LEVEL),
                quote=family.representative.display_form,
            ),
        )
    ranked = sorted(candidates, key=lambda item: (item[1], item[2]))
    chosen: list[tuple[str, str, str]] = []
    for veda in VEDAS:
        if len(chosen) >= MAX_FAMILY_EVIDENCE_SPANS:
            break
        first = next((item[2] for item in ranked if item[0] == veda), None)
        if first is not None:
            chosen.append(first)
    for _, _, entry in ranked:
        if len(chosen) >= MAX_FAMILY_EVIDENCE_SPANS:
            break
        if entry not in chosen:
            chosen.append(entry)
    return tuple(
        EvidenceSpan(locator=locator, surface=surface, quote=quote)
        for locator, surface, quote in sorted(chosen)
    )


def _occurrence_index(
    occurrences: Sequence[Mapping[str, Any]],
) -> dict[str, tuple[tuple[str, str, str], ...]]:
    """Per formula, its occurrence rows as ``(passage_key, surface, quote)``, sorted."""
    grouped: dict[str, list[tuple[str, str, str]]] = {}
    for row in occurrences:
        surface = (
            MatchLevel.SCRIPT_FOLDED
            if "word-aligned" in str(row.get("method", ""))
            else MatchLevel.SANDHI_INSENSITIVE
        )
        grouped.setdefault(str(row["formula_id"]), []).append(
            (str(row["passage_key"]), str(surface), str(row.get("source_form", "")))
        )
    return {key: tuple(sorted(value)) for key, value in sorted(grouped.items())}


def recommend_removals(
    formulas: Sequence[Mapping[str, Any]],
    occurrence_counts: Mapping[str, int],
    token_shares: Mapping[str, float],
) -> tuple[RemovalRecommendation, ...]:
    """Formulas that are one content word plus one token of grammar.

    ``token_shares`` is the maximum per-Veda *document* frequency of each token of the
    comparison surface, measured by the caller over the corpus rather than over the formula
    artifact, because the question is how ordinary a token is in the Veda and not how often
    it turns up inside a formula.

    The rule applies the guards' own reasoning one level down. If a *span* occurring in more
    than :data:`~vedagraph.enrich.guards.MAX_FORMULA_CORPUS_SHARE` of a Veda is that Veda's
    grammar, then a two-word span half of which is above that line is half grammar, and the
    node carries one word of content. Measured on the artifact this flags 59 formulas and 296
    occurrence rows, and what it flags is a theonym orbited by a rotating particle:
    ``ā mitrāvaruṇā`` and ``no mitrāvaruṇā`` stand in 16 mantras each and
    ``te dyāvāpṛthivī``, ``dyāvāpṛthivī ā`` and ``no dyāvāpṛthivī`` in 15, 10 and 9 -- five
    separate cross-Veda "formulae" for two words.

    It is returned rather than applied, and the run report carries the count. Longer formulas
    are deliberately out of scope: at three words the same rule flags 314 nodes, most of them
    real refrains where a particle is genuinely part of the phrase.
    """
    recommendations: list[RemovalRecommendation] = []
    for row in formulas:
        if int(row["word_count"]) != _SHORT_FORMULA_WORDS:
            continue
        tokens = str(row["normalized"]).split()
        flagged = sorted(token for token in tokens if token in CLOSED_CLASS_ABOVE_GRAMMAR_LINE)
        if not flagged:
            continue
        token = flagged[0]
        formula_id = str(row["formula_id"])
        recommendations.append(
            RemovalRecommendation(
                formula_id=formula_id,
                normalized=str(row["normalized"]),
                rule=(
                    f"{_SHORT_FORMULA_WORDS}-word formula one of whose tokens exceeds "
                    f"MAX_FORMULA_CORPUS_SHARE={MAX_FORMULA_CORPUS_SHARE} document frequency "
                    f"in some Veda and is closed-class"
                ),
                grammar_token=token,
                grammar_token_share=token_shares.get(token, 0.0),
                mantra_count=int(row["mantra_count"]),
                occurrence_count=occurrence_counts.get(formula_id, 0),
                vedas=tuple(str(veda) for veda in row.get("vedas", ())),
                cross_veda=bool(row.get("cross_veda", False)),
            )
        )
    recommendations.sort(key=lambda item: (-item.mantra_count, item.normalized))
    return tuple(recommendations)


def build_formula_families(
    formulas: Sequence[Mapping[str, Any]],
    occurrences: Sequence[Mapping[str, Any]],
    parallels: Sequence[Mapping[str, Any]] = (),
    token_shares: Mapping[str, float] | None = None,
) -> tuple[list[FormulaFamilyRow], list[FormulaFamilyMemberRow], RunReport]:
    """Group the Formula artifact into families and report what was left out.

    Reads the written artifacts rather than the graph, so a family is a function of the same
    inputs the Formula layer was, and two runs over unchanged artifacts produce byte-identical
    output. ``parallels`` is optional and only sets ``parallel_corroborated``; ``token_shares``
    is optional and only sizes the removal recommendation in the report.

    Output is sorted by the core's ``normalized`` form and, within a family, by role and then
    by member identity -- a content ordering rather than a rank ordering, so adding one
    formula upstream does not reshuffle the whole artifact and destroy the diff.
    """
    report = RunReport(stage=STAGE)
    members, occurrence_counts = _index_members(formulas, occurrences)
    identifier = run_id(STAGE, len(members), len(occurrences), DERIVATION_METHOD)
    by_identity = {member.identity: member for member in members}

    pairs = _containment_pairs(members)
    components = _components([member.identity for member in members], pairs)

    families: list[_Family] = []
    unfamilied = 0
    for identities in components.values():
        if len(identities) < MIN_FAMILY_MEMBERS:
            unfamilied += len(identities)
            report.reject("formula_in_no_containment_relation", len(identities))
            continue
        group = tuple(by_identity[identity] for identity in identities)
        representative = _pick_representative(group, report)
        roles, links = _assign_roles(group, representative, report)
        families.append(
            _Family(
                members=group,
                representative=representative,
                roles=roles,
                links=links,
                depth=_containment_depth(identities, pairs),
                mantras=frozenset().union(*(member.mantras for member in group)),
            )
        )

    index = _parallel_index(parallels)
    occurrence_spans = _occurrence_index(occurrences)
    families.sort(key=lambda item: item.representative.identity)

    family_rows: list[FormulaFamilyRow] = []
    member_rows: list[FormulaFamilyMemberRow] = []
    role_totals: dict[str, int] = {str(role): 0 for role in MemberRole}
    depth_totals: dict[int, int] = {}
    span_totals: dict[int, int] = {}

    for family in families:
        family_id = stable_id("formula-family", family.representative.identity)
        veda_counts: dict[str, int] = {}
        for mantra in sorted(family.mantras):
            veda = _veda_of(mantra)
            veda_counts[veda] = veda_counts.get(veda, 0) + 1
        vedas = tuple(veda for veda in VEDAS if veda in veda_counts)
        occurrence_total = sum(
            occurrence_counts.get(member.formula_id, 0) for member in family.members
        )
        counts = {role: 0 for role in MemberRole}
        for role in family.roles.values():
            counts[role] += 1
        coverage = (
            len(family.representative.mantras) / len(family.mantras) if family.mantras else 0.0
        )
        depth_totals[family.depth] = depth_totals.get(family.depth, 0) + 1
        span_totals[len(vedas)] = span_totals.get(len(vedas), 0) + 1
        family_rows.append(
            FormulaFamilyRow(
                family_id=family_id,
                representative_formula_id=family.representative.formula_id,
                representative_normalized=family.representative.normalized,
                representative_display_form=family.representative.display_form,
                member_count=len(family.members),
                core_count=counts[MemberRole.CORE],
                secondary_core_count=max(0, counts[MemberRole.CORE] - 1),
                expansion_count=counts[MemberRole.EXPANSION],
                variant_count=counts[MemberRole.VARIANT],
                min_word_count=min(member.word_count for member in family.members),
                max_word_count=max(member.word_count for member in family.members),
                containment_depth=family.depth,
                mantra_count=len(family.mantras),
                occurrence_count=occurrence_total,
                vedas=vedas,
                veda_counts=dict(sorted(veda_counts.items())),
                veda_span=len(vedas),
                cross_veda=len(vedas) > 1,
                representative_coverage=coverage,
                parallel_corroborated=(len(vedas) > 1 and _corroborated(family.mantras, index)),
                derivation_method=DERIVATION_METHOD,
                provenance=Provenance(
                    trust=TrustClass.DETERMINISTIC_DERIVED,
                    method=DERIVATION_METHOD,
                    score=coverage,
                    evidence=_family_evidence(family, occurrence_spans),
                    state=AssertionState.ACCEPTED,
                    run_id=identifier,
                    notes=(
                        "Score is representative_coverage: the share of the family's "
                        "distinct mantras the core alone accounts for. Not a probability."
                    ),
                ),
            )
        )
        ordered = sorted(
            family.members,
            key=lambda member: (
                list(MemberRole).index(family.roles[member.formula_id]),
                member.identity,
            ),
        )
        for member in ordered:
            role = family.roles[member.formula_id]
            linked, score = family.links[member.formula_id]
            role_totals[str(role)] += 1
            method = {
                MemberRole.CORE: MEMBERSHIP_METHOD_CORE,
                MemberRole.EXPANSION: MEMBERSHIP_METHOD_EXPANSION,
                MemberRole.VARIANT: MEMBERSHIP_METHOD_VARIANT,
            }[role]
            spans = occurrence_spans.get(member.formula_id, ())
            evidence = (
                EvidenceSpan(locator=spans[0][0], surface=spans[0][1], quote=spans[0][2])
                if spans
                else EvidenceSpan(
                    locator=member.formula_id,
                    surface=str(FAMILY_MATCH_LEVEL),
                    quote=member.display_form,
                )
            )
            member_rows.append(
                FormulaFamilyMemberRow(
                    family_id=family_id,
                    formula_id=member.formula_id,
                    role=str(role),
                    normalized=member.normalized,
                    display_form=member.display_form,
                    word_count=member.word_count,
                    mantra_count=member.mantra_count,
                    linked_formula_id=linked,
                    similarity=score,
                    match_level=str(FAMILY_MATCH_LEVEL),
                    provenance=Provenance(
                        trust=TrustClass.DETERMINISTIC_DERIVED,
                        method=method,
                        score=score,
                        evidence=(evidence,),
                        state=AssertionState.ACCEPTED,
                        run_id=identifier,
                        notes=(
                            ""
                            if role is not MemberRole.VARIANT
                            else "In the family through another member, not through the "
                            f"core; similarity measured on {FAMILY_MATCH_LEVEL} against "
                            "the nearest member."
                        ),
                    ),
                )
            )

    recommendations = recommend_removals(formulas, occurrence_counts, token_shares or {})
    report.produced = len(family_rows)
    report.notes = {
        "run_id": identifier,
        "derivation": DERIVATION_METHOD,
        "containment_surface": "collapsed identity (normalized without word breaks)",
        "formulas_read": len(members),
        "occurrence_rows_read": len(occurrences),
        "containment_pairs": len(pairs),
        "formulas_strictly_contained_in_another": len({left for left, _ in pairs}),
        "formulas_strictly_containing_another": len({right for _, right in pairs}),
        "containment_components": len(components),
        "families_produced": len(family_rows),
        "family_members": len(member_rows),
        "members_by_role": dict(sorted(role_totals.items())),
        "families_with_a_secondary_core": sum(1 for row in family_rows if row.secondary_core_count),
        "secondary_cores": sum(row.secondary_core_count for row in family_rows),
        "formulas_unfamilied": unfamilied,
        "formulas_accounted_for": len(member_rows) + unfamilied,
        "families_by_containment_depth": dict(sorted(depth_totals.items())),
        "families_by_veda_span": dict(sorted(span_totals.items())),
        "cross_veda_families": sum(1 for row in family_rows if row.cross_veda),
        "cross_veda_families_parallel_corroborated": sum(
            1 for row in family_rows if row.parallel_corroborated
        ),
        "families_reaching_three_or_more_vedas": sum(
            1 for row in family_rows if row.veda_span >= 3
        ),
        "mantras_covered_by_a_family": len(
            {mantra for family in families for mantra in family.mantras}
        ),
        "occurrence_rows_covered_by_a_family": sum(row.occurrence_count for row in family_rows),
        "families_with_imperfect_representative_coverage": sum(
            1 for row in family_rows if row.representative_coverage < 1.0
        ),
        "variant_similarity_floor": VARIANT_SIMILARITY_FLOOR,
        "removal_recommendations": len(recommendations),
        "removal_recommendation_occurrence_rows": sum(
            item.occurrence_count for item in recommendations
        ),
        "removal_recommendation_cross_veda": sum(1 for item in recommendations if item.cross_veda),
    }
    return family_rows, member_rows, report
