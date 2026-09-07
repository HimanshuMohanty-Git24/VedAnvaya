"""Descriptive QA over the sealed Claude Opus 5 V3.2 448 candidate run.

NO HUMAN GOLD EXISTS. MODEL SELF-AGREEMENT IS NOT ACCURACY.
CLAUDE OPUS 5 MODEL REVIEW IS NOT HUMAN GOLD.
ALL SEMANTIC OUTPUTS REMAIN CANDIDATE KNOWLEDGE.
50/448 PASSAGES LACK TRANSLATION ANCHOR COVERAGE UNDER THE CURRENT SEMANTIC CONTRACT.

Every number here is descriptive. None is precision, recall, accuracy or agreement with a
reference, because no reference exists. Nothing here rewrites, deletes or normalises a
model semantic decision; it counts, cross-checks against the packet, and risk-ranks cases.

**Two denominators.** 50 of the 448 EvidencePackets carry no translation text. The frozen
binding contract requires every assertion to anchor RELATION (and TARGET/OUTCOME) evidence
to character spans of the packet translation, so those 50 cannot emit an ordinary
assertion at all. They are ``STRUCTURAL_NO_TRANSLATION_ANCHOR``, not model omissions.
Model-behaviour metrics therefore use N=398; operational metrics use N=448. Both are
reported, always labelled.

Requires the run to be sealed first.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from vedagraph.semantic.claude_opus5_v3_2 import RUN_ID, RUN_ROOT  # noqa: E402
from vedagraph.semantic.codex_direct import ModelAuthoredResponse, PreparedTask  # noqa: E402
from vedagraph.semantic.object_ontology import SemanticObjectKind  # noqa: E402
from vedagraph.semantic.v3 import PREDICATE_CHECKS  # noqa: E402

RUN_DIR = ROOT / RUN_ROOT
TASKS_DIR = RUN_DIR / "store" / "tasks"
BROAD_PREDICATES = ("ASSOCIATED_WITH", "HAS_THEME", "CONTRASTS_WITH")
QUEUE_LIMIT = 75
STRUCTURAL_CODE = "STRUCTURAL_NO_TRANSLATION_ANCHOR"

#: Risk weights for the bounded review queue. Higher is reviewed sooner. These order a
#: queue; they are never a judgement that an assertion is wrong.
TRIGGER_WEIGHT = {
    "CANONICAL_TARGET_CONCERN": 10,
    "CROSS_AGENT_CALIBRATION_DISAGREEMENT": 9,
    "TRANSLATION_BEARING_NO_CLAIM": 9,
    "EXACT_DUPLICATE": 8,
    "REQUESTS_HEAVY_SPLIT": 7,
    "BROAD_PREDICATE": 6,
    "DESCRIBES_ACTION_OVERLAP": 6,
    "ONTOLOGY_GAP": 5,
    "AGENT_REGIME_OUTLIER": 5,
    "REPEATED_OBJECT_DIFFERENT_EVIDENCE": 2,
    "RETRY_HEAVY": 4,
    "UNUSUALLY_DENSE": 3,
    "PARALLEL_DISAGREEMENT": 3,
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


class Run:
    """The sealed run, loaded once, with the translation split precomputed."""

    def __init__(self) -> None:
        seal_path = RUN_DIR / "output_seal.json"
        if not seal_path.exists():
            raise SystemExit("QA_REFUSED: the run is not sealed; seal before aggregating")
        self.seal = read_json(seal_path)
        assignment = read_json(RUN_DIR / "claude_opus5_v3_2_448_agent_assignment.json")
        self.assignment = assignment
        self.group_of = {
            passage_id: name
            for name, row in assignment["groups"].items()
            for passage_id in row["passage_ids"]
        }
        self.tasks: dict[str, PreparedTask] = {}
        self.responses: dict[str, ModelAuthoredResponse] = {}
        for path in sorted(TASKS_DIR.glob("TASK_*/task.json")):
            task = PreparedTask.model_validate_json(path.read_text(encoding="utf-8"))
            terminal = [
                item
                for item in sorted((path.parent / "attempts").glob("attempt_*"))
                if (item / "validated.json").exists()
            ]
            if len(terminal) != 1:
                raise SystemExit(
                    f"QA_REFUSED: {task.passage_id} has {len(terminal)} terminal responses"
                )
            self.tasks[task.passage_id] = task
            self.responses[task.passage_id] = ModelAuthoredResponse.model_validate_json(
                (terminal[0] / "raw_response.json").read_text(encoding="utf-8")
            )
        self.passages = sorted(self.responses)
        self.translatable = [key for key in self.passages if self.has_translation(key)]
        self.translationless = [key for key in self.passages if not self.has_translation(key)]

    def has_translation(self, passage_id: str) -> bool:
        translation = self.tasks[passage_id].evidence_packet.translation
        return bool(translation and translation.text)

    def text(self, passage_id: str) -> str:
        translation = self.tasks[passage_id].evidence_packet.translation
        return (translation.text or "") if translation else ""

    def assertions_of(self, passage_id: str) -> list[Any]:
        return list(self.responses[passage_id].semantic_output.assertions)

    def no_claim(self, passage_id: str) -> bool:
        return bool(self.responses[passage_id].semantic_output.no_claim_reasons)

    def pairs(self, keys: list[str]) -> list[tuple[str, Any]]:
        return [(key, item) for key in keys for item in self.assertions_of(key)]


def span_of(assertion: Any) -> tuple[int, int]:
    span = assertion.evidence[0].translation_span
    return (span.start, span.end) if span else (-1, -1)


def object_span_of(assertion: Any) -> tuple[int, int]:
    span = assertion.object.evidence[0].translation_span
    return (span.start, span.end) if span else (-1, -1)


def distribution(run: Run, keys: list[str], label: str) -> dict[str, Any]:
    """One descriptive block over an explicit passage set, with its denominator named."""
    assertions = [item for key in keys for item in run.assertions_of(key)]
    no_claim = sum(1 for key in keys if run.no_claim(key))
    predicate_counts = Counter(item.predicate.value for item in assertions)
    canonical = sum(
        1
        for item in assertions
        if item.object.object_kind is SemanticObjectKind.CANONICAL_ENTITY_REF
    )
    return {
        "denominator_label": label,
        "passages": len(keys),
        "translation_bearing": sum(1 for key in keys if run.has_translation(key)),
        "translationless": sum(1 for key in keys if not run.has_translation(key)),
        "assertions": len(assertions),
        "assertions_per_passage": ratio(len(assertions), len(keys)),
        "no_claim_passages": no_claim,
        "no_claim_rate": ratio(no_claim, len(keys)),
        "explicitness": dict(
            sorted(Counter(item.explicitness.value for item in assertions).items())
        ),
        "predicate_counts": {key: predicate_counts.get(key, 0) for key in PREDICATE_CHECKS},
        "predicate_passage_presence": {
            key: sum(
                1
                for passage in keys
                if any(item.predicate.value == key for item in run.assertions_of(passage))
            )
            for key in PREDICATE_CHECKS
        },
        "object_kind_counts": dict(
            sorted(Counter(item.object.object_kind.value for item in assertions).items())
        ),
        "canonical_reference_assertions": canonical,
        "canonical_reference_rate": ratio(canonical, len(assertions)),
    }


def agent_block(run: Run, group: str) -> dict[str, Any]:
    """Raw and translation-normalised statistics for one author group.

    Both are reported because the round-robin partition does not equalise translation
    coverage exactly, and a group holding more translationless packets would look
    conservative on raw numbers alone for a reason that has nothing to do with the agent.
    """
    assigned = [key for key in run.passages if run.group_of[key] == group]
    bearing = [key for key in assigned if run.has_translation(key)]
    none = [key for key in assigned if not run.has_translation(key)]
    assertions = [item for key in assigned for item in run.assertions_of(key)]
    bearing_no_claim = sum(1 for key in bearing if run.no_claim(key))
    canonical = sum(
        1
        for item in assertions
        if item.object.object_kind is SemanticObjectKind.CANONICAL_ENTITY_REF
    )
    return {
        "group": group,
        "assigned_passages": len(assigned),
        "translation_bearing_passages": len(bearing),
        "translationless_passages": len(none),
        "assertions": len(assertions),
        "assertions_per_assigned_passage": ratio(len(assertions), len(assigned)),
        "assertions_per_translation_bearing_passage": ratio(len(assertions), len(bearing)),
        "no_claim_passages_overall": sum(1 for key in assigned if run.no_claim(key)),
        "no_claim_rate_overall": ratio(
            sum(1 for key in assigned if run.no_claim(key)), len(assigned)
        ),
        "no_claim_passages_translation_bearing": bearing_no_claim,
        "no_claim_rate_translation_bearing": ratio(bearing_no_claim, len(bearing)),
        "predicate_counts": {
            key: sum(1 for item in assertions if item.predicate.value == key)
            for key in PREDICATE_CHECKS
        },
        "object_kind_counts": dict(
            sorted(Counter(item.object.object_kind.value for item in assertions).items())
        ),
        "canonical_reference_assertions": canonical,
        "canonical_reference_rate": ratio(canonical, len(assertions)),
    }


def broad_row(run: Run, key: str, item: Any) -> dict[str, Any]:
    text = run.text(key)
    relation = span_of(item)
    obj = object_span_of(item)
    relation_text = text[relation[0] : relation[1]]
    object_text = text[obj[0] : obj[1]]
    # Engineering risk, not a semantic verdict: how far the anchors are from carrying the
    # relation on their own. A STRONG_INFERENCE broad predicate with a long, vague object
    # anchor is the shape that turns ASSOCIATED_WITH into a synonym pile.
    risk = "LOW"
    if item.explicitness.value == "STRONG_INFERENCE":
        risk = "HIGH"
    elif len(object_text) > 60 or len(relation_text) > 60:
        risk = "MEDIUM"
    elif item.object.object_kind.value in {"OPAQUE_REFERENT", "ONTOLOGY_GAP_REF"}:
        risk = "MEDIUM"
    return {
        "passage_key": key,
        "citation": run.tasks[key].citation,
        "group": run.group_of[key],
        "assertion_id": item.assertion_id,
        "predicate": item.predicate.value,
        "subject_id": item.subject_id,
        "object_kind": item.object.object_kind.value,
        "display_label": item.object.display_label,
        "normalized_head": item.object.normalized_head,
        "canonical_entity_id": item.object.canonical_entity_id,
        "explicitness": item.explicitness.value,
        "inference_step": item.inference_step,
        "relation_anchor": {"span": list(relation), "text": relation_text},
        "object_anchor": {"span": list(obj), "text": object_text},
        "engineering_risk": risk,
    }


def main() -> None:
    run = Run()
    all_keys, bearing, none_keys = run.passages, run.translatable, run.translationless

    # ---- translation anchor coverage --------------------------------------------------
    structural_returning_no_claim = [key for key in none_keys if run.no_claim(key)]
    structural_emitting = [key for key in none_keys if not run.no_claim(key)]
    translatable_no_claim = [key for key in bearing if run.no_claim(key)]
    coverage = {
        "section": "TRANSLATION_ANCHOR_COVERAGE",
        "diagnostic_code": STRUCTURAL_CODE,
        "code_written_into_candidate_payloads": False,
        "selected_passages": len(all_keys),
        "translation_bearing": len(bearing),
        "translationless": len(none_keys),
        "translationless_percentage": ratio(len(none_keys), len(all_keys)),
        "assertion_capable_under_current_contract": len(bearing),
        "structurally_no_claim_under_current_contract": len(none_keys),
        "translationless_returning_no_claim": len(structural_returning_no_claim),
        "translationless_emitting_assertions": len(structural_emitting),
        "all_translationless_returned_no_claim": len(structural_returning_no_claim)
        == len(none_keys),
        "translationless_emitting_passage_ids": structural_emitting,
        "TRANSLATABLE_PASSAGES_RETURNING_NO_CLAIM": {
            "count": len(translatable_no_claim),
            "rate_of_translation_bearing": ratio(len(translatable_no_claim), len(bearing)),
            "note": (
                "These are the informative no-claims: the packet carried an anchorable "
                "translation and the author still emitted nothing."
            ),
            "passages": [
                {
                    "passage_key": key,
                    "citation": run.tasks[key].citation,
                    "group": run.group_of[key],
                    "translation_text": run.text(key),
                    "no_claim_reasons": list(run.responses[key].semantic_output.no_claim_reasons),
                }
                for key in translatable_no_claim
            ],
        },
        "structural_cases_are_model_omissions": False,
    }

    overall_448 = distribution(run, all_keys, "ALL_SELECTED_N448")
    overall_398 = distribution(run, bearing, "TRANSLATION_BEARING_N398")
    overall_50 = distribution(run, none_keys, "TRANSLATIONLESS_N50")

    # ---- predicate distribution -------------------------------------------------------
    bearing_assertions = run.pairs(bearing)
    predicate_rows = {}
    for name in PREDICATE_CHECKS:
        rows = [(key, item) for key, item in bearing_assertions if item.predicate.value == name]
        participating = {key for key, _ in rows}
        predicate_rows[name] = {
            "assertions": len(rows),
            "passages": len(participating),
            "percentage_of_translation_bearing_passages": ratio(len(participating), len(bearing)),
            "average_per_participating_passage": ratio(len(rows), len(participating)),
            "explicitness": dict(
                sorted(Counter(item.explicitness.value for _, item in rows).items())
            ),
        }

    # ---- object distribution ----------------------------------------------------------
    object_rows = {}
    for kind in sorted(SemanticObjectKind):
        rows = [(key, item) for key, item in bearing_assertions if item.object.object_kind is kind]
        object_rows[kind.value] = {
            "assertions": len(rows),
            "passages": len({key for key, _ in rows}),
            "percentage_of_all_assertions": ratio(len(rows), len(bearing_assertions)),
        }

    # ---- mandala ----------------------------------------------------------------------
    by_mandala = {}
    for mandala in sorted({run.tasks[key].evidence_packet.mandala for key in all_keys}):
        members = [key for key in all_keys if run.tasks[key].evidence_packet.mandala == mandala]
        m_bearing = [key for key in members if run.has_translation(key)]
        m_assertions = [item for key in members for item in run.assertions_of(key)]
        by_mandala[f"M{mandala:02d}"] = {
            "selected_passages": len(members),
            "translation_bearing": len(m_bearing),
            "translationless": len(members) - len(m_bearing),
            "assertions": len(m_assertions),
            "assertions_per_translation_bearing_passage": ratio(len(m_assertions), len(m_bearing)),
            "no_claim_passages": sum(1 for key in members if run.no_claim(key)),
            "no_claim_rate_translation_bearing": ratio(
                sum(1 for key in m_bearing if run.no_claim(key)), len(m_bearing)
            ),
            "predicate_counts": {
                name: sum(1 for item in m_assertions if item.predicate.value == name)
                for name in PREDICATE_CHECKS
                if any(item.predicate.value == name for item in m_assertions)
            },
        }

    # ---- duplicate QA -----------------------------------------------------------------
    # Two signatures, because they answer different questions. The EXACT signature adds
    # both evidence spans: two assertions are a true structural duplicate only when they
    # say the same thing about the same object *from the same wording*. Without the spans,
    # two DESCRIBES assertions about one deity anchored to two different epithets collide,
    # and V3.2 Rule 6 explicitly allows those as independently supported relations. The
    # weaker signature is still reported, as an over-splitting review signal.
    duplicates: dict[str, list[dict[str, Any]]] = defaultdict(list)
    exact_groups = 0
    exact_redundant = 0
    weak_groups = 0
    weak_redundant = 0
    for key in all_keys:
        weak: dict[tuple[Any, ...], list[str]] = defaultdict(list)
        exact: dict[tuple[Any, ...], list[str]] = defaultdict(list)
        for item in run.assertions_of(key):
            base = (
                item.predicate.value,
                item.object.object_kind.value,
                item.object.canonical_entity_id,
                (item.object.normalized_head or "").strip().lower(),
            )
            weak[base].append(item.assertion_id)
            exact[(*base, span_of(item), object_span_of(item))].append(item.assertion_id)
        for signature, ids in exact.items():
            if len(ids) == 1:
                continue
            exact_groups += 1
            exact_redundant += len(ids) - 1
            bucket = {
                "REQUESTED_OUTCOME": "duplicate_requested_outcome",
                "SUBSTANCE_REF": "duplicate_substance_relation",
                "OFFERING_REF": "duplicate_offering_relation",
                "PLACE_REF": "duplicate_place_relation",
                "CANONICAL_ENTITY_REF": "duplicate_canonical_relation",
            }.get(signature[1], "duplicate_predicate_object")
            duplicates[bucket].append(
                {
                    "passage_key": key,
                    "citation": run.tasks[key].citation,
                    "predicate": signature[0],
                    "object_kind": signature[1],
                    "canonical_entity_id": signature[2],
                    "normalized_head": signature[3],
                    "count": len(ids),
                    "assertion_ids": ids,
                }
            )
        for signature, ids in weak.items():
            if len(ids) == 1:
                continue
            weak_groups += 1
            weak_redundant += len(ids) - 1
            duplicates["same_predicate_object_different_evidence"].append(
                {
                    "passage_key": key,
                    "citation": run.tasks[key].citation,
                    "predicate": signature[0],
                    "object_kind": signature[1],
                    "canonical_entity_id": signature[2],
                    "normalized_head": signature[3],
                    "count": len(ids),
                    "assertion_ids": ids,
                }
            )
    duplicate_counts = {
        "exact_duplicate_groups": exact_groups,
        "exact_duplicate_redundant_assertions": exact_redundant,
        "duplicate_canonical_relation": len(duplicates["duplicate_canonical_relation"]),
        "duplicate_requested_outcome": len(duplicates["duplicate_requested_outcome"]),
        "duplicate_substance_relation": len(duplicates["duplicate_substance_relation"]),
        "duplicate_offering_relation": len(duplicates["duplicate_offering_relation"]),
        "duplicate_place_relation": len(duplicates["duplicate_place_relation"]),
        "duplicate_predicate_object": len(duplicates["duplicate_predicate_object"]),
        "same_predicate_object_different_evidence_groups": weak_groups,
        "same_predicate_object_different_evidence_assertions": weak_redundant,
    }

    # ---- REQUESTS QA ------------------------------------------------------------------
    per_passage_requests = {
        key: [item for item in run.assertions_of(key) if item.predicate.value == "REQUESTS"]
        for key in all_keys
    }
    request_passages = {key: rows for key, rows in per_passage_requests.items() if rows}
    duplicate_outcomes = [
        {"passage_key": key, "normalized_head": head, "count": count}
        for key, rows in request_passages.items()
        for head, count in Counter(
            (item.object.normalized_head or "").strip().lower() for item in rows
        ).items()
        if head and count > 1
    ]
    outcome_anchor_failures = []
    for key in request_passages:
        bindings = {b.assertion_id: b for b in run.responses[key].assertion_bindings}
        for item in per_passage_requests[key]:
            binding = bindings.get(item.assertion_id)
            if binding is None or not any(a.role.value == "OUTCOME" for a in binding.anchors):
                outcome_anchor_failures.append(
                    {"passage_key": key, "assertion_id": item.assertion_id}
                )
    counts = {key: len(rows) for key, rows in per_passage_requests.items()}
    requests_qa = {
        "total_requests": sum(counts.values()),
        "passages_with_requests": len(request_passages),
        "average_per_requests_passage": ratio(sum(counts.values()), len(request_passages)),
        "max_in_one_passage": max(counts.values(), default=0),
        "passages_ge_2": sum(1 for n in counts.values() if n >= 2),
        "passages_ge_3": sum(1 for n in counts.values() if n >= 3),
        "passages_ge_5": sum(1 for n in counts.values() if n >= 5),
        "duplicate_normalized_outcome_count": len(duplicate_outcomes),
        "duplicate_normalized_outcomes": duplicate_outcomes,
        "outcome_anchor_failures": len(outcome_anchor_failures),
        "outcome_anchor_failure_rows": outcome_anchor_failures,
        "high_split_risk_queue": sorted(key for key, n in counts.items() if n >= 5),
        "note": "A high split count is a review candidate, never automatically invalid.",
    }

    # ---- DESCRIBES / DESCRIBES_ACTION QA ----------------------------------------------
    describes_only, action_only, both_keys = [], [], []
    exact_overlap, likely_redundant = [], []
    for key in all_keys:
        items = run.assertions_of(key)
        describes = [i for i in items if i.predicate.value == "DESCRIBES"]
        actions = [i for i in items if i.predicate.value == "DESCRIBES_ACTION"]
        if describes and not actions:
            describes_only.append(key)
        if actions and not describes:
            action_only.append(key)
        if describes and actions:
            both_keys.append(key)
            for left in describes:
                for right in actions:
                    left_span, right_span = span_of(left), span_of(right)
                    row = {
                        "passage_key": key,
                        "citation": run.tasks[key].citation,
                        "describes_assertion_id": left.assertion_id,
                        "action_assertion_id": right.assertion_id,
                        "describes_relation_span": list(left_span),
                        "action_relation_span": list(right_span),
                    }
                    if left_span == right_span:
                        exact_overlap.append(row)
                    elif (
                        left_span[0] < right_span[1]
                        and right_span[0] < left_span[1]
                        and left_span != (-1, -1)
                    ):
                        likely_redundant.append(row)
    action_head_problems = [
        {"passage_key": key, "assertion_id": item.assertion_id}
        for key, item in run.pairs(all_keys)
        if item.predicate.value == "DESCRIBES_ACTION"
        and (item.object.event is None or not (item.object.event.action_head or "").strip())
    ]
    describes_qa = {
        "describes_total": sum(
            1 for _, i in run.pairs(all_keys) if i.predicate.value == "DESCRIBES"
        ),
        "describes_action_total": sum(
            1 for _, i in run.pairs(all_keys) if i.predicate.value == "DESCRIBES_ACTION"
        ),
        "passages_describes_only": len(describes_only),
        "passages_action_only": len(action_only),
        "passages_with_both": len(both_keys),
        "exact_evidence_span_overlap_cases": len(exact_overlap),
        "exact_evidence_span_overlap": exact_overlap,
        "partial_span_overlap_likely_redundant_cases": len(likely_redundant),
        "partial_span_overlap_likely_redundant": likely_redundant[:60],
        "distinct_independently_supported_cases": len(both_keys)
        - len({row["passage_key"] for row in exact_overlap + likely_redundant}),
        "unresolved_cases": len({row["passage_key"] for row in likely_redundant}),
        "action_head_problems": len(action_head_problems),
        "relation_binding_failures": 0,
        "note": "No model output is rewritten; overlap cases become review candidates only.",
    }

    # ---- broad predicate audit --------------------------------------------------------
    broad_rows = [
        broad_row(run, key, item)
        for key, item in run.pairs(all_keys)
        if item.predicate.value in BROAD_PREDICATES
    ]
    broad_qa = {
        "counts": {
            name: sum(1 for row in broad_rows if row["predicate"] == name)
            for name in BROAD_PREDICATES
        },
        "total": len(broad_rows),
        "share_of_all_assertions": ratio(len(broad_rows), len(run.pairs(all_keys))),
        "risk_counts": dict(sorted(Counter(row["engineering_risk"] for row in broad_rows).items())),
        "assertions": broad_rows,
        "note": "Broad predicates are risk-ranked, never automatically rejected.",
    }

    # ---- canonical target QA ----------------------------------------------------------
    canonical_rows = []
    canonical_failures: Counter[str] = Counter()
    for key, item in run.pairs(all_keys):
        if item.object.object_kind is not SemanticObjectKind.CANONICAL_ENTITY_REF:
            continue
        packet = run.tasks[key].evidence_packet
        supplied = {mention.entity_key for mention in packet.mentions}
        entity_id = item.object.canonical_entity_id
        binding = next(
            (
                b
                for b in run.responses[key].assertion_bindings
                if b.assertion_id == item.assertion_id
            ),
            None,
        )
        targets = (
            [] if binding is None else [a for a in binding.anchors if a.role.value == "TARGET"]
        )
        problems = []
        if entity_id not in supplied:
            problems.append("ENTITY_NOT_A_SUPPLIED_MENTION")
        if item.predicate.value in {"INVOKES", "PRAISES", "DESCRIBES"}:
            if not targets:
                problems.append("NO_TARGET_ANCHOR")
            elif any(a.entity_id != entity_id for a in targets):
                problems.append("TARGET_ANCHOR_NAMES_ANOTHER_ENTITY")
            elif any((a.start, a.end) == span_of(item) for a in targets):
                problems.append("TARGET_ANCHOR_EQUALS_RELATION_ANCHOR")
        for anchor in targets:
            if anchor.text not in run.text(key):
                problems.append("FABRICATED_TARGET_ANCHOR_TEXT")
        for problem in problems:
            canonical_failures[problem] += 1
        canonical_rows.append(
            {
                "passage_key": key,
                "assertion_id": item.assertion_id,
                "predicate": item.predicate.value,
                "canonical_entity_id": entity_id,
                "target_anchor_texts": [a.text for a in targets],
                "supplied_mentions": sorted(supplied),
                "traditional_devata_keys": list(packet.devata_keys),
                "matches_traditional_devata": entity_id in set(packet.devata_keys),
                "problems": problems,
            }
        )
    contradictions = [
        row
        for row in canonical_rows
        if "TARGET_ANCHOR_NAMES_ANOTHER_ENTITY" in row["problems"]
        or "ENTITY_NOT_A_SUPPLIED_MENTION" in row["problems"]
    ]
    canonical_qa = {
        "canonical_assertion_count": len(canonical_rows),
        "canonical_passages": len({row["passage_key"] for row in canonical_rows}),
        "unique_canonical_ids": len(
            {row["canonical_entity_id"] for row in canonical_rows if row["canonical_entity_id"]}
        ),
        "target_failures": sum(1 for row in canonical_rows if row["problems"]),
        "failures_by_kind": dict(sorted(canonical_failures.items())),
        "fabricated_mentions": canonical_failures["ENTITY_NOT_A_SUPPLIED_MENTION"],
        "fabricated_target_anchor_text": canonical_failures["FABRICATED_TARGET_ANCHOR_TEXT"],
        "possible_contradictions": len(contradictions),
        "canonical_ref_matches_traditional_devata": sum(
            1 for row in canonical_rows if row["matches_traditional_devata"]
        ),
        "blocker": bool(contradictions),
        "note": (
            "A traditional Devata assignment is not semantic gold; the match count is "
            "descriptive and never used to accept or reject an assertion."
        ),
    }

    # ---- ontology gap QA --------------------------------------------------------------
    gap_rows = []
    for key, item in run.pairs(all_keys):
        if item.object.object_kind is not SemanticObjectKind.ONTOLOGY_GAP_REF:
            continue
        packet = run.tasks[key].evidence_packet
        supplied = {mention.entity_key for mention in packet.mentions}
        span = object_span_of(item)
        anchor_text = run.text(key)[span[0] : span[1]]
        code = item.object.ontology_gap_code.value if item.object.ontology_gap_code else None
        if code is None:
            classification = "UNRESOLVED"
        elif supplied and any(
            label.lower() in anchor_text.lower()
            for label in (m.entity_label for m in packet.mentions)
        ):
            classification = "COULD_RESOLVE_EXISTING_ENTITY"
        elif code in {
            "PERSON_LIKE_REFERENT_UNMODELED",
            "PATRON_ROLE_UNMODELED",
            "ANCESTOR_ROLE_UNMODELED",
            "KINSHIP_ROLE_UNMODELED",
        }:
            classification = "TRUE_SCHEMA_GAP"
        elif item.explicitness.value == "STRONG_INFERENCE":
            classification = "EXPERT_REQUIRED"
        else:
            classification = "OPAQUE_IS_SAFER"
        gap_rows.append(
            {
                "passage_key": key,
                "citation": run.tasks[key].citation,
                "assertion_id": item.assertion_id,
                "predicate": item.predicate.value,
                "ontology_gap_code": code,
                "display_label": item.object.display_label,
                "anchor_text": anchor_text,
                "anchor_valid": span != (-1, -1) and anchor_text in run.text(key),
                "supplied_mentions": sorted(supplied),
                "classification": classification,
            }
        )
    ontology_qa = {
        "total_ontology_gap_objects": len(gap_rows),
        "by_code": dict(sorted(Counter(row["ontology_gap_code"] for row in gap_rows).items())),
        "by_classification": dict(
            sorted(Counter(row["classification"] for row in gap_rows).items())
        ),
        "anchor_invalid": sum(1 for row in gap_rows if not row["anchor_valid"]),
        "opaque_referents": sum(
            1 for _, i in run.pairs(all_keys) if i.object.object_kind.value.startswith("OPAQUE")
        ),
        "ontology_expanded": False,
        "rows": gap_rows,
    }

    # ---- agent regime -----------------------------------------------------------------
    groups = sorted({run.group_of[key] for key in all_keys})
    per_agent = {group: agent_block(run, group) for group in groups}
    densities = [row["assertions_per_translation_bearing_passage"] for row in per_agent.values()]
    no_claim_rates = [row["no_claim_rate_translation_bearing"] for row in per_agent.values()]
    canonical_rates = [row["canonical_reference_rate"] for row in per_agent.values()]
    spread = {
        "normalised_density_min": min(densities),
        "normalised_density_max": max(densities),
        "normalised_density_ratio": round(max(densities) / min(densities), 4)
        if min(densities)
        else None,
        "translation_bearing_no_claim_rate_min": min(no_claim_rates),
        "translation_bearing_no_claim_rate_max": max(no_claim_rates),
        "translation_bearing_no_claim_rate_spread": round(
            max(no_claim_rates) - min(no_claim_rates), 4
        ),
        "canonical_reference_rate_min": min(canonical_rates),
        "canonical_reference_rate_max": max(canonical_rates),
        "canonical_reference_rate_spread": round(max(canonical_rates) - min(canonical_rates), 4),
    }
    density_ratio = spread["normalised_density_ratio"] or 1.0
    no_claim_spread = spread["translation_bearing_no_claim_rate_spread"]
    if density_ratio >= 1.5 or no_claim_spread >= 0.25:
        verdict = "CLEAR_AGENT_REGIME_DIVERGENCE"
    elif density_ratio >= 1.25 or no_claim_spread >= 0.12:
        verdict = "POSSIBLE_AGENT_REGIME_DIVERGENCE"
    else:
        verdict = "NO_AGENT_REGIME_DIVERGENCE"
    regime = {
        "verdict": verdict,
        "normalised_on": "translation-bearing passages only",
        "thresholds": (
            "CLEAR at normalised density ratio >= 1.5x or translation-bearing no-claim "
            "spread >= 0.25 (the v3.1 two-run regime split that motivated V3.2 was 1.73x "
            "and 0.47); POSSIBLE at >= 1.25x or >= 0.12"
        ),
        "spread": spread,
        "per_agent": per_agent,
    }

    # ---- review queue -----------------------------------------------------------------
    triggers: dict[str, list[str]] = defaultdict(list)
    for key in translatable_no_claim:
        triggers[key].append("TRANSLATION_BEARING_NO_CLAIM")
    for row in canonical_rows:
        if row["problems"]:
            triggers[row["passage_key"]].append("CANONICAL_TARGET_CONCERN")
    for row in broad_rows:
        triggers[row["passage_key"]].append("BROAD_PREDICATE")
    for key in requests_qa["high_split_risk_queue"]:
        triggers[key].append("REQUESTS_HEAVY_SPLIT")
    for row in exact_overlap + likely_redundant:
        triggers[row["passage_key"]].append("DESCRIBES_ACTION_OVERLAP")
    for bucket, rows in duplicates.items():
        if bucket == "same_predicate_object_different_evidence":
            for row in rows:
                triggers[row["passage_key"]].append("REPEATED_OBJECT_DIFFERENT_EVIDENCE")
            continue
        for row in rows:
            triggers[row["passage_key"]].append("EXACT_DUPLICATE")
    for row in gap_rows:
        if row["classification"] in {
            "COULD_RESOLVE_EXISTING_ENTITY",
            "EXPERT_REQUIRED",
            "UNRESOLVED",
        }:
            triggers[row["passage_key"]].append("ONTOLOGY_GAP")
    dense = sorted((len(run.assertions_of(key)) for key in bearing), reverse=True)
    dense_threshold = dense[max(0, len(dense) // 20)] if dense else 0
    for key in bearing:
        if len(run.assertions_of(key)) >= max(dense_threshold, 6):
            triggers[key].append("UNUSUALLY_DENSE")
    retry_counts = Counter(
        row["passage_id"]
        for row in (
            json.loads(line)
            for line in (RUN_DIR / "execution_events.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip()
        )
        if row.get("event") == "FAILED_IMPORT"
    )
    for key in retry_counts:
        triggers[key].append("RETRY_HEAVY")

    queue = sorted(
        (
            {
                "passage_key": key,
                "citation": run.tasks[key].citation,
                "group": run.group_of[key],
                "translation_bearing": run.has_translation(key),
                "assertions": len(run.assertions_of(key)),
                "no_claim": run.no_claim(key),
                "triggers": sorted(set(items)),
                "trigger_hits": len(items),
                "risk_score": sum(TRIGGER_WEIGHT.get(item, 1) for item in set(items))
                + (len(items) - len(set(items))),
                "status": "MODEL_REVIEW_CANDIDATE",
                "human_gold": False,
            }
            for key, items in triggers.items()
        ),
        key=lambda row: (-row["risk_score"], row["passage_key"]),
    )
    queue_path = ROOT / "docs/manifests/rigveda_semantic_claude_opus5_v3_2_448_review_queue.jsonl"
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    queue_path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
            for row in queue[:QUEUE_LIMIT]
        ),
        encoding="utf-8",
        newline="\n",
    )

    report = {
        "manifest_version": "rigveda-semantic-claude-opus5-v3.2-448-qa-v2",
        "run_id": RUN_ID,
        "seal_sha256": run.seal["seal_sha256"],
        "provenance_bucket": run.seal["provenance_bucket"],
        "human_gold_status": "UNANNOTATED",
        "model_self_agreement_is_accuracy": False,
        "claude_model_review_is_human_gold": False,
        "canonical_promotion": False,
        "unlocked_predicates": [],
        "metrics_are_descriptive_not_accuracy": True,
        "denominators": {
            "all_selected": len(all_keys),
            "translation_bearing": len(bearing),
            "translationless": len(none_keys),
            "primary_model_behaviour_denominator": len(bearing),
        },
        "translation_anchor_coverage": coverage,
        "overall_all_selected_n448": overall_448,
        "overall_translation_bearing_n398": overall_398,
        "overall_translationless_n50": overall_50,
        "predicate_distribution_translation_bearing": predicate_rows,
        "object_distribution_translation_bearing": object_rows,
        "by_mandala": by_mandala,
        "duplicate_qa": {"counts": duplicate_counts, "rows": dict(duplicates)},
        "requests_qa": requests_qa,
        "describes_qa": describes_qa,
        "broad_predicate_qa": broad_qa,
        "canonical_target_qa": canonical_qa,
        "canonical_target_rows": canonical_rows,
        "ontology_gap_qa": ontology_qa,
        "agent_regime": regime,
        "review_queue": {
            "candidates_found": len(queue),
            "queue_written": min(len(queue), QUEUE_LIMIT),
            "queue_limit": QUEUE_LIMIT,
            "dropped_beyond_limit": max(0, len(queue) - QUEUE_LIMIT),
            "path": queue_path.relative_to(ROOT).as_posix(),
            "trigger_counts": dict(
                sorted(Counter(t for row in queue for t in row["triggers"]).items())
            ),
        },
    }
    out = ROOT / "docs/manifests/rigveda_semantic_claude_opus5_v3_2_448_manifest.json"
    out.write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    print(
        json.dumps(
            {
                "denominators": report["denominators"],
                "translation_anchor_coverage": {
                    key: value
                    for key, value in coverage.items()
                    if key != "TRANSLATABLE_PASSAGES_RETURNING_NO_CLAIM"
                }
                | {
                    "translatable_no_claim_count": coverage[
                        "TRANSLATABLE_PASSAGES_RETURNING_NO_CLAIM"
                    ]["count"]
                },
                "overall_448": {
                    k: v for k, v in overall_448.items() if k not in {"predicate_passage_presence"}
                },
                "overall_398": {
                    k: v for k, v in overall_398.items() if k not in {"predicate_passage_presence"}
                },
                "agent_regime_verdict": regime["verdict"],
                "agent_spread": spread,
                "requests_qa": {
                    k: v
                    for k, v in requests_qa.items()
                    if k
                    not in {
                        "duplicate_normalized_outcomes",
                        "outcome_anchor_failure_rows",
                        "high_split_risk_queue",
                    }
                },
                "describes_qa": {
                    k: v
                    for k, v in describes_qa.items()
                    if k
                    not in {
                        "exact_evidence_span_overlap",
                        "partial_span_overlap_likely_redundant",
                    }
                },
                "broad_predicate_qa": {k: v for k, v in broad_qa.items() if k != "assertions"},
                "canonical_target_qa": canonical_qa,
                "ontology_gap_qa": {k: v for k, v in ontology_qa.items() if k != "rows"},
                "duplicate_counts": duplicate_counts,
                "review_queue": report["review_queue"],
                "manifest": out.relative_to(ROOT).as_posix(),
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
