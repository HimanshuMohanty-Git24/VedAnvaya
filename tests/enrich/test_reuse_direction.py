"""Directed textual reuse: what the instrument asserts, and what it refuses.

GAP-CROSS_VEDA-001. One corpus pair carried a direction and all 1,684 of its edges carried
the same sentence explaining it, which is a statement about the class and not about any
edge. These tests pin the properties that make the replacement worth having: the evidence
varies per edge, the instrument reproduces the one direction that has an independent
answer, and a pair it cannot decide is refused with a measurement rather than left silent.
"""

from __future__ import annotations

import collections
import json
import pathlib

import pytest

from vedagraph.enrich.reuse_direction import (
    COMPILATION_SHARE_FLOOR,
    MEDIATION_REFUSAL_FLOOR,
    REFUSAL_EDGE_CONTRADICTS,
    REFUSAL_MEDIATED,
    REFUSAL_UNIT_GRANULARITY,
    SCOPE_CONSISTENCY_FLOOR,
    SCOPE_POWER_FLOOR,
    SHARE_MARGIN,
    UNIT_GRANULARITY_CEILING,
    VersePair,
    measure_directions,
    measure_pair,
    mediation_share,
    top_division,
)

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
STAGED = (
    PROJECT_ROOT
    / "data"
    / "staging"
    / "final_closure_sprint"
    / "agent1"
    / "reuse_direction_edges.jsonl"
)
STAGED_PAIRS = STAGED.with_name("reuse_direction_pairs.jsonl")


#: Verses per synthetic unit. Small on both sides, so the granularity precondition is not
#: what any of these cases is testing.
_UNIT = 5


def _compilation(prefix_a: str, prefix_b: str, count: int) -> list[VersePair]:
    """A synthetic compiler: corpus A's units are wholly made of B's scattered verses.

    Each A unit holds :data:`_UNIT` verses and every one of them has a counterpart, so A's
    counterpart share is 1.0. Each B unit contributes one verse of its :data:`_UNIT`, so
    B's share is 0.2 -- the asymmetry a compiler leaves behind.
    """
    return [
        VersePair(
            left_veda=prefix_a,
            left_key=f"VG:{prefix_a}:X:U{index // _UNIT:03d}:V{index % _UNIT:03d}",
            left_unit=f"VG:{prefix_a}:X:U{index // _UNIT:03d}",
            right_veda=prefix_b,
            right_key=f"VG:{prefix_b}:X:U{index:04d}:V000",
            right_unit=f"VG:{prefix_b}:X:U{index:04d}",
        )
        for index in range(count)
    ]


def _sizes(pairs: list[VersePair], compiler_unit: int, source_unit: int) -> dict[str, int]:
    sizes: dict[str, int] = {}
    for pair in pairs:
        sizes[pair.left_unit] = compiler_unit
        sizes[pair.right_unit] = source_unit
    return sizes


def test_a_unit_made_of_counterparts_points_at_the_unit_that_is_not() -> None:
    """GOOD -> PASS. The whole instrument in one synthetic case."""
    pairs = _compilation("SV", "RV", SCOPE_POWER_FLOOR + 20)
    sizes = _sizes(pairs, compiler_unit=_UNIT, source_unit=_UNIT)
    verdict, rows = measure_pair(pairs, "RV-SV", sizes)
    assert verdict.status == "DIRECTED"
    assert {row.verdict for row in rows} == {"SV->RV"}
    assert all(row.subject_key.startswith("VG:SV") for row in rows if row.subject_key)


def test_two_units_covered_alike_receive_no_direction() -> None:
    """BAD -> FAIL for the naive version: symmetric coverage must not produce a coin flip."""
    pairs = [
        VersePair(
            "AV",
            f"VG:AV:X:U01:V{i:03d}",
            "VG:AV:X:U01",
            "YV",
            f"VG:YV:X:U01:V{i:03d}",
            "VG:YV:X:U01",
        )
        for i in range(1, 200)
    ]
    sizes = {"VG:AV:X:U01": 199, "VG:YV:X:U01": 199}
    verdict, rows = measure_pair(pairs, "AV-YV", sizes)
    assert verdict.status != "DIRECTED"
    assert {row.verdict for row in rows} == {"UNDIRECTED"}
    assert all(row.reason for row in rows), "a refusal without a reason is silence"


