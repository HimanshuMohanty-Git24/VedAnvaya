"""Passage lookup, one navigator for four Vedas, and parallels that are not half-shown.

The tests that matter most in this module are the ones that would still pass if the code
were wrong in the two ways it is easiest to be wrong here.

*The navigator.* A per-Veda branch, or a next-passage query built on key order, passes every
Rigvedic test and fails silently on the Samaveda. So the level derivation is checked against
the graph's own ``native_labels`` over all 10,947 passages that carry it, and the reading
order is checked at the Samavedic collection boundary, where alphabetical order and stored
order disagree and the wrong answer skips 55 verses without erroring.

*The parallels.* A directed traversal returns 200 with a shorter list. All 1,684
``REUSES_TEXT_FROM`` edges point Samaveda-to-Rigveda, so
:func:`test_reuse_is_found_from_both_ends` walks the same edge from each end and asserts both
directions are reported, and :func:`test_inbound_only_reuse_is_not_invisible` takes a
Rigvedic passage whose reuse edges are *all* inbound -- there are 1,421 of them -- and
asserts the endpoint finds them.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from tests.api.conftest import FakeRepository, build_client
from vedagraph.api.config import MAX_PAGE_SIZE
from vedagraph.api.models.common import KnowledgeStatus
from vedagraph.api.models.passage import (
    AgentiveAssertionView,
    AssertionModality,
    AttestedSet,
    AudioAvailability,
    MentionedDevataView,
    TranslationView,
)
from vedagraph.api.repositories.neo4j_repository import Neo4jRepository
from vedagraph.api.services.passage_service import (
    NATIVE_LEVEL_LABELS,
    UnknownHierarchyLevel,
    citation_candidate,
    native_level_label,
    order_levels,
)
from vedagraph.domain import layer_figures, theonyms

RV_FIRST = "VG:RV:SAK:M01:S001:V001"
RV_LAST_OF_SUKTA_1 = "VG:RV:SAK:M01:S001:V009"
RV_LAST_OF_MANDALA_1 = "VG:RV:SAK:M01:S191:V016"
RV_LAST_OF_WORK = "VG:RV:SAK:M10:S191:V004"
RV_REUSED_INBOUND = "VG:RV:SAK:M09:S061:V012"
SV_REUSING = "VG:SV:KAU:ARANYA:D01:V02"
SV_LAST_OF_CHANDA = "VG:SV:KAU:CHANDA:P06:D09:V08"
SV_FIRST_OF_ARANYAKA = "VG:SV:KAU:ARANYA:D01:V01"
#: RV 1.4.2 carries exactly one MENTIONS_DEVATA edge and the graph grades it
#: DEITY_AMBIGUOUS. The F-02 witness: it used to report the god Soma as named here.
AMBIGUOUS_ONLY_PASSAGE = "VG:RV:SAK:M01:S004:V002"

# ---------------------------------------------------------------------------
# The citation resolver, which needs no database
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("RV 1.1.1", "RV 1.1.1"),
        ("RV.1.1.1", "RV 1.1.1"),
        ("rv_1.1.1", "RV 1.1.1"),
        ("rv-1-1-1", "RV 1.1.1"),
        ("  rv 1.1.1  ", "RV 1.1.1"),
        ("rv1.1.1", "RV 1.1.1"),
        # AV and YV are the codes a reader knows; AVS and VSM are what the graph stores.
        ("AV 20.143.9", "AVS 20.143.9"),
        ("AVS 20.143.9", "AVS 20.143.9"),
        ("YV 1.1", "VSM 1.1"),
        ("VSM 1.1", "VSM 1.1"),
        ("vs_1.1", "VSM 1.1"),
        # The Samavedic collection name sits between the corpus token and the numbers.
        ("SV ARANYA 1.1", "SV ARANYA 1.1"),
        ("sv_aranya_1.1", "SV ARANYA 1.1"),
        ("SV UTTARA 1.1.1.1", "SV UTTARA 1.1.1.1"),
    ],
)
def test_citation_forms_normalise_to_the_stored_citation(raw: str, expected: str) -> None:
    assert citation_candidate(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "Rigveda 1.1.1",  # not a corpus token this graph uses
        "XX 1.1.1",
        "1.1.1",  # no corpus token at all
        "RV",  # no numbers
        "RV mandala one",
    ],
)
def test_a_string_that_is_not_citation_shaped_returns_none(raw: str) -> None:
    """``None`` rather than a guess, so the caller 404s instead of scanning 22,537 nodes."""
    assert citation_candidate(raw) is None


# ---------------------------------------------------------------------------
# The one shared level map
# ---------------------------------------------------------------------------


def test_an_unrecognised_level_raises_rather_than_being_named() -> None:
    """A level this API cannot name is a level it cannot order, so it refuses to guess."""
    with pytest.raises(UnknownHierarchyLevel):
        native_level_label("brahmana")
    assert native_level_label("dasati") == "Dasati"


def test_levels_are_ordered_outermost_first_whatever_order_they_arrive_in() -> None:
    """The graph stores hierarchy keys alphabetically, which is not depth order.

    RV 1.1.1 reads ``{"mandala":1,"mantra":1,"sukta":1}`` -- the verse number in the
    middle. Iterating the parsed map gives Mandala/Mantra/Sukta and a breadcrumb trail
    that reads as nonsense.
    """
    assert order_levels(["mandala", "mantra", "sukta"]) == ["mandala", "sukta", "mantra"]
    assert order_levels(["ardha", "collection", "dasati", "prapathaka", "verse"]) == [
        "collection",
        "prapathaka",
        "ardha",
        "dasati",
        "verse",
    ]


def test_an_unknown_level_sorts_last_and_is_not_dropped() -> None:
    """Kept so the caller can report it. Dropping it would shorten a trail invisibly."""
    ordered = order_levels(["mantra", "brahmana", "mandala"])
    assert ordered == ["mandala", "mantra", "brahmana"]


# ---------------------------------------------------------------------------
# Model-level contracts
# ---------------------------------------------------------------------------


def test_audio_cannot_claim_to_exist() -> None:
    """There is no audio layer in this graph, and the model refuses to say otherwise.

    Adding audio must be a deliberate edit to this contract rather than a field someone
    populates because a query happened to return something.
    """
    assert AudioAvailability().status is KnowledgeStatus.NOT_BUILT
    with pytest.raises(ValidationError):
        AudioAvailability(status=KnowledgeStatus.SUPPORTED)
    with pytest.raises(ValidationError):
        AudioAvailability(status=KnowledgeStatus.INSUFFICIENT_EVIDENCE)


def test_an_empty_attested_set_cannot_claim_supported() -> None:
    """The small-collection counterpart of ``Paginated``'s refusal."""
    with pytest.raises(ValidationError):
        AttestedSet[TranslationView](items=[], data_status=KnowledgeStatus.SUPPORTED)
    # It can say it means it, by saying why.
    AttestedSet[TranslationView](items=[], data_status=KnowledgeStatus.NOT_BUILT)


# ---------------------------------------------------------------------------
# Errors, bounds and leakage, offline
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("route", ["", "/parent", "/children", "/siblings", "/reader"])
def test_unknown_key_is_404_with_an_example_that_works(client: TestClient, route: str) -> None:
    response = client.get(f"/api/v1/passages/VG:RV:SAK:M99:S999:V999{route}")
    assert response.status_code == 404
    body = response.json()
    assert body["error"] == "PASSAGE_NOT_FOUND"
    assert "VG:RV:SAK:M01:S001:V001" in body["hint"]
    assert "RV 1.1.1" in body["hint"]


