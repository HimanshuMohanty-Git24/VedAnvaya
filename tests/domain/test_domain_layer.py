"""Contract tests for the Knowledge Model V2 domain layer.

Almost all of this runs offline. The ontology contract, the grading table, the registry
merge, the taxonomy overlay and the claims file are all data-and-logic that can be checked
without a database, and a test that needed Neo4j running would be skipped exactly when it
was most needed.

The tests that genuinely require a live graph are marked ``live`` and additionally gated on
``VEDAGRAPH_LIVE_NEO4J``, because ``pyproject.toml`` does not deselect ``live`` by default
and this file must not turn a green suite red on a machine with no Neo4j.

What is tested here is deliberately weighted towards the failures this pass was built to
prevent, rather than towards line coverage: a river silently labelled a concept, a
scope-inherited attribution silently graded source-explicit, an interpretation silently
promoted to a fact, and an unlabelled `MATCH` silently producing tens of thousands of
edges.
"""

from __future__ import annotations

import io
import os
import pathlib
import sys
import warnings

import pytest

from vedagraph.domain import ontology
from vedagraph.domain.claims import ClaimRegistryError, load_claims
from vedagraph.domain.ontology import (
    ALL_NODE_TYPE_NAMES,
    DOMAIN_RELATIONSHIP_TYPES,
    INTERNAL_LABELS,
    PRODUCT_LABELS,
    RELATIONSHIP_SIGNATURES,
    UNPOPULATED_BY_DESIGN,
    AttributionPrecision,
    ClaimStatus,
    DeityAxis,
    DevataStructure,
    DomainNodeType,
    KnowledgeLayer,
    QualityTier,
    is_meaningful_label,
    labels_for_node_type,
    product_filter,
)
from vedagraph.domain.queries import QUERIES, QUERIES_BY_NAME, questions_served
from vedagraph.domain.registry import load_domain_entities, merge_registry
from vedagraph.domain.taxonomy import load_taxonomy, registry_keys
from vedagraph.domain.tiers import grade_edge, is_per_passage
from vedagraph.enrich.provenance import ACCEPTABLE_WITHOUT_REVIEW, TrustClass
from vedagraph.semantic.ontology import SemanticNodeType

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]

_LIVE = pytest.mark.skipif(
    not os.environ.get("VEDAGRAPH_LIVE_NEO4J"),
    reason="set VEDAGRAPH_LIVE_NEO4J=1 to run against the local Neo4j instance",
)


# ---------------------------------------------------------------------------
# Ontology identity and the flattening fix
# ---------------------------------------------------------------------------


def test_every_frozen_semantic_type_has_a_label() -> None:
    """The V1 defect was a type the projection knew and dropped.

    If a member of the frozen whitelist has no Neo4j label, the projection has nowhere to
    put it and will fall back to ``:Concept`` -- which is exactly how a river came to be
    labelled a concept.
    """
    for member in SemanticNodeType:
        assert member in ontology.LABEL_BY_SEMANTIC_NODE_TYPE


def test_narrow_types_keep_their_broad_label() -> None:
    """A crop is a plant, so asking for plants must still find barley."""
    assert labels_for_node_type("CROP") == ("Crop", "Plant", "DomainEntity")
    assert labels_for_node_type("METAL") == ("Metal", "Substance", "DomainEntity")
    assert labels_for_node_type("WEAPON") == ("Weapon", "Object", "DomainEntity")
    assert labels_for_node_type("RIVER") == ("River", "Place", "DomainEntity")


def test_unknown_node_type_raises_rather_than_defaulting() -> None:
    """Defaulting is how the flattening happened; it must be impossible, not discouraged."""
    with pytest.raises(ValueError, match="not a known domain node type"):
        labels_for_node_type("NOT_A_TYPE")


def test_every_domain_entity_label_carries_the_marker() -> None:
    for name in ALL_NODE_TYPE_NAMES:
        assert labels_for_node_type(name)[-1] == ontology.LABEL_DOMAIN_ENTITY


