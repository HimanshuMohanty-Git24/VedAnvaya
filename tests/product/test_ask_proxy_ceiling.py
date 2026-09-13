"""The Ask proxy ceiling, held against the backend's real worst case.

The frontend reaches the API through a Next rewrite, and that rewrite has a timeout. If it
expires first, Next answers 500 and the UI renders "The VedaGraph knowledge service could
not be reached" -- a claim that the corpus is unreachable, made about a backend that was
still answering. The product's whole contract is not saying untrue things about what it
holds, so the proxy must outlast the backend rather than race it.

The backend's bound is not one number. A single Ask may spend
``VEDAGRAPH_LLM_TIMEOUT_SECONDS`` on each of ``VEDAGRAPH_LLM_MAX_RETRIES + 1`` attempts and
sleep between them, capped per sleep by the provider layer. A release-closure walk measured
one Ask at 120.4s against a 120s ceiling, so this was reachable, not hypothetical.

This test exists because both halves are edited independently: the ceiling lives in
frontend TypeScript and the budget in Python settings, and nothing else would notice them
drifting apart.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from vedagraph.llm.config import LLMSettings
from vedagraph.llm.providers.openai_compat import _MAX_BACKOFF_SECONDS

NEXT_CONFIG = Path(__file__).resolve().parents[2] / "frontend" / "next.config.ts"


def _proxy_timeout_ms() -> int:
    """The configured ceiling, read from the file the frontend actually builds from."""
    source = NEXT_CONFIG.read_text(encoding="utf-8")
    match = re.search(r"proxyTimeout:\s*([\d_]+)", source)
    assert match is not None, f"no proxyTimeout in {NEXT_CONFIG}"
    return int(match.group(1).replace("_", ""))


def _backend_worst_case_seconds(settings: LLMSettings) -> float:
    """Every attempt at full timeout, plus every backoff sleep at its cap."""
    attempts = settings.vedagraph_llm_max_retries + 1
    sleeps = settings.vedagraph_llm_max_retries
    return attempts * settings.vedagraph_llm_timeout_seconds + sleeps * _MAX_BACKOFF_SECONDS


def test_proxy_outlasts_the_backend_so_its_own_error_is_what_surfaces() -> None:
    settings = LLMSettings()
    worst_case = _backend_worst_case_seconds(settings)
    ceiling = _proxy_timeout_ms() / 1000
    assert ceiling > worst_case, (
        f"proxyTimeout is {ceiling:.0f}s but one Ask may take {worst_case:.0f}s "
        f"({settings.vedagraph_llm_max_retries + 1} attempts x "
        f"{settings.vedagraph_llm_timeout_seconds:.0f}s + "
        f"{settings.vedagraph_llm_max_retries} x {_MAX_BACKOFF_SECONDS:.0f}s backoff). "
        "Past the ceiling the reader is told the knowledge service is unreachable while "
        "it is still working. Raise proxyTimeout in frontend/next.config.ts, or lower the "
        "LLM budget."
    )


@pytest.mark.parametrize("retries", [0, 3, 9])
def test_the_bound_tracks_the_settings_rather_than_a_pinned_number(retries: int) -> None:
    """A raised retry count has to move the requirement, or the check rots into a constant."""
    settings = LLMSettings(vedagraph_llm_max_retries=retries)
    assert _backend_worst_case_seconds(settings) == pytest.approx(
        (retries + 1) * settings.vedagraph_llm_timeout_seconds + retries * _MAX_BACKOFF_SECONDS
    )
