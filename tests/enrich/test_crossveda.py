"""Tests for cross-Veda parallel discovery.

Two layers, on purpose.

The synthetic layer builds :class:`TextSurfaces` by hand so that a test can say exactly
which comparison level two texts agree on. That is the only way to test the
identity/variant split honestly: with real corpus text you can assert that a pair comes
back ``VARIANT_OF``, but you cannot assert *why*, and a classifier that got the right
answer for the wrong reason would pass.

The corpus layer runs the real thing over all four Vedas and pins the numbers. It is slow
-- about fifteen seconds including the corpus read -- and every test in it is named and
grouped so that a slow run is never a mystery. It is not marked ``skip``: an enrichment
stage whose corpus-level behaviour is only ever checked by hand is an enrichment stage
that silently regresses.
"""

from __future__ import annotations

import pathlib
import random
from collections import Counter
from difflib import SequenceMatcher

import orjson
import pytest

from vedagraph.enrich.corpus import Corpus, MantraRecord, load_corpus
from vedagraph.enrich.crossveda import (
    MIN_LENGTH_RATIO_FOR_FLOOR,
    MIN_NGRAM_JACCARD_FOR_FLOOR,
    NGRAM_WEIGHT,
    PairScores,
    character_ngrams,
    discover_cross_veda_parallels,
    identity_predicate,
    jaccard,
    lcs_length,
    length_ratio,
    score_pair,
)
from vedagraph.enrich.guards import (
    MAX_NEAR_PARALLELS_PER_MANTRA,
    NEAR_PARALLEL_FLOOR,
)
from vedagraph.enrich.predicates import TextualPredicate
from vedagraph.enrich.provenance import AssertionState, TrustClass
from vedagraph.enrich.records import ParallelRow
from vedagraph.enrich.surfaces import (
    DEVANAGARI,
    LATIN,
    MatchLevel,
    TextSurfaces,
)

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Synthetic fixtures
# ---------------------------------------------------------------------------


def make_surfaces(
    key: str,
    veda: str,
    script: str,
    folded: str,
    *,
    source: str | None = None,
    accentless: str | None = None,
) -> TextSurfaces:
    """Build one mantra's surfaces directly, so a test controls every match level.

    ``build_surfaces`` derives all six surfaces from one source string, which is right for
    production and useless for a classification test: there is no source string that
    produces "identical at SANDHI_INSENSITIVE and different at SCRIPT_FOLDED" on demand.
    """
    text = folded if source is None else source
    return TextSurfaces(
        passage_key=key,
        veda=veda,
        script=script,
        source=text,
        unicode_normalized=text,
        punctuation_normalized=text,
        accent_insensitive=text if accentless is None else accentless,
        script_folded=folded,
        sandhi_insensitive="".join(folded.split()),
    )


def make_mantra(
    key: str,
    veda: str,
    script: str,
    folded: str,
    *,
    source: str | None = None,
    accentless: str | None = None,
) -> MantraRecord:
    return MantraRecord(
        passage_key=key,
        passage_id=key.lower(),
        veda=veda,
        citation=key,
        surfaces=make_surfaces(key, veda, script, folded, source=source, accentless=accentless),
    )


def make_corpus(*mantras: MantraRecord) -> Corpus:
    ordered = tuple(sorted(mantras, key=lambda mantra: mantra.passage_key))
    return Corpus(mantras=ordered, by_key={mantra.passage_key: mantra for mantra in ordered})


#: A Rigvedic verse long enough to clear ``MIN_COMPARABLE_LENGTH``, spaced by word.
RV_TEXT = "agnim ile purohitam yajnasya devam rtvijam hotaram ratnadhatamam"
#: The same verse as an edition that writes continuous sandhi would print it.
SANDHI_TEXT = "agnimilepurohitam yajnasyadevam rtvijamhotaram ratnadhatamam"


def rows_by_predicate(rows: list[ParallelRow]) -> Counter[str]:
    return Counter(row.predicate for row in rows)


