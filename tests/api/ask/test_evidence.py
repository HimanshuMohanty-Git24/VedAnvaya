"""The evidence packet: closed before any prompt exists, and qualified item by item.

Two properties are load-bearing and both are asserted here.

*Absence gets an item.* A term found nowhere must produce a positive statement -- "we
searched all four corpora and here is what each surface could have shown" -- because the
alternative is an empty packet, and an empty packet is what a model answers from memory.

*The qualifier travels with the content.* A translation is not the Sanskrit, an AMBIGUOUS
referent is not a deity occurrence, a graph path is not a claim of the tradition. Those
statements are rendered next to the item they bound rather than in a preamble the model may
not carry through to the sentence it writes.
"""

from __future__ import annotations

from typing import Any

from vedagraph.api.ask.evidence import build_evidence_packet
from vedagraph.api.ask.models import EvidenceItemType
from vedagraph.api.ask.retriever import LexicalPresence, RetrievalResult


def passage_row(key: str, **overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "canonical_key": key,
        "canonical_citation": key.replace("_", " "),
        "veda": "RV",
        "sanskrit": "agnim ile purohitam",
        "translation": "I laud Agni, the chosen Priest.",
        "relation_type": "MENTIONS_DEVATA",
        "certainty": "DEITY_CERTAIN",
    }
    row.update(overrides)
    return row


def lexical_rows() -> list[dict[str, Any]]:
    return [
        {
            "veda": "RV",
            "mantras": 10552,
            "with_sanskrit": 10552,
            "with_translation": 10552,
            "sanskrit_hits": 0,
            "translation_hits": 0,
        },
        {
            "veda": "SV",
            "mantras": 1875,
            "with_sanskrit": 1875,
            "with_translation": 0,
            "sanskrit_hits": 0,
            "translation_hits": 0,
        },
        {
            "veda": "YV",
            "mantras": 1975,
            "with_sanskrit": 0,
            "with_translation": 1975,
            "sanskrit_hits": 0,
            "translation_hits": 3,
        },
    ]


# ---------------------------------------------------------------------------
# The empty packet
# ---------------------------------------------------------------------------


def test_an_empty_result_gives_an_empty_packet_that_says_so() -> None:
    packet = build_evidence_packet(RetrievalResult())

    assert packet.items == []
    prompt = packet.as_prompt()
    assert "NO EVIDENCE RETRIEVED" in prompt
    assert "background knowledge" in prompt


def test_an_empty_packet_has_no_citable_ids() -> None:
    packet = build_evidence_packet(RetrievalResult())

    assert packet.citation_ids() == set()
    assert packet.by_id() == {}
    assert packet.has_interpretive_content() is False


# ---------------------------------------------------------------------------
# Ids and budget
# ---------------------------------------------------------------------------


def test_ids_are_contiguous_after_budgeting() -> None:
    """Renumbered after the cut, so the ids the model sees have no gaps -- a gap invites
    it to cite the id that is missing."""
    result = RetrievalResult(passages=[passage_row(f"RV_1.1.{n}") for n in range(1, 9)])

    packet = build_evidence_packet(result, budget=5)

    assert [item.id for item in packet.items] == ["E1", "E2", "E3", "E4", "E5"]


def test_the_budget_is_respected() -> None:
    result = RetrievalResult(passages=[passage_row(f"RV_1.1.{n}") for n in range(1, 51)])

    packet = build_evidence_packet(result, budget=5)

    assert len(packet.items) == 5


def test_duplicate_passage_keys_are_collapsed() -> None:
    """Two channels can return the same verse, and two identical items would spend the
    budget saying the same thing twice."""
    result = RetrievalResult(
        passages=[passage_row("RV_1.1.1"), passage_row("RV_1.1.1"), passage_row("RV_1.1.2")]
    )

    packet = build_evidence_packet(result)

    assert len(packet.items) == 2


