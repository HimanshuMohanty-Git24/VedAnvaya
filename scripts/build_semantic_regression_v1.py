"""Select the bounded CODEX_DIRECT regression set. Identifiers only, no semantic answers.

Membership is derived from the readiness audit rather than chosen: a mantra is in the set
because an audit record names it under B01 or B02, because it is one side of an audited
parallel pair, or because the hash-ordered clean draw picked it. Nothing is selected for
the answer it is expected to produce, which is the only way a regression set can measure
anything.

The clean controls are drawn by hash of the passage key, round-robin across Maṇḍalas, so
the draw is reproducible from this file and is not front-loaded onto the famous hymns.

Writes ``data/builds/rigveda_semantic_codex_luna_regression_v1.yaml``. Selecting the set
is not authorization to run it.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from vedagraph.semantic.codex_direct import EXECUTION_VERSION, REGRESSION_RUN_ID

SELECTION_POLICY_VERSION = "rigveda-semantic-codex-luna-regression-selection-v1"
CONFIG_VERSION = "rigveda-semantic-codex-luna-regression-v1"
AUDIT = Path("docs/manifests/rigveda_semantic_readiness_audit.json")
PILOT_INDEX = Path(
    "data/semantic/vedagraph-rigveda-semantic-luna-v3-508/evidence_packet_index.jsonl"
)
OUTPUT = Path("data/builds/rigveda_semantic_codex_luna_regression_v1.yaml")

#: Clean controls to draw. Small enough to stay inside a bounded regression, large enough
#: that a systematic new defect in ordinary verses would show up rather than hide.
CLEAN_CONTROL_COUNT = 20

STRATUM_REASONS = {
    "B01_RELATION_BINDING": (
        "an audit record names this mantra under B01: a relation or target was bound to "
        "wording elsewhere in the verse"
    ),
    "B02_EVIDENCE_SPAN": (
        "an audit record names this mantra under B02: a stored evidence span was not "
        "boundary-safe, or its anchors were never validated"
    ),
    "PARALLEL_CONTROL": (
        "one side of an audited parallel pair; included so extraction differences between "
        "twins can be read as evidence rather than guessed at"
    ),
    "CLEAN_CONTROL": (
        "hash-drawn from the 508 pilot with no B01 or B02 record; included so the "
        "regression measures ordinary verses too"
    ),
}


def serialize_config_document(document: dict[str, Any]) -> str:
    """Serialize the IDs-only config with a YAML encoder, never hand-built scalars."""
    return yaml.safe_dump(
        document,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
        width=120,
    )


def _mandala(passage_key: str) -> int:
    return int(passage_key.split(":")[3][1:])


def _order_key(passage_key: str) -> str:
    return hashlib.sha256(f"{SELECTION_POLICY_VERSION}|{passage_key}".encode()).hexdigest()


def _citation(passage_key: str) -> str:
    _, _, _, mandala, sukta, mantra = passage_key.split(":")
    return f"RV {int(mandala[1:])}.{int(sukta[1:])}.{int(mantra[1:])}"


def _blocked(records: list[dict[str, object]], blocker: str) -> set[str]:
    keys: set[str] = set()
    for record in records:
        blockers = record.get("blocker_ids") or []
        if blocker in blockers:
            keys.update(str(item) for item in record.get("passage_ids") or [])
    return keys


def main() -> None:
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    audited: list[dict[str, object]] = [
        *audit["gaps"],
        *audit["parallels"],
        *audit["review_queue"],
    ]

    group_a = _blocked(audited, "B01")
    group_b = _blocked(audited, "B02")
    group_b |= {str(item["passage_id"]) for item in audit["anchor_defects"]}
    group_c = {
        str(key)
        for record in audit["parallels"]
        for key in record["passage_ids"]  # type: ignore[union-attr]
    }

    pilot_ids = sorted(
        str(json.loads(line)["passage_key"])
        for line in PILOT_INDEX.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )
    excluded = group_a | group_b | group_c
    pools: dict[int, list[str]] = {}
    for key in pilot_ids:
        if key not in excluded:
            pools.setdefault(_mandala(key), []).append(key)
    for pool in pools.values():
        pool.sort(key=_order_key)

    group_d: list[str] = []
    while len(group_d) < CLEAN_CONTROL_COUNT:
        drawn = False
        for mandala in sorted(pools):
            if len(group_d) == CLEAN_CONTROL_COUNT:
                break
            if pools[mandala]:
                group_d.append(pools[mandala].pop(0))
                drawn = True
        if not drawn:
            break

    # First group to claim a mantra keeps it, so the counts below do not double-count.
    strata: dict[str, str] = {}
    for key in sorted(group_a):
        strata[key] = "B01_RELATION_BINDING"
    for key in sorted(group_b):
        strata.setdefault(key, "B02_EVIDENCE_SPAN")
    for key in sorted(group_c):
        strata.setdefault(key, "PARALLEL_CONTROL")
    for key in sorted(group_d):
        strata.setdefault(key, "CLEAN_CONTROL")

    ordered = sorted(strata)
    selection_hash = hashlib.sha256(
        json.dumps(
            {"policy": SELECTION_POLICY_VERSION, "ids": ordered},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    counts = {
        name: sum(1 for value in strata.values() if value == name) for name in STRATUM_REASONS
    }

    document: dict[str, Any] = {
        "config_version": CONFIG_VERSION,
        "selection_policy_version": SELECTION_POLICY_VERSION,
        "execution_version": EXECUTION_VERSION,
        "run_id": REGRESSION_RUN_ID,
        "runtime": "CODEX_DIRECT",
        "model_requested": "gpt-5.6-luna",
        "reasoning_requested": "high",
        "human_gold_status": "UNANNOTATED",
        "unlocked_predicates": [],
        "candidate_status": "CANDIDATE / NEEDS_REVIEW",
        "selection_hash": selection_hash,
        "mantra_count": len(ordered),
        "stratum_counts": counts,
        "stratum_reasons": STRATUM_REASONS,
        "selection_policy": (
            "Membership is derived from the readiness audit records and a hash-ordered clean "
            "draw. No mantra was selected for the semantic answer it is expected to produce, "
            "and this file carries no semantic content of any kind."
        ),
        "mantras": [
            {"passage_key": key, "citation": _citation(key), "stratum": strata[key]}
            for key in ordered
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(serialize_config_document(document), encoding="utf-8", newline="\n")

    print(f"{len(ordered)} unique mantras written to {OUTPUT}")
    print(f"selection hash {selection_hash}")
    for name, count in sorted(counts.items()):
        print(f"  {name}: {count}")


if __name__ == "__main__":
    main()
