"""Repeated Sanskrit phrases, discovered and promoted to hub nodes.

The Vedas are formulaic. A phrase like ``indraṃ vardhantu no giraḥ`` is not a sentence one
poet wrote once; it is a building block, and the interesting fact about it is the set of
verses that use it. Recorded as passage-to-passage edges that fact costs N-squared edges:
a refrain shared by 236 mantras is 55,460 ordered pairs, for a single phrase. Recorded as
a hub it costs N. Every formula in this module is therefore a node, and the verses that
use it hang off it by ``USES_FORMULA``.

Why the obvious algorithm does not work here
--------------------------------------------
The obvious algorithm is "count word n-grams". It works for three of the four corpora and
fails for the fourth, and the failure is silent, which is the dangerous part.

Measured on the corpus this module runs against:

=====  =======  =================  ==================================================
Veda   mantras  tokens per mantra  word division in the source
=====  =======  =================  ==================================================
RV      10,552               15.1  GRETIL, spaced by word
SV       1,844               10.2  Wikisource, largely continuous sandhi
YV       1,975               15.0  spaced by word
AV       5,839               14.6  GRETIL, spaced by word
=====  =======  =================  ==================================================

The Samaveda's 10.2 is not a fact about Samavedic style. The Samaveda writes
``पाशमस्मदवाधमं`` -- ``pāśam asmad avādhamaṃ``, three words -- as a single token. A
word-n-gram extractor run over the four corpora therefore reports that the Samaveda, which
is by its own construction a songbook of Rigvedic verses and is almost entirely formulaic,
has essentially no formulaic language. That report would be false, and nothing in the
output would reveal it: the Samaveda column would simply be small.

So discovery is split from detection, and they use different surfaces:

* **Discovery** mines word n-grams from ``script_folded``, in every Veda that divides
  words at all (which includes whatever divisions the Samaveda does print). Mining on
  words is what makes the formulas *readable*: a repeated-substring miner over
  sandhi-collapsed text finds spans that begin and end in the middle of words.
* **Detection** searches every candidate as a substring of ``sandhi_insensitive``, in all
  four Vedas. This is what makes the Samaveda visible, and it also catches the cases where
  one Latin-script edition writes joined what another writes apart.

The honest cost of that choice is stated rather than hidden, twice. First, a formula
occurring *only* in the Samaveda and never written with a word break anywhere in the
corpus cannot be discovered at all: there is no word n-gram to mine it from. Second, a
substring hit on sandhi-collapsed text does not prove that the source divides its words
there; it proves the letters are in that order. Those occurrences are recorded with a
different method name and a lower confidence than the word-aligned ones, and the run
report gives the split per Veda, so a reader can see exactly how much of the Samaveda's
coverage rests on the weaker evidence.

Why the mining floor is 2 and not 3
-----------------------------------
:data:`~vedagraph.enrich.guards.MIN_FORMULA_OCCURRENCES` is 3, but candidates are mined at
a document frequency of 2. A phrase written with word breaks only twice may still be
written sandhi-collapsed thirty more times, and mining at 3 would discard it before the
substring pass ever saw it. The final floor of 3 is applied to the *union* of both
detections. The extra cost was measured rather than assumed: 140,930 candidate n-grams at
floor 2 against 32,876 at floor 3, a difference the Apriori pass and the prefix index
absorb without trouble.

Maximality, and the eight-word ceiling
--------------------------------------
A repeated phrase is found once per sub-span, so ``indraṃ vardhantu``, ``vardhantu no`` and
``indraṃ vardhantu no`` all surface as candidates for one piece of phraseology. Only the
longest is kept, and only where the sub-span occurs in exactly the same verses -- a
sub-span used somewhere the longer one is not is a separate fact and survives.

The ceiling needs the same treatment and it is easy to overlook. ``MAX_FORMULA_WORDS`` is
8 because "above eight words a repeated span is a whole verse, which the parallel layer
already records as a parallel"; but stopping the miner at 8 does not stop those verse
repetitions arriving -- it delivers them chopped to their first eight words, which is the
worst of both. So spans of 9 words are mined as *probes*: counted like formulas, allowed
to subsume, never emitted. Measured before the rule existed, 1,238 of the 1,655 emitted
eight-word formulas were windows cut out of longer repetitions.

Surfaces, sentinels, and what is safe to display
------------------------------------------------
``script_folded`` is a *comparison* surface, not a reading. :mod:`vedagraph.normalize`
folds the IAST and ISO 15919 spellings of four sounds onto private-use sentinels -- U+E000
for vocalic r, U+E001 for its long grade, U+E002 for the whole lateral series, U+E003 for
the anusvara -- so that a GRETIL spelling and a VedaWeb spelling compare equal. Storing
that surface in a graph property would put unassigned code points in front of a reader.

Three different strings therefore come out of this module, and they are not
interchangeable:

``formula_id``
    Derived from the sandhi-collapsed folded form. That form is the identity: two word
    divisions of the same letters are one formula, not two.
``normalized``
    The folded form with the sentinels rendered back into IAST. Readable, and lossy in a
    documented way -- the lateral fold cannot tell vocalic *ḷ* from retroflex *ḷ*, so this
    rendering always prints the retroflex, and the ``cch``/``ch`` fold is not undone.
``display_form`` and ``source_forms``
    Real attested spans, taken from the accent-stripped IAST surface of a mantra that
    actually contains the formula, preferring a Latin-script edition so a reader gets
    GRETIL's spelling rather than a transliteration artefact. That surface is token-aligned
    with ``script_folded`` for 20,210 of 20,210 mantras, which is what makes the span
    extraction exact. The printed source surface is *not* token-aligned -- transliteration
    re-divides 566 Yajurveda and 145 Samaveda mantras -- so it is not used for spans.

Known residuals, measured
-------------------------
Two artefacts survive this design and are recorded rather than papered over, because both
originate one layer down and neither can be fixed here without guessing at orthography.

**A word-final visarga lost to sandhi splits one refrain into two nodes.** The Vajasaneyi
edition writes ``pāta svastibhi sadā`` in 3 of its mantras where the other three corpora
write ``pāta svastibhiḥ sadā``. That makes ``pāta svastibhi`` a legitimate word n-gram, and
the substring pass then finds it as a prefix inside all 90 mantras spelling the visarga --
so the corpus's commonest refrain arrives as a 93-mantra node and a 90-mantra node instead
of one. Maximality cannot merge them: their occurrence sets genuinely differ.

**Avagraha is a separator on the comparison surface, so elided initial *a-* becomes its own
token.** ``vedagraph.normalize`` lists the apostrophe in ``SEPARATOR_MARKS``, so GRETIL's
``jātavedó 'gne`` folds to two tokens and ``gne`` is a word. 62 of the 20,210 mantras carry
a bare ``gne`` token that way, out of 1,829 whose source contains an avagraha at all, and
one visible consequence is a formula displayed as ``gne sakhye mā riṣāmā vayaṃ tava``
rather than ``agne …``. The formula and its occurrence set are right; the display form is
missing a letter the edition also did not print.

Determinism
-----------
Every intermediate is sorted before it can reach the output, and no set or dict iteration
order is ever observable. The one place this is easy to get wrong is the cap: two formulas
of equal rank must not swap places between runs, so the rank key ends in the formula's own
collapsed form.
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass
from typing import Final

from vedagraph.enrich.corpus import VEDAS, Corpus
from vedagraph.enrich.guards import (
    MAX_FORMULA_CORPUS_SHARE,
    MAX_FORMULA_EDGES,
    MAX_FORMULA_NODES,
    MAX_FORMULA_WORDS,
    MIN_FORMULA_CHARS,
    MIN_FORMULA_OCCURRENCES,
    MIN_FORMULA_WORDS,
)
from vedagraph.enrich.provenance import (
    AssertionState,
    EvidenceSpan,
    Provenance,
    RunReport,
    TrustClass,
    run_id,
    stable_id,
)
from vedagraph.enrich.records import FormulaOccurrenceRow, FormulaRow
from vedagraph.enrich.surfaces import LATIN, MatchLevel, to_iast
from vedagraph.normalize import ComparisonForm, comparison_form, normalize_nfc
from vedagraph.normalize.unicode import fold_devanagari_source_conventions

STAGE: Final = "formulas"

#: Named on every Formula node. Changing either half of the derivation changes this name,
#: because a formula found by one derivation is not comparable with one found by another.
DERIVATION_METHOD: Final = "word-ngram-apriori-then-sandhi-substring-v1"

#: The source divides its words exactly where the formula does. The strongest evidence a
#: formula occurrence can carry.
OCCURRENCE_METHOD_WORD: Final = "formula-occurrence-word-aligned-v1"

#: The letters are present in that order, but at least one end of the span falls inside a
#: token the source writes as one word. True of most Samavedic occurrences by construction.
OCCURRENCE_METHOD_SANDHI: Final = "formula-occurrence-sandhi-substring-v1"

#: Document frequency an n-gram needs to survive mining. Deliberately lower than
#: ``MIN_FORMULA_OCCURRENCES``; see the module docstring.
CANDIDATE_MINING_FLOOR: Final = 2

#: One word past the ceiling. Spans this long are mined but never emitted; they exist only
#: so that maximality can tell a genuinely maximal eight-word formula from an eight-word
#: window cut out of a longer repetition. See :func:`_apply_maximality`.
_MAXIMALITY_PROBE_WORDS: Final = MAX_FORMULA_WORDS + 1

#: Distinct attested spellings kept per formula. Five is enough to show that a formula is
#: spelled differently by different editions without turning the node into a concordance.
MAX_SOURCE_FORMS: Final = 5

#: Evidence spans stored on a Formula node. Chosen to cover distinct Vedas first, so a
#: cross-Veda formula proves its cross-Veda claim from the node alone.
MAX_EVIDENCE_SPANS: Final = 3

#: Occurrence confidence by detection method. A word-aligned hit is asserted without
#: reservation; a sandhi substring hit is asserted as a letter sequence and no more, and
#: the gap between the two numbers is the size of that reservation.
WORD_ALIGNED_CONFIDENCE: Final = 1.0
SANDHI_SUBSTRING_CONFIDENCE: Final = 0.8

#: Weights of the three components of a formula's distinctiveness score. Rarity dominates
#: because the failure this layer has to avoid is promoting grammar to phraseology.
_RARITY_WEIGHT: Final = 0.5
_LENGTH_WEIGHT: Final = 0.3
_REACH_WEIGHT: Final = 0.2

#: Window used to bucket candidates for the substring pass. Equal to ``MIN_FORMULA_CHARS``,
#: which every candidate's collapsed form is guaranteed to reach, so no candidate needs a
#: fallback path. See :func:`_scan_sandhi` for why this is not an Aho-Corasick automaton.
_PREFIX_LEN: Final = MIN_FORMULA_CHARS

#: Comparison sentinels back to a printable IAST letter. Injective, so rendering cannot
#: merge two distinct folded forms into one ``normalized`` string.
_SENTINEL_TO_IAST: Final[dict[str, str]] = {
    "\ue000": "\u1e5b",  # vocalic r
    "\ue001": "\u1e5d",  # long vocalic r
    "\ue002": "\u1e37",  # the folded lateral series, always printed retroflex
    "\ue003": "\u1e43",  # anusvara
}
_SENTINEL_TABLE: Final = str.maketrans(_SENTINEL_TO_IAST)


def _readable(folded: str) -> str:
    """Render a folded comparison string as printable IAST."""
    return folded.translate(_SENTINEL_TABLE)


#: Devanagari, Vedic Extensions, Devanagari Extended and the private-use area. A span taken
#: from the accent-stripped IAST surface can still carry one of these: U+1CEA VEDIC SIGN
#: ANUSVARA BAHIRGOMUKHA is Unicode category Lo -- a letter, not a mark -- so
#: ``strip_vedic_accents`` leaves it standing and the Vajasaneyi edition writes it where
#: other editions write an anusvara.
_UNREADABLE_IN_IAST: Final[tuple[tuple[int, int], ...]] = (
    (0x0900, 0x097F),
    (0x1CD0, 0x1CFF),
    (0xA8E0, 0xA8FF),
    (0xE000, 0xF8FF),
)


def _is_readable_iast(form: str) -> bool:
    """True if every character of ``form`` can be read as IAST by a person."""
    return not any(
        low <= ord(char) <= high for char in form for low, high in _UNREADABLE_IN_IAST
    )


def _pick_display_form(forms: tuple[str, ...], fallback: str) -> str:
    """The first attested spelling a reader can actually read, else the rendered form.

    ``display_form``'s contract is *a real attested span*, and that was applied without
    checking that the span was readable. Measured on the rebuilt artifact, 26 formulas had
    a display form carrying a raw U+1CEA -- a Devanagari sign published in the middle of an
    IAST label, from the one edition that spells the anusvara that way. The comparison fold
    was corrected for this at commit 3f2b0d8; the *display* surface was not, which is the
    same defect one layer over.

    Preferring a readable attested spelling keeps the contract wherever the corpus allows
    it. Where no attested spelling is readable, the rendered comparison form is printed
    instead: lossy in the documented way, and readable, which a raw Devanagari sign in a
    Latin string is not.
    """
    for form in forms:
        if _is_readable_iast(form):
            return form
    return fallback


@dataclass(frozen=True)
class _View:
    """One mantra, pre-chopped into everything the two passes need.

    Built once because both passes walk every mantra and both need the same three
    alignments: folded tokens (what is mined), display tokens (what is quoted) and the
    character offset of each token in the collapsed text (what maps a substring hit back
    onto whole words).
    """

    index: int
    passage_key: str
    veda: str
    is_latin: bool
    folded_tokens: tuple[str, ...]
    display_tokens: tuple[str, ...]
    collapsed: str
    #: ``len(folded_tokens) + 1`` offsets; the last is ``len(collapsed)``.
    token_starts: tuple[int, ...]


def _build_views(corpus: Corpus) -> tuple[_View, ...]:
    """Derive the per-mantra working surfaces.

    The display surface is the accent-stripped IAST reading rather than the printed
    source, because only the former is token-aligned with ``script_folded``. Measured over
    the whole corpus: 0 of 20,210 mantras disagree on token count between the folded and
    the accent-stripped IAST surfaces, while 711 disagree between the folded surface and
    the printed one, because transliteration re-divides Devanagari at 566 Yajurveda and
    145 Samaveda mantras. The guard below exists for the day a new edition breaks that.
    """
    views: list[_View] = []
    for index, mantra in enumerate(corpus.mantras):
        surfaces = mantra.surfaces
        folded = tuple(surfaces.script_folded.split())
        # fold_devanagari_source_conventions before transliterating, for exactly the reason
        # build_surfaces does it: the accented Vajasaneyi layer types visarga as an ASCII
        # colon, and transliterating first lets the colon be stripped as punctuation
        # instead of folded to a visarga. Omitted here, 1,305 tokens across 824 mantras lost
        # their visarga on the display surface, so 303 formula evidence quotes misquoted
        # their own passage and `pataye namo nama(ḥ)` split into two nodes printing the
        # same display_form.
        iast = comparison_form(
            to_iast(
                fold_devanagari_source_conventions(normalize_nfc(surfaces.source)),
                surfaces.script,
            ),
            ComparisonForm.ACCENT_STRIPPED_COMPARISON,
        )
        display = tuple(iast.split())
        if len(display) != len(folded):
            display = tuple(_readable(token) for token in folded)
        starts = [0]
        for token in folded:
            starts.append(starts[-1] + len(token))
        views.append(
            _View(
                index=index,
                passage_key=mantra.passage_key,
                veda=mantra.veda,
                is_latin=surfaces.script == LATIN,
                folded_tokens=folded,
                display_tokens=display,
                collapsed=surfaces.sandhi_insensitive,
                token_starts=tuple(starts),
            )
        )
    return tuple(views)


def _covering_span(view: _View, start: int, end: int) -> str:
    """The smallest run of whole display words containing collapsed range ``[start, end)``.

    For a word-aligned hit this is the formula exactly. For a sandhi hit it is wider than
    the formula, and deliberately so: quoting the matched letters alone would produce
    fragments like ``mabhiṣṭaye``, which read as a bug rather than as evidence.
    """
    first = bisect.bisect_right(view.token_starts, start) - 1
    last = bisect.bisect_left(view.token_starts, end) - 1
    return " ".join(view.display_tokens[first : last + 1])


def _mine_ngrams(
    views: tuple[_View, ...], report: RunReport
) -> tuple[set[tuple[str, ...]], set[tuple[str, ...]]]:
    """Word n-grams occurring in at least :data:`CANDIDATE_MINING_FLOOR` mantras.

    Apriori, one word length at a time: an n-gram cannot be frequent if its (n-1)-prefix is
    not, so only extensions of surviving grams are ever counted. Without that the nine
    lengths materialise several million dictionary keys; with it the bigram level is the
    largest and every level after it shrinks. Measured on the corpus: 190,746 distinct
    bigrams of which 38,061 survive, falling to 9,472 survivors at eight words.

    Returns the emittable grams and, separately, the over-long probe grams.
    """
    frequent: set[tuple[str, ...]] | None = None
    mined: set[tuple[str, ...]] = set()
    probes: set[tuple[str, ...]] = set()
    for size in range(MIN_FORMULA_WORDS, _MAXIMALITY_PROBE_WORDS + 1):
        counts: dict[tuple[str, ...], int] = {}
        for view in views:
            tokens = view.folded_tokens
            seen: set[tuple[str, ...]] = set()
            for start in range(len(tokens) - size + 1):
                if frequent is not None and tokens[start : start + size - 1] not in frequent:
                    continue
                gram = tokens[start : start + size]
                if gram not in seen:
                    seen.add(gram)
                    counts[gram] = counts.get(gram, 0) + 1
        frequent = {gram for gram, count in counts.items() if count >= CANDIDATE_MINING_FLOOR}
        report.reject("ngram_below_mining_floor", len(counts) - len(frequent))
        if size > MAX_FORMULA_WORDS:
            probes |= frequent
        else:
            mined |= frequent
        if not frequent:
            break
    return mined, probes


def _build_candidates(
    mined: set[tuple[str, ...]], probes: set[tuple[str, ...]], report: RunReport
) -> tuple[frozenset[str], frozenset[str], dict[str, tuple[str, ...]]]:
    """Collapse mined n-grams to their identity form and index them by leading window.

    Two word divisions of the same letters -- ``devīr abhiṣṭaye`` mined from the Rigveda
    and whatever the Samaveda prints -- collapse to one candidate here. That is the point:
    they are one formula, and keeping them apart would emit two hub nodes with identical
    occurrence sets that maximality could not merge, because neither is a strict substring
    of the other.

    ``MIN_FORMULA_CHARS`` is enforced on the collapsed length, not on the spaced one. The
    guard's own reasoning is that a short fold "matches everywhere", and what matches is
    the collapsed form; counting the spaces would let a pair of two-letter words through on
    the strength of the space between them.

    Probe spans are indexed alongside the real candidates -- they have to be counted the
    same way to be comparable -- but are returned as a separate set so nothing downstream
    can emit one. A probe whose letters coincide with a real candidate's is not a probe:
    the candidate wins, because that collapsed form is attested at a legal word count.
    """
    collapsed_forms: set[str] = set()
    for gram in mined:
        collapsed = "".join(gram)
        if len(collapsed) < MIN_FORMULA_CHARS:
            report.reject("candidate_below_char_floor")
            continue
        collapsed_forms.add(collapsed)
    probe_forms = {"".join(gram) for gram in probes} - collapsed_forms
    buckets: dict[str, list[str]] = {}
    for collapsed in sorted(collapsed_forms | probe_forms):
        buckets.setdefault(collapsed[:_PREFIX_LEN], []).append(collapsed)
    return (
        frozenset(collapsed_forms),
        frozenset(probe_forms),
        {key: tuple(value) for key, value in buckets.items()},
    )


@dataclass
class _WordScan:
    """What the word-aligned pass learned about each candidate.

    Only the things that cannot be recovered later: which word division the editions
    actually print, and how each edition spells the span. Occurrence membership is not
    stored, because the substring pass finds a superset of it.
    """

    #: collapsed form -> folded word division -> number of attestations.
    splits: dict[str, dict[tuple[str, ...], int]]
    #: collapsed form -> attested IAST spelling -> number of attestations.
    spellings: dict[str, dict[str, int]]
    #: collapsed form -> spellings attested in a Latin-script edition.
    latin_spellings: dict[str, set[str]]


def _scan_word_aligned(views: tuple[_View, ...], candidates: frozenset[str]) -> _WordScan:
    """Record the printed word division and spelling of every candidate, where one exists.

    Slices the collapsed text between two token offsets rather than joining tokens: the
    join allocates a fresh string for every one of the 2.05 million (mantra, position,
    length) triples, the slice does not.
    """
    scan = _WordScan(splits={}, spellings={}, latin_spellings={})
    for view in views:
        text = view.collapsed
        starts = view.token_starts
        tokens = view.folded_tokens
        for size in range(MIN_FORMULA_WORDS, MAX_FORMULA_WORDS + 1):
            for start in range(len(tokens) - size + 1):
                collapsed = text[starts[start] : starts[start + size]]
                if collapsed not in candidates:
                    continue
                gram = tokens[start : start + size]
                splits = scan.splits.setdefault(collapsed, {})
                splits[gram] = splits.get(gram, 0) + 1
                spelling = " ".join(view.display_tokens[start : start + size])
                spellings = scan.spellings.setdefault(collapsed, {})
                spellings[spelling] = spellings.get(spelling, 0) + 1
                if view.is_latin:
                    scan.latin_spellings.setdefault(collapsed, set()).add(spelling)
    return scan


def _scan_sandhi(
    views: tuple[_View, ...], buckets: dict[str, tuple[str, ...]]
) -> dict[str, list[int]]:
    """Find every candidate in every mantra's sandhi-collapsed text.

    This is the pass that has to be fast and the one that must not acquire a dependency.
    The naive form -- ``candidate in text`` for every pair -- is 140,930 candidates times
    20,210 mantras, about 2.8 billion scans. An Aho-Corasick automaton is the textbook
    answer and is a few hundred lines of trie plus failure links.

    Neither is needed. Every candidate's collapsed form is at least ``MIN_FORMULA_CHARS``
    long, so bucketing candidates by their leading twelve characters and walking each text
    one position at a time turns the problem into 1.76 million dictionary lookups -- the
    total character length of the corpus -- with a handful of verifications behind the
    lookups that hit. Same asymptotics as Aho-Corasick on this input, twenty lines, and no
    new dependency.

    Returns one entry per *hit*, not per mantra, so a formula repeated twice in one verse
    counts twice towards ``occurrence_count`` and once towards ``mantra_count``.
    """
    hits: dict[str, list[int]] = {}
    for view in views:
        text = view.collapsed
        for position in range(len(text) - _PREFIX_LEN + 1):
            bucket = buckets.get(text[position : position + _PREFIX_LEN])
            if bucket is None:
                continue
            for collapsed in bucket:
                if text.startswith(collapsed, position):
                    hits.setdefault(collapsed, []).append(view.index)
    return hits


def _occurrence_span(view: _View, collapsed: str) -> tuple[str, bool]:
    """Quote a formula's occurrence in one mantra, and say whether the words line up.

    Word alignment is decided geometrically rather than by re-running the n-gram scan: a
    collapsed span whose ends both fall on token offsets *is* a word n-gram of that mantra.
    Where a formula occurs more than once in a verse and only one occurrence is
    word-aligned, the aligned one wins, so the stronger evidence is what gets recorded.
    """
    boundaries = frozenset(view.token_starts)
    fallback: tuple[str, bool] | None = None
    position = view.collapsed.find(collapsed)
    while position >= 0:
        end = position + len(collapsed)
        span = _covering_span(view, position, end)
        if position in boundaries and end in boundaries:
            return span, True
        if fallback is None:
            fallback = (span, False)
        position = view.collapsed.find(collapsed, position + 1)
    return fallback if fallback is not None else (_readable(collapsed), False)


@dataclass(frozen=True)
class _Formula:
    """A candidate that survived counting, before maximality and the caps."""

    collapsed: str
    normalized: str
    display_form: str
    source_forms: tuple[str, ...]
    word_count: int
    mantra_indices: tuple[int, ...]
    occurrence_count: int
    veda_counts: dict[str, int]
    max_share: float
    #: False for a maximality probe: counted like a formula, never written out. Its
    #: readable fields are left empty because nothing may read them.
    emit: bool = True

    @property
    def vedas(self) -> tuple[str, ...]:
        return tuple(veda for veda in VEDAS if veda in self.veda_counts)

    @property
    def cross_veda(self) -> bool:
        return len(self.veda_counts) > 1

    @property
    def score(self) -> float:
        """Normalized distinctiveness in [0, 1]. Comparable only against other formulas.

        Three components, each already expressed as a share of its own ceiling:

        * **rarity** -- how far the formula sits below the per-Veda grammar ceiling. A span
          used in 0.1% of a Veda scores near 1; one sitting at the 8% cap scores 0. This
          dominates the weighting because "is this phraseology or is it grammar" is the
          question the score exists to answer.
        * **length** -- word count between the two-word floor and the eight-word ceiling. A
          longer repeated span is less likely to repeat by accident.
        * **reach** -- Vedas represented, over the four there are. A phrase shared between
          corpora is the finding this layer was built for.

        It is a ranking aid, not a probability, and it means nothing against the score of
        any other stage.
        """
        rarity = 1.0 - self.max_share / MAX_FORMULA_CORPUS_SHARE
        span = MAX_FORMULA_WORDS - MIN_FORMULA_WORDS
        length = (self.word_count - MIN_FORMULA_WORDS) / span if span else 0.0
        reach = (len(self.veda_counts) - 1) / (len(VEDAS) - 1)
        raw = _RARITY_WEIGHT * rarity + _LENGTH_WEIGHT * length + _REACH_WEIGHT * reach
        return min(1.0, max(0.0, raw))


def _rank_key(formula: _Formula) -> tuple[int, int, int, str]:
    """Ordering used when a cap binds: cross-Veda first, then reach, then length.

    A lexicographic key rather than a weighted scalar, because the preference order really
    is lexicographic -- a cross-Veda formula outranks a single-Veda one however common the
    latter is -- and a scalar would have to fake that with weights so large they stop
    meaning anything. The last component is the formula's own identity, so two formulas
    tied on everything else cannot swap places between runs.
    """
    return (
        0 if formula.cross_veda else 1,
        -len(formula.mantra_indices),
        -formula.word_count,
        formula.collapsed,
    )


def _assemble(
    views: tuple[_View, ...],
    hits: dict[str, list[int]],
    scan: _WordScan,
    probe_forms: frozenset[str],
    veda_totals: dict[str, int],
    report: RunReport,
) -> list[_Formula]:
    """Turn raw hits into counted formulas and apply the frequency and share floors.

    The corpus-share cap rejects the whole formula rather than the offending Veda's
    occurrences. Keeping the rest would leave a node whose ``veda_counts`` silently omitted
    the Veda where the span is commonest, which is worse than the omission: a reader asking
    "where does this phrase occur" would get an answer wrong by construction and carrying
    no marker that says so.
    """
    formulas: list[_Formula] = []
    for collapsed in sorted(hits):
        emit = collapsed not in probe_forms
        indices = hits[collapsed]
        unique = tuple(sorted(set(indices)))
        if len(unique) < MIN_FORMULA_OCCURRENCES:
            if emit:
                report.reject("below_occurrence_floor")
            continue
        veda_counts: dict[str, int] = {}
        for index in unique:
            veda = views[index].veda
            veda_counts[veda] = veda_counts.get(veda, 0) + 1
        max_share = max(count / veda_totals[veda] for veda, count in veda_counts.items())
        if max_share > MAX_FORMULA_CORPUS_SHARE:
            if emit:
                report.reject("above_corpus_share")
            continue
        if not emit:
            formulas.append(
                _Formula(
                    collapsed=collapsed,
                    normalized="",
                    display_form="",
                    source_forms=(),
                    word_count=_MAXIMALITY_PROBE_WORDS,
                    mantra_indices=unique,
                    occurrence_count=len(indices),
                    veda_counts=veda_counts,
                    max_share=max_share,
                    emit=False,
                )
            )
            continue
        splits = scan.splits.get(collapsed, {})
        best_split = (
            min(splits.items(), key=lambda item: (-item[1], item[0]))[0] if splits else (collapsed,)
        )
        spellings = scan.spellings.get(collapsed, {})
        latin = scan.latin_spellings.get(collapsed, set())
        ordered = sorted(
            spellings.items(), key=lambda item: (item[0] not in latin, -item[1], item[0])
        )
        forms = tuple(form for form, _ in ordered[:MAX_SOURCE_FORMS])
        if not forms:
            forms = (_occurrence_span(views[unique[0]], collapsed)[0],)
        formulas.append(
            _Formula(
                collapsed=collapsed,
                normalized=_readable(" ".join(best_split)),
                display_form=_pick_display_form(forms, _readable(" ".join(best_split))),
                source_forms=forms,
                word_count=len(best_split),
                mantra_indices=unique,
                occurrence_count=len(indices),
                veda_counts=veda_counts,
                max_share=max_share,
            )
        )
    return formulas


def _apply_maximality(formulas: list[_Formula], report: RunReport) -> list[_Formula]:
    """Drop each formula that is a strict substring of a longer one used by the same verses.

    Without this the single phrase ``indraṃ vardhantu no giraḥ`` arrives as up to ten
    nodes -- every sub-span of two to five words that happens to occur nowhere else -- each
    with an identical occurrence set, and the graph gains ten hubs and ten times the edges
    for one piece of phraseology. Requiring the occurrence sets to be *identical* is what
    keeps the rule safe: a sub-formula that also occurs somewhere the longer one does not
    is a genuinely separate fact about the corpus, and it survives.

    Grouping by occurrence set first turns an all-pairs containment test into a test inside
    small groups. Containment is tested on the collapsed form, so a sub-formula written
    with a different word division is still recognised as contained.

    The second half of the rule is the one that is easy to miss. An eight-word span is not
    maximal merely because mining stopped at eight words: if extending it to nine words
    leaves the occurrence set unchanged, what was found is a window cut out of a longer
    repetition, and ``MAX_FORMULA_WORDS`` says that a repetition that long is a verse
    parallel rather than a formula. Probes make that testable without emitting anything
    over the ceiling. Measured on the corpus before this rule existed: 1,238 of the 1,655
    eight-word formulas were such windows, 20% of the whole node set, and dropping them
    took the layer from over the node cap to comfortably under it -- so the rule buys back
    cap space that was being spent on the parallel layer's work.
    """
    grouped: dict[tuple[int, ...], list[_Formula]] = {}
    for formula in formulas:
        grouped.setdefault(formula.mantra_indices, []).append(formula)
    survivors: list[_Formula] = []
    for key in sorted(grouped):
        group = sorted(grouped[key], key=lambda item: (len(item.collapsed), item.collapsed))
        for position, formula in enumerate(group):
            if not formula.emit:
                continue
            container = next(
                (other for other in group[position + 1 :] if formula.collapsed in other.collapsed),
                None,
            )
            if container is not None:
                report.reject(
                    "subsumed_by_maximal_formula" if container.emit else "truncated_by_word_ceiling"
                )
                continue
            survivors.append(formula)
    survivors.sort(key=_rank_key)
    return survivors


def _apply_caps(ranked: list[_Formula], report: RunReport) -> list[_Formula]:
    """Enforce the node and edge ceilings, keeping the highest-ranked formulas.

    Both caps drop whole formulas. Dropping individual edges under the edge cap would look
    cheaper and would corrupt the nodes: a Formula whose ``mantra_count`` says 40 while 12
    ``USES_FORMULA`` edges exist is a node lying about its own occurrence set, and every
    aggregate query over the layer would then be wrong in a way no reader could detect.
    """
    kept = ranked
    if len(kept) > MAX_FORMULA_NODES:
        report.cap("formula_nodes", len(kept) - MAX_FORMULA_NODES)
        kept = kept[:MAX_FORMULA_NODES]
    edges = 0
    for position, formula in enumerate(kept):
        if edges + len(formula.mantra_indices) > MAX_FORMULA_EDGES:
            report.cap("formula_nodes_dropped_for_edge_cap", len(kept) - position)
            report.cap(
                "occurrence_edges",
                sum(len(later.mantra_indices) for later in kept[position:]),
            )
            return kept[:position]
        edges += len(formula.mantra_indices)
    return kept


def _formula_evidence(views: tuple[_View, ...], formula: _Formula) -> tuple[EvidenceSpan, ...]:
    """Up to three quoted occurrences, spread across Vedas before being filled in order."""
    chosen: list[int] = []
    seen: set[str] = set()
    for index in formula.mantra_indices:
        if len(chosen) >= MAX_EVIDENCE_SPANS:
            break
        veda = views[index].veda
        if veda not in seen:
            seen.add(veda)
            chosen.append(index)
    for index in formula.mantra_indices:
        if len(chosen) >= MAX_EVIDENCE_SPANS:
            break
        if index not in chosen:
            chosen.append(index)
    spans: list[EvidenceSpan] = []
    for index in sorted(chosen):
        view = views[index]
        quote, aligned = _occurrence_span(view, formula.collapsed)
        level = MatchLevel.SCRIPT_FOLDED if aligned else MatchLevel.SANDHI_INSENSITIVE
        spans.append(EvidenceSpan(locator=view.passage_key, surface=str(level), quote=quote))
    return tuple(spans)


def discover_formulas(
    corpus: Corpus,
) -> tuple[list[FormulaRow], list[FormulaOccurrenceRow], RunReport]:
    """Discover repeated Sanskrit phrases and the passages that use them.

    Returns the Formula nodes, one ``USES_FORMULA`` occurrence row per (formula, passage),
    and the report of what was thrown away. Output is sorted by the formula's ``normalized``
    form and, within a formula, by passage key -- a content ordering rather than a rank
    ordering, so adding one formula to the corpus does not reshuffle the artifact and
    destroy the diff.

    ``cross_veda`` and ``veda_counts`` are filled on every row rather than computed by the
    caller, because "which formulas cross corpora" and "how is formulaic language
    distributed across the four Vedas" are the two questions this layer exists to answer,
    and both should be one property read away.
    """
    report = RunReport(stage=STAGE)
    identifier = run_id(STAGE, len(corpus.mantras), DERIVATION_METHOD)
    views = _build_views(corpus)
    veda_totals = corpus.counts()

    mined, probes = _mine_ngrams(views, report)
    candidates, probe_forms, buckets = _build_candidates(mined, probes, report)
    scan = _scan_word_aligned(views, candidates)
    hits = _scan_sandhi(views, buckets)

    formulas = _assemble(views, hits, scan, probe_forms, veda_totals, report)
    before_maximality = sum(1 for item in formulas if item.emit)
    formulas = _apply_maximality(formulas, report)
    collapsed_count = before_maximality - len(formulas)
    formulas = _apply_caps(formulas, report)
    formulas.sort(key=lambda item: item.normalized)

    formula_rows: list[FormulaRow] = []
    occurrence_rows: list[FormulaOccurrenceRow] = []
    method_counts: dict[str, int] = {"word_aligned": 0, "sandhi_substring": 0}
    per_veda: dict[str, dict[str, int]] = {
        veda: {"word_aligned": 0, "sandhi_substring": 0} for veda in VEDAS
    }

    for formula in formulas:
        formula_id = stable_id("formula", formula.collapsed)
        formula_rows.append(
            FormulaRow(
                formula_id=formula_id,
                normalized=formula.normalized,
                display_form=formula.display_form,
                word_count=formula.word_count,
                char_count=len(formula.normalized),
                occurrence_count=formula.occurrence_count,
                mantra_count=len(formula.mantra_indices),
                vedas=formula.vedas,
                veda_counts=dict(sorted(formula.veda_counts.items())),
                cross_veda=formula.cross_veda,
                source_forms=formula.source_forms,
                derivation_method=DERIVATION_METHOD,
                provenance=Provenance(
                    trust=TrustClass.DETERMINISTIC_DERIVED,
                    method=DERIVATION_METHOD,
                    score=formula.score,
                    evidence=_formula_evidence(views, formula),
                    state=AssertionState.ACCEPTED,
                    run_id=identifier,
                    notes=(
                        "Score is a distinctiveness rank, not a probability: "
                        "0.5*(1 - max per-Veda share / cap) + 0.3*length + 0.2*reach."
                    ),
                ),
            )
        )
        for index in formula.mantra_indices:
            view = views[index]
            quote, aligned = _occurrence_span(view, formula.collapsed)
            level = MatchLevel.SCRIPT_FOLDED if aligned else MatchLevel.SANDHI_INSENSITIVE
            bucket_name = "word_aligned" if aligned else "sandhi_substring"
            method_counts[bucket_name] += 1
            per_veda[view.veda][bucket_name] += 1
            occurrence_rows.append(
                FormulaOccurrenceRow(
                    formula_id=formula_id,
                    passage_key=view.passage_key,
                    veda=view.veda,
                    source_form=quote,
                    provenance=Provenance(
                        trust=TrustClass.DETERMINISTIC_DERIVED,
                        method=(OCCURRENCE_METHOD_WORD if aligned else OCCURRENCE_METHOD_SANDHI),
                        score=(WORD_ALIGNED_CONFIDENCE if aligned else SANDHI_SUBSTRING_CONFIDENCE),
                        evidence=(
                            EvidenceSpan(locator=view.passage_key, surface=str(level), quote=quote),
                        ),
                        state=AssertionState.ACCEPTED,
                        run_id=identifier,
                        notes=(
                            ""
                            if aligned
                            else "Letters matched on the sandhi-collapsed surface; the "
                            "source does not divide its words at both ends of the span."
                        ),
                    ),
                )
            )

    report.produced = len(formula_rows)
    report.notes = {
        "run_id": identifier,
        "derivation": DERIVATION_METHOD,
        "candidate_mining_floor": CANDIDATE_MINING_FLOOR,
        "ngrams_mined": len(mined),
        "maximality_probe_ngrams": len(probes),
        "maximality_probe_forms": len(probe_forms),
        "candidates_after_char_floor": len(candidates),
        "forms_with_any_hit_including_probes": len(hits),
        "formulas_before_maximality": before_maximality,
        "formulas_collapsed_by_maximality": collapsed_count,
        "cross_veda_formulas": sum(1 for row in formula_rows if row.cross_veda),
        "formulas_by_veda": {
            veda: sum(1 for row in formula_rows if veda in row.veda_counts) for veda in VEDAS
        },
        "occurrence_edges": len(occurrence_rows),
        "occurrences_by_method": method_counts,
        "occurrences_by_veda": {veda: dict(per_veda[veda]) for veda in VEDAS},
        "mantras_covered": len({row.passage_key for row in occurrence_rows}),
        "corpus_counts": dict(sorted(veda_totals.items())),
    }
    return formula_rows, occurrence_rows, report
