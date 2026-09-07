import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from vedagraph.models.semantic import (
    EvidencePacket,
    GoldAnnotation,
    GoldEntityAnnotation,
    GoldEvidenceReference,
    GoldRelation,
    GoldReviewMetadata,
    PacketMention,
    PacketToken,
    PacketTranslation,
)
from vedagraph.semantic.evaluate import MIN_PREDICATE_SUPPORT, PredicateScore, wilson_interval
from vedagraph.semantic.gold import (
    finalize_gold,
    load_gold_records,
    save_gold_record,
    validate_annotation,
    validate_gold_file,
)
from vedagraph.semantic.ontology import (
    EvidenceReferenceType,
    Explicitness,
    GoldReviewStatus,
    SemanticNodeType,
    SemanticPredicate,
)

KEY = "VG:RV:SAK:M01:S001:V001"
AGNI = "VG:DEVATA:AGNIH"
TOKEN = "VG:TOKEN:TEST:RV:SAK:M01:S001:V001:PA:T001"
TRANSLATION = "translation-test"


def packet() -> EvidencePacket:
    return EvidencePacket(
        packet_version="test",
        passage_key=KEY,
        passage_id=UUID("141a362f-1690-5244-831d-e0304db2fdc8"),
        citation="RV 1.1.1",
        mandala=1,
        sukta=1,
        mantra=1,
        sanskrit="agním īḷe",
        sanskrit_text_version_id="test",
        translation=PacketTranslation(
            translation_id=TRANSLATION,
            translator="test",
            language="en",
            text="I praise Agni",
            text_sha256="".join(["0"] * 64),
        ),
        devata_keys=[AGNI],
        devata_labels=["agniḥ"],
        tokens=[
            PacketToken(
                token_key=TOKEN,
                pada="a",
                sequence=1,
                surface="agním",
                lemma="agni-",
            )
        ],
        mentions=[
            PacketMention(
                entity_key=AGNI,
                entity_label="agniḥ",
                occurrence_count=1,
                token_keys=[TOKEN],
            )
        ],
        sukta_mantra_count=1,
        input_sha256="".join(["1"] * 64),
    )


def complete_gold() -> GoldAnnotation:
    evidence = GoldEvidenceReference(kind=EvidenceReferenceType.TOKEN, reference_id=TOKEN)
    assertion = GoldRelation(
        subject=KEY,
        predicate=SemanticPredicate.PRAISES,
        object_label="agniḥ",
        object_entity_key=AGNI,
        explicitness=Explicitness.EXPLICIT,
        evidence=[evidence],
    )
    return GoldAnnotation(
        passage_key=KEY,
        citation="RV 1.1.1",
        annotator="human-1",
        annotated_at=datetime(2026, 9, 5, tzinfo=UTC),
        status=GoldReviewStatus.COMPLETE,
        review=GoldReviewMetadata(
            reviewer="human-1",
            reviewed_at=datetime(2026, 9, 5, tzinfo=UTC),
            status=GoldReviewStatus.COMPLETE,
            stage_a_locked=True,
        ),
        gold_entities=[
            GoldEntityAnnotation(
                node_type=SemanticNodeType.COSMIC_ENTITY,
                preferred_label="agniḥ",
                existing_entity_key=AGNI,
                evidence=[evidence],
            )
        ],
        gold_assertions=[assertion],
        relations=[assertion],
    )


def write_fixture_run(root: Path) -> None:
    (root / "batches" / "batch_001").mkdir(parents=True)
    (root / "batches" / "batch_001" / "evidence.jsonl").write_text(
        json.dumps(packet().model_dump(mode="json")) + "\n", encoding="utf-8"
    )


def test_evidence_validator_accepts_packet_ids_and_rejects_unknown_ids() -> None:
    good = complete_gold()
    assert validate_annotation(good, packet()) == ()
    bad = good.model_copy(
        update={
            "relations": [
                good.relations[0].model_copy(
                    update={
                        "evidence": [
                            GoldEvidenceReference(
                                kind=EvidenceReferenceType.TOKEN,
                                reference_id="not-in-packet",
                            )
                        ]
                    }
                )
            ],
            "gold_assertions": [
                good.gold_assertions[0].model_copy(
                    update={
                        "evidence": [
                            GoldEvidenceReference(
                                kind=EvidenceReferenceType.TOKEN,
                                reference_id="not-in-packet",
                            )
                        ]
                    }
                )
            ],
        }
    )
    assert "TOKEN id is not present in packet" in validate_annotation(bad, packet())[0]


