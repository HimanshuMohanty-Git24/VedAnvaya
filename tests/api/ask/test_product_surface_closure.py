"""GAP-PRODUCT_SURFACE-004: the citations Ask could not read and the insight it never ran.

Two measured defects, both of which let Ask refuse or mislead on a question the rest of
the API answers directly.

**A citation typed the way a reader types it never became a passage lookup.** The planner's
pattern admitted only the corpus *abbreviations*, so "What does Samaveda Aranyaka 1.1
say?" planned no passage channel at all and retrieved zero evidence items -- for a verse
stored at ``VG:SV:KAU:ARANYA:D01:V01``. The same hole swallowed "Rigveda 1.1.1",
"Yajurveda 1.1" and "Atharvaveda 2.3.4". It is worst for the Samaveda because no one
writes a Samavedic citation in prose without spelling the corpus out, which is why the
benchmark's Q34 was graded MISLEADING.

Worse than not matching: for two corpora the pattern matched and produced a key that
*cannot exist*. The graph cites the Atharvaveda ``AVS 1.1.1`` and the Yajurveda
``VSM 1.1``, so a planned key of "AV 2.3.4" or "YV 1.1" ran a lookup guaranteed to return
nothing -- an empty packet, which is exactly the shape a model answers from memory. The
reader endpoint's own normaliser has always mapped both; Ask simply never called it.

**A materials question reached no channel that knows about materials.** "Which metals
appear in the Vedas?" resolved neither "metals" nor "corpus", so the only channel that ran
was a lexical scan for the English string *metals* -- while ``/api/v1/insights/metals``
answers the same question from a frozen, graded query. These tests bind Ask to that same
named query rather than to a retyped copy of it.
"""

from __future__ import annotations

import pytest

from vedagraph.api.ask import evidence as evidence_stage
from vedagraph.api.ask import resolver as resolver_stage
from vedagraph.api.ask import retriever as retriever_stage
from vedagraph.api.ask.models import EvidenceItemType, QueryIntent
from vedagraph.api.ask.planner import plan
from vedagraph.api.repositories.neo4j_repository import Neo4jRepository

# ---------------------------------------------------------------------------
# Planning: a citation a reader would actually type
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        # The Samaveda, spelled out. This is Q34's question in the words a reader uses.
        ("What does Samaveda Aranyaka 1.1 say?", "SV ARANYA 1.1"),
        ("Samaveda ARANYA 1.1", "SV ARANYA 1.1"),
        ("What does the Samaveda Uttararcika 9.2.10.1 contain?", "SV UTTARA 9.2.10.1"),
        # The other three corpora, spelled out.
        ("What does Rigveda 1.1.1 say?", "RV 1.1.1"),
        ("What does Yajurveda 1.1 say?", "VSM 1.1"),
        ("What does Atharvaveda 2.3.4 say?", "AVS 2.3.4"),
    ],
)
def test_a_spelled_out_corpus_name_still_forms_a_passage_key(question: str, expected: str) -> None:
    result = plan(question)

    assert result.passage_key == expected
    assert QueryIntent.PASSAGE_LOOKUP in result.intents
    assert "passages" in result.retrieval_channels


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        # The reader's Veda code is not the prefix the graph stores.
        ("What does AV 2.3.4 say?", "AVS 2.3.4"),
        ("What does YV 1.1 say?", "VSM 1.1"),
        ("What does VS 1.1 say?", "VSM 1.1"),
        # ... and the ones that already agreed must keep agreeing.
        ("What does RV 1.1.1 say?", "RV 1.1.1"),
        ("What does AVS 1.1.1 say?", "AVS 1.1.1"),
        ("What does VSM 1.1 say?", "VSM 1.1"),
        ("What does SV ARANYA 1.1 contain?", "SV ARANYA 1.1"),
        ("What does sv_aranya_1.1 contain?", "SV ARANYA 1.1"),
        ("What does SV MAHANAMNYA 1 say?", "SV MAHANAMNYA 1"),
    ],
)
def test_the_planned_key_is_the_prefix_the_graph_actually_stores(
    question: str, expected: str
) -> None:
    """A key of "AV 2.3.4" is not a near miss -- it matches nothing, ever."""
    assert plan(question).passage_key == expected


def test_a_bare_book_number_is_still_not_a_locus() -> None:
    """Widening the corpus names must not turn "the Rigveda has 10 mandalas" into a verse."""
    assert plan("How many hymns does Rigveda 10 have?").passage_key is None
    assert plan("Tell me about the Atharvaveda").passage_key is None


