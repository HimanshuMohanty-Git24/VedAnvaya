"""The two contracts whose absence made the first Wave 3 import over-write, then roll back.

Both defects were mine and both were invisible offline. The import reported every group as
ok and the census disagreed with the plan by 9 nodes and 5,930 relationships, which is the
exact shape of failure the campaign's rule 1 exists for: a MERGE can collapse two rows into
one and a MATCH can find no endpoint, and neither shows up until the database is asked.

These tests are on the *spec*, not on a database, so they run in the normal suite and fail
the moment a new element group reintroduces either mistake.
"""

from __future__ import annotations

import importlib

plan = importlib.import_module("scripts.wave3_import_plan")
imp = importlib.import_module("scripts.wave3_import")


def label_less_match_properties() -> set[str]:
    """Properties the spec matches on WITHOUT a label constraint.

    Derived from the groups rather than listed, so adding a label-less group on some other
    property makes the next test start protecting that property too. A hardcoded list would
    protect exactly the one mistake already made.
    """
    at_risk: set[str] = set()
    for group in plan.GROUPS:
        if group.kind not in ("RELATIONSHIP", "RELATIONSHIP_PROPERTY"):
            continue
        if not group.start_label:
            at_risk.add(group.start_key_property)
        if not group.end_label:
            at_risk.add(group.end_key_property)
    return at_risk


def test_no_group_carries_a_foreign_identity_property_onto_its_element() -> None:
    """A referent's key must not become the element's own key.

    The role-filler rows name the canonical entity a filler refers to in a field called
    ``entity_key``, and the passage it sits in as ``canonical_key``. Carrying either
    straight through puts another element's identity onto the filler. That is the
    duplication the M1 card forbids in words -- "not a duplicate of a canonical entity" --
    and this is the same rule with teeth.

    The first one cost an import. ``entity_key`` was unique across all 108,779 pre-import
    nodes; afterwards 85 keys were shared by 481 nodes, and a label-less endpoint match
    fanned 387 intended REFERS_TO edges into 4,564. The second, ``canonical_key``, was
    caught by this test before it cost anything -- no group matches on canonical_key without
    a label today, so it was a hazard rather than a defect, and it is renamed anyway because
    a filler's ``canonical_key`` is not the filler's key.
    """
    groups = {group.group_id: group for group in plan.GROUPS}
    # Union of what the spec matches label-lessly and the identity properties the graph
    # already indexes per label, since a label-less match on either would be ambiguous.
    at_risk = label_less_match_properties() | {
        "entity_key",
        "canonical_key",
        "formula_id",
        "family_id",
    }

    # Every NODE group, not only the ones in CARRIED. The two groups that carried a
    # Passage key were absent from CARRIED and so invisible to the first version of this
    # loop -- the widest exposure was the part the test could not see.
    for group in plan.GROUPS:
        if group.kind != "NODE":
            continue
        assert group.group_id in imp.CARRIED, (
            f"{group.group_id} declares no CARRIED fields, so it would carry whatever its "
            "row happens to hold. List them."
        )
        renamed = imp.RENAMED.get(group.group_id, {})
        for field in imp.CARRIED[group.group_id]:
            if field not in at_risk or field == group.match_property:
                continue
            assert field in renamed, (
                f"{group.group_id} carries {field!r}, which identifies a different "
                f"element, and its own match_property is {group.match_property!r}. Rename "
                f"it in RENAMED or drop it: an element answering to another element's key "
                f"makes every label-less match against that key ambiguous."
            )
    del groups


def test_the_role_filler_keeps_its_referent_under_a_name_that_is_not_an_identity() -> None:
    """The specific rename, asserted so a future edit cannot quietly undo it."""
    renames = imp.RENAMED["SR_ROLE_FILLER_NODES"]
    assert renames["entity_key"] == "refers_to_entity_key"
    assert renames["canonical_key"] == "passage_canonical_key"
    assert plan.GROUPS[0].group_id == "SR_ROLE_FILLER_NODES"
    assert plan.GROUPS[0].match_property == "role_filler_key"


