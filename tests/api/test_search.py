"""Search: the ladder, the surfaces it cannot reach, and the strings it must not parse.

Three groups of tests, and each one guards a different way search can lie.

*Injection.* Every assertion is made against ``fake_repository.query_text`` -- what the
driver was actually asked -- rather than against a status code. A 200 proves nothing: a
query that spliced a client string in and happened to stay syntactically valid also
returns 200. The user's string must appear in the bound parameters and nowhere in the
Cypher.

*Ranking.* The ladder IS the ranking, so the test that matters is that a page's scores
never rise as you read down it, and that an exact entity label outranks a formula prefix.
This caught a live defect during the build: ``ORDER BY match_type`` inside the entity query
sorted the rung names ALPHABETICALLY, so ``CONCEPT_MATCH`` came first, the row budget was
spent on definition matches, and a search for "Indra" never returned ``VG:DEVATA:INDRAH``
at all.

*Coverage.* :data:`~vedagraph.api.services.search_service.SURFACE_COVERAGE` is asserted
against the live graph, in the manner of :mod:`vedagraph.domain.layer_figures`, because
those figures are quoted verbatim in the caveat on every response that reads the surface.
There is no Samavedic English translation in this graph, and a response that let a caller
believe otherwise would be the search-shaped version of this project's oldest defect.
"""

from __future__ import annotations

import time
import unicodedata
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.api.conftest import FakeRepository
from tests.api.test_devatas import KNOWN_NON_DEITY_LABELS, assert_no_internals
from vedagraph.api.models.entity import ENTITY_TYPE_NAMES
from vedagraph.api.models.search import (
    MATCH_TYPE_ORDER,
    MATCH_TYPE_SCORES,
    SPECIFIED_RESULT_TYPES,
    MatchType,
    SearchLanguage,
    SearchResultType,
    SearchSurface,
)
from vedagraph.api.repositories.neo4j_repository import Neo4jRepository
from vedagraph.api.services.search_service import (
    ALL_QUERY_TEMPLATES,
    DIACRITIC_MARKS,
    DIACRITIC_REPERTOIRE_QUERY,
    RUNG_ORDER,
    SANSKRIT_ASCII_BIGRAMS,
    SANSKRIT_ASCII_TRIGRAMS,
    SANSKRIT_REPERTOIRE_QUERY,
    SEARCH_WINDOW_LIMIT,
    SURFACE_COVERAGE,
    SURFACE_NOTES,
    SearchService,
    fold_diacritics,
    marks_present_in,
    measure_surface_coverage,
    sanskrit_cannot_contain,
    sanskrit_repertoire_from,
)

#: Everything the specification requires a search to survive, plus a Cypher payload.
METACHARACTERS = "\" ' \\ { } ( ) ~ * ? : ^ ] ["
INJECTIONS = [
    "MATCH (n) DETACH DELETE n",
    METACHARACTERS,
    "agni AND NOT indra OR *:*",
    "') DETACH DELETE (n) RETURN 1 AS x",
    "indra~2^10",
    "a" * 200,
]


# ---------------------------------------------------------------------------
# The ladder as data
# ---------------------------------------------------------------------------


def test_the_ladder_is_total_and_strictly_descending() -> None:
    assert len(MATCH_TYPE_ORDER) == len(MatchType) == len(MATCH_TYPE_SCORES)
    scores = [MATCH_TYPE_SCORES[rung] for rung in MATCH_TYPE_ORDER]
    assert scores == sorted(scores, reverse=True)
    assert len(set(scores)) == len(scores), "two rungs sharing a score is not a ranking"
    assert MATCH_TYPE_ORDER[0] is MatchType.EXACT_CANONICAL_KEY
    assert MATCH_TYPE_ORDER[-1] is MatchType.CONCEPT_MATCH


def test_the_cypher_rung_order_is_the_documented_ladder() -> None:
    """The bound ordering map must be derived from the ladder, not a copy of it.

    Sorted as strings, ``CONCEPT_MATCH`` < ``EXACT_ENTITY_LABEL`` < ``PREFIX_ENTITY_LABEL``,
    which is the wrong order and was measured returning the wrong page.
    """
    assert RUNG_ORDER == {rung.value: index for index, rung in enumerate(MATCH_TYPE_ORDER)}
    assert RUNG_ORDER["EXACT_ENTITY_LABEL"] < RUNG_ORDER["CONCEPT_MATCH"]
    assert RUNG_ORDER["EXACT_ALIAS"] < RUNG_ORDER["PREFIX_ENTITY_LABEL"]


def test_every_knowledge_type_is_searchable() -> None:
    """A type without a result type is silently unsearchable, which is an empty answer."""
    result_types = {member.value for member in SearchResultType}
    missing = ENTITY_TYPE_NAMES - result_types
    assert not missing, f"unsearchable knowledge types: {sorted(missing)}"
    assert len(SPECIFIED_RESULT_TYPES) == 11
    assert all(member in SearchResultType for member in SPECIFIED_RESULT_TYPES)


def test_every_surface_with_declared_coverage_has_a_note() -> None:
    assert set(SURFACE_COVERAGE) <= set(SURFACE_NOTES)
    for surface, note in SURFACE_NOTES.items():
        assert len(note) > 60, f"{surface} has a note too short to say anything"