def serialize(rows: list[ParallelRow]) -> bytes:
    """The artifact the loader would read. Byte equality of this is the determinism claim."""
    return orjson.dumps([row.as_row() for row in rows], option=orjson.OPT_SORT_KEYS)


def find_row(rows: list[ParallelRow], left: str, right: str, predicate: str) -> ParallelRow | None:
    for row in rows:
        if row.predicate == predicate and {row.subject_key, row.object_key} == {left, right}:
            return row
    return None


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------


def reference_lcs(left: str, right: str) -> int:
    """The textbook dynamic program, kept only so the bit-parallel version can be checked."""
    if len(left) < len(right):
        left, right = right, left
    previous = [0] * (len(right) + 1)
    for character in left:
        current = [0]
        for index, other in enumerate(right):
            if character == other:
                current.append(previous[index] + 1)
            else:
                current.append(max(current[index], previous[index + 1]))
        previous = current
    return previous[-1]


def test_lcs_length_agrees_with_the_dynamic_program() -> None:
    """The bit-vector formulation is unreadable; this is what makes it trustworthy."""
    rng = random.Random(20250909)
    alphabet = "aiuekmnrtsvdgpyh"
    for _ in range(300):
        left = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 60)))
        right = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 60)))
        assert lcs_length(left, right) == reference_lcs(left, right), (left, right)


def test_lcs_length_handles_empty_and_identical_inputs() -> None:
    assert lcs_length("", "") == 0
    assert lcs_length("agni", "") == 0
    assert lcs_length("", "agni") == 0
    assert lcs_length(RV_TEXT, RV_TEXT) == len(RV_TEXT)


def test_character_ngrams_are_overlapping_and_short_text_survives() -> None:
    assert character_ngrams("agnim", 4) == frozenset({"agni", "gnim"})
    # Shorter than the window: yields itself rather than nothing, so it stays comparable.
    assert character_ngrams("ag", 4) == frozenset({"ag"})
    assert character_ngrams("", 4) == frozenset()


def test_jaccard_and_length_ratio_edges() -> None:
    assert jaccard(frozenset(), frozenset()) == 1.0
    assert jaccard(frozenset({"a"}), frozenset()) == 0.0
    assert jaccard(frozenset({"a", "b"}), frozenset({"b", "c"})) == pytest.approx(1 / 3)
    assert length_ratio("", "") == 0.0
    assert length_ratio("abcd", "ab") == 0.5


def test_edit_ratio_disables_autojunk_because_sanskrit_vowels_are_popular() -> None:
    """The reason ``score_pair`` passes ``autojunk=False``, pinned as a measurement.

    ``difflib`` treats any element occurring in more than 1% of a sequence longer than 200
    elements as junk. Over characters that is every vowel, and the result is not a small
    distortion: two 600-character strings that differ in 6% of their positions score 0.0
    with the default and 0.94 without it.
    """
    rng = random.Random(1)
    alphabet = "aiuekmnrtsvdgpyhb"
    left = "".join(rng.choice(alphabet) for _ in range(600))
    mutated = list(left)
    for index in range(0, len(mutated), 17):
        mutated[index] = rng.choice(alphabet)
    right = "".join(mutated)

    assert SequenceMatcher(None, left, right).ratio() < 0.1
    scores = score_pair(
        make_surfaces("A", "RV", LATIN, left),
        make_surfaces("B", "AV", LATIN, right),
    )
    assert scores.edit_ratio > 0.9


def test_similarity_ignores_word_division_and_so_does_not_lose_the_samaveda() -> None:
    """The single most important scoring property, stated as a test rather than a comment.

    The two texts are the same verse; one edition spaces it by word and the other writes
    continuous sandhi. Token overlap collapses. A similarity that leaned on tokens would
    call this pair unrelated, and RV/SV is the largest body of real cross-Veda reuse in
    the corpus.
    """
    scores = score_pair(
        make_surfaces("RV", "RV", LATIN, RV_TEXT),
        make_surfaces("SV", "SV", DEVANAGARI, SANDHI_TEXT, source="devanagari-source"),
    )
    assert scores.token_jaccard < 0.2
    assert scores.ngram_jaccard == 1.0
    assert scores.lcs_ratio == 1.0
    assert scores.similarity == 1.0


