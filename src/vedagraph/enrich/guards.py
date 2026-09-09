"""Caps and thresholds that stop the enrichment layer from eating the graph.

Every stage in this layer is a similarity computation over 20,210 mantras, and every one
of them will happily emit a hundred million edges if asked. That is not a hypothetical:
all-pairs over the corpus is 204 million ordered pairs, a 3-token formula appears in
thousands of verses, and a concept lexicon matched loosely enough will attach every
concept to every passage.

An unbounded graph is not a more complete graph. It is a graph in which nothing is
findable, every query times out, and the true 1,369 cross-Veda repetitions are buried
under noise that looks exactly like them. So the caps here are part of the contract, not
tuning knobs, and three rules apply to all of them:

1. **A cap that fires is reported.** Every stage records what it dropped and why, in its
   :class:`~vedagraph.enrich.provenance.RunReport`. A silently truncated result set is
   indistinguishable from a small one.
2. **Top-K beats a threshold sweep.** Keeping the K strongest connections per node bounds
   the graph by construction, at a size that does not depend on how similar the corpus
   happens to be.
3. **A cap is not a filter for quality.** Anything dropped by a cap is dropped for being
   *numerous*, not for being wrong, and the count of drops is the honest measure of what
   the layer is not showing.

The numbers below are stated with the reasoning that produced them. Changing one changes
which edges exist, so each is part of ``PIPELINE_VERSION``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

# ---------------------------------------------------------------------------
# Cross-Veda parallels
# ---------------------------------------------------------------------------

#: Similarity below which a pair is not a parallel at all, only two verses in the same
#: register. Measured on the corpus: at 0.60 the RV/AV candidate set is dominated by pairs
#: sharing nothing but ``indra``, ``soma`` and a case ending. Pairs below this are counted
#: and discarded, never stored.
NEAR_PARALLEL_FLOOR: Final = 0.72

#: A pair at or above this is reported as a near parallel rather than a candidate. Set
#: from the existing within-Rigveda parallel policy, which uses the same scale, so the two
#: layers do not disagree about what "high confidence" means.
NEAR_PARALLEL_STRONG: Final = 0.85

#: Most connections kept per mantra per Veda pair. A mantra genuinely repeated across
#: Vedas has a handful of counterparts; a mantra with forty is a refrain, and storing all
#: forty buries the real ones. Refrains stay discoverable through the Formula layer, which
#: is the right shape for a many-to-many repetition.
MAX_NEAR_PARALLELS_PER_MANTRA: Final = 5

#: Hard ceiling on near-parallel edges for the whole run. Not expected to bind -- it is a
#: circuit breaker, so that a change to the candidate generator cannot quietly multiply
#: the graph by ten.
MAX_NEAR_PARALLEL_EDGES: Final = 40_000

#: A MinHash band bucket larger than this is a stop-phrase, not a family of parallels: on
#: its own it would contribute a quadratic number of candidate pairs. Skipped and counted.
MAX_LSH_BUCKET: Final = 800

# ---------------------------------------------------------------------------
# Formulas
# ---------------------------------------------------------------------------

#: Word count bounds for a formula. One word is a lexeme -- the Lemma layer already has it,
#: and ``agni`` is not a formula. Above eight words a repeated span is a whole verse, which
#: the parallel layer already records as a parallel.
MIN_FORMULA_WORDS: Final = 2
MAX_FORMULA_WORDS: Final = 8

#: A formula must appear in at least this many distinct mantras. Two occurrences is a
#: coincidence of sandhi as often as it is a formula.
MIN_FORMULA_OCCURRENCES: Final = 3

#: Character length floor. Two very short words fold to a handful of letters and match
#: everywhere; this is the same reasoning as ``MIN_COMPARABLE_LENGTH`` one level down.
MIN_FORMULA_CHARS: Final = 12

#: A span occurring in more than this share of a Veda is that Veda's grammar, not its
#: phraseology. Applied per Veda so a Samaveda refrain is judged against the Samaveda.
MAX_FORMULA_CORPUS_SHARE: Final = 0.08

#: Ceiling on Formula nodes. The point of the Formula node is to *replace* combinatorial
#: passage-to-passage edges with a hub; a hundred thousand hubs would defeat that.
MAX_FORMULA_NODES: Final = 6_000

#: Ceiling on USES_FORMULA edges. Each is one passage using one formula, so this bounds
#: the layer at roughly five formulas per mantra on average.
MAX_FORMULA_EDGES: Final = 120_000

# ---------------------------------------------------------------------------
# Concepts
# ---------------------------------------------------------------------------

#: The concept layer is deliberately small. A concept that needs a hundred siblings to be
#: expressed is a lexicon entry, and the Lemma layer already is one.
MAX_CONCEPT_NODES: Final = 150

#: Concepts attached to one passage. A mantra about everything is about nothing; past four
#: the weakest are dropped, counted, and left to the lexical layer to express.
MAX_CONCEPTS_PER_PASSAGE: Final = 4

#: Ceiling on concept assertions across the run.
MAX_CONCEPT_ASSERTIONS: Final = 60_000

# ---------------------------------------------------------------------------
# Semantic candidates
# ---------------------------------------------------------------------------

#: Passages offered to model-based extraction in one release. Bounded on purpose: the
#: brief forbids an unbounded full-corpus extraction, and an LLM layer's value here is
#: demonstrating the contract, not covering the corpus.
MAX_SEMANTIC_PASSAGES: Final = 400

#: Assertions one passage may contribute. A model asked for relations will produce as many
#: as it is allowed to.
MAX_SEMANTIC_ASSERTIONS_PER_PASSAGE: Final = 6


@dataclass(frozen=True)
class TopKResult[T]:
    """What survived a top-K cut, and how much did not."""

    kept: tuple[T, ...]
    dropped: int


def top_k[T](
    items: list[tuple[float, T]],
    k: int,
    *,
    tiebreak: bool = True,
) -> TopKResult[T]:
    """Keep the ``k`` highest-scoring items, deterministically.

    Ties are broken on the item's own ordering, not on input order, because input order
    depends on dict iteration and would make the graph differ between runs while every
    score stayed identical. That is the exact failure mode that makes a "reproducible"
    pipeline quietly non-reproducible.
    """
    if k < 0:
        raise ValueError("k must not be negative")
    ordered = sorted(items, key=lambda pair: (-pair[0], pair[1]) if tiebreak else -pair[0])
    return TopKResult(kept=tuple(item for _, item in ordered[:k]), dropped=max(0, len(ordered) - k))
