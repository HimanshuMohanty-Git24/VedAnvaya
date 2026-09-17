"""``DerivedMetric.scope_note`` must be measured, not declared.

This sentence has now been wrong twice, and the second time is the instructive one.

*First*, it said the Anukramaṇī attribution layer was Rigveda-only. That was false: a
second predicate, ``HAS_DEVATA_ASCRIPTION``, carries 4,816 Atharvavedic edges over 4,160
mantras.

*Second*, corrected to say ``HAS_DEVATA`` is Rigveda-only, it became **true and
inadequate**. The Atharvavedic derived-dedication import creates 882
``HAS_DEVATA_DERIVED`` edges, at which point the figure is still right, the sentence is
still literally true, and a reader still concludes that the Atharvaveda has no deity
attribution. 214 staged metric rows carry that sentence today.

A prose fix cannot survive that, because the next predicate is always one import away. So
the reach of the whole predicate family is measured at generation time and the sentence is
assembled from the measurement. These tests hold that property rather than any wording:

* the sentence names every predicate in the family and its measured reach;
* a predicate that gains a corpus widens the sentence with **no edit**;
* an unmeasured scope says so instead of falling back on a declaration;
* ``values``, ``method`` and ``scope_note`` describe the same predicate set, so the
  figure and the sentence cannot diverge.
"""

from __future__ import annotations

import contextlib
import os
from collections.abc import Iterator

import pytest

from vedagraph.domain.profiles import (
    ATTRIBUTION_PREDICATES,
    ATTRIBUTION_VEDAS,
    COUNTED_ATTRIBUTION_PREDICATES,
    DevataProfile,
    attribution_metrics,
    measure_attribution_scope,
)

RESOLVED = "HAS_DEVATA"
DERIVED = "HAS_DEVATA_DERIVED"
ASCRIPTION = "HAS_DEVATA_ASCRIPTION"


def _by_veda(scope: dict[str, list[str]] | None) -> str:
    profile = DevataProfile(
        entity_key="VG:DEVATA:INDRAH",
        display_label="Indra",
        attributed_mantras={"RV": 2869},
        attribution_layer_scope=scope or {},
    )
    metric = next(
        m for m in attribution_metrics(profile) if m.metric_name == "DEVATA_ATTRIBUTION_BY_VEDA"
    )
    assert metric.scope_note is not None
    return metric.scope_note


# ---------------------------------------------------------------------------
# The family is enumerated, and the three members are kept apart
# ---------------------------------------------------------------------------


def test_the_three_attribution_predicates_are_distinct_members_of_one_family() -> None:
    names = [name for name, _ in ATTRIBUTION_PREDICATES]
    assert names == [RESOLVED, DERIVED, ASCRIPTION]
    for _name, means in ATTRIBUTION_PREDICATES:
        assert means, "a predicate with no stated meaning collapses into its neighbour"


def test_only_the_resolved_predicate_is_counted() -> None:
    """The figure's basis, in one place, read by values, method and the note alike."""
    assert COUNTED_ATTRIBUTION_PREDICATES == (RESOLVED,)


def test_the_rigveda_only_constant_is_not_widened_to_cover_the_import() -> None:
    """The proposed follow-on, refused, with the reason pinned.

    Widening ``ATTRIBUTION_VEDAS`` to ``("RV", "AV")`` after the Atharvavedic import would
    make "HAS_DEVATA reaches AV" true in prose while that predicate still has no
    Atharvavedic edge -- the same defect in the other direction, and a collapse of three
    predicates into one. The import creates ``HAS_DEVATA_DERIVED``, not ``HAS_DEVATA``.
    """
    assert ATTRIBUTION_VEDAS == ("RV",)


# ---------------------------------------------------------------------------
# The sentence is assembled from the measurement
# ---------------------------------------------------------------------------


def test_the_note_names_every_predicate_and_its_measured_reach() -> None:
    note = _by_veda({RESOLVED: ["RV"], DERIVED: [], ASCRIPTION: ["AV"]})
    for name, _means in ATTRIBUTION_PREDICATES:
        assert name in note, f"{name} is not named in the published sentence"
    assert "HAS_DEVATA reaches RV" in note
    assert "HAS_DEVATA_DERIVED reaches no corpus" in note
    assert "HAS_DEVATA_ASCRIPTION reaches AV" in note


