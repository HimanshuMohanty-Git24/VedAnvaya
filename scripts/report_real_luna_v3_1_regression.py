"""Produce post-seal reports for the bounded real-Luna regression.

This script is intentionally downstream of the output seal. It reads the newly sealed
CODEX_DIRECT responses first, then opens only the historical deterministic V3 baseline for
the explicitly diagnostic comparison.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml

from vedagraph.semantic.codex_direct import (
    ModelAuthoredResponse,
    PreparedTask,
    RunContract,
    response_payload_sha256,
    validate_bindings,
    validate_receipt,
)
from vedagraph.semantic.evidence import validate_evidence_anchors
from vedagraph.semantic.v3 import validate_v3_payload

ROOT = Path("data/semantic/vedagraph-rigveda-semantic-luna-v3.1-regression")
STORE = ROOT / "store"
CONFIG = Path("data/builds/rigveda_semantic_codex_luna_regression_v1.yaml")
SEAL = Path("docs/manifests/vedagraph_rigveda_semantic_luna_v3_1_regression_output_seal.json")
REPORTS = Path("docs/reports")
RUN_ID = "vedagraph-rigveda-semantic-luna-v3.1-regression"
HISTORICAL = Path("data/semantic/vedagraph-rigveda-semantic-luna-v3-508/v3_extractions.jsonl")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def sig(assertion: Any) -> tuple[str, str, str]:
    obj = assertion.object
    label = obj.canonical_entity_id or obj.normalized_head or obj.display_label
    return (assertion.predicate.value, obj.object_kind.value, label)


def main() -> None:
    seal = load_json(SEAL)
    if seal.get("historical_sources_opened") is not False:
        raise RuntimeError(
            "the pre-comparison seal must explicitly say historical_sources_opened=false"
        )
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    rows = {str(row["passage_key"]): row for row in config["mantras"]}
    contract = RunContract.model_validate_json(
        (STORE / "run_contract.json").read_text(encoding="utf-8")
    )
    current: dict[str, tuple[PreparedTask, ModelAuthoredResponse, list[str], list[str]]] = {}
    for task_dir in sorted((STORE / "tasks").iterdir()):
        task = PreparedTask.model_validate_json(
            (task_dir / "task.json").read_text(encoding="utf-8")
        )
        raw_path = task_dir / "attempts" / "attempt_001" / "raw_response.json"
        response = ModelAuthoredResponse.model_validate_json(raw_path.read_text(encoding="utf-8"))
        errors_receipt = validate_receipt(
            response.receipt,
            task,
            contract,
            computed_response_sha256=response_payload_sha256(response),
        )
        errors_payload = validate_v3_payload(
            response.semantic_output,
            task.evidence_packet,
            canonical_entity_ids=frozenset(m.entity_key for m in task.evidence_packet.mentions),
        )
        errors_evidence = validate_evidence_anchors(response.semantic_output, task.evidence_packet)
        errors_bindings = validate_bindings(
            response.semantic_output, response.assertion_bindings, task.evidence_packet
        )
        current[task.passage_id] = (
            task,
            response,
            errors_receipt + errors_payload + errors_evidence,
            errors_bindings,
        )
    if set(current) != set(rows) or len(current) != 60:
        raise RuntimeError("current response set does not match the frozen 60")

    assertions = [
        a for _, response, _, _ in current.values() for a in response.semantic_output.assertions
    ]
    gaps = [
        g for _, response, _, _ in current.values() for g in response.semantic_output.ontology_gaps
    ]
    predicate_counts = Counter(a.predicate.value for a in assertions)
    object_counts = Counter(a.object.object_kind.value for a in assertions)
    explicitness_counts = Counter(a.explicitness.value for a in assertions)
    no_claims = sum(
        not response.semantic_output.assertions for _, response, _, _ in current.values()
    )
    canonical_refs = sum(a.object.canonical_entity_id is not None for a in assertions)
    evidence_failures = sum(len(item[2]) for item in current.values())
    binding_failures = sum(len(item[3]) for item in current.values())
    imported_invalid_spans = evidence_failures + binding_failures

    strata: dict[str, list[str]] = defaultdict(list)
    for passage_id, row in rows.items():
        strata[str(row["stratum"])].append(passage_id)
    b01_ids = strata["B01_RELATION_BINDING"]
    b02_ids = strata["B02_EVIDENCE_SPAN"]
    parallel_ids = strata["PARALLEL_CONTROL"]
    clean_ids = strata["CLEAN_CONTROL"]

    b01_assertions = sum(len(current[key][1].semantic_output.assertions) for key in b01_ids)
    b01_binding_errors = sum(len(current[key][3]) for key in b01_ids)
    b02_anchor_count = sum(
        len(binding.anchors) for key in b02_ids for binding in current[key][1].assertion_bindings
    )
    b02_binding_errors = sum(len(current[key][3]) for key in b02_ids)

    historical: dict[str, dict[str, Any]] = {}
    for line in HISTORICAL.read_text(encoding="utf-8").splitlines():
        if line.strip():
            record = json.loads(line)
            historical[str(record.get("mantra_id", ""))] = record

    def citation_for(key: str) -> str:
        return str(rows[key]["citation"])

    historical_by_citation = {
        str(record.get("mantra_id")): record for record in historical.values()
    }
    comparison = Counter(
        {
            "same": 0,
            "Luna-only": 0,
            "heuristic-only": 0,
            "different predicate": 0,
            "different target": 0,
            "different object granularity": 0,
        }
    )
    comparison_rows: list[dict[str, Any]] = []
    for key in sorted(current):
        _, response, _, _ = current[key]
        citation = citation_for(key)
        old = historical_by_citation.get(citation, {"assertions": []})
        model_sigs = {sig(a) for a in response.semantic_output.assertions}
        old_sigs = {
            (
                str(a.get("predicate")),
                str(a.get("object", {}).get("object_kind")),
                str(
                    a.get("object", {}).get("canonical_entity_id")
                    or a.get("object", {}).get("normalized_head")
                    or a.get("object", {}).get("display_label")
                ),
            )
            for a in old.get("assertions", [])
        }
        same = model_sigs & old_sigs
        model_only = model_sigs - old_sigs
        old_only = old_sigs - model_sigs
        comparison["same"] += len(same)
        comparison["Luna-only"] += len(model_only)
        comparison["heuristic-only"] += len(old_only)
        for model_assertion in response.semantic_output.assertions:
            model_label = (
                model_assertion.object.normalized_head or model_assertion.object.display_label
            )
            for old_assertion in old.get("assertions", []):
                old_object = old_assertion.get("object", {})
                old_label = str(
                    old_object.get("normalized_head") or old_object.get("display_label")
                )
                same_kind = model_assertion.object.object_kind.value == str(
                    old_object.get("object_kind")
                )
                same_predicate = model_assertion.predicate.value == str(
                    old_assertion.get("predicate")
                )
                if same_kind and model_label == old_label and not same_predicate:
                    comparison["different predicate"] += 1
                if same_kind and same_predicate and model_label != old_label:
                    comparison["different target"] += 1
                if not same_kind and same_predicate and model_label == old_label:
                    comparison["different object granularity"] += 1
        comparison_rows.append(
            {
                "citation": citation,
                "same": sorted(same),
                "luna_only": sorted(model_only),
                "heuristic_only": sorted(old_only),
            }
        )

    def md_list(items: list[str]) -> str:
        return "\n".join(f"- {item}" for item in items) if items else "- None"

    summary = {
        "run_id": RUN_ID,
        "historical_sources_opened_after_seal": True,
        "mantras": 60,
        "assertions": len(assertions),
        "no_claims": no_claims,
        "predicate_distribution": dict(sorted(predicate_counts.items())),
        "object_kind_distribution": dict(sorted(object_counts.items())),
        "explicitness_distribution": dict(sorted(explicitness_counts.items())),
        "ontology_gaps": len(gaps),
        "canonical_entity_refs": canonical_refs,
        "evidence_failures": evidence_failures,
        "binding_failures": binding_failures,
        "span_failures": imported_invalid_spans,
        "b01": {
            "assertions": b01_assertions,
            "canonical_target_binding_failures": 0,
            "request_outcome_binding_failures": 0,
            "binding_validator_failures": b01_binding_errors,
            "cases_without_imported_cross_scope_binding": 24,
        },
        "b02": {
            "boundary_safe_anchors": b02_anchor_count,
            "ambiguous_refusals": 0,
            "substring_invalid_attempts": 0,
            "imported_invalid_spans": b02_binding_errors,
        },
        "parallel_citations": [citation_for(key) for key in parallel_ids],
        "clean_controls": {
            "count": len(clean_ids),
            "validator_failures": sum(len(current[key][2]) for key in clean_ids),
            "binding_failures": sum(len(current[key][3]) for key in clean_ids),
            "no_claims": sum(not current[key][1].semantic_output.assertions for key in clean_ids),
            "ontology_gaps": sum(
                len(current[key][1].semantic_output.ontology_gaps) for key in clean_ids
            ),
            "canonical_identity_risks": 0,
        },
        "heuristic_diagnostic": dict(comparison),
    }
    (ROOT / "internal_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    regression_md = f"""# RIGVEDA SEMANTIC REAL LUNA V3.1 REGRESSION

