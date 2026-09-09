"""Cross-Veda textual parallels: what the four corpora actually repeat.

The Rigveda, Samaveda, Yajurveda and Atharvaveda share a great deal of text. The Samaveda
is by its own account a songbook of Rigvedic verses; the Yajurveda quotes the Rigveda
throughout its formulae; the Atharvaveda and the Rigveda overlap in whole hymns. Finding
that overlap is the one enrichment result in this layer that is a *fact about the corpus*
rather than a reading of it, and this module is built so that it stays one.

Four things shape the design, all of them measured rather than assumed.

**A cross-script pair can never agree byte for byte.** RV and AV are stored in Latin, SV
and YV in Devanagari. :func:`~vedagraph.enrich.surfaces.reachable_levels` already encodes
that, and this module only ever compares two texts on levels their scripts can reach. The
consequence is reported per edge: an RV/SV identity is a ``SCRIPT_FOLDED`` identity and is
never presented as though the two editions printed the same characters.

**The Samaveda has no word boundaries worth trusting.** It writes ``devirabhistaye``
where the Rigveda writes ``devir abhistaye``. Every token-based signal is therefore weak
for any pair touching SV, so token overlap is recorded on the row and deliberately kept
out of the similarity that decides whether an edge exists. Character 4-grams and the
longest common subsequence carry that decision instead.

**Character n-grams separate this corpus cleanly.** Over 4,000 random RV/AV pairs the
4-gram Jaccard has mean 0.006 and 99th percentile 0.037, while genuine repetitions sit
above 0.45. That gap is what makes cheap candidate generation possible at all: with such
a sparse feature space MinHash banding can be tuned for recall without proposing the
whole 127.8-million-pair cross-Veda product.

**Exact matching finds most of the truth on its own, in linear time.** Bucketing the
20,095 comparable mantras by each surface finds 1,538 identical cross-Veda pairs -- 573
RV/AV, 504 RV/SV, 189 RV/YV, 141 AV/SV, 83 SV/YV, 48 AV/YV -- of which 750 are identical
at or above ``SCRIPT_FOLDED`` (``EXACT_PARALLEL_OF``) and 788 only once word division is
dropped (``VARIANT_OF``). Near-parallel discovery is the smaller, noisier half of the job
and is the only half that is capped.

A defect this module found in a shared contract, since fixed
-----------------------------------------------------------
The Vajasaneyi Yajurveda source writes visarga as an ASCII colon in 893 of its 1,975
mantras. ``build_surfaces`` used to transliterate the *raw* source, so that colon survived
transliteration and was then deleted by the search fold as an editorial separator: the
Devanagari-level surfaces kept the visarga and the script-folded ones silently lost it --
on the only surfaces a cross-script pair can be compared on at all. Folding the colon to
U+0903 *before* transliteration took RV/YV identities from 90 to 189, AV/YV from 21 to 48,
SV/YV from 75 to 83, and the corpus total from 1,404 to 1,538. The fix is in
:mod:`vedagraph.enrich.surfaces`, where it benefits every stage at once, rather than
papered over locally here.

Finding that defect also disproved an assumption :mod:`vedagraph.enrich.surfaces` used to
state: the surfaces are *not* strictly nested in this corpus. A pair can match at
``ACCENT_INSENSITIVE`` and fail at ``SCRIPT_FOLDED``, because the fold is lossy in ways the
Devanagari surface is not. Bucketing per level rather than only on the weakest level is
what makes those pairs survive, and it costs nothing.
"""

from __future__ import annotations

import hashlib
import time
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Final

from vedagraph.enrich.corpus import Corpus, MantraRecord
from vedagraph.enrich.guards import (
    MAX_LSH_BUCKET,
    MAX_NEAR_PARALLEL_EDGES,
    MAX_NEAR_PARALLELS_PER_MANTRA,
    NEAR_PARALLEL_FLOOR,
    NEAR_PARALLEL_STRONG,
    top_k,
)
from vedagraph.enrich.predicates import (
    NodeKind,
    TextualPredicate,
    check_signature,
    reuse_direction,
)
from vedagraph.enrich.provenance import (
    AssertionState,
    EvidenceSpan,
    Provenance,
    RunReport,
    TrustClass,
    run_id,
)
from vedagraph.enrich.records import ParallelRow, veda_pair
from vedagraph.enrich.surfaces import (
    LEVEL_ORDER,
    MatchLevel,
    TextSurfaces,
    levels_reached,
    render_for_display,
    strongest_level,
)

