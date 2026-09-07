"""The Claude Opus 5 multi-agent V3.2 candidate run: identity, partition, assembly.

NO HUMAN GOLD EXISTS. MODEL SELF-AGREEMENT IS NOT ACCURACY.
CLAUDE OPUS 5 MODEL REVIEW IS NOT HUMAN GOLD.
ALL SEMANTIC OUTPUTS REMAIN CANDIDATE KNOWLEDGE.

This module is the Claude-side analogue of :mod:`vedagraph.semantic.v3_2`, and it exists
for one reason: a Claude-authored candidate may not be stored under a run identity that
claims Luna. The V3.2 prompt, payload schema, predicate ontology and typed-object schema
are reused byte-identically -- reusing the frozen extraction policy is the whole point of
the pilot -- while model, runtime and run identity are recorded as what they actually are.

What is *not* reused is the previous attempt's semantic content. The interrupted Luna run
left ten author inputs on disk; they are classified
``UNTRUSTED_ABANDONED_AUTHOR_INPUT`` and are never read by an author, a validator or the
importer. Only its EvidencePacket preparation is reused, and only after every packet hash
is re-verified against the manifest that froze it.

Like the Codex path, this module authors no semantics. It renders an evidence-only view
for an isolated per-passage author context, and it does the mechanical half of assembly:
resolving a quoted span to boundary-safe offsets, minting a deterministic candidate id,
and building the receipt. Every predicate, object kind, explicitness judgement and
evidence quote comes from the author context.

Two deliberate differences from the Luna assembler, both recorded in the run manifest:

**Candidate ids are globally unique.** The V3.2 prompt says a candidate id is derived from
run, mantra, predicate, evidence and ordinal. The Luna assembler used the ordinal alone,
so ordinal 1 named a different object in all 448 passages and cross-passage duplicate
detection was meaningless. Here the id is a digest of all five, so a duplicate id is a
real collision.

**Spans are boundary-safe and may name an occurrence.** The Luna assembler required a
quote to occur exactly once and matched it with :meth:`str.find`, which anchors ``man``
inside ``Pavamana``. This path uses :func:`vedagraph.semantic.spans.resolve_anchor`, so a
repeated quote is resolvable by naming its occurrence instead of failing, and no anchor
can land inside a word.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from vedagraph.models.semantic import EvidencePacket
from vedagraph.semantic.codex_direct import (
    ExecutionRuntime,
    RunContract,
    canonical_sha256,
    load_run_contract,
)
from vedagraph.semantic.object_ontology import SemanticObjectKind
from vedagraph.semantic.spans import resolve_anchor

RUN_ID = "vedagraph-rigveda-semantic-claude-opus5-v3.2-448-new-v1"

#: The run identity the interrupted attempt used. Its packets are reused; its ten partial
#: author inputs are not, and nothing here reads them.
ABANDONED_RUN_ID = "vedagraph-rigveda-semantic-user-selected-luna-v3.2-448-new-v1"
ABANDONED_RUN_CLASSIFICATION = "ABORTED_BEFORE_IMPORT_EXECUTION_CAPACITY_EXHAUSTED"
ABANDONED_AUTHOR_INPUT_CLASSIFICATION = "UNTRUSTED_ABANDONED_AUTHOR_INPUT"

EXECUTION_VERSION = "rigveda-semantic-execution-v3.2"

#: The model identity the environment reports for this agent runtime. Recorded, not
#: attested: no provider build identifier is available, exactly as for the Codex path.
MODEL = "claude-opus-5"
REASONING = "high"
RUNTIME = ExecutionRuntime.CLAUDE_CODE_DIRECT

#: How this run's provenance bucket is named wherever candidates are aggregated. It must
#: never be merged with a Luna or Sol bucket.
PROVENANCE_BUCKET = "CLAUDE_OPUS5_MAX_MULTI_AGENT_CANDIDATE_EXTRACTION"
MODEL_PROVENANCE_CLASSIFICATION = "AGENT_RUNTIME_SELF_REPORTED_UNATTESTED"

PROMPT_PATH = Path("prompts/semantic_extraction_v3.2.md")
SCHEMA_PATH = Path("schemas/semantic_extraction_v3.schema.json")
ONTOLOGY_PATH = Path("src/vedagraph/semantic/ontology.py")
OBJECT_ONTOLOGY_PATH = Path("src/vedagraph/semantic/object_ontology.py")
SPAN_VALIDATOR_PATH = Path("src/vedagraph/semantic/spans.py")
EVIDENCE_VALIDATOR_PATH = Path("src/vedagraph/semantic/evidence.py")
EXECUTION_CONTRACT_PATH = Path("src/vedagraph/semantic/codex_direct.py")

SELECTION_PATH = Path("data/builds/rigveda_semantic_v3_2_user_selected_luna_448_new.yaml")
RUN_ROOT = Path("data/semantic") / RUN_ID
ABANDONED_ROOT = Path("data/semantic") / ABANDONED_RUN_ID

EXPECTED_PASSAGES = 448
BATCH_SIZE = 24

#: Predicates whose canonical-entity object needs a TARGET anchor. Mirrors the frozen
#: contract set; kept as strings because the intermediate is plain JSON.
CANONICAL_TARGET_PREDICATES = frozenset({"INVOKES", "PRAISES", "DESCRIBES"})

FROZEN_INPUT_PATHS: dict[str, Path] = {
    "prompt_sha256": PROMPT_PATH,
    "schema_sha256": SCHEMA_PATH,
    "semantic_ontology_sha256": ONTOLOGY_PATH,
    "object_ontology_sha256": OBJECT_ONTOLOGY_PATH,
    "span_validator_sha256": SPAN_VALIDATOR_PATH,
    "evidence_validator_sha256": EVIDENCE_VALIDATOR_PATH,
    "execution_contract_sha256": EXECUTION_CONTRACT_PATH,
}


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frozen_hashes(root: Path = Path(".")) -> dict[str, str]:
    return {key: file_sha256(root / path) for key, path in sorted(FROZEN_INPUT_PATHS.items())}


def contract(root: Path = Path(".")) -> RunContract:
    """Pin the Claude run to the same frozen V3.2 bytes the Luna runs used."""
    return load_run_contract(
        run_id=RUN_ID,
        prompt_path=root / PROMPT_PATH,
        schema_path=root / SCHEMA_PATH,
        ontology_path=root / ONTOLOGY_PATH,
        model_requested=MODEL,
        reasoning_requested=REASONING,
        execution_version=EXECUTION_VERSION,
        runtime=RUNTIME,
    )


# --------------------------------------------------------------------------------------
# Deterministic partition
# --------------------------------------------------------------------------------------

GROUP_NAMES: tuple[str, ...] = ("A", "B", "C", "D", "E", "F", "G", "H")

PARTITION_RULE = (
    "sorted(passage_ids)[index] -> GROUP_NAMES[index % group_count]; "
    "round-robin over the lexicographic order of the frozen selection"
)


def partition(passage_ids: list[str], group_count: int) -> dict[str, list[str]]:
    """Round-robin the sorted selection across groups.

    Round-robin rather than contiguous blocks: contiguous blocks would hand one group all
    of Mandala 9, and any per-group difference would then be a difference between
    Mandalas rather than between agents. The multi-agent consistency audit needs groups
    that are comparable by construction.
    """
    if not 1 <= group_count <= len(GROUP_NAMES):
        raise ValueError(f"group count must be 1..{len(GROUP_NAMES)}")
    ordered = sorted(passage_ids)
    if len(set(ordered)) != len(ordered):
        raise ValueError("duplicate passage ids in partition input")
    groups: dict[str, list[str]] = {name: [] for name in GROUP_NAMES[:group_count]}
    for index, passage_id in enumerate(ordered):
        groups[GROUP_NAMES[index % group_count]].append(passage_id)
    return groups


def partition_hash(groups: dict[str, list[str]]) -> str:
    return canonical_sha256({name: sorted(ids) for name, ids in sorted(groups.items())})


# --------------------------------------------------------------------------------------
# Author-facing evidence view
# --------------------------------------------------------------------------------------


def author_view(packet: EvidencePacket) -> dict[str, Any]:
    """Everything an author context may see, and nothing else.

    Carries no predicate, no object, no explicitness, no historical output and no
    expected answer. The traditional Devatā and Chandas keys are included because the
    packet supplies them, and the V3.2 prompt is explicit that a Devatā assignment does
    not by itself establish an assertion.
    """
    translation = packet.translation
    return {
        "passage_id": packet.passage_key,
        "citation": packet.citation,
        "mandala": packet.mandala,
        "sukta": packet.sukta,
        "mantra": packet.mantra,
        "sanskrit": packet.sanskrit,
        "translation": None
        if translation is None
        else {
            "translation_id": translation.translation_id,
            "translator": translation.translator,
            "text": translation.text,
            "length": len(translation.text or ""),
        },
        "tokens": [
            {
                "token_key": token.token_key,
                "surface": token.surface,
                "lemma": token.lemma,
                "pada": token.pada,
                "part_of_speech": token.part_of_speech,
                "morphology": token.morphology,
            }
            for token in packet.tokens
        ],
        "translation_missing": packet.translation_missing,
        "lexical_mentions": [
            {
                "entity_key": mention.entity_key,
                "entity_label": mention.entity_label,
                "occurrence_count": mention.occurrence_count,
                "token_keys": list(mention.token_keys),
            }
            for mention in packet.mentions
        ],
        "traditional_devata_keys": list(packet.devata_keys),
        "traditional_devata_labels": list(packet.devata_labels),
        "traditional_rishi_labels": list(packet.rishi_labels),
        "chandas_labels": list(packet.chandas_labels),
        "neighbours": {
            "previous": None
            if packet.previous is None
            else {
                "citation": packet.previous.citation,
                "sanskrit": packet.previous.sanskrit,
                "translation": None
                if packet.previous.translation is None
                else packet.previous.translation.text,
            },
            "next": None
            if packet.next is None
            else {
                "citation": packet.next.citation,
                "sanskrit": packet.next.sanskrit,
                "translation": None
                if packet.next.translation is None
                else packet.next.translation.text,
            },
        },
        "exact_parallel_passage_keys": list(packet.exact_parallel_passage_keys),
        "near_parallel_passage_keys": list(packet.near_parallel_passage_keys),
        "packet_sha256": packet.input_sha256,
    }


# --------------------------------------------------------------------------------------
# Mechanical assembly
# --------------------------------------------------------------------------------------


class AuthorInputError(ValueError):
    """The author's intermediate JSON cannot be assembled. Always a FORMAT failure."""


