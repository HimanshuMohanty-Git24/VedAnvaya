"""Executable pins for the first production canonical Samaveda ARCIKA release.

What these tests are guarding against, stated as failures rather than features:

* **A corpus built from an artifact that forbids the build.** Until 2026-09-07 the only
  registered Samaveda text version was ``GRETIL.SV.KAUTHUMA``, whose embedded Pandey 1998
  licence forbids modification outright -- and parsing, NFC normalization, structural
  re-keying and JSONL republication are all modification. A selection routine that fell
  back would have produced a corpus that looks complete and cites provenance it may not
  use. :func:`test_the_build_refuses_to_fall_back_to_gretil...` is the proof, and it
  injects a registry rather than editing ``data/registry/text_versions.yaml``.

* **A count made to balance.** The traditional Kauthuma total is 1,875 and this release
  carries 1,844 keys. Every coverage number here is recomputed from the audit rows of the
  run under test, and :func:`test_a_broken_equation_refuses_the_release` doctors the rows
  to prove the arithmetic gate fires instead of merely existing.

* **A key that quietly starts denoting a different verse.** ``uuid5(namespace, urn)``
  returns the identical value before and after a referent swap, so UUID determinism is
  not evidence of anything. The adversarial cases below swap referents *between keys that
  share a byte-identical text*, which is the one shape a text-only comparison cannot see
  -- and which this corpus really has, in 192 equivalence classes covering 385 keys.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.build_samaveda_canonical import (  # noqa: E402
    ARTIFACT_ID,
    COLLECTION_ORDER,
    FORBIDDEN_TEXT_VERSION_IDS,
    LICENSING_RUN,
    TEXT_VERSION_ID,
    WORK_ID,
    BuildOutcome,
    CoverageError,
    build,
    compute_coverage,
    load_migrations,
    registry_text_versions,
    select_samaveda_primary,
    verify_determinism,
    withheld_reason,
)
from scripts.build_samaveda_referent_audit import GRETIL_SNAPSHOT  # noqa: E402
from vedagraph.identity import SV_COLLECTION_LEVELS, SamavedaCollection  # noqa: E402
from vedagraph.models.enums import EntityType, PassageStatus, RightsStatus, TextRole  # noqa: E402
from vedagraph.referent import ReferentVerdict, duplicate_referents, fingerprint_of  # noqa: E402
from vedagraph.release import (  # noqa: E402
    ReleaseIntegrityError,
    TextVersionSelectionError,
    gate_referents,
)

WIKISOURCE_DIR = REPO / "data" / "raw" / "wikisource_sa"
BASELINE = REPO / "tests" / "fixtures" / "identity" / "sv_referent_baseline.jsonl"

# The traditional Kauthuma total. Not the released count, and deliberately never used as
# a target: see the coverage tests.
TRADITIONAL_TOTAL = 1875
RELEASED_KEYS = 1844
CANDIDATE_OCCURRENCES = 1874
WITHHELD_OCCURRENCES = 30
# 1181 is printed twice, so 30 withheld occurrences cover only 29 distinct printed verses.
WITHHELD_PRINTED_VERSES = 29
UNPRINTED_RUNNING_NUMBERS = [1179, 1315]

# The closed vocabulary a withheld verse may state. A withhold outside it is a silent gap.
WITHHELD_REASONS = {
    "REFERENT_UNRESOLVED",
    "SOURCE_MARKER_ANOMALY",
    "STRUCTURAL_AMBIGUITY",
    "SOURCE_NOT_PRINTED",
    "REVIEW_REQUIRED",
}

# MEASURED over the committed baseline, not quoted. The Uttararcika repeats Purvarcika
# verses verbatim, so text equality is emphatically not referent equality here.
# NOTE: src/vedagraph/referent.py's docstring states 184 classes / 369 keys / 1658
# distinct digests for the same property. The current released set measures 192 / 385 /
# 1651, and the baseline file measures the same, so that docstring is stale by a small
# margin. Recorded here rather than silently reconciled.
SHARED_DIGEST_CLASSES = 192
KEYS_SHARING_A_DIGEST = 385
DISTINCT_COMPARISON_DIGESTS = 1651


# --------------------------------------------------------------------------- fixtures


@pytest.fixture(scope="module")
def outcome(tmp_path_factory: pytest.TempPathFactory) -> BuildOutcome:
    """One full release built into a throwaway root, shared by the whole module.

    A throwaway root rather than the configured one: a test run must not be able to
    publish, and must not overwrite the tracked coverage report.
    """
    if not WIKISOURCE_DIR.exists():
        pytest.skip("Sanskrit Wikisource Samaveda snapshots are not pinned locally")
    if not GRETIL_SNAPSHOT.exists():
        pytest.skip("the structural corroboration witness is not pinned locally")
    root = tmp_path_factory.mktemp("samaveda-arcika-v1")
    return build(root / "release")


@pytest.fixture(scope="module")
def coverage_report(outcome: BuildOutcome) -> dict[str, Any]:
    payload: dict[str, Any] = json.loads(outcome.coverage_report_path.read_text(encoding="utf-8"))
    return payload


# ------------------------------------------------------- fail-closed text selection


def test_the_selected_primary_is_the_registered_wikisource_arcika_layer() -> None:
    descriptor = select_samaveda_primary(registry_text_versions())
    assert descriptor.text_version_id == TEXT_VERSION_ID
    assert descriptor.artifact_id == ARTIFACT_ID
    assert descriptor.text_role is TextRole.PRIMARY_TEXT
    assert descriptor.normalized_rights is RightsStatus.CC_BY_SA


def test_the_build_refuses_to_fall_back_to_gretil_when_the_wikisource_layer_is_absent() -> None:
    """THE no-fallback proof, and the reason this whole module exists.

    The injected registry has the Samaveda Wikisource entry REMOVED and
    ``GRETIL.SV.KAUTHUMA`` still PRESENT, so a fallback is genuinely available: a routine
    that resolved "some registered version of this work" would find one and succeed. The
    assertion is that the build path raises instead, and never returns GRETIL.

    The real ``data/registry/text_versions.yaml`` is not touched. Mutating it to test a
    refusal would leave the repository one failed assertion away from an unregistered
    primary layer.
    """
    registry = registry_text_versions()
    without_wikisource = [
        descriptor for descriptor in registry if descriptor.text_version_id != TEXT_VERSION_ID
    ]
    assert len(without_wikisource) == len(registry) - 1, "the entry under test was not removed"
    fallbacks = {
        descriptor.text_version_id
        for descriptor in without_wikisource
        if descriptor.text_version_id.endswith(".SV.KAUTHUMA")
    }
    assert "GRETIL.SV.KAUTHUMA" in fallbacks, (
        "this test is worthless unless a fallback is actually available to be taken"
    )

    with pytest.raises(TextVersionSelectionError) as raised:
        select_samaveda_primary(without_wikisource)

    message = str(raised.value)
    assert TEXT_VERSION_ID in message
    assert "STOPS" in message
    # The refusal must not have quietly resolved anything.
    assert not hasattr(raised.value, "descriptor")
    # And the real registry still resolves, so the refusal came from the injection.
    assert select_samaveda_primary(registry).text_version_id == TEXT_VERSION_ID


@pytest.mark.parametrize("forbidden", sorted(FORBIDDEN_TEXT_VERSION_IDS))
def test_every_pandey_lineage_id_is_refused_by_name(forbidden: str) -> None:
    """Naming them is what makes the refusal assertable rather than incidental.

    GRETIL, TITUS and The Sanskrit Library are three re-publications of one Anshuman
    Pandey 1998/99 e-text. Their agreement is the same defect three times, not
    corroboration, and the prohibition on modification disqualifies all three at once.
    """
    from vedagraph.release import select_primary_text_version

    with pytest.raises(TextVersionSelectionError, match="forbidden"):
        select_primary_text_version(
            forbidden,
            work_id=WORK_ID,
            forbidden_text_version_ids=FORBIDDEN_TEXT_VERSION_IDS,
            descriptors=registry_text_versions(),
        )


def test_selection_refuses_an_artifact_that_is_not_the_pinned_one() -> None:
    from vedagraph.release import select_primary_text_version

    with pytest.raises(TextVersionSelectionError, match="unpinned artifact"):
        select_primary_text_version(
            TEXT_VERSION_ID,
            work_id=WORK_ID,
            expected_artifact_id="GRETIL.SV.KAUTHUMA.TEI.2020",
            descriptors=registry_text_versions(),
        )


# ------------------------------------------------------------------------- coverage


def test_the_coverage_equations_close(outcome: BuildOutcome) -> None:
    equations = outcome.coverage["equations"]
    assert all(item["balances"] for item in equations.values()), equations
    assert equations["printed_vs_traditional"]["statement"] == (
        "1875 = 1873 distinct printed markers + 2 the selected witness does not print"
    )
    assert equations["released_vs_traditional"]["statement"] == (
        "1875 = 1844 minted keys + 29 withheld printed verses + 2 unprinted"
    )


def test_coverage_is_not_forced_to_the_traditional_total(outcome: BuildOutcome) -> None:
    coverage = outcome.coverage
    assert coverage["traditional_total"] == TRADITIONAL_TOTAL
    assert coverage["minted_keys"] == RELEASED_KEYS
    assert coverage["minted_keys"] < TRADITIONAL_TOTAL
    assert coverage["candidate_occurrences"] == CANDIDATE_OCCURRENCES
    assert coverage["withheld_occurrences"] == WITHHELD_OCCURRENCES
    assert coverage["withheld_printed_verses"] == WITHHELD_PRINTED_VERSES
    assert coverage["unprinted_running_numbers"] == UNPRINTED_RUNNING_NUMBERS
    assert coverage["duplicated_printed_markers"] == [1181]
    # The Purvarcika group reaches its traditional 650 from the selected witness alone;
    # the whole shortfall is in the Uttararcika, which is where the disputed dasati
    # partitions are.
    assert coverage["purvarcika_group_minted"] == 650
    assert coverage["minted_by_collection"] == {
        "CHANDA": 585,
        "ARANYA": 55,
        "MAHANAMNYA": 10,
        "UTTARA": 1194,
    }


def test_a_broken_equation_refuses_the_release(outcome: BuildOutcome) -> None:
    """The gate fires, rather than merely being present.

    The doctoring is chosen to survive the two headline equations, because those balance
    automatically whenever released and withheld markers partition the printed set:
    simply DELETING a row moves its marker from "printed" to "unprinted" and everything
    still adds up. What must not survive is a released key that has lost the printed
    verse it denotes -- one half of a weld -- and that is what is injected here.
    """
    rows = list(outcome.audit_rows)
    first_released = next(index for index, row in enumerate(rows) if row.canonical_key)
    doctored = list(rows)
    doctored[first_released] = replace(rows[first_released], source_verse_marker=None)
    with pytest.raises(CoverageError, match="do not close"):
        compute_coverage(doctored)

    # And a second key stealing an already-released marker, which is the other half.
    stolen = list(rows)
    second = next(
        index for index, row in enumerate(rows) if row.canonical_key and index != first_released
    )
    stolen[second] = replace(
        rows[second], source_verse_marker=rows[first_released].source_verse_marker
    )
    with pytest.raises(CoverageError, match="do not close"):
        compute_coverage(stolen)


def test_every_withheld_occurrence_carries_a_reason(outcome: BuildOutcome) -> None:
    withheld = [row for row in outcome.audit_rows if not row.canonical_key]
    assert len(withheld) == WITHHELD_OCCURRENCES
    reasons = Counter(withheld_reason(row) for row in withheld)
    assert set(reasons) <= WITHHELD_REASONS
    assert reasons == {"REFERENT_UNRESOLVED": 9, "STRUCTURAL_AMBIGUITY": 21}

    issues = outcome.release.qa_issues
    assert {issue.check_id for issue in issues} <= WITHHELD_REASONS
    located = {issue.entity_id for issue in issues}
    for row in withheld:
        assert row.source_locator in located, f"{row.source_locator} is withheld in silence"
    # One row per unprinted running number, so the two verses no witness prints are named
    # rather than absorbed into a headline shortfall.
    unprinted = [issue for issue in issues if issue.check_id == "SOURCE_NOT_PRINTED"]
    assert sorted(issue.entity_id or "" for issue in unprinted) == ["RN1179", "RN1315"]


def test_the_resolution_attempt_reports_evidence_and_mints_nothing(
    outcome: BuildOutcome,
) -> None:
    """A resolution pass that could change coverage would be a second segmentation path."""
    findings = outcome.withheld_findings
    assert len(findings) == 5
    assert sum(int(finding["withheld_occurrences"]) for finding in findings) == (
        WITHHELD_OCCURRENCES
    )
    assert all(finding["resolved"] is False for finding in findings)
    assert all(finding["verdict"] != "NOT_ATTEMPTED" for finding in findings)
    assert {str(finding["container_key"]) for finding in findings} == {
        "VG:SV:KAU:UTTARA:P04:R01:D22",
        "VG:SV:KAU:UTTARA:P04:R02:D14",
        "VG:SV:KAU:UTTARA:P05:R01:D02",
        "VG:SV:KAU:UTTARA:P05:R01:D17",
        "VG:SV:KAU:UTTARA:P05:R02:D05",
    }
    # No withheld container is released as a Passage either: withholding a verse while
    # publishing the dasati that holds it would assert a container with no contents.
    released_keys = {passage.canonical_key for passage in outcome.release.passages}
    for finding in findings:
        assert str(finding["container_key"]) not in released_keys


def test_the_coverage_report_states_the_gana_boundary(coverage_report: dict[str, Any]) -> None:
    assert coverage_report["gana_corpus_included"] is False
    scope = coverage_report["scope"]
    assert "SAMAVEDA_GANA_CORPUS IS NOT IMPLIED" in scope
    assert "complete" in scope.lower()
    for value in coverage_report.values():
        if isinstance(value, str) and value is not scope:
            assert "complete Samaveda" not in value


# -------------------------------------------------------------------- referent gate


def test_the_release_reproduces_the_committed_baseline_exactly(outcome: BuildOutcome) -> None:
    assert outcome.verdicts == {
        ReferentVerdict.UNCHANGED_REFERENT.value: RELEASED_KEYS,
        ReferentVerdict.INTENTIONAL_REFERENT_CORRECTION.value: 0,
        ReferentVerdict.REFERENT_DRIFT.value: 0,
        ReferentVerdict.REMOVED_INVALID_PASSAGE.value: 0,
        ReferentVerdict.NEWLY_DISCOVERED_PASSAGE.value: 0,
    }


def test_the_committed_migrations_license_nothing_in_this_run() -> None:
    """Run scoping, and why zero licensed changes is the CORRECT result.

    A migration ledger is append-only and permanent. Without ``licensing_run`` scoping,
    the 144 rows recorded for SAMAVEDA_REFERENT_INTEGRITY_REPAIR would stand as a
    standing licence for the same keys to drift in every release afterwards.
    """
    migrations = load_migrations()
    assert len(migrations) == 144
    assert {migration.recorded_by_run for migration in migrations} == {
        "SAMAVEDA_REFERENT_INTEGRITY_REPAIR"
    }
    assert LICENSING_RUN not in {migration.recorded_by_run for migration in migrations}


def test_no_two_released_keys_claim_one_source_occurrence(outcome: BuildOutcome) -> None:
    fingerprints = [fingerprint_of(binding) for binding in outcome.release.referent_bindings]
    assert duplicate_referents(fingerprints) == {}


def test_a_welded_verse_is_refused_by_the_gate(outcome: BuildOutcome) -> None:
    """One occurrence claimed by two keys. Drift comparison alone cannot see this.

    A split produces two keys that are each individually unchanged against the baseline,
    so every per-key verdict reports success while one printed verse is addressed twice.
    """
    bindings = list(outcome.release.referent_bindings)
    victim, thief = bindings[0], bindings[1]
    welded = [*bindings, thief.model_copy(update={"source_locator": victim.source_locator})]
    with pytest.raises(ReleaseIntegrityError, match="claimed by more than one canonical key"):
        gate_referents(welded, baseline_path=BASELINE, licensing_run=LICENSING_RUN)


def test_text_equality_is_not_referent_equality(outcome: BuildOutcome) -> None:
    """The Uttararcika repeats Purvarcika verses verbatim, so this corpus really has it."""
    bindings = outcome.release.referent_bindings
    by_digest = Counter(binding.comparison_sha256 for binding in bindings)
    shared = [digest for digest, count in by_digest.items() if count > 1]
    assert len(by_digest) == DISTINCT_COMPARISON_DIGESTS
    assert len(shared) == SHARED_DIGEST_CLASSES
    assert sum(by_digest[digest] for digest in shared) == KEYS_SHARING_A_DIGEST
    # Every member of an equivalence class denotes a DIFFERENT occurrence, which is the
    # whole point: a comparison that stopped at the digest would call them the same verse.
    for digest in shared:
        members = [binding for binding in bindings if binding.comparison_sha256 == digest]
        assert len({member.source_locator for member in members}) == len(members)


def test_a_referent_swap_between_two_identical_texts_is_drift(outcome: BuildOutcome) -> None:
    """The adversarial case a text-only comparison is blind to.

    Two keys whose text is byte-identical exchange the occurrences they denote. Their
    digests are unchanged, so a digest-only gate sees two unchanged referents; the
    locator and the printed verse marker are what expose it.
    """
    bindings = list(outcome.release.referent_bindings)
    by_digest: dict[str, list[int]] = defaultdict(list)
    for index, binding in enumerate(bindings):
        by_digest[binding.comparison_sha256].append(index)
    pair = next(indexes for indexes in by_digest.values() if len(indexes) >= 2)
    left, right = bindings[pair[0]], bindings[pair[1]]
    assert left.comparison_sha256 == right.comparison_sha256

    swapped = list(bindings)
    swapped[pair[0]] = left.model_copy(
        update={
            "source_locator": right.source_locator,
            "source_verse_marker": right.source_verse_marker,
        }
    )
    swapped[pair[1]] = right.model_copy(
        update={
            "source_locator": left.source_locator,
            "source_verse_marker": left.source_verse_marker,
        }
    )
    with pytest.raises(Exception) as raised:
        gate_referents(swapped, baseline_path=BASELINE, licensing_run=LICENSING_RUN)
    assert "referent" in str(raised.value).lower()


def test_no_phantom_verse_can_sit_inside_a_dasati(outcome: BuildOutcome) -> None:
    """The V13 defect: a thirteenth verse in a dasati that holds twelve.

    The invariant that makes it unrepresentable is that a container's verse indices are
    exactly ``1..n``. A phantom index is then either a duplicate or a hole, and both fail
    the spine check -- rather than being a plausible-looking extra key.
    """
    by_parent: dict[str | None, list[int]] = defaultdict(list)
    for passage in outcome.release.passages:
        if passage.entity_type is EntityType.MANTRA:
            by_parent[passage.parent_key].append(passage.sequence_in_parent)
    assert by_parent
    for parent, sequences in by_parent.items():
        assert sorted(sequences) == list(range(1, len(sequences) + 1)), parent

    keys = {passage.canonical_key for passage in outcome.release.passages}
    baseline_keys = {
        json.loads(line)["canonical_key"]
        for line in BASELINE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    verse_keys = {
        passage.canonical_key
        for passage in outcome.release.passages
        if passage.entity_type is EntityType.MANTRA
    }
    assert verse_keys == baseline_keys
    assert "VG:SV:KAU:UTTARA:P01:R02:D01:V13" not in keys


# ------------------------------------------------------------------ structural spine


def test_every_parent_key_resolves_and_siblings_are_numbered_1_to_n(
    outcome: BuildOutcome,
) -> None:
    passages = outcome.release.passages
    keys = {passage.canonical_key for passage in passages}
    assert len(keys) == len(passages)
    children: dict[str | None, list[int]] = defaultdict(list)
    for passage in passages:
        if passage.parent_key is not None:
            assert passage.parent_key in keys, passage.canonical_key
            assert passage.canonical_key.startswith(passage.parent_key + ":")
        children[passage.parent_key].append(passage.sequence_in_parent)
    for parent, sequences in children.items():
        assert sorted(sequences) == list(range(1, len(sequences) + 1)), parent
    # The four collection containers are the only roots, and they carry the source's own
    # block order. That order is sibling ORDERING, never identity: the key names the
    # collection precisely because the top-level ARITY is disputed.
    roots = sorted(
        (passage.sequence_in_parent, passage.canonical_key)
        for passage in passages
        if passage.parent_key is None
    )
    assert [key for _, key in roots] == [
        f"VG:SV:KAU:{collection.value}" for collection in COLLECTION_ORDER
    ]


def test_containers_and_verses_use_the_right_entity_types(outcome: BuildOutcome) -> None:
    kinds = Counter(passage.entity_type for passage in outcome.release.passages)
    assert kinds == {EntityType.MANTRA: RELEASED_KEYS, EntityType.STRUCTURAL_CONTAINER: 498}
    assert all(passage.status is PassageStatus.CANONICAL for passage in outcome.release.passages)


def test_native_labels_name_exactly_the_levels_each_collection_declares(
    outcome: BuildOutcome,
) -> None:
    """Depth is not uniform, and a level a collection lacks is OMITTED, never zero-filled."""
    expected = {
        SamavedaCollection.CHANDA: ["Collection", "Prapathaka", "Dasati", "Verse"],
        SamavedaCollection.ARANYA: ["Collection", "Dasati", "Verse"],
        SamavedaCollection.MAHANAMNYA: ["Collection", "Verse"],
        SamavedaCollection.UTTARA: ["Collection", "Prapathaka", "Ardha", "Dasati", "Verse"],
    }
    for passage in outcome.release.passages:
        collection = SamavedaCollection(passage.structural_path[0])
        assert len(passage.structural_path) == len(passage.native_labels)
        assert {label.lower() for label in passage.native_labels} == {
            key.lower() for key in passage.hierarchy
        }
        declared = ["collection", *SV_COLLECTION_LEVELS[collection]]
        lowered = [label.lower() for label in passage.native_labels]
        if passage.entity_type is EntityType.MANTRA:
            assert passage.native_labels == expected[collection]
            assert lowered == [*declared, "verse"]
            # A level the collection does not declare is absent from the address, never
            # written as a literal 0. Zero-filling was the superseded scheme's way of
            # recording a level the rejected edition invented.
            assert "0" not in passage.structural_path
            assert f"VG:SV:KAU:{collection.value}:" in passage.canonical_key + ":"
        else:
            assert passage.native_labels == expected[collection][: len(passage.native_labels)]
            # A container is a strict prefix of the collection's declared level list.
            assert lowered == declared[: len(lowered)]


def test_no_two_released_verses_share_a_collection_coordinate(outcome: BuildOutcome) -> None:
    coordinates = Counter(
        (
            binding.structural_coordinates.get("collection"),
            binding.structural_coordinates.get("prapathaka"),
            binding.structural_coordinates.get("ardha"),
            binding.structural_coordinates.get("dasati"),
            binding.structural_coordinates.get("verse"),
        )
        for binding in outcome.release.referent_bindings
    )
    assert [item for item, count in coordinates.items() if count > 1] == []


def test_a_bare_ordinal_top_slot_would_be_a_referent_collision(outcome: BuildOutcome) -> None:
    """Why the key names the collection instead of numbering it.

    Two attested readings of the top level exist. The Pandey e-text lineage presents four
    flat arcikas; Sanskrit Wikisource, Griffith, Wikipedia, the Vedic Heritage Portal,
    Vedapeetha and B. R. Sharma present two, with Chanda / Aranya / Mahanamnya inside the
    Purvarcika. Under an ordinal top slot the value 2 therefore addresses the Aranya
    collection in one reading and the Uttararcika in the other -- two disjoint, non-empty
    verse populations. Naming the block records what every witness agrees on and leaves
    the bracketing to the container spine, where changing it renumbers nothing.
    """
    pandey_ordinal = {
        SamavedaCollection.CHANDA: 1,
        SamavedaCollection.ARANYA: 2,
        SamavedaCollection.MAHANAMNYA: 3,
        SamavedaCollection.UTTARA: 4,
    }
    two_arcika_ordinal = {
        SamavedaCollection.CHANDA: 1,
        SamavedaCollection.ARANYA: 1,
        SamavedaCollection.MAHANAMNYA: 1,
        SamavedaCollection.UTTARA: 2,
    }
    verses = [
        passage for passage in outcome.release.passages if passage.entity_type is EntityType.MANTRA
    ]
    under_pandey = {
        passage.canonical_key
        for passage in verses
        if pandey_ordinal[SamavedaCollection(passage.structural_path[0])] == 2
    }
    under_two = {
        passage.canonical_key
        for passage in verses
        if two_arcika_ordinal[SamavedaCollection(passage.structural_path[0])] == 2
    }
    assert len(under_pandey) == 55
    assert len(under_two) == 1194
    assert under_pandey.isdisjoint(under_two)
    # The released keys carry no ordinal top slot at all, so the collision is not merely
    # avoided by convention -- it is unrepresentable.
    assert all(
        passage.canonical_key.split(":")[3] in {c.value for c in SamavedaCollection}
        for passage in verses
    )


# ---------------------------------------------------------------------- record families


def test_the_running_number_is_a_non_canonical_citation_and_never_a_key(
    outcome: BuildOutcome,
) -> None:
    canonical = [item for item in outcome.release.citations if item.is_canonical]
    running = [item for item in outcome.release.citations if not item.is_canonical]
    assert len(canonical) == RELEASED_KEYS
    assert len(running) == RELEASED_KEYS
    assert {item.system for item in running} == {"WIKISOURCE_SA_RUNNING_SAMHITA_NUMBER"}
    assert {item.system for item in canonical} == {"VG_SV_KAUTHUMA_COLLECTION_COORDINATE"}
    markers = {
        binding.canonical_key: binding.source_verse_marker
        for binding in outcome.release.referent_bindings
    }
    assert sorted(value for value in markers.values() if value is not None) != []
    for passage in outcome.release.passages:
        if passage.entity_type is not EntityType.MANTRA:
            continue
        marker = markers[passage.canonical_key]
        # The running number reaches 1875 while every verse slot is a dasati-local index
        # of at most two digits, so a key would be a different shape entirely if the
        # running number had leaked into it.
        assert f"V{marker:02d}" not in passage.canonical_key or marker == (
            passage.sequence_in_parent
        )


def test_every_released_verse_is_unaccented_and_that_is_measured(
    outcome: BuildOutcome,
) -> None:
    """MEASURED, and the measurement contradicts the artifact record's own claim.

    ``WIKISOURCE_SA.SV.KAU.SAMHITA.DEVANAGARI`` records that the artifact "includes real
    saman notation in Devanagari Extended". True of the ARTIFACT; false of every parsed
    verse, because that notation lives in page furniture the verse parser does not read.
    "The artifact contains saman notation" and "the ingested text is accented" are
    different claims and only the first holds.
    """
    assert outcome.coverage["accented_occurrences"] == 0
    assert not any(version.accented for version in outcome.release.text_versions)
    assert len(outcome.release.text_versions) == RELEASED_KEYS
    assert {version.text_version_id for version in outcome.release.text_versions} == {
        TEXT_VERSION_ID
    }
    assert {version.rights_status for version in outcome.release.text_versions} == {
        RightsStatus.CC_BY_SA
    }


def test_registry_rows_are_read_and_never_constructed_locally(outcome: BuildOutcome) -> None:
    assert [work.work_id for work in outcome.release.works] == [WORK_ID]
    assert [source.source_id for source in outcome.release.sources] == ["WIKISOURCE_SA"]
    assert [item.artifact_id for item in outcome.release.source_artifacts] == [ARTIFACT_ID]
    assert outcome.release.works[0].identity_status == "FINAL"
    assert outcome.release.works[0].coverage_status == "INCOMPLETE_BOUNDED"
    for assertion in outcome.release.source_assertions:
        assert assertion.source_id == "WIKISOURCE_SA"
        assert assertion.source_artifact_id == ARTIFACT_ID
        assert assertion.source_locator


def test_translations_and_audio_are_emitted_empty_not_omitted(outcome: BuildOutcome) -> None:
    """A zero-length file the manifest counts; an absent file is ambiguous."""
    families = outcome.release.families()
    for name in ("translations", "audio_recordings", "audio_segments", "traditional_metadata"):
        assert families[name] == []
        path = outcome.release.output_root / f"{name}.jsonl"
        assert path.exists()
        assert path.read_bytes() == b""
        assert outcome.manifest.record_counts[f"{name}.jsonl"] == 0


# ------------------------------------------------------------------------ determinism


def test_two_independent_rebuilds_are_byte_identical() -> None:
    if not WIKISOURCE_DIR.exists() or not GRETIL_SNAPSHOT.exists():
        pytest.skip("Samaveda snapshots are not pinned locally")
    identical, differing = verify_determinism()
    assert identical, differing


def test_record_ordering_is_a_documented_total_order(outcome: BuildOutcome) -> None:
    """Emission order is a function of the records, so a rebuild cannot permute a file."""
    passages = outcome.release.passages
    assert [item.canonical_key for item in passages] == sorted(
        item.canonical_key for item in passages
    )
    bindings = outcome.release.referent_bindings
    assert [item.canonical_key for item in bindings] == sorted(
        item.canonical_key for item in bindings
    )
    texts = outcome.release.text_versions
    assert [(str(item.passage_id), str(item.text_id)) for item in texts] == sorted(
        (str(item.passage_id), str(item.text_id)) for item in texts
    )
    citations = outcome.release.citations
    assert [(str(item.passage_id), item.system) for item in citations] == sorted(
        (str(item.passage_id), item.system) for item in citations
    )
    issues = outcome.release.qa_issues
    assert [(item.check_id, item.entity_id or "", str(item.issue_id)) for item in issues] == (
        sorted((item.check_id, item.entity_id or "", str(item.issue_id)) for item in issues)
    )


def test_the_manifest_pins_the_build_rather_than_the_clock(outcome: BuildOutcome) -> None:
    manifest = outcome.manifest
    assert manifest.built_at.isoformat() == "2026-09-07T00:00:00+00:00"
    assert manifest.works == [WORK_ID]
    assert manifest.passage_count == RELEASED_KEYS + 498
    assert manifest.build_config_sha256
    assert manifest.generated_content_sha256
    assert len(manifest.raw_snapshot_hashes) == 106
    assert manifest.parser_versions["samaveda_wikisource"] == ("wikisource-sa-samaveda-arcika-v2")
    assert "SAMAVEDA_GANA_CORPUS IS NOT IMPLIED" in manifest.rights_summary["scope"]
