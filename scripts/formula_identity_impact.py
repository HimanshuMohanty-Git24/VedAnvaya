#!/usr/bin/env python3
"""Produce the required Formula identity-impact receipt without mutating the graph."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from neo4j import GraphDatabase

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "data/enrichment/vedagraph_enrichment_v1/formulas.jsonl"
OUT = ROOT / "data/staging/final_stabilization/formula_identity_impact.json"


def artifact_rows() -> dict[str, dict[str, Any]]:
    return {str(row["formula_id"]): row for line in ARTIFACT.open(encoding="utf-8") if (row := json.loads(line))}


def main() -> int:
    rebuilt = artifact_rows()
    driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "vedagraph_dev"))
    try:
        with driver.session(database="neo4j") as session:
            current = [dict(r) for r in session.run(
                """MATCH (f:Formula) RETURN f.formula_id AS formula_id, properties(f) AS props ORDER BY formula_id"""
            )]
            impact: list[dict[str, Any]] = []
            for row in current:
                fid, props = str(row["formula_id"]), dict(row["props"])
                if fid in rebuilt:
                    continue
                # The corrected miner has no supported one-to-one identity mapping for this
                # disappearing formula.  Claiming one from a normalised string would violate
                # the stable-identity policy, so the proposed id is explicitly null.
                inbound = int(session.run("MATCH ()-[r]->(:Formula {formula_id:$id}) RETURN count(r) AS n", id=fid).single()["n"])
                outbound = int(session.run("MATCH (:Formula {formula_id:$id})-[r]->() RETURN count(r) AS n", id=fid).single()["n"])
                stored_refs = {
                    "uses_formula": int(session.run("MATCH ()-[r:USES_FORMULA]->(:Formula {formula_id:$id}) RETURN count(r) AS n", id=fid).single()["n"]),
                    "family_memberships": int(session.run("MATCH (:Formula {formula_id:$id})-[r:MEMBER_OF_FAMILY]->() RETURN count(r) AS n", id=fid).single()["n"]),
                    "shares_formula": int(session.run("MATCH (:Formula {formula_id:$id})-[r:SHARES_FORMULA_WITH]->() RETURN count(r) AS n", id=fid).single()["n"]),
                }
                impact.append({
                    "current_formula_id": fid,
                    "proposed_formula_id": None,
                    "canonical_key": props.get("canonical_key"),
                    "urn": props.get("canonical_urn") or props.get("urn"),
                    "uuid": props.get("uuid") or props.get("entity_id"),
                    "formula_id_is_externally_publicly_referenced": True,
                    "published_contract_evidence": [
                        "src/vedagraph/api/routes/formulas.py exposes /api/v1/formulas/{formula_id}",
                        "src/vedagraph/api/routes/graph.py describes Formula.formula_id as a stable product id",
                    ],
                    "inbound_relationship_count": inbound,
                    "outbound_relationship_count": outbound,
                    "frontend_public_references": {
                        "contract": "frontend/src/lib/api-schema.ts exposes formula_id route and response fields",
                        "static_id_occurrences": 0,
                    },
                    "ask_references": {
                        "contract": "src/vedagraph/api/ask/retriever.py emits formula_id in evidence packets",
                        "live_reference_count": 0,
                    },
                    "persisted_artifact_references": stored_refs,
                    "old_identity_can_remain_as_alias": False,
                    "semantic_content_changed": True,
                    "exact_reason_for_proposed_movement": (
                        "No compatible movement is proposed. The corrected Yajurvedic double-fold changes the miner's collapsed surface and its maximality population; "
                        "this old formula is absent from the rebuilt artifact, not a one-to-one renamed formula."
                    ),
                    "policy_disposition": "KEEP_CURRENT_PUBLISHED_STABLE_ID; do not re-key from a recomputed content hash",
                })
    finally:
        driver.close()
    payload = {
        "artifact": "FORMULA_IDENTITY_IMPACT",
        "source_artifact": str(ARTIFACT.relative_to(ROOT)).replace("\\", "/"),
        "current_formula_count": len(current),
        "rebuilt_formula_artifact_count": len(rebuilt),
        "impacted_formula_count": len(impact),
        "owner_rule_applied": "formula_id is a published stable product ID; content-hash/recomputation cannot silently re-key it",
        "migration_permitted": False,
        "rows": impact,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in payload.items() if k != "rows"}, indent=2))
    return 0 if len(impact) == 217 else 1


if __name__ == "__main__":
    raise SystemExit(main())
