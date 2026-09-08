"""Adversarial tests for span-to-token alignment and confidence propagation.

Every case here is a failure mode the old positional map ``span[i] ->
token[i]`` handled silently and wrongly. Each asserts two things, because
either alone is insufficient: the alignment the model chose, and the
confidence state a mark riding on that alignment ends up with. An alignment
that is right but reports the wrong confidence is as dangerous as one that is
wrong, since the whole point of the state model is to decide what ships
without human review.

Synthetic geometry follows the 1856 fount as measured on the calibration
lines: an aksara is about 100 px of rule, a word gap 35-55 px, a danda 16 px,
a double danda 39 px. Spans are (x0, x1) and widths are x1 - x0.
"""

from __future__ import annotations

from typing import ClassVar

import pytest

from vedagraph.ingest.av_accent_binder import (
    AUTO_PROMOTE,
    aksara_clusters,
    bind_line_detailed,
)
from vedagraph.ingest.av_alignment import (
    SAFE_ALIGNMENT_STATES,
    UNRESOLVED_ALIGNMENT_STATES,
    align_line,
    cluster_demand,
    token_demand,
)

AKSARA = 100
GAP = 40


def clusters_of(skeleton: str) -> list[list[str]]:
    return [aksara_clusters(t) for t in skeleton.split()]


def lay_out(skeleton: str, gap: int = GAP) -> list[tuple[int, int]]:
    """One span per token, each as wide as the token's expected demand."""
    spans: list[tuple[int, int]] = []
    x = 0
    for token in skeleton.split():
        width = token_demand(aksara_clusters(token))
        spans.append((x, x + width))
        x += width + gap
    return spans


def states(skeleton: str, spans: list[tuple[int, int]]) -> list[str]:
    return [t.state for t in align_line(spans, clusters_of(skeleton)).tokens]


def mark_at(center: float, kind: str = "anudatta", width: int = 38) -> dict:
    half = width // 2
    return {"type": kind, "x0": int(center - half), "x1": int(center + half)}


# ---------------------------------------------------------------------------
# A. exact 1:1 spans and tokens
# ---------------------------------------------------------------------------


class TestCaseAExactOneToOne:
    SKELETON = "कवि सोम अग्नये"

    def test_every_token_takes_its_own_span(self) -> None:
        spans = lay_out(self.SKELETON)
        alignment = align_line(spans, clusters_of(self.SKELETON))
        assert [t.span_indices for t in alignment.tokens] == [(0,), (1,), (2,)]

    def test_all_tokens_are_safe_and_line_passes_the_guard(self) -> None:
        spans = lay_out(self.SKELETON)
        alignment = align_line(spans, clusters_of(self.SKELETON))
        assert all(t.state in SAFE_ALIGNMENT_STATES for t in alignment.tokens)
        assert alignment.unresolved_ops == 0
        assert alignment.line_safe
        assert alignment.safe_token_fraction == 1.0

    def test_a_mark_in_the_middle_token_is_promotable(self) -> None:
        spans = lay_out(self.SKELETON)
        # सोम is span 1; its second aksara cell is the right half of it.
        x0, x1 = spans[1]
        bindings, alignment = bind_line_detailed(
            [mark_at((x0 + x1) / 2 + 40)], self.SKELETON, spans
        )
        assert alignment is not None and alignment.line_safe
        assert bindings[0].word_token == "सोम"
        assert bindings[0].state in AUTO_PROMOTE


# ---------------------------------------------------------------------------
# B. one free-standing visarga span inserted
# ---------------------------------------------------------------------------


