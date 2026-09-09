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

**A scope claim belongs on the query, not in the reader's head.** Only the Rigveda has the
manual morphological annotation, so ``HAS_DEVATA``, ``MENTIONS_LEMMA`` and
``HAS_SEMANTIC_ASSERTION`` are structurally RV-only while ``MENTIONS_DEVATA``,
``ABOUT_CONCEPT`` and ``USES_FORMULA`` span all four Vedas. A cross-Veda query built on the
first group reads a *missing annotation layer* as an *absence in the text*, which is the
worst thing this catalogue can do, and it is invisible in the result set. Queries whose
reach is narrower than their column names suggest therefore carry a ``caveat``.

**Two layers can share one label without sharing a strength.** ``SemanticAssertion`` holds
2,406 TIER_B nodes derived by rule from the Sanskrit annotation and 2,459 TIER_D nodes a
model extracted, unreviewed, from a 19th-century English translation. Every query below that
touches it either filters ``derivation`` or returns it, because one figure over both would
average the two -- and they differ in reach as well as in trust, the rule layer covering
2,228 passages against the model layer's 398. ``MENTIONS_DEVATA`` carries the same warning in
milder form: it does span four corpora, but by manual lemma annotation in the Rigveda and
surface string matching everywhere else.
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
    #: What the result set does NOT establish -- above all, which Vedas the traversal can
    #: physically reach. Empty where the query is a census whose scope is its own answer.
    caveat: str = ""

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
        # The lexical route is MENTIONS_DEVATA, not MENTIONS_ENTITY. The 9,000
        # MENTIONS_ENTITY edges onto :Devata were retired as duplicates of MENTIONS_LEMMA
        # and were Rigveda-only besides, so that disjunct contributed nothing here and the
        # query's promise of "all four Vedas" rested entirely on ABOUT_CONCEPT.
        # MENTIONS_DEVATA is the four-Veda replacement. On its own it reaches AV 471, YV
        # 261 and SV 187 passages; net of what ABOUT_CONCEPT already found, it lifts the
        # non-RV rows by AV +64, YV +141 and SV +72.
        """
        MATCH (p:Mantra)
        WHERE (p)-[:HAS_DEVATA]->(:Devata {entity_key: $devata})
           OR (p)-[:MENTIONS_DEVATA]->(:Devata {entity_key: $devata})
           OR (p)-[:ABOUT_CONCEPT]->(:Concept {concept_id: $concept})
        RETURN p.veda AS veda, count(DISTINCT p) AS passages
        ORDER BY passages DESC
        """,
        {"devata": "VG:DEVATA:AGNIH", "concept": "VG:CONCEPT:AGNI-FIRE"},
        caveat=(
            "The three routes are not equally available: HAS_DEVATA is Rigveda-only, so "
            "the RV row is reachable by three routes and the other three rows by two. "
            "Compare the rows as shares of their corpus (RV 10,552 mantras, AV 5,839, YV "
            "1,975, SV 1,844), not as totals. `agni` is also the word for fire, so a "
            "MENTIONS_DEVATA hit may mean the element: 4,384 of the RV's theonym mentions "
            "are graded DEITY_AMBIGUOUS and this query does not filter on that grade."
        ),
    ),
    InsightQuery(
        "concepts_most_associated_with_soma",
        "Which concepts occur in the passages addressed to Soma.",
        # count(DISTINCT p), not count(*): the two MATCH patterns join into one row per
        # (passage, HAS_DEVATA edge, concept) triple, so count(*) counted rows and
        # avg(a.score) was weighted by the deity-edge multiplicity -- worse than an
        # inflated total, because it presents as a confidence figure. That multiplicity
        # is currently 1 (HAS_DEVATA is MERGEd once per passage-deity pair), so these
        # numbers do not move; the change buys the guarantee, not a correction. WITH
        # DISTINCT p makes the intent structural rather than dependent on that fact.
        """
        MATCH (p:Mantra)-[:HAS_DEVATA]->(:Devata {entity_key: $devata})
        WITH DISTINCT p
        MATCH (p)-[a:ABOUT_CONCEPT]->(c:Concept)
        RETURN c.preferred_label_sa AS concept_sa, c.preferred_label_en AS concept_en,
               count(DISTINCT p) AS passages, avg(a.score) AS mean_confidence
        ORDER BY passages DESC, concept_en ASC
        LIMIT $limit
        """,
        {"devata": "VG:DEVATA:SOMAH", "limit": 20},
        caveat=(
            "Anchored on HAS_DEVATA, so Rigveda-only: this is 'concepts in the RV hymns "
            "the Anukramani ascribes to Soma', not 'concepts near Soma in the corpus'. "
            "VG:DEVATA:SOMAH is also a small fraction of Soma: it is ascribed 80 mantras, "
            "against the 1,087 of the Pavamana cycle, which the Anukramani labels "
            "VG:DEVATA:PAVAMANAH-SOMAH and which this query therefore never sees. Change "
            "the parameter to read the ninth Mandala."
        ),
    ),
    InsightQuery(
        "rishis_most_associated_with_a_devata",
        "Which seers are credited with the most hymns to one deity.",
        # count(DISTINCT p) rather than count(*), which counted (deity edge x rishi edge)
        # pairs per passage. Both edge types are MERGEd once per passage-entity pair, so
        # the product is 1 and the figures are unchanged -- the column was a row count
        # that happened to equal the passage count, and only kept doing so by accident of
        # how the loader writes. domain/queries.py::rishis_invoking_deity asks this
        # question with count(DISTINCT p) already, and the two agree at 217 for Indra.
        """
        MATCH (p:Mantra)-[:HAS_DEVATA]->(:Devata {entity_key: $devata})
        MATCH (p)-[:HAS_RISHI]->(r:Rishi)
        RETURN r.preferred_label AS rishi, count(DISTINCT p) AS mantras
        ORDER BY mantras DESC, rishi ASC
        LIMIT $limit
        """,
        {"devata": "VG:DEVATA:INDRAH", "limit": 15},
        caveat=(
            "Rigveda-only, because HAS_DEVATA is. 10,093 of the RV's 10,565 HAS_RISHI "
            "edges are a sukta's seer projected onto its mantras, so `mantras` measures "
            "hymn length as much as devotion; only 472 RV seer edges are source-stated. "
            "See domain/queries.py::rishis_invoking_deity_strict."
        ),
    ),
    InsightQuery(
        "chandas_distribution_for_a_devata",
        "The metres in which one deity is addressed.",
        # count(DISTINCT p): same latent Cartesian defect as the query above, and the same
        # unchanged figures for the same reason. A mantra does carry more than one metre
        # edge in this corpus (16,320 edges over 15,057 passages), but grouping by c means
        # each row sees only its own, so the inflation never fired here either.
        """
        MATCH (p:Mantra)-[:HAS_DEVATA]->(:Devata {entity_key: $devata})
        MATCH (p)-[:HAS_CHANDAS]->(c:Chandas)
        RETURN c.preferred_label AS chandas, count(DISTINCT p) AS mantras
        ORDER BY mantras DESC, chandas ASC
        """,
        {"devata": "VG:DEVATA:AGNIH"},
        caveat=(
            "Rigveda-only through HAS_DEVATA, even though HAS_CHANDAS itself now reaches "
            "the AV (5,797 edges). A per-deity metre table for the Atharvaveda is not "
            "reachable this way: the AV has metre and seer but no deity ascription, its "
            "deity layer being DevataAscription reached by HAS_DEVATA_ASCRIPTION."
        ),
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
        "Deities by how much of the graph runs through them, across all four Vedas.",
        # MENTIONS_DEVATA alone, where this was HAS_DEVATA|MENTIONS_ENTITY. Half that
        # union no longer exists and the other half is Rigveda-only, so the `vedas`
        # column returned 1 for every deity in the table while presenting as a spread
        # measure -- a spread of one, reported as a measurement. MENTIONS_DEVATA is the
        # only deity predicate that reaches all four corpora, so it is also the only one
        # from which `vedas` can carry information. Keeping HAS_DEVATA in the union was
        # rejected: it would add Rigvedic weight that the other corpora cannot earn, and
        # `passages` would stop meaning one comparable thing per row.
        """
        MATCH (d:Devata)<-[:MENTIONS_DEVATA]-(p:Mantra)
        RETURN d.preferred_label AS devata, d.devata_subtype AS subtype,
               count(DISTINCT p) AS passages,
               count(DISTINCT p.veda) AS vedas,
               collect(DISTINCT p.veda) AS veda_list
        ORDER BY passages DESC, devata ASC
        LIMIT $limit
        """,
        {"limit": 20},
        caveat=(
            "Centrality by lexical naming, not by Anukramani ascription: a deity named in "
            "passing counts the same as one a whole hymn addresses. The two measures "
            "diverge hard and neither is the corrected version of the other -- "
            "pavamanah somah is ascribed 1,087 mantras and named in 89, visvedevah 805 "
            "and 5, while prthivi is named in 666 and ascribed 4. A deity can therefore "
            "be central here and near-absent from a HAS_DEVATA ranking, and the reverse. "
            "Mentions are not filtered on referent_certainty, so DEITY_AMBIGUOUS hits "
            "(8,485 of 16,261 edges, and the majority of each non-RV corpus) count; "
            "deities whose name is also a common noun -- agni fire, apah waters, vak "
            "speech -- are flattered by that."
        ),
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
        # `min_shared` is 2, not 3. `ABOUT_CONCEPT` is capped at four edges per passage
        # and averages 1.79, so a floor of 3 demands three quarters of a passage's whole
        # conceptual profile to coincide -- which is why this query returned zero rows for
        # every anchor rather than only for a badly chosen one. The Nasadiya anchor was
        # separately empty until V3 modelled `sat` and `asat`; it now carries both at
        # 0.85, so the anchor and the floor were two independent causes of the same
        # silence and both had to move.
        {"key": NASADIYA, "min_shared": 2, "limit": 25},
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
        MATCH (q:QAIssue)-[:QA_ISSUE_ON]->(w:Work)
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
    # ------------------------------------------------------------------------
    # The layers added after the four-Veda projection landed. Nothing above this
    # line traverses HAS_SEMANTIC_ASSERTION, PERFORMS_ACTION, IS_ASKED_TO,
    # MEMBER_OF_FAMILY or CO_OCCURS_WITH, so the graph's newest evidence had no
    # published route into it at all.
    # ------------------------------------------------------------------------
    InsightQuery(
        "devata_mentions_by_veda_and_certainty",
        "The four-Veda deity layer, split by corpus, method and referent certainty.",
        # One MATCH pattern, so count(*) is a count of mention edges and is intended;
        # count(DISTINCT p) is returned beside it because a passage carries several
        # mention edges to one deity when the name occurs under several forms.
        """
        MATCH (p:Mantra)-[m:MENTIONS_DEVATA]->(:Devata)
        RETURN m.veda AS veda, m.extraction_path AS extraction_path,
               m.referent_certainty AS certainty, count(*) AS edges,
               count(DISTINCT p) AS passages, count(DISTINCT m.mention_id) AS mentions
        ORDER BY veda ASC, edges DESC
        """,
        caveat=(
            "The census to read before any other MENTIONS_DEVATA query. It spans all four "
            "corpora, which is why the predicate exists, but by two unlike instruments: "
            "the RV's 10,284 edges are the manual scholarly lemma annotation and the other "
            "5,977 are surface token or sandhi matching with no morphology behind them. "
            "DEITY_CERTAIN is a Rigvedic majority (5,900 of 10,284) and a minority in every "
            "other corpus, so a single corpus-wide certainty rate would be meaningless."
        ),
    ),
    InsightQuery(
        "deity_action_profile",
        "What one deity is said to do and asked to do, with the verbal roots behind each.",
        """
        MATCH (d:Devata {entity_key: $devata})-[r:PERFORMS_ACTION|IS_ASKED_TO]->
              (a:ActionPredicate)
        RETURN type(r) AS frame, a.predicate AS action, a.argument_frame AS argument_frame,
               r.assertion_count AS assertions, r.passage_count AS passages,
               r.roots AS verbal_roots
        ORDER BY assertions DESC, action ASC
        LIMIT $limit
        """,
        {"devata": "VG:DEVATA:INDRAH", "limit": 40},
        caveat=(
            "Rigveda-only, and structurally so: PERFORMS_ACTION (441 edges) and IS_ASKED_TO "
            "(224) are aggregates over the 2,406 MORPHOLOGY_RULE assertions, which are "
            "derived from the Rigveda's lemma annotation. All 665 edges are Rigvedic, so "
            "the Samaveda, Yajurveda and Atharvaveda are absent entirely rather than "
            "quiet. `verbal_roots` is the evidence: the predicate is a bucket over roots, "
            "and IS_OR_BECOMES leads most deities' tables because it collects the language's "
            "two commonest verbs rather than because being is anyone's characteristic act."
        ),
    ),
    InsightQuery(
        "assertion_agent_predicate_pairs",
        "Who the rule layer says acts, what it says they do, and in which grammatical frame.",
        # count(DISTINCT s), not count(*): three MATCH patterns are in scope and the
        # passage join would multiply the assertion count by the passage's other
        # assertions if the aggregate were over rows.
        """
        MATCH (p:Mantra)-[:HAS_SEMANTIC_ASSERTION]->
              (s:SemanticAssertion {derivation: 'MORPHOLOGY_RULE'})
        MATCH (s)-[:ASSERTION_AGENT]->(agent:Devata)
        MATCH (s)-[:ASSERTION_PREDICATE]->(a:ActionPredicate)
        RETURN agent.preferred_label AS agent, a.predicate AS predicate,
               s.frame AS frame, count(DISTINCT s) AS assertions,
               count(DISTINCT p) AS passages,
               collect(DISTINCT s.root_label)[0..6] AS roots
        ORDER BY assertions DESC, agent ASC, predicate ASC
        LIMIT $limit
        """,
        {"limit": 40},
        caveat=(
            "Filtered to derivation = 'MORPHOLOGY_RULE' deliberately. SemanticAssertion is "
            "one label over two layers of very unequal strength -- 2,406 TIER_B nodes "
            "derived by rule from the Sanskrit annotation and 2,459 TIER_D nodes extracted "
            "by a model from a 19th-century English translation -- and an aggregate over "
            "both would average the two. This query never sees the model layer. All 4,865 "
            "assertions of either kind are Rigvedic."
        ),
    ),
    InsightQuery(
        "model_extracted_assertions_about_a_deity",
        "What the unreviewed model layer claims about one deity, with its own hedges.",
        """
        MATCH (p:Mantra)-[:HAS_SEMANTIC_ASSERTION]->
              (s:SemanticAssertion {derivation: 'MODEL_EXTRACTION'})
        MATCH (s)-[:ASSERTION_TARGET]->(t:Devata {entity_key: $devata})
        RETURN s.semantic_predicate AS predicate, s.explicitness AS explicitness,
               s.object_kind AS object_kind, s.normalized_head AS claim,
               p.canonical_citation AS citation, s.evidence_basis AS evidence_basis,
               s.review_state AS review_state, s.human_gold_status AS human_gold,
               s.quality_tier AS tier
        ORDER BY citation ASC, predicate ASC
        LIMIT $limit
        """,
        {"devata": "VG:DEVATA:AGNIH", "limit": 40},
        caveat=(
            "Every row is TIER_D, review_state = UNREVIEWED and human_gold_status = "
            "UNANNOTATED, and those columns are returned rather than filtered away so the "
            "status travels with the claim. evidence_basis = TRANSLATION: the extraction "
            "read Griffith's English, so a row here is evidence about a translation and "
            "not about the Sanskrit. `explicitness` = STRONG_INFERENCE marks where the "
            "model judged its own reading to go beyond the words. Only 799 of the 2,459 "
            "model assertions carry an ASSERTION_TARGET at all, so this route sees a third "
            "of that layer; the rest name their object only in prose."
        ),
    ),
    InsightQuery(
        "deity_pairs_above_chance",
        "Deity pairs that share passages far more often than their frequencies predict.",
        # Undirected. CO_OCCURS_WITH is written once per pair in a canonical direction
        # (a.entity_key < b.entity_key), so a directed match returns half the pairs
        # with no indication that it has done so. The WHERE restores the canonical
        # order, which keeps each pair to one row under the undirected traversal.
        """
        MATCH (a:Devata)-[r:CO_OCCURS_WITH]-(b:Devata)
        WHERE a.entity_key < b.entity_key
        RETURN a.preferred_label AS deity_a, b.preferred_label AS deity_b,
               r.lift AS lift, r.passage_count AS shared_passages,
               r.rv_passage_count AS rigvedic, r.non_rv_passage_count AS non_rigvedic,
               r.vedas AS vedas, r.per_veda_counts AS per_veda_counts,
               r.evidence_caveat AS evidence_caveat
        ORDER BY r.lift DESC, shared_passages DESC
        LIMIT $limit
        """,
        {"limit": 30},
        caveat=(
            "A top-30 of 292 pairs by lift, which is co-occurrence over the product of the "
            "marginals -- so a rare pair can outrank a frequent one and `shared_passages` "
            "must be read beside it. The rigvedic/non-rigvedic split is returned because it "
            "decides what the row means: Mitra-Varuna at lift 13.2 is 228 Rigvedic against "
            "43 elsewhere, while 70 of the 292 pairs are majority non-Rigvedic. "
            "Co-occurrence is two names in one passage, not co-invocation; where the "
            "tradition means a pair it uses a dual deity, which is a separate entity. Built "
            "on MENTIONS_DEVATA, so unfiltered on referent_certainty."
        ),
    ),
    InsightQuery(
        "formula_families_by_veda_span",
        "How far formula families reach: shared diction measured by corpus count.",
        """
        MATCH (f:FormulaFamily)
        RETURN f.veda_span AS vedas_reached, f.cross_veda AS cross_veda,
               count(*) AS families, sum(f.member_count) AS memberships,
               sum(f.occurrence_count) AS occurrences,
               collect(f.representative_display_form)[0..5] AS examples
        ORDER BY vedas_reached DESC
        """,
        caveat=(
            "Complete over all 720 families. A family is a representative wording plus "
            "everything that contains or closely resembles it, so `vedas_reached` measures "
            "shared diction and not a demonstrated line of transmission -- and the 105 "
            "single-Veda families are the baseline the 615 cross-Veda ones should be read "
            "against. `examples` is capped at 5 per row with the true count in `families`."
        ),
    ),
    InsightQuery(
        "formula_family_members",
        "One family's members, each with the role and evidence that put it there.",
        # count(DISTINCT p) rather than count(*): the membership pattern and the
        # USES_FORMULA pattern are both in scope, so a widely used formula would
        # otherwise be multiplied by its own membership row.
        """
        MATCH (f:Formula)-[m:MEMBER_OF_FAMILY]->(ff:FormulaFamily {family_id: $family})
        OPTIONAL MATCH (p:Mantra)-[:USES_FORMULA]->(f)
        RETURN ff.representative_display_form AS representative,
               f.display_form AS member, m.role AS role, m.quality_tier AS tier,
               m.contains_representative AS contains_representative,
               m.containment_is_transitive AS only_transitive,
               m.similarity AS similarity, count(DISTINCT p) AS passages,
               collect(DISTINCT p.veda) AS vedas
        ORDER BY passages DESC, member ASC
        LIMIT $limit
        """,
        {
            "family": "VG:ENRICH:FORMULA-FAMILY:709faeaecdc5a79716fa565ce0a051f0",
            "limit": 40,
        },
        caveat=(
            "The default is visva bhuvana, the largest family reaching all four Vedas: 14 "
            "members, 1 core and 13 expansions. `contains_representative` is the load-"
            "bearing column -- 1,796 of the layer's 2,037 memberships directly contain the "
            "representative wording and 240 reach it only transitively, through another "
            "member, which is a much weaker claim that the tier does not distinguish. A "
            "member's `vedas` is where that wording occurs, not where the family does."
        ),
    ),
    InsightQuery(
        "rituals_with_passages_and_apparatus",
        "Each rite with the passages said to describe it, its officiants and its purposes.",
        """
        MATCH (r:Ritual)
        OPTIONAL MATCH (r)-[:DESCRIBED_IN]->(p:Mantra)
        OPTIONAL MATCH (r)-[:PERFORMED_BY]->(office:RitualRole)
        OPTIONAL MATCH (r)-[:PERFORMED_FOR]->(purpose)
        OPTIONAL MATCH (r)-[:HAS_STEP]->(step)
        RETURN r.display_label AS ritual, count(DISTINCT p) AS passages,
               collect(DISTINCT p.veda) AS vedas,
               collect(DISTINCT office.display_label) AS officiants,
               collect(DISTINCT purpose.display_label) AS purposes,
               count(DISTINCT step) AS steps
        ORDER BY passages DESC, ritual ASC
        """,
        caveat=(
            "Complete over all 8 rites, and thin because the corpus is: 71 DESCRIBED_IN "
            "edges and 3 HAS_STEP edges in the whole graph, all TIER_D curation. Elaborate "
            "procedure is Brahmana and Sutra material and was deliberately not imported "
            "into Samhita passages. count(DISTINCT ...) throughout, not count(*): four "
            "OPTIONAL MATCHes are in scope and the yajna row alone would multiply 9 "
            "officiants by 4 purposes by 8 passages into 288."
        ),
    ),
    InsightQuery(
        "layer_veda_scope_census",
        "Which corpora each derived layer actually reaches, as recorded on its own nodes.",
        # UNWIND over an explicit label list, never labels(n)[0]: these nodes carry
        # several labels and Neo4j does not guarantee labels() ordering, so [0] would
        # pick arbitrarily while looking like a stable grouping key.
        """
        MATCH (n)
        WHERE n.layer_veda_scope IS NOT NULL
        UNWIND [l IN labels(n) WHERE l IN $layers] AS layer
        RETURN layer, n.layer_veda_scope_source AS derived_from,
               n.layer_veda_scope AS reaches, count(DISTINCT n) AS nodes
        ORDER BY layer ASC, nodes DESC
        """,
        {
            "layers": [
                "Chandas",
                "Rishi",
                "DevataAscription",
                "SemanticAssertion",
                "ActionPredicate",
            ]
        },
        caveat=(
            "`reaches` is measured from the graph, so a corpus missing from the list means "
            "the layer has no coverage of it and NOT that the corpus lacks the thing -- "
            "which is the single most useful sentence to have before reading a zero "
            "anywhere else in this catalogue. Every row is single-Veda: not one layer "
            "carrying this property spans two corpora. One ActionPredicate has reaches = "
            "[] and reaches nothing at all."
        ),
    ),
    InsightQuery(
        "model_adjudicated_edges_with_reasons",
        "The reviewed edge layer: what was accepted, and the reason recorded for each.",
        """
        MATCH (p:Mantra)-[r]->(target)
        WHERE r.quality_tier = 'TIER_C'
        RETURN p.canonical_citation AS citation, p.veda AS veda, type(r) AS predicate,
               target.display_label AS target, r.object_kind AS object_kind,
               r.review_verdict AS verdict, r.review_reason AS review_reason,
               r.reviewer_model AS reviewer_model,
               r.review_sanskrit_checked AS sanskrit_checked,
               r.review_passage_read AS passage_read
        ORDER BY citation ASC, predicate ASC, target ASC
        LIMIT $limit
        """,
        {"limit": 30},
        caveat=(
            "A top-30 by citation of 587 TIER_C edges. TIER_C is MODEL_ADJUDICATED, not "
            "human-reviewed: a model re-read each passage and accepted the edge with a "
            "stated reason. No edge anywhere in this graph carries HUMAN_REVIEWED and none "
            "may claim to. The layer's reach runs opposite to the assertion layer's -- all "
            "587 are Yajurvedic (320) or Atharvavedic (267) and not one is Rigvedic -- so "
            "this reviews exactly the two corpora the assertion layer never touches, and "
            "the two are not comparable. 16 NEEDS_MORE_EVIDENCE and 10 AMBIGUOUS verdicts "
            "stayed TIER_D rather than being deleted, so the rejections remain auditable."
        ),
    ),
)


def query_by_name(name: str) -> InsightQuery:
    for query in QUERIES:
        if query.name == name:
            return query
    raise KeyError(f"no insight query named {name!r}")
