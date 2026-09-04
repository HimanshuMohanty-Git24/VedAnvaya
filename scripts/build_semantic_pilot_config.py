"""Write the committed, IDs-only pilot config for the semantic extraction pilot.

The config carries mantra identifiers and the stratum each was chosen for. It carries no
Sanskrit and no translation text: it is a *selection*, and a selection does not need to
restate the corpus it selects from. Anyone with the pinned build can rebuild every packet
from these ids.

Deterministic: rerunning this against the same corpus rewrites the same file.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import yaml

from vedagraph.semantic.evaluate import UNANNOTATED
from vedagraph.semantic.packet import load_packet_sources
from vedagraph.semantic.pilot import (
    PILOT_CONFIG_VERSION,
    SELECTION_RULE_VERSION,
    STRATA,
    gold_subset,
    select_pilot,
)

CORPUS_DIR = Path("data/canonical/rigveda_full_v1")
KNOWLEDGE_DIR = Path("data/knowledge/rigveda_deterministic_v1")
LEXICAL_DIR = Path("data/knowledge/rigveda_lexical_v1")
OUTPUT = Path("data/builds/rigveda_semantic_pilot_v1.yaml")
GOLD_WORKSHEET = Path("data/gold/rigveda_semantic_gold_v1.jsonl")


def ambiguous_passage_keys(lexical_dir: Path) -> frozenset[str]:
    """Mantras where the lexical layer deliberately declined to resolve a token."""
    path = lexical_dir / "ambiguous_mentions.jsonl"
    if not path.exists():
        return frozenset()
    keys = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            keys.add(str(json.loads(line)["passage_key"]))
    return frozenset(keys)


def main() -> None:
    sources = load_packet_sources(
        corpus_dir=CORPUS_DIR, knowledge_dir=KNOWLEDGE_DIR, lexical_dir=LEXICAL_DIR
    )
    selection = select_pilot(sources, ambiguous_passage_keys=ambiguous_passage_keys(LEXICAL_DIR))
    gold = set(gold_subset(selection))

    document = {
        "config_version": PILOT_CONFIG_VERSION,
        "selection_rule_version": SELECTION_RULE_VERSION,
        "corpus_dataset_id": "rigveda_full_v1",
        "description": (
            "Mantra ids only. No Sanskrit or translation text is stored here; every "
            "evidence packet is rebuilt from the pinned corpus using these ids."
        ),
        "strata": [
            {
                "name": item.name,
                "quota": item.quota,
                "selected": selection.counts.get(item.name, 0),
                "reason": item.reason,
            }
            for item in STRATA
        ],
        "pilot_mantra_count": len(selection),
        "gold_mantra_count": len(gold),
        "mantras": [
            {
                "passage_key": key,
                "citation": sources.citations[key],
                "stratum": selection.reasons[key],
                "gold": key in gold,
            }
            for key in selection.passage_keys
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        yaml.safe_dump(document, allow_unicode=True, sort_keys=False, width=100), encoding="utf-8"
    )
    per_mandala = Counter(int(key.split(":")[3][1:]) for key in selection.passage_keys)
    print(f"wrote {OUTPUT} ({len(selection)} mantras, {len(gold)} gold)")
    for item in STRATA:
        print(f"  {item.name:22s} {selection.counts.get(item.name, 0):4d} / quota {item.quota}")
    print("  per Mandala:", dict(sorted(per_mandala.items())))
    written = write_gold_worksheet(selection, sources, gold)
    print(f"wrote {GOLD_WORKSHEET} ({written} rows, {written} still UNANNOTATED)")


def write_gold_worksheet(selection, sources, gold) -> int:  # type: ignore[no-untyped-def]
    """Emit one empty annotation row per gold mantra, without overwriting real work.

    The worksheet is committed because it is identifiers only. Rows keep whatever a
    human has already written; only missing rows are added. A row still marked
    UNANNOTATED is skipped by the evaluator rather than scored as "no relations here",
    which would manufacture a precision of zero out of an empty file.
    """
    existing: dict[str, str] = {}
    if GOLD_WORKSHEET.exists():
        for line in GOLD_WORKSHEET.read_text(encoding="utf-8").splitlines():
            if line.strip():
                existing[str(json.loads(line)["passage_key"])] = line
    GOLD_WORKSHEET.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for key in sorted(gold):
        if key in existing:
            lines.append(existing[key])
            continue
        lines.append(
            json.dumps(
                {
                    "passage_key": key,
                    "citation": sources.citations[key],
                    "annotator": UNANNOTATED,
                    "annotated_at": "1970-01-01T00:00:00Z",
                    "entities": [],
                    "relations": [],
                    "notes": "",
                    "schema_version": "1.0.0",
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    GOLD_WORKSHEET.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return len(lines)


if __name__ == "__main__":
    main()
