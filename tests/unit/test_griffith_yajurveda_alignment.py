"""Guards for the Griffith 1899 White Yajurveda alignment.

Why these tests skip rather than ship a fixture
-----------------------------------------------
``data/raw/**`` is gitignored, so the pinned sacred-texts snapshots are absent in a clean
checkout and in CI. The corpus-wide tests skip when they are missing. Trimming a fixture
was rejected because every property guarded here is a whole-book property: the printed
book heading, the numbering run from 1 to the book's last mantra, the duplicate verse in
book 12 that only shows up when both copies are present. An excerpt would assert nothing.

The grammar and addressing tests below need no snapshots and always run.

What is deliberately NOT asserted
---------------------------------
No test pins the five alignment counts to remembered constants. Those are measurements of
a source with real defects; freezing them would turn a measurement into a fixture and make
the next genuine parser fix look like a regression. The tests assert INVARIANTS instead --
that the counts close, that no key is claimed twice, that no unit's text is dropped, and
above all that a canonical key follows the number the source prints rather than where the
unit happens to sit.
"""

from __future__ import annotations

import json
import random
from collections import Counter
from pathlib import Path

import pytest

from vedagraph.ingest.adapters.griffith_yajurveda import (
    BOOK_COUNT,
    AdapterError,
    Alignment,
    BookAlignment,
    CanonicalSpine,
    GriffithYajurvedaAdapter,
    TranslationUnit,
    _read_label,
    align_book,
    build_stage,
    extract_lines,
    parse_book_ordinal,
    segment_units,
    summarize,
)

REPO = Path(__file__).resolve().parents[2]
SNAPSHOT_ID = "2026-09-07"
SNAPSHOT_DIR = REPO / "data" / "raw" / "sacred_texts" / SNAPSHOT_ID / "wyv"
PASSAGES = REPO / "data" / "canonical" / "yajurveda_vsm_v1" / "passages.jsonl"


def _snapshots_available() -> bool:
    if not PASSAGES.exists() or not (SNAPSHOT_DIR / "manifest.json").exists():
        return False
    try:
        GriffithYajurvedaAdapter().load_snapshots(SNAPSHOT_DIR)
    except (AdapterError, KeyError, json.JSONDecodeError):
        return False
    return True


requires_snapshots = pytest.mark.skipif(
    not _snapshots_available(),
    reason="sacred-texts wyv snapshots absent; run scripts/fetch_griffith_yajurveda.py",
)


@pytest.fixture(scope="module")
def spine() -> CanonicalSpine:
    if not PASSAGES.exists():
        pytest.skip("canonical yajurveda_vsm_v1 release absent")
    return CanonicalSpine.from_passages(PASSAGES)


@pytest.fixture(scope="module")
def alignments(spine: CanonicalSpine) -> list[BookAlignment]:
    if not _snapshots_available():
        pytest.skip("sacred-texts wyv snapshots absent")
    return GriffithYajurvedaAdapter().align(SNAPSHOT_DIR, spine)


# --------------------------------------------------------------------------------------
# Grammar and addressing: no snapshots needed.
# --------------------------------------------------------------------------------------


def test_book_ordinal_is_read_from_the_printed_heading() -> None:
    assert parse_book_ordinal("BOOK THE FIRST.") == 1
    assert parse_book_ordinal("BOOK THE FIFTH") == 5
    assert parse_book_ordinal("BOOK THE TWENTY-FIRST.") == 21
    assert parse_book_ordinal("BOOK THE THIRTY-NINTH.") == 39
    assert parse_book_ordinal("BOOK THE FORTIETH.") == 40
    with pytest.raises(AdapterError):
        parse_book_ordinal("BOOK THE UMPTEENTH.")


