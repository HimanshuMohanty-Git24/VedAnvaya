"""Aggregate orchestration: every Cypher an insight route runs, and every typed absence.

**The rule this module exists to keep.** An aggregate is where a zero becomes a claim. So
nothing here reports a figure without also reporting the reason it could be what it is, and
nothing here writes a number into a sentence. Both halves of that matter, and the second is
the one this project learned the hard way: V3.1 and V3.2 each found hand-copied caveat prose
that had drifted from the data it described, and the worst case was a caveat asserting "the
second route returns zero, and that is the finding rather than a gap" over a database that
showed 157 passages naming both deities. A shipped statement contradicted by the shipped
data is worse than no statement, because it converts a gap into a false finding.

Two consequences run through the whole file.

*Caveats are fetched, not written.* :func:`_frozen_caveat` pulls the graded caveat off the
named query in :mod:`vedagraph.domain.queries`; the layer-scope caveats are imported from
that module rather than retyped; and where a caveat has to be assembled it is assembled by
interpolating figures measured in the same request. There is no literal count in any prose
string in this module.

*Queries are reused, not re-authored.* :meth:`Neo4jRepository.run_named` runs the 91-query
frozen library, each entry graded against the 100-question benchmark. A retyped query forks
from the version that was measured, so the Cypher written here is only what the library does
not already hold: the scope read, the cross-Veda class census, the metal enumeration
witness, and the population counts ``/stats`` needs.

**Caching.** None. Every figure in every response is read from the graph on the request that
returns it. The works metadata is four nodes and would be the obvious thing to cache, and it
is not cached, because the offline test suite answers that query from a fake repository: a
process-wide cache would let one test's empty answer become the next test's certified
absence, and certifying an absence against the wrong surface is a mistake this project has
already made twice. Measured cost of not caching it is about 20 ms.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Final

from vedagraph.api.errors import (
    BadRequestError,
    EntityNotFoundError,
    GraphUnavailableError,
    NotFoundError,
)
from vedagraph.api.models.common import (
    AttributionPrecision,
    CaveatView,
    CountedByVeda,
    CoverageView,
    EvidenceSurface,
    EvidenceView,
    KnowledgeStatus,
    PaginationMeta,
    ReferentCertaintyCounts,
    basis_from_attribution_precision,
    evidence_surface,
)
from vedagraph.api.models.entity import DeityPopulation
from vedagraph.api.models.insight import (
    VEDA_ORDER,
    VEDA_PAIRS,
    AtharvavedaConcernsResponse,
    CapabilitiesResponse,
    CapabilityLimit,
    CapabilityMeasurement,
    CapabilityVerdict,
    CivilizationDataRow,
    CivilizationResponse,
    CivilizationSection,
    ConcernEvidenceRow,
    CorpusFigure,
    CostClass,
    CrossVedaCell,
    CrossVedaCellStatus,
    CrossVedaClassView,
    CrossVedaMatrixResponse,
    CrossVedaPairRow,
    CrossVedaRelationshipStat,
    DeclaredLexicalGap,
    DeityPopulationStat,
    DerivedMetricRow,
    DevataInsightResponse,
    FormulaDiffusionResponse,
    FormulaFamilyRow,
    FormulaSpanRow,
    InterpretiveClaimRow,
    MaterialCultureResponse,
    MatrixShape,
    MetalEvidenceStatus,
    MetalRow,
    MetalsInsightResponse,
    MetalVedaCell,
    MethodCensusRow,
    ReuseWitnessRow,
    RitualCoverageView,
    RitualObjectRow,
    RitualsInsightResponse,
    RitualSummaryRow,
    SectionKind,
    SeerPopulationStat,
    StatsResponse,
    VedaCountRow,
    WorkScopeView,
    offset_overrun_caveat,
)
from vedagraph.api.repositories.neo4j_repository import (
    Neo4jRepository,
    named_query_caveat,
)
from vedagraph.api.services.deity_population import is_deity
from vedagraph.domain import layer_figures as figures

# The layer-scope caveats are module-private in the query catalogue and are imported anyway,
# deliberately. They are the sentences the 100-question grading was run against; a second
# copy in this file would be a second thing to keep in step, and the pair falling out of
# step is the exact defect that made three benchmark questions MISLEADING.
from vedagraph.domain.queries import (
    _ADJUDICATION_CAVEAT,
    _ASSERTION_LAYER_CAVEAT,
    _MENTION_LAYER_CAVEAT,
    _SCOPE_CAVEAT,
)

# ---------------------------------------------------------------------------
# Cypher this module owns, because the frozen library does not hold it
# ---------------------------------------------------------------------------

#: The corpus boundaries, read from the ``Work`` nodes that record them. Every per-Veda
#: figure this service emits is accompanied by the matching row, and
#: :class:`~vedagraph.api.models.insight.InsightEnvelope` refuses to construct without it.
_WORKS_QUERY: Final = """
MATCH (w:Work)
RETURN w.veda AS veda, w.work_id AS work_id, w.work_name AS traditional_name,
       w.display_label AS scope_honest_label, w.scope AS scope,
       w.completeness AS completeness, w.excluded_corpora AS excluded_corpora,
       w.scope_source AS scope_source
ORDER BY veda
"""

#: The populations spec section 38 asks for, in one round trip. Each figure is a count of a
#: thing a reader can ask about; the graph's own relationship total is deliberately not
#: among them, because most of those edges are one layer's projection of a container label
#: onto its members and a headline built from them measures the build, not the corpus.
_POPULATION_QUERY: Final = """
CALL () { MATCH (w:Work) RETURN count(w) AS works }
CALL () { MATCH (p:Passage) RETURN count(p) AS passages }
CALL () { MATCH (m:Mantra) RETURN m.veda AS mv, count(*) AS mc }
CALL () { MATCH (:Passage)-[t:HAS_TRANSLATION]->() RETURN count(t) AS translations }
// Two per-Veda tallies rather than one. A bare HAS_TRANSLATION count reports the Samaveda
// at 173, and every one of those 173 is Griffith's Rigvedic rendering attached to a verse
// whose Sanskrit is verified identical -- so the single figure reads as "the Samaveda is
// partly translated", which is the one thing it must not say.
CALL () {
    MATCH (p:Passage)-[:HAS_TRANSLATION]->(t:Translation)
    WHERE t.reuse_kind IS NULL AND t.language = 'en'
    RETURN p.veda AS tv, count(*) AS tc
}
CALL () {
    MATCH (p:Passage)-[:HAS_TRANSLATION]->(t:Translation)
    WHERE t.reuse_kind IS NOT NULL
    RETURN p.veda AS reuse_veda, count(*) AS reuse_count
}
CALL () { MATCH (d:Devata) RETURN d.structure AS ds, count(*) AS dc }
CALL () { MATCH (r:Rishi) RETURN r.is_seer AS seer, r.non_seer_kind AS kind, count(*) AS rc }
CALL () { MATCH (f:RishiFamily) RETURN count(f) AS rishi_families }
CALL () { MATCH (c:Chandas) RETURN count(c) AS chandas }
CALL () { MATCH (c:Concept) RETURN count(c) AS concepts }
CALL () { MATCH (c:PhilosophicalConcept) RETURN count(c) AS philosophical_concepts }
CALL () { MATCH (r:Ritual) RETURN count(r) AS rituals }
CALL () { MATCH (f:Formula) RETURN count(f) AS formulas }
CALL () { MATCH (f:FormulaFamily) RETURN count(f) AS formula_families }
CALL () { MATCH (m:DerivedMetric) RETURN count(m) AS derived_metrics }
CALL () { MATCH (c:InterpretiveClaim) RETURN count(c) AS interpretive_claims }
RETURN works, passages, translations, rishi_families, chandas, concepts,
       philosophical_concepts, rituals, formulas, formula_families, derived_metrics,
       interpretive_claims,
       collect(DISTINCT [mv, mc]) AS mantras_by_veda,
       collect(DISTINCT [tv, tc]) AS translations_by_veda,
       collect(DISTINCT [reuse_veda, reuse_count]) AS reused_renderings_by_veda,
       collect(DISTINCT [ds, dc]) AS devata_structures,
       collect(DISTINCT [seer, kind, rc]) AS rishi_kinds
"""

#: Per class, per corpus pair. Written as a static UNION over typed patterns rather than a
#: parameterised ``type(r) = $cls`` filter: the typed form lets Neo4j scan the relationship
#: type directly and measures about 173 ms against 282 ms, and no client value is involved.
#:
#: ``cross_veda_edges`` and ``directed_edges`` are returned beside ``edges`` because the
#: edge's own ``veda_pair`` is the authority for the pairwise breakdown and the node vedas
#: are the check on it. Where they disagree the cell is typed UNRECONCILED rather than
#: reported, since a pairwise table built on a property that turns out to be wrong is the
#: kind of confident artifact this API exists not to produce.
_CROSS_VEDA_CLASS_QUERY: Final = """
MATCH (a:Passage)-[r:EXACT_PARALLEL_OF]->(b:Passage)
RETURN 'EXACT_PARALLEL_OF' AS relationship_class, r.veda_pair AS veda_pair,
       count(*) AS edges,
       count(CASE WHEN a.veda <> b.veda THEN 1 END) AS cross_veda_edges,
       count(CASE WHEN r.subject_veda IS NOT NULL THEN 1 END) AS directed_edges
UNION ALL
MATCH (a:Passage)-[r:NEAR_PARALLEL_OF]->(b:Passage)
RETURN 'NEAR_PARALLEL_OF' AS relationship_class, r.veda_pair AS veda_pair,
       count(*) AS edges,
       count(CASE WHEN a.veda <> b.veda THEN 1 END) AS cross_veda_edges,
       count(CASE WHEN r.subject_veda IS NOT NULL THEN 1 END) AS directed_edges
UNION ALL
MATCH (a:Passage)-[r:REUSES_TEXT_FROM]->(b:Passage)
RETURN 'REUSES_TEXT_FROM' AS relationship_class, r.veda_pair AS veda_pair,
       count(*) AS edges,
       count(CASE WHEN a.veda <> b.veda THEN 1 END) AS cross_veda_edges,
       count(CASE WHEN r.subject_veda IS NOT NULL THEN 1 END) AS directed_edges
UNION ALL
MATCH (a:Passage)-[r:VARIANT_OF]->(b:Passage)
RETURN 'VARIANT_OF' AS relationship_class, r.veda_pair AS veda_pair,
       count(*) AS edges,
       count(CASE WHEN a.veda <> b.veda THEN 1 END) AS cross_veda_edges,
       count(CASE WHEN r.subject_veda IS NOT NULL THEN 1 END) AS directed_edges
UNION ALL
MATCH (a:Passage)-[r:SHARES_ENTITY_VOCABULARY_WITH]->(b:Passage)
RETURN 'SHARES_ENTITY_VOCABULARY_WITH' AS relationship_class, r.veda_pair AS veda_pair,
       count(*) AS edges,
       count(CASE WHEN a.veda <> b.veda THEN 1 END) AS cross_veda_edges,
       count(CASE WHEN r.subject_veda IS NOT NULL THEN 1 END) AS directed_edges
UNION ALL
MATCH (a:Passage)-[r:PARALLEL_TO]->(b:Passage)
RETURN 'PARALLEL_TO' AS relationship_class, r.veda_pair AS veda_pair,
       count(*) AS edges,
       count(CASE WHEN a.veda <> b.veda THEN 1 END) AS cross_veda_edges,
       count(CASE WHEN r.subject_veda IS NOT NULL THEN 1 END) AS directed_edges
"""

#: The semantic-assertion layer's corpus reach, split by the two derivations that must never
#: be summed. Read for the cross-Veda matrix, whose assertion row is NOT_BUILT for every
#: pair, and this is the measurement that establishes it rather than asserts it.
_ASSERTION_REACH_QUERY: Final = """
MATCH (p:Passage)-[:HAS_SEMANTIC_ASSERTION]->(s:SemanticAssertion)
RETURN p.veda AS veda, s.derivation AS derivation,
       count(DISTINCT s) AS assertions, count(DISTINCT p) AS passages
ORDER BY assertions DESC
"""

#: Product ids for a set of display labels, so an aggregate row can be followed to a
#: detail view.
#:
#: The frozen material-culture and concern queries return ``display_label`` and no key, and
#: an aggregate that hands a client a label it cannot resolve is a row leading nowhere --
#: two renderings of the same seven metals, one of them followable and one not. So the
#: labels are resolved back to nodes here.
#:
#: ``collect(DISTINCT ...)`` rather than a scalar, and the caller drops any label resolving
#: to more than one key. That is the ``profile_co_devatas`` lesson applied: a stored display
#: label is not an identifier, and picking the first of several matches would publish a
#: guess in an id field. Measured today: zero collisions across all 229 registry entities.
_ENTITY_KEY_BY_LABEL_QUERY: Final = """
MATCH (e:DomainEntity)
WHERE e.display_label IN $labels
RETURN e.display_label AS label, collect(DISTINCT e.entity_key) AS keys
"""

#: Which textual surface the semantic layer was read off, split by derivation.
#:
#: Read for the civilization view's interpretation section, because the split is the single
#: most load-bearing disclosure there: half that layer was extracted from a 19th-century
#: English translation and half derived by rule from the Sanskrit annotation, and a claim
#: resting on the first is a claim about a translator. The graph's ``evidence_basis``
#: property answers this question, and it is NOT the API's ``EvidenceBasis`` vocabulary --
#: its value space is :class:`~vedagraph.api.models.common.EvidenceSurface`, and casting one
#: to the other maps every edge in the corpus to UNKNOWN.
_EVIDENCE_SURFACE_QUERY: Final = """
MATCH (s:SemanticAssertion)
RETURN s.evidence_basis AS surface, s.derivation AS derivation, count(*) AS assertions
ORDER BY assertions DESC
"""

#: The metal registry, for the labels and descriptions the grid rows carry.
_METAL_REGISTRY_QUERY: Final = """
MATCH (m:Metal)
RETURN m.entity_key AS entity_key, m.display_label AS display_label,
       m.preferred_label_sa AS preferred_label_sa,
       m.short_description AS short_description
ORDER BY display_label
"""

#: The verse in one corpus that names the most distinct metals, resolved live.
#:
#: This is how the Yajurvedic ``ayas`` locator reaches the response without anyone typing
#: "VSM 18.13" into a string. The declared gap names an entity and a corpus; the citation is
#: measured, and the metals the same verse *is* reached for come back with it, so the row can
#: state what the enumeration contains rather than assert it.
_METAL_ENUMERATION_WITNESS_QUERY: Final = """
MATCH (p:Passage)-[:MENTIONS_ENTITY]->(m:Metal)
WHERE p.veda = $veda
WITH p, count(DISTINCT m) AS metals_named, collect(DISTINCT m.display_label) AS metals
ORDER BY metals_named DESC, p.canonical_citation
LIMIT 1
RETURN p.canonical_citation AS citation, metals_named, metals
"""

#: The ritual layer's bounding figures, measured here rather than described.
#:
#: Both step layers are counted. Counting only ``HAS_STEP`` made this insight state that one
#: rite of 103 "carries any procedure at all" and that "no rite has a recoverable sequence",
#: while 3,121 located sutra steps over 103 rites sat in the graph. The layers stay separate
#: rather than summed: a libation a hymn numbers and a sutra a work prints are different
#: claims, and one total would describe coverage neither layer has.
_RITUAL_COVERAGE_QUERY: Final = """
CALL () { MATCH (r:Ritual) RETURN count(r) AS rituals_modelled }
CALL () { MATCH (r:Ritual) WHERE (r)-[:HAS_STEP]->() RETURN count(r) AS rituals_with_steps }
CALL () { MATCH (:Ritual)-[s:HAS_STEP]->() RETURN count(s) AS step_edges }
CALL () {
    MATCH (r:Ritual) WHERE (r)-[:HAS_RITUAL_STEP]->()
    RETURN count(r) AS rituals_with_procedure
}
CALL () {
    MATCH (:Ritual)-[s:HAS_RITUAL_STEP]->()
    RETURN count(s) AS procedure_step_edges,
           sum(CASE WHEN s.order_completeness = 'PARTIAL_STATED_POSITIONS' THEN 1 ELSE 0 END)
               AS procedure_partial_steps,
           count(DISTINCT s.work_key) AS procedure_source_works
}
CALL () { MATCH (:Ritual)-[:USES_OBJECT]->(o) RETURN count(DISTINCT o) AS implements_curated }
CALL () {
    MATCH (:Ritual)-[:USES_OBJECT]->(o)
    WHERE (:Passage)-[:MENTIONS_ENTITY]->(o)
    RETURN count(DISTINCT o) AS implements_reached
}
CALL () { MATCH (o:Object) RETURN count(o) AS objects_in_registry }
RETURN rituals_modelled, rituals_with_steps, step_edges, rituals_with_procedure,
       procedure_step_edges, procedure_partial_steps, procedure_source_works,
       implements_curated, implements_reached, objects_in_registry
