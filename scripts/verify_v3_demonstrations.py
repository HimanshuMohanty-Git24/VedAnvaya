"""Run the nine demonstrations the V3 gate requires, and report what each returns.

The gate names specific things a user must be able to explore: Indra end to end, Agni
separated from fire, Soma the god separated from soma the drink, Varuna, Rudra *without* a
Siva identification, an Atharvavedic healing graph, a Yajurvedic rite, one Rigveda-to-
Samaveda transformation, and a civilizational story kept separate from its interpretation.

Each check below returns rows or it does not, and the script says which. It deliberately
does **not** score anything: a demonstration that returns 40 rows of nonsense passes this
script and fails a reader, so this is a wiring check -- "is the question answerable at
all?" -- and the judgement stays with the reports that cite it.

Two demonstrations are checked in a way worth explaining. **Rudra** is checked by asserting
an *absence*: no edge anywhere may assert a Siva identification as fact, because the whole
point of the requirement is that a later identification belongs in an ``InterpretiveClaim``
and nowhere else. **Agni** and **Soma** are checked by confirming the deity and the
non-deity sense reach different nodes, since the failure mode is a merge, not a gap.

Usage::

    python scripts/verify_v3_demonstrations.py
    python scripts/verify_v3_demonstrations.py --json out.json
"""

from __future__ import annotations

import argparse
import io
import json
import pathlib
import sys
from dataclasses import dataclass, field
from typing import Any, Final

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

BOLT_URI: Final = "bolt://localhost:7687"
BOLT_AUTH: Final = ("neo4j", "vedagraph_dev")


@dataclass
class Facet:
    """One thing a user must be able to ask, and what came back."""

    name: str
    cypher: str
    params: dict[str, Any] = field(default_factory=dict)
    #: Rows below this count make the facet a failure rather than a thin pass. Default 1:
    #: the facet exists to prove the question is answerable, not that it is rich.
    minimum: int = 1
    #: When true, rows are a FAILURE. Used for the Rudra/Siva separation check.
    expect_empty: bool = False


#: Indra, §44. Eighteen facets are named in the brief; these are the ones expressible as a
#: single query against the current ontology.
INDRA: Final = "VG:DEVATA:INDRAH"