def test_v2_types_are_not_in_the_frozen_enum() -> None:
    """The semantic ontology is frozen because sealed runs record its version.

    Growing it would silently redefine what those runs were produced under.
    """
    frozen = {str(m) for m in SemanticNodeType}
    for member in DomainNodeType:
        assert str(member) not in frozen


# ---------------------------------------------------------------------------
# Product / internal separation
# ---------------------------------------------------------------------------


def test_product_and_internal_labels_are_disjoint() -> None:
    assert PRODUCT_LABELS.isdisjoint(INTERNAL_LABELS)


def test_qa_issue_is_internal() -> None:
    """A QA finding is a fact about this repository, not about the Vedas."""
    assert "QAIssue" in INTERNAL_LABELS
    assert "QAIssue" not in PRODUCT_LABELS


def test_exclusion_is_written_once() -> None:
    """One marker label, so a new diagnostic label is excluded by one edit."""
    assert product_filter("dv") == f"NOT dv:{ontology.LABEL_INTERNAL}"


# ---------------------------------------------------------------------------
# Controlled predicates
# ---------------------------------------------------------------------------


def test_every_v2_predicate_has_an_endpoint_signature() -> None:
    assert set(RELATIONSHIP_SIGNATURES) == DOMAIN_RELATIONSHIP_TYPES


def test_signature_endpoints_are_declared_labels() -> None:
    """A signature naming a label nobody creates cannot ever be satisfied."""
    known = PRODUCT_LABELS | INTERNAL_LABELS
    for predicate, (subjects, objects) in RELATIONSHIP_SIGNATURES.items():
        for label in subjects | objects:
            assert label in known, f"{predicate} names undeclared label {label}"


def test_unpopulated_predicates_are_declared_with_a_reason() -> None:
    """An empty edge type is honest only if it says why it is empty."""
    for predicate, reason in UNPOPULATED_BY_DESIGN.items():
        assert predicate in DOMAIN_RELATIONSHIP_TYPES
        assert len(reason) > 40


# ---------------------------------------------------------------------------
# Grading: the honesty layer
# ---------------------------------------------------------------------------


def test_scope_inherited_attribution_is_not_source_explicit() -> None:
    """The single most important grading rule in the system.

    The Anukramani names a deity for a sukta. Projecting that onto each of its mantras is
    a derivation, and 8,329 of 10,558 HAS_DEVATA edges arrive that way. Grading them
    TIER_A would present a scope rule as a source statement.
    """
    grade = grade_edge(
        "HAS_DEVATA",
        {"provenance_class": "SOURCE_DERIVED_SCOPE", "scope_origin": "SUKTA_WIDE"},
    )
    assert grade.tier is QualityTier.TIER_B
    assert grade.layer is KnowledgeLayer.L2_DETERMINISTIC_DERIVED
    assert grade.precision is AttributionPrecision.CONTAINER_INHERITED
    assert not is_per_passage({"scope_origin": "SUKTA_WIDE"})


def test_per_mantra_attribution_is_source_explicit() -> None:
    for scope in ("SINGLE_MANTRA", "MANTRA_RANGE"):
        grade = grade_edge(
            "HAS_DEVATA", {"provenance_class": "SOURCE_EXPLICIT", "scope_origin": scope}
        )
        assert grade.tier is QualityTier.TIER_A
        assert grade.precision is AttributionPrecision.PER_PASSAGE
        assert is_per_passage({"scope_origin": scope})


def test_unreviewed_model_output_is_not_tier_c() -> None:
    """TIER_C means model evidence that survived review. A CANDIDATE has had none."""
    candidate = grade_edge(
        "DESCRIBES", {"trust": "LLM_EXTRACTED", "state": "CANDIDATE", "model": "x"}
    )
    assert candidate.tier is QualityTier.TIER_D
    accepted = grade_edge(
        "DESCRIBES", {"trust": "LLM_EXTRACTED", "state": "ACCEPTED", "model": "x"}
    )
    assert accepted.tier is QualityTier.TIER_C


def test_an_unrecognised_edge_grades_weakest_not_strongest() -> None:
    """Defaulting upward would let an ungraded edge pass for a strong one."""
    assert grade_edge("SOMETHING_NEW", {}).tier is QualityTier.TIER_D


