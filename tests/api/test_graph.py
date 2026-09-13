"""Tests for the graph exploration surface.

Two kinds, and they answer different questions.

The **offline** tests are contract tests: that a relationship token round-trips and is not a
Neo4j id, that an injected relationship type is a 400 and not an empty graph, that an
out-of-range depth is a 422, that a dead database is a 503 whose body names no hostname.
None of them needs Vedic data and running them against a live graph would only make them
slower and less deterministic.

The **live** tests, marked ``neo4j``, assert the things a mock cannot falsify, and each one
exists because a design decision here rests on a measurement that a rebuild could
invalidate. That no traversable predicate touches an internal node is the *only* reason
``include_internal=true`` is safe. That ``(source, type, target)`` is a key is the only
reason the endpoint-triple token is an identity. That five predicates carry a constant
confidence is the only reason those five return null. If any of those stops being true, the
right outcome is a failing test naming it, not a response that quietly means something else.
"""

from __future__ import annotations

import json
import time
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import FakeRepository, UntracedBlock
from vedagraph.api.errors import BadRequestError
from vedagraph.api.models.graph import RelationshipIdBasis
from vedagraph.api.repositories.neo4j_repository import Neo4jRepository
from vedagraph.api.services.graph_service import (
    DISCLOSABLE_EXCLUDED_TYPES,
    FORBIDDEN_METADATA_KEYS,
    HUB_DEGREE_CEILING,
    LEMMA_RELATIONSHIP,
    NEIGHBOURHOOD_MAX_DEPTH,
    NODE_METADATA_KEYS,
    NON_TRAVERSABLE_REASONS,
    PATH_MAX_DEPTH,
    PATH_RELATIONSHIPS,
    PIPELINE_CONSTANT_PREDICATES,
    PREDICATE_SEMANTICS,
    PRODUCT_TYPE_BY_DISPLAY_TYPE,
    TRAVERSABLE_RELATIONSHIPS,
    decode_relationship_id,
    encode_relationship_id,
)

INDRA = "VG:DEVATA:INDRAH"
AGNI = "VG:DEVATA:AGNIH"
RV_FIRST = "VG:RV:SAK:M01:S001:V001"
SV_FIRST = "VG:SV:KAU:CHANDA:P01:D01:V01"
ALTAR = "VG:CONCEPT:VEDI-ALTAR"
GAYATRI = "VG:CHANDAS:GAYATRI"
VISVA_BHUVANA = "VG:ENRICH:FORMULA-FAMILY:709faeaecdc5a79716fa565ce0a051f0"
#: The one UNSPECIFIED entry in the Anukramani's devata slot. It is a dog.
THE_DOG = "VG:DEVATA:SUNAH"
#: A HUMAN entry and a PATRON_PRAISE entry, both with real traversable degree, so both
#: can be reached as a root and as a neighbour rather than only looked up directly.
VASISTHA_THE_PATRON = "VG:DEVATA:VASISTHAH"
GIFT_PRAISE = "VG:DEVATA:DANASTUTIH"

#: Substrings that must never appear in a serialized response body. ``element_id`` and
#: ``elementId`` are the Neo4j identity leak; the rest are Cypher, build state and
#: connection details.
FORBIDDEN_IN_BODY = (
    "element_id",
    "elementId",
    "QAIssue",
    "qa_issue",
    "issue_id",
    "MATCH (",
    "OPTIONAL MATCH",
    "RETURN ",
    "bolt://",
    "neo4j",
    "run_id",
    "pipeline_version",
    "prompt_policy",
    "build_pass",
    "reviewer_model",
)


def assert_no_leaks(payload: Any) -> None:
    """Assert on the SERIALIZED body, not on the model.

    Deliberately a string search over the JSON rather than a walk over model fields: the
    leak this guards against is a property copied into a free-form ``metadata`` map or
    embedded in a caveat sentence, and a field-by-field check would not see either.
    """
    body = json.dumps(payload, ensure_ascii=False)
    for needle in FORBIDDEN_IN_BODY:
        assert needle not in body, f"{needle!r} leaked into a response body"
    for needle in FORBIDDEN_METADATA_KEYS:
        assert f'"{needle}"' not in body, f"build-state key {needle!r} leaked"


# ---------------------------------------------------------------------------
# Relationship identity: offline, and the heart of spec section 25
# ---------------------------------------------------------------------------


class TestRelationshipIdentity:
    def test_endpoint_triple_round_trips(self) -> None:
        token, basis = encode_relationship_id(
            relationship_type="HAS_RISHI",
            domain_id=None,
            source_id=RV_FIRST,
            target_id="VG:RISHI:MADHUCCHANDAH",
        )
        assert basis is RelationshipIdBasis.ENDPOINT_TRIPLE
        decoded = decode_relationship_id(token, allowed_types=TRAVERSABLE_RELATIONSHIPS)
        assert decoded.basis is RelationshipIdBasis.ENDPOINT_TRIPLE
        assert decoded.relationship_type == "HAS_RISHI"
        assert decoded.source_id == RV_FIRST
        assert decoded.target_id == "VG:RISHI:MADHUCCHANDAH"
        assert decoded.domain_id is None

    def test_domain_id_round_trips(self) -> None:
        token, basis = encode_relationship_id(
            relationship_type="MENTIONS_DEVATA",
            domain_id="VG:ENRICH:THEONYM-MENTION:418e54f1ced1cf50c704b2f78e71e66f",
            source_id=RV_FIRST,
            target_id=INDRA,
        )
        assert basis is RelationshipIdBasis.DOMAIN_ID
        decoded = decode_relationship_id(token, allowed_types=TRAVERSABLE_RELATIONSHIPS)
        assert decoded.domain_id == "VG:ENRICH:THEONYM-MENTION:418e54f1ced1cf50c704b2f78e71e66f"
        assert decoded.source_id is None

    def test_token_is_not_a_neo4j_id(self) -> None:
        """A token must not be mistakable for, or coincide with, a Neo4j identifier."""
        token, _ = encode_relationship_id(
            relationship_type="HAS_DEVATA", domain_id=None, source_id=RV_FIRST, target_id=INDRA
        )
        assert not token.isdigit()
        assert ":" not in token, "a bare element_id contains colons; a token must not look like one"
        assert token.startswith("r1-")
        # An element_id is either an integer string or `4:<uuid>:<n>`; neither decodes.
        for neo4j_shaped in ("0", "4123", "4:9d2c1f0e-0000-0000-0000-000000000000:17"):
            with pytest.raises(BadRequestError):
                decode_relationship_id(neo4j_shaped, allowed_types=TRAVERSABLE_RELATIONSHIPS)

    def test_ids_carrying_the_delimiter_are_refused_at_mint_time(self) -> None:
        """Ten ``DerivedMetric.metric_id`` values contain a pipe, which is why the delimiter
        is a control character -- and why minting still checks."""
        with pytest.raises(ValueError, match="separator character"):
            encode_relationship_id(
                relationship_type="MEASURES",
                domain_id=None,
                source_id="VG:METRIC:X\x1fY",
                target_id=INDRA,
            )

    @pytest.mark.parametrize(
        "token",
        [
            "",
            "123456",
            "r1-",
            "r1-!!!!",
            "r1-" + "A" * 9,
            "notaprefix-abcdef",
            "r2-RE9NQUlOX0lE",
        ],
    )
    def test_malformed_tokens_are_refused(self, token: str) -> None:
        with pytest.raises(BadRequestError) as caught:
            decode_relationship_id(token, allowed_types=TRAVERSABLE_RELATIONSHIPS)
        assert caught.value.status_code == 400

    def test_a_token_naming_a_non_whitelisted_type_is_refused(self) -> None:
        token, _ = encode_relationship_id(
            relationship_type="QA_ISSUE_ON", domain_id=None, source_id="a", target_id="b"
        )
        with pytest.raises(BadRequestError) as caught:
            decode_relationship_id(token, allowed_types=TRAVERSABLE_RELATIONSHIPS)
        assert caught.value.status_code == 400

    def test_membership_tokens_differ_between_the_two_directions(self) -> None:
        """``membership_id`` is shared by ``MEMBER_OF_FAMILY`` and its ``HAS_FORMULA``
        mirror, so a token that carried only the id would be ambiguous between two edges."""
        shared = "VG:ENRICH:FORMULA-FAMILY-MEMBER:106bcc014ce1a886db05747b36dad39b"
        inward, _ = encode_relationship_id(
            relationship_type="MEMBER_OF_FAMILY", domain_id=shared, source_id="a", target_id="b"
        )
        outward, _ = encode_relationship_id(
            relationship_type="HAS_FORMULA", domain_id=shared, source_id="b", target_id="a"
        )
        assert inward != outward
        assert (
            decode_relationship_id(
                inward, allowed_types=TRAVERSABLE_RELATIONSHIPS
            ).relationship_type
            == "MEMBER_OF_FAMILY"
        )
        assert (
            decode_relationship_id(
                outward, allowed_types=TRAVERSABLE_RELATIONSHIPS
            ).relationship_type
            == "HAS_FORMULA"
        )

    def test_non_ascii_ids_survive_the_round_trip(self) -> None:
        """``VG:EPITHET:DASRĀ`` is a real id, and base64url of UTF-8 is why it is safe in a
        URL path."""
        token, _ = encode_relationship_id(
            relationship_type="HAS_EPITHET",
            domain_id=None,
            source_id=INDRA,
            target_id="VG:EPITHET:HAVYAVĀHANA",
        )
        assert token.isascii()
        decoded = decode_relationship_id(token, allowed_types=TRAVERSABLE_RELATIONSHIPS)
        assert decoded.target_id == "VG:EPITHET:HAVYAVĀHANA"


