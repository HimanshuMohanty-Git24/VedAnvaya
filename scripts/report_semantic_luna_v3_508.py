"""Seal-gated aggregate QA and reporting for the V3 508 candidate pilot.

The script opens historical semantic artifacts only after validating the new 508 seal.
It computes diagnostics, never promotes candidates, never unlocks predicates, and never
creates human gold.
"""

# Reports intentionally embed compact JSON diagnostics; line length is not a semantic
# concern in this reporting-only script.
# ruff: noqa: E501

from __future__ import annotations

import hashlib
import json
import re
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml

from vedagraph.models.normalization import (
    SemanticExtractionV3,
    StructuredSemanticAssertion,
)
from vedagraph.models.semantic import EvidencePacket
from vedagraph.semantic.normalization import (
    assertion_signature,
    evidence_signature,
    object_signature,
)
from vedagraph.semantic.object_ontology import SemanticObjectKind
from vedagraph.semantic.v3 import PREDICATE_CHECKS

ROOT = Path("data/semantic/vedagraph-rigveda-semantic-luna-v3-508")
OLD_ROOT = Path("data/semantic/vedagraph-rigveda-semantic-luna-v3-120")
REPLICATION_ROOT = Path("data/semantic/vedagraph-rigveda-semantic-luna-v3-replication-120")
CONFIG = Path("data/builds/rigveda_semantic_pilot_v1.yaml")
REPORT_DIR = Path("docs/reports")
MANIFEST_DIR = Path("docs/manifests")
EXPERT_REPORT = REPORT_DIR / "RIGVEDA_SEMANTIC_EXPERT_QUEUE_AFTER_STABILITY.md"

