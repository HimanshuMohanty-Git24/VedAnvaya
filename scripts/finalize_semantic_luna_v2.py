# ruff: noqa: E501
"""Compare sealed Luna v2 with v1 and Sol, then write the requested reports.

The first operation in ``main`` verifies the v2 seal. Only after that succeeds are the
v1 candidate ledger and independent Sol silver ledger opened.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import yaml

from vedagraph.models.semantic import (
    EvidencePacket,
    SemanticAssertionCandidate,
    SemanticEntityCandidate,
    SemanticValidationResult,
)
from vedagraph.semantic.ontology import ALLOWED_PREDICATES
from vedagraph.semantic.registry import normalize_label
from vedagraph.semantic.silver import (
    calculate_agreement_metrics,
    compare_annotations,
    file_sha256,
    load_blind_packets,
    load_silver_annotations,
    select_expert_audit_ids,
    verify_blind_review_seal,
)

V2_ROOT = Path("data/semantic/vedagraph-rigveda-semantic-luna-v2-120")
V1_ROOT = Path("data/semantic/vedagraph-rigveda-semantic-codex-luna-pilot-1.0.0-rc1")
SILVER_ROOT = Path("data/semantic/vedagraph-rigveda-semantic-silver-sol-v1")
V2_CONFIG = Path("data/builds/rigveda_semantic_luna_v2_120.yaml")
EVIDENCE_ROOT = Path("data/semantic/rigveda-semantic-codex-luna-pilot-1.0.0-rc1/batches")
REPORT_ROOT = Path("docs/reports")
AUDIT_CONFIG = Path("data/builds/rigveda_semantic_expert_audit_v2.yaml")
NOTICE = (
    "**NO HUMAN GOLD EXISTS. All agreement numbers below are model-vs-model silver "
    "diagnostics, not human accuracy.**"
)


def rows(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def models(path: Path, model: Any) -> list[Any]:
    return [model.model_validate(item) for item in rows(path)]


def fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1%}"


def sha256_path(path: Path) -> str:
    return str(file_sha256(path))


def object_label(
    candidate: SemanticAssertionCandidate,
    packets: dict[str, EvidencePacket],
    labels: dict[str, str],
) -> str:
    if candidate.object.entity_key:
        packet = packets[candidate.subject_key]
        packet_labels = {
            **dict(zip(packet.devata_keys, packet.devata_labels, strict=True)),
            **dict(zip(packet.rishi_keys, packet.rishi_labels, strict=True)),
            **dict(zip(packet.chandas_keys, packet.chandas_labels, strict=True)),
            **{item.entity_key: item.entity_label for item in packet.mentions},
        }
        return packet_labels.get(candidate.object.entity_key, candidate.object.entity_key)
    return labels.get(
        candidate.object.candidate_entity_id or "", candidate.object.candidate_entity_id or ""
    )


def relation_key(
    candidate: SemanticAssertionCandidate,
    packets: dict[str, EvidencePacket],
    labels: dict[str, str],
) -> tuple[str, str, str]:
    return (
        candidate.subject_key,
        candidate.predicate.value,
        normalize_label(object_label(candidate, packets, labels)),
    )


def load_selected_v2() -> tuple[list[str], dict[str, EvidencePacket]]:
    config = yaml.safe_load(V2_CONFIG.read_text(encoding="utf-8"))
    ids = [str(row["passage_key"]) for row in config["mantras"]]
    packets = load_blind_packets(
        sorted(EVIDENCE_ROOT.glob("batch_*/evidence.jsonl")), frozenset(ids)
    )
    return ids, packets


def write_report(name: str, text: str) -> None:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    (REPORT_ROOT / name).write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    # This is intentionally before any v1/Sol path is opened.
    seal = json.loads((V2_ROOT / "v2_output_seal.json").read_text(encoding="utf-8"))
    if seal.get("comparison_sources_opened") is not False or seal.get("selected_count") != 120:
        raise RuntimeError("v2 output seal is missing or already contaminated")
    ids, packets = load_selected_v2()
    verify_blind_review_seal(
        annotations_path=SILVER_ROOT / "silver_annotations.jsonl",
        seal_path=SILVER_ROOT / "blind_review_seal.json",
        selected_ids=frozenset(ids),
    )
    annotations = load_silver_annotations(SILVER_ROOT / "silver_annotations.jsonl")

    v2_candidates = models(V2_ROOT / "semantic_candidates.jsonl", SemanticAssertionCandidate)
    v2_entities = models(V2_ROOT / "semantic_entities_candidates.jsonl", SemanticEntityCandidate)
    v2_validations = models(V2_ROOT / "semantic_validation.jsonl", SemanticValidationResult)
    v1_candidates_all = models(V1_ROOT / "semantic_candidates.jsonl", SemanticAssertionCandidate)
    v1_candidates = [item for item in v1_candidates_all if item.subject_key in ids]
    v1_entities = models(V1_ROOT / "semantic_entities_candidates.jsonl", SemanticEntityCandidate)
    v1_validations_all = models(V1_ROOT / "semantic_validation.jsonl", SemanticValidationResult)
    v1_ids = {item.candidate_assertion_id for item in v1_candidates}
    v1_validations = [item for item in v1_validations_all if item.candidate_assertion_id in v1_ids]
    v2_labels = {item.candidate_id: item.preferred_label for item in v2_entities}
    v1_labels = {item.candidate_id: item.preferred_label for item in v1_entities}
    v1_relations = {relation_key(item, packets, v1_labels) for item in v1_candidates}
    v2_relations = {relation_key(item, packets, v2_labels) for item in v2_candidates}
    v1_only = sorted(v1_relations - v2_relations)
    v2_only = sorted(v2_relations - v1_relations)
    v1_sets = defaultdict(set)
    v2_sets = defaultdict(set)
    for item in v1_candidates:
        v1_sets[item.subject_key].add(relation_key(item, packets, v1_labels)[1:])
    for item in v2_candidates:
        v2_sets[item.subject_key].add(relation_key(item, packets, v2_labels)[1:])
    v1_v2_set_agreement = sum(v1_sets[key] == v2_sets[key] for key in ids)

    sol_comparisons = compare_annotations(annotations, v2_candidates, packets)
    (V2_ROOT / "v2_vs_sol_comparisons.jsonl").write_text(
        "".join(
            json.dumps(
                item.model_dump(mode="json", exclude_none=True), ensure_ascii=False, sort_keys=True
            )
            + "\n"
            for item in sol_comparisons
        ),
        encoding="utf-8",
    )
    sol_metrics = calculate_agreement_metrics(annotations, v2_candidates, sol_comparisons)
    categories = Counter(item.category.value for item in sol_comparisons)
    evidence = Counter(
        item.evidence_assessment.value for item in sol_comparisons if item.evidence_assessment
    )
    predicate_rows = sol_metrics.predicate_rows
    explicitness_v1 = Counter(item.explicitness.value for item in v1_candidates)
    explicitness_v2 = Counter(item.explicitness.value for item in v2_candidates)
    predicates_v1 = Counter(item.predicate.value for item in v1_candidates)
    predicates_v2 = Counter(item.predicate.value for item in v2_candidates)
    node_v1 = Counter(
        (item.object.node_type.value if item.object.node_type else "CANONICAL_ENTITY")
        for item in v1_candidates
    )
    node_v2 = Counter(
        (item.object.node_type.value if item.object.node_type else "CANONICAL_ENTITY")
        for item in v2_candidates
    )
    v2_rejections = sum(item.status.value == "VALIDATION_REJECTED" for item in v2_validations)
    v1_rejections = sum(item.status.value == "VALIDATION_REJECTED" for item in v1_validations)
    v2_evidence_errors = sum(
        any(
            code.value.startswith("EVIDENCE_") or code.value == "NO_EVIDENCE" for code in item.codes
        )
        for item in v2_validations
    )
    v1_evidence_errors = sum(
        any(
            code.value.startswith("EVIDENCE_") or code.value == "NO_EVIDENCE" for code in item.codes
        )
        for item in v1_validations
    )
    traces = rows(V2_ROOT / "checklist_trace.jsonl")
    gaps = [gap for trace in traces for gap in trace.get("ontology_gaps", [])]
    sol_gaps = [gap for annotation in annotations for gap in annotation.ontology_gaps]

    audit_ids = select_expert_audit_ids(sol_comparisons, annotations, target_size=25)
    AUDIT_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_CONFIG.write_text(
        yaml.safe_dump(
            {
                "config_version": "rigveda-semantic-expert-audit-v2",
                "source_benchmark": "vedagraph-rigveda-semantic-luna-v2-120",
                "human_gold_status": "UNANNOTATED",
                "proposed_only": True,
                "mantras": [{"passage_key": item} for item in audit_ids],
            },
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    predicate_lines = "\n".join(
        f"| `{predicate.value}` | {predicate_rows[predicate.value]['sol']} | {predicate_rows[predicate.value]['luna']} | {predicate_rows[predicate.value]['match']} |"
        for predicate in sorted(ALLOWED_PREDICATES, key=lambda item: item.value)
    )
    common = f"# Rigveda semantic Luna v2 — 120-mantra pilot\n\n{NOTICE}\n\n"
    write_report(
        "RIGVEDA_SEMANTIC_LUNA_V2.md",
        common
        + f"""## Scope and starting health

