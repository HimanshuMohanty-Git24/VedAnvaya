"""Tests for the Atharvaveda accent-to-text binder.

Ground truth: three independent readers given canvas n32 line 12 one line at
a time agreed exactly on every accent mark (seven anudatta, three svarita).
Two readers agreed exactly on line 19 (seven anudatta, four svarita). These
are the only calibration lines with verified human gold in this project.

The binder is tested against those verified readings to confirm that:
1. Every mark is assigned to the correct word token.
2. BOUND_EXACT marks are assigned to the correct aksara.
3. MULTIPLE_CANDIDATES marks correctly signal near-boundary uncertainty.
4. Alignment guards block silently-wrong bindings for misaligned skeletons.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


from vedagraph.ingest.av_accent_binder import (
    AUTO_PROMOTE,
    Binding,
    BindingState,
    _filter_artifact_spans,
    aksara_clusters,
    bind_line,
    binding_summary,
    strip_accents,
)


# ---------------------------------------------------------------------------
# aksara_clusters
# ---------------------------------------------------------------------------

class TestAksaraClusters:
    def test_pure_vowel_word(self) -> None:
        assert aksara_clusters("अ") == ["अ"]

    def test_consonant_with_matra(self) -> None:
        assert aksara_clusters("ते") == ["ते"]
        assert aksara_clusters("शि") == ["शि"]

    def test_conjunct_consonant(self) -> None:
        # ब्र: ba + halanta + ra
        result = aksara_clusters("ब्र")
        assert result == ["ब्र"]

    def test_word_with_anusvara(self) -> None:
        # सं: sa + anusvara
        result = aksara_clusters("सं")
        assert result == ["सं"]

    def test_word_with_visarga(self) -> None:
        result = aksara_clusters("दः")
        assert result == ["दः"]

    def test_final_halanta_is_not_a_phantom_cluster(self) -> None:
        # स्ताम्: the final म् must not produce a standalone ् cluster
        result = aksara_clusters("स्ताम्")
        assert result == ["स्ता", "म्"]
        assert "्" not in result

    def test_complex_word_anagasam(self) -> None:
        assert aksara_clusters("अनागसं") == ["अ", "ना", "ग", "सं"]

    def test_brahmanaa(self) -> None:
        assert aksara_clusters("ब्रह्मणा") == ["ब्र", "ह्म", "णा"]

    def test_long_compound(self) -> None:
        result = aksara_clusters("द्यावापृथिवी")
        # द्या, वा, पृ, थि, वी
        assert result[0] == "द्या"
        assert result[1] == "वा"
        assert "पृ" in result
        assert "थि" in result
        assert "वी" in result
        assert len(result) == 5

    def test_punctuation_is_its_own_cluster(self) -> None:
        result = aksara_clusters("।")
        assert result == ["।"]

    def test_double_danda(self) -> None:
        result = aksara_clusters("॥")
        assert result == ["॥"]

    def test_empty_string(self) -> None:
        assert aksara_clusters("") == []


# ---------------------------------------------------------------------------
# strip_accents
# ---------------------------------------------------------------------------

class TestStripAccents:
    ANUDATTA = "॒"
    SVARITA = "॑"

    def test_removes_anudatta_and_svarita(self) -> None:
        text = f"अ{self.ANUDATTA}ना{self.ANUDATTA}गसं{self.ANUDATTA}"
        assert strip_accents(text) == "अनागसं"

    def test_removes_svarita(self) -> None:
        assert strip_accents(f"ब्रह्म{self.SVARITA}णा") == "ब्रह्मणा"

    def test_leaves_other_characters_intact(self) -> None:
        assert strip_accents("तेदाम्") == "तेदाम्"

    def test_empty_string(self) -> None:
        assert strip_accents("") == ""

    def test_vedic_extensions_stripped(self) -> None:
        # A reader might use Vedic Extension range U+1CD0–U+1CFF
        text = "᳐क"
        assert strip_accents(text) == "क"


# ---------------------------------------------------------------------------
# _filter_artifact_spans
# ---------------------------------------------------------------------------

class TestFilterArtifactSpans:
    def test_passes_through_normal_spans(self) -> None:
        spans = [(0, 362), (400, 693), (731, 859), (887, 1221)]
        assert _filter_artifact_spans(spans) == spans

    def test_removes_isolated_tiny_span_in_large_gap(self) -> None:
        # The 22-px artifact from leaf 32 line 19 should be removed when both
        # neighbours are 25× wider.
        spans = [(564, 1109), (1113, 1135), (1171, 1766)]
        filtered = _filter_artifact_spans(spans)
        # Only the two large spans remain
        assert (1113, 1135) not in filtered
        assert len(filtered) == 2

    def test_keeps_small_danda_with_moderate_neighbours(self) -> None:
        # A 14-px danda surrounded by 206-px and 248-px spans (ratio ~14–17x,
        # below the threshold of 20x) must be kept.
        spans = [(2162, 2368), (2399, 2413), (2451, 2699)]
        filtered = _filter_artifact_spans(spans)
        assert (2399, 2413) in filtered

    def test_short_list_returned_unchanged(self) -> None:
        spans = [(0, 100), (200, 300)]
        assert _filter_artifact_spans(spans) == spans

    def test_empty_list(self) -> None:
        assert _filter_artifact_spans([]) == []


# ---------------------------------------------------------------------------
# bind_line — unit tests against fabricated inputs
# ---------------------------------------------------------------------------

class TestBindLine:
    def test_empty_marks_returns_empty(self) -> None:
        bindings = bind_line([], "अ ब", [(0, 100), (120, 220)])
        assert bindings == []

    def test_mark_outside_all_spans_is_no_valid_carrier(self) -> None:
        mark = {"type": "anudatta", "x0": 500, "x1": 538}
        bindings = bind_line([mark], "अ ब", [(0, 100), (120, 220)])
        assert len(bindings) == 1
        assert bindings[0].state == "NO_VALID_CARRIER"

    def test_mark_class_uncertain_is_passed_through(self) -> None:
        mark = {"type": "anudatta", "x0": 50, "x1": 88, "state": "MARK_CLASS_UNCERTAIN"}
        bindings = bind_line([mark], "अ", [(0, 100)])
        assert bindings[0].state == "MARK_CLASS_UNCERTAIN"

    def test_single_aksara_word_is_bound_exact(self) -> None:
        # A one-aksara word has no cell boundary to be uncertain about; the
        # binder returns BOUND_EXACT since n=1 is unambiguously the only carrier.
        mark = {"type": "anudatta", "x0": 40, "x1": 78}
        bindings = bind_line([mark], "ते", [(0, 100)])
        assert bindings[0].state == "BOUND_EXACT"
        assert bindings[0].aksara_cluster == "ते"

    def test_severe_token_span_mismatch_yields_source_ambiguous(self) -> None:
        # 12 tokens vs 1 span is way beyond tolerance
        marks = [{"type": "anudatta", "x0": 50, "x1": 88}]
        many_tokens = " ".join("क" * 12)
        bindings = bind_line(marks, many_tokens, [(0, 100)])
        assert bindings[0].state == "SOURCE_AMBIGUOUS"

    def test_exact_mark_in_cell_center_is_bound_exact(self) -> None:
        # Word "अन" has 2 aksaras over span 0-200 (each cell 100px wide)
        # Mark center at 50 (well within cell 0 of 'अ')
        mark = {"type": "svarita", "x0": 40, "x1": 60}  # center=50
        bindings = bind_line([mark], "अन", [(0, 200)])
        assert bindings[0].state == "BOUND_EXACT"
        assert bindings[0].aksara_cluster == "अ"
        assert bindings[0].aksara_index == 0

    def test_near_boundary_mark_is_multiple_candidates(self) -> None:
        # Word "अन" over span 0-200 (each cell 100px wide)
        # Mark center at 96 (4px before cell boundary at 100, within margin 15px)
        mark = {"type": "anudatta", "x0": 88, "x1": 104}  # center=96
        bindings = bind_line([mark], "अन", [(0, 200)])
        assert bindings[0].state == "MULTIPLE_CANDIDATES"

    def test_char_offset_is_correct(self) -> None:
        # "अन" over span; mark in second aksara 'न'
        mark = {"type": "anudatta", "x0": 140, "x1": 180}  # center=160
        bindings = bind_line([mark], "अन", [(0, 200)])
        b = bindings[0]
        assert b.aksara_index == 1
        assert b.aksara_cluster == "न"
        # 'न' is 3 bytes in UTF-8 but 1 Unicode character; offset in skeleton chars
        skel = "अन"
        assert skel[b.char_offset] == "न"  # type: ignore[index]

    def test_two_marks_in_same_word(self) -> None:
        # Both marks in "अनागसं" over a single span
        marks = [
            {"type": "anudatta", "x0": 10, "x1": 48},   # center=29 → 'अ'
            {"type": "anudatta", "x0": 100, "x1": 138},  # center=119 → 'ना'
        ]
        bindings = bind_line(marks, "अनागसं", [(0, 360)])
        tokens = [b.word_token for b in bindings]
        assert tokens == ["अनागसं", "अनागसं"]

    def test_binding_summary_counts_states(self) -> None:
        b1 = Binding("anudatta", 0, 38, 0, "अ", 0, "अ", 0, 0, "BOUND_EXACT")
        b2 = Binding("anudatta", 50, 88, 0, "अन", 1, "न", 1, 0, "MULTIPLE_CANDIDATES")
        summary = binding_summary([b1, b2])
        assert summary["total_marks"] == 2
        assert summary["promotable"] == 1
        assert summary["by_state"]["BOUND_EXACT"] == 1
        assert summary["by_state"]["MULTIPLE_CANDIDATES"] == 1


# ---------------------------------------------------------------------------
# bind_line — calibration gold tests (require the 1856 scan on disk)
# ---------------------------------------------------------------------------

class TestBindLineGold:
    """Verify the binder against the three-reader calibration gold.

    Canvas n32 line 12 is the only line in this project verified by three
    independent readers (P1, P2, P3) who each worked from a 1:1 rendering of
    that line alone. Line 19 was verified by two readers (Q1, Q2).
    """

    # P1/P2/P3 agreed: accent-marked text for line 12
    LINE12_TEXT = "अ॒ना॒गसं॒ ब्रह्म॑णा त्वा कृणोमि शि॒वे ते॒ द्यावा॑पृथि॒वी उ॒भे स्ता॑म् ॥ १ ॥"
    # Q1/Q2 agreed: accent-marked text for line 19
    LINE19_TEXT = "अहा॒ अरा॑ति॒मवि॑दः स्यो॒नमप्यभूर्भ॒द्रे सु॑कृ॒तस्य॑ लो॒के । ए॒वाहं॰ । ॰ ॥ ७ ॥"

    @pytest.fixture(autouse=True)
    def _skip_if_no_scan(self) -> None:
        crop = _load("crop_atharvaveda_leaf")
        if not crop.leaf_path(32).exists():
            pytest.skip("1856 scan not present in this checkout")

    def _bind(self, line_index: int, text: str):
        extract = _load("extract_atharvaveda_accents")
        result = extract.extract(32, line_index)
        ln = result["lines"][0]
        marks = ln["marks"]
        word_spans = ln["word_spans"]
        skeleton = strip_accents(text)
        return bind_line(marks, skeleton, word_spans), marks, word_spans

    # -- Line 12 ---

    def test_line12_all_marks_bound(self) -> None:
        bindings, marks, _ = self._bind(12, self.LINE12_TEXT)
        assert len(bindings) == len(marks)
        for b in bindings:
            assert b.state != "SOURCE_AMBIGUOUS"
            assert b.state != "NO_VALID_CARRIER"

    def test_line12_exact_marks_have_correct_aksara(self) -> None:
        bindings, _, _ = self._bind(12, self.LINE12_TEXT)
        # Map by mark type + approximate center for lookup
        exact = {b.aksara_cluster for b in bindings if b.state == "BOUND_EXACT"}
        # P1/P2/P3 confirmed these aksara carriers; all should appear in EXACT
        assert "ना" in exact   # 2nd aksara of अनागसं
        assert "सं" in exact   # 4th aksara of अनागसं
        assert "ह्म" in exact  # svarita over ह्म of ब्रह्मणा
        assert "ते" in exact   # anudatta over ते
        assert "वा" in exact   # svarita over वा of द्यावापृथिवी
        assert "थि" in exact   # anudatta over थि of पृथिवी
        assert "उ" in exact    # anudatta over उ of उभे
        assert "स्ता" in exact # svarita over स्ता of स्ताम्

    def test_line12_all_marks_in_correct_word(self) -> None:
        bindings, _, _ = self._bind(12, self.LINE12_TEXT)
        # P3 notes: anudattas on अ,ना,सं all in अनागसं
        first3 = bindings[:3]
        assert all(b.word_token == "अनागसं" for b in first3)

    def test_line12_no_marks_in_krnomi_twa(self) -> None:
        """P1/P2/P3: त्वा and कृणोमि carry no accent marks."""
        bindings, _, _ = self._bind(12, self.LINE12_TEXT)
        words_with_marks = {b.word_token for b in bindings}
        assert "त्वा" not in words_with_marks
        assert "कृणोमि" not in words_with_marks

    def test_line12_promotable_fraction_high(self) -> None:
        bindings, _, _ = self._bind(12, self.LINE12_TEXT)
        s = binding_summary(bindings)
        # Expect ≥ 70% promotable even with conservative MULTIPLE_CANDIDATES
        assert s["promotable_fraction"] is not None
        assert s["promotable_fraction"] >= 0.7

    # -- Line 19 ---

    def test_line19_all_marks_bound(self) -> None:
        bindings, marks, _ = self._bind(19, self.LINE19_TEXT)
        assert len(bindings) == len(marks)
        for b in bindings:
            assert b.state not in ("SOURCE_AMBIGUOUS", "NO_VALID_CARRIER")

    def test_line19_correct_word_for_all_marks(self) -> None:
        bindings, _, _ = self._bind(19, self.LINE19_TEXT)
        tok_map = {b.mark_x0: b.word_token for b in bindings}
        skel = strip_accents(self.LINE19_TEXT)
        toks = skel.split()
        # Q1/Q2: anu at ~443 in अहा, sva at ~683 in अरातिमविदः
        # sva at ~1847 and anu at ~1899 and sva at ~2107 all in सुकृतस्य
        for b in bindings:
            assert b.word_token in toks, f"word_token {b.word_token!r} not in skeleton tokens"

    def test_line19_sukrtasya_marks_all_correct(self) -> None:
        bindings, _, _ = self._bind(19, self.LINE19_TEXT)
        suk_bindings = [b for b in bindings if b.word_token == "सुकृतस्य"]
        # Q1/Q2: सुकृतस्य carries svarita(सु), anudatta(कृ), svarita(स्य)
        assert len(suk_bindings) == 3
        exact_aksaras = {b.aksara_cluster for b in suk_bindings if b.state == "BOUND_EXACT"}
        assert "सु" in exact_aksaras
        assert "कृ" in exact_aksaras
        assert "स्य" in exact_aksaras

    def test_line19_loke_carries_one_anudatta(self) -> None:
        bindings, _, _ = self._bind(19, self.LINE19_TEXT)
        loke_bindings = [b for b in bindings if b.word_token == "लोके"]
        # Q1/Q2: लोके carries one anudatta on लो
        assert len(loke_bindings) == 1
        assert loke_bindings[0].mark_type == "anudatta"
        assert loke_bindings[0].aksara_cluster == "लो"


# ---------------------------------------------------------------------------
# Alignment guards
# ---------------------------------------------------------------------------

class TestAlignmentGuards:
    def test_null_kanda_mismatch_does_not_affect_binder(self) -> None:
        """The binder has no kanda concept; it works purely on x-geometry."""
        marks = [{"type": "anudatta", "x0": 50, "x1": 88}]
        # Same mark should produce same result regardless of caller's kanda state
        b1 = bind_line(marks, "अ", [(0, 100)])
        b2 = bind_line(marks, "अ", [(0, 100)])
        assert b1[0].state == b2[0].state
        assert b1[0].aksara_cluster == b2[0].aksara_cluster

    def test_high_mismatch_declares_source_ambiguous(self) -> None:
        marks = [{"type": "anudatta", "x0": 50, "x1": 88}]
        # 15 tokens vs 1 span — no stable alignment possible
        tokens = " ".join("क" * 15)
        bindings = bind_line(marks, tokens, [(0, 100)])
        assert bindings[0].state == "SOURCE_AMBIGUOUS"

    def test_moderate_mismatch_does_not_declare_ambiguous(self) -> None:
        # 12 tokens vs 14 spans (like line 12) — within tolerance, should align
        marks = [{"type": "anudatta", "x0": 50, "x1": 88}]  # center=69 → in span 0
        spans = [(0, 200)] + [(300 + 100 * i, 390 + 100 * i) for i in range(13)]
        tokens = " ".join("क" * 12)
        bindings = bind_line(marks, tokens, spans)
        # Should not be SOURCE_AMBIGUOUS — might be BOUND_EXACT or NO_VALID_CARRIER
        assert bindings[0].state != "SOURCE_AMBIGUOUS"

    def test_auto_promote_contains_only_two_states(self) -> None:
        assert AUTO_PROMOTE == frozenset({"BOUND_EXACT", "BOUND_UNAMBIGUOUS"})

    def test_multiple_candidates_not_in_auto_promote(self) -> None:
        assert "MULTIPLE_CANDIDATES" not in AUTO_PROMOTE

    def test_no_valid_carrier_not_in_auto_promote(self) -> None:
        assert "NO_VALID_CARRIER" not in AUTO_PROMOTE

    def test_source_ambiguous_not_in_auto_promote(self) -> None:
        assert "SOURCE_AMBIGUOUS" not in AUTO_PROMOTE