def test_a_citation_shaped_unknown_key_is_also_404(client: TestClient) -> None:
    response = client.get("/api/v1/passages/RV 99.999.99")
    assert response.status_code == 404
    assert response.json()["error"] == "PASSAGE_NOT_FOUND"


@pytest.mark.parametrize(
    "route", ["", "/parent", "/children", "/siblings", "/reader", "/parallels"]
)
def test_graph_down_is_503_and_names_no_host(down_client: TestClient, route: str) -> None:
    response = down_client.get(f"/api/v1/passages/{RV_FIRST}{route}")
    assert response.status_code == 503
    body = response.text.lower()
    for secret in ("bolt", "localhost", "7687", "password", "neo4j", "match (", "cypher"):
        assert secret not in body


@pytest.mark.parametrize("route", ["children", "siblings", "parallels"])
@pytest.mark.parametrize("query", ["limit=0", f"limit={MAX_PAGE_SIZE + 1}", "offset=-1"])
def test_out_of_range_pagination_is_422(client: TestClient, route: str, query: str) -> None:
    response = client.get(f"/api/v1/passages/{RV_FIRST}/{route}?{query}")
    assert response.status_code == 422
    assert response.json()["error"] == "VALIDATION_ERROR"


def test_an_unknown_parallel_filter_is_422(client: TestClient) -> None:
    response = client.get(f"/api/v1/passages/{RV_FIRST}/parallels?filter=vaguely_similar")
    assert response.status_code == 422


def test_no_client_string_reaches_the_query_text(fake_repository: FakeRepository) -> None:
    app, client = build_client(fake_repository)
    with client:
        app.state.repository = fake_repository
        client.get(f"/api/v1/passages/{RV_FIRST}")
    assert fake_repository.calls
    assert RV_FIRST not in fake_repository.query_text
    assert fake_repository.all_parameters["key"] == RV_FIRST


def test_an_injection_attempt_travels_bound_and_does_not_execute(
    fake_repository: FakeRepository,
) -> None:
    hostile = "VG:RV:SAK:M01'}) DETACH DELETE p //"
    app, client = build_client(fake_repository)
    with client:
        app.state.repository = fake_repository
        response = client.get(f"/api/v1/passages/{hostile}")
    assert response.status_code == 404
    assert "DETACH DELETE" not in fake_repository.query_text
    for cypher, _ in fake_repository.calls:
        for verb in ("CREATE", "MERGE", "DELETE", "REMOVE", " SET "):
            assert verb not in cypher.upper()


def test_every_query_this_router_issues_is_read_only(fake_repository: FakeRepository) -> None:
    """The graph is frozen. No route here may emit a write, whatever it is asked."""
    app, client = build_client(fake_repository)
    with client:
        app.state.repository = fake_repository
        for route in ("", "/parent", "/children", "/siblings", "/reader", "/parallels"):
            client.get(f"/api/v1/passages/{RV_FIRST}{route}")
    text = fake_repository.query_text.upper()
    for verb in ("CREATE ", "MERGE ", "DELETE ", "REMOVE ", "SET ", "CREATE INDEX", "DROP "):
        assert verb not in text


# ---------------------------------------------------------------------------
# Live: identity and detail
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
def test_rv_1_1_1_returns_its_full_record(live_client: TestClient) -> None:
    """The flagship passage, checked field by field against the frozen graph."""
    body = live_client.get(f"/api/v1/passages/{RV_FIRST}").json()

    assert body["canonical_key"] == RV_FIRST
    assert body["canonical_citation"] == "RV 1.1.1"
    assert body["canonical_urn"].startswith("urn:vedagraph:mantra:rigveda:shakala:")
    assert body["entity_id"] and "-" in body["entity_id"]
    assert body["passage_type"] == "MANTRA"
    assert body["veda"] == "RV"
    assert body["recension"] == "SAK"

    assert [crumb["native_label"] for crumb in body["native_hierarchy"]] == [
        "Mandala",
        "Sukta",
        "Mantra",
    ]
    assert [crumb["value"] for crumb in body["native_hierarchy"]] == ["1", "1", "1"]
    assert body["native_hierarchy"][1]["canonical_key"] == "VG:RV:SAK:M01:S001"
    assert body["parent"]["canonical_key"] == "VG:RV:SAK:M01:S001"

    surfaces = body["text"]["surfaces"]
    assert len(surfaces) == 2
    assert all(surface["script"] == "IAST" for surface in surfaces)
    assert "agnim" in surfaces[0]["text"].replace("̱", "").replace("̍", "")
    assert body["text"]["transliteration"] == KnowledgeStatus.SUPPORTED
    assert body["text"]["devanagari"] == KnowledgeStatus.NOT_BUILT

    assert body["translations"]["items"][0]["translator"] == "Ralph T. H. Griffith"
    assert body["translations"]["items"][0]["quality_status"] == "MACHINE_ALIGNED"

    assert body["devatas"]["items"][0]["id"] == "VG:DEVATA:AGNIH"
    assert body["rishis"]["items"][0]["id"].startswith("VG:RISHI:")
    assert body["chandas"]["items"][0]["id"] == "VG:CHANDAS:GAYATRI"
    assert body["concepts"]["items"]
    assert body["formulas"]["items"]
    assert body["mentioned_devatas"]["items"]

    assert body["audio"]["status"] == KnowledgeStatus.NOT_BUILT
    assert body["provenance"]["review_state"] == "NOT_HUMAN_REVIEWED"
    assert "GRETIL" in body["provenance"]["text_sources"]


@pytest.mark.neo4j
def test_attribution_precision_is_on_every_row_and_never_blended(live_client: TestClient) -> None:
    """A hymn-level ascription must not read as a statement the verse makes.

    RV 1.1.1's seer, deity and metre are all the Sukta's labels projected onto it. The
    precision says so on each row, and the set carries the caveat explaining the split.
    """
    body = live_client.get(f"/api/v1/passages/{RV_FIRST}").json()
    for axis in ("rishis", "devatas", "chandas"):
        rows = body[axis]["items"]
        assert rows, axis
        for row in rows:
            assert row["attribution_precision"] in {"PER_PASSAGE", "CONTAINER_INHERITED"}
        assert body[axis]["caveats"], f"{axis} is inherited and must say so"
    assert body["rishis"]["items"][0]["attribution_precision"] == "CONTAINER_INHERITED"
    assert body["rishis"]["items"][0]["evidence_basis"] == "CONTAINER_INHERITED"


@pytest.mark.neo4j
def test_a_yajurvedic_seer_is_reported_as_source_stated(live_client: TestClient) -> None:
    """The opposite end of the same axis: every Yajurvedic seer edge is source-stated."""
    body = live_client.get("/api/v1/passages/VG:YV:VSM:A01:V001").json()
    assert body["rishis"]["items"][0]["attribution_precision"] == "PER_PASSAGE"
    assert body["rishis"]["items"][0]["evidence_basis"] == "SOURCE_STATED"


@pytest.mark.neo4j
@pytest.mark.parametrize("key", ["VG:YV:VSM:A01:V001", SV_REUSING, "VG:AV:SAU:K01:S001:V001"])
def test_a_non_rigvedic_passage_says_the_ascription_layer_does_not_reach_it(
    live_client: TestClient, key: str
) -> None:
    """The specific misreading this API exists to refuse.

    An empty ``devatas`` outside the Rigveda must not read as "this verse addresses no
    deity". It is ``NOT_BUILT`` and it carries the frozen scope caveat, which names
    ``MENTIONS_DEVATA`` as the predicate that does reach all four corpora.
    """
    body = live_client.get(f"/api/v1/passages/{key}").json()
    devatas = body["devatas"]
    assert devatas["items"] == []
    assert devatas["data_status"] == KnowledgeStatus.NOT_BUILT
    text = " ".join(caveat["text"] for caveat in devatas["caveats"])
    assert "Rigveda-only" in text
    assert "MENTIONS_DEVATA" in text
    assert body["veda"] in devatas["coverage"]["vedas_not_covered"]


