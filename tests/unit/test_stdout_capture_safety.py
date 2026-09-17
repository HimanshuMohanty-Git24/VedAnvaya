"""No module may take ownership of pytest's captured stdout at import time.

Measured cost of the defect this pins, at the final closure sprint's baseline:

    pytest tests/unit tests/api tests/domain --collect-only
        before:    349 tests collected, then ValueError: I/O operation on closed file
        after:   3,226 tests collected

22 modules ran ``sys.stdout = io.TextIOWrapper(sys.stdout.buffer, ...)`` at import. That
wrapper takes OWNERSHIP of the buffer it wraps, and when it is garbage collected it closes
it -- and under pytest that buffer is the capture tmpfile. So importing any one of them
mid-session killed collection for everything after it, and the combined command reported
green over **10.8%** of the suite while appearing to pass.

Wave 4 found this in exactly one module (the chandas builder, whose documented residual
shipped *because* pytest could not import it) and fixed that one. The other 21 kept doing it
for two more waves, because nothing measured collection COVERAGE -- only that the tests which
did run, passed. A validator that silently skips is worse than none.

``sys.stdout.reconfigure(...)`` is the remedy: it mutates the existing stream instead of
wrapping it, so nothing takes ownership and capture survives.
"""

from __future__ import annotations

import pathlib
import re

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
SEARCHED = ("scripts", "src")

#: Assignment to sys.stdout/sys.stderr, at any indentation. `reconfigure` is not an
#: assignment and does not match.
OWNERSHIP_TAKEN = re.compile(r"^\s*sys\.std(out|err)\s*=\s*", re.MULTILINE)


def _python_files() -> list[pathlib.Path]:
    found: list[pathlib.Path] = []
    for root in SEARCHED:
        for path in (PROJECT_ROOT / root).rglob("*.py"):
            if "__pycache__" not in path.parts:
                found.append(path)
    return found


def test_no_module_reassigns_sys_stdout() -> None:
    """The check is over every file, so a new offender cannot arrive unnoticed."""
    files = _python_files()
    assert len(files) > 100, f"only {len(files)} files searched; the sweep is not reaching the tree"

    offenders: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in OWNERSHIP_TAKEN.finditer(text):
            line = text[: match.start()].count("\n") + 1
            offenders.append(f"{path.relative_to(PROJECT_ROOT).as_posix()}:{line}")

    assert offenders == [], (
        f"{len(offenders)} module(s) reassign sys.stdout/sys.stderr, which takes ownership "
        "of pytest's capture tmpfile and aborts collection for every test imported after "
        f"them. Use sys.stdout.reconfigure(...) instead. Offenders: {offenders[:8]}"
    )


def test_the_sweep_can_actually_see_an_offender() -> None:
    """The control. Without this, an over-narrow regex would pass by matching nothing."""
    assert OWNERSHIP_TAKEN.search(
        'sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")'
    )
    assert OWNERSHIP_TAKEN.search("    sys.stderr = open('x')"), "indented form must match"
    assert not OWNERSHIP_TAKEN.search(
        'sys.stdout.reconfigure(encoding="utf-8", errors="replace")'
    ), "the remedy must not be flagged as the defect"
    assert not OWNERSHIP_TAKEN.search("if sys.stdout == other:"), "a comparison is not an assignment"