def test_structural_corpus_edges_are_source_explicit() -> None:
    """CONTAINS carries no provenance because nothing about it was inferred."""
    assert grade_edge("CONTAINS", {"sequence": 1}).tier is QualityTier.TIER_A


def test_every_layer_maps_to_exactly_one_tier() -> None:
    assert set(ontology.TIER_BY_LAYER) == set(KnowledgeLayer)
    assert len(set(ontology.TIER_BY_LAYER.values())) == len(KnowledgeLayer)


# ---------------------------------------------------------------------------
# Interpretive claim isolation
# ---------------------------------------------------------------------------


def test_interpretive_claims_can_never_be_accepted() -> None:
    """Enforced by the envelope, not by convention."""
    assert TrustClass.INTERPRETIVE_CLAIM not in ACCEPTABLE_WITHOUT_REVIEW


def test_claims_load_and_every_one_cites_evidence() -> None:
    claims = load_claims(PROJECT_ROOT)
    assert claims, "the claims file should be present"
    for claim in claims:
        assert claim.supported_by or claim.supported_by_statistic
        assert claim.falsifier, f"{claim.claim_id} has no falsifier"
        assert claim.status in set(ClaimStatus)


def test_claim_provenance_is_candidate_and_interpretive() -> None:
    for claim in load_claims(PROJECT_ROOT):
        provenance = claim.provenance
        assert provenance.trust is TrustClass.INTERPRETIVE_CLAIM
        assert str(provenance.state) == "CANDIDATE"
        assert claim.as_row()["quality_tier"] == str(QualityTier.TIER_D)


def test_claims_record_a_disagreement_rather_than_resolving_it() -> None:
    """Two claims contradict each other on purpose; neither is marked as winning."""
    claims = {c.claim_id: c for c in load_claims(PROJECT_ROOT)}
    pairs = [(c.claim_id, other) for c in claims.values() for other in c.contradicts]
    assert pairs, "the claim layer should record at least one live disagreement"
    for left, right in pairs:
        assert right in claims
        assert left in claims[right].contradicts, "contradiction should be symmetric"


def test_a_claim_with_no_evidence_is_refused(tmp_path: pathlib.Path) -> None:
    directory = tmp_path / "data" / "domain" / "vedagraph_domain_v2"
    directory.mkdir(parents=True)
    (directory / "interpretive_claims.yaml").write_text(
        "claims:\n"
        "  - claim_id: VG:CLAIM:NAKED\n"
        "    claim_text: something\n"
        "    claim_type: X\n"
        "    status: MODEL_SYNTHESIS\n"
        "    scope: nowhere\n"
        "    method: none\n"
        "    falsifier: none\n",
        encoding="utf-8",
    )
    with pytest.raises(ClaimRegistryError, match="cites neither a passage nor a metric"):
        load_claims(tmp_path)


def test_a_claim_citing_an_uncomputed_metric_is_refused(tmp_path: pathlib.Path) -> None:
    directory = tmp_path / "data" / "domain" / "vedagraph_domain_v2"
    directory.mkdir(parents=True)
    (directory / "interpretive_claims.yaml").write_text(
        "claims:\n"
        "  - claim_id: VG:CLAIM:GHOST\n"
        "    claim_text: something\n"
        "    claim_type: X\n"
        "    status: MODEL_SYNTHESIS\n"
        "    scope: nowhere\n"
        "    method: none\n"
        "    falsifier: none\n"
        "    supported_by_statistic: [VG:METRIC:DOES_NOT_EXIST:X]\n",
        encoding="utf-8",
    )
    with pytest.raises(ClaimRegistryError, match="does not compute"):
        load_claims(tmp_path, known_metric_ids=frozenset({"VG:METRIC:REAL:X"}))


# ---------------------------------------------------------------------------
# Devata taxonomy: multi-role separation
# ---------------------------------------------------------------------------


def test_taxonomy_covers_every_registry_deity() -> None:
    entries, summary = load_taxonomy(PROJECT_ROOT)
    assert summary.registry_entities == len(registry_keys(PROJECT_ROOT))
    assert not summary.missing_from_overlay
    assert len(entries) == summary.registry_entities


