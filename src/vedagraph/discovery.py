"""Deterministic structural discovery and count assertions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from vedagraph.identity import rv_mandala_key, uuid_for_urn
from vedagraph.ingest.adapters import GRETILAdapter, VHPAdapter
from vedagraph.models import SourceAssertion, SuktaDiscoveryRecord
from vedagraph.models.enums import AssertionStatus
from vedagraph.storage import write_jsonl


@dataclass(frozen=True)
class DiscoveryResult:
    unique_suktas: int
    gretil_suktas: int
    vhp_suktas: int
    agreement: bool
    output_path: Path
    assertions_path: Path


def _assertion(
    subject: str, predicate: str, value: object, source_id: str, locator: str
) -> SourceAssertion:
    urn = f"urn:vedagraph:source-assertion:{subject}:{predicate}:{source_id}:{value}"
    return SourceAssertion(
        assertion_id=uuid_for_urn(urn),
        subject_id=subject,
        predicate=predicate,
        value=value,
        source_id=source_id,
        source_locator=locator,
        status=AssertionStatus.UNREVIEWED,
    )


def discover_rigveda_mandala(
    *,
    mandala: int,
    gretil_snapshot: Path,
    gretil_snapshot_id: str,
    vhp_snapshot: Path,
    vhp_snapshot_id: str,
    output_dir: Path,
) -> DiscoveryResult:
    gretil_adapter = GRETILAdapter()
    gretil = gretil_adapter.discover_suktas(
        gretil_snapshot, snapshot_id=gretil_snapshot_id, mandala=mandala
    )
    vhp = VHPAdapter().discover_suktas(vhp_snapshot, snapshot_id=vhp_snapshot_id, mandala=mandala)
    all_records: list[SuktaDiscoveryRecord] = sorted(
        [*gretil, *vhp], key=lambda record: (record.sukta_number, record.source_id)
    )
    output_path = output_dir / f"rv_mandala_{mandala}_discovery.jsonl"
    write_jsonl(output_path, all_records)

    subject = rv_mandala_key(mandala)
    assertions = [
        _assertion(
            subject,
            "REPORTED_SUKTA_COUNT",
            len(gretil),
            "GRETIL",
            "TEI maṇḍala/sūkta/lg hierarchy",
        ),
        _assertion(
            subject,
            "REPORTED_SUKTA_COUNT",
            len(vhp),
            "VHP",
            "Mandala Sukta navigation",
        ),
        _assertion(
            subject,
            "REPORTED_MANTRA_COUNT",
            sum(record.known_mantra_count or 0 for record in gretil),
            "GRETIL",
            "TEI lg count within Mandala",
        ),
    ]
    assertions_path = output_dir / "source_assertions.jsonl"
    write_jsonl(assertions_path, assertions)
    gretil_numbers = {record.sukta_number for record in gretil}
    vhp_numbers = {record.sukta_number for record in vhp}
    return DiscoveryResult(
        unique_suktas=len(gretil_numbers | vhp_numbers),
        gretil_suktas=len(gretil_numbers),
        vhp_suktas=len(vhp_numbers),
        agreement=gretil_numbers == vhp_numbers,
        output_path=output_path,
        assertions_path=assertions_path,
    )


def assertion_conflicts(
    assertions: list[SourceAssertion],
) -> dict[tuple[str, str], list[SourceAssertion]]:
    grouped: dict[tuple[str, str], list[SourceAssertion]] = {}
    for assertion in assertions:
        grouped.setdefault((assertion.subject_id, assertion.predicate), []).append(assertion)
    return {
        key: values
        for key, values in grouped.items()
        if len({repr(assertion.value) for assertion in values}) > 1
    }
