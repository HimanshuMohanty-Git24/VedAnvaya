from hashlib import sha256
from pathlib import Path

import orjson

from vedagraph.identity import (
    VEDAGRAPH_NAMESPACE_UUID,
    rv_mandala_identity,
    rv_mantra_identity,
    rv_mantra_key,
    rv_sukta_identity,
    uuid_for_urn,
)

FIXTURES = Path("tests/fixtures")


def test_namespace_is_fixed() -> None:
    assert str(VEDAGRAPH_NAMESPACE_UUID) == "7c8cde94-2bc0-50e2-8819-568ae65a3ec4"


def test_same_urn_always_produces_same_uuid() -> None:
    urn = "urn:vedagraph:mantra:rigveda:shakala:mandala:1:sukta:1:mantra:1"
    assert uuid_for_urn(urn) == uuid_for_urn(urn)


def test_different_urns_produce_different_uuids() -> None:
    first = rv_mantra_identity(1, 1, 1)[2]
    second = rv_mantra_identity(1, 1, 2)[2]
    assert first != second


def test_citation_format_does_not_participate_in_identity() -> None:
    _label_a = "RV 1.1.1"
    _label_b = "ṚV I.1.1"
    urn = rv_mantra_identity(1, 1, 1)[1]
    assert uuid_for_urn(urn) == rv_mantra_identity(1, 1, 1)[2]


def test_canonical_key_padding() -> None:
    assert rv_mantra_key(1, 1, 1) == "VG:RV:SAK:M01:S001:V001"


def test_complete_mandala_1_identity_compatibility_fixture() -> None:
    """Every Mandala 1 key/URN/UUID/parent/citation is frozen by one digest."""
    baseline = orjson.loads(
        (FIXTURES / "identity/rv_mandala_1_identity_baseline.json").read_bytes()
    )
    rows: list[dict[str, str | None]] = []
    mandala_key, mandala_urn, mandala_id = rv_mandala_identity(1)
    rows.append(
        {
            "canonical_key": mandala_key,
            "canonical_urn": mandala_urn,
            "entity_id": str(mandala_id),
            "parent_key": None,
            "canonical_citation": "RV 1",
        }
    )
    for sukta, mantra_count in enumerate(baseline["mantra_counts_by_sukta"], start=1):
        sukta_key, sukta_urn, sukta_id = rv_sukta_identity(1, sukta)
        rows.append(
            {
                "canonical_key": sukta_key,
                "canonical_urn": sukta_urn,
                "entity_id": str(sukta_id),
                "parent_key": mandala_key,
                "canonical_citation": f"RV 1.{sukta}",
            }
        )
        for mantra in range(1, mantra_count + 1):
            key, urn, identifier = rv_mantra_identity(1, sukta, mantra)
            rows.append(
                {
                    "canonical_key": key,
                    "canonical_urn": urn,
                    "entity_id": str(identifier),
                    "parent_key": sukta_key,
                    "canonical_citation": f"RV 1.{sukta}.{mantra}",
                }
            )
    encoded = orjson.dumps(
        sorted(rows, key=lambda row: row["canonical_key"] or ""),
        option=orjson.OPT_SORT_KEYS,
    )
    assert len(rows) == baseline["passage_count"]
    assert sha256(encoded).hexdigest() == baseline["identity_sha256"]
