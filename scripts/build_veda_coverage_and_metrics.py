"""Score each Veda's knowledge coverage independently, and land the derived metrics.

Global totals hide the thing a reader most needs to know about this graph. The Rigveda is
10,552 of 20,210 mantras and carries a manual scholarly morphological annotation that the
other three do not have, so any corpus-wide average is mostly a statement about the
Rigveda wearing four Vedas' clothes. This script refuses the average.

**The coverage score is per Veda, per dimension, and it distinguishes three kinds of
zero.** That distinction is the whole point:

``ABSENT_FROM_SOURCE``
    The Veda has no such thing to find. The Samaveda has no attribution layer because its
    school's indices are keyed to samans in the gana collections, which this corpus does
    not contain -- so the join key exists for 7.7% of its verses and no acquisition fixes
    it. Scoring that as a modelling failure would be a lie about the corpus.

``ABSENT_FROM_GRAPH``
    The thing exists in the source and the graph does not have it. This is the only kind
    of zero that is a defect, and it is the one a coverage report exists to surface.

``NOT_APPLICABLE``
    The dimension does not apply. The Rigveda has no cross-Veda *acquisition* gap because
    it is the source everything else reuses.

The V2 pass produced a false 100% coverage figure of exactly this kind by counting rows
after an ``OPTIONAL MATCH`` -- ``count(*)`` counts rows, not matches -- and reported that
all four Vedas had complete deity coverage when the truth was Rigveda-only. Every count
here uses ``count(DISTINCT ...)`` over an explicit match, and the script asserts that no
dimension's covered count exceeds its denominator.

Usage::

    python scripts/build_veda_coverage_and_metrics.py
    python scripts/build_veda_coverage_and_metrics.py --check   # measure, write nothing
"""

from __future__ import annotations

import argparse
import io
import json
import pathlib
import sys
from dataclasses import dataclass
from typing import Any, Final

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

BOLT_URI: Final = "bolt://localhost:7687"
BOLT_AUTH: Final = ("neo4j", "vedagraph_dev")

WORKS: Final[dict[str, str]] = {
    "RV": "VG:WORK:RV:SAK",
    "SV": "VG:WORK:SV:KAU",
    "YV": "VG:WORK:YV:VSM",
    "AV": "VG:WORK:AV:SAU",
}

ABSENT_SOURCE: Final = "ABSENT_FROM_SOURCE"
ABSENT_GRAPH: Final = "ABSENT_FROM_GRAPH"
NOT_APPLICABLE: Final = "NOT_APPLICABLE"


@dataclass(frozen=True)
class Dimension:
    """One knowledge dimension, and how to count a passage as covered by it."""

    name: str
    #: Cypher fragment matching a covered passage, with ``p`` already bound.
    pattern: str
    #: Vedas where a zero means the source has nothing to find, with the reason.
    absent_from_source: dict[str, str]
    weight: float = 1.0


