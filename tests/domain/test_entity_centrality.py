"""Contract tests for stored entity centrality and the concept-layer rank correlation.

Offline. What matters here is arithmetic and honesty, both decidable without a database:
that Spearman handles ties the way Spearman requires, that a correlation over too few
shared members refuses rather than returning a number, that the layer choice is declared
with a reason, and that bridge centrality is typed as absent rather than stored as a zero.
"""

from __future__ import annotations

from typing import Any

from vedagraph.domain.entity_centrality import (
    _WRITE_QUERY,
    AUTHORITATIVE_LAYER,
    AUTHORITY_BASIS,
    RIVAL_LAYER,
    _ranks,
    join_key_scores,
    load,
    rank_correlation,
)


def test_identical_rankings_correlate_perfectly() -> None:
    scores = {"a": 10.0, "b": 5.0, "c": 1.0}
    result = rank_correlation(scores, dict(scores))
    assert result["spearman_rho"] == 1.0
    assert result["shared_members"] == 3


def test_reversed_rankings_correlate_negatively() -> None:
    result = rank_correlation({"a": 3.0, "b": 2.0, "c": 1.0}, {"a": 1.0, "b": 2.0, "c": 3.0})
    assert result["spearman_rho"] == -1.0


def test_ties_are_averaged_not_broken_arbitrarily() -> None:
    """Document frequencies collide often; integer ranking would invent an order.

    Three tied values occupy ranks 1, 2, 3 and must all be reported as 2.0. Breaking the
    tie by key would create an ordering the data does not support and then correlate
    against it.
    """
    assert _ranks({"a": 5.0, "b": 5.0, "c": 5.0}) == {"a": 2.0, "b": 2.0, "c": 2.0}
    assert _ranks({"a": 9.0, "b": 5.0, "c": 5.0}) == {"a": 1.0, "b": 2.5, "c": 2.5}


def test_too_few_shared_members_refuses_rather_than_returning_a_number() -> None:
    """A rho over two shared members is not evidence of agreement and cannot say so."""
    result = rank_correlation({"a": 1.0, "b": 2.0}, {"a": 1.0, "z": 2.0})
    assert result["verdict"] == "INSUFFICIENT_OVERLAP"
    assert result["spearman_rho"] is None


def test_membership_difference_is_reported_apart_from_disagreement() -> None:
    """135 entities absent from the rival layer are not 135 disagreements."""
    result = rank_correlation(
        {"a": 3.0, "b": 2.0, "c": 1.0, "d": 0.5}, {"a": 3.0, "b": 2.0, "c": 1.0}
    )
    assert result["spearman_rho"] == 1.0
    assert result["only_in_authoritative"] == 1
    assert result["only_in_rival"] == 0


def test_the_join_drops_entities_with_no_sanskrit_label_rather_than_matching_english() -> None:
    """A rho over a bad join reads as disagreement when it means the join failed."""
    joined = join_key_scores(
        {"k1": 10.0, "k2": 5.0},
        {"k1": "fire (agni)", "k2": "wealth"},
    )
    assert joined == {"agni": 10.0}


def test_the_authoritative_layer_is_declared_with_a_stated_reason() -> None:
    """An undeclared layer makes centrality a statement about annotation history."""
    assert AUTHORITATIVE_LAYER == "MENTIONS_ENTITY"
    assert RIVAL_LAYER == "ABOUT_CONCEPT"
    assert "Sanskrit" in AUTHORITY_BASIS
    assert len(AUTHORITY_BASIS) > 200, "a one-line reason is not a stated reason"


def test_bridge_centrality_is_typed_absent_and_never_stored_as_zero() -> None:
    """No community structure exists, so a zero column would read as a ranking."""
    assert "NOT_BUILT" in _WRITE_QUERY
    assert "centrality_bridging" in _WRITE_QUERY
    assert "e.centrality_bridging = 0" not in _WRITE_QUERY


def test_the_stored_score_names_its_measure_and_its_layer() -> None:
    """Without both, the number cannot be reproduced or challenged."""
    assert "e.centrality_measure = 'DEGREE_OVER_PASSAGE_CO_MENTION'" in _WRITE_QUERY
    assert "e.centrality_layer = $layer" in _WRITE_QUERY


class _Result:
    def __init__(self, value: int) -> None:
        self._value = value

    def single(self) -> dict[str, int]:
        return {"c": self._value}

    def __iter__(self) -> Any:
        return iter(())


class _FakeSession:
    def __init__(self, count: int) -> None:
        self.statements: list[str] = []
        self._count = count

    def run(self, query: str, **parameters: Any) -> _Result:
        self.statements.append(query)
        return _Result(self._count)


def test_the_metric_is_not_marked_internal() -> None:
    """All 1,071 pre-existing DerivedMetric nodes are product nodes; this must match.

    Marking it ``:Internal`` would hide it from every product query -- including the one
    that exists to report it -- while every loader reported success.
    """
    session = _FakeSession(count=1)
    load(
        session,
        {
            "rows": [{"entity_key": "k", "centrality_degree": 1.0, "centrality_share": 1.0}],
            "correlation": {"spearman_rho": 0.9, "shared_members": 91},
            "labels": {"k": "fire (agni)"},
        },
    )
    metric = next(s for s in session.statements if "DerivedMetric" in s)
    assert "m:Internal" not in metric
    assert "m.interpretation = 'NONE'" in metric
