"""Offline migration and comparison for typed semantic object occurrences.

No function in this module calls a model, modifies a legacy artifact, updates human
gold, or unlocks a predicate.  Legacy text is copied only into display/annotation
fields; deterministic structure, evidence references, and canonical ids carry the
comparison.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from vedagraph.models.enums import EvidenceSpanType
from vedagraph.models.normalization import (
    ActionEvent,
    EventParticipant,
    EventSignature,
    EvidenceSignature,
    SemanticAssertionSignature,
    SemanticEvidenceAnchor,
    SemanticObjectCandidate,
    SemanticObjectSignature,
    StructuredSemanticAssertion,
    StructuredSemanticComparison,
)
from vedagraph.models.semantic import SemanticAssertionCandidate
from vedagraph.models.silver import SilverSemanticAssertion
from vedagraph.semantic.object_ontology import (
    SemanticObjectKind,
    SemanticObjectNormalizationStatus,
    StructuredComparisonCategory,
)
from vedagraph.semantic.ontology import SemanticNodeType, SemanticPredicate
from vedagraph.semantic.registry import normalize_label


@dataclass(frozen=True)
class LegacyEntityLabel:
    """The local object annotation emitted in one immutable legacy payload."""

    label: str
    node_type: SemanticNodeType


def canonical_json_sha256(value: object) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def deterministic_object_candidate_id(
    *,
    run_id: str,
    mantra_id: str,
    predicate: SemanticPredicate,
    evidence: Sequence[SemanticEvidenceAnchor],
    ordinal: int,
    legacy_object_id: str | None,
) -> str:
    """Mint occurrence identity without implying cross-occurrence semantic identity."""
    material = {
        "run_id": run_id,
        "mantra_id": mantra_id,
        "predicate": predicate.value,
        "evidence": evidence_signature(evidence).model_dump(mode="json"),
        "ordinal": ordinal,
        "legacy_object_id": legacy_object_id,
    }
    return f"VG:SEMOBJ:{canonical_json_sha256(material)[:20].upper()}"


def evidence_signature(evidence: Sequence[SemanticEvidenceAnchor]) -> EvidenceSignature:
    references: set[str] = set()
    for item in evidence:
        references.add(f"PASSAGE:{item.source_passage_id}")
        if item.translation_record_id:
            span = item.translation_span
            suffix = f":{span.start}:{span.end}" if span else ""
            references.add(f"TRANSLATION:{item.translation_record_id}{suffix}")
        references.update(f"TOKEN:{value}" for value in item.token_ids)
        references.update(f"PASSAGE:{value}" for value in item.passage_ids)
        references.update(f"OTHER:{value}" for value in item.other_evidence_ids)
    return EvidenceSignature(references=tuple(sorted(references)))


def object_signature(candidate: SemanticObjectCandidate) -> SemanticObjectSignature:
    event: EventSignature | None = None
    if candidate.event is not None:
        participants = tuple(
            sorted(
                (
                    normalize_label(item.role),
                    item.entity_id or normalize_label(item.normalized_head or ""),
                )
                for item in candidate.event.other_participants
            )
        )
        event = EventSignature(
            action_head=normalize_label(candidate.event.action_head),
            actor_entity_id=candidate.event.actor_entity_id,
            patient_entity_id=candidate.event.patient_entity_id,
            participants=participants,
            qualifiers=tuple(sorted(normalize_label(item) for item in candidate.event.qualifiers)),
        )
    return SemanticObjectSignature(
        object_kind=candidate.object_kind,
        canonical_entity_id=candidate.canonical_entity_id,
        normalized_head=(
            normalize_label(candidate.normalized_head) if candidate.normalized_head else None
        ),
        qualifiers=tuple(sorted(normalize_label(item) for item in candidate.qualifiers)),
        beneficiary_entity_id=candidate.beneficiary_entity_id,
        target_entity_id=candidate.target_entity_id,
        event=event,
    )


def assertion_signature(assertion: StructuredSemanticAssertion) -> SemanticAssertionSignature:
    return SemanticAssertionSignature(
        subject_id=assertion.subject_id,
        predicate=assertion.predicate,
        object_signature=object_signature(assertion.object),
        evidence_signature=evidence_signature(assertion.evidence),
    )


def _legacy_label_is_resolved(label: str) -> bool:
    """Accept only a concise copied head; never split or paraphrase legacy prose."""
    raw = " ".join(label.casefold().split())
    if any(delimiter in raw for delimiter in (" and ", " or ", ",", ";")):
        return False
    normalized = normalize_label(label)
    if not normalized or len(normalized.split()) > 5:
        return False
    return True


def _kind_for_legacy(
    predicate: SemanticPredicate, node_type: SemanticNodeType | None
) -> SemanticObjectKind:
    by_predicate = {
        SemanticPredicate.REQUESTS: SemanticObjectKind.REQUESTED_OUTCOME,
        SemanticPredicate.DESCRIBES_ACTION: SemanticObjectKind.EVENT,
        SemanticPredicate.INVOLVES_RITUAL: SemanticObjectKind.RITUAL_EVENT,
        SemanticPredicate.INVOLVES_OFFERING: SemanticObjectKind.OFFERING_REF,
        SemanticPredicate.INVOLVES_SUBSTANCE: SemanticObjectKind.SUBSTANCE_REF,
        SemanticPredicate.REFERS_TO_NATURAL_PHENOMENON: (SemanticObjectKind.NATURAL_PHENOMENON_REF),
        SemanticPredicate.REFERS_TO_PLACE: SemanticObjectKind.PLACE_REF,
        SemanticPredicate.HAS_THEME: SemanticObjectKind.CONCEPT_REF,
    }
    if predicate in by_predicate:
        return by_predicate[predicate]
    if predicate is SemanticPredicate.EXPRESSES:
        if node_type is None:
            return SemanticObjectKind.SEMANTIC_ENTITY_REF
        return {
            SemanticNodeType.STATE: SemanticObjectKind.STATE_REF,
            SemanticNodeType.QUALITY: SemanticObjectKind.QUALITY_REF,
            SemanticNodeType.CONCEPT: SemanticObjectKind.CONCEPT_REF,
            SemanticNodeType.PHILOSOPHICAL_CONCEPT: SemanticObjectKind.CONCEPT_REF,
        }.get(node_type, SemanticObjectKind.SEMANTIC_ENTITY_REF)
    if predicate in {SemanticPredicate.INVOKES, SemanticPredicate.PRAISES}:
        return SemanticObjectKind.OPAQUE_REFERENT
    if predicate is SemanticPredicate.DESCRIBES:
        return SemanticObjectKind.SEMANTIC_ENTITY_REF
    if node_type is SemanticNodeType.ACTION:
        return SemanticObjectKind.ACTION_REF
    return SemanticObjectKind.OPAQUE_REFERENT


_CANONICAL_OBJECT_PREDICATES = {
    SemanticPredicate.INVOKES,
    SemanticPredicate.PRAISES,
    SemanticPredicate.DESCRIBES,
    SemanticPredicate.ASSOCIATED_WITH,
    SemanticPredicate.CONTRASTS_WITH,
}


def _luna_evidence(candidate: SemanticAssertionCandidate) -> list[SemanticEvidenceAnchor]:
    anchors: list[SemanticEvidenceAnchor] = []
    for item in candidate.evidence:
        other: list[str] = []
        if item.span_type in {
            EvidenceSpanType.TRADITIONAL_METADATA,
            EvidenceSpanType.LEXICAL_MENTION,
        }:
            other.append(f"{item.span_type.value}:{item.passage_key}")
        anchors.append(
            SemanticEvidenceAnchor(
                source_passage_id=candidate.subject_key,
                translation_record_id=item.translation_id,
                token_ids=sorted(item.sanskrit_token_keys),
                passage_ids=[item.passage_key],
                other_evidence_ids=other,
            )
        )
    if not anchors:
        anchors.append(
            SemanticEvidenceAnchor(
                source_passage_id=candidate.subject_key,
                passage_ids=[candidate.subject_key],
            )
        )
    return anchors


def migrate_luna_assertion(
    candidate: SemanticAssertionCandidate,
    *,
    run_id: str,
    local_entities: Mapping[str, LegacyEntityLabel],
    ordinal: int,
) -> StructuredSemanticAssertion:
    """Wrap one immutable Luna v1/v2 assertion without interpreting its label."""
    evidence = _luna_evidence(candidate)
    legacy_id = candidate.object.entity_key or candidate.object.candidate_entity_id
    if candidate.object.entity_key and candidate.predicate in _CANONICAL_OBJECT_PREDICATES:
        kind = SemanticObjectKind.CANONICAL_ENTITY_REF
        label = candidate.object.entity_key
        head = None
        status = SemanticObjectNormalizationStatus.CANONICAL_REF
        canonical_entity_id = candidate.object.entity_key
        event = None
    else:
        entity = local_entities.get(candidate.object.candidate_entity_id or "")
        label = (
            entity.label
            if entity
            else (
                candidate.object.candidate_entity_id or candidate.object.entity_key or "unresolved"
            )
        )
        node_type = entity.node_type if entity else candidate.object.node_type
        kind = _kind_for_legacy(candidate.predicate, node_type)
        head = normalize_label(label)
        status = (
            SemanticObjectNormalizationStatus.NORMALIZED_CANDIDATE
            if (
                entity is not None
                and candidate.object.entity_key is None
                and _legacy_label_is_resolved(label)
            )
            else SemanticObjectNormalizationStatus.UNRESOLVED_LEGACY_OBJECT
        )
        canonical_entity_id = None
        event = ActionEvent(action_head=head) if kind is SemanticObjectKind.EVENT else None
    object_candidate = SemanticObjectCandidate(
        candidate_id=deterministic_object_candidate_id(
            run_id=run_id,
            mantra_id=candidate.subject_key,
            predicate=candidate.predicate,
            evidence=evidence,
            ordinal=ordinal,
            legacy_object_id=legacy_id,
        ),
        object_kind=kind,
        normalized_head=head,
        display_label=label,
        canonical_entity_id=canonical_entity_id,
        event=event,
        source_passage_id=candidate.subject_key,
        evidence=evidence,
        extraction_model=candidate.model,
        prompt_version=candidate.prompt_version,
        normalization_status=status,
        legacy_object_id=legacy_id,
    )
    return StructuredSemanticAssertion(
        assertion_id=f"STRUCT:{candidate.candidate_assertion_id}",
        source_run_id=run_id,
        subject_id=candidate.subject_key,
        predicate=candidate.predicate,
        object=object_candidate,
        evidence=evidence,
        explicitness=candidate.explicitness,
        legacy_assertion_id=candidate.candidate_assertion_id,
    )


def _silver_evidence(assertion: SilverSemanticAssertion) -> list[SemanticEvidenceAnchor]:
    translation_ids = [
        item.reference_id for item in assertion.evidence if item.kind == "TRANSLATION"
    ]
    token_ids = [item.reference_id for item in assertion.evidence if item.kind == "TOKEN"]
    passage_ids = [item.reference_id for item in assertion.evidence if item.kind == "PASSAGE"]
    other = [
        f"{item.kind}:{item.reference_id}"
        for item in assertion.evidence
        if item.kind not in {"TRANSLATION", "TOKEN", "PASSAGE"}
    ]
    if not passage_ids:
        passage_ids = [assertion.subject]
    if not translation_ids:
        return [
            SemanticEvidenceAnchor(
                source_passage_id=assertion.subject,
                token_ids=sorted(token_ids),
                passage_ids=sorted(passage_ids),
                other_evidence_ids=sorted(other),
            )
        ]
    return [
        SemanticEvidenceAnchor(
            source_passage_id=assertion.subject,
            translation_record_id=translation_id,
            token_ids=sorted(token_ids),
            passage_ids=sorted(passage_ids),
            other_evidence_ids=sorted(other),
        )
        for translation_id in sorted(translation_ids)
    ]


def migrate_sol_assertion(
    assertion: SilverSemanticAssertion, *, run_id: str, ordinal: int
) -> StructuredSemanticAssertion:
    """Wrap one immutable Sol silver assertion without semantic paraphrase."""
    evidence = _silver_evidence(assertion)
    if assertion.object_entity_key and assertion.predicate in _CANONICAL_OBJECT_PREDICATES:
        kind = SemanticObjectKind.CANONICAL_ENTITY_REF
        head = None
        status = SemanticObjectNormalizationStatus.CANONICAL_REF
        canonical_entity_id = assertion.object_entity_key
        event = None
    else:
        kind = _kind_for_legacy(assertion.predicate, assertion.object_node_type)
        head = normalize_label(assertion.object_label)
        status = (
            SemanticObjectNormalizationStatus.NORMALIZED_CANDIDATE
            if assertion.object_entity_key is None
            and _legacy_label_is_resolved(assertion.object_label)
            else SemanticObjectNormalizationStatus.UNRESOLVED_LEGACY_OBJECT
        )
        canonical_entity_id = None
        event = ActionEvent(action_head=head) if kind is SemanticObjectKind.EVENT else None
    object_candidate = SemanticObjectCandidate(
        candidate_id=deterministic_object_candidate_id(
            run_id=run_id,
            mantra_id=assertion.subject,
            predicate=assertion.predicate,
            evidence=evidence,
            ordinal=ordinal,
            legacy_object_id=assertion.assertion_id,
        ),
        object_kind=kind,
        normalized_head=head,
        display_label=assertion.object_label,
        canonical_entity_id=canonical_entity_id,
        event=event,
        source_passage_id=assertion.subject,
        evidence=evidence,
        extraction_model="gpt-5.6-sol",
        prompt_version="rigveda-semantic-silver-sol-v1",
        normalization_status=status,
        legacy_object_id=assertion.object_entity_key or assertion.assertion_id,
    )
    return StructuredSemanticAssertion(
        assertion_id=f"STRUCT:{assertion.assertion_id}",
        source_run_id=run_id,
        subject_id=assertion.subject,
        predicate=assertion.predicate,
        object=object_candidate,
        evidence=evidence,
        explicitness=assertion.explicitness,
        legacy_assertion_id=assertion.assertion_id,
    )


_UNRESOLVED_STATUSES = {
    SemanticObjectNormalizationStatus.NEEDS_REVIEW,
    SemanticObjectNormalizationStatus.AMBIGUOUS,
    SemanticObjectNormalizationStatus.UNRESOLVED_LEGACY_OBJECT,
}


def _event_comparison(
    left: SemanticObjectSignature, right: SemanticObjectSignature
) -> StructuredComparisonCategory:
    if left.event is None or right.event is None:
        return StructuredComparisonCategory.UNRESOLVED
    left_event = left.event
    right_event = right.event
    same_action = left_event.action_head == right_event.action_head
    directly_conflicting_role = any(
        a is not None and b is not None and a != b
        for a, b in (
            (left_event.actor_entity_id, right_event.actor_entity_id),
            (left_event.patient_entity_id, right_event.patient_entity_id),
        )
    )
    left_fields = {
        value
        for value in (
            left_event.actor_entity_id,
            left_event.patient_entity_id,
            *[f"{role}:{value}" for role, value in left_event.participants],
        )
        if value
    }
    right_fields = {
        value
        for value in (
            right_event.actor_entity_id,
            right_event.patient_entity_id,
            *[f"{role}:{value}" for role, value in right_event.participants],
        )
        if value
    }
    if same_action and not directly_conflicting_role:
        if left_fields <= right_fields or right_fields <= left_fields:
            return StructuredComparisonCategory.GRANULARITY_DIFFERENCE
        return StructuredComparisonCategory.COMPATIBLE_OBJECT
    if not directly_conflicting_role and left_fields & right_fields:
        # Lexically different action heads are not equated.  Shared participants only
        # justify partial overlap (e.g. SLAY vs DESTROY with the same actor/patient).
        return StructuredComparisonCategory.PARTIAL_OBJECT_OVERLAP
    return StructuredComparisonCategory.CONFLICTING_OBJECT


def compare_semantic_objects(
    left_candidate: SemanticObjectCandidate, right_candidate: SemanticObjectCandidate
) -> StructuredComparisonCategory:
    """Compare typed fields.  Label equality and fuzzy similarity are never decisive."""
    left = object_signature(left_candidate)
    right = object_signature(right_candidate)
    if (
        left.object_kind is SemanticObjectKind.CANONICAL_ENTITY_REF
        and right.object_kind is SemanticObjectKind.CANONICAL_ENTITY_REF
    ):
        return (
            StructuredComparisonCategory.EXACT_CANONICAL_ENTITY
            if left.canonical_entity_id == right.canonical_entity_id
            else StructuredComparisonCategory.CONFLICTING_OBJECT
        )
    if SemanticObjectKind.ONTOLOGY_GAP_REF in {left.object_kind, right.object_kind}:
        return StructuredComparisonCategory.EXPERT_REQUIRED
    if left.object_kind != right.object_kind:
        return StructuredComparisonCategory.OBJECT_TYPE_DIFFERENCE
    if (
        left_candidate.normalization_status in _UNRESOLVED_STATUSES
        or right_candidate.normalization_status in _UNRESOLVED_STATUSES
    ):
        return StructuredComparisonCategory.UNRESOLVED
    if left == right:
        return StructuredComparisonCategory.EXACT_NORMALIZED_OBJECT
    if left.object_kind is SemanticObjectKind.EVENT:
        return _event_comparison(left, right)
    if left.normalized_head == right.normalized_head:
        left_qualifiers = set(left.qualifiers)
        right_qualifiers = set(right.qualifiers)
        same_roles = (
            left.beneficiary_entity_id == right.beneficiary_entity_id
            and left.target_entity_id == right.target_entity_id
        )
        if same_roles and (
            left_qualifiers <= right_qualifiers or right_qualifiers <= left_qualifiers
        ):
            return StructuredComparisonCategory.GRANULARITY_DIFFERENCE
        if not any(
            a is not None and b is not None and a != b
            for a, b in (
                (left.beneficiary_entity_id, right.beneficiary_entity_id),
                (left.target_entity_id, right.target_entity_id),
            )
        ):
            return StructuredComparisonCategory.COMPATIBLE_OBJECT
    left_head_tokens = set((left.normalized_head or "").split())
    right_head_tokens = set((right.normalized_head or "").split())
    if left_head_tokens and right_head_tokens:
        if left_head_tokens < right_head_tokens or right_head_tokens < left_head_tokens:
            return StructuredComparisonCategory.GRANULARITY_DIFFERENCE
        if left_head_tokens & right_head_tokens:
            return StructuredComparisonCategory.PARTIAL_OBJECT_OVERLAP
    return StructuredComparisonCategory.CONFLICTING_OBJECT


_MATCH_RANK = {
    StructuredComparisonCategory.EXACT_CANONICAL_ENTITY: 100,
    StructuredComparisonCategory.EXACT_NORMALIZED_OBJECT: 95,
    StructuredComparisonCategory.COMPATIBLE_OBJECT: 80,
    StructuredComparisonCategory.PARTIAL_OBJECT_OVERLAP: 70,
    StructuredComparisonCategory.GRANULARITY_DIFFERENCE: 65,
    StructuredComparisonCategory.OBJECT_TYPE_DIFFERENCE: 45,
    StructuredComparisonCategory.CONFLICTING_OBJECT: 35,
    StructuredComparisonCategory.EXPERT_REQUIRED: 20,
    StructuredComparisonCategory.UNRESOLVED: 10,
}

_CROSS_PREDICATE_ALIGNMENT_CATEGORIES = {
    StructuredComparisonCategory.EXACT_CANONICAL_ENTITY,
    StructuredComparisonCategory.EXACT_NORMALIZED_OBJECT,
    StructuredComparisonCategory.COMPATIBLE_OBJECT,
    StructuredComparisonCategory.PARTIAL_OBJECT_OVERLAP,
    StructuredComparisonCategory.GRANULARITY_DIFFERENCE,
}


def _comparison_row(
    left: StructuredSemanticAssertion,
    right: StructuredSemanticAssertion,
    category: StructuredComparisonCategory,
) -> StructuredSemanticComparison:
    if left.predicate != right.predicate:
        category = StructuredComparisonCategory.PREDICATE_DIFFERENCE
    return StructuredSemanticComparison(
        mantra_id=left.subject_id,
        category=category,
        luna_assertion_id=left.legacy_assertion_id,
        sol_assertion_id=right.legacy_assertion_id,
        luna_predicate=left.predicate,
        sol_predicate=right.predicate,
        luna_object_signature=object_signature(left.object),
        sol_object_signature=object_signature(right.object),
        evidence_overlap=bool(
            set(evidence_signature(left.evidence).references)
            & set(evidence_signature(right.evidence).references)
        ),
        label_equality_signal=(
            normalize_label(left.object.display_label)
            == normalize_label(right.object.display_label)
        ),
        reasoning=_comparison_reason(category, left, right),
    )


def _comparison_reason(
    category: StructuredComparisonCategory,
    left: StructuredSemanticAssertion,
    right: StructuredSemanticAssertion,
) -> str:
    reasons = {
        StructuredComparisonCategory.EXACT_CANONICAL_ENTITY: (
            "Both objects carry the same deterministic canonical entity id."
        ),
        StructuredComparisonCategory.EXACT_NORMALIZED_OBJECT: (
            "Typed normalized object fields agree; display labels were not used as identity."
        ),
        StructuredComparisonCategory.COMPATIBLE_OBJECT: (
            "Typed heads agree and the remaining evidenced fields do not conflict."
        ),
        StructuredComparisonCategory.PARTIAL_OBJECT_OVERLAP: (
            "Some structured event/object fields agree, but the full objects are not equivalent."
        ),
        StructuredComparisonCategory.GRANULARITY_DIFFERENCE: (
            "One typed object contains a strict subset of the other's structured detail."
        ),
        StructuredComparisonCategory.PREDICATE_DIFFERENCE: (
            f"Object alignment is possible, but predicates differ: "
            f"{left.predicate.value} vs {right.predicate.value}."
        ),
        StructuredComparisonCategory.OBJECT_TYPE_DIFFERENCE: (
            "Object kinds differ; ritual, offering, substance, phenomenon, place, and entity "
            "boundaries are not collapsed by shared words."
        ),
        StructuredComparisonCategory.CONFLICTING_OBJECT: (
            "Typed object fields conflict and no identity rule resolves them."
        ),
        StructuredComparisonCategory.UNRESOLVED: (
            "At least one legacy label cannot be deterministically converted beyond an "
            "evidence-anchored occurrence."
        ),
        StructuredComparisonCategory.EXPERT_REQUIRED: (
            "The object exposes an ontology gap or a review-only referent."
        ),
    }
    return reasons[category]


def compare_assertion_sets(
    luna: Sequence[StructuredSemanticAssertion],
    sol: Sequence[StructuredSemanticAssertion],
) -> list[StructuredSemanticComparison]:
    """Deterministically align two assertion sets, independent of extraction order."""
    by_mantra_luna: dict[str, list[StructuredSemanticAssertion]] = defaultdict(list)
    by_mantra_sol: dict[str, list[StructuredSemanticAssertion]] = defaultdict(list)
    for item in luna:
        by_mantra_luna[item.subject_id].append(item)
    for item in sol:
        by_mantra_sol[item.subject_id].append(item)
    rows: list[StructuredSemanticComparison] = []
    for mantra_id in sorted(set(by_mantra_luna) | set(by_mantra_sol)):
        left_items = sorted(by_mantra_luna[mantra_id], key=lambda item: item.assertion_id)
        right_items = sorted(by_mantra_sol[mantra_id], key=lambda item: item.assertion_id)
        if not left_items and not right_items:
            continue
        unmatched = set(range(len(right_items)))
        for left in left_items:
            same_predicate_choices: list[tuple[int, int, StructuredComparisonCategory]] = []
            cross_predicate_choices: list[tuple[int, int, StructuredComparisonCategory]] = []
            for index in unmatched:
                right = right_items[index]
                category = compare_semantic_objects(left.object, right.object)
                choice = (_MATCH_RANK[category], -index, category)
                if left.predicate == right.predicate:
                    same_predicate_choices.append(choice)
                elif category in _CROSS_PREDICATE_ALIGNMENT_CATEGORIES:
                    # A predicate conflict is meaningful only when the typed objects
                    # independently align. Unrelated objects remain one-sided rows.
                    cross_predicate_choices.append(choice)
            choices = same_predicate_choices or cross_predicate_choices
            if not choices:
                rows.append(
                    StructuredSemanticComparison(
                        mantra_id=mantra_id,
                        category=StructuredComparisonCategory.LEFT_ONLY,
                        luna_assertion_id=left.legacy_assertion_id,
                        luna_predicate=left.predicate,
                        luna_object_signature=object_signature(left.object),
                        reasoning="Luna assertion has no remaining Sol assertion to align.",
                    )
                )
                continue
            _, negative_index, category = max(choices)
            index = -negative_index
            unmatched.remove(index)
            rows.append(_comparison_row(left, right_items[index], category))
        for index in sorted(unmatched):
            right = right_items[index]
            rows.append(
                StructuredSemanticComparison(
                    mantra_id=mantra_id,
                    category=StructuredComparisonCategory.RIGHT_ONLY,
                    sol_assertion_id=right.legacy_assertion_id,
                    sol_predicate=right.predicate,
                    sol_object_signature=object_signature(right.object),
                    reasoning="Sol assertion has no remaining Luna assertion to align.",
                )
            )
    return rows


def select_refined_expert_audit_ids(
    existing_ids: Sequence[str],
    comparisons: Sequence[StructuredSemanticComparison],
    *,
    target_max: int = 25,
) -> list[str]:
    """Remove purely representational cases while preserving the existing queue order."""
    if not 20 <= target_max <= 25:
        raise ValueError("refined expert queue maximum must be between 20 and 25")
    by_id: dict[str, set[StructuredComparisonCategory]] = defaultdict(set)
    for row in comparisons:
        by_id[row.mantra_id].add(row.category)
    substantive = {
        StructuredComparisonCategory.PREDICATE_DIFFERENCE,
        StructuredComparisonCategory.OBJECT_TYPE_DIFFERENCE,
        StructuredComparisonCategory.CONFLICTING_OBJECT,
        StructuredComparisonCategory.EXPERT_REQUIRED,
        StructuredComparisonCategory.UNRESOLVED,
        StructuredComparisonCategory.LEFT_ONLY,
        StructuredComparisonCategory.RIGHT_ONLY,
    }
    return [mantra_id for mantra_id in existing_ids if by_id[mantra_id] & substantive][:target_max]


def participant(
    role: str, *, entity_id: str | None = None, normalized_head: str | None = None
) -> EventParticipant:
    """Small public constructor used by callers and tests building event candidates."""
    return EventParticipant(role=role, entity_id=entity_id, normalized_head=normalized_head)