# ---------------------------------------------------------------------------
# Planning: a materials question
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "question",
    [
        "Which metals appear in the Vedas?",
        "What metals are mentioned in the Rigveda?",
        "Which materials and metals does the corpus attest?",
        "Is copper attested in the Vedas?",
        "Which crops occur in each Veda?",
    ],
)
def test_a_materials_question_routes_to_the_materials_channel(question: str) -> None:
    result = plan(question)

    assert "materials" in result.retrieval_channels
    assert QueryIntent.MATERIAL_CULTURE in result.intents
    assert result.material_topics


def test_the_materials_topic_is_the_one_the_question_named() -> None:
    assert plan("Which metals appear in the Vedas?").material_topics == ["metals"]
    assert plan("Which crops occur in each Veda?").material_topics == ["crops"]
    assert plan("Which animals are named in the Atharvaveda?").material_topics == ["animals"]


def test_an_ordinary_question_does_not_run_the_materials_channel() -> None:
    result = plan("How does Indra appear across the four Vedas?")

    assert "materials" not in result.retrieval_channels
    assert result.material_topics == []


# ---------------------------------------------------------------------------
# Retrieval: the materials channel runs the frozen insight query, not a new one
# ---------------------------------------------------------------------------


def test_the_materials_channel_runs_the_frozen_named_query(fake_repository) -> None:  # type: ignore[no-untyped-def]
    """Bound to ``metals_by_veda`` by name, so Ask and /insights/metals cannot fork."""
    from vedagraph.domain.queries import QUERIES_BY_NAME

    query_plan = plan("Which metals appear in the Vedas?")
    retriever_stage.retrieve(query_plan, [], fake_repository)

    assert QUERIES_BY_NAME["metals_by_veda"].cypher in fake_repository.query_text


def test_materials_rows_become_evidence_carrying_the_frozen_caveat(fake_repository) -> None:  # type: ignore[no-untyped-def]
    """The caveat is read from the query, never retyped: a copied caveat drifts."""
    from vedagraph.api.repositories.neo4j_repository import named_query_caveat
    from vedagraph.domain.queries import QUERIES_BY_NAME

    fake_repository.script = {
        QUERIES_BY_NAME["metals_by_veda"].cypher: [
            {
                "metal": "gold",
                "veda": "RV",
                "mantras": 38,
                "per_1000_mantras": 3.601,
                "corpus_mantras": 10552,
                "evidence_status": "LEXICAL_MATCH_MINIMUM",
            },
            {
                "metal": "gold",
                "veda": "AV",
                "mantras": 34,
                "per_1000_mantras": 5.823,
                "corpus_mantras": 5839,
                "evidence_status": "LEXICAL_MATCH_MINIMUM",
            },
        ]
    }

    query_plan = plan("Which metals appear in the Vedas?")
    retrieval = retriever_stage.retrieve(query_plan, [], fake_repository)
    packet = evidence_stage.build_evidence_packet(retrieval)

    material_items = [
        item for item in packet.items if item.type is EvidenceItemType.CORPUS_DISTRIBUTION
    ]
    assert material_items, "the materials channel produced no evidence item"
    item = material_items[0]
    assert item.entity_label == "gold"
    assert item.fact is not None
    assert "38" in item.fact and "RV" in item.fact
    assert item.qualifier == named_query_caveat("metals_by_veda")


def test_a_matched_but_empty_materials_grid_is_reported_not_dropped(fake_repository) -> None:  # type: ignore[no-untyped-def]
    """ "We looked and found nothing" is a different answer from "we never looked"."""
    query_plan = plan("Which metals appear in the Vedas?")
    retrieval = retriever_stage.retrieve(query_plan, [], fake_repository)

    assert "materials" in retrieval.channels_empty


# ---------------------------------------------------------------------------
# Live: against the frozen graph
# ---------------------------------------------------------------------------


@pytest.mark.neo4j
@pytest.mark.parametrize(
    ("question", "citation"),
    [
        ("What does SV ARANYA 1.1 contain?", "SV ARANYA 1.1"),
        ("What does Samaveda Aranyaka 1.1 say?", "SV ARANYA 1.1"),
        ("Samaveda ARANYA 1.1", "SV ARANYA 1.1"),
        ("What does SV UTTARA 1.1 say?", "SV UTTARA 1.1"),
        ("What does SV MAHANAMNYA 1 say?", "SV MAHANAMNYA 1"),
        ("What does Rigveda 1.1.1 say?", "RV 1.1.1"),
        ("What does Yajurveda 1.1 say?", "VSM 1.1"),
        ("What does Atharvaveda 1.1.1 say?", "AVS 1.1.1"),
        ("What does AV 1.1.1 say?", "AVS 1.1.1"),
    ],
)
def test_live_a_direct_citation_retrieves_its_passage_in_all_four_corpora(
    live_repository: Neo4jRepository, question: str, citation: str
) -> None:
    query_plan = plan(question)
    resolved = resolver_stage.resolve_entities(query_plan.entities_mentioned, live_repository)
    retrieval = retriever_stage.retrieve(query_plan, resolved, live_repository)
    packet = evidence_stage.build_evidence_packet(retrieval)

    assert "passage_by_key" in retrieval.channels_used, f"{question!r} never ran a passage lookup"
    citations = [item.citation for item in packet.items if item.type is EvidenceItemType.PASSAGE]
    assert citation in citations, f"{question!r} did not retrieve {citation}: got {citations}"