#: Name this stage reports under, and the prefix of every method string it writes.
STAGE: Final = "crossveda-parallels"

#: Every constant below is part of this string, and this string is part of the run id.
#: Changing a band count changes which candidate pairs exist, so it is not a tuning knob
#: that can be turned without the artifacts saying so.
CROSSVEDA_POLICY_VERSION: Final = "vedagraph-crossveda-parallel-v1"

# ---------------------------------------------------------------------------
# Candidate generation
# ---------------------------------------------------------------------------

#: Character n-gram width. Four characters, not two words: see the module docstring.
#: Four rather than five because five is sparser than it needs to be here -- at n=4 the
#: random-pair Jaccard is already 0.006 -- and a shorter gram degrades more gracefully on
#: the short Samavedic verses, whose sandhi-insensitive surface runs to 54 characters at
#: the tenth percentile.
NGRAM_SIZE: Final = 4

#: 32 bands of 3 rows. Chosen by measurement, not by taste. The Samaveda/Yajurveda
#: product is small enough (3.64 million pairs) to brute-force, so it was: 277 pairs have
#: a 4-gram Jaccard of 0.30 or better, and this banding proposes 276 of them and every
#: single one of the 268 at 0.44 or better. 0.44 is the number that has to be perfect,
#: because it is the point below which a pair provably cannot reach
#: :data:`~vedagraph.enrich.guards.NEAR_PARALLEL_FLOOR` -- see
#: :data:`MIN_NGRAM_JACCARD_FOR_FLOOR`. Wider bands start losing those; narrower ones
#: propose tens of thousands more candidates and recover nothing that survives the floor.
MINHASH_PERMUTATIONS: Final = 96
LSH_BANDS: Final = 32
LSH_ROWS: Final = MINHASH_PERMUTATIONS // LSH_BANDS

assert LSH_BANDS * LSH_ROWS == MINHASH_PERMUTATIONS, "banding must consume the signature"

_MERSENNE_PRIME: Final = (1 << 61) - 1
_MAX_HASH: Final = (1 << 32) - 1

# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

#: How the four measurements are fused into the one number that decides an edge.
#:
#: Only two of them are in the blend, and token overlap is not one. The Samaveda writes
#: continuous sandhi, so a genuine RV/SV repetition can have a token Jaccard near zero
#: while being character-identical; a similarity dominated by tokens would report the
#: largest body of real cross-Veda reuse in the corpus as absent. Edit ratio is left out
#: for a different reason: on these strings it tracks the LCS ratio closely, so including
#: it would only reweight, and it is more useful stored as an independent check on the
#: blend than folded into it.
#:
#: Equal weights, because the two signals fail in opposite directions. The n-gram Jaccard
#: is unforgiving about a reordered pada and forgiving about a changed word; the LCS ratio
#: is the reverse. Neither alone can carry a pair over the floor at these weights: an edge
#: needs both.
NGRAM_WEIGHT: Final = 0.5
LCS_WEIGHT: Final = 0.5

assert abs(NGRAM_WEIGHT + LCS_WEIGHT - 1.0) < 1e-9, "similarity must stay in [0, 1]"

#: Two provably lossless prunes, derived from the blend rather than guessed. Since
#: ``similarity = 0.5 * ngram + 0.5 * lcs`` and both terms are bounded by 1, a pair whose
#: n-gram Jaccard is below ``(FLOOR - LCS_WEIGHT) / NGRAM_WEIGHT`` cannot reach the floor
#: however perfect its LCS, and a pair whose length ratio is below the mirror bound cannot
#: either, because ``lcs_ratio`` is bounded above by ``min(len) / max(len)``. Both come out
#: at 0.44. Applying them before the LCS is computed is a pure speed-up with no recall
#: cost, and the counts are reported separately from real floor rejections so the
#: distinction stays visible.
MIN_NGRAM_JACCARD_FOR_FLOOR: Final = (NEAR_PARALLEL_FLOOR - LCS_WEIGHT) / NGRAM_WEIGHT
MIN_LENGTH_RATIO_FOR_FLOOR: Final = (NEAR_PARALLEL_FLOOR - NGRAM_WEIGHT) / LCS_WEIGHT

#: Defensive bound on the LCS input. It does not bind on this corpus -- the longest
#: sandhi-insensitive surface is 1,139 characters -- and it is not needed for speed
#: either, because :func:`lcs_length` is the bit-parallel algorithm and runs a
#: 1,139x1,139 comparison in under a millisecond. It exists so a future corpus with a
#: pathological block-quoted passage degrades to a *reported* truncation rather than to a
#: stalled run. Truncation only ever lowers the numerator, never the denominator, so a
#: truncated pair is under-scored rather than over-scored.
LCS_MAX_CHARS: Final = 4096

