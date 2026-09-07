"""Contract tests for the four-Veda structural model.

These lock the additive shared contracts introduced for Samaveda, Vajasaneyi and
Atharvaveda, and -- more importantly -- assert that adding them did not move any
Rigveda identity. See docs/FOUR_VEDA_STRUCTURAL_MODEL.md and ADR-017.
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from vedagraph.identity import (
    SamavedaCollection,
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
    """One key shape per collection, carrying exactly the levels that collection declares.

    The top level is the collection's NAME, not an ordinal. A bare ordinal did not denote
    a stable collection: slot-1 value ``2`` means Aranyarcika in the GRETIL/Pandey lineage
    and Uttararcika in six independent witnesses, a 1,225-verse referent collision.
    """
    chanda_key, chanda_urn, _ = sv_mantra_identity(
        SamavedaCollection.CHANDA, prapathaka=1, dasati=1, verse=1
    )
    assert chanda_key == "VG:SV:KAU:CHANDA:P01:D01:V01"
    assert chanda_urn == (
        "urn:vedagraph:mantra:samaveda:kauthuma:chanda:prapathaka:1:dasati:1:verse:1"
    )

    aranya_key, aranya_urn, _ = sv_mantra_identity(SamavedaCollection.ARANYA, dasati=3, verse=1)
    assert aranya_key == "VG:SV:KAU:ARANYA:D03:V01"
    assert aranya_urn == "urn:vedagraph:mantra:samaveda:kauthuma:aranya:dasati:3:verse:1"

    mahanamnya_key, mahanamnya_urn, _ = sv_mantra_identity(SamavedaCollection.MAHANAMNYA, verse=7)
    assert mahanamnya_key == "VG:SV:KAU:MAHANAMNYA:V07"
    assert mahanamnya_urn == "urn:vedagraph:mantra:samaveda:kauthuma:mahanamnya:verse:7"

    uttara_key, uttara_urn, _ = sv_mantra_identity(
        SamavedaCollection.UTTARA, prapathaka=1, ardha=1, dasati=1, verse=1
    )
    assert uttara_key == "VG:SV:KAU:UTTARA:P01:R01:D01:V01"
    assert uttara_urn == (
        "urn:vedagraph:mantra:samaveda:kauthuma:uttara:prapathaka:1:ardha:1:dasati:1:verse:1"
    )


def test_samaveda_omits_a_level_the_collection_does_not_declare() -> None:
    """A level a collection does not have is ABSENT from the key, never a literal 0.

    This test's premise is inverted from the one it replaces. The old scheme wrote
    ``VG:SV:KAU:A2:P00:R0:D03:V01`` for an Aranya verse and ``VG:SV:KAU:A3:P00:R0:D00:V07``
    for a Mahanamnya one, reasoning that ``0`` recorded "the edition marks this level
    absent". That was wrong twice over: the flat five-slot address is the rejected
    GRETIL/Pandey lineage's presentation, so writing ``0`` made one edition's flattening
    choice part of canonical identity -- and no witness declares a prapathaka or an ardha
    for these collections at all, so there is nothing there to number, not even with 0.
    """
    aranya_key, _, _ = sv_mantra_identity(SamavedaCollection.ARANYA, dasati=3, verse=1)
    assert aranya_key == "VG:SV:KAU:ARANYA:D03:V01"
    assert ":P" not in aranya_key
    assert ":R" not in aranya_key

    mahanamnya_key, _, _ = sv_mantra_identity(SamavedaCollection.MAHANAMNYA, verse=7)
    assert mahanamnya_key == "VG:SV:KAU:MAHANAMNYA:V07"
    assert mahanamnya_key.split(":")[3:] == ["MAHANAMNYA", "V07"]

    # An undeclared level cannot be supplied at all -- neither numbered nor zeroed -- and a
    # declared one cannot be omitted.
    for call in (
        lambda: sv_mantra_identity(SamavedaCollection.ARANYA, prapathaka=1, dasati=3, verse=1),
        lambda: sv_mantra_identity(
            SamavedaCollection.CHANDA, prapathaka=1, ardha=2, dasati=1, verse=1
        ),
        lambda: sv_mantra_identity(SamavedaCollection.MAHANAMNYA, dasati=1, verse=7),
        lambda: sv_container_identity(SamavedaCollection.ARANYA, prapathaka=0, dasati=3),
        lambda: sv_container_identity(SamavedaCollection.MAHANAMNYA, dasati=0),
        lambda: sv_mantra_identity(SamavedaCollection.CHANDA, prapathaka=1, verse=1),
    ):
        with pytest.raises(ValueError):
            call()


def test_samaveda_allows_a_third_ardha() -> None:
    """Uttararcika prapathakas 6-9 have three ardhas; depth is not uniform."""
    key, _, _ = sv_mantra_identity(
        SamavedaCollection.UTTARA, prapathaka=6, ardha=3, dasati=16, verse=2
    )
    assert key == "VG:SV:KAU:UTTARA:P06:R03:D16:V02"


def test_samaveda_refuses_identity_for_a_defective_verse_index() -> None:
    """A verse whose own index is 0 is a source defect and gets no canonical key.

    The old corpus coordinate ``(4, 6, 2, 16, 0)`` no longer exists as an address, so the
    synthetic invariants are asserted on Uttara, the collection that carries all three
    inner levels. The upper bound rides along: a value wider than the fixed key slot is
    refused, so the key width -- and with it lexicographic ordering -- cannot drift.
    """
    for call in (
        lambda: sv_mantra_identity(
            SamavedaCollection.UTTARA, prapathaka=6, ardha=2, dasati=16, verse=0
        ),
        lambda: sv_mantra_identity(
            SamavedaCollection.UTTARA, prapathaka=6, ardha=2, dasati=16, verse=-1
        ),
        lambda: sv_mantra_identity(
            SamavedaCollection.UTTARA, prapathaka=-1, ardha=2, dasati=16, verse=1
        ),
        lambda: sv_mantra_identity(
            SamavedaCollection.UTTARA, prapathaka=6, ardha=2, dasati=16, verse=100
        ),
        lambda: sv_mantra_identity(
            SamavedaCollection.UTTARA, prapathaka=100, ardha=2, dasati=16, verse=1
        ),
    ):
        with pytest.raises(ValueError):
            call()


def test_samaveda_container_truncates_at_variable_depth() -> None:
    chanda = SamavedaCollection.CHANDA
    assert sv_container_identity(chanda)[0] == "VG:SV:KAU:CHANDA"
    assert sv_container_identity(chanda, prapathaka=1)[0] == "VG:SV:KAU:CHANDA:P01"
    assert sv_container_identity(chanda, prapathaka=1, dasati=7)[0] == "VG:SV:KAU:CHANDA:P01:D07"
    uttara = SamavedaCollection.UTTARA
    assert sv_container_identity(uttara)[0] == "VG:SV:KAU:UTTARA"
    assert sv_container_identity(uttara, prapathaka=1)[0] == "VG:SV:KAU:UTTARA:P01"
    assert sv_container_identity(uttara, prapathaka=1, ardha=2)[0] == "VG:SV:KAU:UTTARA:P01:R02"
    assert sv_container_identity(uttara, prapathaka=1, ardha=2, dasati=7)[0] == (
        "VG:SV:KAU:UTTARA:P01:R02:D07"
    )


def test_samaveda_container_distinguishes_undeclared_from_unaddressed() -> None:
    """Two different facts, and neither of them is spelt ``0`` any more.

    The old scheme wrote both into the same five-slot address: ``P00`` meant "the source
    marks this level absent" and a missing argument meant "not addressed". Now a level the
    collection does not declare cannot be supplied at all, and a level it does declare but
    that the caller did not supply simply truncates the key.
    """
    with pytest.raises(ValueError):
        sv_container_identity(SamavedaCollection.ARANYA, prapathaka=1, dasati=3)
    addressed_key, addressed_urn, _ = sv_container_identity(SamavedaCollection.ARANYA, dasati=3)
    assert addressed_key == "VG:SV:KAU:ARANYA:D03"
    assert addressed_urn.endswith("aranya:dasati:3")
    unaddressed_key, _, _ = sv_container_identity(SamavedaCollection.ARANYA)
    assert unaddressed_key == "VG:SV:KAU:ARANYA"
    assert addressed_key != unaddressed_key


def test_samaveda_container_rejects_a_gap_in_the_level_chain() -> None:
    with pytest.raises(ValueError):
        sv_container_identity(SamavedaCollection.UTTARA, prapathaka=None, ardha=2)


def test_samaveda_container_and_mantra_urns_cannot_collide() -> None:
    container = sv_container_identity(SamavedaCollection.UTTARA, prapathaka=1, ardha=1, dasati=1)[1]
    mantra = sv_mantra_identity(
        SamavedaCollection.UTTARA, prapathaka=1, ardha=1, dasati=1, verse=1
    )[1]
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


def test_no_work_may_pass_zero_for_a_hierarchy_level() -> None:
    """The positive-integer rule is uniform across all four works. Nothing may pass 0.

    Samaveda used to be the documented exception: the rejected witness wrote a literal 0
    for a level its collection does not have, and identity applied a non-negative rule to
    the inner levels to accommodate it. The collection-keyed model omits the level instead,
    so 0 is no longer a legal value for Samaveda either.
    """
    for call in (
        lambda: vsm_adhyaya_identity(0),
        lambda: avs_kanda_identity(0),
        lambda: avs_sukta_identity(1, 0),
        lambda: sv_container_identity(SamavedaCollection.CHANDA, prapathaka=0),
        lambda: sv_container_identity(SamavedaCollection.UTTARA, prapathaka=1, ardha=0),
        lambda: sv_mantra_identity(SamavedaCollection.ARANYA, dasati=0, verse=1),
        lambda: sv_mantra_identity(SamavedaCollection.MAHANAMNYA, verse=0),
    ):
        with pytest.raises(ValueError):
            call()


# ---------------------------------------------------------- cross-work URN separation


def test_no_two_works_share_a_mantra_urn_or_uuid() -> None:
    identities = [
        rv_mantra_identity(1, 1, 1),
        vsm_mantra_identity(1, 1),
        avs_mantra_identity(1, 1, 1),
        sv_mantra_identity(SamavedaCollection.CHANDA, prapathaka=1, dasati=1, verse=1),
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


def test_structural_path_preserves_zero_padding_and_variable_depth() -> None:
    """Samaveda needs the padded, depth-varying path to survive as written.

    Rebuilt on the Aranya collection, whose address is two levels deep where Uttara's is
    four. It previously used the flattened five-slot Aranya address ``A2:P00:R0:D03:V01``;
    the zero-padding requirement is unchanged, but depth now varies by OMITTING a level
    the collection does not declare rather than by zeroing it.
    """
    key, urn, identifier = sv_mantra_identity(SamavedaCollection.ARANYA, dasati=3, verse=1)
    passage = Passage(
        entity_id=identifier,
        canonical_key=key,
        canonical_urn=urn,
        entity_type=EntityType.MANTRA,
        work_id="VG:WORK:SV:KAU",
        hierarchy={"collection": "ARANYA", "dasati": 3, "verse": 1},
        canonical_citation="SV Aranya 3.1",
        sequence_in_parent=1,
        native_labels=["Collection", "Dasati", "Verse"],
        structural_path=["ARANYA", "03", "01"],
    )
    assert passage.structural_path == ["ARANYA", "03", "01"]
    assert passage.entity_type == EntityType.MANTRA


def test_samaveda_container_passage_uses_the_generic_entity_type() -> None:
    key, urn, identifier = sv_container_identity(SamavedaCollection.CHANDA, prapathaka=1, dasati=7)
    passage = Passage(
        entity_id=identifier,
        canonical_key=key,
        canonical_urn=urn,
        entity_type=EntityType.STRUCTURAL_CONTAINER,
        work_id="VG:WORK:SV:KAU",
        hierarchy={"collection": "CHANDA", "prapathaka": 1, "dasati": 7},
        canonical_citation="SV Chanda 1.7",
        sequence_in_parent=7,
        native_labels=["Collection", "Prapathaka", "Dasati"],
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


def test_section_discovery_covers_a_samaveda_container_at_variable_depth() -> None:
    """Discovery names the level the collection declares, at whatever depth that is.

    This replaces ``test_section_discovery_allows_zero_for_an_absent_samaveda_level``,
    which asserted ``VG:SV:KAU:A2:P00`` with ``section_number=0`` on the reasoning that 0
    recorded a level the edition marks absent. No Samaveda key writes 0 any more: the
    Aranya collection's only container level is the dasati, and its prapathaka is omitted
    rather than zeroed, so a discovery record has nothing to number 0.
    """
    record = SectionDiscoveryRecord(
        work_id="VG:WORK:SV:KAU",
        canonical_section_key=sv_container_identity(SamavedaCollection.ARANYA, dasati=3)[0],
        section_level="Dasati",
        section_number=3,
        parent_key=sv_container_identity(SamavedaCollection.ARANYA)[0],
        availability=DiscoveryAvailability.AVAILABLE,
        discovery_source="GRETIL",
        source_id="GRETIL",
        source_locator="aranya arcika dasati 3",
        snapshot_id="GRETIL:deadbeef",
    )
    assert record.canonical_section_key == "VG:SV:KAU:ARANYA:D03"
    assert record.parent_key == "VG:SV:KAU:ARANYA"
    assert record.section_number == 3


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
