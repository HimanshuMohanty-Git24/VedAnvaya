"""Tests for deterministic gold selection and non-positional gold matching.

Two defects are regression-tested here, both of which could decide a release
gate on their own:

  * gold marks were paired to bindings by list position, so one missed
    detection mis-scored every later mark on the line (c411/l09: eleven
    correctly bound marks reported as 0.2727 word accuracy);
  * the gold record was whichever file the filesystem listed first, which on
    c032/l19 flips the zero-tolerance source_ambiguous gate, and on c159/l02
    and c430/l05 selected the reading the adjudicator had overruled.
"""

from __future__ import annotations

import pathlib
from typing import ClassVar

import pytest

from vedagraph.ingest.av_accent_binder import Binding, bind_line_detailed
from vedagraph.ingest.av_gold import (
    ERROR_CATEGORIES,
    GoldMark,
    PredMark,
    line_exactness,
    load_gold_record,
    match_marks_to_gold,
    normalise_tokenisation,
    parse_gold_marks,
    predicted_marks,
    reassemble_accented_line,
    score_line,
)

REPO = pathlib.Path(__file__).resolve().parents[2]
AV_V2 = REPO / "data/transcriptions/atharvaveda_bsb_1856/v2"
PROBE_DIR = AV_V2 / "accent_probe"
ADJUDICATION_DIR = AV_V2 / "adjudication"

ANUDATTA = "॒"
SVARITA = "॑"


def _gold(*items: tuple[int, int, str, float]) -> list[GoldMark]:
    return [GoldMark(i, w, a, t, p) for i, (w, a, t, p) in enumerate(items)]


def _pred(*items: tuple[str, float]) -> list[PredMark]:
    return [PredMark(i, t, x) for i, (t, x) in enumerate(items)]


# ---------------------------------------------------------------------------
# Declared tokenisation normalisation
# ---------------------------------------------------------------------------


class TestNormaliseTokenisation:
    Q1 = "लो॒के । ए॒वाहं॰ । ॰ ॥ ७ ॥"
    Q2 = "लो॒के। ए॒वाहं॰।॰॥७॥"

    def test_the_two_c032_l19_readers_become_one_text(self) -> None:
        assert normalise_tokenisation(self.Q1) == normalise_tokenisation(self.Q2)

    def test_danda_and_double_danda_are_their_own_tokens(self) -> None:
        assert normalise_tokenisation("क।ख॥").split() == ["क", "।", "ख", "॥"]

    def test_a_digit_run_is_one_token(self) -> None:
        assert normalise_tokenisation("॥१७॥").split() == ["॥", "१७", "॥"]
        assert normalise_tokenisation("॥ १७ ॥").split() == ["॥", "१७", "॥"]

    def test_the_abbreviation_sign_stays_with_its_word(self) -> None:
        assert normalise_tokenisation("ए॒वाहं॰ ।").split() == ["ए॒वाहं॰", "।"]

    def test_accent_marks_are_never_split_off(self) -> None:
        assert normalise_tokenisation(f"लो{ANUDATTA}के") == f"लो{ANUDATTA}के"

    def test_normalisation_is_idempotent(self) -> None:
        once = normalise_tokenisation(self.Q2)
        assert normalise_tokenisation(once) == once

    def test_accent_token_indices_are_unchanged_by_spacing(self) -> None:
        """The convention must not move any accent's word index."""
        line = "अहा॒ अरा॑ति॒मवि॑दः स्यो॒नमप्यभूर्भ॒द्रे सु॑कृ॒तस्य॑ लो॒के । ए॒वाहं॰ । ॰ ॥ ७ ॥"
        marks = parse_gold_marks(normalise_tokenisation(line))
        assert [m.word_index for m in marks] == [0, 1, 1, 1, 2, 2, 3, 3, 3, 4, 6]


# ---------------------------------------------------------------------------
# §8 / §11-H: a missed detection must not cascade
# ---------------------------------------------------------------------------


