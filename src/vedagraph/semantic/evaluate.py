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
from collections.abc import Iterable
from dataclasses import dataclass, field
from math import sqrt
from pathlib import Path
from typing import Any

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
MIN_PREDICATE_SUPPORT = 30
EVIDENCE_VALID_TARGET = 0.99
UNSUPPORTED_RATE_TARGET = 0.01
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
    evidence_correct: int = 0
    evidence_checked: int = 0
    unsupported_assertions: int = 0
    explicitness_counts: dict[str, int] = field(default_factory=dict)
    serious_errors: int = 0

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
    def f1(self) -> float | None:
        if self.precision is None or self.recall is None or self.precision + self.recall == 0:
            return None
        return 2 * self.precision * self.recall / (self.precision + self.recall)

    @property
    def evidence_valid_rate(self) -> float | None:
        return self.evidence_correct / self.evidence_checked if self.evidence_checked else None

    @property
    def unsupported_rate(self) -> float | None:
        return self.unsupported_assertions / self.predicted if self.predicted else None

    @property
    def wilson_interval(self) -> tuple[float, float] | None:
        return wilson_interval(self.true_positives, self.predicted)

    @property
    def meets_target(self) -> bool:
        precision = self.precision
        evidence = self.evidence_valid_rate
        unsupported = self.unsupported_rate
        return (
            precision is not None
            and precision >= PRECISION_TARGET
            and self.predicted >= MIN_PREDICATE_SUPPORT
            and evidence is not None
            and evidence >= EVIDENCE_VALID_TARGET
            and unsupported is not None
            and unsupported <= UNSUPPORTED_RATE_TARGET
            and self.serious_errors == 0
            and set(self.explicitness_counts) <= {Explicitness.EXPLICIT.value}
        )


