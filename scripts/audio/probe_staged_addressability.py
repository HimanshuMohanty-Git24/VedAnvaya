"""Ask the publisher, for every withheld staged recording, whether the media still answers.

**Why this exists.** The two-tier publication policy of 2026-09-19 (see
``docs/decisions/OWNER_DECISION_AUDIO_TWO_TIER_PUBLICATION.md``) lets a row be published
without a human having heard it, but only if the source media *actually resolves* on the
day of admission. ``availability: AVAILABLE`` in a staging row is a claim recorded on
2026-09-15 by whichever agent staged it; re-reading that field would be reading our own
report back to ourselves rather than measuring anything.

**Three hosts, three honest checks.** They are not interchangeable and this script does not
pretend they are.

``vedaweb.uni-koeln.de``
    Refuses ``HEAD`` with 403 and answers ``GET`` with 200, so the check is a full ``GET``
    -- and because these rows record ``sha256`` and ``bytes`` of the file as fetched on
    2026-09-15, the check goes further than reachability and re-hashes the body. A file
    that resolves but has been replaced is caught here and nowhere else.

``huggingface.co``
    Answers ``HEAD`` with a real ``Content-Length`` and an audio content type, so a ``HEAD``
    establishes both. These rows carry no checksum, so no checksum is claimed for them.

``vedsearch.org``
    Serves audio as base64 inside a JSON document; the useful signal from ``HEAD`` is the
    document's ``Content-Length``, which runs about 4/3 of the audio. A short document is an
    error page rather than a recording, so anything under
    :data:`VEDSEARCH_MIN_DOCUMENT_BYTES` is settled with a real ``GET`` and counted as
    resolving only if the body actually carries ``attachment_content_base64``.

**Politeness is a parameter, not a comment.** Four workers by default, a per-request
stagger, one retry on a transport error, and nothing fetched twice. A row whose check fails
is reported ``UNRESOLVED`` -- never as proof the recording is gone, which is a stronger
claim than one probe can make.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Final
from urllib.parse import urlparse

import requests

REPO_ROOT: Final = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from vedagraph.product.audio.net import USER_AGENT  # noqa: E402

#: The three withheld staging sets, in the order they are reported.
STAGED_SETS: Final = ("audio_rv", "audio_av", "audio_yv")

#: Below this, a VedSearch JSON document is too small to be carrying a recitation, so its
#: length settles nothing and the probe falls through to a real GET.
VEDSEARCH_MIN_DOCUMENT_BYTES: Final = 8_000

#: Read cap for the VedaWeb GET. Larger than any file measured, so the hash is over the
#: whole body; present only so a pathological response cannot fill memory.
MAX_BODY_BYTES: Final = 32 * 1024 * 1024


@dataclass(frozen=True)
class ProbeResult:
    canonical_key: str
    audio_id: str
    staged_set: str
    source_id: str
    media_url: str
    method: str
    status: int | None
    content_type: str | None
    content_length: int | None
    resolves: bool
    checksum_matches: bool | None
    outcome: str
    detail: str


def _rows(staged_set: str) -> list[dict[str, Any]]:
    path = REPO_ROOT / "data" / "staging" / staged_set / "rows.jsonl"
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


_local = threading.local()


def _thread_session() -> requests.Session:
    session = getattr(_local, "session", None)
    if session is None:
        session = requests.Session()
        session.headers.update({"User-Agent": USER_AGENT, "Accept": "*/*"})
        _local.session = session
    return session


def _probe_vedaweb(row: dict[str, Any], url: str, timeout: float) -> tuple[Any, ...]:
    """Full GET plus a re-hash against the checksum the staging row recorded."""
    session = _thread_session()
    response = session.get(url, timeout=timeout, stream=True)
    body = response.raw.read(MAX_BODY_BYTES, decode_content=True)
    response.close()
    digest = hashlib.sha256(body).hexdigest()
    measurements = row.get("measurements") or {}
    expected_sha = measurements.get("sha256")
    expected_bytes = measurements.get("bytes")
    ok = response.status_code == 200 and len(body) > 0
    matches: bool | None = None
    detail = f"{len(body)} bytes"
    if expected_sha:
        matches = digest == expected_sha
        detail += f"; sha256 {'matches' if matches else 'DIFFERS FROM'} the staged measurement"
        if expected_bytes is not None and expected_bytes != len(body):
            detail += f"; staged byte count {expected_bytes}"
    return (
        "GET",
        response.status_code,
        response.headers.get("Content-Type"),
        len(body),
        ok,
        matches,
        detail,
    )


def _probe_huggingface(url: str, timeout: float) -> tuple[Any, ...]:
    session = _thread_session()
    response = session.head(url, timeout=timeout, allow_redirects=True)
    length = response.headers.get("Content-Length")
    size = int(length) if length and length.isdigit() else None
    ctype = response.headers.get("Content-Type")
    ok = response.status_code == 200 and bool(size) and bool(ctype and ctype.startswith("audio"))
    return (
        "HEAD",
        response.status_code,
        ctype,
        size,
        ok,
        None,
        f"content-type {ctype}, {size} bytes",
    )


def _probe_vedsearch(url: str, timeout: float) -> tuple[Any, ...]:
    session = _thread_session()
    response = session.head(url, timeout=timeout, allow_redirects=True)
    length = response.headers.get("Content-Length")
    size = int(length) if length and length.isdigit() else None
    ctype = response.headers.get("Content-Type")
    if response.status_code == 200 and size and size >= VEDSEARCH_MIN_DOCUMENT_BYTES:
        return "HEAD", 200, ctype, size, True, None, f"JSON document of {size} bytes"
    # Too short, or the server declined the HEAD: settle it with a real GET, because a
    # length is an argument about a recording and a payload is the recording.
    got = session.get(url, timeout=timeout)
    carries = False
    try:
        document = got.json()
        inner = document.get("data") or document
        payload = inner.get("attachment_content_base64")
        carries = isinstance(payload, str) and len(payload) > 1_000
    except Exception:
        carries = False
    return (
        "HEAD+GET",
        got.status_code,
        got.headers.get("Content-Type"),
        len(got.content),
        carries,
        None,
        "GET carries attachment_content_base64" if carries else "GET carries no audio payload",
    )


def probe(row: dict[str, Any], staged_set: str, timeout: float, stagger: float) -> ProbeResult:
    payload = row["payload"]
    url = payload.get("media_url") or row.get("source_url") or ""
    host = urlparse(url).netloc
    time.sleep(stagger)
    method: str | None = None
    status: int | None = None
    ctype: str | None = None
    size: int | None = None
    ok = False
    matches: bool | None = None
    detail = ""
    for attempt in (1, 2):
        try:
            if host.endswith("vedaweb.uni-koeln.de"):
                method, status, ctype, size, ok, matches, detail = _probe_vedaweb(row, url, timeout)
            elif host.endswith("huggingface.co"):
                method, status, ctype, size, ok, matches, detail = _probe_huggingface(url, timeout)
            elif host.endswith("vedsearch.org"):
                method, status, ctype, size, ok, matches, detail = _probe_vedsearch(url, timeout)
            else:
                method, ok, detail = "NONE", False, f"unrecognised host {host!r}; not probed"
            break
        except Exception as error:
            if attempt == 2:
                method = method or "ERROR"
                detail = f"{type(error).__name__}: {error}"
            else:
                time.sleep(2.0)
    outcome = "RESOLVES" if ok else "UNRESOLVED"
    if ok and matches is False:
        outcome = "RESOLVES_BUT_CHECKSUM_DIFFERS"
    return ProbeResult(
        canonical_key=row["canonical_key"],
        audio_id=payload.get("audio_id", ""),
        staged_set=staged_set,
        source_id=row.get("source_id", ""),
        media_url=url,
        method=str(method),
        status=status,
        content_type=ctype,
        content_length=size,
        resolves=ok,
        checksum_matches=matches,
        outcome=outcome,
        detail=detail,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe staged audio media addressability.")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--stagger", type=float, default=0.25, help="Seconds slept per request.")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--limit", type=int, default=0, help="0 probes every staged row.")
    parser.add_argument(
        "--resummarise",
        action="store_true",
        help="Rebuild the summary from rows already written, without touching the network.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "docs" / "reports" / "audio" / "staged_addressability_probe.jsonl",
    )
    args = parser.parse_args()

    tasks: list[tuple[dict[str, Any], str]] = []
    for staged_set in STAGED_SETS:
        for row in _rows(staged_set):
            tasks.append((row, staged_set))
    if args.limit:
        tasks = tasks[: args.limit]

    started = time.time()
    results: list[ProbeResult] = []
    if args.resummarise:
        with args.out.open(encoding="utf-8") as handle:
            results = [ProbeResult(**json.loads(line)) for line in handle if line.strip()]
    else:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            mapped = pool.map(lambda t: probe(t[0], t[1], args.timeout, args.stagger), tasks)
            for index, result in enumerate(mapped, start=1):
                results.append(result)
                if index % 50 == 0:
                    elapsed = time.time() - started
                    print(f"  {index}/{len(tasks)} probed ({elapsed:.0f}s)", flush=True)

        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("w", encoding="utf-8", newline="\n") as handle:
            for result in sorted(results, key=lambda r: (r.staged_set, r.canonical_key)):
                handle.write(json.dumps(asdict(result), ensure_ascii=False, sort_keys=True) + "\n")

    summary_path = args.out.with_suffix(".summary.json")
    previous: dict[str, Any] = {}
    if args.resummarise and summary_path.exists():
        # Carry the original run's clock forward. A rebuilt summary that stamped itself
        # with today's time and zero seconds would claim a probe that did not happen.
        previous = json.loads(summary_path.read_text(encoding="utf-8"))
    summary: dict[str, Any] = {
        "artifact": "STAGED_AUDIO_ADDRESSABILITY_PROBE",
        "probed_at": previous.get("probed_at")
        or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "user_agent": USER_AGENT,
        "sampling": "census -- every staged row probed, none sampled",
        "requests_made": len(results),
        "elapsed_seconds": previous.get("elapsed_seconds")
        if args.resummarise
        else round(time.time() - started, 1),
        "workers": previous.get("workers") if args.resummarise else args.workers,
        "resummarised_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        if args.resummarise
        else None,
        "by_set": {},
        "by_outcome": {},
        "unresolved": [],
    }
    for result in results:
        per = summary["by_set"].setdefault(
            result.staged_set,
            {
                "probed": 0,
                "resolves": 0,
                "unresolved": 0,
                # Three buckets, not two. A set whose rows recorded no checksum would
                # otherwise report "checksum_matches: 0" and read as 771 mismatches; the
                # absence has to be typed in the row rather than explained in a caveat.
                "checksum_recorded_and_matches": 0,
                "checksum_recorded_and_differs": 0,
                "no_checksum_recorded_so_none_claimed": 0,
            },
        )
        per["probed"] += 1
        per["resolves" if result.resolves else "unresolved"] += 1
        if result.checksum_matches is None:
            per["no_checksum_recorded_so_none_claimed"] += 1
        elif result.checksum_matches:
            per["checksum_recorded_and_matches"] += 1
        else:
            per["checksum_recorded_and_differs"] += 1
        summary["by_outcome"][result.outcome] = summary["by_outcome"].get(result.outcome, 0) + 1
        if not result.resolves or result.checksum_matches is False:
            summary["unresolved"].append(
                {
                    "canonical_key": result.canonical_key,
                    "audio_id": result.audio_id,
                    "outcome": result.outcome,
                    "status": result.status,
                    "detail": result.detail,
                }
            )
    summary_path = args.out.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "unresolved"}, indent=2))
    print(f"rows: {args.out}")
    print(f"summary: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
