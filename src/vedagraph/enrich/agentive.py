"""Who does what, to whom, with what, for whom -- derived by rule from the annotation.

The V2 graph's action layer was five noun entities reached by a mention edge, and
``PERFORMS_ACTION`` was declared and empty. The stated reason was that no evidence source
in the corpus supports "Indra performs *slaying*" as a deterministic edge. That was wrong,
and this module is the correction: the Rigveda carries a manual scholarly morphological
annotation in which **32,029 tokens are verb forms** marked for root, person, number,
tense, mood and voice, and **8,025 nominal tokens are vocatives**. Between them they
support an agentive layer that is derived, reproducible, and grounded in a source rather
than extracted by a model.

**The rule, and it is deliberately narrow.**

Locality is one *pada* -- one metrical line -- because a whole mantra routinely contains
several clauses and one pada usually contains one. Within a pada that has **exactly one
finite verb**:

*The asserted frame.* A third-person finite verb plus **exactly one** nominative deity
whose number agrees with it. ``índraḥ cetati ártham`` -- Indra perceives the purpose.

*The requested frame.* A second-person finite verb in an imperative, optative,
subjunctive, injunctive or precative, plus **exactly one** vocative deity. ``índra yāhi``
-- "Indra, come!". This is the distinction the brief asks for under ``REQUESTS_FROM``, and
it is not an interpretation of the verse: a second-person imperative addressed to a
vocative is grammatically a request, and the mood is in the annotation.

A second-person *indicative* addressed to a vocative deity is the asserted frame, not the
requested one -- ``ágne ... kariṣyási``, "O Agni, what thou wilt do" -- because the verse
states the act rather than asking for it. The deity is the agent either way; the frame
records which.

Roles come from case within the same pada: accusative gives the patient, instrumental the
instrument, dative the beneficiary, locative the location. A role absent from the line is
absent from the assertion and is never guessed.

**What this is not, and the bound matters more than the yield.** The annotation is
morphological. There is no dependency parse, no clause boundary and no subject-verb link
anywhere in it. What the rule above establishes is *co-location plus agreement*: this line
contains a nominative singular deity and a third-person singular finite verb. In a
one-clause line that is the subject of that verb. In a line that packs two clauses it may
not be. The "exactly one" conditions exist to make that failure rare rather than to
pretend it cannot happen, and the precision of the layer is measured by hand-reading a
sample rather than asserted from the rule. Every assertion carries the verb, its
morphology and the line it was read from, so any single one of them can be checked in
about ten seconds.

Predicates come from :mod:`data/registry/action_root_map.yaml`, which maps verbal roots
onto the closed vocabulary in ``data/registry/action_predicates.yaml``. A root with no
mapping produces an assertion marked ``UNMAPPED_ROOT`` rather than no assertion, so the
size of the gap is visible in the graph instead of only in the registry.
"""

from __future__ import annotations

import pathlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

import yaml

from vedagraph.enrich.morphology import (
    ANNOTATION_METHOD,
    ANNOTATION_SOURCE_ID,
    POS_INVARIABLE,
    REQUEST_MOODS,
    AnnotatedToken,
    Annotation,
)
from vedagraph.enrich.provenance import (
    AssertionState,
    EvidenceSpan,
    Provenance,
    RunReport,
    TrustClass,
    run_id,
    stable_id,
)

PREDICATE_REGISTRY: Final = pathlib.Path("data") / "registry" / "action_predicates.yaml"
ROOT_MAP_REGISTRY: Final = pathlib.Path("data") / "registry" / "action_root_map.yaml"

_STAGE: Final = "agentive-assertions"
_METHOD: Final = "agentive-morphology-v1"

#: The verse states that the agent does this.
FRAME_ASSERTED: Final = "ASSERTED"
#: The verse asks the agent to do this.
FRAME_REQUESTED: Final = "REQUESTED"

#: A root the mapping registry does not cover. Kept as a predicate value so the gap is
#: countable in the graph rather than invisible outside the registry.
UNMAPPED: Final = "UNMAPPED_ROOT"

#: Case -> role. The whole of the argument-structure rule, and its narrowness is the
#: point: these are the four cases whose Rigvedic function is stable enough to read
#: without a parse. Genitive and ablative are deliberately absent -- a genitive in a pada
#: modifies some noun in it, and which noun is exactly the question morphology cannot
#: answer.
ROLE_BY_CASE: Final[Mapping[str, str]] = {
    "ACC": "PATIENT",
    "INS": "INSTRUMENT",
    "DAT": "BENEFICIARY",
    "LOC": "LOCATION",
}

