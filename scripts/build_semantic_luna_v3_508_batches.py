"""Build and freeze deterministic EvidencePacket batches for the V3 508 pilot.

This command reads the existing IDs-only semantic pilot selection and deterministic
layers only.  It verifies the frozen 120 V3 contract before writing any 508 batch.
No historical semantic payload is opened here.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

import yaml

from vedagraph.semantic.packet import build_packet, load_packet_sources

CONFIG = Path("data/builds/rigveda_semantic_pilot_v1.yaml")
BENCHMARK_CONFIG = Path("data/builds/rigveda_semantic_luna_v2_120.yaml")
FROZEN_ROOT = Path("data/semantic/vedagraph-rigveda-semantic-luna-v3-120")
ROOT = Path("data/semantic/vedagraph-rigveda-semantic-luna-v3-508")
CORPUS_DIR = Path("data/canonical/rigveda_full_v1")
KNOWLEDGE_DIR = Path("data/knowledge/rigveda_deterministic_v1")
LEXICAL_DIR = Path("data/knowledge/rigveda_lexical_v1")
PROMPT = Path("prompts/semantic_extraction_v3.md")
SCHEMA = Path("schemas/semantic_extraction_v3.schema.json")
BATCH_SIZE = 24


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _selected(document: dict[str, Any]) -> list[str]:
    rows = document.get("mantras")
    if not isinstance(rows, list):
        raise RuntimeError("508 config has no mantra list")
    keys = [str(row["passage_key"]) for row in rows]
    if document.get("pilot_mantra_count") != 508 or len(keys) != 508:
        raise RuntimeError("STOP: existing pilot configuration must contain exactly 508 mantras")
    if len(set(keys)) != 508:
        raise RuntimeError("STOP: existing pilot configuration contains duplicate passage IDs")
    if any(not re.fullmatch(r"VG:RV:SAK:M\d{2}:S\d{3}:V\d{3}", key) for key in keys):
        raise RuntimeError("STOP: malformed passage ID in the existing 508 configuration")
    return keys


def verify_frozen_v3_inputs(sources: Any, selected: list[str]) -> dict[str, Any]:
    """Verify contract hashes and all overlapping packet hashes before extraction."""
    seal_path = FROZEN_ROOT / "v3_output_seal.json"
    if not seal_path.exists():
        raise RuntimeError("STOP: frozen V3 output seal is missing")
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    expected_prompt = str(seal["prompt_sha256"])
    expected_schema = str(seal["schema_sha256"])
    actual_prompt = sha256(PROMPT)
    actual_schema = sha256(SCHEMA)
    if actual_prompt != expected_prompt or actual_schema != expected_schema:
        raise RuntimeError("STOP: frozen V3 prompt or schema hash changed")
    if (
        seal.get("model") != "gpt-5.6-luna"
        or seal.get("runtime") != "CODEX_DIRECT"
        or seal.get("api_invocation") is not False
        or seal.get("reasoning") != "high"
    ):
        raise RuntimeError("STOP: frozen V3 model/runtime/reasoning contract changed")
    benchmark_document: dict[str, Any] = yaml.safe_load(
        BENCHMARK_CONFIG.read_text(encoding="utf-8")
    )
    benchmark_keys = [str(row["passage_key"]) for row in benchmark_document["mantras"]]
    overlap = sorted(set(benchmark_keys) & set(selected))
    if len(benchmark_keys) != 120 or len(overlap) != 120:
        raise RuntimeError("STOP: 508 selection does not embed exactly the frozen 120 benchmark")
    packet_hashes: dict[str, str] = {}
    mismatches: dict[str, dict[str, str]] = {}
    frozen_packet_hashes = {str(key): str(value) for key, value in seal["packet_hashes"].items()}
    for key in overlap:
        packet_hash = build_packet(sources, key).input_sha256
        packet_hashes[key] = packet_hash
        if packet_hash != frozen_packet_hashes.get(key):
            mismatches[key] = {"expected": frozen_packet_hashes.get(key, ""), "actual": packet_hash}
    if mismatches:
        raise RuntimeError(f"STOP: frozen V3 EvidencePacket input changed: {mismatches}")
    if any(key not in sources.passage_ids for key in selected):
        missing = sorted(set(selected) - set(sources.passage_ids))
        raise RuntimeError(f"STOP: invalid passage IDs in 508 config: {missing[:5]}")

    contract_hashes = {
        "prompt": actual_prompt,
        "schema": actual_schema,
        "semantic_ontology": sha256(Path("src/vedagraph/semantic/ontology.py")),
        "object_ontology": sha256(Path("src/vedagraph/semantic/object_ontology.py")),
        "normalization_policy": sha256(Path("src/vedagraph/semantic/normalization.py")),
        "evidence_packet_model": sha256(Path("src/vedagraph/models/semantic.py")),
        "typed_object_model": sha256(Path("src/vedagraph/models/normalization.py")),
        "evidence_packet_schema": sha256(Path("schemas/semantic_evidence_packet.schema.json")),
    }
    return {
        "verified_against": str(seal_path),
        "frozen_v3_seal_sha256": sha256(seal_path),
        "frozen_prompt_sha256": expected_prompt,
        "frozen_schema_sha256": expected_schema,
        "current_contract_hashes": contract_hashes,
        "overlap_count": len(overlap),
        "overlap_packet_hashes": packet_hashes,
        "comparison_sources_opened": False,
        "verification_status": "PASS",
    }


def main() -> None:
    started = time.perf_counter()
    document: dict[str, Any] = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    selected = _selected(document)
    sources = load_packet_sources(
        corpus_dir=CORPUS_DIR, knowledge_dir=KNOWLEDGE_DIR, lexical_dir=LEXICAL_DIR
    )
    frozen = verify_frozen_v3_inputs(sources, selected)

    ROOT.mkdir(parents=True, exist_ok=True)
    batches: list[dict[str, Any]] = []
    all_packet_hashes: dict[str, str] = {}
    for offset in range(0, len(selected), BATCH_SIZE):
        number = offset // BATCH_SIZE + 1
        keys = selected[offset : offset + BATCH_SIZE]
        directory = ROOT / "batches" / f"batch_{number:03d}"
        directory.mkdir(parents=True, exist_ok=True)
        rows: list[str] = []
        packet_hashes: dict[str, str] = {}
        for key in keys:
            packet = build_packet(sources, key)
            rows.append(
                json.dumps(packet.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
            )
            packet_hashes[key] = packet.input_sha256
            all_packet_hashes[key] = packet.input_sha256
        evidence = directory / "evidence.jsonl"
        evidence.write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")
        batches.append(
            {
                "batch": number,
                "batch_size": len(keys),
                "passage_keys": keys,
                "packet_hashes": packet_hashes,
                "evidence_file": str(evidence),
                "evidence_sha256": sha256(evidence),
            }
        )
    if len(all_packet_hashes) != 508:
        raise RuntimeError("STOP: packet preparation did not cover exactly 508 mantras")
    manifest = {
        "run_id": ROOT.name,
        "config_version": str(document["config_version"]),
        "config_sha256": sha256(CONFIG),
        "selected_id_sha256": canonical_hash(selected),
        "selected_ids_sorted_sha256": canonical_hash(sorted(selected)),
        "human_gold_status": "UNANNOTATED",
        "mantra_count": 508,
        "batch_count": len(batches),
        "batch_size": BATCH_SIZE,
        "evidence_packet_preparation_wall_seconds": round(time.perf_counter() - started, 6),
        "batches": batches,
        "frozen_input_verification": frozen,
    }
    (ROOT / "batch_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (ROOT / "input_freeze.json").write_text(
        json.dumps(
            {
                **frozen,
                "selected_id_sha256": canonical_hash(selected),
                "selection_config_sha256": sha256(CONFIG),
                "all_packet_hashes": all_packet_hashes,
                "batch_hashes": {str(row["batch"]): row["evidence_sha256"] for row in batches},
                "evidence_packet_preparation_wall_seconds": manifest[
                    "evidence_packet_preparation_wall_seconds"
                ],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {"mantras": 508, "batches": len(batches), "batch_size": BATCH_SIZE, "status": "PASS"},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
