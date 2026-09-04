"""Replaceable transliteration protocol."""

from typing import Protocol


class Transliterator(Protocol):
    source_script: str
    target_scheme: str

    def transliterate(self, text: str) -> str:
        """Produce deterministic derived display/search text."""
        ...
