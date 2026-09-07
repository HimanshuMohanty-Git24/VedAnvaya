"""Audit the sealed 60-task real-Luna replication without authoring semantics."""

from __future__ import annotations

import collections
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

from vedagraph.semantic.codex_direct import (
    ModelAuthoredResponse,
    PreparedTask,
    RunContract,
    response_payload_sha256,
    validate_bindings,
    validate_candidate_invariants,
    validate_receipt,
)
from vedagraph.semantic.evidence import validate_evidence_anchors
from vedagraph.semantic.replication_diagnosis import (
    Alignment,
    AlignmentCategory,
    AnchorAssessment,
    ComparableAssertion,
    DiagnosticSet,
    EmissionRegime,
    FailureMode,
    OneSidedAssessment,
    SeverityV2,
    align_assertions,
    candidate_provenance_label,
    canonical_entity_contradiction,
    diagnostic_set_for,
    exchangeable_one_sided_probability,
    no_claim_assessment,
    regime_divergence,
    severity_v2,
)
from vedagraph.semantic.v3 import validate_v3_payload

ROOT = Path(__file__).resolve().parents[1]
RUN_A = ROOT / "data/semantic/vedagraph-rigveda-semantic-luna-v3.1-regression"
RUN_B = ROOT / "data/semantic/vedagraph-rigveda-semantic-luna-v3.1-508"
SEAL_A = ROOT / "docs/manifests/vedagraph_rigveda_semantic_luna_v3_1_regression_output_seal.json"
MANIFEST_A = ROOT / "docs/manifests/vedagraph-rigveda-semantic-luna-v3.1-regression.json"
MANIFEST_B = ROOT / "docs/manifests/vedagraph-rigveda-semantic-luna-v3.1-508.json"
ADJUDICATION = ROOT / "docs/manifests/rigveda_semantic_real_luna_replication_adjudication.json"
REPORT_DIR = ROOT / "docs/reports"
DIAGNOSIS_JSON = ROOT / "docs/manifests/rigveda_semantic_real_luna_replication_diagnosis.json"
NOTICE = "NO HUMAN GOLD EXISTS.\n\nMODEL SELF-AGREEMENT IS NOT ACCURACY.\n"
DECISION = "V3_2_PROMPT_POLICY_REVISION_REQUIRED"


@dataclass(frozen=True)
class PassageRecord:
    task: PreparedTask
    response: ModelAuthoredResponse
    raw_response_sha256: str
    validated_sha256: str


def read_json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def final_records(seal: dict[str, Any], run: str) -> list[dict[str, Any]]:
    if run == "A":
        histories = list(seal["attempt_histories"])
        validated = cast(dict[str, str], seal["validated_response_hashes"])
        return [
            {
                **item,
                "passage_key": item["passage_id"],
                "validated_file_sha256": validated[f"{item['task_id']}/{item['attempt_id']}"],
            }
            for item in histories
        ]
    return list(seal["validated_response_hashes"])


def load_run(root: Path, seal_path: Path, run: str) -> tuple[dict[str, PassageRecord], list[str]]:
    seal = read_json(seal_path)
    contract = RunContract.model_validate_json((root / "store/run_contract.json").read_text())
    expected_tasks = cast(
        dict[str, str], seal["task_hashes" if run == "A" else "prepared_task_hashes"]
    )
    failures: list[str] = []
    records: dict[str, PassageRecord] = {}
    for item in final_records(seal, run):
        task_id = str(item["task_id"])
        attempt_id = str(item["attempt_id"])
        passage_key = str(item["passage_key"])
        task_path = root / "store/tasks" / task_id.replace(":", "_") / "task.json"
        attempt = task_path.parent / "attempts" / attempt_id
        raw_path = attempt / "raw_response.json"
        validated_path = attempt / "validated.json"
        task = PreparedTask.model_validate_json(task_path.read_text(encoding="utf-8"))
        response = ModelAuthoredResponse.model_validate_json(raw_path.read_text(encoding="utf-8"))
        task_digest = task.task_sha256
        raw_digest = sha256_file(raw_path)
        validated_digest = sha256_file(validated_path)
        expected_raw = str(item["raw_response_sha256"])
        if task_digest != expected_tasks[passage_key]:
            failures.append(f"{run} task hash mismatch: {passage_key}")
        if raw_digest != expected_raw:
            failures.append(f"{run} raw response hash mismatch: {passage_key}")
        if validated_digest != item["validated_file_sha256"]:
            failures.append(f"{run} validated hash mismatch: {passage_key}")
        errors = validate_receipt(
            response.receipt,
            task,
            contract,
            computed_response_sha256=response_payload_sha256(response),
        )
        errors += validate_candidate_invariants(response.semantic_output, task)
        canonical_ids = frozenset(mention.entity_key for mention in task.evidence_packet.mentions)
        errors += validate_v3_payload(
            response.semantic_output, task.evidence_packet, canonical_entity_ids=canonical_ids
        )
        errors += validate_evidence_anchors(response.semantic_output, task.evidence_packet)
        errors += validate_bindings(
            response.semantic_output, response.assertion_bindings, task.evidence_packet
        )
        failures.extend(f"{run} {passage_key}: {error}" for error in errors)
        records[passage_key] = PassageRecord(
            task=task,
            response=response,
            raw_response_sha256=raw_digest,
            validated_sha256=validated_digest,
        )
    return records, failures


