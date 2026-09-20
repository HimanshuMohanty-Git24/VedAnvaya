"""The ranking guard, tested on shapes rather than on the question that found it.

Q38 is the reason this rule exists, and its two sentences are pinned here verbatim with
the real evidence rows they cited -- because a defect that reached a release gate deserves
a test that would have caught it. Everything else is synthetic, and every failing shape
has a passing twin differing only in what the evidence compares. That pairing is the whole
point: a rule that fires on the word "largest" regardless of the packet is not a guard,
it is a style checker, and it would cost this product the corpus rankings it can actually
prove.

The rule's contract, restated so a reader need not infer it from the regexes:

    a ranking word is sayable only where the cited rows hold a comparison the sentence has
    joined -- two or more labelled groups with figures, and one of them named in the
    ranking's own clause.

Nothing here needs a provider or a database.
"""

from __future__ import annotations

import pytest

from vedagraph.api.ask.evidence import EvidencePacket
from vedagraph.api.ask.models import EvidenceItem, EvidenceItemType
from vedagraph.api.ask.quantitative import REPAIR_INSTRUCTION, QuantitativeRule, validate

RANKING = QuantitativeRule.UNSUPPORTED_RANKING.value


def packet(
    *facts: str,
    item_type: EvidenceItemType = EvidenceItemType.CORPUS_DISTRIBUTION,
) -> EvidencePacket:
    return EvidencePacket(
        items=[
            EvidenceItem(id=f"E{n}", type=item_type, fact=fact, knowledge_status="SUPPORTED")
            for n, fact in enumerate(facts, start=1)
        ]
    )


def rules(answer: str, pkt: EvidencePacket) -> list[str]:
    return [f.rule.value for f in validate(answer, pkt).findings]


# ---------------------------------------------------------------------------
# The failure that motivated the rule
# ---------------------------------------------------------------------------

#: The real E10 from the Q38 packet, replayed from the live graph. It counts one deity
#: across four corpora, which ranks the corpora and says nothing about the deity.
Q38_MENTIONS_FACT = (
    "Verses per corpus for the Maruts — AV via MENTIONS_DEVATA: 77 verses (77 certain, "
    "0 probable); RV via MENTIONS_DEVATA: 401 verses (401 certain, 0 probable); "
    "SV via MENTIONS_DEVATA: 28 verses (28 certain, 0 probable); YV via "
    "MENTIONS_DEVATA: 54 verses (54 certain, 0 probable)."
)

#: The real E11 and E12: the dedication total, and its precision split.
Q38_ATTRIBUTION_FACTS = (
    'DEVATA_ATTRIBUTION_BY_VEDA: {"RV": 428}',
    'DEVATA_ATTRIBUTION_PRECISION: {"per_passage": 49, "container_inherited": 379, '
    '"per_passage_share": 0.1145}',
)

#: The sentences the formal run actually returned, graded MISLEADING. Both are true about
#: every figure they state and false about the only word that is not a figure.
Q38_MENTION_SENTENCE = (
    "They are the most widely mentioned deity group in the corpus: the MENTIONS_DEVATA "
    "layer records 401 certain occurrences in the Rigveda, 77 in the Atharvaveda, 54 in "
    "the Yajurveda and 28 in the Samaveda [E1]."
)
Q38_DEDICATION_SENTENCE = (
    "In the Rigveda they also receive the largest number of hymn-level dedications "
    "(HAS_DEVATA), totalling 428 verses, though the majority of those are "
    "container-inherited from the sukta label rather than stated per verse [E1, E2]."
)


def test_the_q38_mention_ranking_is_caught() -> None:
    """A count of one subject across four corpora ranked the corpora, not the subject."""
    audit = validate(Q38_MENTION_SENTENCE, packet(Q38_MENTIONS_FACT))

    assert not audit.ok
    assert audit.findings[0].rule is QuantitativeRule.UNSUPPORTED_RANKING
    # The finding must say what the rows compare, so a reader can check the call.
    assert "MENTIONS_DEVATA" in audit.findings[0].detail
    assert "A count is not a rank." in audit.findings[0].detail


def test_the_q38_dedication_ranking_is_caught() -> None:
    audit = validate(
        Q38_DEDICATION_SENTENCE,
        packet(*Q38_ATTRIBUTION_FACTS, item_type=EvidenceItemType.METRIC),
    )

    assert not audit.ok
    assert [f.rule for f in audit.findings] == [QuantitativeRule.UNSUPPORTED_RANKING]


