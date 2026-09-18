"""Aggregate response contracts: the shapes in which a zero cannot be read as absence.

**Why this module is the dangerous one.** Every other surface of this API returns a thing
a reader asked for by name, and a missing thing is visibly missing. An aggregate returns a
*table*, and a table's empty cell reads as a fact about the world. The 100-question
benchmark graded three questions ``MISLEADING`` and two of the three were tables: a metals
grid that dropped the cells it could not match, and a deity-pair table standing in for a
community partition that was never built. Neither answer was wrong about a number. Both
were wrong about what an absent number meant.

So the models here refuse three specific shapes.

*A cell may not be omitted.* :class:`MetalVedaCell` and :class:`CrossVedaCell` are emitted
for every member of their grid, including the empty ones, because a query that returns
only its positive rows lets a reader infer a zero nobody measured. The grids state their
own dimensions in :class:`MatrixShape` so a client can check it received every cell rather
than trusting that it did.

*A cell may not be a bare zero.* Where a count is not established -- the lexical matcher
reached nothing, the layer does not cover this pair, the dimension was never built -- the
count is ``None`` and a status says which of those it is. ``0`` is reserved for a figure
the graph can actually stand behind, and :class:`CrossVedaCellStatus` distinguishes the
four ways a cross-Veda cell can be empty.

*A Veda's figure may not travel without its exclusions.* :class:`InsightEnvelope` will not
construct if ``vedas_reported`` names a corpus for which no :class:`WorkScopeView` is
attached, and the scope is read from the ``Work`` node rather than being a sentence someone
typed. The Samavedic case is why the validator exists: this graph holds the Kauthuma arcika
and not the gana corpus, and the ``Work`` node's own scope string opens "ARCIKA ONLY. THIS
IS NOT THE COMPLETE SAMAVEDA." A Samavedic figure published without that sentence is the
single most misleading string this product can emit, and a rule that depends on an author
remembering it is not a rule.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Any, ClassVar, Self

from pydantic import Field, model_validator

from vedagraph.api.models.common import (
    ApiModel,
    CaveatView,
    CountedByVeda,
    CoverageView,
    EvidenceView,
    KnowledgeStatus,
    PaginationMeta,
    ReferentCertaintyCounts,
)

#: Corpus order used in every per-Veda list in this module. Fixed rather than sorted by
#: size, so two tables built from different layers can be read against each other without
#: re-sorting them in your head -- the same reason
#: :func:`vedagraph.domain.layer_figures.veda_breakdown` fixes its order.
VEDA_ORDER: tuple[str, ...] = ("RV", "AV", "YV", "SV")

#: The six unordered corpus pairs a cross-Veda question can be about, in the graph's own
#: ``veda_pair`` spelling. Enumerated as a constant so the matrix is built from the full
#: product rather than from whatever pairs the data happened to contain, which is exactly
#: how a pair with no edges goes missing from a table.
VEDA_PAIRS: tuple[str, ...] = ("AV-RV", "RV-SV", "RV-YV", "AV-SV", "AV-YV", "SV-YV")


class CostClass(StrEnum):
    """What a caller may expect this endpoint to cost.

    The product's latency target -- median under 150 ms, most under 300 ms -- explicitly
    exempts endpoints labelled as aggregates, and the exemption is worthless unless the
    label is machine-readable. So it is on the response and in the OpenAPI description,
    not in a performance document nobody reads at call time.
    """

    POINT_READ = "POINT_READ"
    """A few indexed lookups. Inside the median target."""

    AGGREGATE = "AGGREGATE"
    """Grouped counts over one or more whole layers. Labelled, and exempt from the median."""

    CENSUS = "CENSUS"
    """A scan proportional to the graph. No latency target; the cost cannot be indexed away."""


class SectionKind(StrEnum):
    """Which of three incommensurable kinds of thing a civilization section holds.

    Kept as an enum on each section rather than as a naming convention, because the
    failure this prevents is a client flattening the three into one list. A measured
    lexical count, a derived statistic and a model-authored interpretation are not three
    confidence levels of the same assertion; the third can be false while the first two
    are exactly right.
    """

    DATA = "DATA"
    """Measured off the corpus: a count of passages, a lexical match, an attestation."""

    DERIVED_METRIC = "DERIVED_METRIC"
    """A statistic computed over the graph and stored with its method and its scope note."""

    INTERPRETIVE_CLAIM = "INTERPRETIVE_CLAIM"
    """A reading, authored by a model, permanently CANDIDATE, and carrying its falsifier."""


class CrossVedaCellStatus(StrEnum):
    """Why a cross-Veda cell holds what it holds. Four ways to be empty, and they differ.

    The distinction is the whole point of the matrix. ``REUSES_TEXT_FROM`` carries 1,684
    edges and every one of them is RV-SV; the other five pairs hold nothing. Read as a
    measured zero, that says the Atharvaveda reuses no Rigvedic text -- which is false,
    since the same pair carries hundreds of undirected parallels in this very graph. The
    directed-reuse layer was assigned for one pair and not the others, and
    ``NOT_ESTABLISHED_FOR_PAIR`` says so while carrying the parallel count that proves it.
    """

    MEASURED = "MEASURED"
    """Edges of this class exist for this pair and ``edges`` is their count."""

    MEASURED_ZERO = "MEASURED_ZERO"
    """The class reaches every other pair, so this pair's zero is a figure, not a gap."""

    NOT_ESTABLISHED_FOR_PAIR = "NOT_ESTABLISHED_FOR_PAIR"
    """The class reaches some pairs and not this one. Not a statement about the texts."""

    CLASS_NOT_CROSS_VEDA = "CLASS_NOT_CROSS_VEDA"
    """Every edge of this class is within one Veda, so it cannot enter a cross-Veda pair."""

    NOT_BUILT = "NOT_BUILT"
    """No layer of this kind exists anywhere in the graph. The absence is about us."""

    UNRECONCILED = "UNRECONCILED"
    """Edge population and node vedas disagree. A defect, surfaced rather than smoothed."""


class MetalEvidenceStatus(StrEnum):
    """The frozen ``metals_by_veda`` grid's own per-cell vocabulary, carried through.

    ``NO_LEXICAL_MATCH`` is a fact about the alias registry. The registry admits attested
    whole-word inflections only -- the bare stem ``ayas`` substring-matches 645 times
    inside unrelated words -- so a cell with no match is a lower bound of zero and never
    an attestation that the corpus does not name the metal.
    """

    LEXICAL_MATCH_MINIMUM = "LEXICAL_MATCH_MINIMUM"
    NO_LEXICAL_MATCH = "NO_LEXICAL_MATCH"