"""

#: Each modelled rite with its curated inventory sizes. Separate from ``ritual_profile``,
#: which collects labels; this counts them, so a client can see that a rite with an empty
#: object list has an empty *curation* rather than an empty apparatus.
_RITUAL_INVENTORY_QUERY: Final = """
MATCH (r:Ritual)
RETURN r.display_label AS ritual, r.entity_key AS entity_key,
       count { (:Passage)-[:MENTIONS_ENTITY]->(r) } AS matched_mantras,
       count { (r)-[:HAS_STEP]->() } AS steps,
       count { (r)-[:USES_OBJECT]->() } AS objects,
       count { (r)-[:USES_OFFERING]->() } AS offerings,
       count { (r)-[:USES_SUBSTANCE]->() } AS substances,
       count { (r)-[:INVOKES_DEVATA]->() } AS devatas
ORDER BY matched_mantras DESC, ritual
"""

#: A bounded page of stored statistics, plus the total so the page is legible as a page.
#:
#: The page is collected inside its own ``CALL`` rather than left as the outer pattern, so
#: this query always returns exactly one row carrying the total and a possibly-empty page.
#: The obvious form -- ``CALL`` for the total, then ``MATCH ... SKIP $offset`` -- loses the
#: total whenever the offset overruns, because the outer pattern yields no rows and the
#: total goes with them. That would have reported ``total_available: 0`` against a live
#: 1,072 on exactly the paging condition the caveat is there to explain, and the caveat's
#: own non-empty guard would then have suppressed it. One defect hiding another.
_DERIVED_METRIC_QUERY: Final = """
CALL () { MATCH (m:DerivedMetric) RETURN count(m) AS total }
CALL () {
    MATCH (m:DerivedMetric)
    WITH m ORDER BY m.metric_name, m.metric_id SKIP $offset LIMIT $limit
    RETURN collect(m {.metric_name, .metric_id, .display_label, .metric_family,
                      .dimension, .subject, .subject_key, .value, .values_json,
                      .interpretation, .method, .scope_note, .quality_tier,
                      .knowledge_layer}) AS page
}
RETURN total, page
"""

#: Interpretive claims with their support, their contradictions and their falsifier.
_CLAIMS_QUERY: Final = """
MATCH (c:InterpretiveClaim)
OPTIONAL MATCH (c)-[:SUPPORTED_BY]->(p:Passage)
OPTIONAL MATCH (c)-[:SUPPORTED_BY_STATISTIC]->(m:DerivedMetric)
OPTIONAL MATCH (c)-[:CONTRADICTS]->(other:InterpretiveClaim)
RETURN c.claim_id AS claim_id, c.claim_text AS claim_text, c.claim_type AS claim_type,
       c.about AS about, c.about_basis AS about_basis, c.asserted_by AS asserted_by,
       c.confidence AS confidence, c.status AS status, c.scope AS scope,
       c.falsifier AS falsifier, c.method AS method, c.quality_tier AS quality_tier,
       collect(DISTINCT p.canonical_citation) AS supported_by_passages,
       collect(DISTINCT m.metric_name) AS supported_by_statistics,
       collect(DISTINCT other.claim_id) AS contradicts
ORDER BY claim_id
"""

#: Claims whose subject is one deity, for the deity insight view.
_CLAIMS_ABOUT_DEVATA_QUERY: Final = """
MATCH (c:InterpretiveClaim)-[:CONCERNS]->(d:Devata {entity_key: $key})
RETURN c.claim_id AS claim_id, c.claim_text AS claim_text, c.claim_type AS claim_type,
       c.about AS about, c.about_basis AS about_basis, c.asserted_by AS asserted_by,
       c.confidence AS confidence, c.status AS status, c.scope AS scope,
       c.falsifier AS falsifier, c.method AS method, c.quality_tier AS quality_tier
ORDER BY claim_id
"""

#: One deity's naming reach, ascription total and stored statistics.
#:
#: The two counts sit in separate ``CALL`` subqueries for the reason the catalogue's
#: ``deity_reach_named_versus_ascribed`` documents: as sibling patterns in one scope the
#: mention pattern multiplies the ascription pattern, and for Indra that is 3,196 x 2,869
#: rows collapsed into a single figure.
_DEVATA_INSIGHT_QUERY: Final = """
MATCH (d:Devata {entity_key: $key})
CALL (d) {
    OPTIONAL MATCH (p:Passage)-[m:MENTIONS_DEVATA]->(d)
      WHERE m.referent_certainty IN $tiers
    RETURN p.veda AS veda, count(DISTINCT p) AS named
}
WITH d, collect([veda, named]) AS named_by_veda
CALL (d) {
    OPTIONAL MATCH (p:Passage)-[m:MENTIONS_DEVATA]->(d)
    RETURN m.referent_certainty AS certainty, count(*) AS edges,
           collect(DISTINCT m.evidence_basis) AS surfaces,
           collect(DISTINCT m.attribution_precision) AS precisions
}
WITH d, named_by_veda, collect([certainty, edges]) AS certainty_split,
     collect(surfaces) AS surface_groups, collect(precisions) AS precision_groups
CALL (d) {
    MATCH (p:Passage)-[:HAS_DEVATA]->(d)
    RETURN count(DISTINCT p) AS ascribed, collect(DISTINCT p.veda) AS ascribed_vedas
}
CALL (d) {
    MATCH (m:DerivedMetric {subject_key: d.entity_key})
    RETURN collect(m {.metric_name, .metric_id, .display_label, .metric_family,
                      .dimension, .subject, .subject_key, .value, .values_json,
                      .interpretation, .method, .scope_note, .quality_tier,
                      .knowledge_layer})[0..25] AS metrics
}
RETURN d.entity_key AS entity_key, d.display_label AS display_label,
       d.structure AS structure, named_by_veda, certainty_split, ascribed,
       ascribed_vedas, metrics, surface_groups, precision_groups
"""

# ---------------------------------------------------------------------------
# Constants describing what the classes and categories are
# ---------------------------------------------------------------------------

#: The relationship classes a cross-Veda question can be asked about, with what each one
#: asserts. Enumerated rather than discovered, because a class with no edges for a pair must
#: still produce a typed cell and a class discovered from the data cannot.
_CROSS_VEDA_CLASSES: Final[tuple[tuple[str, str], ...]] = (
    ("EXACT_PARALLEL_OF", "LITERAL_TEXTUAL_REUSE"),
    ("NEAR_PARALLEL_OF", "LITERAL_TEXTUAL_REUSE"),
    ("REUSES_TEXT_FROM", "LITERAL_TEXTUAL_REUSE"),
    ("VARIANT_OF", "LITERAL_TEXTUAL_REUSE"),
    ("SHARES_ENTITY_VOCABULARY_WITH", "ENTITY_VOCABULARY_OVERLAP"),
    ("PARALLEL_TO", "LITERAL_TEXTUAL_REUSE"),
)

#: Two rows of the matrix that carry no edges by construction and appear anyway. Omitting
#: them would leave a reader with a table of five built classes and no way to know that the
#: two questions people most want answered across corpora were never built.
_UNBUILT_CROSS_VEDA_ROWS: Final[tuple[tuple[str, str, str], ...]] = (
    (
        "SEMANTIC_RESEMBLANCE",
        "SEMANTIC_RESEMBLANCE",
        "No non-lexical resemblance measure exists anywhere in this graph: no embedding, no "
        "vector index, no asserted resemblance. This row is NOT_BUILT rather than zero, "
        "because a zero beside the built classes would read as a finding that Vedic "
        "cross-corpus relatedness is purely textual.",
    ),
    (
        "SEMANTIC_ASSERTION",
        "SEMANTIC_PREDICATION",
        "The semantic-assertion layer cannot contribute to any corpus pair: every one of "
        "its assertions is Rigvedic, so it has no non-Rigvedic endpoint to pair with.",
    ),
)

#: Material-culture categories, each mapped to the frozen query that answers it. The label
#: column differs per query, so the mapping carries it rather than the reader guessing.
_MATERIAL_CATEGORIES: Final[dict[str, tuple[str, str, str]]] = {
    "crops": ("crops_by_veda", "crop", "CROP"),
    "animals": ("animals_by_veda", "animal", "ANIMAL"),
    "rivers": ("rivers_mentioned", "river", "RIVER"),
    "tribes": ("tribes_mentioned", "tribe", "TRIBE"),
    "metals": ("metals_by_veda", "metal", "METAL"),
}

#: Cells the project knows are wrong, declared by entity and corpus and by nothing else.
#:
#: The reason is fetched from the frozen ``metals_by_veda`` caveat and the locator is
#: measured, so this constant carries no figure and no prose that can drift. The Yajurvedic
#: ``ayas`` is the only such cell: the corpus names the metal at the verse this resolves,
#: but the elided Devanagari folds to the token of the relative pronoun, so registering an
#: alias for it would land wrong-sense mentions instead of one right one.
_DECLARED_METAL_GAPS: Final[tuple[tuple[str, str], ...]] = (("VG:CONCEPT:AYAS-METAL", "YV"),)

#: What a NO_LEXICAL_MATCH cell means, said on the cell. Assembled from no numbers at all,
#: so there is nothing in it to fall out of step with the grid it annotates.
_NO_MATCH_NOTE: Final = (
    "No registered alias matched a mantra in this corpus. The registry admits attested "
    "whole-word inflections only, so this is a lower bound of zero and a fact about the "
    "matcher; it is not an attestation that the corpus does not name this thing."
)

#: What a lexical hit means. Also numberless, and also on every row that needs it.
_LEXICAL_MINIMUM_NOTE: Final = (
    "A Sanskrit lexical-match minimum: passages in which a registered alias occurs. Counts "
    "are lower bounds, and a mention is not a claim that the passage is about the thing."
)

_MENTION_LAYER_REACH_NOTE: Final = (
    "The lexical mention layer reaches all four corpora, so a corpus with no figure had no "
    "registered alias match rather than no coverage. A null is still not a zero: alias "
    "recall is partial and measured per entity, not assumed."
)

#: Names a client may pass to ``/insights/material-culture``.
MATERIAL_CATEGORIES: Final[tuple[str, ...]] = ("all", *sorted(_MATERIAL_CATEGORIES))


# ---------------------------------------------------------------------------
# Small coercions. The driver hands back Any; mypy runs strict here
# ---------------------------------------------------------------------------


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    return None


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _as_str(value: Any) -> str | None:
    if isinstance(value, str):
        return value or None
    return None


def _as_str_list(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    out: list[str] = []
    for item in value:
        if isinstance(item, str) and item:
            out.append(item)
        elif isinstance(item, (list, tuple)):
            out.extend(inner for inner in item if isinstance(inner, str) and inner)
    return out


def _pairs_to_counts(value: Any) -> dict[str, int]:
    """Fold a ``collect([key, count])`` column into a mapping, dropping null keys."""
    counts: dict[str, int] = {}
    if not isinstance(value, (list, tuple)):
        return counts
    for item in value:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        key = item[0]
        count = _as_int(item[1])
        if isinstance(key, str) and key and count is not None:
            counts[key] = counts.get(key, 0) + count
    return counts


def _parse_values_json(value: Any) -> dict[str, Any] | None:
    """Read one of the graph's JSON-string metric payloads, degrading rather than raising."""
    if value is None:
        return None
    if isinstance(value, dict):
        return {str(key): item for key, item in value.items()}
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (ValueError, TypeError):
            return None
        if isinstance(parsed, dict):
            return {str(key): item for key, item in parsed.items()}
        return {"value": parsed}
    return None


def _frozen_caveat(query_name: str) -> CaveatView:
    """The graded caveat attached to a named domain query, fetched rather than retyped."""
    return CaveatView(text=named_query_caveat(query_name), source=query_name)


def _measured_caveat(text: str) -> CaveatView:
    return CaveatView(text=text, source="measured")


def _counted_by_veda(
    counts: Mapping[str, int], *, status: KnowledgeStatus, note: str
) -> CountedByVeda:
    """A per-Veda breakdown in which a corpus with no row is null and never nought."""
    return CountedByVeda(
        rv=counts.get("RV"),
        av=counts.get("AV"),
        yv=counts.get("YV"),
        sv=counts.get("SV"),
        status=status,
        note=note,
    )


def _per_1000(counts: Mapping[str, int]) -> dict[str, float]:
    """Mantras-per-thousand for each corpus present, so a share is offered beside the raw."""
    return {veda: figures.per_thousand(count, veda) for veda, count in counts.items()}


def _ordering(values: Mapping[str, float]) -> list[str]:
    return [veda for veda, _ in sorted(values.items(), key=lambda item: (-item[1], item[0]))]


def _has_strict_inversion(raw: Mapping[str, int], normalised: Mapping[str, float]) -> bool:
    """Whether normalising actually reverses a strict raw ordering.

    Compared pairwise rather than by comparing the two sorted lists, because two corpora
    with equal raw counts have no raw ordering to invert -- the sorted lists would differ
    only by an alphabetical tie-break, and reporting that as an inversion would announce a
    disagreement the raw figures do not make. Gold is the real case: 38 Rigvedic mantras
    against 34 Atharvavedic, and 3.601 per thousand against 5.823.
    """
    for first, first_raw in raw.items():
        for second, second_raw in raw.items():
            if first_raw > second_raw and normalised.get(first, 0.0) < normalised.get(second, 0.0):
                return True
    return False


def _paginate_rows[T](rows: list[T], *, limit: int, offset: int) -> tuple[list[T], PaginationMeta]:
    """Bound an already-materialised list and describe the bound.

    Slicing in Python rather than in Cypher is deliberate for the aggregate views: their
    result sets are tens of rows, the frozen queries carry their own ``LIMIT`` where the
    population is large, and re-authoring one of them to add ``SKIP``/``LIMIT`` would fork
    it from the version the benchmark graded.
    """
    page = rows[offset : offset + limit]
    return page, PaginationMeta(
        limit=limit,
        offset=offset,
        returned=len(page),
        total=len(rows),
        has_more=(offset + len(page)) < len(rows),
    )


