#!/usr/bin/env python3
"""Shared read-only helpers for the translation Gate B/C evidence packet.

Every function here reads. Nothing in this module writes to Neo4j, because the task that
produced it forbids canonical translation mutation: the packet exists so an owner can
decide, and a measurement that mutates its subject cannot be re-run to check itself.

The digest functions exist for one reason. This analysis has to prove at the end that it
changed nothing, and a node/relationship census alone cannot prove that -- a census is
unchanged by rewriting the text of every translation in place. So the attachment digest
hashes the (passage, translation, source, alignment) tuples themselves.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys
from typing import Any

REPO = pathlib.Path(__file__).resolve().parent.parent
STAGING = REPO / "data" / "staging" / "translation"
PACKET = STAGING / "gate_bc"

CORE_CORPUS_INVARIANT = {
    "RV": 10552,
    "SV": 1844,
    "YV": 1975,
    "AV": 5839,
}

# The single central policy. Imported, never re-declared, so a caller cannot soften it.
sys.path.insert(0, str(REPO / "scripts"))


def not_importable_confidences() -> frozenset[str]:
    """The campaign's central non-importable set, read from the validator that owns it."""
    from validate_staging_artifact import NOT_IMPORTABLE

    return frozenset(NOT_IMPORTABLE)


def driver():
    from neo4j import GraphDatabase

    return GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(
            os.environ.get("NEO4J_USER", "neo4j"),
            os.environ.get("NEO4J_PASSWORD", "vedagraph_dev"),
        ),
    )


def session(drv):
    return drv.session(database=os.environ.get("NEO4J_DATABASE", "neo4j"))


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_rows() -> list[dict[str, Any]]:
    rows = []
    with (STAGING / "rows.jsonl").open(encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            d["_staged_row_index"] = i
            d["_staged_row_id"] = f"TR{i:05d}"
            rows.append(d)
    return rows


def load_rejected() -> list[dict[str, Any]]:
    rows = []
    p = STAGING / "rejected.jsonl"
    with p.open(encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            line = line.strip()
            if line:
                d = json.loads(line)
                d["_staged_row_index"] = i
                rows.append(d)
    return rows


def write_json(name: str, obj: Any) -> pathlib.Path:
    PACKET.mkdir(parents=True, exist_ok=True)
    p = PACKET / name
    p.write_text(json.dumps(obj, indent=1, ensure_ascii=False, sort_keys=False) + "\n", encoding="utf-8")
    return p


def write_jsonl(name: str, rows: list[dict[str, Any]]) -> pathlib.Path:
    PACKET.mkdir(parents=True, exist_ok=True)
    p = PACKET / name
    with p.open("w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    return p


def graph_census(s) -> dict[str, Any]:
    return {
        "nodes": s.run("MATCH (n) RETURN count(n) AS c").single()["c"],
        "relationships": s.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"],
        "translation_nodes": s.run("MATCH (t:Translation) RETURN count(t) AS c").single()["c"],
        "has_translation_edges": s.run(
            "MATCH ()-[r:HAS_TRANSLATION]->() RETURN count(r) AS c"
        ).single()["c"],
    }


def core_corpus(s) -> dict[str, int]:
    """Canonical mantra count per Veda, on the same definition the invariant uses."""
    out = {}
    for r in s.run(
        """
        MATCH (m:Mantra)
        WHERE m.canonical_key STARTS WITH 'VG:'
        WITH split(m.canonical_key,':')[1] AS veda, count(m) AS c
        RETURN veda, c ORDER BY veda
        """
    ):
        out[r["veda"]] = r["c"]
    return out


def translation_coverage(s) -> dict[str, Any]:
    """Per-Veda translated-mantra counts, split by alignment_level.

    Counts distinct *mantras*, not translations: a mantra carrying two translations is one
    covered verse, and conflating the two is how a coverage figure exceeds its corpus.
    """
    # Seeded with an explicit zero for all four Vedas. A Veda with no translation at all
    # returns no row, and a dict that simply lacks the key lets a reader infer whatever
    # they expected -- Samaveda is at 0 of 1,844, and that zero has to be stated, not
    # left as an absent key next to three populated ones.
    per_veda = {
        v: {"covered_mantras": 0, "translation_nodes": 0, "corpus": n, "observed_row": False}
        for v, n in sorted(CORE_CORPUS_INVARIANT.items())
    }
    for r in s.run(
        """
        MATCH (m:Mantra)-[:HAS_TRANSLATION]->(t:Translation)
        WHERE t.language = 'en'
        WITH split(m.canonical_key,':')[1] AS veda, m, t
        RETURN veda,
               count(DISTINCT m) AS covered,
               count(t) AS translations
        ORDER BY veda
        """
    ):
        per_veda[r["veda"]] = {
            "covered_mantras": r["covered"],
            "translation_nodes": r["translations"],
            "corpus": CORE_CORPUS_INVARIANT.get(r["veda"]),
            "observed_row": True,
        }
    by_level = {}
    for r in s.run(
        """
        MATCH (m:Mantra)-[:HAS_TRANSLATION]->(t:Translation)
        WHERE t.language = 'en'
        WITH split(m.canonical_key,':')[1] AS veda,
             coalesce(t.alignment_level,'<null>') AS lvl, count(DISTINCT m) AS c
        RETURN veda, lvl, c ORDER BY veda, lvl
        """
    ):
        by_level.setdefault(r["veda"], {})[r["lvl"]] = r["c"]
    by_source = {}
    for r in s.run(
        """
        MATCH (m:Mantra)-[:HAS_TRANSLATION]->(t:Translation)
        WHERE t.language = 'en'
        WITH split(m.canonical_key,':')[1] AS veda,
             coalesce(t.source_id,'<null>') AS src, count(DISTINCT m) AS c
        RETURN veda, src, c ORDER BY veda, src
        """
    ):
        by_source.setdefault(r["veda"], {})[r["src"]] = r["c"]
    return {"per_veda": per_veda, "by_alignment_level": by_level, "by_source_id": by_source}


def attachment_digest(s) -> dict[str, Any]:
    """A content digest of every English translation attachment in the graph.

    Hashes passage key + source + alignment_level + a hash of the text, sorted. A census
    cannot detect a rewritten translation body; this can.
    """
    h = hashlib.sha256()
    n = 0
    tuples = []
    for r in s.run(
        """
        MATCH (m:Mantra)-[:HAS_TRANSLATION]->(t:Translation)
        WHERE t.language = 'en'
        RETURN m.canonical_key AS k,
               coalesce(t.source_id,'') AS src,
               coalesce(t.alignment_level,'') AS lvl,
               coalesce(t.translation_id,'') AS tid,
               coalesce(t.text,'') AS text
        """
    ):
        tuples.append(
            f"{r['k']}|{r['src']}|{r['lvl']}|{r['tid']}|{hashlib.sha256(r['text'].encode('utf-8')).hexdigest()}"
        )
        n += 1
    for line in sorted(tuples):
        h.update(line.encode("utf-8"))
        h.update(b"\n")
    return {"attachments": n, "digest_sha256": h.hexdigest()}
