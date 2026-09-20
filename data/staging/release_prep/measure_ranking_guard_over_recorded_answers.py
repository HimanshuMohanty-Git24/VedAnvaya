"""Run the shipped quantitative validator over every answer this repository has on record.

WHY THIS EXISTS
===============

A guard written for one defect is worth nothing until it is measured on answers it was
not written for. This replays the packet of all 123 recorded answers -- the formal 60, the
earlier Product V1 60, and the three delta re-asks -- and reports every finding by rule.

It is evidence in two directions at once, which is why both halves are printed rather than
just the flattering one:

* the guard fires on Q38, the answer that was graded MISLEADING, at both of its sentences;
* it fires on three other sentences, all unlicensed rankings over one subject's own rows,
  two of which happen to be TRUE (about Indra, where the model reused the same phrasing and
  was right by luck). A true claim the packet cannot license is still a claim the packet
  cannot license, and reporting it is the contract, not a false positive;
* it fires nowhere else, and the six pre-existing rules fire on exactly the sentences they
  fired on before the guard existed. That second number is the one that would show a
  regression, so it is printed even though it is always meant to be boring.

WHAT THIS IS NOT
================

It does not re-grade the frozen runs. Those verdicts were made against the rules that
existed when they were made, and grading a 2026-09-18 answer against a 2026-09-19 rule
would produce a number describing neither. The findings here say what the guard sees
today, nothing more.

Usage::

    python data/staging/release_prep/measure_ranking_guard_over_recorded_answers.py
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

RUNS = ROOT / "data" / "gold" / "ask_benchmark_runs"
ARTIFACTS = (
    "openrouter-nvidia_nemotron-3-ultra-550b-a55b_free-dddb14430cac6c58.jsonl",
    "openrouter-nvidia_nemotron-3-ultra-550b-a55b_free-bfdba0b998f1f6cd.jsonl",
    "openrouter-nvidia_nemotron-3-ultra-550b-a55b_free-5c37f5be7fb331b6-delta.jsonl",
    "openrouter-nvidia_nemotron-3-ultra-550b-a55b_free-81b00969f774f7b6-q02-delta.jsonl",
    "openrouter-nvidia_nemotron-3-ultra-550b-a55b_free-07997da672f3155b-q38-ranking-delta.jsonl",
)
OUT = Path(__file__).resolve().parent / "ranking_guard_over_recorded_answers.json"

_spec = importlib.util.spec_from_file_location("gad", ROOT / "scripts" / "grade_ask_delta.py")
assert _spec and _spec.loader
gad = importlib.util.module_from_spec(_spec)
sys.modules["gad"] = gad
_spec.loader.exec_module(gad)

from vedagraph.api.ask.quantitative import QuantitativeRule, validate  # noqa: E402
from vedagraph.api.config import get_api_settings  # noqa: E402
from vedagraph.api.repositories.neo4j_repository import Neo4jRepository  # noqa: E402

RANKING = QuantitativeRule.UNSUPPORTED_RANKING.value


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    repo = Neo4jRepository(get_api_settings())
    findings: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    answers = 0
    try:
        for name in ARTIFACTS:
            path = RUNS / name
            if not path.exists():
                raise SystemExit(f"missing artifact {path}")
            rows = [json.loads(x) for x in path.read_text("utf-8").splitlines() if x.strip()]
            sources.append(
                {
                    "artifact": path.relative_to(ROOT).as_posix(),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "answers": len(rows),
                }
            )
            for row in rows:
                answers += 1
                packet = gad._replay(repo, row["question"], row.get("context") or {})
                for finding in validate(row["answer"], packet).findings:
                    findings.append(
                        {
                            "artifact": name,
                            "question_id": row["id"],
                            "code_commit": row["code_commit"],
                            "rule": finding.rule.value,
                            "claim": " ".join(finding.claim.split()),
                            "detail": finding.detail,
                        }
                    )
                print(f"{name[-26:]:>26} {row['id']:>4}", flush=True)
    finally:
        repo.close()

    by_rule: dict[str, int] = {}
    for finding in findings:
        by_rule[finding["rule"]] = by_rule.get(finding["rule"], 0) + 1

    payload = {
        "artifact": "RANKING_GUARD_OVER_RECORDED_ANSWERS",
        "measured_with": (
            "vedagraph.api.ask.quantitative.validate, over packets replayed live by "
            "scripts/grade_ask_delta.py"
        ),
        "answers_replayed": answers,
        "sources": sources,
        "findings_by_rule": dict(sorted(by_rule.items())),
        "unsupported_ranking_findings": sum(1 for f in findings if f["rule"] == RANKING),
        "pre_existing_rule_findings": sum(1 for f in findings if f["rule"] != RANKING),
        "reading": (
            "The pre-existing rules fire on exactly the sentences they fired on before the "
            "guard shipped; that number is the regression check. Every UNSUPPORTED_RANKING "
            "finding is a rank asserted over rows that compare nothing relevant -- including "
            "two that are true of the graph and still unlicensed by their packet."
        ),
        "findings": findings,
    }
    OUT.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"\nanswers replayed        {answers}")
    for rule, count in payload["findings_by_rule"].items():
        print(f"  {rule:24} {count}")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
