"""Tests for the Formula discovery stage.

Two halves, and they check different things.

The synthetic half builds tiny corpora in which exactly one rule is in play, so a failure
names the rule that broke. Every synthetic corpus is padded with filler mantras whose
tokens are unique by construction, because ``MAX_FORMULA_CORPUS_SHARE`` is a *share*: a
three-mantra formula in a ten-mantra corpus is 30% of it and gets rejected as grammar, and
without the padding half of these tests would pass or fail for the wrong reason. The
padding tokens carry a two-letter tag rather than a numeric one because the comparison
surface deletes digits, which would fold every filler onto the same text.

The real-corpus half asserts only invariants and floors, never measured counts. Pinning
"4,891 formulas" here would turn every future corpus correction into a test failure that
says nothing; pinning "no emitted formula is a single word" catches the regression that
would actually matter.
"""

from __future__ import annotations

import pathlib

import orjson
import pytest

from vedagraph.enrich.corpus import Corpus, MantraRecord, load_corpus
from vedagraph.enrich.formulas import (
    OCCURRENCE_METHOD_SANDHI,
    OCCURRENCE_METHOD_WORD,
    discover_formulas,
)
from vedagraph.enrich.guards import (
    MAX_FORMULA_CORPUS_SHARE,
    MAX_FORMULA_WORDS,
    MIN_FORMULA_CHARS,
    MIN_FORMULA_OCCURRENCES,
    MIN_FORMULA_WORDS,
)
from vedagraph.enrich.provenance import AssertionState, TrustClass
from vedagraph.enrich.records import FormulaOccurrenceRow, FormulaRow
from vedagraph.enrich.surfaces import LATIN, build_surfaces

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: Padding size per Veda. Chosen from the share cap rather than by taste: a formula needs
#: at least ``MIN_FORMULA_OCCURRENCES`` mantras, and 3 / 0.08 is 37.5, so a Veda smaller
#: than 38 mantras cannot hold a legal formula at all.
FILLER = 50

_LETTERS = "abcdefghijklmnopqrstuvwxyz"

#: The private-use block the comparison surface parks its folding sentinels in. Nothing
#: readable may contain one.
_PRIVATE_USE = range(0xE000, 0xF900)