class CapabilityVerdict(StrEnum):
    """The frozen benchmark's grade for a question this product deliberately cannot answer."""

    NOT_ANSWERABLE = "NOT_ANSWERABLE"
    """No query can answer it. The dimension the question asks about is absent."""

    PARTIALLY_ANSWERABLE = "PARTIALLY_ANSWERABLE"
    """Something real and incomplete, safe only where the incompleteness is stated."""


# ---------------------------------------------------------------------------
# Scope, and the envelope that will not ship a figure without it
# ---------------------------------------------------------------------------


class WorkScopeView(ApiModel):
    """One corpus's boundary, quoted from the ``Work`` node that records it.

    Both labels are returned. ``traditional_name`` is what a reader will recognise
    ("Samaveda Samhita") and ``scope_honest_label`` is what this graph actually holds
    ("Samaveda Samhita - Kauthuma arcika only (gana corpus NOT included)"). A UI that
    shows only the first is the reason the second exists, so neither is hidden behind the
    other and ``scope`` carries the graph's own full sentence unedited.
    """

    veda: str
    work_id: str
    traditional_name: str | None = None
    scope_honest_label: str | None = None
    scope: str | None = Field(
        default=None,
        description="The corpus boundary in the graph's own words. Not paraphrased here.",
    )
    completeness: str | None = None
    excluded_corpora: list[str] = Field(
        default_factory=list,
        description="Bodies a reader may believe are included and which are not held.",
    )
    scope_source: str | None = None


def reject_meaningless_empty(
    rows: Sequence[object],
    *,
    status: KnowledgeStatus,
    caveats: Sequence[CaveatView],
    offset: int = 0,
) -> None:
    """Raise if an empty first page would claim SUPPORTED with nothing to explain it.

    The same rule :class:`~vedagraph.api.models.common.Paginated` enforces, factored out
    so a composite response carrying one bounded list inherits it without having to *be* a
    ``Paginated``. Duplicating the rule per model would let one model be written without
    it, and that model is the one that ships.

    ``offset != 0`` is exempt, and the exemption is the point: an empty page at a non-zero
    offset is a paging condition, not a knowledge claim. See
    :func:`offset_overrun_caveat` for what such a page says instead.
    """
    if rows or offset != 0:
        return
    if status is KnowledgeStatus.SUPPORTED and not caveats:
        raise ValueError(
            "An empty result must carry a non-SUPPORTED data_status or a caveat: a bare "
            "empty collection cannot distinguish absence in the corpus from an unbuilt "
            "layer or a matcher that never reached it."
        )


def offset_overrun_caveat(bounds: PaginationMeta) -> CaveatView | None:
    """A caveat for a page emptied by its offset, and never a knowledge status.

    Asking for page four million of a fourteen-row collection is a client arithmetic error.
    Answering it with ``INSUFFICIENT_EVIDENCE`` spends a status that means "evidence exists
    and cannot support the claim" on a paging condition, and a vocabulary spent that way is
    worth less everywhere else in the product -- the reader who has seen it mean "you paged
    off the end" will discount it when it means what it says.

    So ``data_status`` continues to describe the *collection* and this caveat describes the
    *page*. Returns ``None`` where there is nothing to explain.

    **Guarded on a positive total, and that guard is load-bearing.** The text asserts the
    collection is not empty, which is true of an overrun and false of a genuinely empty
    collection -- attached unguarded to an empty one it would contradict the very status it
    points at, which is a worse failure than the silence it replaces. A total of ``None``
    is treated the same way: an unknown total cannot support a claim of non-emptiness.
    """
    if bounds.returned or bounds.offset == 0:
        return None
    if not bounds.total:
        return None
    return CaveatView(
        text=(
            f"This page is empty because offset {bounds.offset:,} is past the end of a "
            f"{bounds.total:,}-row collection. That is a paging condition and not a "
            "finding: data_status above describes the collection, which is not empty."
        ),
        source="pagination",
    )


def reject_mismatched_collection_bounds(
    owner: object, collections: Mapping[str, PaginationMeta], fields: Sequence[str]
) -> None:
    """Raise unless every bounded collection has its own block, describing itself.

    A response carrying several collections and one ``pagination`` block is the shape this
    refuses. It shipped once: a ritual response returned ``returned: 0`` while eight rites
    sat in the body, because the single block described the implement list and the rites
    list beside it was unpaginated. A client reading ``pagination.returned`` concluded the
    response was empty when it was not.

    The check is on ``returned`` against the actual list length, so a block cannot describe
    a collection other than the one it is keyed by -- not by convention, but because the
    model will not construct.
    """
    expected = set(fields)
    missing = sorted(expected - set(collections))
    unknown = sorted(set(collections) - expected)
    if missing or unknown:
        raise ValueError(
            "collection bounds must name every bounded collection and nothing else; "
            f"missing {missing}, unexpected {unknown}"
        )
    for name in fields:
        rows = getattr(owner, name)
        if collections[name].returned != len(rows):
            raise ValueError(
                f"collection bounds for {name!r} report returned="
                f"{collections[name].returned} against {len(rows)} rows actually present: "
                "a bounds block that describes a different collection is how an eight-row "
                "response reported itself empty"
            )


class InsightEnvelope(ApiModel):
    """What every insight response says about itself before it says anything else.

    Three invariants are enforced here rather than trusted to each service.

    *A reported Veda carries its exclusions.* ``vedas_reported`` lists the corpora whose
    figures appear in the payload, and construction fails if any of them has no
    :class:`WorkScopeView`. That is the Samaveda rule generalised: the SV work addresses
    the Kauthuma arcika's 1,844 verses and not the roughly 2,639 ganas, the YV work holds
    no Krishna Yajurveda at all, and the AV work holds no Paippalada -- so every one of the
    four has an exclusion a reader would otherwise not know about.

    *A qualified answer carries a caveat.* Any ``data_status`` other than ``SUPPORTED``
    without a caveat tells a client that something is limited and not what.

    *An aggregate says it is one.* ``cost_class`` is machine-readable so a frontend can
    decide what to put behind a spinner, and so the product's latency target can exempt
    aggregates without the exemption being invisible.
    """

    insight: str = Field(description="Stable identifier for this view, safe to key on.")
    question: str = Field(description="The question this view answers, in words.")
    data_status: KnowledgeStatus
    cost_class: CostClass
    cost_note: str = Field(
        description="What this endpoint scans, so a slow response is legible rather than "
        "surprising."
    )
    vedas_reported: list[str] = Field(
        default_factory=list,
        description="Corpora whose figures appear below. Each one's exclusions are attached.",
    )
    scope_statements: list[WorkScopeView] = Field(default_factory=list)
    coverage: CoverageView | None = None
    caveats: list[CaveatView] = Field(default_factory=list)

    @model_validator(mode="after")
    def _figures_travel_with_their_scope(self) -> Self:
        scoped = {statement.veda for statement in self.scope_statements}
        missing = [veda for veda in self.vedas_reported if veda not in scoped]
        if missing:
            raise ValueError(
                f"figures reported for {', '.join(missing)} with no scope statement: a "
                "per-Veda number without its corpus's exclusions is the shape that makes "
                "an arcika-only Samaveda read as the Samaveda"
            )
        if self.data_status is not KnowledgeStatus.SUPPORTED and not self.caveats:
            raise ValueError(
                f"data_status={self.data_status} with no caveat: a client told the answer "
                "is limited must also be told how"
            )
        return self


