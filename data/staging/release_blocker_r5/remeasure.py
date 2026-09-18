"""Remeasure every R5 closure against the live store. Measurement first, status second."""

from __future__ import annotations

import json
import pathlib

import _q

HERE = pathlib.Path(__file__).resolve().parent


def go(session):
    out: dict[str, object] = {}

    out["GAP-SEMANTICS-003"] = {
        "closure_measure": "MATCH (a:SemanticAssertion)-[:ASSERTION_TARGET]->(x) WHERE NOT x:Devata RETURN count(*)",
        "before": 0,
        "after": _q.one(
            session,
            "MATCH (a:SemanticAssertion)-[:ASSERTION_TARGET]->(x) WHERE NOT x:Devata RETURN count(*)",
        ),
        "clause_all_three_slots_before": 0,
        "clause_all_three_slots_after": _q.one(
            session,
            """
            MATCH (a:SemanticAssertion)
            WHERE (a)-[:ASSERTION_AGENT]->() AND (a)-[:ASSERTION_PREDICATE]->()
              AND (a)-[:ASSERTION_TARGET]->()
            RETURN count(a)
            """,
        ),
        "target_labels": _q.rows(
            session,
            """
            MATCH (a:SemanticAssertion)-[:ASSERTION_TARGET]->(x)
            RETURN CASE WHEN x:Devata THEN 'Devata' ELSE 'DomainEntity' END AS kind,
                   count(*) AS c ORDER BY c DESC
            """,
        ),
        "tier_not_blended": _q.rows(
            session,
            """
            MATCH ()-[r:ASSERTION_AGENT|ASSERTION_TARGET]->()
            RETURN r.derivation AS derivation, r.quality_tier AS tier, count(*) AS c
            ORDER BY c DESC
            """,
        ),
    }

    out["GAP-ENTITY_COVERAGE-004"] = {
        "expected_source_null": _q.one(
            session, "MATCH (n:DomainEntity) WHERE n.expected_source IS NULL RETURN count(n)"
        ),
        "expectation_origin_null": _q.one(
            session, "MATCH (n:DomainEntity) WHERE n.expectation_origin IS NULL RETURN count(n)"
        ),
        "origin_distribution": _q.rows(
            session,
            "MATCH (n:DomainEntity) RETURN n.expectation_origin AS origin, count(*) AS c ORDER BY c DESC",
        ),
        "unsupported_expected_source_assertions": _q.one(
            session,
            """
            MATCH (n:DomainEntity)
            WHERE n.expected_source IS NOT NULL
              AND n.expectation_origin <> 'EXPLICITLY_EXPECTED_BY_A_SOURCE'
            RETURN count(n)
            """,
        ),
        "externally_expected_without_a_source": _q.one(
            session,
            "MATCH (n:DomainEntity) WHERE n.externally_expected = true AND n.expected_source IS NULL RETURN count(n)",
        ),
    }

    out["GAP-ENTITY_COVERAGE-006"] = {
        "ayas_yv_cell": _q.one(
            session,
            "MATCH (m:Mantra {veda:'YV'})-[:MENTIONS_ENTITY]->(e) "
            "WHERE e.entity_key='VG:CONCEPT:AYAS-METAL' RETURN count(DISTINCT m)",
        ),
        "ayas_must_stay": 0,
        "recall_applicability_null": _q.one(
            session, "MATCH (n:DomainEntity) WHERE n.recall_applicability IS NULL RETURN count(n)"
        ),
        "applicability_distribution": _q.rows(
            session,
            "MATCH (n:DomainEntity) RETURN n.recall_applicability AS cls, count(*) AS c ORDER BY c DESC",
        ),
        "entities_with_a_measured_figure_and_a_sample_size": _q.one(
            session,
            "MATCH (n:DomainEntity) WHERE n.lexical_recall IS NOT NULL "
            "AND n.lexical_recall_sample_size IS NOT NULL RETURN count(n)",
        ),
    }

    out["GAP-ENTITY_COVERAGE-007"] = {
        "personification_status_null": _q.one(
            session,
            "MATCH (n:NaturalPhenomenon) WHERE n.personification_status IS NULL RETURN count(n)",
        ),
        "personification_match_basis_null": _q.one(
            session,
            "MATCH (n:NaturalPhenomenon) WHERE n.personification_match_basis IS NULL RETURN count(n)",
        ),
        "match_basis_distribution": _q.rows(
            session,
            "MATCH (n:NaturalPhenomenon) RETURN n.personification_match_basis AS basis, count(*) AS c ORDER BY c DESC",
        ),
        "phrase_mentions": _q.rows(
            session,
            """
            MATCH (p:Passage)-[r:MENTIONS_ENTITY]->(e:DomainEntity)
            WHERE r.method = 'domain-mention-v1:sanskrit-phrase'
            RETURN e.entity_key AS entity, count(*) AS c, collect(p.canonical_key)[0..8] AS sample
            ORDER BY c DESC
            """,
        ),
        "multiword_entities_now_reached": _q.rows(
            session,
            """
            UNWIND ['VG:CONCEPT:TRTIYA-SAVANA-THIRD-PRESSING',
                    'VG:CONCEPT:MADHYANDINA-SAVANA-MIDDAY-PRESSING'] AS k
            MATCH (e:DomainEntity {entity_key: k})
            RETURN k, size([(p:Passage)-[:MENTIONS_ENTITY]->(e)|1]) AS mentions,
                   e.aliases_sa_phrases AS phrases
            """,
        ),
    }

    out["GAP-RITUAL-003"] = {
        "uses_object": _q.one(session, "MATCH ()-[r:USES_OBJECT]->() RETURN count(r)"),
        "yupa": _q.rows(
            session,
            """
            MATCH (e:DomainEntity {entity_key:'VG:CONCEPT:YUPA-SACRIFICIAL-POST'})
            RETURN e.vedas_with_matches AS vedas_with_matches,
                   e.vedas_with_matches_list AS list,
                   e.mention_passages_measured AS passages,
                   size(e.aliases_sa) AS aliases
            """,
        ),
        "yupa_vsm_matched": _q.rows(
            session,
            """
            UNWIND ['VG:YV:VSM:A19:V017','VG:YV:VSM:A25:V029'] AS k
            OPTIONAL MATCH (p:Passage {canonical_key:k})-[:MENTIONS_ENTITY]->
                           (e:DomainEntity {entity_key:'VG:CONCEPT:YUPA-SACRIFICIAL-POST'})
            RETURN k, p IS NOT NULL AS matched
            """,
        ),
        "named_objects": _q.rows(
            session,
            """
            UNWIND ['VG:CONCEPT:MANI-AMULET','VG:CONCEPT:DUNDUBHI-DRUM','VG:CONCEPT:AUDUMBARA-AMULET'] AS k
            MATCH (e:DomainEntity {entity_key:k})
            RETURN k, e.ritual_use_status AS status, e.ritual_use_refusal_code AS refusal,
                   size([(r:Ritual)-[:USES_OBJECT]->(e)|1]) AS wired
            """,
        ),
        "objects_with_an_untyped_use_status": _q.one(
            session,
            """
            MATCH (e:DomainEntity) WHERE e.entity_key IN
              ['VG:CONCEPT:MANI-AMULET','VG:CONCEPT:DUNDUBHI-DRUM','VG:CONCEPT:AUDUMBARA-AMULET']
              AND e.ritual_use_status IS NULL RETURN count(e)
            """,
        ),
    }

    out["GAP-RITUAL-005"] = {
        "receives_offering": _q.one(session, "MATCH ()-[r:RECEIVES_OFFERING]->() RETURN count(r)"),
        "rites_total": _q.one(session, "MATCH (r:Ritual) RETURN count(r)"),
        "offering_status_null": _q.one(
            session, "MATCH (r:Ritual) WHERE r.offering_status IS NULL RETURN count(r)"
        ),
        "offering_status_distribution": _q.rows(
            session,
            "MATCH (r:Ritual) RETURN r.offering_status AS status, count(*) AS c ORDER BY c DESC",
        ),
        "probable_rows_imported": 0,
    }

    out["GAP-RITUAL-006"] = {
        "ritual_context_not_null": _q.one(
            session, "MATCH (m:Mantra) WHERE m.ritual_context IS NOT NULL RETURN count(m)"
        ),
        "method_null": _q.one(
            session, "MATCH (m:Mantra) WHERE m.ritual_context_method IS NULL RETURN count(m)"
        ),
        "precision_null": _q.one(
            session, "MATCH (m:Mantra) WHERE m.ritual_context_precision IS NULL RETURN count(m)"
        ),
        "precision_values": _q.rows(
            session,
            """
            MATCH (m:Mantra) WHERE m.ritual_context_precision IS NOT NULL
            RETURN m.ritual_context_precision AS reproducible_rows,
                   m.ritual_context_precision_all_reviewed_rows AS all_reviewed,
                   m.ritual_context_precision_review_level AS review_level,
                   m.ritual_context_precision_human_reviewed AS human_reviewed,
                   count(*) AS mantras LIMIT 3
            """,
        ),
        "metric_nodes": _q.rows(
            session,
            """
            MATCH (m:DerivedMetric)
            WHERE m.metric_name IN ['RITUAL_CONTEXT_PRECISION','MATERIAL_CULTURE_BY_RITUAL_CONTEXT']
            RETURN m.metric_id AS metric_id, m.values_json AS values_json,
                   m.is_human_gold AS is_human_gold, m.reference_set_class AS reference_set_class
            """,
        ),
    }

    out["GAP-SAMAVEDA_MUSIC-003"] = {
        "sv_running_number_null": _q.one(
            session,
            "MATCH (m:Mantra {veda:'SV'}) WHERE m.running_samhita_number IS NULL RETURN count(m)",
        ),
        "range": _q.rows(
            session,
            "MATCH (m:Mantra {veda:'SV'}) RETURN min(m.running_samhita_number) AS lo, "
            "max(m.running_samhita_number) AS hi, count(DISTINCT m.running_samhita_number) AS distinct",
        ),
        "musicalized_as": _q.one(session, "MATCH ()-[r:MUSICALIZED_AS]->() RETURN count(r)"),
        "gana_nodes": _q.one(
            session,
            "MATCH (n) WHERE n.work_id STARTS WITH 'VG:WORK:SV:KAU:GANA' "
            "OR n.canonical_key STARTS WITH 'VG:SV:KAU:GANA' RETURN count(n)",
        ),
    }

    out["GAP-QUALITY-003"] = {
        "predicates_with_a_constant_confidence": _q.rows(
            session,
            """
            MATCH ()-[r]->() WHERE r.confidence IS NOT NULL
            WITH type(r) AS t, collect(DISTINCT r.confidence) AS vals, count(r) AS c
            WHERE size(vals) = 1
            RETURN t, vals[0] AS value, c ORDER BY c DESC
            """,
        ),
        "edges_still_carrying_confidence": _q.one(
            session, "MATCH ()-[r]->() WHERE r.confidence IS NOT NULL RETURN count(r)"
        ),
        "tier_marker_edges": _q.rows(
            session,
            """
            MATCH ()-[r]->() WHERE r.source_explicit_tier_marker IS NOT NULL
            RETURN type(r) AS t, count(r) AS c ORDER BY c DESC
            """,
        ),
        "human_gold_claims_in_the_graph": _q.rows(
            session,
            """
            MATCH (n) WHERE n.is_human_gold = true OR n.human_gold_status = 'ANNOTATED'
            RETURN labels(n) AS labels, count(*) AS c
            """,
        ),
    }

    out["GAP-TRANSLATION-004"] = {
        "old_metric_rv_no_edge": _q.one(
            session,
            "MATCH (m:Mantra {veda:'RV'}) WHERE NOT (m)-[:HAS_TRANSLATION]->() RETURN count(m)",
        ),
        "coverage_state_null": _q.one(
            session, "MATCH (m:Mantra) WHERE m.translation_coverage_state IS NULL RETURN count(m)"
        ),
        "new_metric_rv_uncovered": _q.one(
            session,
            """
            MATCH (m:Mantra {veda:'RV'})
            WHERE m.translation_coverage_state IN
              ['UNCOVERED_REUSABLE_PARALLEL_AVAILABLE','UNCOVERED_NO_RENDERING_REACHES_IT']
            RETURN count(m)
            """,
        ),
        "distribution": _q.rows(
            session,
            """
            MATCH (m:Mantra)
            RETURN m.veda AS veda, m.translation_coverage_state AS state, count(*) AS c
            ORDER BY veda, c DESC
            """,
        ),
        "samaveda_independent_english": _q.one(
            session,
            """
            MATCH (m:Mantra {veda:'SV'})
            WHERE m.translation_coverage_state IN
              ['DEDICATED_TRANSLATION','RANGE_TRANSLATION_ANCHOR','RANGE_COVERED','CONTAINER_TRANSLATION']
            RETURN count(m)
            """,
        ),
    }

    out["GAP-PRODUCT_SURFACE-005"] = {
        "apparatus_still_in_the_graph": _q.rows(
            session,
            """
            MATCH (p:Passage)-[:HAS_TEXT_VERSION]->(t:TextVersion)
            WHERE p.canonical_key IN ['VG:SV:KAU:CHANDA:P01:D08:V04','VG:SV:KAU:ARANYA:D01:V04',
                                      'VG:SV:KAU:CHANDA:P04:D05:V06','VG:SV:KAU:CHANDA:P02:D07:V07']
            RETURN p.canonical_key AS key, t.text_role AS role,
                   left(t.text_nfc, 42) AS head, t.content_sha256 AS sha
            ORDER BY key, role
            """,
        ),
        "edges_with_a_recomputed_metric": _q.one(
            session,
            "MATCH ()-[r]->() WHERE r.cross_veda_metrics_recomputed_by IS NOT NULL RETURN count(r)",
        ),
        "edges_with_a_stale_transformation_marker": _q.one(
            session,
            "MATCH ()-[r]->() WHERE r.cross_veda_transformation_status = "
            "'STALE_RECOMPUTE_REQUIRED_TEXT_CORRECTED' RETURN count(r)",
        ),
    }
    return out


if __name__ == "__main__":
    result = _q.run(go)
    (HERE / "remeasured.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
