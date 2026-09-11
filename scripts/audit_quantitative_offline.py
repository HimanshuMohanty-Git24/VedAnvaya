"""Run the quantitative validator over a finished benchmark run. No provider calls.

A new guardrail that has only ever been run against the example that motivated it is not
a guardrail, it is a patch with a test. Before spending live quota this script replays
every question's retrieval deterministically, rebuilds the evidence packet the model
actually saw, and checks the answer it actually wrote -- so the validator's precision is
measured on sixty real answers rather than asserted on one.

The packet is *rebuilt*, not read back: the frozen artifact records the answer, the
citation ids and the evidence count, but not the item bodies, and the figures a claim
must be checked against live in those bodies. Rebuilding is sound because everything
before synthesis is deterministic and provider-independent, and the check is not blind --
the rebuilt evidence count is compared against the count the run recorded, and a
question whose retrieval has drifted is reported rather than silently scored.

Usage::

    python scripts/audit_quantitative_offline.py <run-artifact.jsonl>
    python scripts/audit_quantitative_offline.py <artifact> --json out.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from vedagraph.api.ask import evidence as evidence_stage
from vedagraph.api.ask import planner as planner_stage
from vedagraph.api.ask import resolver as resolver_stage
from vedagraph.api.ask import retriever as retriever_stage
from vedagraph.api.ask.models import AskMode
from vedagraph.api.ask.quantitative import validate
from vedagraph.api.config import get_api_settings
from vedagraph.api.repositories.neo4j_repository import Neo4jRepository


def _rebuild_packet(
    repo: Neo4jRepository, question: str, context: dict[str, Any]
) -> evidence_stage.EvidencePacket:
    """The packet this question produced, rebuilt from the graph.

    Mirrors :meth:`AskService.ask` up to the point the packet closes. Synthesis is never
    reached, so this costs nothing but Cypher.
    """
    plan = planner_stage.plan(
        question, explicit_veda=context.get("veda"), mode=AskMode(context.get("mode", "AUTO"))
    )
    if context.get("passage_context") and not plan.passage_key:
        plan.passage_key = context["passage_context"]
    if context.get("entity_context"):
        plan.entities_mentioned.insert(0, context["entity_context"])
        if "entities" not in plan.retrieval_channels:
            plan.retrieval_channels.insert(0, "entities")
    resolved = resolver_stage.resolve_entities(plan.entities_mentioned, repo)
    return evidence_stage.build_evidence_packet(retriever_stage.retrieve(plan, resolved, repo))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--json", type=Path, default=None, help="Write the full report here.")
    args = parser.parse_args()

    rows = [json.loads(line) for line in args.artifact.read_text("utf-8").splitlines() if line]
    repo = Neo4jRepository(get_api_settings())

    report: list[dict[str, Any]] = []
    flagged: list[str] = []
    drifted: list[str] = []
    with_numbers = 0

    try:
        for row in rows:
            packet = _rebuild_packet(repo, row["question"], row.get("context") or {})
            if len(packet.items) != row["evidence_count"]:
                drifted.append(row["id"])
            audit = validate(row["answer"], packet)
            if audit.quantitative_sentences:
                with_numbers += 1
            if audit.findings:
                flagged.append(row["id"])
            report.append(
                {
                    "question_id": row["id"],
                    "question": row["question"],
                    "evidence_count_recorded": row["evidence_count"],
                    "evidence_count_rebuilt": len(packet.items),
                    "sentences_checked": audit.sentences_checked,
                    "quantitative_sentences": audit.quantitative_sentences,
                    "findings": [
                        {
                            "rule": f.rule.value,
                            "claim": f.claim,
                            "detail": f.detail,
                            "evidence_ids": f.evidence_ids,
                        }
                        for f in audit.findings
                    ],
                }
            )
    finally:
        repo.close()

    print(f"answers inspected                 = {len(rows)}")
    print(f"answers containing quantitative claims = {with_numbers}")
    print(f"flags                             = {sum(len(r['findings']) for r in report)}")
    print(f"question IDs flagged              = {', '.join(flagged) or 'none'}")
    print(f"retrieval drifted since the run   = {', '.join(drifted) or 'none'}")
    print()
    for entry in report:
        for finding in entry["findings"]:
            print(f"[{entry['question_id']}] {finding['rule']}  cites {finding['evidence_ids']}")
            print(f"    detail: {finding['detail']}")
            print(f"    claim : {finding['claim'][:220]}")
            print()

    if args.json:
        args.json.write_text(
            json.dumps(
                {
                    "artifact": str(args.artifact),
                    "answers_inspected": len(rows),
                    "answers_with_quantitative_claims": with_numbers,
                    "flags": sum(len(r["findings"]) for r in report),
                    "question_ids_flagged": flagged,
                    "retrieval_drifted": drifted,
                    "per_question": report,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print(f"report written to {args.json}")


if __name__ == "__main__":
    main()
