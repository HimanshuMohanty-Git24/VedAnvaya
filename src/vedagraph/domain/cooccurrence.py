"""Deity-pair co-occurrence, recomputed from the theonym mention layer.

This module exists to make an existing layer reproducible. 292 ``CO_OCCURS_WITH`` edges
were present in the live graph with **no producer anywhere in the repository** -- they had
been written by an uncommitted session script -- and they carried
``evidence_basis = UNSPECIFIED`` with the grader's own complaint as their basis string:
*"ungraded: CO_OCCURS_WITH records no recognised provenance vocabulary"*. They were the
last 292 ungraded-basis edges in the graph and the only ones no artifact could rebuild.

**What the edge asserts, exactly.** That these two deities are named in the same verse
``passage_count`` times, and that this is ``lift`` times as often as their individual
frequencies would predict if they were independent. That is a *measurement*, and it is
graded ``TIER_B`` because anyone can recompute it from the mention layer with the formula
below. It is emphatically **not** the claim that the two deities are associated,
paired, or theologically linked; that reading is an interpretation and belongs in an
``InterpretiveClaim``. The previous layer graded itself ``TIER_D`` and
``L4_INTERPRETIVE_CLAIM``, which conflated the measurement with the reading -- a count is
not a claim, and calling it one made the graph unable to say what it had actually counted.

**The formula.** For deities *a* and *b*::

    lift = n_ab * N / (n_a * n_b)

where *n_a* and *n_b* are the mantras mentioning each, *n_ab* the mantras mentioning both,
and **N is the number of mantras carrying at least one theonym mention at all** (11,452 of
20,210), not the corpus size. That denominator is deliberate and it is the conservative
choice: the baseline is "given that a verse names some god, how surprising is this pair?",
which does not reward a pair merely for both appearing in the religiously dense part of
the corpus. Using the full corpus inflates every lift by about 1.76x. The stored value
reproduces on this convention exactly.

**The caveat that travels with every row.** The mention layer's evidence is not uniform
across the four Vedas: Rigvedic mentions come from a manual scholarly morphological
annotation, and Samavedic, Yajurvedic and Atharvavedic ones from adjudicated surface
matching. A lift aggregated over all four therefore mixes two evidence modes. Rather than
suppress the aggregate or pretend it is uniform, each edge carries its per-Veda passage
counts, so a reader can see immediately whether a pair's signal is Rigveda-driven and
recompute on any subset.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Final, Protocol

#: Minimum shared mantras for a pair to be recorded. Below this, lift is dominated by
#: sampling noise -- a pair sharing two verses can post a lift of 40 and mean nothing --
#: and the layer would fill with pairs no one should reason from. Matches the threshold
#: the previous unreproducible layer used, so the two are comparable.
MIN_SHARED_PASSAGES: Final = 5

#: ``N`` in the lift formula: mantras carrying at least one theonym mention. See the
#: module docstring for why this rather than the corpus size.
_BASELINE_QUERY: Final = """
MATCH (p:Mantra)-[:MENTIONS_DEVATA]->(:Devata)
RETURN count(DISTINCT p) AS c
"""

#: One row per unordered pair, in canonical order so no pair is stored twice.
#:
#: ``a.entity_key < b.entity_key`` does two jobs: it fixes the direction, and it halves
#: the work. The pair is symmetric -- "Mitra occurs with Varuna" and the reverse are the
#: same fact -- so storing both directions would double the edge count while adding
#: nothing, and would then need both kept in step forever.
_PAIR_QUERY: Final = """
MATCH (p:Mantra)-[:MENTIONS_DEVATA]->(a:Devata)
MATCH (p)-[:MENTIONS_DEVATA]->(b:Devata)
WHERE a.entity_key < b.entity_key
WITH a, b, collect(DISTINCT p) AS shared
WHERE size(shared) >= $min_shared
RETURN a.entity_key AS a_key,
       b.entity_key AS b_key,
       size(shared) AS passage_count,
       [v IN ['RV', 'SV', 'YV', 'AV']
          WHERE size([q IN shared WHERE q.veda = v]) > 0] AS vedas,
       [v IN ['RV', 'SV', 'YV', 'AV'] |
          size([q IN shared WHERE q.veda = v])] AS per_veda_counts,
       [q IN shared | q.canonical_key][0..5] AS example_citations
"""

_MENTION_TOTALS_QUERY: Final = """
MATCH (p:Mantra)-[:MENTIONS_DEVATA]->(d:Devata)
RETURN d.entity_key AS key, count(DISTINCT p) AS c
"""

_WRITE_QUERY: Final = """
UNWIND $rows AS row
MATCH (a:Devata {entity_key: row.a_key})
MATCH (b:Devata {entity_key: row.b_key})
MERGE (a)-[r:CO_OCCURS_WITH]->(b)
SET r.passage_count = row.passage_count,
    r.lift = row.lift,
    r.mantras_a = row.mantras_a,
    r.mantras_b = row.mantras_b,
    r.baseline_mantras = row.baseline_mantras,
    r.vedas = row.vedas,
    r.veda_count = row.veda_count,
    r.rv_passage_count = row.rv_passage_count,
    r.non_rv_passage_count = row.non_rv_passage_count,
    r.per_veda_counts = row.per_veda_counts,
    r.example_citations = row.example_citations,
    r.quality_tier = 'TIER_B',
    r.evidence_basis = 'SANSKRIT',
    r.attribution_precision = 'TEXTUAL_MENTION',
    r.knowledge_layer = 'L2_DETERMINISTIC_DERIVED',
    r.method = 'devata-cooccurrence-lift-v1',
    r.grade_basis = $grade_basis,
    r.asserts = $asserts,
    r.evidence_caveat = $caveat,
    r.build_pass = $build_pass
