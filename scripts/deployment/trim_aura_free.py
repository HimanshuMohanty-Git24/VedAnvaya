"""Create the AuraDB Free graph profile from an isolated Neo4j copy.

This script only connects to the URI passed on its command line. It never reads local settings
and refuses the normal development Bolt port, so it cannot trim the developer's Neo4j container.
"""

from __future__ import annotations

import argparse
import json
import sys

from neo4j import GraphDatabase

LOCAL_DEVELOPMENT_URIS = frozenset({"bolt://localhost:7687", "bolt://127.0.0.1:7687"})
REMOVED_TYPE = "MENTIONS_LEMMA"
AURA_FREE_RELATIONSHIP_LIMIT = 400_000


def count(session: object, cypher: str) -> int:
    row = session.run(cypher).single()  # type: ignore[attr-defined]
    assert row is not None
    return int(row["count"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Trim an isolated graph for AuraDB Free")
    parser.add_argument("--uri", required=True, help="isolated staging Neo4j Bolt URI")
    parser.add_argument("--user", default="neo4j")
    parser.add_argument("--password", required=True)
    parser.add_argument("--database", default="neo4j")
    args = parser.parse_args()

    if args.uri.rstrip("/") in LOCAL_DEVELOPMENT_URIS:
        parser.error("refusing the normal local development Neo4j port")

    driver = GraphDatabase.driver(args.uri, auth=(args.user, args.password))
    try:
        with driver.session(database=args.database) as session:
            before = count(session, "MATCH ()-[r]->() RETURN count(r) AS count")
            removable = count(session, f"MATCH ()-[r:{REMOVED_TYPE}]->() RETURN count(r) AS count")
            summary = session.run(
                f"MATCH ()-[r:{REMOVED_TYPE}]->() DELETE r RETURN count(r) AS deleted"
            ).single()
            assert summary is not None
            deleted = int(summary["deleted"])
            after = count(session, "MATCH ()-[r]->() RETURN count(r) AS count")
            nodes = count(session, "MATCH (n) RETURN count(n) AS count")
    finally:
        driver.close()

    result = {
        "profile": "aura_free",
        "removed_relationship_type": REMOVED_TYPE,
        "relationships_before": before,
        "relationships_expected_to_remove": removable,
        "relationships_removed": deleted,
        "relationships_after": after,
        "nodes_after": nodes,
        "within_aura_free_relationship_limit": after <= AURA_FREE_RELATIONSHIP_LIMIT,
    }
    print(json.dumps(result, indent=2))
    if deleted != removable or after != before - deleted:
        raise SystemExit("trim verification failed: relationship counts do not reconcile")
    if after > AURA_FREE_RELATIONSHIP_LIMIT:
        raise SystemExit("trim verification failed: graph exceeds AuraDB Free's relationship limit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
