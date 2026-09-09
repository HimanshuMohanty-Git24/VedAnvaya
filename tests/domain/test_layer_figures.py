"""Assert that the figures the catalogue's caveats quote still match the graph.

This is the guard for a defect the V3.1 benchmark diagnosis found in shipped code: a
caveat asserting *"The second route returns zero, and that is the finding rather than a
gap"* while the same database showed 157 passages contradicting it. A caveat is the only
thing standing between a reader and a misleading answer, so a caveat quoting a stale figure
is a correctness defect and not a documentation one.

The offline tests here pin the *internal consistency* of the constants -- the parts that can
be wrong without a database. The live test compares them field by field against a real
graph and names whichever one moved.
"""

from __future__ import annotations

import os

import pytest

from vedagraph.domain import layer_figures as figures


def test_mentions_by_veda_sums_to_the_predicate_total() -> None:
    """A per-Veda breakdown that does not sum to its own total is already wrong."""
    assert (
        sum(figures.MENTIONS_DEVATA_BY_VEDA.values())
        == (figures.PREDICATE_TOTALS["MENTIONS_DEVATA"])
    )


def test_referent_certainty_buckets_sum_to_the_mention_layer() -> None:
    """Every mention edge is in exactly one bucket, so the three must partition it."""
    assert sum(figures.REFERENT_CERTAINTY.values()) == (figures.PREDICATE_TOTALS["MENTIONS_DEVATA"])


def test_the_certainty_split_is_three_way() -> None:
    """Two-way was a proxy for "is Rigvedic"; the third bucket is the V3.1 fix."""
    assert set(figures.REFERENT_CERTAINTY) == {
        "DEITY_CERTAIN",
        "DEITY_PROBABLE",
        "DEITY_AMBIGUOUS",
    }


def test_assertion_layers_sum_to_the_assertion_total() -> None:
    """The two layers must not be summed in a query, but they must account for the label."""
    assert (
        sum(figures.ASSERTION_LAYERS.values())
        == (figures.PREDICATE_TOTALS["HAS_SEMANTIC_ASSERTION"])
    )


def test_every_corpus_has_a_denominator() -> None:
    """Without one, a cross-corpus comparison cannot be normalised and will mislead."""
    assert set(figures.CORPUS_MANTRAS) == {"RV", "AV", "YV", "SV"}
    assert all(count > 0 for count in figures.CORPUS_MANTRAS.values())


def test_normalisation_reverses_the_naive_rudra_comparison() -> None:
    """The worked example the module docstring rests on, pinned as a test.

    Rudra is named in 128 Rigvedic and 41 Yajurvedic passages, which reads as Rudra being
    three times more Rigvedic. Normalised for corpus size it runs the other way, and that
    reversal is the Satarudriya effect the benchmark says was invisible.
    """
    assert figures.per_thousand(128, "RV") < figures.per_thousand(41, "YV")


def test_veda_breakdown_is_in_a_fixed_corpus_order_not_sorted_by_size() -> None:
    """So two caveats built from different layers can be read against each other."""
    rendered = figures.veda_breakdown({"SV": 1, "RV": 4, "YV": 2, "AV": 3})
    assert rendered == "RV 4, AV 3, YV 2, SV 1"


def test_declared_and_measured_have_the_same_shape() -> None:
    """A field present in one and not the other would silently escape the live check."""
    measured_keys = set(figures.measure(_EmptySession()))
    assert measured_keys == set(figures.declared())


class _EmptySession:
    """A session over an empty graph. Used only to compare key sets, never values."""

    def run(self, query: str, **parameters: object) -> _EmptyResult:
        return _EmptyResult()


class _EmptyResult:
    def single(self) -> None:
        return None

    def __iter__(self) -> object:
        return iter(())


@pytest.mark.live
@pytest.mark.skipif(
    not os.environ.get("VEDAGRAPH_LIVE_NEO4J"),
    reason="requires a populated Neo4j; set VEDAGRAPH_LIVE_NEO4J=1",
)
def test_declared_figures_match_the_live_graph() -> None:
    """The whole point of the module. Fails naming the field that moved.

    If this fails, do NOT edit the constant to make it green. Run ``measure`` against the
    graph, satisfy yourself the movement was intended, then update the constant *and* any
    caveat whose wording the new number falsifies.
    """
    from neo4j import GraphDatabase

    with (
        GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "vedagraph_dev")) as driver,
        driver.session() as session,
    ):
        measured = figures.measure(session)

    declared = figures.declared()
    drifted = {
        field: {"declared": declared[field], "measured": measured[field]}
        for field in declared
        if declared[field] != measured[field]
    }
    assert not drifted, f"caveat figures have drifted from the graph: {drifted}"
