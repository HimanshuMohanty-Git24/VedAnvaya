"""The provider contract matrix: every adapter normalises to the same LLMResponse.

The claim these tests defend is the one the whole Ask pipeline rests on -- that switching
provider is a configuration change and nothing downstream can tell. That is only true if
three unrelated vendor payloads collapse onto identical response semantics, so the same
assertions run against all three with the transport mocked.

No test here needs a key or a socket. Gemini speaks REST over an ``httpx.Client`` held at
``self._client``; the other two hold a vendor SDK client at the same attribute. In both
cases the seam is that one attribute, so a fake with the right call shape is enough and
the adapter under test is the real one.
"""

from __future__ import annotations

import json as json_module
from types import SimpleNamespace
from typing import Any

import pytest

from vedagraph.llm.base import (
    LLMCapabilities,
    LLMMessage,
    LLMRequest,
    LLMResponse,
    normalise_finish_reason,
)
from vedagraph.llm.errors import (
    LLMAuthenticationError,
    LLMContentBlockedError,
    LLMProviderUnavailableError,
    LLMRateLimitError,
    LLMResponseError,
)
from vedagraph.llm.providers.anthropic import AnthropicProvider
from vedagraph.llm.providers.gemini import GeminiProvider
from vedagraph.llm.providers.openai_compat import OpenAICompatProvider

#: Not a credential. Shaped like one so a leak would be recognisable in a diff.
FAKE_KEY = "test-key-not-real"

PROVIDER_NAMES = ("gemini", "openai", "anthropic")


# ---------------------------------------------------------------------------
# Gemini: a fake httpx.Client
# ---------------------------------------------------------------------------


GEMINI_BODY: dict[str, Any] = {
    "candidates": [
        {
            "content": {"parts": [{"text": "hello"}], "role": "model"},
            "finishReason": "STOP",
        }
    ],
    "usageMetadata": {"promptTokenCount": 11, "candidatesTokenCount": 3},
    "modelVersion": "gemini-2.5-flash",
    "responseId": "resp-123",
}


class FakeHttpResponse:
    """The two members GeminiProvider reads off an httpx response."""

    def __init__(self, status_code: int, body: Any) -> None:
        self.status_code = status_code
        self._body = body

    def json(self) -> Any:
        if isinstance(self._body, ValueError):
            raise self._body
        return self._body


class FakeGeminiClient:
    """Records every request so the payload can be asserted on."""

    def __init__(self, *, status_code: int = 200, body: Any = None) -> None:
        self.status_code = status_code
        self.body = GEMINI_BODY if body is None else body
        self.calls: list[dict[str, Any]] = []

    def post(self, url: str, *, json: Any = None, timeout: Any = None) -> FakeHttpResponse:
        self.calls.append({"url": url, "json": json, "timeout": timeout})
        return FakeHttpResponse(self.status_code, self.body)

    def close(self) -> None:
        return None


def make_gemini(
    monkeypatch: pytest.MonkeyPatch, *, status_code: int = 200, body: Any = None
) -> tuple[GeminiProvider, FakeGeminiClient]:
    # max_retries=0 so a retryable status raises on the first response instead of
    # sleeping through a backoff ladder inside a unit test.
    provider = GeminiProvider(api_key=FAKE_KEY, model="gemini-2.5-flash", max_retries=0)
    fake = FakeGeminiClient(status_code=status_code, body=body)
    monkeypatch.setattr(provider, "_client", fake)
    return provider, fake


# ---------------------------------------------------------------------------
# OpenAI-compatible and Anthropic: fake SDK clients
# ---------------------------------------------------------------------------


def openai_response() -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="hello"), finish_reason="stop")],
        usage=SimpleNamespace(prompt_tokens=11, completion_tokens=3),
        model="gpt-test",
        id="resp-123",
    )


def anthropic_response() -> SimpleNamespace:
    return SimpleNamespace(
        content=[SimpleNamespace(text="hello")],
        # The vendor spelling. It must not survive into LLMResponse.
        stop_reason="end_turn",
        usage=SimpleNamespace(input_tokens=11, output_tokens=3),
        model="claude-test",
        id="msg-1",
    )


def fake_openai_client(result: Any) -> SimpleNamespace:
    def create(**kwargs: Any) -> Any:
        if isinstance(result, Exception):
            raise result
        return result

    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


def fake_anthropic_client(result: Any) -> SimpleNamespace:
    def create(**kwargs: Any) -> Any:
        if isinstance(result, Exception):
            raise result
        return result

    return SimpleNamespace(messages=SimpleNamespace(create=create))


