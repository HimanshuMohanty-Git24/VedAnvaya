"""No Veda is ever both in scope and not covered, on any endpoint.

GAP-PRODUCT_SURFACE-001. ``GET /api/v1/insights/devatas/{id}`` served
``vedas_in_scope: ["RV","AV","YV","SV"]`` beside ``vedas_not_covered: ["AV","YV","SV"]``
while ``measured`` carried AV 635, YV 221, SV 405 and RV 2305. Three corpora were reported
as in scope, not covered, and measured at once, because ``vedas_not_covered`` was populated
from the *ascription* dimension while ``vedas_in_scope`` and ``measured`` described the
*naming* one. The prose caveats said this correctly; the structured block a machine
consumer reads contradicted them, and a client filtering on ``vedas_not_covered`` would
have discarded three quarters of the figures the endpoint had just measured.

Three layers of test, because a fix at only the top one is one endpoint away from
returning:

*The model refuses it.* :class:`CoverageView` and :class:`CoverageDimension` raise on
construction, so the merged form is unrepresentable rather than merely absent today.

*The response carries its dimensions.* The deity insight reports naming and ascription
separately, each with its own scope.

*Every endpoint is swept.* Every GET route is walked and every coverage block anywhere in
the payload -- nested, in a sub-block, in a list -- is checked. That is the clause of the
closure test that says "no endpoint", and a sweep is the only thing that can establish it.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from vedagraph.api.models.common import CoverageDimension, CoverageView

# ---------------------------------------------------------------------------
# The model refuses the merged form
# ---------------------------------------------------------------------------


def test_a_veda_cannot_be_both_in_scope_and_not_covered() -> None:
    """The exact shape the deity insight shipped, rejected at construction."""
    with pytest.raises(ValidationError) as excinfo:
        CoverageView(
            vedas_in_scope=["RV", "AV", "YV", "SV"],
            vedas_not_covered=["AV", "YV", "SV"],
            measured={"RV": 2305, "AV": 635, "YV": 221, "SV": 405},
        )
    assert "both in scope and not covered" in str(excinfo.value)


def test_a_non_zero_measured_figure_cannot_sit_in_not_covered() -> None:
    """The subtler half: publish a count, then tell a client to discard it."""
    with pytest.raises(ValidationError) as excinfo:
        CoverageView(
            vedas_in_scope=["RV"],
            vedas_not_covered=["AV"],
            measured={"RV": 2305, "AV": 635},
        )
    assert "non-zero measured figure" in str(excinfo.value)


def test_a_measured_zero_beside_not_covered_is_legal() -> None:
    """Stating the zero is how an absent layer is told from a silent corpus."""
    view = CoverageView(
        vedas_in_scope=["RV"], vedas_not_covered=["AV", "YV", "SV"], measured={"RV": 10, "AV": 0}
    )
    assert view.vedas_not_covered == ["AV", "YV", "SV"]


def test_a_dimension_is_held_to_the_same_rule() -> None:
    with pytest.raises(ValidationError) as excinfo:
        CoverageDimension(
            dimension="ascription",
            vedas_in_scope=["RV", "AV"],
            vedas_not_covered=["AV"],
            means="x",
        )
    assert "both in scope and not covered" in str(excinfo.value)


# ---------------------------------------------------------------------------
# The sweep
# ---------------------------------------------------------------------------

#: Every GET route, with ids that resolve against the frozen graph. Hand-listed rather
#: than discovered, because a route that 404s on a discovered id sweeps nothing and reports
#: a pass -- this project has certified an absence against the wrong surface twice.
SWEEP_PATHS: tuple[str, ...] = (
    "/api/v1/stats",
    "/api/v1/works",
    "/api/v1/works/VG:WORK:RV:SAK",
    "/api/v1/works/VG:WORK:SV:KAU",
    "/api/v1/works/VG:WORK:YV:VSM",
    "/api/v1/works/VG:WORK:AV:SAU",
    "/api/v1/works/VG:WORK:RV:SAK/root",
    "/api/v1/devatas",
    "/api/v1/devatas/VG:DEVATA:INDRAH",
    "/api/v1/devatas/VG:DEVATA:INDRAH/network",
    "/api/v1/devatas/VG:DEVATA:INDRAH/passages",
    "/api/v1/entities",
    "/api/v1/insights/devatas/VG:DEVATA:INDRAH",
    "/api/v1/insights/devatas/VG:DEVATA:AGNIH",
    "/api/v1/insights/capabilities",
    "/api/v1/insights/cross-veda",
    "/api/v1/insights/metals",
    "/api/v1/insights/rituals",
    "/api/v1/insights/material-culture",
    "/api/v1/insights/civilization",
    "/api/v1/insights/formula-diffusion",
    "/api/v1/insights/atharvaveda/concerns",
    "/api/v1/passages/VG:RV:SAK:M01:S001:V001",
    "/api/v1/passages/VG:SV:KAU:ARANYA:D01:V01",
    "/api/v1/passages/VG:YV:VSM:A01:V001",
    "/api/v1/passages/VG:AV:SAU:K01:S001:V001",
    "/api/v1/passages/VG:RV:SAK:M01:S001:V001/reader",
    "/api/v1/passages/VG:SV:KAU:ARANYA:D01:V01/reader",
    "/api/v1/passages/VG:RV:SAK:M01:S001:V001/parallels",
    "/api/v1/rituals",
    "/api/v1/search?q=indra",
    "/api/v1/search?q=fire",
)


def _coverage_blocks(node: Any, path: str = "$") -> Iterator[tuple[str, dict[str, Any]]]:
    """Every dict anywhere in a payload that looks like a coverage block."""
    if isinstance(node, dict):
        if "vedas_in_scope" in node or "vedas_not_covered" in node:
            yield path, node
        for key, value in node.items():
            yield from _coverage_blocks(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _coverage_blocks(value, f"{path}[{index}]")


#: How many coverage blocks the sweep must actually inspect. A sweep that reaches nothing
#: passes, which is the failure mode this project has shipped twice, so the count is
#: asserted as well as the contents. Measured at 34 on the frozen graph; the floor is set
#: just below it so a layer that grows does not fail, and a route list that silently stops
#: resolving does.
MINIMUM_COVERAGE_BLOCKS_SWEPT = 30


@pytest.mark.neo4j
def test_no_endpoint_reports_a_veda_as_both_in_scope_and_not_covered(
    live_client: TestClient,
) -> None:
    """One test over every route, reporting every violation rather than the first.

    Not parametrised, deliberately: the interesting assertion is the *global* one, that the
    sweep reached a real number of coverage blocks. A per-route test cannot make it, and a
    per-route test that 404s reports a pass having checked nothing.
    """
    violations: list[str] = []
    unreachable: list[str] = []
    swept = 0
    for route in SWEEP_PATHS:
        response = live_client.get(route)
        if response.status_code != 200:
            unreachable.append(f"{route} -> {response.status_code}")
            continue
        for where, block in _coverage_blocks(response.json()):
            swept += 1
            in_scope = set(block.get("vedas_in_scope") or [])
            not_covered = set(block.get("vedas_not_covered") or [])
            overlap = in_scope & not_covered
            if overlap:
                violations.append(f"{route} {where}: {sorted(overlap)} in scope AND not covered")
            measured = block.get("measured") or {}
            if isinstance(measured, dict):
                contradicted = sorted(veda for veda in not_covered if measured.get(veda))
                if contradicted:
                    violations.append(
                        f"{route} {where}: {contradicted} carries a non-zero measured "
                        "figure while listed as not covered"
                    )
    assert not unreachable, f"sweep could not reach: {unreachable}"
    assert not violations, "\n".join(violations)
    assert swept >= MINIMUM_COVERAGE_BLOCKS_SWEPT, (
        f"the sweep inspected only {swept} coverage blocks, below the floor of "
        f"{MINIMUM_COVERAGE_BLOCKS_SWEPT} -- it is passing vacuously"
    )


@pytest.mark.neo4j
def test_the_deity_insight_reports_coverage_per_dimension(live_client: TestClient) -> None:
    """The second clause: a multi-dimension response states each dimension's scope."""
    body = live_client.get("/api/v1/insights/devatas/VG:DEVATA:INDRAH").json()
    coverage = body["coverage"]
    dimensions = {dim["dimension"]: dim for dim in coverage["dimensions"]}
    assert set(dimensions) == {"naming", "ascription"}

    naming = dimensions["naming"]
    assert set(naming["vedas_in_scope"]) == {"RV", "AV", "YV", "SV"}
    assert naming["vedas_not_covered"] == []
    assert set(naming["measured"]) == {"RV", "AV", "YV", "SV"}

    ascription = dimensions["ascription"]
    # ["RV", "AV"], measured. See
    # test_a_deity_with_no_rigvedic_ascription_still_has_rv_in_ascription_scope for why this
    # moved: GAP-ATTRIBUTION-002 clause 2, and 851 Atharvavedic passages carrying a resolved
    # dedication under HAS_DEVATA_DERIVED.
    assert ascription["vedas_in_scope"] == ["RV", "AV"]
    assert set(ascription["vedas_not_covered"]) == {"YV", "SV"}
    # The layer's scope, not this deity's: Indra is ascribed in the Rigveda, and the per-Veda
    # figures sum to the one the endpoint reports as ``ascribed_total``. Summed rather than
    # read off RV alone, because the total now spans both dedication routes and a check that
    # compared one corpus against the whole would pass while the other corpus went missing.
    assert sum(ascription["measured"].values()) == body["ascribed_total"]
    # And the decomposition is published beside the total, each route with its own method, so
    # the two evidence classes cannot be read as one.
    routes = {row["predicate"]: row for row in body["ascription_routes"]}
    assert set(routes) == {"HAS_DEVATA", "HAS_DEVATA_DERIVED"}
    assert routes["HAS_DEVATA"]["method"] == "SOURCE_STATED_ANUKRAMANI_DEDICATION"
    assert routes["HAS_DEVATA_DERIVED"]["method"] == "TADDHITA_SASYA_DEVATA_DERIVATION"
    # Equality, not `>=`. Measured: 0 passages carry both dedication predicates to one deity,
    # so the routes partition the total exactly -- and `>=` would pass on the very
    # double-counting class this assertion exists to catch, which is how a cartesian-product
    # bug in this query doubled every per-Veda figure once already.
    assert sum(row["passages"] for row in routes.values()) == body["ascribed_total"]

    # And the top-level block now describes exactly one dimension.
    assert coverage["vedas_not_covered"] == []
    assert coverage["measured"] == naming["measured"]