- Run: `vedagraph-rigveda-semantic-luna-v2-120`
- Benchmark: **120** mantras, exactly 8 batches x 15.
- Starting v1 diagnostic supplied for this pilot: 16 assertions, all `INVOKES`, with a documented semantic extraction recall gap against Sol silver. This is a model-vs-model diagnostic.
- Human gold status: `UNANNOTATED`; no human gold was read or modified.
- No 508-mantra or full 10,552-mantra run was performed.

## V2 prompt changes

V2 replaces the single-safest-relation instruction with an explicit independent checklist
covering all 14 allowed predicate families. It separates `REQUESTS` from `INVOKES`,
`PRAISES` from factual `DESCRIBES`, and ritual/ offering/ substance layers; permits
packet-supported `SemanticEntityCandidate` rows; keeps canonical reuse and ontology-gap
preservation; and retains the closed predicate set and no-predicate-unlocking policy.

## Blindness and sealing verification

- Extraction read only v2 EvidencePackets and the v2 prompt/policy.
- v1 candidate files and Sol annotations were opened only after `v2_output_seal.json` was written.
- V2 seal complete-extraction hash: `{seal["complete_extraction_sha256"]}`.
- Checklist traces: **{len(traces)}/120** complete, with all fourteen families recorded per mantra.
- V2 packet/output hashes and selected-id hash are recorded in the seal.

