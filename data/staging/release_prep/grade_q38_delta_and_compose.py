"""Grade the Q38 remediation delta, then compose it with the frozen formal 60.

WHY THIS IS NOT ``scripts/grade_ask_delta.py`` RUN DIRECTLY
===========================================================

That script is the canonical delta mechanism and every measurement here is imported from
it -- the packet replay, the citation audit, the quantitative validator and the stricter
figure check are its functions, not reimplementations. What it cannot do is name the right
baseline: its ``FROZEN_RUN`` is the Product V1 run ``...-bfdba0b998f1f6cd``, and the run
under certification is the later formal 60, ``...-dddb14430cac6c58``. Composing Q38
against the older baseline would produce a number describing neither run.

So this follows the precedent of ``audit_ask_formal_60.py`` next door, which widened the
same machinery from three delta questions to all sixty: same code, different baseline,
and the baseline is named in the output rather than assumed.

WHAT IS AND IS NOT RE-GRADED
============================

Fifty-nine verdicts are copied unchanged from the frozen grading. One question was
re-asked and is re-measured. Nothing else is touched, and the frozen JSONL is not edited:
a delta presented as a fresh sixty would claim fifty-nine answers were generated under a
commit that never produced them.

The two runs differ in ``config_hash`` as well as ``code_commit``, because the fix added a
binding rule to the system prompt and the prompt is inside the config hash. That is
recorded rather than smoothed over -- it is the honest consequence of fixing generation
rather than only detection.

THE VERDICT IS ADJUDICATED, NOT ASSERTED
========================================

``--measure`` prints the mechanical half and stops. Only after a human has read the answer
is ``--verdict`` supplied, and even then the composition refuses to run if any hard gate
fails: an invented citation, a citation outside the replayed packet, Sanskrit absent from
the packet, a quantitative finding, or a truncated generation. A verdict cannot be typed
past a failing measurement.

Usage::

    python data/staging/release_prep/grade_q38_delta_and_compose.py <delta.jsonl> --measure
    python data/staging/release_prep/grade_q38_delta_and_compose.py <delta.jsonl> \
        --verdict SUPPORTED_CORRECT --reason-file reason.txt
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

FROZEN_RUN = ROOT / (
    "data/gold/ask_benchmark_runs/"
    "openrouter-nvidia_nemotron-3-ultra-550b-a55b_free-dddb14430cac6c58.jsonl"
)
FROZEN_GRADING = ROOT / "data/staging/release_prep/ask_formal_60_final.json"
OUT = Path(__file__).resolve().parent / "ask_formal_60_post_remediation.json"

#: The sha256 the certification receipt recorded for the frozen run. Checked, not trusted:
#: a composite that silently read an edited baseline would be the one failure this whole
#: procedure exists to make impossible.
FROZEN_SHA = "f21c917fac78ad163d4a3bc6c357418e990016d1fe5937a48933847adb50ede8"

REMEDIATED = "Q38"
ORIGINAL_FROZEN_RUN = "ORIGINAL_FROZEN_RUN"
POST_FIX_DELTA_RUN = "POST_FIX_DELTA_RUN"

ACCEPTABLE = {"SUPPORTED_CORRECT", "PARTIAL_CORRECT", "INSUFFICIENT_EVIDENCE_CORRECTLY_REFUSED"}

_spec = importlib.util.spec_from_file_location("gad", ROOT / "scripts" / "grade_ask_delta.py")
assert _spec and _spec.loader
gad = importlib.util.module_from_spec(_spec)
sys.modules["gad"] = gad
_spec.loader.exec_module(gad)

from vedagraph.api.ask.citation import audit as citation_audit  # noqa: E402
from vedagraph.api.ask.citation import extract_cited_ids  # noqa: E402
from vedagraph.api.ask.quantitative import validate  # noqa: E402
from vedagraph.api.config import get_api_settings  # noqa: E402
from vedagraph.api.repositories.neo4j_repository import Neo4jRepository  # noqa: E402


def _rows(path: Path) -> list[dict[str, Any]]:
    return [json.loads(x) for x in path.read_text("utf-8").splitlines() if x.strip()]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def measure(delta_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Replay the re-asked question's packet and re-audit the new answer."""
    delta_rows = {r["id"]: r for r in _rows(delta_path)}
    if REMEDIATED not in delta_rows:
        raise SystemExit(f"{delta_path} holds no {REMEDIATED} row")
    if len(delta_rows) != 1:
        raise SystemExit(
            f"{delta_path} holds {len(delta_rows)} questions; the remediation is "
            f"{REMEDIATED} alone and a wider delta would re-roll answers nobody asked about"
        )
    row = delta_rows[REMEDIATED]
    if row.get("degraded"):
        raise SystemExit(
            f"{REMEDIATED} was answered by a degraded provider fallback, not by the "
            "product. That is a provider fault, not a measurement -- delete the artifact "
            "and re-ask when the allowance is available."
        )

    repo = Neo4jRepository(get_api_settings())
    try:
        packet = gad._replay(repo, row["question"], row.get("context") or {})
        audited = citation_audit(row["answer"], packet)
        quantitative = validate(row["answer"], packet)
        figures = gad._figure_check(row["answer"], packet)
    finally:
        repo.close()

    packet_ids = set(packet.by_id())
    cited = extract_cited_ids(row["answer"])
    checks: dict[str, Any] = {
        "packet_items_replayed": len(packet.items),
        "packet_items_recorded": row["evidence_count"],
        "packet_replay_matches": len(packet.items) == row["evidence_count"],
        "citations_in_answer": cited,
        "citations_not_in_packet": [c for c in cited if c not in packet_ids],
        "invented_citations_surviving": row["invented_citations_surviving"],
        "invalid_citations_caught": row["invalid_citations_caught"],
        "sanskrit_absent_from_packet": audited.unverified_quotes,
        "sanskrit_in_packet_but_uncited": audited.uncited_quotes,
        "quantitative_findings": [
            {"rule": f.rule.value, "claim": f.claim, "detail": f.detail}
            for f in quantitative.findings
        ],
        "quantitative_repair_attempted": row.get("quantitative_flagged"),
        "generation_truncated": row["generation_truncated"],
        "runtime_status": row["status"],
        "runtime_support_level": row["support_level"],
        "caveat_sources": row.get("caveat_sources"),
        **figures,
    }
    return row, checks


