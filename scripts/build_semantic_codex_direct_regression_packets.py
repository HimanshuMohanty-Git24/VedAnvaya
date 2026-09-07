"""Build the frozen 60 EvidencePackets for the real CODEX_DIRECT regression.

This script reads the IDs-only regression config and deterministic source layers. It does
not author semantic assertions, objects, or model responses.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml

from vedagraph.models.semantic import EvidencePacket
from vedagraph.semantic.packet import build_packet, load_packet_sources

CONFIG = Path("data/builds/rigveda_semantic_codex_luna_regression_v1.yaml")
ROOT = Path("data/semantic/vedagraph-rigveda-semantic-luna-v3.1-regression")
CORPUS_DIR = Path("data/canonical/rigveda_full_v1")
KNOWLEDGE_DIR = Path("data/knowledge/rigveda_deterministic_v1")
LEXICAL_DIR = Path("data/knowledge/rigveda_lexical_v1")
PASSAGE_PATTERN = re.compile(r"VG:RV:SAK:M\d{2}:S\d{3}:V\d{3}")
EXPECTED_COUNTS = {
    "B01_RELATION_BINDING": 24,
    "B02_EVIDENCE_SPAN": 13,
    "PARALLEL_CONTROL": 3,
    "CLEAN_CONTROL": 20,
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_selection_hash(document: dict[str, Any]) -> str:
    ids = sorted(str(row["passage_key"]) for row in document["mantras"])
    return sha256_bytes(
        json.dumps(
            {"policy": document["selection_policy_version"], "ids": ids},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )


def _write_immutable(path: Path, payload: bytes) -> None:
    if path.exists() and path.read_bytes() != payload:
        raise RuntimeError(f"refusing to overwrite different existing file: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def main() -> None:
    document: dict[str, Any] = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    rows = document.get("mantras")
    if not isinstance(rows, list):
        raise RuntimeError("regression config has no mantra list")
    if document.get("mantra_count") != 60 or len(rows) != 60:
        raise RuntimeError("STOP: regression config must contain exactly 60 mantras")

    ids = [str(row["passage_key"]) for row in rows]
    if len(set(ids)) != 60:
        raise RuntimeError("STOP: regression config contains duplicate passage IDs")
    if any(PASSAGE_PATTERN.fullmatch(key) is None for key in ids):
        raise RuntimeError("STOP: regression config contains an invalid passage ID")
    counts = {name: sum(row.get("stratum") == name for row in rows) for name in EXPECTED_COUNTS}
    if counts != EXPECTED_COUNTS:
        raise RuntimeError(f"STOP: unexpected regression strata: {counts}")
    selection_hash = canonical_selection_hash(document)
    if selection_hash != document.get("selection_hash"):
        raise RuntimeError("STOP: regression selection hash does not match the IDs")

    sources = load_packet_sources(
        corpus_dir=CORPUS_DIR,
        knowledge_dir=KNOWLEDGE_DIR,
        lexical_dir=LEXICAL_DIR,
    )
    missing = sorted(set(ids) - set(sources.passage_ids))
    if missing:
        raise RuntimeError(f"STOP: invalid passage IDs in regression config: {missing}")

    packets: list[EvidencePacket] = []
    packet_hashes: dict[str, str] = {}
    for row in rows:
        key = str(row["passage_key"])
        packet = EvidencePacket.model_validate(build_packet(sources, key))
        if packet.passage_key != key or packet.citation != str(row["citation"]):
            raise RuntimeError(f"STOP: packet identity mismatch for {key}")
        packets.append(packet)
        packet_hashes[key] = packet.input_sha256

    packet_lines = "".join(
        json.dumps(packet.model_dump(mode="json"), ensure_ascii=False, sort_keys=True) + "\n"
        for packet in packets
    ).encode("utf-8")
    index_lines = "".join(
        json.dumps(packet.index_row(), ensure_ascii=False, sort_keys=True) + "\n"
        for packet in sorted(packets, key=lambda item: item.passage_key)
    ).encode("utf-8")
    manifest = {
        "run_id": ROOT.name,
        "config_path": CONFIG.as_posix(),
        "config_sha256": sha256_bytes(CONFIG.read_bytes()),
        "canonical_selection_sha256": selection_hash,
        "packet_count": len(packets),
        "packet_hashes": packet_hashes,
        "stratum_counts": counts,
        "duplicates": 0,
        "missing": 0,
        "invalid_passage_ids": 0,
        "packet_validation_failures": 0,
        "semantic_generation": False,
    }
    _write_immutable(ROOT / "packets.jsonl", packet_lines)
    _write_immutable(ROOT / "packet_index.jsonl", index_lines)
    _write_immutable(
        ROOT / "packet_build_manifest.json",
        (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
