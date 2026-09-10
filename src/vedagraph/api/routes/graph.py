"""Neighbourhoods, relationship explanations and whitelisted paths.

Thin by design: every query, bound and whitelist in this feature lives in
:mod:`vedagraph.api.services.graph_service`, and these handlers only turn query parameters
into service arguments. The reason is not tidiness -- it is that the traversal whitelist,
the hub ceiling and the relationship-id codec have to be the same objects for all three
endpoints, and a route that assembled its own Cypher would be free to disagree with the
other two about what a traversable predicate is.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Path, Query

from vedagraph.api.config import MAX_NEIGHBOURS_PER_TYPE
from vedagraph.api.dependencies import RepositoryDep
from vedagraph.api.errors import COMMON_ERROR_RESPONSES
from vedagraph.api.models.graph import (
    NeighbourhoodView,
    PathView,
    RelationshipExplanation,
)
from vedagraph.api.services.graph_service import (
    NEIGHBOURHOOD_MAX_DEPTH,
    PATH_DEFAULT_DEPTH,
    PATH_MAX_DEPTH,
    PATH_RELATIONSHIPS,
    TRAVERSABLE_RELATIONSHIPS,
    GraphService,
)

router = APIRouter(tags=["Graph"], responses=COMMON_ERROR_RESPONSES)

_NEIGHBOURHOOD_DESCRIPTION = f"""
The bounded local graph around one knowledge object, ready to render as `nodes[]` and
`edges[]`: every `edge.source` and `edge.target` is the `id` of a node in the same payload.

**Which id.** Pass the stable product id and this endpoint works out what kind of thing it
is -- a passage's `canonical_key` (`VG:RV:SAK:M01:S001:V001`), a deity, seer, metre or
entity `entity_key` (`VG:DEVATA:INDRAH`, `VG:CONCEPT:SOMA-DRINK`), a `Formula.formula_id`,
a `FormulaFamily.family_id`, an epithet, a deity axis, a seer family, a derived metric, an
interpretive claim or a work. An unknown id is a 404 with a hint, never an empty graph: "we
have nothing by that name" and "that thing has no connections" are different answers.

**Bounds, and why the response states them.** `limit_per_type` caps the fan-out *per
predicate and direction* at {MAX_NEIGHBOURS_PER_TYPE}, and there is a hard node budget on
top of it. `bounds.total_degree` reports the node's real degree over traversable predicates
and `bounds.truncated_types` names every predicate that was cut, because Indra carries
3,566 deity-mention edges and a graph showing 50 of them, unlabelled, is a false picture of
a deity's prominence.

**`include_internal` cannot leak a QA finding.** Measured over the live graph, none of the
{len(TRAVERSABLE_RELATIONSHIPS)} traversable predicates has an endpoint labelled `Internal`,
`QAIssue`, `TextVersion`, `Translation`, `Source` or `SourceArtifact` -- so no value of any
parameter can return one. What `include_internal=true` does, and the only thing it does, is
add `MENTIONS_LEMMA` so that `:Lemma` nodes become reachable. That layer is marked internal
because 39 deity lemmas were surfacing in product traversal looking like deities while
carrying none of a deity's profile.

**`min_confidence` filters a pipeline prior, not a confidence.** Five predicates stamp one
constant on every edge they have -- `HAS_RISHI`, `HAS_CHANDAS`, `HAS_DEVATA`,
`HAS_DEVATA_ASCRIPTION` and `BELONGS_TO_FAMILY`, all at 1.0 -- so a threshold over them
either keeps every edge or none, and keeping them is not evidence of quality. Those edges
are **not** filtered; they return `confidence: null`, `confidence_basis:
PIPELINE_CONSTANT` and the constant as `pipeline_prior`, and the response carries a caveat
saying so. No predicate in this graph has a labelled evaluation set behind its confidence.

