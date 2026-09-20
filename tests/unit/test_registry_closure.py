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


# --------------------------------------------------------------------------------------
# The gate must be able to fail. Every test below constructs a BAD input and asserts the
# audit rejects it, against a stub session so nothing touches the live graph.
#
# The defect they exist for: ``measurement_disagreements`` compared a graph measurement to a
# pre-declared number and nothing else. It never compared the ruling's *status* to the status
# the registry holds -- so when ``translation_integration_registry.py`` wrote
# STILL_IMPLEMENTATION_FIXABLE onto four translation entries whose owner decisions had been
# made, while the ruling table still said BLOCKED_OWNER_DECISION_REQUIRED, the audit printed
# "0 disagreements" over four plain disagreements and reported 39 fixable against a measured
# 43. A disagreement detector that reports 0 during a real disagreement is worse than none.
# --------------------------------------------------------------------------------------


class _StubRecord:
    def __init__(self, value: int) -> None:
        self._value = value

    def __getitem__(self, _index: int) -> int:
        return self._value


class _StubResult:
    def __init__(self, value: int) -> None:
        self._value = value

    def single(self) -> _StubRecord:
        return _StubRecord(self._value)


class _StubSession:
    """Answers every Cypher with one fixed number. No graph, no network."""

    def __init__(self, value: int = 0) -> None:
        self.value = value
        self.queries: list[str] = []

    def run(self, cypher: str) -> _StubResult:
        self.queries.append(cypher)
        return _StubResult(self.value)


def _one_entry_audit(module, ruling, registry_status: str) -> dict:
    """Run the audit over a single synthetic entry with a stubbed measurement."""
    gid = "GAP-SYNTHETIC-001"
    saved = dict(module.RULINGS)
    try:
        module.RULINGS.clear()
        module.RULINGS[gid] = ruling
        expect = getattr(ruling, "expect", None)
        session = _StubSession(0 if expect is None else expect)
        return module.audit(session, [{"gap_id": gid, "status": registry_status}])
    finally:
        module.RULINGS.clear()
        module.RULINGS.update(saved)


def test_the_ruling_table_agrees_with_every_registry_status(
    registry: dict[str, object],
) -> None:
    """GOOD input, and the one that was failing silently.

    Two mechanisms write ``status`` into the registry: this audit's ``--write``, and
    ``scripts/translation_integration_registry.py``. Two writers on one field need a
    reconciliation, and this is it.
    """
    if not AUDIT.exists():
        pytest.skip("audit script not present in this checkout")
    module = _audit_module()
    rulings = module.RULINGS
    gaps = registry["gaps"]
    assert isinstance(gaps, list)
    disagreements = {
        str(gap["gap_id"]): (rulings[str(gap["gap_id"])].status, str(gap["status"]))
        for gap in gaps
        if str(gap["gap_id"]) in rulings
        and rulings[str(gap["gap_id"])].status != str(gap["status"])
    }
    assert not disagreements, (
        f"{len(disagreements)} entries where the audit's ruling and the registry's status "
        f"disagree (ruling, registry): {disagreements}"
    )


def test_a_registry_status_disagreement_is_reported() -> None:
    """BAD input -> the audit must say so. This is the recurrence guard."""
    if not AUDIT.exists():
        pytest.skip("audit script not present in this checkout")
    module = _audit_module()
    ruling = module.Ruling(
        "BLOCKED_OWNER_DECISION_REQUIRED",
        "synthetic",
        owner_decision="OWNER_DECISION_SYNTHETIC",
    )
    report = _one_entry_audit(module, ruling, "STILL_IMPLEMENTATION_FIXABLE")
    assert report["registry_status_disagreements"], (
        "the ruling said BLOCKED_OWNER_DECISION_REQUIRED and the registry said "
        "STILL_IMPLEMENTATION_FIXABLE, and the audit reported no disagreement"
    )
    assert "GAP-SYNTHETIC-001" in report["registry_status_disagreements"][0]


def test_an_agreeing_registry_status_is_not_reported() -> None:
    """The control. If every input were rejected the test above would prove nothing."""
    if not AUDIT.exists():
        pytest.skip("audit script not present in this checkout")
    module = _audit_module()
    ruling = module.Ruling("STILL_IMPLEMENTATION_FIXABLE", "synthetic")
    report = _one_entry_audit(module, ruling, "STILL_IMPLEMENTATION_FIXABLE")
    assert report["registry_status_disagreements"] == []