def test_no_claim_is_a_valid_complete_annotation() -> None:
    record = complete_gold().model_copy(
        update={"gold_entities": [], "gold_assertions": [], "relations": [], "no_claim": True}
    )
    assert validate_annotation(record, packet()) == ()


def test_gold_save_is_resumable_and_preserves_one_record_per_id(tmp_path: Path) -> None:
    path = tmp_path / "gold.jsonl"
    record = complete_gold().model_copy(update={"status": GoldReviewStatus.IN_PROGRESS})
    save_gold_record(record, path)
    loaded = load_gold_records(path)
    assert len(loaded) == 1
    assert loaded[0].effective_status is GoldReviewStatus.IN_PROGRESS
    save_gold_record(record.model_copy(update={"status": GoldReviewStatus.COMPLETE}), path)
    assert len(load_gold_records(path)) == 1
    assert load_gold_records(path)[0].effective_status is GoldReviewStatus.COMPLETE


def test_second_reviewer_history_is_retained(tmp_path: Path) -> None:
    path = tmp_path / "gold.jsonl"
    first = complete_gold()
    save_gold_record(first, path)
    second = first.model_copy(
        update={
            "annotator": "human-2",
            "review": first.review.model_copy(update={"reviewer": "human-2"}),
        }
    )
    save_gold_record(second, path)
    assert load_gold_records(path)[0].review_history[0].reviewer == "human-1"


def test_gold_file_validator_requires_all_expected_rows(tmp_path: Path) -> None:
    gold_path = tmp_path / "gold.jsonl"
    gold_path.write_text(
        json.dumps(complete_gold().model_dump(mode="json")) + "\n", encoding="utf-8"
    )
    config = tmp_path / "config.yaml"
    config.write_text(
        "mantras:\n  - passage_key: " + KEY + "\n    citation: RV 1.1.1\n    gold: true\n",
        encoding="utf-8",
    )
    run_dir = tmp_path / "run"
    write_fixture_run(run_dir)
    result = validate_gold_file(
        gold_path, config_path=config, run_dir=run_dir, require_complete=True
    )
    assert result.valid
    assert result.complete_count == 1


def test_wilson_interval_and_support_gate_do_not_unlock_eight_examples() -> None:
    interval = wilson_interval(8, 8)
    assert interval is not None
    assert interval[0] == pytest.approx(0.6755843804891231)
    assert interval[1] == 1.0
    score = PredicateScore(
        predicate=SemanticPredicate.PRAISES,
        true_positives=8,
        evidence_correct=8,
        evidence_checked=8,
        explicitness_counts={Explicitness.EXPLICIT.value: 8},
    )
    assert MIN_PREDICATE_SUPPORT == 30
    assert not score.meets_target


def test_finalize_signs_rows_and_writes_hash_manifest(tmp_path: Path) -> None:
    gold_path = tmp_path / "gold.jsonl"
    save_gold_record(complete_gold(), gold_path)
    config = tmp_path / "config.yaml"
    config.write_text(
        "mantras:\n  - passage_key: " + KEY + "\n    citation: RV 1.1.1\n    gold: true\n",
        encoding="utf-8",
    )
    run_dir = tmp_path / "run"
    write_fixture_run(run_dir)
    (run_dir / "semantic_run_manifest.json").write_text(
        json.dumps(
            {
                "ontology_version": "ontology-test",
                "corpus_manifest_sha256": "c" * 64,
                "lexical_knowledge_manifest_sha256": "l" * 64,
            }
        ),
        encoding="utf-8",
    )
    manifest_path = tmp_path / "manifest.json"
    manifest = finalize_gold(
        gold_path,
        config_path=config,
        run_dir=run_dir,
        manifest_path=manifest_path,
    )
    assert manifest["gold_status"] == "SIGNED"
    assert len(manifest["gold_sha256"]) == 64
    assert manifest["reviewers"] == ["human-1"]
    assert len(manifest["evidence_packet_hashes"][KEY]) == 64
    assert load_gold_records(gold_path)[0].effective_status is GoldReviewStatus.SIGNED
