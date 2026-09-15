#!/usr/bin/env python3
"""Validate a specialist agent's staging artifact against the campaign ingestion contract.

Nothing reaches the canonical graph without passing this. The contract it enforces is
docs/reports/data-completeness/INGESTION_CONTRACT.md.

Two design choices are worth stating, because both are lessons paid for earlier in this
project.

First, this reports *coverage of its own checks*, not merely their pass rate. A validator
that skipped every row whose shape it did not recognise once reported a clean run over an
artifact it had barely inspected, which is worse than no validator at all: it converts
absence of checking into evidence of correctness. So every check counts the rows it
actually evaluated, and a check whose coverage is below 100% is reported as a failure of
the validator, separately from any failure of the data.

Second, unrecognised enum values are reported rather than defaulted. An attribution axis in
this project was once written by three mechanisms that disagreed, precisely because an
unknown value was quietly coerced to something plausible. A closed vocabulary that silently
accepts a new member is not closed.

Usage:
    python scripts/validate_staging_artifact.py data/staging/<domain> [--graph] [--json OUT]

    --graph  additionally resolve every canonical_key against the live Neo4j and check the
             row's claimed veda matches the node's. Off by default so an artifact can be
             checked without a database; but the lead must run it with --graph before
             importing, because an unresolvable key is the most common mapping defect and
             it is invisible offline.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any

EVIDENCE_LAYERS = frozenset(
    {
        "SOURCE_EXPLICIT",
        "DETERMINISTIC_DERIVED",
        "SEMANTIC_MODEL_EXTRACTION",
        "INTERPRETIVE_CLAIM",
    }
)

QUALITY_CLASSES = frozenset(
    {
        "PRIMARY_DIGITAL_EDITION",
        "SCHOLARLY_EDITION",
        "TRADITIONAL_INDEX",
        "INSTITUTIONAL_ARCHIVE",
        "PUBLIC_SCAN",
        "COMMUNITY_ARCHIVE",
        "MODEL_ASSISTED_DERIVATION",
    }
)

MAPPING_CONFIDENCES = frozenset({"EXACT", "VERIFIED_SEGMENT", "PROBABLE", "UNVERIFIED"})

# Rows at these confidences are staged but must not be imported. They are the verification
# queue, not a weaker grade of fact.
NOT_IMPORTABLE = frozenset({"PROBABLE", "UNVERIFIED"})

REQUIRED_ROW_FIELDS = (
    "canonical_key",
    "payload",
    "evidence_layer",
    "source_id",
    "source_locator",
    "quality_class",
    "mapping_method",
    "mapping_confidence",
)

REQUIRED_MANIFEST_FIELDS = (
    "domain",
    "agent",
    "schema_version",
    "algorithm_version",
    "created_at",
    "code_commit",
    "config_hash",
    "source_snapshot_ids",
    "files",
    "counts",
    "closes_gaps",
    "qa",
)

REQUIRED_COUNT_KEYS = (
    "candidates_considered",
    "accepted",
    "rejected",
    "verified_zero",
    "not_applicable",
    "unresolved",
)

DUPLICATE_REPORT_LIMIT = 20
FAILURE_PRINT_LIMIT = 10


@dataclass
class Check:
    """One named check, carrying how many rows it actually looked at."""

    name: str
    evaluated: int = 0
    eligible: int = 0
    failures: list[str] = field(default_factory=list)

    @property
    def coverage(self) -> float:
        if self.eligible == 0:
            return 1.0
        return self.evaluated / self.eligible

    @property
    def complete(self) -> bool:
        return self.evaluated == self.eligible


@dataclass
class Result:
    checks: list[Check] = field(default_factory=list)
    fatal: list[str] = field(default_factory=list)
    stats: dict[str, object] = field(default_factory=dict)

    def check(self, name: str) -> Check:
        for existing in self.checks:
            if existing.name == name:
                return existing
        created = Check(name=name)
        self.checks.append(created)
        return created

    @property
    def data_failures(self) -> int:
        return sum(len(c.failures) for c in self.checks)

    @property
    def incomplete_checks(self) -> list[Check]:
        return [c for c in self.checks if not c.complete]

    @property
    def ok(self) -> bool:
        return not self.fatal and self.data_failures == 0 and not self.incomplete_checks


def file_sha256(path: pathlib.Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: pathlib.Path) -> tuple[list[dict[str, Any]], list[str]]:
    """Parse a JSONL file, returning the rows and one error per unparseable line.

    A bad line is reported with its line number and skipped rather than aborting, so one
    malformed row does not hide the state of the other twenty thousand.
    """
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    with path.open("r", encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError as error:
                errors.append(f"{path.name}:{number} is not valid JSON: {error}")
                continue
            if not isinstance(parsed, dict):
                errors.append(f"{path.name}:{number} is not a JSON object")
                continue
            rows.append(parsed)
    return rows, errors


def validate_manifest(manifest: dict[str, Any], root: pathlib.Path, result: Result) -> None:
    missing = [key for key in REQUIRED_MANIFEST_FIELDS if key not in manifest]
    if missing:
        result.fatal.append(f"manifest.json is missing required field(s): {', '.join(missing)}")
        return

    counts = manifest.get("counts")
    if not isinstance(counts, dict):
        result.fatal.append("manifest counts must be an object")
        return

    missing_counts = [key for key in REQUIRED_COUNT_KEYS if key not in counts]
    if missing_counts:
        result.fatal.append(f"manifest counts missing: {', '.join(missing_counts)}")
        return

    # The arithmetic check. An artifact whose parts do not sum to its whole has lost rows
    # somewhere between generation and serialisation, and the lost rows are not random --
    # they are the ones the pipeline could not handle.
    balance = result.check("manifest.counts_balance")
    balance.eligible = 1
    balance.evaluated = 1
    considered = counts["candidates_considered"]
    parts = counts["accepted"] + counts["rejected"] + counts["unresolved"]
    if considered != parts:
        balance.failures.append(
            f"candidates_considered={considered} but accepted+rejected+unresolved={parts}; "
            f"{abs(considered - parts)} row(s) are unaccounted for"
        )

    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        result.fatal.append("manifest files must be a non-empty list")
        return

    checksums = result.check("manifest.file_checksums")
    checksums.eligible = len(files)
    for entry in files:
        if not isinstance(entry, dict) or "path" not in entry or "sha256" not in entry:
            checksums.evaluated += 1
            checksums.failures.append(f"malformed files[] entry: {entry!r}")
            continue
        target = root / entry["path"]
        checksums.evaluated += 1
        if not target.exists():
            checksums.failures.append(f"manifest names {entry['path']}, which does not exist")
            continue
        actual = file_sha256(target)
        if actual != entry["sha256"]:
            checksums.failures.append(
                f"{entry['path']} checksum mismatch: manifest says {entry['sha256'][:12]}..., "
                f"file is {actual[:12]}..."
            )


def validate_rows(
    rows: list[dict[str, Any]], source_ids: set[str], result: Result
) -> tuple[Counter[str], Counter[str]]:
    total = len(rows)

    required = result.check("row.required_fields")
    required.eligible = total
    layers = result.check("row.evidence_layer_closed")
    layers.eligible = total
    quality = result.check("row.quality_class_closed")
    quality.eligible = total
    confidence = result.check("row.mapping_confidence_closed")
    confidence.eligible = total
    provenance = result.check("row.source_id_resolves")
    provenance.eligible = total
    locator = result.check("row.source_locator_substantive")
    locator.eligible = total
    recension = result.check("row.recension_verified_present")
    recension.eligible = total
    zero_guard = result.check("row.no_zero_for_unknown")
    zero_guard.eligible = total

    layer_counts: Counter[str] = Counter()
    confidence_counts: Counter[str] = Counter()
    seen: Counter[tuple[str, Any]] = Counter()

    for index, row in enumerate(rows):
        label = row.get("canonical_key", f"<row {index + 1}>")

        required.evaluated += 1
        absent = [f for f in REQUIRED_ROW_FIELDS if f not in row or row[f] in (None, "")]
        if absent:
            required.failures.append(f"{label}: missing {', '.join(absent)}")

        # Closed vocabularies. Reported, never coerced.
        layers.evaluated += 1
        layer = row.get("evidence_layer")
        if layer not in EVIDENCE_LAYERS:
            layers.failures.append(f"{label}: unknown evidence_layer {layer!r}")
        else:
            layer_counts[layer] += 1

        quality.evaluated += 1
        if row.get("quality_class") not in QUALITY_CLASSES:
            quality.failures.append(f"{label}: unknown quality_class {row.get('quality_class')!r}")

        confidence.evaluated += 1
        conf = row.get("mapping_confidence")
        if conf not in MAPPING_CONFIDENCES:
            confidence.failures.append(f"{label}: unknown mapping_confidence {conf!r}")
        else:
            confidence_counts[conf] += 1

        provenance.evaluated += 1
        if row.get("source_id") not in source_ids:
            provenance.failures.append(
                f"{label}: source_id {row.get('source_id')!r} is not in sources.jsonl"
            )

        # A locator must be precise enough to re-find the datum by hand. A bare title or a
        # naked domain name is not; it is the appearance of provenance.
        locator.evaluated += 1
        loc = str(row.get("source_locator") or "")
        if len(loc.strip()) < 3:
            locator.failures.append(f"{label}: source_locator {loc!r} is not specific enough")

        recension.evaluated += 1
        if "recension_verified" not in row:
            recension.failures.append(f"{label}: recension_verified is absent")
        elif (
            row["recension_verified"] is True
            and not str(row.get("recension_evidence") or "").strip()
        ):
            recension.failures.append(
                f"{label}: claims recension_verified with no recension_evidence"
            )

        # The campaign's central prohibition, checked mechanically: a payload may not use 0
        # to mean "we did not look". Unknown is null, and the row says why.
        zero_guard.evaluated += 1
        payload = row.get("payload")
        if isinstance(payload, dict):
            for key, value in payload.items():
                if value == 0 and "unknown" in str(key).lower():
                    zero_guard.failures.append(
                        f"{label}: payload.{key} is 0; use null for an unknown population"
                    )

        if "canonical_key" in row:
            seen[(row["canonical_key"], row.get("source_id"))] += 1

    duplicates = result.check("row.no_duplicate_key_source")
    duplicates.eligible = 1
    duplicates.evaluated = 1
    repeated = [pair for pair, count in seen.items() if count > 1]
    for pair in repeated[:DUPLICATE_REPORT_LIMIT]:
        duplicates.failures.append(f"duplicate (canonical_key, source_id): {pair}")
    if len(repeated) > DUPLICATE_REPORT_LIMIT:
        duplicates.failures.append(
            f"...and {len(repeated) - DUPLICATE_REPORT_LIMIT} further duplicate pair(s)"
        )

    return layer_counts, confidence_counts


def validate_against_graph(rows: list[dict[str, Any]], result: Result) -> None:
    """Resolve every row's subject against the live graph and check the claimed veda.

    Rows come at two grains, and the first version of this validator only understood one.

    A passage-grained row names a `:Passage` by `canonical_key`. That is most domains, and
    it is the default.

    An entity-grained row names a registry entity rather than a passage. Those nodes carry
    no `canonical_key` and no `:Passage` label, so requiring one made the primary object of
    an entity-grained domain unexpressible. Two agents hit that wall and worked around it by
    moving their real output into a sidecar file and filling `rows.jsonl` with
    passage-grained proxies. The artifacts passed, which is the problem: the check reported
    full coverage over rows that were not the domain's subject.

    So a row may declare `subject_kind: ENTITY`. The two grains are counted as separate
    checks rather than pooled, because a single blended coverage figure would hide a domain
    resolving none of its entities behind a wall of passage proxies.

    **The identity property must be declared, not guessed.** The first version of this
    extension looked up `entity_key` alone, generalising from `:Devata`. That was half a
    fix: `entity_key` is carried by 28 labels but not by `:Formula` (0 of 4,825, which uses
    `formula_id`) or `:FormulaFamily` (0 of 720, `family_id`), and the graph also uses
    `concept_id`, `axis_key`, `group_key`, `family_key`, `epithet_key`, `claim_id`,
    `assertion_id` and more. An agent discovered this by measuring rather than by trusting
    the extension.

    Trying every known identity property in turn would be worse than the original defect,
    because `run_id` or `source_id` would resolve against an unrelated node and report a
    false success. So a row sets `subject_id_property` (default `entity_key`), and may set
    `subject_label` to assert what it expects to find. The resolved labels are reported, so
    a row that resolves against something unexpected is visible rather than merely green.
    """
    sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))
    try:
        from neo4j import GraphDatabase
    except ImportError:
        result.fatal.append("--graph requested but the neo4j driver is not importable")
        return

    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "vedagraph_dev")
    database = os.environ.get("NEO4J_DATABASE", "neo4j")

    passage_rows = [r for r in rows if str(r.get("subject_kind", "PASSAGE")).upper() != "ENTITY"]
    entity_rows = [r for r in rows if str(r.get("subject_kind", "PASSAGE")).upper() == "ENTITY"]

    keys = [row["canonical_key"] for row in passage_rows if row.get("canonical_key")]
    claimed = {
        row["canonical_key"]: row.get("veda") or (row.get("payload") or {}).get("veda")
        for row in passage_rows
        if row.get("canonical_key")
    }
    # (identity property, value, expected label or None) per entity row.
    entity_subjects: list[tuple[str, str, str | None]] = []
    for row in entity_rows:
        prop = str(row.get("subject_id_property") or "entity_key")
        value = row.get(prop) or row.get("entity_key") or row.get("canonical_key")
        if value:
            entity_subjects.append((prop, str(value), row.get("subject_label")))

    resolves = result.check("graph.canonical_key_resolves")
    resolves.eligible = len(keys)
    veda_match = result.check("graph.veda_agrees")

    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        with driver.session(database=database) as session:
            found: dict[str, str] = {}
            batch_size = 2000
            for start in range(0, len(keys), batch_size):
                batch = keys[start : start + batch_size]
                records = session.run(
                    "UNWIND $keys AS k MATCH (p:Passage {canonical_key: k}) "
                    "RETURN p.canonical_key AS key, p.veda AS veda",
                    keys=batch,
                )
                for record in records:
                    found[record["key"]] = record["veda"]
                resolves.evaluated += len(batch)

            for key in keys:
                if key not in found:
                    resolves.failures.append(f"{key} does not resolve to a Passage")

            # Iterate unique keys: `claimed` is keyed by canonical_key, so a duplicated key
            # would otherwise be reported once per row against a single collapsed claim.
            # Duplicates are already a hard failure in row.no_duplicate_key_source.
            checkable = [k for k in dict.fromkeys(keys) if k in found and claimed.get(k)]
            veda_match.eligible = len(checkable)
            for key in checkable:
                veda_match.evaluated += 1
                if found[key] != claimed[key]:
                    veda_match.failures.append(
                        f"{key}: row claims veda {claimed[key]!r}, graph says {found[key]!r}"
                    )

            if entity_subjects:
                entity_check = result.check("graph.entity_subject_resolves")
                entity_check.eligible = len(entity_subjects)
                label_check = result.check("graph.entity_label_agrees")

                by_property: dict[str, list[tuple[str, str | None]]] = {}
                for prop, value, expected in entity_subjects:
                    by_property.setdefault(prop, []).append((value, expected))

                for prop, pairs in by_property.items():
                    # The property name is interpolated because Cypher cannot parameterise a
                    # property key. Restricted to an identifier so it cannot carry a clause.
                    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", prop):
                        entity_check.evaluated += len(pairs)
                        entity_check.failures.append(
                            f"{prop!r} is not a usable property name for an identity lookup"
                        )
                        continue
                    resolved: dict[str, list[str]] = {}
                    values = [value for value, _ in pairs]
                    for start in range(0, len(values), batch_size):
                        batch = values[start : start + batch_size]
                        records = session.run(
                            f"UNWIND $keys AS k MATCH (n) WHERE n.`{prop}` = k "
                            f"RETURN k AS key, labels(n) AS labels",
                            keys=batch,
                        )
                        for record in records:
                            resolved.setdefault(record["key"], []).extend(record["labels"])
                        entity_check.evaluated += len(batch)
                    for value, expected in pairs:
                        if value not in resolved:
                            entity_check.failures.append(
                                f"{value} does not resolve to any node by {prop}"
                            )
                            continue
                        if expected:
                            label_check.eligible += 1
                            label_check.evaluated += 1
                            if expected not in resolved[value]:
                                label_check.failures.append(
                                    f"{value}: row expects :{expected}, graph has "
                                    f"{sorted(set(resolved[value]))}"
                                )
    finally:
        driver.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", help="a data/staging/<domain> directory")
    parser.add_argument("--graph", action="store_true", help="also check keys against Neo4j")
    parser.add_argument("--json", default="", help="write the machine-readable result here")
    args = parser.parse_args()

    root = pathlib.Path(args.directory)
    result = Result()

    if not root.is_dir():
        print(f"FATAL: {root} is not a directory")
        return 2

    manifest_path = root / "manifest.json"
    rows_path = root / "rows.jsonl"
    sources_path = root / "sources.jsonl"
    rejected_path = root / "rejected.jsonl"

    for required_path in (manifest_path, rows_path, sources_path):
        if not required_path.exists():
            result.fatal.append(f"{required_path.name} is required and absent")

    # rejected.jsonl absent is fatal: a domain that cannot say what it declined has not been
    # audited, and the declined candidates are where the mapping errors live.
    if not rejected_path.exists():
        result.fatal.append(
            "rejected.jsonl is absent; a domain that cannot say what it declined has not "
            "been audited"
        )

    if result.fatal:
        _report(result, args)
        return 1

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_manifest(manifest, root, result)

    rows, row_errors = read_jsonl(rows_path)
    sources, source_errors = read_jsonl(sources_path)
    rejected, rejected_errors = read_jsonl(rejected_path)
    result.fatal.extend(row_errors + source_errors + rejected_errors)

    source_ids = {s["source_id"] for s in sources if "source_id" in s}
    layer_counts, confidence_counts = validate_rows(rows, source_ids, result)

    # The manifest's accepted count must match the rows actually present. This is the
    # rows-sent versus rows-landed diff, applied one stage earlier than the import.
    landed = result.check("manifest.accepted_matches_rows")
    landed.eligible = 1
    landed.evaluated = 1
    accepted = manifest.get("counts", {}).get("accepted")
    if accepted != len(rows):
        landed.failures.append(
            f"manifest says accepted={accepted} but rows.jsonl holds {len(rows)} row(s)"
        )

    reasons = result.check("rejected.has_reason")
    reasons.eligible = len(rejected)
    for index, row in enumerate(rejected):
        reasons.evaluated += 1
        if not str(row.get("reason") or "").strip():
            reasons.failures.append(
                f"rejected row {index + 1} has no reason; {row.get('canonical_key', '<no key>')}"
            )

    if args.graph and rows:
        validate_against_graph(rows, result)

    result.stats = {
        "domain": manifest.get("domain"),
        "agent": manifest.get("agent"),
        "rows": len(rows),
        "sources": len(source_ids),
        "rejected": len(rejected),
        "evidence_layers": dict(layer_counts),
        "mapping_confidence": dict(confidence_counts),
        "not_importable": sum(confidence_counts[c] for c in NOT_IMPORTABLE),
        "graph_checked": bool(args.graph),
        "passage_grained_rows": sum(
            1 for r in rows if str(r.get("subject_kind", "PASSAGE")).upper() != "ENTITY"
        ),
        "entity_grained_rows": sum(
            1 for r in rows if str(r.get("subject_kind", "PASSAGE")).upper() == "ENTITY"
        ),
    }

    _report(result, args)
    return 0 if result.ok else 1


def _report(result: Result, args: argparse.Namespace) -> None:
    print()
    if result.stats:
        s = result.stats
        print(f"  {s['domain']} (agent {s['agent']}): {s['rows']} row(s), {s['sources']} source(s)")
        if s.get("not_importable"):
            print(
                f"  {s['not_importable']} row(s) at PROBABLE/UNVERIFIED confidence -- staged, "
                f"not importable"
            )
        if not s["graph_checked"]:
            print(
                "  canonical keys NOT checked against the graph; rerun with --graph before import"
            )
        print()

    for check in result.checks:
        if check.failures:
            mark = "FAIL"
        elif not check.complete:
            mark = "PART"
        else:
            mark = "OK  "
        print(f"  [{mark}] {check.name}  ({check.evaluated}/{check.eligible} evaluated)")
        for failure in check.failures[:FAILURE_PRINT_LIMIT]:
            print(f"         {failure}")
        if len(check.failures) > FAILURE_PRINT_LIMIT:
            print(f"         ...and {len(check.failures) - FAILURE_PRINT_LIMIT} more")

    if result.fatal:
        print()
        for message in result.fatal:
            print(f"  [FATAL] {message}")

    print()
    if result.incomplete_checks:
        names = ", ".join(c.name for c in result.incomplete_checks)
        print(f"  VALIDATOR INCOMPLETE: {names} did not evaluate every eligible row.")
        print("  Treat this as a validator defect, not a clean artifact.")
    elif result.ok:
        print("  PASS. Every check evaluated every eligible row and found no defect.")
    else:
        print(f"  FAIL. {result.data_failures} data defect(s) across fully-evaluated checks.")
    print()

    if args.json:
        payload = {
            "ok": result.ok,
            "stats": result.stats,
            "fatal": result.fatal,
            "checks": [
                {
                    "name": c.name,
                    "evaluated": c.evaluated,
                    "eligible": c.eligible,
                    "coverage": c.coverage,
                    "complete": c.complete,
                    "failures": c.failures,
                }
                for c in result.checks
            ],
        }
        pathlib.Path(args.json).write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