def test_prefilter_bounds_are_the_arithmetic_they_claim_to_be() -> None:
    """Both prunes must be lossless, so they are derived from the blend, not chosen.

    A pair sitting exactly on either bound with a perfect complementary signal lands
    exactly on the floor, which is what "cannot possibly reach the floor below this"
    means.
    """
    assert MIN_NGRAM_JACCARD_FOR_FLOOR == pytest.approx(0.44)
    assert MIN_LENGTH_RATIO_FOR_FLOOR == pytest.approx(0.44)
    on_the_bound = NGRAM_WEIGHT * MIN_NGRAM_JACCARD_FOR_FLOOR + (1 - NGRAM_WEIGHT) * 1.0
    assert on_the_bound == pytest.approx(NEAR_PARALLEL_FLOOR)


def test_identity_predicate_separates_variants_from_exact_parallels() -> None:
    assert identity_predicate(MatchLevel.SANDHI_INSENSITIVE) is TextualPredicate.VARIANT_OF
    for level in MatchLevel:
        if level is MatchLevel.SANDHI_INSENSITIVE:
            continue
        assert identity_predicate(level) is TextualPredicate.EXACT_PARALLEL_OF


def test_pair_scores_strength_uses_the_shared_threshold() -> None:
    weak = PairScores(0.0, 0.8, 0.8, 0.8, 0.80)
    strong = PairScores(0.0, 0.9, 0.9, 0.9, 0.90)
    assert not weak.is_strong
    assert strong.is_strong


# ---------------------------------------------------------------------------
# Classification over a synthetic corpus
# ---------------------------------------------------------------------------


def test_cross_script_identity_is_exact_not_variant() -> None:
    """Same letters, same word division, different scripts: the strongest level possible."""
    corpus = make_corpus(
        make_mantra("K1:RV", "RV", LATIN, RV_TEXT),
        make_mantra("K2:SV", "SV", DEVANAGARI, RV_TEXT, source="devanagari-source"),
    )
    rows, report = discover_cross_veda_parallels(corpus)

    row = find_row(rows, "K1:RV", "K2:SV", str(TextualPredicate.EXACT_PARALLEL_OF))
    assert row is not None
    assert row.match_level == str(MatchLevel.SCRIPT_FOLDED)
    assert row.levels_reached == (
        str(MatchLevel.SCRIPT_FOLDED),
        str(MatchLevel.SANDHI_INSENSITIVE),
    )
    assert row.similarity == 1.0
    assert report.notes["identity_pairs_by_level"][str(MatchLevel.SOURCE_EXACT)] == 0


def test_differing_word_division_is_a_variant_not_an_exact_parallel() -> None:
    """The distinction the brief calls out: same verse, different editorial word-splitting."""
    corpus = make_corpus(
        make_mantra("K1:RV", "RV", LATIN, RV_TEXT),
        make_mantra("K2:SV", "SV", DEVANAGARI, SANDHI_TEXT, source="devanagari-source"),
    )
    rows, _ = discover_cross_veda_parallels(corpus)

    assert rows_by_predicate(rows)[str(TextualPredicate.EXACT_PARALLEL_OF)] == 0
    row = find_row(rows, "K1:RV", "K2:SV", str(TextualPredicate.VARIANT_OF))
    assert row is not None
    assert row.match_level == str(MatchLevel.SANDHI_INSENSITIVE)
    assert row.token_jaccard < 1.0


def test_same_veda_repetition_is_not_a_cross_veda_parallel() -> None:
    """Within-Veda repetition belongs to vedagraph.lexical.parallels, not to this stage."""
    corpus = make_corpus(
        make_mantra("K1:RV", "RV", LATIN, RV_TEXT),
        make_mantra("K2:RV", "RV", LATIN, RV_TEXT),
    )
    rows, _ = discover_cross_veda_parallels(corpus)
    assert rows == []