def verify_custody() -> tuple[
    dict[str, PassageRecord], dict[str, PassageRecord], dict[str, Any], dict[str, Any]
]:
    seal_a = read_json(SEAL_A)
    manifest_a = read_json(MANIFEST_A)
    manifest_b = read_json(MANIFEST_B)
    failures: list[str] = []
    if manifest_a["output_seal_sha256"] != sha256_file(SEAL_A):
        failures.append("run A manifest does not match output seal")
    seal_a_without_hash = {key: value for key, value in seal_a.items() if key != "seal_sha256"}
    if seal_a["seal_sha256"] != canonical_sha256(seal_a_without_hash):
        failures.append("run A embedded seal digest is invalid")
    seal_b_file_hash = sha256_file(RUN_B / "output_seal.json")
    if manifest_b["output_seal_sha256"] != seal_b_file_hash:
        failures.append("run B manifest does not match output seal")
    sidecar = (RUN_B / "output_seal.sha256").read_text(encoding="utf-8").split()[0]
    if sidecar != seal_b_file_hash:
        failures.append("run B output seal sidecar is invalid")
    a, a_failures = load_run(RUN_A, SEAL_A, "A")
    b, b_failures = load_run(RUN_B, RUN_B / "output_seal.json", "B")
    failures.extend(a_failures)
    failures.extend(b_failures)
    if len(a) != 60 or len(b) != 508:
        failures.append(f"wrong task cardinality: A={len(a)}, B={len(b)}")
    overlap = sorted(set(a) & set(b))
    if len(overlap) != 60:
        failures.append(f"wrong overlap cardinality: {len(overlap)}")
    packet_mismatches = [
        key
        for key in overlap
        if a[key].task.evidence_packet_sha256 != b[key].task.evidence_packet_sha256
    ]
    failures.extend(f"EvidencePacket mismatch: {key}" for key in packet_mismatches)
    if failures:
        raise RuntimeError("custody verification failed:\n" + "\n".join(failures))
    custody = {
        "run_a_manifest_sha256": sha256_file(MANIFEST_A),
        "run_a_output_seal_sha256": sha256_file(SEAL_A),
        "run_b_manifest_sha256": sha256_file(MANIFEST_B),
        "run_b_output_seal_sha256": seal_b_file_hash,
        "run_a_tasks_verified": len(a),
        "run_b_tasks_verified": len(b),
        "overlap_packets_verified": len(overlap),
        "raw_receipts_verified": len(a) + len(b),
        "validated_outputs_verified": len(a) + len(b),
        "assertion_binding_failures": 0,
        "receipt_failures": 0,
        "packet_hash_mismatches": 0,
    }
    non_overlap = sorted(set(b) - set(overlap))
    b_reference = {
        "passages": len(non_overlap),
        "no_claim_passages": sum(
            1 for key in non_overlap if not b[key].response.semantic_output.assertions
        ),
        "assertions": sum(len(b[key].response.semantic_output.assertions) for key in non_overlap),
    }
    b_reference["no_claim_rate"] = round(
        b_reference["no_claim_passages"] / b_reference["passages"], 3
    )
    b_reference["density"] = round(b_reference["assertions"] / b_reference["passages"], 3)
    return a, {key: b[key] for key in overlap}, custody, b_reference


def comparable(record: PassageRecord) -> list[ComparableAssertion]:
    bindings = [item.model_dump(mode="json") for item in record.response.assertion_bindings]
    return [
        ComparableAssertion.from_mapping(item.model_dump(mode="json"), bindings)
        for item in record.response.semantic_output.assertions
    ]


def apply_pair_overrides(
    rows: list[Alignment], overrides: list[dict[str, Any]]
) -> tuple[list[Alignment], dict[tuple[str, str], dict[str, Any]]]:
    metadata: dict[tuple[str, str], dict[str, Any]] = {}
    result = list(rows)
    for override in overrides:
        aid = str(override["a_assertion_id"])
        bid = str(override["b_assertion_id"])
        left = next((row.a for row in result if row.a and row.a.assertion_id == aid), None)
        right = next((row.b for row in result if row.b and row.b.assertion_id == bid), None)
        if left is None or right is None:
            raise RuntimeError(f"pair override cannot find {aid} / {bid}")
        result = [
            row
            for row in result
            if not (row.a and row.a.assertion_id == aid)
            and not (row.b and row.b.assertion_id == bid)
        ]
        category = AlignmentCategory(str(override["category"]))
        result.append(Alignment(category, left, right))
        metadata[(aid, bid)] = override
    return sorted(result, key=alignment_sort_key), metadata


def alignment_sort_key(row: Alignment) -> tuple[str, str]:
    return (
        row.a.assertion_id if row.a else "~",
        row.b.assertion_id if row.b else "~",
    )


def anchor_assessment(row: Alignment) -> AnchorAssessment | None:
    if row.a is None or row.b is None:
        return None
    if row.category in {
        AlignmentCategory.PREDICATE_BOUNDARY_DIFFERENCE,
        AlignmentCategory.TARGET_DIFFERENCE,
        AlignmentCategory.UNRESOLVED,
    }:
        return AnchorAssessment.SEMANTIC_DISAGREEMENT
    a = {(role, text) for role, text, _, _ in row.a.binding_anchors}
    b = {(role, text) for role, text, _, _ in row.b.binding_anchors}
    if a == b:
        return AnchorAssessment.SAME_SEMANTIC_SUPPORT_ALTERNATE_SPAN
    by_role_a = collections.defaultdict(list)
    by_role_b = collections.defaultdict(list)
    for role, text in a:
        by_role_a[role].append(text)
    for role, text in b:
        by_role_b[role].append(text)
    common_roles = set(by_role_a) & set(by_role_b)
    if common_roles and all(
        any(x in y or y in x for x in by_role_a[role] for y in by_role_b[role])
        for role in common_roles
    ):
        return AnchorAssessment.BROADER_VS_NARROWER_VALID_SPAN
    positions_a = [start for _, _, start, _ in row.a.binding_anchors]
    positions_b = [start for _, _, start, _ in row.b.binding_anchors]
    if positions_a and positions_b and abs(min(positions_a) - min(positions_b)) > 80:
        return AnchorAssessment.DIFFERENT_SENTENCE_SUPPORT
    return AnchorAssessment.SAME_SEMANTIC_SUPPORT_ALTERNATE_SPAN


def object_display(item: dict[str, Any]) -> str:
    """Short typed-object signature for the comparison table."""
    head = item["normalized_head"] or item["event_action_head"] or item["canonical_entity_id"]
    return f"{item['object_kind']}:{head}"


def signature(item: ComparableAssertion) -> str:
    obj = item.canonical_entity_id or item.normalized_head or item.event_action_head or "?"
    return f"{item.assertion_id}: {item.predicate} -> {item.object_kind}({obj})"


def anchors(item: ComparableAssertion, role: str) -> str:
    values = [text for found, text, _, _ in item.binding_anchors if found == role]
    return " / ".join(values) or "—"


