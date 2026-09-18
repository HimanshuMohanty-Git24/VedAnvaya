"""Contract tests for the three V3 layers: formula families, ritual structure, V2/V3 merge.

Almost all of this runs offline, for the same reason the rest of the domain suite does: the
things worth pinning here are decidable from the artifacts, the queries and the merge
functions, and a test that needed Neo4j running would be skipped exactly when it was most
needed.

Mark-and-sweep is the exception, because retraction cannot be observed without writes. It is
tested against :class:`FakeGraph`, an in-memory store that executes the small Cypher dialect
these two loaders emit, rather than against the shared database. Nothing in this file writes
to the live graph; the ``live`` tests are read-only counts and endpoint checks.

Three of the tests in this file FAIL, and are left failing on purpose. Each is named for the
behaviour it expects and each explains the defect in its own docstring:

* ``test_the_family_loader_persists_the_evidence_count_it_computes``
* ``test_no_containment_membership_rests_only_on_a_similarity_candidate``
* ``test_merge_concern_lists_preserves_the_recorded_promotion``

The ``live`` tests are marked ``live`` and additionally gated on ``VEDAGRAPH_LIVE_NEO4J``,
because ``pyproject.toml`` does not deselect ``live`` by default and this file must not turn
a green suite red on a machine with no Neo4j.
"""

from __future__ import annotations

import functools
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import re
import sys
import warnings
from collections.abc import Iterator, Sequence
from typing import Any, cast

import pytest
import yaml

from vedagraph.domain import v3_loader
from vedagraph.domain.loader import _RITUAL_EDGES, LoadReport, load_rituals
from vedagraph.domain.ontology import (
    LABEL_ACTION,
    LABEL_DEVATA,
    LABEL_FORMULA,
    LABEL_FORMULA_FAMILY,
    LABEL_PASSAGE,
    LABEL_RITUAL,
    REL_DESCRIBED_IN,
    REL_HAS_STEP,
    REL_MEMBER_OF_FAMILY,
    RELATIONSHIP_SIGNATURES,
    labels_for_node_type,
)
from vedagraph.domain.registry import load_domain_entities
from vedagraph.domain.taxonomy import registry_keys
from vedagraph.domain.v3_loader import _property_safe, load_formula_families
from vedagraph.enrich.corpus import load_corpus

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
DOMAIN_DIR = PROJECT_ROOT / "data" / "domain" / "vedagraph_domain_v2"
ENRICHMENT_DIR = PROJECT_ROOT / "data" / "enrichment" / "vedagraph_enrichment_v1"

_LIVE = pytest.mark.skipif(
    not os.environ.get("VEDAGRAPH_LIVE_NEO4J"),
    reason="set VEDAGRAPH_LIVE_NEO4J=1 to run against the local Neo4j instance",
)


# ---------------------------------------------------------------------------
# Loading a build script without letting it reconfigure the interpreter
# ---------------------------------------------------------------------------


@functools.cache
def _script(name: str) -> Any:
    """Import a ``scripts/`` module by path, with its import-time side effects contained.

    ``scripts/`` is not a package, so the module is loaded by path the way
    ``tests/unit/test_semantic_claude_opus5_v3_2.py`` loads its coordinator. Two extra
    precautions are needed here, both because these build scripts configure the
    *interpreter* at import time rather than in ``main()``:

    ``sys.stdout`` is rebound to a UTF-8 ``TextIOWrapper`` over ``sys.stdout.buffer``. Under
    pytest's capture that either fails outright or detaches the stream the capture plugin is
    holding, so a throwaway stdout is installed for the duration of the import and the real
    one put back.

    ``warnings.filterwarnings("ignore")`` mutates a global, so the import runs inside
    ``catch_warnings`` -- otherwise importing this module would silence warnings for every
    test that ran after it in the same session.
    """
    path = PROJECT_ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"_vedagraph_script_{name}", path)
    assert spec is not None and spec.loader is not None, path
    module = importlib.util.module_from_spec(spec)
    saved_stdout = sys.stdout
    sys.stdout = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    try:
        with warnings.catch_warnings():
            spec.loader.exec_module(module)
    finally:
        sys.stdout = saved_stdout
    return module


# ---------------------------------------------------------------------------
# A session double that actually stores what it is told
# ---------------------------------------------------------------------------

_MERGE_NODE_RE = re.compile(r"MERGE \((\w+):(\w+) \{(\w+): row\.(\w+)\}\)")
_MATCH_NODE_RE = re.compile(r"MATCH \((\w+):(\w+) \{(\w+): row\.(\w+)\}\)")
_MERGE_EDGE_RE = re.compile(r"MERGE \((\w+)\)-\[(\w+):(\w+)\]->\((\w+)\)")
_SET_RE = re.compile(r"(\w+)\.(\w+) = (?:row\.(\w+)|\$(\w+)|'([^']*)')")
#: A ``CASE`` assignment whose branches all yield a plain string literal.
#:
#: Generalised from a fixed two-branch pattern once the loader grew a third branch. The
#: earlier regex matched exactly ``CASE WHEN row.x CONTAINS 'y' THEN 'a' ELSE 'b' END``,
#: so adding a ``WHEN NOT row.z`` branch made the whole assignment silently unmatched --
#: the property stopped being written and every tier assertion started reading ``None``.
#: A double that fails *closed* like that is worse than one that refuses loudly, so the
#: branch scanner below is order-preserving and anything it cannot parse falls through to
#: :meth:`FakeGraph.unevaluable`.
_CASE_BLOCK_RE = re.compile(r"(\w+)\.(\w+) = CASE\s+(.*?)\s+END", re.DOTALL)

#: One branch, in source order. ``CONTAINS`` and ``NOT`` are the two predicates the
#: loaders use; ``ELSE`` closes the chain.
_BRANCH_RE = re.compile(
    r"WHEN\s+row\.(?P<contains_field>\w+)\s+CONTAINS\s+'(?P<needle>[^']*)'\s+THEN\s+'(?P<hit>[^']*)'"
    r"|WHEN\s+NOT\s+row\.(?P<not_field>\w+)\s+THEN\s+'(?P<not_hit>[^']*)'"
    r"|ELSE\s+'(?P<fallback>[^']*)'"
)


def _evaluate_case(body: str, row: dict[str, Any]) -> str | None:
    """Resolve a literal-valued ``CASE`` against one row, first matching branch wins."""
    for branch in _BRANCH_RE.finditer(body):
        if branch.group("contains_field"):
            haystack = str(row.get(branch.group("contains_field"), ""))
            if branch.group("needle") in haystack:
                return branch.group("hit")
        elif branch.group("not_field"):
            if not row.get(branch.group("not_field")):
                return branch.group("not_hit")
        elif branch.group("fallback") is not None:
            return branch.group("fallback")
    return None


def _literal_case_assignments(text: str) -> list[tuple[str, str, str]]:
    """``(alias, property, case body)`` for every CASE this double can evaluate.

    A branch yielding a concatenation rather than a bare literal (``'a' + 'b'``) makes the
    whole block unevaluable, which is how ``grade_basis`` is excluded.
    """
    out: list[tuple[str, str, str]] = []
    for alias, prop, body in _CASE_BLOCK_RE.findall(text):
        if not _BRANCH_RE.search(body):
            continue
        # A `+` anywhere in the body means at least one branch builds its value by
        # concatenation rather than yielding a bare literal, and this double does not
        # evaluate expressions. Disqualifying the whole block is deliberate: evaluating
        # the literal branches and skipping the concatenated one would write a value that
        # is right for some rows and absent for others, which is the least debuggable
        # outcome available. `grade_basis` is excluded by exactly this rule.
        if "+" in body:
            continue
        out.append((alias, prop, body))
    return out


_ASSIGN_RE = re.compile(r"(\w+)\.(\w+) = ")
_PATH_RE = re.compile(r"MATCH \((\w*):?(\w*)\)-\[(\w+):(\w+)\]->\((\w*):?(\w*)\)")
_AGG_RE = re.compile(r"RETURN (\w+)\.(\w+) AS (\w+), count\(\*\) AS n")
_NODE_RE = re.compile(r"^MATCH \((\w+):(\w+)\)")


