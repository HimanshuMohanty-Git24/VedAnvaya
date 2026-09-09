"""The theonym-mention gold set and the arithmetic that scores it.

Two things are tested here and they are tested separately on purpose.

**The arithmetic.** ``scripts/evaluate_theonym_gold.py`` produces the only precision and
recall figures the four-Veda mention layer has, so the metric code is checked against
hand-built fixtures whose answers are known by inspection rather than by running the
code. That includes the cases where a rate does not exist -- an empty slice, a slice with
no predicted positives, a slice with no gold positives -- because returning ``0.0`` for
"undefined" is how a measurement quietly reports a failure as a success.

**The schema of the frozen set.** The gold file is a release artifact. The test that
matters most is not that it parses: it is that ``annotator`` says ``MODEL_ADJUDICATED``
on every row. No human has reviewed this set, the project distinguishes the two, and a
row claiming human review would make the whole measurement worth less than no
measurement at all. ``load_gold`` refuses the file outright if that field is anything
else, and this asserts that it does.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
from typing import Any

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
GOLD = REPO / "data" / "gold" / "theonym_mention_gold_v1.jsonl"
EXPECTED_SEED = 20260909


def _evaluator() -> Any:
    spec = importlib.util.spec_from_file_location(
        "evaluate_theonym_gold", REPO / "scripts" / "evaluate_theonym_gold.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["evaluate_theonym_gold"] = module
    spec.loader.exec_module(module)
    return module


EV = _evaluator()


def _row(
    *,
    row_id: str = "T-0001",
    graph_asserts: bool = True,
    gold_label: str = "MENTION",
    name_lemma_present: bool = True,
    veda: str = "RV",
    extraction_path: str = "rv-lemma-annotation",
    referent_certainty: str = "DEITY_CERTAIN",
    devata_id: str = "VG:DEVATA:INDRAH",
    stratum: str = "P1_rv_uniform",
    ambiguity_class: str = "UNAMBIGUOUS",
    borderline: bool = False,
    is_ambiguous_common_noun: bool = False,
) -> Any:
    return EV.GoldRow(
        row_id=row_id,
        stratum=stratum,
        passage_key=f"VG:RV:SAK:M01:S001:V{row_id[-3:]}",
        citation="RV 1.1.1",
        veda=veda,
        devata_id=devata_id,
        surface_form="indra",
        graph_asserts=graph_asserts,
        extraction_path=extraction_path,
        referent_certainty=referent_certainty,
        morphological_role="VOCATIVE",
        gold_label=gold_label,
        name_lemma_present=name_lemma_present,
        ambiguity_class=ambiguity_class,
        borderline=borderline,
        is_ambiguous_common_noun=is_ambiguous_common_noun,
        reasoning="fixture",
    )


# --------------------------------------------------------------------------- arithmetic


def test_score_counts_the_four_cells() -> None:
    rows = [
        _row(row_id="T-001", graph_asserts=True, gold_label="MENTION"),
        _row(row_id="T-002", graph_asserts=True, gold_label="MENTION"),
        _row(row_id="T-003", graph_asserts=True, gold_label="NO_MENTION"),
        _row(row_id="T-004", graph_asserts=False, gold_label="MENTION"),
        _row(row_id="T-005", graph_asserts=False, gold_label="NO_MENTION"),
        _row(row_id="T-006", graph_asserts=False, gold_label="NO_MENTION"),
    ]
    score = EV.score_rows(rows)
    assert (score.tp, score.fp, score.fn, score.tn) == (2, 1, 1, 2)
    assert score.support == 6


def test_precision_recall_f1_on_a_hand_computed_fixture() -> None:
    # 6 true positives, 2 false positives, 3 false negatives.
    # precision = 6/8 = 0.75, recall = 6/9 = 0.6666..., F1 = 2*.75*(2/3)/(.75+2/3).
    rows = (
        [_row(row_id=f"T-1{i:02d}", graph_asserts=True, gold_label="MENTION") for i in range(6)]
        + [
            _row(row_id=f"T-2{i:02d}", graph_asserts=True, gold_label="NO_MENTION")
            for i in range(2)
        ]
        + [
            _row(row_id=f"T-3{i:02d}", graph_asserts=False, gold_label="MENTION")
            for i in range(3)
        ]
    )
    score = EV.score_rows(rows)
    assert score.precision == pytest.approx(0.75)
    assert score.recall == pytest.approx(2 / 3)
    assert score.f1 == pytest.approx(2 * 0.75 * (2 / 3) / (0.75 + 2 / 3))
    assert score.f1 == pytest.approx(0.70588235, abs=1e-8)


def test_perfect_and_zero_scores_are_exact() -> None:
    perfect = EV.score_rows(
        [_row(row_id=f"T-4{i:02d}", graph_asserts=True, gold_label="MENTION") for i in range(5)]
        + [
            _row(row_id=f"T-5{i:02d}", graph_asserts=False, gold_label="NO_MENTION")
            for i in range(5)
        ]
    )
    assert perfect.precision == 1.0
    assert perfect.recall == 1.0
    assert perfect.f1 == 1.0
    assert perfect.specificity == 1.0

    hopeless = EV.score_rows(
        [_row(row_id=f"T-6{i:02d}", graph_asserts=True, gold_label="NO_MENTION") for i in range(4)]
    )
    assert hopeless.precision == 0.0
    assert hopeless.recall is None  # no gold positives: recall is undefined, not zero
    assert hopeless.f1 is None
    assert hopeless.specificity == 0.0


def test_undefined_rates_are_none_not_zero() -> None:
    empty = EV.score_rows([])
    assert empty.precision is None
    assert empty.recall is None
    assert empty.f1 is None
    assert empty.specificity is None

    no_prediction = EV.score_rows(
        [_row(row_id="T-701", graph_asserts=False, gold_label="MENTION")]
    )
    assert no_prediction.precision is None
    assert no_prediction.recall == 0.0
    assert no_prediction.f1 is None


def test_specificity_uses_the_negative_denominator() -> None:
    score = EV.Score(tp=0, fp=3, fn=0, tn=7)
    assert score.specificity == pytest.approx(0.7)


def test_name_lemma_target_scores_a_different_claim() -> None:
    # The layer asserts an edge; the name-word is in the verse but denotes the common
    # noun. That is a false positive on the strict target and a true positive on the
    # weaker one, which is exactly the distinction the two targets exist to draw.
    rows = [_row(row_id="T-801", graph_asserts=True, gold_label="NO_MENTION",
                 name_lemma_present=True)]
    assert EV.score_rows(rows).fp == 1
    assert EV.score_rows(rows, target="name_lemma_present").tp == 1

    # Host intrusion: the word is not a form of the deity's name at all. Wrong on both.
    hosts = [_row(row_id="T-802", graph_asserts=True, gold_label="NO_MENTION",
                  name_lemma_present=False)]
    assert EV.score_rows(hosts).fp == 1
    assert EV.score_rows(hosts, target="name_lemma_present").fp == 1


def test_ambiguous_rows_are_not_scorable() -> None:
    assert _row(gold_label="AMBIGUOUS").scorable is False
    assert _row(gold_label="MENTION").scorable is True
    assert _row(gold_label="NO_MENTION").scorable is True


def test_path_group_never_pools_the_two_paths() -> None:
    assert _row(extraction_path="rv-lemma-annotation").path_group == "rv-lemma-annotation"
    assert _row(extraction_path="sanskrit-surface-token", veda="AV").path_group == "surface"
    assert _row(extraction_path="sanskrit-surface-sandhi", veda="SV").path_group == "surface"
    # A row with no edge has no extraction_path, so it is grouped by its Veda: a missed
    # Rigvedic mention is a failure of the annotation path, not of the surface path.
    assert _row(extraction_path="", veda="RV", graph_asserts=False).path_group == (
        "rv-lemma-annotation"
    )
    assert _row(extraction_path="", veda="AV", graph_asserts=False).path_group == "surface"


def test_wilson_interval_brackets_the_point_estimate() -> None:
    low, high = EV.wilson_interval(8, 10)
    assert low < 0.8 < high
    # The textbook Wilson 95% interval for 8 successes in 10 trials.
    assert (low, high) == pytest.approx((0.4901, 0.9433), abs=1e-3)
    assert EV.wilson_interval(0, 0) == (0.0, 1.0)
    zero_low, zero_high = EV.wilson_interval(0, 20)
    assert zero_low == 0.0
    assert 0.0 < zero_high < 0.25
    one_low, one_high = EV.wilson_interval(20, 20)
    assert one_high == pytest.approx(1.0)
    assert 0.75 < one_low < 1.0


def test_build_report_separates_paths_and_excludes_ambiguous() -> None:
    rows = [
        _row(row_id="T-901", graph_asserts=True, gold_label="MENTION"),
        _row(row_id="T-902", graph_asserts=True, gold_label="NO_MENTION"),
        _row(
            row_id="T-903",
            graph_asserts=True,
            gold_label="MENTION",
            veda="AV",
            extraction_path="sanskrit-surface-token",
        ),
        _row(row_id="T-904", graph_asserts=True, gold_label="AMBIGUOUS"),
    ]
    report = EV.build_report(rows, None)
    assert report["gold_rows"] == 4
    assert report["scorable_rows"] == 3
    assert len(report["excluded_ambiguous"]) == 1
    assert set(report["by_path"]) == {"rv-lemma-annotation", "surface"}
    assert report["by_path"]["rv-lemma-annotation"]["precision"] == pytest.approx(0.5)
    assert report["by_path"]["surface"]["precision"] == pytest.approx(1.0)
    assert "live_graph" not in report


def test_low_support_groups_are_withheld_rather_than_printed() -> None:
    rows = [
        _row(row_id=f"T-A{i:02d}", devata_id="VG:DEVATA:INDRAH", gold_label="MENTION")
        for i in range(EV.MIN_SUPPORT)
    ] + [_row(row_id="T-B01", devata_id="VG:DEVATA:ARANYANI", gold_label="MENTION")]
    report = EV.build_report(rows, None)
    assert "VG:DEVATA:INDRAH" in report["by_deity"]
    assert "VG:DEVATA:ARANYANI" not in report["by_deity"]
    assert report["by_deity_withheld"]["VG:DEVATA:ARANYANI"] == 1


def test_ambiguity_failure_rate_counts_only_wrong_sense() -> None:
    rows = [
        # asserted, name-word present, wrong sense -> counts as an ambiguity failure
        _row(row_id="T-C01", graph_asserts=True, gold_label="NO_MENTION",
             name_lemma_present=True, is_ambiguous_common_noun=True),
        # asserted and right -> not a failure
        _row(row_id="T-C02", graph_asserts=True, gold_label="MENTION",
             is_ambiguous_common_noun=True),
        # asserted but the word is not the deity's name at all -> an attachment error,
        # not a sense error, so it must not inflate the ambiguity rate
        _row(row_id="T-C03", graph_asserts=True, gold_label="NO_MENTION",
             name_lemma_present=False, is_ambiguous_common_noun=True),
        # not asserted -> outside the denominator
        _row(row_id="T-C04", graph_asserts=False, gold_label="MENTION",
             is_ambiguous_common_noun=True),
    ]
    failure = EV.build_report(rows, None)["ambiguity_failure"]
    assert failure["rows_on_ambiguous_common_nouns"] == 4
    assert failure["asserted"] == 3
    assert failure["wrong_sense"] == 1
    assert failure["wrong_sense_rate"] == pytest.approx(1 / 3)


def test_reconcile_names_the_rows_that_drifted() -> None:
    rows = [
        _row(row_id="T-D01", graph_asserts=True),
        _row(row_id="T-D02", graph_asserts=False),
    ]
    live = {(rows[1].passage_key, rows[1].devata_id)}
    assert EV.reconcile(rows, live) == ["T-D01", "T-D02"]
    agreed = {(rows[0].passage_key, rows[0].devata_id)}
    assert EV.reconcile(rows, agreed) == []


# ------------------------------------------------------------------------------- schema


def test_gold_file_exists_and_loads() -> None:
    rows = EV.load_gold(GOLD)
    assert len(rows) >= 400, "the brief requires at least 400 adjudicated rows"
    assert len({row.row_id for row in rows}) == len(rows)


def test_every_row_is_model_adjudicated_and_never_human_reviewed() -> None:
    for line in GOLD.read_text(encoding="utf-8").splitlines():
        record = json.loads(line)
        assert record["annotator"] == "MODEL_ADJUDICATED", record["row_id"]
        assert record["annotator_model"]
        assert record["run_id"]


def test_load_gold_refuses_a_claim_of_human_review(tmp_path: pathlib.Path) -> None:
    first = json.loads(GOLD.read_text(encoding="utf-8").splitlines()[0])
    first["annotator"] = "HUMAN_REVIEWED"
    path = tmp_path / "forged.jsonl"
    path.write_text(json.dumps(first) + "\n", encoding="utf-8")
    with pytest.raises(EV.GoldSetError, match="HUMAN_REVIEWED"):
        EV.load_gold(path)


@pytest.mark.parametrize(
    "mutation",
    [
        {"gold_label": "PROBABLY"},
        {"reasoning": "   "},
        {"sanskrit": ""},
    ],
)
def test_load_gold_refuses_malformed_rows(
    tmp_path: pathlib.Path, mutation: dict[str, str]
) -> None:
    first = json.loads(GOLD.read_text(encoding="utf-8").splitlines()[0])
    first.update(mutation)
    path = tmp_path / "bad.jsonl"
    path.write_text(json.dumps(first) + "\n", encoding="utf-8")
    with pytest.raises(EV.GoldSetError):
        EV.load_gold(path)


def test_load_gold_refuses_a_missing_field(tmp_path: pathlib.Path) -> None:
    first = json.loads(GOLD.read_text(encoding="utf-8").splitlines()[0])
    del first["gold_label"]
    path = tmp_path / "short.jsonl"
    path.write_text(json.dumps(first) + "\n", encoding="utf-8")
    with pytest.raises(EV.GoldSetError, match="missing fields"):
        EV.load_gold(path)


def test_load_gold_refuses_a_duplicate_row_id(tmp_path: pathlib.Path) -> None:
    line = GOLD.read_text(encoding="utf-8").splitlines()[0]
    path = tmp_path / "dup.jsonl"
    path.write_text(line + "\n" + line + "\n", encoding="utf-8")
    with pytest.raises(EV.GoldSetError, match="listed twice"):
        EV.load_gold(path)


def test_load_gold_refuses_a_second_sample_seed(tmp_path: pathlib.Path) -> None:
    lines = GOLD.read_text(encoding="utf-8").splitlines()[:2]
    second = json.loads(lines[1])
    second["sample_seed"] = 1
    path = tmp_path / "reseeded.jsonl"
    path.write_text(lines[0] + "\n" + json.dumps(second) + "\n", encoding="utf-8")
    with pytest.raises(EV.GoldSetError, match="sample seeds"):
        EV.load_gold(path)


def test_the_sample_seed_is_recorded_and_single() -> None:
    seeds = {
        json.loads(line)["sample_seed"]
        for line in GOLD.read_text(encoding="utf-8").splitlines()
    }
    assert seeds == {EXPECTED_SEED}


def test_the_set_is_stratified_over_every_veda_and_both_directions() -> None:
    rows = EV.load_gold(GOLD)
    assert {row.veda for row in rows} == {"RV", "SV", "YV", "AV"}
    assert {row.path_group for row in rows} == {"rv-lemma-annotation", "surface"}
    assert sum(1 for row in rows if row.graph_asserts) >= 100
    assert sum(1 for row in rows if not row.graph_asserts) >= 100
    assert sum(1 for row in rows if row.gold_label == "MENTION") >= 100
    assert sum(1 for row in rows if row.gold_label == "NO_MENTION") >= 100
    # The ambiguous common nouns the brief names must all be represented.
    named = {
        "VG:DEVATA:AGNIH",
        "VG:DEVATA:SOMAH",
        "VG:DEVATA:SURYAH",
        "VG:DEVATA:VAK",
        "VG:DEVATA:SARASVATI",
        "VG:DEVATA:RATHAH",
        "VG:DEVATA:KAH",
    }
    assert named <= {row.devata_id for row in rows}


def test_every_row_carries_evidence_a_reader_can_check() -> None:
    for row in EV.load_gold(GOLD):
        assert row.citation.strip(), row.row_id
        assert row.reasoning.strip(), row.row_id
        assert row.passage_key.startswith("VG:"), row.row_id
        if row.graph_asserts:
            assert row.extraction_path, row.row_id
            assert row.referent_certainty, row.row_id


def test_gold_labels_do_not_contradict_the_name_lemma_flag() -> None:
    # A row may say the name-word is present and still be NO_MENTION (the wrong sense),
    # but a MENTION with no form of the name anywhere is self-contradictory.
    for row in EV.load_gold(GOLD):
        if row.gold_label == "MENTION":
            assert row.name_lemma_present, row.row_id


def test_report_over_the_real_set_is_reproducible() -> None:
    rows = EV.load_gold(GOLD)
    first = EV.build_report(rows, None)
    second = EV.build_report(EV.load_gold(GOLD), None)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert first["overall"]["support"] == first["scorable_rows"]
