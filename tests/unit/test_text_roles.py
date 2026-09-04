"""Text roles, configurable primary selection, and identity independence."""

from pathlib import Path

import pytest
import yaml

from vedagraph.config.registry import load_build_config, load_text_versions
from vedagraph.identity import rv_mantra_identity, rv_sukta_identity
from vedagraph.models import CorpusBuildConfig, TextVersion
from vedagraph.models.enums import RightsStatus, TextForm, TextRole

BUILD_CONFIG = Path("data/builds/rv_mandala_1.yaml")


def _text_version(role: TextRole, version_id: str) -> TextVersion:
    key, urn, identifier = rv_mantra_identity(1, 1, 1)
    del key, urn
    return TextVersion(
        text_id=identifier,
        passage_id=identifier,
        language="sa",
        script="Latin",
        text_form=TextForm.SAMHITA,
        text_role=role,
        text_version_id=version_id,
        text_original="agním",
        text_nfc="agním",
        accented=True,
        source_id="GRETIL",
        source_locator="RV 1.1.1",
        content_sha256="0" * 64,
        rights_status=RightsStatus.CC_BY_NC_SA,
    )


def test_one_passage_can_carry_several_distinct_representations() -> None:
    versions = [
        _text_version(TextRole.PRIMARY_TEXT, "GRETIL.RV.AUFRECHT"),
        _text_version(TextRole.PARALLEL_TEXT, "VEDAWEB.AUFRECHT"),
        _text_version(TextRole.METRICALLY_RESTORED, "VEDAWEB.VNH"),
        _text_version(TextRole.PADAPATHA, "VEDAWEB.PADAPATHA"),
        _text_version(TextRole.SEARCH_DERIVATIVE, "VEDAGRAPH.SEARCH"),
        _text_version(TextRole.DISPLAY_DERIVATIVE, "VEDAGRAPH.IAST"),
    ]
    assert len({version.text_role for version in versions}) == len(versions)
    assert len({version.text_version_id for version in versions}) == len(versions)
    assert len({version.passage_id for version in versions}) == 1


def test_text_role_does_not_replace_text_form() -> None:
    padapatha = _text_version(TextRole.PADAPATHA, "VEDAWEB.PADAPATHA")
    assert padapatha.text_form == TextForm.SAMHITA
    padapatha.text_form = TextForm.PADAPATHA
    assert padapatha.text_role == TextRole.PADAPATHA


def test_default_role_keeps_older_records_valid() -> None:
    minimal = TextVersion(
        text_id=rv_mantra_identity(1, 1, 1)[2],
        passage_id=rv_mantra_identity(1, 1, 1)[2],
        language="sa",
        script="Latin",
        text_form=TextForm.SAMHITA,
        text_original="agním",
        text_nfc="agním",
        accented=True,
        source_id="GRETIL",
        source_locator="RV 1.1.1",
        content_sha256="0" * 64,
        rights_status=RightsStatus.CC_BY_NC_SA,
    )
    assert minimal.text_role == TextRole.PRIMARY_TEXT
    assert minimal.text_version_id is None


def test_primary_selection_lives_in_build_configuration() -> None:
    config = load_build_config(BUILD_CONFIG)
    assert config.primary_sanskrit is not None
    assert config.primary_sanskrit.text_version == "GRETIL.RV.AUFRECHT"
    assert config.primary_sanskrit.role == TextRole.PRIMARY_TEXT
    parallel = {item.text_version: item.role for item in config.parallel_sanskrit}
    assert parallel["VEDAWEB.VNH"] == TextRole.METRICALLY_RESTORED
    assert parallel["VEDAWEB.PADAPATHA"] == TextRole.PADAPATHA
    assert parallel["VEDAWEB.ZURICH"] == TextRole.LINGUISTIC_ANNOTATION
    registered = {item.text_version_id for item in load_text_versions()}
    assert config.primary_sanskrit.text_version in registered
    assert all(item.text_version in registered for item in config.parallel_sanskrit)


def test_no_primary_version_name_is_hardcoded_in_parser_code() -> None:
    sources = list(Path("src/vedagraph").rglob("*.py"))
    offenders = [
        path
        for path in sources
        if path.name not in {"build.py", "run.py"}
        and "VEDAWEB.AUFRECHT" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


def test_changing_the_primary_version_cannot_change_passage_identity(tmp_path: Path) -> None:
    """Identity comes from the citation hierarchy, so swapping editions must be free."""
    payload = yaml.safe_load(BUILD_CONFIG.read_text(encoding="utf-8"))
    baseline_ids = [rv_mantra_identity(1, sukta, 1) for sukta in payload["selected_suktas"]]
    baseline_suktas = [rv_sukta_identity(1, sukta) for sukta in payload["selected_suktas"]]

    payload["primary_sanskrit"] = {
        "artifact": "VEDAWEB.RV.BOOK01.TEI.D3EB8AF",
        "text_version": "VEDAWEB.VNH",
        "role": "METRICALLY_RESTORED",
    }
    payload["parallel_sanskrit"] = [
        {
            "artifact": "GRETIL.RV.AUFRECHT.TEI.2019",
            "text_version": "GRETIL.RV.AUFRECHT",
            "role": "PARALLEL_TEXT",
        }
    ]
    swapped = tmp_path / "swapped.yaml"
    swapped.write_text(yaml.safe_dump(payload, allow_unicode=True), encoding="utf-8")

    config = load_build_config(swapped)
    assert config.primary_sanskrit is not None
    assert config.primary_sanskrit.text_version == "VEDAWEB.VNH"
    assert [rv_mantra_identity(1, sukta, 1) for sukta in config.selected_suktas] == baseline_ids
    assert [rv_sukta_identity(1, sukta) for sukta in config.selected_suktas] == baseline_suktas


def test_a_build_config_may_defer_the_primary_choice() -> None:
    """A provisional configuration must remain loadable so comparison work can continue."""
    payload = yaml.safe_load(BUILD_CONFIG.read_text(encoding="utf-8"))
    payload["primary_sanskrit"] = None
    payload["candidate_text_versions"] = [
        {
            "artifact": "GRETIL.RV.AUFRECHT.TEI.2019",
            "text_version": "GRETIL.RV.AUFRECHT",
            "role": "PARALLEL_TEXT",
        },
        {
            "artifact": "VEDAWEB.RV.BOOK01.TEI.D3EB8AF",
            "text_version": "VEDAWEB.EICHLER",
            "role": "PARALLEL_TEXT",
        },
    ]
    config = CorpusBuildConfig.model_validate(payload)
    assert config.primary_sanskrit is None
    assert len(config.candidate_text_versions) == 2


def test_an_unknown_role_is_rejected() -> None:
    payload = yaml.safe_load(BUILD_CONFIG.read_text(encoding="utf-8"))
    payload["primary_sanskrit"]["role"] = "BEST_TEXT"
    with pytest.raises(ValueError):
        CorpusBuildConfig.model_validate(payload)
