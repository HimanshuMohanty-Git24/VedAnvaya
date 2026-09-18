#!/usr/bin/env python3
"""Measure the state GAP-SAMAVEDA_MUSIC-002 is being closed from, before anything changes.

Nothing here is read out of a prior receipt. HEAD comes from git, the census and the
notation-layer absence come from the live store, the registry counts come from a fresh
audit artifact, and the gate states come from the files that record them. The point of
writing it down first is that a closure report which measures only the end state cannot
tell the reader whether anything moved.

Usage:
    python data/staging/samaveda_music_002_final/build_baseline.py
"""

from __future__ import annotations

import collections
import datetime
import hashlib
import json
import pathlib
import re
import subprocess

from neo4j import GraphDatabase

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = ROOT / "data" / "staging" / "samaveda_music_002_final" / "baseline.json"
ROWS = ROOT / "data" / "staging" / "samaveda_music" / "rows.jsonl"
REJECTED = ROOT / "data" / "staging" / "samaveda_music" / "rejected.jsonl"
MANIFEST = ROOT / "data" / "staging" / "samaveda_music" / "manifest.json"
REGISTRY = ROOT / "data" / "gap_registry.json"
AUDIT = ROOT / "data" / "staging" / "wave4" / "registry_closure_audit.json"
ELIGIBILITY = ROOT / "data" / "staging" / "integration" / "wave3_eligibility.json"
GATE_A = ROOT / "data" / "staging" / "samaveda_music_002_final" / "gate_a.json"

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "vedagraph_dev")
DB = "neo4j"

