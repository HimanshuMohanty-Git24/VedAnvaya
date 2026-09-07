"""Open the baseline only after replication sealing, then write stability reports."""

# Report prose is intentionally kept readable in the generated Markdown.
# ruff: noqa: E501, RUF001

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from vedagraph.semantic.replication import (
    compare_replications,
    file_sha256,
    load_assertions,
    load_payloads,
    readiness_recommendation,
    validate_replication_seal,
)

BASE = Path("data/semantic/vedagraph-rigveda-semantic-luna-v3-120")
REPL = Path("data/semantic/vedagraph-rigveda-semantic-luna-v3-replication-120")
REPORTS = Path("docs/reports")
CORPUS_MANIFEST = Path("data/canonical/rigveda_full_v1/manifest.json")
TRADITIONAL_MANIFEST = Path("data/knowledge/rigveda_deterministic_v1/manifest.json")
LEXICAL_MANIFEST = Path("data/knowledge/rigveda_lexical_v1/manifest.json")
NORMALIZATION_MANIFEST = Path(
    "data/semantic/vedagraph-rigveda-semantic-normalization-v1/normalization_manifest.json"
)


def dump_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def md_table(mapping: dict[str, Any], headers: tuple[str, ...]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    field_names = {
        "A count": "a_count",
        "B count": "b_count",
        "matched assertions": "matched_assertions",
        "A-only": "a_only",
        "B-only": "b_only",
        "exact_matches": "exact_matches",
        "granularity_differences": "granularity_differences",
        "conflicts": "conflicts",
    }
    for key, value in mapping.items():
        if isinstance(value, dict):
            lines.append(
                "| "
                + " | ".join(
                    [f"`{key}`"]
                    + [str(value.get(field_names.get(header, header), 0)) for header in headers[1:]]
                )
                + " |"
            )
        else:
            lines.append(f"| `{key}` | {value} |")
    return "\n".join(lines)


def write_report(name: str, text: str) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / name).write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def write_expert_queue(data: dict[str, Any]) -> None:
    existing_text = (REPORTS / "RIGVEDA_SEMANTIC_EXPERT_AUDIT_QUEUE_V3.md").read_text(
        encoding="utf-8"
    )
    existing_ids = re.findall(r"VG:RV:SAK:M\d{2}:S\d{3}:V\d{3}", existing_text)
    unstable_ids = {row["mantra_id"] for row in data["high_severity_rows"]}
    gap_ids = {
        item.mantra_id
        for side in (load_payloads(BASE), load_payloads(REPL))
        for item in side.values()
        if item.ontology_gaps
    }
    sol_rows = [
        json.loads(line)
        for line in (BASE / "v3_vs_sol_structured_comparisons.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    substantive = {
        "PREDICATE_DIFFERENCE",
        "OBJECT_TYPE_DIFFERENCE",
        "CONFLICTING_OBJECT",
        "LEFT_ONLY",
        "RIGHT_ONLY",
        "UNRESOLVED",
        "EXPERT_REQUIRED",
    }
    sol_ids = {row["mantra_id"] for row in sol_rows if row.get("category") in substantive}
    ranked: list[tuple[int, str, str]] = []
    for mantra_id in existing_ids:
        if mantra_id in unstable_ids:
            ranked.append((0, mantra_id, "MODEL_UNSTABLE"))
        elif mantra_id in gap_ids:
            ranked.append((1, mantra_id, "ONTOLOGY_GAP"))
        elif mantra_id in sol_ids:
            ranked.append((2, mantra_id, "STABLE_MODEL_DISAGREEMENT"))
        else:
            ranked.append((3, mantra_id, "EXPERT_PHILOLOGY_REQUIRED"))
    ranked.sort(key=lambda item: (item[0], existing_ids.index(item[1])))
    lines = [
        "# RIGVEDA SEMANTIC EXPERT QUEUE AFTER STABILITY",
        "",
        "**NO HUMAN GOLD EXISTS.** **STABILITY IS NOT ACCURACY.** No expert answers were obtained; this is only reprioritization of the existing 20-case queue.",
        "",
        "| Priority | Mantra | Classification | Basis |",
        "|---:|---|---|---|",
    ]
    for priority, (rank, mantra_id, classification) in enumerate(ranked[:20], 1):
        basis = {
            0: "A/B high-severity instability",
            1: "A or B ontology gap",
            2: "stable Luna pair but existing Sol disagreement",
            3: "existing expert-review queue",
        }[rank]
        lines.append(f"| {priority} | `{mantra_id}` | `{classification}` | {basis} |")
    lines.extend(
        [
            "",
            "Categories are diagnostic classes only. No queue item modifies either run, unlocks a predicate, or creates human gold.",
        ]
    )
    write_report("RIGVEDA_SEMANTIC_EXPERT_QUEUE_AFTER_STABILITY.md", "\n".join(lines))


def main() -> None:
    # This is the hard gate.  Only after it returns are baseline semantic files opened.
    seal = validate_replication_seal(
        REPL / "v3_replication_output_seal.json", REPL / "input_freeze.json"
    )
    left_payloads = load_payloads(BASE)
    right_payloads = load_payloads(REPL)
    data = compare_replications(BASE, REPL)
    recommendation = readiness_recommendation(data)
    dump_json(REPL / "v3_replication_stability_metrics.json", data)
    rows = data["rows"]
    predicate_lines = [
        "# RIGVEDA SEMANTIC V3 PREDICATE STABILITY",
        "",
        "**NO HUMAN GOLD EXISTS.** **STABILITY IS NOT ACCURACY.** This is a structured model-self-stability comparison.",
        "",
        md_table(
            data["predicate"],
            ("Predicate", "A count", "B count", "matched assertions", "A-only", "B-only"),
        ),
        "",
        "| Predicate | Mantras where presence agrees | Mantras where presence differs |",
        "|---|---:|---:|",
        *[
            f"| `{name}` | {values['mantras_presence_agrees']} | {values['mantras_presence_differs']} |"
            for name, values in data["predicate"].items()
        ],
    ]
    write_report("RIGVEDA_SEMANTIC_V3_PREDICATE_STABILITY.md", "\n".join(predicate_lines))

    object_lines = [
        "# RIGVEDA SEMANTIC V3 OBJECT STABILITY",
        "",
        "**NO HUMAN GOLD EXISTS.** **STABILITY IS NOT ACCURACY.** Object identity is compared by typed fields, not fuzzy labels.",
        "",
        md_table(
            data["object_kind"],
            (
                "Object kind",
                "A count",
                "B count",
                "exact_matches",
                "granularity_differences",
                "conflicts",
            ),
        ),
        "",
        f"Canonical entity contradictions: **{len(data['canonical_entity_contradictions'])}**.",
    ]
    write_report("RIGVEDA_SEMANTIC_V3_OBJECT_STABILITY.md", "\n".join(object_lines))

    high = data["high_severity_rows"]
    high_lines = [
        "# RIGVEDA SEMANTIC V3 HIGH-SEVERITY DIFFERENCES",
        "",
        "**NO HUMAN GOLD EXISTS.** **STABILITY IS NOT ACCURACY.** High severity means a structural stability warning, not a truth judgment.",
        "",
        f"High-severity rows: **{len(high)}**; canonical-entity contradictions: **{len(data['canonical_entity_contradictions'])}**.",
        "",
    ]
    for row in high[:100]:
        high_lines.append(
            f"- `{row['mantra_id']}` — `{row['category']}`: A `{row['left_predicate']}` / `{row['left_object']}`; B `{row['right_predicate']}` / `{row['right_object']}`."
        )
    if not high:
        high_lines.append("- None.")
    write_report("RIGVEDA_SEMANTIC_V3_HIGH_SEVERITY_DIFFERENCES.md", "\n".join(high_lines))

    counts_a = Counter(item.predicate.value for item in load_assertions(BASE))
    counts_b = Counter(item.predicate.value for item in load_assertions(REPL))
    qa_a = {
        "assertions": data["a_assertions"],
        "no_claims": data["a_no_claims"],
        "assertions_per_mantra": data["a_assertions"] / 120,
        "predicate_distribution": dict(sorted(counts_a.items())),
        "object_kind_distribution": {
            kind: value["a_count"]
            for kind, value in data["object_kind"].items()
            if value["a_count"]
        },
        "canonical_entity_refs": data["object_kind"]
        .get("CANONICAL_ENTITY_REF", {})
        .get("a_count", 0),
        "non_canonical_objects": data["a_assertions"]
        + sum(len(item.ontology_gaps) for item in left_payloads.values())
        - data["object_kind"].get("CANONICAL_ENTITY_REF", {}).get("a_count", 0),
        "ontology_gaps": sum(len(item.ontology_gaps) for item in left_payloads.values()),
        "explicitness": dict(
            sorted(Counter(item.explicitness.value for item in load_assertions(BASE)).items())
        ),
    }
    qa_b = {
        "assertions": data["b_assertions"],
        "no_claims": data["b_no_claims"],
        "assertions_per_mantra": data["b_assertions"] / 120,
        "predicate_distribution": dict(sorted(counts_b.items())),
        "object_kind_distribution": {
            kind: value["b_count"]
            for kind, value in data["object_kind"].items()
            if value["b_count"]
        },
        "canonical_entity_refs": data["object_kind"]
        .get("CANONICAL_ENTITY_REF", {})
        .get("b_count", 0),
        "non_canonical_objects": data["b_assertions"]
        + sum(len(item.ontology_gaps) for item in right_payloads.values())
        - data["object_kind"].get("CANONICAL_ENTITY_REF", {}).get("b_count", 0),
        "ontology_gaps": sum(len(item.ontology_gaps) for item in right_payloads.values()),
        "explicitness": dict(
            sorted(Counter(item.explicitness.value for item in load_assertions(REPL)).items())
        ),
    }
    replication_report = f"""# RIGVEDA SEMANTIC V3 REPLICATION

**NO HUMAN GOLD EXISTS.** **STABILITY IS NOT ACCURACY.** This report documents an independent second extraction over the same 120-mantra benchmark. It is not accuracy or truth evaluation.

## Input freeze

- Selected IDs: **120**; selected-ID hash: `{seal["selected_id_sha256"]}`.
- Prompt hash: `{seal["prompt_sha256"]}`; schema hash: `{seal["schema_sha256"]}`.
- EvidencePacket hashes: **120**, sealed before comparison.
- Comparison sources opened during extraction/sealing: **false**.

## Configuration

- Model: `{seal["model"]}`; reasoning: `{seal["reasoning"]}`; runtime: `{seal["runtime"]}`; API invocation: `{seal["api_invocation"]}`.
- Batch structure: **8 × 15**; human gold: **UNANNOTATED**; unlocked predicates: `[]`.

## Replication-only QA

| Measure | V3-A | V3-B |
|---|---:|---:|
| Assertions | {qa_a["assertions"]} | {qa_b["assertions"]} |
| No-claim mantras | {qa_a["no_claims"]} | {qa_b["no_claims"]} |
| Assertions/mantra | {qa_a["assertions_per_mantra"]:.3f} | {qa_b["assertions_per_mantra"]:.3f} |
| Canonical refs | {qa_a["canonical_entity_refs"]} | {qa_b["canonical_entity_refs"]} |
| Non-canonical assertion objects | {qa_a["non_canonical_objects"]} | {qa_b["non_canonical_objects"]} |
| Ontology gaps | {qa_a["ontology_gaps"]} | {qa_b["ontology_gaps"]} |
| EXPLICIT | {qa_a["explicitness"].get("EXPLICIT", 0)} | {qa_b["explicitness"].get("EXPLICIT", 0)} |
| STRONG_INFERENCE | {qa_a["explicitness"].get("STRONG_INFERENCE", 0)} | {qa_b["explicitness"].get("STRONG_INFERENCE", 0)} |
| Validator rejections | 0 | 0 |
| Evidence failures | 0 | 0 |

## Stability

- Exact assertion-set agreement: **{data["exact_assertion_set_agreement"]}**.
- Partial assertion-set agreement: **{data["partial_assertion_set_agreement"]}**.
- Different assertion-set: **{data["different_assertion_set"]}**.
- No-claim agreement: **{data["no_claim_agreement"]}**; no-claim disagreement: **{data["no_claim_disagreement"]}**.
- Evidence references: same **{data["evidence"]["same_evidence_references"]}**, different valid **{data["evidence"]["different_valid_evidence_references"]}**, invalid A/B **{data["evidence"]["a_invalid_evidence_rows"]}/{data["evidence"]["b_invalid_evidence_rows"]}**.
- Explicitness switches EXPLICIT ↔ STRONG_INFERENCE: **{data["explicitness_switches"]}**.
- Severity rows: low **{data["severity_counts"].get("LOW", 0)}**, medium **{data["severity_counts"].get("MEDIUM", 0)}**, high **{data["severity_counts"].get("HIGH", 0)}**.

## Scorecard

| Scorecard item | Result |
|---|---:|
| Mantra exact-set stability | {data["exact_assertion_set_agreement"]}/120 |
| Predicate-presence stability | see predicate report |
| Canonical-entity stability | {len(data["canonical_entity_contradictions"])} contradictions |
| Typed-object stability | see object report |
| Evidence-anchor stability | {data["evidence"]["same_evidence_references"]} same / {data["evidence"]["different_valid_evidence_references"]} different valid |
| No-claim stability | {data["no_claim_agreement"]}/120 agreement |
| High-severity disagreement count | {len(high)} |

## Gate

Recommendation: **{recommendation}**.

This does not unlock predicates, create human gold, auto-accept assertions, or make V3 truth. Any future 508 run remains candidate-only and expert-review cases remain flagged.

## Slow deterministic rebuild

- Knowledge-layer byte-identical rebuild: **PASS**.
- Lexical-layer byte-identical rebuild: **NOT_COMPLETED** after a separate practical wait; it was interrupted.
- Unicode-normalization checks: **PASS**.
"""
    write_report("RIGVEDA_SEMANTIC_V3_REPLICATION.md", replication_report)
    write_expert_queue(data)

    request = data["request"]
    event = data["event"]
    write_report(
        "RIGVEDA_SEMANTIC_V3_STABILITY.md",
        f"""# RIGVEDA SEMANTIC V3 STABILITY

**NO HUMAN GOLD EXISTS.** **STABILITY IS NOT ACCURACY.**

## Mantra and assertion stability

- Exact assertion-set agreement: **{data["exact_assertion_set_agreement"]}**.
- Partial assertion-set agreement: **{data["partial_assertion_set_agreement"]}**.
- Different assertion-set: **{data["different_assertion_set"]}**.
- No-claim agreement/disagreement: **{data["no_claim_agreement"]} / {data["no_claim_disagreement"]}**.

## Typed object and predicate stability

- Exact canonical entity matches are counted per object-kind table; contradictions: **{len(data["canonical_entity_contradictions"])}**.
- Predicate differences: **{sum(row["category"] == "PREDICATE_DIFFERENCE" for row in rows)}**.
- Object-type differences: **{sum(row["category"] == "OBJECT_TYPE_DIFFERENCE" for row in rows)}**.
- Granularity differences: **{sum(row["category"] == "GRANULARITY_DIFFERENCE" for row in rows)}**.
- Low/medium/high rows: **{data["severity_counts"].get("LOW", 0)} / {data["severity_counts"].get("MEDIUM", 0)} / {data["severity_counts"].get("HIGH", 0)}**.

## Request stability

- Same number of requested outcomes: **{request["same_number_of_outcomes_mantras"]}** mantras.
- Same normalized heads: **{request["same_normalized_heads_mantras"]}** mantras.
- Split/merge disagreements: **{request["split_merge_disagreements"]}**; qualifier **{request["qualifier_disagreements"]}**; beneficiary **{request["beneficiary_disagreements"]}**; target **{request["target_disagreements"]}**.
- Outcome order is ignored; normalized-head substitutions are not.

## Event stability

- Paired events: **{event.get("paired_events", 0)}**; same action head: **{event.get("same_action_head", 0)}**; action-head mismatches: **{event.get("action_head_mismatches", 0)}**.
- Actor/patient/participant/qualifier differences: **{event.get("actor_differences", 0)} / {event.get("patient_differences", 0)} / {event.get("participant_differences", 0)} / {event.get("qualifier_differences", 0)}**.
- Action heads are not synonym-normalized; `destroy` versus `slay` is a stability difference.

## Ontology and explicitness

- Ontology-gap counts: A `{data["gap_counts"]["a"]}`; B `{data["gap_counts"]["b"]}`; code-count disagreements **{data["gap_count_disagreements"]}**.
- EXPLICIT ↔ STRONG_INFERENCE switches: **{data["explicitness_switches"]}**; INTERPRETIVE emissions are prohibited by schema.

See the predicate, object, and high-severity reports for detail.
""",
    )

    # The manifest is written last and pins every relevant artifact without touching either run.
    manifest = {
        "manifest_id": REPL.name,
        "manifest_version": "rigveda-semantic-v3-replication-manifest-v1",
        "corpus_manifest": "data/canonical/rigveda_full_v1/manifest.json",
        "traditional_knowledge_manifest": "data/knowledge/rigveda_deterministic_v1/manifest.json",
        "lexical_manifest": "data/knowledge/rigveda_lexical_v1/manifest.json",
        "normalization_manifest": "data/semantic/vedagraph-rigveda-semantic-normalization-v1/normalization_manifest.json",
        "original_v3_manifest_hash": file_sha256(BASE / "manifest.json"),
        "corpus_manifest_sha256": file_sha256(CORPUS_MANIFEST),
        "traditional_knowledge_manifest_sha256": file_sha256(TRADITIONAL_MANIFEST),
        "lexical_manifest_sha256": file_sha256(LEXICAL_MANIFEST),
        "normalization_manifest_sha256": file_sha256(NORMALIZATION_MANIFEST),
        "prompt_sha256": seal["prompt_sha256"],
        "schema_sha256": seal["schema_sha256"],
        "ontology_version": seal["ontology_version"],
        "ontology_sha256": seal["ontology_sha256"],
        "policy_hashes": seal["policy_hashes"],
        "selected_id_sha256": seal["selected_id_sha256"],
        "evidence_packet_hashes": seal["packet_hashes"],
        "replication_output_seal": "v3_replication_output_seal.json",
        "replication_output_seal_sha256": file_sha256(REPL / "v3_replication_output_seal.json"),
        "output_hashes": seal["output_hashes"]
        | {
            "v3_replication_stability_metrics.json": file_sha256(
                REPL / "v3_replication_stability_metrics.json"
            )
        },
        "model": seal["model"],
        "runtime": seal["runtime"],
        "reasoning": seal["reasoning"],
        "api_invocation": seal["api_invocation"],
        "human_gold": "UNANNOTATED",
        "unlocked_predicates": [],
        "comparison_sources_opened": True,
        "comparison_sources_opened_after_valid_seal": True,
        "recommendation": recommendation,
        "slow_rebuild": {
            "knowledge_byte_identical": "PASS",
            "lexical_byte_identical": "NOT_COMPLETED",
            "unicode_normalization": "PASS",
        },
        "notes": "Model self-stability only. No human gold exists; stability is not accuracy.",
    }
    dump_json(REPL / "replication_manifest.json", manifest)
    print(
        json.dumps(
            {
                "recommendation": recommendation,
                "exact_mantra_agreement": data["exact_assertion_set_agreement"],
                "high_severity": len(high),
                "canonical_contradictions": len(data["canonical_entity_contradictions"]),
                "reports": 7,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
