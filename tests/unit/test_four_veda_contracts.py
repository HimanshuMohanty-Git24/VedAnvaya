"""Contract tests for the four-Veda structural model.

These lock the additive shared contracts introduced for Samaveda, Vajasaneyi and
Atharvaveda, and -- more importantly -- assert that adding them did not move any
Rigveda identity. See docs/FOUR_VEDA_STRUCTURAL_MODEL.md and ADR-017.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from vedagraph.identity import (
    avs_kanda_identity,
    avs_mantra_identity,
    avs_sukta_identity,
    rv_mandala_identity,
    rv_mantra_identity,
    rv_sukta_identity,
    sv_container_identity,
    sv_mantra_identity,
    uuid_for_urn,
    vsm_adhyaya_identity,
    vsm_mantra_identity,
)
from vedagraph.models import Passage, SectionDiscoveryRecord, WorkBuildConfig
from vedagraph.models.enums import (
    AlignmentLevel,
    DiscoveryAvailability,
    EntityType,
    RightsStatus,
    TextSelectionPolicy,
)

# --------------------------------------------------------------------------- enums


def test_rigveda_enum_members_are_not_renamed_or_removed() -> None:
    """The sealed Rigveda corpus serialises these strings; they are permanent."""
    assert {member.value for member in EntityType} >= {"WORK", "SECTION", "HYMN", "MANTRA"}
    assert {member.value for member in AlignmentLevel} >= {"WORK", "SECTION", "HYMN", "MANTRA"}
    assert {member.value for member in RightsStatus} >= {
        "PUBLIC_DOMAIN",
        "CC_BY",
        "CC_BY_SA",
        "CC_BY_NC",
        "CC_BY_NC_SA",
        "APACHE_2_0",
        "PERMISSION_GRANTED",
        "PERMISSION_REQUIRED",
        "RESEARCH_ONLY",
        "REFERENCE_ONLY",
        "EXTERNAL_REFERENCE_ONLY",
        "UNKNOWN",
    }


def test_additive_enum_members_exist() -> None:
    assert EntityType.STRUCTURAL_CONTAINER == "STRUCTURAL_CONTAINER"
    assert AlignmentLevel.STRUCTURAL_CONTAINER == "STRUCTURAL_CONTAINER"
    assert RightsStatus.CC0 == "CC0"


def test_cc0_is_distinct_from_public_domain() -> None:
    """A CC0 waiver and a work that is public domain by law are different facts."""
    assert RightsStatus.CC0 != RightsStatus.PUBLIC_DOMAIN


# ------------------------------------------------------------------ Samaveda identity


def test_samaveda_key_encodes_the_native_hierarchy() -> None:
    key, urn, _ = sv_mantra_identity(1, 1, 1, 1, 1)
    assert key == "VG:SV:KAU:A1:P01:R1:D01:V01"
    assert urn == (
        "urn:vedagraph:mantra:samaveda:kauthuma:arcika:1:prapathaka:1:ardha:1:dasati:1:verse:1"
    )


def test_samaveda_accepts_zero_for_a_level_the_edition_marks_absent() -> None:
    """The Aranya and Mahanamnya arcikas genuinely lack levels; 0 is not an error.

    Applying the positive-integer rule here would reject 65 real verses.
    """
    aranya_key, _, _ = sv_mantra_identity(2, 0, 0, 3, 1)
    assert aranya_key == "VG:SV:KAU:A2:P00:R0:D03:V01"
    mahanamnya_key, _, _ = sv_mantra_identity(3, 0, 0, 0, 7)
    assert mahanamnya_key == "VG:SV:KAU:A3:P00:R0:D00:V07"


def test_samaveda_allows_a_third_ardha() -> None:
    """Uttararcika prapathakas 6-9 have three ardhas; depth is not uniform."""
    key, _, _ = sv_mantra_identity(4, 6, 3, 16, 2)
    assert key == "VG:SV:KAU:A4:P06:R3:D16:V02"


def test_samaveda_refuses_identity_for_a_defective_verse_index() -> None:
    """A verse whose own index is 0 is a source defect and gets no canonical key."""
    with pytest.raises(ValueError):
        sv_mantra_identity(4, 6, 2, 16, 0)
    with pytest.raises(ValueError):
        sv_mantra_identity(0, 1, 1, 1, 1)
    with pytest.raises(ValueError):
        sv_mantra_identity(1, -1, 1, 1, 1)


def test_samaveda_container_truncates_at_variable_depth() -> None:
    assert sv_container_identity(1)[0] == "VG:SV:KAU:A1"
    assert sv_container_identity(1, 1)[0] == "VG:SV:KAU:A1:P01"
    assert sv_container_identity(1, 1, 2)[0] == "VG:SV:KAU:A1:P01:R2"
    assert sv_container_identity(1, 1, 2, 7)[0] == "VG:SV:KAU:A1:P01:R2:D07"


def test_samaveda_container_distinguishes_absent_from_unaddressed() -> None:
    """``0`` means the source marks the level absent; ``None`` means not addressed."""
    absent_key, absent_urn, _ = sv_container_identity(2, 0, 0, 3)
    assert absent_key == "VG:SV:KAU:A2:P00:R0:D03"
    assert absent_urn.endswith("arcika:2:prapathaka:0:ardha:0:dasati:3")
    unaddressed_key, _, _ = sv_container_identity(2)
    assert unaddressed_key == "VG:SV:KAU:A2"
    assert absent_key != unaddressed_key


def test_samaveda_container_rejects_a_gap_in_the_level_chain() -> None:
    with pytest.raises(ValueError):
        sv_container_identity(1, None, 2)


def test_samaveda_container_and_mantra_urns_cannot_collide() -> None:
    container = sv_container_identity(1, 1, 1, 1)[1]
    mantra = sv_mantra_identity(1, 1, 1, 1, 1)[1]
    assert container != mantra
    assert ":section:" in container
    assert ":mantra:" in mantra


# ---------------------------------------------------- Vajasaneyi / Atharvaveda identity


def test_vajasaneyi_adhyaya_identity() -> None:
    key, urn, identifier = vsm_adhyaya_identity(7)
    assert key == "VG:YV:VSM:A07"
    assert urn == "urn:vedagraph:section:yajurveda:vajasaneyi-madhyandina:adhyaya:7"
    assert identifier == uuid_for_urn(urn)


def test_vajasaneyi_adhyaya_and_mantra_keys_do_not_collide() -> None:
    assert vsm_adhyaya_identity(7)[0] != vsm_mantra_identity(7, 1)[0]
    assert vsm_adhyaya_identity(7)[2] != vsm_mantra_identity(7, 1)[2]


def test_atharvaveda_container_identity() -> None:
    kanda_key, kanda_urn, kanda_id = avs_kanda_identity(15)
    assert kanda_key == "VG:AV:SAU:K15"
    assert kanda_urn == "urn:vedagraph:section:atharvaveda:shaunaka:kanda:15"
    assert kanda_id == uuid_for_urn(kanda_urn)
    sukta_key, sukta_urn, sukta_id = avs_sukta_identity(15, 2)
    assert sukta_key == "VG:AV:SAU:K15:S002"
    assert sukta_urn == "urn:vedagraph:hymn:atharvaveda:shaunaka:kanda:15:sukta:2"
    assert sukta_id == uuid_for_urn(sukta_urn)


def test_atharvaveda_levels_do_not_collide() -> None:
    keys = {
        avs_kanda_identity(1)[0],
        avs_sukta_identity(1, 1)[0],
        avs_mantra_identity(1, 1, 1)[0],
    }
    assert len(keys) == 3


def test_container_identity_keeps_positive_integer_rule_outside_samaveda() -> None:
    """Only Samaveda's edition encodes absence as 0. Nothing else may pass 0."""
    for call in (
        lambda: vsm_adhyaya_identity(0),
        lambda: avs_kanda_identity(0),
        lambda: avs_sukta_identity(1, 0),
    ):
        with pytest.raises(ValueError):
            call()


