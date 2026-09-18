from __future__ import annotations
import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path("data/staging/release_blocker_r5").resolve()))
from _q import driver, one, rows
o={}
d=driver()
with d.session(database="neo4j") as s:
    keys=[r['propertyKey'] for r in rows(s,"CALL db.propertyKeys() YIELD propertyKey RETURN propertyKey ORDER BY propertyKey")]
    o['propertyKeys_count']=len(keys)
    o['keys_with_r5']=[k for k in keys if 'r5' in k.lower()]
    o['keys_with_contract']=[k for k in keys if 'contract' in k.lower()]
    o['new_ish_keys']=[k for k in keys if k in ('expectation_origin','expected_source','externally_expected','recall_applicability','personification_match_basis','personification_status','offering_status','ritual_context_precision','ritual_context_precision_review_level','translation_coverage_state','running_samhita_number','calibration_status','source_explicit_tier_marker','uncalibrated_pipeline_score','vedas_with_matches','cross_veda_transformation_status')]
    # DerivedMetric census
    o['derived_metric_total']=one(s,"MATCH (n:DerivedMetric) RETURN count(n)")
    o['derived_metric_r5']=rows(s,"MATCH (n:DerivedMetric) WHERE any(k IN keys(n) WHERE k CONTAINS 'r5') RETURN n.metric_id AS id, keys(n) AS ks LIMIT 50")
    o['dm_recent']=rows(s,"MATCH (n:DerivedMetric) WHERE n.computed_at IS NOT NULL AND n.computed_at >= '2026-09-18' RETURN n.metric_id AS id, n.computed_at AS at, n.layer_id AS layer ORDER BY at")
    o['dm_keys_sample']=rows(s,"MATCH (n:DerivedMetric) RETURN keys(n) AS ks LIMIT 3")
    # nodes with r5-ish marker props anywhere
    o['nodes_with_any_r5_key']=one(s,"MATCH (n) WHERE any(k IN keys(n) WHERE k CONTAINS 'r5' OR k CONTAINS 'R5') RETURN count(n)")
    o['labels_with_r5_key']=rows(s,"MATCH (n) WHERE any(k IN keys(n) WHERE toLower(k) CONTAINS 'r5') RETURN labels(n) AS l, count(*) AS c")
    # SEMANTICS-003
    o['sem003']={
      'assertion_agent':one(s,"MATCH ()-[r:ASSERTION_AGENT]->() RETURN count(r)"),
      'assertion_target':one(s,"MATCH ()-[r:ASSERTION_TARGET]->() RETURN count(r)"),
      'agent_nondevata':one(s,"MATCH (a:SemanticAssertion)-[:ASSERTION_AGENT]->(x) WHERE NOT x:Devata RETURN count(*)"),
      'target_nondevata':one(s,"MATCH (a:SemanticAssertion)-[:ASSERTION_TARGET]->(x) WHERE NOT x:Devata RETURN count(*)"),
      'all_three':one(s,"MATCH (a:SemanticAssertion) WHERE (a)-[:ASSERTION_AGENT]->() AND (a)-[:ASSERTION_TARGET]->() AND a.predicate IS NOT NULL RETURN count(a)"),
      'agent_edge_props':rows(s,"MATCH ()-[r:ASSERTION_AGENT]->() RETURN r.derivation AS deriv, r.tier AS tier, r.evidence_basis AS eb, count(r) AS c ORDER BY c DESC"),
      'target_edge_props':rows(s,"MATCH ()-[r:ASSERTION_TARGET]->() RETURN r.derivation AS deriv, r.tier AS tier, count(r) AS c ORDER BY c DESC"),
      'dup_agent':one(s,"MATCH (a:SemanticAssertion)-[r:ASSERTION_AGENT]->(x) WITH a,x,count(r) AS c WHERE c>1 RETURN count(*)"),
      'assertions_with_2plus_agents':one(s,"MATCH (a:SemanticAssertion)-[:ASSERTION_AGENT]->(x) WITH a, count(DISTINCT x) AS c WHERE c>1 RETURN count(a)"),
      'rolefiller_refers_to':one(s,"MATCH (:RoleFiller)-[r:REFERS_TO]->() RETURN count(r)"),
      'rf_refers_nondevata':one(s,"MATCH (:RoleFiller)-[:REFERS_TO]->(x) WHERE NOT x:Devata RETURN count(*)"),
    }
    # QUALITY-003
o=o
d.close()
pathlib.Path("data/staging/release_blocker_r5/agentB/probe2.json").write_text(json.dumps(o,indent=2,ensure_ascii=False,default=str),encoding='utf-8')
print("ok")