def candidate_id_for(
    *, run_id: str, passage_id: str, predicate: str, spans: tuple[int, int, int, int], ordinal: int
) -> str:
    """Derive an occurrence id from run, mantra, predicate, evidence and ordinal."""
    evidence = f"{spans[0]}:{spans[1]}|{spans[2]}:{spans[3]}"
    seed = f"{run_id}|{passage_id}|{predicate}|{evidence}|{ordinal}"
    return "VG:SEMOBJ:" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:20].upper()


def _anchor(*, passage_key: str, translation_id: str, start: int, end: int) -> dict[str, Any]:
    return {
        "source_passage_id": passage_key,
        "passage_ids": [passage_key],
        "token_ids": [],
        "other_evidence_ids": [],
        "translation_record_id": translation_id,
        "translation_span": {"start": start, "end": end},
    }


def _resolve(text: str, quote: object, occurrence: object, *, label: str) -> tuple[int, int]:
    if not isinstance(quote, str) or not quote:
        raise AuthorInputError(f"{label}: quote must be a non-empty string")
    if occurrence is not None and not isinstance(occurrence, int):
        raise AuthorInputError(f"{label}: occurrence must be an integer when supplied")
    try:
        anchor = resolve_anchor(text, quote, occurrence=occurrence)
    except ValueError as exc:
        raise AuthorInputError(f"{label}: {exc}") from exc
    return anchor.start, anchor.end


