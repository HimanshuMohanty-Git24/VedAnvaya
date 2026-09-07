from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from vedagraph.models.enums import EvidenceSpanType
from vedagraph.models.semantic import (
    EvidencePacket,
    GoldAnnotation,
    PacketMention,
    PacketTranslation,
    SemanticAssertionCandidate,
    SemanticAssertionObject,
    SemanticEvidence,
)
from vedagraph.models.silver import (
    SilverBenchmarkManifest,
    SilverComparison,
    SilverEvidenceReference,
    SilverSemanticAnnotation,
    SilverSemanticAssertion,
)
from vedagraph.semantic.ontology import (
    ONTOLOGY_VERSION,
    Explicitness,
    SemanticNodeType,
    SemanticPredicate,
    SemanticSubjectKind,
    SilverComparisonCategory,
)
from vedagraph.semantic.silver import (
    SILVER_REVIEWER_MODEL,
    calculate_agreement_metrics,
    compare_after_blind_seal,
    compare_annotations,
    create_blind_review_seal,
    load_blind_packets,
    persist_blind_batch,
    select_expert_audit_ids,
)

KEY = "VG:RV:SAK:M01:S001:V001"
AGNI = "VG:DEVATA:AGNIH"
TRANSLATION_ID = "translation-1"


def packet(key: str = KEY) -> EvidencePacket:
    text = "I call Agni; grant protection."
    return EvidencePacket(
        packet_version="test",
        passage_key=key,
        passage_id=UUID("141a362f-1690-5244-831d-e0304db2fdc8"),
        citation="RV 1.1.1",
        mandala=1,
        sukta=1,
        mantra=1,
        sanskrit="agnim huve",
        sanskrit_text_version_id="test",
        translation=PacketTranslation(
            translation_id=TRANSLATION_ID,
            translator="test",
            language="en",
            text=text,
            text_sha256="a" * 64,
        ),
        devata_keys=[AGNI],
        devata_labels=["agniḥ"],
        mentions=[
            PacketMention(
                entity_key=AGNI,
                entity_label="agniḥ",
                occurrence_count=1,
                token_keys=["token-1"],
            )
        ],
        sukta_mantra_count=1,
        input_sha256="b" * 64,
    )


def silver_assertion(
    predicate: SemanticPredicate = SemanticPredicate.INVOKES,
    label: str = "agniḥ",
    *,
    assertion_id: str = "silver-1",
) -> SilverSemanticAssertion:
    return SilverSemanticAssertion(
        assertion_id=assertion_id,
        subject=KEY,
        predicate=predicate,
        object_label=label,
        object_node_type=SemanticNodeType.COSMIC_ENTITY,
        object_entity_key=AGNI if label == "agniḥ" else None,
        explicitness=Explicitness.EXPLICIT,
        evidence=[SilverEvidenceReference(kind="TRANSLATION", reference_id=TRANSLATION_ID)],
        rationale_code="TEXT_EXPLICIT",
        confidence=0.9,
    )


def annotation(
    assertions: list[SilverSemanticAssertion] | None = None,
    *,
    key: str = KEY,
    no_claim: bool = False,
) -> SilverSemanticAnnotation:
    assertions = [] if no_claim else (assertions or [silver_assertion()])
    return SilverSemanticAnnotation(
        mantra_id=key,
        citation="RV 1.1.1",
        reviewer_model=SILVER_REVIEWER_MODEL,
        ontology_version=ONTOLOGY_VERSION,
        evidence_packet_hash="b" * 64,
        semantic_assertions=assertions,
        no_claim=no_claim,
        no_claim_code="NO_SUPPORTED_SEMANTIC_ASSERTION" if no_claim else None,
        reviewed_at=datetime(2026, 9, 5, tzinfo=UTC),
        review_run_id="silver-test",
        batch_id="batch_001",
    )


def candidate(
    predicate: SemanticPredicate = SemanticPredicate.INVOKES,
    *,
    entity: str = AGNI,
    key: str = KEY,
) -> SemanticAssertionCandidate:
    return SemanticAssertionCandidate(
        candidate_assertion_id=f"luna-{key}-{predicate.value}",
        subject_key=key,
        subject_kind=SemanticSubjectKind.MANTRA,
        predicate=predicate,
        object=SemanticAssertionObject(entity_key=entity),
        evidence=[
            SemanticEvidence(
                passage_key=key,
                span_type=EvidenceSpanType.TRANSLATION_LINE,
                translation_id=TRANSLATION_ID,
            )
        ],
        explicitness=Explicitness.EXPLICIT,
        confidence=0.9,
        model="gpt-5.6-luna",
        prompt_version="test",
        ontology_version=ONTOLOGY_VERSION,
        schema_name="test",
        input_sha256="b" * 64,
    )


def test_silver_and_human_gold_are_distinct_types() -> None:
    row = annotation()
    assert not isinstance(row, GoldAnnotation)
    with pytest.raises(ValidationError):
        GoldAnnotation.model_validate(row.model_dump(mode="json"))


