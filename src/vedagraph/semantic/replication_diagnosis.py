"""Truth-neutral diagnostics for comparing two sealed semantic extractions.

The types in this module describe model-to-model replication behavior.  They do not
accept either run, historical heuristic output, or model agreement as human gold.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class AlignmentCategory(StrEnum):
    """Permitted assertion-pair outcomes for the real-Luna audit."""

    EXACT_ASSERTION = "EXACT_ASSERTION"
    SAME_PREDICATE_SAME_OBJECT_DIFFERENT_EVIDENCE = "SAME_PREDICATE_SAME_OBJECT_DIFFERENT_EVIDENCE"
    SAME_PREDICATE_COMPATIBLE_OBJECT = "SAME_PREDICATE_COMPATIBLE_OBJECT"
    OBJECT_GRANULARITY_DIFFERENCE = "OBJECT_GRANULARITY_DIFFERENCE"
    PREDICATE_BOUNDARY_DIFFERENCE = "PREDICATE_BOUNDARY_DIFFERENCE"
    TARGET_DIFFERENCE = "TARGET_DIFFERENCE"
    A_ONLY = "A_ONLY"
    B_ONLY = "B_ONLY"
    UNRESOLVED = "UNRESOLVED"


class OneSidedAssessment(StrEnum):
    """Engineering adjudication of an assertion emitted by only one run."""

    SUPPORTED_OMISSION_VARIANCE = "SUPPORTED_OMISSION_VARIANCE"
    PLAUSIBLE_BUT_OPTIONAL = "PLAUSIBLE_BUT_OPTIONAL"
    UNSUPPORTED_EXTRACTION = "UNSUPPORTED_EXTRACTION"
    PREDICATE_POLICY_AMBIGUITY = "PREDICATE_POLICY_AMBIGUITY"
    OBJECT_POLICY_AMBIGUITY = "OBJECT_POLICY_AMBIGUITY"
    EXPERT_REQUIRED = "EXPERT_REQUIRED"
    UNRESOLVED = "UNRESOLVED"


class NoClaimAssessment(StrEnum):
    """Diagnosis for a passage where exactly one run returned no claim."""

    SUPPORTED_CLAIM_VS_OMISSION = "SUPPORTED_CLAIM_VS_OMISSION"
    UNSUPPORTED_CLAIM_VS_NOCLAIM = "UNSUPPORTED_CLAIM_VS_NOCLAIM"
    AMBIGUOUS_CLAIM_VS_NOCLAIM = "AMBIGUOUS_CLAIM_VS_NOCLAIM"


class AnchorAssessment(StrEnum):
    """Semantic importance of two different evidence bindings."""

    SAME_SEMANTIC_SUPPORT_ALTERNATE_SPAN = "SAME_SEMANTIC_SUPPORT_ALTERNATE_SPAN"
    BROADER_VS_NARROWER_VALID_SPAN = "BROADER_VS_NARROWER_VALID_SPAN"
    DIFFERENT_SENTENCE_SUPPORT = "DIFFERENT_SENTENCE_SUPPORT"
    ONE_ANCHOR_WEAK = "ONE_ANCHOR_WEAK"
    SEMANTIC_DISAGREEMENT = "SEMANTIC_DISAGREEMENT"


class SeverityV2(StrEnum):
    """Severity based on failure meaning, not raw set inequality."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class DiagnosticSet(StrEnum):
    """Candidate-only diagnostic groups; none is canonical knowledge."""

    STABLE_CORE = "STABLE_CORE"
    ONE_RUN_SUPPORTED = "ONE_RUN_SUPPORTED"
    POLICY_AMBIGUOUS = "POLICY_AMBIGUOUS"
    SUSPECT_ASSERTION = "SUSPECT_ASSERTION"
    EXPERT_REQUIRED = "EXPERT_REQUIRED"


