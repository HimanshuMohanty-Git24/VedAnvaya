"""``/stats`` contract tests.

Two kinds, and the split is the one ``conftest`` describes. The offline tests hold the
contract -- an outage is a 503 that names no host, an empty read is not a confident zero --
and need no Vedic data. The live tests hold the *numbers*, because "the deity count is the
resolved population and not the Anukramani's slot" is a statement about 214 real nodes and
a mock cannot falsify it.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import FakeRepository, build_client
from vedagraph.api.models.common import KnowledgeStatus
from vedagraph.api.models.insight import CostClass

STATS = "/api/v1/stats"

#: Substrings that must never appear in a response body. ``Internal`` and ``QAIssue`` are
#: real graph labels holding 72,514 diagnostic nodes and 915 build findings between them,
#: and neither is Vedic knowledge; the rest are ways for the connection or the query text to
#: escape into a payload.
FORBIDDEN_IN_BODY: tuple[str, ...] = (
    "QAIssue",
    "element_id",
    "elementId",
    "bolt://",
    "localhost",
    "127.0.0.1",
    "7687",
    "password",
    "MATCH (",
    "OPTIONAL MATCH",
    "RETURN ",
)


def _works_rows() -> list[dict[str, Any]]:
    """The scope read, scripted. Four rows, because a per-corpus figure needs all four.

    Written out rather than taken from the graph so the offline suite can exercise the
    envelope's scope rule without a database. The Samavedic scope sentence is the graph's
    own, abbreviated only in the parts these tests do not assert on.
    """
    return [
        {
            "veda": "RV",
            "work_id": "VG:WORK:RV:SAK",
            "traditional_name": "Rigveda Samhita",
            "scope_honest_label": "Rigveda Samhita",
            "scope": "SAMHITA ONLY, Sakala recension.",
            "completeness": "10,552 of 10,552 mantras addressed.",
            "excluded_corpora": ["RIGVEDIC_BRAHMANA"],
            "scope_source": "data/registry/works.yaml",
        },
        {
            "veda": "AV",
            "work_id": "VG:WORK:AV:SAU",
            "traditional_name": "Atharvaveda Samhita",
            "scope_honest_label": "Atharvaveda Samhita - Saunaka recension",
            "scope": "SAMHITA ONLY, Saunaka recension. The PAIPPALADA recension is NOT HELD.",
            "completeness": "5,839 mantras addressed.",
            "excluded_corpora": ["ATHARVAVEDA_PAIPPALADA_RECENSION"],
            "scope_source": "data/registry/works.yaml",
        },
        {
            "veda": "YV",
            "work_id": "VG:WORK:YV:VSM",
            "traditional_name": "Vajasaneyi Samhita",
            "scope_honest_label": "Vajasaneyi Samhita - Shukla Yajurveda",
            "scope": "SAMHITA ONLY, SHUKLA. The KRISHNA Yajurveda is NOT HELD AT ALL.",
            "completeness": "1,975 of 1,975 mantras addressed.",
            "excluded_corpora": ["KRISHNA_YAJURVEDA_TAITTIRIYA"],
            "scope_source": "data/registry/works.yaml",
        },
        {
            "veda": "SV",
            "work_id": "VG:WORK:SV:KAU",
            "traditional_name": "Samaveda Samhita",
            "scope_honest_label": "Samaveda Samhita - Kauthuma arcika only (gana NOT included)",
            "scope": "ARCIKA ONLY. THIS IS NOT THE COMPLETE SAMAVEDA.",
            "completeness": "1,844 verses. ZERO translations are released.",
            "excluded_corpora": ["SAMAVEDA_GRAMAGEYA_GANA", "SAMAVEDA_UHAGANA"],
            "scope_source": "data/registry/works.yaml",
        },
    ]


def _population_row() -> dict[str, Any]:
    """The population read, scripted. Shaped exactly as the one-shot query returns it.

    The two deity figures are deliberately unequal here so the offline contract tests can
    check that both travel and reconcile without depending on the live registry.
    """
    return {
        "works": 4,
        "passages": 22537,
        "translations": 17283,
        "rishi_families": 87,
        "chandas": 575,
        "concepts": 229,
        "philosophical_concepts": 13,
        "rituals": 8,
        "formulas": 4825,
        "formula_families": 720,
        "derived_metrics": 1072,
        "interpretive_claims": 6,
        "mantras_by_veda": [["RV", 10552], ["AV", 5839], ["YV", 1975], ["SV", 1844]],
        "translations_by_veda": [["RV", 10502], ["AV", 4878], ["YV", 1903]],
        "devata_structures": [
            ["INDIVIDUAL", 72],
            ["ABSTRACT", 41],
            ["PAIR", 38],
            ["GROUP", 33],
            ["HUMAN", 22],
            ["PATRON_PRAISE", 7],
            ["UNSPECIFIED", 1],
        ],
        # Mirrors rishi_kinds: the eligibility RULING, which is what the resolved figure is
        # counted from. Deliberately not derivable from the structures above -- the whole
        # point of the offline contract is that the two figures travel independently.
        "devata_rulings": [[True, 157], [False, 57]],
        "rishi_kinds": [[True, None, 616], [False, "DEITY", 58], [False, "ABSTRACTION", 55]],
    }


@pytest.fixture
def scoped_repository() -> FakeRepository:
    """A repository that answers the scope and population reads and nothing else.

    Every other aggregate then runs against empty result sets, which is the interesting
    offline case: a view that reports nothing must say why rather than returning a
    confident empty payload.
    """
    return FakeRepository(
        {
            "w.scope_source AS scope_source": _works_rows(),
            "AS philosophical_concepts": [_population_row()],
        }
    )


@pytest.fixture
def scoped_client(scoped_repository: FakeRepository) -> TestClient:
    app, client = build_client(scoped_repository)
    with client:
        app.state.repository = scoped_repository
        return client


# ---------------------------------------------------------------------------
# Offline: the contract
# ---------------------------------------------------------------------------


def test_stats_is_503_when_the_graph_is_down(down_client: TestClient) -> None:
    response = down_client.get(STATS)
    assert response.status_code == 503
    assert response.json()["error"] == "KNOWLEDGE_GRAPH_UNAVAILABLE"


def test_stats_outage_body_names_no_host_or_query(down_client: TestClient) -> None:
    """A 503 body must describe the product's state and nothing about its deployment."""
    body = down_client.get(STATS).text
    for token in FORBIDDEN_IN_BODY:
        assert token not in body, f"outage body leaked {token!r}"


