"""Per-edge directional evidence for cross-corpus textual reuse.

The cross-Veda parallel layer identifies the *pairs*. It never measured the *direction*.
One pair was nonetheless stored as directed -- 1,684 ``REUSES_TEXT_FROM`` edges pointing
Samaveda to Rigveda -- and every one of those 1,684 edges carries the identical sentence in
``cross_veda_direction_basis``. That is a pipeline constant: it says why the *class* is
directed and nothing whatever about the edge it sits on, so no reader can tell a strongly
evidenced edge from a weak one, and the benchmark recorded exactly that.

This module supplies the missing thing: a quantity measured on each pair of verses, which
differs between edges, and which can be recomputed from the graph.

The measure: compilation asymmetry
-----------------------------------
A borrowed verse and its source differ structurally, not lexically -- the two texts are by
construction nearly identical, so nothing about the strings can point. What does point is
the company each verse keeps. A compiler assembles a unit out of verses drawn from
elsewhere, so *its* unit is largely made of counterparts and those counterparts are
scattered across many units of the other corpus. A composer's hymn is not made of anything;
only some of its verses happen to have been taken.

So for each side of a pair, measured on the side's own containing structural unit:

``unit_counterpart_share``
    verses of the unit that have at least one counterpart in the other corpus, over the
    unit's size.
``unit_dispersion``
    how many distinct units of the other corpus those counterparts fall into.

Direction is asserted from the side whose unit is substantially made of counterparts to the
side whose unit is not, and only when the gap is wide:
:data:`COMPILATION_SHARE_FLOOR` and :data:`SHARE_MARGIN`. Both numbers vary per edge, so the
evidence is per-edge by construction.

Why it is not simply run everywhere
------------------------------------
Two preconditions are checked first, and both of them refuse pairs on measured grounds
rather than on taste.

``RV_MEDIATION``
    If verse *x* in corpus P and verse *y* in corpus Q are both counterparts of one and the
    same Rigvedic verse, then P and Q share Rigvedic text and not each other's. Measured on
    this graph: 96.1% of AV-SV pairs, 95.4% of SV-YV and 83.3% of AV-YV are mediated this
    way, against 0.0% of RV-YV. Asserting a direction across a mediated pair would
    manufacture a line of transmission that the data says runs through a third corpus.

``UNIT_GRANULARITY``
    The measure is a ratio over a structural unit, so the two units have to be comparable.
    Measured: the median containing unit holds 9 verses in the Rigveda, 4 in the
    Atharvaveda, 3 in the Samaveda -- and **44** in the Yajurveda, whose smallest container
    in this graph is the adhyaya. A share taken over a 44-verse adhyaya is not the same
    instrument as a share taken over a 3-verse decade, so every Yajurvedic pair is refused.

Where the instrument is allowed to speak
-----------------------------------------
A criterion that answers everywhere answers wrongly somewhere. This one is only applied in a
scope where it demonstrates both *power* and *internal consistency*:

- power: at least :data:`SCOPE_POWER_FLOOR` edges in the scope receive a direction at all;
- consistency: at least :data:`SCOPE_CONSISTENCY_FLOOR` of those point the same way.

Evaluated at whole-pair scope first, then, if that fails, at the scope of the top structural
division of each side. Measured on this graph the procedure selects, with no corpus named in
advance:

=========================  =========  ==========  ===========
scope                      decisions  agreement   verdict
=========================  =========  ==========  ===========
RV-SV, whole pair               1212      0.991   SV -> RV
AV-RV, whole pair                480      0.763   rejected
AV-RV, Atharvaveda kanda 20      322      0.966   AV -> RV
every other AV kanda             <100         --  no power
RV-YV, whole pair                325      0.532   rejected
=========================  =========  ==========  ===========

The Samavedic result is the calibration and it is the only one with an independent answer:
the Kauthuma Arcika is an arrangement of Rigvedic verses and its own tradition names the
Rigveda as its source. The instrument, which knows none of that, agrees on 1,201 edges and
contradicts on 11. Those 11 are kept and flagged rather than hidden, because a measured
disagreement with the tradition is the most informative row in the layer -- they are
Rigvedic hymns so heavily quarried by the Samaveda that the hymn itself looks like a
compilation, which is this instrument's one known failure mode.

The Atharvavedic result falls out of the same procedure without being asked for, and lands
on the kanda whose borrowing from the Rigveda is least controversial. It is asserted for
that kanda and for nothing else: outside kanda 20 the instrument *inverts* (55 AV->RV
against 103 RV->AV), which is the honest reason not to extend it.

This is a claim about arrangement, not about chronology. It says that one unit is built out
of the other's verses. It does not date either corpus.
"""

