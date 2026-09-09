"""The queries the enriched graph exists to answer.

Each entry is a named, parameterised Cypher query with a stated purpose, so the set can be
run as a suite, timed, and used as a regression test: a query that starts returning zero
rows is a defect in the graph, and one that starts taking seconds is a missing index.

Two conventions run through all of them.

**Real identities, not placeholders.** Every default parameter is a canonical key or
entity key that exists in this corpus -- ``VG:RV:SAK:M03:S062:V010`` is the Gayatri mantra,
``VG:DEVATA:AGNIH`` is Agni. A query suite parameterised with invented ids proves the
Cypher parses and nothing else.

**Evidence comes back with the answer.** Where a query returns an enrichment relationship
it also returns that relationship's trust, method, score and evidence. The point of the
enrichment layer is that "why are these connected?" is answerable, and a query library that
returns bare node pairs quietly gives that away.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Final


@dataclass(frozen=True)
class InsightQuery:
    """One named query, its purpose, and parameters that actually resolve."""

    name: str
    purpose: str
    cypher: str
    params: dict[str, Any] = field(default_factory=dict)

    def run(self, session: Any, **overrides: Any) -> list[dict[str, Any]]:
        merged = {**self.params, **overrides}
        return [dict(record) for record in session.run(self.cypher, **merged)]


#: A famous, unambiguous anchor used by several queries: RV 3.62.10, the Gayatri mantra.
GAYATRI: Final = "VG:RV:SAK:M03:S062:V010"
#: RV 1.1.1, the first verse of the Rigveda.
RV_FIRST: Final = "VG:RV:SAK:M01:S001:V001"
#: RV 10.129.1, the Nasadiya Sukta's opening -- the creation hymn.
NASADIYA: Final = "VG:RV:SAK:M10:S129:V001"

_EVIDENCE_RETURN = (
    "r.trust AS trust, r.method AS method, r.score AS score, "
    "r.match_level AS match_level, r.evidence AS evidence"
)


QUERIES: Final[tuple[InsightQuery, ...]] = (
    InsightQuery(
        "passages_reused_across_vedas",
        "Every mantra that recurs in another Veda, strongest relationship first.",
        f"""
        MATCH (a:Mantra)-[r:EXACT_PARALLEL_OF|VARIANT_OF|NEAR_PARALLEL_OF]->(b:Mantra)
        WHERE r.pipeline_version IS NOT NULL AND a.veda <> b.veda
        RETURN a.canonical_citation AS source, a.veda AS source_veda,
               b.canonical_citation AS target, b.veda AS target_veda,
               type(r) AS predicate, {_EVIDENCE_RETURN}
        ORDER BY r.score DESC, source ASC
        LIMIT $limit
        """,
        {"limit": 50},
    ),
    InsightQuery(
        "strongest_rv_sv_parallels",
        "The Samaveda's borrowings from the Rigveda, which are most of the Samaveda.",
        f"""
        MATCH (a:Mantra)-[r]->(b:Mantra)
        WHERE r.veda_pair = 'RV-SV' AND r.pipeline_version IS NOT NULL
        RETURN a.canonical_citation AS a, a.veda AS a_veda,
               b.canonical_citation AS b, b.veda AS b_veda,
               type(r) AS predicate, {_EVIDENCE_RETURN}
        ORDER BY r.score DESC, a ASC
        LIMIT $limit
        """,
        {"limit": 25},
    ),
    InsightQuery(
        "strongest_rv_yv_parallels",
        "Rigvedic verses the Vajasaneyi Samhita takes over for the sacrifice.",
        f"""
        MATCH (a:Mantra)-[r]->(b:Mantra)
        WHERE r.veda_pair = 'RV-YV' AND r.pipeline_version IS NOT NULL
        RETURN a.canonical_citation AS a, b.canonical_citation AS b,
               type(r) AS predicate, {_EVIDENCE_RETURN}
        ORDER BY r.score DESC, a ASC
        LIMIT $limit
        """,
        {"limit": 25},
    ),
    InsightQuery(
        "strongest_rv_av_parallels",
        "Where the Atharvaveda and the Rigveda share a verse.",
        f"""
        MATCH (a:Mantra)-[r]->(b:Mantra)
        WHERE r.veda_pair = 'AV-RV' AND r.pipeline_version IS NOT NULL
        RETURN a.canonical_citation AS a, b.canonical_citation AS b,
               type(r) AS predicate, {_EVIDENCE_RETURN}
        ORDER BY r.score DESC, a ASC
        LIMIT $limit
        """,
        {"limit": 25},
    ),
    InsightQuery(
        "agni_across_all_vedas",
        "Passages connected to Agni in any of the four Vedas, by any available route.",
        """
        MATCH (p:Mantra)
        WHERE (p)-[:HAS_DEVATA]->(:Devata {entity_key: $devata})
           OR (p)-[:MENTIONS_ENTITY]->(:Devata {entity_key: $devata})
           OR (p)-[:ABOUT_CONCEPT]->(:Concept {concept_id: $concept})
        RETURN p.veda AS veda, count(*) AS passages
        ORDER BY passages DESC
        """,
        {"devata": "VG:DEVATA:AGNIH", "concept": "VG:CONCEPT:AGNI-FIRE"},
    ),
    InsightQuery(
        "concepts_most_associated_with_soma",
        "Which concepts occur in the passages addressed to Soma.",
        """
        MATCH (p:Mantra)-[:HAS_DEVATA]->(:Devata {entity_key: $devata})
        MATCH (p)-[a:ABOUT_CONCEPT]->(c:Concept)
        RETURN c.preferred_label_sa AS concept_sa, c.preferred_label_en AS concept_en,
               count(*) AS passages, avg(a.score) AS mean_confidence
        ORDER BY passages DESC, concept_en ASC
        LIMIT $limit
        """,
        {"devata": "VG:DEVATA:SOMAH", "limit": 20},
    ),
    InsightQuery(
        "rishis_most_associated_with_a_devata",
        "Which seers are credited with the most hymns to one deity.",
        """
        MATCH (p:Mantra)-[:HAS_DEVATA]->(:Devata {entity_key: $devata})
        MATCH (p)-[:HAS_RISHI]->(r:Rishi)
        RETURN r.preferred_label AS rishi, count(*) AS mantras
        ORDER BY mantras DESC, rishi ASC
        LIMIT $limit
        """,
        {"devata": "VG:DEVATA:INDRAH", "limit": 15},
    ),
    InsightQuery(
        "chandas_distribution_for_a_devata",
        "The metres in which one deity is addressed.",
        """
        MATCH (p:Mantra)-[:HAS_DEVATA]->(:Devata {entity_key: $devata})
        MATCH (p)-[:HAS_CHANDAS]->(c:Chandas)
        RETURN c.preferred_label AS chandas, count(*) AS mantras
        ORDER BY mantras DESC, chandas ASC
        """,
        {"devata": "VG:DEVATA:AGNIH"},
    ),
    InsightQuery(
        "formulas_in_multiple_vedas",
        "Repeated phrases that cross a Veda boundary -- shared poetic diction.",
        """
        MATCH (f:Formula)
        WHERE f.cross_veda
        RETURN f.display_form AS formula, f.word_count AS words,
               f.occurrence_count AS occurrences, f.vedas AS vedas,
               f.derivation_method AS method
        ORDER BY size(f.vedas) DESC, f.occurrence_count DESC, formula ASC
        LIMIT $limit
        """,
        {"limit": 30},
    ),
    InsightQuery(
        "shortest_path_between_two_passages",
        "How two mantras connect, through deities, metres, concepts or shared text.",
        """
        MATCH (a:Passage {canonical_key: $from_key}), (b:Passage {canonical_key: $to_key})
        MATCH path = shortestPath((a)-[:HAS_DEVATA|HAS_RISHI|HAS_CHANDAS|USES_FORMULA
                                       |ABOUT_CONCEPT|EXACT_PARALLEL_OF|NEAR_PARALLEL_OF
                                       |VARIANT_OF*..6]-(b))
        RETURN [n IN nodes(path) |
                  coalesce(n.canonical_citation, n.preferred_label,
                           n.preferred_label_en, n.display_form)] AS hops,
               [rel IN relationships(path) | type(rel)] AS via,
               length(path) AS hop_count
        """,
        {"from_key": GAYATRI, "to_key": NASADIYA},
    ),
    InsightQuery(
        "concepts_bridging_two_vedas",
        "Concepts attested in both of two Vedas, ranked by how evenly they are shared.",
        """
        MATCH (p:Mantra)-[:ABOUT_CONCEPT]->(c:Concept)
        WHERE p.veda IN [$veda_a, $veda_b]
        WITH c,
             sum(CASE WHEN p.veda = $veda_a THEN 1 ELSE 0 END) AS in_a,
             sum(CASE WHEN p.veda = $veda_b THEN 1 ELSE 0 END) AS in_b
        WHERE in_a > 0 AND in_b > 0
        RETURN c.preferred_label_sa AS concept_sa, c.preferred_label_en AS concept_en,
               in_a, in_b,
               toFloat(CASE WHEN in_a < in_b THEN in_a ELSE in_b END) /
               toFloat(CASE WHEN in_a > in_b THEN in_a ELSE in_b END) AS balance
        ORDER BY balance DESC, in_a + in_b DESC
        LIMIT $limit
        """,
        {"veda_a": "RV", "veda_b": "AV", "limit": 20},
    ),
    InsightQuery(
        "most_central_devatas",
        "Deities by how much of the graph runs through them.",
        """
        MATCH (d:Devata)<-[r:HAS_DEVATA|MENTIONS_ENTITY]-(p:Mantra)
        RETURN d.preferred_label AS devata, d.devata_subtype AS subtype,
               count(DISTINCT p) AS passages,
               count(DISTINCT p.veda) AS vedas
        ORDER BY passages DESC, devata ASC
        LIMIT $limit
        """,
        {"limit": 20},
    ),
    InsightQuery(
        "most_connected_passages",
        "Mantras with the richest enrichment neighbourhood.",
        """
        MATCH (p:Mantra)
        OPTIONAL MATCH (p)-[r]-()
        WHERE r.pipeline_version IS NOT NULL
        WITH p, count(r) AS enrichment_degree
        WHERE enrichment_degree > 0
        RETURN p.canonical_citation AS citation, p.veda AS veda,
               enrichment_degree
        ORDER BY enrichment_degree DESC, citation ASC
        LIMIT $limit
        """,
        {"limit": 25},
    ),
    InsightQuery(
        "formula_hub_neighbourhood",
        "The passages sharing the single most widely used cross-Veda formula.",
        """
        MATCH (f:Formula)
        WHERE f.cross_veda
        WITH f ORDER BY f.occurrence_count DESC, f.formula_id ASC LIMIT 1
        MATCH (p:Mantra)-[u:USES_FORMULA]->(f)
        RETURN f.display_form AS formula, p.canonical_citation AS citation,
               p.veda AS veda, u.source_form AS as_written
        ORDER BY veda ASC, citation ASC
        LIMIT $limit
        """,
        {"limit": 40},
    ),
    InsightQuery(
        "similar_in_sense_but_not_in_words",
        "Passages in other Vedas that share this one's concepts but none of its words.",
        # Anchored on one passage, and that is not a convenience. The unanchored form --
        # match every pair of mantras sharing a concept -- is an all-pairs join in
        # disguise: `fire` alone is attached to 2,329 passages, which is 2.7 million pairs
        # from one concept, and running it exhausted a 1.4 GiB transaction heap before
        # returning a row. This is the same graph-explosion failure the enrichment layer
        # guards against in its edges, arriving through a query instead. Anchoring bounds
        # the work to one passage's concept neighbourhood, which is also the only form a
        # UI ever needs: the question is always "what else is like *this*".
        """
        MATCH (a:Mantra {canonical_key: $key})-[:ABOUT_CONCEPT]->(c:Concept)
        WITH a, collect(c) AS anchor_concepts
        UNWIND anchor_concepts AS c
        MATCH (b:Mantra)-[:ABOUT_CONCEPT]->(c)
        WHERE b.veda <> a.veda
        WITH a, b, count(DISTINCT c) AS shared_concepts
        WHERE shared_concepts >= $min_shared
          AND NOT (a)-[:EXACT_PARALLEL_OF|NEAR_PARALLEL_OF|VARIANT_OF|PARALLEL_TO]-(b)
        RETURN a.canonical_citation AS anchor, b.canonical_citation AS similar,
               b.veda AS similar_veda, shared_concepts
        ORDER BY shared_concepts DESC, similar ASC
        LIMIT $limit
        """,
        {"key": NASADIYA, "min_shared": 3, "limit": 25},
    ),
    InsightQuery(
        "textually_close_but_conceptually_apart",
        "Near parallels whose two sides were assigned different concepts.",
        """
        MATCH (a:Mantra)-[r:NEAR_PARALLEL_OF]->(b:Mantra)
        WHERE r.pipeline_version IS NOT NULL
        OPTIONAL MATCH (a)-[:ABOUT_CONCEPT]->(ca:Concept)
        OPTIONAL MATCH (b)-[:ABOUT_CONCEPT]->(cb:Concept)
        WITH a, b, r, collect(DISTINCT ca.concept_id) AS a_concepts,
             collect(DISTINCT cb.concept_id) AS b_concepts
        WHERE size(a_concepts) > 0 AND size(b_concepts) > 0
          AND NONE(x IN a_concepts WHERE x IN b_concepts)
        RETURN a.canonical_citation AS a, b.canonical_citation AS b,
               r.score AS score, a_concepts, b_concepts
        ORDER BY r.score DESC, a ASC
        LIMIT $limit
        """,
        {"limit": 20},
    ),
    InsightQuery(
        "everything_about_one_mantra",
        "One mantra with its text, translations, entities, concepts and parallels.",
        """
        MATCH (p:Passage {canonical_key: $key})
        OPTIONAL MATCH (p)-[:HAS_TEXT_VERSION]->(tv:TextVersion)
        OPTIONAL MATCH (p)-[:HAS_TRANSLATION]->(t:Translation)
        OPTIONAL MATCH (p)-[:HAS_DEVATA]->(d:Devata)
        OPTIONAL MATCH (p)-[:HAS_RISHI]->(rs:Rishi)
        OPTIONAL MATCH (p)-[:HAS_CHANDAS]->(ch:Chandas)
        OPTIONAL MATCH (p)-[:ABOUT_CONCEPT]->(c:Concept)
        OPTIONAL MATCH (p)-[:USES_FORMULA]->(f:Formula)
        OPTIONAL MATCH (p)-[par]-(other:Mantra)
          WHERE par.pipeline_version IS NOT NULL
        RETURN p.canonical_citation AS citation,
               collect(DISTINCT tv.text_nfc)[0..3] AS texts,
               collect(DISTINCT t.text)[0..3] AS translations,
               collect(DISTINCT d.preferred_label) AS devatas,
               collect(DISTINCT rs.preferred_label) AS rishis,
               collect(DISTINCT ch.preferred_label) AS chandas,
               collect(DISTINCT c.preferred_label_en) AS concepts,
               collect(DISTINCT f.display_form)[0..8] AS formulas,
               collect(DISTINCT other.canonical_citation)[0..10] AS parallels
        """,
        {"key": GAYATRI},
    ),
    InsightQuery(
        "concept_distribution_by_veda",
        "How each concept is spread across the four Vedas.",
        """
        MATCH (p:Mantra)-[:ABOUT_CONCEPT]->(c:Concept)
        WITH c, p.veda AS veda, count(*) AS n
        WITH c, collect([veda, n]) AS spread, sum(n) AS total
        RETURN c.preferred_label_sa AS concept_sa, c.preferred_label_en AS concept_en,
               c.node_type AS node_type, total, spread, size(spread) AS vedas
        ORDER BY vedas DESC, total DESC, concept_en ASC
        LIMIT $limit
        """,
        {"limit": 40},
    ),
    InsightQuery(
        "formula_distribution_by_veda",
        "How each formula is spread across the four Vedas.",
        """
        MATCH (p:Mantra)-[:USES_FORMULA]->(f:Formula)
        WITH f, p.veda AS veda, count(*) AS n
        WITH f, collect([veda, n]) AS spread, sum(n) AS total
        RETURN f.display_form AS formula, f.word_count AS words, total, spread,
               size(spread) AS vedas
        ORDER BY vedas DESC, total DESC, formula ASC
        LIMIT $limit
        """,
        {"limit": 40},
    ),
    InsightQuery(
        "neighbourhood_of_a_famous_mantra",
        "Everything within two hops of the Gayatri mantra.",
        """
        MATCH (p:Passage {canonical_key: $key})
        MATCH (p)-[r1]-(n1)
        WHERE type(r1) <> 'HAS_TEXT_VERSION'
        OPTIONAL MATCH (n1)-[r2]-(n2)
        WHERE type(r2) IN ['USES_FORMULA', 'ABOUT_CONCEPT', 'HAS_DEVATA',
                           'EXACT_PARALLEL_OF', 'NEAR_PARALLEL_OF', 'VARIANT_OF']
          AND n2 <> p
        RETURN type(r1) AS via,
               coalesce(n1.canonical_citation, n1.preferred_label, n1.preferred_label_en,
                        n1.display_form, n1.text) AS neighbour,
               count(DISTINCT n2) AS second_hop
        ORDER BY second_hop DESC, via ASC, neighbour ASC
        LIMIT $limit
        """,
        {"key": GAYATRI, "limit": 30},
    ),
    InsightQuery(
        "cross_veda_relationship_matrix",
        "The core deliverable: counts per Veda pair, per predicate.",
        """
        MATCH ()-[r]->()
        WHERE r.pipeline_version IS NOT NULL AND r.veda_pair IS NOT NULL
        RETURN r.veda_pair AS veda_pair, type(r) AS predicate,
               r.trust AS trust, count(*) AS edges
        ORDER BY veda_pair ASC, predicate ASC
        """,
    ),
    InsightQuery(
        "trust_class_census",
        "Every enrichment edge by trust class, so provenance is auditable at a glance.",
        """
        MATCH ()-[r]->()
        WHERE r.pipeline_version IS NOT NULL
        RETURN type(r) AS predicate, r.trust AS trust, r.state AS state, count(*) AS edges
        ORDER BY edges DESC, predicate ASC
        """,
    ),
    InsightQuery(
        "why_are_these_connected",
        "The UI contract: one edge, fully explained, without a second lookup.",
        f"""
        MATCH (a:Passage {{canonical_key: $from_key}})-[r]-(b:Passage)
        WHERE r.pipeline_version IS NOT NULL
        RETURN a.canonical_citation AS source, b.canonical_citation AS target,
               type(r) AS predicate, {_EVIDENCE_RETURN},
               r.state AS state, r.run_id AS run_id, r.levels_reached AS levels
        ORDER BY r.score DESC, target ASC
        LIMIT $limit
        """,
        {"from_key": "VG:RV:SAK:M06:S016:V010", "limit": 10},
    ),
    InsightQuery(
        "corpus_caveats_in_the_graph",
        "The QA findings each corpus records about itself.",
        """
        MATCH (w:Work)-[:HAS_QA_ISSUE]->(q:QAIssue)
        RETURN w.veda AS veda, q.severity AS severity, q.check_id AS check_id,
               count(*) AS findings
        ORDER BY veda ASC, severity ASC, findings DESC
        """,
    ),
    InsightQuery(
        "untranslated_but_paralleled",
        "Mantras with no English of their own that have a translated counterpart elsewhere.",
        """
        MATCH (a:Mantra)-[r]-(b:Mantra)
        WHERE r.pipeline_version IS NOT NULL
          AND NOT (a)-[:HAS_TRANSLATION]->()
          AND (b)-[:HAS_TRANSLATION]->()
        MATCH (b)-[:HAS_TRANSLATION]->(t:Translation)
        RETURN a.canonical_citation AS untranslated, a.veda AS veda,
               b.canonical_citation AS via, b.veda AS via_veda,
               type(r) AS predicate, r.score AS score, left(t.text, 120) AS english
        ORDER BY r.score DESC, untranslated ASC
        LIMIT $limit
        """,
        {"limit": 25},
    ),
)


def query_by_name(name: str) -> InsightQuery:
    for query in QUERIES:
        if query.name == name:
            return query
    raise KeyError(f"no insight query named {name!r}")
