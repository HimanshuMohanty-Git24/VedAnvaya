"""Contract tests for the two V3.1 plumbing repairs: ``HAS_FORMULA`` and the sealed
layer's predicate axis.

Both changes are *directionality and vocabulary* work rather than new derivation, so what
is worth pinning is not "does the loader run" but the four things that would make either
change silently wrong:

1. ``HAS_FORMULA`` points the opposite way to ``MEMBER_OF_FAMILY`` and nowhere else. A
   mirror declared with the same signature as its twin is not a mirror.
2. The mirror does not *restate* any graded property. It has to copy them, because the
   only way two directions of one membership can disagree about tier is if someone wrote
   the tier down twice.
3. Every predicate value the sealed run actually uses is either mapped into the closed
   action vocabulary or explicitly refused, with a reason. An unadjudicated value is how a
   residual grows without anyone deciding it should.
4. The mapping never invents a vocabulary member. ``:ActionPredicate`` is a closed set
   whose registry reserves additions to a deliberate ontology change, and a projection
   that mints one has enlarged an ontology from inside a loader.

All four are decidable offline, from the ontology module, the query text, the registry file
and the sealed artifact -- so they run in the default suite rather than only where a
database happens to be up. The live checks that follow are the ones that genuinely cannot
be answered offline (grading parity between two stored directions, and whether the two
assertion layers are still separable on the edge), and they are marked and gated exactly as
``test_v3_layers.py`` marks and gates its own.
"""

from __future__ import annotations

import os
import pathlib
import re
from typing import Any

import pytest
import yaml

from vedagraph.domain.ontology import (
    DOMAIN_RELATIONSHIP_TYPES,
    LABEL_FORMULA,
    LABEL_FORMULA_FAMILY,
    REL_HAS_FORMULA,
    REL_MEMBER_OF_FAMILY,
    RELATIONSHIP_SIGNATURES,
)
from vedagraph.domain.schema import DOMAIN_REL_INDEXES
from vedagraph.domain.sealed_semantics import iter_sealed_assertions
from vedagraph.domain.tiers import LAYER_OWNED_GRADES
from vedagraph.domain.v3_loader import (
    _FAMILY_OUTWARD_QUERY,
    _SEALED_PREDICATE_MAP,
    _SEALED_PREDICATE_WITHHELD,
)

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
REGISTRY = PROJECT_ROOT / "data" / "registry" / "action_predicates.yaml"

_LIVE = pytest.mark.skipif(
    not os.environ.get("VEDAGRAPH_LIVE_NEO4J"),
    reason="set VEDAGRAPH_LIVE_NEO4J=1 to run against the local Neo4j instance",
)

#: Every property whose value is a *grade*. The mirror may not assign any of them: it has
#: to inherit them, or the two directions of one membership can drift apart.
_GRADED_PROPERTIES = (
    "quality_tier",
    "evidence_basis",
    "grade_basis",
    "knowledge_layer",
    "attribution_precision",
    "trust",
    "score",
    "state",
    "role",
    "membership_id",
    "similarity",
    "method",
    "derivation",
)


# ---------------------------------------------------------------------------
# 1. HAS_FORMULA is the reverse of MEMBER_OF_FAMILY, and is declared as such
# ---------------------------------------------------------------------------


def test_has_formula_is_declared_as_the_exact_reverse_of_member_of_family() -> None:
    """The whole point of the predicate is its direction, so the direction is the test.

    ``FormulaFamily`` was a sink in every directed reading of the graph: 2,037
    ``MEMBER_OF_FAMILY`` edges all ran ``Formula -> FormulaFamily`` and nothing ran the
    other way. A repair that declared the new predicate with the *same* signature would
    typecheck, load, and leave the dead end exactly where it was.
    """
    inbound_subjects, inbound_objects = RELATIONSHIP_SIGNATURES[REL_MEMBER_OF_FAMILY]
    outbound_subjects, outbound_objects = RELATIONSHIP_SIGNATURES[REL_HAS_FORMULA]

    assert inbound_subjects == frozenset({LABEL_FORMULA})
    assert inbound_objects == frozenset({LABEL_FORMULA_FAMILY})
    # Reversed, and reversed *exactly*: same two label sets, swapped.
    assert outbound_subjects == inbound_objects
    assert outbound_objects == inbound_subjects


