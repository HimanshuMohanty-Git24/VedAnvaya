"""Acquire the BSB/MDZ scan of Roth & Whitney 1856 and pin one manifest row per leaf.

Why the leaf manifest is a separate committed file
==================================================

``data/raw/**`` is gitignored, and the scan is ~270 MB of JPEG, so the images themselves
cannot be the provenance record. :class:`~vedagraph.models.SourceArtifact` carries a
single ``checksum_sha256``, which is the right shape for a one-file artifact and the
wrong shape for a 478-leaf one: a single digest over the whole set proves the set is
unchanged but cannot say *which* leaf a transcription came from.

So the artifact row pins the aggregate digest and this script writes the per-leaf rows to
``data/source_registry/atharvaveda_bsb_leaf_manifest.jsonl``, which IS tracked. A
transcription record cites ``mdz_image_id``; that id resolves here to a sha256, a byte
size, a IIIF canvas and a retrieval URL, so any reader can re-fetch the exact leaf and
verify it. Without this file, "page 287" in a transcription record would be an
unverifiable claim.

The aggregate digest is computed over ``(mdz_image_id, sha256)`` pairs in canvas order,
so it changes if any leaf changes, if a leaf is missing, or if leaves are reordered.

Usage::

    python scripts/fetch_atharvaveda_bsb_scan.py             # fetch missing, write manifest
    python scripts/fetch_atharvaveda_bsb_scan.py --manifest-only
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

BSB_ID = "bsb10219750"
SOURCE_ID = "BSB_MDZ"
SNAPSHOT_ID = "2026-09-07"
# The volume has 478 IIIF canvases. Front matter occupies n1-n14, so printed page P is
# leaf n(P+14); this offset is verified in the leaf manifest rather than assumed by any
# consumer, because a transcription that cites the wrong leaf is unfalsifiable.
CANVAS_COUNT = 478
# 4000px, not 2000. MEASURED, and the first pass got this wrong in a way that produced a
# false conclusion. At width 2000 the Vedic accent marks of this fount sit on aksara
# BOUNDARIES and cannot be assigned to a specific aksara without guessing, so readers
# correctly refused to record them under RIGHTS-13 -- and the resulting corpus-wide
# absence of accent read as a transcription-capability failure when it was an
# ACQUISITION-RESOLUTION failure. At width 4000 the same marks are unambiguously
# attached to their aksara. The IIIF 'full' size is only 2025px, so the width must be
# requested explicitly; 4000 is a real derivative, not an upscale.
IMAGE_WIDTH = 4000
USER_AGENT = "VedaGraph/1.0 (canonical corpus research; h.mohanty@accenture.com)"

RAW_DIR = REPO / "data" / "raw" / "bsb_mdz" / SNAPSHOT_ID / BSB_ID
MANIFEST_PATH = REPO / "data" / "source_registry" / "atharvaveda_bsb_leaf_manifest.jsonl"


def image_url(canvas: int) -> str:
    return (
        f"https://api.digitale-sammlungen.de/iiif/image/v2/{BSB_ID}_{canvas:05d}"
        f"/full/{IMAGE_WIDTH},/0/default.jpg"
    )


def canvas_url(canvas: int) -> str:
    return f"https://api.digitale-sammlungen.de/iiif/presentation/v2/{BSB_ID}/canvas/{canvas}"


def _fetch(url: str, tries: int = 5) -> bytes:
    last: Exception | None = None
    for attempt in range(tries):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=120) as response:
                payload: bytes = response.read()
                return payload
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"failed after {tries} attempts: {url}") from last


def acquire() -> tuple[int, int]:
    """Fetch every missing leaf. Returns ``(fetched, reused)``."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    fetched = reused = 0
    for canvas in range(1, CANVAS_COUNT + 1):
        image_id = f"{BSB_ID}_{canvas:05d}"
        jpg = RAW_DIR / f"{image_id}.jpg"
        sidecar = RAW_DIR / f"{image_id}.metadata.json"
        if jpg.exists() and sidecar.exists() and jpg.stat().st_size > 20_000:
            reused += 1
            continue
        data = _fetch(image_url(canvas))
        jpg.write_bytes(data)
        sidecar.write_text(
            json.dumps(
                {
                    "schema_version": "1.0.0",
                    "source_id": SOURCE_ID,
                    "snapshot_id": SNAPSHOT_ID,
                    "bsb_id": BSB_ID,
                    "mdz_image_id": image_id,
                    "canvas_index": canvas,
                    "iiif_canvas": canvas_url(canvas),
                    "retrieval_url": image_url(canvas),
                    "iiif_region": "full",
                    "iiif_size": f"{IMAGE_WIDTH},",
                    "content_type": "image/jpeg",
                    "http_status": 200,
                    "filename": jpg.name,
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "byte_size": len(data),
                    "retrieved_at": datetime.now(UTC).isoformat(),
                    "request_headers": {"User-Agent": USER_AGENT},
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        fetched += 1
        if fetched % 25 == 0:
            print(f"fetched {fetched} (reused {reused}) latest={image_id}", flush=True)
    return fetched, reused


def write_manifest() -> tuple[int, str]:
    """Write the tracked per-leaf manifest. Returns ``(rows, aggregate_sha256)``."""
    rows: list[dict[str, object]] = []
    for canvas in range(1, CANVAS_COUNT + 1):
        image_id = f"{BSB_ID}_{canvas:05d}"
        jpg = RAW_DIR / f"{image_id}.jpg"
        if not jpg.exists():
            raise RuntimeError(
                f"leaf {image_id} is absent from {RAW_DIR}. The manifest must describe the "
                "whole volume or it cannot be an integrity record; run the fetch first."
            )
        payload = jpg.read_bytes()
        rows.append(
            {
                "mdz_image_id": image_id,
                "canvas_index": canvas,
                "printed_page": canvas - 14,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "byte_size": len(payload),
                "iiif_canvas": canvas_url(canvas),
                "retrieval_url": image_url(canvas),
                "source_id": SOURCE_ID,
                "snapshot_id": SNAPSHOT_ID,
                "bsb_id": BSB_ID,
            }
        )

    aggregate = hashlib.sha256()
    for row in rows:
        aggregate.update(f"{row['mdz_image_id']}:{row['sha256']}\n".encode())

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST_PATH.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True))
            handle.write("\n")
    return len(rows), aggregate.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest-only",
        action="store_true",
        help="skip acquisition and rewrite the leaf manifest from what is already on disk",
    )
    args = parser.parse_args()

    if not args.manifest_only:
        fetched, reused = acquire()
        print(f"leaves fetched={fetched} reused={reused} total={fetched + reused}")

    rows, aggregate = write_manifest()
    print(f"leaf manifest rows={rows} -> {MANIFEST_PATH}")
    print(f"aggregate_sha256={aggregate}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
