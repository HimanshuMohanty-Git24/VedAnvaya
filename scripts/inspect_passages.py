"""Print canonical identity, provenance, and alignment for named passages.

Structural inspection only: Sanskrit and English text are shown truncated so a report
built from this output never reproduces bulk source text.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any

import orjson


def _read(root: Path, name: str) -> list[dict[str, Any]]:
    return [orjson.loads(line) for line in (root / name).read_bytes().splitlines() if line]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, default=Path("data/canonical/rigveda_full_v1"))
    parser.add_argument("--citation", action="append", default=[], help="e.g. 'RV 10.129.1'")
    parser.add_argument("--sukta", action="append", default=[], help="e.g. '10.90' (all mantras)")
    parser.add_argument("--chars", type=int, default=60)
    args = parser.parse_args()

    passages = _read(args.corpus, "passages.jsonl")
    texts: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in _read(args.corpus, "text_versions.jsonl"):
        texts[str(row["passage_id"])].append(row)
    translations: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in _read(args.corpus, "translations.jsonl"):
        translations[str(row["passage_id"])].append(row)

    wanted = set(args.citation)
    prefixes = tuple(f"RV {value}." for value in args.sukta)
    selected = [
        row
        for row in passages
        if row["canonical_citation"] in wanted
        or (prefixes and str(row["canonical_citation"]).startswith(prefixes))
    ]
    if not selected:
        raise SystemExit("no matching passages")

    for passage in selected:
        identifier = str(passage["entity_id"])
        print(f"\n{passage['canonical_citation']}  [{passage['entity_type']}]")
        print(f"  key    {passage['canonical_key']}")
        print(f"  urn    {passage['canonical_urn']}")
        print(f"  uuid   {identifier}")
        print(f"  parent {passage.get('parent_key')}")
        for text in sorted(texts[identifier], key=lambda row: str(row["text_role"])):
            body = str(text["text_original"])
            print(
                f"  {text['text_role']:<14} {text['text_version_id']} "
                f"accented={text['accented']} locator={text['source_locator']}"
            )
            print(f"    {body[: args.chars]}{'…' if len(body) > args.chars else ''}")
        for item in translations[identifier]:
            body = str(item["text"])
            print(
                f"  TRANSLATION    {item['alignment']} rev={item['source_revision_id']} "
                f"@{item['source_revision_timestamp']} page={item['source_page_title']!r}"
            )
            print(f"    {body[: args.chars]}{'…' if len(body) > args.chars else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
