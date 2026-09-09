"""The closed relationship vocabulary the enrichment layer may write, and its constraints.

Two vocabularies meet here and they are not the same thing.

**Textual predicates** say something about how two stretches of Sanskrit relate:
``EXACT_PARALLEL_OF``, ``NEAR_PARALLEL_OF``, ``VARIANT_OF``, ``REUSES_TEXT_FROM``,
``SHARES_FORMULA_WITH``. They are decided by string comparison and are as reproducible as
the comparison is. Distinguishing them matters: a verse the Samaveda takes from the
Rigveda unchanged, a verse it takes with one word altered, and a verse that merely shares a
formula with it are three different facts about textual transmission, and a reader who
gets all three back as ``PARALLEL_TO`` has been told nothing.

**Semantic predicates** say something about what a passage means. Those are not invented
here. :mod:`vedagraph.semantic.ontology` already froze a 14-predicate whitelist for the
Rigveda semantic pilot, with a written definition, an interpretation-risk grade and a
subject/object signature for each, plus five predicates *refused by name* with recorded
reasons. This module imports that vocabulary rather than restating it, for two reasons:
a second list would drift from the first, and the refusals are the more valuable half.

That import has a consequence worth stating plainly. The enrichment brief lists ``CAUSES``
and ``IDENTIFIES_WITH`` among its candidate predicates. ``CAUSES`` is already refused by
name in the frozen ontology -- "causal claims in a mythological narrative are not the same
as causal claims about the world, and an edge cannot carry the difference" -- and
``IDENTIFIES_WITH`` is the same claim as the refused ``REPRESENTS``. Neither is emitted.
:data:`BRIEF_PREDICATE_MAPPING` records where every predicate the brief named ended up, so
the omissions are decisions with reasons rather than gaps.

Nothing in this module modifies the frozen ontology. It reads it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from vedagraph.semantic.ontology import (
    ALLOWED_PREDICATES,
    FORBIDDEN_PREDICATES,
    SemanticPredicate,
)


class NodeKind(StrEnum):
    """Node families an enrichment edge may attach to.

    Deliberately coarser than the Neo4j labels: domain and range constraints are about
    what kind of thing an edge connects, and ``Mantra`` is a ``Passage`` for that purpose.
    """

    PASSAGE = "Passage"
    FORMULA = "Formula"
    CONCEPT = "Concept"
    DEVATA = "Devata"
    RISHI = "Rishi"
    CHANDAS = "Chandas"
    LEMMA = "Lemma"


class TextualPredicate(StrEnum):
    """How two stretches of Sanskrit relate. Decided by comparison, never by reading."""

    #: The two verses are identical on the strongest surface their scripts allow. Between
    #: same-script corpora that means identical text; across scripts it means identical
    #: after transliteration and folding, and the edge records which.
    EXACT_PARALLEL_OF = "EXACT_PARALLEL_OF"
    #: Substantially the same verse with differences beyond notation -- a changed word, a
    #: reordered pada, a different ending.
    NEAR_PARALLEL_OF = "NEAR_PARALLEL_OF"
    #: The same verse differing only in how the two editions write it: accent notation,
    #: word division, orthography. A transmission fact about the editions, not the text.
    VARIANT_OF = "VARIANT_OF"
    #: Directed. One Veda takes a verse from another, asserted only where the corpus's own
    #: structure establishes the direction. See :func:`reuse_direction`.
    REUSES_TEXT_FROM = "REUSES_TEXT_FROM"
    #: Two passages share at least one Formula.
    #:
    #: **Declared and deliberately not materialised in v1: zero edges are written.** The
    #: Formula hub already carries this relation losslessly -- ``(a)-[:USES_FORMULA]->(f)
    #: <-[:USES_FORMULA]-(b)`` is the same fact in two hops -- and materialising it would
    #: undo the reason the hub exists: the largest formula spans 93 passages, so that one
    #: node alone would emit 4,278 edges, and the layer as a whole would add 87,296 where it
    #: currently adds 27,511. The name is kept in the vocabulary so a consumer can see the
    #: relation is modelled and how to traverse it, rather than concluding it was forgotten.
    SHARES_FORMULA_WITH = "SHARES_FORMULA_WITH"


class StructuralPredicate(StrEnum):
    """Edges that attach a passage or concept to a hub node."""

    #: Passage to Formula. The hub that replaces combinatorial passage-to-passage edges.
    USES_FORMULA = "USES_FORMULA"
    #: Passage to Concept. Carries evidence, confidence and trust like everything else.
    ABOUT_CONCEPT = "ABOUT_CONCEPT"
    #: Concept to Concept, and only where the narrower term is genuinely a kind of the
    #: broader one. Not a synonym link and not a topical association.
    BROADER_THAN = "BROADER_THAN"
    #: Concept to its Sanskrit or English surface forms.
    HAS_ALIAS = "HAS_ALIAS"
    #: Devata to Concept. The one edge that connects the two ontologies, and the reason
    #: they can stay separate: Agni-the-deity is *associated with* fire-the-concept, and
    #: is not the same node as it.
    DEVATA_ASSOCIATED_WITH = "DEVATA_ASSOCIATED_WITH"
    #: Work to its own QA findings, so a corpus caveat is visible in the graph.
    QA_ISSUE_ON = "QA_ISSUE_ON"


#: Semantic predicates this layer may write. Exactly the frozen whitelist -- not a subset
#: chosen here, because choosing a subset is an ontology decision and this layer does not
#: get to make one.
SEMANTIC_PREDICATES: Final[frozenset[SemanticPredicate]] = ALLOWED_PREDICATES

#: The complete set of relationship type names the enrichment layer may create. Validation
#: rejects anything outside it; there is no path by which a stage invents a name.
CONTROLLED_PREDICATES: Final[frozenset[str]] = (
    frozenset(str(p) for p in TextualPredicate)
    | frozenset(str(p) for p in StructuralPredicate)
    | frozenset(str(p) for p in SEMANTIC_PREDICATES)
)


@dataclass(frozen=True)
class Signature:
    """What one predicate is allowed to connect."""

    subject: frozenset[NodeKind]
    object: frozenset[NodeKind]
    symmetric: bool
    definition: str


_P = NodeKind.PASSAGE
_F = NodeKind.FORMULA
_C = NodeKind.CONCEPT
_D = NodeKind.DEVATA

#: Domain and range for every non-semantic predicate. The semantic ones keep the
#: signatures the frozen ontology already gave them and are checked against it directly.
SIGNATURES: Final[dict[str, Signature]] = {
    str(TextualPredicate.EXACT_PARALLEL_OF): Signature(
        frozenset({_P}), frozenset({_P}), True, "Identical on the strongest reachable surface."
    ),
    str(TextualPredicate.NEAR_PARALLEL_OF): Signature(
        frozenset({_P}), frozenset({_P}), True, "Substantially the same verse, materially altered."
    ),
    str(TextualPredicate.VARIANT_OF): Signature(
        frozenset({_P}), frozenset({_P}), True, "Same verse, different editorial spelling."
    ),
    str(TextualPredicate.REUSES_TEXT_FROM): Signature(
        frozenset({_P}), frozenset({_P}), False, "Directed borrowing, where direction is known."
    ),
    str(TextualPredicate.SHARES_FORMULA_WITH): Signature(
        frozenset({_P}), frozenset({_P}), True, "Two passages share one or more formulas."
    ),
    str(StructuralPredicate.USES_FORMULA): Signature(
        frozenset({_P}), frozenset({_F}), False, "This passage contains this formula."
    ),
    str(StructuralPredicate.ABOUT_CONCEPT): Signature(
        frozenset({_P}), frozenset({_C}), False, "This passage concerns this concept."
    ),
    str(StructuralPredicate.BROADER_THAN): Signature(
        frozenset({_C}), frozenset({_C}), False, "The subject is a genuine superordinate."
    ),
    str(StructuralPredicate.HAS_ALIAS): Signature(
        frozenset({_C}), frozenset({_C}), False, "A surface form of this concept."
    ),
    str(StructuralPredicate.DEVATA_ASSOCIATED_WITH): Signature(
        frozenset({_D}), frozenset({_C}), False, "A deity and a concept that are not the same node."
    ),
}

#: Enrichment predicates that are declared and deliberately carry zero edges.
#:
#: Kept as *data*, not only as a docstring on the enum member, because the emptiness is
#: observed from the graph: an audit enumerating ``db.relationshipTypes()`` found a type
#: with no rows and correctly reported it as an undocumented dead filter option -- the
#: rationale existed, in a place nothing querying the database would look. The ontology
#: reference reads this map together with the domain layer's own.
UNPOPULATED_BY_DESIGN: Final[dict[str, str]] = {
    str(TextualPredicate.SHARES_FORMULA_WITH): (
        "The Formula hub already carries this relation losslessly: "
        "(a)-[:USES_FORMULA]->(f)<-[:USES_FORMULA]-(b) is the same fact in two hops. "
        "Materialising it would defeat the point of the hub -- the widest formula spans "
        "93 passages, so that one node alone would emit 4,278 edges and the layer would "
        "add 87,296 edges in place of 27,511. V3's FormulaFamily layer supersedes it "
        "further, grouping the formulas themselves rather than joining their passages."
    ),
}


#: Where each predicate the enrichment brief named actually ended up. Kept as data so a
#: reader can check the mapping instead of trusting a summary of it.
BRIEF_PREDICATE_MAPPING: Final[dict[str, str]] = {
    "EXACT_PARALLEL_OF": "EXACT_PARALLEL_OF (textual)",
    "NEAR_PARALLEL_OF": "NEAR_PARALLEL_OF (textual)",
    "VARIANT_OF": "VARIANT_OF (textual)",
    "REUSES_TEXT_FROM": "REUSES_TEXT_FROM (textual, directed)",
    "SHARES_FORMULA_WITH": "SHARES_FORMULA_WITH (textual) plus USES_FORMULA hub",
    "INVOKES": "INVOKES (frozen semantic whitelist)",
    "PRAISES": "PRAISES (frozen semantic whitelist)",
    "REQUESTS_FROM": "REQUESTS (frozen semantic whitelist; same relation, existing name)",
    "DESCRIBES": "DESCRIBES (frozen semantic whitelist)",
    "ASSOCIATED_WITH": "ASSOCIATED_WITH (frozen semantic whitelist)",
    "PROTECTS_FROM": "not emitted: no frozen predicate covers it and adding one is an "
    "ontology version bump the semantic freeze does not permit this session",
    "USED_FOR": "INVOLVES_RITUAL / INVOLVES_OFFERING / INVOLVES_SUBSTANCE, which say which "
    "kind of use and are already in the frozen whitelist",
    "CONTRASTS_WITH": "CONTRASTS_WITH (frozen semantic whitelist)",
    "ELABORATES": "not emitted: indistinguishable in practice from NEAR_PARALLEL_OF plus "
    "reading order, and the reading order is the interpretive part",
    "PARALLELS_IDEA_IN": "ABOUT_CONCEPT on both passages, which is queryable and carries "
    "evidence on each side rather than asserting an unevidenced link between them",
    "IDENTIFIES_WITH": "refused: the same claim as REPRESENTS, refused by name in the "
    "frozen ontology",
    "CAUSES": "refused by name in the frozen ontology, with a recorded reason",
}

#: Predicates the brief asked for that this layer declines to write, with the reason. Kept
#: separate from the mapping so a validation test can assert none of them is ever emitted.
REFUSED_PREDICATES: Final[dict[str, str]] = {
    "CAUSES": FORBIDDEN_PREDICATES[SemanticPredicate.CAUSES],
    "IDENTIFIES_WITH": (
        "An identity claim between a deity and a concept ('Agni is fire') is the "
        "REPRESENTS claim under another name, and the frozen ontology refuses it: it "
        "silently picks one commentarial reading. DEVATA_ASSOCIATED_WITH records the "
        "connection without asserting the identity."
    ),
    "PROTECTS_FROM": (
        "No frozen predicate covers it. Adding one is an ontology version bump, and the "
        "semantic layer is sealed at V3.2 while the human gold set is unannotated."
    ),
    "ELABORATES": (
        "Requires asserting which of two passages came first. The corpus does not record "
        "that, and inferring it from Mandala order is a scholarly position, not a fact."
    ),
}

assert REFUSED_PREDICATES.keys().isdisjoint(CONTROLLED_PREDICATES), (
    "a refused predicate must not also be writable"
)


def is_controlled(predicate: str) -> bool:
    """True when ``predicate`` is a name this layer is permitted to write."""
    return predicate in CONTROLLED_PREDICATES


def check_signature(predicate: str, subject: NodeKind, object_: NodeKind) -> None:
    """Raise if an edge violates its predicate's domain/range constraint."""
    if predicate not in CONTROLLED_PREDICATES:
        reason = REFUSED_PREDICATES.get(predicate)
        detail = f": {reason}" if reason else ""
        raise ValueError(f"{predicate} is not a controlled enrichment predicate{detail}")
    signature = SIGNATURES.get(predicate)
    if signature is None:
        # A semantic predicate. Its subject is always a passage; its object types are
        # governed by the frozen ontology's own rule, checked where the assertion is built.
        if subject is not NodeKind.PASSAGE:
            raise ValueError(f"{predicate}: semantic assertions are about passages, not {subject}")
        return
    if subject not in signature.subject:
        raise ValueError(f"{predicate}: subject {subject} not in {sorted(signature.subject)}")
    if object_ not in signature.object:
        raise ValueError(f"{predicate}: object {object_} not in {sorted(signature.object)}")


#: Veda pairs where the corpus's own structure establishes which text borrowed from which.
#: The Samaveda is, by its own construction, a songbook of Rigvedic verses set to melody --
#: this is not a similarity finding but what the Samaveda is. Every other pair is left
#: undirected, because asserting a direction there would be a chronology claim.
ESTABLISHED_REUSE: Final[dict[tuple[str, str], str]] = {
    ("SV", "RV"): (
        "The Samaveda Arcika is a collection of Rigvedic verses arranged for chanting; "
        "its own tradition identifies the Rigveda as the source of its text."
    ),
}


def reuse_direction(veda_a: str, veda_b: str) -> tuple[str, str, str] | None:
    """Return ``(borrower, source, reason)`` when direction is established, else ``None``."""
    reason = ESTABLISHED_REUSE.get((veda_a, veda_b))
    if reason:
        return veda_a, veda_b, reason
    reason = ESTABLISHED_REUSE.get((veda_b, veda_a))
    if reason:
        return veda_b, veda_a, reason
    return None
