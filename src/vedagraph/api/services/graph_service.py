"""Neighbourhood exploration, relationship explanation and whitelisted pathfinding.

This module owns three product features and four decisions that were measured rather than
assumed. The measurements are quoted here because each one closed off a design that looked
obviously right and was wrong.

Relationship identity, and why it is not ``element_id``
-------------------------------------------------------
A client reads a neighbourhood, sees an edge, and asks why the two nodes are connected. It
needs a handle. Neo4j offers ``element_id``, and using it would be a defect that only
shows up after the next rebuild: it is a storage address, it is reassigned freely, and this
graph is rebuilt. A bookmarked explanation URL would come back pointing at a different
edge -- silently, with a 200.

So identity here is derived from the data. Two shapes, and
:class:`~vedagraph.api.models.graph.RelationshipIdBasis` reports which one a token uses:

* Some layers minted a stable id. Measured over every edge of each type rather than by
  sampling one: ``mention_id`` on all 17,165 ``MENTIONS_DEVATA`` and all 28,227
  ``MENTIONS_ENTITY`` edges, ``assertion_id`` on all 24,969 ``ABOUT_CONCEPT``,
  ``membership_id`` on all 2,037 ``MEMBER_OF_FAMILY`` and all 2,037 ``HAS_FORMULA``,
  ``candidate_id`` on all 533 agentive edges, ``parallel_id`` on all of
  ``NEAR_PARALLEL_OF`` (3,049), ``REUSES_TEXT_FROM`` (1,684) and ``VARIANT_OF`` (788).
* Everything else gets ``(source id, relationship type, target id)``.

Two of those measurements changed the design. ``EXACT_PARALLEL_OF`` was expected to carry
``parallel_id`` and **750 of its 1,006 edges do**; the other 256 come from a second
producer with a disjoint property vocabulary (``methods``, ``status``,
``strongest_method``, ``provenance_class``) and carry no id at all -- as do all 69
``PARALLEL_TO`` edges. Sampling ``keys(r)`` from one edge per type would have missed this
entirely and minted tokens for a property that is null on a quarter of the type. So the
basis is decided **per edge**, on whether the id is actually there, never per type.

And ``membership_id`` is *shared* by both directions of a family membership: the same 2,037
values appear on ``MEMBER_OF_FAMILY`` and on its ``HAS_FORMULA`` mirror. A token carrying
only the domain id would be ambiguous between two edges. Every token therefore carries the
relationship type as well, and lookup is by type **and** id.

The endpoint-triple form is only sound if the triple is a key, so that was measured too:
across all 27 relationship types this surface traverses, the maximum number of edges
between any one ordered pair of nodes under one type is **1**.

Hubs, and why they are penalised rather than excluded
------------------------------------------------------
Almost any two Vedic verses are three hops apart, and the connecting node is almost always
generic. Measured degrees over the traversable predicates: the metre *triṣṭubh* 4,195,
Indra 6,539, Agni 4,641, *soma* (the drink) 2,307, *heaven* 2,386. "Both verses are in
triṣṭubh" is true of thousands of pairs and explains nothing about this one.

The obvious fix -- forbid high-degree waypoints inside the path query -- was measured and
rejected. A node predicate inside ``shortestPath`` defeats Neo4j's bidirectional planner
and turns the search into an enumeration: **the same RV-to-SV query runs in 3-7 ms without
the predicate and 22-25 s with it**, which is past the 15 s driver budget, so a legitimate
"these are not connected within four hops" would have surfaced as a 503.

What is done instead: ``allShortestPaths`` is run inside a subquery with a hard candidate
cap, every candidate is scored by its worst waypoint degree, and the least hub-mediated
route wins. That is 3-14 ms at depth 4 and it materially improves the answer -- RV 1.1.1 to
SV 1.1.1 goes from "both mention Agni" (degree 5,459) to "both mention the *hotṛ* priest"
(degree 634). Where even the best shortest route crosses a hub, the route is returned with
``hub_mediated`` set and a caveat quoting the measured degree, because suppressing it would
produce an empty answer that reads as "unconnected", which is the misleading shape this API
exists to refuse.

The residual limit is stated rather than hidden: ``allShortestPaths`` only considers routes
of the *minimum* length, so a longer and more distinctive route can exist and is not
searched. Searching it is the 22-second enumeration above.

QAIssue and Internal cannot appear, structurally
-------------------------------------------------
Spec section 24 requires that no diagnostic node ever reach a neighbourhood. Rather than
filtering them out, the traversable whitelist is built so that they are not reachable, and
that was verified against the live graph: of the 165,311 edges carried by the 57 traversable
predicates, **zero** touch a node labelled ``Internal``, ``QAIssue``, ``TextVersion``,
``Translation``, ``Source``, ``SourceArtifact`` or ``Lemma``. The redundant ``NOT
n:Internal`` filter is kept in the neighbourhood queries anyway; it costs nothing there and
a structural guarantee that nobody re-checks is a guarantee that expires.

``include_internal=true`` therefore admits exactly one thing: ``:Lemma`` nodes, by adding
``MENTIONS_LEMMA`` to the traversable set. It cannot admit a ``QAIssue`` or any other
``:Internal`` node under any parameter value, because no whitelisted predicate reaches one.
"""

from __future__ import annotations

import base64
import binascii
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Final

from vedagraph.api.config import MAX_NEIGHBOURS_PER_TYPE
from vedagraph.api.errors import BadRequestError, EntityNotFoundError, NotFoundError
from vedagraph.api.models.common import (
    AttributionPrecision,
    CaveatView,
    EvidenceBasis,
    EvidenceSpanView,
    EvidenceView,
    KnowledgeStatus,
    basis_from_attribution_precision,
    evidence_surface,
)
from vedagraph.api.models.entity import parse_json_property
from vedagraph.api.models.graph import (
    ConfidenceBasis,
    GraphEdgeView,
    GraphNodeView,
    NeighbourhoodBounds,
    NeighbourhoodView,
    PathHopView,
    PathView,
    RelationshipExplanation,
    RelationshipIdBasis,
    TraversalDirection,
)
from vedagraph.api.repositories.neo4j_repository import (
    Neo4jRepository,
    validated_label,
    validated_relationship_types,
)
from vedagraph.api.services.deity_population import DevataSubject, subject_disclosure
from vedagraph.domain import layer_figures
from vedagraph.domain.ontology import LABEL_DEVATA

# ---------------------------------------------------------------------------
# Traversal whitelists
# ---------------------------------------------------------------------------

#: Predicates a neighbourhood may follow. Every one of the 58 is a knowledge claim about
#: the corpus; the exclusions below are the corpus's plumbing and its own build's opinions.
TRAVERSABLE_RELATIONSHIPS: Final[frozenset[str]] = frozenset(
    {
        # textual reuse across and within corpora
        "EXACT_PARALLEL_OF",
        "NEAR_PARALLEL_OF",
        "REUSES_TEXT_FROM",
        "VARIANT_OF",
        "PARALLEL_TO",

        # formulaic diction
        "HAS_FORMULA",
        "MEMBER_OF_FAMILY",
        "USES_FORMULA",
        # what a passage names or is about
        "MENTIONS_DEVATA",
        "MENTIONS_ENTITY",
        # GAP-ENTITY_COVERAGE-001. Traversable rather than refused: "where does this
        # epithet occur" is the question the layer was built to answer, and refusing the
        # predicate would make the answer unreachable from /api/v1/graph while the edges
        # sit in the graph. Rigveda-only by construction; the bound is on every edge and
        # in the predicate's own limit.
        "MENTIONS_EPITHET",
        "ABOUT_CONCEPT",
        "SHARES_ENTITY_VOCABULARY_WITH",
        # the Anukramani's ascriptions
        "HAS_RISHI",
        "HAS_CHANDAS",
        "HAS_DEVATA",
        "HAS_DEVATA_ASCRIPTION",
        "ASCRIBES_TO_DEVATA",
        "HAS_DEVATA_DERIVED",
        "BELONGS_TO_FAMILY",
        # deity structure
        "CO_OCCURS_WITH",
        "DEVATA_ASSOCIATED_WITH",
        "HAS_AXIS",
        "HAS_EPITHET",
        "EPITHET_VARIANT_OF",
        "SPECIALIZED_FORM_OF",
        "MEMBER_OF",
        "COMPOSED_OF",
        # what a passage is for
        "TREATS",
        "PROTECTS_FROM",
        "ADDRESSES_CONCERN",
        "USED_FOR_RITE",
        "DESCRIBED_IN",
        "ATTESTED_IN",
        "BROADER_THAN",
        # what a scholar says about a passage
        "SCHOLARLY_CLAIM_ABOUT",
        # the formula layer, populated by Wave 3
        "SHARES_FORMULA_WITH",
        # the morphology-derived agentive layer
        "PERFORMS_ACTION",
        "IS_ASKED_TO",
        "HAS_SEMANTIC_ASSERTION",
        # ritual structure
        "HAS_RITUAL_STEP",
        "USES_OBJECT",
        "USES_SUBSTANCE",
        "USES_OFFERING",
        # 4 edges, Devata -> Offering, on 3 of 103 rites. Sparse, and whitelisted anyway:
        # scarcity is a reason to disclose a layer, not a reason to make it unreachable,
        # and its siblings on either side of it here are followed at every size.
        "RECEIVES_OFFERING",
        "INVOKES_DEVATA",
        "PERFORMED_BY",
        "PERFORMED_FOR",
        "HAS_STEP",
        # the model-extracted semantic layer, all of it TIER_C or TIER_D
        "INVOKES",
        "DESCRIBES",
        "REQUESTS",
        "PRAISES",
        "DESCRIBES_ACTION",
        "HAS_THEME",
        "CONTRASTS_WITH",
        "INVOLVES_OFFERING",
        "INVOLVES_RITUAL",
        "INVOLVES_SUBSTANCE",
        "REFERS_TO_NATURAL_PHENOMENON",
        "REFERS_TO_PLACE",
        # interpretive claims and derived metrics
        "MEASURES",
        "CONCERNS",
        "SUPPORTED_BY",
        "SUPPORTED_BY_STATISTIC",
        "CONTRADICTS",
    }
)

#: The one predicate ``include_internal=true`` adds, and the only thing that flag can do.
#: ``MENTIONS_LEMMA`` runs ``Passage -> Lemma``, and all 10,031 ``:Lemma`` nodes are marked
#: ``:Internal`` -- not because a lemma is plumbing, but because V3 demoted the whole layer
#: after 39 deity lemmas began surfacing in product traversal looking like deities.
LEMMA_RELATIONSHIP: Final = "MENTIONS_LEMMA"

#: Predicates deliberately NOT traversable, with the reason, because "we forgot" and "we
#: decided" are indistinguishable from the outside.
#:
#: ``CONTAINS`` (22,537), ``HAS_TEXT_VERSION`` (44,276), ``HAS_TRANSLATION`` (18,415) are
#: the corpus's own tree and its stored surfaces: structure and text, not claims, and
#: navigating them is what the passage endpoints are for. ``MENTIONS_LEMMA`` (9,000) is
#: behind ``include_internal``. ``QA_ISSUE_ON`` (915) attaches this repository's doubts about
#: itself to passages and is never product content. ``ASSERTION_PREDICATE`` (2,672),
#: ``ASSERTION_AGENT`` (2,660) and ``ASSERTION_TARGET`` (918) are the internal wiring of the
#: reified ``SemanticAssertion`` node: a client reaches an assertion through
#: ``HAS_SEMANTIC_ASSERTION`` and reads its roles off the node, so exposing the spokes would
#: add three hops that mean nothing to a reader.
NON_TRAVERSABLE_REASONS: Final[dict[str, str]] = {
    "CONTAINS": "the corpus's own containment tree; use the passage navigation endpoints",
    "HAS_TEXT_VERSION": "a stored text surface, not a knowledge claim",
    "HAS_TRANSLATION": "a stored text surface, not a knowledge claim",
    "MENTIONS_LEMMA": "lexical layer, admitted only by include_internal=true",
    "QA_ISSUE_ON": "this repository's doubts about itself; never product content",
    "ASSERTION_PREDICATE": "internal wiring of a reified assertion node",
    "ASSERTION_AGENT": "internal wiring of a reified assertion node",
    "ASSERTION_TARGET": "internal wiring of a reified assertion node",
    # SHARES_FORMULA_WITH used to be refused here, on the stated grounds that it "carries 0
    # edges, so traversing it would traverse nothing". Wave 3 wrote 6,148 of them and the
    # sentence became a false statement about the graph -- the worst kind of refusal, because
    # it tells a reader the layer is empty. It is traversable above.
    # HAS_RITUAL_STEP was refused here until M7. The reason was measurable and it is now
    # false: the step nodes carry display_type = RITUAL_STEP and a step_key that is
    # deterministic, URN-backed and collision-free over all 3,121 of them, so a traversal
    # reaching one can name it. See docs/reports/data-completeness/SCHEMA_MIGRATION_CARDS.md.
    # Superseded, not abandoned. RESOLVES_TO_DEVATA was invented for a relation the
    # ontology already declares as ASCRIBES_TO_DEVATA, with the right signature and a
    # docstring describing the same derivation; the 39 live edges are staged for retyping
    # into it at zero census delta. It is refused rather than left unclassified because an
    # unclassified populated type is invisible to /api/v1/graph and nothing tells the reader
    # it exists -- and this entry must be DELETED, not amended, once the retype lands.
    "RESOLVES_TO_DEVATA": "superseded by ASCRIBES_TO_DEVATA, which the ontology already "
    "declares for this relation; the 39 edges are staged for retyping and this refusal "
    "comes out in the same change",
    # Measured, not assumed: the 4,079 edges run over only 4,076 distinct (source, type,
    # target) triples, because a verse may contribute more than one pada to the same group.
    # VG:RV:SAK:M01:S097:V001 contributes pada a and pada c to one group, and two more
    # verses do the same. The public relationship id IS that triple, so whitelisting this
    # predicate would publish 6 edges under 3 ids -- the same two-objects-one-id defect the
    # publication-identity repair exists to close, reintroduced on a different layer.
    #
    # This is a refusal about our id scheme, not about the layer, and it is stated rather
    # than left blank so a reader is told the layer is there. It comes out as soon as the
    # relationship id can carry the pada discriminator the edges already store in pada_key.
    "HAS_PARALLEL_PADA": "the public relationship id is the (source, type, target) triple, "
    "and 3 verses each contribute two padas to one group, so 6 of the 4,079 edges would "
    "share an id with another edge; refused until the id can carry the stored pada_key",
    "ASSERTION_ROLE": "internal wiring of a reified assertion node",
    "REFERS_TO": "internal wiring of the semantic-role layer: it resolves a role filler to "
    "its referent, and the filler is not a thing a reader asked to see",
    "QUALITY_VERDICT_ABOUT": "this repository's assessment of its own passages; never "
    "product content, on the same footing as QA_ISSUE_ON",
    "POSITION_ASSERTED_BY": "internal wiring of a reified scholarly position; read the "
    "position through /api/v1/insights, where it arrives with its falsifier",
    "POSITION_STATED_IN": "internal wiring of a reified scholarly position",
    "REPORTED_IN": "internal wiring of a reified scholarly position",
}

