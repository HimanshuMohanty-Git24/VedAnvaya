"""Within-corpus mantra repetition: exact parallels, then reviewed near parallels.

The Rigveda repeats itself. A refrain closes every stanza of a hymn, a whole stanza
reappears in another Mandala, a pāda is reused with one word changed. This module finds
that repetition deterministically, and is careful about two things.

**"Exact" is not one thing.** Two mantras can be identical once accents are removed and
still differ in the source, or share a lemma sequence while differing in every ending.
Those are different facts. :class:`ParallelMethod` keeps them apart and the strongest
level reached is recorded per pair; the levels are never collapsed into a single
"duplicate" flag.

**No quadratic comparison.** 10,552 mantras would be 55.7 million pairs. Candidate pairs
come from MinHash banding over token shingles, which is linear in the corpus and
deterministic: the hash constants are fixed here, so two runs propose the same pairs in
the same order. Only candidates are scored.

Thresholds are not invented in code. Metrics are computed and stored individually, and a
versioned, documented policy decides which pairs become canonical ``PARALLEL_TO`` edges.
Everything below that bar stays a candidate record.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from uuid import UUID

from vedagraph.identity import uuid_for_urn
from vedagraph.models.enums import (
    LexicalPredicate,
    ParallelMethod,
    ParallelStatus,
    ParallelUnit,
)
from vedagraph.models.lexical import (
    ExactParallelGroup,
    MantraParallel,
    ParallelCandidate,
    ParallelMetrics,
)
from vedagraph.normalize import ComparisonForm, comparison_form, normalize_nfc

PARALLEL_POLICY_VERSION = "rigveda-mantra-parallel-policy-v1"

#: Representation levels, strongest first. A pair is reported at every level it reaches;
#: ``strongest_method`` is the first of these it satisfies.
METHOD_ORDER: tuple[ParallelMethod, ...] = (
    ParallelMethod.SOURCE_EXACT,
    ParallelMethod.NFC_EXACT,
    ParallelMethod.ACCENTLESS_EXACT,
    ParallelMethod.TOKEN_EXACT,
    ParallelMethod.LEMMA_SEQUENCE_EXACT,
)

# --- MinHash configuration. Fixed, and part of the policy version: changing any of
# --- these changes which candidate pairs are generated, so they are not tunable knobs.
MINHASH_PERMUTATIONS = 64
LSH_BANDS = 64
LSH_ROWS = MINHASH_PERMUTATIONS // LSH_BANDS
SHINGLE_SIZE = 2
_MERSENNE_PRIME = (1 << 61) - 1
_MAX_HASH = (1 << 32) - 1

#: A band bucket larger than this is a stop-phrase, not a set of parallels: it would
#: contribute a quadratic number of pairs on its own. Such buckets are skipped and
#: counted, so the omission is visible instead of silently capping recall.
MAX_BUCKET_SIZE = 1200


@dataclass(frozen=True)
class MantraText:
    """Every representation of one mantra the parallel engine compares."""

    passage_key: str
    passage_id: UUID
    citation: str
    mandala: int
    source_text: str
    tokens: tuple[str, ...]
    lemmas: tuple[str, ...]

    @property
    def nfc(self) -> str:
        return normalize_nfc(self.source_text)

    @property
    def accentless(self) -> str:
        return comparison_form(self.source_text, ComparisonForm.SEARCH_NORMALIZED)


@dataclass
class ParallelRunReport:
    """Counts that make the engine's behaviour auditable rather than assumed."""

    candidate_pairs_generated: int = 0
    oversized_buckets_skipped: int = 0
    largest_bucket: int = 0
    exact_pairs: dict[str, int] = field(default_factory=dict)


def _permutations() -> list[tuple[int, int]]:
    """Deterministic MinHash coefficients derived from a fixed seed string.

    Derived rather than hard-coded so the list is readable, and derived from a constant
    so it is identical on every machine and every run.
    """
    coefficients: list[tuple[int, int]] = []
    for index in range(MINHASH_PERMUTATIONS):
        digest = hashlib.blake2b(
            f"{PARALLEL_POLICY_VERSION}:{index}".encode(), digest_size=16
        ).digest()
        multiplier = int.from_bytes(digest[:8], "big") % (_MERSENNE_PRIME - 1) + 1
        addend = int.from_bytes(digest[8:], "big") % _MERSENNE_PRIME
        coefficients.append((multiplier, addend))
    return coefficients