class TestCaseBFreeStandingVisarga:
    """The defect that produced 0.1818 akṣara accuracy on c411/l09.

    This fount sets the visarga dot-pair clear of the sirorekha, so it forms
    a rule span of its own with no whitespace token behind it. Under the
    positional map it consumed a token slot and shifted every later carrier.
    """

    SKELETON = "कवि मतयः सोम"

    def spans(self) -> list[tuple[int, int]]:
        return [
            (0, 200),  # कवि, 2 aksaras
            (240, 460),  # मतयः minus its visarga
            (480, 500),  # the detached visarga dot-pair: 20 px, no token
            (545, 745),  # सोम, 2 aksaras
        ]

    def test_visarga_span_merges_into_its_owning_word(self) -> None:
        alignment = align_line(self.spans(), clusters_of(self.SKELETON))
        assert [t.span_indices for t in alignment.tokens] == [(0,), (1, 2), (3,)]

    def test_the_merge_is_many_to_one_and_stays_safe(self) -> None:
        alignment = align_line(self.spans(), clusters_of(self.SKELETON))
        assert alignment.tokens[1].state == "ALIGN_MANY_TO_ONE"
        assert alignment.tokens[1].state in SAFE_ALIGNMENT_STATES
        assert alignment.many_to_one_ops == 1
        assert alignment.unaligned_spans == ()
        assert alignment.line_safe

    def test_no_later_carrier_is_shifted(self) -> None:
        spans = self.spans()
        bindings, _ = bind_line_detailed([mark_at(700)], self.SKELETON, spans)
        # Positionally, span 3 is the fourth span and there is no fourth
        # token; the old map bound this mark to nothing or to the wrong word.
        assert bindings[0].word_token == "सोम"
        assert bindings[0].token_offset == 2
        assert bindings[0].state in AUTO_PROMOTE

    def test_a_mark_on_the_visarga_word_binds_to_that_word(self) -> None:
        bindings, _ = bind_line_detailed([mark_at(280)], self.SKELETON, self.spans())
        assert bindings[0].word_token == "मतयः"
        assert bindings[0].alignment_state == "ALIGN_MANY_TO_ONE"
        assert bindings[0].state in AUTO_PROMOTE


# ---------------------------------------------------------------------------
# C. one image span missing
# ---------------------------------------------------------------------------


class TestCaseCImageSpanMissing:
    """A token the image shows no rule span for.

    At word scale the model does not commit to *which* defect this is, and
    that is the honest reading: "the word printed no sirorekha" and "the
    neighbouring rule bridged the gap" are both near-impossible in this
    fount, and their costs sit within a few tens of units of each other. It
    resolves the geometry as one-to-many rather than a gap, and either way
    the line fails the guard and nothing on it may be promoted — which is
    the property that matters.
    """

    SKELETON = "कवि सोम अग्नये"

    def spans(self) -> list[tuple[int, int]]:
        full = lay_out(self.SKELETON)
        return [full[0], full[2]]  # the middle word printed no rule at all

    def test_the_missing_token_is_never_confidently_aligned(self) -> None:
        alignment = align_line(self.spans(), clusters_of(self.SKELETON))
        assert alignment.tokens[1].state not in SAFE_ALIGNMENT_STATES

    def test_the_line_fails_the_alignment_guard(self) -> None:
        alignment = align_line(self.spans(), clusters_of(self.SKELETON))
        assert alignment.safe_token_fraction < 0.8
        assert not alignment.line_safe

    def test_gap_in_image_is_reachable_when_no_span_can_reach(self) -> None:
        """More tokens than any legal split of the spans can cover."""
        skeleton = "कवि सोम अग्नये तानि वाचो"
        alignment = align_line([(0, 200)], clusters_of(skeleton))
        gaps = [t for t in alignment.tokens if t.state == "ALIGN_GAP_IMAGE"]
        assert gaps, "ALIGN_GAP_IMAGE must be producible"
        assert all(t.span_indices == () for t in gaps)
        assert not alignment.line_safe

    def test_no_mark_on_that_line_is_promotable(self) -> None:
        spans = self.spans()
        bindings, alignment = bind_line_detailed([mark_at(50)], self.SKELETON, spans)
        assert alignment is not None and not alignment.line_safe
        # The mark's own cell placement is fine; the line is not.
        assert bindings[0].cell_state in AUTO_PROMOTE
        assert bindings[0].state == "LINE_ALIGNMENT_UNSAFE"
        assert bindings[0].state not in AUTO_PROMOTE


# ---------------------------------------------------------------------------
# D. one text token missing
# ---------------------------------------------------------------------------


