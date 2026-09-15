"""VedSearch as the audio source: per-verse recitation, mapped and then *verified*.

**Why this replaced the Vedic Heritage Portal.** The portal publishes one file per sukta or
per adhyaya, so a verse's audio was its whole hymn -- audible as "too long" -- and the
mapping could only ever be inferred from a path scheme. VedSearch publishes **one file per
verse** and its API returns, beside the audio, *the text that file recites*. That turns the
mapping from an inference into a checkable claim, which is the whole difference between
this module and the one it replaced.

**The Valakhilya trap, which is why verification is not optional.** VedSearch numbers
Rigvedic Mandala 8 in *Griffith's* order, with the eleven Valakhilya hymns moved to the end
of the book, while this corpus numbers them inline at 8.49-8.59 after Aufrecht. A naive
key-for-key mapping therefore attaches the wrong recitation to **55 hymns** of Mandala 8 --
VedSearch's 8.60 is this corpus's 8.71. That is exactly the defect a user notices and a
schema does not. :func:`vedsearch_coordinates` routes Rigvedic sukta numbers through
:func:`vedagraph.editions.griffith_page`, the edition fact this repository already
established and tested, and :func:`skeleton` then re-checks the result against the text.

**Two independent safeguards, because one is not enough here.** The coordinate transform
could be right and the source could still have renumbered something else; the text check
could pass on a coincidence. So discovery requires both: the coordinates must map, and the
recited text must match the canonical text for that key. A verse that fails either gets no
record.

**Audio arrives as base64 inside JSON, not as a media file.** ``/v1/attachment/audio/...``
returns a JSON document whose ``attachment_content_base64`` decodes to an MP3. A browser
cannot play that URL directly, so :func:`audio_endpoint` is never handed to an ``<audio>``
element -- the product's own streaming route fetches it, decodes it, and serves real bytes
with Range support.
"""

from __future__ import annotations

import base64
import difflib
import json
import re
import unicodedata
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Final

from vedagraph.editions import griffith_page
from vedagraph.transliteration.indic import DevanagariToIAST

#: The public API root, read from the site's own client bundle.
API_ROOT: Final = "https://vedsearch.org/api"

#: A reader-facing page for one verse, used as ``source_page`` so a reader can see the
#: source's own labelling of what they are hearing.
SITE_ROOT: Final = "https://vedsearch.org"

SOURCE_NAME: Final = "VedSearch"

#: The site's own slug per Veda. The Atharvavedic one is irregular -- its pages live under
#: ``/atharvaved`` but its API path is ``atharved`` -- which the client bundle special-cases
#: and so must this.
API_SLUG: Final[dict[str, str]] = {
    "RV": "rigved",
    "SV": "samved",
    "YV": "yajurved",
    "AV": "atharved",
}
PAGE_SLUG: Final[dict[str, str]] = {
    "RV": "rigved",
    "SV": "samved",
    "YV": "yajurved",
    "AV": "atharvaved",
}

#: Only the Sanskrit track is a recitation. The site also publishes a Hindi reading, which
#: is a spoken *translation* and is deliberately not catalogued: a product that offered it
#: beside the Sanskrit under one "audio" affordance would present a paraphrase as recitation.
LANGUAGE: Final = "sanskrit"

#: The API returns at most ten rows per request whatever ``limit`` asks for. Discovered by
#: measurement: a request for 400 rows of an 18-verse sukta returned 10. Paging is therefore
#: mandatory, and a caller that trusted ``limit`` would silently see only the first ten
#: verses of every long hymn.
PAGE_SIZE: Final = 10

_HTTP_TIMEOUT: Final = 45.0

#: Number of structural chapters per Veda, as VedSearch counts them. The Samavedic figure is
#: discovered rather than declared, because the site's Samavedic chapters do not correspond
#: to this corpus's four named collections at all.
CHAPTER_COUNTS: Final[dict[str, int]] = {"RV": 10, "AV": 20, "YV": 40}

#: The middle field of a Yajurvedic ``shlok_id``. Constant at 1 across all 1,975 rows.
YV_CONSTANT_SUKTA: Final = 1

_TRANSLITERATOR = DevanagariToIAST()


