"""The V3.2 prompt policy, its provenance, and the bounded stability experiment.

Everything here is offline. No model is invoked, no API is called, no Luna run is executed,
and nothing under a sealed v3.1 run directory is written -- the last is enforced by a
fixture rather than promised, because it is the property a policy revision is most likely
to break by accident.

NO HUMAN GOLD EXISTS. MODEL SELF-AGREEMENT IS NOT ACCURACY. Nothing in this suite scores
an extraction for correctness; the stability gate measures whether two runs of one prompt
behaved as one policy, which is a different question with a different answer.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest

from vedagraph.models.normalization import (
    SemanticEvidenceAnchor,
    SemanticExtractionV3,
    SemanticObjectCandidate,
    StructuredSemanticAssertion,
    TranslationSpan,
)
from vedagraph.models.semantic import EvidencePacket
from vedagraph.semantic.codex_direct import (
    AssertionBinding,
    BindingAnchor,
    BindingRole,
    ExecutionStore,
    ModelAuthoredResponse,
    ModelExecutionReceipt,
    PreparedTask,
    RunContract,
    load_run_contract,
    prepare_task,
    read_prompt_version,
    response_payload_sha256,
    validate_bindings,
    validate_candidate_invariants,
    validate_receipt,
)
from vedagraph.semantic.evidence import validate_evidence_anchors
from vedagraph.semantic.heuristic_baseline import BASELINE_PROVENANCE, extract_packet
from vedagraph.semantic.normalization import deterministic_object_candidate_id
from vedagraph.semantic.object_ontology import (
    SemanticObjectKind,
    SemanticObjectNormalizationStatus,
)
from vedagraph.semantic.ontology import Explicitness, SemanticPredicate
from vedagraph.semantic.replication_diagnosis import (
    NO_CLAIM_RATE_GAP_ENGINEERING_DEFAULT,
    NO_CLAIM_RATE_GAP_PROVENANCE,
    AlignmentCategory,
    ComparableAssertion,
    DiagnosticSet,
    EmissionRegime,
    OneSidedAssessment,
    PassageOutcome,
    SeverityV2,
    candidate_provenance_label,
    canonical_target_contradictions,
    compare_regimes,
    diagnostic_set_for,
    emission_regime,
    passage_agreement,
    severity_v2,
)
from vedagraph.semantic.spans import find_anchors
from vedagraph.semantic.v3 import PREDICATE_CHECKS, validate_v3_payload
from vedagraph.semantic.v3_2 import (
    EXECUTION_VERSION_V3_2,
    MODEL,
    ONTOLOGY_PATH,
    POLICY_RULES,
    PROMPT_PATH_V3_1,
    PROMPT_PATH_V3_2,
    PROMPT_VERSION_V3_1,
    PROMPT_VERSION_V3_2,
    REASONING,
    RUNTIME,
    SCHEMA_PATH,
    STABILITY_RUN_A,
    STABILITY_RUN_B,
    ExtractionProvenance,
    IntegrityCounts,
    PolicyRule,
    StabilityThresholds,
    build_stability_experiment,
    leaked_identifiers,
    load_selection,
    prompt_policy_errors,
    prompt_sha256,
    prompt_text,
    stability_gate,
)

REGRESSION = Path("data/semantic/vedagraph-rigveda-semantic-luna-v3.1-regression")
PILOT_508 = Path("data/semantic/vedagraph-rigveda-semantic-luna-v3.1-508")
REGRESSION_MANIFEST = Path("docs/manifests/vedagraph-rigveda-semantic-luna-v3.1-regression.json")

#: The inputs the sealed v3.1 runs were pinned to that V3.2 must not disturb. The execution
#: contract file is deliberately absent: it is the one frozen input this revision changes,
#: and the change is verified by re-validating the sealed responses rather than by its hash.
V3_1_UNCHANGED_INPUTS = {
    "prompt_sha256": PROMPT_PATH_V3_1,
    "schema_sha256": SCHEMA_PATH,
    "semantic_ontology_sha256": ONTOLOGY_PATH,
    "object_ontology_sha256": Path("src/vedagraph/semantic/object_ontology.py"),
    "evidence_validator_sha256": Path("src/vedagraph/semantic/evidence.py"),
    "span_validator_sha256": Path("src/vedagraph/semantic/spans.py"),
}

SEALED_ROOTS = (REGRESSION, PILOT_508)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sealed_fingerprint() -> dict[str, str]:
    return {
        str(path): sha256_file(path)
        for root in SEALED_ROOTS
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


@pytest.fixture(scope="module", autouse=True)
def sealed_v3_1_artefacts_are_never_written() -> Iterator[None]:
    """Fail the module if any test writes into a sealed v3.1 run directory."""
    before = sealed_fingerprint()
    yield
    assert sealed_fingerprint() == before, "a test modified a sealed v3.1 artefact"


@lru_cache(maxsize=1)
def regression_manifest() -> dict[str, Any]:
    result: dict[str, Any] = json.loads(REGRESSION_MANIFEST.read_text(encoding="utf-8"))
    return result


@lru_cache(maxsize=1)
def regression_packets() -> dict[str, EvidencePacket]:
    return {
        packet.passage_key: packet
        for line in (REGRESSION / "packets.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
        for packet in [EvidencePacket.model_validate_json(line)]
    }


@lru_cache(maxsize=1)
def sealed_responses() -> dict[str, ModelAuthoredResponse]:
    """Every sealed regression response, keyed by passage. Read only."""
    responses: dict[str, ModelAuthoredResponse] = {}
    for task_dir in sorted((REGRESSION / "store" / "tasks").iterdir()):
        for attempt in sorted((task_dir / "attempts").iterdir()):
            raw = (attempt / "raw_response.json").read_text(encoding="utf-8")
            response = ModelAuthoredResponse.model_validate_json(raw)
            responses[response.receipt.passage_id] = response
    return responses


def v3_2_contract(run_id: str = STABILITY_RUN_A) -> RunContract:
    return load_run_contract(
        run_id=run_id,
        prompt_path=PROMPT_PATH_V3_2,
        schema_path=SCHEMA_PATH,
        ontology_path=ONTOLOGY_PATH,
        model_requested=MODEL,
        reasoning_requested=REASONING,
        execution_version=EXECUTION_VERSION_V3_2,
    )


def unique_phrase(packet: EvidencePacket) -> str:
    """A word occurring exactly once in the translation, so an anchor is unambiguous."""
    assert packet.translation is not None and packet.translation.text is not None
    text = packet.translation.text
    for word in text.replace(",", " ").replace(";", " ").replace(".", " ").split():
        if len(word) >= 4 and len(find_anchors(text, word)) == 1:
            return word
    raise AssertionError(f"no unique anchor phrase in {packet.citation}")


def offering_payload(
    packet: EvidencePacket, run_id: str, phrase: str, *, prompt_version: str
) -> tuple[SemanticExtractionV3, list[AssertionBinding]]:
    """One minimal well-formed candidate payload. Its content is irrelevant to the tests.

    It exists so the provenance boundary can be exercised on the real import path rather
    than on a mock, and it is written by this test, never by any validator.
    """
    assert packet.translation is not None
    anchors = find_anchors(packet.translation.text or "", phrase)
    start, end = anchors[0].start, anchors[0].end
    evidence = [
        SemanticEvidenceAnchor(
            source_passage_id=packet.passage_key,
            translation_record_id=packet.translation.translation_id,
            translation_span=TranslationSpan(start=start, end=end),
            passage_ids=[packet.passage_key],
        )
    ]
    candidate_id = deterministic_object_candidate_id(
        run_id=run_id,
        mantra_id=packet.passage_key,
        predicate=SemanticPredicate.INVOLVES_OFFERING,
        evidence=evidence,
        ordinal=0,
        legacy_object_id=None,
    )
    candidate = SemanticObjectCandidate(
        candidate_id=candidate_id,
        object_kind=SemanticObjectKind.OFFERING_REF,
        normalized_head=phrase,
        display_label=phrase,
        source_passage_id=packet.passage_key,
        evidence=evidence,
        extraction_model=MODEL,
        prompt_version=prompt_version,
        normalization_status=SemanticObjectNormalizationStatus.NORMALIZED_CANDIDATE,
    )
    assertion = StructuredSemanticAssertion(
        assertion_id=f"V32ASSERT:{candidate_id}",
        source_run_id=run_id,
        subject_id=packet.passage_key,
        predicate=SemanticPredicate.INVOLVES_OFFERING,
        object=candidate,
        evidence=evidence,
        explicitness=Explicitness.EXPLICIT,
    )
    binding = AssertionBinding(
        assertion_id=assertion.assertion_id,
        anchors=[
            BindingAnchor(
                role=BindingRole.RELATION,
                translation_record_id=packet.translation.translation_id,
                start=start,
                end=end,
                text=phrase,
            )
        ],
    )
    return SemanticExtractionV3(mantra_id=packet.citation, assertions=[assertion]), [binding]


def response_bytes(
    task: PreparedTask, payload: SemanticExtractionV3, bindings: list[AssertionBinding]
) -> bytes:
    draft = ModelAuthoredResponse.model_construct(
        receipt=None,  # type: ignore[arg-type]
        semantic_output=payload,
        assertion_bindings=bindings,
    )
    receipt = ModelExecutionReceipt(
        execution_version=task.execution_version,
        run_id=task.run_id,
        task_id=task.task_id,
        passage_id=task.passage_id,
        requested_model=task.model_requested,
        reported_model=task.model_requested,
        reasoning=task.reasoning_requested,
        task_sha256=task.task_sha256,
        prompt_sha256=task.prompt_sha256,
        schema_sha256=task.schema_sha256,
        evidence_packet_sha256=task.evidence_packet_sha256,
        response_sha256=response_payload_sha256(draft),
        attempt_id="attempt_001",
        authored_at=datetime.now(UTC),
    )
    row = ModelAuthoredResponse(
        receipt=receipt, semantic_output=payload, assertion_bindings=bindings
    ).model_dump(mode="json")
    return json.dumps(row, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")


def prepared_v3_2(tmp_path: Path, passage_key: str) -> tuple[EvidencePacket, ExecutionStore, Any]:
    packet = regression_packets()[passage_key]
    store = ExecutionStore(tmp_path)
    task = prepare_task(packet, v3_2_contract())
    store.write_task(task)
    return packet, store, task


# --- V3.1 preservation ----------------------------------------------------------------


def test_the_v3_1_prompt_and_its_frozen_semantic_inputs_are_byte_identical() -> None:
    frozen = regression_manifest()["frozen_hashes"]
    for name, path in V3_1_UNCHANGED_INPUTS.items():
        assert sha256_file(path) == frozen[name], f"{path} drifted from the sealed v3.1 run"
    assert read_prompt_version(PROMPT_PATH_V3_1) == PROMPT_VERSION_V3_1


def test_the_sealed_v3_1_responses_still_validate_under_the_current_code() -> None:
    """Reproducibility is the sealed bytes still passing, not the validator file's hash."""
    contract = RunContract.model_validate_json(
        (REGRESSION / "store" / "run_contract.json").read_text(encoding="utf-8")
    )
    assert contract.prompt_version == PROMPT_VERSION_V3_1
    recorded = regression_manifest()["task_hashes"]
    failures: list[str] = []
    for task_dir in sorted((REGRESSION / "store" / "tasks").iterdir()):
        task = PreparedTask.model_validate_json(
            (task_dir / "task.json").read_text(encoding="utf-8")
        )
        assert task.task_sha256 == recorded[task.passage_id]
        packet = task.evidence_packet
        canonical = frozenset(mention.entity_key for mention in packet.mentions)
        for attempt in sorted((task_dir / "attempts").iterdir()):
            raw = (attempt / "raw_response.json").read_text(encoding="utf-8")
            response = ModelAuthoredResponse.model_validate_json(raw)
            errors = validate_receipt(
                response.receipt,
                task,
                contract,
                computed_response_sha256=response_payload_sha256(response),
            )
            errors += validate_candidate_invariants(
                response.semantic_output, task, prompt_version=contract.prompt_version
            )
            errors += validate_v3_payload(
                response.semantic_output, packet, canonical_entity_ids=canonical
            )
            errors += validate_evidence_anchors(response.semantic_output, packet)
            errors += validate_bindings(
                response.semantic_output, response.assertion_bindings, packet
            )
            failures += [f"{task.task_id}: {message}" for message in errors]
    assert failures == []


