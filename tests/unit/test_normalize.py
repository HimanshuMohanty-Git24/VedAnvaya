"""Accent handling must never damage a base letter and never hide a real difference."""

import pytest

from vedagraph.normalize import (
    ComparisonForm,
    ComparisonProfile,
    comparison_form,
    comparison_normalize,
    fold_transcription,
    has_vedic_accents,
    normalize_nfc,
    strip_editorial_marks,
    strip_vedic_accents,
)

# Real Vedic combining characters, not stand-ins.
GRETIL_RV_1_1_1 = "a̱gnim ī̍ḻe pu̱rohi̍taṁ ya̱jñasya̍ de̱vam ṛ̱tvija̍m | hotā̍raṁ ratna̱dhāta̍mam ||"
VEDAWEB_RV_1_1_1 = "agním īḷe puróhitaṁ yajñásya devám r̥tvíjam hótāraṁ ratnadhā́tamam"
EICHLER_RV_1_1_1 = "अ॒ग्निमी॑ळे पु॒रोहि॑तं य॒ज्ञस्य॑ दे॒वमृ॒त्विज॑म् होता॑रं रत्न॒धात॑मम्"


def test_gretil_and_vedaweb_use_different_accent_notations() -> None:
    import unicodedata

    gretil_marks = {char for char in GRETIL_RV_1_1_1 if unicodedata.combining(char)}
    vedaweb_marks = {
        char
        for char in unicodedata.normalize("NFD", VEDAWEB_RV_1_1_1)
        if unicodedata.combining(char)
    }
    assert "̱" in gretil_marks  # anudatta
    assert "̍" in gretil_marks  # svarita
    assert "́" in vedaweb_marks  # udatta
    assert "́" not in gretil_marks
    assert has_vedic_accents(GRETIL_RV_1_1_1)
    assert has_vedic_accents(VEDAWEB_RV_1_1_1)
    assert has_vedic_accents(EICHLER_RV_1_1_1)


def test_stripping_accents_keeps_letters_built_from_the_same_marks() -> None:
    # s-acute is s + U+0301, the same mark VedaWeb uses for udatta.
    assert strip_vedic_accents("darśata") == "darśata"
    assert strip_vedic_accents("viśvátaḥ") == "viśvataḥ"
    # GRETIL's retroflex lateral is l + U+0331, the same mark it uses for anudatta.
    assert strip_vedic_accents("ī̍ḻe") == "īḻe"
    # An accented vocalic r carries two marks, so the acute there really is a tone mark.
    assert strip_vedic_accents("vŕ̥ṣṇo") == "vr̥ṣṇo"
    assert strip_vedic_accents("ṛ̱tvija̍m") == "ṛtvijam"


def test_stripping_accents_handles_devanagari_svara_marks() -> None:
    assert strip_vedic_accents("अ॒ग्निमी॑ळे") == "अग्निमीळे"
    assert not has_vedic_accents("अग्निमीळे")


def test_unaccented_text_is_reported_as_unaccented() -> None:
    assert not has_vedic_accents("agnim ile purohitam")
    assert not has_vedic_accents("agnim īl̥e puraḥ-hitam")


def test_comparison_forms_are_a_refinement_ladder() -> None:
    forms = [
        comparison_form(GRETIL_RV_1_1_1, form)
        for form in (
            ComparisonForm.SOURCE_ORIGINAL,
            ComparisonForm.NFC,
            ComparisonForm.ACCENT_PRESERVING_NORMALIZED,
            ComparisonForm.ACCENT_STRIPPED_COMPARISON,
            ComparisonForm.SEARCH_NORMALIZED,
        )
    ]
    assert forms[0] == GRETIL_RV_1_1_1
    assert "|" not in forms[2]
    assert has_vedic_accents(forms[2])
    assert not has_vedic_accents(forms[3])
    assert len(forms[4]) <= len(forms[3])


def test_two_accent_notations_agree_once_accents_are_removed() -> None:
    left = comparison_form(GRETIL_RV_1_1_1, ComparisonForm.SEARCH_NORMALIZED)
    right = comparison_form(VEDAWEB_RV_1_1_1, ComparisonForm.SEARCH_NORMALIZED)
    assert left == right
    accented_left = comparison_form(GRETIL_RV_1_1_1, ComparisonForm.ACCENT_PRESERVING_NORMALIZED)
    accented_right = comparison_form(VEDAWEB_RV_1_1_1, ComparisonForm.ACCENT_PRESERVING_NORMALIZED)
    assert accented_left != accented_right


def test_transcription_fold_maps_iast_and_iso_15919_together() -> None:
    assert fold_transcription("ṛtvijam") == fold_transcription("r̥tvijam")
    assert fold_transcription("hotāraṁ") == fold_transcription("hotāraṃ")
    assert fold_transcription("gacchati") == fold_transcription("gachati")
    assert fold_transcription("agnim") != fold_transcription("agniḥ")