class TestMissedDetectionDoesNotCascade:
    """H. one missed accent before multiple later accents.

    Gold: svarita, anudatta, svarita, anudatta, svarita, anudatta.
    Detected: everything but the third. Positional pairing scored the fourth
    detection against the third gold mark and so on down the line; a single
    miss produced one false negative *and* five mismatches.
    """

    GOLD = _gold(
        (0, 0, "svarita", 0.05),
        (1, 0, "anudatta", 0.20),
        (2, 0, "svarita", 0.35),
        (3, 0, "anudatta", 0.50),
        (4, 0, "svarita", 0.65),
        (5, 0, "anudatta", 0.80),
    )
    PRED = _pred(
        ("svarita", 0.05),
        ("anudatta", 0.20),
        ("anudatta", 0.50),
        ("svarita", 0.65),
        ("anudatta", 0.80),
    )

    def test_exactly_one_false_negative_and_no_false_positive(self) -> None:
        pairs, _, _ = match_marks_to_gold(self.PRED, self.GOLD)
        assert sum(1 for p in pairs if p.kind == "FALSE_NEGATIVE") == 1
        assert sum(1 for p in pairs if p.kind == "FALSE_POSITIVE") == 0

    def test_the_gap_lands_on_the_mark_that_was_actually_missed(self) -> None:
        pairs, _, _ = match_marks_to_gold(self.PRED, self.GOLD)
        missed = [p.gold_index for p in pairs if p.kind == "FALSE_NEGATIVE"]
        assert missed == [2]

    def test_every_other_mark_is_paired_with_its_own_gold(self) -> None:
        pairs, _, _ = match_marks_to_gold(self.PRED, self.GOLD)
        matched = {p.pred_index: p.gold_index for p in pairs if p.kind == "MATCH"}
        assert matched == {0: 0, 1: 1, 2: 3, 3: 4, 4: 5}

    def test_positional_pairing_would_have_been_wrong(self) -> None:
        """Guard the regression: position pairs 2->2, 3->3, 4->4."""
        pairs, _, _ = match_marks_to_gold(self.PRED, self.GOLD)
        matched = {p.pred_index: p.gold_index for p in pairs if p.kind == "MATCH"}
        assert matched[2] != 2
        assert matched[3] != 3
        assert matched[4] != 4

    def test_five_of_six_marks_are_recalled(self) -> None:
        pairs, _, _ = match_marks_to_gold(self.PRED, self.GOLD)
        assert sum(1 for p in pairs if p.kind == "MATCH") == 5

    def test_two_missed_detections_produce_two_false_negatives(self) -> None:
        pred = _pred(
            ("svarita", 0.05),
            ("anudatta", 0.50),
            ("svarita", 0.65),
            ("anudatta", 0.80),
        )
        pairs, _, _ = match_marks_to_gold(pred, self.GOLD)
        assert sum(1 for p in pairs if p.kind == "FALSE_NEGATIVE") == 2
        assert [p.gold_index for p in pairs if p.kind == "FALSE_NEGATIVE"] == [1, 2]


