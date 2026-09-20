from __future__ import annotations
import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path("data/staging/release_blocker_r5").resolve()))
from _q import driver, one, rows
sys.stdout.reconfigure(encoding="utf-8")
o={}
d=driver()
with d.session(database="neo4j") as s:
    o['rc_by_class']=rows(s,"""MATCH (m:Mantra) RETURN m.ritual_context AS ctx,
      m.ritual_context_precision AS p, m.ritual_context_precision_all_reviewed_rows AS ar,
      m.ritual_context_precision_population AS pop, m.ritual_context_precision_sample_size AS n,
      m.ritual_context_precision_human_reviewed AS hr, m.ritual_context_precision_review_level AS rl,
      m.ritual_context_precision_metric_key AS mk, count(*) AS c
      ORDER BY c DESC""")
    o['precision_distinct']=rows(s,"MATCH (m:Mantra) RETURN DISTINCT m.ritual_context_precision AS p, m.ritual_context_precision_population AS pop, m.ritual_context_precision_sample_size AS n, m.ritual_context_precision_human_reviewed AS hr")
    # PRODUCT_SURFACE-005
    o['sv4']=rows(s,"""MATCH (p:Passage)-[:HAS_TEXT_VERSION]->(t:TextVersion)
      WHERE p.canonical_key IN ['VG:SV:KAU:CHANDA:P01:D08:V04','VG:SV:KAU:ARANYA:D01:V04','VG:SV:KAU:CHANDA:P04:D05:V06','VG:SV:KAU:CHANDA:P02:D07:V07']
      RETURN p.canonical_key AS k, t.text_role AS role, t.text_nfc AS txt, t.content_sha256 AS sha, t.text_original AS orig ORDER BY k, role""")
    o['apparatus_scan']=one(s,"""MATCH (t:TextVersion) WHERE t.text_nfc CONTAINS 'द्र. ' OR t.text_nfc STARTS WITH 'dra ' OR t.text_nfc STARTS WITH '(आरण्यक' OR t.text_nfc STARTS WITH 'आरण्यक' RETURN count(t)""")
    o['apparatus_scan_rows']=rows(s,"""MATCH (p:Passage)-[:HAS_TEXT_VERSION]->(t:TextVersion) WHERE t.text_nfc CONTAINS 'द्र.' OR t.text_nfc CONTAINS 'आरण्यक' OR t.text_nfc CONTAINS '(द्र' RETURN p.canonical_key AS k, t.text_role AS r, substring(t.text_nfc,0,60) AS head LIMIT 20""")
    o['parallel_edges']=rows(s,"""MATCH (a:Passage)-[r]->(b:Passage) WHERE r.cross_veda_transformation_status IS NOT NULL
      RETURN type(r) AS t, r.cross_veda_transformation_status AS st, count(r) AS c ORDER BY c DESC""")
    o['parallel_detail']=rows(s,"""MATCH (a:Passage)-[r]->(b:Passage) WHERE r.cross_veda_transformation_status IS NOT NULL
      RETURN a.canonical_key AS a, b.canonical_key AS b, type(r) AS t, r.cross_veda_transformation_status AS st,
      [x IN keys(r) WHERE x CONTAINS 'similar' OR x CONTAINS 'score' OR x CONTAINS 'transformation' OR x CONTAINS 'jaccard' OR x CONTAINS 'overlap'] AS ks LIMIT 20""")
d.close()
pathlib.Path("data/staging/release_blocker_r5/agentB/probe6.json").write_text(json.dumps(o,indent=2,ensure_ascii=False,default=str),encoding="utf-8")
print(json.dumps({k:v for k,v in o.items() if k!='sv4'},indent=2,ensure_ascii=False,default=str)[:6000])
print("=== SV4 ===")
for r in o['sv4']:
    print(" ",r['k'],'|',r['role'],'|',r['txt'][:70] if r['txt'] else None)
    print("     orig:",(r['orig'] or '')[:70])