# ---------------------------------------------------------------------------
# Whitelists and constants: offline invariants
# ---------------------------------------------------------------------------


class TestWhitelists:
    def test_every_traversable_predicate_has_an_explanation(self) -> None:
        """The point of the explain endpoint is the sentence, so a predicate without one is
        a predicate that would ship a bare edge."""
        missing = (TRAVERSABLE_RELATIONSHIPS | {LEMMA_RELATIONSHIP}) - set(PREDICATE_SEMANTICS)
        assert missing == set()

    def test_explanations_state_a_limit(self) -> None:
        for name, semantics in PREDICATE_SEMANTICS.items():
            assert semantics.limit.strip(), f"{name} has no stated limit"
            assert semantics.asserts.strip(), f"{name} has no stated assertion"

    def test_path_whitelist_excludes_the_plumbing(self) -> None:
        for excluded in (
            "CONTAINS",
            "HAS_TEXT_VERSION",
            "HAS_TRANSLATION",
            "MENTIONS_LEMMA",
            "QA_ISSUE_ON",
            "ASSERTION_PREDICATE",
            "ASSERTION_AGENT",
            "ASSERTION_TARGET",
        ):
            assert excluded not in PATH_RELATIONSHIPS
            assert excluded not in TRAVERSABLE_RELATIONSHIPS
            assert excluded in NON_TRAVERSABLE_REASONS

    def test_path_whitelist_does_not_carry_both_halves_of_a_family_membership(self) -> None:
        """Both directions are the same 2,037 memberships; a path could otherwise bounce."""
        assert "HAS_FORMULA" in PATH_RELATIONSHIPS
        assert "MEMBER_OF_FAMILY" not in PATH_RELATIONSHIPS

    def test_metadata_whitelist_and_forbidden_set_are_disjoint(self) -> None:
        assert NODE_METADATA_KEYS.isdisjoint(FORBIDDEN_METADATA_KEYS)

    def test_the_disclosable_exclusions_never_name_the_qa_predicate(self) -> None:
        """An empty neighbourhood reports the degree it did NOT traverse, and that report
        must not count a node's QA findings: how many doubts this repository's build holds
        about a passage is build state, not Vedic knowledge. The set is derived from the
        exclusions rather than retyped, so a predicate added later is disclosed
        automatically while this one stays out by construction."""
        assert "QA_ISSUE_ON" not in DISCLOSABLE_EXCLUDED_TYPES
        assert set(DISCLOSABLE_EXCLUDED_TYPES) == set(NON_TRAVERSABLE_REASONS) - {"QA_ISSUE_ON"}
        assert "CONTAINS" in DISCLOSABLE_EXCLUDED_TYPES


# ---------------------------------------------------------------------------
# Route contracts: offline, against the fake repository
# ---------------------------------------------------------------------------


class TestRouteContracts:
    @pytest.mark.parametrize(
        "hostile",
        ["HAS_RISHI]->() DETACH DELETE n //", "FOO", "has_rishi", "*", "HAS_RISHI|CONTAINS"],
    )
    def test_relationship_type_injection_is_refused_with_400(
        self, client: TestClient, hostile: str
    ) -> None:
        response = client.get(f"/api/v1/graph/neighborhood/{INDRA}", params={"types": hostile})
        assert response.status_code == 400
        body = response.json()
        assert body["error"] == "BAD_REQUEST"
        assert hostile in body["detail"], "the client must see which value was refused"
        assert_no_leaks(body)

    def test_an_injected_type_never_reaches_the_driver(
        self, client: TestClient, fake_repository: FakeRepository
    ) -> None:
        """A 400 is not enough on its own: the refusal has to happen before any query.

        Validation therefore precedes node resolution, which is also why this is a 400 and
        not a 404 -- the fake repository resolves nothing, so an implementation that
        resolved first would answer 404 here and hide that the type was refused."""
        response = client.get(
            f"/api/v1/graph/neighborhood/{INDRA}",
            params={"types": "HAS_RISHI]->() DETACH DELETE n //"},
        )
        assert response.status_code == 400
        assert fake_repository.calls == [], "no query may run before the type is validated"
        assert "DETACH DELETE" not in fake_repository.query_text

    @pytest.mark.parametrize("depth", [0, 3, 7, -1])
    def test_out_of_range_neighbourhood_depth_is_422(self, client: TestClient, depth: int) -> None:
        response = client.get(f"/api/v1/graph/neighborhood/{INDRA}", params={"depth": depth})
        assert response.status_code == 422
        assert "depth" in response.json()["detail"]

    @pytest.mark.parametrize("depth", [0, PATH_MAX_DEPTH + 1, 99])
    def test_out_of_range_path_depth_is_422(self, client: TestClient, depth: int) -> None:
        response = client.get(
            "/api/v1/graph/path", params={"from": INDRA, "to": AGNI, "max_depth": depth}
        )
        assert response.status_code == 422
        assert "max_depth" in response.json()["detail"]

    def test_limit_per_type_above_the_configured_bound_is_422(self, client: TestClient) -> None:
        response = client.get(f"/api/v1/graph/neighborhood/{INDRA}", params={"limit_per_type": 500})
        assert response.status_code == 422

    def test_min_confidence_outside_zero_to_one_is_422(self, client: TestClient) -> None:
        for value in (-0.1, 1.1):
            response = client.get(
                f"/api/v1/graph/neighborhood/{INDRA}", params={"min_confidence": value}
            )
            assert response.status_code == 422

    def test_unknown_trust_tier_is_422(self, client: TestClient) -> None:
        response = client.get(
            f"/api/v1/graph/neighborhood/{INDRA}", params={"trust_tier": "TIER_Z"}
        )
        assert response.status_code == 422

    def test_unknown_node_id_is_404_with_a_useful_hint(self, client: TestClient) -> None:
        """Never an empty graph: 'no such thing' and 'that thing has no links' differ."""
        response = client.get("/api/v1/graph/neighborhood/NOT-A-REAL-ID")
        assert response.status_code == 404
        body = response.json()
        assert body["error"] == "ENTITY_NOT_FOUND"
        assert body["hint"] and "VG:" in body["hint"]
        assert_no_leaks(body)

    def test_a_neo4j_id_as_a_relationship_id_is_400(self, client: TestClient) -> None:
        response = client.get("/api/v1/graph/relationships/123456")
        assert response.status_code == 400
        assert_no_leaks(response.json())

    def test_a_malformed_relationship_id_is_400_not_500(self, client: TestClient) -> None:
        for token in ("r1-!!!!", "r1-QUJD", "garbage"):
            response = client.get(f"/api/v1/graph/relationships/{token}")
            assert response.status_code == 400, token

    def test_a_wellformed_token_for_a_missing_edge_is_404(self, client: TestClient) -> None:
        token, _ = encode_relationship_id(
            relationship_type="HAS_RISHI", domain_id=None, source_id="a", target_id="b"
        )
        response = client.get(f"/api/v1/graph/relationships/{token}")
        assert response.status_code == 404

    def test_path_requires_both_endpoints(self, client: TestClient) -> None:
        assert client.get("/api/v1/graph/path", params={"from": INDRA}).status_code == 422
        assert client.get("/api/v1/graph/path", params={"to": INDRA}).status_code == 422


