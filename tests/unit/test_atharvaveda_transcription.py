"""Tests for the Atharvaveda 1856 transcription and reconciliation pipeline.

The thing these tests exist to protect is narrow and specific: a unit may be
called verified only when two independent readings of the same page image
produced the same codepoints, accents included. Every other outcome has to
stay visible as an uncertainty, because the failure mode this corpus
actually suffered was two readers who both dropped the accent layer and
therefore agreed with each other while both were wrong.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import unicodedata
from pathlib import Path
from typing import ClassVar

import pytest

REPO = Path(__file__).resolve().parents[2]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


reconcile = _load("reconcile_atharvaveda_v2")

ANUDATTA = "॒"
SVARITA = "॑"


def unit(canvas: int, mantra: int, text: str, **extra) -> dict:
    row = {
        "canvas_index": canvas,
        "mdz_image_id": f"bsb10219750_{canvas:05d}",
        "printed_page": 18,
        "kanda": 2,
        "sukta": 9,
        "mantra": mantra,
        "paryaya": None,
        "text_devanagari": text,
        "accent_marks_present": bool(set(text) & {ANUDATTA, SVARITA}),
        "unclear_count": 0,
        "spans_canvases": None,
        "structural_marker": "running head",
        "reader": "R1",
        "reader_kind": "MODEL_VISUAL_READ",
        "reader_identity": "claude-opus-5/agent:test",
        "run_id": "TEST_RUN",
        "transcription_policy": "bsb-1856-devanagari-v2",
    }
    row.update(extra)
    return row


class TestAccentHandling:
    def test_the_two_printed_marks_are_recognised_as_accents(self) -> None:
        assert reconcile.is_accent(ANUDATTA)
        assert reconcile.is_accent(SVARITA)

    def test_an_ordinary_letter_is_not_an_accent(self) -> None:
        assert not reconcile.is_accent("क")

    def test_vedic_extensions_count_as_accents_if_a_reader_reaches_for_one(self) -> None:
        assert reconcile.is_accent("᳚")

    def test_skeleton_removes_the_accent_layer_and_nothing_else(self) -> None:
        accented = f"दश{SVARITA}वृक{ANUDATTA}्ष"
        bare = "दशवृक्ष"
        assert reconcile.skeleton(accented) == bare

    def test_accent_signature_records_position_in_the_bare_skeleton(self) -> None:
        signature = reconcile.accent_signature(f"क{SVARITA}ख{ANUDATTA}")
        assert signature == [(1, SVARITA), (2, ANUDATTA)]

    def test_the_same_marks_in_different_places_are_different_signatures(self) -> None:
        a = reconcile.accent_signature(f"क{SVARITA}खग")
        b = reconcile.accent_signature(f"कख{SVARITA}ग")
        assert a != b


class TestGrading:
    def test_identical_accented_readings_verify_exactly(self) -> None:
        text = f"दश{SVARITA}व"
        status, _ = reconcile.grade(unit(32, 1, text), unit(32, 1, text))
        assert status == "VERIFIED_EXACT"

    def test_agreement_on_an_unaccented_reading_is_not_verified_exact(self) -> None:
        """Two readers who both dropped the accent layer agree, and are both wrong.

        This is the exact failure that produced the previous corpus, so
        agreement alone must not be allowed to certify it.
        """
        text = "दशव"
        status, detail = reconcile.grade(unit(32, 1, text), unit(32, 1, text))
        assert status == "VERIFIED_WITH_ORTHOGRAPHIC_NOTE"
        assert "accent" in detail

    def test_same_syllables_different_accents_is_accent_uncertain(self) -> None:
        left = unit(32, 1, f"दश{SVARITA}व")
        right = unit(32, 1, f"द{SVARITA}शव")
        status, _ = reconcile.grade(left, right)
        assert status == "ACCENT_UNCERTAIN"

    def test_one_reader_dropping_accents_is_accent_uncertain_not_verified(self) -> None:
        left = unit(32, 1, f"दश{SVARITA}व")
        right = unit(32, 1, "दशव")
        status, detail = reconcile.grade(left, right)
        assert status == "ACCENT_UNCERTAIN"
        assert "dropped the accent layer" in detail

    def test_a_small_syllable_difference_is_character_uncertain(self) -> None:
        left = unit(32, 1, "दशवृक्ष")
        right = unit(32, 1, "दशवृख्ष")
        status, _ = reconcile.grade(left, right)
        assert status == "CHARACTER_UNCERTAIN"

    def test_a_wholesale_difference_is_read_as_a_boundary_disagreement(self) -> None:
        left = unit(32, 1, "क" * 40)
        right = unit(32, 1, "ख" * 40)
        status, _ = reconcile.grade(left, right)
        assert status == "BOUNDARY_UNCERTAIN"

    def test_an_unreadable_mark_from_either_reader_is_character_uncertain(self) -> None:
        left = unit(32, 1, "दश[?]व")
        right = unit(32, 1, "दशगव")
        status, _ = reconcile.grade(left, right)
        assert status == "CHARACTER_UNCERTAIN"

    def test_a_unit_only_one_reader_saw_needs_structural_review(self) -> None:
        status, detail = reconcile.grade(unit(32, 1, "द"), None)
        assert status == "STRUCTURAL_REVIEW_REQUIRED"
        assert "R1" in detail

    @pytest.mark.parametrize("status", sorted(reconcile.RELEASE_ELIGIBLE))
    def test_only_two_statuses_are_release_eligible(self, status: str) -> None:
        assert status in {"VERIFIED_EXACT", "VERIFIED_WITH_ORTHOGRAPHIC_NOTE"}

    def test_uncertain_statuses_are_never_release_eligible(self) -> None:
        for status in (
            "ACCENT_UNCERTAIN",
            "CHARACTER_UNCERTAIN",
            "BOUNDARY_UNCERTAIN",
            "STRUCTURAL_REVIEW_REQUIRED",
            "SOURCE_AMBIGUOUS",
            "PHILOLOGICAL_REVIEW_REQUIRED",
        ):
            assert status not in reconcile.RELEASE_ELIGIBLE


class TestReconciliationOutput:
    def _run(self, tmp_path: Path, left: list[dict], right: list[dict]) -> tuple[dict, list[dict]]:
        r1, r2, out = tmp_path / "R1", tmp_path / "R2", tmp_path / "out"
        for directory, rows in ((r1, left), (r2, right)):
            directory.mkdir(parents=True)
            with (directory / "leaf_00032.jsonl").open("w", encoding="utf-8") as handle:
                for row in rows:
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        summary = reconcile.reconcile(r1, r2, out)
        records = [
            json.loads(line)
            for line in (out / "leaf_00032.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        return summary, records

    def test_a_disagreeing_unit_carries_no_canonical_text(self, tmp_path: Path) -> None:
        """A merged reading is not something either reader saw on the page."""
        summary, records = self._run(
            tmp_path,
            [unit(32, 1, "दशवृक्ष")],
            [unit(32, 1, "दशवृख्ष")],
        )
        assert records[0]["text_devanagari"] is None
        assert records[0]["release_eligible"] is False
        assert records[0]["r1_text"] and records[0]["r2_text"]
        assert summary["release_eligible_units"] == 0

    def test_both_readings_are_kept_so_the_disagreement_stays_auditable(
        self, tmp_path: Path
    ) -> None:
        _, records = self._run(tmp_path, [unit(32, 1, "क")], [unit(32, 1, "ख")])
        assert records[0]["r1_text"] == "क"
        assert records[0]["r2_text"] == "ख"

    def test_released_text_is_nfc(self, tmp_path: Path) -> None:
        text = f"दश{SVARITA}व"
        _, records = self._run(tmp_path, [unit(32, 1, text)], [unit(32, 1, text)])
        assert records[0]["text_devanagari"] == unicodedata.normalize("NFC", text)

    def test_a_unit_seen_by_one_reader_only_is_counted_as_such(self, tmp_path: Path) -> None:
        summary, _ = self._run(
            tmp_path,
            [unit(32, 1, "क"), unit(32, 2, "ख")],
            [unit(32, 1, "क")],
        )
        assert summary["units_total"] == 2
        assert summary["units_read_by_both"] == 1
        assert summary["units_read_by_one_only"] == 1

    def test_the_accent_reproduction_gap_is_reported(self, tmp_path: Path) -> None:
        summary, _ = self._run(
            tmp_path,
            [unit(32, 1, "दशव"), unit(32, 2, f"द{SVARITA}श")],
            [unit(32, 1, "दशव"), unit(32, 2, f"द{SVARITA}श")],
        )
        assert summary["units_carrying_any_vedic_accent"] == 1
        assert summary["accent_reproduction_gap"] == 1

    def test_disagreement_rates_are_reported_separately(self, tmp_path: Path) -> None:
        summary, _ = self._run(
            tmp_path,
            [unit(32, 1, f"दश{SVARITA}व")],
            [unit(32, 1, f"द{SVARITA}शव")],
        )
        assert summary["accent_disagreement_rate_over_accent_bearing_units"] == 1.0
        assert summary["character_disagreement_rate_over_units"] == 0.0

    def test_reconciliation_is_deterministic(self, tmp_path: Path) -> None:
        rows = [unit(32, 1, f"दश{SVARITA}व"), unit(32, 2, "क")]
        first, _ = self._run(tmp_path / "a", rows, rows)
        second, _ = self._run(tmp_path / "b", rows, rows)
        assert first == second


class TestAlignmentAcrossAnUnstatedCoordinate:
    """Leaf n15 prints no running head.

    One reader recorded `kanda: null` because the page does not print it; the
    other carried the kanda over and wrote `1`. They had in fact read the same
    eight units identically. Keying on the raw tuple turned that into sixteen
    one-sided units and measured nothing, so alignment tolerates a coordinate
    one reader left unstated — and nothing else.
    """

    @staticmethod
    def _align(left: dict, right: dict) -> list:
        return reconcile.align({reconcile.unit_key(left): left}, {reconcile.unit_key(right): right})

    def test_a_null_coordinate_does_not_split_two_readings_of_one_unit(self) -> None:
        aligned = self._align(
            unit(15, 1, "क", kanda=None, sukta=1), unit(15, 1, "क", kanda=1, sukta=1)
        )
        assert len(aligned) == 1
        _, a, b, note = aligned[0]
        assert a is not None and b is not None
        assert note is not None and "unstated coordinate" in note

    def test_the_stated_coordinate_is_the_one_carried(self) -> None:
        aligned = self._align(
            unit(15, 1, "क", kanda=None, sukta=1), unit(15, 1, "क", kanda=1, sukta=1)
        )
        assert aligned[0][0] == (15, 1, 1, 1)

    def test_two_readers_who_state_different_coordinates_do_not_align(self) -> None:
        """A null is 'not printed here'. Two different numbers is a real disagreement."""
        aligned = self._align(
            unit(15, 1, "क", kanda=1, sukta=1), unit(15, 1, "क", kanda=2, sukta=1)
        )
        assert len(aligned) == 2
        assert all(a is None or b is None for _, a, b, _ in aligned)

    def test_an_ambiguous_rescue_is_refused(self) -> None:
        """Two candidates means the null cannot be resolved, so it stays unpaired."""
        left = unit(15, 1, "क", kanda=None, sukta=1)
        r2_rows = {}
        for kanda in (1, 2):
            row = unit(15, 1, "क", kanda=kanda, sukta=1)
            r2_rows[reconcile.unit_key(row)] = row
        aligned = reconcile.align({reconcile.unit_key(left): left}, r2_rows)
        assert all(a is None or b is None for _, a, b, _ in aligned)

    def test_a_genuinely_one_sided_unit_is_still_one_sided(self) -> None:
        left = unit(15, 1, "क", kanda=1, sukta=1)
        other = unit(15, 2, "ख", kanda=1, sukta=1)
        aligned = reconcile.align(
            {reconcile.unit_key(left): left, reconcile.unit_key(other): other},
            {reconcile.unit_key(left): left},
        )
        one_sided = [item for item in aligned if item[1] is None or item[2] is None]
        assert len(one_sided) == 1

    def test_the_rescue_is_counted_so_it_is_never_silent(self, tmp_path: Path) -> None:
        r1, r2, out = tmp_path / "R1", tmp_path / "R2", tmp_path / "out"
        for directory, kanda in ((r1, None), (r2, 1)):
            directory.mkdir(parents=True)
            row = unit(15, 1, f"क{SVARITA}", kanda=kanda, sukta=1)
            (directory / "leaf_00015.jsonl").write_text(
                json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8"
            )
        summary = reconcile.reconcile(r1, r2, out)
        assert summary["units_aligned_across_an_unstated_coordinate"] == 1
        assert summary["units_read_by_both"] == 1
        assert summary["units_total"] == 1

    def test_rescued_pairs_are_still_graded_on_their_text(self, tmp_path: Path) -> None:
        """Tolerating a null coordinate must not tolerate a text disagreement."""
        r1, r2, out = tmp_path / "R1", tmp_path / "R2", tmp_path / "out"
        for directory, kanda, text in ((r1, None, "दशवृक्ष"), (r2, 1, "दशवृख्ष")):
            directory.mkdir(parents=True)
            row = unit(15, 1, text, kanda=kanda, sukta=1)
            (directory / "leaf_00015.jsonl").write_text(
                json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8"
            )
        summary = reconcile.reconcile(r1, r2, out)
        assert summary["release_eligible_units"] == 0
        assert summary["status_counts"]["CHARACTER_UNCERTAIN"] == 1


class TestContaminationFirewall:
    def test_the_prohibited_source_list_covers_every_named_edition(self) -> None:
        build = _load("build_atharvaveda_canonical")
        for marker in ("GRETIL", "TITUS", "VEDAWEB", "ORLANDI"):
            assert marker in build.PROHIBITED_MARKERS

    def test_the_build_releases_only_the_1856_scan(self) -> None:
        build = _load("build_atharvaveda_canonical")
        assert build.ARTIFACT_ID == "BSB.AV.SAUNAKA.ROTH_WHITNEY.1856.SCAN"
        assert build.SOURCE_ID == "BSB_MDZ"

    def test_the_build_timestamp_is_fixed_rather_than_read_from_the_clock(self) -> None:
        build = _load("build_atharvaveda_canonical")
        assert build.BUILD_TIMESTAMP.endswith("Z")


class TestReleaseQAStatusIsDerived:
    """The release must not stamp a verdict on itself.

    The build previously passed a hardcoded pass to `write_release`, so a
    corpus where two readers agreed on nothing would still have been published
    carrying a passing QA status.
    """

    @staticmethod
    def _status(reconciled: int, released: int):
        build = _load("build_atharvaveda_canonical")
        return build.qa_status([{}] * reconciled, [{}] * released)

    def test_a_release_that_freed_nothing_is_failed_not_passed(self) -> None:
        assert self._status(21, 0) == "FAILED"

    def test_nothing_reconciled_is_not_run_rather_than_a_pass(self) -> None:
        assert self._status(0, 0) == "NOT_RUN"

    def test_a_partial_release_says_so(self) -> None:
        assert self._status(21, 8) == "PASSED_WITH_WARNINGS"

    def test_only_a_wholly_released_reconciliation_passes(self) -> None:
        assert self._status(21, 21) == "PASSED"


class TestSourceLocators:
    def test_every_locator_names_the_leaf_it_was_read_from(self) -> None:
        build = _load("build_atharvaveda_canonical")
        locator = build.source_locator({"canvas_index": 32, "printed_page": 18})
        assert "bsb10219750" in locator
        assert "00032" in locator
        assert "18" in locator

    def test_an_unpaginated_leaf_is_said_to_be_unpaginated(self) -> None:
        build = _load("build_atharvaveda_canonical")
        locator = build.source_locator({"canvas_index": 3, "printed_page": None})
        assert "unpaginated" in locator


class TestGeometricAccentExtraction:
    """The accent layer read by image geometry rather than by a model.

    Three readers given canvas n32 line 12 one line at a time agreed exactly
    on its accents: seven anudatta and three svarita. That reading is the
    fixture these tests measure against, because it is the only accent
    ground truth in the project that more than one reader has ever confirmed.
    """

    # canvas n32 line 12 confirmed by three readers, line 19 by two, each
    # working alone from a 1:1 rendering of that line and nothing else.
    GROUND_TRUTH: ClassVar[dict[int, dict[str, int]]] = {
        12: {"anudatta": 7, "svarita": 3},
        19: {"anudatta": 7, "svarita": 4},
    }

    def test_the_two_marks_have_separate_shape_profiles(self) -> None:
        """One size rule cannot cover both, and assuming it could cost a pass.

        An anudatta is a broad flat dash and a svarita a narrow upright
        stroke. A single 'small mark' rule tuned on the dash rejects every
        svarita for being too tall, which is exactly what the first version
        of the extractor did.
        """
        extract = _load("extract_atharvaveda_accents")
        anudatta, svarita = extract.SHAPES["anudatta"], extract.SHAPES["svarita"]
        assert anudatta["aspect"][0] > 1.0, "an anudatta is wider than it is tall"
        assert svarita["aspect"][1] < 1.0, "a svarita is taller than it is wide"
        assert svarita["h"][1] > anudatta["h"][1], "a svarita is the taller mark"
        assert anudatta["w"][0] > svarita["w"][1], "an anudatta is the wider mark"

    def test_the_headline_band_is_the_whole_rule_not_its_densest_row(self) -> None:
        """The sirorekha is many pixels thick.

        Taking only its peak row leaves most of the rule inside the svarita
        band, where a flood fill escapes along it and swallows every svarita
        into one line-long component.
        """
        extract = _load("extract_atharvaveda_accents")
        rows = [0, 0, 5, 5, 100, 300, 400, 300, 100, 5, 5, 0]
        top, bottom = extract.find_headline_band(rows)
        peak = extract.find_headline(rows)
        assert top < peak < bottom
        assert (bottom - top) > 1

    def test_a_blank_line_yields_no_marks(self) -> None:
        extract = _load("extract_atharvaveda_accents")
        from PIL import Image

        blank = Image.new("L", (400, 120), color=255)
        result = extract.extract_line(blank, 20, 100, 120.0)
        assert result["marks"] == []

    def test_bands_are_placed_off_pitch_not_off_a_line_s_own_height(self) -> None:
        """A line's measured height is not a stable ruler.

        Whether the anudatta bars merge into the body's ink run varies line to
        line: on canvas n32 that made line 19's run 160px against line 12's
        121, so a band derived from the run bottom searched the empty space
        below line 19's bars and found none of its seven.
        """
        extract = _load("extract_atharvaveda_accents")
        assert extract.line_pitch([(0, 100), (170, 270), (340, 440)]) == 170.0
        assert extract.ANUDATTA_BAND[0] > 0, "the anudatta band sits below the rule"
        assert extract.SVARITA_BAND[0] < 0, "the svarita band sits above the rule"

    @pytest.mark.parametrize("line_index", sorted(GROUND_TRUTH))
    def test_it_reproduces_the_reading_the_readers_agreed_on(self, line_index: int) -> None:
        extract = _load("extract_atharvaveda_accents")
        crop = _load("crop_atharvaveda_leaf")
        if not crop.leaf_path(32).exists():
            pytest.skip("1856 scan not present in this checkout")
        expected = self.GROUND_TRUTH[line_index]
        result = extract.extract(32, line_index)["lines"][0]
        assert result["anudatta_count"] == expected["anudatta"]
        assert result["svarita_count"] == expected["svarita"]

    def test_the_running_head_carries_no_accents(self) -> None:
        """Line 0 of n32 is the running head, which this print does not accent."""
        extract = _load("extract_atharvaveda_accents")
        crop = _load("crop_atharvaveda_leaf")
        if not crop.leaf_path(32).exists():
            pytest.skip("1856 scan not present in this checkout")
        result = extract.extract(32, 0)["lines"][0]
        assert result["anudatta_count"] == 0
        assert result["svarita_count"] == 0


class TestWordSpansSplitOnGapsNotOnRunWidth:
    """A word gap is the blank run between two inked runs, not a narrow run.

    `_WORD_GAP_MIN_PX` is documented as a minimum *gap*, but was once applied
    to the width of the inked run instead. Canvas n32 cannot tell the two
    apart -- its rule never breaks inside a word -- so the error survived a
    calibration that had only n32 gold, and surfaced only when three further
    lines were read by three readers each: the cast rule breaks by 2px inside
    one word on n411 line 9, by 11px after the avagraha on n159 line 2, and by
    5px in the double danda on n430 line 5.

    The cost was not cosmetic. Spans are paired to skeleton tokens left to
    right by position, so each spurious break moved every carrier after it one
    word along -- n159 line 2 bound three of its ten marks to the danda
    instead of the word before it. On n411 line 9 the extra spans pushed the
    token/span mismatch past the alignment guard and the whole line came back
    SOURCE_AMBIGUOUS, failing a zero-tolerance gate.
    """

    @staticmethod
    def _rule_band(inked: list[bool]) -> tuple[list[bool], int]:
        """A one-row rule band in which column x is inked iff `inked[x]`."""
        return list(inked), len(inked)

    def test_a_gap_narrower_than_the_minimum_does_not_split_a_word(self) -> None:
        extract = _load("extract_atharvaveda_accents")
        mask, w = self._rule_band([True] * 40 + [False] * 2 + [True] * 40)
        assert extract._word_spans_from_rule(mask, w, 0, 0) == [(0, 81)]

    def test_a_gap_at_the_minimum_splits_into_two_words(self) -> None:
        extract = _load("extract_atharvaveda_accents")
        gap = extract._WORD_GAP_MIN_PX
        mask, w = self._rule_band([True] * 40 + [False] * gap + [True] * 40)
        assert extract._word_spans_from_rule(mask, w, 0, 0) == [
            (0, 39),
            (40 + gap, 79 + gap),
        ]

    def test_an_inked_run_narrower_than_the_minimum_is_still_a_span(self) -> None:
        """The width test deleted any short run -- a danda stroke, for one."""
        extract = _load("extract_atharvaveda_accents")
        gap = extract._WORD_GAP_MIN_PX
        mask, w = self._rule_band([True] * 40 + [False] * gap + [True] * 8)
        spans = extract._word_spans_from_rule(mask, w, 0, 0)
        assert spans == [(0, 39), (40 + gap, 47 + gap)]

    @pytest.mark.parametrize(("canvas", "line"), [(32, 12), (32, 19), (159, 2), (411, 9), (430, 5)])
    def test_no_two_spans_sit_closer_than_the_minimum_gap(self, canvas: int, line: int) -> None:
        """The invariant, asserted on every line the gold set has readers for."""
        extract = _load("extract_atharvaveda_accents")
        crop = _load("crop_atharvaveda_leaf")
        if not crop.leaf_path(canvas).exists():
            pytest.skip("1856 scan not present in this checkout")
        spans = extract.extract(canvas, line)["lines"][0]["word_spans"]
        gaps = [spans[i + 1][0] - spans[i][1] - 1 for i in range(len(spans) - 1)]
        assert all(g >= extract._WORD_GAP_MIN_PX for g in gaps), (
            f"c{canvas}/l{line} still splits on a sub-threshold gap: {gaps}"
        )

    # Whitespace token count of each line's adjudicated three-reader gold.
    GOLD_TOKENS: ClassVar[dict[tuple[int, int], int]] = {
        (32, 12): 12,
        (32, 19): 12,
        (159, 2): 13,
        (430, 5): 13,
    }

    @pytest.mark.parametrize(("canvas", "line"), sorted(GOLD_TOKENS))
    def test_span_count_equals_the_token_count_of_the_adjudicated_gold(
        self, canvas: int, line: int
    ) -> None:
        """The two-sided check: over-splitting and over-merging both show here.

        Bridging narrow gaps could in principle swallow a real word boundary,
        which the invariant test above cannot see -- it only asserts that no
        gap survives below the threshold, which the bridging loop guarantees
        by construction. This one can fail in both directions: a spurious
        break makes spans exceed tokens, and a swallowed word gap makes spans
        fall short. n411 line 9 is excluded and pinned separately, because its
        two free-standing visarga dot-pairs are real rule spans that carry no
        whitespace token of their own.
        """
        extract = _load("extract_atharvaveda_accents")
        crop = _load("crop_atharvaveda_leaf")
        if not crop.leaf_path(canvas).exists():
            pytest.skip("1856 scan not present in this checkout")
        spans = extract.extract(canvas, line)["lines"][0]["word_spans"]
        assert len(spans) == self.GOLD_TOKENS[(canvas, line)]

    def test_the_line_that_tripped_the_alignment_guard_now_clears_it(self) -> None:
        """n411 line 9 read 17 spans against 11 tokens; the guard allows 5.

        Asserted against the guard rather than against a span count, because
        the residual excess is the two visarga spans: a later fix that binds
        them to their own word should drive the mismatch to zero, and must not
        have to edit this test to do it.
        """
        extract = _load("extract_atharvaveda_accents")
        crop = _load("crop_atharvaveda_leaf")
        if not crop.leaf_path(411).exists():
            pytest.skip("1856 scan not present in this checkout")
        binder = pytest.importorskip("vedagraph.ingest.av_accent_binder")
        spans = extract.extract(411, 9)["lines"][0]["word_spans"]
        tokens = 11  # the adjudicated three-reader gold for this line
        allowed = max(1, round(max(tokens, len(spans)) * binder.MAX_TOKEN_SPAN_MISMATCH))
        assert abs(tokens - len(spans)) <= allowed, (
            f"{len(spans)} spans against {tokens} tokens still trips the guard"
        )


class TestLeafRendering:
    def test_bands_stay_landscape_so_the_accent_layer_survives_downsampling(self) -> None:
        """The reader caps the long edge.

        A band taller than it is wide is shrunk on its height, and this
        fount's accent marks are a few pixels tall, so they go with it.
        """
        crop = _load("crop_atharvaveda_leaf")
        assert crop.READER_LONG_EDGE == 1568

    def test_a_leaf_renders_to_landscape_bands(self, tmp_path: Path) -> None:
        crop = _load("crop_atharvaveda_leaf")
        if not crop.leaf_path(32).exists():
            pytest.skip("1856 scan not present in this checkout")
        from PIL import Image

        for path in crop.render(32, tmp_path):
            with Image.open(path) as band:
                assert band.width >= band.height
                assert band.width <= crop.READER_LONG_EDGE


class TestProvenanceIsTruthful:
    """A reading is evidence only if the record says who produced it.

    The specific falsehood these tests exist to prevent is a model reading
    released as though a human had reviewed it. Every reading in this corpus so
    far was performed by a model looking at a scan, and the release provenance
    has to say so, because rights, reliability, and every downstream claim about
    review depend on the difference.
    """

    def _run(self, tmp_path: Path, left: list[dict], right: list[dict]) -> list[dict]:
        r1, r2, out = tmp_path / "R1", tmp_path / "R2", tmp_path / "out"
        for directory, rows in ((r1, left), (r2, right)):
            directory.mkdir(parents=True)
            with (directory / "leaf_00032.jsonl").open("w", encoding="utf-8") as handle:
                for row in rows:
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        reconcile.reconcile(r1, r2, out)
        return [
            json.loads(line)
            for line in (out / "leaf_00032.jsonl").read_text(encoding="utf-8").splitlines()
        ]

    def test_a_model_reading_is_labelled_model_not_human(self) -> None:
        assert reconcile.MODEL_VISUAL_READ == "MODEL_VISUAL_READ"
        assert reconcile.MODEL_VISUAL_READ != reconcile.HUMAN_REVIEWED
        assert reconcile.HUMAN_REVIEWED not in {reconcile.MODEL_VISUAL_READ}

    def test_agreeing_readings_release_with_provenance(self, tmp_path: Path) -> None:
        text = f"दश{SVARITA}व"
        records = self._run(tmp_path, [unit(32, 1, text)], [unit(32, 1, text)])
        assert records[0]["release_eligible"] is True
        assert records[0]["provenance_complete"] is True
        assert records[0]["r1_provenance"]["reader_kind"] == "MODEL_VISUAL_READ"
        assert records[0]["r2_provenance"]["reader_kind"] == "MODEL_VISUAL_READ"

    @pytest.mark.parametrize("missing", ["reader", "reader_kind", "reader_identity", "run_id"])
    def test_agreeing_readings_are_withheld_when_provenance_is_incomplete(
        self, tmp_path: Path, missing: str
    ) -> None:
        """Agreement is not enough. An unattributable reading stays unreleased."""
        text = f"दश{SVARITA}व"
        blind = unit(32, 1, text)
        del blind[missing]
        records = self._run(tmp_path, [blind], [unit(32, 1, text)])
        assert records[0]["transcription_status"] == "VERIFIED_EXACT"
        assert records[0]["release_eligible"] is False
        assert records[0]["provenance_complete"] is False
        assert records[0]["r1_provenance"] is None

    def test_an_unrecognised_reader_kind_does_not_release(self, tmp_path: Path) -> None:
        text = f"दश{SVARITA}व"
        records = self._run(
            tmp_path,
            [unit(32, 1, text, reader_kind="TRANSCRIBED_BY_SOMEONE")],
            [unit(32, 1, text)],
        )
        assert records[0]["release_eligible"] is False


class TestEveryLeafIsAccountedFor:
    """478 canvases in, 478 canvases out.

    A leaf that was never assigned and a leaf that has no text on it look
    identical in a report that only counts what it read, so the ledger has to
    enumerate the artifact rather than the work done.
    """

    ledger: ClassVar = _load("av_production_ledger")

    def test_the_ledger_covers_every_canvas_in_the_artifact(self) -> None:
        payload = json.loads(self.ledger.LEDGER.read_text(encoding="utf-8"))
        assert payload["leaves_available"] == 478
        assert len(payload["leaves"]) == 478
        assert sum(payload["leaves_by_classification"].values()) == 478
        assert [row["canvas_index"] for row in payload["leaves"]] == list(range(1, 479))

    def test_front_and_back_matter_are_not_counted_as_outstanding_work(self) -> None:
        payload = json.loads(self.ledger.LEDGER.read_text(encoding="utf-8"))
        first, last = payload["samhita_text_canvas_range"]
        assert (first, last) == (15, 472)
        assert payload["text_candidate_leaves"] == last - first + 1
        outside = [
            row["canvas_index"]
            for row in payload["leaves"]
            if row["classification"] == self.ledger.OUT_OF_RANGE
        ]
        assert outside == list(range(1, first)) + list(range(last + 1, 479))

    def test_a_gutter_shadow_does_not_hide_a_page_of_type(self) -> None:
        """Canvas 200 is a dense text page whose binding shadow inks every row.

        Profiling the full block width merges its lines into one run and demotes
        it to front matter; 52 leaves were lost that way before the line profile
        was narrowed to the middle of the leaf.
        """
        payload = json.loads(self.ledger.LEDGER.read_text(encoding="utf-8"))
        rows = {row["canvas_index"]: row for row in payload["leaves"]}
        for canvas in (200, 220, 260):
            assert rows[canvas]["classification"] == self.ledger.TEXT_CANDIDATE
            assert rows[canvas]["located_lines"] >= 20
