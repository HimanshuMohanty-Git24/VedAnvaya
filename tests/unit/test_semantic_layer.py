"""Offline tests for the semantic candidate layer.

Every test here runs without a network, without a key and without a bill. That is not a
convenience: the properties being tested — that a fabricated citation is caught, that a
forbidden predicate is refused, that similarity never merges a concept, that nothing is
auto-accepted before it is measured — are the ones that must hold on every commit, and a
test that needs an API is a test that will be skipped.

The one test that would call the API is marked ``api`` and is deselected by default.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
import yaml

from vedagraph.models.enums import (
    EvidenceSpanType,
    SemanticAssertionStatus,
    SemanticEntityResolution,
    SemanticValidationCode,
)
from vedagraph.models.semantic import (
    EvidencePacket,
    GoldAnnotation,
    GoldRelation,
    SemanticAssertionCandidate,
    SemanticAssertionObject,
    SemanticEvidence,
    TokenUsage,
)
from vedagraph.semantic.evaluate import (
    PRECISION_TARGET,
    UNANNOTATED,
    CostReport,
    compare_exact_parallels,
    evaluate_against_gold,
    load_gold_annotations,
)
from vedagraph.semantic.extract import (
    SCHEMA_NAME,
    ExtractionConfig,
    OpenAILunaProvider,
    RecordedProvider,
    extraction_json_schema,
    load_system_prompt,
    render_user_message,
)
from vedagraph.semantic.ontology import (
    ALLOWED_PREDICATES,
    FORBIDDEN_PREDICATES,
    ONTOLOGY_VERSION,
    Explicitness,
    InterpretationRisk,
    SemanticNodeType,
    SemanticPredicate,
    SemanticSubjectKind,
    predicate_rule,
)
from vedagraph.semantic.packet import PACKET_VERSION, PacketSources, packet_input_hash, sha256_text
from vedagraph.semantic.pilot import STRATA
from vedagraph.semantic.registry import (
    ResolutionIndex,
    candidate_id,
    load_semantic_entities,
    normalization_queue,
    normalize_label,
    resolve_entity_candidates,
)
from vedagraph.semantic.run import build_manifest, run_pilot, write_outputs
from vedagraph.semantic.validate import (
    check_deterministic_conflict,
    decide_status,
    parse_extraction,
    validate_structure,
)

AGNI = "VG:DEVATA:AGNIH"
INDRA = "VG:DEVATA:INDRAH"
KEY = "VG:RV:SAK:M01:S001:V001"
NEXT_KEY = "VG:RV:SAK:M01:S001:V002"
TOKEN = "VG:TOKEN:VEDAWEB-ZURICH:RV:SAK:M01:S001:V001:PA:T001"
TRANSLATION_ID = "b6940a84-f1a1-5a93-8dd6-2fee0fe926be"
TRANSLATION_TEXT = "I laud Agni, the chosen Priest."


def make_packet(**overrides: object) -> EvidencePacket:
    fields: dict[str, object] = {
        "packet_version": PACKET_VERSION,
        "passage_key": KEY,
        "passage_id": UUID("141a362f-1690-5244-831d-e0304db2fdc8"),
        "citation": "RV 1.1.1",
        "mandala": 1,
        "sukta": 1,
        "mantra": 1,
        "sanskrit": "agním īḷe puróhitam",
        "sanskrit_text_version_id": "GRETIL.RV.AUFRECHT",
        "translation": {
            "translation_id": TRANSLATION_ID,
            "translator": "Ralph T. H. Griffith",
            "language": "en",
            "text": TRANSLATION_TEXT,
            "text_sha256": sha256_text(TRANSLATION_TEXT),
        },
        "devata_keys": [AGNI],
        "devata_labels": ["agniḥ"],
        "chandas_keys": ["VG:CHANDAS:GAYATRI"],
        "tokens": [
            {
                "token_key": TOKEN,
                "pada": "a",
                "sequence": 1,
                "surface": "agním",
                "lemma": "agní-",
                "part_of_speech": "nominal stem",
                "morphology": {"case": "ACC", "gender": "M", "number": "SG"},
            }
        ],
        "mentions": [
            {
                "entity_key": AGNI,
                "entity_label": "agniḥ",
                "occurrence_count": 1,
                "token_keys": [TOKEN],
            }
        ],
        "sukta_mantra_count": 9,
        "input_sha256": "a" * 64,
    }
    fields.update(overrides)
    return EvidencePacket.model_validate(fields)


def make_candidate(**overrides: object) -> SemanticAssertionCandidate:
    fields: dict[str, object] = {
        "candidate_assertion_id": "SEMASSERT:test:01",
        "subject_key": KEY,
        "subject_kind": SemanticSubjectKind.MANTRA,
        "predicate": SemanticPredicate.PRAISES,
        "object": SemanticAssertionObject(entity_key=AGNI),
        "evidence": [
            SemanticEvidence(
                passage_key=KEY,
                span_type=EvidenceSpanType.SANSKRIT_TOKEN,
                sanskrit_token_keys=[TOKEN],
            )
        ],
        "explicitness": Explicitness.EXPLICIT,
        "confidence": 0.9,
        "model": "gpt-5.6-luna",
        "prompt_version": "rigveda-semantic-extraction-v1",
        "ontology_version": ONTOLOGY_VERSION,
        "schema_name": SCHEMA_NAME,
        "input_sha256": "a" * 64,
    }
    fields.update(overrides)
    return SemanticAssertionCandidate.model_validate(fields)


def validate(candidate: SemanticAssertionCandidate, packet: EvidencePacket | None = None):
    return validate_structure(
        candidate,
        packet or make_packet(),
        canonical_entity_keys=frozenset({AGNI, INDRA}),
        resolved_candidate_ids=frozenset(),
    )


# --------------------------------------------------------------------------------------
# Ontology
# --------------------------------------------------------------------------------------


def test_every_predicate_is_either_allowed_or_refused_with_a_reason():
    """A predicate that is neither is one nobody decided about."""
    assert ALLOWED_PREDICATES.isdisjoint(FORBIDDEN_PREDICATES)
    assert ALLOWED_PREDICATES | frozenset(FORBIDDEN_PREDICATES) == frozenset(SemanticPredicate)
    assert all(reason.strip() for reason in FORBIDDEN_PREDICATES.values())


def test_metaphysical_predicates_are_refused():
    for predicate in (
        SemanticPredicate.SYMBOLIZES,
        SemanticPredicate.REPRESENTS,
        SemanticPredicate.IS_GOD_OF,
        SemanticPredicate.MEANS,
        SemanticPredicate.CAUSES,
    ):
        assert predicate_rule(predicate) is None
        assert predicate in FORBIDDEN_PREDICATES


def test_no_high_risk_predicate_is_allowed_in_v1():
    assert all(
        rule.risk is not InterpretationRisk.HIGH
        for rule in (predicate_rule(item) for item in ALLOWED_PREDICATES)
        if rule is not None
    )


def test_has_theme_can_never_be_auto_accepted():
    """A theme is a summary judgement. It is the predicate most likely to look right."""
    rule = predicate_rule(SemanticPredicate.HAS_THEME)
    assert rule is not None
    assert rule.auto_acceptable == frozenset()


def test_only_low_risk_predicates_may_auto_accept():
    for predicate in ALLOWED_PREDICATES:
        rule = predicate_rule(predicate)
        assert rule is not None
        if rule.auto_acceptable:
            assert rule.risk is InterpretationRisk.LOW
            assert rule.auto_acceptable == frozenset({Explicitness.EXPLICIT})


# --------------------------------------------------------------------------------------
# Evidence packet
# --------------------------------------------------------------------------------------


def test_packet_hash_is_stable_and_order_independent():
    payload = {"b": 2, "a": 1}
    assert packet_input_hash(payload) == packet_input_hash({"a": 1, "b": 2})


def test_the_stored_packet_index_carries_no_source_text():
    """The rights posture: identifiers and hashes travel, source text does not."""
    packet = make_packet()
    assert packet.translation is not None and packet.translation.text == TRANSLATION_TEXT
    row = json.dumps(packet.index_row())
    assert TRANSLATION_TEXT not in row
    assert packet.sanskrit not in row
    assert packet.translation.text_sha256 in row
    assert packet.input_sha256 in row


def test_missing_translation_is_recorded_not_filled_in():
    packet = make_packet(translation=None, translation_missing=True)
    assert packet.translation is None
    assert packet.translation_missing is True
    assert "translate" not in render_user_message(packet).lower()


def test_citable_surfaces_are_exactly_what_was_supplied():
    packet = make_packet()
    assert packet.citable_token_keys == frozenset({TOKEN})
    assert packet.citable_passage_keys == frozenset({KEY})


# --------------------------------------------------------------------------------------
# Structural validation
# --------------------------------------------------------------------------------------


def test_a_well_formed_candidate_has_no_faults():
    assert validate(make_candidate()) == []


def test_evidence_naming_a_token_the_model_never_saw_is_rejected():
    """The single most valuable check here: it catches a fabricated citation exactly."""
    candidate = make_candidate(
        evidence=[
            SemanticEvidence(
                passage_key=KEY,
                span_type=EvidenceSpanType.SANSKRIT_TOKEN,
                sanskrit_token_keys=["VG:TOKEN:VEDAWEB-ZURICH:RV:SAK:M09:S113:V011:PA:T001"],
            )
        ]
    )
    assert SemanticValidationCode.EVIDENCE_TOKEN_NOT_IN_PASSAGE in validate(candidate)


def test_an_assertion_with_no_evidence_is_rejected():
    assert SemanticValidationCode.NO_EVIDENCE in validate(make_candidate(evidence=[]))


def test_a_claim_about_a_passage_not_in_the_packet_is_rejected():
    candidate = make_candidate(subject_key="VG:RV:SAK:M10:S129:V001")
    assert SemanticValidationCode.PASSAGE_NOT_IN_PACKET in validate(candidate)


def test_a_forbidden_predicate_is_refused_by_name():
    candidate = make_candidate(predicate=SemanticPredicate.SYMBOLIZES)
    codes = validate(candidate)
    assert SemanticValidationCode.PREDICATE_FORBIDDEN in codes
    assert SemanticValidationCode.PREDICATE_NOT_WHITELISTED not in codes


def test_an_object_type_the_predicate_does_not_take_is_rejected():
    """REFERS_TO_PLACE takes a place. An offering is not a place."""
    candidate = make_candidate(
        predicate=SemanticPredicate.REFERS_TO_PLACE,
        object=SemanticAssertionObject(
            candidate_entity_id="soma", node_type=SemanticNodeType.OFFERING
        ),
    )
    assert SemanticValidationCode.OBJECT_TYPE_INVALID in validate(candidate)


def test_an_unknown_canonical_entity_is_rejected():
    candidate = make_candidate(object=SemanticAssertionObject(entity_key="VG:DEVATA:NOT_A_DEITY"))
    assert SemanticValidationCode.UNKNOWN_CANONICAL_ENTITY in validate(candidate)


def test_an_object_naming_both_or_neither_target_cannot_be_built():
    with pytest.raises(ValueError, match="either a canonical entity or a candidate"):
        SemanticAssertionObject(entity_key=AGNI, candidate_entity_id="rta")
    with pytest.raises(ValueError, match="either a canonical entity or a candidate"):
        SemanticAssertionObject()


def test_a_candidate_object_without_a_node_type_is_malformed():
    with pytest.raises(ValueError, match="must declare its node type"):
        SemanticAssertionObject(candidate_entity_id="rta")


def test_explicit_cannot_rest_on_the_english_alone():
    """ "Griffith says so" is explicit about Griffith, not about the Rigveda."""
    candidate = make_candidate(
        evidence=[
            SemanticEvidence(
                passage_key=KEY,
                span_type=EvidenceSpanType.TRANSLATION_LINE,
                translation_id=TRANSLATION_ID,
            )
        ],
        explicitness=Explicitness.EXPLICIT,
    )
    assert SemanticValidationCode.EXPLICITNESS_UNSUPPORTED_BY_EVIDENCE in validate(candidate)


def test_a_translation_id_that_was_not_supplied_is_rejected():
    candidate = make_candidate(
        evidence=[
            SemanticEvidence(
                passage_key=KEY,
                span_type=EvidenceSpanType.TRANSLATION_LINE,
                translation_id="00000000-0000-0000-0000-000000000000",
            )
        ],
        explicitness=Explicitness.STRONG_INFERENCE,
    )
    assert SemanticValidationCode.EVIDENCE_TRANSLATION_NOT_SUPPLIED in validate(candidate)


# --------------------------------------------------------------------------------------
# Acceptance
# --------------------------------------------------------------------------------------


def test_nothing_is_auto_accepted_before_a_predicate_is_unlocked():
    """The default state of the pipeline: a first run accepts nothing automatically."""
    verdict = decide_status(make_candidate(), [], unlocked_predicates=frozenset())
    assert verdict.status is SemanticAssertionStatus.NEEDS_REVIEW
    assert "unlocked" in verdict.reason


def test_high_confidence_alone_never_accepts_anything():
    """Confidence is the model grading its own paper. It buys nothing on its own."""
    verdict = decide_status(make_candidate(confidence=1.0), [], unlocked_predicates=frozenset())
    assert verdict.status is SemanticAssertionStatus.NEEDS_REVIEW


def test_an_unlocked_explicit_low_risk_claim_is_auto_accepted():
    verdict = decide_status(
        make_candidate(), [], unlocked_predicates=frozenset({SemanticPredicate.PRAISES})
    )
    assert verdict.status is SemanticAssertionStatus.AUTO_ACCEPTED


def test_interpretive_claims_always_go_to_a_person():
    verdict = decide_status(
        make_candidate(explicitness=Explicitness.INTERPRETIVE),
        [],
        unlocked_predicates=frozenset(SemanticPredicate),
    )
    assert verdict.status is SemanticAssertionStatus.NEEDS_REVIEW


def test_confidence_below_the_predicate_floor_goes_to_review():
    verdict = decide_status(
        make_candidate(confidence=0.5),
        [],
        unlocked_predicates=frozenset({SemanticPredicate.PRAISES}),
    )
    assert verdict.status is SemanticAssertionStatus.NEEDS_REVIEW
    assert "floor" in verdict.reason


def test_any_structural_fault_rejects_regardless_of_everything_else():
    verdict = decide_status(
        make_candidate(confidence=1.0),
        [SemanticValidationCode.NO_EVIDENCE],
        unlocked_predicates=frozenset(SemanticPredicate),
    )
    assert verdict.status is SemanticAssertionStatus.VALIDATION_REJECTED


def test_a_metadata_divergence_is_flagged_for_review_not_rejected():
    """A mantra assigned to Agni may praise Indra. That is a finding, not an error."""
    candidate = make_candidate(object=SemanticAssertionObject(entity_key=INDRA))
    packet = make_packet()
    assert check_deterministic_conflict(candidate, packet) is True
    verdict = decide_status(
        candidate,
        [],
        unlocked_predicates=frozenset(SemanticPredicate),
        conflicts_with_metadata=True,
    )
    assert verdict.status is SemanticAssertionStatus.NEEDS_REVIEW
    assert verdict.conflicts_with_metadata is True
    assert SemanticValidationCode.DETERMINISTIC_CONTEXT_CONFLICT in verdict.codes


def test_a_claim_matching_the_assigned_devata_is_not_flagged():
    assert check_deterministic_conflict(make_candidate(), make_packet()) is False


# --------------------------------------------------------------------------------------
# Structured output, parsing and the provider
# --------------------------------------------------------------------------------------


def test_the_schema_is_strict_everywhere():
    """Strict mode needs every object closed and every property required."""

    def walk(node: object) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert node.get("additionalProperties") is False
                assert set(node["required"]) == set(node["properties"])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(extraction_json_schema())


def test_the_schema_offers_only_allowed_predicates():
    schema = extraction_json_schema()
    offered = schema["properties"]["assertions"]["items"]["properties"]["predicate"]["enum"]
    assert set(offered) == {item.value for item in ALLOWED_PREDICATES}
    assert not set(offered) & {item.value for item in FORBIDDEN_PREDICATES}


def test_the_committed_prompt_matches_the_code_ontology():
    prompt = load_system_prompt(Path("prompts/semantic_extraction_v1.md"))
    assert prompt.ontology_version == ONTOLOGY_VERSION
    assert prompt.packet_version == PACKET_VERSION
    assert prompt.text


def test_a_prompt_written_against_another_ontology_is_refused(tmp_path):
    path = tmp_path / "p.md"
    path.write_text(
        "---\nprompt_version: x\nontology_version: old\npacket_version: y\n---\nbody",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="was written against ontology"):
        load_system_prompt(path)


def test_parsing_keeps_malformed_assertions_out_rather_than_repairing_them():
    packet = make_packet()
    payload = {
        "mantra_id": "RV 1.1.1",
        "entities": [
            {
                "local_id": "rta",
                "entity_type": "PHILOSOPHICAL_CONCEPT",
                "label": "ṛta",
                "description": "",
                "aliases": [],
            }
        ],
        "assertions": [
            {
                "predicate": "PRAISES",
                "subject_passage_key": KEY,
                "object_entity_key": AGNI,
                "object_local_id": None,
                "explicitness": "EXPLICIT",
                "confidence": 0.9,
                "evidence": [
                    {
                        "passage_key": KEY,
                        "span_type": "SANSKRIT_TOKEN",
                        "sanskrit_token_keys": [TOKEN],
                        "translation_id": None,
                        "note": "",
                    }
                ],
            },
            {
                "predicate": "NOT_A_PREDICATE",
                "subject_passage_key": KEY,
                "object_entity_key": AGNI,
                "object_local_id": None,
                "explicitness": "EXPLICIT",
                "confidence": 0.9,
                "evidence": [],
            },
        ],
        "uncertainties": ["unsure about the second pāda"],
        "no_claim_reasons": [],
    }
    parsed = parse_extraction(
        packet,
        payload,
        model="gpt-5.6-luna",
        model_snapshot="gpt-5.6-luna",
        reasoning_effort="medium",
        prompt_version="rigveda-semantic-extraction-v1",
        ontology_version=ONTOLOGY_VERSION,
        schema_name=SCHEMA_NAME,
    )
    assert len(parsed.candidates) == 1
    assert len(parsed.parse_errors) == 1
    assert parsed.uncertainties == ["unsure about the second pāda"]
    assert parsed.entity_proposals[0][2] == "ṛta"
    assert all(item.status is SemanticAssertionStatus.CANDIDATE for item in parsed.candidates), (
        "the extractor may only ever produce CANDIDATE"
    )


def test_a_transport_failure_is_retried_then_recorded():
    class Flaky:
        def __init__(self) -> None:
            self.calls = 0
            self.responses = self

        def create(self, **_: object) -> object:
            self.calls += 1
            raise TimeoutError("boom")

    client = Flaky()
    provider = OpenAILunaProvider(ExtractionConfig(max_attempts=3), client=client)
    result = provider.extract(make_packet(), load_system_prompt())
    assert client.calls == 3
    assert result.ok is False
    assert "TimeoutError" in result.error


def test_a_refusal_is_recorded_and_not_retried():
    class Refusing:
        def __init__(self) -> None:
            self.calls = 0
            self.responses = self

        def create(self, **_: object) -> object:
            self.calls += 1
            return type("R", (), {"output_text": "", "output": [], "usage": None, "id": "r"})()

    client = Refusing()
    provider = OpenAILunaProvider(ExtractionConfig(max_attempts=3), client=client)
    result = provider.extract(make_packet(), load_system_prompt())
    assert client.calls == 1
    assert result.refused is True


def test_actual_usage_is_read_off_the_reply_never_estimated():
    class WithUsage:
        def __init__(self) -> None:
            self.responses = self

        def create(self, **_: object) -> object:
            usage = type(
                "U",
                (),
                {
                    "input_tokens": 4000,
                    "output_tokens": 700,
                    "input_tokens_details": type("D", (), {"cached_tokens": 3000})(),
                    "output_tokens_details": type("O", (), {"reasoning_tokens": 300})(),
                },
            )()
            return type(
                "R",
                (),
                {
                    "output_text": json.dumps(
                        {
                            "mantra_id": "RV 1.1.1",
                            "entities": [],
                            "assertions": [],
                            "uncertainties": [],
                            "no_claim_reasons": ["nothing the evidence supports"],
                        }
                    ),
                    "usage": usage,
                    "model": "gpt-5.6-luna",
                    "id": "resp_1",
                },
            )()

    provider = OpenAILunaProvider(ExtractionConfig(), client=WithUsage())
    result = provider.extract(make_packet(), load_system_prompt())
    assert result.ok
    assert result.usage.input_tokens == 4000
    assert result.usage.cached_input_tokens == 3000
    assert result.usage.reasoning_tokens == 300


@pytest.mark.api
def test_live_luna_extraction_is_schema_conformant():  # pragma: no cover - opt-in only
    """Deselected by default. Run with `pytest -m api` and a key, and it will cost money."""
    pytest.importorskip("openai")
    provider = OpenAILunaProvider(ExtractionConfig())
    result = provider.extract(make_packet(), load_system_prompt())
    assert result.ok
    assert set(result.payload) >= {"mantra_id", "entities", "assertions"}


# --------------------------------------------------------------------------------------
# Entity registry
# --------------------------------------------------------------------------------------


def test_labels_folding_to_the_same_form_are_one_candidate():
    assert normalize_label("Ṛta") == normalize_label("rta") == "rta"
    assert normalize_label("the Sacrifice") == "sacrifice"
    assert candidate_id(SemanticNodeType.CONCEPT, "Ṛta") == candidate_id(
        SemanticNodeType.CONCEPT, "rta"
    )


def test_different_concepts_are_not_folded_together():
    assert normalize_label("cosmic order") != normalize_label("order")


def test_similarity_never_merges_and_only_asks():
    """The failure mode this module exists for: Cosmic Order and Ṛta stay separate."""
    proposals = [
        ("VG:RV:SAK:M01:S001:V001", SemanticNodeType.CONCEPT, "cosmic order", "", []),
        ("VG:RV:SAK:M01:S001:V002", SemanticNodeType.CONCEPT, "cosmic order", "", []),
        ("VG:RV:SAK:M01:S002:V001", SemanticNodeType.CONCEPT, "the cosmic order", "", []),
        ("VG:RV:SAK:M01:S003:V001", SemanticNodeType.CONCEPT, "ṛta", "", []),
    ]
    resolved = resolve_entity_candidates(
        proposals,
        ResolutionIndex.build({}),
        model="test",
        prompt_version="v1",
        ontology_version=ONTOLOGY_VERSION,
    )
    labels = {item.candidate_id for item in resolved}
    # "cosmic order" and "the cosmic order" fold to one; "ṛta" stays its own.
    assert len(labels) == 2
    queue = normalization_queue(resolved)
    assert queue == [] or all(len(set(group.labels)) > 1 for group in queue)
    assert all(item.matched_entity_key is None for item in resolved)


def test_a_concept_seen_once_is_not_accepted_as_a_new_entity():
    resolved = resolve_entity_candidates(
        [("VG:RV:SAK:M01:S001:V001", SemanticNodeType.CONCEPT, "singular idea", "", [])],
        ResolutionIndex.build({}),
        model="test",
        prompt_version="v1",
        ontology_version=ONTOLOGY_VERSION,
    )
    assert resolved[0].resolution is SemanticEntityResolution.NEEDS_REVIEW


def test_an_exact_registry_hit_matches_and_does_not_create():
    registry_rows = load_semantic_entities(Path("data/registry"))
    index = ResolutionIndex.build(registry_rows)
    proposals = [
        (f"VG:RV:SAK:M01:S001:V00{n}", SemanticNodeType.CONCEPT, "brand new idea", "", [])
        for n in (1, 2, 3)
    ]
    resolved = resolve_entity_candidates(
        proposals, index, model="t", prompt_version="v1", ontology_version=ONTOLOGY_VERSION
    )
    assert resolved[0].resolution is SemanticEntityResolution.ACCEPTED_NEW_ENTITY
    assert resolved[0].evidence_count == 3


def test_the_semantic_entity_registry_starts_empty():
    """Nothing asserts that ṛta exists until an extraction proposes it and a person agrees."""
    assert load_semantic_entities(Path("data/registry")) == {}


def test_a_registry_file_must_pin_its_policy_version(tmp_path):
    (tmp_path / "semantic_entities.yaml").write_text(
        yaml.safe_dump({"policy_version": "wrong", "entities": []}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="policy_version"):
        load_semantic_entities(tmp_path)


def test_the_normalization_queue_creates_nothing():
    resolved = resolve_entity_candidates(
        [
            ("VG:RV:SAK:M01:S001:V001", SemanticNodeType.CONCEPT, "creation", "", []),
            ("VG:RV:SAK:M01:S001:V002", SemanticNodeType.CONCEPT, "creations", "", []),
        ],
        ResolutionIndex.build({}),
        model="t",
        prompt_version="v1",
        ontology_version=ONTOLOGY_VERSION,
    )
    groups = normalization_queue(resolved)
    assert groups and set(groups[0].labels) == {"creation", "creations"}
    assert all(item.matched_entity_key is None for item in resolved)


# --------------------------------------------------------------------------------------
# Evaluation and cost
# --------------------------------------------------------------------------------------


def _gold(**overrides: object) -> GoldAnnotation:
    fields: dict[str, object] = {
        "passage_key": KEY,
        "citation": "RV 1.1.1",
        "annotator": "test",
        "annotated_at": datetime(2026, 9, 5, tzinfo=UTC),
        "entities": ["agniḥ"],
        "relations": [
            GoldRelation(
                predicate=SemanticPredicate.PRAISES,
                object_label="agniḥ",
                object_entity_key=AGNI,
                explicitness=Explicitness.EXPLICIT,
            )
        ],
    }
    fields.update(overrides)
    return GoldAnnotation.model_validate(fields)


def test_a_correct_prediction_scores_a_true_positive():
    report = evaluate_against_gold(
        {KEY: _gold()},
        {KEY: [make_candidate()]},
        {},
        entity_labels={AGNI: "agniḥ"},
        candidate_labels={},
    )
    score = report.relation_scores[SemanticPredicate.PRAISES]
    assert score.true_positives == 1
    assert score.precision == 1.0


def test_emitting_a_relation_the_gold_marked_rejected_is_counted_separately():
    """Restraint is measured. A tempting-but-unsupported claim is worse than a miss."""
    gold = _gold(
        relations=[
            GoldRelation(
                predicate=SemanticPredicate.PRAISES,
                object_label="indraḥ",
                explicitness=Explicitness.INTERPRETIVE,
                rejected=True,
                note="the hymn is about Agni; Indra is not named",
            )
        ]
    )
    report = evaluate_against_gold(
        {KEY: gold},
        {KEY: [make_candidate(object=SemanticAssertionObject(entity_key=INDRA))]},
        {},
        entity_labels={INDRA: "indraḥ"},
        candidate_labels={},
    )
    assert report.rejected_relations_emitted == 1
    assert report.relation_scores[SemanticPredicate.PRAISES].precision == 0.0


def test_overstated_explicitness_is_counted():
    gold = _gold(
        relations=[
            GoldRelation(
                predicate=SemanticPredicate.PRAISES,
                object_label="agniḥ",
                explicitness=Explicitness.STRONG_INFERENCE,
            )
        ]
    )
    report = evaluate_against_gold(
        {KEY: gold},
        {KEY: [make_candidate(explicitness=Explicitness.EXPLICIT)]},
        {},
        entity_labels={AGNI: "agniḥ"},
        candidate_labels={},
    )
    assert report.explicitness_overstated == 1


def test_a_predicate_below_target_is_not_unlocked():
    gold = {
        f"VG:RV:SAK:M01:S001:V{n:03d}": _gold(passage_key=f"VG:RV:SAK:M01:S001:V{n:03d}")
        for n in (1, 2)
    }
    predictions = {
        "VG:RV:SAK:M01:S001:V001": [make_candidate()],
        "VG:RV:SAK:M01:S001:V002": [
            make_candidate(
                candidate_assertion_id="x",
                subject_key="VG:RV:SAK:M01:S001:V002",
                object=SemanticAssertionObject(entity_key=INDRA),
            )
        ],
    }
    report = evaluate_against_gold(
        gold, predictions, {}, entity_labels={AGNI: "agniḥ", INDRA: "indraḥ"}, candidate_labels={}
    )
    score = report.relation_scores[SemanticPredicate.PRAISES]
    assert score.precision == 0.5 < PRECISION_TARGET
    assert report.unlocked_predicates() == frozenset()


def test_an_unannotated_worksheet_row_is_skipped_not_scored_as_empty():
    """An empty worksheet must not be read as "the gold says none of this is there"."""
    path = Path("data/gold/rigveda_semantic_gold_v1.jsonl")
    rows = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert rows, "the worksheet should list the gold mantras"
    loaded = load_gold_annotations(path)
    unannotated = [row for row in rows if json.loads(row)["annotator"] == UNANNOTATED]
    assert len(loaded) == len(rows) - len(unannotated)


def test_gold_worksheet_rows_carry_no_source_text():
    text = Path("data/gold/rigveda_semantic_gold_v1.jsonl").read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.strip():
            row = json.loads(line)
            assert set(row) == {
                "passage_key",
                "citation",
                "annotator",
                "annotated_at",
                "entities",
                "relations",
                "notes",
                "schema_version",
            }


def test_a_predicate_absent_from_gold_is_never_unlocked():
    report = evaluate_against_gold({}, {}, {}, entity_labels={}, candidate_labels={})
    assert report.unlocked_predicates() == frozenset()


def test_exact_parallel_disagreement_is_reported_not_copied():
    other = "VG:RV:SAK:M05:S005:V008"
    predictions = {
        KEY: [make_candidate()],
        other: [
            make_candidate(
                candidate_assertion_id="y",
                subject_key=other,
                object=SemanticAssertionObject(entity_key=INDRA),
            )
        ],
    }
    report = compare_exact_parallels(
        predictions, {KEY: [other], other: [KEY]}, entity_labels={AGNI: "agniḥ", INDRA: "indraḥ"}
    )
    assert report.pairs_compared == 1
    assert report.pairs_identical == 0
    assert report.disagreements[0].only_left == ("PRAISES->agnih",)
    # Nothing was copied across: each mantra keeps exactly what was extracted for it.
    assert len(predictions[KEY]) == 1


def test_cost_uses_actual_usage_and_prices_cached_input_separately():
    cost = CostReport(
        usage=TokenUsage(
            requests=2, input_tokens=1_000_000, cached_input_tokens=500_000, output_tokens=100_000
        ),
        passage_count=2,
        input_usd_per_million=0.20,
        cached_input_usd_per_million=0.02,
        output_usd_per_million=1.20,
    )
    assert cost.uncached_input_tokens == 500_000
    assert cost.total_cost_usd == pytest.approx(0.10 + 0.01 + 0.12)
    assert cost.cost_per_mantra_usd == pytest.approx(cost.total_cost_usd / 2)
    assert cost.projected_full_corpus_usd == pytest.approx(cost.cost_per_mantra_usd * 10552)


# --------------------------------------------------------------------------------------
# Pilot selection and the end-to-end offline run
# --------------------------------------------------------------------------------------


def test_the_committed_pilot_config_is_ids_only_and_in_range():
    document = yaml.safe_load(
        Path("data/builds/rigveda_semantic_pilot_v1.yaml").read_text(encoding="utf-8")
    )
    assert 400 <= document["pilot_mantra_count"] <= 600
    assert 100 <= document["gold_mantra_count"] <= 150
    rows = document["mantras"]
    assert {key for row in rows for key in row} == {"passage_key", "citation", "stratum", "gold"}
    mandalas = {int(row["passage_key"].split(":")[3][1:]) for row in rows}
    assert mandalas == set(range(1, 11)), "every Mandala must be represented"
    assert {item.name for item in STRATA} >= {row["stratum"] for row in rows}


def test_the_gold_subset_is_drawn_from_the_pilot():
    document = yaml.safe_load(
        Path("data/builds/rigveda_semantic_pilot_v1.yaml").read_text(encoding="utf-8")
    )
    gold = {row["passage_key"] for row in document["mantras"] if row["gold"]}
    strata = {row["stratum"] for row in document["mantras"] if row["gold"]}
    assert gold and len(strata) > 1, "gold must span strata, not sample one easy slice"


def _sources() -> PacketSources:
    """A one-mantra PacketSources, so the orchestration is exercised without a corpus."""
    return PacketSources(
        passage_ids={KEY: UUID("141a362f-1690-5244-831d-e0304db2fdc8")},
        citations={KEY: "RV 1.1.1"},
        sanskrit={KEY: "agním īḷe puróhitam"},
        translations={},
        rishis={},
        devatas={KEY: [AGNI]},
        chandas={},
        entity_labels={AGNI: "agniḥ", INDRA: "indraḥ"},
        tokens={},
        mentions={},
        exact_parallels={},
        near_parallels={},
        sukta_sizes={"VG:RV:SAK:M01:S001": 9},
    )


def _reply(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "mantra_id": "RV 1.1.1",
        "entities": [],
        "assertions": [
            {
                "predicate": "PRAISES",
                "subject_passage_key": KEY,
                "object_entity_key": AGNI,
                "object_local_id": None,
                "explicitness": "EXPLICIT",
                "confidence": 0.95,
                "evidence": [
                    {
                        "passage_key": KEY,
                        "span_type": "SANSKRIT_LINE",
                        "sanskrit_token_keys": [],
                        "translation_id": None,
                        "note": "pada a names the deity",
                    }
                ],
            }
        ],
        "uncertainties": [],
        "no_claim_reasons": [],
    }
    payload.update(overrides)
    return payload


def _run(payload: dict[str, object], **kwargs: object):
    return run_pilot(
        [KEY],
        _sources(),
        RecordedProvider(payloads={KEY: payload}),
        load_system_prompt(),
        ExtractionConfig(),
        canonical_entity_keys=frozenset({AGNI, INDRA}),
        registry_index=ResolutionIndex.build({}),
        **kwargs,  # type: ignore[arg-type]
    )


def test_an_offline_run_produces_reviewable_candidates_and_accepts_nothing():
    """The whole pipeline end to end with a recorded provider: no key, no network, no bill."""
    result = _run(_reply())
    assert len(result.assertions) == 1
    assert result.assertions[0].status is SemanticAssertionStatus.NEEDS_REVIEW
    assert result.by_status(SemanticAssertionStatus.AUTO_ACCEPTED) == []
    assert result.usage.requests == 1


def test_an_unlocked_predicate_reaches_auto_accepted_through_the_full_run():
    result = _run(_reply(), unlocked_predicates=frozenset({SemanticPredicate.PRAISES}))
    assert result.assertions[0].status is SemanticAssertionStatus.AUTO_ACCEPTED


def test_a_run_rejects_a_fabricated_citation_end_to_end():
    payload = _reply(
        assertions=[
            {
                "predicate": "PRAISES",
                "subject_passage_key": KEY,
                "object_entity_key": AGNI,
                "object_local_id": None,
                "explicitness": "EXPLICIT",
                "confidence": 0.99,
                "evidence": [
                    {
                        "passage_key": KEY,
                        "span_type": "SANSKRIT_TOKEN",
                        "sanskrit_token_keys": [
                            "VG:TOKEN:VEDAWEB-ZURICH:RV:SAK:M09:S001:V001:PA:T001"
                        ],
                        "translation_id": None,
                        "note": "",
                    }
                ],
            }
        ]
    )
    result = _run(payload, unlocked_predicates=frozenset(SemanticPredicate))
    assert result.assertions[0].status is SemanticAssertionStatus.VALIDATION_REJECTED


def test_an_object_naming_an_entity_the_reply_never_declared_is_unresolved():
    """A local id is scoped to its own reply. Pointing at an undeclared one is dropped."""
    payload = _reply(
        assertions=[
            {
                "predicate": "HAS_THEME",
                "subject_passage_key": KEY,
                "object_entity_key": None,
                "object_local_id": "never_declared",
                "explicitness": "STRONG_INFERENCE",
                "confidence": 0.8,
                "evidence": [
                    {
                        "passage_key": KEY,
                        "span_type": "SANSKRIT_LINE",
                        "sanskrit_token_keys": [],
                        "translation_id": None,
                        "note": "",
                    }
                ],
            }
        ]
    )
    result = _run(payload)
    # The claim cannot be built at all, so it is dropped and the reason is recorded.
    # It is never repaired by guessing which entity was meant.
    assert result.assertions == []
    assert len(result.parse_errors) == 1
    passage_key, message = result.parse_errors[0]
    assert passage_key == KEY
    assert "must declare its node type" in message


def test_an_object_naming_an_entity_the_reply_did_declare_resolves():
    payload = _reply(
        entities=[
            {
                "local_id": "rta",
                "entity_type": "PHILOSOPHICAL_CONCEPT",
                "label": "ṛta",
                "description": "",
                "aliases": [],
            }
        ],
        assertions=[
            {
                "predicate": "HAS_THEME",
                "subject_passage_key": KEY,
                "object_entity_key": None,
                "object_local_id": "rta",
                "explicitness": "STRONG_INFERENCE",
                "confidence": 0.8,
                "evidence": [
                    {
                        "passage_key": KEY,
                        "span_type": "SANSKRIT_LINE",
                        "sanskrit_token_keys": [],
                        "translation_id": None,
                        "note": "",
                    }
                ],
            }
        ],
    )
    result = _run(payload)
    assert result.assertions[0].status is SemanticAssertionStatus.NEEDS_REVIEW
    assert result.entity_candidates[0].preferred_label == "ṛta"


def test_a_provider_failure_is_recorded_and_does_not_stop_the_run():
    result = run_pilot(
        [KEY],
        _sources(),
        RecordedProvider(payloads={}),
        load_system_prompt(),
        ExtractionConfig(),
        canonical_entity_keys=frozenset({AGNI}),
        registry_index=ResolutionIndex.build({}),
    )
    assert result.failures == {KEY: "no recorded payload for this passage"}
    assert result.assertions == []


def test_written_outputs_carry_no_source_text(tmp_path):
    """Everything on disk is identifiers and hashes. A source is cited, never copied."""
    result = _run(_reply())
    cost = CostReport(
        usage=result.usage,
        passage_count=1,
        input_usd_per_million=0.20,
        cached_input_usd_per_million=0.02,
        output_usd_per_million=1.20,
    )
    manifest = build_manifest(
        result,
        run_id="test",
        dataset_id="rigveda-semantic-pilot-v1",
        started_at=datetime(2026, 9, 5, tzinfo=UTC),
        corpus_version="vedagraph-rigveda-shakala-1.0.0-rc1",
        corpus_manifest_sha256="0" * 64,
        lexical_policy_version="rigveda-lexical-mention-policy-v2",
        prompt=load_system_prompt(),
        provider=RecordedProvider(payloads={}),
        config=ExtractionConfig(),
        cost=cost,
    )
    written = write_outputs(result, manifest, cost, tmp_path)
    assert written["evidence_packet_index.jsonl"] == 1
    assert written["parse_errors.jsonl"] == 0
    assert written["semantic_candidates.jsonl"] == 1
    assert written["review_semantic_assertions.jsonl"] == 1
    assert written["accepted_semantic_assertions.jsonl"] == 0
    blob = chr(10).join(path.read_text(encoding="utf-8") for path in sorted(tmp_path.glob("*")))
    assert "agním īḷe puróhitam" not in blob
    assert TRANSLATION_TEXT not in blob
    report = json.loads((tmp_path / "cost_report.json").read_text(encoding="utf-8"))
    assert report["passage_count"] == 1