def assemble(
    intermediate: dict[str, Any], task: Any, run_contract: RunContract
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Turn one author context's semantic decisions into schema-shaped output plus bindings.

    Raises :class:`AuthorInputError` for anything the author must fix. It never repairs a
    semantic decision, and it never supplies one that is missing.
    """
    packet = task.evidence_packet
    translation = packet.translation
    text = translation.text if translation else ""
    translation_id = translation.translation_id if translation else ""
    mention_keys = {mention.entity_key for mention in packet.mentions}

    if intermediate.get("no_claim"):
        reasons = intermediate.get("no_claim_reasons") or []
        if (
            not isinstance(reasons, list)
            or not reasons
            or not all(isinstance(item, str) and item for item in reasons)
        ):
            raise AuthorInputError("no_claim requires at least one non-empty reason string")
        if intermediate.get("assertions"):
            raise AuthorInputError("no_claim may not coexist with assertions")
        return (
            {
                "mantra_id": packet.citation,
                "assertions": [],
                "no_claim_reasons": reasons,
                "ontology_gaps": [],
                "object_schema_version": "rigveda-semantic-object-v1",
                "prompt_version": "rigveda-semantic-extraction-v3",
            },
            [],
        )

    raw_assertions = intermediate.get("assertions")
    if not isinstance(raw_assertions, list) or not raw_assertions:
        raise AuthorInputError("supply a non-empty assertions list or set no_claim")

    assertions: list[dict[str, Any]] = []
    bindings: list[dict[str, Any]] = []
    for ordinal, raw in enumerate(raw_assertions, start=1):
        label = f"assertion {ordinal}"
        if not isinstance(raw, dict):
            raise AuthorInputError(f"{label}: must be an object")
        obj = raw.get("object")
        if not isinstance(obj, dict):
            raise AuthorInputError(f"{label}: object must be an object")
        predicate = raw.get("predicate")
        object_kind = obj.get("object_kind")
        if not isinstance(predicate, str) or not isinstance(object_kind, str):
            raise AuthorInputError(f"{label}: predicate and object_kind must be strings")
        explicitness = raw.get("explicitness")
        if explicitness not in {"EXPLICIT", "STRONG_INFERENCE"}:
            raise AuthorInputError(f"{label}: explicitness must be EXPLICIT or STRONG_INFERENCE")

        relation_start, relation_end = _resolve(
            text,
            raw.get("relation_quote"),
            raw.get("relation_occurrence"),
            label=f"{label} relation",
        )
        object_start, object_end = _resolve(
            text, obj.get("object_quote"), obj.get("object_occurrence"), label=f"{label} object"
        )
        canonical_entity_id = obj.get("canonical_entity_id")
        if object_kind == SemanticObjectKind.CANONICAL_ENTITY_REF.value and (
            not canonical_entity_id or canonical_entity_id not in mention_keys
        ):
            raise AuthorInputError(
                f"{label}: canonical_entity_id {canonical_entity_id!r} is not a supplied "
                "lexical mention"
            )
        candidate_id = candidate_id_for(
            run_id=run_contract.run_id,
            passage_id=packet.passage_key,
            predicate=predicate,
            spans=(relation_start, relation_end, object_start, object_end),
            ordinal=ordinal,
        )
        assertion_id = f"C32A:{candidate_id}"
        object_payload = {
            "candidate_id": candidate_id,
            "object_kind": object_kind,
            "display_label": obj.get("display_label"),
            "normalized_head": obj.get("normalized_head"),
            "canonical_entity_id": canonical_entity_id,
            "target_entity_id": obj.get("target_entity_id"),
            "beneficiary_entity_id": obj.get("beneficiary_entity_id"),
            "event": obj.get("event"),
            "ontology_gap_code": obj.get("ontology_gap_code"),
            "qualifiers": obj.get("qualifiers", []),
            "source_passage_id": packet.passage_key,
            "evidence": [
                _anchor(
                    passage_key=packet.passage_key,
                    translation_id=translation_id,
                    start=object_start,
                    end=object_end,
                )
            ],
            "extraction_model": run_contract.model_requested,
            "prompt_version": run_contract.prompt_version,
            "normalization_status": (
                "CANONICAL_REF"
                if object_kind == SemanticObjectKind.CANONICAL_ENTITY_REF.value
                else "ONTOLOGY_GAP"
                if object_kind == SemanticObjectKind.ONTOLOGY_GAP_REF.value
                else "NORMALIZED_CANDIDATE"
            ),
            "legacy_object_id": None,
            "schema_version": "rigveda-semantic-object-v1",
        }
        assertions.append(
            {
                "assertion_id": assertion_id,
                "source_run_id": run_contract.run_id,
                "subject_id": packet.passage_key,
                "predicate": predicate,
                "object": object_payload,
                "evidence": [
                    _anchor(
                        passage_key=packet.passage_key,
                        translation_id=translation_id,
                        start=relation_start,
                        end=relation_end,
                    )
                ],
                "explicitness": explicitness,
                "inference_step": raw.get("inference_step"),
                "legacy_assertion_id": None,
                "schema_version": "rigveda-semantic-object-v1",
            }
        )
        anchors: list[dict[str, Any]] = [
            {
                "role": "RELATION",
                "translation_record_id": translation_id,
                "start": relation_start,
                "end": relation_end,
                "text": text[relation_start:relation_end],
                "entity_id": None,
            }
        ]
        if (
            object_kind == SemanticObjectKind.CANONICAL_ENTITY_REF.value
            and predicate in CANONICAL_TARGET_PREDICATES
        ):
            anchors.append(
                {
                    "role": "TARGET",
                    "translation_record_id": translation_id,
                    "start": object_start,
                    "end": object_end,
                    "text": text[object_start:object_end],
                    "entity_id": canonical_entity_id,
                }
            )
        if predicate == "REQUESTS":
            anchors.append(
                {
                    "role": "OUTCOME",
                    "translation_record_id": translation_id,
                    "start": object_start,
                    "end": object_end,
                    "text": text[object_start:object_end],
                    "entity_id": None,
                }
            )
        bindings.append({"assertion_id": assertion_id, "anchors": anchors})

    return (
        {
            "mantra_id": packet.citation,
            "assertions": assertions,
            "no_claim_reasons": [],
            "ontology_gaps": [],
            "object_schema_version": "rigveda-semantic-object-v1",
            "prompt_version": "rigveda-semantic-extraction-v3",
        },
        bindings,
    )


def load_intermediate(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise AuthorInputError(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise AuthorInputError(f"{path} must hold a JSON object")
    return value
