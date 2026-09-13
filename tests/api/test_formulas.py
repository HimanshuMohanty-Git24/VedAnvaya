"""Tests for the formula and formula-family detail endpoints.

The whole file exists around one hazard. Every formula-family membership is stored twice --
2,037 ``MEMBER_OF_FAMILY`` edges and 2,037 ``HAS_FORMULA`` edges mirroring them, sharing a
``membership_id`` -- and a traversal that follows both returns every member twice. Measured
against the live graph, that is exactly ``2 x member_count`` on all 720 families, which
would read as a larger family rather than as a bug. So the live tests here reconcile the
traversal against the recorded counts family by family, and the offline tests pin the
direction contract itself so that a later edit cannot quietly add the mirror back.

The second hazard is arithmetic. ``core_count + expansion_count + variant_count`` equals
``member_count`` on all 720 families, but 157 of them additionally record a
``secondary_core_count`` that is a *subset* of ``core_count``. Adding the four over-counts
those 157, nothing in the frozen graph says so, and no membership edge carries a
``SECONDARY_CORE`` role -- so the API has to report the number and refuse to sum it.
"""

from __future__ import annotations

import json
import time

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import FakeRepository, UntracedBlock, build_client
from tests.api.test_graph import assert_no_leaks
from vedagraph.api.repositories.neo4j_repository import Neo4jRepository
from vedagraph.api.routes import formulas
from vedagraph.api.services.formula_service import (
    MAX_FAMILIES_PER_FORMULA,
    MAX_FAMILY_MEMBERS,
    MAX_OCCURRENCES,
    MEMBERSHIP_ROLES,
)
from vedagraph.api.services.graph_service import (
    FAMILY_MEMBERSHIP_DIRECTION,
    FAMILY_MEMBERSHIP_MIRROR,
    PATH_RELATIONSHIPS,
)

VISVA_BHUVANA = "VG:ENRICH:FORMULA-FAMILY:709faeaecdc5a79716fa565ce0a051f0"
PATA_SVASTIBHIH = "VG:ENRICH:FORMULA:01ee076bd8b5c608c52c6cb6f245f7f5"


@pytest.fixture
def formula_client(fake_repository: FakeRepository) -> TestClient:
    """``routes/formulas`` is not mounted in ``app.py`` yet, so the tests mount it.

    Deliberately not a workaround: the router belongs in ``_mount_v1_routers`` and this
    fixture is what keeps these tests honest until it is there. If the module is later
    mounted in the app, this include becomes a harmless no-op rather than a duplicate route,
    because FastAPI matches the first registration.
    """
    app, client = build_client(fake_repository)
    app.include_router(formulas.router, prefix="/api/v1")
    with client:
        app.state.repository = fake_repository
        yield client


@pytest.fixture
def live_formula_client(live_repository: Neo4jRepository) -> TestClient:
    from vedagraph.api.app import create_app
    from vedagraph.api.dependencies import get_repository

    app = create_app()
    app.include_router(formulas.router, prefix="/api/v1")
    app.dependency_overrides[get_repository] = lambda: live_repository
    with TestClient(app) as client:
        app.state.repository = live_repository
        yield client


# ---------------------------------------------------------------------------
# The direction contract: offline
# ---------------------------------------------------------------------------


class TestDirectionContract:
    def test_the_authoritative_direction_is_the_inbound_one(self) -> None:
        """``HAS_FORMULA`` is a mirror copied from ``MEMBER_OF_FAMILY``; the original is
        authoritative, and the loader that wrote the mirror says so."""
        assert FAMILY_MEMBERSHIP_DIRECTION == "MEMBER_OF_FAMILY"
        assert FAMILY_MEMBERSHIP_MIRROR == "HAS_FORMULA"

    def test_no_family_query_traverses_both_directions(self) -> None:
        """Read as source text, because this is the defect that cannot be caught by a
        response assertion on a family whose two counts happen to agree."""
        from vedagraph.api.services import formula_service

        for name in dir(formula_service):
            if not name.endswith("_CYPHER"):
                continue
            cypher = getattr(formula_service, name)
            assert isinstance(cypher, str)
            uses_mirror = FAMILY_MEMBERSHIP_MIRROR in cypher
            uses_direct = FAMILY_MEMBERSHIP_DIRECTION in cypher
            assert not (uses_mirror and uses_direct), (
                f"{name} traverses both directions of one membership and will double-count"
            )
            assert not uses_mirror, f"{name} traverses the mirror instead of the original"

    def test_the_path_whitelist_carries_exactly_one_direction(self) -> None:
        assert (FAMILY_MEMBERSHIP_MIRROR in PATH_RELATIONSHIPS) != (
            FAMILY_MEMBERSHIP_DIRECTION in PATH_RELATIONSHIPS
        )

    def test_the_role_vocabulary_excludes_secondary_core(self) -> None:
        """157 families record a ``secondary_core_count`` and no edge carries the role, so
        the API must not invent a fourth bucket a client would then add up."""
        assert MEMBERSHIP_ROLES == ("CORE", "EXPANSION", "VARIANT")
        assert "SECONDARY_CORE" not in MEMBERSHIP_ROLES