class TestMatcherBlindSpots:
    """The two holes adversarial review found in the correspondence.

    These are recorded as tests so the limitation is pinned rather than
    forgotten. Neither is live on the calibration set — the real c411/l09
    failure is a non-uniform shift and is *not* absorbed — but both mean
    ``matched`` is not a safe denominator on its own, which is why
    ``word_binding_acc_over_gold`` is reported beside it.
    """

    def test_a_far_displaced_mark_escapes_into_a_gap_pair(self) -> None:
        """Beyond 2*GAP_COST/POSITION_WEIGHT of line width, a mark drops out."""
        gold = _gold(
            (0, 0, "anudatta", 0.10),
            (1, 0, "anudatta", 0.35),
            (2, 0, "anudatta", 0.60),
            (3, 0, "anudatta", 0.85),
        )
        pred = _pred(
            ("anudatta", 0.10),
            ("anudatta", 0.35),
            ("anudatta", 0.60),
            ("anudatta", 0.02),
        )
        pairs, _, _ = match_marks_to_gold(pred, gold)
        kinds = [p.kind for p in pairs]
        assert "FALSE_NEGATIVE" in kinds
        assert "FALSE_POSITIVE" in kinds

    def test_a_uniform_one_word_shift_is_absorbed_by_the_matcher(self) -> None:
        """The structural blind spot, stated plainly.

        Every mark displaced by one word pitch, every binding off by one
        word: the alignment shifts wholesale for one flat gap charge and then
        scores each shifted binding against the gold on the shifted word, so
        the gated metric reads 1.0.
        """
        pitch = 0.18
        gold = _gold(*[(i, 0, "anudatta", 0.10 + i * pitch) for i in range(5)])
        pred = _pred(*[("anudatta", 0.10 + (i + 1) * pitch) for i in range(4)])
        bindings = [
            Binding(
                "anudatta",
                0,
                10,
                i + 1,
                "x",
                0,
                "x",
                0,
                i + 1,
                "BOUND_EXACT",
                alignment_state="ALIGN_EXACT",
            )
            for i in range(4)
        ]
        metrics = score_line(bindings, pred, gold, "ADJUDICATED", 0)
        assert metrics.word_binding_acc == 1.0, (
            "if this ever stops being 1.0 the blind spot has been closed and "
            "this test should be rewritten as a positive assertion"
        )
        # The stricter denominator sees the missing mark, but not the shift.
        assert metrics.word_binding_acc_over_gold == 0.8

    def test_the_stricter_denominator_does_catch_an_escaped_mark(self) -> None:
        gold = _gold((0, 0, "anudatta", 0.10), (1, 0, "anudatta", 0.90))
        pred = _pred(("anudatta", 0.10), ("anudatta", 0.12))
        bindings = [
            Binding(
                "anudatta",
                0,
                10,
                0,
                "क",
                0,
                "क",
                0,
                0,
                "BOUND_EXACT",
                alignment_state="ALIGN_EXACT",
            ),
            Binding(
                "anudatta",
                12,
                22,
                0,
                "क",
                0,
                "क",
                0,
                0,
                "BOUND_EXACT",
                alignment_state="ALIGN_EXACT",
            ),
        ]
        metrics = score_line(bindings, pred, gold, "ADJUDICATED", 0)
        assert metrics.word_binding_acc == 1.0
        assert metrics.word_binding_acc_over_gold == 0.5

    def test_a_confident_correspondence_reports_a_safe_margin(self) -> None:
        gold = _gold((0, 0, "anudatta", 0.10), (1, 0, "svarita", 0.80))
        pred = _pred(("anudatta", 0.10), ("svarita", 0.80))
        bindings = [
            Binding(
                "anudatta",
                0,
                10,
                0,
                "क",
                0,
                "क",
                0,
                0,
                "BOUND_EXACT",
                alignment_state="ALIGN_EXACT",
            ),
            Binding(
                "svarita",
                80,
                90,
                1,
                "ख",
                0,
                "ख",
                0,
                1,
                "BOUND_EXACT",
                alignment_state="ALIGN_EXACT",
            ),
        ]
        metrics = score_line(bindings, pred, gold, "ADJUDICATED", 0)
        assert metrics.match_margin_safe
        assert metrics.match_margin >= 300

    def test_a_single_unrivalled_pairing_is_not_called_uncertain(self) -> None:
        gold = _gold((0, 0, "anudatta", 0.5))
        pred = _pred(("anudatta", 0.5))
        bindings = [
            Binding(
                "anudatta",
                40,
                60,
                0,
                "क",
                0,
                "क",
                0,
                0,
                "BOUND_EXACT",
                alignment_state="ALIGN_EXACT",
            )
        ]
        metrics = score_line(bindings, pred, gold, "ADJUDICATED", 0)
        assert metrics.match_margin == 0
        assert metrics.match_margin_safe


