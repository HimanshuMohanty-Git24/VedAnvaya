"""Build the deterministic Rigveda knowledge layer over the finished corpus.

Offline: reads only the canonical corpus, the pinned Anukramaṇī snapshots and the
committed registries. Deterministic: the build timestamp is injected, so two runs from
the same inputs produce byte-identical output.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

from vedagraph.knowledge.build import build_knowledge, load_artifact_index
from vedagraph.knowledge.output import write_knowledge_layer
from vedagraph.knowledge.stats import build_stats

DEFAULT_CORPUS = Path("data/canonical/rigveda_full_v1")
DEFAULT_ARTIFACTS = Path("data/derived/wsc2023_anukramani_artifacts.json")
DEFAULT_OUTPUT = Path("data/knowledge/rigveda_deterministic_v1")
DEFAULT_TIMESTAMP = datetime(2026, 9, 4, tzinfo=UTC)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--artifacts", type=Path, default=DEFAULT_ARTIFACTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--registry", type=Path, default=Path("data/registry"))
    args = parser.parse_args()

    artifacts = load_artifact_index(args.artifacts)
    result = build_knowledge(
        corpus_dir=args.corpus, artifacts=artifacts, registry_root=args.registry
    )
    stats = build_stats(result)
    manifest = write_knowledge_layer(
        result,
        stats,
        output_dir=args.output,
        corpus_dir=args.corpus,
        artifacts=artifacts,
        built_at=DEFAULT_TIMESTAMP,
        registry_root=args.registry,
    )

    print(f"corpus           {manifest.corpus_version} ({manifest.corpus_passage_count} passages)")
    print(f"dataset rows     {stats.dataset_rows} aligned={stats.aligned_rows}")
    print(f"source assertions{stats.source_assertions:>7}")
    print(f"knowledge edges  {stats.knowledge_assertions:>7}")
    for coverage in stats.coverage:
        print(
            f"  {coverage.predicate.value:<12} resolved={coverage.mantras_resolved:>6}"
            f"  unresolved_only={coverage.mantras_unresolved_only:>4}"
            f"  no_claim={coverage.mantras_without_claim:>4}"
            f"  multi={coverage.mantras_with_multiple_entities:>4}"
        )
    print(f"entities         {stats.entity_counts}")
    print(f"unresolved labels{stats.unresolved_label_counts}")
    print(f"QA               {manifest.qa_status.value}")
    return 0 if manifest.qa_status.value != "FAILED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