class TestGraphDown:
    """A dead database is a 503 and the body says nothing about the deployment."""

    @pytest.mark.parametrize(
        "url",
        [
            f"/api/v1/graph/neighborhood/{INDRA}",
            "/api/v1/graph/path?from=VG:DEVATA:INDRAH&to=VG:DEVATA:AGNIH",
        ],
    )
    def test_graph_down_is_503_without_a_hostname(self, down_client: TestClient, url: str) -> None:
        response = down_client.get(url)
        assert response.status_code == 503
        body = response.json()
        assert body["error"] == "KNOWLEDGE_GRAPH_UNAVAILABLE"
        for needle in ("bolt", "localhost", "7687", "neo4j", "127.0.0.1", "password"):
            assert needle not in json.dumps(body).lower()

    def test_relationship_explain_is_503_when_the_graph_is_down(
        self, down_client: TestClient
    ) -> None:
        token, _ = encode_relationship_id(
            relationship_type="HAS_RISHI", domain_id=None, source_id="a", target_id="b"
        )
        response = down_client.get(f"/api/v1/graph/relationships/{token}")
        assert response.status_code == 503
        assert "bolt" not in json.dumps(response.json()).lower()


# ---------------------------------------------------------------------------
# Live graph
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
class TestLiveInvariants:
    """The measurements the design rests on, re-measured.

    Each of these is load-bearing. The endpoint-triple token is only an identity because the
    triple is a key; ``include_internal`` is only safe because no traversable predicate
    reaches an internal node; the five constant-confidence predicates only return null
    because their confidence really is constant. A rebuild that changed any of them would
    otherwise produce responses that are quietly wrong rather than loudly broken.
    """

    def test_source_type_target_is_a_key_for_every_traversable_predicate(
        self, live_repository: Neo4jRepository
    ) -> None:
        pattern = "|".join(sorted(TRAVERSABLE_RELATIONSHIPS))
        row = live_repository.run_one(
            f"MATCH (a)-[r:{pattern}]->(b) "
            "WITH a, b, type(r) AS t, count(*) AS c "
            "RETURN max(c) AS worst"
        )
        assert row is not None
        assert int(row["worst"]) == 1, (
            "the endpoint-triple relationship id assumes at most one edge per "
            "(source, type, target); it is no longer an identity"
        )

    def test_no_traversable_predicate_touches_an_internal_node(
        self, live_repository: Neo4jRepository
    ) -> None:
        pattern = "|".join(sorted(TRAVERSABLE_RELATIONSHIPS))
        row = live_repository.run_one(
            f"MATCH (a)-[r:{pattern}]->(b) "
            "WHERE a:Internal OR a:QAIssue OR a:TextVersion OR a:Translation OR a:Source "
            "OR a:SourceArtifact OR a:Lemma OR b:Internal OR b:QAIssue OR b:TextVersion "
            "OR b:Translation OR b:Source OR b:SourceArtifact OR b:Lemma "
            "RETURN count(*) AS leaking"
        )
        assert row is not None
        assert int(row["leaking"]) == 0, (
            "include_internal=false is enforced structurally by the whitelist; a "
            "traversable predicate now reaches an internal node and the flag no longer "
            "describes what the endpoint can return"
        )

    def test_every_traversable_endpoint_has_a_stable_product_id(
        self, live_repository: Neo4jRepository
    ) -> None:
        pattern = "|".join(sorted(TRAVERSABLE_RELATIONSHIPS))
        row = live_repository.run_one(
            f"MATCH (a)-[r:{pattern}]->(b) "
            "WITH coalesce(a.canonical_key, a.entity_key, a.formula_id, a.family_id, "
            "  a.epithet_key, a.axis_key, a.family_key, a.group_key, a.metric_id, "
            "  a.claim_id, a.work_id, a.assertion_id, a.lemma, a.predicate) AS ka, "
            "  coalesce(b.canonical_key, b.entity_key, b.formula_id, b.family_id, "
            "  b.epithet_key, b.axis_key, b.family_key, b.group_key, b.metric_id, "
            "  b.claim_id, b.work_id, b.assertion_id, b.lemma, b.predicate) AS kb "
            "WHERE ka IS NULL OR kb IS NULL RETURN count(*) AS unidentifiable"
        )
        assert row is not None
        assert int(row["unidentifiable"]) == 0

    def test_the_pipeline_constant_predicates_are_still_constant(
        self, live_repository: Neo4jRepository
    ) -> None:
        for predicate, expected in PIPELINE_CONSTANT_PREDICATES.items():
            rows = live_repository.run(
                f"MATCH ()-[r:{predicate}]->() "
                "RETURN count(DISTINCT r.confidence) AS distinct_values, "
                "collect(DISTINCT r.confidence)[0] AS value"
            )
            assert rows, predicate
            assert int(rows[0]["distinct_values"]) == 1, (
                f"{predicate} confidence is no longer a single constant, so returning null "
                "for it is now hiding a value that varies"
            )
            assert float(rows[0]["value"]) == expected

    def test_the_varying_confidence_predicates_still_vary(
        self, live_repository: Neo4jRepository
    ) -> None:
        """The other half of the same contract: a predicate listed as varying whose value
        collapsed to one constant would be returning an unearned confidence."""
        row = live_repository.run_one(
            "MATCH ()-[r]->() WHERE r.confidence IS NOT NULL "
            "WITH type(r) AS predicate, count(DISTINCT r.confidence) AS values "
            "WHERE values = 1 RETURN collect(predicate) AS constant_predicates"
        )
        assert row is not None
        measured = set(row["constant_predicates"])
        unclassified = measured - set(PIPELINE_CONSTANT_PREDICATES)
        # INVOLVES_SUBSTANCE (3 edges) and REFERS_TO_PLACE (1) are single-valued because
        # they are tiny, which is a sample size and not a pipeline constant; they are
        # documented as deliberately excluded.
        assert unclassified <= {"INVOLVES_SUBSTANCE", "REFERS_TO_PLACE"}, (
            f"a predicate's confidence became constant without being declared: {unclassified}"
        )

    def test_the_product_type_map_covers_every_display_type(
        self, live_repository: Neo4jRepository
    ) -> None:
        rows = live_repository.run(
            "MATCH (n) WHERE NOT n:Internal AND n.display_type IS NOT NULL "
            "RETURN DISTINCT n.display_type AS display_type"
        )
        missing = {row["display_type"] for row in rows} - set(PRODUCT_TYPE_BY_DISPLAY_TYPE)
        assert missing == set(), (
            f"a node type has no product type name and would fall back to a derived one: "
            f"{sorted(missing)}"
        )

    def test_the_hub_ceiling_still_sits_above_every_subject_class(
        self, live_repository: Neo4jRepository
    ) -> None:
        """Mantras, formulas and hymns must not be hubs, or the path endpoint would refuse
        to route through the very things a reader wants in a path."""
        for display_type in ("MANTRA", "Formula", "HYMN", "FormulaFamily"):
            row = live_repository.run_one(
                "MATCH (n) WHERE NOT n:Internal AND n.display_type = $display_type "
                "WITH n, COUNT { (n)--() } AS degree RETURN max(degree) AS worst",
                display_type=display_type,
            )
            assert row is not None
            assert int(row["worst"]) < HUB_DEGREE_CEILING, (
                f"{display_type} now reaches the hub ceiling, so paths would stop routing "
                "through it"
            )