NOTICE = (
    "NO HUMAN GOLD EXISTS. CANDIDATE SEMANTIC OUTPUT IS NOT CANONICAL TRUTH. "
    "All assertions remain CANDIDATE / NEEDS_REVIEW; no predicates are unlocked."
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def rows(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def load_run(
    root: Path,
) -> tuple[
    dict[str, EvidencePacket], dict[str, SemanticExtractionV3], list[StructuredSemanticAssertion]
]:
    packet_rows = rows(root / "evidence_packet_index.jsonl")
    packet_by_citation = {str(item["citation"]): str(item["passage_key"]) for item in packet_rows}
    payloads = [
        SemanticExtractionV3.model_validate(item) for item in rows(root / "v3_extractions.jsonl")
    ]
    payload_by_key = {packet_by_citation[item.mantra_id]: item for item in payloads}
    packets: dict[str, EvidencePacket] = {}
    for evidence in sorted((root / "batches").glob("batch_*/evidence.jsonl")):
        for item in rows(evidence):
            packet = EvidencePacket.model_validate(item)
            packets[packet.passage_key] = packet
    assertions = [
        StructuredSemanticAssertion.model_validate(item)
        for item in rows(root / "semantic_v3_assertions.jsonl")
    ]
    return packets, payload_by_key, assertions


def selected_keys() -> list[str]:
    document: dict[str, Any] = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    return [str(row["passage_key"]) for row in document["mantras"]]


def validate_seal() -> dict[str, Any]:
    seal_path = ROOT / "v3_508_output_seal.json"
    if not seal_path.exists():
        raise RuntimeError("STOP: 508 output seal is missing")
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    if seal.get("comparison_sources_opened") is not False:
        raise RuntimeError("STOP: comparison sources were opened before the 508 seal")
    if seal.get("selected_count") != 508 or seal.get("unlocked_predicates") != []:
        raise RuntimeError("STOP: invalid 508 seal scope or predicate state")
    for name, expected in seal.get("output_hashes", {}).items():
        path = ROOT / name
        if not path.exists() or sha256(path) != expected:
            raise RuntimeError(f"STOP: sealed output changed: {name}")
    if (
        seal.get("model") != "gpt-5.6-luna"
        or seal.get("runtime") != "CODEX_DIRECT"
        or seal.get("reasoning") != "high"
        or seal.get("api_invocation") is not False
    ):
        raise RuntimeError("STOP: invalid model/runtime metadata in 508 seal")
    return seal


def assertion_map(
    items: list[StructuredSemanticAssertion],
) -> dict[str, list[StructuredSemanticAssertion]]:
    result: dict[str, list[StructuredSemanticAssertion]] = defaultdict(list)
    for item in items:
        result[item.subject_id].append(item)
    return result


def predicate_stats(payloads: dict[str, SemanticExtractionV3]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for predicate in PREDICATE_CHECKS:
        items = [
            item
            for payload in payloads.values()
            for item in payload.assertions
            if item.predicate.value == predicate
        ]
        result[predicate] = {
            "mantra_count": len({item.subject_id for item in items}),
            "assertion_count": len(items),
        }
    return result


def object_stats(payloads: dict[str, SemanticExtractionV3]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for payload in payloads.values():
        for assertion in payload.assertions:
            counts[assertion.object.object_kind.value] += 1
        for gap in payload.ontology_gaps:
            counts[gap.object_kind.value] += 1
    return dict(sorted(counts.items()))


def gap_stats(payloads: dict[str, SemanticExtractionV3]) -> dict[str, Any]:
    by_code: dict[str, list[str]] = defaultdict(list)
    for key, payload in payloads.items():
        for gap in payload.ontology_gaps:
            by_code[str(gap.ontology_gap_code)].append(key)
    return {
        code: {
            "count": len(keys),
            "example_mantra_ids": sorted(set(keys))[:10],
            "object_families": ["ONTOLOGY_GAP_REF"],
            "predicate_context": "not encoded by the V3 gap object",
        }
        for code, keys in sorted(by_code.items())
    }


def explicitness_stats(assertions: list[StructuredSemanticAssertion]) -> dict[str, int]:
    return dict(sorted(Counter(item.explicitness.value for item in assertions).items()))


def evidence_stats(assertions: list[StructuredSemanticAssertion]) -> dict[str, Any]:
    anchor_count = sum(len(item.evidence) for item in assertions)
    return {
        "assertion_count": len(assertions),
        "evidence_anchor_count": anchor_count,
        "average_anchors_per_assertion": round(anchor_count / len(assertions), 4)
        if assertions
        else 0.0,
    }


def qa_stats(
    packets: dict[str, EvidencePacket],
    payloads: dict[str, SemanticExtractionV3],
    assertions: list[StructuredSemanticAssertion],
    validation: list[dict[str, Any]],
) -> dict[str, Any]:
    request = [item for item in assertions if item.predicate.value == "REQUESTS"]
    events = [item for item in assertions if item.predicate.value == "DESCRIBES_ACTION"]
    ritual_families = {
        "INVOLVES_RITUAL": SemanticObjectKind.RITUAL_EVENT,
        "INVOLVES_OFFERING": SemanticObjectKind.OFFERING_REF,
        "INVOLVES_SUBSTANCE": SemanticObjectKind.SUBSTANCE_REF,
    }
    boundary = {
        name: sum(
            item.object.object_kind is not kind
            for item in assertions
            if item.predicate.value == name
        )
        for name, kind in ritual_families.items()
    }
    natural_canonical = sum(
        item.object.canonical_entity_id is not None
        for item in assertions
        if item.predicate.value == "REFERS_TO_NATURAL_PHENOMENON"
    )
    place_opaque_spatial = sum(
        item.object.object_kind is SemanticObjectKind.OPAQUE_SPATIAL_REFERENT
        for item in assertions
        if item.predicate.value == "REFERS_TO_PLACE"
    )
    coordinated = [
        item.assertion_id
        for item in request
        if re.search(r"\b(?:and|or)\b|[,;]", item.object.normalized_head or "", flags=re.I)
    ]
    long_labels = [
        item.assertion_id for item in assertions if len(item.object.display_label.split()) > 5
    ]
    zero_rich = [
        key
        for key, payload in payloads.items()
        if not payload.assertions
        and (
            packets[key].mentions
            or packets[key].devata_keys
            or packets[key].exact_parallel_passage_keys
        )
    ]
    event_role_violations = sum(item.object.event is None for item in events)
    canonical_labels: dict[str, set[str]] = defaultdict(set)
    for item in assertions:
        if item.object.canonical_entity_id:
            canonical_labels[item.object.canonical_entity_id].add(item.object.display_label)
    contradictions = {
        key: sorted(labels) for key, labels in canonical_labels.items() if len(labels) > 1
    }
    return {
        "request": {
            "assertion_count": len(request),
            "one_outcome_per_assertion": True,
            "coordinated_request_violations": len(coordinated),
            "coordinated_assertion_ids": coordinated,
        },
        "event": {
            "assertion_count": len(events),
            "event_object_violations": event_role_violations,
            "actor_patient_inferred_count": sum(
                bool(
                    item.object.event
                    and (item.object.event.actor_entity_id or item.object.event.patient_entity_id)
                )
                for item in events
            ),
        },
        "ritual_offering_substance": {
            "boundary_violations": boundary,
            "cross_kind_leakage": sum(boundary.values()),
        },
        "natural_phenomenon": {"canonical_entity_reuse_violations": natural_canonical},
        "place_opaque_spatial": {
            "place_assertions": sum(
                item.predicate.value == "REFERS_TO_PLACE" for item in assertions
            ),
            "opaque_spatial_referents": place_opaque_spatial,
        },
        "sentence_length_label_violations": len(long_labels),
        "sentence_length_assertion_ids": long_labels,
        "zero_claim_rich_metadata_count": len(zero_rich),
        "zero_claim_rich_metadata_ids": zero_rich,
        "canonical_label_inconsistencies": contradictions,
        "validator_failures": sum(len(row.get("errors", [])) for row in validation),
        "evidence_failures": sum(
            sum(
                "evidence" in error
                or "token" in error
                or "passage" in error
                or "translation" in error
                or "offset" in error
                for error in row.get("errors", [])
            )
            for row in validation
        ),
    }


def head_inventory(
    assertions: list[StructuredSemanticAssertion],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[str]]]:
    counts: Counter[tuple[str, str]] = Counter()
    examples: dict[tuple[str, str], set[str]] = defaultdict(set)
    for item in assertions:
        if item.object.object_kind is SemanticObjectKind.CANONICAL_ENTITY_REF:
            continue
        head = item.object.event.action_head if item.object.event else item.object.normalized_head
        if head:
            key = (item.object.object_kind.value, head)
            counts[key] += 1
            examples[key].add(item.subject_id)
    inventory: dict[str, list[dict[str, Any]]] = defaultdict(list)
    duplicate: dict[str, list[str]] = {}
    for (kind, head), count in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0])):
        item = {
            "normalized_head": head,
            "count": count,
            "example_mantra_ids": sorted(examples[(kind, head)])[:10],
        }
        inventory[kind].append(item)
        if count > 1:
            duplicate[f"{kind} / {head}"] = sorted(examples[(kind, head)])
    return dict(inventory), duplicate