def test_every_label_less_relationship_group_is_guarded() -> None:
    """A group matching endpoints without a label must be covered by the ambiguity guard.

    The guard skips a side that carries a label, because a labelled match is constrained by
    that label's own unique index. So the contract is: either the side has a label, or the
    guard runs on it. There is no third option, and the first import took the third option
    by having neither.
    """
    import inspect

    source = inspect.getsource(imp.assert_unambiguous)
    assert "count(n) AS c WHERE c > 1" in source, "the guard must actually count nodes per key"
    assert "if label:" in source, "the guard must skip a labelled side, not every side"

    for group in plan.GROUPS:
        if group.kind not in ("RELATIONSHIP", "RELATIONSHIP_PROPERTY"):
            continue
        # Both writers call the guard, so an unlabelled side is checked at write time. What
        # this asserts is that the group declares the key property the guard will read.
        assert group.start_key_property, f"{group.group_id}: no start key property"
        assert group.end_key_property, f"{group.group_id}: no end key property"


def test_the_writers_count_distinct_elements_not_unwind_rows() -> None:
    """``count(r)`` over an UNWIND counts MERGE operations, not edges.

    Three groups reported landing more than they were sent -- 685 sent and 4,117 "landed" --
    because the count was of rows processed rather than of distinct relationships. A number
    larger than the input should have been impossible, and reading it as a success is how
    5,930 surplus edges got past the per-group check.
    """
    import inspect

    for writer in (imp.write_relationships, imp.write_relationship_properties):
        source = inspect.getsource(writer)
        assert "count(DISTINCT r)" in source, f"{writer.__name__} must count distinct edges"
        assert "RETURN count(r)" not in source, (
            f"{writer.__name__} counts UNWIND rows, which over-reports a repeated pair"
        )


def test_node_writing_labels_an_existing_node_rather_than_merging_a_second() -> None:
    """``MERGE (n:Ritual {entity_key: X})`` does not find an existing ``:Concept`` with X.

    MERGE matches on label and properties together, so it created a second node under the
    same key for each of the 66 registry rows whose element the graph already held. The
    writer now creates the absent and labels the present, which is what the registries mean
    by EXISTING.

    The scan is over the function's code with its docstring removed. The first version of
    this test read the raw source and failed on the docstring above, which names the
    anti-pattern in order to explain it -- a check that cannot tell a prohibition from an
    occurrence is not a check.
    """
    import ast
    import inspect
    import textwrap

    tree = ast.parse(textwrap.dedent(inspect.getsource(imp.write_nodes)))
    function = tree.body[0]
    assert isinstance(function, ast.FunctionDef)
    if (
        function.body
        and isinstance(function.body[0], ast.Expr)
        and isinstance(function.body[0].value, ast.Constant)
    ):
        function.body = function.body[1:]
    code = ast.unparse(function)

    assert "SET n:" in code, "an existing element must gain the label, not a twin node"
    assert "CREATE (n:" in code, "an absent element must be created explicitly"
    assert "MERGE (n:" not in code, (
        "MERGE on label plus key cannot find the same key under another label"
    )


def test_the_plan_refuses_itself_when_an_endpoint_key_is_ambiguous() -> None:
    """The planner carries the same guard, so plan and import cannot disagree about it.

    The plan promised 387 REFERS_TO edges because it counted unique key triples; the import
    wrote 4,564 because it matched nodes. One guard in one of the two would have left the
    other free to be wrong.
    """
    import inspect

    source = inspect.getsource(plan.plan_group)
    assert "ambiguous_endpoint_keys" in source
    usable = inspect.getsource(plan.main)
    assert 'totals["ambiguous_endpoint_keys"] == 0' in usable, (
        "an ambiguous endpoint must make the plan unusable, not merely be reported"
    )


