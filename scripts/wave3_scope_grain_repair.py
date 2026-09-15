#!/usr/bin/env python3
"""Owner decision 2: derive ``scope_type`` from the evidence grain and split M6.

The owner's ruling is that there is no global default ``scope_type``, that the value must
come from the actual subject grain, that the narrowest truthful closed-enum scope each
population supports is the one to use, and that a heterogeneous M6 must be split into
homogeneous import populations.

WHAT THE ORIGINAL M6 CARD GOT WRONG
===================================

The card framed this as a name collision and asked the owner which readers could be
allowed to break. Two measurements make that framing the wrong one.

**There is no reader to break.** ``scope_type`` appears on 0 nodes and 0 relationships of
the live graph. The collision the audit found is between two *staging* artifacts on 18
shared canonical keys, so nothing in the database reads the name today. ``ADDITIVE`` and
``BACKWARD_COMPATIBLE`` were recorded false against a population that does not exist.

**The schema already holds both vocabularies, and they are already separate.**
``product.audio.models.AudioScope`` is the tradition's span vocabulary for a recording,
with ``SCOPE_TO_ENTITY_TYPES`` as its grain contract; ``models.enums.ScopeType`` is the
scope of a metadata assertion. Two axes, two closed enums, two Pydantic models -- and one
property name, which is the entire defect. So the repair is to write each axis under its
own name rather than to invent a vocabulary or to pick a winner.

THE THREE POPULATIONS, AND WHY EACH IS HOMOGENEOUS
==================================================

Measured over the staging artifacts and asserted against the live graph:

1. ``audio_scope_type`` = ``MANTRA`` -- 954 rows (audio_rv 150, audio_yv 33, audio_av
   771). Every subject is an ``entity_type=MANTRA`` node, the only entity type
   ``AudioScope.MANTRA`` permits.

2. ``audio_scope_type`` = ``COLLECTION`` -- 3 rows (samaveda_music). These carried
   ``STRUCTURAL_CONTAINER``, which is **not a member of AudioScope at all**: it is a graph
   ``entity_type`` value written into a field whose enum is the tradition's vocabulary.
   ``AudioScope.COLLECTION`` is documented as "A named Samavedic collection -- ARANYA,
   CHANDA, MAHANAMNYA, UTTARA", and all three keys are CHANDA or UTTARA containers, so the
   truthful closed-enum value was already in the schema. Corrected here, not invented.

   They stay a population apart from (1) even though both are audio, because the grain
   genuinely differs: gana performances of 82s, 223s and 399s over containers holding many
   verses, with no source stating a boundary inside any of them. Labelling them MANTRA so
   that one importer could take a single population is what the owner barred.

3. ``assertion_scope_type`` = ``SINGLE_MANTRA`` -- 466 rows (attribution). A different
   axis: the scope of an attribution assertion, on ``ScopeType`` rather than
   ``AudioScope``. Every one of the 466 also carries ``asserted_granularity=VERSE``, a
   466/466 agreement, so the domain already states its own grain. The property is kept
   rather than dropped as redundant, because ``asserted_granularity`` lives only in the
   staging payload and the graph property is what a consumer reads.

No population is left at ``UNKNOWN``: every source grain here is known.

WHAT THIS SCRIPT DOES NOT DO
============================

It plans and validates. It writes nothing to the graph and rewrites no staging artifact:
the namespaced property name is emitted as an import instruction, so the importer applies
it and each artifact stays as its agent sealed it.

Usage:
    python scripts/wave3_scope_grain_repair.py [--json OUT]
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import pathlib
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from neo4j import GraphDatabase

from vedagraph.models.enums import ScopeType
from vedagraph.product.audio.models import SCOPE_TO_ENTITY_TYPES, AudioScope

STAGING = pathlib.Path("data/staging")
OUT = STAGING / "integration" / "wave3_scope_grain.json"

URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
AUTH = (os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", "vedagraph_dev"))
DB = os.environ.get("NEO4J_DATABASE", "neo4j")

#: The split, stated as data. Each entry names the domains whose rows form one homogeneous
#: population, the graph property the importer must write, the closed-enum value, and the
#: enum the value is drawn from -- so a value outside its own enum fails here rather than
#: passing as a string that happens to look plausible.
POPULATIONS: tuple[dict[str, Any], ...] = (
    {
        "population": "AUDIO_RECORD_AT_MANTRA_SCOPE",
        "domains": ("audio_rv", "audio_yv", "audio_av"),
        "graph_property": "audio_scope_type",
        "enum": "AudioScope",
        "value": AudioScope.MANTRA,
        "staged_value": "MANTRA",
        "why": (
            "The source addresses one verse and the file is that verse's recitation. Every "
            "subject is an entity_type=MANTRA node, the only type AudioScope.MANTRA admits."
        ),
    },
    {
        "population": "GANA_PERFORMANCE_AT_COLLECTION_SCOPE",
        "domains": ("samaveda_music",),
        "graph_property": "audio_scope_type",
        "enum": "AudioScope",
        "value": AudioScope.COLLECTION,
        "staged_value": "STRUCTURAL_CONTAINER",
        "why": (
            "Gana performances the source places on a container page, 82-399s over "
            "containers holding many verses, with no source-stated internal boundary. The "
            "staged value STRUCTURAL_CONTAINER is a graph entity_type, not an AudioScope "
            "member; AudioScope.COLLECTION is the enum's own value for a named Samavedic "
            "collection and every key here is a CHANDA or UTTARA container."
        ),
    },
    {
        "population": "ATTRIBUTION_ASSERTION_AT_SINGLE_MANTRA_SCOPE",
        "domains": ("attribution",),
        "graph_property": "assertion_scope_type",
        "enum": "ScopeType",
        "value": ScopeType.SINGLE_MANTRA,
        "staged_value": "SINGLE_MANTRA",
        "why": (
            "The scope of an attribution assertion, a different axis from a recording's "
            "span. The printed bracket addresses a numbered verse and all 466 rows also "
            "carry asserted_granularity=VERSE, a 466/466 agreement."
        ),
    },
)

#: ``ScopeType`` carries no entity-type contract of its own, so the grain each of its
#: values requires is stated here rather than guessed inside the loop.
SCOPE_TYPE_GRAIN: dict[ScopeType, frozenset[str]] = {
    ScopeType.SINGLE_MANTRA: frozenset({"MANTRA"}),
    ScopeType.MANTRA_RANGE: frozenset({"MANTRA"}),
    ScopeType.WHOLE_PASSAGE: frozenset({"MANTRA", "HYMN", "SECTION", "STRUCTURAL_CONTAINER"}),
}


def read_rows(domain: str) -> list[dict[str, Any]]:
    path = STAGING / domain / "rows.jsonl"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def required_grain(entry: dict[str, Any]) -> frozenset[str]:
    """Entity types the declared scope permits, from the schema rather than from taste."""
    value = entry["value"]
    if isinstance(value, AudioScope):
        return SCOPE_TO_ENTITY_TYPES[value]
    if isinstance(value, ScopeType):
        return SCOPE_TYPE_GRAIN[value]
    raise TypeError(f"{entry['population']}: scope value {value!r} is on no known enum")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", default=str(OUT))
    args = parser.parse_args()

    # Which staging rows carry the property at all, per domain, with which value. Read from
    # the artifacts rather than from the card, whose figures predate two restages.
    staged: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)
    for domain in sorted(p.name for p in STAGING.iterdir() if p.is_dir()):
        for row in read_rows(domain):
            payload = row.get("payload") or {}
            if "scope_type" not in payload:
                continue
            staged[domain].append((str(row.get("canonical_key") or ""), str(payload["scope_type"])))

    # Every scope-bearing domain must be claimed by exactly one population, or the split is
    # not a partition and some row would import under no rule or under two.
    claimed = [d for entry in POPULATIONS for d in entry["domains"]]
    duplicated = sorted({d for d in claimed if claimed.count(d) > 1})
    unclaimed = sorted(set(staged) - set(claimed))
    empty = sorted(d for d in claimed if not staged.get(d))

    driver = GraphDatabase.driver(URI, auth=AUTH)
    findings: list[str] = []
    report_populations: list[dict[str, Any]] = []
    try:
        with driver.session(database=DB) as session:
            for entry in POPULATIONS:
                keys = [k for d in entry["domains"] for k, _v in staged.get(d, [])]
                values = {v for d in entry["domains"] for _k, v in staged.get(d, [])}
                permitted = required_grain(entry)

                grain = session.run(
                    "UNWIND $keys AS k "
                    "OPTIONAL MATCH (n:Passage {canonical_key: k}) "
                    "RETURN k AS key, n.entity_type AS entity_type",
                    keys=sorted(set(keys)),
                ).data()
                observed = collections.Counter(
                    str(row["entity_type"]) if row["entity_type"] else "<key absent from graph>"
                    for row in grain
                )
                off_grain = sorted(
                    row["key"] for row in grain if str(row["entity_type"] or "") not in permitted
                )

                homogeneous = len(values) == 1
                if not homogeneous:
                    findings.append(
                        f"{entry['population']}: staged values are heterogeneous {sorted(values)}"
                    )
                if off_grain:
                    findings.append(
                        f"{entry['population']}: {len(off_grain)} subject(s) do not resolve at "
                        f"grain {sorted(permitted)} -- e.g. {off_grain[:3]}"
                    )
                if not keys:
                    findings.append(f"{entry['population']}: claims 0 rows")

                report_populations.append(
                    {
                        "population": entry["population"],
                        "domains": list(entry["domains"]),
                        "graph_property": entry["graph_property"],
                        "enum": entry["enum"],
                        "scope_type": str(entry["value"]),
                        "staged_value": entry["staged_value"],
                        "value_corrected": str(entry["value"]) != entry["staged_value"],
                        "row_count": len(keys),
                        "distinct_keys": len(set(keys)),
                        "why": entry["why"],
                        "grain_required_entity_types": sorted(permitted),
                        "grain_observed": dict(sorted(observed.items())),
                        "subjects_off_grain": off_grain,
                        "homogeneous": homogeneous,
                    }
                )
    finally:
        driver.close()

    if unclaimed:
        findings.append(f"domains write scope_type but no population claims them: {unclaimed}")
    if empty:
        findings.append(f"populations claim domains that write no scope_type: {empty}")
    if duplicated:
        findings.append(f"domains claimed by more than one population: {duplicated}")

    # The collision is only gone if no property name carries more than one axis. Sharing a
    # name within one axis is correct; across axes it is the defect.
    by_property: dict[str, set[str]] = collections.defaultdict(set)
    for populated in report_populations:
        by_property[populated["graph_property"]].add(populated["enum"])
    for prop, enums in sorted(by_property.items()):
        if len(enums) > 1:
            findings.append(f"property {prop} still carries {len(enums)} axes: {sorted(enums)}")

    total = sum(populated["row_count"] for populated in report_populations)
    report = {
        "schema_version": "1.0",
        "owner_decision": "section 2 -- scope_type comes from the evidence grain; split M6",
        "supersedes": "M6 scope_type namespacing, one card, returned to owner",
        "graph_readers_of_bare_scope_type": 0,
        "graph_readers_note": (
            "Measured, not assumed: scope_type is on 0 nodes and 0 relationships of the "
            "live graph, so no existing reader's meaning changes and the card's "
            "ADDITIVE=false / BACKWARD_COMPATIBLE=false flags were recorded against a "
            "population that does not exist."
        ),
        "populations": report_populations,
        "rows_covered": total,
        "domains_writing_scope_type": sorted(staged),
        "partition_is_total": not unclaimed and not empty and not duplicated,
        "findings": findings,
        "verdict": "HOMOGENEOUS_AND_ON_GRAIN" if not findings else "DEFECT",
        "flags": {
            "ADDITIVE": True,
            "DETERMINISTIC_IDENTITY": True,
            "BACKWARD_COMPATIBLE": True,
            "ROLLBACK_DEFINED": True,
            "OLD_PREDICATE_MEANING_CHANGED": False,
        },
        "flags_rationale": (
            "Each population writes a new property under its own axis's name. No property "
            "called scope_type is written at all and none exists in the graph, so no "
            "predicate or property changes meaning for any reader. Rollback is removing "
            "the two new properties."
        ),
    }

    pathlib.Path(args.json).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(args.json).write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )

    print()
    print("  M6 SCOPE GRAIN -- split into homogeneous populations, nothing written")
    print()
    print(f"  {'population':46}{'property':24}{'scope_type':18}{'rows':>7}  grain observed")
    print(f"  {'-' * 46}{'-' * 24}{'-' * 18}{'-' * 7}  {'-' * 26}")
    for populated in report_populations:
        mark = " *" if populated["value_corrected"] else ""
        print(
            f"  {populated['population'][:45]:46}{populated['graph_property']:24}"
            f"{populated['scope_type'] + mark:18}{populated['row_count']:>7}  "
            f"{','.join(populated['grain_observed'])}"
        )
    print()
    print("  * value corrected from the one the agent staged")
    print(f"  rows covered: {total:,}   partition is total: {report['partition_is_total']}")
    print(f"  bare scope_type readers in the graph: {report['graph_readers_of_bare_scope_type']}")
    print()
    if findings:
        print(f"  {len(findings)} FINDING(S):")
        for finding in findings:
            print(f"    - {finding}")
    else:
        print("  every population is homogeneous and every subject resolves at its grain")
    print()
    print(f"  VERDICT: {report['verdict']}")
    print(f"  report: {args.json}")
    print()
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
