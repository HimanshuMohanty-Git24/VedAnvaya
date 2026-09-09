#!/usr/bin/env python3
"""Load the enrichment artifacts into the live Neo4j, then validate and query it.

This script exists because a serialized projection that validates cleanly can still be
wrong once loaded: a MERGE can collapse two rows into one and a MATCH can find no endpoint,
and neither shows up offline. So every count here is read back out of the database, the
live invariants run against the loaded graph, and the insight queries are executed and
timed rather than merely being syntax-checked.

Usage:
    python scripts/load_enrichment_neo4j.py [--uri URI] [--user U] [--password P]
                                            [--skip-gds] [--json OUT.json]
"""

from __future__ import annotations

import argparse
import json
import logging
import pathlib
import sys
import time
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load and validate the enrichment layer")
    parser.add_argument("--uri", default="bolt://localhost:7687")
    parser.add_argument("--user", default="neo4j")
    parser.add_argument("--password", default="vedagraph_dev")
    parser.add_argument("--skip-gds", action="store_true", help="Skip the optional GDS layer")
    parser.add_argument("--json", default="", help="Write the full result to this path")
    return parser.parse_args()


def _census(session: Any) -> dict[str, dict[str, int]]:
    """Node and relationship counts straight from the database."""
    nodes = {
        record["label"]: record["c"]
        for record in session.run(
            "CALL db.labels() YIELD label "
            "CALL (label) { MATCH (n) WHERE label IN labels(n) RETURN count(n) AS c } "
            "RETURN label, c ORDER BY label"
        )
    }
    rels = {
        record["t"]: record["c"]
        for record in session.run(
            "CALL db.relationshipTypes() YIELD relationshipType AS t "
            "CALL (t) { MATCH ()-[r]->() WHERE type(r) = t RETURN count(r) AS c } "
            "RETURN t, c ORDER BY t"
        )
    }
    totals = {
        "nodes": session.run("MATCH (n) RETURN count(n) AS c").single()["c"],
        "relationships": session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"],
    }
    return {"nodes": nodes, "relationships": rels, "totals": totals}


def main() -> None:
    args = parse_args()

    try:
        from neo4j import GraphDatabase
    except ImportError:
        logger.error("neo4j driver not installed. Run: pip install -r infra/requirements-graph.txt")
        sys.exit(1)

    from vedagraph.enrich.validate import validate_live
    from vedagraph.graph.enrichment_loader import load_enrichment
    from vedagraph.graph.gds import run_analytics
    from vedagraph.graph.insight_queries import QUERIES

    driver = GraphDatabase.driver(
        args.uri, auth=(args.user, args.password), notifications_min_severity="OFF"
    )
    result: dict[str, Any] = {}

    with driver.session() as session:
        before = _census(session)
        logger.info(
            "Before: %d nodes, %d relationships",
            before["totals"]["nodes"],
            before["totals"]["relationships"],
        )
        result["before"] = before

        started = time.time()
        load_counts = load_enrichment(session, PROJECT_ROOT)
        result["load_seconds"] = round(time.time() - started, 2)
        result["load_counts"] = load_counts
        logger.info("Enrichment loaded in %.1fs", result["load_seconds"])
        for name, value in sorted(load_counts.items()):
            logger.info("  %-32s %s", name, value)

        after = _census(session)
        result["after"] = after
        logger.info(
            "After: %d nodes, %d relationships",
            after["totals"]["nodes"],
            after["totals"]["relationships"],
        )

        # --- live invariants ---------------------------------------------------
        expected = {
            key: value
            for key, value in load_counts.items()
            if isinstance(value, int) and not key.startswith(("unmatched", "rejected", "skipped"))
        }
        validation = validate_live(session, expected)
        result["validation"] = validation.as_dict()
        logger.info("=== Live validation: %d checks ===", len(set(validation.checks_run)))
        for finding in validation.findings:
            logger.log(
                logging.ERROR if finding.severity == "ERROR" else logging.WARNING,
                "  %s %s: %d - %s",
                finding.severity,
                finding.check,
                finding.count,
                finding.detail,
            )
            for example in finding.examples[:5]:
                logger.info("      %s", example)

        # --- insight queries ---------------------------------------------------
        logger.info("=== Insight queries ===")
        query_results: dict[str, Any] = {}
        for query in QUERIES:
            started = time.time()
            try:
                rows = query.run(session)
                elapsed_ms = round((time.time() - started) * 1000, 1)
                query_results[query.name] = {
                    "rows": len(rows),
                    "ms": elapsed_ms,
                    "sample": rows[:5],
                }
                logger.info("  %-42s %5d rows  %8.1f ms", query.name, len(rows), elapsed_ms)
            except Exception as exc:
                query_results[query.name] = {"error": f"{type(exc).__name__}: {exc}"}
                logger.error("  %-42s FAILED: %s", query.name, exc)
        result["queries"] = query_results

        # --- optional GDS ------------------------------------------------------
        if args.skip_gds:
            result["gds"] = {"available": False, "reason": "skipped by flag"}
        else:
            logger.info("=== Graph Data Science ===")
            started = time.time()
            result["gds"] = run_analytics(session)
            result["gds_seconds"] = round(time.time() - started, 2)
            if result["gds"].get("available"):
                logger.info(
                    "GDS %s: %d communities, modularity %.3f, %.1fs",
                    result["gds"]["gds_version"],
                    result["gds"]["communities"]["community_count"],
                    result["gds"]["communities"]["modularity"],
                    result["gds_seconds"],
                )
            else:
                logger.info("GDS unavailable: %s", result["gds"].get("reason"))

    driver.close()

    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(result, indent=2, default=str), "utf-8")
        logger.info("Wrote %s", args.json)

    failed_queries = [name for name, r in result["queries"].items() if "error" in r]
    if failed_queries:
        logger.error("Insight queries failed: %s", failed_queries)
    if not validation.passed or failed_queries:
        sys.exit(1)
    logger.info("Enrichment load validated")


if __name__ == "__main__":
    main()