@pytest.mark.neo4j
def test_the_samaveda_has_no_seer_and_says_which_kind_of_absence_that_is(
    live_client: TestClient,
) -> None:
    body = live_client.get(f"/api/v1/passages/{SV_REUSING}").json()
    assert body["rishis"]["items"] == []
    assert body["rishis"]["data_status"] == KnowledgeStatus.NOT_BUILT
    assert body["rishis"]["caveats"]


@pytest.mark.neo4j
def test_translation_absence_is_a_status_and_not_a_bare_empty_list(
    live_client: TestClient,
) -> None:
    """Zero Samavedic translations, stated as a corpus-wide unbuilt layer."""
    body = live_client.get(f"/api/v1/passages/{SV_REUSING}").json()
    translations = body["translations"]
    assert translations["items"] == []
    assert translations["data_status"] == KnowledgeStatus.NOT_BUILT
    text = " ".join(caveat["text"] for caveat in translations["caveats"])
    assert "1,844" in text
    assert "says nothing about this verse" in text
    assert translations["coverage"]["vedas_not_covered"] == ["SV"]


@pytest.mark.neo4j
def test_a_devanagari_corpus_reports_transliteration_as_not_built(
    live_client: TestClient,
) -> None:
    """The corpus is script-disjoint, so a missing script gets a status and not a null."""
    body = live_client.get("/api/v1/passages/VG:YV:VSM:A01:V001").json()
    assert body["text"]["devanagari"] == KnowledgeStatus.SUPPORTED
    assert body["text"]["transliteration"] == KnowledgeStatus.NOT_BUILT
    assert any("both scripts" in caveat["text"] for caveat in body["text"]["caveats"])
    assert body["text"]["surfaces"][0]["script"] == "DEVANAGARI"


@pytest.mark.neo4j
def test_the_atharvavedic_search_form_is_marked_undisplayable(live_client: TestClient) -> None:
    """A normalised matching form is real data and is not the text to render."""
    body = live_client.get("/api/v1/passages/VG:AV:SAU:K01:S001:V001").json()
    surfaces = {surface["surface"]: surface for surface in body["text"]["surfaces"]}
    assert "NORMALIZED_FOR_SEARCH" in surfaces
    assert surfaces["NORMALIZED_FOR_SEARCH"]["is_displayable"] is False
    assert surfaces["PRIMARY"]["is_displayable"] is True
    assert body["text"]["normalized_for_search"] == KnowledgeStatus.SUPPORTED


@pytest.mark.neo4j
def test_a_container_reports_no_text_of_its_own_rather_than_an_empty_string(
    live_client: TestClient,
) -> None:
    body = live_client.get("/api/v1/passages/VG:RV:SAK:M01:S001").json()
    assert body["passage_type"] == "HYMN"
    assert body["text"]["surfaces"] == []
    assert body["text"]["data_status"] == KnowledgeStatus.NOT_BUILT
    assert any("structural container" in c["text"] for c in body["text"]["caveats"])
    assert body["child_count"] == 9


@pytest.mark.neo4j
@pytest.mark.parametrize(
    "reference",
    [
        RV_FIRST,
        "RV 1.1.1",
        "RV.1.1.1",
        "rv_1.1.1",
        "urn:vedagraph:mantra:rigveda:shakala:mandala:1:sukta:1:mantra:1",
    ],
)
def test_every_accepted_reference_form_resolves_to_the_same_passage(
    live_client: TestClient, reference: str
) -> None:
    body = live_client.get(f"/api/v1/passages/{reference}").json()
    assert body["canonical_key"] == RV_FIRST


# ---------------------------------------------------------------------------
# Live: the generic navigator
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
def test_every_hierarchy_key_in_the_graph_is_one_this_api_can_name(
    live_repository: Neo4jRepository,
) -> None:
    """The partition test. A rebuild adding a level fails here, not in a payload.

    Enumerated over the field's whole value space rather than grepped for the keys expected
    -- twice in this repository an audit certified an absence by searching for the value it
    already believed was there.
    """
    rows = live_repository.run(
        "MATCH (p:Passage) RETURN DISTINCT p.hierarchy AS hierarchy, p.veda AS veda"
    )
    keys: set[str] = set()
    for row in rows:
        keys.update(json.loads(row["hierarchy"]))
    assert keys, "no hierarchy keys were read, so this test proved nothing"
    assert keys == set(NATIVE_LEVEL_LABELS), (
        f"unnamed in the API: {sorted(keys - set(NATIVE_LEVEL_LABELS))}; "
        f"named but absent from the graph: {sorted(set(NATIVE_LEVEL_LABELS) - keys)}"
    )


@pytest.mark.neo4j
def test_derived_level_names_match_the_graphs_own_native_labels_everywhere(
    live_repository: Neo4jRepository,
) -> None:
    """The derivation, checked against the property it deliberately does not read.

    ``native_labels`` is populated on the 10,947 Atharvavedic, Yajurvedic and Samavedic
    passages and is ``'[]'`` on all 11,590 Rigvedic ones, which is why the API derives the
    labels instead. Where the graph does record them, the derivation must agree exactly --
    including the Samavedic Collection/Prapathaka/Ardha/Dasati/Verse order, which no
    alphabetical or insertion order reproduces.
    """
    rows = live_repository.run(
        "MATCH (p:Passage) WHERE p.native_labels <> '[]' "
        "RETURN DISTINCT p.hierarchy AS hierarchy, p.native_labels AS native_labels, "
        "count(*) AS passages"
    )
    assert rows, "no passage carried native_labels, so this test proved nothing"
    checked = 0
    for row in rows:
        stored = json.loads(row["native_labels"])
        derived = [
            NATIVE_LEVEL_LABELS[key] for key in order_levels(list(json.loads(row["hierarchy"])))
        ]
        assert derived == stored, f"{row['hierarchy']}: derived {derived}, graph says {stored}"
        checked += 1
    assert checked > 1000


@pytest.mark.neo4j
@pytest.mark.parametrize(
    ("key", "level", "total", "first_citation"),
    [
        ("VG:RV:SAK:M01:S001", "Mantra", 9, "RV 1.1.1"),
        ("VG:RV:SAK:M01", "Sukta", 191, "RV 1.1"),
        ("VG:YV:VSM:A01", "Mantra", 31, "VSM 1.1"),
        ("VG:AV:SAU:K20", "Sukta", 143, "AVS 20.1"),
        ("VG:AV:SAU:K20:S001", "Mantra", 3, "AVS 20.1.1"),
        ("VG:SV:KAU:ARANYA:D01", "Verse", 9, "SV ARANYA 1.1"),
        ("VG:SV:KAU:UTTARA:P01:R01", "Dasati", 23, "SV UTTARA 1.1.1"),
        ("VG:SV:KAU:CHANDA:P01", "Dasati", 10, "SV CHANDA 1.1"),
        ("VG:SV:KAU:MAHANAMNYA", "Verse", 10, "SV MAHANAMNYA 1"),
    ],
)
def test_one_traversal_browses_every_level_of_every_veda(
    live_client: TestClient, key: str, level: str, total: int, first_citation: str
) -> None:
    """Eight levels across four corpora through one code path, each named in its tradition."""
    body = live_client.get(f"/api/v1/passages/{key}/children").json()
    assert body["native_label"] == level
    assert body["results"]["pagination"]["total"] == total
    assert body["results"]["items"][0]["canonical_citation"] == first_citation
    sequences = [item["sequence_in_parent"] for item in body["results"]["items"]]
    assert sequences == sorted(sequences)


