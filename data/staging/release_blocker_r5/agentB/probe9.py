from __future__ import annotations
import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path("data/staging/release_blocker_r5").resolve()))
from _q import driver, one, rows
sys.stdout.reconfigure(encoding="utf-8")
o={}
d=driver()
with d.session(database="neo4j") as s:
    # re-run the frozen disclosure query verbatim
    o['frozen_query_result']=rows(s,"""
        MATCH ()-[r]->()
        WHERE r.confidence IS NOT NULL
        WITH type(r) AS predicate, r.confidence AS value, count(*) AS edges
        WITH predicate, collect({value: value, edges: edges}) AS spread,
             sum(edges) AS predicate_total
        WITH predicate, predicate_total, spread,
             reduce(top = 0, s IN spread | CASE WHEN s.edges > top THEN s.edges ELSE top END)
               AS modal_edges
        RETURN predicate, predicate_total, size(spread) AS distinct_values,
               CASE WHEN size(spread) = 1 THEN 'SINGLE_CONSTANT'
                    WHEN modal_edges * 2 > predicate_total THEN 'MAJORITY_ONE_CONSTANT'
                    ELSE 'DISTRIBUTED' END AS guard_verdict
        ORDER BY predicate_total DESC""")
    o['total_conf_edges']=one(s,"MATCH ()-[r]->() WHERE r.confidence IS NOT NULL RETURN count(r)")
    o['at_1_0']=one(s,"MATCH ()-[r]->() WHERE r.confidence = 1.0 RETURN count(r)")
    o['value_clusters']=rows(s,"MATCH ()-[r]->() WHERE r.confidence IS NOT NULL RETURN r.confidence AS v, count(r) AS c ORDER BY c DESC LIMIT 6")
    o['human_gold_status']=rows(s,"MATCH (n:SemanticAssertion) RETURN n.human_gold_status AS v, count(n) AS c ORDER BY c DESC")
    o['review_state_sa']=rows(s,"MATCH (n:SemanticAssertion) RETURN n.review_state AS v, count(n) AS c ORDER BY c DESC LIMIT 5")
d.close()
print(json.dumps(o,indent=1,ensure_ascii=False,default=str))
