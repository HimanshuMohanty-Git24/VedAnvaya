"""Stage 1: align the treebank to canonical keys and cache the alignment.

Writes the alignment plus an integrity check into the scratchpad. The integrity check
is monotonicity: within one hymn, treebank sentences are ordered, so the verse numbers
they align to must not go backwards. A backwards jump is an alignment defect, and it is
the only cheap independent test available for an alignment produced by text similarity.
"""
from __future__ import annotations

import collections
import json
import os
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from lib_align import HYMN_PREFIX, align, parse_conllu, skeleton  # noqa: E402

from dotenv import load_dotenv  # noqa: E402

load_dotenv("D:/VedaGraph/.env")
from neo4j import GraphDatabase  # noqa: E402

SCRATCH = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
OUT = SCRATCH / "stage1_alignment.json"


def verse_number(key: str) -> int:
    match = re.search(r":V(\d+)$", key)
    return int(match.group(1)) if match else -1


def main() -> None:
    sentences = []
    for split in ("train", "dev", "test"):
        for sentence in parse_conllu(SCRATCH / f"sa_vedic-ud-{split}.conllu"):
            sentences.append((split, sentence))

    driver = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
    )
    texts: dict[str, list[str]] = collections.defaultdict(list)
    with driver.session(database=os.environ.get("NEO4J_DATABASE", "neo4j")) as session:
        for record in session.run(
            "MATCH (m:Mantra)-[:HAS_TEXT_VERSION]->(t:TextVersion) "
            "RETURN m.canonical_key AS k, t.text_nfc AS txt"
        ):
            texts[record["k"]].append(record["txt"])
    driver.close()

    longest = {key: max(values, key=len) for key, values in texts.items()}
    by_hymn: dict[str, dict[str, str]] = collections.defaultdict(dict)
    for key, text in longest.items():
        by_hymn[key.rsplit(":V", 1)[0] + ":"][key] = skeleton(text)

    records = []
    status_counts: collections.Counter = collections.Counter()
    for split, sentence in sentences:
        if sentence.citation_text not in HYMN_PREFIX:
            continue
        prefix = HYMN_PREFIX[sentence.citation_text](sentence.citation_chapter)
        if prefix is None:
            status_counts[f"{sentence.citation_text}:BAD_CITATION"] += 1
            continue
        candidates = by_hymn.get(prefix, {})
        if not candidates:
            status_counts[f"{sentence.citation_text}:HYMN_NOT_IN_CORPUS"] += 1
            continue
        result = align(sentence, candidates)
        status_counts[f"{sentence.citation_text}:{result['status']}"] += 1
        records.append(
            {
                "split": split,
                "sent_id": sentence.sent_id,
                "citation_text": sentence.citation_text,
                "citation_chapter": sentence.citation_chapter,
                "layer": sentence.layer,
                "annotators": sentence.annotators,
                "hymn_prefix": prefix,
                "canonical_key": result["key"],
                "best_key": result.get("best_key"),
                "align_status": result["status"],
                "align_score": result["score"],
                "align_runner_up": result["runner_up"],
                "forms": sentence.forms,
                "lemmas": sentence.lemmas,
                "upos": sentence.upos,
                "feats": sentence.feats,
            }
        )

    # Monotonicity: within a hymn, aligned verse numbers must not go backwards.
    violations = 0
    checked = 0
    by_hymn_seq: dict[str, list[tuple[str, int]]] = collections.defaultdict(list)
    for record in records:
        if record["align_status"] != "ALIGNED":
            continue
        by_hymn_seq[record["hymn_prefix"]].append(
            (record["sent_id"], verse_number(record["canonical_key"]))
        )
    quarantined: set[str] = set()
    for hymn, seq in by_hymn_seq.items():
        seq.sort(key=lambda pair: (int(pair[0].split("_")[0]), int(pair[0].split("_")[1])))
        for earlier, later in zip(seq, seq[1:]):
            checked += 1
            if later[1] < earlier[1]:
                violations += 1
                quarantined.add(earlier[0])
                quarantined.add(later[0])
    # A sentence on either side of a backwards jump is quarantined: one of the two is
    # misaddressed and the evidence does not say which, so neither is used for scoring.
    for record in records:
        if record["sent_id"] in quarantined:
            record["align_status"] = "QUARANTINED_NON_MONOTONIC"
            record["canonical_key"] = None

    OUT.write_text(
        json.dumps(
            {
                "status_counts": dict(status_counts),
                "monotonicity": {
                    "adjacent_pairs_checked": checked,
                    "backwards_jumps": violations,
                    "violation_rate": round(violations / checked, 5) if checked else None,
                    "quarantined_sentences": len(quarantined),
                },
                "records": records,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"status_counts": dict(status_counts)}, ensure_ascii=False, indent=2))
    print("monotonicity:", checked, "pairs,", violations, "backwards jumps")
    aligned = [r for r in records if r["align_status"] == "ALIGNED"]
    print("aligned sentences:", len(aligned))
    print("distinct mantras reached:", len({r["canonical_key"] for r in aligned}))
    per_veda: dict[str, set[str]] = collections.defaultdict(set)
    for record in aligned:
        per_veda[record["canonical_key"].split(":")[1]].add(record["canonical_key"])
    print("distinct mantras by veda:", {k: len(v) for k, v in sorted(per_veda.items())})
    print("quarantined sentences:", len(quarantined))


if __name__ == "__main__":
    main()
