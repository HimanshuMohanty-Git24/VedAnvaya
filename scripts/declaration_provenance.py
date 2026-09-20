"""Where every relationship type and node label is declared, and by whom. Owner Phase A.

The repaired gate answers "is this declared?". This answers "declared *where*?", which is the
question a reviewer needs in order to check the gate is reading an authority rather than a
convenient list.

One row per populated relationship type and per node label, naming the layer constant it
comes from. Unused declarations are listed separately with the reason they exist: an empty
predicate is architecture when something says so and an accident otherwise, and the
difference is only visible if both are written down.

Nothing here writes.

Usage:
    python scripts/declaration_provenance.py [--json OUT]
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from neo4j import GraphDatabase

from vedagraph.domain.ontology import (
    CAMPAIGN_RELATIONSHIP_TYPES,
    CORPUS_RELATIONSHIP_TYPES,
    DOMAIN_RELATIONSHIP_TYPES,
    INTERNAL_LABELS,
    PRODUCT_LABELS,
    SYSTEM_RELATIONSHIP_TYPES,
    all_declared_relationship_types,
    all_endpoint_signatures,
)
from vedagraph.domain.ontology import UNPOPULATED_BY_DESIGN as DOMAIN_UNPOPULATED

OUT = pathlib.Path("data/staging/integration/declaration_provenance.json")

URI = "bolt://localhost:7687"
AUTH = ("neo4j", "vedagraph_dev")
DB = "neo4j"


def source_of(predicate: str) -> str:
    """The layer constant a predicate is declared in. Checked in declaration order."""
    from vedagraph.enrich.predicates import CONTROLLED_PREDICATES

    for name, members in (
        ("ontology.DOMAIN_RELATIONSHIP_TYPES", DOMAIN_RELATIONSHIP_TYPES),
        ("ontology.CORPUS_RELATIONSHIP_TYPES", CORPUS_RELATIONSHIP_TYPES),
        ("ontology.CAMPAIGN_RELATIONSHIP_TYPES", CAMPAIGN_RELATIONSHIP_TYPES),
        ("enrich.predicates.CONTROLLED_PREDICATES", CONTROLLED_PREDICATES),
        ("ontology.SYSTEM_RELATIONSHIP_TYPES", SYSTEM_RELATIONSHIP_TYPES),
    ):
        if predicate in members:
            return name
    return "UNDECLARED"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", default=str(OUT))
    args = parser.parse_args()

    from vedagraph.enrich.predicates import UNPOPULATED_BY_DESIGN as ENRICH_UNPOPULATED

    declared = all_declared_relationship_types()
    every_signature = all_endpoint_signatures()

    driver = GraphDatabase.driver(URI, auth=AUTH)
    try:
        with driver.session(database=DB) as session:
            types = sorted(
                str(r["t"])
                for r in session.run(
                    "CALL db.relationshipTypes() YIELD relationshipType AS t RETURN t"
                )
            )
            edges = {
                t: int(
                    session.run(f"MATCH ()-[r:`{t}`]->() RETURN count(r) AS c").single()["c"]
                )
                for t in types
            }
            labels = sorted(
                str(r["l"]) for r in session.run("CALL db.labels() YIELD label AS l RETURN l")
            )
            label_counts = {
                label: int(
                    session.run(f"MATCH (n:`{label}`) RETURN count(n) AS c").single()["c"]
                )
                for label in labels
            }
    finally:
        driver.close()

    populated = {t: n for t, n in edges.items() if n > 0}
    rows = [
        {
            "predicate": t,
            "edges": n,
            "declared_in": source_of(t),
            "signature_enforced": t in every_signature,
            "subject_labels": sorted(every_signature[t][0]) if t in every_signature else [],
            "object_labels": sorted(every_signature[t][1]) if t in every_signature else [],
        }
        for t, n in sorted(populated.items())
    ]

    unused = sorted(declared - set(populated))
    unused_rows = [
        {
            "predicate": t,
            "declared_in": source_of(t),
            "declared_unpopulated_on_purpose": t in DOMAIN_UNPOPULATED
            or t in ENRICH_UNPOPULATED,
            "reason": DOMAIN_UNPOPULATED.get(t) or ENRICH_UNPOPULATED.get(t),
        }
        for t in unused
    ]

    label_rows = [
        {
            "label": label,
            "nodes": label_counts[label],
            "classification": (
                "PRODUCT"
                if label in PRODUCT_LABELS
                else "INTERNAL"
                if label in INTERNAL_LABELS
                else "UNCLASSIFIED"
            ),
        }
        for label in labels
    ]

    report: dict[str, Any] = {
        "artifact": "DECLARATION_PROVENANCE",
        "owner_phase": "A",
        "authority": (
            "vedagraph.domain.ontology.all_declared_relationship_types(), which composes each "
            "layer's own declaration. The graph is not an input to it."
        ),
        "declared_total": len(declared),
        "graph_types_total": len(types),
        "graph_types_populated": len(populated),
        "undeclared_populated": sorted(set(populated) - declared),
        "declared_but_unused": unused_rows,
        "system_exceptions": sorted(SYSTEM_RELATIONSHIP_TYPES),
        "signature_coverage": {
            "predicates_with_a_signature": len(every_signature),
            "populated_predicates_without_one": sorted(
                t for t in populated if t not in every_signature
            ),
        },
        "predicates": rows,
        "labels": label_rows,
        "unclassified_labels": [
            r["label"] for r in label_rows if r["classification"] == "UNCLASSIFIED"
        ],
    }
    pathlib.Path(args.json).write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    print()
    print("  DECLARATION PROVENANCE")
    print()
    print(f"  declared {len(declared)}   graph types {len(types)}   populated {len(populated)}")
    print(f"  undeclared populated      {report['undeclared_populated'] or 'none'}")
    print(
        "  populated without a signature  "
        f"{report['signature_coverage']['populated_predicates_without_one'] or 'none'}"
    )
    print(f"  unclassified labels       {report['unclassified_labels'] or 'none'}")
    print()
    by_source: dict[str, int] = {}
    for row in rows:
        by_source[str(row["declared_in"])] = by_source.get(str(row["declared_in"]), 0) + 1
    for name, n in sorted(by_source.items()):
        print(f"    {n:>3} populated predicates declared in {name}")
    print()
    print(
        f"  declared but unused: {len(unused_rows)} "
        f"({sum(1 for r in unused_rows if r['declared_unpopulated_on_purpose'])} "
        "with a stated reason)"
    )
    print(f"  report: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
