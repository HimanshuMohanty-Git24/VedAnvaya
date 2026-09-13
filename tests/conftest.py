"""Test configuration: make scripts/ importable, and run the untraced timers last."""

import sys
from pathlib import Path

import pytest

# The scripts that extract, crop, and bind AV scan data import each other as
# sibling modules (crop_atharvaveda_leaf, crop_atharvaveda_line, etc.). Adding
# the scripts directory to sys.path lets importlib-loaded scripts resolve those
# sibling imports without needing the scripts to be packaged.
_scripts = Path(__file__).resolve().parents[1] / "scripts"
if str(_scripts) not in sys.path:
    sys.path.insert(0, str(_scripts))


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Sort the latency tests to the end of the session, because pausing coverage is a
    one-way door for any thread that already exists.

    ``tests/api/conftest.py::untraced_measurement`` pauses coverage so that a millisecond
    budget measures the product rather than ``sys.settrace``. Pausing is
    ``Coverage.stop()`` and resuming is ``Coverage.start()``, and ``start()`` installs a
    tracer on the *calling* thread and arranges one for threads created *later*. It does
    not reach back into a thread that is already running -- and the live ``TestClient`` is
    session-scoped, so every route in this suite is executed on one long-lived anyio portal
    thread that was created before the first pause.

    The result, measured: the same 160 tests run as ``test_devatas.py test_graph.py`` left
    ``graph_service`` with 373 statements unmeasured, and as ``test_graph.py
    test_devatas.py`` with 55. Nothing about the tests changed -- only which of them paused
    coverage first. Left alone, one latency test silently blinded coverage for every live
    request that followed it, which is a worse defect than the one being fixed and an
    invisible one.

    Deferring them costs nothing: they are read-only live reads that no other test depends
    on, and running at the end of a full session is the condition the depth-2 budget was
    failing under anyway, so this measures the harder case rather than an easier one.
    """
    deferred_ids = {
        id(item) for item in items if "untraced_measurement" in getattr(item, "fixturenames", ())
    }
    if not deferred_ids:
        return
    kept = [item for item in items if id(item) not in deferred_ids]
    deferred = [item for item in items if id(item) in deferred_ids]
    items[:] = kept + deferred
