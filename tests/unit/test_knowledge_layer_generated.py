"""Checks against the generated knowledge layer.

Everything here skips when the layer or the pinned snapshots are absent, because both
are deliberately excluded from Git.
"""

import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

import pytest

from vedagraph.knowledge.build import build_knowledge, load_artifact_index
from vedagraph.knowledge.compare import compare_with_vhp
from vedagraph.knowledge.output import write_knowledge_layer
from vedagraph.knowledge.stats import build_stats
from vedagraph.models import KnowledgeAssertion, KnowledgeEntity, MetadataSourceAssertion, Passage
from vedagraph.models.enums import (
    EntityType,
    KnowledgeEntityType,
    MetadataAgreement,
    MetadataPredicate,
    QASeverity,
    ResolutionStatus,
)
from vedagraph.storage.jsonl import read_jsonl

CORPUS = Path("data/canonical/rigveda_full_v1")
KNOWLEDGE = Path("data/knowledge/rigveda_deterministic_v1")
ARTIFACTS = Path("data/derived/wsc2023_anukramani_artifacts.json")
REGISTRY = Path("data/registry")

pytestmark = pytest.mark.skipif(
    not (KNOWLEDGE / "manifest.json").exists() or not ARTIFACTS.exists(),
    reason="knowledge layer or pinned Anukramaṇī snapshots not generated",
)