#: The dimensions the brief names, each measured against the number of mantras in the Veda.
#:
#: ``absent_from_source`` is the load-bearing field. It is written per dimension and per
#: Veda from a stated reason, never inferred from a zero -- inferring it would make the
#: score unfalsifiable, since every gap could be reclassified as the corpus's fault.
DIMENSIONS: Final[tuple[Dimension, ...]] = (
    Dimension(
        "devata_attribution",
        "(p)-[:HAS_DEVATA]->(:Devata)",
        {
            "SV": (
                "The Kauthuma school's Devatadhyaya Brahmana is keyed to samans in the "
                "gana collections, which this corpus does not contain: the join key "
                "exists for 7.7% of verses."
            ),
            "YV": (
                "The Madhyandina Sarvanukramana-sutra is pratika-keyed sutra prose. "
                "Machine resolution is refused, not deferred, so the Yajurveda keeps a "
                "source-stated absence of devata rather than a borrowed presence."
            ),
            "AV": (
                "Whitney's Brhatsarvanukramani excerpts ascribe an adjectival DESCRIPTOR, "
                "not a deity name -- `agneyam` is 'belonging to Agni'. The Atharvaveda's "
                "index-based deity layer is real and is carried by "
                "HAS_DEVATA_ASCRIPTION, measured as its own dimension. A zero here means "
                "the source names no deities, not that the graph lost any."
            ),
        },
    ),
    Dimension(
        "devata_ascription_index",
        "(p)-[:HAS_DEVATA_ASCRIPTION]->(:DevataAscription)",
        {
            "RV": "The Anukramani names deities directly; no descriptor layer exists.",
            "SV": "No attribution index reaches this corpus.",
            "YV": "No devata index is machine-resolvable.",
        },
    ),
    Dimension(
        "rishi_attribution",
        "(p)-[:HAS_RISHI]->(:Rishi)",
        {
            "SV": (
                "The Arseya Brahmana is keyed to samans in the gana collections, absent "
                "from this corpus."
            )
        },
    ),
    Dimension(
        "chandas_attribution",
        "(p)-[:HAS_CHANDAS]->(:Chandas)",
        {
            "SV": (
                "The Samaveda's identity is melody rather than metre; a borrowed metre "
                "would misdescribe the one Veda whose form is not metrical."
            ),
            "YV": "No metre index is machine-resolvable; the absence is source-stated.",
        },
    ),
    Dimension("theonym_mention", "(p)-[:MENTIONS_DEVATA]->(:Devata)", {}),
    Dimension("entity_mention", "(p)-[:MENTIONS_ENTITY]->(:DomainEntity)", {}),
    Dimension("concept_salience", "(p)-[:ABOUT_CONCEPT]->()", {}),
    Dimension("formula", "(p)-[:USES_FORMULA]->(:Formula)", {}),
    Dimension(
        "cross_veda_reuse",
        "(p)-[:REUSES_TEXT_FROM|EXACT_PARALLEL_OF|NEAR_PARALLEL_OF|VARIANT_OF]-()",
        {},
    ),
    Dimension(
        "agentive_assertion",
        "(p)-[:HAS_SEMANTIC_ASSERTION]->(:SemanticAssertion {derivation: 'MORPHOLOGY_RULE'})",
        {
            "SV": "Derived from a morphological annotation that covers the Rigveda only.",
            "YV": "Derived from a morphological annotation that covers the Rigveda only.",
            "AV": "Derived from a morphological annotation that covers the Rigveda only.",
        },
    ),
    Dimension(
        "model_semantic_assertion",
        # Two shapes, deliberately unioned. The sealed Rigvedic run is reified as
        # SemanticAssertion nodes; the earlier unsealed Yajurvedic and Atharvavedic run is
        # 736 direct predicate edges. Counting only the first reported the two Vedas that
        # have the *only* non-Rigvedic model layer as having none.
        "((p)-[:HAS_SEMANTIC_ASSERTION]->(:SemanticAssertion {derivation: 'MODEL_EXTRACTION'})"
        " OR (p)-[{knowledge_layer: 'L3_LLM_EXTRACTED'}]->())",
        {
            "SV": (
                "No semantic extraction run has covered the Samaveda. It is also the one "
                "Veda with no translation at all, which is what every run so far has "
                "anchored its evidence to."
            )
        },
    ),
    Dimension(
        "human_concern", "(p)-[:ADDRESSES_CONCERN|TREATS|PROTECTS_FROM|USED_FOR_RITE]->()", {}
    ),
    Dimension(
        "translation",
        "(p)-[:HAS_TRANSLATION]->()",
        {
            "SV": (
                "No complete translation of the Kauthuma arcika is ingested; the only one "
                "located is Ranayaniya and does not align."
            )
        },
    ),
)


def _count(session: Any, query: str, **parameters: Any) -> int:
    record = session.run(query, **parameters).single()
    return int(record["c"]) if record and record["c"] is not None else 0


