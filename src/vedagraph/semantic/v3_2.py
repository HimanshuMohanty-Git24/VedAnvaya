"""The V3.2 prompt policy, its provenance, and the bounded experiment it must pass first.

NO HUMAN GOLD EXISTS. MODEL SELF-AGREEMENT IS NOT ACCURACY.

Two genuine v3.1 runs processed the same sixty EvidencePackets under a byte-identical
execution contract. Execution integrity was clean: no contradictory canonical target, no
receipt, packet, binding or span failure, nothing imported that a model had not authored.
What the two runs did not share was an *emission regime*. One emitted 57 assertions with a
no-claim rate of 0.167; the other emitted 33 with a no-claim rate of 0.633, and each was
internally consistent. That is a property of the run, not of any single assertion, and no
per-assertion category can express it.

The diagnosis was that the v3.1 wording admits at least two internally coherent readings of
*when* a directly evidenced relation must be emitted. V3.2 is the minimal policy revision
that closes that boundary. It changes no schema, no predicate, no typed object and no
EvidencePacket, and it grants no new licence to claim: the seven rules constrain when a
supported relation may be *omitted*, never what may be asserted without support.

The CODEX_DIRECT contract gained exactly one field, ``RunContract.prompt_version``, so an
object can record which policy authored it. ``PreparedTask`` is untouched, because a field
there would change every ``task_sha256`` and invalidate every sealed receipt.

This module defines. It executes nothing, calls no API, and authors no semantics. The two
runs were subsequently completed and sealed by the separate execution/finalization path.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from vedagraph.semantic.codex_direct import (
    RunContract,
    ValidatedResponse,
    load_run_contract,
    read_prompt_version,
    task_id_for,
)
from vedagraph.semantic.replication_diagnosis import (
    NO_CLAIM_RATE_GAP_ENGINEERING_DEFAULT,
    ONE_SIDED_SKEW_PROBABILITY_ENGINEERING_DEFAULT,
    RegimeComparison,
)
from vedagraph.semantic.v3 import PREDICATE_CHECKS

PROMPT_VERSION_V3_2 = "rigveda-semantic-extraction-v3.2"
PROMPT_PATH_V3_2 = Path("prompts/semantic_extraction_v3.2.md")

#: The policy the v3.1 runs executed. Named here only so a test can prove it is untouched.
PROMPT_VERSION_V3_1 = "rigveda-semantic-extraction-v3"
PROMPT_PATH_V3_1 = Path("prompts/semantic_extraction_v3.md")

SCHEMA_PATH = Path("schemas/semantic_extraction_v3.schema.json")
ONTOLOGY_PATH = Path("src/vedagraph/semantic/ontology.py")

EXECUTION_VERSION_V3_2 = "rigveda-semantic-execution-v3.2"

#: Two independent runs of one experiment. Distinct identities, one semantic contract.
STABILITY_RUN_A = "vedagraph-rigveda-semantic-luna-v3.2-stability-60-a"
STABILITY_RUN_B = "vedagraph-rigveda-semantic-luna-v3.2-stability-60-b"

#: The existing bounded real-Luna selection, reused unchanged. Re-drawing it would make the
#: v3.1 and v3.2 observations incomparable, which is the one thing this experiment needs.
SELECTION_CONFIG = Path("data/builds/rigveda_semantic_codex_luna_regression_v1.yaml")

MODEL = "gpt-5.6-luna"
RUNTIME = "CODEX_DIRECT"
REASONING = "high"


@dataclass(frozen=True)
class PolicyRule:
    """One numbered V3.2 emission rule, as it appears in the prompt."""

    number: int
    title: str

    @property
    def heading(self) -> str:
        return f"### Rule {self.number} — {self.title}"


#: The seven rules the replication audit justified. Nothing else changed.
POLICY_RULES: tuple[PolicyRule, ...] = (
    PolicyRule(1, "Emit-vs-omit floor"),
    PolicyRule(2, "REQUESTS force"),
    PolicyRule(3, "REQUESTS outcome splitting"),
    PolicyRule(4, "DESCRIBES precedence"),
    PolicyRule(5, "DESCRIBES_ACTION scope"),
    PolicyRule(6, "Material and ritual co-emission"),
    PolicyRule(7, "No-claim criterion"),
)

#: Repo-authoritative order. The prompt numbers the families in exactly this sequence.
FAMILY_INSPECTION_ORDER: tuple[str, ...] = PREDICATE_CHECKS


def prompt_text(path: Path = PROMPT_PATH_V3_2) -> str:
    return path.read_text(encoding="utf-8")


def prompt_sha256(path: Path = PROMPT_PATH_V3_2) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prompt_policy_errors(path: Path = PROMPT_PATH_V3_2) -> list[str]:
    """Structural checks on the V3.2 prompt: does it actually say what V3.2 is?

    This is a completeness check on a document, not a semantic one. It cannot tell whether
    the wording works -- only the two-run experiment can speak to that, and only about
    stability.
    """
    text = prompt_text(path)
    errors: list[str] = []
    if read_prompt_version(path) != PROMPT_VERSION_V3_2:
        errors.append(f"{path} does not declare {PROMPT_VERSION_V3_2}")
    errors += [
        f"missing rule heading: {rule.heading}" for rule in POLICY_RULES if rule.heading not in text
    ]
    for position, family in enumerate(FAMILY_INSPECTION_ORDER, start=1):
        if f"{position}. `{family}`" not in text:
            errors.append(f"family {family} is not inspected at position {position}")
    required = {
        "no-claim criterion": "`no_claim` is permitted only after all fourteen families",
        "explicitness floor": "`INTERPRETIVE` is prohibited",
        "candidate status": "CANDIDATE / NEEDS_REVIEW",
        "locked predicates": "`unlocked_predicates` remains empty",
        "no remembered knowledge": "Do not use remembered",
        "no gold claim": "no human gold set exists",
    }
    errors += [f"missing {name}" for name, phrase in sorted(required.items()) if phrase not in text]
    return errors


def leaked_identifiers(text: str, identifiers: tuple[str, ...]) -> tuple[str, ...]:
    """Identifiers from the benchmark that appear verbatim in a prompt.

    A prompt naming a benchmark passage is training on the benchmark, whatever the
    intention. Non-empty output means the prompt must be rewritten, not the check relaxed.
    """
    return tuple(sorted({item for item in identifiers if item and item in text}))


def _selection_hash(document: dict[str, Any]) -> str:
    """The selection identity formula the sealed v3.1 selection was frozen under."""
    ids = sorted(str(row["passage_key"]) for row in document["mantras"])
    return hashlib.sha256(
        json.dumps(
            {"policy": document["selection_policy_version"], "ids": ids},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class Selection:
    """The frozen sixty, with the identity they were frozen under."""

    passage_ids: tuple[str, ...]
    citations: tuple[str, ...]
    selection_hash: str
    policy_version: str


def load_selection(path: Path = SELECTION_CONFIG) -> Selection:
    """Read the existing bounded selection and refuse it if its identity has drifted."""
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"{path} is not a selection document")
    rows = document.get("mantras")
    if not isinstance(rows, list) or len(rows) != 60:
        raise ValueError(f"{path} must hold exactly 60 mantras")
    passage_ids = tuple(str(row["passage_key"]) for row in rows)
    if len(set(passage_ids)) != 60:
        raise ValueError(f"{path} contains duplicate passage IDs")
    computed = _selection_hash(document)
    if computed != document.get("selection_hash"):
        raise ValueError(f"{path} selection hash does not match its IDs")
    return Selection(
        passage_ids=passage_ids,
        citations=tuple(str(row["citation"]) for row in rows),
        selection_hash=computed,
        policy_version=str(document["selection_policy_version"]),
    )


@dataclass(frozen=True)
class StabilityExperiment:
    """Two independent runs over one selection under one semantic contract.

    The type makes the contract the runs share checkable rather than merely asserted in
    prose. Constructing it never executes a model, including after the runs exist on disk.
    """

    run_a: RunContract
    run_b: RunContract
    selection: Selection

    @property
    def run_ids(self) -> tuple[str, str]:
        return (self.run_a.run_id, self.run_b.run_id)

    def contract_differences(self) -> list[str]:
        """Every field on which the two run contracts disagree except their identity.

        Two runs of a replication experiment must differ in exactly one way: which run they
        are. Anything else -- a different prompt, schema, ontology, model or reasoning
        setting -- makes a difference between their outputs uninterpretable.
        """
        if self.run_a.run_id == self.run_b.run_id:
            return ["both runs share one run id; they would not be independent"]
        left = self.run_a.model_dump(mode="json")
        right = self.run_b.model_dump(mode="json")
        return sorted(
            f"{field}: {left[field]!r} != {right[field]!r}"
            for field in left
            if field != "run_id" and left[field] != right[field]
        )

    def task_ids(self, run_id: str) -> dict[str, str]:
        """The task identity each passage would be prepared under, without preparing it."""
        if run_id not in self.run_ids:
            raise ValueError(f"{run_id} is not a run of this experiment")
        return {passage: task_id_for(run_id, passage) for passage in self.selection.passage_ids}


def build_stability_experiment(
    *,
    prompt_path: Path = PROMPT_PATH_V3_2,
    schema_path: Path = SCHEMA_PATH,
    ontology_path: Path = ONTOLOGY_PATH,
    selection_path: Path = SELECTION_CONFIG,
    run_a: str = STABILITY_RUN_A,
    run_b: str = STABILITY_RUN_B,
    execution_version: str = EXECUTION_VERSION_V3_2,
) -> StabilityExperiment:
    """Define the two-run experiment. Prepares no task and runs no model.

    Both contracts are loaded independently from the same files rather than copied from
    each other, so ``contract_differences`` is a real check on the inputs and not a
    restatement of one object.
    """

    def contract_for(run_id: str) -> RunContract:
        return load_run_contract(
            run_id=run_id,
            prompt_path=prompt_path,
            schema_path=schema_path,
            ontology_path=ontology_path,
            model_requested=MODEL,
            reasoning_requested=REASONING,
            execution_version=execution_version,
        )

    return StabilityExperiment(
        run_a=contract_for(run_a),
        run_b=contract_for(run_b),
        selection=load_selection(selection_path),
    )


@dataclass(frozen=True)
class ExtractionProvenance:
    """Everything one validated result must stay traceable to.

    The point is not bookkeeping. A future corpus analysis that averages assertions across
    runs which occupied different emission regimes would report a distribution that no run
    produced, and it would look perfectly well-formed. Every field below already exists in
    the execution contract; this record is where they are read together and checked.
    """

    run_id: str
    task_id: str
    attempt_id: str
    passage_id: str
    evidence_packet_sha256: str
    prompt_sha256: str
    prompt_version: str
    schema_sha256: str
    ontology_sha256: str
    model_requested: str
    reported_model: str
    runtime: str
    reasoning: str
    response_sha256: str
    raw_response_sha256: str
    #: Set when the result reached a run through a batch store; absent for direct custody.
    batch_id: str | None = None

    @classmethod
    def from_validated(
        cls,
        validated: ValidatedResponse,
        contract: RunContract,
        *,
        batch_id: str | None = None,
    ) -> ExtractionProvenance:
        task, receipt = validated.task, validated.receipt
        return cls(
            run_id=task.run_id,
            task_id=task.task_id,
            attempt_id=receipt.attempt_id,
            passage_id=task.passage_id,
            evidence_packet_sha256=task.evidence_packet_sha256,
            prompt_sha256=task.prompt_sha256,
            prompt_version=contract.prompt_version,
            schema_sha256=task.schema_sha256,
            ontology_sha256=task.ontology_sha256,
            model_requested=task.model_requested,
            reported_model=receipt.reported_model,
            runtime=receipt.runtime,
            reasoning=receipt.reasoning,
            response_sha256=receipt.response_sha256,
            raw_response_sha256=validated.raw_response_sha256,
            batch_id=batch_id,
        )

    def incomplete_fields(self) -> tuple[str, ...]:
        """Required provenance fields that are absent or empty. ``batch_id`` is optional."""
        return tuple(
            sorted(
                name
                for name, value in vars(self).items()
                if name != "batch_id" and not str(value or "").strip()
            )
        )


@dataclass(frozen=True)
class StabilityThresholds:
    """Engineering tolerances for the V3.2 gate.

    ``provenance`` is part of the type on purpose. None of these numbers is derived from a
    human annotation, because there is none; they are the values that separate the two
    regimes already observed. They are configurable and they are not evidence of accuracy.
    """

    no_claim_rate_gap: float = NO_CLAIM_RATE_GAP_ENGINEERING_DEFAULT
    #: The v3.1 runs differed by 0.40 assertions per passage over identical packets.
    assertion_density_gap: float = 0.30
    #: Occurrences of a predicate in one run and none in the other. Eight is where the
    #: exchangeable one-sided probability falls below
    #: ``ONE_SIDED_SKEW_PROBABILITY_ENGINEERING_DEFAULT``.
    one_sided_predicate_occurrences: int = 8
    one_sided_skew_probability: float = ONE_SIDED_SKEW_PROBABILITY_ENGINEERING_DEFAULT
    provenance: str = "engineering_default_not_truth_derived"


@dataclass(frozen=True)
class IntegrityCounts:
    """Execution-side failures. Any of these makes the semantic comparison meaningless."""

    receipt_failures: int = 0
    packet_hash_failures: int = 0
    evidence_failures: int = 0
    span_failures: int = 0
    binding_failures: int = 0
    ontology_type_failures: int = 0
    heuristic_contamination: int = 0
    canonical_target_contradictions: int = 0

    def failures(self) -> tuple[str, ...]:
        return tuple(sorted(name for name, count in vars(self).items() if count))


@dataclass(frozen=True)
class StabilityGateResult:
    """Whether V3.2 removed the run-level regime split. Not a correctness verdict.

    ``passed`` means two runs of one prompt behaved as one policy over identical packets.
    It says nothing about whether that policy reads the Rigveda correctly, and it is not
    an accuracy figure. Identical output is not the target either: local variance passes.
    """

    passed: bool
    failures: tuple[str, ...]
    thresholds: StabilityThresholds
    claim: str = "POLICY_STABILITY_ONLY_NOT_ACCURACY"


#: Shared frozen defaults; the gate never mutates either.
CLEAN_INTEGRITY = IntegrityCounts()
DEFAULT_THRESHOLDS = StabilityThresholds()


def stability_gate(
    comparison: RegimeComparison,
    integrity: IntegrityCounts = CLEAN_INTEGRITY,
    thresholds: StabilityThresholds = DEFAULT_THRESHOLDS,
) -> StabilityGateResult:
    """Fail the gate when two runs of one prompt did not behave as one policy."""
    failures: list[str] = [f"integrity: {name}" for name in integrity.failures()]
    if comparison.no_claim_rate_gap > thresholds.no_claim_rate_gap:
        failures.append(
            f"no-claim regime split: gap {comparison.no_claim_rate_gap:.3f} exceeds "
            f"{thresholds.no_claim_rate_gap:.3f}"
        )
    if comparison.density_gap > thresholds.assertion_density_gap:
        failures.append(
            f"assertion density split: gap {comparison.density_gap:.3f} exceeds "
            f"{thresholds.assertion_density_gap:.3f}"
        )
    for predicate in comparison.one_sided_predicates:
        left, right = comparison.predicate_counts[predicate]
        occurrences = max(left, right)
        skew = comparison.skew_probabilities.get(predicate, 1.0)
        if (
            occurrences >= thresholds.one_sided_predicate_occurrences
            or skew < thresholds.one_sided_skew_probability
        ):
            failures.append(
                f"one-sided predicate {predicate}: {left} against {right} "
                f"(exchangeable one-sided probability {skew:.2e})"
            )
    return StabilityGateResult(
        passed=not failures,
        failures=tuple(failures),
        thresholds=thresholds,
    )