_PERMUTATIONS = _permutations()


def shingles(tokens: tuple[str, ...]) -> frozenset[str]:
    """Overlapping token bigrams, which capture word order that a bag of words loses.

    A one-token mantra has no bigram, so it falls back to the token itself rather than
    becoming uncomparable.
    """
    if len(tokens) < SHINGLE_SIZE:
        return frozenset(tokens)
    return frozenset(
        " ".join(tokens[index : index + SHINGLE_SIZE])
        for index in range(len(tokens) - SHINGLE_SIZE + 1)
    )


def _signature(features: frozenset[str]) -> tuple[int, ...]:
    hashes = [
        int.from_bytes(hashlib.blake2b(item.encode("utf-8"), digest_size=4).digest(), "big")
        for item in features
    ]
    if not hashes:
        return tuple([_MAX_HASH] * MINHASH_PERMUTATIONS)
    return tuple(
        min(((multiplier * value + addend) % _MERSENNE_PRIME) for value in hashes)
        for multiplier, addend in _PERMUTATIONS
    )


def generate_candidate_pairs(
    texts: list[MantraText],
    *,
    report: ParallelRunReport,
) -> list[tuple[str, str]]:
    """Propose pairs worth scoring, in linear time, deterministically.

    Two mantras become a candidate when any one of their ``LSH_BANDS`` signature bands
    is identical. The configuration is 64 bands of one row, i.e. a pair is proposed when
    any single MinHash value agrees. That is the most permissive banding this signature
    length allows, and it was chosen by measurement rather than by taste: brute-forcing
    all 613,278 pairs of Mandala 9 and comparing (see RIGVEDA_PARALLEL_REVIEW.md) it
    recovers every pair the policy would accept *and* every pair worth keeping as a
    candidate, while scoring a small fraction of the pairs.
    """
    signatures = {text.passage_key: _signature(shingles(text.tokens)) for text in texts}
    buckets: dict[tuple[int, tuple[int, ...]], list[str]] = defaultdict(list)
    for key, signature in signatures.items():
        for band in range(LSH_BANDS):
            window = signature[band * LSH_ROWS : (band + 1) * LSH_ROWS]
            buckets[(band, window)].append(key)

    pairs: set[tuple[str, str]] = set()
    for members in buckets.values():
        report.largest_bucket = max(report.largest_bucket, len(members))
        if len(members) < 2:
            continue
        if len(members) > MAX_BUCKET_SIZE:
            report.oversized_buckets_skipped += 1
            continue
        ordered = sorted(members)
        for left_index, left in enumerate(ordered):
            for right in ordered[left_index + 1 :]:
                pairs.add((left, right))
    report.candidate_pairs_generated = len(pairs)
    return sorted(pairs)


def _jaccard(left: frozenset[str], right: frozenset[str]) -> float:
    if not left and not right:
        return 1.0
    union = len(left | right)
    return len(left & right) / union if union else 0.0


def score_pair(left: MantraText, right: MantraText) -> ParallelMetrics:
    """Six independent measurements. They are stored separately, never fused here."""
    left_tokens, right_tokens = frozenset(left.tokens), frozenset(right.tokens)
    left_lemmas, right_lemmas = frozenset(left.lemmas), frozenset(right.lemmas)
    left_text, right_text = left.accentless, right.accentless
    return ParallelMetrics(
        token_jaccard=_jaccard(left_tokens, right_tokens),
        lemma_jaccard=_jaccard(left_lemmas, right_lemmas),
        ordered_token_similarity=SequenceMatcher(None, left.tokens, right.tokens).ratio(),
        normalized_edit_similarity=SequenceMatcher(None, left_text, right_text).ratio(),
        character_ngram_similarity=_jaccard(
            _character_ngrams(left_text), _character_ngrams(right_text)
        ),
        length_ratio=(
            min(len(left.tokens), len(right.tokens)) / max(len(left.tokens), len(right.tokens))
            if left.tokens and right.tokens
            else 0.0
        ),
        shared_token_count=len(left_tokens & right_tokens),
        left_token_count=len(left.tokens),
        right_token_count=len(right.tokens),
    )