#: Scored the same for both frames. A score here says only "this rule fired", and the
#: rule's precision is a measured property of the layer, not of the row.
_SCORE: Final = 0.85


class ActionRegistryError(ValueError):
    """The action predicate vocabulary or root mapping is unusable."""


@dataclass(frozen=True)
class RootMapping:
    """One verbal root's place in the closed predicate vocabulary."""

    lemma_label: str
    lemma_id: str
    root_folded: str
    predicate: str
    confidence: str
    tokens: int = 0
    gloss: str = ""
    secondary_predicate: str = ""
    disambiguation: str = ""
    note: str = ""


@dataclass(frozen=True)
class ActionVocabulary:
    """The closed predicate set plus the root mapping into it.

    Keyed on the **accented lemma label**, not on the folded root, and that is a
    correctness requirement rather than a preference. The annotation distinguishes 702
    lemma labels which fold onto only 662 keys, so **22 folded keys carry two roots
    each** -- and they are precisely the roots that matter here:

    ========  =======================================  ==========================
    folded    labels it collapses                      predicates they map to
    ========  =======================================  ==========================
    ``pā``    ``√pā- 1`` / ``√pā- 2``                  PROTECTS / DRINKS
    ``vid``   ``√vid- 1`` / ``√vid- 2``                SEEKS / PERCEIVES
    ``as``    ``√as- 1`` / ``√as- 2``                  IS_OR_BECOMES / unmapped
    ``i``     ``√i- 1`` / ``√i- 2``                    MOVES_TO / LEADS
    ``yā``    ``√yā- 1`` / ``√yā- 2``                  MOVES_TO / SEEKS
    ``dhā``   ``√dhā- 1`` / ``√dhā- 2``                ESTABLISHES / DRINKS
    ========  =======================================  ==========================

    Keying on the folded root would file all Soma-drinking and all divine protection
    under one predicate, and merge "Indra *is*" with "Indra *shoots*". The imperative
    ``pāhi`` occurs in **both** ``pā`` roots' token sets, so no amount of string work
    separates them; only the label does.
    """

    predicates: frozenset[str]
    #: predicate -> the roles its frame expects. Read for reporting, not enforcement:
    #: a verse that supplies no instrument does not make the predicate wrong.
    argument_frames: Mapping[str, tuple[str, ...]]
    #: accented lemma label -> its mapping. The only correct key; see the class docstring.
    by_label: Mapping[str, RootMapping]
    #: Predicates declared in the vocabulary that no root maps onto. A finding, reported
    #: rather than hidden, because a declared-and-empty predicate misreports an absence of
    #: evidence as an absence of modelling.
    unused_predicates: tuple[str, ...]

    def predicate_for(self, lemma_label: str) -> tuple[str, str]:
        """Return ``(predicate, confidence)`` for a lemma label, or the unmapped marker."""
        mapping = self.by_label.get(lemma_label)
        if mapping is None:
            return UNMAPPED, "NONE"
        return mapping.predicate, mapping.confidence


