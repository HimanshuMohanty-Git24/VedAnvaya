"""The controlled vocabulary a semantic extraction may use, and what may be done with it.

Three things are fixed here before any model is asked for anything:

**Node types.** A semantic node is a reusable knowledge entity, not a token. Every
ordinary noun in the Rigveda is not a ``CONCEPT``; ``soma``, ``rta`` and ``the Sindhu``
are. The list is deliberately shared across the four Vedas, because a type invented for
one text will be wrong for the next.

**Predicates.** A closed whitelist. Free-form relation names are the fastest way to turn
a knowledge graph into a synonym pile, and the ones most worth having (``SYMBOLIZES``,
``REPRESENTS``, ``IS_GOD_OF``) are exactly the ones a model will produce most
confidently and least defensibly. Those are named here so they can be *rejected by
name*, rather than left out and silently re-invented.

**What each predicate may connect, and on what terms.** A predicate carries an
interpretation risk, a subject/object type signature, and its own acceptance rule. There
is no global confidence threshold, because there is no single question being answered.

Versioned together: an extraction records ``ONTOLOGY_VERSION``, and a candidate produced
under one version is not silently comparable with one produced under another.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

ONTOLOGY_VERSION = "rigveda-semantic-ontology-v1"
ACCEPTANCE_POLICY_VERSION = "rigveda-semantic-acceptance-policy-v1"


class SemanticNodeType(StrEnum):
    """Categories a semantic entity may belong to.

    Chosen to be usable across the four Vedas, not tuned to the Rigveda. Adding a type
    is an ontology version bump, because every stored candidate names the version it was
    produced under.
    """

    CONCEPT = "CONCEPT"
    PHILOSOPHICAL_CONCEPT = "PHILOSOPHICAL_CONCEPT"
    THEME = "THEME"
    RITUAL = "RITUAL"
    OFFERING = "OFFERING"
    SUBSTANCE = "SUBSTANCE"
    PLANT = "PLANT"
    ANIMAL = "ANIMAL"
    OBJECT = "OBJECT"
    PLACE = "PLACE"
    RIVER = "RIVER"
    REGION = "REGION"
    NATURAL_PHENOMENON = "NATURAL_PHENOMENON"
    COSMIC_ENTITY = "COSMIC_ENTITY"
    ACTION = "ACTION"
    QUALITY = "QUALITY"
    STATE = "STATE"


#: ``PHILOSOPHICAL_CONCEPT`` is a subtype of ``CONCEPT``, not a parallel bucket. It is
#: available so that ṛta, satya, vāc and the rest are not filed next to "cattle", but it
#: is not seeded with entities: nothing in this repository asserts that ``RTA`` exists
#: until an extraction proposes it and a reviewer accepts it. Hard-coding the famous
#: concepts would be writing the answer into the question.
CONCEPT_TYPES: frozenset[SemanticNodeType] = frozenset(
    {SemanticNodeType.CONCEPT, SemanticNodeType.PHILOSOPHICAL_CONCEPT, SemanticNodeType.THEME}
)

PLACE_TYPES: frozenset[SemanticNodeType] = frozenset(
    {SemanticNodeType.PLACE, SemanticNodeType.RIVER, SemanticNodeType.REGION}
)

MATERIAL_TYPES: frozenset[SemanticNodeType] = frozenset(
    {
        SemanticNodeType.OFFERING,
        SemanticNodeType.SUBSTANCE,
        SemanticNodeType.PLANT,
        SemanticNodeType.ANIMAL,
        SemanticNodeType.OBJECT,
    }
)


class SemanticPredicate(StrEnum):
    """Every relation name an extraction may emit, and the ones it may not.

    The forbidden members exist so that a proposal naming one is rejected as a *policy*
    decision with a recorded reason, instead of failing schema validation as an unknown
    string. The difference matters when reading a rejection report.
    """

    # --- allowed in v1 -----------------------------------------------------------
    EXPRESSES = "EXPRESSES"
    DESCRIBES = "DESCRIBES"
    PRAISES = "PRAISES"
    INVOKES = "INVOKES"
    REQUESTS = "REQUESTS"
    ASSOCIATED_WITH = "ASSOCIATED_WITH"
    INVOLVES_RITUAL = "INVOLVES_RITUAL"
    INVOLVES_OFFERING = "INVOLVES_OFFERING"
    INVOLVES_SUBSTANCE = "INVOLVES_SUBSTANCE"
    REFERS_TO_PLACE = "REFERS_TO_PLACE"
    REFERS_TO_NATURAL_PHENOMENON = "REFERS_TO_NATURAL_PHENOMENON"
    DESCRIBES_ACTION = "DESCRIBES_ACTION"
    HAS_THEME = "HAS_THEME"
    CONTRASTS_WITH = "CONTRASTS_WITH"

    # --- named so they can be refused by name, never emitted ---------------------
    SYMBOLIZES = "SYMBOLIZES"
    REPRESENTS = "REPRESENTS"
    IS_GOD_OF = "IS_GOD_OF"
    MEANS = "MEANS"
    CAUSES = "CAUSES"


class InterpretationRisk(StrEnum):
    """How much of a claim comes from the text and how much from the reader."""

    LOW = "LOW_INTERPRETATION"
    MEDIUM = "MEDIUM_INTERPRETATION"
    HIGH = "HIGH_INTERPRETATION"


class Explicitness(StrEnum):
    """How the model says it got there. Self-reported, and validated against evidence."""

    EXPLICIT = "EXPLICIT"
    STRONG_INFERENCE = "STRONG_INFERENCE"
    INTERPRETIVE = "INTERPRETIVE"


class SemanticSubjectKind(StrEnum):
    """Textual units a semantic assertion may be about."""

    MANTRA = "MANTRA"
    SUKTA = "SUKTA"


#: Object families a predicate signature can name. ``CANONICAL_ENTITY`` means an existing
#: Devatā or Ṛṣi from the deterministic registry; the rest are semantic node types.
CANONICAL_ENTITY = "CANONICAL_ENTITY"


@dataclass(frozen=True)
class PredicateRule:
    """Everything the pipeline is allowed to know about one predicate."""

    predicate: SemanticPredicate
    risk: InterpretationRisk
    definition: str
    subject_kinds: frozenset[SemanticSubjectKind]
    #: Node types the object may take. ``CANONICAL_ENTITY`` is admitted separately.
    object_types: frozenset[SemanticNodeType] = field(default_factory=frozenset)
    allows_canonical_entity: bool = False
    #: Explicitness levels that may reach ``AUTO_ACCEPTED`` *if* the predicate has been
    #: unlocked by measured gold precision. Empty means human review always.
    auto_acceptable: frozenset[Explicitness] = field(default_factory=frozenset)
    #: A floor, never a reason on its own. See :func:`decide_status`.
    min_confidence: float = 0.0
    allowed: bool = True
    refusal_reason: str = ""


def _rule(
    predicate: SemanticPredicate,
    risk: InterpretationRisk,
    definition: str,
    *,
    subjects: frozenset[SemanticSubjectKind] = frozenset(
        {SemanticSubjectKind.MANTRA, SemanticSubjectKind.SUKTA}
    ),
    objects: frozenset[SemanticNodeType] = frozenset(),
    canonical: bool = False,
    auto: frozenset[Explicitness] = frozenset(),
    min_confidence: float = 0.0,
) -> PredicateRule:
    return PredicateRule(
        predicate=predicate,
        risk=risk,
        definition=definition,
        subject_kinds=subjects,
        object_types=objects,
        allows_canonical_entity=canonical,
        auto_acceptable=auto,
        min_confidence=min_confidence,
    )


_ALL_NODE_TYPES = frozenset(SemanticNodeType)

PREDICATE_RULES: dict[SemanticPredicate, PredicateRule] = {
    rule.predicate: rule
    for rule in (
        # --- LOW: the text does the work. The reader is reporting, not deciding. ---
        _rule(
            SemanticPredicate.PRAISES,
            InterpretationRisk.LOW,
            "The passage extols the object. Distinct from HAS_DEVATA: praise in the "
            "words, not assignment by the Anukramaṇī.",
            canonical=True,
            objects=CONCEPT_TYPES | {SemanticNodeType.COSMIC_ENTITY},
            auto=frozenset({Explicitness.EXPLICIT}),
            min_confidence=0.75,
        ),
        _rule(
            SemanticPredicate.INVOKES,
            InterpretationRisk.LOW,
            "The passage calls on the object, typically vocatively or imperatively.",
            canonical=True,
            objects=frozenset({SemanticNodeType.COSMIC_ENTITY}),
            auto=frozenset({Explicitness.EXPLICIT}),
            min_confidence=0.75,
        ),
        _rule(
            SemanticPredicate.REQUESTS,
            InterpretationRisk.LOW,
            "The passage asks for the object: wealth, offspring, protection, rain.",
            objects=frozenset(
                {
                    SemanticNodeType.CONCEPT,
                    SemanticNodeType.QUALITY,
                    SemanticNodeType.STATE,
                    SemanticNodeType.OBJECT,
                    SemanticNodeType.SUBSTANCE,
                    SemanticNodeType.ACTION,
                    SemanticNodeType.NATURAL_PHENOMENON,
                }
            ),
            auto=frozenset({Explicitness.EXPLICIT}),
            min_confidence=0.75,
        ),
        _rule(
            SemanticPredicate.REFERS_TO_PLACE,
            InterpretationRisk.LOW,
            "The passage names a place, river or region.",
            objects=PLACE_TYPES,
            auto=frozenset({Explicitness.EXPLICIT}),
            min_confidence=0.75,
        ),
        _rule(
            SemanticPredicate.REFERS_TO_NATURAL_PHENOMENON,
            InterpretationRisk.LOW,
            "The passage names a natural phenomenon: dawn, thunder, flood, drought.",
            objects=frozenset(
                {SemanticNodeType.NATURAL_PHENOMENON, SemanticNodeType.COSMIC_ENTITY}
            ),
            auto=frozenset({Explicitness.EXPLICIT}),
            min_confidence=0.75,
        ),
        _rule(
            SemanticPredicate.INVOLVES_OFFERING,
            InterpretationRisk.LOW,
            "The passage names something offered. The object must be an offering or a "
            "substance; 'the ritual involves devotion' is not this predicate.",
            objects=frozenset(
                {
                    SemanticNodeType.OFFERING,
                    SemanticNodeType.SUBSTANCE,
                    SemanticNodeType.PLANT,
                    SemanticNodeType.ANIMAL,
                }
            ),
            auto=frozenset({Explicitness.EXPLICIT}),
            min_confidence=0.75,
        ),
        _rule(
            SemanticPredicate.INVOLVES_SUBSTANCE,
            InterpretationRisk.LOW,
            "The passage names a material substance, offered or not.",
            objects=MATERIAL_TYPES,
            auto=frozenset({Explicitness.EXPLICIT}),
            min_confidence=0.75,
        ),
        # --- MEDIUM: the reader is choosing a description. Review by default. ------
        _rule(
            SemanticPredicate.DESCRIBES,
            InterpretationRisk.MEDIUM,
            "The passage depicts the object without necessarily praising or invoking it.",
            canonical=True,
            objects=_ALL_NODE_TYPES,
            min_confidence=0.7,
        ),
        _rule(
            SemanticPredicate.DESCRIBES_ACTION,
            InterpretationRisk.MEDIUM,
            "The passage narrates an action: slaying Vṛtra, releasing the waters.",
            objects=frozenset({SemanticNodeType.ACTION}),
            min_confidence=0.7,
        ),
        _rule(
            SemanticPredicate.INVOLVES_RITUAL,
            InterpretationRisk.MEDIUM,
            "The passage takes place in, or refers to, a named ritual act.",
            objects=frozenset({SemanticNodeType.RITUAL, SemanticNodeType.ACTION}),
            min_confidence=0.7,
        ),
        _rule(
            SemanticPredicate.EXPRESSES,
            InterpretationRisk.MEDIUM,
            "The passage voices a quality, state or attitude: awe, fear, confidence.",
            objects=frozenset(
                {SemanticNodeType.QUALITY, SemanticNodeType.STATE, SemanticNodeType.CONCEPT}
            ),
            min_confidence=0.7,
        ),
        _rule(
            SemanticPredicate.HAS_THEME,
            InterpretationRisk.MEDIUM,
            "The passage is about a theme. A summary judgement, and never auto-accepted.",
            objects=CONCEPT_TYPES,
            min_confidence=0.8,
        ),
        _rule(
            SemanticPredicate.CONTRASTS_WITH,
            InterpretationRisk.MEDIUM,
            "The passage sets two things against each other in its own words.",
            canonical=True,
            objects=_ALL_NODE_TYPES,
            min_confidence=0.8,
        ),
        _rule(
            SemanticPredicate.ASSOCIATED_WITH,
            InterpretationRisk.MEDIUM,
            "A link the passage supports but does not characterise. The weakest allowed "
            "predicate and the one most likely to be a shrug; review-heavy on purpose.",
            canonical=True,
            objects=_ALL_NODE_TYPES,
            min_confidence=0.85,
        ),
    )
}

#: Metaphysical and identity claims. These are refusals with reasons, not omissions.
FORBIDDEN_PREDICATES: dict[SemanticPredicate, str] = {
    SemanticPredicate.SYMBOLIZES: (
        "A symbolism claim is a reading of the text, not a report of it, and the "
        "Rigveda has several incompatible commentarial traditions of reading it. "
        "Recording one as a graph edge would silently pick a school."
    ),
    SemanticPredicate.REPRESENTS: (
        "Same objection as SYMBOLIZES, and additionally ambiguous between 'stands for' "
        "and 'is an instance of'."
    ),
    SemanticPredicate.IS_GOD_OF: (
        "A domain assignment ('Agni is the god of fire') is systematised theology, "
        "largely post-Vedic. The Rigveda's own deity scope is given by HAS_DEVATA and "
        "by what the hymns say, both of which are already recorded."
    ),
    SemanticPredicate.MEANS: (
        "A meaning claim about Sanskrit made from an English translation is a claim "
        "about the translator. Lexical semantics belongs to a lexicon with citations."
    ),
    SemanticPredicate.CAUSES: (
        "Causal claims in a mythological narrative are not the same as causal claims "
        "about the world, and an edge cannot carry the difference."
    ),
}

ALLOWED_PREDICATES: frozenset[SemanticPredicate] = frozenset(PREDICATE_RULES)

assert ALLOWED_PREDICATES.isdisjoint(FORBIDDEN_PREDICATES), "a predicate cannot be both"
assert ALLOWED_PREDICATES | frozenset(FORBIDDEN_PREDICATES) == frozenset(SemanticPredicate), (
    "every predicate in the enum must be either allowed or explicitly refused"
)


def predicate_rule(predicate: SemanticPredicate) -> PredicateRule | None:
    """The rule for an allowed predicate, or ``None`` if it is refused."""
    return PREDICATE_RULES.get(predicate)


def object_type_is_valid(rule: PredicateRule, node_type: SemanticNodeType) -> bool:
    return node_type in rule.object_types


#: Predicates whose measured gold precision has met the readiness target and which may
#: therefore reach ``AUTO_ACCEPTED``. Empty by construction: nothing is unlocked until an
#: evaluation run says so, and the evaluation is what fills this set at call time.
NO_PREDICATE_UNLOCKED: frozenset[SemanticPredicate] = frozenset()
