"""Materialise one model-authored v3.1 draft from an explicit decision record.

The decision records are authored by the model while reading one PreparedTask at a time.
This module performs no lexical matching or semantic selection: it only turns a declared
record into the schema object and resolves the exact evidence spans named by that record.
Receipt construction remains delegated to ``persist_codex_direct_response.py``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from vedagraph.models.normalization import (
    ActionEvent,
    EventParticipant,
    SemanticEvidenceAnchor,
    SemanticExtractionV3,
    SemanticObjectCandidate,
    StructuredSemanticAssertion,
)
from vedagraph.semantic.codex_direct import BindingAnchor, BindingRole, PreparedTask
from vedagraph.semantic.object_ontology import (
    SemanticObjectKind,
    SemanticObjectNormalizationStatus,
)
from vedagraph.semantic.ontology import Explicitness, SemanticPredicate
from vedagraph.semantic.spans import resolve_anchor

RUN_ID = "vedagraph-rigveda-semantic-luna-v3.1-508"
PROMPT_VERSION = "rigveda-semantic-extraction-v3"
MODEL = "gpt-5.6-luna"


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:20].upper()


def task_path(store: Path, task_id: str) -> Path:
    return store / "tasks" / task_id.replace(":", "_") / "task.json"


def find_span(text: str, phrase: str, occurrence: int | None) -> tuple[int, int, str]:
    anchor = resolve_anchor(text, phrase, occurrence=occurrence, ignore_case=True)
    return anchor.start, anchor.end, anchor.text


def translation_anchor(
    task: PreparedTask, phrase: str, occurrence: int | None
) -> tuple[dict[str, Any], BindingAnchor]:
    translation = task.evidence_packet.translation
    if translation is None or not translation.text:
        raise ValueError(f"{task.passage_id}: asserted decision requires a supplied translation")
    start, end, actual = find_span(translation.text, phrase, occurrence)
    evidence = {
        "source_passage_id": task.passage_id,
        "translation_record_id": translation.translation_id,
        "translation_span": {"start": start, "end": end},
    }
    binding = BindingAnchor(
        role=BindingRole.RELATION,
        translation_record_id=translation.translation_id,
        start=start,
        end=end,
        text=actual,
    )
    return evidence, binding


def role_anchor(
    task: PreparedTask,
    role: BindingRole,
    phrase: str,
    occurrence: int | None,
    entity_id: str | None = None,
) -> tuple[dict[str, Any], BindingAnchor]:
    translation = task.evidence_packet.translation
    if translation is None or not translation.text:
        raise ValueError(f"{task.passage_id}: binding requires a supplied translation")
    start, end, actual = find_span(translation.text, phrase, occurrence)
    evidence = {
        "source_passage_id": task.passage_id,
        "translation_record_id": translation.translation_id,
        "translation_span": {"start": start, "end": end},
    }
    binding = BindingAnchor(
        role=role,
        translation_record_id=translation.translation_id,
        start=start,
        end=end,
        text=actual,
        entity_id=entity_id,
    )
    return evidence, binding


def status_for(kind: SemanticObjectKind) -> SemanticObjectNormalizationStatus:
    if kind is SemanticObjectKind.CANONICAL_ENTITY_REF:
        return SemanticObjectNormalizationStatus.CANONICAL_REF
    return SemanticObjectNormalizationStatus.NEEDS_REVIEW


def event_from_spec(spec: dict[str, Any]) -> ActionEvent:
    participants = [
        EventParticipant.model_validate(item) for item in spec.get("other_participants", [])
    ]
    return ActionEvent(
        action_head=str(spec["action_head"]),
        actor_entity_id=spec.get("actor_entity_id"),
        patient_entity_id=spec.get("patient_entity_id"),
        other_participants=participants,
        qualifiers=[str(item) for item in spec.get("qualifiers", [])],
    )


def build_draft(task: PreparedTask, decision: dict[str, Any]) -> dict[str, Any]:
    if task.run_id != RUN_ID:
        raise ValueError(f"foreign task run: {task.run_id}")
    if decision.get("passage_key") != task.passage_id:
        raise ValueError(f"decision/task passage mismatch: {decision.get('passage_key')}")
    if decision.get("decision") not in {"NO_CLAIM", "ASSERTIONS"}:
        raise ValueError(f"invalid decision state for {task.passage_id}")

    assertions: list[StructuredSemanticAssertion] = []
    bindings: list[dict[str, Any]] = []
    translation = task.evidence_packet.translation
    if decision["decision"] == "NO_CLAIM":
        if not decision.get("no_claim_reasons"):
            raise ValueError(f"{task.passage_id}: no-claim decision needs an authored reason")
    else:
        specs = decision.get("assertions")
        if not isinstance(specs, list) or not specs:
            raise ValueError(f"{task.passage_id}: ASSERTIONS needs at least one assertion")
        if translation is None or not translation.text:
            raise ValueError(f"{task.passage_id}: assertions cannot be bound without translation")
        for ordinal, spec_value in enumerate(specs, start=1):
            spec = dict(spec_value)
            predicate = SemanticPredicate(str(spec["predicate"]))
            kind = SemanticObjectKind(str(spec["object_kind"]))
            assertion_id = "VG:SEMASSERT:" + digest(
                f"{RUN_ID}|{task.passage_id}|{predicate.value}|{ordinal}"
            )
            candidate_id = "VG:SEMOBJ:" + digest(
                f"{RUN_ID}|{task.passage_id}|{predicate.value}|{ordinal}|object"
            )
            relation_evidence, relation_binding = translation_anchor(
                task, str(spec["relation_phrase"]), spec.get("relation_occurrence")
            )
            object_phrase = str(
                spec.get("target_phrase")
                or spec.get("outcome_phrase")
                or spec.get("object_phrase")
                or spec["relation_phrase"]
            )
            object_occurrence = spec.get(
                "target_occurrence",
                spec.get("outcome_occurrence", spec.get("object_occurrence")),
            )
            object_evidence, object_binding = role_anchor(
                task,
                BindingRole.TARGET
                if kind is SemanticObjectKind.CANONICAL_ENTITY_REF
                else BindingRole.OUTCOME
                if predicate is SemanticPredicate.REQUESTS
                else BindingRole.RELATION,
                object_phrase,
                object_occurrence,
                str(spec["canonical_entity_id"])
                if kind is SemanticObjectKind.CANONICAL_ENTITY_REF
                else None,
            )
            # A non-canonical object's evidence may reuse the declared object phrase, but
            # its execution binding only needs the relation anchor (or OUTCOME for REQUESTS).
            if (
                kind is not SemanticObjectKind.CANONICAL_ENTITY_REF
                and predicate is not SemanticPredicate.REQUESTS
            ):
                binding_anchors = [relation_binding]
            else:
                binding_anchors = [relation_binding, object_binding]
            object_data: dict[str, Any] = {
                "candidate_id": candidate_id,
                "object_kind": kind.value,
                "normalized_head": str(spec["normalized_head"])
                if spec.get("normalized_head") is not None
                else None,
                "display_label": str(
                    spec.get("display_label", spec.get("normalized_head", kind.value))
                ),
                "qualifiers": [str(item) for item in spec.get("qualifiers", [])],
                "canonical_entity_id": str(spec["canonical_entity_id"])
                if kind is SemanticObjectKind.CANONICAL_ENTITY_REF
                else None,
                "beneficiary_entity_id": spec.get("beneficiary_entity_id"),
                "target_entity_id": spec.get("target_entity_id"),
                "event": event_from_spec(dict(spec["event"])) if spec.get("event") else None,
                "source_passage_id": task.passage_id,
                "evidence": [SemanticEvidenceAnchor.model_validate(object_evidence)],
                "extraction_model": MODEL,
                "prompt_version": PROMPT_VERSION,
                "normalization_status": status_for(kind).value,
            }
            object_candidate = SemanticObjectCandidate.model_validate(object_data)
            explicitness = Explicitness(str(spec.get("explicitness", "EXPLICIT")))
            assertion = StructuredSemanticAssertion(
                assertion_id=assertion_id,
                source_run_id=RUN_ID,
                subject_id=task.passage_id,
                predicate=predicate,
                object=object_candidate,
                evidence=[SemanticEvidenceAnchor.model_validate(relation_evidence)],
                explicitness=explicitness,
                inference_step=spec.get("inference_step"),
            )
            assertions.append(assertion)
            bindings.append(
                {
                    "assertion_id": assertion_id,
                    "anchors": [item.model_dump(mode="json") for item in binding_anchors],
                }
            )

    payload = SemanticExtractionV3(
        mantra_id=task.citation,
        assertions=assertions,
        ontology_gaps=[],
        no_claim_reasons=[str(item) for item in decision.get("no_claim_reasons", [])]
        if decision["decision"] == "NO_CLAIM"
        else [],
    )
    return {
        "semantic_output": payload.model_dump(mode="json"),
        "assertion_bindings": bindings,
        "decision_provenance": {
            "decision_source": "MODEL_AUTHORED_PACKET_LOCAL_RECORD",
            "passage_key": task.passage_id,
            "run_id": RUN_ID,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--store", type=Path, required=True)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--task-id", required=True)
    args = parser.parse_args()
    decisions: dict[str, dict[str, Any]] = {}
    for line in args.decisions.read_text(encoding="utf-8").splitlines():
        if line.strip():
            item = json.loads(line)
            key = str(item["passage_key"])
            if key in decisions:
                raise ValueError(f"duplicate decision for {key}")
            decisions[key] = item
    task = PreparedTask.model_validate_json(
        task_path(args.store, args.task_id).read_text(encoding="utf-8")
    )
    if task.passage_id not in decisions:
        raise ValueError(f"no model-authored decision for {task.passage_id}")
    draft = build_draft(task, decisions[task.passage_id])
    output = args.output or args.out_dir / f"{task.task_id.replace(':', '_')}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(draft, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    if output.exists() and output.read_bytes() != data:
        raise ValueError(f"refusing to overwrite draft: {output}")
    if not output.exists():
        output.write_bytes(data)
    print(
        json.dumps({"task_id": task.task_id, "passage_id": task.passage_id, "draft": str(output)})
    )


if __name__ == "__main__":
    main()