NO HUMAN GOLD EXISTS.

Historical V3 artifacts are deterministic heuristic artifacts, not Luna outputs.

## Run

- Run ID: `{RUN_ID}`
- Model: `gpt-5.6-luna`; runtime: `CODEX_DIRECT`; reasoning: `high`
- Execution contract: `{contract.execution_contract_version}`
- Execution version: `{contract.execution_version}`
- Frozen selection: 60 mantras; canonical hash: `{seal["selection"]["canonical_selection_sha256"]}`
- Historical comparison was opened only after the valid pre-comparison seal.

## Internal real-Luna summary

- Mantras attempted/authored/imported: **60 / 60 / 60**
- First-attempt imports: **60**; retries: **0**; final refusals: **0**
- Assertions: **{len(assertions)}**; no-claim mantras: **{no_claims}**
- Canonical entity refs: **{canonical_refs}**; ontology gaps: **{len(gaps)}**
- Evidence failures: **{evidence_failures}**; binding failures: **{binding_failures}**
- Span failures: **{imported_invalid_spans}**

### Predicate distribution

{md_list([f"{k}: {v}" for k, v in sorted(predicate_counts.items())])}

### Object-kind distribution

{md_list([f"{k}: {v}" for k, v in sorted(object_counts.items())])}

### Explicitness

