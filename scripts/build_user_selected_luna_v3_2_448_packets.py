"""Build immutable EvidencePackets and 24-passage persistence batches for V3.2."""

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

ROOT = Path(__file__).resolve().parents[1]
SELECTION = ROOT / "data/builds/rigveda_semantic_v3_2_user_selected_luna_448_new.yaml"
RUN_ID = "vedagraph-rigveda-semantic-user-selected-luna-v3.2-448-new-v1"
OUTPUT_ROOT = ROOT / "data/semantic" / RUN_ID
CORPUS_DIR = ROOT / "data/canonical/rigveda_full_v1"
KNOWLEDGE_DIR = ROOT / "data/knowledge/rigveda_deterministic_v1"
LEXICAL_DIR = ROOT / "data/knowledge/rigveda_lexical_v1"
PROMPT = ROOT / "prompts/semantic_extraction_v3.2.md"
SCHEMA = ROOT / "schemas/semantic_extraction_v3.schema.json"
ONTOLOGY = ROOT / "src/vedagraph/semantic/ontology.py"
PASSAGE_RE = re.compile(r"^VG:RV:SAK:M(?:0[1-9]|10):S\d{3}:V\d{3}$")
BATCH_SIZE = 24


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_immutable(path: Path, payload: bytes) -> None:
    if path.exists() and path.read_bytes() != payload:
        raise RuntimeError(f"refusing to overwrite immutable artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(payload)


def packets_bytes(packets: list[EvidencePacket]) -> bytes:
    return "".join(
        json.dumps(item.model_dump(mode="json"), ensure_ascii=False, sort_keys=True) + "\n"
        for item in packets
    ).encode("utf-8")


def index_bytes(packets: list[EvidencePacket]) -> bytes:
    return "".join(
        json.dumps(item.index_row(), ensure_ascii=False, sort_keys=True) + "\n"
        for item in sorted(packets, key=lambda item: item.passage_key)
    ).encode("utf-8")


def main() -> None:
    started = time.perf_counter()
    document = yaml.safe_load(SELECTION.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise RuntimeError("selection is not a mapping")
    rows = document.get("mantras")
    if not isinstance(rows, list) or len(rows) != 448:
        raise RuntimeError("selection must contain exactly 448 passages")
    selected = [str(row["passage_key"]) for row in rows]
    if len(set(selected)) != 448 or any(PASSAGE_RE.fullmatch(item) is None for item in selected):
        raise RuntimeError("selection has duplicate or invalid passage IDs")
    if document.get("selection_policy") != "SET_DIFFERENCE_ONLY":
        raise RuntimeError("selection policy is not SET_DIFFERENCE_ONLY")
    if canonical_sha256(sorted(selected)) != document.get("result_ids_sha256"):
        raise RuntimeError("selection result hash mismatch")

    sources = load_packet_sources(
        corpus_dir=CORPUS_DIR, knowledge_dir=KNOWLEDGE_DIR, lexical_dir=LEXICAL_DIR
    )
    missing = sorted(set(selected) - set(sources.passage_ids))
    if missing:
        raise RuntimeError(f"invalid canonical passage IDs: {missing[:5]}")
    packets = [
        EvidencePacket.model_validate(build_packet(sources, passage_id)) for passage_id in selected
    ]
    if len(packets) != 448 or len({item.passage_key for item in packets}) != 448:
        raise RuntimeError("packet count or uniqueness failure")
    packet_hashes = {item.passage_key: item.input_sha256 for item in packets}

    batches: list[dict[str, Any]] = []
    for offset in range(0, len(packets), BATCH_SIZE):
        batch = packets[offset : offset + BATCH_SIZE]
        number = offset // BATCH_SIZE + 1
        evidence_path = OUTPUT_ROOT / "batches" / f"batch_{number:03d}" / "evidence.jsonl"
        evidence = packets_bytes(batch)
        write_immutable(evidence_path, evidence)
        batches.append(
            {
                "batch": number,
                "batch_size": len(batch),
                "passage_keys": [item.passage_key for item in batch],
                "packet_hashes": {item.passage_key: item.input_sha256 for item in batch},
                "evidence_file": evidence_path.relative_to(ROOT).as_posix(),
                "evidence_sha256": file_sha256(evidence_path),
                "status": "PENDING",
            }
        )

    write_immutable(OUTPUT_ROOT / "packets.jsonl", packets_bytes(packets))
    write_immutable(OUTPUT_ROOT / "packet_index.jsonl", index_bytes(packets))
    manifest = {
        "manifest_version": "rigveda-semantic-user-selected-luna-v3.2-448-new-input-v1",
        "run_id": RUN_ID,
        "execution_version": "rigveda-semantic-execution-v3.2",
        "execution_contract_version": "codex-direct-semantic-v1",
        "selection_path": SELECTION.relative_to(ROOT).as_posix(),
        "selection_sha256": file_sha256(SELECTION),
        "selection_ids_sha256": document["result_ids_sha256"],
        "selected_count": 448,
        "packet_count": len(packets),
        "packet_hashes": packet_hashes,
        "unique_packet_count": len(packet_hashes),
        "duplicate_packet_count": 0,
        "missing_packet_count": 0,
        "packet_validation_failures": 0,
        "semantic_outputs_in_packets": False,
        "human_gold_status": "UNANNOTATED",
        "unlocked_predicates": [],
        "canonical_promotion": False,
        "historical_sources_opened_before_seal": False,
        "batches": batches,
        "batch_size": BATCH_SIZE,
        "batch_count": len(batches),
        "frozen_hashes": {
            "prompt_sha256": file_sha256(PROMPT),
            "schema_sha256": file_sha256(SCHEMA),
            "ontology_sha256": file_sha256(ONTOLOGY),
        },
        "packet_preparation_wall_seconds": round(time.perf_counter() - started, 6),
    }
    manifest_bytes = (
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    write_immutable(OUTPUT_ROOT / "packet_build_manifest.json", manifest_bytes)
    write_immutable(OUTPUT_ROOT / "batch_manifest.json", manifest_bytes)
    freeze = {
        "freeze_version": "rigveda-semantic-user-selected-luna-v3.2-448-new-input-freeze-v1",
        "run_id": RUN_ID,
        "selected_ids": sorted(selected),
        "selected_ids_sha256": document["result_ids_sha256"],
        "selection_sha256": file_sha256(SELECTION),
        "packet_hashes": packet_hashes,
        "frozen_hashes": manifest["frozen_hashes"],
        "human_gold_status": "UNANNOTATED",
        "unlocked_predicates": [],
        "canonical_promotion": False,
        "historical_sources_opened_before_seal": False,
    }
    write_immutable(
        OUTPUT_ROOT / "input_freeze.json",
        (json.dumps(freeze, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )
    print(
        json.dumps(
            {
                "run_id": RUN_ID,
                "expected_packets": 448,
                "built_packets": len(packets),
                "duplicates": 0,
                "missing": 0,
                "batches": len(batches),
                "batch_sizes": [item["batch_size"] for item in batches],
                "status": "PASS",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
