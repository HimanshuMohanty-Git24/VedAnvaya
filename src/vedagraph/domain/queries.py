"""Named domain queries: what a reader can actually ask the graph.

This module is the product surface. Every entry is a question a researcher would put in
words, the Cypher that answers it, and -- the part that matters most -- a ``caveat``
stating what the answer does *not* establish.

The caveat field is not documentation politeness. Three properties of this corpus make an
uncaveated answer actively misleading, and all three are invisible in the result set:

**The annotation layer is unevenly scoped, and the gaps are no longer where they were.**
Only the Rigveda has the manual scholarly morphological annotation, so the predicates
derived from it are Rigveda-only: ``HAS_DEVATA`` (10,558 edges), ``MENTIONS_LEMMA``
(154,261 over all 10,552 Rigvedic verses) and the ``PERFORMS_ACTION`` (441) /
``IS_ASKED_TO`` (224) pair derived from the morphological assertions.
``HAS_SEMANTIC_ASSERTION`` is *not* in that set any more: it carries 35,131 edges and
reaches all four corpora. The agentive reading inside it was Rigveda-only and is not any
more: ``ASSERTION_AGENT`` carries 2,660 edges over RV 2,406, AV 124 and YV 34, because
GAP-SEMANTICS-003 projected the DCS dependency annotation's own role resolution onto the
assertion. The Sāmaveda still carries no agent. ``HAS_RISHI`` and
``HAS_CHANDAS`` are *not* in that set any more: ``HAS_RISHI`` now carries 17,889 edges
over RV (10,565), AV (5,084) and YV (2,240), and ``HAS_CHANDAS`` 16,320 over RV (10,523)
and AV (5,797). At mantra level, 10,534 of the RV's 10,552, 4,542 of the AV's 5,839 and
1,960 of the YV's 1,975 mantras carry a seer; the Sāmaveda carries neither predicate.

A zero therefore still has to be read carefully, but now in both directions. A caveat
saying "SV/YV/AV have no attribution layer" *understates* what is answerable, and telling
a researcher a question is unanswerable when it is answerable is the same class of defect
as the reverse, not a safe default. ``MENTIONS_DEVATA`` is the four-Veda route to
"does this passage name this deity?", and is the only deity predicate that reaches the
whole corpus. Its edge counts are NOT written here: every figure the caveats quote
now lives in :mod:`vedagraph.domain.layer_figures` and is asserted against the live
graph by ``tests/domain/test_layer_figures.py``, because the hand-written versions
drifted -- this docstring said 16,261 against a live 17,165, and the ambiguous share
said 8,485 against 8,825.

**Most attribution is inherited, not stated.** 8,329 of 10,558 ``HAS_DEVATA`` edges,
15,177 of 17,889 ``HAS_RISHI`` and 10,388 of 16,320 ``HAS_CHANDAS`` arrive by projecting a
container's label onto each passage inside it. The corpus mix differs so sharply that the
aggregate conceals it: the RV's ``HAS_RISHI`` is 10,093 of 10,565 inherited, the AV's is
5,084 of 5,084 -- every Atharvavedic seer edge is a sūkta label projected downward -- and
the YV's is 0 of 2,240, every one source-stated. Every query that counts attributions
therefore has a strict variant filtered to ``attribution_precision = 'PER_PASSAGE'``, and
where the two answers differ materially the pair is offered rather than the flattering one.

**Some words are both a deity and a thing.** ``agniḥ`` is Agni and it is fire. Mentions
reached only through such aliases carry ``theonym_ambiguous``, and the queries that would
otherwise silently assert the impersonal reading expose it. ``MENTIONS_DEVATA`` grades the
same problem per edge as ``referent_certainty``, where DEITY_CERTAIN is a Rigvedic majority
(5,900 of 10,284) and a minority in every other corpus.

**One label can hold five layers of unequal strength, and summing them is the trap.**
``SemanticAssertion`` is the sharpest case. It holds 35,131 nodes over five derivations and
reaches all four corpora -- RV 27,057, AV 6,167, YV 1,543, SV 364 -- and the derivations are
not one instrument: 2,406 are TIER_B derived by rule from the Sanskrit annotation, 2,459 are
TIER_D extracted unreviewed by a model from a 19th-century English translation, 28,370 come
from a predicate-only pass over the same annotation, 1,532 from the treebank dependency
layer, and the 364 Samavedic rows are projected from letter-identical Rigvedic verses rather
than annotated in their own corpus. They differ in reach as much as in trust, so a blended
count reads as one measurement where there are five. Every query here either filters
``derivation`` or returns it as a column; none aggregates across it.

This paragraph read "2,406 of its 4,865 nodes" and "4,865 assertions over the Rigveda" after
the layer had grown sevenfold and reached three more corpora.
``MEMBER_OF_FAMILY`` has the milder version of the same shape, with 2,032 containment-derived
memberships beside 5 similarity-derived ones.

**Coverage boundaries are recorded in the graph, not left to the reader.**
``layer_veda_scope`` on ``Chandas``, ``Rishi``, ``DevataAscription``, ``SemanticAssertion``
and ``ActionPredicate`` states which corpora each layer measurably reaches, and every row of
it is single-Veda: no layer carrying the property spans two. The review layer runs the other
way from everything else -- of the 598 TIER_C edges, the 587 anchored to a passage are
Yajurvedic (320) or Atharvavedic (267) and not one is Rigvedic, so that half adjudicates
exactly the two corpora the assertion layer never touches. The remaining 11 are
Devata-to-Devata epithet identities with no passage and therefore no Veda, and they are
stated here rather than rounded away, because a sentence that named only the 587 is what
let a reader take TIER_C to be wholly non-Rigvedic when those 11 cite RV 3.53 and RV 4.55.
Every figure in this paragraph is :data:`~vedagraph.domain.layer_figures.REVIEW_POPULATION`,
measured against the live graph by its test. TIER_C means MODEL_ADJUDICATED; nothing in this
graph is HUMAN_REVIEWED.

Queries never return internal nodes: :func:`~vedagraph.domain.ontology.product_filter` is
interpolated rather than each query naming excluded labels itself, so a diagnostic label
added later is excluded by editing one constant.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Final

from vedagraph.domain import layer_figures as figures
from vedagraph.domain.ontology import INTERNAL_MARKED_LABELS, LABEL_INTERNAL
from vedagraph.domain.theonyms import (
    DEFAULT_REFERENT_TIERS,
    EXPLORATORY_REFERENT_TIERS,
    STRICT_REFERENT_TIERS,
)

#: The product default: CERTAIN plus PROBABLE, AMBIGUOUS excluded. Interpolated as a
#: parameter rather than written into each query, because the V3.1 deity pass measured
#: what happens when a query hard-codes the strict tier -- filtering to DEITY_CERTAIN
#: returns ZERO non-Rigvedic mentions for Agni, Soma, Surya, Mitra, Savitr, Usas,
#: Vayu, Apah and Prthivi, so the cautious analyst got a worse answer than the
#: careless one and a reader would read those zeros as absence from the text.
_DEFAULT_TIERS: Final = sorted(DEFAULT_REFERENT_TIERS)
_EXPLORATORY_TIERS: Final = sorted(EXPLORATORY_REFERENT_TIERS)
_STRICT_TIERS: Final = sorted(STRICT_REFERENT_TIERS)

#: Default parameters, so every query is runnable as written with no arguments.
INDRA: Final = "VG:DEVATA:INDRAH"
AGNI: Final = "VG:DEVATA:AGNIH"
SOMA: Final = "VG:DEVATA:SOMAH"
VARUNA: Final = "VG:DEVATA:VARUNAH"
RUDRA: Final = "VG:DEVATA:RUDRAH"


@dataclass(frozen=True)
class DomainQuery:
    """One answerable question, with its limits attached."""

    name: str
    question: str
    cypher: str
    parameters: dict[str, Any] = field(default_factory=dict)
    #: What this answer does NOT establish. Empty only where there is genuinely nothing
    #: to warn about, which is rarer than it looks.
    caveat: str = ""
    #: Killer-question numbers this serves, for the answerability audit.
    serves: tuple[int, ...] = ()


_NOT_INTERNAL = f"NOT n:{LABEL_INTERNAL}"

#: Attached to every HAS_DEVATA query. Names the one predicate that is actually
#: Rigveda-only rather than the whole attribution layer, because HAS_RISHI and
#: HAS_CHANDAS are no longer RV-only and a blanket warning would now send a researcher
#: away from questions the graph can answer.
#: Two deity-attribution predicates, and the reason a zero in one is not an absence.
#:
#: The previous wording said "a zero for SV/YV/AV means those corpora carry no Anukramani
#: deity ascription", which was written about HAS_DEVATA and generalised into a claim about
#: the corpus. It was false for the Atharvaveda, which carries 5,385 HAS_DEVATA_ASCRIPTION
#: edges over 4,665 of its 6,590 passages -- so a reader asking which Vedas record
#: dedications was told a whole corpus had none while the graph held the answer.
#:
#: The denominator was wrong too, in both copies, for a whole R2 pass: 4,665 is a *passage*
#: count and it was published against the *mantra* total, 5,839. The mantra-scoped figure is
#: 4,816 edges over 4,160 mantras, and the gap is 505 hymn-level containers. A numerator from
#: one population over a denominator from another overstated Atharvavedic verse coverage by
#: 505 verses while every individual figure in the sentence was correct.
_SCOPE_CAVEAT = (
    "THREE DEITY-ATTRIBUTION PREDICATES, NONE COMPLETE. HAS_DEVATA resolves a dedication to "
    "a :Devata node and is Rigveda-only: 10,558 edges, every one on the RV. The Atharvaveda "
    "carries its dedication under HAS_DEVATA_ASCRIPTION, 5,385 edges over 4,665 of its 6,590 "
    "PASSAGES -- 4,816 of those edges on 4,160 of its 5,839 mantras, the rest on hymn-level "
    "containers -- pointing at a :DevataAscription that holds Whitney's verbatim descriptor "
    "rather than a deity name. Those two share no label value, by category rather than by "
    "coverage. "
    "The bridge between them is now BUILT and is partial: HAS_DEVATA_DERIVED carries 882 "
    "Atharvavedic dedications over 851 passages, resolved from the descriptor's own morphology "
    "under Panini 4.2.24 sasya devata, derived from 39 of them and reaching 35 deities. 47 of "
    "the 324 descriptors now RESOLVE -- R4 widened the resolver and the derived layer has "
    "not been rebuilt from the 8 it gained (R4-RESIDUAL-ATTRIBUTION-002) -- so resolution "
    "and dedication are two figures here and not one. The "
    "other 277 are refused rather than unprocessed, each carrying a typed reason: 202 reach no "
    "canonical deity surface, 67 are compounds naming two ascriptions, 4 are hymn subjects "
    "rather than deities, 3 name a plurality, and 1 is the Anukramani's own deferral marker "
    "lingokta. So a zero here means this predicate does not reach that corpus, NOT that the "
    "corpus records no dedication and NOT that the deity is absent from it. The Samaveda and "
    "Yajurveda carry no dedication layer of any of the three kinds, which is "
    "GAP-ATTRIBUTION-001 and a source block, not an unbuilt projection. MENTIONS_DEVATA "
    "answers 'is this deity named here?' across all "
    f"four ({figures.PREDICATE_TOTALS['MENTIONS_DEVATA']:,} edges: "
    f"{figures.veda_breakdown(figures.MENTIONS_DEVATA_BY_VEDA)})."
)
_INHERIT_CAVEAT = (
    "Counts include CONTAINER_INHERITED attributions: a sukta's label projected onto each "
    "of its mantras. See the *_strict variant for source-stated attribution only."
)

#: Attached to every MENTIONS_DEVATA query. The predicate reaches all four corpora, which
#: is why it exists, but it does so by two different instruments, and a row that sums them
#: averages a hand-annotated lemma against a string match without saying so.
_MENTION_LAYER_CAVEAT = (
    f"MENTIONS_DEVATA spans all four Vedas "
    f"({figures.PREDICATE_TOTALS['MENTIONS_DEVATA']:,} edges: "
    f"{figures.veda_breakdown(figures.MENTIONS_DEVATA_BY_VEDA)}) but not by one "
    "method: the RV's come from the manual scholarly lemma "
    "annotation (extraction_path = 'rv-lemma-annotation') and the other 5,977 from surface "
    "token or sandhi matching, which has no morphology behind it. Compare rows as shares "
    "of their corpus (RV 10,552 mantras, AV 5,839, YV 1,975, SV 1,844), not as totals."
)

#: Attached where a MENTIONS_DEVATA query does not filter referent_certainty. The flag is
#: on the edge, so a query that ignores it is choosing to, and should say so.
_CERTAINTY_CAVEAT = (
    f"Unfiltered on referent_certainty: "
    f"{figures.REFERENT_CERTAINTY['DEITY_AMBIGUOUS']:,} of "
    f"{figures.PREDICATE_TOTALS['MENTIONS_DEVATA']:,} mention edges are DEITY_AMBIGUOUS, "
    "because agni is also fire, soma also the pressed drink, surya also the sun and vac "
    "also speech. Deities whose name is an ordinary noun are flattered accordingly, and "
    "the ambiguous share is the majority in every corpus except the Rigveda."
)

#: Attached to every SemanticAssertion query. One label, two instruments, and summing them
#: is the specific misleading answer this graph exists to refuse.
_ASSERTION_LAYER_CAVEAT = (
    "SemanticAssertion is one label over five derivations of unequal strength that must not "
    "be summed: 28,370 MORPHOLOGY_RULE_PREDICATE_ONLY and 2,406 MORPHOLOGY_RULE (derived by "
    "rule from the Sanskrit lemma annotation), 1,532 TREEBANK_DEPREL, 364 "
    "CROSS_VEDA_TEXT_IDENTITY (projected from a letter-identical Rigvedic verse rather than "
    "annotated in their own corpus) and 2,459 MODEL_EXTRACTION (TIER_D, unreviewed model "
    "output over a 19th-century English translation). The layer reaches all four corpora "
    "unevenly -- RV 27,057, AV 6,167, YV 1,543, SV 364 -- and none of the 35,131 has been "
    "reviewed by a human. Their reach differs as much as their strength, so a blended count "
    "would read as one instrument where there are five. This caveat previously ended 'All "
    "4,865 are Rigvedic', which was true of an earlier state of the layer and became a "
    "blended total of exactly the kind it exists to refuse."
)

#: PERFORMS_ACTION and IS_ASKED_TO are aggregates over the morphology layer only, so they
#: inherit its Rigveda-only scope even though nothing in their column names says so.
_ACTION_SCOPE_CAVEAT = (
    "PERFORMS_ACTION (441 edges) and IS_ASKED_TO (224) are aggregates over the 2,406 "
    "MORPHOLOGY_RULE assertions, which come from the Rigveda-only lemma annotation: all "
    "665 edges are Rigvedic. A deity absent here is absent from that annotation, not from "
    "Vedic action, and the Samaveda, Yajurveda and Atharvaveda are absent entirely."
)

#: Nothing in this graph is human-reviewed, and the review layer must not be read as if it
#: were. Stated on every query that surfaces review_verdict or TIER_C.
_ADJUDICATION_CAVEAT = (
    "TIER_C means MODEL_ADJUDICATED, not human-reviewed. "
    + figures.adjudication_disclosure()
    + " The passage-anchored part of the layer therefore reaches exactly the two corpora "
    "the assertion layer never reaches, and the two cannot be compared."
)

#: Shared by every single-deity profile query. Hoisted to a constant rather than
#: copied per deity, because two profiles that drifted apart would be worse than one.
_DEITY_PROFILE_CYPHER = """
        MATCH (dv:Devata {entity_key: $key})
        OPTIONAL MATCH (dv)-[:HAS_AXIS]->(ax:DeityAxis)
        OPTIONAL MATCH (dv)-[:HAS_EPITHET]->(ep:Epithet)
        WITH dv, collect(DISTINCT ax.axis) AS axes, collect(DISTINCT ep.label_iast) AS epithets
        RETURN dv.display_label AS deity, dv.label_iast AS iast, dv.structure AS structure,
               axes, epithets, dv.short_description AS description,
               dv.profile_attributed_total AS attributed,
               dv.profile_attributed_per_passage AS attributed_per_passage,
               dv.profile_attributed_inherited AS attributed_inherited,
               dv.profile_top_rishis AS top_rishis, dv.profile_top_chandas AS top_chandas,
               dv.profile_top_concepts AS top_concepts, dv.profile_co_devatas AS co_deities,
               dv.profile_attribution_scope AS attribution_scope
        """

QUERIES: Final[tuple[DomainQuery, ...]] = (
    # ---------------------------------------------------------------- deities
    DomainQuery(
        name="deity_profile",
        question="Who is this deity, where do they appear, and what surrounds them?",
        cypher=_DEITY_PROFILE_CYPHER,
        parameters={"key": INDRA},
        caveat=_SCOPE_CAVEAT + " " + _INHERIT_CAVEAT,
        serves=(1, 17, 18, 19, 20, 38, 43, 44, 45, 46),
    ),
    DomainQuery(
        name="varuna_profile",
        question="What is Varuna's corpus profile, and how does it differ from Indra's?",
        cypher=_DEITY_PROFILE_CYPHER,
        parameters={"key": VARUNA},
        caveat=(
            "Uses the same projection as deity_profile, so the two are directly "
            "comparable. Varuna is attributed to 99 Rigvedic mantras against Indra's "
            "2,869, and the gap is a fact about the Anukramani's sukta labels rather "
            "than a measure of prominence: Varuna is also named inside hymns labelled "
            "for Mitravarunau, which is a separate entity. " + _SCOPE_CAVEAT
        ),
        serves=(3, 44),
    ),
    DomainQuery(
        name="deities_by_axis",
        question="Which deities occupy a given functional role?",
        cypher="""
        MATCH (dv:Devata)-[:HAS_AXIS]->(ax:DeityAxis)
        WHERE ax.axis <> 'UNSPECIFIED'
        OPTIONAL MATCH (dv)-[:EPITHET_VARIANT_OF]->(base:Devata)
        WITH ax.axis AS axis, dv,
             coalesce(base.display_label, dv.display_label) AS resolved_label
        WITH axis,
             count(DISTINCT CASE WHEN dv.structure = 'INDIVIDUAL' THEN resolved_label END)
               AS individual_deities,
             count(CASE WHEN dv.structure = 'INDIVIDUAL' THEN dv END) AS individual_subjects,
             count(CASE WHEN dv.structure = 'PAIR' THEN dv END) AS pair_subjects,
             count(CASE WHEN dv.structure = 'GROUP' THEN dv END) AS group_subjects,
             count(CASE WHEN NOT dv.structure IN ['INDIVIDUAL', 'PAIR', 'GROUP']
                        THEN dv END) AS other_subjects,
             count(dv) AS all_subjects,
             collect(CASE WHEN dv.structure = 'INDIVIDUAL' THEN dv.display_label END)[0..12]
               AS individual_examples,
             collect(CASE WHEN dv.structure <> 'INDIVIDUAL' THEN dv.display_label END)[0..8]
               AS non_individual_examples
        RETURN axis, individual_deities, individual_subjects, all_subjects,
               pair_subjects, group_subjects, other_subjects,
               individual_examples, non_individual_examples
        ORDER BY individual_deities DESC, axis
        UNION ALL
        MATCH (dv:Devata)-[:HAS_AXIS]->(:DeityAxis {axis: 'UNSPECIFIED'})
        RETURN 'NO_AXIS_ASSIGNED (not an axis; reported so the 214 reconcile)' AS axis,
               count(DISTINCT CASE WHEN dv.structure = 'INDIVIDUAL'
                                   THEN dv.display_label END) AS individual_deities,
               count(CASE WHEN dv.structure = 'INDIVIDUAL' THEN dv END)
                 AS individual_subjects,
               count(dv) AS all_subjects,
               count(CASE WHEN dv.structure = 'PAIR' THEN dv END) AS pair_subjects,
               count(CASE WHEN dv.structure = 'GROUP' THEN dv END) AS group_subjects,
               count(CASE WHEN NOT dv.structure IN ['INDIVIDUAL', 'PAIR', 'GROUP']
                          THEN dv END) AS other_subjects,
               collect(CASE WHEN dv.structure = 'INDIVIDUAL' THEN dv.display_label END)[0..12]
                 AS individual_examples,
               collect(CASE WHEN dv.structure <> 'INDIVIDUAL' THEN dv.display_label END)[0..8]
                 AS non_individual_examples
        """,
        caveat=(
            "Axes are curated interpretation (TIER_D), not source statements. "
            "`individual_deities` counts DISTINCT RESOLVED DEITIES, not rows: it "
            "collapses epithet variants onto their base through EPITHET_VARIANT_OF and "
            "collapses the six duplicate-label node pairs at the same time, because both "
            "are the same error -- one entity counted twice. Before that resolution "
            "FIRE_MEDIUM read 5 individual deities and is 2, Agni having been counted four "
            "times as Agni, Agni Jatavedas, Agni Pavamana and Agni the slayer of demons. "
            "`individual_subjects` is kept beside it as the unresolved row count so the "
            "gap between them is visible rather than silently corrected. "
            "This was the THIRD stratum of one question -- what counts as a deity -- found "
            "in three successive adversarial passes: the unranked UNSPECIFIED bucket, then "
            "composite double-counting beneath it, then epithet variants beneath that. "
            "Unlike the first two, correcting this one does NOT change the top-ranked "
            "member: the top six are identical before and after, so it was a wrong count "
            "rather than a wrong answer. "
            "RANKED ON `individual_deities`, NOT on `all_subjects`, and the two differ "
            "enough to invert the answer. `all_subjects` counts every Anukramani "
            "addressee carrying the axis, which DOUBLE-COUNTS a deity through every "
            "dyad and group he appears in: WARRIOR reads 20 subjects of which only 3 "
            "are individual deities -- 14 are PAIRs, 2 GROUPs, 1 abstraction -- and 13 "
            "of the 20 are `Indra and X`, so the 20 is substantially Indra counted "
            "eleven times. Ranked on individual deities, WARRIOR is not in the top "
            "eight at all: TERRESTRIAL 7, ABSTRACT_PERSONIFICATION 6, "
            "COSMIC_SOVEREIGN 6, SOLAR 6, then four at 5, and WARRIOR 3. "
            "The V3.1 adversarial re-attack found this UNDERNEATH the UNSPECIFIED "
            "defect: the first fix excluded the unranked bucket and left the composite "
            "inflation, so the query still ranked on a number its own caveat told the "
            "reader not to use, and returned `collect(DISTINCT structure)` -- a set, "
            "not counts -- so the corrected ranking could not be recovered from the "
            "output. Every component count is now a column. "
            "DO NOT filter on `is_composite` for this: it means "
            "'has a recorded decomposition', not 'is a compound', and it is false on "
            "five genuine PAIRs such as `Indra and Parvata`. `structure` is the "
            "reliable discriminator, and it is what `deity_widest_range` uses, so the "
            "two queries now agree on what a deity is. "
            "UNSPECIFIED is excluded from the ranking and returned as a final "
            "NO_AXIS_ASSIGNED row so the 214 reconcile: 113 subjects carry a real axis "
            "and 101 do not, and no subject carries both. For a genuine deity the "
            "registry declines to characterise, UNSPECIFIED is a POSITIVE STATEMENT "
            "rather than a gap -- but the bucket is not only that. Of the 101: 29 "
            "ABSTRACT, 22 HUMAN, 22 INDIVIDUAL, 16 GROUP, 7 PATRON_PRAISE, 4 PAIR and "
            "1 whose `structure` is itself UNSPECIFIED. The Devata label covers every "
            "subject the Anukramani names as a hymn's addressee, which includes human "
            "patrons (`Asamati, a patron`, `Brbu the carpenter`) and abstractions "
            "(`Ka, the Who`) -- the same distinction the risi layer draws with "
            "`is_seer`, where 113 of 729 rows are not seers."
        ),
        serves=(20, 38, 41, 46),
    ),
    DomainQuery(
        name="deity_widest_range",
        question="Which deities have the widest functional range?",
        cypher="""
        MATCH (dv:Devata)-[:HAS_AXIS]->(ax:DeityAxis)
        WHERE ax.axis <> 'UNSPECIFIED' AND dv.structure = 'INDIVIDUAL'
          AND NOT (dv)-[:EPITHET_VARIANT_OF]->(:Devata)
        WITH dv, count(ax) AS axis_count, collect(ax.axis) AS axes
        RETURN dv.display_label AS deity, axis_count, axes,
               coalesce(dv.profile_attributed_total, 0) AS attributed
        ORDER BY axis_count DESC, attributed DESC, deity LIMIT 15
        """,
        caveat=(
            "Range as curated, so this measures the taxonomy as much as the corpus. "
            "`attributed` is coalesced to 0 rather than left null: only the top 25 "
            "deities are profiled, and a null sorted ahead of a real count, which put "
            "composite Anukramani labels at the head of the list."
        ),
        serves=(38, 46),
    ),
    DomainQuery(
        name="deity_composition",
        question="Which deity labels are duals or composites, and of what?",
        cypher="""
        MATCH (whole:Devata)-[:COMPOSED_OF]->(part:Devata)
        RETURN whole.display_label AS composite, whole.structure AS structure,
               collect(part.display_label) AS components
        ORDER BY composite
        """,
        caveat=(
            "Decomposition follows the dual/plural form of the label. The registry marks "
            "MITRAVARUNAU as deliberately not decomposed while devata_components.yaml "
            "decomposes it; the two files disagree and this follows the component file."
        ),
        serves=(33, 42),
    ),
    DomainQuery(
        name="deity_community_capability",
        question="What deity communities emerge from the corpus?",
        cypher="""
        CALL () {
            MATCH (:Devata)-[r:CO_OCCURS_WITH]-(:Devata)
            RETURN count(r) / 2 AS pairwise_edges
        }
        CALL () {
            MATCH (d:Devata)
            RETURN count(d) AS devata_nodes,
                   sum(CASE WHEN d.is_deity = true
                            THEN 1 ELSE 0 END) AS eligible_deities,
                   sum(CASE WHEN d.is_deity IS NULL THEN 1 ELSE 0 END)
                     AS devatas_without_an_eligibility_ruling,
                   sum(CASE WHEN d.is_deity = true
                             AND any(key IN ['community', 'louvain', 'partition']
                                     WHERE properties(d)[key] IS NOT NULL)
                            THEN 1 ELSE 0 END) AS assigned_deities
        }
        RETURN CASE WHEN assigned_deities = 0 THEN 'INSUFFICIENT_EVIDENCE'
                    ELSE 'COMMUNITY_ASSIGNMENTS_AVAILABLE' END AS status,
               assigned_deities, eligible_deities,
               devatas_without_an_eligibility_ruling, devata_nodes, pairwise_edges,
               'PAIRWISE_CO_OCCURRENCE_IS_NOT_A_COMMUNITY_PARTITION' AS evidence_scope
        """,
        caveat=(
            "This is a capability result, not a claim that Vedic deity communities do "
            "not exist. INSUFFICIENT_EVIDENCE means the graph has pairwise co-occurrence "
            "but no stored or computed community assignment; absence of that graph layer "
            "is not absence in the Vedas. `eligible_deities` is the one documented "
            "eligibility predicate `d.is_deity = true` (vedagraph.domain.deity_eligibility, "
            "VG:DEITY_ELIGIBILITY:V1), which excludes 22 human patrons, 7 danastuti "
            "gift-praise labels and the 28 ABSTRACT labels ruled NOT_DEITY per label with a "
            "recorded reason, and keeps the 5 ruled UNDECIDED. Every excluded node keeps "
            "`non_deity_kind` and `deity_eligibility_reason` and stays addressable. This "
            "query published 192 while it excluded structure='HUMAN' alone -- 7 danastuti "
            "labels and one non-divine subject above even the crude figure. "
            "`devatas_without_an_eligibility_ruling` is returned BESIDE the count and is the "
            "figure to read first: while it is 214 the ruling layer has not landed and "
            "`eligible_deities` falls back to curated structure and reads 185; when it is 0 "
            "the ruling is in force and the figure is 157. The transitional state is in the "
            "row rather than in this caveat, because a reader who takes a count from a row "
            "is exactly the reader who did not read the caveat. It is a denominator, not a "
            "census of gods. Dual labels are not decomposed into communities."
        ),
        serves=(23,),
    ),
    DomainQuery(
        name="deity_co_occurrence",
        question="Which deities are attributed to the same mantras?",
        cypher="""
        MATCH (p:Passage)-[:HAS_DEVATA]->(a:Devata)
        MATCH (p)-[:HAS_DEVATA]->(b:Devata)
        WHERE a.entity_key < b.entity_key
          AND a.is_deity = true
          AND b.is_deity = true
        RETURN a.display_label AS deity_a, b.display_label AS deity_b,
               count(DISTINCT p) AS shared_mantras
        ORDER BY shared_mantras DESC LIMIT 25
        """,
        caveat=(
            _SCOPE_CAVEAT
            + " "
            + _INHERIT_CAVEAT
            + " Both members are constrained by the one documented eligibility predicate "
            "`is_deity = true` (vedagraph.domain.deity_eligibility), which excludes the 22 "
            "human patrons AND the 7 danastuti gift-praise labels AND the 28 ABSTRACT "
            "labels ruled NOT_DEITY. The earlier `structure <> 'HUMAN'` kept danastuti, "
            "which has 50 dedications across 15 hymns and would carry 9 partner edges here "
            "-- and a top-ranked patron in a deity pair table is the exact answer this "
            "question was graded MISLEADING for once. The top 25 is unchanged by the "
            "switch today; the point is that it is now unchangeable by accident. This is a "
            "pair table, not a community partition."
        ),
        serves=(33, 35),
    ),
    DomainQuery(
        name="deities_through_common_rishis",
        question="Which deities are connected through the same seers?",
        cypher="""
        MATCH (p:Passage)-[:HAS_DEVATA]->(dv:Devata)
        MATCH (p)-[:HAS_RISHI]->(rs:Rishi)
        WITH rs, dv, count(DISTINCT p) AS n WHERE n > 4
        WITH rs, collect({deity: dv.display_label, mantras: n}) AS deities
        WHERE size(deities) > 1
        RETURN rs.display_label AS rishi, deities ORDER BY size(deities) DESC LIMIT 20
        """,
        caveat=_SCOPE_CAVEAT + " " + _INHERIT_CAVEAT,
        serves=(2, 19, 35),
    ),
    DomainQuery(
        name="rishis_invoking_deity",
        question="Which seers are most associated with this deity?",
        cypher="""
        MATCH (p:Passage)-[:HAS_DEVATA]->(:Devata {entity_key: $key})
        MATCH (p)-[r:HAS_RISHI]->(rs:Rishi)
        RETURN rs.display_label AS rishi, count(DISTINCT p) AS mantras,
               sum(CASE WHEN r.attribution_precision = 'PER_PASSAGE' THEN 1 ELSE 0 END)
                 AS source_stated
        ORDER BY mantras DESC LIMIT 15
        """,
        parameters={"key": AGNI},
        caveat=(
            "The `mantras` and `source_stated` columns can rank differently: 95.5% of "
            "HAS_RISHI is sukta-inherited. Prefer source_stated for a defensible claim."
        ),
        serves=(2, 19),
    ),
    DomainQuery(
        name="rishis_invoking_deity_strict",
        question="Which seers does the source itself name for this deity's mantras?",
        cypher="""
        MATCH (p:Passage)-[d:HAS_DEVATA]->(:Devata {entity_key: $key})
        MATCH (p)-[r:HAS_RISHI]->(rs:Rishi)
        WHERE d.attribution_precision = 'PER_PASSAGE'
          AND r.attribution_precision = 'PER_PASSAGE'
        RETURN rs.display_label AS rishi, count(DISTINCT p) AS mantras
        ORDER BY mantras DESC LIMIT 15
        """,
        parameters={"key": AGNI},
        caveat="Strict: both attributions source-stated. Small result sets are expected.",
        serves=(2, 19, 29),
    ),
    DomainQuery(
        name="deity_epithets",
        question="Which epithets does the graph record, and for whom?",
        cypher="""
        MATCH (dv:Devata)-[:HAS_EPITHET]->(ep:Epithet)
        RETURN dv.display_label AS deity, collect(ep.display_label) AS epithets
        ORDER BY size(epithets) DESC, deity
        """,
        caveat=(
            "Curated for major deities only (13 epithets total), so absence means "
            "uncurated rather than unattested."
        ),
        serves=(42,),
    ),
    DomainQuery(
        name="natural_phenomena_personified",
        question="Which natural phenomena does the corpus treat as deities?",
        cypher="""
        MATCH (dv:Devata)-[:DEVATA_ASSOCIATED_WITH]->(n:NaturalPhenomenon)
        OPTIONAL MATCH (dv)-[:EPITHET_VARIANT_OF]->(base:Devata)
        WITH n, coalesce(base, dv) AS resolved
        WHERE resolved.structure = 'INDIVIDUAL'
        RETURN n.display_label AS phenomenon,
               count(DISTINCT resolved) AS personifications,
               collect(DISTINCT resolved.display_label) AS deities
        ORDER BY personifications DESC, phenomenon
        """,
        caveat=(
            "Association, not identity. The registry refuses IS_GOD_OF and REPRESENTS by "
            "name: 'Agni is associated with fire' is recorded, 'Agni is the fire god' is not."
        ),
        serves=(41, 46),
    ),
    # ------------------------------------------- deities across all four Vedas
    #
    # Everything above this point reaches deities through HAS_DEVATA, which is the
    # Anukramani's sukta label and exists only for the Rigveda. The block below goes
    # through MENTIONS_DEVATA instead -- "is this deity named in this passage?" -- which
    # is the only deity predicate that reaches the whole corpus, and is therefore the
    # only one from which a cross-Veda answer can be built at all.
    DomainQuery(
        name="devatas_named_in_all_four_vedas",
        question="Which deities are named in all four Vedas, and how often in each?",
        # count(DISTINCT p), and count(DISTINCT CASE ... THEN p END) for the certain
        # subset, because a passage carries more than one mention edge to the same deity
        # when the deity's name occurs under several forms: 'the Asvins' reaches SV
        # UTTARA 8.3.9.1 through four matched_forms at once. count(*) would report that
        # passage four times and the corpus totals would exceed the corpus.
        cypher="""
        MATCH (p:Passage)-[m:MENTIONS_DEVATA]->(dv:Devata)
        WITH dv, p.veda AS veda, count(DISTINCT p) AS passages,
             count(DISTINCT CASE WHEN m.referent_certainty = 'DEITY_CERTAIN' THEN p END)
               AS certain,
             count(DISTINCT CASE WHEN m.referent_certainty = 'DEITY_PROBABLE' THEN p END)
               AS probable,
             count(DISTINCT CASE WHEN m.referent_certainty = 'DEITY_AMBIGUOUS' THEN p END)
               AS ambiguous,
             count(DISTINCT CASE WHEN m.referent_certainty IN $tiers THEN p END)
               AS default_scope
        WITH dv, collect([veda, passages, certain, probable, ambiguous, default_scope])
               AS per_veda,
             count(veda) AS vedas, sum(passages) AS total,
             sum(certain) AS total_certain, sum(probable) AS total_probable,
             sum(ambiguous) AS total_ambiguous, sum(default_scope) AS total_default_scope
        WHERE vedas = 4
        RETURN dv.display_label AS deity, total AS passages_naming,
               total_default_scope AS default_scope, total_certain AS deity_certain,
               total_probable AS deity_probable, total_ambiguous AS deity_ambiguous,
               per_veda
        ORDER BY default_scope DESC, passages_naming DESC, deity
        """,
        parameters={"tiers": _DEFAULT_TIERS},
        caveat=(
            "Complete, not a top-N: every deity naming all four corpora is returned. "
            "`per_veda` rows are [veda, passages, certain, probable, ambiguous, "
            "default_scope]. "
            "RANKED ON `default_scope`, WHICH IS CERTAIN + PROBABLE. This query previously "
            "reported only the CERTAIN column, and the V3.1 adversarial pass showed what "
            "that does: Agni read AV 476 passages against **0** certain, beside Indra's "
            "635 / 635 -- because the old two-way certainty split was a function of "
            "extraction path, so CERTAIN effectively meant 'came from the Rigvedic lemma "
            "annotation' and no non-Rigvedic mention of a deity whose name is also an "
            "ordinary noun could ever reach it. A reader comparing the certain columns "
            "would conclude Agni is absent from the Atharvaveda. All three tiers are now "
            "returned so no single column can be read as presence or absence on its own. "
            "Where the honest answer for a corpus is neither a count nor a zero, the "
            "per-deity profile carries `profile_mention_verdict_by_veda`, which returns "
            "INSUFFICIENT_EVIDENCE for 21 (deity, Veda) cells rather than a 0. Apah and "
            "Vac are the two deities the PROBABLE tier does NOT rescue -- gold scores them "
            "0.2500 and 0.0000 -- and they must not be rescued by widening a tier. "
            + _MENTION_LAYER_CAVEAT
        ),
        serves=(1, 21, 34, 36, 44),
    ),
    DomainQuery(
        name="devata_mention_certainty_by_veda",
        question="How much of the deity-mention layer is certain, per Veda and per method?",
        # One MATCH pattern, so count(*) here is a count of mention edges and is the
        # intended figure; count(DISTINCT p) is returned beside it because the two differ
        # (17,165 edges over fewer passages) and only the pair shows by how much.
        cypher="""
        MATCH (p:Passage)-[m:MENTIONS_DEVATA]->(:Devata)
        RETURN m.veda AS veda, m.extraction_path AS extraction_path,
               m.referent_certainty AS certainty, count(*) AS edges,
               count(DISTINCT p) AS passages
        ORDER BY veda, edges DESC
        """,
        caveat=(
            "This is the query to run before trusting any four-Veda deity count. It shows "
            "that DEITY_CERTAIN is a Rigvedic majority (5,900 of 10,284) and a minority "
            "everywhere else, and that the certainty grade is produced by two unlike "
            "methods -- rv-lemma-annotation against sanskrit-surface-token and "
            "sanskrit-surface-sandhi. Certainty is graded per entity-alias, not decided "
            "per occurrence, so it bounds the conflation rather than resolving it."
        ),
        serves=(29, 30, 45, 46),
    ),
    DomainQuery(
        name="deity_reach_named_versus_ascribed",
        question="Where do a deity's naming and its Anukramani ascription most disagree?",
        # The two counts sit in separate CALL subqueries for the reason
        # agni_deity_fire_medium documents: as sibling OPTIONAL MATCHes in one scope the
        # mention pattern multiplies the ascription pattern, and for Indra that is 3,196
        # x 2,869 rows collapsed into one figure.
        cypher="""
        MATCH (dv:Devata)
        CALL (dv) {
            MATCH (p:Passage)-[:MENTIONS_DEVATA]->(dv)
            RETURN count(DISTINCT p) AS named, count(DISTINCT p.veda) AS named_vedas
        }
        CALL (dv) {
            MATCH (p:Passage)-[:HAS_DEVATA]->(dv)
            RETURN count(DISTINCT p) AS ascribed
        }
        WITH dv, named, named_vedas, ascribed
        WHERE named + ascribed > 0
        RETURN dv.display_label AS deity, named, named_vedas, ascribed,
               named - ascribed AS mention_surplus
        ORDER BY abs(named - ascribed) DESC, deity LIMIT 25
        """,
        caveat=(
            "A top-25 by absolute divergence, deliberately not by either column, because "
            "the two measures diverge in both directions and neither is the corrected "
            "version of the other. `named` spans four corpora and `ascribed` one, so part "
            "of every gap is that asymmetry rather than usage; the informative rows are "
            "the ones where the sign is negative -- a deity a whole hymn is dedicated to "
            "and whose name the verses rarely say. " + _MENTION_LAYER_CAVEAT
        ),
        serves=(1, 29, 44, 46),
    ),
    DomainQuery(
        name="deity_pairs_far_above_chance",
        question="Which deity pairs co-occur far above chance, and where is the signal?",
        # Undirected. CO_OCCURS_WITH is written in one canonical direction only
        # (a.entity_key < b.entity_key), so a directed MATCH would silently return half
        # the pairs and a reader would never know which half. The WHERE re-imposes the
        # canonical order so the undirected traversal still yields each pair once.
        cypher="""
        MATCH (a:Devata)-[r:CO_OCCURS_WITH]-(b:Devata)
        WHERE a.entity_key < b.entity_key
          AND a.is_deity = true
          AND b.is_deity = true
        RETURN a.display_label AS deity_a, b.display_label AS deity_b,
               r.lift AS lift, r.passage_count AS shared_passages,
               r.rv_passage_count AS rigvedic, r.non_rv_passage_count AS non_rigvedic,
               r.vedas AS vedas, r.per_veda_counts AS per_veda_counts
        ORDER BY lift DESC, shared_passages DESC LIMIT 25
        """,
        caveat=(
            "A top-25 of 292 pairs by lift. Lift is co-occurrence over the product of the "
            "marginals, so a pair sharing few passages can outrank a frequent one, and the "
            "`rigvedic`/`non_rigvedic` split is returned precisely so the reader can see "
            "whether a headline pair is a corpus-wide fact or a Rigvedic one. Mitra-Varuna "
            "at lift 13.2 is 228 Rigvedic against 43 elsewhere. Co-occurrence is adjacency "
            "in one passage, not co-invocation: where the tradition means a pair it uses a "
            "dual deity, which is its own entity. " + _MENTION_LAYER_CAVEAT
        ),
        serves=(33, 35),
    ),
    DomainQuery(
        name="deity_pairs_not_rigvedic",
        question="Which deity pairings does the corpus outside the Rigveda make its own?",
        cypher="""
        MATCH (a:Devata)-[r:CO_OCCURS_WITH]-(b:Devata)
        WHERE a.entity_key < b.entity_key
          AND a.is_deity = true
          AND b.is_deity = true
          AND r.non_rv_passage_count > r.rv_passage_count
        RETURN a.display_label AS deity_a, b.display_label AS deity_b,
               r.lift AS lift, r.rv_passage_count AS rigvedic,
               r.non_rv_passage_count AS non_rigvedic,
               r.per_veda_counts AS per_veda_counts, r.vedas AS vedas
        ORDER BY non_rigvedic DESC, lift DESC
        """,
        caveat=(
            "Complete, not a top-N: all 70 of the 292 pairs whose evidence is majority "
            "non-Rigvedic. This is the one deity question on which the later corpora "
            "outvote the Rigveda, and it is worth reading against the fact that the "
            f"Rigveda contributes {figures.MENTIONS_DEVATA_BY_VEDA['RV']:,} of the "
            f"{figures.PREDICATE_TOTALS['MENTIONS_DEVATA']:,} mention edges: a pair that still "
            "comes out non-RV-majority against that weighting is a real Yajurvedic or "
            "Atharvavedic association. `per_veda_counts` is ordered [RV, SV, YV, AV]. "
            + _MENTION_LAYER_CAVEAT
        ),
        serves=(1, 33, 36),
    ),
    DomainQuery(
        name="deity_mention_surface_forms",
        question="Which written forms of a deity's name actually carry the mentions?",
        cypher="""
        MATCH (p:Passage)-[m:MENTIONS_DEVATA]->(:Devata {entity_key: $key})
        UNWIND m.matched_forms AS form
        RETURN m.veda AS veda, form, m.referent_certainty AS certainty,
               count(DISTINCT p) AS passages
        ORDER BY passages DESC, veda, form LIMIT 30
        """,
        parameters={"key": AGNI},
        caveat=(
            "A top-30 by passage count. `occurrences` is deliberately not summed here: it "
            "is a per-edge total across all of that edge's forms, so after UNWIND it would "
            "be charged in full to each form and the column would exceed the text. This is "
            "the query that shows why Agni's certainty grade is what it is -- the forms are "
            "the ordinary inflections of the word for fire. " + _MENTION_LAYER_CAVEAT
        ),
        serves=(42, 45, 46),
    ),
    DomainQuery(
        name="soma_certainty_across_the_corpus",
        question="Where is a deity's name certainly the deity, and where cannot we tell?",
        cypher="""
        MATCH (p:Passage)-[m:MENTIONS_DEVATA]->(:Devata {entity_key: $key})
        RETURN m.veda AS veda, m.extraction_path AS extraction_path,
               count(DISTINCT CASE WHEN m.referent_certainty = 'DEITY_CERTAIN' THEN p END)
                 AS deity_certain,
               count(DISTINCT CASE WHEN m.referent_certainty = 'DEITY_PROBABLE' THEN p END)
                 AS deity_probable,
               count(DISTINCT CASE WHEN m.referent_certainty = 'DEITY_AMBIGUOUS' THEN p END)
                 AS ambiguous,
               count(DISTINCT p) AS passages
        ORDER BY passages DESC
        """,
        parameters={"key": SOMA},
        caveat=(
            "ALL THREE TIERS ARE RETURNED and the columns reconcile against `passages`. "
            "This query previously returned certain and ambiguous only, which did not "
            "contrast two tiers -- it OMITTED one: Samavedic Soma read 0 certain and 116 "
            "ambiguous beside 213 passages, so 97 PROBABLE mentions, 46% of SV Soma and "
            "its largest probable count anywhere, sat in no column and the row did not add "
            "up. A row whose parts do not sum to its own total is worse than a missing "
            "column, because it looks complete. "
            "Defaults to Soma, where the ambiguity is not a defect in the matcher but the "
            "subject matter: soma is the god and the pressed drink and the plant, and the "
            "corpus does not lexically separate them. See soma_deity_versus_substance for "
            "the deity/substance cross-tab and VG:CLAIM:AGNI-LEXICALLY-UNDIFFERENTIATED "
            "for the same problem stated in the graph. " + _MENTION_LAYER_CAVEAT
        ),
        serves=(17, 45, 46),
    ),
    DomainQuery(
        name="rv_family_books_versus_outer_books",
        question="Which deities are named more in the RV's family books than its outer ones?",
        # The corpus denominators are computed in a leading CALL subquery rather than
        # hard-coded, so the shares stay correct if the RV is ever reloaded. Mandala comes
        # from substring(canonical_key, 10, 3) because Passage.structural_path is still an
        # empty array on the Rigveda -- there is no structural property to group on.
        cypher="""
        CALL () {
            MATCH (q:Passage:Mantra {veda: 'RV'})
            RETURN count(CASE WHEN substring(q.canonical_key, 10, 3) IN $family THEN 1 END)
                     AS family_total,
                   count(CASE WHEN substring(q.canonical_key, 10, 3) IN $outer THEN 1 END)
                     AS outer_total
        }
        MATCH (p:Passage:Mantra {veda: 'RV'})-[m:MENTIONS_DEVATA]->(dv:Devata)
        WHERE m.referent_certainty IN $tiers
        WITH family_total, outer_total, dv,
             count(DISTINCT CASE WHEN substring(p.canonical_key, 10, 3) IN $family
                                 THEN p END) AS family_books,
             count(DISTINCT CASE WHEN substring(p.canonical_key, 10, 3) IN $outer
                                 THEN p END) AS outer_books
        WHERE family_books + outer_books >= 20
        RETURN dv.display_label AS deity, family_books, outer_books,
               round(1000.0 * family_books / family_total) / 10.0 AS family_pct,
               round(1000.0 * outer_books / outer_total) / 10.0 AS outer_pct
        ORDER BY family_books + outer_books DESC, deity LIMIT 25
        """,
        parameters={
            "family": ["M02", "M03", "M04", "M05", "M06", "M07"],
            "outer": ["M01", "M08", "M09", "M10"],
            "tiers": _DEFAULT_TIERS,
        },
        caveat=(
            "A top-25 of the deities with at least 20 certain mentions. The family-book / "
            "outer-book split is the conventional stratigraphic reading of the Rigveda and "
            "is an interpretation imported by this query, not a property in the graph: "
            "Passage carries no layer, period or date, so this is the nearest the corpus "
            "comes to a diachronic question and it substitutes book order for time. "
            "Restricted to the product DEFAULT referent tiers -- DEITY_CERTAIN plus "
            "DEITY_PROBABLE -- so the comparison is not driven by the ambiguous "
            "common-noun aliases, which would move both columns together anyway. It "
            "previously hard-coded DEITY_CERTAIN, which silently dropped the Rigveda's "
            "1,007 PROBABLE mentions; pass tiers=" + repr(_STRICT_TIERS) + " for the "
            "strict comparison or " + repr(_EXPLORATORY_TIERS) + " for exploratory mode. "
            "DEITY_PROBABLE carries a measured Wilson lower bound of 0.90 on 55 gold rows, "
            "and its worst alias is `surya` for VG:DEVATA:SURYAH at 2 of 3, where a "
            "recorded VOCATIVE can be a sandhi-reduced nominative -- a caller who needs "
            "Surya specifically should read referent_basis rather than trust the tier."
        ),
        serves=(24, 30, 36),
    ),
    # ------------------------------------------------- actions and assertions
    #
    # "Who does what to whom" -- the reified assertion layer and the two derived
    # aggregates over it. Everything in this block is Rigvedic, because everything in it
    # descends from the Rigveda-only lemma annotation, and every caveat says so with the
    # measured number rather than leaving the reader to infer it from a table of zeroes.
    DomainQuery(
        name="deity_actions_performed",
        question="What does the corpus say a deity does?",
        cypher="""
        MATCH (dv:Devata)-[r:PERFORMS_ACTION]->(ap:ActionPredicate)
        RETURN dv.display_label AS deity, ap.predicate AS action,
               r.assertion_count AS assertions, r.passage_count AS passages,
               r.roots AS verbal_roots, ap.argument_frame AS argument_frame
        ORDER BY assertions DESC, deity, action LIMIT 30
        """,
        caveat=(
            "A top-30 of 441 edges. PERFORMS_ACTION is the ASSERTED frame: an indicative "
            "or participial clause whose agent is the deity. It is not a claim about myth "
            "-- IS_OR_BECOMES leads the table because √bhū- and √as- are the commonest "
            "verbs in the language, not because being is Indra's characteristic act. "
            "Rank within one predicate, or read deity_actions_requested beside this. "
            + _ACTION_SCOPE_CAVEAT
        ),
        serves=(17, 18, 20, 43),
    ),
    DomainQuery(
        name="deity_actions_requested",
        question="What does the corpus ask a deity to do?",
        cypher="""
        MATCH (dv:Devata)-[r:IS_ASKED_TO]->(ap:ActionPredicate)
        RETURN dv.display_label AS deity, ap.predicate AS action,
               r.assertion_count AS assertions, r.passage_count AS passages,
               r.roots AS verbal_roots, ap.argument_frame AS argument_frame
        ORDER BY assertions DESC, deity, action LIMIT 30
        """,
        caveat=(
            "A top-30 of 224 edges. IS_ASKED_TO is the REQUESTED frame -- imperative, "
            "injunctive or optative -- so this is the corpus's petition, which is a "
            "different question from what it narrates, and the two rankings are not the "
            "same. 849 of the 2,406 rule-derived assertions are REQUESTED against 1,557 "
            "ASSERTED, so the requested table is the smaller of the two by construction. "
            + _ACTION_SCOPE_CAVEAT
        ),
        serves=(12, 18, 32),
    ),
    DomainQuery(
        name="deity_asserted_versus_requested",
        question="For one deity, what is it said to do versus what is it asked to do?",
        cypher="""
        MATCH (dv:Devata {entity_key: $key})-[r:PERFORMS_ACTION|IS_ASKED_TO]->
              (ap:ActionPredicate)
        WITH ap,
             sum(CASE WHEN type(r) = 'PERFORMS_ACTION' THEN r.assertion_count ELSE 0 END)
               AS asserted,
             sum(CASE WHEN type(r) = 'IS_ASKED_TO' THEN r.assertion_count ELSE 0 END)
               AS requested
        RETURN ap.predicate AS action, ap.argument_frame AS argument_frame,
               asserted, requested, asserted - requested AS asserted_bias
        ORDER BY asserted + requested DESC, action
        """,
        parameters={"key": INDRA},
        caveat=(
            "Complete for the named deity, not a top-N: the whole repertoire the "
            "annotation records for it. The contrast is the point -- a positive "
            "`asserted_bias` is something the hymns narrate the deity doing, a negative "
            "one something they ask of it -- but both columns count clauses in the "
            "Rigveda's lemma annotation, so a zero is silence in that annotation. "
            + _ACTION_SCOPE_CAVEAT
        ),
        serves=(17, 18, 43, 44),
    ),
    DomainQuery(
        name="action_predicate_breadth",
        question="Which actions does the corpus spread across many deities, and which few?",
        cypher="""
        MATCH (dv:Devata)-[r:PERFORMS_ACTION|IS_ASKED_TO]->(ap:ActionPredicate)
        RETURN ap.predicate AS action, ap.argument_frame AS argument_frame,
               count(DISTINCT dv) AS deities,
               count(DISTINCT CASE WHEN dv.structure = 'INDIVIDUAL' THEN dv END)
                 AS individual_deities,
               count(DISTINCT CASE WHEN dv.structure <> 'INDIVIDUAL' THEN dv END)
                 AS pair_group_and_other_subjects,
               count(DISTINCT CASE WHEN type(r) = 'PERFORMS_ACTION' THEN dv END)
                 AS deities_asserted,
               count(DISTINCT CASE WHEN type(r) = 'IS_ASKED_TO' THEN dv END)
                 AS deities_asked,
               sum(r.assertion_count) AS assertions, ap.root_count AS roots_in_vocabulary
        ORDER BY deities DESC, assertions DESC, action
        """,
        caveat=(
            "Complete over the 40 ActionPredicates the annotation reaches. count(DISTINCT "
            "dv) rather than count(*), because a deity contributes up to two edges to the "
            "same predicate -- one per frame -- and counting rows would report every "
            "deity that is both said to do a thing and asked to do it twice. A narrow "
            "predicate can be narrow because it is specific (FLOWS is Soma's) or because "
            "the vocabulary barely covers it (HEALS reaches 4 root tokens in the whole "
            "Rigveda); `roots_in_vocabulary` is returned to let those be told apart. "
            + _ACTION_SCOPE_CAVEAT
        ),
        serves=(18, 38, 46),
    ),
    DomainQuery(
        name="deity_action_repertoire_breadth",
        question="Which deities have the widest range of recorded action?",
        cypher="""
        MATCH (dv:Devata)-[r:PERFORMS_ACTION|IS_ASKED_TO]->(ap:ActionPredicate)
        RETURN dv.display_label AS deity, count(DISTINCT ap) AS distinct_actions,
               count(DISTINCT CASE WHEN type(r) = 'PERFORMS_ACTION' THEN ap END)
                 AS asserted_actions,
               count(DISTINCT CASE WHEN type(r) = 'IS_ASKED_TO' THEN ap END)
                 AS requested_actions,
               sum(r.assertion_count) AS assertions
        ORDER BY distinct_actions DESC, assertions DESC, deity LIMIT 25
        """,
        caveat=(
            "A top-25. This answers 'widest functional range' from clauses in the text "
            "rather than from the curated axis taxonomy that deity_widest_range uses, and "
            "the two disagree usefully: the axis version is topped by composite Anukramani "
            "labels that inherit the union of their parts' axes, while this one is topped "
            "by the deities the annotation actually has most verbs for. Neither is the "
            "corrected version of the other -- this measures annotation volume, so it "
            "tracks prominence in the Rigveda. " + _ACTION_SCOPE_CAVEAT
        ),
        serves=(18, 38, 46),
    ),
    DomainQuery(
        name="deities_who_heal_and_protect",
        question="Which deities are associated with healing and protection?",
        cypher="""
        MATCH (dv:Devata)-[r:PERFORMS_ACTION|IS_ASKED_TO]->(ap:ActionPredicate)
        WHERE ap.predicate IN $actions
        RETURN ap.predicate AS action, type(r) AS frame, dv.display_label AS deity,
               r.assertion_count AS assertions, r.roots AS verbal_roots
        ORDER BY assertions DESC, action, deity LIMIT 30
        """,
        parameters={"actions": ["HEALS", "PROTECTS", "RESCUES", "BLESSES", "RELEASES", "PURIFIES"]},
        caveat=(
            "A top-30. HEALS is deliberately in the filter and contributes almost nothing: "
            "the predicate exists, its vocabulary covers 2 roots, and the whole Rigveda "
            "yields 4 root tokens and 1 assertion for it. So the answer to question 12 is "
            "carried by the adjacent predicates -- PROTECTS, RESCUES, BLESSES, PURIFIES -- "
            "and the healing question proper is answered on the Atharvavedic side by TREATS "
            "and PROTECTS_FROM, which are a different layer with a different tier. "
            + _ACTION_SCOPE_CAVEAT
        ),
        serves=(12, 18, 47),
    ),
    DomainQuery(
        name="who_does_what_to_whom",
        question="Which passages state a full action frame: agent, act, patient, recipient?",
        cypher="""
        MATCH (p:Passage)-[:HAS_SEMANTIC_ASSERTION]->
              (s:SemanticAssertion {derivation: 'MORPHOLOGY_RULE'})
        // :Devata is correct here and must stay. This query is scoped to MORPHOLOGY_RULE,
        // whose 2,406 agents are all deities; the 58 non-deity agents GAP-SEMANTICS-003
        // added carry derivation TREEBANK_DEPREL_ROLE_PROJECTION and belong to a different
        // layer. Widening it would blend two derivations into one answer.
        MATCH (s)-[:ASSERTION_AGENT]->(agent:Devata)
        MATCH (s)-[:ASSERTION_PREDICATE]->(ap:ActionPredicate)
        WHERE s.patient <> '' AND s.beneficiary <> ''
        RETURN p.canonical_citation AS passage, agent.display_label AS agent,
               ap.predicate AS predicate, s.frame AS frame,
               s.agent_surface AS agent_surface, s.patient AS patient,
               s.instrument AS instrument, s.beneficiary AS beneficiary,
               s.root_label AS verbal_root
        ORDER BY passage, predicate LIMIT 30
        """,
        caveat=(
            "A top-30 by citation of the 174 rule-derived assertions carrying both a "
            "patient and a beneficiary; 546 of the 2,406 carry no role at all beyond the "
            "agent. Filtered to derivation = 'MORPHOLOGY_RULE' on purpose: the roles here "
            "are Sanskrit case forms read off the annotation, and mixing in the "
            "MODEL_EXTRACTION layer would put English paraphrase in the same columns. "
            "Roles are the rule's reading of the morphology, not a syntactic parse -- an "
            "accusative is recorded as PATIENT whether or not it is the verb's object. "
            + _ASSERTION_LAYER_CAVEAT
        ),
        serves=(17, 18, 29),
    ),
    DomainQuery(
        name="assertion_layers_reported_separately",
        question="What are the two semantic-assertion layers, and how far does each reach?",
        cypher="""
        MATCH (p:Passage)-[:HAS_SEMANTIC_ASSERTION]->(s:SemanticAssertion)
        RETURN s.derivation AS derivation, s.quality_tier AS tier,
               s.knowledge_layer AS knowledge_layer, s.evidence_basis AS evidence_basis,
               s.review_state AS review_state, s.human_gold_status AS human_gold,
               count(DISTINCT s) AS assertions, count(DISTINCT p) AS passages,
               collect(DISTINCT p.veda) AS vedas
        ORDER BY assertions DESC
        """,
        caveat=(
            "Complete, and the shape of the result is the answer: two rows, never one. "
            "This is the query to run before any aggregate over SemanticAssertion, because "
            "a single figure over both rows blends a rule applied to manual Sanskrit "
            "annotation with unreviewed model output over an English translation. "
            + _ASSERTION_LAYER_CAVEAT
        ),
        serves=(29, 30),
    ),
    DomainQuery(
        name="model_assertion_claims",
        question="What does the model-extracted assertion layer claim, and how sure is it?",
        cypher="""
        MATCH (p:Passage)-[:HAS_SEMANTIC_ASSERTION]->
              (s:SemanticAssertion {derivation: 'MODEL_EXTRACTION'})
        OPTIONAL MATCH (s)-[:ASSERTION_TARGET]->(t:Devata)
        RETURN s.semantic_predicate AS predicate, s.explicitness AS explicitness,
               s.object_kind AS object_kind, count(DISTINCT s) AS assertions,
               count(DISTINCT p) AS passages, count(DISTINCT t) AS deity_targets,
               count(DISTINCT CASE WHEN t.is_deity THEN t END) AS eligible_deity_targets,
               collect(DISTINCT s.review_state)[0..3] AS review_state,
               collect(DISTINCT s.human_gold_status)[0..3] AS human_gold
        ORDER BY assertions DESC, predicate
        """,
        caveat=(
            "Complete over the 2,459 model-extracted assertions, every one of which is "
            "review_state = UNREVIEWED and human_gold_status = UNANNOTATED -- the columns "
            "are returned rather than filtered out so that fact travels with the answer. "
            "`explicitness` splits EXPLICIT from STRONG_INFERENCE, and the second is the "
            "model's own judgement about its own reach. Extracted from Griffith's English, "
            "so a claim here is evidence about a translation. Only 799 of these carry an "
            "ASSERTION_TARGET, so `deity_targets` is far below `assertions` by design. "
            "`deity_targets` counts :Devata nodes, and that label is the slot the "
            "Anukramani deity apparatus projects into, so it holds 22 human patrons and 7 "
            "danastuti gift-praise labels as well as deities. `eligible_deity_targets` is "
            "the same count under the one documented predicate `t.is_deity = true`. Both "
            "read 27 today, so the model layer targets no non-deity; they are returned as "
            "two columns rather than one so a future divergence is visible instead of "
            "silent. "
            + _ASSERTION_LAYER_CAVEAT
        ),
        serves=(29, 30),
    ),
    DomainQuery(
        name="assertions_on_one_passage",
        question="What do both assertion layers say about one passage, side by side?",
        cypher="""
        MATCH (p:Passage {canonical_key: $key})-[:HAS_SEMANTIC_ASSERTION]->
              (s:SemanticAssertion)
        // Untyped on purpose. Both predicates are declared over
        // {Devata, DomainEntity} and GAP-SEMANTICS-003 populated the second half, so a
        // :Devata-typed pattern here would silently drop 103 non-deity targets and 58
        // non-deity agents -- reporting a slot as empty because the filler is a substance
        // rather than a god.
        OPTIONAL MATCH (s)-[:ASSERTION_AGENT]->(agent)
        OPTIONAL MATCH (s)-[:ASSERTION_PREDICATE]->(ap:ActionPredicate)
        OPTIONAL MATCH (s)-[:ASSERTION_TARGET]->(target)
        RETURN s.derivation AS derivation, s.quality_tier AS tier,
               coalesce(ap.predicate, s.semantic_predicate) AS predicate,
               s.frame AS frame, agent.display_label AS agent,
               target.display_label AS target, s.agent_surface AS agent_surface,
               s.patient AS patient, s.normalized_head AS model_head,
               s.evidence_basis AS evidence_basis, s.review_state AS review_state
        ORDER BY derivation, predicate
        """,
        parameters={"key": "VG:RV:SAK:M07:S056:V025"},
        caveat=(
            "The evidence-debugging entry point: one passage, both layers, tier attached "
            "to every row. The default is RV 7.56.25, which carries 13 assertions from "
            "both derivations and so shows the two vocabularies next to each other -- the "
            "rule layer's typed predicate with a Sanskrit agent_surface, the model layer's "
            "English `model_head`. `frame` and `patient` populate only for the rule layer "
            "and `model_head` only for the model layer; the nulls are the layers, not "
            "missing data. " + _ASSERTION_LAYER_CAVEAT
        ),
        serves=(18, 29, 30),
    ),
    DomainQuery(
        name="action_vocabulary_coverage",
        question="Which action predicates does the vocabulary declare but the text never fill?",
        cypher="""
        MATCH (ap:ActionPredicate)
        OPTIONAL MATCH (ap)<-[:ASSERTION_PREDICATE]-(s:SemanticAssertion)
        WITH ap, count(DISTINCT s) AS assertions
        RETURN ap.predicate AS action, ap.root_count AS roots_in_vocabulary,
               ap.root_tokens AS root_tokens_in_corpus,
               ap.layer_veda_scope AS layer_veda_scope, assertions
        ORDER BY assertions ASC, action
        """,
        caveat=(
            "Complete over all 41 predicates, ordered so the empty end of the vocabulary "
            "comes first. CURSES is the clean case: 5 roots declared, 35 root tokens in "
            "the corpus, 0 assertions, and layer_veda_scope = [] -- the one predicate that "
            "reaches no Veda at all, which is what an empty scope list is for. A low count "
            "here is a statement about the derivation rule, not about the Vedas: the rule "
            "fires only where the annotation gives it an agent it can resolve to a Devata."
        ),
        serves=(18, 29, 30),
    ),
    DomainQuery(
        name="unmapped_verbal_roots",
        question="Which verbal roots does the predicate vocabulary fail to classify?",
        cypher="""
        MATCH (dv:Devata)-[r:PERFORMS_ACTION|IS_ASKED_TO]->
              (ap:ActionPredicate {predicate: 'UNMAPPED_ROOT'})
        RETURN dv.display_label AS deity, type(r) AS frame,
               r.assertion_count AS assertions, r.roots AS unmapped_roots
        ORDER BY assertions DESC, deity LIMIT 20
        """,
        caveat=(
            "A top-20 of the residual. UNMAPPED_ROOT is a real bucket in the graph rather "
            "than a discard, so the size of what the vocabulary does not cover is "
            "measurable instead of merely absent: these assertions were derived, and the "
            "root was recognised, and no predicate matched it. Reading it as a deity's "
            "actions would be wrong -- the row means the opposite. " + _ACTION_SCOPE_CAVEAT
        ),
        serves=(18, 29),
    ),
    # ------------------------------------------------------- material culture
    DomainQuery(
        name="crops_by_veda",
        question="Which crops occur in each Veda?",
        cypher="""
        MATCH (p:Passage)-[m:MENTIONS_ENTITY]->(c:Crop)
        RETURN c.display_label AS crop, p.veda AS veda, count(DISTINCT p) AS mantras
        ORDER BY crop, mantras DESC
        """,
        caveat=(
            "Lexical mentions on Sanskrit evidence. A mention is not a claim that the "
            "passage is about agriculture."
        ),
        serves=(9, 48),
    ),
    DomainQuery(
        name="metals_by_veda",
        question="Which metals occur in each Veda?",
        cypher="""
        MATCH (m:Mantra)
        WITH m.veda AS veda, count(*) AS corpus_mantras
        MATCH (x:Metal)
        OPTIONAL MATCH (p:Passage)-[mn:MENTIONS_ENTITY]->(x)
          WHERE p.veda = veda
        WITH veda, corpus_mantras, x,
             count(DISTINCT p) AS mantras,
             collect(DISTINCT mn.matched_aliases)[0..3] AS sample_aliases
        RETURN x.display_label AS metal, veda, mantras,
               round(1000.0 * mantras / corpus_mantras, 3) AS per_1000_mantras,
               corpus_mantras, sample_aliases,
               CASE WHEN mantras = 0 THEN 'NO_LEXICAL_MATCH'
                    ELSE 'LEXICAL_MATCH_MINIMUM' END AS evidence_status
        ORDER BY metal, per_1000_mantras DESC
        """,
        caveat=(
            "Every metal is returned against every Veda, so a cell that found nothing says "
            "NO_LEXICAL_MATCH in its own row rather than going missing: absence here is a "
            "fact about the matcher, never about the text. That distinction is load-bearing "
            "and there is a known false cell. The Yajurveda names ayas at VSM 18.13, where "
            "the Devanagari source writes it with avagraha elision (`me `yas ca me`) and it "
            "folds to the token `yasca`, which is the relative pronoun in 11 of its 12 "
            "corpus occurrences; registering it would land 11 wrong-sense mentions, so ayas "
            "reads NO_LEXICAL_MATCH for YV although that verse names it. `ayo` was rejected "
            "on the same precision test -- 6 token hits, of which only about half are the "
            "metal. Aliases are whole-word inflections only: the bare stem `ayas` "
            "substring-matches 645 times inside payasa/madayasva, and the bare `syama` "
            "token-matches a verb form at RV 6.5.7 and sits inside asyama 22 times, so only "
            "the attested `syamam`/`syamam` forms are admitted. Counts are lower bounds. "
            "`per_1000_mantras` is the figure to compare Vedas on, and it reorders the raw "
            "counts: gold is RV 38 against AV 34 raw but 3.601 against 5.823 normalised."
        ),
        serves=(10,),
    ),
    DomainQuery(
        name="animals_by_veda",
        question="Which animals occur in each Veda?",
        cypher="""
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(a:Animal)
        RETURN a.display_label AS animal, p.veda AS veda, count(DISTINCT p) AS mantras
        ORDER BY animal, mantras DESC
        """,
        caveat="Lexical mentions only.",
        serves=(11, 48),
    ),
    DomainQuery(
        name="animals_with_wealth",
        question="Which animals co-occur with wealth vocabulary?",
        cypher="""
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(a:Animal)
        MATCH (p)-[:MENTIONS_ENTITY]->(w:DomainEntity)
        WHERE w.entity_key IN $wealth
        RETURN a.display_label AS animal, w.display_label AS wealth_term,
               count(DISTINCT p) AS mantras
        ORDER BY mantras DESC LIMIT 20
        """,
        parameters={"wealth": ["VG:CONCEPT:VASU-WEALTH", "VG:CONCEPT:HIRANYA-GOLD"]},
        caveat=(
            "Co-occurrence in one mantra, not a stated relation. Cattle-as-wealth is a "
            "real Vedic association, but this query measures adjacency only."
        ),
        serves=(11, 48),
    ),
    DomainQuery(
        name="weapons_and_deities",
        question="Which weapons and objects belong to which deity's narratives?",
        cypher="""
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(w:Object)
        MATCH (p)-[:HAS_DEVATA]->(dv:Devata)
        RETURN w.display_label AS object, w.display_type AS kind,
               dv.display_label AS deity, count(DISTINCT p) AS mantras
        ORDER BY mantras DESC LIMIT 25
        """,
        caveat=_SCOPE_CAVEAT + " " + _INHERIT_CAVEAT + " Co-occurrence, not possession.",
        serves=(40,),
    ),
    DomainQuery(
        name="ritual_objects_recurring",
        question="Which curated ritual implements have recurring lexical matches?",
        cypher="""
        MATCH (r:Ritual)-[:USES_OBJECT]->(o:Object)
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(o)
        RETURN o.display_label AS ritual_implement, o.display_type AS registry_type,
               count(DISTINCT p) AS matched_mantras_minimum,
               count(DISTINCT p.veda) AS vedas_with_matches,
               count(DISTINCT r) AS curated_rituals,
               'PARTIAL_ALIAS_RECALL' AS evidence_status
        ORDER BY matched_mantras_minimum DESC
        """,
        caveat=(
            "Ritual implement means an Object explicitly used by a curated Ritual via "
            "USES_OBJECT; it is not the flat Object class, so chariots and thunderbolts "
            "are not silently ranked as ritual apparatus. `registry_type` is shown because "
            "one implement (the axe) is registered as a Weapon and is a ritual tool anyway. "
            "Counts are conservative Sanskrit lexical-match minima over the four Samhitas, "
            "not complete frequencies, and the shortfall is measured rather than assumed. "
            "Eleven mantras carry a yupa-word (one of them the place-name Hariyupiya); this "
            "query reaches 6, of which only 3 are yupa forms and 3 arrive through the "
            "`svaravah` alias, and it reaches neither Yajurvedic witness (VSM 19.17, 25.29) "
            "because both are compounds or inflections not registered, so `vedas_with_"
            "matches` for yupa reads 2 where the text attests 3. Ranking therefore tracks "
            "alias coverage as much as textual frequency. Separately, the corpus itself is "
            "the ceiling for the srauta apparatus: the Brahmana and Srautasutra prose that "
            "describes it is not in the corpus at all. A low or absent count must not be "
            "read as absence from a Veda. The class is also the curated one -- amulet "
            "(mani, 86 mentions), drum (dundubhi, 17) and the udumbara amulet are genuine "
            "ritual objects absent here only because no Ritual was wired to them."
        ),
        serves=(25,),
    ),
    DomainQuery(
        name="rivers_mentioned",
        question="Which rivers does the corpus name, and where?",
        cypher="""
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(r:River)
        RETURN r.display_label AS river, p.veda AS veda, count(DISTINCT p) AS mantras
        ORDER BY river, mantras DESC
        """,
        caveat=(
            "There is deliberately no Sarasvati RIVER node: its forms match 172 mantras "
            "of which the great majority are the goddess, and a river node claiming them "
            "would assert 'this passage is about a river' of passages about a deity. "
            "Ancient names are not mapped to modern identifications."
        ),
        serves=(26,),
    ),
    DomainQuery(
        name="tribes_mentioned",
        question="Which tribes and clans does the corpus name, and where?",
        cypher="""
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(t:Tribe)
        RETURN t.display_label AS tribe, p.veda AS veda, count(DISTINCT p) AS mantras,
               collect(p.canonical_citation)[0..5] AS examples
        ORDER BY mantras DESC
        """,
        caveat=(
            "Five tribes, 42 mentions. Published separately from rivers_and_tribes "
            "because the join of the two is empty: the tribes are attested and the "
            "rivers are attested, and they never share a mantra in this corpus."
        ),
        serves=(26,),
    ),
    DomainQuery(
        name="rivers_and_tribes",
        question="Which rivers occur with which tribes or clans?",
        cypher="""
        CALL () {
            MATCH (p:Passage)-[:MENTIONS_ENTITY]->(r:River)
            MATCH (p)-[:MENTIONS_ENTITY]->(t:Tribe)
            RETURN r.display_label AS river, t.display_label AS tribe,
                   count(DISTINCT p) AS mantras,
                   collect(p.canonical_citation)[0..4] AS examples
            ORDER BY mantras DESC LIMIT 20
        }
        RETURN river, tribe, mantras, examples, NULL AS census
        UNION ALL
        CALL () {
            MATCH (p:Passage)-[:MENTIONS_ENTITY]->(r:River)
            RETURN count(DISTINCT p) AS river_passages, count(DISTINCT r) AS rivers
        }
        CALL () {
            MATCH (p:Passage)-[:MENTIONS_ENTITY]->(t:Tribe)
            RETURN count(DISTINCT p) AS tribe_passages, count(DISTINCT t) AS tribes
        }
        CALL () {
            MATCH (p:Passage)-[:MENTIONS_ENTITY]->(:River)
            MATCH (p)-[:MENTIONS_ENTITY]->(:Tribe)
            RETURN count(DISTINCT p) AS both
        }
        RETURN NULL AS river, NULL AS tribe, both AS mantras, [] AS examples,
               'MEASURED AT QUERY TIME: ' + toString(rivers) + ' rivers over '
               + toString(river_passages) + ' passages; ' + toString(tribes)
               + ' tribes over ' + toString(tribe_passages) + ' passages; '
               + toString(both) + ' passages naming one of each' AS census
        """,
        caveat=(
            "The co-occurrence result is EMPTY, and that is a measured finding rather than "
            "a missing feature: no mantra in this corpus names both a river and a tribe, "
            "so Q26 is not answerable by co-occurrence here. The final row carries the "
            "census MEASURED AT QUERY TIME, which is the V3.1 correction: this caveat "
            "previously asserted '12 river mentions' against a live 249 edges over 243 "
            "passages and 8 rivers, because a later lexicon pass grew the river layer "
            "twentyfold and the hand-written figure was never revisited. The conclusion "
            "survived the drift and the number did not, which is exactly why a figure a "
            "reader might act on belongs in a row rather than in a caveat. See "
            "tribes_mentioned and rivers_mentioned."
        ),
        serves=(26,),
    ),
    # ---------------------------------------------------- Atharvaveda concerns
    DomainQuery(
        name="human_concerns_by_veda",
        question="Which human concerns does each Veda address?",
        cypher="""
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(h:HumanConcern)
        RETURN h.display_label AS concern, p.veda AS veda, count(DISTINCT p) AS mantras
        ORDER BY concern, mantras DESC
        """,
        caveat=(
            "A passage naming a concern is evidence it concerns it, not that it prescribes "
            "a remedy for it."
        ),
        serves=(13, 14, 15, 16, 32, 47, 48),
    ),
    DomainQuery(
        name="conditions_treated",
        question="Which afflictions do passages address, and in which Veda?",
        # Filtered on `condition_kind`, NOT on the [:TREATS] predicate, and the difference
        # matters. TREATS and PROTECTS_FROM are whitelists graded on evidence strength --
        # whether the corpus prints an explicit remedy compound, or whether the match set
        # was small enough to read to the end -- not on what kind of thing the target is.
        # So PROTECTS_FROM carries 181 affliction edges over six entities, and filtering by
        # predicate here would drop yaksma, amiva, rapas, grahi, sedi and the evil dream:
        # consumption, the corpus's most-attested disease, among them.
        cypher="""
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(c:Condition)
        WHERE c.condition_kind = 'AFFLICTION'
        RETURN c.display_label AS condition, c.condition_kind AS kind, p.veda AS veda,
               count(DISTINCT p) AS mantras
        ORDER BY condition, mantras DESC
        """,
        caveat=(
            "CORRECTED IN V3.2: this query asked an affliction question and answered it "
            "with demons. Of the 718 MENTIONS_ENTITY edges reaching a Condition, 314 "
            "reached a THREAT and 88 a PATHOGEN_OR_CAUSE, so rakshas, sorcery, curses, "
            "worms and poison were all ranking as diseases. The 8 THREAT and 2 "
            "PATHOGEN_OR_CAUSE conditions are now excluded here by `condition_kind` and "
            "remain reachable through passages_protecting_against and "
            "condition_neighbourhood, both of which stay deliberately broad. "
            "Naming an affliction is weaker than treating it. CORRECTED IN V3.1: this "
            "caveat read 'There is deliberately no separate fever entity: takman- "
            "forms sit in YAKSMA-DISEASE'. That is no longer true -- "
            "VG:CONCEPT:TAKMAN-FEVER exists and carries 33 mentions -- so the caveat "
            "was denying the existence of an entity the same database returns. The "
            "reason it originally gave still matters, and is now a live hazard rather "
            "than a settled policy: the takman- paradigm is split across two "
            "entities, so a query filtering on either alone undercounts fever. Read "
            "TAKMAN-FEVER and YAKSMA-DISEASE together, and treat the split as "
            "unmeasured until someone reconciles the paradigm."
        ),
        serves=(12, 15, 47),
    ),
    DomainQuery(
        name="condition_neighbourhood",
        question="What surrounds one affliction in the Atharvaveda: plants, objects, others?",
        cypher="""
        MATCH (p:Passage {veda: 'AV'})-[:MENTIONS_ENTITY]->(c:Condition {entity_key: $condition})
        OPTIONAL MATCH (p)-[:MENTIONS_ENTITY]->(pl:Plant)
        OPTIONAL MATCH (p)-[:MENTIONS_ENTITY]->(ob:Object)
        OPTIONAL MATCH (p)-[:MENTIONS_ENTITY]->(other:Condition)
          WHERE other.entity_key <> $condition
        RETURN p.canonical_citation AS passage,
               collect(DISTINCT pl.display_label) AS plants,
               collect(DISTINCT ob.display_label) AS objects,
               collect(DISTINCT other.display_label) AS other_conditions,
               collect(DISTINCT other.condition_kind) AS other_condition_kinds
        ORDER BY passage LIMIT 25
        """,
        parameters={"condition": "VG:CONCEPT:VISA-POISON"},
        caveat=(
            "Co-occurrence within a mantra; no causal or prescriptive claim. Keyed on a "
            "Condition rather than on a healing HumanConcern because bheṣaja is not typed "
            "as a :HumanConcern -- it is a :Concept in the CORPOREAL and RITUAL domains, "
            "which is a curation choice and not an absence. It IS curated and IS reachable: "
            "see `stated_remedy_by_veda`, which reaches VG:CONCEPT:BHESAJA-HEALING through "
            "7 registered Sanskrit aliases with per-edge verse evidence. An earlier version "
            "of this caveat said bheṣaja 'was not curated', which was false."
        ),
        serves=(12, 15, 47),
    ),
    DomainQuery(
        name="stated_remedy_by_veda",
        question="Where does the corpus name a remedy, rather than only an affliction?",
        cypher="""
        MATCH (n:Concept {entity_key: 'VG:CONCEPT:BHESAJA-HEALING'})
        CALL (n) {
            MATCH (m:Mantra)-[r:MENTIONS_ENTITY]->(n)
            RETURN m.veda AS veda, count(DISTINCT m) AS mantras,
                   count(r) AS edges,
                   collect(DISTINCT r.evidence_basis) AS evidence_bases
        }
        RETURN n.entity_key AS entity_key, n.display_label AS remedy,
               n.domain AS domain, size(n.aliases_sa) AS registered_sanskrit_aliases,
               veda, mantras, edges, evidence_bases
        ORDER BY mantras DESC
        """,
        caveat=(
            "GAP-ENTITY_COVERAGE-003. This question was published for two rounds as "
            "unanswerable -- 'the registry has no healing entity, bheṣaja was never "
            "curated' -- and the claim was false: VG:CONCEPT:BHESAJA-HEALING has been in "
            "the registry with 7 registered Sanskrit aliases (bheṣajam, bheṣajaṃ, "
            "bheṣajā, bheṣajāni, bheṣajīḥ, bhiṣajā, bhiṣak) and every mention edge carries "
            "a verbatim locator and quote. A remedy is a STATED remedy, not an effective "
            "one: the edge means the verse names bheṣaja, not that the verse prescribes a "
            "treatment that worked. No separate :Remedy or :Bhesaja label exists and none "
            "should -- the concept is the authoritative representation and a second label "
            "would be two answers to one question."
        ),
        serves=(12, 15, 47),
    ),
    DomainQuery(
        name="social_rites",
        question="Which passages concern marriage, childbirth and funerary rites?",
        cypher="""
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(s:SocialRite)
        RETURN s.display_label AS rite, p.veda AS veda, count(DISTINCT p) AS mantras,
               collect(p.canonical_citation)[0..5] AS examples
        ORDER BY rite, mantras DESC
        """,
        caveat=(
            "AV 14 redacts RV 10.85, so marriage vocabulary is not exclusively "
            "Atharvavedic and the RV share is real rather than noise."
        ),
        serves=(13, 14),
    ),
    DomainQuery(
        name="medicinal_plants",
        question="Which plants are named, and alongside which afflictions?",
        # Split rather than filtered. The question says afflictions, but a plant co-named
        # with a demon is a real finding for the counter-witchcraft herbs -- apamarga and
        # darbha are named against sorcery, not against a cough -- so dropping the threat
        # column would answer a narrower question than the corpus supports. Two columns
        # keep the affliction reading exact and the apotropaic reading visible.
        cypher="""
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(pl:Plant)
        OPTIONAL MATCH (p)-[:MENTIONS_ENTITY]->(c:Condition)
        RETURN pl.display_label AS plant, p.veda AS veda, count(DISTINCT p) AS mantras,
               collect(DISTINCT CASE WHEN c.condition_kind = 'AFFLICTION'
                                     THEN c.display_label END) AS co_afflictions,
               collect(DISTINCT CASE WHEN c.condition_kind IN ['THREAT',
                                                               'PATHOGEN_OR_CAUSE']
                                     THEN c.display_label END) AS co_threats
        ORDER BY mantras DESC
        """,
        caveat=(
            "Co-occurrence, not pharmacology. The condition column was split in V3.2: it "
            "previously returned demons and sorcery under a heading that said afflictions."
        ),
        serves=(47,),
    ),
    DomainQuery(
        name="passages_protecting_against",
        question="What does the corpus ask to be protected from?",
        cypher="""
        MATCH (p:Passage)-[r:PROTECTS_FROM]->(threat)
        RETURN threat.display_label AS threat, threat.display_type AS kind,
               threat.condition_kind AS condition_kind,
               p.veda AS veda, count(DISTINCT p) AS passages,
               collect(DISTINCT r.quality_tier) AS tiers
        ORDER BY passages DESC, threat LIMIT 30
        """,
        caveat=(
            "A top-30 of 659 edges. Every one is TIER_D: the predicate is this project's "
            "reading of a passage that names a threat, and naming a demon is not the same "
            "as apotropaic intent. `derived_from_mention` on each edge points back at the "
            "lexical mention it was inferred from, so the inference is auditable rather "
            "than asserted. Compare with ADDRESSES_CONCERN, which carries TIER_B for the "
            "same class of question -- see concerns_addressed_versus_protected_from."
        ),
        serves=(15, 16, 32, 47),
    ),
    DomainQuery(
        name="concerns_addressed_versus_protected_from",
        question="Which human concerns does the corpus address, and on what strength of evidence?",
        # The three predicates are returned side by side rather than unioned into one
        # count, because they do not carry the same tier: ADDRESSES_CONCERN is TIER_B and
        # PROTECTS_FROM / TREATS are TIER_D. Summing them would publish an interpretive
        # reading at the strength of the deterministic one.
        cypher="""
        MATCH (p:Passage)-[r:ADDRESSES_CONCERN|PROTECTS_FROM|TREATS]->(target)
        WITH target, type(r) AS predicate, r.quality_tier AS tier, p.veda AS veda,
             count(DISTINCT p) AS passages
        RETURN target.display_label AS target, target.display_type AS kind,
               target.condition_kind AS condition_kind,
               predicate, tier, collect([veda, passages]) AS by_veda,
               sum(passages) AS passages
        ORDER BY passages DESC, target, predicate LIMIT 30
        """,
        caveat=(
            "A top-30 of 1,145 edges over three predicates whose tiers differ, which is "
            "why `tier` is a returned column and not a filter. Several targets appear "
            "twice under two predicates -- sapatna is both addressed (TIER_B, 101) and "
            "protected from (TIER_D, 101) -- and that duplication is informative, not a "
            "bug: it is the same mention read two ways. Do not sum the rows."
        ),
        serves=(13, 14, 15, 16, 29, 47, 48),
    ),
    DomainQuery(
        name="av_deity_ascription_descriptors",
        question="How does the Atharvaveda label a hymn's deity, when it is not a deity name?",
        cypher="""
        MATCH (p:Passage)-[a:HAS_DEVATA_ASCRIPTION]->(asc:DevataAscription)
        RETURN asc.display_label AS ascription, asc.label_iast AS iast,
               count(DISTINCT p) AS passages, collect(DISTINCT p.veda) AS vedas,
               collect(DISTINCT a.attribution_precision) AS precision,
               asc.layer_veda_scope AS layer_veda_scope
        ORDER BY passages DESC, ascription LIMIT 25
        """,
        caveat=(
            "A top-25 of 324 descriptors over 5,385 edges, all Atharvavedic. These are "
            "deliberately NOT Devata nodes: agneyam is the adjective 'belonging to Agni', "
            "and minting it as a deity would invent an entity the tradition does not have "
            "and then let it be counted alongside Agni. Nor are they translatable one-to-"
            "one into deities -- mantroktadevatyam means 'whose deity is stated in the "
            "mantra', which names no deity at all. Every edge is CONTAINER_INHERITED: the "
            "ascription is a sukta label projected onto each of its mantras, so `passages` "
            "measures hymn length as much as prominence."
        ),
        serves=(29, 41, 42),
    ),
    # ------------------------------------------------------------------ ritual
    DomainQuery(
        name="ritual_profile",
        question="What does a ritual involve: deities, offerings, objects, purpose?",
        cypher="""
        MATCH (r:Ritual)
        OPTIONAL MATCH (p:Passage)-[:MENTIONS_ENTITY]->(r)
        OPTIONAL MATCH (r)-[:USES_OFFERING]->(off:Offering)
        OPTIONAL MATCH (r)-[:USES_SUBSTANCE]->(sub:Substance)
        OPTIONAL MATCH (r)-[:USES_OBJECT]->(ob:Object)
        OPTIONAL MATCH (r)-[:INVOKES_DEVATA]->(dv:Devata)
        RETURN r.display_label AS ritual, count(DISTINCT p) AS mantras,
               'RANK WITHIN 8 NAMED RITUALS: the Ritual class holds 8 nodes against a '
               + 'corpus naming considerably more, so this is not a corpus-wide ranking'
                 AS inventory_coverage,
               collect(DISTINCT off.display_label) AS offerings,
               collect(DISTINCT sub.display_label) AS substances,
               collect(DISTINCT ob.display_label) AS objects,
               collect(DISTINCT dv.display_label) AS deities
        ORDER BY mantras DESC
        """,
        caveat=(
            "Ritual structure is curated and thin by design: elaborate procedure is "
            "largely post-Samhita and was not imported into Samhita passages. The "
            "`inventory_coverage` column states the binding limit in every row rather "
            "than only here: Ritual holds 8 nodes, so a rank in this table is a rank "
            "within 8 and not a statement about the corpus's rites. Offering was "
            "expanded from 2 to 8 nodes in V3.1 and is still marked incomplete; "
            "HumanConcern at 7 nodes is now the binding dimension for the four-way "
            "ritual join."
        ),
        serves=(5, 32, 39, 56),
    ),
    DomainQuery(
        name="agni_and_indra_together",
        question="Which passages address both Agni and Indra?",
        cypher="""
        MATCH (dual:Devata {entity_key: $dual})
        OPTIONAL MATCH (p:Passage)-[:HAS_DEVATA]->(dual)
        RETURN 'attributed to the dual deity indragni' AS route, 'RV' AS veda,
               count(DISTINCT p) AS mantras, 'HAS_DEVATA (Anukramani ascription)' AS layer,
               collect(p.canonical_citation)[0..6] AS examples
        UNION ALL
        MATCH (ag:Devata {entity_key: $a}), (ind:Devata {entity_key: $b})
        OPTIONAL MATCH (p:Passage)-[:HAS_DEVATA]->(ag)
        WHERE (p)-[:HAS_DEVATA]->(ind)
        RETURN 'both singly ascribed in one mantra' AS route, 'RV' AS veda,
               count(DISTINCT p) AS mantras, 'HAS_DEVATA (Anukramani ascription)' AS layer,
               collect(p.canonical_citation)[0..6] AS examples
        UNION ALL
        MATCH (p:Passage)-[:MENTIONS_DEVATA]->(:Devata {entity_key: $a})
        MATCH (p)-[:MENTIONS_DEVATA]->(:Devata {entity_key: $b})
        RETURN 'both NAMED in the same verse' AS route, p.veda AS veda,
               count(DISTINCT p) AS mantras, 'MENTIONS_DEVATA (textual mention)' AS layer,
               collect(p.canonical_citation)[0..6] AS examples
        ORDER BY route, mantras DESC
        """,
        parameters={"a": AGNI, "b": INDRA, "dual": "VG:DEVATA:INDRAGNI"},
        caveat=(
            "Two different questions, and the rows keep them apart because conflating "
            "them is how this query previously misled. ASCRIBED: the Anukramani names "
            f"one addressee per mantra, so only {figures.MULTI_DEVATA_MANTRAS} of "
            f"{figures.CORPUS_MANTRAS['RV']:,} Rigvedic mantras carry more than one "
            "ascribed deity, and where the tradition means the pair it uses the dual "
            "deity VG:DEVATA:INDRAGNI instead. That near-zero is a property of the "
            "ascription apparatus, NOT of the text. NAMED: the four-Veda mention layer "
            "shows Agni and Indra named in the same verse in "
            f"{sum(figures.AGNI_INDRA_CO_MENTION_BY_VEDA.values())} passages "
            f"({figures.veda_breakdown(figures.AGNI_INDRA_CO_MENTION_BY_VEDA)}). "
            "This caveat previously read 'the second route returns zero, and that is the "
            "finding rather than a gap', which the same database disproves; it was "
            "written against HAS_DEVATA and never revised when the mention layer landed. "
            "It also could not be checked by running the query, because a UNION "
            "branch whose MATCH finds nothing returns NO ROW rather than a zero: "
            "the ascribed-pair route was invisible, not visibly empty. Both "
            "ascription routes now use OPTIONAL MATCH so a structural zero is "
            "shown as a zero. "
            "The mention route is unfiltered on referent_certainty, so the impersonal "
            "readings of agni are included. " + _SCOPE_CAVEAT
        ),
        serves=(5, 33),
    ),
    DomainQuery(
        name="ritual_roles",
        question="Which priestly offices does the corpus name?",
        cypher="""
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(rr:RitualRole)
        RETURN rr.display_label AS role, p.veda AS veda, count(DISTINCT p) AS mantras,
               rr.alias_purity AS alias_purity,
               rr.mention_edges_own_alias AS edges_own_alias,
               rr.mention_edges_foreign_alias AS edges_foreign_alias
        ORDER BY mantras DESC, role
        """,
        caveat=(
            "Lexical mentions only, and the alias columns are not decoration. Until V3.1 "
            "hotr carried no RitualRole label at all despite 321 mentions, so this table "
            "omitted the principal officiant of the Rigveda -- a typed-label query "
            "missing the most important member of the class it enumerates, which is one "
            "of the three canonical misleading shapes in the frozen benchmark. It is now "
            "present and heads the table. Its alias list was ALSO wrong in the other "
            "direction and that has been corrected: of the original 321 edges, 14 were "
            "adhvaryu forms and 11 were rtvij-, which names any officiant rather than an "
            "office. The adhvaryu forms moved to their own node and the generic ones were "
            "withdrawn without minting a catch-all office, which would have re-inflated "
            "the very census this fixes. Measured alias purity is now 1.0 on 300 edges, "
            "and it is published per role rather than assumed, so a role whose purity is "
            "below 1.0 can be read as such: prefer `edges_own_alias` to `mantras` "
            "whenever the office itself matters. Roles other than hotr carry no purity "
            "figure yet, and a null there means unmeasured, not clean."
        ),
        serves=(32, 39),
    ),
    DomainQuery(
        name="substances_offered_to_deities",
        question="Which substances co-occur with which deities?",
        cypher="""
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(s:Substance)
        MATCH (p)-[:HAS_DEVATA]->(dv:Devata)
        RETURN dv.display_label AS deity, s.display_label AS substance,
               count(DISTINCT p) AS mantras
        ORDER BY mantras DESC LIMIT 30
        """,
        caveat=(
            _SCOPE_CAVEAT + " " + _INHERIT_CAVEAT + " Co-occurrence, not oblation: this "
            "does not establish that the substance was offered to that deity."
        ),
        serves=(4, 31),
    ),
    DomainQuery(
        name="rituals_described_in_passages",
        question="Which passages describe each rite, and in which Vedas?",
        # DESCRIBED_IN is the curated Ritual -> Passage link, which is the opposite
        # direction from MENTIONS_ENTITY: it says "this passage describes this rite",
        # not "this passage names this word". collect(DISTINCT d.quality_tier) rather
        # than d.quality_tier, because d varies per row and a bare relationship property
        # beside an aggregate is not a legal grouping key.
        cypher="""
        MATCH (r:Ritual)-[d:DESCRIBED_IN]->(p:Passage)
        RETURN r.display_label AS ritual, count(DISTINCT p) AS passages,
               count(DISTINCT p.veda) AS vedas, collect(DISTINCT p.veda) AS veda_list,
               collect(DISTINCT d.quality_tier) AS tiers,
               collect(p.canonical_citation)[0..6] AS examples
        ORDER BY passages DESC, ritual
        """,
        caveat=(
            "Complete: all 8 rites and all 71 edges. Every edge is TIER_D -- the project's "
            "judgement that a passage describes a rite, not a statement the passage makes "
            "about itself -- and the volume is the honest measure of how much procedure "
            "the Samhitas carry: 71 passages out of 22,537. `examples` is capped at 6 per "
            "row and `passages` gives the true total beside it. The Yajurvedic majority in "
            "several rows is real: the YV is the liturgical collection."
        ),
        serves=(5, 32, 39),
    ),
    DomainQuery(
        name="ritual_step_sequence",
        question="Which rites have a recorded sequence of steps, and on what authority?",
        # [l IN labels(step) WHERE l IN $step_labels] rather than labels(step)[0]:
        # a step node is Concept:DomainEntity:Action and labels() has no guaranteed
        # order, so the [0] form would return 'Concept' or 'Action' unpredictably.
        cypher="""
        MATCH (r:Ritual)-[h:HAS_STEP]->(step)
        RETURN r.display_label AS ritual, h.step_order AS step_order,
               step.display_label AS step, h.order_basis AS order_basis,
               [l IN labels(step) WHERE l IN $step_labels] AS step_kind
        ORDER BY ritual, step_order
        """,
        parameters={"step_labels": ["Action", "Ritual", "Offering"]},
        caveat=(
            "Complete, and the size of the result is the finding: 3 steps, on 1 of the 8 "
            "rites. order_basis = 'SOURCE_STATED_ORDINAL' because the soma pressings are "
            "named morning, midday and third in the text itself; no other rite in this "
            "corpus states an order, and none was invented for it. Elaborate procedure is "
            "Brahmana and Sutra material, so a query about ritual dependency structure is "
            "answerable here only in this one instance, and question 39 is otherwise not "
            "answerable from the Samhitas."
        ),
        serves=(32, 39),
    ),
    DomainQuery(
        name="ritual_officiants_and_purposes",
        question="Who performs each rite, and what is it performed for?",
        cypher="""
        MATCH (r:Ritual)
        OPTIONAL MATCH (r)-[:PERFORMED_BY]->(office:RitualRole)
        OPTIONAL MATCH (r)-[:PERFORMED_FOR]->(purpose:DomainEntity)
        OPTIONAL MATCH (r)-[:DESCRIBED_IN]->(p:Passage)
        RETURN r.display_label AS ritual,
               collect(DISTINCT office.display_label) AS officiants,
               collect(DISTINCT purpose.display_label) AS purposes,
               count(DISTINCT p) AS passages
        ORDER BY size(officiants) DESC, ritual
        """,
        caveat=(
            "Complete over all 8 rites; empty lists are real and are why OPTIONAL MATCH is "
            "used. count(DISTINCT p) and not count(*): three OPTIONAL MATCHes are in scope "
            "and the yajna row alone would multiply 9 officiants by 4 purposes by 8 "
            "passages, so count(*) would report 288 passages for 8. All 25 apparatus edges "
            "are TIER_D curation, and 'purpose' is what the rite is said to be for by the "
            "curator, not a purpose clause quoted from a passage."
        ),
        serves=(5, 32, 39),
    ),
    DomainQuery(
        name="passages_used_for_a_rite",
        question="Which passages are used for marriage, childbirth, funerals or assembly?",
        cypher="""
        MATCH (p:Passage)-[u:USED_FOR_RITE]->(rite:SocialRite)
        WHERE u.attribution_precision IN $precision
        RETURN rite.display_label AS rite, p.veda AS veda, count(DISTINCT p) AS passages,
               collect(DISTINCT u.quality_tier) AS tiers,
               collect(DISTINCT u.attribution_precision) AS precision,
               rite.strict_recall_against_locus AS strict_recall_against_locus,
               rite.locus_book AS locus_book,
               rite.locus_tagged_passages AS locus_tagged_passages,
               rite.locus_book_passages AS locus_book_passages,
               collect(p.canonical_citation)[0..5] AS examples
        ORDER BY rite, passages DESC
        """,
        parameters={"precision": ["PER_PASSAGE"]},
        caveat=(
            "DEFAULTS TO STRICT: 110 source-stated PER_PASSAGE edges over 6 rites. The "
            "419 CONTAINER_INHERITED edges added in V3.1 are the locus BOOK's claim "
            "projected onto its verses, not a statement about each verse, and they are "
            "reachable only by passing "
            "precision=['PER_PASSAGE','CONTAINER_INHERITED'] explicitly. "
            "RECALL IS A COLUMN, NOT A CAVEAT, because the frozen criterion requires the "
            "figure and the reader who runs the obvious query never sees a caveat. It is "
            "LOW and is not softened: marriage tags 14 of the 141 passages of AV Kanda 14 "
            "(9.93%), house-building 19 of 311 in AV Kanda 9 (6.11%). Enrichment against "
            "the corpus baseline is nonetheless 58x and 35x, so the edges that do exist "
            "are strongly non-random -- the layer is precise and thin, not noisy. "
            "The locus book was deliberately NOT tagged wholesale: that would make recall "
            "100% by construction and would assert of 127 Kanda 14 verses what no source "
            "in this repository says. For the same reason no funerary locus is declared -- "
            "of 9 Atharvavedic funerary tags Kanda 18 holds only one, so seeding from the "
            "traditional identification would be external knowledge under cover of a "
            "measurement. "
            "TIER_B, so stronger than PROTECTS_FROM and TREATS, but still a derived "
            "reading of a lexical mention rather than a rubric. The RV rows are not "
            "noise: AV 14 redacts RV 10.85. `examples` is capped at 5 with the true total "
            "in `passages`."
        ),
        serves=(13, 14, 32, 60),
    ),
    # ------------------------------------------------------------- cross-Veda
    DomainQuery(
        name="sv_reuse_of_rv",
        question="Which Rigvedic verses are reused in the Samaveda, and how closely?",
        cypher="""
        MATCH (sv:Passage)-[r:REUSES_TEXT_FROM]->(rv:Passage)
        WHERE sv.veda = 'SV' AND rv.veda = 'RV'
        RETURN sv.canonical_citation AS samaveda, rv.canonical_citation AS rigveda,
               r.match_level AS match_level, r.quality_tier AS tier
        ORDER BY samaveda LIMIT 30
        """,
        caveat=(
            "Cross-script comparison bottoms out at SANDHI_INSENSITIVE, the weakest "
            "surface, because a Devanagari SV text and a Latin RV text share no code "
            "points. A blank match_level means the edge predates level recording."
        ),
        # The corpus filter is not decoration, and it was added after the fact. This query
        # is named for one Veda pair, asks its question about one Veda pair and returns two
        # columns called `samaveda` and `rigveda` -- but it matched any passage to any
        # passage, which was harmless only while RV->SV was the sole direction recorded.
        # It stopped being the sole one: REUSES_TEXT_FROM now also carries 311 AV->RV
        # edges, `ORDER BY samaveda` sorts `AVS ...` ahead of every Samavedic citation, and
        # all thirty rows this served were Atharvavedic under a column headed "samaveda".
        # A query whose result contradicts its own field names is worse than a missing one.
        serves=(6, 7, 50),
    ),
    DomainQuery(
        name="cross_veda_formulas",
        question="Which formulas occur across more than one Veda?",
        cypher="""
        MATCH (f:Formula) WHERE f.cross_veda
        RETURN f.display_form AS formula, f.vedas AS vedas,
               f.occurrence_count AS occurrences, f.word_count AS words
        ORDER BY occurrences DESC LIMIT 30
        """,
        caveat=(
            "Formula identity is a normalised-string match, not a tradition of reuse. "
            + figures.formula_nesting_policy()
        ),
        serves=(8, 27),
    ),
    DomainQuery(
        name="formula_family_diffusion",
        question="How does one formula spread across the corpus?",
        cypher="""
        MATCH (p:Passage)-[:USES_FORMULA]->(f:Formula {formula_id: $formula})
        RETURN f.display_form AS formula, p.veda AS veda, count(DISTINCT p) AS mantras,
               collect(p.canonical_citation)[0..6] AS examples
        ORDER BY mantras DESC
        """,
        parameters={"formula": "VG:ENRICH:FORMULA:01ee076bd8b5c608c52c6cb6f245f7f5"},
        caveat=(
            "Default is the widest-spread formula in the corpus, pata svastibhih sada "
            "nah, occurring 93 times across all four Vedas. Formula identity is a "
            "normalised-string match, so a family is a shared wording rather than a "
            "demonstrated line of transmission. " + figures.formula_nesting_policy()
        ),
        serves=(8, 27, 50),
    ),
    DomainQuery(
        name="formula_family_span_census",
        question="How many formula families reach one Veda, and how many reach all four?",
        cypher="""
        MATCH (ff:FormulaFamily)
        RETURN ff.veda_span AS vedas_reached, ff.cross_veda AS cross_veda,
               count(*) AS families, sum(ff.member_count) AS memberships,
               sum(ff.occurrence_count) AS occurrences
        ORDER BY vedas_reached DESC
        """,
        caveat=(
            "Complete over all 720 families. One MATCH pattern is in scope, so count(*) "
            "here is a count of families and is the intended figure. A family is a "
            "representative wording plus everything that contains or closely resembles it, "
            "so `vedas_reached` is a property of shared diction and not of transmission: "
            "105 families are single-Veda, which is the baseline the 615 cross-Veda ones "
            "should be read against rather than a separate finding."
        ),
        serves=(8, 27),
    ),
    DomainQuery(
        name="formula_families_reaching_all_four_vedas",
        question="Which formula families spread most widely across all four Vedas?",
        cypher="""
        MATCH (ff:FormulaFamily)
        WHERE ff.veda_span = 4
        RETURN ff.representative_display_form AS representative,
               ff.member_count AS members, ff.core_count AS core,
               ff.expansion_count AS expansions, ff.variant_count AS variants,
               ff.occurrence_count AS occurrences,
               ff.veda_counts AS occurrences_per_veda, ff.quality_tier AS tier
        ORDER BY members DESC, occurrences DESC, representative LIMIT 25
        """,
        caveat=(
            "A top-25 of the 107 families that reach all four Vedas; formula_family_span_"
            "census gives the full distribution. `occurrences_per_veda` is a JSON string, "
            "not a list, and reading it will usually show a Rigvedic majority -- which is "
            "partly that the RV is the largest corpus and partly that the SV and much of "
            "the YV are drawn from it, so a four-Veda family is often one Rigvedic phrase "
            "carried forward rather than four independent attestations."
        ),
        serves=(8, 27, 50),
    ),
    DomainQuery(
        name="formula_family_membership_roles",
        question="How is a formula family held together: containment, or resemblance?",
        cypher="""
        MATCH (:Formula)-[m:MEMBER_OF_FAMILY]->(ff:FormulaFamily)
        RETURN m.role AS role, m.quality_tier AS tier, m.derivation AS derivation,
               m.contains_representative AS contains_representative,
               m.containment_is_transitive AS only_transitive,
               count(*) AS memberships, count(DISTINCT ff) AS families
        ORDER BY memberships DESC
        """,
        caveat=(
            "Complete over all 2,037 memberships. The two boolean columns are the whole "
            "point: 1,796 memberships directly contain the family's representative wording "
            "and 240 reach it only transitively, through another member. A transitive "
            "membership is a weaker claim -- the member and the representative may share no "
            "words at all -- and the tier does not distinguish them, so a query that wants "
            "only direct containment must filter contains_representative itself."
        ),
        serves=(7, 27, 29),
    ),
    DomainQuery(
        name="formula_family_similarity_derived",
        question="Which family memberships rest on resemblance rather than shared wording?",
        cypher="""
        MATCH (f:Formula)-[m:MEMBER_OF_FAMILY]->(ff:FormulaFamily)
        WHERE m.quality_tier = 'TIER_D'
        RETURN ff.representative_display_form AS representative,
               f.display_form AS member, m.role AS role, m.similarity AS similarity,
               m.derivation AS derivation,
               m.has_containment_support AS containment_support
        ORDER BY similarity DESC, member
        """,
        caveat=(
            "Complete, and small on purpose: 5 of 2,037 memberships. Four are VARIANT rows "
            "derived by string similarity (0.76 to 0.86) and one is an EXPANSION with "
            "has_containment_support = false. These are the only rows in the family layer "
            "that are not a containment fact, so they are the only ones where the family is "
            "an inference; the rest of the layer is TIER_B because containment is checkable. "
            "'nu dyavaprthivi' against 'dyavaprthivi a' shows the failure mode -- the "
            "resemblance is a sandhi boundary, not a variant reading."
        ),
        serves=(7, 27, 29),
    ),
    DomainQuery(
        name="formula_family_profile",
        question="What does one formula family contain, and where does each member occur?",
        cypher="""
        MATCH (ff:FormulaFamily {family_id: $family})
        MATCH (f:Formula)-[m:MEMBER_OF_FAMILY]->(ff)
        OPTIONAL MATCH (p:Passage)-[:USES_FORMULA]->(f)
        RETURN ff.representative_display_form AS representative,
               f.display_form AS member, m.role AS role, m.quality_tier AS tier,
               m.contains_representative AS contains_representative,
               count(DISTINCT p) AS passages, collect(DISTINCT p.veda) AS vedas
        ORDER BY passages DESC, member
        """,
        parameters={"family": "VG:ENRICH:FORMULA-FAMILY:709faeaecdc5a79716fa565ce0a051f0"},
        caveat=(
            "Complete for the named family. The default is visva bhuvana, the largest "
            "four-Veda family: 14 members, 1 core and 13 expansions. count(DISTINCT p) and "
            "not count(*): the membership pattern and the USES_FORMULA pattern are both in "
            "scope, and a formula used by many passages would otherwise be multiplied by "
            "its membership row. A member's `vedas` list is where that wording occurs, not "
            "where the family does -- the family's own span is on the FormulaFamily node."
        ),
        serves=(8, 27, 50),
    ),
    DomainQuery(
        name="entity_vocabulary_overlap_candidates",
        question=(
            "Which cross-Veda passages share entity vocabulary, rather than ideas, "
            "without sharing text?"
        ),
        cypher="""
        MATCH (a:Passage)-[r:SHARES_ENTITY_VOCABULARY_WITH]->(b:Passage)
        RETURN 'ENTITY_VOCABULARY_OVERLAP' AS measure,
               a.canonical_citation AS passage_a, b.canonical_citation AS passage_b,
               r.veda_pair AS veda_pair, r.shared_entities AS shared_entities,
               r.shared_entity_keys AS shared_entity_keys,
               r.distinctiveness AS distinctiveness,
               r.rarest_shared_df AS rarest_shared_passages,
               'NOT_BUILT' AS semantic_resemblance_population,
               'INSUFFICIENT_EVIDENCE for conceptual similarity: no non-lexical '
               + 'resemblance measure exists in this graph' AS conceptual_similarity
        ORDER BY distinctiveness DESC, shared_entities DESC LIMIT 25
        """,
        caveat=(
            "THIS QUERY DOES NOT ANSWER THE CONCEPTUAL-SIMILARITY QUESTION, and the "
            "`conceptual_similarity` column says so in every row rather than leaving it "
            "to this caveat. What it measures is entity-vocabulary overlap: both passages "
            "mention the same registry entities. No non-lexical resemblance measure "
            "exists anywhere in this graph -- no embedding, no vector index, no asserted "
            "resemblance -- so `semantic_resemblance_population` is NOT_BUILT, and that "
            "structural zero is typed rather than returned as a 0 a reader would read as "
            "'no such resemblance in the corpus'. "
            "It was renamed from `conceptually_similar_not_reused` in V3.1. Under the old "
            "name it returned 25 confident-looking cross-Veda pairs ranked on a raw "
            "shared-entity count, and the V3.1 benchmark diagnosis graded Q22 and Q49 "
            "MISLEADING for it: both frozen criteria exclude lexical overlap in terms, and "
            "a caveat is not sufficient because the reader who runs the obvious query "
            "never sees the caveat. "
            "RANK ON `distinctiveness`, NOT ON `shared_entities`. Three shared entities "
            "are weak evidence when they are heaven, sacrifice and soma, which between "
            "them touch a large share of the corpus, and strong evidence when one is "
            "altar (vedi), which appears in 17 passages. `distinctiveness` is the "
            "inverse-document-frequency sum over the shared entities and "
            "`rarest_shared_passages` is the document frequency of the rarest one. "
            "The layer is materialised, which is also why it is fast: computed online it "
            "was an exact all-pairs self-join over a hub-skewed degree distribution "
            "(maximum 1,206) taking 5.3 s, and it exceeded the 1.4 GiB transaction memory "
            "limit and died outright as soon as the shared entities were collected. "
            "Pairs already joined by EXACT_PARALLEL_OF, NEAR_PARALLEL_OF or "
            "REUSES_TEXT_FROM are excluded, because the questions ask for resemblance "
            "WITHOUT shared text."
        ),
        serves=(22, 49, 81),
    ),
    DomainQuery(
        name="confidence_is_a_pipeline_constant",
        question=(
            "Where is the graph uncertain, and is the confidence field a calibrated measurement?"
        ),
        cypher="""
        // Reads all THREE strength fields, not just `confidence`. GAP-QUALITY-003 withdrew
        // `confidence` from the seven source-explicit predicates, and a `confidence IS NOT
        // NULL` filter therefore reported zero SINGLE_CONSTANT rows while 51,364 edges
        // still carried exactly 1.0 under another name -- making the one query whose job is
        // to disclose the constants blind to the largest block of them. Agent B's C01.
        MATCH ()-[r]->()
        WHERE r.confidence IS NOT NULL
           OR r.source_explicit_tier_marker IS NOT NULL
           OR r.uncalibrated_pipeline_score IS NOT NULL
        WITH type(r) AS predicate,
             coalesce(r.confidence, r.source_explicit_tier_marker,
                      r.uncalibrated_pipeline_score) AS value,
             CASE WHEN r.confidence IS NOT NULL THEN 'confidence'
                  WHEN r.source_explicit_tier_marker IS NOT NULL
                       THEN 'source_explicit_tier_marker'
                  ELSE 'uncalibrated_pipeline_score' END AS field,
             r.calibration_status AS calibration_status,
             count(*) AS edges
        WITH predicate, field, calibration_status,
             collect({value: value, edges: edges}) AS spread,
             sum(edges) AS predicate_total
        WITH predicate, field, calibration_status, predicate_total, spread,
             reduce(top = 0, s IN spread | CASE WHEN s.edges > top THEN s.edges ELSE top END)
               AS modal_edges
        RETURN predicate, field, predicate_total, size(spread) AS distinct_values,
               modal_edges,
               round(1000.0 * modal_edges / predicate_total) / 10 AS modal_share_pct,
               CASE WHEN size(spread) = 1 THEN 'SINGLE_CONSTANT'
                    WHEN modal_edges * 2 > predicate_total THEN 'MAJORITY_ONE_CONSTANT'
                    ELSE 'DISTRIBUTED' END AS guard_verdict,
               CASE WHEN field = 'source_explicit_tier_marker'
                      THEN 'AN EVIDENCE TIER, NOT A PROBABILITY'
                    WHEN field = 'uncalibrated_pipeline_score'
                      THEN 'AN UNCALIBRATED PIPELINE SCORE, NOT A PROBABILITY'
                    ELSE 'PIPELINE_PRIOR, NOT A CALIBRATED CONFIDENCE' END
                 AS what_this_field_is,
               coalesce(calibration_status,
                        'NOT_CALIBRATED_NO_HUMAN_LABELLED_SAMPLE') AS calibration_evidence
        ORDER BY predicate_total DESC
        """,
        caveat=(
            "NO FIELD IN THIS GRAPH IS A CALIBRATED CONFIDENCE, and three different fields "
            "carry the three different things that were all once called one. Measured after "
            "GAP-QUALITY-003: 76,838 edges carry a strength figure, and 75,348 of them -- "
            "98.1% -- sit at exactly one of three values (1.0 on 51,364, 0.85 on 12,781, "
            "0.80 on 11,203). A researcher who filters on 0.8 believes they have raised "
            "precision and has selected a set of pipeline branches. "
            "WHICH FIELD an edge uses is returned per row, because the three are not the "
            "same claim. `source_explicit_tier_marker` (51,364 edges over 7 predicates, all "
            "at 1.0) is an EVIDENCE TIER: the source states the relation, and the figure "
            "carries no per-edge information at all. It was called `confidence` until R5 "
            "renamed it, because a constant stamped on every edge of a predicate offers a "
            "threshold that keeps all of them or none. `uncalibrated_pipeline_score` (4 "
            "edges over 2 predicates) is a pipeline default on a population too small to "
            "vary -- 3 edges and 1 -- which is a sample size and not a tier, which is why "
            "those two did NOT get the tier marker. `confidence` (25,470 edges over 11 "
            "predicates) is the only one where the value genuinely varies edge to edge, and "
            "every one of those edges carries "
            "`calibration_status = NOT_CALIBRATED_NO_HUMAN_LABELLED_SAMPLE`. "
            "`guard_verdict` is the constant-value guard, returned per row rather than "
            "described here: SINGLE_CONSTANT means the value carries no information for "
            "that predicate, MAJORITY_ONE_CONSTANT means one value covers over half of it. "
            "Nine predicates read SINGLE_CONSTANT. "
            "CALIBRATION IS HUMAN-BLOCKED and cannot be produced by a model run. There is "
            "no labelled evaluation set and no reliability diagram anywhere in this graph: "
            "`human_gold_status` is UNANNOTATED on 2,459 SemanticAssertion nodes and null "
            "on the other 32,672, and `review_state` is UNREVIEWED on all 35,131. The "
            "reference set that does exist is an "
            "INDEPENDENT_SOURCE_ADJUDICATED_REFERENCE_SET and is NOT human gold; 0 nodes "
            "in this graph claim to be. "
            "For real per-edge uncertainty use `quality_tier`, `evidence_basis` and "
            "`attribution_precision`, which are derived from what the edge actually rests "
            "on. The remaining `confidence` spelling is NOT renamed further, and the reason "
            "is a boundary rather than a backlog: src/vedagraph/semantic/ontology.py is "
            "inside the semantic hash seal, where the same word means a model's own output "
            "rather than a pipeline constant, so a blanket rename would break the seal and "
            "conflate two quantities."
        ),
        serves=(77,),
    ),
    DomainQuery(
        name="entity_centrality_ranked",
        question="Which entities are most central, and on which layer was that measured?",
        cypher="""
        MATCH (e:DomainEntity)
        WHERE e.centrality_degree IS NOT NULL AND NOT e:Internal
        RETURN e.display_label AS entity, e.display_type AS kind,
               e.centrality_degree AS passages, e.centrality_share AS share_of_mentions,
               e.centrality_measure AS measure, e.centrality_layer AS authoritative_layer,
               e.centrality_bridging AS bridge_centrality
        ORDER BY passages DESC LIMIT 30
        """,
        caveat=(
            "The score is STORED, and that is the point. Nothing in this graph carried a "
            "centrality value before V3.1, so a researcher asking this question wrote a "
            "GDS projection -- and the natural projection over Passage/DomainEntity with "
            "MENTIONS_ENTITY is DIRECTED and BIPARTITE, on which betweenness is 0.0 for "
            "every node. The default thing a competent user does returned a full, "
            "sortable ranking of zeros. A stored score cannot be silently mis-projected. "
            "The layer is DECLARED: MENTIONS_ENTITY is authoritative and ABOUT_CONCEPT is "
            "the rival, because 'which layer' was previously a coin flip that changed the "
            "answer. What the choice costs is measured, not asserted -- Spearman rho "
            "between the two rankings is 0.964 over 91 shared members, and the rival "
            "layer's membership is a strict subset of the authoritative one "
            "(only_in_rival = 0). See concept_layer_rank_correlation. "
            "The measure is DEGREE over passage co-mention: how many passages name the "
            "entity. BRIDGE centrality is NOT reported and the bridge_centrality column "
            "says NOT_BUILT rather than 0, because there is no community structure in "
            "this graph -- no Louvain, no modularity, no stored partition -- so bridging "
            "between communities is not computable here and a zero column would read as "
            "a ranking. Degree centrality also flatters ordinary nouns: heaven, soma and "
            "fire lead partly because their words are common, which is a fact about "
            "vocabulary as much as about prominence."
        ),
        serves=(37, 96),
    ),
    DomainQuery(
        name="concept_layer_rank_correlation",
        question=("Is the entity ranking robust to which concept layer it is computed on?"),
        cypher="""
        MATCH (m:DerivedMetric {metric_name: 'CONCEPT_LAYER_RANK_CORRELATION'})
        RETURN m.subject_key AS authoritative_layer, m.values_json AS correlation,
               m.method AS method, m.grade_basis AS why_this_layer,
               m.interpretation AS interpretation
        """,
        caveat=(
            "This is the robustness clause of the centrality questions, answered with a "
            "number rather than a reassurance. A centrality answer computed on an "
            "undeclared layer is a statement about annotation history, not about the "
            "corpus. rho = 0.964 over 91 shared members means the two layers agree "
            "closely, so the declared choice costs little -- but the 135 entities present "
            "only in the authoritative layer are not evidence of disagreement, they are "
            "membership difference, and the row reports them separately for that reason. "
            "The correlation is computed over the two layers' only shared vocabulary, the "
            "Sanskrit preferred label; entities with no Sanskrit label are dropped rather "
            "than joined on English, because a rho over a bad join would read as the "
            "layers disagreeing when it would really mean the join failed."
        ),
        serves=(96, 37),
    ),
    DomainQuery(
        name="cross_veda_relatedness_method_census",
        question=(
            "Which cross-Veda connections come from literal reuse and which from "
            "semantic resemblance?"
        ),
        cypher="""
        UNWIND [
          {method: 'EXACT_PARALLEL_OF', kind: 'LITERAL_TEXTUAL_REUSE'},
          {method: 'NEAR_PARALLEL_OF', kind: 'LITERAL_TEXTUAL_REUSE'},
          {method: 'REUSES_TEXT_FROM', kind: 'LITERAL_TEXTUAL_REUSE'},
          {method: 'VARIANT_OF', kind: 'LITERAL_TEXTUAL_REUSE'},
          {method: 'SHARES_ENTITY_VOCABULARY_WITH', kind: 'ENTITY_VOCABULARY_OVERLAP'}
        ] AS spec
        CALL (spec) {
            MATCH (a:Passage)-[r]->(b:Passage)
            WHERE type(r) = spec.method AND a.veda <> b.veda
            RETURN count(r) AS edges
        }
        RETURN spec.kind AS resemblance_kind, spec.method AS method, edges,
               'BUILT' AS population_status
        UNION ALL
        RETURN 'SEMANTIC_RESEMBLANCE' AS resemblance_kind,
               'no measure implemented' AS method, 0 AS edges,
               'NOT_BUILT' AS population_status
        """,
        caveat=(
            "A METHOD CENSUS, not a finding about the corpus. The distinction is the "
            "whole point of this query: the literal/semantic partition of cross-Veda "
            "relatedness in this graph is 100/0, and read as a finding that would say "
            "Vedic cross-corpus relatedness is purely textual. It says nothing of the "
            "kind. It says no semantic-resemblance measure was ever built, which is why "
            "the semantic row is typed NOT_BUILT rather than returned as a zero beside "
            "the built populations. PARALLEL_TO is deliberately absent: all 69 of its "
            "edges are within a single Veda, so it does not enter a cross-Veda partition "
            "at all. SHARES_ENTITY_VOCABULARY_WITH is listed under its own kind and NOT "
            "as semantic resemblance -- see entity_vocabulary_overlap_candidates."
        ),
        serves=(81, 22, 49),
    ),
    DomainQuery(
        name="concepts_bridging_vedas",
        question="Which entities appear across the most Vedas?",
        cypher="""
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(e:DomainEntity)
        WITH e, collect(DISTINCT p.veda) AS vedas, count(DISTINCT p) AS mantras
        RETURN e.display_label AS entity, e.display_type AS kind,
               size(vedas) AS veda_count, vedas, mantras
        ORDER BY veda_count DESC, mantras DESC LIMIT 30
        """,
        caveat="Presence, not equivalence of sense across corpora.",
        serves=(21, 34, 36),
    ),
    DomainQuery(
        name="entity_distribution_by_veda",
        question="How is each entity type distributed across the four Vedas?",
        cypher="""
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(e:DomainEntity)
        RETURN e.display_type AS kind, p.veda AS veda, count(*) AS mentions,
               count(DISTINCT e) AS entities
        ORDER BY kind, mentions DESC
        """,
        caveat=(
            "Mention counts scale with corpus size: RV is 10,552 mantras against SV's "
            "1,844, so compare shares rather than totals."
        ),
        serves=(21, 24, 36),
    ),
    # ------------------------------------------------- evidence and provenance
    DomainQuery(
        name="claim_evidence_trace",
        question="What supports an interpretive claim, and what would refute it?",
        cypher="""
        MATCH (c:InterpretiveClaim)
        OPTIONAL MATCH (c)-[:SUPPORTED_BY]->(p:Passage)
        OPTIONAL MATCH (c)-[:SUPPORTED_BY_STATISTIC]->(m:DerivedMetric)
        OPTIONAL MATCH (c)-[:CONTRADICTS]->(other:InterpretiveClaim)
        RETURN c.claim_id AS claim, c.about AS about, c.about_basis AS about_basis,
               c.status AS status, c.confidence AS confidence,
               c.quality_tier AS tier, c.claim_text AS text, c.falsifier AS falsifier,
               collect(DISTINCT p.canonical_citation) AS passages,
               collect(DISTINCT {metric: m.metric_name, values: m.values_json}) AS statistics,
               collect(DISTINCT other.claim_id) AS contradicts
        ORDER BY claim
        """,
        caveat=(
            "Every row here is TIER_D interpretation and permanently CANDIDATE. Two of "
            "these claims contradict each other on purpose: that is the state of the "
            "question, not an error to resolve."
        ),
        serves=(28, 29, 30),
    ),
    DomainQuery(
        name="competing_interpretations",
        question="Where does the graph record disagreement?",
        cypher="""
        MATCH (a:InterpretiveClaim)-[:CONTRADICTS]->(b:InterpretiveClaim)
        WHERE a.claim_id < b.claim_id
        WITH a, b,
             CASE WHEN a.about = b.about AND a.about = 'VEDIC_TEXT'
                  THEN 'RIVAL_READINGS_OF_THE_VEDIC_TEXT'
                  WHEN a.about = b.about THEN 'SAME_CATEGORY_DISAGREEMENT_ABOUT_' + a.about
                  ELSE 'CROSS_CATEGORY__' + a.about + '_VERSUS_' + b.about END
               AS disagreement_kind
        RETURN disagreement_kind,
               a.claim_id AS claim_a, a.about AS about_a, a.status AS status_a,
               a.confidence AS confidence_a,
               b.claim_id AS claim_b, b.about AS about_b, b.status AS status_b,
               b.confidence AS confidence_b
        UNION ALL
        MATCH (c:InterpretiveClaim)
        WITH count(CASE WHEN c.about = 'VEDIC_TEXT' THEN 1 END) AS text_claims,
             count(c) AS all_claims
        WITH text_claims, all_claims,
             size([(x:InterpretiveClaim)-[:CONTRADICTS]->(y:InterpretiveClaim)
                   WHERE x.about = 'VEDIC_TEXT' AND y.about = 'VEDIC_TEXT' | x]) AS rival
        WHERE rival = 0
        RETURN 'INSUFFICIENT_EVIDENCE: this graph records no pair of RIVAL SCHOLARLY '
               + 'READINGS of the Vedic text. It holds ' + toString(all_claims)
               + ' interpretive claims, of which ' + toString(text_claims)
               + ' are about the Vedic text, and no two of those contradict each other.'
               AS disagreement_kind,
               NULL AS claim_a, NULL AS about_a, NULL AS status_a, NULL AS confidence_a,
               NULL AS claim_b, NULL AS about_b, NULL AS status_b, NULL AS confidence_b
        """,
        caveat=(
            "Neither side is marked as winning, and -- the V3.1 correction -- the rows now "
            "say WHAT KIND of disagreement each pair is. This query previously returned "
            "one pair with no such marker, which a researcher would reasonably read as "
            "recorded scholarly disagreement about the Vedas. It is not: all six "
            "InterpretiveClaim nodes carry an `about` discriminator, and the single "
            "CONTRADICTS pair is CROSS-CATEGORY -- SV-IDENTITY-IS-MELODIC is about the "
            "VEDIC_TEXT and SV-PREDOMINANTLY-RV-REUSE is about the DATASET (1,662 of "
            "1,844 mantras measured in this build). A measurement and an interpretation "
            "of a tradition are in dialogue but cannot contradict each other. The final "
            "row states INSUFFICIENT_EVIDENCE explicitly: this graph records NO pair of "
            "rival scholarly readings of the Vedic text, and twelve attributed "
            "commentarial positions would be the acquisition that changes that. Each "
            "claim's `about_basis` records why it was classified as it was, because the "
            "classification is a judgement and a query filters on it."
        ),
        serves=(28, 30, 72),
    ),
    DomainQuery(
        name="textual_versus_interpretive",
        question="Which of the graph's claims are textual and which are interpretation?",
        cypher="""
        MATCH ()-[r]->()
        RETURN r.quality_tier AS tier, r.knowledge_layer AS layer,
               count(*) AS edges, collect(DISTINCT type(r))[0..10] AS example_types
        ORDER BY tier, edges DESC
        """,
        caveat=(
            "A WHOLE-GRAPH CENSUS, and the slowest query in the catalogue for that reason: "
            "`MATCH ()-[r]->()` touches every one of the 265,289 relationships, so its "
            "cost is proportional to the graph and cannot be indexed away. Measured across "
            "repeated runs it varies 222-361 ms with page-cache state, so it sits ON the "
            "300 ms boundary rather than under it -- the V3.1 adversarial re-attack timed "
            "it over in 5 of 7 runs, and the claim that all 90 queries are under 300 ms is "
            "therefore false and is not made. It is well under the 1 s threshold at which "
            "this project requires a batch label. Every other query in the catalogue is "
            "under 240 ms and the median is 4.4 ms. "
            "TIER_C is empty by construction: the 736 model-extracted candidates are all "
            "state=CANDIDATE because there is no human gold to accept them against."
        ),
        serves=(29, 30),
    ),
    DomainQuery(
        name="attribution_precision_audit",
        question="How much attribution is source-stated versus scope-inherited?",
        cypher="""
        MATCH ()-[r:HAS_DEVATA|HAS_RISHI|HAS_CHANDAS]->()
        RETURN type(r) AS predicate, r.attribution_precision AS precision,
               count(*) AS edges
        ORDER BY predicate, edges DESC
        """,
        caveat="This is the query most worth running before trusting any deity ranking.",
        serves=(29, 30),
    ),
    DomainQuery(
        name="layer_coverage_boundary",
        question="Which Vedas does each knowledge layer actually reach?",
        # UNWIND over an explicit label list, never labels(n)[0]. These nodes are heavily
        # multi-labelled and Neo4j does not guarantee labels() ordering, so [0] would
        # return a different label per node -- and potentially a different one after a
        # restart -- while presenting as a stable grouping key.
        cypher="""
        MATCH (n) WHERE n.layer_veda_scope IS NOT NULL
        UNWIND [l IN labels(n) WHERE l IN $layers] AS layer
        RETURN layer, n.layer_veda_scope_source AS derived_from,
               n.layer_veda_scope AS reaches, count(DISTINCT n) AS nodes
        ORDER BY layer, nodes DESC
        """,
        parameters={
            "layers": [
                "Chandas",
                "Rishi",
                "DevataAscription",
                "SemanticAssertion",
                "ActionPredicate",
            ]
        },
        caveat=(
            "The boundary made visible rather than tripped over: `reaches` is measured "
            "from the graph, so a Veda absent from the list means the layer has no coverage "
            "of that corpus and NOT that the corpus lacks the thing. The metre layer splits "
            "34 Rigvedic metre nodes from 578 Atharvavedic ones and shares none, which is a "
            "fact about two Anukramani traditions rather than about Vedic prosody. One "
            "ActionPredicate has reaches = [], meaning it reaches nothing at all. Every row "
            "here is single-Veda: no layer carrying this property spans two corpora, so the "
            "boundary is not a rough edge on one layer, it is the shape of all of them."
        ),
        serves=(21, 29, 30, 36),
    ),
    DomainQuery(
        name="rishi_layer_reach_by_veda",
        question="Which Vedas name a seer, and how much of that is source-stated?",
        cypher="""
        MATCH (p:Passage)-[r:HAS_RISHI]->(rs:Rishi)
        RETURN p.veda AS veda, count(DISTINCT p) AS passages,
               count(DISTINCT rs) AS seers,
               count(DISTINCT CASE WHEN r.attribution_precision = 'PER_PASSAGE'
                                   THEN p END) AS source_stated,
               count(DISTINCT CASE WHEN r.attribution_precision = 'CONTAINER_INHERITED'
                                   THEN p END) AS inherited
        ORDER BY passages DESC
        """,
        caveat=(
            "Three rows, not four, and the shape of the answer is the point: the Samaveda "
            "carries no seer at all, while the Yajurveda's 1,960 passages are 1,960 "
            "source-stated and 0 inherited and the Atharvaveda's 5,084 are the exact "
            "reverse. So 'how many mantras have a named seer' has three different meanings "
            "in three corpora, and a single corpus-wide figure averages a per-verse "
            "attribution against a hymn label. Prefer `source_stated` for any defensible "
            "claim about a named seer."
        ),
        serves=(2, 19, 29, 35),
    ),
    DomainQuery(
        name="chandas_layer_reach_by_veda",
        question="Which Vedas record a metre, and do the two traditions share a vocabulary?",
        cypher="""
        MATCH (p:Passage)-[h:HAS_CHANDAS]->(c:Chandas)
        RETURN p.veda AS veda, count(DISTINCT p) AS passages,
               count(DISTINCT c) AS metres,
               count(DISTINCT CASE WHEN h.attribution_precision = 'PER_PASSAGE'
                                   THEN p END) AS source_stated,
               collect(DISTINCT c.layer_veda_scope)[0..3] AS metre_layer_scope
        ORDER BY passages DESC
        """,
        caveat=(
            "Two rows: RV and AV only, so a question about Yajurvedic or Samavedic metre is "
            "not answerable here. The 34 Rigvedic and 578 Atharvavedic metre nodes are "
            "disjoint sets, which makes `metres` incomparable across the two rows -- the AV "
            "Anukramani names compound and irregular metres individually where the RV's "
            "names a handful of standard ones, so the AV's larger count is a difference in "
            "descriptive practice, not in prosodic variety."
        ),
        serves=(24, 29, 30),
    ),
    DomainQuery(
        name="model_adjudicated_edges",
        question="Which model-extracted edges survived an independent per-passage review?",
        cypher="""
        MATCH (p:Passage)-[r]->(target)
        WHERE r.review_verdict IS NOT NULL
        RETURN type(r) AS predicate, r.quality_tier AS tier,
               r.review_verdict AS verdict, r.review_state AS review_state,
               r.reviewer AS reviewer, count(*) AS edges, count(DISTINCT p) AS passages,
               count(DISTINCT target) AS targets
        ORDER BY edges DESC, predicate
        """,
        caveat=(
            "Complete over the "
            f"{figures.REVIEW_POPULATION['MODEL_ADJUDICATED_EDGES']} reviewed edges. One "
            "MATCH pattern, so count(*) counts "
            "edges as intended, with the distinct passage and target counts beside it. The "
            "verdict is what promotes an edge: "
            f"{figures.REVIEW_POPULATION['TIER_C_PASSAGE_ANCHORED']} ACCEPT_MODEL_REVIEWED "
            "became TIER_C, "
            "while 16 NEEDS_MORE_EVIDENCE and 10 AMBIGUOUS stayed TIER_D rather than being "
            "deleted, so the rejections are still auditable. " + _ADJUDICATION_CAVEAT
        ),
        serves=(29, 30),
    ),
    DomainQuery(
        name="model_adjudicated_review_trail",
        question="Why was one model-extracted edge accepted, in the reviewer's own words?",
        cypher="""
        MATCH (p:Passage)-[r]->(target)
        WHERE r.quality_tier = 'TIER_C'
        RETURN p.canonical_citation AS passage, type(r) AS predicate,
               target.display_label AS target, r.object_kind AS object_kind,
               r.review_reason AS review_reason, r.reviewer_model AS reviewer_model,
               r.review_sanskrit_checked AS sanskrit_checked,
               r.review_passage_read AS passage_read
        ORDER BY passage, predicate, target LIMIT 30
        """,
        caveat=(
            "A top-30 by citation of the "
            f"{figures.REVIEW_POPULATION['TIER_C_PASSAGE_ANCHORED']} passage-anchored "
            "TIER_C edges, which is what this query's MATCH selects and is NOT the whole of "
            "TIER_C; model_adjudicated_edges gives the totals. The reasons cite grammar -- "
            "'agne is a vocative with the imperative "
            "yuksva' -- which is the strongest thing about this layer and also its limit: "
            "the reviewer is a model, `sanskrit_checked` records whether it was shown the "
            "Sanskrit, and a plausible-sounding reason is not a checked one. "
            + _ADJUDICATION_CAVEAT
        ),
        serves=(29, 30),
    ),
    DomainQuery(
        name="theonym_ambiguous_mentions",
        question="Which mentions cannot be told apart from a mention of a deity?",
        cypher="""
        MATCH (p:Passage)-[m:MENTIONS_ENTITY]->(e:DomainEntity)
        WHERE m.theonym_ambiguous
        RETURN e.display_label AS entity, e.display_type AS kind,
               count(*) AS ambiguous_mentions,
               collect(DISTINCT m.matched_aliases)[0..3] AS aliases
        ORDER BY ambiguous_mentions DESC
        """,
        caveat=(
            "An upper bound on deity/concept conflation, not a count of errors: some of "
            "these passages do mean the impersonal referent."
        ),
        serves=(29, 45, 46),
    ),
    DomainQuery(
        name="soma_deity_versus_substance",
        question="How does Soma behave as deity versus substance?",
        cypher="""
        MATCH (p:Passage)-[:HAS_DEVATA]->(dv:Devata)
        WHERE dv.entity_key IN $deities
        WITH collect(DISTINCT p) AS deity_passages
        MATCH (q:Passage)-[m:MENTIONS_ENTITY]->(s:Substance {entity_key: $substance})
        WITH deity_passages, collect(DISTINCT q) AS substance_passages
        RETURN size(deity_passages) AS as_deity_attributed,
               size(substance_passages) AS as_substance_mentioned,
               size([x IN substance_passages WHERE x IN deity_passages]) AS both,
               size([x IN substance_passages WHERE NOT x IN deity_passages])
                 AS substance_only
        """,
        parameters={
            "deities": [SOMA, "VG:DEVATA:PAVAMANAH-SOMAH"],
            "substance": "VG:CONCEPT:SOMA-DRINK",
        },
        caveat=(
            "The deity side is Rigveda-only; the substance side spans four Vedas, so "
            "`substance_only` is inflated by that asymmetry rather than by usage."
        ),
        serves=(17, 45),
    ),
    DomainQuery(
        name="agni_deity_fire_medium",
        question="How does Agni behave as deity, as fire, and as ritual medium?",
        cypher="""
        MATCH (dv:Devata {entity_key: $deity})
        OPTIONAL MATCH (dv)-[:HAS_AXIS]->(ax:DeityAxis)
        WITH dv, collect(DISTINCT ax.axis) AS axes
        CALL (dv) {
            MATCH (p:Passage)-[:HAS_DEVATA]->(dv)
            RETURN count(DISTINCT p) AS attributed_mantras
        }
        CALL () {
            MATCH (q:Passage)-[m:MENTIONS_ENTITY]->(:NaturalPhenomenon {entity_key: $fire})
            RETURN count(DISTINCT q) AS fire_mentions,
                   sum(CASE WHEN m.theonym_ambiguous THEN 1 ELSE 0 END)
                     AS ambiguous_fire_mentions
        }
        RETURN dv.display_label AS deity, axes, attributed_mantras, fire_mentions,
               ambiguous_fire_mentions
        """,
        parameters={"deity": AGNI, "fire": "VG:CONCEPT:AGNI-FIRE"},
        caveat=(
            "The corpus does not lexically distinguish the deity from the element -- both "
            "are the word agni -- so the split between these columns is an editorial "
            "convenience. See VG:CLAIM:AGNI-LEXICALLY-UNDIFFERENTIATED. The two counts are "
            "computed in separate CALL subqueries because they are independent: stacking "
            "them as OPTIONAL MATCH multiplied 3 axes by 1,988 attributed passages by "
            "2,206 fire mentions and took 9.5 seconds to return one row."
        ),
        serves=(20, 46),
    ),
    DomainQuery(
        name="rudra_profile_no_shiva",
        question="What is Rudra's corpus profile, without importing later identity?",
        cypher="""
        MATCH (dv:Devata {entity_key: $key})
        OPTIONAL MATCH (dv)-[:HAS_AXIS]->(ax:DeityAxis)
        WITH dv, collect(DISTINCT ax.axis) AS axes
        CALL (dv) {
            MATCH (p:Passage)-[r:HAS_DEVATA]->(dv)
            RETURN count(DISTINCT p) AS attributed_mantras,
                   sum(CASE WHEN r.attribution_precision = 'PER_PASSAGE' THEN 1 ELSE 0 END)
                     AS source_stated,
                   collect(DISTINCT p.veda) AS vedas
        }
        CALL (dv) {
            MATCH (p:Passage)-[m:MENTIONS_DEVATA]->(dv)
            RETURN p.veda AS veda, count(DISTINCT p) AS named_in,
                   sum(CASE WHEN m.referent_certainty = 'DEITY_CERTAIN' THEN 1 ELSE 0 END)
                     AS certain,
                   sum(CASE WHEN m.referent_certainty = 'DEITY_PROBABLE' THEN 1 ELSE 0 END)
                     AS probable,
                   sum(CASE WHEN m.referent_certainty = 'DEITY_AMBIGUOUS' THEN 1 ELSE 0 END)
                     AS ambiguous
        }
        WITH dv, axes, attributed_mantras, source_stated, vedas,
             collect({veda: veda, named_in: named_in,
                      per_1k_mantras:
                        round(1000.0 * named_in / $corpus_mantras[veda] * 100) / 100,
                      certain: certain, probable: probable,
                      ambiguous: ambiguous}) AS named_by_veda
        RETURN dv.display_label AS deity, dv.structure AS structure, axes,
               dv.short_description AS description, attributed_mantras, source_stated,
               vedas AS ascribed_vedas,
               'HAS_DEVATA is the RV-only Anukramani layer: a non-RV zero here is LAYER '
               + 'ABSENT, not deity absent' AS ascription_zero_means,
               named_by_veda
        """,
        parameters={"key": RUDRA, "corpus_mantras": dict(figures.CORPUS_MANTRAS)},
        caveat=(
            "No Siva identification is asserted anywhere in the graph. Rudra's later "
            "identification with Siva is post-Vedic and recording it here would dress a "
            "historical claim as a textual fact. The attribution counts sit in a CALL "
            "subquery for the reason agni_deity_fire_medium documents: as sibling OPTIONAL "
            "MATCHes in one scope, the axis pattern multiplied the passage pattern, and "
            "`source_stated` -- a sum over rows rather than a count of distinct passages "
            "-- came back as 16 for Rudra's 8 source-stated edges, once per axis. "
            "The four-Veda block is the V3.1 correction: this query returned "
            "vedas=['RV'] and 38 attributed mantras while the same database had Rudra "
            "NAMED in all four corpora, and normalised for corpus size he is DENSER in "
            "the Yajurveda than in the Rigveda -- the Satarudriya effect, which the "
            "HAS_DEVATA-only view made invisible. Read per_1k_mantras, not named_in: the "
            f"Rigveda is {figures.CORPUS_MANTRAS['RV'] / figures.CORPUS_MANTRAS['YV']:.1f}x "
            "the Yajurveda by mantra count, so raw counts flatter it. The certainty "
            "columns are reported rather than filtered because filtering to "
            "DEITY_CERTAIN re-imposes the Rigveda-only answer this fix removes. " + _SCOPE_CAVEAT
        ),
        serves=(43,),
    ),
    # -------------------------------------------------------------- integrity
    DomainQuery(
        name="product_graph_census",
        question="What does the product graph contain, excluding internal plumbing?",
        cypher=f"""
        MATCH (n) WHERE {_NOT_INTERNAL}
        UNWIND labels(n) AS label
        WITH label, count(DISTINCT n) AS nodes
        WHERE NOT label IN ['DomainEntity', 'Mantra']
        RETURN label, nodes ORDER BY nodes DESC
        """,
        caveat="DomainEntity and Mantra are marker/sublabels and would double-count.",
        serves=(),
    ),
    DomainQuery(
        name="internal_leakage_check",
        question="Does any internal diagnostic node reach product traversal?",
        cypher=f"""
        MATCH (n:{LABEL_INTERNAL})
        UNWIND labels(n) AS label
        WITH label WHERE NOT label IN $internal_marked_labels
        RETURN label, count(*) AS leaked_nodes
        """,
        parameters={"internal_marked_labels": sorted(INTERNAL_MARKED_LABELS)},
        caveat=(
            "An empty result is the pass condition. The allow-list is DERIVED from "
            "ontology.INTERNAL_MARKED_LABELS rather than restated here, because a "
            "hard-coded copy of it drifted and this query -- whose entire job is to be "
            "trusted about the product boundary -- reported 10,031 Lemma nodes as leaked. "
            "They are not leaked: V3's fix to adversarial finding M-1 deliberately marked "
            "the whole Lemma layer :Internal, because 39 deity lemmas were surfacing in "
            "product traversal looking like deities while carrying none of a Devata's "
            "profile. That decision was never written anywhere a checker could read. Note "
            "also that the V3 close-out's claim that this check 'returns 0 rows (its pass "
            "condition)' was measured BEFORE the marking landed."
        ),
        serves=(),
    ),
    DomainQuery(
        name="orphan_domain_entities",
        question="Which domain entities have no edge at all?",
        cypher="""
        MATCH (e:DomainEntity)
        WHERE NOT (e)--()
        RETURN e.entity_key AS entity, e.display_type AS kind, e.display_label AS label
        ORDER BY kind, entity
        """,
        caveat=(
            "An orphan is either an entity whose aliases match nothing, or one awaiting "
            "curated edges. Both are reportable; neither is automatically a defect."
        ),
        serves=(),
    ),
    DomainQuery(
        name="unlabelled_product_nodes",
        question="Does any product node lack a human-readable label?",
        cypher=f"""
        MATCH (n) WHERE {_NOT_INTERNAL}
          AND (n.display_label IS NULL OR trim(toString(n.display_label)) IN
               ['', 'UNKNOWN', 'Unknown', 'unknown', 'NULL', 'null', 'None', '?', '-'])
        RETURN labels(n) AS labels, count(*) AS nodes ORDER BY nodes DESC
        """,
        caveat="An empty result is the pass condition (UNKNOWN_LABEL_RATE = 0).",
        serves=(),
    ),
    DomainQuery(
        name="devata_taxonomy_coverage",
        question="How much of the deity taxonomy is real, and how much is UNSPECIFIED?",
        cypher="""
        MATCH (dv:Devata)
        RETURN dv.structure AS structure,
               sum(CASE WHEN dv.is_classified THEN 1 ELSE 0 END) AS with_axes,
               sum(CASE WHEN dv.is_classified THEN 0 ELSE 1 END) AS unspecified,
               count(*) AS total
        ORDER BY total DESC
        """,
        caveat=(
            "UNSPECIFIED is a deliberate value, not a gap to be filled: a justified "
            "UNSPECIFIED is worth more than an invented axis."
        ),
        serves=(),
    ),
    DomainQuery(
        name="entity_kinds_by_veda",
        question="Which kinds of entity does each Veda name, counted per kind?",
        # The label-safe form of entity_distribution_by_veda, which groups on the
        # display_type property. Here the grouping is on the labels themselves, via
        # UNWIND over the node's own label list minus the two structural markers -- so a
        # node labelled Concept:DomainEntity:Object:Weapon is counted once as Object and
        # once as Weapon, which is what its curation means. labels(e)[0] would pick one
        # of the four arbitrarily and silently disagree with this table.
        cypher="""
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(e:DomainEntity)
        UNWIND [l IN labels(e) WHERE NOT l IN $structural] AS kind
        RETURN kind, count(DISTINCT e) AS entities, count(DISTINCT p) AS passages,
               count(DISTINCT p.veda) AS vedas, collect(DISTINCT p.veda) AS veda_list
        ORDER BY passages DESC, kind
        """,
        parameters={"structural": ["Concept", "DomainEntity"]},
        caveat=(
            "Rows overlap by construction and must not be summed: Weapon is a subset of "
            "Object and both are counted, because the curation asserts both. Concept and "
            "DomainEntity are excluded as markers that every row would otherwise carry. "
            "count(DISTINCT p) rather than count(*), because an entity is reached by more "
            "than one mention edge from the same passage and the UNWIND multiplies each of "
            "those by the node's label count."
        ),
        serves=(21, 24, 34, 48),
    ),
)

QUERIES_BY_NAME: Final[dict[str, DomainQuery]] = {q.name: q for q in QUERIES}

assert len(QUERIES_BY_NAME) == len(QUERIES), "duplicate query name"


def questions_served() -> dict[int, list[str]]:
    """Killer-question number to the queries that address it."""
    served: dict[int, list[str]] = {}
    for query in QUERIES:
        for number in query.serves:
            served.setdefault(number, []).append(query.name)
    return dict(sorted(served.items()))