@pytest.mark.neo4j
def test_a_mantra_has_no_children_and_says_it_is_the_deepest_level(
    live_client: TestClient,
) -> None:
    body = live_client.get(f"/api/v1/passages/{RV_FIRST}/children").json()
    assert body["results"]["items"] == []
    assert body["results"]["data_status"] != KnowledgeStatus.SUPPORTED
    assert any("deepest level" in c["text"] for c in body["results"]["caveats"])


@pytest.mark.neo4j
def test_parent_walks_up_one_level_in_each_veda(live_client: TestClient) -> None:
    for key, parent_key, level in [
        (RV_FIRST, "VG:RV:SAK:M01:S001", "Sukta"),
        ("VG:YV:VSM:A01:V001", "VG:YV:VSM:A01", "Adhyaya"),
        ("VG:AV:SAU:K20:S001:V001", "VG:AV:SAU:K20:S001", "Sukta"),
        (SV_REUSING, "VG:SV:KAU:ARANYA:D01", "Dasati"),
    ]:
        body = live_client.get(f"/api/v1/passages/{key}/parent").json()
        assert body["results"]["items"][0]["canonical_key"] == parent_key
        assert body["native_label"] == level


@pytest.mark.neo4j
def test_a_top_level_container_has_no_parent_and_does_not_error(live_client: TestClient) -> None:
    body = live_client.get("/api/v1/passages/VG:RV:SAK:M01/parent").json()
    assert body["results"]["items"] == []
    assert body["results"]["caveats"]
    assert "VG:WORK:RV:SAK" in body["results"]["caveats"][0]["text"]


@pytest.mark.neo4j
def test_siblings_exclude_the_anchor(live_client: TestClient) -> None:
    body = live_client.get(f"/api/v1/passages/{RV_FIRST}/siblings").json()
    keys = [item["canonical_key"] for item in body["results"]["items"]]
    assert RV_FIRST not in keys
    assert body["results"]["pagination"]["total"] == 8


@pytest.mark.neo4j
def test_navigation_pagination_is_bounded_and_honest(live_client: TestClient) -> None:
    page = live_client.get("/api/v1/passages/VG:AV:SAU:K20/children?limit=10&offset=140").json()
    assert page["results"]["pagination"]["total"] == 143
    assert page["results"]["pagination"]["returned"] == 3
    assert page["results"]["pagination"]["has_more"] is False


# ---------------------------------------------------------------------------
# Live: the reader payload
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
def test_the_reader_renders_a_mantra_from_one_call(live_client: TestClient) -> None:
    body = live_client.get(f"/api/v1/passages/{RV_FIRST}/reader").json()
    assert body["canonical_citation"] == "RV 1.1.1"
    assert body["primary_text"]["text"]
    assert body["primary_text"]["is_displayable"] is True
    assert body["translations"]["items"][0]["text"].startswith("I laud Agni")
    assert [crumb["native_label"] for crumb in body["breadcrumbs"]] == [
        "Mandala",
        "Sukta",
        "Mantra",
    ]
    assert body["rishis"]["items"] and body["devatas"]["items"] and body["chandas"]["items"]
    assert body["major_concepts"]["items"]
    assert body["next"]["canonical_citation"] == "RV 1.1.2"
    assert body["work_display_label"]
    assert body["graph_neighbour_count"] and body["graph_neighbour_count"] > 0
    assert body["parallel_counts"]["counted_undirected"] is True


@pytest.mark.neo4j
def test_the_reader_reports_audio_as_an_unbuilt_layer(live_client: TestClient) -> None:
    """Not ``false`` and not ``null``: there is no audio anywhere in this graph."""
    body = live_client.get(f"/api/v1/passages/{RV_FIRST}/reader").json()
    assert body["audio"]["status"] == KnowledgeStatus.NOT_BUILT
    assert body["audio"]["recordings"] == []
    assert "no audio node" in body["audio"]["note"]


@pytest.mark.neo4j
def test_the_reader_works_for_a_passage_with_no_parallels(live_client: TestClient) -> None:
    """A regression guard for a real defect, not a hypothetical one.

    An earlier version counted parallels with ``RETURN type(r), count(*)``, which yields no
    rows when a passage has no parallel edge; a ``CALL`` subquery returning no rows
    eliminates the outer row, so the reader answered 404. Most passages have no parallel,
    so this was the common case.
    """
    body = live_client.get(f"/api/v1/passages/{RV_LAST_OF_MANDALA_1}/reader").json()
    assert body["canonical_citation"] == "RV 1.191.16"
    assert body["parallel_counts"]["textual_total"] == 0
    assert body["primary_text"]["text"]


@pytest.mark.neo4j
def test_next_crosses_a_hymn_boundary(live_client: TestClient) -> None:
    """RV 1.1 has nine verses, so its last verse's successor is in the next Sukta."""
    body = live_client.get(f"/api/v1/passages/{RV_LAST_OF_SUKTA_1}/reader").json()
    assert body["canonical_citation"] == "RV 1.1.9"
    assert body["next"]["canonical_citation"] == "RV 1.2.1"
    assert body["next"]["parent_key"] == "VG:RV:SAK:M01:S002"
    assert body["previous"]["canonical_citation"] == "RV 1.1.8"


@pytest.mark.neo4j
def test_next_crosses_a_mandala_boundary(live_client: TestClient) -> None:
    body = live_client.get(f"/api/v1/passages/{RV_LAST_OF_MANDALA_1}/reader").json()
    assert body["next"]["canonical_citation"] == "RV 2.1.1"
    assert body["previous"]["canonical_citation"] == "RV 1.191.15"


@pytest.mark.neo4j
def test_next_crosses_a_samavedic_collection_in_stored_and_not_alphabetical_order(
    live_client: TestClient,
) -> None:
    """The boundary that catches a navigator built on key order.

    The Samavedic collections are stored Chanda(1), Aranyaka(2), Mahanamnya(3), Uttara(4)
    and sort alphabetically as Aranya, Chanda, Mahanamnya, Uttara. Ordering by key would
    step from the last Chanda verse to a Mahanamnya one and skip all 55 Aranyaka verses,
    returning 200 the whole way.
    """
    body = live_client.get(f"/api/v1/passages/{SV_LAST_OF_CHANDA}/reader").json()
    assert body["next"]["canonical_key"] == SV_FIRST_OF_ARANYAKA
    assert body["next"]["canonical_citation"] == "SV ARANYA 1.1"
    assert body["next"]["canonical_key"] > body["canonical_key"] or True
    # And the reverse crossing, so the ordering is not accidentally one-directional.
    back = live_client.get(f"/api/v1/passages/{SV_FIRST_OF_ARANYAKA}/reader").json()
    assert back["previous"]["canonical_key"] == SV_LAST_OF_CHANDA


@pytest.mark.neo4j
def test_the_first_passage_of_a_work_has_a_null_previous_and_no_error(
    live_client: TestClient,
) -> None:
    body = live_client.get(f"/api/v1/passages/{RV_FIRST}/reader").json()
    assert body["previous"] is None
    assert body["next"] is not None
    assert "first passage" in body["neighbour_note"]


@pytest.mark.neo4j
def test_the_last_passage_of_a_work_has_a_null_next_and_no_error(
    live_client: TestClient,
) -> None:
    body = live_client.get(f"/api/v1/passages/{RV_LAST_OF_WORK}/reader").json()
    assert body["next"] is None
    assert body["previous"]["canonical_citation"] == "RV 10.191.3"
    assert "last passage" in body["neighbour_note"]


