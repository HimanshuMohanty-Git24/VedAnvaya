from __future__ import annotations
import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path("data/staging/release_blocker_r5").resolve()))
sys.path.insert(0, str(pathlib.Path("src").resolve()))
from _q import driver, rows
from vedagraph.enrich.surfaces import build_surfaces
from vedagraph.enrich.crossveda import score_pair
sys.stdout.reconfigure(encoding="utf-8")
d=driver()
with d.session(database="neo4j") as s:
    edges=rows(s,"""MATCH (a:Passage)-[r]->(b:Passage) WHERE r.cross_veda_transformation_status IS NOT NULL
      RETURN a.canonical_key AS ak, b.canonical_key AS bk, type(r) AS t,
      r.similarity AS similarity, r.score AS score, r.token_jaccard AS tj, r.ngram_jaccard AS nj,
      r.lcs_ratio AS lcs, r.edit_ratio AS er, r.cross_veda_stored_similarity AS stored,
      r.cross_veda_lcs_ratio_rederived AS lcs_red ORDER BY ak,bk""")
    tv=rows(s,"""MATCH (p:Passage)-[:HAS_TEXT_VERSION]->(t:TextVersion {text_role:'PRIMARY_TEXT'})
      RETURN p.canonical_key AS k, t.text_nfc AS txt, t.script AS sc""")
d.close()
tx={r["k"]:(r["txt"],r["sc"]) for r in tv}
print(f"{'pair':70} {'stored_sim':>10} {'recomp_sim':>10} {'stored_lcs':>10} {'recomp_lcs':>10} {'red_field':>10} {'stored_tj':>9} {'recomp_tj':>9} {'stored_nj':>9} {'recomp_nj':>9}")
bad=0
for e in edges:
    at,asc=tx.get(e["ak"],(None,None)); bt,bsc=tx.get(e["bk"],(None,None))
    if at is None or bt is None:
        print("MISSING TEXT",e["ak"],e["bk"]); continue
    A=build_surfaces(e["ak"],"X",asc or "Devanagari",at)
    B=build_surfaces(e["bk"],"X",bsc or "Devanagari",bt)
    ps=score_pair(A,B)
    def f(x): return "None" if x is None else f"{x:.6f}"
    print(f'{e["ak"]+" -> "+e["bk"]:70} {f(e["similarity"]):>10} {f(ps.similarity):>10} {f(e["lcs"]):>10} {f(ps.lcs_ratio):>10} {f(e["lcs_red"]):>10} {f(e["tj"]):>9} {f(ps.token_jaccard):>9} {f(e["nj"]):>9} {f(ps.ngram_jaccard):>9}')
    for name,stored,rec in [("similarity",e["similarity"],ps.similarity),("lcs_ratio",e["lcs"],ps.lcs_ratio),
                            ("token_jaccard",e["tj"],ps.token_jaccard),("ngram_jaccard",e["nj"],ps.ngram_jaccard),
                            ("edit_ratio",e["er"],ps.edit_ratio)]:
        if stored is not None and abs(stored-rec)>1e-6:
            bad+=1
print()
print("stored-vs-recomputed metric disagreements:",bad)