class _Result:
    """The two shapes the loaders consume: ``.single()["c"]`` and record iteration."""

    def __init__(self, rows: Sequence[dict[str, Any]]) -> None:
        self._rows = list(rows)

    def single(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None

    def __iter__(self) -> Iterator[dict[str, Any]]:
        return iter(self._rows)


class FakeGraph:
    """An in-memory store that executes the Cypher dialect these two loaders emit.

    Enough of Cypher to make *retraction* observable, which is the one property of these
    loaders that a recording fake cannot show: labelled node MERGE on a single property,
    labelled edge MERGE between two separately matched endpoints, ``SET``/``ON CREATE SET``
    from row fields and query parameters, counting under a ``build_pass`` predicate, and both
    sweep forms.

    Three rules make it trustworthy rather than merely convenient. An unrecognised query
    *raises*, so a loader that changed shape fails loudly here instead of having its query
    silently ignored and its assertions pass anyway. ``SET x.p = row.missing`` removes the
    property rather than storing ``None``, which is what Neo4j does with a null -- so a
    property the query never mentions is absent from the store exactly as it is absent from
    the database. And the one class of right-hand side it cannot evaluate -- an expression
    computed inside the query -- is enumerable through :meth:`unevaluable`, which one test
    pins so that a newly computed property cannot quietly fall out of the offline coverage.
    """

    def __init__(self) -> None:
        self.nodes: list[dict[str, Any]] = []
        self.edges: list[dict[str, Any]] = []
        self.queries: list[str] = []

    # -- seeding and inspection ------------------------------------------------

    def add_node(self, *labels: str, **props: Any) -> dict[str, Any]:
        node: dict[str, Any] = {"labels": set(labels), "props": dict(props)}
        self.nodes.append(node)
        return node

    def node(self, label: str, prop: str, value: Any) -> dict[str, Any]:
        found = self._find_node(label, prop, value)
        assert found is not None, f"no :{label} with {prop}={value!r}"
        return found

    def edge_props(self, rel_type: str) -> list[dict[str, Any]]:
        return [dict(e["props"]) for e in self.edges if e["type"] == rel_type]

    def edge_pairs(self, rel_type: str, start_prop: str, end_prop: str) -> set[tuple[Any, Any]]:
        return {
            (e["start"]["props"].get(start_prop), e["end"]["props"].get(end_prop))
            for e in self.edges
            if e["type"] == rel_type
        }

    def node_props(self, label: str) -> list[dict[str, Any]]:
        return [dict(n["props"]) for n in self.nodes if label in n["labels"]]

    @staticmethod
    def unevaluable(query: str) -> set[str]:
        """Property names the query assigns from an expression this store cannot compute."""
        text = " ".join(query.split())
        assigned = {prop for _alias, prop in _ASSIGN_RE.findall(text)}
        known = {prop for _a, prop, *_rest in _SET_RE.findall(text)}
        known |= {prop for _a, prop, _body in _literal_case_assignments(text)}
        return assigned - known

    # -- execution -------------------------------------------------------------

    def run(self, query: str, **params: Any) -> _Result:
        text = " ".join(query.split())
        self.queries.append(text)
        if text.startswith("UNWIND $rows AS row"):
            return self._write(text, params)
        return self._read(text, params)

    def _find_node(self, label: str, prop: str, value: Any) -> dict[str, Any] | None:
        for node in self.nodes:
            if label in node["labels"] and node["props"].get(prop) == value:
                return node
        return None

    def _write(self, text: str, params: dict[str, Any]) -> _Result:
        node_merge = _MERGE_NODE_RE.search(text)
        edge_merge = _MERGE_EDGE_RE.search(text)
        if node_merge is None and edge_merge is None:
            raise AssertionError(f"FakeGraph cannot execute: {text}")
        matches = _MATCH_NODE_RE.findall(text)
        assignments = _SET_RE.findall(text)
        cases = _literal_case_assignments(text)
        for row in params.get("rows", []):
            bound: dict[str, dict[str, Any]] = {}
            for alias, label, prop, field in matches:
                found = self._find_node(label, prop, row.get(field))
                if found is None:
                    break
                bound[alias] = found
            else:
                if node_merge is not None:
                    alias, label, prop, field = node_merge.groups()
                    value = row.get(field)
                    bound[alias] = self._find_node(label, prop, value) or self.add_node(
                        label, **{prop: value}
                    )
                if edge_merge is not None:
                    subject, rel_alias, rel_type, obj = edge_merge.groups()
                    bound[rel_alias] = self._merge_edge(rel_type, bound[subject], bound[obj])
                for alias, prop, field, param, literal in assignments:
                    entity = bound.get(alias)
                    if entity is None:
                        continue
                    if field:
                        value = row.get(field)
                    elif param:
                        value = params.get(param)
                    else:
                        value = literal
                    if value is None:
                        entity["props"].pop(prop, None)
                    else:
                        entity["props"][prop] = value
                for alias, prop, body in cases:
                    entity = bound.get(alias)
                    if entity is None:
                        continue
                    resolved = _evaluate_case(body, row)
                    if resolved is not None:
                        entity["props"][prop] = resolved
        return _Result([])

    def _merge_edge(
        self, rel_type: str, start: dict[str, Any], end: dict[str, Any]
    ) -> dict[str, Any]:
        for edge in self.edges:
            if edge["type"] == rel_type and edge["start"] is start and edge["end"] is end:
                return edge
        edge = {"type": rel_type, "start": start, "end": end, "props": {}}
        self.edges.append(edge)
        return edge

    def _read(self, text: str, params: dict[str, Any]) -> _Result:
        path = _PATH_RE.search(text)
        if path is not None:
            _s_alias, s_label, rel_alias, rel_type, _o_alias, o_label = path.groups()
            edges = [
                edge
                for edge in self.edges
                if edge["type"] == rel_type
                and (not s_label or s_label in edge["start"]["labels"])
                and (not o_label or o_label in edge["end"]["labels"])
            ]
            aggregate = _AGG_RE.search(text)
            if aggregate is not None:
                _agg_alias, prop, name = aggregate.groups()
                counts: dict[Any, int] = {}
                for edge in edges:
                    key = edge["props"].get(prop)
                    counts[key] = counts.get(key, 0) + 1
                ordered = sorted(counts.items(), key=lambda item: (-item[1], str(item[0])))
                return _Result([{name: key, "n": n} for key, n in ordered])
            selected = [e for e in edges if self._predicate(text, rel_alias, e, params)]
            if " DELETE " in text:
                for edge in selected:
                    self.edges.remove(edge)
            return _Result([{"c": len(selected)}])

        node = _NODE_RE.match(text)
        if node is None:
            raise AssertionError(f"FakeGraph cannot execute: {text}")
        alias, label = node.groups()
        candidates = [n for n in self.nodes if label in n["labels"]]
        dangling = re.search(rf"WHERE NOT \({alias}\)-\[:(\w+)\]->\(\)", text)
        if dangling is not None:
            starts = {id(e["start"]) for e in self.edges if e["type"] == dangling.group(1)}
            selected = [n for n in candidates if id(n) not in starts]
        else:
            selected = [n for n in candidates if self._predicate(text, alias, n, params)]
        if "DETACH DELETE" in text:
            for target in selected:
                self.nodes.remove(target)
                self.edges = [
                    e for e in self.edges if e["start"] is not target and e["end"] is not target
                ]
        return _Result([{"c": len(selected)}])

    @staticmethod
    def _predicate(text: str, alias: str, entity: dict[str, Any], params: dict[str, Any]) -> bool:
        stale = re.search(rf"WHERE {alias}\.(\w+) IS NULL OR {alias}\.\w+ <> \$(\w+)", text)
        if stale is not None:
            prop, param = stale.groups()
            return bool(entity["props"].get(prop) != params.get(param))
        equal = re.search(rf"WHERE {alias}\.(\w+) = \$(\w+)", text)
        if equal is not None:
            prop, param = equal.groups()
            return bool(entity["props"].get(prop) == params.get(param))
        truthy = re.search(rf"WHERE {alias}\.(\w+) RETURN", text)
        if truthy is not None:
            return bool(entity["props"].get(truthy.group(1)))
        if " WHERE " in text:
            raise AssertionError(f"FakeGraph cannot evaluate the predicate in: {text}")
        return True


class _PositionalSession:
    """``FakeGraph`` behind ``vedagraph.domain.loader``'s protocol.

    The two loaders declare their session protocol differently, and the difference is not
    satisfiable by one signature. ``loader.Session`` is ``run(query: str, /, **kwargs)``,
    which admits a caller passing ``query`` *again* inside ``**kwargs``; ``v3_loader.Session``
    is ``run(query: str, **parameters)``, which admits a caller passing it by name. An
    implementation can accept one or the other, not both, so ``FakeGraph`` matches the second
    and this adapter supplies the first rather than casting the difference away.
    """

    def __init__(self, graph: FakeGraph) -> None:
        self._graph = graph

    def run(self, query: str, /, **kwargs: Any) -> _Result:
        return self._graph.run(query, **kwargs)


def _load_rituals(graph: FakeGraph, rituals: Sequence[dict[str, Any]]) -> LoadReport:
    return load_rituals(_PositionalSession(graph), rituals)


def test_the_fake_graph_refuses_a_query_it_cannot_execute() -> None:
    """The fake's own safety property, checked, because every other test rests on it.

    A double that silently ignored an unrecognised query would make every assertion below
    vacuous the moment a loader changed shape.
    """
    graph = FakeGraph()
    graph.add_node(LABEL_FORMULA, formula_id="VG:ENRICH:FORMULA:f001", word_count=4)
    with pytest.raises(AssertionError, match="cannot execute"):
        graph.run("MATCH (n) DETACH DELETE n")
    with pytest.raises(AssertionError, match="cannot execute"):
        graph.run("UNWIND $rows AS row CREATE (f:Formula {formula_id: row.formula_id})", rows=[])
    with pytest.raises(AssertionError, match="cannot evaluate the predicate"):
        graph.run("MATCH (f:Formula) WHERE f.word_count > 3 RETURN count(f) AS c")


# ---------------------------------------------------------------------------
# _property_safe: the two fields Neo4j cannot hold
# ---------------------------------------------------------------------------

_SPAN = {"locator": "VG:RV:SAK:M01:S001:V001", "quote": "agnim ile", "surface": "SCRIPT_FOLDED"}


def test_property_safe_json_encodes_the_veda_counts_map() -> None:
    out = _property_safe({"veda_counts": {"RV": 4, "SV": 3}})
    assert isinstance(out["veda_counts"], str)
    assert json.loads(out["veda_counts"]) == {"RV": 4, "SV": 3}


def test_property_safe_json_encodes_evidence_and_counts_the_spans() -> None:
    """The count is the point: it keeps "how many spans?" a numeric comparison."""
    out = _property_safe({"evidence": [_SPAN, dict(_SPAN, locator="VG:SV:KAU:P01:R01:D01:V01")]})
    assert isinstance(out["evidence"], str)
    assert json.loads(out["evidence"])[1]["locator"] == "VG:SV:KAU:P01:R01:D01:V01"
    assert out["evidence_count"] == 2


def test_property_safe_leaves_vedas_a_native_list() -> None:
    """``'SV' IN fam.vedas`` is a query somebody will write; a JSON string breaks it."""
    out = _property_safe({"vedas": ["RV", "SV", "AV"]})
    assert out["vedas"] == ["RV", "SV", "AV"]


def test_property_safe_is_idempotent() -> None:
    once = _property_safe({"veda_counts": {"RV": 1}, "evidence": [_SPAN], "vedas": ["RV"]})
    assert _property_safe(once) == once


def test_property_safe_tolerates_already_encoded_fields() -> None:
    """A row read back from an artifact that stored strings must not be double-encoded."""
    encoded = {"veda_counts": '{"RV": 1}', "evidence": "[]", "evidence_count": 7}
    out = _property_safe(encoded)
    assert out["veda_counts"] == '{"RV": 1}'
    assert out["evidence"] == "[]"
    assert out["evidence_count"] == 7, "an existing count must not be overwritten with 0"


def test_property_safe_defaults_the_count_when_evidence_is_absent() -> None:
    out = _property_safe({"family_id": "VG:ENRICH:FORMULA-FAMILY:x"})
    assert out["evidence_count"] == 0
    assert "evidence" not in out and "veda_counts" not in out


def test_property_safe_does_not_mutate_its_input() -> None:
    row: dict[str, Any] = {"veda_counts": {"RV": 1}, "evidence": [_SPAN]}
    _property_safe(row)
    assert row == {"veda_counts": {"RV": 1}, "evidence": [_SPAN]}


def test_property_safe_output_is_storable_for_every_real_family_row() -> None:
    """Run over the whole artifact, because one unflattened map fails the whole write."""
    rows = _read_jsonl(ENRICHMENT_DIR / "formula_families.jsonl")
    assert rows, "the formula family artifact should be present"
    for row in rows:
        for key, value in _property_safe(row).items():
            assert isinstance(value, str | int | float | bool | list), (row["family_id"], key)
            if isinstance(value, list):
                assert all(isinstance(item, str | int | float | bool) for item in value), key


# ---------------------------------------------------------------------------
# The formula family artifact and its containment claim
# ---------------------------------------------------------------------------


def _read_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


@functools.cache
def _families() -> tuple[dict[str, Any], ...]:
    return tuple(_read_jsonl(ENRICHMENT_DIR / "formula_families.jsonl"))


@functools.cache
def _members() -> tuple[dict[str, Any], ...]:
    return tuple(_read_jsonl(ENRICHMENT_DIR / "formula_family_members.jsonl"))


def _members_by_family() -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for member in _members():
        grouped.setdefault(str(member["family_id"]), []).append(member)
    return grouped


def _identity(normalized: str) -> str:
    """The collapsed identity surface -- ``normalized`` with its word breaks removed.

    Deliberately re-derived here rather than imported from
    ``vedagraph.enrich.formula_families._identity``: the claim under test is that membership
    is recomputable *by a reader*, and importing the producer's own function would test that
    the producer agrees with itself.
    """
    return "".join(normalized.split())


def _related(left: str, right: str) -> bool:
    """Direct containment either way, on the collapsed surface."""
    return bool(left) and bool(right) and (left in right or right in left)


def test_member_of_family_declares_formula_to_formula_family() -> None:
    subjects, objects = RELATIONSHIP_SIGNATURES[REL_MEMBER_OF_FAMILY]
    assert subjects == frozenset({LABEL_FORMULA})
    assert objects == frozenset({LABEL_FORMULA_FAMILY})


def test_the_membership_query_matches_exactly_the_labels_its_signature_names() -> None:
    """A loader that matched a broader label than the signature could land an illegal edge.

    Read off the query rather than off the graph, so it holds before anything is loaded.
    """
    query = v3_loader._FAMILY_MEMBER_QUERY
    matched = {label: alias for alias, label, _prop, _field in _MATCH_NODE_RE.findall(query)}
    merge = _MERGE_EDGE_RE.search(query)
    assert merge is not None
    subject_alias, _rel_alias, rel_type, object_alias = merge.groups()
    subjects, objects = RELATIONSHIP_SIGNATURES[rel_type]
    assert {matched[label] for label in subjects} == {subject_alias}
    assert {matched[label] for label in objects} == {object_alias}
    assert set(matched) == subjects | objects, "the query matched a label outside the signature"


def test_family_ids_are_unique_in_the_artifact() -> None:
    """There is a uniqueness constraint on ``family_id``; a duplicate row would break it."""
    ids = [str(row["family_id"]) for row in _families()]
    assert ids and len(ids) == len(set(ids))


def test_every_membership_names_a_family_the_artifact_declares() -> None:
    declared = {str(row["family_id"]) for row in _families()}
    orphans = {m["family_id"] for m in _members() if str(m["family_id"]) not in declared}
    assert not orphans


def test_membership_ids_are_unique_and_one_formula_joins_one_family() -> None:
    """MEMBER_OF_FAMILY is a partition, not a tagging: two families for one formula would
    make ``formulas_unfamilied`` and ``member_count`` disagree about the same formula."""
    assert len({m["membership_id"] for m in _members()}) == len(_members())
    formula_ids = [m["formula_id"] for m in _members()]
    assert len(formula_ids) == len(set(formula_ids))


def test_every_family_counts_its_own_members_correctly() -> None:
    """The published per-role counts are what a reader filters on, so they must be the rows.

    Checked per family rather than in total, because two families with compensating errors
    would sum correctly.
    """
    grouped = _members_by_family()
    for family in _families():
        rows = grouped.get(str(family["family_id"]), [])
        roles = [str(row["role"]) for row in rows]
        assert family["member_count"] == len(rows), family["family_id"]
        assert family["core_count"] == roles.count("CORE"), family["family_id"]
        assert family["expansion_count"] == roles.count("EXPANSION"), family["family_id"]
        assert family["variant_count"] == roles.count("VARIANT"), family["family_id"]
        assert family["secondary_core_count"] == max(roles.count("CORE") - 1, 0)


def test_member_roles_are_drawn_from_the_closed_vocabulary() -> None:
    assert {str(m["role"]) for m in _members()} == {"CORE", "EXPANSION", "VARIANT"}


def test_every_expansion_strictly_contains_the_member_it_is_linked_to() -> None:
    """The TIER_B claim, in the exact form the loader's ``grade_basis`` states it.

    ``MEMBER_OF_FAMILY`` says ``containment of one stored formula string in another,
    recomputable``, and ``linked_formula_id`` names the *other* string. So this is the whole
    claim, recomputed from the two artifacts on the collapsed surface, for all 1,119
    expansions rather than a sample.
    """
    by_id = {str(m["formula_id"]): m for m in _members()}
    for member in _members():
        if member["role"] != "EXPANSION":
            continue
        parent = by_id[str(member["linked_formula_id"])]
        child, ancestor = _identity(member["normalized"]), _identity(parent["normalized"])
        assert parent["family_id"] == member["family_id"], member["membership_id"]
        assert ancestor in child and ancestor != child, (
            f"{member['formula_id']} is EXPANSION of {parent['formula_id']} "
            f"but {ancestor!r} is not strictly inside {child!r}"
        )


def test_every_member_has_a_sibling_it_directly_contains_or_is_contained_by() -> None:
    """The claim the layer's ``grade_basis`` now makes: a family is a connected component.

    Membership is transitive rather than pairwise -- a member need not contain the family's
    representative -- but the component has to be *connected by containment* for that to be
    decidable at all. A member with no containing or contained sibling would be in the family
    for some other reason, and the grade would be asserting a relation that is not there.
    """
    for rows in _members_by_family().values():
        for row in rows:
            mine = _identity(row["normalized"])
            siblings = [_identity(other["normalized"]) for other in rows if other is not row]
            assert any(_related(sibling, mine) for sibling in siblings), (
                f"{row['formula_id']} has no containment sibling in {row['family_id']}"
            )


def test_no_containment_membership_rests_only_on_a_similarity_candidate() -> None:
    """No TIER_B membership may be anchored solely to a TIER_D similarity candidate.

    The four similarity-derived ``VARIANT`` rows are graded ``TIER_D`` -- a chosen
    threshold is not a decidable relation -- and every containment-derived row would
    otherwise be ``TIER_B``. Those two grades are **not independent**, because a family is
    a connected component and the connection runs through its members.

    In family ``...db7b82d9...`` the member ``anu dyāvāpṛthivī``
    (``VG:ENRICH:FORMULA:a948c428...``, role ``EXPANSION``) has exactly one containment
    sibling in the whole family: the ``VARIANT`` ``nu dyāvāpṛthivī``. Its collapsed form
    contains no other member -- not the core ``dyāvāpṛthivī ā``, not any expansion.
    Withdraw the candidate and it is in no containment component at all, so grading it
    TIER_B would rest it on the very threshold the loader declares insufficient for TIER_B.

    **The invariant, not a proxy for it.** An earlier version of this test flagged rows by
    their ``method`` string, which meant it kept failing after the defect was fixed: the
    loader's resolution is to grade the row ``TIER_D`` via ``has_containment_support``, and
    the row's *method* is still containment-derived because that is how it was derived. So
    this asserts what actually matters -- that such a row does not end up ``TIER_B`` -- and
    it would still fail if the support flag were removed or wired to the wrong branch.
    """
    annotated = v3_loader._annotate_containment(list(_members()), list(_families()))
    by_id = {(r["family_id"], r["formula_id"]): r for r in annotated}

    exposed: list[str] = []
    for rows in _members_by_family().values():
        for row in rows:
            if "similarity" in str(row["method"]):
                continue
            mine = _identity(row["normalized"])
            siblings = [
                other
                for other in rows
                if other is not row and _related(_identity(other["normalized"]), mine)
            ]
            if siblings and all("similarity" in str(s["method"]) for s in siblings):
                # Anchored only to a candidate. Permitted -- the relationship is real --
                # but only if the loader refuses to call it TIER_B.
                resolved = by_id[(row["family_id"], row["formula_id"])]
                if resolved["has_containment_support"]:
                    exposed.append(f"{row['formula_id']} in {row['family_id']}")

    assert not exposed, (
        f"{len(exposed)} member(s) anchored only to a similarity candidate are still "
        f"marked as having containment support, so the loader will grade them TIER_B: "
        f"{exposed}"
    )


def test_a_member_anchored_only_to_a_candidate_actually_exists() -> None:
    """Guards the test above against passing because its premise evaporated.

    The invariant is only meaningful while at least one such row exists in the artifact. If
    the derivation changes so that none does, this fails and says so, rather than letting
    the sibling test go quietly vacuous.
    """
    annotated = v3_loader._annotate_containment(list(_members()), list(_families()))
    unsupported = [r for r in annotated if not r["has_containment_support"]]
    assert unsupported, (
        "no member lacks containment support, so the TIER_B/TIER_D anchoring invariant "
        "is no longer being exercised by real data"
    )


def test_contains_representative_is_measured_against_the_representative() -> None:
    """The per-row flag exists so the stronger subset stays filterable, so it must be that.

    Two populations are easy to confuse and the loader annotates one of them: the members
    that stand in no direct containment relation to the family's *representative*, and the
    members that stand in none to the formula they *cite* in ``linked_formula_id``. They are
    different sets and different sizes, so the flag is pinned to the first and the second is
    computed alongside to prove they are not interchangeable.
    """
    annotated = v3_loader._annotate_containment(list(_members()), list(_families()))
    representative = {
        str(family["family_id"]): _identity(str(family["representative_normalized"]))
        for family in _families()
    }
    by_id = {str(m["formula_id"]): m for m in _members()}
    not_representative = {
        str(row["formula_id"])
        for row in _members()
        if not _related(_identity(row["normalized"]), representative[str(row["family_id"])])
    }
    not_cited = {
        str(row["formula_id"])
        for row in _members()
        if not _related(
            _identity(row["normalized"]),
            _identity(by_id[str(row["linked_formula_id"])]["normalized"]),
        )
    }
    flagged = {str(r["formula_id"]) for r in annotated if not r["contains_representative"]}
    assert flagged == not_representative
    assert not_representative != not_cited, "the two populations must not be conflated"
    for row in annotated:
        assert row["containment_is_transitive"] is not row["contains_representative"]


def test_a_similarity_derived_membership_is_graded_below_a_containment_one(
    formula_graph: FakeGraph,
) -> None:
    """The tier split is decided inside the query, so it is worth landing and reading back.

    Both rows come back ``TIER_D`` and that is the point of the fixture. The ``VARIANT`` is
    ``TIER_D`` because similarity above a threshold is a candidate. The ``CORE`` is
    ``TIER_D`` because in a two-member family whose only other member is that candidate,
    the ``CORE``'s membership has no containment-derived support either -- withdraw the
    candidate and there is no family. Grading it ``TIER_B`` would let a TIER_B row rest on
    a TIER_D one, which is the transitive-trust leak
    ``test_no_containment_membership_rests_only_on_a_similarity_candidate`` exists to
    forbid. For the contrasting case, where containment support is real, see
    ``test_a_containment_membership_with_real_support_stays_tier_b``.
    """
    load_formula_families(
        formula_graph,
        [_family_row(_FAM_A, "VG:ENRICH:FORMULA:f001")],
        [
            _member_row(_FAM_A, "VG:ENRICH:FORMULA:f001"),
            _member_row(
                _FAM_A,
                "VG:ENRICH:FORMULA:f002",
                role="VARIANT",
                method="formula-family-variant-by-similarity-v1",
                similarity=0.79,
            ),
        ],
    )
    tiers = {
        props["role"]: props["quality_tier"]
        for props in formula_graph.edge_props(REL_MEMBER_OF_FAMILY)
    }
    assert tiers == {"CORE": "TIER_D", "VARIANT": "TIER_D"}


def test_a_containment_membership_with_real_support_stays_tier_b(
    formula_graph: FakeGraph,
) -> None:
    """The other half of the tier rule: genuine containment support earns TIER_B.

    Without this, the fixture above could be satisfied by a loader that graded every
    membership ``TIER_D``, which would pass the leak test and destroy the layer.
    """
    load_formula_families(
        formula_graph,
        [_family_row(_FAM_A, "VG:ENRICH:FORMULA:f001")],
        [
            _member_row(_FAM_A, "VG:ENRICH:FORMULA:f001"),
            _member_row(_FAM_A, "VG:ENRICH:FORMULA:f002", role="EXPANSION"),
        ],
    )
    tiers = {
        props["role"]: props["quality_tier"]
        for props in formula_graph.edge_props(REL_MEMBER_OF_FAMILY)
    }
    assert tiers == {"CORE": "TIER_B", "EXPANSION": "TIER_B"}


def test_the_fake_graph_names_the_properties_it_cannot_evaluate() -> None:
    """Pinned so a newly computed property cannot quietly fall out of offline coverage.

    ``grade_basis`` on the membership edge is a ``CASE`` whose branches concatenate two string
    literals, which this store does not evaluate; every other assignment in both queries comes
    from a row field, a parameter, a literal or the tier ``CASE``, and is therefore checked
    above. If this set grows, the property that grew it is untested offline.
    """
    assert FakeGraph.unevaluable(v3_loader._FAMILY_NODE_QUERY) == set()
    assert FakeGraph.unevaluable(v3_loader._FAMILY_MEMBER_QUERY) == {"grade_basis"}


# ---------------------------------------------------------------------------
# The formula family loader: landing, and retracting
# ---------------------------------------------------------------------------


def _family_row(family_id: str, representative: str, **overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "family_id": family_id,
        "representative_formula_id": representative,
        "representative_display_form": "agním īḷe",
        "representative_normalized": "agnim ile",
        "representative_coverage": 1.0,
        "member_count": 1,
        "core_count": 1,
        "secondary_core_count": 0,
        "expansion_count": 0,
        "variant_count": 0,
        "containment_depth": 1,
        "min_word_count": 2,
        "max_word_count": 2,
        "occurrence_count": 2,
        "mantra_count": 2,
        "vedas": ["RV", "SV"],
        "veda_counts": {"RV": 1, "SV": 1},
        "veda_span": 2,
        "cross_veda": True,
        "parallel_corroborated": True,
        "derivation_method": "collapsed-containment-components-v1",
        "evidence": [_SPAN],
        "notes": "",
        "trust": "DETERMINISTIC_DERIVED",
        "method": "collapsed-containment-components-v1",
        "score": 1.0,
        "state": "ACCEPTED",
        "pipeline_version": "vedagraph-graph-enrichment-v1",
        "run_id": "vedagraph-graph-enrichment-v1:test:0000",
    }
    row.update(overrides)
    return row


def _member_row(
    family_id: str, formula_id: str, role: str = "CORE", **overrides: Any
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "membership_id": f"VG:ENRICH:FORMULA-FAMILY-MEMBER:{family_id[-4:]}-{formula_id[-4:]}",
        "family_id": family_id,
        "formula_id": formula_id,
        "role": role,
        "normalized": "agnim ile",
        "display_form": "agním īḷe",
        "similarity": 1.0,
        "match_level": "SANDHI_INSENSITIVE",
        "linked_formula_id": formula_id,
        "word_count": 2,
        "mantra_count": 2,
        "evidence": [_SPAN],
        "trust": "DETERMINISTIC_DERIVED",
        "method": "formula-family-core-v1",
        "score": 1.0,
        "state": "ACCEPTED",
        "pipeline_version": "vedagraph-graph-enrichment-v1",
        "run_id": "vedagraph-graph-enrichment-v1:test:0000",
    }
    row.update(overrides)
    return row


_FAM_A = "VG:ENRICH:FORMULA-FAMILY:aaaa"
_FAM_B = "VG:ENRICH:FORMULA-FAMILY:bbbb"


@pytest.fixture
def formula_graph() -> FakeGraph:
    graph = FakeGraph()
    for suffix in ("f001", "f002", "f003"):
        graph.add_node(LABEL_FORMULA, formula_id=f"VG:ENRICH:FORMULA:{suffix}")
    return graph


def test_the_family_loader_lands_every_family_and_membership_it_is_sent(
    formula_graph: FakeGraph,
) -> None:
    report = load_formula_families(
        formula_graph,
        [_family_row(_FAM_A, "VG:ENRICH:FORMULA:f001")],
        [
            _member_row(_FAM_A, "VG:ENRICH:FORMULA:f001"),
            _member_row(_FAM_A, "VG:ENRICH:FORMULA:f002", role="EXPANSION"),
        ],
    )
    assert report.sent == 3
    assert report.landed == 3
    assert report.complete
    assert report.detail["family_nodes"] == {"sent": 1, "landed": 1}
    assert report.detail["member_edges"] == {"sent": 2, "landed": 2}
    assert report.detail["members_by_role"] == {"CORE": 1, "EXPANSION": 1}
    assert report.detail["members_by_tier"] == {"TIER_B": 2}
    assert report.detail["formulas_unfamilied"] == 1
    assert report.detail["cross_veda_families"] == 1
    assert report.detail["members_containing_representative"] == 2
    assert report.detail["members_transitive_only"] == 0


def test_a_family_absent_from_the_next_pass_is_deleted_not_left_behind(
    formula_graph: FakeGraph,
) -> None:
    """MERGE adds and never retracts, so without the sweep a rebuilt layer would be the
    union of every layer ever built."""
    load_formula_families(
        formula_graph,
        [
            _family_row(_FAM_A, "VG:ENRICH:FORMULA:f001"),
            _family_row(_FAM_B, "VG:ENRICH:FORMULA:f003"),
        ],
        [
            _member_row(_FAM_A, "VG:ENRICH:FORMULA:f001"),
            _member_row(_FAM_A, "VG:ENRICH:FORMULA:f002", role="EXPANSION"),
            _member_row(_FAM_B, "VG:ENRICH:FORMULA:f003"),
        ],
    )
    assert {p["family_id"] for p in formula_graph.node_props(LABEL_FORMULA_FAMILY)} == {
        _FAM_A,
        _FAM_B,
    }

    second = load_formula_families(
        formula_graph,
        [_family_row(_FAM_A, "VG:ENRICH:FORMULA:f001")],
        [_member_row(_FAM_A, "VG:ENRICH:FORMULA:f001")],
    )
    assert {p["family_id"] for p in formula_graph.node_props(LABEL_FORMULA_FAMILY)} == {_FAM_A}
    assert formula_graph.edge_pairs(REL_MEMBER_OF_FAMILY, "formula_id", "family_id") == {
        ("VG:ENRICH:FORMULA:f001", _FAM_A)
    }
    assert second.detail["retired_stale_nodes"] == 1
    assert second.detail["retired_stale_edges"] == 2
    assert second.complete


def test_a_membership_that_moves_family_leaves_no_edge_on_the_old_one(
    formula_graph: FakeGraph,
) -> None:
    """The case a family-level sweep alone would miss: both families survive the rebuild."""
    families = [
        _family_row(_FAM_A, "VG:ENRICH:FORMULA:f001"),
        _family_row(_FAM_B, "VG:ENRICH:FORMULA:f003"),
    ]
    load_formula_families(
        formula_graph,
        families,
        [
            _member_row(_FAM_A, "VG:ENRICH:FORMULA:f002", role="EXPANSION"),
            _member_row(_FAM_B, "VG:ENRICH:FORMULA:f003"),
        ],
    )
    load_formula_families(
        formula_graph,
        families,
        [
            _member_row(_FAM_B, "VG:ENRICH:FORMULA:f002", role="EXPANSION"),
            _member_row(_FAM_B, "VG:ENRICH:FORMULA:f003"),
        ],
    )
    assert formula_graph.edge_pairs(REL_MEMBER_OF_FAMILY, "formula_id", "family_id") == {
        ("VG:ENRICH:FORMULA:f002", _FAM_B),
        ("VG:ENRICH:FORMULA:f003", _FAM_B),
    }


def test_a_membership_whose_formula_is_missing_is_reported_not_invented(
    formula_graph: FakeGraph,
) -> None:
    """Rows-sent against rows-landed is the whole point of ``LoadReport``.

    The loader must not create a ``Formula`` node to hang the edge on, and must not report
    the row as landed.
    """
    report = load_formula_families(
        formula_graph,
        [_family_row(_FAM_A, "VG:ENRICH:FORMULA:f001")],
        [
            _member_row(_FAM_A, "VG:ENRICH:FORMULA:f001"),
            _member_row(_FAM_A, "VG:ENRICH:FORMULA:absent"),
        ],
    )
    assert report.sent == 3
    assert report.landed == 2
    assert not report.complete
    assert len(formula_graph.node_props(LABEL_FORMULA)) == 3


def test_an_empty_family_list_is_a_no_op_rather_than_a_full_sweep(
    formula_graph: FakeGraph,
) -> None:
    """A build that read no artifact must not be able to empty the layer."""
    load_formula_families(
        formula_graph,
        [_family_row(_FAM_A, "VG:ENRICH:FORMULA:f001")],
        [_member_row(_FAM_A, "VG:ENRICH:FORMULA:f001")],
    )
    report = load_formula_families(formula_graph, [], [])
    assert report.sent == 0
    assert formula_graph.node_props(LABEL_FORMULA_FAMILY)
    assert formula_graph.edge_props(REL_MEMBER_OF_FAMILY)


def test_the_family_loader_lands_the_flattened_fields_in_their_stored_shape(
    formula_graph: FakeGraph,
) -> None:
    """Two members, deliberately: a one-member family is not a real input.

    The artifact has no singleton families -- grouping by containment cannot produce one --
    and a lone member has no containment support, so it lands ``TIER_D`` and the tier
    assertion below would be asserting a degenerate case rather than the stored shape this
    test is about.
    """
    load_formula_families(
        formula_graph,
        [_family_row(_FAM_A, "VG:ENRICH:FORMULA:f001")],
        [
            _member_row(_FAM_A, "VG:ENRICH:FORMULA:f001"),
            _member_row(_FAM_A, "VG:ENRICH:FORMULA:f002", role="EXPANSION"),
        ],
    )
    props = formula_graph.node_props(LABEL_FORMULA_FAMILY)[0]
    assert json.loads(props["veda_counts"]) == {"RV": 1, "SV": 1}
    assert props["vedas"] == ["RV", "SV"]
    assert props["quality_tier"] == "TIER_B"
    edge = formula_graph.edge_props(REL_MEMBER_OF_FAMILY)[0]
    assert edge["quality_tier"] == "TIER_B"
    assert edge["knowledge_layer"] == "L2_DETERMINISTIC_DERIVED"


def test_the_family_loader_persists_the_evidence_count_it_computes(
    formula_graph: FakeGraph,
) -> None:
    """FAILING ON PURPOSE -- a computed property is dropped before it reaches the store.

    ``_property_safe`` puts ``evidence_count`` on every family row and every membership row,
    and its docstring gives the reason: it exists so that "how many spans support this?"
    stays a numeric comparison rather than a string parse, and the treatment is claimed to
    match ``iter_formula_nodes`` "exactly" so that a reader need not know which loader
    produced the node.

    Neither ``_FAMILY_NODE_QUERY`` nor ``_FAMILY_MEMBER_QUERY`` assigns it. Both write
    ``evidence`` and stop there, so the count is computed for 2,757 rows per build and thrown
    away. Measured against the live graph: ``evidence_count`` is NULL on 720 of 720
    ``FormulaFamily`` nodes and on 2,037 of 2,037 ``MEMBER_OF_FAMILY`` edges, while it is
    non-NULL on all 4,825 ``Formula`` nodes -- so the claimed parity with the ``Formula``
    layer does not hold and the property is unusable exactly where the docstring promises it.

    The fix is two lines of Cypher, and it is deliberately not made here.
    """
    family = _family_row(_FAM_A, "VG:ENRICH:FORMULA:f001", evidence=[_SPAN, _SPAN, _SPAN])
    member = _member_row(_FAM_A, "VG:ENRICH:FORMULA:f001")
    load_formula_families(formula_graph, [family], [member])
    assert formula_graph.node_props(LABEL_FORMULA_FAMILY)[0].get("evidence_count") == 3
    assert formula_graph.edge_props(REL_MEMBER_OF_FAMILY)[0].get("evidence_count") == 1


# ---------------------------------------------------------------------------
# Ritual structure: DESCRIBED_IN and HAS_STEP
# ---------------------------------------------------------------------------

#: Ritual YAML key -> relationship type. The apparatus keys come from the loader's own table
#: so this test cannot drift from it; the two V3 keys are added because ``load_rituals``
#: reads them through dedicated functions rather than through that table.
_RITUAL_KEYS: dict[str, str] = {
    **{key: rel for key, rel, _labels in _RITUAL_EDGES},
    "described_in": REL_DESCRIBED_IN,
    "has_step": REL_HAS_STEP,
}


@functools.cache
def _rituals_v3() -> tuple[dict[str, Any], ...]:
    parsed = yaml.safe_load((DOMAIN_DIR / "rituals_v3.yaml").read_text(encoding="utf-8"))
    return tuple(parsed.get("rituals") or [])


@functools.cache
def _rituals_v1() -> tuple[dict[str, Any], ...]:
    parsed = yaml.safe_load((DOMAIN_DIR / "rituals.yaml").read_text(encoding="utf-8"))
    return tuple(parsed.get("rituals") or [])


@functools.cache
def _merged_rituals() -> tuple[dict[str, Any], ...]:
    merge = _script("build_domain_v2")._merge_rituals
    return tuple(merge(list(_rituals_v1()), list(_rituals_v3())))


@functools.cache
def _entity_labels() -> dict[str, tuple[str, ...]]:
    """Every key a ritual edge can point at, with the labels the projection gives it."""
    labels: dict[str, tuple[str, ...]] = {
        key: (LABEL_DEVATA,) for key in registry_keys(PROJECT_ROOT)
    }
    for entity in load_domain_entities(PROJECT_ROOT):
        labels[entity.concept_id] = labels_for_node_type(entity.node_type)
    for key in load_corpus(PROJECT_ROOT).by_key:
        labels[key] = (LABEL_PASSAGE,)
    return labels


def test_every_described_in_passage_key_is_a_real_mantra() -> None:
    """A key that resolves to nothing lands nothing, and reads as "no passages" forever."""
    corpus = load_corpus(PROJECT_ROOT)
    assert corpus.mantras, "the corpus should be present"
    missing = [
        (ritual["ritual_id"], key)
        for ritual in _rituals_v3()
        for key in (ritual.get("described_in") or [])
        if key not in corpus.by_key
    ]
    assert not missing


def test_the_v3_file_authors_the_seventy_one_descriptions_the_layer_claims() -> None:
    total = sum(len(r.get("described_in") or []) for r in _merged_rituals())
    assert total == 71


def test_every_has_step_action_is_a_registry_entity_carrying_the_action_label() -> None:
    """HAS_STEP's range is ``Action``, so a step naming a CONCEPT is an endpoint violation."""
    entities = {e.concept_id: e for e in load_domain_entities(PROJECT_ROOT)}
    steps = [step for r in _rituals_v3() for step in (r.get("has_step") or [])]
    assert steps, "the V3 file should author at least one step"
    for step in steps:
        entity = entities.get(str(step["action"]))
        assert entity is not None, step["action"]
        assert LABEL_ACTION in labels_for_node_type(entity.node_type), step["action"]


def test_every_ritual_edge_endpoint_satisfies_its_declared_signature() -> None:
    """All eight keys, both ends, over the merged file the build actually loads."""
    labels = _entity_labels()
    violations: list[str] = []
    for ritual in _merged_rituals():
        subject = set(labels.get(str(ritual["ritual_id"]), ()))
        for key, rel_type in _RITUAL_KEYS.items():
            subjects, objects = RELATIONSHIP_SIGNATURES[rel_type]
            if not subject & subjects:
                violations.append(f"{ritual['ritual_id']} cannot be the subject of {rel_type}")
            for item in ritual.get(key) or []:
                target = str(item["action"] if key == "has_step" else item)
                if not set(labels.get(target, ())) & objects:
                    violations.append(f"{rel_type} -> {target} {sorted(labels.get(target, ()))}")
    assert not violations
    assert LABEL_RITUAL in subjects


def test_a_stated_step_order_always_states_its_basis() -> None:
    """An integer with no basis is exactly the defect ``order_basis`` exists to prevent.

    A step numbered because the corpus calls it the first draught and a step numbered because
    it happens to sit first in a list are not the same claim, and the integer alone cannot
    tell them apart.
    """
    for ritual in _rituals_v3():
        for step in ritual.get("has_step") or []:
            if step.get("order") is None:
                continue
            basis = step.get("order_basis")
            assert isinstance(basis, str) and basis.strip(), (
                f"{ritual['ritual_id']} step {step['action']} has order "
                f"{step['order']!r} with no order_basis"
            )
            assert str(step.get("basis", "")).strip(), "a stated ordinal needs its evidence"


@pytest.fixture
def ritual_graph() -> FakeGraph:
    """One rite, one offering, two passages, one action, and one wrongly-typed role."""
    graph = FakeGraph()
    graph.add_node(LABEL_RITUAL, "DomainEntity", entity_key="VG:CONCEPT:SOMA-PRESSING")
    graph.add_node("Offering", "DomainEntity", entity_key="VG:CONCEPT:HAVIS-OBLATION")
    graph.add_node(LABEL_ACTION, "DomainEntity", entity_key="VG:CONCEPT:PRATAHSAVANA")
    graph.add_node("Concept", "DomainEntity", entity_key="VG:CONCEPT:HOTR-PRIEST")
    for key in ("VG:RV:SAK:M03:S028:V001", "VG:RV:SAK:M03:S028:V004"):
        graph.add_node(LABEL_PASSAGE, canonical_key=key)
    return graph


def _ritual(**keys: Any) -> list[dict[str, Any]]:
    row: dict[str, Any] = {"ritual_id": "VG:CONCEPT:SOMA-PRESSING"}
    row.update(keys)
    return [row]


def test_the_ritual_loader_lands_descriptions_and_steps(ritual_graph: FakeGraph) -> None:
    report = _load_rituals(
        ritual_graph,
        _ritual(
            uses_offering=["VG:CONCEPT:HAVIS-OBLATION"],
            described_in=["VG:RV:SAK:M03:S028:V001", "VG:RV:SAK:M03:S028:V004"],
            has_step=[
                {
                    "action": "VG:CONCEPT:PRATAHSAVANA",
                    "order": 1,
                    "order_basis": "SOURCE_STATED_ORDINAL",
                    "basis": "RV 10.112.1 calls it the first draught.",
                    "passages": ["VG:RV:SAK:M10:S112:V001"],
                }
            ],
        ),
    )
    assert report.detail[REL_DESCRIBED_IN] == {"sent": 2, "landed": 2}
    assert report.detail[REL_HAS_STEP] == {"sent": 1, "landed": 1}
    assert report.complete
    step = ritual_graph.edge_props(REL_HAS_STEP)[0]
    assert step["step_order"] == 1
    assert step["order_basis"] == "SOURCE_STATED_ORDINAL"
    assert step["evidence_passages"] == ["VG:RV:SAK:M10:S112:V001"]
    assert step["quality_tier"] == "TIER_D"


def test_a_step_edge_always_carries_an_order_basis(ritual_graph: FakeGraph) -> None:
    """A YAML row that omits the basis must land ``UNSTATED``, not nothing.

    A missing property and "the source does not state an order" are different facts, and only
    the second is a fact about the corpus.
    """
    _load_rituals(
        ritual_graph, _ritual(has_step=[{"action": "VG:CONCEPT:PRATAHSAVANA", "order": 2}])
    )
    step = ritual_graph.edge_props(REL_HAS_STEP)[0]
    assert step["step_order"] == 2
    assert step["order_basis"] == "UNSTATED"


def test_a_description_row_whose_target_is_not_a_passage_lands_nothing(
    ritual_graph: FakeGraph,
) -> None:
    """DESCRIBED_IN's range is ``Passage``; the loader must not reach a registry entity."""
    report = _load_rituals(ritual_graph, _ritual(described_in=["VG:CONCEPT:HAVIS-OBLATION"]))
    assert report.detail[REL_DESCRIBED_IN] == {"sent": 1, "landed": 0}
    assert not report.complete
    assert ritual_graph.edge_props(REL_DESCRIBED_IN) == []


def test_a_step_row_whose_action_is_typed_concept_lands_nothing(
    ritual_graph: FakeGraph,
) -> None:
    """The blocker ``rituals_v3.yaml`` records: HOTR-PRIEST is ``node_type: CONCEPT``.

    A row that cannot satisfy its signature must be visible as an incomplete report rather
    than as an edge on the wrong label.
    """
    report = _load_rituals(ritual_graph, _ritual(has_step=[{"action": "VG:CONCEPT:HOTR-PRIEST"}]))
    assert report.detail[REL_HAS_STEP] == {"sent": 1, "landed": 0}
    assert not report.complete
    assert ritual_graph.edge_props(REL_HAS_STEP) == []


def test_a_description_removed_from_the_yaml_is_retracted(ritual_graph: FakeGraph) -> None:
    """Without the sweep the registry's retractions would be advisory rather than effective."""
    _load_rituals(
        ritual_graph,
        _ritual(
            described_in=["VG:RV:SAK:M03:S028:V001", "VG:RV:SAK:M03:S028:V004"],
            has_step=[{"action": "VG:CONCEPT:PRATAHSAVANA", "order": 1}],
        ),
    )
    assert len(ritual_graph.edge_props(REL_DESCRIBED_IN)) == 2

    second = _load_rituals(ritual_graph, _ritual(described_in=["VG:RV:SAK:M03:S028:V001"]))
    assert ritual_graph.edge_pairs(REL_DESCRIBED_IN, "entity_key", "canonical_key") == {
        ("VG:CONCEPT:SOMA-PRESSING", "VG:RV:SAK:M03:S028:V001")
    }
    assert ritual_graph.edge_props(REL_HAS_STEP) == [], "the dropped step should be swept too"
    assert second.detail["retired_stale"]["landed"] == 2


def test_reloading_the_same_rituals_changes_nothing(ritual_graph: FakeGraph) -> None:
    rituals = _ritual(
        uses_offering=["VG:CONCEPT:HAVIS-OBLATION"],
        described_in=["VG:RV:SAK:M03:S028:V001"],
        has_step=[{"action": "VG:CONCEPT:PRATAHSAVANA", "order": 1}],
    )
    _load_rituals(ritual_graph, rituals)
    first = len(ritual_graph.edges)
    report = _load_rituals(ritual_graph, rituals)
    assert len(ritual_graph.edges) == first
    assert report.detail["retired_stale"]["landed"] == 0
    assert report.complete


# ---------------------------------------------------------------------------
# The V2/V3 merge helpers
# ---------------------------------------------------------------------------


def _augmented_ids() -> list[str]:
    return [str(r["ritual_id"]) for r in _rituals_v3() if r.get("mode") == "augment"]


def test_the_v3_ritual_file_declares_itself_additive() -> None:
    """The merge semantics are read off the file, so the file has to state them."""
    parsed = yaml.safe_load((DOMAIN_DIR / "rituals_v3.yaml").read_text(encoding="utf-8"))
    assert parsed["merges_with"] == "rituals.yaml"
    assert parsed["supersedes"] == "nothing"
    assert len(_augmented_ids()) == 4


def test_merge_rituals_keeps_the_v1_apparatus_of_every_augmented_rite() -> None:
    """The important one. Letting the V3 record win outright would silently delete the
    yajna's, the soma pressing's, the agnihotra's and the consecration's V1 apparatus."""
    merged = {str(r["ritual_id"]): r for r in _merged_rituals()}
    v1 = {str(r["ritual_id"]): r for r in _rituals_v1()}
    assert set(_augmented_ids()) <= set(v1), "an 'augment' row must have something to augment"
    for ritual_id in _augmented_ids():
        for key, items in v1[ritual_id].items():
            if not isinstance(items, list):
                continue
            for item in items:
                assert item in merged[ritual_id][key], f"{ritual_id}.{key} lost {item}"


def test_merge_rituals_unions_the_two_performed_by_lists_v1_first() -> None:
    """Four V1 offices plus five V3 ones, in that order, with nothing replaced."""
    merge = _script("build_domain_v2")._merge_rituals
    v1 = {
        "ritual_id": "VG:CONCEPT:X",
        "performed_by": ["A", "B"],
        "confidence": "HIGH",
        "basis": "v1 basis",
    }
    v3 = {
        "ritual_id": "VG:CONCEPT:X",
        "mode": "augment",
        "performed_by": ["B", "C"],
        "confidence": "LOW",
        "basis": "v3 basis",
    }
    merged = merge([v1], [v3])
    assert len(merged) == 1
    assert merged[0]["performed_by"] == ["A", "B", "C"]
    assert merged[0]["confidence"] == "LOW", "a scalar describes the merged record"
    assert merged[0]["basis"] == "v3 basis"
    assert merged[0]["mode"] == "augment"


def test_merge_rituals_is_deterministic_and_idempotent() -> None:
    merge = _script("build_domain_v2")._merge_rituals
    once = merge(list(_rituals_v1()), list(_rituals_v3()))
    assert merge(list(_rituals_v1()), list(_rituals_v3())) == once
    assert merge(once, list(_rituals_v3())) == once, "merging twice must equal merging once"
    assert merge(once, once) == once
    assert [r["ritual_id"] for r in once] == sorted(str(r["ritual_id"]) for r in once)


def test_merge_rituals_handles_unhashable_step_mappings() -> None:
    """``has_step`` items are dicts, so identity has to be by content, not by hash."""
    merge = _script("build_domain_v2")._merge_rituals
    step = {"action": "VG:CONCEPT:A", "order": 1, "passages": ["VG:RV:SAK:M01:S001:V001"]}
    other = {"action": "VG:CONCEPT:B", "order": 2}
    merged = merge(
        [{"ritual_id": "VG:CONCEPT:X", "has_step": [step]}],
        [{"ritual_id": "VG:CONCEPT:X", "has_step": [dict(step), other]}],
    )
    assert merged[0]["has_step"] == [step, other], "an identical step must not be duplicated"


def test_merge_rituals_adds_a_rite_that_only_v3_declares() -> None:
    merge = _script("build_domain_v2")._merge_rituals
    merged = {str(r["ritual_id"]) for r in merge([], list(_rituals_v3()))}
    assert "VG:CONCEPT:SAUTRAMANI" in merged
    assert merged == {str(r["ritual_id"]) for r in _rituals_v3()}


def test_merge_rituals_does_not_mutate_its_inputs() -> None:
    merge = _script("build_domain_v2")._merge_rituals
    v1 = [{"ritual_id": "VG:CONCEPT:X", "performed_by": ["A"]}]
    v3 = [{"ritual_id": "VG:CONCEPT:X", "performed_by": ["B"]}]
    merge(v1, v3)
    assert v1 == [{"ritual_id": "VG:CONCEPT:X", "performed_by": ["A"]}]
    assert v3 == [{"ritual_id": "VG:CONCEPT:X", "performed_by": ["B"]}]


@functools.cache
def _concern_files() -> tuple[dict[str, Any], dict[str, Any]]:
    v1 = yaml.safe_load((DOMAIN_DIR / "concern_predicates.yaml").read_text(encoding="utf-8"))
    v3 = yaml.safe_load((DOMAIN_DIR / "concern_predicates_v3.yaml").read_text(encoding="utf-8"))
    return v1, v3


def _merged_concerns() -> dict[str, list[str]]:
    v1, v3 = _concern_files()
    merged: dict[str, list[str]] = _script("build_domain_v2")._merge_concern_lists(v1, v3)
    return merged


def test_the_v3_concern_file_declares_union_semantics() -> None:
    _v1, v3 = _concern_files()
    assert v3["merge_semantics"] == "union_with_v1"


def test_merge_concern_lists_unions_both_files_without_duplicates() -> None:
    """The union is V1, then V3's additions, then whatever ``promotions`` authorises.

    The third term is not decoration. A promotion records a membership deliberately *not*
    repeated in the V3 predicate list, so a merge that stopped after two terms dropped it
    silently -- see ``test_merge_concern_lists_preserves_the_recorded_promotion``. Order is
    asserted, not just set-equality, because the merge is supposed to be deterministic.
    """
    v1, v3 = _concern_files()
    merged = _merged_concerns()
    promoted: dict[str, list[str]] = {}
    for promotion in v3.get("promotions") or []:
        for key in promotion.get("to") or []:
            promoted.setdefault(key, []).append(promotion["concept_id"])

    for key, items in merged.items():
        base = list(v1.get(key) or [])
        expected = base + [item for item in (v3.get(key) or []) if item not in base]
        expected += [item for item in promoted.get(key, []) if item not in expected]
        assert items == expected, key
        assert len(items) == len(set(items)), key


def test_merge_concern_lists_excludes_the_prose_keys() -> None:
    """A whitelist becomes an edge type, so a prose key must never become one.

    ``no_typed_edge`` is the sharp case: it is a list of entity ids that were considered and
    refused, so admitting the key would emit exactly the edges the file exists to refuse.
    """
    _v1, v3 = _concern_files()
    merged = _merged_concerns()
    for prose in ("no_typed_edge", "notes", "version", "merge_semantics", "promotions"):
        assert prose in v3 or prose in _concern_files()[0], f"{prose} is not in either file"
        assert prose not in merged
    refused = set(v3["no_typed_edge"])
    for key, items in merged.items():
        assert not refused & set(items), f"{key} admitted a refused entity"
    assert set(merged) == {"addresses_concern", "used_for_rite", "treats", "protects_from"}


def test_merge_concern_lists_preserves_the_recorded_promotion() -> None:
    """FAILING ON PURPOSE -- the recorded promotion is never applied to the data.

    ``concern_predicates_v3.yaml`` carries a ``promotions`` block with exactly one row:
    ``VG:CONCEPT:SAPATNA-RIVAL-OVERCOMING``, ``from: [addresses_concern]``,
    ``to: [addresses_concern, protects_from]``. The file's own commentary calls it "the part
    that was simply missed" and states that both predicates are true of the rival charms.

    ``_merge_concern_lists`` reads only the four predicate keys. It never looks at
    ``promotions``, and SAPATNA is not repeated in the V3 ``protects_from`` list -- the block
    *is* the authoring of it -- so the union produces the V1 membership unchanged and the
    promotion is recorded in YAML and nowhere else. In the live graph the entity has 101
    ``ADDRESSES_CONCERN`` edges and 0 ``PROTECTS_FROM`` edges.

    This is the ``corrections_applied`` failure shape again: an audit block that says a
    change was made, and rows that were never changed. Not fixed here.
    """
    _v1, v3 = _concern_files()
    merged = _merged_concerns()
    for promotion in v3["promotions"]:
        for key in promotion["to"]:
            assert promotion["concept_id"] in merged[key], (
                f"{promotion['concept_id']} was promoted to {key} and is not in the merged list"
            )


# ---------------------------------------------------------------------------
# Live graph invariants -- read-only
# ---------------------------------------------------------------------------


def _driver() -> Any:
    from neo4j import GraphDatabase

    return GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "vedagraph_dev"))


