"""Stage GAP-SAMAVEDA_MUSIC-003 clause 1 and GAP-ENTITY_COVERAGE-004 from Agent A's evidence.

Agent A's artifacts were verified independently before being staged -- an importer's own
success report is not evidence, and this project has recorded three Wave 3 attempts that
printed a clean per-group table while over-writing the data.

VERIFIED HERE, NOT TAKEN ON REPORT:

*   Both JSONL files re-hash to the sha256 Agent A declared.
*   The running numbers span 1..1875 with 1,844 distinct values and 0 collisions, so they
    are NOT ``enumerate()`` over our own ordering -- an enumerate would be exactly 1..1844
    contiguous.
*   All 31 gaps in the sequence are attributable to a recorded source defect in
    ``data/canonical/samaveda_arcika_v1/qa_issues.jsonl``: 31 distinct
    ``source_running_number`` values across 39 rows over four check_ids --
    STRUCTURAL_AMBIGUITY 21, REFERENT_UNRESOLVED 9, SOURCE_MARKER_ANOMALY 2,
    SOURCE_NOT_PRINTED 2 -- and ``gaps - recorded == {}``. Agent A attributed all 39 rows to
    REFERENT_UNRESOLVED alone, which is a mislabel of the check_id; the conclusion it drew
    is exactly right and is what I re-measured.
*   The expectation rows carry ``expected_source`` on EXACTLY the 161 class-A entities, and
    ``externally_expected`` on exactly the same set. 0 rows carry a source outside class A
    and 0 rows have an empty justification quote. 223 rows keep ``expected_source`` null
    deliberately.

WHAT IS NOT CLAIMED. GAP-SAMAVEDA_MUSIC-003 has a second clause -- re-deriving all 495
``MUSICALIZED_AS`` edges from the graph alone -- and it is not closable here. The edge type
does not exist, and neither does its object end: 0 nodes carry a gana work id or a gana
canonical key, and the four gana Works are ``PROPOSED_FOR_LEAD_ADJUDICATION`` behind
``OWNER_DECISION_E_AUDIO_GATE``. Clause 1 is landed and clause 2 is reported, not absorbed.
"""

from __future__ import annotations

import collections
import hashlib
import json
import pathlib
import sys
from typing import Any

import _q  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]  # release_blocker_r5 -> staging -> data -> VedaGraph
CANONICAL_SV = ROOT / "data" / "canonical" / "samaveda_arcika_v1"
CONTRACT = "VG:R5_CLOSURE:V1"

RUNNING = HERE / "agentA_samaveda_music" / "running_samhita_number.jsonl"
EXPECT = HERE / "agentA_expected_source" / "expectation_origin_rows.jsonl"
RUNNING_SHA = "d7c42150008e549b5284270047b2e1cdbee542c43ba2067cb71cba5dd9a9e214"
EXPECT_SHA = "1a2b2f006d08fdd13fdacefe3952810625c2b4222f773f7b9ef5e896c3ff6ae7"


