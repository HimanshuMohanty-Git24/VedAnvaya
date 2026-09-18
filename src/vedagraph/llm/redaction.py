"""Scrub configured credentials out of any string that might be shown, logged or stored.

The existing adapters are careful: they map on HTTP status and never quote a response
body, which is why ``tests/llm/test_secret_safety.py`` can push a sentinel through every
failure mode and find it nowhere. This module covers the case that care cannot reach --
a value arriving from somewhere the adapter did not construct.

Two such paths exist now that a run may hold several credentials. An SDK that formats the
request into an exception, and a provider that echoes the rejected key in a 401 body, both
produce a string the adapter did not write. And the failover path deliberately raises the
*last* provider error after trying every slot, which is exactly the moment several
credentials are in memory at once.

So the scrub is applied at :class:`~vedagraph.llm.errors.LLMError` construction: one choke
point every normalised error already passes through, which is cheaper to verify than a
list of surfaces that must each remember.

Longest first, so a key that is a prefix of another does not leave the tail of the longer
one behind. Values shorter than :data:`_MIN_SECRET_LENGTH` are ignored: a one-character
"key" would redact every occurrence of that character in the message, which destroys the
diagnostic without protecting anything.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Final

REDACTED: Final = "***REDACTED***"

#: Below this a configured value is treated as unusable rather than as a secret. Real keys
#: from every provider in this repository are far longer; a short one is a misconfiguration.
_MIN_SECRET_LENGTH: Final = 8

#: Values to scrub, set by the credential layer. A module-level register rather than a
#: parameter because the call site that matters -- ``LLMError.__init__`` -- has no access
#: to settings and must not grow one.
_REGISTERED: set[str] = set()


def register_secrets(values: str | Iterable[str]) -> None:
    """Add credential values to the scrub set. Idempotent; never logs what it received."""
    items: Iterable[str] = (values,) if isinstance(values, str) else values
    for value in items:
        text = str(value or "").strip()
        if len(text) >= _MIN_SECRET_LENGTH:
            _REGISTERED.add(text)


def clear_secrets() -> None:
    """Forget every registered value. For tests, so one case cannot bleed into the next."""
    _REGISTERED.clear()


def registered_count() -> int:
    """How many values would be scrubbed. A count, never the values."""
    return len(_REGISTERED)


def scrub(text: str) -> str:
    """Replace every registered credential in ``text`` with :data:`REDACTED`."""
    if not _REGISTERED or not text:
        return text
    for secret in sorted(_REGISTERED, key=len, reverse=True):
        if secret in text:
            text = text.replace(secret, REDACTED)
    return text
