#!/usr/bin/env python3
"""Build and validate the Neo4j graph projection from canonical VedaGraph data.

Usage:
    python scripts/build_neo4j_projection.py [--uri URI] [--user USER] [--password PW]

Defaults to local Docker Neo4j: bolt://localhost:7687 / neo4j / vedagraph_dev
"""

from __future__ import annotations

import argparse
import logging
import pathlib
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = pathlib.Path(__file__).parent.parent


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Load VedaGraph corpus into Neo4j")
    p.add_argument("--uri", default="bolt://localhost:7687")
    p.add_argument("--user", default="neo4j")
    p.add_argument("--password", default="vedagraph_dev")
    p.add_argument(
        "--wipe",
        action="store_true",
        help="Delete all nodes/rels before loading (enables clean rebuild test)",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    try:
        from neo4j import GraphDatabase  # type: ignore[import-untyped]
    except ImportError:
        logger.error("neo4j driver not installed. Run: pip install 'vedagraph[graph]'")
        sys.exit(1)

    from vedagraph.graph.loader import drop_schema, load_all
    from vedagraph.graph.queries import (
        duplicate_canonical_keys,
        fetch_av_kanda,
        fetch_exact_parallels,
        fetch_passage,
        fetch_passage_with_translation,
        fetch_passages_by_chandas,
        fetch_passages_by_devata,
        fetch_sukta_mantras,
        fetch_yv_adhyaya,
        graph_statistics,
        orphan_passages,
    )

    logger.info("Connecting to Neo4j at %s", args.uri)
    driver = GraphDatabase.driver(args.uri, auth=(args.user, args.password))

    with driver.session() as session:
        if args.wipe:
            logger.info("Wiping database...")
            session.run("MATCH (n) DETACH DELETE n")
            drop_schema(session)
            logger.info("Database wiped")

        t0 = time.time()
        counts = load_all(session, PROJECT_ROOT)
        elapsed = time.time() - t0
        logger.info("Load completed in %.1fs", elapsed)

        # --- Validation queries ---
        logger.info("Running validation queries...")

        rv_1_1_1 = fetch_passage(session, "VG:RV:SAK:M01:S001:V001")
        logger.info("RV 1.1.1: %s", rv_1_1_1[0] if rv_1_1_1 else "NOT FOUND")

        sukta_mantras = fetch_sukta_mantras(session, "VG:RV:SAK:M01:S001")
        logger.info("RV 1.1 mantras: %d", len(sukta_mantras))

        agni_passages = fetch_passages_by_devata(session, "VG:DEVATA:AGNIH")
        logger.info("Passages invoking Agni: %d", len(agni_passages))

        gayatri_passages = fetch_passages_by_chandas(session, "VG:CHANDAS:GAYATRI")
        logger.info("Passages in Gāyatrī: %d", len(gayatri_passages))

        rv_1_1_1_trans = fetch_passage_with_translation(session, "VG:RV:SAK:M01:S001:V001")
        logger.info("RV 1.1.1 translations: %d", len(rv_1_1_1_trans))

        parallels = fetch_exact_parallels(session, "VG:RV:SAK:M01:S013:V009")
        logger.info("Parallels of RV 1.13.9: %d", len(parallels))

        yv_adhyaya = fetch_yv_adhyaya(session, "VG:YV:VSM:A01")
        logger.info("YV Adhyaya 1 mantras: %d", len(yv_adhyaya))

        av_kanda = fetch_av_kanda(session, "VG:AV:SAU:K20")
        logger.info("AV Kanda 20 suktas: %d", len(av_kanda))

        # --- Graph invariants ---
        orphans = orphan_passages(session)
        dupes = duplicate_canonical_keys(session)

        logger.info("Orphan Passage nodes: %d", len(orphans))
        if orphans:
            for o in orphans[:10]:
                logger.warning("  Orphan: %s (%s)", o["canonical_key"], o["veda"])

        logger.info("Duplicate canonical keys: %d", len(dupes))
        if dupes:
            for d in dupes[:10]:
                logger.error("  Duplicate: %s (count=%d)", d["key"], d["cnt"])

        # --- Statistics ---
        stats = graph_statistics(session)
        logger.info("=== Graph Statistics ===")
        for row in stats["nodes"]:
            logger.info("  Node  %-20s %d", row["label"], row["count"])
        for row in stats["relationships"]:
            logger.info("  Rel   %-30s %d", row["rel_type"], row["count"])

        # --- Summary ---
        logger.info("=== Load Summary ===")
        for k, v in counts.items():
            logger.info("  %-35s %s", k, v)

        logger.info("Invariants: orphans=%d  duplicates=%d", len(orphans), len(dupes))

    driver.close()

    if orphans or dupes:
        logger.error("Graph invariant failures detected")
        sys.exit(1)

    logger.info("Graph foundation READY")


if __name__ == "__main__":
    main()
