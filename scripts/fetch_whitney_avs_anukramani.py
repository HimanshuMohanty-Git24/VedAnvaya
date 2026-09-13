"""Pin Whitney & Lanman's printed Bṛhatsarvānukramaṇī brackets from en.wikisource.

What the source is
------------------
Whitney, W. D. & C. R. Lanman, *Atharva-Veda Saṁhitā*, Harvard Oriental Series 7-8,
Cambridge MA 1905, transcribed on English Wikisource under ProofreadPage.  At the head of
every translated hymn Whitney prints, in italic brackets, an excerpt of the Atharvaveda's
**own** index -- the Bṛhatsarvānukramaṇī -- in the shape::

    [Atharvan.—vācaspatyam. caturṛcam. ānuṣṭubham: 4. 4-p. virāḍ urobṛhatī.]
     ^rishi     ^devatā       ^verses    ^default metre  ^per-verse metre exception

The recension is Śaunaka and the numbering is the Berlin/Roth-Whitney spine -- the same
spine as ``VG:WORK:AV:SAU``.  In particular Whitney keeps kāṇḍa 12 at **5** hymns rather
than splitting the paryāya-sūktas, exactly as our corpus does; the "numbering does not join
in books 7-13" objection in ``ATHARVAVEDA_SOURCE_RESEARCH.md`` is an objection to
sa.wikisource, not to Whitney.

What the source does and does not state
---------------------------------------
* It states ṛṣi, devatā and metre **at hymn scope**, not per verse.  The only per-verse
  statements in the bracket are the metre *exceptions* after the colon.  Nothing here is a
  per-mantra ascription of a ṛṣi or a devatā, and the builder must not pretend otherwise.
* The prose books (xv, xvi) and the paryāya hymns carry a bracket with **metre only** -- no
  ṛṣi, no devatā.  That is a property of the tradition, not a transcription defect, and the
  gap must be left as a gap.
* **Kāṇḍa 20 is absent at source.**  Whitney deliberately excluded it as "in the main a
  pure mass of excerpts from the Rigveda", so no amount of fetching reaches its 143 hymns.

Why the ``Page:`` namespace and not mainspace
---------------------------------------------
Mainspace holds only 448 of the 588 hymn wrappers for books i-xix (kāṇḍa 7 has 5 of 118,
and kāṇḍas 15 and 16 have none).  The ``Page:`` namespace behind the same two Index files
is complete and gapless -- ``Atharva-Veda samhita.djvu`` pages 1-648 and
``Atharva-Veda samhita volume 2.djvu`` pages 1-606, verified by ``list=allpages`` -- and it
is where the wrappers transclude from.  So this script harvests the scan pages.

The alignment gate this buys us
-------------------------------
The bracket states the hymn's verse count as a Sanskrit numeral word (``caturṛcam`` = 4,
``daçakam`` = 10, ``ṣaṭ`` = 6 ...).  That is a **free, source-stated check** on the join:
the builder refuses any hymn whose stated count disagrees with our own mantra count under
that hymn key, so a numbering slip is caught before it becomes several thousand wrong
edges.  This script only pins the pages; the gate itself lives in
``scripts/build_atharvaveda_anukramani.py``.

Fetch shape
-----------
1,254 scan pages are pulled through ``action=query&prop=revisions`` in batches of 50 with
``rvprop=ids|timestamp|content``, which pins an immutable ``revid`` per page in the same
response as the wikitext.  That is 26 requests rather than 1,254, and every one of them goes
through ``PoliteFetcher`` at ``VEDAGRAPH_REQUESTS_PER_SECOND`` (1.0 by default), lands as a
content-addressed snapshot under ``data/raw/wikisource_whitney_avs/``, and is reused on a
rerun -- so an interrupted harvest resumes instead of restarting.

Usage
-----
    .venv/Scripts/python.exe scripts/fetch_whitney_avs_anukramani.py
    .venv/Scripts/python.exe scripts/fetch_whitney_avs_anukramani.py --volume 2
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from urllib.parse import urlencode

import orjson

from vedagraph.config import get_settings
from vedagraph.ingest.fetcher import PoliteFetcher
from vedagraph.ingest.fetcher.http import SnapshotResult

#: Registered source id (data/registry/sources.yaml). The Anukramaṇī brackets are a further
#: ARTIFACT of the same Wikisource transcription that already supplies the translation, so
#: no new source is minted.
SOURCE_ID = "WIKISOURCE_WHITNEY_AV"
#: Local raw-snapshot namespace, kept separate from the source id so these Page:-namespace
#: scans do not mix with any mainspace harvest of the same source.
SNAPSHOT_SOURCE_ID = "WIKISOURCE_WHITNEY_AVS"
SOURCE_ARTIFACT_ID = "WIKISOURCE_WHITNEY_AV.AVS.BRHATSARVANUKRAMANI.PAGENS"
API = "https://en.wikisource.org/w/api.php"

#: DjVu page counts verified live with list=allpages over ns=104: both ranges are
#: contiguous with zero gaps.
VOLUMES: tuple[tuple[int, str, int], ...] = (
    (1, "Atharva-Veda samhita.djvu", 648),
    (2, "Atharva-Veda samhita volume 2.djvu", 606),
)
#: MediaWiki caps prop=revisions multi-title content requests at 50 pages for anonymous
#: clients; fetch_wikisource_rigveda.py already batches revision queries at the same size.
BATCH = 50
MANIFEST = Path("data/raw/wikisource_whitney_avs/anukramani_page_manifest.jsonl")


def _content_url(titles: list[str]) -> str:
    query = urlencode(
        {
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "prop": "revisions",
            "rvprop": "ids|timestamp|content",
            "rvslots": "main",
            "titles": "|".join(titles),
        }
    )
    return f"{API}?{query}"


def _entry(volume: int, page: int, revid: int | None, result: SnapshotResult) -> dict[str, object]:
    """One manifest row per scan page, carrying the page-level citable locator."""
    _, djvu, _ = VOLUMES[volume - 1]
    return {
        "source_id": SOURCE_ID,
        "source_artifact_id": SOURCE_ARTIFACT_ID,
        "role": "anukramani_page_scan",
        "volume": volume,
        "djvu": djvu,
        "page": page,
        "page_title": f"Page:{djvu}/{page}",
        "page_url": f"https://en.wikisource.org/wiki/Page:{djvu.replace(' ', '_')}/{page}",
        "revid": revid,
        "snapshot_path": result.content_path.as_posix(),
        "snapshot_id": result.metadata.snapshot_id,
        "snapshot_sha256": result.metadata.sha256,
        "batch_retrieval_url": str(result.metadata.retrieval_url),
        "parser_version": "wikisource-whitney-anukramani-v1",
    }


async def _fetch_volume(fetcher: PoliteFetcher, volume: int) -> list[dict[str, object]]:
    _, djvu, last_page = VOLUMES[volume - 1]
    entries: list[dict[str, object]] = []
    for offset in range(1, last_page + 1, BATCH):
        pages = list(range(offset, min(offset + BATCH, last_page + 1)))
        titles = [f"Page:{djvu}/{page}" for page in pages]
        result = await fetcher.fetch(SNAPSHOT_SOURCE_ID, _content_url(titles))
        payload = orjson.loads(result.content_path.read_bytes())
        returned = {item["title"]: item for item in payload.get("query", {}).get("pages", []) or []}
        missing = [title for title in titles if title not in returned]
        if missing:
            raise RuntimeError(f"API omitted {len(missing)} titles, first={missing[0]}")
        for page, title in zip(pages, titles, strict=True):
            revisions = returned[title].get("revisions") or []
            revid = revisions[0].get("revid") if revisions else None
            entries.append(_entry(volume, page, revid, result))
        print(
            f"vol {volume} pages {pages[0]}-{pages[-1]}: "
            f"{'cached' if result.reused else 'fetched'} ({len(pages)} scans)",
            flush=True,
        )
    return entries


async def _main(volumes: list[int]) -> None:
    fetcher = PoliteFetcher(get_settings())
    entries: list[dict[str, object]] = []
    for volume in volumes:
        entries.extend(await _fetch_volume(fetcher, volume))

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if MANIFEST.exists():
        for line in MANIFEST.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                existing[(row["volume"], row["page"])] = row
    for entry in entries:
        existing[(entry["volume"], entry["page"])] = entry
    with MANIFEST.open("w", encoding="utf-8", newline="\n") as handle:
        for key in sorted(existing):
            handle.write(json.dumps(existing[key], ensure_ascii=False, sort_keys=True) + "\n")
    print(f"manifest: {len(existing)} scan pages -> {MANIFEST}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--volume",
        type=int,
        choices=[1, 2],
        action="append",
        help="restrict to one HOS volume; repeatable. Default: both.",
    )
    args = parser.parse_args()
    asyncio.run(_main(sorted(set(args.volume or [1, 2]))))


if __name__ == "__main__":
    main()
