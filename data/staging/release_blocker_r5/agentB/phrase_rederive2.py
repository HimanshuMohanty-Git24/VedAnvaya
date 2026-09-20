from __future__ import annotations
import json, sys, pathlib, collections
sys.path.insert(0, str(pathlib.Path("data/staging/release_blocker_r5").resolve()))
sys.path.insert(0, str(pathlib.Path("src").resolve()))
from _q import driver, rows, one
from vedagraph.enrich.surfaces import build_surfaces
from vedagraph.enrich.concepts import fold_alias
sys.stdout.reconfigure(encoding="utf-8")
PHRASES = {
 "VG:CONCEPT:TRTIYA-SAVANA-THIRD-PRESSING": ["tṛtīye savane","tṛtīye savana","tṛtīyaṃ savanaṃ","tṛtīyaṃ savanam"],
 "VG:CONCEPT:MADHYANDINA-SAVANA-MIDDAY-PRESSING": ["mādhyaṃdine savane","mādhyandine savana"],
}
folded = {k:[tuple(fold_alias(p) for p in ph.split()) for ph in v] for k,v in PHRASES.items()}
d=driver()
with d.session(database="neo4j") as s:
    print("text_role dist:", rows(s,"MATCH (m:Mantra)-[:HAS_TEXT_VERSION]->(t:TextVersion) RETURN m.veda AS v, t.text_role AS r, count(*) AS c ORDER BY v,r"))
    recs=rows(s,"""MATCH (m:Mantra)-[:HAS_TEXT_VERSION]->(t:TextVersion)
        WHERE t.text_role <> 'SEARCH_DERIVATIVE'
        RETURN m.canonical_key AS k, m.veda AS v, t.script AS sc, t.text_nfc AS txt, t.text_role AS role""")
    live=rows(s,"""MATCH (m:Mantra)-[r:MENTIONS_ENTITY]->(e:DomainEntity)
        WHERE e.entity_key IN $ks RETURN m.canonical_key AS k, e.entity_key AS e,
        r.method AS method, r.score AS score, r.matched_aliases AS ali, r.evidence AS ev ORDER BY e,k""", ks=list(PHRASES))
d.close()
print("text version rows scanned:",len(recs), "distinct mantras:", len({r['k'] for r in recs}))
hits=collections.defaultdict(set)
for r in recs:
    su=build_surfaces(r["k"], r["v"], r["sc"] or "Devanagari", r["txt"] or "")
    toks=su.tokens
    for ek,plist in folded.items():
        for parts in plist:
            w=len(parts)
            for i in range(len(toks)-w+1):
                if tuple(toks[i:i+w])==parts:
                    hits[ek].add((r["k"], r["role"]))
out={"counts":{k:len({x[0] for x in v}) for k,v in hits.items()},
     "hits":{k:sorted(v) for k,v in hits.items()},
     "live":live}
pathlib.Path("data/staging/release_blocker_r5/agentB/phrase_rederive2.json").write_text(json.dumps(out,indent=2,ensure_ascii=False,default=str),encoding="utf-8")
print(json.dumps({"counts":out["counts"],"hits":out["hits"]},indent=2,ensure_ascii=False))
print("--- LIVE MENTIONS ---")
for r in live: print(" ",r["e"].split(":")[-1][:22], r["k"], "score=",r["score"], "ali=",r["ali"], "method=",str(r["method"])[:60])