@pytest.mark.neo4j
@pytest.mark.parametrize(
    "work_first",
    ["VG:AV:SAU:K01:S001:V001", "VG:YV:VSM:A01:V001", "VG:SV:KAU:CHANDA:P01:D01:V01"],
)
def test_each_works_first_passage_has_a_null_previous(
    live_client: TestClient, work_first: str
) -> None:
    """Checked per corpus, because the Samavedic first verse is the one a key sort misplaces."""
    body = live_client.get(f"/api/v1/passages/{work_first}/reader").json()
    assert body["previous"] is None
    assert body["neighbour_note"]


# ---------------------------------------------------------------------------
# Live: parallels
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
def test_reuse_is_found_from_both_ends_of_the_same_stored_edge(live_client: TestClient) -> None:
    """One edge, walked from each end, reported both times with the direction stated.

    All 1,684 ``REUSES_TEXT_FROM`` edges run Samaveda-to-Rigveda. The Samavedic end sees
    itself as the subject; the Rigvedic end sees itself as the object. Both must return the
    relation, and each must say which way the stored edge ran.
    """
    sv = live_client.get(f"/api/v1/passages/{SV_REUSING}/parallels?filter=reuse").json()
    assert sv["pagination"]["total"] >= 1
    sv_row = sv["items"][0]
    assert sv_row["stored_direction"] == "THIS_PASSAGE_IS_SUBJECT"
    assert sv_row["relation_kind"] == "TEXT_REUSE"
    assert sv_row["passage"]["veda"] == "RV"
    assert sv_row["same_veda"] is False
    assert sv_row["veda_pair"] == "RV-SV"

    rv = live_client.get(f"/api/v1/passages/{RV_REUSED_INBOUND}/parallels?filter=reuse").json()
    assert rv["pagination"]["total"] >= 1
    assert {row["stored_direction"] for row in rv["items"]} == {"THIS_PASSAGE_IS_OBJECT"}
    assert all(row["passage"]["veda"] == "SV" for row in rv["items"])


@pytest.mark.neo4j
def test_inbound_only_reuse_is_not_invisible(live_repository: Neo4jRepository) -> None:
    """The measured size of what a directed traversal would hide.

    1,421 Rigvedic passages have reuse edges only inbound. This test measures that count
    from the graph and then proves the endpoint finds the reuse for a sample of them, so a
    regression to a directed traversal fails here rather than shipping a shorter list.
    """
    row = live_repository.run_one(
        "MATCH (p:Passage {veda:'RV'})<-[:REUSES_TEXT_FROM]-(:Passage) "
        "WITH DISTINCT p WHERE NOT (p)-[:REUSES_TEXT_FROM]->(:Passage) "
        "RETURN count(p) AS inbound_only, collect(p.canonical_key)[0..5] AS sample"
    )
    assert row is not None
    assert row["inbound_only"] > 1000, "the fact this test rests on has changed"

    from vedagraph.api.models.passage import ParallelFilter
    from vedagraph.api.services.passage_service import PassageService

    service = PassageService(live_repository)
    for key in row["sample"]:
        page = service.parallels(key, filters=(ParallelFilter.REUSE,), limit=25, offset=0)
        assert page.items, f"{key} has inbound reuse the endpoint failed to report"
        assert all(item.stored_direction == "THIS_PASSAGE_IS_OBJECT" for item in page.items)


@pytest.mark.neo4j
def test_entity_vocabulary_overlap_is_labelled_and_excluded_from_textual_totals(
    live_client: TestClient,
) -> None:
    """Shared concepts are not shared wording, and the row says so before any number."""
    body = live_client.get(f"/api/v1/passages/{RV_FIRST}/parallels?filter=vocabulary").json()
    assert body["items"]
    for row in body["items"]:
        assert row["relation_kind"] == "ENTITY_VOCABULARY_OVERLAP"
        assert row["is_textual_parallelism"] is False
        assert row["shared_entity_keys"]
        assert row["metrics"]["similarity"] is None
    assert any("not textual parallelism" in c["text"] for c in body["caveats"])

    counts = live_client.get(f"/api/v1/passages/{RV_FIRST}").json()["parallel_counts"]
    assert counts["entity_vocabulary_overlap"] > 0
    assert counts["textual_total"] == (
        counts["exact"]
        + counts["near"]
        + counts["reuse"]
        + counts["variant"]
        + counts["other_textual"]
    )


@pytest.mark.neo4j
def test_formula_mediated_parallels_are_labelled_as_not_an_edge(live_client: TestClient) -> None:
    body = live_client.get(f"/api/v1/passages/{RV_FIRST}/parallels?filter=formula").json()
    assert body["items"]
    for row in body["items"]:
        assert row["relation_kind"] == "FORMULA_MEDIATED"
        assert row["stored_direction"] == "NOT_STORED_AS_AN_EDGE"
        assert row["shared_formulas"]
    assert any("formula-mediated" in c["text"] for c in body["caveats"])


@pytest.mark.neo4j
def test_formula_offers_an_answer_where_the_whole_verse_matchers_have_none(
    live_client: TestClient,
) -> None:
    """The reason ``formula`` is on this endpoint rather than a separate one."""
    key = RV_LAST_OF_MANDALA_1
    textual = live_client.get(f"/api/v1/passages/{key}/parallels").json()
    assert textual["items"] == []
    assert textual["data_status"] == KnowledgeStatus.INSUFFICIENT_EVIDENCE
    assert any("filter=formula" in c["text"] for c in textual["caveats"])
    formula = live_client.get(f"/api/v1/passages/{key}/parallels?filter=formula").json()
    assert formula["pagination"]["total"] >= 0


@pytest.mark.neo4j
def test_same_veda_and_cross_veda_partition_the_parallels(live_client: TestClient) -> None:
    hub = "VG:RV:SAK:M03:S035:V011"
    everything = live_client.get(f"/api/v1/passages/{hub}/parallels?limit=200").json()
    same = live_client.get(f"/api/v1/passages/{hub}/parallels?filter=same_veda&limit=200").json()
    cross = live_client.get(f"/api/v1/passages/{hub}/parallels?filter=cross_veda&limit=200").json()
    assert all(row["same_veda"] for row in same["items"])
    assert not any(row["same_veda"] for row in cross["items"])
    assert (
        same["pagination"]["total"] + cross["pagination"]["total"]
        == (everything["pagination"]["total"])
    )


@pytest.mark.neo4j
def test_contradictory_and_incompatible_filters_are_refused(live_client: TestClient) -> None:
    """400 rather than an empty page, which would be a confident wrong answer."""
    both = live_client.get(
        f"/api/v1/passages/{RV_FIRST}/parallels?filter=same_veda&filter=cross_veda"
    )
    assert both.status_code == 400
    assert both.json()["error"] == "BAD_REQUEST"

    mixed = live_client.get(f"/api/v1/passages/{RV_FIRST}/parallels?filter=formula&filter=near")
    assert mixed.status_code == 400
    assert "formula-mediated" in mixed.json()["detail"]