def test_a_contract_stored_before_the_policy_field_existed_still_means_v3_1() -> None:
    stored = json.loads((REGRESSION / "store" / "run_contract.json").read_text(encoding="utf-8"))
    stored.pop("prompt_version", None)
    assert RunContract.model_validate(stored).prompt_version == PROMPT_VERSION_V3_1


# --- V3.2 identity --------------------------------------------------------------------


def test_v3_2_is_a_separate_prompt_with_its_own_identity_and_hash() -> None:
    assert PROMPT_PATH_V3_2 != PROMPT_PATH_V3_1
    assert read_prompt_version(PROMPT_PATH_V3_2) == PROMPT_VERSION_V3_2
    assert PROMPT_VERSION_V3_2 != PROMPT_VERSION_V3_1
    assert prompt_sha256(PROMPT_PATH_V3_2) != prompt_sha256(PROMPT_PATH_V3_1)
    assert v3_2_contract().prompt_sha256 == prompt_sha256(PROMPT_PATH_V3_2)
    assert v3_2_contract().prompt_sha256 != regression_manifest()["frozen_hashes"]["prompt_sha256"]


def test_the_v3_2_prompt_states_all_seven_policy_rules() -> None:
    text = prompt_text()
    assert prompt_policy_errors() == []
    titles = [
        "Emit-vs-omit floor",
        "REQUESTS force",
        "REQUESTS outcome splitting",
        "DESCRIBES precedence",
        "DESCRIBES_ACTION scope",
        "Material and ritual co-emission",
        "No-claim criterion",
    ]
    assert [rule.title for rule in POLICY_RULES] == titles
    for number, title in enumerate(titles, start=1):
        assert PolicyRule(number, title).heading in text


