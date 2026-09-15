"""Normalization public API."""

from vedagraph.normalize.unicode import (
    ComparisonForm,
    ComparisonProfile,
    comparison_form,
    comparison_normalize,
    fold_transcription,
    fold_transcription_cross_script,
    has_vedic_accents,
    normalize_nfc,
    strip_editorial_marks,
    strip_vedic_accents,
)

__all__ = [
    "ComparisonForm",
    "ComparisonProfile",
    "comparison_form",
    "comparison_normalize",
    "fold_transcription",
    "fold_transcription_cross_script",
    "has_vedic_accents",
    "normalize_nfc",
    "strip_editorial_marks",
    "strip_vedic_accents",
]
