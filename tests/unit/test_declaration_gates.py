"""Proof that the declaration gates can fail. Owner round four, Phase A and C.

Two gates shipped green while measuring nothing:

* the undeclared-relationship-type gate computed
  ``declared = ontology | every type found in the graph`` and then asked which graph types
  were missing from ``declared``. Nothing can be. It reported 0 for a whole wave while
  eleven predicates went unclassified.
* six node labels were declared by no authoritative source, and 2,568 of them --
  ``:QualityVerdict``, this repository's assessment of its own passages -- were the
  fourth-largest node type in the public world export, because "public" is measured as
  ``NOT n:Internal`` and nothing had marked them.

A green result from a structurally vacuous gate is not evidence, so these tests are written
to prove failure rather than to confirm success. Each one takes something away and asserts
the gate notices.

The governing rule, and the reason both defects were possible: **no gate may derive its
allowed universe from the data it is supposed to validate.**
"""

from __future__ import annotations

import importlib

import pytest

from vedagraph.domain.ontology import (
    CAMPAIGN_RELATIONSHIP_TYPES,
    CORPUS_AND_CAMPAIGN_SIGNATURES,
    CORPUS_RELATIONSHIP_TYPES,
    DOMAIN_RELATIONSHIP_TYPES,
    INTERNAL_LABELS,
    PRODUCT_LABELS,
    RELATIONSHIP_SIGNATURES,
    SYSTEM_RELATIONSHIP_TYPES,
    all_declared_relationship_types,
)

scorecard = importlib.import_module("scripts.graph_quality_scorecard")


# ---------------------------------------------------------------------------
# 1. A fake graph predicate must fail
# ---------------------------------------------------------------------------


def test_a_relationship_type_no_layer_declares_is_reported() -> None:
    """The case the old gate could not express, because the graph was in its own reference."""
    observed = {"MENTIONS_ENTITY": 28_110, "TOTALLY_INVENTED_PREDICATE": 1}
    undeclared = scorecard.undeclared_relationship_types(
        observed, all_declared_relationship_types()
    )
    assert undeclared == ["TOTALLY_INVENTED_PREDICATE"]


def test_the_old_tautology_would_have_passed_the_same_input() -> None:
    """Shows the defect rather than describing it.

    Reconstructs the original expression -- ``declared = ontology | observed`` -- and
    demonstrates that it reports nothing for the very input the repaired gate catches. This
    is the assertion that makes 'a green result from a vacuous gate is not evidence'
    concrete.
    """
    observed = {"MENTIONS_ENTITY": 28_110, "TOTALLY_INVENTED_PREDICATE": 1}
    tautological = frozenset(all_declared_relationship_types() | set(observed))
    assert scorecard.undeclared_relationship_types(observed, tautological) == []
    assert scorecard.undeclared_relationship_types(
        observed, all_declared_relationship_types()
    ) == ["TOTALLY_INVENTED_PREDICATE"]


# ---------------------------------------------------------------------------
# 2. A declared predicate must pass
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "predicate",
    ["MENTIONS_ENTITY", "CONTAINS", "HAS_RITUAL_STEP", "USES_FORMULA"],
)
def test_a_declared_predicate_passes(predicate: str) -> None:
    """One per layer: domain, corpus, campaign, enrichment."""
    assert predicate in all_declared_relationship_types()
    assert scorecard.undeclared_relationship_types(
        {predicate: 1}, all_declared_relationship_types()
    ) == []


# ---------------------------------------------------------------------------
# 3. Removing a declaration must make the gate fail
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "predicate", ["HAS_RITUAL_STEP", "QUALITY_VERDICT_ABOUT", "CONTAINS", "HAS_RISHI"]
)
def test_removing_a_declaration_makes_the_gate_fail(predicate: str) -> None:
    """The owner's explicit requirement: withdraw a declaration, watch the gate go red.

    This is what proves the gate reads the declarations rather than the graph. If it were
    still deriving its universe from observed types, a smaller declaration set would change
    nothing.
    """
    full = all_declared_relationship_types()
    assert predicate in full
    without = frozenset(full - {predicate})
    assert scorecard.undeclared_relationship_types({predicate: 7}, without) == [predicate]


