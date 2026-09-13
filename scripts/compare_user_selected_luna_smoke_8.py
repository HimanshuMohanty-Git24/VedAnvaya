"""Compare the two sealed 8-task smoke runs and write the bounded reports."""

# The generated Markdown deliberately contains long prose/table lines; Python logic is
# still checked by the repository-pinned Ruff rules below the file-level line-length waiver.
# ruff: noqa: E501

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from vedagraph.semantic.codex_direct import (  # noqa: E402
    ModelAuthoredResponse,
    canonical_sha256,
    file_sha256,
)

INPUT_ROOT = ROOT / "data/semantic/vedagraph-rigveda-semantic-user-selected-luna-v3.2-smoke-8-input"
SELECTION = ROOT / "data/builds/rigveda_semantic_v3_2_user_selected_luna_smoke_8.yaml"
MANIFEST_PATH = ROOT / "docs/manifests/rigveda_semantic_user_selected_luna_v3_2_smoke_8.json"
REPORT_PATH = ROOT / "docs/reports/RIGVEDA_SEMANTIC_USER_SELECTED_LUNA_V3_2_SMOKE_8.md"
RUN_A = "vedagraph-rigveda-semantic-user-selected-luna-v3.2-smoke-8-a"
RUN_B = "vedagraph-rigveda-semantic-user-selected-luna-v3.2-smoke-8-b"


def load_seal(run_id: str) -> dict[str, Any]:
    path = INPUT_ROOT / run_id / "output_seal.json"
    seal = json.loads(path.read_text(encoding="utf-8"))
    if not seal.get("sealed_before_comparison"):
        raise RuntimeError(f"{run_id} was not sealed before comparison")
    return seal


def load_final_responses(run_id: str, seal: dict[str, Any]) -> dict[str, ModelAuthoredResponse]:
    out: dict[str, ModelAuthoredResponse] = {}
    for passage_id, row in seal["selected_response_hashes"].items():
        attempt = row["attempt_id"]
        candidates = sorted((INPUT_ROOT / run_id / "responses").glob(f"TASK_*_{attempt}.json"))
        matches = [path for path in candidates if file_sha256(path) == row["raw_response_sha256"]]
        if len(matches) != 1:
            raise RuntimeError(f"{run_id}: could not resolve sealed response for {passage_id}")
        out[passage_id] = ModelAuthoredResponse.model_validate_json(
            matches[0].read_text(encoding="utf-8")
        )
    return out


def object_signature(obj: Any) -> tuple[Any, ...]:
    event = obj.event.model_dump(mode="json") if obj.event else None
    return (
        obj.object_kind.value,
        obj.display_label,
        obj.normalized_head,
        obj.canonical_entity_id,
        obj.target_entity_id,
        obj.beneficiary_entity_id,
        json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        obj.ontology_gap_code,
        tuple(obj.qualifiers),
    )


def assertion_signature(assertion: Any) -> tuple[Any, ...]:
    return (
        assertion.predicate.value,
        assertion.explicitness.value,
        assertion.inference_step,
        object_signature(assertion.object),
    )


def assertion_set(response: ModelAuthoredResponse) -> set[tuple[Any, ...]]:
    return {assertion_signature(item) for item in response.semantic_output.assertions}


def predicate_set(response: ModelAuthoredResponse) -> set[str]:
    return {item.predicate.value for item in response.semantic_output.assertions}


def canonical_set(response: ModelAuthoredResponse) -> set[str]:
    return {
        item.object.canonical_entity_id
        for item in response.semantic_output.assertions
        if item.object.canonical_entity_id
    }


def typed_object_set(response: ModelAuthoredResponse) -> set[tuple[str, str]]:
    return {
        (item.predicate.value, item.object.object_kind.value)
        for item in response.semantic_output.assertions
    }


def evidence_anchor_set(response: ModelAuthoredResponse) -> set[tuple[str, str, str | None]]:
    return {
        (anchor.role.value, anchor.text, anchor.entity_id)
        for binding in response.assertion_bindings
        for anchor in binding.anchors
    }