class TestMatcherProperties:
    def test_a_class_swap_is_a_class_error_not_a_miss_plus_a_spurious_mark(
        self,
    ) -> None:
        gold = _gold((0, 0, "anudatta", 0.30))
        pred = _pred(("svarita", 0.30))
        pairs, _, _ = match_marks_to_gold(pred, gold)
        assert [p.kind for p in pairs] == ["MATCH"]

    def test_a_spurious_detection_far_from_any_gold_is_a_false_positive(
        self,
    ) -> None:
        gold = _gold((0, 0, "anudatta", 0.10))
        pred = _pred(("anudatta", 0.10), ("anudatta", 0.90))
        pairs, _, _ = match_marks_to_gold(pred, gold)
        assert sum(1 for p in pairs if p.kind == "FALSE_POSITIVE") == 1

    def test_correspondence_is_monotonic(self) -> None:
        gold = _gold(
            (0, 0, "anudatta", 0.1),
            (1, 0, "anudatta", 0.4),
            (2, 0, "anudatta", 0.7),
        )
        pred = _pred(("anudatta", 0.1), ("anudatta", 0.4), ("anudatta", 0.7))
        pairs, _, _ = match_marks_to_gold(pred, gold)
        indices = [p.gold_index for p in pairs if p.kind == "MATCH"]
        assert indices == sorted(i for i in indices if i is not None)

    def test_empty_inputs_are_handled(self) -> None:
        assert match_marks_to_gold([], [])[0] == []
        assert all(
            p.kind == "FALSE_NEGATIVE"
            for p in match_marks_to_gold([], _gold((0, 0, "anudatta", 0.5)))[0]
        )

    def test_the_matcher_never_sees_the_binding(self) -> None:
        """A wrongly bound mark must still be matched, and still counted.

        If correspondence consulted the binding, a badly bound mark could be
        dropped into a false-positive/false-negative pair, leaving word
        accuracy untouched. It must instead be matched and scored wrong.
        """
        gold = _gold((0, 0, "anudatta", 0.10), (1, 0, "anudatta", 0.60))
        pred = _pred(("anudatta", 0.10), ("anudatta", 0.60))
        bindings = [
            Binding(
                "anudatta",
                0,
                10,
                0,
                "क",
                0,
                "क",
                0,
                0,
                "BOUND_EXACT",
                alignment_state="ALIGN_EXACT",
            ),
            # Bound to the wrong word entirely.
            Binding(
                "anudatta",
                60,
                70,
                0,
                "क",
                0,
                "क",
                0,
                0,
                "BOUND_EXACT",
                alignment_state="ALIGN_EXACT",
            ),
        ]
        metrics = score_line(bindings, pred, gold, "ADJUDICATED", 0)
        assert metrics.matched == 2
        assert metrics.false_negatives == 0
        assert metrics.false_positives == 0
        assert metrics.word_correct == 1
        assert metrics.word_binding_acc == 0.5
        assert metrics.errors["TOKEN_ALIGNMENT_ERROR"] == 1


# ---------------------------------------------------------------------------
# Error decomposition
# ---------------------------------------------------------------------------


