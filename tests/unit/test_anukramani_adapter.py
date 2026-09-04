"""The Anukramaṇī parser must read every documented form and fail closed on the rest."""

from pathlib import Path

import pytest

from vedagraph.ingest.adapters import WSC2023AnukramaniAdapter
from vedagraph.models.enums import AnukramaniField, AnukramaniParseStatus, ScopeOrigin

FIXTURES = Path("tests/fixtures/anukramani")


def _parse(mandala: int) -> list:  # type: ignore[type-arg]
    return WSC2023AnukramaniAdapter().parse_anukramani(
        FIXTURES / f"Mandala_{mandala}.txt",
        snapshot_id=f"WSC2023:fixture{mandala}",
        source_artifact_id=f"WSC2023.RV.ANUKRAMANI.M{mandala:02d}",
        mandala=mandala,
    )


def test_header_is_required() -> None:
    adapter = WSC2023AnukramaniAdapter()
    with pytest.raises(ValueError, match="expected Anukramaṇī header"):
        adapter.parse_anukramani(
            Path("tests/fixtures/vhp_rv_1_1.html"),
            snapshot_id="x",
            source_artifact_id="y",
            mandala=1,
        )


def test_the_adapter_refuses_to_pretend_the_dataset_is_text() -> None:
    with pytest.raises(NotImplementedError):
        WSC2023AnukramaniAdapter().parse(Path("x"), snapshot_id="y")


def test_an_unscoped_field_is_one_sukta_wide_claim() -> None:
    record = _parse(1)[0]
    assert record.parse_status is AnukramaniParseStatus.PARSED
    assert (record.mandala, record.sukta, record.declared_verse_count) == (1, 1, 3)
    assert {segment.scope_origin for segment in record.segments} == {ScopeOrigin.SUKTA_WIDE}
    assert [segment.raw_value for segment in record.segments] == [
        "vaiśvāmitro madhucchandāḥ",
        "agniḥ",
        "gāyatrī",
    ]


def test_verse_scopes_become_ranges_and_single_mantras() -> None:
    devatas = [
        segment for segment in _parse(1)[1].segments if segment.field is AnukramaniField.DIVINITY
    ]
    assert [
        (item.raw_value, item.scope_origin, item.start_mantra, item.end_mantra) for item in devatas
    ] == [
        ("vāyuḥ", ScopeOrigin.MANTRA_RANGE, 1, 2),
        ("indravāyū", ScopeOrigin.SINGLE_MANTRA, 3, 3),
        ("mitrāvaruṇau", ScopeOrigin.SINGLE_MANTRA, 4, 4),
    ]


def test_a_verse_set_becomes_separate_spans_and_is_never_widened() -> None:
    record = _parse(1)[2]
    ila = [segment for segment in record.segments if segment.raw_value == "iḻā-sarasvatī-mahī"]
    assert [(item.start_mantra, item.end_mantra) for item in ila] == [(1, 2), (5, 5)]
    assert all(item.raw_scope == "1-2,5" for item in ila)


def test_a_composite_label_is_kept_verbatim() -> None:
    values = {segment.raw_value for segment in _parse(1)[2].segments}
    assert "iḻā-sarasvatī-mahī" in values
    assert "iḻā" not in values


def test_a_missing_field_is_reported_not_guessed() -> None:
    record = _parse(2)[0]
    assert record.parse_status is AnukramaniParseStatus.PARTIALLY_PARSED
    assert record.raw_seer_field is None
    assert any("seer field is absent" in note for note in record.parse_notes)
    assert not [segment for segment in record.segments if segment.field is AnukramaniField.SEER]


def test_a_descending_span_is_dropped_and_reported() -> None:
    record = _parse(2)[1]
    assert record.parse_status is AnukramaniParseStatus.PARTIALLY_PARSED
    assert any("ascending span" in note for note in record.parse_notes)
    assert not [segment for segment in record.segments if segment.field is AnukramaniField.METER]


def test_a_span_beyond_the_declared_verse_count_is_dropped_and_reported() -> None:
    record = _parse(2)[2]
    assert record.parse_status is AnukramaniParseStatus.PARTIALLY_PARSED
    assert any("exceeds the declared 2 verses" in note for note in record.parse_notes)


def test_every_mandala_file_parses(tmp_path: Path) -> None:
    for mandala in (1, 2):
        records = _parse(mandala)
        assert records
        assert {record.mandala for record in records} == {mandala}
        assert [record.sukta for record in records] == [1, 2, 3]
