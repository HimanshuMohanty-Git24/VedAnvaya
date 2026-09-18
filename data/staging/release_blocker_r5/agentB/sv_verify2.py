from __future__ import annotations
import json, sys, pathlib, re
sys.path.insert(0, str(pathlib.Path("data/staging/release_blocker_r5").resolve()))
from _q import driver, rows
sys.stdout.reconfigure(encoding="utf-8")
CAN="data/canonical/samaveda_arcika_v1"
pid2key={}
for line in open(f"{CAN}/passages.jsonl",encoding="utf-8"):
    r=json.loads(line); pid2key[r["entity_id"]]=r["canonical_key"]
cit={}
for line in open(f"{CAN}/citations.jsonl",encoding="utf-8"):
    r=json.loads(line)
    if r["system"]=="WIKISOURCE_SA_RUNNING_SAMHITA_NUMBER":
        m=re.match(r"^SV\s+(\d+)$",r["label"].strip())
        cit[pid2key.get(r["passage_id"])] = int(m.group(1)) if m else "BAD:"+r["label"]
loc={}
for line in open(f"{CAN}/text_versions.jsonl",encoding="utf-8"):
    r=json.loads(line)
    if r.get("text_role")=="PRIMARY_TEXT":
        m=re.search(r"RN(\d+)",r.get("source_locator") or "")
        if m: loc[pid2key.get(r["passage_id"])]=int(m.group(1))
print("cit rows:",len(cit),"loc rows:",len(loc))
d=driver()
with d.session(database="neo4j") as s:
    g={x["k"]:x["n"] for x in rows(s,"MATCH (m:Mantra {veda:'SV'}) RETURN m.canonical_key AS k, m.running_samhita_number AS n")}
d.close()
a=[(k,g[k],cit.get(k)) for k in g if g[k]!=cit.get(k)]
b=[(k,g[k],loc.get(k)) for k in g if g[k]!=loc.get(k)]
c=[(k,cit[k],loc.get(k)) for k in cit if cit[k]!=loc.get(k)]
print("graph vs citations mismatches:",len(a),a[:5])
print("graph vs PRIMARY_TEXT locator mismatches:",len(b),b[:5])
print("citations vs locator mismatches:",len(c),c[:5])
print("graph keys not in citations:",len([k for k in g if k not in cit]))
