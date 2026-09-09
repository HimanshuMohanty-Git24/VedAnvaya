"""Materialise cross-Veda ENTITY-VOCABULARY overlap, with its distinctiveness stated.

**The name is the point.** This layer measures whether two passages mention the same
registry entities. It does NOT measure conceptual similarity, and the predicate is called
``SHARES_ENTITY_VOCABULARY_WITH`` so that no reader can mistake it for one. An earlier
draft of this module called the edge ``CONCEPTUALLY_SIMILAR_TO``, which would have shipped
the very defect the layer was built to remove: the V3.1 benchmark diagnosis graded Q22 and
Q49 `MISLEADING` precisely because a shared-entity-overlap measure was presented as an
answer to a conceptual-similarity question, and both frozen acceptance criteria exclude
lexical overlap in terms. A truthful "this measure is vocabulary overlap" plus an explicit
`INSUFFICIENT_EVIDENCE` for the conceptual question is the correct outcome; renaming the
measure is not a cosmetic act, it is the fix.

**Why this layer exists at all.** Two benchmark questions ask for something adjacent --
Q22 "which passages are lexically different but conceptually similar" and Q49 "which
cross-Veda passages express similar ideas without textual reuse" -- and the only query
answering them was an
exact all-pairs self-join over ``MENTIONS_ENTITY`` that took 5.3 seconds, and **died** with
a transaction-memory error the moment a single ``collect`` was added to see *which*
entities a pair shared. `QUESTION_UNLOCKED = Q22, Q49`.

**Why it is precomputed rather than optimised in place.** The entity degree distribution is
severely hub-skewed: median 31, p95 526, maximum 1,206 (``heaven (dyaus)``). The pair space
is therefore about the sum of the squared degrees, on the order of fifteen million pairs,
to yield roughly two and a half thousand qualifying ones. No rewrite makes an exact
all-pairs join an online query; every fast rewrite tried dropped real answers, including
the shipped query's own best row. So the pairs are computed once, deterministically, and
the named query reads them.

The computation is exact and its memory is bounded, which the naive form is not. Rather
than materialising a global pair table, it walks one passage at a time and counts shared
entities over that passage's own postings lists. The work is the same fifteen million
increments; the peak memory is one passage's candidate set instead of all pairs at once.

**Why distinctiveness is on the edge, and why that is a correctness fix rather than a
nicety.** "Shares at least three entities" is weak evidence of a shared idea when the three
are ``heaven``, ``sacrifice`` and ``soma``, which between them touch a large fraction of the
corpus. It is strong evidence when one of them is ``altar (vedi)``, which appears in 17
passages. The old query could not tell those apart and ranked them together, which is
exactly the shape of a confident-looking answer a researcher would reasonably read as true.
Every edge therefore carries the inverse-document-frequency sum of its shared entities and
the document frequency of its rarest shared entity, so a reader can rank on evidence
strength instead of on a raw count -- and can see when a "similarity" rests on nothing but
vocabulary every hymn uses.

**What this layer does NOT claim, restated because it is the whole design.** It is
co-mention of registry entities, not semantics.
Two passages joined here share entity vocabulary; whether they express the same *idea* is
an interpretation the graph does not make. The edge is graded accordingly and its
``grade_basis`` says so, and it is deliberately excluded from the textual-reuse layers:
pairs already joined by ``EXACT_PARALLEL_OF``, ``NEAR_PARALLEL_OF`` or ``REUSES_TEXT_FROM``
are dropped, because the questions ask for resemblance *without* shared text.
"""

from __future__ import annotations

import math
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Protocol

#: Minimum shared entities for a pair to be recorded. Three is the frozen benchmark's own
#: threshold, carried over unchanged so the materialised layer answers the same question
#: the 5.3-second query answered rather than a differently-scoped one.
MIN_SHARED: int = 3

#: Edges are written in batches of this size.
_BATCH = 2_000

REL_SHARES_ENTITY_VOCABULARY_WITH = "SHARES_ENTITY_VOCABULARY_WITH"


class Session(Protocol):
    def run(self, query: str, **parameters: Any) -> Any: ...


@dataclass
class OverlapReport:
    """Rows sent against rows that actually landed."""

    step: str = "entity_overlap"
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