def api_url(veda: str, path: str) -> str:
    return f"{API_ROOT}/v1/{API_SLUG[veda]}/shlok{path}"


def audio_endpoint(veda: str, shlok_id: str) -> str:
    """The JSON-wrapped audio document for one verse.

    Not a media URL. See the module docstring: the response is JSON carrying base64.
    """
    return f"{API_ROOT}/v1/attachment/audio/{API_SLUG[veda]}/{shlok_id}/{LANGUAGE}"


def verse_page(veda: str, chapter: int, sukta: int | None, verse: int) -> str:
    """The human page for a verse, for ``source_page``."""
    slug = PAGE_SLUG[veda]
    if sukta is None:
        return f"{SITE_ROOT}/{slug}/{chapter}/{verse}"
    return f"{SITE_ROOT}/{slug}/{chapter}/{sukta}/{verse}"


@dataclass(frozen=True)
class VerseCoordinates:
    """Where one of our passages lives in VedSearch's numbering."""

    veda: str
    chapter: int
    sukta: int | None
    verse: int

    @property
    def shlok_id(self) -> str:
        if self.sukta is None:
            return f"{self.chapter}.{self.verse}"
        return f"{self.chapter}.{self.sukta}.{self.verse}"


def vedsearch_coordinates(veda: str, canonical_key: str) -> VerseCoordinates | None:
    """Map one canonical mantra key to VedSearch's coordinates, or ``None``.

    ``None`` for any key whose shape is not a mantra of a Veda this function knows how to
    place, so an unexpected key produces no record rather than a wrong one.

    The Rigvedic branch is the load-bearing one: ``griffith_page`` converts this corpus's
    inline Valakhilya numbering into the Griffith order VedSearch uses. Without it, 55 of
    Mandala 8's hymns map eleven hymns away from where they belong.
    """
    parts = canonical_key.split(":")
    # The key's own Veda must be the one being mapped. Without this, a five-segment
    # Rigvedic hymn key (``VG:RV:SAK:M01:S001``) satisfies the Yajurvedic branch's length
    # test and comes back as Yajurvedic adhyaya 1 verse 1 -- a wrong-Veda mapping produced
    # by a length check standing in for an identity check.
    if len(parts) < 3 or parts[1] != veda:
        return None
    try:
        if veda == "RV" and len(parts) == 6:
            mandala, sukta, verse = int(parts[3][1:]), int(parts[4][1:]), int(parts[5][1:])
            return VerseCoordinates("RV", mandala, griffith_page(mandala, sukta), verse)
        if veda == "AV" and len(parts) == 6:
            return VerseCoordinates("AV", int(parts[3][1:]), int(parts[4][1:]), int(parts[5][1:]))
        if veda == "YV" and len(parts) == 5:
            # The Yajurveda has no sukta level, but the source still emits a three-part
            # ``shlok_id`` with a constant middle field: every one of its 1,975 rows
            # carries ``sukt_number`` 1. Measured, not assumed.
            return VerseCoordinates("YV", int(parts[3][1:]), YV_CONSTANT_SUKTA, int(parts[4][1:]))
    except ValueError:
        return None
    return None


# ---------------------------------------------------------------------------
# Text identity
# ---------------------------------------------------------------------------

#: Characters that differ between these two editions for text that is word-for-word the
#: same, and that therefore cannot participate in an identity check.
#:
#: Measured on sampled spans across all four Vedas. The two editions disagree on: the
#: leading OM sign, a trailing verse number in parentheses, sandhi word-splitting
#: (``agnim ile`` against ``agnimile``), final anusvara (``mitra``/``mitram``), visarga,
#: avagraha, gemination (``niyacchatu``/``niyachatu``), dandas, and accent marks -- which
#: the two sources write in three different notations. None of those distinguishes one
#: verse from another.
_STRIP_AFTER_FOLD: Final = re.compile(r"[^a-z]")