def make_openai_compat(
    monkeypatch: pytest.MonkeyPatch, result: Any, *, provider_name: str = "openai"
) -> OpenAICompatProvider:
    pytest.importorskip("openai")
    provider = OpenAICompatProvider(
        provider_name=provider_name,
        api_key=FAKE_KEY,
        model="gpt-test",
        base_url="https://example.invalid/v1",
        max_retries=0,
    )
    monkeypatch.setattr(provider, "_client", fake_openai_client(result))
    return provider


def make_anthropic(monkeypatch: pytest.MonkeyPatch, result: Any) -> AnthropicProvider:
    pytest.importorskip("anthropic")
    provider = AnthropicProvider(api_key=FAKE_KEY, model="claude-test", max_retries=0)
    monkeypatch.setattr(provider, "_client", fake_anthropic_client(result))
    return provider


def happy_provider(name: str, monkeypatch: pytest.MonkeyPatch) -> Any:
    if name == "gemini":
        return make_gemini(monkeypatch)[0]
    if name == "openai":
        return make_openai_compat(monkeypatch, openai_response())
    if name == "anthropic":
        return make_anthropic(monkeypatch, anthropic_response())
    raise AssertionError(f"unknown provider case {name!r}")


def request() -> LLMRequest:
    return LLMRequest(
        messages=[LLMMessage(role="user", content="Who is Indra?")],
        system="You are the synthesis stage.",
        max_output_tokens=256,
    )


# ---------------------------------------------------------------------------
# The contract
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("provider_name", PROVIDER_NAMES)
def test_every_provider_returns_the_same_normalised_response(
    provider_name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = happy_provider(provider_name, monkeypatch)

    response = provider.generate(request())

    assert isinstance(response, LLMResponse)
    assert response.text == "hello"
    assert response.finish_reason == "stop"
    assert response.provider == provider_name
    assert isinstance(response.usage.input_tokens, int)
    assert isinstance(response.usage.output_tokens, int)
    assert response.usage.input_tokens == 11
    assert response.usage.output_tokens == 3
    assert response.latency_ms >= 0
    assert isinstance(response.model, str)
    assert response.model


@pytest.mark.parametrize("provider_name", PROVIDER_NAMES)
def test_provider_identity_and_capabilities_are_declared(
    provider_name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = happy_provider(provider_name, monkeypatch)

    assert provider.name == provider_name
    assert isinstance(provider.model, str)
    assert provider.model
    assert isinstance(provider.capabilities, LLMCapabilities)


def test_vendor_finish_reason_spellings_do_not_survive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Gemini says STOP and Anthropic says end_turn. Both must read as ``stop``."""
    gemini, _ = make_gemini(monkeypatch)
    assert GEMINI_BODY["candidates"][0]["finishReason"] == "STOP"
    assert gemini.generate(request()).finish_reason == "stop"

    raw = anthropic_response()
    assert raw.stop_reason == "end_turn"
    claude = make_anthropic(monkeypatch, raw)
    assert claude.generate(request()).finish_reason == "stop"


# ---------------------------------------------------------------------------
# Truncation: one flag, three vendor spellings
# ---------------------------------------------------------------------------


def test_a_normal_completion_is_not_truncated(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in PROVIDER_NAMES:
        response = happy_provider(name, monkeypatch).generate(request())
        assert response.finish_reason == "stop"
        assert response.generation_truncated is False, name


def test_openai_compatible_length_normalises_to_truncated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The spelling OpenRouter returned for the four capped benchmark answers."""
    raw = openai_response()
    raw.choices[0].finish_reason = "length"
    provider = make_openai_compat(monkeypatch, raw)

    response = provider.generate(request())

    assert response.finish_reason == "length"
    assert response.generation_truncated is True


def test_gemini_max_tokens_normalises_to_truncated(monkeypatch: pytest.MonkeyPatch) -> None:
    body = json_module.loads(json_module.dumps(GEMINI_BODY))
    body["candidates"][0]["finishReason"] = "MAX_TOKENS"
    provider, _ = make_gemini(monkeypatch, body=body)

    response = provider.generate(request())

    assert response.finish_reason == "length"
    assert response.generation_truncated is True


def test_anthropic_max_tokens_normalises_to_truncated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The gap this test exists for.

    Anthropic says ``max_tokens``; the contract says ``length``. The adapter mapped
    ``end_turn`` and left every other spelling alone, so a Claude answer that hit the
    cap arrived carrying a finish reason nothing downstream tested for -- indistinguish-
    able, to the rest of the product, from a finished one.
    """
    raw = anthropic_response()
    raw.stop_reason = "max_tokens"
    provider = make_anthropic(monkeypatch, raw)

    response = provider.generate(request())

    assert response.finish_reason == "length"
    assert response.generation_truncated is True


def test_an_unknown_finish_reason_is_not_reported_as_truncated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A vendor string nobody has seen is an unknown, not a fault and not a cut-off."""
    raw = openai_response()
    raw.choices[0].finish_reason = "some_new_vendor_reason"
    provider = make_openai_compat(monkeypatch, raw)

    response = provider.generate(request())

    assert response.generation_truncated is False


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, "stop"),
        ("", "stop"),
        ("STOP", "stop"),
        ("end_turn", "stop"),
        ("stop_sequence", "stop"),
        ("length", "length"),
        ("LENGTH", "length"),
        ("max_tokens", "length"),
        ("MAX_TOKENS", "length"),
        ("  Max_Tokens  ", "length"),
        ("model_length", "length"),
        ("SAFETY", "content_filter"),
        ("content_filter", "content_filter"),
    ],
)
def test_finish_reason_normalisation_table(raw: str | None, expected: str) -> None:
    assert normalise_finish_reason(raw) == expected


