"""The counts the query catalogue's caveats quote, in one place, with their measurements.

**Why this module exists.** Every caveat in :mod:`vedagraph.domain.queries` quotes figures --
how many edges a predicate carries, how they split by Veda, how many are ambiguous -- and
those figures were written by hand into thirty-odd strings. They drifted. Measured at the
V3.1 audit, the catalogue asserted ``MENTIONS_DEVATA`` at 16,261 edges against a live 17,165,
and ``DEITY_AMBIGUOUS`` at 8,485 against a live 8,825.

Drift in a caveat is not a cosmetic defect, because the caveat is the only thing standing
between a reader and a misleading answer. The V3.1 benchmark diagnosis found the worst case:
``agni_and_indra_together``'s caveat asserted *"The second route returns zero, and that is
the finding rather than a gap"* while the same database showed Agni and Indra named in the
same verse in 157 passages across all four Vedas. A shipped statement contradicted by the
shipped data is worse than no statement, because it converts a gap into a false finding.

So the figures live here as named constants, each paired with the Cypher that measures it,
and :func:`measure` re-derives every one of them from a live session.
``tests/domain/test_layer_figures.py`` asserts that the constants equal the measurement, so
a layer that changes size fails a test instead of quietly making a caveat lie.

**Editing rule.** Do not hand-edit a constant to make a test pass. Run :func:`measure`
against the graph, check that the movement is one you intended, and paste the measured
values -- then fix any caveat whose *wording* the new numbers falsify. A number that moved
because a layer grew is fine; a number that moved because a layer broke is the thing this
module exists to surface.
"""

from __future__ import annotations

from typing import Any, Final, Protocol


class Session(Protocol):
    def run(self, query: str, **parameters: Any) -> Any: ...


#: Mantra counts per corpus. These are the denominators for every normalised comparison:
#: a raw per-Veda count is not comparable across corpora that differ by a factor of six,
#: and comparing the totals is one of the ways a deity looks Rigvedic when it is not.
CORPUS_MANTRAS: Final[dict[str, int]] = {
    "RV": 10_552,
    "AV": 5_839,
    "YV": 1_975,
    "SV": 1_844,
}

#: Total edges per predicate, for the predicates a caveat names.
PREDICATE_TOTALS: Final[dict[str, int]] = {
    "MENTIONS_DEVATA": 17_165,
    "HAS_DEVATA": 10_558,
    "HAS_RISHI": 17_889,
    "HAS_CHANDAS": 16_331,
    "MENTIONS_LEMMA": 9_000,
    "HAS_SEMANTIC_ASSERTION": 4_865,
    "PERFORMS_ACTION": 441,
    "IS_ASKED_TO": 224,
    # 28,223 and not 28,227: the V3.1 ritual pass withdrew 11 rtvij- edges from hotr
    # (a generic officiant is not an office) and moved 14 adhvaryu forms to their own
    # node, while the material-culture pass added 5 aliases that matched 7 verses.
    "MENTIONS_ENTITY": 28_223,
    # 24,969 and not 26,437: adversarial finding F-7 retired 1,468 edges that sat
    # under a second run_id whose output no committed artifact asserts. The figure now
    # reconciles exactly against the artifact: 46,508 rows minus 21,539 english-only
    # (retired by V3) = 24,969.
    "ABOUT_CONCEPT": 24_969,
}

#: ``MENTIONS_DEVATA`` by corpus. The only deity predicate that reaches all four, which is
#: why it exists and why the catalogue must join on it rather than on ``HAS_DEVATA``.
MENTIONS_DEVATA_BY_VEDA: Final[dict[str, int]] = {
    "RV": 10_284,
    "AV": 3_582,
    "YV": 1_964,
    "SV": 1_335,
}

#: Referent certainty on the deity mention layer. Three-way as of V3.1: the two-way split
#: it replaced was a function of extraction path rather than of verse context, so
#: ``DEITY_CERTAIN`` meant "came from the Rigvedic lemma annotation" and a reader who
#: filtered to it got a Rigveda-only answer while believing they had filtered for accuracy.
REFERENT_CERTAINTY: Final[dict[str, int]] = {
    "DEITY_CERTAIN": 8_340,
    "DEITY_PROBABLE": 2_019,
    "DEITY_AMBIGUOUS": 6_806,
}

#: The two layers inside the ``SemanticAssertion`` label, which must never be summed.
ASSERTION_LAYERS: Final[dict[str, int]] = {
    "MORPHOLOGY_RULE": 2_406,
    "MODEL_EXTRACTION": 2_459,
}

#: Rigvedic mantras carrying more than one attributed deity. Load-bearing for the
#: Agni-and-Indra question: the Anukramani names one addressee per mantra, so a
#: co-attribution zero is a property of that apparatus and not of the text.
MULTI_DEVATA_MANTRAS: Final[int] = 6