def test_label_grammar_matches_the_shapes_the_source_actually_prints() -> None:
    plain = _read_label("2 Strainer of Vasu art thou.")
    assert plain is not None and plain.label == "2"

    grouped = _read_label("40, 41 Return again, etc.")
    assert grouped is not None and grouped.label == "40, 41"

    dotted = _read_label("23. Lights of yours in the Sun, O Gods")
    assert dotted is not None and dotted.label == "23"

    crossref = _read_label("18 = IX. 40.")
    assert crossref is not None and crossref.label == "18"

    # OCR of the 1976 reprint: "I" for "1". Repairable under a fixed confusion table.
    repaired = _read_label("I7 The stick which thou, God Agni, laidest round thee")
    assert repaired is not None and repaired.label == "17" and repaired.repaired

    # "S" has no unambiguous digit twin, so this stays unreadable rather than guessed.
    unreadable = _read_label("S5 She who awakens sounds of joy")
    assert unreadable is not None and unreadable.label == "" and unreadable.printed == "S5"

    # A stray numeral beside the real one: both readings carried, neither preferred yet.
    doubled = _read_label("6 56 This is thine ordered place of birth")
    assert doubled is not None and doubled.label == "" and doubled.candidates == (6, 56)

    # A numeral mid-verse before a lower-case word is not a label.
    assert _read_label("1 regions, to the trees with their green tresses") is None
    assert _read_label("Thee for food. Thee for vigour.") is None


def _synthetic_units(labels: list[str]) -> list[TranslationUnit]:
    return [
        TranslationUnit(
            book=1,
            document_index=index,
            label_printed=label,
            label_repaired=None,
            values=tuple(int(part) for part in label.split(",")),
            lines=(f"body for printed label {label}",),
            printed_page=None,
        )
        for index, label in enumerate(labels)
    ]


def test_canonical_key_follows_the_printed_number_not_the_position(
    spine: CanonicalSpine,
) -> None:
    """The decisive test: printed labels out of positional order still address correctly.

    Unit at position 0 prints 3 and unit at position 2 prints 1. If the mapping were
    positional, position 0 would take mantra 1. It takes mantra 3, because that is what
    the source prints on it.
    """
    units = _synthetic_units(["3", "2", "1"])
    result = align_book(units, book=1, spine=spine, snapshot_sha256="x" * 64)
    by_key = {verse.canonical_key: verse.text for verse in result.verses}
    assert by_key["VG:YV:VSM:A01:V003"] == "body for printed label 3"
    assert by_key["VG:YV:VSM:A01:V001"] == "body for printed label 1"
    assert all(verse.alignment is Alignment.EXACT for verse in result.verses)


def test_two_units_printing_one_number_are_ambiguous_not_silently_merged(
    spine: CanonicalSpine,
) -> None:
    units = _synthetic_units(["1", "2", "2"])
    result = align_book(units, book=1, spine=spine, snapshot_sha256="x" * 64)
    assert [verse.mantra for verse in result.verses] == [1]
    assert {unit.alignment for unit in result.carried} == {Alignment.AMBIGUOUS}
    assert len(result.carried) == 2
    assert {unit.text for unit in result.carried} == {"body for printed label 2"}


def test_a_number_outside_the_book_is_unresolved_and_keeps_its_text(
    spine: CanonicalSpine,
) -> None:
    units = _synthetic_units(["1", "999"])
    result = align_book(units, book=1, spine=spine, snapshot_sha256="x" * 64)
    carried = [unit for unit in result.carried if unit.alignment is Alignment.UNRESOLVED]
    assert len(carried) == 1
    assert carried[0].text == "body for printed label 999"


# --------------------------------------------------------------------------------------
# Corpus-wide guards.
# --------------------------------------------------------------------------------------


@requires_snapshots
def test_every_page_prints_the_book_number_its_url_claims() -> None:
    """The URL is never the only witness: the page's own heading has to agree."""
    adapter = GriffithYajurvedaAdapter()
    snapshots = adapter.load_snapshots(SNAPSHOT_DIR)
    assert len(snapshots) == BOOK_COUNT
    for snapshot in snapshots:
        printed_book, lines = extract_lines(snapshot.path.read_bytes())
        assert printed_book == snapshot.book, snapshot.retrieval_url
        assert lines, snapshot.retrieval_url