class TestRouteContracts:
    def test_unknown_formula_is_404_with_a_hint(self, formula_client: TestClient) -> None:
        response = formula_client.get("/api/v1/formulas/VG:ENRICH:FORMULA:nope")
        assert response.status_code == 404
        body = response.json()
        assert body["error"] == "ENTITY_NOT_FOUND"
        assert body["hint"]
        assert_no_leaks(body)

    def test_unknown_family_is_404_with_a_hint(self, formula_client: TestClient) -> None:
        response = formula_client.get("/api/v1/formula-families/VG:ENRICH:FORMULA-FAMILY:nope")
        assert response.status_code == 404
        assert response.json()["hint"]

    def test_ids_travel_bound_and_are_never_interpolated(
        self, formula_client: TestClient, fake_repository: FakeRepository
    ) -> None:
        # No "//" in the payload: a URL path collapses it, and the point of this test is
        # what the driver received, not what the router normalised.
        hostile = "x' }) DETACH DELETE n RETURN 1"
        formula_client.get(f"/api/v1/formulas/{hostile}")
        assert "DETACH DELETE" not in fake_repository.query_text
        assert hostile in fake_repository.all_parameters.values()

    def test_graph_down_is_503_without_a_hostname(self) -> None:
        app, client = build_client(FakeRepository(unavailable=True))
        app.include_router(formulas.router, prefix="/api/v1")
        with client:
            app.state.repository = FakeRepository(unavailable=True)
            for url in (
                f"/api/v1/formulas/{PATA_SVASTIBHIH}",
                f"/api/v1/formula-families/{VISVA_BHUVANA}",
            ):
                response = client.get(url)
                assert response.status_code == 503
                body = json.dumps(response.json()).lower()
                for needle in ("bolt", "localhost", "7687", "neo4j", "127.0.0.1", "password"):
                    assert needle not in body


