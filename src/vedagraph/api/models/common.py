"""The shared response vocabulary.

This module is the reason the API can keep the benchmark's 0-MISLEADING property. The
100-question grading found that the dangerous failure was never a wrong number -- it was a
confident empty answer. A query returned no rows, a reader inferred absence from the text,
and nothing in the payload distinguished "the Vedas do not say this" from "we did not
build that layer" or "the matcher could not reach it".

So an empty list is never allowed to carry the meaning on its own. Every collection that
could be empty for more than one reason travels with a :class:`KnowledgeStatus` and, where
there is something a consumer must not conclude, a :class:`CaveatView` built from measured
figures rather than from prose someone typed once and never re-checked.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any, Final, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from vedagraph.api.config import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE


class ApiModel(BaseModel):
    """Base for every response model."""

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)


class KnowledgeStatus(StrEnum):
    """Why the payload contains what it contains.

    The four values are not degrees of the same thing. ``INSUFFICIENT_EVIDENCE`` and
    ``NOT_BUILT`` both come with no data and mean opposite things about the corpus: the
    first says the text may well say this and our evidence cannot establish it, the second
    says this dimension of the graph was never constructed, so its silence is about us.
    """

    SUPPORTED = "SUPPORTED"
    """The graph answers this over the scope the response declares."""

    PARTIAL = "PARTIAL"
    """A real answer covering only part of the corpus, one Veda, or one evidence mode."""

    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    """Evidence exists but cannot support the claim. NOT a zero, and never render it as 0."""

    NOT_BUILT = "NOT_BUILT"
    """The layer this question needs does not exist in the graph. Absence is about us."""


class EvidenceBasis(StrEnum):
    """How an assertion came to be.

    .. warning::

       **This enum is NOT the graph's ``evidence_basis`` property.** The two share a name
       and describe different axes, and the collision is a trap that was walked into during
       this build: reading ``r.evidence_basis`` straight into this enum mapped *every*
       attribution edge in the corpus to ``UNKNOWN`` -- all 17,889 seer edges, all 16,298
       metre edges, all 10,558 deity edges -- because the value spaces are disjoint.

       The graph property answers "off which textual surface was the evidence read?" and
       its measured value space is :class:`EvidenceSurface` (``SANSKRIT`` 110,087,
       ``STRUCTURAL`` 85,528, ``SOURCE_METADATA`` 51,147, ``MIXED`` 13,667, ``TRANSLATION``
       2,725, ``SHARED_REGISTRY_ENTITIES`` 2,141). This enum answers "what kind of act
       produced the claim?" and is *derived* -- from ``attribution_precision`` for
       attribution edges, and from ``derivation``/``method`` for the semantic layers. Use
       :func:`basis_from_attribution_precision` rather than casting.
    """

    SOURCE_STATED = "SOURCE_STATED"
    CONTAINER_INHERITED = "CONTAINER_INHERITED"
    DETERMINISTIC_DERIVED = "DETERMINISTIC_DERIVED"
    MODEL_EXTRACTION = "MODEL_EXTRACTION"
    MODEL_ADJUDICATED = "MODEL_ADJUDICATED"
    TEXTUAL_MENTION = "TEXTUAL_MENTION"
    """The edge records that a word occurs here, which is not an attribution at all."""

    UNKNOWN = "UNKNOWN"


class EvidenceSurface(StrEnum):
    """Which textual surface an assertion was read off -- the graph's ``evidence_basis``.

    Kept as its own type precisely because it is not :class:`EvidenceBasis`. A client that
    wants to know whether a claim rests on the Sanskrit or on a 19th-century English
    translation is asking this question, and it is a different question from how the claim
    was derived: ``TRANSLATION`` covers 2,725 relationships and 2,459 nodes, and a reader
    who cannot see that is reading Whitney and Griffith as if they were the Samhita.
    """

    SANSKRIT = "SANSKRIT"
    STRUCTURAL = "STRUCTURAL"
    SOURCE_METADATA = "SOURCE_METADATA"
    MIXED = "MIXED"
    TRANSLATION = "TRANSLATION"
    SHARED_REGISTRY_ENTITIES = "SHARED_REGISTRY_ENTITIES"
    UNKNOWN = "UNKNOWN"


class AttributionPrecision(StrEnum):
    """Whether the source states this of *this* passage, or of a container above it.

    The distinction the whole attribution layer turns on. 39,709 edges are
    ``CONTAINER_INHERITED`` -- a hymn's label projected onto each verse inside it -- against
    17,684 ``PER_PASSAGE``, and a response that sums them compares a statement the text
    makes with a projection this project performed.
    """

    PER_PASSAGE = "PER_PASSAGE"
    CONTAINER_INHERITED = "CONTAINER_INHERITED"
    TEXTUAL_MENTION = "TEXTUAL_MENTION"
    NOT_AN_ATTRIBUTION = "NOT_AN_ATTRIBUTION"
    UNKNOWN = "UNKNOWN"


#: The graph's ``attribution_precision`` mapped onto the derivation axis. Separate from the
#: enums so the mapping is one readable table rather than a conditional in each service.
_BASIS_BY_PRECISION: Final[dict[str, EvidenceBasis]] = {
    "PER_PASSAGE": EvidenceBasis.SOURCE_STATED,
    "CONTAINER_INHERITED": EvidenceBasis.CONTAINER_INHERITED,
    "TEXTUAL_MENTION": EvidenceBasis.TEXTUAL_MENTION,
    "NOT_AN_ATTRIBUTION": EvidenceBasis.UNKNOWN,
}


def basis_from_attribution_precision(value: str | None) -> EvidenceBasis:
    """Derive the evidence basis from ``attribution_precision``.

    Returns ``UNKNOWN`` for an unrecognised value rather than raising, because one odd
    property must degrade one field and not fail a request. The value space is asserted
    complete in ``tests/api/test_evidence_vocabulary.py``, so a rebuild that introduces a
    new precision fails a test instead of silently reporting every edge as UNKNOWN -- which
    is exactly the failure this function exists to have caught once.
    """
    if value is None:
        return EvidenceBasis.UNKNOWN
    return _BASIS_BY_PRECISION.get(value, EvidenceBasis.UNKNOWN)


def evidence_surface(value: str | None) -> EvidenceSurface:
    """Read the graph's ``evidence_basis`` property into :class:`EvidenceSurface`."""
    if value is None:
        return EvidenceSurface.UNKNOWN
    try:
        return EvidenceSurface(value)
    except ValueError:
        return EvidenceSurface.UNKNOWN


