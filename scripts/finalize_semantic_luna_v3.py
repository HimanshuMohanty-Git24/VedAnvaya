"""Compare sealed v3 with v2 and Sol only after the v3 output seal verifies."""

# Markdown report templates intentionally preserve readable rendered lines.
# ruff: noqa: E501

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml

from vedagraph.models.normalization import StructuredSemanticAssertion, StructuredSemanticComparison
from vedagraph.models.semantic import EvidencePacket, SemanticAssertionCandidate
from vedagraph.models.silver import SilverSemanticAnnotation
from vedagraph.semantic.normalization import (
    LegacyEntityLabel,
    compare_assertion_sets,
    migrate_luna_assertion,
    migrate_sol_assertion,
    object_signature,
)
from vedagraph.semantic.object_ontology import StructuredComparisonCategory
from vedagraph.semantic.ontology import SemanticNodeType
from vedagraph.semantic.silver import (
    compare_annotations,
    load_silver_annotations,
)

ROOT = Path("data/semantic/vedagraph-rigveda-semantic-luna-v3-120")
V2_ROOT = Path("data/semantic/vedagraph-rigveda-semantic-luna-v2-120")
SILVER_ROOT = Path("data/semantic/vedagraph-rigveda-semantic-silver-sol-v1")
CONFIG = Path("data/builds/rigveda_semantic_luna_v2_120.yaml")
REPORTS = Path("docs/reports")
NOTICE = "**NO HUMAN GOLD EXISTS. All comparison values are model-vs-model silver diagnostics, not precision, recall, accuracy, or F1.**"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def rows(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def write(name: str, text: str) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / name).write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def verify_seal() -> tuple[dict[str, Any], list[str]]:
    seal_path = ROOT / "v3_output_seal.json"
    if not seal_path.exists():
        raise RuntimeError("comparison requires v3_output_seal.json")
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    if seal.get("comparison_sources_opened") is not False or seal.get("selected_count") != 120:
        raise RuntimeError("v3 seal is absent, contaminated, or not for 120 mantras")
    if seal.get("human_gold_status") != "UNANNOTATED" or seal.get("unlocked_predicates") != []:
        raise RuntimeError("v3 seal has unsafe gold or predicate state")
    for name, expected in seal["output_hashes"].items():
        if sha256(ROOT / name) != expected:
            raise RuntimeError(f"v3 output changed after sealing: {name}")
    config: dict[str, Any] = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    ids = [str(row["passage_key"]) for row in config["mantras"]]
    if seal["selected_ids_sha256"] != canonical_hash(sorted(ids)):
        raise RuntimeError("v3 selected-id hash does not match the sealed benchmark config")
    return seal, ids


def load_v3() -> list[StructuredSemanticAssertion]:
    result: list[StructuredSemanticAssertion] = []
    for row in rows(ROOT / "semantic_v3_assertions.jsonl"):
        result.append(StructuredSemanticAssertion.model_validate(row))
    return result


