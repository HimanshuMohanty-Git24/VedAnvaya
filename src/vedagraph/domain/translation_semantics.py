"""The one contract that says what kind of coverage a translation gives a verse.

Three mechanisms used to answer "is this verse translated?" and all three answered it by
testing for a ``HAS_TRANSLATION`` edge: the passage reader, ``TranslationCoverage``, and
Ask's retriever. That test was right while every translation was a 1:1 rendering of its
own verse, and it stopped being right when ``GAP-TRANSLATION-006`` landed. Griffith renders
each pair of dvipada verses in RV 1.65-1.70 as a single unit, so the graph now holds
translations aligned to ``MANTRA_RANGE``: the node hangs off the first verse of the span
and names the whole span in ``covers_canonical_keys``. An edge test therefore reports the
second verse of every pair as untranslated, and the reader told 30 real verses that no
released translation covered them while one did.

Two more distinctions arrive with the same shape. A *reused rendering* is Griffith's
Rigvedic English attached to a Samavedic or Atharvavedic verse whose Sanskrit is verified
character-identical; it is a real translation of that text and it is not an independent
translation of that corpus, and a product that cannot say which has told the reader the
Samaveda has English translations of its own. A *Latin substitution* is Griffith rendering
an explicit passage into Latin rather than English; the literal is his real text, and
counting it as English coverage overstates the English layer by the exact number of
passages Victorian propriety removed from it.

So coverage is not a boolean and never was. This module holds the single classifier, and
:func:`classify` raises on an ``alignment_level`` it does not recognise rather than
defaulting to ``DEDICATED``. Defaulting is how a fourth alignment level would silently be
reported as a verse's own 1:1 translation, which is the defect this module exists to end.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Any, Final

from vedagraph.models.enums import AlignmentLevel


class TranslationCoverageKind(StrEnum):
    """How a translation covers the verse it was asked about.

    The order is the reporting order and the values are deliberately not rankable: a
    ``RANGE_TRANSLATION`` is not a worse ``DEDICATED_TRANSLATION``, it is a different claim
    about what the translator aligned to.
    """

    #: A translation of this verse, aligned to this verse.
    DEDICATED_TRANSLATION = "DEDICATED_TRANSLATION"
    #: A translation whose print unit spans this verse and at least one other.
    RANGE_TRANSLATION = "RANGE_TRANSLATION"
    #: A translation aligned to a container above the verse (a hymn, a section).
    CONTAINER_TRANSLATION = "CONTAINER_TRANSLATION"
    #: Another corpus's published rendering of text verified identical to this verse.
    REUSED_RENDERING = "REUSED_RENDERING"


#: The value of ``reuse_kind`` on a :class:`Translation` node that is a reused rendering.
#: Absence means the rendering is the translator's own work on this passage, which is why
#: nothing had to be written onto the 17,283 nodes that were already canonical.
REUSE_KIND_REUSED_RENDERING: Final = "REUSED_RENDERING"

#: Alignment levels that mean the translation is aligned above the verse.
_CONTAINER_LEVELS: Final[frozenset[str]] = frozenset(
    {
        AlignmentLevel.WORK,
        AlignmentLevel.SECTION,
        AlignmentLevel.HYMN,
        AlignmentLevel.STRUCTURAL_CONTAINER,
    }
)

#: The language every English layer figure is measured over. A translation in any other
#: language is coverage of the verse and is not coverage of the English layer.
ENGLISH: Final = "en"


class UnknownAlignmentLevel(ValueError):
    """An ``alignment_level`` no coverage kind is declared for.

    Raised rather than defaulted. A new alignment level is a data-model change, and the
    failure mode of guessing is that the product presents it as a dedicated 1:1
    translation -- which is the exact untruth ``GAP-TRANSLATION-006`` was opened for.
    """


def classify(
    props: Mapping[str, Any], *, asked_about: str | None = None
) -> TranslationCoverageKind:
    """The kind of coverage ``props`` gives the verse ``asked_about``.

    ``props`` is a :class:`Translation` node's properties. ``asked_about`` is the canonical
    key the caller is rendering; it only matters for ranges, where the answer is the same
    either way but the caller usually wants to know whether it is looking at the anchor.

    Precedence: reuse first. A reused rendering aligned to a mantra is still a reused
    rendering, and reporting it as ``DEDICATED_TRANSLATION`` because its alignment is
    ``MANTRA`` is the failure the owner policy forbids.
    """
    if props.get("reuse_kind") == REUSE_KIND_REUSED_RENDERING:
        return TranslationCoverageKind.REUSED_RENDERING

    level = props.get("alignment_level")
    if level == AlignmentLevel.MANTRA_RANGE:
        return TranslationCoverageKind.RANGE_TRANSLATION
    if level == AlignmentLevel.MANTRA:
        return TranslationCoverageKind.DEDICATED_TRANSLATION
    if level in _CONTAINER_LEVELS:
        return TranslationCoverageKind.CONTAINER_TRANSLATION
    raise UnknownAlignmentLevel(
        f"alignment_level={level!r} has no declared coverage kind"
        + (f" (asked about {asked_about})" if asked_about else "")
        + ". Declare one here rather than letting the product present it as a "
        "verse's own 1:1 translation."
    )


def covered_keys(props: Mapping[str, Any], anchor_key: str | None = None) -> list[str]:
    """Every canonical key this translation covers, anchor included.

    A ``MANTRA_RANGE`` node must enumerate its span; a node that claims the level and
    carries no list is a defect, so this returns the anchor alone and callers that need to
    reject that shape use :func:`range_is_complete`.
    """
    raw = props.get("covers_canonical_keys")
    if isinstance(raw, str):  # a single-element list can arrive unwrapped from a CSV load
        raw = [raw]
    if isinstance(raw, Sequence) and raw:
        keys = [str(k) for k in raw]
    else:
        keys = []
    if not keys and anchor_key:
        keys = [anchor_key]
    if anchor_key and anchor_key not in keys:
        keys = [anchor_key, *keys]
    return keys


def range_is_complete(props: Mapping[str, Any]) -> bool:
    """True when a range translation enumerates a span of at least two verses."""
    if props.get("alignment_level") != AlignmentLevel.MANTRA_RANGE:
        return True
    return len(covered_keys(props)) >= 2


def is_independent(props: Mapping[str, Any]) -> bool:
    """Whether this is the translator's own rendering of this passage.

    Derived from the absence of ``reuse_kind`` rather than from a stored boolean, so the
    17,283 translations that were canonical before reuse existed did not have to be
    rewritten to keep answering correctly.
    """
    return props.get("reuse_kind") != REUSE_KIND_REUSED_RENDERING


def counts_as_independent_english(props: Mapping[str, Any]) -> bool:
    """Whether this translation may be totalled into a corpus's English coverage.

    Both exclusions matter and they are different. A reused rendering is English and is
    not this corpus's own. A Latin substitution is this corpus's own and is not English.
    """
    return is_independent(props) and props.get("language") == ENGLISH


def disclosure(props: Mapping[str, Any]) -> str | None:
    """The sentence a reader must see beside this translation, or None if none is owed.

    Returned as prose from one place so the API, the reader and Ask cannot each phrase the
    same disclosure slightly differently and leave a client guessing whether two wordings
    mean two things.
    """
    if props.get("reuse_kind") == REUSE_KIND_REUSED_RENDERING:
        veda = props.get("reused_from_veda") or "another corpus"
        citation = props.get("reused_from_citation") or props.get("reused_from_passage_key")
        where = f" of {citation}" if citation else ""
        return (
            f"English rendering reused from the {_veda_name(veda)} parallel{where}. "
            "The Sanskrit of the two passages is verified identical; this is not an "
            "independent translation of this verse's own corpus."
        )
    if props.get("alignment_level") == AlignmentLevel.MANTRA_RANGE:
        keys = covered_keys(props)
        return (
            f"The source prints one rendering across {len(keys)} verses of this corpus's "
            "numbering, so this translation covers the span rather than this verse alone."
        )
    if props.get("language") and props.get("language") != ENGLISH:
        return (
            f"This rendering is in {_language_name(str(props['language']))}, not English. "
            "Griffith rendered passages he judged too explicit for an English readership "
            "into Latin instead; the literal is his published text."
        )
    return None


_VEDA_NAMES: Final[dict[str, str]] = {
    "RV": "Rigvedic",
    "SV": "Samavedic",
    "YV": "Yajurvedic",
    "AV": "Atharvavedic",
}

_LANGUAGE_NAMES: Final[dict[str, str]] = {"en": "English", "la": "Latin"}


def _veda_name(code: str) -> str:
    return _VEDA_NAMES.get(code, code)


def _language_name(code: str) -> str:
    return _LANGUAGE_NAMES.get(code, code)


def language_name(code: str | None) -> str | None:
    """A renderable language name, or the code itself when it is not one we name."""
    if not code:
        return None
    return _LANGUAGE_NAMES.get(code, code)
