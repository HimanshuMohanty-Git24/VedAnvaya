"""Gitignored data the tests read, and the skip that names what is missing.

The corpus, the semantic runs and everything derived from them are excluded from Git:
each record carries its own source's rights (see LICENSE_SCOPE.md). A clean checkout --
which is exactly what CI runs -- therefore has none of it, and a test that reads it must
skip there rather than fail.

Check a file the build writes, never the directory it lives in. .gitignore keeps each
canonical build's manifest.json, so ``data/canonical/<build>/`` exists on every checkout;
the guard ``(ROOT / "data" / "canonical").is_dir()`` was true on a clean clone and let the
test go on to read records that were not there.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

#: One gitignored record file per canonical build, present only where the corpus was built.
RV_CORPUS = "data/canonical/rigveda_full_v1/passages.jsonl"
SV_CORPUS = "data/canonical/samaveda_arcika_v1/passages.jsonl"
YV_CORPUS = "data/canonical/yajurveda_vsm_v1/passages.jsonl"
AV_CORPUS = "data/canonical/atharvaveda_saunaka_digital_working_v1/passages.jsonl"
ALL_CORPORA = (RV_CORPUS, SV_CORPUS, YV_CORPUS, AV_CORPUS)


def missing(*paths: str | Path) -> list[str]:
    """The given repository-relative paths that do not exist in this checkout."""
    return [Path(p).as_posix() for p in paths if not (REPO / p).exists()]


def require_data(*paths: str | Path) -> None:
    """Skip the calling test unless every path exists."""
    absent = missing(*paths)
    if absent:
        pytest.skip("gitignored data not in this checkout: " + ", ".join(absent))


def needs_data(*paths: str | Path) -> pytest.MarkDecorator:
    """A skipif mark for a test, class or module that cannot run without these paths."""
    absent = missing(*paths)
    return pytest.mark.skipif(
        bool(absent), reason="gitignored data not in this checkout: " + ", ".join(absent)
    )
