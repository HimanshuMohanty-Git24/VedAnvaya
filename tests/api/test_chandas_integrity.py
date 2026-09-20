"""A bracket fragment may not become a canonical metre assertion. Owner round four, item 1.

``GAP-AV-CHANDOMETRE-SEGMENTATION-001``: the AV registry's segmentation of Whitney's printed
bracket is incomplete, so some ``:Chandas`` entities are whole fragments carrying a deity, a
metre and a per-verse exception in one string. 33 canonical ``HAS_CHANDAS`` edges pointed at
28 of them, and a reader asking a verse's metre was told
``'āindryas. ānuṣṭubham: 2. 3-av. 6-p. jagatī'``.

M9 withdrew those 33. These tests are what stops them, or new ones like them, coming back.

The criterion under test is Whitney's own notation rather than any reading of Sanskrit: he
uses ``:`` to separate a hymn statement from its per-verse exceptions, and a bare ``N.`` is a
verse number. Neither can occur inside a metre *name*. That distinction is what made the 33
demonstrable, and it is why these tests can be written at all — a philological criterion
could not be.

The entity population is deliberately *not* under test for absence: the 28 entities remain in
the graph on purpose, because they hold the printed literal and removing them would destroy
the source's own wording.
"""

from __future__ import annotations

import re

import pytest

from vedagraph.api.repositories.neo4j_repository import Neo4jRepository

#: A bare verse number inside a label. ``3-av.`` and ``6-p.`` are structural qualifiers of a
#: metre name and are excluded by the lookbehind; ``24. `` is a reference to verse 24.
VERSE_REFERENCE = re.compile(r"(?<![0-9a-zA-Z-])\d{1,2}\.\s")

#: What Whitney's notation says about a string that cannot be a metre name.
MALFORMED_SIGNALS = (
    (":", "a colon separates his hymn statement from its per-verse exceptions"),
    (None, "an embedded verse number addresses a verse rather than naming a metre"),
)


def is_malformed(label: str) -> bool:
    return ":" in label or bool(VERSE_REFERENCE.search(label))


def test_the_criterion_recognises_the_fragments_it_was_built_from() -> None:
    """Offline, and first: if the predicate is wrong the live tests below prove nothing.

    The positive cases are the real labels M9 withdrew. The negative cases are real metre
    names carrying the structural qualifiers that a naive "contains a digit and a dot" rule
    would wrongly condemn — which is why the lookbehind exists.
    """
    for label in (
        "āindryas. ānuṣṭubham: 2. 3-av. 6-p. jagatī",
        "sarvātmakaṁ rudram. trāiṣṭubham: 2. anuṣṭubh",
        "bhāumī. ānuṣṭubham: 1, 3. pathyāpan̄kti",
        "6. anuṣṭubh",
        "2. bhurij",
        "3-av. 6-p. virāḍ atijagatī: 24. 5-p. virāḍ atijagatī",
    ):
        assert is_malformed(label), f"{label!r} should be recognised as not a metre name"

    for label in (
        "anuṣṭubh",
        "triṣṭubh",
        "jagatī",
        "pathyāpan̄kti",
        "3-av. 6-p. dvyuṣṇiggarbhā jagatī",
        "1-av. 2-p. nicṛd ārcy anuṣṭubh",
        "upariṣṭādbṛhatī",
    ):
        assert not is_malformed(label), f"{label!r} is a metre name and must pass"


@pytest.mark.neo4j
def test_no_canonical_metre_assertion_points_at_a_bracket_fragment(
    live_repository: Neo4jRepository,
) -> None:
    """The regression itself. 33 such assertions existed before M9.

    Scoped to the assertion, not the entity: the fragments stay in the graph because they
    carry the printed literal, and what must not exist is an *edge* claiming one is a verse's
    metre.
    """
    offenders = [
        {
            "passage": str(row["passage"]),
            "label": str(row["label"]),
            "entity": str(row["entity"]),
        }
        for row in live_repository.run(
            "MATCH (p:Passage)-[:HAS_CHANDAS]->(c:Chandas) "
            "RETURN p.canonical_key AS passage, c.entity_key AS entity, "
            "c.preferred_label AS label"
        )
        if is_malformed(str(row["label"]))
    ]
    assert not offenders, (
        f"{len(offenders)} metre assertion(s) point at an unsegmented source bracket rather "
        f"than a metre name: {offenders[:3]}. See GAP-AV-CHANDOMETRE-SEGMENTATION-001."
    )