@pytest.mark.neo4j
def test_live_a_bare_samavedic_locus_is_disambiguated_rather_than_left_empty(
    live_repository: Neo4jRepository,
) -> None:
    """No Samavedic verse is cited without its arcika section.

    "SV 1.1" therefore matches no ``canonical_citation`` at all. Left there, the packet is
    empty -- and an empty packet is the exact input that produced Q34's denial of a verse
    the graph stores. The sections are tried by name so the answer can show the reader
    which loci that citation could have meant.
    """
    query_plan = plan("What does SV 1.1 say?")
    retrieval = retriever_stage.retrieve(query_plan, [], live_repository)
    packet = evidence_stage.build_evidence_packet(retrieval)

    citations = {item.citation for item in packet.items if item.type is EvidenceItemType.PASSAGE}
    assert citations, "a bare SV locus returned an empty packet"
    assert any(str(c).startswith("SV ") for c in citations)


@pytest.mark.neo4j
def test_live_a_metals_question_reaches_the_metals_insight_evidence(
    live_repository: Neo4jRepository,
) -> None:
    """The measured BEFORE state: one LEXICAL_PRESENCE item for the English word "metals"."""
    query_plan = plan("Which metals appear in the Vedas?")
    resolved = resolver_stage.resolve_entities(query_plan.entities_mentioned, live_repository)
    retrieval = retriever_stage.retrieve(query_plan, resolved, live_repository)
    packet = evidence_stage.build_evidence_packet(retrieval)

    assert "materials" in retrieval.channels_used
    items = [item for item in packet.items if item.type is EvidenceItemType.CORPUS_DISTRIBUTION]
    labels = {item.entity_label for item in items}
    assert "gold (hiraṇya)" in labels, f"no metal reached the packet: {labels}"
    assert "metal (ayas)" in labels
    assert len(packet.items) > 1

    # The known-false cell travels with the evidence, read from the frozen query rather
    # than retyped: the Yajurveda names ayas at VSM 18.13 and the grid reads
    # NO_LEXICAL_MATCH there.
    ayas = next(item for item in items if item.entity_label == "metal (ayas)")
    assert ayas.qualifier is not None
    assert "VSM 18.13" in ayas.qualifier
    assert ayas.fact is not None and "No lexical match in" in ayas.fact


@pytest.mark.neo4j
def test_live_the_samavedic_gana_corpus_is_never_called_a_section_this_graph_holds(
    live_repository: Neo4jRepository,
) -> None:
    """Q45's defect in its data form: ARANYA is an arcika section, not a gana.

    The scope copy the model is given must name both senses, because the only thing that
    stops "Aranyaka-gana section" being written about ``SV ARANYA 1.1`` is being told what
    ARANYA is. This asserts the copy, and that the graph really does hold the section.
    """
    from vedagraph.api.ask.synthesizer import SYSTEM_PROMPT

    # Both senses named, in both directions: the gana corpus is absent, AND the section
    # cited SV ARANYA is arcika verse text that is present.
    assert "the gana corpus is absent" in SYSTEM_PROMPT
    assert "structural section of the modelled arcika, not the forest-treatise genre" in (
        SYSTEM_PROMPT
    )
    assert "must never be refused as an Aranyaka" in " ".join(SYSTEM_PROMPT.split())
    # The only place "gana" may appear is the sentence declaring it absent. Any other
    # occurrence would be the prompt describing a corpus this graph does not hold.
    assert SYSTEM_PROMPT.count("gana") == SYSTEM_PROMPT.count("the gana corpus is absent")

    rows = live_repository.run(
        "MATCH (p:Passage {veda:'SV', display_type:'MANTRA'}) "
        "WHERE p.canonical_citation STARTS WITH 'SV ARANYA' RETURN count(p) AS n"
    )
    assert rows[0]["n"] > 0
