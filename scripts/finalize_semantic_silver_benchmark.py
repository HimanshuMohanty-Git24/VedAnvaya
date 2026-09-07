"""Seal, compare, report, and manifest the 120-mantra independent silver benchmark."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from vedagraph.models.semantic import SemanticAssertionCandidate
from vedagraph.models.silver import SilverBenchmarkManifest
from vedagraph.semantic.gold import expected_gold_ids
from vedagraph.semantic.ontology import ALLOWED_PREDICATES, ONTOLOGY_VERSION
from vedagraph.semantic.silver import (
    SILVER_REVIEWER_MODEL,
    SILVER_RUN_ID,
    calculate_agreement_metrics,
    compare_after_blind_seal,
    file_sha256,
    load_blind_packets,
    load_silver_annotations,
    select_expert_audit_ids,
    verify_blind_review_seal,
)

LUNA_ROOT = Path("data/semantic/vedagraph-rigveda-semantic-codex-luna-pilot-1.0.0-rc1")
EVIDENCE_ROOT = Path("data/semantic/rigveda-semantic-codex-luna-pilot-1.0.0-rc1/batches")
SILVER_ROOT = Path("data/semantic/vedagraph-rigveda-semantic-silver-sol-v1")
REPORT_ROOT = Path("docs/reports")
AUDIT_CONFIG = Path("data/builds/rigveda_semantic_expert_audit_v1.yaml")
NOTICE = (
    "**NO HUMAN GOLD EXISTS YET. These are model-vs-model silver metrics, "
    "not human-gold accuracy.**"
)


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3%}"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def _load_jsonl(path: Path, model: Any) -> list[Any]:
    return [
        model.model_validate(json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> None:
    selected = expected_gold_ids()
    selected_ids = frozenset(selected)
    packets = load_blind_packets(sorted(EVIDENCE_ROOT.glob("batch_*/evidence.jsonl")), selected_ids)
    annotations_path = SILVER_ROOT / "silver_annotations.jsonl"
    seal_path = SILVER_ROOT / "blind_review_seal.json"
    comparisons_path = SILVER_ROOT / "luna_vs_sol_comparisons.jsonl"
    verify_blind_review_seal(
        annotations_path=annotations_path, seal_path=seal_path, selected_ids=selected_ids
    )
    comparisons = compare_after_blind_seal(
        annotations_path=annotations_path,
        seal_path=seal_path,
        luna_candidates_path=LUNA_ROOT / "semantic_candidates.jsonl",
        comparison_path=comparisons_path,
        packets=packets,
        selected_ids=selected_ids,
    )
    annotations = load_silver_annotations(annotations_path)
    all_luna = _load_jsonl(LUNA_ROOT / "semantic_candidates.jsonl", SemanticAssertionCandidate)
    luna = [item for item in all_luna if item.subject_key in selected_ids]
    metrics = calculate_agreement_metrics(annotations, luna, comparisons)
    sol_predicates = Counter(
        assertion.predicate.value
        for annotation in annotations
        for assertion in annotation.semantic_assertions
    )
    luna_predicates = Counter(item.predicate.value for item in luna)
    no_claim_count = sum(item.no_claim for item in annotations)
    ontology_gap_count = sum(len(item.ontology_gaps) for item in annotations)
    category_counts = Counter(item.category.value for item in comparisons)
    evidence_counts = Counter(
        item.evidence_assessment.value
        for item in comparisons
        if item.evidence_assessment is not None
    )
    audit_ids = select_expert_audit_ids(comparisons, annotations, target_size=25)
    _write(
        AUDIT_CONFIG,
        yaml.safe_dump(
            {
                "config_version": "rigveda-semantic-expert-audit-v1",
                "source_benchmark": SILVER_RUN_ID,
                "human_gold_status": "UNANNOTATED",
                "proposed_only": True,
                "mantras": [{"passage_key": item} for item in audit_ids],
            },
            sort_keys=False,
            allow_unicode=True,
        ),
    )

    predicate_lines = [
        f"| `{predicate.value}` | {metrics.predicate_rows[predicate.value]['sol']} | "
        f"{metrics.predicate_rows[predicate.value]['luna']} | "
        f"{metrics.predicate_rows[predicate.value]['match']} |"
        for predicate in sorted(ALLOWED_PREDICATES, key=lambda item: item.value)
    ]
    no_claim_line = (
        f"**{metrics.no_claim_agreements}/{metrics.no_claim_union}** union cases "
        f"({_fmt(metrics.no_claim_agreement)})"
    )
    entity_line = (
        f"**{metrics.entity_agreements}/{metrics.luna_assertion_count}** "
        f"({_fmt(metrics.entity_agreement)})"
    )
    evidence_line = (
        f"**{metrics.evidence_sufficient}/{metrics.evidence_checked}** "
        f"({_fmt(metrics.evidence_agreement)})"
    )
    benchmark = f"""# Rigveda semantic silver benchmark