class TestCaseDTextTokenMissing:
    """The image shows a whole word the transcription does not account for.

    This case caught a real defect. Dropping the spare 200 px span cost 2900
    while swallowing it into the following token cost 2790, so the model
    absorbed an entire extra word, declared the line safe, and promoted a
    mark sitting on ink the skeleton never mentioned. The merge-fit condition
    now judges whether a merged extent actually fits its token, separately
    from what the merge costs.
    """

    SKELETON = "कवि अग्नये"

    def spans(self) -> list[tuple[int, int]]:
        return [(0, 200), (240, 440), (480, 780)]

    def test_the_extra_span_is_reported_rather_than_absorbed(self) -> None:
        alignment = align_line(self.spans(), clusters_of(self.SKELETON))
        assert alignment.unresolved_ops >= 1
        assert not alignment.line_safe

    def test_absorption_is_not_reported_as_a_clean_merge(self) -> None:
        alignment = align_line(self.spans(), clusters_of(self.SKELETON))
        absorbed = [t for t in alignment.tokens if len(t.span_indices) > 1]
        assert absorbed, "expected the model to reach for a merge here"
        for t in absorbed:
            # Here the merge and the gap are a dead heat, so the margin test
            # catches it first; the merge-fit test below covers the case where
            # the merge wins outright and only its fit gives it away.
            assert t.state == "ALIGN_AMBIGUOUS"

    def test_a_confidently_chosen_but_badly_fitting_merge_is_ambiguous(self) -> None:
        """A stray span pressed hard against its neighbour.

        Dropping a span costs a flat 900 on top of its width while merging it
        costs 150, so once the intervening gap is tight enough the merge wins
        by more than the safe margin and the margin test cannot see anything
        wrong. Only the fit gives it away: a whole extra word of ink has been
        folded into a two-akṣara token.
        """
        skeleton = "कवि सोम"
        spans = [(0, 200), (210, 410), (455, 655)]
        alignment = align_line(spans, clusters_of(skeleton))
        merged = [t for t in alignment.tokens if len(t.span_indices) > 1]
        assert merged, "expected the stray span to be merged, not dropped"
        for t in merged:
            assert t.margin >= 500, "margin alone would have called this safe"
            assert t.state == "ALIGN_AMBIGUOUS"
            assert "absorption" in t.note
        assert not alignment.line_safe

    def test_merge_fit_is_unverifiable_without_a_one_to_one_pair(self) -> None:
        """With no 1:1 match there is no measurement of the line's pitch."""
        alignment = align_line([(0, 200), (240, 440)], clusters_of("कवि"))
        merged = [t for t in alignment.tokens if len(t.span_indices) > 1]
        for t in merged:
            assert t.state == "ALIGN_AMBIGUOUS"

    def test_a_mark_over_unaccounted_ink_is_not_promotable(self) -> None:
        spans = self.spans()
        bindings, alignment = bind_line_detailed([mark_at(340)], self.SKELETON, spans)
        assert alignment is not None
        assert bindings[0].state not in AUTO_PROMOTE


# ---------------------------------------------------------------------------
# E. one visual word split into two spans (the cast rule broke)
# ---------------------------------------------------------------------------


class TestCaseERuleBrokeInsideAWord:
    SKELETON = "सध्रीचीर्विश्वा सोम"

    def spans(self) -> list[tuple[int, int]]:
        # 5 aksaras, but the rule broke after the second with a 22 px gap —
        # wider than the extractor's 14 px bridge, narrower than a word gap.
        return [(0, 200), (222, 500), (545, 745)]

    def test_the_two_fragments_rejoin_as_one_token(self) -> None:
        alignment = align_line(self.spans(), clusters_of(self.SKELETON))
        assert alignment.tokens[0].span_indices == (0, 1)
        assert alignment.tokens[0].state == "ALIGN_MANY_TO_ONE"
        assert alignment.tokens[1].span_indices == (2,)

    def test_a_mark_in_either_fragment_binds_to_the_whole_word(self) -> None:
        spans = self.spans()
        for center in (60, 350):
            bindings, alignment = bind_line_detailed([mark_at(center)], self.SKELETON, spans)
            assert alignment is not None and alignment.line_safe
            assert bindings[0].word_token == "सध्रीचीर्विश्वा"
            assert bindings[0].state in AUTO_PROMOTE

    def test_the_carrier_grid_spans_both_fragments(self) -> None:
        """A merged token's cells must be laid over the union, not one span."""
        spans = self.spans()
        bindings, _ = bind_line_detailed([mark_at(470)], self.SKELETON, spans)
        # 5 cells over x 0..500 puts 470 in the last cell. Laid over span 1
        # alone it would land in the middle of that fragment instead.
        assert bindings[0].aksara_index == 4


