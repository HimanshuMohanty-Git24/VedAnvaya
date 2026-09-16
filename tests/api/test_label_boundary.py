"""The product/internal label boundary, asserted against the live graph. Owner Phase C.

Six node labels this campaign created were declared by no authoritative source, and the
consequence was measurable rather than theoretical: ``frontend/.world/world.raw.json`` held
2,568 ``:QualityVerdict`` nodes -- this repository's assessment of its own passages -- as the
fourth-largest type in the public world, ahead of ``:Rishi``.

They got there because "public" is one clause, ``NOT n:Internal``, and nothing had marked
them. ``:RoleFiller`` and ``:DeityCommunity`` escaped only because they carry no id key and
the export drops nodes it cannot name, which is luck and not a boundary.

These tests hold both halves: every label in the graph is classified, and nothing classified
internal can reach a public surface.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from vedagraph.api.repositories.neo4j_repository import Neo4jRepository
from vedagraph.domain.ontology import (
    INTERNAL_LABELS,
    LABEL_INTERNAL,
    PRODUCT_LABELS,
)

WORLD = pathlib.Path("frontend/.world/world.raw.json")

#: Labels present in the graph that are neither product nor internal, each with the reason
#: it is exempt. Empty, and it must stay that way: an entry here is a deliberate act with a
#: written justification, not a place to park a difference nobody classified.
LABEL_EXCEPTIONS: dict[str, str] = {}


@pytest.mark.neo4j
def test_every_graph_label_is_classified(live_repository: Neo4jRepository) -> None:
    """Product, internal, or an exception with a stated reason. No fourth state.

    An unclassified label is the defect this test exists for: it is on the public side of
    ``NOT n:Internal`` by default, so the failure mode of forgetting to classify is
    exposure rather than absence.
    """
    labels = {
        str(row["label"])
        for row in live_repository.run("CALL db.labels() YIELD label RETURN label")
    }
    unclassified = sorted(labels - PRODUCT_LABELS - INTERNAL_LABELS - set(LABEL_EXCEPTIONS))
    assert not unclassified, (
        f"{len(unclassified)} label(s) are neither product nor internal, which puts them on "
        f"the public side of the boundary by default: {unclassified}. Classify each one."
    )


@pytest.mark.neo4j
def test_an_undeclared_public_label_would_be_caught(live_repository: Neo4jRepository) -> None:
    """Proof the check above can fail, without writing to the graph.

    Runs the same set difference against an observed set with one invented label added. If
    the check were deriving its reference from the graph -- the mistake the relationship
    gate made twice -- this would report nothing.
    """
    observed = {
        str(row["label"])
        for row in live_repository.run("CALL db.labels() YIELD label RETURN label")
    } | {"AccidentalSchemaExpansion"}
    unclassified = sorted(observed - PRODUCT_LABELS - INTERNAL_LABELS - set(LABEL_EXCEPTIONS))
    assert unclassified == ["AccidentalSchemaExpansion"]


@pytest.mark.neo4j
def test_every_internally_classified_label_is_marked_in_the_graph(
    live_repository: Neo4jRepository,
) -> None:
    """Declaring a label internal changes nothing unless the nodes carry ``:Internal``.

    The declaration is what a reader of the code sees; the label is what every product query
    actually filters on. A class declared internal and unmarked is the leak with a comment
    denying it.
    """
    for label in sorted(INTERNAL_LABELS - {LABEL_INTERNAL}):
        row = live_repository.run_one(
            f"MATCH (n:`{label}`) RETURN count(n) AS total, "
            f"sum(CASE WHEN n:{LABEL_INTERNAL} THEN 1 ELSE 0 END) AS marked"
        )
        assert row is not None
        total, marked = int(row["total"]), int(row["marked"])
        if not total:
            continue
        assert marked == total, (
            f"{label}: {total - marked} of {total} nodes are not marked :{LABEL_INTERNAL}, "
            f"so they sit on the public side of the product filter"
        )


@pytest.mark.neo4j
def test_no_internal_class_reaches_the_public_entity_surface(
    live_repository: Neo4jRepository,
) -> None:
    """The product filter, applied to each internally classified class."""
    for label in sorted(INTERNAL_LABELS - {LABEL_INTERNAL}):
        row = live_repository.run_one(
            f"MATCH (n:`{label}`) WHERE NOT n:{LABEL_INTERNAL} RETURN count(n) AS c"
        )
        assert row is not None and int(row["c"]) == 0, (
            f"{label} has {row['c']} nodes visible to every product query"
        )


def test_the_exported_world_carries_no_internal_class() -> None:
    """The world file is a second implementation of the boundary, so it is checked too.

    ``export_graph_world.py`` bypasses the API and restates ``NOT n:Internal`` itself, which
    is exactly why it needs its own assertion: the file on disk is what ships.
    """
    if not WORLD.exists():
        pytest.skip("no world export in this checkout")
    payload = json.loads(WORLD.read_text(encoding="utf-8"))
    nodes = payload["nodes"] if isinstance(payload, dict) else payload
    types = {str(node.get("type")) for node in nodes}
    leaked = sorted(types & (INTERNAL_LABELS - {LABEL_INTERNAL}))
    assert not leaked, (
        f"the public world export carries internal class(es) {leaked}. 2,568 "
        f"QualityVerdict nodes were the fourth-largest type in it before M8."
    )


def test_the_scholarship_classes_stay_public() -> None:
    """The other half of the decision, asserted so it cannot be quietly reversed.

    A recorded disagreement is uninterpretable without the scholar who holds it and the work
    that states it, so these three are product content. Demoting them to make the
    unclassified set empty would have been the lazy fix.
    """
    for label in ("Scholar", "ScholarlyWork", "ScholarlyDisagreement"):
        assert label in PRODUCT_LABELS
        assert label not in INTERNAL_LABELS
