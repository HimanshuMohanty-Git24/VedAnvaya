"""Snapshot Sanskrit Wikisource Vajasaneyi Samhita adhyaya pages into data/raw.

Bounded and idempotent: every page goes through ``PoliteFetcher``, so an existing
snapshot with a matching sha256 is reused and never overwritten. Run with an explicit
list of adhyayas, or with no arguments for all forty.

    python scripts/fetch_yajurveda_wikisource.py            # all 40
    python scripts/fetch_yajurveda_wikisource.py 1 16 31 40  # a bounded sample
"""

from __future__ import annotations

import asyncio
import sys

from vedagraph.config import get_settings
from vedagraph.ingest.adapters.yajurveda_wikisource import YajurvedaWikisourceAdapter
from vedagraph.ingest.fetcher import PoliteFetcher

EXTRA_SCOPES = {
    # Traditional apparatus pages in the same wiki tree. Fetched as evidence, parsed
    # separately; the Sarvanukramani is continuous sutra prose and is NOT resolved to
    # per-mantra claims by machine.
    "RISHI_INDEX": "शुक्लयजुर्वेदः/ऋषिसूची",
    "SARVANUKRAMANI": "शुक्लयजुर्वेदः/सर्वानुक्रमणी",
    "ROOT_TOC": "शुक्लयजुर्वेदः",
    # Carries the printed edition's title page verbatim, which is how the underlying
    # edition was identified (Nirnaya Sagara Press, Bombay, Saka 1850 = 1929).
    "PREFACE": "शुक्लयजुर्वेदः/प्राक्कथनम्, विषयानुक्रमणिका च",
}


async def main(adhyayas: list[int], *, include_apparatus: bool = True) -> None:
    settings = get_settings()
    fetcher = PoliteFetcher(settings)
    adapter = YajurvedaWikisourceAdapter()
    for adhyaya in adhyayas:
        resource = (await adapter.discover(f"VSM.{adhyaya}"))[0]
        snapshot = await adapter.fetch(resource, fetcher)
        print(
            f"VSM {adhyaya:2d} {'reused ' if snapshot.reused else 'fetched'} "
            f"{snapshot.metadata.sha256[:16]} {snapshot.content_path}"
        )
    if not include_apparatus:
        return
    from vedagraph.ingest.adapters.yajurveda_wikisource import content_api_url

    for label, title in EXTRA_SCOPES.items():
        snapshot = await fetcher.fetch(adapter.source_id, content_api_url(title))
        print(
            f"{label:15s} {'reused ' if snapshot.reused else 'fetched'} "
            f"{snapshot.metadata.sha256[:16]} {snapshot.content_path}"
        )


if __name__ == "__main__":
    requested = [int(value) for value in sys.argv[1:]] or list(range(1, 41))
    asyncio.run(main(requested))