def test_has_formula_is_a_registered_domain_predicate_with_an_index() -> None:
    """A predicate outside ``DOMAIN_RELATIONSHIP_TYPES`` is a controlled-predicate
    violation that ``vedagraph.domain.guards`` fails the build on, and one outside the
    schema has no index on the ``role`` a family browse filters by."""
    assert REL_HAS_FORMULA in DOMAIN_RELATIONSHIP_TYPES
    assert any(f"[r:{REL_HAS_FORMULA}]" in index for index in DOMAIN_REL_INDEXES)


def test_the_name_reads_in_the_direction_it_points() -> None:
    """``FORMULA_MEMBER_OF`` -- the name the V3 close-out gives this gap -- reads
    subject-first as "the formula is a member of", which is the direction that already
    existed. A predicate whose plain reading contradicts its signature is how a query gets
    written backwards, so the close-out's name is deliberately not the declared one."""
    assert REL_HAS_FORMULA == "HAS_FORMULA"
    assert REL_HAS_FORMULA not in {"FORMULA_MEMBER_OF", REL_MEMBER_OF_FAMILY}


# ---------------------------------------------------------------------------
# 2. The mirror inherits every grade rather than restating it
# ---------------------------------------------------------------------------


def _assigned_properties(query: str) -> set[str]:
    """The edge properties the query writes by name, from its ``SET`` clause."""
    return set(re.findall(r"\bh\.(\w+)\s*=", query))


def test_the_outward_mirror_copies_the_grade_instead_of_writing_one() -> None:
    """A restated grade is a second opinion, and this layer is not entitled to one.

    Four of the 2,037 memberships are ``TIER_D`` -- similarity-threshold ``VARIANT`` rows,
    one of which pairs "who hates us" with "whom we hate" -- and the other 2,033 are
    ``TIER_B``. Any mirror that assigned a tier would have to reproduce that split, and a
    reproduction can be wrong. ``h = properties(m)`` cannot be.
    """
    assert "SET h = properties(m)" in _FAMILY_OUTWARD_QUERY
    assigned = _assigned_properties(_FAMILY_OUTWARD_QUERY)
    assert not assigned & set(_GRADED_PROPERTIES), (
        "the mirror must inherit these, not assign them: "
        f"{sorted(assigned & set(_GRADED_PROPERTIES))}"
    )
    # The three it may write: prose read from the family's side, the mirror marker, and the
    # pass id the sweep keys on.
    assert assigned == {"asserts", "mirrors", "build_pass"}


def test_the_mirror_query_never_uses_an_unlabelled_match() -> None:
    """ "Copy every membership edge" invites ``MATCH ()-[m:MEMBER_OF_FAMILY]->()``, and an
    unlabelled MATCH in a mutation is how this repository once created 39,461 bogus
    edges."""
    for match in re.findall(r"MATCH\s+(.+)", _FAMILY_OUTWARD_QUERY):
        assert "()" not in match.replace(" ", ""), match


def test_both_mirrored_directions_are_owned_grades() -> None:
    """The generic stamper re-derives a grade from the relationship type. Applied to a
    mirror it would grade the two directions independently, and they could disagree --
    which is worse than either being wrong, because the answer would depend on which way
    the query walked."""
    assert REL_HAS_FORMULA in LAYER_OWNED_GRADES
    assert REL_MEMBER_OF_FAMILY in LAYER_OWNED_GRADES


# ---------------------------------------------------------------------------
# 3 and 4. The sealed layer's predicate vocabulary
# ---------------------------------------------------------------------------


def _registry_predicates() -> set[str]:
    document: dict[str, Any] = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))
    return {str(entry["predicate"]) for entry in document["predicates"]}


def test_the_sealed_mapping_only_ever_targets_the_closed_registry_vocabulary() -> None:
    """The registry is the architect's contract and says so in its own header: "adding a
    class is a deliberate ontology change, not something an extractor may do because a
    verse needed it". A projection that MERGEd a predicate node would enlarge a closed set
    from inside a loader, and the coverage number would look like progress."""
    registry = _registry_predicates()
    assert registry, "registry parsed empty"
    unknown = set(_SEALED_PREDICATE_MAP.values()) - registry
    assert not unknown, f"mapping targets predicates absent from the registry: {unknown}"


def test_every_sealed_predicate_is_either_mapped_or_refused_with_a_reason() -> None:
    """An unadjudicated value is how a residual grows without anyone deciding it should.

    Read from the sealed artifact rather than from a hard-coded list, so that if the sealed
    vocabulary ever changes this fails instead of quietly filing the new value under
    "unmapped". Nothing here writes: ``iter_sealed_assertions`` is a read of the frozen
    responses.
    """
    used = {row.predicate for row in iter_sealed_assertions(PROJECT_ROOT) if row.predicate}
    assert used, "the sealed run produced no predicates -- artifact missing?"
    adjudicated = set(_SEALED_PREDICATE_MAP) | set(_SEALED_PREDICATE_WITHHELD)
    assert used <= adjudicated, f"unadjudicated sealed predicates: {sorted(used - adjudicated)}"


