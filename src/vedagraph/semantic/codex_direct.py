"""The CODEX_DIRECT execution contract: a model authors the payload, Python validates it.

There is no API and no key. The model runtime is Codex itself, so "the model ran" cannot
be inferred from a function call — it has to be evidenced by an artefact the model
authored. That is what this module is for:

    packet -> PreparedTask (frozen, no semantics)
           -> the agent reads the task and writes a response file
           -> ModelExecutionReceipt + semantic output, hashed
           -> ReceiptValidator + SemanticPayloadValidator
           -> ValidatedResponse -> BatchStore

Three properties are load-bearing.

**Prepare authors nothing.** :func:`prepare_task` has no path to a predicate, an object, a
confidence or an explicitness. A task is an evidence packet plus the hashes of what it was
pinned against, and that is checked by test rather than promised by comment.

**Import fabricates nothing.** :meth:`ExecutionStore.import_response` reads a response file
that already exists. No file, no semantic output — there is no branch that synthesises one,
which is precisely the defect (B03) that made the previous V3 pilots look like Luna runs
when they were regular expressions.

**Provenance is recorded, never invented.** Codex exposes no immutable server build
identifier, so the receipt records ``provider_build_metadata: UNAVAILABLE`` rather than a
plausible string. What is guaranteed is the requested model, the runtime, the reasoning
setting, the task/prompt/schema/packet hashes and the exact authored response bytes.
Matching outputs across two runs are reported as observed replication agreement under a
pinned configuration; they are never called model determinism.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from vedagraph.models.normalization import SemanticExtractionV3
from vedagraph.models.semantic import EvidencePacket
from vedagraph.semantic.evidence import payload_objects, validate_evidence_anchors
from vedagraph.semantic.object_ontology import SemanticObjectKind
from vedagraph.semantic.ontology import SemanticPredicate
from vedagraph.semantic.spans import span_errors
from vedagraph.semantic.v3 import PROMPT_VERSION, validate_v3_payload

EXECUTION_CONTRACT_VERSION = "codex-direct-semantic-v1"

#: The execution version the next real model run must use. The V3 pilot, replication and
#: 508 identities are retired: they name heuristic artefacts and may not be reused.
EXECUTION_VERSION = "rigveda-semantic-execution-v3.1"
REGRESSION_RUN_ID = "vedagraph-rigveda-semantic-luna-v3.1-regression"


class ExecutionRuntime(StrEnum):
    """Which agent runtime authored a response.

    ``CODEX_DIRECT`` names the contract's original runtime. It is not a synonym for the
    contract: a Claude Code agent authoring the payload under the same rules is a
    different runtime and says so, because a receipt that named the wrong runtime would
    be the same class of defect as B03 -- provenance that looks like evidence and is not.
    Neither value is provider-attested; both mean "an agent runtime authored this and
    Python validated it".
    """

    CODEX_DIRECT = "CODEX_DIRECT"
    CLAUDE_CODE_DIRECT = "CLAUDE_CODE_DIRECT"


RUNTIME = ExecutionRuntime.CODEX_DIRECT
PROVIDER_BUILD_METADATA_UNAVAILABLE = "UNAVAILABLE"

#: Predicates whose object is a canonical entity must name the anchor that identifies or
#: addresses *that* entity. A name occurring elsewhere in the verse is not an address.
CANONICAL_TARGET_PREDICATES = frozenset(
    {
        SemanticPredicate.INVOKES,
        SemanticPredicate.PRAISES,
        SemanticPredicate.DESCRIBES,
    }
)

_DIGEST = r"^[0-9a-f]{64}$"

#: ``prompt_version: <value>`` inside the YAML front matter of a prompt file. The policy a
#: run executes is read from the same bytes the run hashes, so the two cannot disagree.
_PROMPT_VERSION_LINE = re.compile(r"^prompt_version:\s*(?P<version>\S+)\s*$", re.MULTILINE)


def read_prompt_version(prompt_path: Path) -> str:
    """The prompt policy version a prompt file declares in its front matter.

    Fails closed. A run whose prompt does not say which policy it is cannot record honest
    provenance for the objects authored under it, and that is worse than not running.
    """
    text = prompt_path.read_text(encoding="utf-8")
    head = text.split("---", 2)[1] if text.startswith("---") else ""
    match = _PROMPT_VERSION_LINE.search(head)
    if match is None:
        raise ValueError(f"{prompt_path} declares no prompt_version in its front matter")
    return match.group("version")


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RunContract(ContractModel):
    """What one execution run is pinned to. Task and receipt must both agree with it."""

    execution_contract_version: Literal["codex-direct-semantic-v1"] = "codex-direct-semantic-v1"
    execution_version: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    model_requested: str = Field(min_length=1)
    reasoning_requested: str = Field(min_length=1)
    prompt_sha256: str = Field(pattern=_DIGEST)
    schema_sha256: str = Field(pattern=_DIGEST)
    ontology_sha256: str = Field(pattern=_DIGEST)
    #: Which prompt policy the run executes. Defaulted so a contract stored before the
    #: field existed still loads as what it was: the policy the v3.1 runs used.
    prompt_version: str = Field(default=PROMPT_VERSION, min_length=1)
    #: Which agent runtime the run is executed by. Defaulted for the same reason.
    runtime: ExecutionRuntime = ExecutionRuntime.CODEX_DIRECT


def load_run_contract(
    *,
    run_id: str,
    prompt_path: Path,
    schema_path: Path,
    ontology_path: Path,
    model_requested: str,
    reasoning_requested: str,
    execution_version: str = EXECUTION_VERSION,
    runtime: ExecutionRuntime = ExecutionRuntime.CODEX_DIRECT,
) -> RunContract:
    """Pin a run to the exact bytes of its prompt, schema and ontology."""
    return RunContract(
        execution_version=execution_version,
        run_id=run_id,
        model_requested=model_requested,
        reasoning_requested=reasoning_requested,
        runtime=runtime,
        prompt_sha256=file_sha256(prompt_path),
        schema_sha256=file_sha256(schema_path),
        ontology_sha256=file_sha256(ontology_path),
        prompt_version=read_prompt_version(prompt_path),
    )


def task_id_for(run_id: str, passage_key: str) -> str:
    return "TASK:" + hashlib.sha256(f"{run_id}|{passage_key}".encode()).hexdigest()[:20].upper()


class PreparedTask(ContractModel):
    """One immutable model task: one evidence packet and the hashes it is pinned against.

    Deliberately has no field capable of holding a semantic claim.
    """

    execution_contract_version: Literal["codex-direct-semantic-v1"] = "codex-direct-semantic-v1"
    execution_version: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    task_id: str = Field(pattern=r"^TASK:[0-9A-F]{20}$")
    passage_id: str = Field(min_length=1)
    citation: str = Field(min_length=1)
    model_requested: str = Field(min_length=1)
    reasoning_requested: str = Field(min_length=1)
    prompt_sha256: str = Field(pattern=_DIGEST)
    schema_sha256: str = Field(pattern=_DIGEST)
    ontology_sha256: str = Field(pattern=_DIGEST)
    evidence_packet_sha256: str = Field(pattern=_DIGEST)
    evidence_packet: EvidencePacket

    @model_validator(mode="after")
    def packet_matches(self) -> PreparedTask:
        if self.evidence_packet.passage_key != self.passage_id:
            raise ValueError("task passage id and packet disagree")
        if self.evidence_packet.citation != self.citation:
            raise ValueError("task citation and packet disagree")
        if self.evidence_packet.input_sha256 != self.evidence_packet_sha256:
            raise ValueError("task packet hash and packet disagree")
        if self.task_id != task_id_for(self.run_id, self.passage_id):
            raise ValueError("task id is not derived from its run and passage")
        return self

    @property
    def task_sha256(self) -> str:
        """Hash of the canonicalized task bytes, which is what a receipt commits to."""
        return canonical_sha256(self.model_dump(mode="json"))


def prepare_task(packet: EvidencePacket, contract: RunContract) -> PreparedTask:
    """Freeze one extraction task. Generates no semantic content of any kind."""
    return PreparedTask(
        execution_version=contract.execution_version,
        run_id=contract.run_id,
        task_id=task_id_for(contract.run_id, packet.passage_key),
        passage_id=packet.passage_key,
        citation=packet.citation,
        model_requested=contract.model_requested,
        reasoning_requested=contract.reasoning_requested,
        prompt_sha256=contract.prompt_sha256,
        schema_sha256=contract.schema_sha256,
        ontology_sha256=contract.ontology_sha256,
        evidence_packet_sha256=packet.input_sha256,
        evidence_packet=packet,
    )


class BindingRole(StrEnum):
    """Which part of an assertion an anchor is offered as evidence for."""

    RELATION = "RELATION"
    TARGET = "TARGET"
    OUTCOME = "OUTCOME"


class BindingAnchor(ContractModel):
    """An assertion-specific stretch of the translation, quoted exactly.

    ``text`` is redundant with the offsets on purpose: it turns a wrong offset into a
    detectable error rather than a silent one.
    """

    role: BindingRole
    translation_record_id: str = Field(min_length=1)
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    text: str = Field(min_length=1)
    entity_id: str | None = None

    @model_validator(mode="after")
    def consistent(self) -> BindingAnchor:
        if self.end <= self.start:
            raise ValueError("binding anchor end must be greater than start")
        if len(self.text) != self.end - self.start:
            raise ValueError("binding anchor text length does not match its offsets")
        return self


class AssertionBinding(ContractModel):
    """The evidence that belongs to one assertion, rather than to the verse at large."""

    assertion_id: str = Field(min_length=1)
    anchors: list[BindingAnchor] = Field(min_length=1)

    def roles(self) -> set[BindingRole]:
        return {anchor.role for anchor in self.anchors}

    def by_role(self, role: BindingRole) -> list[BindingAnchor]:
        return [anchor for anchor in self.anchors if anchor.role is role]


class ModelExecutionReceipt(ContractModel):
    """What the model runtime actually reported, and what it committed to.

    Nothing here is inferred. ``provider_build_metadata`` stays ``UNAVAILABLE`` unless the
    runtime genuinely exposes a build identifier; a fabricated one would be worse than no
    provenance at all, because it would look like evidence.
    """

    execution_contract_version: Literal["codex-direct-semantic-v1"] = "codex-direct-semantic-v1"
    execution_version: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    task_id: str = Field(pattern=r"^TASK:[0-9A-F]{20}$")
    passage_id: str = Field(min_length=1)
    requested_model: str = Field(min_length=1)
    reported_model: str = Field(min_length=1)
    runtime: ExecutionRuntime = ExecutionRuntime.CODEX_DIRECT
    reasoning: str = Field(min_length=1)
    provider_build_metadata: str = PROVIDER_BUILD_METADATA_UNAVAILABLE
    task_sha256: str = Field(pattern=_DIGEST)
    prompt_sha256: str = Field(pattern=_DIGEST)
    schema_sha256: str = Field(pattern=_DIGEST)
    evidence_packet_sha256: str = Field(pattern=_DIGEST)
    response_sha256: str = Field(pattern=_DIGEST)
    model_response_authored: Literal[True] = True
    attempt_id: str = Field(pattern=r"^attempt_\d{3}$")
    authored_at: datetime


class ModelAuthoredResponse(ContractModel):
    """One response file exactly as the model runtime wrote it."""

    receipt: ModelExecutionReceipt
    semantic_output: SemanticExtractionV3
    assertion_bindings: list[AssertionBinding] = Field(default_factory=list)


def response_payload_sha256(response: ModelAuthoredResponse) -> str:
    """Hash of everything the model authored, excluding the receipt that commits to it."""
    return canonical_sha256(
        {
            "semantic_output": response.semantic_output.model_dump(mode="json"),
            "assertion_bindings": [
                item.model_dump(mode="json") for item in response.assertion_bindings
            ],
        }
    )


@dataclass(frozen=True)
class ValidatedResponse:
    """A response that passed receipt, payload, evidence and binding validation.

    Only :meth:`ExecutionStore.import_response` constructs one, which is how the full-run
    store is stopped from accepting a payload no model authored.
    """

    task: PreparedTask
    receipt: ModelExecutionReceipt
    payload: SemanticExtractionV3
    bindings: tuple[AssertionBinding, ...]
    raw_response_sha256: str

    @property
    def passage_key(self) -> str:
        return self.task.passage_id


def validate_receipt(
    receipt: ModelExecutionReceipt,
    task: PreparedTask,
    contract: RunContract,
    *,
    computed_response_sha256: str,
) -> list[str]:
    """The receipt against the task it claims to answer and the run it belongs to."""
    against_task: list[tuple[str, object, object]] = [
        (
            "execution contract version",
            receipt.execution_contract_version,
            task.execution_contract_version,
        ),
        ("execution version", receipt.execution_version, task.execution_version),
        ("run id", receipt.run_id, task.run_id),
        ("passage id", receipt.passage_id, task.passage_id),
        ("task hash", receipt.task_sha256, task.task_sha256),
        ("prompt hash", receipt.prompt_sha256, task.prompt_sha256),
        ("schema hash", receipt.schema_sha256, task.schema_sha256),
        ("evidence packet hash", receipt.evidence_packet_sha256, task.evidence_packet_sha256),
        ("requested model", receipt.requested_model, task.model_requested),
        ("reasoning", receipt.reasoning, task.reasoning_requested),
        ("response hash", receipt.response_sha256, computed_response_sha256),
        ("runtime", receipt.runtime, contract.runtime),
    ]
    against_contract: list[tuple[str, object, object]] = [
        ("run id", task.run_id, contract.run_id),
        ("execution version", task.execution_version, contract.execution_version),
        ("requested model", task.model_requested, contract.model_requested),
        ("reasoning", task.reasoning_requested, contract.reasoning_requested),
        ("prompt hash", task.prompt_sha256, contract.prompt_sha256),
        ("schema hash", task.schema_sha256, contract.schema_sha256),
        ("ontology hash", task.ontology_sha256, contract.ontology_sha256),
    ]
    errors = [
        f"receipt {name} does not match the prepared task: {found!r} != {expected!r}"
        for name, found, expected in against_task
        if found != expected
    ]
    errors += [
        f"task {name} does not match the run contract: {found!r} != {expected!r}"
        for name, found, expected in against_contract
        if found != expected
    ]
    return errors


def validate_candidate_invariants(
    payload: SemanticExtractionV3,
    task: PreparedTask,
    *,
    prompt_version: str = PROMPT_VERSION,
) -> list[str]:
    """Candidate-only invariants, including the provenance the payload claims for itself.

    ``prompt_version`` is the policy the run contract pins, not a module constant: an
    object authored under v3.2 must say so, and one authored under the v3 policy must not.
    """
    errors: list[str] = []
    if payload.mantra_id != task.evidence_packet.citation:
        errors.append("semantic output names a different mantra than the task")
    errors += [
        f"{assertion.assertion_id}: assertion run id differs from the task"
        for assertion in payload.assertions
        if assertion.source_run_id != task.run_id
    ]
    for candidate in payload_objects(payload):
        if candidate.extraction_model != task.model_requested:
            errors.append(
                f"{candidate.candidate_id}: object claims model {candidate.extraction_model!r}, "
                f"the run requested {task.model_requested!r}"
            )
        if candidate.prompt_version != prompt_version:
            errors.append(f"{candidate.candidate_id}: object prompt version differs from the run")
    identifiers = [item.assertion_id for item in payload.assertions]
    identifiers += [item.candidate_id for item in payload_objects(payload)]
    if len(identifiers) != len(set(identifiers)):
        errors.append("duplicate assertion or object identifiers")
    return errors


def _target_errors(
    label: str,
    canonical_entity_id: str | None,
    binding: AssertionBinding,
    packet: EvidencePacket,
) -> list[str]:
    targets = binding.by_role(BindingRole.TARGET)
    if not targets:
        return [
            f"{label}: a canonical-entity relation needs an anchor that identifies or "
            "addresses that entity"
        ]
    supplied = {mention.entity_key for mention in packet.mentions}
    errors: list[str] = []
    for anchor in targets:
        if anchor.entity_id is None:
            errors.append(f"{label}: the target anchor does not name the entity it identifies")
        elif anchor.entity_id != canonical_entity_id:
            errors.append(
                f"{label}: the target anchor identifies {anchor.entity_id}, "
                f"but the assertion object is {canonical_entity_id}"
            )
        elif anchor.entity_id not in supplied:
            errors.append(f"{label}: the target entity is not a supplied lexical mention")
    return errors


def validate_bindings(
    payload: SemanticExtractionV3,
    bindings: list[AssertionBinding],
    packet: EvidencePacket,
) -> list[str]:
    """Assertion-specific binding evidence: B01's contract, enforced without semantics.

    The validator cannot read Sanskrit and does not try. What it can require is that the
    model say *which* words carry the relation and *which* words identify its target, that
    those words really are at those offsets, and that neither of them is the whole verse.
    A cue somewhere in the translation and an entity somewhere else no longer combine.
    """
    translation = packet.translation
    text = translation.text if translation and translation.text else ""
    by_assertion = {item.assertion_id: item for item in bindings}
    errors: list[str] = []
    if len(by_assertion) != len(bindings):
        errors.append("duplicate assertion bindings")
    known = {item.assertion_id for item in payload.assertions}
    errors += [
        f"binding {identifier} does not belong to any assertion"
        for identifier in sorted(set(by_assertion) - known)
    ]
    for assertion in payload.assertions:
        label = assertion.assertion_id
        binding = by_assertion.get(label)
        if binding is None:
            errors.append(f"{label}: no assertion-specific binding evidence was supplied")
            continue
        for anchor in binding.anchors:
            if translation is None or anchor.translation_record_id != translation.translation_id:
                errors.append(f"{label}: binding anchor is not the packet translation")
                continue
            errors += [
                f"{label} {anchor.role.value} anchor: {message}"
                for message in span_errors(text, anchor.start, anchor.end, claimed_text=anchor.text)
            ]
            if anchor.start == 0 and anchor.end == len(text):
                errors.append(
                    f"{label} {anchor.role.value} anchor: a whole-verse span is not "
                    "assertion-specific evidence"
                )
        roles = binding.roles()
        if BindingRole.RELATION not in roles:
            errors.append(f"{label}: no anchor identifies the relation wording")
        if (
            assertion.predicate in CANONICAL_TARGET_PREDICATES
            and assertion.object.object_kind is SemanticObjectKind.CANONICAL_ENTITY_REF
        ):
            errors += _target_errors(label, assertion.object.canonical_entity_id, binding, packet)
        if assertion.predicate is SemanticPredicate.REQUESTS and BindingRole.OUTCOME not in roles:
            errors.append(f"{label}: REQUESTS needs an anchor on the requested outcome itself")
        relation_spans = {
            (anchor.start, anchor.end) for anchor in binding.by_role(BindingRole.RELATION)
        }
        if any(
            (anchor.start, anchor.end) in relation_spans
            for anchor in binding.anchors
            if anchor.role is not BindingRole.RELATION
        ):
            errors.append(
                f"{label}: the relation anchor and its target/outcome anchor are the same span"
            )
    return errors


class ExecutionStore:
    """Immutable custody of prepared tasks and the responses authored against them.

    A raw receipt is written once and never rewritten. A retry is a new attempt id with its
    own receipt; the previous attempt stays exactly where it was, because the record of
    what the model said the first time is the point.
    """

    def __init__(self, root: Path) -> None:
        self.root = root

    def task_dir(self, task_id: str) -> Path:
        return self.root / "tasks" / task_id.replace(":", "_")

    def write_task(self, task: PreparedTask) -> Path:
        """Persist a prepared task. Re-preparing is fine; preparing it differently is not."""
        path = self.task_dir(task.task_id) / "task.json"
        payload = (
            json.dumps(
                task.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, indent=2
            ).encode("utf-8")
            + b"\n"
        )
        if path.exists() and path.read_bytes() != payload:
            raise ValueError(f"{task.task_id} is already prepared with different content")
        _atomic_bytes(path, payload)
        return path

    def load_task(self, task_id: str) -> PreparedTask:
        path = self.task_dir(task_id) / "task.json"
        if not path.exists():
            raise FileNotFoundError(f"no prepared task for {task_id}; run prepare first")
        return PreparedTask.model_validate_json(path.read_text(encoding="utf-8"))

    def import_response(self, response_path: Path, contract: RunContract) -> ValidatedResponse:
        """Consume a response the model already authored. Never authors one.

        Fails closed on a missing file, a task that was never prepared, any hash that does
        not match, provenance claiming a model the run did not request, evidence that is
        not in the packet, and an assertion without its own binding evidence.
        """
        if not response_path.exists():
            raise FileNotFoundError(
                f"{response_path} does not exist; a model-authored response is required "
                "before any semantic output can be imported"
            )
        raw = response_path.read_bytes()
        response = ModelAuthoredResponse.model_validate_json(raw.decode("utf-8"))
        task = self.load_task(response.receipt.task_id)
        packet = task.evidence_packet
        errors = validate_receipt(
            response.receipt,
            task,
            contract,
            computed_response_sha256=response_payload_sha256(response),
        )
        errors += validate_candidate_invariants(
            response.semantic_output, task, prompt_version=contract.prompt_version
        )
        canonical = frozenset(mention.entity_key for mention in packet.mentions)
        errors += validate_v3_payload(
            response.semantic_output, packet, canonical_entity_ids=canonical
        )
        errors += validate_evidence_anchors(response.semantic_output, packet)
        errors += validate_bindings(response.semantic_output, response.assertion_bindings, packet)
        if errors:
            raise ValueError("; ".join(sorted(set(errors))))
        validated = ValidatedResponse(
            task=task,
            receipt=response.receipt,
            payload=response.semantic_output,
            bindings=tuple(response.assertion_bindings),
            raw_response_sha256=hashlib.sha256(raw).hexdigest(),
        )
        self._persist(validated, raw)
        return validated

    def _persist(self, validated: ValidatedResponse, raw: bytes) -> None:
        directory = (
            self.task_dir(validated.task.task_id) / "attempts" / validated.receipt.attempt_id
        )
        receipt_path = directory / "raw_response.json"
        if receipt_path.exists():
            if receipt_path.read_bytes() != raw:
                raise ValueError(
                    f"{validated.receipt.attempt_id} already holds a different raw receipt; "
                    "a retry needs a new attempt id"
                )
            return
        _atomic_bytes(receipt_path, raw)
        _atomic_bytes(
            directory / "validated.json",
            json.dumps(
                {
                    "task_id": validated.task.task_id,
                    "passage_id": validated.task.passage_id,
                    "attempt_id": validated.receipt.attempt_id,
                    "raw_response_sha256": validated.raw_response_sha256,
                    "response_sha256": validated.receipt.response_sha256,
                    "semantic_output": validated.payload.model_dump(mode="json"),
                },
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            ).encode("utf-8")
            + b"\n",
        )
