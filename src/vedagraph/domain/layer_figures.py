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

#: Verses carrying their own dedicated English translation, by corpus. Four separate
#: figures rather than one because they are four separate claims, and a caveat that quotes
#: "coverage is X of Y" needs the one it names to be measurable.
#:
#: "Dedicated" is the narrow sense on purpose. It excludes a verse reached only by a
#: multi-verse print unit (:data:`RANGE_COVERED_MANTRAS`), a verse showing another corpus's
#: rendering of verified-identical text (:data:`REUSED_RENDERING_MANTRAS`), and a verse
#: whose only rendering is Griffith's Latin (:data:`NON_ENGLISH_MANTRAS`). Summing those
#: into one percentage is what let the reader present all four as the same thing.
#: RV 10,480 and YV 1,950, not 10,479 and 1,939. Both moved upward at b4b1b0b, which
#: imported 1,132 renderings: one Rigvedic verse and eleven Yajurvedic ones gained a
#: dedicated English rendering that is neither a reuse row nor a MANTRA_RANGE span, so they
#: entered this narrow population. Measured against the R3 baseline backup to confirm the
#: move predates R3 and is not a side effect of this pass.
DEDICATED_ENGLISH_MANTRAS: Final[dict[str, int]] = {
    "RV": 10_480,
    "AV": 5_715,
    "YV": 1_950,
    "SV": 0,
}

#: Verses covered only because a translator's print unit spans them. Counts the whole span
#: including its anchor, because the anchor's rendering is not a rendering of the anchor
#: alone either.
RANGE_COVERED_MANTRAS: Final[dict[str, int]] = {
    "RV": 60,
    "AV": 68,
    "YV": 0,
    "SV": 0,
}

#: Verses whose English is another corpus's published rendering of text verified
#: character-identical. Never added to :data:`DEDICATED_ENGLISH_MANTRAS`: the Samavedic 173
#: is the whole reason the distinction is drawn, because it is the only English that
#: reaches that corpus and it is Rigvedic.
REUSED_RENDERING_MANTRAS: Final[dict[str, int]] = {
    "RV": 0,
    "AV": 21,
    "YV": 0,
    "SV": 173,
}

#: Verses whose only rendering is not in English. Griffith rendered passages he judged too
#: explicit for an English readership into Latin; the literal is his real published text
#: and it is not the English layer.
NON_ENGLISH_MANTRAS: Final[dict[str, int]] = {
    "RV": 6,
    "AV": 18,
    "YV": 0,
    "SV": 0,
}

