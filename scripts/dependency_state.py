"""Content-addressed dependency state. Owner round four, Phase B.

The original gate inferred staleness from the Wave 3 stamps on the nodes. Those never come
off, so every consumer read STALE_INPUT for ever and a rebuild could not be expressed at
all. Round three replaced that with per-consumer input hashes, which was the right shape and
too weak in three ways, all fixed here:

1.  **Counts are not a fingerprint.** ``label:Devata=419`` is unchanged by rewriting every
    property on all 419 nodes, and by deleting one edge while adding another. The
    fingerprint now digests the sorted identity keys of the nodes and the sorted endpoint
    pairs of the edges, so a swap of equal size moves it. Where a class carries no identity
    key -- ``:TextVersion``, ``:RoleFiller`` -- that is recorded as ``keyless`` rather than
    silently hashed to nothing, because a fingerprint that cannot see a population should
    say so.

2.  **File inputs were invisible.** A consumer built from a staging artifact went CURRENT on
    the graph alone, so editing the artifact did not make it stale. Declared files are now
    hashed.

3.  **The builder was not an input.** Changing the build script leaves output that no longer
    reproduces. The builder's own source digest is part of the recorded input.

Status is defined by hash comparison, never by a timestamp:

    CURRENT         every current upstream hash equals the recorded one, and the output
                    exists with the recorded digest
    STALE_INPUT     at least one upstream hash differs from what the output was built from
    BLOCKED         the rebuild cannot run: a dependency, source, tool or quota is missing
    NOT_APPLICABLE  there is no meaningful artifact for the current graph

``built_at`` is carried as metadata and is never read when deciding status.

Usage:
    python scripts/dependency_state.py --status
    python scripts/dependency_state.py --record NAME --output-file PATH
    python scripts/dependency_state.py --record NAME --blocked "reason"
    python scripts/dependency_state.py --record NAME --not-applicable "reason"
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from neo4j import GraphDatabase, Session
from wave3_dependency_invalidation import CONSUMERS

LEDGER = pathlib.Path("data/staging/integration/dependency_ledger.json")
OUT = pathlib.Path("data/staging/integration/dependency_status.json")

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "vedagraph_dev")
DB = "neo4j"

#: The properties a node may carry its identity under, in precedence order. A node matching
#: none of them is counted as ``keyless``: the fingerprint records how many it could not see
#: rather than pretending the population is empty.
IDENTITY_PROPERTIES: tuple[str, ...] = (
    "canonical_key",
    "entity_key",
    "formula_id",
    "family_id",
    "metric_id",
    "claim_id",
    "work_id",
    "assertion_id",
    "step_key",
    "lemma",
    "predicate",
)

_IDENTITY = "coalesce(" + ", ".join(f"n.{name}" for name in IDENTITY_PROPERTIES) + ")"
_A_IDENTITY = _IDENTITY.replace("n.", "a.")
_B_IDENTITY = _IDENTITY.replace("n.", "b.")

#: Files each consumer is built from, beyond the graph. Declared here rather than in
#: CONSUMERS so that file lives next to the graph-element declaration it complements without
#: editing a module that several other scripts import.
CONSUMER_FILES: dict[str, tuple[str, ...]] = {
    "semantic resemblance": (
        "data/staging/semantic_resemblance/manifest.json",
        "data/staging/semantic_resemblance/rows.jsonl",
    ),
    "formula / parallel / variant relations": (
        "data/enrichment/vedagraph_enrichment_v1/manifest.json",
    ),
    "entity coverage": ("data/domain/vedagraph_domain_v2/veda_coverage_v3.json",),
    "Ask retrieval": ("data/gold/ask_benchmark_v1.jsonl",),
    # The Lab stage does not read the graph at all: it reads the Python export's output. Until
    # Wave 4 that dependency was expressed nowhere, so re-exporting the world left the Lab
    # CURRENT against a partition measured on the previous one.
    "Visualization Lab aggregates": ("frontend/.world/world.raw.json",),
}

#: The script whose source is part of each consumer's input. A build script that changes
#: leaves output that no longer reproduces, so it belongs in the hash.
CONSUMER_BUILDERS: dict[str, tuple[str, ...]] = {
    "cross-Veda matrices": ("scripts/build_enrichment.py",),
    "formula / parallel / variant relations": ("scripts/build_formula_families.py",),
    "entity coverage": ("scripts/build_veda_coverage_and_metrics.py",),
    "quality evaluation": ("scripts/graph_quality_scorecard.py",),
    # Three stages, so three builders. Round three recorded only the Python export for both
    # world consumers, which is the stage that applies NOT n:Internal -- and the two JS stages
    # that turn its output into the files a browser downloads were in nothing's hash.
    "Visualization Lab aggregates": (
        "frontend/scripts/build-constellations.mjs",
        "frontend/scripts/build-world.mjs",
    ),
    "Knowledge World public projection": (
        "scripts/export_graph_world.py",
        "scripts/export_predicate_semantics.py",
    ),
}

#: Every file a consumer's build produces that something downstream or a reader consumes.
#:
#: Wave 4 finding, and the reason this exists as a declaration rather than a ``--output-file``
#: argument. Both world consumers had recorded ``frontend/.world/world.raw.json`` -- an
#: intermediate, and the SAME intermediate -- as their output. So the Lab stage could never be
#: seen stale, because the file it was judged on is rebuilt by the other consumer, and the four
#: files that actually ship were declared by nothing at all.
#:
#: Measured consequence: M10 marked 28 malformed metre identities internal, the Python export
#: was re-run and dropped them, and ``frontend/public/world/world.labels.json`` still carried
#: all 28 to every reader of the Knowledge World. The dependency report said STALE_INPUT for a
#: digest on the intermediate and nothing about the bundle.
CONSUMER_OUTPUTS: dict[str, tuple[str, ...]] = {
    "cross-Veda matrices": ("data/enrichment/vedagraph_enrichment_v1/manifest.json",),
    "formula / parallel / variant relations": (
        "data/enrichment/vedagraph_enrichment_v1/formula_families.jsonl",
    ),
    "entity coverage": ("data/domain/vedagraph_domain_v2/veda_coverage_v3.json",),
    "quality evaluation": ("docs/reports/GRAPH_QUALITY_V2_SCORECARD.md",),
    "Knowledge World public projection": (
        "frontend/.world/world.raw.json",
        "frontend/public/world/world.predicates.json",
    ),
    "Visualization Lab aggregates": (
        "frontend/.world/constellations.json",
        "frontend/public/world/world.bin",
        "frontend/public/world/world.json",
        "frontend/public/world/world.labels.json",
    ),
}


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def file_digest(path: pathlib.Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def label_fingerprint(session: Session, label: str) -> str:
    """Count, keyless count, and a digest of the sorted identity keys.

    Sorted inside Cypher and digested here, so the value does not depend on row order --
    which the owner's transition test for "reverting an upstream file reproduces the correct
    state" needs in order to mean anything.
    """
    row = session.run(
        f"MATCH (n:`{label}`) WITH {_IDENTITY} AS k "
        "RETURN count(*) AS total, "
        "sum(CASE WHEN k IS NULL THEN 1 ELSE 0 END) AS keyless, "
        "collect(DISTINCT k) AS keys"
    ).single()
    if row is None:
        return "label:absent"
    keys = sorted(str(k) for k in (row["keys"] or []) if k is not None)
    return (
        f"n={int(row['total'])};keyless={int(row['keyless'])};"
        f"keys={digest(chr(10).join(keys))}"
    )


def predicate_fingerprint(session: Session, predicate: str) -> str:
    """Count and a digest of the sorted endpoint identity pairs.

    An edge whose endpoints cannot both be named contributes to ``unnamed`` instead of to
    the digest. Deleting one edge and adding another of the same type moves this value,
    which a count alone does not.
    """
    row = session.run(
        f"MATCH (a)-[r:`{predicate}`]->(b) "
        f"WITH {_A_IDENTITY} AS ka, {_B_IDENTITY} AS kb "
        "RETURN count(*) AS total, "
        "sum(CASE WHEN ka IS NULL OR kb IS NULL THEN 1 ELSE 0 END) AS unnamed, "
        "collect(CASE WHEN ka IS NULL OR kb IS NULL THEN NULL ELSE ka + '>' + kb END) AS pairs"
    ).single()
    if row is None:
        return "type:absent"
    pairs = sorted(str(p) for p in (row["pairs"] or []) if p is not None)
    return (
        f"n={int(row['total'])};unnamed={int(row['unnamed'])};"
        f"pairs={digest(chr(10).join(pairs))}"
    )


def upstream_hashes(session: Session, consumer: dict[str, Any]) -> dict[str, str]:
    """Every declared input, each hashed separately.

    Per input rather than one blended digest, so a STALE_INPUT report can name WHICH input
    moved. A single hash would say only that something did.
    """
    name = str(consumer["consumer"])
    inputs: dict[str, str] = {}
    for label in sorted(consumer["reads_labels"]):
        inputs[f"label:{label}"] = label_fingerprint(session, label)
    for predicate in sorted(consumer["reads_types"]):
        inputs[f"type:{predicate}"] = predicate_fingerprint(session, predicate)
    for relative in CONSUMER_FILES.get(name, ()):
        inputs[f"file:{relative}"] = file_digest(pathlib.Path(relative)) or "absent"
    for builder in CONSUMER_BUILDERS.get(name, ()):
        inputs[f"builder:{builder}"] = file_digest(pathlib.Path(builder)) or "absent"
    return inputs


def declared_output_hashes(name: str) -> dict[str, str]:
    """Every declared output of a consumer, hashed, missing ones recorded as ``absent``.

    ``absent`` rather than omitted: a recorded output that has since been deleted must read
    as a difference, and a key that disappears from the dict would compare equal to nothing.
    """
    return {
        relative: file_digest(pathlib.Path(relative)) or "absent"
        for relative in CONSUMER_OUTPUTS.get(name, ())
    }


def consumer_by_name(name: str) -> dict[str, Any]:
    for consumer in CONSUMERS:
        if consumer["consumer"] == name:
            return consumer
    raise SystemExit(f"unknown consumer {name!r}; known: {[c['consumer'] for c in CONSUMERS]}")


def load_ledger() -> dict[str, Any]:
    return json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.exists() else {}


def classify(
    current: dict[str, str], recorded: dict[str, Any]
) -> tuple[str, list[str], str | None]:
    """The status, the inputs that moved, and the reason where one applies.

    A pure function of (current hashes, recorded entry). No clock, no wave stamp, no
    filesystem: everything it decides on is passed in, which is what makes the transition
    tests possible.
    """
    if recorded.get("not_applicable_reason"):
        return "NOT_APPLICABLE", [], str(recorded["not_applicable_reason"])
    if recorded.get("blocked_reason"):
        return "BLOCKED", [], str(recorded["blocked_reason"])
    if not recorded:
        return "STALE_INPUT", sorted(current), "never built"

    was = dict(recorded.get("input_hashes") or {})
    moved = sorted(
        key
        for key in set(current) | set(was)
        if current.get(key) != was.get(key)
    )
    if moved:
        return "STALE_INPUT", moved, None

    # Declared outputs first, because that is the check that catches a stage rebuilt out of
    # step with the stage it feeds. Every declared output is compared, and the reason names
    # which file rather than saying an output moved.
    for relative, recorded_hash in (recorded.get("output_hashes") or {}).items():
        path = pathlib.Path(relative)
        if not path.exists():
            return "STALE_INPUT", [], f"declared output {relative} is gone"
        actual = file_digest(path)
        if actual != recorded_hash:
            if recorded_hash == "absent":
                return "STALE_INPUT", [], f"declared output {relative} appeared after recording"
            return (
                "STALE_INPUT",
                [],
                f"declared output {relative} no longer matches its recorded digest",
            )

    output = recorded.get("output_file")
    if output:
        path = pathlib.Path(str(output))
        if not path.exists():
            return "STALE_INPUT", [], f"recorded output {output} is gone"
        if file_digest(path) != recorded.get("output_hash"):
            return "STALE_INPUT", [], f"recorded output {output} no longer matches its digest"
    return "CURRENT", [], None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--record", default="")
    parser.add_argument("--output-file", default="")
    parser.add_argument("--blocked", default="")
    parser.add_argument("--not-applicable", default="")
    args = parser.parse_args()

    ledger = load_ledger()
    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session(database=DB) as session:
            nodes = int(session.run("MATCH (n) RETURN count(n) AS c").single()["c"])
            rels = int(session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"])

            if args.record:
                consumer = consumer_by_name(args.record)
                entry: dict[str, Any] = {
                    "consumer": args.record,
                    "input_hashes": upstream_hashes(session, consumer),
                    # Metadata only. Never read when deciding status.
                    "built_at": datetime.datetime.now(datetime.UTC).isoformat(),
                    "graph_census": {"nodes": nodes, "relationships": rels},
                }
                declared = declared_output_hashes(args.record)
                if args.not_applicable:
                    entry["not_applicable_reason"] = args.not_applicable
                elif args.blocked:
                    entry["blocked_reason"] = args.blocked
                elif declared:
                    missing = sorted(k for k, v in declared.items() if v == "absent")
                    if missing:
                        print(f"  declared output(s) do not exist: {missing}")
                        print("  build them before recording; a recorded absence is not a build.")
                        return 1
                    entry["output_hashes"] = declared
                elif args.output_file:
                    path = pathlib.Path(args.output_file)
                    if not path.exists():
                        print(f"  output file {path} does not exist")
                        return 1
                    entry["output_file"] = str(path).replace("\\", "/")
                    entry["output_hash"] = file_digest(path)
                else:
                    print("  --record needs --output-file, --blocked or --not-applicable")
                    return 1
                ledger[args.record] = entry
                LEDGER.write_text(
                    json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
                )
                print(f"  recorded {args.record}: {len(entry['input_hashes'])} declared inputs")
                return 0

            rows: list[dict[str, Any]] = []
            for consumer in CONSUMERS:
                name = str(consumer["consumer"])
                current = upstream_hashes(session, consumer)
                recorded = ledger.get(name) or {}
                status, moved, reason = classify(current, recorded)
                rows.append(
                    {
                        "consumer": name,
                        "status": status,
                        "declared_inputs": len(current),
                        "inputs_that_moved": moved,
                        "reason": reason,
                        "output_file": recorded.get("output_file"),
                        "output_hash": recorded.get("output_hash"),
                        "declared_outputs": sorted(recorded.get("output_hashes") or {}),
                        "built_at": recorded.get("built_at"),
                        "rebuilt_by": consumer.get("rebuilt_by"),
                        "current_input_digest": digest(
                            json.dumps(current, sort_keys=True)
                        ),
                        "recorded_input_digest": digest(
                            json.dumps(recorded.get("input_hashes") or {}, sort_keys=True)
                        ),
                    }
                )
    finally:
        driver.close()

    counts = {
        status: sum(1 for r in rows if r["status"] == status)
        for status in ("CURRENT", "STALE_INPUT", "BLOCKED", "NOT_APPLICABLE")
    }
    summary = {
        "artifact": "DEPENDENCY_STATUS",
        "at": datetime.datetime.now(datetime.UTC).isoformat(),
        "graph_census": {"nodes": nodes, "relationships": rels},
        "consumers": rows,
        "counts": counts,
        "model": (
            "Content-addressed. Each declared input -- graph label, graph predicate, file, "
            "builder source -- is hashed separately, so a STALE_INPUT report names which "
            "one moved. Label and predicate fingerprints digest sorted identity keys and "
            "endpoint pairs rather than counting, because a count is unchanged by a swap of "
            "equal size. built_at is metadata and is never read when deciding status."
        ),
        "unexplained_stale": [
            r["consumer"]
            for r in rows
            if r["status"] == "STALE_INPUT" and not r["inputs_that_moved"] and not r["reason"]
        ],
    }
    OUT.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print()
    print("  DEPENDENCY STATE -- content-addressed")
    print()
    print(f"  {'consumer':40} {'status':14} {'inputs':>7} {'moved':>6}")
    print(f"  {'-' * 72}")
    for row in rows:
        print(
            f"  {row['consumer']:40} {row['status']:14} "
            f"{row['declared_inputs']:>7} {len(row['inputs_that_moved']):>6}"
        )
        if row["inputs_that_moved"]:
            print(f"      moved: {', '.join(row['inputs_that_moved'][:4])}")
        if row["reason"]:
            print(f"      reason: {row['reason'][:90]}")
    print()
    print("  " + "  ".join(f"{k}={v}" for k, v in counts.items()))
    print(f"  unexplained stale: {summary['unexplained_stale'] or 'none'}")
    print(f"  report: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