#: Passages naming both Agni and Indra, by corpus, via the four-Veda mention layer. The
#: figure whose absence let a caveat call a gap a finding.
AGNI_INDRA_CO_MENTION_BY_VEDA: Final[dict[str, int]] = {
    "RV": 89,
    "AV": 31,
    "YV": 30,
    "SV": 7,
}

_TOTALS_QUERY = "MATCH ()-[r]->() RETURN type(r) AS t, count(*) AS c"

_BY_VEDA_QUERY = "MATCH ()-[r:MENTIONS_DEVATA]->() RETURN r.veda AS veda, count(*) AS c"

_CERTAINTY_QUERY = (
    "MATCH ()-[r:MENTIONS_DEVATA]->() RETURN r.referent_certainty AS value, count(*) AS c"
)

_MANTRAS_QUERY = "MATCH (m:Mantra) RETURN m.veda AS veda, count(*) AS c"

_ASSERTION_QUERY = "MATCH (a:SemanticAssertion) RETURN a.derivation AS value, count(*) AS c"

_MULTI_DEVATA_QUERY = (
    "MATCH (p:Passage)-[:HAS_DEVATA]->(d:Devata) "
    "WITH p, count(DISTINCT d) AS n WHERE n > 1 RETURN count(p) AS c"
)

_AGNI_INDRA_QUERY = (
    "MATCH (p:Passage)-[:MENTIONS_DEVATA]->(:Devata {entity_key: 'VG:DEVATA:AGNIH'}) "
    "MATCH (p)-[:MENTIONS_DEVATA]->(:Devata {entity_key: 'VG:DEVATA:INDRAH'}) "
    "RETURN p.veda AS veda, count(DISTINCT p) AS c"
)


def _grouped(session: Session, query: str, key: str) -> dict[str, int]:
    return {
        str(record[key]): int(record["c"])
        for record in session.run(query)
        if record[key] is not None
    }


def measure(session: Session) -> dict[str, Any]:
    """Re-derive every constant in this module from a live graph.

    Returned shape mirrors the constants exactly, so a test can compare them field by
    field and name the one that moved rather than reporting that "the figures" disagree.
    """
    totals = _grouped(session, _TOTALS_QUERY, "t")
    record = session.run(_MULTI_DEVATA_QUERY).single()
    return {
        "CORPUS_MANTRAS": _grouped(session, _MANTRAS_QUERY, "veda"),
        "PREDICATE_TOTALS": {name: totals.get(name, 0) for name in PREDICATE_TOTALS},
        "MENTIONS_DEVATA_BY_VEDA": _grouped(session, _BY_VEDA_QUERY, "veda"),
        "REFERENT_CERTAINTY": _grouped(session, _CERTAINTY_QUERY, "value"),
        "ASSERTION_LAYERS": _grouped(session, _ASSERTION_QUERY, "value"),
        "MULTI_DEVATA_MANTRAS": int(record["c"]) if record else 0,
        "AGNI_INDRA_CO_MENTION_BY_VEDA": _grouped(session, _AGNI_INDRA_QUERY, "veda"),
    }


def declared() -> dict[str, Any]:
    """The constants as this module declares them, in :func:`measure`'s shape."""
    return {
        "CORPUS_MANTRAS": dict(CORPUS_MANTRAS),
        "PREDICATE_TOTALS": dict(PREDICATE_TOTALS),
        "MENTIONS_DEVATA_BY_VEDA": dict(MENTIONS_DEVATA_BY_VEDA),
        "REFERENT_CERTAINTY": dict(REFERENT_CERTAINTY),
        "ASSERTION_LAYERS": dict(ASSERTION_LAYERS),
        "MULTI_DEVATA_MANTRAS": MULTI_DEVATA_MANTRAS,
        "AGNI_INDRA_CO_MENTION_BY_VEDA": dict(AGNI_INDRA_CO_MENTION_BY_VEDA),
    }


def per_thousand(count: int, veda: str) -> float:
    """``count`` normalised to mantras-per-thousand for ``veda``.

    Exists so that no caveat has to state a raw cross-corpus comparison. The Rigveda is
    5.7 times the Yajurveda by mantra count, so an unnormalised "RV 128 / YV 41" reads as
    Rudra being three times more Rigvedic when the density runs the other way.
    """
    total = CORPUS_MANTRAS.get(veda)
    if not total:
        return 0.0
    return round(count * 1000 / total, 2)


def veda_breakdown(counts: dict[str, int]) -> str:
    """``"RV 10,284, AV 3,582, YV 1,964, SV 1,335"`` in a fixed corpus order.

    Fixed order rather than sorted-by-size, so two caveats built from different layers
    can be read against each other without re-sorting them in your head.
    """
    return ", ".join(f"{veda} {counts.get(veda, 0):,}" for veda in ("RV", "AV", "YV", "SV"))
