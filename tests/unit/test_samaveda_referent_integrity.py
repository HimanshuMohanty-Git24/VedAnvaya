"""Pins the Samaveda referent-integrity defects found by SAMAVEDA_CANONICAL_IDENTITY_FINAL_CLOSURE.

**These tests assert a KNOWN-DEFECTIVE state on purpose.** They are characterisation tests, not
statements about desired behaviour. Each one encodes the exact defect set measured against the
pinned GRETIL artifact on 2026-09-07, so that:

* a **repair** breaks the test and forces the recorded ledger to be updated in the same change,
  rather than the record silently drifting from the data; and
* a **regression** that introduces a new collision or phantom also breaks the test.

That bidirectional property is the point. The defect set previously lived only in prose, where it
drifted: the mechanism recorded for the 1868-vs-1875 gap was wrong in six places, three of them
YAML registries a build reads.

Why this file exists at all: the repository has **no** mechanism binding a canonical key to its
text. ``Passage`` carries no text field, ``qa/checks.py`` references ``text_original`` exactly once
(a UTF-8 encodability assert), and ``stable_uuid_deterministic`` recomputes the UUID from the URN
alone -- so repairing a collided address moves the verse behind a key while every existing gate
stays green. Until a ``content_sha256`` invariant exists, these tests are the only thing standing
between that defect set and silent change.

See ``docs/reports/SAMAVEDA_COUNT_RECONCILIATION.md`` and
``data/source_registry/samaveda_count_ledger.yaml``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from vedagraph.identity import sv_mantra_identity
from vedagraph.ingest.adapters.samaveda_gretil import (
    SamavedaGRETILAdapter,
    SamavedaParseResult,
)

#: The artifact whose sha256 is recorded as ``structure_evidence_sha256`` for VG:WORK:SV:KAU.
ARTIFACT = Path(
    "data/raw/gretil/2026-09-07/"
    "91c28c0394e94dccc9bad12a08224fbcde0a1194402b610df26647621ed92456.xml"
)
LEDGER = Path("data/source_registry/samaveda_count_ledger.yaml")

#: Measured directly from the artifact. Four correct counts of four different things.
PRINTED_MARKERS = 1875
MARKERS_LIFTABLE = 1871
DISTINCT_ADDRESSES = 1868
MINTED_KEYS = 1866

#: The seven addresses that absorb nine printed verses, with the markers each absorbs.
COLLIDED: dict[tuple[int, int, int, int, int], list[int]] = {
    (4, 1, 1, 6, 3): [666, 667, 668],
    (4, 5, 2, 6, 3): [1282, 1288],
    (4, 5, 2, 7, 4): [1283, 1295],
    (4, 5, 2, 8, 5): [1284, 1302],
    (4, 5, 2, 10, 1): [1307, 1308, 1309],
    (4, 6, 2, 16, 0): [1421, 1422],
    (4, 8, 2, 8, 2): [1679, 1680],
}

#: Addresses carrying no running number the current adapter can lift. Only two of the six are
#: genuine; the other four are printed in the source and lost to regex strictness.
ZERO_MARKER: set[tuple[int, int, int, int, int]] = {
    (4, 4, 1, 2, 2),  # printed '.. 1035'; stray 'rm' label prefix kills the line
    (4, 4, 2, 1, 12),  # GENUINE -- its 'c' pada was mislabelled '13c'
    (4, 4, 2, 2, 6),  # printed '. 1133' with a single danda
    (4, 5, 1, 6, 2),  # printed corrupt as '121clsdir'
    (4, 7, 3, 10, 3),  # printed '. 1592' with a single danda
    (4, 8, 2, 8, 1),  # GENUINE -- its 'c' pada was mislabelled '0802c'
}
GENUINELY_MARKERLESS: set[tuple[int, int, int, int, int]] = {
    (4, 4, 2, 1, 12),
    (4, 8, 2, 8, 1),
}

#: A canonical key minted for a verse that does not exist.
PHANTOM_ADDRESS = (4, 4, 2, 1, 13)
PHANTOM_KEY = "VG:SV:KAU:A4:P04:R2:D01:V13"

#: Addresses whose first pada label is not 'a'. Each is a pada-assignment defect.
NON_A_HEAD: dict[tuple[int, int, int, int, int], list[int]] = {
    (1, 1, 1, 1, 2): [2],  # the documented 0101a pada bleed
    (1, 3, 1, 1, 8): [201],
    (4, 4, 2, 1, 13): [1127],  # the phantom
    (4, 8, 2, 8, 2): [1679, 1680],
}

#: Verse index 0 is undefined by the declared reference system; identity must fail closed.
ZERO_VERSE_INDEX: set[tuple[int, int, int, int, int]] = {(4, 3, 1, 4, 0), (4, 6, 2, 16, 0)}

PER_ARCIKA_ADDRESSES = {1: 585, 2: 55, 3: 10, 4: 1218}
PER_ARCIKA_MARKERS_LIFTABLE = {1: 585, 2: 55, 3: 10, 4: 1221}


def _address(verse: object) -> tuple[int, int, int, int, int]:
    return (
        verse.arcika,  # type: ignore[attr-defined]
        verse.prapathaka,  # type: ignore[attr-defined]
        verse.ardha,  # type: ignore[attr-defined]
        verse.dasati,  # type: ignore[attr-defined]
        verse.verse,  # type: ignore[attr-defined]
    )


@pytest.fixture(scope="module")
def parse() -> SamavedaParseResult:
    if not ARTIFACT.exists():
        pytest.skip(f"no pinned GRETIL Samaveda snapshot at {ARTIFACT}; run the fetch script")
    return SamavedaGRETILAdapter().parse_structure(ARTIFACT)


# ---------------------------------------------------------------------------
# The ledger must check its own arithmetic. The first draft of it summed to 6,
# not 7, because one of the nine surplus markers had been omitted.
# ---------------------------------------------------------------------------


def test_count_ledger_axis_arithmetic_is_self_consistent() -> None:
    ledger = yaml.safe_load(LEDGER.read_text(encoding="utf-8"))
    arithmetic = ledger["axis_arithmetic"]
    count_axis = ledger["count_axis_ledger"]

    positive = [entry for entry in count_axis if entry["count_delta"] > 0]
    negative = [entry for entry in count_axis if entry["count_delta"] < 0]

    assert len(positive) == arithmetic["count_axis_entries_with_positive_delta"]
    assert len(negative) == arithmetic["count_axis_entries_with_negative_delta"]
    assert sum(e["count_delta"] for e in count_axis) == arithmetic["count_axis_delta_sum"]
    assert arithmetic["count_axis_delta_sum"] == arithmetic["gap"]

    # The five "absent RNs" are lifting failures whose count effect is already booked on the
    # count axis. Summing the two axes is the double count the superseded record committed.
    assert (
        sum(e["count_delta"] for e in ledger["apparatus_read_ledger"])
        == arithmetic["apparatus_read_axis_delta_sum"]
        == 0
    )
    assert (
        sum(e["count_delta"] for e in ledger["canonical_key_defect_ledger"])
        == arithmetic["canonical_key_defect_axis_delta_sum"]
        == 0
    )
    assert (
        sum(e["surplus"] for e in ledger["collided_addresses"])
        == arithmetic["collided_addresses_surplus_sum"]
    )

    measured = ledger["measured"]
    assert (
        measured["printed_verse_terminal_markers"] - measured["distinct_structural_addresses"]
        == arithmetic["gap"]
    )
    assert ledger["unresolved_count_residue"] == 0


def test_count_ledger_matches_the_constants_this_module_asserts() -> None:
    """The YAML record and the executable pins must not drift apart."""
    measured = yaml.safe_load(LEDGER.read_text(encoding="utf-8"))["measured"]
    assert measured["printed_verse_terminal_markers"] == PRINTED_MARKERS
    assert measured["markers_liftable_by_current_adapter"] == MARKERS_LIFTABLE
    assert measured["distinct_structural_addresses"] == DISTINCT_ADDRESSES
    assert measured["minted_canonical_keys"] == MINTED_KEYS
    assert measured["collided_addresses"] == len(COLLIDED)
    assert measured["surplus_markers_on_collided_addresses"] == sum(
        len(v) - 1 for v in COLLIDED.values()
    )
    assert measured["addresses_with_no_printed_marker"] == len(GENUINELY_MARKERLESS)


# ---------------------------------------------------------------------------
# The four-number ladder, measured against the artifact.
# ---------------------------------------------------------------------------


def test_the_four_number_ladder(parse: SamavedaParseResult) -> None:
    addresses = {_address(v) for v in parse.verses}
    assert len(parse.verses) == DISTINCT_ADDRESSES
    assert len(addresses) == DISTINCT_ADDRESSES

    liftable = sum(len(v.running_numbers) for v in parse.verses)
    assert liftable == MARKERS_LIFTABLE

    # Two addresses carry verse index 0, which sv_mantra_identity refuses. That refusal is why
    # the minted key count is 1866 and not 1868, and it must stay a refusal.
    keyable = [v for v in parse.verses if v.verse >= 1]
    assert len(keyable) == MINTED_KEYS
    assert len({v.verse_key for v in keyable}) == MINTED_KEYS, "minted keys must be injective"

    assert {_address(v) for v in parse.verses if v.verse == 0} == ZERO_VERSE_INDEX
    for address in ZERO_VERSE_INDEX:
        with pytest.raises(ValueError):
            sv_mantra_identity(*address)


def test_per_arcika_counts(parse: SamavedaParseResult) -> None:
    addresses: dict[int, int] = {}
    markers: dict[int, int] = {}
    for verse in parse.verses:
        addresses[verse.arcika] = addresses.get(verse.arcika, 0) + 1
        markers[verse.arcika] = markers.get(verse.arcika, 0) + len(verse.running_numbers)
    assert addresses == PER_ARCIKA_ADDRESSES
    assert markers == PER_ARCIKA_MARKERS_LIFTABLE

    # The whole gap lives in the Uttararcika; the Purvarcika group is balanced at 650.
    purvarcika_group = sum(addresses[a] for a in (1, 2, 3))
    assert purvarcika_group == 650
    assert sum(markers[a] for a in (1, 2, 3)) == 650


# ---------------------------------------------------------------------------
# Referent integrity. These are the two blocking defects.
# ---------------------------------------------------------------------------


def test_seven_addresses_still_absorb_nine_printed_verses(parse: SamavedaParseResult) -> None:
    """Pins the collision set. A repair MUST update the ledger in the same change.

    The merge is concatenative rather than first-wins or last-wins, so the text behind each of
    these keys is a welded composite. Repairing them leaves the key, the URN and the UUID
    byte-identical while the verse behind them changes -- undetectably, because no gate binds a
    key to its text.
    """
    collided = {
        _address(v): list(v.running_numbers) for v in parse.verses if len(v.running_numbers) > 1
    }
    assert collided == COLLIDED
    assert sum(len(markers) - 1 for markers in collided.values()) == 9


def test_a_collided_address_holds_a_welded_composite(parse: SamavedaParseResult) -> None:
    """The merged text equals neither the first nor the last constituent."""
    adapter = SamavedaGRETILAdapter()
    verse = next(v for v in parse.verses if _address(v) == (4, 1, 1, 6, 3))
    assert verse.running_numbers == [666, 667, 668]
    # Six pada lines for what should be one verse of two.
    assert [line.line_label for line in verse.lines] == ["a", "c", "a", "c", "a", "c"]
    assert len(adapter.verse_text(verse)) == 197


def test_the_phantom_canonical_key_is_still_present(parse: SamavedaParseResult) -> None:
    """``VG:SV:KAU:A4:P04:R2:D01:V13`` identifies a verse that does not exist.

    Dasati (4,4,2,1) prints markers 1116..1127 -- twelve verses -- and VedaGraph mints thirteen
    addresses. Pada labels ``12a`` and ``13c`` are the two padas of ONE verse, marker 1127.
    Retracting this key later requires DELETING a minted canonical key, which ``ID_SPEC`` says
    demands a versioned migration with an explicit mapping.
    """
    unit = [v for v in parse.verses if (v.arcika, v.prapathaka, v.ardha, v.dasati) == (4, 4, 2, 1)]
    markers = sorted(rn for v in unit for rn in v.running_numbers)
    assert len(unit) == 13, "thirteen addresses minted"
    assert markers[0] == 1116 and markers[-1] == 1127
    assert markers[-1] - markers[0] + 1 == 12, "for a twelve-verse span"

    phantom = next(v for v in unit if _address(v) == PHANTOM_ADDRESS)
    assert phantom.verse_key == PHANTOM_KEY
    assert [line.line_label for line in phantom.lines] == ["c"], "a bare 'c' pada"
    assert phantom.running_numbers == [1127]

    predecessor = next(v for v in unit if _address(v) == (4, 4, 2, 1, 12))
    assert [line.line_label for line in predecessor.lines] == ["a"], "and a bare 'a' pada"
    assert predecessor.running_numbers == [], "which carries no marker of its own"


def test_the_naive_over_minting_detector_has_exactly_one_false_positive(
    parse: SamavedaParseResult,
) -> None:
    """The detector Agent F recommended for the adapter, and the refinement it needs.

    The naive form -- "flag a dasati that mints more addresses than its marker span" -- flags
    TWO units, and only one is a real defect. Recorded because implementing the naive check as
    an adapter defect code would emit a false positive on real data:

    * ``(4,4,2,1)`` is the genuine phantom. Its extra address has an INCOMPLETE pada set
      (``V12=[a]``, ``V13=[c]``), which is the signature: one verse split across two addresses.
    * ``(4,7,3,10)`` is a FALSE POSITIVE. All three of its addresses carry complete ``[a,c,e]``
      triads; the span merely looks short because printed marker 1592 is unliftable (single
      danda). Nothing is over-minted.

    So the sound detector is "over-minted AND at least one address has an incomplete pada set",
    or equivalently it must run only after the single-danda lifting repair (SV-ADAPTER-1).
    """
    units: dict[tuple[int, int, int, int], list[int]] = {}
    counts: dict[tuple[int, int, int, int], int] = {}
    for verse in parse.verses:
        unit = (verse.arcika, verse.prapathaka, verse.ardha, verse.dasati)
        units.setdefault(unit, []).extend(verse.running_numbers)
        counts[unit] = counts.get(unit, 0) + 1

    naive = {
        unit
        for unit, markers in units.items()
        if markers and counts[unit] > (max(markers) - min(markers) + 1)
    }
    assert naive == {(4, 4, 2, 1), (4, 7, 3, 10)}, (
        "if this set changes, update data/source_registry/samaveda_count_ledger.yaml "
        "in the same change"
    )

    # The refinement: a unit is genuinely over-minted only if some address inside it has an
    # incomplete pada set. Every address in (4,7,3,10) is complete, so it drops out.
    pada_counts: dict[tuple[int, int, int, int], set[int]] = {}
    for verse in parse.verses:
        unit = (verse.arcika, verse.prapathaka, verse.ardha, verse.dasati)
        pada_counts.setdefault(unit, set()).add(len(verse.lines))
    refined = {unit for unit in naive if len(pada_counts[unit]) > 1}
    assert refined == {(4, 4, 2, 1)}, "exactly one genuine phantom-bearing dasati"

    assert pada_counts[(4, 7, 3, 10)] == {3}, "all three addresses are complete a/c/e triads"
    assert pada_counts[(4, 4, 2, 1)] == {1, 2}, "the phantom unit mixes complete and half verses"


def test_addresses_whose_first_pada_label_is_not_a(parse: SamavedaParseResult) -> None:
    """The other detector Agent F named. Four addresses violate it, and one is the phantom."""
    offenders = {
        _address(v): list(v.running_numbers)
        for v in parse.verses
        if v.lines and v.lines[0].line_label != "a"
    }
    assert offenders == NON_A_HEAD
    assert PHANTOM_ADDRESS in offenders


def test_six_addresses_carry_no_liftable_marker_but_only_two_are_genuine(
    parse: SamavedaParseResult,
) -> None:
    """Four of the six are printed in the source and lost to adapter regex strictness.

    That distinction is the whole content of the count-mechanism correction: the superseded
    record treated all of them as source gaps, which published a parser configuration as a
    philological result.
    """
    without = {_address(v) for v in parse.verses if not v.running_numbers}
    assert without == ZERO_MARKER
    assert GENUINELY_MARKERLESS < without
    assert len(without) - len(GENUINELY_MARKERLESS) == 4


# ---------------------------------------------------------------------------
# Identity governance. Identity must stay unfrozen while the above holds.
# ---------------------------------------------------------------------------


def test_samaveda_identity_stays_unfrozen_while_referents_are_defective() -> None:
    """Ties the freeze directly to the defect set, so the two cannot drift apart.

    ``tests/unit/test_registry.py`` already asserts ``key_pattern is None``. This test records
    WHY, which that one does not: not the source-edition question, but the collided referents and
    the phantom key pinned above. Whoever freezes must delete this test deliberately.
    """
    works = yaml.safe_load(Path("data/registry/works.yaml").read_text(encoding="utf-8"))["works"]
    samaveda = next(w for w in works if w["work_id"] == "VG:WORK:SV:KAU")
    assert samaveda["key_pattern"] is None
    assert samaveda["identity_status"] == "RESEARCH_REQUIRED"

    blockers = yaml.safe_load(
        Path("data/source_registry/four_veda_canonical_sanskrit_blockers.yaml").read_text(
            encoding="utf-8"
        )
    )
    dimensions = next(b for b in blockers["blockers"] if b["work_id"] == "VG:WORK:SV:KAU")[
        "dimensions"
    ]
    assert dimensions["referent_integrity"] == "OPEN_ENGINEERING"
    assert dimensions["arcika_arity"] == "OPEN_PHILOLOGICAL_REVIEW"
    # Settled positively in the same run, and recorded so it is not re-litigated.
    assert dimensions["addressing_edition_independence"] == "RESOLVED"
    assert dimensions["structural_count_discrepancy"] == "RESOLVED"


def test_the_candidate_key_is_order_independent(parse: SamavedaParseResult) -> None:
    """Coordinates come from the declared label, never from document or parse position.

    This is the one property that survived the adversarial pass intact, and it is worth pinning:
    it is what makes the key shape sound even though the referents are not.
    """
    keys = [v.verse_key for v in parse.verses if v.verse >= 1]
    assert keys == sorted(set(keys), key=keys.index), "no duplicate keys in parse order"
    again = SamavedaGRETILAdapter().parse_structure(ARTIFACT)
    assert [v.verse_key for v in again.verses if v.verse >= 1] == keys
