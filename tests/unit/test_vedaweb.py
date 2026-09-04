"""VedaWeb TEI parsing, per-version licences, and commit pinning."""

from pathlib import Path

import pytest

from vedagraph.config.registry import load_source_artifacts, load_text_versions
from vedagraph.ingest.adapters import VedaWebAdapter, VedaWebCorpusHeader
from vedagraph.ingest.adapters.vedaweb import SANSKRIT_VERSIONS, rights_status_for
from vedagraph.models import SourceArtifact
from vedagraph.models.enums import RightsStatus, TextForm, TextRole

FIXTURES = Path("tests/fixtures/vedaweb")
BOOK = FIXTURES / "rv_book_01_sample.tei"
HEADER = FIXTURES / "vedaweb_corpus_sample.tei"
ARTIFACT = "VEDAWEB.RV.BOOK01.TEI.D3EB8AF"


def test_book_tei_yields_one_record_per_version_per_stanza() -> None:
    records = VedaWebAdapter(source_artifact_id=ARTIFACT).parse_versions(
        BOOK, snapshot_id="fixture"
    )
    versions = {record.text_version_id for record in records}
    assert versions == {f"{ARTIFACT}#{name}" for name in SANSKRIT_VERSIONS}
    assert {int(record.hierarchy["mantra"]) for record in records} == {1, 2}
    assert all(int(record.hierarchy["mandala"]) == 1 for record in records)
    assert all(int(record.hierarchy["sukta"]) == 1 for record in records)


def test_translation_layers_are_never_read_as_sanskrit() -> None:
    records = VedaWebAdapter(source_artifact_id=ARTIFACT).parse_versions(
        BOOK, snapshot_id="fixture"
    )
    assert all(record.language == "sa" for record in records)
    assert not any("Laud Agni" in record.text_original for record in records)


def test_versions_carry_distinct_readings_and_declared_roles() -> None:
    records = VedaWebAdapter(source_artifact_id=ARTIFACT).parse_versions(
        BOOK, snapshot_id="fixture"
    )
    by_version = {
        (record.text_version_id or "").rsplit("#", 1)[-1]: record
        for record in records
        if int(record.hierarchy["mantra"]) == 1
    }
    assert by_version["aufrecht"].text_original != by_version["padapatha"].text_original
    assert by_version["padapatha"].text_role == TextRole.PADAPATHA
    assert by_version["vnh"].text_role == TextRole.METRICALLY_RESTORED
    assert by_version["zurich"].text_role == TextRole.LINGUISTIC_ANNOTATION
    assert by_version["eichler"].script == "Devanagari"
    assert by_version["aufrecht"].script == "Latin"
    assert not by_version["padapatha"].accented
    assert by_version["aufrecht"].accented


def test_token_annotation_lines_never_leak_into_text() -> None:
    records = VedaWebAdapter(source_artifact_id=ARTIFACT, versions=("zurich",)).parse_versions(
        BOOK, snapshot_id="fixture"
    )
    assert records[0].text_original == (
        "agním īḷe puróhitaṃ yajñásya devám r̥tvíjam hótāraṃ ratnadhā́tamam"
    )


def test_sukta_filter_is_applied() -> None:
    records = VedaWebAdapter(source_artifact_id=ARTIFACT).parse_versions(
        BOOK, snapshot_id="fixture", suktas=frozenset({99})
    )
    assert records == []


def test_unknown_version_is_rejected_rather_than_ignored() -> None:
    with pytest.raises(ValueError, match="unknown VedaWeb Sanskrit versions"):
        VedaWebAdapter(source_artifact_id=ARTIFACT, versions=("griffith",))


def test_corpus_header_exposes_a_licence_per_source_not_per_repository() -> None:
    entries = {item["source_version_key"]: item for item in VedaWebCorpusHeader().parse(HEADER)}
    assert entries["zurich"]["license_uri"] == "https://creativecommons.org/licenses/by/4.0/"
    assert (
        entries["aufrecht"]["license_uri"] == "https://creativecommons.org/licenses/by-nc-sa/4.0/"
    )
    assert entries["zurich"]["license_uri"] != entries["aufrecht"]["license_uri"]


