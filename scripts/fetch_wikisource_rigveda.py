"""Pin Griffith Wikisource parse snapshots and exact revision metadata by Mandala.

Run one Mandala at a time.  Parse responses are content-addressed snapshots; revision
queries use the returned immutable revision IDs in batches of at most 50.
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from urllib.parse import quote

import orjson
import yaml

from vedagraph.config import get_settings
from vedagraph.editions import griffith_page
from vedagraph.ingest.adapters.gretil import GRETILAdapter
from vedagraph.ingest.fetcher import PoliteFetcher
from vedagraph.ingest.fetcher.http import SnapshotResult

GRETIL = Path(
    "data/raw/gretil/2026-09-04/"
    "14197d9c1dcced64900ef971d9f4dc5b46aa8750780f5599453c9739d6a29edd.xml"
)


def _title(mandala: int, sukta: int) -> str:
    """Griffith's page for a canonical Sukta; his hymn order is not always Aufrecht's."""
    return f"The Hymns of the Rigveda/Book {mandala}/Hymn {griffith_page(mandala, sukta)}"


def _parse_url(mandala: int, sukta: int) -> str:
    return (
        "https://en.wikisource.org/w/api.php?action=parse&format=json&formatversion=2"
        f"&prop=text%7Crevid%7Cdisplaytitle&page={quote(_title(mandala, sukta))}"
    )


def _revision_url(revision_ids: list[int]) -> str:
    joined = "%7C".join(str(value) for value in revision_ids)
    return (
        "https://en.wikisource.org/w/api.php?action=query&format=json&formatversion=2"
        f"&prop=revisions&rvprop=ids%7Ctimestamp&revids={joined}"
    )


def _entry(
    mandala: int,
    sukta: int,
    role: str,
    parser_version: str,
    result: SnapshotResult,
) -> dict[str, object]:
    return {
        "source_id": "WIKISOURCE_GRIFFITH_RV",
        "role": role,
        "scope": f"RV.{mandala}.{sukta}",
        "source_artifact_id": "GRIFFITH.RV.1896.WIKISOURCE",
        "snapshot_path": result.content_path.as_posix(),
        "snapshot_id": result.metadata.snapshot_id,
        "snapshot_sha256": result.metadata.sha256,
        "parser_version": parser_version,
    }


def _sukta_count(mandala: int) -> int:
    records = GRETILAdapter().discover_suktas(
        GRETIL, snapshot_id="GRETIL:registered", mandala=mandala
    )
    if not records:
        raise ValueError(f"GRETIL contains no Mandala {mandala}")
    return max(record.sukta_number for record in records)


async def _fetch_mandala(mandala: int) -> list[dict[str, object]]:
    fetcher = PoliteFetcher(get_settings())
    parse_results: dict[int, SnapshotResult] = {}
    revision_ids: dict[int, int] = {}
    for sukta in range(1, _sukta_count(mandala) + 1):
        result = await fetcher.fetch("WIKISOURCE_GRIFFITH_RV", _parse_url(mandala, sukta))
        parse_results[sukta] = result
        payload = orjson.loads(result.content_path.read_bytes())
        revision_id = payload.get("parse", {}).get("revid")
        if isinstance(revision_id, int):
            revision_ids[sukta] = revision_id
        print(
            f"RV {mandala}.{sukta}: {'cached' if result.reused else 'fetched'} "
            f"revision={revision_id}",
            flush=True,
        )

    revision_results: dict[int, SnapshotResult] = {}
    ordered = list(revision_ids.items())
    for offset in range(0, len(ordered), 50):
        batch = ordered[offset : offset + 50]
        result = await fetcher.fetch(
            "WIKISOURCE_GRIFFITH_RV", _revision_url([revision for _, revision in batch])
        )
        for sukta, _ in batch:
            revision_results[sukta] = result
        print(
            f"RV {mandala}: pinned revision batch {offset // 50 + 1} ({len(batch)} pages)",
            flush=True,
        )

    entries: list[dict[str, object]] = []
    for sukta, result in sorted(parse_results.items()):
        entries.append(_entry(mandala, sukta, "translation", "wikisource-griffith-v2", result))
        revision = revision_results.get(sukta)
        if revision is not None:
            entries.append(
                _entry(
                    mandala,
                    sukta,
                    "translation_revision",
                    "mediawiki-revision-v1",
                    revision,
                )
            )
    return entries


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mandala", type=int, required=True, choices=range(2, 11))
    args = parser.parse_args()
    entries = asyncio.run(_fetch_mandala(args.mandala))
    output = Path(f"data/derived/wikisource_mandala{args.mandala}_sources.yaml")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(yaml.safe_dump({"sources": entries}, sort_keys=False), encoding="utf-8")
    print(f"Wrote {len(entries)} source entries to {output}")


if __name__ == "__main__":
    main()