#: Predicates a path may cross. Narrower than the neighbourhood set on purpose: a path is a
#: claim that two things are *related*, so each hop has to be a relation a reader would
#: accept as one. ``HAS_FORMULA`` is present and ``MEMBER_OF_FAMILY`` is absent -- see
#: :data:`FAMILY_MEMBERSHIP_DIRECTION`, because they are the same 2,037 memberships and
#: allowing both would let a path bounce between a family and its formulas.
PATH_RELATIONSHIPS: Final[frozenset[str]] = frozenset(
    {
        "EXACT_PARALLEL_OF",
        "NEAR_PARALLEL_OF",
        "REUSES_TEXT_FROM",
        "VARIANT_OF",
        "PARALLEL_TO",
        "HAS_FORMULA",
        "USES_FORMULA",
        "MENTIONS_DEVATA",
        "MENTIONS_ENTITY",
        "ABOUT_CONCEPT",
        "SHARES_ENTITY_VOCABULARY_WITH",
        "HAS_RISHI",
        "HAS_CHANDAS",
        "HAS_DEVATA",
        "BELONGS_TO_FAMILY",
        "CO_OCCURS_WITH",
        "DEVATA_ASSOCIATED_WITH",
        "HAS_AXIS",
        "HAS_EPITHET",
        "TREATS",
        "PROTECTS_FROM",
        "ADDRESSES_CONCERN",
        "USED_FOR_RITE",
        "DESCRIBED_IN",
        "BROADER_THAN",
        "PERFORMS_ACTION",
        "IS_ASKED_TO",
    }
)

assert PATH_RELATIONSHIPS <= TRAVERSABLE_RELATIONSHIPS, (
    "a path may only cross predicates a neighbourhood would also show"
)

# ---------------------------------------------------------------------------
# The FormulaFamily direction contract (spec section 22)
# ---------------------------------------------------------------------------

#: The authoritative direction for a family membership, and the reason there is a choice.
#:
#: ``(Formula)-[:MEMBER_OF_FAMILY]->(FormulaFamily)`` carries 2,037 edges and
#: ``(FormulaFamily)-[:HAS_FORMULA]->(Formula)`` carries the same 2,037, mirrored property
#: for property including ``membership_id``. ``load_formula_family_outward`` states the
#: relationship plainly: ``HAS_FORMULA`` is a *mirror, not a derivation*, copied from the
#: inbound edges that already landed so the two cannot disagree about ``role`` or tier.
#:
#: So ``MEMBER_OF_FAMILY`` is authoritative and is what the formula surfaces traverse.
#: Measured: inbound ``MEMBER_OF_FAMILY`` reconciles with the recorded ``member_count`` on
#: **all 720** families with zero disagreements, outbound ``HAS_FORMULA`` likewise, and
#: traversing both gives exactly ``2 x member_count`` on all 720 -- which is the
#: double-count this constant exists to prevent.
FAMILY_MEMBERSHIP_DIRECTION: Final = "MEMBER_OF_FAMILY"

#: The mirror. Traversable in a neighbourhood, where it is what makes a family navigable
#: outward, and excluded from paths so a route cannot use both halves of one membership.
FAMILY_MEMBERSHIP_MIRROR: Final = "HAS_FORMULA"

# ---------------------------------------------------------------------------
# Confidence: measured, not guessed
# ---------------------------------------------------------------------------

#: Predicates whose ``confidence`` is a single constant on every edge, with that constant.
#:
#: Measured by the frozen query ``confidence_is_a_pipeline_constant``, which grades each
#: confidence-bearing predicate: these seven come back ``SINGLE_CONSTANT`` with
#: ``distinct_values = 1``. A value identical on 17,889 edges orders none of them, so
#: filtering on it selects a pipeline branch and not a quality. The API therefore returns
#: null for ``confidence`` on these and surfaces the constant as ``pipeline_prior``.
#:
#: ``INVOLVES_SUBSTANCE`` (3 edges) and ``REFERS_TO_PLACE`` (1) also grade
#: ``SINGLE_CONSTANT`` and are deliberately absent: with three edges and one edge a single
#: value is a sample size, not a pipeline constant, and calling it one would be a claim
#: about a mechanism that the count cannot support.
PIPELINE_CONSTANT_PREDICATES: Final[dict[str, float]] = {
    "HAS_RISHI": 1.0,
    "HAS_CHANDAS": 1.0,
    "HAS_DEVATA": 1.0,
    "HAS_DEVATA_ASCRIPTION": 1.0,
    "HAS_DEVATA_DERIVED": 1.0,
    "ASCRIBES_TO_DEVATA": 1.0,
    "BELONGS_TO_FAMILY": 1.0,
}
#: ``HAS_DEVATA_DERIVED`` and ``ASCRIBES_TO_DEVATA`` are the two most recent entries, and the
#: note they replace is worth recording because it was wrong in a way nothing caught.
#:
#: That note said they were "deliberately ABSENT" because "neither carries a ``confidence``
#: property at all -- 0 of 882 and 0 of 39", and told the next reader to add them only in the
#: same change that landed a staged property correction. The property correction had already
#: landed. Measured live: 882 of 882 ``HAS_DEVATA_DERIVED`` edges and 39 of 39
#: ``ASCRIBES_TO_DEVATA`` edges carry ``confidence = 1.0``, matching the parent
#: ``HAS_DEVATA_ASCRIPTION`` (5,385 of 5,385 at 1.0) exactly as that note predicted they
#: would. So the stated reason for the omission had become the opposite of the data, and the
#: omission it justified made ``test_the_varying_confidence_predicates_still_vary`` red -- the
#: 921 edges were presenting an unearned per-edge confidence on a serving surface.
#:
#: The lesson is the one the old note was itself drawing, pointed the other way: a comment
#: that carries a measurement goes stale silently, because nothing re-measures a comment.
#: The counts above are asserted by the two live-invariant tests, not by this prose.

#: Predicates where ``confidence`` genuinely varies, so a per-edge value means something
#: relative to its siblings. Still a pipeline output: ``confidence_is_a_pipeline_constant``
#: records ``calibration_evidence = 'NONE'`` for the whole graph, because no labelled
#: evaluation set and no reliability curve exist anywhere in it.
VARYING_CONFIDENCE_PREDICATES: Final[frozenset[str]] = frozenset(
    {
        "ABOUT_CONCEPT",
        "INVOKES",
        "DESCRIBES",
        "REQUESTS",
        "PRAISES",
        "DESCRIBES_ACTION",
        "INVOLVES_OFFERING",
        "INVOLVES_RITUAL",
        "HAS_THEME",
        "CONTRASTS_WITH",
        "REFERS_TO_NATURAL_PHENOMENON",
        # These two carried a single value because they are tiny -- 3 edges and 1 -- which
        # is a sample size and not a pipeline constant. R5 withdrew their confidence too,
        # to uncalibrated_pipeline_score, and deliberately did NOT give them the
        # source-explicit tier marker: 0.85 and 0.75 are not the source-explicit 1.0, and
        # marking them so would assert something false about their evidence. They stay
        # listed here as declared members of the varying set, so that a future edge of
        # either predicate arriving with a real varying confidence is not a surprise.
        "INVOLVES_SUBSTANCE",
        "REFERS_TO_PLACE",
    }
)

#: What a client is told when it filters on ``confidence``. Built from
#: :data:`PIPELINE_CONSTANT_PREDICATES` so the sentence cannot drift from the map.
CONFIDENCE_FILTER_CAVEAT: Final = (
    "min_confidence filters a PIPELINE PRIOR, not a calibrated confidence. "
    + str(len(PIPELINE_CONSTANT_PREDICATES))
    + " predicates stamp one value on every edge they have ("
    + ", ".join(f"{name} = {value}" for name, value in sorted(PIPELINE_CONSTANT_PREDICATES.items()))
    + "), so a threshold either keeps all of their edges or none, and keeping them is not "
    "evidence of quality. GAP-QUALITY-003 WITHDREW the stored field from those seven: the "
    "edges carry source_explicit_tier_marker instead, because the value encoded an evidence "
    "TIER and not a probability, and this map is now the one place the prior is declared. "
    "Those edges return confidence = null and the constant as pipeline_prior; edges of "
    "predicates where the value varies are filtered on it, and every one of those carries "
    "calibration_status = NOT_CALIBRATED_NO_HUMAN_LABELLED_SAMPLE. No predicate in this "
    "graph has a labelled evaluation set or a reliability curve behind its confidence."
)

# ---------------------------------------------------------------------------
# Hubs
# ---------------------------------------------------------------------------

#: Degree above which a node is a hub and a route through it stops distinguishing its
#: endpoints. Calibrated against the live degree distribution rather than chosen: the
#: maximum degree of a mantra is 88, of a formula 95, of a hymn 95, of a formula family 28,
#: of a seer family 51 -- so 200 sits clear of every node class a reader would call a
#: *subject*. Above it are 137 of 108,779 nodes (0.13%) -- measured on the Product-V1
#: graph, and left dated rather than restated, because re-running it is a separate
#: decision and a figure re-attributed to a graph it was not taken on is worse than an
#: old one: the frequent metres, the twenty
#: highest-degree deities, and the concept hubs (*soma*, *heaven*, *sacrifice*, *cattle*).
#:
#: Total degree is used and not degree over the traversable set, for a measured reason: the
#: typed form ``COUNT { (n)-[:57 types]-() }`` cost 700-870 ms on a depth-2 expansion where
#: the untyped ``COUNT { (n)--() }`` cost 74 ms, because the untyped one is an O(1) read
#: from the degree store. The inflation it introduces is small and known -- a passage
#: carries about five internal edges for its text surfaces -- and 88 + 5 is still nowhere
#: near 200.
HUB_DEGREE_CEILING: Final = 200

#: How many shortest routes are scored before the least hub-mediated one is chosen. A hard
#: cap, so a pair joined through a hub with thousands of equivalent routes costs a bounded
#: amount rather than materialising all of them.
PATH_CANDIDATE_LIMIT: Final = 200

#: Path depth bounds. Four is the ceiling because a five-hop route through this graph is
#: connected to everything and explains nothing; three is the default because at three the
#: hub-free routes are still legible.
PATH_MAX_DEPTH: Final = 4
PATH_DEFAULT_DEPTH: Final = 3

#: Neighbourhood depth bounds. Two, and no more: depth 3 from Indra reaches most of the
#: Rigveda, and a payload that large is not a neighbourhood.
NEIGHBOURHOOD_MAX_DEPTH: Final = 2

#: Total nodes a neighbourhood may return, across all types and both depths. Independent of
#: ``limit_per_type``, because 57 predicates times two directions times 50 is 5,700 and a
#: per-type bound alone is not a bound on the payload.
NEIGHBOURHOOD_NODE_BUDGET: Final = 400

#: Edges a depth-2 expansion may add. Smaller than the node budget's implication because
#: the depth-2 frontier is the part that grows multiplicatively.
NEIGHBOURHOOD_DEPTH2_EDGE_BUDGET: Final = 300

# ---------------------------------------------------------------------------
# Node identity resolution
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NodeKind:
    """One resolvable kind of product id: which label carries it, and under which property.

    ``indexed`` records whether the lookup is index-backed. Two kinds are not, and are
    admitted anyway because their label scans are 324 and 41 nodes respectively -- cheaper
    than the index they lack. Anything larger without an index would be excluded.
    """

    label: str
    property: str
    product_type: str
    indexed: bool = True


#: Every id a client may name, in the order the resolver tries them. Derived from the live
#: schema: each of the indexed entries has a uniqueness constraint or range index on
#: exactly this label and property, so resolution is a point lookup and an ambiguous id is
#: detectable rather than merely unlikely.
RESOLVABLE_KINDS: Final[tuple[NodeKind, ...]] = (
    NodeKind("Passage", "canonical_key", "PASSAGE"),
    NodeKind("Devata", "entity_key", "DEVATA"),
    NodeKind("Rishi", "entity_key", "RISHI"),
    NodeKind("Chandas", "entity_key", "CHANDAS"),
    NodeKind("DomainEntity", "entity_key", "DOMAIN_ENTITY"),
    NodeKind("Formula", "formula_id", "FORMULA"),
    NodeKind("FormulaFamily", "family_id", "FORMULA_FAMILY"),
    NodeKind("Epithet", "epithet_key", "EPITHET"),
    NodeKind("DeityAxis", "axis_key", "DEITY_AXIS"),
    NodeKind("DeityGroup", "group_key", "DEITY_GROUP"),
    NodeKind("RishiFamily", "family_key", "RISHI_FAMILY"),
    NodeKind("DerivedMetric", "metric_id", "DERIVED_METRIC"),
    NodeKind("InterpretiveClaim", "claim_id", "INTERPRETIVE_CLAIM"),
    NodeKind("RitualStep", "step_key", "RITUAL_STEP"),
    NodeKind("Work", "work_id", "WORK"),
    NodeKind("DevataAscription", "entity_key", "DEVATA_ASCRIPTION", indexed=False),
    NodeKind("ActionPredicate", "predicate", "ACTION_PREDICATE", indexed=False),
)

#: The properties, in precedence order, that carry a node's stable product id. Used to read
#: an id back off a node the traversal reached rather than one the client named. Measured
#: complete: of the edges carried by the 57 traversable predicates, none has an endpoint
#: for which every one of these is null.
from vedagraph.graph.public_identity import (
    ASSERTION_PREFIX, ID_PROPERTIES, public_id, public_id_cypher,
)

STABLE_ID_PROPERTIES: Final[tuple[str, ...]] = ID_PROPERTIES


#: Product type names, keyed by the graph's own ``display_type``. Every non-internal node
#: carries one and there are 42 distinct values; this map covers all of them, and
#: ``tests/api/test_graph.py`` asserts against the live graph that it still does, so a
#: rebuild that introduces a new type fails a test instead of shipping a raw label.
PRODUCT_TYPE_BY_DISPLAY_TYPE: Final[dict[str, str]] = {
    "RITUAL_STEP": "RITUAL_STEP",
    "MANTRA": "MANTRA",
    "HYMN": "HYMN",
    "SECTION": "SECTION",
    "STRUCTURAL_CONTAINER": "STRUCTURAL_CONTAINER",
    "Work": "WORK",
    "Devata": "DEVATA",
    "Rishi": "RISHI",
    "RishiFamily": "RISHI_FAMILY",
    "Chandas": "CHANDAS",
    "Epithet": "EPITHET",
    "DeityAxis": "DEITY_AXIS",
    "DeityGroup": "DEITY_GROUP",
    "DevataAscription": "DEVATA_ASCRIPTION",
    "ActionPredicate": "ACTION_PREDICATE",
    # One key, because the graph now holds one spelling. It held two: 4,865 nodes carried
    # "SemanticAssertion" from the two domain builders and 30,266 carried
    # "SEMANTIC_ASSERTION" from a stabilisation backfill's
    # coalesce(s.display_type, 'SEMANTIC_ASSERTION') -- a value declared in no ontology
    # module. Mapping both here served one product type under two names and papered over
    # the split rather than closing it; downstream, frontend/scripts/world-groups.json has
    # an entry for the label spelling only, so those 30,266 nodes were drawn in the browser
    # world as "other" while the other 4,865 were drawn as "record". The 30,266 were
    # normalised to the label spelling and the second key is deliberately NOT kept as a
    # tolerance: if a builder writes it again, the live-graph coverage test fails loudly
    # instead of the value being quietly accepted a second time.
    #
    # PADA_PARALLEL_GROUP below is the same shape and was NOT harmless, contrary to an
    # earlier note here: its 1,434 nodes have no entry in world-groups.json either, so they
    # are drawn in the browser world as "other" exactly as the 30,266 assertions were. What
    # differs is the remedy -- no node has ever carried the PascalCase spelling, so there
    # was nothing in the graph to normalise, and the fix is a missing group mapping rather
    # than a migration. It is left open and reported rather than described as benign.
    "SemanticAssertion": "SEMANTIC_ASSERTION",
    # The graph's own spelling, and only it. A "PadaParallelGroup" key sat beside this one
    # and no node has ever carried that value -- measured: 1,434 nodes, all
    # PADA_PARALLEL_GROUP -- so unlike the assertion case there was nothing in the graph to
    # normalise and removing the dead key changes no data. It was NOT harmless: see the
    # note above.
    "PADA_PARALLEL_GROUP": "PADA_PARALLEL_GROUP",
    "DerivedMetric": "DERIVED_METRIC",
    "InterpretiveClaim": "INTERPRETIVE_CLAIM",
    "Formula": "FORMULA",
    "FormulaFamily": "FORMULA_FAMILY",
    "Concept": "CONCEPT",
    "PhilosophicalConcept": "PHILOSOPHICAL_CONCEPT",
    "Condition": "CONDITION",
    "HumanConcern": "HUMAN_CONCERN",
    "SocialRite": "SOCIAL_RITE",
    "RitualRole": "RITUAL_ROLE",
    "Ritual": "RITUAL",
    "Offering": "OFFERING",
    "Substance": "SUBSTANCE",
    "Metal": "METAL",
    "Plant": "PLANT",
    "Crop": "CROP",
    "Animal": "ANIMAL",
    "Object": "OBJECT",
    "Weapon": "WEAPON",
    "Place": "PLACE",
    "River": "RIVER",
    "Region": "REGION",
    "Tribe": "TRIBE",
    "NaturalPhenomenon": "NATURAL_PHENOMENON",
    "CosmicEntity": "COSMIC_ENTITY",
    "Action": "ACTION",
    "Quality": "QUALITY",
    "State": "STATE",
    "Theme": "THEME",
    "Lemma": "LEMMA",
}

