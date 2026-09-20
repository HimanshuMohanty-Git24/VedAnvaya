"""Accent handling must never damage a base letter and never hide a real difference."""


from vedagraph.normalize import (
    ComparisonForm,
    ComparisonProfile,
    comparison_form,
    comparison_normalize,
    fold_transcription,
    fold_transcription_cross_script,
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


def test_anusvara_folds_the_same_whether_or_not_it_was_transliterated() -> None:
    """The five Devanagari anusvara rules were dead where they were needed most.

    `enrich/surfaces.build_surfaces` transliterates before it folds, and the script-folded
    surface is the only one a cross-script pair can be compared on. So every rule keyed on
    a Devanagari codepoint was correct and unreachable -- worse than absent, because the
    table read as though the case were handled.

    The cost was measured, not estimated: the Vajasaneyi cluster arrived as TWO sentinels
    on 1,232 of 3,811 Yajurvedic text records, which mistyped 396 of 6,271 cross-Veda
    transformation types and left 197 stored relationship types contradicted by their own
    text.

    The fix is on the CROSS-SCRIPT fold, not this module's identity fold, and the
    distinction is the whole point: correcting the comparison in place moved the released
    comparison digest of 5 Yajurvedic keys, which the referent gate correctly read as
    drift. Option B of FOLD_FIX_BREAKS_REFERENT_IDENTITY. All 3,819 released referent
    digests reproduce byte for byte under the fix.
    """
    from vedagraph.transliteration.indic import DevanagariToIAST

    transliterate = DevanagariToIAST().transliterate
    cluster = "ᳪं᳭"
    # Compared on the SURFACE, not on the fold alone. U+1CED is removed by accent
    # stripping, which is a pipeline stage rather than a fold rule, so comparing raw fold
    # output would assert against a pipeline that does not exist.
    surface = ComparisonForm.CROSS_SCRIPT_COMPARISON
    assert comparison_form(cluster, surface) == comparison_form(transliterate(cluster), surface)
    assert len(comparison_form(transliterate(cluster), surface)) == 1

    # And on the identity surface it is still two sentinels -- the defect, preserved,
    # because that surface is compared against a released baseline.
    identity = comparison_form(transliterate(cluster), ComparisonForm.SEARCH_NORMALIZED)
    assert len(identity) == 2


def test_candrabindu_does_not_reach_the_comparison_surface_as_punctuation() -> None:
    """U+0901 transliterates to a bare ASCII tilde, which no fold rule reached.

    A nasalisation sign therefore survived into the comparison surface as punctuation, on
    153 Yajurvedic and 3 Samavedic text records. Those 3 Samavedic records are the reason
    the RV-SV pair's correction is 6 edges rather than the 0 a Yajurveda-only assumption
    gave.

    U+007E occurs in the stored text of none of the four corpora, so this spelling can
    only ever arrive by transliteration -- which is why it is safe to fold and why it
    belongs on the cross-script table alone.
    """
    from vedagraph.transliteration.indic import DevanagariToIAST

    folded = fold_transcription_cross_script(DevanagariToIAST().transliterate("ँ"))
    assert "~" not in folded
    assert len(folded) == 1
    # The identity fold must still leave it alone, or the digest would have moved.
    assert "~" in fold_transcription(DevanagariToIAST().transliterate("ँ"))


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


def test_a_run_of_anusvara_markers_collapses_to_one() -> None:
    """Two adjacent markers denote one nasal in every source held here."""
    from vedagraph.normalize.unicode import _ANUSVARA, _VOCALIC_R

    assert fold_transcription_cross_script(_ANUSVARA * 3) == _ANUSVARA
    # Only the anusvara. A run of the other three sentinels is two real letters, and the
    # Rigveda alone carries 419 such runs across 404 records.
    assert fold_transcription_cross_script(_VOCALIC_R * 2) == _VOCALIC_R * 2
    # And the identity fold collapses nothing at all.
    assert fold_transcription(_ANUSVARA * 3) == _ANUSVARA * 3


def test_the_cross_script_fold_never_moves_the_identity_fold() -> None:
    """The contract that makes option B safe, stated as a test rather than a comment.

    ``referent.text_fingerprints`` digests ``SEARCH_NORMALIZED``. Every rule that only a
    transliterated surface needs therefore has to live on the other table, or a comparison
    correction becomes indistinguishable from a key starting to denote a different verse.
    Measured before the split: the sentinel-run collapse alone moved 5 released Yajurvedic
    keys, the U+1CEC rules 4 more and the U+A8F7 rule 1.
    """
    from vedagraph.normalize.unicode import (
        CROSS_SCRIPT_EQUIVALENCES,
        TRANSCRIPTION_EQUIVALENCES,
    )

    identity_spellings = {variant for variant, _ in TRANSCRIPTION_EQUIVALENCES}
    for variant, sentinel in CROSS_SCRIPT_EQUIVALENCES:
        assert variant not in identity_spellings, (
            f"{variant!r} is on both tables; a cross-script rule that is also an identity "
            "rule moves a released comparison digest"
        )
        # Each rule must ADD something. Note the identity fold may legitimately rewrite
        # PART of a multi-character variant -- ANUSVARA_SIGN is one of its own keys -- so
        # the claim is about the result, not about the variant being left untouched.
        assert fold_transcription_cross_script(variant) == sentinel
        assert fold_transcription(variant) != sentinel, (
            f"the identity fold already reaches {variant!r}, so this rule is not a "
            "cross-script addition and the table overstates its own contents"
        )


def test_the_undefined_private_use_codepoint_is_reported_not_folded() -> None:
    """U+F15C sits in 20 unaccented Vajasaneyi records and is deliberately left alone.

    It appears where the same layer elsewhere writes an anusvara -- ``prthivyA<F15C>
    satena``, ``devAnA<F15C> samit`` -- so reading it as one is tempting and is a
    transcription judgement rather than a normalisation. A private-use code point has no
    Unicode identity and no source assertion defines it. Registered as a source-
    transcription defect instead of folded, because the owner's decision is that a folded
    match may generate a candidate and may not establish identity.
    """
    from vedagraph.normalize.unicode import (
        _ANUSVARA,
        UNRESOLVED_PRIVATE_USE_IN_SOURCE,
    )

    assert fold_transcription_cross_script(UNRESOLVED_PRIVATE_USE_IN_SOURCE) != _ANUSVARA
    assert (
        fold_transcription_cross_script(UNRESOLVED_PRIVATE_USE_IN_SOURCE)
        == UNRESOLVED_PRIVATE_USE_IN_SOURCE
    )


def test_cross_script_separators_do_not_widen_the_identity_separator_set() -> None:
    """Four editorial marks only a Devanagari source uses, dropped for comparison only.

    An editorial variant note, an insertion marker and a soft-hyphen stand-in survived
    onto the comparison surface and caused false INEQUALITY on six of 20,210 records.
    ``SEPARATOR_MARKS`` feeds the identity digest, so they are widened for one surface
    rather than added to it.
    """
    from vedagraph.normalize.unicode import CROSS_SCRIPT_SEPARATOR_MARKS, SEPARATOR_MARKS

    assert CROSS_SCRIPT_SEPARATOR_MARKS.isdisjoint(SEPARATOR_MARKS)
    for mark in CROSS_SCRIPT_SEPARATOR_MARKS:
        assert mark in comparison_form(f"a{mark}b", ComparisonForm.SEARCH_NORMALIZED)
        assert mark not in comparison_form(f"a{mark}b", ComparisonForm.CROSS_SCRIPT_COMPARISON)


def test_strip_editorial_marks_default_is_unchanged_for_every_existing_caller() -> None:
    """The new parameter must be invisible unless a caller asks for it."""
    from vedagraph.normalize.unicode import CROSS_SCRIPT_SEPARATOR_MARKS

    sample = "a+b" + chr(0x5C) + "c" + chr(0xAC) + "d" + chr(0x2013) + "e | f ||"
    assert strip_editorial_marks(sample) == strip_editorial_marks(sample, frozenset())
    assert strip_editorial_marks(sample) != strip_editorial_marks(
        sample, CROSS_SCRIPT_SEPARATOR_MARKS
    )