@dataclass(frozen=True)
class OverlapPair:
    """One cross-Veda pair, with the evidence that licenses it."""

    passage_a: str
    passage_b: str
    veda_a: str
    veda_b: str
    shared_entity_keys: tuple[str, ...]
    #: Sum over shared entities of ln(total_passages / document_frequency). High means the
    #: pair is joined by vocabulary the corpus does not use everywhere.
    distinctiveness: float
    #: Document frequency of the rarest shared entity. The single most legible number
    #: here: 17 means these passages share something specific, 646 means they do not.
    rarest_shared_df: int

    @property
    def shared_entities(self) -> int:
        return len(self.shared_entity_keys)

    @property
    def veda_pair(self) -> str:
        return f"{self.veda_a}-{self.veda_b}"

    def as_row(self) -> dict[str, Any]:
        return {
            "passage_a": self.passage_a,
            "passage_b": self.passage_b,
            "veda_pair": self.veda_pair,
            "shared_entities": self.shared_entities,
            "shared_entity_keys": list(self.shared_entity_keys),
            "distinctiveness": round(self.distinctiveness, 4),
            "rarest_shared_df": self.rarest_shared_df,
        }


_MENTIONS_QUERY = """
MATCH (p:Passage)-[:MENTIONS_ENTITY]->(e:DomainEntity)
RETURN p.canonical_key AS passage, p.veda AS veda, e.entity_key AS entity
"""

_EXISTING_PARALLEL_QUERY = """
MATCH (a:Passage)-[:EXACT_PARALLEL_OF|NEAR_PARALLEL_OF|REUSES_TEXT_FROM]-(b:Passage)
WHERE a.canonical_key < b.canonical_key
RETURN a.canonical_key AS a, b.canonical_key AS b
"""


def compute_pairs(
    mentions: list[tuple[str, str, str]],
    already_parallel: set[tuple[str, str]],
    min_shared: int = MIN_SHARED,
) -> list[OverlapPair]:
    """Exact cross-Veda co-mention pairs, computed with bounded memory.

    ``mentions`` is ``(passage_key, veda, entity_key)``. The walk is per passage over its
    own postings lists, so peak memory is one passage's candidate counter rather than the
    whole pair space -- the difference between this running and the equivalent Cypher
    exceeding a 1.4 GiB transaction limit.
    """
    entities_of: dict[str, set[str]] = defaultdict(set)
    veda_of: dict[str, str] = {}
    postings: dict[str, list[str]] = defaultdict(list)

    for passage, veda, entity in mentions:
        if entity not in entities_of[passage]:
            entities_of[passage].add(entity)
            postings[entity].append(passage)
        veda_of[passage] = veda

    total_passages = len(entities_of)
    document_frequency = {entity: len(ps) for entity, ps in postings.items()}
    # ln(N/df), floored at zero so an entity present in every passage contributes nothing
    # rather than a negative amount.
    idf = {
        entity: max(0.0, math.log(total_passages / df)) if df else 0.0
        for entity, df in document_frequency.items()
    }

    pairs: list[OverlapPair] = []
    seen: set[tuple[str, str]] = set()

    for passage in sorted(entities_of):
        own = entities_of[passage]
        if len(own) < min_shared:
            continue
        candidates: Counter[str] = Counter()
        for entity in own:
            for other in postings[entity]:
                if other != passage:
                    candidates[other] += 1
        for other, shared in candidates.items():
            if shared < min_shared:
                continue
            if veda_of[passage] == veda_of[other]:
                continue
            key = (passage, other) if passage < other else (other, passage)
            if key in seen or key in already_parallel:
                continue
            seen.add(key)
            first, second = key
            shared_keys = tuple(sorted(own & entities_of[other]))
            pairs.append(
                OverlapPair(
                    passage_a=first,
                    passage_b=second,
                    veda_a=veda_of[first],
                    veda_b=veda_of[second],
                    shared_entity_keys=shared_keys,
                    distinctiveness=sum(idf[e] for e in shared_keys),
                    rarest_shared_df=min(document_frequency[e] for e in shared_keys),
                )
            )

    pairs.sort(key=lambda p: (-p.distinctiveness, p.passage_a, p.passage_b))
    return pairs


