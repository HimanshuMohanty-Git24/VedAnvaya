"""Agent B independent re-measurement of the 11 R5 closure measures. READ ONLY."""
from __future__ import annotations
import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path("data/staging/release_blocker_r5").resolve()))
from _q import driver, one, rows  # noqa

REG = json.load(open("data/gap_registry.json", encoding="utf-8"))
AUD = json.load(open("data/staging/wave4/registry_closure_audit.json", encoding="utf-8"))
gaps = {g["gap_id"]: g for g in REG["gaps"]}
arows = {r["gap_id"]: r for r in AUD["rows"]}

IDS = ["GAP-ENTITY_COVERAGE-004","GAP-ENTITY_COVERAGE-006","GAP-ENTITY_COVERAGE-007",
       "GAP-PRODUCT_SURFACE-005","GAP-QUALITY-003","GAP-RITUAL-003","GAP-RITUAL-005",
       "GAP-RITUAL-006","GAP-SAMAVEDA_MUSIC-003","GAP-SEMANTICS-003","GAP-TRANSLATION-004"]

out = {"reran_measures": {}, "extra": {}}
d = driver()
with d.session(database="neo4j") as s:
    # 1. rerun every closure_measure that is Cypher, for ALL 85 entries
    all_m = {}
    for gid, g in gaps.items():
        m = g.get("closure_measure") or ""
        if m.strip().upper().startswith(("MATCH", "CALL", "RETURN", "WITH", "UNWIND", "OPTIONAL")):
            try:
                v = one(s, m)
            except Exception as e:
                v = f"ERROR: {type(e).__name__}: {e}"
            all_m[gid] = {"measure": m, "agentB_measured": v,
                          "registry_recorded": g.get("closure_measured_value"),
                          "audit_recorded": arows[gid].get("closure_measured_value"),
                          "audit_expected": arows[gid].get("closure_expected_value"),
                          "status": g.get("status")}
        else:
            all_m[gid] = {"measure": m, "agentB_measured": "NOT_CYPHER",
                          "registry_recorded": g.get("closure_measured_value"),
                          "audit_recorded": arows[gid].get("closure_measured_value"),
                          "status": g.get("status")}
    out["reran_measures"] = all_m

    # 2. census
    out["extra"]["census"] = {
        "nodes": one(s, "MATCH (n) RETURN count(n)"),
        "rels": one(s, "MATCH ()-[r]->() RETURN count(r)"),
        "RV": one(s, "MATCH (m:Mantra {veda:'RV'}) RETURN count(m)"),
        "SV": one(s, "MATCH (m:Mantra {veda:'SV'}) RETURN count(m)"),
        "YV": one(s, "MATCH (m:Mantra {veda:'YV'}) RETURN count(m)"),
        "AV": one(s, "MATCH (m:Mantra {veda:'AV'}) RETURN count(m)"),
        "Mantra": one(s, "MATCH (m:Mantra) RETURN count(m)"),
        "DerivedMetric": one(s, "MATCH (n:DerivedMetric) RETURN count(n)"),
        "Passage": one(s, "MATCH (n:Passage) RETURN count(n)"),
        "Formula": one(s, "MATCH (n:Formula) RETURN count(n)"),
        "SemanticAssertion": one(s, "MATCH (n:SemanticAssertion) RETURN count(n)"),
        "DomainEntity": one(s, "MATCH (n:DomainEntity) RETURN count(n)"),
        "NaturalPhenomenon": one(s, "MATCH (n:NaturalPhenomenon) RETURN count(n)"),
        "Ritual": one(s, "MATCH (n:Ritual) RETURN count(n)"),
        "TextVersion": one(s, "MATCH (n:TextVersion) RETURN count(n)"),
        "Translation": one(s, "MATCH (n:Translation) RETURN count(n)"),
        "RoleFiller": one(s, "MATCH (n:RoleFiller) RETURN count(n)"),
        "Devata": one(s, "MATCH (n:Devata) RETURN count(n)"),
        "Epithet": one(s, "MATCH (n:Epithet) RETURN count(n)"),
        "FormulaFamily": one(s, "MATCH (n:FormulaFamily) RETURN count(n)"),
    }
    out["extra"]["rel_types"] = rows(s, "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType ORDER BY relationshipType")
    out["extra"]["rel_type_counts"] = rows(s, "MATCH ()-[r]->() RETURN type(r) AS t, count(r) AS c ORDER BY t")

    # 3. SEMANTICS-003
out_json = json.dumps(out, indent=2, ensure_ascii=False, default=str)
pathlib.Path("data/staging/release_blocker_r5/agentB/probe1.json").write_text(out_json, encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8")
print("WROTE probe1.json")
d.close()