def test_texts_below_the_comparable_length_are_excluded_and_counted() -> None:
    corpus = make_corpus(
        make_mantra("K1:RV", "RV", LATIN, "agnim ile"),
        make_mantra("K2:AV", "AV", LATIN, "agnim ile"),
    )
    rows, report = discover_cross_veda_parallels(corpus)
    assert rows == []
    assert report.rejected["below_min_comparable_length"] == 2


def test_a_near_parallel_above_the_floor_is_emitted_with_its_metrics() -> None:
    altered = RV_TEXT.replace("hotaram", "hotharam").replace("devam", "devim")
    corpus = make_corpus(
        make_mantra("K1:RV", "RV", LATIN, RV_TEXT),
        make_mantra("K2:AV", "AV", LATIN, altered),
    )
    rows, _ = discover_cross_veda_parallels(corpus)

    row = find_row(rows, "K1:RV", "K2:AV", str(TextualPredicate.NEAR_PARALLEL_OF))
    assert row is not None
    assert NEAR_PARALLEL_FLOOR <= row.similarity < 1.0
    # A near parallel is identical at no level at all, so it claims none. match_level is an
    # identity claim, not a record of which surface the pair was scored on -- naming a level
    # here read as "these two texts are identical at SANDHI_INSENSITIVE" on 4,229 of 6,271
    # published rows, which is precisely what a near parallel is not.
    assert row.match_level == ""
    assert row.levels_reached == ()
    assert 0.0 < row.lcs_ratio < 1.0
    assert 0.0 < row.edit_ratio < 1.0


def test_a_scored_pair_below_the_floor_is_discarded_and_counted() -> None:
    """Rejection has to be *recorded*, not just silent, or a cut is invisible in review.

    The second text keeps the first half of the verse and replaces the second, which is
    similar enough that banding proposes the pair and far enough away that the blend
    lands at 0.63 against a floor of 0.72. That is the interesting case: a pair the stage
    looked at and turned down.
    """
    partial = "agnim ile purohitam yajnasya devam rtvijam somam pavate vasuni"
    left = make_mantra("K1:RV", "RV", LATIN, RV_TEXT)
    right = make_mantra("K2:AV", "AV", LATIN, partial)
    assert score_pair(left.surfaces, right.surfaces).similarity < NEAR_PARALLEL_FLOOR

    rows, report = discover_cross_veda_parallels(make_corpus(left, right))
    assert rows == []
    assert report.notes["candidate_pairs"] == 1
    assert report.rejected["below_near_parallel_floor"] == 1


def test_an_unrelated_pair_is_never_even_proposed() -> None:
    """Candidate generation, not the floor, is what keeps the quadratic blow-up away.

    Two verses sharing only Vedic register have a 4-gram Jaccard around 0.006 on this
    corpus, so no band agrees and the pair costs nothing at all. If this ever starts
    proposing a candidate, the banding has loosened and the scoring stage is about to get
    much more expensive.
    """
    unrelated = "indram vardhanto apturah krnvanto visvam aryam apaghnanto aravnah"
    rows, report = discover_cross_veda_parallels(
        make_corpus(
            make_mantra("K1:RV", "RV", LATIN, RV_TEXT),
            make_mantra("K2:AV", "AV", LATIN, unrelated),
        )
    )
    assert rows == []
    assert report.notes["candidate_pairs"] == 0


def test_near_parallels_are_capped_per_mantra_per_veda_and_the_cap_is_reported() -> None:
    """Seven candidates, five kept, two counted. The cap is a bound, not a suggestion."""
    mantras = [make_mantra("K0:RV", "RV", LATIN, RV_TEXT)]
    for index in range(7):
        variant = RV_TEXT.replace("ratnadhatamam", f"ratnadhatama{index}x")
        mantras.append(make_mantra(f"K{index + 1}:AV", "AV", LATIN, variant))
    rows, report = discover_cross_veda_parallels(make_corpus(*mantras))

    near = [row for row in rows if row.predicate == str(TextualPredicate.NEAR_PARALLEL_OF)]
    assert len(near) == MAX_NEAR_PARALLELS_PER_MANTRA
    assert report.capped["near_parallels_per_mantra"] == 7 - MAX_NEAR_PARALLELS_PER_MANTRA