class FailureMode(StrEnum):
    """Primary source of one unit of observed replication disagreement."""

    EMISSION_RECALL_VARIANCE = "EMISSION_RECALL_VARIANCE"
    PREDICATE_POLICY_AMBIGUITY = "PREDICATE_POLICY_AMBIGUITY"
    OBJECT_GRANULARITY_VARIANCE = "OBJECT_GRANULARITY_VARIANCE"
    EVIDENCE_ANCHOR_VARIANCE = "EVIDENCE_ANCHOR_VARIANCE"
    CANONICAL_TARGET_VARIANCE = "CANONICAL_TARGET_VARIANCE"
    UNSUPPORTED_EXTRACTION_VARIANCE = "UNSUPPORTED_EXTRACTION_VARIANCE"
    EXPERT_DEPENDENT_AMBIGUITY = "EXPERT_DEPENDENT_AMBIGUITY"
    OTHER = "OTHER"


@dataclass(frozen=True)
class ComparableAssertion:
    """Only fields allowed to participate in deterministic structured alignment."""

    assertion_id: str
    predicate: str
    object_kind: str
    normalized_head: str | None
    canonical_entity_id: str | None
    qualifiers: tuple[str, ...]
    beneficiary_entity_id: str | None
    target_entity_id: str | None
    event_action_head: str | None
    event_actor_entity_id: str | None
    event_patient_entity_id: str | None
    event_participants: tuple[tuple[str, str], ...]
    evidence_references: tuple[str, ...]
    binding_anchors: tuple[tuple[str, str, int, int], ...]

    @classmethod
    def from_mapping(
        cls,
        assertion: Mapping[str, Any],
        bindings: Sequence[Mapping[str, Any]] = (),
    ) -> ComparableAssertion:
        """Construct a comparison view without label synonym normalization."""
        obj: Mapping[str, Any] = assertion["object"]
        event_raw = obj.get("event")
        event: Mapping[str, Any] = event_raw if isinstance(event_raw, Mapping) else {}
        participants = tuple(
            sorted(
                (
                    str(item.get("role", "")),
                    str(item.get("entity_id") or item.get("normalized_head") or ""),
                )
                for item in event.get("other_participants", ())
                if isinstance(item, Mapping)
            )
        )
        evidence_refs: set[str] = set()
        for raw in assertion.get("evidence", ()):
            if not isinstance(raw, Mapping):
                continue
            evidence_refs.add(f"PASSAGE:{raw.get('source_passage_id')}")
            translation_id = raw.get("translation_record_id")
            if translation_id:
                span = raw.get("translation_span")
                if isinstance(span, Mapping):
                    evidence_refs.add(
                        f"TRANSLATION:{translation_id}:{span.get('start')}:{span.get('end')}"
                    )
                else:
                    evidence_refs.add(f"TRANSLATION:{translation_id}")
            evidence_refs.update(f"TOKEN:{value}" for value in raw.get("token_ids", ()))
            evidence_refs.update(f"PASSAGE:{value}" for value in raw.get("passage_ids", ()))
            evidence_refs.update(f"OTHER:{value}" for value in raw.get("other_evidence_ids", ()))
        assertion_id = str(assertion["assertion_id"])
        anchors: list[tuple[str, str, int, int]] = []
        for binding in bindings:
            if binding.get("assertion_id") != assertion_id:
                continue
            for anchor in binding.get("anchors", ()):
                if isinstance(anchor, Mapping):
                    anchors.append(
                        (
                            str(anchor.get("role", "")),
                            str(anchor.get("text", "")),
                            int(anchor.get("start", 0)),
                            int(anchor.get("end", 0)),
                        )
                    )
        return cls(
            assertion_id=assertion_id,
            predicate=str(assertion["predicate"]),
            object_kind=str(obj["object_kind"]),
            normalized_head=_optional_str(obj.get("normalized_head")),
            canonical_entity_id=_optional_str(obj.get("canonical_entity_id")),
            qualifiers=tuple(sorted(str(value) for value in obj.get("qualifiers", ()))),
            beneficiary_entity_id=_optional_str(obj.get("beneficiary_entity_id")),
            target_entity_id=_optional_str(obj.get("target_entity_id")),
            event_action_head=_optional_str(event.get("action_head")),
            event_actor_entity_id=_optional_str(event.get("actor_entity_id")),
            event_patient_entity_id=_optional_str(event.get("patient_entity_id")),
            event_participants=participants,
            evidence_references=tuple(sorted(evidence_refs)),
            binding_anchors=tuple(sorted(anchors)),
        )


