"""The quantitative guardrail, tested on shapes rather than on the question that found it.

Q60 is the reason this module exists, so it is pinned here verbatim -- but every other
test is synthetic and question-agnostic, because a validator that only recognises one
benchmark sentence is a hard-coded answer wearing a test suite. The rules are exercised
in both directions: each failing shape has a passing twin differing only in the figures,
which is what distinguishes a rule that checks arithmetic from one that greps for a word.

Nothing here needs a provider or a database.
"""

from __future__ import annotations

import pytest

from vedagraph.api.ask.evidence import EvidencePacket
from vedagraph.api.ask.models import EvidenceItem, EvidenceItemType
from vedagraph.api.ask.quantitative import (
    REPAIR_INSTRUCTION,
    QuantitativeRule,
    numeric_facts,
    validate,
)


def packet(
    fact: str,
    *,
    status: str = "SUPPORTED",
    item_type: EvidenceItemType = EvidenceItemType.CORPUS_DISTRIBUTION,
    eid: str = "E1",
) -> EvidencePacket:
    return EvidencePacket(
        items=[
            EvidenceItem(id=eid, type=item_type, fact=fact, knowledge_status=status),
        ]
    )


def rules(answer: str, pkt: EvidencePacket) -> list[str]:
    return [f.rule.value for f in validate(answer, pkt).findings]


# ---------------------------------------------------------------------------
# The failure that motivated the module
# ---------------------------------------------------------------------------

#: The real E7 from the Q60 evidence packet, copied from the live run.
Q60_HOTR_FACT = (
    "Verses per corpus for priest (hotṛ) — AV via MENTIONS_ENTITY: 18 verses; "
    "AV via ABOUT_CONCEPT: 21 verses; RV via MENTIONS_ENTITY: 195 verses; "
    "RV via ABOUT_CONCEPT: 208 verses; SV via MENTIONS_ENTITY: 38 verses; "
    "SV via ABOUT_CONCEPT: 41 verses; YV via MENTIONS_ENTITY: 49 verses; "
    "YV via ABOUT_CONCEPT: 50 verses."
)

#: The sentence the frozen run actually returned, graded MISLEADING.
Q60_SENTENCE = (
    "Both concepts are widely attested across the four Saṃhitās: the hotṛ appears in "
    "hundreds of verses in each corpus, and the sacrifice in hundreds as well [E1]."
)


def test_the_q60_overstatement_is_caught() -> None:
    audit = validate(Q60_SENTENCE, packet(Q60_HOTR_FACT))

    assert not audit.ok
    assert audit.findings[0].rule is QuantitativeRule.UNIVERSAL
    # The finding must quote the figures that refute the claim, not merely assert one.
    assert "18" in audit.findings[0].detail


def test_the_same_sentence_passes_when_the_figures_support_it() -> None:
    """The rule reads the numbers. Swap them and the identical prose is fine."""
    generous = Q60_HOTR_FACT.replace(": 18 ", ": 180 ").replace(": 21 ", ": 210 ")
    generous = generous.replace(": 38 ", ": 380 ").replace(": 41 ", ": 410 ")
    generous = generous.replace(": 49 ", ": 490 ").replace(": 50 ", ": 500 ")

    assert validate(Q60_SENTENCE, packet(generous)).ok


def test_the_guardrail_names_no_question_and_no_figure() -> None:
    """The repair instruction must stay generic, or it becomes a per-question fix."""
    lowered = REPAIR_INSTRUCTION.lower()
    assert "q60" not in lowered
    assert "hot" not in lowered
    assert not any(character.isdigit() for character in REPAIR_INSTRUCTION)


# ---------------------------------------------------------------------------
# MAGNITUDE and UNIVERSAL
# ---------------------------------------------------------------------------

FOUR_SMALL = "Counts — A: 18 verses; B: 195 verses; C: 38 verses; D: 49 verses."
FOUR_LARGE = "Counts — A: 118 verses; B: 195 verses; C: 138 verses; D: 149 verses."


def test_hundreds_in_each_group_fails_when_a_group_is_below_one_hundred() -> None:
    assert rules("There are hundreds of verses in each group [E1].", packet(FOUR_SMALL)) == [
        "UNIVERSAL"
    ]


def test_more_than_one_hundred_in_each_group_passes_when_every_group_clears_it() -> None:
    claim = "There are more than 100 verses in each group [E1]."
    assert validate(claim, packet(FOUR_LARGE)).ok


def test_more_than_a_bound_fails_when_a_group_is_below_it() -> None:
    claim = "There are more than 100 verses in each group [E1]."
    assert rules(claim, packet(FOUR_SMALL)) == ["UNIVERSAL"]