def test_reuse_is_directed_from_the_samaveda_and_only_there() -> None:
    """Direction is asserted only where the corpus's own structure establishes it."""
    corpus = make_corpus(
        make_mantra("K1:RV", "RV", LATIN, RV_TEXT),
        make_mantra("K2:SV", "SV", DEVANAGARI, RV_TEXT, source="devanagari-source"),
        make_mantra("K3:AV", "AV", LATIN, RV_TEXT),
    )
    rows, _ = discover_cross_veda_parallels(corpus)

    reuse = [row for row in rows if row.predicate == str(TextualPredicate.REUSES_TEXT_FROM)]
    assert len(reuse) == 1
    assert reuse[0].subject_key == "K2:SV"
    assert reuse[0].subject_veda == "SV"
    assert reuse[0].object_key == "K1:RV"
    # The symmetric row survives alongside it: they say different things.
    assert find_row(rows, "K1:RV", "K2:SV", str(TextualPredicate.EXACT_PARALLEL_OF)) is not None
    # RV/AV and SV/AV have no established direction and must stay undirected.
    assert {row.veda_pair for row in reuse} == {"RV-SV"}


def test_every_row_carries_a_deterministic_accepted_provenance_with_two_sided_evidence() -> None:
    corpus = make_corpus(
        make_mantra("K1:RV", "RV", LATIN, RV_TEXT),
        make_mantra("K2:SV", "SV", DEVANAGARI, SANDHI_TEXT, source="devanagari-source"),
    )
    rows, report = discover_cross_veda_parallels(corpus)
    assert rows

    for row in rows:
        provenance = row.provenance
        assert provenance.trust is TrustClass.DETERMINISTIC_DERIVED
        assert provenance.state is AssertionState.ACCEPTED
        assert provenance.model == ""
        assert provenance.method.startswith("crossveda-parallels:")
        assert provenance.run_id == report.notes["run_id"]
        assert provenance.score == pytest.approx(row.similarity)
        assert len(provenance.evidence) == 2
        assert [span.locator for span in provenance.evidence] == [row.subject_key, row.object_key]
        assert {span.surface for span in provenance.evidence} == {row.match_level}
        assert all(span.quote for span in provenance.evidence)


def test_each_unordered_pair_is_emitted_once_per_predicate() -> None:
    corpus = make_corpus(
        make_mantra("K1:RV", "RV", LATIN, RV_TEXT),
        make_mantra("K2:SV", "SV", DEVANAGARI, RV_TEXT, source="devanagari-source"),
        make_mantra("K3:AV", "AV", LATIN, RV_TEXT),
        make_mantra("K4:YV", "YV", DEVANAGARI, RV_TEXT, source="other-devanagari-source"),
    )
    rows, _ = discover_cross_veda_parallels(corpus)

    seen = Counter((row.predicate, frozenset({row.subject_key, row.object_key})) for row in rows)
    assert set(seen.values()) == {1}
    # Four mantras, four Vedas, all identical: six unordered pairs plus the one SV->RV
    # borrowing.
    assert len(rows) == 7


def test_the_synthetic_run_is_byte_identical_when_repeated() -> None:
    corpus = make_corpus(
        make_mantra("K1:RV", "RV", LATIN, RV_TEXT),
        make_mantra("K2:SV", "SV", DEVANAGARI, SANDHI_TEXT, source="devanagari-source"),
        make_mantra("K3:AV", "AV", LATIN, RV_TEXT.replace("hotaram", "hotharam")),
    )
    first, _ = discover_cross_veda_parallels(corpus)
    second, _ = discover_cross_veda_parallels(corpus)
    assert serialize(first) == serialize(second)


# ---------------------------------------------------------------------------
# The real corpus. Slow: roughly fifteen seconds including the read.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def corpus() -> Corpus:
    if not (PROJECT_ROOT / "data" / "canonical").is_dir():
        pytest.skip("canonical corpora are not present in this checkout")
    return load_corpus(PROJECT_ROOT)