**`trust_tier` selects a mechanism, not a quality.** TIER_A is source-stated, TIER_B a
reproducible derivation, TIER_C model-adjudicated, TIER_D unreviewed model output. Edges of
predicates that carry no tier are excluded by the filter, which is not evidence that they
do not exist.
"""

_RELATIONSHIP_DESCRIPTION = """
Why the graph believes two things are connected: the edge, both endpoints, a `why` written
from the edge's own recorded properties, the passages its evidence block cites, the method,
the tier, the derivation and the review status.

**The id is not a Neo4j id and never will be.** `element_id` is a storage address, it is
reassigned on rebuild, and this graph gets rebuilt -- a bookmarked explanation URL built on
one would come back pointing at a different edge, with a 200. So the ids returned by
`GET /graph/neighborhood/{id}` are opaque tokens built from the data: from the layer's own
stable identifier where it minted one (`mention_id`, `assertion_id`, `membership_id`,
`parallel_id`, `candidate_id`), and otherwise from the two endpoints' product ids plus the
predicate. `id_basis` on every edge says which of the two you have. A Neo4j id, a token
from another scheme, or a malformed token is a 400; a well-formed token for an edge the
build no longer produces is a 404.

**`review_status` is spelled out because the honest answer is uniform.** Nothing in this
graph is HUMAN_REVIEWED. The strongest state that exists is MODEL_ADJUDICATED, on 613 edges
across ten predicates, where a model re-read the passage and accepted the edge with a
stated reason. Most edges carry no review record at all, which is not the same as having
been reviewed and passed.
"""

_PATH_DESCRIPTION = f"""
A route between two knowledge objects over a whitelist of {len(PATH_RELATIONSHIPS)}
meaningful predicates, with **every hop explained in words**. That explanation is the point
of the endpoint: a route is only worth returning if a reader can see what each step does
and does not establish.

**What is excluded, and why.** The corpus's containment tree (`CONTAINS`), its stored text
surfaces (`HAS_TEXT_VERSION`, `HAS_TRANSLATION`), the lexical layer (`MENTIONS_LEMMA`), this
repository's own QA findings (`QA_ISSUE_ON`) and the internal wiring of reified assertions
(`ASSERTION_PREDICATE`, `ASSERTION_AGENT`, `ASSERTION_TARGET`) are all excluded. They
connect nearly everything to nearly everything, so a path through them is true and
meaningless. `MEMBER_OF_FAMILY` is excluded here too, because it is the mirror of
`HAS_FORMULA` over the same 2,037 memberships and a route could otherwise bounce between a
family and its own formulas.

**Hubs are penalised by ranking, not excluded, and that was measured.** The shortest routes
are enumerated under a hard candidate cap and the one whose busiest waypoint has the lowest
degree wins, which materially improves the answer: RV 1.1.1 to SV 1.1.1 goes from "both
mention Agni" (a node with 5,459 edges) to "both mention the *hotṛ* priest" (634).
Forbidding high-degree waypoints inside the search instead would be better still and is not
available: a node predicate defeats Neo4j's bidirectional planner, and the same query
measured 3-7 ms without it against 22-25 s with it -- past the driver's own budget, so a
legitimate "not connected within four hops" would have surfaced as a 503.

Where even the best shortest route crosses a node above the measured hub ceiling, the route
is returned with `hub_mediated: true` and a caveat naming the node and its degree, rather
than suppressed into an empty answer a reader would take for "unconnected".

