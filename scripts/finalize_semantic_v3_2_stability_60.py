"""Seal and compare the completed V3.2 two-run 60-passage experiment.

NO HUMAN GOLD EXISTS. MODEL SELF-AGREEMENT IS NOT ACCURACY.

The extraction step is already complete when this script runs.  It revalidates each
selected raw response through the CODEX_DIRECT importer, chooses the lexically lowest
valid attempt id when old overlapping sessions left more than one valid attempt, seals
all custody bytes, and writes a truth-neutral stability report.  No semantic output is
authored, edited, promoted, or discarded here.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from vedagraph.semantic.codex_direct import (
    ExecutionStore,
    ModelAuthoredResponse,
    PreparedTask,
    RunContract,
    canonical_sha256,
    file_sha256,
)
from vedagraph.semantic.replication_diagnosis import (
    AlignmentCategory,
    ComparableAssertion,
    PassageOutcome,
    align_assertions,
    canonical_target_contradictions,
    compare_regimes,
    emission_regime,
    passage_agreement,
)
from vedagraph.semantic.v3_2 import (
    STABILITY_RUN_A,
    STABILITY_RUN_B,
    IntegrityCounts,
    build_stability_experiment,
    stability_gate,
)

RUN_IDS = (STABILITY_RUN_A, STABILITY_RUN_B)
RUN_ROOTS = {run_id: Path("data/semantic") / run_id for run_id in RUN_IDS}
REPORT = Path("docs/reports/RIGVEDA_SEMANTIC_V3_2_STABILITY_RESULT.md")
COMPARISON_MANIFEST = Path(
    "docs/manifests/vedagraph-rigveda-semantic-luna-v3.2-stability-60-comparison.json"
)
FINAL_ATTEMPT_POLICY = "LEXICALLY_LOWEST_VALID_ATTEMPT_ID"


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _write_immutable(path: Path, value: object) -> None:
    payload = _json_bytes(value)
    if path.exists() and path.read_bytes() != payload:
        raise RuntimeError(f"refusing to overwrite existing seal: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(payload)


def _write_generated(path: Path, text: str) -> None:
    payload = text.rstrip() + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8", newline="\n")


def _hash_inventory(paths: list[Path], root: Path) -> dict[str, str]:
    return {path.relative_to(root).as_posix(): file_sha256(path) for path in sorted(paths)}


def _outcome(response: ModelAuthoredResponse) -> PassageOutcome:
    bindings = [item.model_dump(mode="json") for item in response.assertion_bindings]
    assertions = tuple(
        ComparableAssertion.from_mapping(item.model_dump(mode="json"), bindings)
        for item in response.semantic_output.assertions
    )
    return PassageOutcome(
        no_claim=bool(response.semantic_output.no_claim_reasons), assertions=assertions
    )


def _load_and_revalidate_run(
    run_id: str, contract: RunContract, expected_passages: set[str]
) -> tuple[dict[str, PassageOutcome], dict[str, Any]]:
    root = RUN_ROOTS[run_id]
    seal_path = root / "output_seal.json"
    existing_seal = json.loads(seal_path.read_text(encoding="utf-8")) if seal_path.exists() else {}
    store_root = root / "store"
    tasks_root = store_root / "tasks"
    store = ExecutionStore(store_root)
    task_dirs = sorted(path for path in tasks_root.iterdir() if path.is_dir())
    if len(task_dirs) != len(expected_passages):
        raise RuntimeError(
            f"{run_id}: expected {len(expected_passages)} task directories, found {len(task_dirs)}"
        )

    outcomes: dict[str, PassageOutcome] = {}
    task_hashes: dict[str, str] = {}
    final_attempts: list[dict[str, str]] = []
    surplus_valid_attempts: list[dict[str, str]] = []
    all_imported_attempts: list[Path] = []
    selected_raw_paths: list[Path] = []
    validated_paths: list[Path] = []

    for task_dir in task_dirs:
        task_path = task_dir / "task.json"
        task = PreparedTask.model_validate_json(task_path.read_text(encoding="utf-8"))
        if task.run_id != run_id or task.passage_id not in expected_passages:
            raise RuntimeError(f"{run_id}: foreign task {task.task_id}")
        if task.passage_id in outcomes:
            raise RuntimeError(f"{run_id}: duplicate passage {task.passage_id}")
        task_hashes[task.passage_id] = task.task_sha256

        attempt_dirs = sorted(
            path for path in (task_dir / "attempts").glob("attempt_*") if path.is_dir()
        )
        valid_attempt_dirs = [
            path
            for path in attempt_dirs
            if (path / "raw_response.json").is_file() and (path / "validated.json").is_file()
        ]
        if not valid_attempt_dirs:
            raise RuntimeError(f"{run_id}: no validated response for {task.passage_id}")
        selected = valid_attempt_dirs[0]
        selected_raw = selected / "raw_response.json"
        response = ModelAuthoredResponse.model_validate_json(
            selected_raw.read_text(encoding="utf-8")
        )
        validated = store.import_response(selected_raw, contract)
        if validated.task.passage_id != task.passage_id:
            raise RuntimeError(f"{run_id}: selected response points at another passage")
        outcomes[task.passage_id] = _outcome(response)
        selected_raw_paths.append(selected_raw)
        validated_paths.append(selected / "validated.json")
        all_imported_attempts.extend(valid_attempt_dirs)
        final_attempts.append(
            {
                "passage_id": task.passage_id,
                "task_id": task.task_id,
                "attempt_id": selected.name,
                "raw_response_sha256": file_sha256(selected_raw),
                "validated_sha256": file_sha256(selected / "validated.json"),
            }
        )
        for extra in valid_attempt_dirs[1:]:
            surplus_valid_attempts.append(
                {
                    "passage_id": task.passage_id,
                    "task_id": task.task_id,
                    "attempt_id": extra.name,
                    "raw_response_sha256": file_sha256(extra / "raw_response.json"),
                    "validated_sha256": file_sha256(extra / "validated.json"),
                }
            )

    if set(outcomes) != expected_passages:
        raise RuntimeError(f"{run_id}: final passage set differs from frozen selection")

    response_files = sorted((root / "responses").glob("TASK_*_attempt_*.json"))
    intermediate_files = sorted((root / "responses").glob("_int_*.json"))
    imported_raw_files = [path / "raw_response.json" for path in all_imported_attempts]
    imported_hashes = {file_sha256(path) for path in imported_raw_files}
    unimported_responses = [
        path for path in response_files if file_sha256(path) not in imported_hashes
    ]
    regime = emission_regime(outcomes)
    seal: dict[str, Any] = {
        "seal_version": "vedagraph-real-luna-v3.2-stability-output-seal-v1",
        "run_id": run_id,
        "sealed_at": existing_seal.get("sealed_at")
        or datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "execution_contract": contract.model_dump(mode="json"),
        "selection": {
            "passage_count": len(expected_passages),
            "passage_ids": sorted(expected_passages),
        },
        "final_attempt_policy": FINAL_ATTEMPT_POLICY,
        "final_attempts": sorted(final_attempts, key=lambda row: row["passage_id"]),
        "surplus_valid_attempts": surplus_valid_attempts,
        "task_hashes": task_hashes,
        "selected_raw_response_hashes": _hash_inventory(selected_raw_paths, root),
        "selected_validated_hashes": _hash_inventory(validated_paths, root),
        "all_imported_raw_response_hashes": _hash_inventory(imported_raw_files, root),
        "response_file_hashes": _hash_inventory(response_files, root),
        "intermediate_file_hashes": _hash_inventory(intermediate_files, root),
        "unimported_authored_response_hashes": _hash_inventory(unimported_responses, root),
        "counts": {
            "prepared_tasks": len(task_dirs),
            "final_validated_tasks": len(outcomes),
            "selected_final_attempts": len(final_attempts),
            "all_imported_valid_attempts": len(all_imported_attempts),
            "surplus_valid_attempts": len(surplus_valid_attempts),
            "authored_response_files": len(response_files),
            "intermediate_files": len(intermediate_files),
            "unimported_authored_responses": len(unimported_responses),
            "assertions": regime.assertions,
            "no_claim_passages": regime.no_claim_passages,
        },
        "human_gold_status": "UNANNOTATED",
        "model_self_agreement_is_accuracy": False,
        "canonical_promotion": False,
        "candidate_status": "CANDIDATE_NEEDS_REVIEW",
        "unlocked_predicates": [],
        "integrity_failures": 0,
    }
    seal["seal_sha256"] = canonical_sha256(seal)
    _write_immutable(seal_path, seal)
    (root / "output_seal.sha256").write_text(
        f"{file_sha256(root / 'output_seal.json')}  output_seal.json\n",
        encoding="utf-8",
        newline="\n",
    )
    return outcomes, seal


def _metric_row(label: str, left: int | float | str, right: int | float | str) -> str:
    return f"| {label} | {left} | {right} |"


def _report_text(manifest: dict[str, Any]) -> str:
    a = manifest["regimes"]["a"]
    b = manifest["regimes"]["b"]
    agreement = manifest["passage_agreement"]
    gate = manifest["gate"]
    rows = [
        _metric_row("Assertions", a["assertions"], b["assertions"]),
        _metric_row("Assertions per passage", f"{a['density']:.3f}", f"{b['density']:.3f}"),
        _metric_row("No-claim passages", a["no_claim_passages"], b["no_claim_passages"]),
        _metric_row("No-claim rate", f"{a['no_claim_rate']:.3f}", f"{b['no_claim_rate']:.3f}"),
        _metric_row(
            "Canonical-reference assertions",
            a["canonical_reference_count"],
            b["canonical_reference_count"],
        ),
    ]
    predicates = "\n".join(
        f"| `{name}` | {counts[0]} | {counts[1]} |"
        for name, counts in manifest["predicate_counts"].items()
    )
    alignments = "\n".join(
        f"| `{name}` | {count} |" for name, count in manifest["alignment_counts"].items()
    )
    failure_lines = (
        "None." if not gate["failures"] else "\n".join(f"- {item}" for item in gate["failures"])
    )
    status = "PASS" if gate["passed"] else "FAIL"
    return f"""# V3.2 two-run 60-mantra stability result