def test_every_deity_has_a_readable_english_label() -> None:
    """These fill a display slot, so UNKNOWN is not an acceptable value."""
    entries, _ = load_taxonomy(PROJECT_ROOT)
    for entry in entries:
        assert is_meaningful_label(entry.label_en), entry.entity_key


def test_a_deity_may_hold_several_axes_at_once() -> None:
    """The whole point of replacing devata_subtype.

    Agni is a fire medium, a priestly figure and a terrestrial deity. A single enum forced
    a choice between them and answered UNKNOWN on 97.7% of rows rather than choose.
    """
    entries = {e.entity_key: e for e in load_taxonomy(PROJECT_ROOT)[0]}
    agni = entries["VG:DEVATA:AGNIH"]
    assert len(agni.axes) > 1
    assert DeityAxis.UNSPECIFIED not in agni.axes


def test_unspecified_is_never_combined_with_a_real_axis() -> None:
    """UNSPECIFIED means "not classified", not "and also something else"."""
    for entry in load_taxonomy(PROJECT_ROOT)[0]:
        if DeityAxis.UNSPECIFIED in entry.axes:
            assert entry.axes == (DeityAxis.UNSPECIFIED,), entry.entity_key


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ("VG:DEVATA:SURYAH", "VG:DEVATA:SAVITA"),
        ("VG:DEVATA:SOMAH", "VG:DEVATA:PAVAMANAH-SOMAH"),
        ("VG:DEVATA:MITRAH", "VG:DEVATA:VARUNAH"),
        ("VG:DEVATA:MITRAH", "VG:DEVATA:MITRAVARUNAU"),
    ],
)
def test_entities_the_spec_forbids_merging_stay_distinct(left: str, right: str) -> None:
    """Named conflations: Savitr is not Surya, and the dual is not either member."""
    entries = {e.entity_key: e for e in load_taxonomy(PROJECT_ROOT)[0]}
    assert left in entries and right in entries
    assert entries[left].entity_key != entries[right].entity_key


def test_rudra_carries_no_shiva_identification() -> None:
    """Rudra's identification with Siva is post-Vedic, so it must not be asserted.

    The assertion-bearing fields are checked, and ``curation_note`` deliberately is not:
    that field is where a refusal is *recorded*, and the note for Rudra spends a paragraph
    explaining that importing Siva's attributes would dress a historical development as a
    textual fact. Grepping the note would fail the entry for documenting the very
    restraint being tested for, so the second assertion requires the discussion to be
    there rather than forbidding it.
    """
    entries = {e.entity_key: e for e in load_taxonomy(PROJECT_ROOT)[0]}
    rudra = entries["VG:DEVATA:RUDRAH"]
    asserted = " ".join(
        [rudra.label_en, rudra.label_iast, rudra.short_description, *map(str, rudra.axes)]
    ).lower()
    assert "siva" not in asserted
    assert "śiva" not in asserted
    assert "siva" in rudra.curation_note.lower(), (
        "the overlay should record that the Siva identification was considered and refused"
    )


def test_composites_decompose_only_into_real_deities() -> None:
    entries, _ = load_taxonomy(PROJECT_ROOT)
    known = registry_keys(PROJECT_ROOT)
    for entry in entries:
        for component in entry.composed_of:
            assert component in known
            assert component != entry.entity_key


def test_structure_and_axis_vocabularies_are_closed() -> None:
    entries, _ = load_taxonomy(PROJECT_ROOT)
    for entry in entries:
        assert entry.structure in set(DevataStructure)
        for axis in entry.axes:
            assert axis in set(DeityAxis)


def test_unknown_taxonomy_rate_is_measured_against_the_registry() -> None:
    """An entity the overlay omits must count as unclassified, not vanish."""
    _, summary = load_taxonomy(PROJECT_ROOT)
    expected = (summary.registry_entities - summary.classified) / summary.registry_entities
    assert summary.unknown_taxonomy_rate == pytest.approx(expected, abs=1e-6)


# ---------------------------------------------------------------------------
# Registry merge: one alias namespace
# ---------------------------------------------------------------------------