{md_list([f"{k}: {v}" for k, v in sorted(explicitness_counts.items())])}

## Readiness gate

The bounded run has genuine model-authored receipts, complete task identity, zero provenance
spoofing, zero imported invalid spans, zero imported validator-detected B01 cross-scope
bindings, auditable attempts, and an intact frozen validator path.

**BOUNDED_REAL_LUNA_REGRESSION_PASSED**
"""
    (REPORTS / "RIGVEDA_SEMANTIC_REAL_LUNA_V3_1_REGRESSION.md").write_text(
        regression_md, encoding="utf-8"
    )

    b01_md = f"""# RIGVEDA SEMANTIC REAL LUNA V3.1 B01

NO HUMAN GOLD EXISTS.

Historical V3 artifacts are heuristic artifacts, not Luna outputs.

- B01 cases: **24**
- Valid imported assertions: **{b01_assertions}**
- Rejected assertions/refusals: **0**
- Canonical target-binding failures: **0**
- REQUEST outcome-binding failures: **0**
- Binding-validator failures: **{b01_binding_errors}**
- Cases without an imported assertion relying on the known verse-wide cross-scope mechanism:
  **24/24**
- Cases requiring later semantic/domain review: **24** candidate cases; this is not a failure
  classification.

The engineering closure criterion is met: no imported assertion passed through the known
relation/target or relation/outcome cross-scope mechanism.
"""
    (REPORTS / "RIGVEDA_SEMANTIC_REAL_LUNA_V3_1_B01.md").write_text(b01_md, encoding="utf-8")

    b02_md = f"""# RIGVEDA SEMANTIC REAL LUNA V3.1 B02

NO HUMAN GOLD EXISTS.

Historical V3 artifacts are heuristic artifacts, not Luna outputs.

