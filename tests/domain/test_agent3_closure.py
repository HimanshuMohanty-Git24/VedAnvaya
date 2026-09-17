"""Agent 3's closure contracts -- morphology and semantic roles.

Offline. Nothing here reads Neo4j; every assertion is against a generator's rules or a
staged artifact, so the suite states what the pipeline must do rather than what the database
happens to hold today.

Each contract is tested as a pair: an input that must be refused, and one that must be
accepted. The refusal half is load-bearing -- a generator that cannot fail is a generator
whose output nobody can trust.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from build_domain_entity_domains import (
    CURATED_DOMAINS,
    DOMAINS,
    LABEL_DOMAINS,
    assign,
)
from build_lexical_nonresolution_reasons import (
    LEMMA_REASON,
    NONRESOLUTION_REASONS,
    WORKFLOW_REASON,
    type_rows,
)
from build_semantic_assertion_delta import assertion_key
from build_semantic_review_frame import REVIEW_STATES, validate_transition

STAGING = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "staging"
    / "final_closure_sprint"
    / "agent3"
)


def _rows(name: str) -> list[dict]:
    path = STAGING / name
    if not path.exists():
        pytest.skip(f"{name} not staged in this checkout")
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


# --------------------------------------------------------------------------------------
# GAP-SEMANTICS-005 -- the domain vocabulary is closed and multi-domain is representable
# --------------------------------------------------------------------------------------


def test_an_entity_no_rule_reaches_is_refused_rather_than_given_an_empty_list() -> None:
    """BAD -> FAIL. An empty domain list is indistinguishable from 'we never looked',
    which is the exact null this gap is about."""
    with pytest.raises(ValueError, match="resolves to no domain"):
        assign("VG:CONCEPT:NOT-A-REAL-ENTITY", ["Unmapped"], None)


def test_a_labelled_entity_resolves_deterministically() -> None:
    """GOOD -> PASS."""
    row = assign("VG:CONCEPT:SOMETHING", ["Ritual"], "ritual")
    assert row["domain"] == ["RITUAL"]
    assert row["domain_provenance"] == "deterministic"


def test_a_multi_domain_entity_carries_every_applicable_domain() -> None:
    """The closure test's second clause, verbatim: 'multi-domain entities carrying every
    applicable domain rather than one'."""
    row = assign("VG:CONCEPT:SOMA-LIKE", ["Plant", "Substance", "Offering"], "ritual")
    assert set(row["domain"]) == {"BIOTIC", "MATERIAL", "RITUAL"}
    assert row["domain_count"] == 3


def test_the_vocabulary_is_closed_on_both_sides() -> None:
    """Every rule and every curated assignment names a domain the vocabulary declares."""
    for label, domains in LABEL_DOMAINS.items():
        assert set(domains) <= set(DOMAINS), f"{label} names a domain outside the vocabulary"
    for key, domains in CURATED_DOMAINS.items():
        assert set(domains) <= set(DOMAINS), f"{key} names a domain outside the vocabulary"


def test_a_curated_assignment_is_never_typed_as_human_annotation() -> None:
    """The single most important rule for this agent, asserted as code.

    A curated domain was read off an English gloss by a model. It is ``model-assisted``.
    It is not, and may never be reported as, human annotation.
    """
    row = assign("VG:CONCEPT:KAMA-DESIRE", [], None)
    assert row["domain_provenance"] == "model-assisted"
    assert row["domain_is_human_annotation"] is False
    assert "human" not in row["domain_provenance"]


def test_staged_domain_rows_leave_no_entity_null() -> None:
    rows = _rows("domain_entity_domains.jsonl")
    assert rows, "the artifact is empty"
    assert all(row["domain"] for row in rows)
    assert all(row["domain_is_human_annotation"] is False for row in rows)
    assert not [d for row in rows for d in row["domain"] if d not in DOMAINS]


# --------------------------------------------------------------------------------------
# GAP-MORPHOLOGY-004 -- a workflow state is not a linguistic reason
# --------------------------------------------------------------------------------------


def test_a_lemma_with_no_typed_reason_is_refused() -> None:
    """BAD -> FAIL. Letting it through would leave the token carrying a queue state, which
    is what the gap is about."""
    row = {
        "token_key": "VG:TOKEN:X",
        "passage_key": "VG:RV:SAK:M01:S001:V001",
        "lemma": "not-a-registered-lemma-",
        "surface": "x",
        "candidate_entity_keys": [],
        "reason": WORKFLOW_REASON,
    }
    with pytest.raises(ValueError, match="no typed non-resolution reason"):
        type_rows([row], {})


