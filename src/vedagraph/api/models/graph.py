"""Graph exploration contracts: neighbourhoods, relationship identity, and paths.

Three product features live on these models, and each one exists because a naive version
of it would have leaked or misled.

**Relationship identity (spec section 25).** A client that reads a neighbourhood and then
asks "why are these two connected?" needs a handle on the edge, and Neo4j's own
``element_id`` cannot be it. That value is a storage address: it is not stable across a
rebuild, and this graph gets rebuilt -- a bookmarked explanation URL would silently point
at a different edge, or at nothing. So an edge id here is one of exactly two things, and
:class:`RelationshipIdBasis` says which one on every edge returned:

* ``DOMAIN_ID`` -- the build minted a stable domain identifier for this edge and it travels
  in the token. Measured over the live graph, ``parallel_id`` covers 5,521 of the 6,596
  parallel edges, ``mention_id`` all 45,392 mention edges, ``assertion_id`` all 24,969
  ``ABOUT_CONCEPT`` edges, ``membership_id`` all 4,074 family-membership edges and
  ``candidate_id`` all 533 agentive edges.
* ``ENDPOINT_TRIPLE`` -- there is no domain id, so identity is minted from the two
  endpoints' own stable product ids plus the relationship type. ``HAS_RISHI``,
  ``HAS_DEVATA``, ``HAS_CHANDAS``, ``USES_FORMULA``, ``TREATS``, ``PROTECTS_FROM`` and
  ``ADDRESSES_CONCERN`` are all in this class, and so are the 1,075 parallel edges whose
  producer wrote no ``parallel_id``. This is only sound because the triple is a key, and
  that was measured rather than assumed: across all 27 relationship types the traversal
  surfaces, the maximum number of edges between any one ordered pair of nodes under one
  type is **1**.

**Confidence is a pipeline prior on part of this graph, and these models refuse to launder
it.** The frozen query ``confidence_is_a_pipeline_constant`` measures the field, and five
predicates carry a single value on every edge they have: ``HAS_RISHI`` (17,889 edges, all
1.0), ``HAS_CHANDAS`` (16,298, all 1.0), ``HAS_DEVATA`` (10,558, all 1.0),
``HAS_DEVATA_ASCRIPTION`` (5,385, all 1.0) and ``BELONGS_TO_FAMILY`` (305, all 1.0). A
number identical on every edge of a predicate ranks nothing and measures nothing. So on
those predicates :attr:`GraphEdgeView.confidence_basis` is ``PIPELINE_CONSTANT``,
``evidence.confidence`` is **null**, and the constant is returned separately as
:attr:`GraphEdgeView.pipeline_prior`, where a client can see what it is without being able
to mistake it for something earned. ``EvidenceView.confidence`` already promises exactly
this -- "present only where it varies" -- and this is the module that keeps the promise.

**A grade is stored once.** ``tier``, ``evidence_basis``, ``review_state``, ``method`` and
``derivation`` live inside :attr:`GraphEdgeView.evidence` and are deliberately *not* also
flattened onto the edge beside it. Two copies of a grade is how a grade drifts, and this
repository has already shipped an audit block that disagreed with its own rows in 8 of 9
recorded corrections.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import Field

from vedagraph.api.models.common import (
    ApiModel,
    CaveatView,
    EvidenceView,
    KnowledgeStatus,
)


class RelationshipIdBasis(StrEnum):
    """What the opaque relationship token in a response is actually made of.

    Returned on every edge, because the two kinds carry different guarantees and a client
    that caches an explanation URL deserves to know which it holds. A ``DOMAIN_ID`` token
    survives anything that preserves the build's own identifiers. An ``ENDPOINT_TRIPLE``
    token survives anything that preserves the two endpoints' product ids -- a weaker
    promise, and a true one, where ``element_id`` promises nothing at all.
    """

    DOMAIN_ID = "DOMAIN_ID"
    """The build minted a stable id for this edge; the token carries it."""

    ENDPOINT_TRIPLE = "ENDPOINT_TRIPLE"
    """No domain id exists, so identity is (source id, relationship type, target id)."""


class ConfidenceBasis(StrEnum):
    """Whether an edge's ``confidence`` field is a measurement or a stamp.

    Never inferred per request from the number itself: one edge cannot tell you whether its
    predicate's confidence varies. The classification comes from
    :data:`~vedagraph.api.services.graph_service.PIPELINE_CONSTANT_PREDICATES`, which is
    measured over the whole graph and asserted against it by a live test.
    """

    PIPELINE_CONSTANT = "PIPELINE_CONSTANT"
    """Every edge of this predicate carries the same value, so it ranks nothing. Returned as
    a ``pipeline_prior`` and never as a ``confidence``."""

    VARIES_WITHIN_PREDICATE = "VARIES_WITHIN_PREDICATE"
    """The value differs between edges of this predicate. Still a pipeline output rather
    than a calibrated probability -- no labelled evaluation set exists for this graph --
    but it does at least distinguish one edge from another."""

    ABSENT = "ABSENT"
    """The predicate carries no ``confidence`` property at all. Not a zero."""


class TraversalDirection(StrEnum):
    """Which way an edge points relative to the node a neighbourhood was asked for."""

    OUTBOUND = "OUTBOUND"
    INBOUND = "INBOUND"


class GraphNodeView(ApiModel):
    """One node, ready to render, with nothing of the database in it.

    ``type`` is a product type name (``DEVATA``, ``MANTRA``, ``FORMULA_FAMILY``) and never a
    Neo4j label. ``metadata`` is filled from a **whitelist** of property names rather than
    by copying whatever the node happens to carry: the frozen graph stores ``run_id``,
    ``pipeline_version``, ``build_pass``, ``prompt_policy`` and ``model`` on many nodes, all
    of which are facts about this repository's build and none of which is Vedic knowledge.
    A copy-everything projection would have shipped every one of them.

    **``type: "DEVATA"`` does not mean the thing is a god, and :attr:`is_deity` is why this
    model can say so.** The Anukramani names a *devata* for every hymn and 57 of the 214
    entries are not deities: 22 human patrons and seers, 7 labels naming a gift rather than
    a recipient, and 28 abstractions ruled not to name an addressee. The dog is NOT among
    them -- it is a deified animal beside thirteen others in the population, and excluding
    it for carrying structure UNSPECIFIED was the morphological accident the eligibility
    ruling names. The frozen graph labels all of them ``:Devata``, so a generic
    graph explorer -- whose job is to show what is connected to an arbitrary node -- will
    resolve one sooner or later, and eight of them carry real traversable degree.

    ``type`` deliberately stays ``DEVATA`` for those. It is the frontend's rendering and
    routing key, every other deity surface in this API emits ``DEVATA`` for the same node,
    and a graph endpoint that invented a different type name would produce an API where
    following an ``EntityRef`` from ``/devatas/{id}`` changed the node's type -- a sixth
    instance of the very defect class this fixes rather than a fix for it. The honest
    signal is a separate field plus the caveat, and the two are produced together.
    """

    id: str = Field(description="Stable product id, e.g. VG:DEVATA:INDRAH. Never a Neo4j id.")
    type: str = Field(description="Product type name. Never a raw graph label.")
    label: str = Field(description="Display label, ready to show a reader.")
    description: str | None = None
    is_deity: bool | None = Field(
        default=None,
        description="For a node in the Anukramani's devata slot, whether it is actually a "
        "god. Null for everything else, because the question does not apply to a metre or "
        "a formula and false would answer it. False means the slot holds a human patron, "
        "praise of a gift, or an abstraction ruled not to name an addressee -- do not "
        "render it as a deity, whatever `type` says.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Product-meaningful properties only, from a fixed whitelist. Never "
        "build state: no run ids, pipeline versions, prompt policies or model names.",
    )


class GraphEdgeView(ApiModel):
    """One relationship, ready to render, addressable, and honest about its grade.

    ``source`` and ``target`` are the ``id`` values of nodes in the same payload, so a
    frontend can wire a graph without a second request. ``type`` is the predicate name from
    the frozen ontology -- ``MENTIONS_DEVATA``, ``HAS_RISHI`` -- which is exposed on
    purpose: it is the product's own vocabulary, the ``types`` filter takes exactly these
    names, and hiding it behind a synonym would make that filter undocumentable.
    """

    id: str = Field(description="Opaque, stable relationship token. Never a Neo4j id.")
    id_basis: RelationshipIdBasis
    source: str = Field(description="`id` of the source node, present in the same payload.")
    target: str = Field(description="`id` of the target node, present in the same payload.")
    type: str = Field(description="Predicate name from the frozen ontology.")
    label: str = Field(description="The predicate as a readable phrase.")
    direction: TraversalDirection | None = Field(
        default=None,
        description="Set only in a neighbourhood, where it is relative to the root node.",
    )
    evidence: EvidenceView = Field(
        description="Grade, method, review state and witnesses. Tier and evidence_basis "
        "live HERE and not also beside it: one grade, one place."
    )
    confidence_basis: ConfidenceBasis = ConfidenceBasis.ABSENT
    pipeline_prior: float | None = Field(
        default=None,
        description="The constant this predicate stamps on every one of its edges, where "
        "confidence_basis is PIPELINE_CONSTANT. Not a score; it ranks nothing.",
    )
    score: float | None = Field(
        default=None,
        description="The layer's own numeric output where it has one -- a string "
        "similarity, an IDF sum, a match ratio. Its meaning depends on `evidence.method`.",
    )
    caveat: CaveatView | None = Field(
        default=None,
        description="What this edge does not establish, where that is not self-evident.",
    )


class NeighbourhoodBounds(ApiModel):
    """Exactly which bounds were applied, so a short list is never read as a small graph.

    The most misreadable thing about a truncated neighbourhood is that it looks complete.
    ``truncated_types`` names every predicate whose fan-out hit ``limit_per_type``, and
    ``total_degree`` is the root's real degree over the traversable set, so a client can see
    that it received 50 of Indra's 3,566 deity mentions rather than all of them.
    """

    depth: int
    limit_per_type: int
    node_budget: int
    returned_nodes: int
    returned_edges: int
    total_degree: int | None = Field(
        default=None,
        description="The root's full degree over traversable predicates. Null where it was "
        "not measured, which is not the same as zero.",
    )
    truncated_types: list[str] = Field(
        default_factory=list,
        description="Predicates whose fan-out was cut by limit_per_type. Anything named "
        "here has more edges than this response shows.",
    )
    hub_expansions_skipped: int = Field(
        default=0,
        description="Depth-2 expansions not attempted because the depth-1 node is a "
        "measured hub. Always 0 at depth 1, where nothing is expanded.",
    )


class NeighbourhoodView(ApiModel):
    """A bounded local graph around one node, with its own limits attached.

    ``nodes`` and ``edges`` are frontend-ready and closed: every ``edge.source`` and
    ``edge.target`` appears in ``nodes``. ``bounds`` is not decoration -- a graph view is
    the surface where truncation is least visible, and a client that plots 50 edges without
    knowing that 3,516 were dropped draws a false picture of a deity's prominence.
    """

    root: GraphNodeView
    nodes: list[GraphNodeView] = Field(default_factory=list)
    edges: list[GraphEdgeView] = Field(default_factory=list)
    bounds: NeighbourhoodBounds
    data_status: KnowledgeStatus = KnowledgeStatus.SUPPORTED
    caveats: list[CaveatView] = Field(default_factory=list)


class RelationshipExplanation(ApiModel):
    """Why the graph believes two things are connected -- the flagship answer.

    ``why`` is prose assembled from this edge's own recorded properties and a template owned
    per predicate; no figure in it is typed by hand. It is the field a reader actually
    reads, so it is the field that has to state the weak cases out loud: that a seer edge is
    a hymn label projected onto a verse, that a family membership can be transitive and
    share no words with the phrase that names the family, that a cross-script parallel
    bottoms out at the weakest comparable surface.

    ``review_status`` is spelled out rather than left to the presence of
    ``evidence.review_state``, because the honest answer for most of this graph is "no
    review record exists", and nothing anywhere in it is ``HUMAN_REVIEWED``.
    """

    relationship: GraphEdgeView
    source: GraphNodeView
    target: GraphNodeView
    why: str = Field(description="What this edge asserts, and what it does not.")
    method: str | None = None
    trust_tier: str | None = Field(default=None, description="TIER_A..TIER_D.")
    derivation: str | None = None
    review_status: str = Field(
        description="Plain-language review state. Never implies human review, because no "
        "edge in this graph carries any."
    )
    evidence_passages: list[GraphNodeView] = Field(
        default_factory=list,
        description="Passages this edge's own evidence block cites, resolved to nodes.",
    )
    data_status: KnowledgeStatus = KnowledgeStatus.SUPPORTED
    caveats: list[CaveatView] = Field(default_factory=list)


class PathHopView(ApiModel):
    """One step of a path, with the sentence that makes the step worth returning."""

    index: int = Field(description="1-based position of this hop along the path.")
    source: GraphNodeView
    target: GraphNodeView
    relationship: GraphEdgeView
    explanation: str = Field(description="This hop in words, including what it does not say.")


class PathView(ApiModel):
    """A whitelisted route between two knowledge objects, explained hop by hop.

    ``hub_mediated`` is what keeps this endpoint honest. Two Rigvedic verses are nearly
    always connected within three hops through some node that touches thousands of edges --
    the metre tristubh carries 4,195 traversable edges, Indra 6,539 -- and such a route is
    true while saying nothing about the pair. So a hub-free route is searched for first;
    where only a hub-mediated one exists it is returned *labelled*, with the offending
    node's degree in the caveat, rather than suppressed into an empty answer that a reader
    would take for "unconnected".
    """

    source: GraphNodeView
    target: GraphNodeView
    length: int = Field(description="Number of hops. 0 when source and target are one node.")
    hops: list[PathHopView] = Field(default_factory=list)
    hub_mediated: bool = Field(
        default=False,
        description="True when the route passes through a node whose degree exceeds the "
        "measured hub ceiling, so the connection does not distinguish this pair.",
    )
    max_depth_searched: int
    data_status: KnowledgeStatus = KnowledgeStatus.SUPPORTED
    caveats: list[CaveatView] = Field(default_factory=list)
