"""Adversarial QA of the audible-review harness, and the owner sample. Wave 4 Phase 10.

The harness's docstring says a verdict is refused without a named reviewer, refused for an
unknown verdict, and refused for ``AUDIBLY_VERIFIED`` when nothing played. This starts the
real server on a loopback port and tries all three, because a docstring is not a gate and
this campaign has already shipped two gates that could not fail.

It also checks the thing the owner's rules care about most: **no row promotes itself.** The
product audio catalogue must contain none of the 1,021 queued rows, so a staged mapping
cannot reach a reader without a listener first.

**Nothing here listens, and nothing here records a verdict against a real row.** The refusal
tests are run against a synthetic ``review_id`` in a temporary copy of the queue and log, and
the real files are never opened for writing. The output sample manifest is a list of rows for
a person to hear, carrying ``review_status: NEEDS_AUDIBLE_REVIEW`` and no verdict field at
all -- there is no field in it that could be mistaken for a verification.

Usage:
    python scripts/wave4_audio_harness_qa.py [--sample 100] [--seed vedanvaya-wave4]
"""

from __future__ import annotations

import argparse
import contextlib
import datetime
import hashlib
import json
import os
import pathlib
import random
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from typing import Any

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
QUEUE = PROJECT_ROOT / "data" / "staging" / "audio_review_queue.jsonl"
LOG = PROJECT_ROOT / "data" / "staging" / "audio_review_decisions.jsonl"
CATALOG = PROJECT_ROOT / "data" / "product" / "audio_catalog.jsonl"
HARNESS = PROJECT_ROOT / "scripts" / "audio_review_harness.py"
OUT = PROJECT_ROOT / "data" / "staging" / "wave4" / "audio_harness_qa.json"
MANIFEST = PROJECT_ROOT / "data" / "staging" / "wave4" / "audio_owner_sample_manifest.json"

PORT = 8471
BASE = f"http://127.0.0.1:{PORT}"
SYNTHETIC = "REV-WAVE4-QA-SYNTHETIC-NOT-A-REAL-ROW"


