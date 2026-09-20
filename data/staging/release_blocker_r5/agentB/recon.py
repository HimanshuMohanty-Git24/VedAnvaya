from __future__ import annotations
import json, sys, pathlib, collections
sys.path.insert(0, str(pathlib.Path("data/staging/release_blocker_r5").resolve()))
from _q import driver, one, rows
sys.stdout.reconfigure(encoding="utf-8")
BK="data/staging/release_blocker_r5/backup"
lab=collections.Counter(); dm=set(); n=0
ident={"passage_keys":set(),"formula_ids":set(),"entity_keys":set(),"text_ids":set(),"assertion_keys":set(),"metric_ids":set()}
tv_by_id={}
with open(f"{BK}/nodes.jsonl",encoding="utf-8") as f:
    for line in f:
        n+=1; r=json.loads(line); p=r["props"]; L=r["labels"]
        for l in L: lab[l]+=1
        if "DerivedMetric" in L: dm.add(p.get("metric_id")); ident["metric_ids"].add(p.get("metric_id"))
        if "Passage" in L and p.get("canonical_key"): ident["passage_keys"].add(p["canonical_key"])
        if "Formula" in L and p.get("formula_id"): ident["formula_ids"].add(p["formula_id"])
        if "DomainEntity" in L and p.get("entity_key"): ident["entity_keys"].add(p["entity_key"])
        if "TextVersion" in L and p.get("text_id"):
            ident["text_ids"].add(p["text_id"])
        if "SemanticAssertion" in L and p.get("assertion_key"): ident["assertion_keys"].add(p["assertion_key"])
rt=collections.Counter(); rprops=collections.Counter(); m=0
conf_by_type=collections.Counter(); conf_vals=collections.defaultdict(collections.Counter)
with open(f"{BK}/relationships.jsonl",encoding="utf-8") as f:
    for line in f:
        m+=1; r=json.loads(line); rt[r["type"]]+=1
        c=r["props"].get("confidence")
        if c is not None:
            conf_by_type[r["type"]]+=1; conf_vals[r["type"]][c]+=1
out={"backup_nodes":n,"backup_rels":m,"backup_derivedmetric":len(dm)}
d=driver()
with d.session(database="neo4j") as s:
    live_lab={x["l"]:x["c"] for x in rows(s,"CALL db.labels() YIELD label CALL {WITH label MATCH (n) WHERE label IN labels(n) RETURN count(n) AS c} RETURN label AS l, c AS c")}
    live_rt={x["t"]:x["c"] for x in rows(s,"MATCH ()-[r]->() RETURN type(r) AS t, count(r) AS c")}
    out["label_delta"]={k:(lab.get(k,0),live_lab.get(k,0)) for k in set(lab)|set(live_lab) if lab.get(k,0)!=live_lab.get(k,0)}
    out["rel_type_delta"]={k:(rt.get(k,0),live_rt.get(k,0)) for k in set(rt)|set(live_rt) if rt.get(k,0)!=live_rt.get(k,0)}
    live_dm=set(x["i"] for x in rows(s,"MATCH (n:DerivedMetric) RETURN n.metric_id AS i"))
    out["dm_added"]=sorted(x for x in live_dm-dm if x is not None)
    out["dm_removed"]=sorted(x for x in dm-live_dm if x is not None)
    out["dm_null_metric_id_live"]=one(s,"MATCH (n:DerivedMetric) WHERE n.metric_id IS NULL RETURN count(n)")
    for name,q in [("passage_keys","MATCH (p:Passage) RETURN p.canonical_key AS v"),
                   ("formula_ids","MATCH (p:Formula) RETURN p.formula_id AS v"),
                   ("entity_keys","MATCH (p:DomainEntity) RETURN p.entity_key AS v"),
                   ("text_ids","MATCH (p:TextVersion) RETURN p.text_id AS v"),
                   ("assertion_keys","MATCH (p:SemanticAssertion) RETURN p.assertion_key AS v")]:
        lv=set(x["v"] for x in rows(s,q))
        out[f"{name}_added"]=sorted(x for x in lv-ident[name] if x is not None)[:20]
        out[f"{name}_removed"]=sorted(x for x in ident[name]-lv if x is not None)[:20]
        out[f"{name}_n_added"]=len(lv-ident[name]); out[f"{name}_n_removed"]=len(ident[name]-lv)
    # confidence: backup per type
    out["backup_confidence_by_type"]=dict(conf_by_type)
    out["backup_confidence_distinct_values"]={k:dict(v) for k,v in conf_vals.items() if len(v)<=3}
    live_conf={x["t"]:x["c"] for x in rows(s,"MATCH ()-[r]->() WHERE r.confidence IS NOT NULL RETURN type(r) AS t, count(r) AS c")}
    out["live_confidence_by_type"]=live_conf
    out["confidence_type_delta"]={k:(conf_by_type.get(k,0),live_conf.get(k,0)) for k in set(conf_by_type)|set(live_conf) if conf_by_type.get(k,0)!=live_conf.get(k,0)}
d.close()
pathlib.Path("data/staging/release_blocker_r5/agentB/recon.json").write_text(json.dumps(out,indent=2,ensure_ascii=False,default=str),encoding="utf-8")
print(json.dumps(out,indent=2,ensure_ascii=False,default=str)[:9000])
