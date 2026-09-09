"""Validation query suite for the VedaGraph Neo4j graph."""

from __future__ import annotations

from typing import Any


def _run(session: Any, cypher: str, **params: Any) -> list[dict[str, Any]]:
    result = session.run(cypher, **params)
    return [dict(r) for r in result]


def fetch_passage(session: Any, canonical_key: str) -> list[dict[str, Any]]:
    """Fetch a single Passage by canonical_key."""
    return _run(
        session,
        "MATCH (p:Passage {canonical_key: $key}) RETURN p",
        key=canonical_key,
    )


def fetch_sukta_mantras(session: Any, sukta_key: str) -> list[dict[str, Any]]:
    """Fetch all Mantra children of a given sukta/hymn Passage."""
    return _run(
        session,
        """
        MATCH (parent:Passage {canonical_key: $key})-[:CONTAINS]->(child:Mantra)
        RETURN child ORDER BY child.sequence_in_parent
        """,
        key=sukta_key,
    )


def fetch_passages_by_devata(
    session: Any, devata_key: str, limit: int = 100
) -> list[dict[str, Any]]:
    """Fetch the first ``limit`` Passages ascribed to a Devata, in citation order.

    Rigveda-only: ``HAS_DEVATA`` has 10,558 edges and every one is on the RV. The other
    three samhitas have no Anukramani deity ascription, so an empty result for an
    AV/SV/YV-only deity is a missing annotation layer and not an absence from the text.
    Use ``fetch_devata_lexical_mentions`` for the four-Veda question.

    ``total_matched`` is returned on every row because ``limit`` truncates hard and
    silently: Indra is ascribed 2,869 mantras, so the default of 100 returned the
    beginning of Mandala 1 alphabetically and gave a caller no way to tell that from the
    complete answer. Pass ``limit=0`` for no cap.
    """
    return _run(
        session,
        """
        MATCH (p:Passage)-[:HAS_DEVATA]->(:Devata {entity_key: $key})
        WITH count(DISTINCT p) AS total_matched
        MATCH (p:Passage)-[:HAS_DEVATA]->(:Devata {entity_key: $key})
        RETURN p.canonical_key AS canonical_key, p.canonical_citation AS citation,
               total_matched
        ORDER BY p.canonical_key
        LIMIT CASE WHEN $limit <= 0 THEN 2147483647 ELSE $limit END
        """,
        key=devata_key,
        limit=limit,
    )


def fetch_passages_by_rishi(
    session: Any, rishi_key: str, limit: int = 100
) -> list[dict[str, Any]]:
    """Fetch the first ``limit`` Passages ascribed to a Rishi, in citation order.

    Three-Veda, not four: ``HAS_RISHI`` has 17,889 edges over the RV (10,565), AV (5,084)
    and YV (2,240). The Samaveda has none.

    ``total_matched`` and ``limit`` behave as in :func:`fetch_passages_by_devata`.
    """
    return _run(
        session,
        """
        MATCH (p:Passage)-[:HAS_RISHI]->(:Rishi {entity_key: $key})
        WITH count(DISTINCT p) AS total_matched
        MATCH (p:Passage)-[:HAS_RISHI]->(:Rishi {entity_key: $key})
        RETURN p.canonical_key AS canonical_key, p.canonical_citation AS citation,
               total_matched
        ORDER BY p.canonical_key
        LIMIT CASE WHEN $limit <= 0 THEN 2147483647 ELSE $limit END
        """,
        key=rishi_key,
        limit=limit,
    )


def fetch_passages_by_chandas(
    session: Any, chandas_key: str, limit: int = 100
) -> list[dict[str, Any]]:
    """Fetch the first ``limit`` Passages in a given metre, in citation order.

    Two-Veda: ``HAS_CHANDAS`` has 16,320 edges over the RV (10,523) and AV (5,797). The
    Samaveda and Yajurveda have none.

    ``total_matched`` and ``limit`` behave as in :func:`fetch_passages_by_devata`.
    """
    return _run(
        session,
        """
        MATCH (p:Passage)-[:HAS_CHANDAS]->(:Chandas {entity_key: $key})
        WITH count(DISTINCT p) AS total_matched
        MATCH (p:Passage)-[:HAS_CHANDAS]->(:Chandas {entity_key: $key})
        RETURN p.canonical_key AS canonical_key, p.canonical_citation AS citation,
               total_matched
        ORDER BY p.canonical_key
        LIMIT CASE WHEN $limit <= 0 THEN 2147483647 ELSE $limit END
        """,
        key=chandas_key,
        limit=limit,
    )


def fetch_passage_with_translation(
    session: Any, canonical_key: str
) -> list[dict[str, Any]]:
    """Fetch a Passage and its Translations."""
    return _run(
        session,
        """
        MATCH (p:Passage {canonical_key: $key})-[:HAS_TRANSLATION]->(t:Translation)
        RETURN p.canonical_citation AS citation,
               t.translator AS translator, t.year AS year, t.text AS text
        """,
        key=canonical_key,
    )


