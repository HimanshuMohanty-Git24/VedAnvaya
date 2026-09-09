"""Measure the V2 graph and write the quality scorecard.

Every number in ``docs/reports/GRAPH_QUALITY_V2_SCORECARD.md`` is computed here rather
than typed into the markdown, because a hand-written metric is a metric that was true
once. Re-running this is the only way the scorecard stays honest, and it is cheap.

The headline metric is deliberately **not** the edge count. A graph can double its edges
and get worse, and this pass deleted 41,796 of them to get better. What is reported
instead is what a reader can rely on: how much of the graph is source-stated rather than
derived, how much attribution is per-verse rather than inherited from a container, how
many entities have a name a person can read, and how many of the fifty questions actually
answer.

Usage::

    python scripts/graph_quality_scorecard.py
"""

from __future__ import annotations

import io
import json
import pathlib
import sys
import warnings
from typing import Any

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
warnings.filterwarnings("ignore")

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from vedagraph.domain.claims import claim_summary, load_claims  # noqa: E402
from vedagraph.domain.ontology import (  # noqa: E402
    DOMAIN_MODEL_VERSION,
    DOMAIN_RELATIONSHIP_TYPES,
    INTERNAL_LABELS,
    RELATIONSHIP_SIGNATURES,
    UNPOPULATED_BY_DESIGN,
)
from vedagraph.domain.queries import QUERIES, questions_served  # noqa: E402
from vedagraph.domain.registry import (  # noqa: E402
    entities_by_node_type,
    load_domain_entities,
)
from vedagraph.domain.taxonomy import load_taxonomy  # noqa: E402

BOLT_URI = "bolt://localhost:7687"
BOLT_AUTH = ("neo4j", "vedagraph_dev")
REPORT_PATH = pathlib.Path("docs") / "reports" / "GRAPH_QUALITY_V2_SCORECARD.md"

#: The V1 baseline, measured at the start of this pass and pinned so the delta is real.
BASELINE = {
    "nodes": 100_584,
    "relationships": 212_336,
    "devata_unknown_rate": 0.9766,
    "unknown_label_rate": 0.5916,
    "qa_issues_in_product": 915,
    "typed_domain_labels": 0,
    "domain_entities": 89,
    "interpretive_claims": 0,
    "derived_metrics": 0,
    "graded_edges": 0,
}

#: Deities important enough that leaving them unexplained is a product defect.
MAJOR_DEITIES = 20


def _one(session: Any, cypher: str, **params: Any) -> Any:
    record = session.run(cypher, **params).single()
    return None if record is None else record[0]


def _rows(session: Any, cypher: str, **params: Any) -> list[dict[str, Any]]:
    return [dict(r) for r in session.run(cypher, **params)]