@pytest.fixture(scope="module")
def discovered(corpus: Corpus) -> list[ParallelRow]:
    rows, _ = discover_cross_veda_parallels(corpus)
    return rows


class TestFullCorpusSlow:
    """Full-corpus tests. Slow by design and deliberately not skipped.

    Everything in this class runs the real discovery over all 20,210 mantras. The whole
    class shares one module-scoped run, so the cost is paid once.
    """

    def test_slow_known_true_positive_rv_1_90_6_and_vsm_13_27(
        self, corpus: Corpus, discovered: list[ParallelRow]
    ) -> None:
        """``madhu vata rtayate``, the Rigveda's honey verse, reappearing in the Yajurveda.

        Reported as ``VARIANT_OF``, not ``EXACT_PARALLEL_OF``, and that is the correct
        answer rather than a near miss: the Rigveda prints ``madhvir nah santv osadhih``
        and the Vajasaneyi Samhita prints ``madhvirnah santvosadhih``. The two editions
        agree on every letter and disagree on where the words end, which is exactly what
        ``VARIANT_OF`` is for. Both predicates are identities and both carry similarity
        1.0; the pair being absent, or coming back as a near parallel, is the regression
        this test is watching for.
        """
        keys = {mantra.citation: mantra.passage_key for mantra in corpus.mantras}
        left, right = keys["RV 1.90.6"], keys["VSM 13.27"]

        identities = [
            row
            for row in discovered
            if {row.subject_key, row.object_key} == {left, right}
            and row.predicate
            in {str(TextualPredicate.EXACT_PARALLEL_OF), str(TextualPredicate.VARIANT_OF)}
        ]
        assert len(identities) == 1
        row = identities[0]
        assert row.predicate == str(TextualPredicate.VARIANT_OF)
        assert row.match_level == str(MatchLevel.SANDHI_INSENSITIVE)
        assert row.similarity == 1.0
        assert row.veda_pair == "RV-YV"
        assert row.ngram_jaccard == 1.0
        # The word-division difference is visible in the one metric that can see it.
        assert row.token_jaccard < 1.0

    def test_slow_known_true_positive_rv_10_162_6_and_avs_20_96_16(
        self, corpus: Corpus, discovered: list[ParallelRow]
    ) -> None:
        """A same-script identity, which is the case that must come back ``EXACT``."""
        keys = {mantra.citation: mantra.passage_key for mantra in corpus.mantras}
        row = find_row(
            discovered,
            keys["RV 10.162.6"],
            keys["AVS 20.96.16"],
            str(TextualPredicate.EXACT_PARALLEL_OF),
        )
        assert row is not None
        assert row.match_level == str(MatchLevel.SCRIPT_FOLDED)
        assert row.token_jaccard == 1.0
        assert row.veda_pair == "AV-RV"

    def test_slow_identical_pair_count_is_in_the_measured_range(
        self, discovered: list[ParallelRow]
    ) -> None:
        """Identity is the load-bearing half of this stage, so its total is pinned.

        1,538 as measured: 750 ``EXACT_PARALLEL_OF`` and 788 ``VARIANT_OF``. The range is
        wide enough to survive a corpus revision and narrow enough that losing the
        Yajurveda, or double-counting a level, fails here rather than in review.

        This number was 1,404 until ``surfaces.build_surfaces`` was corrected to fold
        Devanagari source conventions *before* transliterating. The accented Vajasaneyi
        layer types visarga as an ASCII colon, and transliterating first let that colon be
        deleted as punctuation instead of folded to a visarga -- so a colon-visarga mantra
        and a real-visarga mantra were unequal on the only surfaces a cross-script pair can
        be compared on. The 134 recovered pairs are almost all Yajurveda; the lower bound
        here is deliberately above 1,450 so that regression cannot pass silently.
        """
        counts = rows_by_predicate(discovered)
        identities = (
            counts[str(TextualPredicate.EXACT_PARALLEL_OF)]
            + counts[str(TextualPredicate.VARIANT_OF)]
        )
        assert 1470 <= identities <= 1620
        assert counts[str(TextualPredicate.EXACT_PARALLEL_OF)] > 0
        assert counts[str(TextualPredicate.VARIANT_OF)] > 0

    def test_slow_every_veda_pair_is_represented(self, discovered: list[ParallelRow]) -> None:
        """All six cells of the matrix, because an empty cell has always meant a bug here.

        The Yajurveda in particular reads as "has no parallels" whenever its non-standard
        ``text_role`` is mishandled upstream, and that failure is silent everywhere else.
        """
        pairs = {row.veda_pair for row in discovered}
        assert pairs == {"AV-RV", "AV-SV", "AV-YV", "RV-SV", "RV-YV", "SV-YV"}

    def test_slow_cross_script_rows_never_claim_a_level_below_script_folded(
        self, corpus: Corpus, discovered: list[ParallelRow]
    ) -> None:
        """Latin and Devanagari share no code points, so any such claim is a fabrication."""
        script = {mantra.passage_key: mantra.surfaces.script for mantra in corpus.mantras}
        forbidden = {
            str(MatchLevel.SOURCE_EXACT),
            str(MatchLevel.UNICODE_NORMALIZED),
            str(MatchLevel.PUNCTUATION_NORMALIZED),
            str(MatchLevel.ACCENT_INSENSITIVE),
        }
        offenders = [
            row
            for row in discovered
            if script[row.subject_key] != script[row.object_key]
            and (row.match_level in forbidden or forbidden & set(row.levels_reached))
        ]
        assert offenders == []

    def test_slow_only_the_permitted_predicates_are_written(
        self, discovered: list[ParallelRow]
    ) -> None:
        """``SHARES_FORMULA_WITH`` belongs to the formula layer and is never emitted here."""
        assert {row.predicate for row in discovered} <= {
            str(TextualPredicate.EXACT_PARALLEL_OF),
            str(TextualPredicate.NEAR_PARALLEL_OF),
            str(TextualPredicate.VARIANT_OF),
            str(TextualPredicate.REUSES_TEXT_FROM),
        }
        assert str(TextualPredicate.SHARES_FORMULA_WITH) not in {
            row.predicate for row in discovered
        }

    def test_slow_directed_reuse_only_ever_points_from_the_samaveda_to_the_rigveda(
        self, discovered: list[ParallelRow]
    ) -> None:
        reuse = [
            row for row in discovered if row.predicate == str(TextualPredicate.REUSES_TEXT_FROM)
        ]
        assert reuse
        assert {(row.subject_veda, row.object_veda) for row in reuse} == {("SV", "RV")}

    def test_slow_no_row_relates_a_mantra_to_itself_or_to_its_own_veda(
        self, discovered: list[ParallelRow]
    ) -> None:
        assert all(row.subject_key != row.object_key for row in discovered)
        assert all(row.subject_veda != row.object_veda for row in discovered)

    def test_slow_the_full_run_is_byte_identical_when_repeated(self, corpus: Corpus) -> None:
        """Determinism over the real corpus, which is where set iteration order would leak."""
        first, first_report = discover_cross_veda_parallels(corpus)
        second, second_report = discover_cross_veda_parallels(corpus)
        assert serialize(first) == serialize(second)
        assert first_report.notes["run_id"] == second_report.notes["run_id"]

    def test_slow_the_report_accounts_for_what_was_dropped(self, corpus: Corpus) -> None:
        """A stage that only reports its output cannot be told from one that capped itself."""
        rows, report = discover_cross_veda_parallels(corpus)
        assert report.stage == "crossveda-parallels"
        assert report.produced == len(rows)
        assert report.rejected["below_min_comparable_length"] > 0
        assert report.rejected["candidate_already_identical"] > 0
        assert report.notes["candidate_pairs"] > 0
        assert report.notes["largest_lsh_bucket"] > 0
        assert report.notes["near_parallel_edge_ceiling_hit"] is False
        assert report.notes["timings"]["total_seconds"] < 600