#: Node properties a response may carry in ``metadata``. A whitelist and not a blacklist:
#: the frozen graph stores ``run_id``, ``pipeline_version``, ``build_pass``,
#: ``prompt_policy``, ``model`` and ``domain_model_version`` on many nodes, every one of
#: which is a fact about this repository's build rather than about the Vedas, and a
#: copy-everything projection would have shipped all of them.
NODE_METADATA_KEYS: Final[frozenset[str]] = frozenset(
    {
        # passage
        "veda",
        "canonical_citation",
        "structural_path",
        "sequence_in_parent",
        # deity
        "structure",
        # The recorded eligibility ruling, so a client reading the graph sees the same
        # decision the deity routes filter on rather than re-deriving one from `structure`.
        "non_deity_kind",
        "deity_eligibility_ruling",
        "is_composite",
        "component_count",
        "axes",
        "axis_count",
        "epithet_count",
        "attribution_scope",
        "axis",
        # naming
        "label_iast",
        "label_en",
        "preferred_label",
        "preferred_label_en",
        "preferred_label_sa",
        "aliases_iast",
        "aliases_en",
        "aliases_sa",
        "normalized_name",
        "eponym_iast",
        "patronymic_iast",
        "patronymics_iast",
        "personal_names_iast",
        # seers
        "is_seer",
        "non_seer_kind",
        "family_assignment_class",
        "vrddhi_derivation",
        # domain entities
        "node_type",
        "condition_kind",
        "centrality_degree",
        "centrality_share",
        "centrality_measure",
        "centrality_layer",
        # formulaic diction
        "display_form",
        "normalized",
        "word_count",
        "char_count",
        "source_forms",
        "representative_display_form",
        "representative_coverage",
        "member_count",
        "core_count",
        "secondary_core_count",
        "expansion_count",
        "variant_count",
        "veda_span",
        "containment_depth",
        "min_word_count",
        "max_word_count",
        "parallel_corroborated",
        # counts and reach
        "occurrence_count",
        "mantra_count",
        "token_count",
        "vedas",
        "veda_counts",
        "cross_veda",
        "layer_veda_scope",
        "layer_veda_scope_note",
        # grading, which is the graph's own and not build state
        "quality_tier",
        "trust",
        "evidence_basis",
        "evidence_count",
        "notes",
        # action predicates and lexis
        "predicate",
        "argument_frame",
        "root_count",
        "root_tokens",
        "lemma",
        "normalized_lemma",
        "parts_of_speech",
        # ascriptions
        "is_ascription_descriptor",
    }
)

#: Property names a response must never carry, whatever a whitelist says. Asserted disjoint
#: from :data:`NODE_METADATA_KEYS` below, so the two cannot drift into agreement by
#: accident, and asserted absent from serialized payloads by
#: ``tests/api/test_graph.py``.
FORBIDDEN_METADATA_KEYS: Final[frozenset[str]] = frozenset(
    {
        "run_id",
        "pipeline_version",
        "build_pass",
        "prompt_policy",
        "model",
        "domain_model_version",
        "vocabulary_version",
        "centrality_pipeline_version",
        "decomposition_build_pass",
        "decomposition_method",
        "registry_namespace",
        "entity_id",
        "source_id",
        "reviewer_model",
        "review_run",
        "candidate_id",
        "issue_id",
        "text_id",
        "translation_id",
    }
)

assert NODE_METADATA_KEYS.isdisjoint(FORBIDDEN_METADATA_KEYS), (
    "a property cannot be both product metadata and build state"
)

#: Values from a JSON-string property that should be parsed before being returned. The
#: frozen graph stores these as JSON text; handing a client the string would make it parse
#: a quoted map that this API already knows the shape of.
JSON_METADATA_KEYS: Final[frozenset[str]] = frozenset({"veda_counts"})

#: Longest string a metadata value may be. ``notes`` and ``layer_veda_scope_note`` are
#: sentences, and a node view is not the place for an essay.
METADATA_STRING_LIMIT: Final = 400

#: Most evidence spans one edge may carry into a response.
MAX_EVIDENCE_SPANS: Final = 6


# ---------------------------------------------------------------------------
# Relationship identity codec
# ---------------------------------------------------------------------------

#: Field separator inside a relationship token, before base64url encoding. ASCII unit
#: separator, chosen by measurement rather than taste: ten ``DerivedMetric.metric_id``
#: values contain a ``|`` (``VG:METRIC:ATTRIBUTION_PRECISION_BY_VEDA:VG:WORK:RV:SAK|
#: HAS_RISHI:CONTAINER_INHERITED``), so the obvious pipe delimiter would have minted
#: tokens that parse back into the wrong number of fields. No stable id in the graph
#: contains ``\x1f``, and a C0 control character cannot appear in a canonical key by
#: construction. :func:`encode_relationship_id` asserts it anyway.
_FIELD_SEPARATOR: Final = "\x1f"

#: Token version prefix. Present so that a token minted under a future scheme is rejected
#: with a 400 naming the problem rather than decoded into something plausible.
_TOKEN_PREFIX: Final = "r1-"

#: Domain id property, per relationship type, where the layer minted one.
#:
#: Presence here means "this type *may* carry the property", never "it does": measured, 750
#: of 1,006 ``EXACT_PARALLEL_OF`` edges carry ``parallel_id`` and 256 do not, so
#: :meth:`GraphService._relationship_token` checks the value on each edge and falls back to
#: the endpoint triple per edge rather than per type.
DOMAIN_ID_PROPERTY_BY_TYPE: Final[dict[str, str]] = {
    "EXACT_PARALLEL_OF": "parallel_id",
    "NEAR_PARALLEL_OF": "parallel_id",
    "REUSES_TEXT_FROM": "parallel_id",
    "VARIANT_OF": "parallel_id",
    "MENTIONS_DEVATA": "mention_id",
    "MENTIONS_ENTITY": "mention_id",
    "ABOUT_CONCEPT": "assertion_id",
    "MEMBER_OF_FAMILY": "membership_id",
    "HAS_FORMULA": "membership_id",
    "INVOKES": "candidate_id",
    "DESCRIBES": "candidate_id",
    "REQUESTS": "candidate_id",
    "PRAISES": "candidate_id",
    "DESCRIBES_ACTION": "candidate_id",
    "HAS_THEME": "candidate_id",
    "CONTRASTS_WITH": "candidate_id",
    "INVOLVES_OFFERING": "candidate_id",
    "INVOLVES_RITUAL": "candidate_id",
    "INVOLVES_SUBSTANCE": "candidate_id",
    "REFERS_TO_NATURAL_PHENOMENON": "candidate_id",
    "REFERS_TO_PLACE": "candidate_id",
}


@dataclass(frozen=True)
class RelationshipToken:
    """A decoded relationship id: enough to look one edge up, parameterised."""

    basis: RelationshipIdBasis
    relationship_type: str
    domain_id: str | None = None
    source_id: str | None = None
    target_id: str | None = None


def encode_relationship_id(
    *,
    relationship_type: str,
    domain_id: str | None,
    source_id: str,
    target_id: str,
) -> tuple[str, RelationshipIdBasis]:
    """Mint a stable, opaque token for one edge, and say which basis it used.

    Prefers the domain id where the edge actually has one. The endpoint fallback is sound
    because ``(source, type, target)`` was measured to be a key over every traversable
    type; the type is always in the token because ``membership_id`` is shared by both
    directions of a family membership and an id-only token would be ambiguous.
    """
    fields: tuple[str, ...]
    if domain_id:
        fields = (relationship_type, domain_id)
        basis = RelationshipIdBasis.DOMAIN_ID
    else:
        fields = (relationship_type, source_id, target_id)
        basis = RelationshipIdBasis.ENDPOINT_TRIPLE
    for field_value in fields:
        if _FIELD_SEPARATOR in field_value:
            # Unreachable against the frozen graph and checked anyway: a token that cannot
            # round-trip must fail here, loudly, rather than resolve to the wrong edge.
            raise ValueError(
                f"cannot mint a relationship token: {relationship_type} carries a "
                "separator character in one of its identity fields"
            )
    payload = _FIELD_SEPARATOR.join((basis.value, *fields))
    encoded = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii").rstrip("=")
    return f"{_TOKEN_PREFIX}{encoded}", basis


def decode_relationship_id(token: str, *, allowed_types: frozenset[str]) -> RelationshipToken:
    """Parse a token back into a parameterised lookup, or refuse it.

    Every failure mode is a 400 and none is a 500: a wrong prefix, invalid base64, a
    payload that is not valid UTF-8, the wrong number of fields, an unknown basis, and a
    relationship type outside ``allowed_types``. The type check runs through
    :func:`validated_relationship_types`, so the only way a name reaches the query text is
    by being in a whitelist this module owns.
    """
    if not token.startswith(_TOKEN_PREFIX):
        raise BadRequestError(
            "That is not a relationship id issued by this API.",
            hint="Relationship ids come from the `edges[].id` field of "
            "GET /api/v1/graph/neighborhood/{id}. Neo4j internal ids are never accepted.",
        )
    body = token[len(_TOKEN_PREFIX) :]
    padding = "=" * (-len(body) % 4)
    try:
        payload = base64.urlsafe_b64decode(body + padding).decode("utf-8")
    except (binascii.Error, ValueError, UnicodeDecodeError) as exc:
        raise BadRequestError("That relationship id is malformed.") from exc
    parts = payload.split(_FIELD_SEPARATOR)
    if len(parts) == 3 and parts[0] == RelationshipIdBasis.DOMAIN_ID.value:
        _, relationship_type, domain_id = parts
        validated_relationship_types((relationship_type,), allowed_types)
        return RelationshipToken(
            basis=RelationshipIdBasis.DOMAIN_ID,
            relationship_type=relationship_type,
            domain_id=domain_id,
        )
    if len(parts) == 4 and parts[0] == RelationshipIdBasis.ENDPOINT_TRIPLE.value:
        _, relationship_type, source_id, target_id = parts
        validated_relationship_types((relationship_type,), allowed_types)
        return RelationshipToken(
            basis=RelationshipIdBasis.ENDPOINT_TRIPLE,
            relationship_type=relationship_type,
            source_id=source_id,
            target_id=target_id,
        )
    raise BadRequestError("That relationship id is malformed.")


# ---------------------------------------------------------------------------
# Predicate semantics: the "why"
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PredicateSemantics:
    """What a predicate asserts, as a phrase and as two sentences.

    ``limit`` is the half that makes this endpoint worth having. Anyone can render
    "RV 1.1.1 --HAS_RISHI--> Madhucchandas"; what a reader needs is that the Anukramani said
    it of the *hymn* and a scope rule projected it onto the verse.
    """

    phrase: str
    asserts: str
    limit: str


