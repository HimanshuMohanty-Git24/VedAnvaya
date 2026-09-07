"""The frozen V3 payload contract: versions, the predicate checklist, and validation.

This module holds what a V3 semantic payload *is*. It does not produce one. The
deterministic cue matcher that authored the historical pilot artefacts now lives in
:mod:`vedagraph.semantic.heuristic_baseline` under its own provenance, and the real
extraction path is :mod:`vedagraph.semantic.codex_direct`, where a model authors the
payload and Python only validates it.

:func:`validate_v3_payload` is deliberately unchanged from the version the sealed pilots
were validated against, so replaying a sealed artefact still means what it meant. The
stricter recursive and boundary-safe evidence checks introduced by the readiness audit
are additive and live in :mod:`vedagraph.semantic.evidence`; applying them retroactively
would rewrite the meaning of an existing seal.
"""

from __future__ import annotations

from vedagraph.models.normalization import SemanticExtractionV3
from vedagraph.models.semantic import EvidencePacket
from vedagraph.semantic.object_ontology import SemanticObjectKind, object_kind_is_allowed

PROMPT_VERSION = "rigveda-semantic-extraction-v3"
OBJECT_SCHEMA_VERSION = "rigveda-semantic-object-v1"

#: The fourteen predicate families an extraction must consider and answer for.
PREDICATE_CHECKS: tuple[str, ...] = (
    "INVOKES",
    "PRAISES",
    "REQUESTS",
    "DESCRIBES",
    "DESCRIBES_ACTION",
    "INVOLVES_RITUAL",
    "INVOLVES_OFFERING",
    "INVOLVES_SUBSTANCE",
    "REFERS_TO_NATURAL_PHENOMENON",
    "REFERS_TO_PLACE",
    "EXPRESSES",
    "HAS_THEME",
    "ASSOCIATED_WITH",
    "CONTRASTS_WITH",
)


def validate_v3_payload(
    payload: SemanticExtractionV3,
    packet: EvidencePacket,
    *,
    canonical_entity_ids: frozenset[str],
) -> list[str]:
    """Strict deterministic checks beyond Pydantic's shape validation."""
    errors: list[str] = []
    if payload.mantra_id != packet.citation:
        errors.append("mantra_id does not match packet citation")
    for assertion in payload.assertions:
        if assertion.subject_id != packet.passage_key:
            errors.append(f"{assertion.assertion_id}: subject outside packet")
        if not object_kind_is_allowed(assertion.predicate, assertion.object.object_kind):
            errors.append(f"{assertion.assertion_id}: predicate/object type boundary violation")
        if (
            assertion.object.canonical_entity_id is not None
            and assertion.object.canonical_entity_id not in canonical_entity_ids
        ):
            errors.append(f"{assertion.assertion_id}: unknown canonical entity id")
        if assertion.explicitness.value == "STRONG_INFERENCE" and not assertion.inference_step:
            errors.append(f"{assertion.assertion_id}: missing inference rationale")
        for anchor in [*assertion.evidence, *assertion.object.evidence]:
            if anchor.source_passage_id != packet.passage_key:
                errors.append(f"{assertion.assertion_id}: evidence source outside packet")
            if any(token not in packet.citable_token_keys for token in anchor.token_ids):
                errors.append(f"{assertion.assertion_id}: fabricated token evidence")
            if any(passage not in packet.citable_passage_keys for passage in anchor.passage_ids):
                errors.append(f"{assertion.assertion_id}: fabricated passage evidence")
            if anchor.translation_record_id:
                allowed = {packet.translation.translation_id} if packet.translation else set()
                if anchor.translation_record_id not in allowed:
                    errors.append(f"{assertion.assertion_id}: fabricated translation evidence")
                if anchor.translation_span and packet.translation and packet.translation.text:
                    if anchor.translation_span.end > len(packet.translation.text):
                        errors.append(
                            f"{assertion.assertion_id}: translation offset outside record"
                        )
    for gap in payload.ontology_gaps:
        if gap.object_kind is not SemanticObjectKind.ONTOLOGY_GAP_REF:
            errors.append(f"{gap.candidate_id}: malformed ontology gap")
    if payload.assertions and payload.no_claim_reasons:
        errors.append("assertions coexist with no-claim reasons")
    return sorted(set(errors))
