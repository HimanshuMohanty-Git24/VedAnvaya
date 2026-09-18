#!/usr/bin/env python3
"""Stage GAP-ATTRIBUTION-002 clause 1: the descriptors the suffix matcher could not reach.

Clause 1 asks that every *resolvable* descriptor reach a ``:Devata``. R3 measured why 41 of
the 210 ``UNRESOLVED_STEM_MATCHES_NO_CANONICAL_DEVATA`` descriptors were not merely failing
to match but generating **no candidate at all**:
:data:`~vedagraph.domain.ascription_bridge.DEITY_ADJECTIVE_SUFFIXES` spells the suffix with
a short a and Whitney prints the vṛddhi form, and suffix stripping ran before any length
folding, so the ``LENGTH_INSENSITIVE`` tier that ``resolve_one`` applies to the candidate
*stem* never received a stem.

:func:`~vedagraph.domain.ascription_bridge.suffix_candidates` now matches the suffix at two
tiers and slices the stem out of the source fold, so the looseness reaches the suffix and
stops there. This script measures what that produced and stages it. It writes nothing to
the graph.

Measured when written: 41 descriptors gained a candidate, of which **8 resolve** and 33
still match no canonical Devatā -- which is the honest outcome and the reason candidate
generation is reported apart from resolution. Resolutions go 39 -> 47 with **0
regressions**: every one of the 39 already-resolved descriptors resolves to the same
``:Devata`` by the same path.

Usage:
    python scripts/r4_stage_attribution_002.py
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

from vedagraph.domain.ascription_bridge import (  # noqa: E402
    CONTRACT_VERSION,
    SurfaceIndex,
    length_collisions,
    resolve_one,
    suffix_candidates,
    vrddhi_candidates,
)
from vedagraph.domain.ascription_bridge import fold as fold_label  # noqa: E402

OUT: Final = PROJECT_ROOT / "data" / "staging" / "release_blocker_r4" / "attribution_002"
URI: Final = "bolt://localhost:7687"
AUTH: Final = ("neo4j", "vedagraph_dev")
DB: Final = "neo4j"
TIMEOUT: Final[float] = 300.0

#: The property contract every ASCRIBES_TO_DEVATA edge already carries, read off the live
#: layer rather than reinvented, so a staged edge is indistinguishable in shape from the 39.
EDGE_CONTRACT: Final[dict[str, str]] = {
    "knowledge_layer": "L2_DETERMINISTIC_DERIVED",
    "ascription_bridge_version": CONTRACT_VERSION,
    "evidence_basis": "SOURCE_METADATA",
    "ascription_resolution_method": "TADDHITA_SASYA_DEVATA_DERIVATION",
    # A float, not the string "1.0". The other 39 edges carry a float and a string here
    # made ASCRIBES_TO_DEVATA read as two distinct confidence values, which tripped the
    # constant-predicate invariant.
    "confidence": 1.0,
    "attribution_precision": "NOT_AN_ATTRIBUTION",
    "quality_tier": "TIER_B",
}


def main() -> int:
    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session(database=DB) as session:
            ascriptions = [
                dict(record)
                for record in session.run(
                    Query(
                        """
                        MATCH (a:DevataAscription)
                        OPTIONAL MATCH (a)-[e:ASCRIBES_TO_DEVATA]->(d:Devata)
                        RETURN a.entity_key AS entity_key, a.label_iast AS label_iast,
                               a.occurrence_count AS occurrence_count,
                               a.ascription_resolution_status AS stored_status,
                               a.ascription_unresolved_reason AS stored_reason,
                               d.entity_key AS stored_devata_key,
                               e.ascription_resolution_path AS stored_path
                        ORDER BY a.entity_key
                        """,
                        timeout=TIMEOUT,
                    )
                )
            ]
            devatas = [
                dict(record)
                for record in session.run(
                    Query(
                        "MATCH (d:Devata) RETURN d.entity_key AS entity_key, "
                        "d.label_iast AS label_iast, d.preferred_label AS preferred_label, "
                        "d.aliases_iast AS aliases_iast",
                        timeout=TIMEOUT,
                    )
                )
            ]
    finally:
        driver.close()

    index = SurfaceIndex.build(devatas)
    resolutions = {row["entity_key"]: resolve_one(row, index) for row in ascriptions}

    # Candidate generation, reported apart from resolution. A descriptor that generates a
    # candidate whose stem is no canonical deity is correctly unresolved; conflating the two
    # is how a matcher's reach gets overstated.
    candidate_generated: list[str] = []
    no_candidate: list[dict[str, Any]] = []
    for row in ascriptions:
        folded = fold_label(row["label_iast"] or "")
        if suffix_candidates(folded) or vrddhi_candidates(folded):
            candidate_generated.append(row["entity_key"])
        else:
            no_candidate.append(
                {
                    "entity_key": row["entity_key"],
                    "label_iast": row["label_iast"],
                    "folded": folded,
                    "reason": (
                        "Neither the explicit deity-adjective suffix family nor the vṛddhi "
                        "taddhita reversal produces a stem from this surface."
                    ),
                }
            )

    new_edges: list[dict[str, Any]] = []
    regressions: list[dict[str, Any]] = []
    unchanged_resolved = 0
    for row in ascriptions:
        resolution = resolutions[row["entity_key"]]
        was_resolved = row["stored_status"] == "RESOLVED_TO_CANONICAL_DEVATA"
        now_resolved = resolution.status == "RESOLVED_TO_CANONICAL_DEVATA"
        if was_resolved:
            if now_resolved and resolution.devata_key == row["stored_devata_key"]:
                unchanged_resolved += 1
            else:
                regressions.append(
                    {
                        "entity_key": row["entity_key"],
                        "label_iast": row["label_iast"],
                        "stored_devata_key": row["stored_devata_key"],
                        "now_status": resolution.status,
                        "now_devata_key": resolution.devata_key,
                    }
                )
            continue
        if now_resolved:
            new_edges.append(
                {
                    "ascription_key": row["entity_key"],
                    "label_iast": row["label_iast"],
                    "devata_key": resolution.devata_key,
                    "occurrence_count": row["occurrence_count"],
                    "previous_status": row["stored_status"],
                    "previous_reason": row["stored_reason"],
                    "edge_properties": {
                        **EDGE_CONTRACT,
                        "ascription_resolution_path": resolution.derivation_path,
                        "ascription_resolution_comparison_tier": resolution.comparison_tier,
                        "ascription_resolution_stem": resolution.stem,
                        **(
                            {"ascription_resolution_taddhita_suffix": resolution.taddhita_suffix}
                            if resolution.taddhita_suffix
                            else {}
                        ),
                    },
                    "reason": resolution.reason,
                }
            )
        elif resolution.status != row["stored_status"]:
            regressions.append(
                {
                    "entity_key": row["entity_key"],
                    "label_iast": row["label_iast"],
                    "stored_status": row["stored_status"],
                    "now_status": resolution.status,
                }
            )

    statuses = collections.Counter(r.status for r in resolutions.values())
    paths = collections.Counter(
        r.derivation_path
        for r in resolutions.values()
        if r.status == "RESOLVED_TO_CANONICAL_DEVATA"
    )

    report = {
        "artifact": "R4_ATTRIBUTION_002_CLAUSE_1_STAGING",
        "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "gap_id": "GAP-ATTRIBUTION-002",
        "clause": 1,
        "descriptor_total": len(ascriptions),
        "candidate_generated": len(candidate_generated),
        "no_candidate_generated": len(no_candidate),
        "resolved": statuses.get("RESOLVED_TO_CANONICAL_DEVATA", 0),
        "resolved_before": unchanged_resolved,
        "newly_resolved": len(new_edges),
        "resolved_by_path": dict(paths),
        "status_distribution": dict(statuses),
        "regressions": regressions,
        "unresolved_with_an_explicit_reason": {
            status: count for status, count in statuses.items() if status.startswith("UNRESOLVED")
        },
        # The looser stem tier's price, enumerated over the live registry rather than
        # assumed. Over- and under-normalising both look like a clean run.
        "length_tier_collisions": length_collisions(devatas),
        "new_edges": new_edges,
        "no_candidate_detail": no_candidate,
    }

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "staging.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )

    print()
    print("  GAP-ATTRIBUTION-002 CLAUSE 1 -- STAGED")
    print()
    print(f"  descriptor total        {report['descriptor_total']}")
    print(f"  candidate generated     {report['candidate_generated']}")
    print(f"  no candidate            {report['no_candidate_generated']}")
    print(f"  resolved                {report['resolved']}  "
          f"(was {report['resolved_before']}, +{report['newly_resolved']})")
    print(f"  by path                 {report['resolved_by_path']}")
    print(f"  regressions             {len(report['regressions'])}")
    print()
    for edge in new_edges:
        print(f"    {edge['label_iast']:<26} -> {edge['devata_key']:<30} "
              f"{edge['edge_properties']['ascription_resolution_comparison_tier']}")
    print()
    print(f"  staged: {(OUT / 'staging.json').relative_to(PROJECT_ROOT)}")
    print()
    return 1 if regressions else 0


if __name__ == "__main__":
    sys.exit(main())