def test_a_predicate_that_gains_a_corpus_widens_the_sentence_with_no_edit() -> None:
    """The sequencing guard. This is the failure the import would otherwise cause.

    Same generator, same prose, one extra measured corpus -- and the published sentence
    stops implying that the Atharvaveda has no deity attribution.
    """
    before = _by_veda({RESOLVED: ["RV"], DERIVED: [], ASCRIPTION: ["AV"]})
    after = _by_veda({RESOLVED: ["RV"], DERIVED: ["AV"], ASCRIPTION: ["AV"]})
    assert "HAS_DEVATA_DERIVED reaches no corpus" in before
    assert "HAS_DEVATA_DERIVED reaches AV" in after
    # And the counted predicate is unchanged, so the figure has not silently widened.
    assert "counts HAS_DEVATA and nothing else" in before
    assert "counts HAS_DEVATA and nothing else" in after


def test_an_unmeasured_scope_refuses_to_declare_one() -> None:
    """BAD -> FAIL. A fallback here would be a validator that silently skips.

    The previous version of this sentence was a confident Rigveda-only claim with nothing
    behind it. An unmeasured build must say so rather than reproduce that.
    """
    note = _by_veda(None)
    assert "NOT measured" in note
    assert "reaches RV" not in note
    assert "Rigveda only" not in note


def test_the_note_never_claims_the_corpus_lacks_a_traditional_index() -> None:
    """The first defect, pinned so it cannot return under any measurement."""
    for scope in (
        {RESOLVED: ["RV"], DERIVED: [], ASCRIPTION: ["AV"]},
        {RESOLVED: ["RV"], DERIVED: ["AV"], ASCRIPTION: ["AV"]},
        {RESOLVED: ["RV"], DERIVED: [], ASCRIPTION: []},
    ):
        note = _by_veda(scope)
        assert "Anukramani attribution layer exists for the Rigveda only" not in note
        assert "no traditional index" in note  # it says the opposite, explicitly


def test_values_method_and_note_describe_the_same_predicate_set() -> None:
    """Figure right, sentence wrong is the failure mode. One source, three readers."""
    profile = DevataProfile(
        entity_key="VG:DEVATA:INDRAH",
        display_label="Indra",
        attributed_mantras={"RV": 2869},
        attribution_layer_scope={RESOLVED: ["RV"], DERIVED: ["AV"], ASCRIPTION: ["AV"]},
    )
    metric = next(
        m for m in attribution_metrics(profile) if m.metric_name == "DEVATA_ATTRIBUTION_BY_VEDA"
    )
    for counted in COUNTED_ATTRIBUTION_PREDICATES:
        assert metric.method is not None and counted in metric.method
        assert metric.scope_note is not None and counted in metric.scope_note
    # The derived predicate is named in the note as context and is NOT in the method,
    # because it is not what the figure counts.
    assert metric.method is not None and DERIVED not in metric.method


# ---------------------------------------------------------------------------
# The measurement itself, against the live graph
# ---------------------------------------------------------------------------


@contextlib.contextmanager
def _live_session() -> Iterator[object]:
    from neo4j import GraphDatabase

    with (
        GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "vedagraph_dev")) as driver,
        driver.session() as session,
    ):
        yield session


@pytest.mark.live
@pytest.mark.skipif(
    not os.environ.get("VEDAGRAPH_LIVE_NEO4J"),
    reason="requires a populated Neo4j; set VEDAGRAPH_LIVE_NEO4J=1",
)
def test_the_measured_scope_reports_every_member_including_the_empty_ones() -> None:
    """An absent key and an empty list mean different things; both must be reachable."""
    with _live_session() as session:
        scope = measure_attribution_scope(session)  # type: ignore[arg-type]
    assert set(scope) == {name for name, _ in ATTRIBUTION_PREDICATES}
    assert scope[RESOLVED] == ["RV"], scope
    # Measured, not assumed: the Atharvavedic descriptor layer is real and is why the
    # first version of this sentence was false.
    assert "AV" in scope[ASCRIPTION], scope


@pytest.mark.live
@pytest.mark.skipif(
    not os.environ.get("VEDAGRAPH_LIVE_NEO4J"),
    reason="requires a populated Neo4j; set VEDAGRAPH_LIVE_NEO4J=1",
)
def test_the_live_note_matches_the_live_graph() -> None:
    with _live_session() as session:
        scope = measure_attribution_scope(session)  # type: ignore[arg-type]
    note = _by_veda(scope)
    for name, _means in ATTRIBUTION_PREDICATES:
        reach = ", ".join(scope[name]) if scope[name] else "no corpus"
        assert f"{name} reaches {reach}" in note, (name, reach)
