"""The gap registry's closure contract. Wave 4 Phase 7.

Before Wave 4 the registry had no closed state: no vocabulary for one, no field to hold one,
and 84 of 85 entries reading ``OPEN``. A registry in that shape cannot answer whether the
campaign is finished, because nothing in it can ever be finished — so the first thing these
tests hold is that a status outside the declared vocabulary cannot appear at all.

The second thing they hold is harder and matters more: **an entry may not be closed by
relabelling.** Five entries sit at ``BLOCKED_OWNER_DECISION_REQUIRED`` because material was
acquired, staged and then not imported, and the registry had already described one of them —
944 Atharvavedic translations — as "closed via the Wayback Machine" while the graph held none
of them. The test that counts data-completeness closures separately from execution blockers is
what stops that happening again silently.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
REGISTRY = PROJECT_ROOT / "data" / "gap_registry.json"
AUDIT = PROJECT_ROOT / "scripts" / "wave4_registry_closure_audit.py"

#: Vocabulary the owner's brief bars outright. A registry carrying any of these is not closed,
#: whatever its prose says.
FORBIDDEN = (
    "TODO",
    "OPEN",
    "LATER",
    "NOT_BUILT",
    "UNASSESSED",
    "UNKNOWN",
    "TEMPORARY",
    "PARTIALLY_ADDRESSED",
)


def _audit_module() -> object:
    """Import the audit script by path. It is a script, not a package member."""
    spec = importlib.util.spec_from_file_location("wave4_registry_closure_audit", AUDIT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def registry() -> dict[str, object]:
    if not REGISTRY.exists():
        pytest.skip("gap registry not present in this checkout")
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def test_no_entry_carries_a_forbidden_status(registry: dict[str, object]) -> None:
    gaps = registry["gaps"]
    assert isinstance(gaps, list)
    offenders = {
        str(gap["gap_id"]): str(gap["status"])
        for gap in gaps
        if str(gap.get("status")) in FORBIDDEN
    }
    assert not offenders, (
        f"{len(offenders)} entries still carry a status the brief bars: {offenders}"
    )


def test_every_status_is_in_the_declared_vocabulary(registry: dict[str, object]) -> None:
    """A status nobody declared is the same defect as an unclassified node label: it sits on
    the permissive side of every check by default."""
    vocabulary = registry["closure_vocabulary"]
    assert isinstance(vocabulary, dict)
    declared = set(
        list(vocabulary["closed"])
        + list(vocabulary["execution_blockers_not_data_completeness_closure"])
        + list(vocabulary["not_terminal"])
    )
    gaps = registry["gaps"]
    assert isinstance(gaps, list)
    used = {str(gap["status"]) for gap in gaps}
    assert used <= declared, f"undeclared status values in use: {sorted(used - declared)}"


def test_every_entry_states_its_basis(registry: dict[str, object]) -> None:
    gaps = registry["gaps"]
    assert isinstance(gaps, list)
    missing = [str(gap["gap_id"]) for gap in gaps if not gap.get("closure_basis")]
    assert not missing, f"entries with a status and no stated basis: {missing}"


def test_a_scope_decision_names_where_it_is_written_down(registry: dict[str, object]) -> None:
    """The check that stops the cheapest way to empty the registry.

    Relabelling forty unbuilt layers ``CLOSED_SCOPE_DECISION`` would satisfy every count in
    this file except this one.
    """
    gaps = registry["gaps"]
    assert isinstance(gaps, list)
    uncited = [
        str(gap["gap_id"])
        for gap in gaps
        if gap["status"] == "CLOSED_SCOPE_DECISION" and not gap.get("closure_citation")
    ]
    assert not uncited, f"scope decisions with no citation: {uncited}"


def test_an_external_source_block_carries_all_five_required_fields(
    registry: dict[str, object],
) -> None:
    vocabulary = registry["closure_vocabulary"]
    assert isinstance(vocabulary, dict)
    required = list(vocabulary["blocked_external_source_required_fields"])
    assert len(required) == 5
    gaps = registry["gaps"]
    assert isinstance(gaps, list)
    for gap in gaps:
        if gap["status"] != "BLOCKED_EXTERNAL_SOURCE_UNAVAILABLE":
            continue
        evidence = gap.get("closure_blocked_evidence") or {}
        missing = [field for field in required if not evidence.get(field)]
        assert not missing, f"{gap['gap_id']} is source-blocked without {missing}"


def test_an_owner_decision_block_names_the_decision(registry: dict[str, object]) -> None:
    gaps = registry["gaps"]
    assert isinstance(gaps, list)
    unnamed = [
        str(gap["gap_id"])
        for gap in gaps
        if gap["status"] == "BLOCKED_OWNER_DECISION_REQUIRED"
        and not gap.get("closure_owner_decision")
    ]
    assert not unnamed, f"owner-decision blocks with no named decision: {unnamed}"


def test_an_execution_blocker_is_never_counted_as_a_closure(
    registry: dict[str, object],
) -> None:
    """The two sets must stay disjoint, or "closed" quietly starts including "waiting"."""
    vocabulary = registry["closure_vocabulary"]
    assert isinstance(vocabulary, dict)
    closed = set(vocabulary["closed"])
    blockers = set(vocabulary["execution_blockers_not_data_completeness_closure"])
    not_terminal = set(vocabulary["not_terminal"])
    assert closed.isdisjoint(blockers)
    assert closed.isdisjoint(not_terminal)
    assert blockers.isdisjoint(not_terminal)
    assert "NEEDS_AUDIBLE_REVIEW" in blockers, (
        "an audio row awaiting a listener must never be a data-completeness closure"
    )


def test_the_ruling_table_covers_the_registry_exactly() -> None:
    """A ruling for an entry that no longer exists, or an entry with no ruling, both make the
    audit's counts a subset of the truth rather than the truth."""
    if not REGISTRY.exists() or not AUDIT.exists():
        pytest.skip("registry or audit script not present in this checkout")
    module = _audit_module()
    rulings = module.RULINGS  # type: ignore[attr-defined]
    ids = {
        str(gap["gap_id"])
        for gap in json.loads(REGISTRY.read_text(encoding="utf-8"))["gaps"]
    }
    assert set(rulings) == ids, (
        f"entries without a ruling: {sorted(ids - set(rulings))}; "
        f"rulings for no entry: {sorted(set(rulings) - ids)}"
    )


def test_the_audit_refuses_an_uncited_scope_decision() -> None:
    """BAD -> FAIL on the audit's own downgrade rule, without touching the registry.

    Asserted against the rule rather than the data: an uncited ``CLOSED_SCOPE_DECISION`` must
    come out of the audit as not-terminal, so the cheap way to empty the registry fails inside
    the instrument as well as in the file it writes.
    """
    if not AUDIT.exists():
        pytest.skip("audit script not present in this checkout")
    module = _audit_module()
    every = module.RULINGS  # type: ignore[attr-defined]
    cited = [r for r in every.values() if r.status == "CLOSED_SCOPE_DECISION"]
    assert cited, "no scope decisions to check"
    assert all(r.citation for r in cited)
    assert "CLOSED_SCOPE_DECISION" in module.CLOSED  # type: ignore[attr-defined]
    assert "STILL_IMPLEMENTATION_FIXABLE" in module.NOT_TERMINAL  # type: ignore[attr-defined]
