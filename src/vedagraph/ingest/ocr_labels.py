"""Reading a printed verse label that OCR has corrupted, without guessing.

Two Griffith layers in this project record a verse as a *source gap* when the source's own
printed number failed to parse. Sometimes that is right -- the print really omits the verse.
Sometimes the number is there and one glyph of it was misread, and the translation is sitting
in the bytes with nothing pointing at it. RV 8.93.29 is the second case: its label is set as
``2`` followed by a section sign, so an integer parse fails, the verse is reported as having
no translation, and its English is silently glued onto verse 28.

The rule here is deliberately narrow, because the failure mode of a permissive one is silent.
A corrupt token is read only when:

* every character is a digit or a glyph in :data:`GLYPH_TO_DIGIT`, and
* substituting them yields a number, and
* that number is the one free slot the surrounding literal labels leave.

Anything else refuses. In particular the token is never *interpolated* from position alone --
that is a different instrument with a different error profile, and mixing the two is how a
global optimiser once "recovered" 60 verses while shifting 53 others by one place.
"""

from __future__ import annotations

from typing import Iterable

#: One glyph, one digit. Measured from the two Griffith OCR layers this project holds:
#: the Yajurveda pass recorded S for 5 and 8, l and I for 1, O for 0; the section sign for 9
#: is the Rigvedic case at 8.93.29. The map is intentionally small -- every entry is a
#: substitution that has actually been observed in these bytes, not a plausible one.
GLYPH_TO_DIGIT: dict[str, str] = {
    "§": "9",   # SECTION SIGN
    "S": "5",
    "s": "5",
    "O": "0",
    "o": "0",
    "l": "1",
    "I": "1",
    "B": "8",
    "Z": "2",
    "G": "6",
    "q": "9",
    "g": "9",
    "J": "3",
    "T": "7",
}


def readings(token: str) -> list[int]:
    """Every number ``token`` can be, literally or under single-glyph substitution.

    Returns an empty list when the token cannot be a number at all, which is the common
    case for ordinary words and the reason this is not a substring search.
    """
    core = token.strip().rstrip(".")
    if not core:
        return []
    out: set[int] = set()
    if core.isdigit():
        out.add(int(core))
    substituted = [GLYPH_TO_DIGIT.get(c, c) for c in core]
    if all(c.isdigit() for c in substituted):
        out.add(int("".join(substituted)))
    return sorted(out)


def resolve_corrupt_label(
    token: str,
    *,
    preceding_label: int,
    following_label: int,
    printed_unit_count: int,
    canonical_verse_count: int,
) -> int | None:
    """The verse number ``token`` denotes, or ``None`` if it is not forced.

    ``preceding_label`` and ``following_label`` are the nearest labels the print sets
    *literally*, either side of the corrupt one. The answer is accepted only when the print
    and the canonical spine agree on how many verses this hymn has -- without that, a
    "recovered" label could be papering over a missing or an extra unit.
    """
    if printed_unit_count != canonical_verse_count:
        return None
    if following_label - preceding_label != 2:
        # More than one slot between the neighbours: the token is not forced by them.
        return None
    forced = preceding_label + 1
    return forced if forced in readings(token) else None


def sole_free_slot(taken: Iterable[int], total: int) -> int | None:
    """The one label in ``1..total`` that ``taken`` does not use, or ``None`` if not one."""
    free = [n for n in range(1, total + 1) if n not in set(taken)]
    return free[0] if len(free) == 1 else None