def test_the_v3_2_prompt_requires_the_fourteen_family_inspection_in_repo_order() -> None:
    text = prompt_text()
    assert len(PREDICATE_CHECKS) == 14
    positions = [
        text.index(f"{index}. `{family}`") for index, family in enumerate(PREDICATE_CHECKS, 1)
    ]
    assert positions == sorted(positions), "families are not listed in repo-authoritative order"
    assert "Inspect all fourteen allowed families independently" in text
    assert "checklist, not a quota" in text


def test_the_no_claim_criterion_is_explicit() -> None:
    text = prompt_text()
    assert "`no_claim` is permitted only after all fourteen families have been inspected" in text
    assert "Do not return\nno claim because a passage is difficult" in text
    assert "it is not canonical knowledge" in text


def test_the_requests_force_and_splitting_policies_are_explicit() -> None:
    text = prompt_text()
    for marker in ("an imperative,", "an optative,", "a prohibitive wish,", "bestowing"):
        assert marker in text
    assert "Do not automatically take\nthe grammatical object of the request verb" in text
    assert "one `REQUESTS` assertion per independently coordinated desired outcome" in text
    assert "splitting one complex request phrase into\nseveral" in text


def test_describes_precedence_and_describes_action_scope_are_explicit() -> None:
    text = prompt_text()
    assert "entity-level state, quality, property, role, or depiction" in text
    assert "do not add a redundant\n`DESCRIBES`" in text
    assert "only for an action asserted or narrated as occurring" in text
    assert "commanded or wished for is a desired future action and belongs to `REQUESTS`" in text


