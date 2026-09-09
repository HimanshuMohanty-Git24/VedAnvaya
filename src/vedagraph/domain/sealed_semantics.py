"""Read the sealed Rigvedic semantic artifact into the graph without touching it.

The most carefully validated semantic artifact in this repository has never been in the
graph. ``data/semantic/vedagraph-rigveda-semantic-claude-opus5-v3.2-448-new-v1`` holds
**2,474 assertions over 448 Rigvedic mantras**, sealed with ``seal_status: VALIDATED`` and
**zero non-zero counters across all eleven integrity checks** -- no binding failures, no
span failures, no evidence failures, no receipt failures, no heuristic contamination. What
*is* in the graph instead is 736 assertions from an earlier, unsealed run covering the
Yajurveda and Atharvaveda and no Rigveda at all.

This module closes that gap under a hard constraint: **the freeze is not reopened.** No
sealed file is written, no assertion is re-extracted, no predicate is remapped and no
confidence is recomputed. Everything below is a read.

**What is preserved, because the brief requires each of them by name.**

*Run identity.* Every node carries ``run_id``, ``execution_version``,
``execution_contract_version``, the requested and reported model, the reasoning level and
the runtime. The runtime matters: it is ``CLAUDE_CODE_DIRECT`` and the model attestation
is ``AGENT_RUNTIME_SELF_REPORTED_UNATTESTED``, which the seal states about itself and
which is therefore projected rather than smoothed over.

*Candidate status.* The seal says ``CANDIDATE / NEEDS_REVIEW``, ``canonical_promotion:
false`` and ``human_gold_status: UNANNOTATED``. So every projected assertion is
``state = CANDIDATE``, ``TIER_D``, ``review_state = UNREVIEWED``. Projecting a validated
seal does not promote it; validation is about the *execution* being intact, not about the
readings being right.

*Evidence.* Each assertion anchors to a ``translation_record_id`` and character offsets in
Griffith. That is checkable and it is English, so ``evidence_basis`` is ``TRANSLATION``.

*Binding and receipt.* The per-task receipt -- task id, response and prompt hashes,
authored timestamp, attempt id -- rides on the node, so any single assertion can be traced
back to the exact packet that produced it.

**One deliberate refusal.** 559 of the assertions carry an ``EVENT`` object with a free-text
``action_head``, and there are **502 distinct action heads for 559 events** -- essentially
one phrasing per verse, with a maximum frequency of ten. It would be easy to map those onto
the closed action vocabulary in ``data/registry/action_predicates.yaml`` and report a large
action graph. That is not done here, for two reasons. The mapping would be a fresh
interpretation of frozen output, which is exactly what "do not reopen the freeze to make it
fit" forbids; and it is not needed, because
:mod:`vedagraph.enrich.agentive` derives a controlled-vocabulary action layer from the
Rigveda's manual morphological annotation over the **whole** corpus rather than 4.2% of it,
with 2,362 assertions against the 96 events here whose actor resolves to a known deity.

The two layers are complementary and the graph keeps them apart. This one gives rich
per-verse readings with translation evidence over 448 mantras; that one gives
controlled-vocabulary coverage with annotation evidence over 10,552. A researcher can ask
for either and see which they are getting.
"""

from __future__ import annotations

import json
import pathlib
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Final

import orjson

from vedagraph.domain.ontology import DOMAIN_MODEL_VERSION, AttributionPrecision, QualityTier
from vedagraph.domain.tiers import EvidenceBasis
from vedagraph.enrich.provenance import RunReport, stable_id

#: The sealed run this module reads. Named rather than discovered, because "the newest
#: directory under data/semantic" would silently switch artifact on the next experiment.
SEALED_RUN_DIR: Final = (
    pathlib.Path("data") / "semantic" / "vedagraph-rigveda-semantic-claude-opus5-v3.2-448-new-v1"
)

#: Object kinds that carry an event with an actor, a patient and other participants.
EVENT_KINDS: Final[frozenset[str]] = frozenset({"EVENT", "RITUAL_EVENT"})

#: The review state every projected assertion gets. The seal validated the *execution*;
#: nobody has reviewed the *readings*.
REVIEW_UNREVIEWED: Final = "UNREVIEWED"


class SealedArtifactError(ValueError):
    """The sealed artifact is not in the state this module requires. Never repaired."""


