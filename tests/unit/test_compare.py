"""Text-version comparison: categories, accent isolation, and identity stability."""

from pathlib import Path

import pytest

from vedagraph.compare import (
    VersionReading,
    classify,
    compare_missing,
    compare_readings,
    load_comparison_config,
    render_report,
    summarize,
)
from vedagraph.compare.run import ComparisonResult
from vedagraph.identity import rv_mantra_identity
from vedagraph.models.enums import TextComparisonCategory, TextRole

KEY = "VG:RV:SAK:M01:S001:V001"
CITATION = "RV 1.1.1"

GRETIL = "a̱gnim ī̍ḻe pu̱rohi̍taṁ ya̱jñasya̍ de̱vam ṛ̱tvija̍m | hotā̍raṁ ratna̱dhāta̍mam ||"
VEDAWEB = "agním īḷe puróhitaṁ yajñásya devám r̥tvíjam hótāraṁ ratnadhā́tamam"
PADAPATHA = "agnim īl̥e puraḥ-hitam yajñasya devam r̥tvijam hotāram ratna-dhātamam"
EICHLER = "अ॒ग्निमी॑ळे पु॒रोहि॑तं य॒ज्ञस्य॑ दे॒वमृ॒त्विज॑म् होता॑रं रत्न॒धात॑मम्"


def _compare(left: str, right: str, right_role: TextRole = TextRole.PARALLEL_TEXT) -> object:
    return compare_readings(
        passage_key=KEY,
        citation=CITATION,
        left=VersionReading("LEFT", left, TextRole.PRIMARY_TEXT),
        right=VersionReading("RIGHT", right, right_role),
    )


def test_identical_source_text_is_identical() -> None:
    result = _compare(GRETIL, GRETIL)
    assert result.category == TextComparisonCategory.IDENTICAL
    assert result.similarity == 1.0
    assert not result.accent_only


def test_nfc_only_difference_is_reported_as_unicode_only() -> None:
    decomposed = "agním"
    composed = "agním"
    result = _compare(decomposed, composed)
    assert result.category == TextComparisonCategory.UNICODE_ONLY


def test_punctuation_only_difference_is_orthographic() -> None:
    result = _compare("agním īḷe | puróhitaṁ ||", "agním īḷe puróhitaṁ")
    assert result.category == TextComparisonCategory.ORTHOGRAPHIC


def test_transcription_system_difference_is_orthographic_not_textual() -> None:
    result = _compare("ṛtvijam hotāraṁ", "r̥tvijam hotāraṃ")
    assert result.category == TextComparisonCategory.ORTHOGRAPHIC
    assert not result.accent_only


def test_two_accent_notations_are_reported_as_accent_only() -> None:
    result = _compare(GRETIL, VEDAWEB)
    assert result.category == TextComparisonCategory.ACCENT_ONLY
    assert result.accent_only
    assert result.left_accented and result.right_accented
    assert result.similarity == 1.0


def test_substantive_difference_is_not_reported_as_accent_only() -> None:
    result = _compare("agním īḷe puróhitam", "agním īḷe puróhitāsam")
    assert result.category == TextComparisonCategory.UNCLASSIFIED
    assert not result.accent_only
    assert result.differing_tokens >= 1
    assert result.similarity < 1.0


def test_word_segmentation_difference_is_separated_from_lexical_change() -> None:
    result = _compare("agnim ile purohitam", "agnimile puro hitam")
    assert result.category == TextComparisonCategory.SANDHI_OR_SEGMENTATION


def test_reordered_tokens_are_a_structural_variant() -> None:
    result = _compare("agnim ile purohitam", "purohitam agnim ile")
    assert result.category == TextComparisonCategory.STRUCTURAL_VARIANT


def test_metrical_restoration_is_labelled_only_from_declared_provenance() -> None:
    restored = _compare("vīryāṇi ca krṇvatām", "vīri̯āṇi ca kr̥ṇvatām", TextRole.METRICALLY_RESTORED)
    assert restored.category == TextComparisonCategory.METRICAL_RESTORATION
    assert "declared provenance" in restored.classification_basis
    plain = _compare("vīryāṇi ca krṇvatām", "vīri̯āṇi ca kr̥ṇvatām", TextRole.PARALLEL_TEXT)
    assert plain.category == TextComparisonCategory.UNCLASSIFIED