def test_a_mapped_predicate_is_never_also_refused() -> None:
    """The two tables are the decision, so an overlap is an undecided decision."""
    assert not set(_SEALED_PREDICATE_MAP) & set(_SEALED_PREDICATE_WITHHELD)


def test_every_refusal_carries_a_substantive_reason() -> None:
    """ "Not mapped" and "nobody looked" are indistinguishable in a coverage number, and
    only one of them is acceptable. The reason is stored so a reader can disagree with it."""
    for predicate, reason in _SEALED_PREDICATE_WITHHELD.items():
        assert len(reason) > 40, f"{predicate} has a reason too short to be one"


def test_assertion_predicate_grade_is_layer_owned() -> None:
    """The type now carries both assertion layers, so the generic ``TIER_B``/``STRUCTURAL``
    it used to get would make "predicates asserted at TIER_B" return unreviewed extraction
    over Griffith's English beside Zurich morphology. That is the identical defect
    ``HAS_SEMANTIC_ASSERTION`` was taken out of the generic rules to fix."""
    assert "ASSERTION_PREDICATE" in LAYER_OWNED_GRADES


# ---------------------------------------------------------------------------
# Live: the two properties that cannot be checked without the stored rows
# ---------------------------------------------------------------------------


@pytest.fixture
def live_session() -> Any:
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "vedagraph_dev"))
    with driver.session() as session:
        yield session
    driver.close()


def _one(session: Any, query: str) -> Any:
    record = session.run(query).single()
    return None if record is None else record[0]


@pytest.mark.live
@_LIVE
def test_live_every_membership_has_exactly_one_identically_graded_mirror(
    live_session: Any,
) -> None:
    inbound = _one(
        live_session,
        f"MATCH (:{LABEL_FORMULA})-[r:{REL_MEMBER_OF_FAMILY}]->"
        f"(:{LABEL_FORMULA_FAMILY}) RETURN count(r)",
    )
    outward = _one(
        live_session,
        f"MATCH (:{LABEL_FORMULA_FAMILY})-[r:{REL_HAS_FORMULA}]->"
        f"(:{LABEL_FORMULA}) RETURN count(r)",
    )
    assert inbound == outward

    disagreeing = _one(
        live_session,
        f"""
        MATCH (f:{LABEL_FORMULA})-[m:{REL_MEMBER_OF_FAMILY}]->
              (fam:{LABEL_FORMULA_FAMILY})-[h:{REL_HAS_FORMULA}]->(f)
        WHERE h.role <> m.role
           OR h.quality_tier <> m.quality_tier
           OR h.grade_basis <> m.grade_basis
           OR h.membership_id <> m.membership_id
        RETURN count(*)
        """,
    )
    assert disagreeing == 0


@pytest.mark.live
@_LIVE
def test_live_no_family_count_disagrees_with_the_edges_that_landed(live_session: Any) -> None:
    """A counts block that drifts from the rows it summarises is a known defect class here:
    eight of nine recorded corrections were once never written into the data."""
    fields = (("member_count", None), ("core_count", "CORE"), ("variant_count", "VARIANT"))
    for field, role in fields:
        clause = "" if role is None else f" {{role: '{role}'}}"
        drift = _one(
            live_session,
            f"""
            MATCH (fam:{LABEL_FORMULA_FAMILY})
            OPTIONAL MATCH (fam)-[r:{REL_HAS_FORMULA}{clause}]->(:{LABEL_FORMULA})
            WITH fam, count(r) AS landed
            WHERE coalesce(fam.{field}, -1) <> landed
            RETURN count(*)
            """,
        )
        assert drift == 0, f"{field} disagrees with the landed edges on {drift} families"