from __future__ import annotations

import collections
import hashlib
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Final

#: The compiling side's unit must be at least this fully made of counterparts. A majority:
#: below one half the unit is not a compilation of the other corpus in any reading.
COMPILATION_SHARE_FLOOR: Final = 0.5

#: And it must exceed the other side's share by at least this much. A quarter of a unit,
#: so that two units that are similarly covered produce no direction rather than a
#: coin-flip one.
SHARE_MARGIN: Final = 0.25

#: A scope must produce at least this many directed verdicts before any of them is kept.
#: Below it, a unanimous scope is unanimous over four edges and says nothing.
SCOPE_POWER_FLOOR: Final = 100

#: And this share of them must agree. Set at the level the calibration pair clears with
#: room to spare (RV-SV measures 0.991) and the rejected pairs miss by a wide margin
#: (AV-RV whole pair 0.763, RV-YV 0.532).
SCOPE_CONSISTENCY_FLOOR: Final = 0.90

#: A corpus pair more mediated than this by a third corpus is refused outright.
MEDIATION_REFUSAL_FLOOR: Final = 0.5

#: The corpus whose text mediates the others. Named rather than discovered: it is the one
#: corpus every other one demonstrably draws on, and the mediation test is only meaningful
#: against a fixed third party.
MEDIATING_VEDA: Final = "RV"

#: Median verses per smallest structural container, above which a corpus's units are not
#: comparable with the others'. Measured: RV 9, AV 4, SV 3, YV 44.
UNIT_GRANULARITY_CEILING: Final = 20

DIRECTION_METHOD: Final = "compilation-asymmetry-v1"

#: Every refusal is one of these. A pair that receives no direction gets one of them and
#: never silence.
REFUSAL_MEDIATED: Final = "REFUSED_MEDIATED_BY_THIRD_CORPUS"
REFUSAL_UNIT_GRANULARITY: Final = "REFUSED_UNIT_GRANULARITY_INCOMPARABLE"
REFUSAL_NO_POWER: Final = "REFUSED_INSUFFICIENT_DIRECTED_VERDICTS"
REFUSAL_INCONSISTENT: Final = "REFUSED_INSTRUMENT_INCONSISTENT_IN_SCOPE"
REFUSAL_EDGE_UNDECIDED: Final = "UNDIRECTED_ASYMMETRY_BELOW_FLOOR"
REFUSAL_EDGE_CONTRADICTS: Final = "UNDIRECTED_CONTRADICTS_SCOPE_MAJORITY"


@dataclass(frozen=True)
class VersePair:
    """One undirected cross-corpus parallel, reduced to what direction measurement reads."""

    left_veda: str
    left_key: str
    left_unit: str
    right_veda: str
    right_key: str
    right_unit: str

    @property
    def pair(self) -> str:
        return "-".join(sorted((self.left_veda, self.right_veda)))

    def sides(self) -> tuple[tuple[str, str, str], tuple[str, str, str]]:
        return (
            (self.left_veda, self.left_key, self.left_unit),
            (self.right_veda, self.right_key, self.right_unit),
        )


