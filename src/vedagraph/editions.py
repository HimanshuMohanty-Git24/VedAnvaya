"""Structural divergences between the editions VedaGraph ingests.

Canonical passage numbering follows Aufrecht (via GRETIL).  A translation edition may
order the same hymns differently, in which case its page number is not the canonical
Sukta number.  Those divergences are recorded here as data, so no parser or build script
carries an edition rule in a conditional.
"""

from __future__ import annotations

# Griffith's Rigveda prints the eleven Valakhilya hymns at the END of Book 8 (his Hymns
# 93-103), while Aufrecht numbers them inline as RV 8.49-8.59.  Hymns 1-48 agree.
# Verified against per-hymn stanza counts and opening lines: Griffith 8/49 renders
# RV 8.60.1, and Griffith 8/93 renders RV 8.49.1.
_VALAKHILYA_FIRST = 49
_VALAKHILYA_LAST = 59
_VALAKHILYA_PAGE_OFFSET = 44


def griffith_page(mandala: int, sukta: int) -> int:
    """The Griffith Wikisource hymn page holding canonical ``RV <mandala>.<sukta>``."""
    if mandala != 8 or sukta < _VALAKHILYA_FIRST:
        return sukta
    if sukta <= _VALAKHILYA_LAST:
        return sukta + _VALAKHILYA_PAGE_OFFSET
    return sukta - (_VALAKHILYA_LAST - _VALAKHILYA_FIRST + 1)