#: A visarga typed as an ASCII colon, which this corpus does and the source does not.
#:
#: Left alone, the two spellings of one sound reduce differently: a Devanagari visarga
#: survives transliteration as ``h``, while a colon is simply dropped as a non-letter. The
#: skeletons then differ by one letter per visarga in a verse that is word-for-word
#: identical, and 893 of the 1,975 Yajurvedic verses carry at least one.
#:
#: Matched only after a Devanagari character, which is what the corpus actually contains:
#: of 1,452 colons across all four Vedas -- 1,451 Yajurvedic, 1 Samavedic, none in the
#: Rigveda or Atharvaveda -- every one is preceded by a Devanagari character. The
#: look-behind therefore costs nothing today and keeps a genuine ASCII colon in Latin
#: text, which would be punctuation rather than a visarga, from being folded later.
_COLON_VISARGA: Final = re.compile(r"(?<=[ऀ-ॿ]):")

#: U+0903 DEVANAGARI SIGN VISARGA, written as an escape rather than the glyph.
#: The glyph is visually near-identical to an ASCII colon -- which is the entire
#: confusion this fold exists to resolve -- so spelling it out keeps the two apart for
#: a reader as well as for the matcher.
_VISARGA: Final = chr(0x0903)


def skeleton(text: str) -> str:
    """The orthography-insensitive identity of a verse: its letters, and nothing else.

    Devanagari is transliterated first so that a Devanagari source and a Latin one become
    comparable, then combining marks are decomposed away and every non-letter is dropped.

    This is deliberately coarse. It is used to confirm that a recording the source placed
    at a given coordinate really is the verse this corpus holds at the corresponding key --
    a yes/no question about one specific pair -- and not to *search* for a verse among
    others, where a coarse key would risk collision. :func:`skeleton_index` is the one
    place it is used for lookup, and it reports collisions rather than resolving them.
    """
    # The source prefixes many verses with the OM sign; this corpus does not. Removed
    # before transliteration, because afterwards it is the two ordinary letters "om" and
    # indistinguishable from a verse that really begins with that word.
    text = text.replace("ॐ", "")
    # Normalise a colon-spelled visarga to the real sign before transliteration, so the
    # transliterator resolves both spellings by the same path.
    text = _COLON_VISARGA.sub(_VISARGA, text)
    if any(0x0900 <= ord(char) < 0x0980 for char in text):
        text = _TRANSLITERATOR.transliterate(text)
    decomposed = unicodedata.normalize("NFD", text.lower())
    letters = "".join(char for char in decomposed if not unicodedata.combining(char))
    return _STRIP_AFTER_FOLD.sub("", letters)


#: How similar two verse skeletons must be to count as the same verse.
#:
#: Calibrated, not guessed -- and recalibrated after the comparator was fixed.
#:
#: The figures previously recorded here (mispaired median 0.247, maximum 0.462) were
#: measured with :func:`similarity` still subject to SequenceMatcher's autojunk heuristic,
#: which discarded nearly the whole alphabet. They described a broken instrument and are
#: kept only as a warning: a calibration is only as sound as the comparator that produced
#: it, and this one passed review for a long time.
#:
#: Remeasured with ``autojunk=False`` and the colon-visarga fold in place:
#:
#: * Coordinate-aligned pairs, all 1,975 Yajurvedic verses against the source edition:
#:   median 1.0000, 5th percentile 0.9862.
#: * Mispaired pairs, 12,000 random same-Veda pairs across all four recensions:
#:   median 0.2683, p95 0.3820, p99 0.4276, **maximum 0.8413**.
#: * Mispaired pairs reaching this threshold: **0 of 12,000**.
#:
#: So 0.90 still separates the populations cleanly, but the headroom is far smaller than
#: the old figures suggested -- 0.0587 above the worst wrong pair, not the better than
#: double they implied. Fixing the comparator raised wrong pairs as well as right ones.
#:
#: The worst wrong pair is worth knowing: VSM 28.43 against VSM 28.37, two adjacent verses
#: of one adhyaya whose formulaic text genuinely nearly coincides. The near-misses are
#: neighbours, which is exactly the confusion an audio mapping must not make, so do not
#: lower this threshold without remeasuring the neighbour population specifically.
#:
#: The threshold exists at all because the two editions differ on visarga, final anusvara
#: and gemination for text that is word-for-word identical -- differences that survive
#: :func:`skeleton` because they are base letters, not combining marks.
MATCH_THRESHOLD: Final = 0.90