#: Evidence quotes are stored, not recomputed, so they are trimmed. Long enough for a
#: whole mantra of ordinary length; short enough that one oversized passage cannot bloat
#: every edge that touches it.
MAX_QUOTE_CHARS: Final = 300


def _permutations() -> list[tuple[int, int]]:
    """Deterministic MinHash coefficients derived from a fixed seed string.

    Same construction as :mod:`vedagraph.lexical.parallels`, and deliberately a separate
    list: that module bands token bigrams within the Rigveda, this one bands character
    4-grams across four corpora, and a shared coefficient table would tie two unrelated
    policies together for no benefit.
    """
    coefficients: list[tuple[int, int]] = []
    for index in range(MINHASH_PERMUTATIONS):
        digest = hashlib.blake2b(
            f"{CROSSVEDA_POLICY_VERSION}:{index}".encode(), digest_size=16
        ).digest()
        multiplier = int.from_bytes(digest[:8], "big") % (_MERSENNE_PRIME - 1) + 1
        addend = int.from_bytes(digest[8:], "big") % _MERSENNE_PRIME
        coefficients.append((multiplier, addend))
    return coefficients


_PERMUTATIONS: Final = _permutations()


def character_ngrams(text: str, size: int = NGRAM_SIZE) -> frozenset[str]:
    """Overlapping character n-grams of a space-free surface.

    A text no longer than ``size`` yields itself, so it stays comparable instead of
    becoming featureless. In practice that never fires here: ``MIN_COMPARABLE_LENGTH``
    is 20.
    """
    if len(text) <= size:
        return frozenset({text} if text else set())
    return frozenset(text[index : index + size] for index in range(len(text) - size + 1))


def _permuted_table(grams: list[str]) -> dict[str, tuple[int, ...]]:
    """Pre-apply every permutation to every distinct n-gram in the corpus.

    The corpus has 20,095 comparable mantras but only 67,674 distinct 4-grams, so each
    permutation is applied 68 thousand times instead of 1.8 million times, and the
    per-document signature collapses to a C-level ``min`` over a transpose. Measured:
    4 seconds to build the table and 7 seconds to sign the corpus, against roughly a
    minute for the naive per-document loop.
    """
    table: dict[str, tuple[int, ...]] = {}
    for gram in grams:
        base = int.from_bytes(hashlib.blake2b(gram.encode("utf-8"), digest_size=4).digest(), "big")
        table[gram] = tuple(
            (multiplier * base + addend) % _MERSENNE_PRIME for multiplier, addend in _PERMUTATIONS
        )
    return table


def _signature(grams: frozenset[str], table: dict[str, tuple[int, ...]]) -> tuple[int, ...]:
    if not grams:
        return tuple([_MAX_HASH] * MINHASH_PERMUTATIONS)
    lanes = zip(*(table[gram] for gram in grams), strict=True)
    return tuple(min(lane) for lane in lanes)


def _candidate_pairs(
    mantras: list[MantraRecord],
    grams: dict[str, frozenset[str]],
    report: RunReport,
) -> list[tuple[str, str]]:
    """Propose cross-Veda pairs worth scoring, in linear time and deterministically.

    Two mantras become candidates when any one of their 32 signature bands agrees.
    Same-Veda collisions are dropped at the bucket rather than filtered afterwards:
    within the Rigveda they are the majority of every bucket, and they are already
    covered by :mod:`vedagraph.lexical.parallels`.

    Oversized buckets are skipped and counted rather than expanded, because a bucket of
    *b* members contributes ``b(b-1)/2`` pairs on its own. On this corpus the cap does not
    fire -- the largest band bucket holds 55 mantras against a cap of 800 -- which is
    itself worth knowing, and is why the largest bucket is reported even when nothing was
    skipped. The whole stage proposes 17,786 cross-Veda candidates out of a 127.8-million
    pair product.
    """
    distinct = sorted({gram for mantra in mantras for gram in grams[mantra.passage_key]})
    table = _permuted_table(distinct)

    buckets: dict[tuple[int, tuple[int, ...]], list[tuple[str, str]]] = defaultdict(list)
    for mantra in mantras:
        signature = _signature(grams[mantra.passage_key], table)
        for band in range(LSH_BANDS):
            window = signature[band * LSH_ROWS : (band + 1) * LSH_ROWS]
            buckets[(band, window)].append((mantra.veda, mantra.passage_key))

    pairs: set[tuple[str, str]] = set()
    largest = 0
    for members in buckets.values():
        largest = max(largest, len(members))
        if len(members) < 2:
            continue
        if len(members) > MAX_LSH_BUCKET:
            report.cap("oversized_lsh_bucket")
            continue
        ordered = sorted(members)
        for index, (left_veda, left_key) in enumerate(ordered):
            for right_veda, right_key in ordered[index + 1 :]:
                if left_veda == right_veda:
                    continue
                pairs.add((left_key, right_key) if left_key < right_key else (right_key, left_key))

    report.notes["largest_lsh_bucket"] = largest
    report.notes["distinct_ngrams"] = len(distinct)
    report.notes["candidate_pairs"] = len(pairs)
    return sorted(pairs)


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PairScores:
    """Four independent measurements of one pair, and the one number that fuses two."""

    token_jaccard: float
    ngram_jaccard: float
    lcs_ratio: float
    edit_ratio: float
    similarity: float

    @property
    def is_strong(self) -> bool:
        return self.similarity >= NEAR_PARALLEL_STRONG


