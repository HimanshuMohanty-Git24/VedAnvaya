"""Persist a model-authored semantic draft with its mechanical execution receipt.

The draft supplies semantic_output and assertion_bindings. This helper only validates their
shape, computes the payload commitment, fills receipt fields from the prepared task, and
persists the resulting response for the repository import command. It never creates or
changes semantic assertions.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from vedagraph.models.normalization import SemanticExtractionV3
from vedagraph.semantic.codex_direct import (
    AssertionBinding,
    ModelAuthoredResponse,
    ModelExecutionReceipt,
    PreparedTask,
    response_payload_sha256,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--draft", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--attempt-id", default="attempt_001")
    parser.add_argument("--reported-model", default="gpt-5.6-luna")
    args = parser.parse_args()

    task = PreparedTask.model_validate_json(args.task.read_text(encoding="utf-8"))
    draft = json.loads(args.draft.read_text(encoding="utf-8"))
    payload = SemanticExtractionV3.model_validate(draft["semantic_output"])
    bindings = [
        AssertionBinding.model_validate(item) for item in draft.get("assertion_bindings", [])
    ]
    shell = ModelAuthoredResponse.model_construct(
        receipt=None, semantic_output=payload, assertion_bindings=bindings
    )
    receipt = ModelExecutionReceipt(
        execution_version=task.execution_version,
        run_id=task.run_id,
        task_id=task.task_id,
        passage_id=task.passage_id,
        requested_model=task.model_requested,
        reported_model=args.reported_model,
        reasoning=task.reasoning_requested,
        task_sha256=task.task_sha256,
        prompt_sha256=task.prompt_sha256,
        schema_sha256=task.schema_sha256,
        evidence_packet_sha256=task.evidence_packet_sha256,
        response_sha256=response_payload_sha256(shell),
        attempt_id=args.attempt_id,
        authored_at=datetime.now(UTC),
    )
    response = ModelAuthoredResponse(
        receipt=receipt,
        semantic_output=payload,
        assertion_bindings=bindings,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(response.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, indent=2)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps({"task_id": task.task_id, "attempt_id": args.attempt_id, "out": str(args.out)})
    )


if __name__ == "__main__":
    main()