#: A fuzzy match must beat the runner-up by this much to be accepted when searching.
#:
#: Only used for the Samaveda, which has no shared numbering and must be aligned by text
#: alone. The Samaveda repeats material heavily, so "best match" is not enough: if two
#: candidates score nearly the same, neither is established and both are refused.
MATCH_MARGIN: Final = 0.05


def similarity(left: str, right: str) -> float:
    """Ratio of two already-reduced skeletons.

    ``autojunk=False`` is load-bearing, not a preference. SequenceMatcher's heuristic
    treats any element occurring in more than 1% of a sequence longer than 200 elements as
    junk and excludes it from matching. A verse skeleton is 200 to 1,100 characters drawn
    from an alphabet of about thirty letters, so the heuristic discards very nearly the
    whole alphabet: measured on a 285-character skeleton, 17 of its 18 distinct letters
    were dropped. The resulting ratio is not a similarity between the verses at all.

    The effect was invisible because :func:`verse_matches` short-circuits on exact skeleton
    equality, so only genuinely-variant pairs ever reached this function -- which is
    precisely the population the heuristic destroys. One Yajurvedic pair differing in five
    letters out of 269 scored 0.2342 with the heuristic active and 0.9777 without it.
    """
    return difflib.SequenceMatcher(None, left, right, autojunk=False).ratio()


def verse_matches(source_text: str, our_text: str) -> tuple[bool, float]:
    """Whether these two strings are the same verse, and how similar they are.

    Exact skeleton equality short-circuits to 1.0. Otherwise the ratio is compared against
    :data:`MATCH_THRESHOLD`.
    """
    left, right = skeleton(source_text), skeleton(our_text)
    if not left or not right:
        return False, 0.0
    if left == right:
        return True, 1.0
    score = similarity(left, right)
    return score >= MATCH_THRESHOLD, score


def best_text_match(our_text: str, candidates: dict[str, str]) -> tuple[str | None, float, float]:
    """The candidate that best matches ``our_text``, its score, and the runner-up's.

    Returns ``(None, best, second)`` when nothing clears :data:`MATCH_THRESHOLD` or when
    the best does not beat the runner-up by :data:`MATCH_MARGIN` -- an ambiguous match is
    not a match. ``candidates`` maps an identifier to an already-reduced skeleton.
    """
    target = skeleton(our_text)
    if not target:
        return None, 0.0, 0.0
    best_id, best, second = None, 0.0, 0.0
    target_length = len(target)
    for identifier, shape in candidates.items():
        # Length gate first: difflib is the expensive part and a verse half the length of
        # another cannot reach 0.90.
        if not shape or abs(len(shape) - target_length) > target_length * 0.25:
            continue
        score = 1.0 if shape == target else similarity(shape, target)
        if score > best:
            best_id, best, second = identifier, score, best
        elif score > second:
            second = score
    if best < MATCH_THRESHOLD or (best - second) < MATCH_MARGIN:
        return None, best, second
    return best_id, best, second


def skeleton_index(rows: dict[str, str]) -> tuple[dict[str, str], dict[str, int]]:
    """Invert ``{key: text}`` into ``{skeleton: key}``, and count collisions separately.

    Returns the unambiguous index and a map of colliding skeletons to how many keys share
    them. A colliding skeleton is excluded from the index: two verses that reduce to the
    same letters cannot be told apart by this instrument, and picking one would be a guess.
    """
    seen: dict[str, list[str]] = {}
    for key, text in rows.items():
        seen.setdefault(skeleton(text), []).append(key)
    index = {shape: keys[0] for shape, keys in seen.items() if len(keys) == 1}
    collisions = {shape: len(keys) for shape, keys in seen.items() if len(keys) > 1}
    return index, collisions


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------


