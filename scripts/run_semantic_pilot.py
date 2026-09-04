"""Run the semantic pilot over the committed pilot config.

This is the only script in the repository that spends money, and it refuses to start
without being told to. It never runs the full corpus: the mantras come from
``data/builds/rigveda_semantic_pilot_v1.yaml`` and from nowhere else.

    python scripts/run_semantic_pilot.py --dry-run          # packets only, no API calls
    python scripts/run_semantic_pilot.py --limit 20 --live  # 20 mantras against Luna
    python scripts/run_semantic_pilot.py --live             # the whole 508-mantra pilot

``--dry-run`` builds every packet, hashes it and reports the input size and projected
cost without contacting anyone. Run it first: it is free, and it is what tells you what
``--live`` will cost before you authorise it.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import yaml

from vedagraph.models.knowledge import KnowledgeEntity
from vedagraph.models.semantic import TokenUsage
from vedagraph.semantic.evaluate import CostReport
from vedagraph.semantic.extract import (
    ExtractionConfig,
    OpenAILunaProvider,
    RecordedProvider,
    load_system_prompt,
    render_user_message,
)
from vedagraph.semantic.packet import build_packet, load_packet_sources
from vedagraph.semantic.registry import ResolutionIndex, load_semantic_entities
from vedagraph.semantic.run import build_manifest, run_pilot, write_outputs
from vedagraph.storage.jsonl import read_jsonl

CORPUS_DIR = Path("data/canonical/rigveda_full_v1")
KNOWLEDGE_DIR = Path("data/knowledge/rigveda_deterministic_v1")
LEXICAL_DIR = Path("data/knowledge/rigveda_lexical_v1")
REGISTRY_DIR = Path("data/registry")
PILOT_CONFIG = Path("data/builds/rigveda_semantic_pilot_v1.yaml")
OUTPUT_ROOT = Path("data/semantic")

#: Rough characters per token for English-and-IAST JSON. Used only by --dry-run, and
#: only to say what a live run would cost. A live run reports the API's real numbers.
CHARS_PER_TOKEN = 3.6


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="call the API and spend money")
    parser.add_argument("--dry-run", action="store_true", help="build packets, call nothing")
    parser.add_argument("--limit", type=int, default=0, help="first N pilot mantras only")
    parser.add_argument("--reasoning-effort", default="medium", choices=["low", "medium", "high"])
    parser.add_argument("--run-id", default="")
    parser.add_argument("--gold-only", action="store_true", help="the gold subset only")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.live == args.dry_run:
        raise SystemExit("choose exactly one of --live and --dry-run")

    config_document = yaml.safe_load(PILOT_CONFIG.read_text(encoding="utf-8"))
    rows = config_document["mantras"]
    if args.gold_only:
        rows = [row for row in rows if row.get("gold")]
    passage_keys = [str(row["passage_key"]) for row in rows]
    if args.limit:
        passage_keys = passage_keys[: args.limit]

    prompt = load_system_prompt()
    config = ExtractionConfig(reasoning_effort=args.reasoning_effort)
    sources = load_packet_sources(
        corpus_dir=CORPUS_DIR, knowledge_dir=KNOWLEDGE_DIR, lexical_dir=LEXICAL_DIR
    )

    if args.dry_run:
        _dry_run(sources, passage_keys, prompt, config)
        return

    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY is not set. A live run needs it; --dry-run does not.")

    entities = {
        entity.entity_key: entity
        for filename in ("entities_devatas.jsonl", "entities_rishis.jsonl")
        for entity in read_jsonl(KNOWLEDGE_DIR / filename, KnowledgeEntity)
    }
    index = ResolutionIndex.build(load_semantic_entities(REGISTRY_DIR))
    provider = OpenAILunaProvider(config)
    started = datetime.now(UTC)
    run_id = args.run_id or f"pilot-{args.reasoning_effort}-{started:%Y%m%dT%H%M%SZ}"

    result = run_pilot(
        passage_keys,
        sources,
        provider,
        prompt,
        config,
        canonical_entity_keys=frozenset(entities),
        registry_index=index,
        # Nothing is unlocked for automatic acceptance until a gold evaluation says so.
        unlocked_predicates=frozenset(),
    )
    cost = CostReport(
        usage=result.usage,
        passage_count=len(result.packets),
        input_usd_per_million=config.input_usd_per_million,
        cached_input_usd_per_million=config.cached_input_usd_per_million,
        output_usd_per_million=config.output_usd_per_million,
    )
    corpus_manifest = json.loads((CORPUS_DIR / "manifest.json").read_text(encoding="utf-8"))
    manifest = build_manifest(
        result,
        run_id=run_id,
        dataset_id=str(config_document["config_version"]),
        started_at=started,
        corpus_version=str(corpus_manifest["corpus_version"]),
        corpus_manifest_sha256=str(corpus_manifest["manifest_sha256"]),
        lexical_policy_version=str(
            json.loads((LEXICAL_DIR / "manifest.json").read_text(encoding="utf-8"))[
                "mention_policy_version"
            ]
        ),
        prompt=prompt,
        provider=provider,
        config=config,
        cost=cost,
    )
    written = write_outputs(result, manifest, cost, OUTPUT_ROOT / run_id)

    print(f"run {run_id}: {len(result.packets)} mantras")
    print(f"  assertions      {len(result.assertions)}")
    print(f"  entities        {len(result.entity_candidates)}")
    print(f"  refusals        {len(result.refusals)}  failures {len(result.failures)}")
    print(f"  tokens          in={result.usage.input_tokens} out={result.usage.output_tokens}")
    print(f"  cost            ${cost.total_cost_usd:.4f}")
    for name, count in sorted(written.items()):
        print(f"  {name:38s} {count}")


def _dry_run(sources, passage_keys, prompt, config) -> None:  # type: ignore[no-untyped-def]
    """Build every packet and price the run that would follow. Contacts nothing."""
    provider = RecordedProvider(payloads={})
    total_chars = 0
    missing_translation = 0
    for passage_key in passage_keys:
        packet = build_packet(sources, passage_key)
        total_chars += len(render_user_message(packet)) + len(prompt.text)
        missing_translation += int(packet.translation_missing)
    estimated_input = int(total_chars / CHARS_PER_TOKEN)
    # Output is the unknown. 900 tokens per reply is a working assumption for planning
    # only, and a live run replaces it with the API's own figure.
    estimated_output = 900 * len(passage_keys)
    cost = CostReport(
        usage=TokenUsage(
            requests=len(passage_keys),
            input_tokens=estimated_input,
            output_tokens=estimated_output,
        ),
        passage_count=len(passage_keys),
        input_usd_per_million=config.input_usd_per_million,
        cached_input_usd_per_million=config.cached_input_usd_per_million,
        output_usd_per_million=config.output_usd_per_million,
    )
    print(f"dry run: {len(passage_keys)} packets built, provider={provider.name}")
    print(f"  translation missing        {missing_translation}")
    print(f"  estimated input tokens     {estimated_input:,}")
    print(f"  assumed output tokens      {estimated_output:,} (900/reply, planning only)")
    print(f"  ESTIMATED pilot cost       ${cost.total_cost_usd:.4f}")
    projected = cost.projected_full_corpus_usd
    print(f"  ESTIMATED full corpus      ${projected:.2f}" if projected else "")
    print("  these are estimates; a live run records the API's actual usage")


if __name__ == "__main__":
    main()