#: Every traversable predicate, with the sentence a reader needs. A live test asserts this
#: covers the whole traversable set, so a predicate added to the whitelist without an
#: explanation fails rather than shipping a bare edge.
PREDICATE_SEMANTICS: Final[dict[str, PredicateSemantics]] = {
    "EXACT_PARALLEL_OF": PredicateSemantics(
        "is an exact parallel of",
        "The two passages match on a normalised textual surface.",
        "Exact means exact on the surface compared, which for a cross-script pair is the "
        "weakest one they share; it is not a claim about which text borrowed from which.",
    ),
    "NEAR_PARALLEL_OF": PredicateSemantics(
        "is a near parallel of",
        "The two passages resemble each other closely on a normalised textual surface.",
        "A resemblance score, not a transmission claim. Cross-script comparison bottoms "
        "out at SANDHI_INSENSITIVE because a Devanagari and a Latin text share no code "
        "points, so the level reached is a property of the scripts as much as of the texts.",
    ),
    "REUSES_TEXT_FROM": PredicateSemantics(
        "reuses text from",
        "This passage's wording is found in the passage it points to.",
        "Direction here follows the corpora's conventional relative order, not a "
        "demonstrated act of borrowing by a redactor.",
    ),
    "VARIANT_OF": PredicateSemantics(
        "is a textual variant of",
        "The two passages differ by an amount the matcher classed as variation.",
        "A string-distance verdict. It does not distinguish a genuine recensional variant "
        "from a sandhi boundary falling differently.",
    ),
    "PARALLEL_TO": PredicateSemantics(
        "is parallel to",
        "The two passages were found parallel by an earlier pass that recorded its "
        "strongest method rather than a score.",
        "These 69 edges come from a producer that wrote no parallel id and no match level, "
        "so they cannot be compared numerically with the near-parallel layer.",
    ),
    "HAS_FORMULA": PredicateSemantics(
        "contains the formula",
        "This formula family counts that formula as a member.",
        "The outward mirror of MEMBER_OF_FAMILY over the same 2,037 memberships; the two "
        "must never both be counted.",
    ),
    "MEMBER_OF_FAMILY": PredicateSemantics(
        "is a member of the formula family",
        "This formula belongs to that family of shared wording.",
        "A family is a representative wording plus what contains or resembles it. "
        "Membership can be transitive, in which case the member and the representative may "
        "share no words at all.",
    ),
    "USES_FORMULA": PredicateSemantics(
        "uses the formula",
        "The passage's text contains this formulaic wording.",
        "Formula identity is a normalised-string match, so a shared formula is shared "
        "diction rather than a demonstrated line of transmission.",
    ),
    "MENTIONS_DEVATA": PredicateSemantics(
        "names the deity",
        "The passage names this deity in its own text.",
        "The only deity predicate reaching all four corpora, and it reaches them by two "
        "different instruments: the Rigveda's edges come from manual scholarly lemma "
        "annotation and the rest from surface token or sandhi matching, which has no "
        "morphology behind it.",
    ),
    "MENTIONS_ENTITY": PredicateSemantics(
        "names",
        "The passage names this entity in its own text.",
        "An alias match. Where the alias is also a deity name the edge is flagged "
        "theonym_ambiguous, because agni is fire and it is also Agni.",
    ),
    "MENTIONS_EPITHET": PredicateSemantics(
        "attests the epithet",
        "The passage attests this epithet, per the Rigvedic morphological annotation.",
        "RIGVEDA ONLY, and the bound is a property of the evidence rather than of the "
        "epithets: the annotation layer covers the Rigveda's 10,552 mantras and none of "
        "the other 9,658, so an epithet with no Samavedic edge is UNANNOTATED there and "
        "not absent. Read `epithet_match_tier`: STEM_LEMMA edges come from the "
        "annotator's own lemma and cover every inflection of it, while "
        "ATTESTED_SURFACE_FORM edges cover one attested word form because the epithet is "
        "itself an inflected form -- the duals dasrā, nāsatyā and rudravartanī, whose "
        "stems the annotator names and whose wider inflection is deliberately not "
        "claimed.",
    ),
    "ABOUT_CONCEPT": PredicateSemantics(
        "is about",
        "The passage was judged to concern this concept.",
        "Reached by alias matching over Sanskrit and a 19th-century English translation; "
        "an edge resting only on the translation inherits that translator's reading.",
    ),
    "SHARES_ENTITY_VOCABULARY_WITH": PredicateSemantics(
        "shares entity vocabulary with",
        "Both passages name the same registry entities.",
        "THIS IS NOT A CONCEPTUAL-SIMILARITY CLAIM. It measures shared vocabulary, and no "
        "non-lexical resemblance measure exists anywhere in this graph. Read "
        "`distinctiveness`, not the count: three shared entities are weak evidence when "
        "they are heaven, sacrifice and soma, and strong when one is the altar.",
    ),
    "HAS_RISHI": PredicateSemantics(
        "is ascribed to the seer",
        "The Anukramani names this seer for this passage.",
        "Mostly inherited rather than stated: 15,177 of 17,889 of these edges are a hymn's "
        "label projected onto each verse inside it, and every one of the Atharvaveda's "
        "5,084 is. Read `evidence.evidence_basis` before treating it as a statement about "
        "this verse.",
    ),
    "HAS_CHANDAS": PredicateSemantics(
        "is in the metre",
        "The Anukramani names this metre for this passage.",
        "10,399 of 16,298 arrive by projecting a hymn's label downward. The Samaveda "
        "carries no metre layer at all, so its absence there is a missing layer.",
    ),
    "HAS_DEVATA": PredicateSemantics(
        "is ascribed to the deity",
        "The Anukramani names this deity as the passage's addressee.",
        "Rigveda-only -- all 10,558 edges -- and 8,329 of them are inherited from a hymn "
        "label. This predicate's Rigvedic bound is NOT the corpus's: the Atharvaveda "
        "records its dedications under HAS_DEVATA_ASCRIPTION and HAS_DEVATA_DERIVED, so a "
        "reader must not take a zero here as a corpus that names no addressee. The devata "
        "slot is also not a theological claim: it holds human patrons and praise of a gift "
        "as well as gods.",
    ),
    "HAS_DEVATA_ASCRIPTION": PredicateSemantics(
        "carries the deity ascription",
        "The passage carries this Anukramani ascription descriptor.",
        "The Atharvaveda's own dedication layer, 5,385 edges over 4,665 of its 6,590 "
        "passages, holding Whitney's verbatim descriptor rather than a deity name. It is a "
        "descriptor of the dedication's FORM and not itself an attribution to a named god "
        "-- but 47 of its 324 descriptors now resolve to one through ASCRIBES_TO_DEVATA, "
        "and the other 277 are refused with a typed reason each rather than unprocessed.",
    ),
    "ASCRIBES_TO_DEVATA": PredicateSemantics(
        "is derived from the deity",
        "This ascription descriptor is morphologically derived from that deity's name.",
        "A grammatical fact, not a reading: aagneyam is the vrddhi taddhita of agni under "
        "Panini 4.2.24 sasya devata. 47 of 324 descriptors resolve; the other 277 keep "
        "their descriptor form and a typed reason, and are NOT silently absent.",
    ),
    "HAS_DEVATA_DERIVED": PredicateSemantics(
        "is dedicated by resolved ascription",
        "The Atharvavedic index dedicates this passage's hymn to that deity.",
        "Separate from HAS_DEVATA on purpose: HAS_DEVATA is the Rigvedic Anukramani naming "
        "a deity directly, this is the Atharvavedic apparatus naming an adjective that a "
        "morphological derivation resolves. Every edge is CONTAINER_INHERITED at SUKTA_WIDE "
        "scope -- the index states a deity for the hymn, and no Atharvavedic verse is "
        "ascribed differently from its sukta. The resolution being exact does not make the "
        "scope per-verse; read `ascription_resolution_*` for that axis.",
    ),
    "BELONGS_TO_FAMILY": PredicateSemantics(
        "belongs to the seer family",
        "This seer is assigned to that family.",
        "Assigned by vrddhi patronymic derivation from the seer's name, which is a "
        "linguistic derivation and not a genealogical record.",
    ),
    "CO_OCCURS_WITH": PredicateSemantics(
        "co-occurs with",
        "The two deities are named together more often than the corpus baseline.",
        "A lift figure over passage co-occurrence. It says nothing about a dual divinity or "
        "a shared cult; read `lift` against the baseline the edge records.",
    ),
    "DEVATA_ASSOCIATED_WITH": PredicateSemantics(
        "is associated with",
        "The deity is associated with this entity by the enrichment layer.",
        "An association derived from co-occurrence in the corpus, not a statement that the "
        "tradition makes this deity the god of that thing.",
    ),
    "HAS_AXIS": PredicateSemantics(
        "holds the functional axis",
        "The corpus treats this deity in this functional role.",
        "An axis is read off what the corpus does with a deity. SOLAR on Surya says the "
        "corpus treats Surya as a solar body, not that Surya is 'the sun god' in a later "
        "systematised theology.",
    ),
    "HAS_EPITHET": PredicateSemantics(
        "is called",
        "This epithet is applied to the deity.",
        "Thirteen curated epithets, which is not the corpus's epithet vocabulary.",
    ),
    "EPITHET_VARIANT_OF": PredicateSemantics(
        "is an epithet variant of",
        "The two deity labels are forms of one name.",
        "A curation judgement over registry labels, with eleven edges behind it.",
    ),
    "MEMBER_OF": PredicateSemantics(
        "is a member of",
        "The deity belongs to this named group.",
        "Two groups are modelled, which is not the corpus's set of divine collectives.",
    ),
    "COMPOSED_OF": PredicateSemantics(
        "is composed of",
        "This composite deity is made of the named deities.",
        "Composition as the registry records it -- a dual or a collective naming its "
        "members -- not a theogony.",
    ),
    "TREATS": PredicateSemantics(
        "treats",
        "The passage is directed at this condition.",
        "Derived from the passage's own mentions, so it records that the verse names the "
        "affliction, not that it works. AFFLICTION, THREAT and PATHOGEN are different "
        "kinds and the condition's own `condition_kind` says which.",
    ),
    "PROTECTS_FROM": PredicateSemantics(
        "protects from",
        "The passage is directed against this condition or concern.",
        "Derived from mentions; it does not distinguish a charm against a disease from one "
        "against a demon.",
    ),
    "ADDRESSES_CONCERN": PredicateSemantics(
        "addresses the concern",
        "The passage addresses this human concern.",
        "Seven concerns are modelled, which is not a taxonomy of Vedic anxiety.",
    ),
    "USED_FOR_RITE": PredicateSemantics(
        "is used for the rite",
        "The passage is associated with this social rite.",
        "Five rites are modelled, and the association is derived from mentions rather than "
        "from a ritual manual.",
    ),
    "DESCRIBED_IN": PredicateSemantics(
        "is described in",
        "This rite or role is described in the passage.",
        "A curated pointer for the modelled rites, not a concordance.",
    ),
    "BROADER_THAN": PredicateSemantics(
        "is broader than",
        "The first concept subsumes the second in the registry hierarchy.",
        "A registry curation over 229 entities, not a Vedic taxonomy.",
    ),
    "PERFORMS_ACTION": PredicateSemantics(
        "performs the action",
        "The deity appears as the grammatical agent of this action.",
        "An aggregate over the 2,406 morphology-rule assertions, which come from the "
        "Rigveda-only lemma annotation: all 441 edges are Rigvedic. A deity absent here is "
        "absent from that annotation, not from Vedic action.",
    ),
    "IS_ASKED_TO": PredicateSemantics(
        "is asked to",
        "The deity appears as the addressee of an imperative for this action.",
        "Same Rigveda-only morphology layer as PERFORMS_ACTION, with 224 edges.",
    ),
    "HAS_SEMANTIC_ASSERTION": PredicateSemantics(
        "carries the semantic assertion",
        "This passage carries a reified assertion about who does what.",
        "One label over five derivations of unequal strength that must not be summed: "
        "28,370 and 2,406 derived by rule from the Sanskrit annotation, 1,532 from the "
        "treebank dependency layer, 364 projected from a letter-identical Rigvedic verse "
        "rather than annotated in their own corpus, and 2,459 extracted unreviewed by a "
        "model from an English translation. The layer reaches all four corpora unevenly "
        "-- RV 27,057, AV 6,167, YV 1,543, SV 364 -- and none of it is human-reviewed. "
        "This said 'All 4,865 are Rigvedic', which was true of an earlier state of the "
        "layer and is now false in both halves. Read the assertion's own `derivation` "
        "before using it.",
    ),
    "USES_OBJECT": PredicateSemantics(
        "uses the object",
        "The rite uses this object.",
        "Curated for the modelled rites only.",
    ),
    "USES_SUBSTANCE": PredicateSemantics(
        "uses the substance",
        "The rite uses this substance.",
        "Curated for the modelled rites only.",
    ),
    "USES_OFFERING": PredicateSemantics(
        "uses the offering",
        "The rite uses this offering.",
        "Curated for the modelled rites only.",
    ),
    "RECEIVES_OFFERING": PredicateSemantics(
        "receives the offering",
        "The deity is named as the recipient of this offering.",
        "Four edges, on 3 of the 103 modelled rites. Each carries its cited verse loci, so "
        "an edge can be checked; the layer is too sparse to support a count over deities.",
    ),
    "INVOKES_DEVATA": PredicateSemantics(
        "invokes the deity",
        "The rite invokes this deity.",
        "Curated for the modelled rites only.",
    ),
    "PERFORMED_BY": PredicateSemantics(
        "is performed by",
        "This ritual role performs the rite.",
        "Eleven roles are modelled, which is not the Vedic priesthood.",
    ),
    "PERFORMED_FOR": PredicateSemantics(
        "is performed for",
        "The rite is performed for this purpose.",
        "A curated purpose, not a statement of what participants believed.",
    ),
    "HAS_STEP": PredicateSemantics(
        "has the step",
        "This action is a step of the rite, in the Samhita text's own numbering.",
        "Three steps exist across the whole layer, all on the soma pressing, so a rite "
        "without them is unmodelled rather than stepless. The sutra-attested procedure is a "
        "separate predicate, HAS_RITUAL_STEP, and the two must not be added together.",
    ),
    "HAS_RITUAL_STEP": PredicateSemantics(
        "has the procedural step",
        "A Srautasutra or Grhyasutra prints this step as part of the rite.",
        "Not the Samhita's own numbering -- that is HAS_STEP, and the two are never summed. "
        "Each source work numbers its own sequence from 1, so these edges do not compose "
        "into one procedure, and most state a position without printing the run it falls "
        "in. Read /api/v1/rituals/{id}, which returns them grouped by source work.",
    ),
    "ATTESTED_IN": PredicateSemantics(
        "is attested in",
        "The registry records this passage as an attestation of the entity.",
        "An attestation locator taken from the entity registry, not a re-reading of the "
        "passage. Absence means the registry recorded no example, not that the passage "
        "does not name the entity.",
    ),
    "SCHOLARLY_CLAIM_ABOUT": PredicateSemantics(
        "is a scholarly claim about",
        "A named scholar's recorded position concerns this passage.",
        "A position held, not a finding accepted. The graph records that someone argued it "
        "and where; it takes no view on whether they were right, and a passage with several "
        "of these has a disagreement rather than an answer.",
    ),
    "SHARES_FORMULA_WITH": PredicateSemantics(
        "shares a formula with",
        "Both mantras contain the same registered formula.",
        "Derived from the formula layer rather than stated by any source: nothing in a text "
        "says these two are related. A shared formula is a shared phrase, which is weaker "
        "than a parallel and much weaker than textual reuse.",
    ),
    "SPECIALIZED_FORM_OF": PredicateSemantics(
        "is a specialized form of",
        "This deity name is a narrower form of the broader one.",
        "Narrower than the broader name, not an alias for it: unlike EPITHET_VARIANT_OF it "
        "does not assert the two are the same referent under two names.",
    ),
    "INVOKES": PredicateSemantics(
        "invokes",
        "A model reading of the passage found it invoking this target.",
        "Model-extracted from an English translation and adjudicated by a second model. "
        "MODEL_ADJUDICATED is the strongest review state anywhere in this graph; nothing "
        "in it is human-reviewed.",
    ),
    "DESCRIBES": PredicateSemantics(
        "describes",
        "A model reading of the passage found it describing this target.",
        "Model-extracted and model-adjudicated. A plausible-sounding reason is not a "
        "checked one, and the edge records whether the reviewer was shown the Sanskrit.",
    ),
    "REQUESTS": PredicateSemantics(
        "requests",
        "A model reading found the passage requesting this.",
        "Model-extracted and model-adjudicated, over a translation.",
    ),
    "PRAISES": PredicateSemantics(
        "praises",
        "A model reading found the passage praising this target.",
        "Model-extracted and model-adjudicated, over a translation.",
    ),
    "DESCRIBES_ACTION": PredicateSemantics(
        "describes the action",
        "A model reading found the passage describing this action.",
        "Model-extracted and model-adjudicated, over a translation.",
    ),
    "HAS_THEME": PredicateSemantics(
        "has the theme",
        "A model reading assigned this theme to the passage.",
        "Eight edges, model-extracted. Not a thematic index of the corpus.",
    ),
    "CONTRASTS_WITH": PredicateSemantics(
        "contrasts with",
        "A model reading found the passage setting these in contrast.",
        "Eight edges, model-extracted over a translation.",
    ),
    "INVOLVES_OFFERING": PredicateSemantics(
        "involves the offering",
        "A model reading found the passage involving this offering.",
        "Eleven edges, model-extracted over a translation.",
    ),
    "INVOLVES_RITUAL": PredicateSemantics(
        "involves the ritual",
        "A model reading found the passage involving this rite.",
        "Nine edges, model-extracted over a translation.",
    ),
    "INVOLVES_SUBSTANCE": PredicateSemantics(
        "involves the substance",
        "A model reading found the passage involving this substance.",
        "Three edges. A single confidence value across three edges is a sample size, not a "
        "measurement.",
    ),
    "REFERS_TO_NATURAL_PHENOMENON": PredicateSemantics(
        "refers to the natural phenomenon",
        "A model reading found the passage referring to this phenomenon.",
        "Five edges, model-extracted over a translation.",
    ),
    "REFERS_TO_PLACE": PredicateSemantics(
        "refers to the place",
        "A model reading found the passage referring to this place.",
        "One edge. It is an example of the layer, not a finding about the corpus.",
    ),
    "MEASURES": PredicateSemantics(
        "measures",
        "This derived metric was computed over that subject.",
        "A statistic this repository computed, not something the corpus says.",
    ),
    "CONCERNS": PredicateSemantics(
        "concerns",
        "This interpretive claim is about that subject.",
        "A claim from secondary scholarship, attributed to its source, and not a statement "
        "of the corpus.",
    ),
    "SUPPORTED_BY": PredicateSemantics(
        "is supported by",
        "This interpretive claim cites that passage.",
        "The citation is the scholar's, and its adequacy is not assessed here.",
    ),
    "SUPPORTED_BY_STATISTIC": PredicateSemantics(
        "is supported by the statistic",
        "This interpretive claim cites that derived metric.",
        "Six edges. The metric was computed by this repository, so the claim and its "
        "support are not independent of each other.",
    ),
    "CONTRADICTS": PredicateSemantics(
        "contradicts",
        "These two interpretive claims disagree.",
        "Two edges, recording a disagreement between scholars rather than adjudicating it.",
    ),
    LEMMA_RELATIONSHIP: PredicateSemantics(
        "names the lemma",
        "The passage contains a token of this lemma.",
        "From the Rigveda-only manual morphological annotation. This whole layer is marked "
        "internal because 39 deity lemmas were surfacing in product traversal looking like "
        "deities while carrying none of a deity's profile.",
    ),
}