def test_editorial_marks_and_gretil_svarita_digits_are_comparison_only() -> None:
    assert strip_editorial_marks("a | b || c") == "a b c"
    assert strip_editorial_marks("i1tthā") == "itthā"
    assert strip_editorial_marks("īḷe-_ puróhitam") == "īḷe puróhitam"
    # Stored text is never rewritten.
    assert normalize_nfc("a | b") == "a | b"


def test_legacy_comparison_profiles_still_behave() -> None:
    assert comparison_normalize(GRETIL_RV_1_1_1, ComparisonProfile.ACCENT_PRESERVING) == (
        normalize_nfc(GRETIL_RV_1_1_1)
    )
    assert not has_vedic_accents(
        comparison_normalize(GRETIL_RV_1_1_1, ComparisonProfile.ACCENTLESS)
    )


@pytest.mark.xfail(
    reason=(
        "The fold fix is correct and is NOT applied, because applying it in place trips "
        "the referent-drift gate on 5 Yajurvedic keys: referent.py computes "
        "comparison_sha256 through this fold. Blocked on "
        "FOLD_FIX_BREAKS_REFERENT_IDENTITY in data/staging/integration/blockers.json, "
        "which sets out three options. These tests are kept as xfail rather than deleted "
        "so the target behaviour is on the record and will announce itself the moment the "
        "blocker is resolved -- a deleted test would let the fix land silently wrong."
    ),
    strict=True,
)
def test_anusvara_folds_the_same_whether_or_not_it_was_transliterated() -> None:
    """The five Devanagari anusvara rules were dead where they were needed most.

    `enrich/surfaces.build_surfaces` transliterates before it folds, and the script-folded
    surface is the only one a cross-script pair can be compared on. So every rule keyed on
    a Devanagari codepoint was correct and unreachable -- worse than absent, because the
    table read as though the case were handled.

    The cost was measured, not estimated: the Vajasaneyi cluster arrived as two sentinels
    across 780 of 1,975 Yajurvedic verses, which mistyped 396 of 6,271 cross-Veda
    transformation types and left 197 stored relationship types contradicted by their own
    text.
    """
    from vedagraph.transliteration.indic import DevanagariToIAST

    transliterate = DevanagariToIAST().transliterate
    cluster = "ᳪं᳭"
    assert fold_transcription(cluster) == fold_transcription(transliterate(cluster))


@pytest.mark.xfail(
    reason=(
        "The fold fix is correct and is NOT applied, because applying it in place trips "
        "the referent-drift gate on 5 Yajurvedic keys: referent.py computes "
        "comparison_sha256 through this fold. Blocked on "
        "FOLD_FIX_BREAKS_REFERENT_IDENTITY in data/staging/integration/blockers.json, "
        "which sets out three options. These tests are kept as xfail rather than deleted "
        "so the target behaviour is on the record and will announce itself the moment the "
        "blocker is resolved -- a deleted test would let the fix land silently wrong."
    ),
    strict=True,
)
def test_candrabindu_does_not_reach_the_comparison_surface_as_punctuation() -> None:
    """U+0901 transliterates to a bare ASCII tilde, which no fold rule reached.

    A nasalisation sign therefore survived into the comparison surface as punctuation, on
    138 Yajurvedic and 3 Samavedic verses. Those 3 Samavedic verses are the reason the
    RV-SV pair's correction is 6 edges rather than the 0 a Yajurveda-only assumption gave.
    """
    from vedagraph.transliteration.indic import DevanagariToIAST

    folded = fold_transcription(DevanagariToIAST().transliterate("ँ"))
    assert "~" not in folded
    assert len(folded) == 1


def test_the_lateral_series_is_still_not_folded() -> None:
    """A guard on what must NOT change, measured rather than assumed.

    Equating the Devanagari lateral with the retroflex is a scholarly position on the
    Rigvedic intervocalic alternation, not a normalisation. The same applies to the
    homorganic nasals: an edition writing one where another writes anusvara genuinely
    differs, and folding them would erase a variant the parallel layer exists to report.
    """
    from vedagraph.transliteration.indic import DevanagariToIAST

    lateral = fold_transcription(DevanagariToIAST().transliterate("ळ"))
    assert lateral != fold_transcription("ḍa")


@pytest.mark.xfail(
    reason=(
        "The fold fix is correct and is NOT applied, because applying it in place trips "
        "the referent-drift gate on 5 Yajurvedic keys: referent.py computes "
        "comparison_sha256 through this fold. Blocked on "
        "FOLD_FIX_BREAKS_REFERENT_IDENTITY in data/staging/integration/blockers.json, "
        "which sets out three options. These tests are kept as xfail rather than deleted "
        "so the target behaviour is on the record and will announce itself the moment the "
        "blocker is resolved -- a deleted test would let the fix land silently wrong."
    ),
    strict=True,
)
def test_a_run_of_anusvara_markers_collapses_to_one() -> None:
    """Two adjacent markers denote one nasal in every source held here."""
    from vedagraph.normalize.unicode import _ANUSVARA

    assert fold_transcription(_ANUSVARA * 3) == _ANUSVARA