def test_material_and_ritual_co_emission_requires_independent_evidence() -> None:
    text = prompt_text()
    assert "each relation independently carries direct local evidence" in text
    assert (
        "do not create duplicate assertions merely because the\nword occurs more than once" in text
    )


def test_the_explicitness_policy_is_not_relaxed_by_v3_2() -> None:
    text = prompt_text()
    assert "`INTERPRETIVE` is prohibited" in text
    assert "STRONG_INFERENCE` only when exactly one limited inferential step" in text
    assert "the emission floor in\nRule 1 applies only to relations that already meet it" in text
    assert read_prompt_version(PROMPT_PATH_V3_2) == PROMPT_VERSION_V3_2


# --- anti-overfitting -----------------------------------------------------------------


def test_the_v3_2_prompt_names_no_benchmark_passage_or_citation() -> None:
    selection = load_selection()
    text = prompt_text()
    assert leaked_identifiers(text, selection.passage_ids) == ()
    assert leaked_identifiers(text, selection.citations) == ()
    assert "RV " not in text and "VG:RV:" not in text
    assert "10.58" not in text


def test_the_v3_2_prompt_leaks_no_sealed_answer_wording() -> None:
    """No distinctive phrase either sealed run produced may appear in the policy text."""
    answers: set[str] = set()
    for response in sealed_responses().values():
        for assertion in response.semantic_output.assertions:
            candidate = assertion.object
            answers.update(
                str(value)
                for value in (
                    candidate.normalized_head,
                    candidate.display_label,
                    candidate.event.action_head if candidate.event else None,
                )
                if value
            )
        answers.update(
            anchor.text for binding in response.assertion_bindings for anchor in binding.anchors
        )
    distinctive = {item for item in answers if len(item) >= 10 and " " in item}
    assert distinctive, "the sealed run produced no multi-word answers to check against"
    assert leaked_identifiers(prompt_text(), tuple(sorted(distinctive))) == ()