@pytest.fixture(scope="module")
def manifest() -> dict[str, object]:
    return json.loads((KNOWLEDGE / "manifest.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def assertions() -> list[KnowledgeAssertion]:
    return list(read_jsonl(KNOWLEDGE / "knowledge_assertions.jsonl", KnowledgeAssertion))


def test_all_ten_mandalas_are_covered(manifest: dict[str, object]) -> None:
    ids = manifest["source_artifact_ids"]
    assert isinstance(ids, list)
    assert sorted(ids) == sorted(f"WSC2023.RV.ANUKRAMANI.M{n:02d}" for n in range(1, 11))
    hashes = manifest["source_artifact_hashes"]
    assert isinstance(hashes, dict)
    assert len(hashes) == 10
    assert all(len(value) == 64 for value in hashes.values())


def test_the_manifest_pins_the_exact_corpus_and_registries(manifest: dict[str, object]) -> None:
    from vedagraph.storage.manifest import file_sha256

    assert manifest["corpus_manifest_sha256"] == file_sha256(CORPUS / "manifest.json")
    assert manifest["corpus_passage_count"] == 10552
    assert len(str(manifest["source_commit_sha"])) == 40
    registry_hashes = manifest["registry_hashes"]
    assert isinstance(registry_hashes, dict)
    for name, digest in registry_hashes.items():
        assert digest == file_sha256(REGISTRY / name)


def test_the_predicate_whitelist_is_exactly_three(manifest: dict[str, object]) -> None:
    assert manifest["predicate_whitelist"] == ["HAS_RISHI", "HAS_DEVATA", "HAS_CHANDAS"]


def test_every_dataset_row_aligned() -> None:
    qa = json.loads((KNOWLEDGE / "knowledge_qa.json").read_text(encoding="utf-8"))
    alignment = qa["alignment"]
    assert alignment["dataset_rows"] == 1028
    assert alignment["aligned_rows"] == 1028
    assert alignment["unaligned_rows"] == []
    assert alignment["duplicate_rows"] == []
    assert alignment["verse_count_mismatches"] == []
    assert alignment["missing_corpus_suktas"] == []
    assert qa["errors"] == 0


def test_no_assertion_points_at_a_passage_or_entity_that_does_not_exist(
    assertions: list[KnowledgeAssertion],
) -> None:
    passages = {
        passage.canonical_key: passage.entity_id
        for passage in read_jsonl(CORPUS / "passages.jsonl", Passage)
        if passage.entity_type is EntityType.MANTRA
    }
    entities: dict[str, object] = {}
    for name in ("entities_rishis.jsonl", "entities_devatas.jsonl", "entities_chandas.jsonl"):
        for entity in read_jsonl(KNOWLEDGE / name, KnowledgeEntity):
            entities[entity.entity_key] = entity.entity_id
    assert len(assertions) > 30_000
    for assertion in assertions:
        assert passages[assertion.subject_key] == assertion.subject_id
        assert entities[assertion.object_key] == assertion.object_id


def test_every_edge_names_a_real_source_assertion(assertions: list[KnowledgeAssertion]) -> None:
    sources = {
        item.assertion_id: item
        for item in read_jsonl(
            KNOWLEDGE / "metadata_source_assertions.jsonl", MetadataSourceAssertion
        )
    }
    for assertion in assertions:
        source = sources[assertion.source_assertion_id]
        assert source.raw_value == assertion.source_label
        assert source.predicate is assertion.predicate
        assert assertion.subject_key.startswith(source.subject_key)


def test_resolution_methods_are_all_deterministic(assertions: list[KnowledgeAssertion]) -> None:
    methods = {assertion.resolution_method for assertion in assertions}
    assert methods <= {
        ResolutionStatus.EXACT,
        ResolutionStatus.NORMALIZED_EXACT,
        ResolutionStatus.KNOWN_ALIAS,
        ResolutionStatus.COMPOSITE_PRESERVED,
    }
    assert ResolutionStatus.KNOWN_ALIAS in methods
    assert ResolutionStatus.COMPOSITE_PRESERVED in methods


def test_multiple_rishis_and_devatas_on_one_mantra_are_representable(
    assertions: list[KnowledgeAssertion],
) -> None:
    per_mantra: dict[tuple[str, MetadataPredicate], set[str]] = defaultdict(set)
    for assertion in assertions:
        per_mantra[(assertion.subject_key, assertion.predicate)].add(assertion.object_key)
    multiples = Counter(predicate for (_, predicate), keys in per_mantra.items() if len(keys) > 1)
    assert multiples[MetadataPredicate.HAS_RISHI] > 0
    assert multiples[MetadataPredicate.HAS_DEVATA] > 0


def test_composite_devatas_are_preserved_and_not_decomposed() -> None:
    entities = list(read_jsonl(KNOWLEDGE / "entities_devatas.jsonl", KnowledgeEntity))
    composites = [entity for entity in entities if entity.is_composite]
    assert composites
    labels = {entity.preferred_label for entity in entities}
    for entity in composites:
        assert len(entity.composite_parts) > 1
        assert entity.resolution_status is ResolutionStatus.COMPOSITE_PRESERVED
    # A dual is one label, never split into its components.
    assert "mitrāvaruṇau" in labels
    duals = {entity.entity_key for entity in entities if entity.preferred_label == "mitrāvaruṇau"}
    assert duals == {"VG:DEVATA:MITRAVARUNAU"}


def test_soma_and_pavamana_soma_stay_distinct() -> None:
    keys = {
        entity.preferred_label: entity.entity_key
        for entity in read_jsonl(KNOWLEDGE / "entities_devatas.jsonl", KnowledgeEntity)
    }
    assert keys["somaḥ"] != keys["pavamānaḥ somaḥ"]


def test_coverage_and_frequency_stats_are_consistent(
    assertions: list[KnowledgeAssertion],
) -> None:
    stats = json.loads((KNOWLEDGE / "knowledge_stats.json").read_text(encoding="utf-8"))
    assert stats["total_mantras"] == 10552
    assert stats["knowledge_assertions"] == len(assertions)
    assert sum(item["assertion_count"] for item in stats["coverage"]) == len(assertions)
    for item in stats["coverage"]:
        assert item["mantras_resolved"] + item["mantras_without_claim"] <= item["total_mantras"]
    top = stats["top_devatas"][0]
    counted = len(
        {
            assertion.subject_key
            for assertion in assertions
            if assertion.object_key == top["entity_key"]
        }
    )
    assert counted == top["mantra_assignment_count"]
    assert "not" in stats["metric_definition"]


def test_the_vhp_overlap_is_compared_without_either_source_winning() -> None:
    artifacts = load_artifact_index(ARTIFACTS)
    result = build_knowledge(corpus_dir=CORPUS, artifacts=artifacts, registry_root=REGISTRY)
    comparisons = compare_with_vhp(CORPUS, result.source_assertions, result.corpus)
    assert comparisons
    verdicts = {comparison.agreement for comparison in comparisons}
    assert verdicts <= set(MetadataAgreement)
    assert MetadataAgreement.AGREE_EXACT in verdicts
    # A disagreement is recorded, not resolved: both sides keep their own values.
    for comparison in comparisons:
        assert comparison.left_values and comparison.right_values
        if comparison.agreement is not MetadataAgreement.AGREE_EXACT:
            assert comparison.notes


def test_the_layer_rebuilds_byte_identically(tmp_path: Path) -> None:
    artifacts = load_artifact_index(ARTIFACTS)
    original = json.loads((KNOWLEDGE / "manifest.json").read_text(encoding="utf-8"))
    result = build_knowledge(corpus_dir=CORPUS, artifacts=artifacts, registry_root=REGISTRY)
    manifest = write_knowledge_layer(
        result,
        build_stats(result),
        output_dir=tmp_path / "rebuild",
        corpus_dir=CORPUS,
        artifacts=artifacts,
        built_at=datetime.fromisoformat(str(original["built_at"])).astimezone(UTC),
        registry_root=REGISTRY,
    )
    rebuilt = {item["path"]: item["sha256"] for item in manifest.generated_files}
    before = {item["path"]: item["sha256"] for item in original["generated_files"]}
    assert rebuilt == before
    assert not [issue for issue in result.qa_issues if issue.severity is QASeverity.ERROR]


def test_every_source_label_reaches_a_registered_entity_or_is_reported() -> None:
    for name, entity_type in (
        ("unresolved_rishis.jsonl", KnowledgeEntityType.RISHI),
        ("unresolved_devatas.jsonl", KnowledgeEntityType.DEVATA),
        ("unresolved_chandas.jsonl", KnowledgeEntityType.CHANDAS),
    ):
        path = KNOWLEDGE / name
        assert path.exists(), f"{entity_type} unresolved report must exist even when empty"
