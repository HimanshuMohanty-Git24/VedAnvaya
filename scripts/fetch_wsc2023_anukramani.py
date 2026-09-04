"""Fetch the ten commit-pinned WSC2023 Rigvedic Anukramaṇī data files.

Only ``Anukramani/Mandala_*.txt`` is retrieved.  The repository's ``dcs_w2v.vec``
word vectors and the linked classifier checkpoints are deliberately never fetched:
model output is not traditional metadata.

Snapshots are content-addressed and gitignored.  The emitted JSON carries only the
artifact metadata needed to update the version-controlled registry.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import orjson

from vedagraph.config import get_settings
from vedagraph.ingest.fetcher import PoliteFetcher

COMMIT = "05b5987d6d8d6ec7228926eb68d6a21117c9b1f2"
OUTPUT = Path("data/derived/wsc2023_anukramani_artifacts.json")


async def _fetch() -> list[dict[str, object]]:
    fetcher = PoliteFetcher(get_settings())
    artifacts: list[dict[str, object]] = []
    for mandala in range(1, 11):
        filename = f"Mandala_{mandala}.txt"
        url = f"https://raw.githubusercontent.com/mahesh-ak/WSC2023/{COMMIT}/Anukramani/{filename}"
        result = await fetcher.fetch("WSC2023", url)
        artifacts.append(
            {
                "mandala": mandala,
                "artifact_id": f"WSC2023.RV.ANUKRAMANI.M{mandala:02d}",
                "filename": filename,
                "repository_path": f"Anukramani/{filename}",
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
