"""The RV dvipada verse spine: every coordinate in RV 1.65-1.70, and both boundaries.

``GAP-TRANSLATION-006``. Griffith's edition numbers each four-pada group as one verse where
ours numbers each hemistich, so his page prints 5 units against our 10 verses. The ingest
bound his unit index onto our verse number and 25 of the span's 31 rows shipped against the
wrong Sanskrit.

The tests are organised around the two ways a fix like this goes wrong:

*   **It does not fire.** So every one of the 31 coordinates is asserted by name, GOOD -> PASS,
    rather than trusting a count.
*   **It fires too widely.** So the historical mapping is asserted to FAIL, the hymns either
    side of the span are asserted untouched, and RV 9.7 -- which also has fewer units than
    verses and whose attachments are CORRECT -- is asserted not to qualify. A rule derived
    from the count alone would have moved eight correct rows there.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from vedagraph.build import looks_like_paired_verse_spine
from vedagraph.graph.corrections import (
    PAIRED_DVIPADA,
    CorrectionApplier,
    VerseSpineCorrection,
    load_spine_corrections,
    verify_corrections_applied,
)
from vedagraph.models.enums import AlignmentLevel, TranslationAlignment

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent
AUDIT = (
    PROJECT_ROOT / "data" / "staging" / "translation" / "rv_1_65_1_70_pre_fix_audit.json"
)

#: The span, and the shape the source prints for each hymn. Written out rather than derived,
#: because a fixture derived from the same measurement the code uses cannot disagree with it.
SPAN_SHAPE: dict[int, tuple[int, int]] = {
    65: (5, 10),
    66: (5, 10),
    67: (5, 10),
    68: (5, 10),
    69: (5, 10),
    70: (6, 11),
}

#: The historical wrong mapping: unit N filed as verse N. Every entry must FAIL.
HISTORICAL_WRONG_TARGET = {unit: unit for unit in range(1, 7)}


def _correction(sukta: int, units: int, verses: int) -> VerseSpineCorrection:
    return VerseSpineCorrection(
        correction_id=f"TEST_1_{sukta}",
        source_artifact_id="GRIFFITH.RV.1896.WIKISOURCE",
        source_revision_id=99,
        hymn_key=f"VG:RV:SAK:M01:S{sukta:03d}",
        spine=PAIRED_DVIPADA,
        source_unit_count=units,
        canonical_verse_count=verses,
        reason="test",
    )


# --------------------------------------------------------------------- the span rule -


@pytest.mark.parametrize(("sukta", "units", "verses"), [(s, *v) for s, v in SPAN_SHAPE.items()])
def test_every_unit_of_every_span_hymn_covers_the_right_pair(
    sukta: int, units: int, verses: int
) -> None:
    """GOOD -> PASS, for all 31 coordinates in the span rather than a sample."""
    correction = _correction(sukta, units, verses)
    key = correction.hymn_key
    for unit in range(1, units + 1):
        expected = [f"{key}:V{2 * unit - 1:03d}"]
        if 2 * unit <= verses:
            expected.append(f"{key}:V{2 * unit:03d}")
        assert list(correction.covers(unit)) == expected, f"unit {unit} of RV 1.{sukta}"


@pytest.mark.parametrize(("sukta", "units", "verses"), [(s, *v) for s, v in SPAN_SHAPE.items()])
def test_the_historical_mapping_fails(sukta: int, units: int, verses: int) -> None:
    """BAD -> FAIL. Unit N filed as verse N is the defect; it must not survive the rule.

    Asserted for every unit except the first, which is the one the old mapping got right by
    coincidence -- and saying so here is what stops a future reader concluding the old
    mapping was simply wrong everywhere.
    """
    correction = _correction(sukta, units, verses)
    key = correction.hymn_key
    for unit in range(1, units + 1):
        anchor = correction.covers(unit)[0]
        historical = f"{key}:V{HISTORICAL_WRONG_TARGET.get(unit, unit):03d}"
        if unit == 1:
            assert anchor == historical, "unit 1 was already on verse 1"
        else:
            assert anchor != historical, (
                f"unit {unit} of RV 1.{sukta} still resolves to the historical wrong "
                f"target {historical}"
            )


def test_the_odd_verse_of_rv_1_70_is_covered_alone() -> None:
    """11 verses against 6 units, and the source prints the last unit as one line.

    The registry warned that the mapping is not uniformly a doubling. It is not, and this is
    where: unit 6 covers verse 11 and nothing else.
    """
    correction = _correction(70, 6, 11)
    assert correction.covers(6) == ("VG:RV:SAK:M01:S070:V011",)
    assert correction.covers(5) == (
        "VG:RV:SAK:M01:S070:V009",
        "VG:RV:SAK:M01:S070:V010",
    )


def test_a_span_is_contiguous_and_exhausts_the_hymn() -> None:
    """Every verse is covered exactly once, or the spine rule has a hole or an overlap."""
    for sukta, (units, verses) in SPAN_SHAPE.items():
        correction = _correction(sukta, units, verses)
        covered = [k for unit in range(1, units + 1) for k in correction.covers(unit)]
        assert len(covered) == verses, f"RV 1.{sukta} covers {len(covered)} of {verses}"
        assert len(set(covered)) == verses, f"RV 1.{sukta} covers a verse twice"


# ------------------------------------------------------- what must NOT be reclassified -


def test_a_declaration_whose_counts_contradict_the_rule_is_refused() -> None:
    """BAD -> FAIL at construction. RV 9.7 is the case this protects.

    9 verses and 8 units is a real mismatch, and it is NOT a paired spine -- there the merge
    falls on the last unit and the first seven attachments are correct. Declaring it
    PAIRED_DVIPADA would move eight correct rows, so the dataclass refuses it.
    """
    with pytest.raises(ValueError, match="requires ceil"):
        _correction(7, 8, 9)


def test_an_unknown_spine_is_refused() -> None:
    with pytest.raises(ValueError, match="unknown spine"):
        VerseSpineCorrection(
            correction_id="TEST",
            source_artifact_id="ART",
            source_revision_id=1,
            hymn_key="VG:RV:SAK:M01:S065",
            spine="GUESSED_FROM_THE_COUNTS",
            source_unit_count=5,
            canonical_verse_count=10,
            reason="test",
        )


def test_a_row_outside_the_hymn_is_not_matched() -> None:
    """Boundary. The hymns either side of the span must be untouchable by this correction."""
    correction = _correction(65, 5, 10)
    for outside in (
        "VG:RV:SAK:M01:S064:V001",
        "VG:RV:SAK:M01:S066:V001",
        "VG:RV:SAK:M09:S007:V008",
        "VG:AV:SAU:K01:S001:V001",
    ):
        assert not correction.matches(outside, 99), outside


def test_a_row_beyond_the_declared_unit_count_is_not_matched() -> None:
    """Verse 6 of RV 1.65 carries no translation, and must not acquire one by matching.

    The unit index is read off the row's own verse number, so a row at verse 6 would resolve
    to unit 6 -- which the source does not print. The declared unit count is the bound.
    """
    correction = _correction(65, 5, 10)
    assert correction.matches("VG:RV:SAK:M01:S065:V005", 99)
    assert not correction.matches("VG:RV:SAK:M01:S065:V006", 99)
    assert not correction.matches("VG:RV:SAK:M01:S065:V010", 99)


def test_a_different_source_revision_is_not_matched() -> None:
    """A re-fetched page might number differently, so the correction is pinned to a revision."""
    correction = _correction(65, 5, 10)
    assert correction.matches("VG:RV:SAK:M01:S065:V002", 99)
    assert not correction.matches("VG:RV:SAK:M01:S065:V002", 100)


# ------------------------------------------------------------------- the applier -


def _applier(correction: VerseSpineCorrection) -> tuple[CorrectionApplier, dict[str, str]]:
    keys = [
        f"{correction.hymn_key}:V{n:03d}"
        for n in range(1, correction.canonical_verse_count + 1)
    ]
    key_by_id = {f"id-{k}": k for k in keys}
    id_by_key = {k: f"id-{k}" for k in keys}
    return CorrectionApplier((), key_by_id, id_by_key, spine_corrections=(correction,)), id_by_key


def test_the_applier_reanchors_and_restates_the_claim() -> None:
    correction = _correction(65, 5, 10)
    applier, id_by_key = _applier(correction)
    row = {
        "translation_id": "old",
        "passage_id": id_by_key["VG:RV:SAK:M01:S065:V002"],
        "text": "The Gods approached the ways of holy Law",
        "alignment_level": AlignmentLevel.MANTRA.value,
        "alignment": TranslationAlignment.EXACT_MANTRA_ALIGNMENT.value,
        "source_revision_id": 99,
    }
    out = applier.apply(row)
    assert out["passage_id"] == id_by_key["VG:RV:SAK:M01:S065:V003"]
    assert out["covers_canonical_keys"] == [
        "VG:RV:SAK:M01:S065:V003",
        "VG:RV:SAK:M01:S065:V004",
    ]
    # The claim must change with the target. Leaving MANTRA on a two-verse span is the half
    # of the defect that is not about which verse the row sits on.
    assert out["alignment_level"] == AlignmentLevel.MANTRA_RANGE.value
    assert out["alignment"] == TranslationAlignment.RANGE_ALIGNMENT.value
    assert out["source_unit"] == 2
    assert out["source_verse_spine"] == PAIRED_DVIPADA
    assert out["upstream_correction_id"] == correction.correction_id
    # The text is carried, never rewritten.
    assert out["text"] == row["text"]
    assert out["translation_id"] != "old", "a re-anchored row derives a new id"


def test_the_applier_leaves_the_text_and_the_provenance_alone() -> None:
    correction = _correction(70, 6, 11)
    applier, id_by_key = _applier(correction)
    row = {
        "translation_id": "old",
        "passage_id": id_by_key["VG:RV:SAK:M01:S070:V006"],
        "text": "Like a brave archer, like one skilled and bold",
        "translator": "Ralph T. H. Griffith",
        "year": 1896,
        "work_edition": "The Hymns of the Rigveda, second edition",
        "rights_status": "PUBLIC_DOMAIN",
        "source_id": "WIKISOURCE_GRIFFITH_RV",
        "alignment_level": AlignmentLevel.MANTRA.value,
        "source_revision_id": 99,
    }
    out = applier.apply(row)
    assert out["passage_id"] == id_by_key["VG:RV:SAK:M01:S070:V011"]
    for field in ("text", "translator", "year", "work_edition", "rights_status", "source_id"):
        assert out[field] == row[field], field
    # Unit 6 covers one verse, so MANTRA is the true claim and must survive.
    assert out["alignment_level"] == AlignmentLevel.MANTRA.value
    assert out["covers_canonical_keys"] == ["VG:RV:SAK:M01:S070:V011"]


def test_a_row_the_correction_does_not_claim_passes_through_untouched() -> None:
    correction = _correction(65, 5, 10)
    applier, _ = _applier(correction)
    row = {"translation_id": "x", "passage_id": "id-unknown", "text": "t"}
    assert applier.apply(row) == row


def test_an_unapplied_spine_declaration_is_an_error() -> None:
    """A declaration that matched nothing documents a fix the data does not contain."""
    correction = _correction(65, 5, 10)
    applier, _ = _applier(correction)
    with pytest.raises(ValueError, match="matched no corpus row"):
        verify_corrections_applied(applier)


# --------------------------------------------------------------- the live registry -


def test_the_registry_declares_exactly_the_six_measured_hymns() -> None:
    """The declared set must be the measured set -- no more, and no fewer."""
    declared = load_spine_corrections(PROJECT_ROOT)
    assert {c.hymn_key for c in declared} == {
        f"VG:RV:SAK:M01:S{s:03d}" for s in SPAN_SHAPE
    }
    for correction in declared:
        sukta = int(correction.hymn_key.split(":")[4][1:])
        units, verses = SPAN_SHAPE[sukta]
        assert correction.source_unit_count == units
        assert correction.canonical_verse_count == verses
        assert correction.spine == PAIRED_DVIPADA


def test_the_audit_artifact_agrees_with_the_declared_corrections() -> None:
    """The declaration and the measurement are separate files; they must still agree.

    This is the check that catches a hand-edited registry drifting away from the evidence it
    claims to rest on.
    """
    if not AUDIT.exists():
        pytest.skip("pre-fix audit artifact not present in this checkout")
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    declared = {c.hymn_key: c for c in load_spine_corrections(PROJECT_ROOT)}
    assert audit["measurement"]["wrongly_attached"] == 25
    assert audit["measurement"]["currently_translated"] == 31
    for hymn in audit["hymns_in_span"]:
        correction = declared[hymn["hymn_key"]]
        assert correction.source_unit_count == hymn["source_unit_count"]
        assert correction.canonical_verse_count == hymn["canonical_verse_count"]
        assert hymn["spine"] == PAIRED_DVIPADA
        assert hymn["is_single_hemistich"] is True


def test_the_neighbouring_hymns_are_one_to_one_in_the_audit() -> None:
    """Boundary, measured rather than asserted: 1.63, 1.64, 1.71 and 1.72 must not move."""
    if not AUDIT.exists():
        pytest.skip("pre-fix audit artifact not present in this checkout")
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    spines = {h["hymn"]: h["spine"] for h in audit["neighbours_unchanged_baseline"]}
    for hymn in ("RV 1.63", "RV 1.64", "RV 1.71", "RV 1.72"):
        assert spines[hymn] == "ONE_TO_ONE", hymn
    # RV 1.73 is a real mismatch of a different kind -- 9 units against 10 verses, two
    # hemistichs per verse -- and it must stay out of the paired class rather than being
    # swept in by the count.
    assert spines["RV 1.73"] == "UNEXPLAINED_MISMATCH"


# ------------------------------------------------- the builder's own classification -


@pytest.mark.parametrize(
    ("translated", "verses", "hemistichs", "expected", "why"),
    [
        (5, 10, {1}, True, "RV 1.65-1.69: half the hymn, single hemistichs"),
        (6, 11, {1}, True, "RV 1.70: odd verse count, still ceil(V/2)"),
        (8, 9, {2}, False, "RV 9.7: fewer units, but normal verses -- merge is at the end"),
        (5, 10, {2}, False, "half the hymn but normal verses: a real coverage gap"),
        (9, 10, {2}, False, "RV 1.73: off by one, not a pairing"),
        (10, 11, {2}, False, "RV 1.53: off by one, not a pairing"),
        (5, 10, {1, 2}, False, "mixed hemistichs: not a uniformly dvipada hymn"),
        (0, 6, {2}, False, "RV 1.179: nothing parsed at all"),
        (10, 10, {2}, False, "complete, so no shortfall to classify"),
    ],
)
def test_the_builder_classifies_a_shortfall_correctly(
    translated: int, verses: int, hemistichs: set[int], expected: bool, why: str
) -> None:
    """GOOD -> PASS and BAD -> FAIL on the predicate the build guard now uses.

    Every row here is a hymn that actually exists in the corpus, so the table is a census of
    the real shapes rather than invented arithmetic. The three ``{2}`` rows are the ones that
    matter: each is a genuine count mismatch that must NOT be reclassified as a spine.
    """
    assert looks_like_paired_verse_spine(translated, verses, hemistichs) is expected, why