{NOTICE}

## Design and scope

- Run: `{SILVER_RUN_ID}`
- Provenance: `MODEL_REVIEWED_SILVER`
- Reviewer: `{SILVER_REVIEWER_MODEL}` via `CODEX_DIRECT`, reasoning effort `high`
- Exact selected benchmark mantras: **{len(annotations)}**
- Batch plan: **8 batches x 15**, persisted and validated after each batch
- Human gold status: `UNANNOTATED`
- Unlocked predicates: `[]`
- Silver assertions remain review evidence; they authorize no accepted semantic edge.

## Independent results

- Sol no-claim count: **{no_claim_count}**
- Sol assertion count: **{metrics.sol_assertion_count}**
- Sol entities used: **{sum(len(item.entities) for item in annotations)}**
- Ontology gaps recorded: **{ontology_gap_count}**
- Predicate distribution: `{dict(sorted(sol_predicates.items()))}`

## Blind-review verification

The review loader accepted only files named `evidence.jsonl`; it rejected model-output
field names. All 120 rows were persisted before `blind_review_seal.json` was written.
The comparison entry point verified the selected-ID hash, the complete annotation-file
hash, every annotation hash, and every EvidencePacket hash before reading Luna output.
The seal records the later reveal separately. Human-gold files were not inputs to the
judgment stage and were not modified.

## Interpretation

This benchmark is suitable for prompt/ontology debugging and audit triage. It is not a
substitute for qualified Sanskrit/Vedic review and must never be reported as precision,
recall, or F1 against human truth.
"""
    _write(REPORT_ROOT / "RIGVEDA_SEMANTIC_SILVER_BENCHMARK.md", benchmark)

    compare_report = f"""# Rigveda semantic Luna vs Sol

{NOTICE}

## Agreement summary

- Luna assertions in the 120-mantra subset: **{metrics.luna_assertion_count}**
- Sol assertions: **{metrics.sol_assertion_count}**
- Exact matches: **{metrics.exact_matches}**
- Partial matches: **{metrics.partial_matches}**
- Silver agreement precision (exact / Luna): **{_fmt(metrics.silver_agreement_precision)}**
- Silver agreement recall (exact / Sol): **{_fmt(metrics.silver_agreement_recall)}**
- Relation-set agreement: **{metrics.relation_set_agreements}/{metrics.mantra_count}**
- No-claim agreement: {no_claim_line}
- Entity agreement among Luna assertions: {entity_line}
- Evidence agreement: {evidence_line}
- Disagreement rate across comparison rows: **{_fmt(metrics.disagreement_rate)}**
- Comparison categories: `{dict(sorted(category_counts.items()))}`

## Predicate-by-predicate agreement

| Predicate | Sol | Luna | Exact match |
|---|---:|---:|---:|
{chr(10).join(predicate_lines)}

## Evidence findings

- Evidence assessments: `{dict(sorted(evidence_counts.items()))}`
- Missing cited token IDs: **{evidence_counts["TOKEN_REFERENCE_MISSING"]}**
- Missing translation IDs: **{evidence_counts["TRANSLATION_REFERENCE_MISSING"]}**
- Metadata-only Luna support: **{evidence_counts["METADATA_ONLY"]}**
- Textual-overreach findings: **{evidence_counts["TEXTUAL_OVERREACH"]}**
- Ambiguous relation support: **{evidence_counts["AMBIGUOUS"]}**

## Safety

`unlocked_predicates = []`. Silver agreement does not authorize `AUTO_ACCEPTED` or
`HUMAN_ACCEPTED`; all semantic outputs remain candidate/review material.
"""
    _write(REPORT_ROOT / "RIGVEDA_SEMANTIC_LUNA_VS_SOL.md", compare_report)

    disagreement_groups: dict[str, list[Any]] = defaultdict(list)
    for item in comparisons:
        if item.category.value not in {"MATCH", "NO_CLAIM_AGREEMENT"}:
            disagreement_groups[item.mantra_id].append(item)
    disagreement_lines: list[str] = []
    for mantra_id, rows in sorted(disagreement_groups.items()):
        labels = ", ".join(
            f"{row.category.value}: "
            f"Luna={row.luna_predicate.value if row.luna_predicate else 'none'}"
            f"/{row.luna_object or 'none'}; "
            f"Sol={row.sol_predicate.value if row.sol_predicate else 'none'}"
            f"/{row.sol_object or 'none'}"
            for row in rows
        )
        disagreement_lines.append(f"- `{mantra_id}` — {labels}")
    disagreement_report = f"""# Rigveda semantic disagreements

