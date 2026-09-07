"""Human semantic-gold storage, validation, signing, and packet indexing.

This module is intentionally independent of the extractor. Stage A records are written
from a reviewer's decisions and contain no model candidates. Stage B is a separate
append/update ledger. All evidence is an id checked against the local packet.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from vedagraph.models.semantic import (
    AdjudicationRecord,
    EvidencePacket,
    GoldAnnotation,
    GoldEvidenceReference,
)
from vedagraph.semantic.ontology import (
    ALLOWED_PREDICATES,
    EvidenceReferenceType,
    GoldReviewStatus,
    SemanticNodeType,
)

DEFAULT_GOLD_FILE = Path("data/gold/rigveda_semantic_gold_v1.jsonl")
DEFAULT_ADJUDICATION_FILE = Path("data/gold/semantic_gold_adjudication_rigveda_v1.jsonl")
DEFAULT_MANIFEST_FILE = Path("data/gold/rigveda_semantic_gold_v1.manifest.json")
DEFAULT_PILOT_CONFIG = Path("data/builds/rigveda_semantic_pilot_v1.yaml")
DEFAULT_PILOT_RUN = Path("data/semantic/vedagraph-rigveda-semantic-codex-luna-pilot-1.0.0-rc1")


@dataclass(frozen=True)
class GoldValidationReport:
    """All validation findings; an empty list is a passing report."""

    errors: tuple[str, ...] = ()
    expected_count: int = 0
    present_count: int = 0
    complete_count: int = 0
    status: GoldReviewStatus = GoldReviewStatus.UNANNOTATED

    @property
    def valid(self) -> bool:
        return not self.errors


@dataclass(frozen=True)
class GoldProgress:
    total: int
    blinded_complete: int
    adjudications_complete: int
    remaining: int
    last_saved: str | None
    status: GoldReviewStatus
    predicates: tuple[str, ...]


def utc_now() -> datetime:
    return datetime.now(UTC)


def expected_gold_ids(config_path: Path = DEFAULT_PILOT_CONFIG) -> dict[str, str]:
    """Return the configured 120 gold ids and citations, without opening source text."""
    document: Any = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    rows = document.get("mantras", []) if isinstance(document, dict) else []
    return {
        str(row["passage_key"]): str(row["citation"])
        for row in rows
        if isinstance(row, dict) and bool(row.get("gold"))
    }


def load_gold_records(path: Path = DEFAULT_GOLD_FILE) -> list[GoldAnnotation]:
    if not path.exists():
        return []
    records: list[GoldAnnotation] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            records.append(GoldAnnotation.model_validate(json.loads(line)))
        except Exception as error:
            raise ValueError(f"invalid GoldAnnotation at {path}:{line_number}") from error
    return records


def load_adjudications(path: Path = DEFAULT_ADJUDICATION_FILE) -> list[AdjudicationRecord]:
    if not path.exists():
        return []
    records: list[AdjudicationRecord] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            records.append(AdjudicationRecord.model_validate(json.loads(line)))
        except Exception as error:
            raise ValueError(f"invalid AdjudicationRecord at {path}:{line_number}") from error
    return records


def load_packet_index(run_dir: Path = DEFAULT_PILOT_RUN) -> dict[str, EvidencePacket]:
    """Load full local packets from batch evidence files.

    The pilot deliberately keeps these files gitignored because they contain source
    text. They are required locally for review and are never copied into gold JSONL.
    """
    packets: dict[str, EvidencePacket] = {}
    paths = sorted(run_dir.glob("batches/batch_*/evidence.jsonl"))
    if not paths:
        paths = [run_dir / "evidence.jsonl"] if (run_dir / "evidence.jsonl").exists() else []
    for path in paths:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                packet = EvidencePacket.model_validate(json.loads(line))
            except Exception as error:
                raise ValueError(f"invalid EvidencePacket at {path}:{line_number}") from error
            packets[packet.passage_key] = packet
    return packets


def _atomic_write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def save_gold_record(record: GoldAnnotation, path: Path = DEFAULT_GOLD_FILE) -> None:
    """Replace one row immediately and atomically, preserving all other rows."""
    records = load_gold_records(path)
    by_key = {item.passage_key: item for item in records}
    previous = by_key.get(record.passage_key)
    if (
        previous is not None
        and previous.review is not None
        and record.review is not None
        and previous.review != record.review
        and previous.review not in record.review_history
    ):
        record = record.model_copy(
            update={"review_history": [*record.review_history, previous.review]}
        )
    by_key[record.passage_key] = record
    _atomic_write_jsonl(
        path,
        [by_key[key].model_dump(mode="json", exclude_none=True) for key in sorted(by_key)],
    )


def save_adjudication(record: AdjudicationRecord, path: Path = DEFAULT_ADJUDICATION_FILE) -> None:
    existing = load_adjudications(path)
    by_key = {(item.mantra_id, item.candidate_assertion_id): item for item in existing}
    by_key[(record.mantra_id, record.candidate_assertion_id)] = record
    _atomic_write_jsonl(
        path,
        [item.model_dump(mode="json", exclude_none=True) for _, item in sorted(by_key.items())],
    )


def _packet_reference_ids(packet: EvidencePacket) -> dict[EvidenceReferenceType, set[str]]:
    translations = set()
    if packet.translation is not None:
        translations.add(packet.translation.translation_id)
    for neighbour in (packet.previous, packet.next):
        if neighbour is not None and neighbour.translation is not None:
            translations.add(neighbour.translation.translation_id)
    return {
        EvidenceReferenceType.PASSAGE: set(packet.citable_passage_keys),
        EvidenceReferenceType.TRANSLATION: translations,
        EvidenceReferenceType.TOKEN: set(packet.citable_token_keys),
        EvidenceReferenceType.ENTITY: set(
            packet.devata_keys + packet.rishi_keys + packet.chandas_keys
        )
        | {mention.entity_key for mention in packet.mentions},
        EvidenceReferenceType.TRADITIONAL_ASSERTION: set(
            packet.devata_keys + packet.rishi_keys + packet.chandas_keys
        ),
        EvidenceReferenceType.PARALLEL: set(
            packet.exact_parallel_passage_keys + packet.near_parallel_passage_keys
        ),
    }


def validate_evidence_reference(
    reference: GoldEvidenceReference, packet: EvidencePacket
) -> str | None:
    if reference.reference_id not in _packet_reference_ids(packet).get(reference.kind, set()):
        return f"{reference.kind.value} id is not present in packet: {reference.reference_id}"
    return None


def validate_annotation(
    annotation: GoldAnnotation,
    packet: EvidencePacket | None,
    *,
    require_complete: bool = False,
) -> tuple[str, ...]:
    """Validate ontology, evidence, identities, status, and Stage A invariants."""
    errors: list[str] = []
    status = annotation.effective_status
    if not annotation.effective_reviewer or annotation.effective_reviewer == "UNANNOTATED":
        errors.append("reviewer identity is missing")
    if annotation.effective_reviewed_at.year <= 1970:
        errors.append("review timestamp is missing")
    if require_complete and status not in {GoldReviewStatus.COMPLETE, GoldReviewStatus.SIGNED}:
        errors.append(f"status is not complete: {status.value}")
    if (
        status in {GoldReviewStatus.COMPLETE, GoldReviewStatus.SIGNED}
        and annotation.review is not None
    ):
        if not annotation.review.stage_a_locked:
            errors.append("complete row is not Stage A locked")
    if annotation.no_claim and annotation.effective_assertions:
        errors.append("no_claim cannot be true while supported assertions exist")
    if (
        annotation.gold_assertions
        and annotation.relations
        and annotation.gold_assertions != annotation.relations
    ):
        errors.append("legacy relations and gold_assertions disagree")

    for assertion in annotation.effective_assertions + annotation.rejected_tempting_relations:
        if assertion.predicate not in ALLOWED_PREDICATES:
            errors.append(f"predicate is not allowed: {assertion.predicate.value}")
        if assertion.object_entity_key is None and assertion.object_node_type is None:
            errors.append(
                f"assertion has no object ontology type or entity: {assertion.object_label}"
            )
        if packet is not None:
            if (
                assertion.object_entity_key is not None
                and assertion.object_entity_key
                not in _packet_reference_ids(packet)[EvidenceReferenceType.ENTITY]
            ):
                errors.append(f"entity is not present in packet: {assertion.object_entity_key}")
            for evidence in assertion.evidence:
                issue = validate_evidence_reference(evidence, packet)
                if issue:
                    errors.append(issue)

    for entity in annotation.gold_entities:
        if not isinstance(entity.node_type, SemanticNodeType):
            errors.append(f"invalid entity node type: {entity.node_type}")
        if entity.existing_entity_key is None and not entity.new_semantic_entity_candidate:
            errors.append(
                f"entity has neither canonical key nor new-candidate flag: {entity.preferred_label}"
            )
        if packet is not None:
            for evidence in entity.evidence:
                issue = validate_evidence_reference(evidence, packet)
                if issue:
                    errors.append(issue)
    if annotation.gold_modified_after_model_reveal and not annotation.modification_reason.strip():
        errors.append("gold modification after model reveal requires a reason")
    if annotation.model_revealed_at is not None and not annotation.review:
        # Legacy-compatible rows may use the direct field, but must still be auditable.
        if not annotation.gold_modified_after_model_reveal:
            pass
    return tuple(dict.fromkeys(errors))


def validate_gold_file(
    gold_path: Path = DEFAULT_GOLD_FILE,
    *,
    config_path: Path = DEFAULT_PILOT_CONFIG,
    run_dir: Path = DEFAULT_PILOT_RUN,
    require_complete: bool = False,
) -> GoldValidationReport:
    expected = expected_gold_ids(config_path)
    records = load_gold_records(gold_path)
    errors: list[str] = []
    by_key: dict[str, GoldAnnotation] = {}
    for record in records:
        if record.passage_key in by_key:
            errors.append(f"duplicate mantra id: {record.passage_key}")
        by_key[record.passage_key] = record
    missing = sorted(set(expected) - set(by_key))
    extra = sorted(set(by_key) - set(expected))
    errors.extend(f"missing mantra id: {key}" for key in missing)
    errors.extend(f"unexpected mantra id: {key}" for key in extra)
    packets = load_packet_index(run_dir) if run_dir.exists() else {}
    for key, record in sorted(by_key.items()):
        if key not in expected:
            continue
        if record.citation != expected[key]:
            errors.append(f"citation mismatch for {key}")
        packet = packets.get(key)
        if packet is None and record.effective_status != GoldReviewStatus.UNANNOTATED:
            errors.append(f"packet missing for annotated mantra: {key}")
        if record.effective_status != GoldReviewStatus.UNANNOTATED:
            errors.extend(
                f"{key}: {issue}"
                for issue in validate_annotation(record, packet, require_complete=require_complete)
            )
        raw = record.model_dump(mode="json")
        if _contains_model_data(raw):
            errors.append(f"model data found in gold record: {key}")
    statuses = [record.effective_status for record in by_key.values()]
    unannotated = sum(status is GoldReviewStatus.UNANNOTATED for status in statuses)
    if require_complete and unannotated:
        errors.append(f"{unannotated} rows are UNANNOTATED")
    complete = sum(
        status in {GoldReviewStatus.COMPLETE, GoldReviewStatus.SIGNED} for status in statuses
    )
    dataset_status = GoldReviewStatus.UNANNOTATED
    if complete == len(expected) and not errors:
        dataset_status = (
            GoldReviewStatus.SIGNED
            if by_key
            and all(
                record.effective_status is GoldReviewStatus.SIGNED for record in by_key.values()
            )
            else GoldReviewStatus.COMPLETE
        )
    if any(status is GoldReviewStatus.IN_PROGRESS for status in statuses):
        dataset_status = GoldReviewStatus.IN_PROGRESS
    if any(status is GoldReviewStatus.NEEDS_SECOND_REVIEW for status in statuses):
        dataset_status = GoldReviewStatus.NEEDS_SECOND_REVIEW
    return GoldValidationReport(
        errors=tuple(dict.fromkeys(errors)),
        expected_count=len(expected),
        present_count=len(by_key),
        complete_count=complete,
        status=dataset_status,
    )


def _contains_model_data(value: object) -> bool:
    forbidden = {"confidence", "model", "model_snapshot", "candidate_assertion_id", "candidate"}
    if isinstance(value, dict):
        if forbidden & set(value):
            return True
        return any(_contains_model_data(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_model_data(item) for item in value)
    return False


def progress(
    gold_path: Path = DEFAULT_GOLD_FILE,
    adjudication_path: Path = DEFAULT_ADJUDICATION_FILE,
    config_path: Path = DEFAULT_PILOT_CONFIG,
) -> GoldProgress:
    expected = expected_gold_ids(config_path)
    records = load_gold_records(gold_path)
    complete = [
        item
        for item in records
        if item.effective_status in {GoldReviewStatus.COMPLETE, GoldReviewStatus.SIGNED}
    ]
    adjudications = load_adjudications(adjudication_path)
    predicates = sorted(
        {assertion.predicate.value for item in complete for assertion in item.effective_assertions}
    )
    saved = max(complete, key=lambda item: item.effective_reviewed_at, default=None)
    statuses = [item.effective_status for item in records]
    status = GoldReviewStatus.UNANNOTATED
    if len(complete) == len(expected):
        status = (
            GoldReviewStatus.SIGNED
            if complete
            and all(item.effective_status is GoldReviewStatus.SIGNED for item in complete)
            else GoldReviewStatus.COMPLETE
        )
    if any(item is GoldReviewStatus.IN_PROGRESS for item in statuses):
        status = GoldReviewStatus.IN_PROGRESS
    if any(item is GoldReviewStatus.NEEDS_SECOND_REVIEW for item in statuses):
        status = GoldReviewStatus.NEEDS_SECOND_REVIEW
    return GoldProgress(
        total=len(expected),
        blinded_complete=len(complete),
        adjudications_complete=len({item.mantra_id for item in adjudications}),
        remaining=max(len(expected) - len(complete), 0),
        last_saved=saved.passage_key if saved else None,
        status=status,
        predicates=tuple(predicates),
    )


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finalize_gold(
    gold_path: Path = DEFAULT_GOLD_FILE,
    *,
    config_path: Path = DEFAULT_PILOT_CONFIG,
    run_dir: Path = DEFAULT_PILOT_RUN,
    manifest_path: Path = DEFAULT_MANIFEST_FILE,
    version: str = "vedagraph-rigveda-semantic-gold-v1",
) -> dict[str, object]:
    report = validate_gold_file(
        gold_path, config_path=config_path, run_dir=run_dir, require_complete=True
    )
    if not report.valid or report.complete_count != report.expected_count:
        raise ValueError(
            "gold is not complete; refusing to finalize: " + "; ".join(report.errors[:8])
        )
    records = load_gold_records(gold_path)
    signed_at = utc_now()
    signed_records: list[GoldAnnotation] = []
    for record in records:
        review = (
            record.review.model_copy(update={"status": GoldReviewStatus.SIGNED})
            if record.review is not None
            else None
        )
        signed_records.append(
            record.model_copy(update={"status": GoldReviewStatus.SIGNED, "review": review})
        )
    _atomic_write_jsonl(
        gold_path,
        [
            record.model_dump(mode="json", exclude_none=True)
            for record in sorted(signed_records, key=lambda item: item.passage_key)
        ],
    )
    reviewers = sorted({item.effective_reviewer for item in records})
    pilot_manifest = run_dir / "semantic_run_manifest.json"
    pilot = (
        json.loads(pilot_manifest.read_text(encoding="utf-8")) if pilot_manifest.exists() else {}
    )
    packet_index = load_packet_index(run_dir)
    payload: dict[str, object] = {
        "version": version,
        "gold_status": GoldReviewStatus.SIGNED.value,
        "signed_at": signed_at.isoformat(),
        "gold_sha256": sha256_file(gold_path),
        "reviewers": reviewers,
        "ontology_version": pilot.get("ontology_version", "rigveda-semantic-ontology-v1"),
        "corpus_manifest_sha256": pilot.get("corpus_manifest_sha256", ""),
        "lexical_manifest_sha256": pilot.get("lexical_knowledge_manifest_sha256", ""),
        "evidence_packet_hashes": {
            key: packet.input_sha256
            for key, packet in sorted(packet_index.items())
            if key in expected_gold_ids(config_path)
        },
        "gold_record_count": len(records),
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload
