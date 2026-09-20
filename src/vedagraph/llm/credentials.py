"""Multiple authorized credentials for one provider, enumerated without ever exposing one.

The 60-question Ask benchmark cannot finish inside one free-tier daily allowance. It is
already resumable, so the owner can come back tomorrow; this module is what lets them come
back *immediately* on a second account they are entitled to use.

WHAT A SLOT IS, AND WHAT IT IS NOT
==================================

A slot is one credential the owner has configured, in a fixed order. Slot 1 is whatever the
existing single-key configuration resolves to, so a repository with one key behaves exactly
as it did. Slots 2..n come from numbered suffixes or from a separator-joined list.

A slot is **not** a different provider, a different model or a different configuration.
Rotating one changes who is billed and nothing else, which is the property the benchmark's
run identity depends on: ``RunIdentity`` hashes benchmark version, question-set digest,
provider, model, code commit and generation config, and no credential appears in any of
them. Two batches of one run served by two different accounts are the same run, and this
module must never make that untrue.

THE VALUE NEVER LEAVES
======================

Slots are held as :class:`~pydantic.SecretStr`. ``describe()`` returns counts only -- no
prefix, no suffix, no length, no masked rendering. A four-character prefix is enough to
identify a key in a leaked log against a list of candidates, and a length distinguishes
vendors; neither is reported. :mod:`vedagraph.llm.redaction` scrubs any configured value
out of error text, which covers the case this module cannot: a vendor echoing the rejected
key back in a 401 body.

ENVIRONMENT
===========

Read directly from ``os.environ`` rather than through :class:`LLMSettings`, because a
pydantic-settings field would have to be declared per slot and the count is open-ended.
For provider ``openrouter`` the names checked, in order, are::

    VEDAGRAPH_LLM_API_KEY        OPENROUTER_API_KEY        (slot 1)
    VEDAGRAPH_LLM_API_KEY_2      OPENROUTER_API_KEY_2      (slot 2)
    VEDAGRAPH_LLM_API_KEY_3      OPENROUTER_API_KEY_3      (slot 3)
    ...
    VEDAGRAPH_LLM_API_KEYS       OPENROUTER_API_KEYS       (any number, separated)

Duplicates are collapsed. The same key configured twice is one slot, not two, because
reporting it as two would tell the owner they have a fallback they do not have.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Final

from pydantic import SecretStr

#: How far the numbered scan goes. Past this the owner wants the list form.
_MAX_NUMBERED_SLOTS: Final = 16

#: Separators accepted inside the plural form. Commas, semicolons and whitespace.
_LIST_SEPARATORS: Final = re.compile(r"[,;\s]+")

#: Provider name to the environment prefix its keys use, matching the fallbacks
#: :meth:`LLMSettings.resolved_api_key` already honours, plus OPENROUTER which the
#: settings model reached only through OPENAI_API_KEY.
_PROVIDER_PREFIXES: Final[dict[str, tuple[str, ...]]] = {
    "gemini": ("GEMINI", "GOOGLE"),
    "openai": ("OPENAI",),
    "anthropic": ("ANTHROPIC",),
    "groq": ("GROQ", "OPENAI"),
    "openrouter": ("OPENROUTER", "OPENAI"),
    "xai": ("XAI", "OPENAI"),
    "openai_compatible": ("OPENAI",),
}


def _env(name: str, environ: dict[str, str]) -> str:
    return (environ.get(name) or "").strip()


def _prefixes_for(provider: str) -> tuple[str, ...]:
    return ("VEDAGRAPH_LLM", *_PROVIDER_PREFIXES.get(provider.lower().strip(), ("OPENAI",)))


@dataclass(frozen=True)
class CredentialSlots:
    """Every configured credential for one provider, in the order they will be used."""

    provider: str
    _values: tuple[SecretStr, ...]
    #: Which environment name supplied each slot, for a diagnostic that names no value.
    sources: tuple[str, ...]

    def __len__(self) -> int:
        return len(self._values)

    def __bool__(self) -> bool:
        return bool(self._values)

    def value(self, index: int) -> str:
        """The credential for slot ``index`` (0-based). The only way to read one."""
        return self._values[index].get_secret_value()

    def raw_values(self) -> tuple[str, ...]:
        """Every configured value. Used by redaction to know what to scrub."""
        return tuple(v.get_secret_value() for v in self._values)

    def with_first(self, value: str, source: str) -> CredentialSlots:
        """A copy with ``value`` as slot 1, deduplicated against the existing slots.

        For a key handed straight to :class:`LLMSettings` rather than set in the
        environment -- which is how every test in ``tests/llm`` configures one, and how a
        ``.env`` file reaches the settings model.
        """
        if not value or value in self.raw_values():
            return self
        return CredentialSlots(
            provider=self.provider,
            _values=(SecretStr(value), *self._values),
            sources=(source, *self.sources),
        )

    def describe(self, active: int = 0) -> dict[str, Any]:
        """Counts and environment *names*. Never a value, a prefix, or a length."""
        return {
            "provider": self.provider,
            "configured_credentials": len(self._values),
            "active_slot": (active + 1) if self._values else 0,
            "remaining_unused_slots": max(len(self._values) - active - 1, 0),
            "configured_from": list(self.sources),
        }

    def __repr__(self) -> str:  # pragma: no cover - trivial, but it must not print values
        return f"CredentialSlots(provider={self.provider!r}, slots={len(self._values)})"

    __str__ = __repr__


def load_credential_slots(
    provider: str, environ: dict[str, str] | None = None
) -> CredentialSlots:
    """Enumerate configured credentials for ``provider``, deduplicated, in use order."""
    env = dict(os.environ if environ is None else environ)
    prefixes = _prefixes_for(provider)

    found: list[tuple[str, str]] = []  # (value, source env name)

    def offer(value: str, source: str) -> None:
        if value:
            found.append((value, source))

    for prefix in prefixes:
        offer(_env(f"{prefix}_API_KEY", env), f"{prefix}_API_KEY")
    for slot in range(2, _MAX_NUMBERED_SLOTS + 1):
        for prefix in prefixes:
            offer(_env(f"{prefix}_API_KEY_{slot}", env), f"{prefix}_API_KEY_{slot}")
    for prefix in prefixes:
        joined = _env(f"{prefix}_API_KEYS", env)
        for piece in _LIST_SEPARATORS.split(joined):
            offer(piece.strip(), f"{prefix}_API_KEYS")

    values: list[SecretStr] = []
    sources: list[str] = []
    seen: set[str] = set()
    for value, source in found:
        if value in seen:
            continue
        seen.add(value)
        values.append(SecretStr(value))
        sources.append(source)

    return CredentialSlots(
        provider=provider.lower().strip(), _values=tuple(values), sources=tuple(sources)
    )
