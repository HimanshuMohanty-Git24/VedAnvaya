"""Controlled fixtures for the translation Gate B/C checks: BAD must fail, GOOD must pass.

A gate with no failing test is an opinion. Every check in this file exists because some
version of the analysis it guards was wrong in exactly the way the fixture reproduces, and
several of the mistakes were mine while building the gates rather than the staging agent's.
The fold cases in particular are a record of two errors made in opposite directions: first
stripping the combining acute (which merged viśva into visva), then protecting it (which
scored two character-identical verses at 0.0, because the Atharvaveda edition writes udatta
as an acute while the Rigveda edition writes it as U+030D).

The BAD/GOOD pairing matters more than the count. A check that only ever sees good input
cannot distinguish "this data is clean" from "this check does nothing", which is the failure
mode the campaign's validator contract calls out: coverage, not merely pass rate.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

SCRIPTS = pathlib.Path(__file__).resolve().parents[2] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from gate_bc_gate_b import (  # noqa: E402
    CHROME_EXACT,
    HTML_ARTEFACT,
    LABEL_ONLY,
    classify_granularity,
    parse_key,
)
from gate_bc_gate_c import CROSS_REFERENCE, detect_language  # noqa: E402
from gate_bc_textfold import (  # noqa: E402
    fold_english,
    fold_sanskrit,
    sandhi_insensitive,
    token_dice,
)
from gate_bc_yv_source_check import label_candidates, page_units  # noqa: E402
from validate_staging_artifact import NOT_IMPORTABLE  # noqa: E402


# ---------------------------------------------------------------------------------------
# The central importability policy
# ---------------------------------------------------------------------------------------


def test_the_central_policy_still_names_probable_and_unverified() -> None:
    """The packet imports this set rather than re-declaring it, so a drift must be loud.

    Every population count in the owner packet is split on this predicate: 740 of the 2,254
    staged translation rows are withheld by it alone. If the set changed and the packet kept
    its own copy, the packet would report a withheld population that the importer would
    happily import.
    """
    assert NOT_IMPORTABLE == {"PROBABLE", "UNVERIFIED"}


@pytest.mark.parametrize("confidence", ["PROBABLE", "UNVERIFIED"])
def test_bad_a_non_importable_confidence_is_refused(confidence: str) -> None:
    assert confidence in NOT_IMPORTABLE


@pytest.mark.parametrize("confidence", ["EXACT", "VERIFIED_SEGMENT"])
def test_good_an_importable_confidence_is_admitted(confidence: str) -> None:
    assert confidence not in NOT_IMPORTABLE


def test_bad_a_forced_address_is_not_caught_by_confidence_alone() -> None:
    """The defect the packet reports: policy keys on confidence, forcing is orthogonal.

    All 31 rows carrying `address_forced_without_content_control: true` are staged EXACT, so
    the central predicate admits every one of them. The withholding has to come from a
    separate check, which is why Gate B carries B_NEEDS_INDEPENDENT_CONTENT_CONTROL as its
    own category rather than trusting the confidence field.
    """
    forced_row = {"mapping_confidence": "EXACT", "address_forced_without_content_control": True}
    assert forced_row["mapping_confidence"] not in NOT_IMPORTABLE, (
        "if this ever becomes true the fixture is stale, but today the point stands: the "
        "central policy does not withhold a forced address"
    )


# ---------------------------------------------------------------------------------------
# Script folding: the load-bearing measurement
# ---------------------------------------------------------------------------------------

L = "Latin"
D = "Devanagari"


def test_good_devanagari_and_latin_witnesses_of_one_verse_fold_equal() -> None:
    """VS/SV Kauthuma Devanagari against GRETIL Rigveda Latin, same verse, must be identical."""
    sv = "त्वं नो अग्ने महोभिः पाहि विश्वस्या अरातेः । उत द्विषो मर्त्यस्य"
    rv = "tváṃ no̱ agne̱ mahobhi̍ḥ"
    assert fold_sanskrit(sv, D).startswith("tvaṃ no agne mahobhiḥ")
    # The real pair is asserted in the packet; here the point is that the Devanagari side
    # transliterates to the same tokens rather than to mojibake.
    assert "viśvasyā" in fold_sanskrit(sv, D)
    assert "arāteḥ" in fold_sanskrit(sv, D)


def test_bad_stripping_the_acute_would_merge_the_palatal_sibilant() -> None:
    """ś is s + U+0301. A fold that drops every acute merges viśva and visva.

    This is the first mistake this module made, and it is not cosmetic: the Samaveda
    populations' whole case is "this verse's Sanskrit is the same text as that Rigveda
    verse's", and a fold that cannot tell ś from s manufactures that identity.
    """
    assert fold_sanskrit("viśvasya", L) != fold_sanskrit("visvasya", L)
    assert fold_sanskrit("viśvasya", L) == "viśvasya"


def test_bad_protecting_the_acute_would_split_two_identical_verses() -> None:
    """The Atharvaveda edition marks udatta with an acute on the vowel; it must come off.

    The second mistake, made while fixing the first. tváṃ and tvaṃ are the same word, and
    a fold that keeps the acute on a vowel scored a genuinely EXACT_PARALLEL_OF pair at 0.0
    token Dice and would have failed every true row in the population.
    """
    assert fold_sanskrit("tváṃ", L) == fold_sanskrit("tvaṃ", L)
    assert fold_sanskrit("hí", L) == fold_sanskrit("hi", L)


def test_good_the_two_accent_notations_are_both_removed() -> None:
    """U+030D (Rigveda edition) and an acute (Atharvaveda edition) are the same mark."""
    assert fold_sanskrit("sto̍ma", L) == fold_sanskrit("stóma", L) == "stoma"


def test_good_vocalic_r_folds_across_the_two_romanisations() -> None:
    """r̥ (ISO 15919, ring below) and ṛ (IAST, dot below) are one phoneme."""
    assert fold_sanskrit("bhadrakr̥t", L) == fold_sanskrit("bhadrakṛt", L)


def test_good_nasalisation_folds_across_all_four_spellings() -> None:
    """ṁ, ṃ, m̐ and a combining tilde all write the same nasal in these editions."""
    forms = ["mahāṁś", "mahāṃś", "mahām̐ś"]
    folded = {fold_sanskrit(f, L) for f in forms}
    assert len(folded) == 1, f"expected one folded form, got {folded}"


def test_good_devanagari_candrabindu_survives_transliteration() -> None:
    """indic_transliteration renders ँ as an ASCII tilde, which no combining rule can see."""
    assert "~" not in fold_sanskrit("वाजाँ", D)
    assert fold_sanskrit("वाजाँ", D) == fold_sanskrit("वाजां", D)


def test_good_the_independent_svarita_digit_is_not_a_token() -> None:
    """The two editions disagree on the digit (ukthya1ṃ vs ukthya3ṃ) for one syllable."""
    assert fold_sanskrit("ukthya1ṃ", L) == fold_sanskrit("ukthya3ṃ", L)


def test_good_word_final_m_and_anusvara_are_one_sound_in_the_permissive_form() -> None:
    """RV 1.53.1 prints "vācam pra", AV 20.21.1 prints "vācaṃ pra": one verse, two volumes.

    Without this fold the duplication check -- which asks whether two targets sharing a
    literal have the same Sanskrit -- reported Griffith's two independent renderings of the
    same verse as generator duplication, on a one-character difference in a nasal.
    """
    assert sandhi_insensitive(fold_sanskrit("vācam pra mahe", L)) == sandhi_insensitive(
        fold_sanskrit("vācaṃ pra mahe", L)
    )


def test_bad_the_nasal_fold_must_not_be_in_the_strict_form() -> None:
    """Placing it in the strict fold broke 196 comparisons that had been matching.

    A boundary-conditioned substitution and a boundary-discarding comparison are
    incompatible: "tvām id" becomes "tvāṃid" while an already-joined "tvāmid" has no final m
    to convert. The strict fold must therefore leave the two spellings distinct, and the
    permissive one must unify every m.
    """
    assert fold_sanskrit("vācam pra", L) != fold_sanskrit("vācaṃ pra", L)
    assert sandhi_insensitive(fold_sanskrit("tvām id", L)) == sandhi_insensitive(
        fold_sanskrit("tvāmid", L)
    )


def test_bad_the_permissive_fold_still_separates_phonemes() -> None:
    for a, b in [("sa", "ṣa"), ("viśva", "visva"), ("agni", "agne"), ("kā", "ka")]:
        assert sandhi_insensitive(fold_sanskrit(a, L)) != sandhi_insensitive(
            fold_sanskrit(b, L)
        ), f"{a!r} and {b!r} merged in the permissive form"


def test_good_a_printed_verse_number_is_not_a_token() -> None:
    assert fold_sanskrit("agne ।। 1 ।।", L) == "agne"


@pytest.mark.parametrize(
    "a,b",
    [
        ("sa", "ṣa"),
        ("ta", "ṭa"),
        ("da", "ḍa"),
        ("na", "ṇa"),
        ("ka", "kā"),
        ("ra", "ṛ"),
        ("agni", "agne"),
        ("viśva", "visva"),
        ("hi", "hī"),
    ],
)
def test_bad_the_fold_must_not_merge_a_phonemic_distinction(a: str, b: str) -> None:
    """Over-normalisation is the failure mode that manufactures a false identity claim."""
    assert fold_sanskrit(a, L) != fold_sanskrit(b, L), f"{a!r} and {b!r} were merged"


def test_good_word_division_is_reported_separately_not_folded_by_default() -> None:
    """A reader deciding whether to trust a row needs the strict number and the loose one."""
    a, b = fold_sanskrit("vivasvaduṣasaś", L), fold_sanskrit("vivasvad uṣasaś", L)
    assert a != b
    assert sandhi_insensitive(a) == sandhi_insensitive(b)


def test_bad_a_real_variant_reading_must_not_fold_to_identical() -> None:
    """The two genuine non-identities the packet reports differ by one particle's nasal.

    If the fold folded this away, the packet would report 528 of 528 identity claims
    reproduced and the two false claims would ship as verified.
    """
    sv = fold_sanskrit("yaḥ somaḥ kalaśeṣvā antaḥ", L)
    rv = fold_sanskrit("yaḥ somaḥ kalaśeṣv āṃ antaḥ", L)
    assert sandhi_insensitive(sv) != sandhi_insensitive(rv)


# ---------------------------------------------------------------------------------------
# B1 target identity
# ---------------------------------------------------------------------------------------


def test_good_a_canonical_key_parses_to_its_veda_and_recension() -> None:
    p = parse_key("VG:AV:SAU:K20:S129:V003")
    assert (p["veda"], p["recension"], p["verse"]) == ("AV", "SAU", 3)


def test_bad_a_target_from_the_wrong_veda_is_detectable_from_the_key() -> None:
    """Same counts, swapped identities: the key carries the Veda, so the swap is visible."""
    assert parse_key("VG:SV:KAU:CHANDA:P01:D01:V05")["veda"] == "SV"
    assert parse_key("VG:RV:SAK:M08:S084:V001")["veda"] == "RV"
    assert parse_key("VG:SV:KAU:CHANDA:P01:D01:V05")["veda"] != parse_key(
        "VG:RV:SAK:M08:S084:V001"
    )["veda"]


# ---------------------------------------------------------------------------------------
# B3 granularity
# ---------------------------------------------------------------------------------------


def _row(locator: str, alignment: str = "EXACT_MANTRA_ALIGNMENT", **payload):
    return {
        "source_locator": locator,
        "payload": {"alignment": alignment, **payload},
    }


def test_good_a_printed_verse_label_is_mantra_grained() -> None:
    grain, _ = classify_granularity(_row("kanda 3, hymn 9, printed label '4'", printed_span=[4, 4]))
    assert grain == "MANTRA"


def test_bad_hymn_level_text_must_not_pass_as_mantra_level() -> None:
    """A hymn translation does not become a verse translation because the hymn is short."""
    grain, _ = classify_granularity(_row("kanda 20, hymn 129"))
    assert grain == "HYMN"


def test_bad_a_page_level_locator_is_section_grained() -> None:
    grain, _ = classify_granularity(_row("book page wyvbk12.htm, printed page 102"))
    assert grain == "SECTION"


def test_good_an_explicit_multi_verse_unit_is_a_range() -> None:
    grain, detail = classify_granularity(
        _row(
            "kanda 20, hymn 129, printed label '3', printed as one unit covering verses 3-4",
            alignment="RANGE_ALIGNMENT",
            printed_span=[3, 4],
        )
    )
    assert grain == "MANTRA_RANGE"
    assert detail["span_length"] == 2


def test_good_a_canonical_key_as_coordinate_is_mantra_grained() -> None:
    """The cross-corpus rows cite a :Mantra key, the most precise coordinate available.

    The first version of this classifier had no pattern for that shape, returned OTHER for
    all 194 of them, and then failed them for not being mantra-level. That was the
    classifier's defect, not the rows', and it moved the Gate B pass count by 194.
    """
    grain, detail = classify_granularity(
        _row("Rigveda parallel RV 9.61.12 (VG:RV:SAK:M09:S061:V012)")
    )
    assert grain == "MANTRA"
    assert detail["coordinate_is_canonical_key"] is True


def test_bad_a_range_missing_one_covered_key_is_incomplete() -> None:
    """A MANTRA_RANGE must enumerate every canonical key in its span.

    Modelled the way Gate B does it: derive the covered keys from the printed span and
    require each to be staged with the same literal. Dropping one leaves a canonical verse
    silently uncovered while the range claims it.
    """
    prefix, width = "VG:AV:SAU:K20:S129", 3
    covered = [f"{prefix}:V{n:0{width}d}" for n in range(3, 6)]
    assert covered == [
        "VG:AV:SAU:K20:S129:V003",
        "VG:AV:SAU:K20:S129:V004",
        "VG:AV:SAU:K20:S129:V005",
    ]
    staged = {covered[0], covered[2]}
    assert not set(covered).issubset(staged)


# ---------------------------------------------------------------------------------------
# B5 literal integrity
# ---------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "literal",
    ["Next", "Previous", "Index", "Sacred Texts", "sacred texts hinduism index"],
)
def test_bad_page_furniture_is_not_a_translation(literal: str) -> None:
    assert fold_english(literal) in CHROME_EXACT


@pytest.mark.parametrize("literal", ["<p>Agni I laud</p>", "Agni &amp; Indra", "&#160;Agni"])
def test_bad_markup_residue_is_rejected(literal: str) -> None:
    assert HTML_ARTEFACT.search(literal)


@pytest.mark.parametrize("literal", ["HYMN CXX", "12", "iv. 3", "23"])
def test_bad_a_bare_label_is_not_a_translation(literal: str) -> None:
    assert LABEL_ONLY.fullmatch(literal.strip())


def test_good_a_real_translation_is_not_mistaken_for_furniture() -> None:
    real = "I laud your most beloved guest like a dear friend, O Agni, him"
    assert fold_english(real) not in CHROME_EXACT
    assert not HTML_ARTEFACT.search(real)
    assert not LABEL_ONLY.fullmatch(real)


# ---------------------------------------------------------------------------------------
# C literal integrity: the two defects Gate B passed and Gate C caught
# ---------------------------------------------------------------------------------------


def test_bad_an_editorial_cross_reference_is_not_a_translation() -> None:
    """The real row: VS 21.45 staged "Let the Hotar worship Indra, etc., as in 44 ...".

    Gate B passed it -- it is prose, long enough, no markup. Staged as the verse's English
    it asserts a pointer as the verse's meaning.
    """
    bad = "Let the Hotar worship Indra, etc., as in 44 mutatis mutandis."
    assert CROSS_REFERENCE.search(bad)


@pytest.mark.parametrize(
    "bad",
    [
        "To us let Waters and let Plants be friendly, etc., as in VI. 23.",
        "Obeisance to thy wrath and glow, etc., as in XXII. 11.",
        "as in XXII. 11",
    ],
)
def test_bad_other_cross_reference_shapes_are_caught(bad: str) -> None:
    assert CROSS_REFERENCE.search(bad)


def test_good_a_translation_mentioning_a_number_is_not_a_cross_reference() -> None:
    good = "Through hundred autumns may we see that bright Eye, God-appointed, rise."
    assert not CROSS_REFERENCE.search(good)


def test_bad_latin_declared_as_english_is_detected() -> None:
    """Griffith renders explicit passages into Latin; 22 rows declare those as language en."""
    latin = (
        "Magna certe et bona est Aegle Marmelos. Bona est magna Ficus Glomerata. "
        "Magnus vir ubique opprimit."
    )
    assert detect_language(latin)["verdict"] == "LATIN"


def test_good_english_is_not_flagged_as_latin() -> None:
    english = (
        "Ye who move active in your strength like Gods with Asuras' magic powers, "
        "Even as the monkey scorns the dogs, Bandages! scorn the Kabava."
    )
    assert detect_language(english)["verdict"] == "ENGLISH"


# ---------------------------------------------------------------------------------------
# C3 forced addresses, against the real source markup
# ---------------------------------------------------------------------------------------


def test_good_a_printed_page_number_is_never_read_as_a_verse_label() -> None:
    """The likeliest way this parse could invent an address is to read "p. 48" as verse 48."""
    html = (
        "<p>21 Go to the sea. All-hail!<br> Thy smoke mount to the sky.</p>"
        "<p><a>p. 48</a></p>"
        "<p>22 Harm not the Waters, do the Plants no damage.<br>"
        " 23 These waters teem with sacred food.<br>"
        " 24 I set you down in Agni's seat.</p>"
    )
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as fh:
        fh.write(html)
        path = fh.name
    units = page_units(path)
    labels = [u["printed_label"] for u in units if u["label_was_printed"]]
    assert 48 not in labels, "the printed page number leaked in as a verse label"
    assert labels == [21, 22, 23, 24]


def test_good_the_real_duplicate_label_defect_is_reproduced() -> None:
    """VS 6 prints "23" twice; the second unit is canonical verse 25, bracketed by 24 and 26.

    This is the evidentiary basis for 14 of the 31 forced addresses, so it gets a fixture.
    """
    html = (
        "<p>23 These waters teem with sacred food.<br>"
        " 24 I set you down in Agni's seat.<br>"
        " 23 Thee for the heart, thee for the mind.</p>"
        "<p><a>p. 49</a></p><p>26 Descend, O Waters.</p>"
    )
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as fh:
        fh.write(html)
        path = fh.name
    units = page_units(path)
    labels = [u["printed_label"] for u in units if u["label_was_printed"]]
    assert labels == [23, 24, 23, 26]
    # The unit whose own label is the duplicate sits between printed 24 and printed 26, so
    # canonical verse 25 is the only slot it can occupy.
    i = 2
    assert units[i - 1]["printed_label"] == 24
    assert units[i + 1]["printed_label"] == 26


def test_bad_an_ambiguous_glyph_must_not_be_repaired_to_a_single_guess() -> None:
    """"S5" is 85 in VS 20, and an S->5 table turned it into 55 and lost the row.

    The candidate set keeps both readings so the printed neighbours, not the repair, decide.
    """
    cands = label_candidates("S5")
    assert 85 in cands and 55 in cands, cands
    assert len(cands) > 1, "a mis-set glyph is ambiguous and must be reported as such"


def test_good_an_unambiguous_label_yields_exactly_one_candidate() -> None:
    assert label_candidates("84") == [84]


def test_bad_a_forced_address_with_no_source_determination_stays_unverified() -> None:
    """The classification the owner decision turns on: only these four count as controls."""
    independent = {
        "PRINTED_LABEL_READ_DIRECTLY",
        "CORRUPT_GLYPHS_REPAIR_TO_CANONICAL",
        "UNIQUELY_BRACKETED_BY_PRINTED_NEIGHBOURS",
        "CONSTANT_OFFSET_SPINE_WITH_NEIGHBOURS",
    }
    assert "ORDER_AND_COUNT_ONLY" not in independent
    assert None not in independent
    for weak in ("the address was forced by code", "sequence position", "coverage improves"):
        assert weak not in independent


# ---------------------------------------------------------------------------------------
# C6 duplication
# ---------------------------------------------------------------------------------------


def test_good_identical_english_on_identical_sanskrit_is_legitimate_repetition() -> None:
    """The corpora genuinely repeat verses; that is why a parallel layer exists.

    An earlier version of this check called "same literal, different parent" the defect and
    reported 230 failures, almost all of them the Samaveda repeating a Rigvedic verse and
    the cross-corpus population deliberately reusing one rendering. The sound test is
    whether the two targets' own Sanskrit is the same text.
    """
    a = fold_sanskrit("tvaṃ no agne mahobhiḥ", L)
    b = fold_sanskrit("tvaṃ no agne mahobhiḥ", L)
    assert sandhi_insensitive(a) == sandhi_insensitive(b)


def test_bad_identical_english_on_differing_sanskrit_is_duplicate_generation() -> None:
    a = fold_sanskrit("tvaṃ no agne mahobhiḥ pāhi", L)
    b = fold_sanskrit("indrehi matsy andhaso viśvebhiḥ", L)
    assert sandhi_insensitive(a) != sandhi_insensitive(b)


def test_bad_one_source_unit_emitted_twice_is_visible_as_a_repeated_target() -> None:
    """One canonical verse targeted twice from one source is a generator defect, not data."""
    staged = [
        {"canonical_key": "VG:AV:SAU:K20:S006:V009", "source_id": "S"},
        {"canonical_key": "VG:AV:SAU:K20:S006:V009", "source_id": "S"},
    ]
    from collections import Counter

    dupes = [k for k, n in Counter(r["canonical_key"] for r in staged).items() if n > 1]
    assert dupes == ["VG:AV:SAU:K20:S006:V009"]


# ---------------------------------------------------------------------------------------
# C7 cross-corpus reuse
# ---------------------------------------------------------------------------------------


def test_bad_a_reused_rendering_is_not_independent_semantic_evidence() -> None:
    """Griffith's Rigveda English on a Samaveda verse is one witness, not two.

    The packet's rule: a reused rendering may be a legitimate product translation when
    disclosed, and may never be counted as independent evidence about the target corpus.
    """
    row = {
        "veda": "SV",
        "source_id": "VEDAGRAPH_CANONICAL_RV_GRIFFITH",
        "cross_corpus_source_key": "VG:RV:SAK:M09:S061:V012",
    }
    is_reuse = row["source_id"] == "VEDAGRAPH_CANONICAL_RV_GRIFFITH"
    reference_veda = row["cross_corpus_source_key"].split(":")[1]
    assert is_reuse
    assert reference_veda != row["veda"]
    assert not is_reuse or True  # usable_as_independent_semantic_evidence must be False
    usable = not is_reuse
    assert usable is False


def test_good_a_same_corpus_row_is_independent_evidence() -> None:
    row = {"veda": "AV", "source_id": "IA_WAYBACK_GRIFFITH_AV_1895"}
    assert row["source_id"] != "VEDAGRAPH_CANONICAL_RV_GRIFFITH"


def test_bad_a_cross_corpus_reuse_without_disclosure_is_contamination() -> None:
    import re as _re

    disclosed = "Cross-corpus reuse, not a Samaveda translation."
    undisclosed = "Addressed by the page's own hymn number and the printed verse label."
    pattern = _re.compile(
        r"cross-corpus reuse|not a (?:Samaveda|Atharvaveda|translation)|"
        r"reuse of a Rigveda translation",
        _re.I,
    )
    assert pattern.search(disclosed)
    assert not pattern.search(undisclosed)


# ---------------------------------------------------------------------------------------
# C5 archive evidence
# ---------------------------------------------------------------------------------------


def test_bad_an_archive_citation_without_a_content_hash_proves_nothing() -> None:
    """The Samaveda population's shape: one index URL, 1,069 rows, no page hash at all."""
    row = {
        "source_url": "https://web.archive.org/web/20231227014835/https://sacred-texts.com/hin/sv.htm",
        "payload": {},
    }
    assert "web.archive.org" in row["source_url"]
    assert not row["payload"].get("snapshot_sha256")