# ---------------------------------------------------------------------------
# /stats
# ---------------------------------------------------------------------------


class CorpusFigure(ApiModel):
    """One corpus-level count with the denominator that makes it comparable."""

    name: str
    total: int | None = None
    by_veda: CountedByVeda | None = None
    denominator: dict[str, int] = Field(
        default_factory=dict, description="Per-Veda mantra totals, for normalising."
    )
    note: str | None = None


class DeityPopulationStat(ApiModel):
    """The two deity numbers, each labelled, because they answer different questions.

    ``resolved_deities`` is the population every deity surface in this API uses.
    ``anukramani_ascriptions`` is the raw slot the tradition fills, which holds human
    patrons, danastuti labels naming a gift rather than a recipient, and abstractions ruled
    not to name an addressee. A single
    "number of deities" would have to pick one and would be wrong for half its readers, so
    both ship, with the difference broken out by structure.
    """

    resolved_deities: int
    anukramani_ascriptions: int
    excluded_non_deities: int
    by_structure: dict[str, int] = Field(default_factory=dict)
    note: str


class SeerPopulationStat(ApiModel):
    """Seers and non-seer addressees kept apart.

    The seer label holds nodes that are not seers: the Anukramani's seer slot also names
    deities, abstractions, mythic beings, a plant and an object. A combined figure is a
    category error, so the split is structural here and the non-seer kinds are enumerated
    rather than summarised.
    """

    seers: int
    non_seer_addressees: int
    non_seer_kinds: dict[str, int] = Field(default_factory=dict)
    families: int
    note: str


class CrossVedaRelationshipStat(ApiModel):
    """Cross-Veda connection counts, by class, and never as one total.

    Deliberately not a single figure and deliberately not the graph's relationship count.
    The classes differ in what they assert -- an exact parallel, a directed reuse, a shared
    entity vocabulary -- and one number over all of them would rank a vocabulary overlap
    beside a verbatim repetition. Intra-Veda edges are excluded and counted separately,
    because a quarter of the exact-parallel class is Rigveda-internal.
    """

    relationship_class: str
    cross_veda_edges: int | None = Field(
        default=None,
        description="Edges joining two corpora. Null where the class was never built; 0 "
        "where it exists and every edge of it stays inside one corpus.",
    )
    within_one_veda_edges: int
    pairs_reached: list[str] = Field(default_factory=list)
    resemblance_kind: str | None = None
    note: str = Field(
        description="What this class asserts and what its reach does not mean, on the row."
    )


class StatsResponse(InsightEnvelope):
    """Product-level corpus statistics.

    **The raw relationship count is absent on purpose.** Most of this graph's edges are one
    annotation layer's projection of a container label onto its members. Published as a
    headline the total measures the build rather than the corpus, and it invites a
    comparison with other knowledge graphs that means nothing. What is published instead is
    the population of each thing a reader can ask about, each with the caveat that makes it
    readable.
    """

    corpus: list[CorpusFigure] = Field(default_factory=list)
    entity_populations: list[CorpusFigure] = Field(default_factory=list)
    deities: DeityPopulationStat
    seers: SeerPopulationStat
    cross_veda_relationships: list[CrossVedaRelationshipStat] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# /insights/cross-veda
# ---------------------------------------------------------------------------


class CrossVedaCell(ApiModel):
    """One (relationship class x corpus pair) cell, typed even when it is empty.

    ``edges`` is ``None`` for every status except ``MEASURED`` and ``MEASURED_ZERO``, which
    is what stops a client rendering an unbuilt layer as a nought. Where the cell is
    ``NOT_ESTABLISHED_FOR_PAIR``, ``related_edges_on_pair`` carries the measured number of
    cross-Veda edges the *other* classes hold for the same pair -- so a reader who sees no
    directed reuse between the Atharvaveda and the Rigveda also sees the parallels that
    make "the AV does not reuse the RV" impossible to conclude.
    """

    relationship_class: str
    pair: str
    edges: int | None = None
    status: CrossVedaCellStatus
    related_edges_on_pair: int | None = Field(
        default=None,
        description="Cross-Veda edges the other classes carry for this pair. Present where "
        "this cell is empty, as the measure of what its emptiness does not mean.",
    )
    note: str = Field(
        description="Why the cell reads as it does, on the cell. A caveat elsewhere in the "
        "payload does not travel with a row a client renders on its own."
    )


class CrossVedaPairRow(ApiModel):
    """Every class's cell for one corpus pair."""

    pair: str
    vedas: list[str]
    cells: list[CrossVedaCell] = Field(default_factory=list)
    measured_edges_total: int = Field(
        description="Sum of the cells carrying a measured count. Not a strength score: the "
        "classes it sums assert different things."
    )


class CrossVedaClassView(ApiModel):
    """What one relationship class is, and how far it reaches."""

    relationship_class: str
    resemblance_kind: str
    cross_veda_edges: int | None = None
    within_one_veda_edges: int = 0
    pairs_reached: list[str] = Field(default_factory=list)
    directed: bool | None = Field(
        default=None,
        description="Whether the class records which corpus is the source. Null where the "
        "class carries no cross-Veda edges at all.",
    )
    population_status: str


class MatrixShape(ApiModel):
    """The grid's own dimensions, so a client can verify it got every cell.

    A completeness claim a consumer can check beats one it has to trust. This project has
    twice certified an absence against the wrong surface; a matrix that states 48 cells and
    ships 41 fails a client-side assertion instead of quietly under-reporting.
    """

    rows: int
    columns: int
    cells_expected: int
    cells_returned: int
    cells_by_status: dict[str, int] = Field(default_factory=dict)


class MethodCensusRow(ApiModel):
    """One row of the frozen relatedness-method census, including its unbuilt row."""

    resemblance_kind: str
    method: str
    edges: int | None = None
    population_status: str
    note: str | None = None


