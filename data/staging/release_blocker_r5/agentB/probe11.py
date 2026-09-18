from __future__ import annotations
import json, sys, pathlib, os
sys.path.insert(0, str(pathlib.Path("data/staging/release_blocker_r5").resolve()))
from _q import driver, rows, one
sys.stdout.reconfigure(encoding="utf-8")
d=driver()
with d.session(database="neo4j") as s:
    a=rows(s,"""MATCH (n:DomainEntity) WHERE n.expectation_origin='EXPLICITLY_EXPECTED_BY_A_SOURCE'
      RETURN n.entity_key AS k, n.expected_source AS src, n.externally_expected AS ee,
      n.expectation_origin_file AS f, n.expectation_origin_quote AS q,
      [x IN keys(n) WHERE x STARTS WITH 'expect'] AS ks ORDER BY k LIMIT 4""")
    b=rows(s,"""MATCH (n:DomainEntity) WHERE n.expectation_origin='PRODUCT_EXPECTATION'
      RETURN n.entity_key AS k, n.expected_source AS src, n.externally_expected AS ee,
      n.expectation_origin_file AS f, n.expectation_origin_quote AS q ORDER BY k LIMIT 3""")
    c=one(s,"MATCH (n:DomainEntity) WHERE n.expectation_origin_file IS NULL RETURN count(n)")
    e=one(s,"MATCH (n:DomainEntity) WHERE n.expectation_origin_quote IS NULL OR trim(n.expectation_origin_quote)='' RETURN count(n)")
    f=rows(s,"MATCH (n:DomainEntity) RETURN DISTINCT n.expectation_origin_file AS f, count(*) AS c ORDER BY c DESC")
    g=one(s,"MATCH (n:DomainEntity) WHERE n.expectation_origin='EXPLICITLY_EXPECTED_BY_A_SOURCE' AND n.expected_source IS NULL RETURN count(n)")
    h=one(s,"MATCH (n:DomainEntity) WHERE n.expectation_origin<>'EXPLICITLY_EXPECTED_BY_A_SOURCE' AND n.expected_source IS NOT NULL RETURN count(n)")
    # recall_applicability measured figures
    i=rows(s,"MATCH (n:DomainEntity) WHERE n.recall_applicability='LEXICAL_RECOVERY_APPLICABLE' RETURN count(n) AS n_applicable, sum(CASE WHEN n.lexical_recall IS NOT NULL THEN 1 ELSE 0 END) AS with_figure, sum(CASE WHEN n.lexical_recall_sample_size IS NOT NULL THEN 1 ELSE 0 END) AS with_n")
    j=rows(s,"MATCH (n:DomainEntity) WHERE n.entity_key='VG:CONCEPT:AYAS-METAL' RETURN n.recall_applicability AS ra, n.aliases_sa AS al, n.lexical_recall AS lr, [x IN keys(n) WHERE x CONTAINS 'recall' OR x CONTAINS 'ayas' OR x CONTAINS 'attest'] AS ks")
d.close()
print("class-A sample:"); [print("  ",r['k'],"| src=",str(r['src'])[:70],"| ee=",r['ee'],"| file=",str(r['f'])[:60]) for r in a]
print("   first quote:",str(a[0]['q'])[:220] if a else None)
print("   keys:",a[0]['ks'] if a else None)
print("PRODUCT_EXPECTATION sample:"); [print("  ",r['k'],"| src=",r['src'],"| ee=",r['ee'],"| file=",str(r['f'])[:60],"| q=",str(r['q'])[:90]) for r in b]
print("origin_file NULL:",c," origin_quote empty/NULL:",e)
print("files:"); [print("   ",r['c'],r['f']) for r in f]
print("class-A without expected_source:",g," non-class-A WITH expected_source:",h)
print("applicable/with figure/with n:",i)
print("ayas:",json.dumps(j,ensure_ascii=False))
# do the named files exist?
for r in f:
    p=(r['f'] or '').split('#')[0].strip()
    if p: print("   exists" if os.path.exists(p) else "   MISSING", p)
