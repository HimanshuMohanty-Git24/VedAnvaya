"""Corpus browsing: one navigator for four Vedas, and the queries behind it.

**Why one navigator and not four.** The four corpora nest differently -- Mandala/Sukta/
Mantra, Kanda/Sukta/Mantra, Adhyaya/Mantra, and a Samavedic Collection/Prapathaka/Ardha/
Dasati/Verse that varies in depth between its own four collections -- and the obvious
implementation is a branch per Veda. That is four places for a bug and four places to
forget the Samaveda. Everything here instead runs off two facts that are uniform across
the corpus: ``parent_key``/``CONTAINS`` gives the tree, and the keys of the ``hierarchy``
property name the levels. :data:`NATIVE_LEVEL_LABELS` maps those keys to the tradition's
names and :data:`LEVEL_ORDER` puts them in order, and that pair is the whole of the
per-Veda knowledge in this module.

**Why the level names cannot be read off the node.** ``native_labels`` looks like exactly
the property this needs, and for the Atharvaveda, Yajurveda and Samaveda it is. It is
``'[]'`` on all 11,590 Rigvedic passages. A navigator that trusted it would present the
Rigveda -- the corpus most users arrive for -- as having no structural vocabulary at all,
so the labels are derived and the property is used only to *check* the derivation in
``tests/api/test_passages.py``, over all 10,947 passages that carry it.

**Why the order cannot come from the property either.** ``hierarchy`` is a JSON string
whose keys are stored alphabetically: RV 1.1.1 reads ``{"mandala":1,"mantra":1,"sukta":1}``,
which puts the verse number in the middle. Iterating the parsed map yields
Mandala/Mantra/Sukta. :data:`LEVEL_ORDER` is a single total order over all ten level names
in the corpus, and every Veda's levels are a subsequence of it, so one sort answers all
four.

**Why reading order is not key order.** Lexicographic ``canonical_key`` order agrees with
``sequence_in_parent`` in every one of the graph's sibling groups -- checked, with zero
disagreements -- because every ordinal in a key is zero-padded. It disagrees across the
Samaveda's four top-level collections, which are stored in the traditional order CHANDA,
ARANYAKA, MAHANAMNYA, UTTARA and sort alphabetically as ARANYA, CHANDA, MAHANAMNYA,
UTTARA. A "next verse" built on key order alone therefore steps from the last CHANDA verse
straight to MAHANAMNYA and silently skips all 55 Aranyaka verses. So
:data:`_NEIGHBOURS` ranks a within-collection candidate above a next-collection one and
takes the next collection from the stored root sequence.

**Why parallels are traversed undirected.** All 1,684 ``REUSES_TEXT_FROM`` edges point
Samaveda-to-Rigveda, and 1,421 Rigvedic passages have reuse edges only inbound. Following
the arrow shows those 1,421 verses no reuse whatsoever while returning HTTP 200.

**A note on ``:Internal``.** ``TextVersion``, ``Translation`` and ``Lemma`` all carry the
``:Internal`` marker label, so the obvious "exclude internal nodes" filter would delete the
text this module exists to return. Text and translations are therefore reached by
relationship type, and ``:Internal`` is used only where it means what it looks like it
means: excluding a passage's own text nodes from its *graph neighbour* count.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Final, Protocol

from vedagraph.api.config import MAX_PAGE_SIZE
from vedagraph.api.errors import (
    BadRequestError,
    PassageNotFoundError,
    WorkNotFoundError,
)
from vedagraph.api.models.common import (
    AttributionPrecision,
    CaveatView,
    CoverageView,
    EvidenceBasis,
    EvidenceSpanView,
    EvidenceView,
    KnowledgeStatus,
    Paginated,
    PaginationMeta,
    ReferentCertaintyCounts,
    basis_from_attribution_precision,
    evidence_surface,
    paginate,
)
from vedagraph.api.models.entity import (
    AttributedRef,
    EntityRef,
    MentionCertainty,
    parse_json_property,
)
from vedagraph.api.models.insight import offset_overrun_caveat
from vedagraph.api.models.passage import (
    AgentiveAssertionView,
    AssertionModality,
    AttestedSet,
    AudioAvailability,
    BreadcrumbView,
    MentionedDevataSet,
    MentionedDevataView,
    NavigationRelation,
    NavigationResult,
    ParallelCounts,
    ParallelFilter,
    ParallelKind,
    ParallelMetrics,
    ParallelView,
    PassageDetail,
    PassageProvenance,
    PassageSummary,
    ReaderPayload,
    SemanticRelationView,
    StoredDirection,
    TextAvailability,
    TextScript,
    TextSurfaceView,
    TranslationView,
)
from vedagraph.api.models.work import (
    AttributionSplit,
    HierarchyLevel,
    LayerAvailability,
    TranslationCoverage,
    WorkDetail,
    WorkRoot,
    WorkSummary,
)
from vedagraph.api.repositories.neo4j_repository import named_query_caveat
from vedagraph.domain import layer_figures, theonyms


class Repository(Protocol):
    """The read surface this service needs. Narrower than ``Neo4jRepository`` so the
    offline tests can substitute a script without importing the driver."""

    def run(self, cypher: str, /, **parameters: Any) -> list[dict[str, Any]]: ...

    def run_one(self, cypher: str, /, **parameters: Any) -> dict[str, Any] | None: ...


# ---------------------------------------------------------------------------
# The one piece of per-Veda knowledge in this module
# ---------------------------------------------------------------------------

#: Hierarchy key to the tradition's name for that level. Ten keys cover all four corpora.
#: An eleventh appearing in a rebuild raises :class:`UnknownHierarchyLevel` rather than
#: being dropped, and ``test_every_hierarchy_key_is_known`` asserts the graph's key set
#: against this map so the failure lands in a test run and not in a payload.
NATIVE_LEVEL_LABELS: Final[dict[str, str]] = {
    "collection": "Collection",
    "mandala": "Mandala",
    "kanda": "Kanda",
    "adhyaya": "Adhyaya",
    "prapathaka": "Prapathaka",
    "ardha": "Ardha",
    "sukta": "Sukta",
    "dasati": "Dasati",
    "mantra": "Mantra",
    "verse": "Verse",
}

#: One total order over every level name in the corpus, outermost first. Each Veda's own
#: levels are a subsequence of it: RV mandala<sukta<mantra, AV kanda<sukta<mantra, YV
#: adhyaya<mantra, SV collection<prapathaka<ardha<dasati<verse. Because a single order
#: satisfies all four, sorting by it is the whole of the ordering logic and there is no
#: per-Veda branch to get wrong.
LEVEL_ORDER: Final[tuple[str, ...]] = (
    "collection",
    "mandala",
    "kanda",
    "adhyaya",
    "prapathaka",
    "ardha",
    "sukta",
    "dasati",
    "mantra",
    "verse",
)

#: Levels whose values are names rather than ordinals. Only the Samavedic ``collection``,
#: whose four values are ARANYA, CHANDA, MAHANAMNYA and UTTARA. Declared because a client
#: that assumed integers throughout would fail on 1,844 verses and 498 containers.
NAME_VALUED_LEVELS: Final[frozenset[str]] = frozenset({"collection"})

_LEVEL_RANK: Final[dict[str, int]] = {key: index for index, key in enumerate(LEVEL_ORDER)}


class UnknownHierarchyLevel(ValueError):
    """A hierarchy key that is not in :data:`NATIVE_LEVEL_LABELS`.

    Raised rather than defaulted. A level this API cannot name is a level it cannot
    order either, and quietly dropping it would shorten a breadcrumb trail without
    changing anything a client could notice.
    """


def native_level_label(level_key: str) -> str:
    """The tradition's name for a hierarchy key, or raise."""
    try:
        return NATIVE_LEVEL_LABELS[level_key]
    except KeyError:
        raise UnknownHierarchyLevel(level_key) from None


def order_levels(level_keys: object) -> list[str]:
    """Hierarchy keys sorted outermost-first, unknown keys last and still present.

    Unknown keys are kept so the caller can report them; :func:`native_level_label` is
    what refuses to name one. Sorting them to the end keeps the known prefix of a
    breadcrumb trail correct even when the graph has grown a level this map has not.
    """
    keys = [str(key) for key in level_keys] if isinstance(level_keys, (list, tuple, set)) else []
    return sorted(keys, key=lambda key: (_LEVEL_RANK.get(key, len(LEVEL_ORDER)), key))


# ---------------------------------------------------------------------------
# Product vocabulary for graph values
# ---------------------------------------------------------------------------

#: ``text_role`` to a product surface name. ``NORMALIZED_FOR_SEARCH`` and
#: ``EXTRACTED_FROM_CONTAINER`` are kept distinct from ``PRIMARY`` on purpose: the first is
#: an accent-stripped matching form that must not be rendered as the text, and the second
#: records that 1,975 Yajurvedic verses were cut out of a printed block rather than
#: transcribed as verses.
_TEXT_SURFACE_BY_ROLE: Final[dict[str, str]] = {
    "PRIMARY_TEXT": "PRIMARY",
    "PARALLEL_TEXT": "PARALLEL_WITNESS",
    "SEARCH_DERIVATIVE": "NORMALIZED_FOR_SEARCH",
    "EXTRACTED_FROM_CONTAINER": "EXTRACTED_FROM_CONTAINER",
}

#: Surfaces a reader may be shown. A search derivative is real data and not the text.
_DISPLAYABLE_SURFACES: Final[frozenset[str]] = frozenset(
    {"PRIMARY", "PARALLEL_WITNESS", "EXTRACTED_FROM_CONTAINER"}
)

#: Preference order when choosing the single witness a reader view renders.
_SURFACE_PREFERENCE: Final[tuple[str, ...]] = (
    "PRIMARY",
    "EXTRACTED_FROM_CONTAINER",
    "PARALLEL_WITNESS",
)

_SCRIPT_BY_GRAPH_VALUE: Final[dict[str, TextScript]] = {
    "Devanagari": TextScript.DEVANAGARI,
    "Latin": TextScript.IAST,
}

#: The four textual parallel predicates and the entity-overlap one, with the kind of claim
#: each makes. ``SHARES_ENTITY_VOCABULARY_WITH`` is in the same map so it can be requested
#: through the same endpoint, and carries a kind that keeps it out of any reuse total.
_PARALLEL_PREDICATES: Final[dict[str, tuple[str, ParallelKind]]] = {
    "EXACT_PARALLEL_OF": ("EXACT_PARALLEL", ParallelKind.TEXTUAL_PARALLEL),
    "NEAR_PARALLEL_OF": ("NEAR_PARALLEL", ParallelKind.TEXTUAL_PARALLEL),
    "PARALLEL_TO": ("PARALLEL", ParallelKind.TEXTUAL_PARALLEL),
    "REUSES_TEXT_FROM": ("TEXT_REUSE", ParallelKind.TEXT_REUSE),
    "VARIANT_OF": ("TEXTUAL_VARIANT", ParallelKind.TEXTUAL_VARIANT),
    "SHARES_ENTITY_VOCABULARY_WITH": (
        "ENTITY_VOCABULARY_OVERLAP",
        ParallelKind.ENTITY_VOCABULARY_OVERLAP,
    ),
}

#: Which stored predicates each client filter selects. ``FORMULA`` maps to nothing here
#: because it is not an edge between passages at all -- see :meth:`PassageService.parallels`.
_FILTER_PREDICATES: Final[dict[ParallelFilter, tuple[str, ...]]] = {
    ParallelFilter.EXACT: ("EXACT_PARALLEL_OF", "PARALLEL_TO"),
    ParallelFilter.NEAR: ("NEAR_PARALLEL_OF",),
    ParallelFilter.REUSE: ("REUSES_TEXT_FROM",),
    ParallelFilter.VARIANT: ("VARIANT_OF",),
    ParallelFilter.VOCABULARY: ("SHARES_ENTITY_VOCABULARY_WITH",),
    ParallelFilter.FORMULA: (),
    ParallelFilter.SAME_VEDA: tuple(_PARALLEL_PREDICATES),
    ParallelFilter.CROSS_VEDA: tuple(_PARALLEL_PREDICATES),
}

#: Interpretive predicates returned through the one generic shape. A predicate added to the
#: graph later and absent from this whitelist is not returned, which is the conservative
#: direction: a named relation is better than an unnamed one on a knowledge surface.
_SEMANTIC_RELATIONS: Final[tuple[str, ...]] = (
    "TREATS",
    "PROTECTS_FROM",
    "ADDRESSES_CONCERN",
    "USED_FOR_RITE",
    "INVOKES",
    "PRAISES",
    "DESCRIBES",
    "DESCRIBES_ACTION",
    "REQUESTS",
    "INVOLVES_OFFERING",
    "INVOLVES_RITUAL",
    "INVOLVES_SUBSTANCE",
    "CONTRASTS_WITH",
    "HAS_THEME",
    "REFERS_TO_NATURAL_PHENOMENON",
    "REFERS_TO_PLACE",
)


@dataclass(frozen=True)
class LayerSpec:
    """One knowledge layer, its predicate, and what a zero for a corpus would mean."""

    layer: str
    relation: str
    absence_note: str