# --- the validator authorship boundary ------------------------------------------------


def test_preparing_a_v3_2_task_authors_no_semantic_content(tmp_path: Path) -> None:
    packet, _, task = prepared_v3_2(tmp_path, "VG:RV:SAK:M06:S042:V004")
    row = task.model_dump(mode="json")
    assert "prompt_version" not in row, "the task must not gain a field that changes its hash"
    serialised = json.dumps(row, ensure_ascii=False)
    for forbidden in ("predicate", "assertion", "explicitness", "normalized_head", "REQUESTS"):
        assert forbidden not in serialised
    assert task.execution_version == EXECUTION_VERSION_V3_2
    assert task.citation == packet.citation


def test_no_v3_2_semantic_output_exists_without_a_model_authored_response(tmp_path: Path) -> None:
    _, store, _ = prepared_v3_2(tmp_path, "VG:RV:SAK:M06:S042:V004")
    with pytest.raises(FileNotFoundError, match="model-authored response is required"):
        store.import_response(tmp_path / "absent.json", v3_2_contract())


def test_validators_report_errors_and_never_edit_the_payload(tmp_path: Path) -> None:
    packet, _, task = prepared_v3_2(tmp_path, "VG:RV:SAK:M06:S042:V004")
    payload, bindings = offering_payload(
        packet, STABILITY_RUN_A, unique_phrase(packet), prompt_version=PROMPT_VERSION_V3_2
    )
    before = payload.model_dump(mode="json")
    canonical = frozenset(mention.entity_key for mention in packet.mentions)
    validate_v3_payload(payload, packet, canonical_entity_ids=canonical)
    validate_evidence_anchors(payload, packet)
    validate_bindings(payload, [], packet)
    validate_candidate_invariants(payload, task, prompt_version=PROMPT_VERSION_V3_2)
    assert payload.model_dump(mode="json") == before
    assert "no assertion-specific binding evidence" in "; ".join(
        validate_bindings(payload, [], packet)
    )
    assert validate_bindings(payload, bindings, packet) == []


def test_a_v3_2_run_imports_a_model_authored_response_and_refuses_a_v3_1_object(
    tmp_path: Path,
) -> None:
    packet, store, task = prepared_v3_2(tmp_path, "VG:RV:SAK:M06:S042:V004")
    phrase = unique_phrase(packet)
    payload, bindings = offering_payload(
        packet, STABILITY_RUN_A, phrase, prompt_version=PROMPT_VERSION_V3_2
    )
    path = tmp_path / "response.json"
    path.write_bytes(response_bytes(task, payload, bindings))
    validated = store.import_response(path, v3_2_contract())
    assert validated.payload.assertions[0].object.prompt_version == PROMPT_VERSION_V3_2

    stale, stale_bindings = offering_payload(
        packet, STABILITY_RUN_A, phrase, prompt_version=PROMPT_VERSION_V3_1
    )
    errors = validate_candidate_invariants(stale, task, prompt_version=PROMPT_VERSION_V3_2)
    assert any("object prompt version differs from the run" in item for item in errors)
    assert validate_candidate_invariants(stale, task, prompt_version=PROMPT_VERSION_V3_1) == []
    assert stale_bindings[0].assertion_id == stale.assertions[0].assertion_id