def jaccard(left: frozenset[str], right: frozenset[str]) -> float:
    if not left and not right:
        return 1.0
    union = len(left | right)
    return len(left & right) / union if union else 0.0


def length_ratio(left: str, right: str) -> float:
    """Shorter over longer. An upper bound on :func:`lcs_length` divided by the longer."""
    longest = max(len(left), len(right))
    return min(len(left), len(right)) / longest if longest else 0.0


def lcs_length(left: str, right: str) -> int:
    """Length of the longest common subsequence, bit-parallel.

    The textbook dynamic program costs O(n*m) Python-level loop iterations, which for the
    thousands of pairs that survive the n-gram bound is about a minute of pure interpreter
    overhead. This is the Allison-Dix / Crochemore bit-vector formulation instead: one
    Python integer holds the whole DP row, so the inner loop is a handful of
    arbitrary-precision integer operations per character of ``left`` and the cost is
    O(n*m/64) machine words. Measured at 22 microseconds against 1.0 millisecond for the
    dynamic program on a typical 90x90 comparison, and under a millisecond on the corpus
    maximum of 1,139x1,139.

    The correspondence with the dynamic program is not obvious from the code, so it is not
    taken on trust: ``tests/enrich/test_crossveda.py`` asserts it against a reference
    implementation over randomly generated strings.
    """
    left = left[:LCS_MAX_CHARS]
    right = right[:LCS_MAX_CHARS]
    width = len(right)
    if not width or not left:
        return 0
    positions: dict[str, int] = {}
    for index, character in enumerate(right):
        positions[character] = positions.get(character, 0) | (1 << index)
    full = (1 << width) - 1
    row = full
    for character in left:
        matched = positions.get(character, 0)
        carry = row & matched
        row = ((row + carry) | (row - carry)) & full
    return width - row.bit_count()


def score_pair(
    left: TextSurfaces,
    right: TextSurfaces,
    left_grams: frozenset[str] | None = None,
    right_grams: frozenset[str] | None = None,
) -> PairScores:
    """Measure one pair four ways, then fuse two of them.

    ``edit_ratio`` is :class:`difflib.SequenceMatcher` with ``autojunk`` switched off.
    That is not a detail: autojunk declares any element appearing in more than 1% of a
    sequence longer than 200 elements to be junk, and on a *character* sequence that
    describes the ordinary vowels of Sanskrit. Left on, it reports two long identical
    verses as dissimilar and gives no indication that it has done so.

    The n-gram sets are accepted as arguments because the pipeline has already built them
    for candidate generation and rebuilding them per pair would dominate the stage.
    """
    if left_grams is None:
        left_grams = character_ngrams(left.sandhi_insensitive)
    if right_grams is None:
        right_grams = character_ngrams(right.sandhi_insensitive)
    left_text, right_text = left.sandhi_insensitive, right.sandhi_insensitive
    longest = max(len(left_text), len(right_text))
    ngram = jaccard(left_grams, right_grams)
    lcs = lcs_length(left_text, right_text) / longest if longest else 0.0
    return PairScores(
        token_jaccard=jaccard(frozenset(left.tokens), frozenset(right.tokens)),
        ngram_jaccard=ngram,
        lcs_ratio=lcs,
        edit_ratio=SequenceMatcher(None, left_text, right_text, autojunk=False).ratio(),
        similarity=NGRAM_WEIGHT * ngram + LCS_WEIGHT * lcs,
    )


