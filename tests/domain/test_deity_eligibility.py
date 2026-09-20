"""The one documented deity-eligibility predicate, and the four ways it may fail.

GAP-ENTITY_COVERAGE-008. ``:Devata`` is the slot the Anukramani's deity apparatus projects
into, and it holds 22 human patrons and 7 danastuti gift-praise labels beside the deities.
The rule for excluding them existed in two staging scripts and a report, and the shipped
product surface had a fourth spelling -- ``structure <> 'HUMAN'`` -- which published
``eligible_deities: 192`` where the ruled population is 157.

Every test is paired BAD -> FAIL / GOOD -> PASS.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from vedagraph.domain import deity_eligibility as eligibility

_STRUCTURES = {
    "VG:DEVATA:INDRAH": "INDIVIDUAL",
    "VG:DEVATA:BARHIH": "INDIVIDUAL",
    "VG:DEVATA:HUMAN-ONE": "HUMAN",
    "VG:DEVATA:DANASTUTIH": "PATRON_PRAISE",
    "VG:DEVATA:SRADDHA": "ABSTRACT",
    "VG:DEVATA:ABHISAPAH": "ABSTRACT",
    "VG:DEVATA:ATMA": "ABSTRACT",
}

_RULINGS = {
    "VG:DEVATA:SRADDHA": {"ruling": "DEITY", "reason": "vocative throughout RV 10.151"},
    "VG:DEVATA:ABHISAPAH": {"ruling": "NOT_DEITY", "reason": "a curse, not an addressee"},
    "VG:DEVATA:ATMA": {"ruling": "UNDECIDED", "reason": "30 dedications; the call is open"},
}


def _devatas() -> list[dict[str, object]]:
    return [
        {"entity_key": key, "display_label": key.split(":")[-1], "structure": structure}
        for key, structure in _STRUCTURES.items()
    ]


def test_the_rulings_produce_one_typed_row_per_node() -> None:
    rows = eligibility.rulings_for(_devatas(), dict(_RULINGS))
    by_key = {row.entity_key: row for row in rows}
    assert len(rows) == len(_STRUCTURES)
    assert by_key["VG:DEVATA:INDRAH"].is_deity
    assert not by_key["VG:DEVATA:HUMAN-ONE"].is_deity
    assert by_key["VG:DEVATA:HUMAN-ONE"].non_deity_kind == "HUMAN_PATRON"
    assert by_key["VG:DEVATA:DANASTUTIH"].non_deity_kind == "DANASTUTI_GIFT_PRAISE"
    assert by_key["VG:DEVATA:ABHISAPAH"].non_deity_kind == "ABSTRACTION_NOT_AN_ADDRESSEE"
    assert by_key["VG:DEVATA:SRADDHA"].is_deity
    assert every_row_has_a_reason(rows)


def every_row_has_a_reason(rows: list[eligibility.EligibilityRow]) -> bool:
    return all(row.reason for row in rows)


def test_undecided_is_kept_and_recorded_not_dropped() -> None:
    """An undecided label removed is a decision made by default."""
    rows = eligibility.rulings_for(_devatas(), dict(_RULINGS))
    atma = next(row for row in rows if row.entity_key == "VG:DEVATA:ATMA")
    assert atma.is_deity
    assert atma.ruling == "UNDECIDED"
    assert atma.non_deity_kind is None
    assert eligibility.check_rows(rows)["undecided_kept"] == ["VG:DEVATA:ATMA"]


def test_a_ruling_that_matches_nothing_raises() -> None:
    """The guard that earned itself: SAMJNANAM against the graph's SANJNANAM.

    That run silently applied 27 of 28 rulings and reported 158 eligible instead of 157.
    BAD: an orphaned key, and a missing key. GOOD: exact correspondence.
    """
    orphaned = dict(_RULINGS)
    orphaned["VG:DEVATA:SAMJNANAM"] = {"ruling": "NOT_DEITY", "reason": "misspelled key"}
    with pytest.raises(eligibility.RulingCoverageError, match="SAMJNANAM"):
        eligibility.rulings_for(_devatas(), orphaned)

    missing = {k: v for k, v in _RULINGS.items() if k != "VG:DEVATA:ATMA"}
    with pytest.raises(eligibility.RulingCoverageError, match="ATMA"):
        eligibility.rulings_for(_devatas(), missing)

    eligibility.rulings_for(_devatas(), dict(_RULINGS))  # GOOD: does not raise


def test_a_ritual_implement_may_never_be_excluded() -> None:
    """Katyayana's opening sutra admits implements as pratimabhuta.

    BAD: barhih typed HUMAN by a contamination sweep. The gate must catch it, because
    "Agent 15 must not treat Yajurvedic ritual implements as contamination" is a constraint
    a silent filter has no way to honour.
    """
    devatas = _devatas()
    good = eligibility.check_rows(eligibility.rulings_for(devatas, dict(_RULINGS)))
    assert good["ritual_implements_retained"]

    contaminated = [
        dict(row, structure="HUMAN") if row["entity_key"] == "VG:DEVATA:BARHIH" else row
        for row in devatas
    ]
    bad = eligibility.check_rows(eligibility.rulings_for(contaminated, dict(_RULINGS)))
    assert not bad["ritual_implements_retained"]
    assert bad["ritual_implements_wrongly_excluded"] == ["VG:DEVATA:BARHIH"]
    assert not bad["passes"]


def test_an_out_of_vocabulary_ruling_raises() -> None:
    """BAD: a ruling file inventing a fourth verdict. The enum is closed on purpose."""
    payload = {"rulings": [{"key": "VG:DEVATA:SRADDHA", "ruling": "PROBABLY", "reason": "x"}]}
    path = pathlib.Path(
        pytest.importorskip("tempfile").mkdtemp(), "rulings.json"
    )
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(eligibility.RulingCoverageError, match="PROBABLY"):
        eligibility.load_abstract_rulings(path)


def test_the_shipped_capability_query_uses_the_documented_predicate() -> None:
    """The defect on the public surface: `eligible_deities: 192`.

    ``domain/queries.py`` excluded ``structure='HUMAN'`` and nothing else, so the figure
    ``/api/v1/insights/capabilities`` published was 35 above the ruled population and 7
    above even the crude all-abstractions-removed one.
    """
    from vedagraph.domain.queries import QUERIES

    query = next(q for q in QUERIES if q.name == "deity_community_capability")
    # Whitespace-normalised: the query line-wraps the predicate, and a test that demanded
    # one physical line would be testing the formatter.
    flat = " ".join(query.cypher.split())
    # The FINAL predicate, not the transitional shim. This asserted
    # ``eligible_predicate("d")``, which falls back to a structure test when ``is_deity`` is
    # null -- correct while the property was landing, and a second eligibility predicate
    # once it had landed. The module states its own removal condition: when no :Devata has
    # a null is_deity, use ELIGIBLE_DEITY_PREDICATE. Measured 214 of 214 ruled, 0 unruled,
    # so the condition is met and the shim is gone from every shipped query.
    assert eligibility.ELIGIBLE_DEITY_PREDICATE in flat
    assert "NOT coalesce(d.structure" not in flat, (
        "the transitional shim is back in a shipped query; that is a second eligibility "
        "predicate, which is the whole of GAP-ENTITY_COVERAGE-008"
    )
    assert "structure, 'UNSPECIFIED') <> 'HUMAN'" not in query.cypher
    assert "157" in query.caveat, "the caveat must state the figure the predicate produces"
    assert "192" in query.caveat, "and the figure it replaces, or nobody can tell it moved"
    assert "devatas_without_an_eligibility_ruling" in query.cypher


def test_the_shim_never_reads_a_property_the_graph_may_not_hold() -> None:
    """The sequencing hazard, made a test.

    A shipped query that gates on ``is_deity = true`` before the property lands does not
    error -- Neo4j returns null, the WHERE drops every row, and the endpoint answers with an
    empty result that reads as a finding. That is the exact failure
    ``tests/api/test_cypher_property_hygiene.py`` was written for, and the first version of
    this change reproduced it: ``/api/v1/insights/capabilities?question=23`` returned a null
    ``pairwise_co_occurrence_edges`` because the whole row disappeared.

    The shim is GONE, and this test now guards its absence rather than its behaviour. Its
    own removal condition -- no :Devata with a null ``is_deity`` -- has been met (214 of 214
    ruled), and while it remained it was a second eligibility predicate disagreeing with the
    ruling on 29 of the 214 nodes.

    What is still asserted is the part that made the shim necessary: the ruling must cover
    every node, so that gating on ``is_deity = true`` cannot silently empty a result.
    """
    assert not hasattr(eligibility, "eligible_predicate"), (
        "the transitional shim is back. Its fallback admits the 28 abstractions ruled "
        "ABSTRACTION_NOT_AN_ADDRESSEE and excludes the dog the ruling admits, so a query "
        "using it disagrees with every deity surface on 29 of the 214 nodes."
    )

    rows = eligibility.rulings_for(_devatas(), dict(_RULINGS))
    ruled = {row.entity_key: row.is_deity for row in rows}
    # The precondition the shim existed to cover: every node carries a ruling, so nothing
    # falls through to a null and disappears from a WHERE.
    assert set(ruled) == set(_STRUCTURES), (
        "a devata-slot entry carries no ruling, so `is_deity = true` would drop it silently"
    )
    for key, structure in _STRUCTURES.items():
        if structure in ("HUMAN", "PATRON_PRAISE"):
            assert ruled[key] is False, key


def test_the_real_ruling_file_is_the_one_copy_of_the_judgement() -> None:
    """Loaded, never re-derived here: 9 DEITY, 28 NOT_DEITY, 5 UNDECIDED over 42 labels."""
    rulings = eligibility.load_abstract_rulings()
    assert len(rulings) == 42
    counts: dict[str, int] = {}
    for value in rulings.values():
        counts[value["ruling"]] = counts.get(value["ruling"], 0) + 1
    assert counts == {"DEITY": 9, "NOT_DEITY": 28, "UNDECIDED": 5}
    assert all(value["reason"] for value in rulings.values())