def test_the_q38_figures_themselves_were_never_the_problem() -> None:
    """Why no rule before this one could see it: every integer checks out.

    560 is the subject's true total, 428 its true dedication count, and both are cited to
    the rows that hold them. Strip the two ranking words and the same sentences audit
    clean -- which is exactly what made the defect survive a citation audit, a figure
    check and six arithmetic rules.
    """
    bounded = (
        "The graph records 401 certain occurrences in the Rigveda, 77 in the "
        "Atharvaveda, 54 in the Yajurveda and 28 in the Samaveda [E1]."
    )

    assert validate(bounded, packet(Q38_MENTIONS_FACT)).ok


# ---------------------------------------------------------------------------
# 1. A count is not a rank
# ---------------------------------------------------------------------------

ONE_SUBJECT = "Verses per corpus for the Maruts — RV via MENTIONS_DEVATA: 560 verses."


@pytest.mark.parametrize(
    "claim",
    [
        "The Maruts are the most widely mentioned deity group [E1].",
        "The Maruts receive the largest number of dedications [E1].",
        "The Maruts hold the highest mention count of any deity [E1].",
        "The Maruts are the greatest recipient of praise in the corpus [E1].",
        "The Maruts are the leading deity group by mention [E1].",
        "The Maruts are the top deity group by mention [E1].",
        "The Maruts are mentioned in more verses than any other deity [E1].",
        "The Maruts are the most frequently mentioned deity group [E1].",
    ],
)
def test_one_subjects_count_cannot_produce_a_rank(claim: str) -> None:
    """Requirement 1 and 2: 560 is a quantity, and no quantity is a rank.

    Eight phrasings of the same unlicensed claim over the same single row. The rule keys
    on the comparison the evidence does or does not hold, so no phrasing escapes it by
    choosing a different word for "first".
    """
    assert rules(claim, packet(ONE_SUBJECT)) == [RANKING]


def test_a_dedication_count_cannot_infer_largest() -> None:
    """Requirement 3, on the real row: 428 is rank six, and the packet cannot tell."""
    claim = "They receive the largest number of hymn-level dedications, 428 verses [E1]."

    assert rules(claim, packet(*Q38_ATTRIBUTION_FACTS, item_type=EvidenceItemType.METRIC)) == [
        RANKING
    ]


def test_the_bounded_form_of_the_same_claim_passes() -> None:
    """The remedy the repair instruction asks for, asserted rather than described."""
    bounded = "The graph records 560 verses mentioning the Maruts [E1]."
    assert validate(bounded, packet(ONE_SUBJECT)).ok
    assert validate(
        "The graph records 428 hymn-level dedications to the Maruts [E1].",
        packet(*Q38_ATTRIBUTION_FACTS, item_type=EvidenceItemType.METRIC),
    ).ok


# ---------------------------------------------------------------------------
# 4. Explicit ranking evidence licenses a superlative
# ---------------------------------------------------------------------------

#: A row that does compare the ranked population: three deities, one measure.
RANKED_DEITIES = (
    "Hymn-level dedications by deity — Indra: 2869 verses; Agni: 1988 verses; Maruts: 428 verses."
)


def test_a_superlative_is_licensed_when_the_evidence_ranks_the_population() -> None:
    """Requirement 4. The same sentence shape, now over rows that compare deities."""
    claim = "Indra receives the largest number of hymn-level dedications, 2869 verses [E1]."

    assert validate(claim, packet(RANKED_DEITIES)).ok


def test_a_licensed_superlative_is_still_checked_for_truth() -> None:
    """Licensing is not a pass. Where the evidence ranks, the ordering rule adjudicates.

    This is the pairing that makes the guard a guard: the same row that licenses Indra's
    claim refutes Agni's, and the finding comes from COMPARISON -- the rule that reads the
    figures -- not from the ranking rule, which has nothing left to say once the
    comparison is present.
    """
    claim = "Agni receives the largest number of hymn-level dedications [E1]."

    assert rules(claim, packet(RANKED_DEITIES)) == [QuantitativeRule.COMPARISON.value]


def test_a_per_corpus_superlative_is_licensed_by_the_corpus_row() -> None:
    """The commonest legitimate ranking this product makes: one corpus against the rest.

    Pinned because it is the shape most easily broken by tightening the rule. The packet
    labels its rows "RV via MENTIONS_DEVATA" and the prose writes "the Rigveda"; if those
    do not meet, every true per-corpus superlative this product writes gets a caveat.
    """
    claim = (
        "According to the MENTIONS_DEVATA annotation layer, the Rigveda has the most "
        "verses that mention Indra [E1]."
    )

    assert validate(claim, packet(Q38_MENTIONS_FACT)).ok


