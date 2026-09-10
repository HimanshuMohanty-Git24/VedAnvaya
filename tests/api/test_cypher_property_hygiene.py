"""Every property the API's Cypher reads must exist in the graph.

**The failure this catches.** Neo4j does not error on a property that does not exist. It
returns null. So ``RETURN a.modality`` against a label with no ``modality`` property is a
successful query, a valid response, a passing test and a field the frontend renders blank
forever -- and the only signal is a driver notification nobody reads, because it arrives
attached to a 4,000-character query string.

That was found in this build by accident, in warning output from a demo run. Once is luck;
this test makes it systematic. It extracts every ``alias.property`` reference from the
Cypher in the API package and checks each name against ``db.propertyKeys()``.

**What it deliberately does not do.** It does not resolve aliases to labels, so it cannot
tell that ``devata.family_key`` is wrong while ``family.family_key`` is right -- that would
need a full parser and a schema model. It checks the weaker and still valuable property:
that the name exists *somewhere* in the graph. A typo, a renamed property and a field
invented from a plausible guess all fail here, which covers the case that actually occurred.

``KNOWN_NON_GRAPH_NAMES`` holds the identifiers that look like property reads and are not:
map keys the queries build for their own return shapes, and procedure namespaces.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Final

import pytest

from vedagraph.api.repositories.neo4j_repository import Neo4jRepository

API_ROOT: Final = Path(__file__).resolve().parents[2] / "src" / "vedagraph" / "api"

#: ``alias.name`` where alias starts lowercase. Deliberately narrow: Cypher aliases in this
#: codebase are lowercase and Python attribute access on capitalised names would otherwise
#: flood the result with ``self.``-style matches from the surrounding Python.
_PROPERTY_REFERENCE: Final = re.compile(r"\b([a-z][A-Za-z0-9_]*)\.([a-z][A-Za-z0-9_]*)\b")

#: A string literal is Cypher if it contains a clause keyword. Used to sort query text from
#: the surrounding Python once the AST has handed us every string in the module.
_CYPHER_CLAUSE: Final = re.compile(r"\b(MATCH|RETURN|WITH|UNWIND|CALL|WHERE|SHOW)\b")

#: Aliases that hold a map the query built itself, not a node. ``item.rel`` reads a key out
#: of a collected map and has nothing to do with the graph schema.
#:
#: Scoped by *alias* rather than by property name on purpose. Excusing the names -- ``rel``,
#: ``node``, ``near``, ``far`` -- would also excuse a genuine typo that happened to collide
#: with one of them, and the whole value of this test is that it does not excuse typos.
MAP_ALIASES: Final[frozenset[str]] = frozenset({"item", "row", "hop", "entry", "pair", "step"})

#: Identifiers that are not graph properties: Python attribute access that survived the
#: string extraction, Cypher procedure namespaces, and names of map keys the queries
#: construct themselves.
KNOWN_NON_GRAPH_NAMES: Final[frozenset[str]] = frozenset(
    {
        # Python / driver surface that can appear inside a docstring example.
        "run",
        "run_one",
        "run_named",
        "cypher",
        "parameters",
        "value",
        "values",
        "items",
        "keys",
        "get",
        "append",
        "format",
        "join",
        "index",
        "fulltext",
        "queryNodes",
        "propertyKeys",
        "labels",
        "py",
        "api",
        "v1",
        "models",
        "services",
        "routes",
        "common",
        "entity",
        "queries",
        "ontology",
        "domain",
    }
)


def _docstring_nodes(tree: ast.Module) -> set[int]:
    """The ``id()`` of every docstring constant, so prose is not tested as query text.

    Docstrings in this codebase quote Cypher freely -- this module's own does -- so they
    would otherwise be scanned for property names and write clauses.
    """
    ids: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        body = getattr(node, "body", [])
        if not body:
            continue
        first = body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
            if isinstance(first.value.value, str):
                ids.add(id(first.value))
    return ids


def _cypher_blocks() -> list[tuple[Path, str]]:
    """Every Cypher string in the API package, whatever quoting style built it.

    Extracted from the AST rather than by matching ``\"\"\"...\"\"\"``. The regex version
    scanned 88 triple-quoted blocks and missed **68** statements assembled from ordinary
    single-line strings -- including all three of ``app.py``'s readiness queries and the
    deity population gate itself. Both tests below therefore certified the API's Cypher
    against roughly half of it, which is the fourth time this project has audited the wrong
    surface. The AST sees implicit concatenation already folded, and f-string literal parts
    as their own constants, so nothing hides behind a quoting choice.
    """
    blocks: list[tuple[Path, str]] = []
    for path in sorted(API_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        skip = _docstring_nodes(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            if id(node) in skip:
                continue
            if _CYPHER_CLAUSE.search(node.value):
                blocks.append((path, node.value))
    return blocks


def test_cypher_extraction_covers_the_whole_package() -> None:
    """Guards the guard twice over: it must find Cypher, and find it in every service.

    The count assertion is a floor, not a pin -- but a module that stops contributing any
    Cypher at all almost certainly means the extractor broke rather than that the module
    stopped querying, and that is the failure this catches.
    """
    blocks = _cypher_blocks()
    assert len(blocks) >= 100, f"expected the API's Cypher, extracted {len(blocks)} strings"
    contributors = {path.name for path, _ in blocks}
    for expected in (
        "app.py",
        "entity_service.py",
        "passage_service.py",
        "search_service.py",
        "graph_service.py",
        "insight_service.py",
    ):
        assert expected in contributors, f"no Cypher extracted from {expected}"


@pytest.mark.neo4j
def test_every_referenced_property_exists_in_the_graph(
    live_repository: Neo4jRepository,
) -> None:
    rows = live_repository.run("CALL db.propertyKeys() YIELD propertyKey RETURN propertyKey")
    live_keys = {str(row["propertyKey"]) for row in rows}
    assert len(live_keys) > 100, f"only {len(live_keys)} property keys; the probe is wrong"

    unknown: dict[str, set[str]] = {}
    for path, block in _cypher_blocks():
        for alias, prop in _PROPERTY_REFERENCE.findall(block):
            if alias in MAP_ALIASES:
                continue
            if prop in live_keys or prop in KNOWN_NON_GRAPH_NAMES:
                continue
            unknown.setdefault(prop, set()).add(f"{path.name}:{alias}.{prop}")

    assert not unknown, (
        "Cypher reads properties that do not exist in the graph; each returns null forever "
        "and renders as a blank field: "
        + "; ".join(
            f"{prop} (in {', '.join(sorted(files))})" for prop, files in sorted(unknown.items())
        )
    )


#: Cypher comments: ``//`` to end of line, and ``/* ... */``. Stripped before the
#: write-clause scan, because prose explaining a query is not part of the query.
_CYPHER_COMMENT: Final = re.compile(r"//[^\n]*|/\*.*?\*/", re.DOTALL)

#: The clauses that would mutate the frozen graph. Case-insensitive on purpose.
_WRITE_CLAUSE: Final = re.compile(
    r"\b(CREATE|MERGE|DELETE|DETACH|SET|REMOVE|DROP|FOREACH)\b", re.IGNORECASE
)


def strip_cypher_comments(block: str) -> str:
    return _CYPHER_COMMENT.sub(" ", block)


def test_the_write_guard_still_catches_a_lowercase_write() -> None:
    """Guards the guard: stripping comments must not have disarmed the scan.

    A comment reading "the SAME predicate set and the SAME count" tripped ``\\bset\\b`` and
    failed the write test on a query that writes nothing. The tempting fix -- match only
    uppercase, since this codebase spells clauses that way -- would let a real lowercase
    ``set n.x = 1`` straight through, because Cypher keywords are case-insensitive. So the
    fix is to stop reading the prose, not to stop reading half the alphabet.
    """
    assert _WRITE_CLAUSE.search(strip_cypher_comments("MATCH (n) set n.x = 1"))
    assert _WRITE_CLAUSE.search(strip_cypher_comments("MATCH (n) DETACH DELETE n"))
    assert not _WRITE_CLAUSE.search(strip_cypher_comments("// the SAME predicate set\nMATCH (n)"))
    assert not _WRITE_CLAUSE.search(strip_cypher_comments("/* set this aside */ MATCH (n)"))


def test_no_api_cypher_writes_to_the_graph() -> None:
    """The API is read-only, asserted against its own query text.

    The graph is frozen for Product V1. A write reaching it from an HTTP handler would be
    the single worst defect this build could ship, and it would not announce itself: a
    successful ``SET`` returns 200.
    """
    write_clause = _WRITE_CLAUSE
    offenders: list[str] = []
    for path, block in _cypher_blocks():
        match = write_clause.search(strip_cypher_comments(block))
        if match:
            offenders.append(f"{path.name}: {match.group(1)}")
    assert not offenders, f"write clauses in API Cypher: {offenders}"
