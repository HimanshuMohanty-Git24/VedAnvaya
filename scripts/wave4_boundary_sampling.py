"""Seeded random and boundary sampling across the corpus. Wave 4 Phase 5.

Every other phase of this wave looked where a report or a registry entry pointed. This one
looks where nothing points, because the defects this campaign found by inspection were all in
places someone had already written about -- and the world export shipping 28 retired metres
was found by looking at a file nobody had checked, not by reading a claim about it.

Two sampling strategies, both reproducible from a seed:

**Boundary rows.** First and last verse of every corpus, of every mandala/kanda/adhyaya, and
the hymns either side of each structural seam. Off-by-one defects live at edges: the
Valakhilya insertion, the merged Griffith verse pairs, the AV sukta-division divergence and
the dasati partition disagreement were every one of them a boundary.

**A seeded random sample.** 240 mantras drawn with a fixed seed, stratified by corpus in
proportion to size, and every layer the product claims for that verse checked against what
the graph actually holds.

**What a finding is here.** Not "this verse has no translation" -- that is a known population
and the registry holds it. A finding is a CONTRADICTION: a row whose layer coverage disagrees
with what a product surface says about it, or a row carrying a value outside its declared
vocabulary, or a boundary whose two sides are inconsistent with each other. Each check states
what would falsify it before it runs.

Usage:
    python scripts/wave4_boundary_sampling.py [--sample 240] [--seed vedanvaya-wave4]
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib
import random
import sys
from typing import Any

from neo4j import GraphDatabase, Session

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from vedagraph.domain.ontology import AttributionPrecision, QualityTier  # noqa: E402

OUT = PROJECT_ROOT / "data" / "staging" / "wave4" / "boundary_sampling.json"

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "vedagraph_dev")
DB = "neo4j"

CORE = {"RV": 10552, "SV": 1844, "YV": 1975, "AV": 5839}

#: Layers a mantra may carry, and the predicate that carries each. Declared here so the
#: sample reports the same dimensions for every row rather than whatever each row happens to
#: have -- a per-row key set would make an absent layer invisible.
LAYERS: dict[str, str] = {
    "text_version": "HAS_TEXT_VERSION",
    "translation": "HAS_TRANSLATION",
    "rishi": "HAS_RISHI",
    "devata": "HAS_DEVATA",
    "devata_ascription": "HAS_DEVATA_ASCRIPTION",
    "chandas": "HAS_CHANDAS",
    "lemma": "MENTIONS_LEMMA",
    "entity": "MENTIONS_ENTITY",
    "semantic_assertion": "HAS_SEMANTIC_ASSERTION",
    "ritual_step": "HAS_RITUAL_STEP",
}

#: Vocabularies a sampled edge's grade properties must stay inside, READ from the enums that
#: declare them. Not from the graph, which would let the data validate itself -- and not typed
#: out here either.
#:
#: The first draft of this file restated them by hand and got ``attribution_precision`` wrong:
#: it listed PER_PASSAGE, CONTAINER_INHERITED, DERIVED and NOT_APPLICABLE, inventing DERIVED
#: and omitting TEXTUAL_MENTION, so the sample reported 20 perfectly valid MENTIONS_DEVATA and
#: MENTIONS_ENTITY edges as vocabulary violations. That is the same mistake as casting a graph
#: property into the wrong enum and reporting 44,778 edges as UNKNOWN: a checker that restates
#: a vocabulary is a second, worse copy of it.
VOCABULARIES: dict[str, frozenset[str]] = {
    "quality_tier": frozenset(str(v) for v in QualityTier),
    "attribution_precision": frozenset(str(v) for v in AttributionPrecision),
}


def boundary_keys(session: Session) -> dict[str, list[str]]:
    """The first and last mantra of every corpus and of every top-level division."""
    out: dict[str, list[str]] = {}
    out["corpus_edges"] = [
        str(r["k"])
        for r in session.run(
            "MATCH (m:Mantra) WITH m.veda AS veda, min(m.canonical_key) AS lo, "
            "max(m.canonical_key) AS hi "
            "UNWIND [lo, hi] AS k RETURN k ORDER BY k"
        )
    ]
    # The top-level division is the second structural segment of the key: M01, K01, A01.
    out["division_edges"] = [
        str(r["k"])
        for r in session.run(
            "MATCH (m:Mantra) WITH m, split(m.canonical_key, ':') AS parts "
            "WITH m.veda + ':' + parts[3] AS division, min(m.canonical_key) AS lo, "
            "max(m.canonical_key) AS hi "
            "UNWIND [lo, hi] AS k RETURN k ORDER BY k"
        )
    ]
    # The spans this campaign already knows are dangerous, sampled whether or not the
    # generic boundary rule happens to reach them.
    out["known_hazard_spans"] = [
        str(r["k"])
        for r in session.run(
            "MATCH (m:Mantra) WHERE "
            # The Valakhilya insertion, where the 1,017-hymn and 1,028-hymn presentations
            # diverge, and Griffith's merged pairs.
            "  m.canonical_key STARTS WITH 'VG:RV:SAK:M08:S049' "
            "  OR m.canonical_key STARTS WITH 'VG:RV:SAK:M08:S059' "
            "  OR m.canonical_key STARTS WITH 'VG:RV:SAK:M01:S065' "
            "  OR m.canonical_key STARTS WITH 'VG:RV:SAK:M01:S070' "
            # Kanda 20, the whole of which both translation sources omit.
            "  OR m.canonical_key STARTS WITH 'VG:AV:SAU:K20:S001' "
            "  OR m.canonical_key STARTS WITH 'VG:AV:SAU:K15:S001' "
            "RETURN m.canonical_key AS k ORDER BY k"
        )
    ]
    return out


def profile(session: Session, keys: list[str]) -> list[dict[str, Any]]:
    """Every declared layer for each key, present or absent, with grades."""
    clauses = ", ".join(
        f"size([(m)-[r:{predicate}]->() | r]) AS {name}" for name, predicate in LAYERS.items()
    )
    rows = session.run(
        f"UNWIND $keys AS k MATCH (m:Mantra {{canonical_key: k}}) "
        f"RETURN m.canonical_key AS key, m.veda AS veda, {clauses}",
        keys=keys,
    )
    return [dict(r) for r in rows]


def grade_violations(session: Session, keys: list[str]) -> list[dict[str, Any]]:
    """Any sampled edge carrying a grade value outside its declared vocabulary."""
    bad: list[dict[str, Any]] = []
    for prop, allowed in VOCABULARIES.items():
        for row in session.run(
            f"UNWIND $keys AS k MATCH (m:Mantra {{canonical_key: k}})-[r]->() "
            f"WHERE r.{prop} IS NOT NULL AND NOT r.{prop} IN $allowed "
            f"RETURN m.canonical_key AS key, type(r) AS predicate, r.{prop} AS value "
            f"LIMIT 20",
            keys=keys,
            allowed=sorted(allowed),
        ):
            bad.append({"property": prop, **dict(row)})
    return bad


def contradictions(session: Session, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Checks whose falsifier is stated, run over the sampled rows.

    Each one asserts a relation BETWEEN two things the graph says, so it can fail. "This
    verse has no translation" cannot fail interestingly; "this verse has a translation edge
    and no Translation node on the other end" can.
    """
    found: list[dict[str, Any]] = []
    keys = [r["key"] for r in rows]

    checks: list[tuple[str, str, str]] = [
        (
            "a translation edge whose object is not a Translation",
            "UNWIND $keys AS k MATCH (m:Mantra {canonical_key: k})-[:HAS_TRANSLATION]->(t) "
            "WHERE NOT t:Translation RETURN count(*) AS n",
            "The predicate's declared range is :Translation. A mismatch means the signature "
            "gate's universe and this edge's reality disagree.",
        ),
        (
            "a mantra with no text version at all",
            "UNWIND $keys AS k MATCH (m:Mantra {canonical_key: k}) "
            "WHERE NOT (m)-[:HAS_TEXT_VERSION]->() RETURN count(*) AS n",
            "A verse with no text is not a verse. Every corpus was ingested with at least a "
            "primary text, so any zero here is an ingest defect rather than a coverage gap.",
        ),
        (
            "a metre object carrying a colon, on a public edge",
            "UNWIND $keys AS k MATCH (m:Mantra {canonical_key: k})-[:HAS_CHANDAS]->(c) "
            "WHERE NOT c:Internal AND c.preferred_label CONTAINS ':' RETURN count(*) AS n",
            "Whitney's colon separates a statement from its per-verse exceptions and cannot "
            "occur inside a metre name. This is the Phase 3 defect, re-checked on a sample "
            "the fix did not select for.",
        ),
        (
            "an edge with no quality tier",
            "UNWIND $keys AS k MATCH (m:Mantra {canonical_key: k})-[r]->() "
            "WHERE r.quality_tier IS NULL RETURN count(*) AS n",
            "Tier coverage is reported as 100%. A single untiered edge on a random sample "
            "falsifies that headline.",
        ),
        (
            "an inherited attribution on an edge whose source asserts per-verse",
            "UNWIND $keys AS k MATCH (m:Mantra {canonical_key: k})-[r:HAS_DEVATA]->() "
            "WHERE r.attribution_precision = 'CONTAINER_INHERITED' AND m.veda <> 'RV' "
            "RETURN count(*) AS n",
            "HAS_DEVATA is Rigveda-only by measurement. A container-inherited deity edge on "
            "another corpus would mean the predicate had quietly grown a second population.",
        ),
        (
            "a mantra whose veda disagrees with its own canonical key",
            "UNWIND $keys AS k MATCH (m:Mantra {canonical_key: k}) "
            "WHERE NOT m.canonical_key STARTS WITH 'VG:' + m.veda + ':' "
            "RETURN count(*) AS n",
            "The key encodes the corpus. A disagreement means one of the two was written by "
            "something that did not read the other.",
        ),
        (
            "a public mantra marked internal",
            "UNWIND $keys AS k MATCH (m:Mantra {canonical_key: k}) WHERE m:Internal "
            "RETURN count(*) AS n",
            "No corpus verse may be internal. This is the boundary the QualityVerdict leak "
            "crossed in the other direction.",
        ),
    ]
    for name, cypher, why in checks:
        record = session.run(cypher, keys=keys).single()
        count = 0 if record is None else int(record["n"])
        found.append(
            {
                "check": name,
                "hits": count,
                "outcome": "PASS" if count == 0 else "FINDING",
                "falsifier": why,
            }
        )
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=int, default=240)
    parser.add_argument("--seed", default="vedanvaya-wave4-boundary")
    args = parser.parse_args()

    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session(database=DB) as session:
            census = {
                str(r["veda"]): int(r["n"])
                for r in session.run(
                    "MATCH (m:Mantra) RETURN m.veda AS veda, count(*) AS n ORDER BY veda"
                )
            }
            if census != CORE:
                print(f"  REFUSING: core corpus is {census}, expected {CORE}.")
                return 1

            boundaries = boundary_keys(session)
            boundary_all = sorted({k for group in boundaries.values() for k in group})

            # Stratified seeded sample. Drawn from a sorted key list so the seed alone
            # determines the selection -- Neo4j's row order must not be part of the identity.
            rng = random.Random(args.seed)
            picked: list[str] = []
            for veda, total in sorted(CORE.items()):
                quota = max(1, round(args.sample * total / sum(CORE.values())))
                keys = sorted(
                    str(r["k"])
                    for r in session.run(
                        "MATCH (m:Mantra {veda: $veda}) RETURN m.canonical_key AS k",
                        veda=veda,
                    )
                )
                picked.extend(rng.sample(keys, min(quota, len(keys))))

            print()
            print("  WAVE 4 PHASE 5 -- BOUNDARY AND SEEDED SAMPLING")
            print()
            print(f"  seed                        {args.seed}")
            print(f"  boundary rows               {len(boundary_all)}")
            for group, keys in sorted(boundaries.items()):
                print(f"      {group:22} {len(keys)}")
            print(f"  seeded random rows          {len(picked)}")
            print()

            boundary_rows = profile(session, boundary_all)
            sample_rows = profile(session, picked)
            all_rows = boundary_rows + sample_rows

            missing = sorted(set(boundary_all + picked) - {str(r["key"]) for r in all_rows})
            if missing:
                print(f"  {len(missing)} sampled key(s) matched no Mantra: {missing[:5]}")

            findings = contradictions(session, all_rows)
            vocabulary = grade_violations(session, boundary_all + picked)

            coverage: dict[str, dict[str, int]] = {}
            for row in all_rows:
                veda = str(row["veda"])
                bucket = coverage.setdefault(veda, dict.fromkeys(LAYERS, 0))
                bucket["rows"] = bucket.get("rows", 0) + 1
                for layer in LAYERS:
                    if int(row[layer] or 0):
                        bucket[layer] += 1

            for row in findings:
                print(f"    {row['outcome']:8} {row['check']}  ({row['hits']})")
            if vocabulary:
                print(f"\n    FINDING  {len(vocabulary)} grade value(s) outside the declared "
                      f"vocabulary: {vocabulary[:3]}")
            else:
                print("    PASS     every sampled grade value is inside its vocabulary")

            print()
            print("  layer coverage over the sample, per corpus (rows with at least one edge)")
            header = "  " + "veda".ljust(6) + "rows".rjust(6)
            for layer in LAYERS:
                header += layer[:9].rjust(11)
            print(header)
            for veda in sorted(coverage):
                line = "  " + veda.ljust(6) + str(coverage[veda]["rows"]).rjust(6)
                for layer in LAYERS:
                    line += str(coverage[veda][layer]).rjust(11)
                print(line)

            report = {
                "artifact": "WAVE4_BOUNDARY_SAMPLING",
                "at": datetime.datetime.now(datetime.UTC).isoformat(),
                "seed": args.seed,
                "method": (
                    "Boundary rows enumerated from the graph's own structural keys, plus a "
                    "seeded stratified random sample drawn from a SORTED key list so the seed "
                    "alone determines the selection. Each contradiction check states its "
                    "falsifier before it runs and asserts a relation between two things the "
                    "graph says, so it can fail."
                ),
                "core_census": census,
                "boundary_groups": {k: len(v) for k, v in boundaries.items()},
                "boundary_keys": boundary_all,
                "sampled_keys": sorted(picked),
                "rows_profiled": len(all_rows),
                "keys_that_matched_no_mantra": missing,
                "contradiction_checks": findings,
                "grade_vocabulary_violations": vocabulary,
                "layer_coverage_over_sample": coverage,
                "findings": [f["check"] for f in findings if f["outcome"] == "FINDING"]
                + (["grade values outside the declared vocabulary"] if vocabulary else [])
                + (["sampled keys matched no Mantra"] if missing else []),
            }
            report["sha256"] = hashlib.sha256(
                json.dumps(report, sort_keys=True, default=str).encode()
            ).hexdigest()
            OUT.write_text(
                json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            print()
            print(f"  report: {OUT.relative_to(PROJECT_ROOT)}")
            if report["findings"]:
                print(f"\n  FINDINGS: {report['findings']}")
            return 1 if report["findings"] else 0
    finally:
        driver.close()


if __name__ == "__main__":
    raise SystemExit(main())