@dataclass(frozen=True)
class Alignment:
    """A deterministic assertion alignment row."""

    category: AlignmentCategory
    a: ComparableAssertion | None
    b: ComparableAssertion | None


def _optional_str(value: object) -> str | None:
    return str(value) if value is not None else None


def _object_fields(item: ComparableAssertion) -> tuple[object, ...]:
    return (
        item.object_kind,
        item.normalized_head,
        item.canonical_entity_id,
        item.qualifiers,
        item.beneficiary_entity_id,
        item.target_entity_id,
        item.event_action_head,
        item.event_actor_entity_id,
        item.event_patient_entity_id,
        item.event_participants,
    )


def _target_conflict(a: ComparableAssertion, b: ComparableAssertion) -> bool:
    canonical_conflict = bool(
        a.object_kind == b.object_kind == "CANONICAL_ENTITY_REF"
        and a.canonical_entity_id
        and b.canonical_entity_id
        and a.canonical_entity_id != b.canonical_entity_id
    )
    role_conflict = any(
        left is not None and right is not None and left != right
        for left, right in (
            (a.target_entity_id, b.target_entity_id),
            (a.beneficiary_entity_id, b.beneficiary_entity_id),
            (a.event_actor_entity_id, b.event_actor_entity_id),
            (a.event_patient_entity_id, b.event_patient_entity_id),
        )
    )
    return canonical_conflict or role_conflict


def canonical_entity_contradiction(a: ComparableAssertion, b: ComparableAssertion) -> bool:
    """True only when two canonical references name different supplied IDs."""
    return bool(
        a.object_kind == b.object_kind == "CANONICAL_ENTITY_REF"
        and a.canonical_entity_id
        and b.canonical_entity_id
        and a.canonical_entity_id != b.canonical_entity_id
    )


def _object_relation(a: ComparableAssertion, b: ComparableAssertion) -> str:
    if _target_conflict(a, b):
        return "TARGET"
    if _object_fields(a) == _object_fields(b):
        return "EXACT"
    if a.object_kind != b.object_kind:
        return "NONE"
    if a.object_kind == "EVENT":
        if a.event_action_head != b.event_action_head:
            return "NONE"
        left = {
            value
            for value in (
                a.event_actor_entity_id,
                a.event_patient_entity_id,
                *[f"{role}:{value}" for role, value in a.event_participants],
            )
            if value
        }
        right = {
            value
            for value in (
                b.event_actor_entity_id,
                b.event_patient_entity_id,
                *[f"{role}:{value}" for role, value in b.event_participants],
            )
            if value
        }
        return "GRANULARITY" if left <= right or right <= left else "COMPATIBLE"
    if a.normalized_head == b.normalized_head:
        qa, qb = set(a.qualifiers), set(b.qualifiers)
        return "GRANULARITY" if qa <= qb or qb <= qa else "COMPATIBLE"
    left_tokens = set((a.normalized_head or "").casefold().split())
    right_tokens = set((b.normalized_head or "").casefold().split())
    if left_tokens and right_tokens and (left_tokens < right_tokens or right_tokens < left_tokens):
        return "GRANULARITY"
    return "NONE"


def _pair_category(a: ComparableAssertion, b: ComparableAssertion) -> AlignmentCategory | None:
    relation = _object_relation(a, b)
    if relation == "NONE":
        return None
    if relation == "TARGET":
        return AlignmentCategory.TARGET_DIFFERENCE
    if a.predicate != b.predicate:
        return AlignmentCategory.PREDICATE_BOUNDARY_DIFFERENCE
    if relation == "GRANULARITY":
        return AlignmentCategory.OBJECT_GRANULARITY_DIFFERENCE
    if relation == "COMPATIBLE":
        return AlignmentCategory.SAME_PREDICATE_COMPATIBLE_OBJECT
    if a.evidence_references == b.evidence_references and a.binding_anchors == b.binding_anchors:
        return AlignmentCategory.EXACT_ASSERTION
    return AlignmentCategory.SAME_PREDICATE_SAME_OBJECT_DIFFERENT_EVIDENCE


