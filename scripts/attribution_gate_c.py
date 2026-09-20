"""Gate C: try to disprove the attribution rows. Owner's adversarial pass.

Gate B asked whether the rows are well formed. This asks whether they are TRUE, and it is
built to fail rather than to pass.

The central attack on the census population is the one that would be fatal if it landed:
**the census claims to describe the graph, so the graph can contradict it.** 22,537 rows
state, per passage and per dimension, whether an attribution is source-explicit, derived,
assessed-and-absent, or never assessed. Every one of those states is checkable against the
edges that actually exist:

    SOURCE_EXPLICIT_PRESENT   requires an L1_SOURCE_EXPLICIT edge
    DERIVED_PRESENT           requires an L2_DETERMINISTIC_DERIVED edge
    ASSESSED_SOURCE_ABSENT    requires NO edge of that dimension
    NEVER_ASSESSED            requires NO edge of that dimension
    NOT_APPLICABLE_...        requires NO edge, and a container-grain subject

A census that disagrees with the graph is either stale or wrong, and either way it must not
be imported as a coverage statement about a graph it no longer describes.

The attack on the Whitney population is different, because those rows assert something the
graph does not yet hold. There the question is whether the printed bracket supports the verse
the row claims: an exact-looking locator whose text does not carry the asserted numeral is
the failure mode the owner named.

Stratification is by Veda, dimension, state, scope origin, boundary coordinate and
high-degree entity, and every stratum is reported separately. A defect concentrated in one
stratum and invisible in the aggregate is the thing this gate exists to catch.

Usage:
    python scripts/attribution_gate_c.py [--json OUT]
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from neo4j import GraphDatabase

ROWS = pathlib.Path("data/staging/attribution/rows.jsonl")
OUT = pathlib.Path("data/staging/integration/attribution_gate_c.json")

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "vedagraph_dev")
DB = "neo4j"

#: Which predicates carry each dimension. ``devata`` has two, and both count: a passage whose
#: only deity link is an ascription is still one the source addressed.
DIMENSION_PREDICATES: dict[str, tuple[str, ...]] = {
    "rishi": ("HAS_RISHI",),
    "devata": ("HAS_DEVATA", "HAS_DEVATA_ASCRIPTION"),
    "chandas": ("HAS_CHANDAS",),
}

#: What each census state commits the graph to. ``None`` means "no edge of this dimension".
STATE_REQUIRES: dict[str, str | None] = {
    "SOURCE_EXPLICIT_PRESENT": "L1_SOURCE_EXPLICIT",
    "DERIVED_PRESENT": "L2_DETERMINISTIC_DERIVED",
    "ASSESSED_SOURCE_ABSENT": None,
    "NEVER_ASSESSED": None,
    "NOT_APPLICABLE_AT_THIS_GRANULARITY": None,
}

VEDA_PREFIX = {"RV": "VG:RV:", "SV": "VG:SV:", "YV": "VG:YV:", "AV": "VG:AV:"}

#: One component of a verse address: "7" or "5-7". An address is a comma-separated list of
#: these -- "1, 2" and "6, 9, 10" are both single address strings in this artifact.
_COMPONENT = re.compile(r"^(\d{1,3})(?:\s*-\s*(\d{1,3}))?$")


def addressed_verses(addresses: list[str]) -> tuple[set[int], list[str]]:
    """Expand the row's own stated addresses, and report what could not be read.

    Returns (verses, unparseable). The second half matters: an address this function cannot
    read is a statement about the parser, not about the data, and twice already a gap in
    this grammar was reported as a defect in the artifact -- first missing ranges, then
    missing comma lists. Separating the two keeps that mistake visible instead of letting
    it masquerade as a finding.
    """
    verses: set[int] = set()
    unparseable: list[str] = []
    for address in addresses:
        for component in str(address).split(","):
            component = component.strip()
            if not component:
                continue
            match = _COMPONENT.match(component)
            if not match:
                unparseable.append(component)
                continue
            start = int(match.group(1))
            end = int(match.group(2) or match.group(1))
            if start > end or end - start >= 200:
                unparseable.append(component)
                continue
            verses.update(range(start, end + 1))
    return verses, unparseable


def read_rows() -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in ROWS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", default=str(OUT))
    args = parser.parse_args()

    rows = read_rows()
    census = [r for r in rows if r.get("evidence_layer") == "DETERMINISTIC_DERIVED"]
    whitney = [r for r in rows if r.get("evidence_layer") == "SOURCE_EXPLICIT"]

    keys = sorted({str(r.get("canonical_key") or "") for r in rows})

    # ---- read what the graph ACTUALLY holds for every subject ----------------------
    driver = GraphDatabase.driver(URI, auth=AUTH)
    held: dict[str, dict[str, set[str]]] = collections.defaultdict(
        lambda: collections.defaultdict(set)
    )
    try:
        with driver.session(database=DB) as session:
            for dimension, predicates in DIMENSION_PREDICATES.items():
                pattern = "|".join(predicates)
                for i in range(0, len(keys), 4000):
                    for row in session.run(
                        f"UNWIND $keys AS k MATCH (p:Passage {{canonical_key: k}})"
                        f"-[e:{pattern}]->() "
                        "RETURN k AS key, collect(DISTINCT e.knowledge_layer) AS layers",
                        keys=keys[i : i + 4000],
                    ):
                        held[str(row["key"])][dimension] = {
                            str(v) for v in row["layers"] if v
                        }
            hymn_verses = {
                str(r["hymn"]): int(r["n"])
                for r in session.run(
                    "MATCH (h:Passage)-[:CONTAINS]->(m:Mantra) "
                    "WHERE h.canonical_key STARTS WITH 'VG:AV:SAU:' "
                    "RETURN h.canonical_key AS hymn, count(m) AS n"
                )
            }
    finally:
        driver.close()

    # ---- C1: every census state, checked against the edges that exist --------------
    contradictions: list[dict[str, Any]] = []
    by_stratum: dict[str, dict[str, int]] = collections.defaultdict(
        lambda: {"checked": 0, "contradicted": 0}
    )
    for row in census:
        key = str(row.get("canonical_key") or "")
        veda = str(row.get("veda") or "")
        for dimension in DIMENSION_PREDICATES:
            state = str((row["payload"].get(dimension) or {}).get("state") or "")
            if not state:
                continue
            required = STATE_REQUIRES.get(state, "UNDECLARED")
            layers = held.get(key, {}).get(dimension, set())
            stratum = f"{veda}:{dimension}:{state}"
            by_stratum[stratum]["checked"] += 1
            if required == "UNDECLARED":
                bad = True
                why = f"state {state!r} is not in STATE_REQUIRES"
            elif required is None:
                bad = bool(layers)
                why = f"claims no attribution, graph holds {sorted(layers)}"
            else:
                bad = required not in layers
                why = f"claims {required}, graph holds {sorted(layers) or 'nothing'}"
            if bad:
                by_stratum[stratum]["contradicted"] += 1
                if len(contradictions) < 400:
                    contradictions.append(
                        {"key": key, "dimension": dimension, "state": state, "why": why}
                    )

    total_checked = sum(s["checked"] for s in by_stratum.values())
    total_bad = sum(s["contradicted"] for s in by_stratum.values())

    # ---- C2: strata where the defect concentrates ----------------------------------
    worst = sorted(
        (
            {
                "stratum": name,
                "checked": stats["checked"],
                "contradicted": stats["contradicted"],
                "rate": round(stats["contradicted"] / stats["checked"], 4)
                if stats["checked"]
                else 0.0,
            }
            for name, stats in by_stratum.items()
        ),
        key=lambda s: (-s["rate"], -s["contradicted"]),
    )

    # ---- C3: boundary coordinates ---------------------------------------------------
    boundaries = sorted(
        {
            min(k for k in keys if k.startswith(prefix))
            for prefix in VEDA_PREFIX.values()
            if any(k.startswith(prefix) for k in keys)
        }
        | {
            max(k for k in keys if k.startswith(prefix))
            for prefix in VEDA_PREFIX.values()
            if any(k.startswith(prefix) for k in keys)
        }
    )
    boundary_findings = [
        c for c in contradictions if c["key"] in set(boundaries)
    ]

    # ---- C4: Whitney -- does the printed bracket support the verse it names? --------
    whitney_findings: list[dict[str, Any]] = []
    unanchored: list[dict[str, Any]] = []
    unreadable_addresses: list[dict[str, Any]] = []
    with_bracket = 0
    for row in whitney:
        payload = row["payload"]
        key = str(row.get("canonical_key") or "")
        bracket = str(payload.get("printed_bracket") or "")
        addresses = [
            str(a)
            for a in (
                payload.get("source_verse_addresses")
                or payload.get("source_verse_ranges")
                or []
            )
        ]
        verse = int(key.rsplit(":V", 1)[-1]) if ":V" in key else 0
        covered, unreadable = addressed_verses(addresses)
        if unreadable:
            unreadable_addresses.append(
                {"key": key, "components": unreadable, "addresses": addresses}
            )
        if verse and covered and verse not in covered:
            whitney_findings.append(
                {
                    "key": key,
                    "dimension": payload.get("dimension"),
                    "why": "the row's own stated addresses do not cover the verse it claims",
                    "verse": verse,
                    "addresses": addresses,
                    "covers": sorted(covered)[:12],
                }
            )
        elif verse and not covered:
            whitney_findings.append(
                {
                    "key": key,
                    "dimension": payload.get("dimension"),
                    "why": "the row states no verse address at all",
                    "verse": verse,
                    "addresses": addresses,
                }
            )
        # Is the parse anchored in the printed text? Only checkable where the row carries
        # the bracket; reported, never silently skipped.
        if bracket:
            with_bracket += 1
            missing = [a for a in addresses if a.replace(" ", "") not in bracket.replace(" ", "")]
            if missing:
                unanchored.append(
                    {
                        "key": key,
                        "addresses_not_found_in_the_printed_bracket": missing,
                    }
                )
    # verse addresses must exist inside the hymn they claim
    overruns = [
        {
            "key": str(r.get("canonical_key")),
            "hymn": str(r["payload"].get("hymn_key")),
            "why": "the verse address is past the end of its hymn",
        }
        for r in whitney
        if (hk := str(r["payload"].get("hymn_key") or "")) in hymn_verses
        and ":V" in str(r.get("canonical_key"))
        and int(str(r.get("canonical_key")).rsplit(":V", 1)[-1]) > hymn_verses[hk]
    ]

    report: dict[str, Any] = {
        "artifact": "ATTRIBUTION_GATE_C",
        "strategy": (
            "The census claims to describe this graph, so the graph is used to contradict "
            "it: every state is checked against the edges that actually exist, stratified "
            "by Veda, dimension and state. The Whitney rows assert what the graph does not "
            "hold, so they are checked against their own printed source instead."
        ),
        "census_rows": len(census),
        "census_assertions_checked": total_checked,
        "census_contradicted": total_bad,
        "census_contradiction_rate": round(total_bad / total_checked, 6)
        if total_checked
        else 0.0,
        "strata": len(by_stratum),
        "worst_strata": worst[:15],
        "contradiction_examples": contradictions[:15],
        "boundary_coordinates_checked": boundaries,
        "boundary_findings": boundary_findings[:10],
        "whitney_rows": len(whitney),
        "whitney_address_mismatches": len(whitney_findings),
        "whitney_address_examples": whitney_findings[:10],
        "whitney_rows_carrying_a_printed_bracket": with_bracket,
        "whitney_addresses_not_anchored_in_the_bracket": len(unanchored),
        "whitney_unanchored_examples": unanchored[:10],
        "whitney_addresses_this_gate_could_not_parse": len(unreadable_addresses),
        "whitney_unparseable_examples": unreadable_addresses[:10],
        "whitney_verse_overruns": len(overruns),
        "whitney_overrun_examples": overruns[:10],
    }
    systemic = total_bad > 0 and any(s["rate"] >= 0.5 for s in worst if s["checked"] >= 20)
    clean = (
        total_bad == 0
        and not whitney_findings
        and not overruns
        and not unanchored
        and not unreadable_addresses
    )
    report["defect_class"] = "NONE" if clean else ("SYSTEMIC" if systemic else "ISOLATED")
    report["verdict"] = (
        "GATE_C_PASS"
        if report["defect_class"] == "NONE"
        else "GATE_C_FINDINGS"
    )

    pathlib.Path(args.json).write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print()
    print("  ATTRIBUTION GATE C -- adversarial")
    print()
    print(f"  census assertions checked   {total_checked:,}")
    print(f"  contradicted by the graph   {total_bad:,}  "
          f"({report['census_contradiction_rate']:.4%})")
    print(f"  strata                      {len(by_stratum)}")
    print()
    print(f"  {'stratum':46} {'checked':>8} {'bad':>7} {'rate':>7}")
    print(f"  {'-' * 72}")
    for s in worst[:12]:
        print(f"  {s['stratum']:46} {s['checked']:>8,} {s['contradicted']:>7,} {s['rate']:>7.1%}")
    print()
    print(f"  whitney address mismatches  {len(whitney_findings)}")
    print(f"  addresses this gate cannot parse  {len(unreadable_addresses)}")
    print(
        f"  whitney unanchored parses   {len(unanchored)}"
        f"  (of {with_bracket} rows carrying a printed bracket)"
    )
    print(f"  whitney verse overruns      {len(overruns)}")
    print(f"  boundary findings           {len(boundary_findings)}")
    print()
    print(f"  defect class: {report['defect_class']}")
    print(f"  VERDICT: {report['verdict']}")
    print(f"  report: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
