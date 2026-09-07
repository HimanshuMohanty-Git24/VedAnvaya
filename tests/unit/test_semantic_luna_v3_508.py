"""Regression checks for the seal-gated V3 508 candidate pilot."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
import yaml

from vedagraph.semantic.v3 import PREDICATE_CHECKS

ROOT = Path("data/semantic/vedagraph-rigveda-semantic-luna-v3-508")
REPORTS = Path("docs/reports")


_builder_spec = importlib.util.spec_from_file_location(
    "build_semantic_luna_v3_508_batches",
    Path("scripts/build_semantic_luna_v3_508_batches.py"),
)
assert _builder_spec is not None and _builder_spec.loader is not None
_builder = importlib.util.module_from_spec(_builder_spec)
_builder_spec.loader.exec_module(_builder)
_selected = _builder._selected


def stats() -> dict[str, object]:
    return json.loads((ROOT / "v3_508_statistics.json").read_text(encoding="utf-8"))


def test_existing_508_config_is_integral_and_not_full_corpus() -> None:
    document = yaml.safe_load(
        Path("data/builds/rigveda_semantic_pilot_v1.yaml").read_text(encoding="utf-8")
    )
    keys = [str(row["passage_key"]) for row in document["mantras"]]
    assert document["pilot_mantra_count"] == 508
    assert len(keys) == len(set(keys)) == 508
    assert len(keys) < 10_552


def test_508_builder_refuses_full_corpus_scope() -> None:
    with pytest.raises(RuntimeError, match="exactly 508"):
        _selected({"pilot_mantra_count": 10_552, "mantras": []})


def test_508_batches_and_seal_are_complete() -> None:
    manifest = json.loads((ROOT / "batch_manifest.json").read_text(encoding="utf-8"))
    seal = json.loads((ROOT / "v3_508_output_seal.json").read_text(encoding="utf-8"))
    assert manifest["mantra_count"] == seal["selected_count"] == 508
    assert manifest["batch_count"] == 22
    assert sum(int(row["batch_size"]) for row in manifest["batches"]) == 508
    assert len(seal["packet_hashes"]) == 508
    assert seal["comparison_sources_opened"] is False


def test_frozen_contract_hashes_and_no_predicate_unlocking() -> None:
    freeze = json.loads((ROOT / "input_freeze.json").read_text(encoding="utf-8"))
    seal = json.loads((ROOT / "v3_508_output_seal.json").read_text(encoding="utf-8"))
    assert freeze["verification_status"] == "PASS"
    assert freeze["overlap_count"] == 120
    assert freeze["frozen_prompt_sha256"] == seal["prompt_sha256"]
    assert freeze["frozen_schema_sha256"] == seal["schema_sha256"]
    assert seal["unlocked_predicates"] == []
    assert seal["human_gold_status"] == "UNANNOTATED"


def test_extraction_coverage_and_all_fourteen_checklists() -> None:
    rows = [
        json.loads(line)
        for line in (ROOT / "predicate_check_trace.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(rows) == 508
    assert all(row["checklist_completed"] for row in rows)
    assert all(set(row["families"]) == set(PREDICATE_CHECKS) for row in rows)


def test_aggregate_contracts_and_candidate_only_state() -> None:
    data = stats()
    summary = data["summary"]
    assert summary["mantras"] == 508
    assert summary["assertions"] == 917
    assert data["explicitness"] == {"EXPLICIT": 917}
    assert data["qa"]["validator_failures"] == 0
    assert data["qa"]["evidence_failures"] == 0
    assert data["qa"]["ritual_offering_substance"]["cross_kind_leakage"] == 0
    assert data["qa"]["natural_phenomenon"]["canonical_entity_reuse_violations"] == 0
    assert all(
        data["predicate"][name]["assertion_count"] == 0
        for name in ("HAS_THEME", "ASSOCIATED_WITH", "CONTRASTS_WITH")
    )


def test_embedded_120_new_388_and_parallel_diagnostics() -> None:
    data = stats()
    overlap = data["embedded_120"]
    assert overlap["overlap_count"] == 120
    assert overlap["exact_assertion_set_agreement"] == 120
    assert overlap["typed_object_agreement"] == 120
    assert overlap["evidence_anchor_agreement"] == 120
    assert overlap["high_severity_difference_count"] == 0
    assert data["new_388"]["mantras"] == 388
    assert data["parallel"]["pair_count"] > 0


def test_requested_aggregation_and_review_artifacts_exist() -> None:
    data = stats()
    assert set(data["mandala"]) == {str(number) for number in range(1, 11)}
    assert data["devata"]
    assert set(data["predicate_mandala"]) == set(PREDICATE_CHECKS)
    assert data["cooccurrence"]
    assert len(data["review_queue"]) >= 30
    assert len(data["expert_cases"]) == 20
    assert all(item["in_508_pilot"] for item in data["expert_cases"])
    assert all(item["v3_result_stable"] for item in data["expert_cases"])
    for name in (
        "RIGVEDA_SEMANTIC_V3_508.md",
        "RIGVEDA_SEMANTIC_V3_508_DISTRIBUTION.md",
        "RIGVEDA_SEMANTIC_V3_508_EMBEDDED_120_STABILITY.md",
        "RIGVEDA_SEMANTIC_V3_508_NEW_388.md",
        "RIGVEDA_SEMANTIC_V3_508_PARALLEL_QA.md",
        "RIGVEDA_SEMANTIC_V3_508_ONTOLOGY_GAPS.md",
        "RIGVEDA_SEMANTIC_V3_508_REVIEW_QUEUE.md",
    ):
        report = (REPORTS / name).read_text(encoding="utf-8")
        assert "NO HUMAN GOLD EXISTS" in report
        assert "NOT CANONICAL TRUTH" in report


def test_exact_candidate_head_groups_do_not_fuzzy_group() -> None:
    data = stats()
    groups = data["duplicate_head_groups"]
    assert all(" / " in key for key in groups)
    assert all("safety" not in key or "protection" not in key for key in groups if "safety" in key)


def test_manifest_pins_no_promotion_and_required_inputs() -> None:
    manifest = json.loads(
        Path("docs/manifests/vedagraph-rigveda-semantic-luna-v3-508.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["manifest_id"] == "vedagraph-rigveda-semantic-luna-v3-508"
    assert manifest["selected_count"] == 508
    assert manifest["human_gold"] == "UNANNOTATED"
    assert manifest["unlocked_predicates"] == []
    assert manifest["canonical_promotion"] is False
    assert manifest["normalization_manifest"].endswith("normalization_manifest.json")
    assert manifest["normalization_manifest_sha256"]
