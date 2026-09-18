#!/usr/bin/env python3
"""Stage GAP-ENTITY_COVERAGE-006: per-entity lexical recall, and the ayas evidence category.

Clause 2 -- the ayas cell
=========================

``ayas`` is named in the Yajurveda at VSM 18.13 and matched by nothing, and that must
**stay** true of the lexical layer. The Devanagari writes the metal sandhi-elided after
``me`` -- avagraha plus ``yas`` -- and the search fold drops the avagraha, leaving the bare
token ``yasca``, which is the relative pronoun in 11 of its 12 corpus occurrences and also
sits inside the ``-ayas ca`` plurals standing in the same line (``girayaśca``,
``parvatāśca``, ``vanaspatayaśca``). Registering an alias for it manufactures false
positives inside the witness verse itself, so the matcher is not touched and the threshold
is not moved.

What was missing is that **the graph could not state the distinction at all**. The product
discloses it well -- the ayas/YV cell returns ``null`` rather than ``0``, carries
``source_witness`` and appears in ``declared_gaps``, and the citation is even resolved live
rather than typed as a literal. But it is resolved by finding the YV verse that names the
most *other* metals, so the graph holds no fact of the form "ayas is attested in the
Yajurveda". Ask the graph directly and the answer is a bare zero.

So one ``ATTESTED_IN`` edge is staged, in the model the layer already uses: 1,266 of these
edges exist, ``knowledge_layer: SOURCE_EXPLICIT``, ``quality_tier: TIER_A``,
``existence_evidence_type: SAMHITA``, and ayas already carries three of them for RV and AV.
The YV one is simply absent. It is **not** a ``MENTIONS_ENTITY`` edge: that predicate means
a lexical match, and fabricating one is what the entry forbids.

Clause 1 -- recall with a sample size
=====================================

No entity carried a measured recall figure, so the size of the shortfall was unknown. Recall
is measured here against the University of Zurich Rigvedic morphological annotation, which
is scholarly ground truth this repository already holds: for an entity whose registered
Sanskrit aliases fold onto annotated lemmas, the annotation gives the mantras that genuinely
contain those lemmas, and the matcher's own ``MENTIONS_ENTITY`` set can be compared against
it.

**Coverage of the measurement is reported, not just its precision.** An entity with no
annotation-resolvable alias is written ``UNMEASURED_NO_ANNOTATION_ANCHOR`` with that reason
rather than skipped, and the Rigveda-only bound is on every row -- the annotation covers
10,552 mantras and none of the other 9,658, so a recall figure here is a Rigvedic figure and
says so. A validator that silently skips is worse than none.

Usage:
    python scripts/r4_stage_entity_recall_and_ayas.py
"""

from __future__ import annotations

import collections
import datetime
import json
import pathlib
import sys
from typing import Any, Final

from neo4j import GraphDatabase, Query

PROJECT_ROOT: Final = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from vedagraph.enrich.concepts import fold_alias  # noqa: E402
from vedagraph.enrich.morphology import fold_annotation, load_annotation  # noqa: E402

OUT: Final = PROJECT_ROOT / "data" / "staging" / "release_blocker_r4" / "entity_006"
URI: Final = "bolt://localhost:7687"
AUTH: Final = ("neo4j", "vedagraph_dev")
DB: Final = "neo4j"
TIMEOUT: Final[float] = 300.0

CONTRACT: Final = "VG:ENTITY_LEXICAL_RECALL:V1"

AYAS: Final = "VG:CONCEPT:AYAS-METAL"
AYAS_WITNESS: Final = "VG:YV:VSM:A18:V013"

