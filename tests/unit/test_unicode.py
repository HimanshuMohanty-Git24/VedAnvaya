import unicodedata

from vedagraph.normalize import (
    ComparisonProfile,
    comparison_normalize,
    has_vedic_accents,
    normalize_nfc,
)


def test_nfc_preserves_vedic_accent() -> None:
    original = "अ\u0952ग्नि"
    normalized = normalize_nfc(original)
    assert normalized == unicodedata.normalize("NFC", original)
    assert "\u0952" in normalized
    assert has_vedic_accents(normalized)


def test_accentless_comparison_is_explicit() -> None:
    accented = "अ\u0952ग्नि"
    assert comparison_normalize(
        accented, ComparisonProfile.ACCENT_PRESERVING
    ) != comparison_normalize(accented, ComparisonProfile.ACCENTLESS)
    assert comparison_normalize(accented, ComparisonProfile.ACCENTLESS) == "अग्नि"


def test_decomposed_devanagari_is_nfc() -> None:
    decomposed = "क़"
    assert normalize_nfc(decomposed) == unicodedata.normalize("NFC", decomposed)