class CoverageView(ApiModel):
    """What corpus this answer actually reached.

    Present wherever a per-Veda number appears. The single most common misreading of this
    graph is treating a Veda's zero as textual absence when the annotation layer simply
    does not reach that corpus, and a coverage block beside the counts is what makes the
    two distinguishable without reading prose.
    """

    vedas_in_scope: list[str] = Field(
        default_factory=list,
        description="Veda codes this layer measurably reaches, e.g. ['RV'].",
    )
    vedas_not_covered: list[str] = Field(
        default_factory=list,
        description="Veda codes where a zero means an absent layer, not an absent text.",
    )
    measured: dict[str, int] = Field(
        default_factory=dict, description="Per-Veda counts behind this answer."
    )
    denominator: dict[str, int] = Field(
        default_factory=dict,
        description="Per-Veda mantra totals, so a client can normalise rather than "
        "compare raw counts across corpora of different size.",
    )


class CaveatView(ApiModel):
    """What this answer does not establish.

    ``text`` is carried with the payload and not left to documentation, because the reader
    who runs the obvious call never reads the documentation -- that is the exact finding
    that made three benchmark questions MISLEADING.
    """

    text: str = Field(description="What a consumer must not conclude from this payload.")
    source: str = Field(
        default="measured",
        description="Where the caveat came from: the name of the frozen domain query whose "
        "caveat this is, or 'measured' when built from figures in this response.",
    )


class EvidenceSpanView(ApiModel):
    """One quoted witness for an assertion."""

    passage_key: str | None = None
    citation: str | None = None
    veda: str | None = None
    quote: str | None = None
    surface: str | None = Field(
        default=None, description="Which textual surface the quote was taken from."
    )


class EvidenceView(ApiModel):
    """Why the graph believes something.

    Attached to any edge or claim a client can act on. ``tier`` and ``evidence_basis`` are
    the frozen graph's own grading; ``review_state`` is included because nothing in this
    graph is human-reviewed and a client must be able to see that rather than assume it.
    """

    method: str | None = None
    tier: str | None = Field(default=None, description="TIER_A..TIER_D quality grading.")
    evidence_basis: EvidenceBasis = Field(
        default=EvidenceBasis.UNKNOWN,
        description="How the claim arose. DERIVED, not the graph's like-named property; "
        "see EvidenceBasis for why casting that property here reports everything UNKNOWN.",
    )
    surface: EvidenceSurface = Field(
        default=EvidenceSurface.UNKNOWN,
        description="Which textual surface the evidence was read off. TRANSLATION means the "
        "claim rests on a 19th-century English rendering, not on the Sanskrit.",
    )
    attribution_precision: AttributionPrecision = Field(
        default=AttributionPrecision.UNKNOWN,
        description="Whether the source states this of this passage (PER_PASSAGE) or of a "
        "container above it (CONTAINER_INHERITED). Never sum the two.",
    )
    review_state: str | None = Field(
        default=None,
        description="MODEL_ADJUDICATED at strongest. No edge in this graph is human-reviewed.",
    )
    confidence: float | None = Field(
        default=None,
        description="Present only where it varies. Several predicates carry a single "
        "constant here, and those return null rather than a number that looks earned.",
    )
    spans: list[EvidenceSpanView] = Field(default_factory=list)
    derivation: str | None = None