GAP = "GAP-SAMAVEDA_MUSIC-002"


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def sha256_of(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    rows = [json.loads(line) for line in ROWS.read_text(encoding="utf-8").splitlines() if line]
    rejected = [
        json.loads(line) for line in REJECTED.read_text(encoding="utf-8").splitlines() if line
    ]
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    eligibility = json.loads(ELIGIBILITY.read_text(encoding="utf-8"))
    gate_a = json.loads(GATE_A.read_text(encoding="utf-8"))

    notation = [r for r in rows if r["payload"]["layer"] == "ARCIKA_NOTATION"]
    withheld = [r for r in rejected if r["disposition"] == "UNRESOLVED"]
    entry = next(g for g in registry["gaps"] if g["gap_id"] == GAP)

    driver = GraphDatabase.driver(URI, auth=AUTH)
    with driver.session(database=DB) as session:
        nodes = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
        rels = session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]
        labels = sorted(session.run("CALL db.labels() YIELD label RETURN label").value())
        rel_types = sorted(
            session.run(
                "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType"
            ).value()
        )
        sv_mantras = session.run(
            "MATCH (m:Mantra {veda:'SV'}) RETURN count(m) AS c"
        ).single()["c"]
        sv_text_versions = session.run(
            "MATCH (:Mantra {veda:'SV'})-[:HAS_TEXT_VERSION]->(t:TextVersion) "
            "RETURN t.text_role AS role, t.accented AS accented, count(*) AS c "
            "ORDER BY role"
        ).data()
        sv_accented = session.run(
            "MATCH (:Mantra {veda:'SV'})-[:HAS_TEXT_VERSION]->(t:TextVersion) "
            "WHERE t.accented = true RETURN count(t) AS c"
        ).single()["c"]
        melodic_labels = [
            label
            for label in labels
            if re.search(r"saman|gana|stobha|melod|svara", label, re.IGNORECASE)
        ]
        staged_keys = sorted({r["canonical_key"] for r in notation})
        resolvable = session.run(
            "MATCH (m:Mantra {veda:'SV'}) WHERE m.canonical_key IN $keys "
            "RETURN count(m) AS c",
            keys=staged_keys,
        ).single()["c"]
    driver.close()

    baseline = {
        "artifact": "SAMAVEDA_MUSIC_002_BASELINE",
        "at": datetime.datetime.now(datetime.UTC).isoformat(),
        "measured_live": True,
        "head": {
            "commit": git("rev-parse", "HEAD"),
            "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
            "modified_tracked_files": len(
                [
                    line
                    for line in git("status", "--porcelain").splitlines()
                    if line and not line.startswith("??")
                ]
            ),
            "untracked_paths": len(
                [
                    line
                    for line in git("status", "--porcelain").splitlines()
                    if line.startswith("??")
                ]
            ),
        },
        "graph": {
            "nodes": nodes,
            "relationships": rels,
            "label_count": len(labels),
            "relationship_type_count": len(rel_types),
            "sv_mantras": sv_mantras,
            "sv_text_versions_by_role": sv_text_versions,
            "sv_accented_text_versions": sv_accented,
            "labels_matching_melodic_vocabulary": melodic_labels,
            "MUSICALIZED_AS_present_in_type_store": "MUSICALIZED_AS" in rel_types,
            "staged_notation_keys_resolving_to_an_sv_mantra": resolvable,
            "staged_notation_keys": len(staged_keys),
        },
        "registry": {
            "audit_artifact": str(AUDIT.relative_to(ROOT)).replace("\\", "/"),
            "audit_at": audit["at"],
            "entries": audit["entries"],
            "closed": audit["closed"],
            "execution_blockers": audit["execution_blockers"],
            "counts": audit["counts"],
            "implementation_fixable": audit["counts"].get("STILL_IMPLEMENTATION_FIXABLE", 0),
            "owner_decision_required": audit["counts"].get(
                "BLOCKED_OWNER_DECISION_REQUIRED", 0
            ),
            "not_terminated": audit["not_terminated"],
            "measurement_disagreements": len(audit["measurement_disagreements"]),
            "status_disagreements": len(audit["registry_status_disagreements"]),
            "gap_002_status": entry["status"],
            "gap_002_closure_measure": entry["closure_measure"],
            "gap_002_closure_measured_value": entry["closure_measured_value"],
            "gap_002_closure_test": entry["closure_test"],
        },
        "notation_population": {
            "domain_rows_total": len(rows),
            "by_layer": dict(
                collections.Counter(r["payload"]["layer"] for r in rows)
            ),
            "arcika_notation_rows": len(notation),
            "arcika_notation_by_collection": dict(
                collections.Counter(r["canonical_key"].split(":")[3] for r in notation)
            ),
            "withheld_unresolved_rows": len(withheld),
            "withheld_reason_classes": dict(
                collections.Counter(
                    "NEAR_LINE_EXISTS_WITNESS_DISAGREEMENT"
                    if r["nearest_accented_line_similarity_at_least_0_90"]
                    else "NO_NEAR_LINE_PROBABLE_ABSENCE"
                    for r in withheld
                )
            ),
            "rejected_non_notation_rows": len(rejected) - len(withheld),
            "sv_verse_denominator": sv_mantras,
            "notation_plus_withheld": len(notation) + len(withheld),
            "every_sv_verse_has_a_typed_disposition": len(notation) + len(withheld)
            == sv_mantras,
            "rows_sha256": sha256_of(ROWS),
            "manifest_rows_sha256": next(
                f["sha256"] for f in manifest["files"] if f["path"] == "rows.jsonl"
            ),
        },
        "gates": {
            "definitions": eligibility["gates"],
            "eligibility_rule": eligibility["rule"],
            "A": {
                "source": "scripts/validate_staging_artifact.py --graph, re-run live",
                "result": "PASS" if gate_a["ok"] else "FAIL",
                "checks": len(gate_a.get("checks", [])),
                "fatal": len(gate_a.get("fatal", [])),
                "every_check_at_full_coverage": all(
                    c["evaluated"] == c["eligible"] for c in gate_a["checks"]
                ),
                "recorded_in_wave3_eligibility": eligibility["domains"]["samaveda_music"][
                    "gate_a_structural"
                ],
            },
            "B": {
                "recorded_in_wave3_eligibility": eligibility["domains"]["samaveda_music"][
                    "gate_b_semantic"
                ],
                "implementation_present_before_this_pass": (
                    ROOT / "scripts" / "samaveda_music_gate_b.py"
                ).exists(),
            },
            "C": {
                "recorded_in_wave3_eligibility": eligibility["domains"]["samaveda_music"][
                    "gate_c_adversarial"
                ],
                "implementation_present_before_this_pass": (
                    ROOT / "scripts" / "samaveda_music_gate_c.py"
                ).exists(),
                "pre_existing_adversarial_sample": {
                    "name": "gana_rendering.adversarial_shortest_40",
                    "target": manifest["qa"]["detail"]["adversarial_sample"]["target"],
                    "size": manifest["qa"]["detail"]["adversarial_sample"]["size"],
                    "defects": manifest["qa"]["detail"]["adversarial_sample"]["defects"],
                    "population_it_covers": "GANA_RENDERING",
                    "covers_the_notation_population": False,
                    "independent_of_the_staging_codepath": False,
                },
            },
        },
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps(baseline, indent=2, ensure_ascii=False)
    OUT.write_text(body + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    print(f"  HEAD                     {baseline['head']['commit']}")
    print(f"  graph                    {nodes:,} nodes / {rels:,} rels")
    print(f"  implementation_fixable   {baseline['registry']['implementation_fixable']}")
    print(f"  not_terminated           {baseline['registry']['not_terminated']}")
    print(f"  notation rows            {len(notation):,}")
    print(f"  withheld rows            {len(withheld):,}")
    print(f"  sv accented textversions {sv_accented}")


if __name__ == "__main__":
    main()