def load_v3_packets() -> dict[str, EvidencePacket]:
    packets: dict[str, EvidencePacket] = {}
    for path in sorted((ROOT / "batches").glob("batch_*/evidence.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                packet = EvidencePacket.model_validate(json.loads(line))
                packets[packet.passage_key] = packet
    return packets


def load_v2_structured(
    ids: set[str],
) -> tuple[
    list[StructuredSemanticAssertion],
    dict[str, LegacyEntityLabel],
    list[SemanticAssertionCandidate],
]:
    candidates = [
        SemanticAssertionCandidate.model_validate(row)
        for row in rows(V2_ROOT / "semantic_candidates.jsonl")
        if str(row["subject_key"]) in ids
    ]
    entities: dict[str, LegacyEntityLabel] = {}
    for row in rows(V2_ROOT / "semantic_entities_candidates.jsonl"):
        entities[str(row["candidate_id"])] = LegacyEntityLabel(
            label=str(row["preferred_label"]),
            node_type=SemanticNodeType(str(row["entity_type"])),
        )
    structured = [
        migrate_luna_assertion(
            item,
            run_id="vedagraph-rigveda-semantic-luna-v2-120",
            local_entities=entities,
            ordinal=index,
        )
        for index, item in enumerate(candidates)
    ]
    return structured, entities, candidates


def load_sol_structured(
    annotations: list[SilverSemanticAnnotation],
) -> list[StructuredSemanticAssertion]:
    return [
        migrate_sol_assertion(
            assertion, run_id="vedagraph-rigveda-semantic-silver-sol-v1", ordinal=index
        )
        for index, annotation in enumerate(annotations)
        for assertion in annotation.semantic_assertions
    ]


def comparison_rows(path: Path, items: list[StructuredSemanticComparison]) -> None:
    path.write_text(
        "".join(
            json.dumps(
                item.model_dump(mode="json", exclude_none=True), ensure_ascii=False, sort_keys=True
            )
            + "\n"
            for item in items
        ),
        encoding="utf-8",
        newline="\n",
    )


def report_metrics(items: list[StructuredSemanticComparison]) -> Counter[str]:
    return Counter(item.category.value for item in items)


def add_no_claim_rows(
    comparisons: list[StructuredSemanticComparison],
    ids: list[str],
    left: list[StructuredSemanticAssertion],
    right: list[StructuredSemanticAssertion],
) -> list[StructuredSemanticComparison]:
    left_ids = {item.subject_id for item in left}
    right_ids = {item.subject_id for item in right}
    rows_for = list(comparisons)
    for mantra_id in sorted(set(ids) - left_ids - right_ids):
        rows_for.append(
            StructuredSemanticComparison(
                mantra_id=mantra_id,
                category=StructuredComparisonCategory.NO_CLAIM_AGREEMENT,
                reasoning="Neither model emitted an assertion for this selected packet.",
            )
        )
    return rows_for


def select_queue(ids: list[str], comparisons: list[StructuredSemanticComparison]) -> list[str]:
    by_id: dict[str, list[StructuredSemanticComparison]] = defaultdict(list)
    for item in comparisons:
        by_id[item.mantra_id].append(item)
    priority = {
        StructuredComparisonCategory.PREDICATE_DIFFERENCE.value: 100,
        StructuredComparisonCategory.OBJECT_TYPE_DIFFERENCE.value: 95,
        StructuredComparisonCategory.CONFLICTING_OBJECT.value: 90,
        StructuredComparisonCategory.EXPERT_REQUIRED.value: 85,
        StructuredComparisonCategory.UNRESOLVED.value: 80,
        StructuredComparisonCategory.LEFT_ONLY.value: 75,
        StructuredComparisonCategory.RIGHT_ONLY.value: 75,
        StructuredComparisonCategory.GRANULARITY_DIFFERENCE.value: 45,
        StructuredComparisonCategory.PARTIAL_OBJECT_OVERLAP.value: 40,
        StructuredComparisonCategory.COMPATIBLE_OBJECT.value: 20,
        StructuredComparisonCategory.EXACT_NORMALIZED_OBJECT.value: 5,
        StructuredComparisonCategory.EXACT_CANONICAL_ENTITY.value: 1,
    }
    ranked = sorted(
        ids,
        key=lambda key: (-sum(priority.get(item.category.value, 0) for item in by_id[key]), key),
    )
    selected: list[str] = []
    seen_category: set[str] = set()
    seen_predicate: set[str] = set()
    while len(selected) < min(20, len(ranked)):
        choices = [key for key in ranked if key not in selected]
        best = max(
            choices,
            key=lambda key: (
                len({item.category.value for item in by_id[key]} - seen_category),
                len(
                    {
                        p
                        for item in by_id[key]
                        for p in (item.luna_predicate, item.sol_predicate)
                        if p
                    }
                    - seen_predicate
                ),
                sum(priority.get(item.category.value, 0) for item in by_id[key]),
                key,
            ),
        )
        selected.append(best)
        seen_category.update(item.category.value for item in by_id[best])
        seen_predicate.update(
            p.value for item in by_id[best] for p in (item.luna_predicate, item.sol_predicate) if p
        )
    return selected


def main() -> None:
    seal, ids = verify_seal()
    # This marker is the auditable boundary: all reads below it are post-seal only.
    marker = ROOT / "comparison_sources_opened.marker"
    if not marker.exists():
        marker.write_text("opened after valid v3 seal\n", encoding="utf-8")

    v3 = load_v3()
    packets = load_v3_packets()
    v2, _, v2_candidates = load_v2_structured(set(ids))
    annotations = load_silver_annotations(SILVER_ROOT / "silver_annotations.jsonl")
    sol = load_sol_structured(annotations)
    v2_vs_v3 = add_no_claim_rows(compare_assertion_sets(v3, v2), ids, v3, v2)
    v3_vs_sol = add_no_claim_rows(compare_assertion_sets(v3, sol), ids, v3, sol)
    comparison_rows(ROOT / "v3_vs_v2_structured_comparisons.jsonl", v2_vs_v3)
    comparison_rows(ROOT / "v3_vs_sol_structured_comparisons.jsonl", v3_vs_sol)

    v3_metrics = report_metrics(v3_vs_sol)
    v2_metrics = report_metrics(v2_vs_v3)
    relation_v3 = {
        (
            item.subject_id,
            item.predicate.value,
            canonical_hash(object_signature(item.object).model_dump(mode="json")),
        )
        for item in v3
    }
    relation_v2 = {
        (
            item.subject_id,
            item.predicate.value,
            canonical_hash(object_signature(item.object).model_dump(mode="json")),
        )
        for item in v2
    }
    v3_only = relation_v3 - relation_v2
    v2_only = relation_v2 - relation_v3
    legacy_sol = compare_annotations(annotations, v2_candidates, packets)
    legacy_categories = Counter(item.category.value for item in legacy_sol)

    write(
        "RIGVEDA_SEMANTIC_LUNA_V2_VS_V3.md",
        f"""# RIGVEDA semantic Luna v2 vs v3

{NOTICE}

The v3 seal was verified before v2 or Sol data was opened. Both runs use the same 120
selected ids. v3 uses native typed occurrence objects; v2 is migrated offline solely for
diagnostic comparison.

| Measure | V2 | V3 |
|---|---:|---:|
| Assertions | {len(v2)} | {len(v3)} |
| No-claim mantras | {len(ids) - len({item.subject_id for item in v2})} | {len(ids) - len({item.subject_id for item in v3})} |
| Canonical entity objects | {sum(item.object.object_kind.value == "CANONICAL_ENTITY_REF" for item in v2)} | {sum(item.object.object_kind.value == "CANONICAL_ENTITY_REF" for item in v3)} |
| Typed event objects | {sum(item.object.object_kind.value == "EVENT" for item in v2)} | {sum(item.object.object_kind.value == "EVENT" for item in v3)} |
| EXPLICIT | {sum(item.explicitness.value == "EXPLICIT" for item in v2)} | {sum(item.explicitness.value == "EXPLICIT" for item in v3)} |
| STRONG_INFERENCE | {sum(item.explicitness.value == "STRONG_INFERENCE" for item in v2)} | {sum(item.explicitness.value == "STRONG_INFERENCE" for item in v3)} |

V2→V3 structured comparison categories: `{dict(sorted(v2_metrics.items()))}`.

Relation-set differences using typed signatures (not labels): **V2-only {len(v2_only)}**, **V3-only {len(v3_only)}**. These are diagnostic differences, not truth judgements.

The v3 run keeps `unlocked_predicates = []`.
""",
    )

    write(
        "RIGVEDA_SEMANTIC_LUNA_V3_VS_SOL.md",
        f"""# RIGVEDA semantic Luna v3 vs Sol silver

{NOTICE}

The sealed structured comparator aligns predicates and typed object fields. It does not
require display-label equality and uses no fuzzy similarity.

- V3 assertions: **{len(v3)}**; Sol assertions: **{len(sol)}**.
- Structured comparison categories: `{dict(sorted(v3_metrics.items()))}`.
- EXACT_CANONICAL_ENTITY: **{v3_metrics.get("EXACT_CANONICAL_ENTITY", 0)}**.
- EXACT_NORMALIZED_OBJECT: **{v3_metrics.get("EXACT_NORMALIZED_OBJECT", 0)}**.
- COMPATIBLE_OBJECT: **{v3_metrics.get("COMPATIBLE_OBJECT", 0)}**.
- PARTIAL_OBJECT_OVERLAP: **{v3_metrics.get("PARTIAL_OBJECT_OVERLAP", 0)}**.
- GRANULARITY_DIFFERENCE: **{v3_metrics.get("GRANULARITY_DIFFERENCE", 0)}**.
- PREDICATE_DIFFERENCE: **{v3_metrics.get("PREDICATE_DIFFERENCE", 0)}**.
- OBJECT_TYPE_DIFFERENCE: **{v3_metrics.get("OBJECT_TYPE_DIFFERENCE", 0)}**.
- CONFLICTING_OBJECT: **{v3_metrics.get("CONFLICTING_OBJECT", 0)}**.
- UNRESOLVED: **{v3_metrics.get("UNRESOLVED", 0)}**.
- LEFT_ONLY: **{v3_metrics.get("LEFT_ONLY", 0)}**; RIGHT_ONLY: **{v3_metrics.get("RIGHT_ONLY", 0)}**.
- NO_CLAIM_AGREEMENT: **{v3_metrics.get("NO_CLAIM_AGREEMENT", 0)}**.

Legacy string-comparator categories are preserved for historical reference only: `{dict(sorted(legacy_categories.items()))}`.

These values are model-vs-model silver diagnostics. They do not establish correctness,
human precision/recall, or predicate acceptance. `unlocked_predicates = []`.
""",
    )

    diagnoses: list[dict[str, Any]] = []
    for mantra_id in ids:
        rows_for = [item for item in v3_vs_sol if item.mantra_id == mantra_id]
        cats = {item.category.value for item in rows_for}
        if not rows_for or all(item.category.value == "NO_CLAIM_AGREEMENT" for item in rows_for):
            primary = "NO_CLAIM_AGREEMENT"
        elif any(
            item in cats
            for item in {"OBJECT_TYPE_DIFFERENCE", "PREDICATE_DIFFERENCE", "CONFLICTING_OBJECT"}
        ):
            primary = "ACTUAL_SEMANTIC_CONFLICT_CANDIDATE"
        elif any(item in cats for item in {"EXPERT_REQUIRED", "UNRESOLVED"}):
            primary = "ONTOLOGY_GAP" if "EXPERT_REQUIRED" in cats else "UNRESOLVED_OBJECT"
        elif "LEFT_ONLY" in cats or "RIGHT_ONLY" in cats:
            primary = "ONE_SIDED_EXTRACTION"
        elif any(item in cats for item in {"GRANULARITY_DIFFERENCE", "PARTIAL_OBJECT_OVERLAP"}):
            primary = "OBJECT_GRANULARITY_MISMATCH"
        else:
            primary = "REPRESENTATION_MISMATCH"
        diagnoses.append(
            {
                "mantra_id": mantra_id,
                "primary_category": primary,
                "comparison_categories": sorted(cats),
            }
        )
    diag_counts = Counter(item["primary_category"] for item in diagnoses)
    write(
        "RIGVEDA_SEMANTIC_V3_DISAGREEMENT_DECOMPOSITION.md",
        f"""# RIGVEDA semantic v3 disagreement decomposition

{NOTICE}

One primary diagnostic category is assigned per benchmark mantra. Categories describe
why two model outputs differ; they do not label either model as correct.

Distribution: `{dict(sorted(diag_counts.items()))}`.

| Category | Meaning |
|---|---|
| REPRESENTATION_MISMATCH | Same evidence-level relation is represented differently. |
| OBJECT_GRANULARITY_MISMATCH | Typed structures differ by detail or outcome granularity. |
| PREDICATE_MISMATCH | Relation family differs. |
| ACTUAL_SEMANTIC_CONFLICT_CANDIDATE | Candidate object/predicate fields conflict; expert review required. |
| ONTOLOGY_GAP | A typed referent cannot be safely modeled. |
| ONE_SIDED_EXTRACTION | Only one model emitted a relation. |
| INSUFFICIENT_EVIDENCE | Packet evidence is not sufficient to resolve the disagreement. |
| UNRESOLVED_OBJECT | An occurrence remains unresolved by deterministic structure. |

Detailed rows are stored in `v3_vs_sol_structured_comparisons.jsonl`.
""",
    )

    queue = select_queue(ids, v3_vs_sol)
    queue_lines = []
    for index, mantra_id in enumerate(queue, 1):
        item_rows = [item for item in v3_vs_sol if item.mantra_id == mantra_id]
        cats = sorted({item.category.value for item in item_rows})
        preds = sorted(
            {p.value for item in item_rows for p in (item.luna_predicate, item.sol_predicate) if p}
        )
        queue_lines.append(
            f"{index}. `{mantra_id}` — categories `{', '.join(cats)}`; predicates `{', '.join(preds) or 'none'}`; packet-bounded expert question."
        )
    write(
        "RIGVEDA_SEMANTIC_EXPERT_AUDIT_QUEUE_V3.md",
        f"""# RIGVEDA semantic v3 expert audit queue

{NOTICE}

The queue contains **{len(queue)}** cases and was rebuilt after typed comparison. Pure
label/format disagreements are excluded where the structured comparator resolves them.
The remaining cases prioritize predicate boundaries, typed object conflicts, one-sided
extraction, ontology gaps, ritual/offering/substance distinctions, Soma granularity,
natural phenomenon versus deity, spatial ambiguity, and translation ambiguity.

{chr(10).join(queue_lines) or "- none"}

No expert answers were obtained. No queue item changes output or unlocks a predicate.
""",
    )

    evaluation_manifest = {
        "run_id": ROOT.name,
        "model": "gpt-5.6-luna",
        "runtime": "CODEX_DIRECT",
        "reasoning": "high",
        "api_invocation": False,
        "benchmark_mantra_count": 120,
        "selected_id_sha256": seal["selected_ids_sha256"],
        "v3_output_seal_sha256": sha256(ROOT / "v3_output_seal.json"),
        "v3_prompt_sha256": seal["prompt_sha256"],
        "v3_schema_sha256": seal["schema_sha256"],
        "structured_comparison_policy": "rigveda-semantic-object-comparison-v1",
        "human_gold_status": "UNANNOTATED",
        "unlocked_predicates": [],
        "comparison_sources_opened_after_seal": True,
        "expert_audit_queue_count": len(queue),
        "reports": [
            "RIGVEDA_SEMANTIC_LUNA_V3.md",
            "RIGVEDA_SEMANTIC_LUNA_V2_VS_V3.md",
            "RIGVEDA_SEMANTIC_LUNA_V3_VS_SOL.md",
            "RIGVEDA_SEMANTIC_V3_DISAGREEMENT_DECOMPOSITION.md",
            "RIGVEDA_SEMANTIC_V3_REQUEST_QA.md",
            "RIGVEDA_SEMANTIC_V3_EVENT_QA.md",
            "RIGVEDA_SEMANTIC_V3_TYPE_BOUNDARY_QA.md",
            "RIGVEDA_SEMANTIC_EXPERT_AUDIT_QUEUE_V3.md",
        ],
    }
    (ROOT / "v3_evaluation_manifest.json").write_text(
        json.dumps(evaluation_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "v3_assertions": len(v3),
                "v2_assertions": len(v2),
                "sol_assertions": len(sol),
                "structured_categories": dict(sorted(v3_metrics.items())),
                "audit_queue": len(queue),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
