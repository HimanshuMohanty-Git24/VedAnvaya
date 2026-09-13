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
diagnostic           nothing (``QA_ISSUE_ON`` carries no properties)
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

**An unannotated edge is graded, not excused.** ``CONTAINS`` and ``QA_ISSUE_ON`` say
nothing about themselves. Rather than defaulting them to something flattering, they are
graded from what the layer is known to be, and an edge whose layer is unknown grades
:attr:`~vedagraph.domain.ontology.QualityTier.TIER_D` -- the weakest tier, so an
ungraded edge can never be mistaken for a strong one by accident.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
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
    #: The corpus structure itself: the edition prints this hymn containing this verse.
    STRUCTURAL = "STRUCTURAL"
    #: A traditional index or registry states it. No text of the passage was matched, and
    #: that is the point: the Anukramaṇī's ascription is a statement *about* the verse by
    #: a later tradition, not a feature of the verse. Split out from ``STRUCTURAL`` in V3,
    #: which had been carrying both and therefore could not distinguish "the edition
    #: prints it this way" from "the index says so".
    SOURCE_METADATA = "SOURCE_METADATA"
    #: A model asserted it without citing any span of text. Distinct from ``TRANSLATION``,
    #: which is what a model citing a translation span rests on: that claim is checkable
    #: against a quote and this one is not.
    MODEL_INTERPRETATION = "MODEL_INTERPRETATION"
    #: No method string, or one this function was not taught to read. **A live
    #: UNSPECIFIED is a defect, not a category.** It stood at 61,861 edges — 25.5% of the
    #: graph, every one of them product knowledge rather than plumbing — because this
    #: function knew four method vocabularies and the pipeline wrote seven.
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


#: Method-string fragments that identify a Sanskrit-derived enrichment path, for methods
#: that do not spell the word "sanskrit".
#:
#: This table is the fix for the largest explainability defect in the V2 graph. The
#: original classifier looked for the literal substrings ``sanskrit``, ``english``,
#: ``translation`` and ``registry``, which the concept layer happens to write and **no
#: other layer does**. So 22,686 formula occurrences matched on a folded Sanskrit surface,
#: 6,596 cross-Veda parallels compared between two Sanskrit texts, and 31,646 Anukramaṇī
#: attributions all graded ``UNSPECIFIED`` — and the two evidence-mode audits a researcher
#: would run ("which conclusions rest only on a translation?", "which survive
#: Sanskrit-only filtering?") were wrong in opposite directions as a result.
#:
#: Matched as substrings of the lowercased method, most specific first.
_SANSKRIT_METHOD_MARKERS: Final[tuple[str, ...]] = (
    "sanskrit",
    # formula-occurrence-word-aligned-v1, formula-occurrence-sandhi-substring-v1
    "formula-occurrence",
    # crossveda-parallels:identity:SCRIPT_FOLDED, :near:minhash-char4+lcs:..., :reuse:...
    "crossveda-parallels",
    # theonym-mention-v1:rv-lemma-annotation, :sanskrit-surface-token, :...-sandhi
    "theonym-mention",
    "lemma-annotation",
    # every surface name the comparison layer can reach a match on
    "script_folded",
    "sandhi_insensitive",
    "accent_insensitive",
    "unicode_normalized",
    "source_exact",
    "punctuation_normalized",
)

#: Method fragments identifying a model that read a *translation* span. The V3.2 semantic
#: runs anchor every assertion to a ``translation_record_id`` plus character offsets in
#: Griffith or Whitney, so the evidence is checkable and it is English.
_TRANSLATION_METHOD_MARKERS: Final[tuple[str, ...]] = (
    "english",
    "translation",
    "semantic-extraction",
)


def classify_evidence(method: str) -> EvidenceBasis:
    """Read an edge's ``method`` string for which text its evidence came from.

    The enrichment layer encodes its evidence path in the method -- for example
    ``concept-alias-v1:english+sanskrit-token`` -- so for that layer the information is
    already stored and only needs surfacing. For every *other* layer the method names an
    algorithm rather than a text, and those are resolved through
    :data:`_SANSKRIT_METHOD_MARKERS` and :data:`_TRANSLATION_METHOD_MARKERS`.

    Returns ``UNSPECIFIED`` only when there is genuinely no method to read. A caller that
    knows the layer should treat that as its cue to supply a basis, not as an answer.
    """
    if not method:
        return EvidenceBasis.UNSPECIFIED
    lowered = method.lower()
    sanskrit = any(marker in lowered for marker in _SANSKRIT_METHOD_MARKERS)
    english = any(marker in lowered for marker in _TRANSLATION_METHOD_MARKERS)
    if sanskrit and english:
        return EvidenceBasis.MIXED
    if sanskrit:
        return EvidenceBasis.SANSKRIT
    if english:
        return EvidenceBasis.TRANSLATION
    if "registry" in lowered or "lexicon" in lowered:
        return EvidenceBasis.SOURCE_METADATA
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
_DIAGNOSTIC_RELS: Final[frozenset[str]] = frozenset({"QA_ISSUE_ON"})

