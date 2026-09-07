"""Write the final v3 provenance manifest after reports and comparisons exist."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from vedagraph.semantic.v3 import PROMPT_VERSION

ROOT = Path("data/semantic/vedagraph-rigveda-semantic-luna-v3-120")
CORPUS = Path("data/canonical/rigveda_full_v1/manifest.json")
TRADITIONAL = Path("data/knowledge/rigveda_deterministic_v1/manifest.json")
LEXICAL = Path("data/knowledge/rigveda_lexical_v1/manifest.json")
NORMALIZATION = Path(
    "data/semantic/vedagraph-rigveda-semantic-normalization-v1/normalization_manifest.json"
)
PROMPT = Path("prompts/semantic_extraction_v3.md")
SCHEMA = Path("schemas/semantic_extraction_v3.schema.json")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    seal = json.loads((ROOT / "v3_output_seal.json").read_text(encoding="utf-8"))
    batch_manifest = json.loads((ROOT / "batch_manifest.json").read_text(encoding="utf-8"))
    output_paths = [
        ROOT / name
        for name in (
            "batch_manifest.json",
            "v3_extractions.jsonl",
            "semantic_v3_assertions.jsonl",
            "semantic_v3_objects.jsonl",
            "v3_validation.jsonl",
            "evidence_packet_index.jsonl",
            "predicate_check_trace.jsonl",
            "semantic_v3_run_manifest.json",
            "v3_output_seal.json",
            "v3_vs_v2_structured_comparisons.jsonl",
            "v3_vs_sol_structured_comparisons.jsonl",
            "v3_evaluation_manifest.json",
        )
    ]
    report_names = [
        "RIGVEDA_SEMANTIC_LUNA_V3.md",
        "RIGVEDA_SEMANTIC_LUNA_V2_VS_V3.md",
        "RIGVEDA_SEMANTIC_LUNA_V3_VS_SOL.md",
        "RIGVEDA_SEMANTIC_V3_DISAGREEMENT_DECOMPOSITION.md",
        "RIGVEDA_SEMANTIC_V3_REQUEST_QA.md",
        "RIGVEDA_SEMANTIC_V3_EVENT_QA.md",
        "RIGVEDA_SEMANTIC_V3_TYPE_BOUNDARY_QA.md",
        "RIGVEDA_SEMANTIC_EXPERT_AUDIT_QUEUE_V3.md",
    ]
    output_hashes = {str(path.relative_to(ROOT)): sha256(path) for path in output_paths}
    output_hashes.update(
        {f"docs/reports/{name}": sha256(Path("docs/reports") / name) for name in report_names}
    )
    manifest = {
        "manifest_id": ROOT.name,
        "manifest_version": "rigveda-semantic-luna-v3-manifest-v1",
        "benchmark_config": "data/builds/rigveda_semantic_luna_v2_120.yaml",
        "benchmark_selection": (
            "same sealed 120-mantra semantic benchmark; no additions or substitutions"
        ),
        "selected_id_sha256": seal["selected_ids_sha256"],
        "selected_count": 120,
        "batch_count": 8,
        "batch_size": 15,
        "batch_hashes": batch_manifest["batches"],
        "corpus_manifest_sha256": sha256(CORPUS),
        "traditional_knowledge_manifest_sha256": sha256(TRADITIONAL),
        "lexical_knowledge_manifest_sha256": sha256(LEXICAL),
        "semantic_normalization_manifest_sha256": sha256(NORMALIZATION),
        "v3_schema_sha256": sha256(SCHEMA),
        "v3_prompt_sha256": sha256(PROMPT),
        "prompt_version": PROMPT_VERSION,
        "ontology_version": "rigveda-semantic-ontology-v1",
        "object_schema_version": "rigveda-semantic-object-v1",
        "explicitness_policy_version": "rigveda-semantic-explicitness-v2",
        "comparison_policy_version": "rigveda-semantic-object-comparison-v1",
        "evidence_packet_hashes": seal["packet_hashes"],
        "output_seal": "v3_output_seal.json",
        "output_seal_sha256": sha256(ROOT / "v3_output_seal.json"),
        "output_hashes": output_hashes,
        "model": "gpt-5.6-luna",
        "runtime": "CODEX_DIRECT",
        "reasoning": "high",
        "api_invocation": False,
        "human_gold_status": "UNANNOTATED",
        "unlocked_predicates": [],
        "comparison_sources_opened_after_valid_seal": True,
        "stopped_after_benchmark": True,
        "created_at": datetime.now(UTC).isoformat(),
        "notes": "Model-vs-model comparison only. No human truth labels were created or modified.",
    }
    (ROOT / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "manifest": str(ROOT / "manifest.json"),
                "outputs": len(output_hashes),
                "human_gold_status": "UNANNOTATED",
                "unlocked_predicates": [],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