def test_the_heuristic_baseline_cannot_enter_v3_2_custody(tmp_path: Path) -> None:
    packet, _, task = prepared_v3_2(tmp_path, "VG:RV:SAK:M06:S042:V004")
    payload, _ = extract_packet(packet, run_id=STABILITY_RUN_A)
    models = {item.object.extraction_model for item in payload.assertions}
    models |= {item.extraction_model for item in payload.ontology_gaps}
    assert models <= {BASELINE_PROVENANCE}
    errors = validate_candidate_invariants(payload, task, prompt_version=PROMPT_VERSION_V3_2)
    assert any("claims model 'DETERMINISTIC_HEURISTIC_BASELINE'" in item for item in errors)
    assert any("object prompt version differs from the run" in item for item in errors)


def test_v3_2_output_stays_candidate_only_and_unlocks_no_predicate(tmp_path: Path) -> None:
    packet, _, task = prepared_v3_2(tmp_path, "VG:RV:SAK:M06:S042:V004")
    payload, _ = offering_payload(
        packet, STABILITY_RUN_A, unique_phrase(packet), prompt_version=PROMPT_VERSION_V3_2
    )
    row = payload.model_dump(mode="json")
    assert row["prompt_version"] == PROMPT_VERSION_V3_1, "the payload schema version is unchanged"
    assert row["object_schema_version"] == "rigveda-semantic-object-v1"
    assert "unlocked_predicates" not in row
    assert "`unlocked_predicates` remains empty" in prompt_text()
    assert {item.predicate.value for item in payload.assertions} <= set(PREDICATE_CHECKS)
    assert all(item.explicitness is Explicitness.EXPLICIT for item in payload.assertions)
    assert task.run_id == STABILITY_RUN_A


# --- the two-run experiment -----------------------------------------------------------


def test_the_experiment_resolves_the_same_sixty_passages_as_the_sealed_selection() -> None:
    experiment = build_stability_experiment()
    selection = experiment.selection
    assert len(selection.passage_ids) == 60
    assert set(selection.passage_ids) == set(regression_manifest()["packet_hashes"])
    assert selection.selection_hash == regression_manifest()["selection_hash"]


def test_run_a_and_run_b_differ_only_in_identity() -> None:
    experiment = build_stability_experiment()
    assert experiment.run_ids == (STABILITY_RUN_A, STABILITY_RUN_B)
    assert experiment.run_a.run_id != experiment.run_b.run_id
    assert experiment.contract_differences() == []
    for contract in (experiment.run_a, experiment.run_b):
        assert contract.model_requested == MODEL == "gpt-5.6-luna"
        assert contract.reasoning_requested == REASONING == "high"
        assert contract.prompt_version == PROMPT_VERSION_V3_2
        assert contract.execution_version == EXECUTION_VERSION_V3_2
    assert RUNTIME == "CODEX_DIRECT"
    a_tasks = experiment.task_ids(STABILITY_RUN_A)
    b_tasks = experiment.task_ids(STABILITY_RUN_B)
    assert set(a_tasks) == set(b_tasks) == set(experiment.selection.passage_ids)
    assert set(a_tasks.values()).isdisjoint(b_tasks.values())


def test_the_experiment_refuses_a_run_id_it_does_not_define() -> None:
    with pytest.raises(ValueError, match="is not a run of this experiment"):
        build_stability_experiment().task_ids("some-other-run")


# --- regime diagnostics ---------------------------------------------------------------


def regime(assertions: int, no_claim: int, counts: dict[str, int]) -> EmissionRegime:
    return EmissionRegime(
        passages=60, assertions=assertions, no_claim_passages=no_claim, predicate_counts=counts
    )


def comparable(predicate: str, entity: str | None = None) -> ComparableAssertion:
    return ComparableAssertion(
        assertion_id=f"A:{predicate}:{entity}",
        predicate=predicate,
        object_kind="CANONICAL_ENTITY_REF" if entity else "OFFERING_REF",
        normalized_head=None if entity else "offerings",
        canonical_entity_id=entity,
        qualifiers=(),
        beneficiary_entity_id=None,
        target_entity_id=None,
        event_action_head=None,
        event_actor_entity_id=None,
        event_patient_entity_id=None,
        event_participants=(),
        evidence_references=("PASSAGE:P",),
        binding_anchors=(("RELATION", "text", 0, 4),),
    )


