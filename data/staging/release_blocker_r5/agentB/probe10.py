from __future__ import annotations
import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path("data/staging/release_blocker_r5").resolve()))
sys.path.insert(0, str(pathlib.Path("src").resolve()))
from _q import driver, rows, one
from vedagraph.enrich.surfaces import build_surfaces
from vedagraph.enrich.crossveda import lcs_length
sys.stdout.reconfigure(encoding="utf-8")
d=driver()
with d.session(database="neo4j") as s:
    # apparatus substring anywhere in any relationship string property, scoped to rels touching SV corrected keys
    r1=rows(s,"""MATCH (a)-[r]-(b) WHERE a.canonical_key IN $keys OR b.canonical_key IN $keys
      WITH r, [k IN keys(r) WHERE r[k] IS NOT NULL AND toString(r[k]) =~ '(?s).*(draiḍ|dra iḍ|āraṇyakagānam|ārṣeyabrāhmaṇam|āraṇyakam |āraṇyakaga|draya |drāya|dra ya|dra abhi|draabhi|āraṇyakamabhi).*'] AS bad
      WHERE size(bad)>0 RETURN type(r) AS t, bad, count(*) AS c""",
      keys=['VG:SV:KAU:CHANDA:P01:D08:V04','VG:SV:KAU:ARANYA:D01:V04','VG:SV:KAU:CHANDA:P04:D05:V06','VG:SV:KAU:CHANDA:P02:D07:V07'])
    r2=rows(s,"""MATCH ()-[r]->() WHERE r.cross_veda_transformation_status IS NOT NULL
      RETURN type(r) AS t, r.formula_evidence AS fe, r.evidence AS ev, r.formula_difference_spans AS fds LIMIT 20""")
    # node-level scan on all TextVersion / Formula / Translation
    r3=one(s,"""MATCH (n) WHERE any(k IN keys(n) WHERE n[k] IS NOT NULL AND toString(n[k]) CONTAINS 'āraṇyakagānam') RETURN count(n)""")
    r4=rows(s,"""MATCH (n) WHERE any(k IN keys(n) WHERE n[k] IS NOT NULL AND toString(n[k]) CONTAINS 'āraṇyakagānam')
      RETURN labels(n) AS l, [k IN keys(n) WHERE toString(n[k]) CONTAINS 'āraṇyakagānam'] AS ks, n.canonical_key AS ck, n.text_id AS tid""")
    r5=rows(s,"""MATCH ()-[r]->() WHERE any(k IN keys(r) WHERE r[k] IS NOT NULL AND toString(r[k]) CONTAINS 'draiḍāmagne')
      RETURN type(r) AS t, [k IN keys(r) WHERE toString(r[k]) CONTAINS 'draiḍāmagne'] AS ks, count(*) AS c""")
    tv=rows(s,"""MATCH (p:Passage)-[:HAS_TEXT_VERSION]->(t:TextVersion {text_role:'PRIMARY_TEXT'})
      WHERE p.canonical_key IN ['VG:RV:SAK:M03:S001:V023','VG:SV:KAU:CHANDA:P01:D08:V04']
      RETURN p.canonical_key AS k, t.text_nfc AS txt, t.script AS sc""")
d.close()
print("rels touching the 4 with an apparatus-looking string:",json.dumps(r1,indent=1,ensure_ascii=False))
print("nodes containing 'āraṇyakagānam':",r3)
print(json.dumps(r4,indent=1,ensure_ascii=False))
print("rels containing 'draiḍāmagne':",json.dumps(r5,indent=1,ensure_ascii=False))
print("=== formula_evidence on the 13 ===")
seen=set()
for r in r2:
    fe=r['fe'] or ''
    flag='APPARATUS' if 'draiḍ' in fe or 'dra ' in fe[:400] else 'clean'
    key=(r['t'],flag,fe[:60])
    if key in seen: continue
    seen.add(key)
    print(" ",r['t'],flag)
    if fe: print("    formula_evidence:",fe[:300])
    if r['fds']: print("    formula_difference_spans:",str(r['fds'])[:220])
tx={r['k']:(r['txt'],r['sc']) for r in tv}
A=build_surfaces('a','X',tx['VG:RV:SAK:M03:S001:V023'][1] or 'Devanagari',tx['VG:RV:SAK:M03:S001:V023'][0])
B=build_surfaces('b','X',tx['VG:SV:KAU:CHANDA:P01:D08:V04'][1] or 'Devanagari',tx['VG:SV:KAU:CHANDA:P01:D08:V04'][0])
for name,x,y in [("sandhi_insensitive",A.sandhi_insensitive,B.sandhi_insensitive),("script_folded",A.script_folded,B.script_folded),("accent_insensitive",A.accent_insensitive,B.accent_insensitive)]:
    longest=max(len(x),len(y))
    print(f"  lcs_ratio on {name}: {lcs_length(x,y)/longest if longest else 0:.6f}")
