"""Named domain queries: what a reader can actually ask the graph.

This module is the product surface. Every entry is a question a researcher would put in
words, the Cypher that answers it, and -- the part that matters most -- a ``caveat``
stating what the answer does *not* establish.

The caveat field is not documentation politeness. Three properties of this corpus make an
uncaveated answer actively misleading, and all three are invisible in the result set:

**The annotation layer is unevenly scoped, and the gaps are no longer where they were.**
Only the Rigveda has the manual scholarly morphological annotation, so the predicates
derived from it are Rigveda-only: ``HAS_DEVATA`` (10,558 edges), ``MENTIONS_LEMMA``
(9,000), ``HAS_SEMANTIC_ASSERTION`` (4,865) and the ``PERFORMS_ACTION`` (441) /
``IS_ASKED_TO`` (224) pair derived from those assertions. ``HAS_RISHI`` and
``HAS_CHANDAS`` are *not* in that set any more: ``HAS_RISHI`` now carries 17,889 edges
over RV (10,565), AV (5,084) and YV (2,240), and ``HAS_CHANDAS`` 16,320 over RV (10,523)
and AV (5,797). At mantra level, 10,534 of the RV's 10,552, 4,542 of the AV's 5,839 and
1,960 of the YV's 1,975 mantras carry a seer; the Sāmaveda carries neither predicate.

A zero therefore still has to be read carefully, but now in both directions. A caveat
saying "SV/YV/AV have no attribution layer" *understates* what is answerable, and telling
a researcher a question is unanswerable when it is answerable is the same class of defect
as the reverse, not a safe default. ``MENTIONS_DEVATA`` (16,261 edges: RV 10,284, AV
2,861, YV 1,781, SV 1,335) is the four-Veda route to "does this passage name this
deity?", and is the only deity predicate that reaches the whole corpus.

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

**One label can hold two layers of unequal strength, and summing them is the trap.**
``SemanticAssertion`` is the sharpest case: 2,406 of its 4,865 nodes are TIER_B, derived by
rule from the Sanskrit annotation, and 2,459 are TIER_D, extracted unreviewed by a model
from a 19th-century English translation. They also differ in reach -- the rule layer spreads
over 2,228 passages, the model layer concentrates on 398 -- so a blended count reads as
4,865 assertions over the Rigveda when half of them sit on 3.8% of it. Every query here
either filters ``derivation`` or returns it as a column; none aggregates across it.
``MEMBER_OF_FAMILY`` has the milder version of the same shape, with 2,032 containment-derived
memberships beside 5 similarity-derived ones.

**Coverage boundaries are recorded in the graph, not left to the reader.**
``layer_veda_scope`` on ``Chandas``, ``Rishi``, ``DevataAscription``, ``SemanticAssertion``
and ``ActionPredicate`` states which corpora each layer measurably reaches, and every row of
it is single-Veda: no layer carrying the property spans two. The review layer runs the other
way from everything else -- all 587 TIER_C edges are Yajurvedic (320) or Atharvavedic (267)
and not one is Rigvedic -- so it adjudicates exactly the two corpora the assertion layer
never touches. TIER_C means MODEL_ADJUDICATED; nothing in this graph is HUMAN_REVIEWED.

Queries never return internal nodes: :func:`~vedagraph.domain.ontology.product_filter` is
interpolated rather than each query naming excluded labels itself, so a diagnostic label
added later is excluded by editing one constant.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Final

from vedagraph.domain.ontology import LABEL_INTERNAL

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
_SCOPE_CAVEAT = (
    "HAS_DEVATA is Rigveda-only: 10,558 edges, every one on the RV. A zero for SV/YV/AV "
    "means those corpora carry no Anukramani deity ascription, not that the deity is "
    "absent from them. MENTIONS_DEVATA answers 'is this deity named here?' across all "
    "four (16,261 edges: RV 10,284, AV 2,861, YV 1,781, SV 1,335)."
)
_INHERIT_CAVEAT = (
    "Counts include CONTAINER_INHERITED attributions: a sukta's label projected onto each "
    "of its mantras. See the *_strict variant for source-stated attribution only."
)

#: Attached to every MENTIONS_DEVATA query. The predicate reaches all four corpora, which
#: is why it exists, but it does so by two different instruments, and a row that sums them
#: averages a hand-annotated lemma against a string match without saying so.
_MENTION_LAYER_CAVEAT = (
    "MENTIONS_DEVATA spans all four Vedas (16,261 edges: RV 10,284, AV 2,861, YV 1,781, "
    "SV 1,335) but not by one method: the RV's come from the manual scholarly lemma "
    "annotation (extraction_path = 'rv-lemma-annotation') and the other 5,977 from surface "
    "token or sandhi matching, which has no morphology behind it. Compare rows as shares "
    "of their corpus (RV 10,552 mantras, AV 5,839, YV 1,975, SV 1,844), not as totals."
)

#: Attached where a MENTIONS_DEVATA query does not filter referent_certainty. The flag is
#: on the edge, so a query that ignores it is choosing to, and should say so.
_CERTAINTY_CAVEAT = (
    "Unfiltered on referent_certainty: 8,485 of 16,261 mention edges are DEITY_AMBIGUOUS, "
    "because agni is also fire, soma also the pressed drink, surya also the sun and vac "
    "also speech. Deities whose name is an ordinary noun are flattered accordingly, and "
    "the ambiguous share is the majority in every corpus except the Rigveda."
)

#: Attached to every SemanticAssertion query. One label, two instruments, and summing them
#: is the specific misleading answer this graph exists to refuse.
_ASSERTION_LAYER_CAVEAT = (
    "SemanticAssertion is one label over two layers of unequal strength that must not be "
    "summed: 2,406 nodes carry derivation = 'MORPHOLOGY_RULE' (TIER_B, derived by rule from "
    "the Sanskrit lemma annotation) and 2,459 carry 'MODEL_EXTRACTION' (TIER_D, unreviewed "
    "model output over a 19th-century English translation). All 4,865 are Rigvedic, and "
    "their reach differs as much as their strength: the rule layer spreads its 2,406 over "
    "2,228 passages, the model layer packs its 2,459 into 398. A blended count would read "
    "as 4,865 assertions over the Rigveda when half of them concentrate on 3.8% of it."
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
    "TIER_C means MODEL_ADJUDICATED, not human-reviewed: 587 edges were re-read per passage "
    "by a model and accepted with a stated reason. No edge anywhere in this graph carries "
    "HUMAN_REVIEWED and none may claim to; there is still no human gold set. The layer's "
    "reach also runs opposite to every other derived layer here -- all 587 are Yajurvedic "
    "(320) or Atharvavedic (267) and not one is Rigvedic -- so it reviews exactly the two "
    "corpora the assertion layer never reaches, and the two cannot be compared."
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
        RETURN ax.axis AS axis, count(dv) AS deities,
               collect(dv.display_label)[0..12] AS examples
        ORDER BY deities DESC, axis
        """,
        caveat=(
            "Axes are curated interpretation (TIER_D), not source statements. 101 of 214 "
            "deities are deliberately [UNSPECIFIED] and do not appear here."
        ),
        serves=(20, 38, 41, 46),
    ),
    DomainQuery(
        name="deity_widest_range",
        question="Which deities have the widest functional range?",
        cypher="""
        MATCH (dv:Devata)-[:HAS_AXIS]->(ax:DeityAxis)
        WHERE ax.axis <> 'UNSPECIFIED'
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
        name="deity_co_occurrence",
        question="Which deities are attributed to the same mantras?",
        cypher="""
        MATCH (p:Passage)-[:HAS_DEVATA]->(a:Devata)
        MATCH (p)-[:HAS_DEVATA]->(b:Devata)
        WHERE a.entity_key < b.entity_key
        RETURN a.display_label AS deity_a, b.display_label AS deity_b,
               count(DISTINCT p) AS shared_mantras
        ORDER BY shared_mantras DESC LIMIT 25
        """,
        caveat=_SCOPE_CAVEAT + " " + _INHERIT_CAVEAT,
        serves=(23, 33, 35),
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
        RETURN dv.display_label AS deity, dv.axes AS axes,
               collect(n.display_label) AS phenomena
        ORDER BY deity
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
               AS certain
        WITH dv, collect([veda, passages, certain]) AS per_veda,
             count(veda) AS vedas, sum(passages) AS total,
             sum(certain) AS total_certain
        WHERE vedas = 4
        RETURN dv.display_label AS deity, total AS passages_naming,
               total_certain AS deity_certain, per_veda
        ORDER BY passages_naming DESC, deity
        """,
        caveat=(
            "Complete, not a top-N: every deity naming all four corpora is returned. "
            "`per_veda` rows are [veda, passages, deity_certain]. " + _MENTION_LAYER_CAVEAT
        ),
        serves=(1, 21, 34, 36, 44),
    ),
    DomainQuery(
        name="devata_mention_certainty_by_veda",
        question="How much of the deity-mention layer is certain, per Veda and per method?",
        # One MATCH pattern, so count(*) here is a count of mention edges and is the
        # intended figure; count(DISTINCT p) is returned beside it because the two differ
        # (16,261 edges over fewer passages) and only the pair shows by how much.
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
        serves=(23, 33, 35),
    ),
    DomainQuery(
        name="deity_pairs_not_rigvedic",
        question="Which deity pairings does the corpus outside the Rigveda make its own?",
        cypher="""
        MATCH (a:Devata)-[r:CO_OCCURS_WITH]-(b:Devata)
        WHERE a.entity_key < b.entity_key
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
            "Rigveda contributes 10,284 of the 16,261 mention edges: a pair that still "
            "comes out non-RV-majority against that weighting is a real Yajurvedic or "
            "Atharvavedic association. `per_veda_counts` is ordered [RV, SV, YV, AV]. "
            + _MENTION_LAYER_CAVEAT
        ),
        serves=(1, 23, 33, 36),
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
               count(DISTINCT CASE WHEN m.referent_certainty = 'DEITY_AMBIGUOUS' THEN p END)
                 AS ambiguous,
               count(DISTINCT p) AS passages
        ORDER BY passages DESC
        """,
        parameters={"key": SOMA},
        caveat=(
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
        WHERE m.referent_certainty = 'DEITY_CERTAIN'
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
        },
        caveat=(
            "A top-25 of the deities with at least 20 certain mentions. The family-book / "
            "outer-book split is the conventional stratigraphic reading of the Rigveda and "
            "is an interpretation imported by this query, not a property in the graph: "
            "Passage carries no layer, period or date, so this is the nearest the corpus "
            "comes to a diachronic question and it substitutes book order for time. "
            "Restricted to DEITY_CERTAIN so the comparison is not driven by the ambiguous "
            "common-noun aliases, which would move both columns together anyway."
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
        parameters={
            "actions": ["HEALS", "PROTECTS", "RESCUES", "BLESSES", "RELEASES", "PURIFIES"]
        },
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
        OPTIONAL MATCH (s)-[:ASSERTION_AGENT]->(agent:Devata)
        OPTIONAL MATCH (s)-[:ASSERTION_PREDICATE]->(ap:ActionPredicate)
        OPTIONAL MATCH (s)-[:ASSERTION_TARGET]->(target:Devata)
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
        MATCH (p:Passage)-[m:MENTIONS_ENTITY]->(x:Metal)
        RETURN x.display_label AS metal, p.veda AS veda, count(DISTINCT p) AS mantras,
               collect(DISTINCT m.matched_aliases)[0..3] AS sample_aliases
        ORDER BY metal, mantras DESC
        """,
        caveat=(
            "The bare stem `ayas` was rejected as an alias: it token-matches nothing and "
            "substring-matches 645 times inside payasa/madayasva. Only inflected forms "
            "that occur as whole words are used, so recall is deliberately conservative."
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
        parameters={
            "wealth": ["VG:CONCEPT:VASU-WEALTH", "VG:CONCEPT:HIRANYA-GOLD"]
        },
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
        serves=(25, 40),
    ),
    DomainQuery(
        name="ritual_objects_recurring",
        question="Which ritual objects recur most?",
        cypher="""
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(o:Object)
        RETURN o.display_label AS object, count(DISTINCT p) AS mantras,
               count(DISTINCT p.veda) AS vedas
        ORDER BY mantras DESC
        """,
        caveat="Lexical mentions only.",
        serves=(25, 40),
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
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(r:River)
        MATCH (p)-[:MENTIONS_ENTITY]->(t:Tribe)
        RETURN r.display_label AS river, t.display_label AS tribe,
               count(DISTINCT p) AS mantras, collect(p.canonical_citation)[0..4] AS examples
        ORDER BY mantras DESC LIMIT 20
        """,
        caveat=(
            "Returns nothing, and that is a measured result rather than a missing "
            "feature: 42 tribe mentions and 12 river mentions exist, and no mantra "
            "carries one of each. Question 26 is therefore not answerable by "
            "co-occurrence in this corpus. See tribes_mentioned and rivers_mentioned."
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
        cypher="""
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(c:Condition)
        RETURN c.display_label AS condition, p.veda AS veda,
               count(DISTINCT p) AS mantras
        ORDER BY condition, mantras DESC
        """,
        caveat=(
            "Naming an affliction is weaker than treating it. There is deliberately no "
            "separate 'fever' entity: takman- forms sit in YAKSMA-DISEASE because "
            "splitting them would have put 39% of the paradigm under 'fever' and 61% "
            "under 'disease' invisibly."
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
               collect(DISTINCT other.display_label) AS other_conditions
        ORDER BY passage LIMIT 25
        """,
        parameters={"condition": "VG:CONCEPT:VISA-POISON"},
        caveat=(
            "Co-occurrence within a mantra; no causal or prescriptive claim. Keyed on a "
            "Condition rather than on a healing HumanConcern because the registry has no "
            "healing concern entity: bhesaja was not curated, so passages about healing "
            "are reachable only through the afflictions and plants named in them."
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
        cypher="""
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(pl:Plant)
        OPTIONAL MATCH (p)-[:MENTIONS_ENTITY]->(c:Condition)
        RETURN pl.display_label AS plant, p.veda AS veda, count(DISTINCT p) AS mantras,
               collect(DISTINCT c.display_label) AS co_conditions
        ORDER BY mantras DESC
        """,
        caveat="Co-occurrence, not pharmacology.",
        serves=(47,),
    ),
    DomainQuery(
        name="passages_protecting_against",
        question="What does the corpus ask to be protected from?",
        cypher="""
        MATCH (p:Passage)-[r:PROTECTS_FROM]->(threat)
        RETURN threat.display_label AS threat, threat.display_type AS kind,
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
               collect(DISTINCT off.display_label) AS offerings,
               collect(DISTINCT sub.display_label) AS substances,
               collect(DISTINCT ob.display_label) AS objects,
               collect(DISTINCT dv.display_label) AS deities
        ORDER BY mantras DESC
        """,
        caveat=(
            "Ritual structure is curated and thin by design: elaborate procedure is "
            "largely post-Samhita and was not imported into Samhita passages."
        ),
        serves=(5, 32, 39),
    ),
    DomainQuery(
        name="agni_and_indra_together",
        question="Which passages address both Agni and Indra?",
        cypher="""
        MATCH (p:Passage)-[:HAS_DEVATA]->(:Devata {entity_key: $dual})
        RETURN 'dual entity indragni' AS route, count(DISTINCT p) AS mantras,
               collect(p.canonical_citation)[0..6] AS examples
        UNION ALL
        MATCH (p:Passage)-[:HAS_DEVATA]->(:Devata {entity_key: $a})
        MATCH (p)-[:HAS_DEVATA]->(:Devata {entity_key: $b})
        RETURN 'both singly attributed' AS route, count(DISTINCT p) AS mantras,
               collect(p.canonical_citation)[0..6] AS examples
        """,
        parameters={"a": AGNI, "b": INDRA, "dual": "VG:DEVATA:INDRAGNI"},
        caveat=(
            "The second route returns zero, and that is the finding rather than a gap: "
            "only 6 of 10,552 Rigvedic mantras carry more than one attributed deity, "
            "because the Anukramani names one addressee per mantra. Where the tradition "
            "means the pair it uses a dual deity, which is why VG:DEVATA:INDRAGNI exists "
            "as its own entity, so co-attribution asks the wrong question of this "
            "apparatus. " + _SCOPE_CAVEAT
        ),
        serves=(5, 33),
    ),
    DomainQuery(
        name="ritual_roles",
        question="Which priestly offices does the corpus name?",
        cypher="""
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(rr:RitualRole)
        RETURN rr.display_label AS role, p.veda AS veda, count(DISTINCT p) AS mantras
        ORDER BY role, mantras DESC
        """,
        caveat="Lexical mentions only.",
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
        RETURN rite.display_label AS rite, p.veda AS veda, count(DISTINCT p) AS passages,
               collect(DISTINCT u.quality_tier) AS tiers,
               collect(p.canonical_citation)[0..5] AS examples
        ORDER BY rite, passages DESC
        """,
        caveat=(
            "Complete: all 110 edges over 6 rites. TIER_B, so stronger than PROTECTS_FROM "
            "and TREATS, but it is still a derived reading of a lexical mention rather than "
            "a rubric: recall on the gold-standard book is low, and AV Kanda 14 -- the "
            "marriage book, 141 passages -- contributes only a minority of the marriage "
            "rows. The RV rows are not noise: AV 14 redacts RV 10.85. `examples` is capped "
            "at 5 with the true total in `passages`."
        ),
        serves=(13, 14, 32),
    ),
    # ------------------------------------------------------------- cross-Veda
    DomainQuery(
        name="sv_reuse_of_rv",
        question="Which Rigvedic verses are reused in the Samaveda, and how closely?",
        cypher="""
        MATCH (sv:Passage)-[r:REUSES_TEXT_FROM]->(rv:Passage)
        RETURN sv.canonical_citation AS samaveda, rv.canonical_citation AS rigveda,
               r.match_level AS match_level, r.quality_tier AS tier
        ORDER BY samaveda LIMIT 30
        """,
        caveat=(
            "Cross-script comparison bottoms out at SANDHI_INSENSITIVE, the weakest "
            "surface, because a Devanagari SV text and a Latin RV text share no code "
            "points. A blank match_level means the edge predates level recording."
        ),
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
        caveat="Formula identity is a normalised-string match, not a tradition of reuse.",
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
            "demonstrated line of transmission."
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
        name="conceptually_similar_not_reused",
        question="Which cross-Veda passages share ideas without sharing text?",
        cypher="""
        MATCH (a:Passage)-[:MENTIONS_ENTITY]->(e:DomainEntity)<-[:MENTIONS_ENTITY]-(b:Passage)
        WHERE a.veda < b.veda
        WITH a, b, count(DISTINCT e) AS shared WHERE shared >= 3
        AND NOT (a)-[:EXACT_PARALLEL_OF|NEAR_PARALLEL_OF|REUSES_TEXT_FROM]-(b)
        RETURN a.canonical_citation AS passage_a, b.canonical_citation AS passage_b,
               a.veda AS veda_a, b.veda AS veda_b, shared AS shared_entities
        ORDER BY shared_entities DESC LIMIT 25
        """,
        caveat=(
            "Shared vocabulary is a weak proxy for shared idea, and high-frequency "
            "entities dominate. Treat as a candidate list, not a finding."
        ),
        serves=(22, 49),
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
        RETURN c.claim_id AS claim, c.status AS status, c.confidence AS confidence,
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
        RETURN a.claim_id AS claim_a, a.status AS status_a, a.confidence AS confidence_a,
               b.claim_id AS claim_b, b.status AS status_b, b.confidence AS confidence_b
        """,
        caveat="Neither side is marked as winning.",
        serves=(28,),
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
            "Complete over the 613 reviewed edges. One MATCH pattern, so count(*) counts "
            "edges as intended, with the distinct passage and target counts beside it. The "
            "verdict is what promotes an edge: 587 ACCEPT_MODEL_REVIEWED became TIER_C, "
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
            "A top-30 by citation of 587 TIER_C edges; model_adjudicated_edges gives the "
            "totals. The reasons cite grammar -- 'agne is a vocative with the imperative "
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
        RETURN dv.display_label AS deity, dv.structure AS structure, axes,
               dv.short_description AS description, attributed_mantras, source_stated,
               vedas
        """,
        parameters={"key": RUDRA},
        caveat=(
            "No Siva identification is asserted anywhere in the graph. Rudra's later "
            "identification with Siva is post-Vedic and recording it here would dress a "
            "historical claim as a textual fact. The attribution counts sit in a CALL "
            "subquery for the reason agni_deity_fire_medium documents: as sibling OPTIONAL "
            "MATCHes in one scope, the axis pattern multiplied the passage pattern, and "
            "`source_stated` -- a sum over rows rather than a count of distinct passages "
            "-- came back as 16 for Rudra's 8 source-stated edges, once per axis. "
            + _SCOPE_CAVEAT
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
        WITH label WHERE NOT label IN
          ['{LABEL_INTERNAL}', 'QAIssue', 'TextVersion', 'Translation', 'Source',
           'SourceArtifact']
        RETURN label, count(*) AS leaked_nodes
        """,
        caveat="An empty result is the pass condition.",
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
