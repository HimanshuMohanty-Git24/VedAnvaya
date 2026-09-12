"""Citation validation, and the grouped-citation bug that made it decidable.

The defect: models group ids, and they group them often. Gemini answering "Who is Indra?"
wrote ``[E6, E7, E8, E9]`` in prose, and the single-id pattern ``\\[E(\\d+)\\]`` matched
none of those four. The consequence was not cosmetic. Grouped ids were absent from the
response's citation list, and -- the part that matters -- they were never checked against
the packet, so an invented id inside a group would have reached the reader with the audit
reporting the answer clean.

The second failure is subtler and has its own tests below: a model can cite a *real* id and
attach Sanskrit that item does not contain. The citation resolves, so a reader who follows
it sees a real verse and assumes the quote came from it.
"""

from __future__ import annotations

import pytest

from vedagraph.api.ask.citation import (
    _IAST_MARKS,
    _rewrite_citations,
    _sanskrit_runs,
    audit,
    extract_cited_ids,
    verify_quotes,
)
from vedagraph.api.ask.evidence import EvidencePacket
from vedagraph.api.ask.models import EvidenceItem, EvidenceItemType

SANSKRIT = "agnim īḷe purohitaṃ yajñasya devam ṛtvijam"


def item(
    item_id: str,
    *,
    item_type: EvidenceItemType = EvidenceItemType.PASSAGE,
    citation: str = "RV 1.1.1",
    sanskrit: str | None = None,
    translation: str | None = None,
) -> EvidenceItem:
    return EvidenceItem(
        id=item_id,
        type=item_type,
        citation=citation,
        passage_key=citation.replace(" ", "_"),
        veda="RV",
        sanskrit=sanskrit,
        translation=translation,
    )


def packet(*items: EvidenceItem) -> EvidencePacket:
    return EvidencePacket(items=list(items))


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


def test_single_ids_are_extracted_in_order() -> None:
    assert extract_cited_ids("Simple [E1] and [E2].") == ["E1", "E2"]


def test_a_grouped_citation_yields_every_id() -> None:
    """The bug. A single-id regex matched none of these four."""
    assert extract_cited_ids("Grouped [E6, E7, E8, E9] here.") == [
        "E6",
        "E7",
        "E8",
        "E9",
    ]


def test_mixed_single_and_grouped_spellings() -> None:
    found = extract_cited_ids("Mixed [E1] then [E2, E3] and [E4;E5].")

    assert found == ["E1", "E2", "E3", "E4", "E5"]


@pytest.mark.parametrize(
    "answer",
    [
        "Adjacent [E1][E2].",
        "Semicolons [E1; E2].",
        "Prose [E1 and E2].",
        "Spaced [ E1 , E2 ].",
    ],
)
def test_group_separators_do_not_need_a_pattern_each(answer: str) -> None:
    assert extract_cited_ids(answer) == ["E1", "E2"]


def test_bracketed_text_that_is_not_a_citation_is_ignored() -> None:
    assert extract_cited_ids("Not a citation [see above] but [E3] is.") == ["E3"]


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        ("Fullwidth 【E1】 here.", ["E1"]),
        ("Fullwidth grouped 【E2, E3】.", ["E2", "E3"]),
        ("Fullwidth square ［E4］.", ["E4"]),  # noqa: RUF001
        ("Mixed [E1] and 【E5】.", ["E1", "E5"]),
    ],
)
def test_non_ascii_bracket_spellings_are_still_citations(answer: str, expected: list[str]) -> None:
    """``gpt-oss-120b`` on Groq emits CJK fullwidth brackets: ``【E1】``.

    An ASCII-only pattern scored those as *uncited*, which is worse than losing a
    footnote: support grading is citation-derived, so a properly grounded answer was
    reported INSUFFICIENT_EVIDENCE with an empty citation list -- telling the reader the
    graph had nothing to say about a question it had answered from four passages.
    """
    assert extract_cited_ids(answer) == expected