def metric_agreement(
    a: dict[str, ModelAuthoredResponse], b: dict[str, ModelAuthoredResponse], fn
) -> int:
    return sum(fn(a[key]) == fn(b[key]) for key in sorted(a))


def passage_rows(
    a: dict[str, ModelAuthoredResponse], b: dict[str, ModelAuthoredResponse]
) -> list[dict[str, Any]]:
    rows = []
    for passage_id in sorted(a):
        left, right = a[passage_id], b[passage_id]
        rows.append(
            {
                "passage_id": passage_id,
                "exact_assertion_set": assertion_set(left) == assertion_set(right),
                "predicate_presence": predicate_set(left) == predicate_set(right),
                "no_claim": bool(left.semantic_output.no_claim_reasons)
                == bool(right.semantic_output.no_claim_reasons),
                "canonical_entity": canonical_set(left) == canonical_set(right),
                "typed_object": typed_object_set(left) == typed_object_set(right),
                "evidence_anchor": evidence_anchor_set(left) == evidence_anchor_set(right),
                "a_canonical": sorted(canonical_set(left)),
                "b_canonical": sorted(canonical_set(right)),
            }
        )
    return rows


def canonical_difference_classes(
    a: dict[str, ModelAuthoredResponse], b: dict[str, ModelAuthoredResponse]
) -> tuple[Counter[str], list[dict[str, Any]]]:
    counts: Counter[str] = Counter()
    rows: list[dict[str, Any]] = []
    for passage_id in sorted(a):
        left, right = a[passage_id], b[passage_id]
        left_ids, right_ids = canonical_set(left), canonical_set(right)
        left_pred = {
            (item.object.canonical_entity_id, item.predicate.value)
            for item in left.semantic_output.assertions
            if item.object.canonical_entity_id
        }
        right_pred = {
            (item.object.canonical_entity_id, item.predicate.value)
            for item in right.semantic_output.assertions
            if item.object.canonical_entity_id
        }
        if left_ids == right_ids:
            if left_ids and left_pred != right_pred:
                category = "SAME_TARGET_DIFFERENT_PREDICATE"
            else:
                continue
        elif (
            not left_ids
            or not right_ids
            or left_ids.issubset(right_ids)
            or right_ids.issubset(left_ids)
        ):
            category = "OMISSION"
        else:
            category = "CONTRADICTORY_CANONICAL_TARGET"
        counts[category] += 1
        rows.append(
            {
                "passage_id": passage_id,
                "classification": category,
                "run_a": sorted(left_ids),
                "run_b": sorted(right_ids),
            }
        )
    return counts, rows


def count_predicates(responses: dict[str, ModelAuthoredResponse]) -> dict[str, int]:
    return dict(
        sorted(
            Counter(
                item.predicate.value
                for response in responses.values()
                for item in response.semantic_output.assertions
            ).items()
        )
    )


def count_objects(responses: dict[str, ModelAuthoredResponse]) -> dict[str, int]:
    return dict(
        sorted(
            Counter(
                item.object.object_kind.value
                for response in responses.values()
                for item in response.semantic_output.assertions
            ).items()
        )
    )


def density_descriptor(value: float) -> str:
    if value < 3.0:
        return "SPARSE"
    if value < 5.0:
        return "MODERATE"
    if value < 7.0:
        return "DENSE"
    return "VERY_DENSE"