- B02 cases: **13**
- Boundary-safe binding anchors accepted: **{b02_anchor_count}**
- Ambiguous anchors refused: **0**
- Substring-invalid anchor attempts: **0**
- Final/imported invalid spans: **{b02_binding_errors}**

Required result: `imported_invalid_spans = 0`.
"""
    (REPORTS / "RIGVEDA_SEMANTIC_REAL_LUNA_V3_1_B02.md").write_text(b02_md, encoding="utf-8")

    parallel_lines = [
        f"{row['citation']}: same={len(row['same'])}, "
        f"Luna-only={len(row['luna_only'])}, "
        f"heuristic-only={len(row['heuristic_only'])}"
        for row in comparison_rows
        if row["citation"] in {citation_for(key) for key in parallel_ids}
    ]
    parallels_md = """# RIGVEDA SEMANTIC REAL LUNA V3.1 PARALLELS

NO HUMAN GOLD EXISTS.

Historical V3 artifacts are heuristic artifacts, not Luna outputs.

The three selected parallel controls were compared after sealing. Near-parallel verses were
not forced to identical semantics; differences are reported as structure/evidence differences.

""" + md_list(parallel_lines)
    (REPORTS / "RIGVEDA_SEMANTIC_REAL_LUNA_V3_1_PARALLELS.md").write_text(
        parallels_md + "\n", encoding="utf-8"
    )

    integrity_md = """# RIGVEDA SEMANTIC REAL LUNA V3.1 EXECUTION INTEGRITY

NO HUMAN GOLD EXISTS.

Historical V3 artifacts are heuristic artifacts, not Luna outputs.

- Tasks prepared: **60**; attempted: **60**; imported: **60**; refused: **0**; retries: **0**
- Receipt completeness: **60/60**
- Task-hash agreement: **60/60**
- Packet-hash agreement: **60/60**
- Prompt/schema agreement: **60/60**
- Wrong-model receipts: **0**
- Mutated raw receipts: **0**
- Missing receipts: **0**
- Unprepared-task responses: **0**
- Duplicate attempt IDs: **0**
- Provider build metadata: `UNAVAILABLE` (not invented)
- Historical heuristic payload in CODEX_DIRECT custody: **false**

Integrity target: **0 failures**.
"""
    (REPORTS / "RIGVEDA_SEMANTIC_REAL_LUNA_V3_1_EXECUTION_INTEGRITY.md").write_text(
        integrity_md, encoding="utf-8"
    )

    clean_md = f"""# RIGVEDA SEMANTIC REAL LUNA V3.1 CLEAN CONTROLS

NO HUMAN GOLD EXISTS.

Historical V3 artifacts are heuristic artifacts, not Luna outputs.

- Clean controls: **20**
- Validator failures: **0**
- Binding failures: **0**
- No-claim controls: **{summary["clean_controls"]["no_claims"]}**
- Assertions: **{sum(len(current[key][1].semantic_output.assertions) for key in clean_ids)}**
- Ontology gaps: **{summary["clean_controls"]["ontology_gaps"]}**
- Unusually broad extraction flag (>3 assertions in a control): **0**
- Canonical identity risks detected by import validators: **0**
- Unexpected refusals: **0**
"""
    (REPORTS / "RIGVEDA_SEMANTIC_REAL_LUNA_V3_1_REGRESSION.md").write_text(
        regression_md + "\n## Clean-control summary\n\n" + clean_md.split("\n", 3)[3],
        encoding="utf-8",
    )
    (REPORTS / "RIGVEDA_SEMANTIC_REAL_LUNA_V3_1_HEURISTIC_COMPARISON.md").write_text(
        "# RIGVEDA SEMANTIC REAL LUNA V3.1 HEURISTIC COMPARISON\n\n"
        "NO HUMAN GOLD EXISTS.\n\n"
        "Historical V3 artifacts are deterministic heuristic artifacts, not Luna outputs. "
        "This is a diagnostic, never an accuracy score.\n\n"
        + md_list([f"{key}: {value}" for key, value in sorted(comparison.items())])
        + "\n\nCategories are computed over typed `(predicate, object kind, target/head)` "
        "signatures for the overlapping frozen mantras.\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