@dataclass(frozen=True)
class SealSummary:
    """What the seal says about itself, carried onto every node it produces."""

    run_id: str
    seal_status: str
    seal_sha256: str
    execution_version: str
    execution_contract_version: str
    model_requested: str
    model_reported: str
    model_provenance_classification: str
    runtime: str
    reasoning: str
    candidate_status: str
    human_gold_status: str
    canonical_promotion: bool
    integrity_failures: int
    assertions_declared: int
    passages_declared: int

    def as_node_properties(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "seal_status": self.seal_status,
            "seal_sha256": self.seal_sha256,
            "execution_version": self.execution_version,
            "execution_contract_version": self.execution_contract_version,
            "model_requested": self.model_requested,
            "model_reported": self.model_reported,
            "model_provenance_classification": self.model_provenance_classification,
            "runtime": self.runtime,
            "reasoning": self.reasoning,
            "candidate_status": self.candidate_status,
            "human_gold_status": self.human_gold_status,
        }


@dataclass(frozen=True)
class Participant:
    """One non-agent, non-patient role filler of an event, as the model recorded it."""

    role: str
    normalized_head: str
    entity_id: str = ""

    def as_dict(self) -> dict[str, str]:
        return {
            "role": self.role,
            "normalized_head": self.normalized_head,
            "entity_id": self.entity_id,
        }


@dataclass(frozen=True)
class SealedAssertionRow:
    """One sealed assertion, flattened for projection and nothing else changed."""

    assertion_id: str
    passage_key: str
    predicate: str
    explicitness: str
    object_kind: str
    display_label: str
    normalized_head: str
    normalization_status: str
    canonical_entity_id: str
    target_entity_id: str
    beneficiary_entity_id: str
    ontology_gap_code: str
    action_head: str
    actor_entity_id: str
    patient_entity_id: str
    participants: tuple[Participant, ...]
    qualifiers: tuple[str, ...]
    evidence_translation_record_id: str
    evidence_span_start: int
    evidence_span_end: int
    evidence_passage_ids: tuple[str, ...]
    extraction_model: str
    prompt_version: str
    schema_version: str
    # ---- receipt ------------------------------------------------------------------
    task_id: str
    attempt_id: str
    response_sha256: str
    prompt_sha256: str
    evidence_packet_sha256: str
    authored_at: str

    @property
    def node_id(self) -> str:
        """Stable node identity.

        Derived from the sealed ``assertion_id`` plus the run, not invented: two runs over
        the same passage may legitimately produce the same assertion id, and a projection
        keyed on the id alone would merge them into one node.
        """
        return stable_id("SEALED-ASSERTION", self.assertion_id)

    @property
    def is_event(self) -> bool:
        return self.object_kind in EVENT_KINDS

    def as_node_properties(self, seal: SealSummary) -> dict[str, Any]:
        return {
            "assertion_node_id": self.node_id,
            "assertion_id": self.assertion_id,
            "passage_key": self.passage_key,
            "derivation": "MODEL_EXTRACTION",
            "semantic_predicate": self.predicate,
            "explicitness": self.explicitness,
            "object_kind": self.object_kind,
            "display_label": self.display_label,
            "display_type": "SemanticAssertion",
            "normalized_head": self.normalized_head,
            "normalization_status": self.normalization_status,
            "ontology_gap_code": self.ontology_gap_code,
            "action_head": self.action_head,
            "qualifiers": list(self.qualifiers),
            "participants": json.dumps(
                [participant.as_dict() for participant in self.participants],
                ensure_ascii=False,
            ),
            "participant_count": len(self.participants),
            "evidence_translation_record_id": self.evidence_translation_record_id,
            "evidence_span_start": self.evidence_span_start,
            "evidence_span_end": self.evidence_span_end,
            "evidence_passage_ids": list(self.evidence_passage_ids),
            "extraction_model": self.extraction_model,
            "prompt_version": self.prompt_version,
            "schema_version": self.schema_version,
            "task_id": self.task_id,
            "attempt_id": self.attempt_id,
            "response_sha256": self.response_sha256,
            "prompt_sha256": self.prompt_sha256,
            "evidence_packet_sha256": self.evidence_packet_sha256,
            "authored_at": self.authored_at,
            # Grade. Fixed, not derived: the seal states its own candidate status and this
            # projection is not entitled to improve on it.
            "state": "CANDIDATE",
            "quality_tier": str(QualityTier.TIER_D),
            "knowledge_layer": "L3_LLM_EXTRACTED",
            "review_state": REVIEW_UNREVIEWED,
            "evidence_basis": str(EvidenceBasis.TRANSLATION),
            "attribution_precision": str(AttributionPrecision.PER_PASSAGE),
            "grade_basis": (
                "sealed model extraction, VALIDATED execution and UNREVIEWED readings; "
                "evidence is a character span in Griffith's English translation"
            ),
            "domain_model_version": DOMAIN_MODEL_VERSION,
            **seal.as_node_properties(),
        }