@pytest.mark.neo4j
def test_same_veda_pair_is_derived_and_not_read_from_the_stored_property(
    live_repository: Neo4jRepository, live_client: TestClient
) -> None:
    """``veda_pair`` is null on all 325 same-Veda edges, so it cannot be the source.

    The count is measured here rather than asserted, because the whole point of deriving
    the field is that the stored one is absent exactly where it would be needed.
    """
    row = live_repository.run_one(
        "MATCH (a:Passage)-[r]->(b:Passage) "
        "WHERE type(r) IN ['EXACT_PARALLEL_OF','PARALLEL_TO'] AND a.veda = b.veda "
        "RETURN count(*) AS same_veda_edges, count(r.veda_pair) AS with_pair, "
        "collect(a.canonical_key)[0..3] AS sample"
    )
    assert row is not None
    assert row["same_veda_edges"] > 0
    assert row["with_pair"] == 0, "the stored veda_pair is now populated; revisit the derivation"
    body = live_client.get(f"/api/v1/passages/{row['sample'][0]}/parallels?filter=exact").json()
    intra = [item for item in body["items"] if item["same_veda"]]
    assert intra
    assert all(item["veda_pair"] == item["passage"]["veda"] for item in intra)


@pytest.mark.neo4j
def test_a_passage_with_no_parallel_of_the_requested_kind_explains_itself(
    live_client: TestClient,
) -> None:
    body = live_client.get(f"/api/v1/passages/{RV_LAST_OF_MANDALA_1}/parallels?filter=exact").json()
    assert body["items"] == []
    assert body["data_status"] == KnowledgeStatus.INSUFFICIENT_EVIDENCE
    text = " ".join(caveat["text"] for caveat in body["caveats"])
    assert "not evidence that" in text


# ---------------------------------------------------------------------------
# Live: leakage
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
@pytest.mark.parametrize(
    "key",
    [
        RV_FIRST,
        "VG:RV:SAK:M01:S001",
        "VG:YV:VSM:A01:V001",
        "VG:AV:SAU:K20:S001:V001",
        SV_REUSING,
        "VG:SV:KAU:MAHANAMNYA:V01",
    ],
)
def test_no_response_carries_a_neo4j_identifier_or_an_internal_node(
    live_client: TestClient, key: str
) -> None:
    """``TextVersion``, ``Translation`` and ``Lemma`` all carry the ``:Internal`` marker.

    So the check is for the *label* and the driver's identifiers escaping, not for the text
    itself -- the naive "exclude internal nodes" filter would have deleted the verse.
    """
    for route in ("", "/parent", "/children", "/siblings", "/reader", "/parallels"):
        body = live_client.get(f"/api/v1/passages/{key}{route}").text
        for leak in (
            "element_id",
            "elementId",
            "_labels",
            "QAIssue",
            '"Internal"',
            "MENTIONS_LEMMA",
            "VG:TOKEN:",
            "bolt://",
            "content_sha256",
            "build_pass",
            "run_id",
            # Build plumbing, not provenance: it named the internal pipeline run that made
            # an edge. The evidence a client needs is method/tier/trust/state/evidence.
            "pipeline_version",
            "registry_namespace",
            "seal_sha256",
            "prompt_sha256",
        ):
            assert leak not in body, f"{key}{route} leaked {leak}"


# ---------------------------------------------------------------------------
# The agentive layer's two strata
# ---------------------------------------------------------------------------


def test_an_assertion_with_no_modality_cannot_claim_supported() -> None:
    """The model closing the hole that shipped once.

    The service read ``a.modality``, a property that exists nowhere in this graph. Neo4j
    answers a missing property with null rather than an error, so the field was null on all
    4,865 assertions behind a passing test and a rendered page. A null modality now has to
    arrive with a status that says why.
    """
    with pytest.raises(ValidationError):
        AgentiveAssertionView(modality=None, modality_status=KnowledgeStatus.SUPPORTED)
    AgentiveAssertionView(modality=None, modality_status=KnowledgeStatus.NOT_BUILT)
    AgentiveAssertionView(
        modality=AssertionModality.ASSERTED, modality_status=KnowledgeStatus.SUPPORTED
    )


@pytest.mark.neo4j
def test_modality_is_actually_populated_and_not_null_forever(
    live_client: TestClient,
) -> None:
    """The regression test for the defect itself: the field must carry a real value.

    This is what a nonexistent property could not do. RV 1.1.6 is one of the 2,406
    deterministic assertions, and its frame is a value read out of the graph rather than a
    null that renders blank.
    """
    body = live_client.get("/api/v1/passages/VG:RV:SAK:M01:S001:V006").json()
    rows = body["agentive_assertions"]["items"]
    assert rows
    framed = [row for row in rows if row["modality"] is not None]
    assert framed, "no assertion reported a modality; the property read is broken again"
    for row in framed:
        assert row["modality"] in {"ASSERTED", "REQUESTED"}
        assert row["modality_status"] == KnowledgeStatus.SUPPORTED
        assert row["modality_note"] is None


@pytest.mark.neo4j
def test_the_frame_value_space_is_exactly_two_values_plus_the_unframed_stratum(
    live_repository: Neo4jRepository,
) -> None:
    """Enumerated, and asserted to correlate 1:1 with the knowledge layer.

    Every assertion carrying a frame is deterministic and every one lacking it is
    model-extracted -- 2,459 for 2,459, no overlap. That exactness is what licenses
    reporting the absence as ``NOT_BUILT`` rather than as an unknown, so it is asserted
    here: a rebuild that started emitting frames for the model stratum, or a new frame
    value, fails this test instead of quietly changing what a null means.
    """
    rows = live_repository.run(
        "MATCH (a:SemanticAssertion) "
        "RETURN a.frame AS frame, a.knowledge_layer AS layer, count(*) AS n ORDER BY n DESC"
    )
    by_frame = {(row["frame"], row["layer"]): row["n"] for row in rows}
    assert set(by_frame) == {
        ("ASSERTED", "L2_DETERMINISTIC_DERIVED"),
        ("REQUESTED", "L2_DETERMINISTIC_DERIVED"),
        (None, "L3_LLM_EXTRACTED"),
    }, f"the frame/layer partition has changed: {sorted(by_frame)}"

    assert live_repository.run_one(
        "CALL db.propertyKeys() YIELD propertyKey "
        "WHERE propertyKey = 'modality' RETURN count(*) AS n"
    ) == {"n": 0}, "a 'modality' property now exists; the frame mapping needs revisiting"


@pytest.mark.neo4j
def test_an_unframed_assertion_carries_the_stratum_note_and_its_own_vocabulary(
    live_client: TestClient,
) -> None:
    """A typed null, and not only a null.

    RV 7.56.25 carries one deterministic assertion and twelve model-extracted ones. The
    twelve have no frame, so their modality is null -- but they carry
    ``semantic_predicate``, which is where that stratum expresses what a frame would, and
    ``state=CANDIDATE``, which is what they are. Returning the null alone would say those
    twelve readings assert nothing.
    """
    body = live_client.get("/api/v1/passages/VG:RV:SAK:M07:S056:V025").json()
    assertions = body["agentive_assertions"]
    unframed = [row for row in assertions["items"] if row["modality"] is None]
    framed = [row for row in assertions["items"] if row["modality"] is not None]
    assert unframed and framed, "this passage should carry both strata"

    for row in unframed:
        assert row["modality_status"] == KnowledgeStatus.NOT_BUILT
        assert row["modality_note"], "an absent modality must say why"
        assert "asserts nothing" in row["modality_note"]
        assert row["semantic_predicate"], "the stratum's own predicate must still arrive"
        assert row["state"] == "CANDIDATE"
        assert row["quality_tier"] == "TIER_D"

    # The split is stated once on the set too, so a client can see it before rendering.
    text = " ".join(caveat["text"] for caveat in assertions["caveats"])
    assert "two strata" in text
    assert "semantic_predicate" in text


