# ruff: noqa: E501
"""Run the sealed-independent Luna semantic v2 extraction over 120 packets only."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from vedagraph.models.knowledge import KnowledgeEntity
from vedagraph.semantic.evaluate import CostReport
from vedagraph.semantic.extract import CodexDirectProvider, ExtractionConfig, load_system_prompt
from vedagraph.semantic.packet import load_packet_sources
from vedagraph.semantic.registry import ResolutionIndex, load_semantic_entities
from vedagraph.semantic.run import build_manifest, run_pilot, write_outputs
from vedagraph.storage.jsonl import read_jsonl

CONFIG = Path("data/builds/rigveda_semantic_luna_v2_120.yaml")
ROOT = Path("data/semantic/vedagraph-rigveda-semantic-luna-v2-120")
CORPUS_DIR = Path("data/canonical/rigveda_full_v1")
KNOWLEDGE_DIR = Path("data/knowledge/rigveda_deterministic_v1")
LEXICAL_DIR = Path("data/knowledge/rigveda_lexical_v1")
REGISTRY_DIR = Path("data/registry")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    config_document = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    keys = [str(row["passage_key"]) for row in config_document["mantras"]]
    if len(keys) != 120:
        raise RuntimeError("v2 run refuses a benchmark other than 120 mantras")
    prompt = load_system_prompt(Path("prompts/semantic_extraction_v2.md"))
    config = ExtractionConfig(reasoning_effort="high", prompt_path=prompt_path())
    sources = load_packet_sources(
        corpus_dir=CORPUS_DIR, knowledge_dir=KNOWLEDGE_DIR, lexical_dir=LEXICAL_DIR
    )
    payloads: dict[str, dict[str, Any]] = {}
    for line in (ROOT / "codex_direct_payloads.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            payloads[str(row["passage_key"])] = dict(row["payload"])
    if set(payloads) != set(keys):
        raise RuntimeError("v2 payload set does not exactly match the 120 benchmark ids")
    entities = {
        entity.entity_key: entity
        for filename in ("entities_devatas.jsonl", "entities_rishis.jsonl")
        for entity in read_jsonl(KNOWLEDGE_DIR / filename, KnowledgeEntity)
    }
    index = ResolutionIndex.build(load_semantic_entities(REGISTRY_DIR))
    provider = CodexDirectProvider(payloads=payloads, model=config.model)
    started = datetime.now(UTC)
    result = run_pilot(
        keys,
        sources,
        provider,
        prompt,
        config,
        canonical_entity_keys=frozenset(entities),
        registry_index=index,
        unlocked_predicates=frozenset(),
    )
    if len(result.packets) != 120 or result.failures or result.refusals or result.parse_errors:
        raise RuntimeError(
            f"v2 extraction incomplete: packets={len(result.packets)} failures={len(result.failures)} "
            f"refusals={len(result.refusals)} parse_errors={len(result.parse_errors)}"
        )
    trace_count = sum(
        1
        for line in (ROOT / "checklist_trace.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    )
    if trace_count != 120:
        raise RuntimeError(f"expected 120 checklist traces, found {trace_count}")
    cost = CostReport(
        usage=result.usage,
        passage_count=120,
        input_usd_per_million=config.input_usd_per_million,
        cached_input_usd_per_million=config.cached_input_usd_per_million,
        output_usd_per_million=config.output_usd_per_million,
    )
    corpus_manifest = json.loads((CORPUS_DIR / "manifest.json").read_text(encoding="utf-8"))
    lexical_manifest = json.loads((LEXICAL_DIR / "manifest.json").read_text(encoding="utf-8"))
    batch_manifest = json.loads((ROOT / "batch_manifest.json").read_text(encoding="utf-8"))
    manifest = build_manifest(
        result,
        run_id="vedagraph-rigveda-semantic-luna-v2-120",
        dataset_id=str(config_document["config_version"]),
        started_at=started,
        corpus_version=str(corpus_manifest["version"]),
        corpus_manifest_sha256=sha256(CORPUS_DIR / "manifest.json"),
        prompt=prompt,
        provider=provider,
        config=config,
        cost=cost,
        lexical_policy_version=str(lexical_manifest["mention_policy_version"]),
        batch_count=8,
        batch_size=15,
        packet_hashes={
            key: value
            for batch in batch_manifest["batches"]
            for key, value in batch["packet_hashes"].items()
        },
        qa_result="PASSED_WITH_WARNINGS" if result.entity_candidates else "PASSED",
        traditional_knowledge_manifest_sha256=sha256(KNOWLEDGE_DIR / "manifest.json"),
        lexical_knowledge_manifest_sha256=str(lexical_manifest["knowledge_manifest_sha256"]),
        pilot_config_sha256=sha256(CONFIG),
        prompt_sha256=sha256(prompt_path()),
    )
    write_outputs(result, manifest, cost, ROOT)
    output_files = sorted(
        path
        for path in ROOT.iterdir()
        if path.is_file() and path.name != "semantic_run_manifest.json"
    )
    manifest.output_hashes = {path.name: sha256(path) for path in output_files}
    manifest.notes = (
        "V2 uses the explicit fourteen-family checklist. Checklist traces are stored "
        "separately from schema-conformant model payloads. NO HUMAN GOLD EXISTS. "
        "Comparison sources were not opened during extraction or sealing."
    )
    (ROOT / "semantic_run_manifest.json").write_text(
        json.dumps(manifest.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "run_id": manifest.run_id,
                "mantras": len(result.packets),
                "assertions": len(result.assertions),
                "entities": len(result.entity_candidates),
                "no_claims": sum(not result.predictions()[key] for key in keys),
                "validation_rejected": sum(
                    1
                    for item in result.assertions
                    if result.validations[item.candidate_assertion_id].status.value
                    == "VALIDATION_REJECTED"
                ),
                "unlocked_predicates": [],
            },
            indent=2,
            sort_keys=True,
        )
    )


def prompt_path() -> Path:
    return Path("prompts/semantic_extraction_v2.md")


if __name__ == "__main__":
    main()