@pytest.mark.live
@_LIVE
def test_live_the_two_assertion_layers_remain_separable_on_the_predicate_edge(
    live_session: Any,
) -> None:
    """The rule layer spreads its assertions over 2,228 passages and the model layer packs
    its own into a few hundred; summing them is the specific misleading answer this graph
    exists to refuse. So every ``ASSERTION_PREDICATE`` edge has to say which layer it came
    from *on the edge*, without a hop to the node."""
    ungraded = _one(
        live_session,
        "MATCH ()-[r:ASSERTION_PREDICATE]->(:ActionPredicate) "
        "WHERE r.derivation IS NULL OR r.quality_tier IS NULL RETURN count(r)",
    )
    assert ungraded == 0

    layers = {
        record["d"]: (record["t"], record["b"])
        for record in live_session.run(
            "MATCH ()-[r:ASSERTION_PREDICATE]->(:ActionPredicate) "
            "RETURN r.derivation AS d, collect(DISTINCT r.quality_tier)[0] AS t, "
            "collect(DISTINCT r.evidence_basis)[0] AS b"
        )
    }
    assert layers["MORPHOLOGY_RULE"] == ("TIER_B", "SANSKRIT")
    assert layers["MODEL_EXTRACTION"] == ("TIER_D", "TRANSLATION")


@pytest.mark.live
@_LIVE
def test_live_the_closed_predicate_vocabulary_was_not_enlarged(live_session: Any) -> None:
    """41 nodes: the registry's 40 classes plus ``UNMAPPED_ROOT``. The sealed layer links
    into them and mints none, which is the difference between using a vocabulary and
    editing one."""
    assert _one(live_session, "MATCH (p:ActionPredicate) RETURN count(p)") == 41
    assert (
        _one(
            live_session,
            "MATCH (p:ActionPredicate) RETURN count(DISTINCT p.vocabulary_version)",
        )
        == 1
    )


# ---------------------------------------------------------------------------
# Ritual-layer depth (Wave 2): every typing claim must be witnessed, and every
# threshold-dependent claim must be graded for the threshold
# ---------------------------------------------------------------------------

RITUAL_DEPTH = PROJECT_ROOT / "data" / "domain" / "vedagraph_domain_v2" / "ritual_depth_v3_1.yaml"


def _ritual_depth() -> dict[str, Any]:
    parsed: dict[str, Any] = yaml.safe_load(RITUAL_DEPTH.read_text(encoding="utf-8"))
    return parsed


def test_every_ritual_depth_claim_declares_a_witness() -> None:
    """A curated typing file's characteristic failure is a plausible entry nobody
    re-measured, so the loader disbelieves the file -- which only works if every entry
    carries something to disbelieve."""
    spec = _ritual_depth()
    for block in ("ritual_role_typing", "offering_typing"):
        rows = spec.get(block) or []
        assert rows, f"{block} is empty"
        for row in rows:
            assert row.get("witness"), f"{block}/{row.get('concept_id')} has no witness"
            assert row.get("basis"), f"{block}/{row.get('concept_id')} has no basis"


def test_every_ritual_depth_block_names_the_question_it_unlocks() -> None:
    """ "No answer, no addition" is the wave's rule, and an ontology addition with no
    question behind it is how a ritual model grows past what anyone asked of it."""
    text = RITUAL_DEPTH.read_text(encoding="utf-8")
    for question in ("QUESTION_UNLOCKED: 90", "QUESTION_UNLOCKED: 100", "QUESTION_UNLOCKED: 13"):
        assert question in text


def test_offering_typing_adds_a_label_and_never_substitutes_one() -> None:
    """ghṛta is a substance and an offering both. Substituting would break
    ``USES_SUBSTANCE``, which is the mirror of the error being fixed -- so every row has to
    say which labels it keeps, and the material label has to be among them."""
    for row in _ritual_depth()["offering_typing"]:
        assert row["add_label"] == "Offering"
        keep = row.get("keep_labels") or []
        assert "Concept" in keep and "DomainEntity" in keep, row["concept_id"]
        assert {"Substance", "Animal", "Plant"} & set(keep), row["concept_id"]


def test_the_rite_locus_thresholds_are_declared_and_the_layer_is_tier_d() -> None:
    """A chosen threshold is not a decidable relation. The formula layer's four
    similarity-derived ``VARIANT`` rows are ``TIER_D`` for exactly this reason and the book
    locus rests on two chosen numbers, so it gets the same grade."""
    from vedagraph.domain.v3_loader import (
        _RITE_PRIOR_GRADE,
        RITE_LOCUS_MIN_ENRICHMENT,
        RITE_LOCUS_MIN_TAGGED,
    )

    assert RITE_LOCUS_MIN_ENRICHMENT == 20.0
    assert RITE_LOCUS_MIN_TAGGED == 5
    assert _RITE_PRIOR_GRADE["quality_tier"] == "TIER_D"
    # The load-bearing value: the book makes this claim, not the verse.
    assert _RITE_PRIOR_GRADE["attribution_precision"] == "CONTAINER_INHERITED"
    assert _RITE_PRIOR_GRADE["state"] == "CANDIDATE"