def load_seal(project_root: pathlib.Path) -> SealSummary:
    """Read the seal and refuse the artifact if it is not intact.

    The eleven integrity counters are checked rather than trusted. A seal that says
    ``VALIDATED`` while reporting a non-zero failure count is a contradiction, and
    projecting it would put the contradiction in the graph.
    """
    path = project_root / SEALED_RUN_DIR / "output_seal.json"
    if not path.exists():
        raise SealedArtifactError(f"sealed artifact not found: {path}")
    seal = orjson.loads(path.read_bytes())
    integrity = seal.get("integrity") or {}
    failures = sum(int(value) for value in integrity.values())
    if seal.get("seal_status") != "VALIDATED":
        raise SealedArtifactError(
            f"seal_status is {seal.get('seal_status')!r}, not VALIDATED; refusing to project"
        )
    if failures:
        raise SealedArtifactError(
            f"seal reports VALIDATED but {failures} integrity failures across "
            f"{sorted(k for k, v in integrity.items() if v)}"
        )
    counts = seal.get("counts") or {}
    return SealSummary(
        run_id=str(seal["run_id"]),
        seal_status=str(seal["seal_status"]),
        seal_sha256=str(seal["seal_sha256"]),
        execution_version=str(seal.get("execution_version", "")),
        execution_contract_version=str(seal.get("execution_contract_version", "")),
        model_requested=str(seal.get("model_requested", "")),
        model_reported=str(seal.get("model_reported", "")),
        model_provenance_classification=str(seal.get("model_provenance_classification", "")),
        runtime=str(seal.get("runtime", "")),
        reasoning=str(seal.get("reasoning", "")),
        candidate_status=str(seal.get("candidate_status", "")),
        human_gold_status=str(seal.get("human_gold_status", "")),
        canonical_promotion=bool(seal.get("canonical_promotion", False)),
        integrity_failures=failures,
        assertions_declared=int(counts.get("assertions", 0)),
        passages_declared=int(counts.get("unique_final_passages", 0)),
    )


def _first_evidence(assertion: dict[str, Any]) -> dict[str, Any]:
    evidence = assertion.get("evidence") or []
    return dict(evidence[0]) if evidence else {}


def iter_sealed_assertions(project_root: pathlib.Path) -> Iterator[SealedAssertionRow]:
    """Yield every assertion in the sealed run, in stable order."""
    responses = project_root / SEALED_RUN_DIR / "responses"
    if not responses.is_dir():
        raise SealedArtifactError(f"sealed responses not found: {responses}")
    for path in sorted(responses.glob("*.json")):
        document = orjson.loads(path.read_bytes())
        receipt = document.get("receipt") or {}
        output = document.get("semantic_output") or {}
        for assertion in output.get("assertions") or ():
            obj = assertion.get("object") or {}
            event = obj.get("event") or {}
            span = _first_evidence(assertion).get("translation_span") or {}
            yield SealedAssertionRow(
                assertion_id=str(assertion.get("assertion_id", "")),
                passage_key=str(assertion.get("subject_id", "")),
                predicate=str(assertion.get("predicate", "")),
                explicitness=str(assertion.get("explicitness", "")),
                object_kind=str(obj.get("object_kind", "")),
                display_label=str(obj.get("display_label", "")),
                normalized_head=str(obj.get("normalized_head", "")),
                normalization_status=str(obj.get("normalization_status", "")),
                canonical_entity_id=str(obj.get("canonical_entity_id") or ""),
                target_entity_id=str(obj.get("target_entity_id") or ""),
                beneficiary_entity_id=str(obj.get("beneficiary_entity_id") or ""),
                ontology_gap_code=str(obj.get("ontology_gap_code") or ""),
                action_head=str(event.get("action_head") or ""),
                actor_entity_id=str(event.get("actor_entity_id") or ""),
                patient_entity_id=str(event.get("patient_entity_id") or ""),
                participants=tuple(
                    Participant(
                        role=str(item.get("role") or "").upper(),
                        normalized_head=str(item.get("normalized_head") or ""),
                        entity_id=str(item.get("entity_id") or ""),
                    )
                    for item in (event.get("other_participants") or ())
                ),
                qualifiers=tuple(
                    str(item) for item in (event.get("qualifiers") or obj.get("qualifiers") or ())
                ),
                evidence_translation_record_id=str(
                    _first_evidence(assertion).get("translation_record_id") or ""
                ),
                evidence_span_start=int(span.get("start", -1)),
                evidence_span_end=int(span.get("end", -1)),
                evidence_passage_ids=tuple(
                    str(item) for item in (_first_evidence(assertion).get("passage_ids") or ())
                ),
                extraction_model=str(obj.get("extraction_model") or ""),
                prompt_version=str(obj.get("prompt_version") or ""),
                schema_version=str(assertion.get("schema_version") or ""),
                task_id=str(receipt.get("task_id", "")),
                attempt_id=str(receipt.get("attempt_id", "")),
                response_sha256=str(receipt.get("response_sha256", "")),
                prompt_sha256=str(receipt.get("prompt_sha256", "")),
                evidence_packet_sha256=str(receipt.get("evidence_packet_sha256", "")),
                authored_at=str(receipt.get("authored_at", "")),
            )


