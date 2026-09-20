"""Align UD_Sanskrit-Vedic (human-validated) sentences to VedaGraph canonical keys.

The treebank cites a hymn, never a verse. So the verse must be recovered by text
alignment. Both sides are reduced to a de-accented, de-spaced skeleton, because the
treebank is unsandhied and the canonical text is sandhied: word boundaries and vowel
finals are exactly what differ, so a token-level match would fail on correct pairs.

An alignment is accepted only when the best candidate both clears an absolute
containment floor and beats the runner-up by a margin. Everything else is recorded as
unresolved rather than forced, because a wrong verse address resolves as cleanly as a
right one.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher

ALIGN_FLOOR = 0.62          # containment of the treebank skeleton in the verse skeleton
ALIGN_MARGIN = 0.06         # how far the winner must beat the runner-up

_COMBINING = {
    "́",  # acute / udatta
    "̀",  # grave
    "॑", "॒", "॓", "॔",
    "᳐", "᳑", "᳒", "᳚", "᳛", "᳠", "᳡",
}


def deaccent(text: str) -> str:
    """Drop tone marks but keep the below-dot and below-ring, which are letters in IAST.

    This is the mistake the Atharvavedic SEARCH_DERIVATIVE layer made: U+0323 and
    U+0325 are part of the letter in IAST, and stripping them turns kr̥dhi into kdhi.
    """
    decomposed = unicodedata.normalize("NFD", text)
    kept = [ch for ch in decomposed if ch not in _COMBINING]
    return unicodedata.normalize("NFC", "".join(kept))


_DEVANAGARI = re.compile(r"[ऀ-ॿ]")


def to_iast(text: str) -> str:
    """Transliterate Devanagari to IAST so a Latin treebank can be compared to it.

    The Samavedic and Yajurvedic canonical texts are Devanagari-only and the treebank is
    Latin-only, so without this step those two recensions are simply unreachable by any
    published annotation and would be reported as uncovered for the wrong reason.
    """
    if not _DEVANAGARI.search(text):
        return text
    from indic_transliteration import sanscript
    from indic_transliteration.sanscript import transliterate

    return transliterate(text, sanscript.DEVANAGARI, sanscript.IAST)


def skeleton(text: str) -> str:
    """De-accented, lowercased, punctuation- and space-free comparison form."""
    folded = deaccent(to_iast(text)).lower()
    folded = re.sub(r"\|+|//|\d+|[|।॥,.;:!?\"'()\[\]-]", " ", folded)
    return re.sub(r"\s+", "", folded)


def containment(needle: str, haystack: str) -> float:
    """Fraction of ``needle`` that SequenceMatcher can place inside ``haystack``."""
    if not needle:
        return 0.0
    matcher = SequenceMatcher(None, needle, haystack, autojunk=False)
    matched = sum(block.size for block in matcher.get_matching_blocks())
    return matched / len(needle)


@dataclass
class TreebankSentence:
    sent_id: str
    citation_text: str
    citation_chapter: str
    layer: str
    text: str
    forms: list[str] = field(default_factory=list)
    lemmas: list[str] = field(default_factory=list)
    upos: list[str] = field(default_factory=list)
    feats: list[str] = field(default_factory=list)
    annotators: list[str] = field(default_factory=list)

    @property
    def base_id(self) -> str:
        return self.sent_id.split("_")[0]


def parse_conllu(path) -> list[TreebankSentence]:
    sentences: list[TreebankSentence] = []
    meta: dict[str, str] = {}
    forms: list[str] = []
    lemmas: list[str] = []
    upos: list[str] = []
    feats: list[str] = []
    annotators: list[str] = []

    def flush() -> None:
        if meta.get("sent_id") and forms:
            sentences.append(
                TreebankSentence(
                    sent_id=meta.get("sent_id", ""),
                    citation_text=meta.get("citation_text", ""),
                    citation_chapter=meta.get("citation_chapter", ""),
                    layer=meta.get("layer", ""),
                    text=meta.get("text", ""),
                    forms=list(forms),
                    lemmas=list(lemmas),
                    upos=list(upos),
                    feats=list(feats),
                    annotators=sorted(set(annotators)),
                )
            )
        meta.clear()
        forms.clear()
        lemmas.clear()
        upos.clear()
        feats.clear()
        annotators.clear()

    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.rstrip("\n")
            if not line.strip():
                flush()
                continue
            if line.startswith("#"):
                body = line.lstrip("#").strip()
                if "=" in body:
                    key, _, value = body.partition("=")
                    meta[key.strip()] = value.strip()
                continue
            cols = line.split("\t")
            if len(cols) < 10 or "-" in cols[0] or "." in cols[0]:
                continue
            forms.append(cols[1])
            lemmas.append(cols[2])
            upos.append(cols[3])
            feats.append(cols[5])
            for piece in cols[9].split("|"):
                if piece.startswith("Annotator="):
                    annotators.append(piece.split("=", 1)[1])
    flush()
    return sentences


def rv_hymn_prefix(chapter: str) -> str | None:
    parts = [p.strip() for p in chapter.split(",")]
    if len(parts) != 2 or not all(p.isdigit() for p in parts):
        return None
    return f"VG:RV:SAK:M{int(parts[0]):02d}:S{int(parts[1]):03d}:"


def av_hymn_prefix(chapter: str) -> str | None:
    parts = [p.strip() for p in chapter.split(",")]
    if len(parts) != 2 or not all(p.isdigit() for p in parts):
        return None
    return f"VG:AV:SAU:K{int(parts[0]):02d}:S{int(parts[1]):03d}:"


def yv_hymn_prefix(chapter: str) -> str | None:
    part = chapter.strip()
    if not part.isdigit():
        return None
    return f"VG:YV:VSM:A{int(part):02d}:"


HYMN_PREFIX = {"ṚV": rv_hymn_prefix, "AVŚ": av_hymn_prefix, "VSM": yv_hymn_prefix}


def align(sentence: TreebankSentence, candidates: dict[str, str]) -> dict:
    """Pick the canonical key whose skeleton best contains this sentence's skeleton."""
    needle = skeleton(" ".join(sentence.forms))
    scored = sorted(
        ((containment(needle, hay), key) for key, hay in candidates.items()),
        reverse=True,
    )
    if not scored:
        return {"status": "NO_CANDIDATES", "key": None, "score": 0.0, "runner_up": 0.0}
    best_score, best_key = scored[0]
    runner_up = scored[1][0] if len(scored) > 1 else 0.0
    if best_score < ALIGN_FLOOR:
        status = "BELOW_FLOOR"
    elif best_score - runner_up < ALIGN_MARGIN:
        status = "AMBIGUOUS_MARGIN"
    else:
        status = "ALIGNED"
    return {
        "status": status,
        "key": best_key if status == "ALIGNED" else None,
        "best_key": best_key,
        "score": round(best_score, 4),
        "runner_up": round(runner_up, 4),
        "candidates": len(candidates),
    }