#: The edge properties the ATTESTED_IN layer already carries, read off a live sibling edge
#: rather than invented, plus the three fields that record *this* cell's evidence category.
AYAS_EDGE: Final[dict[str, Any]] = {
    "knowledge_layer": "SOURCE_EXPLICIT",
    "samhita_attested": True,
    "bucket": "YV",
    "attestation_basis": "source_enumeration_read_verbatim",
    "existence_evidence_type": "SAMHITA",
    "quality_tier": "TIER_A",
    # The distinction the entry asks for, stated on the edge.
    "source_attested": True,
    "lexical_match": "NOT_SAFELY_RECOVERABLE",
    "lexical_nonrecovery_reason": (
        "The Devanagari writes the metal sandhi-elided after 'me' as avagraha plus yas. The "
        "search fold drops the avagraha, leaving the bare token 'yasca', which is the "
        "relative pronoun in 11 of its 12 corpus occurrences and also sits inside the "
        "-ayas ca plurals in this same line (girayasca, parvatasca, vanaspatayasca). "
        "Registering an alias would manufacture false positives inside the witness verse "
        "itself, which RIGVEDA_LEXICAL_MENTION_POLICY.md forbids."
    ),
    "evidence_quote": "hiraṇyaṃ ca me 'yaś ca me śyāmaṃ ca me lohaṃ ca me sīsaṃ ca me trapu ca me",
    "witness_locator": AYAS_WITNESS,
    "r4_created_by": "scripts/r4_stage_entity_recall_and_ayas.py",
}