@pytest.mark.neo4j
def test_a_deity_with_no_rigvedic_ascription_still_has_rv_in_ascription_scope(
    live_client: TestClient,
) -> None:
    """Scope is a property of the layer. A deity's own zero is not an absent layer.

    Reporting RV as not-covered for a deity the apparatus simply never dedicates a hymn to
    would invert the very distinction this block exists to draw.
    """
    # The layer scope is ["RV", "AV"] and is now MEASURED rather than read from
    # profiles.ATTRIBUTION_VEDAS, which is ("RV",) and correct about HAS_DEVATA alone.
    # GAP-ATTRIBUTION-002 clause 2: HAS_DEVATA_DERIVED carries 882 Atharvavedic dedications
    # over 851 passages, so publishing AV in vedas_not_covered was a false absence on the one
    # field whose job is to tell an absent layer from a real zero. The claim this test makes
    # is unchanged -- scope belongs to the LAYER, not to the deity -- so it is asserted over
    # every corpus the layer reaches rather than over the single one it used to.
    listing = live_client.get("/api/v1/devatas?limit=100").json()
    for row in listing["items"]:
        body = live_client.get(f"/api/v1/insights/devatas/{row['id']}").json()
        ascription = next(
            dim for dim in body["coverage"]["dimensions"] if dim["dimension"] == "ascription"
        )
        assert ascription["vedas_in_scope"] == ["RV", "AV"], row["id"]
        for reached in ("RV", "AV"):
            assert reached not in ascription["vedas_not_covered"], (row["id"], reached)
        # The Samaveda and Yajurveda carry no dedication layer of any kind, which is
        # GAP-ATTRIBUTION-001 and a source block. Those zeros ARE absent layers and must stay
        # named, or this assertion would pass on a block that had quietly stopped disclosing.
        assert set(ascription["vedas_not_covered"]) == {"SV", "YV"}, row["id"]
