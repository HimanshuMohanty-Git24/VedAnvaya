"""Generate supplementary/fact_freeze.json: the single measured fact set the
manuscript cites.

Every project-specific number in the paper is read from this file, so that no two
sections can quote different values for the same quantity. Re-run it and diff:

    python figures-src/fact_freeze.py

Read-only with respect to the product: it issues MATCH/RETURN Cypher and reads
repository files. It writes only inside paper/vedgraph-agentic-kg/supplementary/.
"""

from __future__ import annotations

import json
import os
import statistics
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import yaml
from dotenv import load_dotenv
from neo4j import GraphDatabase

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parents[1] / "supplementary" / "fact_freeze.json"

# Two pipeline generations wrote the epistemic-layer field with and without the
# L-prefix. Folding them is a reporting decision, recorded here rather than hidden:
# the raw distribution is emitted alongside the folded one.
LAYER_FOLD = {
    "L1_SOURCE_EXPLICIT": "L1_SOURCE_EXPLICIT",
    "SOURCE_EXPLICIT": "L1_SOURCE_EXPLICIT",
    "L2_DETERMINISTIC_DERIVED": "L2_DETERMINISTIC_DERIVED",
    "DETERMINISTIC_DERIVED": "L2_DETERMINISTIC_DERIVED",
    "L3_LLM_EXTRACTED": "L3_LLM_EXTRACTED",
    "L4_INTERPRETIVE_CLAIM": "L4_INTERPRETIVE_CLAIM",
}
WORK_ABBR = {
    "VG:WORK:RV:SAK": "RV",
    "VG:WORK:SV:KAU": "SV",
    "VG:WORK:YV:VSM": "YV",
    "VG:WORK:AV:SAU": "AV",
}
REUSE_TYPES = [
    "EXACT_PARALLEL_OF",
    "NEAR_PARALLEL_OF",
    "VARIANT_OF",
    "REUSES_TEXT_FROM",
    "HAS_PARALLEL_PADA",
    "PARALLEL_TO",
]


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def main() -> int:
    load_dotenv(ROOT / ".env")
    driver = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
    )

    def q(cypher: str) -> list[dict]:
        with driver.session(database=os.environ.get("NEO4J_DATABASE", "neo4j")) as s:
            return s.run(cypher).data()

    def one(cypher: str) -> int:
        return int(q(cypher)[0]["v"])

    f: dict[str, object] = {}
    f["provenance"] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_commit": git("rev-parse", "HEAD"),
        "git_commit_short": git("rev-parse", "--short", "HEAD"),
        "git_branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "git_tree_clean": git("status", "--porcelain") == "",
        "commit_count": int(git("rev-list", "--count", "HEAD")),
        "first_commit_date": git(
            "log", "--reverse", "--format=%ad", "--date=short"
        ).split("\n")[0],
        "head_commit_date": git("log", "-1", "--format=%ad", "--date=short"),
    }

    # ---- graph scale -------------------------------------------------------
    rel_total = one("MATCH ()-[r]->() RETURN count(r) AS v")
    f["graph"] = {
        "nodes_total": one("MATCH (n) RETURN count(n) AS v"),
        "relationships_total": rel_total,
        # Declared and in-use differ: the store keeps a label in its token table
        # after the last node carrying it is deleted. Both are reported because
        # quoting only the declared count would overstate the ontology in use.
        "node_labels_declared": one(
            "CALL db.labels() YIELD label RETURN count(*) AS v"
        ),
        "node_labels_in_use": one(
            "MATCH (n) UNWIND labels(n) AS l RETURN count(DISTINCT l) AS v"
        ),
        "node_labels_declared_but_empty": [
            r["label"]
            for r in q(
                "CALL db.labels() YIELD label "
                "WHERE NOT EXISTS { MATCH (n) WHERE label IN labels(n) } "
                "RETURN label ORDER BY label"
            )
        ],
        "relationship_types_declared": one(
            "CALL db.relationshipTypes() YIELD relationshipType RETURN count(*) AS v"
        ),
        "relationship_types_in_use": one(
            "MATCH ()-[r]->() RETURN count(DISTINCT type(r)) AS v"
        ),
        "public_nodes": one("MATCH (n) WHERE NOT n:Internal RETURN count(n) AS v"),
        "internal_nodes": one("MATCH (n:Internal) RETURN count(n) AS v"),
        "node_labels": {
            r["l"]: r["n"]
            for r in q(
                "MATCH (n) UNWIND labels(n) AS l "
                "RETURN l, count(*) AS n ORDER BY n DESC"
            )
        },
        "relationship_types": {
            r["t"]: r["n"]
            for r in q(
                "MATCH ()-[r]->() RETURN type(r) AS t, count(*) AS n ORDER BY n DESC"
            )
        },
    }

    # ---- corpus ------------------------------------------------------------
    mantras = {
        WORK_ABBR.get(r["w"], r["w"]): r["n"]
        for r in q("MATCH (m:Mantra) RETURN m.work_id AS w, count(*) AS n")
    }
    f["corpus"] = {
        "mantras_by_work": mantras,
        "mantras_total": sum(mantras.values()),
        "passages_total": one("MATCH (p:Passage) RETURN count(p) AS v"),
        "works": one("MATCH (w:Work) RETURN count(w) AS v"),
        "text_versions": one("MATCH (t:TextVersion) RETURN count(t) AS v"),
        "excluded_corpora": {
            WORK_ABBR.get(r["w"], r["w"]): r["x"]
            for r in q(
                "MATCH (w:Work) RETURN w.work_id AS w, w.excluded_corpora AS x"
            )
        },
    }

    # ---- epistemic typing --------------------------------------------------
    raw_rel = {
        str(r["v"]): r["n"]
        for r in q(
            "MATCH ()-[r]->() RETURN r.knowledge_layer AS v, count(*) AS n"
        )
    }
    folded: Counter = Counter()
    for k, n in raw_rel.items():
        folded[LAYER_FOLD.get(k, "UNLABELLED")] += n
    f["epistemic"] = {
        "relationship_knowledge_layer_raw": raw_rel,
        "relationship_knowledge_layer_folded": dict(folded),
        "relationship_knowledge_layer_pct": {
            k: round(100.0 * v / rel_total, 3) for k, v in folded.items()
        },
        "relationship_quality_tier": {
            str(r["v"]): r["n"]
            for r in q(
                "MATCH ()-[r]->() RETURN r.quality_tier AS v, count(*) AS n"
            )
        },
        "quality_tier_coverage_pct": round(
            100.0
            * one(
                "MATCH ()-[r]->() WHERE r.quality_tier IS NOT NULL "
                "RETURN count(r) AS v"
            )
            / rel_total,
            3,
        ),
        "knowledge_layer_coverage_pct": round(
            100.0
            * one(
                "MATCH ()-[r]->() WHERE r.knowledge_layer IS NOT NULL "
                "RETURN count(r) AS v"
            )
            / rel_total,
            3,
        ),
        "unlabelled_layer_edges_by_type": {
            r["t"]: r["n"]
            for r in q(
                "MATCH ()-[r]->() WHERE r.knowledge_layer IS NULL "
                "RETURN type(r) AS t, count(*) AS n ORDER BY n DESC"
            )
        },
        "attribution_precision": {
            str(r["v"]): r["n"]
            for r in q(
                "MATCH ()-[r]->() "
                "RETURN r.attribution_precision AS v, count(*) AS n ORDER BY n DESC"
            )
        },
        "node_knowledge_layer": {
            str(r["v"]): r["n"]
            for r in q("MATCH (n) RETURN n.knowledge_layer AS v, count(*) AS n")
        },
    }

    # ---- semantic assertion layer -----------------------------------------
    f["semantic"] = {
        "assertions_total": one("MATCH (a:SemanticAssertion) RETURN count(a) AS v"),
        "by_derivation": {
            str(r["v"]): r["n"]
            for r in q(
                "MATCH (a:SemanticAssertion) "
                "RETURN a.derivation AS v, count(*) AS n ORDER BY n DESC"
            )
        },
        "by_knowledge_layer": {
            str(r["v"]): r["n"]
            for r in q(
                "MATCH (a:SemanticAssertion) "
                "RETURN a.knowledge_layer AS v, count(*) AS n ORDER BY n DESC"
            )
        },
        "by_predicate_status": {
            str(r["v"]): r["n"]
            for r in q(
                "MATCH (a:SemanticAssertion) "
                "RETURN a.predicate_status AS v, count(*) AS n ORDER BY n DESC"
            )
        },
        "human_annotated_true": one(
            "MATCH (a:SemanticAssertion) WHERE a.human_annotated = true "
            "RETURN count(a) AS v"
        ),
        "roles_withheld_true": one(
            "MATCH (a:SemanticAssertion) WHERE a.roles_withheld = true "
            "RETURN count(a) AS v"
        ),
        "three_slot_complete_true": one(
            "MATCH (a:SemanticAssertion) WHERE a.three_slot_complete = true "
            "RETURN count(a) AS v"
        ),
        "role_fillers": one("MATCH (n:RoleFiller) RETURN count(n) AS v"),
        "distinct_predicates": one(
            "MATCH (a:SemanticAssertion) WHERE a.predicate IS NOT NULL "
            "RETURN count(DISTINCT a.predicate) AS v"
        ),
    }

    # ---- connection discovery ---------------------------------------------
    f["connections"] = {
        "by_type": {
            t: one("MATCH ()-[r:" + t + "]->() RETURN count(r) AS v")
            for t in REUSE_TYPES
        },
        "cross_work_matrix": {
            t: {
                WORK_ABBR.get(r["s"], r["s"]) + "->" + WORK_ABBR.get(r["t"], r["t"]): r["n"]
                for r in q(
                    "MATCH (a:Mantra)-[:" + t + "]->(b:Mantra) "
                    "RETURN a.work_id AS s, b.work_id AS t, count(*) AS n ORDER BY n DESC"
                )
            }
            for t in REUSE_TYPES[:4]
        },
        "methods": {
            str(r["v"]): r["n"]
            for r in q(
                "MATCH ()-[r]->() WHERE r.method IS NOT NULL "
                "RETURN r.method AS v, count(*) AS n ORDER BY n DESC"
            )
        },
        "formulae": one("MATCH (n:Formula) RETURN count(n) AS v"),
        "formula_families": one("MATCH (n:FormulaFamily) RETURN count(n) AS v"),
        "formula_occurrences": one("MATCH ()-[r:USES_FORMULA]->() RETURN count(r) AS v"),
        "pada_parallel_groups": one("MATCH (n:PadaParallelGroup) RETURN count(n) AS v"),
        "lemmas": one("MATCH (n:Lemma) RETURN count(n) AS v"),
        "lemma_mentions": one("MATCH ()-[r:MENTIONS_LEMMA]->() RETURN count(r) AS v"),
    }

    # ---- translation -------------------------------------------------------
    f["translation"] = {
        "translation_nodes": one("MATCH (t:Translation) RETURN count(t) AS v"),
        "mantras_with_translation_by_work": {
            WORK_ABBR.get(r["w"], r["w"]): r["n"]
            for r in q(
                "MATCH (m:Mantra)-[:HAS_TRANSLATION]->() "
                "RETURN m.work_id AS w, count(DISTINCT m) AS n"
            )
        },
        "by_alignment_level": {
            str(r["v"]): r["n"]
            for r in q(
                "MATCH (t:Translation) "
                "RETURN t.alignment_level AS v, count(*) AS n ORDER BY n DESC"
            )
        },
        "by_quality_status": {
            str(r["v"]): r["n"]
            for r in q(
                "MATCH (t:Translation) "
                "RETURN t.quality_status AS v, count(*) AS n ORDER BY n DESC"
            )
        },
        "by_translator": {
            str(r["tr"]) + " (" + str(r["y"]) + ", " + str(r["l"]) + ")": r["n"]
            for r in q(
                "MATCH (t:Translation) RETURN t.translator AS tr, t.year AS y, "
                "t.language AS l, count(*) AS n ORDER BY n DESC"
            )
        },
        "import_batches": {
            str(r["v"]): r["n"]
            for r in q(
                "MATCH (t:Translation) WHERE t.import_batch IS NOT NULL "
                "RETURN t.import_batch AS v, count(*) AS n ORDER BY n DESC"
            )
        },
        # "Coverage is a kind, not a boolean": the terminal per-verse state is
        # written onto every one of the 20,210 mantras, so an absence is always
        # accompanied by the reason for it.
        "verse_coverage_state": {
            str(r["s"]) + "|" + WORK_ABBR.get(r["w"], str(r["w"])): r["n"]
            for r in q(
                "MATCH (m:Mantra) RETURN m.translation_coverage_state AS s, "
                "m.work_id AS w, count(*) AS n ORDER BY n DESC"
            )
        },
        "verse_coverage_state_totals": {
            str(r["s"]): r["n"]
            for r in q(
                "MATCH (m:Mantra) RETURN m.translation_coverage_state AS s, "
                "count(*) AS n ORDER BY n DESC"
            )
        },
    }

    # ---- attribution -------------------------------------------------------
    attribution: dict[str, object] = {}
    for rel in ["HAS_DEVATA", "HAS_RISHI", "HAS_CHANDAS", "MENTIONS_DEVATA"]:
        attribution[rel] = {
            WORK_ABBR.get(r["w"], r["w"]) + ":" + str(r["p"]): r["n"]
            for r in q(
                "MATCH (p)-[r:" + rel + "]->() WHERE p.work_id IS NOT NULL "
                "RETURN p.work_id AS w, r.attribution_precision AS p, count(*) AS n "
                "ORDER BY n DESC"
            )
        }
    attribution["entity_counts"] = {
        lab: one("MATCH (n:" + lab + ") RETURN count(n) AS v")
        for lab in [
            "Devata",
            "Rishi",
            "Chandas",
            "RishiFamily",
            "DevataAscription",
            "Concept",
            "DomainEntity",
        ]
    }
    f["attribution"] = attribution

    # ---- Samaveda notation (the deep case study) --------------------------
    f["samaveda_notation"] = {
        "disposition": {
            str(r["v"]): r["n"]
            for r in q(
                "MATCH (m:Mantra {work_id:'VG:WORK:SV:KAU'}) "
                "RETURN m.samavedic_notation_state AS v, count(*) AS n ORDER BY n DESC"
            )
        },
        "withheld_classes": {
            str(r["v"]): r["n"]
            for r in q(
                "MATCH (m:Mantra {work_id:'VG:WORK:SV:KAU'}) "
                "WHERE m.samavedic_notation_withheld_class IS NOT NULL "
                "RETURN m.samavedic_notation_withheld_class AS v, count(*) AS n "
                "ORDER BY n DESC"
            )
        },
        "text_versions_by_role": {
            str(r["role"]) + "/accented=" + str(r["acc"]): r["n"]
            for r in q(
                "MATCH (m:Mantra {work_id:'VG:WORK:SV:KAU'})-[:HAS_TEXT_VERSION]->"
                "(t:TextVersion) RETURN t.text_role AS role, t.accented AS acc, "
                "count(*) AS n ORDER BY n DESC"
            )
        },
        # The refusal is itself a stored property, so it is measurable rather
        # than merely asserted in prose.
        "notation_interpreted_into_pitch": {
            str(r["v"]): r["n"]
            for r in q(
                "MATCH (t:TextVersion) "
                "WHERE t.notation_is_interpreted_into_pitch IS NOT NULL "
                "RETURN t.notation_is_interpreted_into_pitch AS v, count(*) AS n"
            )
        },
        "musicalized_as_relationship_exists": bool(
            q(
                "CALL db.relationshipTypes() YIELD relationshipType "
                "WITH collect(relationshipType) AS t "
                "RETURN 'MUSICALIZED_AS' IN t AS present"
            )[0]["present"]
        ),
    }

    # ---- ritual and material culture --------------------------------------
    # This layer is the clearest case for per-edge rather than per-predicate
    # typing: USED_FOR_RITE and PERFORMED_BY each carry claims of two different
    # epistemic kinds, so a predicate-level grade would be wrong for one of them.
    f["ritual"] = {
        "node_counts": {
            lab: one("MATCH (n:" + lab + ") RETURN count(n) AS v")
            for lab in [
                "Ritual", "RitualStep", "RitualRole", "Offering", "Substance",
                "Object", "Plant", "Animal", "Metal", "Weapon", "Crop",
                "SocialRite",
            ]
        },
        "edges_by_predicate_and_layer": {
            str(r["t"]) + "|" + str(r["kl"]): r["n"]
            for r in q(
                "MATCH ()-[r]->() WHERE type(r) IN ['HAS_RITUAL_STEP',"
                "'USED_FOR_RITE','PERFORMS_ACTION','RECEIVES_OFFERING',"
                "'USES_OBJECT','USES_SUBSTANCE','INVOLVES_OFFERING',"
                "'INVOLVES_RITUAL','PERFORMED_BY','PERFORMED_FOR',"
                "'USES_OFFERING','HAS_STEP','INVOLVES_SUBSTANCE'] "
                "RETURN type(r) AS t, r.knowledge_layer AS kl, count(*) AS n "
                "ORDER BY n DESC"
            )
        },
    }

    # ---- invariant state, measured rather than quoted ----------------------
    # An earlier draft of the manuscript asserted that all twenty live invariants
    # passed, on the authority of the project's release certification. They do not.
    # These are the three that do not read zero, measured here so the paper cannot
    # repeat the mistake.
    f["invariants"] = {
        "edges_without_grade_basis": one(
            "MATCH ()-[r]->() WHERE r.grade_basis IS NULL RETURN count(r) AS v"
        ),
        "edges_without_attribution_precision": one(
            "MATCH ()-[r]->() WHERE r.attribution_precision IS NULL "
            "RETURN count(r) AS v"
        ),
        "assertions_without_predicate_edge": one(
            "MATCH (a:SemanticAssertion) WHERE NOT (a)-[:ASSERTION_PREDICATE]->() "
            "RETURN count(a) AS v"
        ),
        "ungraded_edges": one(
            "MATCH ()-[r]->() WHERE r.quality_tier IS NULL RETURN count(r) AS v"
        ),
        "unlabelled_nodes": one(
            "MATCH (n) WHERE size(labels(n)) = 0 RETURN count(n) AS v"
        ),
        # The untyped residue is not merely untyped: it is graded.
        "untyped_layer_edges_by_tier": {
            str(r["t"]): r["n"]
            for r in q(
                "MATCH ()-[r]->() WHERE r.knowledge_layer IS NULL "
                "RETURN r.quality_tier AS t, count(*) AS n ORDER BY n DESC"
            )
        },
        # TIER_BY_LAYER is documented as a total bijection. It is not one here.
        "tier_layer_crosstab": {
            str(r["kl"]) + "|" + str(r["qt"]): r["n"]
            for r in q(
                "MATCH ()-[r]->() RETURN r.knowledge_layer AS kl, "
                "r.quality_tier AS qt, count(*) AS n ORDER BY n DESC"
            )
        },
        # The denominator question: edges no extraction method could author.
        "plumbing_edges": one(
            "MATCH ()-[r]->() WHERE type(r) IN ['MENTIONS_LEMMA',"
            "'HAS_TEXT_VERSION','CONTAINS','HAS_TRANSLATION'] RETURN count(r) AS v"
        ),
    }
    f["invariants"]["non_plumbing_edges"] = (
        rel_total - f["invariants"]["plumbing_edges"]  # type: ignore[index]
    )

    # ---- rankings the manuscript asserts ----------------------------------
    # The project's own worst benchmark failure was a sentence in which every
    # figure was real and correctly cited while the comparative words around
    # them asserted a ranking the cited rows did not contain. Every superlative
    # in this paper is therefore resolved here, against the live graph, with the
    # runner-up recorded so the claim can be checked rather than believed.
    f["rankings"] = {
        "undirected_parallel_coverage_by_work": [
            {
                "work": WORK_ABBR.get(r["w"], r["w"]),
                "covered": r["covered"],
                "total": r["total"],
                "pct": round(100.0 * r["covered"] / r["total"], 1),
            }
            for r in q(
                "MATCH (m:Mantra) OPTIONAL MATCH (m)-"
                "[:EXACT_PARALLEL_OF|NEAR_PARALLEL_OF|VARIANT_OF|REUSES_TEXT_FROM]"
                "-(o:Mantra) WITH m.work_id AS w, m, count(o) AS c "
                "RETURN w, sum(CASE WHEN c>0 THEN 1 ELSE 0 END) AS covered, "
                "count(m) AS total ORDER BY 1.0*covered/count(m) DESC"
            )
        ],
        # The compilation-asymmetry measure is a ratio over a containing unit, so
        # the units have to be comparable. They are not, and this is the figure
        # that refuses every Yajurvedic pair.
        # Computed in Python rather than in Cypher: for an even-sized population
        # the median is the mean of the two middle values, and indexing the
        # collected list gives the upper one (45 rather than 44 for the
        # Yajurveda, which is the figure the repository states).
        "median_containing_unit_size": {
            WORK_ABBR.get(r["w"], r["w"]): statistics.median(r["sizes"])
            for r in q(
                "MATCH (parent:Passage)-[:CONTAINS]->(m:Mantra) "
                "WITH parent, m.work_id AS w, count(m) AS sz "
                "WITH w, collect(sz) AS sizes RETURN w, sizes"
            )
            if r["w"] in WORK_ABBR
        },
        # The modal Samavedic containing unit, quoted in the reuse-direction
        # argument. Reported as a count rather than by its traditional name,
        # because the name for a unit of this size is contested.
        "samaveda_containing_units": {
            "total": one(
                "MATCH (p:Passage)-[:CONTAINS]->(:Mantra {work_id:'VG:WORK:SV:KAU'}) "
                "RETURN count(DISTINCT p) AS v"
            ),
            "holding_exactly_three_verses": one(
                "MATCH (p:Passage)-[:CONTAINS]->(m:Mantra {work_id:'VG:WORK:SV:KAU'}) "
                "WITH p, count(m) AS sz WHERE sz = 3 RETURN count(p) AS v"
            ),
        },
        "most_dedicated_deity_top5": [
            {"deity": r["d"], "has_devata_edges": r["n"]}
            for r in q(
                "MATCH ()-[:HAS_DEVATA]->(dv:Devata) "
                "RETURN dv.display_label AS d, count(*) AS n ORDER BY n DESC LIMIT 5"
            )
        ],
    }

    # ---- review state, and the corpus no external annotation reaches ------
    f["review"] = {
        "edge_review_state": {
            str(r["v"]): r["n"]
            for r in q(
                "MATCH ()-[r]->() WHERE r.review_state IS NOT NULL "
                "RETURN r.review_state AS v, count(*) AS n ORDER BY n DESC"
            )
        },
        "edges_with_human_review_provenance": sum(
            one(
                "MATCH ()-[r]->() WHERE r." + prop + " = 'HUMAN_REVIEWED' "
                "RETURN count(r) AS v"
            )
            for prop in ["provenance_class", "trust", "knowledge_layer",
                         "annotation_provenance"]
        ),
        "nodes_flagged_human_gold": one(
            "MATCH (n) WHERE n.is_human_gold = true RETURN count(n) AS v"
        ),
        "quality_verdicts_with_not_human_gold_reason": one(
            "MATCH (n:QualityVerdict) WHERE n.not_human_gold_because IS NOT NULL "
            "RETURN count(n) AS v"
        ),
        # Enrichment edges on the Samaveda: every outgoing edge from an SV mantra
        # other than text-version, translation and containment plumbing. Quoted in
        # the text as the population no external annotation can reach.
        "samaveda_enrichment_edges": one(
            "MATCH (m:Mantra {work_id:'VG:WORK:SV:KAU'})-[r]->() "
            "WHERE NOT type(r) IN "
            "['HAS_TEXT_VERSION','HAS_TRANSLATION','CONTAINS'] "
            "RETURN count(r) AS v"
        ),
    }

    # ---- repository-side facts --------------------------------------------
    reg = json.loads((ROOT / "data" / "gap_registry.json").read_text(encoding="utf-8"))
    gaps = reg["gaps"]
    f["gap_registry"] = {
        "entries": len(gaps),
        "by_status": dict(Counter(g["status"] for g in gaps).most_common()),
        "baseline_commit": reg.get("baseline_commit"),
    }

    f["registries"] = {
        "adr_count": len(list((ROOT / "docs" / "decisions").glob("ADR-*.md"))),
        "owner_decision_docs": len(
            list((ROOT / "docs" / "decisions").glob("OWNER_DECISION*.md"))
        ),
        "schema_files": len(list((ROOT / "schemas").glob("*.schema.json"))),
        "scripts": len(list((ROOT / "scripts").glob("*.py"))),
        "report_docs": len(list((ROOT / "docs" / "reports").rglob("*.md"))),
        "test_files": len(list((ROOT / "tests").rglob("test_*.py"))),
        "staging_campaigns": len(
            [p for p in (ROOT / "data" / "staging").iterdir() if p.is_dir()]
        ),
        "prompt_files": len(list((ROOT / "prompts").glob("*.md"))),
        "registry_yaml_files": len(list((ROOT / "data" / "registry").glob("*.yaml"))),
    }

    # Source and rights registries are keyed maps; count their entries.
    for name, path in [
        ("sources", ROOT / "data" / "registry" / "sources.yaml"),
        ("rights", ROOT / "data" / "registry" / "rights.yaml"),
        ("text_versions", ROOT / "data" / "registry" / "text_versions.yaml"),
    ]:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        f["registries"][name + "_entries"] = _count(loaded)  # type: ignore[index]

    driver.close()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(f, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
    )
    print("wrote " + str(OUT))
    summary = {
        "nodes": f["graph"]["nodes_total"],  # type: ignore[index]
        "rels": f["graph"]["relationships_total"],  # type: ignore[index]
        "mantras": f["corpus"]["mantras_total"],  # type: ignore[index]
        "commit": f["provenance"]["git_commit_short"],  # type: ignore[index]
        "layers": f["epistemic"]["relationship_knowledge_layer_pct"],  # type: ignore[index]
    }
    print(json.dumps(summary, indent=2))
    return 0


def _count(obj: object) -> int:
    """Entry count for a registry document, whichever shape it uses."""
    if isinstance(obj, list):
        return len(obj)
    if isinstance(obj, dict):
        for value in obj.values():
            if isinstance(value, (list, dict)):
                return len(value)
        return len(obj)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
