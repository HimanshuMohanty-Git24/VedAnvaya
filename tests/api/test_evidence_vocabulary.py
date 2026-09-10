"""The graph's evidence vocabularies must stay inside the API's declared value spaces.

**The failure these tests exist to have caught.** ``EvidenceBasis`` was written to name how
an assertion arose -- SOURCE_STATED, CONTAINER_INHERITED, MODEL_EXTRACTION -- and the frozen
graph carries a relationship property called ``evidence_basis`` whose values are SANSKRIT,
STRUCTURAL, SOURCE_METADATA, MIXED, TRANSLATION and SHARED_REGISTRY_ENTITIES. The name is
identical and the value spaces are disjoint, so reading one into the other type-checks,
serialises, returns HTTP 200, and reports every attribution edge in the corpus as UNKNOWN:
all 17,889 seer edges, all 16,331 metre edges, all 10,558 deity edges.

Nothing in a unit test catches that. It needs the live graph and it needs to enumerate the
property's *whole* value space rather than grep for the values it expects to find -- this
project has twice certified an absence by asking the wrong question, once against the wrong
surface and once with the wrong vocabulary.

So these tests enumerate. If a rebuild introduces a seventh surface or a fifth precision,
the assertion fails and names the new value, instead of the API quietly downgrading a corpus
of evidence to UNKNOWN.
"""

from __future__ import annotations

import pytest

from vedagraph.api.models.common import (
    AttributionPrecision,
    EvidenceBasis,
    EvidenceSurface,
    basis_from_attribution_precision,
    evidence_surface,
)
from vedagraph.api.repositories.neo4j_repository import Neo4jRepository


def test_the_two_axes_are_genuinely_disjoint() -> None:
    """Documents the collision, so a future edit that "unifies" them fails here first.

    They are not two spellings of one idea. Merging them would produce a field that
    sometimes says how a claim was derived and sometimes says what it was read off, and a
    client could not tell which it got.
    """
    derivation_axis = {member.value for member in EvidenceBasis} - {"UNKNOWN"}
    surface_axis = {member.value for member in EvidenceSurface} - {"UNKNOWN"}
    assert derivation_axis.isdisjoint(surface_axis), (
        "EvidenceBasis and EvidenceSurface have started to overlap; they answer different "
        "questions and a shared member means one of them is being used for the other's job"
    )


def test_precision_mapping_covers_every_declared_precision() -> None:
    for precision in AttributionPrecision:
        if precision is AttributionPrecision.UNKNOWN:
            continue
        assert basis_from_attribution_precision(precision.value) is not None


def test_unrecognised_values_degrade_rather_than_raise() -> None:
    """One odd property must cost one field, not the whole request."""
    assert basis_from_attribution_precision("SOMETHING_NEW") is EvidenceBasis.UNKNOWN
    assert basis_from_attribution_precision(None) is EvidenceBasis.UNKNOWN
    assert evidence_surface("SOMETHING_NEW") is EvidenceSurface.UNKNOWN
    assert evidence_surface(None) is EvidenceSurface.UNKNOWN


@pytest.mark.neo4j
def test_live_relationship_evidence_basis_is_a_known_surface(
    live_repository: Neo4jRepository,
) -> None:
    rows = live_repository.run(
        "MATCH ()-[r]->() WHERE r.evidence_basis IS NOT NULL "
        "RETURN DISTINCT r.evidence_basis AS value ORDER BY value"
    )
    found = {str(row["value"]) for row in rows}
    known = {member.value for member in EvidenceSurface}
    assert found <= known, f"unmapped evidence surfaces on relationships: {sorted(found - known)}"
    # The property is meant to be widely populated; an empty result would mean the query,
    # not the graph, had changed, and would pass the subset assertion vacuously.
    assert found, "no relationship carries evidence_basis -- the query is wrong, not the graph"


@pytest.mark.neo4j
def test_live_node_evidence_basis_is_a_known_surface(live_repository: Neo4jRepository) -> None:
    rows = live_repository.run(
        "MATCH (n) WHERE n.evidence_basis IS NOT NULL "
        "RETURN DISTINCT n.evidence_basis AS value ORDER BY value"
    )
    found = {str(row["value"]) for row in rows}
    known = {member.value for member in EvidenceSurface}
    assert found <= known, f"unmapped evidence surfaces on nodes: {sorted(found - known)}"


@pytest.mark.neo4j
def test_live_attribution_precision_is_fully_mapped(live_repository: Neo4jRepository) -> None:
    """Every precision the graph uses must map to a basis, or attribution reads UNKNOWN."""
    rows = live_repository.run(
        "MATCH ()-[r]->() WHERE r.attribution_precision IS NOT NULL "
        "RETURN DISTINCT r.attribution_precision AS value ORDER BY value"
    )
    found = {str(row["value"]) for row in rows}
    known = {member.value for member in AttributionPrecision}
    assert found <= known, f"unmapped attribution precisions: {sorted(found - known)}"
    assert found, "no relationship carries attribution_precision -- the query is wrong"


@pytest.mark.neo4j
def test_live_attribution_edges_do_not_all_read_unknown(
    live_repository: Neo4jRepository,
) -> None:
    """The regression itself, stated as a number rather than as a vocabulary.

    Casting the graph's ``evidence_basis`` into :class:`EvidenceBasis` produced UNKNOWN for
    every one of these edges. Deriving from ``attribution_precision`` must not.
    """
    rows = live_repository.run(
        "MATCH ()-[r:HAS_RISHI|HAS_CHANDAS|HAS_DEVATA]->() "
        "RETURN r.attribution_precision AS precision, count(*) AS total"
    )
    assert rows, "the attribution layer is missing from the graph"
    resolved = sum(
        int(row["total"])
        for row in rows
        if basis_from_attribution_precision(
            None if row["precision"] is None else str(row["precision"])
        )
        is not EvidenceBasis.UNKNOWN
    )
    total = sum(int(row["total"]) for row in rows)
    assert total > 40_000, f"expected the full attribution layer, measured {total}"
    assert resolved == total, (
        f"{total - resolved} of {total} attribution edges resolve to UNKNOWN; the derivation "
        "is reading the wrong property again"
    )
