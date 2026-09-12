"""The VedSearch source: coordinate mapping, the Valakhilya permutation, text identity.

The tests that matter most here are the Mandala 8 ones. VedSearch numbers Rigvedic Mandala
8 in Griffith's order -- Valakhilya at the end of the book -- while this corpus numbers it
inline after Aufrecht, so a key-for-key mapping attaches the wrong recitation to 55 hymns.
That is a defect a listener notices immediately and no schema check would ever see, and it
is the reason the previous source's mappings were wrong in practice.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from vedagraph.product.audio.catalog import AudioCatalog
from vedagraph.product.audio.models import (
    AudioRecord,
    AudioScope,
    AudioType,
    MappingConfidence,
    PlaybackMode,
)
from vedagraph.product.audio.vedsearch import (
    API_SLUG,
    MATCH_MARGIN,
    MATCH_THRESHOLD,
    PAGE_SLUG,
    VerseCoordinates,
    audio_endpoint,
    best_text_match,
    has_sanskrit_audio,
    index_rows,
    row_coordinates,
    skeleton,
    vedsearch_coordinates,
    verse_matches,
    verse_page,
)


def record(**overrides: object) -> AudioRecord:
    base: dict[str, object] = {
        "audio_id": "VEDSEARCH:RV:1.1.1",
        "veda": "RV",
        "recension": "SAK",
        "scope_type": AudioScope.MANTRA,
        "scope_key": "VG:RV:SAK:M01:S001:V001",
        "audio_type": AudioType.RECITATION,
        "title": "Rigveda RV 1.1.1 - recitation of this verse",
        "source_name": "VedSearch",
        "source_page": "https://vedsearch.org/rigved/1/1/1",
        "media_url": "https://vedsearch.org/api/v1/attachment/audio/rigved/1.1.1/sanskrit",
        "mapping_method": "mapped by coordinates and confirmed against the recited text",
        "mapping_confidence": MappingConfidence.EXACT,
        "playback_mode": PlaybackMode.PROXIED_STREAM,
        "source_reference": "1.1.1",
        "text_verified": True,
    }
    base.update(overrides)
    return AudioRecord(**base)  # type: ignore[arg-type]


def coordinates(veda: str, key: str) -> VerseCoordinates:
    result = vedsearch_coordinates(veda, key)
    assert result is not None, f"{key} did not map"
    return result


# ---------------------------------------------------------------------------
# The Valakhilya permutation
# ---------------------------------------------------------------------------


def test_rigvedic_coordinates_apply_the_valakhilya_permutation() -> None:
    """Our 8.71 is the source's 8.60. This is the mapping that was wrong before."""
    assert coordinates("RV", "VG:RV:SAK:M08:S071:V001").shlok_id == "8.60.1"
    assert coordinates("RV", "VG:RV:SAK:M08:S060:V001").shlok_id == "8.49.1"
    assert coordinates("RV", "VG:RV:SAK:M08:S103:V001").shlok_id == "8.92.1"


def test_mandala_eight_below_the_valakhilya_is_unshifted() -> None:
    """Hymns 1-48 agree, so the transform must be the identity there."""
    assert coordinates("RV", "VG:RV:SAK:M08:S001:V001").shlok_id == "8.1.1"
    assert coordinates("RV", "VG:RV:SAK:M08:S048:V006").shlok_id == "8.48.6"


def test_the_valakhilya_hymns_map_past_the_end_of_the_source_book() -> None:
    """8.49-8.59 map to 8.93-8.103, which the source does not publish.

    So they resolve to no row, produce no record, and the reader gets no player -- rather
    than getting some other hymn's recitation.
    """
    assert coordinates("RV", "VG:RV:SAK:M08:S049:V001").sukta == 93
    assert coordinates("RV", "VG:RV:SAK:M08:S059:V001").sukta == 103


def test_other_mandalas_are_never_shifted() -> None:
    assert coordinates("RV", "VG:RV:SAK:M01:S001:V001").shlok_id == "1.1.1"
    assert coordinates("RV", "VG:RV:SAK:M10:S191:V004").shlok_id == "10.191.4"
    assert coordinates("RV", "VG:RV:SAK:M09:S060:V001").shlok_id == "9.60.1"


def test_the_permutation_is_injective_across_mandala_eight() -> None:
    """Two of our hymns landing on one of theirs would reuse one recitation twice."""
    mapped = [
        coordinates("RV", f"VG:RV:SAK:M08:S{number:03d}:V001").sukta for number in range(1, 104)
    ]
    assert len(set(mapped)) == len(mapped) == 103


# ---------------------------------------------------------------------------
# The other three Vedas
# ---------------------------------------------------------------------------