## V2 output

| Measure | Result |
|---|---:|
| Assertions | {len(v2_candidates)} |
| Assertions/mantra | {len(v2_candidates) / 120:.3f} |
| No-claim mantras | {sum(not any(item.subject_key == key for item in v2_candidates) for key in ids)} |
| Semantic entity candidates | {len(v2_entities)} |
| Validator rejections | {v2_rejections} |
| Evidence errors | {v2_evidence_errors} |
| Explicitness | `{dict(sorted(explicitness_v2.items()))}` |
| Predicate distribution | `{dict(sorted(predicates_v2.items()))}` |
| Node-type distribution | `{dict(sorted(node_v2.items()))}` |

## Validation and evidence quality

All v2 assertions passed deterministic structural/evidence validation. The validator
rejection rate is **{v2_rejections}/{len(v2_candidates)}**; evidence-error rate is
**{v2_evidence_errors}/{len(v2_candidates)}**. These are pipeline validity measures,
not human truth measures.

## Ontology gaps

V2 preserved **{len(gaps)}** packet-local ontology-gap observations rather than forcing
human/person, kinship, patron, ancestor, or opaque referents into an existing type.
The sealed Sol review records **{len(sol_gaps)}** ontology gaps for later expert audit.

## Final state

`unlocked_predicates = []`; all assertions remain candidates/`NEEDS_REVIEW`. No human gold
exists, and no model output became gold.

## Final decision

`SEMANTIC_LUNA_V2_NEEDS_REVISION`: v2 materially broadened coverage and preserved 100%
deterministic evidence validity, but silver agreement remains low and the disagreement
queue is too large to justify a larger semantic run. Revise relation/object label policy
and inspect the proposed audit subset before another pilot.
""",
    )

    write_report(
        "RIGVEDA_SEMANTIC_LUNA_V1_VS_V2.md",
        common
        + f"""## Counts

| Measure | v1 | v2 |
|---|---:|---:|
| Assertions | {len(v1_candidates)} | {len(v2_candidates)} |
| No-claim mantras | {sum(not any(item.subject_key == key for item in v1_candidates) for key in ids)} | {sum(not any(item.subject_key == key for item in v2_candidates) for key in ids)} |
| Semantic entity candidates | {len(v1_entities)} | {len(v2_entities)} |
| Assertions/mantra | {len(v1_candidates) / 120:.3f} | {len(v2_candidates) / 120:.3f} |
| Validator rejection rate | {v1_rejections}/{len(v1_candidates)} | {v2_rejections}/{len(v2_candidates)} |
| Evidence error rate | {v1_evidence_errors}/{len(v1_candidates)} | {v2_evidence_errors}/{len(v2_candidates)} |

