"""The deity population contract, including the partition test the module promises.

The load-bearing test in this file is
:func:`test_known_structures_partition_every_devata_node`. Everything else here checks a
function; that one checks that the *world* still looks the way the function assumes.

:data:`~vedagraph.api.services.deity_population.KNOWN_DEITY_STRUCTURES` fails closed: an
unrecognised ``structure`` is excluded from the deity population, because we cannot certify
as a god a thing whose type we do not recognise. On its own that is a slow-motion bug --
a rebuild introducing ``structure='SEMI_DIVINE'`` would silently shrink the pantheon and
no response would say so, which is precisely the shape that once let a guard cascade into
deleting all 419 layer-owned grades. The partition test converts that silence into a
failing test.
"""

from __future__ import annotations

from typing import Any

import pytest

from vedagraph.api.models.entity import (
    DEITY_STRUCTURES,
    NON_DEITY_STRUCTURES,
    DeityPopulation,
)
from vedagraph.api.repositories.neo4j_repository import Neo4jRepository
from vedagraph.api.services.deity_population import (
    DEITY_STRUCTURE_PARAM,
    KNOWN_DEITY_STRUCTURES,
    NON_DEITY_EXCLUSION_CAVEAT,
    deity_structure_clause,
    deity_structure_parameters,
    filter_co_deity_labels,
    is_deity,
    population_caveats,
)

#: The live distribution, measured today. Asserted rather than assumed, so a rebuild that
#: moves a deity between structures fails here instead of in a caveat that has gone quiet.
EXPECTED_STRUCTURE_COUNTS = {
    "INDIVIDUAL": 72,
    "ABSTRACT": 41,
    "PAIR": 38,
    "GROUP": 33,
    "HUMAN": 22,
    "PATRON_PRAISE": 7,
    "UNSPECIFIED": 1,
}
EXPECTED_DEVATA_TOTAL = 214
#: The ruled eligible population. Not derived from the structure counts above, because the
#: ruling and the structure disagree on 29 nodes and that disagreement is the whole of
#: GAP-ENTITY_COVERAGE-008.
EXPECTED_ELIGIBLE_DEITIES = 157


# ---------------------------------------------------------------------------
# The contract, offline
# ---------------------------------------------------------------------------


def test_known_structures_is_the_union_of_the_two_contract_sets() -> None:
    assert KNOWN_DEITY_STRUCTURES == DEITY_STRUCTURES | NON_DEITY_STRUCTURES
    assert DEITY_STRUCTURES.isdisjoint(NON_DEITY_STRUCTURES), (
        "a structure cannot be both a god and not a god"
    )


@pytest.mark.parametrize("structure", sorted(DEITY_STRUCTURES))
def test_deity_structures_are_deities(structure: str) -> None:
    assert is_deity(structure)


@pytest.mark.parametrize("structure", sorted(NON_DEITY_STRUCTURES))
def test_non_deity_structures_are_not_deities(structure: str) -> None:
    assert not is_deity(structure)


@pytest.mark.parametrize("structure", [None, "", "SEMI_DIVINE", "individual", "Human"])
def test_unknown_and_null_structures_fail_closed(structure: str | None) -> None:
    """An unrecognised structure is not a deity. Case-sensitively, and null included."""
    assert not is_deity(structure)


def test_structure_clause_binds_a_parameter_and_reads_the_ruling() -> None:
    """Nothing a caller controls reaches the query text, and the clause reads the ruling.

    It read ``structure``, which made it a second eligibility predicate beside the
    documented one. Asserting the property name here is what stops it drifting back: a
    structure list is the thing that got spelled four ways.
    """
    clause = deity_structure_clause("dv")
    assert f"${DEITY_STRUCTURE_PARAM}" in clause
    assert "coalesce(dv.is_deity, false)" in clause
    assert "structure" not in clause, "eligibility is the ruling, not the structure"
    for structure in DEITY_STRUCTURES:
        assert structure not in clause, "no value may be interpolated into the query text"


def test_structure_clause_coalesces_so_an_unruled_node_is_excluded() -> None:
    """The coalesce default must be false, or a missing ruling admits a god."""
    clause = deity_structure_clause("x")
    assert "coalesce(x.is_deity, false)" in clause
    assert "coalesce(x.is_deity, true)" not in clause