# ---------------------------------------------------------------------------
# Parameterisation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("payload", INJECTIONS)
def test_the_query_string_never_reaches_the_query_text(
    client: TestClient, fake_repository: FakeRepository, payload: str
) -> None:
    response = client.get("/api/v1/search", params={"q": payload})
    assert response.status_code == 200, response.text
    assert fake_repository.calls, "no query ran, so this assertion proves nothing"
    assert payload not in fake_repository.query_text
    assert payload.lower() not in fake_repository.query_text.lower()
    bound = {value for value in fake_repository.all_parameters.values() if isinstance(value, str)}
    assert payload in bound or payload.lower() in bound, (
        "the string must have travelled bound, not been silently dropped"
    )


@pytest.mark.parametrize("payload", INJECTIONS)
def test_every_query_issued_comes_from_the_closed_template_set(
    client: TestClient, fake_repository: FakeRepository, payload: str
) -> None:
    """No input can synthesise a query. The stronger form of "nothing is interpolated".

    This deliberately does NOT assert that the query text is identical whatever the user
    typed: the repertoire prefilter makes *which* templates run depend on the query's
    letters, and that is the optimisation working. What must hold is that every query the
    driver is ever asked is one of the eight fixed templates, verbatim.
    """
    client.get("/api/v1/search", params={"q": payload})
    assert fake_repository.calls, "no query ran, so this assertion proves nothing"
    for cypher, _ in fake_repository.calls:
        assert cypher in ALL_QUERY_TEMPLATES, (
            "search issued a query outside the closed template set, so something was built "
            f"from input: {cypher[:200]!r}"
        )


def test_filters_travel_bound_too(client: TestClient, fake_repository: FakeRepository) -> None:
    client.get("/api/v1/search", params={"q": "agni", "veda": "RV", "work": "VG:WORK:RV:SAK"})
    assert "VG:WORK:RV:SAK" not in fake_repository.query_text
    assert fake_repository.all_parameters["work"] == "VG:WORK:RV:SAK"
    assert fake_repository.all_parameters["veda"] == "RV"


# ---------------------------------------------------------------------------
# Refusals
# ---------------------------------------------------------------------------


def test_an_empty_query_is_refused(client: TestClient) -> None:
    assert client.get("/api/v1/search", params={"q": ""}).status_code == 422
    assert client.get("/api/v1/search").status_code == 422


def test_a_whitespace_query_is_a_400_with_a_hint(client: TestClient) -> None:
    response = client.get("/api/v1/search", params={"q": "   "})
    assert response.status_code == 400
    assert response.json()["hint"]


def test_deep_paging_is_refused_rather_than_ranked_against_a_partial_set(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/v1/search", params={"q": "agni", "limit": 50, "offset": SEARCH_WINDOW_LIMIT}
    )
    assert response.status_code == 400
    assert str(SEARCH_WINDOW_LIMIT) in response.json()["detail"]


def test_unknown_result_type_is_400_listing_the_alternatives(client: TestClient) -> None:
    response = client.get("/api/v1/search", params={"q": "agni", "type": "sonnet"})
    assert response.status_code == 400
    hint = response.json()["hint"]
    assert "devata" in hint and "passage" in hint


def test_unknown_veda_and_work_are_400_not_empty_results(client: TestClient) -> None:
    for params in ({"veda": "ZZ"}, {"work": "VG:WORK:ZZ:ZZZ"}):
        response = client.get("/api/v1/search", params={"q": "agni", **params})
        assert response.status_code == 400, params
        assert response.json()["hint"]


def test_limit_above_the_maximum_is_422(client: TestClient) -> None:
    assert client.get("/api/v1/search", params={"q": "a", "limit": 500}).status_code == 422


def test_graph_outage_is_503_naming_no_host(down_client: TestClient) -> None:
    response = down_client.get("/api/v1/search", params={"q": "agni"})
    assert response.status_code == 503
    assert_no_internals(response.text)


def test_an_empty_result_set_declares_what_it_read(client: TestClient) -> None:
    body = client.get("/api/v1/search", params={"q": "agni"}).json()
    assert body["items"] == []
    assert body["data_status"] == "PARTIAL"
    assert body["caveats"], "an empty search must say which surfaces it read"
    assert body["surfaces_searched"]
    assert any("not textual absence" in caveat["text"] for caveat in body["caveats"])
    assert body["score_semantics"].startswith("score is a RANK ORDERING")


# ---------------------------------------------------------------------------
# Live: coverage
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
def test_declared_surface_coverage_matches_the_graph(live_repository: Neo4jRepository) -> None:
    """The figures every search caveat quotes, re-derived from the live graph.

    Do not hand-edit the constant to make this pass. Re-measure, check the movement is one
    you intended, and then fix any caveat whose wording the new figures falsify.
    """
    measured = measure_surface_coverage(live_repository)
    assert measured == SURFACE_COVERAGE


@pytest.mark.neo4j
def test_the_samaveda_has_no_english_translation_and_the_response_says_so(
    live_repository: Neo4jRepository, live_client: TestClient
) -> None:
    row = live_repository.run_one(
        "MATCH (p:Passage {veda: 'SV'})-[:HAS_TRANSLATION]->(:Translation) RETURN count(p) AS n"
    )
    assert row is not None and int(row["n"]) == 0, (
        "a Samavedic translation has landed; the caveat must be re-measured"
    )
    body = live_client.get("/api/v1/search", params={"q": "thunderbolt"}).json()
    english = [
        view for view in body["surface_coverage"] if view["surface"] == "ENGLISH_TRANSLATION"
    ]
    assert english, "the English surface was read but not declared"
    assert "SV" in english[0]["vedas_not_covered"]
    assert any("NO SAMAVEDIC TRANSLATION" in c["text"] for c in body["caveats"])