def derive(session: Session, min_shared: int = MIN_SHARED) -> list[OverlapPair]:
    """Read the mention layer live and compute the pairs. Writes nothing."""
    mentions = [
        (str(r["passage"]), str(r["veda"]), str(r["entity"])) for r in session.run(_MENTIONS_QUERY)
    ]
    already = {(str(r["a"]), str(r["b"])) for r in session.run(_EXISTING_PARALLEL_QUERY)}
    return compute_pairs(mentions, already, min_shared=min_shared)


_WRITE_QUERY = """
UNWIND $rows AS row
MATCH (a:Passage {canonical_key: row.passage_a})
MATCH (b:Passage {canonical_key: row.passage_b})
MERGE (a)-[r:SHARES_ENTITY_VOCABULARY_WITH]->(b)
SET r.shared_entities = row.shared_entities,
    r.shared_entity_keys = row.shared_entity_keys,
    r.distinctiveness = row.distinctiveness,
    r.rarest_shared_df = row.rarest_shared_df,
    r.veda_pair = row.veda_pair,
    r.method = 'entity-co-mention-idf',
    r.pipeline_version = $pipeline_version,
    r.run_id = $run_id,
    r.knowledge_layer = 'L2_DETERMINISTIC_DERIVED',
    r.quality_tier = 'TIER_B',
    r.evidence_basis = 'SHARED_REGISTRY_ENTITIES',
    r.attribution_precision = 'NOT_AN_ATTRIBUTION',
    r.state = 'ACCEPTED',
    r.trust = 'DERIVED',
    r.score = row.distinctiveness,
    r.evidence = row.shared_entity_keys,
    r.evidence_count = row.shared_entities,
    r.grade_basis =
      'co-mention of ' + toString(row.shared_entities) +
      ' registry entities in both passages, rarest shared entity in ' +
      toString(row.rarest_shared_df) + ' passages; entity vocabulary overlap is NOT a ' +
      'claim that the two passages express the same idea, and no textual reuse edge ' +
      'joins this pair'
"""
# Directed a->b with a canonically the lexicographically smaller key, so the pair is
# stored once and the "which is the source" question -- which this layer cannot answer and
# must not appear to -- is never implied by the arrow. Consumers traverse it undirected.

PIPELINE_VERSION = "entity-vocabulary-overlap-v3.1"


def load(session: Session, pairs: list[OverlapPair]) -> OverlapReport:
    """Write the pairs, retiring every edge this run did not produce.

    Retirement is by ``run_id``, not by ``pipeline_version``, and the difference is a bug
    that was in this module and was caught by its own sent-vs-landed diff. Filtering on
    ``pipeline_version`` retires edges from an OLDER version of the code but not edges
    from an older *input* under the same version -- so when the mention layer shrank by
    four edges, eight pairs stopped qualifying, were not rewritten, were not retired, and
    the loader reported ``sent=2141 landed=2149``. Landed exceeding sent is the signature
    of exactly that. ``run_id`` is fresh per call, so anything not rewritten this run is
    stale by construction, whether the code changed or only the data did.
    """
    report = OverlapReport(sent=len(pairs))
    rows = [p.as_row() for p in pairs]
    run_id = f"{PIPELINE_VERSION}:{uuid.uuid4().hex}"

    for start in range(0, len(rows), _BATCH):
        session.run(
            _WRITE_QUERY,
            rows=rows[start : start + _BATCH],
            pipeline_version=PIPELINE_VERSION,
            run_id=run_id,
        )

    stale = session.run(
        """
        MATCH ()-[r:SHARES_ENTITY_VOCABULARY_WITH]->()
        WHERE r.run_id IS NULL OR r.run_id <> $run_id
        DELETE r
        RETURN count(r) AS c
        """,
        run_id=run_id,
    ).single()
    report.detail["retired"] = int(stale["c"]) if stale else 0
    report.detail["run_id"] = run_id

    landed = session.run(
        "MATCH ()-[r:SHARES_ENTITY_VOCABULARY_WITH]->() WHERE r.run_id = $run_id "
        "RETURN count(r) AS c",
        run_id=run_id,
    ).single()
    report.landed = int(landed["c"]) if landed else 0

    by_pair = session.run(
        "MATCH ()-[r:SHARES_ENTITY_VOCABULARY_WITH]->() "
        "RETURN r.veda_pair AS pair, count(*) AS c ORDER BY c DESC"
    )
    report.detail["by_veda_pair"] = {str(r["pair"]): int(r["c"]) for r in by_pair}
    return report
