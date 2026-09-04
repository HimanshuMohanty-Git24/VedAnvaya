"""Fetch the nine remaining commit-pinned VedaWeb Rigveda TEI books.

The snapshots are content-addressed and gitignored.  The emitted JSON contains only
artifact metadata safe to use when updating the version-controlled registry.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import orjson

from vedagraph.config import get_settings
from vedagraph.ingest.fetcher import PoliteFetcher

COMMIT = "d3eb8af7324338161520d2d35eae8f7e985a19a5"
OUTPUT = Path("data/derived/vedaweb_rigveda_artifacts.json")


async def _fetch() -> list[dict[str, object]]:
    fetcher = PoliteFetcher(get_settings())
    artifacts: list[dict[str, object]] = []
    for mandala in range(2, 11):
        filename = f"rv_book_{mandala:02d}.tei"
        url = (
            "https://raw.githubusercontent.com/VedaWebProject/vedaweb-data/"
            f"{COMMIT}/rigveda/TEI/{filename}"
        )
        result = await fetcher.fetch("VEDAWEB", url)
        artifacts.append(
            {
                "mandala": mandala,
                "filename": filename,
                "snapshot_path": result.content_path.as_posix(),
                "snapshot_id": result.metadata.snapshot_id,
                "sha256": result.metadata.sha256,
                "size": result.content_path.stat().st_size,
                "url": url,
            }
        )
        state = "cached" if result.reused else "fetched"
        print(f"Mandala {mandala}: {state} {result.content_path}", flush=True)
    return artifacts


def main() -> None:
    artifacts = asyncio.run(_fetch())
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(orjson.dumps(artifacts, option=orjson.OPT_INDENT_2) + b"\n")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
