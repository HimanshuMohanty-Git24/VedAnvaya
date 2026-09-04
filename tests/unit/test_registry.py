from vedagraph.config.registry import load_source_artifacts, load_sources, load_works
from vedagraph.models.enums import RightsStatus


def test_source_registry_loads_as_models() -> None:
    sources = load_sources()
    assert {source.source_id for source in sources} >= {"VHP", "GRETIL", "VEDSEARCH"}
    assert next(source for source in sources if source.source_id == "VHP").rights.status == (
        RightsStatus.PERMISSION_REQUIRED
    )


def test_work_registry_preserves_samaveda_uncertainty() -> None:
    work = next(work for work in load_works() if work.work_id == "VG:WORK:SV:KAU")
    assert work.identity_status == "RESEARCH_REQUIRED"
    assert work.key_pattern is None


def test_source_artifact_registry_is_file_granular() -> None:
    artifacts = load_source_artifacts()
    gretil = next(item for item in artifacts if item.source_id == "GRETIL")
    assert gretil.filename == "sa_Rgveda-edAufrecht.xml"
    assert gretil.rights_status == RightsStatus.CC_BY_NC_SA
    assert gretil.checksum_sha256 == (
        "14197d9c1dcced64900ef971d9f4dc5b46aa8750780f5599453c9739d6a29edd"
    )
