"""Build the sealed 8 x 15 v3 evidence batches from the existing 120-id config."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from vedagraph.semantic.packet import build_packet, load_packet_sources

CONFIG = Path("data/builds/rigveda_semantic_luna_v2_120.yaml")
ROOT = Path("data/semantic/vedagraph-rigveda-semantic-luna-v3-120")
CORPUS_DIR = Path("data/canonical/rigveda_full_v1")
KNOWLEDGE_DIR = Path("data/knowledge/rigveda_deterministic_v1")
LEXICAL_DIR = Path("data/knowledge/rigveda_lexical_v1")
BATCH_SIZE = 15


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    document: dict[str, Any] = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    keys = [str(row["passage_key"]) for row in document["mantras"]]
    if len(keys) != 120 or len(set(keys)) != 120:
        raise RuntimeError("v3 batches require exactly 120 unique benchmark ids")
    sources = load_packet_sources(
        corpus_dir=CORPUS_DIR, knowledge_dir=KNOWLEDGE_DIR, lexical_dir=LEXICAL_DIR
    )
    batches: list[dict[str, Any]] = []
    for offset in range(0, len(keys), BATCH_SIZE):
        number = offset // BATCH_SIZE + 1
        selected = keys[offset : offset + BATCH_SIZE]
        directory = ROOT / "batches" / f"batch_{number:03d}"
        directory.mkdir(parents=True, exist_ok=True)
        packet_rows: list[str] = []
        packet_hashes: dict[str, str] = {}
        for key in selected:
            packet = build_packet(sources, key)
            packet_rows.append(
                json.dumps(packet.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
            )
            packet_hashes[key] = packet.input_sha256
        evidence_path = directory / "evidence.jsonl"
        evidence_path.write_text("\n".join(packet_rows) + "\n", encoding="utf-8", newline="\n")
        batches.append(
            {
                "batch": number,
                "batch_size": len(selected),
                "passage_keys": selected,
                "packet_hashes": packet_hashes,
                "evidence_file": str(evidence_path),
                "evidence_sha256": sha256(evidence_path),
            }
        )
    manifest = {
        "run_id": "vedagraph-rigveda-semantic-luna-v3-120",
        "config_version": str(document["config_version"]),
        "config_sha256": sha256(CONFIG),
        "selected_id_sha256": hashlib.sha256(
            json.dumps(sorted(keys), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "human_gold_status": "UNANNOTATED",
        "batch_count": len(batches),
        "batch_size": BATCH_SIZE,
        "mantra_count": len(keys),
        "batches": batches,
    }
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "batch_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"batches": len(batches), "mantras": len(keys), "root": str(ROOT)}, indent=2))


if __name__ == "__main__":
    main()
