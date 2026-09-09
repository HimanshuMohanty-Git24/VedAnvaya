"""Upstream correction registry: the fix, and the guard against a fix that never applied."""

from __future__ import annotations

import pathlib

import pytest

from vedagraph.graph.corrections import (
    CorrectionApplier,
    VerseNumberCorrection,
    corrected_translation_id,
    load_corrections,
    verify_corrections_applied,
)

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent


def _correction(**overrides: object) -> VerseNumberCorrection:
    base: dict[str, object] = {
        "correction_id": "TEST",
        "source_artifact_id": "ART",
        "source_revision_id": 1,
        "wrong_passage_key": "VG:RV:SAK:M01:S001:V001",
        "correct_passage_key": "VG:RV:SAK:M01:S001:V002",
        "text_prefix": "Second verse",
        "reason": "test",
    }
    base.update(overrides)
    return VerseNumberCorrection(**base)  # type: ignore[arg-type]


def _applier(correction: VerseNumberCorrection) -> CorrectionApplier:
    return CorrectionApplier(
        (correction,),
        {"uuid-1": correction.wrong_passage_key, "uuid-2": correction.correct_passage_key},
        {correction.wrong_passage_key: "uuid-1", correction.correct_passage_key: "uuid-2"},
    )


def test_registry_declares_both_known_wikisource_verse_number_defects() -> None:
    corrections = load_corrections(PROJECT_ROOT)
    ids = {c.correction_id for c in corrections}
    assert ids == {
        "WIKISOURCE_GRIFFITH_RV_1_91_18_PRINTED_AS_16",
        "WIKISOURCE_GRIFFITH_RV_5_44_14_PRINTED_AS_11",
    }
    for correction in corrections:
        assert correction.wrong_passage_key != correction.correct_passage_key
        assert correction.text_prefix
        assert correction.reason


def test_a_correction_matches_on_content_not_on_the_colliding_identifier() -> None:
    """The two rows share a translation_id, so only the text can tell them apart."""
    correction = _correction()
    applier = _applier(correction)

    first = {"passage_id": "uuid-1", "translation_id": "shared", "text": "First verse text"}
    second = {"passage_id": "uuid-1", "translation_id": "shared", "text": "Second verse text"}

    assert applier.apply(first) is first
    corrected = applier.apply(second)
    assert corrected["passage_id"] == "uuid-2"
    assert corrected["translation_id"] != "shared"
    assert corrected["upstream_correction_id"] == "TEST"


def test_correcting_a_row_de_collides_the_derived_translation_id() -> None:
    """The new id comes from the standard derivation, not from a de-collision suffix."""
    assert corrected_translation_id("uuid-2", "ART", 1) != corrected_translation_id(
        "uuid-1", "ART", 1
    )
    assert corrected_translation_id("uuid-2", "ART", 1) == corrected_translation_id(
        "uuid-2", "ART", 1
    )


def test_a_declared_correction_that_never_matched_a_row_is_an_error() -> None:
    """A registry entry that does nothing reads as though the data were fixed."""
    applier = _applier(_correction())
    applier.apply({"passage_id": "uuid-1", "translation_id": "x", "text": "Unrelated text"})
    with pytest.raises(ValueError, match="matched no corpus row"):
        verify_corrections_applied(applier)


def test_a_correction_pointing_at_a_missing_passage_fails_loudly() -> None:
    correction = _correction(correct_passage_key="VG:RV:SAK:M99:S999:V999")
    applier = CorrectionApplier(
        (correction,),
        {"uuid-1": correction.wrong_passage_key},
        {correction.wrong_passage_key: "uuid-1"},
    )
    with pytest.raises(ValueError, match="does not exist in the corpus"):
        applier.apply({"passage_id": "uuid-1", "translation_id": "x", "text": "Second verse"})


def test_every_corpus_translation_id_is_unique_once_corrections_are_applied() -> None:
    """The whole point: 17,283 corpus rows become 17,283 representable Translation nodes."""
    from vedagraph.graph.projection import build_correction_applier, iter_translation_nodes

    applier = build_correction_applier(PROJECT_ROOT)
    rows = list(iter_translation_nodes(PROJECT_ROOT, applier))
    verify_corrections_applied(applier)

    assert len(rows) == 17_283
    assert len({row["translation_id"] for row in rows}) == len(rows)


def test_the_corrected_rows_land_on_the_passages_that_had_no_translation() -> None:
    """Checked against the rows, not against the applier's own record of what it did."""
    from vedagraph.graph.projection import (
        _passage_key_maps,
        build_correction_applier,
        iter_translation_nodes,
    )

    key_by_id, _ = _passage_key_maps(PROJECT_ROOT)
    applier = build_correction_applier(PROJECT_ROOT)
    landed = {
        key_by_id[row["passage_id"]]: row["text"][:30]
        for row in iter_translation_nodes(PROJECT_ROOT, applier)
        if row["upstream_correction_id"]
    }
    assert set(landed) == {"VG:RV:SAK:M01:S091:V018", "VG:RV:SAK:M05:S044:V014"}
    assert landed["VG:RV:SAK:M01:S091:V018"].startswith("In thee be juicy")
    assert landed["VG:RV:SAK:M05:S044:V014"].startswith("The sacred hymns love him")


def test_qa_issues_project_for_every_veda_with_stable_unique_ids() -> None:
    from vedagraph.graph.projection import iter_qa_issue_nodes

    first = list(iter_qa_issue_nodes(PROJECT_ROOT))
    second = list(iter_qa_issue_nodes(PROJECT_ROOT))

    assert first == second, "QA issue ids must be content-derived and stable across runs"
    assert len({row["issue_id"] for row in first}) == len(first)
    by_veda = {
        veda: sum(1 for r in first if r["veda"] == veda) for veda in ("RV", "SV", "YV", "AV")
    }
    assert by_veda["AV"] == 9
    assert all(count > 0 for count in by_veda.values())
    assert {row["severity"] for row in first} <= {"INFO", "WARNING", "ERROR"}
