"""The planner: deterministic classification, and the Ap bug it must not reintroduce.

Planning runs before any provider exists, which is what makes the Ask pipeline's evidence
reproducible: the same question selects the same channels on every run, so an answer that
changed can only have changed at synthesis. These tests assert that property directly
rather than trusting it.

The named defect is *Ap*. The deity of the waters is spelled ``ap``, which is a substring
of "appear", so a substring test nominates a deity for any question containing that word.
The resolver would then resolve it and the evidence packet would carry a subject the
question never mentioned -- plausible, silent and wrong.
"""

from __future__ import annotations

from vedagraph.api.ask.models import AskMode, QueryIntent
from vedagraph.api.ask.planner import plan


def test_planning_is_deterministic() -> None:
    """Compared field by field: ``planning_ms`` differs between two runs by design."""
    question = "How does Indra appear across the four Vedas?"

    first = plan(question)
    second = plan(question)

    assert first.intents == second.intents
    assert first.entities_mentioned == second.entities_mentioned
    assert first.retrieval_channels == second.retrieval_channels
    assert first.veda_scope == second.veda_scope
    assert first.lexical_terms == second.lexical_terms
    assert first.passage_key == second.passage_key
    assert first.search_term == second.search_term


def test_passage_reference_is_detected_and_scoped() -> None:
    result = plan("What is RV 1.1.1 about?")

    assert result.passage_key == "RV 1.1.1"
    assert result.veda_scope == "RV"
    assert QueryIntent.PASSAGE_LOOKUP in result.intents
    assert "passages" in result.retrieval_channels


def test_cross_veda_question_is_classified_and_unscoped() -> None:
    result = plan("How does Indra appear across the four Vedas?")

    assert QueryIntent.CROSS_VEDA in result.intents
    assert "Indra" in result.entities_mentioned
    assert result.veda_scope == "ALL"
    assert "cross_veda" in result.retrieval_channels


def test_the_deity_ap_is_not_found_inside_the_word_appear() -> None:
    """The Ap bug. Word-boundary matching, never substring containment."""
    result = plan("How does Indra appear across the four Vedas?")

    assert "Ap" not in result.entities_mentioned
    assert not any(e.lower() == "ap" for e in result.entities_mentioned)


def test_ap_is_still_detected_when_the_question_actually_names_it() -> None:
    """The fix must not be a blocklist: the deity is real and askable."""
    result = plan("Which hymns are dedicated to Ap?")

    assert "Ap" in result.entities_mentioned


def test_presence_question_routes_to_the_lexical_channel() -> None:
    """The question whose wrong answer is the dangerous one.

    Asked whether the Yajurveda mentions *ayas*, a system that finds no row and says "no"
    has asserted textual absence from a retrieval artefact. The lexical channel is the only
    one that reports the searchable surface alongside the hit count.
    """
    result = plan("Does Yajurveda mention ayas?")

    assert result.veda_scope == "YV"
    assert "ayas" in result.lexical_terms
    assert "lexical" in result.retrieval_channels


def test_quoted_term_wins_as_the_lexical_subject() -> None:
    result = plan("Is the word 'ayas' attested in the Rigveda?")

    assert result.lexical_terms[0] == "ayas"


def test_connection_question_needs_two_entities() -> None:
    result = plan("How are Agni and Soma connected?")

    assert QueryIntent.GRAPH_CONNECTION in result.intents
    assert "Agni" in result.entities_mentioned
    assert "Soma" in result.entities_mentioned
    assert "graph_paths" in result.retrieval_channels


def test_one_entity_does_not_select_the_path_channel() -> None:
    """A path needs two endpoints, so the channel is not selected with one subject."""
    result = plan("What is Agni connected to?")

    assert QueryIntent.GRAPH_CONNECTION not in result.intents


def test_explicit_veda_overrides_detection() -> None:
    result = plan("What does the Rigveda say about Agni?", explicit_veda="AV")

    assert result.veda_scope == "AV"


def test_explicit_all_does_not_override_detection() -> None:
    result = plan("What does the Rigveda say about Agni?", explicit_veda="ALL")

    assert result.veda_scope == "RV"


def test_two_named_vedas_leave_the_scope_open() -> None:
    """Naming two corpora is a comparison, not a restriction to either."""
    result = plan("Does the Rigveda or the Atharvaveda mention takman?")

    assert result.veda_scope == "ALL"


def test_stopwords_are_not_entities() -> None:
    result = plan("Which Veda mentions Agni?")

    assert "Agni" in result.entities_mentioned
    assert "Veda" not in result.entities_mentioned
    assert "Which" not in result.entities_mentioned


def test_the_search_channel_is_always_a_fallback() -> None:
    result = plan("Tell me something about the corpus")

    assert "search" in result.retrieval_channels
    assert result.intents == [QueryIntent.GENERAL_VEDIC_QUERY]


def test_search_term_is_stripped_of_query_metacharacters() -> None:
    """The term reaches a parameter, not a query, but a Lucene metacharacter in it would
    still make a legitimate question fail as a syntax error."""
    result = plan("What about (soma) ~ *pressing* {ritual} 'x' \"y\"?")

    for char in "\"'\\{}()[]~*?:^":
        assert char not in result.search_term


def test_mode_does_not_change_the_selected_channels() -> None:
    """Mode is a synthesis directive. Retrieval must not vary with it, or two modes would
    answer from different evidence and neither would be comparable to the other."""
    question = "How are Agni and Soma connected?"

    auto = plan(question, mode=AskMode.AUTO)
    graph = plan(question, mode=AskMode.GRAPH)

    assert auto.retrieval_channels == graph.retrieval_channels
    assert auto.intents == graph.intents


def test_intents_and_channels_are_deduplicated() -> None:
    result = plan("Compare the recurring formula in the Rigveda and the Samaveda: is it reused?")

    assert len(result.intents) == len(set(result.intents))
    assert len(result.retrieval_channels) == len(set(result.retrieval_channels))