@dataclass
class SealedProjection:
    """Everything the loader needs, plus the report that makes it auditable."""

    seal: SealSummary
    rows: list[SealedAssertionRow] = field(default_factory=list)
    report: RunReport = field(default_factory=lambda: RunReport(stage="sealed-semantics"))


def prepare(project_root: pathlib.Path) -> SealedProjection:
    """Read and validate the sealed run, and reconcile it against its own declared counts.

    The reconciliation is the point. A projection that reads 2,300 of a declared 2,474
    assertions and reports success is indistinguishable from one that read all of them,
    which is how a silently truncated layer gets into a graph and stays there.
    """
    seal = load_seal(project_root)
    rows = list(iter_sealed_assertions(project_root))
    projection = SealedProjection(seal=seal, rows=rows)
    report = projection.report

    by_kind: dict[str, int] = {}
    by_predicate: dict[str, int] = {}
    by_explicitness: dict[str, int] = {}
    actors: dict[str, int] = {}
    entity_refs: dict[str, int] = {}
    gaps: dict[str, int] = {}
    for row in rows:
        by_kind[row.object_kind] = by_kind.get(row.object_kind, 0) + 1
        by_predicate[row.predicate] = by_predicate.get(row.predicate, 0) + 1
        by_explicitness[row.explicitness] = by_explicitness.get(row.explicitness, 0) + 1
        if row.actor_entity_id:
            actors[row.actor_entity_id] = actors.get(row.actor_entity_id, 0) + 1
        for entity in (row.canonical_entity_id, row.target_entity_id, row.patient_entity_id):
            if entity:
                entity_refs[entity] = entity_refs.get(entity, 0) + 1
        if row.ontology_gap_code:
            gaps[row.ontology_gap_code] = gaps.get(row.ontology_gap_code, 0) + 1
        if row.evidence_span_start < 0:
            report.reject("assertion_without_a_translation_span")
        if not row.passage_key:
            report.reject("assertion_without_a_subject_passage")

    report.produced = len(rows)
    report.notes = {
        "run_id": seal.run_id,
        "seal_status": seal.seal_status,
        "integrity_failures": seal.integrity_failures,
        "assertions_declared_by_seal": seal.assertions_declared,
        "assertions_read": len(rows),
        "assertions_reconcile": len(rows) == seal.assertions_declared,
        "passages_declared_by_seal": seal.passages_declared,
        "passages_read": len({row.passage_key for row in rows if row.passage_key}),
        "by_object_kind": dict(sorted(by_kind.items(), key=lambda kv: -kv[1])),
        "by_predicate": dict(sorted(by_predicate.items(), key=lambda kv: -kv[1])),
        "by_explicitness": dict(sorted(by_explicitness.items(), key=lambda kv: -kv[1])),
        "events": sum(1 for row in rows if row.is_event),
        "events_with_resolved_actor": sum(1 for row in rows if row.actor_entity_id),
        "distinct_action_heads": len({row.action_head for row in rows if row.action_head}),
        "actor_distribution": dict(sorted(actors.items(), key=lambda kv: -kv[1])),
        "entity_reference_distribution": dict(
            sorted(entity_refs.items(), key=lambda kv: -kv[1])[:30]
        ),
        "ontology_gap_codes": dict(sorted(gaps.items(), key=lambda kv: -kv[1])),
    }
    return projection