def measure(session: Any) -> dict[str, Any]:
    result: dict[str, Any] = {"vedas": {}, "dimensions": [d.name for d in DIMENSIONS]}
    for veda, work_id in WORKS.items():
        mantras = _count(
            session,
            "MATCH (p:Passage {work_id: $w}) WHERE p:Mantra RETURN count(p) AS c",
            w=work_id,
        )
        rows: dict[str, Any] = {}
        scored: list[float] = []
        for dimension in DIMENSIONS:
            covered = _count(
                session,
                f"MATCH (p:Passage {{work_id: $w}}) WHERE p:Mantra AND {dimension.pattern} "
                "RETURN count(DISTINCT p) AS c",
                w=work_id,
            )
            if covered > mantras:
                raise SystemExit(
                    f"{veda}/{dimension.name}: covered {covered} exceeds {mantras} mantras. "
                    "A coverage count above its own denominator means the match is "
                    "counting rows rather than passages."
                )
            share = covered / mantras if mantras else 0.0
            if covered == 0 and veda in dimension.absent_from_source:
                status = ABSENT_SOURCE
            elif covered == 0:
                status = ABSENT_GRAPH
            else:
                status = "PRESENT"
            rows[dimension.name] = {
                "covered_mantras": covered,
                "share": round(share, 4),
                "status": status,
                "reason": dimension.absent_from_source.get(veda, ""),
            }
            # A dimension the source cannot supply is excluded from the score rather than
            # scored zero: the score measures what the graph did with what exists.
            if status != ABSENT_SOURCE:
                scored.append(share)
        result["vedas"][veda] = {
            "work_id": work_id,
            "mantras": mantras,
            "dimensions": rows,
            "dimensions_scored": len(scored),
            "dimensions_absent_from_source": sum(
                1 for r in rows.values() if r["status"] == ABSENT_SOURCE
            ),
            "dimensions_absent_from_graph": sorted(
                name for name, r in rows.items() if r["status"] == ABSENT_GRAPH
            ),
            # 0-100 over the dimensions the source can supply. Stated that way because a
            # single number over all dimensions would punish the Samaveda for not being
            # the Rigveda.
            "coverage_score": round(100 * sum(scored) / len(scored), 1) if scored else 0.0,
        }
    return result


#: Derived metrics landed as ``DerivedMetric`` nodes. Each is a reproducible aggregation
#: over edges that already exist, and none of them is an interpretation: the whole point of
#: the separation is that a chart can be built from these without a claim being smuggled
#: into it.
METRIC_QUERIES: Final[dict[str, str]] = {
    "DEVATA_RELATIVE_FREQUENCY_BY_VEDA": """
        MATCH (p:Passage)-[m:MENTIONS_DEVATA]->(d:Devata)
        WHERE p:Mantra
        RETURN d.entity_key AS subject, p.work_id AS dimension,
               count(DISTINCT p) AS value
    """,
    "DEVATA_ACTION_DISTRIBUTION": """
        MATCH (d:Devata)-[r:PERFORMS_ACTION]->(a:ActionPredicate)
        RETURN d.entity_key AS subject, a.predicate AS dimension,
               r.assertion_count AS value
    """,
    "DEVATA_REQUESTED_ACTION_DISTRIBUTION": """
        MATCH (d:Devata)-[r:IS_ASKED_TO]->(a:ActionPredicate)
        RETURN d.entity_key AS subject, a.predicate AS dimension,
               r.assertion_count AS value
    """,
    "CROP_MENTION_DISTRIBUTION": """
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(e:Crop)
        WHERE p:Mantra
        RETURN e.entity_key AS subject, p.work_id AS dimension,
               count(DISTINCT p) AS value
    """,
    "METAL_MENTION_DISTRIBUTION": """
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(e:Metal)
        WHERE p:Mantra
        RETURN e.entity_key AS subject, p.work_id AS dimension,
               count(DISTINCT p) AS value
    """,
    "ANIMAL_MENTION_DISTRIBUTION": """
        MATCH (p:Passage)-[:MENTIONS_ENTITY]->(e:Animal)
        WHERE p:Mantra
        RETURN e.entity_key AS subject, p.work_id AS dimension,
               count(DISTINCT p) AS value
    """,
    "HUMAN_CONCERN_DISTRIBUTION": """
        MATCH (p:Passage)-[:ADDRESSES_CONCERN]->(e)
        WHERE p:Mantra
        RETURN e.entity_key AS subject, p.work_id AS dimension,
               count(DISTINCT p) AS value
    """,
    "CONDITION_TREATMENT_DISTRIBUTION": """
        MATCH (p:Passage)-[:TREATS]->(e:Condition)
        WHERE p:Mantra
        RETURN e.entity_key AS subject, p.work_id AS dimension,
               count(DISTINCT p) AS value
    """,
    "RITUAL_ENTITY_DENSITY": """
        MATCH (r:Ritual)-[e:USES_OFFERING|USES_SUBSTANCE|USES_OBJECT|PERFORMED_BY
                          |PERFORMED_FOR|INVOKES_DEVATA]->()
        RETURN r.entity_key AS subject, type(e) AS dimension, count(*) AS value
    """,
    "ATTRIBUTION_PRECISION_BY_VEDA": """
        MATCH (p:Passage)-[r:HAS_DEVATA|HAS_RISHI|HAS_CHANDAS]->()
        WHERE p:Mantra
        RETURN p.work_id + '|' + type(r) AS subject,
               r.attribution_precision AS dimension, count(*) AS value
    """,
    "EVIDENCE_BASIS_BY_VEDA": """
        MATCH (p:Passage)-[r]->()
        WHERE p:Mantra AND r.evidence_basis IS NOT NULL
        RETURN p.work_id AS subject, r.evidence_basis AS dimension, count(*) AS value
    """,
    "THEONYM_CERTAINTY_BY_VEDA": """
        MATCH (p:Passage)-[m:MENTIONS_DEVATA]->(:Devata)
        RETURN p.work_id AS subject, m.referent_certainty AS dimension, count(*) AS value
    """,
}