@dataclass
class GoldReport:
    """Everything measured against the gold subset."""

    passage_count: int = 0
    entity_true_positives: int = 0
    entity_false_positives: int = 0
    entity_false_negatives: int = 0
    model_entity_mentions: int = 0
    duplicate_entity_mentions: int = 0
    unsupported_new_entity_mentions: int = 0
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
    error_taxonomy: Counter[str] = field(default_factory=Counter)
    explicitness_counts: Counter[str] = field(default_factory=Counter)

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

    @property
    def evidence_valid_rate(self) -> float | None:
        return self.evidence_accuracy

    @property
    def unsupported_evidence_rate(self) -> float | None:
        return self.unsupported_rate

    @property
    def wrong_entity_rate(self) -> float | None:
        predicted = self.entity_true_positives + self.entity_false_positives
        return self.entity_false_positives / predicted if predicted else None

    @property
    def duplicate_concept_rate(self) -> float | None:
        """Repeated model concepts among its entity mentions."""
        return (
            self.duplicate_entity_mentions / self.model_entity_mentions
            if self.model_entity_mentions
            else None
        )

    @property
    def unsupported_new_entity_rate(self) -> float | None:
        """New model entity mentions absent from the human-supported concepts."""
        return (
            self.unsupported_new_entity_mentions / self.model_entity_mentions
            if self.model_entity_mentions
            else None
        )

    @property
    def wrong_token_citation_rate(self) -> float | None:
        count = self.error_taxonomy.get("wrong token citation", 0)
        return count / self.evidence_checked if self.evidence_checked else None

    @property
    def wrong_translation_citation_rate(self) -> float | None:
        count = self.error_taxonomy.get("wrong translation citation", 0)
        return count / self.evidence_checked if self.evidence_checked else None

    @property
    def relation_f1(self) -> float | None:
        tp = sum(item.true_positives for item in self.relation_scores.values())
        predicted = sum(item.predicted for item in self.relation_scores.values())
        expected = tp + sum(item.false_negatives for item in self.relation_scores.values())
        precision = tp / predicted if predicted else None
        recall = tp / expected if expected else None
        if precision is None or recall is None or precision + recall == 0:
            return None
        return 2 * precision * recall / (precision + recall)

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
    scores: dict[SemanticPredicate, dict[str, Any]] = defaultdict(Counter)

    for passage_key, annotation in sorted(gold.items()):
        predicted = predictions.get(passage_key, [])
        report.total_assertions += len(predicted)

        expected_entities = {normalize_label(item) for item in annotation.effective_entity_labels}
        got_entities = {
            _object_label(candidate, entity_labels)
            or normalize_label(candidate_labels.get(candidate.object.candidate_entity_id or "", ""))
            for candidate in predicted
        } - {""}
        entity_mention_pairs = [
            (
                candidate,
                _object_label(candidate, entity_labels)
                or normalize_label(
                    candidate_labels.get(candidate.object.candidate_entity_id or "", "")
                ),
            )
            for candidate in predicted
        ]
        entity_mentions = [label for _, label in entity_mention_pairs if label]
        report.model_entity_mentions += len(entity_mentions)
        report.duplicate_entity_mentions += len(entity_mentions) - len(set(entity_mentions))
        report.unsupported_new_entity_mentions += sum(
            1
            for candidate, label in entity_mention_pairs
            if label
            if candidate.object.candidate_entity_id is not None and label not in expected_entities
        )
        report.entity_true_positives += len(expected_entities & got_entities)
        report.entity_false_positives += len(got_entities - expected_entities)
        report.entity_false_negatives += len(expected_entities - got_entities)

        expected_relations = {
            (relation.predicate, normalize_label(relation.object_label)): relation
            for relation in annotation.effective_assertions
            if not relation.rejected
        }
        rejected_relations = {
            (relation.predicate, normalize_label(relation.object_label))
            for relation in annotation.effective_assertions + annotation.rejected_tempting_relations
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
                scores[candidate.predicate]["evidence_checked"] += 1
                if verdict.status.value != "VALIDATION_REJECTED":
                    scores[candidate.predicate]["evidence_correct"] += 1
                else:
                    scores[candidate.predicate]["unsupported"] += 1
                for code in verdict.codes:
                    if code.value == "EVIDENCE_TOKEN_NOT_IN_PASSAGE":
                        report.error_taxonomy["wrong token citation"] += 1
                    elif code.value == "EVIDENCE_TRANSLATION_NOT_SUPPLIED":
                        report.error_taxonomy["wrong translation citation"] += 1
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
            explicitness = scores[candidate.predicate].setdefault("explicitness", Counter())
            explicitness[candidate.explicitness.value] += 1
            report.explicitness_counts[candidate.explicitness.value] += 1

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
            evidence_correct=counts["evidence_correct"],
            evidence_checked=counts["evidence_checked"],
            unsupported_assertions=counts["unsupported"],
            explicitness_counts=dict(counts.get("explicitness", {})),
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


def wilson_interval(successes: int, trials: int, *, z: float = 1.96) -> tuple[float, float] | None:
    """Return the two-sided 95% Wilson interval for a binomial proportion."""
    if trials <= 0 or successes < 0 or successes > trials:
        return None
    denominator = 1 + z * z / trials
    centre = (successes / trials + z * z / (2 * trials)) / denominator
    margin = (
        z
        * sqrt((successes * (trials - successes) / trials**3) + z * z / (4 * trials**2))
        / denominator
    )
    return (max(0.0, centre - margin), min(1.0, centre + margin))


def predicate_coverage(
    gold: dict[str, GoldAnnotation],
    predictions: dict[str, list[SemanticAssertionCandidate]],
) -> dict[str, object]:
    """Report predicate and node-type vocabularies represented by each side."""
    gold_predicates = {
        relation.predicate.value
        for annotation in gold.values()
        for relation in annotation.effective_assertions
        if not relation.rejected
    }
    model_predicates = {
        candidate.predicate.value for candidates in predictions.values() for candidate in candidates
    }
    gold_node_types = {
        entity.node_type.value
        for annotation in gold.values()
        for entity in annotation.gold_entities
    } | {
        relation.object_node_type.value
        for annotation in gold.values()
        for relation in annotation.effective_assertions
        if relation.object_node_type is not None
    }
    model_node_types = {
        candidate.object.node_type.value
        for candidates in predictions.values()
        for candidate in candidates
        if candidate.object.node_type is not None
    } | {
        "CANONICAL_ENTITY"
        for candidates in predictions.values()
        for candidate in candidates
        if candidate.object.entity_key
    }
    gold_support = Counter(
        relation.predicate.value
        for annotation in gold.values()
        for relation in annotation.effective_assertions
        if not relation.rejected
    )
    model_support = Counter(
        candidate.predicate.value for candidates in predictions.values() for candidate in candidates
    )
    return {
        "gold_predicates": sorted(gold_predicates),
        "model_predicates": sorted(model_predicates),
        "missing_predicate_coverage": sorted(gold_predicates - model_predicates),
        "PREDICATE_GOLD_SUPPORT": dict(sorted(gold_support.items())),
        "PREDICATE_MODEL_SUPPORT": dict(sorted(model_support.items())),
        "gold_node_types": sorted(gold_node_types),
        "model_node_types": sorted(model_node_types),
    }


def recommend_second_pilot(
    gold: dict[str, GoldAnnotation],
    predictions: dict[str, list[SemanticAssertionCandidate]],
    report: GoldReport,
) -> bool:
    """Flag coverage too narrow for a full-corpus promotion decision."""
    coverage = predicate_coverage(gold, predictions)
    model_predicates = coverage["model_predicates"]
    return (
        len(report.relation_scores) < 7
        or (
            isinstance(model_predicates, list)
            and set(model_predicates).issubset({"INVOKES", "PRAISES"})
        )
        or not any(annotation.gold_entities for annotation in gold.values())
    )


def write_evaluation_reports(
    *,
    output_dir: Path,
    gold_complete: bool,
    expected_count: int,
    gold_count: int,
    report: GoldReport | None = None,
    gold: dict[str, GoldAnnotation] | None = None,
    predictions: dict[str, list[SemanticAssertionCandidate]] | None = None,
    adjudications: Iterable[object] = (),
) -> None:
    """Write safe aggregate progress, evaluation, error, and coverage reports."""
    output_dir.mkdir(parents=True, exist_ok=True)
    marker = "" if gold_complete else "PRELIMINARY — GOLD INCOMPLETE\n\n"
    progress_text = (
        f"# RIGVEDA semantic gold progress\n\n{marker}"
        f"- Expected mantra ids: **{expected_count}**\n- Complete Stage A rows: **{gold_count}**\n"
        f"- Remaining: **{max(expected_count - gold_count, 0)}**\n"
        "\nThe reviewer must complete and validate every row before final evaluation "
        "metrics are produced.\n"
    )
    (output_dir / "RIGVEDA_SEMANTIC_GOLD_PROGRESS.md").write_text(progress_text, encoding="utf-8")
    if not gold_complete or report is None or gold is None or predictions is None:
        eval_text = (
            "# RIGVEDA semantic evaluation\n\nPRELIMINARY — GOLD INCOMPLETE\n\n"
            "Final precision, recall, F1, and unlocking decisions are withheld until "
            "the signed gold dataset is complete.\n"
        )
        coverage_text = (
            "# RIGVEDA semantic ontology coverage\n\nPRELIMINARY — GOLD INCOMPLETE\n\n"
            "Coverage will be reported after every gold row is complete.\n"
        )
    else:
        lines = [
            "# RIGVEDA semantic evaluation",
            "",
            "Gold is complete; signing is recorded by the gold manifest.",
            "",
            "## Relations",
        ]
        for predicate, score in report.relation_scores.items():
            interval = score.wilson_interval
            interval_text = f"[{interval[0]:.3f}, {interval[1]:.3f}]" if interval else "n/a"
            lines.append(
                f"- `{predicate.value}`: TP={score.true_positives}, FP={score.false_positives}, "
                f"FN={score.false_negatives}, precision={score.precision}, recall={score.recall}, "
                f"F1={score.f1}, Wilson={interval_text}, support={score.predicted}, "
                f"evidence-valid={score.evidence_valid_rate}, "
                f"unlock={'yes' if score.meets_target else 'no'}"
            )
        missing_support = predicate_coverage(gold, predictions)["missing_predicate_coverage"]
        lines.extend(
            [
                "",
                "## Entities",
                f"- precision: {report.entity_precision}",
                f"- recall: {report.entity_recall}",
                f"- wrong-entity findings: {report.wrong_entity}",
                f"- wrong-entity rate: {report.wrong_entity_rate}",
                f"- duplicate-concept rate: {report.duplicate_concept_rate}",
                f"- unsupported-new-entity rate: {report.unsupported_new_entity_rate}",
                f"- explicitness counts: {dict(report.explicitness_counts)}",
                "",
                "## Coverage",
                "- PREDICATE_GOLD_SUPPORT: "
                f"{predicate_coverage(gold, predictions)['PREDICATE_GOLD_SUPPORT']}",
                "- PREDICATE_MODEL_SUPPORT: "
                f"{predicate_coverage(gold, predictions)['PREDICATE_MODEL_SUPPORT']}",
                f"- MISSING_PREDICATE_COVERAGE: {missing_support}",
                f"- SECOND_PILOT_REQUIRED: "
                f"{'yes' if recommend_second_pilot(gold, predictions, report) else 'no'}",
            ]
        )
        eval_text = "\n".join(lines) + "\n"
        coverage = predicate_coverage(gold, predictions)
        coverage_text = (
            "# RIGVEDA semantic ontology coverage\n\n"
            + "\n".join(f"- {key}: {value}" for key, value in coverage.items())
            + "\n"
        )
    (output_dir / "RIGVEDA_SEMANTIC_EVAL.md").write_text(eval_text, encoding="utf-8")
    error_counts: Counter[str] = Counter()
    for item in adjudications:
        human = getattr(item, "human_decision", "OTHER")
        human_value = getattr(human, "value", human)
        if human_value in {"ACCEPT", "REJECT"}:
            continue
        category = getattr(item, "error_category", None) or human
        error_counts[str(getattr(category, "value", category))] += 1
    error_text = (
        "# RIGVEDA semantic error analysis\n\n"
        + marker
        + "\n".join(f"- {key}: {value}" for key, value in sorted(error_counts.items()))
        + "\n"
    )
    (output_dir / "RIGVEDA_SEMANTIC_ERROR_ANALYSIS.md").write_text(error_text, encoding="utf-8")
    (output_dir / "RIGVEDA_SEMANTIC_ONTOLOGY_COVERAGE.md").write_text(
        coverage_text, encoding="utf-8"
    )


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
