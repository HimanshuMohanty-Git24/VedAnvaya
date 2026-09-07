"""Independent V3 replication sealing and structured stability diagnostics.

This module compares two already-sealed V3 outputs.  It never assigns truth labels,
uses fuzzy similarity, edits either run, unlocks predicates, or reads human gold.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from vedagraph.models.normalization import (
    SemanticExtractionV3,
    StructuredSemanticAssertion,
)
from vedagraph.semantic.normalization import (
    compare_semantic_objects,
    evidence_signature,
    object_signature,
)
from vedagraph.semantic.object_ontology import (
    SemanticObjectKind,
    StructuredComparisonCategory,
)
from vedagraph.semantic.ontology import Explicitness, SemanticPredicate

REPLICATION_RUN_ID = "vedagraph-rigveda-semantic-luna-v3-replication-120"
COMPARISON_CATEGORIES = tuple(item.value for item in StructuredComparisonCategory)
PREDICATES = tuple(
    item.value
    for item in SemanticPredicate
    if item.value not in {"SYMBOLIZES", "REPRESENTS", "IS_GOD_OF", "MEANS", "CAUSES"}
)
HIGH_CATEGORIES = {
    StructuredComparisonCategory.PREDICATE_DIFFERENCE,
    StructuredComparisonCategory.OBJECT_TYPE_DIFFERENCE,
    StructuredComparisonCategory.CONFLICTING_OBJECT,
}
MEDIUM_CATEGORIES = {
    StructuredComparisonCategory.PARTIAL_OBJECT_OVERLAP,
    StructuredComparisonCategory.GRANULARITY_DIFFERENCE,
    StructuredComparisonCategory.LEFT_ONLY,
    StructuredComparisonCategory.RIGHT_ONLY,
    StructuredComparisonCategory.UNRESOLVED,
    StructuredComparisonCategory.EXPERT_REQUIRED,
}


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha256(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def jsonl_rows(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def load_payloads(root: Path) -> dict[str, SemanticExtractionV3]:
    path = root / "v3_extractions.jsonl"
    payloads = [SemanticExtractionV3.model_validate(row) for row in jsonl_rows(path)]
    index = {
        row["citation"]: row["passage_key"]
        for row in jsonl_rows(root / "evidence_packet_index.jsonl")
    }
    return {index.get(item.mantra_id, item.mantra_id): item for item in payloads}


def load_assertions(root: Path) -> list[StructuredSemanticAssertion]:
    return [
        StructuredSemanticAssertion.model_validate(row)
        for row in jsonl_rows(root / "semantic_v3_assertions.jsonl")
    ]


def _object_key(assertion: StructuredSemanticAssertion) -> str:
    return canonical_sha256(
        {
            "predicate": assertion.predicate.value,
            "object": object_signature(assertion.object).model_dump(mode="json"),
            "explicitness": assertion.explicitness.value,
        }
    )


def _semantic_key_without_explicitness(assertion: StructuredSemanticAssertion) -> str:
    return canonical_sha256(
        {
            "predicate": assertion.predicate.value,
            "object": object_signature(assertion.object).model_dump(mode="json"),
        }
    )


def _evidence_key(assertion: StructuredSemanticAssertion) -> str:
    return canonical_sha256(evidence_signature(assertion.evidence).model_dump(mode="json"))


def _sort_assertions(items: list[StructuredSemanticAssertion]) -> list[StructuredSemanticAssertion]:
    return sorted(items, key=lambda item: (_object_key(item), item.assertion_id))


def _best_pair(
    left: StructuredSemanticAssertion,
    candidates: list[tuple[int, StructuredSemanticAssertion]],
) -> tuple[int, StructuredComparisonCategory] | None:
    choices: list[tuple[int, int, StructuredComparisonCategory]] = []
    for index, right in candidates:
        category = compare_semantic_objects(left.object, right.object)
        rank = {
            StructuredComparisonCategory.EXACT_CANONICAL_ENTITY: 100,
            StructuredComparisonCategory.EXACT_NORMALIZED_OBJECT: 95,
            StructuredComparisonCategory.COMPATIBLE_OBJECT: 80,
            StructuredComparisonCategory.PARTIAL_OBJECT_OVERLAP: 70,
            StructuredComparisonCategory.GRANULARITY_DIFFERENCE: 65,
            StructuredComparisonCategory.OBJECT_TYPE_DIFFERENCE: 45,
            StructuredComparisonCategory.CONFLICTING_OBJECT: 35,
            StructuredComparisonCategory.EXPERT_REQUIRED: 20,
            StructuredComparisonCategory.UNRESOLVED: 10,
        }[category]
        choices.append((rank, -index, category))
    if not choices:
        return None
    _, negative_index, category = max(choices)
    return -negative_index, category


def _aligned_rows(
    mantra_id: str,
    left: list[StructuredSemanticAssertion],
    right: list[StructuredSemanticAssertion],
) -> list[dict[str, Any]]:
    left_sorted = _sort_assertions(left)
    right_sorted = _sort_assertions(right)
    remaining = {index for index in range(len(right_sorted))}
    rows: list[dict[str, Any]] = []
    for left_item in left_sorted:
        same_predicate = [
            (index, right_sorted[index])
            for index in sorted(remaining)
            if right_sorted[index].predicate is left_item.predicate
        ]
        choice = _best_pair(left_item, same_predicate)
        underlying: StructuredComparisonCategory | None = None
        predicate_difference = False
        if choice is None:
            cross = [
                (index, right_sorted[index])
                for index in sorted(remaining)
                if right_sorted[index].predicate is not left_item.predicate
            ]
            cross_choice = _best_pair(left_item, cross)
            if cross_choice is not None and cross_choice[1] in {
                StructuredComparisonCategory.EXACT_CANONICAL_ENTITY,
                StructuredComparisonCategory.EXACT_NORMALIZED_OBJECT,
                StructuredComparisonCategory.COMPATIBLE_OBJECT,
                StructuredComparisonCategory.PARTIAL_OBJECT_OVERLAP,
                StructuredComparisonCategory.GRANULARITY_DIFFERENCE,
            }:
                choice = cross_choice
                underlying = cross_choice[1]
                predicate_difference = True
        if choice is None:
            rows.append(
                {
                    "mantra_id": mantra_id,
                    "category": StructuredComparisonCategory.LEFT_ONLY.value,
                    "left": left_item,
                    "right": None,
                    "underlying_category": None,
                }
            )
            continue
        index, category = choice
        remaining.remove(index)
        rows.append(
            {
                "mantra_id": mantra_id,
                "category": (
                    StructuredComparisonCategory.PREDICATE_DIFFERENCE.value
                    if predicate_difference
                    else category.value
                ),
                "left": left_item,
                "right": right_sorted[index],
                "underlying_category": underlying.value if underlying else None,
            }
        )
    for index in sorted(remaining):
        rows.append(
            {
                "mantra_id": mantra_id,
                "category": StructuredComparisonCategory.RIGHT_ONLY.value,
                "left": None,
                "right": right_sorted[index],
                "underlying_category": None,
            }
        )
    return rows


def _serialise_row(row: dict[str, Any]) -> dict[str, Any]:
    left = row["left"]
    right = row["right"]
    return {
        "mantra_id": row["mantra_id"],
        "category": row["category"],
        "underlying_category": row["underlying_category"],
        "left_assertion_id": left.assertion_id if left else None,
        "right_assertion_id": right.assertion_id if right else None,
        "left_predicate": left.predicate.value if left else None,
        "right_predicate": right.predicate.value if right else None,
        "left_object": object_signature(left.object).model_dump(mode="json") if left else None,
        "right_object": object_signature(right.object).model_dump(mode="json") if right else None,
        "left_display_label": left.object.display_label if left else None,
        "right_display_label": right.object.display_label if right else None,
        "left_evidence": evidence_signature(left.evidence).model_dump(mode="json")
        if left
        else None,
        "right_evidence": evidence_signature(right.evidence).model_dump(mode="json")
        if right
        else None,
        "left_explicitness": left.explicitness.value if left else None,
        "right_explicitness": right.explicitness.value if right else None,
    }


def _group(
    items: list[StructuredSemanticAssertion],
) -> dict[str, list[StructuredSemanticAssertion]]:
    grouped: dict[str, list[StructuredSemanticAssertion]] = defaultdict(list)
    for item in items:
        grouped[item.subject_id].append(item)
    return grouped


def _counter(values: list[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def _request_metrics(
    left: dict[str, list[StructuredSemanticAssertion]],
    right: dict[str, list[StructuredSemanticAssertion]],
    ids: list[str],
) -> dict[str, Any]:
    same_number = same_heads = 0
    split_merge = qualifier = beneficiary = target = 0
    cases: list[dict[str, Any]] = []
    for mantra_id in ids:
        a = [
            item for item in left.get(mantra_id, []) if item.predicate is SemanticPredicate.REQUESTS
        ]
        b = [
            item
            for item in right.get(mantra_id, [])
            if item.predicate is SemanticPredicate.REQUESTS
        ]
        aheads = Counter(item.object.normalized_head or "" for item in a)
        bheads = Counter(item.object.normalized_head or "" for item in b)
        if len(a) == len(b):
            same_number += 1
        if aheads == bheads:
            same_heads += 1
        if len(a) != len(b) or aheads != bheads:
            split_merge += 1
            cases.append(
                {
                    "mantra_id": mantra_id,
                    "a_heads": sorted(aheads.elements()),
                    "b_heads": sorted(bheads.elements()),
                }
            )
        b_by_head: dict[str, list[StructuredSemanticAssertion]] = defaultdict(list)
        for item in b:
            b_by_head[item.object.normalized_head or ""].append(item)
        for item in a:
            head = item.object.normalized_head or ""
            if not b_by_head[head]:
                continue
            other = b_by_head[head].pop()
            if sorted(item.object.qualifiers) != sorted(other.object.qualifiers):
                qualifier += 1
            if item.object.beneficiary_entity_id != other.object.beneficiary_entity_id:
                beneficiary += 1
            if item.object.target_entity_id != other.object.target_entity_id:
                target += 1
    return {
        "same_number_of_outcomes_mantras": same_number,
        "same_normalized_heads_mantras": same_heads,
        "split_merge_disagreements": split_merge,
        "qualifier_disagreements": qualifier,
        "beneficiary_disagreements": beneficiary,
        "target_disagreements": target,
        "cases": cases,
    }


def _event_metrics(
    left: dict[str, list[StructuredSemanticAssertion]],
    right: dict[str, list[StructuredSemanticAssertion]],
    ids: list[str],
) -> dict[str, Any]:
    totals: Counter[str] = Counter()
    examples: list[dict[str, Any]] = []
    for mantra_id in ids:
        a = _sort_assertions(
            [
                item
                for item in left.get(mantra_id, [])
                if item.predicate is SemanticPredicate.DESCRIBES_ACTION
            ]
        )
        b = _sort_assertions(
            [
                item
                for item in right.get(mantra_id, [])
                if item.predicate is SemanticPredicate.DESCRIBES_ACTION
            ]
        )
        for left_item, right_item in zip(a, b, strict=False):
            if left_item.object.event is None or right_item.object.event is None:
                totals["invalid_event_shape"] += 1
                continue
            le = left_item.object.event
            re = right_item.object.event
            totals["paired_events"] += 1
            if le.action_head == re.action_head:
                totals["same_action_head"] += 1
            else:
                totals["action_head_mismatches"] += 1
                examples.append({"mantra_id": mantra_id, "a": le.action_head, "b": re.action_head})
            if le.actor_entity_id == re.actor_entity_id:
                totals["same_actor"] += 1
            else:
                totals["actor_differences"] += 1
            if le.patient_entity_id == re.patient_entity_id:
                totals["same_patient"] += 1
            else:
                totals["patient_differences"] += 1
            if le.other_participants == re.other_participants:
                totals["same_participants"] += 1
            else:
                totals["participant_differences"] += 1
            if sorted(le.qualifiers) == sorted(re.qualifiers):
                totals["same_qualifiers"] += 1
            else:
                totals["qualifier_differences"] += 1
    expected = {
        "paired_events": 0,
        "same_action_head": 0,
        "action_head_mismatches": 0,
        "same_actor": 0,
        "actor_differences": 0,
        "same_patient": 0,
        "patient_differences": 0,
        "same_participants": 0,
        "participant_differences": 0,
        "same_qualifiers": 0,
        "qualifier_differences": 0,
        "invalid_event_shape": 0,
    }
    expected.update(totals)
    return {**dict(sorted(expected.items())), "action_head_mismatch_examples": examples}


def _object_kind_metrics(
    rows: list[dict[str, Any]],
) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {
        kind.value: {
            "a_count": 0,
            "b_count": 0,
            "exact_matches": 0,
            "granularity_differences": 0,
            "conflicts": 0,
        }
        for kind in SemanticObjectKind
    }
    for row in rows:
        left = row["left_object"]
        right = row["right_object"]
        if left:
            result[left["object_kind"]]["a_count"] += 1
        if right:
            result[right["object_kind"]]["b_count"] += 1
        if left and right and left["object_kind"] == right["object_kind"]:
            kind_result = result[left["object_kind"]]
            if row["category"] in {
                StructuredComparisonCategory.EXACT_CANONICAL_ENTITY.value,
                StructuredComparisonCategory.EXACT_NORMALIZED_OBJECT.value,
            }:
                kind_result["exact_matches"] += 1
            if row["category"] == StructuredComparisonCategory.GRANULARITY_DIFFERENCE.value:
                kind_result["granularity_differences"] += 1
            if row["category"] in {
                StructuredComparisonCategory.CONFLICTING_OBJECT.value,
                StructuredComparisonCategory.PREDICATE_DIFFERENCE.value,
            }:
                kind_result["conflicts"] += 1
    return result


def _severity(row: dict[str, Any]) -> str:
    category = StructuredComparisonCategory(row["category"])
    left = row["left_object"]
    right = row["right_object"]
    if category is StructuredComparisonCategory.CONFLICTING_OBJECT:
        if (
            left
            and right
            and left.get("object_kind") == SemanticObjectKind.CANONICAL_ENTITY_REF.value
        ):
            return "HIGH"
        if (
            left
            and right
            and SemanticObjectKind.ONTOLOGY_GAP_REF.value
            in {left.get("object_kind"), right.get("object_kind")}
        ):
            return "HIGH"
        return "MEDIUM"
    if category in HIGH_CATEGORIES:
        return "HIGH"
    if category in MEDIUM_CATEGORIES:
        return "MEDIUM"
    return "LOW"


def canonical_entity_contradiction(
    left: dict[str, Any] | None, right: dict[str, Any] | None
) -> bool:
    """Return true only for two canonical refs that name different entity IDs."""
    return bool(
        left
        and right
        and left.get("object_kind") == SemanticObjectKind.CANONICAL_ENTITY_REF.value
        and right.get("object_kind") == SemanticObjectKind.CANONICAL_ENTITY_REF.value
        and left.get("canonical_entity_id") != right.get("canonical_entity_id")
    )


def compare_replications(left_root: Path, right_root: Path) -> dict[str, Any]:
    """Compare V3-A (left) and V3-B (right) without fuzzy semantic equivalence."""
    left_payloads = load_payloads(left_root)
    right_payloads = load_payloads(right_root)
    left_assertions = load_assertions(left_root)
    right_assertions = load_assertions(right_root)
    left_grouped = _group(left_assertions)
    right_grouped = _group(right_assertions)
    ids = sorted(set(left_payloads) | set(right_payloads))
    exact = partial = different = no_claim_agreement = no_claim_disagreement = 0
    rows: list[dict[str, Any]] = []
    mantra_summaries: list[dict[str, Any]] = []
    for mantra_id in ids:
        a = left_grouped.get(mantra_id, [])
        b = right_grouped.get(mantra_id, [])
        a_no_claim = not a
        b_no_claim = not b
        if a_no_claim and b_no_claim:
            no_claim_agreement += 1
            mantra_summaries.append({"mantra_id": mantra_id, "status": "NO_CLAIM_AGREEMENT"})
            continue
        if a_no_claim != b_no_claim:
            no_claim_disagreement += 1
        aligned = _aligned_rows(mantra_id, a, b)
        serialised = [_serialise_row(item) for item in aligned]
        rows.extend(serialised)
        semantic_a = Counter(_object_key(item) for item in a)
        semantic_b = Counter(_object_key(item) for item in b)
        if semantic_a == semantic_b:
            exact += 1
            status = "EXACT_ASSERTION_SET"
        elif a and b:
            partial += 1
            status = "PARTIAL_ASSERTION_SET"
        else:
            different += 1
            status = "DIFFERENT_ASSERTION_SET"
        mantra_summaries.append({"mantra_id": mantra_id, "status": status, "rows": serialised})
    predicate: dict[str, dict[str, int]] = {}
    for name in PREDICATES:
        pred = SemanticPredicate(name)
        a = [item for item in left_assertions if item.predicate is pred]
        b = [item for item in right_assertions if item.predicate is pred]
        a_mantras = {item.subject_id for item in a}
        b_mantras = {item.subject_id for item in b}
        predicate[name] = {
            "a_count": len(a),
            "b_count": len(b),
            "matched_assertions": sum(
                row["left_predicate"] == name and row["right_predicate"] == name for row in rows
            ),
            "a_only": sum(
                row["left_predicate"] == name and row["right_predicate"] is None for row in rows
            ),
            "b_only": sum(
                row["right_predicate"] == name and row["left_predicate"] is None for row in rows
            ),
            "mantras_presence_agrees": len(a_mantras & b_mantras)
            + len(set(ids) - (a_mantras | b_mantras)),
            "mantras_presence_differs": len(a_mantras ^ b_mantras),
        }
    gap_counts_a = Counter(
        gap.ontology_gap_code.value
        for payload in left_payloads.values()
        for gap in payload.ontology_gaps
        if gap.ontology_gap_code
    )
    gap_counts_b = Counter(
        gap.ontology_gap_code.value
        for payload in right_payloads.values()
        for gap in payload.ontology_gaps
        if gap.ontology_gap_code
    )
    gap_by_mantra_a = {
        mantra_id: {
            gap.ontology_gap_code.value for gap in payload.ontology_gaps if gap.ontology_gap_code
        }
        for mantra_id, payload in left_payloads.items()
    }
    gap_by_mantra_b = {
        mantra_id: {
            gap.ontology_gap_code.value for gap in payload.ontology_gaps if gap.ontology_gap_code
        }
        for mantra_id, payload in right_payloads.items()
    }
    gap_transitions = [
        {
            "mantra_id": mantra_id,
            "a_gap_codes": sorted(gap_by_mantra_a.get(mantra_id, set())),
            "b_gap_codes": sorted(gap_by_mantra_b.get(mantra_id, set())),
            "a_assertions": bool(left_grouped.get(mantra_id)),
            "b_assertions": bool(right_grouped.get(mantra_id)),
        }
        for mantra_id in ids
        if gap_by_mantra_a.get(mantra_id, set()) != gap_by_mantra_b.get(mantra_id, set())
    ]
    a_validation = jsonl_rows(left_root / "v3_validation.jsonl")
    b_validation = jsonl_rows(right_root / "v3_validation.jsonl")
    evidence_same = evidence_different = 0
    for row in rows:
        if row["left_evidence"] and row["right_evidence"]:
            if row["left_evidence"] == row["right_evidence"]:
                evidence_same += 1
            else:
                evidence_different += 1
    explicitness_switches = sum(
        (
            row["left_explicitness"] == Explicitness.EXPLICIT.value
            and row["right_explicitness"] == Explicitness.STRONG_INFERENCE.value
        )
        or (
            row["left_explicitness"] == Explicitness.STRONG_INFERENCE.value
            and row["right_explicitness"] == Explicitness.EXPLICIT.value
        )
        for row in rows
    )
    high_rows = [{**row, "severity": _severity(row)} for row in rows if _severity(row) == "HIGH"]
    severity_counts = Counter(_severity(row) for row in rows)
    high_rows.extend(
        {**transition, "category": "ONTOLOGY_GAP_VS_ASSERTION", "severity": "HIGH"}
        for transition in gap_transitions
    )
    if gap_transitions:
        severity_counts["HIGH"] += len(gap_transitions)
    return {
        "mantra_count": len(ids),
        "a_assertions": len(left_assertions),
        "b_assertions": len(right_assertions),
        "a_no_claims": sum(not payload.assertions for payload in left_payloads.values()),
        "b_no_claims": sum(not payload.assertions for payload in right_payloads.values()),
        "exact_assertion_set_agreement": exact,
        "partial_assertion_set_agreement": partial,
        "different_assertion_set": different,
        "no_claim_agreement": no_claim_agreement,
        "no_claim_disagreement": no_claim_disagreement,
        "predicate": predicate,
        "object_kind": _object_kind_metrics(rows),
        "rows": rows,
        "mantra_summaries": mantra_summaries,
        "gap_counts": {
            "a": dict(sorted(gap_counts_a.items())),
            "b": dict(sorted(gap_counts_b.items())),
        },
        "gap_count_disagreements": sum(
            gap_counts_a.get(code) != gap_counts_b.get(code)
            for code in set(gap_counts_a) | set(gap_counts_b)
        ),
        "ontology_gap_transitions": gap_transitions,
        "explicitness_switches": explicitness_switches,
        "evidence": {
            "same_evidence_references": evidence_same,
            "different_valid_evidence_references": evidence_different,
            "a_missing_evidence": sum("evidence" in row.get("errors", []) for row in a_validation),
            "b_missing_evidence": sum("evidence" in row.get("errors", []) for row in b_validation),
            "a_invalid_evidence_rows": sum(bool(row.get("errors")) for row in a_validation),
            "b_invalid_evidence_rows": sum(bool(row.get("errors")) for row in b_validation),
        },
        "request": _request_metrics(left_grouped, right_grouped, ids),
        "event": _event_metrics(left_grouped, right_grouped, ids),
        "severity_counts": dict(sorted(severity_counts.items())),
        "high_severity_rows": high_rows,
        "canonical_entity_contradictions": [
            row
            for row in rows
            if canonical_entity_contradiction(row["left_object"], row["right_object"])
        ],
    }


def validate_replication_seal(seal_path: Path, freeze_path: Path) -> dict[str, Any]:
    """Refuse comparison unless the replication output seal and its inputs validate."""
    seal: dict[str, Any] = json.loads(seal_path.read_text(encoding="utf-8"))
    freeze: dict[str, Any] = json.loads(freeze_path.read_text(encoding="utf-8"))
    if seal.get("comparison_sources_opened") is not False:
        raise ValueError("replication seal is contaminated")
    if seal.get("selected_count") != 120 or seal.get("model") != "gpt-5.6-luna":
        raise ValueError("replication seal has wrong benchmark or model")
    if (
        seal.get("reasoning") != "high"
        or seal.get("runtime") != "CODEX_DIRECT"
        or seal.get("api_invocation") is not False
    ):
        raise ValueError("replication seal has wrong execution configuration")
    if seal.get("human_gold_status") != "UNANNOTATED" or seal.get("unlocked_predicates") != []:
        raise ValueError("replication seal has unsafe gold or predicate state")
    if (
        freeze.get("freeze_valid") is not True
        or freeze.get("comparison_sources_opened") is not False
    ):
        raise ValueError("input freeze did not validate or was contaminated")
    for key in (
        "selected_id_sha256",
        "prompt_sha256",
        "schema_sha256",
        "complete_extraction_sha256",
    ):
        if not isinstance(seal.get(key), str) or len(seal[key]) != 64:
            raise ValueError(f"replication seal missing {key}")
    expected_outputs = seal.get("output_hashes", {})
    root = seal_path.parent
    for name, expected in expected_outputs.items():
        if not (root / name).exists() or file_sha256(root / name) != expected:
            raise ValueError(f"replication output changed after seal: {name}")
    return seal


def readiness_recommendation(data: dict[str, Any]) -> str:
    """Apply the documented qualitative 508 gate, never a single percentage."""
    high = len(data["high_severity_rows"])
    canonical = len(data["canonical_entity_contradictions"])
    predicate_diff = sum(
        1
        for row in data["rows"]
        if row["category"] == StructuredComparisonCategory.PREDICATE_DIFFERENCE.value
    )
    type_diff = sum(
        1
        for row in data["rows"]
        if row["category"] == StructuredComparisonCategory.OBJECT_TYPE_DIFFERENCE.value
    )
    evidence = data["evidence"]
    b = data["b_assertions"]
    presence = sum(item["mantras_presence_agrees"] for item in data["predicate"].values())
    total_presence = sum(
        item["mantras_presence_agrees"] + item["mantras_presence_differs"]
        for item in data["predicate"].values()
    )
    consistent = total_presence == 0 or presence / total_presence >= 0.95
    if (
        canonical == 0
        and type_diff <= 2
        and predicate_diff <= 2
        and high <= 5
        and consistent
        and not evidence["b_invalid_evidence_rows"]
    ):
        return "V3_STABLE_ENOUGH_FOR_508_CANDIDATE_PILOT"
    if high <= max(10, int(b * 0.05)) and canonical <= 2 and consistent:
        return "V3_NEEDS_ONE_MORE_REPLICATION"
    return "V3_UNSTABLE_DO_NOT_SCALE"