def read_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def post(path: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    request = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        body = error.read() or b"{}"
        with contextlib.suppress(json.JSONDecodeError):
            return error.code, json.loads(body)
        return error.code, {"raw": body.decode("utf-8", "replace")}


def wait_for_server(deadline: float) -> bool:
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{BASE}/api/queue", timeout=2):
                return True
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(0.4)
    return False


def refusal_tests(root: pathlib.Path) -> list[dict[str, Any]]:
    """Start the harness over a COPY of the queue and try to record dishonest verdicts.

    The copy holds one synthetic row. Any write the server makes lands in the sandbox, so a
    bug in these tests cannot mark a real recording verified.
    """
    sandbox = root / "data" / "staging"
    queue_copy = sandbox / "audio_review_queue.jsonl"
    log_copy = sandbox / "audio_review_decisions.jsonl"
    row = {
        "review_id": SYNTHETIC,
        "stratum": "WAVE4_QA",
        "stratum_description": "synthetic row, not part of the corpus",
        "review_priority": 99,
        "canonical_key": "VG:QA:SYNTHETIC",
        "citation": "QA synthetic",
        "canonical_sanskrit": "na etat satyam",
        "media_url": "about:blank",
        "source_name": "none -- synthetic",
        "is_segmented": False,
        "review_status": "NEEDS_AUDIBLE_REVIEW",
        "reviewer": None,
        "reviewed_at": None,
        "verdict": None,
        "reviewer_notes": None,
        "prior_automated_checks": {"note": "synthetic"},
        "listen_for": "nothing; this row exists to test a refusal",
        "blind_candidates": None,
    }
    queue_copy.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    log_copy.write_text("", encoding="utf-8")

    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    process = subprocess.Popen(
        [
            sys.executable,
            str(HARNESS),
            "--port",
            str(PORT),
            "--no-browser",
        ],
        cwd=root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    results: list[dict[str, Any]] = []
    try:
        if not wait_for_server(time.time() + 25):
            return [
                {
                    "check": "server_start",
                    "outcome": "FAIL",
                    "detail": "the harness did not answer on the loopback port",
                }
            ]

        cases = [
            (
                "an unknown verdict is refused",
                {
                    "review_id": SYNTHETIC,
                    "verdict": "SOUNDS_FINE_TO_ME",
                    "reviewer": "wave4-qa",
                    "listened_seconds": 30,
                },
                400,
                "a fourth verdict would be a way to avoid deciding",
            ),
            (
                "an anonymous verdict is refused",
                {
                    "review_id": SYNTHETIC,
                    "verdict": "AUDIBLY_VERIFIED",
                    "reviewer": "",
                    "listened_seconds": 30,
                },
                400,
                "a listening claim with no listener is what the queue exists to prevent",
            ),
            (
                "AUDIBLY_VERIFIED is refused when nothing played",
                {
                    "review_id": SYNTHETIC,
                    "verdict": "AUDIBLY_VERIFIED",
                    "reviewer": "wave4-qa",
                    "listened_seconds": 0,
                },
                400,
                "this is the rule that makes 'do not simulate listening' mechanical",
            ),
            (
                "an unknown review_id is refused",
                {
                    "review_id": "REV-DOES-NOT-EXIST",
                    "verdict": "AUDIBLE_REVIEW_UNCERTAIN",
                    "reviewer": "wave4-qa",
                    "listened_seconds": 5,
                },
                400,
                "a verdict on a row that is not in the queue would be unattributable",
            ),
        ]
        for name, payload, expected, why in cases:
            status, body = post("/api/decision", payload)
            results.append(
                {
                    "check": name,
                    "expected_status": expected,
                    "actual_status": status,
                    "outcome": "PASS" if status == expected else "FAIL",
                    "server_said": str(body.get("error") or body)[:220],
                    "why_it_matters": why,
                }
            )

        # The control: a permitted verdict must be ACCEPTED, or the refusals above prove only
        # that the endpoint rejects everything.
        status, body = post(
            "/api/decision",
            {
                "review_id": SYNTHETIC,
                "verdict": "AUDIBLE_REVIEW_UNCERTAIN",
                "reviewer": "wave4-qa",
                "listened_seconds": 0,
                "notes": "synthetic QA row; nothing was heard and nothing is claimed",
            },
        )
        results.append(
            {
                "check": "UNCERTAIN is accepted with nothing played (the control)",
                "expected_status": 200,
                "actual_status": status,
                "outcome": "PASS" if status == 200 else "FAIL",
                "server_said": str(body)[:220],
                "why_it_matters": (
                    "Uncertain must be as easy to record as the other two. A queue that makes "
                    "uncertainty inconvenient collects false certainty -- and if every verdict "
                    "were refused, the refusal tests above would be meaningless."
                ),
            }
        )

        # Resumability: the decision is in the append-only log, and replaying the log over the
        # queue reproduces it. Read from disk, not from the server's memory.
        logged = read_jsonl(log_copy)
        results.append(
            {
                "check": "the decision reached the append-only log on disk",
                "expected_status": None,
                "actual_status": None,
                "outcome": "PASS"
                if any(
                    entry.get("review_id") == SYNTHETIC
                    and entry.get("verdict") == "AUDIBLE_REVIEW_UNCERTAIN"
                    for entry in logged
                )
                else "FAIL",
                "server_said": f"{len(logged)} log entries",
                "why_it_matters": (
                    "The log is the record and the queue is a projection of it, so a decision "
                    "has to survive the process dying immediately after the response."
                ),
            }
        )
    finally:
        process.terminate()
        with contextlib.suppress(subprocess.TimeoutExpired):
            process.wait(timeout=10)
        process.kill()
    return results


#: The one stratum whose rows ARE already in the product catalogue, by construction. Named
#: rather than tolerated as a count: a numeric allowance would absorb the next real promotion.
ALREADY_SERVED_BY_DESIGN: dict[str, str] = {
    "RV_1_65_TO_1_70_AFFECTED_SPAN": (
        "These 61 rows were shipped before this campaign and are queued for audible RE-review, "
        "not for promotion: the span is where an edition merges verse pairs, so the risk is a "
        "recording of the pair rather than of the verse. Their presence in the catalogue is "
        "the reason they are in the queue, not evidence that the queue leaked."
    ),
}


def promotion_check(queue: list[dict[str, Any]]) -> dict[str, Any]:
    """No row awaiting its FIRST hearing may already be serving a reader.

    Scoped by stratum, because one stratum is already-served by construction. Checking the
    whole queue against the catalogue reports 61 hits and says nothing: the number that
    matters is how many of the 960 rows recovered or remapped in Wave 1 reached a reader
    without a listener.
    """
    catalogue = read_jsonl(CATALOG)
    served = {str(row.get("scope_key")) for row in catalogue}
    awaiting_first_hearing = [
        row for row in queue if str(row.get("stratum")) not in ALREADY_SERVED_BY_DESIGN
    ]
    leaked = sorted(
        str(row.get("canonical_key"))
        for row in awaiting_first_hearing
        if str(row.get("canonical_key")) in served
    )
    exempt = sorted(
        {
            str(row.get("stratum"))
            for row in queue
            if str(row.get("stratum")) in ALREADY_SERVED_BY_DESIGN
        }
    )
    return {
        "check": "no row awaiting its first hearing has promoted itself into the catalogue",
        "catalogue_rows": len(catalogue),
        "queued_rows": len(queue),
        "rows_awaiting_a_first_hearing": len(awaiting_first_hearing),
        "queued_keys_already_served": len(leaked),
        "examples": leaked[:5],
        "strata_already_served_by_design": {s: ALREADY_SERVED_BY_DESIGN[s] for s in exempt},
        "outcome": "PASS" if not leaked else "FAIL",
        "why_it_matters": (
            "A staged mapping that reaches a reader without a listener is exactly what the "
            "queue exists to prevent, and the registry already described these rows as closed."
        ),
    }


def sample(queue: list[dict[str, Any]], size: int, seed: str) -> dict[str, Any]:
    """A stratified, seeded, reproducible sample for the owner to hear.

    Proportional to stratum size with a floor of one, so the 6-row Samavedic container
    stratum -- the one with the most unusual grain and therefore the most to teach a
    listener -- is present rather than rounded away.
    """
    by_stratum: dict[str, list[dict[str, Any]]] = {}
    for row in queue:
        by_stratum.setdefault(str(row.get("stratum")), []).append(row)

    total = len(queue)
    quota: dict[str, int] = {}
    for stratum, rows in by_stratum.items():
        quota[stratum] = max(1, round(size * len(rows) / total))
    # Trim the largest stratum until the quota matches the requested size exactly, so the
    # manifest's own count is not an approximation of itself.
    while sum(quota.values()) > size:
        largest = max(quota, key=lambda s: quota[s])
        quota[largest] -= 1
    while sum(quota.values()) < size:
        largest = max(by_stratum, key=lambda s: len(by_stratum[s]))
        quota[largest] += 1

    rng = random.Random(seed)
    picked: list[dict[str, Any]] = []
    for stratum in sorted(by_stratum):
        rows = sorted(by_stratum[stratum], key=lambda r: str(r.get("review_id")))
        picked.extend(rng.sample(rows, min(quota[stratum], len(rows))))

    return {
        "artifact": "WAVE4_AUDIO_OWNER_SAMPLE_MANIFEST",
        "at": datetime.datetime.now(datetime.UTC).isoformat(),
        "seed": seed,
        "method": (
            "Stratified by review stratum, proportional to stratum size with a floor of one, "
            "sampled from a citation-sorted list with a fixed seed. Re-running with the same "
            "seed over the same queue reproduces the same rows."
        ),
        "not_a_verification": (
            "Every row here is NEEDS_AUDIBLE_REVIEW and carries no verdict field. Nothing in "
            "this manifest has been heard. Producing it is not reviewing, and it must not be "
            "read as a sample that passed."
        ),
        "requested": size,
        "selected": len(picked),
        "quota_by_stratum": dict(sorted(quota.items())),
        "rows": [
            {
                "review_id": row.get("review_id"),
                "stratum": row.get("stratum"),
                "review_priority": row.get("review_priority"),
                "citation": row.get("citation"),
                "canonical_key": row.get("canonical_key"),
                "canonical_sanskrit": row.get("canonical_sanskrit"),
                "media_url": row.get("media_url"),
                "source_name": row.get("source_name"),
                "performer": row.get("performer"),
                "licence": row.get("licence"),
                "duration_seconds": row.get("duration_seconds"),
                "is_segmented": row.get("is_segmented"),
                "listen_for": row.get("listen_for"),
                "blind_candidates": row.get("blind_candidates"),
                "review_status": "NEEDS_AUDIBLE_REVIEW",
            }
            for row in picked
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=int, default=100)
    parser.add_argument("--seed", default="vedanvaya-wave4-audio-sample")
    args = parser.parse_args()

    queue = read_jsonl(QUEUE)
    if not queue:
        print(f"  {QUEUE} is empty or missing.")
        return 1

    print()
    print("  WAVE 4 PHASE 10 -- AUDIO HARNESS QA")
    print()
    print(f"  queue rows                      {len(queue)}")
    print(f"  review_status NEEDS_AUDIBLE_REVIEW  "
          f"{sum(1 for r in queue if r.get('review_status') == 'NEEDS_AUDIBLE_REVIEW')}")
    print(f"  rows carrying a verdict         {sum(1 for r in queue if r.get('verdict'))}")
    print(f"  rows naming no source           {sum(1 for r in queue if not r.get('source_name'))}")
    print(f"  segmented (boundary review)     {sum(1 for r in queue if r.get('is_segmented'))}")
    print(f"  decisions recorded to date      {len(read_jsonl(LOG))}")
    print()

    structural = [
        {
            "check": "every row is queued for audible review and none carries a verdict",
            "outcome": "PASS"
            if all(
                r.get("review_status") == "NEEDS_AUDIBLE_REVIEW" and not r.get("verdict")
                for r in queue
            )
            else "FAIL",
            "why_it_matters": "0 of 1,021 rows have been listened to, and the file must say so.",
        },
        {
            "check": "every row names the source whose recording it is",
            "outcome": "PASS" if all(r.get("source_name") for r in queue) else "FAIL",
            "why_it_matters": (
                "804 rows carried source_name null before Wave 4, because the builder read a "
                "payload field the staged rows do not have. A reviewer was given a URL and "
                "left to infer whose recording it is."
            ),
        },
        {
            "check": "every row has something to play",
            "outcome": "PASS" if all(r.get("media_url") for r in queue) else "FAIL",
            "why_it_matters": "A row with no media cannot be reviewed and would sit forever.",
        },
        {
            "check": "no row asserts a timestamp nobody measured",
            "outcome": "PASS"
            if all(
                (r.get("start_seconds") is None) == (not r.get("is_segmented")) for r in queue
            )
            else "FAIL",
            "why_it_matters": (
                "is_segmented must mean exactly 'a start offset is asserted'. The campaign's "
                "rule is that no boundary is invented, so the flag and the field must agree."
            ),
        },
    ]
    for row in structural:
        print(f"    {row['outcome']}  {row['check']}")

    promotion = promotion_check(queue)
    print(f"    {promotion['outcome']}  {promotion['check']}")

    print()
    print("  refusal tests against the live harness, on a sandbox copy ...")
    # The harness resolves its paths as data/staging/... relative to its own cwd, so the
    # sandbox root is what it is launched in and the copies go two levels below it.
    root = PROJECT_ROOT / "data" / "staging" / "wave4" / "harness_sandbox"
    if root.exists():
        shutil.rmtree(root)
    (root / "data" / "staging").mkdir(parents=True, exist_ok=True)
    refusals = refusal_tests(root)
    for row in refusals:
        http = row.get("actual_status")
        suffix = f"  (HTTP {http})" if http is not None else ""
        print(f"    {row['outcome']}  {row['check']}{suffix}")
        if row["outcome"] == "FAIL" and row.get("detail"):
            print(f"          {row['detail']}")

    manifest = sample(queue, args.sample, args.seed)
    MANIFEST.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print()
    print(f"  owner sample: {manifest['selected']} rows -> {MANIFEST.relative_to(PROJECT_ROOT)}")
    for stratum, n in manifest["quota_by_stratum"].items():
        print(f"      {stratum:34} {n}")
    print("  NOT a verification: no row in it has been heard.")

    checks = [*structural, promotion, *refusals]
    failed = [c for c in checks if c["outcome"] == "FAIL"]
    report = {
        "artifact": "WAVE4_AUDIO_HARNESS_QA",
        "at": datetime.datetime.now(datetime.UTC).isoformat(),
        "queue_rows": len(queue),
        "queue_sha256": hashlib.sha256(QUEUE.read_bytes()).hexdigest(),
        "decisions_recorded": len(read_jsonl(LOG)),
        "rows_listened_to": 0,
        "listening_note": (
            "No audio was played by this script and none was simulated. The refusal tests use "
            "a synthetic review_id in a sandbox copy of the queue; the real queue and the real "
            "decision log were opened read-only."
        ),
        "checks": checks,
        "failed": [c["check"] for c in failed],
        "sample_manifest": str(MANIFEST.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "sample_rows": manifest["selected"],
        "sample_seed": args.seed,
    }
    report["sha256"] = hashlib.sha256(
        json.dumps(report, sort_keys=True, default=str).encode()
    ).hexdigest()
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print()
    print(f"  report: {OUT.relative_to(PROJECT_ROOT)}")
    if failed:
        print(f"\n  FAILED: {report['failed']}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
