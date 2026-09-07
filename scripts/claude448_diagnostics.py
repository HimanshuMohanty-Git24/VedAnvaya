"""Post-seal diagnostics: deterministic parallels and the bounded cross-agent calibration.

NO HUMAN GOLD EXISTS. MODEL SELF-AGREEMENT IS NOT ACCURACY.
CLAUDE OPUS 5 MODEL REVIEW IS NOT HUMAN GOLD.
ALL SEMANTIC OUTPUTS REMAIN CANDIDATE KNOWLEDGE.

Two diagnostics, both run only after the run is sealed.

``parallel`` compares the outputs of passage pairs the deterministic layer already marked
as exact or near parallels. Similarity across a parallel pair is a consistency signal, not
truth: two parallel verses may legitimately be read differently, and equality is never
forced.

``calibration-select`` picks exactly twelve passages, deterministically and stratified,
and assigns each to a *different* author group than the one that authored it.
``calibration-compare`` reports how the replica differs from the original. Replicas never
replace originals and are never imported into the sealed run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from vedagraph.semantic.claude_opus5_v3_2 import (  # noqa: E402
    GROUP_NAMES,
    RUN_ID,
    RUN_ROOT,
    canonical_sha256,
)
from vedagraph.semantic.codex_direct import ModelAuthoredResponse, PreparedTask  # noqa: E402

RUN_DIR = ROOT / RUN_ROOT
TASKS_DIR = RUN_DIR / "store" / "tasks"
CALIBRATION_DIR = RUN_DIR / "calibration"
CALIBRATION_COUNT = 12


def require_seal() -> dict[str, Any]:
    path = RUN_DIR / "output_seal.json"
    if not path.exists():
        raise SystemExit("DIAGNOSTIC_REFUSED: seal the run before running any diagnostic")
    return json.loads(path.read_text(encoding="utf-8"))


def load() -> tuple[dict[str, PreparedTask], dict[str, ModelAuthoredResponse], dict[str, str]]:
    assignment = json.loads(
        (RUN_DIR / "claude_opus5_v3_2_448_agent_assignment.json").read_text(encoding="utf-8")
    )
    group_of = {
        passage_id: name
        for name, row in assignment["groups"].items()
        for passage_id in row["passage_ids"]
    }
    tasks: dict[str, PreparedTask] = {}
    responses: dict[str, ModelAuthoredResponse] = {}
    for path in sorted(TASKS_DIR.glob("TASK_*/task.json")):
        task = PreparedTask.model_validate_json(path.read_text(encoding="utf-8"))
        terminal = [
            item
            for item in sorted((path.parent / "attempts").glob("attempt_*"))
            if (item / "validated.json").exists()
        ]
        if len(terminal) != 1:
            raise SystemExit(
                f"DIAGNOSTIC_REFUSED: {task.passage_id} has no single terminal response"
            )
        tasks[task.passage_id] = task
        responses[task.passage_id] = ModelAuthoredResponse.model_validate_json(
            (terminal[0] / "raw_response.json").read_text(encoding="utf-8")
        )
    return tasks, responses, group_of


def signature(response: ModelAuthoredResponse) -> dict[str, Any]:
    assertions = response.semantic_output.assertions
    return {
        "no_claim": bool(response.semantic_output.no_claim_reasons),
        "count": len(assertions),
        "predicates": Counter(item.predicate.value for item in assertions),
        "object_kinds": Counter(item.object.object_kind.value for item in assertions),
        "canonical_ids": {
            item.object.canonical_entity_id
            for item in assertions
            if item.object.canonical_entity_id
        },
        "heads": {
            (item.predicate.value, (item.object.normalized_head or "").strip().lower())
            for item in assertions
        },
    }


def classify(left: dict[str, Any], right: dict[str, Any]) -> str:
    if left["no_claim"] and right["no_claim"]:
        return "SAME"
    if left["no_claim"] != right["no_claim"]:
        return "DIFFERENT"
    if left["heads"] == right["heads"] and left["predicates"] == right["predicates"]:
        return "SAME"
    shared_predicates = set(left["predicates"]) & set(right["predicates"])
    if not shared_predicates:
        return "DIFFERENT"
    if set(left["predicates"]) != set(right["predicates"]):
        return "PREDICATE_DIFFERENCE"
    if left["object_kinds"] != right["object_kinds"]:
        return "OBJECT_GRANULARITY"
    if left["heads"] & right["heads"]:
        return "PARTIAL"
    return "OBJECT_GRANULARITY"


def classify_calibration(left: dict[str, Any], right: dict[str, Any]) -> str:
    """How an independent replica differs from the original. Never an accuracy verdict.

    ``left`` is the original, ``right`` the replica. A replica that claims a canonical
    target the original did not is the one shape worth escalating, because a canonical
    binding is the only part of the payload that names a registry entity.
    """
    if left["no_claim"] and right["no_claim"]:
        return "SAME"
    if left["no_claim"] != right["no_claim"]:
        return "EMIT_OMIT_VARIANCE"
    if left["heads"] == right["heads"] and left["predicates"] == right["predicates"]:
        return "SAME"
    if left["canonical_ids"] != right["canonical_ids"]:
        return "CANONICAL_TARGET_VARIANCE"
    if set(left["predicates"]) != set(right["predicates"]):
        return "PREDICATE_BOUNDARY"
    if left["object_kinds"] != right["object_kinds"]:
        return "OBJECT_GRANULARITY"
    if left["count"] != right["count"]:
        return "EMIT_OMIT_VARIANCE"
    if left["heads"] & right["heads"]:
        return "EVIDENCE_VARIANCE"
    return "UNRESOLVED"


def cmd_parallel(_: argparse.Namespace) -> dict[str, Any]:
    seal = require_seal()
    tasks, responses, group_of = load()
    selection = set(tasks)
    rows: list[dict[str, Any]] = []
    for kind, attribute in (
        ("EXACT", "exact_parallel_passage_keys"),
        ("NEAR", "near_parallel_passage_keys"),
    ):
        seen: set[tuple[str, str]] = set()
        for passage_id, task in tasks.items():
            for other in getattr(task.evidence_packet, attribute):
                if other not in selection or other == passage_id:
                    continue
                pair = tuple(sorted((passage_id, other)))
                if pair in seen:
                    continue
                seen.add(pair)
                left, right = pair
                if kind == "NEAR" and any(
                    row["pair"] == list(pair) and row["kind"] == "EXACT" for row in rows
                ):
                    continue
                rows.append(
                    {
                        "kind": kind,
                        "pair": list(pair),
                        "citations": [tasks[left].citation, tasks[right].citation],
                        "groups": [group_of[left], group_of[right]],
                        "same_group": group_of[left] == group_of[right],
                        "classification": classify(
                            signature(responses[left]), signature(responses[right])
                        ),
                        "assertion_counts": [
                            len(responses[left].semantic_output.assertions),
                            len(responses[right].semantic_output.assertions),
                        ],
                    }
                )
    report = {
        "manifest_version": "rigveda-semantic-claude-opus5-v3.2-448-parallel-diagnostic-v1",
        "run_id": RUN_ID,
        "seal_sha256": seal["seal_sha256"],
        "ran_after_seal": True,
        "parallel_similarity_is_diagnostic_not_truth": True,
        "equality_forced": False,
        "pairs_evaluated": len(rows),
        "exact_pairs": sum(1 for row in rows if row["kind"] == "EXACT"),
        "near_pairs": sum(1 for row in rows if row["kind"] == "NEAR"),
        "classification_counts": dict(
            sorted(Counter(row["classification"] for row in rows).items())
        ),
        "cross_group_pairs": sum(1 for row in rows if not row["same_group"]),
        "statistical_power": (
            "LOW: the 448 selection was not drawn to maximise parallel coverage, so only a "
            "handful of parallel pairs have both members inside it."
        ),
        "pairs": rows,
    }
    path = ROOT / "docs/manifests/rigveda_semantic_claude_opus5_v3_2_parallel_diagnostic.json"
    path.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return {key: value for key, value in report.items() if key != "pairs"} | {
        "pairs_sample": rows[:8]
    }


def cmd_calibration_select(_: argparse.Namespace) -> dict[str, Any]:
    seal = require_seal()
    tasks, responses, group_of = load()
    groups = sorted({group_of[key] for key in tasks})
    picks: list[dict[str, Any]] = []
    per_group = CALIBRATION_COUNT // len(groups)
    for group in groups:
        # Translatable only: a packet with no translation forces no_claim under the binding
        # contract, so replicating it measures the contract, not the author. This is a
        # packet property, decided before any output was read.
        eligible = sorted(
            key
            for key in tasks
            if group_of[key] == group
            and tasks[key].evidence_packet.translation
            and tasks[key].evidence_packet.translation.text
        )
        ranked = sorted(eligible, key=lambda key: hashlib.sha256(key.encode()).hexdigest())
        for passage_id in ranked[:per_group]:
            replica_group = GROUP_NAMES[(groups.index(group) + 1) % len(groups)]
            picks.append(
                {
                    "passage_id": passage_id,
                    "citation": tasks[passage_id].citation,
                    "original_group": group,
                    "replica_group": replica_group,
                    "original_assertions": len(responses[passage_id].semantic_output.assertions),
                }
            )
    picks.sort(key=lambda row: row["passage_id"])
    manifest = {
        "manifest_version": "rigveda-semantic-claude-opus5-v3.2-448-calibration-12-v1",
        "run_id": RUN_ID,
        "seal_sha256": seal["seal_sha256"],
        "selected_after_seal": True,
        "selection_rule": (
            "two per author group; within a group, the translatable passages ranked by "
            "sha256(passage_id) ascending, lowest two taken; replica group is the next "
            "group letter cyclically, so no replica is authored by the original group"
        ),
        "selection_used_outputs": False,
        "count": len(picks),
        "max_extra_calibration_tasks": CALIBRATION_COUNT,
        "replicas_replace_originals": False,
        "replicas_imported_into_sealed_run": False,
        "selection_sha256": canonical_sha256([row["passage_id"] for row in picks]),
        "passages": picks,
    }
    CALIBRATION_DIR.mkdir(parents=True, exist_ok=True)
    (CALIBRATION_DIR / "calibration_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return {
        "count": len(picks),
        "selection_sha256": manifest["selection_sha256"],
        "assignments": [f"{row['replica_group']}|{row['passage_id']}" for row in picks],
    }


def cmd_calibration_compare(_: argparse.Namespace) -> dict[str, Any]:
    seal = require_seal()
    _tasks, responses, _group_of = load()
    manifest = json.loads(
        (CALIBRATION_DIR / "calibration_manifest.json").read_text(encoding="utf-8")
    )
    rows: list[dict[str, Any]] = []
    for entry in manifest["passages"]:
        passage_id = entry["passage_id"]
        safe = passage_id.replace(":", "_")
        replica_path = CALIBRATION_DIR / entry["replica_group"] / f"{safe}.json"
        if not replica_path.exists():
            rows.append({"passage_id": passage_id, "status": "REPLICA_MISSING"})
            continue
        replica = json.loads(replica_path.read_text(encoding="utf-8"))
        original = responses[passage_id]
        original_sig = signature(original)
        replica_assertions = [] if replica.get("no_claim") else replica.get("assertions", [])
        replica_sig = {
            "no_claim": bool(replica.get("no_claim")),
            "count": len(replica_assertions),
            "predicates": Counter(item["predicate"] for item in replica_assertions),
            "object_kinds": Counter(item["object"]["object_kind"] for item in replica_assertions),
            "canonical_ids": {
                item["object"].get("canonical_entity_id")
                for item in replica_assertions
                if item["object"].get("canonical_entity_id")
            },
            "heads": {
                (item["predicate"], (item["object"].get("normalized_head") or "").strip().lower())
                for item in replica_assertions
            },
        }
        rows.append(
            {
                "passage_id": passage_id,
                "citation": entry["citation"],
                "original_group": entry["original_group"],
                "replica_group": entry["replica_group"],
                "status": "COMPARED",
                "classification": classify(original_sig, replica_sig),
                "disagreement_class": classify_calibration(original_sig, replica_sig),
                "exact_assertion_set_agreement": (
                    original_sig["heads"] == replica_sig["heads"]
                    and original_sig["predicates"] == replica_sig["predicates"]
                ),
                "typed_object_agreement": (
                    original_sig["object_kinds"] == replica_sig["object_kinds"]
                ),
                "original_assertions": original_sig["count"],
                "replica_assertions": replica_sig["count"],
                "assertion_delta": replica_sig["count"] - original_sig["count"],
                "no_claim_agreement": original_sig["no_claim"] == replica_sig["no_claim"],
                "predicate_presence_jaccard": round(
                    len(set(original_sig["predicates"]) & set(replica_sig["predicates"]))
                    / len(set(original_sig["predicates"]) | set(replica_sig["predicates"])),
                    4,
                )
                if (set(original_sig["predicates"]) | set(replica_sig["predicates"]))
                else 1.0,
                "shared_predicates": sorted(
                    set(original_sig["predicates"]) & set(replica_sig["predicates"])
                ),
                "original_only_predicates": sorted(
                    set(original_sig["predicates"]) - set(replica_sig["predicates"])
                ),
                "replica_only_predicates": sorted(
                    set(replica_sig["predicates"]) - set(original_sig["predicates"])
                ),
                "canonical_targets_identical": original_sig["canonical_ids"]
                == replica_sig["canonical_ids"],
                "original_canonical_ids": sorted(original_sig["canonical_ids"]),
                "replica_canonical_ids": sorted(replica_sig["canonical_ids"]),
                "object_kind_identical": original_sig["object_kinds"]
                == replica_sig["object_kinds"],
            }
        )
    compared = [row for row in rows if row["status"] == "COMPARED"]
    densities_original = [row["original_assertions"] for row in compared]
    densities_replica = [row["replica_assertions"] for row in compared]
    report = {
        "manifest_version": "rigveda-semantic-claude-opus5-v3.2-448-calibration-result-v1",
        "run_id": RUN_ID,
        "seal_sha256": seal["seal_sha256"],
        "model_self_agreement_is_accuracy": False,
        "replicas_replace_originals": False,
        "extra_calibration_tasks_used": len(compared),
        "compared": len(compared),
        "missing": len(rows) - len(compared),
        "classification_counts": dict(
            sorted(Counter(row["classification"] for row in compared).items())
        ),
        "disagreement_class_counts": dict(
            sorted(Counter(row["disagreement_class"] for row in compared).items())
        ),
        "exact_assertion_set_agreement": sum(
            1 for row in compared if row["exact_assertion_set_agreement"]
        ),
        "typed_object_agreement": sum(1 for row in compared if row["typed_object_agreement"]),
        "predicate_presence_agreement": sum(
            1 for row in compared if row["predicate_presence_jaccard"] == 1.0
        ),
        "no_claim_agreement": sum(1 for row in compared if row["no_claim_agreement"]),
        "canonical_targets_identical": sum(
            1 for row in compared if row["canonical_targets_identical"]
        ),
        "mean_original_assertions": round(sum(densities_original) / len(compared), 4)
        if compared
        else 0.0,
        "mean_replica_assertions": round(sum(densities_replica) / len(compared), 4)
        if compared
        else 0.0,
        "mean_absolute_assertion_delta": round(
            sum(abs(row["assertion_delta"]) for row in compared) / len(compared), 4
        )
        if compared
        else 0.0,
        "mean_predicate_presence_jaccard": round(
            sum(row["predicate_presence_jaccard"] for row in compared) / len(compared), 4
        )
        if compared
        else 0.0,
        "rows": rows,
    }
    path = ROOT / "docs/manifests/rigveda_semantic_claude_opus5_v3_2_calibration_12.json"
    path.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return {key: value for key, value in report.items() if key != "rows"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("parallel").set_defaults(func=cmd_parallel)
    sub.add_parser("calibration-select").set_defaults(func=cmd_calibration_select)
    sub.add_parser("calibration-compare").set_defaults(func=cmd_calibration_compare)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    print(json.dumps(args.func(args), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