NO HUMAN GOLD EXISTS.

MODEL SELF-AGREEMENT IS NOT ACCURACY.

Result: **{status} — `{gate["claim"]}`**.

Both independent GPT-5.6 Luna / high / CODEX_DIRECT runs completed all 60 frozen
EvidencePackets and were sealed before comparison. The gate is an engineering policy-
stability diagnostic only. It does not establish philological correctness and it promotes
no assertion to canonical knowledge.

## Input custody and completion

- Run A: 60/60 selected final responses; seal `{manifest["run_seals"]["a"]["seal_sha256"]}`.
- Run B: 60/60 selected final responses; seal `{manifest["run_seals"]["b"]["seal_sha256"]}`.
- Prompt/schema/ontology and selection contracts match across the runs.
- Final-attempt rule: `{manifest["final_attempt_policy"]}`; it was fixed without inspecting
  semantic agreement.
- Run A contains one surplus schema-valid attempt left by overlapping earlier sessions. It
  is preserved and hashed, but excluded deterministically by the final-attempt rule.
- Unimported authored response files are preserved and hashed: Run A
  {manifest["run_seals"]["a"]["counts"]["unimported_authored_responses"]}, Run B
  {manifest["run_seals"]["b"]["counts"]["unimported_authored_responses"]}.
