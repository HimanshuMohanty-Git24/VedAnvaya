from __future__ import annotations
import json, sys, pathlib, hashlib, unicodedata
sys.path.insert(0, str(pathlib.Path("data/staging/release_blocker_r5").resolve()))
from _q import driver, one, rows
sys.stdout.reconfigure(encoding="utf-8")
o={}
d=driver()
with d.session(database="neo4j") as s:
    # how many TextVersions carry apparatus in text_original?
    o['orig_apparatus']=rows(s,"""MATCH (p:Passage)-[:HAS_TEXT_VERSION]->(t:TextVersion)
      WHERE t.text_original IS NOT NULL AND (t.text_original STARTS WITH 'dra ' OR t.text_original STARTS WITH 'āraṇyaka' OR t.text_original STARTS WITH 'araṇyaka' OR t.text_original CONTAINS 'ārṣeyabrāhmaṇam')
      RETURN p.canonical_key AS k, t.text_role AS r, substring(t.text_original,0,70) AS head ORDER BY k,r""")
    o['orig_vs_nfc_mismatch_sv']=one(s,"""MATCH (m:Mantra {veda:'SV'})-[:HAS_TEXT_VERSION]->(t:TextVersion {text_role:'SEARCH_DERIVATIVE'})
      WHERE t.text_original <> t.text_nfc RETURN count(t)""")
    o['sv_deriv_sample']=rows(s,"""MATCH (m:Mantra {veda:'SV'})-[:HAS_TEXT_VERSION]->(t:TextVersion {text_role:'SEARCH_DERIVATIVE'})
      WHERE NOT m.canonical_key IN ['VG:SV:KAU:CHANDA:P01:D08:V04','VG:SV:KAU:ARANYA:D01:V04','VG:SV:KAU:CHANDA:P04:D05:V06','VG:SV:KAU:CHANDA:P02:D07:V07']
      RETURN m.canonical_key AS k, substring(t.text_nfc,0,50) AS nfc, substring(t.text_original,0,50) AS orig, t.text_nfc = t.text_original AS same LIMIT 5""")
    o['sv_deriv_same_count']=rows(s,"""MATCH (m:Mantra {veda:'SV'})-[:HAS_TEXT_VERSION]->(t:TextVersion {text_role:'SEARCH_DERIVATIVE'})
      RETURN t.text_nfc = t.text_original AS same, count(t) AS c""")
    o['sha_check']=rows(s,"""MATCH (p:Passage)-[:HAS_TEXT_VERSION]->(t:TextVersion)
      WHERE p.canonical_key IN ['VG:SV:KAU:CHANDA:P01:D08:V04','VG:SV:KAU:ARANYA:D01:V04','VG:SV:KAU:CHANDA:P04:D05:V06','VG:SV:KAU:CHANDA:P02:D07:V07']
      RETURN p.canonical_key AS k, t.text_role AS r, t.text_nfc AS nfc, t.content_sha256 AS sha, t.text_original AS orig ORDER BY k,r""")
    o['parallel_values']=rows(s,"""MATCH (a:Passage)-[r]->(b:Passage) WHERE r.cross_veda_transformation_status IS NOT NULL
      RETURN a.canonical_key AS a, b.canonical_key AS b, type(r) AS t,
      r.similarity AS similarity, r.score AS score, r.token_jaccard AS tj, r.ngram_jaccard AS nj,
      r.cross_veda_stored_similarity AS stored, r.cross_veda_transformation AS transf,
      r.cross_veda_transformation_uncorrected AS uncorr, r.cross_veda_transformation_superseded AS sup,
      r.cross_veda_transformation_basis AS basis, r.cross_veda_transformation_stale_reason AS reason,
      r.cross_veda_transformation_scope AS scope ORDER BY a,b""")
d.close()
pathlib.Path("data/staging/release_blocker_r5/agentB/probe7.json").write_text(json.dumps(o,indent=2,ensure_ascii=False,default=str),encoding="utf-8")
print("orig_apparatus rows:",len(o['orig_apparatus']))
for r in o['orig_apparatus']: print("  ",r['k'],'|',r['r'],'|',r['head'][:70])
print("SV derivative text_original != text_nfc:",o['orig_vs_nfc_mismatch_sv'])
print("SV derivative same counts:",o['sv_deriv_same_count'])
print("sample:",json.dumps(o['sv_deriv_sample'],ensure_ascii=False,indent=1)[:1200])
print("=== sha check ===")
for r in o['sha_check']:
    nfc=r['nfc'] or ''
    h=hashlib.sha256(unicodedata.normalize('NFC',nfc).encode('utf-8')).hexdigest()
    print("  ",r['k'],r['r'],"stored=",r['sha'][:16],"sha256(text_nfc)=",h[:16],"MATCH" if h==r['sha'] else "DIFFER")
print("=== parallel values ===")
for r in o['parallel_values']:
    print("  ",r['a'],'->',r['b'],r['t'])
    print("     similarity=",r['similarity'],"score=",r['score'],"tj=",r['tj'],"nj=",r['nj'])
    print("     stored=",r['stored'],"transf=",r['transf'],"uncorr=",r['uncorr'],"sup=",r['sup'])
    print("     basis=",str(r['basis'])[:150])
    print("     reason=",str(r['reason'])[:200])
    print("     scope=",str(r['scope'])[:120])
