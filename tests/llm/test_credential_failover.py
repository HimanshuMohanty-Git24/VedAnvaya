"""Multi-credential failover: what rotates, what must not, and what a rotation may change.

The benchmark is 60 questions against a free tier that will not serve them in one day. The
owner has more than one account they are entitled to use. That is worth exactly one
behaviour -- move to the next credential when the provider says the allowance is spent --
and it is worth a lot of tests, because every other reason to rotate is a way to burn a
second account on a fault the first one reported correctly.

The sentinels here are unmistakable. If an assertion about leakage fails, the string in the
output *is* the credential.
"""

from __future__ import annotations

import json
import logging
import pathlib
from collections.abc import Iterator
from typing import Any

import pytest
from pydantic import SecretStr

from vedagraph.llm import redaction
from vedagraph.llm.base import LLMMessage, LLMProvider, LLMRequest, LLMResponse, LLMUsage
from vedagraph.llm.config import LLMSettings
from vedagraph.llm.credentials import load_credential_slots
from vedagraph.llm.errors import (
    LLMAuthenticationError,
    LLMError,
    LLMProviderUnavailableError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
)
from vedagraph.llm.factory import credential_slots, get_llm_provider
from vedagraph.llm.failover import FailoverProvider, is_terminal_quota

KEY_1 = "sk-SLOT1-must-never-appear-1a2b3c"
KEY_2 = "sk-SLOT2-must-never-appear-4d5e6f"
KEY_3 = "sk-SLOT3-must-never-appear-7g8h9i"
ALL_KEYS = (KEY_1, KEY_2, KEY_3)


@pytest.fixture(autouse=True)
def _isolate_redaction() -> Iterator[None]:
    """One case's registered secrets must not survive into the next."""
    redaction.clear_secrets()
    yield
    redaction.clear_secrets()


@pytest.fixture(autouse=True)
def _no_ambient_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """The developer's own .env and shell must not decide what these tests measure."""
    prefixes = ("VEDAGRAPH_LLM", "OPENROUTER", "OPENAI", "GEMINI", "GOOGLE")
    for prefix in (*prefixes, "ANTHROPIC", "GROQ", "XAI"):
        monkeypatch.delenv(f"{prefix}_API_KEY", raising=False)
        monkeypatch.delenv(f"{prefix}_API_KEYS", raising=False)
        for n in range(2, 17):
            monkeypatch.delenv(f"{prefix}_API_KEY_{n}", raising=False)


def settings(**overrides: Any) -> LLMSettings:
    base: dict[str, Any] = {
        "vedagraph_llm_provider": "openrouter",
        "vedagraph_llm_model": "test/model-v1",
        "vedagraph_llm_api_key": None,
        "vedagraph_llm_base_url": "https://example.invalid/v1",
        "google_api_key": None,
        "gemini_api_key": None,
        "openai_api_key": None,
        "anthropic_api_key": None,
    }
    base.update(overrides)
    return LLMSettings(_env_file=None, **base)


def request() -> LLMRequest:
    return LLMRequest(messages=[LLMMessage(role="user", content="Who is Indra?")])


class ScriptedProvider(LLMProvider):
    """One credential's adapter, whose next outcome is scripted per call."""

    def __init__(self, label: str, outcomes: list[BaseException | str]) -> None:
        self.label = label
        self._outcomes = list(outcomes)
        self.calls = 0

    @property
    def name(self) -> str:
        return "openrouter"

    @property
    def model(self) -> str:
        return "test/model-v1"

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.calls += 1
        outcome = self._outcomes.pop(0) if self._outcomes else f"{self.label}-ok"
        if isinstance(outcome, BaseException):
            raise outcome
        return LLMResponse(
            text=outcome,
            finish_reason="stop",
            provider=self.name,
            model=self.model,
            usage=LLMUsage(input_tokens=1, output_tokens=1),
        )

    def stream(self, request: LLMRequest) -> Iterator[str]:  # pragma: no cover - unused
        yield "x"


def daily_quota() -> LLMRateLimitError:
    return LLMRateLimitError(provider="openrouter", daily_exhausted=True)


def minute_quota() -> LLMRateLimitError:
    return LLMRateLimitError(provider="openrouter", retry_after_seconds=30.0)


# ---------------------------------------------------------------------------
# Enumerating slots
# ---------------------------------------------------------------------------


def test_numbered_environment_keys_become_ordered_slots(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY_1)
    monkeypatch.setenv("OPENROUTER_API_KEY_2", KEY_2)
    monkeypatch.setenv("OPENROUTER_API_KEY_3", KEY_3)

    slots = load_credential_slots("openrouter")

    assert len(slots) == 3
    assert [slots.value(i) for i in range(3)] == [KEY_1, KEY_2, KEY_3]
    assert slots.sources == ("OPENROUTER_API_KEY", "OPENROUTER_API_KEY_2", "OPENROUTER_API_KEY_3")