def test_lexical_variant_is_never_assigned_automatically() -> None:
    categories = {
        classify(
            VersionReading("a", left, TextRole.PRIMARY_TEXT),
            VersionReading("b", right, role),
        )[0]
        for left, right in (
            (GRETIL, VEDAWEB),
            (GRETIL, PADAPATHA),
            ("agnim", "indram"),
            ("agnim ile", "ile agnim"),
        )
        for role in TextRole
    }
    assert TextComparisonCategory.LEXICAL_VARIANT not in categories


def test_cross_script_readings_are_not_compared_as_strings() -> None:
    result = _compare(GRETIL, EICHLER)
    assert result.category == TextComparisonCategory.UNCLASSIFIED
    assert "different scripts" in result.classification_basis


def test_missing_reading_is_recorded_rather_than_dropped() -> None:
    result = compare_missing(
        passage_key=KEY, citation=CITATION, left_version_id="A", right_version_id="B"
    )
    assert result.category == TextComparisonCategory.MISSING
    assert result.similarity == 0.0


def test_comparison_is_deterministic() -> None:
    first = _compare(GRETIL, VEDAWEB)
    second = _compare(GRETIL, VEDAWEB)
    assert first.model_dump() == second.model_dump()


def test_passage_identity_does_not_depend_on_which_version_is_primary() -> None:
    """The point of the whole exercise: swapping the base edition must not renumber."""
    key, urn, identifier = rv_mantra_identity(1, 1, 1)
    for text, role in (
        (GRETIL, TextRole.PRIMARY_TEXT),
        (VEDAWEB, TextRole.PRIMARY_TEXT),
        (PADAPATHA, TextRole.PADAPATHA),
        (EICHLER, TextRole.PARALLEL_TEXT),
    ):
        reading = VersionReading("V", text, role)
        result = compare_readings(
            passage_key=key,
            citation=CITATION,
            left=reading,
            right=VersionReading("W", text, role),
        )
        assert result.passage_key == key
    again_key, again_urn, again_id = rv_mantra_identity(1, 1, 1)
    assert (again_key, again_urn, again_id) == (key, urn, identifier)


def test_sample_config_is_stratified_not_the_first_n_suktas() -> None:
    config = load_comparison_config(Path("data/builds/rv_m1_text_comparison.yaml"))
    suktas = config.selected_suktas
    assert len(suktas) >= 10
    assert suktas != list(range(1, len(suktas) + 1))
    assert 164 in suktas and 191 in suktas
    assert max(suktas) > 150 and min(suktas) == 1
    assert all(str(sukta) in config.sample_rationale for sukta in suktas)
    assert config.baseline_version_id not in config.compared_version_ids


def test_report_is_rendered_from_comparison_records() -> None:
    config = load_comparison_config(Path("data/builds/rv_m1_text_comparison.yaml"))
    comparisons = [
        _compare(GRETIL, VEDAWEB),
        _compare(GRETIL, PADAPATHA),
        _compare(GRETIL, VEDAWEB, TextRole.METRICALLY_RESTORED),
    ]
    for comparison in comparisons:
        comparison.left_version_id = "GRETIL.RV.AUFRECHT"
    comparisons[0].right_version_id = "VEDAWEB.AUFRECHT"
    comparisons[1].right_version_id = "VEDAWEB.PADAPATHA"
    comparisons[2].right_version_id = "VEDAWEB.VNH"
    result = ComparisonResult(
        config_sha256="0" * 64,
        aligned_passages=1,
        comparisons=comparisons,
        readings_per_version={"GRETIL.RV.AUFRECHT": 1, "VEDAWEB.AUFRECHT": 1},
        accented_per_version={"GRETIL.RV.AUFRECHT": 1, "VEDAWEB.AUFRECHT": 1},
        output_path=Path("data/derived/test"),
        report_path=Path("data/derived/test/report.md"),
    )
    report = render_report(config, result)
    assert "ACCENT_ONLY" in report
    assert "CC_BY_NC_SA" in report
    assert "van Nooten and Holland" in report
    assert "not for commercial purposes" in report
    assert "LEXICAL_VARIANT` is never assigned automatically" in report
    assert summarize(comparisons)[("GRETIL.RV.AUFRECHT", "VEDAWEB.AUFRECHT")]


def test_comparison_config_rejects_an_unregistered_version(tmp_path: Path) -> None:
    from vedagraph.compare.run import run_comparison

    source = Path("data/builds/rv_m1_text_comparison.yaml").read_text(encoding="utf-8")
    broken = tmp_path / "broken.yaml"
    broken.write_text(source.replace("VEDAWEB.AUFRECHT", "VEDAWEB.NOT_REGISTERED"), "utf-8")
    with pytest.raises(ValueError, match="unregistered text versions"):
        run_comparison(broken)
