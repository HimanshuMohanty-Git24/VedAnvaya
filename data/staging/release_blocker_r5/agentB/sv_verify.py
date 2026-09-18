from __future__ import annotations
import json, sys, pathlib, re, collections
sys.path.insert(0, str(pathlib.Path("data/staging/release_blocker_r5").resolve()))
from _q import driver, one, rows
sys.stdout.reconfigure(encoding="utf-8")
CAN="data/canonical/samaveda_arcika_v1"
# 1. citations.jsonl running numbers
cit={}
kinds=collections.Counter()
for line in open(f"{CAN}/citations.jsonl",encoding="utf-8"):
    r=json.loads(line); kinds[r.get("system") or r.get("citation_system") or "?"]+=1
    sysname=r.get("system") or r.get("citation_system")
    if sysname=="WIKISOURCE_SA_RUNNING_SAMHITA_NUMBER":
        lab=r.get("label") or ""
        mm=re.match(r"^SV\s+(\d+)$",lab.strip())
        cit[r.get("passage_key") or r.get("canonical_key")]= int(mm.group(1)) if mm else ("BADLABEL:"+lab)
print("citation systems:",dict(kinds))
print("running-number citations:",len(cit))
# 2. text_versions source_locator RN
loc={}
for line in open(f"{CAN}/text_versions.jsonl",encoding="utf-8"):
    r=json.loads(line)
    sl=r.get("source_locator") or ""
    mm=re.search(r"RN(\d+)",sl)
    if mm: loc.setdefault(r.get("passage_key") or r.get("canonical_key"), int(mm.group(1)))
print("text_version RN locators:",len(loc))
# 3. qa_issues
qa=[]
for line in open(f"{CAN}/qa_issues.jsonl",encoding="utf-8"):
    qa.append(json.loads(line))
qrn=set()
for r in qa:
    v=(r.get("details") or {}).get("source_running_number")
    if v is not None:
        try: qrn.add(int(v))
        except: qrn.add(v)
print("qa_issues rows:",len(qa),"distinct source_running_number:",len(qrn))
print("qa kinds:",collections.Counter(r.get("issue_type") or r.get("kind") for r in qa))
# 4. graph
d=driver()
with d.session(database="neo4j") as s:
    g={x["k"]:x["n"] for x in rows(s,"MATCH (m:Mantra {veda:'SV'}) RETURN m.canonical_key AS k, m.running_samhita_number AS n")}
d.close()
print("graph SV mantras:",len(g))
# compare
mism=[(k,g.get(k),cit.get(k)) for k in g if g.get(k)!=cit.get(k)]
print("graph vs citations mismatches:",len(mism), mism[:10])
mism2=[(k,g.get(k),loc.get(k)) for k in g if g.get(k)!=loc.get(k)]
print("graph vs text_version RN mismatches:",len(mism2), mism2[:10])
mism3=[(k,cit.get(k),loc.get(k)) for k in cit if cit.get(k)!=loc.get(k)]
print("citations vs locator mismatches:",len(mism3), mism3[:10])
# 5. gaps 1..1875
have=set(g.values()); full=set(range(1,1876))
missing=sorted(full-have)
print("range gaps count:",len(missing))
print("missing numbers:",missing)
print("missing explained by qa_issues:",sorted(set(missing)&qrn))
print("missing NOT in qa_issues:",sorted(set(missing)-qrn))
print("qa numbers NOT missing:",sorted(qrn-set(missing)))
# 6. is it enumerate()? compare to canonical order index
order=[]
for line in open(f"{CAN}/passages.jsonl",encoding="utf-8"):
    r=json.loads(line)
    if (r.get("passage_type") or r.get("kind") or "")=="MANTRA" or r.get("level")=="MANTRA":
        order.append(r.get("canonical_key") or r.get("passage_key"))
print("passages.jsonl MANTRA rows:",len(order))
if len(order)==1844:
    enum_match=sum(1 for i,k in enumerate(order,1) if g.get(k)==i)
    print("rows where running_number == enumerate index:",enum_match,"of 1844")