class CrossVedaMatrixResponse(InsightEnvelope):
    """The full corpus-pair by relationship-class matrix, with every cell typed.

    Enumerated from the constant six pairs and the constant class list rather than from the
    pairs the data happens to contain. Building it the other way round is how five of
    ``REUSES_TEXT_FROM``'s six pairs disappear from a table and a reader concludes that only
    the Samaveda reuses Rigvedic text.

    Two rows carry no edges by construction and are here anyway, and they carry different
    statuses because the reasons differ. The semantic resemblance row is ``NOT_BUILT`` -- no
    embedding, no vector index and no asserted resemblance exists anywhere in this graph.
    The semantic assertion row is ``CLASS_NOT_CROSS_VEDA``: the layer exists, holds 35,131
    assertions and reaches all four corpora, and still cannot contribute to a pair, because
    an assertion is a predication about one passage rather than a relation between two.

    That row read ``NOT_BUILT`` "because all of its assertions are Rigvedic". The premise
    was false -- the layer reaches AV, YV and SV -- and the status told a reader the layer
    does not exist anywhere in this graph, beside a measured total in the same cell that
    said otherwise.
    """

    pairs: list[CrossVedaPairRow] = Field(default_factory=list)
    relationship_classes: list[CrossVedaClassView] = Field(default_factory=list)
    method_census: list[MethodCensusRow] = Field(default_factory=list)
    shape: MatrixShape


# ---------------------------------------------------------------------------
# /insights/metals -- the Q10 contract
# ---------------------------------------------------------------------------


class MetalVedaCell(ApiModel):
    """One metal in one Veda. Present whatever the matcher found.

    ``matched_mantras`` is ``None`` and never ``0`` where nothing matched, because a lexical
    miss is a fact about the alias registry. ``source_witness`` is the locator of a verse
    this Veda is recorded to attest for the metal even though no alias reaches it -- the
    Yajurvedic ``ayas`` at VSM 18.13 is the one such cell in this graph, and it is typed in
    the row so that a client rendering only rows still cannot conclude the Yajurveda does
    not name the metal.
    """

    veda: str
    matched_mantras: int | None = None
    per_1000_mantras: float | None = None
    corpus_mantras: int = Field(description="Mantras in this corpus: the denominator.")
    evidence_status: MetalEvidenceStatus
    knowledge_status: KnowledgeStatus
    sample_aliases: list[str] = Field(default_factory=list)
    source_witness: str | None = Field(
        default=None,
        description="Citation of a verse this corpus is recorded to attest for this metal "
        "despite the lexical miss. Its presence means the cell is a matcher limitation and "
        "not an absence from the text.",
    )
    note: str


class MetalRow(ApiModel):
    """One metal across all four corpora, with the ordering the normalisation produces."""

    metal: str
    entity_key: str
    preferred_label_sa: str | None = None
    short_description: str | None = None
    by_veda: list[MetalVedaCell] = Field(default_factory=list)
    raw_ordering: list[str] = Field(
        default_factory=list, description="Vedas ranked by raw matched mantras, highest first."
    )
    normalised_ordering: list[str] = Field(
        default_factory=list, description="Vedas ranked per 1,000 mantras, highest first."
    )
    ordering_inverts: bool = Field(
        default=False,
        description="True where normalising changes the ranking. Reported per metal because "
        "a share and a raw count can disagree, and the raw count is the one a reader sees.",
    )
    ordering_note: str | None = None


class DeclaredLexicalGap(ApiModel):
    """A cell the project knows is wrong and refuses to silently correct or hide.

    Registering an alias for the Yajurvedic ``ayas`` would land eleven wrong-sense mentions,
    because the elided Devanagari folds to the token of the relative pronoun. So the cell
    stays ``NO_LEXICAL_MATCH`` and this row states the locator, what else the same verse is
    measured to name, and the frozen reason -- the alternative being an API that quietly
    asserts the Yajurveda has no metal.
    """

    entity_key: str
    display_label: str
    veda: str
    source_witness: str | None = None
    co_attested_at_witness: list[str] = Field(
        default_factory=list,
        description="Metals the mention layer is measured to reach at the same verse.",
    )
    evidence_status: MetalEvidenceStatus = MetalEvidenceStatus.NO_LEXICAL_MATCH
    reason: str


class MetalsInsightResponse(InsightEnvelope):
    """The complete metal-by-Veda grid: every registered metal against every corpus.

    This is the endpoint the Q10 regression protects. The frozen query already returns the
    full grid with a ``NO_LEXICAL_MATCH`` marker per cell; what this adds is that an
    unmatched cell's count is null rather than nought, that the known Yajurvedic gap carries
    its locator in its own cell as well as in ``declared_gaps``, and that the normalisation
    which reorders gold from RV-first to AV-first is reported per metal rather than left for
    a reader to notice.
    """

    metals: list[MetalRow] = Field(default_factory=list)
    declared_gaps: list[DeclaredLexicalGap] = Field(default_factory=list)
    shape: MatrixShape


# ---------------------------------------------------------------------------
# /insights/material-culture, /insights/rituals, /insights/atharvaveda/concerns
# ---------------------------------------------------------------------------


class VedaCountRow(ApiModel):
    """A named thing counted per corpus, raw and normalised, with its denominators.

    Used wherever an insight ranks entities across the four Samhitas. The Rigveda is 5.7
    times the Yajurveda by mantra count, so ``by_veda`` alone partly ranks corpus size;
    per-1,000 figures sit beside it rather than replacing it, because normalising can invert
    the ordering and a client needs both to know that it did.
    """

    label: str
    kind: str | None = None
    entity_key: str | None = None
    total_mantras: int | None = None
    by_veda: CountedByVeda
    per_1000_by_veda: dict[str, float] = Field(default_factory=dict)
    vedas_reached: int | None = None
    evidence_status: str | None = None
    note: str | None = None


class MaterialCultureResponse(InsightEnvelope):
    """Crops, animals, metals, rivers, tribes and curated ritual implements.

    Every figure is a Sanskrit lexical-match minimum, which is why each row carries an
    ``evidence_status`` rather than the response carrying one for all of them: alias recall
    differs sharply by entity, and the frozen ``ritual_objects_recurring`` caveat measures
    the shortfall for the sacrificial post at 6 reached against 11 attested.
    """

    category: str
    rows: list[VedaCountRow] = Field(default_factory=list)
    pagination: PaginationMeta
    categories_available: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _empty_category_explains_itself(self) -> Self:
        reject_meaningless_empty(
            self.rows,
            status=self.data_status,
            caveats=self.caveats,
            offset=self.pagination.offset,
        )
        return self