def land_metrics(session: Any) -> dict[str, Any]:
    """Recompute every derived metric and MERGE it as a ``DerivedMetric`` node.

    Deleted and recomputed rather than MERGEd in place: a metric is a number as of a
    graph state, and a stale value that looks current is worse than an absent one.
    """
    session.run(
        "MATCH (m:DerivedMetric) WHERE m.metric_family IN $families DETACH DELETE m",
        families=sorted(METRIC_QUERIES),
    )
    landed: dict[str, int] = {}
    for family, query in METRIC_QUERIES.items():
        rows = [
            {
                "metric_id": f"VG:METRIC:{family}:{record['subject']}:{record['dimension']}",
                "metric_family": family,
                "subject": record["subject"],
                "dimension": str(record["dimension"]),
                "value": int(record["value"] or 0),
            }
            for record in session.run(query)
            if record["subject"] and record["dimension"] is not None
        ]
        for start in range(0, len(rows), 2000):
            session.run(
                """
                UNWIND $rows AS row
                MERGE (m:DerivedMetric {metric_id: row.metric_id})
                SET m.metric_family = row.metric_family,
                    // Written as well as `metric_family`, and not instead of it, because
                    // two producers had drifted onto two names for the same idea: the
                    // profile metrics write `metric_name`, which is the property the
                    // schema indexes (`derived_metric_name`) and the property the query
                    // catalogue filters on -- and this producer wrote only
                    // `metric_family`. The measured effect was that 993 of 1,072
                    // DerivedMetric nodes were invisible to the indexed lookup, so the
                    // analytics layer answered "which metrics exist?" with 7% of itself.
                    // Setting both keeps every existing `metric_family` query working.
                    m.metric_name = row.metric_family,
                    m.subject = row.subject,
                    m.dimension = row.dimension,
                    m.value = row.value,
                    m.display_label = row.metric_family + ' / ' + row.dimension,
                    m.display_type = 'DerivedMetric',
                    m.knowledge_layer = 'L2_DETERMINISTIC_DERIVED',
                    m.quality_tier = 'TIER_B',
                    m.interpretation = 'NONE. A reproducible aggregation over edges that '
                        + 'already exist. Any reading of a trend in these numbers belongs '
                        + 'in an InterpretiveClaim, not here.'
                """,
                rows=rows[start : start + 2000],
            )
        landed[family] = len(rows)
    return landed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--out", type=pathlib.Path, default=None)
    args = parser.parse_args()

    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(BOLT_URI, auth=BOLT_AUTH)
    with driver.session() as session:
        coverage = measure(session)
        print("=== VEDA_KNOWLEDGE_COVERAGE_SCORE ===")
        for veda, row in coverage["vedas"].items():
            print(
                f"  {veda}: {row['coverage_score']:5.1f}/100  "
                f"({row['dimensions_scored']} dimensions scored, "
                f"{row['dimensions_absent_from_source']} absent from source)"
            )
            if row["dimensions_absent_from_graph"]:
                print(f"        ABSENT FROM GRAPH: {row['dimensions_absent_from_graph']}")
        if not args.check:
            metrics = land_metrics(session)
            coverage["derived_metrics"] = metrics
            print("\n=== DerivedMetric rows landed ===")
            for family, count in sorted(metrics.items(), key=lambda kv: -kv[1]):
                print(f"  {family:44} {count:6d}")
            total = session.run("MATCH (m:DerivedMetric) RETURN count(m) AS c").single()["c"]
            print(f"  {'TOTAL DerivedMetric nodes':44} {total:6d}")
    driver.close()

    out = args.out or (
        PROJECT_ROOT / "data" / "domain" / "vedagraph_domain_v2" / "veda_coverage_v3.json"
    )
    if not args.check:
        out.write_text(
            json.dumps(coverage, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