def test_the_audit_downgrades_a_constructed_uncited_scope_decision() -> None:
    """BAD input, built rather than looked for.

    The earlier version of this check asserted that the scope decisions in the shipped table
    all carry citations -- a fact about the data, not a demonstration that the rule fires. It
    would have passed unchanged if the downgrade branch had been deleted.
    """
    if not AUDIT.exists():
        pytest.skip("audit script not present in this checkout")
    module = _audit_module()
    ruling = module.Ruling("CLOSED_SCOPE_DECISION", "synthetic", citation="")
    report = _one_entry_audit(module, ruling, "CLOSED_SCOPE_DECISION")
    row = report["rows"][0]
    assert row["closure_status"] == "STILL_IMPLEMENTATION_FIXABLE"
    assert row["downgraded"] is True
    assert report["closed"] == 0
    assert any("no citation" in f for f in report["measurement_disagreements"])


def test_a_cited_scope_decision_survives() -> None:
    """The control for the downgrade."""
    if not AUDIT.exists():
        pytest.skip("audit script not present in this checkout")
    module = _audit_module()
    ruling = module.Ruling(
        "CLOSED_SCOPE_DECISION", "synthetic", citation="docs/PRODUCT_V1_SCOPE.md:212-221"
    )
    report = _one_entry_audit(module, ruling, "CLOSED_SCOPE_DECISION")
    assert report["rows"][0]["closure_status"] == "CLOSED_SCOPE_DECISION"
    assert report["closed"] == 1


def test_a_graph_measurement_that_misses_its_expectation_is_reported() -> None:
    """BAD input: the stub returns a number the ruling did not declare."""
    if not AUDIT.exists():
        pytest.skip("audit script not present in this checkout")
    module = _audit_module()
    gid = "GAP-SYNTHETIC-001"
    saved = dict(module.RULINGS)
    try:
        module.RULINGS.clear()
        module.RULINGS[gid] = module.Ruling(
            "CLOSED_DERIVED", "synthetic", "MATCH (n) RETURN count(n)", 5385
        )
        report = module.audit(
            _StubSession(5384), [{"gap_id": gid, "status": "CLOSED_DERIVED"}]
        )
    finally:
        module.RULINGS.clear()
        module.RULINGS.update(saved)
    assert report["measurement_disagreements"], (
        "5,384 measured against 5,385 declared, and the audit reported no disagreement"
    )
    assert report["rows"][0]["closure_measured_value"] == 5384


def test_an_external_source_block_missing_a_field_is_downgraded() -> None:
    """BAD input: four of the five required fields, which is not five."""
    if not AUDIT.exists():
        pytest.skip("audit script not present in this checkout")
    module = _audit_module()
    partial = {field: "stated" for field in module.BLOCKED_EVIDENCE_FIELDS[:-1]}
    ruling = module.Ruling(
        "BLOCKED_EXTERNAL_SOURCE_UNAVAILABLE", "synthetic", blocked_evidence=partial
    )
    report = _one_entry_audit(module, ruling, "BLOCKED_EXTERNAL_SOURCE_UNAVAILABLE")
    row = report["rows"][0]
    assert row["closure_status"] == "BLOCKED_EVIDENCE_INCOMPLETE"
    assert row["closure_blocked_evidence_missing"] == [module.BLOCKED_EVIDENCE_FIELDS[-1]]
    assert report["closed"] == 0


def test_gate_coverage_is_reported_so_a_skipped_row_is_visible() -> None:
    """A ruling with no ``expect`` is never compared to anything and passes by being skipped.

    Precision without coverage is how a validator reports a clean run over rows it never
    looked at, so the count of ungated entries -- and of closures asserted with no live
    measurement -- is published rather than left to be noticed.
    """
    if not AUDIT.exists():
        pytest.skip("audit script not present in this checkout")
    module = _audit_module()
    ruling = module.Ruling("CLOSED_DERIVED", "synthetic")
    report = _one_entry_audit(module, ruling, "CLOSED_DERIVED")
    cov = report["gate_coverage"]
    assert cov["without_a_gating_measurement"] == 1
    assert cov["closures_asserted_with_no_live_measurement"] == ["GAP-SYNTHETIC-001"]
