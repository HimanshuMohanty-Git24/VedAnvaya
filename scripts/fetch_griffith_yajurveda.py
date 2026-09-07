"""Snapshot Griffith's 1899 White Yajurveda from the Internet Sacred Text Archive.

What is acquired
================
Forty book pages, ``https://sacred-texts.com/hin/wyv/wyvbk01.htm`` .. ``wyvbk40.htm``,
plus the work index and the errata page that the book pages themselves link to. One
sacred-texts "book" is one VSM adhyaya, so the forty pages cover the whole samhita.

Why the files are content-addressed
===================================
``data/raw/**`` is gitignored, so the bytes are not the provenance record; the sha256 in
the filename is. A snapshot named ``<sha256>.html`` cannot be silently edited in place:
any change to the bytes changes the name, and every downstream record that cites a
``snapshot_sha256`` either resolves to a file or does not. A ``<sha256>.metadata.json``
sidecar records the retrieval URL, byte size, HTTP status and fetch time, and
``manifest.json`` maps the logical page ids (``book-01`` .. ``book-40``, ``index``,
``errata``) onto those digests in a stable order.

Re-running is cheap and non-destructive: a page whose current bytes already exist on disk
is not re-written, and a page whose bytes have changed lands beside the old snapshot
rather than over it.

The site now serves a JavaScript application shell around the text, so roughly 97% of each
response is chrome. This script deliberately stores the response VERBATIM and does no
extraction at all -- extraction is the adapter's job
(:mod:`vedagraph.ingest.adapters.griffith_yajurveda`) and must be re-runnable against the
pinned bytes without a network.

Usage::

    python scripts/fetch_griffith_yajurveda.py             # fetch all pages
    python scripts/fetch_griffith_yajurveda.py --books 1 2 # fetch a subset
    python scripts/fetch_griffith_yajurveda.py --manifest-only
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

SOURCE_ID = "SACRED_TEXTS"
SNAPSHOT_ID = "2026-09-07"
BOOK_COUNT = 40
BASE = "https://sacred-texts.com/hin/wyv"
USER_AGENT = "VedaGraph/1.0 (research; h.mohanty@accenture.com)"
REQUEST_DELAY_SECONDS = 1.5

RAW_DIR = REPO / "data" / "raw" / "sacred_texts" / SNAPSHOT_ID / "wyv"
MANIFEST_PATH = RAW_DIR / "manifest.json"
CANONICAL_RELEASE = "yajurveda_vsm_v1"
CANONICAL_PASSAGES = REPO / "data" / "canonical" / CANONICAL_RELEASE / "passages.jsonl"
STAGE_PATH = REPO / "data" / "staged" / "yajurveda_translation_stage.json"


@dataclass(frozen=True)
class Page:
    """One logical page of the work and the URL it is served from."""

    page_id: str
    url: str
    book: int | None


def pages(books: list[int] | None = None) -> list[Page]:
    """The ordered page set: index, then the requested books, then errata."""
    wanted = books if books is not None else list(range(1, BOOK_COUNT + 1))
    out = [Page("index", f"{BASE}/index.htm", None)]
    out += [Page(f"book-{n:02d}", f"{BASE}/wyvbk{n:02d}.htm", n) for n in wanted]
    out.append(Page("errata", f"{BASE}/errata.htm", None))
    # The only rights statement the site links from the work: pinned as evidence, because
    # a licence read once and not snapshotted is an unverifiable claim.
    out.append(Page("copyrights", "https://sacred-texts.com/copyrights.htm", None))
    return out


def _fetch(url: str, tries: int = 4) -> tuple[bytes, int]:
    last: Exception | None = None
    for attempt in range(tries):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=120) as response:
                payload: bytes = response.read()
                status: int = int(response.status)
                return payload, status
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"failed after {tries} attempts: {url}") from last


def snapshot_page(page: Page) -> dict[str, object]:
    """Fetch one page, write ``<sha256>.html`` and its sidecar, return the manifest row."""
    payload, status = _fetch(page.url)
    digest = hashlib.sha256(payload).hexdigest()
    body_path = RAW_DIR / f"{digest}.html"
    sidecar_path = RAW_DIR / f"{digest}.metadata.json"
    if not body_path.exists():
        body_path.write_bytes(payload)
    sidecar = {
        "byte_size": len(payload),
        "content_type": "text/html",
        "filename": body_path.name,
        "http_status": status,
        "page_id": page.page_id,
        "request_headers": {"User-Agent": USER_AGENT},
        "retrieval_url": page.url,
        "retrieved_at": datetime.now(UTC).isoformat(),
        "schema_version": "1.0.0",
        "sha256": digest,
        "snapshot_id": SNAPSHOT_ID,
        "source_id": SOURCE_ID,
        "wyv_book": page.book,
    }
    sidecar_path.write_text(
        json.dumps(sidecar, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return {
        "byte_size": len(payload),
        "http_status": status,
        "page_id": page.page_id,
        "retrieval_url": page.url,
        "sha256": digest,
        "wyv_book": page.book,
    }


def read_manifest() -> dict[str, object]:
    if not MANIFEST_PATH.exists():
        return {}
    loaded: dict[str, object] = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return loaded


def write_manifest(rows: list[dict[str, object]]) -> None:
    """Merge new rows over any existing manifest, keyed by page id, and write it back."""
    existing = read_manifest()
    prior = existing.get("pages")
    merged: dict[str, dict[str, object]] = {}
    if isinstance(prior, list):
        for row in prior:
            if isinstance(row, dict):
                merged[str(row.get("page_id"))] = row
    for row in rows:
        merged[str(row["page_id"])] = row
    ordered = sorted(merged.values(), key=lambda row: str(row["page_id"]))
    aggregate = hashlib.sha256(
        "".join(f"{row['page_id']}:{row['sha256']}\n" for row in ordered).encode("utf-8")
    ).hexdigest()
    manifest = {
        "aggregate_sha256": aggregate,
        "base_url": BASE,
        "page_count": len(ordered),
        "pages": ordered,
        "schema_version": "1.0.0",
        "snapshot_id": SNAPSHOT_ID,
        "source_id": SOURCE_ID,
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def stage() -> int:
    """Align the pinned snapshots and write the staged translation payload."""
    sys.path.insert(0, str(REPO / "src"))
    from vedagraph.ingest.adapters.griffith_yajurveda import (
        CanonicalSpine,
        GriffithYajurvedaAdapter,
        build_stage,
    )

    spine = CanonicalSpine.from_passages(CANONICAL_PASSAGES)
    alignments = GriffithYajurvedaAdapter().align(RAW_DIR, spine)
    payload = build_stage(
        alignments,
        spine=spine,
        snapshot_id=SNAPSHOT_ID,
        canonical_release=CANONICAL_RELEASE,
    )
    STAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STAGE_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    summary = payload["alignment_summary"]
    assert isinstance(summary, dict)
    for key in sorted(summary):
        print(f"{key:>24}: {summary[key]}")
    print(f"\nwritten: {STAGE_PATH}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--books", type=int, nargs="*", default=None)
    parser.add_argument("--manifest-only", action="store_true")
    parser.add_argument("--stage", action="store_true", help="align snapshots, no network")
    args = parser.parse_args(argv)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if args.stage:
        return stage()
    if args.manifest_only:
        write_manifest([])
        print(f"manifest rewritten: {MANIFEST_PATH}")
        return 0

    rows: list[dict[str, object]] = []
    for index, page in enumerate(pages(args.books)):
        if index:
            time.sleep(REQUEST_DELAY_SECONDS)
        row = snapshot_page(page)
        rows.append(row)
        print(f"{row['page_id']:>8}  {row['http_status']}  {row['byte_size']:>8}  {row['sha256']}")
    write_manifest(rows)
    print(f"\n{len(rows)} pages snapshotted into {RAW_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