def test_a_registered_lemma_gets_its_typed_reason() -> None:
    """GOOD -> PASS."""
    row = {
        "token_key": "VG:TOKEN:Y",
        "passage_key": "VG:RV:SAK:M01:S008:V007",
        "lemma": "áp-",
        "surface": "ā́paḥ",
        "candidate_entity_keys": ["VG:DEVATA:APAH"],
        "reason": WORKFLOW_REASON,
    }
    typed = type_rows([row], {"VG:RV:SAK:M01:S008:V007": {"VG:DEVATA:APAH"}})
    assert typed[0]["nonresolution_reason"] == "LEXEME_COVERS_DEITY_AND_APPELLATIVE"
    assert typed[0]["anukramani_corroborated"] is True
    # Corroborated and still no edge. Fail-closed on ambiguity is the layer's own policy.
    assert typed[0]["edge_created"] is False


def test_every_typed_reason_is_in_the_closed_vocabulary() -> None:
    assert set(LEMMA_REASON.values()) <= set(NONRESOLUTION_REASONS)


def test_no_typed_reason_merely_restates_the_queue_state() -> None:
    """A reason that says 'not reviewed' explains nothing. Guarded so a later edit cannot
    quietly reintroduce one."""
    for name, text in NONRESOLUTION_REASONS.items():
        assert "not reviewed" not in text.lower()
        assert "ACCEPTED" not in name


def test_staged_lexical_rows_all_carry_a_linguistic_reason() -> None:
    rows = _rows("lexical_nonresolution_typed.jsonl")
    assert len(rows) == 711
    assert all(row["nonresolution_reason"] in NONRESOLUTION_REASONS for row in rows)
    assert all(row["edge_created"] is False for row in rows)


# --------------------------------------------------------------------------------------
# GAP-SEMANTICS-003 -- the role edge must resolve to an assertion, not to a passage
# --------------------------------------------------------------------------------------


def test_the_assertion_key_is_the_prefix_of_the_role_filler_key() -> None:
    """The key is read back out of a key the artifact already ships, never invented.

    BAD -> FAIL if the minting drifts: a role filler key whose assertion segment does not
    match is exactly how 2,052 edges came to hang off a passage instead.
    """
    filler_key = "VG:AV:SAU:K01:S001:V001:A001:R01"
    minted = assertion_key("VG:AV:SAU:K01:S001:V001", 1)
    assert filler_key.startswith(minted + ":")
    assert minted == "VG:AV:SAU:K01:S001:V001:A001"


def test_a_mismatched_ordinal_does_not_produce_the_filler_prefix() -> None:
    """BAD -> FAIL."""
    filler_key = "VG:AV:SAU:K01:S001:V001:A001:R01"
    assert not filler_key.startswith(assertion_key("VG:AV:SAU:K01:S001:V001", 2) + ":")


def test_staged_role_edges_all_start_at_an_assertion_not_a_passage() -> None:
    edges = _rows("assertion_role_edges.jsonl")
    assertions = {row["assertion_key"] for row in _rows("semantic_assertions.jsonl")}
    assert edges
    assert all(edge["assertion_key"] in assertions for edge in edges)
    # An assertion key always ends in the :Annn segment; a bare passage key never does, so
    # this is what distinguishes an edge anchored on the assertion from one anchored on the
    # passage -- the defect that put all 2,052 live edges on the wrong endpoint.
    tails = {edge["assertion_key"].rsplit(":", 1)[-1] for edge in edges}
    assert all(tail.startswith("A") and tail[1:].isdigit() for tail in tails)


def test_the_staged_layer_reaches_a_non_rigvedic_corpus_and_completes_a_triple() -> None:
    rows = _rows("semantic_assertions.jsonl")
    vedas = {row["veda"] for row in rows}
    assert vedas - {"RV"}, "GAP-SEMANTICS-001 needs a non-Rigvedic corpus"
    assert sum(1 for row in rows if row["three_slot_complete"]) > 0
    # The five instruments must stay apart. A single blended figure is the failure mode.
    assert len({row["role_derivation"] for row in rows}) > 1


def test_the_assertion_role_signature_matches_the_migration_card() -> None:
    """Pin ASSERTION_ROLE's endpoints to what migration card M1 declared.

    This pin exists because the signature had already drifted once. M1 declares
    ``(:SemanticAssertion)-[:ASSERTION_ROLE]->(:RoleFiller)``; the Wave 3 importer wrote
    ``start_label="Passage"`` and the signature was later written to match the defective
    import instead of the card, so live conformance to M1's own migration test was 0 of
    2,052.

    BAD -> FAIL if the subject is widened back to Passage or Mantra.
    """
    from vedagraph.domain.ontology import all_endpoint_signatures

    subject, obj = all_endpoint_signatures()["ASSERTION_ROLE"]
    assert subject == frozenset({"SemanticAssertion"})
    assert obj == frozenset({"RoleFiller"})
    assert "Passage" not in subject and "Mantra" not in subject