@pytest.mark.parametrize(
    "answer",
    [
        "Agni is praised 【E1】.",
        "Agni is praised ［E1］.",  # noqa: RUF001
        "Agni is praised [E1].",
    ],
)
def test_every_surviving_marker_is_normalised_to_ascii(answer: str) -> None:
    """Whatever spelling the model chose, one form leaves this API.

    The frontend renders a marker as a clickable chip by parsing ASCII ``[E1]``, so an
    un-normalised ``【E1】`` reached the page as inert literal text: the citation was
    verified, listed in ``citations``, and completely unreachable to the reader. The
    marker format has to be a property of this API rather than of whichever vendor
    answered, so normalisation runs on every answer and not only on ones needing repair.
    """
    result = audit(answer, packet(item("E1")))

    assert result.cleaned_answer == "Agni is praised [E1]."
    assert result.invented_ids == []
    assert [c.id for c in result.citations] == ["E1"]


def test_ids_are_deduplicated_preserving_first_appearance() -> None:
    assert extract_cited_ids("[E1] and again [E1]") == ["E1"]
    assert extract_cited_ids("[E2] then [E1] then [E2]") == ["E2", "E1"]


def test_no_citations_is_an_empty_list_not_a_guess() -> None:
    assert extract_cited_ids("A confident answer with no citations at all.") == []


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------


def test_an_answer_citing_only_real_ids_is_clean() -> None:
    result = audit("Indra is invoked [E1] and so is Agni [E2].", packet(item("E1"), item("E2")))

    assert result.invented_ids == []
    assert result.is_clean is True
    assert len(result.citations) == 2
    assert [c.id for c in result.citations] == ["E1", "E2"]
    assert result.citations[0].citation == "RV 1.1.1"
    assert result.cleaned_answer == "Indra is invoked [E1] and so is Agni [E2]."


def test_an_invented_id_inside_a_group_is_removed_from_the_prose() -> None:
    """Group-aware stripping. A naive ``replace("[E9]", "")`` cannot touch the ``E9``
    inside ``[E1, E9]``: it would leave the fabricated id in the prose while the caveat
    claimed it had been removed."""
    result = audit("Indra is invoked [E1, E9] in this verse.", packet(item("E1"), item("E2")))

    assert result.invented_ids == ["E9"]
    assert result.is_clean is False
    assert "E9" not in result.cleaned_answer
    assert "E1" in result.cleaned_answer
    assert [c.id for c in result.citations] == ["E1"]


def test_a_group_that_loses_every_id_is_removed_entirely() -> None:
    result = audit("This is asserted [E9].", packet(item("E1")))

    assert result.invented_ids == ["E9"]
    assert "E9" not in result.cleaned_answer
    assert "[" not in result.cleaned_answer
    assert result.cleaned_answer == "This is asserted."


def test_stripping_leaves_non_citation_brackets_alone() -> None:
    cleaned = _rewrite_citations("See [above] and [E1, E9] here.", frozenset({"E9"}))

    assert "[above]" in cleaned
    assert "[E1]" in cleaned
    assert "E9" not in cleaned


def test_the_sentence_survives_its_removed_marker() -> None:
    """The sentence is left standing because its other citations may still support it.
    What cannot remain is a marker pointing at evidence that does not exist."""
    result = audit("Agni is the first word of the Rigveda [E1, E9].", packet(item("E1")))

    assert "Agni is the first word of the Rigveda" in result.cleaned_answer


# ---------------------------------------------------------------------------
# Quotes
# ---------------------------------------------------------------------------


def test_sanskrit_present_in_a_cited_item_verifies() -> None:
    cited = [item("E1", sanskrit=SANSKRIT)]

    assert verify_quotes("The verse reads yajñasya devam ṛtvijam [E1].", cited) == []


def test_invented_sanskrit_is_reported_even_though_the_citation_resolves() -> None:
    """The harder failure: the id is real, so a reader who follows it sees a real verse
    and assumes the quote came from it."""
    cited = [item("E1", sanskrit="indraṃ mitraṃ varuṇam agnim āhuḥ")]

    unverified = verify_quotes("The verse reads agnimīḷe purohitaṃ [E1].", cited)

    assert unverified
    assert any("agnim" in run for run in unverified)


