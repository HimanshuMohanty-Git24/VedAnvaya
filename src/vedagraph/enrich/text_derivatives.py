"""Deterministic derived text versions: the search surface and the accent-stripped surface.

Two derivatives, one instrument each, and the instrument is named on every row rather than
implied by the role.

**Why this module exists.** Only the Atharvaveda ever received a search-normalised text
version, so an accent-bearing query reached one corpus of four and reported the other three
as having no such wording. That is not a coverage difference in the corpus; it is a
difference in what each ingest happened to derive, which is exactly the kind of gap a
reader mistakes for a fact about the text.

**The script problem, stated because it is the whole design.** The Rigvedic and
Atharvavedic texts are stored in Latin transliteration; the Samavedic and Yajurvedic texts
are stored in Devanagari. :func:`~vedagraph.normalize.unicode.comparison_form` does not
transliterate, so applying ``SEARCH_NORMALIZED`` to all four leaves two corpora in
Devanagari and two in Latin, and **no single query string can reach both halves**. A
Devanagari-primary corpus therefore takes one extra, declared step -- transliteration to
IAST -- before the same final fold. That step is recorded per row in
``derivation_steps`` so a reader can tell which surface travelled further from its source.

**What a derivative is not.** A search-normalised Samavedic text is not an accented
Samavedic text. Stripping an accent that was never there does not supply one. Nothing here
claims an accented Samavedic witness, and :data:`ACCENT_SOURCE_DERIVED` exists so that an
accent-stripped row derived from our own accented text is never mistaken for the source's
own unaccented witness.
"""

from __future__ import annotations

import hashlib
from typing import Final, NamedTuple

from vedagraph.enrich.surfaces import to_iast
from vedagraph.normalize.unicode import (
    ComparisonForm,
    comparison_form,
    fold_devanagari_source_conventions,
    normalize_nfc,
)

#: The stored text is the source's own unaccented witness.
ACCENT_SOURCE_WITNESS: Final = "SOURCE_UNACCENTED_WITNESS"
#: The stored text is our accent-stripped derivative of our own accented text. It is
#: evidence about our transform, never about a second edition.
ACCENT_SOURCE_DERIVED: Final = "DERIVED_ACCENT_STRIPPED"

#: Scripts that must be transliterated before the shared search fold. Anything not listed
#: is assumed already Latin and is folded directly; an unknown script raises rather than
#: passing through silently, because a pass-through would produce a row in a script no
#: query can reach while still reporting as SEARCH_DERIVATIVE.
_DEVANAGARI_SCRIPTS: Final = frozenset({"Devanagari", "Deva"})
_LATIN_SCRIPTS: Final = frozenset({"Latin", "Latn", "IAST"})

#: Every search derivative lands here, whatever it started as.
SEARCH_SURFACE_SCRIPT: Final = "Latin"


class DerivedText(NamedTuple):
    """One derived surface with the exact transform chain that produced it."""

    text: str
    script: str
    derivation_steps: tuple[str, ...]
    content_sha256: str


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def search_surface(source_text: str, script: str) -> DerivedText:
    """The cross-corpus search surface for one stored text.

    A Latin-script source gets ``SEARCH_NORMALIZED`` alone, which is byte-for-byte the
    instrument the Atharvavedic build already used, so the existing 5,839 rows and the new
    ones are the same kind of object. A Devanagari source is folded for source conventions,
    transliterated to IAST, and only then given the same final fold.

    :raises ValueError: if the script is neither Latin nor Devanagari. A silent
        pass-through would emit a row that reports as searchable and is not.
    """
    steps: tuple[str, ...]
    if script in _LATIN_SCRIPTS:
        text = comparison_form(source_text, ComparisonForm.SEARCH_NORMALIZED)
        steps = ("comparison_form:SEARCH_NORMALIZED",)
    elif script in _DEVANAGARI_SCRIPTS:
        folded = fold_devanagari_source_conventions(normalize_nfc(source_text))
        text = comparison_form(to_iast(folded, script), ComparisonForm.SEARCH_NORMALIZED)
        steps = (
            "normalize_nfc",
            "fold_devanagari_source_conventions",
            "to_iast",
            "comparison_form:SEARCH_NORMALIZED",
        )
    else:
        raise ValueError(
            f"no declared search-surface transform for script {script!r}; "
            "add one rather than letting the text pass through unfolded"
        )
    return DerivedText(text, SEARCH_SURFACE_SCRIPT, steps, _digest(text))


def accent_stripped_surface(source_text: str, script: str) -> DerivedText:
    """The accent-stripped surface, in the source's own script.

    Used only where the source supplies no unaccented witness of its own. The result keeps
    the source script, because it is a reading aid for that corpus rather than a
    cross-corpus comparison surface.
    """
    if script not in _LATIN_SCRIPTS and script not in _DEVANAGARI_SCRIPTS:
        raise ValueError(f"no declared accent-stripping transform for script {script!r}")
    text = comparison_form(source_text, ComparisonForm.ACCENT_STRIPPED_COMPARISON)
    return DerivedText(
        text,
        script,
        ("normalize_nfc", "fold_devanagari_source_conventions", "strip_vedic_accents"),
        _digest(text),
    )