def test_the_declared_set_does_not_read_the_graph() -> None:
    """Composed from layer declarations only, and each layer is present.

    Asserted as containment rather than equality so adding a predicate to a layer does not
    fail this test -- it should not. What must hold is that the composed set is exactly the
    union of the declaring layers, with nothing else mixed in.
    """
    from vedagraph.enrich.predicates import CONTROLLED_PREDICATES

    composed = all_declared_relationship_types()
    layers = (
        DOMAIN_RELATIONSHIP_TYPES
        | CORPUS_RELATIONSHIP_TYPES
        | CAMPAIGN_RELATIONSHIP_TYPES
        | CONTROLLED_PREDICATES
        | SYSTEM_RELATIONSHIP_TYPES
    )
    assert composed == frozenset(layers)
    # Every layer actually contributes, so none can be silently dropped from the union.
    for layer in (
        DOMAIN_RELATIONSHIP_TYPES,
        CORPUS_RELATIONSHIP_TYPES,
        CAMPAIGN_RELATIONSHIP_TYPES,
        CONTROLLED_PREDICATES,
    ):
        assert layer <= composed and layer


def test_system_exceptions_are_declared_even_when_empty() -> None:
    """Neo4j reserves no relationship types, so this is empty -- and says so.

    An empty declared set answers "are there system exceptions?" explicitly. An absent one
    leaves the answer implicit, and adding an exception later would then be invisible.
    """
    assert SYSTEM_RELATIONSHIP_TYPES == frozenset()


# ---------------------------------------------------------------------------
# 4. Endpoint signatures
# ---------------------------------------------------------------------------


def test_every_corpus_and_campaign_predicate_has_a_signature() -> None:
    """141,264 edges across 18 predicates had their endpoints checked by nothing.

    The scorecard's signature loop iterated RELATIONSHIP_SIGNATURES, whose key set is
    asserted equal to DOMAIN_RELATIONSHIP_TYPES -- so the corpus and campaign predicates
    were outside it by construction.
    """
    assert set(CORPUS_AND_CAMPAIGN_SIGNATURES) == (
        CORPUS_RELATIONSHIP_TYPES | CAMPAIGN_RELATIONSHIP_TYPES
    )
    for predicate, (subjects, objects) in CORPUS_AND_CAMPAIGN_SIGNATURES.items():
        assert subjects, f"{predicate} declares no subject labels"
        assert objects, f"{predicate} declares no object labels"


def test_a_wrong_endpoint_signature_is_detectable() -> None:
    """A step edge from a Devata is a violation, and the declared signature says so.

    Checked against the declaration rather than against the graph, so this holds whether or
    not such an edge currently exists -- which is the point: the check must be able to
    describe a violation before one is written.
    """
    subjects, objects = CORPUS_AND_CAMPAIGN_SIGNATURES["HAS_RITUAL_STEP"]
    assert "Ritual" in subjects and "RitualStep" in objects
    assert "Devata" not in subjects, "a deity is not a rite"
    assert "Passage" not in objects, "a step is not a passage"

    # And the Samhita predicate keeps its own, narrower range: widening HAS_STEP to reach
    # :RitualStep is exactly the meaning change the campaign refused.
    from vedagraph.domain.ontology import RELATIONSHIP_SIGNATURES

    _, has_step_objects = RELATIONSHIP_SIGNATURES["HAS_STEP"]
    assert "RitualStep" not in has_step_objects
    assert has_step_objects != objects


# ---------------------------------------------------------------------------
# 5. Labels
# ---------------------------------------------------------------------------


def test_a_label_cannot_be_both_product_and_internal() -> None:
    assert PRODUCT_LABELS.isdisjoint(INTERNAL_LABELS)


@pytest.mark.parametrize(
    "label", ["RitualStep", "Scholar", "ScholarlyWork", "ScholarlyDisagreement"]
)
def test_the_product_visible_campaign_labels_are_declared_product(label: str) -> None:
    assert label in PRODUCT_LABELS
    assert label not in INTERNAL_LABELS


