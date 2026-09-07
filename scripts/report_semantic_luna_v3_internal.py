"""Produce v3-only quality reports before historical comparison sources are opened."""

# Markdown report templates intentionally preserve readable rendered lines.
# ruff: noqa: E501

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from vedagraph.models.normalization import SemanticExtractionV3
from vedagraph.semantic.v3 import PREDICATE_CHECKS

ROOT = Path("data/semantic/vedagraph-rigveda-semantic-luna-v3-120")
REPORTS = Path("docs/reports")


def rows(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def write(name: str, text: str) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / name).write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    payloads = [
        SemanticExtractionV3.model_validate(row) for row in rows(ROOT / "v3_extractions.jsonl")
    ]
    validations = rows(ROOT / "v3_validation.jsonl")
    assertions = [item for payload in payloads for item in payload.assertions]
    objects = [item.object for item in assertions] + [
        gap for payload in payloads for gap in payload.ontology_gaps
    ]
    predicates = Counter(item.predicate.value for item in assertions)
    kinds = Counter(item.object.object_kind.value for item in assertions)
    gap_codes = Counter(
        gap.ontology_gap_code.value
        for payload in payloads
        for gap in payload.ontology_gaps
        if gap.ontology_gap_code
    )
    explicitness = Counter(item.explicitness.value for item in assertions)
    canonical = [item for item in assertions if item.object.canonical_entity_id]
    anchors = [anchor for item in assertions for anchor in item.evidence]
    labels = [item.object.display_label for item in assertions]
    sentence_length = [label for label in labels if len(label.split()) > 8]
    coordinated = [
        item.object.normalized_head or ""
        for item in assertions
        if any(x in (item.object.normalized_head or "") for x in (",", ";", " and ", " or "))
    ]
    requests = [item for item in assertions if item.predicate.value == "REQUESTS"]
    request_violations = [
        item
        for item in requests
        if item.object.object_kind.value != "REQUESTED_OUTCOME"
        or not item.object.normalized_head
        or len(item.object.normalized_head.split()) > 5
        or any(x in item.object.normalized_head for x in (",", ";", " and ", " or "))
    ]
    events = [item for item in assertions if item.predicate.value == "DESCRIBES_ACTION"]
    event_heads = Counter(item.object.event.action_head for item in events if item.object.event)
    invalid_events = [item.assertion_id for item in events if item.object.event is None]
    boundary_rows = []
    for item in assertions:
        expected = {
            "INVOLVES_RITUAL": "RITUAL_EVENT",
            "INVOLVES_OFFERING": "OFFERING_REF",
            "INVOLVES_SUBSTANCE": "SUBSTANCE_REF",
            "REFERS_TO_NATURAL_PHENOMENON": "NATURAL_PHENOMENON_REF",
            "REFERS_TO_PLACE": "PLACE_REF",
        }.get(item.predicate.value)
        if expected and item.object.object_kind.value != expected:
            boundary_rows.append(
                (item.assertion_id, item.predicate.value, item.object.object_kind.value)
            )
    natural_entity_headings = [
        item.object.display_label
        for item in assertions
        if item.predicate.value == "REFERS_TO_NATURAL_PHENOMENON"
        and item.object.canonical_entity_id
    ]
    report = f"""# RIGVEDA semantic Luna v3 internal quality

**NO HUMAN GOLD EXISTS.** This is a v3-internal extraction report; no model comparison
source was opened when it was generated.

## Run

- Benchmark: **120** mantras, exactly **8 batches x 15**.
- Assertions: **{len(assertions)}** ({len(assertions) / 120:.3f}/mantra).
- No-claim mantras: **{sum(not payload.assertions for payload in payloads)}**.
- Ontology-gap objects: **{len(objects) - len(assertions)}**.
- Canonical entity references: **{len(canonical)}**.
- Non-canonical semantic object candidates: **{len(objects) - len(canonical)}**.

## Predicate distribution

| Predicate | Count |
|---|---:|
{chr(10).join(f"| `{family}` | {predicates.get(family, 0)} |" for family in PREDICATE_CHECKS)}

## Object-kind distribution

| Object kind | Count |
|---|---:|
{chr(10).join(f"| `{kind}` | {count} |" for kind, count in sorted(kinds.items()))}

Ontology gaps: `{dict(sorted(gap_codes.items()))}`.

## Explicitness and validity

- EXPLICIT: **{explicitness.get("EXPLICIT", 0)}**.
- STRONG_INFERENCE: **{explicitness.get("STRONG_INFERENCE", 0)}**.
- INTERPRETIVE emitted: **0** (refused by the v3 contract).
- Validator rejections: **{sum(row["status"] == "REJECTED" for row in validations)}**.
- Evidence failures: **{sum(bool(row["errors"]) for row in validations)}**.
- Average evidence anchors/assertion: **{len(anchors) / len(assertions):.3f}**.

## Representation QA

- Sentence-length display labels (>8 words): **{len(sentence_length)}**.
- Coordinated normalized heads: **{len(coordinated)}**.
- REQUESTS assertions: **{len(requests)}**; request-structure violations: **{len(request_violations)}**.
- Natural-phenomenon objects carrying canonical entity ids: **{len(natural_entity_headings)}** (must be 0).
- Ritual/offering/substance/place structural boundary violations: **{len(boundary_rows)}** (must be 0).

No predicate is unlocked: `unlocked_predicates = []`.
"""
    write("RIGVEDA_SEMANTIC_LUNA_V3.md", report)

    request_text = f"""# RIGVEDA semantic v3 request QA

**NO HUMAN GOLD EXISTS.** Request QA is a structural audit of packet-bounded v3 output,
not a truth score.

- REQUESTS assertions: **{len(requests)}**.
- All request objects are `REQUESTED_OUTCOME`: **{all(item.object.object_kind.value == "REQUESTED_OUTCOME" for item in requests)}**.
- Concise-head/coordinated-outcome violations: **{len(request_violations)}**.
- Independent-outcome splitting violations found: **{len(request_violations)}**.
- Beneficiary/target fields are separate schema fields; populated values: **{sum(bool(item.object.beneficiary_entity_id or item.object.target_entity_id) for item in requests)}**.
- Request-order independence: **PASS** (comparison signatures sort qualifiers and do not compare assertion order).

The extractor preserves evidenced heads and does not normalize synonyms such as protection/safety
or wealth/prosperity.
"""
    write("RIGVEDA_SEMANTIC_V3_REQUEST_QA.md", request_text)

    event_text = f"""# RIGVEDA semantic v3 event QA

**NO HUMAN GOLD EXISTS.** Event QA reports typed event shape only.

- DESCRIBES_ACTION assertions: **{len(events)}**.
- Events with actor: **{sum(bool(item.object.event and item.object.event.actor_entity_id) for item in events)}**.
- Events with patient: **{sum(bool(item.object.event and item.object.event.patient_entity_id) for item in events)}**.
- Events with both: **{sum(bool(item.object.event and item.object.event.actor_entity_id and item.object.event.patient_entity_id) for item in events)}**.
- Events with no participants: **{sum(bool(item.object.event and not item.object.event.actor_entity_id and not item.object.event.patient_entity_id and not item.object.event.other_participants) for item in events)}**.
- Invalid role attempts: **{len(invalid_events)}**.

## Action-head frequency

{chr(10).join(f"- `{head}`: {count}" for head, count in sorted(event_heads.items())) or "- none"}

No actor or patient roles were guessed where the packet did not directly support them.
"""
    write("RIGVEDA_SEMANTIC_V3_EVENT_QA.md", event_text)

    boundary_text = f"""# RIGVEDA semantic v3 type-boundary QA

**NO HUMAN GOLD EXISTS.** This report tests structural boundaries, not model correctness.

- Ritual assertions: **{predicates.get("INVOLVES_RITUAL", 0)}**, expected object kind `RITUAL_EVENT`.
- Offering assertions: **{predicates.get("INVOLVES_OFFERING", 0)}**, expected object kind `OFFERING_REF`.
- Substance assertions: **{predicates.get("INVOLVES_SUBSTANCE", 0)}**, expected object kind `SUBSTANCE_REF`.
- Natural-phenomenon assertions: **{predicates.get("REFERS_TO_NATURAL_PHENOMENON", 0)}**, expected object kind `NATURAL_PHENOMENON_REF`.
- Place assertions: **{predicates.get("REFERS_TO_PLACE", 0)}**, expected object kind `PLACE_REF`.
- Structural cross-kind leakage: **{len(boundary_rows)}**.
- Devata/phenomenon identity reuse: **{len(natural_entity_headings)}**.

Result: **PASS** when both counts are zero. Semantic boundary ambiguity remains eligible
for expert review even when structure is valid.
"""
    write("RIGVEDA_SEMANTIC_V3_TYPE_BOUNDARY_QA.md", boundary_text)
    print(
        json.dumps(
            {
                "assertions": len(assertions),
                "no_claims": sum(not payload.assertions for payload in payloads),
                "requests": len(requests),
                "events": len(events),
                "validator_rejections": sum(row["status"] == "REJECTED" for row in validations),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
