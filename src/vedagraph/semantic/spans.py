"""Boundary-safe anchoring of evidence into a pinned translation record.

An evidence span is a claim that a specific stretch of a specific translation supports a
specific assertion. A substring match is not that claim: ``man`` occurs inside
``manifested``, ``many``, ``Pavamana``, ``woman`` and ``Aryaman``, and a span that lands
in one of those has the shape of evidence without the substance. The readiness audit
found fourteen such anchors in the 508 pilot, all of them structurally valid and all of
them pointing at the wrong characters.

Two rules close that hole, and nothing here interprets meaning:

**Boundaries.** When an anchor begins or ends with a word character the corresponding
edge of the match must not sit inside a word. Word-ness is Unicode-aware and includes
combining marks, so a Devanagari matra does not silently end a word.

**Offsets belong to one string.** Matching happens against the translation exactly as
stored. Folding the text and reusing the folded offsets is how the original defect was
produced, because folding is not length-preserving.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


class AmbiguousAnchorError(ValueError):
    """The anchor occurs more than once and no occurrence was chosen."""


class MissingAnchorError(ValueError):
    """The anchor does not occur in the text as a boundary-safe match."""


@dataclass(frozen=True)
class Anchor:
    """One boundary-safe occurrence: half-open offsets and the exact source text."""

    start: int
    end: int
    text: str


def is_word_char(char: str) -> bool:
    """Unicode word-ness: letters, digits, underscore, and combining marks."""
    return char.isalnum() or char == "_" or unicodedata.category(char).startswith("M")


def span_errors(text: str, start: int, end: int, *, claimed_text: str | None = None) -> list[str]:
    """Everything wrong with one stored span, checked against the source it names."""
    errors: list[str] = []
    if start < 0 or end <= start or end > len(text):
        return [f"span {start}:{end} is outside the translation record"]
    snippet = text[start:end]
    if claimed_text is not None and snippet != claimed_text:
        errors.append(f"span {start}:{end} holds {snippet!r}, not the claimed {claimed_text!r}")
    if is_word_char(snippet[0]) and start > 0 and is_word_char(text[start - 1]):
        errors.append(f"span {start}:{end} begins inside a word: {text[max(0, start - 8) : end]!r}")
    if is_word_char(snippet[-1]) and end < len(text) and is_word_char(text[end]):
        errors.append(f"span {start}:{end} ends inside a word: {text[start : end + 8]!r}")
    return errors


def find_anchors(text: str, anchor: str, *, ignore_case: bool = False) -> list[Anchor]:
    """Every boundary-safe occurrence of ``anchor``, in source order.

    ``ignore_case`` matches with the regex engine so the returned offsets remain offsets
    into ``text``; the stored text is always what the source actually says.
    """
    if not anchor:
        return []
    flags = re.IGNORECASE if ignore_case else 0
    return [
        Anchor(match.start(), match.end(), match.group(0))
        for match in re.finditer(re.escape(anchor), text, flags)
        if not span_errors(text, match.start(), match.end())
    ]


def resolve_anchor(
    text: str,
    anchor: str,
    *,
    occurrence: int | None = None,
    ignore_case: bool = False,
) -> Anchor:
    """One occurrence, or a refusal.

    A repeated anchor is only resolvable when the caller says which occurrence it means:
    silently taking the first is how an assertion ends up anchored to a different clause
    than the one it was authored from.
    """
    found = find_anchors(text, anchor, ignore_case=ignore_case)
    if not found:
        raise MissingAnchorError(f"{anchor!r} has no boundary-safe occurrence")
    if occurrence is None:
        if len(found) > 1:
            raise AmbiguousAnchorError(
                f"{anchor!r} occurs {len(found)} times; name the occurrence or supply offsets"
            )
        return found[0]
    if not 1 <= occurrence <= len(found):
        raise MissingAnchorError(
            f"{anchor!r} has {len(found)} occurrences; {occurrence} was requested"
        )
    return found[occurrence - 1]


def first_anchor(text: str, anchors: list[str], *, ignore_case: bool = True) -> Anchor | None:
    """The first supplied anchor with exactly one boundary-safe occurrence, or ``None``.

    Used by the deterministic baseline, where an ambiguous anchor is dropped rather than
    guessed. Returning ``None`` costs a span; guessing costs the meaning of every span.
    """
    for anchor in anchors:
        if not anchor:
            continue
        found = find_anchors(text, anchor, ignore_case=ignore_case)
        if len(found) == 1:
            return found[0]
    return None