def test_the_card_still_declares_the_endpoints_the_signature_is_pinned_to() -> None:
    """Read the card, not a memory of it. If M1 is ever revised, this fails first."""
    card = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "reports"
        / "data-completeness"
        / "SCHEMA_MIGRATION_CARDS.md"
    ).read_text(encoding="utf-8")
    assert "(:SemanticAssertion)-[:ASSERTION_ROLE]->(:RoleFiller)" in card


def test_every_staged_role_edge_resolves_to_exactly_one_assertion() -> None:
    """M1's own migration test, run against the staged delta. Live it measures 0 of 2,052."""
    edges = _rows("assertion_role_edges.jsonl")
    assertions = {row["assertion_key"] for row in _rows("semantic_assertions.jsonl")}
    per_filler: dict[str, set[str]] = {}
    for edge in edges:
        per_filler.setdefault(edge["role_filler_key"], set()).add(edge["assertion_key"])
    assert per_filler
    assert all(len(keys) == 1 for keys in per_filler.values())
    assert all(next(iter(keys)) in assertions for keys in per_filler.values())


# --------------------------------------------------------------------------------------
# LEAD RULING 1 -- a cross-Veda projected assertion must name its source verse
# --------------------------------------------------------------------------------------


def test_a_projected_assertion_with_no_source_verse_is_refused() -> None:
    """BAD -> FAIL. A transferred analysis with no address is not auditable."""
    from build_semantic_assertion_delta import _projection_fields

    with pytest.raises(ValueError, match="names no source verse"):
        _projection_fields(
            {"canonical_key": "VG:SV:KAU:ARANYA:D02:V01"},
            {},
            {"derivation": "CROSS_VEDA_TEXT_IDENTITY"},
            {},
        )


def test_a_projected_assertion_whose_pair_has_no_parallel_edge_is_refused() -> None:
    """BAD -> FAIL. The ruling's condition is that the identity rests on evidence already
    in the graph; a pair with no edge does not meet it."""
    from build_semantic_assertion_delta import _projection_fields

    with pytest.raises(ValueError, match="carries no parallel edge"):
        _projection_fields(
            {"canonical_key": "VG:SV:X"},
            {"projected_from": "VG:RV:Y"},
            {"derivation": "CROSS_VEDA_TEXT_IDENTITY"},
            {},
        )


def test_a_backed_projection_records_the_source_verse_and_the_whole_edge_set() -> None:
    """GOOD -> PASS. The single-valued artifact claim is kept beside the live set rather
    than silently replaced by it."""
    from build_semantic_assertion_delta import _projection_fields

    fields = _projection_fields(
        {"canonical_key": "VG:SV:A"},
        {
            "projected_from": "VG:RV:B",
            "projection_relationship_in_graph": "VARIANT_OF",
            "projection_graph_score": 1.0,
        },
        {"derivation": "CROSS_VEDA_TEXT_IDENTITY"},
        {("VG:SV:A", "VG:RV:B"): ["REUSES_TEXT_FROM", "VARIANT_OF"]},
    )
    assert fields["projected_from_canonical_key"] == "VG:RV:B"
    assert fields["projection_edge_types"] == ["REUSES_TEXT_FROM", "VARIANT_OF"]
    assert fields["projection_relationship_claimed_by_artifact"] == "VARIANT_OF"
    assert fields["is_samavedic_annotation"] is False


def test_a_near_parallel_pair_is_refused_from_the_import_rows() -> None:
    """BAD -> FAIL. Near is not exact, and a transferred morphological analysis on a near
    pair gives a differing word the analysis of the word it differs from."""
    from build_semantic_assertion_delta import _projection_fields

    with pytest.raises(ValueError, match="GRAPH_TYPES_PAIR_NEAR_PARALLEL_NOT_EXACT"):
        _projection_fields(
            {"canonical_key": "VG:SV:A"},
            {"projected_from": "VG:RV:B"},
            {"derivation": "CROSS_VEDA_TEXT_IDENTITY"},
            {("VG:SV:A", "VG:RV:B"): ["NEAR_PARALLEL_OF", "REUSES_TEXT_FROM"]},
        )