@pytest.mark.neo4j
def test_the_normalized_and_lemma_surfaces_declare_their_single_corpus(
    live_client: TestClient,
) -> None:
    """A low-yield Sanskrit query, so every Sanskrit surface is actually read and declared."""
    body = live_client.get(
        "/api/v1/search", params={"q": "vasukra", "language": "sa", "limit": 25}
    ).json()
    views = {view["surface"]: view for view in body["surface_coverage"]}
    assert set(views) >= {"SANSKRIT_TEXT", "NORMALIZED_SANSKRIT", "LEMMA"}, (
        f"a Sanskrit surface went unread and undeclared: {sorted(views)}"
    )
    assert views["NORMALIZED_SANSKRIT"]["vedas_not_covered"] == ["RV", "YV", "SV"]
    assert views["LEMMA"]["vedas_not_covered"] == ["AV", "YV", "SV"]


# ---------------------------------------------------------------------------
# Live: the Sanskrit repertoire prefilter
# ---------------------------------------------------------------------------

#: Words whose Sanskrit scans must be skippable, and words whose must not. The second list
#: is the one that keeps the filter honest: if it ever grew a rejection, the optimisation
#: would be silently costing recall on real Vedic vocabulary.
_ENGLISH_WORDS = [
    "fever",
    "healing",
    "horse",
    "dawn",
    "chariot",
    "gold",
    "waters",
    "thunderbolt",
    "cow",
    "fire",
    "sacrifice",
    "priest",
    "wealth",
    "battle",
    "cattle",
]
_SANSKRIT_WORDS = ["indra", "soma", "agni", "somam", "vacas", "mitra", "rta", "takman", "namas"]


def test_the_declared_repertoire_is_well_formed() -> None:
    assert len(SANSKRIT_ASCII_BIGRAMS) == 308
    assert len(SANSKRIT_ASCII_TRIGRAMS) == 2419
    assert all(len(g) == 2 and g.isalpha() and g.islower() for g in SANSKRIT_ASCII_BIGRAMS)
    assert all(len(g) == 3 and g.isalpha() and g.islower() for g in SANSKRIT_ASCII_TRIGRAMS)
    for absent in "fqwxz":
        assert not any(absent in g for g in SANSKRIT_ASCII_BIGRAMS), (
            f"{absent!r} does not occur in Vedic IAST and must not be in the repertoire"
        )
        assert not any(absent in g for g in SANSKRIT_ASCII_TRIGRAMS)


def test_every_declared_trigram_is_built_from_declared_bigrams() -> None:
    """Internal consistency: a trigram whose halves are absent would be unreachable."""
    for gram in SANSKRIT_ASCII_TRIGRAMS:
        assert gram[:2] in SANSKRIT_ASCII_BIGRAMS, gram
        assert gram[1:] in SANSKRIT_ASCII_BIGRAMS, gram


@pytest.mark.parametrize("word", _SANSKRIT_WORDS)
def test_real_vedic_vocabulary_is_never_rejected(word: str) -> None:
    """The filter must cost no recall on the words the corpus actually contains."""
    assert sanskrit_cannot_contain(word) is None


@pytest.mark.parametrize("word", _ENGLISH_WORDS)
def test_ordinary_english_words_are_provably_absent_from_the_sanskrit(word: str) -> None:
    assert sanskrit_cannot_contain(word) is not None


def test_a_query_carrying_iast_diacritics_is_not_rejected_on_their_account() -> None:
    """Only ASCII runs are tested, so a diacritic can never be the reason for a skip."""
    for word in ("vāc", "uṣas", "agním", "kṛṣṇa", "ṛta"):
        assert sanskrit_cannot_contain(word) is None, word


@pytest.mark.neo4j
def test_the_declared_repertoire_matches_the_graph(live_repository: Neo4jRepository) -> None:
    """Re-derived from the live corpus. Do not hand-edit the constants to make this pass.

    A gram REMOVED from a declared set is the dangerous direction: it would make the filter
    reject a query the corpus can actually contain, which is silent recall loss.
    """
    row = live_repository.run_one(SANSKRIT_REPERTOIRE_QUERY)
    assert row is not None
    for size, declared in ((2, SANSKRIT_ASCII_BIGRAMS), (3, SANSKRIT_ASCII_TRIGRAMS)):
        measured = sanskrit_repertoire_from(row["tokens"], size)
        assert measured == declared, (
            f"{size}-grams declared but not measured: {sorted(declared - measured)}; "
            f"measured but not declared: {sorted(measured - declared)}"
        )


@pytest.mark.neo4j
@pytest.mark.parametrize("word", _ENGLISH_WORDS)
def test_the_repertoire_filter_never_skips_a_scan_that_would_have_matched(
    live_repository: Neo4jRepository, word: str
) -> None:
    """THE soundness test. Every rejection is checked against the scan it replaces.

    The filter's whole licence to skip a query rests on the rejection being a proof. So for
    every word it rejects, the three Sanskrit surfaces are actually scanned and asserted
    empty. A single non-empty result here means the optimisation is losing real answers.
    """
    assert sanskrit_cannot_contain(word) is not None, f"{word} is not rejected; nothing proved"
    for cypher in (
        "MATCH (tv:TextVersion) WHERE tv.text_role IN "
        "['PRIMARY_TEXT', 'PARALLEL_TEXT', 'SEARCH_DERIVATIVE'] "
        "AND toLower(tv.text_nfc) CONTAINS $q RETURN count(*) AS n",
        "MATCH (l:Lemma) WHERE toLower(l.normalized_lemma) CONTAINS $q RETURN count(*) AS n",
    ):
        row = live_repository.run_one(cypher, q=word.lower())
        assert row is not None and int(row["n"]) == 0, (
            f"the filter skipped the Sanskrit scan for {word!r}, but the corpus has "
            f"{row['n'] if row else '?'} matches for it"
        )