{NOTICE}

## Major patterns

- Luna emitted only `INVOKES` in this selected subset; Sol used
  **{len(sol_predicates)}** predicates.
- Explicit Luna-missed relations: **{category_counts["LUNA_MISSED_RELATION"]}**.
- Non-explicit Sol-only relations: **{category_counts["SOL_ONLY_RELATION"]}**.
- Wrong-predicate alignments: **{category_counts["WRONG_PREDICATE"]}**.
- Wrong-entity alignments: **{category_counts["WRONG_ENTITY"]}**.
- Partial matches: **{category_counts["PARTIAL_MATCH"]}**.
- Luna unsupported-only claims: **{category_counts["UNSUPPORTED"]}**.
- `SEMANTIC_EXTRACTION_RECALL_GAP`: **flagged**.

The large gap is a model-model diagnostic, not proof that every Sol relation is correct.
The dominant pattern supports `LUNA_TOO_CONSERVATIVE`, `PROMPT_REVISION_REQUIRED`, and
`SECOND_PILOT_REQUIRED`. Cases with opaque referents or person-role ontology gaps remain
`DISAGREEMENT_REQUIRES_EXPERT` in the audit plan rather than being treated as Sol wins.

## Complete disagreement index

{chr(10).join(disagreement_lines)}
"""
    _write(REPORT_ROOT / "RIGVEDA_SEMANTIC_DISAGREEMENTS.md", disagreement_report)

    annotations_by_id = {item.mantra_id: item for item in annotations}
    audit_lines: list[str] = []
    for index, mantra_id in enumerate(audit_ids[:20], 1):
        rows = [item for item in comparisons if item.mantra_id == mantra_id]
        categories = sorted({item.category.value for item in rows})
        predicates = sorted(
            {
                predicate.value
                for item in rows
                for predicate in (item.luna_predicate, item.sol_predicate)
                if predicate is not None
            }
        )
        entities = sorted(
            {value for item in rows for value in (item.luna_object, item.sol_object) if value}
        )
        evidence = sorted(
            {
                item.evidence_assessment.value
                for item in rows
                if item.evidence_assessment is not None
            }
        )
        annotation = annotations_by_id[mantra_id]
        reason_bits = []
        if annotation.ontology_gaps:
            reason_bits.append("ontology gap")
        if annotation.uncertainties:
            reason_bits.append("ambiguous packet evidence")
        if any(item.category.value == "LUNA_MISSED_RELATION" for item in rows):
            reason_bits.append("tests conservative-recall policy")
        if any(item.category.value in {"WRONG_ENTITY", "WRONG_PREDICATE"} for item in rows):
            reason_bits.append("direct model disagreement")
        audit_lines.append(
            f"{index}. `{mantra_id}` — predicates `{', '.join(predicates) or 'none'}`; "
            f"entities `{', '.join(entities) or 'none'}`; categories `{', '.join(categories)}`; "
            f"evidence `{', '.join(evidence) or 'packet-only'}`. "
            f"Review value: {', '.join(reason_bits) or 'stratified control case'}."
        )
    audit_report = f"""# Rigveda semantic expert audit queue

{NOTICE}

This is a proposed expert-audit queue, not human gold. The configuration contains
**{len(audit_ids)}** IDs selected to maximize disagreement, predicate, evidence,
ontology-gap, and Maṇḍala coverage. The 20 highest-value cases are summarized here
without bulk verse text.

{chr(10).join(audit_lines)}

The expert should adjudicate these packet-bounded claims; they should not be asked to
annotate all 120 mantras from scratch.
"""
    _write(REPORT_ROOT / "RIGVEDA_SEMANTIC_EXPERT_AUDIT_QUEUE.md", audit_report)

    covered = sorted(sol_predicates)
    missing = sorted(item.value for item in ALLOWED_PREDICATES if item.value not in sol_predicates)
    coverage_report = f"""# Rigveda semantic predicate coverage

{NOTICE}