def test_populations_differ_only_in_the_bound_list() -> None:
    deities = deity_structure_parameters(DeityPopulation.DEITIES)
    everything = deity_structure_parameters(DeityPopulation.ALL_ASCRIPTIONS)
    assert deities[DEITY_STRUCTURE_PARAM] == [True]
    assert sorted(everything[DEITY_STRUCTURE_PARAM]) == [False, True]
    assert deities.keys() == everything.keys()


def test_both_populations_carry_a_caveat() -> None:
    """Filtering hides 57 real ascriptions; not filtering returns them. Both need saying.

    The figure was 30 and named a dog among the excluded. The recorded ruling admits the dog
    and excludes 28 abstractions this caveat never mentioned, so the sentence was wrong in
    both directions at once.
    """
    for population in DeityPopulation:
        caveats = population_caveats(population)
        assert caveats, f"{population} returned no caveat"
        assert all(caveat.text for caveat in caveats)
    assert "57 of the 214" in NON_DEITY_EXCLUSION_CAVEAT
    assert "one dog" not in NON_DEITY_EXCLUSION_CAVEAT


def test_filter_co_deity_labels_drops_humans_unknowns_and_unresolved() -> None:
    rows: list[dict[str, Any]] = [
        {"display_label": "Soma", "structure": "INDIVIDUAL", "is_deity": True},
        {"display_label": "Vasukra", "structure": "HUMAN", "is_deity": False},
        {"display_label": "praise of a gift", "structure": "PATRON_PRAISE", "is_deity": False},
        {"display_label": "the dog", "structure": "UNSPECIFIED", "is_deity": True},
        {"display_label": "something new", "structure": "SEMI_DIVINE"},
        {"display_label": "unresolvable"},
    ]
    kept = filter_co_deity_labels(rows)
    # The dog is kept now: the recorded ruling admits it, and dropping it was the
    # morphological accident the ruling names. The unruled rows still fail closed.
    assert [row["display_label"] for row in kept] == ["Soma", "the dog"]


# ---------------------------------------------------------------------------
# The world, live
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
def test_known_structures_partition_every_devata_node(live_repository: Neo4jRepository) -> None:
    """THE test this module exists for: no ``:Devata`` carries an unrecognised structure.

    A structure value outside :data:`KNOWN_DEITY_STRUCTURES` would be excluded from every
    deity surface, silently, because the contract fails closed. This makes that a failing
    test instead of a quietly smaller pantheon.
    """
    rows = live_repository.run(
        "MATCH (dv:Devata) RETURN coalesce(dv.structure, 'UNSPECIFIED') AS structure, count(*) AS n"
    )
    measured = {str(row["structure"]): int(row["n"]) for row in rows}
    unknown = set(measured) - KNOWN_DEITY_STRUCTURES
    assert not unknown, (
        f"unrecognised Devata structure(s) {sorted(unknown)}: these are excluded from "
        "every deity surface by the fail-closed contract, so the pantheon has shrunk "
        "without any response saying so. Add them to DEITY_STRUCTURES or "
        "NON_DEITY_STRUCTURES deliberately."
    )
    assert measured == EXPECTED_STRUCTURE_COUNTS
    assert sum(measured.values()) == EXPECTED_DEVATA_TOTAL


@pytest.mark.neo4j
def test_the_clause_resolves_the_expected_population_live(
    live_repository: Neo4jRepository,
) -> None:
    """The two populations, run against the graph, differ by exactly the 57 ruled out."""
    cypher = f"MATCH (dv:Devata) WHERE {deity_structure_clause('dv')} RETURN count(dv) AS n"
    deities = live_repository.run_one(cypher, **deity_structure_parameters(DeityPopulation.DEITIES))
    everything = live_repository.run_one(
        cypher, **deity_structure_parameters(DeityPopulation.ALL_ASCRIPTIONS)
    )
    assert deities is not None and everything is not None
    assert int(everything["n"]) == EXPECTED_DEVATA_TOTAL
    # 157, the ruled population: 22 HUMAN_PATRON + 7 DANASTUTI_GIFT_PRAISE +
    # 28 ABSTRACTION_NOT_AN_ADDRESSEE excluded. The structure clause returned 184 because it
    # admitted all 41 ABSTRACT and excluded the one UNSPECIFIED node the ruling admits.
    assert int(deities["n"]) == EXPECTED_ELIGIBLE_DEITIES == 157
    assert int(everything["n"]) - int(deities["n"]) == 57


