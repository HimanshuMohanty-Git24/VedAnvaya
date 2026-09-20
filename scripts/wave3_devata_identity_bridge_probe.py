#!/usr/bin/env python3
"""Owner section 9: size CROSS_VEDA_DEVATA_IDENTITY_BRIDGE. Do not build it on a guess.

Agent 11 found that ``HAS_DEVATA`` values and ``HAS_DEVATA_ASCRIPTION`` values intersect at
exactly zero, so any cross-Veda deity analytic that joins the two dedication layers on a
display label fails silently for the Rigveda against the Atharvaveda. The owner's ruling is
that this is a separate implementation gap, that the layers must be bridged through
canonical Devata identity rather than through display labels, and that an ascription which
cannot deterministically resolve keeps its unresolved form.

WHY THE INTERSECTION IS ZERO, WHICH IS NOT THE SAME AS WHY IT IS HARD
=====================================================================

The two layers do not hold the same kind of object.

``HAS_DEVATA`` points at a ``:Devata``: 214 nodes, ``VG:DEVATA:ADITIH``, whose
``display_label`` is the English "Aditi". ``HAS_DEVATA_ASCRIPTION`` points at a
``:DevataAscription``: 324 nodes, ``VG:ASCRIPTION:AV:ABDEVATYAM-AFCD``, whose
``display_label`` is the Sanskrit adjective "abdevatyam", meaning *having the waters as its
deity*. So the zero is structural rather than a coverage accident, and no normalisation of
either label can close it: one side is a deity's name in English and the other is a
derived adjective in Sanskrit.

A bridge therefore has to parse the adjective, recover its stem, and resolve that stem
against canonical Devata identity. This script measures how far a deterministic parse gets,
and reports what it cannot reach rather than reaching for it.

WHAT THE PROBE DOES NOT DO
==========================

It writes nothing and it creates no bridge edge. Its output is the gap's measured size and
the residue's shape, so the gap can be registered with a denominator instead of an
intention. Every unresolved ascription stays unresolved.

Usage:
    python scripts/wave3_devata_identity_bridge_probe.py [--json OUT]
"""

from __future__ import annotations

import argparse
import ast
import collections
import json
import os
import pathlib
import re
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from neo4j import GraphDatabase

from vedagraph.normalize import ComparisonForm, comparison_form

OUT = pathlib.Path("data/staging/integration/wave3_devata_identity_bridge.json")

URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
AUTH = (os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", "vedagraph_dev"))
DB = os.environ.get("NEO4J_DATABASE", "neo4j")

#: Suffixes that mark an adjective as *having X as its deity*, longest first so a longer
#: formation is never truncated by a shorter one inside it. Every spelling here was read
#: off the 324 stored labels rather than taken from a grammar, because the source is a
#: printed Anukramani transcription and it spells the same formation several ways.
DEITY_ADJECTIVE_SUFFIXES: tuple[str, ...] = (
    "devatakam",
    "devatyam",
    "daivatyam",
    "daivatam",
    "ddivatam",  # transcription slip for -daivatam, 2 labels
    "devatya",
    "devata",
    "daivata",
)

#: Labels whose head is not a deity at all. Whitney's apparatus puts the hymn's SUBJECT in
#: the same slot as its deity -- "bhaisajyam" is healing, "ayusyam" is for long life -- so a
#: bridge that resolved these would be asserting a dedication the source never made.
NON_DEITY_HEADS: tuple[str, ...] = (
    "bhaisajyam",
    "ayusyam",
    "suktam",
    "mantroktam",
)

#: A conjunction inside the label. "bahudevatyam uta candramasam" is two ascriptions, so a
#: single-target resolution is wrong by construction and the label is split and reported.
CONJUNCTION = re.compile(r"\s+ut[aā]\s+|\s+ca\s+")

#: "of many deities". Deliberately not resolved: it names a plurality, not a deity.
PLURAL_HEAD = "bahu"


def fold(text: str) -> str:
    return comparison_form(text or "", ComparisonForm.SEARCH_NORMALIZED)


def parse_list(value: Any) -> list[str]:
    """Neo4j stores these list properties as their Python repr string."""
    if isinstance(value, list):
        return [str(v) for v in value]
    if not value:
        return []
    try:
        parsed = ast.literal_eval(str(value))
    except (ValueError, SyntaxError):
        return []
    return [str(v) for v in parsed] if isinstance(parsed, list) else []


def strip_suffix(folded: str) -> tuple[str, str] | None:
    for suffix in DEITY_ADJECTIVE_SUFFIXES:
        if folded.endswith(fold(suffix)) and len(folded) > len(fold(suffix)):
            return folded[: -len(fold(suffix))], suffix
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", default=str(OUT))
    args = parser.parse_args()

    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session(database=DB) as session:
            ascriptions = session.run(
                "MATCH (n:DevataAscription) RETURN n.entity_key AS key, n.label_iast AS label, "
                "n.occurrence_count AS occurrences"
            ).data()
            devatas = session.run(
                "MATCH (n:Devata) RETURN n.entity_key AS key, n.label_iast AS label_iast, "
                "n.preferred_label AS preferred, n.aliases_iast AS aliases, n.label_en AS label_en"
            ).data()
            # The claim being verified, not restated: the two layers' values share nothing.
            overlap = session.run(
                "MATCH ()-[:HAS_DEVATA]->(d:Devata) WITH collect(DISTINCT d.display_label) AS a "
                "MATCH ()-[:HAS_DEVATA_ASCRIPTION]->(x:DevataAscription) "
                "WITH a, collect(DISTINCT x.display_label) AS b "
                "RETURN size(a) AS left, size(b) AS right, "
                "size([v IN a WHERE v IN b]) AS shared"
            ).single()
            edge_counts = {
                rel: session.run(f"MATCH ()-[r:{rel}]->() RETURN count(r) AS n").single()["n"]
                for rel in ("HAS_DEVATA", "HAS_DEVATA_ASCRIPTION")
            }
    finally:
        driver.close()

    # Every folded surface a canonical Devata answers to. Built once; a stem resolves only
    # on an exact folded match, because a partial match is how a guess gets in.
    surfaces: dict[str, set[str]] = collections.defaultdict(set)
    for row in devatas:
        for value in (row["label_iast"], row["preferred"], *parse_list(row["aliases"])):
            folded = fold(str(value or ""))
            if folded:
                surfaces[folded].add(row["key"])

    resolved: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []
    unresolved: collections.defaultdict[str, list[dict[str, Any]]] = collections.defaultdict(list)

    for row in ascriptions:
        label = str(row["label"] or "")
        folded = fold(label)
        record = {
            "ascription_key": row["key"],
            "label": label,
            "occurrences": row["occurrences"],
        }

        if CONJUNCTION.search(label):
            unresolved["COMPOUND_TWO_ASCRIPTIONS"].append(record)
            continue
        if any(folded.startswith(fold(head)) for head in NON_DEITY_HEADS) or folded in {
            fold(head) for head in NON_DEITY_HEADS
        }:
            unresolved["NOT_A_DEITY_ASCRIPTION"].append(record)
            continue

        stripped = strip_suffix(folded)
        if stripped is None:
            unresolved["NO_RECOGNISED_DEITY_ADJECTIVE_SUFFIX"].append(record)
            continue
        stem, suffix = stripped
        record["stem"] = stem
        record["suffix"] = suffix

        if stem.startswith(fold(PLURAL_HEAD)):
            unresolved["NAMES_A_PLURALITY_NOT_A_DEITY"].append(record)
            continue

        candidates = surfaces.get(stem, set())
        if len(candidates) == 1:
            record["resolves_to"] = next(iter(candidates))
            resolved.append(record)
        elif len(candidates) > 1:
            record["candidates"] = sorted(candidates)
            ambiguous.append(record)
        else:
            unresolved["STEM_MATCHES_NO_CANONICAL_DEVATA"].append(record)

    total = len(ascriptions)
    unresolved_total = sum(len(v) for v in unresolved.values())
    occurrences_resolved = sum(int(r["occurrences"] or 0) for r in resolved)
    occurrences_total = sum(int(r["occurrences"] or 0) for r in ascriptions)

    report = {
        "schema_version": "1.0",
        "gap_id": "CROSS_VEDA_DEVATA_IDENTITY_BRIDGE",
        "owner_decision": (
            "section 9 -- treat as a separate implementation gap; bridge through canonical "
            "Devata identity, never through display labels; retain the unresolved form "
            "where resolution is not deterministic; do not guess"
        ),
        "mode": "PROBE_NO_WRITE",
        "the_defect_verified": {
            "has_devata_distinct_display_labels": overlap["left"],
            "has_devata_ascription_distinct_display_labels": overlap["right"],
            "shared_values": overlap["shared"],
            "edges": edge_counts,
            "why_zero_is_structural": (
                "HAS_DEVATA points at a :Devata whose display_label is an English deity "
                "name; HAS_DEVATA_ASCRIPTION points at a :DevataAscription whose "
                "display_label is a Sanskrit adjective meaning 'having X as its deity'. No "
                "normalisation of either label can close that, so the zero is a category "
                "difference rather than a coverage accident."
            ),
        },
        "deterministic_resolution": {
            "ascriptions": total,
            "resolved_to_exactly_one_devata": len(resolved),
            "resolved_share": round(len(resolved) / total, 4) if total else None,
            "ambiguous_two_or_more_devatas": len(ambiguous),
            "unresolved": unresolved_total,
            "ascription_occurrences_total": occurrences_total,
            "ascription_occurrences_resolved": occurrences_resolved,
            "occurrence_share_resolved": (
                round(occurrences_resolved / occurrences_total, 4) if occurrences_total else None
            ),
        },
        "unresolved_by_reason": {k: len(v) for k, v in sorted(unresolved.items())},
        "resolved_sample": resolved[:15],
        "ambiguous": ambiguous,
        "unresolved_detail": {k: v[:12] for k, v in sorted(unresolved.items())},
        "what_must_not_happen": [
            "joining the two dedication layers on display_label",
            "resolving an ambiguous stem by picking the more frequent Devata",
            "resolving a plurality ascription such as bahudevatyam to a single deity",
            "resolving a subject descriptor such as bhaisajyam to a deity at all",
        ],
        "blocks": ["semantic_resemblance TIER_B", "cross-Veda deity analytics"],
        "verdict": "GAP_SIZED_NOT_CLOSED",
    }

    pathlib.Path(args.json).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(args.json).write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )

    print()
    print("  CROSS_VEDA_DEVATA_IDENTITY_BRIDGE -- probe only, nothing written")
    print()
    defect = report["the_defect_verified"]
    print(
        f"  the defect: {defect['has_devata_distinct_display_labels']} HAS_DEVATA labels vs "
        f"{defect['has_devata_ascription_distinct_display_labels']} ascription labels, "
        f"sharing {defect['shared_values']}"
    )
    print(
        f"  edges: HAS_DEVATA {edge_counts['HAS_DEVATA']:,}  "
        f"HAS_DEVATA_ASCRIPTION {edge_counts['HAS_DEVATA_ASCRIPTION']:,}"
    )
    print()
    res = report["deterministic_resolution"]
    print(f"  of {res['ascriptions']} ascriptions, a deterministic parse resolves:")
    print(f"    to exactly one canonical Devata : {res['resolved_to_exactly_one_devata']:>4}"
          f"  ({res['resolved_share']:.1%})")
    print(f"    ambiguous, two or more          : {res['ambiguous_two_or_more_devatas']:>4}")
    print(f"    unresolved                      : {res['unresolved']:>4}")
    print()
    print("  unresolved, by reason:")
    for reason, count in report["unresolved_by_reason"].items():
        print(f"    {reason:42}{count:>5}")
    print()
    print(
        f"  weighted by occurrence: {res['ascription_occurrences_resolved']:,} of "
        f"{res['ascription_occurrences_total']:,} "
        f"({res['occurrence_share_resolved']:.1%})"
    )
    print()
    print(f"  VERDICT: {report['verdict']}")
    print(f"  report: {args.json}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
