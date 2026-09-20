#!/usr/bin/env python3
"""Account for every test in the release report, including the ones a gate skips.

The defect this exists for
==========================

R3 ran ``tests/domain`` with ``VEDAGRAPH_LIVE_NEO4J=1`` -- the gate the default run skips --
and found six failures the reported "5 known failures" had never included. A skipped test
reports neither pass nor fail, so a release report built from one run's totals is silent
about every test that run did not execute. Four formula-family failures and one community
failure had been sitting behind that silence.

"N passed, M skipped" is therefore not an accounting. This script produces one, by running
the suite under **every gate** and reconciling the runs against each other:

*   ``collected``, ``executed``, ``skipped`` and ``deselected`` are reported per run, not
    summed into a single number that hides which run contributed what.

*   **A test skipped in one run must be executed in another.** Anything skipped in all of
    them is ``never_executed`` and reported by name. That is the hiding place, and a count
    of skips can never reveal it -- only the reconciliation can.

*   **A failure under any gate is a release failure.** ``live_gated_failures`` is reported
    separately from default-run failures so that "the default run is green" can never be
    mistaken for "the suite is green", which is the exact substitution R3 caught.

The exit code is non-zero while ``never_executed`` or any failure is non-empty.

Usage:
    python scripts/release_test_accounting.py [--paths tests/domain tests/graph]
                                              [--json OUT]
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from typing import Any, Final, NamedTuple

PROJECT_ROOT: Final = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_OUT: Final = PROJECT_ROOT / "data" / "staging" / "release_blocker_r4" / "test_accounting.json"

#: Each gate is a name and the environment that opens it. The default run is the one whose
#: totals a release report would otherwise quote on its own.
GATES: Final[tuple[tuple[str, dict[str, str]], ...]] = (
    ("default", {}),
    ("live_neo4j", {"VEDAGRAPH_LIVE_NEO4J": "1"}),
)

_COLLECTED: Final = re.compile(r"collected (\d+) items?")
_DESELECTED: Final = re.compile(r"(\d+) deselected")

#: Skip reasons that describe an input this project deliberately does not hold, rather
#: than a test nobody runs. Reported, allowed, and named -- not silently tolerated.
ALLOWED_SKIP_REASONS: Final[tuple[str, ...]] = (
    "1856 scan not present in this checkout",
    "OPENAI_API_KEY",
)


class Run(NamedTuple):
    gate: str
    collected: int
    deselected: int
    executed: tuple[str, ...]
    passed: tuple[str, ...]
    failed: tuple[str, ...]
    skipped: tuple[str, ...]
    errored: tuple[str, ...]
    returncode: int
    #: node id -> the reason pytest gave for skipping it. A node id cannot distinguish a
    #: skip on an input this project deliberately removed from a test nobody runs, and
    #: that is exactly the distinction the exit code turns on.
    skip_reasons: tuple[tuple[str, str], ...] = ()


def _node_id(case: ET.Element) -> str:
    """The pytest node id for a junit ``testcase``, as ``path::name``."""
    classname = (case.get("classname") or "").replace(".", "/")
    name = case.get("name") or "?"
    file_attr = case.get("file")
    if file_attr:
        return f"{file_attr.replace(chr(92), '/')}::{name}"
    return f"{classname}.py::{name}"


def run_gate(gate: str, env_extra: dict[str, str], paths: list[str]) -> Run:
    with tempfile.TemporaryDirectory() as tmp:
        xml = pathlib.Path(tmp) / "report.xml"
        env = {**os.environ, **env_extra}
        # Coverage is priced out deliberately: this script counts outcomes, and the tracer
        # only makes the run slower. The recorded hazard is that a latency assertion
        # elsewhere prices the tracer, which is not what is being measured here.
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                *paths,
                "-p",
                "no:randomly",
                "--no-cov",
                "-q",
                f"--junitxml={xml}",
            ],
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        stdout = proc.stdout or ""
        collected = max((int(m.group(1)) for m in _COLLECTED.finditer(stdout)), default=0)
        deselected = max((int(m.group(1)) for m in _DESELECTED.finditer(stdout)), default=0)

        passed: list[str] = []
        failed: list[str] = []
        skipped: list[str] = []
        errored: list[str] = []
        reasons: dict[str, str] = {}
        if xml.exists():
            root = ET.parse(xml).getroot()
            # ``-q`` does not print "collected N items", so the junit total is the reliable
            # source. Reading it off stdout returned 0 and made the column look empty.
            collected = max(
                collected,
                sum(int(suite.get("tests") or 0) for suite in root.iter("testsuite")),
            )
            for case in root.iter("testcase"):
                node = _node_id(case)
                if case.find("failure") is not None:
                    failed.append(node)
                elif case.find("error") is not None:
                    errored.append(node)
                elif (skip := case.find("skipped")) is not None:
                    skipped.append(node)
                    reasons[node] = (skip.get("message") or "") + " " + (skip.text or "")
                else:
                    passed.append(node)

    executed = tuple(sorted(passed + failed + errored))
    return Run(
        gate=gate,
        collected=collected,
        deselected=deselected,
        executed=executed,
        passed=tuple(sorted(passed)),
        failed=tuple(sorted(failed)),
        skipped=tuple(sorted(skipped)),
        errored=tuple(sorted(errored)),
        returncode=proc.returncode,
        skip_reasons=tuple(sorted(reasons.items())),
    )


def reconcile(runs: list[Run]) -> dict[str, Any]:
    executed_anywhere = {node for run in runs for node in run.executed}
    skipped_anywhere = {node for run in runs for node in run.skipped}
    never_executed = sorted(skipped_anywhere - executed_anywhere)

    default = next((r for r in runs if r.gate == "default"), None)
    gated = [r for r in runs if r.gate != "default"]
    reasons: dict[str, str] = {}
    for run in runs:
        reasons.update(dict(run.skip_reasons))
    allowed = [
        node
        for node in never_executed
        if any(marker in reasons.get(node, "") for marker in ALLOWED_SKIP_REASONS)
    ]
    unexplained = [node for node in never_executed if node not in set(allowed)]

    return {
        "per_gate": {
            run.gate: {
                "collected": run.collected,
                "executed": len(run.executed),
                "passed": len(run.passed),
                "failed": len(run.failed),
                "errored": len(run.errored),
                "skipped": len(run.skipped),
                "deselected": run.deselected,
                "returncode": run.returncode,
                "failures": list(run.failed),
                "errors": list(run.errored),
            }
            for run in runs
        },
        "default_run_failures": list(default.failed + default.errored) if default else [],
        "live_gated_failures": sorted(
            {node for run in gated for node in run.failed + run.errored}
        ),
        # A test the default run skipped and a gated run then failed. R3's exact finding:
        # it is absent from the default totals and red under the gate.
        "hidden_by_a_skip": sorted(
            {node for run in gated for node in run.failed + run.errored}
            & set(default.skipped if default else ())
        ),
        "never_executed_under_any_gate": never_executed,
        "never_executed_allowed_by_reason": allowed,
        "never_executed_unexplained": unexplained,
        "allowed_skip_reasons": list(ALLOWED_SKIP_REASONS),
        "skip_reasons_seen": sorted({reasons[node] .strip()[:120] for node in never_executed}),
        "executed_under_at_least_one_gate": len(executed_anywhere),
        "skipped_under_at_least_one_gate": len(skipped_anywhere),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--paths",
        nargs="+",
        default=["tests"],
        help=(
            "Test paths to account for. Defaults to the WHOLE tree: an earlier default of "
            "domain/graph/unit left tests/api -- 1,539 tests, including every file R4 "
            "modified -- outside the accounted set, which let one path-set's totals stand "
            "in for the suite. That is the same substitution this script exists to stop, "
            "one level up."
        ),
    )
    parser.add_argument("--json", type=pathlib.Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    runs = [run_gate(gate, env, args.paths) for gate, env in GATES]
    summary = reconcile(runs)

    report = {
        "artifact": "RELEASE_TEST_ACCOUNTING",
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "paths": args.paths,
        "gates": [gate for gate, _ in GATES],
        **summary,
    }

    print()
    print("  RELEASE TEST ACCOUNTING")
    print()
    print(f"  {'gate':<12} {'collected':>9} {'executed':>9} {'passed':>7} {'failed':>7} "
          f"{'skipped':>8} {'desel':>6}")
    for gate, row in report["per_gate"].items():
        print(f"  {gate:<12} {row['collected']:>9} {row['executed']:>9} {row['passed']:>7} "
              f"{row['failed'] + row['errored']:>7} {row['skipped']:>8} {row['deselected']:>6}")
    print()
    print(f"  executed under at least one gate   {report['executed_under_at_least_one_gate']}")
    print(f"  live-gated failures                {len(report['live_gated_failures'])}")
    print(f"  default-run failures               {len(report['default_run_failures'])}")
    print(f"  hidden by a skip                   {len(report['hidden_by_a_skip'])}")
    print(f"  never executed under any gate      {len(report['never_executed_under_any_gate'])}"
          f"  (allowed by reason {len(report['never_executed_allowed_by_reason'])}, "
          f"unexplained {len(report['never_executed_unexplained'])})")
    print()
    for node in report["live_gated_failures"]:
        print(f"  LIVE-GATED FAILURE: {node}")
    for node in report["default_run_failures"]:
        print(f"  FAILURE: {node}")
    for node in report["never_executed_unexplained"]:
        print(f"  NEVER EXECUTED, UNEXPLAINED: {node}")
    for reason in report["skip_reasons_seen"]:
        print(f"  skip reason seen: {reason}")

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"  report: {args.json.relative_to(PROJECT_ROOT)}")
    print()

    # A never-executed test is a finding, not automatically a failure: 40 of them skip on
    # "1856 scan not present in this checkout", an input this project deliberately removed
    # when the Atharvavedic image transcription was cancelled, and one on a missing
    # OPENAI_API_KEY. A guard with no green state gets ignored, so those are allowed BY
    # THEIR REASON and anything else still fails.
    bad = (
        bool(report["live_gated_failures"])
        or bool(report["default_run_failures"])
        or bool(report["never_executed_unexplained"])
    )
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
