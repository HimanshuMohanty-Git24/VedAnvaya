"""Build the frozen 448-passage V3.2 set by pure set subtraction."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml

from vedagraph.semantic.codex_direct import canonical_sha256

ROOT = Path(__file__).resolve().parents[1]
HISTORICAL = ROOT / "data/builds/rigveda_semantic_pilot_v1.yaml"
EXCLUDED = ROOT / "data/builds/rigveda_semantic_codex_luna_regression_v1.yaml"
OUTPUT = ROOT / "data/builds/rigveda_semantic_v3_2_user_selected_luna_448_new.yaml"
PASSAGE_RE = re.compile(r"^VG:RV:SAK:M(?:0[1-9]|10):S\d{3}:V\d{3}$")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected YAML mapping: {path}")
    return value


def ids(document: dict[str, Any], *, expected: int, label: str) -> list[str]:
    rows = document.get("mantras")
    if not isinstance(rows, list) or len(rows) != expected:
        raise RuntimeError(f"{label}: expected {expected} mantra rows")
    result = [str(row["passage_key"]) for row in rows]
    if len(set(result)) != expected:
        raise RuntimeError(f"{label}: duplicate passage IDs")
    if any(PASSAGE_RE.fullmatch(item) is None for item in result):
        raise RuntimeError(f"{label}: invalid passage ID")
    return result


def selection_identity(document: dict[str, Any], values: list[str], policy_key: str) -> str:
    policy = str(document.get(policy_key, ""))
    return canonical_sha256({"policy": policy, "ids": sorted(values)})


def main() -> None:
    historical = load(HISTORICAL)
    excluded = load(EXCLUDED)
    historical_ids = ids(historical, expected=508, label="historical 508")
    excluded_ids = ids(excluded, expected=60, label="frozen 60")
    overlap = sorted(set(historical_ids) & set(excluded_ids))
    if len(overlap) != 60:
        raise RuntimeError(f"historical/frozen overlap is {len(overlap)}, expected 60")
    result = sorted(set(historical_ids) - set(excluded_ids))
    if len(result) != 448 or len(set(result)) != 448:
        raise RuntimeError("set difference is not exactly 448 unique IDs")
    invalid = sorted(item for item in result if PASSAGE_RE.fullmatch(item) is None)
    if invalid:
        raise RuntimeError(f"set difference contains invalid IDs: {invalid[:3]}")

    historical_rows = {str(row["passage_key"]): row for row in historical["mantras"]}
    document = {
        "config_version": "rigveda-semantic-v3.2-user-selected-luna-448-new-v1",
        "selection_policy_version": "rigveda-semantic-user-selected-luna-448-new-selection-v1",
        "selection_policy": "SET_DIFFERENCE_ONLY",
        "source_508_selection_path": HISTORICAL.relative_to(ROOT).as_posix(),
        "source_508_selection_identity": str(historical.get("config_version")),
        "source_508_selection_file_sha256": file_sha256(HISTORICAL),
        "source_508_selection_identity_sha256": selection_identity(
            historical, historical_ids, "selection_rule_version"
        ),
        "excluded_60_selection_path": EXCLUDED.relative_to(ROOT).as_posix(),
        "excluded_60_selection_identity": str(excluded.get("config_version")),
        "excluded_60_selection_file_sha256": file_sha256(EXCLUDED),
        "excluded_60_selection_identity_sha256": selection_identity(
            excluded, excluded_ids, "selection_policy_version"
        ),
        "historical_total": 508,
        "excluded_total": 60,
        "overlap_total": len(overlap),
        "result_total": 448,
        "result_unique": len(set(result)),
        "result_invalid_ids": 0,
        "result_frozen_overlap": 0,
        "result_ids_sha256": canonical_sha256(result),
        "mantras": [
            {
                "passage_key": passage_id,
                "citation": str(historical_rows[passage_id]["citation"]),
            }
            for passage_id in result
        ],
    }
    payload = (yaml.safe_dump(document, allow_unicode=True, sort_keys=False) + "\n").encode("utf-8")
    if OUTPUT.exists() and OUTPUT.read_bytes() != payload:
        raise RuntimeError(f"refusing to overwrite changed selection: {OUTPUT}")
    if not OUTPUT.exists():
        OUTPUT.write_bytes(payload)
    print(
        json.dumps(
            {
                "historical_total": 508,
                "excluded_total": 60,
                "overlap": len(overlap),
                "result_total": len(result),
                "unique": len(set(result)),
                "invalid_ids": len(invalid),
                "frozen_overlap": len(set(result) & set(excluded_ids)),
                "result_ids_sha256": document["result_ids_sha256"],
                "output": str(OUTPUT),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