def test_a_corpus_whose_units_are_too_large_is_refused_before_measurement() -> None:
    """The Yajurvedic case: an adhyaya is not comparable with a three-verse decade."""
    pairs = _compilation("YV", "RV", 150)
    sizes = _sizes(pairs, compiler_unit=UNIT_GRANULARITY_CEILING + 30, source_unit=_UNIT)
    verdict, _rows = measure_pair(pairs, "RV-YV", sizes)
    assert verdict.status == REFUSAL_UNIT_GRANULARITY
    assert f"{UNIT_GRANULARITY_CEILING}" in verdict.note


def test_a_pair_mediated_by_a_third_corpus_is_refused_with_its_share() -> None:
    """Both sides are versions of one Rigvedic verse, so they share the RV and not each other."""
    mediated = []
    for index in range(1, 40):
        av = f"VG:AV:X:U{index:02d}:V001"
        sv = f"VG:SV:X:U{index:02d}:V001"
        rv = f"VG:RV:X:U{index:02d}:V001"
        mediated.append(
            VersePair("AV", av, f"VG:AV:X:U{index:02d}", "SV", sv, f"VG:SV:X:U{index:02d}")
        )
        mediated.append(
            VersePair("AV", av, f"VG:AV:X:U{index:02d}", "RV", rv, f"VG:RV:X:U{index:02d}")
        )
        mediated.append(
            VersePair("RV", rv, f"VG:RV:X:U{index:02d}", "SV", sv, f"VG:SV:X:U{index:02d}")
        )
    share = mediation_share(mediated, "AV-SV")
    assert share == pytest.approx(1.0)
    assert share >= MEDIATION_REFUSAL_FLOOR
    sizes = {pair.left_unit: 4 for pair in mediated} | {pair.right_unit: 4 for pair in mediated}
    verdict, rows = measure_pair(mediated, "AV-SV", sizes)
    assert verdict.status == REFUSAL_MEDIATED
    assert all(row.reason == REFUSAL_MEDIATED for row in rows)


def test_a_pair_sharing_the_mediating_corpus_is_never_called_mediated_by_itself() -> None:
    pairs = _compilation("SV", "RV", 10)
    assert mediation_share(pairs, "RV-SV") == 0.0


def test_a_unanimous_scope_with_no_power_is_not_trusted() -> None:
    """Four unanimous edges are unanimous about nothing."""
    pairs = _compilation("SV", "RV", 4)
    sizes = _sizes(pairs, compiler_unit=_UNIT, source_unit=_UNIT)
    verdict, rows = measure_pair(pairs, "RV-SV", sizes)
    assert verdict.status != "DIRECTED"
    assert verdict.decisions < SCOPE_POWER_FLOOR
    assert {row.verdict for row in rows} == {"UNDIRECTED"}


def test_a_scope_that_clears_both_floors_survives_a_pair_that_does_not() -> None:
    """The subdivision step, which is how a second pair was found without naming it.

    One division of the compiling corpus is a real compilation; the rest is noise pointing
    the other way. The pair as a whole must fail and the division must survive.
    """
    signal = [
        VersePair(
            "AV",
            f"VG:AV:SAU:K20:S{i:03d}:V001",
            f"VG:AV:SAU:K20:S{i:03d}",
            "RV",
            f"VG:RV:SAK:M{i % 9 + 1:02d}:S{i:03d}:V001",
            f"VG:RV:SAK:M{i % 9 + 1:02d}:S{i:03d}",
        )
        for i in range(1, SCOPE_POWER_FLOOR + 30)
    ]
    noise = [
        VersePair(
            "AV",
            f"VG:AV:SAU:K05:S{i:03d}:V001",
            f"VG:AV:SAU:K05:S{i:03d}",
            "RV",
            f"VG:RV:SAK:M10:S085:V{i:03d}",
            "VG:RV:SAK:M10:S085",
        )
        for i in range(1, 60)
    ]
    sizes: dict[str, int] = {}
    for pair in signal:
        sizes[pair.left_unit] = 1
        sizes[pair.right_unit] = 10
    for pair in noise:
        sizes[pair.left_unit] = 10
        sizes[pair.right_unit] = 59
    verdict, rows = measure_pair(signal + noise, "AV-RV", sizes)
    assert verdict.status == "DIRECTED"
    assert verdict.scopes and all(":K20" in scope for scope in verdict.scopes)
    directed = [row for row in rows if row.verdict != "UNDIRECTED"]
    assert directed and all(":K20:" in (row.subject_key or "") for row in directed)


