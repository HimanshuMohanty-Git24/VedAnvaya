"""Split validated pilot outputs into the deterministic evidence batches."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path("data/semantic/vedagraph-rigveda-semantic-codex-luna-pilot-1.0.0-rc1")


def load_rows(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> None:
    manifest = json.loads((ROOT / "batch_manifest.json").read_text(encoding="utf-8"))
    candidates = load_rows(ROOT / "semantic_candidates.jsonl")
    validations = load_rows(ROOT / "semantic_validation.jsonl")
    by_passage: dict[str, list[dict[str, object]]] = {}
    for row in candidates:
        by_passage.setdefault(str(row["subject_key"]), []).append(row)
    validation_by_id = {str(row["candidate_assertion_id"]): row for row in validations}
    for batch in manifest["batches"]:
        batch_dir = ROOT / "batches" / f"batch_{int(batch['batch']):03d}"
        keys = [str(key) for key in batch["passage_keys"]]
        batch_candidates = [row for key in keys for row in by_passage.get(key, [])]
        batch_validation = [
            validation_by_id[str(row["candidate_assertion_id"])] for row in batch_candidates
        ]
        for name, rows in (
            ("candidates.jsonl", batch_candidates),
            ("validation.jsonl", batch_validation),
        ):
            (batch_dir / name).write_text(
                "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
                encoding="utf-8",
            )
        stats = {
            "batch": int(batch["batch"]),
            "mantra_count": len(keys),
            "candidate_assertions": len(batch_candidates),
            "structurally_valid": sum(
                1 for row in batch_validation if row["status"] != "VALIDATION_REJECTED"
            ),
            "validation_rejected": sum(
                1 for row in batch_validation if row["status"] == "VALIDATION_REJECTED"
            ),
            "needs_review": sum(1 for row in batch_validation if row["status"] == "NEEDS_REVIEW"),
            "auto_accepted": sum(1 for row in batch_validation if row["status"] == "AUTO_ACCEPTED"),
        }
        (batch_dir / "stats.json").write_text(
            json.dumps(stats, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(f"materialized {len(manifest['batches'])} batch output sets")


if __name__ == "__main__":
    main()