@pytest.mark.neo4j
def test_the_named_non_deities_are_really_in_the_graph(live_repository: Neo4jRepository) -> None:
    """The caveat names Vasistha, Brbu the carpenter and a dog. Check it is not fiction.

    A caveat that describes data the graph does not hold is worse than no caveat, and this
    project has shipped one: ``agni_and_indra_together`` called a gap a finding while the
    same database returned 157 rows. So the prose is checked against the rows.
    """
    rows = live_repository.run(
        "MATCH (dv:Devata) WHERE dv.entity_key IN $keys "
        "RETURN dv.entity_key AS key, dv.structure AS structure",
        keys=[
            "VG:DEVATA:VASISTHAH",
            "VG:DEVATA:BRBUSTAKSA",
            "VG:DEVATA:SUNAH",
            "VG:DEVATA:PAIJAVANASYA-SUDASO-DANASTUTIH",
        ],
    )
    found = {str(row["key"]): str(row["structure"]) for row in rows}
    assert found == {
        "VG:DEVATA:VASISTHAH": "HUMAN",
        "VG:DEVATA:BRBUSTAKSA": "HUMAN",
        "VG:DEVATA:SUNAH": "UNSPECIFIED",
        "VG:DEVATA:PAIJAVANASYA-SUDASO-DANASTUTIH": "PATRON_PRAISE",
    }
    assert not any(is_deity(structure) for structure in found.values())


# ---------------------------------------------------------------------------
# GAP-ENTITY_COVERAGE-008: product consumer consistency
# ---------------------------------------------------------------------------
#
# OWNER_DECISION_ENTITY_008_DEITY_MEMBERSHIP (OWNER_DECISIONS.md section 35) rules that
# canonical product Deity membership and source addressability-as-deity are NOT the same
# semantic predicate, and that `d.is_deity` is the authoritative product one. The registry's
# old closure measure asked the two to AGREE and returned 29 by construction; driving it to 0
# would mean overturning either the 28 per-label ABSTRACT refusals or the recorded ruling that
# keeps the dog. These tests pin the replacement measure: the divergence is allowed, and every
# product surface reads the authoritative predicate.


@pytest.mark.neo4j
def test_the_intentional_divergence_is_exactly_the_recorded_curation(
    live_repository: Neo4jRepository,
) -> None:
    """The 29 are allowed -- and pinned, so a later pass cannot "fix" them by flattening.

    This is clause 4 of the owner decision. If a future rebuild makes the two predicates
    agree, that is not an improvement: it means one of two recorded curations was overturned
    to satisfy a metric, and this test is what says so out loud.
    """
    rows = live_repository.run(
        "MATCH (d:Devata) "
        "WHERE (coalesce(d.structure,'UNSPECIFIED') IN ['HUMAN','PATRON_PRAISE','UNSPECIFIED']) "
        "      <> (d.is_deity = false) "
        "RETURN d.structure AS structure, d.is_deity AS is_deity, "
        "       d.deity_eligibility_ruling AS ruling, count(*) AS n"
    )
    divergence = {
        (str(row["structure"]), bool(row["is_deity"]), str(row["ruling"])): int(row["n"])
        for row in rows
    }
    assert divergence == {
        # The structure predicate admits every ABSTRACT label; the curation refuses these 28
        # one at a time, each with its own recorded reason.
        ("ABSTRACT", False, "NOT_DEITY"): 28,
        # VG:DEVATA:SUNAH, the dog. The structure predicate excludes it for being UNSPECIFIED
        # rather than INDIVIDUAL, which the ruling names as a morphological accident.
        ("UNSPECIFIED", True, "DEITY"): 1,
    }, (
        "the intentional predicate divergence has changed. This is NOT a test to re-baseline: "
        "check whether a recorded curation was overturned, and see "
        "docs/reports/data-completeness/OWNER_DECISIONS.md section 35."
    )


