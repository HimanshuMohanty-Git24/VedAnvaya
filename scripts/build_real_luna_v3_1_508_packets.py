"""Build fresh EvidencePackets for the real-Luna v3.1 508 candidate pilot.

This builder is intentionally identifier- and deterministic-layer-only.  It never opens
historical semantic payloads and never creates a semantic candidate.  The output root is a
new execution identity so the retired heuristic v3-508 custody remains untouched.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

import yaml

from vedagraph.models.semantic import EvidencePacket
from vedagraph.semantic.codex_direct import canonical_sha256
from vedagraph.semantic.packet import build_packet, load_packet_sources

RUN_ID = "vedagraph-rigveda-semantic-luna-v3.1-508"
CONFIG = Path("data/builds/rigveda_semantic_pilot_v1.yaml")
REGRESSION_CONFIG = Path("data/builds/rigveda_semantic_codex_luna_regression_v1.yaml")
REGRESSION_ROOT = Path("data/semantic/vedagraph-rigveda-semantic-luna-v3.1-regression")
REGRESSION_SEAL = Path(
    "docs/manifests/vedagraph_rigveda_semantic_luna_v3_1_regression_output_seal.json"
)
ROOT = Path("data/semantic") / RUN_ID
CORPUS_DIR = Path("data/canonical/rigveda_full_v1")
KNOWLEDGE_DIR = Path("data/knowledge/rigveda_deterministic_v1")
LEXICAL_DIR = Path("data/knowledge/rigveda_lexical_v1")
BATCH_SIZE = 24
PASSAGE_PATTERN = re.compile(r"VG:RV:SAK:M\d{2}:S\d{3}:V\d{3}")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_immutable(path: Path, payload: bytes) -> None:
    if path.exists() and path.read_bytes() != payload:
        raise RuntimeError(f"refusing to overwrite immutable packet artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(payload)


def document(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected mapping in {path}")
    return value


def selected_ids(config: dict[str, Any]) -> list[str]:
    rows = config.get("mantras")
    if not isinstance(rows, list):
        raise RuntimeError("STOP: 508 configuration has no mantra list")
    ids = [str(row["passage_key"]) for row in rows]
    if config.get("pilot_mantra_count") != 508 or len(ids) != 508:
        raise RuntimeError("STOP: expected exactly 508 configured mantras")
    if len(set(ids)) != 508:
        raise RuntimeError("STOP: 508 configuration contains duplicate passage IDs")
    if any(PASSAGE_PATTERN.fullmatch(item) is None for item in ids):
        raise RuntimeError("STOP: 508 configuration contains an invalid passage ID")
    return ids


def regression_ids(config: dict[str, Any]) -> list[str]:
    rows = config.get("mantras")
    if not isinstance(rows, list) or len(rows) != 60:
        raise RuntimeError("STOP: sealed regression selection is not 60 IDs")
    ids = [str(row["passage_key"]) for row in rows]
    if len(set(ids)) != 60 or any(PASSAGE_PATTERN.fullmatch(item) is None for item in ids):
        raise RuntimeError("STOP: malformed or duplicate regression selection")
    return ids


def packet_lines(packets: list[EvidencePacket]) -> bytes:
    return "".join(
        json.dumps(item.model_dump(mode="json"), ensure_ascii=False, sort_keys=True) + "\n"
        for item in packets
    ).encode("utf-8")


def index_lines(packets: list[EvidencePacket]) -> bytes:
    return "".join(
        json.dumps(item.index_row(), ensure_ascii=False, sort_keys=True) + "\n"
        for item in sorted(packets, key=lambda item: item.passage_key)
    ).encode("utf-8")


def main() -> None:
    started = time.perf_counter()
    config = document(CONFIG)
    selected = selected_ids(config)
    regression = document(REGRESSION_CONFIG)
    regression_selected = regression_ids(regression)
    overlap = sorted(set(selected) & set(regression_selected))
    if overlap != sorted(regression_selected):
        raise RuntimeError("STOP: the 508 selection does not embed all 60 regression IDs")

    regression_manifest = json.loads(
        (REGRESSION_ROOT / "packet_build_manifest.json").read_text(encoding="utf-8")
    )
    regression_packet_hashes = {
        str(key): str(value) for key, value in regression_manifest["packet_hashes"].items()
    }
    if set(regression_packet_hashes) != set(regression_selected):
        raise RuntimeError("STOP: regression packet manifest does not cover its 60 IDs")

    regression_seal = json.loads(REGRESSION_SEAL.read_text(encoding="utf-8"))
    frozen_hashes = dict(regression_seal["frozen_hashes"])
    frozen_paths = {
        "prompt_sha256": Path("prompts/semantic_extraction_v3.md"),
        "schema_sha256": Path("schemas/semantic_extraction_v3.schema.json"),
        "semantic_ontology_sha256": Path("src/vedagraph/semantic/ontology.py"),
        "object_ontology_sha256": Path("src/vedagraph/semantic/object_ontology.py"),
        "span_validator_sha256": Path("src/vedagraph/semantic/spans.py"),
        "evidence_validator_sha256": Path("src/vedagraph/semantic/evidence.py"),
        "execution_contract_sha256": Path("src/vedagraph/semantic/codex_direct.py"),
    }
    current_hashes = {name: file_sha256(path) for name, path in frozen_paths.items()}
    if current_hashes != frozen_hashes:
        raise RuntimeError("STOP: v3.1 frozen execution input hash drift detected")

    sources = load_packet_sources(
        corpus_dir=CORPUS_DIR, knowledge_dir=KNOWLEDGE_DIR, lexical_dir=LEXICAL_DIR
    )
    missing = sorted(set(selected) - set(sources.passage_ids))
    if missing:
        raise RuntimeError(f"STOP: invalid canonical passage IDs: {missing[:5]}")

    packets = [
        EvidencePacket.model_validate(build_packet(sources, passage_id)) for passage_id in selected
    ]
    if len(packets) != 508:
        raise RuntimeError("STOP: packet build did not produce exactly 508 packets")
    packet_ids = [item.passage_key for item in packets]
    if len(set(packet_ids)) != 508:
        raise RuntimeError("STOP: packet build contains duplicate passage IDs")
    if any(item.passage_key not in selected for item in packets):
        raise RuntimeError("STOP: packet build contains an unselected passage")
    packet_hashes = {item.passage_key: item.input_sha256 for item in packets}
    if len(packet_hashes) != 508:
        raise RuntimeError("STOP: packet hash index is incomplete")
    packet_mismatches = {
        key: {"expected": regression_packet_hashes[key], "actual": packet_hashes[key]}
        for key in overlap
        if packet_hashes[key] != regression_packet_hashes[key]
    }
    if packet_mismatches:
        raise RuntimeError(f"STOP: regression-overlap packet hash drift: {packet_mismatches}")

    batches: list[dict[str, Any]] = []
    for offset in range(0, len(packets), BATCH_SIZE):
        number = offset // BATCH_SIZE + 1
        batch_packets = packets[offset : offset + BATCH_SIZE]
        batch_dir = ROOT / "batches" / f"batch_{number:03d}"
        evidence_path = batch_dir / "evidence.jsonl"
        evidence = packet_lines(batch_packets)
        write_immutable(evidence_path, evidence)
        batches.append(
            {
                "batch": number,
                "batch_size": len(batch_packets),
                "passage_keys": [item.passage_key for item in batch_packets],
                "packet_hashes": {item.passage_key: item.input_sha256 for item in batch_packets},
                "evidence_file": evidence_path.as_posix(),
                "evidence_sha256": file_sha256(evidence_path),
                "status": "PENDING",
            }
        )

    packet_path = ROOT / "packets.jsonl"
    index_path = ROOT / "packet_index.jsonl"
    write_immutable(packet_path, packet_lines(packets))
    write_immutable(index_path, index_lines(packets))
    manifest = {
        "run_id": RUN_ID,
        "execution_version": "rigveda-semantic-execution-v3.1",
        "execution_contract_version": "codex-direct-semantic-v1",
        "config_path": CONFIG.as_posix(),
        "config_sha256": file_sha256(CONFIG),
        "selected_count": 508,
        "selected_ids_sha256": canonical_sha256(sorted(selected)),
        "packet_count": len(packets),
        "packet_hashes": packet_hashes,
        "duplicates": 0,
        "missing": 0,
        "invalid_passage_ids": 0,
        "packet_validation_failures": 0,
        "semantic_generation": False,
        "human_gold_status": "UNANNOTATED",
        "unlocked_predicates": [],
        "canonical_promotion": False,
        "historical_sources_opened": False,
        "regression_overlap_count": len(overlap),
        "regression_overlap_packet_hashes_match": True,
        "frozen_hashes": current_hashes,
        "batches": batches,
        "packet_preparation_wall_seconds": round(time.perf_counter() - started, 6),
    }
    write_immutable(
        ROOT / "packet_build_manifest.json",
        (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )
    write_immutable(
        ROOT / "batch_manifest.json",
        (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )
    freeze = {
        "run_id": RUN_ID,
        "selected_ids": sorted(selected),
        "selected_ids_sha256": canonical_sha256(sorted(selected)),
        "selection_config_sha256": file_sha256(CONFIG),
        "packet_hashes": packet_hashes,
        "frozen_hashes": current_hashes,
        "regression_run_id": regression_seal["run_id"],
        "regression_seal_sha256": file_sha256(REGRESSION_SEAL),
        "regression_overlap_ids": overlap,
        "regression_overlap_packet_hashes_match": True,
        "human_gold_status": "UNANNOTATED",
        "unlocked_predicates": [],
        "canonical_promotion": False,
        "historical_sources_opened": False,
    }
    write_immutable(
        ROOT / "input_freeze.json",
        (json.dumps(freeze, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )
    print(
        json.dumps(
            {
                "run_id": RUN_ID,
                "expected": 508,
                "built": len(packets),
                "duplicates": 0,
                "missing": 0,
                "validation_failures": 0,
                "batches": len(batches),
                "batch_sizes": [item["batch_size"] for item in batches],
                "regression_overlap": len(overlap),
                "regression_packet_hash_mismatches": 0,
                "status": "PASS",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