def test_a_quote_matching_the_translation_also_verifies() -> None:
    cited = [item("E1", translation="I laud Agni, the chosen Priest, God, ṛtvijam")]

    assert verify_quotes("Griffith renders it ṛtvijam [E1].", cited) == []


def test_a_verified_quote_mid_sentence_is_not_reported_unverified() -> None:
    """A correctly quoted Sanskrit word followed by English prose is not a finding.

    Regression for a real false alarm. ``_IAST_RUN`` once ended in a class containing
    plain Latin letters and whitespace, so it ran past the Sanskrit into the English
    after it and captured "ṛtvijam priest" as one run. That composite is in no evidence
    item -- it is not a quotation -- so a verbatim quote was reported unverified and the
    service told the reader to distrust a citation that was sound. Every word of a run
    must now carry a diacritic, so the run stops at the first English word.
    """
    cited = [item("E1", sanskrit=SANSKRIT)]

    assert verify_quotes("The verse names the ṛtvijam priest [E1].", cited) == []


#: RV 1.1.1 as the corpus actually stores it: pitch accents inline.
ACCENTED = "agnim ī́ḷe puróhitaṃ yajñásya devam ṛtvijám | hotā́raṃ ratnadhā́tamam ||"


@pytest.mark.parametrize(
    "answer",
    [
        "The formula devam ṛtvijam is recorded here [E1].",
        "It reads devam ṛtvijám [E1].",
        "It opens agnim īḷe purohitaṃ [E1].",
    ],
)
def test_an_unaccented_quote_of_accented_text_verifies(answer: str) -> None:
    """A model writes Sanskrit without pitch accents; the corpus stores it with them.

    Every Rigvedic and Atharvavedic primary text in this graph is accented inline, and
    scholarly prose quotes unaccented, so a literal comparison failed on *correct*
    quotations: ``ṛtvijam`` did not match the stored ``ṛtvijám`` and the service told the
    reader the answer contained Sanskrit absent from its evidence. Tone marks are folded
    on both sides so the two forms meet.
    """
    assert verify_quotes(answer, [item("E1", sanskrit=ACCENTED)]) == []


def test_folding_tone_marks_does_not_excuse_a_different_word() -> None:
    """Only tone marks fold. Phonemic diacritics survive, so an invented word still fails."""
    unverified = verify_quotes(
        "It reads somaṣya pavitram asti [E1].", [item("E1", sanskrit=ACCENTED)]
    )

    assert unverified


def test_a_multi_word_accented_quote_stays_whole() -> None:
    """The transmitted Rigvedic Sanskrit is accented inline, so a genuine multi-word
    quotation carries pitch accents on every word and must match as one run rather than
    being reported back to the reader as fragments of the words they wrote."""
    cited = [item("E1", sanskrit=SANSKRIT)]

    assert verify_quotes(f"It opens {SANSKRIT} [E1].", cited) == []


def test_no_quotable_cited_text_means_no_quote_verdict() -> None:
    """A quote check against a lexical-presence or metric item is vacuous, so it does not
    manufacture a finding."""
    cited = [
        item(
            "E1",
            item_type=EvidenceItemType.LEXICAL_PRESENCE,
            citation="",
            sanskrit=SANSKRIT,
        )
    ]

    assert verify_quotes("It reads yajñasya devam ṛtvijam [E1].", cited) == []


def test_short_entity_names_in_prose_are_not_treated_as_quotations() -> None:
    cited = [item("E1", translation="I laud Agni, the chosen Priest.")]

    assert verify_quotes("Ṛta is a concept [E1].", cited) == []


def test_an_unverified_quote_makes_the_audit_unclean() -> None:
    result = audit(
        "The verse reads agnimīḷe purohitaṃ [E1].",
        packet(item("E1", sanskrit="indraṃ mitraṃ varuṇam agnim āhuḥ")),
    )

    assert result.invented_ids == []
    assert result.unverified_quotes
    assert result.is_clean is False