def test_the_withholding_rule_names_near_parallel_and_nothing_stronger() -> None:
    """GOOD -> PASS on the types that stay importable; refusal on the one that does not.

    A REUSES_TEXT_FROM + VARIANT_OF pair is still importable: VARIANT_OF is a weaker
    corroborator, not a contradiction of identity the way NEAR_PARALLEL_OF is.
    """
    from build_semantic_assertion_delta import projection_withholding_reason

    assert projection_withholding_reason(["NEAR_PARALLEL_OF", "REUSES_TEXT_FROM"]) == (
        "GRAPH_TYPES_PAIR_NEAR_PARALLEL_NOT_EXACT"
    )
    assert projection_withholding_reason(["REUSES_TEXT_FROM", "VARIANT_OF"]) is None
    assert projection_withholding_reason(["EXACT_PARALLEL_OF", "REUSES_TEXT_FROM"]) is None


def test_no_withheld_pair_reached_the_import_rows() -> None:
    """The routing and the guard must agree. If they ever disagree, the guard raises during
    the build; this asserts the outcome from the other side."""
    rows = _rows("semantic_assertions.jsonl")
    assert not [r for r in rows if "NEAR_PARALLEL_OF" in (r.get("projection_edge_types") or [])]


def test_the_withheld_rows_are_kept_not_deleted() -> None:
    """A bounded evidenced queue, the same shape as the 79 corroborated lexical tokens."""
    withheld = _rows("semantic_assertions_withheld.jsonl")
    assert len(withheld) == 8
    assert len({r["canonical_key"] for r in withheld}) == 5
    assert all(r["withheld_reason"] == "GRAPH_TYPES_PAIR_NEAR_PARALLEL_NOT_EXACT" for r in withheld)
    assert all("NEAR_PARALLEL_OF" in r["projection_edge_types"] for r in withheld)
    assert all(r["deleted"] is False for r in withheld)
    # Each carries its source verse, so the refusal is addressable rather than an absence.
    assert all(r["projected_from_canonical_key"].startswith("VG:RV:") for r in withheld)


def test_the_artifacts_own_score_agrees_with_the_graphs_typing() -> None:
    """Every withheld pair scores below 1.0 on the artifact's own containment figure.

    Independent of the graph typing that triggered the withholding: the projection was
    asserting letter identity on five pairs its own score already said were not identical.
    """
    withheld = _rows("semantic_assertions_withheld.jsonl")
    assert all(r["projection_graph_score"] < 1.0 for r in withheld)
    kept = [
        r
        for r in _rows("semantic_assertions.jsonl")
        if r.get("derivation") == "CROSS_VEDA_TEXT_IDENTITY"
    ]
    assert kept and all(r["projection_graph_score"] == 1.0 for r in kept)


def test_a_non_projected_assertion_gets_no_projection_fields() -> None:
    """A Rigvedic row inherits nothing and must not carry an empty source verse."""
    from build_semantic_assertion_delta import _projection_fields

    assert _projection_fields({}, {}, {"derivation": "MORPHOLOGY_RULE_PREDICATE_ONLY"}, {}) == {}


def test_every_staged_samavedic_row_names_its_rigvedic_source() -> None:
    rows = [r for r in _rows("semantic_assertions.jsonl") if r["veda"] == "SV"]
    # 364, not 372: the 8 assertions on the 5 NEAR_PARALLEL_OF pairs are withheld.
    assert len(rows) == 364
    assert len({r["canonical_key"] for r in rows}) == 211
    assert all(r["projected_from_canonical_key"].startswith("VG:RV:") for r in rows)
    assert all(r["projection_edge_types"] for r in rows)
    # The ruling's basis: every pair rests on a pre-existing edge, not on a staged fold.
    assert all("REUSES_TEXT_FROM" in r["projection_edge_types"] for r in rows)
    # The disclosure the lead asked to keep verbatim. Membership, not equality: 50 of the
    # 364 carry this caution AND a further one -- FIRST_PERSON_AGENT_IS_THE_UNNAMED_SPEAKER,
    # POLARITY_NOT_MODELLED_NEGATION_PARTICLE_IN_SCOPE, FRAME_MAY_INVERT_NONACTIVE_VOICE.
    # Asserting equality would have deleted real disclosure to satisfy a test.
    #
    # Still 50 after the NEAR_PARALLEL_OF withholding, not 49: all 8 withheld rows carried
    # exactly one caution, so the withholding removed none of the doubly-flagged rows. That
    # was measured after the count failed against a guessed 49 -- the guess was wrong and
    # the artifact was right.
    required = "ANALYSIS_IS_OF_A_LETTER_IDENTICAL_RIGVEDIC_VERSE_NOT_OF_A_SAMAVEDIC_ANNOTATION"
    assert all(required in r["cautions"] for r in rows)
    assert sum(len(r["cautions"]) > 1 for r in rows) == 50
    assert all(r["human_annotated"] is False and r["model_assisted"] is False for r in rows)
    assert all(r["provenance"] == "deterministic" for r in rows)
    assert all(r["roles_withheld"] is True and r["roles_withheld_reason"] for r in rows)


