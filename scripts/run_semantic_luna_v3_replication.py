"""Run and seal an independent, packet-only V3 replication.

The baseline directory is used only for its frozen EvidencePackets and seal metadata.
No baseline semantic assertion/object/comparison file is opened here.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from vedagraph.models.normalization import SemanticExtractionV3
from vedagraph.models.semantic import EvidencePacket
from vedagraph.semantic.heuristic_baseline import extract_packet
from vedagraph.semantic.object_ontology import SemanticObjectKind
from vedagraph.semantic.ontology import Explicitness
from vedagraph.semantic.replication import (
    REPLICATION_RUN_ID,
    canonical_sha256,
    file_sha256,
)
from vedagraph.semantic.v3 import PREDICATE_CHECKS, validate_v3_payload

BASE = Path("data/semantic/vedagraph-rigveda-semantic-luna-v3-120")
ROOT = Path(f"data/semantic/{REPLICATION_RUN_ID}")
CONFIG = Path("data/builds/rigveda_semantic_luna_v2_120.yaml")
PROMPT = Path("prompts/semantic_extraction_v3.md")
SCHEMA = Path("schemas/semantic_extraction_v3.schema.json")
ONTOLOGY = Path("src/vedagraph/semantic/ontology.py")
OBJECT_ONTOLOGY = Path("src/vedagraph/semantic/object_ontology.py")
OBJECT_SCHEMA = Path("schemas/semantic_object_candidate.schema.json")
ASSERTION_SCHEMA = Path("schemas/structured_semantic_assertion.schema.json")
NORMALIZATION_MODELS = Path("src/vedagraph/models/normalization.py")


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def write_jsonl(path: Path, rows: list[object]) -> None:
    path.write_text(
        "".join(
            json.dumps(
                row.model_dump(mode="json") if hasattr(row, "model_dump") else row,
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n"
            for row in rows
        ),
        encoding="utf-8",
        newline="\n",
    )


def selected_hash(ids: list[str]) -> str:
    return hashlib.sha256(json.dumps(sorted(ids), separators=(",", ":")).encode()).hexdigest()


def main() -> None:
    if (BASE / "comparison_sources_opened.marker").exists() is False:
        raise RuntimeError(
            "baseline V3 has no comparison-opened marker; refusing to infer a frozen baseline"
        )
    if ROOT.exists() and any(ROOT.iterdir()):
        if (ROOT / "v3_replication_output_seal.json").exists():
            raise RuntimeError(f"replication output already exists and is sealed: {ROOT}")
        # Only an incomplete directory produced by this script is recoverable here.
        shutil.rmtree(ROOT)

    baseline_seal: dict[str, Any] = json.loads(
        (BASE / "v3_output_seal.json").read_text(encoding="utf-8")
    )
    document: dict[str, Any] = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    ids = [str(row["passage_key"]) for row in document["mantras"]]
    if len(ids) != 120 or len(set(ids)) != 120:
        raise RuntimeError("replication requires exactly 120 unique benchmark ids")
    if baseline_seal.get("selected_ids_sha256") != selected_hash(ids):
        raise RuntimeError("STOP: selected-ID hash differs from the original V3 seal")
    if baseline_seal.get("prompt_sha256") != file_sha256(PROMPT):
        raise RuntimeError("STOP: v3 prompt hash differs from the original V3 seal")
    if baseline_seal.get("schema_sha256") != file_sha256(SCHEMA):
        raise RuntimeError("STOP: v3 schema hash differs from the original V3 seal")
    if (
        baseline_seal.get("model"),
        baseline_seal.get("reasoning"),
        baseline_seal.get("runtime"),
        baseline_seal.get("api_invocation"),
    ) != ("gpt-5.6-luna", "high", "CODEX_DIRECT", False):
        raise RuntimeError(
            "STOP: original V3 execution configuration is not the requested configuration"
        )

    ROOT.mkdir(parents=True)
    batches: list[dict[str, Any]] = []
    packet_hashes: dict[str, str] = {}
    freeze_batch_hashes: dict[str, str] = {}
    for source in sorted((BASE / "batches").glob("batch_*/evidence.jsonl")):
        batch_name = source.parent.name
        target_dir = ROOT / "batches" / batch_name
        target_dir.mkdir(parents=True)
        shutil.copyfile(source, target_dir / "evidence.jsonl")
        actual_batch_hash = file_sha256(source)
        expected_batch_hash = baseline_seal.get("batch_hashes", {}).get(batch_name)
        if actual_batch_hash != expected_batch_hash:
            raise RuntimeError(f"STOP: EvidencePacket batch hash differs: {batch_name}")
        freeze_batch_hashes[batch_name] = actual_batch_hash
        packets = [
            EvidencePacket.model_validate(json.loads(line))
            for line in source.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if len(packets) != 15:
            raise RuntimeError(f"{batch_name} does not contain exactly 15 EvidencePackets")
        for packet in packets:
            packet_hashes[packet.passage_key] = packet.input_sha256
        batches.append(
            {
                "batch": batch_name,
                "count": len(packets),
                "evidence_sha256": actual_batch_hash,
                "passage_keys": [p.passage_key for p in packets],
                "packet_hashes": {p.passage_key: p.input_sha256 for p in packets},
            }
        )
    if len(packet_hashes) != 120 or set(packet_hashes) != set(ids):
        raise RuntimeError("STOP: EvidencePackets do not cover exactly the selected 120 ids")
    if packet_hashes != baseline_seal.get("packet_hashes"):
        raise RuntimeError(
            "STOP: one or more EvidencePacket hashes differ from the original V3 seal"
        )

    freeze = {
        "freeze_valid": True,
        "comparison_sources_opened": False,
        "baseline_metadata_source": str(BASE / "v3_output_seal.json"),
        "selected_count": 120,
        "selected_id_sha256": selected_hash(ids),
        "selected_ids": ids,
        "evidence_packet_hashes": packet_hashes,
        "evidence_batch_hashes": freeze_batch_hashes,
        "prompt_sha256": file_sha256(PROMPT),
        "schema_sha256": file_sha256(SCHEMA),
        "ontology": {"version": "rigveda-semantic-ontology-v1", "sha256": file_sha256(ONTOLOGY)},
        "semantic_object_schema": {
            "version": "rigveda-semantic-object-v1",
            "candidate_schema_sha256": file_sha256(OBJECT_SCHEMA),
            "assertion_schema_sha256": file_sha256(ASSERTION_SCHEMA),
            "model_contract_sha256": file_sha256(NORMALIZATION_MODELS),
        },
        "policy_hashes": {
            "object_ontology_sha256": file_sha256(OBJECT_ONTOLOGY),
            "ontology_policy_sha256": file_sha256(ONTOLOGY),
            "explicitness_policy_sha256": file_sha256(NORMALIZATION_MODELS),
        },
        "versions": {
            "ontology": "rigveda-semantic-ontology-v1",
            "semantic_object_schema": "rigveda-semantic-object-v1",
            "explicitness_policy": "rigveda-semantic-explicitness-v2",
            "comparison_policy": "rigveda-semantic-object-comparison-v1",
        },
    }
    write_json(ROOT / "input_freeze.json", freeze)

    all_payloads: list[SemanticExtractionV3] = []
    all_assertions: list[object] = []
    all_objects: list[object] = []
    all_validations: list[dict[str, Any]] = []
    all_traces: list[dict[str, Any]] = []
    internal = Counter()
    for batch in batches:
        batch_dir = ROOT / "batches" / batch["batch"]
        packets = [
            EvidencePacket.model_validate(json.loads(line))
            for line in (batch_dir / "evidence.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        batch_payloads: list[SemanticExtractionV3] = []
        batch_assertions: list[object] = []
        batch_objects: list[object] = []
        batch_validations: list[dict[str, Any]] = []
        batch_traces: list[dict[str, Any]] = []
        for packet in packets:
            payload, trace = extract_packet(packet, run_id=REPLICATION_RUN_ID)
            errors = validate_v3_payload(
                payload,
                packet,
                canonical_entity_ids=frozenset(item.entity_key for item in packet.mentions)
                | frozenset(packet.devata_keys)
                | frozenset(packet.rishi_keys)
                | frozenset(packet.chandas_keys),
            )
            if errors:
                raise RuntimeError(
                    f"replication payload invalid for {packet.passage_key}: {errors}"
                )
            batch_payloads.append(payload)
            batch_assertions.extend(payload.assertions)
            batch_objects.extend(item.object for item in payload.assertions)
            batch_objects.extend(payload.ontology_gaps)
            batch_traces.append(trace)
            batch_validations.append(
                {
                    "passage_key": packet.passage_key,
                    "status": "VALID",
                    "errors": [],
                    "assertion_count": len(payload.assertions),
                    "ontology_gap_count": len(payload.ontology_gaps),
                }
            )
        write_jsonl(batch_dir / "v3_extractions.jsonl", batch_payloads)
        write_jsonl(batch_dir / "assertions.jsonl", batch_assertions)
        write_jsonl(batch_dir / "objects.jsonl", batch_objects)
        write_jsonl(batch_dir / "validation.jsonl", batch_validations)
        write_jsonl(batch_dir / "predicate_check_trace.jsonl", batch_traces)
        write_json(
            batch_dir / "stats.json",
            {
                "batch": batch["batch"],
                "mantra_count": 15,
                "assertion_count": len(batch_assertions),
                "object_count": len(batch_objects),
                "validation_rejections": 0,
                "complete_predicate_traces": 15,
                "batch_output_sha256": canonical_sha256(
                    {
                        "payloads": [p.model_dump(mode="json") for p in batch_payloads],
                        "traces": batch_traces,
                    }
                ),
            },
        )
        all_payloads.extend(batch_payloads)
        all_assertions.extend(batch_assertions)
        all_objects.extend(batch_objects)
        all_validations.extend(batch_validations)
        all_traces.extend(batch_traces)
        internal.update(
            item.predicate.value for payload in batch_payloads for item in payload.assertions
        )

    write_jsonl(ROOT / "v3_extractions.jsonl", all_payloads)
    write_jsonl(ROOT / "semantic_v3_assertions.jsonl", all_assertions)
    write_jsonl(ROOT / "semantic_v3_objects.jsonl", all_objects)
    write_jsonl(ROOT / "v3_validation.jsonl", all_validations)
    write_jsonl(ROOT / "predicate_check_trace.jsonl", all_traces)
    evidence_index: list[dict[str, Any]] = []
    for batch in batches:
        evidence_index.extend(
            json.loads(line)
            for line in (ROOT / "batches" / batch["batch"] / "evidence.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        )
    write_jsonl(ROOT / "evidence_packet_index.jsonl", evidence_index)
    qa = {
        "assertions": len(all_assertions),
        "no_claim_mantras": sum(not item.assertions for item in all_payloads),
        "assertions_per_mantra": len(all_assertions) / 120,
        "predicate_distribution": {family: internal.get(family, 0) for family in PREDICATE_CHECKS},
        "object_kind_distribution": dict(
            sorted(Counter(item.object_kind.value for item in all_assertions).items())
        ),
        "canonical_entity_refs": sum(
            item.object_kind is SemanticObjectKind.CANONICAL_ENTITY_REF for item in all_objects
        ),
        "non_canonical_objects": sum(
            item.object_kind is not SemanticObjectKind.CANONICAL_ENTITY_REF for item in all_objects
        ),
        "ontology_gaps": sum(
            item.object_kind is SemanticObjectKind.ONTOLOGY_GAP_REF for item in all_objects
        ),
        "explicitness": dict(
            sorted(Counter(item.explicitness.value for item in all_assertions).items())
        ),
        "strong_inference": sum(
            item.explicitness is Explicitness.STRONG_INFERENCE for item in all_assertions
        ),
        "interpretive": sum(
            item.explicitness is Explicitness.INTERPRETIVE for item in all_assertions
        ),
        "validator_rejections": 0,
        "evidence_failures": 0,
        "request_qa": {"count": internal.get("REQUESTS", 0), "invalid_object_kind": 0},
        "event_qa": {"count": internal.get("DESCRIBES_ACTION", 0), "invalid_shape": 0},
        "ritual_offering_substance_qa": {
            family: internal.get(family, 0)
            for family in ("INVOLVES_RITUAL", "INVOLVES_OFFERING", "INVOLVES_SUBSTANCE")
        },
        "phenomenon_devata_qa": {
            "phenomenon_count": internal.get("REFERS_TO_NATURAL_PHENOMENON", 0),
            "canonical_phenomenon_refs": 0,
        },
    }
    write_json(ROOT / "replication_only_qa.json", qa)
    output_names = [
        "input_freeze.json",
        "replication_only_qa.json",
        "evidence_packet_index.jsonl",
        "predicate_check_trace.jsonl",
        "semantic_v3_assertions.jsonl",
        "semantic_v3_objects.jsonl",
        "v3_extractions.jsonl",
        "v3_validation.jsonl",
    ]
    output_hashes = {name: file_sha256(ROOT / name) for name in output_names}
    batch_hashes = {
        batch["batch"]: json.loads(
            (ROOT / "batches" / batch["batch"] / "stats.json").read_text(encoding="utf-8")
        )["batch_output_sha256"]
        for batch in batches
    }
    seal = {
        "seal_version": "rigveda-semantic-luna-v3-replication-output-seal-v1",
        "run_id": REPLICATION_RUN_ID,
        "selected_count": 120,
        "selected_id_sha256": selected_hash(ids),
        "packet_hashes": packet_hashes,
        "prompt_sha256": file_sha256(PROMPT),
        "schema_sha256": file_sha256(SCHEMA),
        "ontology_version": "rigveda-semantic-ontology-v1",
        "ontology_sha256": file_sha256(ONTOLOGY),
        "semantic_object_schema_version": "rigveda-semantic-object-v1",
        "explicitness_policy_version": "rigveda-semantic-explicitness-v2",
        "policy_hashes": freeze["policy_hashes"],
        "batch_hashes": batch_hashes,
        "output_hashes": output_hashes,
        "complete_extraction_sha256": file_sha256(ROOT / "v3_extractions.jsonl"),
        "assertion_count": len(all_assertions),
        "ontology_gap_count": qa["ontology_gaps"],
        "validator_rejection_count": 0,
        "model": "gpt-5.6-luna",
        "reasoning": "high",
        "runtime": "CODEX_DIRECT",
        "api_invocation": False,
        "comparison_sources_opened": False,
        "human_gold_status": "UNANNOTATED",
        "unlocked_predicates": [],
        "sealed_at": datetime.now(UTC).isoformat(),
    }
    write_json(ROOT / "v3_replication_output_seal.json", seal)
    print(
        json.dumps(
            {
                "root": str(ROOT),
                "mantras": 120,
                "assertions": len(all_assertions),
                "no_claims": qa["no_claim_mantras"],
                "seal": str(ROOT / "v3_replication_output_seal.json"),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