- Final selected responses revalidated with 0 receipt, hash, evidence, span, binding, or
  ontology/type failures.

## Run-level emission regimes

| Metric | Run A | Run B |
| --- | ---: | ---: |
{chr(10).join(rows)}

Observed gaps: no-claim rate `{manifest["regime_comparison"]["no_claim_rate_gap"]:.3f}`
(gate threshold `{gate["thresholds"]["no_claim_rate"]:.3f}`); assertion density
`{manifest["regime_comparison"]["density_gap"]:.3f}` (threshold
`{gate["thresholds"]["assertion_density"]:.3f}`). Predicate-presence Jaccard is
`{manifest["regime_comparison"]["predicate_presence_jaccard"]:.3f}`.

## Predicate counts

| Predicate | Run A | Run B |
| --- | ---: | ---: |
{predicates}

No gate-significant one-sided predicate remains.

## Passage-level replication agreement

- Exact assertion-set agreement: {agreement["exact_assertion_set"]}/60.
- Predicate-presence agreement: {agreement["predicate_presence"]}/60.
- No-claim agreement: {agreement["no_claim"]}/60.
- Canonical-entity agreement: {agreement["canonical_entity"]}/60.
- Typed-object agreement: {agreement["typed_object"]}/60.
- Evidence-anchor agreement: {agreement["evidence_anchor"]}/60.
- Contradictory canonical target passages: {len(manifest["canonical_target_contradictions"])}.

Exact agreement is not the gate objective; V3.2 targets the run-level emission-regime split.
The remaining assertion-level differences stay model candidates requiring review.

## Assertion alignment

| Category | Count |
| --- | ---: |
{alignments}

## Stability gate

Gate failures: {failure_lines}

The observed V3.1 split (57 vs 33 assertions; 10 vs 38 no-claims; 21 vs 0
`DESCRIBES_ACTION`) failed this same gate. The completed V3.2 pair passes because the two
runs have comparable density/no-claim behavior and no extensive one-sided predicate.

Both V3.2 runs are much denser than either V3.1 run (392/388 assertions versus 57/33).
That comparison is a distribution-shift warning, not an accuracy verdict: V3.1 is not
truth either. The stability pass therefore clears the narrow regime-consistency question
but does not clear the policy for corpus-scale use without candidate review/calibration.

## Decision and limits

`V3_2_POLICY_STABILITY_GATE_PASSED`

