"""Optionally keep local copies of catalogued audio, so playback works offline.

**Nothing is cached unless asked for.** The product's default playback path fetches a verse
from its source, decodes it and streams it, holding only a small in-memory window. That
needs no disk and no up-front download. This tool exists for the case where you want a
corpus available offline, and it requires an explicit ``--all``, ``--veda`` or
``--audio-id``: there is no mode in which running it with no arguments downloads 16,834
files.

**It decodes rather than downloads.** VedSearch serves a verse as base64 inside a JSON
document, so saving the response body would leave JSON on disk under an ``.mp3`` name and
every cached file would be silently unplayable. Records whose playback mode is
``PROXIED_STREAM`` therefore go through the source client, which decodes the payload and
verifies it is really MP3 before a byte is written.

**Bounded by default.** ``--max-total-mb`` caps the run and ``--max-file-mb`` caps one
file. The measured median verse is about 40 KB, so a whole Veda is a few hundred megabytes
rather than gigabytes -- but the cap is there so that a change upstream cannot turn this
into an unbounded download.

**Binaries stay out of Git.** Files land under ``data/audio/cache/``, which is gitignored.
The catalog that describes them is committed, and each cached record gains a SHA-256 so a
later ``--verify`` can tell a changed file from an unchanged one.

Usage::

    python scripts/audio/cache_audio.py --dry-run --veda YV
    python scripts/audio/cache_audio.py --veda RV --max-total-mb 800
    python scripts/audio/cache_audio.py --audio-id VEDSEARCH:YV:1.1.1
    python scripts/audio/cache_audio.py --verify
"""

from __future__ import annotations

import argparse
import hashlib
import io
import pathlib
import sys
import time
import warnings
from datetime import UTC, datetime

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")

from vedagraph.product.audio.catalog import (  # noqa: E402
    CACHE_RELATIVE_PATH,
    CATALOG_RELATIVE_PATH,
    AudioCatalog,
    write_catalog,
)
from vedagraph.product.audio.models import (  # noqa: E402
    AudioRecord,
    PlaybackMode,
)
from vedagraph.product.audio.net import USER_AGENT  # noqa: E402
from vedagraph.product.audio.vedsearch import VedSearchClient  # noqa: E402

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]

_CHUNK = 256 * 1024