#: What every response says about review, because the honest answer is uniform across the
#: graph and a client must not have to infer it from a null.
#: The population sentence is built from the measured figures rather than typed. "ten
#: predicates" was wrong -- MODEL_ADJUDICATED spans twelve -- and the same paragraph in
#: three other modules had drifted in three different directions.
NO_HUMAN_REVIEW_CAVEAT: Final = (
    layer_figures.adjudication_disclosure()
    + " Everything else carries either UNREVIEWED or no review "
    "record at all, and those two are different: the second means the layer never had a "
    "review step, not that a reviewer passed it."
)

#: Plain-language review states. A null is the common case and gets the sentence that says
#: so, rather than being rendered as though a reviewer had looked and shrugged.
_REVIEW_STATUS_TEXT: Final[dict[str, str]] = {
    "MODEL_ADJUDICATED": "A model re-read the passage and accepted this edge with a stated "
    "reason. This is the strongest review state in this graph and it is not human review.",
    "UNREVIEWED": "This layer has a review step and this edge has not been through it.",
}
_NO_REVIEW_RECORD: Final = (
    "This layer records no review at all, which is not the same as having been reviewed and passed."
)


def _snake_upper(value: str) -> str:
    """CamelCase to UPPER_SNAKE, for a display type this module's map does not know.

    A fallback and not the primary path: :data:`PRODUCT_TYPE_BY_DISPLAY_TYPE` covers all 42
    display types the live graph carries and a test asserts it still does. This exists so
    that a rebuild introducing a 43rd returns a plausible product type rather than raising
    inside a request handler, while the test fails and names it.
    """
    out: list[str] = []
    for index, char in enumerate(value):
        if char.isupper() and index and not value[index - 1].isupper():
            out.append("_")
        out.append(char.upper())
    return "".join(out)


# ---------------------------------------------------------------------------
# Cypher
# ---------------------------------------------------------------------------


def _resolution_clause(variable: str, parameter: str) -> str:
    """A ``CALL`` union that resolves one client-supplied id to at most one node.

    One branch per resolvable kind, each a point lookup on a label and a property this
    module owns -- nothing a client sends is interpolated. Labels go through
    :func:`validated_label` even though they are ours, because a whitelist that is checked
    only when it is untrusted is a whitelist that stops being checked.

    Written as a union of narrow lookups rather than the obvious
    ``MATCH (n) WHERE n.canonical_key = $id OR n.entity_key = $id ...``, which was measured:
    that form is an all-node scan -- over 108,779 nodes when this was measured, on the
    Product-V1 graph -- with a disjunction the planner cannot
    index, and it did not finish inside a two-minute probe. This form is 9-17 ms.
    """
    branches = [
        f"MATCH ({variable}:{validated_label(kind.label)} "
        f"{{{kind.property}: ${parameter}}}) RETURN {variable}"
        for kind in RESOLVABLE_KINDS
    ]
    branches.append(
        f"MATCH ({variable}:SemanticAssertion) "
        f"WHERE {variable}.assertion_id = ${parameter} "
        f"RETURN {variable}"
    )
    branches.append(
        f"WITH ${parameter} AS public_id "
        f"WHERE public_id STARTS WITH '{ASSERTION_PREFIX}' "
        f"MATCH ({variable}:SemanticAssertion) "
        f"WHERE {variable}.assertion_key = substring(public_id, {len(ASSERTION_PREFIX)}) "
        f"AND {variable}.assertion_id IS NULL RETURN {variable}"
    )
    return "CALL () {\n  " + "\n  UNION ".join(branches) + "\n}"


_RESOLVE_ROOT: Final = (
    _resolution_clause("n", "node_id")
    + """
WITH n LIMIT 2
RETURN n AS node, labels(n) AS node_labels, properties(n) AS node_properties
"""
)


def _neighbourhood_depth1_cypher(types: tuple[str, ...]) -> str:
    """Depth-1 fan-out, per-type limited, with the untruncated group size returned.

    ``group_total`` is the whole point of the shape: the batch is sliced to
    ``limit_per_type`` and the client is told how many edges the slice came from, so 50 of
    Indra's 3,566 deity mentions cannot be mistaken for all of them.

    The ``$allow_lemma`` guard is a bound parameter and not a constant exception in the
    query text. ``:Internal`` marks four different things -- ``TextVersion``,
    ``Translation``, ``Source`` and ``Lemma`` -- so "exclude internal" is a coarser
    instrument than it looks, and the flag has to be able to admit exactly one of them.
    Today no traversable predicate reaches a lemma unless ``MENTIONS_LEMMA`` is in the type
    list, so the guard is belt to the whitelist's braces; a predicate added later that did
    reach one would be caught by it rather than leaking.
    """
    pattern = "|".join(types)
    return (
        _resolution_clause("root", "node_id")
        + f"""
WITH root LIMIT 1
MATCH (root)-[r:{pattern}]-(neighbour)
WHERE NOT neighbour:Internal OR ($allow_lemma AND neighbour:Lemma)
WITH root, type(r) AS relationship_type, (startNode(r) = root) AS outgoing,
     count(*) AS group_total, collect({{rel: r, node: neighbour}})[0..$limit] AS batch
UNWIND batch AS item
WITH relationship_type, outgoing, group_total, item.rel AS rel, item.node AS node
RETURN relationship_type, outgoing, group_total,
       properties(rel) AS rel_properties,
       properties(node) AS node_properties, labels(node) AS node_labels
LIMIT $node_budget
"""
    )


def _neighbourhood_depth2_cypher(types: tuple[str, ...]) -> str:
    """One bounded step out from the depth-1 frontier.

    Hub nodes are dropped from the frontier before expanding rather than after, which is
    the difference between 74 ms and 870 ms: an untyped ``COUNT { (f)--() }`` is an O(1)
    read from the degree store, and expanding *triṣṭubh* would pull 4,195 edges for a
    depth-2 view that has a 300-edge budget anyway.
    """
    pattern = "|".join(types)
    return (
        _resolution_clause("root", "node_id")
        + f"""
WITH root LIMIT 1
MATCH (root)-[r:{pattern}]-(neighbour)
WHERE NOT neighbour:Internal OR ($allow_lemma AND neighbour:Lemma)
WITH root, type(r) AS rt, (startNode(r) = root) AS outgoing,
     collect(neighbour)[0..$limit] AS batch
UNWIND batch AS frontier_node
WITH root, collect(DISTINCT frontier_node)[0..$frontier_cap] AS frontier
WITH root, frontier,
     size([f IN frontier WHERE COUNT {{ (f)--() }} > $hub_ceiling]) AS hub_skipped,
     [f IN frontier WHERE COUNT {{ (f)--() }} <= $hub_ceiling] AS expandable
UNWIND expandable AS f
MATCH (f)-[r2:{pattern}]-(g)
WHERE (NOT g:Internal OR ($allow_lemma AND g:Lemma)) AND g <> root AND NOT g IN frontier
WITH hub_skipped, type(r2) AS relationship_type,
     collect(DISTINCT {{rel: r2, near: f, far: g}})[0..$limit] AS batch2
UNWIND batch2 AS item
WITH hub_skipped, relationship_type, item.rel AS rel, item.near AS near, item.far AS far
RETURN hub_skipped, relationship_type,
       properties(rel) AS rel_properties,
       startNode(rel) = near AS near_is_source,
       properties(near) AS near_properties, labels(near) AS near_labels,
       properties(far) AS far_properties, labels(far) AS far_labels
LIMIT $edge_budget
"""
    )


def _relationship_lookup_cypher(token: RelationshipToken) -> str:
    """Look one edge up from a decoded token, entirely by bound parameter.

    The relationship type is the only interpolated value and it has already been through
    :func:`validated_relationship_types` against a whitelist this module owns. The domain id
    and the endpoint ids travel bound, so the injection payloads in the test suite --
    ``HAS_RISHI]->() DETACH DELETE n //`` and ``FOO`` -- are refused at decode time and
    never reach a query at all.
    """
    if token.basis is RelationshipIdBasis.DOMAIN_ID:
        property_name = DOMAIN_ID_PROPERTY_BY_TYPE.get(token.relationship_type)
        if property_name is None:
            raise BadRequestError(
                "That relationship id claims a domain identifier for a predicate that "
                "does not issue one."
            )
        match = (
            f"MATCH (source)-[rel:{token.relationship_type}]->(target)\n"
            f"WHERE rel.{property_name} = $domain_id"
        )
    else:
        match = (
            f"MATCH (source)-[rel:{token.relationship_type}]->(target)\n"
            "WHERE " + _stable_id_expression("source") + " = $source_id\n"
            "  AND " + _stable_id_expression("target") + " = $target_id"
        )
    return (
        match
        + """
RETURN properties(rel) AS rel_properties,
       properties(source) AS source_properties, labels(source) AS source_labels,
       properties(target) AS target_properties, labels(target) AS target_labels
LIMIT 2
"""
    )


def _stable_id_expression(variable: str) -> str:
    """The same public identity expression used by the offline exporter."""
    return public_id_cypher(variable)


def _path_cypher(types: tuple[str, ...], max_depth: int) -> str:
    """Least-hub-mediated route among the shortest routes, with a hard candidate cap.

    ``max_depth`` is interpolated as an integer this module computed from a bounded query
    parameter, because Cypher will not accept a parameter inside a variable-length bound.
    The route search itself is a subquery with ``LIMIT``, so the number of candidate paths
    scored is capped whatever the pair's connectivity looks like.

    The ordering is the hub penalty: ``worst_waypoint_degree`` is the largest degree of any
    node strictly between the endpoints, and taking the minimum picks the most distinctive
    of the equally short routes. The endpoints themselves are excluded from that score --
    a client that asks about Indra is not to be told Indra is too popular to discuss.
    """
    pattern = "|".join(types)
    return (
        _resolution_clause("source", "source_id")
        + _resolution_clause("target", "target_id")
        + f"""
WITH source, target LIMIT 1
CALL (source, target) {{
  MATCH candidate = allShortestPaths((source)-[:{pattern}*1..{max_depth}]-(target))
  RETURN candidate
  LIMIT $candidate_limit
}}
WITH candidate,
     reduce(worst = 0, w IN nodes(candidate)[1..-1] |
       CASE WHEN COUNT {{ (w)--() }} > worst THEN COUNT {{ (w)--() }} ELSE worst END)
       AS worst_waypoint_degree
ORDER BY worst_waypoint_degree ASC, length(candidate) ASC
LIMIT 1
RETURN worst_waypoint_degree, length(candidate) AS hop_count,
       [x IN nodes(candidate) | properties(x)] AS node_properties,
       [x IN nodes(candidate) | labels(x)] AS node_labels,
       [x IN nodes(candidate) | COUNT {{ (x)--() }}] AS node_degrees,
       [y IN relationships(candidate) | properties(y)] AS rel_properties,
       [y IN relationships(candidate) | type(y)] AS rel_types,
       [y IN relationships(candidate) | {_stable_id_expression("startNode(y)")}]
         AS rel_source_ids
"""
    )


_EVIDENCE_PASSAGE_CYPHER: Final = """
MATCH (p:Passage) WHERE p.canonical_key IN $keys
RETURN properties(p) AS node_properties, labels(p) AS node_labels
LIMIT $limit
"""

#: What a node carries that this endpoint does not traverse. Run ONLY when the traversable
#: fan-out came back empty, so it costs nothing on the hot path, and it is what turns a
#: dead-end response into an actionable one: 1,888 Passages and 2 of the 4 Works have zero
#: traversable edges because their whole connectivity is ``CONTAINS``, and telling a client
#: "nothing here" without telling it where the 74 contained passages went is a worse answer
#: than the truth.
#:
#: ``$excluded_types`` is bound and deliberately does NOT include ``QA_ISSUE_ON``. Naming
#: that predicate with a count would disclose how many doubts this repository's build holds
#: about this node, which is build state and not Vedic knowledge -- the one exclusion whose
#: reason a client may not be told.
_EXCLUDED_DEGREE_CYPHER: Final = (
    _resolution_clause("n", "node_id")
    + """
WITH n LIMIT 1
MATCH (n)-[r]-()
WHERE type(r) IN $excluded_types
RETURN type(r) AS relationship_type, count(*) AS edges
ORDER BY edges DESC
LIMIT 12
"""
)

#: The excluded predicates a client may be told about, in the order the caveat lists them.
#: Derived from :data:`NON_TRAVERSABLE_REASONS` minus the QA predicate rather than retyped,
#: so a predicate added to the exclusions is disclosed automatically and the QA one stays
#: out by construction.
DISCLOSABLE_EXCLUDED_TYPES: Final[tuple[str, ...]] = tuple(
    sorted(set(NON_TRAVERSABLE_REASONS) - {"QA_ISSUE_ON"})
)


# ---------------------------------------------------------------------------
# Projection
# ---------------------------------------------------------------------------


def stable_id(properties: dict[str, Any]) -> str | None:
    """The shared publication contract, never the assertion's passage context."""
    return public_id(properties)


def product_type(properties: dict[str, Any], labels: list[str]) -> str:
    """A product type name for a node, never a raw Neo4j label.

    Reads the graph's own ``display_type``, which every non-internal node carries and which
    is more precise than the label set where it matters: a ``:Passage`` is a ``MANTRA``, a
    ``HYMN``, a ``SECTION`` or a ``STRUCTURAL_CONTAINER``, and a frontend that cannot tell a
    verse from a book renders both the same.
    """
    display_type = properties.get("display_type")
    if isinstance(display_type, str) and display_type:
        mapped = PRODUCT_TYPE_BY_DISPLAY_TYPE.get(display_type)
        return mapped if mapped is not None else _snake_upper(display_type)
    for label in labels:
        mapped = PRODUCT_TYPE_BY_DISPLAY_TYPE.get(label)
        if mapped is not None:
            return mapped
    return "UNTYPED"


def _node_metadata(properties: dict[str, Any]) -> dict[str, Any]:
    """Whitelisted, bounded metadata. Never build state, never an essay."""
    metadata: dict[str, Any] = {}
    for key in sorted(NODE_METADATA_KEYS & properties.keys()):
        value = properties[key]
        if value is None:
            continue
        if key in JSON_METADATA_KEYS:
            parsed = parse_json_property(value)
            if parsed is not None:
                metadata[key] = parsed
            continue
        if isinstance(value, str) and len(value) > METADATA_STRING_LIMIT:
            metadata[key] = value[:METADATA_STRING_LIMIT]
            continue
        metadata[key] = value
    return metadata


def node_view(properties: dict[str, Any], labels: list[str]) -> GraphNodeView:
    """Project one node, including whether a devata-slot entry is actually a deity.

    ``id`` falls back to nothing: a node without a stable id is a defect, and returning an
    empty id is better than returning a storage address.

    ``is_deity`` is tri-state and the third state is load-bearing. It is ``None`` for every
    node not in the Anukramani's devata slot, because "is this metre a god?" is not a
    question with a false answer -- it is a question that does not apply, and returning
    ``false`` for 20,000 mantras would convert a typed absence into a negative claim.

    The flag comes from :func:`~vedagraph.api.services.deity_population.subject_disclosure`,
    which returns it together with the caveat owed when it is false, so this surface cannot
    take the flag and forget the disclosure. That coupling is the whole point: the same
    defect -- a non-deity served as a deity -- has now been found on five separate routes,
    every time because a second surface re-implemented half of a contract.
    """
    node_id = stable_id(properties)
    label = properties.get("display_label")
    is_deity: bool | None = None
    if LABEL_DEVATA in labels:
        # The ruling, carried on the node. Deriving it from ``structure`` here made a graph
        # node's is_deity flag disagree with the deity routes' own gate on 29 nodes.
        is_deity, _ = subject_disclosure(
            DevataSubject(
                structure=_as_optional_str(properties.get("structure")),
                is_deity=properties.get("is_deity") is True,
                non_deity_kind=_as_optional_str(properties.get("non_deity_kind")),
            )
        )
    return GraphNodeView(
        id=node_id or "",
        type=product_type(properties, labels),
        label=str(label) if label else (node_id or ""),
        # text_iast last, and only reached by nodes that carry no curated description:
        # a :RitualStep IS its sutra, so projecting the locator as the label and nothing as
        # the description showed a reader a citation with no content behind it.
        description=_first_string(
            properties, ("short_description", "definition", "scope_note", "text_iast")
        ),
        is_deity=is_deity,
        metadata=_node_metadata(properties),
    )


