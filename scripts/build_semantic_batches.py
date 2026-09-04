"""Build deterministic small EvidencePacket batches for Codex-direct review.

This script only assembles and hashes packets. It does not call a model, read a key, or
write semantic claims. The batch directory is ignored because packets contain source
text and are the private evidence boundary for the local extraction session.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import yaml

from vedagraph.semantic.packet import build_packet, load_packet_sources

PILOT_CONFIG = Path("data/builds/rigveda_semantic_pilot_v1.yaml")
OUTPUT_ROOT = Path("data/semantic/vedagraph-rigveda-semantic-codex-luna-pilot-1.0.0-rc1")
CORPUS_DIR = Path("data/canonical/rigveda_full_v1")
KNOWLEDGE_DIR = Path("data/knowledge/rigveda_deterministic_v1")
LEXICAL_DIR = Path("data/knowledge/rigveda_lexical_v1")
DEFAULT_BATCH_SIZE = 24


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    args = parser.parse_args()
    if args.batch_size < 1:
        raise SystemExit("--batch-size must be positive")

    config = yaml.safe_load(PILOT_CONFIG.read_text(encoding="utf-8"))
    passage_keys = [str(row["passage_key"]) for row in config["mantras"]]
    sources = load_packet_sources(
        corpus_dir=CORPUS_DIR, knowledge_dir=KNOWLEDGE_DIR, lexical_dir=LEXICAL_DIR
    )
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    batch_rows: list[dict[str, object]] = []
    for offset in range(0, len(passage_keys), args.batch_size):
        keys = passage_keys[offset : offset + args.batch_size]
        batch_number = offset // args.batch_size + 1
        batch_dir = OUTPUT_ROOT / "batches" / f"batch_{batch_number:03d}"
        batch_dir.mkdir(parents=True, exist_ok=True)
        evidence_path = batch_dir / "evidence.jsonl"
        with evidence_path.open("w", encoding="utf-8", newline="\n") as handle:
            for key in keys:
                packet = build_packet(sources, key)
                handle.write(
                    json.dumps(packet.model_dump(mode="json"), ensure_ascii=False, sort_keys=True)
                    + "\n"
                )
        batch_rows.append(
            {
                "batch": batch_number,
                "passage_keys": keys,
                "evidence_file": str(evidence_path),
                "evidence_sha256": _sha256(evidence_path),
            }
        )
    manifest = {
        "dataset_id": str(config["config_version"]),
        "batch_size": args.batch_size,
        "batch_count": len(batch_rows),
        "pilot_mantra_count": len(passage_keys),
        "batches": batch_rows,
    }
    (OUTPUT_ROOT / "batch_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"built {len(batch_rows)} batches for {len(passage_keys)} mantras")


if __name__ == "__main__":
    main()