@dataclass(frozen=True)
class EdgeEvidence:
    """The per-edge directional record. Every field is measured on this pair."""

    left_key: str
    right_key: str
    pair: str
    scope: str
    verdict: str
    subject_key: str | None
    object_key: str | None
    left_unit_counterpart_share: float
    right_unit_counterpart_share: float
    left_unit_dispersion: int
    right_unit_dispersion: int
    left_unit_size: int
    right_unit_size: int
    asymmetry: float
    reason: str | None

    def evidence_digest(self) -> str:
        """A digest of the measured record alone, so a constant is detectable by counting."""
        payload = "|".join(
            (
                f"{self.left_unit_counterpart_share:.6f}",
                f"{self.right_unit_counterpart_share:.6f}",
                str(self.left_unit_dispersion),
                str(self.right_unit_dispersion),
                str(self.left_unit_size),
                str(self.right_unit_size),
                f"{self.asymmetry:.6f}",
            )
        )
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def as_row(self) -> dict[str, object]:
        return {
            "left_key": self.left_key,
            "right_key": self.right_key,
            "pair": self.pair,
            "scope": self.scope,
            "verdict": self.verdict,
            "subject_key": self.subject_key,
            "object_key": self.object_key,
            "direction_method": DIRECTION_METHOD,
            "left_unit_counterpart_share": round(self.left_unit_counterpart_share, 6),
            "right_unit_counterpart_share": round(self.right_unit_counterpart_share, 6),
            "left_unit_dispersion": self.left_unit_dispersion,
            "right_unit_dispersion": self.right_unit_dispersion,
            "left_unit_size": self.left_unit_size,
            "right_unit_size": self.right_unit_size,
            "asymmetry": round(self.asymmetry, 6),
            "evidence_digest": self.evidence_digest(),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class PairVerdict:
    """One corpus pair's outcome, with the measured reason when it is a refusal."""

    pair: str
    status: str
    scopes: tuple[str, ...]
    directed_edges: int
    undirected_edges: int
    mediation_share: float | None
    decisions: int
    agreement: float | None
    note: str

    def as_row(self) -> dict[str, object]:
        return {
            "pair": self.pair,
            "status": self.status,
            "scopes_directed": list(self.scopes),
            "directed_edges": self.directed_edges,
            "undirected_edges": self.undirected_edges,
            "mediation_share": (
                None if self.mediation_share is None else round(self.mediation_share, 6)
            ),
            "scope_decisions": self.decisions,
            "scope_agreement": None if self.agreement is None else round(self.agreement, 6),
            "direction_method": DIRECTION_METHOD,
            "note": self.note,
        }


def top_division(canonical_key: str) -> str:
    """The top structural division of a canonical key: ``VG:AV:SAU:K20:S001:V003`` -> K20.

    Used only to subdivide a corpus pair the instrument could not decide whole. Keys are
    colon-delimited with corpus and recension in the first three fields, so the fourth is
    the first division; a key that does not have one is its own division.
    """
    parts = canonical_key.split(":")
    return parts[3] if len(parts) > 4 else canonical_key


def median_unit_size(unit_sizes: Mapping[str, int], veda: str) -> float:
    """Median verses per structural unit for one corpus, from the unit sizes given."""
    sizes = sorted(size for unit, size in unit_sizes.items() if unit.split(":")[1:2] == [veda])
    if not sizes:
        return 0.0
    middle = len(sizes) // 2
    if len(sizes) % 2:
        return float(sizes[middle])
    return (sizes[middle - 1] + sizes[middle]) / 2


def mediation_share(pairs: Sequence[VersePair], pair_name: str) -> float:
    """Share of one pair's verses that are both counterparts of one mediating-corpus verse.

    Zero rather than undefined when the mediating corpus is one of the two: a pair cannot be
    mediated by itself.
    """
    vedas = set(pair_name.split("-"))
    if MEDIATING_VEDA in vedas:
        return 0.0
    counterparts: dict[str, set[tuple[str, str]]] = collections.defaultdict(set)
    for item in pairs:
        left, right = item.sides()
        counterparts[left[1]].add((right[0], right[1]))
        counterparts[right[1]].add((left[0], left[1]))
    selected = [item for item in pairs if item.pair == pair_name]
    if not selected:
        return 0.0
    mediated = 0
    for item in selected:
        left, right = item.sides()
        left_mediators = {k for v, k in counterparts[left[1]] if v == MEDIATING_VEDA}
        right_mediators = {k for v, k in counterparts[right[1]] if v == MEDIATING_VEDA}
        if left_mediators & right_mediators:
            mediated += 1
    return mediated / len(selected)


def _unit_measures(
    pairs: Sequence[VersePair], pair_name: str
) -> tuple[dict[tuple[str, str], set[str]], dict[tuple[str, str], set[str]]]:
    covered: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    dispersion: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    for item in pairs:
        if item.pair != pair_name:
            continue
        left, right = item.sides()
        for near, far in ((left, right), (right, left)):
            covered[(near[0], near[2])].add(near[1])
            dispersion[(near[0], near[2])].add(far[2])
    return covered, dispersion


def _raw_verdict(
    item: VersePair,
    covered: Mapping[tuple[str, str], set[str]],
    dispersion: Mapping[tuple[str, str], set[str]],
    unit_sizes: Mapping[str, int],
) -> tuple[str, EdgeEvidence]:
    left, right = item.sides()
    measures = {}
    for side in (left, right):
        size = unit_sizes.get(side[2], 0)
        share = len(covered.get((side[0], side[2]), ())) / size if size else 0.0
        measures[side[0]] = (share, len(dispersion.get((side[0], side[2]), ())), size)
    left_share, left_disp, left_size = measures[left[0]]
    right_share, right_disp, right_size = measures[right[0]]

    verdict = "UNDIRECTED"
    subject = obj = None
    if left_share >= COMPILATION_SHARE_FLOOR and left_share - right_share >= SHARE_MARGIN:
        verdict = f"{left[0]}->{right[0]}"
        subject, obj = left[1], right[1]
    elif right_share >= COMPILATION_SHARE_FLOOR and right_share - left_share >= SHARE_MARGIN:
        verdict = f"{right[0]}->{left[0]}"
        subject, obj = right[1], left[1]

    evidence = EdgeEvidence(
        left_key=left[1],
        right_key=right[1],
        pair=item.pair,
        scope="",
        verdict=verdict,
        subject_key=subject,
        object_key=obj,
        left_unit_counterpart_share=left_share,
        right_unit_counterpart_share=right_share,
        left_unit_dispersion=left_disp,
        right_unit_dispersion=right_disp,
        left_unit_size=left_size,
        right_unit_size=right_size,
        asymmetry=abs(left_share - right_share),
        reason=None if verdict != "UNDIRECTED" else REFUSAL_EDGE_UNDECIDED,
    )
    return verdict, evidence


def _scope_of(item: VersePair, scope_veda: str | None) -> str:
    if scope_veda is None:
        return item.pair
    for veda, key, _unit in item.sides():
        if veda == scope_veda:
            return f"{item.pair}:{veda}:{top_division(key)}"
    return item.pair


def measure_pair(
    pairs: Sequence[VersePair],
    pair_name: str,
    unit_sizes: Mapping[str, int],
) -> tuple[PairVerdict, tuple[EdgeEvidence, ...]]:
    """Decide one corpus pair, returning its verdict and one evidence row per edge.

    Every edge of the pair gets a row whether or not it is directed, because a refusal with
    its measurement attached is the thing the registry says is missing.
    """
    selected = [item for item in pairs if item.pair == pair_name]
    left_veda, right_veda = pair_name.split("-")

    def refuse(
        status: str, note: str, share: float | None = None
    ) -> tuple[PairVerdict, tuple[EdgeEvidence, ...]]:
        covered, dispersion = _unit_measures(pairs, pair_name)
        rows = []
        for item in selected:
            _verdict, evidence = _raw_verdict(item, covered, dispersion, unit_sizes)
            rows.append(
                EdgeEvidence(
                    **{
                        **evidence.__dict__,
                        "verdict": "UNDIRECTED",
                        "subject_key": None,
                        "object_key": None,
                        "scope": pair_name,
                        "reason": status,
                    }
                )
            )
        return (
            PairVerdict(
                pair=pair_name,
                status=status,
                scopes=(),
                directed_edges=0,
                undirected_edges=len(rows),
                mediation_share=share,
                decisions=0,
                agreement=None,
                note=note,
            ),
            tuple(rows),
        )

    for veda in (left_veda, right_veda):
        median = median_unit_size(unit_sizes, veda)
        if median > UNIT_GRANULARITY_CEILING:
            return refuse(
                REFUSAL_UNIT_GRANULARITY,
                f"{veda}'s smallest structural container holds a median of {median:g} "
                f"verses against a ceiling of {UNIT_GRANULARITY_CEILING}. A counterpart "
                "share taken over it is not the same instrument as one taken over the "
                "other corpus's units, so no direction is measured for this pair.",
            )

    share = mediation_share(pairs, pair_name)
    if share >= MEDIATION_REFUSAL_FLOOR:
        return refuse(
            REFUSAL_MEDIATED,
            f"{share:.1%} of this pair's verses are counterparts of one and the same "
            f"{MEDIATING_VEDA} verse, so the two corpora share {MEDIATING_VEDA} text rather "
            "than each other's. A direction here would assert a line of transmission the "
            "data routes through a third corpus.",
            share,
        )

    covered, dispersion = _unit_measures(pairs, pair_name)
    raw = [(item, *_raw_verdict(item, covered, dispersion, unit_sizes)) for item in selected]

    for scope_veda in (None, left_veda, right_veda):
        buckets: dict[str, list[tuple[VersePair, str, EdgeEvidence]]] = collections.defaultdict(
            list
        )
        for item, verdict, evidence in raw:
            buckets[_scope_of(item, scope_veda)].append((item, verdict, evidence))
        accepted: dict[str, str] = {}
        decisions = agreed = 0
        for scope, members in sorted(buckets.items()):
            votes = collections.Counter(
                verdict for _i, verdict, _e in members if verdict != "UNDIRECTED"
            )
            total = sum(votes.values())
            if total < SCOPE_POWER_FLOOR:
                continue
            top, count = votes.most_common(1)[0]
            if count / total < SCOPE_CONSISTENCY_FLOOR:
                continue
            accepted[scope] = top
            decisions += total
            agreed += count
        if not accepted:
            continue
        rows: list[EdgeEvidence] = []
        directed = undirected = 0
        for scope, members in sorted(buckets.items()):
            winner: str | None = accepted.get(scope)
            for _item, verdict, evidence in members:
                keep = winner is not None and verdict == winner
                reason = None
                if not keep:
                    reason = (
                        REFUSAL_EDGE_CONTRADICTS
                        if winner is not None and verdict != "UNDIRECTED"
                        else REFUSAL_EDGE_UNDECIDED
                        if winner is not None
                        else REFUSAL_NO_POWER
                    )
                rows.append(
                    EdgeEvidence(
                        **{
                            **evidence.__dict__,
                            "scope": scope,
                            "verdict": verdict if keep else "UNDIRECTED",
                            "subject_key": evidence.subject_key if keep else None,
                            "object_key": evidence.object_key if keep else None,
                            "reason": reason,
                        }
                    )
                )
                directed += 1 if keep else 0
                undirected += 0 if keep else 1
        scope_label = "the whole pair" if scope_veda is None else f"{scope_veda} divisions"
        return (
            PairVerdict(
                pair=pair_name,
                status="DIRECTED",
                scopes=tuple(sorted(accepted)),
                directed_edges=directed,
                undirected_edges=undirected,
                mediation_share=share,
                decisions=decisions,
                agreement=agreed / decisions if decisions else None,
                note=(
                    f"Direction measured by {DIRECTION_METHOD} over {scope_label}: "
                    f"{decisions} directed verdicts at {agreed / decisions:.1%} agreement "
                    f"in {len(accepted)} scope(s). {undirected} edges of the pair receive "
                    "no direction and say why on the edge."
                ),
            ),
            tuple(rows),
        )

    votes = collections.Counter(v for _i, v, _e in raw if v != "UNDIRECTED")
    total = sum(votes.values())
    best = votes.most_common(1)[0][1] / total if total else None
    status = REFUSAL_NO_POWER if total < SCOPE_POWER_FLOOR else REFUSAL_INCONSISTENT
    note = (
        f"The instrument produced {total} directed verdicts for this pair, below the "
        f"{SCOPE_POWER_FLOOR} needed to trust any of them."
        if status == REFUSAL_NO_POWER
        else f"The instrument produced {total} directed verdicts for this pair and only "
        f"{best:.1%} of them agree, against a floor of {SCOPE_CONSISTENCY_FLOOR:.0%}. "
        "Splitting by top structural division did not find a scope that clears both "
        "floors. An assertion here would be the instrument's noise written into the graph."
    )
    refused, refused_rows = refuse(status, note, share)
    return (
        PairVerdict(**{**refused.__dict__, "decisions": total, "agreement": best}),
        refused_rows,
    )


def measure_directions(
    pairs: Iterable[VersePair], unit_sizes: Mapping[str, int]
) -> tuple[tuple[PairVerdict, ...], tuple[EdgeEvidence, ...]]:
    """Every corpus pair present, decided independently, with one row per edge."""
    items = tuple(pairs)
    names = sorted({item.pair for item in items})
    verdicts: list[PairVerdict] = []
    evidence: list[EdgeEvidence] = []
    for name in names:
        verdict, rows = measure_pair(items, name, unit_sizes)
        verdicts.append(verdict)
        evidence.extend(rows)
    return tuple(verdicts), tuple(evidence)