#: The layers whose per-corpus reach the works endpoint measures. The reach is not
#: guessable from the layer's purpose -- deity ascription is Rigveda-only while its
#: *descriptor* layer is Atharvaveda-only, and the agentive assertion layer reaches only the
#: Rigveda while the review layer that grades assertions reaches only the other two -- so
#: every row here is a count and none is an assertion.
_LAYER_SPECS: Final[tuple[LayerSpec, ...]] = (
    LayerSpec(
        "DEVATA_ASCRIPTION",
        "HAS_DEVATA",
        "The Anukramani ascribes a deity per hymn and that apparatus exists for the "
        "Rigveda only. A zero elsewhere means no ascription layer, not a godless verse; "
        "ask the DEVATA_MENTION layer instead, which reaches all four corpora.",
    ),
    LayerSpec(
        "DEVATA_MENTION",
        "MENTIONS_DEVATA",
        "Reaches all four corpora, but by two instruments: the Rigveda's edges come from "
        "a manual scholarly lemma annotation and the rest from surface matching.",
    ),
    LayerSpec(
        "RISHI_ATTRIBUTION",
        "HAS_RISHI",
        "Three corpora, by two incompatible instruments, and the Samaveda has none. Read "
        "the attribution split before comparing two works on this figure.",
    ),
    LayerSpec(
        "CHANDAS_ATTRIBUTION",
        "HAS_CHANDAS",
        "Rigveda and Atharvaveda only, and their metre vocabularies are disjoint sets, so "
        "the two counts are not comparable as prosodic variety.",
    ),
    LayerSpec(
        "DEVATA_ASCRIPTION_DESCRIPTOR",
        "HAS_DEVATA_ASCRIPTION",
        "Atharvaveda only. This is the descriptor layer for Atharvavedic deity ascription "
        "and it runs opposite to DEVATA_ASCRIPTION, which is Rigvedic.",
    ),
    LayerSpec(
        "AGENTIVE_ASSERTION",
        "HAS_SEMANTIC_ASSERTION",
        "Rigveda only. Who does what to whom is derived from the Rigveda-only lemma "
        "annotation, so the other three corpora are absent from it entirely.",
    ),
    LayerSpec(
        "CONCEPT_ASSERTION",
        "ABOUT_CONCEPT",
        "Reaches all four corpora, partly through the English translation, so its reach "
        "into the Samaveda is bounded by that corpus having no translation at all.",
    ),
    LayerSpec(
        "ENTITY_MENTION",
        "MENTIONS_ENTITY",
        "Reaches all four corpora by Sanskrit surface matching against a fixed registry, "
        "so it finds only entities the registry names.",
    ),
    LayerSpec(
        "FORMULA_OCCURRENCE",
        "USES_FORMULA",
        "Reaches all four corpora. Formula identity is a normalised-string match and not a "
        "tradition of reuse.",
    ),
    LayerSpec(
        "TRANSLATION",
        "HAS_TRANSLATION",
        "Three corpora. The Samaveda has zero released translations, so every "
        "translation-derived layer is empty for it and none of those zeros is textual.",
    ),
)

#: Layers whose edges carry ``attribution_precision``, where source-stated and inherited
#: must be reported apart. See :class:`AttributionSplit`.
_SPLIT_RELATIONS: Final[tuple[str, ...]] = ("HAS_RISHI", "HAS_CHANDAS", "HAS_DEVATA")

_INHERITANCE_NOTE: Final = (
    "PER_PASSAGE is an attribution the source states verse by verse; CONTAINER_INHERITED "
    "is a containing hymn's label projected onto each of its mantras. The two must not be "
    "summed: 15,177 of the 17,889 seer edges are inherited, every one of the "
    "Atharvaveda's 5,084 is, and every one of the Yajurveda's 2,240 is source-stated, so a "
    "blended total compares a statement of the text against a projection of this build."
)

#: Why an assertion can have no modality, with the two stratum sizes interpolated from
#: :data:`vedagraph.domain.layer_figures.ASSERTION_LAYERS` rather than typed here. The
#: figures are the frozen measured ones, so this sentence cannot drift from the split it
#: describes -- and the split is exact: every assertion carrying a ``frame`` is
#: deterministic and every one lacking it is model-extracted, 2,459 for 2,459.
_MODALITY_ABSENT_NOTE: Final = (
    "The agentive layer is two strata that do not share a vocabulary. The "
    f"{layer_figures.ASSERTION_LAYERS['MORPHOLOGY_RULE']:,} deterministic assertions carry "
    "a frame (ASSERTED or REQUESTED) derived from Vedic morphology; the "
    f"{layer_figures.ASSERTION_LAYERS['MODEL_EXTRACTION']:,} model-extracted ones carry no "
    "frame at all, and express what a frame would through `semantic_predicate` "
    "(DESCRIBES, REQUESTS, INVOKES) and `object_kind` instead. A null modality here is a "
    "row from a stratum that has no modality axis, NOT a verse whose modality is unknown "
    "and NOT a verse that asserts nothing. Model-extracted rows are also state=CANDIDATE: "
    "unreviewed extractions rather than settled readings."
)

#: Why an ambiguous mention is withheld, with every figure interpolated from
#: :data:`vedagraph.domain.layer_figures.REFERENT_CERTAINTY` rather than typed. The share is
#: divided here from the same three counts the response carries, so the sentence cannot
#: drift from the data the way three V3.1 caveats did.
_MENTION_TIER_TOTAL: Final = sum(layer_figures.REFERENT_CERTAINTY.values())
_AMBIGUOUS_SHARE: Final = (
    100 * layer_figures.REFERENT_CERTAINTY["DEITY_AMBIGUOUS"] / _MENTION_TIER_TOTAL
)

_AMBIGUITY_CONTRACT_CAVEAT: Final = (
    "Vedic Sanskrit uses one word for a god and for the thing it is: `soma` is the deity, "
    "the plant and the pressed drink, `agni` is the deity and it is fire. Every one of the "
    f"{_MENTION_TIER_TOTAL:,} mention edges is graded, and "
    f"{layer_figures.REFERENT_CERTAINTY['DEITY_AMBIGUOUS']:,} of them "
    f"({_AMBIGUOUS_SHARE:.1f}%) "
    "come out DEITY_AMBIGUOUS, meaning the grader could not tell the deity from the "
    "ordinary noun. This response counts DEITY_CERTAIN "
    f"({layer_figures.REFERENT_CERTAINTY['DEITY_CERTAIN']:,}) and DEITY_PROBABLE "
    f"({layer_figures.REFERENT_CERTAINTY['DEITY_PROBABLE']:,}) and withholds the "
    "ambiguous ones; ask with include_ambiguous=true to see them, graded. All three counts "
    "are in `certainty` either way."
)

#: For the 2,997 passages whose *every* mention is ambiguous. Their filtered list is empty
#: and that emptiness is the opposite of "no deity is named here" -- a deity was matched and
#: the matcher will not vouch for it, which is INSUFFICIENT_EVIDENCE and never a zero.
_ALL_MENTIONS_AMBIGUOUS_CAVEAT: Final = (
    "Every deity name matched in this passage is graded DEITY_AMBIGUOUS, so none is "
    "reported by default and this empty list is NOT a statement that the verse names no "
    "deity. It names at least one form that is also an ordinary noun, and the grader could "
    "not decide which is meant. 2,997 of the corpus's passages are in this position. Ask "
    "with include_ambiguous=true to see the candidates with their grades."
)

#: The mention layer reaches all four corpora, so no match is not an unbuilt layer.
_NO_MENTION_MATCHED_CAVEAT: Final = (
    "No deity name was matched in this passage. The mention layer reaches all four corpora "
    f"({layer_figures.PREDICATE_TOTALS['MENTIONS_DEVATA']:,} edges: "
    f"{layer_figures.veda_breakdown(layer_figures.MENTIONS_DEVATA_BY_VEDA)}), so this is a "
    "limit of surface matching against a fixed theonym registry and not an unbuilt layer -- "
    "a deity referred to by an epithet this registry does not list would not appear here."
)

_SCRIPT_DISJOINT_CAVEAT: Final = (
    "No passage in this corpus carries both scripts: 16,391 Rigvedic and Atharvavedic "
    "mantras are held in romanised transliteration only and 3,819 Samavedic and Yajurvedic "
    "ones in Devanagari only. A missing script is a property of what was ingested for that "
    "corpus and not of the text, which is why it is reported as NOT_BUILT and not as null."
)

_UNDIRECTED_CAVEAT: Final = (
    "Parallelism is symmetric and this graph stores it as a directed edge, so these "
    "relations are traversed in both directions and each row states which way the stored "
    "edge ran. All 1,684 REUSES_TEXT_FROM edges point Samaveda-to-Rigveda, and 1,421 "
    "Rigvedic passages have reuse edges only inbound; following the arrow would show those "
    "1,421 verses no reuse at all."
)

_VOCABULARY_CAVEAT: Final = (
    "SHARES_ENTITY_VOCABULARY_WITH is not textual parallelism. It means two passages name "
    "some of the same registry concepts and says nothing about shared wording, so it is "
    "reported with relation_kind=ENTITY_VOCABULARY_OVERLAP and is excluded from "
    "textual_total."
)

_FORMULA_MEDIATED_CAVEAT: Final = (
    "filter=formula is formula-mediated and not a stored passage-to-passage edge: these "
    "passages use the same Formula, reached through USES_FORMULA. Formula identity is a "
    "normalised-string match over the corpus, so a shared formula is shared wording and "
    "not a claim that either passage reuses the other."
)

_CONTAINER_HAS_NO_TEXT_CAVEAT: Final = (
    "This passage is a structural container and carries no text of its own: the corpus "
    "attaches text to its 20,210 mantras and not to the 2,327 containers above them. Ask "
    "for its children to reach the text."
)

_CITATION_SEPARATORS: Final = re.compile(r"[\s._\-]+")

#: Corpus tokens a client may use in a citation, mapped to the form the graph stores.
#: ``AV`` and ``YV`` are the Veda codes a reader knows; ``AVS`` and ``VSM`` are the
#: abbreviations the citations were built from, and both must resolve.
_CITATION_PREFIXES: Final[dict[str, str]] = {
    "RV": "RV",
    "AV": "AVS",
    "AVS": "AVS",
    "YV": "VSM",
    "VS": "VSM",
    "VSM": "VSM",
    "SV": "SV",
}

#: Shown in a 404 so the client sees a form that works rather than only that theirs did not.
_KEY_HINT: Final = (
    "Use a canonical key such as VG:RV:SAK:M01:S001:V001, a citation such as 'RV 1.1.1' "
    "(RV.1.1.1 and rv_1.1.1 also resolve), or a URN such as "
    "urn:vedagraph:mantra:rigveda:shakala:mandala:1:sukta:1:mantra:1."
)


def _summary_projection(variable: str) -> str:
    """A Cypher map projection for :class:`PassageSummary`, over a query-author's alias.

    ``variable`` is always a literal written in this module -- never a client value -- and
    exists so that eleven queries return one shape. Two queries that projected a passage
    separately would be two places for a field to go missing.
    """
    return (
        "{"
        f"canonical_key: {variable}.canonical_key, "
        f"canonical_citation: {variable}.canonical_citation, "
        f"canonical_urn: {variable}.canonical_urn, "
        f"entity_id: {variable}.entity_id, "
        f"veda: {variable}.veda, "
        f"work_id: {variable}.work_id, "
        f"display_type: {variable}.display_type, "
        f"display_label: {variable}.display_label, "
        f"hierarchy: {variable}.hierarchy, "
        f"parent_key: {variable}.parent_key, "
        f"sequence_in_parent: {variable}.sequence_in_parent"
        "}"
    )


_P = _summary_projection("p")
_OTHER = _summary_projection("other")
_CHILD = _summary_projection("child")
_ANC = _summary_projection("anc")

# ---------------------------------------------------------------------------
# Cypher
# ---------------------------------------------------------------------------

_RESOLVE_BY_KEY: Final = """
MATCH (p:Passage {canonical_key: $key})
RETURN p.canonical_key AS canonical_key
"""

_RESOLVE_BY_URN: Final = """
MATCH (p:Passage {canonical_urn: $key})
RETURN p.canonical_key AS canonical_key
"""

# The only lookup in this module that cannot use an index: canonical_citation is unique in
# fact but carries no constraint, so this is a scan of 22,537 nodes at roughly 25ms. It runs
# only when the client supplied a citation rather than a key.
_RESOLVE_BY_CITATION: Final = """
MATCH (p:Passage {canonical_citation: $citation})
RETURN p.canonical_key AS canonical_key
"""

_WORKS: Final = """
MATCH (w:Work)
CALL (w) {
    MATCH (p:Passage {work_id: w.work_id})
    RETURN count(p) AS passage_count,
           count(CASE WHEN p.display_type = 'MANTRA' THEN 1 END) AS mantra_count
}
CALL (w) {
    MATCH (p:Passage {work_id: w.work_id, display_type: 'MANTRA'})
          -[:HAS_TRANSLATION]->(t:Translation)
    RETURN count(DISTINCT p) AS translated_count,
           collect(DISTINCT t.translator) AS translators
}
RETURN w.work_id AS work_id, w.veda AS veda, w.abbreviation AS abbreviation,
       w.display_label AS display_label, w.work_name AS work_name, w.scope AS scope,
       w.scope_source AS scope_source, w.scope_evidence AS scope_evidence,
       w.completeness AS completeness, w.excluded_corpora AS excluded_corpora,
       w.rights AS rights,
       passage_count, mantra_count, translated_count, translators
ORDER BY w.work_id
"""

_WORK: Final = _WORKS.replace("MATCH (w:Work)", "MATCH (w:Work {work_id: $work_id})")

# Grouped on (display_type, key depth, native_labels) rather than on the hierarchy string
# itself, which has 22,537 distinct values. native_labels is in the grouping key because it
# separates the two Samavedic shapes that share a key depth -- Collection/Dasati against
# Collection/Prapathaka, both five segments -- and min/max give two representatives per
# group so a group holding two shapes still yields both. Fifteen rows for the largest work.
_WORK_STRUCTURE: Final = """
MATCH (p:Passage {work_id: $work_id})
WITH p.display_type AS passage_type,
     size(split(p.canonical_key, ':')) AS key_depth,
     p.native_labels AS native_labels,
     count(*) AS passages,
     min(p.hierarchy) AS first_shape,
     max(p.hierarchy) AS last_shape
RETURN passage_type, key_depth, native_labels, passages, first_shape, last_shape
ORDER BY key_depth, passage_type
"""

# Two queries rather than one, because the two questions cost very different amounts.
# Reach needs one `count(DISTINCT p)` over every layer; the attribution split needs three
# of them, and three distinct aggregations over the Rigveda's 120,000 out-edges measured
# 189ms against 88ms for one. Only three predicates carry attribution_precision, so the
# expensive query runs over a twentieth of the edges and the endpoint drops to ~160ms.
_WORK_LAYERS: Final = """
MATCH (p:Passage {work_id: $work_id})-[r]->()
WHERE type(r) IN $layer_relations
RETURN type(r) AS relation, count(r) AS edges, count(DISTINCT p) AS passages
ORDER BY relation
"""

