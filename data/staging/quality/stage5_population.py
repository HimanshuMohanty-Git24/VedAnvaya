"""Stage 5: the measurements that need the whole graph rather than the evaluation set.

Everything here is a full-population count, so none of it carries sampling error. It is
separated from the scored measurements for exactly that reason: a reader should be able to
tell at a glance which figures are estimates from 3,072 annotated verses and which are
censuses of all 20,210.

Read-only.
"""

from __future__ import annotations

import collections
import json
import os
import pathlib
import re
import sys
import unicodedata

from dotenv import load_dotenv

load_dotenv("D:/VedaGraph/.env")
from neo4j import GraphDatabase  # noqa: E402

SCRATCH = pathlib.Path(sys.argv[1])

#: A Sanskrit verbal root always contains a vowel. These are the vowel letters, written as
#: escapes so this file survives any encoding.
VOWELS = set("aiu" "\u0101\u012b\u016b" "\u1e5b\u1e5d\u1e37\u1e39" "eo")


def has_no_vowel(root: str) -> bool:
    """True when a claimed root carries no vowel letter at all.

    This is the signature of the below-mark stripping defect Agent 2 found in the
    Atharvavedic SEARCH_DERIVATIVE layer: a vocalic r is r plus U+0325, and a normaliser
    that removes the base letter leaves the bare mark behind. The root of *karisyasi* is
    *kr* with a ring below the r; strip the r and what remains renders as a lone k.
    """
    if not root:
        return False
    decomposed = unicodedata.normalize("NFD", root)
    letters = [ch for ch in decomposed if not unicodedata.combining(ch)]
    return not any(ch.lower() in VOWELS for ch in letters)