def test_merged_registry_is_clean_and_loads() -> None:
    report = merge_registry(PROJECT_ROOT)
    assert report.clean
    assert not report.duplicate_ids
    assert not report.alias_collisions
    entities = load_domain_entities(PROJECT_ROOT)
    assert len(entities) == report.merged_entities


def test_merge_refuses_a_duplicate_entity_across_fragments() -> None:
    """The guard that caught VARMAN-ARMOUR being authored twice.

    Two fragments defining one id would otherwise be resolved by file order.
    """
    report = merge_registry(PROJECT_ROOT)
    ids = [e.concept_id for e in load_domain_entities(PROJECT_ROOT)]
    assert len(ids) == len(set(ids))
    assert report.merged_entities == len(set(ids))


def test_every_entity_declares_a_known_node_type() -> None:
    for entity in load_domain_entities(PROJECT_ROOT):
        assert entity.node_type in ALL_NODE_TYPE_NAMES
        labels_for_node_type(entity.node_type)


def test_the_domain_types_the_killer_questions_name_are_populated() -> None:
    """Questions 9, 10, 15 and 16 name crops, metals and afflictions by name."""
    by_type: dict[str, int] = {}
    for entity in load_domain_entities(PROJECT_ROOT):
        by_type[entity.node_type] = by_type.get(entity.node_type, 0) + 1
    for required in ("CROP", "METAL", "CONDITION", "HUMAN_CONCERN", "RIVER", "ANIMAL"):
        assert by_type.get(required, 0) > 0, f"no {required} entities"


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------


def test_query_names_are_unique() -> None:
    assert len(QUERIES_BY_NAME) == len(QUERIES)


def test_every_query_states_its_limits() -> None:
    """An answer published without its caveat is the failure this pass exists to fix."""
    for query in QUERIES:
        assert query.question.endswith("?"), query.name
        assert query.caveat, f"{query.name} has no caveat"


def test_no_query_returns_internal_nodes_unfiltered() -> None:
    """A query naming an internal label directly has bypassed the central exclusion."""
    for query in QUERIES:
        for label in ("QAIssue", "TextVersion", "Translation"):
            assert f":{label}" not in query.cypher, f"{query.name} touches {label}"


def test_queries_cover_a_substantial_share_of_the_killer_questions() -> None:
    """The benchmark is 100 questions, not 50, and the bound was never widened.

    ``max(served) <= 50`` was correct while the benchmark was
    ``VEDAGRAPH_50_KILLER_QUESTIONS``. The frozen V3 benchmark is Q1-Q100, so the old
    bound made serving any question above 50 a test failure -- which is why the V3.1
    audit found Q51-Q100 with no named query at all while this test stayed green. A
    guard that forbids the work it is meant to encourage is worse than no guard.
    """
    served = questions_served()
    assert len(served) >= 30, f"only {len(served)} of 100 questions have a query"
    assert max(served) <= 100 and min(served) >= 1


# ---------------------------------------------------------------------------
# Live graph invariants
# ---------------------------------------------------------------------------


def _session() -> object:
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "vedagraph_dev"))
    return driver


@pytest.mark.live
@_LIVE
def test_live_no_internal_node_reaches_product_traversal() -> None:
    driver = _session()
    try:
        with driver.session() as session:  # type: ignore[attr-defined]
            leaked = session.run(
                "MATCH (n) WHERE NOT n:Internal AND "
                "(n:QAIssue OR n:TextVersion OR n:Translation OR n:Source) "
                "RETURN count(n) AS c"
            ).single()["c"]
            assert leaked == 0
    finally:
        driver.close()  # type: ignore[attr-defined]


@pytest.mark.live
@_LIVE
def test_live_every_edge_is_graded() -> None:
    driver = _session()
    try:
        with driver.session() as session:  # type: ignore[attr-defined]
            ungraded = session.run(
                "MATCH ()-[r]->() WHERE r.quality_tier IS NULL RETURN count(r) AS c"
            ).single()["c"]
            assert ungraded == 0
    finally:
        driver.close()  # type: ignore[attr-defined]