def _character_ngrams(text: str, size: int = 4) -> frozenset[str]:
    compact = text.replace(" ", "")
    if len(compact) < size:
        return frozenset({compact} if compact else set())
    return frozenset(compact[index : index + size] for index in range(len(compact) - size + 1))


def find_exact_parallels(
    texts: list[MantraText],
    *,
    report: ParallelRunReport,
) -> tuple[list[ExactParallelGroup], dict[tuple[str, str], list[ParallelMethod]]]:
    """Group mantras identical at each representation level, and record every pair.

    Grouping is by exact bucket, so this is linear. A pair identical at several levels
    appears once, carrying all of them.
    """
    by_key: dict[str, MantraText] = {text.passage_key: text for text in texts}
    groups: list[ExactParallelGroup] = []
    pair_methods: dict[tuple[str, str], list[ParallelMethod]] = defaultdict(list)

    representations: dict[ParallelMethod, dict[str, str]] = {
        ParallelMethod.SOURCE_EXACT: {t.passage_key: t.source_text for t in texts},
        ParallelMethod.NFC_EXACT: {t.passage_key: t.nfc for t in texts},
        ParallelMethod.ACCENTLESS_EXACT: {t.passage_key: t.accentless for t in texts},
        ParallelMethod.TOKEN_EXACT: {t.passage_key: "␟".join(t.tokens) for t in texts},
        ParallelMethod.LEMMA_SEQUENCE_EXACT: {t.passage_key: "␟".join(t.lemmas) for t in texts},
    }

    for method in METHOD_ORDER:
        buckets: dict[str, list[str]] = defaultdict(list)
        for passage_key, value in representations[method].items():
            if value.strip():
                buckets[value].append(passage_key)
        pairs_at_level = 0
        for value, members in sorted(buckets.items()):
            if len(members) < 2:
                continue
            ordered = sorted(members)
            digest = hashlib.blake2b(f"{method.value}:{value}".encode(), digest_size=8).hexdigest()
            groups.append(
                ExactParallelGroup(
                    group_id=f"{method.value}:{digest}",
                    method=method,
                    member_keys=ordered,
                    member_citations=[by_key[key].citation for key in ordered],
                    mandalas=sorted({by_key[key].mandala for key in ordered}),
                    size=len(ordered),
                )
            )
            for left_index, left in enumerate(ordered):
                for right in ordered[left_index + 1 :]:
                    pair_methods[(left, right)].append(method)
                    pairs_at_level += 1
        report.exact_pairs[method.value] = pairs_at_level

    groups.sort(key=lambda group: (METHOD_ORDER.index(group.method), group.group_id))
    return groups, dict(pair_methods)


def strongest(methods: list[ParallelMethod]) -> ParallelMethod:
    return min(methods, key=METHOD_ORDER.index)


# --- Near-parallel acceptance policy ---------------------------------------------
#
# These numbers are the output of the stratified review in
# docs/reports/RIGVEDA_PARALLEL_REVIEW.md, not a guess made while writing the code.
# A pair is accepted as HIGH_CONFIDENCE_NEAR_PARALLEL only when it clears every one of
# them; a single metric cannot carry a pair on its own.
ACCEPT_ORDERED_TOKEN_SIMILARITY = 0.80
ACCEPT_TOKEN_JACCARD = 0.70
ACCEPT_EDIT_SIMILARITY = 0.80
ACCEPT_LENGTH_RATIO = 0.60
ACCEPT_MIN_TOKENS = 4

#: Below this, a pair is not even worth keeping as a candidate for review.
CANDIDATE_ORDERED_TOKEN_SIMILARITY = 0.50


