"""The audio catalog's safety properties, stated as tests.

Every test here corresponds to a way the product could tell a reader something false about
a recording. The interesting ones are not "does the model parse" but "can the model be
made to accept the mislabelling", so most of these assert that a construction *fails*.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from vedagraph.product.audio.catalog import (
    AudioCatalog,
    ancestor_keys,
    scope_label,
    work_id_for_veda,
    write_catalog,
)
from vedagraph.product.audio.models import (
    SCOPE_TO_ENTITY_TYPES,
    VEDA_RECENSIONS,
    AudioRecord,
    AudioScope,
    AudioType,
    MappingConfidence,
    PlaybackMode,
)


def record(**overrides: object) -> AudioRecord:
    base: dict[str, object] = {
        "audio_id": "TEST:RV:one.mp3",
        "veda": "RV",
        "recension": "SAK",
        "scope_type": AudioScope.SUKTA,
        "scope_key": "VG:RV:SAK:M01:S001",
        "audio_type": AudioType.RECITATION,
        "title": "A recitation",
        "source_name": "A source",
        "source_page": "https://example.invalid/page",
        "media_url": "https://example.invalid/one.mp3",
        "mapping_method": "derived from the publisher's own one-file-per-sukta layout",
        "mapping_confidence": MappingConfidence.STRUCTURAL,
        "playback_mode": PlaybackMode.REMOTE_DIRECT,
    }
    base.update(overrides)
    return AudioRecord(**base)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Cross-recension safety
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("veda", "recension"),
    [
        ("YV", "TAI"),  # Taittiriya passing as this corpus's Yajurveda
        ("YV", "VSK"),  # Vajasaneyi-Kanva, the other Shukla recension
        ("SV", "JAI"),  # Jaiminiya passing as Kauthuma
        ("SV", "RAN"),  # Ranayaniya
        ("AV", "PAI"),  # Paippalada passing as Saunaka
        ("RV", "ASV"),  # Asvalayana
    ],
)
def test_a_foreign_recension_cannot_be_catalogued_as_ours(veda: str, recension: str) -> None:
    """The defect Section 7 of the release spec names: silent cross-recension mapping.

    Not a hypothetical. Archives routinely publish several recensions of one Veda side by
    side, so a discovery run that followed links rather than deriving from our own keys
    would collect all of them. The record must be impossible to construct, not merely
    flagged after the fact.
    """
    with pytest.raises(ValidationError, match="recension"):
        record(veda=veda, recension=recension)


def test_every_veda_has_exactly_one_accepted_recension() -> None:
    assert VEDA_RECENSIONS == {"RV": "SAK", "SV": "KAU", "YV": "VSM", "AV": "SAU"}


def test_an_unknown_veda_is_rejected() -> None:
    with pytest.raises(ValidationError, match="unknown veda"):
        record(veda="KYV", recension="TAI")


# ---------------------------------------------------------------------------
# Scope honesty
# ---------------------------------------------------------------------------


def test_unknown_scope_cannot_name_a_passage() -> None:
    """An UNKNOWN span with a key claims a position the source never stated."""
    with pytest.raises(ValidationError, match="UNKNOWN"):
        record(scope_type=AudioScope.UNKNOWN)


def test_a_structural_mapping_must_name_its_passage() -> None:
    with pytest.raises(ValidationError, match="STRUCTURAL"):
        record(scope_key=None)


def test_an_exact_mapping_must_name_its_passage() -> None:
    with pytest.raises(ValidationError, match="EXACT"):
        record(mapping_confidence=MappingConfidence.EXACT, scope_key=None)


def test_offsets_are_ordered() -> None:
    with pytest.raises(ValidationError, match="end_seconds"):
        record(
            mapping_confidence=MappingConfidence.EXACT,
            scope_type=AudioScope.MANTRA,
            scope_key="VG:RV:SAK:M01:S001:V001",
            start_seconds=30.0,
            end_seconds=12.0,
        )


def test_scope_to_entity_types_covers_every_scope() -> None:
    """A scope with no entry would silently skip the node-type check in the validator."""
    assert set(SCOPE_TO_ENTITY_TYPES) == set(AudioScope)


def test_a_sukta_scope_never_admits_a_mantra_node() -> None:
    assert "MANTRA" not in SCOPE_TO_ENTITY_TYPES[AudioScope.SUKTA]
    assert "HYMN" not in SCOPE_TO_ENTITY_TYPES[AudioScope.MANTRA]


# ---------------------------------------------------------------------------
# Playback integrity
# ---------------------------------------------------------------------------


def test_remote_playback_must_have_a_url() -> None:
    with pytest.raises(ValidationError, match="REMOTE_DIRECT"):
        record(media_url=None)


def test_local_playback_must_have_a_path() -> None:
    with pytest.raises(ValidationError, match="LOCAL_CACHE"):
        record(playback_mode=PlaybackMode.LOCAL_CACHE)


def test_embed_playback_must_have_an_embed_url() -> None:
    with pytest.raises(ValidationError, match="EXTERNAL_EMBED"):
        record(playback_mode=PlaybackMode.EXTERNAL_EMBED)


@pytest.mark.parametrize("bad", ["../../.env", "/etc/passwd", "\\windows\\system32", "a/../../b"])
def test_a_cache_path_cannot_escape_the_cache_root(bad: str) -> None:
    """Defence in depth: the service also confines the resolved path."""
    with pytest.raises(ValidationError):
        record(playback_mode=PlaybackMode.LOCAL_CACHE, local_cache_path=bad)


def test_local_copies_are_refused_unless_explicitly_permitted() -> None:
    """The cache tool's safety default lives on the record, not in the script."""
    assert record().local_copy_permitted is False