def test_provider_info_is_the_pair_the_response_reports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, _ = make_gemini(monkeypatch)
    response = provider.generate(request())
    assert response.provider_info == {
        "provider": response.provider,
        "model": response.model,
    }


# ---------------------------------------------------------------------------
# Error normalisation
# ---------------------------------------------------------------------------


def failing_provider(name: str, kind: str, monkeypatch: pytest.MonkeyPatch) -> Any:
    if name == "gemini":
        status = {"auth": 401, "rate_limit": 429, "unavailable": 503}[kind]
        return make_gemini(monkeypatch, status_code=status)[0]

    if name == "openai":
        openai = pytest.importorskip("openai")
        exc = _sdk_error(openai, kind)
        return make_openai_compat(monkeypatch, exc)

    anthropic = pytest.importorskip("anthropic")
    return make_anthropic(monkeypatch, _sdk_error(anthropic, kind))


def _sdk_error(sdk: Any, kind: str) -> Exception:
    """A real vendor exception instance, built without a socket."""
    import httpx

    http_request = httpx.Request("POST", "https://example.invalid/v1/messages")
    status = {"auth": 401, "rate_limit": 429, "unavailable": 503}[kind]
    cls = {
        "auth": sdk.AuthenticationError,
        "rate_limit": sdk.RateLimitError,
        "unavailable": sdk.InternalServerError,
    }[kind]
    return cls(
        f"vendor said {status}",
        response=httpx.Response(status, request=http_request),
        body=None,
    )


