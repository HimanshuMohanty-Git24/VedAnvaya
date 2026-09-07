"""Blind independent-silver review, sealing, comparison, and metrics.

The independent phase accepts EvidencePackets only.  Luna output is opened exclusively
by :func:`compare_after_blind_seal`, after the complete 120-row annotation file and its
per-row hashes have been verified against an immutable seal.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from vedagraph.models.semantic import EvidencePacket, SemanticAssertionCandidate
from vedagraph.models.silver import (
    SilverComparison,
    SilverEvidenceReference,
    SilverSemanticAnnotation,
    SilverSemanticAssertion,
)
from vedagraph.semantic.ontology import (
    ALLOWED_PREDICATES,
    Explicitness,
    SemanticPredicate,
    SilverComparisonCategory,
    SilverEvidenceAssessment,
    predicate_rule,
)
from vedagraph.semantic.registry import normalize_label

SILVER_RUN_ID = "vedagraph-rigveda-semantic-silver-sol-v1"
SILVER_PROVENANCE = "MODEL_REVIEWED_SILVER"
SILVER_REVIEWER_MODEL = "gpt-5.6-sol"
SILVER_RUNTIME = "CODEX_DIRECT"
EXPECTED_SILVER_COUNT = 120
DEFAULT_BATCH_SIZE = 15

_LUNA_FIELD_NAMES = frozenset(
    {
        "candidate",
        "candidates",
        "candidate_assertion",
        "candidate_assertions",
        "luna",
        "luna_output",
        "model_output",
        "pilot_output",
        "confidence",
    }
)


def canonical_json_sha256(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def _jsonl_text(rows: Iterable[object]) -> str:
    output: list[str] = []
    for row in rows:
        value = (
            row.model_dump(mode="json", exclude_none=True) if hasattr(row, "model_dump") else row
        )
        output.append(json.dumps(value, ensure_ascii=False, sort_keys=True))
    return "".join(f"{line}\n" for line in output)


def _walk_keys(value: object) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            yield str(key).lower()
            yield from _walk_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk_keys(nested)


def assert_blind_evidence_payload(value: Mapping[str, object]) -> None:
    """Reject payloads containing extractor-output fields before independent review."""
    leaked = sorted(set(_walk_keys(value)) & _LUNA_FIELD_NAMES)
    if leaked:
        raise ValueError(f"blind evidence payload exposes model fields: {', '.join(leaked)}")


def load_blind_packets(
    evidence_paths: Sequence[Path], selected_ids: frozenset[str]
) -> dict[str, EvidencePacket]:
    """Load only files explicitly named ``evidence.jsonl``; never inspect siblings."""
    packets: dict[str, EvidencePacket] = {}
    for path in evidence_paths:
        if path.name != "evidence.jsonl":
            raise ValueError(f"blind review may only open evidence.jsonl, got {path.name}")
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            raw: Any = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError(f"packet is not an object at {path}:{line_number}")
            assert_blind_evidence_payload(raw)
            packet = EvidencePacket.model_validate(raw)
            if packet.passage_key in selected_ids:
                if packet.passage_key in packets:
                    raise ValueError(f"duplicate selected packet: {packet.passage_key}")
                packets[packet.passage_key] = packet
    missing = sorted(selected_ids - packets.keys())
    if missing:
        raise ValueError(f"selected EvidencePackets missing: {', '.join(missing)}")
    return packets


def _packet_reference_ids(packet: EvidencePacket) -> dict[str, set[str]]:
    translations: set[str] = set()
    if packet.translation is not None:
        translations.add(packet.translation.translation_id)
    for neighbour in (packet.previous, packet.next):
        if neighbour is not None and neighbour.translation is not None:
            translations.add(neighbour.translation.translation_id)
    return {
        "PASSAGE": set(packet.citable_passage_keys),
        "TRANSLATION": translations,
        "TOKEN": set(packet.citable_token_keys),
        "ENTITY": set(packet.devata_keys + packet.rishi_keys + packet.chandas_keys)
        | {mention.entity_key for mention in packet.mentions},
        "PARALLEL": set(packet.exact_parallel_passage_keys + packet.near_parallel_passage_keys),
    }


def validate_silver_annotation(
    annotation: SilverSemanticAnnotation, packet: EvidencePacket
) -> tuple[str, ...]:
    """Validate an independent judgment without consulting any model candidate."""
    errors: list[str] = []
    if annotation.mantra_id != packet.passage_key:
        errors.append("annotation mantra_id does not match packet")
    if annotation.citation != packet.citation:
        errors.append("annotation citation does not match packet")
    if annotation.evidence_packet_hash != packet.input_sha256:
        errors.append("annotation EvidencePacket hash does not match packet")
    if annotation.provenance != SILVER_PROVENANCE:
        errors.append("silver provenance must be MODEL_REVIEWED_SILVER")
    if annotation.reviewer_model != SILVER_REVIEWER_MODEL:
        errors.append("unexpected independent reviewer model")
    if annotation.reviewer_runtime != SILVER_RUNTIME:
        errors.append("unexpected independent reviewer runtime")

    allowed_refs = _packet_reference_ids(packet)
    entity_keys = allowed_refs["ENTITY"]
    for entity in annotation.entities:
        if entity.entity_key is not None and entity.entity_key not in entity_keys:
            errors.append(f"entity is not present in packet: {entity.entity_key}")
        errors.extend(_validate_refs(entity.evidence, allowed_refs))
    seen_ids: set[str] = set()
    for assertion in annotation.semantic_assertions:
        if assertion.assertion_id in seen_ids:
            errors.append(f"duplicate assertion id: {assertion.assertion_id}")
        seen_ids.add(assertion.assertion_id)
        if assertion.subject != annotation.mantra_id:
            errors.append(f"assertion subject does not match mantra: {assertion.assertion_id}")
        if assertion.predicate not in ALLOWED_PREDICATES:
            errors.append(f"predicate is not allowed: {assertion.predicate.value}")
        rule = predicate_rule(assertion.predicate)
        if (
            rule is not None
            and assertion.object_node_type is not None
            and assertion.object_node_type not in rule.object_types
            and not (assertion.object_entity_key is not None and rule.allows_canonical_entity)
        ):
            errors.append(
                f"object type {assertion.object_node_type.value} is invalid for "
                f"{assertion.predicate.value}"
            )
        if (
            assertion.object_entity_key is not None
            and assertion.object_entity_key not in entity_keys
        ):
            errors.append(
                f"assertion entity is not present in packet: {assertion.object_entity_key}"
            )
        errors.extend(_validate_refs(assertion.evidence, allowed_refs))
    return tuple(dict.fromkeys(errors))


def _validate_refs(
    references: Iterable[SilverEvidenceReference], allowed: Mapping[str, set[str]]
) -> list[str]:
    return [
        f"{reference.kind} id is not present in packet: {reference.reference_id}"
        for reference in references
        if reference.reference_id not in allowed[reference.kind]
    ]


def annotation_sha256(annotation: SilverSemanticAnnotation) -> str:
    return canonical_json_sha256(annotation.model_dump(mode="json", exclude_none=True))


def persist_blind_batch(
    *,
    annotations_path: Path,
    batch_path: Path,
    annotations: Sequence[SilverSemanticAnnotation],
    packets: Mapping[str, EvidencePacket],
) -> None:
    """Validate and atomically persist one deterministic batch and the merged ledger."""
    if not annotations:
        raise ValueError("cannot persist an empty silver batch")
    batch_ids = {item.batch_id for item in annotations}
    if len(batch_ids) != 1:
        raise ValueError("a persisted batch must have exactly one batch_id")
    for annotation in annotations:
        packet = packets.get(annotation.mantra_id)
        if packet is None:
            raise ValueError(f"annotation has no selected packet: {annotation.mantra_id}")
        errors = validate_silver_annotation(annotation, packet)
        if errors:
            raise ValueError("; ".join(errors))

    existing = load_silver_annotations(annotations_path) if annotations_path.exists() else []
    merged = {item.mantra_id: item for item in existing}
    for annotation in annotations:
        if annotation.mantra_id in merged:
            raise ValueError(f"blind annotation already persisted: {annotation.mantra_id}")
        merged[annotation.mantra_id] = annotation
    ordered_batch = sorted(annotations, key=lambda item: item.mantra_id)
    _atomic_write_text(batch_path, _jsonl_text(ordered_batch))
    _atomic_write_text(annotations_path, _jsonl_text(merged[key] for key in sorted(merged)))


def load_silver_annotations(path: Path) -> list[SilverSemanticAnnotation]:
    return [
        SilverSemanticAnnotation.model_validate(json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def create_blind_review_seal(
    *,
    annotations_path: Path,
    seal_path: Path,
    packets: Mapping[str, EvidencePacket],
    selected_ids: frozenset[str],
    sealed_at: datetime | None = None,
) -> dict[str, object]:
    annotations = load_silver_annotations(annotations_path)
    by_id = {item.mantra_id: item for item in annotations}
    if len(annotations) != len(by_id):
        raise ValueError("duplicate mantra in silver annotation ledger")
    if set(by_id) != set(selected_ids):
        raise ValueError("blind seal requires exactly the selected benchmark ids")
    for mantra_id, annotation in by_id.items():
        errors = validate_silver_annotation(annotation, packets[mantra_id])
        if errors:
            raise ValueError("; ".join(errors))
    seal: dict[str, object] = {
        "seal_version": "rigveda-semantic-silver-blind-seal-v1",
        "run_id": SILVER_RUN_ID,
        "provenance": SILVER_PROVENANCE,
        "reviewer_model": SILVER_REVIEWER_MODEL,
        "reviewer_runtime": SILVER_RUNTIME,
        "reviewed_count": len(annotations),
        "selected_ids_sha256": canonical_json_sha256(sorted(selected_ids)),
        "annotations_file_sha256": file_sha256(annotations_path),
        "annotation_hashes": {key: annotation_sha256(by_id[key]) for key in sorted(by_id)},
        "evidence_packet_hashes": {key: packets[key].input_sha256 for key in sorted(selected_ids)},
        "sealed_at": (sealed_at or datetime.now(UTC)).isoformat(),
        "luna_output_revealed": False,
    }
    _atomic_write_text(
        seal_path, json.dumps(seal, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    return seal


def verify_blind_review_seal(
    *, annotations_path: Path, seal_path: Path, selected_ids: frozenset[str]
) -> dict[str, object]:
    raw: Any = json.loads(seal_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("blind seal is not an object")
    if raw.get("reviewed_count") != len(selected_ids):
        raise ValueError("blind seal count does not match selected benchmark")
    if raw.get("selected_ids_sha256") != canonical_json_sha256(sorted(selected_ids)):
        raise ValueError("blind seal selected-id hash mismatch")
    if raw.get("annotations_file_sha256") != file_sha256(annotations_path):
        raise ValueError("silver annotations changed after blind seal")
    annotations = load_silver_annotations(annotations_path)
    hashes = raw.get("annotation_hashes")
    if not isinstance(hashes, dict):
        raise ValueError("blind seal lacks annotation hashes")
    for annotation in annotations:
        if hashes.get(annotation.mantra_id) != annotation_sha256(annotation):
            raise ValueError(f"annotation hash mismatch: {annotation.mantra_id}")
    return raw


def _candidate_object_label(
    candidate: SemanticAssertionCandidate, packets: Mapping[str, EvidencePacket]
) -> str:
    if candidate.object.entity_key:
        key = candidate.object.entity_key
        packet = packets[candidate.subject_key]
        labels = dict(zip(packet.devata_keys, packet.devata_labels, strict=True))
        labels.update(zip(packet.rishi_keys, packet.rishi_labels, strict=True))
        labels.update(zip(packet.chandas_keys, packet.chandas_labels, strict=True))
        labels.update({item.entity_key: item.entity_label for item in packet.mentions})
        return labels.get(key, key)
    return candidate.object.candidate_entity_id or ""


def assess_luna_evidence(
    candidate: SemanticAssertionCandidate,
    packet: EvidencePacket,
    *,
    relation_supported: bool,
) -> SilverEvidenceAssessment:
    token_keys = packet.citable_token_keys
    translation_ids = _packet_reference_ids(packet)["TRANSLATION"]
    for evidence in candidate.evidence:
        if any(key not in token_keys for key in evidence.sanskrit_token_keys):
            return SilverEvidenceAssessment.TOKEN_REFERENCE_MISSING
        if evidence.translation_id and evidence.translation_id not in translation_ids:
            return SilverEvidenceAssessment.TRANSLATION_REFERENCE_MISSING
    if relation_supported:
        return SilverEvidenceAssessment.SUFFICIENT
    if candidate.object.entity_key in packet.devata_keys and not any(
        mention.entity_key == candidate.object.entity_key for mention in packet.mentions
    ):
        return SilverEvidenceAssessment.METADATA_ONLY
    if candidate.explicitness is Explicitness.INTERPRETIVE:
        return SilverEvidenceAssessment.TEXTUAL_OVERREACH
    return SilverEvidenceAssessment.AMBIGUOUS


def _same_object(left: str, right: str) -> bool:
    return normalize_label(left) == normalize_label(right)


def compare_annotations(
    annotations: Sequence[SilverSemanticAnnotation],
    luna_candidates: Sequence[SemanticAssertionCandidate],
    packets: Mapping[str, EvidencePacket],
) -> list[SilverComparison]:
    """Compare two model relation sets without treating either model as ground truth."""
    silver_by_id = {item.mantra_id: item for item in annotations}
    luna_by_id: dict[str, list[SemanticAssertionCandidate]] = defaultdict(list)
    for candidate in luna_candidates:
        if candidate.subject_key in silver_by_id:
            luna_by_id[candidate.subject_key].append(candidate)

    comparisons: list[SilverComparison] = []
    for mantra_id in sorted(silver_by_id):
        annotation = silver_by_id[mantra_id]
        sol = annotation.semantic_assertions
        luna = luna_by_id.get(mantra_id, [])
        if not sol and not luna:
            comparisons.append(
                SilverComparison(
                    mantra_id=mantra_id,
                    category=SilverComparisonCategory.NO_CLAIM_AGREEMENT,
                    reasoning="Both models emitted no supported relation for this packet.",
                )
            )
            continue

        matched_sol: set[int] = set()
        for candidate in luna:
            luna_label = _candidate_object_label(candidate, packets)
            exact = next(
                (
                    index
                    for index, assertion in enumerate(sol)
                    if index not in matched_sol
                    and assertion.predicate is candidate.predicate
                    and _same_object(assertion.object_label, luna_label)
                ),
                None,
            )
            if exact is not None:
                matched_sol.add(exact)
                exact_assertion = sol[exact]
                comparisons.append(
                    _comparison_row(
                        mantra_id,
                        SilverComparisonCategory.MATCH,
                        candidate,
                        exact_assertion,
                        luna_label,
                        assess_luna_evidence(
                            candidate, packets[mantra_id], relation_supported=True
                        ),
                        "Predicate and normalized object agree.",
                    )
                )
                continue

            same_predicate = next(
                (
                    (index, assertion)
                    for index, assertion in enumerate(sol)
                    if index not in matched_sol and assertion.predicate is candidate.predicate
                ),
                None,
            )
            same_object = next(
                (
                    (index, assertion)
                    for index, assertion in enumerate(sol)
                    if index not in matched_sol and _same_object(assertion.object_label, luna_label)
                ),
                None,
            )
            aligned_sol: SilverSemanticAssertion | None
            if same_predicate is not None:
                index, aligned_sol = same_predicate
                matched_sol.add(index)
                left_words = set(normalize_label(luna_label).split())
                right_words = set(normalize_label(aligned_sol.object_label).split())
                if left_words & right_words:
                    category = SilverComparisonCategory.PARTIAL_MATCH
                    reason = (
                        "Predicate agrees and object labels overlap, but entity granularity "
                        "differs."
                    )
                else:
                    category = SilverComparisonCategory.WRONG_ENTITY
                    reason = "Models chose the same predicate but different objects."
            elif same_object is not None:
                index, aligned_sol = same_object
                matched_sol.add(index)
                category = SilverComparisonCategory.WRONG_PREDICATE
                reason = "Models chose the same object but different predicates."
            else:
                aligned_sol = None
                if not sol:
                    category = (
                        SilverComparisonCategory.OVERINTERPRETATION
                        if candidate.explicitness is not Explicitness.EXPLICIT
                        else SilverComparisonCategory.UNSUPPORTED
                    )
                    reason = (
                        "Luna emitted a relation where the independent review found no support."
                    )
                else:
                    category = SilverComparisonCategory.DISAGREEMENT_REQUIRES_EXPERT
                    reason = (
                        "Luna relation has no aligned Sol relation; neither model is authoritative."
                    )
            assessment = assess_luna_evidence(
                candidate,
                packets[mantra_id],
                relation_supported=category
                in {SilverComparisonCategory.MATCH, SilverComparisonCategory.PARTIAL_MATCH},
            )
            if assessment in {
                SilverEvidenceAssessment.TOKEN_REFERENCE_MISSING,
                SilverEvidenceAssessment.TRANSLATION_REFERENCE_MISSING,
            }:
                category = SilverComparisonCategory.EVIDENCE_PROBLEM
                reason = "Luna cited evidence that is absent from the supplied packet."
            comparisons.append(
                _comparison_row(
                    mantra_id,
                    category,
                    candidate,
                    aligned_sol,
                    luna_label,
                    assessment,
                    reason,
                )
            )

        for index, assertion in enumerate(sol):
            if index in matched_sol:
                continue
            category = (
                SilverComparisonCategory.LUNA_MISSED_RELATION
                if assertion.explicitness is Explicitness.EXPLICIT
                else SilverComparisonCategory.SOL_ONLY_RELATION
            )
            comparisons.append(
                SilverComparison(
                    mantra_id=mantra_id,
                    category=category,
                    sol_assertion_id=assertion.assertion_id,
                    sol_predicate=assertion.predicate,
                    sol_object=assertion.object_label,
                    reasoning=(
                        "The sealed independent review found an explicit relation absent from Luna."
                        if category is SilverComparisonCategory.LUNA_MISSED_RELATION
                        else (
                            "The sealed independent review found a non-explicit relation "
                            "absent from Luna."
                        )
                    ),
                )
            )
    return comparisons


def _comparison_row(
    mantra_id: str,
    category: SilverComparisonCategory,
    luna: SemanticAssertionCandidate,
    sol: SilverSemanticAssertion | None,
    luna_label: str,
    evidence: SilverEvidenceAssessment,
    reasoning: str,
) -> SilverComparison:
    return SilverComparison(
        mantra_id=mantra_id,
        category=category,
        luna_assertion_id=luna.candidate_assertion_id,
        sol_assertion_id=sol.assertion_id if sol else None,
        luna_predicate=luna.predicate,
        sol_predicate=sol.predicate if sol else None,
        luna_object=luna_label,
        sol_object=sol.object_label if sol else None,
        evidence_assessment=evidence,
        reasoning=reasoning,
    )


def compare_after_blind_seal(
    *,
    annotations_path: Path,
    seal_path: Path,
    luna_candidates_path: Path,
    comparison_path: Path,
    packets: Mapping[str, EvidencePacket],
    selected_ids: frozenset[str],
) -> list[SilverComparison]:
    """Verify the complete independent ledger before the first Luna-output read."""
    verify_blind_review_seal(
        annotations_path=annotations_path, seal_path=seal_path, selected_ids=selected_ids
    )
    annotations = load_silver_annotations(annotations_path)
    luna_candidates = [
        SemanticAssertionCandidate.model_validate(json.loads(line))
        for line in luna_candidates_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    comparisons = compare_annotations(annotations, luna_candidates, packets)
    _atomic_write_text(comparison_path, _jsonl_text(comparisons))
    seal: Any = json.loads(seal_path.read_text(encoding="utf-8"))
    seal["luna_output_revealed"] = True
    seal["comparison_created_at"] = datetime.now(UTC).isoformat()
    seal["comparison_file_sha256"] = file_sha256(comparison_path)
    _atomic_write_text(
        seal_path, json.dumps(seal, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )
    return comparisons


@dataclass
class SilverAgreementMetrics:
    """Agreement measurements only; fields are intentionally not named gold accuracy."""

    mantra_count: int
    sol_assertion_count: int
    luna_assertion_count: int
    exact_matches: int
    partial_matches: int
    no_claim_agreements: int
    no_claim_union: int
    relation_set_agreements: int
    evidence_sufficient: int
    evidence_checked: int
    entity_agreements: int
    categories: Counter[str] = field(default_factory=Counter)
    predicate_rows: dict[str, dict[str, int]] = field(default_factory=dict)

    @property
    def silver_agreement_precision(self) -> float | None:
        return self.exact_matches / self.luna_assertion_count if self.luna_assertion_count else None

    @property
    def silver_agreement_recall(self) -> float | None:
        return self.exact_matches / self.sol_assertion_count if self.sol_assertion_count else None

    @property
    def no_claim_agreement(self) -> float | None:
        return self.no_claim_agreements / self.no_claim_union if self.no_claim_union else None

    @property
    def evidence_agreement(self) -> float | None:
        return self.evidence_sufficient / self.evidence_checked if self.evidence_checked else None

    @property
    def entity_agreement(self) -> float | None:
        return (
            self.entity_agreements / self.luna_assertion_count
            if self.luna_assertion_count
            else None
        )

    @property
    def disagreement_rate(self) -> float:
        agreed = self.exact_matches + self.no_claim_agreements
        return 1 - agreed / max(sum(self.categories.values()), 1)


def calculate_agreement_metrics(
    annotations: Sequence[SilverSemanticAnnotation],
    luna_candidates: Sequence[SemanticAssertionCandidate],
    comparisons: Sequence[SilverComparison],
) -> SilverAgreementMetrics:
    categories = Counter(item.category.value for item in comparisons)
    exact = categories[SilverComparisonCategory.MATCH.value]
    partial = categories[SilverComparisonCategory.PARTIAL_MATCH.value]
    no_claim = categories[SilverComparisonCategory.NO_CLAIM_AGREEMENT.value]
    luna_by_id = {item.subject_key for item in luna_candidates}
    sol_claim_ids = {item.mantra_id for item in annotations if item.semantic_assertions}
    no_claim_union = len({item.mantra_id for item in annotations} - (luna_by_id & sol_claim_ids))
    predicate_rows: dict[str, dict[str, int]] = {}
    for predicate in sorted(ALLOWED_PREDICATES, key=lambda item: item.value):
        sol_count = sum(
            1
            for annotation in annotations
            for assertion in annotation.semantic_assertions
            if assertion.predicate is predicate
        )
        luna_count = sum(1 for item in luna_candidates if item.predicate is predicate)
        matches = sum(
            1
            for item in comparisons
            if item.category is SilverComparisonCategory.MATCH and item.sol_predicate is predicate
        )
        predicate_rows[predicate.value] = {"sol": sol_count, "luna": luna_count, "match": matches}
    checked = [item for item in comparisons if item.luna_assertion_id is not None]
    sufficient = sum(
        1 for item in checked if item.evidence_assessment is SilverEvidenceAssessment.SUFFICIENT
    )
    entity_agreements = sum(
        1
        for item in checked
        if item.category
        in {
            SilverComparisonCategory.MATCH,
            SilverComparisonCategory.PARTIAL_MATCH,
            SilverComparisonCategory.WRONG_PREDICATE,
        }
    )
    relation_sets: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for item in comparisons:
        if item.category is SilverComparisonCategory.MATCH:
            relation_sets[item.mantra_id].add(
                ((item.sol_predicate or SemanticPredicate.DESCRIBES).value, item.sol_object or "")
            )
    relation_set_agreements = no_claim + sum(
        1
        for annotation in annotations
        if annotation.semantic_assertions
        and len(relation_sets[annotation.mantra_id]) == len(annotation.semantic_assertions)
        and all(
            (assertion.predicate.value, assertion.object_label)
            in relation_sets[annotation.mantra_id]
            for assertion in annotation.semantic_assertions
        )
    )
    return SilverAgreementMetrics(
        mantra_count=len(annotations),
        sol_assertion_count=sum(len(item.semantic_assertions) for item in annotations),
        luna_assertion_count=len(luna_candidates),
        exact_matches=exact,
        partial_matches=partial,
        no_claim_agreements=no_claim,
        no_claim_union=no_claim_union,
        relation_set_agreements=relation_set_agreements,
        evidence_sufficient=sufficient,
        evidence_checked=len(checked),
        entity_agreements=entity_agreements,
        categories=categories,
        predicate_rows=predicate_rows,
    )


def select_expert_audit_ids(
    comparisons: Sequence[SilverComparison],
    annotations: Sequence[SilverSemanticAnnotation],
    *,
    target_size: int = 25,
) -> list[str]:
    """Select a deterministic, predicate/category/Maṇḍala-diverse audit queue."""
    if not 20 <= target_size <= 30:
        raise ValueError("expert audit target must be between 20 and 30")
    by_id = {item.mantra_id: item for item in annotations}
    category_priority = {
        SilverComparisonCategory.EVIDENCE_PROBLEM: 100,
        SilverComparisonCategory.DISAGREEMENT_REQUIRES_EXPERT: 95,
        SilverComparisonCategory.WRONG_PREDICATE: 90,
        SilverComparisonCategory.WRONG_ENTITY: 85,
        SilverComparisonCategory.UNSUPPORTED: 80,
        SilverComparisonCategory.OVERINTERPRETATION: 75,
        SilverComparisonCategory.LUNA_MISSED_RELATION: 70,
        SilverComparisonCategory.SOL_ONLY_RELATION: 65,
        SilverComparisonCategory.PARTIAL_MATCH: 60,
        SilverComparisonCategory.MATCH: 20,
        SilverComparisonCategory.NO_CLAIM_AGREEMENT: 5,
    }
    score: Counter[str] = Counter()
    categories_by_id: dict[str, set[str]] = defaultdict(set)
    for item in comparisons:
        score[item.mantra_id] += category_priority[item.category]
        categories_by_id[item.mantra_id].add(item.category.value)
    for annotation in annotations:
        # Gaps and unresolved packet-bounded readings are especially valuable to a
        # domain expert, including cosmological riddles where both models may abstain.
        score[annotation.mantra_id] += 200 * len(annotation.ontology_gaps)
        score[annotation.mantra_id] += 50 * len(annotation.uncertainties)

    ranked = sorted(by_id, key=lambda key: (-score[key], key))
    selected: list[str] = []
    seen_mandalas: set[str] = set()
    seen_predicates: set[str] = set()
    seen_categories: set[str] = set()
    while len(selected) < min(target_size, len(ranked)):
        best = max(
            (key for key in ranked if key not in selected),
            key=lambda key: (
                20 if key.split(":")[3] not in seen_mandalas else 0,
                10
                * len(
                    {item.predicate.value for item in by_id[key].semantic_assertions}
                    - seen_predicates
                ),
                5 * len(categories_by_id[key] - seen_categories),
                score[key],
                key,
            ),
        )
        selected.append(best)
        seen_mandalas.add(best.split(":")[3])
        seen_predicates.update(item.predicate.value for item in by_id[best].semantic_assertions)
        seen_categories.update(categories_by_id[best])
    return selected


def load_comparisons(path: Path) -> list[SilverComparison]:
    return [
        SilverComparison.model_validate(json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