# ---------------------------------------------------------------------------
# F. two visual spans belonging to one token, and one span carrying two
# ---------------------------------------------------------------------------


class TestCaseFSpanTokenCardinality:
    def test_two_spans_one_token_is_many_to_one_and_safe(self) -> None:
        skeleton = "अनयन्वाचो सोम"
        spans = [(0, 240), (262, 500), (545, 745)]
        alignment = align_line(spans, clusters_of(skeleton))
        assert alignment.tokens[0].span_indices == (0, 1)
        assert alignment.tokens[0].state == "ALIGN_MANY_TO_ONE"
        assert alignment.line_safe

    def test_one_span_two_tokens_is_one_to_many(self) -> None:
        # The rule printed continuously across a word boundary, so the image
        # never showed where कवि ended and सोम began.
        skeleton = "कवि सोम अग्नये"
        spans = [(0, 400), (445, 745)]
        alignment = align_line(spans, clusters_of(skeleton))
        assert alignment.tokens[0].span_indices == (0,)
        assert alignment.tokens[1].span_indices == (0,)
        assert alignment.tokens[0].state == "ALIGN_ONE_TO_MANY"
        assert alignment.tokens[1].state == "ALIGN_ONE_TO_MANY"

    def test_one_to_many_is_never_a_safe_state(self) -> None:
        assert "ALIGN_ONE_TO_MANY" not in SAFE_ALIGNMENT_STATES

    def test_a_mark_inside_a_two_token_span_is_not_promotable(self) -> None:
        skeleton = "कवि सोम अग्नये"
        spans = [(0, 400), (445, 745)]
        bindings, alignment = bind_line_detailed([mark_at(200)], skeleton, spans)
        assert alignment is not None
        assert bindings[0].state not in AUTO_PROMOTE
        assert bindings[0].token_offset is None
        assert "never showed where one word ended" in bindings[0].note


# ---------------------------------------------------------------------------
# G. punctuation between tokens
# ---------------------------------------------------------------------------


class TestCaseGPunctuation:
    SKELETON = "शंस्या । इन्द्राय ॥ ६ ॥"

    def spans(self) -> list[tuple[int, int]]:
        return [
            (0, 200),  # शंस्या, 2 aksaras
            (241, 258),  # danda, 17 px
            (299, 570),  # इन्द्राय, 3 aksaras
            (632, 673),  # double danda, 41 px
            (698, 763),  # numeral, 65 px
            (789, 828),  # double danda, 39 px
        ]

    def test_punctuation_takes_its_own_span_one_to_one(self) -> None:
        alignment = align_line(self.spans(), clusters_of(self.SKELETON))
        assert [t.span_indices for t in alignment.tokens] == [(0,), (1,), (2,), (3,), (4,), (5,)]

    def test_the_punctuation_tail_is_not_reported_ambiguous(self) -> None:
        """A danda is 16 demand units against a +-20% width noise floor.

        With splits priced like merges the model preferred to carve a danda
        out of the double-danda span, and reported ALIGN_AMBIGUOUS across
        well-aligned tails on two of the five gold lines.
        """
        alignment = align_line(self.spans(), clusters_of(self.SKELETON))
        assert all(t.state not in UNRESOLVED_ALIGNMENT_STATES for t in alignment.tokens)
        assert alignment.line_safe

    def test_punctuation_demand_ranks_below_an_aksara(self) -> None:
        assert cluster_demand("।") < cluster_demand("॥") < cluster_demand("६")
        assert cluster_demand("६") < cluster_demand("क")

    def test_a_mark_before_the_danda_binds_to_the_word(self) -> None:
        bindings, _ = bind_line_detailed([mark_at(150, "svarita", 11)], self.SKELETON, self.spans())
        assert bindings[0].word_token == "शंस्या"
        assert bindings[0].state in AUTO_PROMOTE


# ---------------------------------------------------------------------------
# I. repeated identical Sanskrit tokens
# ---------------------------------------------------------------------------


