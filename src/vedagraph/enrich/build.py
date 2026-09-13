"""Run every deterministic enrichment stage and write the artifacts.

The artifacts are the deliverable, not the database. Everything this module writes is
reproducible from the corpus alone, reviewable as a diff, and loadable into an empty Neo4j
without re-running any discovery. That separation is what lets the graph be rebuilt, and
what lets a reviewer check a claim without a database at all.

The model-based semantic layer is not run here. It is a separate, bounded stage with its
own entry point in :mod:`vedagraph.enrich.semantic`, because a build that silently calls a
language model is not a deterministic build no matter how it is documented.
"""

from __future__ import annotations

import logging
import pathlib
import time
from collections.abc import Sequence
from typing import Any

import orjson

from vedagraph.enrich.analytics import (
    concept_by_veda,
    concept_connection_matrix,
    coverage_report,
    cross_veda_matrix,
    devata_chandas,
    devata_concept,
    formula_by_veda,
    formula_sharing_matrix,
    rishi_devata,
)
from vedagraph.enrich.corpus import Corpus, load_corpus
from vedagraph.enrich.provenance import PIPELINE_VERSION, RunReport
from vedagraph.enrich.records import (
    ConceptAssertionRow,
    ConceptRow,
    FormulaOccurrenceRow,
    FormulaRow,
    ParallelRow,
)

logger = logging.getLogger(__name__)

RELEASE_DIR = pathlib.Path("data") / "enrichment" / "vedagraph_enrichment_v1"

PARALLELS_FILE = "cross_veda_parallels.jsonl"
FORMULAS_FILE = "formulas.jsonl"
FORMULA_OCCURRENCES_FILE = "formula_occurrences.jsonl"
CONCEPTS_FILE = "concepts.jsonl"
CONCEPT_ASSERTIONS_FILE = "concept_assertions.jsonl"
SEMANTIC_CANDIDATES_FILE = "semantic_candidates.jsonl"
ANALYTICS_FILE = "analytics.json"
MANIFEST_FILE = "manifest.json"


def write_jsonl(path: pathlib.Path, rows: Sequence[dict[str, Any]]) -> str:
    """Write rows as JSONL with sorted keys, and return the content digest.

    Keys are sorted so a diff between two builds shows changed values rather than changed
    field order, and the digest is returned so the manifest can pin what was written
    without re-reading the file.
    """
    from hashlib import sha256

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = b"".join(orjson.dumps(row, option=orjson.OPT_SORT_KEYS) + b"\n" for row in rows)
    path.write_bytes(payload)
    return sha256(payload).hexdigest()


def _reports(*reports: RunReport) -> list[dict[str, Any]]:
    return [report.as_dict() for report in reports]


def build_enrichment(project_root: pathlib.Path) -> dict[str, Any]:
    """Run the deterministic stages and write every artifact. Returns the manifest."""
    # Imported here rather than at module scope so that a stage that fails to import
    # cannot take down the whole package for callers that only want the record shapes.
    from vedagraph.enrich.concepts import assign_concepts, load_concepts
    from vedagraph.enrich.crossveda import discover_cross_veda_parallels
    from vedagraph.enrich.formulas import discover_formulas

    release = project_root / RELEASE_DIR
    timings: dict[str, float] = {}

    start = time.time()
    corpus = load_corpus(project_root)
    timings["load_corpus"] = round(time.time() - start, 2)
    logger.info("Corpus loaded: %s", corpus.counts())

    start = time.time()
    parallels, parallel_report = discover_cross_veda_parallels(corpus)
    timings["cross_veda_parallels"] = round(time.time() - start, 2)
    logger.info("Cross-Veda parallels: %d", len(parallels))

    start = time.time()
    formulas, occurrences, formula_report = discover_formulas(corpus)
    timings["formulas"] = round(time.time() - start, 2)
    logger.info("Formulas: %d nodes, %d occurrences", len(formulas), len(occurrences))

    start = time.time()
    concepts = list(load_concepts(project_root))
    assertions, concept_report = assign_concepts(corpus, concepts)
    timings["concepts"] = round(time.time() - start, 2)
    logger.info("Concepts: %d nodes, %d assertions", len(concepts), len(assertions))

    digests = {
        PARALLELS_FILE: write_jsonl(release / PARALLELS_FILE, [row.as_row() for row in parallels]),
        FORMULAS_FILE: write_jsonl(release / FORMULAS_FILE, [row.as_row() for row in formulas]),
        FORMULA_OCCURRENCES_FILE: write_jsonl(
            release / FORMULA_OCCURRENCES_FILE, [row.as_row() for row in occurrences]
        ),
        CONCEPTS_FILE: write_jsonl(release / CONCEPTS_FILE, [row.as_row() for row in concepts]),
        CONCEPT_ASSERTIONS_FILE: write_jsonl(
            release / CONCEPT_ASSERTIONS_FILE, [row.as_row() for row in assertions]
        ),
    }

    start = time.time()
    analytics = build_analytics(corpus, parallels, formulas, occurrences, concepts, assertions)
    timings["analytics"] = round(time.time() - start, 2)
    (release / ANALYTICS_FILE).write_bytes(
        orjson.dumps(analytics, option=orjson.OPT_SORT_KEYS | orjson.OPT_INDENT_2)
    )

    manifest: dict[str, Any] = {
        "pipeline_version": PIPELINE_VERSION,
        "corpus_counts": corpus.counts(),
        "counts": {
            "cross_veda_parallels": len(parallels),
            "formulas": len(formulas),
            "formula_occurrences": len(occurrences),
            "concepts": len(concepts),
            "concept_assertions": len(assertions),
        },
        "digests": digests,
        "timings_seconds": timings,
        "stage_reports": _reports(parallel_report, formula_report, concept_report),
    }
    (release / MANIFEST_FILE).write_bytes(
        orjson.dumps(manifest, option=orjson.OPT_SORT_KEYS | orjson.OPT_INDENT_2)
    )
    return manifest


def build_analytics(
    corpus: Corpus,
    parallels: Sequence[ParallelRow],
    formulas: Sequence[FormulaRow],
    occurrences: Sequence[FormulaOccurrenceRow],
    concepts: Sequence[ConceptRow],
    assertions: Sequence[ConceptAssertionRow],
) -> dict[str, Any]:
    """Assemble every derived statistic into one artifact.

    Truncated to the top rows per table. The full Rishi/Devata cross-tabulation is tens of
    thousands of cells and nobody reads it; what a report needs is the head of each table
    plus the totals, and the tables are recomputable from the graph on demand.
    """
    return {
        "relationship_matrix": cross_veda_matrix(parallels),
        "formula_sharing_matrix": formula_sharing_matrix(formulas, occurrences),
        "concept_connection_matrix": concept_connection_matrix(assertions),
        "coverage": coverage_report(corpus, concepts, assertions),
        "rishi_devata_top": [stat.as_row() for stat in rishi_devata(corpus)[:50]],
        "devata_chandas_top": [stat.as_row() for stat in devata_chandas(corpus)[:50]],
        "devata_concept_top": [stat.as_row() for stat in devata_concept(corpus, assertions)[:50]],
        "concept_by_veda": concept_by_veda(assertions)[:150],
        "formula_by_veda": formula_by_veda(formulas)[:100],
    }


def read_artifact(project_root: pathlib.Path, filename: str) -> list[dict[str, Any]]:
    """Read one written artifact back. Missing file yields an empty list."""
    path = project_root / RELEASE_DIR / filename
    if not path.exists():
        return []
    return [orjson.loads(line) for line in path.read_bytes().split(b"\n") if line.strip()]