def _scalar(session: Any, query: str, **params: Any) -> Any:
    record = session.run(query, **params).single()
    return None if record is None else record["c"]

@functools.lru_cache(maxsize=1)
def _published_pin() -> dict[str, Any]:
    """The pinned census of the graph's *published* formula generation.

    Not ``_families()``. The four tests below used to assert the graph against the
    enrichment JSONL, and that equality is unachievable by owner rule rather than by
    defect: ``formula_id`` is a published stable product ID served at
    ``/api/v1/formulas/{formula_id}``, it is a content hash, so re-mining re-keys it, and
    ``data/staging/final_stabilization/formula_identity_impact.json`` records
    ``migration_permitted: false`` over all 217 affected formulas. The enrichment layer was
    rebuilt anyway -- legitimately; ``manifest.json``'s digests match the live
    ``formulas.jsonl`` and its ``corpus_counts`` are this graph's own 20,210 mantras -- so
    the disk now holds a *later* generation than the frozen graph.

    Two generations, both correct, and a rule against collapsing them. Asserting they are
    equal failed on the count and so never reached the invariants these tests exist for.
    The suite already held the tell: ``tests/api/test_stats.py`` pins
    ``formula_families: 720``, which is the graph's figure and what the product serves, and
    it passes.

    So the expectation source is now ``scripts/pin_formula_layer_generation.py``'s pin,
    which records the published census AND its exact id-set distance from the rebuild.
    Both are falsifiers: change the graph and the census stops matching; rebuild the
    enrichment layer differently and the delta stops matching.
    """
    path = ENRICHMENT_DIR / "formula_layer_published_pin.json"
    assert path.exists(), (
        f"{path} is missing. Regenerate it with "
        "`python scripts/pin_formula_layer_generation.py --write`."
    )
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