class TestCaseIRepeatedTokens:
    """वा and ये each appear twice on c159/l02, in the same line.

    Identical tokens are the case where a content-based mapping would be
    tempted to pair on identity. The alignment is monotonic, so position
    alone must keep them apart.
    """

    SKELETON = "वा ये अनयन्वाचो वा ये तानि"

    def test_repeated_tokens_take_distinct_spans_in_order(self) -> None:
        spans = lay_out(self.SKELETON)
        alignment = align_line(spans, clusters_of(self.SKELETON))
        assert [t.span_indices for t in alignment.tokens] == [(0,), (1,), (2,), (3,), (4,), (5,)]
        assert alignment.line_safe

    def test_a_mark_on_the_second_copy_does_not_bind_to_the_first(self) -> None:
        spans = self.SKELETON and lay_out(self.SKELETON)
        x0, x1 = spans[3]  # the second वा
        bindings, _ = bind_line_detailed([mark_at((x0 + x1) / 2)], self.SKELETON, spans)
        assert bindings[0].token_offset == 3
        assert bindings[0].word_token == "वा"

    def test_alignment_stays_monotonic_across_repeats(self) -> None:
        spans = lay_out(self.SKELETON)
        alignment = align_line(spans, clusters_of(self.SKELETON))
        assigned = [t.span_indices for t in alignment.tokens if t.span_indices]
        flat = [s for group in assigned for s in group]
        assert flat == sorted(flat)


# ---------------------------------------------------------------------------
# J. the real c411/l09 shift, end to end against the scan
# ---------------------------------------------------------------------------


class TestCaseJRealLine411:
    """The verified silent high-confidence failure, from the actual scan.

    Before: auto_promote_frac 1.0, every mark BOUND_EXACT, akṣara accuracy
    0.1818. The two visarga spans are indices 4 (x1007-1027) and 6
    (x1399-1420) against neighbours of 223 and 296 px, so the artifact-ratio
    filter cannot reach them either.
    """

    SKELETON = "अच्छा म इन्द्रं मतयः स्वर्विदः सध्रीचीर्विश्वा उशतीरनूषत । ॥ १७ ॥"
    SPANS: ClassVar[list[tuple[int, int]]] = [
        (182, 406),
        (446, 529),
        (570, 727),
        (763, 986),
        (1007, 1027),
        (1083, 1379),
        (1399, 1420),
        (1471, 2032),
        (2072, 2597),
        (2649, 2666),
        (2933, 2973),
        (2998, 3121),
        (3147, 3183),
    ]

    def test_thirteen_spans_align_onto_eleven_tokens(self) -> None:
        alignment = align_line(self.SPANS, clusters_of(self.SKELETON))
        assert alignment.span_count == 13
        assert alignment.token_count == 11
        assert [t.span_indices for t in alignment.tokens] == [
            (0,),
            (1,),
            (2,),
            (3, 4),
            (5, 6),
            (7,),
            (8,),
            (9,),
            (10,),
            (11,),
            (12,),
        ]

    def test_both_visarga_spans_merge_left(self) -> None:
        alignment = align_line(self.SPANS, clusters_of(self.SKELETON))
        assert alignment.many_to_one_ops == 2
        assert alignment.tokens[3].state == "ALIGN_MANY_TO_ONE"
        assert alignment.tokens[4].state == "ALIGN_MANY_TO_ONE"

    def test_the_line_now_passes_the_alignment_guard(self) -> None:
        alignment = align_line(self.SPANS, clusters_of(self.SKELETON))
        assert alignment.unaligned_spans == ()
        assert alignment.unresolved_ops == 0
        assert alignment.safe_token_fraction == 1.0
        assert alignment.line_safe

    def test_every_alignment_choice_clears_the_safe_margin(self) -> None:
        alignment = align_line(self.SPANS, clusters_of(self.SKELETON))
        assert min(t.margin for t in alignment.tokens) >= 500

    @pytest.mark.parametrize(
        ("center", "token", "aksara"),
        [
            (327.0, "अच्छा", 1),
            (507.0, "म", 0),
            (820.5, "मतयः", 0),
            (963.5, "मतयः", 2),
            (1173.0, "स्वर्विदः", 0),
            (1357.5, "स्वर्विदः", 2),
            (1525.0, "सध्रीचीर्विश्वा", 0),
            (1715.0, "सध्रीचीर्विश्वा", 2),
            (1970.0, "सध्रीचीर्विश्वा", 4),
            (2211.0, "उशतीरनूषत", 1),
            (2365.5, "उशतीरनूषत", 3),
        ],
    )
    def test_each_detected_mark_reaches_the_gold_carrier(
        self, center: float, token: str, aksara: int
    ) -> None:
        """The eleven detected marks against the adjudicated T1/T2/T3 gold."""
        bindings, _ = bind_line_detailed([mark_at(center)], self.SKELETON, self.SPANS)
        assert bindings[0].word_token == token
        assert bindings[0].aksara_index == aksara