@pytest.mark.neo4j
def test_a_skipped_surface_is_named_with_its_reason(live_client: TestClient) -> None:
    body = live_client.get("/api/v1/search", params={"q": "fever", "limit": 25}).json()
    assert "SANSKRIT_TEXT" not in body["surfaces_searched"]
    assert "ENGLISH_TRANSLATION" in body["surfaces_searched"]
    assert body["pagination"]["total"] is None, "a skipped surface must null the total"
    skips = [c["text"] for c in body["caveats"] if "was NOT read" in c["text"]]
    assert skips, "a skipped surface must be named"
    assert any("letter pair 'fe'" in text for text in skips), skips
    assert any("proof" in text for text in skips)


@pytest.mark.neo4j
def test_a_real_sanskrit_query_still_reads_the_sanskrit(live_client: TestClient) -> None:
    """The other half: the filter must not have turned the Sanskrit surface off."""
    body = live_client.get("/api/v1/search", params={"q": "somam", "limit": 25}).json()
    assert "SANSKRIT_TEXT" in body["surfaces_searched"]
    assert any(i["match_type"] == "EXACT_SANSKRIT_PHRASE" for i in body["items"])


# ---------------------------------------------------------------------------
# Live: diacritic folding on the entity surfaces
# ---------------------------------------------------------------------------

#: The ASCII transliterations a frontend search box actually receives, with the
#: diacritic-bearing entity each one must reach. Before folding, every one of these
#: returned nothing from the entity surface: labels carry IAST and nothing folded them.
_FOLDED_RECALL: tuple[tuple[str, str], ...] = (
    ("yajna", "VG:CONCEPT:YAJNA-SACRIFICE"),
    ("yaksma", "VG:CONCEPT:YAKSMA-DISEASE"),
    ("hiranya", "VG:CONCEPT:HIRANYA-GOLD"),
    ("rta", "VG:CONCEPT:RTA-ORDER"),
    ("asvamedha", "VG:CONCEPT:ASVAMEDHA-HORSE-SACRIFICE"),
)


@pytest.mark.parametrize(
    ("raw", "folded"),
    [
        ("yajña", "yajna"),
        ("yakṣma", "yaksma"),
        ("varuṇa", "varuna"),
        ("hiraṇya", "hiranya"),
        ("Uṣas", "usas"),
        ("kṛṣṇa", "krsna"),
        ("aśvamedha", "asvamedha"),
        ("ṛta", "rta"),
        ("agním", "agnim"),
        ("sacrifice (yajña)", "sacrifice (yajna)"),
        ("plain ascii", "plain ascii"),
    ],
)
def test_the_fold_reduces_iast_to_its_ascii_skeleton(raw: str, folded: str) -> None:
    assert fold_diacritics(raw) == folded


def test_folding_is_idempotent() -> None:
    for word in ("yajña", "kṛṣṇa", "aśvamedha", "ṛta"):
        once = fold_diacritics(word)
        assert fold_diacritics(once) == once


@pytest.mark.neo4j
def test_the_python_and_cypher_folds_agree_on_every_entity_label(
    live_repository: Neo4jRepository,
) -> None:
    """Two folds that disagree would silently drop matches, so both are checked.

    Over EVERY label the entity surface reads, not a sample: the Cypher fold runs inside
    the scan and the Python fold produces the value it is compared against, and a
    disagreement on one character class would make a whole family of words unfindable
    while every test on a sample still passed.
    """
    rows = live_repository.run(
        """
        CALL () {
                MATCH (n:DomainEntity) RETURN n
            UNION MATCH (n:Devata) RETURN n
            UNION MATCH (n:Rishi) RETURN n
            UNION MATCH (n:RishiFamily) RETURN n
            UNION MATCH (n:Chandas) RETURN n
            UNION MATCH (n:Epithet) RETURN n
            UNION MATCH (n:ActionPredicate) RETURN n
            UNION MATCH (n:DeityAxis) RETURN n
            UNION MATCH (n:DeityGroup) RETURN n
        }
        UNWIND [n.display_label, n.preferred_label, n.label_iast, n.preferred_label_sa,
                n.normalized_name, n.predicate] AS raw
        WITH raw WHERE raw IS NOT NULL
        RETURN DISTINCT raw,
               reduce(s = normalize(toLower(raw), NFD), m IN $fold_marks |
                      replace(s, m, '')) AS cypher_folded
        """,
        fold_marks=list(DIACRITIC_MARKS),
    )
    assert len(rows) > 1500, f"only {len(rows)} labels checked; the sweep is not sweeping"
    disagreements = [
        (row["raw"], row["cypher_folded"], fold_diacritics(str(row["raw"])))
        for row in rows
        if fold_diacritics(str(row["raw"])) != row["cypher_folded"]
    ]
    assert not disagreements, (
        f"{len(disagreements)} labels fold differently in Python and Cypher; first three: "
        f"{disagreements[:3]}"
    )


