"""Build the ten Mandalas as individually gated units, then assemble the full corpus.

Each Mandala is staged, built, and gated on its own.  One failing Mandala stops the run
before assembly, so a broken unit can never disappear inside aggregate statistics.
Timings and record counts are written to ``data/derived/rigveda_build_performance.json``.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import orjson

BUILDS = Path("data/builds")
PERFORMANCE = Path("data/derived/rigveda_build_performance.json")


def _run(*command: str) -> float:
    start = time.perf_counter()
    result = subprocess.run(command, check=False)
    elapsed = time.perf_counter() - start
    if result.returncode != 0:
        raise SystemExit(f"command failed ({result.returncode}): {' '.join(command)}")
    return elapsed


def _gate(mandala: int) -> tuple[bool, dict[str, Any]]:
    root = Path(f"data/canonical/rv_mandala_{mandala}_full_v1")

    def read(name: str) -> list[dict[str, Any]]:
        return [orjson.loads(line) for line in (root / name).read_bytes().splitlines() if line]

    passages = read("passages.jsonl")
    texts = read("text_versions.jsonl")
    mantras = {row["entity_id"] for row in passages if row["entity_type"] == "MANTRA"}
    covered = {
        role: {row["passage_id"] for row in texts if row["text_role"] == role}
        for role in ("PRIMARY_TEXT", "PARALLEL_TEXT")
    }
    severity = Counter(row["severity"] for row in read("qa_issues.jsonl"))
    summary = {
        "mandala": mandala,
        "suktas": sum(row["entity_type"] == "HYMN" for row in passages),
        "mantras": len(mantras),
        "primary": len(covered["PRIMARY_TEXT"] & mantras),
        "parallel": len(covered["PARALLEL_TEXT"] & mantras),
        "griffith": dict(Counter(row["alignment"] for row in read("translations.jsonl"))),
        "qa": dict(severity),
        "qa_checks": dict(Counter(row["check_id"] for row in read("qa_issues.jsonl"))),
        "output_bytes": sum(path.stat().st_size for path in root.glob("*.jsonl")),
    }
    passed = (
        bool(mantras)
        and severity.get("ERROR", 0) == 0
        and severity.get("CRITICAL", 0) == 0
        and covered["PRIMARY_TEXT"] >= mantras
        and covered["PARALLEL_TEXT"] >= mantras
    )
    return passed, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mandalas", type=int, nargs="*", default=list(range(1, 11)))
    parser.add_argument("--skip-assembly", action="store_true")
    args = parser.parse_args()

    timings: dict[str, float] = {}
    gates: list[dict[str, Any]] = []
    overall = time.perf_counter()
    for mandala in args.mandalas:
        config = BUILDS / f"rv_mandala_{mandala}_full_v1.yaml"
        print(f"\n=== MANDALA {mandala} ===", flush=True)
        timings[f"stage_m{mandala}"] = _run(
            sys.executable, "-m", "vedagraph", "ingest", "stage", "--config", str(config)
        )
        timings[f"build_m{mandala}"] = _run(
            sys.executable, "-m", "vedagraph", "corpus", "build", "--config", str(config)
        )
        passed, summary = _gate(mandala)
        gates.append({**summary, "gate": "PASS" if passed else "FAIL"})
        print(
            f"Mandala {mandala}: {summary['suktas']} Suktas, {summary['mantras']} mantras, "
            f"primary {summary['primary']}, parallel {summary['parallel']}, "
            f"griffith {summary['griffith']}, qa {summary['qa']} "
            f"{summary['qa_checks']} -> {'PASS' if passed else 'FAIL'}",
            flush=True,
        )
        if not passed:
            raise SystemExit(f"Mandala {mandala} failed its gate; assembly refused")

    if not args.skip_assembly:
        print("\n=== FULL ASSEMBLY ===", flush=True)
        timings["assemble"] = _run(
            sys.executable,
            "-m",
            "vedagraph",
            "corpus",
            "assemble",
            "--config",
            str(BUILDS / "rv_full_v1.yaml"),
        )
    timings["total"] = time.perf_counter() - overall

    PERFORMANCE.parent.mkdir(parents=True, exist_ok=True)
    PERFORMANCE.write_bytes(
        orjson.dumps(
            {
                "seconds": {key: round(value, 3) for key, value in timings.items()},
                "mandalas": gates,
            },
            option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS,
        )
        + b"\n"
    )
    print(f"\nWrote {PERFORMANCE} (total {timings['total']:.1f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
