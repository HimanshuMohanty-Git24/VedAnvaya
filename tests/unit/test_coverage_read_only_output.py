"""``--read-only-output`` must be a write barrier, not a label on one.

The coverage builder's default path MERGEs 1,085 ``:DerivedMetric`` nodes. During the
release-blocker pass the graph is frozen at 164,201 / 508,042 and the coverage figure still
has to be measured, so the flag exists. A flag whose name promises a read is worth nothing
unless something fails when the promise stops being kept, and there are two separate
promises to keep:

1.  the Neo4j session is opened ``READ``, so a mutation is refused by the driver;
2.  :func:`land_metrics` is unreachable, so no mutation is even composed.

Both are asserted here against a fake driver, which is what makes the test meaningful: a
real driver would let a regression pass on a standalone server, where READ routing is a
routing hint and not an authorization boundary. The fake raises on any mutating clause it
is handed, so reaching the write path fails loudly instead of quietly succeeding.

The negative control is the load-bearing half. ``test_the_default_path_still_lands_metrics``
asserts that WITHOUT the flag the write path IS reached -- so if the gate on line
``if not args.check and not args.read_only_output`` were deleted, the read-only tests break
rather than silently agreeing with a builder that now writes.
"""

from __future__ import annotations

import importlib
import json
import re
from typing import Any

import neo4j
import pytest

builder = importlib.import_module("build_veda_coverage_and_metrics")

MUTATION = re.compile(r"\b(CREATE|MERGE|SET|DELETE|DETACH|REMOVE|DROP|FOREACH)\b", re.I)


class FakeResult:
    """Enough of a driver result for ``_count`` and for iteration."""

    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def single(self) -> dict[str, Any] | None:
        return self._rows[0] if self._rows else None

    def __iter__(self):
        return iter(self._rows)


class FakeSession:
    def __init__(self, log: dict[str, Any]) -> None:
        self.log = log

    def __enter__(self) -> "FakeSession":
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def run(self, query: str, **parameters: Any) -> FakeResult:
        self.log["queries"].append(query)
        if MUTATION.search(query):
            self.log["mutations"].append(query)
            raise AssertionError(f"a mutation reached the driver: {query.strip()[:80]}")
        # Every read this builder performs is a `count(...) AS c`, plus the metric
        # aggregations, which are only reached on the write path.
        return FakeResult([{"c": 1}])


class FakeDriver:
    def __init__(self, log: dict[str, Any]) -> None:
        self.log = log

    def session(self, **kwargs: Any) -> FakeSession:
        self.log["access_modes"].append(kwargs.get("default_access_mode"))
        return FakeSession(self.log)

    def close(self) -> None:
        self.log["closed"] = True


@pytest.fixture()
def harness(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Run ``main()`` against a fake driver, with ``land_metrics`` replaced by a tripwire."""
    log: dict[str, Any] = {"queries": [], "mutations": [], "access_modes": [],
                           "land_metrics_calls": 0, "closed": False}

    def tripwire(session: Any) -> dict[str, Any]:
        log["land_metrics_calls"] += 1
        return {"TRIPWIRE": 0}

    monkeypatch.setattr(builder, "land_metrics", tripwire)
    monkeypatch.setattr(neo4j.GraphDatabase, "driver",
                        staticmethod(lambda *a, **k: FakeDriver(log)))

    def run(*argv: str) -> tuple[int, dict[str, Any]]:
        out = tmp_path / "coverage.json"
        monkeypatch.setattr(
            "sys.argv",
            ["build_veda_coverage_and_metrics.py", *argv, "--out", str(out)],
        )
        code = builder.main()
        log["output"] = json.loads(out.read_text(encoding="utf-8")) if out.exists() else None
        return code, log

    return run


def test_read_only_output_opens_a_read_session(harness) -> None:
    code, log = harness("--read-only-output")
    assert code == 0
    assert log["access_modes"] == ["READ"]


def test_read_only_output_cannot_reach_land_metrics(harness) -> None:
    code, log = harness("--read-only-output")
    assert code == 0
    assert log["land_metrics_calls"] == 0
    assert log["mutations"] == []


def test_read_only_output_still_writes_the_measured_coverage(harness) -> None:
    code, log = harness("--read-only-output")
    assert code == 0
    assert log["output"] is not None
    assert sorted(log["output"]["vedas"]) == ["AV", "RV", "SV", "YV"]
    # The metrics block is the write path's product and must be absent.
    assert "derived_metrics" not in log["output"]


def test_check_is_also_read_only(harness) -> None:
    code, log = harness("--check")
    assert code == 0
    assert log["access_modes"] == ["READ"]
    assert log["land_metrics_calls"] == 0


def test_the_default_path_still_lands_metrics(harness) -> None:
    """The negative control. Remove the gate and the tests above stop meaning anything."""
    code, log = harness()
    assert code == 0
    assert log["access_modes"] == ["WRITE"]
    assert log["land_metrics_calls"] == 1
    assert log["output"]["derived_metrics"] == {"TRIPWIRE": 0}


def test_the_flag_gates_the_only_call_site_in_the_source() -> None:
    """Belt and braces: the gate is in the source, not only in this test's fake.

    Reading the source as well as exercising it, because a fake driver proves what the code
    did on one path and this proves there is no second, ungated call site.
    """
    source = builder.__file__
    assert source is not None
    text = __import__("pathlib").Path(source).read_text(encoding="utf-8")
    call_sites = [
        line for line in text.splitlines() if "land_metrics(" in line and "def " not in line
    ]
    assert len(call_sites) == 1, call_sites
    assert "if not args.check and not args.read_only_output:" in text
    assert 'default_access_mode="READ" if args.check or args.read_only_output else "WRITE"' in text
