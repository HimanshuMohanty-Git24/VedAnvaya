"""Record the ASK_FORMAL_60 outcome in the registry and the dependency ledger.

Both surfaces currently say the Ask regrade is blocked by an external quota. That was
true and is no longer: a fresh commit-keyed run at ``de7195c`` answered all sixty
questions and has been graded. Leaving the old reason in place would be the stalest kind
of claim -- one that names a cause the repository itself disproves -- so it is replaced
rather than merely annotated, with the superseded text kept beside it.

What replaces it is NOT a closure. The entry's own closure test has three clauses. One
and two are demonstrated by the run. The third asks for ``MISLEADING`` at 0 and the
measurement is 1, so the status moves from an EXTERNAL blocker to an IMPLEMENTATION one:
the thing standing in the way is now our own synthesis guardrail, not someone's rate
limit. That reading is deliberately the worse-sounding of the two available -- it moves
``REGISTRY_IMPLEMENTATION_FIXABLE`` from 0 to 1 -- because the alternative is to narrow
clause three until it passes, which is the one move this registry's rules forbid.

Run twice, this script is a no-op: it matches on the status it is replacing.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REGISTRY = ROOT / "data" / "gap_registry.json"
LEDGER = ROOT / "data" / "staging" / "integration" / "dependency_ledger.json"

GAP = "GAP-PRODUCT_SURFACE-004"
OLD = "ASK_FORMAL_REGRADE_BLOCKED_EXTERNAL_QUOTA"
NEW = "STILL_IMPLEMENTATION_FIXABLE"

RUN_ID = "openrouter-nvidia_nemotron-3-ultra-550b-a55b:free-dddb14430cac6c58"
RECEIPT = "data/staging/release_prep/ask_formal_60_final.json"

CLOSURE_BASIS = (
    "The formal re-grade is no longer blocked and is no longer unrun. A commit-keyed run "
    f"at de7195c, run_id {RUN_ID}, answered 60 of 60 -- slot 1 carried Q1-Q49, reported its "
    "allowance exhausted, and slot 2 carried Q50-Q60 without changing run_id, config_hash "
    "or code_commit. It was then graded against this entry's own three-clause closure test, "
    f"with the measurement in {RECEIPT}. "
    "CLAUSE 1 PASSES: Ask reaches Samavedic passages. Q34 'What does SV ARANYA 1.1 contain?' "
    "returns the Sanskrit held at VG:SV:KAU:ARANYA:D01:V01, cited [E1], with no invented id "
    "and no claim of absence; Q45 independently returns four SV ARANYA loci for Varuna. "
    "CLAUSE 2 PASSES: planner.py carries the metals route, and Q13, Q21 and Q47 answer ayas "
    "questions correctly, each reading the known-false lexical zero as a matcher artefact "
    "rather than as textual absence. "
    "CLAUSE 3 FAILS: the clause requires MISLEADING at 0 with Q34 answered. Q34 is answered "
    "and graded PARTIAL_CORRECT. MISLEADING is 1, not 0, at Q38 'Who are the Maruts?' -- an "
    "answer returned as SUPPORTED / STRONG that asserts two corpus-level rankings the live "
    "graph contradicts: the Maruts are called 'the most widely mentioned deity group in the "
    "corpus' when their 560 MENTIONS_DEVATA verses rank third behind apah at 761 and "
    "asvinau at 626, and they are said to 'receive the largest number of hymn-level "
    "dedications' when their 428 HAS_DEVATA edges rank sixth behind Indra 2,869, Agni 1,988, "
    "Soma Pavamana 1,087, the All-Gods 805 and the Asvins 631. "
    "The defect is NOT the one this entry was opened for. Retrieval is sound: all 60 packets "
    "replayed to identical item counts, every citation resolves, no Sanskrit is fabricated "
    "and no figure is invented -- 428 is real and correctly cited. The unsupported tokens are "
    "'most widely' and 'largest'. No check reaches them: the figure check tests integers and "
    "a superlative carries none, and the quantitative validator scopes to the rows a sentence "
    "cites, which hold no comparison. That is the same shape as the Q02 'all ten mandalas' "
    "defect and is not covered by the universal rule shipped for it, so it is implementation "
    "work on the synthesis guardrail, not data work and not an external block. "
    "The status therefore moves from an external-quota execution blocker to "
    f"{NEW}. The smallest remediation is Q38 alone, by the documented "
    "scripts/grade_ask_delta.py procedure: fix, re-ask the one question at the new commit, "
    "compose 59 + 1 with per-question provenance, and leave the frozen 60 as evidence. "
    "MISLEADING = 0 is NOT claimed."
)

LEDGER_REASON = (
    "ASK_FORMAL_60_GRADED_GATE_FAILED. The external quota block is discharged: a "
    f"commit-keyed run at de7195c, run_id {RUN_ID}, answered 60 of 60 across two credential "
    "slots without forking run identity, and has been graded. The gate is not met. "
    "MISLEADING = 1 against a required 0, at Q38, which asserts two deity rankings the live "
    "graph contradicts while every figure it prints is real and correctly cited. Retrieval "
    "is not implicated: 60 of 60 packets replayed to identical item counts, 304 citations "
    "all resolve, 0 invented ids survived and 0 Sanskrit runs are fabricated. This consumer "
    "stays BLOCKED, but on our own synthesis guardrail rather than on a rate limit. The "
    "deterministic Ask suites still pass. Measurement: " + RECEIPT + ". "
    "SUPERSEDED REASON, kept because it was true when written: a fresh commit-keyed run at "
    "b986193 reached 0 of 60 and stopped at Q01 with LLMRateLimitError, the daily allowance "
    "being exhausted."
)


def patch_registry() -> bool:
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    for gap in data["gaps"]:
        if gap.get("gap_id") != GAP:
            continue
        if gap.get("status") == NEW:
            print(f"registry: {GAP} already {NEW}, no change")
            return False
        if gap.get("status") != OLD:
            raise SystemExit(f"registry: {GAP} is {gap.get('status')!r}, expected {OLD!r}")
        gap["status"] = NEW
        gap["closure_basis"] = CLOSURE_BASIS
        gap["ask_formal_60"] = {
            "run_id": RUN_ID,
            "code_commit": "de7195c",
            "answered": "60/60",
            "graded": "60/60",
            "clause_1_samavedic_passage": "PASS",
            "clause_2_metals_route": "PASS",
            "clause_3_misleading_zero": "FAIL",
            "MISLEADING": 1,
            "MISLEADING_ids": ["Q38"],
            "HALLUCINATED": 0,
            "invented_citations_surviving": 0,
            "receipt": RECEIPT,
        }
        REGISTRY.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print(f"registry: {GAP} {OLD} -> {NEW}")
        return True
    raise SystemExit(f"registry: {GAP} not found")


def patch_ledger() -> bool:
    data = json.loads(LEDGER.read_text(encoding="utf-8"))
    entry = data.get("Ask retrieval")
    if entry is None:
        raise SystemExit("ledger: 'Ask retrieval' consumer not found")
    if entry.get("blocked_reason", "").startswith("ASK_FORMAL_60_GRADED_GATE_FAILED"):
        print("ledger: already updated, no change")
        return False
    if not entry.get("blocked_reason", "").startswith(OLD):
        raise SystemExit(f"ledger: unexpected blocked_reason {entry.get('blocked_reason')!r:.80}")
    entry["blocked_reason"] = LEDGER_REASON
    LEDGER.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("ledger: 'Ask retrieval' blocked_reason replaced")
    return True


if __name__ == "__main__":
    patch_registry()
    patch_ledger()