# ---------------------------------------------------------------------------
# Stage 1: identity
# ---------------------------------------------------------------------------


def identical_pairs(
    mantras: list[MantraRecord],
    by_key: dict[str, MantraRecord],
    report: RunReport,
) -> dict[tuple[str, str], MatchLevel]:
    """Every cross-Veda pair identical on some surface, with the strongest level reached.

    Bucketing, not comparison: each level is one pass over the corpus grouping mantras by
    the value of that surface, so the whole stage is linear in mantras rather than
    quadratic in pairs. Cross-script collisions cannot occur below ``SCRIPT_FOLDED``
    because the two scripts share no code points, but the level a pair is *reported* at
    still comes from :func:`~vedagraph.enrich.surfaces.strongest_level`, which consults
    ``reachable_levels`` rather than trusting that argument.

    Every level is bucketed, not just the weakest one, because the surfaces turn out not
    to be strictly nested -- see the module docstring. Nothing here is capped: an identity
    is a fact about the corpus, and the largest cross-Veda identity bucket holds 15
    mantras, so there would be nothing to cap in any case.
    """
    pairs: dict[tuple[str, str], MatchLevel] = {}
    by_level: dict[str, int] = {}
    largest = 0

    for level in LEVEL_ORDER:
        buckets: dict[str, list[str]] = defaultdict(list)
        for mantra in mantras:
            value = mantra.surfaces.surface(level)
            if value.strip():
                buckets[value].append(mantra.passage_key)
        found = 0
        for members in buckets.values():
            if len(members) < 2 or len({by_key[key].veda for key in members}) < 2:
                continue
            largest = max(largest, len(members))
            ordered = sorted(members)
            for index, left_key in enumerate(ordered):
                for right_key in ordered[index + 1 :]:
                    if by_key[left_key].veda == by_key[right_key].veda:
                        continue
                    found += 1
                    if (left_key, right_key) in pairs:
                        continue
                    strongest = strongest_level(
                        by_key[left_key].surfaces, by_key[right_key].surfaces
                    )
                    if strongest is not None:
                        pairs[(left_key, right_key)] = strongest
        by_level[str(level)] = found

    report.notes["identity_pairs_by_level"] = by_level
    report.notes["largest_identity_bucket"] = largest
    return pairs


def identity_predicate(level: MatchLevel) -> TextualPredicate:
    """Split an identity into "the same verse" and "the same verse, written differently".

    A pair identical only once word boundaries are dropped is not an exact parallel: the
    two editions disagree about where the words are. That is a real transmission fact --
    the Samaveda writes continuous sandhi where the Rigveda spaces by word -- and it is
    788 of the 1,538 identities in this corpus, so collapsing it into ``EXACT_PARALLEL_OF``
    would misdescribe over half the layer.
    """
    if level is MatchLevel.SANDHI_INSENSITIVE:
        return TextualPredicate.VARIANT_OF
    return TextualPredicate.EXACT_PARALLEL_OF


# ---------------------------------------------------------------------------
# Row construction
# ---------------------------------------------------------------------------


def _quote(text: str) -> str:
    """Truncate and render a comparison surface for publication.

    ``render_for_display`` is applied here rather than at the call sites because this is the
    single funnel every evidence quote passes through. Without it the private-use fold
    sentinels reach the artifact and the graph: 88.6% of this stage's rows carried one, and
    since an unassigned code point usually renders as nothing, ``pṛñcatīr`` was published as
    ``pñcatīr``. Rendering must never happen before a comparison -- only on the way out.
    """
    rendered = render_for_display(text)
    if len(rendered) <= MAX_QUOTE_CHARS:
        return rendered
    return rendered[: MAX_QUOTE_CHARS - 3] + "..."


