"""Test configuration: make scripts/ importable, keep credentials from leaking between
tests, and run the untraced timers last."""

import os
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


#: Environment names that configure a credential. ``load_credential_slots`` reads
#: ``os.environ`` directly and deliberately -- a slot is a deployment fact rather than a
#: settings field -- so any of these appearing mid-session silently reconfigures the LLM
#: factory for every test that follows.
_CREDENTIAL_MARKERS = ("_API_KEY", "_API_KEYS")


def _credential_env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if any(m in k for m in _CREDENTIAL_MARKERS)}


@pytest.fixture(scope="session")
def _credential_baseline() -> dict[str, str]:
    """The credentials configured before any test ran. The only trustworthy snapshot.

    Taken at session scope on purpose. A per-test snapshot is too late when the leak
    happens inside a *module*-scoped fixture: higher-scoped fixtures are set up first, so
    the per-test "before" would already contain the leaked key and would faithfully
    restore it.
    """
    return _credential_env()


@pytest.fixture(autouse=True)
def _no_credential_leaks_between_tests(_credential_baseline: dict[str, str]):
    """Undo credentials a test publishes into ``os.environ``, however it publishes them.

    Around two dozen one-off scripts under ``data/staging/**`` call ``load_dotenv`` on an
    absolute path at *import* time, and several tests import one of them with
    ``spec_from_file_location`` to reach a single pure function. Importing is enough: the
    developer's real ``VEDAGRAPH_LLM_API_KEY`` lands in ``os.environ`` and stays there.

    ``vedagraph.llm.credentials.load_credential_slots`` then finds it, and four tests in
    ``tests/llm`` that assert the *no-key* behaviour fail -- ``get_llm_provider`` stops
    raising on a missing key, and ``/ask/health`` answers 200 where it must answer 503.
    Whether they fail depends on collection order, so the suite is green on a machine with
    no ``.env`` and red on a developer's, which is the kind of difference that gets
    written off as "works in CI". The opposite ordering is the dangerous one: a guard that
    must fire when no key is configured cannot be trusted while any earlier test can
    quietly configure one.

    Restoring against the session baseline fixes it once for every importer, rather than
    once per test that happens to import such a module today, and it edits no sealed
    staging artifact. Only credential-shaped names are touched, so a test that legitimately
    manages its own environment is unaffected.
    """
    yield
    current = _credential_env()
    for name in current.keys() - _credential_baseline.keys():
        del os.environ[name]
    for name, value in _credential_baseline.items():
        if current.get(name) != value:
            os.environ[name] = value


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