#: The gates a verdict may not be typed past. Each is a measurement, not a judgement.
def hard_gate_failures(checks: dict[str, Any]) -> list[str]:
    failures = []
    if not checks["packet_replay_matches"]:
        failures.append("the packet did not replay to the recorded item count")
    if checks["citations_not_in_packet"]:
        failures.append(f"citations outside the packet: {checks['citations_not_in_packet']}")
    if checks["invented_citations_surviving"]:
        failures.append("an invented citation survived")
    if checks["sanskrit_absent_from_packet"]:
        failures.append(f"Sanskrit absent from the packet: {checks['sanskrit_absent_from_packet']}")
    if checks["quantitative_findings"]:
        failures.append(
            "the quantitative validator still reports: "
            + "; ".join(f["rule"] for f in checks["quantitative_findings"])
        )
    if checks["generation_truncated"]:
        failures.append("the generation was truncated")
    if not checks["citations_in_answer"]:
        failures.append("the answer cites nothing")
    return failures


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("delta", type=lambda x: Path(x).resolve())
    parser.add_argument("--measure", action="store_true", help="Print and stop; compose nothing.")
    parser.add_argument("--verdict", help="The adjudicated verdict, after reading the answer.")
    parser.add_argument("--reason-file", type=Path, help="The reasoning behind the verdict.")
    args = parser.parse_args()

    frozen_sha = _sha(FROZEN_RUN)
    print(f"frozen run sha256      {frozen_sha}")
    print(f"matches the receipt    {frozen_sha == FROZEN_SHA}")
    if frozen_sha != FROZEN_SHA:
        raise SystemExit("the frozen run has changed since it was graded; refusing to compose")
    print(f"delta artifact sha256  {_sha(args.delta)}\n")

    row, checks = measure(args.delta)
    print(f"{REMEDIATED}  {row['question']}")
    print(f"  run_id       {row['run_id']}")
    print(f"  code_commit  {row['code_commit']}   config_hash {row['config_hash']}\n")
    for key, value in checks.items():
        print(f"  {key:38} {value}")
    print()
    failures = hard_gate_failures(checks)
    for failure in failures:
        print(f"  HARD GATE FAILED: {failure}")
    print(f"\n  hard gates: {'PASS' if not failures else 'FAIL'}")
    print("\n--- ANSWER AS RETURNED ---")
    print(row["answer"])
    print("--- END ---\n")

    if args.measure or not args.verdict:
        print("measurement only; no composite written")
        return
    if failures:
        raise SystemExit("refusing to compose a verdict over a failing hard gate")
    if args.verdict not in ACCEPTABLE | {"MISLEADING", "HALLUCINATED"}:
        raise SystemExit(f"unknown verdict {args.verdict!r}")
    reason = args.reason_file.read_text("utf-8").strip() if args.reason_file else ""
    if not reason:
        raise SystemExit("a verdict without its reasoning is a label, not a grade")

    frozen_grading = json.loads(FROZEN_GRADING.read_text("utf-8"))
    frozen_run = {r["id"]: r for r in _rows(FROZEN_RUN)}
    per_question = frozen_grading["grading"]["per_question"]
    if len(per_question) != 60:
        raise SystemExit(f"frozen grading holds {len(per_question)} rows, not 60")

    composite: list[dict[str, Any]] = []
    for entry in per_question:
        qid = entry["question_id"]
        if qid == REMEDIATED:
            continue
        composite.append(
            {
                "question_id": qid,
                "question": entry["question"],
                "provenance": ORIGINAL_FROZEN_RUN,
                "code_commit": frozen_run[qid]["code_commit"],
                "config_hash": frozen_run[qid]["config_hash"],
                "final_verdict": entry["final_verdict"],
                "runtime_status": entry["runtime_status"],
            }
        )
    original = next(e for e in per_question if e["question_id"] == REMEDIATED)
    composite.append(
        {
            "question_id": REMEDIATED,
            "question": row["question"],
            "provenance": POST_FIX_DELTA_RUN,
            "code_commit": row["code_commit"],
            "config_hash": row["config_hash"],
            "original_verdict": original["final_verdict"],
            "original_reason": original["reason_for_verdict"],
            "final_verdict": args.verdict,
            "runtime_status": row["status"],
            "reason": reason,
            "checks": checks,
            "answer": row["answer"],
        }
    )

    buckets = dict.fromkeys(
        ["SUPPORTED_CORRECT", "PARTIAL_CORRECT", "CORRECTLY_REFUSED", "MISLEADING", "HALLUCINATED"],
        0,
    )
    for entry in composite:
        key = entry["final_verdict"].replace(
            "INSUFFICIENT_EVIDENCE_CORRECTLY_REFUSED", "CORRECTLY_REFUSED"
        )
        buckets[key] += 1
    acceptable = sum(
        1
        for e in composite
        if e["final_verdict"].replace(
            "INSUFFICIENT_EVIDENCE_CORRECTLY_REFUSED", "CORRECTLY_REFUSED"
        )
        in {"SUPPORTED_CORRECT", "PARTIAL_CORRECT", "CORRECTLY_REFUSED"}
    )

    payload = {
        "artifact": "ASK_FORMAL_60_POST_REMEDIATION",
        "composition": (
            "The original immutable 60-question run, plus one formally graded remediation "
            "delta. 59 verdicts are copied unchanged from the frozen grading; Q38 alone was "
            "re-asked at a new commit and re-measured. The frozen JSONL is unedited and its "
            "sha256 is checked above."
        ),
        "baseline_run": {
            "run_id": frozen_grading["run_id"],
            "artifact": FROZEN_RUN.relative_to(ROOT).as_posix(),
            "sha256": frozen_sha,
            "code_commit": frozen_grading["code_commit"],
            "config_hash": frozen_grading["config_hash"],
            "grading_receipt": FROZEN_GRADING.relative_to(ROOT).as_posix(),
        },
        "delta_run": {
            "run_id": row["run_id"],
            "artifact": args.delta.relative_to(ROOT).as_posix(),
            "sha256": _sha(args.delta),
            "code_commit": row["code_commit"],
            "config_hash": row["config_hash"],
            "question_ids": [REMEDIATED],
            "config_hash_differs_because": (
                "the fix added binding rule 9 to the synthesis system prompt, and the prompt "
                "digest is inside the config hash. Recorded rather than hidden: the "
                "remediation changed generation as well as detection."
            ),
        },
        "measured_by": (
            "scripts/grade_ask_delta.py (_replay, _figure_check) + vedagraph.api.ask citation "
            "audit and quantitative validator; no new rubric"
        ),
        "graded": len(composite),
        "counts": buckets,
        "effective_acceptable": f"{acceptable}/{len(composite)}",
        "MISLEADING": buckets["MISLEADING"],
        "HALLUCINATED": buckets["HALLUCINATED"],
        "provenance_counts": {
            ORIGINAL_FROZEN_RUN: sum(
                1 for e in composite if e["provenance"] == ORIGINAL_FROZEN_RUN
            ),
            POST_FIX_DELTA_RUN: sum(1 for e in composite if e["provenance"] == POST_FIX_DELTA_RUN),
        },
        "per_question": sorted(composite, key=lambda e: int(e["question_id"][1:])),
    }
    OUT.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    print("=" * 78)
    print("ASK_FORMAL_60_POST_REMEDIATION")
    print("=" * 78)
    print(f"  graded                     {len(composite)}")
    for name, count in buckets.items():
        print(f"  {name:26} {count}")
    print(f"  effective acceptable       {acceptable}/{len(composite)}")
    print(f"  from {ORIGINAL_FROZEN_RUN:22} {payload['provenance_counts'][ORIGINAL_FROZEN_RUN]}")
    print(f"  from {POST_FIX_DELTA_RUN:22} {payload['provenance_counts'][POST_FIX_DELTA_RUN]}")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
