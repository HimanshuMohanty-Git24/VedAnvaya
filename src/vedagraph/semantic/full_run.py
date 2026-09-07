"""Offline batch custody and resume safety. No extraction or model invocation exists here.

The caller supplies already authored V3 payloads. A single-writer lock protects each
transaction; outputs land before checkpoints so an interrupted commit can be recovered.
This is mechanical infrastructure, not permission to start a semantic run.

Model output reaches a run through :meth:`BatchStore.commit_receipts`, which accepts only
a ``ValidatedResponse`` — a type that exists only downstream of a model-authored receipt.
The deterministic heuristic baseline cannot construct one and cannot satisfy the model
provenance check either, so it has no path into a run whose provenance claims a model.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from vedagraph.models.normalization import SemanticExtractionV3
from vedagraph.models.semantic import EvidencePacket
from vedagraph.semantic.codex_direct import EXECUTION_CONTRACT_VERSION, ValidatedResponse
from vedagraph.semantic.evidence import validate_evidence_anchors
from vedagraph.semantic.packet import packet_input_hash
from vedagraph.semantic.v3 import PROMPT_VERSION, validate_v3_payload

#: What a model-authored object must claim in its model field. The deterministic heuristic
#: baseline records DETERMINISTIC_HEURISTIC_BASELINE instead, so its payloads are refused
#: here rather than quietly entering a run whose provenance says a model produced them.
MODEL_PROVENANCE = "gpt-5.6-luna"

Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
REQUIRED_ROLES = frozenset(
    {
        "corpus_manifest",
        "traditional_manifest",
        "lexical_manifest",
        "morphology",
        "prompt",
        "schema",
        "object_ontology",
        "semantic_ontology",
        "explicitness_policy",
        "normalization_policy",
        "packet_schema",
        "packet_builder",
        "packet_model",
        "object_model",
        "validator",
        "runtime_lock",
        "operations",
        # Added with execution version v3.1: the model-execution contract and the two
        # evidence validators are inputs to a run exactly as the prompt and schema are.
        "execution_contract",
        "evidence_validator",
        "span_validator",
    }
)


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def file_hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Freeze(ContractModel):
    run_id: str = Field(pattern=r"^[a-z0-9][a-z0-9.-]+$")
    files: dict[str, Digest]
    roles: dict[str, str]
    passage_ids: list[str]
    model: Literal["gpt-5.6-luna"] = "gpt-5.6-luna"
    reasoning: Literal["high"] = "high"
    runtime: Literal["CODEX_DIRECT"] = "CODEX_DIRECT"
    runtime_version: str = Field(min_length=1)
    execution_contract_version: Literal["codex-direct-semantic-v1"] = "codex-direct-semantic-v1"
    candidate_status: Literal["CANDIDATE / NEEDS_REVIEW"] = "CANDIDATE / NEEDS_REVIEW"
    provenance: Literal["LLM_EXTRACTED / MODEL_CANDIDATE"] = "LLM_EXTRACTED / MODEL_CANDIDATE"
    unlocked_predicates: list[str] = Field(default_factory=list, max_length=0)
    human_gold_status: Literal["UNANNOTATED"] = "UNANNOTATED"

    @model_validator(mode="after")
    def complete(self) -> Freeze:
        if not REQUIRED_ROLES <= self.roles.keys():
            raise ValueError("missing required freeze roles")
        if any(path not in self.files for path in self.roles.values()):
            raise ValueError("role without a frozen file")
        validate_ids(self.passage_ids, expected_count=10552)
        return self

    def verify(self, repository: Path, corpus_ids: list[str]) -> None:
        validate_ids(corpus_ids, expected_count=10552)
        if self.passage_ids != sorted(corpus_ids):
            raise ValueError("full corpus ID set changed")
        for name, expected in self.files.items():
            path = (repository / name).resolve()
            if not path.is_relative_to(repository.resolve()) or file_hash(path) != expected:
                raise ValueError(f"frozen input changed: {name}; require new extraction version")


def validate_ids(ids: list[str], *, expected_count: int) -> None:
    if len(ids) != expected_count or len(set(ids)) != expected_count:
        raise ValueError("incomplete or duplicate ID set")
    if any(not re.fullmatch(r"VG:RV:SAK:M(?:0[1-9]|10):S\d{3}:V\d{3}", key) for key in ids):
        raise ValueError("invalid mantra ID")


class Batch(ContractModel):
    batch_id: str = Field(pattern=r"^batch_\d{4}$")
    mantra_ids: list[str] = Field(min_length=1, max_length=30)


class Plan(ContractModel):
    run_id: str
    freeze_hash: Digest
    batch_size: int = Field(ge=20, le=30)
    passage_ids: list[str]
    batches: list[Batch]

    @model_validator(mode="after")
    def deterministic(self) -> Plan:
        validate_ids(self.passage_ids, expected_count=len(self.passage_ids))
        if not self.passage_ids or self.passage_ids != sorted(self.passage_ids):
            raise ValueError("IDs must be nonempty and sorted")
        expected = [
            Batch(
                batch_id=f"batch_{i // self.batch_size + 1:04d}",
                mantra_ids=self.passage_ids[i : i + self.batch_size],
            )
            for i in range(0, len(self.passage_ids), self.batch_size)
        ]
        if self.batches != expected:
            raise ValueError("batch plan changed or duplicates introduced")
        return self


def make_plan(run_id: str, ids: list[str], freeze_hash: str, batch_size: int = 24) -> Plan:
    ids = sorted(ids)
    return Plan(
        run_id=run_id,
        freeze_hash=freeze_hash,
        batch_size=batch_size,
        passage_ids=ids,
        batches=[
            Batch(batch_id=f"batch_{i // batch_size + 1:04d}", mantra_ids=ids[i : i + batch_size])
            for i in range(0, len(ids), batch_size)
        ],
    )


class Checkpoint(ContractModel):
    run_id: str
    batch_id: str
    mantra_ids: list[str]
    packet_hashes: dict[str, Digest]
    plan_hash: Digest
    status: Literal["PENDING", "EXTRACTED", "VALIDATED", "FAILED", "SEALED"] = "PENDING"
    output_hash: Digest | None = None
    validator_result: list[str] = Field(default_factory=list)
    completed_timestamp: str | None = None

    @model_validator(mode="after")
    def status_fields(self) -> Checkpoint:
        if len(set(self.mantra_ids)) != len(self.mantra_ids):
            raise ValueError("duplicate checkpoint IDs")
        if set(self.packet_hashes) != set(self.mantra_ids):
            raise ValueError("checkpoint packet coverage mismatch")
        if self.status in {"EXTRACTED", "VALIDATED", "SEALED"} and not self.output_hash:
            raise ValueError("completed output needs a hash")
        if self.status in {"VALIDATED", "SEALED"}:
            if self.validator_result or not self.completed_timestamp:
                raise ValueError("validated checkpoint requires clean validation and timestamp")
        if self.status == "FAILED" and not self.validator_result:
            raise ValueError("failure needs a diagnostic")
        return self


def validate_recorded_payload(
    payload: SemanticExtractionV3,
    packet: EvidencePacket,
    run_id: str,
    *,
    prompt_version: str = PROMPT_VERSION,
) -> list[str]:
    """Supplement legacy validation with complete anchor and nested-ID membership checks.

    ``prompt_version`` is the policy the run executes. It defaults to the v3 policy the
    recorded pilots were authored under, so a stored payload keeps meaning what it meant.
    """
    canonical = frozenset(m.entity_key for m in packet.mentions)
    errors = validate_v3_payload(payload, packet, canonical_entity_ids=canonical)
    objects = [a.object for a in payload.assertions] + payload.ontology_gaps
    anchors = [e for a in payload.assertions for e in a.evidence]
    anchors += [e for obj in objects for e in obj.evidence]
    allowed_other = {f"LEXICAL_MENTION:{key}" for key in canonical}
    for obj in objects:
        if obj.source_passage_id != packet.passage_key:
            errors.append("object outside packet")
        if obj.extraction_model != MODEL_PROVENANCE:
            errors.append("object model differs from freeze")
        if obj.prompt_version != prompt_version:
            errors.append("object prompt differs from freeze")
        entity_ids = [obj.canonical_entity_id, obj.beneficiary_entity_id, obj.target_entity_id]
        if obj.event:
            entity_ids += [obj.event.actor_entity_id, obj.event.patient_entity_id]
            entity_ids += [p.entity_id for p in obj.event.other_participants]
        if any(key is not None and key not in canonical for key in entity_ids):
            errors.append("unknown nested canonical entity ID")
    for anchor in anchors:
        if anchor.source_passage_id != packet.passage_key:
            errors.append("anchor outside packet")
        if not set(anchor.token_ids) <= packet.citable_token_keys:
            errors.append("invalid token anchor")
        if not set(anchor.passage_ids) <= packet.citable_passage_keys:
            errors.append("invalid passage anchor")
        if not set(anchor.other_evidence_ids) <= allowed_other:
            errors.append("invalid other evidence anchor")
        if anchor.translation_record_id:
            if (
                not packet.translation
                or anchor.translation_record_id != packet.translation.translation_id
            ):
                errors.append("invalid translation anchor")
            elif anchor.translation_span:
                span = anchor.translation_span
                if not 0 <= span.start < span.end <= len(packet.translation.text or ""):
                    errors.append("invalid translation span")
    errors += validate_evidence_anchors(payload, packet)
    if any(a.source_run_id != run_id for a in payload.assertions):
        errors.append("assertion run ID differs from checkpoint")
    ids = [a.assertion_id for a in payload.assertions] + [obj.candidate_id for obj in objects]
    if len(ids) != len(set(ids)):
        errors.append("duplicate assertion/object IDs")
    return sorted(set(errors))


class BatchStore:
    """Single-writer, restartable custody of recorded outputs, never a model runner.

    Concurrent or abandoned locks fail closed. A human/operator must verify the old
    writer is dead before removing an abandoned lock; never auto-expire a live lease.
    """

    def __init__(self, root: Path, plan: Plan, *, prompt_version: str = PROMPT_VERSION):
        self.root = root
        self.prompt_version = prompt_version
        self.plan = Plan.model_validate(plan.model_dump())
        self.plan_hash = digest(self.plan.model_dump(mode="json"))
        root.mkdir(parents=True, exist_ok=True)
        with self.lock():
            path = root / "plan.json"
            if path.exists():
                if digest(json.loads(path.read_text(encoding="utf-8"))) != self.plan_hash:
                    raise ValueError("existing plan hash mismatch")
            else:
                atomic_json(path, self.plan.model_dump(mode="json"))

    @contextmanager
    def lock(self) -> Iterator[None]:
        path = self.root / ".writer.lock"
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        try:
            os.write(fd, str(os.getpid()).encode())
            yield
        finally:
            os.close(fd)
            path.unlink()

    def _batch(self, batch_id: str) -> Batch:
        return next(b for b in self.plan.batches if b.batch_id == batch_id)

    def _checkpoint(self, batch_id: str) -> Checkpoint:
        checkpoint = Checkpoint.model_validate_json(
            (self.root / batch_id / "checkpoint.json").read_text(encoding="utf-8")
        )
        batch = self._batch(batch_id)
        if (
            checkpoint.run_id != self.plan.run_id
            or checkpoint.batch_id != batch_id
            or checkpoint.mantra_ids != batch.mantra_ids
            or checkpoint.plan_hash != self.plan_hash
        ):
            raise ValueError("checkpoint identity mismatch")
        return checkpoint

    def _save(self, checkpoint: Checkpoint) -> None:
        checked = Checkpoint.model_validate(checkpoint.model_dump())
        atomic_json(
            self.root / checked.batch_id / "checkpoint.json", checked.model_dump(mode="json")
        )

    def prepare(self, batch_id: str, packets: list[EvidencePacket]) -> Checkpoint:
        with self.lock():
            batch = self._batch(batch_id)
            if [p.passage_key for p in packets] != batch.mantra_ids:
                raise ValueError("batch packet IDs/order mismatch")
            for packet in packets:
                actual = packet_input_hash(packet.model_dump(mode="json", exclude={"input_sha256"}))
                if actual != packet.input_sha256:
                    raise ValueError("packet hash mismatch")
            hashes = {p.passage_key: p.input_sha256 for p in packets}
            path = self.root / batch_id / "packets.json"
            rows = [p.model_dump(mode="json") for p in packets]
            if path.exists() and json.loads(path.read_text(encoding="utf-8")) != rows:
                raise ValueError("frozen batch packets changed")
            cp_path = self.root / batch_id / "checkpoint.json"
            if cp_path.exists():
                cp = self._checkpoint(batch_id)
                if cp.packet_hashes != hashes:
                    raise ValueError("checkpoint packet hashes changed")
                return cp
            if (self.root / "seal.json").exists():
                raise ValueError("run already sealed")
            atomic_json(path, rows)
            cp = Checkpoint(
                run_id=self.plan.run_id,
                batch_id=batch_id,
                mantra_ids=batch.mantra_ids,
                packet_hashes=hashes,
                plan_hash=self.plan_hash,
            )
            self._save(cp)
            return cp

    def _validate_output(self, batch_id: str) -> tuple[Checkpoint, list[SemanticExtractionV3]]:
        cp = self._checkpoint(batch_id)
        directory = self.root / batch_id
        packets = [
            EvidencePacket.model_validate(p)
            for p in json.loads((directory / "packets.json").read_text(encoding="utf-8"))
        ]
        if [p.passage_key for p in packets] != cp.mantra_ids:
            raise ValueError("stored packet IDs changed")
        for p in packets:
            if (
                packet_input_hash(p.model_dump(mode="json", exclude={"input_sha256"}))
                != cp.packet_hashes[p.passage_key]
            ):
                raise ValueError("stored packet hash mismatch")
            if p.input_sha256 != cp.packet_hashes[p.passage_key]:
                raise ValueError("declared packet hash mismatch")
        output = directory / "output.json"
        if cp.output_hash and file_hash(output) != cp.output_hash:
            raise ValueError("batch output hash mismatch")
        payloads = [
            SemanticExtractionV3.model_validate(p)
            for p in json.loads(output.read_text(encoding="utf-8"))
        ]
        if len(payloads) != len(packets):
            raise ValueError("batch output coverage mismatch")
        errors = [
            e
            for payload, packet in zip(payloads, packets, strict=True)
            for e in validate_recorded_payload(
                payload, packet, self.plan.run_id, prompt_version=self.prompt_version
            )
        ]
        if errors:
            raise ValueError("; ".join(errors))
        return cp, payloads

    def commit(self, batch_id: str, payloads: list[SemanticExtractionV3]) -> Checkpoint:
        with self.lock():
            cp = self._checkpoint(batch_id)
            if cp.status != "PENDING" or (self.root / "seal.json").exists():
                raise ValueError("batch already processed; use recovery or explicit retry")
            output = self.root / batch_id / "output.json"
            if output.exists():
                raise ValueError("orphan output exists; recover without re-extraction")
            atomic_json(output, [p.model_dump(mode="json") for p in payloads])
            cp.status = "EXTRACTED"
            cp.output_hash = file_hash(output)
            self._save(cp)
            return self._recover(batch_id)

    def commit_receipts(self, batch_id: str, responses: list[ValidatedResponse]) -> Checkpoint:
        """The only supported way for model output to enter a full run.

        A ``ValidatedResponse`` is constructible only by
        ``ExecutionStore.import_response``, which requires a model-authored receipt whose
        task, prompt, schema and packet hashes all check out. The deterministic heuristic
        baseline cannot produce one, and its payloads are rejected downstream anyway
        because they do not carry the run's model in their provenance. The separation is
        in the types, not in an operator's discipline.
        """
        batch = self._batch(batch_id)
        if [response.passage_key for response in responses] != batch.mantra_ids:
            raise ValueError("batch response IDs/order mismatch")
        if any(response.task.run_id != self.plan.run_id for response in responses):
            raise ValueError("response run ID differs from the plan")
        if any(
            response.receipt.execution_contract_version != EXECUTION_CONTRACT_VERSION
            for response in responses
        ):
            raise ValueError("response execution contract differs from this build")
        return self.commit(batch_id, [response.payload for response in responses])

    def _recover(self, batch_id: str) -> Checkpoint:
        cp = self._checkpoint(batch_id)
        try:
            _, _payloads = self._validate_output(batch_id)
        except (ValueError, OSError) as exc:
            if cp.status in {"VALIDATED", "SEALED"}:
                raise ValueError("completed batch verification failed") from exc
            cp.status = "FAILED"
            cp.validator_result = [str(exc)]
            self._save(cp)
            return cp
        cp.output_hash = file_hash(self.root / batch_id / "output.json")
        if cp.status != "SEALED":
            cp.status = "VALIDATED"
        cp.validator_result = []
        cp.completed_timestamp = cp.completed_timestamp or datetime.now(UTC).isoformat()
        self._save(cp)
        return cp

    def recover(self, batch_id: str) -> Checkpoint:
        with self.lock():
            return self._recover(batch_id)

    def retry_failed(self, batch_id: str) -> Checkpoint:
        with self.lock():
            cp = self._checkpoint(batch_id)
            if cp.status != "FAILED" or (self.root / "seal.json").exists():
                raise ValueError("only failed unsealed batches can be retried")
            output = self.root / batch_id / "output.json"
            if output.exists():
                destination = output.with_name(f"failed-{file_hash(output)}.json")
                if destination.exists():
                    raise ValueError("identical failed attempt already archived")
                os.replace(output, destination)
            cp.status = "PENDING"
            cp.output_hash = None
            cp.validator_result = []
            cp.completed_timestamp = None
            self._save(cp)
            return cp

    def _aggregate(self) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        ids: set[str] = set()
        for batch in self.plan.batches:
            if not (self.root / batch.batch_id / "checkpoint.json").exists():
                raise ValueError("all batches must be validated before aggregation/seal")
            cp, payloads = self._validate_output(batch.batch_id)
            if cp.status not in {"VALIDATED", "SEALED"}:
                raise ValueError("all batches must be validated before aggregation/seal")
            for payload in payloads:
                current = [a.assertion_id for a in payload.assertions]
                current += [a.object.candidate_id for a in payload.assertions]
                current += [g.candidate_id for g in payload.ontology_gaps]
                if ids.intersection(current):
                    raise ValueError("cross-batch duplicate assertion/object IDs")
                ids.update(current)
                rows.append(payload.model_dump(mode="json"))
        return rows

    def regenerate(self) -> Path:
        with self.lock():
            rows = self._aggregate()
            path = self.root / "aggregate.json"
            atomic_json(path, rows)
            return path

    def seal(self, freeze: Freeze, repository: Path, corpus_ids: list[str]) -> str:
        with self.lock():
            freeze.verify(repository, corpus_ids)
            if (
                digest(freeze.model_dump(mode="json")) != self.plan.freeze_hash
                or freeze.passage_ids != self.plan.passage_ids
                or freeze.run_id != self.plan.run_id
            ):
                raise ValueError("full-run freeze/plan mismatch")
            rows = self._aggregate()
            atomic_json(self.root / "aggregate.json", rows)
            batch_records = {
                b.batch_id: self._checkpoint(b.batch_id).model_dump(mode="json")
                for b in self.plan.batches
            }
            seal = {
                "run_id": self.plan.run_id,
                "plan_hash": self.plan_hash,
                "freeze_hash": self.plan.freeze_hash,
                "candidate_status": freeze.candidate_status,
                "unlocked_predicates": [],
                "aggregate_hash": file_hash(self.root / "aggregate.json"),
                "batches": batch_records,
            }
            # Normalize status so re-sealing after partial checkpoint updates is idempotent.
            for record in batch_records.values():
                record["status"] = "SEALED"
            seal_hash = digest(seal)
            path = self.root / "seal.json"
            if path.exists() and json.loads(path.read_text(encoding="utf-8")) != seal:
                raise ValueError("existing full-run seal differs")
            atomic_json(path, seal)
            for batch in self.plan.batches:
                cp = self._checkpoint(batch.batch_id)
                cp.status = "SEALED"
                self._save(cp)
            return seal_hash
