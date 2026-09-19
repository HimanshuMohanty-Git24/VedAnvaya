"""Passage identity, textual surfaces, navigation and parallelism.

Four contracts are enforced by the models in this file rather than by the routes that
build them, because a route can forget and a model cannot.

*A surface that is not there is not a null.* No passage in this graph carries both
scripts: 16,391 Rigvedic and Atharvavedic mantras are Latin-only and 3,819 Samavedic and
Yajurvedic ones are Devanagari-only. A frontend handed ``devanagari: null`` for RV 1.1.1
renders an empty box and the reader concludes the verse has no Sanskrit, so
:class:`TextAvailability` reports a :class:`KnowledgeStatus` per script and never a bare
null.

*A collection too small to paginate still has to say why it is empty.* A passage has at
most one translation, so wrapping it in :class:`~vedagraph.api.models.common.Paginated`
would be theatre -- but the Samaveda has zero translations of its own across all 1,844
verses, and an empty list there means "no translation was ever released for this corpus"
rather than "this verse is untranslated". The 173 Samavedic verses that do return an item
return a rendering reused from the Rigvedic parallel, which the item discloses.
:class:`AttestedSet` is the small-collection counterpart of
``Paginated`` and carries the same refusal: an empty set cannot claim ``SUPPORTED``
without a caveat.

*Parallelism is symmetric and the graph stores it directed.* All 1,684
``REUSES_TEXT_FROM`` edges run Samaveda-to-Rigveda, and 1,421 Rigvedic passages have reuse
edges only inbound. A traversal that followed the arrow would show those 1,421 verses no
reuse at all, so :class:`ParallelView` carries ``stored_direction`` and the service
traverses undirected.

*Entity-vocabulary overlap is not textual reuse.* ``SHARES_ENTITY_VOCABULARY_WITH`` means
two passages name some of the same registry concepts; it says nothing about shared
wording. It travels with ``relation_kind = ENTITY_VOCABULARY_OVERLAP`` and
``is_textual_parallelism = False`` so it cannot be totalled with the four textual
predicates by accident.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator

from vedagraph.api.models.common import (
    ApiModel,
    CaveatView,
    CoverageView,
    EvidenceView,
    KnowledgeStatus,
    Paginated,
    ReferentCertaintyCounts,
)
from vedagraph.api.models.entity import AttributedRef, EntityRef, MentionCertainty
from vedagraph.domain import layer_figures
from vedagraph.domain.translation_semantics import TranslationCoverageKind

# ---------------------------------------------------------------------------
# A bounded collection that explains its own size
# ---------------------------------------------------------------------------


class AttestedSet[T](ApiModel):
    """A small collection whose emptiness is a claim, so it must be justified.

    Used for the per-passage collections whose size the corpus fixes at one or two --
    translations, seers, metres, the ascribed deity -- where pagination would add a
    ``PaginationMeta`` block to a list that can never exceed three entries. It keeps the
    one property of ``Paginated`` that matters: ``SUPPORTED`` plus zero items is refused,
    because that shape asserts textual absence and is usually reporting a missing layer.
    """

    items: list[T] = Field(default_factory=list)
    total: int | None = Field(
        default=None,
        description="Items available where that differs from the number returned; null "
        "means not established and never means zero.",
    )
    data_status: KnowledgeStatus = KnowledgeStatus.SUPPORTED
    coverage: CoverageView | None = None
    caveats: list[CaveatView] = Field(default_factory=list)

    @model_validator(mode="after")
    def _empty_must_explain_itself(self) -> Self:
        """Refuse a silent empty set, for the reason ``Paginated`` refuses a silent page."""
        if not self.items and self.data_status is KnowledgeStatus.SUPPORTED and not self.caveats:
            raise ValueError(
                "An empty AttestedSet must carry a non-SUPPORTED data_status or a caveat: "
                "the Samaveda's zero translations of its own and the Yajurveda's absent "
                "deity "
                "ascription layer are both empty lists and neither is textual absence."
            )
        return self


# ---------------------------------------------------------------------------
# Structure
# ---------------------------------------------------------------------------


class BreadcrumbView(ApiModel):
    """One step of a passage's position in its Veda's own structure.

    ``native_label`` is derived from ``level_key`` through the single map in
    ``passage_service``, not read off the node: ``native_labels`` is ``'[]'`` on all 11,590
    Rigvedic passages and populated on the other three corpora, so a reader that trusted
    the property would present the Rigveda as having no structural vocabulary at all.

    ``value`` is a string because the Samavedic ``collection`` level is a name (``ARANYA``,
    ``CHANDA``, ``MAHANAMNYA``, ``UTTARA``) where every other level is an ordinal.
    """

    level_key: str = Field(description="The graph's hierarchy key, e.g. 'mandala'.")
    native_label: str | None = Field(
        default=None,
        description="The tradition's name for this level, e.g. 'Mandala'. Null only when "
        "the key is unrecognised, in which case the payload also carries a caveat.",
    )
    value: str
    depth: int = Field(ge=1, description="1 for the outermost level.")
    canonical_key: str | None = Field(
        default=None, description="The container passage at this level, where one is a node."
    )
    canonical_citation: str | None = None
    display_label: str | None = None
    passage_type: str | None = Field(
        default=None, description="MANTRA, HYMN, SECTION or STRUCTURAL_CONTAINER."
    )


class PassageSummary(ApiModel):
    """The list-row and cross-reference shape for a passage.

    Carries ``canonical_key``, ``canonical_citation`` and ``canonical_urn`` together
    because they are three different addressing schemes a client may already hold, and
    none of them is a Neo4j identifier.
    """

    canonical_key: str
    canonical_citation: str | None = None
    canonical_urn: str | None = None
    entity_id: str | None = Field(
        default=None, description="The passage's own stable UUID. Not a Neo4j id."
    )
    veda: str
    work_id: str
    passage_type: str = Field(description="MANTRA, HYMN, SECTION or STRUCTURAL_CONTAINER.")
    display_label: str | None = None
    native_levels: list[str] = Field(
        default_factory=list,
        description="This passage's level names outermost-first, e.g. "
        "['Mandala', 'Sukta', 'Mantra'].",
    )
    hierarchy: dict[str, str] = Field(
        default_factory=dict, description="Level key to value, e.g. {'mandala': '1'}."
    )
    parent_key: str | None = None
    sequence_in_parent: int | None = None


# ---------------------------------------------------------------------------
# Text
# ---------------------------------------------------------------------------


class TextScript(StrEnum):
    """The two scripts in the corpus, named as a reader would name them."""

    DEVANAGARI = "DEVANAGARI"
    IAST = "IAST"
    UNKNOWN = "UNKNOWN"


class TextSurfaceView(ApiModel):
    """One witness of a passage's Sanskrit.

    ``surface`` is a product name for the graph's ``text_role``. The mapping is not
    cosmetic: ``NORMALIZED_FOR_SEARCH`` is an accent-stripped matching form and is wrong to
    display as the text, and ``EXTRACTED_FROM_CONTAINER`` marks the 1,975 Yajurvedic verses
    cut out of a printed block rather than transcribed as verses, which is a provenance
    fact a reader is entitled to see beside the words.
    """

    surface: str = Field(
        description="PRIMARY, PARALLEL_WITNESS, NORMALIZED_FOR_SEARCH or EXTRACTED_FROM_CONTAINER."
    )
    script: TextScript
    accented: bool | None = Field(
        default=None, description="Whether this witness records Vedic accent."
    )
    text: str
    language: str = "sa"
    witness_id: str | None = Field(
        default=None, description="The edition this text came from, e.g. GRETIL.RV.AUFRECHT."
    )
    source_id: str | None = None
    rights_status: str | None = None
    is_displayable: bool = Field(
        default=True,
        description="False for a search-normalised form, which is real data and not the "
        "text a reader should be shown.",
    )
    note: str | None = None


class TextAvailability(ApiModel):
    """Every Sanskrit witness a passage has, plus a status per script.

    The per-script statuses exist because the corpus is script-disjoint. Asking for the
    Devanagari of RV 1.1.1 has the answer "the Rigvedic witnesses held here are romanised",
    which is a statement about this collection and not about the Rigveda; asking for the
    transliteration of a Samavedic verse has the mirror answer. Both are ``NOT_BUILT``
    rather than ``INSUFFICIENT_EVIDENCE``: the absence is about what was ingested.
    """

    surfaces: list[TextSurfaceView] = Field(default_factory=list)
    devanagari: KnowledgeStatus = KnowledgeStatus.NOT_BUILT
    transliteration: KnowledgeStatus = KnowledgeStatus.NOT_BUILT
    normalized_for_search: KnowledgeStatus = KnowledgeStatus.NOT_BUILT
    data_status: KnowledgeStatus = KnowledgeStatus.SUPPORTED
    caveats: list[CaveatView] = Field(default_factory=list)

    @model_validator(mode="after")
    def _no_surfaces_must_explain_itself(self) -> Self:
        if not self.surfaces and self.data_status is KnowledgeStatus.SUPPORTED:
            raise ValueError(
                "A passage with no textual surface must not claim SUPPORTED: the 2,327 "
                "container passages carry no text of their own, and that is a fact about "
                "containers rather than about the text."
            )
        return self


class TranslationView(ApiModel):
    """One aligned translation, and what kind of coverage it actually gives this verse.

    ``quality_status`` is ``MACHINE_ALIGNED`` on all of them: the alignment of a
    public-domain translation to a canonical key was done by machine and never checked
    against the Sanskrit. A client must be able to see that rather than infer editorial
    care from the presence of a translator's name.

    ``coverage_kind`` is the field that stops this model asserting something false, and it
    is required rather than optional. Three shapes now reach a reader and only one of them
    is a 1:1 rendering of the verse asked for: a ``RANGE_TRANSLATION`` is one print unit
    over a span of verses, a ``REUSED_RENDERING`` is another corpus's published English on
    text verified identical, and a non-English ``language`` is Griffith's Latin
    substitution. Each was previously indistinguishable from a dedicated translation, and
    the validators below refuse a payload that presents one as the other.
    """

    text: str
    translator: str | None = None
    language: str = "en"
    language_name: str | None = Field(
        default=None,
        description="The language in words, e.g. 'Latin'. Present so a client need not "
        "carry an ISO table to avoid labelling a Latin rendering 'Translation'.",
    )
    year: int | None = None
    work_edition: str | None = None
    quality_status: str | None = None
    alignment_level: str | None = Field(
        default=None, description="The unit the alignment claims, e.g. MANTRA."
    )
    coverage_kind: TranslationCoverageKind = Field(
        description="How this translation covers the passage it was returned for: "
        "DEDICATED_TRANSLATION, RANGE_TRANSLATION, CONTAINER_TRANSLATION or "
        "REUSED_RENDERING. Never infer 1:1 alignment from the presence of a translation."
    )
    covers_canonical_keys: list[str] = Field(
        default_factory=list,
        description="Every canonical key this one rendering covers. A single-key list on a "
        "dedicated translation and the complete span on a range translation; never a "
        "partial span, which is refused.",
    )
    anchor_canonical_key: str | None = Field(
        default=None,
        description="The passage the translation node is attached to. Differs from the "
        "passage requested when a range translation reaches it through its span.",
    )
    is_this_passages_own: bool = Field(
        default=True,
        description="False when the passage requested is inside a range anchored on "
        "another verse, so a client can render 'covered by' rather than 'translated as'.",
    )
    source_unit: str | None = Field(
        default=None,
        description="The print unit the translator numbered, where it differs from this "
        "corpus's verse numbering.",
    )
    independent_translation: bool = Field(
        default=True,
        description="False for a reused rendering. A false here means the text must not "
        "be totalled into this corpus's own translated count, nor used as independent "
        "semantic evidence about this passage.",
    )
    reuse_kind: str | None = Field(
        default=None,
        description="REUSED_RENDERING, or null when the rendering is this "
        "translator's own work on this passage.",
    )
    reused_from_veda: str | None = None
    reused_from_passage_key: str | None = None
    reused_from_citation: str | None = None
    reused_from_translation_id: str | None = Field(
        default=None,
        description="The identity of the translation actually being shown, in the corpus "
        "it was published for.",
    )
    reuse_basis: str | None = Field(
        default=None, description="How the text equivalence was established."
    )
    disclosure: str | None = Field(
        default=None,
        description="The sentence a reader must be shown beside this translation. Non-null "
        "whenever the rendering is not a dedicated English translation of this verse, and "
        "a payload that omits it in that case is refused.",
    )
    rights_status: str | None = None
    source_id: str | None = None
    upstream_correction_id: str | None = None
    upstream_correction_reason: str | None = None

    @model_validator(mode="after")
    def _a_rendering_that_is_not_this_verses_own_must_say_so(self) -> Self:
        """Refuse the three payloads that would read as a dedicated English translation.

        A route can forget to set a disclosure on one branch; this model cannot. The
        Samaveda is the reason it is enforced here: every English string that will ever
        reach a Samavedic verse is a Rigvedic rendering, so an undisclosed one tells a
        visitor the corpus has 173 translations of its own.
        """
        if self.coverage_kind is TranslationCoverageKind.REUSED_RENDERING:
            if self.independent_translation:
                raise ValueError(
                    "a REUSED_RENDERING cannot claim independent_translation: it is "
                    "another corpus's published English on verified-identical text."
                )
            if not self.reused_from_passage_key:
                raise ValueError(
                    "a REUSED_RENDERING must name the passage whose rendering it is; "
                    "'The Hymns of the Rigveda' in an edition line is not a disclosure."
                )
            if not self.disclosure:
                raise ValueError("a REUSED_RENDERING must carry its disclosure sentence")
        if self.coverage_kind is TranslationCoverageKind.RANGE_TRANSLATION:
            if len(self.covers_canonical_keys) < 2:
                raise ValueError(
                    "a RANGE_TRANSLATION must enumerate its complete span: a range that "
                    "names one verse is indistinguishable from a dedicated translation."
                )
            if not self.disclosure:
                raise ValueError("a RANGE_TRANSLATION must disclose that it covers a span")
        if self.language != "en" and not self.disclosure:
            raise ValueError(
                f"a translation in {self.language!r} must disclose that it is not English: "
                "the 22 Latin substitutions are Griffith's real text and are not the "
                "English layer."
            )
        if not self.is_this_passages_own and not self.anchor_canonical_key:
            raise ValueError(
                "a translation reached through another passage's span must name the anchor"
            )
        return self


# ---------------------------------------------------------------------------
# Parallelism
# ---------------------------------------------------------------------------


class ParallelFilter(StrEnum):
    """The parallel kinds a client may ask for.

    ``FORMULA`` is the odd one and is deliberately in the same enum. It is not a
    passage-to-passage edge at all: it means two passages use the same ``Formula``, reached
    through the 22,686 ``USES_FORMULA`` edges. Offering it beside the four stored predicates
    is what stops a client concluding that a passage with no ``EXACT_PARALLEL_OF`` shares no
    wording with anything in the corpus.
    """

    EXACT = "exact"
    NEAR = "near"
    REUSE = "reuse"
    VARIANT = "variant"
    VOCABULARY = "vocabulary"
    FORMULA = "formula"
    SAME_VEDA = "same_veda"
    CROSS_VEDA = "cross_veda"


class ParallelKind(StrEnum):
    """What sort of claim a parallel row is making."""

    TEXTUAL_PARALLEL = "TEXTUAL_PARALLEL"
    TEXT_REUSE = "TEXT_REUSE"
    TEXTUAL_VARIANT = "TEXTUAL_VARIANT"
    ENTITY_VOCABULARY_OVERLAP = "ENTITY_VOCABULARY_OVERLAP"
    FORMULA_MEDIATED = "FORMULA_MEDIATED"


class StoredDirection(StrEnum):
    """Which way the edge was written, for a relation that is symmetric in fact."""

    THIS_PASSAGE_IS_SUBJECT = "THIS_PASSAGE_IS_SUBJECT"
    THIS_PASSAGE_IS_OBJECT = "THIS_PASSAGE_IS_OBJECT"
    NOT_STORED_AS_AN_EDGE = "NOT_STORED_AS_AN_EDGE"


class ParallelMetrics(ApiModel):
    """The similarity figures, each nullable because the predicates do not share them.

    ``NEAR_PARALLEL_OF`` carries ``similarity`` and no ``match_level``;
    ``SHARES_ENTITY_VOCABULARY_WITH`` carries ``distinctiveness`` and no similarity at all;
    the 256 same-Veda ``EXACT_PARALLEL_OF`` edges carry ``methods`` where the other 750
    carry ``levels_reached``. Returning zero for an absent metric would make an
    entity-overlap row look like a textual near-miss.
    """

    similarity: float | None = None
    score: float | None = None
    token_jaccard: float | None = None
    ngram_jaccard: float | None = None
    lcs_ratio: float | None = None
    edit_ratio: float | None = None
    distinctiveness: float | None = None
    rarest_shared_df: int | None = None


class ParallelView(ApiModel):
    """One related passage, with the kind of relation stated before any number."""

    relation: str = Field(description="Product name of the relation, e.g. EXACT_PARALLEL.")
    relation_kind: ParallelKind
    is_textual_parallelism: bool = Field(
        description="False for entity-vocabulary overlap, which shares concepts and not "
        "wording, so it must never be counted as reuse."
    )
    passage: PassageSummary
    stored_direction: StoredDirection
    same_veda: bool
    veda_pair: str | None = Field(
        default=None,
        description="Derived from the two passages' vedas. The stored veda_pair property "
        "is null on all 325 same-Veda edges, so it is not the source of this field.",
    )
    metrics: ParallelMetrics = Field(default_factory=ParallelMetrics)
    match_level: str | None = Field(
        default=None,
        description="The textual surface the match was made on. Null where the edge "
        "predates level recording; the graph stores an empty string for 4,229 of them.",
    )
    method: str | None = None
    methods: list[str] = Field(default_factory=list)
    levels_reached: list[str] = Field(default_factory=list)
    strongest_method: str | None = None
    shared_entities: int | None = None
    shared_entity_keys: list[str] = Field(default_factory=list)
    shared_formulas: list[EntityRef] = Field(
        default_factory=list, description="Populated only for FORMULA_MEDIATED rows."
    )
    quality_tier: str | None = None
    trust: str | None = None
    state: str | None = None
    knowledge_layer: str | None = None
    attribution_precision: str | None = None
    # `pipeline_version` deliberately absent. It named the internal build run that produced
    # the edge (`entity-vocabulary-overlap-v3.1`), which identifies *our build* rather than
    # the evidence, and no spec clause asks for it. What a client legitimately needs about a
    # derived edge is already here in product terms: `method`, `quality_tier`, `trust`,
    # `state`, `knowledge_layer`, `attribution_precision` and the quoted `evidence`.
    parallel_id: str | None = None
    evidence: EvidenceView | None = None


class ParallelCounts(ApiModel):
    """Parallel counts by kind, measured undirected.

    Split by kind and never summed into one headline, because the four textual predicates
    and the entity-overlap predicate answer different questions: a single "42 parallels"
    figure would average a shared verse against a shared word for 'horse'.
    """

    exact: int = 0
    near: int = 0
    reuse: int = 0
    variant: int = 0
    entity_vocabulary_overlap: int = 0
    other_textual: int = 0
    textual_total: int = 0
    counted_undirected: bool = True
    data_status: KnowledgeStatus = KnowledgeStatus.SUPPORTED
    caveats: list[CaveatView] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Semantics attached to a passage
# ---------------------------------------------------------------------------


class SemanticRelationView(ApiModel):
    """One interpretive statement the graph makes about a passage.

    Covers the whole interpretive predicate family in one shape -- ``TREATS``,
    ``PROTECTS_FROM``, ``USED_FOR_RITE``, ``INVOKES``, ``PRAISES``, ``REQUESTS`` and the
    rest -- rather than a field per predicate, so a predicate this API does not yet name by
    hand is still returned instead of dropped.
    """

    relation: str
    target: EntityRef
    attribution_precision: str | None = None
    evidence_basis: str | None = None
    quality_tier: str | None = None
    state: str | None = None
    confidence: float | None = None
    knowledge_layer: str | None = None


class MentionedDevataView(AttributedRef):
    """A deity named in a passage, carrying the grade the graph gave that identification.

    ``referent_certainty`` is on the row and not optional, because the whole difficulty of
    this predicate is that the name and the noun are the same word. ``soma`` is the god, the
    plant and the pressed drink; ``agni`` is the god and it is fire; ``vāc`` is the goddess
    Speech and it is speech. The graph grades every one of the 17,165 mention edges
    accordingly, and 6,806 of them -- 39.6% -- come out ``DEITY_AMBIGUOUS``.

    A row without its grade is the defect this model closes: RV 1.4.2 has exactly one
    mention edge, graded ``DEITY_AMBIGUOUS``, and reporting it ungraded tells a reader that
    the verse names the god Soma when the matcher's own verdict is that it may be the drink.
    """

    referent_certainty: str = Field(
        description="DEITY_CERTAIN, DEITY_PROBABLE or DEITY_AMBIGUOUS -- the graph's own "
        "grade for whether this form denotes the deity or the ordinary noun."
    )
    is_ambiguous: bool = Field(
        description="True where the grader could not distinguish the deity from the common "
        "noun. Present as a boolean so a client cannot render an ambiguous row as fact by "
        "forgetting to compare a string."
    )
    occurrences: int | None = None


class MentionedDevataSet(AttestedSet[MentionedDevataView]):
    """The mention set, which always reports all three tiers whichever it returned.

    Reporting only the included total would let the product default look like the whole
    truth. A deity whose name is an ordinary noun is flattered or penalised by that choice
    by a factor of four -- Soma has 240 CERTAIN, 181 PROBABLE and 1,091 AMBIGUOUS mentions
    across the corpus -- so the counts travel together and the caller can see what the
    default excluded.
    """

    certainty: ReferentCertaintyCounts = Field(
        description="All three tiers, counted before filtering."
    )
    included_certainty: MentionCertainty = Field(
        default=MentionCertainty.DEFAULT,
        description="Which tiers `items` actually contains.",
    )
    excluded_count: int = Field(
        default=0, description="Mentions the requested certainty mode withheld."
    )


class AssertionModality(StrEnum):
    """Whether the text asserts something of a deity or asks it of one.

    Read from the graph's ``frame`` property, whose value space is ``ASSERTED`` (1,557),
    ``REQUESTED`` (849) and null (2,459). The null is not a third modality and is not an
    unknown one: it is the whole of the model-extraction stratum, which was never given
    this axis. See :attr:`AgentiveAssertionView.modality_status`.
    """

    ASSERTED = "ASSERTED"
    REQUESTED = "REQUESTED"


class AgentiveAssertionView(ApiModel):
    """One agent-predicate-target assertion from the semantic assertion layer.

    This said "the Rigveda-only agentive layer" and "all 4,865 ``SemanticAssertion`` nodes
    hang off Rigvedic passages". Both were true of an earlier state and are now false: the
    layer holds 35,131 assertions and reaches all four corpora -- RV 27,057, AV 6,167,
    YV 1,543, SV 364. A Yajurvedic verse returning none of these is a verse the layer did
    not reach, not a corpus outside it, which is why the set carries a status.

    The *agentive* reading was Rigveda-only and is not any more. 2,660 assertions carry
    an ``ASSERTION_AGENT``: 2,406 Rigvedic, from a morphological annotation covering the
    Rigveda alone, plus 124 Atharvavedic and 34 Yajurvedic projected from the DCS
    dependency annotation's own role resolution by GAP-SEMANTICS-003. The Sāmaveda carries
    no agent at all. The two derivations are separable on every edge -- the projected ones
    carry ``derivation = TREEBANK_DEPREL_ROLE_PROJECTION`` and the morphological ones carry
    none -- so a reader is never shown one tier as the other.

    **The layer is two layers and they do not share their vocabulary.** The 2,406
    deterministic assertions carry ``frame`` (ASSERTED or REQUESTED), ``verb_surface`` and
    ``root_label``, and no ``semantic_predicate``. The 2,459 model-extracted ones carry
    ``semantic_predicate`` (DESCRIBES, REQUESTS, INVOKES), ``explicitness`` and
    ``object_kind``, and no ``frame`` at all -- the correlation with ``knowledge_layer`` is
    exact, 2,459 for 2,459. So a model-extracted row has no modality to report, and
    reporting ``null`` alone would tell a reader that half the assertion layer asserts
    nothing. Both vocabularies are therefore returned, and ``modality_status`` says which
    stratum a row came from.
    """

    display_label: str | None = None
    agent: EntityRef | None = None
    predicate: EntityRef | None = None
    target: EntityRef | None = None

    modality: AssertionModality | None = Field(
        default=None,
        description="ASSERTED or REQUESTED, from the deterministic stratum. Null on every "
        "model-extracted row; read modality_status before rendering the absence.",
    )
    modality_status: KnowledgeStatus = Field(
        default=KnowledgeStatus.NOT_BUILT,
        description="SUPPORTED where the assertion carries a frame. NOT_BUILT on the "
        "model-extraction stratum, which was never given this axis -- not a row whose "
        "modality is unknown, a row from a layer that has no modality.",
    )
    modality_note: str | None = None
    semantic_predicate: str | None = Field(
        default=None,
        description="The model-extraction stratum's own predicate, e.g. DESCRIBES or "
        "REQUESTS. This is where a model-extracted row expresses what a frame would.",
    )
    explicitness: str | None = Field(
        default=None, description="EXPLICIT or STRONG_INFERENCE, on model-extracted rows."
    )
    state: str | None = Field(
        default=None,
        description="CANDIDATE on all 2,459 model-extracted rows: unreviewed extractions, "
        "not settled readings.",
    )

    verb_surface: str | None = None
    root_label: str | None = None
    quality_tier: str | None = None
    evidence_basis: str | None = None
    knowledge_layer: str | None = None
    cautions: list[str] = Field(
        default_factory=list,
        description="Caution codes the assertion node carries, verbatim. The load-bearing "
        "one is ANALYSIS_IS_OF_A_LETTER_IDENTICAL_RIGVEDIC_VERSE_NOT_OF_A_SAMAVEDIC_"
        "ANNOTATION, on all 364 Samavedic assertions: the reading was carried across on "
        "textual identity and is not an analysis of the verse in its own collection. The "
        "graph has recorded this since the layer was built and this field is what reads it.",
    )

    @model_validator(mode="after")
    def _absent_modality_must_be_typed(self) -> Self:
        """A null modality must never travel as ``SUPPORTED``.

        This is the model closing the exact hole that shipped once already: the service
        read a property that does not exist in the graph, Neo4j returned null without
        erroring, and the field was set to render blank forever behind a passing test.
        Now a null has to be accompanied by a status that says why.
        """
        if self.modality is None and self.modality_status is KnowledgeStatus.SUPPORTED:
            raise ValueError(
                "An assertion with no modality cannot claim SUPPORTED: the 2,459 "
                "model-extracted assertions have no frame at all, and a blank modality "
                "beside a SUPPORTED status reads as a verse that asserts nothing."
            )
        return self


class AudioAvailability(ApiModel):
    """The *graph's* recitation layer, which does not exist. Not the product's.

    Deliberately not a boolean and not a null. ``false`` reads as "this verse has no
    recording" and ``null`` renders as a disabled button with no explanation; both invite a
    frontend to ship a play control over a layer that is not there. The validator refuses
    any other status, so adding audio to the *graph* means editing this contract on purpose.

    The note used to read "No recitation audio exists anywhere in this graph", which was
    true of the graph and false as a sentence a reader would understand: the product serves
    16,834 catalogued recordings from ``/api/v1/passages/{key}/audio``, and RV 1.1.1
    returns a playable track from the same server that was answering "anywhere" with
    "none". A field can be correct about its own layer and still be the wrong thing to say,
    and this one is read by clients that have no way to know the distinction. It now names
    the surface that does hold the audio.
    """

    status: KnowledgeStatus = KnowledgeStatus.NOT_BUILT
    recordings: list[EntityRef] = Field(default_factory=list)
    note: str = (
        "The knowledge graph holds no audio node, relationship or property, so this block "
        "is always empty. It is not a statement about whether a recording exists: "
        "recitations are served from the audio catalogue at "
        "GET /api/v1/passages/{key}/audio, which is the surface to ask."
    )

    @model_validator(mode="after")
    def _audio_is_not_built(self) -> Self:
        if self.status is not KnowledgeStatus.NOT_BUILT or self.recordings:
            raise ValueError(
                "There is no audio layer in the frozen graph. Reporting anything but "
                "NOT_BUILT here would be a claim no node supports. Catalogued recordings "
                "are served by /api/v1/passages/{key}/audio and do not belong in this block."
            )
        return self


# ---------------------------------------------------------------------------
# The composed payloads
# ---------------------------------------------------------------------------


class PassageProvenance(ApiModel):
    """Where a passage's content came from and how far it has been checked.

    ``review_state`` is a constant and says so: nothing in this graph is human-reviewed.
    Omitting the field would let a client assume review; making it null would look like a
    gap in one record rather than a property of the whole build.
    """

    work_id: str
    recension: str | None = None
    text_sources: list[str] = Field(default_factory=list)
    translation_sources: list[str] = Field(default_factory=list)
    rights: list[str] = Field(default_factory=list)
    status: str | None = Field(default=None, description="The passage's canonical status.")
    review_state: str = "NOT_HUMAN_REVIEWED"
    # Built from the measured figures rather than typed. The sentence this replaces said
    # "MODEL_ADJUDICATED, on 587 edges, none of them Rigvedic", which is the TIER_C
    # passage-anchored count wearing the MODEL_ADJUDICATED label: MODEL_ADJUDICATED is 613.
    review_note: str = layer_figures.adjudication_disclosure()


class PassageDetail(ApiModel):
    """The full passage payload (spec section 9)."""

    canonical_key: str
    canonical_citation: str | None = None
    canonical_urn: str | None = None
    entity_id: str | None = None
    display_label: str | None = None
    passage_type: str
    veda: str
    work_id: str
    work_display_label: str | None = Field(
        default=None,
        description="The work's scope-honest label. Never its traditional name alone: "
        "'Samaveda Samhita' over a corpus that is the arcika only is this graph's single "
        "most misleading string, which is why the honest label travels with the passage.",
    )
    work_traditional_name: str | None = None
    recension: str | None = None

    native_hierarchy: list[BreadcrumbView] = Field(default_factory=list)
    structural_path: list[str] = Field(default_factory=list)
    parent: PassageSummary | None = None
    child_count: int | None = None
    sequence_in_parent: int | None = None

    text: TextAvailability
    translations: AttestedSet[TranslationView]

    rishis: AttestedSet[AttributedRef]
    devatas: AttestedSet[AttributedRef]
    chandas: AttestedSet[AttributedRef]
    mentioned_devatas: MentionedDevataSet

    concepts: AttestedSet[EntityRef]
    mentioned_entities: AttestedSet[EntityRef]
    formulas: AttestedSet[EntityRef]
    semantic_relations: AttestedSet[SemanticRelationView]
    agentive_assertions: AttestedSet[AgentiveAssertionView]

    parallel_counts: ParallelCounts
    audio: AudioAvailability = Field(default_factory=AudioAvailability)
    provenance: PassageProvenance

    data_status: KnowledgeStatus = KnowledgeStatus.SUPPORTED
    coverage: CoverageView | None = None
    caveats: list[CaveatView] = Field(default_factory=list)


class NavigationRelation(StrEnum):
    PARENT = "PARENT"
    CHILDREN = "CHILDREN"
    SIBLINGS = "SIBLINGS"


class NavigationResult(ApiModel):
    """One structural move away from a passage (spec section 10).

    The same shape answers parent, children and siblings so that a client walking the four
    Vedas writes one traversal rather than four. ``level_key`` and ``native_label`` describe
    the level the returned passages sit at, which is how a Samavedic Dasati and a Rigvedic
    Sukta come back through one code path with their own names intact.
    """

    of: PassageSummary
    relation: NavigationRelation
    level_key: str | None = None
    native_label: str | None = None
    results: Paginated[PassageSummary]


class FormulaPhraseView(ApiModel):
    """A fixed phrase this verse shares with other verses, and how far it travels.

    The reader carried no formula layer at all, which left 10,574 mantras - 1,311 of the
    Samaveda's 1,844 among them - with real, readable substance the reading page could not
    show. For a Samavedic verse that matters more than for any other corpus: it has no
    seer, no metre and no ascribed deity of its own, so its shared wording is most of what
    there is to say about it beyond the text.

    ``match_level`` travels because the formula layer's identity is a normalised-string
    match and the strength of that match varies per occurrence: ``SCRIPT_FOLDED`` is a
    stronger claim than ``SANDHI_INSENSITIVE``, and a surface that showed both as "shares
    this phrase" would flatten the distinction the edge went to the trouble of recording.
    ``source_form`` is what this verse actually reads, which can differ from the family's
    ``display_form``.
    """

    formula_id: str
    display_form: str
    #: The wording as it stands in *this* verse, where the edge recorded it.
    source_form: str | None = None
    #: Verses carrying this formula anywhere in the corpus. Null means not established.
    occurrence_count: int | None = None
    #: The corpora it is attested in, as recorded on the formula.
    vedas: list[str] = Field(default_factory=list)
    cross_veda: bool | None = None
    #: How closely this verse's wording matched. Null where the edge predates recording.
    match_level: str | None = None


class ReaderPayload(ApiModel):
    """Everything needed to render one mantra in a single call (spec section 11).

    The field set is chosen so a reader view never needs a second request: text, aligned
    translation, breadcrumbs, both neighbours, the three attribution axes, the major
    concepts, and counts for the things a UI shows as affordances rather than as content --
    audio, parallels, graph neighbours.
    """

    canonical_key: str
    canonical_citation: str | None = None
    canonical_urn: str | None = None
    display_label: str | None = None
    passage_type: str
    veda: str
    work_id: str
    work_display_label: str | None = None

    breadcrumbs: list[BreadcrumbView] = Field(default_factory=list)
    primary_text: TextSurfaceView | None = Field(
        default=None,
        description="The witness to render. Null only when text.data_status says why.",
    )
    text: TextAvailability
    translations: AttestedSet[TranslationView]

    rishis: AttestedSet[AttributedRef]
    devatas: AttestedSet[AttributedRef]
    chandas: AttestedSet[AttributedRef]
    mentioned_devatas: MentionedDevataSet = Field(
        description="Deities *named* in the verse, graded. Distinct from `devatas`, which "
        "is the Anukramani's ascription and reaches the Rigveda only -- for a Samavedic, "
        "Yajurvedic or Atharvavedic verse this is the only deity signal there is, which is "
        "why the reader carries it rather than leaving those three corpora blank."
    )
    major_concepts: AttestedSet[EntityRef]
    formulas: AttestedSet[FormulaPhraseView] = Field(
        default_factory=lambda: AttestedSet[FormulaPhraseView](
            data_status=KnowledgeStatus.NOT_BUILT
        ),
        description="Fixed phrases this verse shares with others. For a Samavedic verse "
        "this is often the only knowledge layer besides the text and its Rigvedic "
        "counterpart, because the seer, metre and ascription layers are Rigveda-only.",
    )

    previous: PassageSummary | None = None
    next: PassageSummary | None = None
    neighbour_note: str | None = Field(
        default=None,
        description="Why a neighbour is null, when one is: the first and last passage of a "
        "work have no predecessor or successor, and that is not an error.",
    )

    audio: AudioAvailability = Field(default_factory=AudioAvailability)
    parallel_counts: ParallelCounts
    graph_neighbour_count: int | None = Field(
        default=None,
        description="Distinct knowledge nodes this passage links to, excluding its own "
        "text and translation nodes and its structural container.",
    )

    data_status: KnowledgeStatus = KnowledgeStatus.SUPPORTED
    coverage: CoverageView | None = None
    caveats: list[CaveatView] = Field(default_factory=list)
