"""Entity centrality, stored once on a declared-authoritative layer, with its rank
correlation against the rival layer measured.

**The defect this replaces.** There was no stored centrality anywhere in the graph -- no
node carried a ``central*``, ``betweenness*``, ``pagerank*``, ``louvain*`` or ``community*``
key -- so a researcher asking "which entities are central" wrote a GDS projection. The
natural projection over ``Passage``/``DomainEntity`` with ``MENTIONS_ENTITY`` is **directed
and bipartite**, and betweenness on a directed bipartite graph is **0.0 for every node**.
The default thing a competent user does therefore returns a full, sortable ranking of
zeros, and nothing in the graph or the catalogue steers them away from it. A stored score
cannot be silently mis-projected, which is the whole reason this module exists.

**Two rival layers, and the choice is declared rather than left to the caller.**
``MENTIONS_ENTITY`` (over ``DomainEntity``) and ``ABOUT_CONCEPT`` (over ``Concept``) both
answer "what is this passage about", they overlap heavily in membership, and neither
carried an authority marker -- so "which layer" was a coin flip that changed the answer.
``MENTIONS_ENTITY`` is declared authoritative here, for a stated reason: its edges rest on
Sanskrit surface and lemma matching against a disclosed alias list, whereas the concept
layer's V1 build had 21,246 of 47,542 assertions resting on no Sanskrit evidence at all
(they matched a word in a nineteenth-century English translation), and although V3 retired
those, the layer that remains is a *concept* layer at a different granularity rather than a
better entity layer. The rival layer is not hidden: :func:`rank_correlation` measures
Spearman's rho between the two rankings over their shared members and stores it, so a
reader can see how much the choice actually costs. That figure is the core clause of the
robustness question, and it is reported rather than asserted.

**What is NOT built, and is typed as absent rather than returned as a zero.** There is no
community structure in this graph: no Louvain, no modularity, no stored partition. So
"which entities bridge between *communities*" cannot be answered, and the honest output is
``INSUFFICIENT_EVIDENCE`` rather than a betweenness column of zeros that looks like a
ranking. Degree centrality over the co-mention projection *is* computable and is what this
module stores; bridging is not, and says so.

Centrality is computed in deterministic Python rather than through GDS for the reason
``vedagraph.enrich.analytics`` gives: nothing in the pipeline may depend on an optional
plugin, and a number that changes when a plugin is absent is not a measurement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

#: The layer whose ranking the product answers with. Declared, not inferred.
AUTHORITATIVE_LAYER = "MENTIONS_ENTITY"
RIVAL_LAYER = "ABOUT_CONCEPT"

AUTHORITY_BASIS = (
    "MENTIONS_ENTITY edges rest on Sanskrit surface and lemma matching against a "
    "disclosed alias list. ABOUT_CONCEPT is a concept layer at a different granularity "
    "whose V1 build had 21,246 of 47,542 assertions resting on no Sanskrit evidence at "
    "all; V3 retired those, but the remainder is still a concept layer rather than a "
    "better entity layer. The choice is declared so that 'which layer' stops changing "
    "the answer, and its cost is measured as Spearman rho against the rival layer."
)

PIPELINE_VERSION = "entity-centrality-v3.1"


class Session(Protocol):
    def run(self, query: str, **parameters: Any) -> Any: ...


@dataclass
class CentralityReport:
    step: str = "entity_centrality"
    sent: int = 0
    landed: int = 0
    detail: dict[str, Any] = field(default_factory=dict)

    @property
    def complete(self) -> bool:
        return self.landed >= self.sent

    def as_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "sent": self.sent,
            "landed": self.landed,
            "complete": self.complete,
            "detail": self.detail,
        }


def _ranks(scores: dict[str, float]) -> dict[str, float]:
    """Ranks with ties averaged, which is what Spearman requires.

    Ties are not a corner case here: document frequencies collide often, and integer
    ranking without tie handling would invent an ordering the data does not support and
    then report a correlation against it.
    """
    ordered = sorted(scores, key=lambda k: (-scores[k], k))
    ranks: dict[str, float] = {}
    index = 0
    while index < len(ordered):
        stop = index
        while stop + 1 < len(ordered) and scores[ordered[stop + 1]] == scores[ordered[index]]:
            stop += 1
        average = (index + stop) / 2 + 1
        for position in range(index, stop + 1):
            ranks[ordered[position]] = average
        index = stop + 1
    return ranks


def rank_correlation(a: dict[str, float], b: dict[str, float]) -> dict[str, Any]:
    """Spearman's rho between two rankings, over their shared members only.

    Returns the overlap alongside the coefficient, because a rho computed over three
    shared members is not evidence of agreement and the number alone cannot say so.
    """
    shared = sorted(set(a) & set(b))
    if len(shared) < 3:
        return {
            "spearman_rho": None,
            "shared_members": len(shared),
            "verdict": "INSUFFICIENT_OVERLAP",
        }
    rank_a = _ranks({k: a[k] for k in shared})
    rank_b = _ranks({k: b[k] for k in shared})
    n = len(shared)
    squared = sum((rank_a[k] - rank_b[k]) ** 2 for k in shared)
    rho = 1 - (6 * squared) / (n * (n * n - 1))
    return {
        "spearman_rho": round(rho, 4),
        "shared_members": n,
        "only_in_authoritative": len(set(a) - set(b)),
        "only_in_rival": len(set(b) - set(a)),
        "verdict": "MEASURED",
    }


_AUTHORITATIVE_QUERY = """
MATCH (p:Passage)-[:MENTIONS_ENTITY]->(e:DomainEntity)
RETURN e.entity_key AS key, e.display_label AS label, count(DISTINCT p) AS passages
"""

_RIVAL_QUERY = """
MATCH (p:Passage)-[:ABOUT_CONCEPT]->(c:Concept)
RETURN coalesce(c.preferred_label_sa, c.concept_id) AS key, count(DISTINCT p) AS passages
"""


def derive(session: Session) -> dict[str, Any]:
    """Read both layers and compute the stored scores plus the correlation."""
    authoritative: dict[str, float] = {}
    labels: dict[str, str] = {}
    for record in session.run(_AUTHORITATIVE_QUERY):
        key = str(record["key"])
        authoritative[key] = float(record["passages"])
        labels[key] = str(record["label"] or key)

    rival: dict[str, float] = {}
    for record in session.run(_RIVAL_QUERY):
        rival[str(record["key"])] = float(record["passages"])

    correlation = rank_correlation(join_key_scores(authoritative, labels), rival)

    total = sum(authoritative.values()) or 1.0
    rows = [
        {
            "entity_key": key,
            "centrality_degree": score,
            "centrality_share": round(score / total, 6),
        }
        for key, score in authoritative.items()
    ]
    return {"rows": rows, "correlation": correlation, "labels": labels}


def join_key_scores(scores: dict[str, float], labels: dict[str, str]) -> dict[str, float]:
    """Re-key the authoritative scores onto the vocabulary the rival layer uses.

    The two layers key differently -- ``entity_key`` against a Sanskrit preferred label --
    so the only vocabulary they share is the Sanskrit label, and the rival layer's label
    sits inside the authoritative layer's ``display_label`` as "fire (agni)". This
    function is named and separate rather than inlined because the correlation is only as
    good as this join, and a rho computed over a bad join is worse than no rho at all:
    a low number would be read as the two layers disagreeing when it would really mean
    the join failed. ``rank_correlation`` reports ``shared_members`` for the same reason.
    """
    joined: dict[str, float] = {}
    for key, score in scores.items():
        label = labels.get(key) or ""
        # "fire (agni)" -> "agni". Anything without the parenthetical has no Sanskrit
        # label to join on and is deliberately dropped rather than matched on English.
        if "(" in label and label.rstrip().endswith(")"):
            sanskrit = label[label.rindex("(") + 1 : -1].strip()
            if sanskrit:
                joined[sanskrit] = score
    return joined


_WRITE_QUERY = """
UNWIND $rows AS row
MATCH (e:DomainEntity {entity_key: row.entity_key})
SET e.centrality_degree = row.centrality_degree,
    e.centrality_share = row.centrality_share,
    e.centrality_layer = $layer,
    e.centrality_measure = 'DEGREE_OVER_PASSAGE_CO_MENTION',
    e.centrality_bridging = 'NOT_BUILT: no community structure exists in this graph, so '
      + 'bridge centrality is not computable and is not reported as a zero',
    e.centrality_pipeline_version = $pipeline_version