def test_stats_reports_both_deity_figures_offline_and_they_reconcile(
    scoped_client: TestClient,
) -> None:
    """Both figures travel and the difference is accounted for, whatever the data says.

    Asserted offline as well as live because it is a *shape* contract: a single deity count
    would be wrong for half its readers, and the response must be incapable of publishing
    one even against a registry these tests invented.
    """
    body = scoped_client.get(STATS).json()
    deities = body["deities"]
    assert deities["resolved_deities"] == 157
    assert deities["anukramani_ascriptions"] == 214
    assert (
        deities["resolved_deities"] + deities["excluded_non_deities"]
        == deities["anukramani_ascriptions"]
    )


def test_stats_refuses_to_serve_when_the_corpus_boundaries_cannot_be_read(
    client: TestClient,
) -> None:
    """No scope, no figures.

    An unscripted repository answers the scope read with no rows, and the service turns
    that into a 503 rather than serving per-corpus counts with no exclusions attached. The
    alternative is publishing "1,844" for the Samaveda without "THIS IS NOT THE COMPLETE
    SAMAVEDA", which is the single most misleading string this product can emit.
    """
    response = client.get(STATS)
    assert response.status_code == 503


def test_stats_is_labelled_an_aggregate(scoped_client: TestClient) -> None:
    """The latency exemption has to be visible to the caller that pays for it."""
    body = scoped_client.get(STATS).json()
    assert body["cost_class"] == CostClass.AGGREGATE
    assert body["cost_note"]


