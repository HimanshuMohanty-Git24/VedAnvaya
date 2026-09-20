"""Regression tests for GAP-SAMAVEDA_MUSIC-002, closed by the Samaveda notation import.

Each block pins the thing that was WRONG rather than only the thing that is now right,
because several of these could be re-broken by a change that looks like a tidy-up:

*   The entry closed on a NEW measure. The old one -- ``MUSICALIZED_AS`` -- still reads 0 and
    is SUPPOSED to, so a later pass must not be able to "finish the job" by populating it.
*   Gate C found a defect. The failing run is an artifact on disk, and a test asserts it
    still records 39, so the finding cannot be erased by regenerating the passing run alone.
*   The import first shipped without two graph-wide contracts. Both are pinned here, because
    the importer's own readback reported success while both were missing.
*   Six product surfaces carried a sentence the notation makes false. The exact phrases are
    named so the stale claim cannot come back by a copy-paste.

Live tests are gated on ``VEDAGRAPH_LIVE_NEO4J`` and are reported by
``scripts/release_test_accounting.py`` under that gate, so a failure here cannot vanish from
a release report by being skipped.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
from typing import Any

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

_LIVE = pytest.mark.skipif(
    not os.environ.get("VEDAGRAPH_LIVE_NEO4J"),
    reason="set VEDAGRAPH_LIVE_NEO4J=1 to run against the local Neo4j instance",
)

PASS_DIR = PROJECT_ROOT / "data" / "staging" / "samaveda_music_002_final"
INTEGRATION = PROJECT_ROOT / "data" / "staging" / "integration"

NOTATED = 1136
WITHHELD = 708
SV_VERSES = 1844
EXHAUSTION_CLASS = "WITNESS_OCCURRENCE_CONSUMED_BY_A_COREFERENT_REPEAT"
TEXT_VERSION_ID = "WIKISOURCE_SA.SV.KAU.ARCIKA_SASVARA"


def _driver() -> Any:
    from neo4j import GraphDatabase

    return GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "vedagraph_dev"))


def _scalar(query: str, **params: Any) -> Any:
    driver = _driver()
    try:
        with driver.session() as session:
            record = session.run(query, **params).single()
            return None if record is None else record[0]
    finally:
        driver.close()


def _rows(query: str, **params: Any) -> list[dict[str, Any]]:
    driver = _driver()
    try:
        with driver.session() as session:
            return [record.data() for record in session.run(query, **params)]
    finally:
        driver.close()


def _load(path: pathlib.Path) -> Any:
    if not path.exists():
        pytest.skip(f"{path.relative_to(PROJECT_ROOT)} not present in this checkout")
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# The three gates, and the owner clarification that made all three load-bearing
# ---------------------------------------------------------------------------


def test_all_three_gates_pass_because_the_owner_said_all_three_count() -> None:
    """Not Gate A alone. Section 42 settled that, so a Gate-A-only reading must fail here."""
    gate_a = _load(PASS_DIR / "gate_a.json")
    gate_b = _load(INTEGRATION / "samaveda_music_gate_b.json")
    gate_c = _load(INTEGRATION / "samaveda_music_gate_c.json")

    assert gate_a["ok"] is True
    assert gate_a["fatal"] == []
    assert all(check["complete"] for check in gate_a["checks"]), (
        "a check below full coverage is a failure of the VALIDATOR, and a validator that "
        "silently skips is worse than none"
    )

    assert gate_b["verdict"] == "PASS"
    assert gate_b["summary"]["total_failures"] == 0
    assert gate_b["summary"]["checks_below_full_coverage"] == []
    assert {check["section"] for check in gate_b["checks"]} == {
        "classification",
        "population",
        "source",
        "relation",
    }, "Gate B is defined as four sections by wave3_eligibility.json; all four must be covered"

    assert gate_c["verdict"] == "SURVIVED"
    assert gate_c["summary"]["total_defects"] == 0
    assert gate_c["summary"]["checks_below_full_coverage"] == []


def test_gate_c_negative_control_is_what_makes_its_pass_evidence() -> None:
    """A fold loose enough to match anything would score 1,136/1,136 and prove nothing.

    Pinned as a GAP rather than as two numbers: the aligned comparison must succeed on every
    row and the one-verse-shifted comparison must succeed on none. Either half alone is
    worthless.
    """
    gate_c = _load(INTEGRATION / "samaveda_music_gate_c.json")
    control = next(
        check
        for check in gate_c["checks"]
        if check["name"] == "independent.the_comparison_has_discriminating_power"
    )
    observed = control["observed"]
    assert observed["aligned_agreement_invariant"] == NOTATED
    assert observed["shifted_by_one_agreement_invariant"] == 0
    assert observed["shifted_by_one_agreement_positional"] == 0


def test_gate_c_refuses_to_read_the_artifacts_own_derivation() -> None:
    """Independence is the whole point of Gate C, and it is asserted rather than assumed."""
    gate_c = _load(INTEGRATION / "samaveda_music_gate_c.json")
    refused = gate_c["independence"]["fields_this_gate_refuses_to_read"]
    assert "payload.tone_stripped_text" in refused
    assert "the graph's stored SV primary text" in refused
    source = pathlib.Path(PROJECT_ROOT / "scripts" / "samaveda_music_gate_c.py").read_text(
        encoding="utf-8"
    )
    # The string appears only in the prose that explains the refusal, never in a read.
    assert 'payload["tone_stripped_text"]' not in source
    assert "'tone_stripped_text'" not in source


def test_gate_c_adversarial_sample_is_declared_and_was_not_redrawn() -> None:
    """A sample chosen after seeing which rows fail is not a sample."""
    gate_c = _load(INTEGRATION / "samaveda_music_gate_c.json")
    check = next(
        c
        for c in gate_c["checks"]
        if c["name"] == "adversarial_sample_40.every_check_re_applied_row_by_row"
    )
    sample = check["observed"]["sample"]
    assert sample["seed"] == 20260918
    assert sample["size"] == sample["declared_size"] == 40
    assert check["observed"]["defects"] == 0
    # The artifact's own 40-row sample is kept and labelled, not swapped out for this one.
    prior = check["observed"]["pre_existing_sample_in_the_artifact"]
    assert prior["population"] == "GANA_RENDERING"
    assert prior["kept_not_replaced"] is True


def test_the_failing_gate_c_run_is_preserved_with_its_defect_count() -> None:
    """The finding must survive the fix.

    If a later pass regenerates only the passing run, this test is what notices that the
    39-defect record has gone. A gate that found something and then lost the evidence is
    indistinguishable from a gate that never ran.
    """
    first = _load(PASS_DIR / "gate_c_run1.json")
    assert first["verdict"] == "DEFECT_FOUND"
    assert first["summary"]["total_defects"] == 39
    check = next(
        c
        for c in first["checks"]
        if c["name"] == "independent.the_withheld_reason_survives_its_own_falsification"
    )
    assert check["failures"] == 39
    assert check["observed"]["misattributed_by_stated_class"] == {
        "NEAR_LINE_EXISTS_WITNESS_DISAGREEMENT": 34,
        "NO_NEAR_LINE_PROBABLE_ABSENCE": 5,
    }


# ---------------------------------------------------------------------------
# The correction: 39 reasons, 0 rows moved, 0 notation invented
# ---------------------------------------------------------------------------


def test_the_overlay_changes_a_reason_and_never_a_disposition() -> None:
    """The one thing the owner decision forbids outright is inventing notation.

    All 39 corrected verses stay withheld. Their text IS released on a twin, which is
    exactly why copying the twin's marks would be tempting and wrong: marks belong to the
    coordinate the source printed them at.
    """
    overlay = _load(PASS_DIR / "withheld_reason_overlay.json")
    assert overlay["counts"]["corrected"] == 39
    assert overlay["what_did_not_change"]["rows_moving_from_withheld_to_released"] == 0
    assert overlay["what_did_not_change"]["notation_values_invented"] == 0
    assert overlay["what_did_not_change"]["released_population"] == NOTATED
    assert overlay["what_did_not_change"]["withheld_population"] == WITHHELD
    for correction in overlay["corrections"]:
        assert correction["disposition"] == "WITHHELD"
        assert correction["disposition_unchanged"] is True
        assert correction["corrected_class"] == EXHAUSTION_CLASS
        assert correction["original_class"] != correction["corrected_class"]
        assert correction["original_reason_verbatim"], (
            "the original reason must be preserved; a correction that erases what it "
            "replaced is indistinguishable from editing the record to make it green"
        )
        assert correction["released_coreferent_twins"]


def test_the_sealed_staging_artifact_was_not_edited_in_place() -> None:
    """Gate A verifies twelve checksums, so an in-place edit would have broken it.

    Pinned because the tempting fix -- rewriting the 39 reasons in rejected.jsonl -- would
    have been unreproducible: the generator that built the artifact is not in this
    repository.
    """
    overlay = _load(PASS_DIR / "withheld_reason_overlay.json")
    assert overlay["seals_respected"]["staging_directory_untouched"] is True
    assert overlay["seals_respected"]["manifest_checksums_still_valid"] is True
    gate_a = _load(PASS_DIR / "gate_a.json")
    checksums = next(
        check for check in gate_a["checks"] if check["name"] == "manifest.file_checksums"
    )
    assert checksums["evaluated"] == checksums["eligible"] == 12
    assert checksums["failures"] == []


# ---------------------------------------------------------------------------
# The graph, live
# ---------------------------------------------------------------------------


@_LIVE
def test_live_every_samavedic_verse_carries_a_typed_notation_disposition() -> None:
    """1,136 present and 708 withheld, with nothing untyped.

    The untyped count is the load-bearing assertion. A layer that publishes only its
    positive rows lets a reader infer a zero the data never stated, which is the defect this
    campaign has recorded more than once.
    """
    assert (
        _scalar(
            "MATCH (m:Mantra {veda:'SV', samavedic_notation_state:'SOURCE_EXPLICIT_PRESENT'}) "
            "RETURN count(m)"
        )
        == NOTATED
    )
    assert (
        _scalar(
            "MATCH (m:Mantra {veda:'SV', samavedic_notation_state:'WITHHELD'}) RETURN count(m)"
        )
        == WITHHELD
    )
    assert (
        _scalar(
            "MATCH (m:Mantra {veda:'SV'}) WHERE m.samavedic_notation_state IS NULL "
            "RETURN count(m)"
        )
        == 0
    )
    assert _scalar("MATCH (m:Mantra {veda:'SV'}) RETURN count(m)") == SV_VERSES


@_LIVE
def test_live_every_withheld_verse_names_a_class_from_the_declared_three() -> None:
    """An untyped absence is a defect; so is a fourth class arriving unannounced."""
    rows = _rows(
        "MATCH (m:Mantra {veda:'SV', samavedic_notation_state:'WITHHELD'}) "
        "RETURN m.samavedic_notation_withheld_class AS cls, count(m) AS n ORDER BY cls"
    )
    assert {row["cls"] for row in rows} == {
        "NEAR_LINE_EXISTS_WITNESS_DISAGREEMENT",
        "NO_NEAR_LINE_PROBABLE_ABSENCE",
        EXHAUSTION_CLASS,
    }
    assert {row["cls"]: row["n"] for row in rows}[EXHAUSTION_CLASS] == 39
    assert sum(row["n"] for row in rows) == WITHHELD
    assert (
        _scalar(
            "MATCH (m:Mantra {veda:'SV', samavedic_notation_state:'WITHHELD'}) "
            "WHERE m.samavedic_notation_withheld_reason IS NULL RETURN count(m)"
        )
        == 0
    )


@_LIVE
def test_live_notation_never_reaches_a_verse_that_was_withheld() -> None:
    """The withheld are withheld in the graph too, not merely in the staging file."""
    assert (
        _scalar(
            "MATCH (m:Mantra {veda:'SV', samavedic_notation_state:'WITHHELD'})"
            "-[:HAS_TEXT_VERSION]->(t:TextVersion {text_version_id:$tv}) RETURN count(t)",
            tv=TEXT_VERSION_ID,
        )
        == 0
    )
    assert (
        _scalar(
            "MATCH (:Mantra {veda:'SV'})-[:HAS_TEXT_VERSION]->"
            "(t:TextVersion {text_version_id:$tv}) RETURN count(t)",
            tv=TEXT_VERSION_ID,
        )
        == NOTATED
    )
    assert (
        _scalar(
            "MATCH (t:TextVersion {text_version_id:$tv}) "
            "WHERE t.notation_tone_mark_count IS NULL OR t.notation_tone_mark_count < 1 "
            "RETURN count(t)",
            tv=TEXT_VERSION_ID,
        )
        == 0
    ), "a source-explicit notation row with no mark would be a claim with nothing behind it"


@_LIVE
def test_live_the_marks_are_recorded_and_never_interpreted_into_pitch() -> None:
    """A refusal, not a gap: no decipherment authority for this school is held."""
    assert (
        _scalar(
            "MATCH (t:TextVersion {text_version_id:$tv}) "
            "WHERE t.notation_is_interpreted_into_pitch = true RETURN count(t)",
            tv=TEXT_VERSION_ID,
        )
        == 0
    )
    keys = _scalar(
        "MATCH (t:TextVersion {text_version_id:$tv}) UNWIND keys(t) AS k "
        "RETURN collect(DISTINCT k)",
        tv=TEXT_VERSION_ID,
    )
    # notation_is_interpreted_into_pitch is the property that RECORDS the refusal, so it
    # is the one key allowed to name a pitch. A first version of this scan flagged the
    # guard as the thing it guards against.
    records_the_refusal = {"notation_is_interpreted_into_pitch"}
    forbidden = [
        key
        for key in keys
        if key not in records_the_refusal
        and any(
            word in key.lower()
            for word in ("pitch", "hertz", "frequency", "udatta", "svarita", "anudatta")
        )
    ]
    assert forbidden == []


@_LIVE
def test_live_section_41_is_untouched_by_this_closure() -> None:
    """The old measure still reads 0, and a later pass must not "finish" it.

    GAP-SAMAVEDA_MUSIC-002's own closure_test asked for MUSICALIZED_AS to be non-zero.
    Owner decision G places the object side outside Product V1 and forbids minting a node or
    an edge to satisfy a count, so 0 is the correct value and not an unfinished one.
    """
    assert _scalar("MATCH ()-[r:MUSICALIZED_AS]->() RETURN count(r)") == 0
    assert (
        _scalar(
            "CALL db.labels() YIELD label "
            "WHERE label =~ '(?i).*(saman|gana|stobha|melod).*' RETURN count(label)"
        )
        == 0
    )
    assert (
        _scalar(
            "MATCH (n) WHERE n.work_id STARTS WITH 'VG:WORK:SV:KAU:GANA' "
            "OR n.canonical_key STARTS WITH 'VG:SV:KAU:GANA' RETURN count(n)"
        )
        == 0
    )


@_LIVE
def test_live_the_new_layer_keeps_the_two_graph_wide_contracts_it_first_missed() -> None:
    """Pinned because the import's own readback reported success while both were missing.

    ``scripts/graph_quality_scorecard.py`` caught them, at exactly 1,136 on three integrity
    gates. An importer's own success report is not evidence.
    """
    from vedagraph.domain.tiers import grade_edge

    assert _scalar("MATCH (t:TextVersion) WHERE NOT t:Internal RETURN count(t)") == 0, (
        "TextVersion is in INTERNAL_LABELS; without the marker these nodes count as "
        "PRODUCT nodes and read as leaked internals with no readable label"
    )
    assert (
        _scalar(
            "MATCH ()-[r:HAS_TEXT_VERSION]->() WHERE r.quality_tier IS NULL RETURN count(r)"
        )
        == 0
    )
    contracted = grade_edge("HAS_TEXT_VERSION", {}).as_edge_properties()
    stored = _rows(
        "MATCH (:Mantra {veda:'SV'})-[r:HAS_TEXT_VERSION]->"
        "(:TextVersion {text_version_id:$tv}) "
        "RETURN DISTINCT r.quality_tier AS quality_tier, r.knowledge_layer AS knowledge_layer, "
        "r.attribution_precision AS attribution_precision, r.evidence_basis AS evidence_basis, "
        "r.grade_basis AS grade_basis",
        tv=TEXT_VERSION_ID,
    )
    assert len(stored) == 1, "one layer, one grade; more than one means the axis drifted"
    assert stored[0] == contracted, (
        "the grade must come from the single contract in vedagraph.domain.tiers, not from a "
        "value copied off a neighbouring edge"
    )


@_LIVE
def test_live_the_primary_text_is_still_the_primary_text() -> None:
    """The notation is offered BESIDE the text, never as it.

    The witness is a community transcription pinned to one revision. Promoting it would make
    a community archive canonical for 1,136 verses.
    """
    assert (
        _scalar(
            "MATCH (:Mantra {veda:'SV'})-[:HAS_TEXT_VERSION]->"
            "(t:TextVersion {text_role:'PRIMARY_TEXT'}) RETURN count(t)"
        )
        == SV_VERSES
    )
    assert (
        _scalar(
            "MATCH (t:TextVersion {text_version_id:$tv}) WHERE t.text_role <> 'PARALLEL_TEXT' "
            "RETURN count(t)",
            tv=TEXT_VERSION_ID,
        )
        == 0
    )
    assert (
        _scalar(
            "MATCH (t:TextVersion {text_version_id:$tv}) "
            "WHERE t.notation_quality_class <> 'COMMUNITY_ARCHIVE' RETURN count(t)",
            tv=TEXT_VERSION_ID,
        )
        == 0
    )


@_LIVE
def test_live_the_import_kept_its_promise_and_the_readback_agrees() -> None:
    """actual == promised, and the hash comparison is per row rather than a total.

    A total can survive two rows swapping their text; a per-row hash cannot.
    """
    receipt = _load(PASS_DIR / "import_receipt.json")
    assert receipt["promise_kept"] is True
    assert receipt["disagreements"] == {}
    readback = _load(PASS_DIR / "readback.json")
    assert readback["content_hash_mismatches"] == 0
    assert readback["distinct_text_ids_among_them"] == NOTATED, (
        "text_id is the unique key and text_version_id is NOT: 58,786 nodes share twelve of "
        "them, so a SET keyed on the wrong one writes thousands of nodes"
    )
    repair = _load(PASS_DIR / "repair_receipt.json")
    assert repair["creates_nothing"]["nodes"] is True
    assert repair["creates_nothing"]["relationships"] is True
    assert all(value == 0 for value in repair["contracts_closed"].values())


# ---------------------------------------------------------------------------
# Product surfaces and the registry. The two live API assertions live in
# tests/api/test_samaveda_notation_surface.py, where the live_client fixture is.
# ---------------------------------------------------------------------------


def test_no_product_surface_still_says_the_notation_does_not_exist() -> None:
    """Six surfaces carried a sentence the notation makes false.

    Named by exact phrase rather than by file, because the way this claim comes back is a
    copy-paste into a seventh surface.
    """
    stale = (
        "No melodic layer of any kind exists",
        "Nothing here shows, notates or infers melody",
        "Nothing here shows or infers melody",
        "the melodic\n                    apparatus are not held",
        "complete musical information are not",
    )
    searched = [
        PROJECT_ROOT / "src" / "vedagraph",
        PROJECT_ROOT / "frontend" / "src",
    ]
    hits: list[str] = []
    for root in searched:
        for path in root.rglob("*"):
            if path.suffix not in {".py", ".ts", ".tsx", ".md"} or not path.is_file():
                continue
            if "node_modules" in path.parts:
                continue
            body = path.read_text(encoding="utf-8", errors="ignore")
            hits.extend(
                f"{path.relative_to(PROJECT_ROOT)}: {phrase!r}"
                for phrase in stale
                if phrase in body
            )
    assert hits == [], f"stale Samaveda-music claims still served: {hits}"


def test_the_registry_entry_closed_on_a_measure_that_is_not_musicalized_as() -> None:
    """And the superseded clauses of its own written test are recorded as failing.

    A closure that quietly rewrites the test it was measured against is the failure mode
    this file exists to catch. Two of the three clauses do not hold; both are marked
    superseded and both name the decision that supersedes them.
    """
    registry = _load(PROJECT_ROOT / "data" / "gap_registry.json")
    entry = next(g for g in registry["gaps"] if g["gap_id"] == "GAP-SAMAVEDA_MUSIC-002")
    assert entry["status"] == "CLOSED_SOURCE_ACQUIRED"
    assert "MUSICALIZED_AS" not in entry["closure_measure"]
    assert entry["closure_measured_value"] == 0
    assert entry["closure_reaudit"], "a changed measure requires a stated basis"

    accounting = entry["closure_test_as_written_measured"]
    assert accounting["clauses_passing_as_written"] == 1
    assert accounting["clauses_superseded_by_a_recorded_owner_decision"] == 2
    for clause in accounting["clauses"]:
        if not clause["passes"]:
            assert clause["superseded_by"], (
                "a failing clause must name the recorded decision that supersedes it, or the "
                "closure is resting on a test it silently redefined"
            )
            assert "OWNER_DECISIONS.md" in clause["superseded_by"]


def test_the_registry_has_no_implementation_fixable_row_left() -> None:
    """The number this whole pass existed to move."""
    audit = _load(PROJECT_ROOT / "data" / "staging" / "wave4" / "registry_closure_audit.json")
    assert audit["counts"].get("STILL_IMPLEMENTATION_FIXABLE", 0) == 0
    assert audit["counts"].get("BLOCKED_OWNER_DECISION_REQUIRED", 0) == 0
    assert audit["counts"].get("BLOCKED_EVIDENCE_INCOMPLETE", 0) == 0
    assert audit["not_terminated"] == []
    assert audit["measurement_disagreements"] == []
    assert audit["registry_status_disagreements"] == []