#: Total edges per predicate, for the predicates a caveat names.
PREDICATE_TOTALS: Final[dict[str, int]] = {
    "MENTIONS_DEVATA": 17_165,
    "HAS_DEVATA": 10_558,
    "HAS_RISHI": 17_889,
    # 16,298 and not 16,331: OWNER_DECISIONS section 27 withdrew M9's 33 malformed metre
    # assertions under authorisation. 16,331 - 33 = 16,298.
    "HAS_CHANDAS": 16_298,
    # 154,261 and not 9,000. The 9,000 was the V2 arrangement in which MENTIONS_ENTITY
    # reached :Devata; the lemma projection GAP-MORPHOLOGY-001 asked for has since been run
    # and reaches all 10,031 :Lemma nodes over all 10,552 Rigvedic mantras, one edge per
    # mantra-lemma pair. Still Rigveda-only: the Zurich annotation is the only source and it
    # covers no other corpus, so an SV/YV/AV zero here is an unannotated corpus.
    "MENTIONS_LEMMA": 154_261,
    # 35,131 and not 4,865, and this is the R2 F1 figure surviving in the one module whose
    # whole contract is that no caveat types its own number. The delta is exactly the 30,266
    # edges R1's identity repair restored. Reaches four corpora, not the Rigveda alone --
    # see ASSERTION_LAYERS for the five derivations it must be split into before it is
    # quoted, because summing them is the defect GAP-SEMANTICS-001 was opened for.
    "HAS_SEMANTIC_ASSERTION": 35_131,
    "PERFORMS_ACTION": 441,
    "IS_ASKED_TO": 224,
    # 28,116 landed, against 28,227 rows in data/domain/vedagraph_domain_v2/
    # domain_mentions.jsonl. The earlier declaration was the ARTIFACT ROW COUNT and not the
    # landed edge count -- rows sent, not rows landed, which is the one diff this project
    # requires. Reconciles exactly: 28,227 artifact rows, MINUS 117 VG:CONCEPT:SOMA-PRESSING
    # rows withheld under OWNER_DECISIONS section 13 (its weak aliases lose assertion
    # authority), PLUS the 6 yupa- witnesses the alias fix added outside that artifact
    # (RV 1.162.6, 4.33.3, 5.2.7, VSM 19.17, VSM 25.29, AVS 12.1.38) = 28,116.
    "MENTIONS_ENTITY": 28_116,
    # 24,861 landed, against 46,439 rows in data/enrichment/vedagraph_enrichment_v1/
    # concept_assertions.jsonl. The pre-R3 declaration cited "46,508 rows minus 21,539
    # english-only = 24,969" and neither operand matches the committed artifact any more.
    #
    # R3's FIRST reconciliation of this figure was also wrong, and is corrected here rather
    # than quietly replaced. It said "MINUS the 21,603 whose evidence is English-only". By
    # `method`, the English-only population is 21,526, not 21,603 -- and 21,603 is not a
    # population at all, it is 46,439 - 24,836, the residue that makes the subtraction come
    # out. A warrant reverse-engineered from the answer reproduces the answer and nothing
    # else, which is the whole failure mode a stated reconciliation exists to prevent.
    #
    # Measured per pair against the live graph, and it reconciles exactly:
    #     24,913  Sanskrit-evidenced pairs (method != concept-alias-v1:english)
    #   -     91  Sanskrit-evidenced pairs that did NOT land, and whose retirement has NO
    #             recorded reason -- SOMA-DRINK 15, YAJNA-SACRIFICE 12, VASU-WEALTH 7,
    #             SOMA-PRESSING 6, AGNI-FIRE 5, RAKSAS-DEMON 5, VAJA-PRIZE 4,
    #             BHESAJA-HEALING 4 and 19 more concepts
    #   +     14  English-only pairs that landed ANYWAY, contrary to the stated retirement
    #   +     25  pairs absent from this artifact entirely, 16 of them hotr- from the
    #             ritual-role pass
    #   = 24,861
    #
    # The 91 and the 14 are open: they are a real, small, two-directional disagreement
    # between the artifact's own rule and what the loader landed, and naming them is the
    # point. They are NOT an R3 regression -- the R3 baseline logical export carries the same
    # 24,861 -- so this constant describes a pre-R3 state accurately while disclosing that
    # 105 of its rows do not follow the rule the artifact declares.
    "ABOUT_CONCEPT": 24_861,
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

#: The derivations inside the ``SemanticAssertion`` label, which must never be summed.
#:
#: **Five, not two.** Three were missing -- and the test asserting that these sum to
#: ``PREDICATE_TOTALS["HAS_SEMANTIC_ASSERTION"]`` passed anyway, because BOTH sides were
#: stale by the same 30,266: 2,406 + 2,459 = 4,865 exactly. A sum check over two figures
#: that drift together cannot fail, which is why the live-graph test is the one that finds
#: this and why it must not be left skipped. All five: 2,406 + 2,459 + 28,370 + 1,532 + 364
#: = 35,131.
#:
#: The split is load-bearing rather than descriptive. ``MODEL_EXTRACTION`` is model-assisted
#: and ``MORPHOLOGY_RULE`` is deterministic over a manual scholarly annotation, so a blended
#: total states a confidence about 35,131 assertions that is true of neither population --
#: the clause-3 defect GAP-SEMANTICS-001 was opened for, and the reason no surface may
#: publish this label's total without the breakdown beside it.
ASSERTION_LAYERS: Final[dict[str, int]] = {
    "MORPHOLOGY_RULE": 2_406,
    "MODEL_EXTRACTION": 2_459,
    "MORPHOLOGY_RULE_PREDICATE_ONLY": 28_370,
    "TREEBANK_DEPREL": 1_532,
    "CROSS_VEDA_TEXT_IDENTITY": 364,
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

#: Every figure a client-facing sentence quotes about *review*, in one place, because five
#: sentences across three modules each typed their own and three of them were wrong. ``587``
#: was quoted as the whole of ``TIER_C`` (598) and as the whole of ``MODEL_ADJUDICATED``
#: (613), and ``613`` was said to span ten predicates (twelve).
#:
#: **TIER_C is two populations, and a sentence naming only one states a false zero.** 587
#: edges hang off a ``:Passage``: a model re-read that passage and accepted the edge, which
#: is the definition ``vedagraph.domain.tiers`` applies. The other 11 are
#: ``EPITHET_VARIANT_OF`` / ``SPECIALIZED_FORM_OF`` between two ``:Devata`` nodes, where the
#: adjudication is of a *label* against its base and there is no passage to read. They carry
#: ``review_state = UNREVIEWED`` because no passage review happened, and TIER_C because
#: ``LAYER_OWNED_GRADES`` grades that predicate L3/C by design. The published sentence said
#: "all 587 TIER_C edges are Yajurvedic (320) or Atharvavedic (267) and not one is
#: Rigvedic", which typed those 11 out of existence -- and their evidence cites RV 3.53,
#: RV 4.55 and the ninth mandala.
#:
#: ``HUMAN_REVIEWED`` is here because it is the single most consequential claim the product
#: makes about itself, and a zero nothing measures is a zero nobody would notice moving.
REVIEW_POPULATION: Final[dict[str, int]] = {
    "MODEL_ADJUDICATED_EDGES": 613,
    "MODEL_ADJUDICATED_PREDICATES": 12,
    "TIER_C_EDGES": 598,
    "TIER_C_PASSAGE_ANCHORED": 587,
    "TIER_C_PASSAGE_ANCHORED_YV": 320,
    "TIER_C_PASSAGE_ANCHORED_AV": 267,
    "TIER_C_PASSAGE_ANCHORED_RV": 0,
    "TIER_C_LABEL_LEVEL": 11,
    "HUMAN_REVIEWED_EDGES": 0,
}


#: The formula layer's nesting census, because a formula frequency ranking is a ranking
#: over a population that double-counts itself and no surface said so.
#:
#: 1,103 of the 4,825 ``Formula`` nodes are a strict substring of another formula on the
#: collapsed identity surface, so a ranking by occurrence count returns the same piece of
#: phraseology several times at several lengths. Measured on the live graph, 26 of the 30
#: rows the cross-Veda formula ranking returns are nested wordings -- so this is not a
#: footnote about a tail, it is a description of the head of the list.
#:
#: The project's contract is that the nesting is *typed and published*, not deduplicated:
#: a sub-span attested where its container is not is a separate fact about the corpus and
#: survives as its own node. Every surface that ranks formulas by frequency therefore has
#: to say which reading it applies, and :func:`formula_nesting_policy` is the sentence all
#: of them quote so that the three readings cannot drift apart.
FORMULA_NESTING: Final[dict[str, int]] = {
    "FORMULAS": 4825,
    "INDEPENDENT": 2788,
    "NESTED_IN_ANOTHER": 918,
    "NESTED_AND_CONTAINING": 185,
    "CONTAINS_ANOTHER": 934,
    "STRICT_SUBSTRING_OF_ANOTHER": 1103,
    "TYPED": 4825,
}


def formula_nesting_policy() -> str:
    """The nesting policy sentence every formula frequency ranking states.

    Built from :data:`FORMULA_NESTING` rather than typed, so a ranking cannot publish a
    stale share, and so a population change fails ``tests/domain/test_layer_figures.py``
    before it reaches a reader.
    """
    f = FORMULA_NESTING
    return (
        f"NESTING POLICY: EVERY_FORMULA_COUNTED_ONCE_AND_TYPED. "
        f"{f['STRICT_SUBSTRING_OF_ANOTHER']:,} of {f['FORMULAS']:,} formulas are a strict "
        f"substring of another on the collapsed identity surface, so this ranking returns "
        f"one piece of phraseology at several lengths rather than several phrases. Nothing "
        f"is deduplicated and nothing is rolled up: every formula carries "
        f"formula_nesting_type ({f['INDEPENDENT']:,} INDEPENDENT, "
        f"{f['NESTED_IN_ANOTHER']:,} NESTED_IN_ANOTHER, {f['CONTAINS_ANOTHER']:,} "
        f"CONTAINS_ANOTHER, {f['NESTED_AND_CONTAINING']:,} NESTED_AND_CONTAINING) and the "
        f"reader applies whichever reading the question needs. For a ranking of distinct "
        f"phraseology rather than of strings, rank FormulaFamily instead."
    )


def adjudication_disclosure() -> str:
    """The sentence every surface exposing ``review_state`` or ``TIER_C`` says.

    Built from :data:`REVIEW_POPULATION` rather than typed, so the three modules that quote
    it cannot drift apart again, and so a figure that moves fails
    ``tests/domain/test_layer_figures.py`` before it reaches a reader.
    """
    f = REVIEW_POPULATION
    return (
        f"No edge in this graph is HUMAN_REVIEWED and none may claim to be "
        f"({f['HUMAN_REVIEWED_EDGES']} carry it); there is still no human gold set. The "
        f"strongest review state that exists is MODEL_ADJUDICATED, on "
        f"{f['MODEL_ADJUDICATED_EDGES']} edges across {f['MODEL_ADJUDICATED_PREDICATES']} "
        f"predicates, where a model re-read the passage and accepted the edge with a stated "
        f"reason. TIER_C is wider than that: of its {f['TIER_C_EDGES']} edges, "
        f"{f['TIER_C_PASSAGE_ANCHORED']} hang off a passage "
        f"({f['TIER_C_PASSAGE_ANCHORED_YV']} Yajurvedic, "
        f"{f['TIER_C_PASSAGE_ANCHORED_AV']} Atharvavedic, "
        f"{f['TIER_C_PASSAGE_ANCHORED_RV']} Rigvedic) and {f['TIER_C_LABEL_LEVEL']} are "
        f"Devata-to-Devata epithet identities, adjudicated as labels with no passage to "
        f"read and carrying review_state UNREVIEWED for that reason."
    )


_TOTALS_QUERY = "MATCH ()-[r]->() RETURN type(r) AS t, count(*) AS c"

# One query per figure, and deliberately not one query with eight aggregations: the whole
# point of the block above is that the passage-anchored and label-level halves of TIER_C
# are counted apart, and a single grouped query is how they got merged.
_REVIEW_POPULATION_QUERY = """
RETURN
  count { ()-[r]->() WHERE r.review_state = 'MODEL_ADJUDICATED' }
    AS MODEL_ADJUDICATED_EDGES,
  size([t IN collect { MATCH ()-[r]->() WHERE r.review_state = 'MODEL_ADJUDICATED'
        RETURN DISTINCT type(r) } | t]) AS MODEL_ADJUDICATED_PREDICATES,
  count { ()-[r]->() WHERE r.quality_tier = 'TIER_C' } AS TIER_C_EDGES,
  count { (:Passage)-[r]->() WHERE r.quality_tier = 'TIER_C' } AS TIER_C_PASSAGE_ANCHORED,
  count { (p:Passage)-[r]->() WHERE r.quality_tier = 'TIER_C' AND p.veda = 'YV' }
    AS TIER_C_PASSAGE_ANCHORED_YV,
  count { (p:Passage)-[r]->() WHERE r.quality_tier = 'TIER_C' AND p.veda = 'AV' }
    AS TIER_C_PASSAGE_ANCHORED_AV,
  count { (p:Passage)-[r]->() WHERE r.quality_tier = 'TIER_C' AND p.veda = 'RV' }
    AS TIER_C_PASSAGE_ANCHORED_RV,
  count { (a)-[r]->() WHERE r.quality_tier = 'TIER_C' AND NOT a:Passage }
    AS TIER_C_LABEL_LEVEL,
  count { ()-[r]->() WHERE r.review_state = 'HUMAN_REVIEWED'
          OR r.provenance_class = 'HUMAN_REVIEWED' } AS HUMAN_REVIEWED_EDGES
"""

_BY_VEDA_QUERY = "MATCH ()-[r:MENTIONS_DEVATA]->() RETURN r.veda AS veda, count(*) AS c"

_CERTAINTY_QUERY = (
    "MATCH ()-[r:MENTIONS_DEVATA]->() RETURN r.referent_certainty AS value, count(*) AS c"
)

_MANTRAS_QUERY = "MATCH (m:Mantra) RETURN m.veda AS veda, count(*) AS c"

# The four coverage populations, each measured on its own definition rather than derived
# from the others. Derivation is what made them one number in the first place: a verse
# reached only by a neighbour's print unit satisfies "has some English nearby" and does not
# satisfy "has its own translation", and a subtraction cannot tell you which was meant.
_DEDICATED_ENGLISH_QUERY = """
MATCH (m:Mantra)-[:HAS_TRANSLATION]->(t:Translation)
WHERE t.language = 'en'
  AND t.reuse_kind IS NULL
  AND t.alignment_level <> 'MANTRA_RANGE'
RETURN m.veda AS veda, count(DISTINCT m) AS c
"""

# Counts the whole declared span and not the anchors, so the second verse of every pair is
# in the figure. Counting anchors is the bug: it returns 30 for a population of 60.
_RANGE_COVERED_QUERY = """
MATCH (:Mantra)-[:HAS_TRANSLATION]->(t:Translation)
WHERE t.alignment_level = 'MANTRA_RANGE'
UNWIND t.covers_canonical_keys AS key
MATCH (m:Mantra {canonical_key: key})
RETURN m.veda AS veda, count(DISTINCT m) AS c
"""

_REUSED_RENDERING_QUERY = """
MATCH (m:Mantra)-[:HAS_TRANSLATION]->(t:Translation)
WHERE t.reuse_kind = 'REUSED_RENDERING'
RETURN m.veda AS veda, count(DISTINCT m) AS c
"""

# A verse counts here only when it has no English at all. A verse with both an English
# rendering and a Latin one is an English verse that also holds a Latin witness, and
# putting it in this bucket would understate the English layer.
_NON_ENGLISH_QUERY = """
MATCH (m:Mantra)-[:HAS_TRANSLATION]->(t:Translation)
WHERE t.language <> 'en'
  AND NOT EXISTS { (m)-[:HAS_TRANSLATION]->(:Translation {language: 'en'}) }
RETURN m.veda AS veda, count(DISTINCT m) AS c
"""

_ASSERTION_QUERY = "MATCH (a:SemanticAssertion) RETURN a.derivation AS value, count(*) AS c"

# The nesting census is taken from the stored type AND from the stored containment list, so
# a type that stopped agreeing with the relation it describes shows up as drift rather than
# as two consistent-looking halves of one wrong figure.
_FORMULA_NESTING_QUERY = """
MATCH (f:Formula)
RETURN
  count(f) AS FORMULAS,
  count(CASE WHEN f.formula_nesting_type = 'INDEPENDENT' THEN 1 END) AS INDEPENDENT,
  count(CASE WHEN f.formula_nesting_type = 'NESTED_IN_ANOTHER' THEN 1 END)
    AS NESTED_IN_ANOTHER,
  count(CASE WHEN f.formula_nesting_type = 'NESTED_AND_CONTAINING' THEN 1 END)
    AS NESTED_AND_CONTAINING,
  count(CASE WHEN f.formula_nesting_type = 'CONTAINS_ANOTHER' THEN 1 END)
    AS CONTAINS_ANOTHER,
  count(CASE WHEN size(f.formula_contained_in_formula_ids) > 0 THEN 1 END)
    AS STRICT_SUBSTRING_OF_ANOTHER,
  count(CASE WHEN f.formula_nesting_type IS NOT NULL THEN 1 END) AS TYPED
"""

_MULTI_DEVATA_QUERY = (
    "MATCH (p:Passage)-[:HAS_DEVATA]->(d:Devata) "
    "WITH p, count(DISTINCT d) AS n WHERE n > 1 RETURN count(p) AS c"
)

_AGNI_INDRA_QUERY = (
    "MATCH (p:Passage)-[:MENTIONS_DEVATA]->(:Devata {entity_key: 'VG:DEVATA:AGNIH'}) "
    "MATCH (p)-[:MENTIONS_DEVATA]->(:Devata {entity_key: 'VG:DEVATA:INDRAH'}) "
    "RETURN p.veda AS veda, count(DISTINCT p) AS c"
)


def _per_veda(session: Session, query: str) -> dict[str, int]:
    """A per-corpus count seeded with an explicit zero for all four Vedas.

    A corpus with none of whatever is being counted returns no row, and a dict that simply
    lacks the key lets a reader infer whatever they expected. The Samaveda is at 0
    dedicated English translations of 1,844 verses, and that zero has to be stated rather
    than left as an absent key beside three populated ones.
    """
    counts = dict.fromkeys(CORPUS_MANTRAS, 0)
    counts.update(_grouped(session, query, "veda"))
    return counts


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
        "DEDICATED_ENGLISH_MANTRAS": _per_veda(session, _DEDICATED_ENGLISH_QUERY),
        "RANGE_COVERED_MANTRAS": _per_veda(session, _RANGE_COVERED_QUERY),
        "REUSED_RENDERING_MANTRAS": _per_veda(session, _REUSED_RENDERING_QUERY),
        "NON_ENGLISH_MANTRAS": _per_veda(session, _NON_ENGLISH_QUERY),
        "PREDICATE_TOTALS": {name: totals.get(name, 0) for name in PREDICATE_TOTALS},
        "MENTIONS_DEVATA_BY_VEDA": _grouped(session, _BY_VEDA_QUERY, "veda"),
        "REFERENT_CERTAINTY": _grouped(session, _CERTAINTY_QUERY, "value"),
        "ASSERTION_LAYERS": _grouped(session, _ASSERTION_QUERY, "value"),
        "MULTI_DEVATA_MANTRAS": int(record["c"]) if record else 0,
        "AGNI_INDRA_CO_MENTION_BY_VEDA": _grouped(session, _AGNI_INDRA_QUERY, "veda"),
        "REVIEW_POPULATION": _review_population(session),
        "FORMULA_NESTING": _formula_nesting(session),
    }


def _formula_nesting(session: Session) -> dict[str, int]:
    record = session.run(_FORMULA_NESTING_QUERY).single()
    if record is None:  # pragma: no cover - an aggregation always yields one row
        return dict.fromkeys(FORMULA_NESTING, 0)
    return {name: int(record[name]) for name in FORMULA_NESTING}


def _review_population(session: Session) -> dict[str, int]:
    record = session.run(_REVIEW_POPULATION_QUERY).single()
    if record is None:  # pragma: no cover - a RETURN-only query always yields one row
        return dict.fromkeys(REVIEW_POPULATION, 0)
    return {name: int(record[name]) for name in REVIEW_POPULATION}


def declared() -> dict[str, Any]:
    """The constants as this module declares them, in :func:`measure`'s shape."""
    return {
        "CORPUS_MANTRAS": dict(CORPUS_MANTRAS),
        "DEDICATED_ENGLISH_MANTRAS": dict(DEDICATED_ENGLISH_MANTRAS),
        "RANGE_COVERED_MANTRAS": dict(RANGE_COVERED_MANTRAS),
        "REUSED_RENDERING_MANTRAS": dict(REUSED_RENDERING_MANTRAS),
        "NON_ENGLISH_MANTRAS": dict(NON_ENGLISH_MANTRAS),
        "PREDICATE_TOTALS": dict(PREDICATE_TOTALS),
        "MENTIONS_DEVATA_BY_VEDA": dict(MENTIONS_DEVATA_BY_VEDA),
        "REFERENT_CERTAINTY": dict(REFERENT_CERTAINTY),
        "ASSERTION_LAYERS": dict(ASSERTION_LAYERS),
        "MULTI_DEVATA_MANTRAS": MULTI_DEVATA_MANTRAS,
        "AGNI_INDRA_CO_MENTION_BY_VEDA": dict(AGNI_INDRA_CO_MENTION_BY_VEDA),
        "REVIEW_POPULATION": dict(REVIEW_POPULATION),
        "FORMULA_NESTING": dict(FORMULA_NESTING),
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