# ---------------------------------------------------------- cross-work URN separation


def test_no_two_works_share_a_mantra_urn_or_uuid() -> None:
    identities = [
        rv_mantra_identity(1, 1, 1),
        vsm_mantra_identity(1, 1),
        avs_mantra_identity(1, 1, 1),
        sv_mantra_identity(1, 1, 1, 1, 1),
    ]
    assert len({item[0] for item in identities}) == 4
    assert len({item[1] for item in identities}) == 4
    assert len({item[2] for item in identities}) == 4


def test_rigveda_identity_is_unchanged_by_the_four_veda_work() -> None:
    """Hard-coded expected values: these must never move for any reason."""
    assert rv_mandala_identity(1)[0] == "VG:RV:SAK:M01"
    assert rv_sukta_identity(1, 1)[0] == "VG:RV:SAK:M01:S001"
    key, urn, identifier = rv_mantra_identity(1, 1, 1)
    assert key == "VG:RV:SAK:M01:S001:V001"
    assert urn == "urn:vedagraph:mantra:rigveda:shakala:mandala:1:sukta:1:mantra:1"
    assert str(identifier) == "141a362f-1690-5244-831d-e0304db2fdc8"


# ------------------------------------------------------------------- Passage contract


def _passage(**overrides: object) -> Passage:
    key, urn, identifier = rv_mantra_identity(1, 1, 1)
    payload: dict[str, object] = {
        "entity_id": identifier,
        "canonical_key": key,
        "canonical_urn": urn,
        "entity_type": EntityType.MANTRA,
        "work_id": "VG:WORK:RV:SAK",
        "hierarchy": {"mandala": 1, "sukta": 1, "mantra": 1},
        "canonical_citation": "RV 1.1.1",
        "sequence_in_parent": 1,
    }
    payload.update(overrides)
    return Passage.model_validate(payload)