def test_the_plural_form_is_split_on_commas_and_whitespace(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEYS", f"{KEY_1}, {KEY_2}\n{KEY_3}")

    slots = load_credential_slots("openrouter")

    assert [slots.value(i) for i in range(3)] == [KEY_1, KEY_2, KEY_3]


def test_the_same_key_configured_twice_is_one_slot(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reporting it as two would promise a fallback that does not exist."""
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY_1)
    monkeypatch.setenv("OPENROUTER_API_KEY_2", KEY_1)
    monkeypatch.setenv("OPENAI_API_KEY", KEY_1)

    assert len(load_credential_slots("openrouter")) == 1


def test_no_configured_key_is_zero_slots() -> None:
    assert len(load_credential_slots("openrouter")) == 0
    assert not load_credential_slots("openrouter")


def test_a_key_given_to_settings_is_slot_one(monkeypatch: pytest.MonkeyPatch) -> None:
    """A .env key reaches the settings model, not os.environ. It is still slot 1."""
    monkeypatch.setenv("OPENROUTER_API_KEY_2", KEY_2)

    slots = credential_slots(settings(vedagraph_llm_api_key=SecretStr(KEY_1)))

    assert [slots.value(i) for i in range(2)] == [KEY_1, KEY_2]


def test_describe_reports_counts_and_names_and_no_value(monkeypatch: pytest.MonkeyPatch) -> None:
    """Not even a prefix: four characters identifies a key against a candidate list."""
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY_1)
    monkeypatch.setenv("OPENROUTER_API_KEY_2", KEY_2)

    described = load_credential_slots("openrouter").describe(active=0)

    assert described["configured_credentials"] == 2
    assert described["active_slot"] == 1
    assert described["remaining_unused_slots"] == 1
    rendered = json.dumps(described)
    for key in ALL_KEYS:
        assert key not in rendered
        assert key[:6] not in rendered
        assert key[-6:] not in rendered


def test_slots_repr_and_str_hide_every_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY_1)
    monkeypatch.setenv("OPENROUTER_API_KEY_2", KEY_2)
    slots = load_credential_slots("openrouter")

    for rendered in (repr(slots), str(slots)):
        assert all(key not in rendered for key in ALL_KEYS)


# ---------------------------------------------------------------------------
# What rotates
# ---------------------------------------------------------------------------


def test_a_terminal_daily_quota_rotates_to_slot_two() -> None:
    first = ScriptedProvider("one", [daily_quota()])
    second = ScriptedProvider("two", [])
    failover = FailoverProvider([first, second])

    assert failover.generate(request()).text == "two-ok"
    assert failover.active_slot == 2
    assert (first.calls, second.calls) == (1, 1), "the same question, once under the next key"


@pytest.mark.parametrize(
    "fault",
    [
        LLMAuthenticationError(provider="openrouter"),
        LLMResponseError(provider="openrouter", detail="model not found"),
        LLMTimeoutError(provider="openrouter", timeout_seconds=60.0),
        LLMProviderUnavailableError(provider="openrouter"),
        minute_quota(),
    ],
    ids=["401", "model-not-found", "timeout", "5xx", "per-minute-429"],
)
def test_nothing_except_a_terminal_quota_rotates(fault: LLMError) -> None:
    """Billing a second account does not fix a bad key, a bad model or a blip."""
    first = ScriptedProvider("one", [fault])
    second = ScriptedProvider("two", [])
    failover = FailoverProvider([first, second])

    with pytest.raises(type(fault)):
        failover.generate(request())

    assert failover.active_slot == 1
    assert second.calls == 0, "a second account was spent on a fault the first reported"


def test_a_per_minute_limit_keeps_its_retryable_flag() -> None:
    """The existing backoff ladder must still see a window that refills as retryable."""
    assert minute_quota().retryable is True
    assert is_terminal_quota(minute_quota()) is False
    assert daily_quota().retryable is False
    assert is_terminal_quota(daily_quota()) is True


def test_exhausting_every_slot_stops_cleanly_and_not_retryably() -> None:
    providers = [ScriptedProvider(str(n), [daily_quota()]) for n in range(3)]
    failover = FailoverProvider(providers)

    with pytest.raises(LLMRateLimitError) as caught:
        failover.generate(request())

    assert caught.value.daily_exhausted is True
    assert caught.value.retryable is False, "the benchmark would sleep on a spent allowance"
    assert [p.calls for p in providers] == [1, 1, 1], "each credential was tried exactly once"
    assert failover.remaining_slots == 0
    assert failover.all_exhausted is True
    # Never a slot number that does not exist: three credentials cannot report a fourth.
    assert failover.active_slot == 3
    assert failover.status()["slots_reported_exhausted"] == 3


def test_a_rotated_run_stays_on_the_new_slot() -> None:
    """The spent credential is not retried on the next question."""
    first = ScriptedProvider("one", [daily_quota()])
    second = ScriptedProvider("two", [])
    failover = FailoverProvider([first, second])

    failover.generate(request())
    failover.generate(request())

    assert first.calls == 1, "a credential whose allowance is spent was asked again"
    assert second.calls == 2


def test_rotation_does_not_change_the_reported_provider_or_model() -> None:
    """The two fields the benchmark's run identity reads off the provider."""
    first = ScriptedProvider("one", [daily_quota()])
    failover = FailoverProvider([first, ScriptedProvider("two", [])])
    before = (failover.name, failover.model)

    failover.generate(request())

    assert (failover.name, failover.model) == before


def test_status_reports_slots_and_never_a_credential() -> None:
    failover = FailoverProvider(
        [ScriptedProvider("one", [daily_quota()]), ScriptedProvider("two", [])]
    )
    failover.generate(request())
    status = failover.status()

    assert status["configured_credentials"] == 2
    assert status["active_slot"] == 2
    assert status["remaining_unused_slots"] == 0
    assert status["slots_reported_exhausted"] == 1
    assert all(key not in json.dumps(status) for key in ALL_KEYS)


def test_the_factory_wraps_only_when_more_than_one_credential_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A one-key repository gets exactly the object it always got."""
    pytest.importorskip("openai", reason="openai SDK not installed")
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY_1)
    assert not isinstance(get_llm_provider(settings()), FailoverProvider)

    monkeypatch.setenv("OPENROUTER_API_KEY_2", KEY_2)
    built = get_llm_provider(settings())
    assert isinstance(built, FailoverProvider)
    assert built.slot_count == 2
    assert built.name == "openrouter" and built.model == "test/model-v1"


# ---------------------------------------------------------------------------
# Redaction
# ---------------------------------------------------------------------------


def test_a_vendor_error_quoting_the_key_is_scrubbed() -> None:
    """The path the adapters cannot guard: a string they did not construct."""
    redaction.register_secrets([KEY_1])

    error = LLMError(f"401 from upstream: key {KEY_1} is not valid", provider="openrouter")

    assert KEY_1 not in str(error)
    assert KEY_1 not in error.detail
    assert KEY_1 not in repr(error)
    assert redaction.REDACTED in error.detail


def test_every_configured_slot_is_scrubbed_not_only_the_active_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Failover holds several credentials at once, which is when this matters most."""
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY_1)
    monkeypatch.setenv("OPENROUTER_API_KEY_2", KEY_2)
    monkeypatch.setenv("OPENROUTER_API_KEY_3", KEY_3)
    credential_slots(settings())

    error = LLMError(f"upstream said {KEY_1} {KEY_2} {KEY_3}", provider="openrouter")

    assert all(key not in error.detail for key in ALL_KEYS)


def test_redaction_leaves_ordinary_diagnostics_intact() -> None:
    redaction.register_secrets([KEY_1])

    error = LLMError("Rate limit reached for provider 'openrouter'.", provider="openrouter")

    assert error.detail == "Rate limit reached for provider 'openrouter'."


def test_a_short_value_is_not_treated_as_a_secret() -> None:
    """Redacting a one-character 'key' would destroy the message and protect nothing."""
    redaction.register_secrets(["ab"])

    assert redaction.registered_count() == 0
    assert redaction.scrub("a table of abbreviations") == "a table of abbreviations"


def test_a_key_that_is_a_prefix_of_another_leaves_no_tail() -> None:
    redaction.register_secrets([KEY_1, KEY_1 + "-extended"])

    scrubbed = redaction.scrub(f"saw {KEY_1}-extended here")

    assert "extended" not in scrubbed
    assert KEY_1 not in scrubbed


def test_rotation_logs_a_slot_number_and_no_credential(
    caplog: pytest.LogCaptureFixture,
) -> None:
    redaction.register_secrets(list(ALL_KEYS))
    failover = FailoverProvider(
        [ScriptedProvider("one", [daily_quota()]), ScriptedProvider("two", [])]
    )

    with caplog.at_level(logging.DEBUG):
        failover.generate(request())

    assert caplog.records, "a rotation with no notice at all is its own problem"
    for record in caplog.records:
        formatted = logging.Formatter().format(record)
        assert all(key not in formatted for key in ALL_KEYS)
    assert "slot 2" in caplog.text


def test_no_credential_reaches_a_written_artifact(tmp_path: pathlib.Path) -> None:
    """Whatever a slot report is serialised into, it carries counts and nothing else."""
    failover = FailoverProvider(
        [ScriptedProvider("one", [daily_quota()]), ScriptedProvider("two", [])]
    )
    failover.generate(request())

    artifact = tmp_path / "receipt.json"
    artifact.write_text(json.dumps(failover.status()), encoding="utf-8")
    written = artifact.read_text(encoding="utf-8")

    assert all(key not in written for key in ALL_KEYS)
    assert "api_key" not in written and "secret" not in written.lower()