def test_a_group_named_after_the_ranking_word_licenses_it_too() -> None:
    """ "most densely in X" names what it ranks over on the other side of the word."""
    claim = "The concept appears most densely in the Atharvaveda [E1]."

    assert validate(claim, packet(Q38_MENTIONS_FACT)).ok


def test_a_scope_phrase_is_not_the_ranked_subject() -> None:
    """The one preposition that separates the two Q38 sentences from the licensed ones.

    "In the Rigveda they receive the largest ..." is set in a corpus and ranks deities;
    ", the Rigveda has the most ..." ranks the corpora. Same corpus name, same row, and
    only one of them is a claim the evidence can carry.
    """
    ranks_deities = "In the Rigveda they receive the largest number of dedications [E1]."
    ranks_corpora = "Of the four corpora, the Rigveda carries the largest number [E1]."

    assert rules(ranks_deities, packet(Q38_MENTIONS_FACT)) == [RANKING]
    assert validate(ranks_corpora, packet(Q38_MENTIONS_FACT)).ok


def test_the_clause_after_a_colon_does_not_license_the_claim_before_it() -> None:
    """Q38's exact shape: assert a rank, then change subject to the figures behind it."""
    claim = "They are the most widely mentioned deity group: the RV records 401 verses [E1]."

    assert rules(claim, packet(Q38_MENTIONS_FACT)) == [RANKING]


def test_an_earlier_clause_does_not_license_a_later_ranking() -> None:
    """The window is bounded on both sides, and for the same reason.

    "The RV records 401 verses" is a licensed statement of one row; the clause after the
    semicolon is a rank over deities. Letting the first license the second would mean any
    answer that quoted a figure first could rank anything afterwards.
    """
    claim = "The RV records 401 verses; they are the most widely mentioned deity group [E1]."

    assert rules(claim, packet(Q38_MENTIONS_FACT)) == [RANKING]


def test_a_relation_name_shared_by_every_cited_row_names_no_group() -> None:
    """Naming the measure is not picking a side in the comparison.

    All four of E10's rows are labelled "<corpus> via MENTIONS_DEVATA", so the relation
    name distinguishes none of them. An answer writing "under MENTIONS_DEVATA" has said
    which layer it counted in, not which row it claims is first -- and that is the exact
    token the graded failure had in its sentence.
    """
    claim = "They are the most widely mentioned deity group under MENTIONS_DEVATA [E1]."

    assert rules(claim, packet(Q38_MENTIONS_FACT)) == [RANKING]


# ---------------------------------------------------------------------------
# 5. Ordinary quantitative prose is untouched
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "claim",
    [
        "The MENTIONS_DEVATA layer records 401 verses in the Rigveda [E1].",
        "Of the four corpora, the Rigveda carries 401 verses and the Samaveda 28 [E1].",
        "At most 401 verses carry the annotation [E1].",
        "At least 28 verses carry it in every corpus [E1].",
        "The figure is most likely an undercount of the annotation layer [E1].",
        "Most of the 401 verses are in the Rigveda [E1].",
        "The layer records 401 verses, leading to a four-corpus total of 560 [E1].",
    ],
)
def test_non_ranking_quantitative_prose_is_unchanged(claim: str) -> None:
    """Requirement 5. A bound, a hedge, a majority and a participle are not rankings.

    "at most" and "at least" are numeric bounds the comparison rule owns; "most likely" is
    a hedge; "most of" is a majority; "leading to" is a preposition. Each of them contains
    a word from the ranking lexicon, and a rule that flagged them would be reporting on
    English rather than on evidence.
    """
    assert RANKING not in rules(claim, packet(Q38_MENTIONS_FACT))


def test_a_bare_most_is_a_majority_and_not_a_rank() -> None:
    """ "Most hymns carry it" is a claim about more than half, and has its own rule."""
    found = rules("Most hymns carry it [E1].", packet("Coverage: 3 of 10 hymns."))

    assert found == [QuantitativeRule.MAJORITY.value]


