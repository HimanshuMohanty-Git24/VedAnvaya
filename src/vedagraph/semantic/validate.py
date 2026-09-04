"""Turn a model's reply into candidates, check them, and decide what happens next.

Three stages, deliberately separate because they fail for different reasons and a report
that conflates them is unreadable:

**Structural** (:func:`validate_structure`) — is this a well-formed claim about things
that exist? Unknown passage, unknown entity, predicate not on the whitelist, object type
wrong for the predicate, evidence naming a token the model was never shown. These are
faults, and they end at ``VALIDATION_REJECTED``.

**Policy** (:func:`check_deterministic_conflict`) — does the claim sit oddly beside the
deterministic layers? A proposal that does not match the Anukramaṇī's Devatā is *not* an
error. Tradition assigns; the text says; the two differ constantly, and flattening that
difference would destroy the distinction the whole knowledge layer is built on. So a
conflict is a flag for review, never a rejection.

**Acceptance** (:func:`decide_status`) — given a clean candidate, does it become
knowledge, or does it wait for a person?

The one thing acceptance never does is trust the model's confidence. Confidence is a
self-assessment: it is produced by the same process that produced the claim, so it
carries no independent information about whether the claim is true. It is used only as a
floor inside a predicate's own rule, and a predicate cannot auto-accept at all until a
gold evaluation has measured its precision and unlocked it. High confidence on a locked
predicate buys exactly nothing, which is the intended behaviour.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from vedagraph.models.enums import (
    EvidenceSpanType,
    SemanticAssertionStatus,
    SemanticValidationCode,
)
from vedagraph.models.semantic import (
    EvidencePacket,
    SemanticAssertionCandidate,
    SemanticAssertionObject,
    SemanticEvidence,
    SemanticValidationResult,
)
from vedagraph.semantic.ontology import (
    ACCEPTANCE_POLICY_VERSION,
    FORBIDDEN_PREDICATES,
    Explicitness,
    SemanticNodeType,
    SemanticPredicate,
    SemanticSubjectKind,
    predicate_rule,
)

#: Span types whose claim rests on the model's own reading of English rather than on the
#: Sanskrit. An assertion evidenced only by these cannot be ``EXPLICIT``: the Sanskrit is
#: the primary text, and "Griffith says so" is explicit about Griffith, not about the
#: Rigveda.
_TRANSLATION_ONLY_SPANS = frozenset({EvidenceSpanType.TRANSLATION_LINE})


@dataclass
class ParsedExtraction:
    """One reply, turned into candidates, with the entity proposals it referenced."""

    passage_key: str
    candidates: list[SemanticAssertionCandidate] = field(default_factory=list)
    #: ``(passage_key, node_type, label, description, aliases)`` for the registry.
    entity_proposals: list[tuple[str, SemanticNodeType, str, str, list[str]]] = field(
        default_factory=list
    )
    #: The ``local_id`` values the reply declared, which are what an assertion's
    #: ``object_local_id`` must name. Scoped to one reply: a local id means nothing
    #: outside the packet it was invented in.
    local_entity_ids: set[str] = field(default_factory=set)
    uncertainties: list[str] = field(default_factory=list)
    no_claim_reasons: list[str] = field(default_factory=list)
    #: Structural faults found while parsing, before any candidate could be built.
    parse_errors: list[str] = field(default_factory=list)


def candidate_assertion_id(
    subject_key: str, predicate: SemanticPredicate, object_ref: str, index: int
) -> str:
    """Stable within a run and readable in a diff. Not a canonical id: this is a proposal."""
    return f"SEMASSERT:{subject_key}:{predicate.value}:{object_ref}:{index:02d}"


def parse_extraction(
    packet: EvidencePacket,
    payload: dict[str, Any],
    *,
    model: str,
    model_snapshot: str | None,
    reasoning_effort: str,
    prompt_version: str,
    ontology_version: str,
    schema_name: str,
) -> ParsedExtraction:
    """Build candidates from a schema-conformant reply.

    Anything malformed enough that a candidate cannot be constructed is recorded in
    ``parse_errors`` and dropped. It is never repaired: guessing what the model meant is
    how an unsupported assertion enters the graph wearing a validator's approval.
    """
    parsed = ParsedExtraction(passage_key=packet.passage_key)
    parsed.uncertainties = [str(item) for item in payload.get("uncertainties", [])]
    parsed.no_claim_reasons = [str(item) for item in payload.get("no_claim_reasons", [])]

    local_types: dict[str, SemanticNodeType] = {}
    for raw in payload.get("entities", []):
        try:
            node_type = SemanticNodeType(str(raw["entity_type"]))
            label = str(raw["label"]).strip()
        except (KeyError, ValueError) as error:
            parsed.parse_errors.append(f"entity: {error}")
            continue
        if not label:
            parsed.parse_errors.append("entity: empty label")
            continue
        local_id = str(raw.get("local_id") or label)
        local_types[local_id] = node_type
        parsed.local_entity_ids.add(local_id)
        parsed.entity_proposals.append(
            (
                packet.passage_key,
                node_type,
                label,
                str(raw.get("description", "")),
                [str(item) for item in raw.get("aliases", [])],
            )
        )

    for index, raw in enumerate(payload.get("assertions", [])):
        try:
            predicate = SemanticPredicate(str(raw["predicate"]))
            explicitness = Explicitness(str(raw["explicitness"]))
            evidence = [_evidence(item) for item in raw.get("evidence", [])]
            entity_key = raw.get("object_entity_key") or None
            object_local_id = raw.get("object_local_id") or None
            obj = SemanticAssertionObject(
                entity_key=str(entity_key) if entity_key else None,
                candidate_entity_id=str(object_local_id) if object_local_id else None,
                node_type=local_types.get(str(object_local_id)) if object_local_id else None,
            )
            reference = str(entity_key or object_local_id)
            parsed.candidates.append(
                SemanticAssertionCandidate(
                    candidate_assertion_id=candidate_assertion_id(
                        packet.passage_key, predicate, reference, index
                    ),
                    subject_key=str(raw.get("subject_passage_key") or packet.passage_key),
                    subject_kind=SemanticSubjectKind.MANTRA,
                    predicate=predicate,
                    object=obj,
                    evidence=evidence,
                    explicitness=explicitness,
                    confidence=float(raw.get("confidence", 0.0)),
                    model=model,
                    model_snapshot=model_snapshot,
                    reasoning_effort=reasoning_effort,
                    prompt_version=prompt_version,
                    ontology_version=ontology_version,
                    schema_name=schema_name,
                    input_sha256=packet.input_sha256,
                    status=SemanticAssertionStatus.CANDIDATE,
                )
            )
        except (KeyError, ValueError, TypeError) as error:
            parsed.parse_errors.append(f"assertion {index}: {error}")
    return parsed


def _evidence(raw: dict[str, Any]) -> SemanticEvidence:
    translation_id = raw.get("translation_id") or None
    return SemanticEvidence(
        passage_key=str(raw["passage_key"]),
        span_type=EvidenceSpanType(str(raw["span_type"])),
        translation_id=str(translation_id) if translation_id else None,
        sanskrit_token_keys=[str(item) for item in raw.get("sanskrit_token_keys", [])],
        note=str(raw.get("note", "")),
    )


def validate_structure(
    candidate: SemanticAssertionCandidate,
    packet: EvidencePacket,
    *,
    canonical_entity_keys: frozenset[str],
    resolved_candidate_ids: frozenset[str],
) -> list[SemanticValidationCode]:
    """Every structural fault in one candidate. Empty means well formed, not true."""
    codes: list[SemanticValidationCode] = []

    if candidate.subject_key not in packet.citable_passage_keys:
        codes.append(SemanticValidationCode.PASSAGE_NOT_IN_PACKET)
    if candidate.subject_kind is not SemanticSubjectKind.MANTRA:
        # Sūkta-level subjects are in the ontology but not in the v1 packet, which shows
        # one mantra. Accepting one would mean accepting a claim about text not supplied.
        codes.append(SemanticValidationCode.SUBJECT_KIND_INVALID)

    rule = predicate_rule(candidate.predicate)
    if candidate.predicate in FORBIDDEN_PREDICATES:
        codes.append(SemanticValidationCode.PREDICATE_FORBIDDEN)
    elif rule is None:
        codes.append(SemanticValidationCode.PREDICATE_NOT_WHITELISTED)
    else:
        if candidate.subject_kind not in rule.subject_kinds:
            codes.append(SemanticValidationCode.SUBJECT_KIND_INVALID)
        if candidate.object.entity_key is not None:
            if not rule.allows_canonical_entity:
                codes.append(SemanticValidationCode.OBJECT_TYPE_INVALID)
            if candidate.object.entity_key not in canonical_entity_keys:
                codes.append(SemanticValidationCode.UNKNOWN_CANONICAL_ENTITY)
        else:
            node_type = candidate.object.node_type
            if node_type is None:
                codes.append(SemanticValidationCode.CANDIDATE_ENTITY_MALFORMED)
            elif node_type not in rule.object_types:
                codes.append(SemanticValidationCode.OBJECT_TYPE_INVALID)
            if (
                candidate.object.candidate_entity_id is not None
                and candidate.object.candidate_entity_id not in resolved_candidate_ids
            ):
                codes.append(SemanticValidationCode.OBJECT_UNRESOLVED)

    if not 0.0 <= candidate.confidence <= 1.0:
        codes.append(SemanticValidationCode.CONFIDENCE_OUT_OF_RANGE)

    codes.extend(_evidence_codes(candidate, packet))
    return codes


def _evidence_codes(
    candidate: SemanticAssertionCandidate, packet: EvidencePacket
) -> list[SemanticValidationCode]:
    if not candidate.evidence:
        return [SemanticValidationCode.NO_EVIDENCE]
    codes: list[SemanticValidationCode] = []
    citable_tokens = packet.citable_token_keys
    citable_passages = packet.citable_passage_keys
    translation_ids = {
        item.translation_id
        for item in (
            packet.translation,
            *(n.translation for n in (packet.previous, packet.next) if n),
        )
        if item is not None
    }
    for item in candidate.evidence:
        if item.passage_key not in citable_passages:
            codes.append(SemanticValidationCode.EVIDENCE_PASSAGE_NOT_SUPPLIED)
        for token_key in item.sanskrit_token_keys:
            if token_key not in citable_tokens:
                # The model named a token it was not shown. This is the single most
                # useful check in the layer: it catches a fabricated citation exactly.
                codes.append(SemanticValidationCode.EVIDENCE_TOKEN_NOT_IN_PASSAGE)
                break
        if item.span_type is EvidenceSpanType.TRANSLATION_LINE:
            if item.translation_id not in translation_ids:
                codes.append(SemanticValidationCode.EVIDENCE_TRANSLATION_NOT_SUPPLIED)

    spans = {item.span_type for item in candidate.evidence}
    if candidate.explicitness is Explicitness.EXPLICIT and spans <= _TRANSLATION_ONLY_SPANS:
        codes.append(SemanticValidationCode.EXPLICITNESS_UNSUPPORTED_BY_EVIDENCE)
    return codes


def check_deterministic_conflict(
    candidate: SemanticAssertionCandidate, packet: EvidencePacket
) -> bool:
    """True when the claim should be looked at beside the traditional metadata.

    Fires when a claim about *address* — praising or invoking a deity — names a Devatā
    the Anukramaṇī did not assign to this mantra. That is a normal and well attested
    situation, so it is not treated as an error, and this function never rejects
    anything. It exists so a reviewer can sample the disagreements: a pattern in them
    says something about the extractor, and a single one usually says something about
    the hymn.
    """
    if candidate.predicate not in {SemanticPredicate.PRAISES, SemanticPredicate.INVOKES}:
        return False
    entity_key = candidate.object.entity_key
    if entity_key is None or not entity_key.startswith("VG:DEVATA:"):
        return False
    return entity_key not in set(packet.devata_keys)


def decide_status(
    candidate: SemanticAssertionCandidate,
    codes: list[SemanticValidationCode],
    *,
    unlocked_predicates: frozenset[SemanticPredicate],
    conflicts_with_metadata: bool = False,
) -> SemanticValidationResult:
    """The deterministic verdict. The model never writes this field."""
    faults = [code for code in codes if code is not SemanticValidationCode.OK]
    if faults:
        return SemanticValidationResult(
            candidate_assertion_id=candidate.candidate_assertion_id,
            codes=sorted(set(faults), key=lambda code: code.value),
            status=SemanticAssertionStatus.VALIDATION_REJECTED,
            reason="; ".join(sorted({code.value for code in faults})),
            conflicts_with_metadata=conflicts_with_metadata,
        )

    rule = predicate_rule(candidate.predicate)
    assert rule is not None, "a candidate with no faults has an allowed predicate"

    if conflicts_with_metadata:
        return _review(
            candidate,
            "claim is about address and names a Devatā the Anukramaṇī did not assign; "
            "a legitimate divergence, but one a person should see",
            conflict=True,
        )
    if candidate.explicitness is Explicitness.INTERPRETIVE:
        return _review(candidate, "INTERPRETIVE claims are reviewed by a person, always")
    if candidate.predicate not in unlocked_predicates:
        return _review(
            candidate,
            f"{candidate.predicate.value} has not been unlocked for automatic acceptance "
            "by a measured gold precision",
        )
    if candidate.explicitness not in rule.auto_acceptable:
        return _review(
            candidate,
            f"{candidate.explicitness.value} is not auto-acceptable for "
            f"{candidate.predicate.value} ({rule.risk.value})",
        )
    if candidate.confidence < rule.min_confidence:
        return _review(
            candidate,
            f"confidence {candidate.confidence:.2f} is below the {rule.min_confidence:.2f} "
            f"floor for {candidate.predicate.value}",
        )
    return SemanticValidationResult(
        candidate_assertion_id=candidate.candidate_assertion_id,
        codes=[SemanticValidationCode.OK],
        status=SemanticAssertionStatus.AUTO_ACCEPTED,
        reason=(
            f"{ACCEPTANCE_POLICY_VERSION}: {candidate.predicate.value} is unlocked, the "
            f"claim is {candidate.explicitness.value}, evidence checks out"
        ),
    )


def _review(
    candidate: SemanticAssertionCandidate, reason: str, *, conflict: bool = False
) -> SemanticValidationResult:
    return SemanticValidationResult(
        candidate_assertion_id=candidate.candidate_assertion_id,
        codes=[
            SemanticValidationCode.DETERMINISTIC_CONTEXT_CONFLICT
            if conflict
            else SemanticValidationCode.OK
        ],
        status=SemanticAssertionStatus.NEEDS_REVIEW,
        reason=reason,
        conflicts_with_metadata=conflict,
    )
