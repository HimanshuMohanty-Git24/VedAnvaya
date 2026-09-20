from __future__ import annotations
import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path("data/staging/release_blocker_r5").resolve()))
from _q import driver, one, rows
sys.stdout.reconfigure(encoding="utf-8")
o={}
d=driver()
with d.session(database="neo4j") as s:
    o['entity_mention_coverage']=rows(s,"MATCH (m:Mantra) OPTIONAL MATCH (m)-[:MENTIONS_ENTITY]->() WITH m.veda AS v, m, count(*) AS c WITH v, sum(CASE WHEN c>0 THEN 1 ELSE 0 END) AS covered, count(m) AS total RETURN v, covered, total, round(1.0*covered/total,4) AS share ORDER BY v")
    o['ritual_entity_density']=one(s,"MATCH (n:DerivedMetric) WHERE n.metric_name='RITUAL_ENTITY_DENSITY' RETURN count(n)")
    o['dm_by_name']=rows(s,"MATCH (n:DerivedMetric) RETURN n.metric_name AS n, count(*) AS c ORDER BY n")
    # personification
    o['natphen']=rows(s,"MATCH (n:NaturalPhenomenon) RETURN n.entity_key AS k, n.personification_status AS st, n.personification_match_basis AS basis, n.personification_evidence_contract AS contract, n.personification_contract AS pc, n.personification_evidence AS ev, n.personification_phrase AS ph, n.personification_passages AS ps ORDER BY k")
    o['natphen_keys']=rows(s,"MATCH (n:NaturalPhenomenon) RETURN n.entity_key AS k, [x IN keys(n) WHERE x STARTS WITH 'personification'] AS ks ORDER BY k")
    # RITUAL-003
    o['yupa']=rows(s,"MATCH (n:DomainEntity) WHERE n.entity_key CONTAINS 'YUPA' RETURN n.entity_key AS k, n.aliases_sa AS al, n.vedas_with_matches AS vwm, n.ritual_use_contract AS c")
    o['yupa_mentions']=rows(s,"MATCH (m:Mantra)-[:MENTIONS_ENTITY]->(e:DomainEntity) WHERE e.entity_key CONTAINS 'YUPA' RETURN m.veda AS v, collect(m.canonical_key) AS keys ORDER BY v")
    o['uses_object']=rows(s,"MATCH (a)-[r:USES_OBJECT]->(b) RETURN a.entity_key AS rite, b.entity_key AS obj, count(r) AS c ORDER BY rite,obj")
    o['named_objects']=rows(s,"MATCH (n:DomainEntity) WHERE n.entity_key IN ['VG:CONCEPT:MANI-AMULET','VG:CONCEPT:DUNDUBHI-DRUM','VG:CONCEPT:AUDUMBARA-AMULET'] RETURN n.entity_key AS k, n.ritual_use_status AS st, n.ritual_use_refusal AS rf, n.ritual_use_evidence AS ev, n.ritual_use_review_level AS rl, n.ritual_use_contract AS c, [x IN keys(n) WHERE x STARTS WITH 'ritual_use'] AS ks")
    # RITUAL-005
    o['offering']=rows(s,"MATCH (r:Ritual) RETURN r.offering_status AS st, r.offering_status_review_level AS rl, count(r) AS c ORDER BY c DESC")
    o['offering_keys']=rows(s,"MATCH (r:Ritual) WHERE r.offering_status='OFFERING_ASSERTED_FROM_SOURCE_EXPLICIT_EVIDENCE' RETURN r.entity_key AS k, r.offering_status_evidence AS ev, [x IN keys(r) WHERE x STARTS WITH 'offering'] AS ks")
    o['receives_offering']=rows(s,"MATCH (a)-[r:RECEIVES_OFFERING]->(b) RETURN a.entity_key AS a, b.entity_key AS b, r.evidence_basis AS eb, r.review_level AS rl")
    o['uses_offering']=one(s,"MATCH ()-[r:USES_OFFERING]->() RETURN count(r)")
    # RITUAL-006
    o['rc_precision']=rows(s,"MATCH (m:Mantra) RETURN DISTINCT m.ritual_context_precision AS p, m.ritual_context_precision_review_level AS rl, m.ritual_context_precision_all_reviewed AS ar, m.ritual_context_human_reviewed AS hr, m.ritual_context_method AS me LIMIT 10")
    o['rc_keys']=rows(s,"MATCH (m:Mantra) RETURN [x IN keys(m) WHERE x STARTS WITH 'ritual_context'] AS ks LIMIT 2")
    o['rc_dist']=rows(s,"MATCH (m:Mantra) RETURN m.ritual_context AS c, count(m) AS n ORDER BY n DESC")
d.close()
pathlib.Path("data/staging/release_blocker_r5/agentB/probe4.json").write_text(json.dumps(o,indent=2,ensure_ascii=False,default=str),encoding="utf-8")
print("ok")