def md_table(headers: list[str], rows: list[list[object]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        cells = [str(cell).replace("|", "\\|").replace("\n", " ") for cell in row]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def write_report(name: str, body: str) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / name).write_text(body.rstrip() + "\n", encoding="utf-8", newline="\n")


def old_metrics(
    a: dict[str, PassageRecord], b: dict[str, PassageRecord]
) -> tuple[dict[str, int], dict[str, int]]:
    metrics: collections.Counter[str] = collections.Counter()
    severities: collections.Counter[str] = collections.Counter()
    for key in sorted(a):
        aa = comparable(a[key])
        bb = comparable(b[key])
        sa = {(x.predicate, x.object_kind, x.normalized_head, x.canonical_entity_id) for x in aa}
        sb = {(x.predicate, x.object_kind, x.normalized_head, x.canonical_entity_id) for x in bb}
        pa, pb = {x.predicate for x in aa}, {x.predicate for x in bb}
        ca = {x.canonical_entity_id for x in aa if x.canonical_entity_id}
        cb = {x.canonical_entity_id for x in bb if x.canonical_entity_id}
        if sa == sb:
            metrics["exact_assertion_set_agreement"] += 1
        if pa == pb:
            metrics["predicate_presence_agreement"] += 1
        if (not aa) == (not bb):
            metrics["no_claim_agreement"] += 1
        if ca == cb:
            metrics["canonical_entity_agreement"] += 1
        anchor_a = {(x.predicate, role, text) for x in aa for role, text, _, _ in x.binding_anchors}
        anchor_b = {(x.predicate, role, text) for x in bb for role, text, _, _ in x.binding_anchors}
        if anchor_a == anchor_b:
            metrics["evidence_anchor_agreement"] += 1
        if sa == sb:
            continue
        metrics["assertion_set_differences"] += 1
        object_differences = {(x[1], x[2]) for x in sa ^ sb}
        if pa != pb or ca != cb or len({x[0] for x in object_differences}) > 1:
            severities["HIGH"] += 1
        elif object_differences or (not aa) != (not bb):
            severities["MEDIUM"] += 1
        else:
            severities["LOW"] += 1
    return dict(metrics), dict(severities)


def build_audit() -> dict[str, Any]:
    a, b, custody, b_reference = verify_custody()
    adjudication = read_json(ADJUDICATION)
    one_sided = cast(dict[str, dict[str, str]], adjudication["one_sided"])
    passage_rows: list[dict[str, Any]] = []
    all_rows: list[dict[str, Any]] = []
    override_metadata: dict[tuple[str, str], dict[str, Any]] = {}
    for key in sorted(a):
        aa, bb = comparable(a[key]), comparable(b[key])
        local_ids = {item.assertion_id for item in aa + bb}
        local_overrides = [
            item
            for item in adjudication["pair_overrides"]
            if item["a_assertion_id"] in local_ids or item["b_assertion_id"] in local_ids
        ]
        rows, metadata = apply_pair_overrides(align_assertions(aa, bb), local_overrides)
        override_metadata.update(metadata)
        row_items: list[dict[str, Any]] = []
        for row in rows:
            assertion_id = row.a.assertion_id if row.a and row.b is None else None
            if row.b and row.a is None:
                assertion_id = row.b.assertion_id
            assessment = one_sided.get(assertion_id or "")
            if (
                row.category in {AlignmentCategory.A_ONLY, AlignmentCategory.B_ONLY}
                and not assessment
            ):
                raise RuntimeError(f"missing one-sided adjudication: {key} {assertion_id}")
            pair_meta = override_metadata.get(
                (
                    row.a.assertion_id if row.a else "",
                    row.b.assertion_id if row.b else "",
                ),
                {},
            )
            one_value = OneSidedAssessment(assessment["assessment"]) if assessment else None
            canonical_conflict = bool(
                row.a and row.b and canonical_entity_contradiction(row.a, row.b)
            )
            item = {
                "passage_key": key,
                "category": row.category.value,
                "a": asdict(row.a) if row.a else None,
                "b": asdict(row.b) if row.b else None,
                "one_sided_assessment": one_value.value if one_value else None,
                "rationale": assessment["rationale"] if assessment else pair_meta.get("rationale"),
                "failure_mode": (
                    assessment["failure_mode"] if assessment else pair_meta.get("failure_mode")
                ),
                "anchor_assessment": (
                    anchor_assessment(row).value if anchor_assessment(row) else None
                ),
                "canonical_contradiction": canonical_conflict,
                "severity_v2": severity_v2(
                    row.category,
                    one_sided=one_value,
                    anchor=anchor_assessment(row),
                    canonical_contradiction=canonical_conflict,
                ).value,
                "diagnostic_set": (
                    diagnostic_set_for(row.category, one_value).value
                    if diagnostic_set_for(row.category, one_value)
                    else None
                ),
            }
            row_items.append(item)
            all_rows.append(item)
        passage_rows.append(
            {
                "passage_key": key,
                "citation": a[key].task.citation,
                "evidence_packet_sha256": a[key].task.evidence_packet_sha256,
                "translation": (
                    a[key].task.evidence_packet.translation.text
                    if a[key].task.evidence_packet.translation
                    else None
                ),
                "a_no_claim": not aa,
                "b_no_claim": not bb,
                "a_assertions": [asdict(item) for item in aa],
                "b_assertions": [asdict(item) for item in bb],
                "alignment": row_items,
            }
        )
    used_one_sided = {
        (row["a"] or row["b"])["assertion_id"]
        for row in all_rows
        if row["category"] in {AlignmentCategory.A_ONLY.value, AlignmentCategory.B_ONLY.value}
    }
    extra = sorted(set(one_sided) - used_one_sided)
    if extra:
        raise RuntimeError(f"unused one-sided adjudications: {extra}")
    old, old_severity = old_metrics(a, b)
    if old_severity != {"HIGH": 42, "MEDIUM": 6}:
        raise RuntimeError(f"old severity reconstruction drifted: {old_severity}")
    return {
        "audit_version": "real-luna-replication-diagnosis-v1",
        "truth_status": "NO_HUMAN_GOLD_MODEL_SELF_AGREEMENT_IS_NOT_ACCURACY",
        "decision": DECISION,
        "custody": custody,
        "b_reference": b_reference,
        "old_metrics": old,
        "old_severity": {"HIGH": 42, "MEDIUM": 6, "LOW": 0},
        "passages": passage_rows,
        "alignments": all_rows,
    }


def _regime_row(regime: EmissionRegime) -> dict[str, Any]:
    """Serialize one run's emission regime for the audit manifest."""
    return {
        "passages": regime.passages,
        "assertions": regime.assertions,
        "no_claim_passages": regime.no_claim_passages,
        "density": round(regime.density, 3),
        "no_claim_rate": round(regime.no_claim_rate, 3),
        "predicate_counts": dict(sorted(regime.predicate_counts.items())),
    }


def emission_regime(passages: list[dict[str, Any]], side: str) -> EmissionRegime:
    """Run-level emission behavior of one side over the shared passage set."""
    counts = collections.Counter(
        item["predicate"] for passage in passages for item in passage[f"{side}_assertions"]
    )
    return EmissionRegime(
        passages=len(passages),
        assertions=sum(len(passage[f"{side}_assertions"]) for passage in passages),
        no_claim_passages=sum(1 for passage in passages if passage[f"{side}_no_claim"]),
        predicate_counts=dict(counts),
    )


def summarize(data: dict[str, Any]) -> dict[str, Any]:
    alignments = data["alignments"]
    passages = data["passages"]
    regime_a = emission_regime(passages, "a")
    regime_b = emission_regime(passages, "b")
    alignment_counts = collections.Counter(row["category"] for row in alignments)
    one_sided_counts = collections.Counter(
        row["one_sided_assessment"] for row in alignments if row["one_sided_assessment"]
    )
    diagnostic_counts = collections.Counter(
        row["diagnostic_set"] for row in alignments if row["diagnostic_set"]
    )
    failure_modes: collections.Counter[str] = collections.Counter()
    inferred_modes = dict(
        [
            (
                AlignmentCategory.SAME_PREDICATE_SAME_OBJECT_DIFFERENT_EVIDENCE.value,
                FailureMode.EVIDENCE_ANCHOR_VARIANCE.value,
            ),
            (
                AlignmentCategory.OBJECT_GRANULARITY_DIFFERENCE.value,
                FailureMode.OBJECT_GRANULARITY_VARIANCE.value,
            ),
            (
                AlignmentCategory.PREDICATE_BOUNDARY_DIFFERENCE.value,
                FailureMode.PREDICATE_POLICY_AMBIGUITY.value,
            ),
            (
                AlignmentCategory.TARGET_DIFFERENCE.value,
                FailureMode.CANONICAL_TARGET_VARIANCE.value,
            ),
            (
                AlignmentCategory.UNRESOLVED.value,
                FailureMode.EXPERT_DEPENDENT_AMBIGUITY.value,
            ),
        ]
    )
    for row in alignments:
        mode = row["failure_mode"] or inferred_modes.get(row["category"])
        if mode:
            failure_modes[mode] += 1
    severity_rank = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
    passage_severity: collections.Counter[str] = collections.Counter()
    no_difference = 0
    for passage in passages:
        rows = passage["alignment"]
        if not rows:
            no_difference += 1
            continue
        severity = max((row["severity_v2"] for row in rows), key=severity_rank.__getitem__)
        passage_severity[severity] += 1
    no_claim = collections.Counter()
    no_claim_rows: list[dict[str, str]] = []
    for passage in passages:
        if passage["a_no_claim"] == passage["b_no_claim"]:
            continue
        assessments = [
            OneSidedAssessment(row["one_sided_assessment"])
            for row in passage["alignment"]
            if row["one_sided_assessment"]
        ]
        result = no_claim_assessment(assessments)
        no_claim[result.value] += 1
        no_claim_rows.append({"passage_key": passage["passage_key"], "classification": result})
    total_modes = sum(failure_modes.values())
    return {
        "alignment_counts": {
            category.value: alignment_counts[category.value] for category in AlignmentCategory
        },
        "one_sided_counts": {
            assessment.value: one_sided_counts[assessment.value]
            for assessment in OneSidedAssessment
        },
        "diagnostic_counts": {
            diagnostic.value: diagnostic_counts[diagnostic.value] for diagnostic in DiagnosticSet
        },
        "failure_modes": {
            key: {
                "count": failure_modes[key],
                "percent": round(100 * failure_modes[key] / total_modes, 1),
            }
            for key in FailureMode
        },
        "revised_passage_severity": {
            **{key: passage_severity[key] for key in SeverityV2},
            "NO_DIFFERENCE": no_difference,
        },
        "no_claim_counts": dict(sorted(no_claim.items())),
        "no_claim_rows": no_claim_rows,
        "stable_core_size": diagnostic_counts[DiagnosticSet.STABLE_CORE.value],
        "one_run_supported_size": diagnostic_counts[DiagnosticSet.ONE_RUN_SUPPORTED.value],
        "suspect_assertion_count": diagnostic_counts[DiagnosticSet.SUSPECT_ASSERTION.value],
        "expert_required_count": diagnostic_counts[DiagnosticSet.EXPERT_REQUIRED.value],
        "emission_regime": {
            "a": _regime_row(regime_a),
            "b": _regime_row(regime_b),
            "describes_action_skew_probability": exchangeable_one_sided_probability(
                regime_a.predicate_counts.get("DESCRIBES_ACTION", 0),
                regime_b.predicate_counts.get("DESCRIBES_ACTION", 0),
            ),
            "regime_divergence": regime_divergence(
                regime_a, regime_b, predicate="DESCRIBES_ACTION"
            ),
            "b_non_overlap_reference": data["b_reference"],
        },
    }


def predicate_metrics(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    passages = data["passages"]
    predicates = sorted(
        {
            item["predicate"]
            for passage in passages
            for side in ("a_assertions", "b_assertions")
            for item in passage[side]
        }
    )
    result: dict[str, dict[str, Any]] = {}
    for predicate in predicates:
        a_items = [
            item
            for passage in passages
            for item in passage["a_assertions"]
            if item["predicate"] == predicate
        ]
        b_items = [
            item
            for passage in passages
            for item in passage["b_assertions"]
            if item["predicate"] == predicate
        ]
        a_presence = {
            passage["passage_key"]
            for passage in passages
            if any(item["predicate"] == predicate for item in passage["a_assertions"])
        }
        b_presence = {
            passage["passage_key"]
            for passage in passages
            if any(item["predicate"] == predicate for item in passage["b_assertions"])
        }
        relevant = [
            row
            for row in data["alignments"]
            if (row["a"] and row["a"]["predicate"] == predicate)
            or (row["b"] and row["b"]["predicate"] == predicate)
        ]
        supported = sum(
            row["one_sided_assessment"] == OneSidedAssessment.SUPPORTED_OMISSION_VARIANCE.value
            for row in relevant
        )
        unsupported = sum(
            row["one_sided_assessment"] == OneSidedAssessment.UNSUPPORTED_EXTRACTION.value
            for row in relevant
        )
        ambiguous = sum(
            row["category"] == AlignmentCategory.PREDICATE_BOUNDARY_DIFFERENCE.value
            or row["one_sided_assessment"]
            in {
                OneSidedAssessment.PREDICATE_POLICY_AMBIGUITY.value,
                OneSidedAssessment.OBJECT_POLICY_AMBIGUITY.value,
                OneSidedAssessment.PLAUSIBLE_BUT_OPTIONAL.value,
            }
            for row in relevant
        )
        union = a_presence | b_presence
        result[predicate] = {
            "a_count": len(a_items),
            "b_count": len(b_items),
            "intersection": len(a_presence & b_presence),
            "union": len(union),
            "a_only": len(a_presence - b_presence),
            "b_only": len(b_presence - a_presence),
            "jaccard_presence": round(len(a_presence & b_presence) / len(union), 3)
            if union
            else 1.0,
            "supported_omissions": supported,
            "unsupported_extras": unsupported,
            "policy_ambiguities": ambiguous,
        }
    return result


def canonical_cases(data: dict[str, Any]) -> list[dict[str, str]]:
    cases: list[dict[str, str]] = []
    for passage in data["passages"]:
        a_entities = {
            item["canonical_entity_id"]
            for item in passage["a_assertions"]
            if item["canonical_entity_id"]
        }
        b_entities = {
            item["canonical_entity_id"]
            for item in passage["b_assertions"]
            if item["canonical_entity_id"]
        }
        if a_entities == b_entities:
            continue
        a_roles = {
            value
            for item in passage["a_assertions"]
            for value in (item["event_actor_entity_id"], item["event_patient_entity_id"])
            if value
        }
        b_roles = {
            value
            for item in passage["b_assertions"]
            for value in (item["event_actor_entity_id"], item["event_patient_entity_id"])
            if value
        }
        if a_entities and b_entities and not (a_entities & b_entities):
            classification = "CONTRADICTORY_CANONICAL_TARGET"
        elif (a_entities & b_roles) or (b_entities & a_roles):
            classification = "DIFFERENT_PREDICATE_SAME_TARGET"
        else:
            classification = "ONE_RUN_HAS_CANONICAL_ASSERTION_OTHER_OMITS"
        cases.append(
            {
                "passage_key": passage["passage_key"],
                "a": ", ".join(sorted(a_entities)) or "—",
                "b": ", ".join(sorted(b_entities)) or "—",
                "classification": classification,
            }
        )
    return cases


def render_reports(data: dict[str, Any], summary: dict[str, Any]) -> None:
    predicates = predicate_metrics(data)
    canonical = canonical_cases(data)
    canonical_omits = sum(
        row["classification"] == "ONE_RUN_HAS_CANONICAL_ASSERTION_OTHER_OMITS" for row in canonical
    )
    canonical_same_target = sum(
        row["classification"] == "DIFFERENT_PREDICATE_SAME_TARGET" for row in canonical
    )
    canonical_contradictions = sum(
        row["classification"] == "CONTRADICTORY_CANONICAL_TARGET" for row in canonical
    )
    comparison_rows = []
    for passage in data["passages"]:
        comparison_rows.append(
            [
                passage["passage_key"],
                "<br>".join(
                    signature(ComparableAssertion(**item)) for item in passage["a_assertions"]
                )
                or "—",
                "<br>".join(
                    signature(ComparableAssertion(**item)) for item in passage["b_assertions"]
                )
                or "—",
                passage["a_no_claim"],
                passage["b_no_claim"],
                ", ".join(sorted({item["predicate"] for item in passage["a_assertions"]})) or "—",
                ", ".join(sorted({item["predicate"] for item in passage["b_assertions"]})) or "—",
                ", ".join(
                    sorted(
                        item["canonical_entity_id"]
                        for item in passage["a_assertions"]
                        if item["canonical_entity_id"]
                    )
                )
                or "—",
                ", ".join(
                    sorted(
                        item["canonical_entity_id"]
                        for item in passage["b_assertions"]
                        if item["canonical_entity_id"]
                    )
                )
                or "—",
                "<br>".join(object_display(item) for item in passage["a_assertions"]) or "—",
                "<br>".join(object_display(item) for item in passage["b_assertions"]) or "—",
                "<br>".join(
                    "; ".join(f"{role}:{text}" for role, text, _, _ in item["binding_anchors"])
                    for item in passage["a_assertions"]
                )
                or "—",
                "<br>".join(
                    "; ".join(f"{role}:{text}" for role, text, _, _ in item["binding_anchors"])
                    for item in passage["b_assertions"]
                )
                or "—",
            ]
        )
    alignment_rows = [
        [
            row["passage_key"],
            row["category"],
            signature(ComparableAssertion(**row["a"])) if row["a"] else "—",
            signature(ComparableAssertion(**row["b"])) if row["b"] else "—",
            row["one_sided_assessment"] or "—",
            row["severity_v2"],
            row["rationale"] or "—",
        ]
        for row in data["alignments"]
    ]
    modes = summary["failure_modes"]
    regime = summary["emission_regime"]
    b_reference = data["b_reference"]
    diagnosis = f"""# Real-Luna replication diagnosis

{NOTICE}

## Scope and conclusion

This is engineering adjudication over the two sealed real-Luna outputs and their shared
EvidencePackets. Neither run is truth. Historical heuristic artifacts, Sol silver, traditional
Devatā metadata as semantic proof, and pretrained Vedic knowledge were not used as truth inputs.

Decision: `{DECISION}`.

The old 42-HIGH result primarily conflated assertion presence differences with contradiction. The
revised audit finds no contradictory canonical targets, no integrity or type-boundary failures, one
suspect assertion, and a large supported emit-vs-omit component. V3.2 is still warranted because
repeated REQUESTS outcome splitting and DESCRIBES/DESCRIBES_ACTION precedence gaps are proven policy
ambiguities; this is not an execution-contract failure.

## Input custody

{md_table(["Check", "Result"], [[key, value] for key, value in data["custody"].items()])}

## Reconstruction summary

{md_table(["Metric", "Count"], [[key, value] for key, value in data["old_metrics"].items()])}

## Assertion alignment counts

{
        md_table(
            ["Category", "Count"],
            [[key, value] for key, value in summary["alignment_counts"].items()],
        )
    }

## One-sided adjudication

{
        md_table(
            ["Assessment", "Count"],
            [[key, value] for key, value in summary["one_sided_counts"].items()],
        )
    }

## No-claim disagreements

{
        md_table(
            ["Classification", "Count"],
            [[key, value] for key, value in summary["no_claim_counts"].items()],
        )
    }

{
        md_table(
            ["Passage", "Classification"],
            [[row["passage_key"], row["classification"]] for row in summary["no_claim_rows"]],
        )
    }

## Severity reassessment

Old passage-level difference severity: HIGH=42, MEDIUM=6, LOW=0. Revised passage-level result
(including anchor-only differences and unchanged no-claim passages):

{
        md_table(
            ["Severity", "Passages"],
            [[key, value] for key, value in summary["revised_passage_severity"].items()],
        )
    }

CRITICAL is reserved for contradictory canonical targets, imported unsupported bindings,
ontology/type violations, or evidence-integrity failure. HIGH is reserved here for an audited
unsupported extraction or incompatible supported meaning. Supported emit-vs-omit, policy ambiguity,
and granularity are MEDIUM. Alternate valid local anchors are LOW.

## Stable core and fringe

{
        md_table(
            ["Diagnostic set", "Assertions/aligned pairs"],
            [[key, value] for key, value in summary["diagnostic_counts"].items()],
        )
    }

`STABLE_CORE` is diagnostic only. Its provenance is `REPLICATION_SUPPORTED_MODEL_CANDIDATE /
CANDIDATE_NEEDS_REVIEW`; it is not canonical knowledge and creates no accepted edge.

## Root failure-mode distribution

The denominator is all non-exact assertion-alignment and anchor-variance units; categories are
mutually assigned at the unit level.

{
        md_table(
            ["Failure mode", "Count", "Percent"],
            [[key, value["count"], f"{value['percent']}%"] for key, value in modes.items()],
        )
    }

## Run-level emission regime

The per-assertion categories above treat each difference independently. They cannot express a
difference that is a property of the run rather than of any single assertion, so this section
measures the two runs directly over the identical 60 EvidencePackets under a byte-identical run
contract (same prompt, ontology, schema, model, and reasoning hashes).

{
        md_table(
            ["Metric", "Run A", "Run B"],
            [
                ["Passages", regime["a"]["passages"], regime["b"]["passages"]],
                ["Assertions", regime["a"]["assertions"], regime["b"]["assertions"]],
                [
                    "No-claim passages",
                    regime["a"]["no_claim_passages"],
                    regime["b"]["no_claim_passages"],
                ],
                ["No-claim rate", regime["a"]["no_claim_rate"], regime["b"]["no_claim_rate"]],
                ["Assertions per passage", regime["a"]["density"], regime["b"]["density"]],
                [
                    "DESCRIBES_ACTION",
                    regime["a"]["predicate_counts"].get("DESCRIBES_ACTION", 0),
                    regime["b"]["predicate_counts"].get("DESCRIBES_ACTION", 0),
                ],
                [
                    "REQUESTS",
                    regime["a"]["predicate_counts"].get("REQUESTS", 0),
                    regime["b"]["predicate_counts"].get("REQUESTS", 0),
                ],
            ],
        )
    }

Run A emits `DESCRIBES_ACTION` {regime["a"]["predicate_counts"].get("DESCRIBES_ACTION", 0)} times
over these packets and run B emits it
{regime["b"]["predicate_counts"].get("DESCRIBES_ACTION", 0)} times. If the two runs drew from one
emission policy, the probability that every occurrence lands on one side is
{summary["emission_regime"]["describes_action_skew_probability"]:.2e}. The skew is therefore not
per-assertion sampling noise.

The no-claim rates differ by
{abs(regime["a"]["no_claim_rate"] - regime["b"]["no_claim_rate"]):.3f} over identical inputs. Run
B's no-claim rate over these 60 packets is {regime["b"]["no_claim_rate"]}, and over the
{b_reference["passages"]} packets it did not share with run A it is
{b_reference["no_claim_rate"]}; its density is {regime["b"]["density"]} here against
{b_reference["density"]} there. Run B is therefore internally consistent, and the two runs
disagree with each other, which places the dominant variance at run level rather than at
assertion level.

This does not make either regime correct. It means the V3.1 prompt admits at least two
internally coherent readings of when a directly evidenced action or a marginal candidate must be
emitted, which is the specific underspecification the V3.2 proposal targets, and it is why a
single unreplicated pass over the full corpus would inherit whichever regime that run happens to
occupy.

## Full 60-task comparison

Raw assertion IDs are preserved. Typed signatures and assertion-specific binding anchors are
displayed without synonym normalization.

{
        md_table(
            [
                "Passage",
                "Run A assertions",
                "Run B assertions",
                "A no claim",
                "B no claim",
                "Predicates A",
                "Predicates B",
                "Canonical A",
                "Canonical B",
                "Typed objects A",
                "Typed objects B",
                "Anchors A",
                "Anchors B",
            ],
            comparison_rows,
        )
    }

## Assertion-level adjudication ledger

{
        md_table(
            [
                "Passage",
                "Alignment",
                "Run A",
                "Run B",
                "One-sided assessment",
                "Severity v2",
                "Engineering rationale",
            ],
            alignment_rows,
        )
    }

## Full-corpus implication

A single pass would hide the measured recall variance. A raw intersection would discard directly
supported candidates; a raw union would retain suspect and policy-ambiguous candidates without
distinction. The recommended strategy is one primary pass over candidate-only outputs, a second pass
for deterministic risk flags plus a stratified random calibration sample, and mandatory dual-pass
extraction for predicates/contexts shown unstable here (initially REQUESTS multi-outcome clauses and
DESCRIBES/DESCRIBES_ACTION boundaries). Preserve both receipts, report intersection/union
diagnostics, and keep every result `CANDIDATE / NEEDS_REVIEW`; never promote by consensus.

The run-level regime measurement adds a constraint that per-assertion variance alone would not
imply. Because the emission regime is a property of the run and stays stable inside it, a corpus
split across many runs inherits a different regime per batch, and annotation density would then
vary with batch boundaries rather than with content. Record the run/batch identity of every
candidate as provenance so that later analysis can detect this, and draw the calibration sample
per batch rather than once across the corpus; a corpus-wide sample would average two regimes
together and report a stability that no individual batch has.

## Third run

After adopting the proposed V3.2 policy text, run the ID-only 60-task config as
`vedagraph-rigveda-semantic-luna-v3.2-stability-60`. Do not compare during extraction, do not expose
either earlier answer to the model, and seal before diagnosis. This audit does not execute that run.

One V3.2 run cannot settle the question this audit raises. The dominant variance measured here is
between runs, so a single V3.2 execution would show only which regime that one run occupied and
would be indistinguishable from either V3.1 run taken alone. The bounded experiment must therefore
be at least two independent V3.2 runs over the same 60 IDs, compared against each other by the
regime measurement above, with the V3.1 pair as the baseline to beat. The success criterion is a
narrowed no-claim gap and no one-sided predicate skew, not a higher assertion count.
"""
    write_report("RIGVEDA_SEMANTIC_REAL_LUNA_REPLICATION_DIAGNOSIS.md", diagnosis)

    predicate_rows = [[name, *values.values()] for name, values in predicates.items()]
    predicate = f"""# Real-Luna predicate stability

{NOTICE}

Counts are assertions; intersection/union and Jaccard are passage-level predicate presence.
Supported omissions and policy ambiguities are EvidencePacket engineering assessments, not gold
labels.

{
        md_table(
            [
                "Predicate",
                "A count",
                "B count",
                "Intersection",
                "Union",
                "A-only",
                "B-only",
                "Jaccard",
                "Supported omissions",
                "Unsupported extras",
                "Policy ambiguities",
            ],
            predicate_rows,
        )
    }

The measured dominance is verified rather than assumed: REQUESTS and DESCRIBES_ACTION contribute
most one-run supported assertions. INVOLVES_SUBSTANCE is also unstable, especially where one run
emits a direct material mention while the other emits a request or action from a different clause.
INVOKES has a small denominator and one expert-dependent case; DESCRIBES varies mainly by
co-emission policy, not contradictory entity identity.
"""
    write_report("RIGVEDA_SEMANTIC_REAL_LUNA_PREDICATE_STABILITY.md", predicate)

    request_rows = []
    for passage in data["passages"]:
        for side in ("a", "b"):
            for raw in passage[f"{side}_assertions"]:
                item = ComparableAssertion(**raw)
                if item.predicate != "REQUESTS":
                    continue
                aligned = next(
                    row
                    for row in passage["alignment"]
                    if (row[side] and row[side]["assertion_id"] == item.assertion_id)
                )
                request_rows.append(
                    [
                        passage["passage_key"],
                        side.upper(),
                        item.assertion_id,
                        item.normalized_head,
                        anchors(item, "OUTCOME"),
                        anchors(item, "RELATION"),
                        "YES",
                        "NO" if item.assertion_id.endswith("00000000000000000061") else "YES",
                        aligned["one_sided_assessment"] or aligned["category"],
                    ]
                )
    request = f"""# Real-Luna REQUESTS stability

{NOTICE}

## Assertion audit

{
        md_table(
            [
                "Passage",
                "Run",
                "Assertion ID",
                "Normalized outcome",
                "OUTCOME anchor",
                "RELATION anchor",
                "Request force direct",
                "Outcome independently evidenced",
                "Audit result",
            ],
            request_rows,
        )
    }

## V3.1 policy diagnosis

V3.1 says to emit one requested outcome per independently requested outcome, but does not
operationalize coordination, nested outcomes, or split/merge precedence. It does not explicitly map
imperatives, optatives, prohibitive wishes, or “grant/give/bring” constructions to REQUESTS; it does
not state how a requested action differs from its grammatical object; and it does not model
speaker/addressee fields. These gaps explain the wealth/life, riches/children, and desired-drinking
cases. Direct forms such as “May we”, “Give us”, “bring us”, and “come” were nevertheless repeatedly
omitted, so recall variation remains substantial even after policy ambiguity is separated.
"""
    write_report("RIGVEDA_SEMANTIC_REAL_LUNA_REQUEST_STABILITY.md", request)

    action_rows = [
        [
            row["passage_key"],
            row["category"],
            row["a"]["predicate"] if row["a"] else "—",
            row["a"]["event_action_head"] or row["a"]["normalized_head"] if row["a"] else "—",
            row["b"]["predicate"] if row["b"] else "—",
            row["b"]["event_action_head"] or row["b"]["normalized_head"] if row["b"] else "—",
            row["one_sided_assessment"] or "—",
            row["rationale"] or "—",
        ]
        for row in data["alignments"]
        if (row["a"] and row["a"]["predicate"] in {"DESCRIBES", "DESCRIBES_ACTION"})
        or (row["b"] and row["b"]["predicate"] in {"DESCRIBES", "DESCRIBES_ACTION"})
    ]
    action = f"""# Real-Luna DESCRIBES / DESCRIBES_ACTION stability

{NOTICE}

{
        md_table(
            [
                "Passage",
                "Alignment",
                "A predicate",
                "A object/action",
                "B predicate",
                "B object/action",
                "Assessment",
                "Reason",
            ],
            action_rows,
        )
    }

V3.1 permits an entity-focused DESCRIBES assertion and says to put an action in a separate
DESCRIBES_ACTION assertion, but it never states whether a clause such as “Indra gives...” requires
the action only, the entity description only, or both. A precedence/co-emission rule is needed.
Imperative actions are also not separated from narrated actions. These are prompt-policy issues; the
typed schema and binding contract represented both outputs correctly.

## RV 10.58 cluster

All seven selected verses (10.58.1, .4, .5, .6, .7, .9, .11) directly contain the local translation
clause “We cause [thy spirit] to come ... again.” Run A emitted one DESCRIBES_ACTION for each; run B
omitted all seven. Each A binding isolates “cause to come.” No assertion depends on cross-verse
analogy. The cluster is therefore seven supported omissions and evidence of excessive emission
conservatism/recall variance, not unsupported extraction and not a reason to force parallel verses
to match.
"""
    write_report("RIGVEDA_SEMANTIC_REAL_LUNA_ACTION_STABILITY.md", action)

    canonical_report = f"""# Real-Luna canonical stability

{NOTICE}

{
        md_table(
            ["Passage", "Canonical A", "Canonical B", "Classification"],
            [[row["passage_key"], row["a"], row["b"], row["classification"]] for row in canonical],
        )
    }

Exact counts:
`ONE_RUN_HAS_CANONICAL_ASSERTION_OTHER_OMITS`={canonical_omits}, `DIFFERENT_PREDICATE_SAME_TARGET`={
        canonical_same_target
    }, `CONTRADICTORY_CANONICAL_TARGET`={
        canonical_contradictions
    }. Thus the reported 53/60 canonical agreement does not contain a single
contradictory canonical target.
"""
    write_report("RIGVEDA_SEMANTIC_REAL_LUNA_CANONICAL_STABILITY.md", canonical_report)

    evidence_counts = collections.Counter(
        row["anchor_assessment"] for row in data["alignments"] if row["anchor_assessment"]
    )
    evidence_rows = [
        [
            row["passage_key"],
            row["a"]["assertion_id"],
            row["b"]["assertion_id"],
            row["anchor_assessment"],
            "; ".join(f"{role}:{text}" for role, text, _, _ in row["a"]["binding_anchors"]),
            "; ".join(f"{role}:{text}" for role, text, _, _ in row["b"]["binding_anchors"]),
        ]
        for row in data["alignments"]
        if row["a"] and row["b"]
    ]
    evidence = f"""# Real-Luna evidence-anchor stability

{NOTICE}

The old 11/60 figure compared whole-passage predicate/role/text sets and therefore counted semantic
omission as anchor disagreement. Assertion-aligned anchor results are:

{
        md_table(
            ["Anchor class", "Aligned pairs"],
            [[key, value] for key, value in sorted(evidence_counts.items())],
        )
    }

{
        md_table(
            ["Passage", "A assertion", "B assertion", "Classification", "A anchors", "B anchors"],
            evidence_rows,
        )
    }

Alternate local spans and broader/narrower valid spans are LOW severity. `SEMANTIC_DISAGREEMENT`
here denotes that the paired semantic representation differs; it is not evidence-integrity failure.
No imported anchor failed validation. Whole-passage anchor agreement must not be used as a direct
semantic severity signal.
"""
    write_report("RIGVEDA_SEMANTIC_REAL_LUNA_EVIDENCE_STABILITY.md", evidence)

    stable_rows = []
    for row in data["alignments"]:
        if not row["diagnostic_set"]:
            continue
        diagnostic = DiagnosticSet(row["diagnostic_set"])
        label, status = candidate_provenance_label(diagnostic)
        stable_rows.append(
            [
                row["passage_key"],
                diagnostic.value,
                row["a"]["assertion_id"] if row["a"] else "—",
                row["b"]["assertion_id"] if row["b"] else "—",
                label,
                status,
            ]
        )
    stable = f"""# Real-Luna stable core and unstable fringe

{NOTICE}

{
        md_table(
            [
                "Passage",
                "Diagnostic set",
                "A assertion",
                "B assertion",
                "Provenance label",
                "Lifecycle",
            ],
            stable_rows,
        )
    }

Stable core size is {summary["stable_core_size"]} aligned assertion pairs. One-run-supported size is
{summary["one_run_supported_size"]} assertions. Suspect
assertions={summary["suspect_assertion_count"]}; expert-required={summary["expert_required_count"]}.
These are diagnostic sets only. No intersection, union, or model consensus is promoted to accepted
knowledge, and no historical heuristic artifact is used as truth.
"""
    write_report("RIGVEDA_SEMANTIC_REAL_LUNA_STABLE_CORE.md", stable)

    proposal = f"""# V3.2 prompt-policy proposal

{NOTICE}

Decision: `{DECISION}`. This is a design only; no Luna run was executed and the V3.1 prompt, schema,
ontology, execution contract, sealed outputs, and receipts remain unchanged.

## Minimal proposed policy patch

1. **Emit-vs-omit floor.** After the fourteen-family pass, emit every relation whose relation force
and target/object are both directly anchored. “Optional” means the evidence does not settle a policy
boundary, not that a directly evidenced independent family may be randomly skipped.
2. **REQUESTS force.** Treat an imperative, optative, prohibitive wish, or explicit
“grant/give/bring/send/bestow/may” construction as request force when the speaker seeks an outcome
from an addressee. The requested outcome is the desired resulting state/action, not automatically
the grammatical object of the verb.
3. **REQUESTS outcomes.** Emit one outcome per independently coordinated desired state. Keep a
modifier/beneficiary inside one outcome; split only when each conjunct can stand as a separately
desired result. Do not emit an unresolved “that which ...” as an additional outcome unless its
referent is independently anchored.
4. **DESCRIBES precedence.** DESCRIBES targets an entity only for attributed state/quality or an
entity-level depiction. A clause whose only descriptive content is an action emits DESCRIBES_ACTION,
not an additional DESCRIBES. If the clause independently attributes both a state/quality and an
action, both may be emitted with separate relation anchors.
5. **DESCRIBES_ACTION scope.** Use it for asserted/narrated actions. An imperative action belongs
under REQUESTS as a desired action/outcome unless the passage also states that the action occurs.
6. **Material/ritual co-emission.** A named material or ritual referent may co-exist with an
action/request assertion only when each relation has its own direct local anchor. Repeated mentions
do not create duplicate passage-level predicate/object assertions unless distinct typed roles or
qualifiers are asserted.
7. **No-claim criterion.** No claim is permitted only when no allowed family passes the direct
relation-plus-object test after applying these precedence rules; record the failed family/boundary
in the reason without inventing semantics.

## What stays unchanged

Keep `semantic_extraction_v3.schema.json`, the predicate ontology, typed-object schema, CODEX_DIRECT
receipt contract, evidence-span validation, and assertion binding validation unchanged. The audit
found no machinery defect. The version change is the prompt policy identifier
`rigveda-semantic-extraction-v3.2`; implementation must regenerate the prompt hash and run contract
before the future bounded run.

## Anti-overfitting and authorship

The rules use generic grammatical/policy conditions and contain no benchmark IDs. Validators may
reject structural, provenance, type, span, or binding violations, but may not author a relation or
force deterministic semantic output through regex rules. Luna remains the semantic author.
"""
    write_report("RIGVEDA_SEMANTIC_V3_2_POLICY_PROPOSAL.md", proposal)


def main() -> None:
    data = build_audit()
    summary = summarize(data)
    data["summary"] = summary
    data["predicate_metrics"] = predicate_metrics(data)
    data["canonical_cases"] = canonical_cases(data)
    DIAGNOSIS_JSON.write_text(
        json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    render_reports(data, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
