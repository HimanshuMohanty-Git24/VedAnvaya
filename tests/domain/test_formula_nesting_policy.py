"""A formula frequency ranking has to say which nesting policy it applies.

GAP-FORMULA-003's declared closure test is two clauses. The first -- every formula either
has no strict-substring relation or carries an explicit nesting type -- holds on the live
graph and is measured in ``data/staging/final_closure_sprint/agent1/formula_nesting_audit
.json``: all 4,825 nodes carry ``formula_nesting_type`` and a recomputation of the
containment relation from the stored strings disagrees with the stored type on 0 of them.

The second clause did not hold, and this module is what makes it hold. ``cross_veda_formulas``
returns the thirty most frequent cross-Veda formulas and its caveat said only that formula
identity is a normalised-string match. Measured on the live graph, **26 of those 30 rows are
nested wordings** -- 22 NESTED_IN_ANOTHER and 4 NESTED_AND_CONTAINING -- so the ranking is
mostly one piece of phraseology at several lengths and nothing said so. That is the head of
the list, not its tail.
"""

from __future__ import annotations

import re

import pytest

from vedagraph.domain import layer_figures as figures
from vedagraph.domain.queries import QUERIES, DomainQuery

#: A query ranks formulas by frequency when it matches ``:Formula`` and orders on a count.
#: Deliberately a property of the Cypher rather than a hand-kept list of query names: a new
#: ranking added later is caught by the same predicate that catches these.
_FORMULA_MATCH = re.compile(r":Formula\b")
_FREQUENCY_ORDER = re.compile(
    r"ORDER BY[^\n]*\b(occurrences|occurrence_count|mantras|mantra_count|count)\b",
    re.IGNORECASE,
)


def ranks_formulas_by_frequency(query: DomainQuery) -> bool:
    return bool(_FORMULA_MATCH.search(query.cypher) and _FREQUENCY_ORDER.search(query.cypher))


def _rankings() -> list[DomainQuery]:
    return [query for query in QUERIES if ranks_formulas_by_frequency(query)]


def test_the_predicate_finds_the_rankings_that_exist() -> None:
    """If this ever returns nothing the rest of the module is vacuously green."""
    names = {query.name for query in _rankings()}
    assert names, "no formula frequency ranking was detected; the predicate has rotted"
    assert "cross_veda_formulas" in names


def test_every_formula_frequency_ranking_states_its_nesting_policy() -> None:
    """The closure test's second clause, as a test over the whole catalogue."""
    policy = figures.formula_nesting_policy()
    missing = [query.name for query in _rankings() if policy not in query.caveat]
    assert not missing, f"formula frequency rankings with no nesting policy: {missing}"


def test_the_predicate_fails_a_ranking_that_does_not_state_the_policy() -> None:
    """BAD -> FAIL. The same check, run against the caveat this replaced.

    Without this the test above proves only that the current strings contain a substring
    somebody put there; here the pre-fix wording is fed to the same predicate and must be
    rejected.
    """
    before = DomainQuery(
        name="cross_veda_formulas_before_the_fix",
        question="Which formulas occur across more than one Veda?",
        cypher="""
        MATCH (f:Formula) WHERE f.cross_veda
        RETURN f.display_form AS formula, f.occurrence_count AS occurrences
        ORDER BY occurrences DESC LIMIT 30
        """,
        caveat="Formula identity is a normalised-string match, not a tradition of reuse.",
    )
    assert ranks_formulas_by_frequency(before)
    assert figures.formula_nesting_policy() not in before.caveat


def test_a_query_that_does_not_rank_formulas_is_not_required_to_state_the_policy() -> None:
    """The predicate has to be able to say no, or it is not a predicate."""
    unrelated = DomainQuery(
        name="probe",
        question="probe",
        cypher="MATCH (d:Devata) RETURN d.display_label AS label ORDER BY label LIMIT 5",
    )
    assert not ranks_formulas_by_frequency(unrelated)


def test_the_policy_sentence_is_built_from_the_measured_figures() -> None:
    """A policy quoting a hand-typed share is the drift this repository keeps finding."""
    policy = figures.formula_nesting_policy()
    nesting = figures.FORMULA_NESTING
    assert f"{nesting['STRICT_SUBSTRING_OF_ANOTHER']:,}" in policy
    assert f"{nesting['FORMULAS']:,}" in policy
    for role in ("INDEPENDENT", "NESTED_IN_ANOTHER", "CONTAINS_ANOTHER", "NESTED_AND_CONTAINING"):
        assert role in policy
        assert f"{nesting[role]:,}" in policy


def test_the_four_nesting_types_partition_the_formula_population() -> None:
    """A type that does not partition would let a formula be counted twice or not at all."""
    nesting = figures.FORMULA_NESTING
    assert (
        nesting["INDEPENDENT"]
        + nesting["NESTED_IN_ANOTHER"]
        + nesting["CONTAINS_ANOTHER"]
        + nesting["NESTED_AND_CONTAINING"]
        == nesting["FORMULAS"]
    )
    assert nesting["TYPED"] == nesting["FORMULAS"], "an untyped formula fails clause one"
    assert (
        nesting["NESTED_IN_ANOTHER"] + nesting["NESTED_AND_CONTAINING"]
        == nesting["STRICT_SUBSTRING_OF_ANOTHER"]
    ), "the nested types must agree with the containment relation they describe"


def test_the_policy_names_the_surface_it_measured_on() -> None:
    """1,039, 984 and 1,103 are all correct figures for three different surfaces.

    A share published without its surface is how the same layer got audited as
    unreproducible once already.
    """
    assert "collapsed identity surface" in figures.formula_nesting_policy()


def test_the_policy_is_stated_in_the_formula_diffusion_response() -> None:
    """The endpoint that ranks families, asserted on the response and not on the source.

    Reading the module text would pass for a policy assigned to a variable nobody serves.
    This builds the response the client gets.
    """
    from vedagraph.api.services.insight_service import InsightService

    class _Repository:
        def run(self, cypher: str, /, **parameters: object) -> list[dict[str, object]]:
            if "MATCH (w:Work)" in cypher:
                return [
                    {
                        "veda": veda,
                        "work_id": f"VG:WORK:{veda}",
                        "traditional_name": veda,
                        "scope_honest_label": veda,
                        "scope": "COMPLETE",
                        "completeness": "COMPLETE",
                        "excluded_corpora": [],
                        "scope_source": "test",
                    }
                    for veda in ("RV", "SV", "YV", "AV")
                ]
            return []

        def run_one(self, cypher: str, /, **parameters: object) -> dict[str, object] | None:
            rows = self.run(cypher, **parameters)
            return rows[0] if rows else None

        def run_named(self, name: str, /, **overrides: object) -> list[dict[str, object]]:
            from vedagraph.domain.queries import QUERIES_BY_NAME

            return self.run(QUERIES_BY_NAME[name].cypher)

    response = InsightService(_Repository()).formula_diffusion(limit=5, offset=0)  # type: ignore[arg-type]
    served = " ".join(caveat.text for caveat in response.caveats)
    assert figures.formula_nesting_policy() in served


@pytest.mark.parametrize("role", ["NESTED_IN_ANOTHER", "NESTED_AND_CONTAINING"])
def test_the_nested_roles_are_non_empty(role: str) -> None:
    """A nesting type nothing carries is a vocabulary, not a classification."""
    assert figures.FORMULA_NESTING[role] > 0