# ---------------------------------------------------------------------------
# Confidence propagation invariants
# ---------------------------------------------------------------------------


class TestConfidencePropagation:
    def test_auto_promotion_requires_a_safe_token_alignment(self) -> None:
        """ACCENT_AUTO_PROMOTION requires TOKEN_ALIGNMENT_SAFE."""
        skeleton = "कवि सोम अग्नये"
        spans = [(0, 400), (445, 745)]  # कवि and सोम share one span
        bindings, alignment = bind_line_detailed([mark_at(120), mark_at(600)], skeleton, spans)
        assert alignment is not None
        by_state = {b.state for b in bindings}
        assert "ALIGNMENT_UNSAFE" in by_state or "LINE_ALIGNMENT_UNSAFE" in by_state
        for b in bindings:
            if b.state in AUTO_PROMOTE:
                assert b.alignment_state in SAFE_ALIGNMENT_STATES

    def test_a_later_stage_cannot_outrank_an_unresolved_earlier_one(self) -> None:
        skeleton = "कवि सोम अग्नये"
        spans = [lay_out(skeleton)[0], lay_out(skeleton)[2]]
        bindings, _ = bind_line_detailed([mark_at(50)], skeleton, spans)
        b = bindings[0]
        # Cell placement is confident, the line is not, and the weaker wins.
        assert b.cell_state in AUTO_PROMOTE
        assert b.state not in AUTO_PROMOTE

    def test_a_healthy_line_leaves_cell_confidence_untouched(self) -> None:
        skeleton = "कवि सोम अग्नये"
        spans = lay_out(skeleton)
        bindings, alignment = bind_line_detailed([mark_at(50)], skeleton, spans)
        assert alignment is not None and alignment.line_safe
        assert bindings[0].state == bindings[0].cell_state

    def test_line_guard_overrides_a_perfect_promotion_rate(self) -> None:
        """A high per-mark promotion rate must not survive a bad line."""
        skeleton = "कवि सोम अग्नये"
        spans = [lay_out(skeleton)[0], lay_out(skeleton)[2]]
        marks = [mark_at(50), mark_at(150)]
        bindings, alignment = bind_line_detailed(marks, skeleton, spans)
        assert alignment is not None and not alignment.line_safe
        assert not any(b.state in AUTO_PROMOTE for b in bindings)


class TestAlignmentDeterminism:
    def test_repeated_alignment_is_identical(self) -> None:
        skeleton = TestCaseJRealLine411.SKELETON
        spans = TestCaseJRealLine411.SPANS
        first = align_line(spans, clusters_of(skeleton))
        for _ in range(4):
            again = align_line(spans, clusters_of(skeleton))
            assert again.tokens == first.tokens
            assert again.total_cost == first.total_cost
            assert again.scale == first.scale

    def test_empty_inputs_fail_closed(self) -> None:
        assert not align_line([], [["क"]]).line_safe
        assert not align_line([(0, 100)], []).line_safe

    def test_state_sets_are_disjoint(self) -> None:
        assert not (SAFE_ALIGNMENT_STATES & UNRESOLVED_ALIGNMENT_STATES)