@pytest.mark.neo4j
@pytest.mark.parametrize(("query", "expected_id"), _FOLDED_RECALL)
def test_an_ascii_transliteration_reaches_its_diacritic_bearing_entity(
    live_client: TestClient, query: str, expected_id: str
) -> None:
    body = live_client.get("/api/v1/search", params={"q": query, "limit": 25}).json()
    ids = [item["stable_id"] for item in body["items"]]
    assert expected_id in ids, f"{query!r} did not reach {expected_id}; got {ids[:5]}"
    matched = next(item for item in body["items"] if item["stable_id"] == expected_id)
    assert matched["match_type"] in {"FOLDED_ENTITY_LABEL", "EXACT_ENTITY_LABEL"}


@pytest.mark.neo4j
@pytest.mark.parametrize(("query", "expected_id"), _FOLDED_RECALL)
def test_the_diacritic_form_still_outranks_the_folded_one(
    live_repository: Neo4jRepository, live_client: TestClient, query: str, expected_id: str
) -> None:
    """Folding must add recall without costing precision: an exact hit still wins."""
    row = live_repository.run_one(
        "MATCH (n) WHERE coalesce(n.entity_key, n.concept_id) = $id "
        "RETURN coalesce(n.preferred_label_sa, n.label_iast, n.display_label) AS label",
        id=expected_id,
    )
    assert row is not None and row["label"]
    exact = live_client.get("/api/v1/search", params={"q": str(row["label"]), "limit": 25}).json()[
        "items"
    ]
    folded = live_client.get("/api/v1/search", params={"q": query, "limit": 25}).json()["items"]
    exact_score = next(i["score"] for i in exact if i["stable_id"] == expected_id)
    folded_score = next(i["score"] for i in folded if i["stable_id"] == expected_id)
    assert exact_score >= folded_score, (
        f"{expected_id}: the folded match scored {folded_score} against the exact "
        f"{exact_score}, so folding cost precision"
    )


def test_the_repertoire_prefilter_never_gates_the_entity_stage() -> None:
    """The load-bearing interaction between the two optimisations.

    The prefilter's grams are derived from the UNFOLDED text surfaces, so it is sound only
    against those. The entity stage folds diacritics on both sides, and gating it by that
    prefilter would reject ``yajna`` -- which contains the pair ``jn``, absent from the
    corpus because it spells the word ``yajña`` -- before the fold could match the entity.
    """
    assert sanskrit_cannot_contain("yajna") == "jn", "the premise of this test has moved"
    stages = SearchService(FakeRepository())._stages(SearchLanguage.ANY)
    entity_stages = [s for s in stages if SearchSurface.ENTITY_LABELS in s.surfaces]
    assert entity_stages, "no stage reads entity labels"
    for stage in entity_stages:
        assert not stage.reads_sanskrit, (
            f"stage {stage.name!r} reads entity labels AND is gated by the repertoire "
            "prefilter, which would make diacritic folding unsound"
        )


@pytest.mark.neo4j
def test_a_folded_query_whose_text_surfaces_are_skipped_still_finds_its_entity(
    live_client: TestClient,
) -> None:
    """The end-to-end statement of the interaction above."""
    body = live_client.get("/api/v1/search", params={"q": "yajna", "limit": 25}).json()
    assert "SANSKRIT_TEXT" not in body["surfaces_searched"], (
        "the premise has moved: the prefilter should skip the Sanskrit surfaces for 'yajna'"
    )
    assert any(item["stable_id"] == "VG:CONCEPT:YAJNA-SACRIFICE" for item in body["items"])
    text = " ".join(caveat["text"] for caveat in body["caveats"])
    assert "letter pair 'jn'" in text, "the skip must still be declared"


# ---------------------------------------------------------------------------
# The fold's coverage, derived from the graph rather than from the scheme
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
def test_the_declared_marks_cover_every_mark_in_the_graph(
    live_repository: Neo4jRepository,
) -> None:
    """THE guard this fold was missing, and the reason it shipped incomplete.

    The previous guard asserted that the Python and Cypher folds AGREED -- and they did,
    because both read the same table, which was written from knowledge of IAST and missed
    sixteen marks that actually occur. 635 labels folded incompletely and ``q=camtati``
    could not reach ``Çaṁtāti``. *An agreement test cannot see a coverage gap*, which is
    the same wrong-question failure as this project's two stale-claim audits.

    So this enumerates the value space instead of testing for the marks we expect. Both
    directions are asserted: a mark present but undeclared loses every label carrying it,
    and a mark declared but absent leaves the table implying a coverage it does not have.
    """
    row = live_repository.run_one(DIACRITIC_REPERTOIRE_QUERY)
    assert row is not None
    values = list(row["values"])
    assert len(values) > 10_000, f"only {len(values)} label values scanned; not a sweep"

    measured = marks_present_in(values)
    declared = frozenset(DIACRITIC_MARKS)

    undeclared = sorted(measured - declared)
    assert not undeclared, (
        "these combining marks occur in the graph's labels and are not folded, so every "
        "label carrying one folds incompletely and is unreachable by a folded query: "
        + ", ".join(f"U+{ord(mark):04X} {unicodedata.name(mark, '?')}" for mark in undeclared)
    )
    absent = sorted(declared - measured)
    assert not absent, (
        "these marks are declared but no longer occur; re-measure and remove them rather "
        "than leaving the table implying a coverage it does not have: "
        + ", ".join(f"U+{ord(mark):04X} {unicodedata.name(mark, '?')}" for mark in absent)
    )