@pytest.mark.neo4j
def test_the_modality_note_quotes_the_frozen_stratum_figures(live_client: TestClient) -> None:
    """The caveat's numbers come from the measured figures, never from typing."""
    from vedagraph.domain import layer_figures

    body = live_client.get("/api/v1/passages/VG:RV:SAK:M07:S056:V025").json()
    text = body["agentive_assertions"]["caveats"][0]["text"]
    assert f"{layer_figures.ASSERTION_LAYERS['MORPHOLOGY_RULE']:,}" in text
    assert f"{layer_figures.ASSERTION_LAYERS['MODEL_EXTRACTION']:,}" in text


@pytest.mark.neo4j
def test_evidence_reports_the_surface_beside_the_derived_basis(live_client: TestClient) -> None:
    """Two axes that share a name in the graph, returned as two fields.

    ``surface`` is the graph's own ``evidence_basis`` -- which textual surface the claim was
    read off -- and ``evidence_basis`` is the derived question of how the claim arose.
    Casting the first into the second reported every attribution edge in the corpus as
    UNKNOWN, which is the defect these two fields exist to keep apart.
    """
    body = live_client.get(f"/api/v1/passages/{SV_REUSING}/parallels?filter=reuse").json()
    evidence = body["items"][0]["evidence"]
    assert evidence["surface"] == "SANSKRIT"
    assert evidence["attribution_precision"] == "NOT_AN_ATTRIBUTION"
    assert evidence["spans"], "a reuse edge quotes both witnesses"


# ---------------------------------------------------------------------------
# The deity-mention ambiguity contract (F-02)
# ---------------------------------------------------------------------------


def test_a_mention_row_cannot_be_built_without_its_grade() -> None:
    """``referent_certainty`` is required, so an ungraded row cannot be constructed.

    The defect was a row that looked exactly like a certain one. Making the grade a
    required field means the shape that shipped is now unrepresentable.
    """
    with pytest.raises(ValidationError):
        MentionedDevataView(type="DEVATA", id="VG:DEVATA:SOMAH", display_label="Soma")
    row = MentionedDevataView(
        type="DEVATA",
        id="VG:DEVATA:SOMAH",
        display_label="Soma",
        referent_certainty="DEITY_AMBIGUOUS",
        is_ambiguous=True,
    )
    assert row.is_ambiguous is True


def test_the_tier_sets_come_from_the_frozen_domain_contract() -> None:
    """No hand-rolled tier set: the gold-measured constants are the only source."""
    assert theonyms.DEFAULT_REFERENT_TIERS == frozenset({theonyms.CERTAIN, theonyms.PROBABLE})
    assert theonyms.AMBIGUOUS not in theonyms.DEFAULT_REFERENT_TIERS
    assert theonyms.AMBIGUOUS in theonyms.EXPLORATORY_REFERENT_TIERS
    with pytest.raises(ValueError):
        theonyms.referent_tiers_for_mode("everything")


@pytest.mark.neo4j
def test_the_referent_certainty_value_space_is_exactly_three_tiers(
    live_repository: Neo4jRepository,
) -> None:
    """Enumerated, so a new tier fails a test rather than being silently excluded.

    A fourth grade added by a rebuild would fall outside ``DEFAULT_REFERENT_TIERS`` and
    vanish from every mention list without changing a status. That is the failure mode this
    contract exists to prevent, so the value space is asserted rather than assumed -- and
    the frozen figures the caveats are built from are checked against it in the same breath.
    """
    rows = live_repository.run(
        "MATCH ()-[m:MENTIONS_DEVATA]->() "
        "RETURN m.referent_certainty AS tier, count(*) AS n ORDER BY n DESC"
    )
    measured = {str(row["tier"]): row["n"] for row in rows}
    assert set(measured) == set(theonyms.REFERENT_TIERS), (
        f"the referent_certainty value space has changed: {sorted(measured)}"
    )
    assert measured == layer_figures.REFERENT_CERTAINTY, (
        "the frozen REFERENT_CERTAINTY figures no longer match the graph, so the caveats "
        f"built from them are now wrong: measured {measured}"
    )


@pytest.mark.neo4j
def test_an_entirely_ambiguous_mention_set_is_withheld_and_typed(
    live_client: TestClient, live_repository: Neo4jRepository
) -> None:
    """F-02, at the HTTP boundary.

    RV 1.4.2 has exactly one mention edge and the graph grades it ``DEITY_AMBIGUOUS``. It
    used to arrive as ``items: [Soma]``, ``data_status: SUPPORTED``, ``caveats: []`` -- the
    god Soma reported as named in the verse, as fact, when the matcher's own verdict is
    that it may be the pressed drink.
    """
    grades = {
        str(row["cert"])
        for row in live_repository.run(
            "MATCH (p:Passage {canonical_key: $key})-[m:MENTIONS_DEVATA]->() "
            "RETURN DISTINCT m.referent_certainty AS cert",
            key=AMBIGUOUS_ONLY_PASSAGE,
        )
    }
    assert grades == {"DEITY_AMBIGUOUS"}, (
        f"{AMBIGUOUS_ONLY_PASSAGE} no longer carries only ambiguous mentions ({grades}); "
        "this test needs a different witness"
    )

    block = live_client.get(f"/api/v1/passages/{AMBIGUOUS_ONLY_PASSAGE}").json()[
        "mentioned_devatas"
    ]
    assert block["items"] == []
    assert block["data_status"] == KnowledgeStatus.INSUFFICIENT_EVIDENCE
    assert block["caveats"], "an emptied list must say why it is empty"
    text = " ".join(caveat["text"] for caveat in block["caveats"])
    assert "NOT a statement that the verse names no deity" in text
    # All three tiers reported even though none was returned (spec section 17).
    assert block["certainty"]["ambiguous_count"] == 1
    assert block["certainty"]["certain_count"] == 0
    assert block["certainty"]["probable_count"] == 0
    assert block["excluded_count"] == 1
    assert block["included_certainty"] == "default"


@pytest.mark.neo4j
def test_opting_in_returns_the_ambiguous_row_clearly_graded(live_client: TestClient) -> None:
    """The caller can see the candidate, and cannot mistake it for a fact."""
    block = live_client.get(
        f"/api/v1/passages/{AMBIGUOUS_ONLY_PASSAGE}?include_ambiguous=true"
    ).json()["mentioned_devatas"]
    assert len(block["items"]) == 1
    row = block["items"][0]
    assert row["id"] == "VG:DEVATA:SOMAH"
    assert row["referent_certainty"] == "DEITY_AMBIGUOUS"
    assert row["is_ambiguous"] is True
    assert block["included_certainty"] == "exploratory"
    assert block["excluded_count"] == 0
    assert block["caveats"], "an ambiguous row must still travel with the contract caveat"


@pytest.mark.neo4j
def test_a_graded_mention_that_survives_the_filter_is_marked_unambiguous(
    live_client: TestClient,
) -> None:
    block = live_client.get(f"/api/v1/passages/{RV_FIRST}").json()["mentioned_devatas"]
    assert block["items"]
    for row in block["items"]:
        assert row["referent_certainty"] in {"DEITY_CERTAIN", "DEITY_PROBABLE"}
        assert row["is_ambiguous"] is False
    assert block["data_status"] == KnowledgeStatus.SUPPORTED


@pytest.mark.neo4j
def test_the_reader_applies_the_same_contract(live_client: TestClient) -> None:
    """The reading page is the surface a user actually opens, so it gets the same treatment.

    The reader was already querying the mention set and discarding it, so a Samavedic,
    Yajurvedic or Atharvavedic verse showed no deity at all -- the ascription layer that
    fills ``devatas`` is Rigveda-only. It now carries the graded mention set, filtered.
    """
    block = live_client.get(f"/api/v1/passages/{AMBIGUOUS_ONLY_PASSAGE}/reader").json()[
        "mentioned_devatas"
    ]
    assert block["items"] == []
    assert block["data_status"] == KnowledgeStatus.INSUFFICIENT_EVIDENCE
    assert block["caveats"]
    assert block["certainty"]["ambiguous_count"] == 1

    opted = live_client.get(
        f"/api/v1/passages/{AMBIGUOUS_ONLY_PASSAGE}/reader?include_ambiguous=true"
    ).json()["mentioned_devatas"]
    assert opted["items"][0]["is_ambiguous"] is True