def load_vocabulary(project_root: pathlib.Path) -> ActionVocabulary:
    """Read the closed predicate vocabulary and the root mapping, and check they agree."""
    predicate_path = project_root / PREDICATE_REGISTRY
    if not predicate_path.exists():
        raise ActionRegistryError(f"predicate vocabulary not found: {predicate_path}")
    predicate_doc = yaml.safe_load(predicate_path.read_text(encoding="utf-8"))
    predicates = {str(row["predicate"]) for row in predicate_doc["predicates"]}
    frames = {
        str(row["predicate"]): tuple(str(role) for role in row.get("argument_frame") or ())
        for row in predicate_doc["predicates"]
    }

    root_path = project_root / ROOT_MAP_REGISTRY
    if not root_path.exists():
        raise ActionRegistryError(
            f"root mapping not found: {root_path}. The agentive layer cannot be built "
            "without it, and defaulting every root to a predicate would invent a "
            "semantics the registry never authorised."
        )
    root_doc = yaml.safe_load(root_path.read_text(encoding="utf-8"))

    by_label: dict[str, RootMapping] = {}
    for row in root_doc.get("roots") or ():
        predicate = str(row.get("predicate") or UNMAPPED)
        label = str(row.get("lemma_label") or "")
        if not label:
            raise ActionRegistryError(f"root row without a lemma_label: {row!r}")
        if predicate == UNMAPPED:
            continue
        if predicate not in predicates:
            raise ActionRegistryError(
                f"root {label!r} maps to {predicate!r}, which is not in the closed "
                "vocabulary. The vocabulary is the contract; a mapping may not widen it."
            )
        secondary = str(row.get("secondary_predicate") or "")
        if secondary and secondary not in predicates:
            raise ActionRegistryError(
                f"root {label!r} has secondary predicate {secondary!r}, which is not in "
                "the closed vocabulary"
            )
        if label in by_label:
            raise ActionRegistryError(f"lemma label {label!r} mapped twice")
        by_label[label] = RootMapping(
            lemma_label=label,
            lemma_id=str(row.get("lemma_id") or ""),
            root_folded=str(row.get("root_folded") or ""),
            predicate=predicate,
            confidence=str(row.get("confidence") or "UNSPECIFIED"),
            tokens=int(row.get("tokens") or 0),
            gloss=str(row.get("gloss") or ""),
            secondary_predicate=secondary,
            disambiguation=str(row.get("disambiguation") or ""),
            note=str(row.get("note") or ""),
        )

    used = {mapping.predicate for mapping in by_label.values()} | {
        mapping.secondary_predicate for mapping in by_label.values() if mapping.secondary_predicate
    }
    return ActionVocabulary(
        predicates=frozenset(predicates),
        argument_frames=frames,
        by_label=by_label,
        unused_predicates=tuple(sorted(predicates - used)),
    )


@dataclass(frozen=True)
class RoleFiller:
    """One argument of one assertion, as the line spells it."""

    role: str
    surface: str
    lemma: str
    case: str

    def as_dict(self) -> dict[str, str]:
        return {"role": self.role, "surface": self.surface, "lemma": self.lemma, "case": self.case}


@dataclass
class AgentiveAssertion:
    """One agentive fact read off one metrical line."""

    passage_key: str
    veda: str
    pada: str
    devata_id: str
    frame: str
    predicate: str
    predicate_confidence: str
    root: str
    root_label: str
    verb_surface: str
    verb_features: str
    agent_surface: str
    agent_case: str
    #: True when the verb is dual or plural and the named agent is singular, so the verse
    #: has other agents this assertion does not name. RV 1.2.5 `vāyav índraś ca cetathaḥ`
    #: -- "Vāyu and Indra, ye perceive" -- is a dual verb with one vocative, and the
    #: assertion "Vāyu perceives" is true but incomplete. Recorded rather than dropped,
    #: because the claim is not wrong; a query that needs sole agency can filter on it.
    agent_incomplete: bool
    roles: tuple[RoleFiller, ...]
    preverbs: tuple[str, ...]
    provenance: Provenance

    @property
    def assertion_id(self) -> str:
        return stable_id(
            "AGENTIVE",
            self.passage_key,
            self.pada,
            self.devata_id,
            self.root,
            self.verb_surface,
        )

    def as_row(self) -> dict[str, Any]:
        return {
            "assertion_id": self.assertion_id,
            "passage_key": self.passage_key,
            "veda": self.veda,
            "pada": self.pada,
            "devata_id": self.devata_id,
            "frame": self.frame,
            "predicate": self.predicate,
            "predicate_confidence": self.predicate_confidence,
            "root": self.root,
            "root_label": self.root_label,
            "verb_surface": self.verb_surface,
            "verb_features": self.verb_features,
            "agent_surface": self.agent_surface,
            "agent_case": self.agent_case,
            "agent_incomplete": self.agent_incomplete,
            "roles": [filler.as_dict() for filler in self.roles],
            "role_count": len(self.roles),
            "patient": next((f.surface for f in self.roles if f.role == "PATIENT"), ""),
            "instrument": next((f.surface for f in self.roles if f.role == "INSTRUMENT"), ""),
            "beneficiary": next((f.surface for f in self.roles if f.role == "BENEFICIARY"), ""),
            "location": next((f.surface for f in self.roles if f.role == "LOCATION"), ""),
            "preverbs": list(self.preverbs),
            **self.provenance.as_edge_properties(),
        }


