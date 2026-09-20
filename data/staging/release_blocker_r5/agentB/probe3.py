from __future__ import annotations
import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path("data/staging/release_blocker_r5").resolve()))
from _q import driver, one, rows
sys.stdout.reconfigure(encoding="utf-8")
o={}
d=driver()
with d.session(database="neo4j") as s:
    # ---- QUALITY-003 ----
    q={}
    q['conf_edges']=one(s,"MATCH ()-[r]->() WHERE r.confidence IS NOT NULL RETURN count(r)")
    q['conf_without_calibration_status']=one(s,"MATCH ()-[r]->() WHERE r.confidence IS NOT NULL AND r.calibration_status IS NULL RETURN count(r)")
    q['calibration_status_dist']=rows(s,"MATCH ()-[r]->() WHERE r.calibration_status IS NOT NULL RETURN r.calibration_status AS v, type(r) AS t, count(r) AS c ORDER BY c DESC")
    q['per_type_conf_profile']=rows(s,"""MATCH ()-[r]->() WHERE r.confidence IS NOT NULL
        RETURN type(r) AS t, count(r) AS n, count(DISTINCT r.confidence) AS distinct_vals,
               min(r.confidence) AS mn, max(r.confidence) AS mx ORDER BY t""")
    q['type_total_vs_conf']=rows(s,"""MATCH ()-[r]->() WITH type(r) AS t, count(r) AS total,
        sum(CASE WHEN r.confidence IS NOT NULL THEN 1 ELSE 0 END) AS withconf
        WHERE withconf>0 RETURN t, total, withconf ORDER BY t""")
    q['tier_marker']=rows(s,"MATCH ()-[r]->() WHERE r.source_explicit_tier_marker IS NOT NULL RETURN type(r) AS t, count(r) AS c, collect(DISTINCT r.source_explicit_tier_marker)[0..5] AS vals ORDER BY c DESC")
    q['tier_marker_total']=one(s,"MATCH ()-[r]->() WHERE r.source_explicit_tier_marker IS NOT NULL RETURN count(r)")
    q['tier_marker_and_confidence_both']=one(s,"MATCH ()-[r]->() WHERE r.source_explicit_tier_marker IS NOT NULL AND r.confidence IS NOT NULL RETURN count(r)")
    q['uncal']=rows(s,"MATCH ()-[r]->() WHERE r.uncalibrated_pipeline_score IS NOT NULL RETURN type(r) AS t, r.uncalibrated_pipeline_score AS v, count(r) AS c")
    q['human_gold_nodes']=one(s,"MATCH (n) WHERE n.is_human_gold = true RETURN count(n)")
    q['human_gold_any']=rows(s,"MATCH (n) WHERE n.is_human_gold IS NOT NULL RETURN n.is_human_gold AS v, count(n) AS c")
    q['reference_set_class']=rows(s,"MATCH (n) WHERE n.reference_set_class IS NOT NULL RETURN n.reference_set_class AS v, count(n) AS c")
    o['QUALITY_003']=q
    # ---- TRANSLATION-004 ----
    t={}
    t['state_null']=one(s,"MATCH (m:Mantra) WHERE m.translation_coverage_state IS NULL RETURN count(m)")
    t['dist']=rows(s,"MATCH (m:Mantra) RETURN m.veda AS v, m.translation_coverage_state AS st, count(m) AS c ORDER BY v, c DESC")
    t['rv_no_edge']=one(s,"MATCH (m:Mantra {veda:'RV'}) WHERE NOT (m)-[:HAS_TRANSLATION]->() RETURN count(m)")
    t['rv_no_edge_keys']=rows(s,"MATCH (m:Mantra {veda:'RV'}) WHERE NOT (m)-[:HAS_TRANSLATION]->() RETURN m.canonical_key AS k, m.translation_coverage_state AS st ORDER BY k")
    t['rv_uncovered']=rows(s,"MATCH (m:Mantra {veda:'RV'}) WHERE m.translation_coverage_state='UNCOVERED_NO_RENDERING_REACHES_IT' RETURN m.canonical_key AS k ORDER BY k")
    t['sv_independent_english']=one(s,"""MATCH (m:Mantra {veda:'SV'})-[:HAS_TRANSLATION]->(tr:Translation) RETURN count(tr)""")
    t['sv_translation_edges']=one(s,"MATCH (m:Mantra {veda:'SV'})-[r:HAS_TRANSLATION]->() RETURN count(r)")
    t['sv_reused']=one(s,"MATCH (m:Mantra {veda:'SV'}) WHERE m.translation_coverage_state='REUSED_RENDERING' RETURN count(m)")
    t['m165_170']=rows(s,"""MATCH (m:Mantra {veda:'RV'}) WHERE m.canonical_key =~ 'VG:RV:SAK:M01:S0(6[5-9]|70):V.*'
        OPTIONAL MATCH (m)-[:HAS_TRANSLATION]->(tr:Translation)
        RETURN m.canonical_key AS k, m.translation_coverage_state AS st, count(tr) AS edges ORDER BY k""")
    o['TRANSLATION_004']=t
    # ---- SAMAVEDA_MUSIC-003 ----
    sm={}
    sm['null']=one(s,"MATCH (m:Mantra {veda:'SV'}) WHERE m.running_samhita_number IS NULL RETURN count(m)")
    sm['range']=rows(s,"MATCH (m:Mantra {veda:'SV'}) RETURN min(m.running_samhita_number) AS lo, max(m.running_samhita_number) AS hi, count(DISTINCT m.running_samhita_number) AS distinct")
    sm['contract']=rows(s,"MATCH (m:Mantra {veda:'SV'}) RETURN DISTINCT m.running_samhita_number_contract AS c LIMIT 5")
    sm['first20']=rows(s,"MATCH (m:Mantra {veda:'SV'}) RETURN m.canonical_key AS k, m.running_samhita_number AS n ORDER BY n LIMIT 20")
    sm['musicalized']=one(s,"MATCH ()-[r]->() WHERE type(r)='MUSICALIZED_AS' RETURN count(r)")
    o['SAMAVEDA_MUSIC_003']=sm
d.close()
pathlib.Path("data/staging/release_blocker_r5/agentB/probe3.json").write_text(json.dumps(o,indent=2,ensure_ascii=False,default=str),encoding="utf-8")
print("ok")