def test_atharvavedic_coordinates_are_direct() -> None:
    assert coordinates("AV", "VG:AV:SAU:K01:S001:V001").shlok_id == "1.1.1"
    assert coordinates("AV", "VG:AV:SAU:K20:S143:V009").shlok_id == "20.143.9"


def test_yajurvedic_coordinates_carry_the_constant_middle_field() -> None:
    """The Yajurveda has no sukta level; the source still emits a three-part id."""
    assert coordinates("YV", "VG:YV:VSM:A01:V001").shlok_id == "1.1.1"
    assert coordinates("YV", "VG:YV:VSM:A40:V017").shlok_id == "40.1.17"


def test_a_samavedic_key_has_no_coordinate_mapping() -> None:
    """Deliberate: the two numberings have no published correspondence, so the Samaveda
    is aligned by text or not at all."""
    assert vedsearch_coordinates("SV", "VG:SV:KAU:ARANYA:D01:V01") is None


@pytest.mark.parametrize(
    ("veda", "key"),
    [
        ("RV", "VG:RV:SAK:M01:S001"),  # a hymn, not a verse
        ("YV", "VG:YV:VSM:A01"),  # an adhyaya
        ("RV", "VG:RV:SAK:MXX:SYYY:VZZZ"),  # unparsable ordinals
        ("RV", "nonsense"),
        ("AV", ""),
    ],
)
def test_an_unmappable_key_yields_no_coordinates(veda: str, key: str) -> None:
    """No coordinates means no record, which is the safe direction to fail in."""
    assert vedsearch_coordinates(veda, key) is None


@pytest.mark.parametrize(
    ("veda", "key"),
    [
        ("YV", "VG:RV:SAK:M01:S001"),  # 5 segments, satisfies the YV length test
        ("RV", "VG:AV:SAU:K01:S001:V001"),  # 6 segments, satisfies the RV length test
        ("AV", "VG:RV:SAK:M01:S001:V001"),
    ],
)
def test_a_key_is_never_mapped_for_the_wrong_veda(veda: str, key: str) -> None:
    """A length check is not an identity check.

    ``VG:RV:SAK:M01:S001`` is five segments, which is the shape of a Yajurvedic mantra
    key, so a branch that tested only the length returned Yajurvedic adhyaya 1 verse 1 for
    a Rigvedic hymn -- a wrong-Veda mapping from a missing guard.
    """
    assert vedsearch_coordinates(veda, key) is None


# ---------------------------------------------------------------------------
# URLs
# ---------------------------------------------------------------------------


def test_the_atharvavedic_slug_differs_between_api_and_pages() -> None:
    """The site's own irregularity: pages are /atharvaved, the API path is atharved.

    Getting this wrong 404s every Atharvavedic file, which is 4,680 records.
    """
    assert API_SLUG["AV"] == "atharved"
    assert PAGE_SLUG["AV"] == "atharvaved"
    assert "/atharved/" in audio_endpoint("AV", "1.1.1")
    assert "/atharvaved/" in verse_page("AV", 1, 1, 1)


def test_the_audio_endpoint_requests_the_sanskrit_track() -> None:
    """Hindi is a spoken translation and must never be served as recitation."""
    assert audio_endpoint("RV", "1.1.1").endswith("/sanskrit")


# ---------------------------------------------------------------------------
# Text identity
# ---------------------------------------------------------------------------


def test_skeleton_ignores_the_notations_the_editions_disagree_on() -> None:
    """Accent marks, in three different notations, are not part of a verse's identity."""
    assert skeleton("a̱gnim ī̍le") == skeleton("agnim ile")
    assert skeleton("agním īḷe") == skeleton("agnim ile")


def test_skeleton_folds_devanagari_onto_latin() -> None:
    assert skeleton("अग्निम्") == skeleton("agnim")


def test_skeleton_drops_the_om_and_the_trailing_verse_number() -> None:
    """The source prefixes OM and suffixes a parenthesised numeral; this corpus does not."""
    assert skeleton("ॐ agnim (१)") == skeleton("agnim")


def test_skeleton_ignores_sandhi_word_splitting() -> None:
    """`agnim ile` against `agnimile` is a segmentation convention, not a variant verse."""
    assert skeleton("agnim ile purohitam") == skeleton("agnimile purohitam")


def test_verse_matches_accepts_an_orthographic_variant() -> None:
    matched, score = verse_matches(
        "gir mitra bhagam aditi nunam asyah", "gir mitram bhagam aditim nunam asyah"
    )
    assert matched is True
    assert score >= MATCH_THRESHOLD


def test_verse_matches_rejects_a_different_verse() -> None:
    """The Valakhilya failure mode reduced to its essence: two real but different verses."""
    matched, score = verse_matches(
        "tvam no agne mahobhih pahi visvasya arateh uta dviso martyasya",
        "agna a yahy agnibhir hotaram tva vrnimahe a tvam anaktu prayata",
    )
    assert matched is False
    assert score < MATCH_THRESHOLD