def test_source_text_outranks_interpretation_under_the_budget() -> None:
    """Interpretation is last on purpose: it is the item type most likely to be restated
    as fact, so it earns its place only when there is room."""
    result = RetrievalResult(
        passages=[passage_row("RV_1.1.1")],
        interpretive_claims=[
            {
                "claim_text": "Agni is the axis of the sacrifice.",
                "asserted_by": "Some scholar",
                "claim_type": "READING",
                "scope": "RV",
                "about": "VG:DEVATA:AGNI",
            }
        ],
    )

    packet = build_evidence_packet(result, budget=1)

    assert [item.type for item in packet.items] == [EvidenceItemType.PASSAGE]


# ---------------------------------------------------------------------------
# Lexical presence: the item that makes absence sayable
# ---------------------------------------------------------------------------


def test_a_lexical_row_becomes_an_item_whose_qualifier_refuses_the_zero() -> None:
    result = RetrievalResult(lexical=LexicalPresence(term="ayas", rows=lexical_rows()))

    packet = build_evidence_packet(result)

    lexical = [i for i in packet.items if i.type is EvidenceItemType.LEXICAL_PRESENCE]
    assert len(lexical) == 1
    qualifier = lexical[0].qualifier or ""
    assert "NOT textual absence" in qualifier
    assert lexical[0].entity_label == "ayas"
    # The measured surface per corpus, so a miss can be attributed rather than asserted.
    assert "0 Sanskrit-surface" in (lexical[0].fact or "")
    assert "Yajurveda" in qualifier


def test_a_corpus_with_no_searchable_surface_is_named_on_the_packet() -> None:
    """Carried on the packet rather than inside an item, because it constrains the whole
    answer and not one citation."""
    rows = lexical_rows()
    rows.append(
        {
            "veda": "AV",
            "mantras": 100,
            "with_sanskrit": 0,
            "with_translation": 0,
            "sanskrit_hits": 0,
            "translation_hits": 0,
        }
    )
    result = RetrievalResult(lexical=LexicalPresence(term="ayas", rows=rows))

    packet = build_evidence_packet(result)

    assert packet.unsearchable_vedas == ["AV"]
    assert "AV" in (packet.items[0].qualifier or "")


# ---------------------------------------------------------------------------
# Qualifiers travel with the item
# ---------------------------------------------------------------------------


def test_a_translation_only_passage_says_it_is_not_the_sanskrit() -> None:
    result = RetrievalResult(passages=[passage_row("RV_1.1.1", sanskrit=None)])

    packet = build_evidence_packet(result)

    qualifier = packet.items[0].qualifier or ""
    assert "not the" in qualifier
    assert "Sanskrit" in qualifier
    assert "19th-century" in qualifier


def test_an_ambiguous_referent_is_not_a_deity_occurrence() -> None:
    result = RetrievalResult(passages=[passage_row("RV_1.1.1", certainty="DEITY_AMBIGUOUS")])

    packet = build_evidence_packet(result)

    qualifier = packet.items[0].qualifier or ""
    assert "AMBIGUOUS" in qualifier
    assert "not count this as a deity occurrence" in qualifier


def test_a_translation_match_says_the_match_is_in_the_translators_wording() -> None:
    result = RetrievalResult(
        passages=[passage_row("RV_1.1.1", relation_type="TRANSLATION_MATCH", certainty=None)]
    )

    packet = build_evidence_packet(result)

    assert "translator's wording" in (packet.items[0].qualifier or "")


def test_an_ascription_is_rendered_as_dedication_and_not_mention() -> None:
    result = RetrievalResult(
        ascription_passages=[
            {
                "canonical_key": "RV_1.1.1",
                "canonical_citation": "RV 1.1.1",
                "veda": "RV",
                "translation": "I laud Agni.",
                "_entity_label": "Agni",
                "relation_type": "HAS_DEVATA",
                "attribution_precision": "CONTAINER_INHERITED",
            }
        ]
    )

    packet = build_evidence_packet(result)

    item = packet.items[0]
    assert item.type is EvidenceItemType.ATTRIBUTION
    assert "dedication and not" in (item.fact or "")
    assert "Not a per-verse statement" in (item.qualifier or "")


