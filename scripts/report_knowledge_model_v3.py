"""Measure every figure the Knowledge Model V3 close-out report has to state.

The V3 brief asks for 87 numbered facts about the finished graph. Typing them by hand is
how a close-out report drifts from the thing it describes -- and this repository has
already been burned by exactly that: a query catalogue shipped a scope caveat asserting
that two predicates had zero non-Rigvedic edges, and by the time anyone read it the graph
held 13,121 of them. So every number the report quotes is produced here, from the live
database and the artifacts on disk, and the report cites this script.

Nothing is written to the database. Nothing is inferred. Where a figure cannot be
measured, the value is the string ``NOT_MEASURABLE`` with a reason beside it, because a
missing number that says so is worth more than a plausible one that does not.

Usage::

    python scripts/report_knowledge_model_v3.py
    python scripts/report_knowledge_model_v3.py --json out.json
"""

from __future__ import annotations

import argparse
import collections
import io
import json
import pathlib
import subprocess
import sys
from typing import Any, Final

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import orjson  # noqa: E402

BOLT_URI: Final = "bolt://localhost:7687"
BOLT_AUTH: Final = ("neo4j", "vedagraph_dev")

ENRICH: Final = PROJECT_ROOT / "data" / "enrichment" / "vedagraph_enrichment_v1"
DOMAIN: Final = PROJECT_ROOT / "data" / "domain" / "vedagraph_domain_v2"