# ---------------------------------------------------------------------------
# Live graph
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
class TestLiveDoubleCount:
    def test_both_directions_still_carry_the_same_memberships(
        self, live_repository: Neo4jRepository
    ) -> None:
        """The premise of the whole contract, re-measured: if the mirror ever stopped
        matching, choosing a direction would stop being a free choice."""
        row = live_repository.run_one(
            f"MATCH ()-[a:{FAMILY_MEMBERSHIP_DIRECTION}]->() "
            "WITH count(a) AS inbound "
            f"MATCH ()-[b:{FAMILY_MEMBERSHIP_MIRROR}]->() "
            "RETURN inbound, count(b) AS outbound"
        )
        assert row is not None
        assert int(row["inbound"]) == int(row["outbound"])

    def test_traversing_both_directions_would_double_count_every_family(
        self, live_repository: Neo4jRepository
    ) -> None:
        """The measurement the caveat quotes, asserted rather than trusted: following both
        gives exactly twice the recorded member count, on all 720 families."""
        row = live_repository.run_one(
            "MATCH (ff:FormulaFamily) "
            f"OPTIONAL MATCH (:Formula)-[m:{FAMILY_MEMBERSHIP_DIRECTION}]->(ff) "
            f"OPTIONAL MATCH (ff)-[h:{FAMILY_MEMBERSHIP_MIRROR}]->(:Formula) "
            "WITH ff, count(DISTINCT m) + count(DISTINCT h) AS both, ff.member_count AS recorded "
            "RETURN count(*) AS families, "
            "sum(CASE WHEN both = 2 * recorded THEN 1 ELSE 0 END) AS doubled"
        )
        assert row is not None
        assert int(row["families"]) == int(row["doubled"]) > 0

    def test_the_authoritative_direction_reconciles_for_every_family(
        self, live_repository: Neo4jRepository
    ) -> None:
        row = live_repository.run_one(
            "MATCH (ff:FormulaFamily) "
            f"OPTIONAL MATCH (:Formula)-[m:{FAMILY_MEMBERSHIP_DIRECTION}]->(ff) "
            "WITH ff, count(m) AS traversed "
            "WHERE traversed <> ff.member_count "
            "RETURN count(*) AS disagreeing"
        )
        assert row is not None
        assert int(row["disagreeing"]) == 0

    def test_secondary_core_is_a_subset_of_core_and_not_a_fourth_role(
        self, live_repository: Neo4jRepository
    ) -> None:
        """Both halves: the three roles sum to the member count, and adding the fourth
        number breaks it -- which is why the API reports it and never sums it."""
        row = live_repository.run_one(
            "MATCH (ff:FormulaFamily) "
            "RETURN count(*) AS families, "
            "sum(CASE WHEN ff.core_count + ff.expansion_count + ff.variant_count "
            "  = ff.member_count THEN 1 ELSE 0 END) AS three_roles_sum, "
            "sum(CASE WHEN ff.secondary_core_count > 0 THEN 1 ELSE 0 END) AS with_secondary"
        )
        assert row is not None
        assert int(row["three_roles_sum"]) == int(row["families"])
        assert int(row["with_secondary"]) > 0, (
            "no family records a secondary core any more; the caveat about it is now stale"
        )
        roles = live_repository.run(
            f"MATCH ()-[m:{FAMILY_MEMBERSHIP_DIRECTION}]->() RETURN DISTINCT m.role AS role"
        )
        assert {row_["role"] for row_ in roles} <= set(MEMBERSHIP_ROLES)


