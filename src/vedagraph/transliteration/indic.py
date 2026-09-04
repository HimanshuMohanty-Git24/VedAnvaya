"""indic-transliteration backed Devanagari-to-IAST implementation."""

from indic_transliteration import sanscript  # type: ignore[import-untyped]
from indic_transliteration.sanscript import transliterate  # type: ignore[import-untyped]

from vedagraph.normalize import normalize_nfc


class DevanagariToIAST:
    source_script = "Devanagari"
    target_scheme = "IAST"

    def transliterate(self, text: str) -> str:
        # Vedic marks are passed through by the current dependency but its complete
        # tonal semantics are not guaranteed; this output remains derived data.
        return normalize_nfc(
            transliterate(normalize_nfc(text), sanscript.DEVANAGARI, sanscript.IAST)
        )
