from __future__ import annotations
import json, sys, pathlib, os
sys.path.insert(0, str(pathlib.Path("data/staging/release_blocker_r5").resolve()))
from _q import driver, rows, one
sys.stdout.reconfigure(encoding="utf-8")
d=driver()
with d.session(database="neo4j") as s:
    print("origin_evidence NULL:",one(s,"MATCH (n:DomainEntity) WHERE n.expectation_origin_evidence IS NULL RETURN count(n)"))
    print("origin_evidence_quote NULL/empty:",one(s,"MATCH (n:DomainEntity) WHERE n.expectation_origin_evidence_quote IS NULL OR trim(n.expectation_origin_evidence_quote)='' RETURN count(n)"))
    print("internal_origin_file dist:")
    for r in rows(s,"MATCH (n:DomainEntity) RETURN n.expectation_internal_origin_file AS f, count(*) AS c ORDER BY c DESC"):
        p=(r['f'] or '').split('#')[0].strip()
        ok='' if not p else (' exists' if os.path.exists(p) else ' MISSING')
        print("   ",r['c'],r['f'],ok)
    print("evidence sample per origin:")
    for r in rows(s,"""MATCH (n:DomainEntity) WITH n.expectation_origin AS o, collect(n)[0] AS n
      RETURN o, n.entity_key AS k, n.expectation_origin_evidence AS ev, n.expectation_origin_evidence_quote AS q,
      n.expected_source AS src, n.expected_source_sense_review AS rev ORDER BY o"""):
        print("  --",r['o'],r['k'])
        print("     evidence:",str(r['ev'])[:200])
        print("     quote   :",str(r['q'])[:200])
        print("     src     :",str(r['src'])[:140])
        print("     review  :",str(r['rev'])[:160])
d.close()