class TestMarginZeroMeansATie:
    """A margin of zero means an exact tie, and nothing else.

    Reading a token as a gap is always itself a candidate assignment, so a
    token never lacks a rival and the margin is never undefined. That makes
    zero unambiguous — and it made the runner's old ``if t.margin`` filter
    exactly wrong, because the single worst case was the one value it
    dropped from the reported minimum.
    """

    def test_every_token_always_has_a_rival_assignment(self) -> None:
        for spans, skeleton in (
            ([(0, 200)], "कवि"),
            ([(0, 200), (240, 440)], "कवि सोम"),
            (TestCaseJRealLine411.SPANS, TestCaseJRealLine411.SKELETON),
        ):
            alignment = align_line(spans, clusters_of(skeleton))
            # No token reports the sentinel that would mean "no alternative".
            assert all(t.margin >= 0 for t in alignment.tokens)

    def test_a_healthy_line_has_margins_well_clear_of_the_threshold(self) -> None:
        skeleton = "कवि सोम अग्नये"
        alignment = align_line(lay_out(skeleton), clusters_of(skeleton))
        assert min(t.margin for t in alignment.tokens) >= 500
        assert alignment.line_safe

    def test_a_tie_reports_zero_and_is_ambiguous(self) -> None:
        alignment = align_line([(0, 200), (240, 440), (480, 780)], clusters_of("कवि अग्नये"))
        tied = [t for t in alignment.tokens if t.margin == 0]
        assert tied, "expected an exact tie in this configuration"
        assert all(t.state == "ALIGN_AMBIGUOUS" for t in tied)
        assert not alignment.line_safe

    def test_the_reported_minimum_must_not_filter_zeros(self) -> None:
        """The reporting rule itself, on a line that mixes a tie with a margin.

        A real line where one token ties and another does not is what the
        runner has to survive. The old expression, `min(m for m in margins if
        m)`, silently reported the second-worst token.
        """
        margins = [1500, 0, 1200]
        assert min(margins) == 0
        assert min((m for m in margins if m), default=0) == 1200

    def test_a_tie_is_visible_in_the_line_guard_regardless(self) -> None:
        """Defence in depth: the guard does not rely on the reported minimum."""
        alignment = align_line([(0, 200), (240, 440), (480, 780)], clusters_of("कवि अग्नये"))
        assert min(t.margin for t in alignment.tokens) == 0
        assert alignment.unresolved_ops > 0
        assert not alignment.line_safe


class TestEdgeToleranceWeakening:
    """A mark reached only by the span-edge tolerance is weaker evidence.

    The weakening was gated on ``cell_state == "BOUND_EXACT"`` and so never
    fired for a single-aksara token, because _aksara_cell returns
    BOUND_UNAMBIGUOUS when n == 1. Single-aksara tokens are common here, so a
    mark up to SPAN_EDGE_TOLERANCE px outside every inked span was being
    auto-promoted with no note at all.
    """

    SPANS: ClassVar[list[tuple[int, int]]] = [(300, 340), (380, 580), (620, 920)]
    SKELETON = "ते सोम अग्नये"

    def test_a_mark_outside_the_span_on_a_one_aksara_token_is_demoted(self) -> None:
        bindings, alignment = bind_line_detailed(
            [mark_at(355, "svarita", 11)], self.SKELETON, self.SPANS
        )
        assert alignment is not None
        assert bindings[0].token_offset == 0
        assert bindings[0].cell_state == "MULTIPLE_CANDIDATES"
        assert bindings[0].state not in AUTO_PROMOTE

    def test_a_mark_inside_the_span_is_still_promotable(self) -> None:
        bindings, _ = bind_line_detailed([mark_at(320, "svarita", 11)], self.SKELETON, self.SPANS)
        assert bindings[0].cell_state == "BOUND_UNAMBIGUOUS"
        assert bindings[0].state in AUTO_PROMOTE

    def test_a_mark_beyond_the_tolerance_has_no_carrier_at_all(self) -> None:
        bindings, _ = bind_line_detailed([mark_at(200, "svarita", 11)], self.SKELETON, self.SPANS)
        assert bindings[0].state == "NO_VALID_CARRIER"