def test_corpus_distribution_reports_the_excluded_ambiguous_count() -> None:
    result = RetrievalResult(
        entity_by_veda=[
            {
                "_entity_key": "VG:DEVATA:AGNI",
                "_entity_label": "Agni",
                "veda": "RV",
                "relation_type": "MENTIONS_DEVATA",
                "certain": 831,
                "probable": 12,
                "ambiguous": 400,
                "ungraded": 0,
            }
        ]
    )

    packet = build_evidence_packet(result)

    item = packet.items[0]
    assert item.type is EvidenceItemType.CORPUS_DISTRIBUTION
    assert "400 ambiguous excluded" in (item.fact or "")
    assert "400 AMBIGUOUS occurrences are excluded" in (item.qualifier or "")
    assert "not the same as the text being silent" in (item.qualifier or "")


def test_a_hub_route_says_it_explains_little() -> None:
    result = RetrievalResult(
        graph_paths=[
            {
                "node_labels": ["Agni", "RV 1.1.1", "Soma"],
                "rel_types": ["MENTIONS_DEVATA", "MENTIONS_DEVATA"],
                "max_degree": 3566,
            }
        ]
    )

    packet = build_evidence_packet(result)

    qualifier = packet.items[0].qualifier or ""
    assert "only that these edges exist" in qualifier
    assert "high-degree node" in qualifier
    assert "Path: Agni -[MENTIONS_DEVATA]- RV 1.1.1" in (packet.items[0].fact or "")


def test_a_token_resolved_entity_says_which_word_matched() -> None:
    result = RetrievalResult(
        entity_profiles=[
            {
                "entity_key": "VG:CONDITION:TAKMAN",
                "label": "fever (takman)",
                "entity_type": "Condition",
                "description": "A febrile affliction.",
                "_match_rank": "TOKEN_IN_LABEL",
                "_asked_as": "takman",
            }
        ]
    )

    packet = build_evidence_packet(result)

    assert "not the whole label" in (packet.items[0].qualifier or "")


# ---------------------------------------------------------------------------
# Interpretation
# ---------------------------------------------------------------------------


def test_has_interpretive_content_is_true_only_with_an_interpretive_item() -> None:
    without = build_evidence_packet(RetrievalResult(passages=[passage_row("RV_1.1.1")]))
    with_claim = build_evidence_packet(
        RetrievalResult(
            interpretive_claims=[
                {
                    "claim_text": "Agni is the axis of the sacrifice.",
                    "asserted_by": "Some scholar",
                    "claim_type": "READING",
                    "scope": "RV",
                    "about": "VG:DEVATA:AGNI",
                    "falsifier": "A hymn dedicating the sacrifice to another deity.",
                }
            ]
        )
    )

    assert without.has_interpretive_content() is False
    assert with_claim.has_interpretive_content() is True
    qualifier = with_claim.items[0].qualifier or ""
    assert "ONE INTERPRETATION" in qualifier
    assert "falsified by" in qualifier


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def test_the_qualifier_is_the_last_line_of_a_rendered_item() -> None:
    """Nearest line to whatever the model writes next."""
    result = RetrievalResult(passages=[passage_row("RV_1.1.1", sanskrit=None)])

    rendered = build_evidence_packet(result).as_prompt()

    assert rendered.startswith("[E1] PASSAGE")
    assert rendered.strip().splitlines()[-1].strip().startswith("QUALIFIER:")


def test_long_quoted_text_is_bounded_in_the_prompt() -> None:
    result = RetrievalResult(passages=[passage_row("RV_1.1.1", translation="word " * 400)])

    rendered = build_evidence_packet(result).as_prompt()

    assert len(rendered) < 1200