class PaginationMeta(ApiModel):
    """Bounds on a collection response."""

    limit: int
    offset: int
    returned: int
    total: int | None = Field(
        default=None,
        description="Total matching items where counting is cheap; null where it is not, "
        "which is not the same as zero.",
    )
    has_more: bool


LimitParam = Annotated[
    int,
    Field(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Items per page."),
]
OffsetParam = Annotated[int, Field(default=0, ge=0, description="Items to skip.")]


class Paginated[T](ApiModel):
    """A bounded collection that says why it is the size it is."""

    items: list[T] = Field(default_factory=list)
    pagination: PaginationMeta
    data_status: KnowledgeStatus = KnowledgeStatus.SUPPORTED
    coverage: CoverageView | None = None
    caveats: list[CaveatView] = Field(default_factory=list)

    @model_validator(mode="after")
    def _empty_must_explain_itself(self) -> Self:
        """An empty first page claiming SUPPORTED is the misleading shape, so refuse it.

        SUPPORTED plus zero items on the first page asserts "the corpus has none of these".
        That is occasionally true and usually not -- and it is exactly the assertion the
        benchmark grades MISLEADING. A service that means it can still say so by passing a
        caveat; what it cannot do is say it by accident.
        """
        first_page_empty = not self.items and self.pagination.offset == 0
        if first_page_empty and self.data_status is KnowledgeStatus.SUPPORTED and not self.caveats:
            raise ValueError(
                "An empty first page must carry a non-SUPPORTED data_status or a caveat: "
                "a bare empty list cannot distinguish absence in the text from an "
                "unbuilt layer."
            )
        return self


class CountedByVeda(ApiModel):
    """A per-Veda breakdown that refuses to imply a zero it cannot support."""

    rv: int | None = None
    sv: int | None = None
    yv: int | None = None
    av: int | None = None
    status: KnowledgeStatus = KnowledgeStatus.SUPPORTED
    note: str | None = Field(
        default=None,
        description="Why a null is null. A null means not established; it never means zero.",
    )


class ReferentCertaintyCounts(ApiModel):
    """The deity-mention ambiguity split, always returned in full.

    ``agni`` is the god and it is fire. The graph grades every mention edge, and the
    product default counts CERTAIN plus PROBABLE while excluding AMBIGUOUS -- but it
    reports all three, because a deity whose name is an ordinary noun is flattered or
    penalised by that choice and the client has to be able to see it.
    """

    certain_count: int = 0
    probable_count: int = 0
    ambiguous_count: int = 0
    included_tiers: list[str] = Field(
        default_factory=list, description="Which tiers the accompanying totals actually used."
    )

    @property
    def default_total(self) -> int:
        return self.certain_count + self.probable_count


class StatusEnvelope(ApiModel):
    """For answers whose whole content may be 'we cannot establish this'."""

    data_status: KnowledgeStatus
    coverage: CoverageView | None = None
    caveats: list[CaveatView] = Field(default_factory=list)
    detail: dict[str, Any] = Field(default_factory=dict)


def paginate[T](
    items: list[T],
    *,
    limit: int,
    offset: int,
    total: int | None = None,
    data_status: KnowledgeStatus = KnowledgeStatus.SUPPORTED,
    coverage: CoverageView | None = None,
    caveats: list[CaveatView] | None = None,
) -> Paginated[T]:
    """Wrap an already-bounded list. ``items`` must be the page, not the whole result."""
    return Paginated[T](
        items=items,
        pagination=PaginationMeta(
            limit=limit,
            offset=offset,
            returned=len(items),
            total=total,
            has_more=(offset + len(items)) < total if total is not None else len(items) == limit,
        ),
        data_status=data_status,
        coverage=coverage,
        caveats=list(caveats or []),
    )