def main() -> None:
    driver = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
    )
    out: dict[str, object] = {}
    with driver.session(database=os.environ.get("NEO4J_DATABASE", "neo4j")) as session:

        def rows(query: str, **params) -> list[dict]:
            return [dict(record) for record in session.run(query, **params)]

        def one(query: str, **params) -> dict:
            record = session.run(query, **params).single()
            return dict(record) if record else {}

        out["graph_size"] = {
            "nodes": one("MATCH (n) RETURN count(n) AS n")["n"],
            "relationships": one("MATCH ()-[r]->() RETURN count(r) AS n")["n"],
        }

        # ---------------------------------------------------- the confidence property
        out["confidence_by_predicate"] = rows(
            "MATCH ()-[r]->() WHERE r.confidence IS NOT NULL "
            "WITH type(r) AS predicate, r.confidence AS value, count(*) AS edges "
            "WITH predicate, collect({value: value, edges: edges}) AS spread, "
            "     sum(edges) AS total "
            "RETURN predicate, total, size(spread) AS distinct_values, "
            "       [s IN spread | [s.value, s.edges]] AS spread, "
            "       CASE WHEN size(spread) = 1 THEN 'SINGLE_CONSTANT' ELSE 'VARIES' END "
            "         AS guard "
            "ORDER BY total DESC"
        )
        out["confidence_values"] = rows(
            "MATCH ()-[r]->() WHERE r.confidence IS NOT NULL "
            "RETURN r.confidence AS value, count(*) AS edges ORDER BY edges DESC"
        )
        out["confidence_by_tier"] = rows(
            "MATCH ()-[r]->() WHERE r.confidence IS NOT NULL "
            "RETURN type(r) AS predicate, r.confidence AS confidence, "
            "       r.quality_tier AS quality_tier, r.knowledge_layer AS knowledge_layer, "
            "       r.attribution_precision AS attribution_precision, count(*) AS edges "
            "ORDER BY edges DESC"
        )

        # ----------------------------------- two values for one attribute, same confidence
        def duplicate_axis(predicate: str) -> dict:
            result = one(
                f"MATCH (m:Mantra)-[r:{predicate}]->(x) "
                "WITH m, collect(DISTINCT r.quality_tier) AS tiers, "
                "     collect(DISTINCT x) AS targets, collect(DISTINCT r.confidence) AS conf "
                "WHERE size(targets) > 1 "
                "RETURN count(*) AS mantras_with_multiple_values, "
                "       sum(CASE WHEN size(tiers) > 1 THEN 1 ELSE 0 END) AS across_tiers, "
                "       sum(CASE WHEN size(conf) = 1 THEN 1 ELSE 0 END) AS at_one_confidence"
            )
            total = one(
                f"MATCH (m:Mantra)-[:{predicate}]->() RETURN count(DISTINCT m) AS n"
            )["n"]
            result["mantras_with_the_predicate"] = total
            return result

        out["multi_valued_attribution"] = {
            predicate: duplicate_axis(predicate)
            for predicate in ("HAS_CHANDAS", "HAS_DEVATA", "HAS_RISHI")
        }
        out["chandas_tier_conflict_examples"] = rows(
            "MATCH (m:Mantra)-[a:HAS_CHANDAS]->(x), (m)-[b:HAS_CHANDAS]->(y) "
            "WHERE a.quality_tier = 'TIER_A' AND b.quality_tier = 'TIER_B' AND x <> y "
            "RETURN m.canonical_key AS key, x.display_label AS source_explicit, "
            "       y.display_label AS inherited, a.confidence AS confidence_a, "
            "       b.confidence AS confidence_b LIMIT 12"
        )
        out["chandas_tier_conflict_total"] = one(
            "MATCH (m:Mantra)-[a:HAS_CHANDAS]->(x), (m)-[b:HAS_CHANDAS]->(y) "
            "WHERE a.quality_tier = 'TIER_A' AND b.quality_tier = 'TIER_B' AND x <> y "
            "RETURN count(DISTINCT m) AS mantras"
        )

        # ---------------------------------------------------- the lemma layer, as it is
        inventory = one(
            "MATCH (l:Lemma) RETURN count(*) AS nodes, sum(l.mantra_count) AS implied_pairs, "
            "sum(l.token_count) AS implied_tokens"
        )
        wired = one(
            "MATCH (:Mantra)-[e:MENTIONS_LEMMA]->(l:Lemma) "
            "RETURN count(e) AS edges, count(DISTINCT l) AS lemmas"
        )
        wired_implied = one(
            "MATCH (:Mantra)-[:MENTIONS_LEMMA]->(l:Lemma) "
            "WITH DISTINCT l RETURN sum(l.mantra_count) AS implied"
        )
        out["lemma_layer"] = {
            **inventory,
            **wired,
            "implied_pairs_for_the_wired_lemmas": wired_implied["implied"],
            "recall_against_the_graphs_own_inventory": round(
                wired["edges"] / inventory["implied_pairs"], 5
            ),
            "recall_within_the_lemmas_it_attempted": round(
                wired["edges"] / wired_implied["implied"], 5
            ),
            "parts_of_speech": rows(
                "MATCH (l:Lemma) RETURN l.parts_of_speech AS pos, count(*) AS n "
                "ORDER BY n DESC"
            ),
            "wired_lemmas": rows(
                "MATCH (:Mantra)-[e:MENTIONS_LEMMA]->(l:Lemma) "
                "RETURN l.lemma AS lemma, count(e) AS edges ORDER BY edges DESC"
            ),
        }

        # ---------------------------------------------------- semantic assertion census
        out["semantic_assertions"] = {
            "by_derivation": rows(
                "MATCH (a:SemanticAssertion) RETURN a.derivation AS derivation, "
                "a.quality_tier AS quality_tier, a.knowledge_layer AS knowledge_layer, "
                "a.state AS state, a.review_state AS review_state, "
                "a.human_gold_status AS human_gold_status, "
                "a.extraction_model AS extraction_model, count(*) AS n ORDER BY n DESC"
            ),
            "role_slots": rows(
                "MATCH (a:SemanticAssertion) "
                "WITH a, size([x IN ['ASSERTION_AGENT', 'ASSERTION_PREDICATE', "
                "  'ASSERTION_TARGET'] WHERE exists(()<-[]-(a))]) AS ignored "
                "RETURN a.derivation AS derivation, "
                "  COUNT { (a)-[:ASSERTION_AGENT]->() } AS agents, "
                "  COUNT { (a)-[:ASSERTION_PREDICATE]->() } AS predicates, "
                "  COUNT { (a)-[:ASSERTION_TARGET]->() } AS targets, count(*) AS n"
            ),
            "role_slot_histogram": rows(
                "MATCH (a:SemanticAssertion) "
                "WITH a, COUNT { (a)-[:ASSERTION_AGENT]->() } "
                "        + COUNT { (a)-[:ASSERTION_PREDICATE]->() } "
                "        + COUNT { (a)-[:ASSERTION_TARGET]->() } AS slots "
                "RETURN a.derivation AS derivation, slots, count(*) AS n "
                "ORDER BY derivation, slots"
            ),
        }

        roots = rows(
            "MATCH (a:SemanticAssertion) WHERE a.root IS NOT NULL "
            "RETURN a.root AS root, count(*) AS n ORDER BY n DESC"
        )
        defective = [row for row in roots if has_no_vowel(row["root"])]
        out["root_defect"] = {
            "assertions_with_a_root": sum(row["n"] for row in roots),
            "distinct_roots": len(roots),
            "distinct_roots_with_no_vowel": len(defective),
            "assertions_with_a_vowelless_root": sum(row["n"] for row in defective),
            "share": round(
                sum(row["n"] for row in defective) / max(sum(row["n"] for row in roots), 1),
                4,
            ),
            "examples": [
                {
                    "root_repr": ascii(row["root"]),
                    "codepoints": [f"U+{ord(ch):04X}" for ch in row["root"]],
                    "assertions": row["n"],
                }
                for row in defective[:15]
            ],
        }

        # ---------------------------------------------------- formula and parallel layers
        out["formula_layer"] = {
            "uses_formula": one(
                "MATCH (m:Mantra)-[r:USES_FORMULA]->(f:Formula) "
                "RETURN count(r) AS edges, count(DISTINCT m) AS mantras, "
                "count(DISTINCT f) AS formulae"
            ),
            "shares_formula_with": one(
                "MATCH ()-[r:SHARES_FORMULA_WITH]->() RETURN count(r) AS edges"
            ),
            "by_tier": rows(
                "MATCH ()-[r:USES_FORMULA]->() RETURN r.quality_tier AS tier, "
                "r.method AS method, r.evidence_basis AS evidence_basis, count(*) AS n "
                "ORDER BY n DESC"
            ),
            "formula_length": rows(
                "MATCH (f:Formula) RETURN f.token_count AS tokens, count(*) AS n "
                "ORDER BY n DESC LIMIT 12"
            ),
        }
        out["parallel_layer"] = {
            predicate: one(
                f"MATCH ()-[r:{predicate}]->() RETURN count(r) AS edges, "
                "count(DISTINCT r.transformation_type) AS transformation_types"
            )
            for predicate in (
                "PARALLEL_TO", "EXACT_PARALLEL_OF", "NEAR_PARALLEL_OF", "REUSES_TEXT_FROM"
            )
        }

        # ---------------------------------------------------- the attribution split
        out["attribution_split"] = rows(
            "MATCH (m:Mantra)-[r]->() "
            "WHERE type(r) IN ['HAS_DEVATA', 'HAS_DEVATA_ASCRIPTION', 'HAS_RISHI', "
            "                  'HAS_CHANDAS'] "
            "RETURN type(r) AS predicate, m.veda AS veda, r.quality_tier AS tier, "
            "r.attribution_precision AS precision, count(*) AS edges, "
            "count(DISTINCT m) AS mantras ORDER BY predicate, veda, tier"
        )

    driver.close()
    (SCRATCH / "stage5_population.json").write_text(
        json.dumps(out, ensure_ascii=False, default=str), encoding="utf-8"
    )
    print(json.dumps(
        {
            k: v for k, v in out.items()
            if k in ("graph_size", "lemma_layer", "root_defect",
                     "multi_valued_attribution", "chandas_tier_conflict_total",
                     "formula_layer", "parallel_layer")
        },
        ensure_ascii=False, indent=1, default=str,
    )[:6000])
    print("== confidence per predicate")
    for row in out["confidence_by_predicate"]:
        print("  {:28s} total={:6d} distinct={:2d} {}".format(
            row["predicate"], row["total"], row["distinct_values"], row["guard"]))
    print("== semantic role slot histogram")
    for row in out["semantic_assertions"]["role_slot_histogram"]:
        print("  ", row)


if __name__ == "__main__":
    main()