**The residual limit, stated.** Only routes of the *minimum* length are considered, so a
longer and more distinctive route can exist and is not searched. `max_depth` is bounded at
{PATH_MAX_DEPTH}; anything higher is a 422, because a five-hop route through this graph
reaches everything.
"""


@router.get(
    "/graph/neighborhood/{node_id}",
    summary="The bounded graph neighbourhood of one knowledge object",
    description=_NEIGHBOURHOOD_DESCRIPTION,
    response_model=NeighbourhoodView,
    responses=COMMON_ERROR_RESPONSES,
)
def neighbourhood_endpoint(
    repository: RepositoryDep,
    node_id: Annotated[
        str,
        Path(
            description="A stable product id: a passage canonical_key, an entity_key, a "
            "formula_id, a family_id or any other product id. Never a Neo4j id.",
            min_length=1,
            max_length=200,
        ),
    ],
    depth: Annotated[
        int,
        Query(
            ge=1,
            le=NEIGHBOURHOOD_MAX_DEPTH,
            description="1 for direct links, 2 to include one bounded step beyond them. "
            "Capped at 2: depth 3 from Indra reaches most of the Rigveda.",
        ),
    ] = 1,
    types: Annotated[
        list[str] | None,
        Query(
            description="Restrict to these predicates, repeatable. A name outside the "
            "traversable whitelist is a 400 naming it, never an empty result.",
        ),
    ] = None,
    trust_tier: Annotated[
        Literal["TIER_A", "TIER_B", "TIER_C", "TIER_D"] | None,
        Query(description="Keep only edges of this tier. Tier is a mechanism, not a score."),
    ] = None,
    min_confidence: Annotated[
        float | None,
        Query(
            ge=0.0,
            le=1.0,
            description="Threshold on the confidence property. Not applied to predicates "
            "whose confidence is a pipeline constant; those are kept and disclosed.",
        ),
    ] = None,
    include_internal: Annotated[
        bool,
        Query(
            description="Admits :Lemma nodes via MENTIONS_LEMMA, and nothing else. It "
            "cannot return a QAIssue or any other internal node under any value.",
        ),
    ] = False,
    limit_per_type: Annotated[
        int,
        Query(
            ge=1,
            le=MAX_NEIGHBOURS_PER_TYPE,
            description="Maximum neighbours per predicate per direction.",
        ),
    ] = 25,
) -> NeighbourhoodView:
    return GraphService(repository).neighbourhood(
        node_id,
        depth=depth,
        requested_types=tuple(types) if types else None,
        trust_tier=trust_tier,
        min_confidence=min_confidence,
        include_internal=include_internal,
        limit_per_type=limit_per_type,
    )


@router.get(
    "/graph/relationships/{relationship_id}",
    summary="Why are these two connected?",
    description=_RELATIONSHIP_DESCRIPTION,
    response_model=RelationshipExplanation,
    responses=COMMON_ERROR_RESPONSES,
)
def relationship_endpoint(
    repository: RepositoryDep,
    relationship_id: Annotated[
        str,
        Path(
            description="An opaque relationship token from the `edges[].id` field of a "
            "neighbourhood or a path. Neo4j ids are refused.",
            min_length=1,
            max_length=600,
        ),
    ],
) -> RelationshipExplanation:
    return GraphService(repository).explain_relationship(relationship_id)


@router.get(
    "/graph/path",
    summary="A meaningful path between two knowledge objects, explained hop by hop",
    description=_PATH_DESCRIPTION,
    response_model=PathView,
    responses=COMMON_ERROR_RESPONSES,
)
def path_endpoint(
    repository: RepositoryDep,
    source_id: Annotated[
        str,
        Query(
            alias="from",
            description="Stable product id of the starting object.",
            min_length=1,
            max_length=200,
        ),
    ],
    target_id: Annotated[
        str,
        Query(
            alias="to",
            description="Stable product id of the destination object.",
            min_length=1,
            max_length=200,
        ),
    ],
    max_depth: Annotated[
        int,
        Query(
            ge=1,
            le=PATH_MAX_DEPTH,
            description="Longest route to consider, in hops. Bounded so a request cannot "
            "make the server enumerate the graph.",
        ),
    ] = PATH_DEFAULT_DEPTH,
) -> PathView:
    return GraphService(repository).find_path(source_id, target_id, max_depth=max_depth)