@pytest.mark.live
@_LIVE
def test_live_every_formula_family_has_a_unique_family_id() -> None:
    """There is a uniqueness constraint; this checks the layer landed whole under it.

    Uniqueness is asserted over the whole graph population, and the population itself is
    asserted against the published pin -- see :func:`_published_pin` for why not the JSONL.
    """
    pin = _published_pin()["published_generation"]
    driver = _driver()
    try:
        with driver.session() as session:
            total = _scalar(session, "MATCH (f:FormulaFamily) RETURN count(f) AS c")
            distinct = _scalar(
                session, "MATCH (f:FormulaFamily) RETURN count(DISTINCT f.family_id) AS c"
            )
            assert total == distinct, f"{total - distinct} families share a family_id"
            assert total == pin["families"], (
                f"the graph holds {total} families and the published pin records "
                f"{pin['families']}. Either the frozen generation changed -- which the "
                "owner rule bars -- or the pin is stale."
            )
            assert (
                _scalar(
                    session,
                    "MATCH (f:FormulaFamily) WHERE f.family_id IS NULL RETURN count(f) AS c",
                )
                == 0
            )
            # A content-hash id that collided would put two formulas behind one published
            # URL, which is the failure the frozen-identity rule protects against.
            formulas = _scalar(session, "MATCH (f:Formula) RETURN count(f) AS c")
            assert formulas == pin["formulas"]
            assert (
                _scalar(
                    session,
                    "MATCH (f:Formula) "
                    'RETURN count(DISTINCT replace(f.normalized, " ", "")) AS c',
                )
                == formulas
            )
    finally:
        driver.close()


