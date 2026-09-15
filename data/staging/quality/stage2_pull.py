"""Stage 2: pull every graph claim that falls on an aligned mantra, plus the registries.

Read-only. Nothing here mutates the canonical store.
"""
from __future__ import annotations

import collections
import json
import os
import pathlib
import sys

from dotenv import load_dotenv

load_dotenv("D:/VedaGraph/.env")
from neo4j import GraphDatabase  # noqa: E402

SCRATCH = pathlib.Path(sys.argv[1])


def main() -> None:
    alignment = json.loads((SCRATCH / "stage1_alignment.json").read_text(encoding="utf-8"))
    keys = sorted(
        {r["canonical_key"] for r in alignment["records"] if r["align_status"] == "ALIGNED"}
    )
    driver = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
    )
    out: dict[str, object] = {"aligned_keys": keys}
    with driver.session(database=os.environ.get("NEO4J_DATABASE", "neo4j")) as session:

        def rows(query: str, **params) -> list[dict]:
            return [dict(record) for record in session.run(query, **params)]

        out["devatas"] = rows(
            "MATCH (d:Devata) RETURN d.entity_key AS key, d.label_iast AS label_iast, "
            "d.label_en AS label_en, d.aliases_iast AS aliases, d.structure AS structure, "
            "d.devata_subtype AS subtype, d.is_composite AS is_composite"
        )
        out["concepts"] = rows(
            "MATCH (c:Concept) RETURN c.entity_key AS key, c.preferred_label_sa AS label_sa, "
            "c.preferred_label_en AS label_en, c.aliases_sa AS aliases_sa, "
            "c.aliases_en AS aliases_en, labels(c) AS labels"
        )
        out["mentions_devata"] = rows(
            "MATCH (m:Mantra)-[r:MENTIONS_DEVATA]->(d:Devata) WHERE m.canonical_key IN $keys "
            "RETURN m.canonical_key AS key, d.entity_key AS devata, r.matched_forms AS forms, "
            "r.referent_certainty AS certainty, r.referent_basis AS basis, "
            "r.quality_tier AS tier, r.occurrences AS occurrences, r.method AS method, "
            "r.morphological_roles AS roles, r.evidence AS evidence, r.veda AS veda",
            keys=keys,
        )
        out["mentions_entity"] = rows(
            "MATCH (m:Mantra)-[r:MENTIONS_ENTITY]->(e) WHERE m.canonical_key IN $keys "
            "RETURN m.canonical_key AS key, e.entity_key AS entity, labels(e) AS labels, "
            "r.matched_aliases AS aliases, r.quality_tier AS tier, r.method AS method, "
            "r.evidence AS evidence, r.theonym_ambiguous AS theonym_ambiguous",
            keys=keys,
        )
        out["about_concept"] = rows(
            "MATCH (m:Mantra)-[r:ABOUT_CONCEPT]->(c) WHERE m.canonical_key IN $keys "
            "RETURN m.canonical_key AS key, c.entity_key AS concept, r.confidence AS confidence, "
            "r.score AS score, r.method AS method, r.quality_tier AS tier, "
            "r.evidence_basis AS evidence_basis, r.evidence AS evidence, r.veda AS veda",
            keys=keys,
        )
        out["mentions_lemma"] = rows(
            "MATCH (m:Mantra)-[r:MENTIONS_LEMMA]->(l:Lemma) WHERE m.canonical_key IN $keys "
            "RETURN m.canonical_key AS key, l.canonical_key AS lemma_key, "
            "properties(l) AS lemma_props",
            keys=keys,
        )
        out["has_devata"] = rows(
            "MATCH (m:Mantra)-[r:HAS_DEVATA]->(d:Devata) WHERE m.canonical_key IN $keys "
            "RETURN m.canonical_key AS key, d.entity_key AS devata, r.confidence AS confidence, "
            "r.quality_tier AS tier, r.knowledge_layer AS layer, "
            "r.attribution_precision AS precision, r.scope_origin AS scope, "
            "r.source_id AS source_id",
            keys=keys,
        )
        out["has_devata_ascription"] = rows(
            "MATCH (m:Mantra)-[r:HAS_DEVATA_ASCRIPTION]->(d) WHERE m.canonical_key IN $keys "
            "RETURN m.canonical_key AS key, d.entity_key AS target, labels(d) AS labels, "
            "properties(d) AS props, r.confidence AS confidence, r.quality_tier AS tier, "
            "r.attribution_precision AS precision",
            keys=keys,
        )
        out["has_rishi"] = rows(
            "MATCH (m:Mantra)-[r:HAS_RISHI]->(x) WHERE m.canonical_key IN $keys "
            "RETURN m.canonical_key AS key, x.entity_key AS rishi, r.confidence AS confidence, "
            "r.quality_tier AS tier, r.attribution_precision AS precision",
            keys=keys,
        )
        out["has_chandas"] = rows(
            "MATCH (m:Mantra)-[r:HAS_CHANDAS]->(x) WHERE m.canonical_key IN $keys "
            "RETURN m.canonical_key AS key, x.entity_key AS chandas, "
            "x.display_label AS label, r.confidence AS confidence, r.quality_tier AS tier, "
            "r.attribution_precision AS precision",
            keys=keys,
        )
        out["semantic_assertions"] = rows(
            "MATCH (m:Mantra)-[:HAS_SEMANTIC_ASSERTION]->(a:SemanticAssertion) "
            "WHERE m.canonical_key IN $keys RETURN m.canonical_key AS key, properties(a) AS props",
            keys=keys,
        )
        out["uses_formula"] = rows(
            "MATCH (m:Mantra)-[r:USES_FORMULA]->(f:Formula) WHERE m.canonical_key IN $keys "
            "RETURN m.canonical_key AS key, f.entity_key AS formula, "
            "properties(f) AS formula_props, r.quality_tier AS tier, r.method AS method, "
            "r.score AS score, r.evidence AS evidence",
            keys=keys,
        )
        out["texts"] = rows(
            "MATCH (m:Mantra)-[:HAS_TEXT_VERSION]->(t:TextVersion) WHERE m.canonical_key IN $keys "
            "RETURN m.canonical_key AS key, t.text_nfc AS text, properties(t) AS props",
            keys=keys,
        )
        out["translations"] = rows(
            "MATCH (m:Mantra)-[:HAS_TRANSLATION]->(t:Translation) WHERE m.canonical_key IN $keys "
            "RETURN m.canonical_key AS key, t.text AS text, t.translator AS translator, "
            "t.source_id AS source_id",
            keys=keys,
        )
        out["corpus_totals"] = rows(
            "MATCH (m:Mantra) RETURN m.veda AS veda, count(*) AS n"
        )
    driver.close()

    (SCRATCH / "stage2_graph.json").write_text(
        json.dumps(out, ensure_ascii=False), encoding="utf-8"
    )
    for name, value in out.items():
        if isinstance(value, list):
            print(f"{name:26s} {len(value)}")
    print("aligned keys:", len(keys))
    print("per veda:", dict(collections.Counter(k.split(":")[1] for k in keys)))


if __name__ == "__main__":
    main()
