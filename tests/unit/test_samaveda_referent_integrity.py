"""Executable pins for repaired Samaveda referent integrity.

This file replaces a characterisation suite that pinned the DEFECTIVE state -- seven
addresses absorbing nine printed verses, a phantom thirteenth verse, a four-number count
ladder. Those numbers were correct descriptions of a broken build and every one of them is
now obsolete. What survives from that suite is its two genuine invariants: that coordinates
never come from document position, and that minted keys are injective.

The central claim under test is that a byte-identical UUID is NOT evidence that a key still
denotes the same verse. ``stable_uuid_deterministic`` recomputes ``uuid5(namespace, urn)``
from the URN alone, so it returns the identical verdict across a referent swap. The tests
below therefore assert properties of the BINDING between a key and its source occurrence,
not just properties of the key.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from vedagraph.config.registry import load_works
from vedagraph.identity import (
    SV_COLLECTION_LEVELS,
    SV_MAX_LEVEL_VALUE,
    SamavedaCollection,
    sv_container_identity,
    sv_mantra_identity,
)
from vedagraph.ingest.adapters.samaveda_wikisource import (
    MarkerDialect,
    PageKind,
    ReferentClass,
    SamavedaWikisourceAdapter,
    classify_page,
    is_gana_line,
    resolve_local_indices,
)
from vedagraph.models import PassageReferentBinding, ReferentMigration
from vedagraph.referent import (
    MigrationClass,
    ReferentDriftError,
    ReferentFingerprint,
    ReferentVerdict,
    assert_no_referent_drift,
    compare_referents,
    duplicate_referents,
    read_baseline,
    text_fingerprints,
)

REPO = Path(__file__).resolve().parents[2]
WORKS = REPO / "data" / "registry" / "works.yaml"
BLOCKERS = REPO / "data" / "source_registry" / "four_veda_canonical_sanskrit_blockers.yaml"
MIGRATIONS = REPO / "data" / "source_registry" / "samaveda_referent_migrations.jsonl"
LEDGER = REPO / "data" / "source_registry" / "samaveda_count_ledger.yaml"
BASELINE = REPO / "tests" / "fixtures" / "identity" / "sv_referent_baseline.jsonl"
WIKISOURCE_DIR = REPO / "data" / "raw" / "wikisource_sa"

# The traditional Kauthuma total, corroborated independently of the Pandey lineage.
TRADITIONAL_TOTAL = 1875
# Purvarcika group = Chanda 585 + Aranya 55 + Mahanamnya 10. The repaired build reaches
# this exactly, from the selected witness alone.
PURVARCIKA_GROUP = 650
CHANDA_VERSES = 585
ARANYA_VERSES = 55
MAHANAMNYA_VERSES = 10
# Keys the repaired build mints. The 31-verse shortfall against 1875 is a COVERAGE gap
# with a named cause, not an identity ambiguity: see test_the_count_equation_closes.
MINTED_KEYS = 1844
# The dasati groups whose partition the second witness contradicts, so no key is minted
# anywhere inside them. Named here so a rebuild cannot quietly start minting one.
UNCORROBORATED_GROUPS = (
    "VG:SV:KAU:UTTARA:P04:R01:D22",
    "VG:SV:KAU:UTTARA:P04:R02:D14",
    "VG:SV:KAU:UTTARA:P05:R01:D17",
    "VG:SV:KAU:UTTARA:P05:R02:D05",
)


# --------------------------------------------------------------------------- fixtures


@pytest.fixture(scope="module")
def pages() -> list:
    """Every pinned Samaveda arcika samhita page, segmented and resolved."""
    if not WIKISOURCE_DIR.exists():
        pytest.skip("Sanskrit Wikisource Samaveda snapshots are not pinned locally")
    adapter = SamavedaWikisourceAdapter()
    parsed = []
    for meta in sorted(WIKISOURCE_DIR.rglob("*.metadata.json")):
        sha = meta.name.split(".")[0]
        body = meta.with_name(f"{sha}.php")
        if not body.exists():
            continue
        try:
            payload = json.loads(body.read_text(encoding="utf-8"))
        except ValueError:
            continue
        parse = payload.get("parse")
        if not parse:
            continue
        title = parse.get("title", "")
        if "/संहिता/पूर्वार्चिकः" not in title and "/संहिता/उत्तरार्चिकः" not in title:
            continue
        parsed.append(adapter.parse_page(body, snapshot_sha256=sha))
    if not parsed:
        pytest.skip("no Samaveda arcika snapshots found")
    resolve_local_indices(parsed)
    return sorted(parsed, key=lambda page: page.page_title)


@pytest.fixture(scope="module")
def occurrences(pages: list) -> list:
    return [item for page in pages for item in page.occurrences]


# ------------------------------------------------------------------- the frozen scheme


def test_the_four_collection_key_shapes() -> None:
    """Each key carries exactly the levels its collection declares, and no others."""
    chanda, chanda_urn, _ = sv_mantra_identity(
        SamavedaCollection.CHANDA, prapathaka=1, dasati=1, verse=1
    )
    assert chanda == "VG:SV:KAU:CHANDA:P01:D01:V01"
    assert chanda_urn == (
        "urn:vedagraph:mantra:samaveda:kauthuma:chanda:prapathaka:1:dasati:1:verse:1"
    )

    aranya, aranya_urn, _ = sv_mantra_identity(SamavedaCollection.ARANYA, dasati=3, verse=1)
    assert aranya == "VG:SV:KAU:ARANYA:D03:V01"
    assert aranya_urn == "urn:vedagraph:mantra:samaveda:kauthuma:aranya:dasati:3:verse:1"

    mahanamnya, mahanamnya_urn, _ = sv_mantra_identity(SamavedaCollection.MAHANAMNYA, verse=7)
    assert mahanamnya == "VG:SV:KAU:MAHANAMNYA:V07"
    assert mahanamnya_urn == "urn:vedagraph:mantra:samaveda:kauthuma:mahanamnya:verse:7"

    uttara, uttara_urn, _ = sv_mantra_identity(
        SamavedaCollection.UTTARA, prapathaka=6, ardha=3, dasati=16, verse=2
    )
    assert uttara == "VG:SV:KAU:UTTARA:P06:R03:D16:V02"
    assert uttara_urn == (
        "urn:vedagraph:mantra:samaveda:kauthuma:uttara:prapathaka:6:ardha:3:dasati:16:verse:2"
    )


def test_the_top_slot_is_a_name_so_no_ordinal_can_be_reinterpreted() -> None:
    """The collision the repair exists to remove is unrepresentable.

    Slot-1 value 2 meant Aranyarcika in the Pandey lineage and Uttararcika in six
    independent witnesses. Under a named slot the two are different tokens, so no
    reinterpretation of an ordinal can silently move 1,225 verses.
    """
    keys = {
        collection: sv_mantra_identity(
            collection,
            verse=1,
            **{level: 1 for level in SV_COLLECTION_LEVELS[collection]},
        )[0]
        for collection in SamavedaCollection
    }
    assert len(set(keys.values())) == len(SamavedaCollection)
    for collection, key in keys.items():
        assert f":{collection.value}:" in f"{key}:"
    # No key contains an arcika ordinal slot at all.
    assert not any(":A1:" in key or ":A2:" in key for key in keys.values())


def test_a_level_the_collection_does_not_declare_is_refused() -> None:
    """The superseded scheme wrote a literal 0 here; refusing is the repair.

    Writing 0 for an absent level made the rejected edition's flattening choice part of
    canonical identity, and it made "the text has no ardha here" indistinguishable from
    "the edition declined to number it".
    """
    with pytest.raises(ValueError, match="declares no ardha"):
        sv_mantra_identity(SamavedaCollection.CHANDA, prapathaka=1, ardha=2, dasati=1, verse=1)
    with pytest.raises(ValueError, match="declares no prapathaka"):
        sv_mantra_identity(SamavedaCollection.ARANYA, prapathaka=1, dasati=1, verse=1)
    with pytest.raises(ValueError, match="declares no dasati"):
        sv_mantra_identity(SamavedaCollection.MAHANAMNYA, dasati=1, verse=1)


def test_a_level_the_collection_does_declare_is_required() -> None:
    with pytest.raises(ValueError, match="is required"):
        sv_mantra_identity(SamavedaCollection.CHANDA, prapathaka=1, verse=1)
    with pytest.raises(ValueError, match="is required"):
        sv_mantra_identity(SamavedaCollection.UTTARA, prapathaka=1, ardha=1, verse=1)


def test_zero_and_negative_and_overwide_values_fail_closed() -> None:
    with pytest.raises(ValueError, match="positive"):
        sv_mantra_identity(SamavedaCollection.ARANYA, dasati=1, verse=0)
    with pytest.raises(ValueError, match="positive"):
        sv_mantra_identity(SamavedaCollection.ARANYA, dasati=0, verse=1)
    with pytest.raises(ValueError, match="positive"):
        sv_mantra_identity(SamavedaCollection.ARANYA, dasati=-1, verse=1)
    with pytest.raises(ValueError, match="exceeds the fixed key width"):
        sv_mantra_identity(SamavedaCollection.ARANYA, dasati=1, verse=SV_MAX_LEVEL_VALUE + 1)


def test_the_literal_zero_is_refused_on_every_path_for_every_collection() -> None:
    """Exhaustive, because the one-case version of this test passed while the bug was live.

    An earlier revision of ``_sv_levels`` read ``value not in (None, 0)``, so a literal 0
    on an undeclared level was silently swallowed by the MANTRA path while the CONTAINER
    path refused the same input. A single hand-picked case can miss an asymmetry like that;
    4 collections x 3 levels x 2 paths cannot.
    """
    levels = ("prapathaka", "ardha", "dasati")
    for collection in SamavedaCollection:
        declared = SV_COLLECTION_LEVELS[collection]
        for level in levels:
            supplied = {name: 1 for name in declared}
            supplied[level] = 0
            with pytest.raises(ValueError):
                sv_mantra_identity(collection, verse=1, **supplied)
            with pytest.raises(ValueError):
                sv_container_identity(collection, **supplied)
        with pytest.raises(ValueError, match="positive"):
            sv_mantra_identity(collection, verse=0, **{n: 1 for n in declared})


def test_keys_are_fixed_width_prefix_free_and_sort_in_coordinate_order() -> None:
    """Lexicographic order must equal coordinate order, and no key may prefix another.

    The superseded key left the arcika and ardha slots unpadded, so ``A10`` sorted before
    ``A2``, and the verse slot was two digits at ``V01`` and three at ``V100``.
    """
    coordinates = [
        (prapathaka, ardha, dasati, verse)
        for prapathaka in (1, 2, 10)
        for ardha in (1, 2, 10)
        for dasati in (1, 5, 23)
        for verse in (1, 3, 12)
    ]
    keyed = [
        (
            (prapathaka, ardha, dasati, verse),
            sv_mantra_identity(
                SamavedaCollection.UTTARA,
                prapathaka=prapathaka,
                ardha=ardha,
                dasati=dasati,
                verse=verse,
            )[0],
        )
        for prapathaka, ardha, dasati, verse in coordinates
    ]
    assert [key for _, key in sorted(keyed)] == sorted(key for _, key in keyed)
    widths = {len(key) for _, key in keyed}
    assert len(widths) == 1, f"mixed key widths: {widths}"

    containers = [
        sv_container_identity(SamavedaCollection.UTTARA, prapathaka=1),
        sv_container_identity(SamavedaCollection.UTTARA, prapathaka=1, ardha=1),
        sv_container_identity(SamavedaCollection.UTTARA, prapathaka=1, ardha=1, dasati=1),
    ]
    mantra = sv_mantra_identity(SamavedaCollection.UTTARA, prapathaka=1, ardha=1, dasati=1, verse=1)
    # A container key IS a prefix of its descendants -- that is the parent chain -- but a
    # mantra key must never be a prefix of another mantra key.
    assert all(mantra[0].startswith(container[0]) for container in containers)
    assert mantra[1].startswith("urn:vedagraph:mantra:")
    assert containers[-1][1].startswith("urn:vedagraph:section:")


def test_container_and_mantra_urns_cannot_collide() -> None:
    for collection in SamavedaCollection:
        levels = {level: 1 for level in SV_COLLECTION_LEVELS[collection]}
        container = sv_container_identity(collection, **levels)
        mantra = sv_mantra_identity(collection, verse=1, **levels)
        assert container[1] != mantra[1]
        assert container[2] != mantra[2]


def test_container_levels_must_be_outermost_first_without_gaps() -> None:
    with pytest.raises(ValueError, match="outermost-first"):
        sv_container_identity(SamavedaCollection.UTTARA, ardha=2)


# ------------------------------------------------------- the registry states it is frozen


def test_the_work_registry_declares_the_frozen_samaveda_key() -> None:
    """Whoever unfreezes must change this deliberately."""
    works = {work.work_id: work for work in load_works(WORKS)}
    samaveda = works["VG:WORK:SV:KAU"]
    assert samaveda.identity_status == "FINAL"
    assert samaveda.key_pattern is not None
    assert "{collection}" in samaveda.key_pattern
    assert ":A{arcika}" not in samaveda.key_pattern
    assert samaveda.urn_pattern is not None
    assert samaveda.hierarchy == ["Collection", "Prapathaka", "Ardha", "Dasati", "Verse"]
    # Coverage is tracked separately from identity, and is honestly incomplete.
    assert samaveda.coverage_status == "INCOMPLETE_BOUNDED"


def test_the_blocker_registry_records_the_referent_dimensions_as_resolved() -> None:
    payload = yaml.safe_load(BLOCKERS.read_text(encoding="utf-8"))
    text = json.dumps(payload)
    assert "referent_integrity" in text
    samaveda = _find_samaveda_block(payload)
    dimensions = samaveda["dimensions"]
    assert dimensions["referent_integrity"] == "RESOLVED"
    assert dimensions["arcika_arity"] == "RESOLVED"


def _find_samaveda_block(node: object) -> dict:
    if isinstance(node, dict):
        if node.get("veda") == "Samaveda" and "dimensions" in node:
            return node
        for value in node.values():
            found = _find_samaveda_block(value)
            if found:
                return found
    if isinstance(node, list):
        for value in node:
            found = _find_samaveda_block(value)
            if found:
                return found
    return {}


# ------------------------------------------------------------------- source segmentation


def test_page_titles_are_read_against_each_collection_declared_shape() -> None:
    """Slot 3 means three different things in this witness, so it is never read by position.

    The dotted address in a page title is prapathaka under ``1.1.x``, dasati under
    ``1.2.x`` and ardha under ``2.x.y``. A positional read mis-keys.
    """
    chanda = classify_page(
        "सामवेदः/कौथुमीया/संहिता/पूर्वार्चिकः/छन्द आर्चिकः/1.1.1 प्रथमप्रपाठकः/1.1.1.5 पञ्चमी दशतिः"
    )
    assert chanda is not None
    assert chanda.collection is SamavedaCollection.CHANDA
    assert chanda.kind is PageKind.CHANDA_DASATI
    assert (chanda.prapathaka, chanda.dasati) == (1, 5)
    assert chanda.ardha is None

    aranya = classify_page("सामवेदः/कौथुमीया/संहिता/पूर्वार्चिकः/अथारण्यार्चिकः/1.2.3 तृतीया दशतिः")
    assert aranya is not None
    assert aranya.collection is SamavedaCollection.ARANYA
    assert aranya.dasati == 3
    assert aranya.prapathaka is None

    uttara = classify_page("सामवेदः/कौथुमीया/संहिता/उत्तरार्चिकः/2.6 षष्ठप्रपाठकः/2.6.3 तृतीयोऽर्द्धः")
    assert uttara is not None
    assert uttara.collection is SamavedaCollection.UTTARA
    assert (uttara.prapathaka, uttara.ardha) == (6, 3)
    # The dasati is NOT in the title for an Uttararcika ardha page; it is printed inside.
    assert uttara.dasati is None

    mahanamnya = classify_page("सामवेदः/कौथुमीया/संहिता/पूर्वार्चिकः/महानाम्न्यार्चिकः")
    assert mahanamnya is not None
    assert mahanamnya.kind is PageKind.MAHANAMNYA


def test_gana_lines_are_detected_by_notation_not_by_position() -> None:
    """Gana is a separate work and carries its own numbering.

    The gana sections are written in the Samaveda svara notation, which lives in the
    Devanagari Extended combining range. Excluding them by notation rather than by
    position is what keeps a gana verse number out of the arcika running series.
    """
    gana = "पा꣢न्त꣣मा꣢ वो꣣ अ꣡न्ध꣢स꣣ इ꣡न्द्र꣢म꣣भि꣡ प्र गा꣢꣯यत ।। 1।।"
    arcika = "अग्न आ याहि वीतये गृणानो हव्यदातये ।"
    assert is_gana_line(gana)
    assert not is_gana_line(arcika)


def test_every_marker_dialect_the_source_uses_is_lifted(occurrences: list) -> None:
    """Four spellings of one boundary, all accepted, and which matched is recorded.

    A single-notation reader loses whole pages silently: the double-danda-only regex this
    adapter replaced found 1,195 of 1,875 markers and reported nothing wrong.
    """
    seen = {item.marker_dialect for item in occurrences if item.marker_dialect}
    assert MarkerDialect.DOUBLE_DANDA in seen
    assert MarkerDialect.TWO_DANDA in seen
    assert MarkerDialect.ASCII_PIPES in seen
    assert MarkerDialect.UNTERMINATED in seen
    assert MarkerDialect.SINGLE_DANDA in seen
    # The dialect whose omission cost a freeze: "...carsaninam 713 ॥", no opening
    # separator. Read as an ordinary pada line, it welded two printed verses onto one key.
    assert MarkerDialect.NO_OPENING_SEPARATOR in seen


def test_a_marker_with_no_preceding_text_delimits_no_verse(pages: list) -> None:
    """It is refused, and the refusal is recorded rather than silently dropped."""
    for page in pages:
        for item in page.occurrences:
            assert item.text, f"empty verse emitted on {page.page_title}"
    codes = {defect.defect_code for page in pages for defect in page.defects}
    assert "MARKER_WITHOUT_TEXT" in codes


def test_the_local_verse_index_is_derived_from_printed_arithmetic(occurrences: list) -> None:
    """Never from position in the document.

    Within a dasati the source prints a contiguous ascending run, so the local index is
    ``running - first + 1``. Where that run does not close the index is REFUSED, because a
    positional fallback would silently renumber every verse after the break.
    """
    groups: dict[tuple, list] = {}
    for item in occurrences:
        key = (
            item.collection.value,
            item.prapathaka or 0,
            item.ardha or 0,
            item.dasati or 0,
        )
        groups.setdefault(key, []).append(item)

    for members in groups.values():
        resolved = [m for m in members if m.local_index is not None]
        if not resolved:
            continue
        runs = sorted(m.running_number or 0 for m in resolved)
        if runs != list(range(runs[0], runs[0] + len(runs))):
            # Non-contiguous groups must not have produced an index at all.
            assert all(m.referent_class is not ReferentClass.ONE_TO_ONE for m in resolved)
            continue
        first = runs[0]
        for member in resolved:
            assert member.local_index == (member.running_number or 0) - first + 1


def test_segmentation_does_not_depend_on_document_order(pages: list) -> None:
    """Re-parsing the same snapshots must produce identical addresses.

    The one genuine invariant inherited from the superseded suite.
    """
    adapter = SamavedaWikisourceAdapter()
    sample = [page for page in pages if page.occurrences][:6]
    for page in sample:
        matching = list(WIKISOURCE_DIR.rglob(f"{page.snapshot_sha256}.php"))
        assert matching, page.snapshot_sha256
        again = adapter.parse_page(matching[0], snapshot_sha256=page.snapshot_sha256)
        resolve_local_indices([again])
        assert [
            (item.collection, item.prapathaka, item.ardha, item.dasati, item.local_index)
            for item in again.occurrences
        ] == [
            (item.collection, item.prapathaka, item.ardha, item.dasati, item.local_index)
            for item in page.occurrences
        ]


# ------------------------------------------------------------------------ referent audit


def test_no_two_verses_resolve_onto_one_canonical_address(occurrences: list) -> None:
    """Zero two-referent/one-key collisions. The whole point of the repair."""
    minted: dict[str, list[int | None]] = {}
    for item in occurrences:
        if item.local_index is None:
            continue
        key = sv_mantra_identity(
            item.collection,
            verse=item.local_index,
            prapathaka=item.prapathaka,
            ardha=item.ardha,
            dasati=item.dasati,
        )[0]
        minted.setdefault(key, []).append(item.running_number)
    collided = {key: runs for key, runs in minted.items() if len(runs) > 1}
    assert collided == {}, f"addresses absorbing more than one printed verse: {collided}"


def test_the_purvarcika_group_reaches_the_traditional_count_exactly(
    occurrences: list,
) -> None:
    """585 + 55 + 10 = 650, from the selected witness alone.

    This is the strongest single corroboration in the repair: three collections whose
    extents are agreed by every witness, reproduced exactly with no gap and no surplus.
    """
    per_collection: dict[str, int] = {}
    for item in occurrences:
        per_collection[item.collection.value] = per_collection.get(item.collection.value, 0) + 1
    assert per_collection[SamavedaCollection.CHANDA.value] == CHANDA_VERSES
    assert per_collection[SamavedaCollection.ARANYA.value] == ARANYA_VERSES
    assert per_collection[SamavedaCollection.MAHANAMNYA.value] == MAHANAMNYA_VERSES
    assert CHANDA_VERSES + ARANYA_VERSES + MAHANAMNYA_VERSES == PURVARCIKA_GROUP


def test_the_count_equation_closes(occurrences: list) -> None:
    """1875 = 1873 printed distinct markers + 2 the selected witness does not print.

    This list was ``[713, 1179, 1315]`` until the adversarial pass found that **713 IS
    printed** -- as ``...carsaninam 713 ॥``, a marker with no opening separator, which the
    lifter read as an ordinary pada line and welded onto verse 714. The lesson is recorded
    rather than quietly fixed: an "absent from the source" figure is a claim about the
    PARSER until every dialect the source uses has been enumerated.
    """
    printed = {item.running_number for item in occurrences if item.running_number}
    missing = sorted(set(range(1, TRADITIONAL_TOTAL + 1)) - printed)
    assert len(printed) + len(missing) == TRADITIONAL_TOTAL
    # 1179 is unprinted by BOTH lineages and is the single genuinely unattested value.
    assert missing == [1179, 1315]
    assert max(printed) == TRADITIONAL_TOTAL
    assert min(printed) == 1


def test_the_weld_detector_separates_svarita_from_a_leftover_marker() -> None:
    """Both directions, because it was wrong in each of them in turn.

    A whitespace-bounded rule missed every leftover marker adjacent to punctuation, which
    is the shape a marker actually takes -- a numeral next to a danda. Replacing it with a
    ``\\w`` rule then reported all 20 of the corpus's in-word numeric svarita as leftover
    markers, because a svarita digit is flanked by Devanagari combining marks and ``\\w``
    does not match those. The rule is now "neither neighbour is a letter OR a mark".
    """
    from scripts.build_samaveda_referent_audit import stray_numerals

    for svarita in ("गाथान्या३ं", "पाह्यू३त", "त्वा३स्य"):
        assert stray_numerals(svarita) == [], f"in-word svarita flagged: {svarita}"
    for leftover in (
        "चर्षणीनां ७१३ ॥",
        "चर्षणीनां ७१३॥",
        "चर्षणीनां ७१३।",
        "चर्षणीनां ॥७१३",
        "चर्षणीनां (७१३)",
    ):
        assert stray_numerals(leftover), f"leftover marker missed: {leftover}"


def test_no_released_verse_carries_surviving_markup(occurrences: list) -> None:
    """Table tags leaked into 20 released verses, and a pada label into 18 of them.

    ``clean_wikitext``'s tag list omitted ``table|tr|td``, and the row/cell splitters that
    do handle them are used only when reading the declared local index, never on the body
    path. The addresses were correct and corroborated throughout -- this was text
    contamination, not a weld -- but it would have pinned a contaminated comparison digest
    into the committed baseline, so that a later markup cleanup registered as 20 referent
    drifts needing 20 migration rows for what is purely a cleanup.
    """
    import re as _re

    tag = _re.compile(r"</?(?:tr|td|th|table|tbody|thead|p|span|poem)\b", _re.IGNORECASE)
    tagged = [item.source_locator for item in occurrences if tag.search(item.text)]
    assert tagged == [], f"surviving markup in verse text: {tagged[:8]}"
    # A pada label from the table dialect's second cell, e.g. "1c", leaking into the text.
    label = _re.compile(r"[०-९]\s*[अछए]्?\s*$")  # noqa: RUF001 - Devanagari digit range
    leaked = [item.source_locator for item in occurrences if label.search(item.text)]
    assert leaked == [], f"leaked pada labels in verse text: {leaked[:8]}"


def test_no_verse_carries_a_leftover_marker_numeral(occurrences: list) -> None:
    """A stray numeral in verse text means a boundary the lifter did not see.

    This is the check that would have caught running number 713 directly, without needing
    a second witness: its digits were sitting inside verse 714's stored text. The audit
    previously *asserted* one-marker-per-occurrence instead of measuring it.
    """
    from scripts.build_samaveda_referent_audit import stray_numerals

    offenders = {
        item.source_locator: stray_numerals(item.text)
        for item in occurrences
        if stray_numerals(item.text)
    }
    assert offenders == {}, f"leftover marker numerals in verse text: {offenders}"


def test_the_phantom_thirteenth_verse_is_now_unrepresentable(occurrences: list) -> None:
    """The superseded build minted a key for a verse that does not exist.

    Dasati (4,4,2,1) prints twelve verse numbers and thirteen addresses were minted,
    because two pada labels of one verse landed in different verse buckets. Under the
    repaired scheme the index is derived from the printed run, so an index above the
    printed count cannot be produced at all.
    """
    corresponding = [
        item
        for item in occurrences
        if item.collection is SamavedaCollection.UTTARA
        and item.prapathaka == 4
        and item.ardha == 2
        and item.dasati == 1
    ]
    if corresponding:
        indices = sorted(item.local_index for item in corresponding if item.local_index)
        assert indices == list(range(1, len(indices) + 1))
    migrations = _load_migrations()
    retired = {
        row.old_canonical_key
        for row in migrations
        if row.migration_class == MigrationClass.PASSAGE_REMOVED_AS_SPURIOUS.value
    }
    assert "VG:SV:KAU:A4:P04:R2:D01:V13" in retired


def _load_migrations() -> list[ReferentMigration]:
    if not MIGRATIONS.exists():
        return []
    return [
        ReferentMigration.model_validate_json(line)
        for line in MIGRATIONS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_the_count_ledger_still_checks_its_own_arithmetic() -> None:
    """The superseded ledger is retained as evidence, so its arithmetic must still hold.

    This harness is inherited from the suite this file replaced and is kept deliberately:
    the ledger's first draft summed to 6 instead of 7 because one of the nine surplus
    markers had been omitted, so a ledger that does not check its own totals is exactly
    the drift hazard it was written to stop. The ledger no longer describes the canonical
    corpus -- it describes the REJECTED witness -- but it is the evidence base for the six
    `REFERENT_CORRECTED` migrations, so it has to stay internally consistent.
    """
    ledger = yaml.safe_load(LEDGER.read_text(encoding="utf-8"))
    arithmetic = ledger["axis_arithmetic"]

    count_axis = ledger["count_axis_ledger"]
    positive = [row for row in count_axis if row["count_delta"] > 0]
    negative = [row for row in count_axis if row["count_delta"] < 0]
    assert len(positive) == arithmetic["count_axis_entries_with_positive_delta"]
    assert len(negative) == arithmetic["count_axis_entries_with_negative_delta"]
    assert sum(row["count_delta"] for row in count_axis) == arithmetic["count_axis_delta_sum"]
    assert arithmetic["count_axis_delta_sum"] == arithmetic["gap"]

    # The apparatus-read axis must stay at zero, or it double counts the count axis.
    assert (
        sum(row["count_delta"] for row in ledger["apparatus_read_ledger"])
        == arithmetic["apparatus_read_axis_delta_sum"]
        == 0
    )
    assert (
        sum(row["count_delta"] for row in ledger["canonical_key_defect_ledger"])
        == arithmetic["canonical_key_defect_axis_delta_sum"]
        == 0
    )

    collided = ledger["collided_addresses"]
    assert sum(row["surplus"] for row in collided) == arithmetic["collided_addresses_surplus_sum"]

    # The 7-vs-6 relationship, pinned so neither figure can be quoted alone: one collided
    # address never received a key (verse index 0 failed closed), so it has nothing to
    # migrate, and 7 - 1 = the 6 REFERENT_CORRECTED entries in the ledger.
    keyless = [row for row in collided if row["key"] is None]
    assert len(keyless) == 1
    corrected = [
        row
        for row in _load_migrations()
        if row.migration_class == MigrationClass.REFERENT_CORRECTED.value
    ]
    assert len(collided) - len(keyless) == len(corrected) == 6
    keyed = {row["key"] for row in collided if row["key"]}
    assert keyed == {row.old_canonical_key for row in corrected}


def test_every_retired_key_shape_has_a_recorded_migration() -> None:
    """Nothing here is called backwards compatible; the referent changed for six keys."""
    migrations = _load_migrations()
    assert migrations, "the migration ledger must be committed"
    assert all(row.work_id == "VG:WORK:SV:KAU" for row in migrations)
    assert all(not row.externally_frozen_before_change for row in migrations)
    classes = {row.migration_class for row in migrations}
    assert MigrationClass.KEY_REASSIGNED_BEFORE_FREEZE.value in classes
    assert MigrationClass.REFERENT_CORRECTED.value in classes
    assert MigrationClass.PASSAGE_REMOVED_AS_SPURIOUS.value in classes
    corrected = [
        row for row in migrations if row.migration_class == MigrationClass.REFERENT_CORRECTED.value
    ]
    # The six welded addresses the count ledger measured on the rejected witness.
    assert len(corrected) == 6
    for row in corrected:
        assert row.old_canonical_key and row.old_canonical_key.startswith("VG:SV:KAU:A")
        assert row.new_canonical_key and ":A4:" not in row.new_canonical_key
        assert row.evidence


# -------------------------------------------------------------------- the referent gate


def _fingerprint(
    key: str, text: str, locator: str, marker: int | None = None
) -> ReferentFingerprint:
    raw, folded = text_fingerprints(text)
    return ReferentFingerprint(
        canonical_key=key,
        source_locator=locator,
        text_sha256=raw,
        comparison_sha256=folded,
        source_verse_marker=marker,
    )


RUN = "SAMAVEDA_REFERENT_INTEGRITY_REPAIR"


def _migration(
    migration_class: str, old: str | None, new: str | None, run: str = RUN
) -> ReferentMigration:
    return ReferentMigration(
        migration_class=migration_class,
        old_canonical_key=old,
        new_canonical_key=new,
        work_id="VG:WORK:SV:KAU",
        reason="test",
        evidence="test",
        externally_frozen_before_change=False,
        downstream_impact="test",
        recorded_by_run=run,
    )


def test_an_unchanged_referent_is_reported_unchanged() -> None:
    before = [_fingerprint("VG:SV:KAU:ARANYA:D01:V01", "agna a yahi", "RN586")]
    deltas = compare_referents(before, list(before))
    assert [delta.verdict for delta in deltas] == [ReferentVerdict.UNCHANGED_REFERENT]
    assert_no_referent_drift(deltas)


def test_a_moved_referent_under_a_stable_key_fails_the_build() -> None:
    """The defect class that every existing gate reported as a success.

    Same key, same URN, same UUID, different verse. ``stable_uuid_deterministic`` cannot
    see this, because its only inputs are the URN it is comparing against and a
    compile-time namespace constant.
    """
    key = "VG:SV:KAU:UTTARA:P01:R01:D06:V03"
    before = [_fingerprint(key, "welded composite of three verses", "RN666+667+668")]
    after = [_fingerprint(key, "one verse only", "RN668")]
    deltas = compare_referents(before, after)
    assert [delta.verdict for delta in deltas] == [ReferentVerdict.REFERENT_DRIFT]
    with pytest.raises(ReferentDriftError, match="changed their textual referent"):
        assert_no_referent_drift(deltas)


def test_a_recorded_migration_licenses_a_referent_correction() -> None:
    key = "VG:SV:KAU:UTTARA:P01:R01:D06:V03"
    before = [_fingerprint(key, "welded composite", "RN666+667+668")]
    after = [_fingerprint(key, "one verse only", "RN668")]
    migration = ReferentMigration(
        migration_class=MigrationClass.REFERENT_CORRECTED.value,
        old_canonical_key=key,
        new_canonical_key=key,
        work_id="VG:WORK:SV:KAU",
        reason="the key held a concatenative weld of three printed verses",
        evidence="the selected witness prints 666/667/668 at three distinct addresses",
        externally_frozen_before_change=False,
        downstream_impact="referent narrowed",
        recorded_by_run="SAMAVEDA_REFERENT_INTEGRITY_REPAIR",
    )
    deltas = compare_referents(before, after, [migration])
    assert [delta.verdict for delta in deltas] == [ReferentVerdict.INTENTIONAL_REFERENT_CORRECTION]
    assert_no_referent_drift(deltas)


def test_a_re_encoding_that_preserves_the_occurrence_is_not_drift() -> None:
    """The fingerprint must distinguish "different bytes" from "different verse"."""
    key = "VG:SV:KAU:ARANYA:D01:V01"
    before = [_fingerprint(key, "indra jyeṣṭhaṃ na ā bhara", "RN586")]
    after = [_fingerprint(key, "indra   jyeṣṭhaṃ na ā bhara ", "RN586")]
    deltas = compare_referents(before, after)
    assert [delta.verdict for delta in deltas] == [ReferentVerdict.UNCHANGED_REFERENT]
    assert before[0].text_sha256 != after[0].text_sha256
    assert before[0].comparison_sha256 == after[0].comparison_sha256


def test_a_disappearing_key_needs_a_retirement_migration() -> None:
    key = "VG:SV:KAU:UTTARA:P04:R02:D01:V13"
    before = [_fingerprint(key, "a verse that does not exist", "RN1127")]
    drifted = compare_referents(before, [])
    assert [delta.verdict for delta in drifted] == [ReferentVerdict.REFERENT_DRIFT]
    with pytest.raises(ReferentDriftError):
        assert_no_referent_drift(drifted)

    retirement = ReferentMigration(
        migration_class=MigrationClass.PASSAGE_REMOVED_AS_SPURIOUS.value,
        old_canonical_key=key,
        work_id="VG:WORK:SV:KAU",
        reason="the key identified a verse that does not exist",
        evidence="the dasati prints twelve verse numbers and twelve verses",
        externally_frozen_before_change=False,
        downstream_impact="never materialized",
        recorded_by_run="SAMAVEDA_REFERENT_INTEGRITY_REPAIR",
    )
    licensed = compare_referents(before, [], [retirement])
    assert [delta.verdict for delta in licensed] == [ReferentVerdict.REMOVED_INVALID_PASSAGE]
    assert_no_referent_drift(licensed)


def test_a_newly_discovered_passage_is_additive_and_never_drift() -> None:
    """Filling a coverage gap must not be reported as a breaking change."""
    after = [_fingerprint("VG:SV:KAU:MAHANAMNYA:V01", "new verse", "RN641")]
    deltas = compare_referents([], after)
    assert [delta.verdict for delta in deltas] == [ReferentVerdict.NEWLY_DISCOVERED_PASSAGE]
    assert_no_referent_drift(deltas)


def test_a_changed_locator_is_drift_even_when_the_text_is_identical() -> None:
    """Text alone cannot identify an occurrence in THIS corpus, so it is not the test.

    The Uttararcika repeats Purvarcika verses verbatim in gana context, so of the released
    keys only 1,658 have a distinct comparison digest: 184 classes covering 369 keys share
    one, and 173 of those share a byte-identical raw digest too. A gate comparing text
    alone accepted a wholesale rewrite of every locator as "unchanged", and would accept
    two genuinely different occurrences swapping keys.
    """
    key = "VG:SV:KAU:ARANYA:D01:V01"
    text = "indra jyeṣṭhaṃ na ā bhara"
    before = [_fingerprint(key, text, "WS ARANYA.D1 RN586", 586)]
    after = [_fingerprint(key, text, "WS UTTARA.P1.R1.D1 RN9999", 9999)]
    assert before[0].comparison_sha256 == after[0].comparison_sha256
    deltas = compare_referents(before, after)
    assert [delta.verdict for delta in deltas] == [ReferentVerdict.REFERENT_DRIFT]
    with pytest.raises(ReferentDriftError):
        assert_no_referent_drift(deltas)


def test_two_keys_sharing_a_text_digest_cannot_swap_undetected() -> None:
    """The real collision surface: genuine verse repetition across collections."""
    shared = "agna ā yāhi vītaye"
    aranya = "VG:SV:KAU:ARANYA:D01:V08"
    uttara = "VG:SV:KAU:UTTARA:P01:R01:D08:V03"
    before = [
        _fingerprint(aranya, shared, "WS ARANYA.D1 RN593", 593),
        _fingerprint(uttara, shared, "WS UTTARA.P1.R1.D8 RN674", 674),
    ]
    swapped = [
        _fingerprint(aranya, shared, "WS UTTARA.P1.R1.D8 RN674", 674),
        _fingerprint(uttara, shared, "WS ARANYA.D1 RN593", 593),
    ]
    deltas = compare_referents(before, swapped)
    assert {delta.verdict for delta in deltas} == {ReferentVerdict.REFERENT_DRIFT}
    with pytest.raises(ReferentDriftError):
        assert_no_referent_drift(deltas)


def test_a_key_shape_reassignment_does_not_license_future_drift() -> None:
    """An append-only ledger must not become a standing licence to drift.

    The committed ledger holds 137 ``KEY_REASSIGNED_BEFORE_FREEZE`` rows, each naming an
    old and a new key. When that class counted as a *correction* and both names were
    registered, those rows pre-licensed referent change on 105 already-released keys and
    removal on 99 of them -- permanently, from a tracked file.
    """
    key = "VG:SV:KAU:UTTARA:P01:R01:D01:V01"
    before = [_fingerprint(key, "the original verse", "RN651", 651)]
    after = [_fingerprint(key, "a completely different verse", "RN999", 999)]
    reassignment = _migration(
        MigrationClass.KEY_REASSIGNED_BEFORE_FREEZE.value,
        "VG:SV:KAU:A4:P01:R1:D01:V01",
        key,
    )
    deltas = compare_referents(before, after, [reassignment])
    assert [delta.verdict for delta in deltas] == [ReferentVerdict.REFERENT_DRIFT]
    with pytest.raises(ReferentDriftError):
        assert_no_referent_drift(deltas)


def test_a_migration_from_another_run_licenses_nothing() -> None:
    """Licences are scoped to the run being validated, not to the whole ledger."""
    key = "VG:SV:KAU:UTTARA:P01:R01:D01:V01"
    before = [_fingerprint(key, "the original verse", "RN651", 651)]
    after = [_fingerprint(key, "a different verse", "RN652", 652)]
    stale = _migration(MigrationClass.REFERENT_CORRECTED.value, key, key, run="SOME_PAST_RUN")

    licensed = compare_referents(before, after, [stale])
    assert [d.verdict for d in licensed] == [ReferentVerdict.INTENTIONAL_REFERENT_CORRECTION]

    scoped = compare_referents(before, after, [stale], licensing_run="THE_RUN_BEING_BUILT")
    assert [d.verdict for d in scoped] == [ReferentVerdict.REFERENT_DRIFT]
    with pytest.raises(ReferentDriftError):
        assert_no_referent_drift(scoped)


def test_the_committed_ledger_licenses_no_released_key_to_drift() -> None:
    """Over the real committed files, and it INJECTS drift rather than comparing no-change.

    The first version of this test compared the baseline against itself and asserted that
    no delta carried a covering migration. That was vacuous: ``covering_migration`` is only
    populated on a delta that actually changed, so the assertion held by construction and
    would have passed if every key were licensed. It was: measured against an injected
    drift, the six shape-changing ``REFERENT_CORRECTED`` rows licensed six RELEASED keys,
    because both the old and the new key name were being registered as licensed.
    """
    baseline = read_baseline(BASELINE)
    migrations = _load_migrations()
    assert migrations

    # Move every released key's referent, then assert the ledger licenses none of it.
    drifted = [
        ReferentFingerprint(
            canonical_key=row.canonical_key,
            source_locator=f"{row.source_locator} MOVED",
            text_sha256="f" * 64,
            comparison_sha256="e" * 64,
            source_verse_marker=None,
        )
        for row in baseline
    ]
    deltas = compare_referents(baseline, drifted, migrations, licensing_run=RUN)
    licensed = [
        delta.canonical_key
        for delta in deltas
        if delta.verdict is not ReferentVerdict.REFERENT_DRIFT
    ]
    assert licensed == [], (
        f"{len(licensed)} released key(s) are licensed to drift by the committed ledger: "
        f"{licensed[:8]}"
    )
    with pytest.raises(ReferentDriftError):
        assert_no_referent_drift(deltas)

    # And a no-change comparison is still clean.
    unchanged = compare_referents(baseline, baseline, migrations, licensing_run=RUN)
    assert {delta.verdict for delta in unchanged} == {ReferentVerdict.UNCHANGED_REFERENT}


def test_the_committed_ledger_licenses_no_released_key_to_disappear() -> None:
    """The removal half of the same question, also by injection."""
    baseline = read_baseline(BASELINE)
    deltas = compare_referents(baseline, [], _load_migrations(), licensing_run=RUN)
    survived = [
        delta.canonical_key
        for delta in deltas
        if delta.verdict is not ReferentVerdict.REFERENT_DRIFT
    ]
    assert survived == [], (
        f"{len(survived)} released key(s) may be removed without a fresh migration: {survived[:8]}"
    )


# ------------------------------------------------------------------ the committed baseline


def test_the_committed_baseline_exists_and_is_the_gate_reference() -> None:
    """It must be git-tracked. ``data/derived/**`` is gitignored, so a baseline there
    would silently be no baseline at all."""
    assert BASELINE.exists(), "the referent baseline must be committed"
    baseline = read_baseline(BASELINE)
    assert len(baseline) == MINTED_KEYS
    assert len({row.canonical_key for row in baseline}) == MINTED_KEYS
    assert all(row.canonical_key.startswith("VG:SV:KAU:") for row in baseline)
    assert all(len(row.text_sha256) == 64 for row in baseline)
    assert all(len(row.comparison_sha256) == 64 for row in baseline)


def test_no_source_occurrence_is_claimed_by_two_keys() -> None:
    """Zero one-referent/two-key accidental splits."""
    baseline = read_baseline(BASELINE)
    assert duplicate_referents(baseline) == {}


def test_the_baseline_only_contains_collection_named_keys() -> None:
    baseline = read_baseline(BASELINE)
    prefixes = {row.canonical_key.split(":")[3] for row in baseline}
    assert prefixes == {collection.value for collection in SamavedaCollection}


def test_a_rebuild_reproduces_the_baseline_exactly(occurrences: list) -> None:
    """Deterministic rebuild: the committed baseline must equal a fresh build."""
    rebuilt: dict[str, tuple[str, str]] = {}
    for item in occurrences:
        if item.local_index is None or not item.text:
            continue
        key = sv_mantra_identity(
            item.collection,
            verse=item.local_index,
            prapathaka=item.prapathaka,
            ardha=item.ardha,
            dasati=item.dasati,
        )[0]
        rebuilt[key] = text_fingerprints(item.text)

    baseline = {row.canonical_key: row for row in read_baseline(BASELINE)}
    # The baseline is the corroborated subset; every baseline key must be reproduced with
    # an identical fingerprint.
    missing = sorted(set(baseline) - set(rebuilt))
    assert missing == [], f"baseline keys absent from a rebuild: {missing[:10]}"
    # The keys a rebuild mints but the baseline does not carry must be EXACTLY the
    # uncorroborated groups, nothing else. Asserting only baseline-subset-of-rebuild would
    # let a build invent keys the gate never sees, because compare_referents reports an
    # unknown key as NEWLY_DISCOVERED_PASSAGE and never as drift. ``rebuilt`` here is the
    # pre-corroboration set: the adapter addresses every resolvable occurrence, and the
    # withholding is applied by the audit builder.
    extra = sorted(set(rebuilt) - set(baseline))
    unexpected = [
        key
        for key in extra
        if not any(key.startswith(f"{group}:") for group in UNCORROBORATED_GROUPS)
    ]
    assert unexpected == [], (
        f"rebuild minted {len(unexpected)} key(s) that are neither released nor in a "
        f"known uncorroborated group: {unexpected[:10]}"
    )
    changed = [key for key, row in baseline.items() if rebuilt[key][1] != row.comparison_sha256]
    assert changed == [], f"referent changed for {len(changed)} keys: {changed[:10]}"


def test_a_binding_records_everything_needed_to_re_verify_it() -> None:
    raw, folded = text_fingerprints("agna a yahi vitaye")
    binding = PassageReferentBinding(
        canonical_key="VG:SV:KAU:ARANYA:D01:V01",
        canonical_urn="urn:vedagraph:mantra:samaveda:kauthuma:aranya:dasati:1:verse:1",
        entity_id=sv_mantra_identity(SamavedaCollection.ARANYA, dasati=1, verse=1)[2],
        work_id="VG:WORK:SV:KAU",
        structural_coordinates={"collection": "ARANYA", "dasati": 1, "verse": 1},
        source_id="WIKISOURCE_SA",
        source_artifact_id="WIKISOURCE_SA.SV.KAU.SAMHITA.DEVANAGARI",
        source_locator="WS ARANYA.D1 RN586",
        source_revision_id=323308,
        source_snapshot_sha256="e" * 64,
        text_sha256=raw,
        comparison_sha256=folded,
        source_verse_marker=586,
        segmentation_policy_version="sv-referent-segmentation-v1",
        parser_version="wikisource-sa-samaveda-arcika-v2",
    )
    # The fingerprint is a guard, never an identity input: the UUID is the hash of the URN
    # alone, so it is unchanged by any text.
    from vedagraph.identity import uuid_for_urn

    assert binding.entity_id == uuid_for_urn(binding.canonical_urn)
    assert binding.source_verse_marker == 586
