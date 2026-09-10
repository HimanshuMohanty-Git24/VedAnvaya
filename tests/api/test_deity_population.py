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


def test_structure_clause_binds_a_parameter_and_names_no_structure() -> None:
    """Nothing a caller controls, and no structure name, reaches the query text."""
    clause = deity_structure_clause("dv")
    assert f"${DEITY_STRUCTURE_PARAM}" in clause
    assert "coalesce(dv.structure, 'UNSPECIFIED')" in clause
    for structure in DEITY_STRUCTURES:
        assert structure not in clause, "the structure list must travel as a parameter"


def test_structure_clause_coalesces_so_a_null_structure_is_excluded() -> None:
    """The coalesce default must be a NON-deity, or a missing property admits a god."""
    clause = deity_structure_clause("x")
    default = clause.split("'")[1]
    assert default in NON_DEITY_STRUCTURES


def test_populations_differ_only_in_the_bound_list() -> None:
    deities = deity_structure_parameters(DeityPopulation.DEITIES)
    everything = deity_structure_parameters(DeityPopulation.ALL_ASCRIPTIONS)
    assert set(deities[DEITY_STRUCTURE_PARAM]) == DEITY_STRUCTURES
    assert set(everything[DEITY_STRUCTURE_PARAM]) == KNOWN_DEITY_STRUCTURES
    assert deities.keys() == everything.keys()


def test_both_populations_carry_a_caveat() -> None:
    """Filtering hides 30 real ascriptions; not filtering returns a dog. Both need saying."""
    for population in DeityPopulation:
        caveats = population_caveats(population)
        assert caveats, f"{population} returned no caveat"
        assert all(caveat.text for caveat in caveats)
    assert "30 of the 214" in NON_DEITY_EXCLUSION_CAVEAT


def test_filter_co_deity_labels_drops_humans_unknowns_and_unresolved() -> None:
    rows: list[dict[str, Any]] = [
        {"display_label": "Soma", "structure": "INDIVIDUAL"},
        {"display_label": "Vasukra", "structure": "HUMAN"},
        {"display_label": "praise of a gift", "structure": "PATRON_PRAISE"},
        {"display_label": "the dog", "structure": "UNSPECIFIED"},
        {"display_label": "something new", "structure": "SEMI_DIVINE"},
        {"display_label": "unresolvable"},
    ]
    kept = filter_co_deity_labels(rows)
    assert [row["display_label"] for row in kept] == ["Soma"]


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
    """The two populations, run against the graph, differ by exactly the 30 non-deities."""
    cypher = f"MATCH (dv:Devata) WHERE {deity_structure_clause('dv')} RETURN count(dv) AS n"
    deities = live_repository.run_one(cypher, **deity_structure_parameters(DeityPopulation.DEITIES))
    everything = live_repository.run_one(
        cypher, **deity_structure_parameters(DeityPopulation.ALL_ASCRIPTIONS)
    )
    assert deities is not None and everything is not None
    non_deities = sum(EXPECTED_STRUCTURE_COUNTS[s] for s in NON_DEITY_STRUCTURES)
    assert int(everything["n"]) == EXPECTED_DEVATA_TOTAL
    assert int(deities["n"]) == EXPECTED_DEVATA_TOTAL - non_deities == 184


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