def test_every_declared_rite_locus_passes_its_own_declared_thresholds() -> None:
    """The artifact refuses K18 = funerary against the diagnosis's own suggestion, because
    the graph's tag distribution does not support it. That refusal is only coherent if
    everything the file *does* accept clears the bar it refused K18 on."""
    from vedagraph.domain.v3_loader import RITE_LOCUS_MIN_ENRICHMENT, RITE_LOCUS_MIN_TAGGED

    loci = _ritual_depth()["rite_loci"]
    assert loci
    for row in loci:
        measured = row["measured"]
        assert measured["enrichment"] >= RITE_LOCUS_MIN_ENRICHMENT, row["rite_id"]
        assert measured["strict_tagged_in_book"] >= RITE_LOCUS_MIN_TAGGED, row["rite_id"]
        # The recall figure is the deliverable and must be the ratio it claims to be.
        expected = measured["strict_tagged_in_book"] / measured["book_passages"]
        assert abs(measured["strict_recall_against_locus"] - expected) < 0.001, row["rite_id"]


@pytest.mark.live
@_LIVE
def test_live_the_hotr_heads_the_priestly_role_table_with_its_purity(
    live_session: Any,
) -> None:
    """Q90. A typed-label query that omits the principal officiant of the Rigveda does not
    shorten the answer, it inverts it: a reader concludes the adhvaryu or the patron is the
    central Vedic officiant."""
    top = live_session.run(
        "MATCH (r:RitualRole) OPTIONAL MATCH (:Passage)-[m:MENTIONS_ENTITY]->(r) "
        "WITH r, count(m) AS mentions RETURN r.concept_id AS cid, mentions, "
        "r.alias_purity AS purity ORDER BY mentions DESC LIMIT 1"
    ).single()
    assert top is not None
    assert top["cid"] == "VG:CONCEPT:HOTR-PRIEST"
    # Purity is PUBLISHED, not implied, and the value moved once the correction landed.
    # It was measured at 0.9221 (296 own alias / 25 foreign) against the alias list as it
    # stood mid-session; the shared build_domain_v2.py rebuild then re-extracted mentions
    # from the corrected list, which is what the correction was for, and the 14 adhvaryu
    # forms and 11 generic rtvij- forms are no longer on this node at all. So the value
    # is now 1.0 and the assertion is that the number is present and credible, not that
    # it is still impure. A test that demanded impurity would fail the moment the fix it
    # exists to protect actually worked.
    assert top["purity"] is not None and 0.9 < top["purity"] <= 1.0


@pytest.mark.live
@_LIVE
def test_live_the_book_prior_never_overwrites_a_verse_level_rite_tag(
    live_session: Any,
) -> None:
    """The strict layer is the only honest recall denominator. If the prior had been merged
    into it, recall against the locus book would be 100% by construction and the
    measurement the criterion demands would be destroyed."""
    strict = _one(
        live_session,
        "MATCH (:Passage)-[r:USED_FOR_RITE]->(:SocialRite) "
        "WHERE r.attribution_precision = 'PER_PASSAGE' RETURN count(r)",
    )
    assert strict == 110
    mixed = _one(
        live_session,
        "MATCH (:Passage)-[r:USED_FOR_RITE]->(:SocialRite) "
        "WHERE r.derivation = 'BOOK_LOCUS_PRIOR' "
        "AND r.attribution_precision <> 'CONTAINER_INHERITED' RETURN count(r)",
    )
    assert mixed == 0


@pytest.mark.live
@_LIVE
def test_live_every_rite_with_a_locus_publishes_a_measured_recall(live_session: Any) -> None:
    """Q13/Q60. The figure has to be a column in the row, because the reader who runs the
    obvious query never sees a caveat."""
    rows = list(
        live_session.run(
            "MATCH (s:SocialRite) WHERE s.recall_is_measured "
            "RETURN s.strict_recall_against_locus AS recall, s.locus_book_passages AS size, "
            "s.locus_tagged_passages AS tagged, s.locus_enrichment AS enrichment"
        )
    )
    assert rows
    for row in rows:
        assert row["recall"] is not None and 0.0 < row["recall"] < 1.0
        assert abs(row["recall"] - row["tagged"] / row["size"]) < 0.001
        assert row["enrichment"] >= 20.0