@pytest.mark.live
@_LIVE
def test_live_every_membership_edge_lands_on_a_real_formula() -> None:
    pin = _published_pin()["published_generation"]
    driver = _driver()
    try:
        with driver.session() as session:
            assert (
                _scalar(
                    session,
                    "MATCH (a)-[r:MEMBER_OF_FAMILY]->(b) "
                    "WHERE NOT a:Formula OR NOT b:FormulaFamily RETURN count(r) AS c",
                )
                == 0
            )
            assert (
                _scalar(
                    session,
                    "MATCH (:Formula)-[r:MEMBER_OF_FAMILY]->(:FormulaFamily) "
                    "RETURN count(r) AS c",
                )
                == pin["members"]
            )
            tiers = {
                record["c"]
                for record in session.run(
                    "MATCH ()-[r:MEMBER_OF_FAMILY]->() RETURN DISTINCT r.quality_tier AS c"
                )
            }
            assert tiers <= {"TIER_B", "TIER_D"}, tiers
            assert tiers == set(
                pin["quality_tiers"]
            ), "the tier vocabulary on landed edges moved away from the pinned one"
            # One formula joins one family: the layer's whole premise, and something the
            # count equality never checked.
            assert (
                _scalar(
                    session,
                    "MATCH (f:Formula)-[:MEMBER_OF_FAMILY]->(x) "
                    "WITH f, count(DISTINCT x) AS n WHERE n > 1 RETURN count(f) AS c",
                )
                == 0
            )
            # Each family's own declared member_count must equal what landed under it.
            assert (
                _scalar(
                    session,
                    "MATCH (fam:FormulaFamily) "
                    "OPTIONAL MATCH (:Formula)-[r:MEMBER_OF_FAMILY]->(fam) "
                    "WITH fam, count(r) AS landed "
                    "WHERE coalesce(fam.member_count, -1) <> landed RETURN count(fam) AS c",
                )
                == 0
            )
    finally:
        driver.close()