def test_every_declared_mark_is_really_a_combining_mark() -> None:
    """Folding away something that is not a mark would delete a letter, silently."""
    for mark in DIACRITIC_MARKS:
        assert len(mark) == 1
        assert unicodedata.category(mark) in {"Mn", "Mc", "Me"}, (
            f"U+{ord(mark):04X} is not a combining mark; folding it would remove a letter"
        )


def test_folding_never_shortens_a_label_to_nothing_that_had_letters() -> None:
    """The fold must remove marks and only marks: a label of letters keeps its letters."""
    for label in ("yajña", "Çaṁtāti", "kṛṣṇa", "aśvamedha", "r̥ta"):
        folded = fold_diacritics(label)
        assert folded
        assert all(unicodedata.category(c) not in {"Mn", "Mc", "Me"} for c in folded)
        assert len(folded) <= len(unicodedata.normalize("NFD", label))


@pytest.mark.neo4j
def test_the_reported_miss_is_reachable(live_client: TestClient) -> None:
    """``q=camtati`` returned nothing while ``Çaṁtāti`` sat in the graph."""
    body = live_client.get("/api/v1/search", params={"q": "camtati", "limit": 25}).json()
    labels = [item["display_label"] for item in body["items"]]
    assert labels, "camtati still reaches nothing"
    assert any("aṁtāti" in label or "amtāti" in label for label in labels), labels
    assert body["items"][0]["match_type"] == "FOLDED_ENTITY_LABEL"


# ---------------------------------------------------------------------------
# A query with nothing left after folding
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mark", DIACRITIC_MARKS)
def test_a_query_of_bare_combining_marks_is_refused(client: TestClient, mark: str) -> None:
    """``str.strip()`` does not remove combining marks, so emptiness is tested AFTER folding.

    Before: a single U+0304 folded to ``""``, survived the whitespace guard, and then
    matched every entity in the graph through ``x STARTS WITH ''`` -- returning arbitrary
    deities at score 0.8 and costing 668ms to do it.
    """
    response = client.get("/api/v1/search", params={"q": mark})
    assert response.status_code == 400, f"U+{ord(mark):04X} returned {response.status_code}"
    body = response.json()
    assert "combining mark" in body["detail"]
    assert body["hint"]


@pytest.mark.parametrize(
    "query", ["\u0304", "\u0304\u0323", "  \u0304  ", "\u0304" * 40, "\u0327\u0325"]
)
def test_nothing_that_folds_to_nothing_reaches_a_query(
    client: TestClient, fake_repository: FakeRepository, query: str
) -> None:
    """And it is refused before any query runs, so the universal match cannot happen."""
    # .strip() first, exactly as the service does: whitespace is removed before folding,
    # and it is the FOLD that can empty what strip() left behind.
    assert fold_diacritics(query.strip()) == ""
    assert client.get("/api/v1/search", params={"q": query}).status_code == 400
    assert not fake_repository.calls, "a query that folds to nothing still hit the driver"


def test_a_mark_attached_to_letters_is_still_a_real_query(client: TestClient) -> None:
    """The refusal must be narrow: only a query with NOTHING left after folding."""
    for query in ("\u0304indra", "indr\u0304a", "agn\u0323i"):
        assert fold_diacritics(query) != ""
        assert client.get("/api/v1/search", params={"q": query}).status_code == 200


@pytest.mark.neo4j
def test_an_accent_bearing_query_still_reaches_its_entity(live_client: TestClient) -> None:
    body = live_client.get("/api/v1/search", params={"q": "\u0304indra", "limit": 5}).json()
    assert any(item["stable_id"] == "VG:DEVATA:INDRAH" for item in body["items"])


# ---------------------------------------------------------------------------
# Live: the ladder
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
def test_scores_never_rise_as_you_read_down_a_page(live_client: TestClient) -> None:
    for query in ("Indra", "agni", "soma", "fever", "hotar", "thunderbolt"):
        items = live_client.get("/api/v1/search", params={"q": query, "limit": 50}).json()["items"]
        scores = [item["score"] for item in items]
        assert scores == sorted(scores, reverse=True), f"{query} came back out of rank order"
        for item in items:
            assert item["score"] == MATCH_TYPE_SCORES[MatchType(item["match_type"])]


@pytest.mark.neo4j
def test_an_exact_entity_label_outranks_a_formula_prefix(live_client: TestClient) -> None:
    """The regression for the alphabetical-ordering defect found during this build."""
    items = live_client.get("/api/v1/search", params={"q": "Indra", "limit": 25}).json()["items"]
    assert items, "the flagship query returned nothing"
    assert items[0]["stable_id"] == "VG:DEVATA:INDRAH", (
        f"Indra himself must head a search for Indra, not {items[0]['stable_id']}"
    )
    assert items[0]["match_type"] == "EXACT_ENTITY_LABEL"
    assert items[0]["type"] == "DEVATA"


@pytest.mark.neo4j
def test_a_canonical_key_and_a_citation_reach_their_rungs(live_client: TestClient) -> None:
    by_key = live_client.get("/api/v1/search", params={"q": "VG:DEVATA:INDRAH"}).json()["items"]
    assert by_key[0]["match_type"] == "EXACT_CANONICAL_KEY"
    assert by_key[0]["score"] == 1.0

    by_citation = live_client.get("/api/v1/search", params={"q": "RV 1.1.1"}).json()["items"]
    assert by_citation[0]["match_type"] == "EXACT_CITATION"
    assert by_citation[0]["type"] == "PASSAGE"
    assert by_citation[0]["stable_id"] == "VG:RV:SAK:M01:S001:V001"
    assert by_citation[0]["veda"] == "RV"