class TestErrorDecomposition:
    def test_a_carrier_error_is_not_reported_as_an_alignment_error(self) -> None:
        gold = _gold((0, 2, "anudatta", 0.50))
        pred = _pred(("anudatta", 0.50))
        bindings = [
            Binding(
                "anudatta",
                40,
                60,
                0,
                "कविता",
                1,
                "वि",
                0,
                0,
                "MULTIPLE_CANDIDATES",
                alignment_state="ALIGN_EXACT",
            )
        ]
        metrics = score_line(bindings, pred, gold, "ADJUDICATED", 0)
        assert metrics.errors["CARRIER_ASSIGNMENT_ERROR"] == 1
        assert metrics.errors["TOKEN_ALIGNMENT_ERROR"] == 0
        assert metrics.word_correct == 1
        assert metrics.aksara_correct == 0

    def test_a_missed_detection_is_a_detection_miss(self) -> None:
        metrics = score_line([], [], _gold((0, 0, "anudatta", 0.5)), "ADJUDICATED", 0)
        assert metrics.errors["DETECTION_MISS"] == 1

    def test_every_residual_lands_in_exactly_one_category(self) -> None:
        gold = _gold((0, 0, "anudatta", 0.1), (5, 0, "svarita", 0.9))
        pred = _pred(("anudatta", 0.1))
        bindings = [
            Binding(
                "anudatta",
                0,
                10,
                0,
                "क",
                0,
                "क",
                0,
                0,
                "BOUND_EXACT",
                alignment_state="ALIGN_EXACT",
            )
        ]
        metrics = score_line(bindings, pred, gold, "ADJUDICATED", 0)
        assert sum(metrics.errors.values()) == 1
        assert set(metrics.errors) == set(ERROR_CATEGORIES)

    def test_majority_gold_attributes_residuals_to_gold_ambiguity(self) -> None:
        gold = _gold((0, 2, "anudatta", 0.50))
        pred = _pred(("anudatta", 0.50))
        bindings = [
            Binding(
                "anudatta",
                40,
                60,
                0,
                "कविता",
                1,
                "वि",
                0,
                0,
                "MULTIPLE_CANDIDATES",
                alignment_state="ALIGN_EXACT",
            )
        ]
        metrics = score_line(bindings, pred, gold, "PROBE_MAJORITY", 0)
        # A wrong carrier on a majority-selected line is still the binder's
        # error. Attributing it to the readers laundered it: c032/l12 is
        # PROBE_MAJORITY over a verse numeral that carries no accent, so
        # every residual there would have been blamed on P2's dissent.
        assert metrics.errors["CARRIER_ASSIGNMENT_ERROR"] == 1
        assert metrics.errors["GOLD_AMBIGUITY"] == 0

    def test_a_class_only_error_is_still_classified(self) -> None:
        """Right word, right akṣara, wrong class — still an incorrect binding.

        This used to be skipped entirely: the loop returned early on
        `aksara_ok`, so an anudatta/svarita swap left class_accuracy below
        1.0 with nothing in the decomposition to account for it.
        """
        gold = _gold((0, 0, "anudatta", 0.50))
        pred = _pred(("svarita", 0.50))
        bindings = [
            Binding(
                "svarita",
                40,
                60,
                0,
                "क",
                0,
                "क",
                0,
                0,
                "BOUND_EXACT",
                alignment_state="ALIGN_EXACT",
            )
        ]
        metrics = score_line(bindings, pred, gold, "PROBE_MAJORITY", 0)
        assert metrics.class_correct == 0
        assert metrics.class_accuracy == 0.0
        assert sum(metrics.errors.values()) == 1
        assert metrics.errors["OTHER"] == 1
        assert metrics.errors["CARRIER_ASSIGNMENT_ERROR"] == 0

    def test_gold_ambiguity_is_declared_unreachable(self) -> None:
        """Documented, not quietly left looking exercised.

        The only signal available is that the gold came from a strict
        majority, and using that alone attributed binder errors to the
        readers. Firing it properly needs the dissenting reader's own text
        re-parsed against the mark in question.
        """
        gold = _gold((0, 2, "anudatta", 0.50))
        pred = _pred(("anudatta", 0.50))
        bindings = [
            Binding(
                "anudatta",
                40,
                60,
                0,
                "कविता",
                1,
                "वि",
                0,
                0,
                "MULTIPLE_CANDIDATES",
                alignment_state="ALIGN_EXACT",
            )
        ]
        for source in ("ADJUDICATED", "PROBE_MAJORITY", "PROBE_UNANIMOUS"):
            metrics = score_line(bindings, pred, gold, source, 0)
            assert metrics.errors["GOLD_AMBIGUITY"] == 0
            assert metrics.errors["CARRIER_ASSIGNMENT_ERROR"] == 1
        assert "GOLD_AMBIGUITY" in ERROR_CATEGORIES