def _row(
    predicate: TextualPredicate,
    subject: MantraRecord,
    object_: MantraRecord,
    *,
    level: MatchLevel,
    reached: tuple[MatchLevel, ...],
    scores: PairScores,
    similarity: float,
    method: str,
    identity: str,
    notes: str,
) -> ParallelRow:
    """Assemble one row, with the evidence and the domain check that every row needs.

    :func:`~vedagraph.enrich.predicates.check_signature` is called per row rather than
    once per predicate. It costs three dictionary lookups, and calling it here means there
    is no code path in this module that can build a row without it.

    The two evidence spans quote the surface the claim was actually decided on, not the
    stored source. For a ``SCRIPT_FOLDED`` identity that means the reader is shown the two
    folded strings and can see they are equal; showing the Devanagari and the Latin source
    instead would look like evidence while proving nothing. The citations are carried in
    ``notes`` so the human-readable reference is not lost.
    """
    check_signature(str(predicate), NodeKind.PASSAGE, NodeKind.PASSAGE)
    evidence = (
        EvidenceSpan(
            locator=subject.passage_key,
            surface=str(level),
            quote=_quote(subject.surfaces.surface(level)),
        ),
        EvidenceSpan(
            locator=object_.passage_key,
            surface=str(level),
            quote=_quote(object_.surfaces.surface(level)),
        ),
    )
    return ParallelRow(
        predicate=str(predicate),
        subject_key=subject.passage_key,
        object_key=object_.passage_key,
        subject_veda=subject.veda,
        object_veda=object_.veda,
        veda_pair=veda_pair(subject.veda, object_.veda),
        # An identity claim, and only that. A near parallel reaches no level, so it must
        # publish an empty match_level rather than naming the surface it was *scored* on:
        # naming it read as "these two texts are identical at SANDHI_INSENSITIVE", which is
        # exactly what a near parallel is not. Left populated, this claimed identity on
        # 4,229 of 6,271 rows and inflated the manifest's identity tally from 2,042 to
        # 5,432. The surface a pair was compared on is recoverable from the method string.
        match_level=str(level) if reached else "",
        levels_reached=tuple(str(item) for item in reached),
        similarity=similarity,
        token_jaccard=scores.token_jaccard,
        ngram_jaccard=scores.ngram_jaccard,
        lcs_ratio=scores.lcs_ratio,
        edit_ratio=scores.edit_ratio,
        provenance=Provenance(
            trust=TrustClass.DETERMINISTIC_DERIVED,
            method=method,
            score=similarity,
            evidence=evidence,
            state=AssertionState.ACCEPTED,
            run_id=identity,
            notes=notes,
        ),
    )


def _reuse_row(
    base: ParallelRow,
    borrower: MantraRecord,
    source: MantraRecord,
    why: str,
) -> ParallelRow:
    """Mirror a symmetric finding as the directed borrowing it also is.

    Emitted only where :func:`~vedagraph.enrich.predicates.reuse_direction` returns a
    direction, which today means only Samaveda to Rigveda. The symmetric row is kept as
    well, because the two say different things: a query for "verses the Samaveda and the
    Rigveda share" should not have to know about the borrowing in order to find them.
    """
    return _row(
        TextualPredicate.REUSES_TEXT_FROM,
        borrower,
        source,
        # The surface the pair was compared on, taken from the base row's evidence rather
        # than from its match_level: match_level is an identity claim and is empty for a
        # near parallel, whereas evidence always records the surface actually used.
        level=MatchLevel(base.provenance.evidence[0].surface),
        reached=tuple(MatchLevel(item) for item in base.levels_reached),
        scores=PairScores(
            token_jaccard=base.token_jaccard,
            ngram_jaccard=base.ngram_jaccard,
            lcs_ratio=base.lcs_ratio,
            edit_ratio=base.edit_ratio,
            similarity=base.similarity,
        ),
        similarity=base.similarity,
        method=f"{STAGE}:reuse:{base.predicate}:{base.match_level}",
        identity=base.provenance.run_id,
        notes=f"{borrower.citation} borrows from {source.citation}. {why}",
    )


# ---------------------------------------------------------------------------
# Stage 5: guards
# ---------------------------------------------------------------------------


def _apply_degree_cap(
    scored: list[tuple[str, str, PairScores]],
    by_key: dict[str, MantraRecord],
    report: RunReport,
) -> list[tuple[str, str, PairScores]]:
    """Keep at most ``MAX_NEAR_PARALLELS_PER_MANTRA`` near parallels per mantra per Veda.

    A pair is kept only when it survives the cut on *both* of its endpoints. The looser
    rule -- keep it if either side wants it -- does not actually bound anything: a refrain
    that is nobody's top five can still collect forty edges from forty mantras that each
    rank it sixth. Intersection makes the cap the degree bound it claims to be, at the
    cost of dropping some asymmetric pairs, and the count of those drops is reported.

    Identity rows never reach this function. They are facts, not rankings.
    """
    per_side: dict[tuple[str, str], list[tuple[float, str]]] = defaultdict(list)
    for left_key, right_key, scores in scored:
        left_veda, right_veda = by_key[left_key].veda, by_key[right_key].veda
        per_side[(left_key, right_veda)].append((scores.similarity, right_key))
        per_side[(right_key, left_veda)].append((scores.similarity, left_key))

    survivors: set[tuple[str, str]] = set()
    for (owner, _other_veda), items in sorted(per_side.items()):
        result = top_k(items, MAX_NEAR_PARALLELS_PER_MANTRA)
        for other in result.kept:
            survivors.add((owner, other))

    kept = [
        pair
        for pair in scored
        if (pair[0], pair[1]) in survivors and (pair[1], pair[0]) in survivors
    ]
    if len(kept) < len(scored):
        report.cap("near_parallels_per_mantra", len(scored) - len(kept))
    return kept