def non_deity_subject_caveats(nodes: Sequence[GraphNodeView]) -> list[CaveatView]:
    """The disclosure owed when a payload carries a devata-slot entry that is not a god.

    Two parts, and the split is deliberate. The NOT-A-DEITY text itself comes only from
    :func:`~vedagraph.api.services.deity_population.subject_disclosure` -- one producer, so
    the wording cannot drift between the deity routes and this one -- and it is emitted
    once per distinct Anukramani structure rather than once per node, because three copies
    of one paragraph is noise a reader stops reading.

    The second part is this surface's own, and it is why a caveat alone is not sufficient
    here. A neighbourhood returns up to 400 nodes; a payload-level sentence saying "one of
    these is not a deity" cannot tell a reader *which* one. So the affected subjects are
    named from the nodes actually returned, and every node also carries its own
    ``is_deity`` flag for a client reading the graph rather than the prose.
    """
    offenders = [node for node in nodes if node.is_deity is False]
    if not offenders:
        return []
    caveats: list[CaveatView] = []
    seen: set[str] = set()
    for node in offenders:
        structure = str(node.metadata.get("structure") or "UNSPECIFIED")
        kind = node.metadata.get("non_deity_kind")
        key = f"{structure}|{kind}"
        if key in seen:
            continue
        seen.add(key)
        caveats.extend(
            subject_disclosure(
                DevataSubject(
                    structure=structure,
                    is_deity=False,
                    non_deity_kind=str(kind) if kind else None,
                )
            )[1]
        )
    named = ", ".join(f"{node.label} ({node.id})" for node in offenders[:8])
    more = "" if len(offenders) <= 8 else f", and {len(offenders) - 8:,} more"
    count = len(offenders)
    lead = (
        f"1 of the {len(nodes):,} nodes in this payload is a devata-slot entry that is NOT a deity"
        if count == 1
        else f"{count:,} of the {len(nodes):,} nodes in this payload are devata-slot "
        "entries that are NOT deities"
    )
    caveats.append(
        CaveatView(
            text=(
                f"{lead}: "
                f"{named}{more}. This endpoint has no `population` parameter -- it is a "
                "general graph explorer and resolves whatever id it is given -- so such a "
                "subject appears here because it is genuinely connected to what was asked "
                "for, not because a parameter admitted it. It carries type DEVATA because "
                "the frozen graph labels it :Devata and every other deity surface in this "
                "API says the same, so read each node's `is_deity` flag rather than its "
                "`type` before rendering one as a god."
            ),
            source="deity_population_contract",
        )
    )
    return caveats


def _first_string(properties: dict[str, Any], names: tuple[str, ...]) -> str | None:
    for name in names:
        value = properties.get(name)
        if isinstance(value, str) and value.strip():
            return value
    return None


def evidence_spans(properties: dict[str, Any]) -> list[EvidenceSpanView]:
    """Parse the edge's ``evidence`` blob into quoted witnesses.

    Most layers store a JSON array of ``{locator, quote, surface}``; the vocabulary-overlap
    layer stores a bare list of entity keys instead. Both are handled, and a blob that
    parses to neither yields no spans rather than raising -- one malformed property should
    degrade one field, which is the rule ``parse_json_property`` already sets.
    """
    parsed = parse_json_property(properties.get("evidence"))
    if not isinstance(parsed, list):
        return []
    spans: list[EvidenceSpanView] = []
    for entry in parsed[:MAX_EVIDENCE_SPANS]:
        if isinstance(entry, str):
            spans.append(EvidenceSpanView(citation=entry, surface="shared_entity_key"))
            continue
        if not isinstance(entry, dict):
            continue
        locator = entry.get("locator")
        quote = entry.get("quote")
        surface = entry.get("surface")
        spans.append(
            EvidenceSpanView(
                passage_key=str(locator) if isinstance(locator, str) else None,
                citation=str(locator) if isinstance(locator, str) else None,
                veda=_veda_from_key(locator) if isinstance(locator, str) else None,
                quote=str(quote) if isinstance(quote, str) else None,
                surface=str(surface) if isinstance(surface, str) else None,
            )
        )
    return spans


def _veda_from_key(canonical_key: str) -> str | None:
    """The corpus code out of a canonical key, e.g. ``VG:RV:SAK:M01:S001:V001`` -> ``RV``."""
    parts = canonical_key.split(":")
    if len(parts) > 2 and parts[0] == "VG" and parts[1] in {"RV", "SV", "YV", "AV"}:
        return parts[1]
    return None


def _evidence_basis(value: Any) -> EvidenceBasis:
    """Map the edge's ``trust`` onto the API's basis vocabulary.

    ``trust`` and not ``evidence_basis``: the graph's ``evidence_basis`` records which
    *surface* the evidence came from (``SANSKRIT``, ``TRANSLATION``, ``STRUCTURAL``,
    ``SOURCE_METADATA``, ``MIXED``, ``SHARED_REGISTRY_ENTITIES``), which is not the same
    axis as how the claim was reached, and :class:`EvidenceBasis` is the second axis.
    Unknown values fall to ``UNKNOWN`` rather than to the nearest-looking member.
    """
    mapping = {
        "SOURCE_EXPLICIT": EvidenceBasis.SOURCE_STATED,
        "DETERMINISTIC_DERIVED": EvidenceBasis.DETERMINISTIC_DERIVED,
        "DERIVED": EvidenceBasis.DETERMINISTIC_DERIVED,
        "LLM_EXTRACTED": EvidenceBasis.MODEL_EXTRACTION,
    }
    if isinstance(value, str):
        return mapping.get(value, EvidenceBasis.UNKNOWN)
    return EvidenceBasis.UNKNOWN


def attribution_basis(properties: dict[str, Any]) -> EvidenceBasis:
    """The evidence basis for one edge, through the shared contract and not a second copy.

    The attribution axis is type-level, three mechanisms in this repository have written it
    and disagreed, and the rule that came out of that is to apply **one** contract last. So
    ``attribution_precision`` is read by
    :func:`~vedagraph.api.models.common.basis_from_attribution_precision`, which owns the
    mapping and whose value space is asserted complete against the live graph, rather than
    by a table here that would be free to drift from it.

    The trust fallback is a refinement of that contract and not a competitor: it applies
    only where the shared mapping returns ``UNKNOWN``, which is the 105,855 edges whose
    ``attribution_precision`` is ``NOT_AN_ATTRIBUTION`` -- a parallel, a formula occurrence,
    a family membership, where "did the source say this of this verse?" is not a well-formed
    question. For those, how the claim arose is what ``trust`` records, and reporting
    ``UNKNOWN`` for a deterministically derived parallel would be throwing information away.
    """
    basis = basis_from_attribution_precision(
        _as_optional_str(properties.get("attribution_precision"))
    )
    if basis is not EvidenceBasis.UNKNOWN:
        return basis
    return _evidence_basis(properties.get("trust"))


def attribution_precision(properties: dict[str, Any]) -> AttributionPrecision:
    """Read the graph's ``attribution_precision`` into its own enum.

    Returned beside the derived basis rather than instead of it, because the two answer
    different questions and ``EvidenceView`` now carries both. An unrecognised value becomes
    ``UNKNOWN`` rather than raising -- ``REGISTRY_STATED`` was found live on 6 edges and was
    never a member of the enum -- and the value space is asserted complete elsewhere, so a
    new value fails a test rather than a request.
    """
    value = _as_optional_str(properties.get("attribution_precision"))
    if value is None:
        return AttributionPrecision.UNKNOWN
    try:
        return AttributionPrecision(value)
    except ValueError:
        return AttributionPrecision.UNKNOWN


def _as_optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _confidence(
    relationship_type: str, properties: dict[str, Any]
) -> tuple[ConfidenceBasis, float | None, float | None]:
    """Split the ``confidence`` property into a basis, a confidence and a pipeline prior.

    Returns ``(basis, confidence, pipeline_prior)`` with at most one of the two numbers
    set. A predicate in :data:`PIPELINE_CONSTANT_PREDICATES` never returns a confidence,
    however tempting the number looks, because it is the same number on every edge of that
    predicate and reporting it as a confidence is how a reader comes to believe a filter
    raised precision.
    """
    # Three fields, because GAP-QUALITY-003 split one into three. `confidence` survives only
    # where the value genuinely varies; `source_explicit_tier_marker` carries the constant
    # 1.0 of the seven source-explicit predicates; `uncalibrated_pipeline_score` carries the
    # 0.85 and 0.75 of the two predicates that were constant because they are tiny. Reading
    # only `confidence` made the last of those UNREACHABLE through the API -- the edge went
    # from reporting VARIES_WITHIN_PREDICATE with its value to reporting nothing at all,
    # which is information the product used to publish disappearing rather than being
    # relabelled. Agent B's M19.
    raw = properties.get("confidence")
    if raw is None:
        raw = properties.get("source_explicit_tier_marker")
    if raw is None:
        raw = properties.get("uncalibrated_pipeline_score")
    value = float(raw) if isinstance(raw, (int, float)) else None
    if relationship_type in PIPELINE_CONSTANT_PREDICATES:
        return (
            ConfidenceBasis.PIPELINE_CONSTANT,
            None,
            value if value is not None else PIPELINE_CONSTANT_PREDICATES[relationship_type],
        )
    if properties.get("uncalibrated_pipeline_score") is not None:
        # Constant on a 3-edge and a 1-edge population: a sample size, not a tier. Reported
        # as a prior rather than a confidence, for the same reason as the seven.
        return (ConfidenceBasis.PIPELINE_CONSTANT, None, value)
    if value is None:
        return ConfidenceBasis.ABSENT, None, None
    return ConfidenceBasis.VARIES_WITHIN_PREDICATE, value, None


def _semantics(relationship_type: str) -> PredicateSemantics:
    """The predicate's explanation, or an honest placeholder.

    A missing entry does not raise. A 500 inside a request handler is a worse outcome than
    a sentence saying the product has no curated explanation for this predicate, and the
    live test that asserts full coverage of the traversable set turns the gap into a failing
    test instead of a failing request.
    """
    known = PREDICATE_SEMANTICS.get(relationship_type)
    if known is not None:
        return known
    readable = relationship_type.replace("_", " ").lower()
    return PredicateSemantics(
        phrase=readable,
        asserts=f"The graph records a {readable} relationship between these two.",
        limit="This API carries no curated explanation for this predicate, so what the "
        "edge does and does not establish is not stated here. Treat it as unexplained "
        "rather than as unqualified.",
    )


def layer_method(properties: dict[str, Any]) -> str | None:
    """The layer's method, from whichever of the three property names it used.

    ``methods`` is parsed rather than stringified because the frozen graph is inconsistent
    about it: some layers store a JSON string and others a native list, under one property
    name. Returning the raw value would hand a client ``'["minhash-char4","lcs"]'`` on one
    edge and a readable list on the next.
    """
    method = properties.get("method")
    if isinstance(method, str) and method:
        return method
    methods = parse_json_property(properties.get("methods"))
    if isinstance(methods, list) and methods:
        return ", ".join(str(entry) for entry in methods[:4])
    if isinstance(methods, str) and methods:
        return methods
    strongest = properties.get("strongest_method")
    return str(strongest) if isinstance(strongest, str) and strongest else None


def _review_status(properties: dict[str, Any]) -> str:
    state = properties.get("review_state")
    if isinstance(state, str) and state:
        return _REVIEW_STATUS_TEXT.get(state, f"Review state recorded as {state}.")
    return _NO_REVIEW_RECORD


def _score(properties: dict[str, Any]) -> float | None:
    for name in ("similarity", "distinctiveness", "lift", "score"):
        value = properties.get(name)
        if isinstance(value, (int, float)):
            return float(value)
    return None


def _edge_caveat(relationship_type: str, properties: dict[str, Any]) -> CaveatView | None:
    """The one thing a reader of *this* edge must not conclude.

    Assembled from the edge's own recorded properties, never from a figure typed into a
    sentence. Where an edge carries a property that weakens it -- an inherited attribution,
    an ambiguous referent, a transitive family membership, a translation-only witness -- that
    property is what produces the caveat, so an edge without the weakness does not carry the
    warning and an edge with it always does.
    """
    notes: list[str] = []
    precision = properties.get("attribution_precision")
    if precision == "CONTAINER_INHERITED":
        notes.append(
            "This attribution is CONTAINER_INHERITED: the source stated it of the "
            "containing hymn and a scope rule projected it onto this passage. It is not a "
            "statement the passage itself makes."
        )
    certainty = properties.get("referent_certainty")
    if certainty == "DEITY_AMBIGUOUS":
        notes.append(
            "referent_certainty is DEITY_AMBIGUOUS: the matched form is also an ordinary "
            "noun, so this passage may mean fire rather than Agni, the pressed drink rather "
            "than Soma, the sun rather than Surya."
        )
    if properties.get("theonym_ambiguous"):
        notes.append(
            "theonym_ambiguous: this entity was reached through an alias that is also a "
            "deity name, so the edge may be recording a mention of the god instead."
        )
    if properties.get("containment_is_transitive"):
        notes.append(
            "This membership reaches the family's representative wording only transitively, "
            "through another member, so this formula and the representative may share no "
            "words at all."
        )
    if properties.get("has_containment_support") is False:
        notes.append(
            "This membership has no containment support: it rests on string resemblance "
            "alone, which is the only part of the family layer that is an inference rather "
            "than a checkable containment fact."
        )
    if properties.get("evidence_basis") == "TRANSLATION":
        notes.append(
            "The only witness for this edge is a 19th-century English translation, so it "
            "inherits that translator's reading of the Sanskrit."
        )
    if properties.get("derived_from_mention"):
        notes.append(
            "Derived from the passage's own mentions: it records that the verse names the "
            "thing, not that the verse achieves anything about it."
        )
    if properties.get("state") == "CANDIDATE":
        notes.append(
            "state is CANDIDATE: this edge was not accepted into the deterministic layer "
            "and is offered for inspection rather than as a settled fact."
        )
    if relationship_type in PIPELINE_CONSTANT_PREDICATES:
        notes.append(
            f"confidence on {relationship_type} is a pipeline constant, identical on all "
            f"{relationship_type} edges, so it is returned as pipeline_prior and not as a "
            "confidence."
        )
    if not notes:
        return None
    return CaveatView(text=" ".join(notes), source="measured")


def edge_view(
    *,
    relationship_type: str,
    properties: dict[str, Any],
    source_id: str,
    target_id: str,
    direction: TraversalDirection | None = None,
    include_spans: bool = False,
) -> GraphEdgeView:
    """Project one relationship, id and grade and caveat included."""
    semantics = _semantics(relationship_type)
    basis, confidence, prior = _confidence(relationship_type, properties)
    domain_property = DOMAIN_ID_PROPERTY_BY_TYPE.get(relationship_type)
    domain_id = properties.get(domain_property) if domain_property else None
    token, id_basis = encode_relationship_id(
        relationship_type=relationship_type,
        domain_id=str(domain_id) if isinstance(domain_id, str) and domain_id else None,
        source_id=source_id,
        target_id=target_id,
    )
    tier = properties.get("quality_tier")
    derivation = properties.get("derivation")
    return GraphEdgeView(
        id=token,
        id_basis=id_basis,
        source=source_id,
        target=target_id,
        type=relationship_type,
        label=semantics.phrase,
        direction=direction,
        evidence=EvidenceView(
            method=layer_method(properties),
            tier=str(tier) if isinstance(tier, str) else None,
            evidence_basis=attribution_basis(properties),
            surface=evidence_surface(_as_optional_str(properties.get("evidence_basis"))),
            attribution_precision=attribution_precision(properties),
            review_state=(
                str(properties["review_state"])
                if isinstance(properties.get("review_state"), str)
                else None
            ),
            confidence=confidence,
            spans=evidence_spans(properties) if include_spans else [],
            derivation=str(derivation) if isinstance(derivation, str) else None,
        ),
        confidence_basis=basis,
        pipeline_prior=prior,
        score=_score(properties),
        caveat=_edge_caveat(relationship_type, properties),
    )