def test_new_passage_fields_are_optional_and_default_empty() -> None:
    """A record written before these fields existed must still validate."""
    passage = _passage()
    assert passage.native_labels == []
    assert passage.structural_path == []


def test_native_labels_must_name_exactly_the_hierarchy_levels() -> None:
    _passage(native_labels=["Mandala", "Sukta", "Mantra"])
    with pytest.raises(ValueError):
        _passage(native_labels=["Mandala", "Sukta"])
    with pytest.raises(ValueError):
        _passage(native_labels=["Mandala", "Sukta", "Kanda"])
    with pytest.raises(ValueError):
        _passage(native_labels=["Mandala", "Mandala", "Mantra"])


def test_structural_path_must_align_with_native_labels() -> None:
    passage = _passage(
        native_labels=["Mandala", "Sukta", "Mantra"], structural_path=["1", "1", "1"]
    )
    assert passage.structural_path == ["1", "1", "1"]
    with pytest.raises(ValueError):
        _passage(native_labels=["Mandala", "Sukta", "Mantra"], structural_path=["1", "1"])
    with pytest.raises(ValueError):
        _passage(structural_path=["1", "1", "1"])


def test_structural_path_preserves_zero_padding_and_absent_levels() -> None:
    """Samaveda needs the padded, depth-varying path to survive as written."""
    key, urn, identifier = sv_mantra_identity(2, 0, 0, 3, 1)
    passage = Passage(
        entity_id=identifier,
        canonical_key=key,
        canonical_urn=urn,
        entity_type=EntityType.MANTRA,
        work_id="VG:WORK:SV:KAU",
        hierarchy={"arcika": 2, "prapathaka": 0, "ardha": 0, "dasati": 3, "verse": 1},
        canonical_citation="SV 2.0.0.3.1",
        sequence_in_parent=1,
        native_labels=["Arcika", "Prapathaka", "Ardha", "Dasati", "Verse"],
        structural_path=["2", "00", "0", "03", "01"],
    )
    assert passage.structural_path == ["2", "00", "0", "03", "01"]
    assert passage.entity_type == EntityType.MANTRA


def test_samaveda_container_passage_uses_the_generic_entity_type() -> None:
    key, urn, identifier = sv_container_identity(1, 1, 2, 7)
    passage = Passage(
        entity_id=identifier,
        canonical_key=key,
        canonical_urn=urn,
        entity_type=EntityType.STRUCTURAL_CONTAINER,
        work_id="VG:WORK:SV:KAU",
        hierarchy={"arcika": 1, "prapathaka": 1, "ardha": 2, "dasati": 7},
        canonical_citation="SV 1.1.2.7",
        sequence_in_parent=7,
        native_labels=["Arcika", "Prapathaka", "Ardha", "Dasati"],
    )
    assert passage.entity_type == EntityType.STRUCTURAL_CONTAINER
    assert "Dasati" in passage.native_labels


def test_passage_still_forbids_unknown_fields() -> None:
    with pytest.raises(ValueError):
        _passage(invented_field="nope")


# --------------------------------------------------------- generic records for B/C/D


def test_section_discovery_record_covers_a_work_without_a_sukta_level() -> None:
    record = SectionDiscoveryRecord(
        work_id="VG:WORK:YV:VSM",
        canonical_section_key="VG:YV:VSM:A07",
        section_level="Adhyaya",
        section_number=7,
        parent_key=None,
        known_child_count=48,
        availability=DiscoveryAvailability.AVAILABLE,
        discovery_source="GRETIL",
        source_id="GRETIL",
        source_locator="adhyaya 7",
        snapshot_id="GRETIL:deadbeef",
    )
    assert record.section_level == "Adhyaya"
    assert record.known_child_count == 48


