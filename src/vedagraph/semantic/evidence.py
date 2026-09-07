"""Complete, recursive validation of every evidence reference in a V3 payload.

The readiness audit found two independent holes. Identifier membership was checked on
assertion anchors but not on ontology-gap anchors, ``other_evidence_ids`` or nested
entity references, so an object could name an entity the packet never supplied. And a
translation span was checked only for being inside the record, so ``man`` anchored inside
``Pavamana`` passed.

Both are closed here, and neither is a semantic judgement: this module says whether a
reference points at something the packet actually contains, never whether the assertion
it supports is true. It is additive by design — :func:`vedagraph.semantic.v3.validate_v3_payload`
is left exactly as the sealed pilots were validated against, and this runs alongside it
on the paths introduced after the audit.
"""

from __future__ import annotations

from collections.abc import Iterator

from vedagraph.models.normalization import (
    SemanticEvidenceAnchor,
    SemanticExtractionV3,
    SemanticObjectCandidate,
)
from vedagraph.models.semantic import EvidencePacket
from vedagraph.semantic.spans import span_errors


def payload_objects(payload: SemanticExtractionV3) -> list[SemanticObjectCandidate]:
    """Every typed object in the payload: assertion objects and ontology gaps alike."""
    return [item.object for item in payload.assertions] + list(payload.ontology_gaps)


def payload_anchors(
    payload: SemanticExtractionV3,
) -> Iterator[tuple[str, SemanticEvidenceAnchor]]:
    """Every evidence anchor with the record that owns it, assertions and gaps included."""
    for assertion in payload.assertions:
        for anchor in assertion.evidence:
            yield f"{assertion.assertion_id} evidence", anchor
        for anchor in assertion.object.evidence:
            yield f"{assertion.object.candidate_id} object evidence", anchor
    for gap in payload.ontology_gaps:
        for anchor in gap.evidence:
            yield f"{gap.candidate_id} gap evidence", anchor


def nested_entity_ids(candidate: SemanticObjectCandidate) -> list[str]:
    """Every canonical entity id an object refers to, at any depth."""
    ids = [
        candidate.canonical_entity_id,
        candidate.beneficiary_entity_id,
        candidate.target_entity_id,
    ]
    if candidate.event is not None:
        ids += [candidate.event.actor_entity_id, candidate.event.patient_entity_id]
        ids += [item.entity_id for item in candidate.event.other_participants]
    return [item for item in ids if item is not None]


def validate_anchor(
    label: str, anchor: SemanticEvidenceAnchor, packet: EvidencePacket
) -> list[str]:
    """One anchor against the packet it claims to cite, offsets included."""
    errors: list[str] = []
    canonical = {mention.entity_key for mention in packet.mentions}
    allowed_other = {f"LEXICAL_MENTION:{key}" for key in canonical}
    if anchor.source_passage_id != packet.passage_key:
        errors.append(f"{label}: anchor source outside packet")
    if not set(anchor.token_ids) <= packet.citable_token_keys:
        errors.append(f"{label}: token anchor is not in the packet")
    if not set(anchor.passage_ids) <= packet.citable_passage_keys:
        errors.append(f"{label}: passage anchor is not in the packet")
    if not set(anchor.other_evidence_ids) <= allowed_other:
        errors.append(f"{label}: other evidence anchor is not a supplied lexical mention")
    if anchor.translation_record_id is None:
        if anchor.translation_span is not None:
            errors.append(f"{label}: translation offsets without a translation record")
        return errors
    translation = packet.translation
    if translation is None or anchor.translation_record_id != translation.translation_id:
        errors.append(f"{label}: translation anchor is not the packet translation")
        return errors
    if anchor.translation_span is not None:
        errors += [
            f"{label}: {message}"
            for message in span_errors(
                translation.text or "",
                anchor.translation_span.start,
                anchor.translation_span.end,
            )
        ]
    return errors


def validate_evidence_anchors(payload: SemanticExtractionV3, packet: EvidencePacket) -> list[str]:
    """Every anchor and every nested identifier in one payload. Sorted and deduplicated."""
    canonical = {mention.entity_key for mention in packet.mentions}
    errors = [
        message
        for label, anchor in payload_anchors(payload)
        for message in validate_anchor(label, anchor, packet)
    ]
    for candidate in payload_objects(payload):
        if candidate.source_passage_id != packet.passage_key:
            errors.append(f"{candidate.candidate_id}: object outside packet")
        errors += [
            f"{candidate.candidate_id}: entity {key} is not a supplied canonical mention"
            for key in nested_entity_ids(candidate)
            if key not in canonical
        ]
    return sorted(set(errors))