@pytest.mark.neo4j
class TestLiveFamilyDetail:
    def test_the_demo_family_returns_representative_core_and_expansions(
        self, live_formula_client: TestClient
    ) -> None:
        response = live_formula_client.get(f"/api/v1/formula-families/{VISVA_BHUVANA}")
        assert response.status_code == 200
        body = response.json()
        assert body["type"] == "FORMULA_FAMILY"
        assert body["representative_display_form"]
        assert body["core"], "a family always has at least one core member"
        assert body["expansions"]
        assert body["veda_span"] == 4
        assert set(body["vedas"]) == {"RV", "SV", "YV", "AV"}
        assert set(body["occurrences_by_veda"]) == {"RV", "SV", "YV", "AV"}
        assert all(isinstance(count, int) for count in body["occurrences_by_veda"].values())
        assert body["occurrences"], "a family's passage occurrences must be listed"
        assert_no_leaks(body)

    def test_the_response_reconciles_traversal_against_the_recorded_counts(
        self, live_formula_client: TestClient
    ) -> None:
        body = live_formula_client.get(f"/api/v1/formula-families/{VISVA_BHUVANA}").json()
        reconciliation = body["reconciliation"]
        assert reconciliation["direction_traversed"] == FAMILY_MEMBERSHIP_DIRECTION
        assert reconciliation["agrees"] is True
        assert reconciliation["traversed_member_count"] == body["member_count"]
        assert reconciliation["traversed_core_count"] == body["core_count"]
        assert reconciliation["traversed_expansion_count"] == body["expansion_count"]
        assert reconciliation["traversed_variant_count"] == body["variant_count"]
        # And the traversal is not double counted: the three role lists sum to the recorded
        # member count, not to twice it.
        assert (
            len(body["core"]) + len(body["expansions"]) + len(body["variants"])
            == body["member_count"]
        )

    def test_every_family_reconciles_and_none_double_counts(
        self, live_formula_client: TestClient, live_repository: Neo4jRepository
    ) -> None:
        """A sample across the layer rather than one family, because a single family whose
        counts happen to agree proves nothing about the direction chosen."""
        rows = live_repository.run(
            "MATCH (ff:FormulaFamily) RETURN ff.family_id AS id, ff.member_count AS members "
            "ORDER BY ff.member_count DESC LIMIT 12"
        )
        assert rows
        for row in rows:
            body = live_formula_client.get(f"/api/v1/formula-families/{row['id']}").json()
            members = len(body["core"]) + len(body["expansions"]) + len(body["variants"])
            assert body["reconciliation"]["agrees"] is True, row["id"]
            assert members == int(row["members"]), (
                f"{row['id']} traversed {members} members against a recorded {row['members']}"
            )
            assert members <= MAX_FAMILY_MEMBERS

    def test_the_direction_contract_is_disclosed_in_the_payload(
        self, live_formula_client: TestClient
    ) -> None:
        body = live_formula_client.get(f"/api/v1/formula-families/{VISVA_BHUVANA}").json()
        text = " ".join(caveat["text"] for caveat in body["caveats"])
        assert FAMILY_MEMBERSHIP_DIRECTION in text
        assert FAMILY_MEMBERSHIP_MIRROR in text
        assert "twice" in text

    def test_a_family_with_a_secondary_core_says_it_must_not_be_summed(
        self, live_formula_client: TestClient, live_repository: Neo4jRepository
    ) -> None:
        row = live_repository.run_one(
            "MATCH (ff:FormulaFamily) WHERE ff.secondary_core_count > 0 "
            "RETURN ff.family_id AS id LIMIT 1"
        )
        assert row is not None
        body = live_formula_client.get(f"/api/v1/formula-families/{row['id']}").json()
        assert body["secondary_core_count"] > 0
        assert body["reconciliation"]["agrees"] is True
        text = " ".join(caveat["text"] for caveat in body["caveats"])
        assert "SUBSET of core_count" in text

    def test_a_similarity_derived_variant_is_labelled_and_caveated(
        self, live_formula_client: TestClient, live_repository: Neo4jRepository
    ) -> None:
        """Four of 2,037 memberships rest on string similarity. They are the only rows in
        the layer where membership is an inference, so they must not read like the rest."""
        row = live_repository.run_one(
            f"MATCH ()-[m:{FAMILY_MEMBERSHIP_DIRECTION}]->(ff:FormulaFamily) "
            "WHERE m.quality_tier = 'TIER_D' AND m.role = 'VARIANT' "
            "RETURN ff.family_id AS id LIMIT 1"
        )
        assert row is not None
        body = live_formula_client.get(f"/api/v1/formula-families/{row['id']}").json()
        assert body["variants"]
        variant = body["variants"][0]
        assert variant["quality_tier"] == "TIER_D"
        assert variant["similarity"] is not None and 0 < variant["similarity"] < 1
        text = " ".join(caveat["text"] for caveat in body["caveats"])
        assert "TIER_D" in text
        assert "inference" in text

    def test_member_reach_is_the_members_own_and_not_the_familys(
        self, live_formula_client: TestClient
    ) -> None:
        """The trap the frozen ``formula_family_profile`` caveat names: a member's Vedas are
        where that wording occurs, not where the family does."""
        body = live_formula_client.get(f"/api/v1/formula-families/{VISVA_BHUVANA}").json()
        narrower = [
            member
            for member in body["expansions"]
            if member["vedas"] and set(member["vedas"]) != set(body["vedas"])
        ]
        assert narrower, "at least one member reaches fewer corpora than its family"
        for member in body["core"] + body["expansions"] + body["variants"]:
            assert set(member["vedas"]) <= set(body["vedas"])
            assert member["passage_count"] is not None

    def test_occurrence_truncation_is_declared(self, live_formula_client: TestClient) -> None:
        body = live_formula_client.get(f"/api/v1/formula-families/{VISVA_BHUVANA}").json()
        assert len(body["occurrences"]) <= MAX_OCCURRENCES
        if body["occurrence_count"] > len(body["occurrences"]):
            assert body["occurrences_truncated"] is True
            assert any("bounded" in caveat["text"] for caveat in body["caveats"])


