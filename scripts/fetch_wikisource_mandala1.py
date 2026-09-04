"""One-off retrieval: pin Wikisource Griffith snapshots for all 191 Mandala 1 Suktas.

Idempotent: ``PoliteFetcher`` caches by exact retrieval URL, so re-running only fetches
Suktas not already snapshotted (the 5 from the sample build are reused). Writes the
fetched (source_id, role, scope, snapshot, checksum, parser_version) entries as a YAML
fragment; ``scripts/build_rv_mandala_1_full_config.py`` assembles these into the full
build configuration. No corpus text is written here, only source-input pins.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from urllib.parse import quote

import yaml

from vedagraph.config import get_settings
from vedagraph.ingest.fetcher import PoliteFetcher
from vedagraph.ingest.fetcher.http import SnapshotResult

MANDALA = 1
OUTPUT = Path("data/derived/wikisource_mandala1_sources.yaml")


def _title(sukta: int) -> str:
    return f"The Hymns of the Rigveda/Book {MANDALA}/Hymn {sukta}"


def _parse_url(sukta: int) -> str:
    return (
        "https://en.wikisource.org/w/api.php?action=parse&format=json&formatversion=2"
        f"&prop=text%7Crevid%7Cdisplaytitle&page={quote(_title(sukta))}"
    )


def _revision_url(sukta: int) -> str:
    return (
        "https://en.wikisource.org/w/api.php?action=query&format=json&formatversion=2"
        f"&prop=revisions&rvprop=ids%7Ctimestamp&titles={quote(_title(sukta))}"
    )


def _entry(sukta: int, role: str, parser_version: str, result: SnapshotResult) -> dict[str, object]:
    return {
        "source_id": "WIKISOURCE_GRIFFITH_RV",
        "role": role,
        "scope": f"RV.{MANDALA}.{sukta}",
        "source_artifact_id": "GRIFFITH.RV.1896.WIKISOURCE",
        "snapshot_path": result.content_path.as_posix(),
        "snapshot_id": result.metadata.snapshot_id,
        "snapshot_sha256": result.metadata.sha256,
        "parser_version": parser_version,
    }


async def _fetch_all() -> list[dict[str, object]]:
    fetcher = PoliteFetcher(get_settings())
    entries: list[dict[str, object]] = []
    for sukta in range(1, 192):
        parsed = await fetcher.fetch("WIKISOURCE_GRIFFITH_RV", _parse_url(sukta))
        entries.append(_entry(sukta, "translation", "wikisource-griffith-v2", parsed))
        revision = await fetcher.fetch("WIKISOURCE_GRIFFITH_RV", _revision_url(sukta))
        entries.append(_entry(sukta, "translation_revision", "mediawiki-revision-v1", revision))
        print(
            f"RV {MANDALA}.{sukta}: parse={'cached' if parsed.reused else 'fetched'} "
            f"revision={'cached' if revision.reused else 'fetched'}",
            flush=True,
        )
    return entries


def main() -> None:
    entries = asyncio.run(_fetch_all())
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(yaml.safe_dump({"sources": entries}, sort_keys=False), encoding="utf-8")
    print(f"Wrote {len(entries)} source entries to {OUTPUT}")


if __name__ == "__main__":
    main()
