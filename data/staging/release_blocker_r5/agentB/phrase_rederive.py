from __future__ import annotations
import json, sys, pathlib, collections
sys.path.insert(0, str(pathlib.Path("data/staging/release_blocker_r5").resolve()))
sys.path.insert(0, str(pathlib.Path("src").resolve()))
from _q import driver, rows
from vedagraph.enrich.surfaces import build_surfaces
from vedagraph.enrich.concepts import fold_alias
sys.stdout.reconfigure(encoding="utf-8")

PHRASES = {
 "VG:CONCEPT:TRTIYA-SAVANA-THIRD-PRESSING": ["tṛtīye savane","tṛtīye savana","tṛtīyaṃ savanaṃ","tṛtīyaṃ savanam"],
 "VG:CONCEPT:MADHYANDINA-SAVANA-MIDDAY-PRESSING": ["mādhyaṃdine savane","mādhyandine savana"],
}
folded = {k:[tuple(fold_alias(p) for p in ph.split()) for ph in v] for k,v in PHRASES.items()}
print("folded phrase token tuples:")
for k,v in folded.items():
    for ph,orig in zip(v,PHRASES[k]): print("  ",k,repr(orig),"->",ph)

d=driver()
with d.session(database="neo4j") as s:
    recs=rows(s,"""MATCH (m:Mantra)-[:HAS_TEXT_VERSION]->(t:TextVersion {text_role:'PRIMARY_TEXT'})
        RETURN m.canonical_key AS k, m.veda AS v, t.script AS sc, t.text_nfc AS txt""")
    live=rows(s,"""MATCH (m:Mantra)-[r:MENTIONS_ENTITY]->(e:DomainEntity)
        WHERE e.entity_key IN $ks RETURN m.canonical_key AS k, e.entity_key AS e,
        r.match_path AS path, r.paths AS paths, r.score AS score, r.matched_aliases AS ali,
        keys(r) AS rk ORDER BY e,k""", ks=list(PHRASES))
d.close()
print("primary text rows:",len(recs))
hits=collections.defaultdict(list)
for r in recs:
    su=build_surfaces(r["k"], r["v"], r["sc"] or "Devanagari", r["txt"] or "")
    toks=su.tokens
    for ek,plist in folded.items():
        for parts in plist:
            w=len(parts)
            for i in range(len(toks)-w+1):
                if tuple(toks[i:i+w])==parts:
                    hits[ek].append((r["k"]," ".join(parts)))
out={"independent_phrase_hits":{k:sorted(set(v)) for k,v in hits.items()},
     "counts":{k:len(set(v)) for k,v in hits.items()},
     "live_mentions_for_these_entities":live}
pathlib.Path("data/staging/release_blocker_r5/agentB/phrase_rederive.json").write_text(json.dumps(out,indent=2,ensure_ascii=False,default=str),encoding="utf-8")
print(json.dumps(out,indent=2,ensure_ascii=False,default=str))