class RitualCoverageView(ApiModel):
    """What the ritual layer holds, stated as the numbers that bound it.

    The inventory is not a taxonomy of Vedic ritual, and the length of a list is not evidence
    of how many there are, so every bounding figure here is measured and returned rather than
    described as "curated".

    The two step layers are separate fields because they are separate claims. ``step_edges``
    counts what a Samhita text numbers in its own words; ``procedure_step_edges`` counts what
    a Srautasutra or Grhyasutra prints. Summing them would assert a procedural coverage the
    Samhita layer does not have, and reporting only the first — which this view did for a
    whole import — states that no rite has a recoverable sequence while thousands of located
    sutra steps sit in the graph.
    """

    rituals_modelled: int
    rituals_with_steps: int = Field(
        description="Rites with at least one step the Samhita text itself numbers."
    )
    step_edges: int = Field(description="Samhita-numbered step edges, whole graph.")
    rituals_with_procedure: int | None = Field(
        default=None, description="Rites with at least one sutra-attested procedural step."
    )
    procedure_step_edges: int | None = Field(
        default=None, description="Sutra-attested procedural step edges, whole graph."
    )
    procedure_partial_steps: int | None = Field(
        default=None,
        description="Of those, the ones stating a position without printing the run it "
        "falls in. A high share means the sequences are located steps, not procedures.",
    )
    procedure_source_works: int | None = Field(
        default=None,
        description="Distinct source works cited. None of them has a node in this graph.",
    )
    implements_curated: int | None = None
    implements_reached_by_mentions: int | None = None
    statement: str


class RitualObjectRow(ApiModel):
    """One curated ritual implement and its measured lexical reach."""

    implement: str
    registry_type: str | None = Field(
        default=None,
        description="What the registry types it as. The axe is a weapon and a ritual tool.",
    )
    matched_mantras_minimum: int
    vedas_with_matches: int
    curated_rituals: int
    evidence_status: str


class RitualSummaryRow(ApiModel):
    """One of the modelled rites, with its curated inventory sizes."""

    ritual: str
    entity_key: str | None = None
    matched_mantras: int
    steps: int
    objects: int
    offerings: int
    substances: int
    devatas: int
    inventory_coverage: str | None = None


class RitualsInsightResponse(InsightEnvelope):
    """The ritual layer, labelled PARTIAL because it is -- and the Q25 answer.

    Q25 asks which ritual objects recur most, and the honest answer is a ranking over a
    curated implement class whose alias recall is measured and incomplete. The rows are
    real; the class is not a census of Vedic ritual apparatus, and the ceiling is the corpus
    itself, since the Brahmana and Srautasutra prose that describes the apparatus is not
    held at all.
    """

    _BOUNDED: ClassVar[tuple[str, ...]] = ("objects", "rituals")

    coverage_view: RitualCoverageView
    objects: list[RitualObjectRow] = Field(default_factory=list)
    rituals: list[RitualSummaryRow] = Field(default_factory=list)
    collections: dict[str, PaginationMeta] = Field(
        description="Bounds per collection, keyed by the field each one describes. Two "
        "collections travel here and one shared block described only the first, so a client "
        "reading it concluded an eight-row response was empty."
    )
    not_covered: list[str] = Field(
        default_factory=list,
        description="Named things a reader would expect here and which are absent, with the "
        "reason. An empty list would assert completeness.",
    )

    @model_validator(mode="after")
    def _partial_layer_states_what_is_missing(self) -> Self:
        reject_mismatched_collection_bounds(self, self.collections, self._BOUNDED)
        reject_meaningless_empty(
            self.objects,
            status=self.data_status,
            caveats=self.caveats,
            offset=self.collections["objects"].offset,
        )
        if not self.not_covered:
            raise ValueError(
                "the ritual layer is PARTIAL by construction, so not_covered may not be "
                "empty: an empty list would assert that the modelled rites are a taxonomy "
                "of Vedic ritual"
            )
        return self


class ConcernEvidenceRow(ApiModel):
    """A concern or affliction, with the predicate and tier that reached it.

    ``ADDRESSES_CONCERN`` is TIER_B and ``PROTECTS_FROM`` and ``TREATS`` are TIER_D, so the
    predicate is a returned column and never a filter, and the rows must not be summed:
    sapatna is both addressed and protected from, and that duplication is the same mention
    read two ways rather than two findings.
    """

    target: str
    kind: str | None = None
    condition_kind: str | None = Field(
        default=None,
        description="AFFLICTION, THREAT or PATHOGEN_OR_CAUSE. A demon is not a disease.",
    )
    predicate: str
    tier: str | None = None
    passages: int
    by_veda: CountedByVeda


class AtharvavedaConcernsResponse(InsightEnvelope):
    """What the Atharvaveda is about, with its afflictions kept apart from its demons.

    The V3.2 pass found the affliction question being answered with demons: of the mention
    edges reaching a condition, hundreds reached a threat or a cause rather than an
    affliction, so sorcery and worms were ranking as diseases. The two are split here by
    ``condition_kind`` on the row, and the apotropaic reading stays reachable rather than
    being filtered away.

    All four corpora are reported deliberately. The Atharvaveda dominates every concern row,
    and a reader shown only the AV column cannot tell whether that is Atharvavedic
    specialisation or the only column that was measured.
    """

    _BOUNDED: ClassVar[tuple[str, ...]] = (
        "concerns",
        "afflictions",
        "protection_and_treatment",
        "social_rites",
        "stated_remedy",
    )

    concerns: list[VedaCountRow] = Field(default_factory=list)
    afflictions: list[VedaCountRow] = Field(default_factory=list)
    protection_and_treatment: list[ConcernEvidenceRow] = Field(default_factory=list)
    social_rites: list[VedaCountRow] = Field(default_factory=list)
    #: GAP-ENTITY_COVERAGE-003. The remedy side of the question, which this endpoint
    #: published as unanswerable for two rounds on a premise that was false. The caveat
    #: stood here for two rounds saying "the registry has no healing entity -- bhesaja
    #: was never curated", which was false, and
    #: ``VG:CONCEPT:BHESAJA-HEALING`` had been in the registry all along with 7 registered
    #: Sanskrit aliases and 108 mention edges carrying verbatim verse evidence across all
    #: four corpora. A reader could reach afflictions and plants and was told the remedy
    #: was unreachable.
    stated_remedy: list[VedaCountRow] = Field(default_factory=list)
    collections: dict[str, PaginationMeta] = Field(
        description="Bounds per collection, keyed by the field each one describes. Five "
        "collections travel here, so one shared block would describe four of them wrongly."
    )

    @model_validator(mode="after")
    def _empty_concerns_explain_themselves(self) -> Self:
        reject_mismatched_collection_bounds(self, self.collections, self._BOUNDED)
        reject_meaningless_empty(
            self.concerns,
            status=self.data_status,
            caveats=self.caveats,
            offset=self.collections["concerns"].offset,
        )
        return self


# ---------------------------------------------------------------------------
# /insights/formula-diffusion
# ---------------------------------------------------------------------------


