"""Move to the next authorized credential when, and only when, the day's allowance is gone.

WHAT ROTATES AND WHAT DOES NOT
==============================

Exactly one condition rotates: :class:`LLMRateLimitError` carrying ``daily_exhausted``.
That flag is set by the adapter, from the provider's own prose -- Groq writes ``tokens per
day (TPD)``, OpenAI writes ``requests per day (RPD)`` -- and the adapter is conservative
about it: a 429 that does not name a day is treated as a momentary spike and stays
retryable, because misreading a transient limit as a terminal one ends a run that would
have recovered. This class inherits that judgement rather than re-deriving it, so there is
one definition of "the allowance is over" in the repository.

Everything else is an error and stays one. A 401, a 403, a malformed request, an unknown
model, a 5xx, a timeout, a content filter: none of them is fixed by billing someone else,
and rotating on any of them would burn a second account on a fault the first one reported
honestly. A per-minute rate limit is left to the adapter's existing backoff, which is the
right response to a window that refills.

WHAT THIS MUST NOT CHANGE
=========================

``name`` and ``model`` delegate to the first provider and are identical across slots, so
the benchmark's ``RunIdentity`` -- benchmark version, question-set digest, provider, model,
code commit, config hash -- is unmoved by a rotation. Two batches of one run served by two
accounts are the same run, and must remain resumable as one.

WHEN EVERY SLOT IS GONE
=======================

The last daily-quota error is re-raised, still marked non-retryable, so the benchmark's
existing ``_waiting_can_help`` sees a fault waiting cannot fix and stops cleanly with every
answered question already checkpointed. There is no new stop path to get wrong.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Final

from vedagraph.llm.base import LLMProvider, LLMRequest, LLMResponse
from vedagraph.llm.errors import LLMRateLimitError

logger: Final = logging.getLogger(__name__)


def is_terminal_quota(error: BaseException) -> bool:
    """Whether this fault is the provider saying the allowance is spent for the period.

    The single definition of "rotate". Deliberately narrow: only a rate-limit error the
    adapter positively classified as a daily/period exhaustion qualifies. Anything the
    adapter left retryable is a window that refills and is not this.
    """
    return isinstance(error, LLMRateLimitError) and error.daily_exhausted


class FailoverProvider(LLMProvider):
    """Try each configured credential in turn, once, on terminal quota exhaustion."""

    def __init__(self, providers: list[LLMProvider]) -> None:
        if not providers:
            raise ValueError("FailoverProvider needs at least one provider")
        self._providers = providers
        self._active = 0
        #: Slots whose allowance the provider has reported spent, in this process.
        self._exhausted: set[int] = set()

    # -- identity: constant across slots, which is the whole contract ------------------

    @property
    def name(self) -> str:
        return self._providers[0].name

    @property
    def model(self) -> str:
        return self._providers[0].model

    # -- slot reporting: counts only, never a value -----------------------------------

    @property
    def active_slot(self) -> int:
        """1-based, for display, clamped to a slot that exists.

        Once every credential has reported its allowance spent, ``_active`` runs one past
        the end -- which is what makes the loop terminate. Reporting that index would
        print "slot 4 active" over three configured credentials, so the last real slot is
        shown instead and ``all_exhausted`` carries the fact.
        """
        return min(self._active, len(self._providers) - 1) + 1

    @property
    def slot_count(self) -> int:
        return len(self._providers)

    @property
    def remaining_slots(self) -> int:
        return max(len(self._providers) - self._active - 1, 0)

    @property
    def all_exhausted(self) -> bool:
        return self._active >= len(self._providers)

    def status(self) -> dict[str, int | str | bool]:
        return {
            "provider": self.name,
            "configured_credentials": self.slot_count,
            "active_slot": self.active_slot,
            "remaining_unused_slots": self.remaining_slots,
            "slots_reported_exhausted": len(self._exhausted),
            "all_credentials_exhausted": self.all_exhausted,
        }

    # -- the loop ---------------------------------------------------------------------

    def generate(self, request: LLMRequest) -> LLMResponse:
        last: LLMRateLimitError | None = None
        while self._active < len(self._providers):
            try:
                return self._providers[self._active].generate(request)
            except LLMRateLimitError as error:
                if not is_terminal_quota(error):
                    raise
                last = error
                self._exhausted.add(self._active)
                self._active += 1
                if self._active < len(self._providers):
                    # Names no credential and no value: the slot number is an index into
                    # the owner's own configuration and identifies nothing by itself.
                    logger.warning(
                        "credential slot %d of %d reported its allowance exhausted; "
                        "continuing on slot %d",
                        self._active,
                        len(self._providers),
                        self._active + 1,
                    )
        # Every slot has reported the same terminal state. Re-raise the last one rather
        # than inventing a new error type: the benchmark already stops correctly on a
        # non-retryable fault, and a new one would be a second stop path to keep right.
        assert last is not None  # the loop only exits here via the rotate branch
        raise last

    def stream(self, request: LLMRequest) -> Iterator[str]:
        """Streaming stays on the active slot.

        A rotation mid-stream would have to replay the prompt and re-emit tokens the
        caller has already consumed. The benchmark does not stream, and a live Ask call
        that hits a daily quota should report it rather than silently restart on another
        account.
        """
        return self._providers[self._active].stream(request)
