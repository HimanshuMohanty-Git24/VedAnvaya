"""Deterministic surface normalization for Anukramaṇī labels.

This module normalizes *writing*, never *meaning*. It folds Unicode form, whitespace
and letter case, because those differences cannot distinguish two Vedic entities. It
never merges two different spellings: ``uṣṇik`` and ``uṣnik`` stay distinct strings
here, and are only ever united by an explicit reviewed alias in
``data/registry/anukramani_aliases.yaml``.

Two key derivations exist:

``ascii_key``
    A readable ASCII fold used for canonical entity keys (``gāyatrī`` → ``GAYATRI``).
    The fold is lossy: ``ś``, ``ṣ`` and ``s`` all become ``S``. Two distinct labels
    may therefore collide, and a collision is never treated as evidence of identity.

``distinct_key``
    A longer, length- and sibilant-preserving fold used only to disambiguate a
    collision (``aśvaḥ`` → ``ASHVAH``, ``aśvāḥ`` → ``ASHVAAH``).

Entity keys are not recomputed at build time. They are generated once, reviewed, and
pinned in the committed registries; the build reads them as data.
"""

from __future__ import annotations

import re
import unicodedata

NORMALIZATION_POLICY_VERSION = "anukramani-surface-normalization-v1"

_WHITESPACE = re.compile(r"\s+")
_NON_KEY = re.compile(r"[^A-Z0-9]+")

# Readable fold. Diacritics are dropped; distinctions that only diacritics carry are
# lost on purpose, and the loss is detected as a collision rather than assumed benign.
_ASCII_FOLD = str.maketrans(
    {
        "ā": "a",
        "ī": "i",
        "ū": "u",
        "ṛ": "r",
        "ṝ": "r",
        "ḷ": "l",
        "ḹ": "l",
        "ḻ": "l",
        "ś": "s",
        "ṣ": "s",
        "ṭ": "t",
        "ḍ": "d",
        "ṇ": "n",
        "ṅ": "n",
        "ñ": "n",
        "ḥ": "h",
        "ṁ": "m",
        "ṃ": "m",
        "ē": "e",
        "ō": "o",
    }
)

# Collision-breaking fold. Long vowels double, sibilants and retroflexes keep a marker.
_DISTINCT_FOLD = {
    "ā": "aa",
    "ī": "ii",
    "ū": "uu",
    "ṛ": "ri",
    "ṝ": "rii",
    "ḷ": "li",
    "ḹ": "lii",
    "ḻ": "lh",
    "ś": "sh",
    "ṣ": "ss",
    "ṭ": "tt",
    "ḍ": "dd",
    "ṇ": "nn",
    "ṅ": "ng",
    "ñ": "ny",
    "ḥ": "h",
    "ṁ": "m",
    "ṃ": "m",
    "ē": "e",
    "ō": "o",
}


def normalize_label(raw: str) -> str:
    """NFC, trim, collapse internal whitespace, and lowercase.

    Nothing semantic is touched: hyphens, which join the components of a composite
    label, are preserved exactly.
    """
    return _WHITESPACE.sub(" ", unicodedata.normalize("NFC", raw).strip()).lower()


def ascii_key(label: str) -> str:
    """Readable uppercase ASCII key for a normalized label."""
    return _NON_KEY.sub("-", label.translate(_ASCII_FOLD).upper()).strip("-")


def distinct_key(label: str) -> str:
    """Collision-breaking key that keeps vowel length and sibilant class."""
    folded = "".join(_DISTINCT_FOLD.get(character, character) for character in label)
    return _NON_KEY.sub("-", folded.upper()).strip("-")


def is_composite_label(label: str) -> bool:
    """True when the source itself joined several names with hyphens.

    A hyphen in this dataset is the authors' own compositional marker
    (``iḻā-sarasvatī-mahī``). Dual and plural forms such as ``mitrāvaruṇau`` or
    ``ādityāḥ`` are *not* detected here: recognising them requires morphology, which is
    interpretation, so they are classified only where the registry says so explicitly.
    """
    return "-" in label


def composite_parts(label: str) -> list[str]:
    """The hyphen-separated surface parts of a composite label, unresolved."""
    return [part for part in (piece.strip() for piece in label.split("-")) if part]