def align_assertions(
    a_assertions: Sequence[ComparableAssertion],
    b_assertions: Sequence[ComparableAssertion],
) -> list[Alignment]:
    """Align structured assertions without fuzzy or synonym equivalence."""
    a_sorted = sorted(a_assertions, key=lambda item: item.assertion_id)
    b_sorted = sorted(b_assertions, key=lambda item: item.assertion_id)
    remaining = set(range(len(b_sorted)))
    rows: list[Alignment] = []
    rank = {
        AlignmentCategory.EXACT_ASSERTION: 100,
        AlignmentCategory.SAME_PREDICATE_SAME_OBJECT_DIFFERENT_EVIDENCE: 95,
        AlignmentCategory.SAME_PREDICATE_COMPATIBLE_OBJECT: 90,
        AlignmentCategory.OBJECT_GRANULARITY_DIFFERENCE: 80,
        AlignmentCategory.PREDICATE_BOUNDARY_DIFFERENCE: 60,
        AlignmentCategory.TARGET_DIFFERENCE: 50,
    }
    for left in a_sorted:
        choices: list[tuple[int, int, AlignmentCategory]] = []
        for index in sorted(remaining):
            right = b_sorted[index]
            category = _pair_category(left, right)
            if category is not None:
                same_predicate_bonus = 1000 if left.predicate == right.predicate else 0
                choices.append((same_predicate_bonus + rank[category], -index, category))
        if not choices:
            rows.append(Alignment(AlignmentCategory.A_ONLY, left, None))
            continue
        _, negative_index, category = max(choices)
        index = -negative_index
        remaining.remove(index)
        rows.append(Alignment(category, left, b_sorted[index]))
    rows.extend(
        Alignment(AlignmentCategory.B_ONLY, None, b_sorted[index]) for index in sorted(remaining)
    )
    return rows


def no_claim_assessment(
    one_sided: Iterable[OneSidedAssessment],
) -> NoClaimAssessment:
    """Reduce assertion assessments to one claim-vs-no-claim diagnosis."""
    values = set(one_sided)
    if OneSidedAssessment.SUPPORTED_OMISSION_VARIANCE in values:
        return NoClaimAssessment.SUPPORTED_CLAIM_VS_OMISSION
    if values and values <= {OneSidedAssessment.UNSUPPORTED_EXTRACTION}:
        return NoClaimAssessment.UNSUPPORTED_CLAIM_VS_NOCLAIM
    return NoClaimAssessment.AMBIGUOUS_CLAIM_VS_NOCLAIM


def diagnostic_set_for(
    category: AlignmentCategory,
    one_sided: OneSidedAssessment | None = None,
) -> DiagnosticSet | None:
    """Map an audit row to a candidate-only diagnostic group."""
    if category in {
        AlignmentCategory.EXACT_ASSERTION,
        AlignmentCategory.SAME_PREDICATE_SAME_OBJECT_DIFFERENT_EVIDENCE,
        AlignmentCategory.SAME_PREDICATE_COMPATIBLE_OBJECT,
        AlignmentCategory.OBJECT_GRANULARITY_DIFFERENCE,
    }:
        return DiagnosticSet.STABLE_CORE
    if category is AlignmentCategory.UNRESOLVED:
        return DiagnosticSet.EXPERT_REQUIRED
    if one_sided is OneSidedAssessment.SUPPORTED_OMISSION_VARIANCE:
        return DiagnosticSet.ONE_RUN_SUPPORTED
    if one_sided in {
        OneSidedAssessment.PREDICATE_POLICY_AMBIGUITY,
        OneSidedAssessment.OBJECT_POLICY_AMBIGUITY,
        OneSidedAssessment.PLAUSIBLE_BUT_OPTIONAL,
    }:
        return DiagnosticSet.POLICY_AMBIGUOUS
    if one_sided is OneSidedAssessment.UNSUPPORTED_EXTRACTION:
        return DiagnosticSet.SUSPECT_ASSERTION
    if one_sided in {OneSidedAssessment.EXPERT_REQUIRED, OneSidedAssessment.UNRESOLVED}:
        return DiagnosticSet.EXPERT_REQUIRED
    return None