#: Lexical mention edges. The Rigvedic morphology behind them is manual scholarly
#: annotation, but the *entity* attached to a lemma is this project's alias table, so the
#: edge as a whole is a derivation over an annotation rather than a source statement.
_LEXICAL_RELS: Final[frozenset[str]] = frozenset({"MENTIONS_LEMMA", "MENTIONS_ENTITY"})

#: Relationship types whose evidence is, by construction, a comparison between two
#: Sanskrit texts. Used to supply a basis where the edge's own method string is absent.
_SANSKRIT_TEXT_RELS: Final[frozenset[str]] = frozenset(
    {
        "EXACT_PARALLEL_OF",
        "NEAR_PARALLEL_OF",
        "PARALLEL_TO",
        "VARIANT_OF",
        "REUSES_TEXT_FROM",
        "USES_FORMULA",
    }
)


#: V2 and V3 predicates whose grade follows from the predicate itself, because they carry
#: no enrichment envelope of their own. Listed here rather than set by each loader so that
#: the grading table stays the single source of truth: ``stamp_grades`` runs before the
#: domain loaders, so a tier the loader applied only ``ON CREATE`` was silently overwritten
#: on every rebuild and the edge ended up graded by the fall-through default.
#:
#: The split is the claim. ``ADDRESSES_CONCERN`` and ``USED_FOR_RITE`` assert no more than
#: the mention they derive from -- naming what you want is wanting it, and the rite
#: vocabulary occurs nowhere but the occasion -- so they are TIER_B. ``TREATS`` and
#: ``PROTECTS_FROM`` assert a *function*, that the passage acts on the affliction rather
#: than naming it, which is a reading of the charm. Everything curated is TIER_D.
#:
#: Each entry now names its own **evidence basis** as a third element. It used to be
#: inferred from the tier -- TIER_B meant SANSKRIT and anything else meant STRUCTURAL --
#: which told a reader that a hand-authored deity axis rested on "the corpus structure as
#: printed by the edition". A curated registry statement and a printed hymn boundary are
#: not the same kind of evidence, and the whole purpose of this axis is that a reader can
#: tell them apart.
_V2_PREDICATE_GRADE: Final[dict[str, tuple[KnowledgeLayer, QualityTier, EvidenceBasis]]] = {
    # Derived from a deterministic mention plus a curated whitelist.
    "ADDRESSES_CONCERN": (
        KnowledgeLayer.L2_DETERMINISTIC_DERIVED,
        QualityTier.TIER_B,
        EvidenceBasis.SANSKRIT,
    ),
    "USED_FOR_RITE": (
        KnowledgeLayer.L2_DETERMINISTIC_DERIVED,
        QualityTier.TIER_B,
        EvidenceBasis.SANSKRIT,
    ),
    # Structural decomposition of a dual or plural label: follows from its morphology.
    "COMPOSED_OF": (
        KnowledgeLayer.L2_DETERMINISTIC_DERIVED,
        QualityTier.TIER_B,
        EvidenceBasis.SOURCE_METADATA,
    ),
    # Identity of an epithet-qualified label with its base deity. Read off the source label
    # and nothing else, but read by a model rather than derived: `rakṣohāgniḥ` needs the
    # sandhi seen through, and `sāvitrī sūryā` is refused precisely because the string
    # invites the identification and the grammar denies it. That is adjudication, so L3/C.
    "EPITHET_VARIANT_OF": (
        KnowledgeLayer.L3_LLM_EXTRACTED,
        QualityTier.TIER_C,
        EvidenceBasis.SANSKRIT,
    ),
    # Reproducible aggregation over edges that already exist.
    "MEASURES": (
        KnowledgeLayer.L2_DETERMINISTIC_DERIVED,
        QualityTier.TIER_B,
        EvidenceBasis.STRUCTURAL,
    ),
    # ---- V3: the reified assertion layer -------------------------------------------
    # The spine edges assert nothing about the corpus. "This assertion was read off this
    # passage" and "this assertion predicates this vocabulary member" are bookkeeping about
    # the layer, so they are graded as the derivation they are and carry STRUCTURAL
    # evidence. The *assertions* carry the claim and carry their own grade.
    "HAS_SEMANTIC_ASSERTION": (
        KnowledgeLayer.L2_DETERMINISTIC_DERIVED,
        QualityTier.TIER_B,
        EvidenceBasis.STRUCTURAL,
    ),
    "ASSERTION_PREDICATE": (
        KnowledgeLayer.L2_DETERMINISTIC_DERIVED,
        QualityTier.TIER_B,
        EvidenceBasis.STRUCTURAL,
    ),
    # An assertion's agent and target are read from the same morphological annotation the
    # assertion is, so they are exactly as good as it and no better.
    "ASSERTION_AGENT": (
        KnowledgeLayer.L2_DETERMINISTIC_DERIVED,
        QualityTier.TIER_B,
        EvidenceBasis.SANSKRIT,
    ),
    "ASSERTION_TARGET": (
        KnowledgeLayer.L2_DETERMINISTIC_DERIVED,
        QualityTier.TIER_B,
        EvidenceBasis.SANSKRIT,
    ),
    # One-hop aggregates, rebuilt from the assertion nodes on every load.
    "PERFORMS_ACTION": (
        KnowledgeLayer.L2_DETERMINISTIC_DERIVED,
        QualityTier.TIER_B,
        EvidenceBasis.SANSKRIT,
    ),
    "IS_ASKED_TO": (
        KnowledgeLayer.L2_DETERMINISTIC_DERIVED,
        QualityTier.TIER_B,
        EvidenceBasis.SANSKRIT,
    ),
    # A descriptor derived from a deity name by vrddhi is a morphological fact about the
    # index's own wording.
    "ASCRIBES_TO_DEVATA": (
        KnowledgeLayer.L2_DETERMINISTIC_DERIVED,
        QualityTier.TIER_B,
        EvidenceBasis.SOURCE_METADATA,
    ),
    # Concept-lexicon structure. Both were falling through to the TIER_D "ungraded"
    # default -- 39 edges each -- because they carry no provenance vocabulary at all.
    # They are curated registry statements, which is what the lexicon is for, so they
    # grade as the registry does rather than as an unread edge.
    "BROADER_THAN": (
        KnowledgeLayer.L2_DETERMINISTIC_DERIVED,
        QualityTier.TIER_B,
        EvidenceBasis.SOURCE_METADATA,
    ),
    "DEVATA_ASSOCIATED_WITH": (
        KnowledgeLayer.L4_INTERPRETIVE_CLAIM,
        QualityTier.TIER_D,
        EvidenceBasis.SOURCE_METADATA,
    ),
    # Asserts a function beyond naming.
    "TREATS": (KnowledgeLayer.L4_INTERPRETIVE_CLAIM, QualityTier.TIER_D, EvidenceBasis.SANSKRIT),
    "PROTECTS_FROM": (
        KnowledgeLayer.L4_INTERPRETIVE_CLAIM,
        QualityTier.TIER_D,
        EvidenceBasis.SANSKRIT,
    ),
    # Curated deity and ritual structure.
    "HAS_AXIS": (
        KnowledgeLayer.L4_INTERPRETIVE_CLAIM,
        QualityTier.TIER_D,
        EvidenceBasis.SOURCE_METADATA,
    ),
    "HAS_EPITHET": (
        KnowledgeLayer.L4_INTERPRETIVE_CLAIM,
        QualityTier.TIER_D,
        EvidenceBasis.SOURCE_METADATA,
    ),
    "MEMBER_OF": (
        KnowledgeLayer.L4_INTERPRETIVE_CLAIM,
        QualityTier.TIER_D,
        EvidenceBasis.SOURCE_METADATA,
    ),
    "USES_OFFERING": (
        KnowledgeLayer.L4_INTERPRETIVE_CLAIM,
        QualityTier.TIER_D,
        EvidenceBasis.SOURCE_METADATA,
    ),
    "USES_SUBSTANCE": (
        KnowledgeLayer.L4_INTERPRETIVE_CLAIM,
        QualityTier.TIER_D,
        EvidenceBasis.SOURCE_METADATA,
    ),
    "USES_OBJECT": (
        KnowledgeLayer.L4_INTERPRETIVE_CLAIM,
        QualityTier.TIER_D,
        EvidenceBasis.SOURCE_METADATA,
    ),
    "INVOKES_DEVATA": (
        KnowledgeLayer.L4_INTERPRETIVE_CLAIM,
        QualityTier.TIER_D,
        EvidenceBasis.SOURCE_METADATA,
    ),
    "PERFORMED_BY": (
        KnowledgeLayer.L4_INTERPRETIVE_CLAIM,
        QualityTier.TIER_D,
        EvidenceBasis.SOURCE_METADATA,
    ),
    "PERFORMED_FOR": (
        KnowledgeLayer.L4_INTERPRETIVE_CLAIM,
        QualityTier.TIER_D,
        EvidenceBasis.SOURCE_METADATA,
    ),
    # These two differ from the apparatus predicates above, and the difference is which
    # artefact the evidence lives in. `USES_OBJECT` and its siblings point at an *entity*
    # and rest on the curated registry's assembled picture of the rite as an institution,
    # so SOURCE_METADATA is right for them: no single verse says "the yajna uses the
    # ladle". `DESCRIBED_IN` and `HAS_STEP` point at a *passage* and rest on its Sanskrit
    # -- the sautramani is named at VS 19.31, and the morning pressing is called the
    # first draught at RV 10.112.1 in the text's own words. Grading those SOURCE_METADATA
    # would claim a traditional index states them, and none does; the reading is ours,
    # which is what TIER_D already says. So the tier stays and the basis is corrected.
    "DESCRIBED_IN": (
        KnowledgeLayer.L4_INTERPRETIVE_CLAIM,
        QualityTier.TIER_D,
        EvidenceBasis.SANSKRIT,
    ),
    "HAS_STEP": (
        KnowledgeLayer.L4_INTERPRETIVE_CLAIM,
        QualityTier.TIER_D,
        EvidenceBasis.SANSKRIT,
    ),
    # The interpretive layer's own edges.
    "SUPPORTED_BY": (
        KnowledgeLayer.L4_INTERPRETIVE_CLAIM,
        QualityTier.TIER_D,
        EvidenceBasis.STRUCTURAL,
    ),
    "SUPPORTED_BY_STATISTIC": (
        KnowledgeLayer.L4_INTERPRETIVE_CLAIM,
        QualityTier.TIER_D,
        EvidenceBasis.STRUCTURAL,
    ),
    "CONCERNS": (
        KnowledgeLayer.L4_INTERPRETIVE_CLAIM,
        QualityTier.TIER_D,
        EvidenceBasis.STRUCTURAL,
    ),
    "CONTRADICTS": (
        KnowledgeLayer.L4_INTERPRETIVE_CLAIM,
        QualityTier.TIER_D,
        EvidenceBasis.STRUCTURAL,
    ),
    "ASSERTED_BY": (
        KnowledgeLayer.L4_INTERPRETIVE_CLAIM,
        QualityTier.TIER_D,
        EvidenceBasis.STRUCTURAL,
    ),
}