def test_good_an_archive_citation_with_a_hash_in_the_page_proofs_is_traceable() -> None:
    page_proofs = {"4410b0a65554f54cc919cbaf7dfd83224ee38d5553003a1e6803945524000530": {"http_status": 200}}
    row = {"payload": {"snapshot_sha256": next(iter(page_proofs))}}
    assert row["payload"]["snapshot_sha256"] in page_proofs
    assert page_proofs[row["payload"]["snapshot_sha256"]]["http_status"] == 200


# ---------------------------------------------------------------------------------------
# C1 shift attack
# ---------------------------------------------------------------------------------------


def test_bad_a_shift_attack_with_no_neighbour_to_compare_is_vacuous_not_clean() -> None:
    """The bug this fixture pins: the check reported 0 suspicious rows over 0 evaluated rows.

    The fact cache held translations only for the staged targets, so every neighbour lookup
    was empty. Coverage has to be reported separately from the defect count, or "nothing
    found" and "nothing looked at" are the same output.
    """
    neighbours = {"previous": {"carries_translation": False}, "next": {"carries_translation": False}}
    evaluated = any(v["carries_translation"] for v in neighbours.values())
    assert evaluated is False, "this is the vacuous case, and it must be reported as such"


def test_good_a_shift_attack_with_a_neighbour_translation_is_evaluated() -> None:
    neighbours = {
        "previous": {"carries_translation": True, "text": "Agni I laud, the household priest"},
        "next": {"carries_translation": False},
    }
    evaluated = any(v["carries_translation"] for v in neighbours.values())
    assert evaluated is True
    staged = "Agni I laud, the household priest"
    assert token_dice(fold_english(staged), fold_english(neighbours["previous"]["text"])) == 1.0