def test_hundreds_without_a_universal_passes_when_one_group_reaches_it() -> None:
    """Unquantified "hundreds" is defensible if any cited figure is that large."""
    assert validate("The term appears in hundreds of verses [E1].", packet(FOUR_SMALL)).ok


def test_hundreds_without_a_universal_fails_when_no_group_reaches_it() -> None:
    small = "Counts — A: 18 verses; B: 20 verses."
    assert rules("The term appears in hundreds of verses [E1].", packet(small)) == ["MAGNITUDE"]


def test_thousands_fails_below_one_thousand() -> None:
    assert rules("Thousands of verses attest it [E1].", packet("Counts — RV: 400 verses.")) == [
        "MAGNITUDE"
    ]


def test_thousands_passes_at_one_thousand() -> None:
    assert validate("Thousands of verses attest it [E1].", packet("Counts — RV: 1400 verses.")).ok


def test_a_counted_universal_fails_when_the_evidence_enumerates_fewer_groups() -> None:
    """ "all ten mandalas" over an enumeration of nine.

    Found by running this validator over the sixty already-graded answers: Indra's
    structural spread lists nine mandalas because he has no HAS_DEVATA attribution in
    mandala 9 at all, and the answer rounded that to "all ten".
    """
    spread = 'DEVATA_STRUCTURAL_SPREAD: {"1": 493, "10": 402, "2": 141, "3": 229, "8": 862}'
    claim = "These verses are distributed across all ten mandalas [E1]."

    assert rules(claim, packet(spread, item_type=EvidenceItemType.METRIC)) == ["UNIVERSAL"]


def test_a_counted_universal_passes_when_the_enumeration_matches() -> None:
    spread = 'SPREAD: {"1": 493, "2": 402, "3": 141, "4": 229, "5": 862}'
    claim = "These verses are distributed across all five mandalas [E1]."

    assert validate(claim, packet(spread, item_type=EvidenceItemType.METRIC)).ok


def test_more_rows_than_groups_is_never_a_contradiction() -> None:
    """ "all four corpora" against an item carrying two rows per corpus."""
    claim = "The concept is attested in all four corpora [E1]."
    assert validate(claim, packet(Q60_HOTR_FACT)).ok


# ---------------------------------------------------------------------------
# COMPARISON
# ---------------------------------------------------------------------------

A_TEN_B_TWENTY = "Counts — A: 10 verses; B: 20 verses."


def test_a_has_more_than_b_fails_when_b_is_larger() -> None:
    assert rules("A has more than B [E1].", packet(A_TEN_B_TWENTY)) == ["COMPARISON"]


def test_b_has_more_than_a_passes_when_b_is_larger() -> None:
    assert validate("B has more than A [E1].", packet(A_TEN_B_TWENTY)).ok


def test_a_has_fewer_than_b_passes_when_a_is_smaller() -> None:
    assert validate("A has fewer than B [E1].", packet(A_TEN_B_TWENTY)).ok


def test_a_superlative_fails_when_another_group_holds_the_maximum() -> None:
    counts = "Counts — RV: 400 verses; AVS: 30 verses."
    assert rules("AVS has the largest share [E1].", packet(counts)) == ["COMPARISON"]


def test_a_superlative_passes_when_the_named_group_holds_the_maximum() -> None:
    counts = "Counts — RV: 400 verses; AVS: 30 verses."
    assert validate("RV has the largest share [E1].", packet(counts)).ok


# ---------------------------------------------------------------------------
# MAJORITY
# ---------------------------------------------------------------------------


def test_most_fails_at_or_below_one_half() -> None:
    assert rules("Most hymns carry it [E1].", packet("Coverage: 3 of 10 hymns.")) == ["MAJORITY"]


def test_most_passes_above_one_half() -> None:
    assert validate("Most hymns carry it [E1].", packet("Coverage: 8 of 10 hymns.")).ok


def test_exactly_half_is_not_most() -> None:
    assert rules("Most hymns carry it [E1].", packet("Coverage: 5 of 10 hymns.")) == ["MAJORITY"]


def test_superlative_most_is_not_read_as_a_majority() -> None:
    """ "most densely" is a superlative. Flagging it would be a false positive."""
    assert validate("It appears most densely in the RV [E1].", packet("Coverage: 3 of 10.")).ok


def test_most_with_no_ratio_in_the_evidence_is_not_judged() -> None:
    """No ratio, no finding. The rule stays silent rather than guessing a denominator."""
    assert validate("Most hymns carry it [E1].", packet("Counts — RV: 3 verses.")).ok


