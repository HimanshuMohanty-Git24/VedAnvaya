"""The same checkout must produce byte-identical AV calibration metrics.

The previous runner failed this in two ways. It resolved split gold by
``PROBE_DIR.glob()`` order, which on c032/l19 alone moves the aggregate
word-binding accuracy from 0.85454 to 0.65454 and flips the zero-tolerance
``source_ambiguous_gold`` gate from PASS to FAIL. And it wrote a
machine-absolute Windows path into the committed result artifact, so the file
could not be byte-compared across machines at all.

These tests run the real per-line pipeline over the gold lines under
deliberately perturbed enumeration orders and require the canonical payload
hash to be identical every time.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
SCAN = REPO / "data/raw/bsb_mdz/2026-09-07/bsb10219750"
GOLD_LINES = [
    {"canvas_index": 32, "line_index": 12, "stratum": "gold_verified", "note": ""},
    {"canvas_index": 32, "line_index": 19, "stratum": "gold_verified", "note": ""},
    {"canvas_index": 159, "line_index": 2, "stratum": "middle_kandas", "note": ""},
    {"canvas_index": 411, "line_index": 9, "stratum": "kanda19_area", "note": ""},
    {"canvas_index": 430, "line_index": 5, "stratum": "kanda20_area", "note": ""},
]


def _runner():  # type: ignore[no-untyped-def]
    spec = importlib.util.spec_from_file_location(
        "run_av_calibration", REPO / "scripts" / "run_av_calibration.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_av_calibration"] = module
    spec.loader.exec_module(module)
    return module


def _canonical(results: list[dict]) -> str:
    return json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True)


def _digest(results: list[dict]) -> str:
    return hashlib.sha256(_canonical(results).encode("utf-8")).hexdigest()


pytestmark = pytest.mark.skipif(not SCAN.exists(), reason="1856 scan not present in this checkout")


class TestEnumerationOrderIndependence:
    def _run(self, order: str) -> list[dict]:
        run = _runner()
        ordered = run._order_lines(GOLD_LINES, order)
        by_key = {}
        for entry in ordered:
            r = run._run_line(entry)
            by_key[(r["canvas_index"], r["line_index"])] = r
        return [by_key[(e["canvas_index"], e["line_index"])] for e in GOLD_LINES]

    def test_normal_and_reversed_order_agree_exactly(self) -> None:
        assert _digest(self._run("normal")) == _digest(self._run("reversed"))

    def test_normal_and_shuffled_order_agree_exactly(self) -> None:
        assert _digest(self._run("normal")) == _digest(self._run("shuffled"))

    def test_all_three_orders_agree_exactly(self) -> None:
        digests = {
            self._run(o) and _digest(self._run(o)) for o in ("normal", "reversed", "shuffled")
        }
        assert len(digests) == 1

    def test_a_repeated_run_in_the_same_order_agrees(self) -> None:
        assert _digest(self._run("normal")) == _digest(self._run("normal"))

    def test_the_perturbations_really_do_change_the_order(self) -> None:
        run = _runner()
        normal = run._order_lines(GOLD_LINES, "normal")
        assert run._order_lines(GOLD_LINES, "reversed") != normal
        assert run._order_lines(GOLD_LINES, "shuffled") != normal

    def test_the_shuffle_is_itself_deterministic(self) -> None:
        run = _runner()
        first = run._order_lines(GOLD_LINES, "shuffled")
        assert run._order_lines(GOLD_LINES, "shuffled") == first


class TestDirectoryOrderIndependence:
    def test_reversed_directory_listing_changes_nothing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        run = _runner()
        baseline = [run._run_line(e) for e in GOLD_LINES]
        original = pathlib.Path.glob

        def reversed_glob(self: pathlib.Path, pattern: str):  # type: ignore[no-untyped-def]
            return reversed(list(original(self, pattern)))

        monkeypatch.setattr(pathlib.Path, "glob", reversed_glob)
        flipped = [run._run_line(e) for e in GOLD_LINES]
        assert _digest(flipped) == _digest(baseline)

    def test_c032_l19_does_not_depend_on_which_probe_is_listed_first(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The specific defect: Q1 first passes the gate, Q2 first fails it."""
        run = _runner()
        baseline = run._run_line(GOLD_LINES[1])
        original = pathlib.Path.glob

        def reversed_glob(self: pathlib.Path, pattern: str):  # type: ignore[no-untyped-def]
            return reversed(list(original(self, pattern)))

        monkeypatch.setattr(pathlib.Path, "glob", reversed_glob)
        flipped = run._run_line(GOLD_LINES[1])
        assert flipped == baseline
        assert baseline["source_ambiguous"] == 0
        assert flipped["source_ambiguous"] == 0


class TestArtifactPortability:
    def test_no_absolute_path_leaks_into_a_result_row(self) -> None:
        run = _runner()
        blob = _canonical([run._run_line(e) for e in GOLD_LINES])
        assert "D:\\" not in blob
        assert "D:/" not in blob
        assert str(REPO) not in blob
        assert "\\\\" not in blob

    def test_gold_record_paths_are_repo_relative_posix(self) -> None:
        run = _runner()
        for entry in GOLD_LINES:
            row = run._run_line(entry)
            for path in row["gold_records"]:
                assert not pathlib.PurePosixPath(path).is_absolute()
                assert "\\" not in path
                assert (REPO / path).exists()

    def test_the_scan_directory_is_anchored_to_the_repo(self) -> None:
        crop_spec = importlib.util.spec_from_file_location(
            "crop_atharvaveda_leaf", REPO / "scripts" / "crop_atharvaveda_leaf.py"
        )
        assert crop_spec and crop_spec.loader
        crop = importlib.util.module_from_spec(crop_spec)
        crop_spec.loader.exec_module(crop)
        assert crop.SCAN_DIR.is_absolute()
        assert crop.leaf_path(32).is_absolute()


class TestGateDirection:
    def test_a_must_be_zero_gate_is_read_as_a_ceiling(self) -> None:
        """The old runner compared every gate with >=, so this printed PASS."""
        run = _runner()
        text, passed = run._verdict(11, "source_ambiguous_gold")
        assert not passed
        assert "FAIL" in text
        text, passed = run._verdict(0, "source_ambiguous_gold")
        assert passed

    def test_floor_gates_are_still_read_as_floors(self) -> None:
        run = _runner()
        _, passed = run._verdict(0.94, "word_binding_acc")
        assert not passed
        _, passed = run._verdict(0.95, "word_binding_acc")
        assert passed

    def test_every_threshold_declares_a_direction(self) -> None:
        run = _runner()
        assert set(run.GATE_DIRECTION) == set(run.THRESHOLD)

    def test_the_seven_thresholds_are_unchanged(self) -> None:
        """§15: the predeclared gates are frozen."""
        run = _runner()
        assert run.THRESHOLD == {
            "detection_recall": 0.90,
            "detection_precision": 0.85,
            "class_accuracy": 1.00,
            "word_binding_acc": 0.95,
            "auto_promote_frac": 0.50,
            "source_ambiguous_gold": 0,
            "extractor_success_rate": 0.95,
        }
