"""Run the pilot end to end and write what it produced.

The order is fixed and each step depends only on the ones before it:

    packet  ->  extract  ->  parse  ->  resolve entities  ->  validate  ->  decide  ->  write

The interesting property is what is *not* in that chain. Nothing reads back into the
canonical, traditional or lexical layers. The extractor cannot see the validator, so it
cannot learn to satisfy it. The acceptance policy cannot see the model's reasoning, only
its claim and its evidence. And ``unlocked_predicates`` — the one input that lets anything
be accepted without a person — comes from a gold evaluation, never from this run.

Outputs are written under ``data/semantic/`` and are gitignored. They contain evidence
identifiers and hashes, never Sanskrit or translation text: an assertion is verifiable by
anyone holding the same pinned build, without this repository redistributing a source.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from vedagraph.models.enums import SemanticAssertionStatus
from vedagraph.models.semantic import (
    EvidencePacket,
    SemanticAssertionCandidate,
    SemanticEntityCandidate,
    SemanticRunManifest,
    SemanticValidationResult,
    TokenUsage,
)
from vedagraph.semantic.evaluate import CostReport
from vedagraph.semantic.extract import (
    SCHEMA_NAME,
    ExtractionConfig,
    SemanticExtractorProvider,
    SystemPrompt,
)
from vedagraph.semantic.ontology import (
    ACCEPTANCE_POLICY_VERSION,
    ONTOLOGY_VERSION,
    SemanticPredicate,
)
from vedagraph.semantic.packet import PACKET_VERSION, PacketSources, build_packet
from vedagraph.semantic.registry import (
    ResolutionIndex,
    normalization_queue,
    resolve_entity_candidates,
)
from vedagraph.semantic.validate import (
    ParsedExtraction,
    check_deterministic_conflict,
    decide_status,
    parse_extraction,
    validate_structure,
)


@dataclass
class SemanticRunResult:
    """Everything one pilot run produced, in memory, before anything is written."""

    packets: dict[str, EvidencePacket] = field(default_factory=dict)
    parsed: dict[str, ParsedExtraction] = field(default_factory=dict)
    entity_candidates: list[SemanticEntityCandidate] = field(default_factory=list)
    assertions: list[SemanticAssertionCandidate] = field(default_factory=list)
    validations: dict[str, SemanticValidationResult] = field(default_factory=dict)
    usage: TokenUsage = field(default_factory=TokenUsage)
    failures: dict[str, str] = field(default_factory=dict)
    refusals: list[str] = field(default_factory=list)

    @property
    def parse_errors(self) -> list[tuple[str, str]]:
        """Replies that were schema-conformant but held a claim that could not be built.

        Reported rather than repaired. Guessing what the model meant is how an
        unsupported assertion enters the graph wearing a validator's approval.
        """
        return [
            (passage_key, message)
            for passage_key, parsed in sorted(self.parsed.items())
            for message in parsed.parse_errors
        ]

    def by_status(self, status: SemanticAssertionStatus) -> list[SemanticAssertionCandidate]:
        return [
            assertion
            for assertion in self.assertions
            if self.validations[assertion.candidate_assertion_id].status is status
        ]

    def predictions(self) -> dict[str, list[SemanticAssertionCandidate]]:
        grouped: dict[str, list[SemanticAssertionCandidate]] = {key: [] for key in self.packets}
        for assertion in self.assertions:
            grouped.setdefault(assertion.subject_key, []).append(assertion)
        return grouped


def run_pilot(
    passage_keys: Iterable[str],
    sources: PacketSources,
    provider: SemanticExtractorProvider,
    prompt: SystemPrompt,
    config: ExtractionConfig,
    *,
    canonical_entity_keys: frozenset[str],
    registry_index: ResolutionIndex,
    unlocked_predicates: frozenset[SemanticPredicate] = frozenset(),
) -> SemanticRunResult:
    """Extract, resolve and validate one set of mantras.

    ``unlocked_predicates`` defaults to empty, which means *nothing is auto-accepted*.
    That is the correct default for a first run: a predicate earns automatic acceptance
    by being measured against gold, and a run that has not been measured has not earned
    anything.
    """
    result = SemanticRunResult()

    for passage_key in passage_keys:
        packet = build_packet(sources, passage_key)
        result.packets[passage_key] = packet
        reply = provider.extract(packet, prompt)
        result.usage = result.usage + reply.usage
        if reply.refused:
            result.refusals.append(passage_key)
            continue
        if not reply.ok:
            result.failures[passage_key] = reply.error
            continue
        result.parsed[passage_key] = parse_extraction(
            packet,
            reply.payload,
            model=reply.model,
            model_snapshot=reply.model_snapshot,
            reasoning_effort=config.reasoning_effort,
            prompt_version=prompt.version,
            ontology_version=ONTOLOGY_VERSION,
            schema_name=SCHEMA_NAME,
        )

    proposals = [
        proposal for parsed in result.parsed.values() for proposal in parsed.entity_proposals
    ]
    result.entity_candidates = resolve_entity_candidates(
        proposals,
        registry_index,
        model=provider.model_identity(),
        prompt_version=prompt.version,
        ontology_version=ONTOLOGY_VERSION,
    )
    for passage_key, parsed in sorted(result.parsed.items()):
        packet = result.packets[passage_key]
        # A local id is scoped to the reply that invented it, so an assertion may only
        # point at an entity its own reply declared. Accepting another reply's local id
        # would silently join two packets' proposals into one claim.
        citable = frozenset(parsed.local_entity_ids)
        for candidate in parsed.candidates:
            codes = validate_structure(
                candidate,
                packet,
                canonical_entity_keys=canonical_entity_keys,
                resolved_candidate_ids=citable,
            )
            conflict = not codes and check_deterministic_conflict(candidate, packet)
            verdict = decide_status(
                candidate,
                codes,
                unlocked_predicates=unlocked_predicates,
                conflicts_with_metadata=conflict,
            )
            result.assertions.append(candidate.model_copy(update={"status": verdict.status}))
            result.validations[candidate.candidate_assertion_id] = verdict
    return result


def _write_jsonl(path: Path, rows: Iterable[object]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            payload = row.model_dump(mode="json") if hasattr(row, "model_dump") else row
            handle.write(json.dumps(payload, sort_keys=True, ensure_ascii=False) + "\n")
            count += 1
    return count


def write_outputs(
    result: SemanticRunResult,
    manifest: SemanticRunManifest,
    cost: CostReport,
    output_dir: Path,
) -> dict[str, int]:
    """Write the run's artefacts. Packets are stored as an index; no source text is kept."""
    written: dict[str, int] = {}
    written["semantic_candidates.jsonl"] = _write_jsonl(
        output_dir / "semantic_candidates.jsonl", result.assertions
    )
    written["semantic_entities_candidates.jsonl"] = _write_jsonl(
        output_dir / "semantic_entities_candidates.jsonl", result.entity_candidates
    )
    written["semantic_validation.jsonl"] = _write_jsonl(
        output_dir / "semantic_validation.jsonl",
        [result.validations[key] for key in sorted(result.validations)],
    )
    for filename, status in (
        ("accepted_semantic_assertions.jsonl", SemanticAssertionStatus.AUTO_ACCEPTED),
        ("review_semantic_assertions.jsonl", SemanticAssertionStatus.NEEDS_REVIEW),
        ("rejected_semantic_assertions.jsonl", SemanticAssertionStatus.VALIDATION_REJECTED),
    ):
        written[filename] = _write_jsonl(output_dir / filename, result.by_status(status))
    written["evidence_packet_index.jsonl"] = _write_jsonl(
        output_dir / "evidence_packet_index.jsonl",
        [result.packets[key].index_row() for key in sorted(result.packets)],
    )
    written["parse_errors.jsonl"] = _write_jsonl(
        output_dir / "parse_errors.jsonl",
        [
            {"passage_key": passage_key, "error": message}
            for passage_key, message in result.parse_errors
        ],
    )
    written["normalization_queue.jsonl"] = _write_jsonl(
        output_dir / "normalization_queue.jsonl",
        [
            {
                "entity_type": group.entity_type.value,
                "members": list(group.members),
                "labels": list(group.labels),
                "reason": group.reason,
            }
            for group in normalization_queue(result.entity_candidates)
        ],
    )

    (output_dir / "semantic_run_manifest.json").write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    (output_dir / "token_usage.json").write_text(
        json.dumps(result.usage.model_dump(mode="json"), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "cost_report.json").write_text(
        json.dumps(
            {
                "usage": cost.usage.model_dump(mode="json"),
                "passage_count": cost.passage_count,
                "uncached_input_tokens": cost.uncached_input_tokens,
                "average_input_tokens_per_request": cost.average_input_tokens,
                "average_output_tokens_per_request": cost.average_output_tokens,
                "total_cost_usd": cost.total_cost_usd,
                "cost_per_mantra_usd": cost.cost_per_mantra_usd,
                "projected_full_corpus_usd": cost.projected_full_corpus_usd,
                "projection_note": (
                    "A projection from the pilot's per-mantra token profile, not a "
                    "measurement. The pilot is stratified towards awkward mantras."
                ),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return written


def build_manifest(
    result: SemanticRunResult,
    *,
    run_id: str,
    dataset_id: str,
    started_at: datetime,
    corpus_version: str,
    corpus_manifest_sha256: str,
    lexical_policy_version: str,
    prompt: SystemPrompt,
    provider: SemanticExtractorProvider,
    config: ExtractionConfig,
    cost: CostReport,
    batch_count: int = 0,
    batch_size: int = 0,
    packet_hashes: dict[str, str] | None = None,
    output_hashes: dict[str, str] | None = None,
    qa_result: str = "",
    traditional_knowledge_manifest_sha256: str = "",
    lexical_knowledge_manifest_sha256: str = "",
    pilot_config_sha256: str = "",
    prompt_sha256: str = "",
) -> SemanticRunManifest:
    return SemanticRunManifest(
        run_id=run_id,
        dataset_id=dataset_id,
        started_at=started_at,
        finished_at=datetime.now(UTC),
        corpus_version=corpus_version,
        corpus_manifest_sha256=corpus_manifest_sha256,
        traditional_knowledge_manifest_sha256=traditional_knowledge_manifest_sha256,
        lexical_knowledge_manifest_sha256=lexical_knowledge_manifest_sha256,
        pilot_config_sha256=pilot_config_sha256,
        prompt_sha256=prompt_sha256,
        lexical_policy_version=lexical_policy_version,
        ontology_version=ONTOLOGY_VERSION,
        acceptance_policy_version=ACCEPTANCE_POLICY_VERSION,
        prompt_version=prompt.version,
        packet_version=PACKET_VERSION,
        schema_name=SCHEMA_NAME,
        provider=provider.name,
        extraction_runtime=("CODEX_DIRECT" if provider.name == "codex-direct" else "API"),
        api_invocation=(provider.name != "codex-direct"),
        model=provider.model_identity(),
        model_snapshot=next(
            (item.model_snapshot for item in result.assertions if item.model_snapshot), None
        ),
        reasoning_effort=config.reasoning_effort,
        max_output_tokens=config.max_output_tokens,
        temperature=config.temperature,
        passage_count=len(result.packets),
        usage=result.usage,
        input_cost_usd_per_million=config.input_usd_per_million,
        cached_input_cost_usd_per_million=config.cached_input_usd_per_million,
        output_cost_usd_per_million=config.output_usd_per_million,
        total_cost_usd=cost.total_cost_usd,
        batch_count=batch_count,
        batch_size=batch_size,
        unlocked_predicates=[],
        gold_status="UNANNOTATED",
        validator_version="rigveda-semantic-validator-v1",
        qa_result=qa_result,
        packet_hashes=packet_hashes or {},
        output_hashes=output_hashes or {},
        notes=(
            f"{len(result.refusals)} refusals, {len(result.failures)} failures, "
            f"{len(result.parse_errors)} unbuildable claims dropped. "
            "LLM output is not deterministic; the reproducibility claim is over the "
            "input packet hash, the prompt version and the model configuration only."
        ),
    )