@pytest.mark.neo4j
def test_a_sanskrit_phrase_returns_passages_with_a_snippet(live_client: TestClient) -> None:
    items = live_client.get(
        "/api/v1/search", params={"q": "vacas", "language": "sa", "limit": 25}
    ).json()["items"]
    passages = [item for item in items if item["type"] == "PASSAGE"]
    assert passages, "a Sanskrit phrase search returned no passage"
    assert all(item["snippet"] for item in passages)
    assert {item["match_type"] for item in passages} <= {
        "EXACT_SANSKRIT_PHRASE",
        "NORMALIZED_SANSKRIT_PHRASE",
        "LEMMA_FORM",
        "EXACT_CITATION",
        "EXACT_CANONICAL_KEY",
    }


@pytest.mark.neo4j
def test_an_english_phrase_returns_translation_matches(live_client: TestClient) -> None:
    body = live_client.get(
        "/api/v1/search", params={"q": "slayer of Vrtra", "language": "en", "limit": 25}
    ).json()
    passages = [item for item in body["items"] if item["match_type"] == "TRANSLATION_PHRASE"]
    assert passages, "an English phrase search returned no translated passage"
    assert all(item["snippet"] for item in passages)
    assert all(item["veda"] in {"RV", "AV", "YV"} for item in passages)


@pytest.mark.neo4j
def test_a_language_filter_says_which_rungs_it_silenced(live_client: TestClient) -> None:
    body = live_client.get("/api/v1/search", params={"q": "thunderbolt", "language": "sa"}).json()
    assert "ENGLISH_TRANSLATION" not in body["surfaces_searched"]
    assert any("language=sa" in caveat["text"] for caveat in body["caveats"])
    assert any("not a finding" in caveat["text"] for caveat in body["caveats"])


@pytest.mark.neo4j
def test_a_type_filter_returns_only_that_type(live_client: TestClient) -> None:
    for requested, expected in (("devata", "DEVATA"), ("condition", "CONDITION")):
        items = live_client.get(
            "/api/v1/search", params={"q": "a", "type": requested, "limit": 25}
        ).json()["items"]
        assert items, f"type={requested} returned nothing at all"
        assert {item["type"] for item in items} == {expected}


@pytest.mark.neo4j
def test_a_veda_filter_scopes_passages_and_says_it_does_not_scope_entities(
    live_client: TestClient,
) -> None:
    body = live_client.get(
        "/api/v1/search", params={"q": "takman", "veda": "AV", "limit": 50}
    ).json()
    passages = [item for item in body["items"] if item["type"] == "PASSAGE"]
    assert all(item["veda"] == "AV" for item in passages)
    assert any("veda=AV filters PASSAGE rows only" in c["text"] for c in body["caveats"])


# ---------------------------------------------------------------------------
# Live: the deity population contract
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
def test_searching_a_human_patron_never_types_him_a_deity(live_client: TestClient) -> None:
    """Vasistha is in the Anukramani's devata slot. Search must not offer him as a god."""
    body = live_client.get("/api/v1/search", params={"q": "Vasistha", "limit": 50}).json()
    for item in body["items"]:
        assert not (item["type"] == "DEVATA"), f"Vasistha surfaced as a deity: {item['stable_id']}"
        assert item["display_label"] not in KNOWN_NON_DEITY_LABELS or item["type"] != "DEVATA"
    assert any("not gods" in caveat["text"] for caveat in body["caveats"]), (
        "the excluded ascription must be reported, or the absence is unexplained"
    )
    assert any("all_ascriptions" in caveat["text"] for caveat in body["caveats"])


@pytest.mark.neo4j
def test_no_devata_row_anywhere_in_search_is_a_non_deity(
    live_repository: Neo4jRepository, live_client: TestClient
) -> None:
    non_deities = {
        str(row["label"])
        for row in live_repository.run(
            "MATCH (dv:Devata) "
            "WHERE coalesce(dv.structure, 'UNSPECIFIED') IN "
            "['HUMAN', 'PATRON_PRAISE', 'UNSPECIFIED'] "
            "RETURN dv.display_label AS label"
        )
    }
    assert len(non_deities) == 30
    for query in ("Vasistha", "Atri", "praise", "the dog", "Visvamitra", "Brbu"):
        for item in live_client.get("/api/v1/search", params={"q": query, "limit": 50}).json()[
            "items"
        ]:
            if item["type"] == "DEVATA":
                assert item["display_label"] not in non_deities, query


@pytest.mark.neo4j
def test_a_lemma_is_matched_against_but_never_returned(live_client: TestClient) -> None:
    """All 10,031 ``:Lemma`` nodes are marked ``:Internal``; a lemma may not be a result."""
    body = live_client.get(
        "/api/v1/search", params={"q": "agni", "language": "sa", "limit": 50}
    ).json()
    for item in body["items"]:
        assert item["type"] != "LEMMA"
        assert not item["stable_id"].startswith("lemma_")
        if item["match_type"] == "LEMMA_FORM":
            assert item["type"] == "PASSAGE"


@pytest.mark.neo4j
def test_no_search_response_leaks_an_internal(live_client: TestClient) -> None:
    for query in ("Indra", "agni", "fever", "VG:DEVATA:INDRAH", "RV 1.1.1", METACHARACTERS):
        response = live_client.get("/api/v1/search", params={"q": query, "limit": 25})
        assert response.status_code == 200, query
        assert_no_internals(response.text)


