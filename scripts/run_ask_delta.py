"""Re-ask named questions from the frozen set after a fix, as a separate delta run.

The 60-question benchmark is graded and frozen. When a fix closes a defect that two of
those answers exposed, the honest way to show it is not to re-run all sixty -- that costs
a day of free-tier quota and re-rolls fifty-eight answers nobody has a question about --
and *certainly* not to edit the frozen artifact. It is to re-ask exactly the questions the
fix was about, under a new run identity, and to keep both artifacts.

Which is why this writes a file named ``...-delta.jsonl`` and never touches the original.
The questions come from the same frozen ``ask_benchmark_v1.jsonl`` and are selected by id,
so the wording cannot drift: a re-asked question that was reworded measures the rewording.

The composite result is then 58 verdicts from the original run plus the delta's, and every
row in the report says which. A delta presented as a fresh sixty would claim that fifty-
eight answers were generated under a commit that never produced them.

Usage::

    python scripts/run_ask_delta.py Q34 Q60
    python scripts/run_ask_delta.py Q34 Q60 --label post_fix_v1
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

# The benchmark runner owns the run identity, the usage wrapper and the record shape, and
# a delta must reuse all three or it is not comparable with the run it extends. ``scripts``
# is not an installable package, so it is reached by path rather than by import name.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_ask_benchmark import (
    CHECKPOINT_DIR,
    UsageRecordingProvider,
    _record,
    build_identity,
    load_questions,
    safe_filename,
)

from vedagraph.api.ask.models import AskRequest
from vedagraph.api.ask.service import AskService
from vedagraph.api.config import get_api_settings
from vedagraph.api.repositories.neo4j_repository import Neo4jRepository
from vedagraph.llm import get_llm_provider
from vedagraph.llm.errors import LLMError


def delta_path(run_id: str, label: str) -> Path:
    return CHECKPOINT_DIR / f"{safe_filename(run_id)}-{label}.jsonl"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ids", nargs="+", help="Question ids from the frozen set.")
    parser.add_argument("--label", default="delta", help="Artifact suffix.")
    parser.add_argument("--pace", type=float, default=3.0)
    args = parser.parse_args()

    logging.disable(logging.WARNING)
    cases, question_set_hash = load_questions()
    by_id = {case["id"]: case for case in cases}

    missing = [qid for qid in args.ids if qid not in by_id]
    if missing:
        raise SystemExit(f"not in the frozen question set: {', '.join(missing)}")
    selected = [by_id[qid] for qid in args.ids]

    provider = UsageRecordingProvider(get_llm_provider())
    identity = build_identity(provider, question_set_hash)
    out = delta_path(identity.run_id, args.label)

    print(f"delta run   {identity.run_id}")
    print(f"provider    {identity.provider}  model {identity.model}")
    print(f"commit      {identity.code_commit}")
    print(f"questions   {', '.join(args.ids)}")
    print(f"artifact    {out}\n")

    repo = Neo4jRepository(get_api_settings())
    service = AskService(repo, provider)
    records: list[dict[str, Any]] = []
    try:
        for index, case in enumerate(selected):
            if index:
                time.sleep(args.pace)
            provider.clear_fault()
            started = time.monotonic()
            try:
                response = service.ask(AskRequest(question=case["question"], **case["context"]))
            except LLMError as exc:
                detail = getattr(exc, "detail", str(exc)) or type(exc).__name__
                print(f"[{case['id']}] STOPPED {type(exc).__name__}: {detail}")
                raise SystemExit(1) from exc

            record = _record(
                case, response, identity, provider, (time.monotonic() - started) * 1000
            )
            records.append(record)
            print(
                f"[{case['id']}] {record['status']:22} "
                f"cites {record['citation_count']:>2}  "
                f"evidence {record['evidence_count']:>2}  "
                f"out {record['output_tokens']} tok"
            )
    finally:
        repo.close()

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"\nwrote {len(records)} row(s) to {out}")


if __name__ == "__main__":
    main()