@pytest.mark.live
@_LIVE
def test_live_every_product_node_has_a_readable_label() -> None:
    driver = _session()
    try:
        with driver.session() as session:  # type: ignore[attr-defined]
            unnamed = session.run(
                "MATCH (n) WHERE NOT n:Internal AND (n.display_label IS NULL OR "
                "trim(toString(n.display_label)) IN "
                "['', 'UNKNOWN', 'NULL', 'null', 'None', '?', '-']) RETURN count(n) AS c"
            ).single()["c"]
            assert unnamed == 0
    finally:
        driver.close()  # type: ignore[attr-defined]


@pytest.mark.live
@_LIVE
def test_live_no_claim_points_at_a_passage_via_concerns() -> None:
    """The unlabelled-MATCH bug: CONCERNS once matched 11,590 passages per Work.

    A claim concerns the Rigveda; it does not concern each of its verses individually.
    """
    driver = _session()
    try:
        with driver.session() as session:  # type: ignore[attr-defined]
            bogus = session.run(
                "MATCH (:InterpretiveClaim)-[r:CONCERNS]->(:Passage) RETURN count(r) AS c"
            ).single()["c"]
            assert bogus == 0
            metric_bogus = session.run(
                "MATCH (:DerivedMetric)-[r:MEASURES]->(:Passage) RETURN count(r) AS c"
            ).single()["c"]
            assert metric_bogus == 0
    finally:
        driver.close()  # type: ignore[attr-defined]


@pytest.mark.live
@_LIVE
def test_live_typed_labels_exist_for_the_flattened_types() -> None:
    """The V1 defect, checked against the store rather than against the projection."""
    driver = _session()
    try:
        with driver.session() as session:  # type: ignore[attr-defined]
            for label in ("Animal", "River", "Crop", "Metal", "Condition", "Ritual"):
                count = session.run(f"MATCH (n:{label}) RETURN count(n) AS c").single()["c"]
                assert count > 0, f"no :{label} nodes in the live graph"
    finally:
        driver.close()  # type: ignore[attr-defined]


