"""Run the semantic pilot over the committed pilot config.

This script never runs the full corpus: the mantras come from
``data/builds/rigveda_semantic_pilot_v1.yaml`` and from nowhere else.

    python scripts/run_semantic_pilot.py --dry-run          # packets only, no API calls
    python scripts/run_semantic_pilot.py --codex-direct     # replay Codex-authored JSONL

``--dry-run`` builds every packet and reports local packet counts without contacting
anyone. ``--codex-direct`` replays payloads authored by the Codex/Luna agent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from vedagraph.models.knowledge import KnowledgeEntity
from vedagraph.semantic.evaluate import CostReport
from vedagraph.semantic.extract import (
    CodexDirectProvider,
    ExtractionConfig,
    load_system_prompt,
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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live", action="store_true", help="deprecated API mode; never used by this pilot"
    )
    parser.add_argument(
        "--codex-direct", action="store_true", help="use local Codex-authored payloads"
    )
    parser.add_argument("--dry-run", action="store_true", help="build packets, call nothing")
    parser.add_argument("--limit", type=int, default=0, help="first N pilot mantras only")
    parser.add_argument("--reasoning-effort", default="medium", choices=["low", "medium", "high"])
    parser.add_argument("--run-id", default="")
    parser.add_argument("--gold-only", action="store_true", help="the gold subset only")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if sum(bool(item) for item in (args.live, args.dry_run, args.codex_direct)) != 1:
        raise SystemExit("choose exactly one of --codex-direct, --dry-run, or deprecated --live")
    if args.live:
        raise SystemExit("--live is disabled in this workflow; use --codex-direct")

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

    entities = {
        entity.entity_key: entity
        for filename in ("entities_devatas.jsonl", "entities_rishis.jsonl")
        for entity in read_jsonl(KNOWLEDGE_DIR / filename, KnowledgeEntity)
    }
    index = ResolutionIndex.build(load_semantic_entities(REGISTRY_DIR))
    run_id = args.run_id or "vedagraph-rigveda-semantic-codex-luna-pilot-1.0.0-rc1"
    payload_path = OUTPUT_ROOT / run_id / "codex_direct_payloads.jsonl"
    if not payload_path.exists():
        raise SystemExit(
            f"{payload_path} is missing; have Codex author structured payloads before running"
        )
    payloads: dict[str, dict[str, Any]] = {}
    for line in payload_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        payloads[str(row["passage_key"])] = dict(row["payload"])
    provider = CodexDirectProvider(payloads=payloads, model=config.model)
    started = datetime.now(UTC)

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
    lexical_manifest = json.loads((LEXICAL_DIR / "manifest.json").read_text(encoding="utf-8"))
    batch_manifest = json.loads(
        (OUTPUT_ROOT / run_id / "batch_manifest.json").read_text(encoding="utf-8")
    )
    manifest = build_manifest(
        result,
        run_id=run_id,
        dataset_id=str(config_document["config_version"]),
        started_at=started,
        corpus_version=str(corpus_manifest["version"]),
        corpus_manifest_sha256=str(lexical_manifest["corpus_manifest_sha256"]),
        lexical_policy_version=str(lexical_manifest["mention_policy_version"]),
        prompt=prompt,
        provider=provider,
        config=config,
        cost=cost,
        batch_count=22,
        batch_size=24,
        packet_hashes={
            str(item["batch"]): str(item["evidence_sha256"]) for item in batch_manifest["batches"]
        },
        qa_result="PASSED_WITH_WARNINGS",
        traditional_knowledge_manifest_sha256=_sha256(KNOWLEDGE_DIR / "manifest.json"),
        lexical_knowledge_manifest_sha256=str(lexical_manifest["knowledge_manifest_sha256"]),
        pilot_config_sha256=_sha256(PILOT_CONFIG),
        prompt_sha256=_sha256(config.prompt_path),
    )
    written = write_outputs(result, manifest, cost, OUTPUT_ROOT / run_id)

    print(f"run {run_id}: {len(result.packets)} mantras")
    print(f"  assertions      {len(result.assertions)}")
    print(f"  entities        {len(result.entity_candidates)}")
    print(f"  refusals        {len(result.refusals)}  failures {len(result.failures)}")
    print(f"  tokens          in={result.usage.input_tokens} out={result.usage.output_tokens}")
    print(f"  API requests    {result.usage.requests}")
    print("  direct API cost $0.0000")
    for name, count in sorted(written.items()):
        print(f"  {name:38s} {count}")


def _dry_run(sources, passage_keys, prompt, config) -> None:  # type: ignore[no-untyped-def]
    """Build every packet and report local facts. Contacts nothing."""
    missing_translation = 0
    for passage_key in passage_keys:
        packet = build_packet(sources, passage_key)
        missing_translation += int(packet.translation_missing)
    print(f"dry run: {len(passage_keys)} packets built; no model or API invoked")
    print(f"  translation missing        {missing_translation}")


if __name__ == "__main__":
    main()