def _apply_edge_ceiling(
    kept: list[tuple[str, str, PairScores]],
    report: RunReport,
) -> tuple[list[tuple[str, str, PairScores]], bool]:
    """Truncate at :data:`~vedagraph.enrich.guards.MAX_NEAR_PARALLEL_EDGES`, loudly.

    The ceiling is a circuit breaker against a change to the candidate generator, not a
    quality filter, so hitting it is reported as an anomaly rather than as a routine cap:
    the run's own notes then say, in words, that the result is incomplete and by how much.
    """
    if len(kept) <= MAX_NEAR_PARALLEL_EDGES:
        return kept, False
    ordered = sorted(kept, key=lambda item: (-item[2].similarity, item[0], item[1]))
    dropped = len(ordered) - MAX_NEAR_PARALLEL_EDGES
    report.cap("max_near_parallel_edges", dropped)
    report.notes["circuit_breaker"] = (
        f"MAX_NEAR_PARALLEL_EDGES ({MAX_NEAR_PARALLEL_EDGES}) was reached and {dropped} "
        "near parallels were discarded. This result is truncated and must not be read as "
        "the complete near-parallel set."
    )
    return ordered[:MAX_NEAR_PARALLEL_EDGES], True


def _directed_reuse_rows(
    rows: list[ParallelRow],
    by_key: dict[str, MantraRecord],
) -> list[ParallelRow]:
    """Add the directed borrowing edge wherever the corpus establishes a direction."""
    extra: list[ParallelRow] = []
    for row in rows:
        direction = reuse_direction(row.subject_veda, row.object_veda)
        if direction is None:
            continue
        borrower_veda, _source_veda, why = direction
        borrows_from_object = row.subject_veda == borrower_veda
        borrower_key = row.subject_key if borrows_from_object else row.object_key
        source_key = row.object_key if borrows_from_object else row.subject_key
        extra.append(_reuse_row(row, by_key[borrower_key], by_key[source_key], why))
    return extra