class VedSearchClient:
    """Minimal, polite client for the two endpoints this product uses."""

    def __init__(self, *, user_agent: str, timeout: float = _HTTP_TIMEOUT) -> None:
        self._user_agent = user_agent
        self._timeout = timeout

    def _post(self, url: str, body: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": self._user_agent},
        )
        with urllib.request.urlopen(request, timeout=self._timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        data = payload.get("data")
        return data if isinstance(data, dict) else {}

    def chapter_page(
        self, veda: str, chapter: int, *, skip: int, sukta: int | None = None
    ) -> tuple[list[dict[str, Any]], int]:
        """One page of a chapter, plus the chapter's total verse count."""
        body: dict[str, Any] = {
            "chapter_number": chapter,
            "language": LANGUAGE,
            "limit": PAGE_SIZE,
            "skip": skip,
        }
        if sukta is not None:
            body["sukt_number"] = sukta
        data = self._post(api_url(veda, "/search/by/chapter"), body)
        rows = data.get("shloks") or []
        total = int(data.get("total_shloks") or 0)
        return list(rows), total

    def chapter_verses(self, veda: str, chapter: int) -> list[dict[str, Any]]:
        """Every verse of one chapter, paged. Empty list for a chapter that does not exist."""
        rows, total = self.chapter_page(veda, chapter, skip=0)
        if not rows:
            return []
        collected = list(rows)
        while len(collected) < total:
            page, _ = self.chapter_page(veda, chapter, skip=len(collected))
            if not page:
                break
            collected.extend(page)
        return collected

    def audio_document(self, veda: str, shlok_id: str) -> dict[str, Any]:
        """The raw audio document for one verse."""
        request = urllib.request.Request(
            audio_endpoint(veda, shlok_id), headers={"User-Agent": self._user_agent}
        )
        with urllib.request.urlopen(request, timeout=self._timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        data = payload.get("data")
        return data if isinstance(data, dict) else {}

    def audio_bytes(self, veda: str, shlok_id: str) -> tuple[bytes, str]:
        """Decoded audio and its content type.

        Raises :class:`ValueError` when the document carries no decodable payload, so a
        caller never serves an empty body as if it were audio.
        """
        document = self.audio_document(veda, shlok_id)
        encoded = document.get("attachment_content_base64")
        if not isinstance(encoded, str) or not encoded:
            raise ValueError(f"no audio payload for {veda} {shlok_id}")
        raw = base64.b64decode(encoded)
        if not raw:
            raise ValueError(f"empty audio payload for {veda} {shlok_id}")
        content_type = str(document.get("content_type") or "audio/mpeg")
        return raw, content_type


def row_coordinates(row: dict[str, Any]) -> tuple[int, int, int] | None:
    """``(chapter, sukta, verse)`` read off the row's own fields.

    Preferred over parsing ``shlok_id``: the id is a formatted string and the fields are
    the data behind it, so indexing on the fields survives a change in how the source
    formats its ids.
    """
    try:
        return (
            int(str(row["chapter_number"]).strip()),
            int(str(row["sukt_number"]).strip()),
            int(str(row["shlok_number"]).strip()),
        )
    except (KeyError, TypeError, ValueError):
        return None


def index_rows(rows: list[dict[str, Any]]) -> dict[tuple[int, int, int], dict[str, Any]]:
    """Index harvested rows by their own coordinates."""
    indexed: dict[tuple[int, int, int], dict[str, Any]] = {}
    for row in rows:
        coordinates = row_coordinates(row)
        if coordinates is not None:
            indexed[coordinates] = row
    return indexed


def has_sanskrit_audio(row: dict[str, Any]) -> bool:
    """Whether the source says a Sanskrit recitation exists for this verse."""
    audio = row.get("audio")
    return bool(isinstance(audio, dict) and audio.get(LANGUAGE))


def row_text(row: dict[str, Any]) -> str:
    """The verse text as the source prints it."""
    return str(row.get("shlok") or "")


def row_shlok_id(row: dict[str, Any]) -> str | None:
    value = row.get("shlok_id")
    return str(value) if value else None


__all__ = [
    "API_ROOT",
    "API_SLUG",
    "CHAPTER_COUNTS",
    "LANGUAGE",
    "MATCH_MARGIN",
    "MATCH_THRESHOLD",
    "PAGE_SIZE",
    "PAGE_SLUG",
    "SITE_ROOT",
    "SOURCE_NAME",
    "YV_CONSTANT_SUKTA",
    "VedSearchClient",
    "VerseCoordinates",
    "audio_endpoint",
    "best_text_match",
    "has_sanskrit_audio",
    "index_rows",
    "row_coordinates",
    "row_shlok_id",
    "row_text",
    "similarity",
    "skeleton",
    "skeleton_index",
    "vedsearch_coordinates",
    "verse_matches",
    "verse_page",
]