def fetch_exact_parallels(session: Any, canonical_key: str) -> list[dict[str, Any]]:
    """Fetch exact parallels of a given Passage, from either side of the edge.

    Traversed undirected, because parallelism is symmetric but its storage is not: the
    edge is written once, from the lexicographically smaller canonical key to the larger.
    A directed ``-[:EXACT_PARALLEL_OF]->`` therefore answers only for whichever side
    happens to sort first, and returns empty for the other -- across the 1,006 edges, 713
    passages are the target of one and the source of none (553 RV, 82 SV, 78 YV), so every
    one of them had a recorded parallel this function could not see. RV 1.3.4 is one: its
    parallel at AV
    20.84.1 is real, and ``VG:AV:...`` sorts before ``VG:RV:...``, so the RV side was
    blind to it.
    """
    return _run(
        session,
        """
        MATCH (p:Passage {canonical_key: $key})-[:EXACT_PARALLEL_OF]-(q:Passage)
        RETURN q.canonical_key AS parallel_key, q.canonical_citation AS citation,
               q.veda AS veda
        ORDER BY q.canonical_key
        """,
        key=canonical_key,
    )


def fetch_near_parallels(session: Any, canonical_key: str) -> list[dict[str, Any]]:
    """Fetch near parallels (PARALLEL_TO) of a Passage, from either side of the edge.

    Undirected for the reason given in :func:`fetch_exact_parallels`; all 69 PARALLEL_TO
    edges likewise run from the smaller canonical key to the larger.

    Every edge is returned and ``status`` comes back with it, rather than the query
    filtering to accepted rows. All 69 edges currently carry the single status
    ``HIGH_CONFIDENCE_NEAR_PARALLEL``, so a ``WHERE r.status = ...`` clause would be a
    filter that changes no result while quietly acquiring the power to drop edges the day
    a second status is introduced. Exposing the grade and letting the caller judge is what
    this function's returned ``status`` column was for; the previous docstring's claim
    that these were "accepted" near parallels described an acceptance step that does not
    exist in the data.
    """
    return _run(
        session,
        """
        MATCH (p:Passage {canonical_key: $key})-[r:PARALLEL_TO]-(q:Passage)
        RETURN q.canonical_key AS parallel_key, q.canonical_citation AS citation,
               r.similarity AS similarity, r.status AS status
        ORDER BY r.similarity DESC, q.canonical_key
        """,
        key=canonical_key,
    )


def fetch_sv_passages_related_to_rv(
    session: Any, rv_key: str
) -> list[dict[str, Any]]:
    """Fetch Samaveda passages that are exact parallels of a given RV passage."""
    return _run(
        session,
        """
        MATCH (rv:Passage {canonical_key: $key})-[:EXACT_PARALLEL_OF]-(sv:Passage)
        WHERE sv.work_id = 'VG:WORK:SV:KAU'
        RETURN sv.canonical_key AS sv_key, sv.canonical_citation AS sv_citation
        """,
        key=rv_key,
    )


def fetch_yv_adhyaya(session: Any, adhyaya_key: str) -> list[dict[str, Any]]:
    """Fetch all Yajurveda mantras in an Adhyaya."""
    return _run(
        session,
        """
        MATCH (a:Passage {canonical_key: $key})-[:CONTAINS]->(m:Mantra)
        RETURN m.canonical_key AS canonical_key, m.canonical_citation AS citation
        ORDER BY m.sequence_in_parent
        """,
        key=adhyaya_key,
    )


def fetch_av_kanda(session: Any, kanda_key: str) -> list[dict[str, Any]]:
    """Fetch all Atharvaveda suktas in a given Kanda."""
    return _run(
        session,
        """
        MATCH (k:Passage {canonical_key: $key})-[:CONTAINS]->(s:Passage)
        RETURN s.canonical_key AS sukta_key, s.canonical_citation AS citation
        ORDER BY s.sequence_in_parent
        """,
        key=kanda_key,
    )


def fetch_lemma_mentions(session: Any, normalized_lemma: str) -> list[dict[str, Any]]:
    """Fetch RV passages mentioning any Lemma with this normalized form.

    Matches on normalized_lemma deliberately: it is a many-to-one search key, so a
    caller searching "atra" reaches every accented variant. The lemma itself is
    returned so the caller can tell the variants apart.
    """
    return _run(
        session,
        """
        MATCH (p:Passage)-[r:MENTIONS_LEMMA]->(l:Lemma {normalized_lemma: $lemma})
        RETURN p.canonical_key AS canonical_key, l.lemma AS lemma,
               r.occurrence_count AS count
        ORDER BY r.occurrence_count DESC, p.canonical_key LIMIT 50
        """,
        lemma=normalized_lemma,
    )


