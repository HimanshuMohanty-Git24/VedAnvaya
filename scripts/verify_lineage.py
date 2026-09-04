"""Stratified lineage spot-check over any built VedaGraph corpus.

Traces, for a deterministic sample of mantras spread across every Mandala present:

  passage -> primary TextVersion   -> registered SourceArtifact -> raw snapshot -> checksum
  passage -> parallel TextVersion  -> registered SourceArtifact -> raw snapshot -> checksum
  passage -> Translation           -> Wikisource page/revision provenance (when present)

Prints PASS/FAIL per mantra; exits non-zero if any hop breaks. No corpus text is printed.
"""

from __future__ import annotations

import argparse
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

import orjson

from vedagraph.config.registry import load_source_artifacts
from vedagraph.models import SourceArtifact
from vedagraph.storage.manifest import file_sha256

Row = dict[str, Any]


def _read_jsonl(path: Path) -> list[Row]:
    return [orjson.loads(line) for line in path.read_bytes().splitlines() if line.strip()]


def _snapshot_matches(artifact: SourceArtifact | None) -> bool:
    if artifact is None or not artifact.checksum_sha256:
        return False
    snapshot = next(
        (
            path
            for path in Path("data/raw").glob(f"**/{artifact.checksum_sha256}.*")
            if not path.name.endswith(".metadata.json")
        ),
        None,
    )
    return snapshot is not None and file_sha256(snapshot) == artifact.checksum_sha256


def _sample(mantras: list[Row], per_mandala: int, seed: int) -> list[Row]:
    """Deterministic, spread-out sample: first, last, and random middles per Mandala."""
    by_mandala: dict[int, list[Row]] = defaultdict(list)
    for row in mantras:
        by_mandala[int(row["hierarchy"]["mandala"])].append(row)
    rng = random.Random(seed)
    chosen: list[Row] = []
    for mandala in sorted(by_mandala):
        ordered = sorted(
            by_mandala[mandala],
            key=lambda row: (int(row["hierarchy"]["sukta"]), int(row["hierarchy"]["mantra"])),
        )
        picked = [ordered[0], ordered[-1]]
        middle = [row for row in ordered if row not in picked]
        picked += rng.sample(middle, min(max(per_mandala - 2, 0), len(middle)))
        chosen.extend(
            sorted(picked, key=lambda row: (row["hierarchy"]["sukta"], row["hierarchy"]["mantra"]))
        )
    return chosen


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, default=Path("data/canonical/rigveda_full_v1"))
    parser.add_argument("--per-mandala", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20260904)
    args = parser.parse_args()

    passages = _read_jsonl(args.corpus / "passages.jsonl")
    artifacts = {item.artifact_id: item for item in load_source_artifacts()}
    texts_by_passage: dict[str, list[Row]] = defaultdict(list)
    for text in _read_jsonl(args.corpus / "text_versions.jsonl"):
        texts_by_passage[str(text["passage_id"])].append(text)
    translations_by_passage = {
        str(item["passage_id"]): item for item in _read_jsonl(args.corpus / "translations.jsonl")
    }
    checksum_cache: dict[str | None, bool] = {}

    failures = 0
    sample = _sample(
        [row for row in passages if row["entity_type"] == "MANTRA"], args.per_mandala, args.seed
    )
    for passage in sample:
        passage_id = str(passage["entity_id"])
        readings = texts_by_passage.get(passage_id, [])
        results: dict[str, str] = {}
        role_ok = True
        for role in ("PRIMARY_TEXT", "PARALLEL_TEXT"):
            reading = next((item for item in readings if item["text_role"] == role), None)
            artifact = artifacts.get(reading["source_artifact_id"]) if reading else None
            key = artifact.artifact_id if artifact else None
            if key not in checksum_cache:
                checksum_cache[key] = _snapshot_matches(artifact)
            good = reading is not None and artifact is not None and checksum_cache[key]
            role_ok &= good
            results[role] = "match" if good else "BROKEN"
        translation = translations_by_passage.get(passage_id)
        translation_ok = translation is None or (
            translation.get("source_page_title") is not None
            and translation.get("source_revision_id") is not None
        )
        passed = role_ok and translation_ok
        failures += not passed
        print(
            f"{'PASS' if passed else 'FAIL'} {passage['canonical_citation']}: "
            f"primary={results['PRIMARY_TEXT']} parallel={results['PARALLEL_TEXT']} "
            f"translation={'ok' if translation_ok else 'INCOMPLETE'}"
            f"{'' if translation is not None else ' (none)'}"
        )
    print(f"\n{len(sample)} mantras checked, {failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