def severity_v2(
    category: AlignmentCategory,
    *,
    one_sided: OneSidedAssessment | None = None,
    anchor: AnchorAssessment | None = None,
    integrity_failure: bool = False,
    ontology_violation: bool = False,
    canonical_contradiction: bool = False,
) -> SeverityV2:
    """Assign severity from diagnosed failure meaning rather than set inequality."""
    if integrity_failure or ontology_violation or canonical_contradiction:
        return SeverityV2.CRITICAL
    if one_sided is OneSidedAssessment.UNSUPPORTED_EXTRACTION:
        return SeverityV2.HIGH
    if category in {AlignmentCategory.TARGET_DIFFERENCE, AlignmentCategory.UNRESOLVED}:
        return SeverityV2.HIGH
    if category in {
        AlignmentCategory.A_ONLY,
        AlignmentCategory.B_ONLY,
        AlignmentCategory.PREDICATE_BOUNDARY_DIFFERENCE,
        AlignmentCategory.OBJECT_GRANULARITY_DIFFERENCE,
        AlignmentCategory.SAME_PREDICATE_COMPATIBLE_OBJECT,
    }:
        return SeverityV2.MEDIUM
    if anchor in {
        AnchorAssessment.ONE_ANCHOR_WEAK,
        AnchorAssessment.SEMANTIC_DISAGREEMENT,
    }:
        return SeverityV2.MEDIUM
    return SeverityV2.LOW


def candidate_provenance_label(diagnostic: DiagnosticSet) -> tuple[str, str]:
    """Return a diagnostic provenance label that can never promote a graph edge."""
    if diagnostic is DiagnosticSet.STABLE_CORE:
        return "REPLICATION_SUPPORTED_MODEL_CANDIDATE", "CANDIDATE_NEEDS_REVIEW"
    return diagnostic.value, "CANDIDATE_NEEDS_REVIEW"


@dataclass(frozen=True)
class EmissionRegime:
    """Run-level emission behavior over one set of passages."""

    passages: int
    assertions: int
    no_claim_passages: int
    predicate_counts: Mapping[str, int]
    #: Typed-object shape of what the run emitted, and how much of it named a supplied
    #: canonical entity.  Two runs can agree on predicates and still differ here.
    object_kind_counts: Mapping[str, int] = field(default_factory=dict)
    canonical_reference_count: int = 0

    @property
    def density(self) -> float:
        """Assertions emitted per passage."""
        return self.assertions / self.passages if self.passages else 0.0

    @property
    def no_claim_rate(self) -> float:
        """Share of passages where the run emitted nothing."""
        return self.no_claim_passages / self.passages if self.passages else 0.0

    def share_of(self, predicate: str) -> float:
        """Share of this run's assertions carrying one predicate."""
        return self.predicate_counts.get(predicate, 0) / self.assertions if self.assertions else 0.0


def exchangeable_one_sided_probability(left: int, right: int) -> float:
    """Two-sided probability that all occurrences land in one run by chance.

    Used only to show that a predicate skew over identical inputs is not sampling
    noise.  It is evidence about run behavior, never evidence about correctness.
    """
    total = left + right
    if total == 0 or (left and right):
        return 1.0
    return min(1.0, 2.0 * 0.5**total)


#: Tolerated gap between two runs' no-claim rates before the difference is read as a
#: run-level regime split rather than local variance. ``engineering_default_not_truth_derived``:
#: it is the value that separates the two observed v3.1 regimes (0.167 against 0.633), not a
#: constant derived from any gold annotation, and every caller may override it.
NO_CLAIM_RATE_GAP_ENGINEERING_DEFAULT = 0.2
NO_CLAIM_RATE_GAP_PROVENANCE = "engineering_default_not_truth_derived"