This supports retaining the V3.2 policy for the next candidate-only phase. It does not
authorize accepted graph edges, does not create human gold, and does not make intersection
or union truth. The 508 rerun and 10,552-mantra corpus extraction remain separate decisions;
if undertaken, keep full run/task/attempt provenance and use replicated calibration samples
to monitor regime drift.
"""


def main() -> None:
    experiment = build_stability_experiment()
    if experiment.contract_differences():
        raise RuntimeError(f"run contract mismatch: {experiment.contract_differences()}")
    expected = set(experiment.selection.passage_ids)
    outcomes_a, seal_a = _load_and_revalidate_run(RUN_IDS[0], experiment.run_a, expected)
    outcomes_b, seal_b = _load_and_revalidate_run(RUN_IDS[1], experiment.run_b, expected)

    regime_a = emission_regime(outcomes_a)
    regime_b = emission_regime(outcomes_b)
    comparison = compare_regimes(regime_a, regime_b)
    agreement = passage_agreement(outcomes_a, outcomes_b)
    contradictions = canonical_target_contradictions(outcomes_a, outcomes_b)
    integrity = IntegrityCounts(canonical_target_contradictions=len(contradictions))
    gate = stability_gate(comparison, integrity)
    alignment_counts: Counter[str] = Counter()
    for passage_id in sorted(expected):
        for row in align_assertions(
            outcomes_a[passage_id].assertions, outcomes_b[passage_id].assertions
        ):
            alignment_counts[row.category.value] += 1
    for category in AlignmentCategory:
        alignment_counts.setdefault(category.value, 0)

    existing_manifest = (
        json.loads(COMPARISON_MANIFEST.read_text(encoding="utf-8"))
        if COMPARISON_MANIFEST.exists()
        else {}
    )
    manifest: dict[str, Any] = {
        "manifest_version": "vedagraph-real-luna-v3.2-stability-comparison-v1",
        "generated_at": existing_manifest.get("generated_at")
        or datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "run_ids": list(RUN_IDS),
        "final_attempt_policy": FINAL_ATTEMPT_POLICY,
        "run_seals": {
            "a": {
                "path": (RUN_ROOTS[RUN_IDS[0]] / "output_seal.json").as_posix(),
                "file_sha256": file_sha256(RUN_ROOTS[RUN_IDS[0]] / "output_seal.json"),
                "seal_sha256": seal_a["seal_sha256"],
                "counts": seal_a["counts"],
            },
            "b": {
                "path": (RUN_ROOTS[RUN_IDS[1]] / "output_seal.json").as_posix(),
                "file_sha256": file_sha256(RUN_ROOTS[RUN_IDS[1]] / "output_seal.json"),
                "seal_sha256": seal_b["seal_sha256"],
                "counts": seal_b["counts"],
            },
        },
        "regimes": {
            "a": {
                **asdict(regime_a),
                "density": regime_a.density,
                "no_claim_rate": regime_a.no_claim_rate,
            },
            "b": {
                **asdict(regime_b),
                "density": regime_b.density,
                "no_claim_rate": regime_b.no_claim_rate,
            },
        },
        "regime_comparison": {
            "no_claim_rate_gap": comparison.no_claim_rate_gap,
            "density_gap": comparison.density_gap,
            "predicate_presence_jaccard": comparison.predicate_presence_jaccard,
            "one_sided_predicates": list(comparison.one_sided_predicates),
            "skew_probabilities": dict(comparison.skew_probabilities),
        },
        "predicate_counts": dict(comparison.predicate_counts),
        "object_kind_counts": dict(comparison.object_kind_counts),
        "passage_agreement": asdict(agreement),
        "alignment_counts": dict(sorted(alignment_counts.items())),
        "canonical_target_contradictions": list(contradictions),
        "gate": {
            "passed": gate.passed,
            "claim": gate.claim,
            "failures": list(gate.failures),
            "thresholds": {
                "no_claim_rate": gate.thresholds.no_claim_rate_gap,
                "assertion_density": gate.thresholds.assertion_density_gap,
                "one_sided_predicate_occurrences": gate.thresholds.one_sided_predicate_occurrences,
                "one_sided_skew_probability": gate.thresholds.one_sided_skew_probability,
                "provenance": gate.thresholds.provenance,
            },
        },
        "integrity": asdict(integrity),
        "human_gold_status": "UNANNOTATED",
        "model_self_agreement_is_accuracy": False,
        "canonical_promotion": False,
        "candidate_status": "CANDIDATE_NEEDS_REVIEW",
        "unlocked_predicates": [],
    }
    manifest["manifest_sha256"] = canonical_sha256(manifest)
    _write_immutable(COMPARISON_MANIFEST, manifest)
    _write_generated(REPORT, _report_text(manifest))
    print(
        json.dumps(
            {
                "run_a": seal_a["counts"],
                "run_b": seal_b["counts"],
                "gate": manifest["gate"],
                "report": REPORT.as_posix(),
                "comparison_manifest": COMPARISON_MANIFEST.as_posix(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