@pytest.mark.neo4j
def test_the_withdrawn_literals_are_preserved_not_deleted(
    live_repository: Neo4jRepository,
) -> None:
    """Withdrawing the claim must not destroy the source's wording.

    Two halves. The 28 entities still exist, so the printed string is still in the graph; and
    each of the 33 affected passages carries a withheld-claim record naming that string, the
    entity, the original scope and source, and the reason.

    Without the second half a deleted assertion becomes silence, and silence reads as *the
    source says nothing here* — false for all 33, and for the 16 passages left with no other
    metre edge it is the only thing standing between a reader and a false zero.
    """
    row = live_repository.run_one(
        "MATCH (p:Passage) WHERE p.chandas_withheld_literal IS NOT NULL "
        "RETURN count(p) AS records, "
        "count(DISTINCT p.chandas_withheld_entity_key) AS entities, "
        "sum(CASE WHEN p.chandas_withheld_reason IS NULL "
        "  OR p.chandas_withheld_source_id IS NULL "
        "  OR p.chandas_withheld_scope_origin IS NULL THEN 1 ELSE 0 END) AS untyped"
    )
    assert row is not None
    assert int(row["records"]) == 33, (
        f"expected 33 withheld-claim records, found {row['records']}"
    )
    assert int(row["untyped"]) == 0, (
        f"{row['untyped']} record(s) lack a reason or their provenance, so a reader cannot "
        "tell why the claim is absent or where it came from"
    )

    # Every recorded literal is still reachable as an entity: the record points somewhere.
    dangling = live_repository.run_one(
        "MATCH (p:Passage) WHERE p.chandas_withheld_entity_key IS NOT NULL "
        "AND NOT EXISTS { MATCH (:Chandas {entity_key: p.chandas_withheld_entity_key}) } "
        "RETURN count(p) AS c"
    )
    assert dangling is not None and int(dangling["c"]) == 0, (
        "a withheld record names an entity the graph no longer holds; the literal it was "
        "meant to preserve is gone"
    )


@pytest.mark.neo4j
def test_the_withdrawal_created_no_inferred_replacement(
    live_repository: Neo4jRepository,
) -> None:
    """No metre was read out of the mixed string, which the owner barred.

    A replacement would show up as a verse-level metre edge stamped by M9. There are none,
    and there should be none: every metre assertion for these passages traces to the source
    whose segmentation is the defect, so no independent evidence exists to build one from.
    """
    row = live_repository.run_one(
        "MATCH (p:Passage)-[e:HAS_CHANDAS]->() WHERE e.m9_replacement IS NOT NULL "
        "RETURN count(e) AS c"
    )
    assert row is not None and int(row["c"]) == 0


@pytest.mark.neo4j
def test_the_chandas_entity_population_was_not_migrated(
    live_repository: Neo4jRepository,
) -> None:
    """No re-keying, merging or renaming, which the owner barred explicitly.

    Asserted on the namespace totals: 541 AV_WHITNEY entities and 34 RV. A migration would
    move one of these numbers even if every label still looked plausible.
    """
    counts = {
        str(row["ns"]): int(row["n"])
        for row in live_repository.run(
            "MATCH (c:Chandas) RETURN c.registry_namespace AS ns, count(*) AS n"
        )
    }
    assert counts.get("AV_WHITNEY_ANUKRAMANI") == 541
    assert counts.get("RV_WSC2023_ANUKRAMANI") == 34

    keyless = live_repository.run_one(
        "MATCH (c:Chandas) WHERE c.entity_key IS NULL OR c.preferred_label IS NULL "
        "RETURN count(c) AS c"
    )
    assert keyless is not None and int(keyless["c"]) == 0
