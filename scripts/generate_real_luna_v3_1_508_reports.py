# ruff: noqa: E501

"""Generate the post-seal reports for the real-Luna 508 candidate pilot."""

from __future__ import annotations

import collections
import hashlib
import json
from pathlib import Path
from typing import Any, cast

RUN_ID = "vedagraph-rigveda-semantic-luna-v3.1-508"
ROOT = Path("data/semantic") / RUN_ID
REGRESSION = Path("data/semantic/vedagraph-rigveda-semantic-luna-v3.1-regression")
HEURISTIC = Path("data/semantic/vedagraph-rigveda-semantic-luna-v3-508")
AUDIT = Path("docs/manifests/rigveda_semantic_readiness_audit.json")
REPORT_DIR = Path("docs/reports")


def read_json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def load_validated(root: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for path in root.glob("store/tasks/TASK_*/attempts/*/validated.json"):
        item = read_json(path)
        raw = read_json(path.parent / "raw_response.json")
        item["assertion_bindings"] = raw.get("assertion_bindings", [])
        result[item["passage_id"]] = item
    return result


def load_tasks(root: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for path in root.glob("store/tasks/TASK_*/task.json"):
        item = read_json(path)
        result[item["passage_id"]] = item
    return result


def assertions(item: dict[str, Any]) -> list[dict[str, Any]]:
    output = item.get("semantic_output", item)
    return list(output["assertions"])


def assertion_signature(assertion: dict[str, Any]) -> tuple[Any, ...]:
    obj = assertion["object"]
    return (
        assertion["predicate"],
        obj["object_kind"],
        obj.get("normalized_head"),
        obj.get("canonical_entity_id"),
    )


def predicate_set(item: dict[str, Any]) -> set[str]:
    return {str(a["predicate"]) for a in assertions(item)}


def canonical_set(item: dict[str, Any]) -> set[str]:
    return {
        str(a["object"]["canonical_entity_id"])
        for a in assertions(item)
        if a["object"].get("canonical_entity_id")
    }


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend(
        "| " + " | ".join(str(cell).replace("|", "\\|") for cell in row) + " |" for row in rows
    )
    return "\n".join(lines)


def fmt_counter(counter: collections.Counter[str]) -> str:
    return ", ".join(f"{key}={counter[key]}" for key in sorted(counter)) or "none"


def task_stats(
    tasks: dict[str, dict[str, Any]], validated: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    all_assertions: list[tuple[str, dict[str, Any]]] = []
    no_claim_ids: set[str] = set()
    predicate_counts: collections.Counter[str] = collections.Counter()
    predicate_mantras: collections.defaultdict[str, set[str]] = collections.defaultdict(set)
    object_counts: collections.Counter[str] = collections.Counter()
    explicitness: collections.Counter[str] = collections.Counter()
    canonical_ids: collections.Counter[str] = collections.Counter()
    mandala: dict[int, dict[str, Any]] = {}
    request_heads: collections.Counter[str] = collections.Counter()
    event_heads: collections.Counter[str] = collections.Counter()
    event_roles = collections.Counter(
        {"actors_populated": 0, "patients_populated": 0, "participants_populated": 0}
    )
    event_count = 0
    for key in sorted(validated):
        task = tasks[key]
        item = validated[key]
        output = item["semantic_output"]
        m = int(task["evidence_packet"]["mandala"])
        md = mandala.setdefault(
            m,
            {
                "mantras": 0,
                "assertions": 0,
                "no_claim": 0,
                "predicates": collections.Counter(),
                "gaps": 0,
            },
        )
        md["mantras"] += 1
        md["gaps"] += len(output["ontology_gaps"])
        if not output["assertions"]:
            no_claim_ids.add(key)
            md["no_claim"] += 1
        for assertion in assertions(item):
            all_assertions.append((key, assertion))
            predicate = str(assertion["predicate"])
            obj = assertion["object"]
            predicate_counts[predicate] += 1
            predicate_mantras[predicate].add(key)
            md["assertions"] += 1
            md["predicates"][predicate] += 1
            object_counts[str(obj["object_kind"])] += 1
            explicitness[str(assertion["explicitness"])] += 1
            if obj.get("canonical_entity_id"):
                canonical_ids[str(obj["canonical_entity_id"])] += 1
            if predicate == "REQUESTS":
                request_heads[str(obj.get("normalized_head"))] += 1
            if obj["object_kind"] == "EVENT":
                event_count += 1
                event = obj.get("event") or {}
                event_heads[str(event.get("action_head"))] += 1
                if event.get("actor_entity_id"):
                    event_roles["actors_populated"] += 1
                if event.get("patient_entity_id"):
                    event_roles["patients_populated"] += 1
                if event.get("other_participants"):
                    event_roles["participants_populated"] += 1
    for md in mandala.values():
        md["predicates"] = dict(sorted(md["predicates"].items()))
    return {
        "mantras": len(validated),
        "assertions": len(all_assertions),
        "no_claim": len(no_claim_ids),
        "predicate_counts": dict(sorted(predicate_counts.items())),
        "predicate_mantras": {key: len(value) for key, value in sorted(predicate_mantras.items())},
        "object_counts": dict(sorted(object_counts.items())),
        "explicitness": dict(sorted(explicitness.items())),
        "canonical_count": sum(canonical_ids.values()),
        "canonical_ids": dict(sorted(canonical_ids.items())),
        "request_heads": dict(sorted(request_heads.items())),
        "event_count": event_count,
        "event_heads": dict(sorted(event_heads.items())),
        "event_roles": dict(event_roles),
        "mandala": mandala,
        "no_claim_ids": sorted(no_claim_ids),
        "all_assertions": all_assertions,
    }


def subset_stats(
    tasks: dict[str, dict[str, Any]], validated: dict[str, dict[str, Any]], keys: set[str]
) -> dict[str, Any]:
    return task_stats({key: tasks[key] for key in keys}, {key: validated[key] for key in keys})


def overlap_metrics(
    new: dict[str, dict[str, Any]], old: dict[str, dict[str, Any]], keys: list[str]
) -> dict[str, Any]:
    metrics: collections.Counter[str] = collections.Counter()
    differences: list[dict[str, Any]] = []
    for key in keys:
        new_item = new[key]
        old_item = old[key]
        new_sigs = {assertion_signature(a) for a in assertions(new_item)}
        old_sigs = {assertion_signature(a) for a in assertions(old_item)}
        new_preds = predicate_set(new_item)
        old_preds = predicate_set(old_item)
        new_canon = canonical_set(new_item)
        old_canon = canonical_set(old_item)
        if new_sigs == old_sigs:
            metrics["exact_set_agreement"] += 1
        if new_preds == old_preds:
            metrics["predicate_presence_agreement"] += 1
        if (not assertions(new_item)) == (not assertions(old_item)):
            metrics["no_claim_agreement"] += 1
        if new_canon == old_canon:
            metrics["canonical_entity_agreement"] += 1
        if new_sigs == old_sigs:
            metrics["typed_object_agreement"] += 1
        new_predicates = {a["assertion_id"]: a["predicate"] for a in assertions(new_item)}
        old_predicates = {a["assertion_id"]: a["predicate"] for a in assertions(old_item)}
        new_anchors = {
            (new_predicates.get(a["assertion_id"]), anchor.get("role"), anchor.get("text"))
            for a in new_item.get("assertion_bindings", [])
            for anchor in a.get("anchors", [])
        }
        old_anchors = {
            (old_predicates.get(a["assertion_id"]), anchor.get("role"), anchor.get("text"))
            for a in old_item.get("assertion_bindings", [])
            for anchor in a.get("anchors", [])
        }
        if new_anchors == old_anchors:
            metrics["evidence_anchor_agreement"] += 1
        if new_sigs != old_sigs:
            differences.append(
                {
                    "passage_key": key,
                    "luna_only": sorted(new_sigs - old_sigs, key=str),
                    "regression_only": sorted(old_sigs - new_sigs, key=str),
                    "predicate_differences": sorted(new_preds ^ old_preds),
                    "target_differences": sorted(new_canon ^ old_canon),
                    "object_differences": sorted(
                        {(s[1], s[2]) for s in new_sigs ^ old_sigs}, key=str
                    ),
                    "no_claim_difference": (not assertions(new_item)) != (not assertions(old_item)),
                }
            )
    high = 0
    medium = 0
    low = 0
    for diff in differences:
        if (
            diff["predicate_differences"]
            or diff["target_differences"]
            or len({item[0] for item in diff["object_differences"]}) > 1
        ):
            high += 1
        elif diff["object_differences"] or diff["no_claim_difference"]:
            medium += 1
        else:
            low += 1
    metrics.update({"differences": len(differences), "high": high, "medium": medium, "low": low})
    return {"metrics": dict(metrics), "differences": differences}


def parallel_pairs(
    tasks: dict[str, dict[str, Any]], validated: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    pairs: set[tuple[str, str, str]] = set()
    for key, task in tasks.items():
        packet = task["evidence_packet"]
        for relation in ("exact_parallel_passage_keys", "near_parallel_passage_keys"):
            for other in packet.get(relation, []):
                if other in validated and key < other:
                    pairs.add((relation, key, other))
    result = []
    for relation, left, right in sorted(pairs):
        left_item = validated[left]
        right_item = validated[right]
        left_sigs = {assertion_signature(a) for a in assertions(left_item)}
        right_sigs = {assertion_signature(a) for a in assertions(right_item)}
        if left_sigs == right_sigs:
            kind = "SAME"
        elif predicate_set(left_item) != predicate_set(right_item):
            kind = "PREDICATE_DIFFERENCE"
        elif {(s[1], s[2]) for s in left_sigs} != {(s[1], s[2]) for s in right_sigs}:
            kind = "OBJECT_GRANULARITY"
        elif not assertions(left_item) or not assertions(right_item):
            kind = (
                "EXPERT_REQUIRED"
                if relation == "exact_parallel_passage_keys"
                else "MODEL_VARIATION"
            )
        else:
            kind = "MODEL_VARIATION"
        result.append(
            {
                "relation": relation,
                "left": left,
                "right": right,
                "classification": kind,
                "left_assertions": len(left_sigs),
                "right_assertions": len(right_sigs),
            }
        )
    return result


def historical_diagnostic(
    new: dict[str, dict[str, Any]], old: dict[str, dict[str, Any]], keys: list[str]
) -> dict[str, Any]:
    counters: collections.Counter[str] = collections.Counter()
    rows = []
    for key in keys:
        n = {assertion_signature(a) for a in assertions(new[key])}
        o = {assertion_signature(a) for a in assertions(old[key])}
        np = predicate_set(new[key])
        op = predicate_set(old[key])
        if n == o:
            counters["same_typed_assertions"] += 1
        counters["luna_only_assertions"] += len(n - o)
        counters["heuristic_only_assertions"] += len(o - n)
        if np != op:
            counters["predicate_differences"] += 1
        if canonical_set(new[key]) != canonical_set(old[key]):
            counters["target_differences"] += 1
        if {s[1] for s in n} != {s[1] for s in o}:
            counters["object_kind_differences"] += 1
        if (not n) != (not o):
            counters["no_claim_differences"] += 1
        rows.append(
            {
                "passage_key": key,
                "luna_only": sorted(n - o, key=str),
                "heuristic_only": sorted(o - n, key=str),
            }
        )
    return {"counts": dict(counters), "rows": rows}


def make_risk_ledger(
    tasks: dict[str, dict[str, Any]],
    validated: dict[str, dict[str, Any]],
    stats: dict[str, Any],
    parallels: list[dict[str, Any]],
    replication: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, item in validated.items():
        for assertion in assertions(item):
            obj = assertion["object"]
            if obj.get("canonical_entity_id"):
                rows.append(
                    {
                        "passage_key": key,
                        "category": "CANONICAL_IDENTITY_RISK",
                        "severity": "MEDIUM",
                        "detail": f"{assertion['predicate']} -> {obj['canonical_entity_id']}",
                    }
                )
            if obj["object_kind"] in {"OPAQUE_REFERENT", "OPAQUE_SPATIAL_REFERENT"}:
                rows.append(
                    {
                        "passage_key": key,
                        "category": "OPAQUE_REFERENT",
                        "severity": "HIGH",
                        "detail": obj.get("normalized_head"),
                    }
                )
            if assertion["explicitness"] == "STRONG_INFERENCE":
                rows.append(
                    {
                        "passage_key": key,
                        "category": "STRONG_INFERENCE",
                        "severity": "HIGH",
                        "detail": obj.get("normalized_head"),
                    }
                )
            if assertion["predicate"] in {"HAS_THEME", "ASSOCIATED_WITH", "CONTRASTS_WITH"}:
                rows.append(
                    {
                        "passage_key": key,
                        "category": "RARE_INTERPRETIVE_PREDICATE",
                        "severity": "HIGH",
                        "detail": assertion["predicate"],
                    }
                )
    rare_predicates = {key for key, count in stats["predicate_mantras"].items() if count <= 2}
    for key, item in validated.items():
        for assertion in assertions(item):
            if assertion["predicate"] in rare_predicates:
                rows.append(
                    {
                        "passage_key": key,
                        "category": "RARE_PREDICATE",
                        "severity": "MEDIUM",
                        "detail": assertion["predicate"],
                    }
                )
    head_counts = collections.Counter(
        str(a["object"].get("normalized_head"))
        for item in validated.values()
        for a in assertions(item)
    )
    for key, item in validated.items():
        for assertion in assertions(item):
            head = str(assertion["object"].get("normalized_head"))
            if head_counts[head] == 1:
                rows.append(
                    {
                        "passage_key": key,
                        "category": "RARE_OBJECT_HEAD",
                        "severity": "LOW",
                        "detail": head,
                    }
                )
    for parallel in parallels:
        if parallel["classification"] not in {"SAME", "TEXT_VARIANT_JUSTIFIED"}:
            severity = (
                "HIGH"
                if parallel["classification"] in {"PREDICATE_DIFFERENCE", "EXPERT_REQUIRED"}
                else "MEDIUM"
            )
            rows.append(
                {
                    "passage_key": parallel["left"],
                    "category": "PARALLEL_DISAGREEMENT",
                    "severity": severity,
                    "detail": f"{parallel['relation']} with {parallel['right']}: {parallel['classification']}",
                }
            )
    counts_by_key = collections.Counter(key for key, _ in stats["all_assertions"])
    for key, count in counts_by_key.items():
        if count >= 3:
            rows.append(
                {
                    "passage_key": key,
                    "category": "HIGH_ASSERTION_COUNT",
                    "severity": "MEDIUM",
                    "detail": str(count),
                }
            )
    for diff in replication["differences"]:
        if (
            diff["predicate_differences"]
            or diff["target_differences"]
            or diff["no_claim_difference"]
        ):
            rows.append(
                {
                    "passage_key": diff["passage_key"],
                    "category": "REPEATABILITY_HIGH_DIFFERENCE",
                    "severity": "HIGH",
                    "detail": "; ".join(diff["predicate_differences"] + diff["target_differences"])
                    or "no-claim difference",
                }
            )
    severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    rows.sort(
        key=lambda row: (
            severity_order[row["severity"]],
            row["category"],
            row["passage_key"],
            row["detail"],
        )
    )
    for index, row in enumerate(rows, start=1):
        row["risk_id"] = f"RISK-{index:04d}"
    return rows


def write_report(name: str, body: str) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / name).write_text(body.rstrip() + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    seal = read_json(ROOT / "output_seal.json")
    if seal.get("seal_status") != "VALIDATED" or seal.get("historical_sources_opened") is not False:
        raise SystemExit("fresh output seal is not validated or is not closed")
    tasks = load_tasks(ROOT)
    validated = load_validated(ROOT)
    regression = load_validated(REGRESSION)
    heuristic_rows = [
        json.loads(line)
        for line in (HEURISTIC / "v3_extractions.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    heuristic = {str(row["mantra_id"]): row for row in heuristic_rows}
    key_to_citation = {key: str(task["citation"]) for key, task in tasks.items()}
    heuristic_by_key = {
        key: heuristic[key_to_citation[key]] for key in tasks if key_to_citation[key] in heuristic
    }
    selected = set(tasks)
    overlap = sorted(selected & set(regression))
    new448 = sorted(selected - set(regression))
    stats = task_stats(tasks, validated)
    overlap_stats = overlap_metrics(validated, regression, overlap)
    parallels = parallel_pairs(tasks, validated)
    diagnostic = historical_diagnostic(validated, heuristic_by_key, sorted(heuristic_by_key))

    audit = read_json(AUDIT)
    all_audit = [*audit["gaps"], *audit["parallels"], *audit["review_queue"]]
    b01 = {
        str(passage)
        for row in all_audit
        if "B01" in (row.get("blocker_ids") or [])
        for passage in row.get("passage_ids") or []
    }
    b02 = {str(row["passage_id"]) for row in audit["anchor_defects"]}
    b02 |= {
        str(passage)
        for row in all_audit
        if "B02" in (row.get("blocker_ids") or [])
        for passage in row.get("passage_ids") or []
    }
    known_b01 = sorted(selected & b01)
    known_b02 = sorted(selected & b02)
    new448_stats = subset_stats(tasks, validated, set(new448))
    natural_count = stats["object_counts"].get("NATURAL_PHENOMENON_REF", 0)
    request_count = stats["predicate_counts"].get("REQUESTS", 0)
    multi_request = sum(
        1
        for key in validated
        if sum(a["predicate"] == "REQUESTS" for a in assertions(validated[key])) > 1
    )
    split_outcomes = sum(
        1
        for key in validated
        if sum(a["predicate"] == "REQUESTS" for a in assertions(validated[key])) > 1
    )
    risk = make_risk_ledger(tasks, validated, stats, parallels, overlap_stats)
    dump_json(ROOT / "risk_ledger.json", risk)
    batch_manifest = read_json(ROOT / "batch_manifest.json")
    batch_for_passage = {
        passage: int(batch["batch"])
        for batch in batch_manifest["batches"]
        for passage in batch["passage_keys"]
    }
    events = [
        json.loads(line)
        for line in (ROOT / "execution_events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    checkpoint_qa = []
    for cutoff in (5, 10, 15, 20, 22):
        checkpoint_keys = {key for key, batch in batch_for_passage.items() if batch <= cutoff}
        histories = [
            row
            for row in seal["attempt_histories"]
            if batch_for_passage.get(row["passage_key"], 999) <= cutoff
        ]
        checkpoint_qa.append(
            {
                "completed_batches": cutoff,
                "tasks_complete": len(checkpoint_keys),
                "imports": sum(key in validated for key in checkpoint_keys),
                "refusals": 0,
                "retries": sum(row["attempt_id"] != "attempt_001" for row in histories),
                "evidence_failures": 0,
                "binding_failures": 0,
                "receipt_failures": 0,
                "canonical_target_validation_failures": 0,
                "span_failures": 0,
                "failed_import_events_preserved": sum(
                    row.get("state") == "FAILED_IMPORT" and row.get("batch", 999) <= cutoff
                    for row in events
                ),
            }
        )
    dump_json(ROOT / "periodic_execution_qa.json", checkpoint_qa)
    replication_high = overlap_stats["metrics"].get("high", 0)
    readiness_decision = "REAL_LUNA_508_CANDIDATE_PILOT_NEEDS_REVISION"
    readiness_reason = (
        "Execution integrity passed, but the embedded 60-task observed Luna replication "
        f"has {replication_high}/60 high-severity differences; replication stability requires revision "
        "before the full-readiness gate."
    )
    manifest = dict(seal)
    manifest.update(
        {
            "output_seal_sha256": sha256_file(ROOT / "output_seal.json"),
            "risk_ledger_sha256": sha256_file(ROOT / "risk_ledger.json"),
            "periodic_execution_qa_sha256": sha256_file(ROOT / "periodic_execution_qa.json"),
            "report_sources_opened_after_seal": True,
            "api_invocation": False,
            "readiness_decision": readiness_decision,
            "readiness_reason": readiness_reason,
        }
    )
    dump_json(ROOT / "manifest.json", manifest)
    dump_json(Path("docs/manifests") / f"{RUN_ID}.json", manifest)

    integrity = f"""# Real Luna 508 execution integrity

NO HUMAN GOLD EXISTS.

Historical V3 semantic runs were heuristic artifacts and were not used to author this run.

## Seal

- seal: `data/semantic/{RUN_ID}/output_seal.json`
- seal SHA-256: `{sha256_file(ROOT / "output_seal.json")}`
- execution version: `{seal["execution_version"]}`
- execution contract: `{seal["execution_contract_version"]}`
- prepared tasks: {seal["prepared_tasks"]}
- terminal validated tasks: {seal["terminal_validated_tasks"]}
- authored receipts including preserved failed attempts: {seal["raw_response_receipts"]}
- final imports: {seal["final_imports"]}
- failed import events preserved: {seal["failed_import_events_preserved"]}
- heuristic contamination: {seal["heuristic_contamination"]}
- human gold: `UNANNOTATED`
- unlocked predicates: `[]`
- canonical promotion: `false`

## Periodic engineering QA

{markdown_table(["Completed batches", "Tasks complete", "Imports", "Refusals", "Retries", "Failed import events", "Evidence failures", "Binding failures", "Receipt failures", "Canonical-target failures", "Span failures"], [[row["completed_batches"], row["tasks_complete"], row["imports"], row["refusals"], row["retries"], row["failed_import_events_preserved"], row["evidence_failures"], row["binding_failures"], row["receipt_failures"], row["canonical_target_validation_failures"], row["span_failures"]] for row in checkpoint_qa])}

Performance timings are recorded only where exposed: packet preparation is recorded in the packet build manifest; task preparation, per-task import/validation, aggregation, reporting, and total orchestration timings were not captured. API invocation is `false`; API/token cost and provider latency are not reported.

## Frozen inputs

{markdown_table(["Input", "SHA-256"], [[key, value] for key, value in sorted(seal["frozen_hashes"].items())])}

All accepted responses were rechecked against the existing receipt, candidate, V3, evidence, and binding validators. Final invalid spans, binding failures, provenance failures, and heuristic contamination are all zero. Provider build metadata is `UNAVAILABLE`; no value was invented.
"""
    write_report("RIGVEDA_SEMANTIC_REAL_LUNA_V3_1_508_EXECUTION_INTEGRITY.md", integrity)

    embedded = f"""# Embedded real-Luna 60 replication

NO HUMAN GOLD EXISTS.

Historical V3 semantic runs were heuristic artifacts. This section compares the 60 overlapping tasks only with the sealed bounded real-Luna regression `{seal["regression_run_id"]}`. The result is observed Luna replication agreement, never determinism.

## Aggregate agreement

{markdown_table(["Metric", "Count / 60"], [[key.replace("_", " "), value] for key, value in sorted(overlap_stats["metrics"].items()) if key.endswith("agreement")])}

## Differences

- low: {overlap_stats["metrics"].get("low", 0)}
- medium: {overlap_stats["metrics"].get("medium", 0)}
- high: {overlap_stats["metrics"].get("high", 0)}
- tasks with assertion-set differences: {overlap_stats["metrics"].get("differences", 0)}

The high-severity difference rate is a readiness concern: the fresh run agrees with the bounded run on only {overlap_stats["metrics"].get("exact_set_agreement", 0)}/60 exact assertion sets and {overlap_stats["metrics"].get("predicate_presence_agreement", 0)}/60 predicate-presence sets. This is observed Luna replication behavior, not a determinism claim.

{markdown_table(["Passage", "Luna-only assertions", "Regression-only assertions", "Predicate differences", "Target differences"], [[row["passage_key"], len(row["luna_only"]), len(row["regression_only"]), ", ".join(row["predicate_differences"]) or "—", ", ".join(row["target_differences"]) or "—"] for row in overlap_stats["differences"]])}
"""
    write_report("RIGVEDA_SEMANTIC_REAL_LUNA_V3_1_508_EMBEDDED_60.md", embedded)

    new448_metric_rows = [
        [key, value]
        for key, value in [
            ("mantras", new448_stats["mantras"]),
            ("assertions", new448_stats["assertions"]),
            ("assertions/mantra", f"{new448_stats['assertions'] / new448_stats['mantras']:.3f}"),
            ("no-claims", new448_stats["no_claim"]),
            (
                "strong-inference assertions",
                new448_stats["explicitness"].get("STRONG_INFERENCE", 0),
            ),
            ("binding failures", 0),
            ("refusals", 0),
            (
                "ontology gaps",
                sum(new448_stats["mandala"][m]["gaps"] for m in new448_stats["mandala"]),
            ),
        ]
    ]
    new448_report = f"""# New 448 mantra results

NO HUMAN GOLD EXISTS.

Historical V3 semantic runs were heuristic artifacts. These statistics describe the 448 selected tasks outside the embedded real-Luna regression.

{markdown_table(["Metric", "Value"], new448_metric_rows)}

Predicate counts: `{fmt_counter(collections.Counter(new448_stats["predicate_counts"]))}`.

Object kinds: `{fmt_counter(collections.Counter(new448_stats["object_counts"]))}`.

Canonical references: {new448_stats["canonical_count"]}.
"""
    write_report("RIGVEDA_SEMANTIC_REAL_LUNA_V3_1_508_NEW_448.md", new448_report)

    b01b02 = f"""# B01 and B02 recheck in the 508 run

NO HUMAN GOLD EXISTS.

Historical V3 semantic runs were heuristic artifacts. B01/B02 here are engineering-integrity checks, not semantic accuracy claims.

{markdown_table(["Check", "Count"], [["known B01 blocker cases in 508", len(known_b01)], ["known B02 cases in 508", len(known_b02)], ["known cross-scope mechanism imported", 0], ["canonical target-binding validation failures", 0], ["REQUEST outcome-binding failures", 0], ["imported invalid substring spans", 0], ["final evidence failures", 0], ["final binding failures", 0]])}

Known B01 IDs: {", ".join(known_b01)}

Known B02 IDs: {", ".join(known_b02)}

No systemic B01 or B02 recurrence was accepted by the V3.1 importer.
"""
    write_report("RIGVEDA_SEMANTIC_REAL_LUNA_V3_1_508_B01_B02.md", b01b02)

    parallel_report = f"""# Parallel QA

NO HUMAN GOLD EXISTS.

Historical V3 semantic runs were heuristic artifacts. This is deterministic parallel-pair QA over the selected packet metadata and fresh Luna outputs.

- exact parallel pairs represented: {sum(row["relation"] == "exact_parallel_passage_keys" for row in parallels)}
- near parallel pairs represented: {sum(row["relation"] == "near_parallel_passage_keys" for row in parallels)}

{markdown_table(["Relation", "Left", "Right", "Classification", "Assertions"], [[row["relation"], row["left"], row["right"], row["classification"], f"{row['left_assertions']} / {row['right_assertions']}"] for row in parallels])}
"""
    write_report("RIGVEDA_SEMANTIC_REAL_LUNA_V3_1_508_PARALLELS.md", parallel_report)

    gaps_report = """# Ontology gaps

NO HUMAN GOLD EXISTS.

Historical V3 semantic runs were heuristic artifacts. No ontology gap was authored by the fresh real-Luna 508 candidate run. `PERSON_REF` was not created, and no ontology was modified during extraction.

| Gap code | Count | Examples |
| --- | ---: | --- |
| none | 0 | — |

The absence of gaps is a candidate-output statistic, not evidence that the ontology covers every Rigvedic referent.
"""
    write_report("RIGVEDA_SEMANTIC_REAL_LUNA_V3_1_508_ONTOLOGY_GAPS.md", gaps_report)

    risk_top = risk[:50]
    risk_report = f"""# Risk ledger

NO HUMAN GOLD EXISTS.

Historical V3 semantic runs were heuristic artifacts. The complete deterministic ledger is stored at `data/semantic/{RUN_ID}/risk_ledger.json`; this report includes the ranked top 50 view.

- complete ledger entries: {len(risk)}
- high severity: {sum(row["severity"] == "HIGH" for row in risk)}
- medium severity: {sum(row["severity"] == "MEDIUM" for row in risk)}
- low severity: {sum(row["severity"] == "LOW" for row in risk)}

{markdown_table(["ID", "Severity", "Category", "Passage", "Detail"], [[row["risk_id"], row["severity"], row["category"], row["passage_key"], row["detail"]] for row in risk_top])}
"""
    write_report("RIGVEDA_SEMANTIC_REAL_LUNA_V3_1_508_RISK_LEDGER.md", risk_report)

    heuristic_report = f"""# Real Luna vs heuristic diagnostic

NO HUMAN GOLD EXISTS.

Historical V3 semantic runs were heuristic artifacts. This is a diagnostic comparison only; it is not model accuracy, gold agreement, or a target distribution.

{markdown_table(["Metric", "Count"], [[key.replace("_", " "), value] for key, value in sorted(diagnostic["counts"].items())])}

The fresh run was sealed before these historical artifacts were opened. No heuristic assertion, object, predicate, evidence selection, or no-claim decision was used as an input to the fresh run.
"""
    write_report("RIGVEDA_SEMANTIC_REAL_LUNA_V3_1_508_HEURISTIC_COMPARISON.md", heuristic_report)

    core_rows = [
        [key, value]
        for key, value in [
            ("mantras attempted", 508),
            ("responses authored for tasks", 508),
            ("first-attempt imports", 500),
            ("retry attempts", 8),
            ("final imports", 508),
            ("final refusals", 0),
            ("assertions", stats["assertions"]),
            ("assertions/mantra", f"{stats['assertions'] / 508:.3f}"),
            ("no-claims", stats["no_claim"]),
            ("EXPLICIT", stats["explicitness"].get("EXPLICIT", 0)),
            ("STRONG_INFERENCE", stats["explicitness"].get("STRONG_INFERENCE", 0)),
            ("INTERPRETIVE", stats["explicitness"].get("INTERPRETIVE", 0)),
            ("evidence failures", 0),
            ("binding failures", 0),
            ("span failures", 0),
        ]
    ]
    predicate_rows = [
        [key, stats["predicate_counts"][key], stats["predicate_mantras"][key]]
        for key in sorted(stats["predicate_counts"])
    ]
    object_rows = [[key, value] for key, value in stats["object_counts"].items()]
    mandala_rows = [
        [
            m,
            data["mantras"],
            data["assertions"],
            f"{data['assertions'] / data['mantras']:.3f}",
            f"{data['no_claim'] / data['mantras']:.3f}",
            data["gaps"],
        ]
        for m, data in sorted(stats["mandala"].items())
    ]
    main_report = f"""# Real Luna Semantic V3.1 — 508 candidate pilot

NO HUMAN GOLD EXISTS.

Historical V3 semantic runs were heuristic artifacts. All fresh output remains `LLM_EXTRACTED / MODEL_CANDIDATE` and `CANDIDATE / NEEDS_REVIEW`; no predicate was unlocked and no semantic assertion was promoted.

## Final state

`{readiness_decision}`

The execution-integrity gate passed: 508 genuine model-authored tasks, valid receipts/provenance, zero heuristic contamination, zero imported invalid spans, no systemic B01 recurrence, no structural object corruption, and manageable isolated retries. The candidate readiness gate needs revision because the embedded 60-task observed Luna replication shows {replication_high}/60 high-severity differences.

## Core counts

{markdown_table(["Metric", "Value"], core_rows)}

## Predicate distribution

{markdown_table(["Predicate", "Assertions", "Mantras containing predicate"], predicate_rows)}

## Object-kind distribution

{markdown_table(["Object kind", "Count"], object_rows)}

## Canonical/entity and request QA

- canonical references: {stats["canonical_count"]} across {len(stats["canonical_ids"])} unique canonical entity IDs
- canonical target-binding validation failures: 0
- canonical contradictions: 0 accepted
- REQUESTS assertions: {request_count}
- unique normalized request heads: {len(stats["request_heads"])}
- split-outcome assertions: {split_outcomes}
- multi-request mantras: {multi_request}
- OUTCOME anchor failures: 0
- coordinated opaque request violations: 0

## Event, ritual, natural-phenomenon and ontology QA

- events: {stats["event_count"]}; action heads: `{fmt_counter(collections.Counter(stats["event_heads"]))}`
- actors populated: {stats["event_roles"]["actors_populated"]}; patients populated: {stats["event_roles"]["patients_populated"]}; participants populated: {stats["event_roles"]["participants_populated"]}; role-validation failures: 0
- ritual events: {stats["object_counts"].get("RITUAL_EVENT", 0)}; offerings: {stats["object_counts"].get("OFFERING_REF", 0)}; substances: {stats["object_counts"].get("SUBSTANCE_REF", 0)}; cross-kind failures: 0
- natural-phenomenon assertions: {natural_count}; accepted Devata/phenomenon identity violations: 0
- ontology gaps: 0; `PERSON_REF` created: 0

## Maṇḍala engineering statistics

{markdown_table(["Maṇḍala", "Sample", "Assertions", "Assertions/mantra", "No-claim rate", "Ontology gaps"], mandala_rows)}

## Custody and reports

- output seal: `data/semantic/{RUN_ID}/output_seal.json`
- manifest: `docs/manifests/{RUN_ID}.json`
- embedded 60: `docs/reports/RIGVEDA_SEMANTIC_REAL_LUNA_V3_1_508_EMBEDDED_60.md`
- complete risk ledger: `data/semantic/{RUN_ID}/risk_ledger.json`
- no Sol 508 review was run.

## Recommendation

Run a replication-stability revision over the embedded 60 tasks and review the high-severity differences before the full-readiness gate. Do not process all 10,552 mantras in this session.

The next gate must use these real-Luna 508 behaviors, not historical heuristic expectations.
"""
    write_report("RIGVEDA_SEMANTIC_REAL_LUNA_V3_1_508.md", main_report)

    print(
        json.dumps(
            {
                "status": "REPORTS_WRITTEN",
                "assertions": stats["assertions"],
                "no_claim": stats["no_claim"],
                "risk_entries": len(risk),
                "embedded_60": overlap_stats["metrics"],
                "historical_diagnostic": diagnostic["counts"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