@pytest.mark.live
@_LIVE
def test_live_member_role_counts_are_the_published_generations() -> None:
    """Renamed: the expectation is the published pin, not "what the artifact says".

    The old name described its own defect. The artifact it read is a later generation the
    owner rule bars from landing, so the phrase "what the artifact says" stopped naming
    anything the graph is permitted to equal.
    """
    pin = _published_pin()["published_generation"]
    driver = _driver()
    try:
        with driver.session() as session:
            landed = {
                record["role"]: record["n"]
                for record in session.run(
                    "MATCH ()-[r:MEMBER_OF_FAMILY]->() RETURN r.role AS role, count(*) AS n"
                )
            }
            assert landed == pin["roles"]
            assert sum(landed.values()) == pin["members"]
            # The role vocabulary is closed, and the two generations agree about *which*
            # roles exist even where they disagree about how many.
            assert set(landed) == {"CORE", "EXPANSION", "VARIANT"}
            assert set(landed) == {str(m["role"]) for m in _members()}
    finally:
        driver.close()


@pytest.mark.live
@_LIVE
def test_live_the_containment_claim_is_recomputable_from_the_graph_alone() -> None:
    """The TIER_B claim, recomputed from the stored strings the graph itself holds.

    Nothing is read from the artifacts: the expansion's ``normalized``, its parent's
    ``normalized`` and the link between them all come out of the database, which is the
    property the grade claims -- "recomputable from the graph's own data by anyone who
    doubts it".

    That was the docstring before, and the test contradicted it on the next line by sizing
    its result set from ``_members()``. Dropping that read is what the docstring already
    asked for, and it widens the recomputation from the artifact's 1,079 expansions to all
    1,119 the graph holds. The count is pinned separately, against the published
    generation.
    """
    pin = _published_pin()["published_generation"]
    driver = _driver()
    try:
        with driver.session() as session:
            rows = list(
                session.run(
                    """
                    MATCH (child:Formula)-[r:MEMBER_OF_FAMILY]->(fam:FormulaFamily)
                    WHERE r.role = 'EXPANSION'
                    MATCH (parent:Formula {formula_id: r.linked_formula_id})
                          -[:MEMBER_OF_FAMILY]->(fam)
                    RETURN child.normalized AS child, parent.normalized AS parent,
                           child.formula_id AS child_id
                    """
                )
            )
            assert len(rows) == pin["roles"]["EXPANSION"], (
                "every EXPANSION edge must reach a parent inside its own family; "
                f"{pin['roles']['EXPANSION'] - len(rows)} did not"
            )
            for row in rows:
                child, parent = _identity(row["child"]), _identity(row["parent"])
                assert parent in child and parent != child, row["child_id"]
    finally:
        driver.close()