@requires_snapshots
def test_shuffling_the_unit_order_does_not_change_the_mapping(spine: CanonicalSpine) -> None:
    """Permuting the units the caller hands over cannot move a single canonical key."""
    adapter = GriffithYajurvedaAdapter()
    rng = random.Random(20260907)
    for snapshot in adapter.load_snapshots(SNAPSHOT_DIR):
        printed_book, lines = extract_lines(snapshot.path.read_bytes())
        units = list(segment_units(printed_book, lines))
        straight = align_book(
            units, book=printed_book, spine=spine, snapshot_sha256=snapshot.sha256
        )
        shuffled_units = units[:]
        rng.shuffle(shuffled_units)
        shuffled = align_book(
            shuffled_units, book=printed_book, spine=spine, snapshot_sha256=snapshot.sha256
        )
        assert [verse.as_json() for verse in straight.verses] == [
            verse.as_json() for verse in shuffled.verses
        ], f"book {printed_book} mapping moved when the unit order changed"
        assert [unit.as_json() for unit in straight.carried] == [
            unit.as_json() for unit in shuffled.carried
        ]


@requires_snapshots
def test_position_and_printed_number_really_do_disagree(
    alignments: list[BookAlignment],
) -> None:
    """Keeps the order-free test honest: if they never disagreed it would prove nothing."""
    disagreements = 0
    for alignment in alignments:
        for position, verse in enumerate(alignment.verses):
            if verse.mantra != position + 1:
                disagreements += 1
    assert disagreements > 0, "no book's numbering departs from position; test is vacuous"


@requires_snapshots
def test_no_canonical_key_is_claimed_twice(alignments: list[BookAlignment]) -> None:
    keys = Counter(verse.canonical_key for a in alignments for verse in a.verses)
    duplicated = {key: count for key, count in keys.items() if count > 1}
    assert duplicated == {}


@requires_snapshots
def test_a_key_is_either_aligned_or_a_gap_never_both(
    alignments: list[BookAlignment], spine: CanonicalSpine
) -> None:
    aligned = {verse.canonical_key for a in alignments for verse in a.verses}
    gaps = {gap.canonical_key for a in alignments for gap in a.gaps}
    assert aligned & gaps == set()
    assert aligned | gaps == set(spine.keys.values())


@requires_snapshots
def test_the_five_counts_close_over_the_whole_accounting_universe(
    alignments: list[BookAlignment], spine: CanonicalSpine
) -> None:
    """Universe = every canonical mantra, plus every unit that binds to none of them."""
    summary = summarize(alignments, spine)
    assert (
        summary["EXACT"] + summary["STRUCTURAL_DIVERGENCE"] + summary["SOURCE_GAP"]
        == summary["canonical_mantra_count"]
        == 1975
    )
    assert summary["total_accounted"] == 1975 + summary["AMBIGUOUS"] + summary["UNRESOLVED"]
    assert summary["english_coverage"] == summary["EXACT"] + summary["STRUCTURAL_DIVERGENCE"]
    assert summary["books"] == BOOK_COUNT


@requires_snapshots
def test_every_canonical_key_emitted_exists_in_the_release(
    alignments: list[BookAlignment], spine: CanonicalSpine
) -> None:
    """No key is ever formatted by this adapter; every one is looked up in the release."""
    released = set(spine.keys.values())
    for alignment in alignments:
        for verse in alignment.verses:
            assert verse.canonical_key in released
            assert spine.keys[(verse.adhyaya, verse.mantra)] == verse.canonical_key