def _rows(path: pathlib.Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def go(session) -> dict[str, Any]:
    out: dict[str, Any] = {}

    # ---------------- GAP-SAMAVEDA_MUSIC-003 ----------------
    assert hashlib.sha256(RUNNING.read_bytes()).hexdigest() == RUNNING_SHA, "running number sha mismatch"
    running = _rows(RUNNING)
    numbers = [r["running_samhita_number"] for r in running]
    gaps = sorted(set(range(min(numbers), max(numbers) + 1)) - set(numbers))

    qa = _rows(CANONICAL_SV / "qa_issues.jsonl")
    recorded: set[int] = set()
    by_check: collections.Counter[str] = collections.Counter()
    for issue in qa:
        by_check[issue["check_id"]] += 1
        value = (issue.get("details") or {}).get("source_running_number")
        if isinstance(value, int):
            recorded.add(value)

    live_sv = {
        r["key"]
        for r in _q.rows(session, "MATCH (m:Mantra {veda:'SV'}) RETURN m.canonical_key AS key")
    }
    staged_keys = {r["canonical_key"] for r in running}

    sv_updates = [
        {
            "canonical_key": r["canonical_key"],
            "properties": {
                "running_samhita_number": r["running_samhita_number"],
                "running_samhita_number_source_locator": r["source_locator_verbatim"],
                "running_samhita_number_source_artifact": r["source_artifact"],
                "running_samhita_number_join_method": r["join_method"],
                "running_samhita_number_is_deterministic": r["join_is_deterministic"],
                "running_samhita_number_contract": "VG:SV_RUNNING_SAMHITA_NUMBER:V1",
                "running_samhita_number_corroborated_by_second_witness": r[
                    "corroborated_by_second_source_gana_page"
                ],
                "running_samhita_number_sequence_note": (
                    "The number is the source's own printed running number over the whole "
                    "Samhita, spanning 1..1875 for 1,844 verses. It is NOT an index into this "
                    "corpus: the 31 absent numbers are verses the source prints and this "
                    "release withholds a canonical key for, each recorded in qa_issues.jsonl."
                ),
                "r5_contract": CONTRACT,
            },
        }
        for r in running
    ]

    out["samaveda_music_003"] = {
        "gap_id": "GAP-SAMAVEDA_MUSIC-003",
        "clause_1": {
            "requirement": "Every Samavedic mantra exposes its running Samhita number.",
            "before": {"sv_mantras_with_a_running_number": 0, "of": 1844},
            "after": {"sv_mantras_with_a_running_number": len(sv_updates), "of": len(live_sv)},
            "closes": len(sv_updates) == len(live_sv) == 1844,
        },
        "clause_2": {
            "requirement": (
                "Re-deriving the MUSICALIZED_AS edges from the graph alone reproduces all 495."
            ),
            "closes": False,
            "why_not": (
                "MUSICALIZED_AS carries 0 edges and the relationship type does not exist, and "
                "neither does its object end: 0 nodes carry a gana work id or a gana canonical "
                "key, and the only SV Work is VG:WORK:SV:KAU. The four gana Works are "
                "PROPOSED_FOR_LEAD_ADJUDICATION behind OWNER_DECISION_E_AUDIO_GATE, which is "
                "the same gate GAP-SAMAVEDA_MUSIC-002 is recorded against. The predicate is "
                "also glossed Passage->Passage RV->SV and would need widening before it could "
                "honestly carry an SV->gana edge."
            ),
            "is_implementation_fixable": False,
            "blocked_on": "OWNER_DECISION_E_AUDIO_GATE + the gana Work adjudication",
        },
        "not_fake_proof": {
            "value_range": [min(numbers), max(numbers)],
            "distinct": len(set(numbers)),
            "collisions": len(numbers) - len(set(numbers)),
            "would_be_if_enumerate": "exactly 1..1844 contiguous",
            "is_enumerate": sorted(numbers) == list(range(1, 1845)),
            "gap_count": len(gaps),
            "gaps": gaps,
            "gaps_all_attributable_to_a_recorded_source_defect": not (set(gaps) - recorded),
            "qa_issue_check_id_distribution": dict(by_check),
            "distinct_source_running_numbers_recorded_in_qa_issues": len(recorded),
            "independent_second_witness_control": (
                "On the 332 verses where the gana pages independently print an arcika running "
                "number, the source number agrees 332/332 and an enumerate() over our own "
                "ordering agrees 256/332, its offset climbing 0->9->12->21->24->30->31 and "
                "ending exactly at the 31-verse deficit. That is the control that makes this a "
                "published number rather than a restatement of our own array order."
            ),
        },
        "staged_keys_equal_live_sv_keys": staged_keys == live_sv,
        "registry_source_dependency_correction": {
            "was": "NONE. The number is already captured in the staging artifact.",
            "is": (
                "NONE. The number is captured in the CANONICAL artifact -- "
                "data/canonical/samaveda_arcika_v1/citations.jsonl and text_versions.jsonl, "
                "1,844 of 1,844 agreeing across the two files. data/staging/samaveda_music/ "
                "holds a running number for only 332 verses, and holds it as the GANA source's "
                "number, which is a different series."
            ),
        },
        "promised": {"mantras_updated": len(sv_updates), "nodes_created": 0, "relationships_created": 0},
    }
    out["samaveda_music_003"]["node_updates"] = sv_updates

    # ---------------- GAP-ENTITY_COVERAGE-004 ----------------
    assert hashlib.sha256(EXPECT.read_bytes()).hexdigest() == EXPECT_SHA, "expectation sha mismatch"
    expect = _rows(EXPECT)
    dist = collections.Counter(r["expectation_origin"] for r in expect)
    with_source = [r for r in expect if r.get("expected_source")]
    externally = [r for r in expect if r.get("externally_expected")]
    class_a = [r for r in expect if r["expectation_origin"] == "EXPLICITLY_EXPECTED_BY_A_SOURCE"]

    live_entities = {
        r["key"]
        for r in _q.rows(session, "MATCH (n:DomainEntity) RETURN n.entity_key AS key")
    }

    entity_updates = [
        {
            "entity_key": r["entity_key"],
            "properties": {
                "expectation_origin": r["expectation_origin"],
                "expectation_origin_contract": "VG:ENTITY_EXPECTATION_ORIGIN:V1",
                "expectation_origin_evidence": r["expectation_origin_evidence"],
                "expectation_origin_evidence_quote": r["expectation_origin_evidence_quote"],
                "expected_source": r["expected_source"],
                "externally_expected": bool(r["externally_expected"]),
                "expectation_internal_origin_file": r["internal_origin_file"],
                "expectation_internal_origin_kind": r["internal_origin_kind"],
                "expected_source_sense_review": (
                    "HEADWORD_LEXICAL_MATCH_SENSE_NOT_HUMAN_REVIEWED"
                    if r["expected_source"]
                    else None
                ),
                "r5_contract": CONTRACT,
            },
        }
        for r in expect
    ]

    out["entity_coverage_004"] = {
        "gap_id": "GAP-ENTITY_COVERAGE-004",
        "class_distribution": dict(dist),
        "expected_source_populated": len(with_source),
        "expected_source_deliberately_null": len(expect) - len(with_source),
        "external_source": {
            "work": "Macdonell & Keith, Vedic Index of Names and Subjects",
            "publisher": "London: John Murray",
            "year": 1912,
            "rights": "public domain by age; the archive.org scan text is CC0 1.0",
            "machine_readable_as": "Cologne CDSD dictionary id 'vei', TEI-P5",
            "entries": 3834,
            "distinct_headwords": 3704,
            "headwords_whose_body_names_a_samhita": 2532,
            "licence_caveat": (
                "The Cologne repository declares no licence for 'vei' and the XML header reads "
                "'Copyright Universitat Koln 2013'. The lawful route is the CC0 archive.org "
                "full text or a C-SALT enquiry. Recorded rather than glossed."
            ),
            "scope_caveat": (
                "VEI's editorial scope excludes mythology and abstracta -- agni, anna and amrta "
                "are absent -- so the external denominator is valid for 11 of our 22 entity "
                "labels (Animal, Place, River, Metal, Weapon, Tribe, Crop at 100%, Plant 95%, "
                "Substance 91%, Offering 81%, Object 78%) and UNDEFINED for Ritual 18%, "
                "Action 15% and Quality 0%. A single coverage ratio over all 384 would hide that."
            ),
        },
        "closure_test_clause_1": {
            "requirement": "Entity nodes carry an expected_source.",
            "measure_as_written": "MATCH (n:DomainEntity) WHERE n.expected_source IS NULL RETURN count(n) -> 0",
            "cannot_be_satisfied_as_written": True,
            "why": (
                "Reaching 0 means putting a source on all 384, including 223 rows for which no "
                "external source names the entity. That is the decorative field completion the "
                "brief forbids by name: a row that is an internal product expectation must not "
                "pretend a scholarly source predicted it. 223 rows keep expected_source null "
                "ON PURPOSE, and a later closure that populates all 384 should be rejected on "
                "sight."
            ),
            "restated_measure": (
                "unsupported expected-source assertions = 0, AND every entity carries a typed "
                "expectation_origin"
            ),
            "unsupported_expected_source_assertions": len(
                [r for r in with_source if r["expectation_origin"] != "EXPLICITLY_EXPECTED_BY_A_SOURCE"]
            ),
            "entities_without_a_typed_origin": len(expect) - sum(dist.values()),
        },
        "falsifier": {
            "expected_source_set_equals_class_A_set": {r["entity_key"] for r in with_source}
            == {r["entity_key"] for r in class_a},
            "externally_expected_set_equals_class_A_set": {r["entity_key"] for r in externally}
            == {r["entity_key"] for r in class_a},
            "rows_with_a_source_outside_class_A": len(
                [r for r in with_source if r["expectation_origin"] != "EXPLICITLY_EXPECTED_BY_A_SOURCE"]
            ),
            "rows_with_an_empty_justification": len(
                [r for r in expect if not (r.get("expectation_origin_evidence_quote") or "").strip()]
            ),
            "staged_keys_equal_live_entity_keys": {r["entity_key"] for r in expect} == live_entities,
            "class_E_unsupported_legacy": dist.get("UNSUPPORTED_LEGACY_EXPECTATION", 0),
        },
        "prior_claim_corrected": {
            "claim": (
                "release_blocker_r4/agent_b_receipt.json: '229 from concept registries with NO "
                "external source citation and 155 from ritual registries WITH "
                "existence_evidence_type'"
            ),
            "origin_split_229_155": "CORRECT, reproduced independently from the files",
            "155_with_existence_evidence_type": (
                "WRONG by 73. 228 carry it -- the 155 ritual-origin plus 73 registry-origin "
                "rows re-measured by the ritual wave -- and 156 carry none."
            ),
            "229_with_no_external_citation": (
                "INVERTED. Across all 384, 375 have no external citation and only 9 do -- and "
                "all 9 are ritual-origin, i.e. inside the '155' and not the '229'."
            ),
        },
        "promised": {"nodes_updated": len(entity_updates), "nodes_created": 0, "relationships_created": 0},
    }
    out["entity_coverage_004"]["node_updates"] = entity_updates
    return out


if __name__ == "__main__":
    result = _q.run(go)
    (HERE / "staged_agentA_gaps.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
