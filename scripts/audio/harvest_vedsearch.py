"""Harvest every VedSearch verse row once, so alignment can then run offline.

**Why harvest instead of querying during discovery.** Aligning ~20,000 verses needs the
source's text for every one of them, and the API returns ten rows per request. Doing that
inside the discovery step would mean 2,000 network calls every time the mapping is
re-derived, and a mapping that cannot be re-derived cheaply stops being checked. So the
network phase runs once into a derived file, and alignment is a pure function of that file
plus the graph -- fast, offline, and reproducible.

The output lands in ``data/derived/``, which is gitignored: it is a reproducible copy of
someone else's database and has no place in this repository. The *catalog* built from it is
what gets committed.

**Resume is per chapter.** A chapter already present in the output file is skipped unless
``--refresh`` is passed, so an interrupted run costs only the chapter it was in the middle
of. The Samavedic chapter count is discovered by walking upward until a chapter comes back
empty, because VedSearch's Samavedic chapters do not correspond to this corpus's four named
collections and the count is not documented anywhere.

Usage::

    python scripts/audio/harvest_vedsearch.py --veda YV          # 40 chapters, quick
    python scripts/audio/harvest_vedsearch.py                    # all four
    python scripts/audio/harvest_vedsearch.py --refresh --veda SV
"""

from __future__ import annotations

import argparse
import io
import json
import pathlib
import sys
import time
import urllib.error
import warnings
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "src"))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")

from vedagraph.product.audio.net import USER_AGENT  # noqa: E402
from vedagraph.product.audio.vedsearch import (  # noqa: E402
    CHAPTER_COUNTS,
    VedSearchClient,
    has_sanskrit_audio,
)

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_OUT = PROJECT_ROOT / "data" / "derived" / "vedsearch_harvest.json"

#: Upper bound on the Samavedic chapter walk. Generous, and only reached if the site grows;
#: the walk stops at the first empty chapter regardless.
_SV_CHAPTER_CEILING = 60


def load_existing(path: pathlib.Path) -> dict[str, Any]:
    if not path.exists():
        return {"vedas": {}}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"vedas": {}}
    if not isinstance(loaded, dict) or "vedas" not in loaded:
        return {"vedas": {}}
    return loaded


def save(path: pathlib.Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Written whole each time. The file is a few megabytes and an atomic replace is worth
    # more here than an append format that a killed process could leave half-written.
    temporary = path.with_suffix(".part")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def harvest_veda(
    client: VedSearchClient,
    veda: str,
    store: dict[str, Any],
    *,
    refresh: bool,
    pause: float,
    out: pathlib.Path,
    payload: dict[str, Any],
) -> None:
    chapters: dict[str, Any] = store.setdefault("chapters", {})
    declared = CHAPTER_COUNTS.get(veda)
    chapter = 1
    while True:
        if declared is not None and chapter > declared:
            break
        if veda == "SV" and chapter > _SV_CHAPTER_CEILING:
            break
        key = str(chapter)
        if key in chapters and not refresh:
            rows = chapters[key]
            print(f"  {veda} ch{chapter:<3} cached  verses={len(rows)}")
            chapter += 1
            continue
        try:
            rows = client.chapter_verses(veda, chapter)
        except (urllib.error.URLError, TimeoutError, ValueError) as error:
            print(f"  {veda} ch{chapter:<3} FAILED  {type(error).__name__}: {error}")
            # A failed chapter is left absent rather than recorded empty, so a later run
            # retries it instead of treating the gap as established.
            chapter += 1
            time.sleep(pause * 3)
            continue
        if not rows:
            if declared is None:
                print(f"  {veda} ch{chapter:<3} empty -> {chapter - 1} chapters total")
                break
            print(f"  {veda} ch{chapter:<3} empty")
            chapter += 1
            continue
        with_audio = sum(1 for row in rows if has_sanskrit_audio(row))
        chapters[key] = rows
        print(f"  {veda} ch{chapter:<3} verses={len(rows):<5} sanskrit_audio={with_audio}")
        save(out, payload)
        chapter += 1
        time.sleep(pause)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--veda", choices=["RV", "SV", "YV", "AV"], action="append", default=[])
    parser.add_argument("--refresh", action="store_true", help="re-fetch cached chapters")
    parser.add_argument("--pause", type=float, default=0.35, help="seconds between chapters")
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    vedas = args.veda or ["RV", "AV", "YV", "SV"]
    client = VedSearchClient(user_agent=USER_AGENT)
    payload = load_existing(args.out)
    started = time.time()

    for veda in vedas:
        print(f"== {veda} ==")
        store = payload["vedas"].setdefault(veda, {})
        harvest_veda(
            client,
            veda,
            store,
            refresh=args.refresh,
            pause=args.pause,
            out=args.out,
            payload=payload,
        )

    save(args.out, payload)
    print("\nSummary:")
    grand = grand_audio = 0
    for veda in sorted(payload["vedas"]):
        chapters = payload["vedas"][veda].get("chapters", {})
        verses = sum(len(rows) for rows in chapters.values())
        audio = sum(1 for rows in chapters.values() for row in rows if has_sanskrit_audio(row))
        grand += verses
        grand_audio += audio
        print(f"  {veda}: {len(chapters)} chapters, {verses} verses, {audio} with Sanskrit audio")
    print(f"  TOTAL: {grand} verses, {grand_audio} with Sanskrit audio")
    print(f"  elapsed {time.time() - started:.0f}s -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
