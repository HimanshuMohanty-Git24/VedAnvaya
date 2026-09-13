"""Derived statistics over the enriched graph, as aggregates rather than edges.

The brief asks for six co-occurrence statistics -- Rishi/Devata, Devata/Chandas,
Devata/Concept, Lemma/Devata, Concept/Veda, Formula/Veda -- and then says the thing that
matters most about them: "Do not necessarily create pairwise edges for every statistic."

That instruction is load-bearing. Materialising Rishi/Devata co-occurrence as edges adds
about 1,400 relationships that carry no information the graph does not already hold: every
one of them is derivable by a two-hop traversal from the ``HAS_RISHI`` and ``HAS_DEVATA``
edges that produced it. What it *does* add is a second copy of the same fact that can go
stale, and a plausible-looking edge that a reader cannot tell from a source assertion.

So these are computed, written to their own artifact, and reported. They are read by the
report generator and by the insight queries; they are not loaded into Neo4j as edges. The
one exception is ``DEVATA_ASSOCIATED_WITH``, which is *not* a statistic -- it is a
hand-curated claim in the concept registry about which deity a concept relates to, and it
is the join between two ontologies that must otherwise stay separate.

Every number here is a count over deterministic inputs, so the whole module is
reproducible and none of it is a claim about meaning.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from vedagraph.enrich.corpus import Corpus, MantraRecord
from vedagraph.enrich.records import (
    ConceptAssertionRow,
    ConceptRow,
    FormulaOccurrenceRow,
    FormulaRow,
    ParallelRow,
)


@dataclass(frozen=True)
class PairStat:
    """One co-occurrence cell, with enough context to be interpretable on its own.

    ``support`` is the raw count. ``subject_total`` and ``object_total`` are the marginals,
    which is what stops the table being read wrongly: Agni co-occurs with Gayatri more than
    any other deity does, and also occurs more than any other deity does, so the raw count
    alone says nothing. ``lift`` is the ratio of observed to expected under independence,
    and it is the column worth sorting on.
    """

    subject: str
    object: str
    support: int
    subject_total: int
    object_total: int
    lift: float

    def as_row(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "object": self.object,
            "support": self.support,
            "subject_total": self.subject_total,
            "object_total": self.object_total,
            "lift": round(self.lift, 6),
        }


def _pair_stats(
    pairs: Iterable[tuple[str, str]],
    universe: int,
    *,
    min_support: int = 2,
) -> list[PairStat]:
    """Turn a stream of co-occurring (subject, object) pairs into a ranked table.

    ``min_support`` of 2 drops the long tail of singletons, which in this corpus is most of
    the table by row count and none of it by interest: a Rishi credited with one hymn
    co-occurs once with each of its deities and produces a maximal lift that means nothing.
    """
    joint: Counter[tuple[str, str]] = Counter()
    subject_totals: Counter[str] = Counter()
    object_totals: Counter[str] = Counter()
    for subject, object_ in pairs:
        joint[(subject, object_)] += 1
        subject_totals[subject] += 1
        object_totals[object_] += 1

    stats: list[PairStat] = []
    for (subject, object_), support in joint.items():
        if support < min_support:
            continue
        expected = (subject_totals[subject] * object_totals[object_]) / universe if universe else 0
        stats.append(
            PairStat(
                subject=subject,
                object=object_,
                support=support,
                subject_total=subject_totals[subject],
                object_total=object_totals[object_],
                lift=(support / expected) if expected else 0.0,
            )
        )
    stats.sort(key=lambda s: (-s.support, -s.lift, s.subject, s.object))
    return stats


def rishi_devata(corpus: Corpus) -> list[PairStat]:
    """Which seers are credited with hymns to which deities.

    Rigveda only: no other corpus in this project carries an anukramani, so a reader
    comparing this table across Vedas would conclude the Samaveda has no seers rather than
    that the source has no seer field. :func:`coverage_report` states that explicitly.
    """
    pairs = [
        (rishi, devata)
        for mantra in corpus.mantras
        for rishi in mantra.rishis
        for devata in mantra.devatas
    ]
    return _pair_stats(pairs, universe=len(corpus.mantras))


def devata_chandas(corpus: Corpus) -> list[PairStat]:
    """Which deities are addressed in which metres."""
    pairs = [
        (devata, chandas)
        for mantra in corpus.mantras
        for devata in mantra.devatas
        for chandas in mantra.chandas
    ]
    return _pair_stats(pairs, universe=len(corpus.mantras))


def devata_concept(corpus: Corpus, assertions: Sequence[ConceptAssertionRow]) -> list[PairStat]:
    """Which concepts appear in passages addressed to which deities.

    Distinct from the curated ``DEVATA_ASSOCIATED_WITH`` link in the concept registry, and
    the difference is the point of having both: the registry says Agni-the-deity relates to
    fire-the-concept because a person decided so, while this table says the passages
    addressed to Agni are the ones where the fire vocabulary occurs, because they are.
    """
    concepts_by_passage: dict[str, list[str]] = defaultdict(list)
    for assertion in assertions:
        concepts_by_passage[assertion.passage_key].append(assertion.concept_id)
    pairs = [
        (devata, concept)
        for mantra in corpus.mantras
        for devata in mantra.devatas
        for concept in concepts_by_passage.get(mantra.passage_key, ())
    ]
    return _pair_stats(pairs, universe=len(corpus.mantras))


def concept_by_veda(assertions: Sequence[ConceptAssertionRow]) -> list[dict[str, Any]]:
    """Concept distribution across the four Vedas, one row per concept."""
    by_concept: dict[str, Counter[str]] = defaultdict(Counter)
    for assertion in assertions:
        by_concept[assertion.concept_id][assertion.veda] += 1
    ranked = sorted(by_concept.items(), key=lambda item: (-sum(item[1].values()), item[0]))
    return [
        {
            "concept_id": concept_id,
            "total": sum(counts.values()),
            "vedas": sorted(counts),
            "veda_counts": dict(sorted(counts.items())),
            "cross_veda": len(counts) > 1,
        }
        for concept_id, counts in ranked
    ]


def formula_by_veda(formulas: Sequence[FormulaRow]) -> list[dict[str, Any]]:
    """Formula distribution across the four Vedas, one row per formula."""
    ranked = sorted(formulas, key=lambda f: (-f.occurrence_count, f.formula_id))
    return [
        {
            "formula_id": formula.formula_id,
            "display_form": formula.display_form,
            "total": formula.occurrence_count,
            "vedas": list(formula.vedas),
            "veda_counts": dict(sorted(formula.veda_counts.items())),
            "cross_veda": formula.cross_veda,
        }
        for formula in ranked
    ]


def lemma_devata(corpus: Corpus, mentions: Iterable[tuple[str, str]]) -> list[PairStat]:
    """Which lemmas occur in passages addressed to which deities.

    ``mentions`` is a stream of ``(passage_key, lemma)`` from the existing deterministic
    lexical layer. Passed in rather than read here, so this module has one input shape and
    the caller owns the file paths.
    """
    devatas_by_passage = {m.passage_key: m.devatas for m in corpus.mantras}
    pairs = [
        (lemma, devata)
        for passage_key, lemma in mentions
        for devata in devatas_by_passage.get(passage_key, ())
    ]
    return _pair_stats(pairs, universe=len(corpus.mantras), min_support=3)


def cross_veda_matrix(parallels: Sequence[ParallelRow]) -> dict[str, dict[str, int]]:
    """The relationship matrix: counts per Veda pair, per predicate, plus distinct pairs.

    The core deliverable of this release. Keyed by the sorted pair label so ``RV-SV`` and
    ``SV-RV`` are one cell, which is what makes the six-cell matrix six cells.

    Each cell also carries ``distinct_pairs``, and it is not decoration. ``REUSES_TEXT_FROM``
    mirrors a symmetric row rather than adding a finding: every one of the 1,684 RV-SV reuse
    edges restates an EXACT, VARIANT or NEAR row as a directed borrowing. So the RV-SV
    predicate counts sum to 3,368 relationships over 1,684 distinct passage pairs, and a
    reader totalling the predicate columns counts every Samavedic borrowing twice. Reporting
    both numbers is the only way the table is safe to add up.
    """
    matrix: dict[str, Counter[str]] = defaultdict(Counter)
    pairs: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for row in parallels:
        matrix[row.veda_pair][row.predicate] += 1
        pairs[row.veda_pair].add(tuple(sorted((row.subject_key, row.object_key))))  # type: ignore[arg-type]
    return {
        pair: {**dict(sorted(counts.items())), "distinct_pairs": len(pairs[pair])}
        for pair, counts in sorted(matrix.items())
    }


def formula_sharing_matrix(
    formulas: Sequence[FormulaRow], occurrences: Sequence[FormulaOccurrenceRow]
) -> dict[str, int]:
    """Per Veda pair, how many formulas occur in both.

    Computed from the formula's own per-Veda counts rather than by joining occurrences
    pairwise: the latter is quadratic in occurrences per formula and produces the same
    number.
    """
    del occurrences  # Present for symmetry with the other matrix builders.
    shared: Counter[str] = Counter()
    for formula in formulas:
        present = sorted(formula.vedas)
        for i, first in enumerate(present):
            for second in present[i + 1 :]:
                shared[f"{first}-{second}"] += 1
    return dict(sorted(shared.items()))


def concept_connection_matrix(
    assertions: Sequence[ConceptAssertionRow],
) -> dict[str, int]:
    """Per Veda pair, how many concepts are attested in both.

    A "concept connection" between two Vedas is a concept both of them talk about. Counted
    at concept granularity, not assertion granularity: a concept attested 900 times in the
    Rigveda and twice in the Yajurveda is one bridge, not eighteen hundred.
    """
    vedas_by_concept: dict[str, set[str]] = defaultdict(set)
    for assertion in assertions:
        vedas_by_concept[assertion.concept_id].add(assertion.veda)
    shared: Counter[str] = Counter()
    for vedas in vedas_by_concept.values():
        present = sorted(vedas)
        for i, first in enumerate(present):
            for second in present[i + 1 :]:
                shared[f"{first}-{second}"] += 1
    return dict(sorted(shared.items()))


def coverage_report(
    corpus: Corpus,
    concepts: Sequence[ConceptRow],
    assertions: Sequence[ConceptAssertionRow],
) -> dict[str, Any]:
    """What each layer actually covers, per Veda, including where it covers nothing.

    Written because every coverage gap in this corpus has a source-level cause that a bare
    count hides: the Samaveda has no English translation at all, so an English-evidence
    concept assertion is impossible for it; only the Rigveda has an anukramani, so three of
    the four Vedas contribute nothing to the Rishi and Chandas tables. Reporting those as
    zeros without the reason invites the conclusion that the enrichment failed.
    """
    per_veda: dict[str, dict[str, Any]] = {}
    assertions_by_veda: Counter[str] = Counter(a.veda for a in assertions)
    passages_with_concept: dict[str, set[str]] = defaultdict(set)
    for assertion in assertions:
        passages_with_concept[assertion.veda].add(assertion.passage_key)

    for veda, mantras in _group_by_veda(corpus.mantras).items():
        total = len(mantras)
        translated = sum(1 for m in mantras if m.has_translation)
        with_metadata = sum(1 for m in mantras if m.devatas)
        covered = len(passages_with_concept.get(veda, ()))
        per_veda[veda] = {
            "mantras": total,
            "with_translation": translated,
            "translation_coverage": round(translated / total, 4) if total else 0.0,
            "with_traditional_metadata": with_metadata,
            "concept_assertions": assertions_by_veda.get(veda, 0),
            "mantras_with_a_concept": covered,
            "concept_coverage": round(covered / total, 4) if total else 0.0,
        }

    return {
        "concepts_defined": len(concepts),
        "per_veda": dict(sorted(per_veda.items())),
        "known_source_gaps": {
            "SV": "no English translation in any source, so English-evidence concept "
            "assertions are impossible; Sanskrit evidence only",
            "SV/YV/AV": "no anukramani in any source, so Rishi, Devata and Chandas tables "
            "are Rigveda-only and their zeros are source gaps, not enrichment failures",
        },
    }


def _group_by_veda(mantras: Sequence[MantraRecord]) -> dict[str, list[MantraRecord]]:
    grouped: dict[str, list[MantraRecord]] = defaultdict(list)
    for mantra in mantras:
        grouped[mantra.veda].append(mantra)
    return dict(sorted(grouped.items()))
