"""Prove the dependency system can report STALE, and then return. Wave 4 Phase 8.

A dependency report that says CURRENT for everything is indistinguishable from a dependency
report that cannot say anything else, and this campaign has shipped two gates of exactly that
kind -- an M9 readback that rebuilt its expectation from the mutated graph, and an orphan
sweep that looked at one label family. So the report is not evidence until a perturbation
moves it.

**What is perturbed, and why that one.** ``frontend/.world/world.raw.json`` is the Python
export's declared OUTPUT and the Lab stage's declared FILE INPUT. Both of those declarations
are new in Wave 4, and both were added because of a measured defect: the two world consumers
had recorded that same intermediate as their output, so the Lab could never be seen stale and
the four files a browser downloads were declared by nothing. M10 marked 28 malformed metre
identities internal, the export dropped them, and ``world.labels.json`` still carried all 28
to every reader.

One byte appended to that file must therefore move two consumers for two different reasons:

    Knowledge World public projection   its declared output no longer matches its digest
    Visualization Lab aggregates        a declared file input moved

and no others. A perturbation that moved everything would prove nothing about which edges the
system actually holds.

**Restoration is byte-exact and verified.** The original bytes are held in the scratch copy,
written back, and the sha256 re-measured against the value taken before the perturbation. The
file is a gitignored derived artifact, so nothing in version control is touched either way.

Usage:
    python scripts/wave4_dependency_perturbation.py
"""

from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
import subprocess
import sys

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
TARGET = PROJECT_ROOT / "frontend" / ".world" / "world.raw.json"
HOLD = PROJECT_ROOT / "data" / "staging" / "wave4" / "perturbation_hold.bin"
OUT = PROJECT_ROOT / "data" / "staging" / "wave4" / "dependency_perturbation.json"
REPORT = PROJECT_ROOT / "data" / "staging" / "integration" / "dependency_status.json"

#: Exactly the consumers that must move, and the reason each must give. Declared here, ahead
#: of the run, so the assertion is against a stated expectation rather than against whatever
#: the run happens to produce -- the mistake M9's readback made.
EXPECTED_STALE: dict[str, str] = {
    "Knowledge World public projection": "declared output",
    "Visualization Lab aggregates": "file:frontend/.world/world.raw.json",
}


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def statuses() -> dict[str, dict[str, object]]:
    """Run the real reporter as a subprocess and read its artifact.

    A subprocess rather than an import: the status path opens its own driver session and
    writes the report the rest of the campaign reads, and running anything else here would be
    testing a second implementation.
    """
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scripts" / "dependency_state.py"), "--status"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode not in (0, 1):
        raise SystemExit(f"dependency_state.py --status failed: {result.stderr[-2000:]}")
    payload = json.loads(REPORT.read_text(encoding="utf-8"))
    return {
        str(row["consumer"]): {
            "status": str(row["status"]),
            "moved": list(row["inputs_that_moved"] or []),
            "reason": row.get("reason"),
        }
        for row in payload["consumers"]
    }


def main() -> int:
    if not TARGET.exists():
        print(f"  {TARGET} is missing; nothing to perturb.")
        return 1

    before_hash = sha256(TARGET)
    original = TARGET.read_bytes()
    HOLD.parent.mkdir(parents=True, exist_ok=True)
    HOLD.write_bytes(original)
    if sha256(HOLD) != before_hash:
        print("  the scratch copy does not match the original; refusing to perturb.")
        return 1

    print()
    print("  WAVE 4 PHASE 8 -- DEPENDENCY PERTURBATION")
    print()
    print(f"  target   {TARGET.relative_to(PROJECT_ROOT)}")
    print(f"  sha256   {before_hash[:16]}...  ({len(original):,} bytes)")
    print(f"  held at  {HOLD.relative_to(PROJECT_ROOT)}")
    print()

    print("  baseline ...")
    baseline = statuses()
    for name, row in baseline.items():
        print(f"    {name:40} {row['status']}")
    not_current = sorted(n for n, r in baseline.items() if r["status"] == "STALE_INPUT")
    if not_current:
        print(f"\n  REFUSING: {not_current} is already STALE, so a transition to STALE would "
              "prove nothing. Rebuild and re-record first.")
        TARGET.write_bytes(original)
        return 1

    restored_hash = ""
    try:
        print("\n  perturbing: one newline appended ...")
        TARGET.write_bytes(original + b"\n")
        perturbed = statuses()
        print()
        for name, row in perturbed.items():
            mark = "<<<" if row["status"] == "STALE_INPUT" else "   "
            print(f"    {name:40} {row['status']!s:14} {mark}")
    finally:
        TARGET.write_bytes(original)
        restored_hash = sha256(TARGET)
        HOLD.unlink(missing_ok=True)

    print("\n  restored ...")
    restored = statuses()
    for name, row in restored.items():
        print(f"    {name:40} {row['status']}")

    went_stale = {n for n, r in perturbed.items() if r["status"] == "STALE_INPUT"}
    expected = set(EXPECTED_STALE)
    findings: list[str] = []
    if went_stale != expected:
        findings.append(
            f"consumers that went stale {sorted(went_stale)} != expected {sorted(expected)}"
        )
    for name, token in EXPECTED_STALE.items():
        row = perturbed.get(name) or {}
        said = " ".join([str(row.get("reason") or ""), *[str(m) for m in row.get("moved") or []]])
        if token not in said:
            findings.append(f"{name} went stale without naming {token!r}: {said!r}")
    if restored_hash != before_hash:
        findings.append("the file was not restored byte-exactly")
    if {n: r["status"] for n, r in restored.items()} != {
        n: r["status"] for n, r in baseline.items()
    }:
        findings.append("the restored report does not match the baseline report")

    receipt = {
        "artifact": "WAVE4_DEPENDENCY_PERTURBATION",
        "at": datetime.datetime.now(datetime.UTC).isoformat(),
        "target": str(TARGET.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "perturbation": "one newline appended, then the original bytes written back",
        "sha256_before": before_hash,
        "sha256_after_restore": restored_hash,
        "byte_exact_restore": restored_hash == before_hash,
        "expected_stale": EXPECTED_STALE,
        "baseline": baseline,
        "perturbed": perturbed,
        "restored": restored,
        "went_stale": sorted(went_stale),
        "findings": findings,
        "passed": not findings,
    }
    receipt["sha256"] = hashlib.sha256(
        json.dumps(receipt, sort_keys=True, default=str).encode()
    ).hexdigest()
    OUT.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print()
    print(f"  went stale under perturbation   {sorted(went_stale)}")
    print(f"  byte-exact restore              {receipt['byte_exact_restore']}")
    print(f"  baseline reproduced            {'yes' if not findings else 'see findings'}")
    for finding in findings:
        print(f"  FINDING: {finding}")
    print()
    print(f"  receipt: {OUT.relative_to(PROJECT_ROOT)}")
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
