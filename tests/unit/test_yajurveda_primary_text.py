"""Coverage and fidelity guards for the Vajasaneyi Samhita accented layer.

Why this file exists
--------------------
The ``FOUR_VEDA_CANONICAL_SANSKRIT_BLOCKER_CLOSURE`` run closed the Yajurveda
primary-text blocker on a measured claim: the accented layer reaches 1975/1975
addresses once mula boundaries are read from the edition's declared ordinal
headers instead of being inferred from accent presence. Before this file, that
claim had NO test guarding it -- ``-k "yajurveda or vsm or YV"`` selected exactly
two identity-key tests and nothing that touched the parser. A regression in the
boundary logic would have silently dropped mantras with nothing to catch it,
which is precisely how the layer reached 1958/1975 in the first place.

Why these tests skip rather than ship fixtures
----------------------------------------------
``data/raw/**`` is gitignored, so the 44 pinned Wikisource snapshots are NOT in
the repository and are absent in a clean checkout and in CI. These tests
therefore skip when the snapshots are missing rather than failing, and they are
guards for a working tree that has fetched them -- not a substitute for the
fixture-backed tests elsewhere in this suite. Embedding a fixture instead was
rejected deliberately: a hand-trimmed excerpt would exercise the excerpt, and
every defect these tests exist to catch (a commentator siglum masquerading as an
ordinal prefix, a space-separated section marker, a colophon colliding with a
mantra number) lives in the full-page structure that an excerpt discards.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from vedagraph.ingest.adapters.yajurveda_wikisource import (
    PARSER_VERSION,
    AdhyayaParse,
    YajurvedaWikisourceAdapter,
    adhyaya_title,
    content_api_url,
)
from vedagraph.models import RawSnapshotMetadata

RAW_ROOT = Path("data/raw/wikisource_sa")
ADHYAYA_COUNT = 40
#: Computed from the artifact by the closure run, not quoted from a reference work.
EXPECTED_MANTRA_ADDRESSES = 1975
#: The one address where the 1929 print carries two readings of the same mantra.
KNOWN_VARIANT = (16, 37)


def _snapshot_index() -> dict[str, tuple[Path, RawSnapshotMetadata]]:
    index: dict[str, tuple[Path, RawSnapshotMetadata]] = {}
    if not RAW_ROOT.exists():
        return index
    for metadata_path in sorted(RAW_ROOT.glob("**/*.metadata.json")):
        metadata = RawSnapshotMetadata.model_validate_json(metadata_path.read_bytes())
        content_path = metadata_path.with_name(metadata.filename)
        if content_path.exists():
            index[str(metadata.retrieval_url)] = (content_path, metadata)
    return index


def _parse_all() -> dict[int, AdhyayaParse]:
    index = _snapshot_index()
    adapter = YajurvedaWikisourceAdapter()
    parses: dict[int, AdhyayaParse] = {}
    for adhyaya in range(1, ADHYAYA_COUNT + 1):
        url = content_api_url(adhyaya_title(adhyaya))
        if url not in index:
            pytest.skip(f"no pinned snapshot for adhyaya {adhyaya}; run the fetch script")
        path, metadata = index[url]
        parses[adhyaya] = adapter.parse_adhyaya(path, snapshot_id=metadata.snapshot_id)
    return parses


@pytest.fixture(scope="module")
def parses() -> dict[int, AdhyayaParse]:
    if not _snapshot_index():
        pytest.skip("data/raw/wikisource_sa is gitignored and absent in this tree")
    return _parse_all()


def test_parser_version_records_the_ordinal_header_implementation() -> None:
    """v1 inferred boundaries from accent presence; v2 reads declared headers.

    Pinned because the version string is carried into every release manifest, so
    a silent bump would make two structurally different layers indistinguishable
    after the fact.
    """
    assert PARSER_VERSION == "wikisource-sa-vsm-v2"


def test_accented_layer_covers_every_mantra_address(
    parses: dict[int, AdhyayaParse],
) -> None:
    """1975/1975, the claim the blocker closure rests on.

    Before the ordinal-header reimplementation this was 1958/1975. If this test
    fails at 1958 the boundary detection has regressed to accent-presence
    inference; if it fails at some other number, read the per-adhyaya breakdown
    in the assertion message rather than adjusting the constant.
    """
    accented = {
        (adhyaya, int(record.hierarchy["mantra"]))
        for adhyaya, parse in parses.items()
        for record in parse.accented
    }
    unaccented = {
        (adhyaya, int(record.hierarchy["mantra"]))
        for adhyaya, parse in parses.items()
        for record in parse.samhita
    }
    missing = sorted(unaccented - accented)
    assert not missing, (
        f"addresses in the samhita layer but absent from the accented layer: {missing}"
    )
    assert len(accented) == EXPECTED_MANTRA_ADDRESSES
    assert len(accented | unaccented) == EXPECTED_MANTRA_ADDRESSES


def test_every_adhyaya_is_present_and_contiguous(parses: dict[int, AdhyayaParse]) -> None:
    """No adhyaya silently empty, and mantra numbering has no interior holes.

    A hole would mean the parser lost a mantra the source labels, which is a
    different and worse failure than a mantra the source never carried.
    """
    assert sorted(parses) == list(range(1, ADHYAYA_COUNT + 1))
    for adhyaya, parse in parses.items():
        numbers = {int(record.hierarchy["mantra"]) for record in parse.accented}
        assert numbers, f"adhyaya {adhyaya} yielded no accented mantras"
        expected = set(range(1, max(numbers) + 1))
        assert numbers == expected, (
            f"adhyaya {adhyaya} missing mantra numbers {sorted(expected - numbers)}"
        )


def test_vsm_16_37_keeps_both_printed_readings(parses: dict[int, AdhyayaParse]) -> None:
    """The variant is preserved as data, never resolved by the parser.

    The 1929 page prints this mantra twice. Choosing between the two readings is
    a philological judgement reserved for recorded human review, so the parser
    keeps the first as the record, retains the second as a reviewable
    intervention, and decides nothing. A green suite with this test removed would
    mean a build had quietly picked a reading.
    """
    adhyaya, mantra = KNOWN_VARIANT
    parse = parses[adhyaya]
    assert parse.accented_collisions.get(mantra) == 2

    second_readings = [
        item
        for item in parse.editorial_interventions
        if item.mantra == mantra and "SECOND_READING" in item.kind
    ]
    assert second_readings, "the second printed reading of VSM 16.37 was dropped without a record"
    assert second_readings[0].removed.strip(), "the second reading was recorded but carries no text"


def test_variant_collisions_do_not_spread_beyond_the_known_address(
    parses: dict[int, AdhyayaParse],
) -> None:
    """VSM 16.37 must be the ONLY collision.

    This is the regression guard for a real defect found during the closure run:
    a commentator siglum ("u0") was being matched as a two-word inline ordinal
    prefix, so Uvata's and Mahidhara's prose was parsed as mula and produced
    dozens of spurious "second readings". Collisions appearing at new addresses
    mean commentary is leaking into the text layer again.
    """
    collisions = {
        (adhyaya, mantra)
        for adhyaya, parse in parses.items()
        for mantra in parse.accented_collisions
    }
    assert collisions == {KNOWN_VARIANT}


def test_parsing_is_deterministic(parses: dict[int, AdhyayaParse]) -> None:
    """Two parses of the same bytes agree exactly, including failures.

    Deterministic rebuild is a release guarantee, and comparing the failure list
    as well as the text matters: a parser that reported different failures run to
    run would still produce identical output while being unreproducible.
    """
    again = _parse_all()
    for adhyaya, parse in parses.items():
        other = again[adhyaya]
        assert [r.text_original for r in parse.accented] == [
            r.text_original for r in other.accented
        ]
        assert [r.text_original for r in parse.samhita] == [
            r.text_original for r in other.samhita
        ]
        assert [f.reason for f in parse.failures] == [f.reason for f in other.failures]


def test_no_mantra_text_is_empty(parses: dict[int, AdhyayaParse]) -> None:
    """Coverage counts are worthless if an address can carry an empty string.

    Guards the specific way a coverage metric can be gamed: emitting a record per
    address regardless of whether any text was captured for it.
    """
    empties = [
        (adhyaya, int(record.hierarchy["mantra"]))
        for adhyaya, parse in parses.items()
        for record in parse.accented
        if not record.text_original.strip()
    ]
    assert not empties, f"accented records carrying no text: {empties}"