# ---------------------------------------------------------------------------
# §9: deterministic gold selection
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not PROBE_DIR.exists(), reason="AV v2 probe data not present in this checkout")
class TestGoldSelection:
    def test_adjudicated_record_wins_over_the_raw_probes(self) -> None:
        record = load_gold_record(430, 5, PROBE_DIR, ADJUDICATION_DIR, REPO)
        assert record.status == "GOLD_OK"
        assert record.source == "ADJUDICATED"
        assert record.record_paths == (
            "data/transcriptions/atharvaveda_bsb_1856/v2/adjudication/"
            "adjudicated_c00430_line05.json",
        )

    def test_the_overruled_reader_is_not_the_one_measured(self) -> None:
        """R1 read ह्यस्य and was overruled; the adjudicated text is हस्य."""
        record = load_gold_record(430, 5, PROBE_DIR, ADJUDICATION_DIR, REPO)
        assert "ह॑स्य" in record.text
        assert "ह्य॑स्य" not in record.text

    def test_c159_uses_the_adjudicated_reading_not_s1(self) -> None:
        """S1 read अनयद्वाचो / अयं and was overruled on both."""
        record = load_gold_record(159, 2, PROBE_DIR, ADJUDICATION_DIR, REPO)
        assert record.source == "ADJUDICATED"
        assert "अन॑यन्वा॒चो" in record.text
        assert "अग्रं॒" in record.text

    def test_c032_l19_is_unanimous_after_normalisation(self) -> None:
        """The specific repair: the split that was resolved by glob order."""
        record = load_gold_record(32, 19, PROBE_DIR, ADJUDICATION_DIR, REPO)
        assert record.status == "GOLD_OK"
        assert record.source == "PROBE_UNANIMOUS"
        assert record.readers == ("Q1", "Q2")

    def test_c032_l12_is_a_recorded_strict_majority(self) -> None:
        record = load_gold_record(32, 12, PROBE_DIR, ADJUDICATION_DIR, REPO)
        assert record.status == "GOLD_OK"
        assert record.source == "PROBE_MAJORITY"
        assert "P1,P3" in record.note
        assert record.dissent, "P2's differing verse numeral must be recorded"

    def test_a_line_with_no_gold_is_absent_not_invented(self) -> None:
        record = load_gold_record(15, 2, PROBE_DIR, ADJUDICATION_DIR, REPO)
        assert record.status == "GOLD_ABSENT"
        assert not record.usable

    @pytest.mark.parametrize(("canvas", "line"), [(32, 12), (32, 19), (159, 2), (411, 9), (430, 5)])
    def test_selection_is_independent_of_directory_order(
        self, canvas: int, line: int, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The same checkout must yield the same gold on any filesystem."""
        baseline = load_gold_record(canvas, line, PROBE_DIR, ADJUDICATION_DIR, REPO)
        original = pathlib.Path.glob

        def reversed_glob(self: pathlib.Path, pattern: str):  # type: ignore[no-untyped-def]
            return reversed(list(original(self, pattern)))

        monkeypatch.setattr(pathlib.Path, "glob", reversed_glob)
        flipped = load_gold_record(canvas, line, PROBE_DIR, ADJUDICATION_DIR, REPO)
        assert flipped == baseline

    @pytest.mark.parametrize(("canvas", "line"), [(32, 12), (32, 19), (159, 2), (411, 9), (430, 5)])
    def test_every_gold_line_resolves_deterministically(self, canvas: int, line: int) -> None:
        record = load_gold_record(canvas, line, PROBE_DIR, ADJUDICATION_DIR, REPO)
        assert record.status == "GOLD_OK"
        assert record.source in ("ADJUDICATED", "PROBE_UNANIMOUS", "PROBE_MAJORITY")
        assert record.record_paths


class TestGoldSelectionOrderGuards:
    """Guard the sorts themselves, not only the outcomes they no longer decide.

    The five real gold lines no longer have a tie for filesystem order to
    break, so a directory-order test over them passes whether or not the
    globs are sorted. These use a genuine unadjudicated split, where the
    reader list and the recorded dissent are the order-sensitive outputs.
    """

    @staticmethod
    def _probes(tmp_path: pathlib.Path) -> pathlib.Path:
        import json

        probes = tmp_path / "probes"
        probes.mkdir()
        for reader, text in (("Z9", "क॒ ख"), ("A1", "क ख॒"), ("M5", "क ख ग॒")):
            (probes / f"{reader}_line.json").write_text(
                json.dumps(
                    {
                        "reader": reader,
                        "canvas_index": 1,
                        "line_index": 1,
                        "text_devanagari": text,
                    }
                ),
                encoding="utf-8",
            )
        return probes

    def test_readers_are_ordered_by_reader_id_not_by_listing(self, tmp_path: pathlib.Path) -> None:
        probes = self._probes(tmp_path)
        record = load_gold_record(1, 1, probes, tmp_path / "adj", tmp_path)
        assert record.status == "GOLD_UNADJUDICATED"
        assert record.readers == ("A1", "M5", "Z9")

    def test_a_reversed_listing_gives_the_identical_record(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        probes = self._probes(tmp_path)
        baseline = load_gold_record(1, 1, probes, tmp_path / "adj", tmp_path)
        original = pathlib.Path.glob

        def reversed_glob(self: pathlib.Path, pattern: str):  # type: ignore[no-untyped-def]
            return reversed(list(original(self, pattern)))

        monkeypatch.setattr(pathlib.Path, "glob", reversed_glob)
        assert load_gold_record(1, 1, probes, tmp_path / "adj", tmp_path) == baseline


class TestGoldSelectionFailsClosed:
    def test_a_split_with_no_majority_is_withheld(self, tmp_path: pathlib.Path) -> None:
        import json

        probes = tmp_path / "probes"
        probes.mkdir()
        for reader, text in (("A1", "क॒ ख"), ("A2", "क ख॒")):
            (probes / f"{reader}.json").write_text(
                json.dumps(
                    {
                        "reader": reader,
                        "canvas_index": 1,
                        "line_index": 1,
                        "text_devanagari": text,
                    }
                ),
                encoding="utf-8",
            )
        record = load_gold_record(1, 1, probes, tmp_path / "adj", tmp_path)
        assert record.status == "GOLD_UNADJUDICATED"
        assert not record.usable
        assert len(record.dissent) == 2

    def test_two_adjudicated_records_for_one_line_fail_closed(self, tmp_path: pathlib.Path) -> None:
        import json

        adj = tmp_path / "adj"
        adj.mkdir()
        for name in ("adjudicated_a.json", "adjudicated_b.json"):
            (adj / name).write_text(
                json.dumps(
                    {
                        "canvas_index": 1,
                        "line_index": 1,
                        "adjudicated_text": "क॒ ख",
                    }
                ),
                encoding="utf-8",
            )
        record = load_gold_record(1, 1, tmp_path / "probes", adj, tmp_path)
        assert record.status == "GOLD_MULTIPLE_ADJUDICATED"
        assert not record.usable

    def test_unreadable_json_does_not_crash_selection(self, tmp_path: pathlib.Path) -> None:
        probes = tmp_path / "probes"
        probes.mkdir()
        (probes / "broken.json").write_text("{not json", encoding="utf-8")
        record = load_gold_record(1, 1, probes, tmp_path / "adj", tmp_path)
        assert record.status == "GOLD_ABSENT"


# ---------------------------------------------------------------------------
# Reassembly and exactness
# ---------------------------------------------------------------------------


class TestReassembly:
    def test_a_bound_mark_round_trips_to_the_accented_line(self) -> None:
        skeleton = "अनागसं ब्रह्मणा"
        bindings = [
            Binding("anudatta", 0, 10, 0, "अनागसं", 0, "अ", 0, 0, "BOUND_EXACT"),
            Binding("svarita", 20, 30, 1, "ब्रह्मणा", 1, "ह्म", 0, 1, "BOUND_EXACT"),
        ]
        # The mark is written immediately after its carrier cluster, which is
        # where parse_gold_marks reads it from — so the two are inverses.
        assert reassemble_accented_line(skeleton, bindings) == (
            "अ" + ANUDATTA + "नागसं ब्र" + "ह्म" + SVARITA + "णा"
        )

    def test_reassembly_of_a_real_gold_line_matches_the_gold_text(self) -> None:
        text = normalise_tokenisation("अ॒ना॒गसं॒ ब्रह्म॑णा त्वा कृणोमि शि॒वे ते॒ द्यावा॑पृथि॒वी उ॒भे स्ता॑म् ॥ १ ॥")
        marks = parse_gold_marks(text)
        skeleton = " ".join(
            "".join(c for c in token if c not in (ANUDATTA, SVARITA)) for token in text.split()
        )
        bindings = [
            Binding(
                m.mark_type,
                0,
                0,
                m.word_index,
                None,
                m.aksara_index,
                None,
                None,
                m.word_index,
                "BOUND_EXACT",
            )
            for m in marks
        ]
        assert reassemble_accented_line(skeleton, bindings) == text

    def test_exactness_is_false_when_a_carrier_is_wrong(self) -> None:
        text = normalise_tokenisation("अ॒नागसं")
        skeleton = "अनागसं"
        bindings = [Binding("anudatta", 0, 10, 0, "अनागसं", 1, "ना", 0, 0, "BOUND_EXACT")]
        pred = _pred(("anudatta", 0.1))
        gold = parse_gold_marks(text)
        metrics = score_line(bindings, pred, gold, "ADJUDICATED", 0)
        exact = line_exactness(text, skeleton, skeleton, bindings, metrics)
        assert exact.skeleton_exact
        assert exact.accent_set_exact
        assert not exact.carrier_exact
        assert not exact.full_accented_line_exact


# ---------------------------------------------------------------------------
# End-to-end on the real c411/l09 geometry
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not ADJUDICATION_DIR.exists(), reason="AV v2 gold data not present")
class TestRealLine411EndToEnd:
    """The verified silent high-confidence failure, scored end to end.

    Before the repair: word_binding_acc 0.2727, akṣara 0.1818,
    auto_promote_frac 1.0, every mark BOUND_EXACT.
    """

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
    CENTERS: ClassVar[list[tuple[float, str]]] = [
        (327.0, "svarita"),
        (507.0, "anudatta"),
        (820.5, "anudatta"),
        (963.5, "svarita"),
        (1173.0, "anudatta"),
        (1357.5, "svarita"),
        (1525.0, "anudatta"),
        (1715.0, "anudatta"),
        (1970.0, "svarita"),
        (2211.0, "anudatta"),
        (2365.5, "svarita"),
    ]

    def _run(self):  # type: ignore[no-untyped-def]
        record = load_gold_record(411, 9, PROBE_DIR, ADJUDICATION_DIR, REPO)
        marks = [
            {
                "type": kind,
                "x0": int(c - (5 if kind == "svarita" else 19)),
                "x1": int(c + (5 if kind == "svarita" else 19)),
            }
            for c, kind in self.CENTERS
        ]
        bindings, alignment = bind_line_detailed(marks, record.skeleton, self.SPANS)
        gold = parse_gold_marks(record.text)
        pred = predicted_marks(marks, self.SPANS)
        assert alignment is not None
        metrics = score_line(bindings, pred, gold, record.source, len(alignment.unaligned_spans))
        return record, bindings, alignment, metrics

    def test_eleven_of_twelve_gold_marks_are_recalled(self) -> None:
        _, _, _, metrics = self._run()
        assert metrics.gold_total == 12
        assert metrics.matched == 11
        assert metrics.false_negatives == 1
        assert metrics.false_positives == 0

    def test_the_single_miss_is_the_svarita_on_indram(self) -> None:
        record, _, _, metrics = self._run()
        gold = parse_gold_marks(record.text)
        detail = " ".join(metrics.error_detail)
        assert "DETECTION_MISS" in detail
        assert gold[2].word_index == 2  # इन्द्रं
        assert gold[2].mark_type == "svarita"

    def test_word_binding_is_now_perfect_on_the_matched_marks(self) -> None:
        _, _, _, metrics = self._run()
        assert metrics.word_correct == 11
        assert metrics.word_binding_acc == 1.0

    def test_carrier_binding_is_now_perfect_on_the_matched_marks(self) -> None:
        _, _, _, metrics = self._run()
        assert metrics.aksara_correct == 11
        assert metrics.aksara_binding_acc == 1.0

    def test_the_only_residual_is_the_detection_miss(self) -> None:
        _, _, _, metrics = self._run()
        assert metrics.errors["DETECTION_MISS"] == 1
        assert metrics.errors["TOKEN_ALIGNMENT_ERROR"] == 0
        assert metrics.errors["CARRIER_ASSIGNMENT_ERROR"] == 0
        assert metrics.errors["SPAN_SEGMENTATION_ERROR"] == 0
        assert sum(metrics.errors.values()) == 1

    def test_the_line_no_longer_claims_a_perfect_promotion_rate_falsely(
        self,
    ) -> None:
        _, bindings, alignment, metrics = self._run()
        assert alignment.line_safe
        # Promotion is now earned rather than asserted: every promoted mark is
        # on the right carrier.
        assert metrics.promoted_aksara_correct == metrics.promoted
        assert metrics.promoted_aksara_acc == 1.0
        assert all(b.alignment_state for b in bindings)
