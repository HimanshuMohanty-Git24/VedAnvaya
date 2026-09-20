from __future__ import annotations
import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path("data/staging/release_blocker_r5").resolve()))
from _q import driver, rows
sys.stdout.reconfigure(encoding="utf-8")
d=driver()
with d.session(database="neo4j") as s:
    r=rows(s,"""MATCH (a:Passage {canonical_key:'VG:RV:SAK:M03:S001:V023'})-[r]->(b:Passage {canonical_key:'VG:SV:KAU:CHANDA:P01:D08:V04'})
      RETURN type(r) AS t, properties(r) AS p""")
    r2=rows(s,"""MATCH (a:Passage)-[r:REUSES_TEXT_FROM]->(b:Passage) WHERE r.cross_veda_transformation_status IS NOT NULL
      RETURN a.canonical_key AS a,b.canonical_key AS b, properties(r) AS p LIMIT 1""")
d.close()
print(json.dumps(r,indent=1,ensure_ascii=False,default=str))
print("=== REUSES_TEXT_FROM ===")
print(json.dumps(r2,indent=1,ensure_ascii=False,default=str))
