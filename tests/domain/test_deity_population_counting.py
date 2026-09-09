"""Every query that counts the ``Devata`` population must say which subjects it counts.

**Why this file exists.** Three successive adversarial passes found three strata of one
question -- *what counts as a deity* -- in the same query, each hidden beneath the last:

1. `deities_by_axis` ranked ``UNSPECIFIED`` as the top functional axis of the pantheon,
   101 against WARRIOR's 20, while its own caveat said those 101 "do not appear here".
2. With that fixed it ranked WARRIOR top at 20, of which only **3** were individual
   deities: 14 were PAIRs and 13 of the 20 were "Indra and X", so the figure was largely
   Indra counted eleven times through dyads.
3. With that fixed, ``FIRE_MEDIUM`` read 5 individual deities and was **2**, Agni having
   been counted four times as `Agni`, `Agni Jatavedas`, `Agni Pavamana` and
   `Agni the slayer of demons`.

Each fix was correct and each revealed the next, which is the signature of a missing
*contract* rather than three unrelated bugs. This is that contract. The `Devata` label
covers every subject the Anukramaṇī names as a hymn's addressee -- individual deities, dual
and group compounds, abstractions, and human patrons including a carpenter -- so a bare
count over it is not a count of deities and must not be presented as one.

The rule enforced: a query that AGGREGATES over `:Devata` must either constrain
`structure`, or return `structure` so the reader can constrain it. Queries keyed to one
named deity by parameter are exempt: they count that deity's edges, not a population.
"""

from __future__ import annotations

import re

from vedagraph.domain.queries import QUERIES, DomainQuery

#: Variables bound to the ``Devata`` label, e.g. ``(dv:Devata)`` -> ``dv``.
_DEVATA_BINDING = re.compile(r"\(\s*(\w+)\s*:Devata")

#: Naming a deity by parameter means the query is about that deity, not about the
#: population, so a structure breakdown would be noise.
_PARAMETERISED = re.compile(r"Devata\s*\{\s*entity_key:\s*\$", re.IGNORECASE)


def _aggregates_over_the_population(query: DomainQuery) -> bool:
    """True when the query counts DEVATA NODES, as opposed to counting anything else.

    Precision matters here, and the first version of this guard did not have it: any
    ``count(`` in a query that merely mentioned ``:Devata`` was flagged, which caught
    twelve queries of which most count PASSAGES -- ``ritual_profile`` counts the mantras
    naming a rite, not the deities in it. A guard that cries wolf gets an exemption list
    bolted onto it, and an exemption list is how this contract would quietly die. So the
    test looks for a count over a variable actually bound to ``:Devata``.
    """
    cypher = query.cypher
    if _PARAMETERISED.search(cypher):
        return False
    variables = set(_DEVATA_BINDING.findall(cypher))
    if not variables:
        return False
    return any(
        re.search(rf"count\s*\(\s*(?:DISTINCT\s+)?{variable}\s*\)", cypher)
        for variable in variables
    )


def _states_which_subjects(query: DomainQuery) -> bool:
    """True when the query constrains ``structure`` or hands it back to the reader."""
    return "structure" in query.cypher


def test_every_devata_population_count_states_which_subjects_it_counts() -> None:
    """A bare count over :Devata is not a count of deities.

    If this fails for a new query, the fix is one of two lines: add
    ``WHERE dv.structure = 'INDIVIDUAL'`` if the question is about deities, or return
    ``dv.structure`` if the question is about hymn addressees. Do NOT add the query to an
    exemption list -- the whole point is that the reader cannot tell which was meant.
    """
    offenders = [
        query.name
        for query in QUERIES
        if _aggregates_over_the_population(query) and not _states_which_subjects(query)
    ]
    assert offenders == [], (
        "these queries aggregate over the Devata population without saying which "
        f"subjects they count: {offenders}"
    )


def test_the_two_axis_leaderboards_agree_on_what_a_deity_is() -> None:
    """Q38 is served by two queries and they must not give different answers.

    They agreed for a while by coincidence rather than by construction:
    ``deity_widest_range`` gated on ``is_composite = false AND structure = 'INDIVIDUAL'``,
    and the first clause was exactly equivalent to the second only because no node happens
    to be INDIVIDUAL with ``is_composite`` true. One registry edit would have split Q38
    again with nothing to catch it. Worse, ``is_composite`` does not mean what its name
    suggests -- it means "has a recorded decomposition" and is false on 24 of the 38 PAIRs
    -- so it was never a compound filter at all.
    """
    by_axis = next(q for q in QUERIES if q.name == "deities_by_axis")
    widest = next(q for q in QUERIES if q.name == "deity_widest_range")

    for query in (by_axis, widest):
        assert "structure = 'INDIVIDUAL'" in query.cypher, query.name
        assert "EPITHET_VARIANT_OF" in query.cypher, query.name
        assert "is_composite" not in query.cypher, (
            f"{query.name} must not gate on is_composite: it means 'has a recorded "
            "decomposition', is false on 24 of 38 PAIRs, and made Q38's agreement a "
            "coincidence rather than a contract"
        )


def test_the_axis_ranking_resolves_epithet_variants() -> None:
    """Counting rows rather than resolved deities made FIRE_MEDIUM read 5 when it is 2."""
    by_axis = next(q for q in QUERIES if q.name == "deities_by_axis")
    assert "count(DISTINCT CASE WHEN dv.structure = 'INDIVIDUAL' THEN resolved_label END)" in (
        by_axis.cypher
    ), "the ranking column must count DISTINCT resolved labels, not rows"
    assert "individual_subjects" in by_axis.cypher, (
        "the unresolved row count must be returned beside the resolved one, so the gap "
        "between them is visible rather than silently corrected"
    )


def test_the_axis_query_does_not_rank_on_the_unranked_bucket() -> None:
    """UNSPECIFIED was returned as the top-ranked axis while the caveat denied it."""
    by_axis = next(q for q in QUERIES if q.name == "deities_by_axis")
    assert "ax.axis <> 'UNSPECIFIED'" in by_axis.cypher
    assert "ORDER BY individual_deities DESC" in by_axis.cypher
    assert "NO_AXIS_ASSIGNED" in by_axis.cypher, (
        "the excluded bucket must still be returned as a named non-axis row, or the 214 "
        "stop reconciling and the exclusion looks like data loss"
    )