def test_a_ranking_word_the_packet_itself_printed_is_not_the_models_claim() -> None:
    """An answer reporting what a cited item says has invented nothing.

    This project's own registry describes Savitr as "invoked in the most repeated verse of
    the tradition". Flagging the answer that quotes it would tell the reader to distrust a
    correctly attributed characterisation, and would make this rule a complaint about the
    registry's prose.
    """
    registry = (
        "The Impeller, the vivifying power of the sun, invoked in the most repeated "
        "verse of the tradition.; Registry occurrence count: 34"
    )
    claim = (
        "One interpretation in VedaGraph's registry glosses Savitr as invoked in the "
        "most repeated verse of the tradition [E1]."
    )

    assert validate(claim, packet(registry, item_type=EvidenceItemType.ENTITY_FACT)).ok


def test_a_superlative_over_rows_with_no_figures_is_not_this_modules_business() -> None:
    """A rendered epithet is translation, not arithmetic.

    RV 1.1.1 calls Agni "the most lavish bestower of wealth (ratnadhatama)". The module
    opening refuses to be an entailment engine, and judging a superlative the packet
    printed no figures for would make it one.
    """
    claim = "It lauds Agni as the most lavish bestower of wealth (ratnadhatama) [E1]."
    passage = packet("", item_type=EvidenceItemType.PASSAGE)

    assert validate(claim, passage).ok


def test_a_refusal_to_rank_is_not_a_ranking() -> None:
    """The answer this product asks for must not be the answer it caveats."""
    claims = [
        "VedaGraph does not record which deity is mentioned most often [E1].",
        "The evidence does not establish which corpus carries the largest share [E1].",
        "No ranking of deities by dedication count is recorded in the graph [E1].",
    ]

    for claim in claims:
        assert RANKING not in rules(claim, packet(ONE_SUBJECT)), claim


# ---------------------------------------------------------------------------
# 6. Nothing already checked is weakened
# ---------------------------------------------------------------------------


def test_the_six_original_rules_still_fire_on_their_own_shapes() -> None:
    """Requirement 6, as a single reconciliation rather than six restatements.

    Each row is a shape one of the pre-existing rules owns. The ranking rule is additive:
    it must not displace, absorb or silence any of them, and a finding list that lost one
    of these would mean the new rule had eaten an older guarantee.
    """
    cases = [
        # MAGNITUDE: "hundreds" under 100.
        ("It fills hundreds of verses [E1].", "Counts — RV: 18 verses.", "MAGNITUDE"),
        # UNIVERSAL: a counted universal over fewer groups than claimed.
        (
            "It is attested in all four corpora [E1].",
            'SPREAD: {"RV": 195, "AV": 18}',
            "UNIVERSAL",
        ),
        # EXACT_COUNT: a restated figure in no cited row.
        ("It appears in 77 verses [E1].", "Counts — RV: 18 verses.", "EXACT_COUNT"),
        # COMPARISON: a numeric bound no cited figure meets.
        ("More than 400 verses carry it [E1].", "Counts — RV: 18 verses.", "COMPARISON"),
        # MAJORITY: "most" at or below one half.
        ("Most hymns carry it [E1].", "Coverage: 3 of 10 hymns.", "MAJORITY"),
    ]
    for claim, fact, expected in cases:
        item_type = (
            EvidenceItemType.METRIC
            if fact.startswith("SPREAD")
            else EvidenceItemType.CORPUS_DISTRIBUTION
        )
        assert expected in rules(claim, packet(fact, item_type=item_type)), claim


def test_the_absence_rule_is_untouched_by_the_ranking_lexicon() -> None:
    """ABSENCE reads a knowledge status, not a word, and shares no vocabulary."""
    pkt = EvidencePacket(
        items=[
            EvidenceItem(
                id="E1",
                type=EvidenceItemType.LEXICAL_PRESENCE,
                fact="Counts — RV: 0 verses; AV: 0 verses.",
                knowledge_status="NO_LEXICAL_MATCH",
            )
        ]
    )

    assert QuantitativeRule.ABSENCE.value in rules("The term does not occur [E1].", pkt)


def test_an_uncited_ranking_is_left_to_the_citation_contract() -> None:
    """Scope is unchanged: this module reads cited sentences and no others."""
    assert validate("The Maruts are the most mentioned deity group.", packet(ONE_SUBJECT)).ok


def test_the_repair_instruction_names_the_class_and_no_question() -> None:
    """A repair prompt that named the figure would teach a one-sentence patch.

    The instruction must describe the rule and the remedy without naming the question, the
    subject or the number that failed -- otherwise the fix is per-question, which is the
    one thing this contract forbids.
    """
    lowered = REPAIR_INSTRUCTION.lower()

    assert "rank" in lowered
    assert "quantity, not a rank" in lowered
    for leaked in ("marut", "q38", "560", "428", "indra"):
        assert leaked not in lowered
