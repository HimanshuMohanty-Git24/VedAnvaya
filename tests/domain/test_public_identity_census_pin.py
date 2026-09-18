"""The public-identity census pin, asserted as a test rather than only as an assert.

``scripts/audit_public_identity.py`` pins the graph census so an unexpected mutation
cannot slip past the audit. Its own comment records what went wrong with that design
once already (Agent B's C06): the assert *aborts* the script, so when an authorised
import moved the census and nobody moved the pin, the audit stopped reporting entirely
instead of reporting a failure. Nothing was wired to a gate, so the silence was invisible.

That recurred at ``360d9c5``, when the receipted GAP-SAMAVEDA_MUSIC-002 import added
1,136 TextVersion nodes and 1,136 HAS_TEXT_VERSION relationships and the pin stayed at
the pre-import figures. The audit had been unrunnable ever since, and no release check
noticed, because a script that raises before its first finding produces no findings.

This test is the wiring. It reads the pin out of the script's source and compares it to
the live graph, so a future authorised import fails *red* here -- naming both numbers --
instead of silently disabling the public-identity audit. It deliberately does not import
the script: that would execute the audit, which is slow and needs the full graph.
"""

from __future__ import annotations

import ast
import os
import pathlib
import sys
from typing import Any

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

_AUDIT = PROJECT_ROOT / "scripts" / "audit_public_identity.py"

_LIVE = pytest.mark.skipif(
    not os.environ.get("VEDAGRAPH_LIVE_NEO4J"),
    reason="set VEDAGRAPH_LIVE_NEO4J=1 to run against the local Neo4j instance",
)


def _pinned_census() -> dict[str, int]:
    """The literal the audit asserts, read from source without running it."""
    tree = ast.parse(_AUDIT.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assert) or not isinstance(node.test, ast.Compare):
            continue
        left, comparators = node.test.left, node.test.comparators
        if not (isinstance(left, ast.Name) and left.id == "census" and comparators):
            continue
        value = ast.literal_eval(comparators[0])
        assert isinstance(value, dict)
        return value
    raise AssertionError(f"no `assert census == {{...}}` found in {_AUDIT}")


def _live_census() -> dict[str, int]:
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "vedagraph_dev"))
    try:
        with driver.session(default_access_mode="READ") as session:
            return {
                "nodes": session.run("MATCH (n) RETURN count(n) AS n").single()["n"],
                "relationships": session.run(
                    "MATCH ()-[r]->() RETURN count(r) AS n"
                ).single()["n"],
            }
    finally:
        driver.close()


def test_the_pin_is_a_two_key_census() -> None:
    """Parsed without a live graph, so a malformed pin fails even when Neo4j is down."""
    pinned: dict[str, Any] = _pinned_census()
    assert sorted(pinned) == ["nodes", "relationships"]
    assert all(isinstance(v, int) and v > 0 for v in pinned.values())


@_LIVE
def test_pinned_census_matches_the_live_graph() -> None:
    pinned, live = _pinned_census(), _live_census()
    assert pinned == live, (
        f"scripts/audit_public_identity.py pins {pinned} but the graph holds {live}. "
        "If the delta is an authorised, receipted migration, move the pin AND record the "
        "reconciliation in the comment above it. Until then the public-identity audit "
        "aborts before its first finding rather than reporting one."
    )