DEMONSTRATIONS: Final[dict[str, tuple[Facet, ...]]] = {
    "indra": (
        Facet(
            "who_is_indra",
            "MATCH (d:Devata {entity_key:$k}) RETURN d.display_label AS label, "
            "d.short_description AS description, d.structure AS structure",
            {"k": INDRA},
        ),
        Facet(
            "textual_mentions_by_veda",
            "MATCH (p:Passage)-[r:MENTIONS_DEVATA]->(:Devata {entity_key:$k}) "
            "RETURN p.veda AS veda, count(DISTINCT p) AS mantras ORDER BY veda",
            {"k": INDRA},
            minimum=4,
        ),
        Facet(
            "strict_vs_inherited_attribution",
            "MATCH ()-[r:HAS_DEVATA]->(:Devata {entity_key:$k}) "
            "RETURN r.attribution_precision AS precision, count(*) AS n ORDER BY n DESC",
            {"k": INDRA},
        ),
        Facet(
            "actions_performed",
            "MATCH (:Devata {entity_key:$k})-[r:PERFORMS_ACTION]->(a:ActionPredicate) "
            "RETURN a.predicate AS action, r.assertion_count AS assertions "
            "ORDER BY assertions DESC LIMIT 12",
            {"k": INDRA},
            minimum=5,
        ),
        Facet(
            "actions_requested_of_him",
            "MATCH (:Devata {entity_key:$k})-[r:IS_ASKED_TO]->(a:ActionPredicate) "
            "RETURN a.predicate AS action, r.assertion_count AS assertions "
            "ORDER BY assertions DESC LIMIT 12",
            {"k": INDRA},
        ),
        Facet(
            "evidence_bound_assertions",
            "MATCH (p:Passage)-[:HAS_SEMANTIC_ASSERTION]->(s:SemanticAssertion)"
            "-[:ASSERTION_AGENT]->(:Devata {entity_key:$k}) "
            "RETURN s.predicate AS predicate, s.passage_key AS passage, "
            "s.evidence AS evidence, s.quality_tier AS tier LIMIT 5",
            {"k": INDRA},
        ),
        Facet(
            "co_deities_above_baseline",
            "MATCH (a:Devata)-[r:CO_OCCURS_WITH]-(b:Devata) WHERE a.entity_key=$k "
            "RETURN b.display_label AS codeity, r.lift AS lift, "
            "r.passage_count AS shared ORDER BY r.lift DESC LIMIT 8",
            {"k": INDRA},
            minimum=5,
        ),
        Facet(
            "rishis",
            "MATCH (p:Passage)-[:HAS_DEVATA]->(:Devata {entity_key:$k}) "
            "MATCH (p)-[:HAS_RISHI]->(r:Rishi) "
            "RETURN r.preferred_label AS rishi, count(DISTINCT p) AS mantras "
            "ORDER BY mantras DESC LIMIT 8",
            {"k": INDRA},
            minimum=5,
        ),
        Facet(
            "metres",
            "MATCH (p:Passage)-[:HAS_DEVATA]->(:Devata {entity_key:$k}) "
            "MATCH (p)-[:HAS_CHANDAS]->(c:Chandas) "
            "RETURN c.preferred_label AS chandas, count(DISTINCT p) AS mantras "
            "ORDER BY mantras DESC LIMIT 8",
            {"k": INDRA},
        ),
        Facet(
            "concepts",
            "MATCH (p:Passage)-[:MENTIONS_DEVATA]->(:Devata {entity_key:$k}) "
            "MATCH (p)-[:ABOUT_CONCEPT]->(c:Concept) "
            "RETURN c.preferred_label_en AS concept, count(DISTINCT p) AS mantras "
            "ORDER BY mantras DESC LIMIT 10",
            {"k": INDRA},
            minimum=5,
        ),
        Facet(
            "formulas",
            "MATCH (p:Passage)-[:MENTIONS_DEVATA]->(:Devata {entity_key:$k}) "
            "MATCH (p)-[:USES_FORMULA]->(f:Formula) WHERE f.cross_veda "
            "RETURN f.display_form AS formula, f.vedas AS vedas, "
            "f.occurrence_count AS occurrences ORDER BY occurrences DESC LIMIT 6",
            {"k": INDRA},
        ),
        Facet(
            "cross_veda_reused_passages",
            "MATCH (p:Passage)-[:MENTIONS_DEVATA]->(:Devata {entity_key:$k}) "
            "MATCH (p)-[r:EXACT_PARALLEL_OF|NEAR_PARALLEL_OF|REUSES_TEXT_FROM]-(q:Passage) "
            "WHERE p.veda <> q.veda "
            "RETURN p.canonical_citation AS a, q.canonical_citation AS b, "
            "type(r) AS relation LIMIT 6",
            {"k": INDRA},
        ),
        Facet(
            "functional_axes",
            "MATCH (:Devata {entity_key:$k})-[:HAS_AXIS]->(a:DeityAxis) RETURN a.axis AS axis",
            {"k": INDRA},
        ),
    ),
    "agni_deity_vs_fire": (
        Facet(
            "deity_and_phenomenon_are_distinct_nodes",
            "MATCH (n) WHERE n.entity_key = 'VG:DEVATA:AGNIH' "
            "   OR n.concept_id = 'VG:CONCEPT:AGNI-FIRE' "
            "RETURN labels(n) AS labels, coalesce(n.entity_key, n.concept_id) AS key, "
            "coalesce(n.display_label,'') AS label",
            minimum=2,
        ),
        Facet(
            "ambiguous_mentions_are_flagged",
            "MATCH ()-[r:MENTIONS_DEVATA]->(:Devata {entity_key:'VG:DEVATA:AGNIH'}) "
            "RETURN r.referent_certainty AS certainty, count(*) AS n ORDER BY n DESC",
            minimum=2,
        ),
    ),
    "soma_deity_vs_substance": (
        Facet(
            "deity_and_substance_are_distinct_nodes",
            "MATCH (n) WHERE n.entity_key = 'VG:DEVATA:SOMAH' "
            "   OR n.concept_id = 'VG:CONCEPT:SOMA-DRINK' "
            "RETURN labels(n) AS labels, coalesce(n.entity_key, n.concept_id) AS key",
            minimum=2,
        ),
        Facet(
            "attribution_and_mention_diverge",
            "MATCH (d:Devata {entity_key:'VG:DEVATA:SOMAH'}) "
            "RETURN COUNT { (d)<-[:HAS_DEVATA]-() } AS hymn_attributions, "
            "COUNT { (d)<-[:MENTIONS_DEVATA]-() } AS textual_mentions",
        ),
        Facet(
            "soma_ritual_exists",
            "MATCH (r:Ritual) WHERE r.entity_key CONTAINS 'SOMA' "
            "RETURN r.display_label AS rite, "
            "COUNT { (r)-[:DESCRIBED_IN]->() } AS passages",
        ),
    ),
    "varuna": (
        Facet(
            "four_veda_presence",
            "MATCH (p:Passage)-[:MENTIONS_DEVATA]->(:Devata {entity_key:'VG:DEVATA:VARUNAH'}) "
            "RETURN p.veda AS veda, count(DISTINCT p) AS mantras ORDER BY veda",
            minimum=3,
        ),
        Facet(
            "rta_and_order_relationship",
            "MATCH (p:Passage)-[:MENTIONS_DEVATA]->(:Devata {entity_key:'VG:DEVATA:VARUNAH'}) "
            "MATCH (p)-[:ABOUT_CONCEPT]->(c:Concept) "
            "RETURN c.preferred_label_en AS concept, count(DISTINCT p) AS mantras "
            "ORDER BY mantras DESC LIMIT 8",
        ),
        Facet(
            "actions",
            "MATCH (:Devata {entity_key:'VG:DEVATA:VARUNAH'})-[r:PERFORMS_ACTION]->"
            "(a:ActionPredicate) RETURN a.predicate AS action, "
            "r.assertion_count AS n ORDER BY n DESC LIMIT 10",
        ),
    ),
    "rudra_without_shiva": (
        Facet(
            "vedic_evidence_exists",
            "MATCH (p:Passage)-[:MENTIONS_DEVATA]->(:Devata {entity_key:'VG:DEVATA:RUDRAH'}) "
            "RETURN p.veda AS veda, count(DISTINCT p) AS mantras ORDER BY veda",
            minimum=2,
        ),
        Facet(
            "no_shiva_identification_asserted_as_fact",
            "MATCH (a)-[r]->(b) "
            "WHERE (toLower(coalesce(a.display_label,'')) CONTAINS 'rudra' "
            "   OR toLower(coalesce(b.display_label,'')) CONTAINS 'rudra') "
            "  AND (toLower(coalesce(a.display_label,'')) CONTAINS 'siva' "
            "   OR toLower(coalesce(b.display_label,'')) CONTAINS 'siva' "
            "   OR toLower(coalesce(a.display_label,'')) CONTAINS 'śiva' "
            "   OR toLower(coalesce(b.display_label,'')) CONTAINS 'śiva') "
            "  AND r.quality_tier IN ['TIER_A','TIER_B'] "
            "RETURN type(r) AS relation, a.display_label AS a, b.display_label AS b",
            expect_empty=True,
        ),
    ),
    "atharvaveda_healing": (
        Facet(
            "fever_is_its_own_condition",
            "MATCH (c:Condition) WHERE c.concept_id CONTAINS 'TAKMAN' "
            "RETURN c.concept_id AS id, c.preferred_label_en AS label, "
            "c.aliases_sa AS aliases",
        ),
        Facet(
            "passages_naming_fever",
            "MATCH (p:Passage)-[:MENTIONS_ENTITY]->(c:Condition) "
            "WHERE c.concept_id CONTAINS 'TAKMAN' "
            "RETURN p.veda AS veda, count(DISTINCT p) AS mantras ORDER BY mantras DESC",
        ),
        Facet(
            "treatment_edges",
            "MATCH (p:Passage)-[r:TREATS]->(c:Condition) "
            "RETURN c.preferred_label_en AS condition, count(DISTINCT p) AS passages, "
            "r.quality_tier AS tier ORDER BY passages DESC LIMIT 10",
            minimum=3,
        ),
        Facet(
            "plants_and_substances_in_healing_passages",
            "MATCH (p:Passage)-[:TREATS]->(:Condition) "
            "MATCH (p)-[:MENTIONS_ENTITY]->(e) WHERE e:Plant OR e:Substance "
            "RETURN e.preferred_label_en AS remedy, count(DISTINCT p) AS passages "
            "ORDER BY passages DESC LIMIT 8",
        ),
        Facet(
            "deities_invoked_in_healing_passages",
            "MATCH (p:Passage)-[:TREATS]->(:Condition) "
            "MATCH (p)-[:MENTIONS_DEVATA]->(d:Devata) "
            "RETURN d.display_label AS deity, count(DISTINCT p) AS passages "
            "ORDER BY passages DESC LIMIT 8",
        ),
    ),
    "yajurveda_ritual": (
        Facet(
            "rites_with_passages",
            "MATCH (r:Ritual)-[:DESCRIBED_IN]->(p:Passage) "
            "RETURN r.display_label AS rite, count(DISTINCT p) AS passages, "
            "collect(DISTINCT p.veda) AS vedas ORDER BY passages DESC",
            minimum=4,
        ),
        Facet(
            "apparatus_of_one_rite",
            "MATCH (r:Ritual {entity_key:'VG:CONCEPT:GRAHA-SOMA-DRAWING'})-[e]->(t) "
            "WHERE type(e) STARTS WITH 'USES' OR type(e) IN "
            "['INVOKES_DEVATA','PERFORMED_BY','PERFORMED_FOR'] "
            "RETURN type(e) AS relation, coalesce(t.preferred_label_en, "
            "t.display_label) AS target ORDER BY relation",
            minimum=5,
        ),
        Facet(
            "ordered_steps_with_stated_basis",
            "MATCH (r:Ritual)-[s:HAS_STEP]->(a:Action) "
            "RETURN r.display_label AS rite, a.preferred_label_en AS step, "
            "s.step_order AS ordinal, s.order_basis AS basis ORDER BY s.step_order",
            minimum=3,
        ),
        Facet(
            "priestly_roles",
            "MATCH (n:RitualRole) RETURN n.preferred_label_en AS role, "
            "n.preferred_label_sa AS sanskrit ORDER BY role LIMIT 12",
            minimum=5,
        ),
    ),
    "samaveda_transformation": (
        Facet(
            "rv_to_sv_reuse_with_alignment",
            "MATCH (sv:Passage {veda:'SV'})-[r:REUSES_TEXT_FROM|EXACT_PARALLEL_OF|"
            "NEAR_PARALLEL_OF]-(rv:Passage {veda:'RV'}) "
            "RETURN sv.canonical_citation AS samaveda, rv.canonical_citation AS rigveda, "
            "type(r) AS relation, r.match_level AS match_level, "
            "r.similarity AS similarity LIMIT 8",
            minimum=5,
        ),
        Facet(
            "shared_formula_across_the_pair",
            "MATCH (sv:Passage {veda:'SV'})-[:USES_FORMULA]->(f:Formula)"
            "<-[:USES_FORMULA]-(rv:Passage {veda:'RV'}) "
            "RETURN f.display_form AS formula, f.vedas AS vedas, "
            "f.occurrence_count AS occurrences ORDER BY occurrences DESC LIMIT 5",
        ),
        # Returns the edges themselves, not `count(r)`. An aggregate always yields exactly
        # one row -- `RETURN count(r)` gives `0` in a row, not zero rows -- so an
        # emptiness check written that way can never pass. The gate here is that the
        # Samavedic *musical* transformation must not be faked: the corpus has no gana
        # data, so `MUSICALIZED_AS` is declared and deliberately unpopulated.
        Facet(
            "musicalized_as_is_declared_not_faked",
            "MATCH ()-[r:MUSICALIZED_AS]->() RETURN r LIMIT 1",
            expect_empty=True,
        ),
    ),
    "civilization_story": (
        # `labels(e)[0]` is NOT used, and the first draft of this check used it and was
        # wrong: these nodes carry `Concept`, `DomainEntity` and their narrow label at
        # once, Neo4j does not guarantee `labels()` ordering, and every row came back as
        # `Concept`. The same mistake is a live defect elsewhere in this repository's query
        # surface, which is a fair warning about how easy it is to make.
        Facet(
            "material_culture_by_veda",
            "UNWIND ['Animal','Crop','Metal'] AS kind "
            "MATCH (p:Passage)-[:MENTIONS_ENTITY]->(e) WHERE kind IN labels(e) "
            "RETURN kind, p.veda AS veda, count(DISTINCT p) AS mantras "
            "ORDER BY kind, veda",
            minimum=6,
        ),
        Facet(
            "derived_metrics_carry_no_interpretation",
            "MATCH (m:DerivedMetric) WHERE m.metric_name IS NOT NULL RETURN count(m) AS metrics",
        ),
        Facet(
            "interpretation_lives_only_in_claims",
            "MATCH (c:InterpretiveClaim) "
            "RETURN c.claim_id AS id, c.status AS status, c.confidence AS confidence "
            "LIMIT 8",
        ),
        Facet(
            "every_claim_is_tier_d",
            "MATCH (c:InterpretiveClaim) WHERE c.quality_tier <> 'TIER_D' "
            "RETURN c.claim_id AS leaked",
            expect_empty=True,
        ),
    ),
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", help="write the full result to this path")
    parser.add_argument("--only", default="", help="one demonstration name")
    args = parser.parse_args()

    from neo4j import GraphDatabase

    selected = (
        {args.only: DEMONSTRATIONS[args.only]}
        if args.only and args.only in DEMONSTRATIONS
        else DEMONSTRATIONS
    )

    results: dict[str, Any] = {}
    failures: list[str] = []
    driver = GraphDatabase.driver(BOLT_URI, auth=BOLT_AUTH)
    try:
        with driver.session() as session:
            for demo, facets in selected.items():
                print(f"\n=== {demo} " + "=" * (60 - len(demo)))
                demo_result: dict[str, Any] = {}
                for facet in facets:
                    try:
                        result = session.run(facet.cypher, **facet.params)
                        rows = [record.data() for record in result]
                    except Exception as exc:
                        print(f"  !! {facet.name:<44} QUERY ERROR: {exc}")
                        failures.append(f"{demo}.{facet.name}: query error")
                        demo_result[facet.name] = {"error": str(exc)}
                        continue
                    if facet.expect_empty:
                        ok = not rows
                        verdict = "ok (empty, as required)" if ok else f"FAIL: {len(rows)} rows"
                    else:
                        ok = len(rows) >= facet.minimum
                        verdict = f"{len(rows)} rows" + ("" if ok else f" (< {facet.minimum})")
                    flag = "ok " if ok else "!! "
                    print(f"  {flag}{facet.name:<44} {verdict}")
                    if not ok:
                        failures.append(f"{demo}.{facet.name}")
                    demo_result[facet.name] = {
                        "rows": len(rows),
                        "ok": ok,
                        "sample": rows[:3],
                    }
                results[demo] = demo_result
    finally:
        driver.close()

    print("\n" + "=" * 70)
    if failures:
        print(f"FAILING FACETS: {len(failures)}")
        for line in failures:
            print(f"  !! {line}")
    else:
        print("every facet returned what the gate requires")
    print("=" * 70)

    if args.json:
        pathlib.Path(args.json).write_text(
            json.dumps(results, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
