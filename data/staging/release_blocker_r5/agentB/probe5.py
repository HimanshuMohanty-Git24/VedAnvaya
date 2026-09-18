from __future__ import annotations
import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path("data/staging/release_blocker_r5").resolve()))
sys.path.insert(0, str(pathlib.Path("src").resolve()))
from _q import driver, one, rows
from vedagraph.enrich.concepts import fold_alias
sys.stdout.reconfigure(encoding="utf-8")
o={}
d=driver()
with d.session(database="neo4j") as s:
    o['coverage_fixed']=rows(s,"MATCH (m:Mantra) OPTIONAL MATCH (m)-[e:MENTIONS_ENTITY]->() WITH m.veda AS v, m, count(e) AS c WITH v, sum(CASE WHEN c>0 THEN 1 ELSE 0 END) AS covered, count(m) AS total RETURN v, covered, total, round(1.0*covered/total,4) AS share ORDER BY v")
    o['natphen_detail']=rows(s,"""MATCH (n:NaturalPhenomenon) WHERE n.personification_match_basis='UNAVAILABLE'
      RETURN n.entity_key AS k, n.preferred_label_sa AS sa, n.aliases_sa AS al,
      n.personification_status AS st, n.personification_status_reason AS reason,
      n.personification_evidence_reason AS ereason, n.personification_evidence_witness_count AS wc
      ORDER BY k""")
    o['devata_labels']=rows(s,"MATCH (dv:Devata) RETURN dv.devata_id AS id, dv.preferred_label_sa AS sa, dv.aliases_sa AS al")
    o['natphen_all_aliases']=rows(s,"MATCH (n:NaturalPhenomenon) RETURN n.entity_key AS k, n.preferred_label_sa AS sa, n.aliases_sa AS al ORDER BY k")
d.close()
# fold devata labels and compare
dl={}
for r in o['devata_labels']:
    for lab in [r['sa']]+list(r['al'] or []):
        if lab: dl.setdefault(fold_alias(lab), []).append(r['id'])
report=[]
for r in o['natphen_all_aliases']:
    cands=[]
    for lab in [r['sa']]+list(r['al'] or []):
        if lab:
            f=fold_alias(lab)
            if f in dl: cands.append((lab, dl[f]))
    report.append({"k":r['k'], "sa":r['sa'], "devata_alias_collisions":cands})
o['natphen_vs_devata']=report
pathlib.Path("data/staging/release_blocker_r5/agentB/probe5.json").write_text(json.dumps(o,indent=2,ensure_ascii=False,default=str),encoding="utf-8")
print(json.dumps(o['coverage_fixed'],indent=1))
print("=== UNAVAILABLE rows ===")
for r in o['natphen_detail']:
    print(" ",r['k'].split(':')[-1][:24],'| wc=',r['wc'],'| st=',r['st'])
    print("    reason:",str(r['reason'])[:300])
    print("    ev_reason:",str(r['ereason'])[:300])
print("=== natphen vs devata alias collisions ===")
for r in o['natphen_vs_devata']:
    if r['devata_alias_collisions']:
        print(" ",r['k'].split(':')[-1][:24], r['devata_alias_collisions'])
