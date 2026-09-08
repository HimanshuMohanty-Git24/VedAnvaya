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


def fetch_passages_by_devata(session: Any, devata_key: str) -> list[dict[str, Any]]:
    """Fetch all Passages linked to a Devata entity."""
    return _run(
        session,
        """
        MATCH (p:Passage)-[:HAS_DEVATA]->(d:Devata {entity_key: $key})
        RETURN p.canonical_key AS canonical_key, p.canonical_citation AS citation
        ORDER BY p.canonical_key LIMIT 100
        """,
        key=devata_key,
    )


def fetch_passages_by_rishi(session: Any, rishi_key: str) -> list[dict[str, Any]]:
    """Fetch all Passages linked to a Rishi entity."""
    return _run(
        session,
        """
        MATCH (p:Passage)-[:HAS_RISHI]->(r:Rishi {entity_key: $key})
        RETURN p.canonical_key AS canonical_key, p.canonical_citation AS citation
        ORDER BY p.canonical_key LIMIT 100
        """,
        key=rishi_key,
    )


def fetch_passages_by_chandas(session: Any, chandas_key: str) -> list[dict[str, Any]]:
    """Fetch all Passages linked to a Chandas entity."""
    return _run(
        session,
        """
        MATCH (p:Passage)-[:HAS_CHANDAS]->(c:Chandas {entity_key: $key})
        RETURN p.canonical_key AS canonical_key, p.canonical_citation AS citation
        ORDER BY p.canonical_key LIMIT 100
        """,
        key=chandas_key,
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
    """Fetch exact parallels of a given Passage."""
    return _run(
        session,
        """
        MATCH (p:Passage {canonical_key: $key})-[:EXACT_PARALLEL_OF]->(q:Passage)
        RETURN q.canonical_key AS parallel_key, q.canonical_citation AS citation
        """,
        key=canonical_key,
    )


def fetch_near_parallels(session: Any, canonical_key: str) -> list[dict[str, Any]]:
    """Fetch accepted near parallels (PARALLEL_TO), which are not verbatim matches."""
    return _run(
        session,
        """
        MATCH (p:Passage {canonical_key: $key})-[r:PARALLEL_TO]->(q:Passage)
        RETURN q.canonical_key AS parallel_key, q.canonical_citation AS citation,
               r.similarity AS similarity, r.status AS status
        ORDER BY r.similarity DESC
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


def fetch_devata_lexical_mentions(session: Any, devata_key: str) -> list[dict[str, Any]]:
    """Fetch passages lexically mentioning a Devata (MENTIONS_ENTITY, not Anukramani)."""
    return _run(
        session,
        """
        MATCH (p:Passage)-[r:MENTIONS_ENTITY]->(d:Devata {entity_key: $key})
        RETURN p.canonical_key AS canonical_key, r.occurrence_count AS count,
               r.provenance_class AS provenance_class
        ORDER BY p.canonical_key LIMIT 100
        """,
        key=devata_key,
    )


def graph_statistics(session: Any) -> dict[str, Any]:
    """Return node and relationship counts by type."""
    simple_node_query = """
    MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count
    ORDER BY label
    """
    simple_rel_query = """
    MATCH ()-[r]->() RETURN type(r) AS rel_type, count(r) AS count
    ORDER BY rel_type
    """
    nodes = _run(session, simple_node_query)
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