# ---------------------------------------------------------------------------
# Ancestry and resolution
# ---------------------------------------------------------------------------


def test_ancestor_keys_walk_up_and_stop_at_the_corpus_prefix() -> None:
    assert ancestor_keys("VG:RV:SAK:M01:S001:V003") == [
        "VG:RV:SAK:M01:S001",
        "VG:RV:SAK:M01",
    ]


def test_ancestor_keys_handle_the_deeper_samavedic_shape() -> None:
    assert ancestor_keys("VG:SV:KAU:UTTARA:P01:R01:D01:V01") == [
        "VG:SV:KAU:UTTARA:P01:R01:D01",
        "VG:SV:KAU:UTTARA:P01:R01",
        "VG:SV:KAU:UTTARA:P01",
        "VG:SV:KAU:UTTARA",
    ]


def test_ancestor_keys_of_a_top_container_is_empty() -> None:
    assert ancestor_keys("VG:RV:SAK:M01") == []


def test_resolving_a_mantra_finds_its_hymn_and_reports_the_distance() -> None:
    """The central behaviour: a verse's answer is its hymn's recording, and says so."""
    catalog = AudioCatalog([record()])
    matches = catalog.resolve("VG:RV:SAK:M01:S001:V003")
    assert len(matches) == 1
    assert matches[0].matched_key == "VG:RV:SAK:M01:S001"
    assert matches[0].levels_above == 1
    assert matches[0].is_own_level is False


def test_resolving_the_recorded_level_itself_reports_zero_distance() -> None:
    catalog = AudioCatalog([record()])
    match = catalog.resolve("VG:RV:SAK:M01:S001")[0]
    assert match.levels_above == 0
    assert match.is_own_level is True


def test_resolution_stops_at_the_nearest_level_that_answers() -> None:
    """A hymn recording and a mandala recording both cover a verse; only the nearer is
    returned, because offering both invites reading the coarser as an alternative."""
    catalog = AudioCatalog(
        [
            record(audio_id="TEST:hymn", scope_key="VG:RV:SAK:M01:S001"),
            record(
                audio_id="TEST:mandala",
                scope_type=AudioScope.SECTION,
                scope_key="VG:RV:SAK:M01",
            ),
        ]
    )
    matches = catalog.resolve("VG:RV:SAK:M01:S001:V003")
    assert [m.record.audio_id for m in matches] == ["TEST:hymn"]


