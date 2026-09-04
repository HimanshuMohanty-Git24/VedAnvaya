"""Deterministic comparison of Rigveda mantra text across editions.

This compares different *editions of the same mantra*. It is not a cross-Veda matcher
and it never decides which reading is correct: it classifies how two readings differ.

Classification is a strict refinement ladder. Each rung is a pure string predicate over
one named comparison surface, so the same inputs always yield the same category. Rungs
that would require philological judgement are not attempted; those fall through to
``UNCLASSIFIED``. ``LEXICAL_VARIANT`` is reserved for human review and is never emitted
automatically.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from difflib import SequenceMatcher

from vedagraph.identity import uuid_for_urn
from vedagraph.models import TextComparison
from vedagraph.models.enums import TextComparisonCategory, TextRole
from vedagraph.normalize import (
    ComparisonForm,
    comparison_form,
    fold_transcription,
    has_vedic_accents,
    strip_editorial_marks,
)

COMPARATOR_VERSION = "text-compare-v1"


@dataclass(frozen=True)
class VersionReading:
    """One version's reading of one mantra."""

    version_id: str
    text: str
    role: TextRole = TextRole.PARALLEL_TEXT


DEVANAGARI = range(0x0900, 0x0980)


def _has_devanagari(text: str) -> bool:
    return any(ord(char) in DEVANAGARI for char in text)


def _letters(text: str) -> str:
    return "".join(text.split())


def _tokens(text: str) -> list[str]:
    return text.split()


def _difference_size(left: Sequence[str], right: Sequence[str]) -> int:
    """Number of positions the two sequences do not share, as an edit-size measure."""
    matcher = SequenceMatcher(None, left, right, autojunk=False)
    return sum(
        max(i2 - i1, j2 - j1) for tag, i1, i2, j1, j2 in matcher.get_opcodes() if tag != "equal"
    )


def classify(
    left: VersionReading, right: VersionReading
) -> tuple[TextComparisonCategory, str, str | None]:
    """Return ``(category, classification_basis, equal_at_form)``."""
    if _has_devanagari(left.text) != _has_devanagari(right.text):
        return (
            TextComparisonCategory.UNCLASSIFIED,
            "the two readings are in different scripts; a reviewed transliteration step "
            "must run before these versions can be compared as strings",
            None,
        )
    forms = (
        (ComparisonForm.SOURCE_ORIGINAL, TextComparisonCategory.IDENTICAL, "byte-identical source"),
        (ComparisonForm.NFC, TextComparisonCategory.UNICODE_ONLY, "equal after Unicode NFC"),
        (
            ComparisonForm.ACCENT_PRESERVING_NORMALIZED,
            TextComparisonCategory.ORTHOGRAPHIC,
            "equal after whitespace and editorial-punctuation normalization",
        ),
    )
    for form, category, basis in forms:
        if comparison_form(left.text, form) == comparison_form(right.text, form):
            return category, basis, form.value

    accent_kept = (
        _fold_keeping_accents(left.text),
        _fold_keeping_accents(right.text),
    )
    if accent_kept[0] == accent_kept[1]:
        return (
            TextComparisonCategory.ORTHOGRAPHIC,
            "equal after folding IAST and ISO 15919 transcription variants",
            "TRANSCRIPTION_FOLDED",
        )

    stripped = (
        comparison_form(left.text, ComparisonForm.SEARCH_NORMALIZED),
        comparison_form(right.text, ComparisonForm.SEARCH_NORMALIZED),
    )
    if stripped[0] == stripped[1]:
        return (
            TextComparisonCategory.ACCENT_ONLY,
            "equal only once Vedic tone marks are removed",
            ComparisonForm.SEARCH_NORMALIZED.value,
        )

    if _letters(stripped[0]) == _letters(stripped[1]):
        return (
            TextComparisonCategory.SANDHI_OR_SEGMENTATION,
            "identical letter sequence with different word segmentation",
            None,
        )

    if Counter(_tokens(stripped[0])) == Counter(_tokens(stripped[1])):
        return (
            TextComparisonCategory.STRUCTURAL_VARIANT,
            "same tokens in a different order",
            None,
        )

    if TextRole.METRICALLY_RESTORED in (left.role, right.role):
        return (
            TextComparisonCategory.METRICAL_RESTORATION,
            "one side is a declared metrically restored version; "
            "the label follows declared provenance, not textual analysis",
            None,
        )

    return (
        TextComparisonCategory.UNCLASSIFIED,
        "no deterministic rule applies; classification requires human review",
        None,
    )


def _fold_keeping_accents(text: str) -> str:
    """Transcription fold that keeps tone marks, so accent-only diffs stay visible."""
    return " ".join(fold_transcription(strip_editorial_marks(text)).casefold().split())


def compare_readings(
    *,
    passage_key: str,
    citation: str,
    left: VersionReading,
    right: VersionReading,
) -> TextComparison:
    """Compare one mantra across two versions."""
    category, basis, equal_at = classify(left, right)
    left_search = comparison_form(left.text, ComparisonForm.SEARCH_NORMALIZED)
    right_search = comparison_form(right.text, ComparisonForm.SEARCH_NORMALIZED)
    left_accented_form = _fold_keeping_accents(left.text)
    right_accented_form = _fold_keeping_accents(right.text)
    return TextComparison(
        comparison_id=uuid_for_urn(
            f"urn:vedagraph:text-comparison:{passage_key}:"
            f"{left.version_id}:{right.version_id}:{COMPARATOR_VERSION}"
        ),
        passage_key=passage_key,
        citation=citation,
        left_version_id=left.version_id,
        right_version_id=right.version_id,
        category=category,
        classification_basis=basis,
        equal_at_form=equal_at,
        similarity=round(
            SequenceMatcher(None, left_search, right_search, autojunk=False).ratio(), 6
        ),
        differing_codepoints=_difference_size(left_search, right_search),
        differing_tokens=_difference_size(_tokens(left_search), _tokens(right_search)),
        left_token_count=len(_tokens(left_search)),
        right_token_count=len(_tokens(right_search)),
        accent_only=(left_accented_form != right_accented_form and left_search == right_search),
        left_accented=has_vedic_accents(left.text),
        right_accented=has_vedic_accents(right.text),
    )


def compare_missing(
    *,
    passage_key: str,
    citation: str,
    left_version_id: str,
    right_version_id: str,
) -> TextComparison:
    """Record that a version has no reading for an aligned passage."""
    return TextComparison(
        comparison_id=uuid_for_urn(
            f"urn:vedagraph:text-comparison:{passage_key}:"
            f"{left_version_id}:{right_version_id}:{COMPARATOR_VERSION}"
        ),
        passage_key=passage_key,
        citation=citation,
        left_version_id=left_version_id,
        right_version_id=right_version_id,
        category=TextComparisonCategory.MISSING,
        classification_basis="at least one version has no reading for this passage",
        similarity=0.0,
        differing_codepoints=0,
        differing_tokens=0,
        left_token_count=0,
        right_token_count=0,
    )