_WORK_ATTRIBUTION_SPLITS: Final = """
MATCH (p:Passage {work_id: $work_id})-[r]->()
WHERE type(r) IN $split_relations
RETURN type(r) AS relation, count(r) AS edges,
       count(DISTINCT CASE WHEN r.attribution_precision = 'PER_PASSAGE' THEN p END)
           AS source_stated,
       count(DISTINCT CASE WHEN r.attribution_precision = 'CONTAINER_INHERITED' THEN p END)
           AS container_inherited
ORDER BY relation
"""

_WORK_SCRIPTS: Final = """
MATCH (:Passage {work_id: $work_id})-[:HAS_TEXT_VERSION]->(tv:TextVersion)
RETURN collect(DISTINCT tv.script) AS scripts
"""

_WORK_ROOTS: Final = f"""
MATCH (w:Work {{work_id: $work_id}})-[c:CONTAINS]->(child:Passage)
WITH child, c.sequence AS sequence ORDER BY sequence, child.canonical_key
WITH collect({_CHILD}) AS rows
RETURN size(rows) AS total, rows[$offset..($offset + $limit)] AS items
"""

_ANCESTORS: Final = f"""
MATCH (p:Passage {{canonical_key: $key}})
OPTIONAL MATCH (anc:Passage)-[:CONTAINS*1..8]->(p)
WITH anc ORDER BY size(split(anc.canonical_key, ':'))
RETURN collect({_ANC}) AS ancestors
"""

_CHILDREN: Final = f"""
MATCH (child:Passage {{parent_key: $key}})
WITH child ORDER BY child.sequence_in_parent, child.canonical_key
WITH collect({_CHILD}) AS rows
RETURN size(rows) AS total, rows[$offset..($offset + $limit)] AS items
"""

# Siblings exclude the anchor itself. Excluding it means an only child returns an empty
# page, which is why the route attaches a caveat saying so rather than letting the empty
# list read as "this passage has no siblings in the corpus".
_SIBLINGS: Final = f"""
MATCH (child:Passage {{parent_key: $parent_key}})
WHERE child.canonical_key <> $key
WITH child ORDER BY child.sequence_in_parent, child.canonical_key
WITH collect({_CHILD}) AS rows
RETURN size(rows) AS total, rows[$offset..($offset + $limit)] AS items
"""

_PASSAGE_BY_KEY: Final = f"""
MATCH (p:Passage {{canonical_key: $key}})
RETURN {_P} AS passage
"""

# The neighbour context: which top-level container this passage sits under, and which
# containers precede and follow it in the *stored* sequence. The stored sequence is what
# makes the Samaveda work: its four collections are CHANDA(1), ARANYAKA(2), MAHANAMNYA(3),
# UTTARA(4) and sort alphabetically in a different order.
_NEIGHBOUR_CONTEXT: Final = """
MATCH (p:Passage {canonical_key: $key})
OPTIONAL MATCH (root:Passage)-[:CONTAINS*0..8]->(p)
WHERE root.parent_key IS NULL
CALL (p, root) {
    OPTIONAL MATCH (nr:Passage {work_id: p.work_id})
    WHERE nr.parent_key IS NULL AND nr.sequence_in_parent > root.sequence_in_parent
    RETURN nr.canonical_key AS next_root
    ORDER BY nr.sequence_in_parent
    LIMIT 1
}
CALL (p, root) {
    OPTIONAL MATCH (pr:Passage {work_id: p.work_id})
    WHERE pr.parent_key IS NULL AND pr.sequence_in_parent < root.sequence_in_parent
    RETURN pr.canonical_key AS previous_root
    ORDER BY pr.sequence_in_parent DESC
    LIMIT 1
}
RETURN p.work_id AS work_id, p.display_type AS display_type,
       root.canonical_key AS root_key, next_root, previous_root
"""

# Four candidates, ranked. rank 0 stays inside the current top-level container and rank 1
# steps into the next one, so a within-container neighbour always wins and the step across
# a boundary happens only at a real boundary. This is what crosses RV 1.1.9 to RV 1.2.1,
# RV 1.191.16 to RV 2.1.1, and the last CHANDA verse to SV ARANYA 1.1 rather than to
# MAHANAMNYA. A missing $next_root or $previous_root yields no row, so the first and last
# passage of a work return a null neighbour instead of an error.
_NEIGHBOURS: Final = f"""
CALL () {{
    MATCH (other:Passage {{work_id: $work_id, display_type: $display_type}})
    WHERE other.canonical_key STARTS WITH $root_key AND other.canonical_key > $key
    RETURN {_OTHER} AS passage, 'NEXT' AS direction, 0 AS rank
    ORDER BY other.canonical_key
    LIMIT 1
  UNION ALL
    MATCH (other:Passage {{work_id: $work_id, display_type: $display_type}})
    WHERE $next_root IS NOT NULL AND other.canonical_key STARTS WITH $next_root
    RETURN {_OTHER} AS passage, 'NEXT' AS direction, 1 AS rank
    ORDER BY other.canonical_key
    LIMIT 1
  UNION ALL
    MATCH (other:Passage {{work_id: $work_id, display_type: $display_type}})
    WHERE other.canonical_key STARTS WITH $root_key AND other.canonical_key < $key
    RETURN {_OTHER} AS passage, 'PREVIOUS' AS direction, 0 AS rank
    ORDER BY other.canonical_key DESC
    LIMIT 1
  UNION ALL
    MATCH (other:Passage {{work_id: $work_id, display_type: $display_type}})
    WHERE $previous_root IS NOT NULL AND other.canonical_key STARTS WITH $previous_root
    RETURN {_OTHER} AS passage, 'PREVIOUS' AS direction, 1 AS rank
    ORDER BY other.canonical_key DESC
    LIMIT 1
}}
RETURN direction, rank, passage
ORDER BY direction, rank
"""

_TEXT_BLOCK: Final = """
CALL (p) {
    MATCH (p)-[:HAS_TEXT_VERSION]->(tv:TextVersion)
    RETURN collect({
        text_role: tv.text_role, script: tv.script, accented: tv.accented,
        text: tv.text_nfc, language: tv.language, witness_id: tv.text_version_id,
        source_id: tv.source_id, rights_status: tv.rights_status
    }) AS text_versions
}
CALL (p) {
    MATCH (p)-[:HAS_TRANSLATION]->(t:Translation)
    RETURN collect({
        text: t.text, translator: t.translator, language: t.language, year: t.year,
        work_edition: t.work_edition, quality_status: t.quality_status,
        alignment_level: t.alignment_level, rights_status: t.rights_status,
        source_id: t.source_id, upstream_correction_id: t.upstream_correction_id,
        upstream_correction_reason: t.upstream_correction_reason
    }) AS translations
}
"""

_ATTRIBUTION_BLOCK: Final = """
CALL (p) {
    MATCH (p)-[r:HAS_RISHI]->(x:Rishi)
    RETURN collect({
        id: x.entity_key, display_label: x.display_label, subtitle: x.label_iast,
        attribution_precision: r.attribution_precision, evidence_basis: r.evidence_basis
    }) AS rishis
}
CALL (p) {
    MATCH (p)-[r:HAS_DEVATA]->(x:Devata)
    RETURN collect({
        id: x.entity_key, display_label: x.display_label, subtitle: x.short_description,
        attribution_precision: r.attribution_precision, evidence_basis: r.evidence_basis
    }) AS devatas
}
CALL (p) {
    MATCH (p)-[r:HAS_CHANDAS]->(x:Chandas)
    RETURN collect({
        id: x.entity_key, display_label: x.display_label, subtitle: x.label_iast,
        attribution_precision: r.attribution_precision, evidence_basis: r.evidence_basis
    }) AS chandas
}
CALL (p) {
    // Every tier is fetched and the filtering happens in Python, deliberately. Filtering
    // in Cypher would make the excluded rows unobservable, and the ambiguity contract
    // requires reporting all three counts whenever any count is reported -- a client has
    // to be able to see that RV 1.4.2's single mention was withheld, not just that the
    // list is empty. `referent_certainty` is the load-bearing projection: without it the
    // row is indistinguishable from a certain one, which is what made this a defect.
    MATCH (p)-[r:MENTIONS_DEVATA]->(x:Devata)
    RETURN collect({
        id: x.entity_key, display_label: x.display_label, subtitle: x.short_description,
        attribution_precision: r.attribution_precision, evidence_basis: r.evidence_basis,
        referent_certainty: r.referent_certainty, occurrences: r.occurrences
    }) AS mentioned_devatas
}
"""

_CONCEPT_BLOCK: Final = """
CALL (p) {
    MATCH (p)-[r:ABOUT_CONCEPT]->(c:Concept)
    WITH c, r ORDER BY coalesce(r.score, 0) DESC, c.display_label
    WITH collect({
        type: c.node_type, id: c.entity_key, display_label: c.display_label,
        subtitle: c.short_description
    }) AS rows
    RETURN size(rows) AS concept_total, rows[0..$entity_limit] AS concepts
}
"""

_DETAIL: Final = (
    """
MATCH (p:Passage {canonical_key: $key})
OPTIONAL MATCH (w:Work {work_id: p.work_id})
OPTIONAL MATCH (parent:Passage {canonical_key: p.parent_key})
"""
    + _TEXT_BLOCK
    + _ATTRIBUTION_BLOCK
    + _CONCEPT_BLOCK
    + """
CALL (p) {
    MATCH (p)-[r:MENTIONS_ENTITY]->(c:Concept)
    WITH c, r ORDER BY coalesce(r.score, 0) DESC, c.display_label
    WITH collect({
        type: c.node_type, id: c.entity_key, display_label: c.display_label,
        subtitle: c.short_description
    }) AS rows
    RETURN size(rows) AS mention_total, rows[0..$entity_limit] AS mentioned_entities
}
CALL (p) {
    MATCH (p)-[:USES_FORMULA]->(f:Formula)
    WITH f ORDER BY coalesce(f.occurrence_count, 0) DESC, f.display_form
    WITH collect({
        type: 'FORMULA', id: f.formula_id, display_label: f.display_form,
        subtitle: f.normalized
    }) AS rows
    RETURN size(rows) AS formula_total, rows[0..$entity_limit] AS formulas
}
CALL (p) {
    MATCH (p)-[r]->(target)
    WHERE type(r) IN $semantic_relations
    WITH r, target ORDER BY type(r), target.display_label
    WITH collect({
        relation: type(r),
        target: {
            type: coalesce(target.node_type, 'CONCEPT'), id: target.entity_key,
            display_label: target.display_label, subtitle: target.short_description
        },
        attribution_precision: r.attribution_precision, evidence_basis: r.evidence_basis,
        quality_tier: r.quality_tier, state: r.state, confidence: r.confidence,
        knowledge_layer: r.knowledge_layer
    }) AS rows
    RETURN size(rows) AS relation_total, rows[0..$entity_limit] AS semantic_relations
}
CALL (p) {
    MATCH (p)-[:HAS_SEMANTIC_ASSERTION]->(a:SemanticAssertion)
    OPTIONAL MATCH (a)-[:ASSERTION_AGENT]->(agent)
    OPTIONAL MATCH (a)-[:ASSERTION_PREDICATE]->(predicate)
    OPTIONAL MATCH (a)-[:ASSERTION_TARGET]->(object)
    WITH a, agent, predicate, object ORDER BY a.display_label
    WITH collect({
        display_label: a.display_label,
        // `frame`, not `modality`. There is no `modality` property anywhere in this graph
        // -- reading one returned null on all 4,865 assertions without erroring, because
        // Neo4j answers a missing property with null rather than a failure, so the defect
        // survived a passing test and a rendered page. `frame` is the real axis:
        // ASSERTED 1,557, REQUESTED 849, absent on the 2,459 model-extracted rows.
        frame: a.frame,
        semantic_predicate: a.semantic_predicate, explicitness: a.explicitness,
        state: a.state,
        verb_surface: a.verb_surface, root_label: a.root_label,
        quality_tier: a.quality_tier, evidence_basis: a.evidence_basis,
        attribution_precision: a.attribution_precision,
        knowledge_layer: a.knowledge_layer,
        agent: CASE WHEN agent IS NULL THEN NULL ELSE
            {type: 'DEVATA', id: agent.entity_key, display_label: agent.display_label}
        END,
        predicate: CASE WHEN predicate IS NULL THEN NULL ELSE
            {type: 'ACTION_PREDICATE', id: predicate.entity_key,
             display_label: predicate.display_label}
        END,
        target: CASE WHEN object IS NULL THEN NULL ELSE
            {type: 'DEVATA', id: object.entity_key, display_label: object.display_label}
        END
    }) AS rows
    RETURN size(rows) AS assertion_total, rows[0..$entity_limit] AS agentive_assertions
}
CALL (p) {
    MATCH (p)-[:CONTAINS]->(child:Passage)
    RETURN count(child) AS child_count
}
"""
    + f"""
RETURN {_P} AS passage,
       w.display_label AS work_display_label, w.work_name AS work_traditional_name,
       w.rights AS work_rights,
       CASE WHEN parent IS NULL THEN NULL ELSE {_summary_projection("parent")} END AS parent,
       text_versions, translations, rishis, devatas, chandas, mentioned_devatas,
       concepts, concept_total, mentioned_entities, mention_total,
       formulas, formula_total, semantic_relations, relation_total,
       agentive_assertions, assertion_total, child_count
"""
)

_READER: Final = (
    """
MATCH (p:Passage {canonical_key: $key})
OPTIONAL MATCH (w:Work {work_id: p.work_id})
"""
    + _TEXT_BLOCK
    + _ATTRIBUTION_BLOCK
    + _CONCEPT_BLOCK
    + """
// The inner WITH-then-collect is load-bearing and not a style choice. Aggregating with a
// grouping key -- RETURN type(r), count(*) -- yields no rows for a passage that has no
// parallel edge, and a CALL subquery returning no rows eliminates the outer row, so the
// whole reader payload would vanish and the route would answer 404. Most passages have no
// parallel, so that is the common case, not the edge case. Collecting without a grouping
// key always produces exactly one row, empty list included.
CALL (p) {
    MATCH (p)-[r]-(other:Passage)
    WHERE type(r) IN $parallel_predicates
    WITH type(r) AS predicate, count(*) AS edges
    RETURN collect({predicate: predicate, edges: edges}) AS parallel_counts
}
CALL (p) {
    MATCH (p)-[r]-(o)
    WHERE NOT o:Internal AND type(r) <> 'CONTAINS'
    RETURN count(DISTINCT o) AS graph_neighbour_count
}
"""
    + f"""
RETURN {_P} AS passage, w.display_label AS work_display_label,
       w.work_name AS work_traditional_name,
       text_versions, translations, rishis, devatas, chandas, mentioned_devatas,
       concepts, concept_total, parallel_counts, graph_neighbour_count
"""
)

