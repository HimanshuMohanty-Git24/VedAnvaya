"""Release guards for the full canonical Vajasaneyi Samhita build.

Why these tests skip rather than ship fixtures
----------------------------------------------
``data/raw/**`` is gitignored, so the pinned Sanskrit Wikisource snapshots are absent in
a clean checkout and in CI. These tests skip when the snapshots are missing rather than
failing. Embedding a trimmed fixture instead was rejected for the same reason as in
``test_yajurveda_primary_text.py``: every property guarded here -- the ordinal-header
boundary signal, the duplicated reading at VSM 16.37, the rsi index's range syntax --
lives in the full-page structure that an excerpt discards.

What is deliberately NOT asserted
---------------------------------
No test here asserts the rsi assertion count against a remembered constant. Prior
research projected 2,106 and the build recomputes a different figure from the source
records; pinning either number would turn a measurement into a fixture and make the next
genuine index fix look like a regression. The tests assert INTERNAL CONSISTENCY instead:
that every metadata row has exactly one provenance row, that every row resolves to a
released passage, and that the reported count equals the emitted count.
"""

from __future__ import annotations

import json
from collections import Counter
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from scripts.build_yajurveda_canonical import (
    DEFAULT_CONFIG,
    INFERENCE_DERIVED,
    SOURCE_DECLARED,
    VsmReleaseConfig,
    build,
    registry_text_roles,
)
from vedagraph.config.registry import load_text_versions
from vedagraph.models import (
    Passage,
    PassageReferentBinding,
    SourceAssertion,
    TextVersion,
    TraditionalMetadataAssertion,
)
from vedagraph.models.enums import AssertionStatus, EntityType, MetadataPredicate, TextRole
from vedagraph.normalize import strip_vedic_accents
from vedagraph.storage import read_jsonl

RAW_ROOT = Path("data/raw/wikisource_sa")
ADHYAYA_COUNT = 40
#: Computed from the pinned artifact, not quoted from a reference work. It is asserted
#: here because the whole point of this release is that all 40 adhyayas are addressed.
EXPECTED_MANTRA_ADDRESSES = 1975
ACCENTED = "WIKISOURCE_SA.YV.VSM.ACCENTED"
UNACCENTED = "WIKISOURCE_SA.YV.VSM.UNACCENTED"

pytestmark = pytest.mark.skipif(
    not RAW_ROOT.exists(),
    reason="pinned Sanskrit Wikisource snapshots are gitignored and absent here",
)


@pytest.fixture(scope="module")
def config() -> VsmReleaseConfig:
    return VsmReleaseConfig.load(DEFAULT_CONFIG)