def _tag(ordinal: int) -> str:
    return _LETTERS[ordinal // 26] + _LETTERS[ordinal % 26]


def _filler(count: int) -> list[str]:
    """Mantras that cannot repeat anything, in each other or in the test phrases."""
    return [
        f"nasvara{_tag(i)} pravāha{_tag(i)} hutama{_tag(i)} sadhrī{_tag(i)}" for i in range(count)
    ]


def _corpus(blocks: dict[str, list[str]]) -> Corpus:
    mantras: list[MantraRecord] = []
    for veda, texts in sorted(blocks.items()):
        for ordinal, text in enumerate(texts):
            key = f"VG:{veda}:TEST:{ordinal:04d}"
            mantras.append(
                MantraRecord(
                    passage_key=key,
                    passage_id=key,
                    veda=veda,
                    citation=key,
                    surfaces=build_surfaces(key, veda, LATIN, text),
                )
            )
    mantras.sort(key=lambda mantra: mantra.passage_key)
    return Corpus(mantras=tuple(mantras), by_key={m.passage_key: m for m in mantras})


def _normalized(rows: list[FormulaRow]) -> set[str]:
    return {row.normalized for row in rows}


# ---------------------------------------------------------------------------
# Length, frequency and share rules
# ---------------------------------------------------------------------------


def test_a_repeated_single_word_is_not_a_formula() -> None:
    """A word repeated everywhere in different company is a lemma, not a formula."""
    corpus = _corpus(
        {
            "RV": _filler(FILLER)
            + [f"agnim hotāra{_tag(i)} vahni{_tag(i)}" for i in range(MIN_FORMULA_OCCURRENCES + 2)]
        }
    )
    rows, _, _ = discover_formulas(corpus)
    assert "agnim" not in _normalized(rows)
    assert all(row.word_count >= MIN_FORMULA_WORDS for row in rows)


def test_a_span_below_the_character_floor_is_rejected() -> None:
    """``somaḥ pavate`` folds to eleven characters and is one short of the floor."""
    corpus = _corpus(
        {
            "RV": _filler(FILLER)
            + ["somaḥ pavate " + _tag(i) + "ka" for i in range(3)]
            + ["somaḥ pavatai " + _tag(i) + "ma" for i in range(3)]
        }
    )
    rows, _, report = discover_formulas(corpus)
    assert report.rejected["candidate_below_char_floor"] >= 1
    assert "somaḥ pavate" not in _normalized(rows)
    assert "somaḥ pavatai" in _normalized(rows)
    assert all(len(row.normalized.replace(" ", "")) >= MIN_FORMULA_CHARS for row in rows)


def test_two_occurrences_are_a_coincidence_and_three_are_a_formula() -> None:
    corpus = _corpus(
        {
            "RV": _filler(FILLER)
            + ["indraṃ vardhantu twice " + _tag(i) for i in range(2)]
            + ["marutaḥ śarma yachata " + _tag(i) for i in range(3)]
        }
    )
    rows, _, report = discover_formulas(corpus)
    assert "indraṃ vardhantu" not in _normalized(rows)
    assert "marutaḥ śarma yachata" in _normalized(rows)
    assert report.rejected["below_occurrence_floor"] >= 1
    assert all(row.mantra_count >= MIN_FORMULA_OCCURRENCES for row in rows)


def test_the_corpus_share_cap_is_measured_per_veda() -> None:
    """A span common enough in *any one* Veda is that Veda's grammar and goes entirely.

    The phrase below is 3 of 53 Rigvedic mantras, well inside the cap, and 3 of 23
    Samavedic ones, well outside it. Rejecting only the Samavedic occurrences would leave
    a node whose ``veda_counts`` omitted the Veda where the span is commonest.
    """
    phrase = "marutaḥ śarma yachata"
    corpus = _corpus(
        {
            "RV": _filler(FILLER) + [f"{phrase} rv{_tag(i)}" for i in range(3)],
            "SV": _filler(20) + [f"{phrase} sv{_tag(i)}" for i in range(3)],
        }
    )
    rows, _, report = discover_formulas(corpus)
    assert phrase not in _normalized(rows)
    assert report.rejected["above_corpus_share"] >= 1

    roomy = _corpus(
        {
            "RV": _filler(FILLER) + [f"{phrase} rv{_tag(i)}" for i in range(3)],
            "SV": _filler(FILLER) + [f"{phrase} sv{_tag(i)}" for i in range(3)],
        }
    )
    rows, _, _ = discover_formulas(roomy)
    assert phrase in _normalized(rows)


# ---------------------------------------------------------------------------
# Maximality
# ---------------------------------------------------------------------------


def test_maximality_keeps_only_the_longest_span_of_one_phrase() -> None:
    """One phrase, one node -- not one node per sub-span that goes nowhere else."""
    corpus = _corpus(
        {"RV": _filler(FILLER) + [f"indraṃ vardhantu no giraḥ pada{_tag(i)}" for i in range(3)]}
    )
    rows, occurrences, report = discover_formulas(corpus)
    assert _normalized(rows) == {"indraṃ vardhantu no giraḥ"}
    assert report.rejected["subsumed_by_maximal_formula"] >= 2
    assert len(occurrences) == 3


def test_a_sub_span_used_more_widely_survives_maximality() -> None:
    """Identical occurrence sets are the whole test; a wider sub-span is its own fact.

    Padded to 96 rather than 56 mantras because the sub-span reaches six of them, and six
    of fifty-six is 10.7% -- the share cap would fire and the test would pass its first
    assertion for entirely the wrong reason.
    """
    corpus = _corpus(
        {
            "RV": _filler(90)
            + [f"indraṃ vardhantu no giraḥ pada{_tag(i)}" for i in range(3)]
            + [f"sutāsa{_tag(i)} vardhantu no giraḥ" for i in range(3)]
        }
    )
    rows, _, _ = discover_formulas(corpus)
    assert _normalized(rows) == {"indraṃ vardhantu no giraḥ", "vardhantu no giraḥ"}
    by_form = {row.normalized: row for row in rows}
    assert by_form["indraṃ vardhantu no giraḥ"].mantra_count == 3
    assert by_form["vardhantu no giraḥ"].mantra_count == 6


def test_an_eight_word_window_of_a_longer_repetition_is_not_a_formula() -> None:
    """Stopping the miner at the ceiling must not deliver the ceiling's worth of a verse.

    Same phrase twice: at eight words it is a formula, at nine the eight-word windows are
    windows and the whole thing belongs to the parallel layer instead.
    """
    eight = "agnim īḷe purohitaṃ yajñasya devam ṛtvijaṃ hotāraṃ ratnadhātamam"
    corpus = _corpus({"RV": _filler(FILLER) + [eight] * 3})
    rows, _, _ = discover_formulas(corpus)
    assert _normalized(rows) == {eight}
    assert rows[0].word_count == MAX_FORMULA_WORDS

    corpus = _corpus({"RV": _filler(FILLER) + [f"{eight} iti"] * 3})
    rows, _, report = discover_formulas(corpus)
    assert rows == []
    assert report.rejected["truncated_by_word_ceiling"] >= 1


# ---------------------------------------------------------------------------
# Caps
# ---------------------------------------------------------------------------


def _two_formula_corpus() -> Corpus:
    """A cross-Veda formula and a same-sized single-Veda one, so rank order is decidable."""
    return _corpus(
        {
            "RV": _filler(FILLER)
            + [f"indraṃ vardhantu no giraḥ rv{_tag(i)}" for i in range(2)]
            + [f"marutaḥ śarma yachata rv{_tag(i)}" for i in range(3)],
            "SV": _filler(FILLER) + [f"indraṃ vardhantu no giraḥ sv{_tag(i)}" for i in range(1)],
        }
    )


def test_the_node_cap_keeps_cross_veda_formulas_first(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("vedagraph.enrich.formulas.MAX_FORMULA_NODES", 1)
    rows, _, report = discover_formulas(_two_formula_corpus())
    assert _normalized(rows) == {"indraṃ vardhantu no giraḥ"}
    assert rows[0].cross_veda is True
    assert report.capped["formula_nodes"] == 1


def test_the_edge_cap_drops_whole_formulas(monkeypatch: pytest.MonkeyPatch) -> None:
    """A node whose ``mantra_count`` outran its edges would lie about its own occurrences."""
    monkeypatch.setattr("vedagraph.enrich.formulas.MAX_FORMULA_EDGES", 3)
    rows, occurrences, report = discover_formulas(_two_formula_corpus())
    assert _normalized(rows) == {"indraṃ vardhantu no giraḥ"}
    assert len(occurrences) == 3
    assert rows[0].mantra_count == len(occurrences)
    assert report.capped["formula_nodes_dropped_for_edge_cap"] == 1
    assert report.capped["occurrence_edges"] == 3


# ---------------------------------------------------------------------------
# The Samaveda problem
# ---------------------------------------------------------------------------


def test_a_formula_written_without_word_breaks_is_still_detected() -> None:
    """The whole reason detection runs on the sandhi-collapsed surface.

    The third witness writes the phrase joined to the word before it, exactly as the
    Samaveda does. A word-n-gram-only extractor scores this corpus at two occurrences,
    drops the formula under ``MIN_FORMULA_OCCURRENCES``, and reports nothing.
    """
    corpus = _corpus(
        {
            "RV": _filler(FILLER) + [f"somasya pibatu indraḥ rv{_tag(i)}" for i in range(2)],
            "SV": [*_filler(FILLER), "yaṃsomasya pibatu indraḥ"],
        }
    )
    rows, occurrences, _ = discover_formulas(corpus)
    assert _normalized(rows) == {"somasya pibatu indraḥ"}
    assert rows[0].cross_veda is True
    assert rows[0].veda_counts == {"RV": 2, "SV": 1}

    methods = {row.veda: row.provenance.method for row in occurrences}
    assert methods["RV"] == OCCURRENCE_METHOD_WORD
    assert methods["SV"] == OCCURRENCE_METHOD_SANDHI
    sv = next(row for row in occurrences if row.veda == "SV")
    assert sv.provenance.score < 1.0
    assert "somasya pibatu indraḥ" in sv.source_form


# ---------------------------------------------------------------------------
# Envelope and determinism
# ---------------------------------------------------------------------------


def _payload(rows: list[FormulaRow], occurrences: list[FormulaOccurrenceRow]) -> bytes:
    return orjson.dumps(
        {"f": [row.as_row() for row in rows], "o": [row.as_row() for row in occurrences]}
    )


def test_every_row_carries_a_complete_provenance_envelope() -> None:
    rows, occurrences, _ = discover_formulas(_two_formula_corpus())
    assert rows and occurrences
    for row in [*rows, *occurrences]:
        assert row.provenance.trust is TrustClass.DETERMINISTIC_DERIVED
        assert row.provenance.state is AssertionState.ACCEPTED
        assert row.provenance.model == ""
        assert 0.0 <= row.provenance.score <= 1.0
        assert row.provenance.evidence
        for span in row.provenance.evidence:
            assert span.locator.startswith("VG:")
            assert span.quote.strip()
    for row in rows:
        locators = {span.locator for span in row.provenance.evidence}
        assert locators <= {
            occurrence.passage_key
            for occurrence in occurrences
            if occurrence.formula_id == row.formula_id
        }


def test_two_runs_over_one_corpus_are_byte_identical() -> None:
    corpus = _two_formula_corpus()
    first = discover_formulas(corpus)
    second = discover_formulas(corpus)
    assert _payload(first[0], first[1]) == _payload(second[0], second[1])
    assert first[2].as_dict() == second[2].as_dict()


# ---------------------------------------------------------------------------
# The real corpus
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def real() -> tuple[Corpus, list[FormulaRow], list[FormulaOccurrenceRow]]:
    if not (PROJECT_ROOT / "data" / "canonical").is_dir():
        pytest.skip("canonical corpora are not present in this checkout")
    corpus = load_corpus(PROJECT_ROOT)
    rows, occurrences, _ = discover_formulas(corpus)
    return corpus, rows, occurrences


def test_real_corpus_finds_formulas_shared_between_vedas(
    real: tuple[Corpus, list[FormulaRow], list[FormulaOccurrenceRow]],
) -> None:
    """Cross-Veda reuse is the deliverable, and it must be queryable from the node."""
    _, rows, _ = real
    cross = [row for row in rows if row.cross_veda]
    assert len(cross) > 100
    assert all(len(row.vedas) > 1 for row in cross)
    assert all(row.veda_counts and set(row.vedas) == set(row.veda_counts) for row in rows)
    assert any(len(row.vedas) == 4 for row in cross)


def test_real_corpus_respects_every_guard(
    real: tuple[Corpus, list[FormulaRow], list[FormulaOccurrenceRow]],
) -> None:
    corpus, rows, occurrences = real
    totals = corpus.counts()
    assert rows
    for row in rows:
        assert MIN_FORMULA_WORDS <= row.word_count <= MAX_FORMULA_WORDS
        assert len(row.normalized.replace(" ", "")) >= MIN_FORMULA_CHARS
        assert row.mantra_count >= MIN_FORMULA_OCCURRENCES
        assert row.occurrence_count >= row.mantra_count
        for veda, count in row.veda_counts.items():
            assert count / totals[veda] <= MAX_FORMULA_CORPUS_SHARE
    edges_per_formula: dict[str, int] = {}
    for occurrence in occurrences:
        edges_per_formula[occurrence.formula_id] = (
            edges_per_formula.get(occurrence.formula_id, 0) + 1
        )
    assert edges_per_formula == {row.formula_id: row.mantra_count for row in rows}


def test_real_corpus_covers_the_samaveda(
    real: tuple[Corpus, list[FormulaRow], list[FormulaOccurrenceRow]],
) -> None:
    """The regression this whole module is shaped around.

    A word-n-gram-only extractor leaves the Samaveda nearly empty, and the failure is
    silent. The floors below sit far under the measured values -- 71.5% of Samavedic
    mantras carry a formula, and 584 of their 3,112 occurrences are found only on the
    sandhi-collapsed surface -- so this fails when the Samaveda path breaks, not when the
    corpus is corrected.
    """
    corpus, _, occurrences = real
    samavedic = [row for row in occurrences if row.veda == "SV"]
    covered = {row.passage_key for row in samavedic}
    assert len(covered) / corpus.counts()["SV"] > 0.25
    sandhi_only = [row for row in samavedic if row.provenance.method == OCCURRENCE_METHOD_SANDHI]
    assert len(sandhi_only) > 50


def test_real_corpus_display_strings_are_free_of_folding_sentinels(
    real: tuple[Corpus, list[FormulaRow], list[FormulaOccurrenceRow]],
) -> None:
    """``script_folded`` is a comparison surface; none of it may reach a graph property."""
    _, rows, occurrences = real
    for row in rows:
        for text in (row.normalized, row.display_form, *row.source_forms):
            assert not any(ord(char) in _PRIVATE_USE for char in text), text
    for occurrence in occurrences:
        assert not any(ord(char) in _PRIVATE_USE for char in occurrence.source_form)