def _rows(path: pathlib.Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [orjson.loads(r) for r in path.read_bytes().split(b"\n") if r.strip()]


def _declared_predicates() -> int:
    """How many predicates the closed action vocabulary declares.

    Read through the real loader rather than by counting YAML keys, so the figure the
    report prints is the figure the graph builder used.
    """
    from vedagraph.enrich.agentive import load_vocabulary

    return len(load_vocabulary(PROJECT_ROOT).by_label)


def _one(session: Any, query: str, **params: Any) -> Any:
    record = session.run(query, **params).single()
    if record is None:
        return None
    return record[record.keys()[0]]


def _table(session: Any, query: str, **params: Any) -> dict[str, int]:
    out: dict[str, int] = {}
    for record in session.run(query, **params):
        keys = record.keys()
        out[str(record[keys[0]])] = int(record[keys[1]])
    return out


def collect(session: Any) -> dict[str, Any]:
    """Every measurable figure, grouped the way the report presents them."""
    report: dict[str, Any] = {}

    report["identity"] = {
        "commit": subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        ).stdout.strip(),
        "branch": subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        ).stdout.strip(),
        "neo4j": _one(session, "CALL dbms.components() YIELD versions RETURN versions[0]"),
    }

    report["size"] = {
        "nodes": _one(session, "MATCH (n) RETURN count(n) AS c"),
        "relationships": _one(session, "MATCH ()-[r]->() RETURN count(r) AS c"),
        "product_nodes": _one(session, "MATCH (n) WHERE NOT n:Internal RETURN count(n) AS c"),
        "internal_nodes": _one(session, "MATCH (n:Internal) RETURN count(n) AS c"),
        "label_tokens": _one(session, "CALL db.labels() YIELD label RETURN count(label) AS c"),
        "populated_labels": len(
            _table(
                session,
                "CALL db.labels() YIELD label "
                "CALL (label) { MATCH (n) WHERE label IN labels(n) RETURN count(n) AS c } "
                "WITH label, c WHERE c > 0 RETURN label, c",
            )
        ),
        "rel_type_tokens": _one(
            session,
            "CALL db.relationshipTypes() YIELD relationshipType RETURN count(*) AS c",
        ),
    }

    report["labels"] = _table(
        session,
        "CALL db.labels() YIELD label "
        "CALL (label) { MATCH (n) WHERE label IN labels(n) RETURN count(n) AS c } "
        "RETURN label, c ORDER BY c DESC",
    )
    report["relationship_types"] = _table(
        session,
        "CALL db.relationshipTypes() YIELD relationshipType "
        "CALL (relationshipType) { MATCH ()-[r]->() "
        "  WHERE type(r) = relationshipType RETURN count(r) AS c } "
        "RETURN relationshipType, c ORDER BY c DESC",
    )
    report["empty_declared_types"] = sorted(
        name for name, count in report["relationship_types"].items() if count == 0
    )
    report["empty_declared_labels"] = sorted(
        name for name, count in report["labels"].items() if count == 0
    )

    # --- grading -----------------------------------------------------------------
    report["quality_tiers"] = _table(
        session,
        "MATCH ()-[r]->() RETURN r.quality_tier AS t, count(*) AS c ORDER BY t",
    )
    report["evidence_basis"] = _table(
        session,
        "MATCH ()-[r]->() RETURN r.evidence_basis AS b, count(*) AS c ORDER BY c DESC",
    )
    report["attribution_precision"] = _table(
        session,
        "MATCH ()-[r]->() WHERE r.attribution_precision IS NOT NULL "
        "RETURN r.attribution_precision AS p, count(*) AS c ORDER BY c DESC",
    )
    report["grading_gaps"] = {
        "edges_without_tier": _one(
            session, "MATCH ()-[r]->() WHERE r.quality_tier IS NULL RETURN count(*) AS c"
        ),
        "edges_without_basis": _one(
            session,
            "MATCH ()-[r]->() WHERE r.evidence_basis IS NULL RETURN count(*) AS c",
        ),
        "edges_basis_unspecified": _one(
            session,
            "MATCH ()-[r]->() WHERE r.evidence_basis = 'UNSPECIFIED' RETURN count(*) AS c",
        ),
        "assertion_nodes_without_tier": _one(
            session,
            "MATCH (s:SemanticAssertion) WHERE s.quality_tier IS NULL RETURN count(*) AS c",
        ),
    }
    report["review_states"] = _table(
        session,
        "MATCH ()-[r]->() WHERE r.review_state IS NOT NULL "
        "RETURN r.review_state AS s, count(*) AS c ORDER BY c DESC",
    )
    report["human_reviewed_claims"] = _one(
        session,
        "MATCH ()-[r]->() WHERE r.review_state = 'HUMAN_REVIEWED' RETURN count(*) AS c",
    )

    # --- theonym layer -----------------------------------------------------------
    report["theonym"] = {
        "edges": _one(session, "MATCH ()-[r:MENTIONS_DEVATA]->() RETURN count(r) AS c"),
        "by_veda": _table(
            session,
            "MATCH ()-[r:MENTIONS_DEVATA]->() RETURN r.veda AS v, count(*) AS c ORDER BY c DESC",
        ),
        "by_certainty": _table(
            session,
            "MATCH ()-[r:MENTIONS_DEVATA]->() "
            "RETURN r.referent_certainty AS rc, count(*) AS c ORDER BY c DESC",
        ),
        "by_tier": _table(
            session,
            "MATCH ()-[r:MENTIONS_DEVATA]->() "
            "RETURN r.quality_tier AS t, count(*) AS c ORDER BY t",
        ),
        "deities_covered": _one(
            session,
            "MATCH ()-[:MENTIONS_DEVATA]->(d:Devata) RETURN count(DISTINCT d) AS c",
        ),
        "mantras_covered": _one(
            session,
            "MATCH (p:Mantra)-[:MENTIONS_DEVATA]->() RETURN count(DISTINCT p) AS c",
        ),
    }

    # --- attribution -------------------------------------------------------------
    report["attribution"] = {}
    for rel in ("HAS_DEVATA", "HAS_RISHI", "HAS_CHANDAS", "HAS_DEVATA_ASCRIPTION"):
        report["attribution"][rel] = {
            "total": _one(
                session, f"MATCH ()-[r:{rel}]->() RETURN count(r) AS c"
            ),
            "by_veda": _table(
                session,
                f"MATCH (p:Passage)-[r:{rel}]->() "
                "RETURN p.veda AS v, count(*) AS c ORDER BY c DESC",
            ),
            "by_precision": _table(
                session,
                f"MATCH ()-[r:{rel}]->() "
                "RETURN r.attribution_precision AS p, count(*) AS c ORDER BY c DESC",
            ),
        }

    # --- action / agentive -------------------------------------------------------
    report["agentive"] = {
        "action_predicates_declared": _declared_predicates(),
        "action_predicate_nodes": _one(
            session, "MATCH (a:ActionPredicate) RETURN count(a) AS c"
        ),
        "predicates_with_zero_assertions": _one(
            session,
            "MATCH (a:ActionPredicate) WHERE NOT (a)<-[:ASSERTION_PREDICATE]-() "
            "RETURN count(a) AS c",
        ),
        "assertions_total": _one(
            session, "MATCH (s:SemanticAssertion) RETURN count(s) AS c"
        ),
        "assertions_by_derivation": _table(
            session,
            "MATCH (s:SemanticAssertion) RETURN s.derivation AS d, count(*) AS c "
            "ORDER BY c DESC",
        ),
        "assertions_by_tier": _table(
            session,
            "MATCH (s:SemanticAssertion) RETURN s.quality_tier AS t, count(*) AS c "
            "ORDER BY t",
        ),
        "performs_action": _one(
            session, "MATCH ()-[r:PERFORMS_ACTION]->() RETURN count(r) AS c"
        ),
        "is_asked_to": _one(
            session, "MATCH ()-[r:IS_ASKED_TO]->() RETURN count(r) AS c"
        ),
    }

    # --- candidate adjudication --------------------------------------------------
    review = _rows(ENRICH / "semantic_candidate_review_v3.jsonl")
    report["candidate_review"] = {
        "adjudicated": len(review),
        "verdicts": dict(
            sorted(collections.Counter(r.get("verdict", "?") for r in review).items())
        ),
        "reviewer": sorted({r.get("reviewer", "?") for r in review}),
        "passage_read": sum(1 for r in review if r.get("passage_read")),
        "sanskrit_checked": sum(1 for r in review if r.get("sanskrit_checked")),
        "live_tier_c": _one(
            session, "MATCH ()-[r]->() WHERE r.quality_tier='TIER_C' RETURN count(r) AS c"
        ),
        "rejected_still_live": _one(
            session,
            "MATCH ()-[r]->() WHERE r.review_verdict = 'REJECT' RETURN count(r) AS c",
        ),
        "retained_unresolved": _one(
            session,
            "MATCH ()-[r]->() WHERE r.review_verdict IN "
            "['AMBIGUOUS','NEEDS_MORE_EVIDENCE'] RETURN count(r) AS c",
        ),
    }

    # --- concepts, formulas, rituals, concerns -----------------------------------
    report["concepts"] = {
        "nodes": _one(session, "MATCH (c:Concept) RETURN count(c) AS c"),
        "about_concept_edges": _one(
            session, "MATCH ()-[r:ABOUT_CONCEPT]->() RETURN count(r) AS c"
        ),
        "mentions_entity_edges": _one(
            session, "MATCH ()-[r:MENTIONS_ENTITY]->() RETURN count(r) AS c"
        ),
        "about_concept_corroborated_by_mention": _one(
            session,
            "MATCH (p:Passage)-[:ABOUT_CONCEPT]->(c) "
            "WHERE (p)-[:MENTIONS_ENTITY]->(c) RETURN count(*) AS c",
        ),
        "by_node_type": _table(
            session,
            "MATCH (c:Concept) RETURN c.node_type AS t, count(*) AS c ORDER BY c DESC",
        ),
    }
    report["formulas"] = {
        "formula_nodes": _one(session, "MATCH (f:Formula) RETURN count(f) AS c"),
        "family_nodes": _one(session, "MATCH (f:FormulaFamily) RETURN count(f) AS c"),
        "membership_edges": _one(
            session, "MATCH ()-[r:MEMBER_OF_FAMILY]->() RETURN count(r) AS c"
        ),
        "members_by_role": _table(
            session,
            "MATCH ()-[r:MEMBER_OF_FAMILY]->() RETURN r.role AS r, count(*) AS c "
            "ORDER BY c DESC",
        ),
        "members_by_tier": _table(
            session,
            "MATCH ()-[r:MEMBER_OF_FAMILY]->() RETURN r.quality_tier AS t, count(*) AS c "
            "ORDER BY t",
        ),
        "members_containing_representative": _one(
            session,
            "MATCH ()-[r:MEMBER_OF_FAMILY]->() WHERE r.contains_representative "
            "RETURN count(r) AS c",
        ),
        "formulas_unfamilied": _one(
            session,
            "MATCH (f:Formula) WHERE NOT (f)-[:MEMBER_OF_FAMILY]->() RETURN count(f) AS c",
        ),
        "cross_veda_families": _one(
            session,
            "MATCH (f:FormulaFamily) WHERE f.cross_veda RETURN count(f) AS c",
        ),
        "families_spanning_3_plus": _one(
            session,
            "MATCH (f:FormulaFamily) WHERE f.veda_span >= 3 RETURN count(f) AS c",
        ),
    }
    report["ritual"] = {
        "rituals": _one(session, "MATCH (r:Ritual) RETURN count(r) AS c"),
        "ritual_roles": _one(session, "MATCH (r:RitualRole) RETURN count(r) AS c"),
        "actions": _one(session, "MATCH (a:Action) RETURN count(a) AS c"),
        "described_in": _one(
            session, "MATCH (:Ritual)-[r:DESCRIBED_IN]->(:Passage) RETURN count(r) AS c"
        ),
        "has_step": _one(
            session, "MATCH (:Ritual)-[r:HAS_STEP]->(:Action) RETURN count(r) AS c"
        ),
        "structure_edges": _one(
            session,
            "MATCH (:Ritual)-[r]->() WHERE type(r) IN "
            "['USES_OFFERING','USES_SUBSTANCE','USES_OBJECT','INVOKES_DEVATA',"
            "'PERFORMED_BY','PERFORMED_FOR'] RETURN count(r) AS c",
        ),
    }
    report["concerns"] = {
        "conditions": _one(session, "MATCH (c:Condition) RETURN count(c) AS c"),
        "human_concerns": _one(session, "MATCH (c:HumanConcern) RETURN count(c) AS c"),
        "treats": _one(session, "MATCH ()-[r:TREATS]->() RETURN count(r) AS c"),
        "protects_from": _one(
            session, "MATCH ()-[r:PROTECTS_FROM]->() RETURN count(r) AS c"
        ),
        "addresses_concern": _one(
            session, "MATCH ()-[r:ADDRESSES_CONCERN]->() RETURN count(r) AS c"
        ),
    }

    # --- cross-Veda, analytics, coverage ------------------------------------------
    report["cross_veda"] = {
        rel: _one(session, f"MATCH ()-[r:{rel}]->() RETURN count(r) AS c")
        for rel in (
            "EXACT_PARALLEL_OF",
            "NEAR_PARALLEL_OF",
            "VARIANT_OF",
            "REUSES_TEXT_FROM",
            "PARALLEL_TO",
        )
    }
    report["analytics"] = {
        "derived_metrics": _one(
            session, "MATCH (m:DerivedMetric) RETURN count(m) AS c"
        ),
        "metric_families": _table(
            session,
            "MATCH (m:DerivedMetric) RETURN m.metric_name AS n, count(*) AS c "
            "ORDER BY c DESC",
        ),
        "cooccurrence_edges": _one(
            session, "MATCH ()-[r:CO_OCCURS_WITH]->() RETURN count(r) AS c"
        ),
        "interpretive_claims": _one(
            session, "MATCH (c:InterpretiveClaim) RETURN count(c) AS c"
        ),
    }
    coverage_path = DOMAIN / "veda_coverage_v3.json"
    if coverage_path.exists():
        coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
        report["veda_coverage_score"] = {
            veda: info.get("coverage_score")
            for veda, info in sorted(coverage.get("vedas", {}).items())
        }
    else:
        report["veda_coverage_score"] = "NOT_MEASURABLE: veda_coverage_v3.json absent"

    # --- product / internal separation --------------------------------------------
    report["separation"] = {
        "internal_labels_in_product": _table(
            session,
            "MATCH (n) WHERE NOT n:Internal UNWIND labels(n) AS l "
            "WITH l WHERE l IN ['QAIssue','TextVersion','Translation','Source',"
            "'SourceArtifact'] RETURN l, count(*) AS c",
        ),
        "unlabelled_product_nodes": _one(
            session,
            "MATCH (n) WHERE NOT n:Internal AND size(labels(n)) = 0 RETURN count(n) AS c",
        ),
        "product_nodes_without_display_label": _one(
            session,
            "MATCH (n) WHERE NOT n:Internal AND n.display_label IS NULL "
            "RETURN count(n) AS c",
        ),
    }

    # --- layer scope self-description ---------------------------------------------
    # The key is built in Python: `layer_veda_scope` is a list, and Cypher's toString()
    # refuses lists, so composing the label there is not available.
    report["layer_veda_scope"] = {
        f"{record['label']} {sorted(record['scope'])}": int(record["c"])
        for record in session.run(
            "MATCH (n) WHERE n.layer_veda_scope IS NOT NULL "
            "RETURN labels(n)[0] AS label, n.layer_veda_scope AS scope, count(*) AS c "
            "ORDER BY c DESC"
        )
    }

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", help="also write the full measurement to this path")
    args = parser.parse_args()

    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(BOLT_URI, auth=BOLT_AUTH)
    try:
        with driver.session() as session:
            report = collect(session)
    finally:
        driver.close()

    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    print(text)
    if args.json:
        pathlib.Path(args.json).write_text(text + "\n", encoding="utf-8", newline="\n")
        print(f"\nwrote {args.json}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