def main() -> int:
    annotation = load_annotation(PROJECT_ROOT)
    by_lemma: dict[str, set[str]] = collections.defaultdict(set)
    by_surface: dict[str, set[str]] = collections.defaultdict(set)
    for token in annotation.tokens:
        by_lemma[fold_annotation(token.normalized_lemma)].add(token.passage_key)
        by_surface[fold_annotation(token.surface_form)].add(token.passage_key)
    annotated_mantras = {token.passage_key for token in annotation.tokens}

    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session(database=DB) as session:
            entities = [
                dict(record)
                for record in session.run(
                    Query(
                        "MATCH (n:DomainEntity) RETURN n.entity_key AS entity_key, "
                        "n.display_label AS display_label, n.aliases_sa AS aliases_sa "
                        "ORDER BY n.entity_key",
                        timeout=TIMEOUT,
                    )
                )
            ]
            matched: dict[str, set[str]] = collections.defaultdict(set)
            for record in session.run(
                Query(
                    "MATCH (m:Mantra {veda:'RV'})-[:MENTIONS_ENTITY]->(n:DomainEntity) "
                    "RETURN n.entity_key AS k, m.canonical_key AS mantra",
                    timeout=TIMEOUT,
                )
            ):
                matched[record["k"]].add(record["mantra"])

            ayas_existing = [
                record["k"]
                for record in session.run(
                    Query(
                        "MATCH ({entity_key:$key})-[:ATTESTED_IN]->(m) "
                        "RETURN m.canonical_key AS k",
                        timeout=TIMEOUT,
                    ),
                    key=AYAS,
                )
            ]
            witness_exists = (
                session.run(
                    Query(
                        "MATCH (m:Mantra {canonical_key:$k}) RETURN count(m)", timeout=TIMEOUT
                    ),
                    k=AYAS_WITNESS,
                ).single()[0]
                == 1
            )
            ayas_yv_lexical = session.run(
                Query(
                    "MATCH (m:Mantra {veda:'YV'})-[:MENTIONS_ENTITY]->({entity_key:$key}) "
                    "RETURN count(DISTINCT m)",
                    timeout=TIMEOUT,
                ),
                key=AYAS,
            ).single()[0]
    finally:
        driver.close()

    rows: list[dict[str, Any]] = []
    for entity in entities:
        aliases = [str(a) for a in (entity["aliases_sa"] or [])]
        anchors: set[str] = set()
        anchor_kinds: set[str] = set()
        for alias in aliases:
            folded = fold_alias(alias)
            if folded in by_lemma:
                anchors |= by_lemma[folded]
                anchor_kinds.add("LEMMA")
            elif folded in by_surface:
                anchors |= by_surface[folded]
                anchor_kinds.add("SURFACE_FORM")
        found = matched.get(entity["entity_key"], set()) & annotated_mantras

        if not aliases:
            rows.append(
                {
                    "entity_key": entity["entity_key"],
                    "recall_status": "UNMEASURED_NO_REGISTERED_SANSKRIT_ALIAS",
                    "recall_reason": (
                        "The entity registers no Sanskrit alias, so there is nothing for the "
                        "lexical layer to match and nothing to measure recall of."
                    ),
                }
            )
            continue
        if not anchors:
            rows.append(
                {
                    "entity_key": entity["entity_key"],
                    "recall_status": "UNMEASURED_NO_ANNOTATION_ANCHOR",
                    "recall_reason": (
                        "No registered alias folds onto an annotated lemma or surface form, "
                        "so the Rigvedic annotation offers no ground truth for this entity. "
                        "Recall is unknown, not zero."
                    ),
                    "registered_aliases": len(aliases),
                }
            )
            continue

        recalled = len(found & anchors)
        rows.append(
            {
                "entity_key": entity["entity_key"],
                "recall_status": "MEASURED_AGAINST_RV_ANNOTATION",
                # The sample size the entry asks for, and it is the annotation's set rather
                # than the matcher's -- a denominator taken from the matcher would measure
                # the matcher against itself and always read 1.0.
                "recall_sample_size": len(anchors),
                "recall_matched": recalled,
                "recall": round(recalled / len(anchors), 4),
                "matcher_found_beyond_the_sample": len(found - anchors),
                "anchor_kinds": sorted(anchor_kinds),
                "registered_aliases": len(aliases),
                "recall_scope": "RV_ONLY_ANNOTATION_COVERS_NO_OTHER_CORPUS",
            }
        )

    measured = [row for row in rows if row["recall_status"] == "MEASURED_AGAINST_RV_ANNOTATION"]
    report = {
        "artifact": "R4_ENTITY_006_RECALL_AND_AYAS_STAGING",
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "gap_id": "GAP-ENTITY_COVERAGE-006",
        "contract": CONTRACT,
        "clause_1_recall": {
            "entities": len(entities),
            "measured": len(measured),
            "measurement_coverage": round(len(measured) / len(entities), 4),
            "status_distribution": dict(
                collections.Counter(row["recall_status"] for row in rows)
            ),
            "recall_quartiles": (
                {
                    "min": min(row["recall"] for row in measured),
                    "median": sorted(row["recall"] for row in measured)[len(measured) // 2],
                    "max": max(row["recall"] for row in measured),
                    "entities_at_zero_recall": sum(1 for r in measured if r["recall"] == 0.0),
                    "entities_at_full_recall": sum(1 for r in measured if r["recall"] == 1.0),
                }
                if measured
                else {}
            ),
            "scope": (
                "Rigveda only. The annotation covers the RV's 10,552 mantras and none of "
                "the other 9,658, so an entity's recall figure here is Rigvedic and every "
                "row says so in recall_scope."
            ),
            "rows": rows,
        },
        "clause_2_ayas": {
            "witness": AYAS_WITNESS,
            "witness_exists_in_graph": witness_exists,
            "yv_lexical_matches_now": ayas_yv_lexical,
            "yv_lexical_matches_must_stay": 0,
            "existing_attested_in": sorted(ayas_existing),
            "yv_attestation_present_before": any(
                key.startswith("VG:YV:") for key in ayas_existing
            ),
            "staged_edge": {
                "subject": AYAS,
                "predicate": "ATTESTED_IN",
                "object": AYAS_WITNESS,
                "properties": AYAS_EDGE,
            },
            "not_staged": (
                "No MENTIONS_ENTITY edge. That predicate means a lexical match and there is "
                "not one; fabricating it is what the entry forbids and it would also "
                "flip the closure measure away from its correct 0."
            ),
        },
        "promised": {
            "attested_in_edges_created": 0 if any(
                key.startswith("VG:YV:") for key in ayas_existing
            ) else 1,
            "entity_nodes_updated": len(rows),
        },
    }

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "staging.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )

    clause1 = report["clause_1_recall"]
    print()
    print("  GAP-ENTITY_COVERAGE-006 -- STAGED")
    print()
    print(f"  entities                     {clause1['entities']}")
    print(f"  recall measured              {clause1['measured']}  "
          f"(coverage {clause1['measurement_coverage']:.1%})")
    for status, count in sorted(clause1["status_distribution"].items()):
        print(f"      {count:>4}  {status}")
    print(f"  recall spread                {clause1['recall_quartiles']}")
    print()
    print(f"  ayas witness in graph        {witness_exists}")
    print(f"  ayas YV lexical matches      {ayas_yv_lexical}  (must stay 0)")
    print(f"  ayas ATTESTED_IN before      {sorted(ayas_existing)}")
    print(f"  ATTESTED_IN edges to create  {report['promised']['attested_in_edges_created']}")
    print()
    print(f"  staged: {(OUT / 'staging.json').relative_to(PROJECT_ROOT)}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