RETURN count(e) AS c
"""


def load(session: Session, derived: dict[str, Any]) -> CentralityReport:
    """Store centrality on the authoritative layer and the correlation as a metric."""
    rows: list[dict[str, Any]] = derived["rows"]
    report = CentralityReport(sent=len(rows))
    if rows:
        session.run(
            _WRITE_QUERY,
            rows=rows,
            layer=AUTHORITATIVE_LAYER,
            pipeline_version=PIPELINE_VERSION,
        )
    landed = session.run(
        "MATCH (e:DomainEntity) WHERE e.centrality_degree IS NOT NULL RETURN count(e) AS c"
    ).single()
    report.landed = int(landed["c"]) if landed else 0

    correlation = derived["correlation"]
    session.run(
        """
        MERGE (m:DerivedMetric {metric_id: $metric_id})
        SET m.metric_name = 'CONCEPT_LAYER_RANK_CORRELATION',
            m.subject_key = $authoritative,
            m.values_json = $values,
            m.interpretation = 'NONE',
            m.method = 'spearman rho over shared preferred labels',
            m.quality_tier = 'TIER_B',
            m.grade_basis = $basis,
            m.display_label = 'Rank correlation: ' + $authoritative + ' vs ' + $rival,
            m.display_type = 'DerivedMetric',
            m.pipeline_version = $pipeline_version
        """,
        metric_id=f"VG:METRIC:CONCEPT_LAYER_RANK_CORRELATION:{AUTHORITATIVE_LAYER}",
        authoritative=AUTHORITATIVE_LAYER,
        rival=RIVAL_LAYER,
        values=str(correlation),
        basis=AUTHORITY_BASIS,
        pipeline_version=PIPELINE_VERSION,
    )
    report.detail["correlation"] = correlation
    report.detail["authoritative_layer"] = AUTHORITATIVE_LAYER
    return report
