"""What the product is allowed to say about how good its evidence is.

Three rules, and each of them had already been broken somewhere in the shipped code when
these tests were written:

1. **A figure in a disclosure sentence is measured, never typed.** ``587`` was quoted as
   the whole of ``TIER_C`` (598) and as the whole of ``MODEL_ADJUDICATED`` (613), and
   ``613`` was said to span ten predicates (twelve). Four modules each held their own copy
   and three had drifted, in three different directions.
2. **A population sentence names every part of its population.** TIER_C is 587
   passage-anchored edges plus 11 Devata-to-Devata epithet identities. The published
   sentence said "all 587 TIER_C edges are Yajurvedic (320) or Atharvavedic (267) and not
   one is Rigvedic", which types the 11 out of existence -- and their evidence cites RV
   3.53 and RV 4.55. A reader takes that for a verified zero.
3. **A model label is never a human label, and a confidence is never a probability.**
   Nothing in ``data/gold/`` is human gold: 120 rows are an empty scaffold and 575 are
   ``MODEL_ADJUDICATED`` by ``claude-opus-5``. Both facts are true of the files on disk and
   both are asserted here, so a future run that fills either one by machine and relabels it
   fails a test rather than shipping.

Each test that pins a contract also constructs the violating case and asserts it is
rejected, because a guard nobody has seen fail is a guard nobody has tested.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from vedagraph.domain import layer_figures as figures
from vedagraph.semantic.gold import _contains_model_data

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
GOLD_DIR = PROJECT_ROOT / "data" / "gold"


def _rows(path: pathlib.Path) -> list[dict]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


# ---------------------------------------------------------------------------
# Rule 1: the figures are derived from the measurement, not typed beside it
# ---------------------------------------------------------------------------


def test_the_disclosure_quotes_only_measured_figures() -> None:
    """Every integer in the sentence is a value of :data:`REVIEW_POPULATION`."""
    sentence = figures.adjudication_disclosure()
    quoted = {int(token) for token in _integers(sentence)}
    declared = set(figures.REVIEW_POPULATION.values())
    assert quoted <= declared, f"the sentence quotes a figure nothing measures: {quoted - declared}"


def test_a_figure_that_moves_moves_the_sentence(monkeypatch: pytest.MonkeyPatch) -> None:
    """BAD -> FAIL. A hand-typed 613 would survive this; a derived one cannot.

    The 613 in the shipped sentence was right and the "ten predicates" beside it was
    wrong, which is exactly what a typed figure looks like: correct on the day it was
    written and unowned afterwards.
    """
    before = figures.adjudication_disclosure()
    moved = dict(figures.REVIEW_POPULATION)
    moved["MODEL_ADJUDICATED_EDGES"] = 9999
    monkeypatch.setattr(figures, "REVIEW_POPULATION", moved)
    after = figures.adjudication_disclosure()
    assert "9999" in after, "the sentence is not built from the constants it claims to quote"
    assert before != after


def test_the_live_check_covers_the_review_figures() -> None:
    """A constant absent from ``measure``/``declared`` escapes the drift test silently."""
    assert "REVIEW_POPULATION" in figures.declared()
    assert "REVIEW_POPULATION" in figures.measure(_EmptySession())
    assert set(figures.declared()["REVIEW_POPULATION"]) == set(figures.REVIEW_POPULATION)


# ---------------------------------------------------------------------------
# Rule 2: a population sentence names every part of its population
# ---------------------------------------------------------------------------


def test_tier_c_is_stated_as_two_populations_not_one() -> None:
    """The 11 label-level edges must be in the sentence, not rounded out of it."""
    sentence = figures.adjudication_disclosure()
    assert str(figures.REVIEW_POPULATION["TIER_C_EDGES"]) in sentence
    assert str(figures.REVIEW_POPULATION["TIER_C_PASSAGE_ANCHORED"]) in sentence
    assert str(figures.REVIEW_POPULATION["TIER_C_LABEL_LEVEL"]) in sentence
    assert "UNREVIEWED" in sentence, (
        "the 11 label-level TIER_C edges carry review_state UNREVIEWED, and a sentence "
        "describing all of TIER_C as reviewed overstates them"
    )


def test_the_two_halves_of_tier_c_account_for_all_of_it() -> None:
    """An arithmetic identity, so a future third population cannot hide inside one."""
    f = figures.REVIEW_POPULATION
    assert f["TIER_C_PASSAGE_ANCHORED"] + f["TIER_C_LABEL_LEVEL"] == f["TIER_C_EDGES"]
    assert (
        f["TIER_C_PASSAGE_ANCHORED_YV"]
        + f["TIER_C_PASSAGE_ANCHORED_AV"]
        + f["TIER_C_PASSAGE_ANCHORED_RV"]
        == f["TIER_C_PASSAGE_ANCHORED"]
    )


def test_a_sentence_naming_only_the_passage_half_is_rejected() -> None:
    """BAD -> FAIL. The exact sentence that shipped, run through the same check."""
    shipped = (
        "TIER_C means MODEL_ADJUDICATED, not human-reviewed: 587 edges were re-read per "
        "passage by a model and accepted with a stated reason. All 587 are Yajurvedic "
        "(320) or Atharvavedic (267) and not one is Rigvedic."
    )
    assert not _states_both_halves(shipped)
    assert _states_both_halves(figures.adjudication_disclosure())


def test_model_adjudicated_is_not_confined_to_tier_c() -> None:
    """613 edges are MODEL_ADJUDICATED and only 587 of them became TIER_C.

    Quoting the TIER_C figure as the MODEL_ADJUDICATED one understates how much of this
    graph a model has touched, which is the direction that matters.
    """
    f = figures.REVIEW_POPULATION
    assert f["MODEL_ADJUDICATED_EDGES"] > f["TIER_C_PASSAGE_ANCHORED"]


# ---------------------------------------------------------------------------
# Rule 3: a model label is never a human label
# ---------------------------------------------------------------------------


def test_nothing_in_this_graph_claims_human_review() -> None:
    """The single most consequential claim the product makes about itself."""
    assert figures.REVIEW_POPULATION["HUMAN_REVIEWED_EDGES"] == 0
    assert "HUMAN_REVIEWED" in figures.adjudication_disclosure()
    assert "no human gold set" in figures.adjudication_disclosure()


def test_the_rigveda_semantic_gold_set_is_an_unannotated_scaffold() -> None:
    """120 rows, 0 annotations. Named a gold set and holding none.

    Asserted rather than assumed, because the failure mode is a process that checks for
    the file's existence instead of its contents and reports a gold set present.
    """
    rows = _rows(GOLD_DIR / "rigveda_semantic_gold_v1.jsonl")
    assert len(rows) == 120
    assert {row["annotator"] for row in rows} == {"UNANNOTATED"}
    assert not any(row["entities"] or row["relations"] for row in rows)
    assert not (GOLD_DIR / "semantic_gold_adjudication_rigveda_v1.jsonl").exists()
    assert not (GOLD_DIR / "rigveda_semantic_gold_v1.manifest.json").exists()


def test_the_theonym_reference_set_is_model_adjudicated_on_every_row() -> None:
    """575 rows by claude-opus-5. A legitimate reference set; never a human gold set."""
    rows = _rows(GOLD_DIR / "theonym_mention_gold_v1.jsonl")
    assert len(rows) == 575
    assert {row["annotator"] for row in rows} == {"MODEL_ADJUDICATED"}
    assert {row["annotator_model"] for row in rows} == {"claude-opus-5"}
    assert not any(str(row["annotator"]).upper().startswith("HUMAN") for row in rows)


def test_the_gold_harness_refuses_model_data(monkeypatch: pytest.MonkeyPatch) -> None:
    """BAD -> FAIL, GOOD -> PASS, on the guard that makes a machine-filled gold impossible.

    ``_contains_model_data`` is private and tested directly on purpose: it is the one
    mechanism standing between "no human annotator was available" and a gold file filled
    by the model whose output it exists to score.
    """
    human = {
        "passage_key": "VG:RV:SAK:M01:S005:V003",
        "annotator": "Himanshu",
        "entities": [{"surface": "agnim", "node_type": "DEITY"}],
        "relations": [],
    }
    assert not _contains_model_data(human)

    for polluted in (
        {**human, "confidence": 0.9},
        {**human, "entities": [{"surface": "agnim", "model": "claude-opus-5"}]},
        {**human, "relations": [{"candidate_assertion_id": "CA-1"}]},
        {**human, "entities": [{"nested": {"model_snapshot": "v3.2"}}]},
    ):
        assert _contains_model_data(polluted), f"model data passed the guard: {polluted}"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _integers(text: str) -> list[str]:
    out, buf = [], ""
    for char in text:
        if char.isdigit():
            buf += char
        elif buf:
            out.append(buf)
            buf = ""
    if buf:
        out.append(buf)
    return out


def _states_both_halves(sentence: str) -> bool:
    """Whether a sentence names both TIER_C populations rather than only the larger one."""
    f = figures.REVIEW_POPULATION
    return (
        str(f["TIER_C_EDGES"]) in sentence
        and str(f["TIER_C_PASSAGE_ANCHORED"]) in sentence
        and str(f["TIER_C_LABEL_LEVEL"]) in sentence
    )


class _EmptySession:
    """A session over an empty graph, used to compare key sets and never values."""

    def run(self, query: str, **parameters: object) -> _EmptyResult:
        return _EmptyResult()


class _EmptyResult:
    def single(self) -> None:
        return None

    def __iter__(self) -> object:
        return iter(())
