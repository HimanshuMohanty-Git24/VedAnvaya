"""Measure the extraction against hand-annotated gold, and price what it cost.

Four things live here because they answer the same question — is this pipeline good
enough to run over ten thousand mantras? — from four directions.

**Gold metrics.** Precision and recall for entities and relations, broken down by
predicate, plus the error classes that matter operationally: assertions with no support
in the gold, wrong entity, wrong predicate, evidence that does not check out. Precision
is reported *per predicate* because the acceptance policy is per predicate; a global
average would hide a predicate at 60% behind one at 99% and unlock both.

**Restraint.** A gold annotation may record a relation as ``rejected``: tempting, and not
supported by the text. Producing one is a *false positive that a naive evaluation would
never see*, because it is not simply "absent from gold". Counting these separately is the
only way to measure whether the model declines when it should.

**Parallel consistency.** Two mantras with identical Sanskrit that get different
extractions are not necessarily wrong — context differs — but a high disagreement rate
means the extractor is unstable, and that is a property of the extractor rather than of
the text. Reported, never used to copy assertions between parallels.

**Cost.** From the API's own usage numbers. Never estimated when a real figure exists,
and a projection to the full corpus is labelled as a projection.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from vedagraph.models.semantic import (
    GoldAnnotation,
    SemanticAssertionCandidate,
    SemanticValidationResult,
    TokenUsage,
)
from vedagraph.semantic.ontology import Explicitness, SemanticPredicate
from vedagraph.semantic.registry import normalize_label

#: Readiness target for a predicate to be unlocked for automatic acceptance. Not a knob:
#: lowering it to make a run pass would make the number meaningless, and the correct
#: response to missing it is to restrict the auto-accepted predicate set instead.
PRECISION_TARGET = 0.95
EVALUATION_VERSION = "rigveda-semantic-evaluation-v1"

#: The annotator field a generated worksheet row carries. A row still holding it has not
#: been annotated by anyone, and :func:`load_gold_annotations` refuses to score against
#: it. This is the guard that stops an empty worksheet from being read as "the model
#: proposed things and the gold says none of them are there", which would report a
#: precision of zero and be just as wrong as reporting one.
UNANNOTATED = "UNANNOTATED"


def load_gold_annotations(path: Path) -> dict[str, GoldAnnotation]:
    """Read hand-annotated gold, skipping worksheet rows nobody has filled in yet.

    Returns only annotated mantras. An entirely unannotated worksheet yields an empty
    mapping, and an empty gold set unlocks no predicate — which is the correct outcome:
    the pipeline is not measured, so nothing it produces may be accepted automatically.
    """
    if not path.exists():
        return {}
    annotations: dict[str, GoldAnnotation] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if str(row.get("annotator", UNANNOTATED)) == UNANNOTATED:
            continue
        annotation = GoldAnnotation.model_validate(row)
        annotations[annotation.passage_key] = annotation
    return annotations


@dataclass(frozen=True)
class PredicateScore:
    """Precision and recall for one predicate, with the counts they came from."""

    predicate: SemanticPredicate
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    #: Predicted relations the gold explicitly marked as tempting-but-unsupported.
    rejected_hits: int = 0

    @property
    def predicted(self) -> int:
        return self.true_positives + self.false_positives

    @property
    def precision(self) -> float | None:
        return self.true_positives / self.predicted if self.predicted else None

    @property
    def recall(self) -> float | None:
        expected = self.true_positives + self.false_negatives
        return self.true_positives / expected if expected else None

    @property
    def meets_target(self) -> bool:
        precision = self.precision
        return precision is not None and precision >= PRECISION_TARGET


@dataclass
class GoldReport:
    """Everything measured against the gold subset."""

    passage_count: int = 0
    entity_true_positives: int = 0
    entity_false_positives: int = 0
    entity_false_negatives: int = 0
    relation_scores: dict[SemanticPredicate, PredicateScore] = field(default_factory=dict)
    #: Assertions whose evidence did not survive validation, over all assertions.
    unsupported_assertions: int = 0
    total_assertions: int = 0
    wrong_entity: int = 0
    wrong_predicate: int = 0
    explicitness_overstated: int = 0
    rejected_relations_emitted: int = 0
    evidence_correct: int = 0
    evidence_checked: int = 0

    @property
    def entity_precision(self) -> float | None:
        predicted = self.entity_true_positives + self.entity_false_positives
        return self.entity_true_positives / predicted if predicted else None

    @property
    def entity_recall(self) -> float | None:
        expected = self.entity_true_positives + self.entity_false_negatives
        return self.entity_true_positives / expected if expected else None

    @property
    def unsupported_rate(self) -> float | None:
        return (
            self.unsupported_assertions / self.total_assertions if self.total_assertions else None
        )

    @property
    def evidence_accuracy(self) -> float | None:
        return self.evidence_correct / self.evidence_checked if self.evidence_checked else None

    def unlocked_predicates(self) -> frozenset[SemanticPredicate]:
        """Predicates whose measured precision earns automatic acceptance.

        This is the *only* thing that unlocks a predicate. A predicate absent from the
        gold subset is not unlocked: no evidence is not the same as good evidence.
        """
        return frozenset(
            predicate for predicate, score in self.relation_scores.items() if score.meets_target
        )


def _object_label(candidate: SemanticAssertionCandidate, entity_labels: dict[str, str]) -> str:
    if candidate.object.entity_key is not None:
        return normalize_label(
            entity_labels.get(candidate.object.entity_key, candidate.object.entity_key)
        )
    return normalize_label(candidate.object.candidate_entity_id or "")


def evaluate_against_gold(
    gold: dict[str, GoldAnnotation],
    predictions: dict[str, list[SemanticAssertionCandidate]],
    validations: dict[str, SemanticValidationResult],
    *,
    entity_labels: dict[str, str],
    candidate_labels: dict[str, str],
) -> GoldReport:
    """Score predictions for the annotated mantras only.

    ``candidate_labels`` maps a proposal's local id to the label it was given, so a
    predicted relation can be compared with a gold relation written in plain words.
    Matching is on the normalized label, which is the same folding the entity registry
    uses — so the evaluation cannot be gamed by a spelling the registry would also fold.
    """
    report = GoldReport(passage_count=len(gold))
    scores: dict[SemanticPredicate, dict[str, int]] = defaultdict(Counter)

    for passage_key, annotation in sorted(gold.items()):
        predicted = predictions.get(passage_key, [])
        report.total_assertions += len(predicted)

        expected_entities = {normalize_label(item) for item in annotation.entities}
        got_entities = {
            _object_label(candidate, entity_labels)
            or normalize_label(candidate_labels.get(candidate.object.candidate_entity_id or "", ""))
            for candidate in predicted
        } - {""}
        report.entity_true_positives += len(expected_entities & got_entities)
        report.entity_false_positives += len(got_entities - expected_entities)
        report.entity_false_negatives += len(expected_entities - got_entities)

        expected_relations = {
            (relation.predicate, normalize_label(relation.object_label)): relation
            for relation in annotation.relations
            if not relation.rejected
        }
        rejected_relations = {
            (relation.predicate, normalize_label(relation.object_label))
            for relation in annotation.relations
            if relation.rejected
        }
        seen: set[tuple[SemanticPredicate, str]] = set()

        for candidate in predicted:
            label = _object_label(candidate, entity_labels) or normalize_label(
                candidate_labels.get(candidate.object.candidate_entity_id or "", "")
            )
            key = (candidate.predicate, label)
            seen.add(key)
            verdict = validations.get(candidate.candidate_assertion_id)
            if verdict is not None:
                report.evidence_checked += 1
                if verdict.status.value != "VALIDATION_REJECTED":
                    report.evidence_correct += 1
                else:
                    report.unsupported_assertions += 1
            if key in expected_relations:
                scores[candidate.predicate]["tp"] += 1
                gold_relation = expected_relations[key]
                if _overstated(candidate.explicitness, gold_relation.explicitness):
                    report.explicitness_overstated += 1
            else:
                scores[candidate.predicate]["fp"] += 1
                if key in rejected_relations:
                    scores[candidate.predicate]["rejected"] += 1
                    report.rejected_relations_emitted += 1
                elif any(label == other for _, other in expected_relations):
                    # Right thing, wrong relation name.
                    report.wrong_predicate += 1
                elif any(candidate.predicate == other for other, _ in expected_relations):
                    report.wrong_entity += 1

        for key in expected_relations:
            if key not in seen:
                scores[key[0]]["fn"] += 1

    report.relation_scores = {
        predicate: PredicateScore(
            predicate=predicate,
            true_positives=counts["tp"],
            false_positives=counts["fp"],
            false_negatives=counts["fn"],
            rejected_hits=counts["rejected"],
        )
        for predicate, counts in sorted(scores.items(), key=lambda item: item[0].value)
    }
    return report


_ORDER = {Explicitness.INTERPRETIVE: 0, Explicitness.STRONG_INFERENCE: 1, Explicitness.EXPLICIT: 2}


def _overstated(predicted: Explicitness, expected: Explicitness) -> bool:
    return _ORDER[predicted] > _ORDER[expected]


@dataclass(frozen=True)
class ParallelDisagreement:
    """Two exact-parallel mantras whose extractions differ."""

    left: str
    right: str
    only_left: tuple[str, ...]
    only_right: tuple[str, ...]


@dataclass
class ParallelConsistencyReport:
    """How stable the extractor is on identical text."""

    pairs_compared: int = 0
    pairs_identical: int = 0
    disagreements: list[ParallelDisagreement] = field(default_factory=list)

    @property
    def agreement_rate(self) -> float | None:
        return self.pairs_identical / self.pairs_compared if self.pairs_compared else None


def compare_exact_parallels(
    predictions: dict[str, list[SemanticAssertionCandidate]],
    exact_parallels: dict[str, list[str]],
    *,
    entity_labels: dict[str, str],
) -> ParallelConsistencyReport:
    """Compare extractions across verbatim-identical mantras. Copies nothing.

    Disagreement is a finding, not a defect to repair: two identical lines in two hymns
    genuinely can carry different claims. What the number is for is stability — an
    extractor that disagrees with itself half the time on identical input is telling you
    its output is noise, whatever its precision on a single pass looks like.
    """
    report = ParallelConsistencyReport()
    compared: set[tuple[str, str]] = set()
    for left, partners in sorted(exact_parallels.items()):
        for right in partners:
            pair = (left, right) if left < right else (right, left)
            if pair in compared or pair[0] not in predictions or pair[1] not in predictions:
                continue
            compared.add(pair)
            report.pairs_compared += 1
            left_set = _relation_set(predictions[pair[0]], entity_labels)
            right_set = _relation_set(predictions[pair[1]], entity_labels)
            if left_set == right_set:
                report.pairs_identical += 1
            else:
                report.disagreements.append(
                    ParallelDisagreement(
                        left=pair[0],
                        right=pair[1],
                        only_left=tuple(sorted(left_set - right_set)),
                        only_right=tuple(sorted(right_set - left_set)),
                    )
                )
    return report


def _relation_set(
    candidates: list[SemanticAssertionCandidate], entity_labels: dict[str, str]
) -> set[str]:
    return {
        f"{candidate.predicate.value}->{_object_label(candidate, entity_labels)}"
        for candidate in candidates
    }


@dataclass(frozen=True)
class CostReport:
    """What a run actually cost, and what the full corpus would cost at that rate."""

    usage: TokenUsage
    passage_count: int
    input_usd_per_million: float
    cached_input_usd_per_million: float
    output_usd_per_million: float
    full_corpus_mantras: int = 10552

    @property
    def uncached_input_tokens(self) -> int:
        return max(self.usage.input_tokens - self.usage.cached_input_tokens, 0)

    @property
    def total_cost_usd(self) -> float:
        return (
            self.uncached_input_tokens * self.input_usd_per_million
            + self.usage.cached_input_tokens * self.cached_input_usd_per_million
            + self.usage.output_tokens * self.output_usd_per_million
        ) / 1_000_000

    @property
    def cost_per_mantra_usd(self) -> float | None:
        return self.total_cost_usd / self.passage_count if self.passage_count else None

    @property
    def average_input_tokens(self) -> float | None:
        return self.usage.input_tokens / self.usage.requests if self.usage.requests else None

    @property
    def average_output_tokens(self) -> float | None:
        return self.usage.output_tokens / self.usage.requests if self.usage.requests else None

    @property
    def projected_full_corpus_usd(self) -> float | None:
        """A projection, and labelled one everywhere it is printed.

        It assumes the pilot's per-mantra token profile holds across the corpus. The
        pilot is deliberately stratified towards awkward mantras, so this is more likely
        to over- than under-estimate — but it is an assumption either way.
        """
        per_mantra = self.cost_per_mantra_usd
        return per_mantra * self.full_corpus_mantras if per_mantra is not None else None
