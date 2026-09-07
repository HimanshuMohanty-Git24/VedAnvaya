"""Materialise the same 120 benchmark ids used by the independent silver review.

This reads only the existing ids-only pilot selection metadata. It never reads model
outputs, silver annotations, or human-gold judgments.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import yaml

SOURCE = Path("data/builds/rigveda_semantic_pilot_v1.yaml")
OUTPUT = Path("data/builds/rigveda_semantic_luna_v2_120.yaml")


def main() -> None:
    source = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))
    rows = [row for row in source["mantras"] if row.get("gold")]
    if len(rows) != 120:
        raise RuntimeError(f"expected 120 benchmark ids, found {len(rows)}")
    rows = sorted(rows, key=lambda row: str(row["passage_key"]))
    ids_hash = hashlib.sha256(
        "\n".join(str(row["passage_key"]) for row in rows).encode("utf-8")
    ).hexdigest()
    document = {
        "config_version": "rigveda-semantic-luna-v2-120",
        "source_selection_config": "rigveda-semantic-pilot-v1",
        "benchmark_id_sha256": ids_hash,
        "human_gold_status": "UNANNOTATED",
        "mantra_count": len(rows),
        "mantras": [
            {
                "passage_key": str(row["passage_key"]),
                "citation": str(row["citation"]),
                "stratum": str(row["stratum"]),
            }
            for row in rows
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        yaml.safe_dump(document, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    print(f"wrote {OUTPUT} ({len(rows)} ids; {ids_hash})")


if __name__ == "__main__":
    main()
