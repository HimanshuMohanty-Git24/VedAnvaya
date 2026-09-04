"""Build the deterministic lexical and cross-mantra layer over the finished corpus.

Offline: reads only the canonical corpus, the finished traditional knowledge layer, the
commit-pinned VedaWeb book TEI snapshots, and the committed registries. Deterministic:
the build timestamp is injected, so two runs from the same inputs produce byte-identical
output. No language model, embedding or classifier is involved.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

from vedagraph.lexical.build import build_lexical_layer
from vedagraph.lexical.morphology import load_morphology_artifacts
from vedagraph.lexical.output import write_lexical_layer

DEFAULT_CORPUS = Path("data/canonical/rigveda_full_v1")
DEFAULT_KNOWLEDGE = Path("data/knowledge/rigveda_deterministic_v1")
DEFAULT_ARTIFACTS = Path("data/derived/vedaweb_morphology_artifacts.json")
DEFAULT_OUTPUT = Path("data/knowledge/rigveda_lexical_v1")
DEFAULT_TIMESTAMP = datetime(2026, 9, 4, tzinfo=UTC)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--knowledge", type=Path, default=DEFAULT_KNOWLEDGE)
    parser.add_argument("--artifacts", type=Path, default=DEFAULT_ARTIFACTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--registry", type=Path, default=Path("data/registry"))
    args = parser.parse_args()

    artifacts = load_morphology_artifacts(args.artifacts)
    result = build_lexical_layer(
        corpus_dir=args.corpus,
        knowledge_dir=args.knowledge,
        artifacts=artifacts,
        registry_root=args.registry,
    )
    manifest = write_lexical_layer(
        result,
        output_dir=args.output,
        corpus_dir=args.corpus,
        knowledge_dir=args.knowledge,
        artifacts=artifacts,
        built_at=DEFAULT_TIMESTAMP,
        registry_root=args.registry,
    )

    stats = result.stats
    print(f"corpus            {manifest.corpus_version} ({manifest.corpus_passage_count} passages)")
    print(
        f"morphology        {manifest.morphology_annotation_layer_id} @ "
        f"{manifest.morphology_commit_sha[:7]} ({manifest.morphology_license})"
    )
    print(f"tokens            {stats.total_tokens:>7}  lemmas={stats.distinct_lemmas}")
    print(f"morph coverage    {stats.mantras_with_morphology}/{stats.total_mantras} mantras")
    print(
        f"lexical aliases   accepted={stats.accepted_lexical_aliases} "
        f"do_not_match={stats.do_not_match_aliases} candidates={stats.alias_candidates}"
    )
    print(
        f"MENTIONS_ENTITY   {stats.mention_assertions:>7} edges over "
        f"{stats.mantras_with_mentions} mantras "
        f"({stats.mention_token_occurrences} token occurrences)"
    )
    print(f"  ambiguous       {stats.ambiguous_mentions:>7} tokens deliberately unresolved")
    print(f"  no mentions     {stats.mantras_without_mentions:>7} mantras")
    print(f"HAS_COMPONENT     {stats.component_assertions:>7} reviewed edges")
    print(
        f"exact parallels   {stats.exact_parallel_pairs:>7} pairs in "
        f"{stats.exact_parallel_groups} groups (largest {stats.largest_exact_group})"
    )
    print(
        f"near parallels    accepted={stats.accepted_near_parallels} "
        f"candidates={stats.near_parallel_candidates}"
    )
    print(f"co-occurrence     {len(result.co_occurrences):>7} entity pairs")
    print(f"QA                {manifest.qa_status.value}")
    for name, seconds in sorted(result.timings.items()):
        print(f"  {name:<20} {seconds:7.2f}s")
    return 0 if manifest.qa_status.value != "FAILED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