@pytest.mark.parametrize("provider_name", PROVIDER_NAMES)
@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ("auth", LLMAuthenticationError),
        ("rate_limit", LLMRateLimitError),
        ("unavailable", LLMProviderUnavailableError),
    ],
)
def test_failures_normalise_to_the_same_error_type(
    provider_name: str,
    kind: str,
    expected: type[Exception],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = failing_provider(provider_name, kind, monkeypatch)

    with pytest.raises(expected) as caught:
        provider.generate(request())

    assert caught.value.provider == provider_name
    # Retryability is a property of the normalised error, not of the vendor.
    assert caught.value.retryable is (kind != "auth")


# ---------------------------------------------------------------------------
# Gemini specifics
# ---------------------------------------------------------------------------


def test_thinking_budget_is_disabled_in_the_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Load-bearing, not a tuning knob.

    With reasoning enabled a 2.5-series model spends the whole output budget before the
    first visible token and returns zero parts, so the adapter must switch it off on
    every request rather than relying on a model default.
    """
    provider, fake = make_gemini(monkeypatch)

    provider.generate(request())

    assert len(fake.calls) == 1
    payload = fake.calls[0]["json"]
    assert payload["generationConfig"]["thinkingConfig"]["thinkingBudget"] == 0


def test_max_tokens_with_no_parts_names_the_output_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The real defect found this session: thinking tokens ate the whole budget.

    ``finishReason: MAX_TOKENS`` with no parts is not a truncated answer, it is no answer,
    and "empty response" would send a reader to look at the prompt instead of the budget.
    """
    provider, _ = make_gemini(
        monkeypatch,
        body={
            "candidates": [{"content": {"role": "model"}, "finishReason": "MAX_TOKENS"}],
            "usageMetadata": {"promptTokenCount": 11, "candidatesTokenCount": 0},
        },
    )

    with pytest.raises(LLMResponseError) as caught:
        provider.generate(request())

    assert "output budget" in caught.value.detail
    assert "VEDAGRAPH_LLM_MAX_OUTPUT_TOKENS" in caught.value.detail


def test_prompt_feedback_block_reason_is_a_content_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, _ = make_gemini(monkeypatch, body={"promptFeedback": {"blockReason": "SAFETY"}})

    with pytest.raises(LLMContentBlockedError):
        provider.generate(request())


def test_no_candidates_is_a_response_error_not_an_empty_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, _ = make_gemini(monkeypatch, body={})

    with pytest.raises(LLMResponseError) as caught:
        provider.generate(request())

    assert "no candidates" in caught.value.detail.lower()


def test_safety_finish_reason_is_a_content_block(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, _ = make_gemini(
        monkeypatch,
        body={
            "candidates": [{"content": {"parts": [{"text": "partial"}]}, "finishReason": "SAFETY"}]
        },
    )

    with pytest.raises(LLMContentBlockedError):
        provider.generate(request())


def test_system_message_is_hoisted_into_system_instruction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Gemini carries system text in its own field, so a system *message* must be moved
    rather than dropped -- a dropped one silently removes the binding rules."""
    provider, fake = make_gemini(monkeypatch)

    provider.generate(
        LLMRequest(
            messages=[
                LLMMessage(role="system", content="RULE-SENTINEL"),
                LLMMessage(role="user", content="Who is Indra?"),
            ]
        )
    )

    payload = fake.calls[0]["json"]
    rendered = [part["text"] for part in payload["systemInstruction"]["parts"]]
    assert "RULE-SENTINEL" in rendered
    assert [c["role"] for c in payload["contents"]] == ["user"]


# ---------------------------------------------------------------------------
# Rate-limit backoff: Retry-After over guessing
# ---------------------------------------------------------------------------


class _Headers(dict[str, str]):
    def get(self, key: str, default: str | None = None) -> str | None:  # type: ignore[override]
        return dict.get(self, key, default)


class _Response:
    def __init__(self, headers: dict[str, str]) -> None:
        self.headers = _Headers(headers)


class _HeaderError(Exception):
    def __init__(self, headers: dict[str, str]) -> None:
        super().__init__("rate limited")
        self.response = _Response(headers)


@pytest.mark.parametrize(
    ("headers", "expected"),
    [
        ({"retry-after": "18"}, 18.0),
        ({"Retry-After": "7.5s"}, 7.5),
        ({"x-ratelimit-reset-tokens": "22s"}, 22.0),
        ({}, None),
        ({"retry-after": "not-a-number"}, None),
    ],
)
def test_retry_after_is_read_defensively(headers: dict[str, str], expected: float | None) -> None:
    from vedagraph.llm.providers.openai_compat import _retry_after_seconds

    assert _retry_after_seconds(_HeaderError(headers)) == expected


def test_retry_after_is_preferred_over_exponential_backoff() -> None:
    """A per-minute token quota does not clear in 1+2+4 seconds.

    Exponential backoff from one second is right for a transient 5xx and useless against
    a TPM ceiling: the window has not moved, all three retries fail, and the caller is
    told the backend is unreachable when it was merely busy. One benchmark question
    failed on every run at the same position for exactly this reason.
    """
    from vedagraph.llm.errors import LLMRateLimitError
    from vedagraph.llm.providers.openai_compat import OpenAICompatProvider

    hinted = LLMRateLimitError(provider="groq", retry_after_seconds=18)
    assert OpenAICompatProvider._backoff_seconds(hinted, 0) > 7.0

    blind = LLMRateLimitError(provider="groq")
    assert OpenAICompatProvider._backoff_seconds(blind, 2) == 4.0


def test_a_long_retry_after_is_capped_rather_than_honoured() -> None:
    """A provider asking for 15 minutes is not something to hold a request open for."""
    from vedagraph.llm.errors import LLMRateLimitError
    from vedagraph.llm.providers.openai_compat import (
        _MAX_BACKOFF_SECONDS,
        OpenAICompatProvider,
    )

    huge = LLMRateLimitError(provider="groq", retry_after_seconds=900)

    assert OpenAICompatProvider._backoff_seconds(huge, 0) == _MAX_BACKOFF_SECONDS


# ---------------------------------------------------------------------------
# Transient faults reach the retry ladder; daily ones do not
# ---------------------------------------------------------------------------


def _sequenced_openai(
    monkeypatch: pytest.MonkeyPatch, results: list[Any], *, max_retries: int = 3
) -> tuple[OpenAICompatProvider, list[int]]:
    """An adapter whose client returns each result in turn. Sleeps are not slept."""
    pytest.importorskip("openai")
    provider = OpenAICompatProvider(
        provider_name="openrouter",
        api_key=FAKE_KEY,
        model="free-model",
        base_url="https://example.invalid/v1",
        max_retries=max_retries,
    )
    calls = {"n": 0}
    slept: list[int] = []

    def create(**kwargs: Any) -> Any:
        result = results[min(calls["n"], len(results) - 1)]
        calls["n"] += 1
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(
        provider,
        "_client",
        SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))),
    )
    monkeypatch.setattr(
        "vedagraph.llm.providers.openai_compat.time.sleep", lambda s: slept.append(s)
    )
    provider._calls = calls  # type: ignore[attr-defined]
    return provider, slept


def _empty_200() -> SimpleNamespace:
    """A 200 carrying no choice: the gateway accepted, the upstream produced nothing."""
    return SimpleNamespace(choices=[], usage=None, model="free-model", id="resp-empty")


def test_an_empty_200_is_retried_rather_than_ending_the_caller(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The defect this file exists to pin: the ladder was promised and never ran.

    ``generate`` raises ``LLMProviderUnavailableError`` on an empty ``choices`` *so that
    the retry ladder answers it* -- the branch says so in a comment. But the handler
    below it caught every already-normalised ``LLMError`` and re-raised unconditionally,
    so the blip got zero of its three attempts. A free-tier gateway returning one empty
    200 ended a 60-question benchmark batch on the spot, twice, while the very next call
    to the same model succeeded.
    """
    provider, slept = _sequenced_openai(monkeypatch, [_empty_200(), openai_response()])

    response = provider.generate(request())

    assert response.text == "hello"
    assert provider._calls["n"] == 2, "the empty 200 must cost one retry, not the batch"
    assert slept == [1.0], "and it must back off before asking again"


def test_an_unavailable_provider_still_fails_once_the_ladder_is_spent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retrying is bounded. Four empty 200s with max_retries=3 is still a failure."""
    provider, slept = _sequenced_openai(monkeypatch, [_empty_200()])

    with pytest.raises(LLMProviderUnavailableError):
        provider.generate(request())

    assert provider._calls["n"] == 4, "one attempt plus three retries"
    assert slept == [1.0, 2.0, 4.0]


def test_a_content_filter_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    """Making normalised errors retryable must not make *every* normalised error retry.

    A safety filter returns the same verdict however many times it is asked, and each
    ask is metered.
    """
    blocked = SimpleNamespace(
        choices=[
            SimpleNamespace(message=SimpleNamespace(content=""), finish_reason="content_filter")
        ],
        usage=None,
        model="free-model",
        id="resp-blocked",
    )
    provider, slept = _sequenced_openai(monkeypatch, [blocked])

    with pytest.raises(LLMContentBlockedError):
        provider.generate(request())

    assert provider._calls["n"] == 1
    assert slept == []


def test_a_daily_quota_is_marked_and_never_waited_out(monkeypatch: pytest.MonkeyPatch) -> None:
    """A per-day ceiling must reach the caller as non-retryable.

    A batch runner that sleeps five minutes and asks again spends the very allowance it
    is waiting for. The period is legible only in the provider's prose, so the adapter
    that read it records the finding on the error rather than leaving each caller to
    re-derive it.
    """
    import httpx

    sdk = pytest.importorskip("openai")
    daily = sdk.RateLimitError(
        "Rate limit reached on requests per day (RPD): Limit 50, Used 50",
        response=httpx.Response(
            429, request=httpx.Request("POST", "https://example.invalid/v1/chat/completions")
        ),
        body=None,
    )
    provider, slept = _sequenced_openai(monkeypatch, [daily])

    with pytest.raises(LLMRateLimitError) as caught:
        provider.generate(request())

    assert caught.value.daily_exhausted is True
    assert caught.value.retryable is False
    assert provider._calls["n"] == 1, "a daily allowance is not probed three more times"
    assert slept == []


def test_a_per_minute_quota_stays_retryable(monkeypatch: pytest.MonkeyPatch) -> None:
    """The distinction must not swallow the limit that *does* clear by waiting."""
    import httpx

    sdk = pytest.importorskip("openai")
    per_minute = sdk.RateLimitError(
        "Rate limit reached on tokens per minute (TPM): Limit 6000",
        response=httpx.Response(
            429, request=httpx.Request("POST", "https://example.invalid/v1/chat/completions")
        ),
        body=None,
    )
    provider, _ = _sequenced_openai(monkeypatch, [per_minute], max_retries=0)

    with pytest.raises(LLMRateLimitError) as caught:
        provider.generate(request())

    assert caught.value.daily_exhausted is False
    assert caught.value.retryable is True
