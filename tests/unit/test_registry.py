from vedagraph.config.registry import load_source_artifacts, load_sources, load_works
from vedagraph.models.enums import RightsStatus


def test_source_registry_loads_as_models() -> None:
    sources = load_sources()
    assert {source.source_id for source in sources} >= {"VHP", "GRETIL", "VEDSEARCH"}
    assert next(source for source in sources if source.source_id == "VHP").rights.status == (
        RightsStatus.PERMISSION_REQUIRED
    )


def test_work_registry_preserves_samaveda_uncertainty() -> None:
    """No Samaveda key is declared, because the artifact evidencing it was rejected.

    The hierarchy is a corrected observation and is asserted here. The key is a
    commitment and is deliberately absent: the sole evidencing artifact failed both
    rights and edition-identity adjudication, and every known digital Kauthuma text
    descends from the same encumbered lineage, so no independent witness exists.
    """
    work = next(work for work in load_works() if work.work_id == "VG:WORK:SV:KAU")
    assert work.identity_status == "RESEARCH_REQUIRED"
    assert work.key_pattern is None
    # The hierarchy correction must survive: the source declares its own reference
    # system, and that observation does not depend on whether we may ingest the bytes.
    assert work.hierarchy == ["Arcika", "Prapathaka", "Ardha", "Dasati", "Verse"]
    # The superseded VHP-derived guess must not creep back in.
    assert "Adhyaya" not in work.hierarchy
    assert "Khanda" not in work.hierarchy
    # "line" is a sub-verse pada label and is never an identity level.
    assert "Line" not in work.hierarchy


def test_other_works_keep_final_identity() -> None:
    """Adding Samaveda must not disturb the three works whose keys are frozen."""
    works = {work.work_id: work for work in load_works()}
    for work_id, hierarchy in (
        ("VG:WORK:RV:SAK", ["Mandala", "Sukta", "Mantra"]),
        ("VG:WORK:YV:VSM", ["Adhyaya", "Mantra"]),
        ("VG:WORK:AV:SAU", ["Kanda", "Sukta", "Mantra"]),
    ):
        assert works[work_id].identity_status == "FINAL"
        assert works[work_id].hierarchy == hierarchy
        assert works[work_id].key_pattern is not None
    # Yajurveda genuinely has no hymn level; nothing may invent one for it.
    assert "Sukta" not in works["VG:WORK:YV:VSM"].hierarchy


def test_source_artifact_registry_is_file_granular() -> None:
    artifacts = load_source_artifacts()
    gretil = next(item for item in artifacts if item.source_id == "GRETIL")
    assert gretil.filename == "sa_Rgveda-edAufrecht.xml"
    assert gretil.rights_status == RightsStatus.CC_BY_NC_SA
    assert gretil.checksum_sha256 == (
        "14197d9c1dcced64900ef971d9f4dc5b46aa8750780f5599453c9739d6a29edd"
    )