class InsightService:
    """Every aggregate view, and the typed absence each one needs."""

    def __init__(self, repository: Neo4jRepository) -> None:
        self._repository = repository

    # -- scope -------------------------------------------------------------

    def work_scopes(self) -> dict[str, WorkScopeView]:
        """The four corpora's boundaries, keyed by Veda code.

        Raises rather than returning an empty mapping when the read finds nothing. A
        per-Veda figure whose corpus boundary could not be read must not be served at all:
        the Samavedic figure is the one this protects, and "1,844" published without "THIS
        IS NOT THE COMPLETE SAMAVEDA" is the single most misleading string in the product.
        """
        rows = self._repository.run(_WORKS_QUERY)
        scopes: dict[str, WorkScopeView] = {}
        for row in rows:
            veda = _as_str(row.get("veda"))
            work_id = _as_str(row.get("work_id"))
            if veda is None or work_id is None:
                continue
            scopes[veda] = WorkScopeView(
                veda=veda,
                work_id=work_id,
                traditional_name=_as_str(row.get("traditional_name")),
                scope_honest_label=_as_str(row.get("scope_honest_label")),
                scope=_as_str(row.get("scope")),
                completeness=_as_str(row.get("completeness")),
                excluded_corpora=_as_str_list(row.get("excluded_corpora")),
                scope_source=_as_str(row.get("scope_source")),
            )
        if not scopes:
            raise GraphUnavailableError(
                "The knowledge graph could not report the corpus boundaries, so no "
                "per-corpus figure can be served."
            )
        return scopes

    def _resolve_entity_keys(self, labels: Iterable[str]) -> dict[str, str]:
        """Product ids for these display labels, omitting any that does not resolve to one.

        A label resolving to several entities, or to none, is left out rather than guessed
        at: the caller then reports ``entity_key: null`` for that row, which is honest, and
        never an id that points at the wrong entity. One query for the whole request rather
        than one per category, because five scoped lookups to populate one field is a cost
        with no reader.
        """
        wanted = sorted({label for label in labels if label})
        if not wanted:
            return {}
        resolved: dict[str, str] = {}
        for row in self._repository.run(_ENTITY_KEY_BY_LABEL_QUERY, labels=wanted):
            label = _as_str(row.get("label"))
            keys = _as_str_list(row.get("keys"))
            if label is not None and len(keys) == 1:
                resolved[label] = keys[0]
        return resolved

    def _scope_statements(self, vedas: Iterable[str]) -> list[WorkScopeView]:
        scopes = self.work_scopes()
        wanted = [veda for veda in VEDA_ORDER if veda in set(vedas)]
        return [scopes[veda] for veda in wanted if veda in scopes]

    # -- /stats ------------------------------------------------------------

    def product_stats(self) -> StatsResponse:
        """Corpus and entity populations, with the two deity counts kept apart.

        Labelled an aggregate: it groups over the mantra, translation, deity and seer
        layers in one round trip, and the translation grouping alone touches every
        translation edge in the graph.
        """
        row = self._repository.run_one(_POPULATION_QUERY)
        if row is None:
            raise GraphUnavailableError("The knowledge graph could not report its populations.")

        mantras = _pairs_to_counts(row.get("mantras_by_veda"))
        translations = _pairs_to_counts(row.get("translations_by_veda"))
        reused = _pairs_to_counts(row.get("reused_renderings_by_veda"))
        structures = _pairs_to_counts(row.get("devata_structures"))
        seer_rows = row.get("rishi_kinds")

        corpus: list[CorpusFigure] = [
            CorpusFigure(
                name="works",
                total=_as_int(row.get("works")),
                note="One recension per Veda. Each work's exclusions are in scope_statements.",
            ),
            CorpusFigure(
                name="passages",
                total=_as_int(row.get("passages")),
                note="Mantras plus their containing hymns, sections and structural nodes. "
                "Not a verse count; see 'mantras'.",
            ),
            CorpusFigure(
                name="mantras",
                total=sum(mantras.values()) or None,
                by_veda=_counted_by_veda(
                    mantras,
                    status=KnowledgeStatus.SUPPORTED,
                    note="Addressed verses per corpus. These are the denominators every "
                    "normalised comparison in this API divides by.",
                ),
                denominator=dict(figures.CORPUS_MANTRAS),
            ),
            CorpusFigure(
                name="translations",
                total=_as_int(row.get("translations")),
                by_veda=self._translation_counts(translations),
                denominator=dict(figures.CORPUS_MANTRAS),
                note="Counts a corpus's own English renderings and nothing else. A corpus "
                "with 0 here has no released translation at all, which is a measured fact "
                "about the product's holdings. What it implies downstream is the part that "
                "misleads: every translation-derived layer is absent for that corpus rather "
                "than empty in it. Renderings reused from another corpus are counted under "
                "'reused_renderings' and never here, and Griffith's Latin substitutions are "
                "in neither.",
            ),
            CorpusFigure(
                name="reused_renderings",
                total=sum(reused.values()),
                by_veda=self._translation_counts(reused),
                denominator=dict(figures.CORPUS_MANTRAS),
                note="Another corpus's published English shown against a verse whose "
                "Sanskrit is verified character-identical. Reported apart from "
                "'translations' because it is translation assistance and not evidence about "
                "the corpus it appears in: every one of the Samaveda's is Rigvedic, so "
                "adding the two figures would report a translated Samaveda.",
            ),
        ]

        entity_populations = [
            CorpusFigure(
                name="rishi_families",
                total=_as_int(row.get("rishi_families")),
                note="Seer families. Membership is mostly containment-derived.",
            ),
            CorpusFigure(
                name="chandas",
                total=_as_int(row.get("chandas")),
                note="Metres. The Rigvedic and Atharvavedic metre vocabularies are disjoint "
                "sets, so this total is not a count of distinct prosodic forms.",
            ),
            CorpusFigure(
                name="concepts",
                total=_as_int(row.get("concepts")),
                note="Curated domain entities of every kind: the registry, not the corpus's "
                "vocabulary.",
            ),
            CorpusFigure(
                name="philosophical_concepts",
                total=_as_int(row.get("philosophical_concepts")),
                note="A subset of concepts, counted separately and not additionally.",
            ),
            CorpusFigure(
                name="rituals",
                total=_as_int(row.get("rituals")),
                note="Modelled rites. Not a taxonomy of Vedic ritual; see "
                "/api/v1/insights/rituals for what the layer does and does not cover.",
            ),
            CorpusFigure(
                name="formulas",
                total=_as_int(row.get("formulas")),
                note="Repeated wordings, identified by normalised-string match rather than by "
                "a tradition of reuse.",
            ),
            CorpusFigure(
                name="formula_families",
                total=_as_int(row.get("formula_families")),
                note="A representative wording plus what contains or resembles it.",
            ),
            CorpusFigure(
                name="derived_metrics",
                total=_as_int(row.get("derived_metrics")),
                note="Stored statistics, each with its own method and scope note.",
            ),
            CorpusFigure(
                name="interpretive_claims",
                total=_as_int(row.get("interpretive_claims")),
                note="Model-authored readings, permanently CANDIDATE, each carrying a "
                "falsifier. Not findings.",
            ),
        ]

        class_views, _cells, _unreconciled = self._cross_veda_class_views()
        cross_veda = [
            CrossVedaRelationshipStat(
                relationship_class=view.relationship_class,
                cross_veda_edges=(
                    view.cross_veda_edges
                    if view.cross_veda_edges
                    else (0 if view.population_status == "BUILT" else None)
                ),
                within_one_veda_edges=view.within_one_veda_edges,
                pairs_reached=view.pairs_reached,
                resemblance_kind=view.resemblance_kind,
                note=self._class_reach_note(view),
            )
            for view in class_views
        ]

        return StatsResponse(
            insight="product_stats",
            question="What does this product contain?",
            data_status=KnowledgeStatus.SUPPORTED,
            cost_class=CostClass.AGGREGATE,
            cost_note="Groups over the mantra, translation, deity, seer and cross-Veda "
            "layers. Labelled an aggregate and exempt from the median latency target.",
            vedas_reported=list(VEDA_ORDER),
            scope_statements=self._scope_statements(VEDA_ORDER),
            coverage=CoverageView(
                vedas_in_scope=list(VEDA_ORDER),
                measured=mantras,
                denominator=dict(figures.CORPUS_MANTRAS),
            ),
            caveats=[
                _measured_caveat(
                    "The graph's own relationship count is not reported. Most of its edges "
                    "are one annotation layer's projection of a container label onto the "
                    "passages inside it, so a headline built from them measures this build "
                    "rather than the corpus. The per-population figures above are what a "
                    "reader can act on."
                ),
                _measured_caveat(
                    "Entity population counts overlap by construction and must not be "
                    "summed: a metal is also a substance and a concept, and the curation "
                    "asserts all three."
                ),
                _frozen_caveat("cross_veda_relatedness_method_census"),
            ],
            corpus=corpus,
            entity_populations=entity_populations,
            deities=self._deity_population_stat(structures),
            seers=self._seer_population_stat(seer_rows, _as_int(row.get("rishi_families")) or 0),
            cross_veda_relationships=cross_veda,
        )

    @staticmethod
    def _class_reach_note(view: CrossVedaClassView) -> str:
        """What one class's reach does and does not mean, said on the stats row.

        A class reaching one corpus pair is the case that needs this most: read as a
        cross-corpus finding it says only the Samaveda reuses Rigvedic text, and read as
        what it is it says the directed-reuse layer was assigned for one pair.
        """
        if view.population_status != "BUILT":
            return "Never built. Null rather than 0, because the absence is about this graph."
        if not view.cross_veda_edges:
            return (
                f"All {view.within_one_veda_edges:,} edges of this class join two passages "
                "inside a single corpus, so it contributes nothing to any corpus pair. That "
                "is a property of the class and not a zero for the pairs."
            )
        if len(view.pairs_reached) < len(VEDA_PAIRS):
            return (
                f"Reaches {', '.join(view.pairs_reached)} only. A pair absent from that list "
                "carries no edge of this class, which is a fact about what was built and not "
                "about what the texts share; see /api/v1/insights/cross-veda for the typed "
                "matrix."
            )
        return (
            f"Reaches all {len(VEDA_PAIRS)} corpus pairs. Intra-corpus edges are excluded "
            "from this figure and counted separately."
        )

    def _translation_counts(self, measured: Mapping[str, int]) -> CountedByVeda:
        """Translation counts, where a corpus with none carries a measured 0 and a note.

        This is the one place in the module where 0 is the right answer for an empty layer,
        and the reason is worth stating. The Samaveda has no released translation, and that
        is a measured fact about what this product holds -- not an unknown. A null would say
        "we cannot establish how many translations the Samaveda has", which is false.

        What must not be inferred is anything *downstream*: an SV zero in a
        translation-derived layer is an absent layer and not an absent text, and the SV work
        node says so in as many words. So the zero ships with the note that says it, and the
        status stays PARTIAL so a client cannot read the row as complete coverage.
        """
        counts = {veda: measured.get(veda, 0) for veda in VEDA_ORDER}
        untranslated = [veda for veda, count in counts.items() if not count]
        status = KnowledgeStatus.SUPPORTED if not untranslated else KnowledgeStatus.PARTIAL
        note = (
            "Translations released per corpus."
            if not untranslated
            else f"{', '.join(untranslated)} has no released translation in this build, and "
            "this 0 is a measured fact about what the product holds. It does not mean the "
            "corpus is untranslatable, and it does mean that every translation-derived "
            "figure elsewhere in this API excludes that corpus: a zero from such a layer is "
            "an absent layer, not an absent text."
        )
        return _counted_by_veda(counts, status=status, note=note)

    def _deity_population_stat(self, structures: Mapping[str, int]) -> DeityPopulationStat:
        """Both deity counts, with the resolved population computed from the structures.

        Routed through :func:`~vedagraph.api.services.deity_population.is_deity` rather than
        re-listing the structures, so the resolved population here is the same answer every
        deity surface in this API uses. A structure the contract does not recognise counts
        as a non-deity, which fails closed.
        """
        resolved = sum(count for name, count in structures.items() if is_deity(name))
        total = sum(structures.values())
        return DeityPopulationStat(
            resolved_deities=resolved,
            anukramani_ascriptions=total,
            excluded_non_deities=total - resolved,
            by_structure=dict(sorted(structures.items())),
            note=(
                "Two figures, and they answer different questions. resolved_deities is the "
                "population every deity surface here uses. anukramani_ascriptions is the "
                "tradition's devata slot as it stands, which also holds human patrons, "
                "labels naming a gift rather than a recipient, and one dog. Neither is the "
                "corrected version of the other."
            ),
        )

    def _seer_population_stat(self, rows: Any, families: int) -> SeerPopulationStat:
        """Seers and non-seer addressees, split on the graph's own ``is_seer`` flag."""
        seers = 0
        non_seer = 0
        kinds: dict[str, int] = {}
        if isinstance(rows, (list, tuple)):
            for item in rows:
                if not isinstance(item, (list, tuple)) or len(item) < 3:
                    continue
                count = _as_int(item[2]) or 0
                if item[0] is True:
                    seers += count
                    continue
                non_seer += count
                kind = _as_str(item[1]) or "UNSPECIFIED"
                kinds[kind] = kinds.get(kind, 0) + count
        return SeerPopulationStat(
            seers=seers,
            non_seer_addressees=non_seer,
            non_seer_kinds=dict(sorted(kinds.items())),
            families=families,
            note=(
                "The seer slot of the traditional apparatus also names things that are not "
                "seers: deities, abstractions, mythic beings, a plant, an object. They are "
                "counted separately because a combined figure would be a category error, "
                "and each non-seer kind is enumerated so a client can see which."
            ),
        )

    # -- /insights/cross-veda ---------------------------------------------

    def _cross_veda_class_views(
        self,
    ) -> tuple[list[CrossVedaClassView], dict[tuple[str, str], int], dict[str, int]]:
        """Per-class reach, per-cell counts, and any pair the two measures disagree on.

        The edge's ``veda_pair`` is the authority for the breakdown, as the spec requires,
        and the node vedas are the check. ``unreconciled`` counts, per class, edges whose
        ``veda_pair`` is null while their endpoints sit in different corpora -- zero in this
        build, and typed rather than assumed, because the whole matrix rests on that
        property being right.
        """
        rows = self._repository.run(_CROSS_VEDA_CLASS_QUERY)
        cells: dict[tuple[str, str], int] = {}
        per_class: dict[str, dict[str, int]] = {}
        unreconciled: dict[str, int] = {}
        for row in rows:
            name = _as_str(row.get("relationship_class"))
            if name is None:
                continue
            bucket = per_class.setdefault(
                name, {"cross_veda": 0, "within": 0, "directed": 0, "total": 0}
            )
            edges = _as_int(row.get("edges")) or 0
            cross = _as_int(row.get("cross_veda_edges")) or 0
            directed = _as_int(row.get("directed_edges")) or 0
            pair = _as_str(row.get("veda_pair"))
            bucket["total"] += edges
            bucket["cross_veda"] += cross
            bucket["within"] += edges - cross
            bucket["directed"] += directed
            if pair is None:
                unreconciled[name] = unreconciled.get(name, 0) + cross
                continue
            cells[(name, pair)] = cells.get((name, pair), 0) + edges

        views: list[CrossVedaClassView] = []
        for name, kind in _CROSS_VEDA_CLASSES:
            bucket = per_class.get(name, {"cross_veda": 0, "within": 0, "directed": 0, "total": 0})
            reached = [pair for pair in VEDA_PAIRS if cells.get((name, pair))]
            has_cross = bucket["cross_veda"] > 0
            views.append(
                CrossVedaClassView(
                    relationship_class=name,
                    resemblance_kind=kind,
                    cross_veda_edges=bucket["cross_veda"] if has_cross else None,
                    within_one_veda_edges=bucket["within"],
                    pairs_reached=reached,
                    directed=(bucket["directed"] == bucket["cross_veda"]) if has_cross else None,
                    population_status="BUILT" if bucket["total"] else "NOT_BUILT",
                )
            )
        return views, cells, unreconciled

    def cross_veda_matrix(self) -> CrossVedaMatrixResponse:
        """Every corpus pair against every relationship class, with every cell typed.

        The grid is built from the constant six pairs and the constant class list, so a pair
        a class never reached still gets a row. The alternative -- grouping the query result
        -- silently drops five of ``REUSES_TEXT_FROM``'s six pairs, and a reader of that
        table concludes that only the Samaveda reuses Rigvedic text.
        """
        views, cells, unreconciled = self._cross_veda_class_views()
        assertion_rows = self._repository.run(_ASSERTION_REACH_QUERY)
        assertion_vedas = sorted({_as_str(row.get("veda")) or "" for row in assertion_rows} - {""})
        assertion_total = sum(_as_int(row.get("assertions")) or 0 for row in assertion_rows)

        by_class = {view.relationship_class: view for view in views}
        pair_totals = {
            pair: sum(cells.get((name, pair), 0) for name, _ in _CROSS_VEDA_CLASSES)
            for pair in VEDA_PAIRS
        }

        pair_rows: list[CrossVedaPairRow] = []
        status_counts: dict[str, int] = {}
        for pair in VEDA_PAIRS:
            row_cells: list[CrossVedaCell] = []
            for name, _kind in _CROSS_VEDA_CLASSES:
                cell = self._cross_veda_cell(
                    name=name,
                    pair=pair,
                    edges=cells.get((name, pair), 0),
                    view=by_class[name],
                    other_edges=pair_totals[pair] - cells.get((name, pair), 0),
                    unreconciled=unreconciled.get(name, 0),
                )
                status_counts[cell.status] = status_counts.get(cell.status, 0) + 1
                row_cells.append(cell)
            for name, _kind, why in _UNBUILT_CROSS_VEDA_ROWS:
                note = why
                if name == "SEMANTIC_ASSERTION":
                    note = (
                        f"{why} Measured: {assertion_total:,} assertions over "
                        f"{', '.join(assertion_vedas) or 'no corpus'}."
                    )
                cell = CrossVedaCell(
                    relationship_class=name,
                    pair=pair,
                    edges=None,
                    status=CrossVedaCellStatus.NOT_BUILT,
                    related_edges_on_pair=pair_totals[pair],
                    note=note,
                )
                status_counts[cell.status] = status_counts.get(cell.status, 0) + 1
                row_cells.append(cell)
            pair_rows.append(
                CrossVedaPairRow(
                    pair=pair,
                    vedas=pair.split("-"),
                    cells=row_cells,
                    measured_edges_total=sum(
                        cell.edges or 0
                        for cell in row_cells
                        if cell.status
                        in {CrossVedaCellStatus.MEASURED, CrossVedaCellStatus.MEASURED_ZERO}
                    ),
                )
            )

        census = [
            MethodCensusRow(
                resemblance_kind=_as_str(row.get("resemblance_kind")) or "UNKNOWN",
                method=_as_str(row.get("method")) or "UNKNOWN",
                edges=(
                    _as_int(row.get("edges"))
                    if _as_str(row.get("population_status")) == "BUILT"
                    else None
                ),
                population_status=_as_str(row.get("population_status")) or "UNKNOWN",
                note=(
                    None
                    if _as_str(row.get("population_status")) == "BUILT"
                    else "NOT_BUILT, and therefore null rather than 0: no such measure was "
                    "ever implemented, so its emptiness is about this graph."
                ),
            )
            for row in self._repository.run_named("cross_veda_relatedness_method_census")
        ]

        classes = list(views) + [
            CrossVedaClassView(
                relationship_class=name,
                resemblance_kind=kind,
                cross_veda_edges=None,
                within_one_veda_edges=0,
                pairs_reached=[],
                directed=None,
                population_status="NOT_BUILT",
            )
            for name, kind, _why in _UNBUILT_CROSS_VEDA_ROWS
        ]
        total_classes = len(_CROSS_VEDA_CLASSES) + len(_UNBUILT_CROSS_VEDA_ROWS)

        pairwise_totals_text = ", ".join(f"{pair} {pair_totals[pair]:,}" for pair in VEDA_PAIRS)
        # Same-corpus parallels carry no veda_pair at all, so a matrix that filtered on that
        # property would drop them silently and its cross-corpus share would be a share of a
        # population it never named. They are counted from the node vedas instead and
        # published as their own figure.
        intra_corpus = {
            view.relationship_class: view.within_one_veda_edges
            for view in views
            if view.within_one_veda_edges
        }
        intra_corpus_total = sum(intra_corpus.values())
        intra_corpus_text = (
            ", ".join(f"{name} {count:,}" for name, count in sorted(intra_corpus.items()))
            or "none measured"
        )
        caveats = [
            _frozen_caveat("cross_veda_relatedness_method_census"),
            _measured_caveat(
                "Cells are typed, not merely counted. "
                f"{status_counts.get(CrossVedaCellStatus.MEASURED, 0)} of "
                f"{len(VEDA_PAIRS) * total_classes} cells carry a measured count; the rest "
                "are null with a status, because a class that never reached a pair and a "
                "pair the texts do not share are different answers and this matrix refuses "
                "to render both as 0."
            ),
            _measured_caveat(
                "Do not sum a pair's cells into a relatedness score. An exact parallel, a "
                "directed reuse and a shared entity vocabulary assert different things, and "
                f"the pairwise totals shown ({pairwise_totals_text}) are the sum of the "
                "measured cells only."
            ),
            _frozen_caveat("entity_vocabulary_overlap_candidates"),
            CaveatView(text=_ASSERTION_LAYER_CAVEAT, source="assertion_layer_scope"),
            _measured_caveat(
                "This matrix is the cross-corpus population only, and it is not the whole "
                f"parallel layer: {intra_corpus_total:,} parallel edges join two passages "
                "inside a single corpus and carry no corpus pair at all "
                f"({intra_corpus_text}). They are excluded from every cell here and reported "
                "per class in relationship_classes.within_one_veda_edges, so a cross-corpus "
                "share computed from this matrix alone would overstate itself by that much."
            ),
        ]
        if any(unreconciled.values()):
            caveats.append(
                _measured_caveat(
                    "DEFECT: "
                    + ", ".join(
                        f"{name} has {count:,} cross-corpus edges with no veda_pair"
                        for name, count in sorted(unreconciled.items())
                        if count
                    )
                    + ". Those cells are typed UNRECONCILED and their counts withheld."
                )
            )

        return CrossVedaMatrixResponse(
            insight="cross_veda_relatedness_matrix",
            question="How are the four Samhitas connected, pair by pair and class by class?",
            data_status=KnowledgeStatus.PARTIAL,
            cost_class=CostClass.AGGREGATE,
            cost_note="Scans six relationship types in full plus the assertion layer. "
            "Labelled an aggregate and exempt from the median latency target.",
            vedas_reported=list(VEDA_ORDER),
            scope_statements=self._scope_statements(VEDA_ORDER),
            coverage=CoverageView(
                vedas_in_scope=list(VEDA_ORDER),
                measured=pair_totals,
                denominator=dict(figures.CORPUS_MANTRAS),
            ),
            caveats=caveats,
            pairs=pair_rows,
            relationship_classes=classes,
            method_census=census,
            shape=MatrixShape(
                rows=len(VEDA_PAIRS),
                columns=total_classes,
                cells_expected=len(VEDA_PAIRS) * total_classes,
                cells_returned=sum(len(row.cells) for row in pair_rows),
                cells_by_status=dict(sorted(status_counts.items())),
            ),
        )

    def _cross_veda_cell(
        self,
        *,
        name: str,
        pair: str,
        edges: int,
        view: CrossVedaClassView,
        other_edges: int,
        unreconciled: int,
    ) -> CrossVedaCell:
        """Type one cell. Four ways to be empty, and the row says which."""
        if unreconciled:
            return CrossVedaCell(
                relationship_class=name,
                pair=pair,
                edges=None,
                status=CrossVedaCellStatus.UNRECONCILED,
                related_edges_on_pair=other_edges,
                note=(
                    f"{unreconciled:,} edges of this class join passages in different "
                    "corpora while carrying no veda_pair, so the pairwise breakdown cannot "
                    "be trusted for it and no count is published."
                ),
            )
        if edges:
            return CrossVedaCell(
                relationship_class=name,
                pair=pair,
                edges=edges,
                status=CrossVedaCellStatus.MEASURED,
                note=f"{edges:,} edges of this class join this corpus pair.",
            )
        if view.population_status == "NOT_BUILT":
            return CrossVedaCell(
                relationship_class=name,
                pair=pair,
                edges=None,
                status=CrossVedaCellStatus.NOT_BUILT,
                related_edges_on_pair=other_edges,
                note="This class carries no edges anywhere in the graph.",
            )
        if not view.cross_veda_edges:
            return CrossVedaCell(
                relationship_class=name,
                pair=pair,
                edges=None,
                status=CrossVedaCellStatus.CLASS_NOT_CROSS_VEDA,
                related_edges_on_pair=other_edges,
                note=(
                    f"Every one of this class's {view.within_one_veda_edges:,} edges joins "
                    "two passages within a single corpus, so it does not enter a cross-Veda "
                    "pair at all. This is not a zero for this pair; the class is not about "
                    "pairs."
                ),
            )
        if len(view.pairs_reached) == len(VEDA_PAIRS):
            return CrossVedaCell(
                relationship_class=name,
                pair=pair,
                edges=0,
                status=CrossVedaCellStatus.MEASURED_ZERO,
                related_edges_on_pair=other_edges,
                note=(
                    "This class reaches every other corpus pair, so its zero here is a "
                    "measured figure rather than an unbuilt cell."
                ),
            )
        return CrossVedaCell(
            relationship_class=name,
            pair=pair,
            edges=None,
            status=CrossVedaCellStatus.NOT_ESTABLISHED_FOR_PAIR,
            related_edges_on_pair=other_edges,
            note=(
                f"This class carries {view.cross_veda_edges:,} cross-corpus edges and reaches "
                f"only {', '.join(view.pairs_reached)}. It was not established for {pair}, and "
                f"that is not a statement about the texts: the other classes carry "
                f"{other_edges:,} cross-corpus edges for this very pair."
            ),
        )

    # -- /insights/metals, the Q10 contract -------------------------------

    def metals(self) -> MetalsInsightResponse:
        """The complete metal-by-corpus grid, with the known Yajurvedic gap typed in its row.

        Q10 was graded MISLEADING once for omitting a metal the corpus's own stored Sanskrit
        attests, and the fix that closed it was a shape fix rather than a roster fix: the
        frozen query now returns a full grid in which a cell that matched nothing says so.
        This method carries that through to the response and adds the two things a row-only
        renderer needs. An unmatched cell's count is ``None`` rather than ``0``. And the one
        cell the project knows is wrong -- Yajurvedic ``ayas``, named at a verse this graph
        can locate, unreachable by any alias that would not also land eleven wrong-sense
        mentions -- carries that verse's citation in the cell itself.
        """
        registry = {
            _as_str(row.get("display_label")) or "": row
            for row in self._repository.run(_METAL_REGISTRY_QUERY)
        }
        grid = self._repository.run_named("metals_by_veda")
        gaps = self._declared_metal_gaps(registry)
        gap_by_cell = {(gap.entity_key, gap.veda): gap for gap in gaps}

        measured: dict[str, dict[str, int]] = {}
        normalised: dict[str, dict[str, float]] = {}
        denominators: dict[str, dict[str, int]] = {}
        aliases: dict[str, dict[str, list[str]]] = {}
        for row in grid:
            metal = _as_str(row.get("metal"))
            veda = _as_str(row.get("veda"))
            if metal is None or veda is None:
                continue
            measured.setdefault(metal, {})[veda] = _as_int(row.get("mantras")) or 0
            # The normalised figure is taken from the frozen query's own column rather than
            # recomputed. The graded caveat quotes it to three decimals, and a recomputation
            # rounding to two would put the response one digit away from the sentence
            # describing it -- which is the drift this module exists to prevent, in miniature.
            normalised.setdefault(metal, {})[veda] = _as_float(row.get("per_1000_mantras")) or 0.0
            denominators.setdefault(metal, {})[veda] = _as_int(row.get("corpus_mantras")) or 0
            aliases.setdefault(metal, {})[veda] = _as_str_list(row.get("sample_aliases"))

        rows: list[MetalRow] = []
        cells_returned = 0
        inverted: list[str] = []
        for metal in sorted(measured):
            node = registry.get(metal, {})
            entity_key = _as_str(node.get("entity_key")) or metal
            hits = measured[metal]
            positive = {veda: count for veda, count in hits.items() if count}
            per_1000 = {veda: normalised[metal].get(veda, 0.0) for veda in positive}
            raw_order = _ordering({veda: float(count) for veda, count in positive.items()})
            norm_order = _ordering(per_1000)
            inverts = _has_strict_inversion(positive, per_1000)
            if inverts:
                inverted.append(metal)
            cells: list[MetalVedaCell] = []
            for veda in VEDA_ORDER:
                gap = gap_by_cell.get((entity_key, veda))
                cells.append(
                    self._metal_cell(
                        metal=metal,
                        veda=veda,
                        matched=hits.get(veda, 0),
                        per_1000=normalised[metal].get(veda),
                        corpus_mantras=denominators.get(metal, {}).get(veda)
                        or figures.CORPUS_MANTRAS.get(veda, 0),
                        aliases=aliases.get(metal, {}).get(veda, []),
                        declared_gap=gap,
                    )
                )
                cells_returned += 1
            rows.append(
                MetalRow(
                    metal=metal,
                    entity_key=entity_key,
                    preferred_label_sa=_as_str(node.get("preferred_label_sa")),
                    short_description=_as_str(node.get("short_description")),
                    by_veda=cells,
                    raw_ordering=raw_order,
                    normalised_ordering=norm_order,
                    ordering_inverts=inverts,
                    ordering_note=self._ordering_note(
                        raw_order=raw_order,
                        norm_order=norm_order,
                        per_1000=per_1000,
                        inverts=inverts,
                    ),
                )
            )

        caveats = [_frozen_caveat("metals_by_veda")]
        caveats.append(
            _measured_caveat(
                "Every registered metal is returned against every corpus, so no cell is "
                "omitted. A cell with no lexical match carries a null count and "
                "NO_LEXICAL_MATCH rather than 0: the registry admits attested whole-word "
                "inflections only, so the miss is a fact about the matcher."
            )
        )
        if gaps:
            caveats.append(
                _measured_caveat(
                    "Known-wrong cells, typed in their own rows and not only here: "
                    + "; ".join(
                        f"{gap.display_label} in {gap.veda}, attested at "
                        f"{gap.source_witness or 'a verse this build could not locate'}"
                        for gap in gaps
                    )
                    + ". Read each cell's source_witness before concluding an absence."
                )
            )
        if inverted:
            caveats.append(
                _measured_caveat(
                    "Normalising reorders "
                    + ", ".join(inverted)
                    + ": each of those rows ranks corpora differently raw than per 1,000 "
                    "mantras, and the row states both orderings."
                )
            )

        return MetalsInsightResponse(
            insight="metals_by_veda",
            question="Which metals occur in each Veda?",
            data_status=KnowledgeStatus.PARTIAL,
            cost_class=CostClass.AGGREGATE,
            cost_note="A full metal-by-corpus grid plus one witness lookup per declared "
            "gap. Labelled an aggregate.",
            vedas_reported=list(VEDA_ORDER),
            scope_statements=self._scope_statements(VEDA_ORDER),
            coverage=CoverageView(
                vedas_in_scope=list(VEDA_ORDER),
                measured={
                    veda: sum(hits.get(veda, 0) for hits in measured.values())
                    for veda in VEDA_ORDER
                },
                denominator=dict(figures.CORPUS_MANTRAS),
            ),
            caveats=caveats,
            metals=rows,
            declared_gaps=gaps,
            shape=MatrixShape(
                rows=len(rows),
                columns=len(VEDA_ORDER),
                cells_expected=len(rows) * len(VEDA_ORDER),
                cells_returned=cells_returned,
                cells_by_status={
                    status.value: sum(
                        1 for row in rows for cell in row.by_veda if cell.evidence_status is status
                    )
                    for status in MetalEvidenceStatus
                },
            ),
        )

    @staticmethod
    def _ordering_note(
        *,
        raw_order: Sequence[str],
        norm_order: Sequence[str],
        per_1000: Mapping[str, float],
        inverts: bool,
    ) -> str | None:
        """State the two orderings whenever they differ, and say which kind of difference.

        A strict inversion and a broken tie are both worth reporting and they mean different
        things. Gold is a strict inversion -- 38 Rigvedic mantras against 34 Atharvavedic,
        and 3.601 per thousand against 5.823 -- and calling that "the ranking depends on the
        column" is the whole point. Two corpora with equal raw counts have no raw ordering to
        invert, and saying they do would announce a disagreement the raw figures never made.
        """
        if list(raw_order) == list(norm_order):
            return None
        figures_text = ", ".join(f"{veda} {per_1000[veda]}" for veda in norm_order)
        if inverts:
            return (
                f"Raw ranking {' > '.join(raw_order)} becomes {' > '.join(norm_order)} per "
                f"1,000 mantras ({figures_text}). Compare corpora on the normalised figure; "
                "the raw one partly ranks corpus size."
            )
        return (
            f"The raw counts tie, so {' > '.join(raw_order)} is an alphabetical tie-break "
            f"and not an ordering. Per 1,000 mantras the corpora do order: "
            f"{' > '.join(norm_order)} ({figures_text})."
        )

    def _metal_cell(
        self,
        *,
        metal: str,
        veda: str,
        matched: int,
        per_1000: float | None,
        corpus_mantras: int,
        aliases: Sequence[str],
        declared_gap: DeclaredLexicalGap | None,
    ) -> MetalVedaCell:
        if matched:
            return MetalVedaCell(
                veda=veda,
                matched_mantras=matched,
                per_1000_mantras=per_1000,
                corpus_mantras=corpus_mantras,
                evidence_status=MetalEvidenceStatus.LEXICAL_MATCH_MINIMUM,
                knowledge_status=KnowledgeStatus.PARTIAL,
                sample_aliases=sorted(set(aliases)),
                note=_LEXICAL_MINIMUM_NOTE,
            )
        if declared_gap is not None:
            return MetalVedaCell(
                veda=veda,
                matched_mantras=None,
                per_1000_mantras=None,
                corpus_mantras=corpus_mantras,
                evidence_status=MetalEvidenceStatus.NO_LEXICAL_MATCH,
                knowledge_status=KnowledgeStatus.INSUFFICIENT_EVIDENCE,
                source_witness=declared_gap.source_witness,
                note=declared_gap.reason,
            )
        return MetalVedaCell(
            veda=veda,
            matched_mantras=None,
            per_1000_mantras=None,
            corpus_mantras=corpus_mantras,
            evidence_status=MetalEvidenceStatus.NO_LEXICAL_MATCH,
            knowledge_status=KnowledgeStatus.INSUFFICIENT_EVIDENCE,
            note=f"{_NO_MATCH_NOTE} No alias of {metal} matched a {veda} mantra.",
        )

    def _declared_metal_gaps(
        self, registry: Mapping[str, Mapping[str, Any]]
    ) -> list[DeclaredLexicalGap]:
        """Resolve each declared gap's locator from the graph rather than from a string.

        The declaration itself is an entity key and a corpus code. The citation is measured
        as the verse in that corpus naming the most distinct metals, and the metals the
        mention layer *does* reach there come back with it -- so the row states the
        enumeration it sits inside instead of asserting one.
        """
        by_key = {
            _as_str(row.get("entity_key")): row
            for row in registry.values()
            if _as_str(row.get("entity_key"))
        }
        gaps: list[DeclaredLexicalGap] = []
        for entity_key, veda in _DECLARED_METAL_GAPS:
            node = by_key.get(entity_key, {})
            label = _as_str(node.get("display_label")) or entity_key
            witness = self._repository.run_one(_METAL_ENUMERATION_WITNESS_QUERY, veda=veda)
            citation = _as_str(witness.get("citation")) if witness else None
            co_attested = _as_str_list(witness.get("metals")) if witness else []
            located = (
                f"{label} is named in this corpus at {citation}, the verse this graph "
                f"measures as naming the most metals in it "
                f"({len(co_attested)} reached there: {', '.join(sorted(co_attested))})."
                if citation
                else f"{label} is recorded as named in this corpus, at a verse this build "
                "could not locate."
            )
            gaps.append(
                DeclaredLexicalGap(
                    entity_key=entity_key,
                    display_label=label,
                    veda=veda,
                    source_witness=citation,
                    co_attested_at_witness=sorted(co_attested),
                    reason=(
                        f"NO_LEXICAL_MATCH, and knowingly wrong. {located} No alias reaches "
                        "it here: the elided form folds to a token that is the relative "
                        "pronoun in almost all of its corpus occurrences, so registering it "
                        "would land wrong-sense mentions instead of one right one. This "
                        "cell is therefore NOT '0 occurrences' and NOT 'absent from this "
                        "Veda'. The full lexical reason is the caveat sourced "
                        "'metals_by_veda'."
                    ),
                )
            )
        return gaps

    # -- /insights/material-culture ---------------------------------------

    def material_culture(
        self, *, category: str, limit: int, offset: int
    ) -> MaterialCultureResponse:
        """Crops, animals, metals, rivers and tribes, folded per entity and normalised."""
        if category not in MATERIAL_CATEGORIES:
            # 400 rather than an empty page. "No such category" and "that category is empty"
            # are different answers, and returning [] for the first is the shape this whole
            # module exists to refuse.
            raise BadRequestError(
                f"'{category}' is not a material-culture category.",
                hint=f"Available: {', '.join(MATERIAL_CATEGORIES)}.",
            )
        wanted = sorted(_MATERIAL_CATEGORIES) if category == "all" else [category]
        # Fetched before folding so the labels of every requested category can be resolved
        # to product ids in one query rather than one per category.
        fetched: list[tuple[str, str, str, list[dict[str, Any]]]] = []
        caveats: list[CaveatView] = []
        for name in wanted:
            query_name, label_column, kind = _MATERIAL_CATEGORIES[name]
            caveats.append(_frozen_caveat(query_name))
            fetched.append((label_column, kind, query_name, self._repository.run_named(query_name)))
        keys = self._resolve_entity_keys(
            _as_str(row.get(label_column)) or ""
            for label_column, _kind, _query_name, result in fetched
            for row in result
        )
        rows: list[VedaCountRow] = []
        for label_column, kind, _query_name, result in fetched:
            rows.extend(
                self._fold_veda_rows(
                    result,
                    label_column=label_column,
                    count_column="mantras",
                    kind=kind,
                    keys=keys,
                )
            )
        rows.sort(key=lambda row: (-(row.total_mantras or 0), row.label))
        page, pagination = _paginate_rows(rows, limit=limit, offset=offset)
        caveats.append(_measured_caveat(_MENTION_LAYER_REACH_NOTE))
        overrun = offset_overrun_caveat(pagination)
        if overrun is not None:
            caveats.append(overrun)
        measured_totals: dict[str, int] = {}
        for row in rows:
            for veda in VEDA_ORDER:
                value = getattr(row.by_veda, veda.lower())
                if isinstance(value, int):
                    measured_totals[veda] = measured_totals.get(veda, 0) + value
        return MaterialCultureResponse(
            insight="material_culture",
            question="What material culture does the corpus name, and where?",
            # Derived from the whole collection and never from the page. An empty page at a
            # large offset is a client asking for page four million of a forty-row table,
            # and answering that with INSUFFICIENT_EVIDENCE spends a status meaning
            # "evidence exists and cannot support the claim" on an arithmetic error --
            # which makes the status worth less everywhere it means what it says.
            data_status=KnowledgeStatus.PARTIAL if rows else KnowledgeStatus.INSUFFICIENT_EVIDENCE,
            cost_class=CostClass.AGGREGATE,
            cost_note="One grouped mention scan per requested category, plus one label "
            "resolution. Labelled an aggregate.",
            vedas_reported=list(VEDA_ORDER),
            scope_statements=self._scope_statements(VEDA_ORDER),
            coverage=CoverageView(
                vedas_in_scope=list(VEDA_ORDER),
                measured=measured_totals,
                denominator=dict(figures.CORPUS_MANTRAS),
            ),
            caveats=caveats,
            category=category,
            rows=page,
            pagination=pagination,
            categories_available=list(MATERIAL_CATEGORIES),
        )

    def _fold_veda_rows(
        self,
        rows: Sequence[Mapping[str, Any]],
        *,
        label_column: str,
        count_column: str,
        kind: str,
        keys: Mapping[str, str] | None = None,
    ) -> list[VedaCountRow]:
        """Fold one-row-per-(entity, Veda) results into one row per entity.

        The folding is where a zero would otherwise be invented. A corpus absent from the
        result gets ``None`` and a note, not ``0``: the mention layer reaches all four
        corpora, so a missing corpus means no registered alias matched there, and alias
        recall is measured to be partial.

        ``keys`` carries the resolved product ids. A label absent from it yields
        ``entity_key: null`` rather than a guess, which is the only honest answer for a
        label that resolved to several entities or to none.
        """
        resolved = keys or {}
        grouped: dict[str, dict[str, int]] = {}
        statuses: dict[str, set[str]] = {}
        for row in rows:
            label = _as_str(row.get(label_column))
            veda = _as_str(row.get("veda"))
            if label is None or veda is None:
                continue
            count = _as_int(row.get(count_column)) or 0
            if count:
                grouped.setdefault(label, {})[veda] = count
            else:
                grouped.setdefault(label, {})
            status = _as_str(row.get("evidence_status"))
            if status:
                statuses.setdefault(label, set()).add(status)
        folded: list[VedaCountRow] = []
        for label in sorted(grouped):
            counts = grouped[label]
            evidence = (
                "/".join(sorted(statuses[label])) if label in statuses else "LEXICAL_MATCH_MINIMUM"
            )
            folded.append(
                VedaCountRow(
                    label=label,
                    kind=kind,
                    entity_key=resolved.get(label),
                    total_mantras=sum(counts.values()) or None,
                    by_veda=_counted_by_veda(
                        counts,
                        status=(
                            KnowledgeStatus.PARTIAL
                            if len(counts) < len(VEDA_ORDER)
                            else KnowledgeStatus.SUPPORTED
                        ),
                        note=_MENTION_LAYER_REACH_NOTE,
                    ),
                    per_1000_by_veda=_per_1000(counts),
                    vedas_reached=len(counts) or None,
                    evidence_status=evidence,
                    note=_LEXICAL_MINIMUM_NOTE if counts else _NO_MATCH_NOTE,
                )
            )
        return folded

    # -- /insights/rituals, the Q25 contract ------------------------------

    def rituals(self, *, limit: int, offset: int) -> RitualsInsightResponse:
        """The ritual layer, and the partial answer Q25 is entitled to.

        Q25 asks which ritual objects recur most. The version that was graded MISLEADING
        ranked a flat object class and returned the chariot and the thunderbolt; the frozen
        replacement intersects the mention layer with implements a modelled rite actually
        uses, so those two are excluded by construction rather than by a blocklist. What
        this method adds is the bound: the layer's own numbers, measured, and a
        ``not_covered`` list that the model refuses to let be empty.
        """
        coverage_row = self._repository.run_one(_RITUAL_COVERAGE_QUERY) or {}
        object_rows = self._repository.run_named("ritual_objects_recurring")
        inventory = self._repository.run_named("ritual_profile")
        inventory_counts = self._repository.run(_RITUAL_INVENTORY_QUERY)

        modelled = _as_int(coverage_row.get("rituals_modelled")) or 0
        with_steps = _as_int(coverage_row.get("rituals_with_steps")) or 0
        step_edges = _as_int(coverage_row.get("step_edges")) or 0
        with_procedure = _as_int(coverage_row.get("rituals_with_procedure")) or 0
        procedure_edges = _as_int(coverage_row.get("procedure_step_edges")) or 0
        procedure_partial = _as_int(coverage_row.get("procedure_partial_steps")) or 0
        procedure_works = _as_int(coverage_row.get("procedure_source_works")) or 0
        curated = _as_int(coverage_row.get("implements_curated"))
        reached = _as_int(coverage_row.get("implements_reached"))
        registry = _as_int(coverage_row.get("objects_in_registry"))

        objects = [
            RitualObjectRow(
                implement=_as_str(row.get("ritual_implement")) or "",
                registry_type=_as_str(row.get("registry_type")),
                matched_mantras_minimum=_as_int(row.get("matched_mantras_minimum")) or 0,
                vedas_with_matches=_as_int(row.get("vedas_with_matches")) or 0,
                curated_rituals=_as_int(row.get("curated_rituals")) or 0,
                evidence_status=_as_str(row.get("evidence_status")) or "PARTIAL_ALIAS_RECALL",
            )
            for row in object_rows
            if _as_str(row.get("ritual_implement"))
        ]
        object_page, object_bounds = _paginate_rows(objects, limit=limit, offset=offset)

        coverage_note = next(
            (
                _as_str(row.get("inventory_coverage"))
                for row in inventory
                if _as_str(row.get("inventory_coverage"))
            ),
            None,
        )
        summaries = [
            RitualSummaryRow(
                ritual=_as_str(row.get("ritual")) or "",
                entity_key=_as_str(row.get("entity_key")),
                matched_mantras=_as_int(row.get("matched_mantras")) or 0,
                steps=_as_int(row.get("steps")) or 0,
                objects=_as_int(row.get("objects")) or 0,
                offerings=_as_int(row.get("offerings")) or 0,
                substances=_as_int(row.get("substances")) or 0,
                devatas=_as_int(row.get("devatas")) or 0,
                inventory_coverage=coverage_note,
            )
            for row in inventory_counts
            if _as_str(row.get("ritual"))
        ]
        ritual_page, ritual_bounds = _paginate_rows(summaries, limit=limit, offset=offset)

        caveats = [
            _frozen_caveat("ritual_objects_recurring"),
            _frozen_caveat("ritual_profile"),
            _measured_caveat(
                f"PARTIAL, and here is the bound: {modelled} rites are modelled. "
                f"{with_steps} of them {'carries' if with_steps == 1 else 'carry'} a step "
                f"the Samhita text numbers in its own words ({step_edges} such edges in the "
                f"whole graph), and {with_procedure} carry sutra-attested procedure "
                f"({procedure_edges:,} steps from {procedure_works} works, of which "
                f"{procedure_partial:,} state a position without printing the run it falls "
                "in). The two are not one figure and neither is a complete procedure. A "
                f"ranking here is a ranking within {modelled} curated rites and is not a "
                "statement about Vedic ritual."
            ),
        ]
        caveats.extend(
            caveat
            for caveat in (
                offset_overrun_caveat(object_bounds),
                offset_overrun_caveat(ritual_bounds),
            )
            if caveat is not None
        )

        return RitualsInsightResponse(
            insight="ritual_layer",
            question="Which ritual objects recur most, and what does the ritual layer cover?",
            data_status=KnowledgeStatus.PARTIAL,
            cost_class=CostClass.AGGREGATE,
            cost_note="Two grouped mention scans over the curated ritual layer plus its "
            "inventory counts. Labelled an aggregate.",
            vedas_reported=list(VEDA_ORDER),
            scope_statements=self._scope_statements(VEDA_ORDER),
            coverage=CoverageView(
                vedas_in_scope=list(VEDA_ORDER),
                measured={"curated_implements": curated or 0, "reached_by_mentions": reached or 0},
                denominator=dict(figures.CORPUS_MANTRAS),
            ),
            caveats=caveats,
            coverage_view=RitualCoverageView(
                rituals_modelled=modelled,
                rituals_with_steps=with_steps,
                step_edges=step_edges,
                rituals_with_procedure=with_procedure,
                procedure_step_edges=procedure_edges,
                procedure_partial_steps=procedure_partial,
                procedure_source_works=procedure_works,
                implements_curated=curated,
                implements_reached_by_mentions=reached,
                statement=(
                    f"{modelled} modelled rites, and no rite has a recoverable sequence on "
                    f"either layer. {step_edges} step edges state an order in the Samhita's "
                    f"own words. A second and much larger layer is sutra-attested -- "
                    f"{procedure_edges:,} steps over {with_procedure} rites from "
                    f"{procedure_works} works -- but it does not close the gap: each work "
                    f"numbers its own sequence, so the works do not compose into one "
                    f"procedure, and {procedure_partial:,} of those steps state a position "
                    f"without printing the run it falls in. Located steps, not procedures. "
                    f"{curated if curated is not None else 'Some'} of "
                    f"{registry if registry is not None else 'the'} curated objects are "
                    "linked to a rite and so eligible for the implement ranking, and "
                    f"{reached if reached is not None else 'an unmeasured number'} of those "
                    "are reached by the mention layer at all. Two ceilings apply and both "
                    "are real: the curation links only some objects to a rite, and the "
                    "corpus does not hold the post-Samhita prose in which the apparatus is "
                    "actually described."
                ),
            ),
            objects=object_page,
            rituals=ritual_page,
            # One block per collection, each describing itself. A single shared block once
            # reported returned=0 while eight rites sat in the body beside it.
            collections={"objects": object_bounds, "rituals": ritual_bounds},
            not_covered=[
                "The chariot and the thunderbolt are absent by construction, not by "
                "blocklist: they are objects no modelled rite uses. That is the fix for the "
                "version of this question that ranked them as the corpus's foremost ritual "
                "objects.",
                f"{curated if curated is not None else 'Some'} of "
                f"{registry if registry is not None else 'the'} curated objects are linked "
                "to a rite, so genuine ritual objects are missing here for want of a link "
                "rather than for want of attestation -- the amulet and the drum among them. "
                "Their absence is not an absence from the corpus.",
                "No rite has a full recoverable sequence. The Samhita layer holds "
                f"{step_edges} step edges over {modelled} rites, and the sutra layer's "
                f"{procedure_edges:,} steps are located points in {procedure_works} "
                "independently numbered works rather than one procedure; "
                f"{procedure_partial:,} of them do not print the run they fall in.",
                "The Brahmana and Srautasutra prose that actually describes the srauta "
                "apparatus is not held by this product at all, so the apparatus is visible "
                "only where a Samhita verse happens to name it.",
            ],
        )

    # -- /insights/atharvaveda/concerns -----------------------------------

    def atharvaveda_concerns(self, *, limit: int, offset: int) -> AtharvavedaConcernsResponse:
        """What the Atharvaveda is about, with afflictions, threats and causes kept apart.

        Reported across all four corpora on purpose. The Atharvaveda leads every row here,
        and a reader shown the AV column alone cannot tell whether that is Atharvavedic
        specialisation or the only column anyone measured -- which is the same shape as
        reading a missing annotation layer as a silent text.
        """
        concern_rows = self._repository.run_named("human_concerns_by_veda")
        affliction_rows = self._repository.run_named("conditions_treated")
        rite_rows = self._repository.run_named("social_rites")
        # One resolution for all three collections, so every row a client sees can be
        # followed to its entity rather than ending at a display label.
        keys = self._resolve_entity_keys(
            [
                *(_as_str(row.get("concern")) or "" for row in concern_rows),
                *(_as_str(row.get("condition")) or "" for row in affliction_rows),
                *(_as_str(row.get("rite")) or "" for row in rite_rows),
            ]
        )
        concerns = self._fold_veda_rows(
            concern_rows,
            label_column="concern",
            count_column="mantras",
            kind="HUMAN_CONCERN",
            keys=keys,
        )
        concerns.sort(key=lambda row: (-(row.total_mantras or 0), row.label))
        afflictions = self._fold_veda_rows(
            affliction_rows,
            label_column="condition",
            count_column="mantras",
            kind="AFFLICTION",
            keys=keys,
        )
        afflictions.sort(key=lambda row: (-(row.total_mantras or 0), row.label))
        rites = self._fold_veda_rows(
            rite_rows,
            label_column="rite",
            count_column="mantras",
            kind="SOCIAL_RITE",
            keys=keys,
        )
        rites.sort(key=lambda row: (-(row.total_mantras or 0), row.label))

        evidence_rows: list[ConcernEvidenceRow] = []
        for row in self._repository.run_named("concerns_addressed_versus_protected_from"):
            target = _as_str(row.get("target"))
            predicate = _as_str(row.get("predicate"))
            if target is None or predicate is None:
                continue
            per_veda = _pairs_to_counts(row.get("by_veda"))
            evidence_rows.append(
                ConcernEvidenceRow(
                    target=target,
                    kind=_as_str(row.get("kind")),
                    condition_kind=_as_str(row.get("condition_kind")),
                    predicate=predicate,
                    tier=_as_str(row.get("tier")),
                    passages=_as_int(row.get("passages")) or 0,
                    by_veda=_counted_by_veda(
                        per_veda,
                        status=KnowledgeStatus.PARTIAL,
                        note="A corpus with no figure carries no edge of this predicate for "
                        "this target. The three predicates differ in tier and must not be "
                        "summed.",
                    ),
                )
            )

        concern_page, concern_bounds = _paginate_rows(concerns, limit=limit, offset=offset)
        affliction_page, affliction_bounds = _paginate_rows(afflictions, limit=limit, offset=offset)
        rite_page, rite_bounds = _paginate_rows(rites, limit=limit, offset=offset)
        evidence_page, evidence_bounds = _paginate_rows(evidence_rows, limit=limit, offset=offset)
        bounds = {
            "concerns": concern_bounds,
            "afflictions": affliction_bounds,
            "protection_and_treatment": evidence_bounds,
            "social_rites": rite_bounds,
        }
        overruns = [
            caveat
            for caveat in (offset_overrun_caveat(meta) for meta in bounds.values())
            if caveat is not None
        ]
        return AtharvavedaConcernsResponse(
            insight="atharvaveda_concerns",
            question="What human concerns does the corpus address, and on what evidence?",
            data_status=KnowledgeStatus.PARTIAL,
            cost_class=CostClass.AGGREGATE,
            cost_note="Four grouped mention scans plus the three-predicate concern join and "
            "one label resolution. Labelled an aggregate.",
            vedas_reported=list(VEDA_ORDER),
            scope_statements=self._scope_statements(VEDA_ORDER),
            coverage=CoverageView(
                vedas_in_scope=list(VEDA_ORDER),
                measured={
                    "concerns": len(concerns),
                    "afflictions": len(afflictions),
                    "social_rites": len(rites),
                },
                denominator=dict(figures.CORPUS_MANTRAS),
            ),
            caveats=[
                _frozen_caveat("human_concerns_by_veda"),
                _frozen_caveat("conditions_treated"),
                _frozen_caveat("concerns_addressed_versus_protected_from"),
                _frozen_caveat("social_rites"),
                _measured_caveat(
                    "Afflictions are separated from threats and causes by condition_kind on "
                    "the row. An earlier version of this question ranked demons, sorcery and "
                    "worms as diseases; the apotropaic material is still reachable, under "
                    "its own kind."
                ),
                _measured_caveat(
                    "The registry has no healing entity -- bhesaja was never curated -- so "
                    "'what does the corpus do about illness' is reachable only through the "
                    "afflictions and plants a verse names, never through a stated remedy."
                ),
                *overruns[:1],
            ],
            concerns=concern_page,
            afflictions=affliction_page,
            protection_and_treatment=evidence_page,
            social_rites=rite_page,
            # Four collections, four blocks. One shared block would have described three of
            # them wrongly, and a client reading it would read three real lists as empty.
            collections=bounds,
        )

    # -- /insights/formula-diffusion --------------------------------------

    def formula_diffusion(self, *, limit: int, offset: int) -> FormulaDiffusionResponse:
        """How shared wording spreads, with the single-corpus baseline kept in view."""
        span = [
            FormulaSpanRow(
                vedas_reached=_as_int(row.get("vedas_reached")) or 0,
                cross_veda=bool(row.get("cross_veda")),
                families=_as_int(row.get("families")) or 0,
                memberships=_as_int(row.get("memberships")) or 0,
                occurrences=_as_int(row.get("occurrences")) or 0,
            )
            for row in self._repository.run_named("formula_family_span_census")
        ]
        families: list[FormulaFamilyRow] = []
        for row in self._repository.run_named("formula_families_reaching_all_four_vedas"):
            representative = _as_str(row.get("representative"))
            if representative is None:
                continue
            per_veda = _parse_values_json(row.get("occurrences_per_veda")) or {}
            families.append(
                FormulaFamilyRow(
                    representative=representative,
                    members=_as_int(row.get("members")) or 0,
                    core=_as_int(row.get("core")),
                    expansions=_as_int(row.get("expansions")),
                    variants=_as_int(row.get("variants")),
                    occurrences=_as_int(row.get("occurrences")) or 0,
                    occurrences_per_veda={
                        str(key): _as_int(value) or 0 for key, value in per_veda.items()
                    },
                    tier=_as_str(row.get("tier")),
                )
            )
        family_page, family_bounds = _paginate_rows(families, limit=limit, offset=offset)
        witnesses = [
            ReuseWitnessRow(
                samaveda=_as_str(row.get("samaveda")) or "",
                rigveda=_as_str(row.get("rigveda")) or "",
                match_level=_as_str(row.get("match_level")),
                tier=_as_str(row.get("tier")),
            )
            for row in self._repository.run_named("sv_reuse_of_rv")
            if _as_str(row.get("samaveda"))
        ]
        witness_page, witness_bounds = _paginate_rows(witnesses, limit=limit, offset=offset)
        span_page, span_bounds = _paginate_rows(span, limit=limit, offset=offset)
        bounds = {
            "span_census": span_bounds,
            "widest_families": family_bounds,
            "reuse_witnesses": witness_bounds,
        }
        overruns = [
            caveat
            for caveat in (offset_overrun_caveat(meta) for meta in bounds.values())
            if caveat is not None
        ]

        single = next((row.families for row in span if row.vedas_reached == 1), 0)
        four = next((row.families for row in span if row.vedas_reached == 4), 0)
        total_families = sum(row.families for row in span)
        return FormulaDiffusionResponse(
            insight="formula_diffusion",
            question="How does shared wording spread across the four Samhitas?",
            data_status=KnowledgeStatus.PARTIAL,
            cost_class=CostClass.AGGREGATE,
            cost_note="Three grouped reads over the formula-family layer. Labelled an aggregate.",
            vedas_reported=list(VEDA_ORDER),
            scope_statements=self._scope_statements(VEDA_ORDER),
            coverage=CoverageView(
                vedas_in_scope=list(VEDA_ORDER),
                measured={"families": total_families, "reaching_all_four": four},
                denominator=dict(figures.CORPUS_MANTRAS),
            ),
            caveats=[
                _frozen_caveat("formula_family_span_census"),
                _frozen_caveat("formula_families_reaching_all_four_vedas"),
                _frozen_caveat("sv_reuse_of_rv"),
                _measured_caveat(
                    f"{four} of {total_families} families reach all four corpora and {single} "
                    "reach one, and the second figure is the baseline the first should be "
                    "read against. A family is a shared wording identified by normalised "
                    "string match, so its span measures diction and not a demonstrated line "
                    "of transmission."
                ),
                _measured_caveat(
                    "The Samavedic reuse witnesses are directed RV-to-SV and exist for that "
                    "pair only. No other corpus pair carries a directed reuse edge, which is "
                    "a property of what was built rather than of what the texts share; see "
                    "/api/v1/insights/cross-veda for the pairwise matrix that types it."
                ),
                *overruns[:1],
            ],
            span_census=span_page,
            widest_families=family_page,
            reuse_witnesses=witness_page,
            # The span census is complete over all families and the other two are pages, so
            # one block cannot describe all three without lying about two of them.
            collections=bounds,
        )

    # -- /insights/civilization -------------------------------------------

    def civilization(self, *, limit: int, offset: int) -> CivilizationResponse:
        """The corpus's world in three sections that are not one list.

        A census: the data section groups the whole mention layer by label. The three
        sections carry separate statuses and separate caveats, and the section model refuses
        to hold a row of a kind other than the one it declares, so a claim cannot arrive in
        the data section by accident.
        """
        data_rows = [
            CivilizationDataRow(
                kind=_as_str(row.get("kind")) or "",
                entities=_as_int(row.get("entities")) or 0,
                passages=_as_int(row.get("passages")) or 0,
                vedas_reached=_as_int(row.get("vedas")) or 0,
                vedas=[veda for veda in VEDA_ORDER if veda in _as_str_list(row.get("veda_list"))],
            )
            for row in self._repository.run_named("entity_kinds_by_veda")
            if _as_str(row.get("kind"))
        ]
        data_page, data_bounds = _paginate_rows(data_rows, limit=limit, offset=offset)

        # Paged in Cypher, so the bounds are assembled from the query's own total rather
        # than from a materialised list this method never holds.
        metric_row = self._repository.run_one(
            _DERIVED_METRIC_QUERY, limit=limit, offset=offset
        ) or {"total": 0, "page": []}
        metric_total = _as_int(metric_row.get("total")) or 0
        metrics = [
            self._metric_row(metric)
            for metric in (metric_row.get("page") or [])
            if isinstance(metric, dict)
        ]
        metric_bounds = PaginationMeta(
            limit=limit,
            offset=offset,
            returned=len(metrics),
            total=metric_total,
            has_more=(offset + len(metrics)) < metric_total,
        )

        # Paged like the other two. It was not, and under limit=5 it returned all six
        # claims while reporting returned: 6 -- the same six rows at every offset.
        all_claims = [self._claim_row(row) for row in self._repository.run(_CLAIMS_QUERY)]
        claims, claim_bounds = _paginate_rows(all_claims, limit=limit, offset=offset)
        surface_split = self._semantic_evidence_surfaces()
        section_bounds = {
            SectionKind.DATA.value: data_bounds,
            SectionKind.DERIVED_METRIC.value: metric_bounds,
            SectionKind.INTERPRETIVE_CLAIM.value: claim_bounds,
        }
        overruns = [
            caveat
            for caveat in (offset_overrun_caveat(meta) for meta in section_bounds.values())
            if caveat is not None
        ]

        sections = [
            CivilizationSection(
                section_kind=SectionKind.DATA,
                title="What the corpus names",
                what_this_is="Measured Sanskrit lexical attestation: how many curated "
                "entities of each kind the corpus names, and in how many passages. The "
                "strongest rows in this view, and still lower bounds.",
                data_status=KnowledgeStatus.PARTIAL,
                total_available=len(data_rows),
                returned=len(data_page),
                caveats=[
                    _frozen_caveat("entity_kinds_by_veda"),
                    _measured_caveat(_LEXICAL_MINIMUM_NOTE),
                ],
                data_rows=data_page,
            ),
            CivilizationSection(
                section_kind=SectionKind.DERIVED_METRIC,
                title="What this project computed over it",
                what_this_is="Stored statistics, each carrying its own method and scope "
                "note. A metric is a reproducible derivation from the graph and not a "
                "reading of the corpus; several carry a scope note saying in as many words "
                "that a zero for a non-Rigvedic corpus means that corpus has no such layer.",
                data_status=KnowledgeStatus.PARTIAL,
                total_available=metric_total,
                returned=len(metrics),
                caveats=[
                    _measured_caveat(
                        "Read each metric's scope_note before comparing it with another. The "
                        "attribution metrics are Rigveda-only because the layer they measure "
                        "is, and a metric with a null value carries its finding in `values` "
                        "instead."
                    ),
                    CaveatView(text=_SCOPE_CAVEAT, source="has_devata_layer_scope"),
                ],
                metric_rows=metrics,
            ),
            CivilizationSection(
                section_kind=SectionKind.INTERPRETIVE_CLAIM,
                title="What a model read into it",
                what_this_is="Interpretation, and never a finding. Every claim here is "
                "model-authored, permanently CANDIDATE, and carries the falsifier that "
                "would refute it. Two of them contradict each other on purpose: that is "
                "the state of the question rather than an error to resolve.",
                data_status=KnowledgeStatus.INSUFFICIENT_EVIDENCE,
                total_available=len(all_claims),
                returned=len(claims),
                caveats=[
                    _frozen_caveat("claim_evidence_trace"),
                    _frozen_caveat("competing_interpretations"),
                    _measured_caveat(
                        "INSUFFICIENT_EVIDENCE is the status of the section, not of any one "
                        "claim: these are readings this project can neither establish nor "
                        "refute, and none is asserted to a named scholarly position."
                    ),
                    _measured_caveat(surface_split),
                ],
                claim_rows=claims,
            ),
        ]

        return CivilizationResponse(
            insight="civilization",
            question="What does the corpus say about the world it came from?",
            data_status=KnowledgeStatus.PARTIAL,
            cost_class=CostClass.CENSUS,
            cost_note="A census. The data section groups the entire mention layer by label, "
            "so its cost is proportional to that layer and cannot be indexed away. No "
            "latency target applies to this endpoint.",
            vedas_reported=list(VEDA_ORDER),
            scope_statements=self._scope_statements(VEDA_ORDER),
            caveats=[
                _measured_caveat(
                    "Three sections, three kinds of thing, and they are not three confidence "
                    "levels of one assertion. A lexical count can be exactly right while the "
                    "interpretation beside it is false. Do not merge the sections into one "
                    "ranked list."
                ),
                _measured_caveat(
                    f"Section sizes: {len(data_rows)} measured entity kinds, "
                    f"{metric_total} stored statistics, {len(all_claims)} interpretive "
                    "claims. The last number is small because interpretation here is "
                    "deliberate and enumerated, not because the corpus is uncontroversial. "
                    "Each section is paged separately; see `collections`."
                ),
                *overruns[:1],
            ],
            sections=sections,
            collections=section_bounds,
        )

    def _semantic_evidence_surfaces(self) -> str:
        """Which textual surface the semantic layer rests on, measured and per derivation.

        The disclosure that separates a claim about the Vedas from a claim about a
        translator. Half the semantic layer was extracted by a model from a 19th-century
        English rendering and half derived by rule from the Sanskrit annotation, and a reader
        who cannot see which is reading Griffith as if he were the Samhita.

        Uses the graph's ``evidence_basis`` property, whose value space is
        :class:`~vedagraph.api.models.common.EvidenceSurface` and is disjoint from the API's
        :class:`~vedagraph.api.models.common.EvidenceBasis` -- reading one as the other
        reported every attribution edge in the corpus as UNKNOWN once already.
        """
        rows = self._repository.run(_EVIDENCE_SURFACE_QUERY)
        if not rows:
            return (
                "The textual surface behind the semantic layer could not be measured on this "
                "request, so no claim here should be read as resting on the Sanskrit."
            )
        parts: list[str] = []
        translation_total = 0
        for row in rows:
            surface = evidence_surface(_as_str(row.get("surface")))
            derivation = _as_str(row.get("derivation")) or "unrecorded derivation"
            count = _as_int(row.get("assertions")) or 0
            parts.append(f"{count:,} read off {surface.value} via {derivation}")
            if surface is EvidenceSurface.TRANSLATION:
                translation_total += count
        return (
            "Which text the evidence was read off, measured: "
            + "; ".join(parts)
            + f". {translation_total:,} of those rest on a 19th-century English rendering "
            "rather than on the Sanskrit, so a reading built on them is evidence about a "
            "translator. The two surfaces must not be aggregated into one confidence."
        )

    def _metric_row(self, row: Mapping[str, Any]) -> DerivedMetricRow:
        return DerivedMetricRow(
            metric_name=_as_str(row.get("metric_name")) or "",
            metric_id=_as_str(row.get("metric_id")) or "",
            display_label=_as_str(row.get("display_label")),
            metric_family=_as_str(row.get("metric_family")),
            dimension=_as_str(row.get("dimension")),
            subject=_as_str(row.get("subject")),
            subject_key=_as_str(row.get("subject_key")),
            value=_as_float(row.get("value")),
            values=_parse_values_json(row.get("values_json")),
            interpretation=_as_str(row.get("interpretation")),
            method=_as_str(row.get("method")),
            scope_note=_as_str(row.get("scope_note")),
            quality_tier=_as_str(row.get("quality_tier")),
            knowledge_layer=_as_str(row.get("knowledge_layer")),
        )

    def _claim_row(self, row: Mapping[str, Any]) -> InterpretiveClaimRow:
        return InterpretiveClaimRow(
            claim_id=_as_str(row.get("claim_id")) or "",
            claim_text=_as_str(row.get("claim_text")) or "",
            claim_type=_as_str(row.get("claim_type")),
            about=_as_str(row.get("about")),
            about_basis=_as_str(row.get("about_basis")),
            asserted_by=_as_str(row.get("asserted_by")),
            confidence=_as_str(row.get("confidence")),
            status=_as_str(row.get("status")),
            scope=_as_str(row.get("scope")),
            falsifier=_as_str(row.get("falsifier"))
            or "No falsifier is recorded for this claim, which is itself a reason to treat "
            "it as unusable: a reading that cannot say what would refute it is not testable.",
            method=_as_str(row.get("method")),
            quality_tier=_as_str(row.get("quality_tier")),
            supported_by_passages=_as_str_list(row.get("supported_by_passages")),
            supported_by_statistics=_as_str_list(row.get("supported_by_statistics")),
            contradicts=_as_str_list(row.get("contradicts")),
        )

    # -- /insights/capabilities, the Q23 / Q25 contract -------------------

    def capabilities(self, *, question: int | None) -> CapabilitiesResponse:
        """What this product will not answer, measured live and typed as a refusal.

        Served as data so a frontend can enumerate the boundary rather than discovering it
        by getting an empty list back from a reasonable question. Each entry's measurements
        are read from the graph on this request, so the catalogue cannot drift from the
        graph the way a hand-written limitations page would.
        """
        all_limits = self._capability_limits()
        limits = all_limits
        if question is not None:
            limits = [limit for limit in all_limits if limit.question_number == question]
            if not limits:
                raise NotFoundError(
                    f"No recorded capability limit for question {question}.",
                    hint="GET /api/v1/insights/capabilities lists every recorded limit.",
                )
        return CapabilitiesResponse(
            insight="capabilities",
            question="What can this product not answer, and why?",
            data_status=KnowledgeStatus.SUPPORTED,
            cost_class=CostClass.AGGREGATE,
            cost_note="Runs the frozen capability probes that establish each limit. "
            "Labelled an aggregate.",
            vedas_reported=[],
            scope_statements=[],
            caveats=[
                _measured_caveat(
                    "Every limit here is a fact about this graph, never about the Vedas. "
                    "NOT_ANSWERABLE means the dimension the question asks about was not "
                    "built; it does not mean the corpus is silent, and an answer of 'we "
                    "cannot establish this' is the honest outcome rather than a shortfall."
                ),
                _measured_caveat(
                    "This catalogue is not exhaustive. It records the limits the "
                    "100-question benchmark graded and probed; a question absent from it is "
                    "not thereby answerable."
                ),
            ],
            limits=limits,
            total_available=len(all_limits),
            requested_question=question,
        )

    def _capability_limits(self) -> list[CapabilityLimit]:
        return [
            self._q23_deity_communities(),
            self._q25_ritual_objects(),
            self._q22_conceptual_similarity(),
            self._q28_rival_readings(),
            self._q52_assertions_outside_the_rigveda(),
            self._q77_calibrated_confidence(),
            self._q82_samavedic_melody(),
        ]

    def _q23_deity_communities(self) -> CapabilityLimit:
        """Q23. The refusal the benchmark grades NOT_ANSWERABLE, with its measurements.

        The failure this replaces is instructive: asked for deity communities, the obvious
        query returned a confident four-row pair table whose top and fourth rows were human
        patrons, while no community structure existed anywhere in the graph. A clean zero
        would have been better than a plausible table, and a typed refusal is better than
        either.
        """
        rows = self._repository.run_named("deity_community_capability")
        row = rows[0] if rows else None
        assigned = _as_int(row.get("assigned_deities")) if row else None
        eligible = _as_int(row.get("eligible_deities")) if row else None
        pairwise = _as_int(row.get("pairwise_edges")) if row else None
        scope = _as_str(row.get("evidence_scope")) if row else None
        return CapabilityLimit(
            limit_id="deity_communities",
            question_number=23,
            question="What deity communities emerge from the corpus?",
            verdict=CapabilityVerdict.NOT_ANSWERABLE,
            data_status=KnowledgeStatus.NOT_BUILT,
            why=(
                "No community structure exists anywhere in this graph. No node carries a "
                "community, louvain or partition assignment, no modularity was computed and "
                "no partition is stored, so there is nothing to return and nothing to "
                "compute it from. Pairwise co-occurrence exists and is a different object: "
                f"{scope or 'pairwise co-occurrence is not a community partition'}."
            ),
            what_this_is_not=(
                "This is NOT a finding that Vedic deities form no communities, and it is NOT "
                "an empty result. The dimension was never built. Substituting the deity-pair "
                "table for it is how this question was graded MISLEADING: that table's "
                "top-ranked members were human patrons carried in the deity registry, "
                "presented in a deity column with nothing saying so."
            ),
            measurements=[
                CapabilityMeasurement(
                    name="deities_with_a_community_assignment",
                    value=assigned,
                    means="Nodes carrying any community, louvain or partition property. This "
                    "zero is the finding: it is about the graph, not the pantheon.",
                ),
                CapabilityMeasurement(
                    name="eligible_deities",
                    value=eligible,
                    means="A denominator, not a census. It is the devata registry minus the "
                    "entries typed as human, and it still carries gift-praise labels and one "
                    "non-divine subject.",
                ),
                CapabilityMeasurement(
                    name="pairwise_co_occurrence_edges",
                    value=pairwise,
                    means="Deity pairs that share passages. Real, and not a partition: pairs "
                    "cannot be read as communities without a clustering nobody ran.",
                ),
            ],
            safe_alternative=(
                "Deity pairs far above chance, with lift and per-corpus counts over all four "
                "Vedas. It answers a narrower question honestly and is still pairs."
            ),
            what_would_change_it=(
                "A stored community assignment computed over an explicitly declared "
                "projection. A projection chosen at query time will not do: the natural one "
                "over passages and entities is directed and bipartite, on which betweenness "
                "is 0.0 for every node, so the obvious analysis returns a full sortable "
                "ranking of zeros."
            ),
            endpoint="/api/v1/insights/capabilities?question=23",
            caveats=[_frozen_caveat("deity_community_capability")],
        )

    def _q25_ritual_objects(self) -> CapabilityLimit:
        """Q25. A real answer, labelled partial, with the recall shortfall measured."""
        row = self._repository.run_one(_RITUAL_COVERAGE_QUERY) or {}
        modelled = _as_int(row.get("rituals_modelled"))
        step_edges = _as_int(row.get("step_edges"))
        curated = _as_int(row.get("implements_curated"))
        reached = _as_int(row.get("implements_reached"))
        registry = _as_int(row.get("objects_in_registry"))
        procedure_edges = _as_int(row.get("procedure_step_edges"))
        procedure_works = _as_int(row.get("procedure_source_works"))
        reached_text = "some" if reached is None else f"{reached}"
        curated_text = "the" if curated is None else f"{curated}"
        steps_text = "a handful of" if step_edges is None else f"{step_edges}"
        rites_text = "the" if modelled is None else f"{modelled}"
        registry_text = "the object registry" if registry is None else f"{registry} objects"
        procedure_text = (
            "a sutra-attested layer exists but was not measured"
            if procedure_edges is None
            else f"a second layer holds {procedure_edges:,} sutra-attested steps from "
            f"{procedure_works or 'several'} works, which are located points in "
            "independently numbered sources rather than one procedure"
        )
        return CapabilityLimit(
            limit_id="recurring_ritual_objects",
            question_number=25,
            question="Which ritual objects recur most?",
            verdict=CapabilityVerdict.PARTIALLY_ANSWERABLE,
            data_status=KnowledgeStatus.PARTIAL,
            why=(
                "There is a real ranking and it covers part of the question. Ritual implement "
                "means an object a modelled rite is curated to use, which makes the "
                f"population small: {curated_text} of {registry_text} in the registry are "
                f"linked to a rite, and {reached_text} of those are reached by the mention "
                "layer at all. What is partial is per-implement recall rather than class "
                "membership: every count is a lexical minimum over registered whole-word "
                "aliases, and the caveat sourced 'ritual_objects_recurring' measures the "
                "shortfall for the sacrificial post and the altar. Procedure in the "
                f"Samhita's own words is thinner still, at {steps_text} step edges across "
                f"{rites_text} rites; {procedure_text}."
            ),
            what_this_is_not=(
                "The ranking is NOT a census of Vedic ritual apparatus and a low count is NOT "
                "absence from a Veda. Two ceilings sit above it: the curation, which links "
                f"{curated_text} of {registry_text} to a rite at all, and the corpus, which "
                "does not include the Brahmana and Srautasutra prose where the apparatus is "
                "actually described. The earlier version of this answer ranked the chariot "
                "and the thunderbolt first, which is why the class is now defined by use in a "
                "rite rather than by being an object."
            ),
            measurements=[
                CapabilityMeasurement(
                    name="rituals_modelled",
                    value=modelled,
                    means="Rites with a node. A rank in the table is a rank within these.",
                ),
                CapabilityMeasurement(
                    name="step_edges",
                    value=step_edges,
                    means="Steps a Samhita text numbers in its own words, whole graph. On "
                    "this evidence no rite has a recoverable full sequence.",
                ),
                CapabilityMeasurement(
                    name="procedure_step_edges",
                    value=procedure_edges,
                    means="Steps a Srautasutra or Grhyasutra prints -- a different claim "
                    "about a different source, so a separate measurement and never summed "
                    "with step_edges. Each work numbers its own sequence, so these are "
                    "located points and still not a recoverable procedure.",
                ),
                CapabilityMeasurement(
                    name="curated_implements",
                    value=curated,
                    means="Objects a modelled rite is curated to use. The population the "
                    "ranking is drawn from.",
                ),
                CapabilityMeasurement(
                    name="objects_in_the_registry",
                    value=registry,
                    means="Every curated object, ritual or not. The difference from "
                    "curated_implements is the curation ceiling: an object with no link to a "
                    "rite is absent from the ranking however often the corpus names it.",
                ),
                CapabilityMeasurement(
                    name="implements_reached_by_the_mention_layer",
                    value=reached,
                    means="Of those, the ones any passage is measured to name. The gap is "
                    "alias recall, not textual absence.",
                ),
            ],
            safe_alternative=(
                "The full ritual layer view, which returns the implement ranking together "
                "with the figures that bound it and an explicit list of what it does not "
                "cover."
            ),
            what_would_change_it=(
                "A ritual-implement class complete enough that the sacrificial post and the "
                "altar are not below their attested frequency, plus the post-Samhita prose "
                "that describes the apparatus."
            ),
            endpoint="/api/v1/insights/rituals",
            caveats=[
                _frozen_caveat("ritual_objects_recurring"),
                _frozen_caveat("ritual_profile"),
            ],
        )

    def _q22_conceptual_similarity(self) -> CapabilityLimit:
        rows = self._repository.run_named("cross_veda_relatedness_method_census")
        built = sum(
            _as_int(row.get("edges")) or 0
            for row in rows
            if _as_str(row.get("population_status")) == "BUILT"
        )
        semantic = next(
            (row for row in rows if _as_str(row.get("population_status")) == "NOT_BUILT"), None
        )
        return CapabilityLimit(
            limit_id="conceptual_similarity_without_shared_text",
            question_number=22,
            question="Which passages are lexically different but conceptually similar?",
            verdict=CapabilityVerdict.NOT_ANSWERABLE,
            data_status=KnowledgeStatus.NOT_BUILT,
            why=(
                "No non-lexical similarity measure exists in this graph: no embedding, no "
                "vector index, no asserted semantic resemblance. Every cross-corpus "
                "relatedness edge here is literal reuse or shared entity vocabulary, so "
                "'conceptually similar' can only be operationalised as 'shares a word', "
                "which is what the question excludes."
            ),
            what_this_is_not=(
                "The literal-to-semantic split of cross-corpus relatedness in this graph is "
                "total, and read as a finding that would say Vedic relatedness is purely "
                "textual. It says no semantic measure was built. Entity-vocabulary overlap is "
                "offered under its own name and is not a substitute: three shared entities are "
                "weak evidence when they are heaven, sacrifice and soma."
            ),
            measurements=[
                CapabilityMeasurement(
                    name="semantic_resemblance_edges",
                    value=None,
                    means="NOT_BUILT, and therefore null rather than 0: the population does "
                    f"not exist. The census reports it as "
                    f"{_as_str(semantic.get('population_status')) if semantic else 'NOT_BUILT'}.",
                ),
                CapabilityMeasurement(
                    name="built_relatedness_edges",
                    value=built,
                    means="Cross-corpus edges that do exist, all of them literal reuse or "
                    "entity-vocabulary overlap.",
                ),
            ],
            safe_alternative=(
                "Entity-vocabulary overlap ranked on distinctiveness rather than on a raw "
                "shared-entity count, with every row typing its own conceptual-similarity "
                "column as unestablished."
            ),
            what_would_change_it=(
                "An embedding or a human-annotated semantic type over the passages, so that "
                "similarity is measurable without shared vocabulary."
            ),
            endpoint="/api/v1/insights/cross-veda",
            caveats=[
                _frozen_caveat("entity_vocabulary_overlap_candidates"),
                _frozen_caveat("cross_veda_relatedness_method_census"),
            ],
        )

    def _q28_rival_readings(self) -> CapabilityLimit:
        rows = self._repository.run_named("competing_interpretations")
        recorded = sum(1 for row in rows if _as_str(row.get("claim_a")))
        return CapabilityLimit(
            limit_id="rival_scholarly_readings",
            question_number=28,
            question="Where does the graph record scholarly disagreement about the Vedas?",
            verdict=CapabilityVerdict.NOT_ANSWERABLE,
            data_status=KnowledgeStatus.INSUFFICIENT_EVIDENCE,
            why=(
                "The graph records no pair of rival scholarly readings of the Vedic text. It "
                "holds a small number of interpretive claims, only some of which are about "
                "the text at all, and no two of those contradict each other. The one "
                "contradiction it does record is cross-category -- an interpretation of a "
                "tradition against a measurement of this dataset -- and those two are in "
                "dialogue rather than in conflict."
            ),
            what_this_is_not=(
                "This is NOT a claim that the Vedas are uncontroversial. No attributed "
                "commentarial position is held by this product at all, so the absence is an "
                "absence of sources."
            ),
            measurements=[
                CapabilityMeasurement(
                    name="recorded_contradiction_pairs",
                    value=recorded,
                    means="Pairs the graph marks as contradicting. Read each pair's "
                    "disagreement_kind: a cross-category pair is not scholarly dissent.",
                ),
            ],
            safe_alternative=(
                "The recorded contradictions with their kind stated per row, alongside the "
                "explicit statement that none of them is a rival reading of the text."
            ),
            what_would_change_it=(
                "Attributed commentarial positions ingested as claims with a named asserter."
            ),
            endpoint="/api/v1/insights/civilization",
            caveats=[_frozen_caveat("competing_interpretations")],
        )

    def _q52_assertions_outside_the_rigveda(self) -> CapabilityLimit:
        rows = self._repository.run(_ASSERTION_REACH_QUERY)
        vedas = sorted({_as_str(row.get("veda")) or "" for row in rows} - {""})
        total = sum(_as_int(row.get("assertions")) or 0 for row in rows)
        return CapabilityLimit(
            limit_id="semantic_roles_outside_the_rigveda",
            question_number=52,
            question="What semantic roles does each corpus assign, and how do they differ?",
            verdict=CapabilityVerdict.NOT_ANSWERABLE,
            data_status=KnowledgeStatus.NOT_BUILT,
            why=(
                f"The semantic-assertion layer reaches {', '.join(vedas) or 'no corpus'} and "
                f"nothing else: all {total:,} of its assertions sit in one corpus, because it "
                "derives from a manual morphological annotation that exists for that corpus "
                "alone. There is no non-Rigvedic row to compare, and no divergence statistic "
                "anywhere in the graph."
            ),
            what_this_is_not=(
                "A zero for the other three corpora is an absent annotation layer and not an "
                "absence of semantic structure in those texts. The layer must also never be "
                "aggregated across its two derivations, which differ in strength and in reach."
            ),
            measurements=[
                CapabilityMeasurement(
                    name="assertions",
                    value=total,
                    means=f"All of them in {', '.join(vedas) or 'no corpus'}. The predicates "
                    "derived from this layer inherit its scope, so they are single-corpus too.",
                ),
            ],
            safe_alternative=(
                "The deity mention layer, which reaches all four corpora, though by two "
                "different instruments that must not be averaged."
            ),
            what_would_change_it=(
                "A morphological annotation for the other three corpora, plus a divergence "
                "measure with a stated significance test."
            ),
            endpoint="/api/v1/insights/cross-veda",
            caveats=[
                CaveatView(text=_ASSERTION_LAYER_CAVEAT, source="assertion_layer_scope"),
                CaveatView(text=_MENTION_LAYER_CAVEAT, source="mention_layer_scope"),
            ],
        )

    def _q77_calibrated_confidence(self) -> CapabilityLimit:
        row = self._repository.run_one(
            "MATCH (s:SemanticAssertion) WHERE s.human_gold_status = 'ANNOTATED' "
            "RETURN count(s) AS annotated"
        )
        annotated = _as_int(row.get("annotated")) if row else None
        return CapabilityLimit(
            limit_id="calibrated_confidence",
            question_number=77,
            question="How reliable are the graph's assertions, measured against a gold set?",
            verdict=CapabilityVerdict.NOT_ANSWERABLE,
            data_status=KnowledgeStatus.NOT_BUILT,
            why=(
                "There is no human-annotated evaluation set, so there is no reliability curve "
                "and no calibration. The confidence values several predicates carry are "
                "pipeline priors and not calibrated probabilities -- for a number of "
                "predicates the value is a single constant on every edge -- so a threshold on "
                "them selects nothing. The strongest review this graph holds is a per-passage "
                "re-read by a model; nothing anywhere is human-reviewed."
            ),
            what_this_is_not=(
                "A confidence of 0.9 here is not a 90% chance of being right. It is a "
                "provenance marker. Treating it as a probability, or filtering on it, produces "
                "a selection that looks principled and is not."
            ),
            measurements=[
                CapabilityMeasurement(
                    name="human_annotated_assertions",
                    value=annotated,
                    means="The size of the gold set. This zero is why no reliability figure "
                    "is published anywhere in this API.",
                ),
            ],
            safe_alternative=(
                "The quality tier and evidence basis on each edge, which record how an "
                "assertion was arrived at rather than how likely it is to be true."
            ),
            what_would_change_it=(
                "A human-annotated sample per predicate, and a calibration measured against it."
            ),
            endpoint="/api/v1/insights/civilization",
            caveats=[CaveatView(text=_ADJUDICATION_CAVEAT, source="adjudication_layer_scope")],
        )

    def _q82_samavedic_melody(self) -> CapabilityLimit:
        scopes = self.work_scopes()
        sv = scopes.get("SV")
        excluded = sv.excluded_corpora if sv else []
        return CapabilityLimit(
            limit_id="samavedic_melodic_layer",
            question_number=82,
            question="What does the Samaveda's musical dimension contain?",
            verdict=CapabilityVerdict.NOT_ANSWERABLE,
            data_status=KnowledgeStatus.NOT_BUILT,
            why=(
                "The Samavedic corpus held here is the Kauthuma arcika verse text and nothing "
                "else. The gana collections -- the sung realisation that is the reason the "
                "Samaveda is a distinct Veda rather than a Rigvedic excerpt -- are excluded by "
                f"the work's own declaration ({', '.join(excluded) or 'no exclusions recorded'}) "
                "and require their own work identifier. No melodic layer of any kind exists in "
                "this graph."
            ),
            what_this_is_not=(
                "This is NOT a statement that the Samaveda lacks a musical dimension, and no "
                "Samavedic figure anywhere in this API may be read as covering the Samaveda. "
                "The work node's own scope sentence begins by saying so in capitals."
            ),
            measurements=[
                CapabilityMeasurement(
                    name="excluded_samavedic_corpora",
                    value=len(excluded),
                    means="Bodies the Samavedic work declares it does not hold. Every one of "
                    "them is part of what a reader means by 'the Samaveda'.",
                ),
            ],
            safe_alternative=(
                "The arcika verse text itself, and the measured Rigvedic reuse within it, "
                "both of which are real and both of which are about the verse and not the song."
            ),
            what_would_change_it=(
                "Ingesting a gana corpus under its own work identifier, with the melodic "
                "assignment linked to the verses it realises."
            ),
            endpoint="/api/v1/insights/formula-diffusion",
            caveats=[
                _measured_caveat(
                    "Samavedic scope, in the graph's own words: "
                    + (sv.scope if sv and sv.scope else "not recorded")
                )
            ],
        )

    # -- /insights/devatas/{id} -------------------------------------------

    def devata_insight(
        self, *, devata_id: str, tiers: Sequence[str], population: DeityPopulation
    ) -> DevataInsightResponse:
        """One deity's naming reach and ascription total, never added together.

        Both figures are real and they measure different things over different corpora. A
        blended "passages about this deity" would add a statement the verse makes to a
        dedication the traditional apparatus makes about a whole hymn, and would do it only
        for the one corpus that has the apparatus.

        **The population gate runs first, and it is not this module's gate.**
        :meth:`EntityService._resolve_devata` is THE gate for every deity surface, and this
        route calls it rather than checking ``is_deity`` itself. That is the whole lesson of
        the finding it closes: this endpoint had the machine-readable half right --
        ``is_resolved_deity: false`` and ``structure`` on the row -- and still served the dog
        at 200 with no disclosure, under a question calling it a deity, while
        ``/devatas/VG:DEVATA:SUNAH`` 404'd for the same id in the same API. A second
        implementation of a contract is how the first one gets forgotten one route over, so
        there is no second implementation: the gate decides, and
        :func:`subject_disclosure` produces the flag and the caveat in one call so neither
        can ship without the other.
        """
        # Imported here rather than at module scope: the two services are peers, and a
        # top-level import between them would make either one unimportable if the other
        # ever grew an import-time failure.
        from vedagraph.api.services.entity_service import EntityService, subject_disclosure

        structure = EntityService(self._repository)._resolve_devata(devata_id, population)
        is_resolved_deity, disclosure = subject_disclosure(structure)

        row = self._repository.run_one(_DEVATA_INSIGHT_QUERY, key=devata_id, tiers=list(tiers))
        if row is None:  # pragma: no cover - the gate above already resolved the node
            raise EntityNotFoundError(
                f"No deity or devata ascription with id {devata_id!r}.",
                hint="GET /api/v1/devatas lists the resolved deity population.",
            )
        named = _pairs_to_counts(row.get("named_by_veda"))
        certainty_split = _pairs_to_counts(row.get("certainty_split"))
        surfaces = sorted(set(_as_str_list(row.get("surface_groups"))))
        precisions = sorted(set(_as_str_list(row.get("precision_groups"))))
        ascribed = _as_int(row.get("ascribed"))
        ascribed_vedas = _as_str_list(row.get("ascribed_vedas"))
        named_total = sum(named.values()) or None

        certainty = ReferentCertaintyCounts(
            certain_count=certainty_split.get("DEITY_CERTAIN", 0),
            probable_count=certainty_split.get("DEITY_PROBABLE", 0),
            ambiguous_count=certainty_split.get("DEITY_AMBIGUOUS", 0),
            included_tiers=sorted(tiers),
        )
        claims = [
            self._claim_row(row)
            for row in self._repository.run(_CLAIMS_ABOUT_DEVATA_QUERY, key=devata_id)
        ]
        metrics = [
            self._metric_row(metric)
            for metric in (row.get("metrics") or [])
            if isinstance(metric, dict)
        ]
        return DevataInsightResponse(
            insight="devata_reach",
            # The question names what the subject actually is. Calling a danastuti label or
            # a dog "this deity" in the question string is the same error as omitting the
            # disclosure, one field along.
            question=(
                "How far does this deity reach, by naming and by ascription?"
                if is_resolved_deity
                else "How far does this devata-slot subject -- which is NOT a deity -- "
                "reach, by naming and by ascription?"
            ),
            data_status=KnowledgeStatus.PARTIAL,
            cost_class=CostClass.POINT_READ,
            cost_note="Indexed lookups on one deity plus its stored statistics.",
            vedas_reported=list(VEDA_ORDER),
            scope_statements=self._scope_statements(VEDA_ORDER),
            coverage=CoverageView(
                vedas_in_scope=list(VEDA_ORDER),
                vedas_not_covered=[veda for veda in VEDA_ORDER if veda not in ascribed_vedas],
                measured=named,
                denominator=dict(figures.CORPUS_MANTRAS),
            ),
            # The disclosure goes first. A client that renders one caveat renders the one
            # saying this subject is not a god.
            caveats=[
                *disclosure,
                CaveatView(text=_MENTION_LAYER_CAVEAT, source="mention_layer_scope"),
                CaveatView(text=_SCOPE_CAVEAT, source="has_devata_layer_scope"),
                _frozen_caveat("deity_reach_named_versus_ascribed"),
                _measured_caveat(
                    "named and ascribed are not summable and not comparable without their "
                    f"scopes: named spans {', '.join(VEDA_ORDER)} and ascribed reaches "
                    f"{', '.join(ascribed_vedas) or 'no corpus'}. Compare corpora on the "
                    "per-1,000 figures rather than on raw counts."
                ),
            ],
            devata_id=_as_str(row.get("entity_key")) or devata_id,
            display_label=_as_str(row.get("display_label")) or devata_id,
            structure=structure,
            is_resolved_deity=is_resolved_deity,
            named_by_veda=VedaCountRow(
                label=_as_str(row.get("display_label")) or devata_id,
                kind="DEVATA",
                entity_key=_as_str(row.get("entity_key")),
                total_mantras=named_total,
                by_veda=_counted_by_veda(
                    named,
                    status=(
                        KnowledgeStatus.SUPPORTED
                        if len(named) == len(VEDA_ORDER)
                        else KnowledgeStatus.PARTIAL
                    ),
                    note="Passages naming this deity, at the requested certainty tiers. A "
                    "corpus with no figure had no mention edge at those tiers; the layer "
                    "itself reaches all four, so this is not an absent layer.",
                ),
                per_1000_by_veda=_per_1000(named),
                vedas_reached=len(named) or None,
                evidence_status="MENTION_LAYER_TWO_INSTRUMENTS",
            ),
            named_total=named_total,
            certainty=certainty,
            ascribed_total=ascribed,
            ascribed_scope=ascribed_vedas,
            ascription_note=(
                "Ascription is the traditional apparatus dedicating a hymn, and it exists for "
                f"{', '.join(ascribed_vedas) or 'no corpus in this graph'}. A zero elsewhere "
                "is a missing apparatus rather than an absent deity, and most ascriptions are "
                "a hymn label projected onto each verse inside it rather than a per-verse "
                "statement."
            ),
            mention_surplus=(
                (named_total or 0) - ascribed if ascribed is not None and named_total else None
            ),
            derived_metrics=metrics,
            interpretive_claims=claims,
            # Describes the naming figure only, and deliberately not the ascription one:
            # naming is a textual mention and ascription is an attribution, so one evidence
            # block over both would have to pick a basis and would be wrong about the other.
            # The ascription side carries its own account in `ascription_note`.
            #
            # Both fields are read off the edges rather than asserted. `evidence_basis` is
            # DERIVED from attribution_precision and `surface` is the graph's own
            # evidence_basis property, which is a different axis with a disjoint value space
            # -- casting one to the other reported every attribution edge in the corpus as
            # UNKNOWN once already. A surface is reported only where the edges agree on one;
            # naming several and picking the first would be a guess wearing a field name.
            evidence=EvidenceView(
                method="The verse's own text names the deity (mention layer).",
                tier="TIER_B",
                evidence_basis=basis_from_attribution_precision(
                    precisions[0] if len(precisions) == 1 else None
                ),
                surface=(
                    evidence_surface(surfaces[0]) if len(surfaces) == 1 else EvidenceSurface.MIXED
                ),
                attribution_precision=(
                    AttributionPrecision(precisions[0])
                    if len(precisions) == 1 and precisions[0] in set(AttributionPrecision)
                    else AttributionPrecision.UNKNOWN
                ),
                review_state=None,
                confidence=None,
            ),
        )