@pytest.mark.neo4j
class TestLiveFormulaDetail:
    def test_the_widest_spread_formula_reports_its_reach_per_corpus(
        self, live_formula_client: TestClient
    ) -> None:
        response = live_formula_client.get(f"/api/v1/formulas/{PATA_SVASTIBHIH}")
        assert response.status_code == 200
        body = response.json()
        assert body["type"] == "FORMULA"
        assert body["display_form"]
        assert body["cross_veda"] is True
        assert body["occurrence_count"] == sum(body["occurrences_by_veda"].values()), (
            "the per-corpus counts must reconcile with the total, or one of them is stale"
        )
        assert set(body["occurrences_by_veda"]) == {"RV", "SV", "YV", "AV"}
        assert body["families"], "this formula is the core of its own family"
        assert body["families"][0]["role"] in MEMBERSHIP_ROLES
        assert len(body["families"]) <= MAX_FAMILIES_PER_FORMULA
        assert_no_leaks(body)

    def test_a_cross_veda_formula_carries_the_diction_caveat(
        self, live_formula_client: TestClient
    ) -> None:
        body = live_formula_client.get(f"/api/v1/formulas/{PATA_SVASTIBHIH}").json()
        text = " ".join(caveat["text"] for caveat in body["caveats"])
        assert "normalised-string match" in text
        assert "shared DICTION" in text
        assert "drawn " in text and "Rigveda" in text

    def test_occurrences_carry_the_wording_the_passage_actually_has(
        self, live_formula_client: TestClient
    ) -> None:
        body = live_formula_client.get(f"/api/v1/formulas/{PATA_SVASTIBHIH}").json()
        assert body["occurrences"]
        for occurrence in body["occurrences"]:
            assert occurrence["passage_id"].startswith("VG:")
            assert occurrence["veda"] in {"RV", "SV", "YV", "AV"}
        assert any(occurrence["source_form"] for occurrence in body["occurrences"])

    def test_the_formula_evidence_never_reports_a_confidence(
        self, live_formula_client: TestClient
    ) -> None:
        """Neither node type carries a ``confidence`` property; a family's ``score`` is its
        representative coverage, and the graph's own note says it is not a probability."""
        for url in (
            f"/api/v1/formulas/{PATA_SVASTIBHIH}",
            f"/api/v1/formula-families/{VISVA_BHUVANA}",
        ):
            body = live_formula_client.get(url).json()
            assert body["evidence"]["confidence"] is None
            assert body["evidence"]["method"], url

    def test_only_the_family_carries_a_tier(self, live_formula_client: TestClient) -> None:
        """A ``Formula`` node has no ``quality_tier`` and a ``FormulaFamily`` does, so the
        formula returns null rather than borrowing its family's grade. Two formulas in one
        family are not equally well attested, and inheriting the family tier would say they
        were."""
        formula = live_formula_client.get(f"/api/v1/formulas/{PATA_SVASTIBHIH}").json()
        family = live_formula_client.get(f"/api/v1/formula-families/{VISVA_BHUVANA}").json()
        assert formula["evidence"]["tier"] is None
        assert family["evidence"]["tier"] == "TIER_B"

    def test_a_family_score_is_reported_with_the_graphs_own_note(
        self, live_formula_client: TestClient
    ) -> None:
        body = live_formula_client.get(f"/api/v1/formula-families/{VISVA_BHUVANA}").json()
        assert body["representative_coverage"] is not None
        assert body["notes"] and "not a probability" in body["notes"].lower()


@pytest.mark.neo4j
class TestLivePerformance:
    def test_both_detail_endpoints_are_point_reads(
        self, live_formula_client: TestClient, untraced_measurement: UntracedBlock
    ) -> None:
        """150 ms is the product's number, so it is read without the coverage tracer.

        The budget is read with the coverage tracer paused; see the
        ``untraced_measurement`` fixture for why that is not cosmetic.
        """
        for label, url in (
            ("formula", f"/api/v1/formulas/{PATA_SVASTIBHIH}"),
            ("family", f"/api/v1/formula-families/{VISVA_BHUVANA}"),
        ):
            timings: list[float] = []
            with untraced_measurement():
                for _ in range(5):
                    started = time.perf_counter()
                    assert live_formula_client.get(url).status_code == 200
                    timings.append((time.perf_counter() - started) * 1000)
            # Traced, and after the measurement: coverage, not a warm-up.
            assert live_formula_client.get(url).status_code == 200
            timings.sort()
            median = timings[len(timings) // 2]
            assert median < 150, f"{label}: median {median:.0f} ms"

    def test_the_payloads_are_bounded(self, live_formula_client: TestClient) -> None:
        for url in (
            f"/api/v1/formulas/{PATA_SVASTIBHIH}",
            f"/api/v1/formula-families/{VISVA_BHUVANA}",
        ):
            body = live_formula_client.get(url).json()
            assert len(json.dumps(body)) < 120_000
