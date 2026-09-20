#!/usr/bin/env python3
"""Fetch, once, every graph fact the translation gates need, into a local cache.

Gate B and Gate C ask overlapping questions of the same few thousand passages, and the
adversarial checks need neighbours of neighbours. Re-querying per row would make the run
slow enough that it would get sampled instead of run at 100%, which is how a gate quietly
becomes an opinion. So this resolves everything up front and writes a cache the gates read.

Nothing here writes. The cache is an intermediate, kept out of the packet directory and
regenerable from the graph at any time.
"""

from __future__ import annotations

import json
import pathlib
import sys
import time

_T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - _T0:7.1f}s] {msg}", flush=True)

from gate_bc_common import driver, load_rows, session

CACHE = pathlib.Path(
    r"C:\Users\HKM49\AppData\Local\Temp\claude\d--VedaGraph"
    r"\9811a2e5-56d7-4f68-aa33-48f350e56c58\scratchpad\graph_facts.json"
)

CHUNK = 500


def chunks(seq, n=CHUNK):
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def main() -> int:
    rows = load_rows()
    target_keys = sorted({r["canonical_key"] for r in rows})
    ref_keys = sorted(
        {
            k
            for r in rows
            for k in (
                r["payload"].get("control_rv_key"),
                r["payload"].get("cross_corpus_source_key"),
            )
            if k
        }
    )
    all_keys = sorted(set(target_keys) | set(ref_keys))
    print(f"targets={len(target_keys)} referenced_rv={len(ref_keys)} union={len(all_keys)}")

    passages: dict[str, dict] = {}
    texts: dict[str, list[dict]] = {}
    translations: dict[str, list[dict]] = {}
    siblings: dict[str, list[str]] = {}

    drv = driver()
    with session(drv) as s:
        for bi, batch in enumerate(chunks(all_keys)):
            log(f"passage batch {bi}")
            for rec in s.run(
                """
                UNWIND $keys AS k
                MATCH (m:Passage) WHERE m.canonical_key = k
                RETURN k AS key, labels(m) AS labels, m.veda AS veda, m.work_id AS work_id,
                       m.parent_key AS parent_key, m.status AS status,
                       m.hierarchy AS hierarchy, m.display_label AS display_label,
                       m.sequence_in_parent AS seq, m.canonical_citation AS citation,
                       m.display_type AS display_type
                """,
                keys=batch,
            ):
                passages[rec["key"]] = {
                    "labels": sorted(rec["labels"]),
                    "veda": rec["veda"],
                    "work_id": rec["work_id"],
                    "parent_key": rec["parent_key"],
                    "status": rec["status"],
                    "hierarchy": rec["hierarchy"],
                    "display_label": rec["display_label"],
                    "sequence_in_parent": rec["seq"],
                    "citation": rec["citation"],
                    "display_type": rec["display_type"],
                }
            for rec in s.run(
                """
                UNWIND $keys AS k
                MATCH (m:Passage)-[:HAS_TEXT_VERSION]->(t:TextVersion)
                WHERE m.canonical_key = k AND t.language = 'sa'
                RETURN k AS key, t.text_nfc AS text, t.script AS script,
                       t.text_role AS role, t.source_id AS source_id,
                       t.accented AS accented, t.content_sha256 AS sha
                """,
                keys=batch,
            ):
                texts.setdefault(rec["key"], []).append(
                    {
                        "text": rec["text"],
                        "script": rec["script"],
                        "role": rec["role"],
                        "source_id": rec["source_id"],
                        "accented": rec["accented"],
                        "content_sha256": rec["sha"],
                    }
                )
            for rec in s.run(
                """
                UNWIND $keys AS k
                MATCH (m:Passage)-[:HAS_TRANSLATION]->(t:Translation)
                WHERE m.canonical_key = k
                RETURN k AS key, t.text AS text, t.source_id AS source_id,
                       t.translator AS translator, t.language AS language,
                       t.alignment_level AS alignment_level,
                       t.translation_id AS translation_id,
                       t.work_edition AS work_edition,
                       t.upstream_correction_id AS upstream_correction_id,
                       t.quality_status AS quality_status
                """,
                keys=batch,
            ):
                translations.setdefault(rec["key"], []).append(
                    {
                        "text": rec["text"],
                        "source_id": rec["source_id"],
                        "translator": rec["translator"],
                        "language": rec["language"],
                        "alignment_level": rec["alignment_level"],
                        "translation_id": rec["translation_id"],
                        "work_edition": rec["work_edition"],
                        "upstream_correction_id": rec["upstream_correction_id"],
                        "quality_status": rec["quality_status"],
                    }
                )

        log("passages/texts/translations done")
        # Sibling spines, for the off-by-one attack: every child of each target's parent,
        # in the graph's own sequence_in_parent order.
        parents = sorted({p["parent_key"] for p in passages.values() if p.get("parent_key")})
        for batch in chunks(parents):
            for rec in s.run(
                """
                UNWIND $parents AS pk
                MATCH (c:Passage) WHERE c.parent_key = pk AND c.canonical_key IS NOT NULL
                WITH pk, c ORDER BY coalesce(c.sequence_in_parent, 0), c.canonical_key
                RETURN pk AS parent, collect(c.canonical_key) AS kids
                """,
                parents=batch,
            ):
                siblings[rec["parent"]] = rec["kids"]

        log("siblings done")
        # The off-by-one attack compares a staged literal against the translations already
        # live on the target's canonical *neighbours*. The first version of this cache
        # fetched only the staged targets and the Rigveda keys they cite, so every
        # neighbour lookup came back empty and the shift attack reported zero suspicious
        # rows over zero evaluated rows -- a check that cannot fail is not a check. So the
        # sibling spines are resolved first, and then every key on them is fetched too.
        sibling_keys = sorted({k for kids in siblings.values() for k in kids} - set(passages))
        log(f"fetching {len(sibling_keys)} neighbour keys for the shift attack")
        for batch in chunks(sibling_keys):
            for rec in s.run(
                """
                UNWIND $keys AS k
                MATCH (m:Passage)-[:HAS_TRANSLATION]->(t:Translation)
                WHERE m.canonical_key = k
                RETURN k AS key, t.text AS text, t.source_id AS source_id,
                       t.language AS language, t.alignment_level AS alignment_level,
                       t.translator AS translator, t.translation_id AS translation_id
                """,
                keys=batch,
            ):
                translations.setdefault(rec["key"], []).append(
                    {
                        "text": rec["text"],
                        "source_id": rec["source_id"],
                        "language": rec["language"],
                        "alignment_level": rec["alignment_level"],
                        "translator": rec["translator"],
                        "translation_id": rec["translation_id"],
                    }
                )
            for rec in s.run(
                """
                UNWIND $keys AS k
                MATCH (m:Passage) WHERE m.canonical_key = k
                RETURN k AS key, labels(m) AS labels, m.veda AS veda, m.work_id AS work_id,
                       m.parent_key AS parent_key, m.status AS status,
                       m.display_label AS display_label, m.sequence_in_parent AS seq,
                       m.canonical_citation AS citation, m.display_type AS display_type,
                       m.hierarchy AS hierarchy
                """,
                keys=batch,
            ):
                passages.setdefault(
                    rec["key"],
                    {
                        "labels": sorted(rec["labels"]),
                        "veda": rec["veda"],
                        "work_id": rec["work_id"],
                        "parent_key": rec["parent_key"],
                        "status": rec["status"],
                        "hierarchy": rec["hierarchy"],
                        "display_label": rec["display_label"],
                        "sequence_in_parent": rec["seq"],
                        "citation": rec["citation"],
                        "display_type": rec["display_type"],
                        "fetched_as_neighbour": True,
                    },
                )
        log("neighbour keys done")

        # Parent existence and hierarchy, for B1/B2.
        parent_info = {}
        for batch in chunks(parents):
            for rec in s.run(
                """
                UNWIND $parents AS pk
                MATCH (p:Passage) WHERE p.canonical_key = pk
                RETURN pk AS key, labels(p) AS labels, p.display_label AS label,
                       p.parent_key AS grandparent, p.work_id AS work_id
                """,
                parents=batch,
            ):
                parent_info[rec["key"]] = {
                    "labels": sorted(rec["labels"]),
                    "display_label": rec["label"],
                    "grandparent": rec["grandparent"],
                    "work_id": rec["work_id"],
                }

        log("parent_info done")
        # The graph's own parallel-layer relations between each row's target and its cited
        # Rigveda key. The staging metadata claims one of these; this is the graph's answer.
        pairs = sorted(
            {
                (r["canonical_key"], k)
                for r in rows
                for k in (
                    r["payload"].get("control_rv_key"),
                    r["payload"].get("cross_corpus_source_key"),
                )
                if k
            }
        )
        rels: dict[str, list[str]] = {}
        for batch in chunks([{"a": a, "b": b} for a, b in pairs]):
            for rec in s.run(
                """
                UNWIND $pairs AS p
                MATCH (a:Passage)-[r]-(b:Passage)
                WHERE a.canonical_key = p.a AND b.canonical_key = p.b
                RETURN p.a + '||' + p.b AS pair, collect(DISTINCT type(r)) AS types
                """,
                pairs=batch,
            ):
                rels[rec["pair"]] = sorted(rec["types"])

        log("graph relations done")
        # Every :Mantra in each Veda, so coverage prediction and boundary sampling can be
        # computed without another pass.
        corpus: dict[str, list[str]] = {}
        for rec in s.run(
            """
            MATCH (m:Mantra) WHERE m.canonical_key STARTS WITH 'VG:'
            WITH split(m.canonical_key,':')[1] AS veda, m.canonical_key AS k
            RETURN veda, collect(k) AS keys
            """
        ):
            corpus[rec["veda"]] = sorted(rec["keys"])

        log("corpus done")
        # Which mantras already carry an English translation, per Veda.
        covered: dict[str, list[str]] = {}
        for rec in s.run(
            """
            MATCH (m:Mantra)-[:HAS_TRANSLATION]->(t:Translation)
            WHERE t.language = 'en'
            WITH split(m.canonical_key,':')[1] AS veda, collect(DISTINCT m.canonical_key) AS ks
            RETURN veda, ks
            """
        ):
            covered[rec["veda"]] = sorted(rec["ks"])
    log("covered done")
    drv.close()

    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(
        json.dumps(
            {
                "passages": passages,
                "texts": texts,
                "translations": translations,
                "siblings": siblings,
                "parent_info": parent_info,
                "graph_relations": rels,
                "corpus": corpus,
                "covered_en": covered,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"cache -> {CACHE}")
    print(f"passages resolved: {len(passages)} / {len(all_keys)}")
    print(f"targets unresolved: {sorted(set(target_keys) - set(passages))[:10]}")
    print(f"rv refs unresolved: {sorted(set(ref_keys) - set(passages))[:10]}")
    print(f"with sanskrit text: {len(texts)}  with translations: {len(translations)}")
    print(f"sibling spines: {len(siblings)}  graph relation pairs: {len(rels)}")
    print(f"corpus: { {k: len(v) for k, v in sorted(corpus.items())} }")
    print(f"covered_en: { {k: len(v) for k, v in sorted(covered.items())} }")
    return 0


if __name__ == "__main__":
    sys.exit(main())