class FormulaSpanRow(ApiModel):
    """How many formula families reach one corpus, and how many reach four."""

    vedas_reached: int
    cross_veda: bool
    families: int
    memberships: int
    occurrences: int


class FormulaFamilyRow(ApiModel):
    """One widely-spread formula family and its per-corpus occurrence counts."""

    representative: str
    members: int
    core: int | None = None
    expansions: int | None = None
    variants: int | None = None
    occurrences: int
    occurrences_per_veda: dict[str, int] = Field(default_factory=dict)
    tier: str | None = None


class ReuseWitnessRow(ApiModel):
    """One Samavedic verse and the Rigvedic verse it is measured to reuse."""

    samaveda: str
    rigveda: str
    match_level: str | None = Field(
        default=None,
        description="Comparison surface the match was reached on. Blank where the edge "
        "predates level recording, which is not the same as a weak match.",
    )
    tier: str | None = None


class FormulaDiffusionResponse(InsightEnvelope):
    """How shared wording spreads across the four Samhitas.

    A formula family is a representative wording plus everything containing or closely
    resembling it, so ``vedas_reached`` is a property of shared diction and not of
    demonstrated transmission. The single-Veda families are the baseline the cross-Veda ones
    should be read against rather than a separate finding, which is why the span census is
    returned whole instead of filtered to the four-Veda rows.
    """

    _BOUNDED: ClassVar[tuple[str, ...]] = (
        "span_census",
        "widest_families",
        "reuse_witnesses",
    )

    span_census: list[FormulaSpanRow] = Field(default_factory=list)
    widest_families: list[FormulaFamilyRow] = Field(default_factory=list)
    reuse_witnesses: list[ReuseWitnessRow] = Field(default_factory=list)
    collections: dict[str, PaginationMeta] = Field(
        description="Bounds per collection, keyed by the field each one describes. The span "
        "census is complete and the other two are pages, and one block cannot say both."
    )

    @model_validator(mode="after")
    def _empty_census_explains_itself(self) -> Self:
        reject_mismatched_collection_bounds(self, self.collections, self._BOUNDED)
        reject_meaningless_empty(
            self.span_census,
            status=self.data_status,
            caveats=self.caveats,
            offset=self.collections["span_census"].offset,
        )
        return self


# ---------------------------------------------------------------------------
# /insights/civilization -- three kinds of thing, kept apart
# ---------------------------------------------------------------------------


class CivilizationDataRow(ApiModel):
    """A measured attestation. The strongest kind of row in the civilization view."""

    kind: str
    entities: int
    passages: int
    vedas_reached: int
    vedas: list[str] = Field(default_factory=list)
    evidence_basis: str = "SANSKRIT_LEXICAL_MENTION"


class DerivedMetricRow(ApiModel):
    """A stored statistic, with the method and scope note that make it readable.

    ``value`` and ``values`` are separate fields because the layer stores both a scalar and
    a JSON map depending on the metric, and coercing one into the other would either lose
    the per-Veda breakdown or invent a total. ``scope_note`` is the metric's own warning --
    the attribution metrics say in as many words that a zero for a non-Rigvedic corpus means
    that corpus has no attribution layer -- and it is carried unedited.
    """

    metric_name: str
    metric_id: str
    display_label: str | None = None
    metric_family: str | None = None
    dimension: str | None = None
    subject: str | None = None
    subject_key: str | None = None
    value: float | None = None
    values: dict[str, Any] | None = None
    interpretation: str | None = None
    method: str | None = None
    scope_note: str | None = None
    quality_tier: str | None = None
    knowledge_layer: str | None = None


class InterpretiveClaimRow(ApiModel):
    """A reading, with what would refute it.

    ``falsifier`` is the field that makes this object a different kind of thing from a
    measurement, and it is required rather than optional for that reason: a claim that
    cannot say what would refute it is not a claim this API will publish beside a count.
    ``about`` and ``about_basis`` carry the discriminator that stopped a cross-category
    disagreement being read as recorded scholarly dissent about the Vedas.
    """

    claim_id: str
    claim_text: str
    claim_type: str | None = None
    about: str | None = Field(
        default=None,
        description="What the claim is about: VEDIC_TEXT, DATASET or TRADITIONAL_APPARATUS. "
        "A claim about this dataset and a claim about the corpus are not comparable.",
    )
    about_basis: str | None = None
    asserted_by: str | None = None
    confidence: str | None = Field(
        default=None, description="The claim's own qualitative grade. Not a probability."
    )
    status: str | None = None
    scope: str | None = None
    falsifier: str
    method: str | None = None
    quality_tier: str | None = None
    supported_by_passages: list[str] = Field(default_factory=list)
    supported_by_statistics: list[str] = Field(default_factory=list)
    contradicts: list[str] = Field(default_factory=list)


class CivilizationSection(ApiModel):
    """One of the three sections, carrying its kind and the reason it is separate."""

    section_kind: SectionKind
    title: str
    what_this_is: str
    data_status: KnowledgeStatus
    total_available: int | None = None
    returned: int
    caveats: list[CaveatView] = Field(default_factory=list)
    data_rows: list[CivilizationDataRow] = Field(default_factory=list)
    metric_rows: list[DerivedMetricRow] = Field(default_factory=list)
    claim_rows: list[InterpretiveClaimRow] = Field(default_factory=list)

    @model_validator(mode="after")
    def _rows_match_the_declared_kind(self) -> Self:
        """A section may only carry the row type its ``section_kind`` names.

        The flattening this endpoint exists to prevent would arrive as a claim row in a data
        section long before it arrived as a design decision, so the model refuses it.
        """
        populated = {
            SectionKind.DATA: bool(self.data_rows),
            SectionKind.DERIVED_METRIC: bool(self.metric_rows),
            SectionKind.INTERPRETIVE_CLAIM: bool(self.claim_rows),
        }
        wrong = [
            kind.value
            for kind, filled in populated.items()
            if filled and kind is not self.section_kind
        ]
        if wrong:
            raise ValueError(
                f"a {self.section_kind} section carries {', '.join(wrong)} rows: "
                "interpretation must not be flattened into fact"
            )
        return self


