"""One reader-facing grade for edges that five layers describe in five vocabularies.

The V1 graph did not lose its provenance. Every layer recorded it carefully -- and each
recorded it in its own words:

===================  ==========================================================
layer                what an edge says about itself
===================  ==========================================================
corpus               nothing (``CONTAINS`` carries only ``sequence``)
knowledge            ``provenance_class``, ``scope_origin``, ``confidence``
lexical              ``provenance_class``, ``annotation_layer_id``
enrichment           ``trust``, ``method``, ``score``, ``evidence``, ``state``
semantic             the enrichment envelope, plus ``model`` and ``prompt_policy``
diagnostic           nothing (``HAS_QA_ISSUE`` carries no properties)
===================  ==========================================================

Each vocabulary is right for its layer, and together they make the one question a reader
actually asks unanswerable: *which of these edges is a source telling me something, and
which is us working something out?* You cannot filter for that, because there is no field
to filter on -- ``trust`` is absent from 49,646 knowledge and lexical edges, and
``provenance_class`` is absent from the enrichment ones. Asking for
``r.trust = 'SOURCE_EXPLICIT'`` silently returns nothing from half the graph.

So this module does not add a sixth vocabulary. It *derives* a single grade from whatever
each edge already says, and the derivation is the whole content of the module:

**Scope inheritance is a derivation, not a source statement.** The Anukramaṇī names a
deity for a *sūkta*. Projecting that label onto each of the sūkta's mantras is what makes
"the mantras of Indra" answerable at all, and it is also not something the Anukramaṇī
said about any of those mantras. 8,329 of 10,558 ``HAS_DEVATA`` edges reach their mantra
that way. They are graded ``TIER_B`` and marked ``CONTAINER_INHERITED``, so a reader who
wants only per-verse attribution can have it -- and a reader who does not ask still sees
a count that is not quietly overstated.

**An unannotated edge is graded, not excused.** ``CONTAINS`` and ``HAS_QA_ISSUE`` say
nothing about themselves. Rather than defaulting them to something flattering, they are
graded from what the layer is known to be, and an edge whose layer is unknown grades
:attr:`~vedagraph.domain.ontology.QualityTier.TIER_D` -- the weakest tier, so an
ungraded edge can never be mistaken for a strong one by accident.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Final

from vedagraph.domain.ontology import (
    KNOWLEDGE_TIER_BY_PROVENANCE,
    PRECISION_BY_SCOPE_ORIGIN,
    TIER_BY_LAYER,
    AttributionPrecision,
    KnowledgeLayer,
    QualityTier,
)


class EvidenceBasis(StrEnum):
    """What an edge's evidence is *about*: the Sanskrit, or a translation of it.

    A dimension distinct from tier, and one whose absence was a real defect. 21,246 of
    47,542 ``ABOUT_CONCEPT`` edges (44.7%) fired on an English word in Griffith 1896 with
    no Sanskrit evidence at all, and they carried exactly the same
    ``DETERMINISTIC_DERIVED`` / ``TIER_B`` grade as an edge matched on the verse itself.
    Both grades are *correct* -- a rule over a stored translation is as reproducible as a
    rule over stored Sanskrit -- which is precisely why tier cannot carry this and a
    separate axis has to. A claim about what Griffith wrote is not a claim about what the
    Rigveda says, and a reader must be able to filter on the difference.
    """

    #: Matched against the Sanskrit of the passage.
    SANSKRIT = "SANSKRIT"
    #: Matched only against a nineteenth-century English translation.
    TRANSLATION = "TRANSLATION"
    #: Both paths fired independently, which is the only genuinely corroborated case.
    MIXED = "MIXED"
    #: The corpus structure itself, or a registry statement: no text was matched.
    STRUCTURAL = "STRUCTURAL"
    #: No method string, or one this function was not taught to read.
    UNSPECIFIED = "UNSPECIFIED"


@dataclass(frozen=True)
class Grade:
    """The unified grade stamped onto one product edge."""

    layer: KnowledgeLayer
    tier: QualityTier
    precision: AttributionPrecision
    #: Why this grade, in a form a reader can check against the edge's own properties.
    basis: str
    evidence_basis: EvidenceBasis = EvidenceBasis.UNSPECIFIED

    def as_edge_properties(self) -> dict[str, str]:
        return {
            "knowledge_layer": str(self.layer),
            "quality_tier": str(self.tier),
            "attribution_precision": str(self.precision),
            "grade_basis": self.basis,
            "evidence_basis": str(self.evidence_basis),
        }


def classify_evidence(method: str) -> EvidenceBasis:
    """Read an edge's ``method`` string for which text its evidence came from.

    The enrichment layer encodes its evidence paths in the method -- for example
    ``concept-alias-v1:english+sanskrit-token`` -- so the information is already stored and
    only needs surfacing.
    """
    if not method:
        return EvidenceBasis.UNSPECIFIED
    lowered = method.lower()
    sanskrit = "sanskrit" in lowered
    english = "english" in lowered or "translation" in lowered
    if sanskrit and english:
        return EvidenceBasis.MIXED
    if sanskrit:
        return EvidenceBasis.SANSKRIT
    if english:
        return EvidenceBasis.TRANSLATION
    if "registry" in lowered:
        return EvidenceBasis.STRUCTURAL
    return EvidenceBasis.UNSPECIFIED


#: ``trust`` values the enrichment envelope uses, mapped to a layer. Kept as strings
#: rather than importing ``TrustClass`` so that a value written by an older pipeline
#: version still grades instead of raising: this module reads the graph as it is, not as
#: the current code would write it.
_LAYER_BY_TRUST: Final[dict[str, KnowledgeLayer]] = {
    "SOURCE_EXPLICIT": KnowledgeLayer.L1_SOURCE_EXPLICIT,
    "DETERMINISTIC_DERIVED": KnowledgeLayer.L2_DETERMINISTIC_DERIVED,
    "LLM_EXTRACTED": KnowledgeLayer.L3_LLM_EXTRACTED,
    "HUMAN_REVIEWED": KnowledgeLayer.L1_SOURCE_EXPLICIT,
    "INTERPRETIVE_CLAIM": KnowledgeLayer.L4_INTERPRETIVE_CLAIM,
}

#: Relationship types produced by the corpus structure itself. These are as source-explicit
#: as anything in the graph -- the edition prints the hymn containing the verse -- and they
#: carry no provenance properties precisely because nothing about them was inferred.
_STRUCTURAL_RELS: Final[frozenset[str]] = frozenset(
    {"CONTAINS", "HAS_TEXT_VERSION", "HAS_TRANSLATION", "EXTRACTED_FROM_CONTAINER"}
)

#: Relationship types that are facts about this repository. Graded so that nothing is
#: ungraded, but they are excluded from product traversal anyway.
_DIAGNOSTIC_RELS: Final[frozenset[str]] = frozenset({"HAS_QA_ISSUE"})

#: Lexical mention edges. The Rigvedic morphology behind them is manual scholarly
#: annotation, but the *entity* attached to a lemma is this project's alias table, so the
#: edge as a whole is a derivation over an annotation rather than a source statement.
_LEXICAL_RELS: Final[frozenset[str]] = frozenset({"MENTIONS_LEMMA", "MENTIONS_ENTITY"})


#: V2 predicates whose tier follows from the predicate itself, because they carry no
#: enrichment envelope of their own. Listed here rather than set by each loader so that the
#: grading table stays the single source of truth: ``stamp_grades`` runs before the domain
#: loaders, so a tier the loader applied only ``ON CREATE`` was silently overwritten on
#: every rebuild and the edge ended up graded by the fall-through default.
#:
#: The split is the claim. ``ADDRESSES_CONCERN`` and ``USED_FOR_RITE`` assert no more than
#: the mention they derive from -- naming what you want is wanting it, and the rite
#: vocabulary occurs nowhere but the occasion -- so they are TIER_B. ``TREATS`` and
#: ``PROTECTS_FROM`` assert a *function*, that the passage acts on the affliction rather
#: than naming it, which is a reading of the charm. Everything curated is TIER_D.
_V2_PREDICATE_GRADE: Final[dict[str, tuple[KnowledgeLayer, QualityTier]]] = {
    # Derived from a deterministic mention plus a curated whitelist.
    "ADDRESSES_CONCERN": (KnowledgeLayer.L2_DETERMINISTIC_DERIVED, QualityTier.TIER_B),
    "USED_FOR_RITE": (KnowledgeLayer.L2_DETERMINISTIC_DERIVED, QualityTier.TIER_B),
    # Structural decomposition of a dual or plural label: follows from its morphology.
    "COMPOSED_OF": (KnowledgeLayer.L2_DETERMINISTIC_DERIVED, QualityTier.TIER_B),
    # Reproducible aggregation over edges that already exist.
    "MEASURES": (KnowledgeLayer.L2_DETERMINISTIC_DERIVED, QualityTier.TIER_B),
    # Asserts a function beyond naming.
    "TREATS": (KnowledgeLayer.L4_INTERPRETIVE_CLAIM, QualityTier.TIER_D),
    "PROTECTS_FROM": (KnowledgeLayer.L4_INTERPRETIVE_CLAIM, QualityTier.TIER_D),
    # Curated deity and ritual structure.
    "HAS_AXIS": (KnowledgeLayer.L4_INTERPRETIVE_CLAIM, QualityTier.TIER_D),
    "HAS_EPITHET": (KnowledgeLayer.L4_INTERPRETIVE_CLAIM, QualityTier.TIER_D),
    "MEMBER_OF": (KnowledgeLayer.L4_INTERPRETIVE_CLAIM, QualityTier.TIER_D),
    "USES_OFFERING": (KnowledgeLayer.L4_INTERPRETIVE_CLAIM, QualityTier.TIER_D),
    "USES_SUBSTANCE": (KnowledgeLayer.L4_INTERPRETIVE_CLAIM, QualityTier.TIER_D),
    "USES_OBJECT": (KnowledgeLayer.L4_INTERPRETIVE_CLAIM, QualityTier.TIER_D),
    "INVOKES_DEVATA": (KnowledgeLayer.L4_INTERPRETIVE_CLAIM, QualityTier.TIER_D),
    "PERFORMED_BY": (KnowledgeLayer.L4_INTERPRETIVE_CLAIM, QualityTier.TIER_D),
    "PERFORMED_FOR": (KnowledgeLayer.L4_INTERPRETIVE_CLAIM, QualityTier.TIER_D),
    "DESCRIBED_IN": (KnowledgeLayer.L4_INTERPRETIVE_CLAIM, QualityTier.TIER_D),
    # The interpretive layer's own edges.
    "SUPPORTED_BY": (KnowledgeLayer.L4_INTERPRETIVE_CLAIM, QualityTier.TIER_D),
    "SUPPORTED_BY_STATISTIC": (KnowledgeLayer.L4_INTERPRETIVE_CLAIM, QualityTier.TIER_D),
    "CONCERNS": (KnowledgeLayer.L4_INTERPRETIVE_CLAIM, QualityTier.TIER_D),
    "CONTRADICTS": (KnowledgeLayer.L4_INTERPRETIVE_CLAIM, QualityTier.TIER_D),
    "ASSERTED_BY": (KnowledgeLayer.L4_INTERPRETIVE_CLAIM, QualityTier.TIER_D),
}


def grade_edge(rel_type: str, properties: Mapping[str, Any]) -> Grade:
    """Derive the unified grade for one edge from whatever it already records.

    Ordered most-specific first. The enrichment envelope is checked before the relationship
    type, because a relationship type can be produced by two layers -- ``MENTIONS_ENTITY``
    is written both by the lexical layer and, in V2, by the domain mention layer with a
    full envelope -- and the envelope is the better witness when both are present.
    """
    evidence = classify_evidence(str(properties.get("method", "")))

    trust = properties.get("trust")
    if isinstance(trust, str) and trust in _LAYER_BY_TRUST:
        layer = _LAYER_BY_TRUST[trust]
        state = str(properties.get("state", ""))
        # A model's proposal that no one has accepted is not the same claim as one that has
        # been. Both stay in L3; the tier separates them, because TIER_C is defined as
        # model-extracted evidence that survived review and a CANDIDATE has not had any.
        if layer is KnowledgeLayer.L3_LLM_EXTRACTED and state != "ACCEPTED":
            return Grade(
                layer=layer,
                tier=QualityTier.TIER_D,
                precision=AttributionPrecision.PER_PASSAGE,
                basis=f"trust={trust}, state={state or 'unset'}: unreviewed model proposal",
                evidence_basis=evidence,
            )
        return Grade(
            layer=layer,
            tier=TIER_BY_LAYER[layer],
            precision=AttributionPrecision.PER_PASSAGE,
            basis=f"trust={trust}",
            evidence_basis=evidence,
        )

    provenance_class = properties.get("provenance_class")
    if isinstance(provenance_class, str) and provenance_class in KNOWLEDGE_TIER_BY_PROVENANCE:
        tier = KNOWLEDGE_TIER_BY_PROVENANCE[provenance_class]
        scope = str(properties.get("scope_origin", ""))
        precision = PRECISION_BY_SCOPE_ORIGIN.get(scope, AttributionPrecision.PER_PASSAGE)
        layer = (
            KnowledgeLayer.L1_SOURCE_EXPLICIT
            if tier is QualityTier.TIER_A
            else KnowledgeLayer.L2_DETERMINISTIC_DERIVED
        )
        detail = f"provenance_class={provenance_class}"
        if scope:
            detail += f", scope_origin={scope}"
        return Grade(
            layer=layer,
            tier=tier,
            precision=precision,
            basis=detail,
            evidence_basis=evidence or EvidenceBasis.STRUCTURAL,
        )

    if rel_type in _STRUCTURAL_RELS:
        return Grade(
            layer=KnowledgeLayer.L1_SOURCE_EXPLICIT,
            tier=QualityTier.TIER_A,
            precision=AttributionPrecision.PER_PASSAGE,
            basis="corpus structure as printed by the edition",
            evidence_basis=EvidenceBasis.STRUCTURAL,
        )

    if rel_type in _LEXICAL_RELS:
        return Grade(
            layer=KnowledgeLayer.L2_DETERMINISTIC_DERIVED,
            tier=QualityTier.TIER_B,
            precision=AttributionPrecision.PER_PASSAGE,
            basis="lexical match over annotated tokens",
            evidence_basis=EvidenceBasis.SANSKRIT,
        )

    v2 = _V2_PREDICATE_GRADE.get(rel_type)
    if v2 is not None:
        layer, tier = v2
        return Grade(
            layer=layer,
            tier=tier,
            precision=AttributionPrecision.PER_PASSAGE,
            basis=f"{rel_type}: tier follows from the predicate (V2 domain layer)",
            evidence_basis=(
                EvidenceBasis.SANSKRIT
                if tier is QualityTier.TIER_B
                else EvidenceBasis.STRUCTURAL
            ),
        )

    if rel_type in _DIAGNOSTIC_RELS:
        return Grade(
            layer=KnowledgeLayer.L2_DETERMINISTIC_DERIVED,
            tier=QualityTier.TIER_B,
            precision=AttributionPrecision.PER_PASSAGE,
            basis="repository self-audit, not a claim about the corpus",
            evidence_basis=EvidenceBasis.STRUCTURAL,
        )

    # Deliberately the weakest tier. An edge nobody taught this function to read must not
    # be able to pass for a strong one by defaulting upward.
    return Grade(
        layer=KnowledgeLayer.L4_INTERPRETIVE_CLAIM,
        tier=QualityTier.TIER_D,
        precision=AttributionPrecision.PER_PASSAGE,
        basis=f"ungraded: {rel_type} records no recognised provenance vocabulary",
        evidence_basis=evidence,
    )


def is_per_passage(properties: Mapping[str, Any]) -> bool:
    """Whether an attribution is about this passage rather than a container it sits in.

    The filter a query wants when it must not overstate: ``HAS_DEVATA`` answers "mantras
    of Indra" with 2,869 rows, of which the large majority arrive by sūkta inheritance.
    """
    scope = str(properties.get("scope_origin", ""))
    if not scope:
        return True
    return (
        PRECISION_BY_SCOPE_ORIGIN.get(scope, AttributionPrecision.PER_PASSAGE)
        is AttributionPrecision.PER_PASSAGE
    )