def fetch_devata_lexical_mentions(
    session: Any, devata_key: str, limit: int = 100
) -> list[dict[str, Any]]:
    """Fetch passages that name a Devata in their text, across all four Vedas.

    This is the lexical question -- "does this passage say the word?" -- as against the
    Anukramani ascription reached by ``HAS_DEVATA``, which is Rigveda-only. It runs on
    ``MENTIONS_DEVATA`` (16,261 edges: RV 10,284, AV 2,861, YV 1,781, SV 1,335). It used
    to run on ``MENTIONS_ENTITY`` edges onto ``:Devata``, all 9,000 of which were deleted
    as duplicates of ``MENTIONS_LEMMA``, so it returned zero rows for every deity.

    ``referent_certainty`` is returned rather than filtered on, and a caller who ignores
    it will overcount. Several theonyms are also common nouns -- ``agni`` is Agni and it
    is fire -- so 8,485 of the 16,261 edges are graded ``DEITY_AMBIGUOUS``, including the
    majority of every non-Rigvedic corpus. ``extraction_path`` says how the row was
    reached: the RV rows come from the manual morphological annotation by lemma identity,
    the other three from adjudicated surface forms, which is why the RV is the only corpus
    with ``TIER_A`` rows.

    ``total_matched`` and ``limit`` behave as in :func:`fetch_passages_by_devata`.
    """
    return _run(
        session,
        """
        MATCH (p:Passage)-[:MENTIONS_DEVATA]->(:Devata {entity_key: $key})
        WITH count(DISTINCT p) AS total_matched
        MATCH (p:Passage)-[r:MENTIONS_DEVATA]->(:Devata {entity_key: $key})
        RETURN p.canonical_key AS canonical_key, p.veda AS veda,
               r.occurrences AS occurrences, r.referent_certainty AS referent_certainty,
               r.evidence_basis AS evidence_basis, r.quality_tier AS quality_tier,
               r.extraction_path AS extraction_path, total_matched
        ORDER BY p.canonical_key
        LIMIT CASE WHEN $limit <= 0 THEN 2147483647 ELSE $limit END
        """,
        key=devata_key,
        limit=limit,
    )


def graph_statistics(session: Any) -> dict[str, Any]:
    """Return node counts per label and relationship counts per type.

    A node is counted under *every* label it carries, so the label counts sum to more
    than the node total and are not a partition. That is the honest shape for this graph:
    it is heavily multi-labelled -- ``Passage:Mantra`` (20,210 nodes),
    ``TextVersion:Internal`` (44,276), ``Concept:DomainEntity:Condition`` -- and the
    previous ``labels(n)[0]`` reported one label per node, chosen by an ordering Neo4j
    does not guarantee. The same node could be filed under a different label between runs,
    and in the meantime ``Mantra`` and ``Internal`` were missing from the census entirely
    while every ``Passage:Mantra`` was silently booked as a bare ``Passage``.

    No ``:Internal`` filter is applied, deliberately. This is the whole-graph census in
    the integrity suite, the counterpart of ``orphan_passages`` and
    ``duplicate_canonical_keys``: its job is to reconcile against the store's own totals,
    and 72,475 of the graph's 108,759 nodes are ``:Internal``, so excluding them would
    make a census that cannot be checked against anything. The ``Internal`` label is now
    itself a row, so a caller who wants the product-facing figure can subtract it -- or
    use ``domain.queries.product_graph_census``, which is the query written for that
    question and excludes internal nodes by construction.
    """
    label_query = """
    MATCH (n)
    UNWIND labels(n) AS label
    RETURN label, count(DISTINCT n) AS count
    ORDER BY count DESC, label
    """
    simple_rel_query = """
    MATCH ()-[r]->() RETURN type(r) AS rel_type, count(r) AS count
    ORDER BY rel_type
    """
    nodes = _run(session, label_query)
    rels = _run(session, simple_rel_query)
    return {"nodes": nodes, "relationships": rels}


def orphan_passages(session: Any) -> list[dict[str, Any]]:
    """Find Passage nodes with no incoming CONTAINS relationship."""
    return _run(
        session,
        """
        MATCH (p:Passage)
        WHERE NOT ()-[:CONTAINS]->(p)
        RETURN p.canonical_key AS canonical_key, p.veda AS veda
        ORDER BY p.canonical_key
        """,
    )


def duplicate_canonical_keys(session: Any) -> list[dict[str, Any]]:
    """Find any duplicate canonical_key values (should be zero)."""
    return _run(
        session,
        """
        MATCH (p:Passage)
        WITH p.canonical_key AS key, count(*) AS cnt
        WHERE cnt > 1
        RETURN key, cnt
        """,
    )