def test_run_level_metrics_are_derived_from_what_a_run_actually_emitted() -> None:
    outcomes = {
        "P1": PassageOutcome(False, (comparable("PRAISES", "VG:DEVATA:AGNIH"),)),
        "P2": PassageOutcome(False, (comparable("INVOLVES_OFFERING"), comparable("REQUESTS"))),
        "P3": PassageOutcome(True),
        "P4": PassageOutcome(True),
    }
    derived = emission_regime(outcomes)
    assert derived.passages == 4
    assert derived.assertions == 3
    assert derived.no_claim_passages == 2
    assert derived.no_claim_rate == pytest.approx(0.5)
    assert derived.density == pytest.approx(0.75)
    assert derived.predicate_counts == {"PRAISES": 1, "INVOLVES_OFFERING": 1, "REQUESTS": 1}
    assert derived.object_kind_counts == {"CANONICAL_ENTITY_REF": 1, "OFFERING_REF": 2}
    assert derived.canonical_reference_count == 1
    assert derived.share_of("REQUESTS") == pytest.approx(1 / 3)

    sparse = emission_regime({key: PassageOutcome(True) for key in outcomes})
    comparison = compare_regimes(derived, sparse)
    assert comparison.canonical_reference_counts == (1, 0)
    assert comparison.object_kind_counts == {
        "CANONICAL_ENTITY_REF": (1, 0),
        "OFFERING_REF": (2, 0),
    }


def test_regime_comparison_separates_a_distribution_split_from_a_contradiction() -> None:
    """The observed v3.1 split is a run-level difference with no contradictory target."""
    observed = compare_regimes(
        regime(57, 10, {"DESCRIBES_ACTION": 21, "REQUESTS": 21, "DESCRIBES": 15}),
        regime(33, 38, {"DESCRIBES_ACTION": 0, "REQUESTS": 15, "DESCRIBES": 18}),
    )
    assert observed.no_claim_rate_gap == pytest.approx(0.4666, abs=1e-3)
    assert observed.density_gap == pytest.approx(0.4, abs=1e-9)
    assert observed.one_sided_predicates == ("DESCRIBES_ACTION",)
    assert observed.skew_probabilities["DESCRIBES_ACTION"] < 1e-5
    assert observed.predicate_presence_jaccard == pytest.approx(2 / 3)

    same_target = {"P": PassageOutcome(False, (comparable("DESCRIBES", "VG:DEVATA:AGNIH"),))}
    other_target = {"P": PassageOutcome(False, (comparable("DESCRIBES", "VG:DEVATA:INDRAH"),))}
    assert canonical_target_contradictions(same_target, same_target) == ()
    assert canonical_target_contradictions(same_target, other_target) == ("P",)

    agreement = passage_agreement(same_target, other_target)
    assert agreement.passages == 1
    assert agreement.no_claim == 1
    assert agreement.predicate_presence == 1
    assert agreement.canonical_entity == 0
    assert agreement.exact_assertion_set == 0


def test_passage_agreement_refuses_a_different_passage_set() -> None:
    left = {"P": PassageOutcome(True)}
    with pytest.raises(ValueError, match="same passages"):
        passage_agreement(left, {"Q": PassageOutcome(True)})


def test_a_supported_omission_is_not_an_unsupported_extraction() -> None:
    omission = OneSidedAssessment.SUPPORTED_OMISSION_VARIANCE
    unsupported = OneSidedAssessment.UNSUPPORTED_EXTRACTION
    assert diagnostic_set_for(AlignmentCategory.A_ONLY, omission) is DiagnosticSet.ONE_RUN_SUPPORTED
    assert (
        diagnostic_set_for(AlignmentCategory.A_ONLY, unsupported) is DiagnosticSet.SUSPECT_ASSERTION
    )
    assert severity_v2(AlignmentCategory.A_ONLY, one_sided=omission) is SeverityV2.MEDIUM
    assert severity_v2(AlignmentCategory.A_ONLY, one_sided=unsupported) is SeverityV2.HIGH
    assert severity_v2(AlignmentCategory.EXACT_ASSERTION, canonical_contradiction=True) is (
        SeverityV2.CRITICAL
    )


