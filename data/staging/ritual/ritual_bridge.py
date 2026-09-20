"""The pratika bridge: which Samhita mantra a ritual locus quotes.

This is the mechanism GAP-RITUAL-006 needs. The registry's own warning about that gap is
that assigning a ritual context by proximity to ritual vocabulary is circular -- the ritual
vocabulary is the thing the context is supposed to explain. This module avoids the
circularity by using external evidence instead of lexical proximity: a mantra is employed
in ritual when a ritual text quotes it in an instruction, and the citing locus is named.

The quotation convention it exploits is the pratika -- Sanskrit ritual literature cites a
mantra by its opening words, usually closed by `iti`. So the test is whether a mantra's
opening letters occur at a word boundary in a ritual line.

Three precision controls, each one added because a measured sample showed it was needed:

1. The match must begin at a word boundary in the ritual line. Without this the matcher
   finds mantra openings inside compounds.
2. The match must span at least two words OF THE MANTRA. A one-word match is not a
   quotation, it is a shared common word -- the first sample of 25 contained five such,
   including `samvatsarasya` and `vaisvanaram` matching Brahmana prose that is plainly not
   quoting anything.
3. A mantra whose opening letters are shared with another mantra is not attributed to
   either. It goes to the unresolved queue with its rival named, because a confident wrong
   address resolves exactly as cleanly as a right one.
"""

from __future__ import annotations

import collections
from dataclasses import dataclass

from ritual_core import SuppLine, letters_only, norm_iast

# `iti` closes a quotation. Sandhi fuses it with the last quoted word, so the marker has to
# be recognised both free (`... iti`) and fused (`... tvety`, `... aganmeti`).
ITI_FREE = ("iti", "ity", "itī")
ITI_FUSED_ENDINGS = ("eti", "ety", "etī", "iti", "ity", "itī")

MIN_LETTERS = 12          # shortest accepted prefix, in normalised letters
MIN_MANTRA_WORDS = 2      # a one-word match is not a quotation
EXACT_LETTERS = 20        # an unmarked match this long is accepted without `iti`


@dataclass(frozen=True)
class WordMap:
    """Letter-offset bookkeeping for one line, so word boundaries survive space removal."""

    starts: tuple[int, ...]
    words: tuple[str, ...]
    total: int

    def word_index_at(self, offset: int) -> int:
        lo, hi = 0, len(self.starts) - 1
        best = 0
        while lo <= hi:
            mid = (lo + hi) // 2
            if self.starts[mid] <= offset:
                best, lo = mid, mid + 1
            else:
                hi = mid - 1
        return best


def word_map(text: str) -> WordMap:
    starts: list[int] = []
    words: list[str] = []
    offset = 0
    for word in norm_iast(text).split():
        letters = letters_only(word)
        if not letters:
            continue
        starts.append(offset)
        words.append(letters)
        offset += len(letters)
    return WordMap(tuple(starts), tuple(words), offset)


def mantra_word_span(wmap: WordMap, matched_letters: int) -> int:
    """How many of the mantra's own words the matched run covers, counting a word as
    covered only when the match reaches past its first letter."""
    return sum(1 for s in wmap.starts if s < matched_letters)


def ends_at_word_boundary(line_map: WordMap, offset_after: int) -> bool:
    """Did the matched run stop where a word of the citing line stops?

    This is the control the first adversarial sample was missing. A pratika quotation is
    made of whole words, so a run that stops in the middle of a citing word means the
    citing word and the mantra word diverge -- which is to say they are not the same text.
    AVS 4.38.5 opens `suryasya rasmin` and eleven ritual works quote the standard
    purification formula `suryasya rasmibhir iti`; the first twelve letters agree, the run
    then stops inside `rasmibhir`, and nine works were credited with quoting an
    Atharvavedic verse they are not quoting.
    """
    return offset_after in line_map.starts or offset_after == line_map.total


def iti_marked(line_map: WordMap, offset_after: int) -> bool:
    """Is the matched run closed by `iti` in the citing line?

    Only counted when the run itself ends cleanly: either at a word boundary with `iti` as
    the next word, or inside a word whose tail is a sandhi-fused `iti` and which the run
    reaches the end of.
    """
    words = line_map.words
    idx = line_map.word_index_at(max(offset_after - 1, 0))
    word_end = line_map.starts[idx] + len(words[idx])
    if offset_after == word_end and any(
        words[idx].endswith(e) for e in ITI_FUSED_ENDINGS
    ):
        return True
    if (
        ends_at_word_boundary(line_map, offset_after)
        and idx + 1 < len(words)
        and words[idx + 1].startswith(ITI_FREE)
    ):
        return True
    return False


class RitualQuotationIndex:
    """Word-anchored prefix index over the supplementary ritual prose."""

    def __init__(self, corpus: dict[str, list[SuppLine]], k: int = MIN_LETTERS) -> None:
        self.k = k
        self.corpus = corpus
        self.maps: dict[str, list[WordMap]] = {}
        self.index: dict[str, list[tuple[str, int, int]]] = collections.defaultdict(list)
        for abbr, lines in corpus.items():
            maps = [word_map(ln.text) for ln in lines]
            self.maps[abbr] = maps
            for i, line in enumerate(lines):
                letters = line.letters
                for start in maps[i].starts:
                    if start + k <= len(letters):
                        self.index[letters[start:start + k]].append((abbr, i, start))

    def lookup(self, prefix: str) -> list[tuple[str, int, int]]:
        return self.index.get(prefix[: self.k], [])

    def match(
        self, mantra_letters: str, mantra_map: WordMap
    ) -> dict[tuple[str, int], tuple[int, bool, bool]]:
        """Best (matched_letters, iti_marked, clean_end) per citing locus for one form."""
        out: dict[tuple[str, int], tuple[int, bool, bool]] = {}
        if len(mantra_letters) < self.k:
            return out
        for abbr, i, start in self.lookup(mantra_letters):
            target = self.corpus[abbr][i].letters
            n = self.k
            while (
                start + n < len(target)
                and n < len(mantra_letters)
                and target[start + n] == mantra_letters[n]
            ):
                n += 1
            if mantra_word_span(mantra_map, n) < MIN_MANTRA_WORDS:
                continue
            line_map = self.maps[abbr][i]
            clean = ends_at_word_boundary(line_map, start + n)
            marked = iti_marked(line_map, start + n)
            key = (abbr, i)
            prior = out.get(key)
            if prior is None or n > prior[0]:
                out[key] = (n, marked, clean)
        return out


def confidence_for(matched_letters: int, marked: bool, clean_end: bool) -> str:
    """EXACT only when the run ends where a citing word ends AND is marked or long.

    The clean-end requirement is not a refinement, it is the difference between a citation
    and a coincidence. Without it, 20 of 20 in the shortest-match sample looked correct and
    one of them -- repeated across nine works -- was crediting a purification formula from
    a different recension to an Atharvavedic verse.
    """
    if not clean_end:
        return "PROBABLE"
    if marked or matched_letters >= EXACT_LETTERS:
        return "EXACT"
    return "PROBABLE"