def _features(verb: AnnotatedToken) -> str:
    parts = [
        value for value in (verb.person, verb.number, verb.tense, verb.mood, verb.voice) if value
    ]
    if verb.secondary_conjugation:
        parts.append(verb.secondary_conjugation)
    return "/".join(parts)


def _roles(tokens: Sequence[AnnotatedToken], agent: AnnotatedToken) -> tuple[RoleFiller, ...]:
    """Argument fillers in this line, by case, excluding the agent itself."""
    fillers: list[RoleFiller] = []
    for token in tokens:
        if token is agent or token.case is None:
            continue
        role = ROLE_BY_CASE.get(token.case)
        if role is None:
            continue
        if token.part_of_speech not in {"nominal stem", "pronoun"}:
            continue
        fillers.append(
            RoleFiller(
                role=role,
                surface=token.surface_form,
                lemma=token.normalized_lemma,
                case=token.case,
            )
        )
    return tuple(fillers)


def _preverbs(tokens: Sequence[AnnotatedToken], verb: AnnotatedToken) -> tuple[str, ...]:
    """Local particles **adjacent** to this verb, in sequence order.

    Recorded as a qualifier rather than folded into the predicate, because a preverb
    genuinely changes a verb's sense -- ``ā-gam`` "come" against ``gam`` "go" -- and the
    annotation tags it as a separate token, so the root alone cannot see it. On exactly
    one root of consequence the predicate *inverts*: bare ``vṛ-`` closes and ``apa-vṛ-``
    opens, so an extractor ignoring the particle reports Indra binding the waters he
    released.

    **Selected by the annotation's own ``local particle`` feature and bound by adjacency**,
    not by line membership. Both halves were wrong first: line membership reported three
    particles for a root that carries the flag on 3 of its 106 tokens, and adjacency alone
    reported ``ca`` "and" as a preverb because a conjunction sits next to a verb as
    readily as ``ā`` "hither" does. The annotation marks ``local particle`` on the
    *particle's own* token, and a line routinely holds particles belonging to other verbs
    -- three were being reported for a root that carries the flag on 3 of its 106
    tokens. So only a particle
    immediately before or after the verb in ``sequence`` order is attributed to it. That
    still is not a parse: Vedic tmesis separates preverb from verb freely, so this
    under-reports rather than over-reports, which is the right direction for a qualifier
    a reader may act on.
    """
    ordered = sorted(tokens, key=lambda token: token.sequence)
    index = next((i for i, token in enumerate(ordered) if token is verb), None)
    if index is None:
        return ()
    neighbours = [
        ordered[position] for position in (index - 1, index + 1) if 0 <= position < len(ordered)
    ]
    return tuple(
        token.surface_form
        for token in neighbours
        if token.part_of_speech == POS_INVARIABLE
        and token.local_particle is not None
        and token.surface_form
    )


def _line_quote(tokens: Sequence[AnnotatedToken]) -> str:
    return " ".join(token.surface_form for token in tokens if token.surface_form)


