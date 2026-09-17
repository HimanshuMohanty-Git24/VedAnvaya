#!/usr/bin/env python3
"""Apply the final-stabilization provenance and display contracts.

This is intentionally a small, one-purpose migration rather than a generic "fill in
missing fields" command.  Every branch below names the evidence already stored on the
affected edge or endpoint; an unrecognised branch remains ungraded and makes the command
fail.  In particular, confidence is never consulted when deriving a quality tier.

Run without ``--apply`` to write the preflight/contract receipt.  ``--apply`` first
requires that preflight to have no undeclared rows, then writes only NULL metadata fields.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys
from typing import Any

from neo4j import GraphDatabase

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "staging" / "final_stabilization" / "provenance_display_contract_receipt.json"
URI = "bolt://localhost:7687"
AUTH = ("neo4j", "vedagraph_dev")

BASE_FIELDS = """r.knowledge_layer = $layer,
    r.quality_tier = $tier,
    r.evidence_basis = $basis,
    r.attribution_precision = $precision,
    r.grade_basis = $grade_basis"""


def count(session: Any, cypher: str, **params: Any) -> int:
    return int(session.run(cypher, **params).single()["n"])


def preflight(session: Any) -> dict[str, int]:
    """Return undeclared populations; every value must be zero before applying."""
    return {
        "semantic_spine_without_deterministic_evidence": count(
            session,
            """MATCH (a)-[r:HAS_SEMANTIC_ASSERTION|ASSERTION_PREDICATE]->(b)
            WHERE r.quality_tier IS NULL
              AND ((type(r)='HAS_SEMANTIC_ASSERTION' AND b.evidence_layer <> 'DETERMINISTIC_DERIVED')
                OR (type(r)='ASSERTION_PREDICATE' AND a.evidence_layer <> 'DETERMINISTIC_DERIVED'))
            RETURN count(r) AS n""",
        ),
        "assertion_role_without_deterministic_evidence": count(
            session,
            """MATCH (s:SemanticAssertion)-[r:ASSERTION_ROLE]->()
            WHERE r.quality_tier IS NULL
              AND NOT (s.evidence_layer='DETERMINISTIC_DERIVED' AND r.provenance='deterministic')
            RETURN count(r) AS n""",
        ),
        "text_edges_without_recorded_deterministic_transform": count(
            session,
            """MATCH ()-[r:HAS_TEXT_VERSION]->(t:TextVersion)
            WHERE r.quality_tier IS NULL AND t.provenance <> 'deterministic'
            RETURN count(r) AS n""",
        ),
        "entity_mentions_without_sanskrit_token_method": count(
            session,
            """MATCH ()-[r:MENTIONS_ENTITY]->()
            WHERE r.quality_tier IS NULL AND r.method <> 'domain-mention-v1:sanskrit-token'
            RETURN count(r) AS n""",
        ),
        "ritual_edges_without_source_explicit_citation": count(
            session,
            """MATCH ()-[r:PERFORMED_BY|RECEIVES_OFFERING|USES_OBJECT]->()
            WHERE r.quality_tier IS NULL
              AND NOT (r.evidence_layer='SOURCE_EXPLICIT'
                       AND (r.evidence_citation IS NOT NULL OR size(coalesce(r.evidence_citations, [])) > 0))
            RETURN count(r) AS n""",
        ),
    }


def apply(session: Any) -> dict[str, int]:
    writes: dict[str, tuple[str, dict[str, str]]] = {
        "semantic_spine": (
            """MATCH (a)-[r:HAS_SEMANTIC_ASSERTION|ASSERTION_PREDICATE]->(b)
            WHERE r.quality_tier IS NULL
              AND ((type(r)='HAS_SEMANTIC_ASSERTION' AND b.evidence_layer='DETERMINISTIC_DERIVED')
                OR (type(r)='ASSERTION_PREDICATE' AND a.evidence_layer='DETERMINISTIC_DERIVED'))
            SET """ + BASE_FIELDS + """
            RETURN count(r) AS n""",
            {
                "layer": "L2_DETERMINISTIC_DERIVED", "tier": "TIER_B",
                "basis": "STRUCTURAL", "precision": "NOT_AN_ATTRIBUTION",
                "grade_basis": "reified semantic spine; target assertion records DETERMINISTIC_DERIVED evidence",
            },
        ),
        "assertion_role": (
            """MATCH (s:SemanticAssertion)-[r:ASSERTION_ROLE]->()
            WHERE r.quality_tier IS NULL AND s.evidence_layer='DETERMINISTIC_DERIVED'
              AND r.provenance='deterministic'
            SET """ + BASE_FIELDS + """
            RETURN count(r) AS n""",
            {
                "layer": "L2_DETERMINISTIC_DERIVED", "tier": "TIER_B",
                "basis": "SANSKRIT", "precision": "NOT_AN_ATTRIBUTION",
                "grade_basis": "DCS/VedaWeb deterministic dependency or morphology derivation recorded on assertion",
            },
        ),
        "text_derivative": (
            """MATCH ()-[r:HAS_TEXT_VERSION]->(t:TextVersion)
            WHERE r.quality_tier IS NULL AND t.provenance='deterministic'
            SET """ + BASE_FIELDS + """
            RETURN count(r) AS n""",
            {
                "layer": "L2_DETERMINISTIC_DERIVED", "tier": "TIER_B",
                "basis": "STRUCTURAL", "precision": "NOT_AN_ATTRIBUTION",
                "grade_basis": "named source TextVersion transformed deterministically; source_artifact_id retained on endpoint",
            },
        ),
        "domain_sanskrit_mention": (
            """MATCH ()-[r:MENTIONS_ENTITY]->()
            WHERE r.quality_tier IS NULL AND r.method='domain-mention-v1:sanskrit-token'
            SET """ + BASE_FIELDS + """
            RETURN count(r) AS n""",
            {
                "layer": "L2_DETERMINISTIC_DERIVED", "tier": "TIER_B",
                "basis": "SANSKRIT", "precision": "TEXTUAL_MENTION",
                "grade_basis": "deterministic Sanskrit-token match; matched_aliases retained on edge",
            },
        ),
        "ritual_source_explicit": (
            """MATCH ()-[r:PERFORMED_BY|RECEIVES_OFFERING|USES_OBJECT]->()
            WHERE r.quality_tier IS NULL AND r.evidence_layer='SOURCE_EXPLICIT'
              AND (r.evidence_citation IS NOT NULL OR size(coalesce(r.evidence_citations, [])) > 0)
            SET """ + BASE_FIELDS + """
            RETURN count(r) AS n""",
            {
                "layer": "L1_SOURCE_EXPLICIT", "tier": "TIER_A",
                "basis": "SOURCE_METADATA", "precision": "NOT_AN_ATTRIBUTION",
                "grade_basis": "source-explicit ritual relation; citation and source type retained on edge",
            },
        ),
    }
    result: dict[str, int] = {}
    for name, (cypher, params) in writes.items():
        result[name] = count(session, cypher, **params)

    # A display string is derived from the controlled predicate plus the exact source surface.
    # It is neither an identity nor a normalization; the original verb_surface is untouched.
    result["semantic_display_labels"] = count(
        session,
        """MATCH (s:SemanticAssertion)
        WHERE s.display_label IS NULL AND s.predicate IS NOT NULL AND s.verb_surface IS NOT NULL
        SET s.display_label = s.predicate + ': ' + s.verb_surface,
            s.display_type = coalesce(s.display_type, 'SEMANTIC_ASSERTION')
        RETURN count(s) AS n""",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session(database="neo4j") as session:
            before_ungraded = count(session, "MATCH ()-[r]->() WHERE r.quality_tier IS NULL RETURN count(r) AS n")
            before_unlabeled = count(session, "MATCH (n) WHERE NOT n:Internal AND n.display_label IS NULL RETURN count(n) AS n")
            blockers = preflight(session)
            if any(blockers.values()):
                outcome: dict[str, Any] = {"applied": False, "blockers": blockers}
            elif args.apply:
                outcome = {"applied": True, "writes": apply(session), "blockers": blockers}
            else:
                outcome = {"applied": False, "blockers": blockers}
            after_ungraded = count(session, "MATCH ()-[r]->() WHERE r.quality_tier IS NULL RETURN count(r) AS n")
            after_unlabeled = count(session, "MATCH (n) WHERE NOT n:Internal AND n.display_label IS NULL RETURN count(n) AS n")
            payload = {
                "artifact": "FINAL_STABILIZATION_PROVENANCE_AND_DISPLAY_CONTRACT",
                "at": dt.datetime.now(dt.UTC).isoformat(),
                "contracts": {
                    "semantic_spine": "evidence_layer=DETERMINISTIC_DERIVED -> L2/TIER_B/STRUCTURAL",
                    "assertion_role": "assertion deterministic evidence plus relation provenance -> L2/TIER_B/SANSKRIT",
                    "text_derivative": "TextVersion provenance=deterministic -> L2/TIER_B/STRUCTURAL",
                    "domain_mention": "exact Sanskrit-token method -> L2/TIER_B/SANSKRIT",
                    "ritual": "SOURCE_EXPLICIT plus stored citation -> L1/TIER_A/SOURCE_METADATA",
                    "display_label": "SemanticAssertion predicate + exact verb_surface; no identity field changes",
                },
                "before": {"ungraded_edges": before_ungraded, "nodes_without_label": before_unlabeled},
                "outcome": outcome,
                "after": {"ungraded_edges": after_ungraded, "nodes_without_label": after_unlabeled},
            }
    finally:
        driver.close()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if not any(payload["outcome"]["blockers"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