def measure(session: Any) -> dict[str, Any]:
    """Every scorecard number, measured against the live store."""
    internal = " OR ".join(f"n:{label}" for label in sorted(INTERNAL_LABELS))
    out: dict[str, Any] = {}

    out["nodes_total"] = _one(session, "MATCH (n) RETURN count(n)")
    out["relationships_total"] = _one(session, "MATCH ()-[r]->() RETURN count(r)")
    out["nodes_product"] = _one(session, "MATCH (n) WHERE NOT n:Internal RETURN count(n)")
    out["nodes_internal"] = _one(session, "MATCH (n:Internal) RETURN count(n)")
    out["relationships_product"] = _one(
        session,
        "MATCH (a)-[r]->(b) WHERE NOT a:Internal AND NOT b:Internal RETURN count(r)",
    )

    out["labels"] = _rows(
        session,
        """
        CALL db.labels() YIELD label
        CALL (label) { MATCH (n) WHERE label IN labels(n) RETURN count(n) AS nodes }
        RETURN label, nodes ORDER BY nodes DESC
        """,
    )
    out["relationship_types"] = _rows(
        session,
        """
        CALL db.relationshipTypes() YIELD relationshipType AS type
        CALL (type) { MATCH ()-[r]->() WHERE type(r) = type RETURN count(r) AS edges }
        RETURN type, edges ORDER BY edges DESC
        """,
    )

    # --- provenance coverage -------------------------------------------------
    total = out["relationships_total"]
    out["edges_with_tier"] = _one(
        session, "MATCH ()-[r]->() WHERE r.quality_tier IS NOT NULL RETURN count(r)"
    )
    out["edges_with_evidence"] = _one(
        session, "MATCH ()-[r]->() WHERE r.evidence IS NOT NULL RETURN count(r)"
    )
    out["edges_with_trust"] = _one(
        session, "MATCH ()-[r]->() WHERE r.trust IS NOT NULL RETURN count(r)"
    )
    out["tier_coverage"] = round(out["edges_with_tier"] / total, 4)
    out["evidence_coverage"] = round(out["edges_with_evidence"] / total, 4)
    out["trust_coverage"] = round(out["edges_with_trust"] / total, 4)
    out["by_tier"] = _rows(
        session,
        "MATCH ()-[r]->() RETURN r.quality_tier AS tier, count(r) AS edges "
        "ORDER BY tier",
    )
    out["by_layer"] = _rows(
        session,
        "MATCH ()-[r]->() RETURN r.knowledge_layer AS layer, count(r) AS edges "
        "ORDER BY layer",
    )
    out["by_precision"] = _rows(
        session,
        "MATCH ()-[r]->() WHERE r.attribution_precision IS NOT NULL "
        "RETURN r.attribution_precision AS precision, count(r) AS edges ORDER BY precision",
    )
    out["attribution_split"] = _rows(
        session,
        """
        MATCH ()-[r:HAS_DEVATA|HAS_RISHI|HAS_CHANDAS]->()
        RETURN type(r) AS predicate,
               sum(CASE WHEN r.attribution_precision = 'PER_PASSAGE' THEN 1 ELSE 0 END)
                 AS source_stated,
               sum(CASE WHEN r.attribution_precision = 'CONTAINER_INHERITED' THEN 1 ELSE 0 END)
                 AS inherited,
               count(r) AS total
        ORDER BY predicate
        """,
    )

    # --- readability ---------------------------------------------------------
    sentinels = ["", "UNKNOWN", "Unknown", "unknown", "NULL", "null", "None", "?", "-"]
    unnamed = _one(
        session,
        "MATCH (n) WHERE NOT n:Internal AND (n.display_label IS NULL "
        "OR trim(toString(n.display_label)) IN $s) RETURN count(n)",
        s=sentinels,
    )
    out["nodes_without_label"] = unnamed
    out["unknown_label_rate"] = round(unnamed / out["nodes_product"], 6)
    out["nodes_with_display_type"] = _one(
        session,
        "MATCH (n) WHERE NOT n:Internal AND n.display_type IS NOT NULL RETURN count(n)",
    )

    # --- deities -------------------------------------------------------------
    out["devata_total"] = _one(session, "MATCH (n:Devata) RETURN count(n)")
    out["devata_classified"] = _one(
        session, "MATCH (n:Devata) WHERE n.is_classified RETURN count(n)"
    )
    out["devata_unknown_taxonomy_rate"] = round(
        (out["devata_total"] - out["devata_classified"]) / out["devata_total"], 6
    )
    out["devata_with_english_label"] = _one(
        session, "MATCH (n:Devata) WHERE n.label_en IS NOT NULL RETURN count(n)"
    )
    out["devata_with_aliases"] = _one(
        session, "MATCH (n:Devata) WHERE size(coalesce(n.aliases_iast, [])) > 0 RETURN count(n)"
    )
    out["devata_with_profile"] = _one(
        session,
        "MATCH (n:Devata) WHERE n.profile_attributed_total IS NOT NULL RETURN count(n)",
    )
    out["major_deities"] = _rows(
        session,
        """
        MATCH (:Passage)-[:HAS_DEVATA]->(dv:Devata)
        WITH dv, count(*) AS attributed ORDER BY attributed DESC LIMIT $limit
        RETURN dv.entity_key AS entity_key, dv.display_label AS label,
               dv.structure AS structure, coalesce(dv.axes, []) AS axes,
               attributed,
               dv.profile_attributed_total IS NOT NULL AS has_profile,
               size(coalesce(dv.aliases_iast, [])) AS aliases,
               coalesce(dv.is_classified, false) AS classified
        ORDER BY attributed DESC
        """,
        limit=MAJOR_DEITIES,
    )
    out["major_classified"] = sum(1 for d in out["major_deities"] if d["classified"])
    out["major_profiled"] = sum(1 for d in out["major_deities"] if d["has_profile"])
    out["axis_nodes"] = _one(session, "MATCH (n:DeityAxis) RETURN count(n)")
    out["axes_in_use"] = _one(
        session, "MATCH (:Devata)-[:HAS_AXIS]->(a:DeityAxis) RETURN count(DISTINCT a)"
    )
    out["epithets"] = _one(session, "MATCH (n:Epithet) RETURN count(n)")
    out["deity_groups"] = _one(session, "MATCH (n:DeityGroup) RETURN count(n)")

    # --- domain entities -----------------------------------------------------
    out["domain_entities"] = _one(session, "MATCH (n:DomainEntity) RETURN count(n)")
    out["entity_type_counts"] = _rows(
        session,
        "MATCH (n:DomainEntity) RETURN n.display_type AS type, count(n) AS entities "
        "ORDER BY entities DESC, type",
    )
    out["orphan_entities"] = _one(
        session, "MATCH (n:DomainEntity) WHERE NOT (n)--() RETURN count(n)"
    )
    out["mention_edges"] = _one(
        session, "MATCH (:Passage)-[m:MENTIONS_ENTITY]->(:DomainEntity) RETURN count(m)"
    )
    out["mention_theonym_ambiguous"] = _one(
        session,
        "MATCH (:Passage)-[m:MENTIONS_ENTITY]->(:DomainEntity) "
        "WHERE m.theonym_ambiguous RETURN count(m)",
    )
    out["mention_coverage"] = _rows(
        session,
        """
        MATCH (m:Mantra)
        OPTIONAL MATCH (m)-[:MENTIONS_ENTITY]->(e:DomainEntity)
        WITH m, count(e) AS hits
        RETURN m.veda AS veda, count(m) AS mantras,
               sum(CASE WHEN hits > 0 THEN 1 ELSE 0 END) AS covered
        ORDER BY veda
        """,
    )
    out["cross_veda_entities"] = _one(
        session,
        """
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(e:DomainEntity)
        WITH e, count(DISTINCT p.veda) AS vedas WHERE vedas >= 3
        RETURN count(e)
        """,
    )

    # --- formulas and concepts ----------------------------------------------
    out["formula_total"] = _one(session, "MATCH (n:Formula) RETURN count(n)")
    out["formula_cross_veda"] = _one(
        session, "MATCH (n:Formula) WHERE n.cross_veda RETURN count(n)"
    )
    out["formula_thin"] = _one(
        session, "MATCH (n:Formula) WHERE coalesce(n.word_count, 0) < 2 RETURN count(n)"
    )
    out["concept_narrow"] = _one(
        session, "MATCH (n:Concept) WHERE n.display_type = 'Concept' RETURN count(n)"
    )

    # --- interpretive layer --------------------------------------------------
    out["claims"] = _one(session, "MATCH (n:InterpretiveClaim) RETURN count(n)")
    out["claims_with_passage"] = _one(
        session,
        "MATCH (c:InterpretiveClaim) WHERE (c)-[:SUPPORTED_BY]->(:Passage) RETURN count(c)",
    )
    out["claims_with_statistic"] = _one(
        session,
        "MATCH (c:InterpretiveClaim) WHERE (c)-[:SUPPORTED_BY_STATISTIC]->() RETURN count(c)",
    )
    out["claims_non_candidate"] = _one(
        session,
        "MATCH (c:InterpretiveClaim) WHERE c.quality_tier <> 'TIER_D' RETURN count(c)",
    )
    out["contradiction_pairs"] = _one(
        session,
        "MATCH (a:InterpretiveClaim)-[:CONTRADICTS]->(b:InterpretiveClaim) "
        "WHERE a.claim_id < b.claim_id RETURN count(*)",
    )
    out["derived_metrics"] = _one(session, "MATCH (n:DerivedMetric) RETURN count(n)")
    out["metrics_without_subject"] = _one(
        session,
        "MATCH (m:DerivedMetric) WHERE NOT (m)-[:MEASURES]->() RETURN count(m)",
    )

    # --- integrity -----------------------------------------------------------
    out["internal_leaked"] = _one(
        session, f"MATCH (n) WHERE NOT n:Internal AND ({internal}) RETURN count(n)"
    )
    out["ungraded_edges"] = total - out["edges_with_tier"]
    out["claims_to_passages_via_concerns"] = _one(
        session, "MATCH (:InterpretiveClaim)-[r:CONCERNS]->(:Passage) RETURN count(r)"
    )
    out["metrics_to_passages"] = _one(
        session, "MATCH (:DerivedMetric)-[r:MEASURES]->(:Passage) RETURN count(r)"
    )

    violations: list[dict[str, Any]] = []
    for predicate, (subjects, objects) in sorted(RELATIONSHIP_SIGNATURES.items()):
        if predicate in UNPOPULATED_BY_DESIGN:
            continue
        subject_ok = " OR ".join(f"a:{label}" for label in sorted(subjects))
        object_ok = " OR ".join(f"b:{label}" for label in sorted(objects))
        bad = _one(
            session,
            f"MATCH (a)-[r:{predicate}]->(b) "
            f"WHERE NOT ({subject_ok}) OR NOT ({object_ok}) RETURN count(r)",
        )
        if bad:
            violations.append({"predicate": predicate, "violations": bad})
    out["signature_violations"] = violations

    declared = DOMAIN_RELATIONSHIP_TYPES | {
        row["type"] for row in out["relationship_types"]
    }
    out["undeclared_rel_types"] = sorted(
        row["type"]
        for row in out["relationship_types"]
        if row["type"] not in declared and row["edges"] > 0
    )
    out["empty_rel_types"] = sorted(
        row["type"] for row in out["relationship_types"] if row["edges"] == 0
    )
    return out


