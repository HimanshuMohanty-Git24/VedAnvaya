"""Contract tests for the ``Work`` corpus-scope overlay.

These run offline. What is worth pinning here is decidable from the registry and from the
Cypher the loader emits: that every declared work carries a scope, that the Sāmavedic
label can no longer read as the complete Sāmaveda, that the loader never mints a ``Work``
node, and that the verification counts each property separately instead of counting
matched nodes once. A test needing Neo4j running would be skipped exactly when it mattered.
"""

from __future__ import annotations

from typing import Any

import pytest

from vedagraph.config.registry import load_works
from vedagraph.domain.upgrade import _DISPLAY_SOURCES
from vedagraph.domain.work_scope import (
    _SCOPE_QUERY,
    SCOPE_PROPERTIES,
    load_work_scope,
    rows_from_works,
)
from vedagraph.models import Work


class _Record:
    def __init__(self, value: int) -> None:
        self._value = value

    def __getitem__(self, key: str) -> int:
        return self._value


class _Result:
    def __init__(self, value: int) -> None:
        self._value = value

    def single(self) -> _Record:
        return _Record(self._value)


class _FakeSession:
    """Records every statement and answers each count with a fixed number."""

    def __init__(self, count: int = 4) -> None:
        self.statements: list[str] = []
        self.rows: list[dict[str, Any]] = []
        self._count = count

    def run(self, query: str, **parameters: Any) -> _Result:
        self.statements.append(query)
        if "rows" in parameters:
            self.rows = list(parameters["rows"])
        return _Result(self._count)


@pytest.fixture
def works() -> list[Work]:
    return load_works()


def test_every_declared_work_carries_a_scope(works: list[Work]) -> None:
    """A ``Work`` with no scope is the defect this layer exists to remove."""
    unscoped = [work.work_id for work in works if not work.scope]
    assert unscoped == []


def test_every_scope_names_its_evidence(works: list[Work]) -> None:
    """A scope claim without a pointer to what licenses it is an unsourced assertion."""
    for work in works:
        assert work.scope_evidence, work.work_id


def test_every_work_states_a_measured_completeness_and_not_only_a_verdict(
    works: list[Work],
) -> None:
    """``coverage_status`` is a verdict; a reader also needs the figure behind it."""
    for work in works:
        assert work.completeness, work.work_id
        assert any(char.isdigit() for char in work.completeness), work.work_id


def test_the_samaveda_label_can_no_longer_read_as_the_complete_samaveda() -> None:
    """The corpus is the Kauthuma ārcika; its own manifest forbids the broader claim.

    ``work_name`` stays "Samaveda Samhita" because that is what the hashed canonical
    artifact records and because it is a true name. The product label must not.
    """
    samaveda = next(w for w in load_works() if w.work_id == "VG:WORK:SV:KAU")
    assert samaveda.display_label_override is not None
    label = samaveda.display_label_override.lower()
    assert "arcika" in label
    assert "gana" in label
    assert "SAMAVEDA_GRAMAGEYA_GANA" in samaveda.excluded_corpora
    assert "SAMAVEDA_UHAGANA" in samaveda.excluded_corpora


def test_the_yajurveda_scope_says_the_krishna_recensions_are_absent() -> None:
    """ "The Yajurveda" covers both in ordinary use; this corpus holds only the Śukla."""
    yajurveda = next(w for w in load_works() if w.work_id == "VG:WORK:YV:VSM")
    assert "KRISHNA_YAJURVEDA_TAITTIRIYA" in yajurveda.excluded_corpora
    assert yajurveda.scope is not None and "KRISHNA" in yajurveda.scope.upper()


def test_the_atharvaveda_scope_says_paippalada_is_absent() -> None:
    """A Śaunaka absence is not an Atharvavedic absence."""
    atharvaveda = next(w for w in load_works() if w.work_id == "VG:WORK:AV:SAU")
    assert "ATHARVAVEDA_PAIPPALADA_RECENSION" in atharvaveda.excluded_corpora


def test_unscoped_works_are_skipped_rather_than_written_as_null() -> None:
    """Writing the null would be indistinguishable from the defect being fixed."""
    scoped = Work(
        work_id="VG:WORK:XX:AAA",
        abbreviation="XX",
        veda="Test",
        work_name="Test",
        recension="Test",
        hierarchy=["Mantra"],
        citation_pattern="XX {mantra}",
        scope="a scope",
    )
    unscoped = scoped.model_copy(update={"work_id": "VG:WORK:XX:BBB", "scope": None})
    rows = rows_from_works([scoped, unscoped])
    assert [row["work_id"] for row in rows] == ["VG:WORK:XX:AAA"]


def test_the_loader_never_mints_a_work_node() -> None:
    """An unlabelled or MERGEd write here would invent a fifth Veda from a typo."""
    assert "MERGE (w:Work" not in _SCOPE_QUERY
    assert "MATCH (w:Work {work_id: row.work_id})" in _SCOPE_QUERY


def test_verification_counts_each_property_separately() -> None:
    """One count of matched nodes would report 4/4 with a property missing on all four."""
    session = _FakeSession()
    report = load_work_scope(session, load_works())
    assert report.sent == 4
    for prop in SCOPE_PROPERTIES:
        assert prop in report.detail
        assert any(f"w.{prop} IS NOT NULL" in stmt for stmt in session.statements)


def test_the_display_override_is_written_onto_the_node_not_only_applied() -> None:
    """Order-independence with ``upgrade.set_display_properties`` depends on this."""
    assert "w.display_label_override = row.display_label_override" in _SCOPE_QUERY
    work_sources = next(sources for label, sources, _ in _DISPLAY_SOURCES if label == "Work")
    assert work_sources[0] == "display_label_override", (
        "set_display_properties must coalesce the override first, or whichever loader "
        "runs last wins and the scope-honest label silently reverts"
    )