@pytest.mark.neo4j
def test_every_divergent_node_carries_its_recorded_reason(
    live_repository: Neo4jRepository,
) -> None:
    """Clause 3. A divergence with no reason is a defect wearing a decision's clothes."""
    from vedagraph.api.config import get_api_settings
    from vedagraph.domain.deity_eligibility import check_product_consumers

    with live_repository.driver.session(database=get_api_settings().neo4j_database) as session:
        measured = check_product_consumers(session)
    assert measured["every_node_ruled"], f"{measured['unruled']} :Devata carry no ruling"
    assert measured["divergence_is_explained"], (
        "these nodes diverge from the source predicate with no recorded reason: "
        f"{measured['nodes_diverging_without_a_recorded_reason']}"
    )
    assert measured["authoritative_population"] == EXPECTED_ELIGIBLE_DEITIES
    assert measured["passes"]


def test_no_consumer_outside_the_contract_substitutes_the_source_predicate() -> None:
    """Clause 1 and 2, as a fact about the source tree rather than about the graph.

    The R1 gate for this entry asked "is the eligibility field POPULATED", which passes on a
    field nothing reads -- the validator-that-silently-skips shape. So this asserts the thing
    that actually matters: no module outside the contract filters deity MEMBERSHIP on
    `structure`. The allowed list names each exemption and why it is one.
    """
    import pathlib

    from vedagraph.domain.deity_eligibility import _STRUCTURE_PREDICATE_ALLOWED_IN

    root = pathlib.Path(__file__).resolve().parents[2] / "src" / "vedagraph"
    needles = ("DEITY_STRUCTURES", "NON_DEITY_STRUCTURES", "'HUMAN','PATRON_PRAISE'")
    offenders = sorted(
        str(path.relative_to(root))
        for path in root.rglob("*.py")
        if path.name not in _STRUCTURE_PREDICATE_ALLOWED_IN
        and any(needle in path.read_text(encoding="utf-8") for needle in needles)
    )
    assert not offenders, (
        f"{offenders} reference a structure-based deity predicate. Product Deity membership "
        "reads deity_eligibility.ELIGIBLE_DEITY_PREDICATE and nothing else; add a deliberate "
        "exemption to _STRUCTURE_PREDICATE_ALLOWED_IN with its reason if this is structural "
        "rather than membership."
    )


def test_no_reader_facing_surface_publishes_a_superseded_deity_population() -> None:
    """Clause 5. 184 was the structure predicate's population and 192 the pre-contract one.

    Both shipped. R2 corrected them where it found them; this is the sweep that says they are
    gone from everything a reader sees, because the repeated defect in this campaign is a
    sentence fixed in one file and alive in another.

    Scoped to READER-FACING copy and generated artifacts, deliberately not to Python
    docstrings. Two modules describe these figures as defects they fixed --
    ``insight_service._deity_population_stat`` says it "published 184 resolved deities while
    every deity route served 157" -- and a sweep that flagged those would be demanding the
    project forget why the number was wrong. A historical note is not a claim; a rendered
    string is.
    """
    import pathlib
    import re

    from vedagraph.domain.deity_eligibility import SUPERSEDED_POPULATION_FIGURES

    root = pathlib.Path(__file__).resolve().parents[2]
    targets = [
        *(root / "frontend" / "src").rglob("*.ts"),
        *(root / "frontend" / "src").rglob("*.tsx"),
        *(root / "frontend" / "public").rglob("*.json"),
    ]
    # The figure adjacent to a deity word. A bare 184 is not a claim: entity_service
    # legitimately says "184 of the 214" about the PROFILED population, 214 minus 30 profiles.
    pattern = re.compile(
        r"\b(?:" + "|".join(str(n) for n in SUPERSEDED_POPULATION_FIGURES) + r")\b"
        r"(?:\s+\w+){0,3}?\s+(?:deities|deity|eligible_deities|pantheon)",
        re.IGNORECASE,
    )
    hits = [
        f"{path.relative_to(root)}: {match.group(0)!r}"
        for path in targets
        for match in pattern.finditer(path.read_text(encoding="utf-8"))
    ]
    assert not hits, (
        "a superseded deity population is still published to a reader: "
        f"{hits}. The population is 157 by deity_eligibility.ELIGIBLE_DEITY_PREDICATE."
    )