def classify(metrics: ParallelMetrics) -> ParallelStatus:
    """Apply the versioned acceptance policy to one scored pair."""
    if min(metrics.left_token_count, metrics.right_token_count) < ACCEPT_MIN_TOKENS:
        # Very short mantras reach high similarity by accident; they stay candidates.
        return ParallelStatus.CANDIDATE_PARALLEL
    if (
        metrics.ordered_token_similarity >= ACCEPT_ORDERED_TOKEN_SIMILARITY
        and metrics.token_jaccard >= ACCEPT_TOKEN_JACCARD
        and metrics.normalized_edit_similarity >= ACCEPT_EDIT_SIMILARITY
        and metrics.length_ratio >= ACCEPT_LENGTH_RATIO
    ):
        return ParallelStatus.HIGH_CONFIDENCE_NEAR_PARALLEL
    if metrics.ordered_token_similarity >= CANDIDATE_ORDERED_TOKEN_SIMILARITY:
        return ParallelStatus.CANDIDATE_PARALLEL
    return ParallelStatus.REJECTED


def stratum_for(metrics: ParallelMetrics) -> str:
    """Bucket a pair for the stratified review sample."""
    value = metrics.ordered_token_similarity
    for bound in (0.95, 0.90, 0.85, 0.80, 0.70, 0.60, 0.50):
        if value >= bound:
            return f">={bound:.2f}"
    return "<0.50"


def parallel_identity(subject_key: str, object_key: str, predicate: LexicalPredicate) -> UUID:
    urn = (
        f"urn:vedagraph:assertion:{predicate.value.lower()}:"
        f"{subject_key.lower()}:{object_key.lower()}"
    )
    return uuid_for_urn(urn)


def build_parallels(
    texts: list[MantraText],
    *,
    report: ParallelRunReport,
) -> tuple[list[MantraParallel], list[ParallelCandidate], list[ExactParallelGroup]]:
    """Run the whole engine: exact groups, candidate generation, scoring, policy."""
    by_key = {text.passage_key: text for text in texts}
    groups, exact_pairs = find_exact_parallels(texts, report=report)

    parallels: list[MantraParallel] = []
    for (left_key, right_key), methods in exact_pairs.items():
        left, right = by_key[left_key], by_key[right_key]
        parallels.append(
            MantraParallel(
                assertion_id=parallel_identity(
                    left_key, right_key, LexicalPredicate.EXACT_PARALLEL_OF
                ),
                subject_key=left_key,
                subject_id=left.passage_id,
                object_key=right_key,
                object_id=right.passage_id,
                predicate=LexicalPredicate.EXACT_PARALLEL_OF,
                unit=ParallelUnit.MANTRA,
                status=ParallelStatus.EXACT_PARALLEL,
                methods=sorted(set(methods), key=METHOD_ORDER.index),
                strongest_method=strongest(methods),
                metrics=score_pair(left, right),
                parallel_policy_version=PARALLEL_POLICY_VERSION,
                text_version_id="GRETIL.RV.AUFRECHT",
                subject_citation=left.citation,
                object_citation=right.citation,
            )
        )

    candidates: list[ParallelCandidate] = []
    for left_key, right_key in generate_candidate_pairs(texts, report=report):
        if (left_key, right_key) in exact_pairs:
            continue
        left, right = by_key[left_key], by_key[right_key]
        metrics = score_pair(left, right)
        status = classify(metrics)
        if status is ParallelStatus.REJECTED:
            continue
        if status is ParallelStatus.HIGH_CONFIDENCE_NEAR_PARALLEL:
            parallels.append(
                MantraParallel(
                    assertion_id=parallel_identity(
                        left_key, right_key, LexicalPredicate.PARALLEL_TO
                    ),
                    subject_key=left_key,
                    subject_id=left.passage_id,
                    object_key=right_key,
                    object_id=right.passage_id,
                    predicate=LexicalPredicate.PARALLEL_TO,
                    unit=ParallelUnit.MANTRA,
                    status=status,
                    methods=[],
                    metrics=metrics,
                    parallel_policy_version=PARALLEL_POLICY_VERSION,
                    text_version_id="GRETIL.RV.AUFRECHT",
                    subject_citation=left.citation,
                    object_citation=right.citation,
                )
            )
        candidates.append(
            ParallelCandidate(
                candidate_key=f"{left_key}|{right_key}",
                subject_key=left_key,
                object_key=right_key,
                subject_citation=left.citation,
                object_citation=right.citation,
                status=status,
                metrics=metrics,
                stratum=stratum_for(metrics),
            )
        )

    parallels.sort(key=lambda item: (item.subject_key, item.object_key, item.predicate.value))
    candidates.sort(key=lambda item: item.candidate_key)
    return parallels, candidates, groups