- Current ontology: `{ONTOLOGY_VERSION}` (unchanged)
- Allowed predicates: **{len(ALLOWED_PREDICATES)}**
- Predicates represented by Sol: **{len(covered)}** — `{covered}`
- Predicates absent from Sol: **{len(missing)}** — `{missing}`
- Luna predicates in this subset: `{dict(sorted(luna_predicates.items()))}`
- Full Luna pilot predicate scope remains `INVOKES` and `PRAISES` only.
- `SEMANTIC_EXTRACTION_RECALL_GAP`: **flagged**
- Ontology gaps: **{ontology_gap_count}**, dominated by missing human person/role typing
  and opaque referents.
- Ontology was not changed and no predicate was unlocked.

| Predicate | Sol assertions | Luna assertions | Exact matches |
|---|---:|---:|---:|
{chr(10).join(predicate_lines)}

Recommended next step: revise the extraction prompt to ask explicitly—but conservatively—
about each whitelisted low/medium-risk family, then run a second 120-mantra pilot and
send the proposed 25-case subset to a qualified Sanskrit/Vedic expert. Do not scale to
10,552 mantras before that review.
"""
    _write(REPORT_ROOT / "RIGVEDA_SEMANTIC_PREDICATE_COVERAGE.md", coverage_report)

    metrics_payload = {
        "notice": "These are model-vs-model silver metrics, not human-gold accuracy.",
        "mantra_count": metrics.mantra_count,
        "sol_no_claim_count": no_claim_count,
        "sol_assertion_count": metrics.sol_assertion_count,
        "luna_assertion_count": metrics.luna_assertion_count,
        "exact_matches": metrics.exact_matches,
        "partial_matches": metrics.partial_matches,
        "silver_agreement_precision": metrics.silver_agreement_precision,
        "silver_agreement_recall": metrics.silver_agreement_recall,
        "no_claim_agreement": metrics.no_claim_agreement,
        "entity_agreement": metrics.entity_agreement,
        "evidence_agreement": metrics.evidence_agreement,
        "disagreement_rate": metrics.disagreement_rate,
        "categories": dict(sorted(category_counts.items())),
        "predicate_rows": metrics.predicate_rows,
        "unlocked_predicates": [],
    }
    _write(
        SILVER_ROOT / "silver_metrics.json", json.dumps(metrics_payload, indent=2, sort_keys=True)
    )

    output_paths = [
        annotations_path,
        seal_path,
        comparisons_path,
        SILVER_ROOT / "silver_metrics.json",
        AUDIT_CONFIG,
        REPORT_ROOT / "RIGVEDA_SEMANTIC_SILVER_BENCHMARK.md",
        REPORT_ROOT / "RIGVEDA_SEMANTIC_LUNA_VS_SOL.md",
        REPORT_ROOT / "RIGVEDA_SEMANTIC_DISAGREEMENTS.md",
        REPORT_ROOT / "RIGVEDA_SEMANTIC_EXPERT_AUDIT_QUEUE.md",
        REPORT_ROOT / "RIGVEDA_SEMANTIC_PREDICATE_COVERAGE.md",
    ]
    luna_manifest: Any = json.loads((LUNA_ROOT / "semantic_run_manifest.json").read_text())
    manifest = SilverBenchmarkManifest(
        run_id=SILVER_RUN_ID,
        corpus_manifest_sha256=file_sha256(Path("data/canonical/rigveda_full_v1/manifest.json")),
        deterministic_knowledge_manifest_sha256=file_sha256(
            Path("data/knowledge/rigveda_deterministic_v1/manifest.json")
        ),
        lexical_manifest_sha256=file_sha256(
            Path("data/knowledge/rigveda_lexical_v1/manifest.json")
        ),
        semantic_ontology_version=ONTOLOGY_VERSION,
        luna_pilot_run_id=luna_manifest["run_id"],
        luna_model_id=luna_manifest["model"],
        sol_reviewer_model_id=SILVER_REVIEWER_MODEL,
        silver_status="COMPLETE",
        selected_mantra_count=len(selected_ids),
        reviewed_mantra_count=len(annotations),
        evidence_packet_hashes={key: packets[key].input_sha256 for key in sorted(packets)},
        output_hashes={path.as_posix(): file_sha256(path) for path in output_paths},
        unlocked_predicates=[],
        created_at=datetime.now(UTC),
    )
    _write(
        SILVER_ROOT / "semantic_silver_manifest.json",
        json.dumps(manifest.model_dump(mode="json"), ensure_ascii=False, indent=2, sort_keys=True),
    )
    print(json.dumps(metrics_payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