_PARALLEL_COUNTS: Final = """
MATCH (p:Passage {canonical_key: $key})-[r]-(other:Passage)
WHERE type(r) IN $parallel_predicates
RETURN type(r) AS predicate, count(*) AS edges
ORDER BY predicate
"""

# Both directions, tagged. The UNION ALL is the whole point: a directed traversal shows
# 1,421 Rigvedic passages no text reuse while returning 200.
_PARALLELS: Final = f"""
MATCH (p:Passage {{canonical_key: $key}})
CALL (p) {{
    MATCH (p)-[r]->(other:Passage)
    WHERE type(r) IN $predicates
    RETURN type(r) AS predicate, properties(r) AS props, {_OTHER} AS passage,
           other.veda AS other_veda, 'THIS_PASSAGE_IS_SUBJECT' AS stored_direction
  UNION ALL
    MATCH (p)<-[r]-(other:Passage)
    WHERE type(r) IN $predicates
    RETURN type(r) AS predicate, properties(r) AS props, {_OTHER} AS passage,
           other.veda AS other_veda, 'THIS_PASSAGE_IS_OBJECT' AS stored_direction
}}
WITH p, predicate, props, passage, other_veda, stored_direction
WHERE ($same_veda_only = false OR other_veda = p.veda)
  AND ($cross_veda_only = false OR other_veda <> p.veda)
WITH predicate, props, passage, other_veda, stored_direction, p.veda AS this_veda
ORDER BY predicate, passage.canonical_key
WITH collect({{
    predicate: predicate, props: props, passage: passage, other_veda: other_veda,
    stored_direction: stored_direction, this_veda: this_veda
}}) AS rows
RETURN size(rows) AS total, rows[$offset..($offset + $limit)] AS items
"""

# Formula-mediated, which is not an edge. The inner LIMIT bounds the fan-out: one formula
# occurring in several hundred passages would otherwise make this the slowest read in the
# API, and a bound with a stated ceiling is better than a timeout.
_FORMULA_PARALLELS: Final = f"""
MATCH (p:Passage {{canonical_key: $key}})-[:USES_FORMULA]->(f:Formula)
      <-[:USES_FORMULA]-(other:Passage)
WHERE other.canonical_key <> p.canonical_key
  AND ($same_veda_only = false OR other.veda = p.veda)
  AND ($cross_veda_only = false OR other.veda <> p.veda)
WITH p, other, f
LIMIT $fan_out
WITH p, other, collect(DISTINCT {{
    type: 'FORMULA', id: f.formula_id, display_label: f.display_form,
    subtitle: f.normalized
}}) AS shared_formulas
ORDER BY size(shared_formulas) DESC, other.canonical_key
WITH collect({{
    passage: {_OTHER}, other_veda: other.veda, this_veda: p.veda,
    shared_formulas: shared_formulas
}}) AS rows
RETURN size(rows) AS total, rows[$offset..($offset + $limit)] AS items
"""


# ---------------------------------------------------------------------------
# Pure mapping helpers
# ---------------------------------------------------------------------------


def _json_list(value: object) -> list[str]:
    """A graph property that is a JSON string list, a real list, or neither."""
    parsed = parse_json_property(value)
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    return []


def _hierarchy_map(value: object) -> dict[str, str]:
    """The ``hierarchy`` JSON string as a string-valued map.

    Values are stringified because the Samavedic ``collection`` level holds a name where
    every other level holds an ordinal, and a union type on the wire would push that
    branch into every client.
    """
    parsed = parse_json_property(value)
    if not isinstance(parsed, dict):
        return {}
    return {str(key): str(item) for key, item in parsed.items()}


def _nonempty(value: object) -> str | None:
    """``None`` for a null or an empty string.

    The graph stores ``match_level = ''`` on 4,229 parallel edges and
    ``upstream_correction_reason = ''`` on most translations. An empty string rendered in a
    UI is a blank field that looks like data; a null is a field a client can skip.
    """
    if value is None:
        return None
    text = str(value)
    return text or None


def _as_float(value: object) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _as_int(value: object) -> int | None:
    return int(value) if isinstance(value, int) and not isinstance(value, bool) else None


def _evidence_basis(value: object, precision: object = None) -> EvidenceBasis:
    """The evidence basis, derived from ``attribution_precision`` where the edge has one.

    The derivation lives in ``models.common`` now, not here. It was written in this module
    first because the graph's ``evidence_basis`` property does not answer the question
    :class:`EvidenceBasis` asks -- its value space is six names for *which surface* the
    evidence was read off, not one of which is a member of the enum, so casting it reported
    every attribution edge in the corpus as ``UNKNOWN``. That finding is now a shared
    contract with its own vocabulary test, and keeping a second copy of the table here
    would be exactly the drift this repository has been burned by three times.

    ``attribution_precision`` is preferred and the graph property is the fallback, for the
    handful of edges that carry a value the enum happens to share.
    """
    if precision is not None:
        derived = basis_from_attribution_precision(_nonempty(precision))
        if derived is not EvidenceBasis.UNKNOWN:
            return derived
    try:
        return EvidenceBasis(str(value))
    except ValueError:
        return EvidenceBasis.UNKNOWN


def _attribution_precision(value: object) -> AttributionPrecision:
    """The graph's ``attribution_precision`` as its own type, unknown values included."""
    try:
        return AttributionPrecision(str(value))
    except ValueError:
        return AttributionPrecision.UNKNOWN


def _assertion_modality(value: object) -> AssertionModality | None:
    """The graph's ``frame`` as a modality, or ``None`` for the model-extracted stratum.

    ``None`` is a real answer here and the caller must type it: see
    :data:`_MODALITY_ABSENT_NOTE`. An unrecognised frame also returns ``None`` rather than
    being passed through, so a new value shows up as an absence with a note attached rather
    than as a string a client is invited to render.
    """
    try:
        return AssertionModality(str(value))
    except ValueError:
        return None


def _summary(row: object) -> PassageSummary | None:
    """Map a ``_summary_projection`` row onto :class:`PassageSummary`."""
    if not isinstance(row, dict) or not row.get("canonical_key"):
        return None
    hierarchy = _hierarchy_map(row.get("hierarchy"))
    levels = order_levels(list(hierarchy))
    return PassageSummary(
        canonical_key=str(row["canonical_key"]),
        canonical_citation=_nonempty(row.get("canonical_citation")),
        canonical_urn=_nonempty(row.get("canonical_urn")),
        entity_id=_nonempty(row.get("entity_id")),
        veda=str(row.get("veda") or ""),
        work_id=str(row.get("work_id") or ""),
        passage_type=str(row.get("display_type") or "UNKNOWN"),
        display_label=_nonempty(row.get("display_label")),
        native_levels=[NATIVE_LEVEL_LABELS.get(key, "UNKNOWN") for key in levels],
        hierarchy=hierarchy,
        parent_key=_nonempty(row.get("parent_key")),
        sequence_in_parent=_as_int(row.get("sequence_in_parent")),
    )


def _require_summary(row: object, key: str) -> PassageSummary:
    summary = _summary(row)
    if summary is None:
        raise PassageNotFoundError(f"No passage matches {key!r}.", hint=_KEY_HINT)
    return summary


def _attributed(rows: object) -> list[AttributedRef]:
    """Map attribution rows, each keeping its own precision.

    Precision travels per row and is never folded into the set, because a passage can
    carry one source-stated seer and one inherited from its hymn, and a set-level flag
    would have to pick one of them.
    """
    out: list[AttributedRef] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict) or not row.get("id"):
            continue
        out.append(
            AttributedRef(
                type="DEVATA" if "DEVATA" in str(row["id"]) else _ref_type(str(row["id"])),
                id=str(row["id"]),
                display_label=str(row.get("display_label") or row["id"]),
                subtitle=_nonempty(row.get("subtitle")),
                attribution_precision=_nonempty(row.get("attribution_precision")),
                evidence_basis=_evidence_basis(
                    row.get("evidence_basis"), row.get("attribution_precision")
                ),
            )
        )
    return out


def _ref_type(entity_id: str) -> str:
    """The product type from a ``VG:TYPE:...`` product id.

    Read off the id rather than off ``labels(n)``: these nodes are heavily multi-labelled
    and Neo4j does not guarantee ``labels()`` ordering, so ``labels(n)[0]`` returns a
    different type per node and potentially a different one after a restart.
    """
    parts = entity_id.split(":")
    return parts[1] if len(parts) > 2 and parts[0] == "VG" else "UNKNOWN"


def _entity_refs(rows: object) -> list[EntityRef]:
    out: list[EntityRef] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict) or not row.get("id"):
            continue
        out.append(
            EntityRef(
                type=str(row.get("type") or _ref_type(str(row["id"]))),
                id=str(row["id"]),
                display_label=str(row.get("display_label") or row["id"]),
                subtitle=_nonempty(row.get("subtitle")),
            )
        )
    return out


def _text_surfaces(rows: object) -> list[TextSurfaceView]:
    out: list[TextSurfaceView] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict) or not row.get("text"):
            continue
        role = str(row.get("text_role") or "")
        surface = _TEXT_SURFACE_BY_ROLE.get(role, "PRIMARY" if not role else role)
        out.append(
            TextSurfaceView(
                surface=surface,
                script=_SCRIPT_BY_GRAPH_VALUE.get(str(row.get("script")), TextScript.UNKNOWN),
                accented=row.get("accented") if isinstance(row.get("accented"), bool) else None,
                text=str(row["text"]),
                language=str(row.get("language") or "sa"),
                witness_id=_nonempty(row.get("witness_id")),
                source_id=_nonempty(row.get("source_id")),
                rights_status=_nonempty(row.get("rights_status")),
                is_displayable=surface in _DISPLAYABLE_SURFACES,
                note=(
                    "Accent-stripped and normalised for matching. Not the text to render."
                    if surface == "NORMALIZED_FOR_SEARCH"
                    else None
                ),
            )
        )
    out.sort(
        key=lambda item: (
            _SURFACE_PREFERENCE.index(item.surface)
            if item.surface in _SURFACE_PREFERENCE
            else len(_SURFACE_PREFERENCE)
        )
    )
    return out


def _text_availability(rows: object, *, is_container: bool) -> TextAvailability:
    """Surfaces plus a status per script.

    A container gets ``NOT_BUILT`` and a caveat rather than ``SUPPORTED`` with an empty
    list, because "this Sukta has no text" and "this verse has no text" would otherwise be
    the same payload, and only the first is a fact about the corpus's shape.
    """
    surfaces = _text_surfaces(rows)
    if not surfaces:
        return TextAvailability(
            surfaces=[],
            data_status=KnowledgeStatus.NOT_BUILT if is_container else KnowledgeStatus.PARTIAL,
            caveats=[
                CaveatView(
                    text=(
                        _CONTAINER_HAS_NO_TEXT_CAVEAT
                        if is_container
                        else "No Sanskrit witness is attached to this passage. That is a gap "
                        "in the ingested corpus and not a statement about the text."
                    ),
                    source="measured",
                )
            ],
        )
    scripts = {surface.script for surface in surfaces}
    caveats = [CaveatView(text=_SCRIPT_DISJOINT_CAVEAT, source="measured")]
    return TextAvailability(
        surfaces=surfaces,
        devanagari=(
            KnowledgeStatus.SUPPORTED
            if TextScript.DEVANAGARI in scripts
            else KnowledgeStatus.NOT_BUILT
        ),
        transliteration=(
            KnowledgeStatus.SUPPORTED if TextScript.IAST in scripts else KnowledgeStatus.NOT_BUILT
        ),
        normalized_for_search=(
            KnowledgeStatus.SUPPORTED
            if any(surface.surface == "NORMALIZED_FOR_SEARCH" for surface in surfaces)
            else KnowledgeStatus.NOT_BUILT
        ),
        data_status=KnowledgeStatus.SUPPORTED,
        caveats=caveats,
    )


def _translations(rows: object) -> list[TranslationView]:
    out: list[TranslationView] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict) or not row.get("text"):
            continue
        out.append(
            TranslationView(
                text=str(row["text"]),
                translator=_nonempty(row.get("translator")),
                language=str(row.get("language") or "en"),
                year=_as_int(row.get("year")),
                work_edition=_nonempty(row.get("work_edition")),
                quality_status=_nonempty(row.get("quality_status")),
                alignment_level=_nonempty(row.get("alignment_level")),
                rights_status=_nonempty(row.get("rights_status")),
                source_id=_nonempty(row.get("source_id")),
                upstream_correction_id=_nonempty(row.get("upstream_correction_id")),
                upstream_correction_reason=_nonempty(row.get("upstream_correction_reason")),
            )
        )
    return out


def _evidence_view(props: dict[str, Any]) -> EvidenceView | None:
    """The edge's evidence, whichever of its two storage shapes it used.

    ``evidence`` is a JSON string of quoted spans on the four textual predicates and a
    plain list of concept keys on ``SHARES_ENTITY_VOCABULARY_WITH``. Reading one shape
    would silently drop the other predicate's evidence.
    """
    raw = props.get("evidence")
    spans: list[EvidenceSpanView] = []
    parsed = parse_json_property(raw)
    if isinstance(parsed, list):
        for item in parsed:
            if isinstance(item, dict):
                spans.append(
                    EvidenceSpanView(
                        passage_key=_nonempty(item.get("locator")),
                        quote=_nonempty(item.get("quote")),
                        surface=_nonempty(item.get("surface")),
                    )
                )
    if not spans and not props.get("method") and not props.get("quality_tier"):
        return None
    return EvidenceView(
        method=_nonempty(props.get("method")),
        tier=_nonempty(props.get("quality_tier")),
        evidence_basis=_evidence_basis(
            props.get("evidence_basis"), props.get("attribution_precision")
        ),
        # Both axes, side by side. `surface` is the graph's own evidence_basis read into
        # its own type, which is what lets a client see that a claim rests on Griffith's
        # English rather than on the Sanskrit; `evidence_basis` above is the derived
        # question of how the claim arose. Conflating them is the collision this pair of
        # fields exists to make visible.
        surface=evidence_surface(_nonempty(props.get("evidence_basis"))),
        attribution_precision=_attribution_precision(props.get("attribution_precision")),
        review_state=_nonempty(props.get("review_state")),
        confidence=_as_float(props.get("confidence")),
        spans=spans,
        derivation=_nonempty(props.get("grade_basis")),
    )