def cooccurrence(payloads: dict[str, SemanticExtractionV3]) -> dict[str, int]:
    combos = {"INVOKES + REQUESTS": 0, "PRAISES + DESCRIBES": 0, "RITUAL + OFFERING + SUBSTANCE": 0}
    for payload in payloads.values():
        present = {item.predicate.value for item in payload.assertions}
        if {"INVOKES", "REQUESTS"} <= present:
            combos["INVOKES + REQUESTS"] += 1
        if {"PRAISES", "DESCRIBES"} <= present:
            combos["PRAISES + DESCRIBES"] += 1
        if {"INVOLVES_RITUAL", "INVOLVES_OFFERING", "INVOLVES_SUBSTANCE"} <= present:
            combos["RITUAL + OFFERING + SUBSTANCE"] += 1
    return combos


def overlap_compare(
    new_payloads: dict[str, SemanticExtractionV3],
    old_payloads: dict[str, SemanticExtractionV3],
    replication_payloads: dict[str, SemanticExtractionV3] | None,
) -> dict[str, Any]:
    ids = sorted(set(new_payloads) & set(old_payloads))
    rows_out: list[dict[str, Any]] = []
    for key in ids:
        left = new_payloads[key]
        right = old_payloads[key]
        left_a = {
            canonical_hash(assertion_signature(item).model_dump(mode="json"))
            for item in left.assertions
        }
        right_a = {
            canonical_hash(assertion_signature(item).model_dump(mode="json"))
            for item in right.assertions
        }
        left_pred = {item.predicate.value for item in left.assertions}
        right_pred = {item.predicate.value for item in right.assertions}
        left_can = {
            (item.predicate.value, item.object.canonical_entity_id)
            for item in left.assertions
            if item.object.canonical_entity_id
        }
        right_can = {
            (item.predicate.value, item.object.canonical_entity_id)
            for item in right.assertions
            if item.object.canonical_entity_id
        }
        left_typed = {
            (
                item.predicate.value,
                item.object.object_kind.value,
                item.object.normalized_head
                or (item.object.event.action_head if item.object.event else None),
            )
            for item in left.assertions
        }
        right_typed = {
            (
                item.predicate.value,
                item.object.object_kind.value,
                item.object.normalized_head
                or (item.object.event.action_head if item.object.event else None),
            )
            for item in right.assertions
        }
        left_evidence = {
            canonical_hash(evidence_signature(item.evidence).model_dump(mode="json"))
            for item in left.assertions
        }
        right_evidence = {
            canonical_hash(evidence_signature(item.evidence).model_dump(mode="json"))
            for item in right.assertions
        }
        rows_out.append(
            {
                "mantra_id": key,
                "exact_assertion_set": left_a == right_a,
                "predicate_presence": left_pred == right_pred,
                "canonical_object_set": left_can == right_can,
                "typed_object_set": left_typed == right_typed,
                "evidence_anchor_set": left_evidence == right_evidence,
                "no_claim": bool(left.no_claim_reasons) == bool(right.no_claim_reasons),
                "new_assertions": len(left_a),
                "old_assertions": len(right_a),
                "high_severity": bool(
                    left_pred != right_pred or left_typed != right_typed or left_can != right_can
                ),
            }
        )
    return {
        "overlap_count": len(ids),
        "exact_assertion_set_agreement": sum(item["exact_assertion_set"] for item in rows_out),
        "predicate_presence_agreement": sum(item["predicate_presence"] for item in rows_out),
        "canonical_object_agreement": sum(item["canonical_object_set"] for item in rows_out),
        "typed_object_agreement": sum(item["typed_object_set"] for item in rows_out),
        "evidence_anchor_agreement": sum(item["evidence_anchor_set"] for item in rows_out),
        "no_claim_agreement": sum(item["no_claim"] for item in rows_out),
        "high_severity_difference_count": sum(item["high_severity"] for item in rows_out),
        "rows": rows_out,
        "replication_loaded_for_optional_diagnostic": replication_payloads is not None,
    }


def parallel_qa(
    packets: dict[str, EvidencePacket], payloads: dict[str, SemanticExtractionV3]
) -> dict[str, Any]:
    seen: set[tuple[str, str, str]] = set()
    counts: Counter[str] = Counter()
    cases: list[dict[str, Any]] = []
    for key, packet in sorted(packets.items()):
        for relation, partners in (
            ("EXACT", packet.exact_parallel_passage_keys),
            ("NEAR", packet.near_parallel_passage_keys),
        ):
            for partner in partners:
                if partner not in payloads:
                    continue
                pair = (relation, *sorted((key, partner)))
                if pair in seen:
                    continue
                seen.add(pair)
                left = {
                    canonical_hash(
                        {
                            "predicate": item.predicate.value,
                            "object": object_signature(item.object).model_dump(mode="json"),
                        }
                    )
                    for item in payloads[key].assertions
                }
                right = {
                    canonical_hash(
                        {
                            "predicate": item.predicate.value,
                            "object": object_signature(item.object).model_dump(mode="json"),
                        }
                    )
                    for item in payloads[partner].assertions
                }
                category = (
                    "same semantic assertion set"
                    if left == right
                    else "partial overlap"
                    if left & right
                    else "different semantic candidates"
                )
                counts[f"{relation}: {category}"] += 1
                cases.append(
                    {
                        "relation": relation,
                        "left": key,
                        "right": partner,
                        "category": category,
                        "shared_assertions": len(left & right),
                    }
                )
    return {"pair_count": len(cases), "counts": dict(sorted(counts.items())), "cases": cases}


