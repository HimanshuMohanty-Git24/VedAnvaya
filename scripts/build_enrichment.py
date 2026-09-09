#!/usr/bin/env python3
"""Run the deterministic enrichment stages and write data/enrichment/.

No database and no network. Everything this produces is a function of the canonical corpus
and the concept registry, so a second run over unchanged inputs must produce byte-identical
files -- which ``--verify-determinism`` checks by building twice and comparing digests.

Usage:
    python scripts/build_enrichment.py [--verify-determinism] [--validate]
"""

from __future__ import annotations

import argparse
import logging
import pathlib
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the VedaGraph enrichment layer")
    parser.add_argument(
        "--verify-determinism",
        action="store_true",
        help="Build twice and fail if any artifact digest differs",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Run the offline invariant checks over the written artifacts",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    from vedagraph.enrich.build import (
        CONCEPT_ASSERTIONS_FILE,
        CONCEPTS_FILE,
        FORMULA_OCCURRENCES_FILE,
        FORMULAS_FILE,
        PARALLELS_FILE,
        SEMANTIC_CANDIDATES_FILE,
        build_enrichment,
        read_artifact,
    )

    manifest = build_enrichment(PROJECT_ROOT)

    logger.info("=== Enrichment counts ===")
    for name, value in sorted(manifest["counts"].items()):
        logger.info("  %-28s %d", name, value)
    logger.info("=== Timings ===")
    for name, value in sorted(manifest["timings_seconds"].items()):
        logger.info("  %-28s %.2fs", name, value)

    matrix = manifest.get("relationship_matrix")
    if matrix:
        logger.info("=== Relationship matrix ===")
        for pair, counts in matrix.items():
            logger.info("  %-8s %s", pair, counts)

    if args.verify_determinism:
        logger.info("Rebuilding to verify determinism...")
        second = build_enrichment(PROJECT_ROOT)
        if second["digests"] != manifest["digests"]:
            differing = [
                name
                for name, digest in manifest["digests"].items()
                if second["digests"].get(name) != digest
            ]
            logger.error("Non-deterministic artifacts: %s", differing)
            sys.exit(1)
        logger.info("Determinism verified: all %d artifacts byte-identical", len(second["digests"]))

    if args.validate:
        from vedagraph.enrich.validate import validate_artifacts

        result = validate_artifacts(
            read_artifact(PROJECT_ROOT, PARALLELS_FILE),
            read_artifact(PROJECT_ROOT, FORMULAS_FILE),
            read_artifact(PROJECT_ROOT, FORMULA_OCCURRENCES_FILE),
            read_artifact(PROJECT_ROOT, CONCEPTS_FILE),
            read_artifact(PROJECT_ROOT, CONCEPT_ASSERTIONS_FILE),
            read_artifact(PROJECT_ROOT, SEMANTIC_CANDIDATES_FILE),
        )
        logger.info("=== Offline validation: %d checks ===", len(set(result.checks_run)))
        for finding in result.findings:
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
        if not result.passed:
            logger.error("Offline validation FAILED with %d errors", len(result.errors))
            sys.exit(1)
        logger.info("Offline validation PASSED")


if __name__ == "__main__":
    main()
