"""Mechanically import one model-authored V3.2 smoke response.

The intermediate JSON supplied to this command is the semantic authorship boundary. This
module only resolves quoted spans, creates contract IDs, records the truthful CODEX_DIRECT
receipt, and lets the existing importer validate the result. It never invents assertions or
repairs failed semantics.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from run_semantic_v3_2_stability_60 import (  # noqa: E402
    CANONICAL_TARGET_PREDICATES,
    _find_span,
)

from vedagraph.semantic.codex_direct import (  # noqa: E402
    ExecutionStore,
    ModelAuthoredResponse,
    canonical_sha256,
    load_run_contract,
)

INPUT_ROOT = ROOT / "data/semantic/vedagraph-rigveda-semantic-user-selected-luna-v3.2-smoke-8-input"
PROMPT = ROOT / "prompts/semantic_extraction_v3.2.md"
SCHEMA = ROOT / "schemas/semantic_extraction_v3.schema.json"
ONTOLOGY = ROOT / "src/vedagraph/semantic/ontology.py"
MODEL = "gpt-5.6-luna"
REASONING = "high"
RUNTIME = "CODEX_DIRECT"


def contract_for(run_id: str):
    return load_run_contract(
        run_id=run_id,
        prompt_path=PROMPT,
        schema_path=SCHEMA,
        ontology_path=ONTOLOGY,
        model_requested=MODEL,
        reasoning_requested=REASONING,
        execution_version="rigveda-semantic-execution-v3.2",
    )


def anchor(*, passage_key: str, translation_id: str, start: int, end: int) -> dict[str, object]:
    return {
        "source_passage_id": passage_key,
        "passage_ids": [passage_key],
        "token_ids": [],
        "other_evidence_ids": [],
        "translation_record_id": translation_id,
        "translation_span": {"start": start, "end": end},
    }


def assemble(
    intermediate: dict[str, object], task, contract
) -> tuple[dict[str, object], list[dict[str, object]]]:
    packet = task.evidence_packet
    translation = packet.translation
    text = translation.text if translation else ""
    translation_id = translation.translation_id if translation else ""
    mention_keys = {mention.entity_key for mention in packet.mentions}
    if intermediate.get("no_claim"):
        reasons = intermediate.get("no_claim_reasons") or []
        if not reasons:
            raise ValueError("no_claim requires at least one reason")
        return (
            {
                "mantra_id": packet.citation,
                "assertions": [],
                "no_claim_reasons": reasons,
                "ontology_gaps": [],
                "object_schema_version": "rigveda-semantic-object-v1",
                # The top-level payload schema remains the frozen V3 schema; the
                # per-object prompt_version records the V3.2 policy that authored it.
                "prompt_version": "rigveda-semantic-extraction-v3",
            },
            [],
        )

    assertions: list[dict[str, object]] = []
    bindings: list[dict[str, object]] = []
    raw_assertions = intermediate.get("assertions", [])
    if not isinstance(raw_assertions, list):
        raise ValueError("assertions must be a list")
    for ordinal, raw in enumerate(raw_assertions, start=1):
        if not isinstance(raw, dict):
            raise ValueError("each assertion must be an object")
        predicate = str(raw["predicate"])
        obj = raw["object"]
        if not isinstance(obj, dict):
            raise ValueError("assertion object must be an object")
        object_kind = str(obj["object_kind"])
        relation_quote = str(raw["relation_quote"])
        object_quote = str(obj["object_quote"])
        relation_start, relation_end = _find_span(
            text, relation_quote, label=f"assertion {ordinal} relation"
        )
        object_start, object_end = _find_span(
            text, object_quote, label=f"assertion {ordinal} object"
        )
        candidate_id = f"VG:SEMOBJ:{ordinal:020X}"
        assertion_id = f"{contract.run_id[-1].upper()}32A:{candidate_id}"
        canonical_entity_id = obj.get("canonical_entity_id")
        if object_kind == "CANONICAL_ENTITY_REF":
            if not canonical_entity_id or canonical_entity_id not in mention_keys:
                raise ValueError(f"assertion {ordinal}: canonical target is not a supplied mention")

        object_payload = {
            "candidate_id": candidate_id,
            "object_kind": object_kind,
            "display_label": obj["display_label"],
            "normalized_head": obj.get("normalized_head"),
            "canonical_entity_id": canonical_entity_id,
            "target_entity_id": obj.get("target_entity_id"),
            "beneficiary_entity_id": obj.get("beneficiary_entity_id"),
            "event": obj.get("event"),
            "ontology_gap_code": obj.get("ontology_gap_code"),
            "qualifiers": obj.get("qualifiers", []),
            "source_passage_id": packet.passage_key,
            "evidence": [
                anchor(
                    passage_key=packet.passage_key,
                    translation_id=translation_id,
                    start=object_start,
                    end=object_end,
                )
            ],
            "extraction_model": contract.model_requested,
            "prompt_version": contract.prompt_version,
            "normalization_status": "CANONICAL_REF"
            if object_kind == "CANONICAL_ENTITY_REF"
            else "ONTOLOGY_GAP"
            if object_kind == "ONTOLOGY_GAP_REF"
            else "NORMALIZED_CANDIDATE",
            "legacy_object_id": None,
            "schema_version": "rigveda-semantic-object-v1",
        }
        assertions.append(
            {
                "assertion_id": assertion_id,
                "source_run_id": contract.run_id,
                "subject_id": packet.passage_key,
                "predicate": predicate,
                "object": object_payload,
                "evidence": [
                    anchor(
                        passage_key=packet.passage_key,
                        translation_id=translation_id,
                        start=relation_start,
                        end=relation_end,
                    )
                ],
                "explicitness": raw["explicitness"],
                "inference_step": raw.get("inference_step"),
                "legacy_assertion_id": None,
                "schema_version": "rigveda-semantic-object-v1",
            }
        )
        assertion_anchors: list[dict[str, object]] = [
            {
                "role": "RELATION",
                "translation_record_id": translation_id,
                "start": relation_start,
                "end": relation_end,
                "text": relation_quote,
                "entity_id": None,
            }
        ]
        if object_kind == "CANONICAL_ENTITY_REF" and predicate in CANONICAL_TARGET_PREDICATES:
            assertion_anchors.append(
                {
                    "role": "TARGET",
                    "translation_record_id": translation_id,
                    "start": object_start,
                    "end": object_end,
                    "text": object_quote,
                    "entity_id": canonical_entity_id,
                }
            )
        if predicate == "REQUESTS":
            assertion_anchors.append(
                {
                    "role": "OUTCOME",
                    "translation_record_id": translation_id,
                    "start": object_start,
                    "end": object_end,
                    "text": object_quote,
                    "entity_id": None,
                }
            )
        bindings.append({"assertion_id": assertion_id, "anchors": assertion_anchors})

    return (
        {
            "mantra_id": packet.citation,
            "assertions": assertions,
            "no_claim_reasons": [],
            "ontology_gaps": [],
            "object_schema_version": "rigveda-semantic-object-v1",
            # The top-level payload schema remains the frozen V3 schema; the per-object
            # prompt_version records the V3.2 policy that authored it.
            "prompt_version": "rigveda-semantic-extraction-v3",
        },
        bindings,
    )


def main() -> None:
    _, _, run_id, passage_id, intermediate_path, *rest = sys.argv
    attempt = int(rest[0]) if rest else 1
    contract = contract_for(run_id)
    store = ExecutionStore(INPUT_ROOT / run_id / "store")
    from vedagraph.semantic.codex_direct import task_id_for

    task = store.load_task(task_id_for(run_id, passage_id))
    intermediate = json.loads(Path(intermediate_path).read_text(encoding="utf-8"))
    semantic_output, bindings = assemble(intermediate, task, contract)
    response_body = {"semantic_output": semantic_output, "assertion_bindings": bindings}
    response_sha256 = canonical_sha256(response_body)
    receipt = {
        "execution_contract_version": "codex-direct-semantic-v1",
        "execution_version": task.execution_version,
        "run_id": run_id,
        "task_id": task.task_id,
        "passage_id": passage_id,
        "requested_model": MODEL,
        "reported_model": MODEL,
        "runtime": RUNTIME,
        "reasoning": REASONING,
        "provider_build_metadata": "UNAVAILABLE",
        "task_sha256": task.task_sha256,
        "prompt_sha256": task.prompt_sha256,
        "schema_sha256": task.schema_sha256,
        "evidence_packet_sha256": task.evidence_packet_sha256,
        "response_sha256": response_sha256,
        "model_response_authored": True,
        "attempt_id": f"attempt_{attempt:03d}",
        "authored_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    response = ModelAuthoredResponse.model_validate({"receipt": receipt, **response_body})
    response_dir = INPUT_ROOT / run_id / "responses"
    response_dir.mkdir(parents=True, exist_ok=True)
    response_path = response_dir / f"{task.task_id.replace(':', '_')}_{receipt['attempt_id']}.json"
    if response_path.exists():
        raise RuntimeError(f"refusing to overwrite existing response: {response_path}")
    response_path.write_text(
        json.dumps(response.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, indent=2)
        + "\n",
        encoding="utf-8",
    )
    validated = store.import_response(response_path, contract)
    print(
        json.dumps(
            {
                "run_id": run_id,
                "passage_id": passage_id,
                "task_id": task.task_id,
                "attempt_id": receipt["attempt_id"],
                "assertions": len(validated.payload.assertions),
                "no_claim": bool(validated.payload.no_claim_reasons),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    if len(sys.argv) < 5:
        raise SystemExit("usage: import <run_id> <passage_id> <intermediate.json> [attempt]")
    main()
