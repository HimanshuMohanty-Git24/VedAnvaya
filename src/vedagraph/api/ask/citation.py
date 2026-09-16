"""Citation validation: every id in the answer must name an item in the packet.

The packet is closed before synthesis, so this check is decidable rather than heuristic:
either an id is in the packet or the model produced it. An id that is not there is
*removed from the prose* and reported, not merely flagged -- a footnote saying "one
citation could not be verified" beside prose that still carries `[E9]` leaves the reader
to work out which sentence is unsupported.

**Quotes are checked against their own item, not the packet.** A model can cite a real id
and attach Sanskrit that item does not contain, which is the harder failure: the citation
resolves, so a reader who follows it sees a real verse and assumes the quote came from it.
:func:`verify_quotes` compares any Devanagari or IAST run in the answer against the
sanskrit and translation fields of the items the answer cited.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Final

from vedagraph.api.ask.evidence import EvidencePacket
from vedagraph.api.ask.models import CitationRef, EvidenceItem, EvidenceItemType
from vedagraph.normalize.unicode import strip_vedic_accents

#: Bracket pairs a model may use to delimit a citation, as ``(open, close)``.
#:
#: More than ASCII because the prompt asks for ``[E1]`` and models comply approximately.
#: Three vendors were observed producing three different spellings: Gemini groups ids inside
#: one pair (``[E6, E7, E8, E9]``), ``gpt-oss-120b`` on Groq emits CJK fullwidth brackets
#: (``【E1】``), and ``nemotron-3-ultra`` on OpenRouter uses round parentheses (``(E11)``).
#: All are correct citations by intent, and a pattern
#: that knows only ``[`` scored both as *uncited* -- which does not merely lose a link:
#: support grading is citation-derived, so a properly grounded answer was reported
#: ``INSUFFICIENT_EVIDENCE`` with an empty citation list. That is a worse failure than a
#: missing footnote, because it tells the reader the graph had nothing to say.
#:
#: Being permissive about the delimiter is safe because the *content* test is strict: a
#: group contributes nothing unless it contains a bare ``E<digits>`` token.
_BRACKET_PAIRS: Final[tuple[tuple[str, str], ...]] = (
    ("[", "]"),
    ("【", "】"),  # 【 】 fullwidth, emitted by gpt-oss
    ("〚", "〛"),  # 〚 〛
    ("［", "］"),  # noqa: RUF001 - U+FF3B/U+FF3D, fullwidth square brackets
    # Third vendor, same cause. nemotron-3-ultra writes (E11). Q20 of the round-four
    # benchmark answered "Which Veda does not mention Agni?" with per-corpus counts and the
    # markers (E11), (E5), (E6, E12), and was scored uncited with status
    # INSUFFICIENT_EVIDENCE -- the failure the docstring above predicts.
    #
    # Round brackets are riskier than square ones, because prose is full of them. The strict
    # content test is what makes it safe: a group contributes nothing without a bare
    # E<digits> token, so "(the pressed plant)" and "(1990)" match nothing.
    ("(", ")"),
)

_CITATION_GROUP: Final = re.compile(
    "|".join(
        f"{re.escape(open_)}([^{re.escape(open_)}{re.escape(close)}]{{0,120}}?){re.escape(close)}"
        for open_, close in _BRACKET_PAIRS
    )
)

_ID_IN_GROUP: Final = re.compile(r"\bE(\d+)\b")


def _group_body(match: re.Match[str]) -> str:
    """The inside of whichever bracket alternative matched.

    The pattern is an alternation of one capturing group per bracket pair, so exactly one
    group is non-None per match.
    """
    for group in match.groups():
        if group is not None:
            return group
    return ""


def extract_cited_ids(text: str) -> list[str]:
    """Every evidence id the text cites, in first-appearance order, deduplicated.

    The single definition of "what this answer cited", shared by the synthesizer's
    support grading and this module's audit. Two implementations would drift, and the one
    that drifted low would grade an answer on citations the other had already rejected.
    """
    found: list[str] = []
    for group in _CITATION_GROUP.finditer(text):
        for match in _ID_IN_GROUP.finditer(_group_body(group)):
            found.append(f"E{match.group(1)}")
    return list(dict.fromkeys(found))


#: A run of Devanagari, long enough to be a quotation rather than a stray sign.
#: Any run of whitespace, collapsed before comparison. See :func:`_normalise`.
_WHITESPACE: Final = re.compile(r"\s+")

_DEVANAGARI_RUN: Final = re.compile(r"[ऀ-ॿ][ऀ-ॿ\s॑-॔]{3,}")

#: The IAST diacritics that mark a Latin word as transliterated Sanskrit.
#:
#: Both cases, and the uppercase half is *derived* rather than typed out. A hand-written
#: second list is how this drifted in the first place: the class held only lowercase, so
#: every Sanskrit word that begins with a capitalised diacritic -- which is most proper
#: nouns a reader would quote -- behaved wrongly in two different ways at once.
#: ``Āraṇyaka`` was reported as the fragment ``raṇyaka``, because matching could not begin
#: at the capital and started at the next letter instead; and ``Ṛgvedic`` and ``Śaunaka``
#: were not audited *at all*, because after excluding the capital nothing left in the word
#: carried a mark. The first is a false alarm a reader sees named in a caveat; the second
#: is a silent gap in coverage, which is worse. ``ç`` is included for the older
#: transliteration of ``ś`` that some editions use.
_IAST_MARKS_LOWER: Final = "āīūṛṝḷḹṅñṇṃṁṭḍḥśṣēōç"
_IAST_MARKS: Final = _IAST_MARKS_LOWER + _IAST_MARKS_LOWER.upper()

#: Vedic pitch accents, which the transmitted Rigvedic and Atharvavedic Sanskrit carries
#: *inline*: all 10,552 Rigvedic and all 5,839 Atharvavedic primary texts are accented.
#: They are letters of a quoted word, not boundaries between words. Omitting them split
#: ``puróhitaṃ`` at its acute into ``hitaṃ`` -- which still matched by substring, so it
#: raised no false alarm, but it meant the run reported to a reader was a fragment of the
#: word they actually wrote. Both precomposed forms and the combining marks are listed
#: because the corpus carries both.
_VEDIC_ACCENTS: Final = "áàéèíìóòúùÁÀÉÈÍÌÓÒÚÙ̀́̂̃"

_SANSKRIT_LETTERS: Final = f"A-Za-z{_IAST_MARKS}{_VEDIC_ACCENTS}"

#: One transliterated Sanskrit word: Latin letters, at least one of them diacritical.
#: A word of bare ASCII is English and must not enter a run.
_IAST_WORD: Final = rf"[{_SANSKRIT_LETTERS}]*[{_IAST_MARKS}{_VEDIC_ACCENTS}][{_SANSKRIT_LETTERS}]*"

#: A quoted Sanskrit run: consecutive words that are *each* transliterated Sanskrit.
#:
#: The per-word requirement is the whole point, and its absence was a defect. The previous
#: pattern ended in ``[A-Za-z<marks>\s]{3,}`` -- plain Latin letters *and* whitespace -- so
#: it ran past the Sanskrit word into the English after it: "names the ṛtvijam priest"
#: yielded the run ``ṛtvijam priest``. That composite appears in no evidence item, because
#: it is not a quotation, so :func:`verify_quotes` reported it unverified and
#: ``AskService`` attached "the answer contains Sanskrit that does not appear in the
#: evidence it cited" to an answer that had quoted correctly. A false alarm on this caveat
#: is expensive: it tells a researcher to distrust a citation that was sound.
#:
#: Requiring a diacritic in every word of the run stops at the first English word while
#: still matching genuine multi-word quotations, where every word carries marks.
_IAST_RUN: Final = re.compile(rf"{_IAST_WORD}(?:\s+{_IAST_WORD})*")

#: Item types that carry no quotable text, so a quote check against them is vacuous.
_UNQUOTABLE: Final = frozenset(
    {
        EvidenceItemType.LEXICAL_PRESENCE,
        EvidenceItemType.CORPUS_DISTRIBUTION,
        EvidenceItemType.METRIC,
        EvidenceItemType.GRAPH_PATH,
    }
)


@dataclass
class CitationAudit:
    citations: list[CitationRef] = field(default_factory=list)
    invented_ids: list[str] = field(default_factory=list)
    """Ids the answer cited that the packet does not contain."""
    unverified_quotes: list[str] = field(default_factory=list)
    """Sanskrit in the answer that appears nowhere in the packet. Possibly fabricated."""
    uncited_quotes: list[str] = field(default_factory=list)
    """Sanskrit that *is* in the packet, but only in an item the answer did not cite.

    A citation-precision slip, not a fabrication: the wording is real and was retrieved.
    Kept apart from :attr:`unverified_quotes` so the response does not tell a reader to
    distrust a genuine quotation.
    """
    cleaned_answer: str = ""

    @property
    def is_clean(self) -> bool:
        """No fabricated ids and no Sanskrit from outside the packet.

        ``uncited_quotes`` deliberately does not count: the answer quoted real retrieved
        text and merely pointed at the wrong id, which is worth reporting but is not a
        reason to treat the answer as unsound.
        """
        return not self.invented_ids and not self.unverified_quotes


def _normalise(text: str) -> str:
    """Comparison form for quote checking: NFC, case-folded, Vedic accents removed.

    Accent-folding is not cosmetic, it is what makes this check usable. The transmitted
    Sanskrit carries pitch accents inline -- all 10,552 Rigvedic and all 5,839
    Atharvavedic primary texts are accented -- while a model quoting a phrase writes it
    unaccented, as scholarly prose normally does. Comparing the two literally made
    ``ṛtvijam`` fail against the stored ``ṛtvijám``, so a *correct* quotation from RV
    1.1.1 was reported as Sanskrit that appears in no cited evidence. Every accented verse
    in the corpus would have produced that false alarm, on the one caveat whose whole job
    is to tell a reader when not to trust a quotation.

    Only tone marks are folded. Diacritics that distinguish phonemes -- ``ṛ``, ``ṣ``,
    ``ā`` -- survive, so a genuinely different word still fails to match.

    Whitespace is collapsed for the same reason and it is not cosmetic either. The stored
    Sanskrit keeps the verse's own line breaks -- a two-pada mantra is held with a newline
    between the padas -- while a model quoting it reflows the two lines into one. Compared
    literally, a verbatim quotation of a two-line verse fails on the newline alone, and
    the reader is told the Sanskrit "may not be a quotation from this corpus at all"
    about text copied out of the corpus.
    """
    folded = strip_vedic_accents(unicodedata.normalize("NFC", text)).lower()
    return _WHITESPACE.sub(" ", folded).strip()


def _describe(item: EvidenceItem) -> str:
    """A human-readable label for a citation, preferring the canonical locus."""
    if item.citation:
        return item.citation
    if item.entity_label:
        return item.entity_label
    if item.claim_source:
        return f"interpretive claim ({item.claim_source})"
    return item.type.value


def _quotable_text(items: list[EvidenceItem]) -> str:
    return " ".join(
        _normalise(part)
        for item in items
        if item.type not in _UNQUOTABLE
        for part in (item.sanskrit, item.translation, item.claim_text, item.fact)
        if part
    )


#: Trimmed from the ends of a matched run before it is compared or reported.
#:
#: Whitespace is in this set because the Devanagari pattern admits ``\s`` inside a run --
#: a verse's own line breaks belong to the quotation -- so a match ending at a paragraph
#: break carries the newlines with it. A set containing the space character does not
#: remove a newline, and the surviving ``\n\n`` made a byte-exact quotation of
#: SV ARANYA 1.1 fail its containment check: the answer was told to distrust the verse it
#: had copied correctly out of the evidence.
_RUN_EDGE_CHARS: Final = " \t\r\n.,;:!?-\u2013\u2014"


def _sanskrit_runs(answer: str) -> list[str]:
    runs: list[str] = []
    for pattern in (_DEVANAGARI_RUN, _IAST_RUN):
        for match in pattern.finditer(answer):
            # Stripping a *set* of edge characters is the intent here, not a
            # prefix/suffix substring, so the multi-character argument is correct.
            run = match.group(0).strip(_RUN_EDGE_CHARS)
            if len(run) >= 4:
                runs.append(run)
    return list(dict.fromkeys(runs))


def verify_quotes(answer: str, cited: list[EvidenceItem]) -> list[str]:
    """Sanskrit runs in the answer that occur in none of the cited items.

    Compared after NFC normalisation, case folding and Vedic-accent folding, and only
    against items that carry text. A run matching any cited item's sanskrit, translation
    or claim text passes: the answer need not say which of several cited verses a phrase
    came from.
    """
    haystack = _quotable_text(cited)
    if not haystack:
        return []
    return [run for run in _sanskrit_runs(answer) if _normalise(run) not in haystack]


def classify_quotes(
    answer: str, cited: list[EvidenceItem], packet_items: list[EvidenceItem]
) -> tuple[list[str], list[str]]:
    """Split unverified Sanskrit into ``(absent_from_packet, uncited_but_retrieved)``.

    Two findings of very different weight were being reported as one. A run absent from
    the *whole packet* may be fabricated, and a reader should distrust it. A run that is
    in the packet but only in an item the answer did not cite is a citation-precision
    slip: the wording is real and retrieved, and the answer simply pointed at the wrong
    id. Observed live -- the model quoted *devam ṛtvijam* from RV 1.1.1 while citing the
    formula-family and parallel items instead of the passage.

    Collapsing them told a reader to distrust a genuine quotation, which is the same
    false-alarm cost the accent folding in :func:`_normalise` exists to avoid. The caller
    words a different caveat for each.
    """
    cited_text = _quotable_text(cited)
    packet_text = _quotable_text(packet_items)

    absent: list[str] = []
    uncited: list[str] = []
    for run in _sanskrit_runs(answer):
        folded = _normalise(run)
        if cited_text and folded in cited_text:
            continue
        if packet_text and folded in packet_text:
            uncited.append(run)
        else:
            absent.append(run)
    return absent, uncited


def _rewrite_citations(answer: str, invented: frozenset[str]) -> str:
    """Normalise every citation group to ASCII, dropping any invented ids.

    Runs on *every* answer, not only when something was invented. Normalisation is the
    load-bearing half: the frontend renders each marker as a clickable chip by parsing
    ASCII ``[E1]``, so a model that writes ``【E1】`` -- which ``gpt-oss-120b`` does --
    produced an answer whose citation appeared in the page as inert literal text. The
    link was verified, present in ``citations`` and completely unreachable to the reader.
    Emitting one spelling here means the marker format is a property of this API rather
    than of whichever vendor answered.

    Group-aware because a plain ``replace("[E9]", "")`` cannot touch the ``E9`` inside
    ``[E6, E7, E9]`` -- it would leave the fabricated id in the prose while the caveat
    claimed it had been removed. A group that loses every id is removed entirely;
    a group that keeps some is rewritten with only those.
    """

    def rewrite(match: re.Match[str]) -> str:
        ids = [f"E{m.group(1)}" for m in _ID_IN_GROUP.finditer(_group_body(match))]
        if not ids:
            # Not a citation group at all -- some other bracketed text. Left alone.
            return match.group(0)
        kept = [cid for cid in ids if cid not in invented]
        if not kept:
            return ""
        # Normalised to ASCII brackets: whatever spelling the model chose, the reader and
        # the frontend's marker parser see one form.
        return "[" + ", ".join(kept) + "]"

    cleaned = _CITATION_GROUP.sub(rewrite, answer)
    cleaned = re.sub(r" {2,}", " ", cleaned)
    cleaned = re.sub(r"\s+([.,;:)])", r"\1", cleaned)
    return cleaned.strip()


def audit(answer: str, packet: EvidencePacket) -> CitationAudit:
    """Validate every citation and quotation in the answer against the packet."""
    by_id = packet.by_id()
    cited_ids = extract_cited_ids(answer)

    citations: list[CitationRef] = []
    invented: list[str] = []
    cited_items: list[EvidenceItem] = []

    for cid in cited_ids:
        item = by_id.get(cid)
        if item is None:
            invented.append(cid)
            continue
        cited_items.append(item)
        citations.append(
            CitationRef(
                id=cid,
                citation=_describe(item),
                passage_key=item.passage_key,
                veda=item.veda,
            )
        )

    # Always rewritten, for two reasons that share one pass: invented markers are removed
    # from the prose rather than annotated beside it, and every surviving marker is
    # normalised to ASCII so the frontend can render it as a chip.
    cleaned = _rewrite_citations(answer, frozenset(invented))
    absent, uncited = classify_quotes(answer, cited_items, packet.items)

    return CitationAudit(
        citations=citations,
        invented_ids=invented,
        unverified_quotes=absent,
        uncited_quotes=uncited,
        cleaned_answer=cleaned,
    )