@pytest.mark.live
@_LIVE
def test_live_the_published_pin_records_its_distance_from_the_rebuild() -> None:
    """The rebuild may differ from the graph. It may not differ *silently*.

    Pinning only the graph's census would let the enrichment layer drift with nothing
    watching, and the drift is precisely what an owner has to re-adjudicate: it is the set
    of formulas whose published ids a recomputation would re-key. So the delta is pinned by
    id set, digested, and re-measured here against the live files. A rebuild that swapped
    one formula for another of equal count would still trip this.
    """
    pin = _published_pin()
    delta = pin["delta_published_to_rebuild"]
    assert pin["owner_rule"]["migration_permitted"] == "false"
    assert pin["owner_rule"]["recorded_in"].endswith("formula_identity_impact.json")

    live = {
        "formulas": {
            str(row["formula_id"]) for row in _read_jsonl(ENRICHMENT_DIR / "formulas.jsonl")
        },
        "families": {str(row["family_id"]) for row in _families()},
        "members": {f"{m['formula_id']}|{m['family_id']}|{m['role']}" for m in _members()},
    }
    for name, rebuilt in live.items():
        assert len(rebuilt) == delta[name]["rebuilt"], (
            f"the on-disk {name} generation moved: {len(rebuilt)} rows against the pinned "
            f"{delta[name]['rebuilt']}. Re-adjudicate the divergence against the owner "
            "rule, then regenerate the pin."
        )
        digest = hashlib.sha256(
            "\n".join(sorted(rebuilt - _pinned_published_ids(name))).encode("utf-8")
        ).hexdigest()
        assert digest == delta[name]["rebuilt_only_sha256"], (
            f"the {name} rows the rebuild holds and the published generation does not are "
            "no longer the pinned set"
        )