def test_the_floors_are_the_documented_ones() -> None:
    """A threshold that drifts from its docstring is a threshold nobody can audit."""
    assert COMPILATION_SHARE_FLOOR == 0.5
    assert SHARE_MARGIN == 0.25
    assert SCOPE_POWER_FLOOR == 100
    assert SCOPE_CONSISTENCY_FLOOR == 0.90


def test_top_division_reads_the_first_structural_field() -> None:
    assert top_division("VG:AV:SAU:K20:S001:V003") == "K20"
    assert top_division("VG:RV:SAK:M10:S085:V047") == "M10"
    assert top_division("SHORT") == "SHORT"


def test_every_edge_of_every_pair_gets_exactly_one_row() -> None:
    """Silence is the failure mode this layer exists to remove."""
    pairs = _compilation("SV", "RV", 30) + _compilation("AV", "YV", 20)
    sizes = {}
    for pair in pairs:
        sizes[pair.left_unit] = _UNIT
        sizes[pair.right_unit] = _UNIT
    verdicts, rows = measure_directions(pairs, sizes)
    assert len(rows) == len(pairs)
    assert {verdict.pair for verdict in verdicts} == {"RV-SV", "AV-YV"}
    assert all(row.verdict == "UNDIRECTED" or row.reason is None for row in rows)
    assert all(row.reason is not None for row in rows if row.verdict == "UNDIRECTED")


# -- the real artifact -------------------------------------------------------


def _staged() -> list[dict[str, object]]:
    if not STAGED.exists():
        pytest.skip("agent 1 staging not built; run scripts/agent1_final_closure.py")
    with STAGED.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def test_the_real_layer_does_not_carry_one_constant_on_every_directed_edge() -> None:
    """The defect, stated as a test: a per-edge record that never varies is a constant."""
    rows = [row for row in _staged() if row["verdict"] != "UNDIRECTED"]
    assert rows, "no directed edge was measured"
    digests = {row["evidence_digest"] for row in rows}
    assert len(digests) > 1
    assert len(digests) > len(rows) / 10, (
        "fewer than one distinct measurement per ten directed edges is a constant "
        "wearing a per-edge shape"
    )


def test_the_real_layer_reaches_more_than_one_corpus_pair() -> None:
    """GAP-CROSS_VEDA-001's declared closure test, measured on the staged layer."""
    directed = {row["pair"] for row in _staged() if row["verdict"] != "UNDIRECTED"}
    assert len(directed) > 1, directed


def test_the_instrument_reproduces_the_one_direction_that_has_an_outside_answer() -> None:
    """Calibration. The Samavedic direction is established independently of this measure.

    The Kauthuma Arcika is an arrangement of Rigvedic verses. The instrument knows nothing
    about that, so its agreement is a check on the instrument rather than on the Samaveda,
    and its disagreements are kept in view.
    """
    rows = [row for row in _staged() if row["pair"] == "RV-SV"]
    verdicts = collections.Counter(str(row["verdict"]) for row in rows)
    assert verdicts["SV->RV"] > 1_000
    assert verdicts["RV->SV"] == 0, "no edge may be stored against the established direction"
    contradicting = [row for row in rows if row["reason"] == REFUSAL_EDGE_CONTRADICTS]
    assert contradicting, "the instrument's disagreements must be recorded, not dropped"
    assert len(contradicting) < len(rows) * 0.05


def test_every_refused_pair_states_a_measured_reason() -> None:
    if not STAGED_PAIRS.exists():
        pytest.skip("agent 1 staging not built")
    with STAGED_PAIRS.open(encoding="utf-8") as handle:
        pairs = [json.loads(line) for line in handle]
    assert len(pairs) == 6
    for row in pairs:
        assert row["note"], row["pair"]
        if row["status"] != "DIRECTED":
            assert row["status"].startswith("REFUSED_"), row
            assert any(char.isdigit() for char in row["note"]), (
                f"{row['pair']} is refused with prose and no measurement"
            )