#: Predicates whose **owning layer** computes the grade, so the bulk stamper must not
#: touch them.
#:
#: ``MENTIONS_DEVATA`` is the case that forced this. Its grade is not derivable from the
#: generic rules: a Rigvedic row earns TIER_A because a manual scholarly annotation states
#: the lemma, a homonym's non-vocative row earns TIER_B because the same annotation does
#: *not* state the deity reading, and every row carries
#: ``attribution_precision = TEXTUAL_MENTION`` because naming a god in the text is not the
#: Anukramani ascribing a hymn to one. Re-deriving it from ``trust`` alone would flatten
#: all three distinctions and silently rewrite TEXTUAL_MENTION to PER_PASSAGE, which is
#: the one value the layer exists to keep separate.
#: ``CO_OCCURS_WITH`` is owned because its grade is a statement about *how it was
#: computed*, not about any source's provenance envelope. It is a count over the mention
#: layer -- recomputable, therefore TIER_B, therefore SANSKRIT -- and it carries no
#: ``method`` vocabulary the generic classifier knows, so the stamper graded all 292 edges
#: ``UNSPECIFIED`` and wrote its own complaint into their ``grade_basis``.
#:
#: The twelve candidate predicates are owned for a sharper reason: **their grade is the
#: output of an independent review, and no provenance signature can reproduce it.** All
#: twelve are written by the model extraction layer with ``trust = LLM_EXTRACTED``, so the
#: generic rule above correctly grades an *unreviewed* one TIER_D. But 587 of them were
#: then adjudicated one at a time against the passage and accepted, which is the
#: definition of TIER_C -- and re-deriving the grade from ``trust`` immediately demoted
#: every one of them back to TIER_D. That was measured: a post-load regrade silently
#: erased all 587 promotions in one pass. The review verdict lives on the edge
#: (``review_verdict``, ``review_state``) and in
#: :mod:`vedagraph.domain.candidate_review`; the stamper has no access to either and must
#: not guess.
#: ``HAS_SEMANTIC_ASSERTION`` is owned because its grade is the grade of the *node it
#: points at*, and the stamper cannot see across an edge. The ``:SemanticAssertion`` label
#: holds two layers of unequal strength -- rule-over-manual-annotation at TIER_B/SANSKRIT
#: and unreviewed model extraction at TIER_D/TRANSLATION -- and the generic rule graded
#: every edge into both ``TIER_B``/``STRUCTURAL``, which made the documented
#: "filter by quality_tier to exclude model output" recipe silently fail.
#: :func:`vedagraph.domain.v3_loader.reconcile_assertion_edge_grades` owns it instead.
#:
#: ``MEMBER_OF_FAMILY`` is owned because its tier depends on *which derivation produced
#: the row*: containment-derived rows are TIER_B and the four similarity-threshold rows
#: are TIER_D, and no provenance signature distinguishes them.
#:
#: ``HAS_FORMULA`` is owned for the same reason and one more: it is a *mirror* of
#: ``MEMBER_OF_FAMILY``, so its grade must be byte-identical to its inbound twin's. Letting
#: the generic rules re-derive it would let the two directions of one membership disagree,
#: which is worse than either grade being wrong -- a query would get a different tier
#: depending on which way it walked.
#:
#: ``ASSERTION_PREDICATE`` is owned because, like ``HAS_SEMANTIC_ASSERTION``, its grade is
#: the grade of the *assertion it starts from* and the stamper cannot see across an edge.
#: The generic rules graded every edge in the type ``TIER_B``/``STRUCTURAL`` on the
#: reasoning that "this assertion predicates this vocabulary member" is structural. That is
#: the identical mistake the ``HAS_SEMANTIC_ASSERTION`` note above describes: once the
#: sealed model layer also reaches ``:ActionPredicate``, a uniform ``TIER_B`` makes
#: "predicates asserted at TIER_B" return unreviewed extraction over Griffith's English
#: next to Zurich morphology, with nothing on the edge to separate them.
#: :func:`vedagraph.domain.v3_loader.load_sealed_predicate_edges` owns it instead, and
#: grades **both** populations from their source assertion rather than only the rows it
#: created -- a reconciler that graded only its own additions would leave the older half
#: dependent on a pass outside the V3 projection for its grade.
#:
#: ``BELONGS_TO_FAMILY`` is owned because, like ``MEMBER_OF_FAMILY``, its ``grade_basis``
#: depends on which derivation produced the row and no provenance signature distinguishes
#: them: 290 rows read a patronymic the Anukramaṇī printed as its own word, 14 read one
#: this layer split out of a sandhi-fused token, and the second warrant is weaker in a way
#: the generic rules cannot see. All 305 are TIER_B, so a re-grade would not change the
#: tier -- it would overwrite the sentence that says which of the two the reader is
#: looking at, which is the only thing on that edge worth reading.
LAYER_OWNED_GRADES: Final[frozenset[str]] = frozenset(
    {
        "BELONGS_TO_FAMILY",
        "MENTIONS_DEVATA",
        "CO_OCCURS_WITH",
        "HAS_SEMANTIC_ASSERTION",
        "MEMBER_OF_FAMILY",
        "HAS_FORMULA",
        "SHARES_ENTITY_VOCABULARY_WITH",
        # Layer-owned because the rite layer holds TWO populations that the generic
        # signature cannot tell apart: 110 source-stated verse-level tags and 419 book
        # locus priors, the latter marked by `derivation = 'BOOK_LOCUS_PRIOR'`. That
        # property is not one of _SIGNATURE_FIELDS, so the generic grader saw one
        # signature, graded both alike, and flattened all 529 to PER_PASSAGE -- turning a
        # book's claim about its verses into 419 per-verse statements, which is the
        # inherited-as-per-verse shape the frozen benchmark names first among misleading
        # answers. Caught by a live test, not by a count.
        "USED_FOR_RITE",
        "ASSERTION_PREDICATE",
        "CONTRASTS_WITH",
        "DESCRIBES",
        "DESCRIBES_ACTION",
        "HAS_THEME",
        "INVOKES",
        "INVOLVES_OFFERING",
        "INVOLVES_RITUAL",
        "INVOLVES_SUBSTANCE",
        "PRAISES",
        "REFERS_TO_NATURAL_PHENOMENON",
        "REFERS_TO_PLACE",
        "REQUESTS",
    }
)