class TestDynamicProgrammingConsistency:
    """The reported margin is only meaningful if the two DP passes agree.

    A per-token margin is ``forward[i][j] + op_cost + backward[i2][j2] -
    best``. If the forward and backward recurrences disagreed anywhere, or if
    the reconstructed path were not the optimum they both found, every margin
    would be wrong and so would every ALIGN_AMBIGUOUS verdict — silently.
    """

    CASES: ClassVar[list[tuple[str, list[tuple[int, int]]]]] = [
        ("कवि सोम अग्नये", [(0, 200), (240, 440), (480, 780)]),
        ("कवि मतयः सोम", [(0, 200), (240, 460), (480, 500), (545, 745)]),
        ("कवि अग्नये", [(0, 200), (240, 440), (480, 780)]),
        ("कवि", [(0, 200), (240, 440), (480, 680), (720, 920)]),
        (TestCaseJRealLine411.SKELETON, TestCaseJRealLine411.SPANS),
    ]

    @pytest.mark.parametrize(("skeleton", "spans"), CASES)
    def test_forward_and_backward_optima_and_path_agree(
        self, skeleton: str, spans: list[tuple[int, int]]
    ) -> None:
        import vedagraph.ingest.av_alignment as module

        token_clusters = clusters_of(skeleton)
        n, m = len(spans), len(token_clusters)
        coarse = module._fit_scale(spans, token_clusters)
        first = module._Model(spans, token_clusters, coarse)
        _, _, first_path = module._solve(first, n, m)
        model = module._Model(
            spans,
            token_clusters,
            module._refine_scale(module._one_to_one_ratios(first, first_path), coarse),
        )
        forward, backward, path = module._solve(model, n, m)
        assert forward[n][m] == backward[0][0]
        assert sum(model.op_cost(*op) for op in path) == forward[n][m]

    @pytest.mark.parametrize(
        ("skeleton", "spans"),
        [
            *CASES,
            # One span carrying two tokens, so the union is not a partition.
            ("कवि सोम अग्नये", [(0, 400), (445, 745)]),
        ],
    )
    def test_every_span_and_token_is_accounted_for(
        self, skeleton: str, spans: list[tuple[int, int]]
    ) -> None:
        """No span or token may be silently dropped from the result.

        Spans are not partitioned — ALIGN_ONE_TO_MANY puts one span under two
        tokens — so this is a covering property, not a bijection.
        """
        token_clusters = clusters_of(skeleton)
        alignment = align_line(spans, token_clusters)
        covered = {si for t in alignment.tokens for si in t.span_indices}
        assert covered | set(alignment.unaligned_spans) == set(range(len(spans)))
        assert not covered & set(alignment.unaligned_spans)
        assert [t.token_index for t in alignment.tokens] == list(range(len(token_clusters)))


class TestGapInTextReachability:
    """ALIGN_GAP_TEXT is a span-level verdict, not a token-level one.

    A span the alignment cannot account for has no token to carry the state,
    so it is surfaced through ``unaligned_spans`` and counted in
    ``unresolved_ops`` instead. This is the reachability evidence for it.

    Note what is *not* asserted here. The binder has an ALIGN_GAP_TEXT branch
    for a mark sitting on such a span, and no input was found that reaches it:
    whenever spans go unaligned, either the coarse token/span count guard has
    already declared the line SOURCE_AMBIGUOUS or the line-level guard has
    already stripped promotability from every mark on it. The branch is
    defence in depth against a future loosening of those guards, and is
    documented as unexercised rather than claimed as tested.
    """

    def test_spans_beyond_the_merge_bound_are_reported_unaligned(self) -> None:
        # Six spans onto one token: a merge reaches at most three of them.
        spans = [
            (0, 200),
            (240, 440),
            (480, 680),
            (720, 920),
            (960, 1160),
            (1200, 1400),
        ]
        alignment = align_line(spans, clusters_of("कवि"))
        assert alignment.unaligned_spans == (0, 1, 2)
        assert alignment.unresolved_ops >= len(alignment.unaligned_spans)
        assert not alignment.line_safe

    def test_unaligned_spans_are_counted_as_unresolved(self) -> None:
        spans = [(0, 200), (240, 440), (480, 680), (720, 920)]
        alignment = align_line(spans, clusters_of("कवि"))
        assert alignment.unaligned_spans
        assert alignment.unresolved_ops > 0
        assert not alignment.line_safe

    def test_that_case_fails_closed_at_the_binder_too(self) -> None:
        spans = [
            (0, 200),
            (240, 440),
            (480, 680),
            (720, 920),
            (960, 1160),
            (1200, 1400),
        ]
        bindings, alignment = bind_line_detailed([mark_at(1300)], "कवि", spans)
        # The count guard fires first here, which is why the binder's own
        # ALIGN_GAP_TEXT branch is not the thing that catches this.
        assert alignment is None
        assert bindings[0].state == "SOURCE_AMBIGUOUS"
        assert bindings[0].state not in AUTO_PROMOTE
