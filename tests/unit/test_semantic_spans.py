"""B02: boundary-safe evidence anchoring, and the recursive validation around it.

The audited defects are named individually rather than summarised, because "spans are
validated now" is exactly the kind of claim that stops being true without anyone noticing.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import pytest

from vedagraph.models.normalization import SemanticExtractionV3
from vedagraph.models.semantic import EvidencePacket
from vedagraph.semantic.evidence import (
    nested_entity_ids,
    payload_anchors,
    payload_objects,
    validate_evidence_anchors,
)
from vedagraph.semantic.heuristic_baseline import extract_packet
from vedagraph.semantic.spans import (
    AmbiguousAnchorError,
    MissingAnchorError,
    find_anchors,
    is_word_char,
    resolve_anchor,
    span_errors,
)

PILOT = Path("data/semantic/vedagraph-rigveda-semantic-luna-v3-508")
BASELINE_RUN_ID = "test-heuristic-baseline"

#: The audited substring anchors from RIGVEDA_SEMANTIC_508_ONTOLOGY_AUDIT.md. Every one of
#: these is a real Griffith string in which "man" or "men" occurs only inside another word.
KNOWN_BAD_HOSTS = ("manifested", "many", "Pavamana", "woman", "Aryaman")


@lru_cache(maxsize=1)
def pilot_packets() -> dict[str, EvidencePacket]:
    """Every 508-pilot packet, by citation. Read-only."""
    return {
        packet.citation: packet
        for path in sorted((PILOT / "batches").glob("batch_*/evidence.jsonl"))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
        for packet in [EvidencePacket.model_validate_json(line)]
    }


@lru_cache(maxsize=1)
def sealed_payloads() -> dict[str, SemanticExtractionV3]:
    """The sealed 508 payloads, by citation. Never rewritten by any test."""
    return {
        payload.mantra_id: payload
        for line in (PILOT / "v3_extractions.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
        for payload in [SemanticExtractionV3.model_validate_json(line)]
    }


# --- boundary matching ---------------------------------------------------------------


@pytest.mark.parametrize("host", KNOWN_BAD_HOSTS)
def test_man_does_not_match_inside_another_word(host: str) -> None:
    text = f"They have {host} in the hymn."
    assert find_anchors(text, "man", ignore_case=True) == []
    with pytest.raises(MissingAnchorError):
        resolve_anchor(text, "man", ignore_case=True)


def test_man_still_matches_when_it_is_actually_a_word() -> None:
    text = "The pious man, and many a woman, praise Aryaman."
    found = find_anchors(text, "man", ignore_case=True)
    assert len(found) == 1
    assert text[found[0].start : found[0].end] == "man"
    assert found[0].text == "man"


def test_boundaries_apply_only_where_the_anchor_has_a_word_edge() -> None:
    text = "the meath-drops flow"
    # A leading hyphen means no left boundary is required, so this is a legitimate anchor.
    assert [anchor.text for anchor in find_anchors(text, "-drops")] == ["-drops"]
    assert find_anchors(text, "drop") == []


def test_word_boundaries_are_unicode_aware() -> None:
    assert is_word_char("ṛ") and is_word_char("9") and is_word_char("_")
    # A combining mark continues a word, so an anchor may not stop in front of one.
    assert is_word_char("́")
    assert find_anchors("sómase pávate", "som", ignore_case=True) == []
    assert [anchor.text for anchor in find_anchors("agni and soma", "soma")] == ["soma"]


def test_case_insensitive_matching_keeps_offsets_into_the_original_text() -> None:
    text = "Men wash the Soma; men dress it."
    found = find_anchors(text, "men", ignore_case=True)
    assert [text[a.start : a.end] for a in found] == ["Men", "men"]
    assert [a.text for a in found] == ["Men", "men"]


# --- multiple occurrences ------------------------------------------------------------


def test_a_repeated_anchor_is_ambiguous_unless_an_occurrence_is_named() -> None:
    text = "The man calls, and the man is heard."
    with pytest.raises(AmbiguousAnchorError, match="occurs 2 times"):
        resolve_anchor(text, "man")
    assert resolve_anchor(text, "man", occurrence=1).start == 4
    assert resolve_anchor(text, "man", occurrence=2).start == 23
    with pytest.raises(MissingAnchorError, match="has 2 occurrences"):
        resolve_anchor(text, "man", occurrence=3)


# --- the span validator --------------------------------------------------------------


def test_span_validator_reports_offsets_text_and_both_boundaries() -> None:
    text = "have manifested light"
    assert span_errors(text, 5, 8) == ["span 5:8 ends inside a word: 'manifested '"]
    assert span_errors(text, 6, 21) == ["span 6:21 begins inside a word: 'have manifested light'"]
    assert span_errors(text, 0, 4) == []
    assert span_errors(text, 0, 999)[0].startswith("span 0:999 is outside")
    assert "not the claimed" in span_errors(text, 0, 4, claimed_text="hold")[0]


# --- the audited historical defects ---------------------------------------------------


def test_every_audited_substring_anchor_is_now_refused() -> None:
    """The fourteen sealed anchors the readiness audit found, re-checked one by one."""
    defects = json.loads(
        Path("docs/manifests/rigveda_semantic_readiness_audit.json").read_text(encoding="utf-8")
    )["anchor_defects"]
    assert len(defects) == 14
    by_key = {packet.passage_key: packet for packet in pilot_packets().values()}
    payloads = {
        packet.passage_key: sealed_payloads()[packet.citation] for packet in by_key.values()
    }
    for defect in defects:
        packet = by_key[defect["passage_id"]]
        translation = packet.translation
        assert translation is not None and translation.text is not None
        span = defect["span"]
        assert span_errors(translation.text, span["start"], span["end"]), (
            f"{packet.citation} span {span} should be refused"
        )
        # And the payload that carries it is refused as a whole, not just the span.
        assert validate_evidence_anchors(payloads[packet.passage_key], packet)


def test_the_repaired_baseline_produces_no_defective_span_on_those_mantras() -> None:
    defects = json.loads(
        Path("docs/manifests/rigveda_semantic_readiness_audit.json").read_text(encoding="utf-8")
    )["anchor_defects"]
    by_key = {packet.passage_key: packet for packet in pilot_packets().values()}
    for passage_id in sorted({item["passage_id"] for item in defects}):
        packet = by_key[passage_id]
        payload, _ = extract_packet(packet, run_id=BASELINE_RUN_ID)
        assert validate_evidence_anchors(payload, packet) == [], packet.citation


def test_the_repaired_baseline_is_clean_across_the_whole_pilot() -> None:
    for packet in pilot_packets().values():
        payload, _ = extract_packet(packet, run_id=BASELINE_RUN_ID)
        assert validate_evidence_anchors(payload, packet) == [], packet.citation


# --- recursive validation -------------------------------------------------------------


def test_gap_anchors_and_object_anchors_are_both_walked() -> None:
    packet = next(
        packet
        for packet in pilot_packets().values()
        if sealed_payloads()[packet.citation].ontology_gaps
    )
    payload = sealed_payloads()[packet.citation]
    owners = {label.split()[0] for label, _ in payload_anchors(payload)}
    assert {gap.candidate_id for gap in payload.ontology_gaps} <= owners
    assert len(payload_objects(payload)) == len(payload.assertions) + len(payload.ontology_gaps)


def test_a_gap_anchor_with_a_bad_span_fails_validation() -> None:
    packet = next(
        packet
        for packet in pilot_packets().values()
        if sealed_payloads()[packet.citation].ontology_gaps and packet.translation
    )
    payload = sealed_payloads()[packet.citation]
    row = payload.model_dump(mode="json")
    translation = packet.translation
    assert translation is not None and translation.text is not None
    row["ontology_gaps"][0]["evidence"][0]["translation_record_id"] = translation.translation_id
    row["ontology_gaps"][0]["evidence"][0]["translation_span"] = {"start": 1, "end": 3}
    errors = validate_evidence_anchors(SemanticExtractionV3.model_validate(row), packet)
    assert any("inside a word" in message for message in errors)


def test_nested_entity_references_must_be_supplied_by_the_packet() -> None:
    packet = next(
        packet
        for packet in pilot_packets().values()
        if any(
            item.object.canonical_entity_id
            for item in sealed_payloads()[packet.citation].assertions
        )
    )
    payload = sealed_payloads()[packet.citation]
    assert validate_evidence_anchors(payload, packet) == []
    row = payload.model_dump(mode="json")
    target = next(
        item for item in row["assertions"] if item["object"]["canonical_entity_id"] is not None
    )
    target["object"]["beneficiary_entity_id"] = "VG:DEVATA:NOT_IN_THIS_PACKET"
    errors = validate_evidence_anchors(SemanticExtractionV3.model_validate(row), packet)
    assert any("NOT_IN_THIS_PACKET" in message for message in errors)
    assert "VG:DEVATA:NOT_IN_THIS_PACKET" in nested_entity_ids(
        SemanticExtractionV3.model_validate(row).assertions[row["assertions"].index(target)].object
    )


def test_other_evidence_ids_must_be_supplied_lexical_mentions() -> None:
    packet = next(
        packet
        for packet in pilot_packets().values()
        if sealed_payloads()[packet.citation].assertions
    )
    row = sealed_payloads()[packet.citation].model_dump(mode="json")
    row["assertions"][0]["evidence"][0]["other_evidence_ids"] = ["LEXICAL_MENTION:VG:DEVATA:NOPE"]
    errors = validate_evidence_anchors(SemanticExtractionV3.model_validate(row), packet)
    assert any("not a supplied lexical mention" in message for message in errors)