class CivilizationResponse(InsightEnvelope):
    """What the corpus says about its world, in three sections that are not one list.

    ``DATA`` is what the text is measured to name. ``DERIVED_METRIC`` is what this project
    computed over that. ``INTERPRETIVE_CLAIM`` is what a model read into it, permanently
    CANDIDATE, and two of the claims contradict each other on purpose. Presenting the three
    as a single ranked feed is the failure mode; the sections are separately typed,
    separately statused and separately caveated so that a client has to choose to conflate
    them rather than doing it by accident.
    """

    sections: list[CivilizationSection] = Field(default_factory=list)
    collections: dict[str, PaginationMeta] = Field(
        description="Bounds per section, keyed by `section_kind`. The same vocabulary the "
        "other bounded insights use: this view's three sections are three separately paged "
        "collections, and one of them once ignored `limit` entirely."
    )

    @model_validator(mode="after")
    def _all_three_kinds_are_present(self) -> Self:
        kinds = {section.section_kind for section in self.sections}
        missing = [kind.value for kind in SectionKind if kind not in kinds]
        if missing:
            raise ValueError(
                f"civilization view missing section(s) {', '.join(missing)}: the point of "
                "the view is the contrast between the three, so a missing section changes "
                "what the present ones appear to be"
            )
        return self

    @model_validator(mode="after")
    def _every_section_is_bounded_by_its_own_block(self) -> Self:
        """Each section's bounds must describe that section and agree with its rows.

        The sibling of :func:`reject_mismatched_collection_bounds`, written out here because
        these collections live inside ``sections`` rather than in top-level fields. The
        defect is the same one and it shipped here too: the interpretation section reported
        ``returned: 6`` under ``limit=5`` because it was never paged at all, while the two
        beside it were.
        """
        expected = {section.section_kind.value for section in self.sections}
        missing = sorted(expected - set(self.collections))
        unknown = sorted(set(self.collections) - expected)
        if missing or unknown:
            raise ValueError(
                "civilization bounds must name every section and nothing else; "
                f"missing {missing}, unexpected {unknown}"
            )
        for section in self.sections:
            rows = len(section.data_rows) + len(section.metric_rows) + len(section.claim_rows)
            bounds = self.collections[section.section_kind.value]
            if bounds.returned != rows or section.returned != rows:
                raise ValueError(
                    f"the {section.section_kind} section reports "
                    f"bounds.returned={bounds.returned} and section.returned="
                    f"{section.returned} against {rows} rows actually present: a section "
                    "that is not paged cannot claim to be"
                )
        return self


# ---------------------------------------------------------------------------
# /insights/capabilities -- the Q23 / Q25 contract
# ---------------------------------------------------------------------------


class CapabilityMeasurement(ApiModel):
    """A figure measured to establish a limit, with what it does and does not mean.

    A zero here is the point rather than an accident: no node in this graph carries a
    community assignment, and this row is where that is said with the count beside it. The
    ``means`` field is required so the zero cannot be read on its own.
    """

    name: str
    value: int | None = None
    means: str


class CapabilityLimit(ApiModel):
    """One question this product will not answer, and why refusing is the answer.

    Modelled on the frozen benchmark's own verdicts. ``NOT_ANSWERABLE`` is not a sub-grade
    of partial -- it says the dimension the question asks about is absent from the graph --
    and the response that serves it must be a typed refusal rather than an empty list,
    because an empty list is indistinguishable from a corpus that is silent.
    """

    limit_id: str
    question_number: int | None = None
    question: str
    verdict: CapabilityVerdict
    benchmark_verdict: CapabilityVerdict | None = Field(
        default=None,
        description="The frozen V3.3 benchmark's grade, kept beside the live one. They can "
        "differ, and when they do the difference is the finding: the graph has moved since "
        "the benchmark was frozen, and copying the frozen grade forward would publish a "
        "limitation that no longer holds.",
    )
    data_status: KnowledgeStatus
    why: str = Field(description="What is missing, in terms of the graph rather than the corpus.")
    what_this_is_not: str = Field(
        description="The false conclusion this refusal exists to prevent."
    )
    measurements: list[CapabilityMeasurement] = Field(default_factory=list)
    safe_alternative: str | None = Field(
        default=None, description="A question this graph can answer that is near this one."
    )
    what_would_change_it: str | None = Field(
        default=None, description="The acquisition or build that would make it answerable."
    )
    endpoint: str | None = Field(
        default=None, description="Where the partial or alternative answer is served."
    )
    caveats: list[CaveatView] = Field(default_factory=list)


class CapabilitiesResponse(InsightEnvelope):
    """The catalogue of what not to ask, as data a frontend can enumerate.

    Served so a client can discover the boundary instead of finding it by getting an empty
    list back from a plausible question. Every entry is a graded benchmark verdict with the
    live measurement that establishes it, so the catalogue cannot drift from the graph the
    way a hand-maintained limitations page would.
    """

    limits: list[CapabilityLimit] = Field(default_factory=list)
    total_available: int
    requested_question: int | None = None
    benchmark_not_answerable_total: int = Field(
        default=0,
        description="How many questions the frozen 100-question benchmark graded "
        "NOT_ANSWERABLE. The population this catalogue must cover.",
    )
    benchmark_not_answerable_published: int = Field(
        default=0,
        description="How many of those this catalogue publishes a probed card for. The "
        "catalogue published 7 against 21 once, and said so rather than implying "
        "completeness; these two fields are what make that claim checkable.",
    )
    unpublished_not_answerable: list[int] = Field(
        default_factory=list,
        description="Benchmark question numbers graded NOT_ANSWERABLE with no card here. "
        "Empty is the closed state, and it is a measurement rather than an assurance.",
    )

    @model_validator(mode="after")
    def _the_published_count_must_match_the_cards(self) -> Self:
        """The completeness claim is recomputed from ``limits``, never asserted.

        A hand-set ``benchmark_not_answerable_published`` is exactly the sort of figure
        typed into a payload that nothing checks. Deriving it here means a card that is
        dropped moves the number and repopulates ``unpublished_not_answerable``.
        """
        if self.requested_question is not None:
            return self
        covered = {
            limit.question_number
            for limit in self.limits
            if limit.question_number is not None
            and limit.benchmark_verdict is CapabilityVerdict.NOT_ANSWERABLE
        }
        if len(covered) != self.benchmark_not_answerable_published:
            raise ValueError(
                f"benchmark_not_answerable_published says "
                f"{self.benchmark_not_answerable_published} but {len(covered)} cards carry a "
                "NOT_ANSWERABLE benchmark verdict"
            )
        return self

    @model_validator(mode="after")
    def _a_refusal_is_never_an_empty_list(self) -> Self:
        if not self.limits and self.requested_question is not None:
            raise ValueError(
                "a capability lookup that matched nothing must be a 404, not an empty list: "
                "an empty capability list asserts that the product has no limits"
            )
        reject_meaningless_empty(self.limits, status=self.data_status, caveats=self.caveats)
        return self


# ---------------------------------------------------------------------------
# /insights/devatas/{id}/by-book, /by-metre, /dispersion -- the three viz blockers
# ---------------------------------------------------------------------------