"""

#: Passed as parameters rather than inlined. Cypher has no implicit concatenation of
#: adjacent string literals, so a prose property long enough to need wrapping cannot be
#: written inline without either an explicit `+` chain or a very long line.
_GRADE_BASIS: Final = (
    "counted over the theonym mention layer; recomputable from the graph"
)
_ASSERTS: Final = (
    "Both deities are named in this many of the same mantras, at this lift. A count, "
    "not a claim that the deities are associated."
)
_CAVEAT: Final = (
    "The mention layer is manual annotation for RV and adjudicated surface matching "
    "for SV/YV/AV; per_veda_counts is carried so any subset can be recomputed."
)

_SWEEP_QUERY: Final = """
MATCH (:Devata)-[r:CO_OCCURS_WITH]->(:Devata)
WHERE r.build_pass IS NULL OR r.build_pass <> $build_pass
DELETE r
RETURN count(*) AS c
"""


class Session(Protocol):
    def run(self, query: str, /, **parameters: Any) -> Any: ...


@dataclass
class CooccurrenceReport:
    """Rows sent against rows landed, plus the delta from whatever was there before."""

    step: str = "devata_cooccurrence"
    sent: int = 0
    landed: int = 0
    detail: dict[str, Any] = field(default_factory=dict)

    @property
    def complete(self) -> bool:
        return self.landed == self.sent

    def as_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "sent": self.sent,
            "landed": self.landed,
            "complete": self.complete,
            "detail": self.detail,
        }


def _count(session: Session, query: str, **parameters: Any) -> int:
    record = session.run(query, **parameters).single()
    return int(record["c"]) if record else 0


def rebuild(session: Session) -> CooccurrenceReport:
    """Recompute every deity pair from the mention layer, and retire the rest.

    The delta against the pre-existing layer is reported rather than assumed to be zero.
    An unreproducible layer being replaced by a reproducible one is exactly the moment to
    check whether the two agree, and "we replaced it and the count happened to match" is
    not the same statement as "we replaced it and every row matched".
    """
    report = CooccurrenceReport()
    before = _count(
        session, "MATCH (:Devata)-[r:CO_OCCURS_WITH]->(:Devata) RETURN count(r) AS c"
    )
    baseline = _count(session, _BASELINE_QUERY)
    if not baseline:
        report.detail = {"skipped": "no theonym mention layer present"}
        return report

    totals = {
        record["key"]: int(record["c"])
        for record in session.run(_MENTION_TOTALS_QUERY)
    }

    rows: list[dict[str, Any]] = []
    for record in session.run(_PAIR_QUERY, min_shared=MIN_SHARED_PASSAGES):
        a_key, b_key = record["a_key"], record["b_key"]
        n_a, n_b = totals.get(a_key, 0), totals.get(b_key, 0)
        if not n_a or not n_b:
            continue
        shared = int(record["passage_count"])
        per_veda = [int(value) for value in record["per_veda_counts"]]
        rows.append(
            {
                "a_key": a_key,
                "b_key": b_key,
                "passage_count": shared,
                "lift": round(shared * baseline / (n_a * n_b), 3),
                "mantras_a": n_a,
                "mantras_b": n_b,
                "baseline_mantras": baseline,
                "vedas": list(record["vedas"]),
                "veda_count": len(record["vedas"]),
                # Carried explicitly because "is this pair only a Rigvedic phenomenon?"
                # is the first question a reader should ask of any cross-Veda lift, and
                # it should not require unpacking the array to answer.
                "rv_passage_count": per_veda[0],
                "non_rv_passage_count": sum(per_veda[1:]),
                "per_veda_counts": per_veda,
                "example_citations": list(record["example_citations"]),
            }
        )

    report.sent = len(rows)
    if not rows:
        report.detail = {"skipped": "no pair met the shared-passage floor"}
        return report

    build_pass = uuid.uuid4().hex
    session.run(
        _WRITE_QUERY,
        rows=rows,
        build_pass=build_pass,
        grade_basis=_GRADE_BASIS,
        asserts=_ASSERTS,
        caveat=_CAVEAT,
    )
    report.landed = _count(
        session,
        "MATCH (:Devata)-[r:CO_OCCURS_WITH]->(:Devata) "
        "WHERE r.build_pass = $build_pass RETURN count(r) AS c",
        build_pass=build_pass,
    )
    retired = _count(session, _SWEEP_QUERY, build_pass=build_pass)
    report.detail = {
        "baseline_mantras": baseline,
        "min_shared_passages": MIN_SHARED_PASSAGES,
        "edges_before": before,
        "edges_after": report.landed,
        "retired_unreproducible": retired,
        "cross_veda_pairs": sum(1 for row in rows if row["veda_count"] > 1),
        "rv_only_pairs": sum(1 for row in rows if row["non_rv_passage_count"] == 0),
        "top_by_lift": [
            {
                "a": row["a_key"],
                "b": row["b_key"],
                "lift": row["lift"],
                "passages": row["passage_count"],
            }
            for row in sorted(rows, key=lambda r: -float(r["lift"]))[:5]
        ],
    }
    return report
