import json
import shutil
from pathlib import Path

import pytest

from vedagraph.semantic.object_ontology import SemanticObjectKind, StructuredComparisonCategory
from vedagraph.semantic.replication import (
    _group,
    _request_metrics,
    _severity,
    canonical_entity_contradiction,
    compare_replications,
    load_assertions,
    readiness_recommendation,
    validate_replication_seal,
)

BASE = Path("data/semantic/vedagraph-rigveda-semantic-luna-v3-120")
REPLICATION = Path("data/semantic/vedagraph-rigveda-semantic-luna-v3-replication-120")


def metrics() -> dict[str, object]:
    return compare_replications(BASE, REPLICATION)


def test_input_freeze_and_prompt_schema_equality() -> None:
    freeze = json.loads((REPLICATION / "input_freeze.json").read_text(encoding="utf-8"))
    seal = json.loads((REPLICATION / "v3_replication_output_seal.json").read_text(encoding="utf-8"))
    assert freeze["freeze_valid"] is True
    assert freeze["prompt_sha256"] == seal["prompt_sha256"]
    assert freeze["schema_sha256"] == seal["schema_sha256"]
    assert len(freeze["evidence_packet_hashes"]) == 120


def test_blind_replication_and_seal_before_comparison(tmp_path: Path) -> None:
    assert (
        json.loads((REPLICATION / "input_freeze.json").read_text(encoding="utf-8"))[
            "comparison_sources_opened"
        ]
        is False
    )
    assert not (REPLICATION / "comparison_sources_opened.marker").exists()
    copied = tmp_path / "replication"
    shutil.copytree(REPLICATION, copied)
    seal_path = copied / "v3_replication_output_seal.json"
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    seal["comparison_sources_opened"] = True
    seal_path.write_text(json.dumps(seal), encoding="utf-8")
    with pytest.raises(ValueError, match="contaminated"):
        validate_replication_seal(seal_path, copied / "input_freeze.json")


def test_mantra_set_and_predicate_presence_stability() -> None:
    data = metrics()
    assert data["mantra_count"] == 120
    assert data["no_claim_agreement"] == 28
    predicate = data["predicate"]
    assert all(value["mantras_presence_differs"] == 0 for value in predicate.values())


def test_canonical_entity_and_typed_object_stability() -> None:
    data = metrics()
    assert data["canonical_entity_contradictions"] == []
    kinds = data["object_kind"]
    assert kinds[SemanticObjectKind.CANONICAL_ENTITY_REF.value]["exact_matches"] == 57
    assert all(value["granularity_differences"] == 0 for value in kinds.values())
    assert canonical_entity_contradiction(
        {"object_kind": "CANONICAL_ENTITY_REF", "canonical_entity_id": "A"},
        {"object_kind": "CANONICAL_ENTITY_REF", "canonical_entity_id": "B"},
    )


def test_request_order_event_and_evidence_stability() -> None:
    data = metrics()
    request = data["request"]
    assert request["same_number_of_outcomes_mantras"] == 120
    assert request["same_normalized_heads_mantras"] == 120
    assert request["split_merge_disagreements"] == 0
    event = data["event"]
    assert event["paired_events"] == 20
    assert event["action_head_mismatches"] == 0
    assert data["evidence"]["same_evidence_references"] == 211


def test_request_set_comparison_is_order_independent() -> None:
    left = _group(load_assertions(BASE))
    right = {
        mantra_id: list(reversed(items))
        for mantra_id, items in _group(load_assertions(REPLICATION)).items()
    }
    request = _request_metrics(left, right, sorted(left))
    assert request["same_normalized_heads_mantras"] == len(left)
    assert request["split_merge_disagreements"] == 0


def test_ontology_gap_explicitness_and_severity_stability() -> None:
    data = metrics()
    assert data["gap_counts"]["a"] == data["gap_counts"]["b"]
    assert data["gap_count_disagreements"] == 0
    assert data["explicitness_switches"] == 0
    assert data["severity_counts"] == {"LOW": 211}
    assert readiness_recommendation(data) == "V3_STABLE_ENOUGH_FOR_508_CANDIDATE_PILOT"


def test_severity_classification_marks_structural_changes_high() -> None:
    row = {
        "category": "OBJECT_TYPE_DIFFERENCE",
        "left_object": {"object_kind": "EVENT"},
        "right_object": {"object_kind": "REQUESTED_OUTCOME"},
    }
    assert _severity(row) == "HIGH"


def test_no_predicate_unlocking_and_comparison_categories_are_diagnostic() -> None:
    seal = json.loads((REPLICATION / "v3_replication_output_seal.json").read_text(encoding="utf-8"))
    assert seal["unlocked_predicates"] == []
    assert StructuredComparisonCategory.EXACT_CANONICAL_ENTITY.value in {
        row["category"] for row in metrics()["rows"]
    }