def test_upstream_notices_are_preserved_alongside_the_creative_commons_licence() -> None:
    entries = {item["source_version_key"]: item for item in VedaWebCorpusHeader().parse(HEADER)}
    gretil_notice = " ".join(str(note) for note in entries["aufrecht"]["upstream_rights_notes"])
    assert "provided to GRETIL in good faith" in gretil_notice
    vnh_notice = " ".join(str(note) for note in entries["vnh"]["upstream_rights_notes"])
    assert "Copyright with the authors and Harvard Oriental Series" in vnh_notice
    assert "not for commercial purposes" in vnh_notice
    assert "van Nooten and Holland" in vnh_notice


def test_licence_uri_maps_to_a_registry_status_without_guessing() -> None:
    assert rights_status_for("https://creativecommons.org/licenses/by/4.0/") == RightsStatus.CC_BY
    assert (
        rights_status_for("https://creativecommons.org/licenses/by-nc-sa/4.0")
        == RightsStatus.CC_BY_NC_SA
    )
    assert rights_status_for(None) == RightsStatus.UNKNOWN
    assert rights_status_for("https://example.invalid/licence") == RightsStatus.UNKNOWN


def test_registered_text_versions_match_the_licences_declared_in_the_tei() -> None:
    header = {item["source_version_key"]: item for item in VedaWebCorpusHeader().parse(HEADER)}
    registered = {item.text_version_id: item for item in load_text_versions()}
    for key, entry in header.items():
        version = registered[f"VEDAWEB.{key.upper()}"]
        assert str(version.license_uri).rstrip("/") == str(entry["license_uri"]).rstrip("/")
        assert version.verbatim_license == entry["verbatim_license"]
        assert version.normalized_rights == rights_status_for(str(entry["license_uri"]))


def test_registry_records_one_role_and_one_rights_status_per_version() -> None:
    versions = {item.text_version_id: item for item in load_text_versions()}
    assert versions["VEDAWEB.ZURICH"].normalized_rights == RightsStatus.CC_BY
    assert versions["VEDAWEB.VNH"].normalized_rights == RightsStatus.CC_BY_NC_SA
    assert versions["VEDAWEB.VNH"].metrical_restoration
    assert versions["VEDAWEB.VNH"].source_specific_restrictions is not None
    assert not versions["GRETIL.RV.AUFRECHT"].metrical_restoration
    assert versions["GRETIL.RV.AUFRECHT"].text_role == TextRole.PRIMARY_TEXT
    assert versions["VEDAWEB.PADAPATHA"].text_form == TextForm.PADAPATHA
    assert len({item.text_role for item in versions.values()}) > 1


def test_every_registered_version_points_at_a_registered_artifact() -> None:
    artifacts = {item.artifact_id for item in load_source_artifacts()}
    for version in load_text_versions():
        assert version.artifact_id in artifacts


def test_git_hosted_artifacts_are_pinned_to_a_commit() -> None:
    for artifact in load_source_artifacts():
        if artifact.repository_url is None:
            continue
        assert artifact.repository_commit_sha is not None
        assert artifact.repository_path is not None
        assert artifact.checksum_sha256 is not None
        assert artifact.file_size_bytes is not None
        assert "main" not in str(artifact.url).split("/")[6:7]


def test_a_repository_artifact_without_a_commit_is_refused() -> None:
    with pytest.raises(ValueError, match="repository_commit_sha"):
        SourceArtifact(
            artifact_id="TEST.UNPINNED",
            source_id="VEDAWEB",
            url="https://example.invalid/rv.tei",
            format="TEI_XML",
            filename="rv.tei",
            rights_status=RightsStatus.UNKNOWN,
            repository_url="https://github.com/VedaWebProject/vedaweb-data",
        )


def test_a_pinned_artifact_without_a_path_is_refused() -> None:
    with pytest.raises(ValueError, match="repository_path"):
        SourceArtifact(
            artifact_id="TEST.NOPATH",
            source_id="VEDAWEB",
            url="https://example.invalid/rv.tei",
            format="TEI_XML",
            filename="rv.tei",
            rights_status=RightsStatus.UNKNOWN,
            repository_commit_sha="d3eb8af7324338161520d2d35eae8f7e985a19a5",
        )