class CellStatus(StrEnum):
    """Why a cell in a deity aggregate holds the value it holds.

    ``MEASURED_ZERO`` and ``NOT_BUILT`` both render as an empty cell and mean opposite
    things: the first says the deity is not named in that book and the layer looked, the
    second says the layer does not reach that corpus and nothing was looked at. A heatmap
    that drew both as a pale square would assert the Samaveda has no metre.
    """

    MEASURED = "MEASURED"
    MEASURED_ZERO = "MEASURED_ZERO"
    NOT_BUILT = "NOT_BUILT"


class BookCountRow(ApiModel):
    """One book of one corpus, with the deity's count in it and the book's own size.

    ``denominator`` is the book's mantra total and it is not optional. Mandala 9 is four
    times the size of Mandala 2; a heatmap read on raw counts says the Soma book is where
    every deity lives.
    """

    book_key: str
    book_label: str
    veda: str
    count: int | None = Field(
        default=None, description="Null unless status is MEASURED or MEASURED_ZERO."
    )
    denominator: int = Field(description="Mantras in this book.")
    per_1000: float | None = None
    status: CellStatus = CellStatus.MEASURED
    note: str | None = None


class DevataByBookResponse(InsightEnvelope):
    """VIZ_BLOCKER_02. The per-book aggregate a deity x mandala heatmap needs.

    The blocker's own warning is the reason this is an endpoint rather than a client-side
    roll-up of ``/devatas/{id}/passages``: that route is capped at 200 rows a page, so a
    heatmap built by paging it would truncate silently and a truncated heatmap is
    indistinguishable from a sparse one.
    """

    devata_id: str
    display_label: str
    basis: str = Field(
        description="Which layer the counts come from: 'naming' spans four corpora, "
        "'ascription' reaches the Rigveda alone. Never mixed in one response."
    )
    books: list[BookCountRow] = Field(default_factory=list)
    total: int = Field(description="Sum over the measured books. Equals the naming total.")


class MetreCountRow(ApiModel):
    """One deity x metre cell."""

    metre_key: str
    metre_label: str
    veda: str
    count: int | None = None
    status: CellStatus = CellStatus.MEASURED
    note: str | None = None


class DevataByMetreResponse(InsightEnvelope):
    """VIZ_BLOCKER_03. The deity x metre aggregate, with two thirds of it typed unbuilt.

    The blocker called this low priority because "the metre layer reaches only RV and AV,
    so the matrix would be two-thirds hatched -- honest, but thin". Thin and honest is the
    right trade and it is served here: the Samavedic and Yajurvedic rows are present and
    typed ``NOT_BUILT`` rather than omitted, because a matrix with two corpora silently
    missing is read as a matrix of two corpora.
    """

    devata_id: str
    display_label: str
    cells: list[MetreCountRow] = Field(default_factory=list)
    vedas_with_a_metre_layer: list[str] = Field(default_factory=list)
    total: int


class DispersionSeries(ApiModel):
    """Where in one corpus a deity is attested, as ordinal positions and nothing else.

    ``positions`` are 1-based indices into the corpus's canonical mantra order, not
    citations and not payloads. That is the point: an Invocation Landscape for a major
    deity needs every attesting position, and returning the passages would be 2,305 objects
    behind an endpoint capped at 200 rows a page.
    """

    veda: str
    positions: list[int] = Field(default_factory=list)
    denominator: int = Field(description="Mantras in this corpus, the axis length.")
    status: CellStatus = CellStatus.MEASURED
    note: str | None = None


class DevataDispersionResponse(InsightEnvelope):
    """VIZ_BLOCKER_01. Dispersion for a deity of any size, unbounded by the page cap."""

    devata_id: str
    display_label: str
    basis: str
    by_veda: dict[str, DispersionSeries] = Field(default_factory=dict)
    total_positions: int


# ---------------------------------------------------------------------------
# /insights/devatas/{id}
# ---------------------------------------------------------------------------


class DedicationRouteRow(ApiModel):
    """One resolved-dedication route, with the method that produced it.

    ``ascribed_total`` sums two routes that are not the same kind of evidence:
    ``HAS_DEVATA`` is the Anukramani naming a deity the registry already holds, and
    ``HAS_DEVATA_DERIVED`` is that dedication recovered from a Sanskrit adjective by
    morphology. A single total with a single method string would be wrong about one of
    them, so the decomposition is published beside the total rather than folded into it,
    and each row carries its own method. GAP-ATTRIBUTION-002 clause 2 -- *"returns AV in
    ascribed_scope with its method stated"*.
    """

    predicate: str = Field(description="The graph predicate this row counts.")
    method: str = Field(description="How the dedication was arrived at, as a stable code.")
    means: str = Field(description="What this route asserts, and what it does not.")
    vedas_reached: list[str] = Field(
        default_factory=list, description="Veda codes this route reaches for this deity."
    )
    measured: dict[str, int] = Field(
        default_factory=dict, description="Passages per Veda on this route."
    )
    passages: int = Field(description="Passages this route reaches, summed over its own Vedas.")


class DevataInsightResponse(InsightEnvelope):
    """A deity's measured reach, with naming and ascription never added together.

    ``named`` counts passages whose text says the deity's name and spans all four corpora.
    ``ascribed`` counts the Anukramani's dedication and reaches the corpora an Anukramani
    apparatus was ingested for -- the Rigveda directly, the Atharvaveda through the
    morphological resolution of its descriptors. They diverge in both directions and
    neither is the corrected version of the other, so they are separate fields with
    separate scopes, and the per-1,000 figures are what a cross-corpus comparison should be
    read on.

    ``ascribed_total`` and ``ascribed_scope`` are computed from ONE pattern over both
    dedication routes, so the figure and the scope label cannot disagree about which routes
    they cover; ``ascription_routes`` decomposes the total by route and method.
    """

    devata_id: str
    display_label: str
    structure: str | None = None
    is_resolved_deity: bool = Field(
        description="Whether this node is in the resolved deity population. False for the "
        "human patrons, gift-praise labels and ruled-out abstractions the Anukramani also "
        "names."
    )
    named_by_veda: VedaCountRow
    named_total: int | None = None
    certainty: ReferentCertaintyCounts
    ascribed_total: int | None = None
    ascribed_scope: list[str] = Field(default_factory=list)
    ascription_routes: list[DedicationRouteRow] = Field(
        default_factory=list,
        description="The dedication total decomposed by route and method. Every route is "
        "present even where it reaches nothing, so a zero is distinguishable from a route "
        "the response omitted.",
    )
    ascription_note: str
    mention_surplus: int | None = Field(
        default=None,
        description="named minus ascribed. Negative means a deity whole hymns are dedicated "
        "to whose name the verses rarely say.",
    )
    derived_metrics: list[DerivedMetricRow] = Field(default_factory=list)
    interpretive_claims: list[InterpretiveClaimRow] = Field(default_factory=list)
    evidence: EvidenceView | None = None
