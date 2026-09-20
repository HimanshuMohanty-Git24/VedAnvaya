"""Classify every builder by re-running it. Wave 4 Phase 2.

The dependency system says whether an output is CURRENT against its recorded inputs. It does
not say whether re-running the builder would produce that output again, and those are
different questions: a builder that stamps a timestamp into its artifact is CURRENT forever
and reproducible never.

So this runs each builder **twice** and compares the bytes. Nothing is inferred from the
dependency ledger, because the ledger's own digest is the thing under test.

Classification, per the owner's vocabulary:

``REPRODUCIBLE``
    Two consecutive runs produced byte-identical output.

``NONDETERMINISTIC_BUT_SEMANTICALLY_EQUIVALENT``
    The bytes differ and every difference is accounted for by a declared volatile field --
    a generation timestamp, a run id. The volatile fields are named per builder BEFORE the
    comparison, so "semantically equivalent" is a prediction that can fail rather than a
    description of whatever came out.

``DEFECTIVE_REGENERATION``
    The bytes differ in a way no declared volatile field explains. The output cannot be
    trusted to be what the builder would make.

``BLOCKED_EXTERNAL_SOURCE``
    The builder cannot run here: it needs a network source, a quota, or material this
    checkout does not hold.

``NOT_APPLICABLE``
    There is no builder, or nothing it would rebuild.

**A run that writes to the canonical store is not attempted.** Every builder here writes a
file. The graph-mutating migrations are receipted, single-shot and explicitly not idempotent
by design, and re-running one to measure its determinism would be a canonical mutation
performed for a measurement -- which the owner's rules bar and which no result would justify.
They are classified NOT_APPLICABLE with that reason, and their receipts are the evidence.

Usage:
    python scripts/wave4_rebuild_reproducibility.py [--only NAME]
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys
from typing import Any, Final, NamedTuple

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = PROJECT_ROOT / "data" / "staging" / "wave4" / "rebuild_reproducibility.json"
HOLD = PROJECT_ROOT / "data" / "staging" / "wave4" / "reproducibility_hold"


class Builder(NamedTuple):
    """One builder, its command, its outputs, and what is allowed to differ."""

    name: str
    #: argv. ``sys.executable`` and ``node`` are substituted for the first element.
    argv: tuple[str, ...]
    #: Files the run is expected to write, relative to the project root.
    outputs: tuple[str, ...]
    #: Working directory relative to the project root.
    cwd: str = "."
    #: Regexes for text that may legitimately differ between two runs. Declared per builder
    #: and applied to both sides before comparison.
    volatile: tuple[str, ...] = ()
    #: Exit codes that mean "the builder ran". Some of these scripts return a VERDICT rather
    #: than a health status -- the registry audit exits 1 while any entry is not terminated,
    #: and the dependency reporter exits 1 on unexplained staleness. Treating that as a failed
    #: build classified the audit DEFECTIVE_REGENERATION on the first run of this script, when
    #: its two runs in fact differed only by a timestamp. A builder whose exit code is an
    #: opinion needs its acceptable codes declared, not inferred.
    ok_exit: tuple[int, ...] = (0,)
    #: Set when the builder is not run, with the reason.
    skip: str = ""
    #: The classification to record when ``skip`` is set.
    skip_status: str = ""


_ISO = r'"\d{4}-\d{2}-\d{2}T[0-9:.]+(?:\+00:00|Z)?"'
_GENERATED = r'"generated(?:_at)?"\s*:\s*"[^"]*"'
_BUILT = r'"(?:built_at|at|created_at|measured_at|closure_measured_at)"\s*:\s*"[^"]*"'
_MD_STAMP = r"(?i)(generated|measured|as of|last built)[^\n]*\d{4}-\d{2}-\d{2}[^\n]*"
_RUN_ID = r'"run_id"\s*:\s*"[^"]*"'
_SHA = r'"sha256"\s*:\s*"[0-9a-f]{64}"'
_SECONDS = r"\d+\.\d+s"

BUILDERS: Final[tuple[Builder, ...]] = (
    Builder(
        "graph_quality_scorecard",
        ("python", "scripts/graph_quality_scorecard.py"),
        ("docs/reports/GRAPH_QUALITY_V2_SCORECARD.md",),
        volatile=(_MD_STAMP,),
    ),
    Builder(
        "generate_ontology_reference",
        ("python", "scripts/generate_ontology_reference.py"),
        ("docs/reports/VEDAGRAPH_ONTOLOGY_REFERENCE_V3.md",),
        volatile=(_MD_STAMP,),
    ),
    Builder(
        "export_predicate_semantics",
        ("python", "scripts/export_predicate_semantics.py"),
        ("frontend/public/world/world.predicates.json",),
        volatile=(_GENERATED, _ISO),
    ),
    Builder(
        "export_graph_world",
        ("python", "scripts/export_graph_world.py"),
        ("frontend/.world/world.raw.json",),
        volatile=(_GENERATED, _ISO),
    ),
    Builder(
        "build_atharvaveda_anukramani",
        ("python", "scripts/build_atharvaveda_anukramani.py"),
        (
            "data/canonical/atharvaveda_saunaka_digital_working_v1/traditional_metadata.jsonl",
            "data/registry/chandas_av.yaml",
        ),
        volatile=(_GENERATED, _ISO, _BUILT),
    ),
    Builder(
        "build_constellations",
        ("node", "scripts/build-constellations.mjs"),
        ("frontend/.world/constellations.json",),
        cwd="frontend",
        volatile=(_GENERATED, _ISO),
    ),
    Builder(
        "build_world",
        ("node", "scripts/build-world.mjs"),
        (
            "frontend/public/world/world.json",
            "frontend/public/world/world.labels.json",
            "frontend/public/world/world.bin",
        ),
        cwd="frontend",
        volatile=(_GENERATED, _ISO, _SECONDS),
    ),
    Builder(
        "wave4_registry_closure_audit",
        ("python", "scripts/wave4_registry_closure_audit.py"),
        ("data/staging/wave4/registry_closure_audit.json",),
        volatile=(_BUILT, _ISO, _SHA),
        ok_exit=(0, 1),
    ),
    Builder(
        "dependency_state",
        ("python", "scripts/dependency_state.py", "--status"),
        ("data/staging/integration/dependency_status.json",),
        volatile=(_BUILT, _ISO),
        ok_exit=(0, 1),
    ),
    Builder(
        "run_ask_benchmark",
        (),
        (),
        skip=(
            "Needs a live LLM provider and a daily quota. The fresh commit-keyed run stalled "
            "at 31 of 60 on a rate limit, which is recorded as "
            "ASK_FORMAL_REGRADE_BLOCKED_EXTERNAL_QUOTA rather than as a reproducibility "
            "result. Determinism of the RETRIEVAL half is covered by the deterministic Ask "
            "suite, which does not call a provider."
        ),
        skip_status="BLOCKED_EXTERNAL_SOURCE",
    ),
    Builder(
        "graph migrations M7-M12",
        (),
        (),
        skip=(
            "Single-shot receipted mutations of the canonical store, not idempotent by "
            "design: each refuses to run twice (M10 refuses if the targets are already "
            "internal, M12's rows are already written). Re-running one to measure its "
            "determinism would be a canonical mutation performed for a measurement. Their "
            "receipts in data/staging/integration/ carry the before and after census, the "
            "additive flag and the residual count, which is the evidence that exists and the "
            "evidence the owner's rules permit."
        ),
        skip_status="NOT_APPLICABLE",
    ),
    Builder(
        "semantic resemblance re-derivation",
        (),
        (),
        skip=(
            "The staged artifact is pre-Wave-3 and the owner bars importing an old score "
            "artifact, so the layer needs re-derivation from the final canonical snapshot "
            "rather than a rebuild. Nothing to re-run: there is no current builder whose "
            "output could be compared."
        ),
        skip_status="NOT_APPLICABLE",
    ),
)


def _resolve(argv: tuple[str, ...]) -> list[str]:
    head, *rest = argv
    if head == "python":
        return [sys.executable, *rest]
    if head == "node":
        return [shutil.which("node") or "node", *rest]
    return list(argv)


def _normalise(text: str, volatile: tuple[str, ...]) -> str:
    for pattern in volatile:
        text = re.sub(pattern, "<VOLATILE>", text)
    return text


def _digest(path: pathlib.Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def _snapshot(builder: Builder, tag: str) -> dict[str, dict[str, Any]]:
    """Copy each output aside and record its digest."""
    target = HOLD / builder.name.replace(" ", "_") / tag
    target.mkdir(parents=True, exist_ok=True)
    snap: dict[str, dict[str, Any]] = {}
    for relative in builder.outputs:
        source = PROJECT_ROOT / relative
        held = target / pathlib.Path(relative).name
        if source.exists():
            shutil.copy2(source, held)
        snap[relative] = {
            "digest": _digest(source),
            "bytes": source.stat().st_size if source.exists() else None,
            "held": str(held),
        }
    return snap


def _run(builder: Builder) -> tuple[int, str]:
    result = subprocess.run(
        _resolve(builder.argv),
        cwd=PROJECT_ROOT / builder.cwd,
        capture_output=True,
        text=True,
        errors="replace",
        check=False,
    )
    return result.returncode, (result.stdout + result.stderr)[-1500:]


def classify(builder: Builder) -> dict[str, Any]:
    if builder.skip:
        return {
            "builder": builder.name,
            "status": builder.skip_status,
            "reason": builder.skip,
            "runs": 0,
        }

    first_code, first_log = _run(builder)
    first = _snapshot(builder, "run1")
    second_code, second_log = _run(builder)
    second = _snapshot(builder, "run2")

    if first_code not in builder.ok_exit or second_code not in builder.ok_exit:
        return {
            "builder": builder.name,
            "status": "DEFECTIVE_REGENERATION",
            "reason": f"exit {first_code} then {second_code}, "
            f"declared acceptable: {list(builder.ok_exit)}",
            "log": second_log,
            "runs": 2,
            "differ_only_in_declared_volatile_fields": [],
            "unexplained_differences": ["not compared: a run did not complete"],
        }

    identical: list[str] = []
    volatile_only: list[str] = []
    differing: list[str] = []
    for relative in builder.outputs:
        a, b = first[relative]["digest"], second[relative]["digest"]
        if a is None or b is None:
            differing.append(f"{relative}: missing after a run")
            continue
        if a == b:
            identical.append(relative)
            continue
        path_a = pathlib.Path(first[relative]["held"])
        path_b = pathlib.Path(second[relative]["held"])
        try:
            text_a = path_a.read_text(encoding="utf-8", errors="replace")
            text_b = path_b.read_text(encoding="utf-8", errors="replace")
        except OSError:
            differing.append(f"{relative}: binary, digests differ")
            continue
        if _normalise(text_a, builder.volatile) == _normalise(text_b, builder.volatile):
            volatile_only.append(relative)
        else:
            differing.append(relative)

    if differing:
        status = "DEFECTIVE_REGENERATION"
    elif volatile_only:
        status = "NONDETERMINISTIC_BUT_SEMANTICALLY_EQUIVALENT"
    else:
        status = "REPRODUCIBLE"

    return {
        "builder": builder.name,
        "status": status,
        "runs": 2,
        "byte_identical_outputs": identical,
        "differ_only_in_declared_volatile_fields": volatile_only,
        "unexplained_differences": differing,
        "declared_volatile_patterns": list(builder.volatile),
        "first_run_tail": first_log[-400:],
        "outputs": {k: {"digest": v["digest"], "bytes": v["bytes"]} for k, v in second.items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", default="")
    args = parser.parse_args()

    chosen = [b for b in BUILDERS if not args.only or b.name == args.only]
    if not chosen:
        print(f"  no builder named {args.only!r}; known: {[b.name for b in BUILDERS]}")
        return 1

    print()
    print("  WAVE 4 PHASE 2 -- REBUILD REPRODUCIBILITY")
    print()
    print("  Each builder is run TWICE and the bytes compared. The dependency ledger is not")
    print("  consulted: its own digest is the thing under test.")
    print()

    rows: list[dict[str, Any]] = []
    for builder in chosen:
        print(f"  {builder.name} ...", flush=True)
        row = classify(builder)
        rows.append(row)
        print(f"      {row['status']}")
        for relative in row.get("unexplained_differences") or []:
            print(f"      UNEXPLAINED: {relative}")

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1

    report = {
        "artifact": "WAVE4_REBUILD_REPRODUCIBILITY",
        "at": datetime.datetime.now(datetime.UTC).isoformat(),
        "method": (
            "Two consecutive runs per builder, outputs compared byte for byte, then compared "
            "again with each builder's own declared volatile patterns masked. Volatile fields "
            "are declared before the comparison so that 'semantically equivalent' is a "
            "prediction that can fail."
        ),
        "counts": dict(sorted(counts.items())),
        "defective": sorted(r["builder"] for r in rows if r["status"] == "DEFECTIVE_REGENERATION"),
        "builders": rows,
    }
    report["sha256"] = hashlib.sha256(
        json.dumps(report, sort_keys=True, default=str).encode()
    ).hexdigest()
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print()
    for status, n in report["counts"].items():
        print(f"    {status:48} {n}")
    print()
    print(f"  report: {OUT.relative_to(PROJECT_ROOT)}")
    if report["defective"]:
        print(f"\n  DEFECTIVE REGENERATION: {report['defective']}")
    return 1 if report["defective"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