@pytest.mark.neo4j
class TestLiveNeighbourhood:
    def test_indra_neighbourhood_is_bounded_and_declares_its_bounds(
        self, live_client: TestClient
    ) -> None:
        response = live_client.get(
            f"/api/v1/graph/neighborhood/{INDRA}", params={"limit_per_type": 25}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["root"]["type"] == "DEVATA"
        assert body["root"]["label"] == "Indra"
        assert body["root"]["id"] == INDRA
        bounds = body["bounds"]
        assert bounds["returned_edges"] == len(body["edges"])
        assert bounds["returned_nodes"] == len(body["nodes"])
        assert bounds["total_degree"] > bounds["returned_edges"], (
            "Indra is truncated by construction; a total equal to the returned count means "
            "the degree figure stopped being the untruncated one"
        )
        assert bounds["truncated_types"], "the truncated predicates must be named"
        # A truncated response must say so in words, not only in a number.
        assert any("bounded view" in caveat["text"] for caveat in body["caveats"])

    def test_the_node_and_edge_sets_are_closed(self, live_client: TestClient) -> None:
        """Every edge endpoint must be a node in the same payload, or a frontend draws
        edges into nothing."""
        body = live_client.get(f"/api/v1/graph/neighborhood/{INDRA}", params={"depth": 2}).json()
        ids = {node["id"] for node in body["nodes"]}
        for edge in body["edges"]:
            assert edge["source"] in ids, edge["source"]
            assert edge["target"] in ids, edge["target"]

    def test_no_response_body_carries_a_neo4j_identifier(self, live_client: TestClient) -> None:
        for url, params in [
            (f"/api/v1/graph/neighborhood/{INDRA}", {"depth": 2}),
            (f"/api/v1/graph/neighborhood/{RV_FIRST}", {"depth": 2}),
            (f"/api/v1/graph/neighborhood/{VISVA_BHUVANA}", {}),
            ("/api/v1/graph/path", {"from": GAYATRI, "to": ALTAR, "max_depth": 4}),
        ]:
            response = live_client.get(url, params=params)
            assert response.status_code == 200, url
            assert_no_leaks(response.json())

    @pytest.mark.parametrize("include_internal", [False, True])
    def test_qaissue_and_internal_never_appear_even_with_include_internal(
        self, live_client: TestClient, include_internal: bool
    ) -> None:
        """Spec section 24: never leak QAIssue. The flag can admit lemmas and nothing else."""
        for node_id in (INDRA, RV_FIRST):
            response = live_client.get(
                f"/api/v1/graph/neighborhood/{node_id}",
                params={"depth": 2, "include_internal": include_internal},
            )
            assert response.status_code == 200
            body = response.json()
            assert_no_leaks(body)
            types = {node["type"] for node in body["nodes"]}
            assert "QA_ISSUE" not in types
            assert "TRANSLATION" not in types
            assert "TEXT_VERSION" not in types
            if not include_internal:
                assert "LEMMA" not in types

    def test_include_internal_admits_lemmas_and_only_lemmas(self, live_client: TestClient) -> None:
        without = live_client.get(
            f"/api/v1/graph/neighborhood/{RV_FIRST}", params={"include_internal": False}
        ).json()
        with_lemmas = live_client.get(
            f"/api/v1/graph/neighborhood/{RV_FIRST}", params={"include_internal": True}
        ).json()
        added = {node["type"] for node in with_lemmas["nodes"]} - {
            node["type"] for node in without["nodes"]
        }
        assert added <= {"LEMMA"}, f"include_internal admitted more than lemmas: {added}"
        assert any(edge["type"] == LEMMA_RELATIONSHIP for edge in with_lemmas["edges"]), (
            "the flag did not actually reach the lexical layer"
        )
        assert any("include_internal=true" in c["text"] for c in with_lemmas["caveats"])

    def test_min_confidence_on_a_constant_predicate_is_disclosed_not_applied(
        self, live_client: TestClient
    ) -> None:
        """A threshold over HAS_DEVATA selects a pipeline branch. Those edges are kept, their
        confidence returns null, and the response says why."""
        response = live_client.get(
            f"/api/v1/graph/neighborhood/{INDRA}",
            params={"min_confidence": 0.99, "types": ["HAS_DEVATA"], "limit_per_type": 5},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["edges"], "a constant-confidence predicate must not be filtered away"
        for edge in body["edges"]:
            assert edge["confidence_basis"] == "PIPELINE_CONSTANT"
            assert edge["evidence"]["confidence"] is None, (
                "a constant must never be returned in a field named confidence"
            )
            assert edge["pipeline_prior"] == PIPELINE_CONSTANT_PREDICATES["HAS_DEVATA"]
        assert any("PIPELINE PRIOR" in caveat["text"] for caveat in body["caveats"])

    def test_min_confidence_is_applied_where_confidence_varies(
        self, live_client: TestClient
    ) -> None:
        body = live_client.get(
            f"/api/v1/graph/neighborhood/{RV_FIRST}",
            params={"min_confidence": 0.86, "types": ["ABOUT_CONCEPT"], "limit_per_type": 50},
        ).json()
        for edge in body["edges"]:
            assert edge["confidence_basis"] == "VARIES_WITHIN_PREDICATE"
            assert edge["evidence"]["confidence"] is not None
            assert edge["evidence"]["confidence"] >= 0.86

    def test_an_empty_neighbourhood_explains_itself(self, live_client: TestClient) -> None:
        """A filter combination that matches nothing must not return a bare empty graph."""
        body = live_client.get(
            f"/api/v1/graph/neighborhood/{INDRA}",
            params={"types": ["TREATS"], "trust_tier": "TIER_A"},
        ).json()
        assert body["edges"] == []
        assert body["data_status"] != "SUPPORTED"
        assert body["caveats"]

    @pytest.mark.parametrize(
        ("node_id", "params"),
        [
            (INDRA, {"types": ["TREATS"]}),
            (INDRA, {"types": ["HAS_DEVATA"], "trust_tier": "TIER_D"}),
            (INDRA, {"min_confidence": 1.0, "types": ["ABOUT_CONCEPT"]}),
            ("VG:WORK:AV:SAU", {}),
            ("VG:AV:SAU:K01", {}),
            ("CURSES", {}),
        ],
    )
    def test_an_empty_neighbourhood_is_partial_and_never_insufficient_evidence(
        self, live_client: TestClient, node_id: str, params: dict[str, Any]
    ) -> None:
        """The F-19 pattern. INSUFFICIENT_EVIDENCE means "evidence exists and cannot
        support the claim", and no empty neighbourhood is an evidence question: the graph
        knows exactly which edges a node has, so the emptiness is always a scope fact --
        either the client's filters or this endpoint's own whitelist. Spending the status
        here devalues it everywhere it means what it says.

        Paging cannot be a cause: this endpoint has no ``offset`` and ``limit_per_type`` is
        bounded ``ge=1``, so no value a client can send empties the collection.
        """
        response = live_client.get(f"/api/v1/graph/neighborhood/{node_id}", params=params)
        assert response.status_code == 200
        body = response.json()
        assert body["edges"] == [], "this case is meant to come back empty"
        assert body["data_status"] == "PARTIAL", body["data_status"]
        assert "INSUFFICIENT_EVIDENCE" not in json.dumps(body)
        assert body["caveats"], "an empty collection may never travel bare"

    def test_a_structural_node_says_where_its_edges_went(self, live_client: TestClient) -> None:
        """1,888 Passages and 2 of the 4 Works carry zero traversable edges because their
        whole connectivity is CONTAINS, which this endpoint excludes. "No edges" without
        saying where they went is true and useless, so the excluded degree is measured and
        named and the client is pointed at the endpoints that do traverse it."""
        for node_id in ("VG:WORK:AV:SAU", "VG:AV:SAU:K01"):
            body = live_client.get(f"/api/v1/graph/neighborhood/{node_id}").json()
            assert body["edges"] == []
            assert body["bounds"]["total_degree"] == 0
            scope = next(caveat for caveat in body["caveats"] if "excluded kinds" in caveat["text"])
            assert "CONTAINS" in scope["text"]
            assert "passage navigation" in scope["text"]
            # The count is measured, not asserted: a hand-typed figure is what this
            # repository has already shipped wrong.
            assert any(character.isdigit() for character in scope["text"])
            assert_no_leaks(body)

    def test_the_excluded_degree_report_never_counts_qa_findings(
        self, live_client: TestClient, live_repository: Neo4jRepository
    ) -> None:
        """``VG:WORK:AV:SAU`` is the sharp case: it has zero traversable edges and the Work
        label carries all 915 ``QA_ISSUE_ON`` edges in the graph, so a naive "what did we
        not traverse?" report would tell a client how many doubts the build holds."""
        row = live_repository.run_one(
            "MATCH (w:Work)-[r:QA_ISSUE_ON]-() RETURN count(r) AS qa_edges"
        )
        assert row is not None and int(row["qa_edges"]) > 0, (
            "this test is only meaningful while Works carry QA findings"
        )
        body = live_client.get("/api/v1/graph/neighborhood/VG:WORK:AV:SAU").json()
        blob = json.dumps(body)
        assert "QA_ISSUE_ON" not in blob
        assert str(row["qa_edges"]) not in blob

    def test_a_filter_emptied_neighbourhood_gives_actionable_advice(
        self, live_client: TestClient
    ) -> None:
        """The two causes get different advice, split on the measured degree: telling a
        client to relax ``trust_tier`` when the predicates they asked for have no edges at
        all would send them in a circle."""
        types_only = live_client.get(
            f"/api/v1/graph/neighborhood/{INDRA}", params={"types": ["TREATS"]}
        ).json()
        assert types_only["bounds"]["total_degree"] == 0
        assert any(
            "no edge of any predicate you requested" in caveat["text"]
            for caveat in types_only["caveats"]
        )

        tier_only = live_client.get(
            f"/api/v1/graph/neighborhood/{INDRA}",
            params={"types": ["HAS_DEVATA"], "trust_tier": "TIER_D"},
        ).json()
        assert tier_only["bounds"]["total_degree"] > 0
        graded = next(
            caveat for caveat in tier_only["caveats"] if "grading filters" in caveat["text"]
        )
        assert f"{tier_only['bounds']['total_degree']:,}" in graded["text"]

    def test_limit_per_type_cannot_empty_the_collection(self, live_client: TestClient) -> None:
        """The reason paging is not a cause of emptiness here: the smallest value a client
        may send is 1, and 1 per predicate per direction is not zero."""
        body = live_client.get(
            f"/api/v1/graph/neighborhood/{INDRA}", params={"limit_per_type": 1}
        ).json()
        assert body["edges"], "limit_per_type=1 must still return edges"
        assert body["data_status"] == "SUPPORTED"

    def test_inherited_attributions_carry_their_caveat(self, live_client: TestClient) -> None:
        body = live_client.get(
            f"/api/v1/graph/neighborhood/{INDRA}",
            params={"types": ["HAS_DEVATA"], "limit_per_type": 50},
        ).json()
        inherited = [
            edge
            for edge in body["edges"]
            if edge["evidence"]["evidence_basis"] == "CONTAINER_INHERITED"
        ]
        assert inherited, "8,329 of 10,558 HAS_DEVATA edges are inherited; none came back"
        for edge in inherited:
            assert edge["caveat"] is not None
            assert "CONTAINER_INHERITED" in edge["caveat"]["text"]

    def test_every_returned_edge_id_resolves_to_the_same_edge(
        self, live_client: TestClient
    ) -> None:
        """The round trip that matters: an id handed out by one endpoint is accepted by the
        other and comes back describing the same two nodes."""
        body = live_client.get(
            f"/api/v1/graph/neighborhood/{INDRA}", params={"limit_per_type": 2}
        ).json()
        assert body["edges"]
        checked = 0
        for edge in body["edges"][:20]:
            explained = live_client.get(f"/api/v1/graph/relationships/{edge['id']}")
            assert explained.status_code == 200, edge["id"]
            payload = explained.json()
            assert payload["relationship"]["type"] == edge["type"]
            assert {payload["source"]["id"], payload["target"]["id"]} == {
                edge["source"],
                edge["target"],
            }
            assert payload["relationship"]["id"] == edge["id"], "the token is not stable"
            checked += 1
        assert checked >= 10

    def test_both_id_bases_occur_and_both_resolve(self, live_client: TestClient) -> None:
        """A neighbourhood of a passage mixes domain-id edges (mentions, assertions) with
        endpoint-triple ones (seer, metre), and both kinds have to work."""
        body = live_client.get(
            f"/api/v1/graph/neighborhood/{RV_FIRST}", params={"limit_per_type": 3}
        ).json()
        bases = {edge["id_basis"] for edge in body["edges"]}
        assert bases == {"DOMAIN_ID", "ENDPOINT_TRIPLE"}, bases
        for basis in bases:
            edge = next(e for e in body["edges"] if e["id_basis"] == basis)
            assert live_client.get(f"/api/v1/graph/relationships/{edge['id']}").status_code == 200

    def test_exact_parallel_edges_without_a_domain_id_still_get_an_identity(
        self, live_client: TestClient, live_repository: Neo4jRepository
    ) -> None:
        """256 of the 1,006 EXACT_PARALLEL_OF edges carry no parallel_id. Deciding the basis
        per type instead of per edge would have minted a broken token for every one."""
        row = live_repository.run_one(
            "MATCH (a:Passage)-[r:EXACT_PARALLEL_OF]->(b:Passage) "
            "WHERE r.parallel_id IS NULL "
            "RETURN a.canonical_key AS source LIMIT 1"
        )
        if row is None:
            pytest.skip("every EXACT_PARALLEL_OF edge now carries a parallel_id")
        body = live_client.get(
            f"/api/v1/graph/neighborhood/{row['source']}",
            params={"types": ["EXACT_PARALLEL_OF"], "limit_per_type": 50},
        ).json()
        idless = [e for e in body["edges"] if e["id_basis"] == "ENDPOINT_TRIPLE"]
        assert idless, "an EXACT_PARALLEL_OF edge with no parallel_id must fall back"
        assert live_client.get(f"/api/v1/graph/relationships/{idless[0]['id']}").status_code == 200


@pytest.mark.neo4j
class TestLiveExplanation:
    def test_an_inherited_seer_edge_explains_that_it_is_inherited(
        self, live_client: TestClient
    ) -> None:
        body = live_client.get(
            f"/api/v1/graph/neighborhood/{RV_FIRST}", params={"types": ["HAS_RISHI"]}
        ).json()
        assert body["edges"]
        explained = live_client.get(f"/api/v1/graph/relationships/{body['edges'][0]['id']}").json()
        assert "seer" in explained["why"]
        assert "inherited" in explained["why"] or "projected" in explained["why"]
        assert "HUMAN_REVIEWED" in " ".join(c["text"] for c in explained["caveats"])
        assert explained["review_status"]

    def test_a_cross_veda_reuse_edge_carries_both_witnesses(
        self, live_client: TestClient, live_repository: Neo4jRepository
    ) -> None:
        """The RV<->SV demo: a Samavedic verse reusing a Rigvedic one, with the quoted text
        of both sides and the surface they were compared on."""
        row = live_repository.run_one(
            "MATCH (sv:Passage)-[r:REUSES_TEXT_FROM]->(rv:Passage) "
            "WHERE r.parallel_id IS NOT NULL "
            "RETURN sv.canonical_key AS source, rv.veda AS target_veda LIMIT 1"
        )
        assert row is not None
        assert row["target_veda"] == "RV"
        body = live_client.get(
            f"/api/v1/graph/neighborhood/{row['source']}",
            params={"types": ["REUSES_TEXT_FROM"]},
        ).json()
        edge = body["edges"][0]
        assert edge["id_basis"] == "DOMAIN_ID"
        explained = live_client.get(f"/api/v1/graph/relationships/{edge['id']}").json()
        spans = explained["relationship"]["evidence"]["spans"]
        assert len(spans) >= 2, "a parallel has two witnesses and both must be quoted"
        assert {span["veda"] for span in spans} == {"RV", "SV"}
        assert all(span["quote"] for span in spans)
        assert explained["evidence_passages"], "the cited passages must resolve to nodes"
        assert_no_leaks(explained)

    def test_a_model_extracted_edge_reports_model_adjudicated_not_reviewed(
        self, live_client: TestClient, live_repository: Neo4jRepository
    ) -> None:
        row = live_repository.run_one(
            "MATCH (p:Passage)-[r:INVOKES]->() WHERE r.review_state = 'MODEL_ADJUDICATED' "
            "RETURN p.canonical_key AS source LIMIT 1"
        )
        assert row is not None
        body = live_client.get(
            f"/api/v1/graph/neighborhood/{row['source']}", params={"types": ["INVOKES"]}
        ).json()
        explained = live_client.get(f"/api/v1/graph/relationships/{body['edges'][0]['id']}").json()
        assert explained["relationship"]["evidence"]["review_state"] == "MODEL_ADJUDICATED"
        assert "not human review" in explained["review_status"]
        assert explained["relationship"]["confidence_basis"] == "VARIES_WITHIN_PREDICATE"

    def test_the_explanation_preserves_upper_case_values(
        self, live_client: TestClient, live_repository: Neo4jRepository
    ) -> None:
        """A regression guard: ``str.capitalize`` on the assembled detail lowercased the
        whole sentence, turning CORE into core and SANDHI_INSENSITIVE into
        sandhi_insensitive."""
        row = live_repository.run_one(
            "MATCH (p:Passage)-[r:MENTIONS_DEVATA]->() "
            "WHERE r.referent_certainty = 'DEITY_AMBIGUOUS' "
            "RETURN p.canonical_key AS source LIMIT 1"
        )
        assert row is not None
        body = live_client.get(
            f"/api/v1/graph/neighborhood/{row['source']}",
            params={"types": ["MENTIONS_DEVATA"], "limit_per_type": 50},
        ).json()
        ambiguous = [
            edge
            for edge in body["edges"]
            if edge["caveat"] and "DEITY_AMBIGUOUS" in edge["caveat"]["text"]
        ]
        assert ambiguous
        explained = live_client.get(f"/api/v1/graph/relationships/{ambiguous[0]['id']}").json()
        assert "DEITY_AMBIGUOUS" in explained["why"]


@pytest.mark.neo4j
class TestLivePath:
    def test_a_meaningful_path_explains_every_hop(self, live_client: TestClient) -> None:
        response = live_client.get(
            "/api/v1/graph/path", params={"from": GAYATRI, "to": ALTAR, "max_depth": 4}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["length"] == len(body["hops"])
        assert body["hops"], "gayatri and the altar are connected within four hops"
        for index, hop in enumerate(body["hops"], start=1):
            assert hop["index"] == index
            assert hop["explanation"].strip()
            assert "does not establish" in hop["explanation"]
            assert hop["relationship"]["type"] in PATH_RELATIONSHIPS
        # The hops must chain: each hop's target is the next hop's source.
        for first, second in zip(body["hops"], body["hops"][1:], strict=False):
            assert first["target"]["id"] == second["source"]["id"]
        assert body["hops"][0]["source"]["id"] == body["source"]["id"]
        assert body["hops"][-1]["target"]["id"] == body["target"]["id"]

    def test_a_hub_mediated_route_is_labelled_rather_than_suppressed(
        self, live_client: TestClient
    ) -> None:
        """RV 1.1.1 and SV 1.1.1 are two hops apart through a busy entity. Returning nothing
        would read as 'unconnected', which is false."""
        body = live_client.get(
            "/api/v1/graph/path", params={"from": RV_FIRST, "to": SV_FIRST, "max_depth": 3}
        ).json()
        assert body["hops"]
        assert body["hub_mediated"] is True
        hub_caveat = next(c for c in body["caveats"] if "HUB-MEDIATED" in c["text"])
        assert str(HUB_DEGREE_CEILING) in hub_caveat["text"]
        assert "does not distinguish this one" in hub_caveat["text"]

    def test_a_direct_edge_is_not_hub_mediated(self, live_client: TestClient) -> None:
        """Indra and Agni share a CO_OCCURS_WITH edge. Both are hubs; neither is a waypoint,
        and a client that asks about Indra must not be told Indra is too popular."""
        body = live_client.get(
            "/api/v1/graph/path", params={"from": INDRA, "to": AGNI, "max_depth": 2}
        ).json()
        assert body["length"] == 1
        assert body["hub_mediated"] is False

    def test_the_same_node_twice_is_a_zero_length_answer_not_an_error(
        self, live_client: TestClient
    ) -> None:
        body = live_client.get("/api/v1/graph/path", params={"from": INDRA, "to": INDRA}).json()
        assert body["length"] == 0
        assert body["hops"] == []
        assert body["caveats"]

    def test_no_path_says_so_without_claiming_the_corpus_is_silent(
        self, live_client: TestClient
    ) -> None:
        """INSUFFICIENT_EVIDENCE is correct HERE and wrong for an empty neighbourhood, and
        the difference is real rather than an inconsistency.

        An empty neighbourhood is a scope fact: the graph knows exactly which edges the node
        has. An empty path is an unresolved question: the search was bounded to a depth and
        to 27 predicates, ``allShortestPaths`` considers only minimum-length routes, and a
        longer route may exist and was not searched -- so the API genuinely cannot say
        whether these two are connected, which is what the status means.
        """
        body = live_client.get(
            "/api/v1/graph/path", params={"from": GAYATRI, "to": ALTAR, "max_depth": 1}
        ).json()
        assert body["hops"] == []
        assert body["data_status"] == "INSUFFICIENT_EVIDENCE"
        assert any("not about the corpus" in c["text"] for c in body["caveats"])

    def test_an_unknown_endpoint_is_404_and_not_an_empty_path(
        self, live_client: TestClient
    ) -> None:
        response = live_client.get(
            "/api/v1/graph/path", params={"from": INDRA, "to": "VG:DEVATA:NOPE"}
        )
        assert response.status_code == 404
        assert "VG:DEVATA:NOPE" in response.json()["detail"]

    @pytest.mark.parametrize(
        ("source", "target"),
        [
            (RV_FIRST, SV_FIRST),
            (RV_FIRST, "VG:AV:SAU:K01:S001:V001"),
            ("VG:RV:SAK:M10:S191:V004", "VG:CONCEPT:GO-CATTLE"),
            (GAYATRI, ALTAR),
            (INDRA, "VG:CONCEPT:SOMA-DRINK"),
        ],
    )
    def test_path_explosion_is_bounded_in_time_and_payload(
        self, live_client: TestClient, source: str, target: str
    ) -> None:
        """The requirement is that a request cannot make the server enumerate the graph.

        The naive implementation of this endpoint -- a hub-degree predicate inside
        ``shortestPath`` -- measured 22 to 25 seconds on the first two of these pairs, past
        the driver's own 15-second budget. The bound is asserted here rather than described,
        at the deepest depth the endpoint allows and on the pairs that were slowest.
        """
        started = time.perf_counter()
        response = live_client.get(
            "/api/v1/graph/path",
            params={"from": source, "to": target, "max_depth": PATH_MAX_DEPTH},
        )
        elapsed = time.perf_counter() - started
        assert response.status_code == 200
        assert elapsed < 2.0, f"{source} -> {target} took {elapsed:.1f}s"
        body = response.json()
        assert len(json.dumps(body)) < 60_000, "a path payload must stay small"
        assert len(body["hops"]) <= PATH_MAX_DEPTH


@pytest.mark.neo4j
class TestLivePerformance:
    """Latency, asserted rather than hoped for.

    The neighbourhood is aggregate-class at depth 2 and is held to a looser bound than the
    point reads, which is stated here rather than quietly absorbed: it fans out over up to
    57 predicates and then takes one bounded step beyond that frontier.

    Every test here takes ``untraced_measurement``, and the budgets assume it. Depth 2 does
    more Python per request than any other route in this file, so it paid the coverage
    tracer more than any other route: 185 ms with the tracer paused against 360-459 ms with
    it running, back to back in one process. Traced, this class passed at 282 ms in a small
    run and failed at 769 ms in a large one against the same 400 ms budget -- the budget was
    never what moved.
    """

    @pytest.mark.parametrize(
        ("label", "url", "params", "budget_ms"),
        [
            ("neighbourhood depth 1 (deity hub)", f"/api/v1/graph/neighborhood/{INDRA}", {}, 300),
            (
                "neighbourhood depth 1 (passage)",
                f"/api/v1/graph/neighborhood/{RV_FIRST}",
                {},
                150,
            ),
            (
                "neighbourhood depth 2 (aggregate-class)",
                f"/api/v1/graph/neighborhood/{INDRA}",
                {"depth": 2},
                400,
            ),
            (
                "path depth 4 (aggregate-class)",
                "/api/v1/graph/path",
                {"from": GAYATRI, "to": ALTAR, "max_depth": 4},
                300,
            ),
        ],
    )
    def test_median_latency(
        self,
        live_client: TestClient,
        untraced_measurement: UntracedBlock,
        label: str,
        url: str,
        params: dict[str, Any],
        budget_ms: int,
    ) -> None:
        timings: list[float] = []
        with untraced_measurement():
            for _ in range(5):
                started = time.perf_counter()
                response = live_client.get(url, params=params)
                timings.append((time.perf_counter() - started) * 1000)
                assert response.status_code == 200
        # Re-issued under the tracer, *after* the measurement and never before it: these
        # routes have to stay in the coverage report, and the timed loop must stay exactly
        # as written -- five samples, the first of them cold.
        assert live_client.get(url, params=params).status_code == 200
        timings.sort()
        median = timings[len(timings) // 2]
        assert median < budget_ms, f"{label}: median {median:.0f} ms over {budget_ms} ms"

    def test_relationship_explanation_is_a_point_read(
        self, live_client: TestClient, untraced_measurement: UntracedBlock
    ) -> None:
        body = live_client.get(
            f"/api/v1/graph/neighborhood/{RV_FIRST}", params={"limit_per_type": 1}
        ).json()
        token = body["edges"][0]["id"]
        timings: list[float] = []
        with untraced_measurement():
            for _ in range(5):
                started = time.perf_counter()
                assert live_client.get(f"/api/v1/graph/relationships/{token}").status_code == 200
                timings.append((time.perf_counter() - started) * 1000)
        # Re-issued under the tracer, *after* the measurement and never before it: these
        # routes have to stay in the coverage report, and the timed loop must stay exactly
        # as written -- five samples, the first of them cold.
        assert live_client.get(f"/api/v1/graph/relationships/{token}").status_code == 200
        timings.sort()
        assert timings[len(timings) // 2] < 150


@pytest.mark.neo4j
def test_neighbourhood_depth_is_capped_at_the_documented_maximum(
    live_client: TestClient,
) -> None:
    assert (
        live_client.get(
            f"/api/v1/graph/neighborhood/{INDRA}",
            params={"depth": NEIGHBOURHOOD_MAX_DEPTH + 1},
        ).status_code
        == 422
    )


@pytest.mark.neo4j
class TestNonDeitySubjects:
    """G-01b: a devata-slot entry that is not a god must say so, on every graph surface.

    The Anukramani names a *devata* for every hymn and 30 of the 214 entries are not
    deities: 22 human patrons and seers, 7 labels naming a gift rather than a recipient, and
    one dog. The frozen graph labels all 30 ``:Devata``. These endpoints are generic -- they
    resolve 16 id kinds and a deity is one of them -- so they will meet one, and eight of
    the 30 carry real traversable degree, which means they arrive as neighbours and
    waypoints and not only as a directly requested root.

    This is the fifth route caught by this defect class, so the tests assert the *shared*
    producer is what is speaking: the NOT-A-DEITY sentence comes from
    ``entity_service.subject_disclosure`` and nothing here re-implements it.
    """

    @pytest.mark.parametrize("node_id", [THE_DOG, VASISTHA_THE_PATRON, GIFT_PRAISE])
    def test_a_non_deity_root_is_flagged_and_caveated(
        self, live_client: TestClient, node_id: str
    ) -> None:
        response = live_client.get(f"/api/v1/graph/neighborhood/{node_id}")
        assert response.status_code == 200
        body = response.json()
        assert body["root"]["is_deity"] is False
        # type stays DEVATA on purpose: every other deity surface says DEVATA for this node,
        # and a graph endpoint inventing a different type would make following an EntityRef
        # change a node's type.
        assert body["root"]["type"] == "DEVATA"
        assert body["root"]["metadata"]["structure"] in {
            "HUMAN",
            "PATRON_PRAISE",
            "UNSPECIFIED",
        }
        assert "THIS SUBJECT IS NOT A DEITY" in body["caveats"][0]["text"], (
            "the disclosure must come first; a reader who stops after one caveat must not "
            "stop before the one that matters"
        )
        assert body["caveats"][0]["source"] == "deity_population_contract"
        assert any(node_id in caveat["text"] for caveat in body["caveats"]), (
            "a multi-node payload must name WHICH subject is not a deity"
        )
        assert_no_leaks(body)

    def test_the_caveat_text_comes_from_the_shared_producer(self, live_client: TestClient) -> None:
        """Not a graph-local variant. The same defect has been fixed five times because
        each surface wrote its own half of the contract; this asserts the wording is the
        one producer's."""
        from vedagraph.api.services.entity_service import (
            NOT_A_DEITY_SUBJECT,
            subject_disclosure,
        )

        expected = subject_disclosure("UNSPECIFIED")[1][0].text
        assert expected == NOT_A_DEITY_SUBJECT.format(structure="UNSPECIFIED")
        body = live_client.get(f"/api/v1/graph/neighborhood/{THE_DOG}").json()
        assert body["caveats"][0]["text"] == expected

    def test_a_real_deity_is_not_flagged_and_carries_no_disclosure(
        self, live_client: TestClient
    ) -> None:
        body = live_client.get(f"/api/v1/graph/neighborhood/{INDRA}").json()
        assert body["root"]["is_deity"] is True
        assert not any("NOT A DEITY" in caveat["text"] for caveat in body["caveats"]), (
            "crying wolf on Indra would train a reader to ignore the caveat"
        )

    def test_is_deity_is_null_for_everything_that_is_not_a_devata_slot_entry(
        self, live_client: TestClient
    ) -> None:
        """Tri-state, and the third state is the point. "Is this metre a god?" has no false
        answer -- it does not apply -- and returning false for 20,000 mantras would turn a
        typed absence into a negative claim."""
        body = live_client.get(f"/api/v1/graph/neighborhood/{RV_FIRST}", params={"depth": 2}).json()
        non_devata = [node for node in body["nodes"] if node["type"] != "DEVATA"]
        assert non_devata
        assert all(node["is_deity"] is None for node in non_devata)
        devata = [node for node in body["nodes"] if node["type"] == "DEVATA"]
        assert devata
        assert all(isinstance(node["is_deity"], bool) for node in devata)

    def test_a_non_deity_reached_as_a_neighbour_is_flagged(
        self, live_client: TestClient, live_repository: Neo4jRepository
    ) -> None:
        """Reached rather than requested: a passage whose Anukramani devata slot holds a
        gift-praise label. The root is a mantra, so only the per-node flag can carry this."""
        row = live_repository.run_one(
            "MATCH (p:Passage)-[:HAS_DEVATA]->(d:Devata) "
            "WHERE coalesce(d.structure, 'UNSPECIFIED') IN "
            "  ['HUMAN', 'PATRON_PRAISE', 'UNSPECIFIED'] "
            "RETURN p.canonical_key AS passage LIMIT 1"
        )
        assert row is not None
        body = live_client.get(
            f"/api/v1/graph/neighborhood/{row['passage']}",
            params={"types": ["HAS_DEVATA"], "limit_per_type": 50},
        ).json()
        assert body["root"]["is_deity"] is None, "the root here is a passage"
        flagged = [node for node in body["nodes"] if node["is_deity"] is False]
        assert flagged, "a non-deity reached as a neighbour must still be flagged"
        assert any("NOT A DEITY" in caveat["text"] for caveat in body["caveats"])
        assert any(flagged[0]["id"] in caveat["text"] for caveat in body["caveats"])

    def test_a_path_touching_a_non_deity_discloses_it(self, live_client: TestClient) -> None:
        body = live_client.get(
            "/api/v1/graph/path",
            params={"from": THE_DOG, "to": "VG:CONCEPT:SOMA-DRINK", "max_depth": 4},
        ).json()
        assert body["source"]["is_deity"] is False
        assert "THIS SUBJECT IS NOT A DEITY" in body["caveats"][0]["text"]

    def test_a_path_between_two_non_deities_names_both(self, live_client: TestClient) -> None:
        body = live_client.get(
            "/api/v1/graph/path",
            params={"from": VASISTHA_THE_PATRON, "to": "VG:DEVATA:VISVAMITRAH", "max_depth": 4},
        ).json()
        assert body["source"]["is_deity"] is False
        assert body["target"]["is_deity"] is False
        naming = next(
            caveat for caveat in body["caveats"] if "devata-slot entries" in caveat["text"]
        )
        assert VASISTHA_THE_PATRON in naming["text"]
        assert "VG:DEVATA:VISVAMITRAH" in naming["text"]
        assert "are devata-slot entries that are NOT deities" in naming["text"], (
            "number agreement: two subjects take the plural reading"
        )

    def test_the_singular_reading_is_used_for_one_subject(self, live_client: TestClient) -> None:
        body = live_client.get(f"/api/v1/graph/neighborhood/{THE_DOG}").json()
        naming = next(caveat for caveat in body["caveats"] if "devata-slot entry" in caveat["text"])
        assert "is a devata-slot entry that is NOT a deity" in naming["text"]

    def test_an_explanation_of_an_edge_touching_a_non_deity_discloses_it(
        self, live_client: TestClient
    ) -> None:
        neighbourhood = live_client.get(
            f"/api/v1/graph/neighborhood/{GIFT_PRAISE}", params={"limit_per_type": 1}
        ).json()
        assert neighbourhood["edges"]
        explained = live_client.get(
            f"/api/v1/graph/relationships/{neighbourhood['edges'][0]['id']}"
        ).json()
        assert False in (explained["source"]["is_deity"], explained["target"]["is_deity"])
        assert "THIS SUBJECT IS NOT A DEITY" in explained["caveats"][0]["text"]

    def test_the_disclosure_does_not_claim_a_population_parameter_this_route_lacks(
        self, live_client: TestClient
    ) -> None:
        """The shared template says the subject is served "only because
        population=all_ascriptions was requested", which is true of the deity routes and
        false here: these endpoints have no such parameter and resolve whatever id they are
        given. The adjacent sentence corrects the scope rather than forking the template."""
        body = live_client.get(f"/api/v1/graph/neighborhood/{THE_DOG}").json()
        text = " ".join(caveat["text"] for caveat in body["caveats"])
        assert "has no `population` parameter" in text
        assert "population" not in " ".join(
            str(parameter)
            for parameter in live_client.get("/openapi.json")
            .json()["paths"]["/api/v1/graph/neighborhood/{node_id}"]["get"]
            .get("parameters", [])
        )

    def test_all_thirty_non_deity_subjects_are_flagged(
        self, live_client: TestClient, live_repository: Neo4jRepository
    ) -> None:
        """Per subject, not per sample. This project has twice certified an absence from a
        sample that happened to miss the failing rows."""
        rows = live_repository.run(
            "MATCH (d:Devata) "
            "WHERE coalesce(d.structure, 'UNSPECIFIED') IN "
            "  ['HUMAN', 'PATRON_PRAISE', 'UNSPECIFIED'] "
            "RETURN d.entity_key AS key ORDER BY d.entity_key"
        )
        assert len(rows) == 30, f"the non-deity population moved: {len(rows)}"
        for row in rows:
            body = live_client.get(f"/api/v1/graph/neighborhood/{row['key']}").json()
            assert body["root"]["is_deity"] is False, row["key"]
            assert "THIS SUBJECT IS NOT A DEITY" in body["caveats"][0]["text"], row["key"]

    def test_every_real_deity_is_flagged_as_one(
        self, live_client: TestClient, live_repository: Neo4jRepository
    ) -> None:
        """The other half of the partition, so a change that flagged everything as a
        non-deity would fail rather than look like a clean pass."""
        rows = live_repository.run(
            "MATCH (d:Devata) "
            "WHERE coalesce(d.structure, 'UNSPECIFIED') IN "
            "  ['INDIVIDUAL', 'PAIR', 'GROUP', 'ABSTRACT'] "
            "RETURN d.entity_key AS key ORDER BY d.entity_key LIMIT 25"
        )
        assert len(rows) == 25
        for row in rows:
            body = live_client.get(f"/api/v1/graph/neighborhood/{row['key']}").json()
            assert body["root"]["is_deity"] is True, row["key"]
            assert not any("NOT A DEITY" in c["text"] for c in body["caveats"]), row["key"]