def test_the_manifest_carries_the_zero_token_yield_beside_the_sv_assertion_count() -> None:
    """The two figures travel together or the true one becomes the misleading one."""
    path = STAGING / "semantic_assertion_delta_manifest.json"
    if not path.exists():
        pytest.skip("delta manifest not staged in this checkout")
    block = json.loads(path.read_text(encoding="utf-8"))["samaveda_standing_constraint"]
    assert block["sv_assertions"] == 364
    assert block["sv_verses_with_an_assertion"] == 211
    assert block["sv_morphological_tokens_analysed"] == 0
    # The pre-withholding figures stay on the row so the change is visible, not silent.
    assert block["sv_assertions_before_the_near_parallel_withholding"] == 372
    assert block["sv_verses_before_the_near_parallel_withholding"] == 216


def test_the_manifest_states_the_post_import_unreviewed_population() -> None:
    """LEAD CORRECTION 3. The live 4,865 is a pre-import figure."""
    path = STAGING / "semantic_assertion_delta_manifest.json"
    if not path.exists():
        pytest.skip("delta manifest not staged in this checkout")
    block = json.loads(path.read_text(encoding="utf-8"))["closure_measures_after_import"][
        "GAP-SEMANTICS-002"
    ]
    assert block["unreviewed_after_import"] == (
        block["live_unreviewed_before"] + block["staged_assertions_all_unreviewed"]
    )
    assert block["unreviewed_after_import"] > block["live_unreviewed_before"]
    assert block["closes"] is False


# --------------------------------------------------------------------------------------
# GAP-SEMANTICS-002 -- the harness refuses to call a model a human
# --------------------------------------------------------------------------------------


def test_a_model_may_not_write_a_human_reviewed_state() -> None:
    """BAD -> FAIL. This is the one failure that would make every later figure a lie."""
    with pytest.raises(ValueError):
        validate_transition(
            "HUMAN_REVIEWED",
            {"reviewer_kind": "model", "reviewer_id": "claude-opus-5", "reviewed_at": "now"},
        )


def test_a_human_review_record_with_a_named_reviewer_is_accepted() -> None:
    """GOOD -> PASS."""
    validate_transition(
        "HUMAN_REVIEWED",
        {"reviewer_kind": "human", "reviewer_id": "a-named-person", "reviewed_at": "now"},
    )


def test_a_model_adjudication_must_name_its_model() -> None:
    with pytest.raises(ValueError, match="requires model_id"):
        validate_transition("MODEL_ADJUDICATED", {"reviewer_kind": "model", "reviewed_at": "now"})
    validate_transition(
        "MODEL_ADJUDICATED",
        {"reviewer_kind": "model", "model_id": "claude-opus-5", "reviewed_at": "now"},
    )


def test_an_unknown_review_state_is_refused() -> None:
    with pytest.raises(ValueError, match="the vocabulary is closed"):
        validate_transition("LOOKED_AT_BRIEFLY", {})


def test_exactly_one_review_state_counts_as_human_review() -> None:
    human = [name for name, spec in REVIEW_STATES.items() if spec["counts_as_human_review"]]
    assert human == ["HUMAN_REVIEWED"]


def test_the_review_frame_writes_nothing_to_a_reviewed_state() -> None:
    rows = _rows("semantic_review_frame.jsonl")
    assert rows
    assert all(row["review_state"] == "UNREVIEWED" for row in rows)
    assert all(row["reviewer_id"] is None for row in rows)


# --------------------------------------------------------------------------------------
# GAP-MORPHOLOGY-001 -- two figures, never one
# --------------------------------------------------------------------------------------


def test_the_lemma_manifest_states_both_coverage_figures() -> None:
    path = STAGING / "mentions_lemma_manifest.json"
    if not path.exists():
        pytest.skip("lemma projection not staged in this checkout")
    contract = json.loads(path.read_text(encoding="utf-8"))["lemma_coverage_surface_contract"]
    assert contract["distinct_lemmas_reached_after"] > contract["distinct_lemmas_reached_before"]
    assert "mantras_reached_after" in contract
    # The two must differ, or the surface could report one and be read as the other -- which
    # is exactly how "Lemma: RV 6,560" concealed a reach of 39.
    assert contract["distinct_lemmas_reached_after"] != contract["mantras_reached_after"]
