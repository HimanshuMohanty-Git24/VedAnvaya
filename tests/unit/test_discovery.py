from pathlib import Path
from uuid import uuid4

from vedagraph.discovery import assertion_conflicts, discover_rigveda_mandala
from vedagraph.models import SourceAssertion

FIXTURES = Path("tests/fixtures")


def test_discovery_is_persisted_and_deterministic(tmp_path: Path) -> None:
    first = discover_rigveda_mandala(
        mandala=1,
        gretil_snapshot=FIXTURES / "gretil/rv_sample.xml",
        gretil_snapshot_id="gretil-fixture",
        vhp_snapshot=FIXTURES / "vhp_rv_1_1.html",
        vhp_snapshot_id="vhp-fixture",
        output_dir=tmp_path,
    )
    first_bytes = first.output_path.read_bytes()
    second = discover_rigveda_mandala(
        mandala=1,
        gretil_snapshot=FIXTURES / "gretil/rv_sample.xml",
        gretil_snapshot_id="gretil-fixture",
        vhp_snapshot=FIXTURES / "vhp_rv_1_1.html",
        vhp_snapshot_id="vhp-fixture",
        output_dir=tmp_path,
    )
    assert second.output_path.read_bytes() == first_bytes
    assert first.unique_suktas == 2
    assert first.gretil_suktas == 1
    assert first.vhp_suktas == 2
    assert not first.agreement


def test_assertion_conflict_reporting() -> None:
    common = {
        "subject_id": "VG:RV:SAK:M01",
        "predicate": "REPORTED_SUKTA_COUNT",
        "source_locator": "fixture",
    }
    assertions = [
        SourceAssertion(assertion_id=uuid4(), value=191, source_id="GRETIL", **common),
        SourceAssertion(assertion_id=uuid4(), value=190, source_id="VHP", **common),
    ]
    conflicts = assertion_conflicts(assertions)
    assert ("VG:RV:SAK:M01", "REPORTED_SUKTA_COUNT") in conflicts