def test_section_discovery_allows_zero_for_an_absent_samaveda_level() -> None:
    record = SectionDiscoveryRecord(
        work_id="VG:WORK:SV:KAU",
        canonical_section_key="VG:SV:KAU:A2:P00",
        section_level="Prapathaka",
        section_number=0,
        availability=DiscoveryAvailability.AVAILABLE,
        discovery_source="GRETIL",
        source_id="GRETIL",
        source_locator="aranya arcika",
        snapshot_id="GRETIL:deadbeef",
    )
    assert record.section_number == 0


def test_work_build_config_expresses_a_work_with_no_mandala() -> None:
    config = WorkBuildConfig(
        config_version="1.0.0",
        dataset_id="vsm_pilot",
        release_version="0.1.0",
        work_id="VG:WORK:YV:VSM",
        section_level="Adhyaya",
        selected_sections=[3, 1, 2],
        mantra_level="Mantra",
        text_selection_policy=TextSelectionPolicy.ORIGINAL,
        sources=[],
        reconciliation_policy_version="rp-v1",
        output_location="data/canonical/vsm_pilot",
        build_timestamp=datetime.now(UTC),
    )
    assert config.selected_sections == [1, 2, 3]
    assert config.mantra_level == "Mantra"


def test_work_build_config_requires_a_named_section_level_when_slicing() -> None:
    with pytest.raises(ValueError):
        WorkBuildConfig(
            config_version="1.0.0",
            dataset_id="bad",
            release_version="0.1.0",
            work_id="VG:WORK:SV:KAU",
            selected_sections=[1],
            text_selection_policy=TextSelectionPolicy.ORIGINAL,
            sources=[],
            reconciliation_policy_version="rp-v1",
            output_location="data/canonical/bad",
            build_timestamp=datetime.now(UTC),
        )


def test_work_build_config_rejects_duplicate_sections() -> None:
    with pytest.raises(ValueError):
        WorkBuildConfig(
            config_version="1.0.0",
            dataset_id="bad",
            release_version="0.1.0",
            work_id="VG:WORK:SV:KAU",
            section_level="Prapathaka",
            selected_sections=[1, 1],
            text_selection_policy=TextSelectionPolicy.ORIGINAL,
            sources=[],
            reconciliation_policy_version="rp-v1",
            output_location="data/canonical/bad",
            build_timestamp=datetime.now(UTC),
        )


def test_translation_may_align_to_a_container_that_is_not_a_hymn() -> None:
    """Vajasaneyi has no hymn level, so it must never claim HYMN alignment."""
    from vedagraph.models import Translation

    translation = Translation(
        translation_id=uuid4(),
        passage_id=uuid4(),
        language="en",
        translator="Example",
        work_edition="Example edition",
        text="placeholder",
        source_id="GRETIL",
        rights_status=RightsStatus.PUBLIC_DOMAIN,
        alignment_level=AlignmentLevel.STRUCTURAL_CONTAINER,
        quality_status="UNREVIEWED",
    )
    assert translation.alignment_level == AlignmentLevel.STRUCTURAL_CONTAINER


def test_extracted_layer_role_exists_and_is_not_primary() -> None:
    """A layer whose extent is an editorial judgement must not be PRIMARY_TEXT.

    A Vajasaneyi layer built by lifting mantra quotations out of a commentary block has
    boundaries the source never declared. Labelling it PRIMARY_TEXT would make an
    interpretive segmentation canonical; NORMALIZED and LINGUISTIC_ANNOTATION would both
    be false claims about what was done to it.
    """
    from vedagraph.models.enums import TextRole

    assert TextRole.EXTRACTED_FROM_CONTAINER == "EXTRACTED_FROM_CONTAINER"
    assert TextRole.EXTRACTED_FROM_CONTAINER is not TextRole.PRIMARY_TEXT
    # The pre-existing role vocabulary is unchanged.
    assert {member.value for member in TextRole} >= {
        "PRIMARY_TEXT",
        "PARALLEL_TEXT",
        "PADAPATHA",
        "METRICALLY_RESTORED",
        "NORMALIZED",
        "SEARCH_DERIVATIVE",
        "DISPLAY_DERIVATIVE",
        "LINGUISTIC_ANNOTATION",
        "COMPARISON_ONLY",
        "REFERENCE_ONLY",
    }