@requires_snapshots
def test_no_unit_text_is_dropped(spine: CanonicalSpine) -> None:
    """Every unit the parser saw survives, either bound to a key or carried whole."""
    adapter = GriffithYajurvedaAdapter()
    for snapshot in adapter.load_snapshots(SNAPSHOT_DIR):
        printed_book, lines = extract_lines(snapshot.path.read_bytes())
        units = segment_units(printed_book, lines)
        result = align_book(units, book=printed_book, spine=spine, snapshot_sha256=snapshot.sha256)
        surviving = {verse.text for verse in result.verses}
        surviving |= {unit.text for unit in result.carried}
        missing = [unit.label_printed for unit in units if unit.text not in surviving]
        assert missing == [], f"book {printed_book} dropped units {missing}"
        assert result.unit_count == len(units)


@requires_snapshots
def test_the_printed_numbering_ends_where_the_canonical_book_ends(
    spine: CanonicalSpine,
) -> None:
    """An end-to-end anchor: both spines must terminate together, or be reported.

    38 of 40 books close exactly on the canonical mantra count, which is what makes the
    per-verse claims credible rather than merely locally consistent. The two that do not
    are recorded here as known, reported divergences, not tolerated silently.
    """
    adapter = GriffithYajurvedaAdapter()
    mismatched: dict[int, tuple[int | None, int]] = {}
    for snapshot in adapter.load_snapshots(SNAPSHOT_DIR):
        printed_book, lines = extract_lines(snapshot.path.read_bytes())
        labels = [value for unit in segment_units(printed_book, lines) for value in unit.values]
        last = labels[-1] if labels else None
        if last != spine.counts[printed_book]:
            mismatched[printed_book] = (last, spine.counts[printed_book])
    assert set(mismatched) <= {12, 36}, mismatched
    assert len(mismatched) <= 2


@requires_snapshots
def test_a_divergent_numbering_spine_is_refused_rather_than_shifted(
    alignments: list[BookAlignment],
) -> None:
    """Book 12 prints 118 labels for 117 mantras and prints one verse twice.

    Either copy could be the spurious one, so no shift is applied: the tail is carried as
    UNRESOLVED with its text intact and the keys it would have claimed are reported gaps.
    """
    divergent = {a.book: a.spine_divergence_from for a in alignments if a.spine_divergence_from}
    assert divergent == {12: 97}
    book12 = next(a for a in alignments if a.book == 12)
    refused = [u for u in book12.carried if u.alignment is Alignment.UNRESOLVED]
    assert refused, "the divergent tail must be carried, not dropped"
    assert all(unit.text.strip() for unit in refused)
    assert max(verse.mantra for verse in book12.verses) < 97


@requires_snapshots
def test_printed_omissions_are_reported_as_gaps_not_invented(
    alignments: list[BookAlignment],
) -> None:
    """Griffith replaces VSM 23.20-31 with rows of dots; nothing may be inferred there."""
    book23 = next(a for a in alignments if a.book == 23)
    omitted = {gap.mantra for gap in book23.gaps if gap.defect.value == "PRINTED_OMISSION"}
    assert omitted == set(range(20, 32))


@requires_snapshots
def test_the_stage_payload_is_deterministic(
    alignments: list[BookAlignment], spine: CanonicalSpine
) -> None:
    first = build_stage(
        alignments, spine=spine, snapshot_id=SNAPSHOT_ID, canonical_release="yajurveda_vsm_v1"
    )
    second = build_stage(
        GriffithYajurvedaAdapter().align(SNAPSHOT_DIR, spine),
        spine=spine,
        snapshot_id=SNAPSHOT_ID,
        canonical_release="yajurveda_vsm_v1",
    )
    dumped = json.dumps(first, ensure_ascii=False, indent=2, sort_keys=True)
    assert dumped == json.dumps(second, ensure_ascii=False, indent=2, sort_keys=True)
    assert "\r" not in dumped
    assert first["work_id"] == "VG:WORK:YV:VSM"
    assert first["source_id"] == "SACRED_TEXTS"