#: MP3 magic: an ID3 tag, or a bare MPEG audio frame header.
_MP3_PREFIXES = (b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2", b"\xff\xfa")


def cache_name(record: AudioRecord) -> str:
    """A stable, filesystem-safe path derived from the audio id.

    Derived from the id rather than the URL's basename: two sources can both serve
    ``1.1.1`` and the second would otherwise overwrite the first.
    """
    safe = "".join(ch if ch.isalnum() or ch in "-._" else "_" for ch in record.audio_id)
    return f"{record.veda}/{safe[:120]}.mp3"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(_CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def looks_like_mp3(payload: bytes) -> bool:
    return payload.startswith(_MP3_PREFIXES)


def fetch_decoded(
    client: VedSearchClient, record: AudioRecord, *, max_file_bytes: int
) -> tuple[bytes | None, str]:
    """Decoded audio for one record, or ``(None, reason)``."""
    if not record.source_reference:
        return None, "record names no source reference"
    try:
        payload, _ = client.audio_bytes(record.veda, record.source_reference)
    except Exception as error:
        return None, f"{type(error).__name__}: {error}"
    if len(payload) > max_file_bytes:
        return None, f"{len(payload)} bytes exceeds the per-file cap"
    if not looks_like_mp3(payload):
        # The whole reason this tool decodes rather than downloads. Writing this would put
        # an unplayable file on disk under an .mp3 name.
        return None, f"decoded payload is not MP3 ({payload[:4]!r})"
    return payload, "cached"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="every eligible record")
    parser.add_argument("--veda", choices=["RV", "SV", "YV", "AV"], default=None)
    parser.add_argument("--audio-id", action="append", default=[])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verify", action="store_true", help="re-check checksums, fetch nothing")
    parser.add_argument("--limit", type=int, default=0, help="cap how many files are fetched")
    parser.add_argument("--max-file-mb", type=float, default=20.0)
    parser.add_argument("--max-total-mb", type=float, default=1200.0)
    parser.add_argument("--pause", type=float, default=0.2, help="seconds between fetches")
    parser.add_argument("--data-dir", type=pathlib.Path, default=PROJECT_ROOT / "data")
    args = parser.parse_args()

    catalog_path = args.data_dir / CATALOG_RELATIVE_PATH
    cache_root = args.data_dir / CACHE_RELATIVE_PATH
    catalog = AudioCatalog.load(catalog_path)
    records = list(catalog)
    if not records:
        print(f"No catalog at {catalog_path}. Run discovery first.")
        return 0

    if args.verify:
        checked = mismatched = missing = 0
        for record in records:
            if not record.local_cache_path or not record.checksum:
                continue
            checked += 1
            path = cache_root / record.local_cache_path
            if not path.is_file():
                missing += 1
                print(f"  MISSING {record.audio_id}")
            elif sha256_file(path) != record.checksum:
                mismatched += 1
                print(f"  CHANGED {record.audio_id}")
        print(f"\nverified {checked} cached record(s): {missing} missing, {mismatched} changed")
        return 1 if (missing or mismatched) else 0

    candidates = records
    if args.audio_id:
        wanted = set(args.audio_id)
        candidates = [r for r in candidates if r.audio_id in wanted]
    elif args.veda:
        candidates = [r for r in candidates if r.veda == args.veda]
    elif not args.all:
        parser.error("choose --all, --veda or --audio-id (or --verify)")

    eligible = [
        r
        for r in candidates
        if r.playback_mode is PlaybackMode.PROXIED_STREAM and r.source_reference
    ]
    already = [r for r in eligible if (cache_root / (r.local_cache_path or "x")).is_file()]
    todo = [r for r in eligible if r not in already]
    if args.limit:
        todo = todo[: args.limit]

    approx_mb = len(todo) * 0.045
    print(f"Catalog: {len(records)} records; {len(candidates)} selected")
    print(f"  eligible       : {len(eligible)}")
    print(f"  already cached : {len(already)}")
    print(f"  to fetch       : {len(todo)}  (~{approx_mb:.0f} MB at the measured median)")

    if not todo:
        print("\nNothing to fetch. Playback continues to stream from the source.")
        return 0
    if args.dry_run:
        for record in todo[:10]:
            print(f"  would cache {record.audio_id} -> {cache_name(record)}")
        if len(todo) > 10:
            print(f"  ... and {len(todo) - 10} more")
        print("\n--dry-run: nothing fetched, nothing written.")
        return 0

    cache_root.mkdir(parents=True, exist_ok=True)
    client = VedSearchClient(user_agent=USER_AGENT)
    budget = int(args.max_total_mb * 1024 * 1024)
    max_file = int(args.max_file_mb * 1024 * 1024)
    updates: dict[str, tuple[str, str]] = {}
    cached = failed = 0
    total = 0

    print(f"\nFetching {len(todo)} file(s) into {cache_root}")
    for index, record in enumerate(todo, start=1):
        payload, detail = fetch_decoded(client, record, max_file_bytes=max_file)
        if payload is None:
            failed += 1
            print(f"  SKIP {record.audio_id}: {detail}")
            time.sleep(args.pause)
            continue
        if len(payload) > budget:
            print("  run budget exhausted; stopping")
            break
        relative = cache_name(record)
        destination = cache_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        partial = destination.with_suffix(".part")
        partial.write_bytes(payload)
        partial.replace(destination)
        updates[record.audio_id] = (relative, sha256_bytes(payload))
        budget -= len(payload)
        total += len(payload)
        cached += 1
        if index % 50 == 0 or index == len(todo):
            print(f"  [{index}/{len(todo)}] {cached} cached, {total / 1024 / 1024:.1f} MB")
        time.sleep(args.pause)

    today = datetime.now(UTC).date().isoformat()
    rewritten = [
        record.model_copy(
            update={
                "local_cache_path": updates[record.audio_id][0],
                "checksum": updates[record.audio_id][1],
                "last_verified": today,
            }
        )
        if record.audio_id in updates
        else record
        for record in records
    ]
    write_catalog(catalog_path, rewritten)
    print(
        f"\ncached {cached} file(s), {total / 1024 / 1024:.1f} MB, {failed} skipped; "
        f"catalog updated"
    )
    print("Playback prefers the local copy where one exists and streams otherwise.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
