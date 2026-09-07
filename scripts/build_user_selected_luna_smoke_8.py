"""Build the new 8-passage V3.2 smoke inputs without semantic authorship.

This script only copies EvidencePackets from the already sealed V3.2 input custody and
prepares immutable task envelopes for the two new run identities. It never reads prior
semantic response files and it never creates predicates, objects, or no-claim decisions.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from vedagraph.models.semantic import EvidencePacket  # noqa: E402
from vedagraph.semantic.codex_direct import (  # noqa: E402
    ExecutionStore,
    canonical_sha256,
    file_sha256,
    load_run_contract,
    prepare_task,
)

SELECTION = ROOT / "data/builds/rigveda_semantic_v3_2_user_selected_luna_smoke_8.yaml"
SOURCE_ROOT = ROOT / "data/semantic/vedagraph-rigveda-semantic-luna-v3.2-stability-60-a/store/tasks"
INPUT_ROOT = ROOT / "data/semantic/vedagraph-rigveda-semantic-user-selected-luna-v3.2-smoke-8-input"
PROMPT = ROOT / "prompts/semantic_extraction_v3.2.md"
SCHEMA = ROOT / "schemas/semantic_extraction_v3.schema.json"
ONTOLOGY = ROOT / "src/vedagraph/semantic/ontology.py"
RUNS = (
    "vedagraph-rigveda-semantic-user-selected-luna-v3.2-smoke-8-a",
    "vedagraph-rigveda-semantic-user-selected-luna-v3.2-smoke-8-b",
)


def read_selection() -> dict[str, object]:
    document = yaml.safe_load(SELECTION.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or document.get("mantra_count") != 8:
        raise RuntimeError("smoke selection must contain exactly 8 passages")
    rows = document.get("mantras")
    if not isinstance(rows, list) or len(rows) != 8:
        raise RuntimeError("smoke selection must contain exactly 8 mantra rows")
    ids = [str(row["passage_key"]) for row in rows if isinstance(row, dict)]
    if len(ids) != 8 or len(set(ids)) != 8:
        raise RuntimeError("smoke selection IDs must be unique")
    return document


def load_source_packets(ids: list[str]) -> dict[str, EvidencePacket]:
    packets: dict[str, EvidencePacket] = {}
    for task_path in SOURCE_ROOT.glob("*/task.json"):
        task = json.loads(task_path.read_text(encoding="utf-8"))
        packet = EvidencePacket.model_validate(task["evidence_packet"])
        if packet.passage_key in ids:
            if packet.passage_key in packets:
                raise RuntimeError(f"duplicate source packet: {packet.passage_key}")
            packets[packet.passage_key] = packet
    if set(packets) != set(ids):
        raise RuntimeError(f"missing source packets: {sorted(set(ids) - set(packets))}")
    return packets


def main() -> None:
    selection = read_selection()
    rows = selection["mantras"]
    assert isinstance(rows, list)
    ids = [str(row["passage_key"]) for row in rows]
    packets = load_source_packets(ids)

    INPUT_ROOT.mkdir(parents=True, exist_ok=True)
    packet_lines = "".join(
        json.dumps(packets[passage_id].model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
        + "\n"
        for passage_id in ids
    )
    packet_path = INPUT_ROOT / "evidence.jsonl"
    index_path = INPUT_ROOT / "evidence_index.json"
    manifest_path = INPUT_ROOT / "input_manifest.json"
    if packet_path.exists() or index_path.exists() or manifest_path.exists():
        raise RuntimeError("refusing to overwrite existing smoke input custody")
    packet_path.write_text(packet_lines, encoding="utf-8")
    index = {
        packet.passage_key: {
            "citation": packet.citation,
            "input_sha256": packet.input_sha256,
        }
        for packet in packets.values()
    }
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    contracts = {}
    for run_id in RUNS:
        contract = load_run_contract(
            run_id=run_id,
            prompt_path=PROMPT,
            schema_path=SCHEMA,
            ontology_path=ONTOLOGY,
            model_requested="gpt-5.6-luna",
            reasoning_requested="high",
            execution_version="rigveda-semantic-execution-v3.2",
        )
        contracts[run_id] = contract.model_dump(mode="json")
        store = ExecutionStore(INPUT_ROOT / run_id / "store")
        for passage_id in ids:
            store.write_task(prepare_task(packets[passage_id], contract))

    manifest = {
        "manifest_version": "rigveda-semantic-user-selected-luna-v3.2-smoke-8-input-v1",
        "selection_path": "data/builds/rigveda_semantic_v3_2_user_selected_luna_smoke_8.yaml",
        "selection_hash": selection["selection_hash"],
        "parent_selection_hash": selection["parent_selection_hash"],
        "evidence_packet_count": len(packets),
        "unique_packet_count": len(set(packets)),
        "missing_packet_count": len(set(ids) - set(packets)),
        "duplicate_packet_count": 0,
        "evidence_jsonl_sha256": file_sha256(packet_path),
        "packet_hashes": {key: packet.input_sha256 for key, packet in sorted(packets.items())},
        "contracts": contracts,
        "semantic_outputs_in_packets": False,
    }
    manifest["manifest_sha256"] = canonical_sha256(manifest)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
