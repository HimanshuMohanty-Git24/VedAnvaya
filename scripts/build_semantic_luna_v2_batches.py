"""Build exactly eight deterministic 15-packet v2 evidence batches."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

from vedagraph.semantic.packet import build_packet, load_packet_sources

CONFIG = Path("data/builds/rigveda_semantic_luna_v2_120.yaml")
ROOT = Path("data/semantic/vedagraph-rigveda-semantic-luna-v2-120")
CORPUS_DIR = Path("data/canonical/rigveda_full_v1")
KNOWLEDGE_DIR = Path("data/knowledge/rigveda_deterministic_v1")
LEXICAL_DIR = Path("data/knowledge/rigveda_lexical_v1")
BATCH_SIZE = 15


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    keys = [str(row["passage_key"]) for row in config["mantras"]]
    if len(keys) != 120:
        raise RuntimeError("v2 batches must contain exactly 120 benchmark ids")
    sources = load_packet_sources(
        corpus_dir=CORPUS_DIR, knowledge_dir=KNOWLEDGE_DIR, lexical_dir=LEXICAL_DIR
    )
    batches: list[dict[str, object]] = []
    for offset in range(0, len(keys), BATCH_SIZE):
        batch_number = offset // BATCH_SIZE + 1
        selected = keys[offset : offset + BATCH_SIZE]
        directory = ROOT / "batches" / f"batch_{batch_number:03d}"
        directory.mkdir(parents=True, exist_ok=True)
        evidence = directory / "evidence.jsonl"
        with evidence.open("w", encoding="utf-8", newline="\n") as handle:
            for key in selected:
                packet = build_packet(sources, key)
                handle.write(
                    json.dumps(packet.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
                    + "\n"
                )
        batches.append(
            {
                "batch": batch_number,
                "passage_keys": selected,
                "evidence_file": str(evidence),
                "evidence_sha256": sha256(evidence),
                "packet_hashes": {key: build_packet(sources, key).input_sha256 for key in selected},
            }
        )
    manifest = {
        "run_id": "vedagraph-rigveda-semantic-luna-v2-120",
        "config_sha256": sha256(CONFIG),
        "batch_size": BATCH_SIZE,
        "batch_count": len(batches),
        "pilot_mantra_count": len(keys),
        "human_gold_status": "UNANNOTATED",
        "batches": batches,
    }
    (ROOT / "batch_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"built {len(batches)} batches for {len(keys)} mantras")


if __name__ == "__main__":
    main()