def test_a_quote_from_an_uncited_item_is_a_provenance_note_not_an_alarm() -> None:
    """The answer quoted E1's wording while citing E2. Reported, but not as fabrication.

    Both findings used to land in ``unverified_quotes``, and collapsing them was a real
    cost: the service's caveat told the reader the answer contained Sanskrit absent from
    the evidence, when the wording was genuine, retrieved, and sitting in the packet
    under a different id. Observed live -- the model quoted *devam ṛtvijam* from RV 1.1.1
    while citing the formula-family and parallel items instead of the passage. The split
    keeps "possibly invented" separate from "right words, wrong id".
    """
    result = audit(
        "The verse reads yajñasya devam ṛtvijam [E2].",
        packet(item("E1", sanskrit=SANSKRIT), item("E2", sanskrit="agnim dutam vrnimahe")),
    )

    assert result.uncited_quotes, "the quote must still be detected and reported"
    assert not result.unverified_quotes, "it is in the packet, so not possibly fabricated"
    assert result.is_clean, "wrong id beside real wording is not grounds to distrust"


def test_sanskrit_absent_from_the_whole_packet_is_an_alarm() -> None:
    """The serious half of the split: nothing retrieved contains this wording."""
    result = audit(
        "The verse reads somaṣya pavitram asti [E1].",
        packet(item("E1", sanskrit=SANSKRIT)),
    )

    assert result.unverified_quotes
    assert not result.uncited_quotes
    assert result.is_clean is False


# ---------------------------------------------------------------------------
# ASK_BL_07: the tokenizer's character class held only lowercase diacritics
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "word",
    [
        "Āraṇyaka",
        "Ṛgvedic",
        "Śaunaka",
        "Ṣaḍja",
        "Ūrdhva",
        "Ṇakāra",
    ],
)
def test_a_capitalised_diacritic_does_not_split_the_word(word: str) -> None:
    """The word a reader wrote must be reported whole, or not reported at all.

    With a lowercase-only class, matching could not begin at the capital, so it began at
    the next letter: ``Āraṇyaka`` came back as ``raṇyaka``. That fragment is then named
    verbatim in a user-facing caveat, telling a reader their citation is suspect and
    quoting a word they never wrote.
    """
    runs = _sanskrit_runs(f"the {word} tradition")
    assert runs == [word], f"expected the whole word, got {runs}"


@pytest.mark.parametrize("word", ["Ṛgvedic", "Śaunaka", "Ṭīkā"])
def test_a_word_whose_only_diacritic_is_capitalised_is_still_audited(word: str) -> None:
    """The silent half, and the worse one.

    ``Śaunaka`` carries exactly one diacritic and it is the capital. Excluding capitals
    left nothing in the word to match, so the auditor did not skip a *character* -- it
    skipped the word, and reported no run at all. A quote auditor that silently declines
    to audit is worse than none, because its silence reads as a pass.
    """
    assert _sanskrit_runs(f"quoted from the {word} recension") == [word]


def test_the_diacritic_class_covers_both_cases() -> None:
    """Derived, not typed twice. A hand-written second list is how this drifted."""
    for lower in "āīūṛṝḷḹṅñṇṃṁṭḍḥśṣēōç":
        assert lower in _IAST_MARKS
        assert lower.upper() in _IAST_MARKS


def test_plain_english_still_yields_no_run() -> None:
    """Widening the class must not start matching English, which would flag every answer."""
    assert _sanskrit_runs("The hymn is addressed to Agni and Indra by the seer") == []
    assert _sanskrit_runs("A plain English sentence about ritual and fire") == []


def test_a_capitalised_quote_verifies_against_its_cited_item() -> None:
    """End to end: the fix must make a real quotation pass, not merely tokenize better."""
    cited = [item("E1", sanskrit="āraṇyaka kāṇḍa")]
    assert verify_quotes("The Āraṇyaka kāṇḍa is cited here [E1].", cited) == []