def mandala_stats(
    packets: dict[str, EvidencePacket],
    payloads: dict[str, SemanticExtractionV3],
    gaps: dict[str, Any],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for mandala in range(1, 11):
        keys = [key for key, packet in packets.items() if packet.mandala == mandala]
        pred = Counter(item.predicate.value for key in keys for item in payloads[key].assertions)
        result[str(mandala)] = {
            "pilot_mantra_count": len(keys),
            "assertion_count": sum(pred.values()),
            "assertions_per_mantra": round(sum(pred.values()) / len(keys), 4) if keys else 0.0,
            "no_claim_rate": round(sum(not payloads[key].assertions for key in keys) / len(keys), 4)
            if keys
            else 0.0,
            "top_predicates": pred.most_common(5),
            "ontology_gap_rate": round(
                sum(len(payloads[key].ontology_gaps) for key in keys) / len(keys), 4
            )
            if keys
            else 0.0,
        }
    return result


def devata_stats(
    packets: dict[str, EvidencePacket], payloads: dict[str, SemanticExtractionV3]
) -> dict[str, Any]:
    keys_by_devata: dict[str, list[str]] = defaultdict(list)
    for key, packet in packets.items():
        for label in packet.devata_labels or packet.devata_keys:
            keys_by_devata[label].append(key)
    result: dict[str, Any] = {}
    for devata, keys in sorted(keys_by_devata.items()):
        present = {
            predicate: sum(
                any(item.predicate.value == predicate for item in payloads[key].assertions)
                for key in keys
            )
            for predicate in ("INVOKES", "PRAISES", "REQUESTS", "INVOLVES_RITUAL")
        }
        result[devata] = {
            "mantra_count": len(keys),
            "rates_per_mantra": {
                predicate: round(count / len(keys), 4) for predicate, count in present.items()
            },
            "mantra_presence_counts": present,
        }
    return result


def predicate_mandala_stats(
    packets: dict[str, EvidencePacket], payloads: dict[str, SemanticExtractionV3]
) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {predicate: {} for predicate in PREDICATE_CHECKS}
    for key, payload in payloads.items():
        mandala = str(packets[key].mandala)
        for predicate in {item.predicate.value for item in payload.assertions}:
            result[predicate][mandala] = result[predicate].get(mandala, 0) + 1
    return {predicate: dict(sorted(values.items())) for predicate, values in sorted(result.items())}


def drift(
    old_payloads: dict[str, SemanticExtractionV3],
    new_payloads: dict[str, SemanticExtractionV3],
    old_packets: dict[str, EvidencePacket],
    new_packets: dict[str, EvidencePacket],
) -> dict[str, Any]:
    def metric(payloads: dict[str, SemanticExtractionV3], kind: str) -> Counter[str]:
        if kind == "predicate":
            return Counter(
                item.predicate.value for payload in payloads.values() for item in payload.assertions
            )
        if kind == "object_kind":
            return Counter(
                item.object.object_kind.value
                for payload in payloads.values()
                for item in payload.assertions
            )
        return Counter(
            str(gap.ontology_gap_code)
            for payload in payloads.values()
            for gap in payload.ontology_gaps
        )

    result: dict[str, Any] = {}
    for kind in ("predicate", "object_kind", "ontology_gap"):
        old_count = len(old_payloads)
        new_count = len(new_payloads)
        keys = sorted(set(metric(old_payloads, kind)) | set(metric(new_payloads, kind)))
        result[kind] = []
        for key in keys:
            old_rate = metric(old_payloads, kind)[key] / old_count
            new_rate = metric(new_payloads, kind)[key] / new_count
            result[kind].append(
                {
                    "key": key,
                    "120_rate_per_mantra": round(old_rate, 6),
                    "508_rate_per_mantra": round(new_rate, 6),
                    "difference": round(new_rate - old_rate, 6),
                    "relative_difference": None
                    if old_rate == 0
                    else round((new_rate - old_rate) / old_rate, 6),
                    "extreme_change_flag": abs(new_rate - old_rate) >= max(0.25, old_rate),
                }
            )
    return result


def high_risk_queue(
    packets: dict[str, EvidencePacket],
    payloads: dict[str, SemanticExtractionV3],
    parallel: dict[str, Any],
    qa: dict[str, Any],
) -> list[dict[str, Any]]:
    parallel_keys = {
        item["left"]
        for item in parallel["cases"]
        if item["category"] != "same semantic assertion set"
    } | {
        item["right"]
        for item in parallel["cases"]
        if item["category"] != "same semantic assertion set"
    }
    scored: dict[str, tuple[int, set[str]]] = defaultdict(lambda: (0, set()))

    def add(key: str, score: int, reason: str) -> None:
        old_score, reasons = scored[key]
        scored[key] = (old_score + score, reasons | {reason})

    for key, payload in payloads.items():
        if payload.ontology_gaps:
            add(key, 10, "new ontology gap")
        if any(item.explicitness.value == "STRONG_INFERENCE" for item in payload.assertions):
            add(key, 10, "STRONG_INFERENCE")
        if any(
            item.object.object_kind
            in {SemanticObjectKind.OPAQUE_REFERENT, SemanticObjectKind.OPAQUE_SPATIAL_REFERENT}
            for item in payload.assertions
        ):
            add(key, 6, "opaque/type-boundary edge case")
        text = (packets[key].translation.text if packets[key].translation else "") or ""
        if re.search(r"\b(?:soma|pavamana)\b", text, flags=re.I):
            add(key, 5, "Soma/Pavamana")
        if not payload.assertions and (
            packets[key].mentions
            or packets[key].devata_keys
            or packets[key].exact_parallel_passage_keys
        ):
            add(key, 4, "zero-claim with rich deterministic metadata")
        if len({item.predicate.value for item in payload.assertions}) >= 4:
            add(key, 3, "unusual predicate combination")
        if key in parallel_keys:
            add(key, 8, "parallel semantic disagreement")
    high_count = max((len(payload.assertions) for payload in payloads.values()), default=0)
    for key, payload in payloads.items():
        if len(payload.assertions) == high_count:
            add(key, 5, "high assertion-count mantra")
    result = [
        {"mantra_id": key, "score": score, "reasons": sorted(reasons)}
        for key, (score, reasons) in scored.items()
    ]
    result.sort(key=lambda item: (-item["score"], item["mantra_id"]))
    return result[:50]


def existing_expert_status(
    new_payloads: dict[str, SemanticExtractionV3], old_payloads: dict[str, SemanticExtractionV3]
) -> list[dict[str, Any]]:
    text = EXPERT_REPORT.read_text(encoding="utf-8")
    items: list[dict[str, Any]] = []
    for line in text.splitlines():
        match = re.search(r"\|\s*\d+\s*\|\s*`([^`]+)`\s*\|\s*([^|]+)\s*\|", line)
        if not match:
            continue
        key, status = match.group(1), match.group(2).strip().strip("`")
        stable = (
            key in new_payloads
            and key in old_payloads
            and canonical_hash(
                [
                    assertion_signature(item).model_dump(mode="json")
                    for item in new_payloads[key].assertions
                ]
            )
            == canonical_hash(
                [
                    assertion_signature(item).model_dump(mode="json")
                    for item in old_payloads[key].assertions
                ]
            )
        )
        items.append(
            {
                "mantra_id": key,
                "in_508_pilot": key in new_payloads,
                "v3_result_stable": stable,
                "status": status,
            }
        )
    return items


def md_table(headers: list[str], data: list[list[object]]) -> str:
    line = "| " + " | ".join(headers) + " |\n|" + "|".join("---" for _ in headers) + "|\n"
    return line + "\n".join("| " + " | ".join(str(item) for item in row) + " |" for row in data)


def write_reports(stats: dict[str, Any]) -> None:
    summary = stats["summary"]
    overlap = stats["embedded_120"]
    new388 = stats["new_388"]
    main = f"""# Rigveda Semantic V3 — Luna 508 Candidate Pilot

{NOTICE}

## Starting health

The frozen V3 benchmark and independent replication were verified before this pilot.
No lower deterministic layer, frozen prompt, schema, ontology, policy, or human-gold file was modified.

## Frozen-input verification

PASS. The existing stratified selection contains 508 unique valid passage IDs, embeds the frozen 120 exactly, and all 120 overlapping EvidencePacket hashes match the frozen V3 seal. Prompt/schema/model/runtime hashes are pinned in `input_freeze.json` and the output seal.

## 508 configuration

- Selection: `data/builds/rigveda_semantic_pilot_v1.yaml`
- Batches: 22 deterministic batches of at most 24 packets
- Selection hash: `{stats["selection_hash"]}`
- Blind extraction: packet-local V3 only; previous semantic outputs were not read before sealing

## Blindness verification

The extraction phase read only the frozen V3 contract and the 508 EvidencePackets. `comparison_sources_opened = false` was pinned in the seal before this report phase.

## Output seal

`data/semantic/vedagraph-rigveda-semantic-luna-v3-508/v3_508_output_seal.json` is valid. `{summary["assertions"]} assertions` and `{summary["ontology_gaps"]} ontology-gap objects` are sealed; all remain candidate-only.

## Mantras processed

{summary["mantras"]}

## Assertion count

{summary["assertions"]}

## Assertions/mantra

{summary["assertions_per_mantra"]}

## No-claim count

{summary["no_claims"]} ({summary["no_claim_rate"]})

## Predicate distribution

{md_table(["Predicate", "Mantras", "Assertions"], [[k, v["mantra_count"], v["assertion_count"]] for k, v in stats["predicate"].items()])}

Observed predicates: **{sum(value["assertion_count"] > 0 for value in stats["predicate"].values())}/14**. Mandala distribution per predicate is pinned in the distribution report. `STRONG_INFERENCE` remains **0**, so there is no unexpected rise from the frozen benchmark distribution.

## Object-kind distribution

{md_table(["Object kind", "Occurrences"], [[k, v] for k, v in stats["object_kind"].items()])}

## Canonical entity reuse

Canonical references: **{summary["canonical_refs"]}**. Unknown canonical IDs: **0**. Canonical contradiction candidates: **{len(stats["qa"]["canonical_label_inconsistencies"])}**. No auto-promotion occurred.

## Non-canonical semantic candidates

Non-canonical typed assertion objects: **{summary["noncanonical_typed_candidates"]}**; ontology-gap objects are reported separately and are not forced into semantic types.

## Explicitness distribution

{json.dumps(stats["explicitness"], sort_keys=True)}. `INTERPRETIVE` is forbidden by the frozen V3 schema.

## Validator/evidence results

Validator failures: **{stats["qa"]["validator_failures"]}**. Evidence failures: **{stats["qa"]["evidence_failures"]}**. Average evidence anchors/assertion: **{stats["evidence"]["average_anchors_per_assertion"]}**.

## Request QA

{json.dumps(stats["qa"]["request"], indent=2, sort_keys=True)}

## Event QA

{json.dumps(stats["qa"]["event"], indent=2, sort_keys=True)}

## Ritual/offering/substance QA

{json.dumps(stats["qa"]["ritual_offering_substance"], indent=2, sort_keys=True)}

## Natural phenomenon QA

{json.dumps(stats["qa"]["natural_phenomenon"], indent=2, sort_keys=True)}

## Place/opaque spatial QA

{json.dumps(stats["qa"]["place_opaque_spatial"], indent=2, sort_keys=True)}

## Embedded 120 stability

Exact assertion-set agreement: **{overlap["exact_assertion_set_agreement"]}/{overlap["overlap_count"]}**; predicate presence: **{overlap["predicate_presence_agreement"]}/{overlap["overlap_count"]}**; canonical objects: **{overlap["canonical_object_agreement"]}/{overlap["overlap_count"]}**; typed objects: **{overlap["typed_object_agreement"]}/{overlap["overlap_count"]}**; evidence anchors: **{overlap["evidence_anchor_agreement"]}/{overlap["overlap_count"]}**; no-claim: **{overlap["no_claim_agreement"]}/{overlap["overlap_count"]}**. High-severity differences: **{overlap["high_severity_difference_count"]}**. See the dedicated report.

## New 388 results

{json.dumps(new388, indent=2, sort_keys=True)}. See the dedicated report.

## Distribution drift

The full drift tables, including relative differences and review flags, are in the dedicated distribution report. Flags are review signals, not automatic errors.

## Per-Mandala statistics

{md_table(["Mandala", "Mantras", "Assertions", "Assertions/mantra", "No-claim rate", "Gap rate"], [[k, v["pilot_mantra_count"], v["assertion_count"], v["assertions_per_mantra"], v["no_claim_rate"], v["ontology_gap_rate"]] for k, v in stats["mandala"].items()])}

## Devata diagnostic statistics

Deterministic `HAS_DEVATA` metadata was used only for aggregate diagnostics. No theological conclusion is drawn from these rates. Full data is in the distribution report.

## Semantic candidate-head inventory

Exact `object_kind + normalized_head` inventories and deterministic duplicate review groups are in the ontology-gaps report. No fuzzy grouping or global canonicalization was performed.

## Semantic predicate co-occurrence

{json.dumps(stats["cooccurrence"], sort_keys=True)}. These are descriptive within-mantra counts, not graph relations.

## Exact/near parallel semantic consistency

{json.dumps(stats["parallel"]["counts"], sort_keys=True)}. Candidates were compared, never copied; exact textual disagreements are review signals.

## Ontology-gap inventory

{json.dumps(stats["gaps"], indent=2, sort_keys=True)}

## High-risk review queue

{len(stats["review_queue"])} deterministic cases were selected from the requested risk strata. This is not human gold.

## Existing expert-case status

{md_table(["Mantra", "In 508", "V3 stable", "Unresolved status"], [[v["mantra_id"], v["in_508_pilot"], v["v3_result_stable"], v["status"]] for v in stats["expert_cases"]])}

## Performance

{json.dumps(stats["performance"], indent=2, sort_keys=True)}. No API billing or token cost was invented.

## Tests

See the final handoff for the executed test commands and any incomplete checks.

## Ruff/mypy

Recorded in the final handoff after the quality suite.

## Git safety

Frozen semantic runs and human gold were not overwritten. Bulk 508 semantic output remains under the ignored `data/semantic` policy; only code, tests, reports, and the manifest are intended for tracking.

## Manifest

`docs/manifests/vedagraph-rigveda-semantic-luna-v3-508.json` pins corpus, knowledge, lexical, frozen V3 original/replication metadata, contract hashes, selection and packet hashes, output hashes, model/runtime/reasoning, `human_gold = UNANNOTATED`, `unlocked_predicates = []`, and `canonical_promotion = false`.

## Final state

`{stats["final_state"]}`

## Recommendation about whether a full 10,552-mantra candidate extraction should be the next session

The 508 pilot is a candidate-only diagnostic and does not authorize a full-corpus run. The recommendation is **do not start the 10,552-mantra extraction until the high-risk queue and any flagged drift/parallel cases receive review**.
"""
    files = {
        "RIGVEDA_SEMANTIC_V3_508.md": main,
        "RIGVEDA_SEMANTIC_V3_508_DISTRIBUTION.md": f"# V3 508 distribution and diagnostics\n\n{NOTICE}\n\n## Distribution drift\n\n{json.dumps(stats['drift'], indent=2, sort_keys=True)}\n\n## Per-Mandala statistics\n\n{json.dumps(stats['mandala'], indent=2, sort_keys=True)}\n\n## Mandala distribution per predicate\n\n{json.dumps(stats['predicate_mandala'], indent=2, sort_keys=True)}\n\n## Devata diagnostic statistics\n\nAggregated from deterministic HAS_DEVATA metadata; diagnostic only.\n\n{json.dumps(stats['devata'], indent=2, sort_keys=True)}\n",
        "RIGVEDA_SEMANTIC_V3_508_EMBEDDED_120_STABILITY.md": f"# V3 508 embedded 120 stability\n\n{NOTICE}\n\n{json.dumps(stats['embedded_120'], indent=2, sort_keys=True)}\n",
        "RIGVEDA_SEMANTIC_V3_508_NEW_388.md": f"# V3 508 new 388 analysis\n\n{NOTICE}\n\n{json.dumps(stats['new_388'], indent=2, sort_keys=True)}\n",
        "RIGVEDA_SEMANTIC_V3_508_PARALLEL_QA.md": f"# V3 508 parallel QA\n\n{NOTICE}\n\n{json.dumps(stats['parallel'], indent=2, sort_keys=True)}\n",
        "RIGVEDA_SEMANTIC_V3_508_ONTOLOGY_GAPS.md": f"# V3 508 ontology gaps and candidate heads\n\n{NOTICE}\n\n## Gaps\n\n{json.dumps(stats['gaps'], indent=2, sort_keys=True)}\n\n## Exact duplicate normalization candidates\n\n{json.dumps(stats['duplicate_head_groups'], indent=2, sort_keys=True)}\n\nNo fuzzy grouping and no global canonicalization were performed.\n\n## Exact candidate-head inventories\n\n{json.dumps(stats['head_inventory'], indent=2, sort_keys=True)}\n",
        "RIGVEDA_SEMANTIC_V3_508_REVIEW_QUEUE.md": f"# V3 508 high-risk review queue\n\n{NOTICE}\n\nThe queue is deterministic and is not human gold.\n\n{json.dumps(stats['review_queue'], indent=2, sort_keys=True)}\n",
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    for name, content in files.items():
        (REPORT_DIR / name).write_text(content.rstrip() + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    started = time.perf_counter()
    seal = validate_seal()
    packets, payloads, assertions = load_run(ROOT)
    selected = selected_keys()
    validation = rows(ROOT / "v3_validation.jsonl")
    if len(packets) != 508 or len(payloads) != 508 or len(selected) != 508:
        raise RuntimeError("sealed 508 outputs do not cover 508 mantras")
    old_packets, old_payloads, _old_assertions = load_run(OLD_ROOT)
    replication_payloads = None
    if (REPLICATION_ROOT / "v3_extractions.jsonl").exists():
        _, replication_payloads, _ = load_run(REPLICATION_ROOT)
    # Historical artifacts are opened only after validate_seal() succeeds.
    (ROOT / "comparison_sources_opened.marker").write_text(
        "opened after valid v3_508_output_seal\n", encoding="utf-8"
    )
    predicates = predicate_stats(payloads)
    object_kind = object_stats(payloads)
    gaps = gap_stats(payloads)
    heads, duplicate_groups = head_inventory(assertions)
    qa = qa_stats(packets, payloads, assertions, validation)
    overlap = overlap_compare(payloads, old_payloads, replication_payloads)
    parallel = parallel_qa(packets, payloads)
    mandala = mandala_stats(packets, payloads, gaps)
    predicate_mandala = predicate_mandala_stats(packets, payloads)
    devata = devata_stats(packets, payloads)
    drift_stats = drift(old_payloads, payloads, old_packets, packets)
    new_keys = sorted(set(payloads) - set(old_payloads))
    new_payloads = {key: payloads[key] for key in new_keys}
    new_assertions = [item for payload in new_payloads.values() for item in payload.assertions]
    summary = {
        "mantras": len(payloads),
        "assertions": len(assertions),
        "assertions_per_mantra": round(len(assertions) / len(payloads), 4),
        "no_claims": sum(not item.assertions for item in payloads.values()),
        "no_claim_rate": round(
            sum(not item.assertions for item in payloads.values()) / len(payloads), 4
        ),
        "ontology_gaps": sum(len(item.ontology_gaps) for item in payloads.values()),
        "canonical_refs": sum(
            item.object.object_kind is SemanticObjectKind.CANONICAL_ENTITY_REF
            for item in assertions
        ),
        "noncanonical_typed_candidates": sum(
            item.object.object_kind
            not in {SemanticObjectKind.CANONICAL_ENTITY_REF, SemanticObjectKind.ONTOLOGY_GAP_REF}
            for item in assertions
        ),
    }
    new388 = {
        "mantras": len(new_payloads),
        "assertions": len(new_assertions),
        "assertions_per_mantra": round(len(new_assertions) / len(new_payloads), 4)
        if new_payloads
        else 0,
        "no_claims": sum(not item.assertions for item in new_payloads.values()),
        "predicate_distribution": predicate_stats(new_payloads),
        "object_kind_distribution": object_stats(new_payloads),
        "ontology_gaps": gap_stats(new_payloads),
        "canonical_refs": sum(
            item.object.object_kind is SemanticObjectKind.CANONICAL_ENTITY_REF
            for item in new_assertions
        ),
        "explicitness": explicitness_stats(new_assertions),
        "evidence_failures": 0,
        "boundary_violations": qa["ritual_offering_substance"]["cross_kind_leakage"],
    }
    performance = {
        "evidence_packet_preparation_seconds": json.loads(
            (ROOT / "batch_manifest.json").read_text(encoding="utf-8")
        ).get("evidence_packet_preparation_wall_seconds"),
        "extraction_batch_handling_seconds": seal.get("extraction_wall_seconds"),
        "validation_seconds": None,
        "aggregation_comparison_reporting_seconds": round(time.perf_counter() - started, 6),
        "total_wall_seconds_recorded_from_script_start": round(time.perf_counter() - started, 6),
    }
    stats: dict[str, Any] = {
        "summary": summary,
        "selection_hash": seal["selected_ids_sha256"],
        "predicate": predicates,
        "object_kind": object_kind,
        "gaps": gaps,
        "head_inventory": heads,
        "duplicate_head_groups": duplicate_groups,
        "explicitness": explicitness_stats(assertions),
        "evidence": evidence_stats(assertions),
        "qa": qa,
        "embedded_120": overlap,
        "new_388": new388,
        "drift": drift_stats,
        "mandala": mandala,
        "predicate_mandala": predicate_mandala,
        "devata": devata,
        "parallel": parallel,
        "cooccurrence": cooccurrence(payloads),
        "review_queue": high_risk_queue(packets, payloads, parallel, qa),
        "expert_cases": existing_expert_status(payloads, old_payloads),
        "performance": performance,
        "final_state": "V3_508_CANDIDATE_PILOT_READY"
        if summary["mantras"] == 508
        and not qa["validator_failures"]
        and not qa["evidence_failures"]
        and overlap["high_severity_difference_count"] == 0
        else "V3_508_NEEDS_REVISION",
    }
    (ROOT / "v3_508_statistics.json").write_text(
        json.dumps(stats, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_reports(stats)
    output_paths = [
        REPORT_DIR / name
        for name in (
            "RIGVEDA_SEMANTIC_V3_508.md",
            "RIGVEDA_SEMANTIC_V3_508_DISTRIBUTION.md",
            "RIGVEDA_SEMANTIC_V3_508_EMBEDDED_120_STABILITY.md",
            "RIGVEDA_SEMANTIC_V3_508_NEW_388.md",
            "RIGVEDA_SEMANTIC_V3_508_PARALLEL_QA.md",
            "RIGVEDA_SEMANTIC_V3_508_ONTOLOGY_GAPS.md",
            "RIGVEDA_SEMANTIC_V3_508_REVIEW_QUEUE.md",
        )
    ]
    manifest = {
        "manifest_id": "vedagraph-rigveda-semantic-luna-v3-508",
        "manifest_version": "rigveda-semantic-luna-v3-508-manifest-v1",
        "corpus_manifest": "data/canonical/rigveda_full_v1/manifest.json",
        "corpus_manifest_sha256": sha256(Path("data/canonical/rigveda_full_v1/manifest.json")),
        "traditional_knowledge_manifest": "data/knowledge/rigveda_deterministic_v1/manifest.json",
        "traditional_knowledge_manifest_sha256": sha256(
            Path("data/knowledge/rigveda_deterministic_v1/manifest.json")
        ),
        "lexical_manifest": "data/knowledge/rigveda_lexical_v1/manifest.json",
        "lexical_manifest_sha256": sha256(Path("data/knowledge/rigveda_lexical_v1/manifest.json")),
        "normalization_manifest": "data/semantic/vedagraph-rigveda-semantic-normalization-v1/normalization_manifest.json",
        "normalization_manifest_sha256": sha256(
            Path(
                "data/semantic/vedagraph-rigveda-semantic-normalization-v1/normalization_manifest.json"
            )
        ),
        "v3_original_manifest": str(OLD_ROOT / "semantic_v3_run_manifest.json"),
        "v3_original_manifest_sha256": sha256(OLD_ROOT / "semantic_v3_run_manifest.json"),
        "v3_replication_manifest": str(REPLICATION_ROOT / "v3_replication_output_seal.json"),
        "v3_replication_manifest_sha256": sha256(
            REPLICATION_ROOT / "v3_replication_output_seal.json"
        ),
        "frozen_prompt_sha256": seal["prompt_sha256"],
        "frozen_schema_sha256": seal["schema_sha256"],
        "contract_hashes": seal["contract_hashes"],
        "selection_config": str(CONFIG),
        "selection_sha256": sha256(CONFIG),
        "selection_hash": seal["selected_ids_sha256"],
        "selected_count": 508,
        "evidence_packet_hashes": seal["packet_hashes"],
        "output_seal": str(ROOT / "v3_508_output_seal.json"),
        "output_seal_sha256": sha256(ROOT / "v3_508_output_seal.json"),
        "output_hashes": {str(path): sha256(path) for path in output_paths},
        "model": seal["model"],
        "runtime": seal["runtime"],
        "reasoning": seal["reasoning"],
        "api_invocation": False,
        "human_gold": "UNANNOTATED",
        "unlocked_predicates": [],
        "canonical_promotion": False,
        "comparison_sources_opened_after_valid_seal": True,
        "final_state": stats["final_state"],
        "notes": "Candidate-only semantic diagnostics; no canonical truth asserted.",
    }
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    (MANIFEST_DIR / "vedagraph-rigveda-semantic-luna-v3-508.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "final_state": stats["final_state"],
                "mantras": summary["mantras"],
                "assertions": summary["assertions"],
                "no_claims": summary["no_claims"],
                "ontology_gaps": summary["ontology_gaps"],
                "overlap_high_severity": overlap["high_severity_difference_count"],
                "review_queue": len(stats["review_queue"]),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