def _tally(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def discover_cross_veda_parallels(corpus: Corpus) -> tuple[list[ParallelRow], RunReport]:
    """Find every cross-Veda textual parallel the corpus supports, and say what was cut.

    Five stages, cheapest first: bucket for identity, band for candidates, score the
    candidates, classify, then guard. The returned rows are sorted, and every count that
    would otherwise be invisible -- pairs pruned before scoring, pairs below the floor,
    pairs lost to a per-mantra cap -- lands in the report rather than nowhere.

    Deterministic by construction, not by luck. Nothing that reaches the output is read
    out of a set or a dict in iteration order: n-grams are sorted before they are hashed,
    LSH buckets emit sorted members, candidate pairs are returned sorted, the per-mantra
    cap iterates a sorted key list, and the rows are sorted before they are returned. Two
    runs over the same corpus serialise byte for byte.
    """
    started = time.perf_counter()
    report = RunReport(stage=STAGE)
    timings: dict[str, float] = {}

    comparable = [mantra for mantra in corpus.mantras if mantra.surfaces.is_comparable()]
    report.reject("below_min_comparable_length", len(corpus.mantras) - len(comparable))
    by_key = {mantra.passage_key: mantra for mantra in comparable}
    identity = run_id(
        STAGE,
        CROSSVEDA_POLICY_VERSION,
        len(comparable),
        *(f"{veda}={count}" for veda, count in sorted(corpus.counts().items())),
    )

    mark = time.perf_counter()
    identical = identical_pairs(comparable, by_key, report)
    timings["identity_seconds"] = round(time.perf_counter() - mark, 3)

    mark = time.perf_counter()
    grams = {
        mantra.passage_key: character_ngrams(mantra.surfaces.sandhi_insensitive)
        for mantra in comparable
    }
    candidates = _candidate_pairs(comparable, grams, report)
    timings["candidate_seconds"] = round(time.perf_counter() - mark, 3)

    mark = time.perf_counter()
    scored: list[tuple[str, str, PairScores]] = []
    for left_key, right_key in candidates:
        if (left_key, right_key) in identical:
            report.reject("candidate_already_identical")
            continue
        left, right = by_key[left_key], by_key[right_key]
        if jaccard(grams[left_key], grams[right_key]) < MIN_NGRAM_JACCARD_FOR_FLOOR:
            report.reject("below_floor_by_ngram_bound")
            continue
        if (
            length_ratio(left.surfaces.sandhi_insensitive, right.surfaces.sandhi_insensitive)
            < MIN_LENGTH_RATIO_FOR_FLOOR
        ):
            report.reject("below_floor_by_length_bound")
            continue
        scores = score_pair(left.surfaces, right.surfaces, grams[left_key], grams[right_key])
        if scores.similarity < NEAR_PARALLEL_FLOOR:
            report.reject("below_near_parallel_floor")
            continue
        scored.append((left_key, right_key, scores))
    timings["scoring_seconds"] = round(time.perf_counter() - mark, 3)

    mark = time.perf_counter()
    kept, truncated = _apply_edge_ceiling(_apply_degree_cap(scored, by_key, report), report)
    timings["guard_seconds"] = round(time.perf_counter() - mark, 3)

    rows: list[ParallelRow] = []
    for (left_key, right_key), level in identical.items():
        left, right = by_key[left_key], by_key[right_key]
        rows.append(
            _row(
                identity_predicate(level),
                left,
                right,
                level=level,
                reached=levels_reached(left.surfaces, right.surfaces),
                scores=score_pair(left.surfaces, right.surfaces, grams[left_key], grams[right_key]),
                # An identity is an identity. The blend is a ranking device for pairs that
                # are *not* identical, and it reads 0.97 for the 35 pairs that agree in
                # Devanagari but diverge under the Yajurveda visarga defect; recording that
                # as the score would make a certainty look like a guess.
                similarity=1.0,
                method=f"{STAGE}:identity:{level}",
                identity=identity,
                notes=f"{left.citation} == {right.citation} at {level}",
            )
        )

    near_method = f"{STAGE}:near:minhash-char{NGRAM_SIZE}+lcs:{MatchLevel.SANDHI_INSENSITIVE}"
    for left_key, right_key, scores in kept:
        left, right = by_key[left_key], by_key[right_key]
        strength = "strong" if scores.is_strong else "near"
        rows.append(
            _row(
                TextualPredicate.NEAR_PARALLEL_OF,
                left,
                right,
                level=MatchLevel.SANDHI_INSENSITIVE,
                # Deliberately empty: a near parallel is identical at no level at all, and
                # an empty tuple here is the difference between "not the same text" and
                # "the same text, reached weakly".
                reached=(),
                scores=scores,
                similarity=scores.similarity,
                method=near_method,
                identity=identity,
                notes=(
                    f"{left.citation} ~ {right.citation} "
                    f"({strength}, similarity {scores.similarity:.3f})"
                ),
            )
        )

    rows.extend(_directed_reuse_rows(rows, by_key))
    rows.sort(key=lambda row: (row.predicate, row.subject_key, row.object_key))

    report.produced = len(rows)
    report.notes["policy_version"] = CROSSVEDA_POLICY_VERSION
    report.notes["run_id"] = identity
    report.notes["corpus_counts"] = dict(sorted(corpus.counts().items()))
    report.notes["comparable_mantras"] = len(comparable)
    report.notes["lsh"] = {
        "ngram_size": NGRAM_SIZE,
        "permutations": MINHASH_PERMUTATIONS,
        "bands": LSH_BANDS,
        "rows": LSH_ROWS,
        "max_bucket": MAX_LSH_BUCKET,
    }
    report.notes["rows_by_predicate"] = _tally(row.predicate for row in rows)
    report.notes["rows_by_veda_pair"] = _tally(row.veda_pair for row in rows)
    report.notes["rows_by_match_level"] = _tally(row.match_level for row in rows)
    report.notes["near_parallel_edge_ceiling_hit"] = truncated
    timings["total_seconds"] = round(time.perf_counter() - started, 3)
    report.notes["timings"] = timings
    report.notes["surface_contract"] = (
        "893 of 1,975 Yajurveda mantras write visarga as an ASCII colon. "
        "vedagraph.enrich.surfaces folds it to U+0903 before transliterating; without that "
        "fold the identical cross-Veda total is 1,404 rather than 1,538."
    )
    return rows, report
