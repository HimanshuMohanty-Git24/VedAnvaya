from pathlib import Path

from vedagraph.ingest.adapters import GRETILAdapter, VHPAdapter, WikisourceTranslationAdapter
from vedagraph.models.enums import TextSelectionPolicy, TranslationAlignment

FIXTURES = Path("tests/fixtures")


def test_vhp_fixture_parser_preserves_accents() -> None:
    records = VHPAdapter().parse(FIXTURES / "vhp_rv_1_1.html", snapshot_id="fixture")
    assert [record.hierarchy["mantra"] for record in records] == [1, 2]
    assert records[0].accented
    assert "॥१॥" in records[0].text_original


def test_gretil_tei_parser_uses_tei_hierarchy() -> None:
    records = GRETILAdapter().parse(FIXTURES / "gretil/rv_sample.xml", snapshot_id="fixture")
    assert len(records) == 2
    assert records[0].source_locator == "RV 1.1.1"
    assert records[0].accented
    assert records[0].text_original.count("ī") == 1
    assert "īḷe" not in records[0].text_original


def test_gretil_tei_selection_keeps_variants_distinct() -> None:
    original = GRETILAdapter(text_selection_policy=TextSelectionPolicy.ORIGINAL).parse(
        FIXTURES / "gretil/rv_sample.xml", snapshot_id="fixture"
    )
    regularized = GRETILAdapter(text_selection_policy=TextSelectionPolicy.REGULARIZED).parse(
        FIXTURES / "gretil/rv_sample.xml", snapshot_id="fixture"
    )
    assert "a̱gnim ī̍ḻe" in original[0].text_original
    assert "agnim īḷe" in regularized[0].text_original
    assert "ī̍ḻeīḷe" not in original[0].text_original
    assert original[0].alternate_text == regularized[0].text_original
    assert original[1].text_original != regularized[1].text_original


def test_gretil_header_metadata_and_discovery() -> None:
    adapter = GRETILAdapter()
    header = adapter.extract_header_metadata(FIXTURES / "gretil/rv_sample.xml")
    assert header.title == "Ṛgveda-Saṃhitā"
    assert header.publication_date == "2019-10-03"
    assert header.responsibility_statements["data entry"] == [
        "Barend A. Van Nooten",
        "Gary B. Holland",
    ]
    assert str(header.license_url) == "https://creativecommons.org/licenses/by-nc-sa/4.0/"
    discovery = adapter.discover_suktas(
        FIXTURES / "gretil/rv_sample.xml", snapshot_id="fixture", mandala=1
    )
    assert [(item.sukta_number, item.known_mantra_count) for item in discovery] == [(1, 2)]


def test_wikisource_translation_fixture_parser() -> None:
    records = WikisourceTranslationAdapter().parse_translations(
        FIXTURES / "wikisource/rv_1_1.html", snapshot_id="fixture"
    )
    assert [record.text_original for record in records] == ["I laud Agni.", "Worthy is Agni."]
    assert records[0].translator == "Ralph T. H. Griffith"
    assert all(item.alignment == TranslationAlignment.EXACT_MANTRA_ALIGNMENT for item in records)


def test_wikisource_api_revision_provenance() -> None:
    records = WikisourceTranslationAdapter().parse_translations(
        FIXTURES / "wikisource/rv_1_1_api.json", snapshot_id="fixture"
    )
    assert records[0].page_id == 12345
    assert records[0].revision_id == 987654321
    assert str(records[0].canonical_page_url).endswith("Book_1/Hymn_1")


def test_wikisource_legacy_numbering_punctuation_variants(tmp_path: Path) -> None:
    snapshot = tmp_path / "legacy.html"
    snapshot.write_text(
        "<div class='verse'><pre>1.FIRST stanza\n2, Second stanza\n3 Third stanza</pre></div>",
        encoding="utf-8",
    )
    records = WikisourceTranslationAdapter().parse_translations(
        snapshot, snapshot_id="fixture", mandala=2, sukta=10
    )
    assert [record.hierarchy["mantra"] for record in records] == [1, 2, 3]
    assert [record.text_original for record in records] == [
        "FIRST stanza",
        "Second stanza",
        "Third stanza",
    ]
    assert all(item.alignment == TranslationAlignment.EXACT_MANTRA_ALIGNMENT for item in records)


def test_vhp_discovery_and_metadata_staging() -> None:
    adapter = VHPAdapter()
    discoveries = adapter.discover_suktas(
        FIXTURES / "vhp_rv_1_1.html", snapshot_id="fixture", mandala=1
    )
    assert [item.sukta_number for item in discoveries] == [1, 2]
    metadata = adapter.parse_metadata(FIXTURES / "vhp_rv_1_1.html", snapshot_id="fixture")
    assert metadata.reported_mantra_count == 2
    assert metadata.rishis == ["मधुच्छन्दा वैश्वामित्रः"]
    assert len(metadata.media_urls) == 1


def test_wikisource_pages_without_poem_or_pre_markup_still_parse(tmp_path: Path) -> None:
    """The oldest transcriptions (e.g. RV 5.65) carry stanzas as plain body text."""
    snapshot = tmp_path / "plain.html"
    snapshot.write_text(
        "<div class='mw-parser-output'>"
        "<div class='ws-header'>Hymn 64 Hymn 66</div>"
        "<p>1. FULL wise is he.\n     The man whose praise-songs.</p>"
        "<p>2. For they are Kings.</p></div>",
        encoding="utf-8",
    )
    records = WikisourceTranslationAdapter().parse_translations(
        snapshot, snapshot_id="fixture", mandala=5, sukta=65
    )
    assert [record.hierarchy["mantra"] for record in records] == [1, 2]
    assert records[0].text_original == "FULL wise is he. The man whose praise-songs."
    assert all(item.alignment == TranslationAlignment.EXACT_MANTRA_ALIGNMENT for item in records)


def test_a_gap_in_source_stanza_numbering_is_never_silently_renumbered(tmp_path: Path) -> None:
    """RV 5.55 skips stanza 8 on Wikisource; the gap must stay a gap."""
    snapshot = tmp_path / "gap.html"
    snapshot.write_text(
        "<div class='verse'><pre>1. First\n2. Second\n4. Fourth</pre></div>", encoding="utf-8"
    )
    records = WikisourceTranslationAdapter().parse_translations(
        snapshot, snapshot_id="fixture", mandala=5, sukta=55
    )
    assert [record.hierarchy["mantra"] for record in records] == [1, 2, 4]
    assert all(item.alignment == TranslationAlignment.UNCERTAIN_ALIGNMENT for item in records)