def test_stats_carries_every_reported_corpus_scope(scoped_client: TestClient) -> None:
    body = scoped_client.get(STATS).json()
    scoped = {statement["veda"] for statement in body["scope_statements"]}
    assert set(body["vedas_reported"]) <= scoped


def test_stats_never_reports_a_raw_graph_relationship_total(scoped_client: TestClient) -> None:
    """The headline this endpoint deliberately does not have.

    Most of this graph's edges are one annotation layer projecting a container label onto
    the passages inside it. A total over them measures the build, so the response reports
    cross-corpus connections per class instead and no field anywhere carries the graph-wide
    figure.
    """
    body = scoped_client.get(STATS).json()
    names = {figure["name"] for figure in body["corpus"]} | {
        figure["name"] for figure in body["entity_populations"]
    }
    assert not {"relationships", "edges", "relationship_total", "graph_size"} & names


def test_stats_leaks_no_internal_label(scoped_client: TestClient) -> None:
    body = scoped_client.get(STATS).text
    for token in FORBIDDEN_IN_BODY:
        assert token not in body, f"stats body leaked {token!r}"


# ---------------------------------------------------------------------------
# Live: the numbers
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
def test_stats_reports_the_resolved_deity_population_and_the_ascription_slot(
    live_client: TestClient,
) -> None:
    """Both deity figures, labelled, and the resolved one smaller than the slot.

    The frozen graph types 214 nodes ``:Devata`` because the traditional apparatus names a
    devata for every hymn, and 30 of those are human patrons, gift-praise labels or a dog.
    A single deity count would be wrong for half its readers, so this asserts that both are
    present, that they differ, and that the difference reconciles.
    """
    body = live_client.get(STATS).json()
    deities = body["deities"]
    assert deities["resolved_deities"] < deities["anukramani_ascriptions"]
    assert (
        deities["resolved_deities"] + deities["excluded_non_deities"]
        == deities["anukramani_ascriptions"]
    )
    assert deities["resolved_deities"] == 157
    assert deities["anukramani_ascriptions"] == 214
    # The excluded structures must be visible, not merely subtracted.
    assert {"HUMAN", "PATRON_PRAISE"} <= set(deities["by_structure"])


@pytest.mark.neo4j
def test_stats_separates_seers_from_non_seer_addressees(live_client: TestClient) -> None:
    """616 seers and 113 things the seer slot names that are not seers."""
    seers = live_client.get(STATS).json()["seers"]
    assert seers["seers"] == 616
    assert seers["non_seer_addressees"] == 113
    assert seers["non_seer_kinds"]["DEITY"] == 58
    assert sum(seers["non_seer_kinds"].values()) == seers["non_seer_addressees"]


@pytest.mark.neo4j
def test_stats_reports_the_samavedic_translation_zero_as_a_measured_zero(
    live_client: TestClient,
) -> None:
    """The one place in this surface where 0 is the right answer for an empty layer.

    The Samaveda has no released translation, and that is a measured fact about what the
    product holds rather than an unknown -- a null would say "we cannot establish how many
    translations the Samaveda has", which is false. What must not be inferred is anything
    downstream, so the row carries the note that says it: a zero coming out of a
    translation-derived layer is an absent layer and not an absent text.
    """
    body = live_client.get(STATS).json()
    translations = next(figure for figure in body["corpus"] if figure["name"] == "translations")
    assert translations["by_veda"]["sv"] == 0
    assert translations["by_veda"]["status"] != KnowledgeStatus.SUPPORTED
    note = translations["by_veda"]["note"] or ""
    assert "SV" in note
    assert "absent layer, not an absent text" in note
    assert translations["by_veda"]["rv"] == 10510
    assert translations["by_veda"]["yv"] == 1950
    assert translations["by_veda"]["av"] == 5749

    # The Samavedic zero survived an import that put a rendering on 173 of its verses, and
    # it survived because this figure counts a corpus's own English and the reuse is a
    # figure of its own. Both are asserted: a zero that is right by accident -- because the
    # reuse was dropped rather than reported -- would leave a reader unable to find out
    # that any English reaches the corpus at all.
    reused = next(figure for figure in body["corpus"] if figure["name"] == "reused_renderings")
    assert reused["by_veda"]["sv"] == 173
    assert reused["by_veda"]["av"] == 21
    assert reused["by_veda"]["rv"] == 0
    assert reused["total"] == 194
    reused_note = reused["note"] or ""
    assert "Rigvedic" in reused_note, reused_note
    assert "would report a translated Samaveda" in reused_note, reused_note