#: Probability below which an all-in-one-run predicate skew is reported as run behavior
#: rather than sampling noise. Also an engineering default, not a truth-derived constant.
ONE_SIDED_SKEW_PROBABILITY_ENGINEERING_DEFAULT = 0.01


def regime_divergence(
    a: EmissionRegime,
    b: EmissionRegime,
    *,
    predicate: str,
    no_claim_tolerance: float = NO_CLAIM_RATE_GAP_ENGINEERING_DEFAULT,
) -> bool:
    """True when two runs occupy different emission regimes over identical inputs.

    A regime difference is a run-level policy split, which the per-assertion
    categories cannot express: they would score it as many independent omissions.

    ``no_claim_tolerance`` is an engineering threshold, not a measured constant; see
    :data:`NO_CLAIM_RATE_GAP_ENGINEERING_DEFAULT`.
    """
    skew = exchangeable_one_sided_probability(
        a.predicate_counts.get(predicate, 0), b.predicate_counts.get(predicate, 0)
    )
    return skew < 0.01 or abs(a.no_claim_rate - b.no_claim_rate) > no_claim_tolerance


@dataclass(frozen=True)
class RegimeComparison:
    """Run-level differences between two extractions of the same passages.

    Every field describes run behavior. With two runs none of it says which behavior is
    right, and it cannot say how many latent regimes exist -- only whether these two runs
    behaved alike.
    """

    a: EmissionRegime
    b: EmissionRegime
    no_claim_rate_gap: float
    density_gap: float
    predicate_counts: Mapping[str, tuple[int, int]]
    one_sided_predicates: tuple[str, ...]
    predicate_presence_jaccard: float
    skew_probabilities: Mapping[str, float]
    object_kind_counts: Mapping[str, tuple[int, int]]
    canonical_reference_counts: tuple[int, int]


def compare_regimes(a: EmissionRegime, b: EmissionRegime) -> RegimeComparison:
    """Measure two runs against each other at run level rather than assertion level."""
    predicates = sorted(set(a.predicate_counts) | set(b.predicate_counts))
    counts = {
        name: (a.predicate_counts.get(name, 0), b.predicate_counts.get(name, 0))
        for name in predicates
    }
    present_a = {name for name, (left, _) in counts.items() if left}
    present_b = {name for name, (_, right) in counts.items() if right}
    union = present_a | present_b
    return RegimeComparison(
        a=a,
        b=b,
        no_claim_rate_gap=abs(a.no_claim_rate - b.no_claim_rate),
        density_gap=abs(a.density - b.density),
        predicate_counts=counts,
        one_sided_predicates=tuple(
            name for name, (left, right) in counts.items() if bool(left) != bool(right)
        ),
        predicate_presence_jaccard=(len(present_a & present_b) / len(union) if union else 1.0),
        skew_probabilities={
            name: exchangeable_one_sided_probability(left, right)
            for name, (left, right) in counts.items()
        },
        object_kind_counts={
            kind: (a.object_kind_counts.get(kind, 0), b.object_kind_counts.get(kind, 0))
            for kind in sorted(set(a.object_kind_counts) | set(b.object_kind_counts))
        },
        canonical_reference_counts=(a.canonical_reference_count, b.canonical_reference_count),
    )


@dataclass(frozen=True)
class PassageOutcome:
    """What one run produced for one passage, in comparison form."""

    no_claim: bool
    assertions: tuple[ComparableAssertion, ...] = ()


@dataclass(frozen=True)
class PassageAgreement:
    """Per-passage agreement counts. Agreement is replication, never correctness."""

    passages: int
    exact_assertion_set: int
    predicate_presence: int
    no_claim: int
    canonical_entity: int
    typed_object: int
    evidence_anchor: int


def _assertion_signatures(items: Sequence[ComparableAssertion]) -> set[tuple[object, ...]]:
    return {
        (item.predicate, item.object_kind, item.normalized_head, item.canonical_entity_id)
        for item in items
    }


