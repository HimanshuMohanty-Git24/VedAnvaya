from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))

from author_semantic_luna_v2_payloads import FAMILIES, author_payload


def packet(text: str, *, mention: bool = True) -> dict[str, object]:
    mentions: list[dict[str, object]] = []
    if mention:
        mentions.append(
            {
                "entity_key": "VG:DEVATA:AGNIH",
                "entity_label": "agniḥ",
                "occurrence_count": 1,
                "token_keys": ["token-1"],
            }
        )
    return {
        "passage_key": "VG:RV:SAK:M01:S001:V001",
        "citation": "RV 1.1.1",
        "translation": {
            "translation_id": "translation-1",
            "text": text,
        },
        "mentions": mentions,
    }


def test_every_packet_gets_all_fourteen_checklist_families() -> None:
    _, trace = author_payload(packet("A quiet line."))
    assert trace["checklist_completed"] is True
    assert set(trace["families"]) == set(FAMILIES)
    assert len(FAMILIES) == 14


def test_no_claim_has_a_completed_checklist_and_reason() -> None:
    payload, trace = author_payload(packet("A quiet line.", mention=False))
    assert payload["assertions"] == []
    assert payload["no_claim_reasons"]
    assert trace["checklist_completed"] is True


def test_multiple_independent_families_can_coexist() -> None:
    payload, _ = author_payload(
        packet("O Agni, praise Agni and grant protection; the offering of Soma is poured.")
    )
    predicates = {row["predicate"] for row in payload["assertions"]}
    assert {
        "INVOKES",
        "PRAISES",
        "REQUESTS",
        "INVOLVES_RITUAL",
        "INVOLVES_OFFERING",
        "INVOLVES_SUBSTANCE",
    } <= predicates


def test_requests_and_invokes_are_distinct_relations() -> None:
    payload, _ = author_payload(packet("O Agni, come to us and grant protection."))
    assert {row["predicate"] for row in payload["assertions"]} >= {"INVOKES", "REQUESTS"}


def test_praises_is_not_a_factual_description() -> None:
    descriptive, _ = author_payload(packet("Agni is mighty and gives strength."))
    assert "DESCRIBES" in {row["predicate"] for row in descriptive["assertions"]}
    assert "PRAISES" not in {row["predicate"] for row in descriptive["assertions"]}


def test_ritual_offering_and_substance_are_separate() -> None:
    payload, _ = author_payload(packet("Soma is poured as an offering in the rite."))
    predicates = {row["predicate"] for row in payload["assertions"]}
    assert {"INVOLVES_RITUAL", "INVOLVES_OFFERING", "INVOLVES_SUBSTANCE"} <= predicates
    types = {row["entity_type"] for row in payload["entities"]}
    assert {"RITUAL", "OFFERING", "SUBSTANCE"} <= types


def test_semantic_candidate_and_canonical_entity_reuse() -> None:
    payload, _ = author_payload(packet("O Agni, grant protection."))
    canonical = [row for row in payload["assertions"] if row["predicate"] == "INVOKES"]
    assert canonical and canonical[0]["object_entity_key"] == "VG:DEVATA:AGNIH"
    candidate = [row for row in payload["assertions"] if row["predicate"] == "REQUESTS"]
    assert candidate and candidate[0]["object_local_id"]
    assert any(row["entity_type"] == "STATE" for row in payload["entities"])


def test_ontology_gap_is_preserved_for_human_role() -> None:
    payload, trace = author_payload(packet("The patron is renowned.", mention=False))
    assert payload["assertions"] == []
    assert payload["uncertainties"]
    assert trace["ontology_gaps"]


def test_sealed_run_records_no_unlock_and_comparison_order() -> None:
    root = Path("data/semantic/vedagraph-rigveda-semantic-luna-v2-120")
    seal = json.loads((root / "v2_output_seal.json").read_text(encoding="utf-8"))
    assert seal["comparison_sources_opened"] is False
    assert (
        json.loads((root / "semantic_run_manifest.json").read_text(encoding="utf-8"))[
            "unlocked_predicates"
        ]
        == []
    )
    source = Path("scripts/finalize_semantic_luna_v2.py").read_text(encoding="utf-8")
    assert source.index("v2_output_seal.json") < source.index("semantic_candidates.jsonl")