def _veda_pair(this_veda: str, other_veda: str) -> str | None:
    """The corpus pair, derived from the two passages.

    Never read from the stored ``veda_pair``: it is null on all 325 same-Veda edges, so a
    client filtering on it would lose every intra-Rigvedic parallel.
    """
    if not this_veda or not other_veda:
        return None
    return "-".join(sorted({this_veda, other_veda}))


def _parallel_view(row: dict[str, Any]) -> ParallelView | None:
    passage = _summary(row.get("passage"))
    if passage is None:
        return None
    predicate = str(row.get("predicate") or "")
    relation, kind = _PARALLEL_PREDICATES.get(
        predicate, (predicate or "RELATED", ParallelKind.TEXTUAL_PARALLEL)
    )
    props = row.get("props") if isinstance(row.get("props"), dict) else {}
    assert isinstance(props, dict)
    this_veda = str(row.get("this_veda") or "")
    other_veda = str(row.get("other_veda") or "")
    shared = props.get("evidence")
    return ParallelView(
        relation=relation,
        relation_kind=kind,
        is_textual_parallelism=kind is not ParallelKind.ENTITY_VOCABULARY_OVERLAP,
        passage=passage,
        stored_direction=StoredDirection(str(row.get("stored_direction"))),
        same_veda=this_veda == other_veda,
        veda_pair=_veda_pair(this_veda, other_veda),
        metrics=ParallelMetrics(
            similarity=_as_float(props.get("similarity")),
            score=_as_float(props.get("score")),
            token_jaccard=_as_float(props.get("token_jaccard")),
            ngram_jaccard=_as_float(props.get("ngram_jaccard")),
            lcs_ratio=_as_float(props.get("lcs_ratio")),
            edit_ratio=_as_float(props.get("edit_ratio")),
            distinctiveness=_as_float(props.get("distinctiveness")),
            rarest_shared_df=_as_int(props.get("rarest_shared_df")),
        ),
        match_level=_nonempty(props.get("match_level")),
        method=_nonempty(props.get("method")),
        methods=_json_list(props.get("methods")),
        levels_reached=_json_list(props.get("levels_reached")),
        strongest_method=_nonempty(props.get("strongest_method")),
        shared_entities=_as_int(props.get("shared_entities")),
        shared_entity_keys=(
            [str(item) for item in shared]
            if kind is ParallelKind.ENTITY_VOCABULARY_OVERLAP and isinstance(shared, list)
            else _json_list(props.get("shared_entity_keys"))
        ),
        quality_tier=_nonempty(props.get("quality_tier")),
        trust=_nonempty(props.get("trust")),
        state=_nonempty(props.get("state")),
        knowledge_layer=_nonempty(props.get("knowledge_layer")),
        attribution_precision=_nonempty(props.get("attribution_precision")),
        parallel_id=_nonempty(props.get("parallel_id")),
        evidence=_evidence_view(props),
    )


def _formula_parallel_view(row: dict[str, Any]) -> ParallelView | None:
    passage = _summary(row.get("passage"))
    if passage is None:
        return None
    this_veda = str(row.get("this_veda") or "")
    other_veda = str(row.get("other_veda") or "")
    formulas = _entity_refs(row.get("shared_formulas"))
    return ParallelView(
        relation="SHARES_FORMULA",
        relation_kind=ParallelKind.FORMULA_MEDIATED,
        is_textual_parallelism=True,
        passage=passage,
        stored_direction=StoredDirection.NOT_STORED_AS_AN_EDGE,
        same_veda=this_veda == other_veda,
        veda_pair=_veda_pair(this_veda, other_veda),
        shared_formulas=formulas,
        shared_entities=len(formulas),
        method="formula-occurrence-word-aligned-v1",
    )


def paged_meaning[T](
    items: list[T],
    *,
    limit: int,
    offset: int,
    total: int | None,
    empty_status: KnowledgeStatus,
    empty_caveats: list[CaveatView] | None = None,
) -> tuple[KnowledgeStatus, list[CaveatView]]:
    """Status describes the collection; caveats describe the page.

    Every paginated collection in this module derives its ``data_status`` from ``total``
    and never from the page, because those are different questions and only one of them is
    about the corpus. ``GET /api/v1/works?offset=99999999`` is a client asking for page four
    million of a four-row collection: answering it ``INSUFFICIENT_EVIDENCE`` spends a status
    that means "evidence exists and cannot support the claim" on client arithmetic, and a
    reader who has seen it mean "you paged off the end" will discount it everywhere it is
    load-bearing.

    The same reasoning applies to the *prose*, which is the sharper half of the bug. A
    caveat chosen from the page rather than the collection can be flatly false: asking for
    ``/passages/VG:AV:SAU:K20/children?offset=99999`` used to answer "This passage contains
    no further passages: it is a mantra, the deepest level of its work" about a Kanda
    holding 143 Suktas. So ``empty_caveats`` is attached only when the collection really is
    empty, and a page emptied by paging gets the paging sentence instead.
    """
    collection_is_empty = total == 0 if total is not None else not items and offset == 0
    status = empty_status if collection_is_empty else KnowledgeStatus.SUPPORTED
    caveats = list(empty_caveats or []) if collection_is_empty else []
    if not collection_is_empty:
        # Guarded on a non-empty collection because the shared sentence ends "data_status
        # above describes the collection, which is not empty" -- true of an overrun and
        # false of a collection that really has no rows. Attaching it to a genuinely empty
        # collection would contradict the status it points at.
        #
        # The PaginationMeta is built only to ask the shared helper its question and is
        # then discarded; `paginate` builds the one actually returned, and `has_more` is
        # not read here, so it is not computed twice.
        overrun = offset_overrun_caveat(
            PaginationMeta(
                limit=limit, offset=offset, returned=len(items), total=total, has_more=False
            )
        )
        if overrun is not None:
            caveats.append(overrun)
    return status, caveats


def _parallel_counts(rows: list[dict[str, Any]]) -> ParallelCounts:
    by_predicate = {
        str(row.get("predicate")): _as_int(row.get("edges")) or 0
        for row in rows
        if row.get("predicate")
    }
    exact = by_predicate.get("EXACT_PARALLEL_OF", 0)
    other_textual = by_predicate.get("PARALLEL_TO", 0)
    near = by_predicate.get("NEAR_PARALLEL_OF", 0)
    reuse = by_predicate.get("REUSES_TEXT_FROM", 0)
    variant = by_predicate.get("VARIANT_OF", 0)
    vocabulary = by_predicate.get("SHARES_ENTITY_VOCABULARY_WITH", 0)
    textual_total = exact + near + reuse + variant + other_textual
    caveats = [CaveatView(text=_UNDIRECTED_CAVEAT, source="measured")]
    if vocabulary:
        caveats.append(CaveatView(text=_VOCABULARY_CAVEAT, source="measured"))
    return ParallelCounts(
        exact=exact,
        near=near,
        reuse=reuse,
        variant=variant,
        entity_vocabulary_overlap=vocabulary,
        other_textual=other_textual,
        textual_total=textual_total,
        data_status=(
            KnowledgeStatus.SUPPORTED if textual_total or vocabulary else KnowledgeStatus.PARTIAL
        ),
        caveats=caveats,
    )


# ---------------------------------------------------------------------------
# Citation resolution
# ---------------------------------------------------------------------------


def citation_candidate(raw: str) -> str | None:
    """A client string normalised to the ``canonical_citation`` the graph stores.

    Accepts ``RV 1.1.1``, ``RV.1.1.1``, ``rv_1.1.1``, ``rv-1-1-1``, ``AV 20.143.9`` (the
    graph stores ``AVS``), ``YV 1.1`` (stored ``VSM``) and ``sv_aranya_1.1``. Returns
    ``None`` where the string is not citation-shaped, so the caller can 404 rather than
    scan for a citation that cannot exist.

    The result is used only as a bound query parameter. Nothing here reaches query text.
    """
    tokens = [token for token in _CITATION_SEPARATORS.split(raw.strip()) if token]
    if not tokens:
        return None
    # A leading token like "RV1" is split so that "rv1.1.1" resolves too.
    head = tokens[0]
    match = re.fullmatch(r"([A-Za-z]+)(\d*)", head)
    if match is None:
        return None
    prefix = _CITATION_PREFIXES.get(match.group(1).upper())
    if prefix is None:
        return None
    rest = ([match.group(2)] if match.group(2) else []) + tokens[1:]
    words = [token.upper() for token in rest if token.isalpha()]
    numbers = [token for token in rest if token.isdigit()]
    if len(words) + len(numbers) != len(rest) or not numbers:
        return None
    return " ".join([prefix, *words, ".".join(numbers)])


# ---------------------------------------------------------------------------
# The service
# ---------------------------------------------------------------------------