def test_node_props_refuses_a_group_that_declares_nothing() -> None:
    """The fallback is gone, and its absence is the assertion.

    ``node_props`` used to default to every field in the row. That is how a Passage's
    ``canonical_key`` reached 2,568 quality verdicts: nobody chose to put it there, an
    implicit rule did.
    """
    import dataclasses

    invented = dataclasses.replace(
        next(g for g in plan.GROUPS if g.kind == "NODE"),
        group_id="A_GROUP_THAT_DECLARES_NOTHING",
    )
    try:
        imp.node_props({"canonical_key": "VG:RV:SAK:M01:S001:V001"}, invented)
    except imp.UndeclaredProperties:
        return
    raise AssertionError("node_props accepted a group with no declared properties")


def test_the_quality_verdict_carries_its_reference_set_as_a_property() -> None:
    """The one distinction the quality domain exists to preserve must be queryable.

    161 passages carry two verdicts on different evidence: an
    INDEPENDENT_SOURCE_ADJUDICATED_REFERENCE_SET over the mention and concept layers,
    adjudicated by a published human treebank, and a DETERMINISTIC_TEXT_DERIVED_REFERENCE
    over HAS_CHANDAS, adjudicated by counting syllables. Left inside a JSON payload, that
    difference is invisible to every query, including the closure test.
    """
    lifted = imp.LIFTED["QUALITY_VERDICT_NODES"]
    assert lifted["payload.reference_set_type"] == "reference_set_type"
    assert lifted["payload.adjudicated_by"] == "adjudicated_by"


def test_no_written_property_collides_with_the_curated_domain_entity_contract() -> None:
    """A property name the curated loader writes must not be written by an import.

    ``SET n += row`` overwrites a MENTIONED key, and ``domain/loader.py`` writes
    display_label as ``f"{en} ({sa})" if en and sa else (en or sa)``. Writing display_label
    from a registry's label_en replaced that on 102 pre-existing nodes, and
    VG:CONCEPT:AYAS-METAL went from "metal (ayas)" to "metal" -- which broke the Q10
    assertion that ayas must never render as a bare zero, because the product's second
    rendering path looks the label up by prefix.

    The loader carries a comment about the other half of this rule, that an UNmentioned key
    is left in place. This is the half it does not mention.
    """
    curated = {
        "entity_key",
        "concept_id",
        "node_type",
        "preferred_label_sa",
        "preferred_label_en",
        "definition",
        "short_description",
        "aliases_sa",
        "aliases_en",
        "display_label",
        "display_type",
        "condition_kind",
        "domain_model_version",
    }
    for group in plan.GROUPS:
        if group.kind != "NODE":
            continue
        written = set(imp.CARRIED[group.group_id]) | set(
            imp.RENAMED.get(group.group_id, {}).values()
        )
        collisions = sorted(written & curated - {group.match_property})
        assert not collisions, (
            f"{group.group_id} writes {collisions}, which the curated DomainEntity loader "
            f"also writes. SET n += row overwrites a mentioned key, so this silently "
            f"replaces curated product data on every pre-existing node the group touches."
        )


def test_the_display_label_write_is_coalesced_and_never_direct() -> None:
    """The label goes on under a staging name and is coalesced in Cypher.

    Written directly it overwrote 102 curated labels. ``setdefault`` on the props dict was
    no protection: that dict is what the import is about to write, not what the node holds.
    """
    import ast
    import inspect
    import textwrap

    for fn in (imp.write_nodes,):
        tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
        function = tree.body[0]
        assert isinstance(function, ast.FunctionDef)
        if (
            function.body
            and isinstance(function.body[0], ast.Expr)
            and isinstance(function.body[0].value, ast.Constant)
        ):
            function.body = function.body[1:]
        # Whitespace-insensitive: the Cypher wraps across source lines, so the first
        # version of this assertion looked for an exact substring the query never contains.
        code = " ".join(ast.unparse(function).split())
        assert "n.display_label = coalesce( n.display_label" in code or (
            "n.display_label = coalesce(n.display_label" in code
        ), "an existing display_label must survive the write"
