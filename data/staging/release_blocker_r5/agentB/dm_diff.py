from __future__ import annotations
import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path("data/staging/release_blocker_r5").resolve()))
from _q import driver, one, rows
sys.stdout.reconfigure(encoding="utf-8")
back=set(); nlab={}; nodes=0
with open("data/staging/release_blocker_r5/backup/nodes.jsonl", encoding="utf-8") as f:
    for line in f:
        nodes+=1
        r=json.loads(line)
        labs=r.get("labels") or []
        if "DerivedMetric" in labs:
            back.add(r.get("properties",{}).get("metric_id"))
print("backup node lines:", nodes, "backup DerivedMetric:", len(back))
d=driver()
with d.session(database="neo4j") as s:
    live=set(x["i"] for x in rows(s,"MATCH (n:DerivedMetric) RETURN n.metric_id AS i"))
    print("live DerivedMetric:", len(live))
    added=sorted(x for x in live-back if x is not None)
    removed=sorted(x for x in back-live if x is not None)
    print("ADDED:", json.dumps(added,indent=1,ensure_ascii=False))
    print("REMOVED:", json.dumps(removed,indent=1,ensure_ascii=False))
    for a in added:
        print("---", a)
        print(json.dumps(rows(s,"MATCH (n:DerivedMetric {metric_id:$i}) RETURN properties(n) AS p",i=a),indent=1,ensure_ascii=False)[:2500])
d.close()