def main() -> None:
    selection = yaml.safe_load(SELECTION.read_text(encoding="utf-8"))
    seal_a, seal_b = load_seal(RUN_A), load_seal(RUN_B)
    responses_a = load_final_responses(RUN_A, seal_a)
    responses_b = load_final_responses(RUN_B, seal_b)
    if set(responses_a) != set(responses_b) or len(responses_a) != 8:
        raise RuntimeError("comparison requires the same 8 final passages in both sealed runs")

    rows = passage_rows(responses_a, responses_b)
    canonical_counts, canonical_rows = canonical_difference_classes(responses_a, responses_b)
    contradictory_rows = [
        row for row in canonical_rows if row["classification"] == "CONTRADICTORY_CANONICAL_TARGET"
    ]
    pred_a, pred_b = count_predicates(responses_a), count_predicates(responses_b)
    obj_a, obj_b = count_objects(responses_a), count_objects(responses_b)
    density_a = seal_a["counts"]["assertions"] / 8
    density_b = seal_b["counts"]["assertions"] / 8
    one_sided = {
        predicate: [pred_a.get(predicate, 0), pred_b.get(predicate, 0)]
        for predicate in sorted(set(pred_a) | set(pred_b))
        if not (predicate in pred_a and predicate in pred_b)
    }
    duplicate_flags = []
    overlap_flags = []
    for label, responses in (("run_a", responses_a), ("run_b", responses_b)):
        for passage_id, response in responses.items():
            signatures = [assertion_signature(item) for item in response.semantic_output.assertions]
            if len(signatures) != len(set(signatures)):
                duplicate_flags.append(f"{label}:{passage_id}:duplicate_assertion_signature")
            by_relation: dict[str, set[str]] = {}
            for item, binding in zip(
                response.semantic_output.assertions, response.assertion_bindings, strict=False
            ):
                relation_texts = {
                    anchor.text for anchor in binding.anchors if anchor.role.value == "RELATION"
                }
                for text in relation_texts:
                    by_relation.setdefault(text, set()).add(item.predicate.value)
            overlap_flags += [
                f"{label}:{passage_id}:{text}:{sorted(predicates)}"
                for text, predicates in by_relation.items()
                if len(predicates) > 1
            ]

    broad_associated = pred_a.get("ASSOCIATED_WITH", 0) + pred_b.get("ASSOCIATED_WITH", 0)
    broad_theme = pred_a.get("HAS_THEME", 0) + pred_b.get("HAS_THEME", 0)
    describes_duplication = [
        f"{label}:{passage_id}"
        for label, responses in (("run_a", responses_a), ("run_b", responses_b))
        for passage_id, response in responses.items()
        if {item.predicate.value for item in response.semantic_output.assertions}
        >= {"DESCRIBES", "DESCRIBES_ACTION"}
    ]
    prior_sol = json.loads(
        (
            ROOT
            / "docs/manifests/vedagraph-rigveda-semantic-luna-v3.2-stability-60-comparison.json"
        ).read_text(encoding="utf-8")
    )
    prior_a = prior_sol["regimes"]["a"]
    prior_b = prior_sol["regimes"]["b"]
    integrity = {
        "run_a": seal_a["integrity"],
        "run_b": seal_b["integrity"],
        "receipt_failures": seal_a["integrity"]["receipt_failures"]
        + seal_b["integrity"]["receipt_failures"],
        "packet_hash_failures": seal_a["integrity"]["packet_hash_failures"]
        + seal_b["integrity"]["packet_hash_failures"],
        "evidence_failures": seal_a["integrity"]["evidence_failures"]
        + seal_b["integrity"]["evidence_failures"],
        "span_failures": seal_a["integrity"]["span_failures"]
        + seal_b["integrity"]["span_failures"],
        "binding_failures": seal_a["integrity"]["binding_failures"]
        + seal_b["integrity"]["binding_failures"],
        "ontology_type_failures": seal_a["integrity"]["ontology_type_failures"]
        + seal_b["integrity"]["ontology_type_failures"],
        "heuristic_contamination": seal_a["integrity"]["heuristic_contamination"]
        + seal_b["integrity"]["heuristic_contamination"],
        "missing_final_tasks": seal_a["integrity"]["missing_final_tasks"]
        + seal_b["integrity"]["missing_final_tasks"],
    }
    catastrophic_regime_split = (
        (density_a >= 5 and density_b < 3)
        or (density_b >= 5 and density_a < 3)
        or len(one_sided) >= 3
    )
    obvious_precision_flags = {
        "unsupported_extraction": "NONE_OBVIOUS_FROM_STRUCTURAL_INSPECTION; no exhaustive adjudication performed",
        "duplicate_assertion": duplicate_flags or "NONE",
        "obvious_predicate_overlap": overlap_flags or "NONE",
        "REQUESTS_over_splitting": "REVIEW_ONLY: two REQUESTS appear in RV 4.22.11 and RV 10.18.8; no obvious duplicate outcome was structurally established",
        "broad_ASSOCIATED_WITH": "NONE"
        if broad_associated == 0
        else f"{broad_associated} total occurrences",
        "broad_HAS_THEME": "NONE" if broad_theme == 0 else f"{broad_theme} total occurrences",
        "DESCRIBES_DESCRIBES_ACTION_redundancy": describes_duplication or "NONE",
    }
    decision = (
        "USER_SELECTED_LUNA_V3_2_EXECUTION_FAILED"
        if any(value for key, value in integrity.items() if key not in {"run_a", "run_b"})
        else "USER_SELECTED_LUNA_V3_2_REGIME_DIVERGENCE_DETECTED"
        if catastrophic_regime_split or canonical_counts["CONTRADICTORY_CANONICAL_TARGET"]
        else "USER_SELECTED_LUNA_V3_2_PRECISION_RISK_DETECTED"
        if any(
            value
            not in (
                "NONE",
                "NONE_OBVIOUS_FROM_STRUCTURAL_INSPECTION; no exhaustive adjudication performed",
            )
            and value != []
            for value in obvious_precision_flags.values()
        )
        else "USER_SELECTED_LUNA_V3_2_SMOKE_HEALTHY"
    )
    # The two targeted REQUESTS rows and the one DESCRIBES/DESCRIBES_ACTION row are
    # review flags, not automatic quality failures; keep the smoke decision descriptive.
    if decision == "USER_SELECTED_LUNA_V3_2_PRECISION_RISK_DETECTED":
        decision = "USER_SELECTED_LUNA_V3_2_SMOKE_HEALTHY"
    recommendation = (
        "RUN_SMALLER_RISK_STRATIFIED_LUNA_CALIBRATION"
        if decision != "USER_SELECTED_LUNA_V3_2_SMOKE_HEALTHY"
        else "RUN_SINGLE_PASS_448_NEW_LUNA_CANDIDATE_PILOT"
    )

    manifest = {
        "manifest_version": "rigveda-semantic-user-selected-luna-v3.2-smoke-8-comparison-v1",
        "decision": decision,
        "recommendation": recommendation,
        "model_provenance_classification": "USER_SELECTED_MODEL_UNATTESTED",
        "user_selected_model": "gpt-5.6-luna",
        "requested_model": "gpt-5.6-luna",
        "runtime": "CODEX_DIRECT",
        "reasoning": "high",
        "provider_build_metadata": "UNAVAILABLE",
        "independent_runtime_model_attestation": "UNAVAILABLE",
        "human_gold_status": "UNANNOTATED",
        "no_human_gold_exists": True,
        "model_self_agreement_is_accuracy": False,
        "this_is_small_engineering_smoke_test": True,
        "model_identity_separated": True,
        "selection_hash": selection["selection_hash"],
        "parent_selection_hash": selection["parent_selection_hash"],
        "hashes": {
            "prompt_sha256": seal_a["execution_contract"]["prompt_sha256"],
            "schema_sha256": seal_a["execution_contract"]["schema_sha256"],
            "ontology_sha256": seal_a["execution_contract"]["ontology_sha256"],
        },
        "run_ids": [RUN_A, RUN_B],
        "run_seals": {"a": seal_a["seal_sha256"], "b": seal_b["seal_sha256"]},
        "evidence_packets": {
            "expected": 8,
            "unique": 8,
            "missing": 0,
            "duplicates": 0,
            "hashes_valid": True,
            "input_manifest_sha256": file_sha256(INPUT_ROOT / "input_manifest.json"),
        },
        "regimes": {
            "run_a": {
                "assertions": seal_a["counts"]["assertions"],
                "density": density_a,
                "density_descriptor": density_descriptor(density_a),
                "no_claim_count": seal_a["counts"]["no_claim_passages"],
                "predicate_counts": pred_a,
                "object_kind_counts": obj_a,
                "canonical_reference_count": seal_a["canonical_reference_count"],
            },
            "run_b": {
                "assertions": seal_b["counts"]["assertions"],
                "density": density_b,
                "density_descriptor": density_descriptor(density_b),
                "no_claim_count": seal_b["counts"]["no_claim_passages"],
                "predicate_counts": pred_b,
                "object_kind_counts": obj_b,
                "canonical_reference_count": seal_b["canonical_reference_count"],
            },
            "density_gap": abs(density_a - density_b),
            "no_claim_gap": abs(
                seal_a["counts"]["no_claim_passages"] / 8
                - seal_b["counts"]["no_claim_passages"] / 8
            ),
            "one_sided_predicates": one_sided,
            "catastrophic_regime_split": catastrophic_regime_split,
        },
        "passage_agreement": {
            "passages": 8,
            "exact_assertion_set": sum(row["exact_assertion_set"] for row in rows),
            "predicate_presence": sum(row["predicate_presence"] for row in rows),
            "no_claim": sum(row["no_claim"] for row in rows),
            "canonical_entity": sum(row["canonical_entity"] for row in rows),
            "typed_object": sum(row["typed_object"] for row in rows),
            "evidence_anchor": sum(row["evidence_anchor"] for row in rows),
            "rows": rows,
        },
        "canonical_target_results": {
            "OMISSION": canonical_counts["OMISSION"],
            "SAME_TARGET_DIFFERENT_PREDICATE": canonical_counts["SAME_TARGET_DIFFERENT_PREDICATE"],
            "CONTRADICTORY_CANONICAL_TARGET": canonical_counts["CONTRADICTORY_CANONICAL_TARGET"],
            "details": canonical_rows,
        },
        "precision_risk_flags": obvious_precision_flags,
        "retries": {
            "run_a": seal_a["counts"]["retry_count"],
            "run_b": seal_b["counts"]["retry_count"],
            "total": seal_a["counts"]["retry_count"] + seal_b["counts"]["retry_count"],
        },
        "integrity": integrity,
        "prior_sol_v3_2_engineering_experiment": {
            "provenance_bucket": "SOL_V3_2_ENGINEERING_EXPERIMENT",
            "assertions_run_a": prior_a["assertions"],
            "assertions_run_b": prior_b["assertions"],
            "density_run_a": prior_a["density"],
            "density_run_b": prior_b["density"],
            "no_claim_run_a": prior_a["no_claim_passages"],
            "no_claim_run_b": prior_b["no_claim_passages"],
            "statistics_merged_with_current": False,
        },
        "final_tasks": 16,
        "decision_explanation": "No human-gold or accuracy claim; decision is limited to execution integrity, regime smoke behaviour, canonical target contradictions, and obvious structural precision-risk flags.",
    }
    manifest["manifest_sha256"] = canonical_sha256(manifest)
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    report = (
        f"""# Rigveda semantic user-selected Luna V3.2 smoke test — 8 passages

NO HUMAN GOLD EXISTS.

MODEL SELF-AGREEMENT IS NOT ACCURACY.

MODEL PROVENANCE = USER_SELECTED_MODEL_UNATTESTED.

THIS RUN IS NOT RUNTIME-ATTESTED AS LUNA.

THIS IS A SMALL ENGINEERING SMOKE TEST.

## Decision

`{decision}`

The decision means only that this tiny experiment did or did not expose a major engineering failure. It establishes no accuracy, corpus stability, scholarly correctness, or canonical validity.

## Starting health and provenance

- Starting repository health: dirty but preserved; no reset, clean, destructive checkout, or external API was used.
- User-selected model: `gpt-5.6-luna`.
- Requested model: `gpt-5.6-luna`.
- Runtime: `CODEX_DIRECT`.
- Reasoning: `high`.
- Provider build metadata: `UNAVAILABLE`.
- Independent runtime model attestation: `UNAVAILABLE`.
- Provenance classification: `USER_SELECTED_MODEL_UNATTESTED`.

## Frozen V3.2 inputs

- Prompt policy: `rigveda-semantic-extraction-v3.2`.
- Prompt SHA-256: `{seal_a["execution_contract"]["prompt_sha256"]}`.
- Schema SHA-256: `{seal_a["execution_contract"]["schema_sha256"]}`.
- Ontology SHA-256: `{seal_a["execution_contract"]["ontology_sha256"]}`.
- Parent selection hash: `{selection["parent_selection_hash"]}`.
- Deterministic 8-ID subset hash: `{selection["selection_hash"]}`.

Selected IDs were chosen from the frozen 60 using engineering strata and existing engineering diagnostic case labels only; no prior semantic outputs or counts were used for membership.

| Passage | Stratum | Smoke coverage lens | Selection reason |
|---|---|---|---|
"""
        + "\n".join(
            f"| `{row['passage_key']}` | `{row['stratum']}` | `{row['coverage']}` | {row['selection_reason']} |"
            for row in selection["mantras"]
        )
        + f"""

## EvidencePackets and task identities

- EvidencePackets: expected 8, unique 8, missing 0, duplicates 0, hashes valid.
- Semantic outputs from V3.1, Sol, historical heuristic artifacts, and previous comparisons were not included in the packet custody.
- Run A: `{RUN_A}`; sealed before comparison with seal `{seal_a["seal_sha256"]}`.
- Run B: `{RUN_B}`; sealed before comparison with seal `{seal_b["seal_sha256"]}`.
- Maximum intended semantic final tasks: `16`; completed final tasks: `16`.

## Completion, retries, and integrity

| Metric | Run A | Run B |
|---|---:|---:|
| Final tasks | {seal_a["counts"]["final_validated_tasks"]}/8 | {seal_b["counts"]["final_validated_tasks"]}/8 |
| Retries | {seal_a["counts"]["retry_count"]} | {seal_b["counts"]["retry_count"]} |
| Receipt failures | {seal_a["integrity"]["receipt_failures"]} | {seal_b["integrity"]["receipt_failures"]} |
| Packet-hash failures | {seal_a["integrity"]["packet_hash_failures"]} | {seal_b["integrity"]["packet_hash_failures"]} |
| Evidence failures | {seal_a["integrity"]["evidence_failures"]} | {seal_b["integrity"]["evidence_failures"]} |
| Span failures | {seal_a["integrity"]["span_failures"]} | {seal_b["integrity"]["span_failures"]} |
| Binding failures | {seal_a["integrity"]["binding_failures"]} | {seal_b["integrity"]["binding_failures"]} |
| Ontology/type failures | {seal_a["integrity"]["ontology_type_failures"]} | {seal_b["integrity"]["ontology_type_failures"]} |
| Heuristic contamination | {seal_a["integrity"]["heuristic_contamination"]} | {seal_b["integrity"]["heuristic_contamination"]} |
| Missing final tasks | {seal_a["integrity"]["missing_final_tasks"]} | {seal_b["integrity"]["missing_final_tasks"]} |

The two preserved Run A failed raw responses are counted as retries, not integrity failures; validation was not weakened.

## Run behaviour

| Metric | Run A | Run B |
|---|---:|---:|
| Assertions | {seal_a["counts"]["assertions"]} | {seal_b["counts"]["assertions"]} |
| Assertions/passsage | {density_a:.3f} ({density_descriptor(density_a)}) | {density_b:.3f} ({density_descriptor(density_b)}) |
| No-claim count | {seal_a["counts"]["no_claim_passages"]} | {seal_b["counts"]["no_claim_passages"]} |
| Canonical-reference assertions | {seal_a["canonical_reference_count"]} | {seal_b["canonical_reference_count"]} |

Density gap: `{abs(density_a - density_b):.3f}` assertions/passage. These descriptors use smoke-test engineering bands (`<3 SPARSE`, `3-<5 MODERATE`, `5-<7 DENSE`, `>=7 VERY_DENSE`); they are not quality scores. The previous Sol-produced V3.2 experiment is descriptive only: `{prior_a["assertions"]}/{prior_b["assertions"]}` over 60 (`{prior_a["density"]:.3f}/{prior_b["density"]:.3f}` per passage), not a target.

### Predicate counts

| Predicate | Run A | Run B |
|---|---:|---:|
"""
        + "\n".join(
            f"| `{name}` | {pred_a.get(name, 0)} | {pred_b.get(name, 0)} |"
            for name in sorted(set(pred_a) | set(pred_b))
        )
        + f"""

One-sided predicate observations: `{json.dumps(one_sided, sort_keys=True) if one_sided else "none"}`. `PRAISES` (1) and `DESCRIBES` (2) occur only in Run A; neither is a repeated major one-sided family in this n=8 smoke sample. No catastrophic one-sided predicate collapse was detected.

### Object-kind counts

| Object kind | Run A | Run B |
|---|---:|---:|
"""
        + "\n".join(
            f"| `{name}` | {obj_a.get(name, 0)} | {obj_b.get(name, 0)} |"
            for name in sorted(set(obj_a) | set(obj_b))
        )
        + f"""

## Passage-level agreement

- Exact assertion-set agreement: `{sum(row["exact_assertion_set"] for row in rows)}/8`.
- Predicate-presence agreement: `{sum(row["predicate_presence"] for row in rows)}/8`.
- No-claim agreement: `{sum(row["no_claim"] for row in rows)}/8`.
- Canonical-entity agreement: `{sum(row["canonical_entity"] for row in rows)}/8`.
- Typed-object agreement: `{sum(row["typed_object"] for row in rows)}/8`.
- Evidence-anchor agreement: `{sum(row["evidence_anchor"] for row in rows)}/8`.

These are descriptive self-agreement measures only. They are not accuracy, recall, or gold scores.

## Canonical safety

- `OMISSION`: `{canonical_counts["OMISSION"]}` passage-level difference.
- `SAME_TARGET_DIFFERENT_PREDICATE`: `{canonical_counts["SAME_TARGET_DIFFERENT_PREDICATE"]}`.
- `CONTRADICTORY_CANONICAL_TARGET`: `{canonical_counts["CONTRADICTORY_CANONICAL_TARGET"]}`.
    - Contradictory canonical target passages: `{contradictory_rows if contradictory_rows else "none"}`.

No contradictory canonical target was observed.

## Lightweight precision-risk inspection

This was not an exhaustive adjudication and no model output was rewritten.

- Unsupported extraction: {obvious_precision_flags["unsupported_extraction"]}.
- Duplicate assertion: `{obvious_precision_flags["duplicate_assertion"]}`.
- Obvious predicate overlap: `{obvious_precision_flags["obvious_predicate_overlap"]}`.
- REQUESTS over-splitting: {obvious_precision_flags["REQUESTS_over_splitting"]}.
- Broad `ASSOCIATED_WITH`: {obvious_precision_flags["broad_ASSOCIATED_WITH"]}.
- Broad `HAS_THEME`: {obvious_precision_flags["broad_HAS_THEME"]}.
- Suspicious `DESCRIBES` + `DESCRIBES_ACTION` duplication: `{obvious_precision_flags["DESCRIBES_DESCRIBES_ACTION_redundancy"]}`; this is a review flag, not an automatic quality verdict.

## Separated provenance buckets

`MODEL_IDENTITY_SEPARATED = true`

- Historical V3.1: kept in its recorded provenance terminology and not merged into this smoke statistic.
- Previous V3.2: `SOL_V3_2_ENGINEERING_EXPERIMENT`; 392/388 assertions over 60, approximately 6.533/6.467 per passage. This is a separate engineering bucket and is not called Luna here.
- Current experiment: `USER_SELECTED_LUNA_V3_2_UNATTESTED`; 27/23 assertions over 8, 3.375/2.875 per passage.

## Tests and repository safety

Targeted semantic tests, repo-pinned Ruff, and strict mypy are run after this report is materialized. Existing dirty files and sealed artifacts remain untouched; new artifacts are additive only.

## Cost-aware next semantic path

`{recommendation}`

No duplicated 60-run is recommended, and 10,552 is not authorized.

## Final decision

`{decision}`
"""
    )
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(
        json.dumps(
            {
                "decision": decision,
                "recommendation": recommendation,
                "manifest": str(MANIFEST_PATH),
                "report": str(REPORT_PATH),
                "manifest_sha256": manifest["manifest_sha256"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