@pytest.mark.neo4j
def test_metacharacters_and_cypher_are_harmless_against_the_real_graph(
    live_repository: Neo4jRepository, live_client: TestClient
) -> None:
    """The payloads must be inert AND must not have changed the graph."""
    before = live_repository.run_one("MATCH (n) RETURN count(n) AS n")
    assert before is not None
    for payload in INJECTIONS:
        response = live_client.get("/api/v1/search", params={"q": payload})
        assert response.status_code == 200, (payload, response.text[:200])
    after = live_repository.run_one("MATCH (n) RETURN count(n) AS n")
    assert after is not None and after["n"] == before["n"]


# ---------------------------------------------------------------------------
# Live: latency
# ---------------------------------------------------------------------------


#: How much faster a repertoire-rejected query must be than a full-ladder one.
#:
#: **Why this is relative and not a wall clock.** There were absolute ceilings here, and
#: they flaked -- not on a regression, but on contention this very file creates: its
#: all-214 deity sweep, its all-729 seer sweep and its 10,624-label fold sweep hammer the
#: same database, and ``varuna`` measured 278-336ms alone against 420ms alongside them.
#: Raising the bound would have been fitting the number to the noise, and threshold-chasing
#: a wall clock on a shared resource does not converge.
#:
#: A ratio does converge, because both halves are measured interleaved under whatever load
#: is present, and it guards the thing that actually matters: that the optimisation is in
#: effect. Absolute figures are reported to the coordinator rather than gated -- measured
#: isolated and warmed, the sixteen-query median is 107ms at ``limit=25`` and 156ms at
#: ``limit=200``, with a 355ms worst case on the shape no prefilter can reject.
PREFILTER_SPEEDUP = 1.6

#: A query the repertoire prefilter proves cannot match the Sanskrit surfaces, and one it
#: cannot reject. The first must skip three scans; the second must run all of them.
_REJECTED_QUERY = "fever"
_FULL_LADDER_QUERY = "varuna"


@pytest.mark.neo4j
def test_the_repertoire_prefilter_measurably_reduces_work(live_client: TestClient) -> None:
    """The optimisation is in effect, measured as a ratio so load cannot fake it.

    ``fever`` fails on the pair ``fe`` and skips the plain, normalised and lemma Sanskrit
    scans -- 144ms of the 203ms of text scanning. ``varuna`` is legal Sanskrit shape whose
    ASCII form the corpus does not contain (it spells the word ``varuṇa``), so nothing can
    be proven about it in advance and every surface must be read. If the two ever cost the
    same, the prefilter has stopped working, whatever the absolute numbers say.
    """
    params_rejected: dict[str, Any] = {"q": _REJECTED_QUERY, "limit": 25}
    params_full: dict[str, Any] = {"q": _FULL_LADDER_QUERY, "limit": 25}
    live_client.get("/api/v1/search", params=params_rejected)
    live_client.get("/api/v1/search", params=params_full)

    # Interleaved, so a load spike lands on both rather than on one.
    rejected: list[float] = []
    full: list[float] = []
    for _ in range(5):
        rejected.append(_elapsed_ms(live_client, "/api/v1/search", params_rejected))
        full.append(_elapsed_ms(live_client, "/api/v1/search", params_full))

    best_rejected = min(rejected)
    best_full = min(full)
    assert best_full / best_rejected >= PREFILTER_SPEEDUP, (
        f"the prefilter is not reducing work: {_REJECTED_QUERY!r} took "
        f"{best_rejected:.0f}ms and {_FULL_LADDER_QUERY!r} {best_full:.0f}ms, a ratio of "
        f"{best_full / best_rejected:.2f} against {PREFILTER_SPEEDUP}"
    )

    # And the reason must be the one claimed, not an accident of caching.
    body = live_client.get("/api/v1/search", params=params_rejected).json()
    assert "SANSKRIT_TEXT" not in body["surfaces_searched"]
    assert any("letter pair 'fe'" in c["text"] for c in body["caveats"])
    full_body = live_client.get("/api/v1/search", params=params_full).json()
    assert "SANSKRIT_TEXT" in full_body["surfaces_searched"]


@pytest.mark.neo4j
def test_an_identifier_query_costs_less_than_a_phrase_query(live_client: TestClient) -> None:
    """The other skip, measured the same relative way.

    An exact canonical key means the caller named one object, so the text surfaces are not
    read at all. It must therefore be cheaper than a phrase over the same page size.
    """
    identifier: dict[str, Any] = {"q": "VG:DEVATA:INDRAH", "limit": 25}
    phrase: dict[str, Any] = {"q": _FULL_LADDER_QUERY, "limit": 25}
    live_client.get("/api/v1/search", params=identifier)
    live_client.get("/api/v1/search", params=phrase)
    best_id = min(_elapsed_ms(live_client, "/api/v1/search", identifier) for _ in range(5))
    best_phrase = min(_elapsed_ms(live_client, "/api/v1/search", phrase) for _ in range(5))
    assert best_phrase / best_id >= PREFILTER_SPEEDUP, (
        f"an identifier lookup ({best_id:.0f}ms) is not measurably cheaper than a phrase "
        f"({best_phrase:.0f}ms)"
    )


def _elapsed_ms(client: TestClient, path: str, params: dict[str, Any]) -> float:
    started = time.perf_counter()
    response = client.get(path, params=params)
    assert response.status_code == 200
    return (time.perf_counter() - started) * 1000