def _grade_edge_uncontracted(rel_type: str, properties: Mapping[str, Any]) -> Grade:
    """Derive the unified grade for one edge from whatever it already records.

    Do not call directly. :func:`grade_edge` wraps this and applies
    :data:`ATTRIBUTION_CONTRACT` to the attribution axis afterwards. Every ``precision``
    written below is therefore provisional; the layer, tier, basis and evidence axes are
    final. The split exists because those axes are derived from what the edge *records*
    (its method, trust and provenance vocabulary), while the attribution axis is a fact
    about the edge's *endpoints* that no property on the edge can witness.

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
            # An Anukramaṇī ascription is a traditional index's statement about the verse,
            # not a feature of the verse's text. Was `evidence or STRUCTURAL`, which never
            # reached the fallback: `EvidenceBasis.UNSPECIFIED` is a non-empty string and
            # therefore truthy, so 31,646 attribution edges kept UNSPECIFIED while the
            # code read as though it handled them.
            evidence_basis=(
                EvidenceBasis.SOURCE_METADATA if evidence is EvidenceBasis.UNSPECIFIED else evidence
            ),
        )

    # A `provenance_class` holding a *trust* value: 256 RV-internal EXACT_PARALLEL_OF and
    # 69 PARALLEL_TO edges carry `provenance_class = 'DETERMINISTIC_DERIVED'`, a value from
    # the enrichment envelope's vocabulary written into the knowledge layer's field. They
    # matched neither branch and fell through to the TIER_D default, so exact parallels
    # with `similarity = 1.0` and five concurring detection methods were graded
    # "interpretive". Read rather than dropped, because the alternative is to misgrade
    # them: this module's job is to read the graph as it is.
    if isinstance(provenance_class, str) and provenance_class in _LAYER_BY_TRUST:
        layer = _LAYER_BY_TRUST[provenance_class]
        return Grade(
            layer=layer,
            tier=TIER_BY_LAYER[layer],
            precision=AttributionPrecision.PER_PASSAGE,
            basis=(
                f"provenance_class={provenance_class}, which is a trust-vocabulary value "
                "recorded in the knowledge layer's field by an earlier pipeline"
            ),
            evidence_basis=(
                EvidenceBasis.SANSKRIT
                if rel_type in _SANSKRIT_TEXT_RELS or rel_type in _LEXICAL_RELS
                else evidence
            ),
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
        layer, tier, declared_basis = v2
        return Grade(
            layer=layer,
            tier=tier,
            precision=AttributionPrecision.PER_PASSAGE,
            basis=f"{rel_type}: grade follows from the predicate (domain layer)",
            evidence_basis=declared_basis,
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


#: Which relationships carry an attribution at all, and which value each may hold.
#:
#: THE DEFECT THIS CLOSES. ``_grade_edge_uncontracted`` has eight return sites and seven of
#: them hardcode ``PER_PASSAGE``; only the ``scope_origin`` branch consults
#: :data:`PRECISION_BY_SCOPE_ORIGIN`. Every edge the Anukramaṇī did not produce therefore
#: got ``PER_PASSAGE`` **by construction, whatever it was**, and
#: :func:`vedagraph.domain.upgrade.stamp_grades` discovers relationship types from the live
#: graph and propagated that value graph-wide. The result: ``CONTAINS`` claimed per-passage
#: attribution over the corpus's own containment tree, ``QA_ISSUE_ON`` claimed it over this
#: repository's self-audit, ``SHARES_ENTITY_VOCABULARY_WITH`` claimed it over a symmetric
#: analytics edge with no subject, and ``HAS_TEXT_VERSION`` claimed it over the edition's
#: own typesetting. 190,731 of 265,289 edges held a value that did not mean what it said.
#:
#: THE DEFINING TEST, applied mechanically to all 65 live types:
#:
#:   An edge is attribution-bearing if and only if one endpoint is a ``:Passage``, and the
#:   edge attaches a claim to that passage which could *in principle* have arrived from the
#:   enclosing sūkta instead -- so that "did a source say this of THIS verse, or of the
#:   container it sits in, or does the verse's own Sanskrit say it?" is a well-formed
#:   question with more than one possible answer.
#:
#: Five rules follow, and each is cited on the rows it decides:
#:
#: * **R1** no ``:Passage`` endpoint -> not an attribution. The value space is *defined*
#:   over passages (see :class:`~vedagraph.domain.ontology.AttributionPrecision`).
#: * **R2** *both* endpoints are ``:Passage`` -> not an attribution. An attribution has one
#:   subject and one attributed thing; a passage-to-passage edge has two subjects, so "about
#:   which unit?" is ill-formed. A symmetric pair has no subject to be precise about.
#: * **R3** the other endpoint is the passage's own physical text -> not an attribution.
#:   Nobody *claims* a verse has a text; ``CONTAINER_INHERITED`` is inconceivable there, so
#:   the property would be a constant carrying zero bits.
#: * **R4** the other endpoint is something the passage's own Sanskrit **names** ->
#:   ``TEXTUAL_MENTION``, which is that value's own definition.
#: * **R5** otherwise a source, curator or model attached a claim -> ``PER_PASSAGE``, or
#:   ``None`` below where the layer legitimately holds both halves.
#:
#: ``None`` means MIXED: the type carries both ``PER_PASSAGE`` and ``CONTAINER_INHERITED``
#: and the ``scope_origin`` branch decides per edge. The four MIXED types must never be
#: swept to a single value -- ``USED_FOR_RITE`` is in :data:`LAYER_OWNED_GRADES` precisely
#: because a generic sweep once flattened all 529 of them and turned 419 book-locus priors
#: into per-verse statements.
#:
#: A relationship type absent from this table **raises**. That is deliberate and is the
#: whole point of preferring a sentinel to an absent property: ``stamp_grades`` auto-enrols
#: every new type the moment it exists, so a new type nobody classified must fail the build
#: loudly rather than default to looking correct.
ATTRIBUTION_CONTRACT: Final[dict[str, AttributionPrecision | None]] = {
    # -- R5. A source, curator or model attached a claim to this verse. -----------------
    # MIXED: both halves are real and scope_origin decides. Never sweep these.
    "HAS_DEVATA": None,
    "HAS_RISHI": None,
    "HAS_CHANDAS": None,
    "USED_FOR_RITE": None,
    "HAS_DEVATA_ASCRIPTION": AttributionPrecision.CONTAINER_INHERITED,
    "HAS_SEMANTIC_ASSERTION": AttributionPrecision.PER_PASSAGE,
    "ADDRESSES_CONCERN": AttributionPrecision.PER_PASSAGE,
    "PROTECTS_FROM": AttributionPrecision.PER_PASSAGE,
    "TREATS": AttributionPrecision.PER_PASSAGE,
    "INVOKES": AttributionPrecision.PER_PASSAGE,
    "DESCRIBES": AttributionPrecision.PER_PASSAGE,
    "DESCRIBES_ACTION": AttributionPrecision.PER_PASSAGE,
    "PRAISES": AttributionPrecision.PER_PASSAGE,
    "REQUESTS": AttributionPrecision.PER_PASSAGE,
    "HAS_THEME": AttributionPrecision.PER_PASSAGE,
    "CONTRASTS_WITH": AttributionPrecision.PER_PASSAGE,
    "INVOLVES_OFFERING": AttributionPrecision.PER_PASSAGE,
    "INVOLVES_RITUAL": AttributionPrecision.PER_PASSAGE,
    "INVOLVES_SUBSTANCE": AttributionPrecision.PER_PASSAGE,
    "REFERS_TO_NATURAL_PHENOMENON": AttributionPrecision.PER_PASSAGE,
    "REFERS_TO_PLACE": AttributionPrecision.PER_PASSAGE,
    # The Passage is the OBJECT here, not the subject (Ritual -> Passage,
    # InterpretiveClaim -> Passage). Kept attribution-bearing because the claim really is
    # attached to that verse and could in principle have been attached to its sukta. A
    # stricter "the subject must be the passage" reading would move these two to the
    # sentinel; it is defensible and it is not the reading taken here.
    "DESCRIBED_IN": AttributionPrecision.PER_PASSAGE,
    "SUPPORTED_BY": AttributionPrecision.PER_PASSAGE,
    # -- R4. The verse's own Sanskrit names the thing. ----------------------------------
    # MENTIONS_DEVATA already held TEXTUAL_MENTION. The other four are the same kind of
    # fact and were graded PER_PASSAGE, which is the incoherence at the centre of this
    # table: MENTIONS_ENTITY is the generalisation of MENTIONS_DEVATA to every domain
    # entity, and the two were describing one act of naming with two different words.
    "MENTIONS_DEVATA": AttributionPrecision.TEXTUAL_MENTION,
    "MENTIONS_ENTITY": AttributionPrecision.TEXTUAL_MENTION,
    "MENTIONS_LEMMA": AttributionPrecision.TEXTUAL_MENTION,
    "USES_FORMULA": AttributionPrecision.TEXTUAL_MENTION,
    # The judgement call of the table. ABOUT_CONCEPT is not literally a naming, so this is
    # a slight stretch of TEXTUAL_MENTION -- but it is a salience ranking computed over the
    # mention layer and provably a subset of it, and grading a subset differently from its
    # superset is exactly the drift the table exists to stop. PER_PASSAGE was the one
    # indefensible option, because no source states a concept of a verse.
    "ABOUT_CONCEPT": AttributionPrecision.TEXTUAL_MENTION,
    # -- R3. The edition's own layout, not a claim. -------------------------------------
    "HAS_TEXT_VERSION": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "HAS_TRANSLATION": AttributionPrecision.NOT_AN_ATTRIBUTION,
    # -- R2. Passage to passage: two subjects, so no subject. ---------------------------
    "CONTAINS": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "EXACT_PARALLEL_OF": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "NEAR_PARALLEL_OF": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "PARALLEL_TO": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "REUSES_TEXT_FROM": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "VARIANT_OF": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "SHARES_ENTITY_VOCABULARY_WITH": AttributionPrecision.NOT_AN_ATTRIBUTION,
    # -- R1. No passage endpoint at all. ------------------------------------------------
    # Entity-to-entity, reification spokes, derived analytics, taxonomy, and this
    # repository's own self-audit. None of these has a verse to be precise about.
    "ASSERTION_AGENT": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "ASSERTION_PREDICATE": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "ASSERTION_TARGET": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "BELONGS_TO_FAMILY": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "BROADER_THAN": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "COMPOSED_OF": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "CONCERNS": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "CONTRADICTS": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "CO_OCCURS_WITH": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "DEVATA_ASSOCIATED_WITH": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "EPITHET_VARIANT_OF": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "HAS_AXIS": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "HAS_EPITHET": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "HAS_FORMULA": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "HAS_STEP": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "INVOKES_DEVATA": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "IS_ASKED_TO": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "MEASURES": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "MEMBER_OF": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "MEMBER_OF_FAMILY": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "PERFORMED_BY": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "PERFORMED_FOR": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "PERFORMS_ACTION": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "QA_ISSUE_ON": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "SUPPORTED_BY_STATISTIC": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "USES_OBJECT": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "USES_OFFERING": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "USES_SUBSTANCE": AttributionPrecision.NOT_AN_ATTRIBUTION,
    # -- Declared but not yet populated. --------------------------------------------------
    # These carry no live edges, so the V3.2 survey of the graph did not see them. They are
    # classified here anyway, from their declared endpoint signatures, because the grader
    # raises on an unknown type: leaving them out would turn "someone finally populated this
    # layer" into a build failure with a confusing message. Every one of them is
    # entity-to-entity or passage-to-passage, so R1 or R2 decides all but one.
    "ASCRIBES_TO_DEVATA": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "ASSERTED_BY": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "ASSOCIATED_WITH_CONCEPT": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "ASSOCIATED_WITH_PHENOMENON": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "ASSOCIATED_WITH_SUBSTANCE": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "MUSICALIZED_AS": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "PERSONIFIES": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "RECEIVES_OFFERING": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "TEXTUALLY_REUSED_AS": AttributionPrecision.NOT_AN_ATTRIBUTION,
    "WIELDS": AttributionPrecision.NOT_AN_ATTRIBUTION,
    # The one exception, and the only heterogeneous subject in the vocabulary: this
    # signature admits Passage, Rishi AND RishiFamily as the subject, so whether an edge of
    # it is an attribution depends on the edge and not only on its type. MIXED defers to the
    # per-edge scope_origin branch. Whoever populates this layer must set the value per
    # edge; a Rishi -> Tribe edge that claims one anyway is caught independently by the
    # `attribution_claimed_on_an_edge_with_no_passage` live invariant.
    "ASSOCIATED_WITH_TRIBE": None,
}


class UncontractedRelationshipError(KeyError):
    """A relationship type reached the grader with no entry in the attribution contract.

    Raised rather than defaulted. ``stamp_grades`` discovers types from the live graph, so
    a new relationship auto-enrols the moment one edge of it exists; without this the new
    type would silently acquire whatever the cascade happened to return, which is how
    ``PER_PASSAGE`` reached 190,731 edges that were not attributions.
    """


def grade_edge(rel_type: str, properties: Mapping[str, Any]) -> Grade:
    """Grade one edge, with the attribution axis decided by :data:`ATTRIBUTION_CONTRACT`.

    The layer, tier, basis and evidence axes come from what the edge records about its own
    provenance. The attribution axis does not: it is a fact about the edge's *endpoints*,
    which no property on the edge witnesses, so it is looked up by relationship type and
    overrides whatever the cascade provisionally returned.

    ``MIXED`` types (contract value ``None``) keep the cascade's answer, because for those
    four the ``scope_origin`` branch is the correct decision procedure and is already
    per-edge.
    """
    grade = _grade_edge_uncontracted(rel_type, properties)
    if rel_type not in ATTRIBUTION_CONTRACT:
        raise UncontractedRelationshipError(
            f"{rel_type} has no entry in ATTRIBUTION_CONTRACT. Classify it against the "
            f"defining test in that table before it can be graded: an edge is "
            f"attribution-bearing only if one endpoint is a Passage and the claim could "
            f"in principle have been inherited from its container instead."
        )
    contracted = ATTRIBUTION_CONTRACT[rel_type]
    if contracted is None or contracted is grade.precision:
        return grade
    return replace(grade, precision=contracted)


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