@pytest.fixture(scope="module")
def release_root(config: VsmReleaseConfig, tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("yajurveda_vsm_v1")
    build(config, DEFAULT_CONFIG, output_root=root)
    return root


@pytest.fixture(scope="module")
def passages(release_root: Path) -> list[Passage]:
    return list(read_jsonl(release_root / "passages.jsonl", Passage))


@pytest.fixture(scope="module")
def text_versions(release_root: Path) -> list[TextVersion]:
    return list(read_jsonl(release_root / "text_versions.jsonl", TextVersion))


@pytest.fixture(scope="module")
def assertions(release_root: Path) -> list[SourceAssertion]:
    return list(read_jsonl(release_root / "source_assertions.jsonl", SourceAssertion))


@pytest.fixture(scope="module")
def report(release_root: Path) -> dict[str, Any]:
    payload: dict[str, Any] = json.loads(
        (release_root / "reports" / "build_report.json").read_text(encoding="utf-8")
    )
    return payload


# -- scale ------------------------------------------------------------------------------


def test_all_forty_adhyayas_are_released(passages: list[Passage]) -> None:
    sections = [item for item in passages if item.entity_type == EntityType.SECTION]
    assert len(sections) == ADHYAYA_COUNT
    assert sorted(int(item.hierarchy["adhyaya"]) for item in sections) == list(range(1, 41))


def test_all_1975_mantra_addresses_are_released(passages: list[Passage]) -> None:
    mantras = [item for item in passages if item.entity_type == EntityType.MANTRA]
    assert len(mantras) == EXPECTED_MANTRA_ADDRESSES
    assert len({item.canonical_key for item in mantras}) == EXPECTED_MANTRA_ADDRESSES


def test_every_mantra_hangs_off_its_adhyaya_with_a_contiguous_sequence(
    passages: list[Passage],
) -> None:
    by_key = {item.canonical_key: item for item in passages}
    children: dict[str, list[int]] = {}
    for item in passages:
        if item.entity_type != EntityType.MANTRA:
            continue
        assert item.parent_key is not None
        assert by_key[item.parent_key].entity_type == EntityType.SECTION
        children.setdefault(item.parent_key, []).append(item.sequence_in_parent)
    assert len(children) == ADHYAYA_COUNT
    for parent, sequences in children.items():
        assert sorted(sequences) == list(range(1, len(sequences) + 1)), parent


# -- roles: the regression guard against the forbidden relabelling -----------------------


def test_text_roles_are_taken_from_the_registry(text_versions: list[TextVersion]) -> None:
    declared = {item.text_version_id: item.text_role for item in load_text_versions()}
    emitted = {item.text_version_id: item.text_role for item in text_versions}
    assert emitted == {
        ACCENTED: declared[ACCENTED],
        UNACCENTED: declared[UNACCENTED],
    }
    assert registry_text_roles((ACCENTED, UNACCENTED)) == emitted


def test_the_accented_layer_is_never_emitted_as_primary_text(
    text_versions: list[TextVersion], report: dict[str, Any]
) -> None:
    """The forbidden shortcut, guarded directly.

    Relabelling ``EXTRACTED_FROM_CONTAINER`` as ``PRIMARY_TEXT`` would make the layer
    statistics uniform and would make an interpretive segmentation canonical. It is the
    one change this release must never make, so it is asserted as a property of the
    emitted rows rather than left to code review.
    """
    accented = [item for item in text_versions if item.text_version_id == ACCENTED]
    assert accented, "the accented layer must be emitted"
    assert {item.text_role for item in accented} == {TextRole.EXTRACTED_FROM_CONTAINER}
    assert all(item.text_role is not TextRole.PRIMARY_TEXT for item in text_versions)
    assert report["has_primary_text_layer"] == "NO"


def test_layer_statistics_are_four_distinct_figures(report: dict[str, Any]) -> None:
    statistics = report["layer_statistics"]
    assert set(statistics) == {
        "source_declared_units",
        "inference_derived_units",
        "variant_bearing_units",
        "review_items",
    }
    assert (
        statistics["source_declared_units"] + statistics["inference_derived_units"]
        == EXPECTED_MANTRA_ADDRESSES
    )
    # A build that merged the two would report every unit as source-declared. Both classes
    # must be genuinely populated for the split to mean anything.
    assert statistics["source_declared_units"] > 0
    assert statistics["inference_derived_units"] > 0


def test_boundary_provenance_is_carried_per_record(
    assertions: list[SourceAssertion], report: dict[str, Any]
) -> None:
    rows = [item for item in assertions if item.predicate == "ACCENTED_BOUNDARY_PROVENANCE"]
    assert len(rows) == EXPECTED_MANTRA_ADDRESSES
    counts = Counter(item.value["boundary_provenance"] for item in rows)
    assert counts[SOURCE_DECLARED] == report["layer_statistics"]["source_declared_units"]
    assert counts[INFERENCE_DERIVED] == report["layer_statistics"]["inference_derived_units"]
    inferred = [item for item in rows if item.value["boundary_provenance"] == INFERENCE_DERIVED]
    assert all(item.status is AssertionStatus.NEEDS_REVIEW for item in inferred)


# -- VSM 16.37 ---------------------------------------------------------------------------


def test_vsm_16_37_keeps_both_printed_readings(
    text_versions: list[TextVersion], assertions: list[SourceAssertion]
) -> None:
    """One occurrence identity, two attested readings, no silent selection."""
    key = "VG:YV:VSM:A16:V037"
    record = next(
        item
        for item in text_versions
        if item.text_version_id == ACCENTED and item.source_locator.endswith("#16.37")
    )
    second = [
        item
        for item in assertions
        if item.subject_id == key and item.predicate == "EDITORIAL_INTERVENTION_SECOND_READING"
    ]
    assert len(second) == 1
    preserved = second[0].value["text"]

    # Both readings survive, and they differ at exactly the disputed word. Accents are
    # stripped only for this comparison, because the two printings mark tone differently
    # and the point at issue is the CONSONANTS: srutyaya against satyaya.
    kept = strip_vedic_accents(record.text_nfc)
    other = strip_vedic_accents(preserved)
    assert "स्रुत्याय" in kept and "सत्याय" not in kept  # srutyaya, not satyaya
    assert "सत्याय" in other and "स्रुत्याय" not in other  # satyaya, not srutyaya
    assert preserved != record.text_original

    # Untruncated: the preserved reading still carries the source's own terminal marker
    # for mantra 37, which is only present if the whole unit was stored rather than a
    # truncated excerpt of it.
    assert preserved.rstrip().endswith("।।")
    assert "३७" in preserved
    assert len(preserved) > 80

    # No winner was chosen: the variant is flagged for recorded human review.
    assert second[0].status is AssertionStatus.NEEDS_REVIEW
    assert "NEEDS_REVIEW" in second[0].value["declared_status"]


def test_the_variant_does_not_split_passage_identity(passages: list[Passage]) -> None:
    """The corpus is not blocked over 16.37 and the address stays one occurrence."""
    matches = [item for item in passages if item.canonical_key == "VG:YV:VSM:A16:V037"]
    assert len(matches) == 1
    assert matches[0].canonical_citation == "VSM 16.37"


def test_the_variant_is_reported_rather_than_resolved(release_root: Path) -> None:
    issues = json.loads(
        (release_root / "reports" / "build_report.json").read_text(encoding="utf-8")
    )
    assert issues["variant_bearing_addresses"] == ["VSM 16.37"]
    assert issues["qa_issue_counts"]["YV-VARIANT-READING-UNRESOLVED"] == 1


# -- traditional metadata ----------------------------------------------------------------


def test_rishi_assertions_are_recomputed_and_internally_consistent(
    release_root: Path,
    report: dict[str, Any],
    passages: list[Passage],
    assertions: list[SourceAssertion],
) -> None:
    rows = list(
        read_jsonl(release_root / "traditional_metadata.jsonl", TraditionalMetadataAssertion)
    )
    rishi = report["rishi"]

    # The reported figure is the emitted figure, recomputed at build time.
    assert rishi["computed_assertions"] == len(rows)
    assert rishi["computed_assertions"] > 0
    assert (
        rishi["difference_vs_projection"]
        == rishi["computed_assertions"] - rishi["projected_assertions_prior_research"]
    )

    # Every row resolves to a released passage, and every row is paired 1:1 with a
    # provenance assertion carrying the artifact the metadata model cannot hold.
    known = {item.entity_id for item in passages if item.entity_type == EntityType.MANTRA}
    assert all(item.scope.passage_id in known for item in rows)
    assert all(item.predicate is MetadataPredicate.HAS_RISHI for item in rows)

    provenance = [
        item for item in assertions if item.predicate == "TRADITIONAL_METADATA_PROVENANCE"
    ]
    assert len(provenance) == len(rows)
    assert {str(item.assertion_id) for item in rows} == {
        item.value["metadata_assertion_id"] for item in provenance
    }
    assert all(item.source_artifact_id == "WIKISOURCE_SA.YV.VSM.RISHISUCI" for item in provenance)
    assert all(item.source_locator for item in rows)
    assert all("entity_resolution_method" in item.value for item in provenance)


def test_no_devata_or_chandas_assertion_is_invented(
    release_root: Path, report: dict[str, Any]
) -> None:
    rows = list(
        read_jsonl(release_root / "traditional_metadata.jsonl", TraditionalMetadataAssertion)
    )
    predicates = {item.predicate for item in rows}
    assert MetadataPredicate.HAS_DEVATA not in predicates
    assert MetadataPredicate.HAS_CHANDAS not in predicates
    assert report["rishi"]["devata_assertions"] == 0
    assert report["rishi"]["chandas_assertions"] == 0
    # The absence is reported as a gap rather than left silent.
    assert report["qa_issue_counts"]["YV-DEVATA-NOT-ASSERTED"] == 1
    assert report["qa_issue_counts"]["YV-CHANDAS-NOT-ASSERTED"] == 1


def test_metadata_gaps_are_reported_not_defaulted(report: dict[str, Any]) -> None:
    rishi = report["rishi"]
    assert rishi["rows_off_corpus"] == []
    # Any adhyaya the index does not reach is reported, never filled with the
    # Sarvanukramasutra's samhita-wide vivasvan default.
    if rishi["adhyayas_not_covered"]:
        assert report["qa_issue_counts"]["YV-RISHI-ADHYAYA-UNCOVERED"] == 1


# -- translations and audio ---------------------------------------------------------------


def test_english_translation_coverage_is_partial_and_the_gap_is_reported(
    release_root: Path, report: dict[str, Any]
) -> None:
    """Griffith 1899 is ingested, and the 72 mantras it does not reach stay visible.

    REPLACES ``test_english_translation_is_absent_and_said_to_be_absent``, which asserted
    zero translations. That was true when the slot was empty and became false the moment
    the slot was filled -- so on its own it would have failed for the RIGHT reason and been
    "fixed" by deleting it. What it was really guarding is that the English layer never
    claims more coverage than it has, and that property is what is asserted here instead:
    partial coverage, counted, with the shortfall named.
    """
    rows = [
        json.loads(line)
        for line in (release_root / "translations.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert rows, "Griffith 1899 is declared in the config, so the layer must not be empty"
    assert len(rows) == report["record_counts"]["translations"]

    # One translation per passage at most: a duplicate would mean two printed verse numbers
    # resolved to one key, which is the alignment defect the acquisition stage refuses.
    passage_ids = [row["passage_id"] for row in rows]
    assert len(passage_ids) == len(set(passage_ids))

    assert {row["language"] for row in rows} == {"en"}
    assert {row["rights_status"] for row in rows} == {"PUBLIC_DOMAIN"}
    assert {row["year"] for row in rows} == {1899}

    # Coverage is PARTIAL and the shortfall is arithmetic, not prose.
    mantras = report["address_count"]
    assert 0 < len(rows) < mantras, "coverage must be partial; full coverage is not claimed"
    assert report["gaps"]["english_translation_missing"] == mantras - len(rows)

    # Units whose spine diverges are not passed off as exact.
    alignments = {row["alignment"] for row in rows}
    assert alignments <= {"EXACT_MANTRA_ALIGNMENT", "RANGE_ALIGNMENT"}


def test_a_translation_source_can_be_declared_later(
    config: VsmReleaseConfig, tmp_path: Path
) -> None:
    """The empty slot is live: a declared source is read, and a broken one stops the build.

    Without this, "translation_sources: []" would be indistinguishable from a config key
    nothing reads, and Griffith could be dropped in later against a builder that ignores
    it.
    """
    from dataclasses import replace

    from scripts.build_yajurveda_canonical import BuildError, TranslationSourceSpec, assemble

    missing = replace(
        config,
        translation_sources=(
            TranslationSourceSpec(
                source_id="WIKISOURCE_EN",
                source_artifact_id="WIKISOURCE_EN.YV.VSM.GRIFFITH_1899",
                jsonl_path=tmp_path / "not-fetched-yet.jsonl",
            ),
        ),
    )
    with pytest.raises(BuildError, match="does not exist"):
        assemble(missing, output_root=tmp_path / "out")


def test_audio_is_reference_only(release_root: Path) -> None:
    assert (release_root / "audio_recordings.jsonl").read_bytes() == b""
    assert (release_root / "audio_segments.jsonl").read_bytes() == b""


# -- integrity ----------------------------------------------------------------------------


def test_every_address_has_a_referent_binding_and_no_key_shares_an_occurrence(
    release_root: Path,
) -> None:
    bindings = list(read_jsonl(release_root / "referent_bindings.jsonl", PassageReferentBinding))
    assert len(bindings) == EXPECTED_MANTRA_ADDRESSES
    assert len({item.canonical_key for item in bindings}) == EXPECTED_MANTRA_ADDRESSES
    assert len({item.source_locator for item in bindings}) == EXPECTED_MANTRA_ADDRESSES


# -- determinism ---------------------------------------------------------------------------


def test_two_independent_rebuilds_are_byte_identical(
    config: VsmReleaseConfig, release_root: Path, tmp_path: Path
) -> None:
    second = tmp_path / "rebuild"
    build(config, DEFAULT_CONFIG, output_root=second)
    assert _tree(release_root) == _tree(second)


def _tree(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }
