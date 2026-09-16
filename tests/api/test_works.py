"""The works endpoints: two names kept apart, and a scope that reaches the client.

The offline tests here own the contract -- that a bad limit is 422, that an unknown work id
is 404 and not an empty record, that a dead graph is 503 with no hostname in the body, that
a layer with no edges is ``NOT_BUILT`` and not a measured zero. None of that needs Vedic
data and running it against the live graph would only make it slow.

The live tests own the facts, and they are the ones that matter here: whether the Samaveda
really does say *arcika only* through the API, whether its translation count really is
zero, whether the hierarchy this API derives for each Veda really is the hierarchy the
graph records. This project has twice certified an absence against the wrong surface, and
a work endpoint that asserted the Samavedic exclusion from a hand-written constant would be
a third opportunity.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import FakeRepository, build_client
from vedagraph.api.config import EXPECTED_WORK_IDS, MAX_PAGE_SIZE
from vedagraph.api.models.common import KnowledgeStatus
from vedagraph.api.services.passage_service import (
    LEVEL_ORDER,
    NATIVE_LEVEL_LABELS,
    PassageService,
)

WORKS_NEEDLE = "MATCH (w:Work)\nCALL (w)"
WORK_NEEDLE = "MATCH (w:Work {work_id: $work_id})"

#: A Samavedic row shaped like the graph's, because the Samaveda is the work every contract
#: in this module exists for: a true traditional name over a corpus that is a fraction of
#: what that name denotes.
SAMAVEDA_ROW: dict[str, Any] = {
    "work_id": "VG:WORK:SV:KAU",
    "veda": "SV",
    "abbreviation": "SV",
    "display_label": "Samaveda Samhita - Kauthuma arcika only (gana corpus NOT included)",
    "work_name": "Samaveda Samhita",
    "scope": "ARCIKA ONLY. THIS IS NOT THE COMPLETE SAMAVEDA.",
    "scope_source": "data/registry/works.yaml",
    "scope_evidence": "manifest",
    "completeness": "1,844 of the traditional 1,875 verses carry a canonical key (98.3%).",
    "excluded_corpora": ["SAMAVEDA_GRAMAGEYA_GANA", "SAMAVEDA_UHAGANA"],
    "rights": "Per manifest.",
    "passage_count": 2342,
    "mantra_count": 1844,
    # The four coverage populations the works query returns, each measured on its own
    # definition. The Samaveda is zero on all four and 1,844 uncovered, which is what makes
    # it the right fixture for this endpoint: every translation-derived layer is empty for
    # it, and a single `translated_count` could not say whether that was because nothing
    # was aligned or because what reached it was another corpus's English.
    "dedicated_count": 0,
    "range_covered_count": 0,
    "reused_count": 0,
    "other_language_count": 0,
    "any_coverage_count": 0,
    "translators": [],
}


@pytest.fixture
def works_repository() -> FakeRepository:
    return FakeRepository({WORK_NEEDLE: [SAMAVEDA_ROW], WORKS_NEEDLE: [SAMAVEDA_ROW]})


@pytest.fixture
def works_app(works_repository: FakeRepository) -> Any:
    app, client = build_client(works_repository)
    with client:
        app.state.repository = works_repository
        yield client


# ---------------------------------------------------------------------------
# The two names
# ---------------------------------------------------------------------------


def test_display_label_and_traditional_name_are_separate_fields(works_app: TestClient) -> None:
    """The one defect this endpoint exists to prevent, asserted on the list route.

    ``work_name`` is *Samaveda Samhita* over a corpus that is the Kauthuma arcika only.
    Both names are true; only one of them describes what is held. They must arrive as
    distinct fields so a client cannot render the wrong one by reading the obvious key.
    """
    row = works_app.get("/api/v1/works").json()["items"][0]
    assert row["display_label"] != row["traditional_name"]
    assert "gana corpus NOT included" in row["display_label"]
    assert row["traditional_name"] == "Samaveda Samhita"


def test_no_response_field_is_called_work_name(works_app: TestClient) -> None:
    """There is no key a client can read that returns the traditional name as the label."""
    body = works_app.get("/api/v1/works").json()
    assert "work_name" not in body["items"][0]
    detail = works_app.get("/api/v1/works/VG:WORK:SV:KAU").json()
    assert "work_name" not in detail


def test_list_carries_the_corpus_scope_caveat(works_app: TestClient) -> None:
    """The list route is where a work picker is built, so the caveat travels with it."""
    body = works_app.get("/api/v1/works").json()
    assert body["caveats"]
    text = " ".join(caveat["text"] for caveat in body["caveats"])
    assert "arcika" in text
    assert "Krishna Yajurveda" in text or "Krishna" in text


def test_excluded_corpora_are_a_filterable_list_not_only_prose(works_app: TestClient) -> None:
    row = works_app.get("/api/v1/works").json()["items"][0]
    assert "SAMAVEDA_GRAMAGEYA_GANA" in row["excluded_corpora"]


def test_scope_is_returned_verbatim_and_not_paraphrased(works_app: TestClient) -> None:
    detail = works_app.get("/api/v1/works/VG:WORK:SV:KAU").json()
    assert detail["scope"] == SAMAVEDA_ROW["scope"]
    assert detail["completeness"] == SAMAVEDA_ROW["completeness"]


# ---------------------------------------------------------------------------
# Zero against unknown
# ---------------------------------------------------------------------------


def test_zero_translations_is_reported_with_a_status_and_a_caveat(works_app: TestClient) -> None:
    """A measured zero is allowed to be zero -- but never a bare zero.

    The Samaveda genuinely has no translations, so 0 is the right number. What it must not
    do is arrive as a plain 0 beside ``SUPPORTED``, because every translation-derived layer
    is empty for that corpus as a consequence and a client has to be told once.
    """
    detail = works_app.get("/api/v1/works/VG:WORK:SV:KAU").json()
    coverage = detail["translation_coverage"]
    assert coverage["translated"] == 0
    # All four populations, because "the Samaveda has no translation" is now four separate
    # measured zeros and a reader is entitled to see that each was measured.
    assert coverage["dedicated"] == 0
    assert coverage["range_covered"] == 0
    assert coverage["reused_rendering"] == 0
    assert coverage["other_language"] == 0
    assert coverage["uncovered"] == coverage["mantras"]
    assert coverage["status"] == KnowledgeStatus.NOT_BUILT
    assert any("Zero" in caveat["text"] for caveat in coverage["caveats"])
    assert detail["data_status"] != KnowledgeStatus.SUPPORTED


def test_a_layer_with_no_edges_reports_null_and_not_zero(works_app: TestClient) -> None:
    """``NOT_BUILT`` with null counts, because a zero here reads as a godless corpus."""
    detail = works_app.get("/api/v1/works/VG:WORK:SV:KAU").json()
    layers = {layer["layer"]: layer for layer in detail["knowledge_layers"]}
    ascription = layers["DEVATA_ASCRIPTION"]
    assert ascription["status"] == KnowledgeStatus.NOT_BUILT
    assert ascription["passages"] is None
    assert ascription["edges"] is None
    assert "not a godless verse" in ascription["note"]


def test_attribution_split_is_reported_apart_and_never_summed(works_app: TestClient) -> None:
    detail = works_app.get("/api/v1/works/VG:WORK:SV:KAU").json()
    splits = {split["layer"]: split for split in detail["attribution_splits"]}
    assert "HAS_RISHI" in splits
    assert "source_stated" in splits["HAS_RISHI"]
    assert "container_inherited" in splits["HAS_RISHI"]
    assert "must not be summed" in splits["HAS_RISHI"]["note"]
    # No field offers the sum, so a client cannot read one by accident.
    assert "total" not in splits["HAS_RISHI"]


def test_empty_first_page_does_not_claim_supported() -> None:
    repository = FakeRepository({})
    app, client = build_client(repository)
    with client:
        app.state.repository = repository
        body = client.get("/api/v1/works").json()
    assert body["items"] == []
    assert body["data_status"] != KnowledgeStatus.SUPPORTED
    assert body["caveats"]


# ---------------------------------------------------------------------------
# Errors and bounds
# ---------------------------------------------------------------------------


def test_unknown_work_id_is_404_and_not_an_empty_record() -> None:
    repository = FakeRepository({})
    app, client = build_client(repository)
    with client:
        app.state.repository = repository
        response = client.get("/api/v1/works/VG:WORK:XX:YYY")
    assert response.status_code == 404
    body = response.json()
    assert body["error"] == "WORK_NOT_FOUND"
    assert body["hint"]


@pytest.mark.parametrize(
    "url",
    [
        f"/api/v1/works?limit={MAX_PAGE_SIZE + 1}",
        "/api/v1/works?limit=0",
        "/api/v1/works?offset=-1",
        f"/api/v1/works/VG:WORK:SV:KAU/root?limit={MAX_PAGE_SIZE + 1}",
        "/api/v1/works/VG:WORK:SV:KAU/root?offset=-1",
    ],
)
def test_out_of_range_pagination_is_422(works_app: TestClient, url: str) -> None:
    """422 and not a silently truncated page: truncation looks like 'that is all there is'."""
    response = works_app.get(url)
    assert response.status_code == 422
    assert response.json()["error"] == "VALIDATION_ERROR"


@pytest.mark.parametrize(
    "url",
    [
        "/api/v1/works",
        "/api/v1/works/VG:WORK:RV:SAK",
        "/api/v1/works/VG:WORK:RV:SAK/root",
    ],
)
def test_graph_down_is_503_and_leaks_nothing(down_client: TestClient, url: str) -> None:
    response = down_client.get(url)
    assert response.status_code == 503
    body = response.text.lower()
    for secret in ("bolt", "localhost", "7687", "neo4j", "password", "match (", "cypher"):
        assert secret not in body


def test_no_client_string_is_spliced_into_cypher(works_repository: FakeRepository) -> None:
    """Every client value travels bound. Asserted against what reached the driver."""
    app, client = build_client(works_repository)
    with client:
        app.state.repository = works_repository
        client.get("/api/v1/works/VG:WORK:SV:KAU")
    assert works_repository.calls
    assert "VG:WORK:SV:KAU" not in works_repository.query_text
    assert works_repository.all_parameters["work_id"] == "VG:WORK:SV:KAU"


def test_no_neo4j_internal_identifier_in_a_work_response(works_app: TestClient) -> None:
    for url in ("/api/v1/works", "/api/v1/works/VG:WORK:SV:KAU"):
        body = works_app.get(url).text
        for leak in ("element_id", "elementId", '"id()"', "_labels", "QAIssue", '"Internal"'):
            assert leak not in body


# ---------------------------------------------------------------------------
# The shared level map, checked without a database
# ---------------------------------------------------------------------------


def test_level_order_covers_every_named_level() -> None:
    """The order and the label map must describe the same set of levels.

    If they drift, a level gets a name and no position or a position and no name, and a
    breadcrumb trail silently reorders. Cheaper to fail here than to read it in a payload.
    """
    assert set(LEVEL_ORDER) == set(NATIVE_LEVEL_LABELS)
    assert len(LEVEL_ORDER) == len(set(LEVEL_ORDER))


@pytest.mark.parametrize(
    ("veda", "levels"),
    [
        ("RV", ("mandala", "sukta", "mantra")),
        ("AV", ("kanda", "sukta", "mantra")),
        ("YV", ("adhyaya", "mantra")),
        ("SV", ("collection", "prapathaka", "ardha", "dasati", "verse")),
    ],
)
def test_each_vedas_levels_are_a_subsequence_of_the_one_global_order(
    veda: str, levels: tuple[str, ...]
) -> None:
    """One total order serves four corpora, which is why there is no per-Veda branch.

    This is the assumption the whole navigator rests on. If a rebuild introduced a Veda
    whose nesting contradicted another's, sorting by ``LEVEL_ORDER`` would silently emit
    the wrong depth order, and this test is what refuses that.
    """
    ranks = [LEVEL_ORDER.index(level) for level in levels]
    assert ranks == sorted(ranks), f"{veda} levels are not in LEVEL_ORDER order"


def test_recension_code_comes_from_the_work_id() -> None:
    assert PassageService._recension_code("VG:WORK:SV:KAU") == "KAU"
    assert PassageService._recension_code("VG:WORK:RV:SAK") == "SAK"
    assert PassageService._recension_code("nonsense") is None


# ---------------------------------------------------------------------------
# Live graph
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
def test_all_four_works_are_returned(live_client: TestClient) -> None:
    body = live_client.get("/api/v1/works").json()
    assert {item["work_id"] for item in body["items"]} == set(EXPECTED_WORK_IDS)
    assert body["pagination"]["total"] == 4


@pytest.mark.neo4j
def test_samaveda_says_arcika_only_through_the_api(live_client: TestClient) -> None:
    """The single most misleading string in this graph, checked at the HTTP boundary."""
    detail = live_client.get("/api/v1/works/VG:WORK:SV:KAU").json()
    assert "arcika only" in detail["display_label"]
    assert "gana corpus NOT included" in detail["display_label"]
    assert detail["traditional_name"] == "Samaveda Samhita"
    assert "THIS IS NOT THE COMPLETE SAMAVEDA" in detail["scope"]
    assert any("GANA" in item for item in detail["excluded_corpora"])


@pytest.mark.neo4j
def test_yajurveda_says_the_krishna_recension_is_not_held(live_client: TestClient) -> None:
    detail = live_client.get("/api/v1/works/VG:WORK:YV:VSM").json()
    assert "NOT HELD AT ALL" in detail["scope"]
    assert "Krishna Yajurveda NOT included" in detail["display_label"]


@pytest.mark.neo4j
def test_atharvaveda_says_paippalada_is_not_held(live_client: TestClient) -> None:
    detail = live_client.get("/api/v1/works/VG:WORK:AV:SAU").json()
    assert "PAIPPALADA recension is NOT HELD" in detail["scope"]
    assert "Paippalada NOT included" in detail["display_label"]


@pytest.mark.neo4j
def test_samaveda_translation_count_is_measured_as_zero(live_client: TestClient) -> None:
    """Measured, not asserted. If the Samaveda ever gains a translation this must change.

    The brief for this work said to verify the Samavedic translation count rather than
    trust it, because a zero there is a first-class coverage fact that several other
    endpoints inherit.
    """
    coverage = live_client.get("/api/v1/works/VG:WORK:SV:KAU").json()["translation_coverage"]
    assert coverage["mantras"] == 1844
    assert coverage["translated"] == 0
    assert coverage["percent"] == 0.0
    assert coverage["status"] == KnowledgeStatus.NOT_BUILT
    assert coverage["translators"] == [], (
        "a name reaches `translators` only if it translated this corpus; Griffith appears "
        "on 173 Samavedic verses and translated none of them"
    )
    assert coverage["reused_from_translators"] == ["Ralph T. H. Griffith"], (
        "the reuse must be visible somewhere, and this is where: apart from `translators` "
        "rather than absent from the response"
    )
    assert coverage["reused_rendering"] == 173


#: Per corpus: mantras, verses with a rendering of their own, and verses reached only by a
#: multi-verse print unit.
#:
#: Two things moved these figures and they moved in opposite directions, which is why the
#: third column exists. The bulk translation import raised all three translated counts. And
#: `translated` narrowed to mean a verse's *own* rendering, so the 30 anchors of the
#: RV 1.65-1.70 spans left it: Griffith renders each pair of dvipada verses as one unit, so
#: those renderings cover 60 verses and none of the 60 has a translation aligned to it
#: alone. The Atharvaveda gained 34 more such spans over 68 verses. Asserting the range
#: population beside the dedicated one is what makes the narrowing visible -- a coverage
#: figure that fell with nothing to account for it is indistinguishable from a regression.
@pytest.mark.neo4j
@pytest.mark.parametrize(
    ("work_id", "mantras", "translated", "range_covered"),
    [
        ("VG:WORK:RV:SAK", 10_552, 10_479, 60),
        ("VG:WORK:YV:VSM", 1_975, 1_939, 0),
        ("VG:WORK:AV:SAU", 5_839, 5_715, 68),
        ("VG:WORK:SV:KAU", 1_844, 0, 0),
    ],
)
def test_translation_coverage_is_divided_from_the_counts_in_the_response(
    live_client: TestClient, work_id: str, mantras: int, translated: int, range_covered: int
) -> None:
    """The percentage is computed from the two numbers beside it, never transcribed.

    Copying a figure out of the work's ``completeness`` prose is how three caveats in this
    repository drifted from the data they described.
    """
    coverage = live_client.get(f"/api/v1/works/{work_id}").json()["translation_coverage"]
    assert coverage["mantras"] == mantras
    assert coverage["translated"] == translated
    assert coverage["percent"] == round(100 * translated / mantras, 2)
    assert coverage["range_covered"] == range_covered, (
        "the verses a multi-verse print unit covers are a population of their own; folding "
        "them into `translated` asserts each has a 1:1 rendering, and dropping them "
        "asserts no translation reaches them"
    )
    assert coverage["translated"] == coverage["dedicated"]


@pytest.mark.neo4j
@pytest.mark.parametrize(
    ("work_id", "expected"),
    [
        ("VG:WORK:RV:SAK", ["mandala", "sukta", "mantra"]),
        ("VG:WORK:AV:SAU", ["kanda", "sukta", "mantra"]),
        ("VG:WORK:YV:VSM", ["adhyaya", "mantra"]),
        ("VG:WORK:SV:KAU", ["collection", "prapathaka", "ardha", "dasati", "verse"]),
    ],
)
def test_each_work_reports_its_own_hierarchy_in_depth_order(
    live_client: TestClient, work_id: str, expected: list[str]
) -> None:
    """Derived from the hierarchy keys, including for the Rigveda, which stores no labels."""
    detail = live_client.get(f"/api/v1/works/{work_id}").json()
    assert [level["key"] for level in detail["hierarchy"]] == expected
    assert all(level["native_label"] for level in detail["hierarchy"])


@pytest.mark.neo4j
@pytest.mark.neo4j
def test_the_samavedic_translation_layer_discloses_its_reuse(live_client: TestClient) -> None:
    """The layer reaches the Samaveda; the note must say what it reaches it with.

    Without this, ``TRANSLATION`` appearing beside all four work ids is indistinguishable
    from a translated Samaveda -- and the corpus has no released translation of its own.
    """
    detail = live_client.get("/api/v1/works/VG:WORK:SV:KAU").json()
    layer = next(row for row in detail["knowledge_layers"] if row["layer"] == "TRANSLATION")
    assert layer["passages"] == 173
    note = layer["note"]
    assert "zero released" in note, f"the note must not imply a translated Samaveda: {note}"
    assert "reuse" in note.lower(), f"the note must name the reuse: {note}"


def test_the_samavedic_collection_level_is_declared_name_valued(live_client: TestClient) -> None:
    """A client that assumed integers throughout would fail on 1,844 verses."""
    detail = live_client.get("/api/v1/works/VG:WORK:SV:KAU").json()
    kinds = {level["key"]: level["value_kind"] for level in detail["hierarchy"]}
    assert kinds["collection"] == "NAME"
    assert kinds["verse"] == "ORDINAL"


@pytest.mark.neo4j
@pytest.mark.parametrize(
    ("layer", "reaches"),
    [
        ("DEVATA_ASCRIPTION", {"VG:WORK:RV:SAK"}),
        ("AGENTIVE_ASSERTION", {"VG:WORK:RV:SAK"}),
        ("DEVATA_ASCRIPTION_DESCRIPTOR", {"VG:WORK:AV:SAU"}),
        ("CHANDAS_ATTRIBUTION", {"VG:WORK:RV:SAK", "VG:WORK:AV:SAU"}),
        ("RISHI_ATTRIBUTION", {"VG:WORK:RV:SAK", "VG:WORK:AV:SAU", "VG:WORK:YV:VSM"}),
        # All four, and the Samavedic reach is not a translated Samaveda. The
        # HAS_TRANSLATION relation now touches 173 of its verses because each carries
        # Griffith's Rigvedic rendering of verified-identical text; the layer's own note
        # says so, and test_the_samavedic_translation_layer_discloses_its_reuse below
        # asserts that it does rather than trusting this set to carry the meaning.
        ("TRANSLATION", set(EXPECTED_WORK_IDS)),
        ("DEVATA_MENTION", set(EXPECTED_WORK_IDS)),
        ("FORMULA_OCCURRENCE", set(EXPECTED_WORK_IDS)),
        ("ENTITY_MENTION", set(EXPECTED_WORK_IDS)),
        ("CONCEPT_ASSERTION", set(EXPECTED_WORK_IDS)),
    ],
)
def test_layer_availability_is_measured_and_uneven(
    live_client: TestClient, layer: str, reaches: set[str]
) -> None:
    """The reach of each layer, measured per work rather than declared anywhere.

    The pattern is not guessable and that is the point: deity ascription is Rigveda-only
    while the Atharvavedic ascription *descriptor* layer is Atharvaveda-only, and the two
    would look like the same layer to anyone reading only their names.
    """
    supported = set()
    for work_id in EXPECTED_WORK_IDS:
        detail = live_client.get(f"/api/v1/works/{work_id}").json()
        row = next(item for item in detail["knowledge_layers"] if item["layer"] == layer)
        if row["status"] == KnowledgeStatus.SUPPORTED:
            assert row["passages"] and row["passages"] > 0
            supported.add(work_id)
        else:
            assert row["status"] == KnowledgeStatus.NOT_BUILT
            assert row["passages"] is None
    assert supported == reaches


@pytest.mark.neo4j
def test_atharvavedic_seer_attribution_is_entirely_inherited(live_client: TestClient) -> None:
    """Two corpora at opposite ends of the same axis, which is why they are never summed."""
    av = live_client.get("/api/v1/works/VG:WORK:AV:SAU").json()
    yv = live_client.get("/api/v1/works/VG:WORK:YV:VSM").json()
    av_rishi = next(s for s in av["attribution_splits"] if s["layer"] == "HAS_RISHI")
    yv_rishi = next(s for s in yv["attribution_splits"] if s["layer"] == "HAS_RISHI")
    assert av_rishi["source_stated"] == 0
    assert av_rishi["container_inherited"] == 5084
    assert yv_rishi["container_inherited"] == 0
    assert yv_rishi["source_stated"] == 1960


@pytest.mark.neo4j
def test_text_scripts_are_disjoint_across_the_corpus(live_client: TestClient) -> None:
    """No work holds both scripts, so a script list is a fact and not a preference."""
    scripts = {
        work_id: live_client.get(f"/api/v1/works/{work_id}").json()["text_scripts"]
        for work_id in EXPECTED_WORK_IDS
    }
    assert scripts["VG:WORK:RV:SAK"] == ["IAST"]
    assert scripts["VG:WORK:AV:SAU"] == ["IAST"]
    assert scripts["VG:WORK:YV:VSM"] == ["DEVANAGARI"]
    assert scripts["VG:WORK:SV:KAU"] == ["DEVANAGARI"]


@pytest.mark.neo4j
def test_work_root_returns_the_samavedic_collections_in_stored_order(
    live_client: TestClient,
) -> None:
    """Traditional order, not alphabetical order.

    The stored sequence is Chanda, Aranyaka, Mahanamnya, Uttara. Sorting the keys instead
    would put Aranyaka first, and the same mistake in the reader's next-passage query would
    skip all 55 Aranyaka verses.
    """
    body = live_client.get("/api/v1/works/VG:WORK:SV:KAU/root").json()
    keys = [item["canonical_key"] for item in body["results"]["items"]]
    assert keys == [
        "VG:SV:KAU:CHANDA",
        "VG:SV:KAU:ARANYA",
        "VG:SV:KAU:MAHANAMNYA",
        "VG:SV:KAU:UTTARA",
    ]
    assert keys != sorted(keys), "alphabetical order would be a different, wrong answer"
    assert body["root_level"]["key"] == "collection"
    assert body["root_level"]["native_label"] == "Collection"


@pytest.mark.neo4j
@pytest.mark.parametrize(
    ("work_id", "total", "level"),
    [
        ("VG:WORK:RV:SAK", 10, "Mandala"),
        ("VG:WORK:AV:SAU", 20, "Kanda"),
        ("VG:WORK:YV:VSM", 40, "Adhyaya"),
        ("VG:WORK:SV:KAU", 4, "Collection"),
    ],
)
def test_each_work_enters_at_its_own_level(
    live_client: TestClient, work_id: str, total: int, level: str
) -> None:
    body = live_client.get(f"/api/v1/works/{work_id}/root").json()
    assert body["results"]["pagination"]["total"] == total
    assert body["root_level"]["native_label"] == level


@pytest.mark.neo4j
def test_work_root_pagination_is_honest_past_the_end(live_client: TestClient) -> None:
    body = live_client.get("/api/v1/works/VG:WORK:SV:KAU/root?offset=10").json()
    assert body["results"]["items"] == []
    assert body["results"]["pagination"]["total"] == 4
    assert body["results"]["pagination"]["has_more"] is False


@pytest.mark.neo4j
def test_live_work_responses_carry_no_neo4j_identifier(live_client: TestClient) -> None:
    for work_id in EXPECTED_WORK_IDS:
        for suffix in ("", "/root"):
            body = live_client.get(f"/api/v1/works/{work_id}{suffix}").text
            for leak in ("element_id", "elementId", "_labels", "QAIssue", "corpus_dir"):
                assert leak not in body, f"{work_id}{suffix} leaked {leak}"