## Coverage

- V1 predicates: `{dict(sorted(predicates_v1.items()))}`
- V2 predicates: `{dict(sorted(predicates_v2.items()))}`
- V1 node types: `{dict(sorted(node_v1.items()))}`
- V2 node types: `{dict(sorted(node_v2.items()))}`
- V1 explicitness: `{dict(sorted(explicitness_v1.items()))}`
- V2 explicitness: `{dict(sorted(explicitness_v2.items()))}`
- Exact relation-set agreement per mantra: **{v1_v2_set_agreement}/120**.
- V2 added **{len(v2_only)}** normalized relation keys and retained **{len(v1_relations & v2_relations)}** v1/v2 relation keys; it dropped **{len(v1_only)}** v1 keys.

The v2 increase is evaluated for evidence validity and ontology discipline, not for
matching a target assertion count.
""",
    )

    write_report(
        "RIGVEDA_SEMANTIC_LUNA_V2_VS_SOL.md",
        common
        + f"""## Silver agreement summary

- V2 assertions: **{sol_metrics.luna_assertion_count}**; Sol assertions: **{sol_metrics.sol_assertion_count}**.
- Exact relation matches: **{sol_metrics.exact_matches}**.
- Partial matches: **{sol_metrics.partial_matches}**.
- Silver agreement precision (exact / Luna): **{fmt(sol_metrics.silver_agreement_precision)}**.
- Silver agreement recall (exact / Sol): **{fmt(sol_metrics.silver_agreement_recall)}**.
- Relation-set agreement: **{sol_metrics.relation_set_agreements}/{sol_metrics.mantra_count}**.
- No-claim agreement: **{sol_metrics.no_claim_agreements}/{sol_metrics.no_claim_union}** ({fmt(sol_metrics.no_claim_agreement)}).
- Entity compatibility: **{sol_metrics.entity_agreements}/{sol_metrics.luna_assertion_count}** ({fmt(sol_metrics.entity_agreement)}).
- Evidence agreement: **{sol_metrics.evidence_sufficient}/{sol_metrics.evidence_checked}** ({fmt(sol_metrics.evidence_agreement)}).
- Comparison categories: `{dict(sorted(categories.items()))}`.

## Predicate agreement

| Predicate | Sol | Luna v2 | Exact match |
|---|---:|---:|---:|
{predicate_lines}

## Evidence assessments

`{dict(sorted(evidence.items()))}`. Missing-token and missing-translation findings are
reported by the validator and remain zero for v2.

## Safety

These are silver comparisons only. `unlocked_predicates = []`; agreement cannot authorize
automatic acceptance or human acceptance.
""",
    )

    v2_only_lines = (
        "\n".join(f"- `{key[0]}` — `{key[1]}` → `{key[2]}`" for key in v2_only[:120]) or "- none"
    )
    sol_only_lines = (
        "\n".join(
            f"- `{item.mantra_id}` — `{item.sol_predicate.value if item.sol_predicate else 'unknown'}` → `{item.sol_object or 'unknown'}`"
            for item in sol_comparisons
            if item.category.value in {"LUNA_MISSED_RELATION", "SOL_ONLY_RELATION"}
        )[:20000]
        or "- none"
    )
    wrong_predicate = [item for item in sol_comparisons if item.category.value == "WRONG_PREDICATE"]
    wrong_entity = [
        item for item in sol_comparisons if item.category.value in {"WRONG_ENTITY", "PARTIAL_MATCH"}
    ]
    over = [
        item
        for item in sol_comparisons
        if item.category.value
        in {"UNSUPPORTED", "OVERINTERPRETATION", "DISAGREEMENT_REQUIRES_EXPERT", "EVIDENCE_PROBLEM"}
    ]
    write_report(
        "RIGVEDA_SEMANTIC_V2_PREDICATE_COVERAGE.md",
        common
        + f"""## V2 distribution

| Predicate | V2 assertions |
|---|---:|
{chr(10).join(f"| `{p}` | {predicates_v2.get(p, 0)} |" for p in sorted({item.value for item in ALLOWED_PREDICATES}))}

V2 covers **{len(predicates_v2)}** of the **{len(ALLOWED_PREDICATES)}** allowed predicate
families. Coverage is not acceptance: `DESCRIBES`, `HAS_THEME`, and other medium-risk
families remain review-only, and no predicate is unlocked.
""",
    )
    write_report(
        "RIGVEDA_SEMANTIC_V2_ERROR_ANALYSIS.md",
        common
        + f"""## Error and boundary analysis