def test_resolution_returns_nothing_rather_than_reaching_for_a_foreign_veda() -> None:
    catalog = AudioCatalog([record()])
    assert catalog.resolve("VG:AV:SAU:K01:S001:V001") == []


def test_unmapped_passage_resolves_to_nothing() -> None:
    assert AudioCatalog(()).resolve("VG:RV:SAK:M01:S001:V001") == []


def test_duplicate_audio_ids_are_refused() -> None:
    with pytest.raises(ValueError, match="duplicate audio_id"):
        AudioCatalog([record(), record()])


def test_work_id_for_veda_matches_the_expected_work_ids() -> None:
    assert work_id_for_veda("RV") == "VG:WORK:RV:SAK"
    assert work_id_for_veda("SV") == "VG:WORK:SV:KAU"
    assert work_id_for_veda("QQ") is None


def test_for_work_only_returns_that_works_veda() -> None:
    catalog = AudioCatalog(
        [
            record(),
            record(
                audio_id="TEST:YV",
                veda="YV",
                recension="VSM",
                scope_type=AudioScope.ADHYAYA,
                scope_key="VG:YV:VSM:A01",
            ),
        ]
    )
    assert {r.veda for r in catalog.for_work("VG:WORK:RV:SAK")} == {"RV"}
    assert catalog.for_work("VG:WORK:NOPE:XX") == ()


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def test_a_missing_catalog_is_an_empty_catalog_not_an_error(tmp_path: Path) -> None:
    """No audio is a supported product state, so audio must not break startup."""
    assert len(AudioCatalog.load(tmp_path / "absent.jsonl")) == 0


def test_a_malformed_catalog_line_is_an_error_naming_the_line(tmp_path: Path) -> None:
    """An absence is tolerated; a defect is not."""
    path = tmp_path / "bad.jsonl"
    path.write_text('{"audio_id": "x"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match=r"bad\.jsonl:1"):
        AudioCatalog.load(path)


def test_writing_the_same_records_twice_is_byte_identical(tmp_path: Path) -> None:
    """Discovery re-runs must produce an empty diff, or every run looks like a change."""
    path = tmp_path / "catalog.jsonl"
    records = [record(audio_id="TEST:b"), record(audio_id="TEST:a")]
    write_catalog(path, records)
    first = path.read_bytes()
    write_catalog(path, list(reversed(records)))
    assert path.read_bytes() == first


def test_written_catalog_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "catalog.jsonl"
    write_catalog(path, [record()])
    loaded = AudioCatalog.load(path)
    assert len(loaded) == 1
    assert loaded.records[0] == record()


def test_written_lines_are_sorted_by_audio_id(tmp_path: Path) -> None:
    path = tmp_path / "catalog.jsonl"
    write_catalog(path, [record(audio_id="TEST:z"), record(audio_id="TEST:a")])
    ids = [json.loads(line)["audio_id"] for line in path.read_text(encoding="utf-8").splitlines()]
    assert ids == sorted(ids)


# ---------------------------------------------------------------------------
# Reader-facing prose
# ---------------------------------------------------------------------------


def test_no_scope_label_claims_a_verse_unless_the_scope_is_a_verse() -> None:
    """Guards the phrasing that would produce "play this mantra" over a hymn's file."""
    for scope in AudioScope:
        label = scope_label(scope)
        if scope is not AudioScope.MANTRA:
            assert "verse" not in label, f"{scope} reads {label!r}"


def test_plural_scope_labels_read_as_a_class_not_a_demonstrative() -> None:
    """A work-level caveat aggregates a thousand recordings, so "this hymn" is wrong there.

    The defect: "These recordings cover structural spans -- this hymn -- and not
    individual verses."
    """
    from vedagraph.product.audio.catalog import scope_plural

    for scope in AudioScope:
        plural = scope_plural(scope)
        assert not plural.startswith("this "), f"{scope} reads {plural!r}"
    assert scope_plural(AudioScope.SUKTA) == "hymns"