def test_verse_matches_refuses_an_empty_side() -> None:
    """A passage with no stored text must not match everything."""
    assert verse_matches("", "agnim ile")[0] is False
    assert verse_matches("agnim ile", "")[0] is False


def test_the_threshold_sits_well_clear_of_observed_wrong_pairs() -> None:
    """Calibration kept as an assertion, so loosening it has to be deliberate.

    Measured over all 1,975 Yajurvedic verses: correctly aligned pairs scored a median of
    0.995 and a 5th percentile of 0.973; 400 deliberately mispaired verses reached a
    maximum of 0.462.
    """
    assert MATCH_THRESHOLD >= 0.462 * 1.5
    assert MATCH_THRESHOLD <= 0.973
    assert MATCH_MARGIN > 0


# ---------------------------------------------------------------------------
# Ambiguity, which is the Samavedic hazard
# ---------------------------------------------------------------------------


def test_best_text_match_accepts_a_clear_winner() -> None:
    target = "agnim ile purohitam yajnasya devam rtvijam hotaram ratnadhatamam"
    candidates = {
        "right": skeleton(target),
        "wrong": skeleton("indram vardhanto apturah krnvanto visvam aryam apaghnanto"),
    }
    chosen, best, _ = best_text_match(target, candidates)
    assert chosen == "right"
    assert best >= MATCH_THRESHOLD


def test_best_text_match_refuses_a_hairs_breadth_winner() -> None:
    """Repeated Samavedic material must not be assigned on a negligible margin."""
    target = "agnim ile purohitam yajnasya devam rtvijam hotaram ratnadhatamam"
    candidates = {"a": skeleton(target), "b": skeleton(target + "m")}
    chosen, best, second = best_text_match(target, candidates)
    assert chosen is None
    assert best >= MATCH_THRESHOLD
    assert second >= MATCH_THRESHOLD


def test_best_text_match_finds_nothing_among_unrelated_candidates() -> None:
    chosen, _, _ = best_text_match(
        "agnim ile purohitam yajnasya",
        {"x": skeleton("indram vardhanto apturah krnvanto visvam aryam")},
    )
    assert chosen is None


def test_best_text_match_on_an_empty_target_matches_nothing() -> None:
    assert best_text_match("", {"x": skeleton("agnim ile")})[0] is None


# ---------------------------------------------------------------------------
# Row handling
# ---------------------------------------------------------------------------


def test_row_coordinates_read_the_fields_not_the_id_string() -> None:
    row = {"chapter_number": "8", "sukt_number": "60", "shlok_number": "1", "shlok_id": "wrong"}
    assert row_coordinates(row) == (8, 60, 1)


def test_a_malformed_row_yields_no_coordinates() -> None:
    assert row_coordinates({"chapter_number": "x"}) is None
    assert row_coordinates({}) is None


def test_index_rows_skips_rows_it_cannot_place() -> None:
    rows = [
        {"chapter_number": 1, "sukt_number": 1, "shlok_number": 1},
        {"chapter_number": "bad"},
    ]
    assert list(index_rows(rows)) == [(1, 1, 1)]


def test_only_a_sanskrit_flag_counts_as_recitation() -> None:
    """Hindi audio exists per verse and is a translation reading, not a recitation."""
    assert has_sanskrit_audio({"audio": {"sanskrit": True, "hindi": True}}) is True
    assert has_sanskrit_audio({"audio": {"sanskrit": False, "hindi": True}}) is False
    assert has_sanskrit_audio({"audio": {}}) is False
    assert has_sanskrit_audio({}) is False


# ---------------------------------------------------------------------------
# The record shape this source produces
# ---------------------------------------------------------------------------


def test_an_exact_mapping_requires_the_text_check_that_earns_it() -> None:
    with pytest.raises(ValidationError, match="text_verified"):
        record(text_verified=False)


def test_a_verified_exact_mapping_is_accepted() -> None:
    assert record().mapping_confidence is MappingConfidence.EXACT


def test_a_proxied_record_must_name_what_to_fetch() -> None:
    with pytest.raises(ValidationError, match="PROXIED_STREAM"):
        record(media_url=None)


def test_a_per_verse_record_covers_the_verse_itself() -> None:
    """The whole point of the change: distance zero, not a container's recording."""
    match = AudioCatalog([record()]).resolve("VG:RV:SAK:M01:S001:V001")[0]
    assert match.levels_above == 0
    assert match.is_own_level is True


def test_a_per_verse_record_does_not_answer_for_a_sibling_verse() -> None:
    """A verse's recording must not be offered for the verse next to it."""
    assert AudioCatalog([record()]).resolve("VG:RV:SAK:M01:S001:V002") == []