@pytest.mark.neo4j
def test_stats_mantra_denominators_match_the_corpus_figures(live_client: TestClient) -> None:
    """The denominators a client normalises with, and they are the measured ones."""
    body = live_client.get(STATS).json()
    mantras = next(figure for figure in body["corpus"] if figure["name"] == "mantras")
    assert mantras["by_veda"]["rv"] == 10552
    assert mantras["by_veda"]["sv"] == 1844
    assert mantras["denominator"] == {"RV": 10552, "AV": 5839, "YV": 1975, "SV": 1844}
    assert mantras["total"] == 20210


@pytest.mark.neo4j
def test_stats_cross_veda_classes_are_reported_apart_and_exclude_intra_corpus_edges(
    live_client: TestClient,
) -> None:
    """Per class, cross-corpus only, and the class reaching one pair says so.

    A quarter of the exact-parallel class is Rigveda-internal, and the directed-reuse class
    reaches one corpus pair. Both facts are on the rows: one total over the classes would
    rank a shared vocabulary beside a verbatim repetition, and a class reaching one pair
    read as a finding says only the Samaveda reuses Rigvedic text.
    """
    classes = {
        row["relationship_class"]: row
        for row in live_client.get(STATS).json()["cross_veda_relationships"]
    }
    assert classes["EXACT_PARALLEL_OF"]["cross_veda_edges"] == 750
    assert classes["EXACT_PARALLEL_OF"]["within_one_veda_edges"] == 256
    # Two pairs since the reuse-direction layer was extended; was ["RV-SV"].
    assert classes["REUSES_TEXT_FROM"]["pairs_reached"] == ["AV-RV", "RV-SV"]
    assert "not about what the texts share" in classes["REUSES_TEXT_FROM"]["note"]
    # Every edge of this class stays inside one corpus, so it contributes to no pair.
    assert classes["PARALLEL_TO"]["cross_veda_edges"] == 0
    assert classes["PARALLEL_TO"]["within_one_veda_edges"] == 69
    assert classes["PARALLEL_TO"]["pairs_reached"] == []


@pytest.mark.neo4j
def test_stats_samavedic_figures_carry_the_arcika_disclaimer(live_client: TestClient) -> None:
    """Wherever a Samavedic number appears, so does the graph's own scope sentence."""
    body = live_client.get(STATS).json()
    assert "SV" in body["vedas_reported"]
    samaveda = next(
        statement for statement in body["scope_statements"] if statement["veda"] == "SV"
    )
    assert "NOT THE COMPLETE SAMAVEDA" in (samaveda["scope"] or "").upper()
    assert samaveda["excluded_corpora"]
    assert "gana" in (samaveda["scope_honest_label"] or "").lower()


@pytest.mark.neo4j
def test_stats_body_leaks_no_internal_content(live_client: TestClient) -> None:
    body = live_client.get(STATS).text
    for token in FORBIDDEN_IN_BODY:
        assert token not in body, f"stats body leaked {token!r}"
    # `Internal` is checked separately: the word is legitimate English and the label is not,
    # so this looks for the label form rather than for the substring.
    assert '"Internal"' not in body
    assert ":Internal" not in body


@pytest.mark.neo4j
def test_stats_is_json_serialisable_without_surprises(live_client: TestClient) -> None:
    """A guard against a driver type escaping into the payload."""
    json.dumps(live_client.get(STATS).json())
