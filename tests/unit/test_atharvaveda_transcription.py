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
        _, records = self._run(
            tmp_path, [unit(32, 1, "क")], [unit(32, 1, "ख")]
        )
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
