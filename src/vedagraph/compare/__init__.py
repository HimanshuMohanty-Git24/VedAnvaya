"""Deterministic comparison of Rigveda text versions."""

from vedagraph.compare.report import render_report, write_report
from vedagraph.compare.run import (
    ComparisonResult,
    TextComparisonConfig,
    load_comparison_config,
    load_readings,
    run_comparison,
    summarize,
)
from vedagraph.compare.text import (
    COMPARATOR_VERSION,
    VersionReading,
    classify,
    compare_missing,
    compare_readings,
)

__all__ = [
    "COMPARATOR_VERSION",
    "ComparisonResult",
    "TextComparisonConfig",
    "VersionReading",
    "classify",
    "compare_missing",
    "compare_readings",
    "load_comparison_config",
    "load_readings",
    "render_report",
    "run_comparison",
    "summarize",
    "write_report",
]