def _merged_concern_whitelists() -> dict[str, list[str]]:
    """The concern whitelist as the builder assembles it: V1 + V3 + promotions.

    Imported from the build script rather than reimplemented, so this test cannot drift
    from the merge it is checking. That mattered: an earlier copy of the merge rule here
    omitted the promotions block and turned a correct projection into a test failure.
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "_build_domain_v2_for_test", PROJECT_ROOT / "scripts" / "build_domain_v2.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    saved = sys.stdout
    try:
        # The script rebinds sys.stdout at import time; give it a throwaway.
        sys.stdout = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            spec.loader.exec_module(module)
    finally:
        sys.stdout = saved

    domain_dir = PROJECT_ROOT / "data" / "domain" / "vedagraph_domain_v2"
    return dict(
        module._merge_concern_lists(
            module._read_yaml(domain_dir / "concern_predicates.yaml"),
            module._read_yaml(domain_dir / "concern_predicates_v3.yaml"),
        )
    )


@pytest.mark.live
@_LIVE
def test_live_typed_concern_predicates_only_reach_whitelisted_entities() -> None:
    """A typed edge is a mention plus whitelist membership, and nothing else.

    The whitelist is shorter than the entity list on purpose: an entity absent from it
    stays a mention, and emitting a typed edge for it would be wrong rather than
    generous. This checks the projector honoured that.

    **The whitelist is the merged one, not the V1 file.** V3 adds
    ``concern_predicates_v3.yaml`` (declared ``merge_semantics: union_with_v1``) plus a
    ``promotions`` block, and the projector honours all three. Reading only the V1 file
    here made this test fail with "ADDRESSES_CONCERN reached an entity outside the
    whitelist" on 107 edges that are, in fact, whitelisted -- the test was measuring a
    subset of the contract and reporting the difference as a violation. It now reads the
    same merge the builder uses, so the two cannot disagree.
    """
    lists = _merged_concern_whitelists()
    driver = _session()
    try:
        with driver.session() as session:  # type: ignore[attr-defined]
            for key, rel_type in (
                ("addresses_concern", "ADDRESSES_CONCERN"),
                ("treats", "TREATS"),
                ("protects_from", "PROTECTS_FROM"),
                ("used_for_rite", "USED_FOR_RITE"),
            ):
                allowed = [str(k) for k in (lists.get(key) or [])]
                stray = session.run(
                    f"MATCH ()-[:{rel_type}]->(e) WHERE NOT e.entity_key IN $allowed "
                    "RETURN count(*) AS c",
                    allowed=allowed,
                ).single()["c"]
                assert stray == 0, f"{rel_type} reached an entity outside the whitelist"
    finally:
        driver.close()  # type: ignore[attr-defined]


@pytest.mark.live
@_LIVE
def test_live_treats_is_interpretive_and_addresses_concern_is_derived() -> None:
    """The tier split is the claim, so it is worth a test.

    TREATS asserts that a passage acts on an affliction; ADDRESSES_CONCERN asserts only
    what naming a wish already asserts. Grading them alike would lose that.
    """
    driver = _session()
    try:
        with driver.session() as session:  # type: ignore[attr-defined]
            for rel_type, expected in (
                ("ADDRESSES_CONCERN", "TIER_B"),
                ("USED_FOR_RITE", "TIER_B"),
                ("TREATS", "TIER_D"),
                ("PROTECTS_FROM", "TIER_D"),
            ):
                tiers = session.run(
                    f"MATCH ()-[r:{rel_type}]->() RETURN collect(DISTINCT r.quality_tier) AS tiers"
                ).single()["tiers"]
                if tiers:
                    # USED_FOR_RITE carries TWO populations by design and must not be
                    # collapsed to one tier: 110 source-stated verse-level tags at TIER_B
                    # and 419 book locus priors at TIER_D. The prior is a CANDIDATE
                    # interpretive claim -- the book makes the claim, not the verse, and
                    # the enrichment that identified the book rests on a chosen threshold.
                    # This assertion previously read `tiers == [expected]` and passed only
                    # because the generic regrade was flattening the priors to TIER_B,
                    # presenting 419 candidate priors as Sanskrit-grounded facts. Once
                    # USED_FOR_RITE became layer-owned the flattening stopped and this
                    # test caught the difference, which is what it is for.
                    if rel_type == "USED_FOR_RITE":
                        assert tiers == ["TIER_B", "TIER_D"], f"{rel_type} graded {tiers}"
                        continue
                    assert tiers == [expected], f"{rel_type} graded {tiers}"
    finally:
        driver.close()  # type: ignore[attr-defined]


@pytest.mark.live
@_LIVE
def test_live_ritual_structure_endpoints_are_typed() -> None:
    """Curated ritual edges must land on the label their signature names."""
    driver = _session()
    try:
        with driver.session() as session:  # type: ignore[attr-defined]
            checks = (
                ("USES_OFFERING", "Offering"),
                ("USES_OBJECT", "Object"),
                ("INVOKES_DEVATA", "Devata"),
                ("PERFORMED_BY", "RitualRole"),
            )
            for rel_type, label in checks:
                bad = session.run(
                    f"MATCH (a)-[:{rel_type}]->(b) "
                    f"WHERE NOT a:Ritual OR NOT b:{label} RETURN count(*) AS c"
                ).single()["c"]
                assert bad == 0, f"{rel_type} has a wrongly-typed endpoint"
    finally:
        driver.close()  # type: ignore[attr-defined]


@pytest.mark.live
@_LIVE
def test_live_evidence_never_publishes_a_private_use_code_point() -> None:
    """Unrendered, U+E000-U+E003 display as nothing, so `rtasya` prints as `tasya`.

    Evidence that silently misquotes the text is worse than no evidence, because it looks
    checkable.
    """
    driver = _session()
    try:
        with driver.session() as session:  # type: ignore[attr-defined]
            rows = session.run(
                "MATCH ()-[m:MENTIONS_ENTITY]->() WHERE m.evidence IS NOT NULL "
                "RETURN m.evidence AS evidence LIMIT 4000"
            )
            for record in rows:
                text = str(record["evidence"])
                assert not any(0xE000 <= ord(ch) <= 0xF8FF for ch in text)
    finally:
        driver.close()  # type: ignore[attr-defined]