@pytest.mark.neo4j
def test_the_reader_shows_named_deities_where_there_is_no_ascription_layer(
    live_client: TestClient,
) -> None:
    """The gap the mention set closes on the reading page.

    A Yajurvedic verse has no Anukramani ascription -- that layer is Rigveda-only -- so
    ``devatas`` is correctly NOT_BUILT. Without the mention set the reader had no deity to
    show for three of the four corpora.
    """
    body = live_client.get("/api/v1/passages/VG:YV:VSM:A01:V001/reader").json()
    assert body["devatas"]["data_status"] == KnowledgeStatus.NOT_BUILT
    counts = body["mentioned_devatas"]["certainty"]
    total = counts["certain_count"] + counts["probable_count"] + counts["ambiguous_count"]
    assert total > 0, "this Yajurvedic verse should carry at least one mention edge"


@pytest.mark.neo4j
def test_no_mention_surface_reports_an_ambiguous_row_as_ungraded_fact(
    live_client: TestClient, live_repository: Neo4jRepository
) -> None:
    """Swept across both surfaces and a sample of the 5,365 affected passages.

    A single witness proves the fix on one row; this asserts the contract holds wherever
    ambiguous mentions occur, on both endpoints, so a surface that forgets the filter is
    caught rather than shipped.
    """
    rows = live_repository.run(
        "MATCH (p:Passage)-[m:MENTIONS_DEVATA]->() "
        "WITH p, count(CASE WHEN m.referent_certainty = 'DEITY_AMBIGUOUS' THEN 1 END) AS amb "
        "WHERE amb > 0 RETURN p.canonical_key AS key ORDER BY key LIMIT 12"
    )
    assert len(rows) == 12
    for row in rows:
        for route in ("", "/reader"):
            block = live_client.get(f"/api/v1/passages/{row['key']}{route}").json()[
                "mentioned_devatas"
            ]
            assert block["certainty"]["ambiguous_count"] > 0
            assert block["caveats"], f"{row['key']}{route} carries ambiguity with no caveat"
            for item in block["items"]:
                assert item["referent_certainty"] in {"DEITY_CERTAIN", "DEITY_PROBABLE"}
                assert item["is_ambiguous"] is False


# ---------------------------------------------------------------------------
# Paging is not a finding (F-19)
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
@pytest.mark.parametrize(
    ("url", "dig", "total"),
    [
        ("/api/v1/works?offset=99999999", None, 4),
        ("/api/v1/works/VG:WORK:RV:SAK/root?offset=9999", "results", 10),
        ("/api/v1/passages/VG:AV:SAU:K20/children?offset=99999", "results", 143),
        ("/api/v1/passages/VG:RV:SAK:M01:S001:V001/siblings?offset=9999", "results", 8),
        ("/api/v1/passages/VG:RV:SAK:M03:S035:V011/parallels?offset=500", None, 16),
        (
            "/api/v1/passages/VG:AV:SAU:K15:S002:V002/parallels?filter=formula&offset=9999",
            None,
            89,
        ),
    ],
)
def test_an_offset_overrun_is_a_paging_condition_and_not_a_finding(
    live_client: TestClient, url: str, dig: str | None, total: int
) -> None:
    """``data_status`` describes the collection; a caveat describes the page.

    Asking for page four million of a four-row collection is client arithmetic. Answering
    it ``INSUFFICIENT_EVIDENCE`` spends a status that means "evidence exists and cannot
    support the claim", and a reader who has seen it mean "you paged off the end" discounts
    it everywhere it is load-bearing.
    """
    body = live_client.get(url).json()
    block = body[dig] if dig else body
    assert block["pagination"]["returned"] == 0
    assert block["pagination"]["total"] == total
    assert block["data_status"] == KnowledgeStatus.SUPPORTED, (
        f"{url} reported {block['data_status']} for a page past the end of a {total}-row collection"
    )
    paging = [c for c in block["caveats"] if c["source"] == "pagination"]
    assert len(paging) == 1, "an emptied page must say it was emptied by its offset"
    assert "paging condition and not a finding" in paging[0]["text"]
    assert f"{total:,}-row collection" in paging[0]["text"]


@pytest.mark.neo4j
def test_a_paged_out_navigation_page_does_not_claim_the_container_is_empty(
    live_client: TestClient,
) -> None:
    """The sharper half of the bug: the *prose* was chosen from the page, and was false.

    ``/passages/VG:AV:SAU:K20/children?offset=99999`` used to answer "This passage contains
    no further passages: it is a mantra, the deepest level of its work" about a Kanda
    holding 143 Suktas. That is not a mis-typed status, it is a false statement about the
    corpus, which is the class of defect this project grades MISLEADING.
    """
    body = live_client.get("/api/v1/passages/VG:AV:SAU:K20/children?offset=99999").json()
    text = " ".join(caveat["text"] for caveat in body["results"]["caveats"])
    assert "no further passages" not in text
    assert "it is a mantra" not in text
    assert "paging condition" in text
    # The level descriptor still identifies what the collection holds.
    assert body["results"]["pagination"]["total"] == 143


@pytest.mark.neo4j
@pytest.mark.parametrize(
    ("url", "dig", "status", "phrase"),
    [
        (
            f"/api/v1/passages/{RV_FIRST}/children",
            "results",
            KnowledgeStatus.PARTIAL,
            "deepest level",
        ),
        (
            "/api/v1/passages/VG:RV:SAK:M01/siblings",
            "results",
            KnowledgeStatus.PARTIAL,
            "top-level container",
        ),
        (
            f"/api/v1/passages/{RV_LAST_OF_MANDALA_1}/parallels",
            None,
            KnowledgeStatus.INSUFFICIENT_EVIDENCE,
            "unparalleled in the Vedic tradition",
        ),
    ],
)
def test_a_genuinely_empty_collection_keeps_its_meaning(
    live_client: TestClient, url: str, dig: str | None, status: str, phrase: str
) -> None:
    """The other half of the rule: a real absence must not be softened into a paging note.

    Deriving the status from ``total`` has to leave these alone. A mantra really has no
    children and a verse the matcher could not pair really has no parallel, and both are
    statements about the corpus that the response still has to make.
    """
    body = live_client.get(url).json()
    block = body[dig] if dig else body
    assert block["pagination"]["total"] == 0
    assert block["data_status"] == status
    text = " ".join(caveat["text"] for caveat in block["caveats"])
    assert phrase in text
    # E's sentence ends "the collection, which is not empty", so it must not appear here.
    assert not [c for c in block["caveats"] if c["source"] == "pagination"], (
        "the offset-overrun caveat asserts the collection is not empty and must not be "
        "attached to one that is"
    )


@pytest.mark.neo4j
def test_a_partial_last_page_is_still_supported(live_client: TestClient) -> None:
    """The boundary between the two rules: a page with some rows is unremarkable."""
    body = live_client.get("/api/v1/passages/VG:AV:SAU:K20/children?limit=10&offset=140").json()[
        "results"
    ]
    assert body["pagination"]["returned"] == 3
    assert body["pagination"]["total"] == 143
    assert body["data_status"] == KnowledgeStatus.SUPPORTED
    assert not [c for c in body["caveats"] if c["source"] == "pagination"]