# ---------------------------------------------------------------------------
# The service
# ---------------------------------------------------------------------------


class GraphService:
    """Neighbourhoods, relationship explanations and whitelisted paths.

    Every method here bounds its own result before the repository sees it: a page limit, a
    per-type fan-out limit, a node budget, a path candidate cap and a depth ceiling. That
    is not defensive style, it is the requirement -- a request must not be able to make this
    server enumerate the whole edge set -- 265,295 edges when this was measured, on the
    Product-V1 graph -- and the enumeration is genuinely reachable. A
    two-hop expansion from Indra with no frontier cap touches 6,539 edges at the first step
    alone.
    """

    def __init__(self, repository: Neo4jRepository) -> None:
        self._repository = repository

    # -- resolution --------------------------------------------------------------

    def resolve_node(self, node_id: str) -> tuple[dict[str, Any], list[str]]:
        """Resolve a client-supplied product id to one node, or raise a useful 404.

        ``LIMIT 2`` and not ``LIMIT 1``: an id matching two kinds is a genuine ambiguity and
        the client has to be told, not silently handed whichever branch the planner
        evaluated first. Nothing in the frozen graph is ambiguous today, and a rebuild that
        made two id spaces overlap would surface here as a 400 rather than as a
        neighbourhood of the wrong thing.
        """
        rows = self._repository.run(_RESOLVE_ROOT, node_id=node_id)
        if not rows:
            raise EntityNotFoundError(
                f"No knowledge object has the id {node_id!r}.",
                hint="Ids look like VG:DEVATA:INDRAH (deity), VG:RV:SAK:M01:S001:V001 "
                "(passage), VG:CONCEPT:SOMA-DRINK (entity), "
                "VG:ENRICH:FORMULA:<hash> (formula) or "
                "VG:ENRICH:FORMULA-FAMILY:<hash> (formula family). Use GET "
                "/api/v1/search to find one.",
            )
        if len(rows) > 1:
            raise BadRequestError(
                f"The id {node_id!r} matches more than one kind of knowledge object.",
                hint="This is a defect in the graph's id spaces, not in your request. "
                "Please report it.",
            )
        row = rows[0]
        properties: dict[str, Any] = dict(row["node_properties"])
        labels: list[str] = list(row["node_labels"])
        return properties, labels

    # -- neighbourhood (spec section 24) -----------------------------------------

    def neighbourhood(
        self,
        node_id: str,
        *,
        depth: int,
        requested_types: tuple[str, ...] | None,
        trust_tier: str | None,
        min_confidence: float | None,
        include_internal: bool,
        limit_per_type: int,
    ) -> NeighbourhoodView:
        """The bounded local graph around one node.

        ``requested_types`` goes through :func:`validated_relationship_types` against
        :data:`TRAVERSABLE_RELATIONSHIPS`, so an unknown or hostile type name is a 400
        naming the offending value rather than an empty graph -- "no such predicate" and
        "that predicate has no edges here" are different answers.

        ``trust_tier`` and ``min_confidence`` are applied in Python, after the bounded fetch,
        and that ordering is deliberate: filtering inside the fan-out query would silently
        change what ``group_total`` counts, and then a truncation figure meant to say "50 of
        3,566" would be reporting the size of the filtered set instead.
        """
        # Parameters are validated BEFORE the node is resolved, so that "that is not a
        # traversable predicate" is a 400 whether or not the node exists. The other order
        # makes the status code depend on data the client cannot see: an injected type
        # against an unknown id would come back 404, which reads as "the id was the
        # problem" and hides the fact that the type was refused at all.
        types = self._traversable_types(requested_types, include_internal=include_internal)
        limit = min(limit_per_type, MAX_NEIGHBOURS_PER_TYPE)
        properties, labels = self.resolve_node(node_id)
        root = node_view(properties, labels)

        nodes: dict[str, GraphNodeView] = {root.id: root}
        edges: list[GraphEdgeView] = []
        truncated: set[str] = set()
        total_degree = 0

        rows = self._repository.run(
            _neighbourhood_depth1_cypher(types),
            node_id=node_id,
            limit=limit,
            node_budget=NEIGHBOURHOOD_NODE_BUDGET,
            allow_lemma=include_internal,
        )
        seen_groups: set[tuple[str, bool]] = set()
        for row in rows:
            relationship_type = str(row["relationship_type"])
            outgoing = bool(row["outgoing"])
            group = (relationship_type, outgoing)
            if group not in seen_groups:
                seen_groups.add(group)
                total_degree += int(row["group_total"])
                if int(row["group_total"]) > limit:
                    truncated.add(relationship_type)
            edge_properties: dict[str, Any] = dict(row["rel_properties"])
            if not self._passes_filters(
                relationship_type, edge_properties, trust_tier, min_confidence
            ):
                continue
            neighbour = node_view(dict(row["node_properties"]), list(row["node_labels"]))
            if not neighbour.id:
                continue
            nodes.setdefault(neighbour.id, neighbour)
            edges.append(
                edge_view(
                    relationship_type=relationship_type,
                    properties=edge_properties,
                    source_id=root.id if outgoing else neighbour.id,
                    target_id=neighbour.id if outgoing else root.id,
                    direction=(
                        TraversalDirection.OUTBOUND if outgoing else TraversalDirection.INBOUND
                    ),
                )
            )

        hub_skipped = 0
        if depth >= 2:
            hub_skipped = self._expand_depth2(
                node_id=node_id,
                types=types,
                limit=limit,
                nodes=nodes,
                edges=edges,
                trust_tier=trust_tier,
                min_confidence=min_confidence,
                allow_lemma=include_internal,
            )

        return NeighbourhoodView(
            root=root,
            nodes=list(nodes.values()),
            edges=edges,
            bounds=NeighbourhoodBounds(
                depth=depth,
                limit_per_type=limit,
                node_budget=NEIGHBOURHOOD_NODE_BUDGET,
                returned_nodes=len(nodes),
                returned_edges=len(edges),
                total_degree=total_degree,
                truncated_types=sorted(truncated),
                hub_expansions_skipped=hub_skipped,
            ),
            # PARTIAL and never INSUFFICIENT_EVIDENCE for an empty neighbourhood. See
            # `_empty_neighbourhood_caveat`: an empty fan-out here is always a statement
            # about scope -- mine or the client's -- and never about evidence.
            data_status=(KnowledgeStatus.SUPPORTED if edges else KnowledgeStatus.PARTIAL),
            caveats=self._neighbourhood_caveats(
                root=root,
                nodes=list(nodes.values()),
                node_id=node_id,
                total_degree=total_degree,
                returned_edges=len(edges),
                truncated=sorted(truncated),
                min_confidence=min_confidence,
                trust_tier=trust_tier,
                include_internal=include_internal,
                narrowed_by_types=bool(requested_types),
            ),
        )

    def _expand_depth2(
        self,
        *,
        node_id: str,
        types: tuple[str, ...],
        limit: int,
        nodes: dict[str, GraphNodeView],
        edges: list[GraphEdgeView],
        trust_tier: str | None,
        min_confidence: float | None,
        allow_lemma: bool,
    ) -> int:
        rows = self._repository.run(
            _neighbourhood_depth2_cypher(types),
            node_id=node_id,
            limit=limit,
            frontier_cap=NEIGHBOURHOOD_NODE_BUDGET,
            hub_ceiling=HUB_DEGREE_CEILING,
            edge_budget=NEIGHBOURHOOD_DEPTH2_EDGE_BUDGET,
            allow_lemma=allow_lemma,
        )
        hub_skipped = 0
        for row in rows:
            hub_skipped = int(row["hub_skipped"])
            if len(nodes) >= NEIGHBOURHOOD_NODE_BUDGET:
                break
            relationship_type = str(row["relationship_type"])
            edge_properties: dict[str, Any] = dict(row["rel_properties"])
            if not self._passes_filters(
                relationship_type, edge_properties, trust_tier, min_confidence
            ):
                continue
            near = node_view(dict(row["near_properties"]), list(row["near_labels"]))
            far = node_view(dict(row["far_properties"]), list(row["far_labels"]))
            if not near.id or not far.id:
                continue
            nodes.setdefault(near.id, near)
            nodes.setdefault(far.id, far)
            near_is_source = bool(row["near_is_source"])
            edges.append(
                edge_view(
                    relationship_type=relationship_type,
                    properties=edge_properties,
                    source_id=near.id if near_is_source else far.id,
                    target_id=far.id if near_is_source else near.id,
                )
            )
        return hub_skipped

    def _traversable_types(
        self, requested: tuple[str, ...] | None, *, include_internal: bool
    ) -> tuple[str, ...]:
        """The predicates this traversal will follow, validated and never client-authored.

        ``include_internal`` can add exactly one predicate, and the reason it can add no
        more is structural: measured over the live graph, none of the 57 traversable
        predicates has an endpoint labelled ``Internal``, ``QAIssue``, ``TextVersion``,
        ``Translation``, ``Source`` or ``SourceArtifact``. So there is no parameter value
        that admits a QA finding, and the flag's whole effect is to let ``MENTIONS_LEMMA``
        through to the 10,031 lemma nodes.
        """
        allowed = TRAVERSABLE_RELATIONSHIPS
        if include_internal:
            allowed = allowed | {LEMMA_RELATIONSHIP}
        if requested:
            return validated_relationship_types(requested, allowed)
        return tuple(sorted(allowed))

    def _passes_filters(
        self,
        relationship_type: str,
        properties: dict[str, Any],
        trust_tier: str | None,
        min_confidence: float | None,
    ) -> bool:
        """Apply ``trust_tier`` and ``min_confidence``, the latter only where it can mean
        anything.

        A ``min_confidence`` threshold is **not** applied to a predicate whose confidence is
        a pipeline constant. Applying it there would be worse than useless: the filter would
        either keep every ``HAS_RISHI`` edge or drop all 17,889 of them on the strength of a
        number that is 1.0 by construction, and a caller who set 0.9 to raise precision
        would read the survivors as the good ones. Those edges are kept and disclosed
        instead, which is what :data:`CONFIDENCE_FILTER_CAVEAT` tells the client happened.
        """
        if trust_tier is not None and properties.get("quality_tier") != trust_tier:
            return False
        if min_confidence is None:
            return True
        if relationship_type in PIPELINE_CONSTANT_PREDICATES:
            return True
        raw = properties.get("confidence")
        if not isinstance(raw, (int, float)):
            return True
        return float(raw) >= min_confidence

    def _neighbourhood_caveats(
        self,
        *,
        root: GraphNodeView,
        nodes: Sequence[GraphNodeView],
        node_id: str,
        total_degree: int,
        returned_edges: int,
        truncated: list[str],
        min_confidence: float | None,
        trust_tier: str | None,
        include_internal: bool,
        narrowed_by_types: bool,
    ) -> list[CaveatView]:
        # The non-deity disclosure goes FIRST. A reader who stops after one caveat must not
        # stop before the one saying the subject of this graph is a dog.
        caveats: list[CaveatView] = non_deity_subject_caveats(nodes)
        if truncated:
            caveats.append(
                CaveatView(
                    text=(
                        f"This is a bounded view, not {root.label}'s whole neighbourhood. "
                        f"{returned_edges} edges are shown out of {total_degree} the node "
                        f"carries over traversable predicates, and the fan-out of "
                        f"{', '.join(truncated)} was cut by limit_per_type. Do not read "
                        f"the shape of this graph as the shape of {root.label}'s "
                        "connections."
                    ),
                    source="measured",
                )
            )
        if min_confidence is not None:
            caveats.append(CaveatView(text=CONFIDENCE_FILTER_CAVEAT, source="measured"))
        if trust_tier is not None:
            caveats.append(
                CaveatView(
                    text=(
                        f"Filtered to quality_tier = {trust_tier}. Tier records how a claim "
                        "was reached and not how likely it is to be right: TIER_B is a "
                        "reproducible derivation and TIER_C means a model adjudicated it, "
                        "so a tier filter selects a mechanism rather than a confidence "
                        "level. Edges of predicates that carry no tier are excluded by this "
                        "filter, which is not evidence that they do not exist."
                    ),
                    source="measured",
                )
            )
        if include_internal:
            caveats.append(
                CaveatView(
                    text=(
                        "include_internal=true added the lexical layer: MENTIONS_LEMMA "
                        "edges to Lemma nodes, which are marked internal because 39 deity "
                        "lemmas were surfacing in product traversal looking like deities "
                        "while carrying none of a deity's profile. It admits nothing else, "
                        "and no parameter value admits a QA finding or any other internal "
                        "node."
                    ),
                    source="measured",
                )
            )
        if returned_edges == 0:
            caveats.append(
                self._empty_neighbourhood_caveat(
                    root=root,
                    node_id=node_id,
                    total_degree=total_degree,
                    narrowed=(
                        narrowed_by_types or trust_tier is not None or min_confidence is not None
                    ),
                )
            )
        caveats.append(CaveatView(text=NO_HUMAN_REVIEW_CAVEAT, source="measured"))
        return caveats

    def _empty_neighbourhood_caveat(
        self, *, root: GraphNodeView, node_id: str, total_degree: int, narrowed: bool
    ) -> CaveatView:
        """Why this neighbourhood is empty, told apart into its two causes.

        **Why the status beside this is PARTIAL and not INSUFFICIENT_EVIDENCE.** That status
        means "evidence exists and cannot support the claim", and no empty neighbourhood is
        an evidence question: the graph knows exactly which edges this node has, and the
        emptiness is always a scope fact. Either the client narrowed the scope with
        ``types``, ``trust_tier`` or ``min_confidence``, or *this endpoint* narrowed it by
        excluding the containment tree, the stored text surfaces, the lexical layer and the
        assertion wiring. Spending a status that means "we could not establish this" on "you
        asked for TIER_A TREATS edges on a deity that has none" devalues the vocabulary
        everywhere else in the product, which is the same reasoning that took it off a page
        emptied by its offset.

        Paging is not a cause here and could not be: this endpoint has no ``offset``, and
        ``limit_per_type`` is bounded ``ge=1``, so no value a client can send empties the
        collection.

        **The second cause is common, and the response has to be useful about it.**
        Measured, 2,884 resolvable nodes carry zero traversable edges: 1,888 Passages -- the
        structural containers and hymns, such as a whole Atharvaveda kanda -- 993 derived
        metrics, one action predicate, and 2 of the 4 Works. For those the whole
        connectivity is ``CONTAINS``, which this endpoint does not traverse, so "no edges"
        without saying where they went would be true and useless. The excluded degree is
        therefore measured and named, and the client is pointed at the endpoints that do
        traverse it.
        """
        if narrowed and total_degree:
            # The requested predicates DO have edges here, so `trust_tier` or
            # `min_confidence` removed them and relaxing those is the useful advice.
            return CaveatView(
                text=(
                    f"No edge survived the grading filters in this request for {root.label}. "
                    "That is a statement about the filter combination, not about the corpus: "
                    f"over the predicates you requested this node carries {total_degree:,} "
                    "traversable edges, and `trust_tier` or `min_confidence` excluded all of "
                    "them. Relax those before reading this as an absence."
                ),
                source="measured",
            )
        if narrowed:
            # Degree zero over the requested predicates, so no grading filter can be at
            # fault and telling the client to relax one would send them in a circle.
            return CaveatView(
                text=(
                    f"{root.label} carries no edge of any predicate you requested. That is a "
                    "statement about the predicates in this request and not about the "
                    "corpus; widen or drop `types` to see what the node does carry."
                ),
                source="measured",
            )
        excluded = self._excluded_degree(node_id)
        if excluded:
            breakdown = ", ".join(f"{name} ({count:,})" for name, count in excluded.items())
            return CaveatView(
                text=(
                    f"{root.label} carries no edge of any kind this endpoint traverses, and "
                    "that is about this endpoint's scope rather than about the corpus. It "
                    f"does carry {sum(excluded.values()):,} edges of excluded kinds: "
                    f"{breakdown}. Those are the corpus's own structure and its stored text "
                    "surfaces rather than knowledge claims about it, which is why a "
                    "knowledge traversal does not follow them -- use the passage navigation "
                    "and reading endpoints to reach them."
                ),
                source="measured",
            )
        return CaveatView(
            text=(
                f"{root.label} carries no relationship of any kind in this graph, "
                "traversable or otherwise. That is a fact about how this node was built and "
                "not a statement that the corpus relates it to nothing."
            ),
            source="measured",
        )

    def _excluded_degree(self, node_id: str) -> dict[str, int]:
        """This node's degree over the predicates this endpoint refuses to traverse.

        Only reached when the traversable fan-out is empty, so the extra round trip is paid
        by the responses that need it and by no others. ``QA_ISSUE_ON`` is absent from the
        bound type list, so a node's QA findings cannot be counted into a number a client
        sees: how many doubts the build holds about a passage is build state.
        """
        rows = self._repository.run(
            _EXCLUDED_DEGREE_CYPHER,
            node_id=node_id,
            excluded_types=list(DISCLOSABLE_EXCLUDED_TYPES),
        )
        return {str(row["relationship_type"]): int(row["edges"]) for row in rows}

    # -- explanation (spec section 25) --------------------------------------------

    def explain_relationship(self, relationship_id: str) -> RelationshipExplanation:
        """Why the graph believes two things are connected.

        The token is decoded before anything touches the database, so a malformed id, a
        token from another scheme, and an injection payload dressed as a relationship type
        are all 400s with no query run. A well-formed token for an edge that no longer
        exists is a 404, which is the honest answer after a rebuild dropped it.
        """
        token = decode_relationship_id(
            relationship_id,
            allowed_types=TRAVERSABLE_RELATIONSHIPS | {LEMMA_RELATIONSHIP},
        )
        parameters: dict[str, Any] = {}
        if token.basis is RelationshipIdBasis.DOMAIN_ID:
            parameters["domain_id"] = token.domain_id
        else:
            parameters["source_id"] = token.source_id
            parameters["target_id"] = token.target_id
        rows = self._repository.run(_relationship_lookup_cypher(token), **parameters)
        if not rows:
            raise NotFoundError(
                "No relationship with that id exists in this graph.",
                hint="Relationship ids are stable across a rebuild only as far as the "
                "underlying data is; an edge the build no longer produces has no "
                "explanation. Re-read the neighbourhood to get current ids.",
            )
        row = rows[0]
        edge_properties: dict[str, Any] = dict(row["rel_properties"])
        source = node_view(dict(row["source_properties"]), list(row["source_labels"]))
        target = node_view(dict(row["target_properties"]), list(row["target_labels"]))
        edge = edge_view(
            relationship_type=token.relationship_type,
            properties=edge_properties,
            source_id=source.id,
            target_id=target.id,
            include_spans=True,
        )
        semantics = _semantics(token.relationship_type)
        # Order is contractual, not cosmetic, and it is the same on all three graph
        # surfaces: the non-deity disclosure first, then this edge's own weakness, then the
        # review statement. A reader who stops after one caveat must not stop before the
        # one saying the subject is a dog -- which is what an `insert(0, ...)` for the edge
        # caveat did here until a test caught it.
        caveats = [
            *non_deity_subject_caveats([source, target]),
            *([edge.caveat] if edge.caveat is not None else []),
            CaveatView(text=NO_HUMAN_REVIEW_CAVEAT, source="measured"),
        ]
        return RelationshipExplanation(
            relationship=edge,
            source=source,
            target=target,
            why=self._why(semantics, source, target, edge_properties),
            method=edge.evidence.method,
            trust_tier=edge.evidence.tier,
            derivation=edge.evidence.derivation,
            review_status=_review_status(edge_properties),
            evidence_passages=self._evidence_passages(edge),
            data_status=KnowledgeStatus.SUPPORTED,
            caveats=caveats,
        )

    def _why(
        self,
        semantics: PredicateSemantics,
        source: GraphNodeView,
        target: GraphNodeView,
        properties: dict[str, Any],
    ) -> str:
        """The explanation sentence, assembled from this edge's own recorded properties.

        Deliberately built by concatenating a fixed template with measured values pulled
        off the edge, and never by formatting a number someone typed. Where a property that
        matters is absent the clause is absent too, so the sentence is short rather than
        confidently wrong.
        """
        parts = [f"{source.label} {semantics.phrase} {target.label}.", semantics.asserts]
        detail = self._measured_detail(properties)
        if detail:
            parts.append(detail)
        parts.append(f"What it does not establish: {semantics.limit}")
        return " ".join(parts)

    def _measured_detail(self, properties: dict[str, Any]) -> str:
        """Per-edge specifics, each one read off a property rather than assumed."""
        clauses: list[str] = []
        role = properties.get("role")
        if isinstance(role, str):
            clauses.append(f"Its role in the family is {role}")
        match_level = properties.get("match_level")
        if isinstance(match_level, str) and match_level:
            clauses.append(f"the surface they were compared on is {match_level}")
        certainty = properties.get("referent_certainty")
        if isinstance(certainty, str):
            clauses.append(f"the referent is graded {certainty}")
        extraction = properties.get("extraction_path")
        if isinstance(extraction, str):
            clauses.append(f"the mention was found by {extraction}")
        forms = properties.get("matched_forms") or properties.get("matched_aliases")
        if isinstance(forms, list) and forms:
            shown = ", ".join(str(form) for form in forms[:4])
            clauses.append(f"the matched form was {shown}")
        source_form = properties.get("source_form")
        if isinstance(source_form, str) and source_form:
            clauses.append(f"the wording in the passage is {source_form}")
        shared = properties.get("shared_entities")
        distinctiveness = properties.get("distinctiveness")
        if isinstance(shared, int) and isinstance(distinctiveness, (int, float)):
            clauses.append(
                f"they share {shared} registry entities with a distinctiveness of "
                f"{round(float(distinctiveness), 2)}"
            )
        lift = properties.get("lift")
        baseline = properties.get("baseline_mantras")
        if isinstance(lift, (int, float)) and isinstance(baseline, int):
            clauses.append(
                f"they co-occur at {round(float(lift), 2)} times the rate a baseline of "
                f"{baseline} mantras would predict"
            )
        roots = properties.get("roots")
        if isinstance(roots, list) and roots:
            clauses.append(f"the verbal roots behind it are {', '.join(str(r) for r in roots[:4])}")
        reason = properties.get("review_reason")
        if isinstance(reason, str) and reason:
            clauses.append(f"the adjudicating model's stated reason was: {reason}")
        occurrences = properties.get("occurrences")
        if isinstance(occurrences, int) and occurrences > 1:
            clauses.append(f"the form occurs {occurrences} times in the passage")
        surface = properties.get("evidence_basis")
        if isinstance(surface, str) and surface:
            if surface == "TRANSLATION":
                clauses.append(
                    "the only surface it was read off is a 19th-century English translation"
                )
            else:
                clauses.append(f"the surface it was read off is {surface}")
        # `veda_pair` is null on all 325 same-Veda parallel edges, so it is derived from the
        # two endpoints' own corpus codes rather than read: filtering or reporting on the
        # stored property alone drops every intra-Rigvedic parallel.
        subject_veda = properties.get("subject_veda")
        object_veda = properties.get("object_veda")
        if isinstance(subject_veda, str) and isinstance(object_veda, str):
            clauses.append(f"the corpora involved are {subject_veda} and {object_veda}")
        scope_origin = properties.get("scope_origin")
        if isinstance(scope_origin, str) and scope_origin:
            clauses.append(f"the scope rule that produced it is {scope_origin}")
        grade_basis = properties.get("grade_basis")
        if isinstance(grade_basis, str) and grade_basis:
            clauses.append(f"its tier rests on {grade_basis}")
        asserts = properties.get("asserts")
        if isinstance(asserts, str) and asserts:
            clauses.append(f"the layer states it as: {asserts}")
        if not clauses:
            return ""
        joined = "; ".join(clauses)
        # Only the first character, never ``str.capitalize``: that lowercases the rest, and
        # the rest is full of values that mean something in upper case -- CORE,
        # DEITY_AMBIGUOUS, SANDHI_INSENSITIVE, SUKTA_WIDE.
        return joined[0].upper() + joined[1:] + "."

    def _evidence_passages(self, edge: GraphEdgeView) -> list[GraphNodeView]:
        """Resolve the locators in the edge's evidence blob to passage nodes.

        Bounded by the span cap, and tolerant: a locator that resolves to nothing is
        dropped, because an evidence block naming a passage the graph no longer has is a
        data defect and not a reason to fail the request.
        """
        keys = [span.passage_key for span in edge.evidence.spans if span.passage_key]
        if not keys:
            return []
        rows = self._repository.run(
            _EVIDENCE_PASSAGE_CYPHER,
            keys=keys[:MAX_EVIDENCE_SPANS],
            limit=MAX_EVIDENCE_SPANS,
        )
        return [node_view(dict(row["node_properties"]), list(row["node_labels"])) for row in rows]

    # -- path (spec section 26) ---------------------------------------------------

    def find_path(self, source_id: str, target_id: str, *, max_depth: int) -> PathView:
        """The least hub-mediated of the shortest whitelisted routes between two nodes.

        Both endpoints are resolved first, separately, so an unknown one produces a 404 that
        names *which* id was not found rather than an empty path a reader would take for
        "unconnected".
        """
        source_properties, source_labels = self.resolve_node(source_id)
        target_properties, target_labels = self.resolve_node(target_id)
        source = node_view(source_properties, source_labels)
        target = node_view(target_properties, target_labels)
        depth = max(1, min(max_depth, PATH_MAX_DEPTH))

        if source.id == target.id:
            return PathView(
                source=source,
                target=target,
                length=0,
                hops=[],
                max_depth_searched=depth,
                data_status=KnowledgeStatus.SUPPORTED,
                caveats=[
                    *non_deity_subject_caveats([source]),
                    CaveatView(
                        text="The two ids name the same node, so there is no path to explain.",
                        source="measured",
                    ),
                ],
            )

        types = tuple(sorted(PATH_RELATIONSHIPS))
        rows = self._repository.run(
            _path_cypher(validated_relationship_types(types, PATH_RELATIONSHIPS), depth),
            source_id=source_id,
            target_id=target_id,
            candidate_limit=PATH_CANDIDATE_LIMIT,
        )
        if not rows:
            return PathView(
                source=source,
                target=target,
                length=0,
                hops=[],
                max_depth_searched=depth,
                data_status=KnowledgeStatus.INSUFFICIENT_EVIDENCE,
                caveats=[
                    *non_deity_subject_caveats([source, target]),
                    CaveatView(
                        text=(
                            f"No route of {depth} hops or fewer joins these two over the "
                            f"{len(types)} predicates this endpoint traverses. That is a "
                            "statement about this bounded search, not about the corpus: a "
                            "longer route may exist, and the excluded predicates -- the "
                            "containment tree, the stored text surfaces, the lexical layer "
                            "and the assertion wiring -- connect almost everything to "
                            "almost everything and are excluded for exactly that reason."
                        ),
                        source="measured",
                    ),
                    CaveatView(text=NO_HUMAN_REVIEW_CAVEAT, source="measured"),
                ],
            )

        row = rows[0]
        return self._path_view(
            row=row,
            source=source,
            target=target,
            depth=depth,
            predicate_count=len(types),
        )

    def _path_view(
        self,
        *,
        row: dict[str, Any],
        source: GraphNodeView,
        target: GraphNodeView,
        depth: int,
        predicate_count: int,
    ) -> PathView:
        node_properties: list[dict[str, Any]] = [dict(p) for p in row["node_properties"]]
        node_labels: list[list[str]] = [list(labels) for labels in row["node_labels"]]
        rel_properties: list[dict[str, Any]] = [dict(p) for p in row["rel_properties"]]
        rel_types: list[str] = [str(t) for t in row["rel_types"]]
        rel_source_ids: list[str | None] = [
            str(value) if isinstance(value, str) else None for value in row["rel_source_ids"]
        ]
        views = [
            node_view(properties, labels)
            for properties, labels in zip(node_properties, node_labels, strict=True)
        ]
        worst = int(row["worst_waypoint_degree"])
        hops: list[PathHopView] = []
        for index, relationship_type in enumerate(rel_types):
            near, far = views[index], views[index + 1]
            # `rel_source_ids` records which endpoint the stored edge points FROM, which is
            # not always the direction the path walks; a hop rendered the wrong way round
            # would say a verse ascribes a seer to itself.
            forward = rel_source_ids[index] == near.id
            edge = edge_view(
                relationship_type=relationship_type,
                properties=rel_properties[index],
                source_id=near.id if forward else far.id,
                target_id=far.id if forward else near.id,
                include_spans=True,
            )
            semantics = _semantics(relationship_type)
            subject, object_ = (near, far) if forward else (far, near)
            hops.append(
                PathHopView(
                    index=index + 1,
                    source=near,
                    target=far,
                    relationship=edge,
                    explanation=(
                        f"{subject.label} {semantics.phrase} {object_.label}. "
                        f"{semantics.asserts} What it does not establish: {semantics.limit}"
                    ),
                )
            )
        caveats = [
            *non_deity_subject_caveats(views),
            CaveatView(
                text=(
                    "A path is a route, not a claim that the corpus relates these two. Each "
                    "hop's own explanation states what that hop does and does not establish, "
                    "and the route as a whole establishes nothing beyond the conjunction of "
                    f"those {len(hops)} statements. This is the least hub-mediated of the "
                    f"shortest routes found over {predicate_count} predicates within "
                    f"{depth} hops; a longer and more distinctive route may exist and was "
                    "not searched, because searching it is a graph enumeration rather than a "
                    "bounded query."
                ),
                source="measured",
            ),
            CaveatView(text=NO_HUMAN_REVIEW_CAVEAT, source="measured"),
        ]
        if worst > HUB_DEGREE_CEILING:
            # The busiest waypoint is named rather than described, because "a node carrying
            # 4,195 edges" is abstract and "the metre tristubh" is the thing a reader needs
            # to see in order to discount the route.
            degrees: list[int] = [int(value) for value in row["node_degrees"]]
            waypoints = list(zip(views[1:-1], degrees[1:-1], strict=True))
            busiest = max(waypoints, key=lambda pair: pair[1])[0] if waypoints else None
            hub_label = busiest.label if busiest is not None else "an intermediate node"
            caveats.insert(
                0,
                CaveatView(
                    text=(
                        f"HUB-MEDIATED: this route passes through {hub_label}, which "
                        f"carries {worst} edges -- above the measured hub ceiling of "
                        f"{HUB_DEGREE_CEILING}. A connection "
                        "through a node that busy is true of thousands of pairs and does "
                        "not distinguish this one. It is returned labelled rather than "
                        "suppressed, because an empty answer would read as 'unconnected'."
                    ),
                    source="measured",
                ),
            )
        return PathView(
            source=source,
            target=target,
            length=len(hops),
            hops=hops,
            hub_mediated=worst > HUB_DEGREE_CEILING,
            max_depth_searched=depth,
            data_status=KnowledgeStatus.SUPPORTED,
            caveats=caveats,
        )