def test_silver_annotation_serialization_and_no_claim_invariant() -> None:
    row = annotation()
    assert SilverSemanticAnnotation.model_validate_json(row.model_dump_json()) == row
    with pytest.raises(ValidationError):
        SilverSemanticAnnotation.model_validate(
            row.model_dump(mode="json")
            | {"no_claim": True, "no_claim_code": "NO_SUPPORTED_SEMANTIC_ASSERTION"}
        )


def test_blind_loader_accepts_only_evidence_named_files(tmp_path: Path) -> None:
    forbidden = tmp_path / "candidates.jsonl"
    forbidden.write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"only open evidence\.jsonl"):
        load_blind_packets([forbidden], frozenset({KEY}))


def test_blind_loader_rejects_luna_fields(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence.jsonl"
    raw = packet().model_dump(mode="json") | {"luna_output": []}
    evidence.write_text(json.dumps(raw) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="exposes model fields"):
        load_blind_packets([evidence], frozenset({KEY}))


def test_comparison_cannot_read_luna_before_valid_seal(tmp_path: Path) -> None:
    annotations = tmp_path / "annotations.jsonl"
    batch = tmp_path / "batch.jsonl"
    packets = {KEY: packet()}
    persist_blind_batch(
        annotations_path=annotations,
        batch_path=batch,
        annotations=[annotation()],
        packets=packets,
    )
    seal = tmp_path / "seal.json"
    create_blind_review_seal(
        annotations_path=annotations,
        seal_path=seal,
        packets=packets,
        selected_ids=frozenset({KEY}),
    )
    annotations.write_text(annotations.read_text() + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="changed after blind seal"):
        compare_after_blind_seal(
            annotations_path=annotations,
            seal_path=seal,
            luna_candidates_path=tmp_path / "does-not-exist.jsonl",
            comparison_path=tmp_path / "comparison.jsonl",
            packets=packets,
            selected_ids=frozenset({KEY}),
        )


def test_comparison_categories_and_missing_relation_detection() -> None:
    request = silver_assertion(SemanticPredicate.REQUESTS, "protection", assertion_id="silver-2")
    rows = compare_annotations(
        [annotation([silver_assertion(), request])], [candidate()], {KEY: packet()}
    )
    assert {item.category for item in rows} == {
        SilverComparisonCategory.MATCH,
        SilverComparisonCategory.LUNA_MISSED_RELATION,
    }


def test_no_claim_agreement_and_agreement_metrics() -> None:
    rows = compare_annotations([annotation(no_claim=True)], [], {KEY: packet()})
    metrics = calculate_agreement_metrics([annotation(no_claim=True)], [], rows)
    assert rows[0].category is SilverComparisonCategory.NO_CLAIM_AGREEMENT
    assert metrics.no_claim_agreement == 1.0
    assert metrics.silver_agreement_precision is None


def test_predicate_coverage_records_zero_and_nonzero_support() -> None:
    rows = compare_annotations([annotation()], [candidate()], {KEY: packet()})
    metrics = calculate_agreement_metrics([annotation()], [candidate()], rows)
    assert metrics.predicate_rows["INVOKES"] == {"sol": 1, "luna": 1, "match": 1}
    assert metrics.predicate_rows["HAS_THEME"] == {"sol": 0, "luna": 0, "match": 0}


def test_expert_audit_selection_is_bounded_and_deterministic() -> None:
    annotations: list[SilverSemanticAnnotation] = []
    comparisons: list[SilverComparison] = []
    for index in range(25):
        key = f"VG:RV:SAK:M{index % 10 + 1:02d}:S001:V{index + 1:03d}"
        annotations.append(annotation(no_claim=True, key=key))
        comparisons.append(
            SilverComparison(
                mantra_id=key,
                category=SilverComparisonCategory.NO_CLAIM_AGREEMENT,
                reasoning="control",
            )
        )
    first = select_expert_audit_ids(comparisons, annotations, target_size=20)
    assert len(first) == 20
    assert first == select_expert_audit_ids(comparisons, annotations, target_size=20)


def test_silver_manifest_forbids_predicate_unlocking() -> None:
    fields = {
        "run_id": "silver-test",
        "corpus_manifest_sha256": "a" * 64,
        "deterministic_knowledge_manifest_sha256": "b" * 64,
        "lexical_manifest_sha256": "c" * 64,
        "semantic_ontology_version": ONTOLOGY_VERSION,
        "luna_pilot_run_id": "luna-test",
        "luna_model_id": "gpt-5.6-luna",
        "sol_reviewer_model_id": SILVER_REVIEWER_MODEL,
        "silver_status": "COMPLETE",
        "selected_mantra_count": 120,
        "reviewed_mantra_count": 120,
        "evidence_packet_hashes": {},
        "output_hashes": {},
        "created_at": datetime(2026, 9, 5, tzinfo=UTC),
    }
    assert SilverBenchmarkManifest.model_validate(fields).unlocked_predicates == []
    with pytest.raises(ValidationError):
        SilverBenchmarkManifest.model_validate(fields | {"unlocked_predicates": ["INVOKES"]})