def test_no_diagnostic_group_is_promoted_to_canonical_knowledge() -> None:
    for group in DiagnosticSet:
        provenance, status = candidate_provenance_label(group)
        assert status == "CANDIDATE_NEEDS_REVIEW"
        assert "CANONICAL" not in provenance
    assert regression_manifest()["canonical_promotion"] is False
    assert regression_manifest()["human_gold_status"] == "UNANNOTATED"
    assert regression_manifest()["unlocked_predicates"] == []


# --- provenance and the gate ----------------------------------------------------------


def test_every_validated_result_stays_traceable_to_its_run_and_batch(tmp_path: Path) -> None:
    packet, store, task = prepared_v3_2(tmp_path, "VG:RV:SAK:M06:S042:V004")
    payload, bindings = offering_payload(
        packet, STABILITY_RUN_A, unique_phrase(packet), prompt_version=PROMPT_VERSION_V3_2
    )
    path = tmp_path / "response.json"
    path.write_bytes(response_bytes(task, payload, bindings))
    contract = v3_2_contract()
    validated = store.import_response(path, contract)
    record = ExtractionProvenance.from_validated(validated, contract, batch_id="batch_0001")
    assert record.incomplete_fields() == ()
    assert record.run_id == STABILITY_RUN_A
    assert record.task_id == task.task_id
    assert record.attempt_id == "attempt_001"
    assert record.passage_id == packet.passage_key
    assert record.prompt_version == PROMPT_VERSION_V3_2
    assert record.prompt_sha256 == prompt_sha256(PROMPT_PATH_V3_2)
    assert record.evidence_packet_sha256 == packet.input_sha256
    assert record.batch_id == "batch_0001"
    assert ExtractionProvenance.from_validated(validated, contract).batch_id is None


def test_the_stability_threshold_is_configurable_and_labelled_engineering_only() -> None:
    defaults = StabilityThresholds()
    assert defaults.provenance == "engineering_default_not_truth_derived"
    assert defaults.no_claim_rate_gap == NO_CLAIM_RATE_GAP_ENGINEERING_DEFAULT == 0.2
    assert NO_CLAIM_RATE_GAP_PROVENANCE == "engineering_default_not_truth_derived"
    loosened = StabilityThresholds(no_claim_rate_gap=0.9, assertion_density_gap=0.9)
    split = compare_regimes(
        regime(57, 10, {"REQUESTS": 21}),
        regime(33, 38, {"REQUESTS": 15}),
    )
    assert stability_gate(split).passed is False
    assert stability_gate(split, thresholds=loosened).passed is True


def test_the_gate_fails_the_observed_v3_1_regime_split_and_passes_local_variance() -> None:
    observed = compare_regimes(
        regime(57, 10, {"DESCRIBES_ACTION": 21, "REQUESTS": 21}),
        regime(33, 38, {"DESCRIBES_ACTION": 0, "REQUESTS": 15}),
    )
    failed = stability_gate(observed)
    assert failed.passed is False
    assert failed.claim == "POLICY_STABILITY_ONLY_NOT_ACCURACY"
    joined = " ".join(failed.failures)
    assert "no-claim regime split" in joined
    assert "assertion density split" in joined
    assert "one-sided predicate DESCRIBES_ACTION" in joined

    tolerable = compare_regimes(
        regime(55, 11, {"DESCRIBES_ACTION": 20, "REQUESTS": 20}),
        regime(52, 13, {"DESCRIBES_ACTION": 18, "REQUESTS": 21}),
    )
    assert stability_gate(tolerable).passed is True, "local variance must not fail the gate"
    assert stability_gate(tolerable, IntegrityCounts(binding_failures=1)).passed is False
    assert stability_gate(
        tolerable, IntegrityCounts(canonical_target_contradictions=1)
    ).failures == ("integrity: canonical_target_contradictions",)


def test_a_passing_gate_is_a_stability_result_and_not_an_accuracy_result() -> None:
    clean = compare_regimes(regime(10, 0, {"REQUESTS": 10}), regime(10, 0, {"REQUESTS": 10}))
    result = stability_gate(clean)
    assert result.passed is True
    assert result.failures == ()
    assert result.claim == "POLICY_STABILITY_ONLY_NOT_ACCURACY"
    assert result.thresholds.provenance == "engineering_default_not_truth_derived"
    # Two identical runs still say nothing about correctness: there is no gold to score.
    assert regression_manifest()["human_gold_status"] == "UNANNOTATED"
