#!/usr/bin/env python3
"""Group the Formula artifact into families and write data/enrichment/.

Reads the written enrichment artifacts, never the graph: a family is a function of the same
inputs the Formula layer was, so a second run over unchanged artifacts produces
byte-identical files -- which ``--verify-determinism`` checks by building twice and
comparing digests, and ``--shuffle-input`` checks by building once over a permuted input
so that nothing about the output can depend on row order.

The corpus is read for one thing only: the per-Veda document frequency of every token, which
sizes the two-word removal recommendation. ``--skip-corpus`` leaves that measurement out and
runs the family build alone.

Usage:
    python scripts/build_formula_families.py [--verify-determinism] [--shuffle-input]
                                             [--skip-corpus] [--recommendations N]
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import pathlib
import random
import sys
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

FAMILIES_FILE = "formula_families.jsonl"
FAMILY_MEMBERS_FILE = "formula_family_members.jsonl"

#: Seed for ``--shuffle-input``. Fixed so that a determinism failure is reproducible rather
#: than a thing that happened once on someone's machine.
SHUFFLE_SEED = 20260909


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the VedaGraph formula family layer")
    parser.add_argument(
        "--verify-determinism",
        action="store_true",
        help="Build twice and fail if either artifact digest differs",
    )
    parser.add_argument(
        "--shuffle-input",
        action="store_true",
        help="Also build over a permuted input and fail if the digests differ",
    )
    parser.add_argument(
        "--skip-corpus",
        action="store_true",
        help="Do not read the corpus; omits the two-word removal recommendation",
    )
    parser.add_argument(
        "--recommendations",
        type=int,
        default=15,
        help="How many removal recommendations to log (default 15, 0 for all)",
    )
    return parser.parse_args()


def token_document_shares(project_root: pathlib.Path) -> dict[str, float]:
    """Maximum per-Veda document frequency of every corpus token, on the readable surface.

    Document frequency, not token frequency: the guard the recommendation reuses is expressed
    as a share of a Veda's *mantras*, so the measurement has to be too. Keyed by the rendered
    IAST form rather than the folded one, because that is the surface a Formula row's
    ``normalized`` property is written on and the two have to join.
    """
    from vedagraph.enrich.corpus import VEDAS, load_corpus
    from vedagraph.enrich.surfaces import render_for_display

    corpus = load_corpus(project_root)
    totals = corpus.counts()
    per_veda: dict[str, dict[str, int]] = {veda: {} for veda in VEDAS}
    for mantra in corpus.mantras:
        counts = per_veda[mantra.veda]
        for token in set(mantra.surfaces.script_folded.split()):
            counts[token] = counts.get(token, 0) + 1
    shares: dict[str, float] = {}
    for veda, counts in per_veda.items():
        if not totals.get(veda):
            continue
        for token, count in counts.items():
            readable = render_for_display(token)
            share = count / totals[veda]
            if share > shares.get(readable, 0.0):
                shares[readable] = share
    return shares


def digest(rows: list[dict[str, Any]]) -> str:
    import orjson

    payload = b"".join(orjson.dumps(row, option=orjson.OPT_SORT_KEYS) + b"\n" for row in rows)
    return hashlib.sha256(payload).hexdigest()


def main() -> None:
    args = parse_args()

    from vedagraph.enrich.build import (
        FORMULA_OCCURRENCES_FILE,
        FORMULAS_FILE,
        PARALLELS_FILE,
        RELEASE_DIR,
        read_artifact,
        write_jsonl,
    )
    from vedagraph.enrich.formula_families import (
        build_formula_families,
        recommend_removals,
    )

    formulas = read_artifact(PROJECT_ROOT, FORMULAS_FILE)
    occurrences = read_artifact(PROJECT_ROOT, FORMULA_OCCURRENCES_FILE)
    parallels = read_artifact(PROJECT_ROOT, PARALLELS_FILE)
    if not formulas:
        raise SystemExit(
            f"no formulas in {RELEASE_DIR / FORMULAS_FILE}; "
            "run scripts/build_enrichment.py first"
        )
    logger.info(
        "read %d formulas, %d occurrence rows, %d parallel rows",
        len(formulas),
        len(occurrences),
        len(parallels),
    )

    shares: dict[str, float] = {}
    if not args.skip_corpus:
        shares = token_document_shares(PROJECT_ROOT)
        logger.info("measured document frequency for %d corpus token types", len(shares))

    families, members, report = build_formula_families(formulas, occurrences, parallels, shares)

    if args.verify_determinism or args.shuffle_input:
        again_f, again_m, _ = build_formula_families(formulas, occurrences, parallels, shares)
        for label, left, right in (
            ("families", families, again_f),
            ("members", members, again_m),
        ):
            if digest([row.as_row() for row in left]) != digest([row.as_row() for row in right]):
                raise SystemExit(f"non-deterministic {label}: two runs disagree")
        logger.info("determinism: two runs over the same input agree")

    if args.shuffle_input:
        rng = random.Random(SHUFFLE_SEED)
        shuffled_f, shuffled_o = list(formulas), list(occurrences)
        rng.shuffle(shuffled_f)
        rng.shuffle(shuffled_o)
        permuted_f, permuted_m, _ = build_formula_families(
            shuffled_f, shuffled_o, parallels, shares
        )
        for label, left, right in (
            ("families", families, permuted_f),
            ("members", members, permuted_m),
        ):
            if digest([row.as_row() for row in left]) != digest([row.as_row() for row in right]):
                raise SystemExit(f"input-order dependent {label}: permuted input disagrees")
        logger.info("determinism: a permuted input produces byte-identical output")

    release = PROJECT_ROOT / RELEASE_DIR
    digests = {
        FAMILIES_FILE: write_jsonl(
            release / FAMILIES_FILE, [row.as_row() for row in families]
        ),
        FAMILY_MEMBERS_FILE: write_jsonl(
            release / FAMILY_MEMBERS_FILE, [row.as_row() for row in members]
        ),
    }

    logger.info("=== Run report ===")
    logger.info("  produced   %d families, %d member rows", report.produced, len(members))
    for reason, count in sorted(report.rejected.items()):
        logger.info("  rejected   %-46s %d", reason, count)
    for reason, count in sorted(report.capped.items()):
        logger.info("  capped     %-46s %d", reason, count)
    for name, value in report.notes.items():
        logger.info("  note       %-46s %s", name, value)
    for name, value in digests.items():
        logger.info("  wrote      %-46s %s", name, value)

    if not args.skip_corpus:
        occurrence_counts: dict[str, int] = {}
        for row in occurrences:
            key = str(row["formula_id"])
            occurrence_counts[key] = occurrence_counts.get(key, 0) + 1
        recommendations = recommend_removals(formulas, occurrence_counts, shares)
        limit = args.recommendations or len(recommendations)
        logger.info(
            "=== Removal recommendations (%d formulas, %d occurrence rows) ===",
            len(recommendations),
            sum(item.occurrence_count for item in recommendations),
        )
        logger.info("  rule: %s", recommendations[0].rule if recommendations else "n/a")
        for item in recommendations[:limit]:
            logger.info(
                "  %3dx  %-28s token=%-4s share=%.4f vedas=%s",
                item.mantra_count,
                item.normalized,
                item.grammar_token,
                item.grammar_token_share,
                ",".join(item.vedas),
            )
        if len(recommendations) > limit:
            logger.info("  ... %d more", len(recommendations) - limit)


if __name__ == "__main__":
    main()