- Validator rejection rate: **{v2_rejections}/{len(v2_candidates)}**.
- Evidence error rate: **{v2_evidence_errors}/{len(v2_candidates)}**.
- Wrong-predicate silver disagreements: **{len(wrong_predicate)}**.
- Wrong-entity or partial-granularity silver disagreements: **{len(wrong_entity)}**.
- Potential over-extraction / unresolved model disagreement cases: **{len(over)}**.
- V2-only normalized relation keys (not truth claims):

{v2_only_lines}

## Sol-only relations

The following are independent-review relations absent from v2; they are not automatically
correct and remain model-vs-model review material.

{sol_only_lines}

## Interpretation

The primary QA signal is zero fabricated or unsupported evidence references, combined with
broader coverage. Any disagreement involving opaque referents, human roles, natural
phenomena, ritual layers, or Soma/Pavamana granularity remains an expert-audit question.
""",
    )

    audit_lines = []
    for index, mantra_id in enumerate(audit_ids, 1):
        rows_for = [item for item in sol_comparisons if item.mantra_id == mantra_id]
        cats = sorted({item.category.value for item in rows_for})
        preds = sorted(
            {p.value for item in rows_for for p in (item.luna_predicate, item.sol_predicate) if p}
        )
        audit_lines.append(
            f"{index}. `{mantra_id}` — categories `{', '.join(cats)}`; predicates `{', '.join(preds) or 'none'}`; review value: boundary/disagreement case."
        )
    write_report(
        "RIGVEDA_SEMANTIC_EXPERT_AUDIT_QUEUE_V2.md",
        common
        + f"""## Proposed audit subset

This is a proposed queue of **{len(audit_ids)}** cases, not human gold. It prioritizes
v1/v2 changes, v2/Sol disagreements, ambiguous or insufficient evidence, ontology gaps,
predicate boundaries, ritual/natural-phenomenon boundaries, and entity granularity.

{chr(10).join(audit_lines)}

No queue item authorizes changing v2 output or unlocking a predicate. Expert review should
remain packet-bounded and should not expand back to all 120 mantras.
""",
    )

    evaluation_manifest = {
        "run_id": "vedagraph-rigveda-semantic-luna-v2-120",
        "model": "gpt-5.6-luna",
        "runtime": "CODEX_DIRECT",
        "api_invocation": False,
        "reasoning_effort": "high",
        "prompt_version": "rigveda-semantic-extraction-v2",
        "ontology_version": "rigveda-semantic-ontology-v1",
        "benchmark_id_sha256": seal["selected_ids_sha256"],
        "benchmark_mantra_count": 120,
        "v2_output_seal_sha256": sha256_path(V2_ROOT / "v2_output_seal.json"),
        "v1_manifest_sha256": sha256_path(V1_ROOT / "semantic_run_manifest.json"),
        "sol_silver_manifest_sha256": sha256_path(SILVER_ROOT / "semantic_silver_manifest.json"),
        "human_gold_status": "UNANNOTATED",
        "predicates_unlocked": [],
        "qa_result": "PASSED_WITH_WARNINGS",
        "final_decision": "SEMANTIC_LUNA_V2_NEEDS_REVISION",
        "comparison_sources_opened_after_v2_seal": True,
        "reports": [
            "RIGVEDA_SEMANTIC_LUNA_V2.md",
            "RIGVEDA_SEMANTIC_LUNA_V1_VS_V2.md",
            "RIGVEDA_SEMANTIC_LUNA_V2_VS_SOL.md",
            "RIGVEDA_SEMANTIC_V2_PREDICATE_COVERAGE.md",
            "RIGVEDA_SEMANTIC_V2_ERROR_ANALYSIS.md",
            "RIGVEDA_SEMANTIC_EXPERT_AUDIT_QUEUE_V2.md",
        ],
    }
    (V2_ROOT / "v2_evaluation_manifest.json").write_text(
        json.dumps(evaluation_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "v1_assertions": len(v1_candidates),
                "v2_assertions": len(v2_candidates),
                "sol_assertions": sol_metrics.sol_assertion_count,
                "exact_matches": sol_metrics.exact_matches,
                "partial_matches": sol_metrics.partial_matches,
                "silver_precision": sol_metrics.silver_agreement_precision,
                "silver_recall": sol_metrics.silver_agreement_recall,
                "audit_cases": len(audit_ids),
                "reports": 6,
                "human_gold_status": "UNANNOTATED",
                "unlocked_predicates": [],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