class PassageService:
    """Every graph read for the works, passage, navigation, reader and parallel routes."""

    #: How many concepts, mentions, formulas and relations a passage detail returns per
    #: collection. Each set reports its own ``total`` so a truncated list is visible.
    ENTITY_LIMIT: Final = 25

    #: Ceiling on the formula-mediated fan-out. A formula occurring in several hundred
    #: passages would otherwise dominate the query's cost.
    FORMULA_FAN_OUT: Final = 4_000

    def __init__(self, repository: Repository) -> None:
        self._repository = repository

    # -- works -------------------------------------------------------------

    def works(self) -> list[WorkSummary]:
        rows = self._repository.run(_WORKS)
        return [self._work_summary(row) for row in rows]

    def work_detail(self, work_id: str) -> WorkDetail:
        row = self._repository.run_one(_WORK, work_id=work_id)
        if row is None:
            raise WorkNotFoundError(
                f"No work matches {work_id!r}.",
                hint="GET /api/v1/works lists the four work ids.",
            )
        summary = self._work_summary(row)
        structure = self._repository.run(_WORK_STRUCTURE, work_id=work_id)
        layer_rows = self._repository.run(
            _WORK_LAYERS,
            work_id=work_id,
            layer_relations=[spec.relation for spec in _LAYER_SPECS],
        )
        split_rows = self._repository.run(
            _WORK_ATTRIBUTION_SPLITS, work_id=work_id, split_relations=list(_SPLIT_RELATIONS)
        )
        script_row = self._repository.run_one(_WORK_SCRIPTS, work_id=work_id)
        measured = {str(item.get("relation")): item for item in layer_rows}
        splits = {str(item.get("relation")): item for item in split_rows}
        mantra_count = summary.mantra_count or 0

        return WorkDetail(
            **summary.model_dump(),
            scope=_nonempty(row.get("scope")),
            scope_source=_nonempty(row.get("scope_source")),
            scope_evidence=_nonempty(row.get("scope_evidence")),
            completeness=_nonempty(row.get("completeness")),
            rights=_nonempty(row.get("rights")),
            hierarchy=self._hierarchy_levels(structure),
            passage_counts_by_type=self._counts_by_type(structure),
            knowledge_layers=[
                self._layer_availability(spec, measured.get(spec.relation), mantra_count)
                for spec in _LAYER_SPECS
            ],
            attribution_splits=[
                self._attribution_split(relation, splits.get(relation))
                for relation in _SPLIT_RELATIONS
            ],
            translation_coverage=self._translation_coverage(row, summary),
            text_scripts=sorted(
                _SCRIPT_BY_GRAPH_VALUE.get(str(script), TextScript.UNKNOWN).value
                for script in (script_row or {}).get("scripts", [])
            ),
            coverage=CoverageView(
                vedas_in_scope=[summary.veda],
                vedas_not_covered=[
                    veda for veda in layer_figures.CORPUS_MANTRAS if veda != summary.veda
                ],
                measured={summary.veda: mantra_count},
                denominator=dict(layer_figures.CORPUS_MANTRAS),
            ),
        )

    def work_root(self, work_id: str, *, limit: int, offset: int) -> WorkRoot:
        detail_row = self._repository.run_one(_WORK, work_id=work_id)
        if detail_row is None:
            raise WorkNotFoundError(
                f"No work matches {work_id!r}.",
                hint="GET /api/v1/works lists the four work ids.",
            )
        row = self._repository.run_one(_WORK_ROOTS, work_id=work_id, limit=limit, offset=offset)
        items = [
            summary
            for summary in (_summary(item) for item in (row or {}).get("items", []))
            if summary is not None
        ]
        total = _as_int((row or {}).get("total"))
        levels = self._hierarchy_levels(self._repository.run(_WORK_STRUCTURE, work_id=work_id))
        status, caveats = paged_meaning(
            items,
            limit=limit,
            offset=offset,
            total=total,
            empty_status=KnowledgeStatus.INSUFFICIENT_EVIDENCE,
            empty_caveats=[
                CaveatView(
                    text="This work has no top-level container at all, which no work in "
                    "this corpus should be: the four enter at 10 Mandalas, 20 Kandas, 40 "
                    "Adhyayas and 4 Samavedic collections respectively.",
                    source="measured",
                )
            ],
        )
        return WorkRoot(
            work_id=work_id,
            veda=str(detail_row.get("veda") or ""),
            display_label=str(detail_row.get("display_label") or work_id),
            traditional_name=_nonempty(detail_row.get("work_name")),
            root_level=levels[0] if levels else None,
            results=paginate(
                items,
                limit=limit,
                offset=offset,
                total=total,
                data_status=status,
                caveats=caveats,
            ),
        )

    def _work_summary(self, row: dict[str, Any]) -> WorkSummary:
        """Build the summary, keeping the honest label and the traditional name apart."""
        work_id = str(row.get("work_id") or "")
        mantra_count = _as_int(row.get("mantra_count"))
        translated = _as_int(row.get("translated_count"))
        caveats: list[CaveatView] = []
        status = KnowledgeStatus.SUPPORTED
        if mantra_count and translated == 0:
            status = KnowledgeStatus.PARTIAL
            caveats.append(
                CaveatView(
                    text=(
                        f"This work has {mantra_count:,} mantras and zero released "
                        "translations, so every translation-derived layer is empty for it. "
                        "None of those empty results is a statement about the text."
                    ),
                    source="measured",
                )
            )
        return WorkSummary(
            work_id=work_id,
            veda=str(row.get("veda") or ""),
            abbreviation=_nonempty(row.get("abbreviation")),
            display_label=str(row.get("display_label") or row.get("work_name") or work_id),
            traditional_name=_nonempty(row.get("work_name")),
            recension=self._recension_code(work_id),
            excluded_corpora=[str(item) for item in row.get("excluded_corpora") or []],
            passage_count=_as_int(row.get("passage_count")),
            mantra_count=mantra_count,
            translated_mantra_count=translated,
            data_status=status,
            caveats=caveats,
        )

    @staticmethod
    def _recension_code(work_id: str) -> str | None:
        """The recension segment of the work id, e.g. ``KAU``.

        A code and not a name. The registry records *Kauthuma*, *Shakala*, *Madhyandina*
        and *Shaunaka*, but the frozen ``Work`` node carries no ``recension`` property, so
        naming them here would mean typing knowledge the graph does not hold. The
        human-readable recension is inside ``display_label`` and ``scope``, both of which
        this endpoint returns verbatim.
        """
        parts = work_id.split(":")
        return parts[3] if len(parts) >= 4 else None

    def _hierarchy_levels(self, structure: list[dict[str, Any]]) -> list[HierarchyLevel]:
        """The work's levels, ordered, with a count of passages bottoming out at each.

        Built from the union of the shapes ``_WORK_STRUCTURE`` returns and then sorted by
        :data:`LEVEL_ORDER`, so the Samaveda's five levels come back in traditional depth
        order even though its four collections nest to four different depths.
        """
        types_by_level: dict[str, set[str]] = {}
        counts: dict[str, int] = {}
        for row in structure:
            passage_type = str(row.get("passage_type") or "UNKNOWN")
            passages = _as_int(row.get("passages")) or 0
            shapes = [row.get("first_shape"), row.get("last_shape")]
            deepest: str | None = None
            for shape in shapes:
                keys = order_levels(list(_hierarchy_map(shape)))
                for key in keys:
                    types_by_level.setdefault(key, set()).add(passage_type)
                if keys:
                    deepest = keys[-1]
            if deepest is not None:
                counts[deepest] = counts.get(deepest, 0) + passages
        return [
            HierarchyLevel(
                key=key,
                native_label=NATIVE_LEVEL_LABELS.get(key),
                depth=depth,
                value_kind="NAME" if key in NAME_VALUED_LEVELS else "ORDINAL",
                passage_types=sorted(types_by_level[key]),
                passage_count=counts.get(key),
                status=(
                    KnowledgeStatus.SUPPORTED
                    if key in NATIVE_LEVEL_LABELS
                    else KnowledgeStatus.INSUFFICIENT_EVIDENCE
                ),
            )
            for depth, key in enumerate(order_levels(list(types_by_level)), start=1)
        ]

    @staticmethod
    def _counts_by_type(structure: list[dict[str, Any]]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for row in structure:
            passage_type = str(row.get("passage_type") or "UNKNOWN")
            counts[passage_type] = counts.get(passage_type, 0) + (_as_int(row.get("passages")) or 0)
        return counts

    @staticmethod
    def _layer_availability(
        spec: LayerSpec, row: dict[str, Any] | None, mantra_count: int
    ) -> LayerAvailability:
        """One measured layer row. A layer with no edges is ``NOT_BUILT`` for this work.

        ``NOT_BUILT`` and not zero-with-SUPPORTED: the Yajurveda's absence from the deity
        ascription layer is a fact about the Anukramani apparatus, and reporting it as a
        measured zero invites the reading that its verses address no deity.
        """
        passages = _as_int((row or {}).get("passages")) or 0
        edges = _as_int((row or {}).get("edges")) or 0
        reaches = edges > 0
        return LayerAvailability(
            layer=spec.layer,
            relation=spec.relation,
            status=KnowledgeStatus.SUPPORTED if reaches else KnowledgeStatus.NOT_BUILT,
            passages=passages if reaches else None,
            edges=edges if reaches else None,
            share_of_mantras=(
                round(passages / mantra_count, 4) if reaches and mantra_count else None
            ),
            note=spec.absence_note,
        )

    @staticmethod
    def _attribution_split(relation: str, row: dict[str, Any] | None) -> AttributionSplit:
        source_stated = _as_int((row or {}).get("source_stated"))
        inherited = _as_int((row or {}).get("container_inherited"))
        present = bool(_as_int((row or {}).get("edges")) or 0)
        return AttributionSplit(
            layer=relation,
            source_stated=source_stated if present else None,
            container_inherited=inherited if present else None,
            status=KnowledgeStatus.SUPPORTED if present else KnowledgeStatus.NOT_BUILT,
            note=_INHERITANCE_NOTE,
        )

    @staticmethod
    def _translation_coverage(row: dict[str, Any], summary: WorkSummary) -> TranslationCoverage:
        """Translation coverage, with the percentage computed here and not transcribed.

        The percentage is divided from the two counts in the same response. Copying the
        figure out of the work's ``completeness`` prose is what let three caveats in this
        repository drift from the data they described.
        """
        mantras = summary.mantra_count
        translated = summary.translated_mantra_count
        percent = (
            round(100 * translated / mantras, 2) if mantras and translated is not None else None
        )
        caveats = [
            CaveatView(
                text=(
                    "Every translation in this graph is MACHINE_ALIGNED: a public-domain "
                    "translation matched to a canonical key without review against the "
                    "Sanskrit. Coverage measures alignment, not translation quality."
                ),
                source="measured",
            )
        ]
        status = KnowledgeStatus.SUPPORTED
        if translated == 0:
            status = KnowledgeStatus.NOT_BUILT
            caveats.append(
                CaveatView(
                    text=(
                        f"Zero of this work's {mantras:,} mantras carry a translation. "
                        "Every layer derived from the English translation is therefore "
                        "empty for this corpus, and none of those absences is textual."
                    ),
                    source="measured",
                )
            )
        elif percent is not None and percent < 100:
            status = KnowledgeStatus.PARTIAL
        return TranslationCoverage(
            mantras=mantras,
            translated=translated,
            percent=percent,
            translators=sorted(str(item) for item in row.get("translators") or []),
            status=status,
            caveats=caveats,
        )

    # -- key resolution ----------------------------------------------------

    def resolve(self, raw: str) -> str:
        """A client's passage reference resolved to a canonical key, or 404.

        Tries the indexed lookups first and reaches the unindexed citation scan only when
        the string is not a key or a URN, so the common case is a single index hit.
        """
        value = raw.strip()
        if not value:
            raise PassageNotFoundError("No passage reference was given.", hint=_KEY_HINT)
        if value.startswith("VG:"):
            row = self._repository.run_one(_RESOLVE_BY_KEY, key=value)
            if row is not None:
                return str(row["canonical_key"])
        elif value.startswith("urn:"):
            row = self._repository.run_one(_RESOLVE_BY_URN, key=value)
            if row is not None:
                return str(row["canonical_key"])
        else:
            citation = citation_candidate(value)
            if citation is not None:
                row = self._repository.run_one(_RESOLVE_BY_CITATION, citation=citation)
                if row is not None:
                    return str(row["canonical_key"])
        raise PassageNotFoundError(f"No passage matches {value!r}.", hint=_KEY_HINT)

    def summary(self, key: str) -> PassageSummary:
        row = self._repository.run_one(_PASSAGE_BY_KEY, key=key)
        return _require_summary((row or {}).get("passage"), key)

    # -- detail ------------------------------------------------------------

    def detail(
        self, key: str, *, certainty: MentionCertainty = MentionCertainty.DEFAULT
    ) -> PassageDetail:
        """The full passage record. ``certainty`` governs the deity *mention* set only.

        It does not touch ``devatas``, which is the Anukramani's ascription and carries no
        referent grade -- the ascription names an addressee rather than matching a word, so
        there is nothing there to be ambiguous about.
        """
        row = self._repository.run_one(
            _DETAIL,
            key=key,
            entity_limit=self.ENTITY_LIMIT,
            semantic_relations=list(_SEMANTIC_RELATIONS),
        )
        if row is None:
            raise PassageNotFoundError(f"No passage matches {key!r}.", hint=_KEY_HINT)
        passage = _require_summary(row.get("passage"), key)
        is_container = passage.passage_type != "MANTRA"
        breadcrumbs, breadcrumb_caveats = self._breadcrumbs(passage)
        counts = _parallel_counts(
            self._repository.run(
                _PARALLEL_COUNTS, key=key, parallel_predicates=list(_PARALLEL_PREDICATES)
            )
        )
        text = _text_availability(row.get("text_versions"), is_container=is_container)
        caveats = [*breadcrumb_caveats]
        return PassageDetail(
            canonical_key=passage.canonical_key,
            canonical_citation=passage.canonical_citation,
            canonical_urn=passage.canonical_urn,
            entity_id=passage.entity_id,
            display_label=passage.display_label,
            passage_type=passage.passage_type,
            veda=passage.veda,
            work_id=passage.work_id,
            work_display_label=_nonempty(row.get("work_display_label")),
            work_traditional_name=_nonempty(row.get("work_traditional_name")),
            recension=self._recension_code(passage.work_id),
            native_hierarchy=breadcrumbs,
            structural_path=[crumb.value for crumb in breadcrumbs],
            parent=_summary(row.get("parent")),
            child_count=_as_int(row.get("child_count")),
            sequence_in_parent=passage.sequence_in_parent,
            text=text,
            translations=self._translation_set(row.get("translations"), passage),
            rishis=self._attribution_set("HAS_RISHI", row.get("rishis"), passage),
            devatas=self._attribution_set("HAS_DEVATA", row.get("devatas"), passage),
            chandas=self._attribution_set("HAS_CHANDAS", row.get("chandas"), passage),
            mentioned_devatas=self._mentioned_devata_set(row.get("mentioned_devatas"), certainty),
            concepts=self._entity_set(
                row.get("concepts"), row.get("concept_total"), "ABOUT_CONCEPT", is_container
            ),
            mentioned_entities=self._entity_set(
                row.get("mentioned_entities"),
                row.get("mention_total"),
                "MENTIONS_ENTITY",
                is_container,
            ),
            formulas=self._entity_set(
                row.get("formulas"), row.get("formula_total"), "USES_FORMULA", is_container
            ),
            semantic_relations=self._semantic_relation_set(
                row.get("semantic_relations"), row.get("relation_total"), is_container
            ),
            agentive_assertions=self._assertion_set(
                row.get("agentive_assertions"), row.get("assertion_total"), passage
            ),
            parallel_counts=counts,
            audio=AudioAvailability(),
            provenance=PassageProvenance(
                work_id=passage.work_id,
                recension=self._recension_code(passage.work_id),
                text_sources=sorted(
                    {surface.source_id for surface in text.surfaces if surface.source_id}
                ),
                translation_sources=sorted(
                    {
                        item.source_id
                        for item in _translations(row.get("translations"))
                        if item.source_id
                    }
                ),
                rights=sorted(
                    {surface.rights_status for surface in text.surfaces if surface.rights_status}
                ),
                status=_nonempty(row.get("status")) or "CANONICAL",
            ),
            data_status=KnowledgeStatus.SUPPORTED,
            caveats=caveats,
        )

    # -- navigation --------------------------------------------------------

    def parent(self, key: str) -> NavigationResult:
        passage = self.summary(key)
        parent = (
            _summary(
                (self._repository.run_one(_PASSAGE_BY_KEY, key=passage.parent_key) or {}).get(
                    "passage"
                )
            )
            if passage.parent_key
            else None
        )
        items = [parent] if parent is not None else []
        caveats = (
            []
            if parent is not None
            else [
                CaveatView(
                    text=(
                        "This passage is a top-level container of its work, so it has no "
                        "parent passage. Its parent is the work itself: "
                        f"GET /api/v1/works/{passage.work_id}."
                    ),
                    source="measured",
                )
            ]
        )
        level_key = self._deepest_level(parent) if parent is not None else None
        return NavigationResult(
            of=passage,
            relation=NavigationRelation.PARENT,
            level_key=level_key,
            native_label=NATIVE_LEVEL_LABELS.get(level_key or ""),
            results=paginate(items, limit=1, offset=0, total=len(items), caveats=caveats),
        )

    def children(self, key: str, *, limit: int, offset: int) -> NavigationResult:
        passage = self.summary(key)
        row = self._repository.run_one(_CHILDREN, key=key, limit=limit, offset=offset)
        return self._navigation(
            passage,
            NavigationRelation.CHILDREN,
            row,
            limit=limit,
            offset=offset,
            empty_caveat=(
                "This passage contains no further passages: it is a mantra, the deepest "
                "level of its work. Its text is in the `text` block of "
                f"GET /api/v1/passages/{passage.canonical_key}."
            ),
        )

    def siblings(self, key: str, *, limit: int, offset: int) -> NavigationResult:
        passage = self.summary(key)
        if passage.parent_key is None:
            return NavigationResult(
                of=passage,
                relation=NavigationRelation.SIBLINGS,
                level_key=self._deepest_level(passage),
                native_label=NATIVE_LEVEL_LABELS.get(self._deepest_level(passage) or ""),
                results=paginate(
                    [],
                    limit=limit,
                    offset=offset,
                    total=0,
                    data_status=KnowledgeStatus.PARTIAL,
                    caveats=[
                        CaveatView(
                            text="This passage is a top-level container, so its siblings are "
                            "the work's other top-level containers: "
                            f"GET /api/v1/works/{passage.work_id}/root.",
                            source="measured",
                        )
                    ],
                ),
            )
        row = self._repository.run_one(
            _SIBLINGS, parent_key=passage.parent_key, key=key, limit=limit, offset=offset
        )
        return self._navigation(
            passage,
            NavigationRelation.SIBLINGS,
            row,
            limit=limit,
            offset=offset,
            empty_caveat=(
                "This passage is the only one inside its container, so it has no siblings. "
                "The anchor passage is always excluded from its own sibling list."
            ),
        )

    def _navigation(
        self,
        passage: PassageSummary,
        relation: NavigationRelation,
        row: dict[str, Any] | None,
        *,
        limit: int,
        offset: int,
        empty_caveat: str,
    ) -> NavigationResult:
        items = [
            summary
            for summary in (_summary(item) for item in (row or {}).get("items", []))
            if summary is not None
        ]
        total = _as_int((row or {}).get("total"))
        level_key = self._deepest_level(items[0]) if items else None
        # Both the status and the prose come from `total`. Deriving them from the page made
        # /passages/VG:AV:SAU:K20/children?offset=99999 answer "this passage contains no
        # further passages: it is a mantra" about a Kanda holding 143 Suktas.
        status, caveats = paged_meaning(
            items,
            limit=limit,
            offset=offset,
            total=total,
            empty_status=KnowledgeStatus.PARTIAL,
            empty_caveats=[CaveatView(text=empty_caveat, source="measured")],
        )
        return NavigationResult(
            of=passage,
            relation=relation,
            level_key=level_key,
            native_label=NATIVE_LEVEL_LABELS.get(level_key or ""),
            results=paginate(
                items,
                limit=limit,
                offset=offset,
                total=total,
                data_status=status,
                caveats=caveats,
            ),
        )

    @staticmethod
    def _deepest_level(passage: PassageSummary | None) -> str | None:
        if passage is None:
            return None
        levels = order_levels(list(passage.hierarchy))
        return levels[-1] if levels else None

    def _breadcrumbs(
        self, passage: PassageSummary
    ) -> tuple[list[BreadcrumbView], list[CaveatView]]:
        """The passage's position, one crumb per level, innermost crumb being itself.

        The container nodes are fetched and paired with the levels by depth. The pairing is
        checked rather than assumed: where the number of ancestors plus one does not equal
        the number of levels, the crumbs are still returned with their level names and
        values and the response says the container links are missing, which is better than
        a breadcrumb trail pointing at the wrong Sukta.
        """
        levels = order_levels(list(passage.hierarchy))
        caveats: list[CaveatView] = []
        unknown = [key for key in levels if key not in NATIVE_LEVEL_LABELS]
        if unknown:
            caveats.append(
                CaveatView(
                    text=(
                        "This passage carries structural levels this API cannot name: "
                        f"{', '.join(sorted(unknown))}. They are returned with a null "
                        "native_label rather than dropped, but their position in the "
                        "hierarchy is not established."
                    ),
                    source="measured",
                )
            )
        ancestor_row = self._repository.run_one(_ANCESTORS, key=passage.canonical_key)
        ancestors = [
            summary
            for summary in (_summary(item) for item in (ancestor_row or {}).get("ancestors", []))
            if summary is not None
        ]
        chain: list[PassageSummary | None] = [*ancestors, passage]
        if len(chain) != len(levels):
            caveats.append(
                CaveatView(
                    text=(
                        f"This passage sits at {len(levels)} structural levels but "
                        f"{len(ancestors)} containers were found above it, so the "
                        "breadcrumbs carry level names and values without container links."
                    ),
                    source="measured",
                )
            )
            chain = [None] * (len(levels) - 1) + [passage]
        crumbs: list[BreadcrumbView] = []
        for depth, (level_key, node) in enumerate(zip(levels, chain, strict=False), start=1):
            crumbs.append(
                BreadcrumbView(
                    level_key=level_key,
                    native_label=NATIVE_LEVEL_LABELS.get(level_key),
                    value=passage.hierarchy.get(level_key, ""),
                    depth=depth,
                    canonical_key=node.canonical_key if node is not None else None,
                    canonical_citation=node.canonical_citation if node is not None else None,
                    display_label=node.display_label if node is not None else None,
                    passage_type=node.passage_type if node is not None else None,
                )
            )
        return crumbs, caveats

    # -- reader ------------------------------------------------------------

    def reader(
        self, key: str, *, certainty: MentionCertainty = MentionCertainty.DEFAULT
    ) -> ReaderPayload:
        """One compact payload for a reader view. ``certainty`` governs mentioned deities.

        The reader carries ``mentioned_devatas`` as well as ``devatas`` because the two
        answer different questions and only one of them reaches the whole corpus: the
        ascription layer is Rigveda-only, so for a Samavedic, Yajurvedic or Atharvavedic
        verse the mention set is the only deity signal a reading page can show. It was
        already being queried here and discarded.
        """
        row = self._repository.run_one(
            _READER,
            key=key,
            entity_limit=self.ENTITY_LIMIT,
            parallel_predicates=list(_PARALLEL_PREDICATES),
        )
        if row is None:
            raise PassageNotFoundError(f"No passage matches {key!r}.", hint=_KEY_HINT)
        passage = _require_summary(row.get("passage"), key)
        is_container = passage.passage_type != "MANTRA"
        breadcrumbs, caveats = self._breadcrumbs(passage)
        text = _text_availability(row.get("text_versions"), is_container=is_container)
        previous, following, neighbour_note = self.neighbours(passage)
        return ReaderPayload(
            canonical_key=passage.canonical_key,
            canonical_citation=passage.canonical_citation,
            canonical_urn=passage.canonical_urn,
            display_label=passage.display_label,
            passage_type=passage.passage_type,
            veda=passage.veda,
            work_id=passage.work_id,
            work_display_label=_nonempty(row.get("work_display_label")),
            breadcrumbs=breadcrumbs,
            primary_text=next(
                (surface for surface in text.surfaces if surface.is_displayable), None
            ),
            text=text,
            translations=self._translation_set(row.get("translations"), passage),
            rishis=self._attribution_set("HAS_RISHI", row.get("rishis"), passage),
            devatas=self._attribution_set("HAS_DEVATA", row.get("devatas"), passage),
            chandas=self._attribution_set("HAS_CHANDAS", row.get("chandas"), passage),
            mentioned_devatas=self._mentioned_devata_set(row.get("mentioned_devatas"), certainty),
            major_concepts=self._entity_set(
                row.get("concepts"), row.get("concept_total"), "ABOUT_CONCEPT", is_container
            ),
            previous=previous,
            next=following,
            neighbour_note=neighbour_note,
            audio=AudioAvailability(),
            parallel_counts=_parallel_counts(
                [
                    item
                    for item in row.get("parallel_counts") or []
                    if isinstance(item, dict) and item.get("predicate")
                ]
            ),
            graph_neighbour_count=_as_int(row.get("graph_neighbour_count")),
            data_status=KnowledgeStatus.SUPPORTED,
            caveats=caveats,
        )

    def neighbours(
        self, passage: PassageSummary
    ) -> tuple[PassageSummary | None, PassageSummary | None, str | None]:
        """The passage before and after this one in reading order.

        Two queries. The first finds the top-level container this passage sits under and
        the containers stored either side of it; the second offers four ranked candidates
        and lets a within-container neighbour beat a cross-container one. Both directions
        can legitimately be null -- at the first and last passage of a work -- and the note
        says which case a null is.
        """
        context = self._repository.run_one(_NEIGHBOUR_CONTEXT, key=passage.canonical_key)
        if context is None or not context.get("root_key"):
            return (
                None,
                None,
                (
                    "This passage has no containing structure in the graph, so reading order "
                    "could not be established for it."
                ),
            )
        rows = self._repository.run(
            _NEIGHBOURS,
            key=passage.canonical_key,
            work_id=str(context.get("work_id") or passage.work_id),
            display_type=passage.passage_type,
            root_key=str(context["root_key"]),
            next_root=context.get("next_root"),
            previous_root=context.get("previous_root"),
        )
        best: dict[str, PassageSummary] = {}
        for row in sorted(rows, key=lambda item: _as_int(item.get("rank")) or 0):
            direction = str(row.get("direction"))
            if direction not in best:
                summary = _summary(row.get("passage"))
                if summary is not None:
                    best[direction] = summary
        previous = best.get("PREVIOUS")
        following = best.get("NEXT")
        note = None
        if previous is None and following is None:
            note = "This is the only passage at its level in this work."
        elif previous is None:
            note = (
                "This is the first passage at its level in this work, so there is no "
                "previous one. A null neighbour here is the start of the corpus."
            )
        elif following is None:
            note = (
                "This is the last passage at its level in this work, so there is no "
                "next one. A null neighbour here is the end of the corpus."
            )
        return previous, following, note

    # -- parallels ---------------------------------------------------------

    def parallels(
        self, key: str, *, filters: tuple[ParallelFilter, ...], limit: int, offset: int
    ) -> Paginated[ParallelView]:
        """Related passages, traversed undirected, with the relation kind on every row.

        ``filter=formula`` runs a different query because it is a different question: it
        asks which passages use the same ``Formula``, which is mediated by a node rather
        than stored as an edge between the two passages.
        """
        limit = min(limit, MAX_PAGE_SIZE)
        selected = filters or (
            ParallelFilter.EXACT,
            ParallelFilter.NEAR,
            ParallelFilter.REUSE,
            ParallelFilter.VARIANT,
            ParallelFilter.VOCABULARY,
        )
        same_veda_only = ParallelFilter.SAME_VEDA in selected
        cross_veda_only = ParallelFilter.CROSS_VEDA in selected
        # Refused rather than answered with an empty page. Asking for parallels that are
        # both inside and across a corpus has no rows by construction, and returning zero
        # would be a confident "this passage has no parallels" for a request that never
        # had an answer -- the exact shape this API exists to refuse.
        if same_veda_only and cross_veda_only:
            raise BadRequestError(
                "filter=same_veda and filter=cross_veda exclude each other: no parallel is "
                "both within one Veda and across two.",
                hint="Ask for one of them, or omit both for every parallel.",
            )
        # Refused rather than silently dropped. `formula` selects no stored predicate, so
        # combining it with `near` would run the near-parallel query alone and answer as
        # though the formula question had been asked and found nothing.
        if ParallelFilter.FORMULA in selected and not set(selected) <= {
            ParallelFilter.FORMULA,
            ParallelFilter.SAME_VEDA,
            ParallelFilter.CROSS_VEDA,
        }:
            raise BadRequestError(
                "filter=formula cannot be combined with a stored parallel predicate: it is "
                "formula-mediated rather than an edge between two passages, so the two are "
                "different queries.",
                hint="Request filter=formula on its own, optionally with same_veda or cross_veda.",
            )
        predicates = sorted(
            {predicate for chosen in selected for predicate in _FILTER_PREDICATES[chosen]}
        )
        if ParallelFilter.FORMULA in selected:
            return self._formula_parallels(
                key,
                limit=limit,
                offset=offset,
                same_veda_only=same_veda_only,
                cross_veda_only=cross_veda_only,
            )
        row = self._repository.run_one(
            _PARALLELS,
            key=key,
            predicates=predicates,
            same_veda_only=same_veda_only,
            cross_veda_only=cross_veda_only,
            limit=limit,
            offset=offset,
        )
        items = [
            view
            for view in (
                _parallel_view(item)
                for item in (row or {}).get("items", [])
                if isinstance(item, dict)
            )
            if view is not None
        ]
        caveats = [CaveatView(text=_UNDIRECTED_CAVEAT, source="measured")]
        if any(not view.is_textual_parallelism for view in items) or (
            ParallelFilter.VOCABULARY in selected
        ):
            caveats.append(CaveatView(text=_VOCABULARY_CAVEAT, source="measured"))
        if ParallelFilter.REUSE in selected:
            caveats.append(
                CaveatView(text=named_query_caveat("sv_reuse_of_rv"), source="sv_reuse_of_rv")
            )
        total = _as_int((row or {}).get("total"))
        status, paging_caveats = paged_meaning(
            items,
            limit=limit,
            offset=offset,
            total=total,
            empty_status=KnowledgeStatus.INSUFFICIENT_EVIDENCE,
            empty_caveats=[
                CaveatView(
                    text=(
                        "No parallel of the requested kinds was found for this passage. "
                        "The parallel layer is derived by string comparison over the "
                        "corpus, so this is a limit of that matcher and not evidence that "
                        "the verse is unparalleled in the Vedic tradition. Try "
                        "filter=formula, which asks a different question through shared "
                        "wording rather than whole-verse similarity."
                    ),
                    source="measured",
                )
            ],
        )
        return paginate(
            items,
            limit=limit,
            offset=offset,
            total=total,
            data_status=status,
            caveats=caveats + paging_caveats,
        )

    def _formula_parallels(
        self,
        key: str,
        *,
        limit: int,
        offset: int,
        same_veda_only: bool,
        cross_veda_only: bool,
    ) -> Paginated[ParallelView]:
        row = self._repository.run_one(
            _FORMULA_PARALLELS,
            key=key,
            limit=limit,
            offset=offset,
            fan_out=self.FORMULA_FAN_OUT,
            same_veda_only=same_veda_only,
            cross_veda_only=cross_veda_only,
        )
        items = [
            view
            for view in (
                _formula_parallel_view(item)
                for item in (row or {}).get("items", [])
                if isinstance(item, dict)
            )
            if view is not None
        ]
        caveats = [CaveatView(text=_FORMULA_MEDIATED_CAVEAT, source="measured")]
        total = _as_int((row or {}).get("total"))
        status, paging_caveats = paged_meaning(
            items,
            limit=limit,
            offset=offset,
            total=total,
            empty_status=KnowledgeStatus.INSUFFICIENT_EVIDENCE,
            empty_caveats=[
                CaveatView(
                    text=(
                        "This passage shares no Formula with another passage. Formulas are "
                        "recurring word sequences found by n-gram matching, so a verse with "
                        "none is a verse whose wording that matcher found nowhere else, not "
                        "a verse of unique diction."
                    ),
                    source="measured",
                )
            ],
        )
        return paginate(
            items,
            limit=limit,
            offset=offset,
            total=total,
            data_status=status,
            caveats=caveats + paging_caveats,
        )

    # -- set builders ------------------------------------------------------

    def _translation_set(
        self, rows: object, passage: PassageSummary
    ) -> AttestedSet[TranslationView]:
        """Translations, with the Samavedic zero named as a corpus fact.

        The whole reason this is not a bare list: the Samaveda has 0 translations from
        1,844 verses, so ``[]`` there means no translation was ever released for the
        corpus. For the other three it means this particular verse is unaligned, which is
        ``INSUFFICIENT_EVIDENCE`` rather than ``NOT_BUILT``.
        """
        items = _translations(rows)
        if items:
            return AttestedSet[TranslationView](items=items, total=len(items))
        if passage.passage_type != "MANTRA":
            return AttestedSet[TranslationView](
                items=[],
                total=0,
                data_status=KnowledgeStatus.NOT_BUILT,
                caveats=[
                    CaveatView(
                        text="Translations are aligned to mantras, not to containers. Ask "
                        "for this passage's children.",
                        source="measured",
                    )
                ],
            )
        if passage.veda == "SV":
            return AttestedSet[TranslationView](
                items=[],
                total=0,
                data_status=KnowledgeStatus.NOT_BUILT,
                coverage=CoverageView(
                    vedas_in_scope=["RV", "AV", "YV"],
                    vedas_not_covered=["SV"],
                    denominator=dict(layer_figures.CORPUS_MANTRAS),
                ),
                caveats=[
                    CaveatView(
                        text=(
                            "Zero translations are released for the Samaveda: none of its "
                            "1,844 verses carries one. This empty list is an unbuilt layer "
                            "for the whole corpus and says nothing about this verse."
                        ),
                        source="measured",
                    )
                ],
            )
        return AttestedSet[TranslationView](
            items=[],
            total=0,
            data_status=KnowledgeStatus.INSUFFICIENT_EVIDENCE,
            caveats=[
                CaveatView(
                    text=(
                        "No translation is aligned to this verse, although its corpus is "
                        "translated: coverage is 10,502 of 10,552 for the Rigveda, 1,903 "
                        "of 1,975 for the Yajurveda and 4,878 of 5,839 for the "
                        "Atharvaveda. This is an alignment gap, not an untranslated verse."
                    ),
                    source="measured",
                )
            ],
        )

    @staticmethod
    def _mentioned_devata_set(rows: object, certainty: MentionCertainty) -> MentionedDevataSet:
        """Deities named in a passage, with the ambiguity contract applied.

        This method is the fix for a real defect. It previously ran through
        :meth:`_attribution_set`, which projected no grade and attached a caveat only on
        the *empty* branch -- so a populated list of purely ambiguous mentions asserted
        them as fact. RV 1.4.2 has one mention edge, graded ``DEITY_AMBIGUOUS``, and the
        reading page reported the god Soma as named there with nothing saying the grader
        was unsure. 5,365 passages carry at least one ambiguous mention and 2,997 carry
        nothing else, so for those 2,997 the entire deity list was ungraded guesswork.

        Three rules, in order:

        *Count before filtering.* All three tiers are counted over every row, so the
        response can state what the default withheld. A count of the filtered rows alone
        would make the exclusion invisible.

        *Filter through the frozen tier sets.* The included tiers come from
        :func:`vedagraph.domain.theonyms.referent_tiers_for_mode`, which is measured against
        the gold set -- CERTAIN+PROBABLE score 0.9742 against 0.6142 for what is left in
        AMBIGUOUS. Hand-rolling the tier set here would fork it from the figure that
        justifies it, and an unknown mode raises there rather than widening the filter.

        *An emptied list is not an empty one.* Where filtering removed everything, the
        status is ``INSUFFICIENT_EVIDENCE`` -- evidence exists and cannot support the claim
        -- and never a bare empty list, which would read as "no deity is named here".
        """
        graded = [
            row
            for row in (rows if isinstance(rows, list) else [])
            if isinstance(row, dict) and row.get("id")
        ]
        tiers = theonyms.referent_tiers_for_mode(certainty.value)
        counts = ReferentCertaintyCounts(
            certain_count=sum(
                1 for row in graded if row.get("referent_certainty") == theonyms.CERTAIN
            ),
            probable_count=sum(
                1 for row in graded if row.get("referent_certainty") == theonyms.PROBABLE
            ),
            ambiguous_count=sum(
                1 for row in graded if row.get("referent_certainty") == theonyms.AMBIGUOUS
            ),
            included_tiers=sorted(tiers),
        )
        included = [row for row in graded if row.get("referent_certainty") in tiers]
        excluded = len(graded) - len(included)

        items = [
            MentionedDevataView(
                type="DEVATA",
                id=str(row["id"]),
                display_label=str(row.get("display_label") or row["id"]),
                subtitle=_nonempty(row.get("subtitle")),
                attribution_precision=_nonempty(row.get("attribution_precision")),
                evidence_basis=_evidence_basis(
                    row.get("evidence_basis"), row.get("attribution_precision")
                ),
                # Never defaulted. An unrecognised grade is reported as unknown *and* marked
                # ambiguous, so a tier this API does not know cannot arrive looking certain.
                referent_certainty=str(row.get("referent_certainty") or "UNKNOWN"),
                is_ambiguous=row.get("referent_certainty") != theonyms.CERTAIN
                and row.get("referent_certainty") != theonyms.PROBABLE,
                occurrences=_as_int(row.get("occurrences")),
            )
            for row in included
        ]

        caveats: list[CaveatView] = []
        status = KnowledgeStatus.SUPPORTED
        if not graded:
            status = KnowledgeStatus.INSUFFICIENT_EVIDENCE
            caveats.append(CaveatView(text=_NO_MENTION_MATCHED_CAVEAT, source="measured"))
        elif not items:
            status = KnowledgeStatus.INSUFFICIENT_EVIDENCE
            caveats.append(CaveatView(text=_ALL_MENTIONS_AMBIGUOUS_CAVEAT, source="measured"))
        elif excluded:
            # A real answer over one evidence mode, which is what PARTIAL means.
            status = KnowledgeStatus.PARTIAL
        if counts.ambiguous_count:
            caveats.append(CaveatView(text=_AMBIGUITY_CONTRACT_CAVEAT, source="measured"))
        return MentionedDevataSet(
            items=items,
            total=len(items),
            data_status=status,
            caveats=caveats,
            certainty=counts,
            included_certainty=certainty,
            excluded_count=excluded,
        )

    @staticmethod
    def _attribution_set(
        relation: str, rows: object, passage: PassageSummary
    ) -> AttestedSet[AttributedRef]:
        """One attribution axis, with an out-of-scope corpus named as such.

        This is the method that stops a Yajurvedic verse reporting "no deity". Its empty
        ``HAS_DEVATA`` list gets ``NOT_BUILT`` plus the frozen scope caveat, so a reader
        sees that the Anukramani ascription layer does not reach that corpus rather than
        that the verse addresses no god.
        """
        items = _attributed(rows)
        if items:
            return AttestedSet[AttributedRef](
                items=items,
                total=len(items),
                caveats=[CaveatView(text=_INHERITANCE_NOTE, source="measured")]
                if any(item.attribution_precision == "CONTAINER_INHERITED" for item in items)
                else [],
            )
        caveat_text = named_query_caveat(_LAYER_CAVEAT_QUERIES.get(relation, ""))
        source = _LAYER_CAVEAT_QUERIES.get(relation, "measured")
        if not caveat_text:
            caveat_text = (
                f"No {relation} attribution is recorded for this passage. An absent "
                "attribution is a gap in an annotation layer and not a statement that the "
                "text lacks the thing."
            )
            source = "measured"
        return AttestedSet[AttributedRef](
            items=[],
            total=0,
            data_status=KnowledgeStatus.NOT_BUILT,
            coverage=CoverageView(
                vedas_not_covered=[passage.veda],
                denominator=dict(layer_figures.CORPUS_MANTRAS),
            ),
            caveats=[CaveatView(text=caveat_text, source=source)],
        )

    @staticmethod
    def _entity_set(
        rows: object, total: object, relation: str, is_container: bool
    ) -> AttestedSet[EntityRef]:
        items = _entity_refs(rows)
        if items:
            return AttestedSet[EntityRef](items=items, total=_as_int(total) or len(items))
        return AttestedSet[EntityRef](
            items=[],
            total=0,
            data_status=(
                KnowledgeStatus.NOT_BUILT if is_container else KnowledgeStatus.INSUFFICIENT_EVIDENCE
            ),
            caveats=[
                CaveatView(
                    text=(
                        f"{relation} links mantras to registry entities and not containers "
                        "to them. Ask for this passage's children."
                        if is_container
                        else f"The {relation} layer matched nothing in this passage. It "
                        "matches against a fixed registry of named entities, so this is a "
                        "limit of that registry and of the matcher, not a verse without "
                        "subject matter."
                    ),
                    source="measured",
                )
            ],
        )

    @staticmethod
    def _semantic_relation_set(
        rows: object, total: object, is_container: bool
    ) -> AttestedSet[SemanticRelationView]:
        items: list[SemanticRelationView] = []
        for item in rows if isinstance(rows, list) else []:
            if not isinstance(item, dict) or not item.get("relation"):
                continue
            target = _entity_refs([item.get("target")])
            if not target:
                continue
            items.append(
                SemanticRelationView(
                    relation=str(item["relation"]),
                    target=target[0],
                    attribution_precision=_nonempty(item.get("attribution_precision")),
                    evidence_basis=_nonempty(item.get("evidence_basis")),
                    quality_tier=_nonempty(item.get("quality_tier")),
                    state=_nonempty(item.get("state")),
                    confidence=_as_float(item.get("confidence")),
                    knowledge_layer=_nonempty(item.get("knowledge_layer")),
                )
            )
        if items:
            return AttestedSet[SemanticRelationView](
                items=items, total=_as_int(total) or len(items)
            )
        return AttestedSet[SemanticRelationView](
            items=[],
            total=0,
            data_status=(
                KnowledgeStatus.NOT_BUILT if is_container else KnowledgeStatus.INSUFFICIENT_EVIDENCE
            ),
            caveats=[
                CaveatView(
                    text=(
                        "The interpretive relation layer -- what a passage treats, protects "
                        "against, is used for, invokes or requests -- covers a small and "
                        "uneven share of the corpus: 2,876 edges over 22,537 passages, most "
                        "of them Atharvavedic. Nothing here means nothing was extracted."
                    ),
                    source="measured",
                )
            ],
        )

    @staticmethod
    def _assertion_set(
        rows: object, total: object, passage: PassageSummary
    ) -> AttestedSet[AgentiveAssertionView]:
        """The agentive layer, whose absence outside the Rigveda is the layer's shape.

        All 4,865 assertions hang off Rigvedic passages, so an empty set for the other
        three corpora is ``NOT_BUILT`` and carries the frozen action-scope caveat.
        """
        items: list[AgentiveAssertionView] = []
        for item in rows if isinstance(rows, list) else []:
            if not isinstance(item, dict):
                continue
            agent = _entity_refs([item.get("agent")])
            predicate = _entity_refs([item.get("predicate")])
            target = _entity_refs([item.get("target")])
            modality = _assertion_modality(item.get("frame"))
            items.append(
                AgentiveAssertionView(
                    display_label=_nonempty(item.get("display_label")),
                    agent=agent[0] if agent else None,
                    predicate=predicate[0] if predicate else None,
                    target=target[0] if target else None,
                    modality=modality,
                    modality_status=(
                        KnowledgeStatus.SUPPORTED if modality else KnowledgeStatus.NOT_BUILT
                    ),
                    modality_note=None if modality else _MODALITY_ABSENT_NOTE,
                    semantic_predicate=_nonempty(item.get("semantic_predicate")),
                    explicitness=_nonempty(item.get("explicitness")),
                    state=_nonempty(item.get("state")),
                    verb_surface=_nonempty(item.get("verb_surface")),
                    root_label=_nonempty(item.get("root_label")),
                    quality_tier=_nonempty(item.get("quality_tier")),
                    evidence_basis=_nonempty(item.get("evidence_basis")),
                    knowledge_layer=_nonempty(item.get("knowledge_layer")),
                )
            )
        if items:
            # The stratum split is reported on the set as well as per row, because a client
            # showing a modality column needs to know before it renders that some rows
            # cannot fill it, rather than discovering it one blank cell at a time.
            without_frame = sum(1 for item in items if item.modality is None)
            caveats = (
                [CaveatView(text=_MODALITY_ABSENT_NOTE, source="measured")] if without_frame else []
            )
            return AttestedSet[AgentiveAssertionView](
                items=items, total=_as_int(total) or len(items), caveats=caveats
            )
        return AttestedSet[AgentiveAssertionView](
            items=[],
            total=0,
            data_status=KnowledgeStatus.NOT_BUILT,
            coverage=CoverageView(
                vedas_in_scope=["RV"],
                vedas_not_covered=[veda for veda in layer_figures.CORPUS_MANTRAS if veda != "RV"],
                denominator=dict(layer_figures.CORPUS_MANTRAS),
            ),
            caveats=[
                CaveatView(
                    text=named_query_caveat("action_predicate_breadth")
                    or (
                        "The agentive assertion layer is Rigveda-only: all 4,865 assertions "
                        "hang off Rigvedic passages, because the layer is derived from a "
                        "morphological annotation that covers the Rigveda alone."
                    ),
                    source="action_predicate_breadth",
                )
                if passage.veda != "RV"
                else CaveatView(
                    text="No agentive assertion was extracted from this Rigvedic verse. The "
                    "layer covers 2,542 of the Rigveda's 10,552 mantras, so most Rigvedic "
                    "verses are outside it.",
                    source="measured",
                )
            ],
        )


#: Frozen domain queries whose caveat already states each attribution layer's reach. Reused
#: rather than retyped: V3.1 and V3.2 both found hand-copied caveat prose that had drifted
#: from the data it described, and the fix was to stop copying it.
#:
#: ``MENTIONS_DEVATA`` is deliberately absent. It no longer routes through
#: :meth:`PassageService._attribution_set` at all, because that method cannot express the
#: ambiguity contract: it projected no grade onto the row and attached a caveat only on the
#: empty branch, so a populated list of purely ambiguous mentions asserted them as fact.
#: Mentions go through :meth:`PassageService._mentioned_devata_set` instead. Leaving the
#: entry here would be dead configuration that looks like coverage.
_LAYER_CAVEAT_QUERIES: Final[dict[str, str]] = {
    "HAS_DEVATA": "deity_profile",
    "HAS_RISHI": "rishi_layer_reach_by_veda",
    "HAS_CHANDAS": "chandas_layer_reach_by_veda",
}

__all__ = [
    "LEVEL_ORDER",
    "NAME_VALUED_LEVELS",
    "NATIVE_LEVEL_LABELS",
    "PassageService",
    "UnknownHierarchyLevel",
    "citation_candidate",
    "native_level_label",
    "order_levels",
    "paged_meaning",
]
