"""Execute the v3.1 508 custody from explicit model-authored decision records.

This runner is orchestration only.  It does not choose predicates, objects, or evidence;
those must already exist in ``model_authored_decisions.jsonl``.  Mechanical draft, receipt,
and repository import commands are run separately for every prepared task.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, cast

from vedagraph.semantic.codex_direct import task_id_for

RUN_ID = "vedagraph-rigveda-semantic-luna-v3.1-508"
ROOT = Path("data/semantic") / RUN_ID
STORE = ROOT / "store"
DECISIONS = ROOT / "model_authored_decisions.jsonl"
DRAFTS = ROOT / "drafts"
RESPONSES = ROOT / "responses"
EVENTS = ROOT / "execution_events.jsonl"
STATE = ROOT / "execution_state.json"


def load_decisions() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for line in DECISIONS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            item = json.loads(line)
            key = str(item["passage_key"])
            if key in result:
                raise RuntimeError(f"duplicate model-authored decision: {key}")
            result[key] = cast(dict[str, Any], item)
    return result


def load_manifest() -> dict[str, Any]:
    return cast(
        dict[str, Any],
        json.loads((ROOT / "batch_manifest.json").read_text(encoding="utf-8")),
    )


def append_event(event: dict[str, Any]) -> None:
    EVENTS.parent.mkdir(parents=True, exist_ok=True)
    with EVENTS.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def run_command(command: list[str]) -> None:
    completed = subprocess.run(command, check=False)
    if completed.returncode:
        raise RuntimeError(f"command failed ({completed.returncode}): {' '.join(command)}")


def task_paths(task_id: str) -> tuple[Path, Path, Path]:
    task_dir = STORE / "tasks" / task_id.replace(":", "_")
    task_path = task_dir / "task.json"
    draft_path = DRAFTS / f"{task_id.replace(':', '_')}.json"
    return task_path, task_dir, draft_path


def next_attempt(task_dir: Path, task_id: str) -> str:
    attempts = [path.name for path in (task_dir / "attempts").glob("attempt_*")]
    response_prefix = task_id.replace(":", "_") + "_"
    attempts.extend(
        path.stem.removeprefix(response_prefix)
        for path in RESPONSES.glob(f"{response_prefix}attempt_*.json")
    )
    numbers = [
        int(name.split("_")[1])
        for name in attempts
        if len(name.split("_")) > 1 and name.split("_")[1].isdigit()
    ]
    return f"attempt_{max(numbers, default=0) + 1:03d}"


def process_batch(batch: dict[str, Any], decisions: dict[str, dict[str, Any]]) -> dict[str, Any]:
    started = time.perf_counter()
    attempted = imported = refused = retries = 0
    missing = [key for key in batch["passage_keys"] if key not in decisions]
    if missing:
        raise RuntimeError(
            f"missing model-authored decisions for batch {batch['batch']}: {missing}"
        )
    for passage_key in batch["passage_keys"]:
        task_id = task_id_for(RUN_ID, passage_key)
        task_path, task_dir, draft_path = task_paths(task_id)
        if not task_path.exists():
            raise RuntimeError(f"prepared task missing: {task_id}")
        validated = list((task_dir / "attempts").glob("*/validated.json"))
        if validated:
            append_event(
                {
                    "batch": batch["batch"],
                    "task_id": task_id,
                    "passage_key": passage_key,
                    "state": "SKIPPED_COMPLETED",
                }
            )
            continue
        attempted += 1
        attempt_id = next_attempt(task_dir, task_id)
        if attempt_id != "attempt_001":
            retries += 1
        draft_path = DRAFTS / f"{task_id.replace(':', '_')}_{attempt_id}.json"
        run_command(
            [
                sys.executable,
                "scripts/materialize_real_luna_v3_1_508_draft.py",
                "--store",
                str(STORE),
                "--decisions",
                str(DECISIONS),
                "--out-dir",
                str(DRAFTS),
                "--output",
                str(draft_path),
                "--task-id",
                task_id,
            ]
        )
        response_path = RESPONSES / f"{task_id.replace(':', '_')}_{attempt_id}.json"
        run_command(
            [
                sys.executable,
                "scripts/persist_codex_direct_response.py",
                "--task",
                str(task_path),
                "--draft",
                str(draft_path),
                "--out",
                str(response_path),
                "--attempt-id",
                attempt_id,
                "--reported-model",
                "gpt-5.6-luna",
            ]
        )
        try:
            run_command(
                [
                    "vedagraph",
                    "semantic",
                    "execute",
                    "import-response",
                    str(response_path),
                    "--store-dir",
                    str(STORE),
                ]
            )
        except RuntimeError:
            refused += 1
            append_event(
                {
                    "batch": batch["batch"],
                    "task_id": task_id,
                    "passage_key": passage_key,
                    "state": "FAILED_IMPORT",
                    "attempt_id": attempt_id,
                }
            )
            raise
        imported += 1
        append_event(
            {
                "batch": batch["batch"],
                "task_id": task_id,
                "passage_key": passage_key,
                "state": "VALIDATED",
                "attempt_id": attempt_id,
            }
        )
    result = {
        "batch": batch["batch"],
        "batch_size": batch["batch_size"],
        "tasks_attempted": attempted,
        "imported": imported,
        "refused": refused,
        "retries": retries,
        "status": "VALIDATED",
        "wall_seconds": round(time.perf_counter() - started, 6),
    }
    state = []
    if STATE.exists():
        state = json.loads(STATE.read_text(encoding="utf-8"))
    state = [item for item in state if item.get("batch") != batch["batch"]]
    state.append(result)
    STATE.write_text(
        json.dumps(sorted(state, key=lambda item: item["batch"]), indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int)
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    if bool(args.batch) == bool(args.all):
        raise SystemExit("choose exactly one of --batch N or --all")
    manifest = load_manifest()
    decisions = load_decisions()
    batches = manifest["batches"]
    if args.batch is not None:
        wanted = [item for item in batches if item["batch"] == args.batch]
        if not wanted:
            raise SystemExit(f"unknown batch: {args.batch}")
    else:
        wanted = batches
    for batch in wanted:
        process_batch(batch, decisions)


if __name__ == "__main__":
    main()