def extract_agentive(
    annotation: Annotation,
    vocabulary: ActionVocabulary,
    deity_lemmas: Mapping[str, str],
) -> tuple[list[AgentiveAssertion], RunReport]:
    """Read every agentive assertion the annotation supports.

    ``deity_lemmas`` maps a folded lemma to a Devata entity key -- the same mapping the
    theonym layer uses, passed in rather than re-derived so the two layers cannot disagree
    about which lemma is which god.
    """
    identity = run_id(_STAGE, len(annotation.tokens), len(vocabulary.by_label), len(deity_lemmas))
    report = RunReport(stage=_STAGE)
    assertions: list[AgentiveAssertion] = []
    frame_counts: dict[str, int] = {FRAME_ASSERTED: 0, FRAME_REQUESTED: 0}
    predicate_counts: dict[str, int] = {}
    unmapped_roots: dict[str, int] = {}
    deity_counts: dict[str, int] = {}
    incomplete_agents = 0

    for (passage_key, pada), tokens in annotation.by_pada.items():
        finite = [token for token in tokens if token.is_finite_verb]
        if not finite:
            report.reject("pada_has_no_finite_verb")
            continue
        if len(finite) > 1:
            report.reject("pada_has_multiple_finite_verbs")
            continue
        verb = finite[0]

        nominatives = [
            token
            for token in tokens
            if token.is_nominal and token.case == "NOM" and token.folded_lemma in deity_lemmas
        ]
        vocatives = [
            token
            for token in tokens
            if token.is_nominal and token.is_vocative and token.folded_lemma in deity_lemmas
        ]

        agent: AnnotatedToken | None = None
        frame = ""
        if verb.person == "3" and len(nominatives) == 1:
            if nominatives[0].number != verb.number:
                report.reject("nominative_disagrees_with_verb_number")
            else:
                agent, frame = nominatives[0], FRAME_ASSERTED
        elif verb.person == "2" and len(vocatives) == 1:
            agent = vocatives[0]
            frame = FRAME_REQUESTED if verb.mood in REQUEST_MOODS else FRAME_ASSERTED
        elif verb.person == "3" and len(nominatives) > 1:
            report.reject("pada_has_multiple_nominative_deities")
        elif verb.person == "2" and len(vocatives) > 1:
            report.reject("pada_has_multiple_vocative_deities")
        else:
            report.reject("no_deity_in_the_grammatical_position_the_verb_requires")

        if agent is None:
            continue

        predicate, confidence = vocabulary.predicate_for(verb.lemma_label)
        if predicate == UNMAPPED:
            unmapped_roots[verb.lemma_label] = unmapped_roots.get(verb.lemma_label, 0) + 1

        devata_id = deity_lemmas[agent.folded_lemma]
        provenance = Provenance(
            trust=TrustClass.DETERMINISTIC_DERIVED,
            method=f"{_METHOD}:{frame.lower()}",
            score=_SCORE,
            evidence=(
                EvidenceSpan(
                    locator=f"{passage_key}:{pada}",
                    surface=f"{ANNOTATION_SOURCE_ID} {ANNOTATION_METHOD}",
                    quote=_line_quote(tokens),
                ),
            ),
            state=AssertionState.ACCEPTED,
            run_id=identity,
            notes=(
                f"agent {agent.surface_form} ({agent.case}/{agent.number}); "
                f"verb {verb.surface_form} ({verb.lemma_label}; {_features(verb)}); "
                "one finite verb in this pada, one deity in the required case"
            ),
        )
        assertions.append(
            AgentiveAssertion(
                passage_key=passage_key,
                veda="RV",
                pada=pada,
                devata_id=devata_id,
                frame=frame,
                predicate=predicate,
                predicate_confidence=confidence,
                root=verb.folded_lemma,
                root_label=verb.lemma_label,
                verb_surface=verb.surface_form,
                verb_features=_features(verb),
                agent_surface=agent.surface_form,
                agent_case=agent.case or "",
                agent_incomplete=(verb.number in {"DU", "PL"} and agent.number == "SG"),
                roles=_roles(tokens, agent),
                preverbs=_preverbs(tokens, verb),
                provenance=provenance,
            )
        )
        if assertions[-1].agent_incomplete:
            incomplete_agents += 1
        frame_counts[frame] += 1
        predicate_counts[predicate] = predicate_counts.get(predicate, 0) + 1
        deity_counts[devata_id] = deity_counts.get(devata_id, 0) + 1

    assertions.sort(key=lambda row: (row.passage_key, row.pada, row.devata_id, row.root))
    report.produced = len(assertions)
    report.notes = {
        "padas_examined": len(annotation.by_pada),
        "frames": dict(sorted(frame_counts.items())),
        "agent_incomplete": incomplete_agents,
        "predicates": dict(sorted(predicate_counts.items(), key=lambda kv: -kv[1])),
        "unmapped_roots": dict(sorted(unmapped_roots.items(), key=lambda kv: -kv[1])[:40]),
        "unmapped_assertions": sum(unmapped_roots.values()),
        "deities": dict(sorted(deity_counts.items(), key=lambda kv: -kv[1])),
        "distinct_deities": len(deity_counts),
        "distinct_roots": len({row.root for row in assertions}),
        "passages_covered": len({row.passage_key for row in assertions}),
        "role_fill": {
            role: sum(1 for row in assertions if any(f.role == role for f in row.roles))
            for role in sorted(set(ROLE_BY_CASE.values()))
        },
        "vocabulary_predicates_with_no_root": list(vocabulary.unused_predicates),
    }
    return assertions, report