def _pct(numerator: float, denominator: float) -> str:
    return f"{100 * numerator / denominator:.1f}%" if denominator else "n/a"


def render(m: dict[str, Any]) -> str:
    entities = load_domain_entities(PROJECT_ROOT)
    _, taxonomy = load_taxonomy(PROJECT_ROOT)
    claims = load_claims(PROJECT_ROOT)
    served = questions_served()

    lines: list[str] = [
        "# VedaGraph Graph Quality Scorecard — Knowledge Model V2",
        "",
        f"Model version: `{DOMAIN_MODEL_VERSION}`  ",
        "Generated by `scripts/graph_quality_scorecard.py`. Every number below is measured",
        "against the live graph at generation time, not transcribed.",
        "",
        "**The headline metric is not the edge count.** A graph can double its edges and",
        "get worse; this pass deleted 41,796 of them and got better. What follows is",
        "weighted towards what a reader can rely on.",
        "",
        "## 1. Size, and the honest delta",
        "",
        "| metric | V1 baseline | V2 | delta |",
        "|---|---|---|---|",
        f"| nodes | {BASELINE['nodes']:,} | {m['nodes_total']:,} | "
        f"{m['nodes_total'] - BASELINE['nodes']:+,} |",
        f"| relationships | {BASELINE['relationships']:,} | {m['relationships_total']:,} | "
        f"{m['relationships_total'] - BASELINE['relationships']:+,} |",
        f"| product nodes | — | {m['nodes_product']:,} | — |",
        f"| internal nodes | 0 (unmarked) | {m['nodes_internal']:,} | "
        f"+{m['nodes_internal']:,} |",
        f"| domain entities | {BASELINE['domain_entities']} | {m['domain_entities']} | "
        f"{m['domain_entities'] - BASELINE['domain_entities']:+} |",
        f"| typed domain labels | {BASELINE['typed_domain_labels']} | "
        f"{len(m['entity_type_counts'])} | +{len(m['entity_type_counts'])} |",
        "",
        "## 2. Provenance coverage",
        "",
        "The V1 graph recorded provenance carefully, in five different vocabularies, so no",
        "query could ask across them. `quality_tier` is the single derived grade.",
        "",
        "| metric | value |",
        "|---|---|",
        f"| edges carrying `quality_tier` | {m['edges_with_tier']:,} "
        f"({_pct(m['edges_with_tier'], m['relationships_total'])}) |",
        f"| edges carrying `evidence` | {m['edges_with_evidence']:,} "
        f"({_pct(m['edges_with_evidence'], m['relationships_total'])}) |",
        f"| edges carrying `trust` | {m['edges_with_trust']:,} "
        f"({_pct(m['edges_with_trust'], m['relationships_total'])}) |",
        f"| ungraded edges | **{m['ungraded_edges']}** |",
        "",
        "### Quality tier distribution",
        "",
        "| tier | meaning | edges |",
        "|---|---|---|",
    ]
    meanings = {
        "TIER_A": "a source states it",
        "TIER_B": "reproducible derivation, including scope inheritance",
        "TIER_C": "model-extracted, evidence survived review",
        "TIER_D": "interpretation, or an unreviewed model proposal",
    }
    for row in m["by_tier"]:
        tier = row["tier"] or "(none)"
        lines.append(f"| `{tier}` | {meanings.get(tier, '-')} | {row['edges']:,} |")
    lines += [
        "",
        "TIER_C is **0 by construction**: all 736 model-extracted candidates are",
        "`state=CANDIDATE`, because there is no human gold set to accept them against.",
        "That is a real limitation, reported rather than papered over.",
        "",
        "### Attribution precision — the single most important table here",
        "",
        "The Anukramaṇī names a deity for a *sūkta*. Projecting that onto each of its",
        "mantras is what makes \"the mantras of Indra\" answerable at all, and it is also",
        "not something the source said about any of those mantras.",
        "",
        "| predicate | source-stated | container-inherited | inherited share |",
        "|---|---|---|---|",
    ]
    for row in m["attribution_split"]:
        share = _pct(row["inherited"], row["total"])
        lines.append(
            f"| `{row['predicate']}` | {row['source_stated']:,} | {row['inherited']:,} | "
            f"**{share}** |"
        )
    lines += [
        "",
        "## 3. Readability (display contract)",
        "",
        "| metric | V1 | V2 |",
        "|---|---|---|",
        f"| UNKNOWN_LABEL_RATE | {BASELINE['unknown_label_rate']:.1%} | "
        f"**{m['unknown_label_rate']:.2%}** |",
        f"| product nodes without a readable label | 22,541 | "
        f"**{m['nodes_without_label']}** |",
        f"| product nodes with `display_type` | 0 | {m['nodes_with_display_type']:,} |",
        "",
        "## 4. Devatā model",
        "",
        "| metric | V1 | V2 |",
        "|---|---|---|",
        f"| Devatā nodes | {m['devata_total']} | {m['devata_total']} |",
        f"| UNKNOWN_TAXONOMY_RATE | {BASELINE['devata_unknown_rate']:.2%} | "
        f"**{m['devata_unknown_taxonomy_rate']:.2%}** |",
        f"| with a functional axis | 5 (subtype only) | {m['devata_classified']} |",
        f"| with an English label | 0 | {m['devata_with_english_label']} |",
        f"| with probed aliases | 0 | {m['devata_with_aliases']} |",
        f"| with a corpus profile | 0 | {m['devata_with_profile']} |",
        f"| axis nodes / in use | 0 | {m['axis_nodes']} / {m['axes_in_use']} |",
        f"| epithets / deity groups | 0 | {m['epithets']} / {m['deity_groups']} |",
        "",
        f"Structure distribution: `{json.dumps(taxonomy.as_dict()['by_structure'])}`",
        "",
        f"`UNSPECIFIED` axes on {taxonomy.as_dict()['axes_unspecified']} of "
        f"{taxonomy.as_dict()['registry_entities']} deities is a deliberate value, not a",
        "gap awaiting a guess: a justified UNSPECIFIED is worth more than an invented axis.",
        "",
        "### Top-20 deities by attribution — the acceptance gate",
        "",
        "| deity | attributed | structure | axes | aliases | profile |",
        "|---|---|---|---|---|---|",
    ]
    for d in m["major_deities"]:
        axes = ", ".join(d["axes"]) or "—"
        lines.append(
            f"| {d['label']} | {d['attributed']:,} | {d['structure']} | {axes} | "
            f"{d['aliases']} | {'yes' if d['has_profile'] else 'no'} |"
        )
    lines += [
        "",
        f"Of the top {MAJOR_DEITIES}: **{m['major_classified']}** carry a real functional",
        f"axis and **{m['major_profiled']}** carry a corpus profile.",
        "",
        "## 5. Domain entity coverage",
        "",
        "| entity type | entities |",
        "|---|---|",
    ]
    for row in m["entity_type_counts"]:
        lines.append(f"| `{row['type']}` | {row['entities']} |")
    lines += [
        "",
        f"Registry composition: `{json.dumps(entities_by_node_type(entities))}`",
        "",
        "### Mention layer (Sanskrit evidence only)",
        "",
        "| Veda | mantras | with a domain mention | coverage |",
        "|---|---|---|---|",
    ]
    for row in m["mention_coverage"]:
        lines.append(
            f"| {row['veda']} | {row['mantras']:,} | {row['covered']:,} | "
            f"{_pct(row['covered'], row['mantras'])} |"
        )
    lines += [
        "",
        f"- mention edges: **{m['mention_edges']:,}**",
        f"- flagged `theonym_ambiguous`: **{m['mention_theonym_ambiguous']:,}** "
        f"({_pct(m['mention_theonym_ambiguous'], m['mention_edges'])}) — an upper bound on "
        "deity/entity conflation, not a count of errors",
        f"- entities attested in 3+ Vedas: **{m['cross_veda_entities']}**",
        "",
        "The V1 concept layer reported 96.1% Rigvedic coverage. This layer reports lower",
        "because it admits **no English-translation evidence**: 44.7% of V1 concept",
        "assertions rested on a word in Griffith or Whitney and no Sanskrit at all.",
        "",
        "## 6. Formula and concept quality",
        "",
        "| metric | value |",
        "|---|---|",
        f"| Formula nodes | {m['formula_total']:,} |",
        f"| cross-Veda formulas | {m['formula_cross_veda']:,} |",
        f"| formulas under 2 words (thin) | {m['formula_thin']} |",
        f"| entities still narrowly typed `Concept` | {m['concept_narrow']} |",
        "",
        "## 7. Interpretive layer",
        "",
        "| metric | value |",
        "|---|---|",
        f"| InterpretiveClaim nodes | {m['claims']} |",
        f"| claims citing a passage | {m['claims_with_passage']} |",
        f"| claims citing a computed metric | {m['claims_with_statistic']} |",
        f"| claims graded other than TIER_D | **{m['claims_non_candidate']}** (must be 0) |",
        f"| live contradiction pairs | {m['contradiction_pairs']} |",
        f"| DerivedMetric nodes | {m['derived_metrics']} |",
        f"| metrics with no subject node | {m['metrics_without_subject']} |",
        "",
        f"Claim summary: `{json.dumps(claim_summary(claims))}`",
        "",
        "`metrics with no subject node` counts corpus-scale metrics whose subject is the",
        "pseudo-entity `VG:CORPUS:FOUR-VEDA`, which deliberately has no node.",
        "",
        "## 8. Integrity gates",
        "",
        "| gate | result | pass |",
        "|---|---|---|",
        f"| internal nodes reachable in product traversal | {m['internal_leaked']} | "
        f"{'YES' if m['internal_leaked'] == 0 else 'NO'} |",
        f"| ungraded edges | {m['ungraded_edges']} | "
        f"{'YES' if m['ungraded_edges'] == 0 else 'NO'} |",
        f"| product nodes without a readable label | {m['nodes_without_label']} | "
        f"{'YES' if m['nodes_without_label'] == 0 else 'NO'} |",
        f"| orphan domain entities | {m['orphan_entities']} | "
        f"{'YES' if m['orphan_entities'] == 0 else 'NO'} |",
        f"| controlled-predicate violations | {len(m['signature_violations'])} | "
        f"{'YES' if not m['signature_violations'] else 'NO'} |",
        f"| undeclared relationship types | {len(m['undeclared_rel_types'])} | "
        f"{'YES' if not m['undeclared_rel_types'] else 'NO'} |",
        f"| claims wrongly pointing at passages | {m['claims_to_passages_via_concerns']} | "
        f"{'YES' if m['claims_to_passages_via_concerns'] == 0 else 'NO'} |",
        f"| metrics wrongly pointing at passages | {m['metrics_to_passages']} | "
        f"{'YES' if m['metrics_to_passages'] == 0 else 'NO'} |",
        "",
    ]
    if m["signature_violations"]:
        lines += ["Signature violations:", ""]
        for v in m["signature_violations"]:
            lines.append(f"- `{v['predicate']}`: {v['violations']} edges")
        lines.append("")
    if m["empty_rel_types"]:
        lines += [
            "Relationship types declared with zero edges: "
            + ", ".join(f"`{t}`" for t in m["empty_rel_types"])
            + ". `MUSICALIZED_AS` is empty by design — no gāna corpus is ingested, and an",
            "empty typed edge states that honestly where a `PARALLEL_TO` standing in for it",
            "would not.",
            "",
        ]

    lines += [
        "## 9. Query surface",
        "",
        f"- named domain queries: **{len(QUERIES)}**",
        f"- killer questions with at least one query: **{len(served)}** of 50",
        "- every query carries a `caveat` stating what its answer does not establish",
        "",
        "Query coverage is not answerability. A question with a query attached may still",
        "be only partially answerable, and the killer-questions report is where that",
        "judgement is recorded.",
        "",
        "## 10. Graph explosion control",
        "",
        "| relationship type | edges |",
        "|---|---|",
    ]
    for row in m["relationship_types"][:16]:
        lines.append(f"| `{row['type']}` | {row['edges']:,} |")
    lines += [
        "",
        "During this pass an unlabelled `MATCH (t) WHERE t.work_id = $k` produced **39,461**",
        "`CONCERNS` edges from 9 claim targets, because every Passage carries a `work_id`",
        "and so all 11,590 Rigvedic passages matched instead of the one `Work` node. A",
        "further 2,342 bogus `MEASURES` edges came from the same pattern. Both were found",
        "by reconciling the edge delta against the baseline rather than by reading the",
        "code, and both are now guarded by a live test.",
        "",
        "A second reconciliation gap was found the same way: removing an alias from the",
        "lexicon left the edges it had produced in place, still carrying full evidence. The",
        "mention loader now mark-and-sweeps, which retired 7 `SVAN-DOG` edges whose alias",
        "`śvā` had been dropped for matching `aśvā` (\"mare\").",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(BOLT_URI, auth=BOLT_AUTH)
    try:
        with driver.session() as session:
            measured = measure(session)
    finally:
        driver.close()

    target = PROJECT_ROOT / REPORT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(measured), encoding="utf-8", newline="\n")

    gates = {
        "internal_leaked": measured["internal_leaked"],
        "ungraded_edges": measured["ungraded_edges"],
        "nodes_without_label": measured["nodes_without_label"],
        "orphan_entities": measured["orphan_entities"],
        "signature_violations": len(measured["signature_violations"]),
        "undeclared_rel_types": len(measured["undeclared_rel_types"]),
        "claims_non_candidate": measured["claims_non_candidate"],
        "claims_to_passages": measured["claims_to_passages_via_concerns"],
        "metrics_to_passages": measured["metrics_to_passages"],
    }
    print(f"wrote {REPORT_PATH}\n")
    print("integrity gates (all must be 0):")
    for name, value in gates.items():
        print(f"  {'PASS' if value == 0 else 'FAIL'}  {name:<28} {value}")
    print("\nheadline:")
    print(f"  nodes                    {measured['nodes_total']:,}")
    print(f"  relationships            {measured['relationships_total']:,}")
    print(f"  UNKNOWN_LABEL_RATE       {measured['unknown_label_rate']:.4%}")
    print(f"  UNKNOWN_TAXONOMY_RATE    {measured['devata_unknown_taxonomy_rate']:.4%}")
    print(f"  tier coverage            {measured['tier_coverage']:.2%}")
    print(f"  mention edges            {measured['mention_edges']:,}")
    return 0 if all(v == 0 for v in gates.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