# ---------------------------------------------------------------------------
# ABSENCE
# ---------------------------------------------------------------------------


def test_a_zero_over_an_unestablished_status_fails() -> None:
    audit = validate(
        "There are zero occurrences of the term [E1].",
        packet("Lexical search. RV: 0 matches.", status="NO_LEXICAL_MATCH"),
    )
    assert [f.rule for f in audit.findings] == [QuantitativeRule.ABSENCE]


@pytest.mark.parametrize("status", ["UNKNOWN", "INSUFFICIENT_EVIDENCE", "NOT_BUILT"])
def test_every_unestablished_status_refuses_a_hard_zero(status: str) -> None:
    audit = validate("The term does not occur [E1].", packet("A: 0 matches.", status=status))
    assert [f.rule for f in audit.findings] == [QuantitativeRule.ABSENCE]


def test_a_zero_over_a_measured_status_is_allowed() -> None:
    """A measured search result may be reported as one. This rule is about provenance."""
    assert validate(
        "There are zero occurrences of the term [E1].",
        packet("Lexical search. RV: 0 matches.", status="SUPPORTED"),
    ).ok


# ---------------------------------------------------------------------------
# Scope: what the validator refuses to judge
# ---------------------------------------------------------------------------


def test_an_uncited_sentence_is_not_judged() -> None:
    """Already unsupported under the citation contract; not this module's finding."""
    assert validate("There are hundreds in each group.", packet(FOUR_SMALL)).ok


def test_an_empty_packet_yields_no_findings() -> None:
    assert validate("Hundreds in each group [E1].", EvidencePacket(items=[])).ok


def test_an_invented_citation_is_not_a_quantitative_finding() -> None:
    """E9 is not in the packet. The citation audit owns that; this module skips it."""
    assert validate("There are hundreds in each group [E9].", packet(FOUR_SMALL)).ok


def test_a_verse_locus_is_not_read_as_a_quantity() -> None:
    """ "AVS 1.11.1" must not become the figures 1, 11 and 1."""
    assert validate(
        "The hotṛ utters the call at AVS 1.11.1 [E1].",
        packet("Counts — AV: 18 verses."),
    ).ok


def test_a_claim_is_checked_only_against_the_rows_its_own_sentence_cites() -> None:
    """A figure in an uncited item cannot manufacture a contradiction."""
    pkt = EvidencePacket(
        items=[
            EvidenceItem(
                id="E1",
                type=EvidenceItemType.CORPUS_DISTRIBUTION,
                fact="Counts — A: 400 verses; B: 500 verses.",
                knowledge_status="SUPPORTED",
            ),
            EvidenceItem(
                id="E2",
                type=EvidenceItemType.CORPUS_DISTRIBUTION,
                fact="Counts — C: 2 verses; D: 3 verses.",
                knowledge_status="SUPPORTED",
            ),
        ]
    )
    assert validate("There are hundreds of verses in each group [E1].", pkt).ok
    assert not validate("There are hundreds of verses in each group [E2].", pkt).ok


# ---------------------------------------------------------------------------
# Fact extraction
# ---------------------------------------------------------------------------


def test_per_corpus_rows_keep_their_own_labels_and_units() -> None:
    facts = numeric_facts(
        EvidenceItem(id="E7", type=EvidenceItemType.CORPUS_DISTRIBUTION, fact=Q60_HOTR_FACT)
    )
    by_group = {f.group: f.value for f in facts}

    assert by_group["AV via MENTIONS_ENTITY"] == 18
    assert by_group["RV via ABOUT_CONCEPT"] == 208
    assert {f.unit for f in facts} == {"verse"}


def test_a_json_metric_is_split_into_one_group_per_key() -> None:
    facts = numeric_facts(
        EvidenceItem(
            id="E13",
            type=EvidenceItemType.METRIC,
            fact='DEVATA_STRUCTURAL_SPREAD: {"1": 493, "8": 862}',
        )
    )
    assert {f.value for f in facts} == {493, 862}
    assert len({f.group for f in facts}) == 2


def test_an_item_with_no_figures_yields_no_facts() -> None:
    item = EvidenceItem(
        id="E21", type=EvidenceItemType.GRAPH_PATH, fact="Path: Soma -[CO_OCCURS_WITH]- Agni"
    )
    assert numeric_facts(item) == []


def test_the_summary_is_readable_and_names_no_internals() -> None:
    audit = validate(Q60_SENTENCE, packet(Q60_HOTR_FACT))
    summary = audit.summary()

    assert "quantitative" in summary.lower()
    assert "E1" not in summary
    assert "UNIVERSAL" not in summary