def _typed_object_signatures(items: Sequence[ComparableAssertion]) -> set[tuple[object, ...]]:
    return {(item.predicate, *_object_fields(item)) for item in items}


def _anchor_signatures(items: Sequence[ComparableAssertion]) -> set[tuple[object, ...]]:
    return {
        (item.predicate, role, text) for item in items for role, text, _, _ in item.binding_anchors
    }


def passage_agreement(
    a: Mapping[str, PassageOutcome], b: Mapping[str, PassageOutcome]
) -> PassageAgreement:
    """Compare two runs passage by passage over an identical passage set.

    A differing passage set is refused: an agreement rate computed over an intersection
    would silently reward a run for the passages it skipped.
    """
    if set(a) != set(b):
        raise ValueError("passage agreement requires both runs to cover the same passages")
    exact = predicates = no_claim = canonical = typed = anchors = 0
    for key in sorted(a):
        left, right = a[key], b[key]
        if _assertion_signatures(left.assertions) == _assertion_signatures(right.assertions):
            exact += 1
        if {item.predicate for item in left.assertions} == {
            item.predicate for item in right.assertions
        }:
            predicates += 1
        if left.no_claim == right.no_claim:
            no_claim += 1
        if {item.canonical_entity_id for item in left.assertions if item.canonical_entity_id} == {
            item.canonical_entity_id for item in right.assertions if item.canonical_entity_id
        }:
            canonical += 1
        if _typed_object_signatures(left.assertions) == _typed_object_signatures(right.assertions):
            typed += 1
        if _anchor_signatures(left.assertions) == _anchor_signatures(right.assertions):
            anchors += 1
    return PassageAgreement(
        passages=len(a),
        exact_assertion_set=exact,
        predicate_presence=predicates,
        no_claim=no_claim,
        canonical_entity=canonical,
        typed_object=typed,
        evidence_anchor=anchors,
    )


def canonical_target_contradictions(
    a: Mapping[str, PassageOutcome], b: Mapping[str, PassageOutcome]
) -> tuple[str, ...]:
    """Passages where the two runs name different canonical targets for one predicate.

    This is the one difference class that is a contradiction rather than a variance: both
    runs make the same relation claim about the same passage and disagree about its target.
    """
    contradictions: list[str] = []
    for key in sorted(set(a) & set(b)):
        by_predicate: dict[str, tuple[set[str], set[str]]] = {}
        for index, outcome in enumerate((a[key], b[key])):
            for item in outcome.assertions:
                if item.object_kind != "CANONICAL_ENTITY_REF" or not item.canonical_entity_id:
                    continue
                left_ids, right_ids = by_predicate.setdefault(item.predicate, (set(), set()))
                (left_ids if index == 0 else right_ids).add(item.canonical_entity_id)
        if any(left and right and left != right for left, right in by_predicate.values()):
            contradictions.append(key)
    return tuple(contradictions)


def emission_regime(outcomes: Mapping[str, PassageOutcome]) -> EmissionRegime:
    """Derive one run's regime from what it actually emitted, per passage.

    Counting this way rather than by hand is the point: a run-level metric assembled
    manually is the kind of number that quietly disagrees with the artefacts it describes.
    """
    assertions = [item for outcome in outcomes.values() for item in outcome.assertions]
    predicate_counts: dict[str, int] = {}
    object_kind_counts: dict[str, int] = {}
    for item in assertions:
        predicate_counts[item.predicate] = predicate_counts.get(item.predicate, 0) + 1
        object_kind_counts[item.object_kind] = object_kind_counts.get(item.object_kind, 0) + 1
    return EmissionRegime(
        passages=len(outcomes),
        assertions=len(assertions),
        no_claim_passages=sum(1 for outcome in outcomes.values() if outcome.no_claim),
        predicate_counts=predicate_counts,
        object_kind_counts=object_kind_counts,
        canonical_reference_count=sum(1 for item in assertions if item.canonical_entity_id),
    )