@pytest.mark.parametrize("label", ["QualityVerdict", "RoleFiller", "DeityCommunity"])
def test_the_internal_campaign_labels_are_declared_internal(label: str) -> None:
    """These three are facts about the record, not Vedic subjects.

    :QualityVerdict is this repository's assessment of its own passages, on the same footing
    as :QAIssue. :RoleFiller is the wiring by which a role assignment reaches its referent
    and carries no entity_key at all. :DeityCommunity is an analytic partition imported with
    its own refusal and no membership claim.
    """
    assert label in INTERNAL_LABELS
    assert label not in PRODUCT_LABELS


# ---------------------------------------------------------------------------
# 6. Signature coverage, pinned so the uncovered set cannot grow
# ---------------------------------------------------------------------------


def test_all_three_signature_layers_are_composed() -> None:
    """One function, three sources. Two scripts disagreed by 12 predicates until it existed.

    The scorecard iterated ``RELATIONSHIP_SIGNATURES`` alone, which left 18 predicates and
    141,264 edges unconstrained. Adding the corpus and campaign dicts fixed that and left
    the enrichment layer's own ``SIGNATURES`` still unread -- so the scorecard and the
    provenance report gave different coverage figures for the same graph.
    """
    from vedagraph.domain.ontology import all_endpoint_signatures
    from vedagraph.enrich.predicates import SIGNATURES as ENRICH_SIGNATURES

    composed = all_endpoint_signatures()
    for source in (RELATIONSHIP_SIGNATURES, CORPUS_AND_CAMPAIGN_SIGNATURES):
        assert set(source) <= set(composed)
    assert set(ENRICH_SIGNATURES) <= set(composed)
    for predicate, (subjects, objects) in composed.items():
        assert subjects, f"{predicate} declares no subject labels"
        assert objects, f"{predicate} declares no object labels"


#: Populated predicates whose endpoints nothing constrains. The model-extracted semantic
#: layer plus QA_ISSUE_ON, registered as GAP-SEMANTIC-SIGNATURE-COVERAGE-001.
#:
#: Pinned as an exact set rather than a count so that closing one entry is visible and
#: ADDING one fails. A "<= 15" assertion would let a new unconstrained predicate in as long
#: as an old one was fixed in the same change.
#:
#: Built from the DECLARED set, not the populated one. My first version listed only the 13
#: that carry edges and this test caught the other two: ASSOCIATED_WITH and EXPRESSES are
#: declared and unpopulated, and an unsigned predicate is a hole whether or not an edge
#: exists through it yet.
UNCONSTRAINED_BY_DESIGN_FOR_NOW: frozenset[str] = frozenset(
    {
        "ASSOCIATED_WITH",
        "CONTRASTS_WITH",
        "DESCRIBES",
        "DESCRIBES_ACTION",
        "EXPRESSES",
        "HAS_THEME",
        "INVOKES",
        "INVOLVES_OFFERING",
        "INVOLVES_RITUAL",
        "INVOLVES_SUBSTANCE",
        "PRAISES",
        "QA_ISSUE_ON",
        "REFERS_TO_NATURAL_PHENOMENON",
        "REFERS_TO_PLACE",
        "REQUESTS",
    }
)


def test_no_new_predicate_escapes_endpoint_enforcement() -> None:
    """Every declared predicate is either signed or on the named exception list.

    Declared rather than populated, so this runs without a database: a predicate declared
    and unsigned is a hole whether or not an edge exists yet.
    """
    from vedagraph.domain.ontology import all_endpoint_signatures

    unsigned = all_declared_relationship_types() - set(all_endpoint_signatures())
    unexpected = sorted(unsigned - UNCONSTRAINED_BY_DESIGN_FOR_NOW)
    assert not unexpected, (
        f"{len(unexpected)} declared predicate(s) have no endpoint signature and are not on "
        f"the exception list: {unexpected}. Declare a signature, or add it to the list with "
        f"a registry gap explaining why."
    )