def _pinned_published_ids(name: str) -> set[str]:
    """The published-generation id set for ``name``, recovered from the live graph.

    The pin stores digests rather than the id lists themselves -- 4,825 formula ids would
    dominate a file whose job is to be readable -- so the set is re-read from the graph
    when the delta is checked. That is sound here because the surrounding test's other
    assertions have already pinned the graph's census against the same file.
    """
    query = {
        "formulas": "MATCH (f:Formula) RETURN f.formula_id AS i",
        "families": "MATCH (f:FormulaFamily) RETURN f.family_id AS i",
        "members": (
            "MATCH (a:Formula)-[r:MEMBER_OF_FAMILY]->(b:FormulaFamily) "
            "RETURN a.formula_id + '|' + b.family_id + '|' + r.role AS i"
        ),
    }[name]
    driver = _driver()
    try:
        with driver.session() as session:
            return {record["i"] for record in session.run(query) if record["i"] is not None}
    finally:
        driver.close()


@pytest.mark.live
@_LIVE
def test_live_ritual_descriptions_and_steps_are_the_counts_the_yaml_authors() -> None:
    driver = _driver()
    try:
        with driver.session() as session:
            assert _scalar(
                session, "MATCH (:Ritual)-[r:DESCRIBED_IN]->(:Passage) RETURN count(r) AS c"
            ) == sum(len(r.get("described_in") or []) for r in _merged_rituals())
            assert _scalar(
                session, "MATCH (:Ritual)-[r:HAS_STEP]->(:Action) RETURN count(r) AS c"
            ) == sum(len(r.get("has_step") or []) for r in _merged_rituals())
            for rel_type, label in ((REL_DESCRIBED_IN, "Passage"), (REL_HAS_STEP, "Action")):
                assert (
                    _scalar(
                        session,
                        f"MATCH (a)-[r:{rel_type}]->(b) WHERE NOT a:Ritual OR NOT b:{label} "
                        "RETURN count(r) AS c",
                    )
                    == 0
                )
    finally:
        driver.close()


@pytest.mark.live
@_LIVE
def test_live_every_step_edge_states_the_basis_for_its_order() -> None:
    driver = _driver()
    try:
        with driver.session() as session:
            assert (
                _scalar(
                    session,
                    "MATCH ()-[r:HAS_STEP]->() WHERE r.step_order IS NOT NULL AND "
                    "(r.order_basis IS NULL OR trim(toString(r.order_basis)) = '') "
                    "RETURN count(r) AS c",
                )
                == 0
            )
            assert (
                _scalar(
                    session,
                    "MATCH ()-[r:HAS_STEP]->() WHERE r.quality_tier <> 'TIER_D' "
                    "RETURN count(r) AS c",
                )
                == 0
            )
    finally:
        driver.close()
