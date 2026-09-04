"""Checks against the generated lexical layer.

Everything here skips when the layer or the pinned snapshots are absent, because both
are deliberately excluded from Git. When they are present these are the tests that
matter most: they assert against the real 10,552-mantra build rather than a fixture.
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import pytest

from vedagraph.lexical.build import build_lexical_layer
from vedagraph.lexical.morphology import load_morphology_artifacts
from vedagraph.lexical.output import write_lexical_layer
from vedagraph.models.enums import (
    LexicalPredicate,
    LexicalProvenanceClass,
    MentionMethod,
    QASeverity,
)
from vedagraph.models.lexical import (
    AmbiguousMention,
    ComponentAssertion,
    EntityCoOccurrence,
    ExactParallelGroup,
    MantraParallel,
    MentionAssertion,
    MorphologyToken,
)
from vedagraph.storage.jsonl import read_jsonl

CORPUS = Path("data/canonical/rigveda_full_v1")
KNOWLEDGE = Path("data/knowledge/rigveda_deterministic_v1")
LEXICAL = Path("data/knowledge/rigveda_lexical_v1")
ARTIFACT_INDEX = Path("data/derived/vedaweb_morphology_artifacts.json")
BUILT_AT = datetime(2026, 9, 4, tzinfo=UTC)

pytestmark = pytest.mark.skipif(
    not (LEXICAL / "manifest.json").exists(),
    reason="generated lexical layer is not present (excluded from Git)",
)


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads((LEXICAL / "manifest.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def stats() -> dict:
    return json.loads((LEXICAL / "lexical_stats.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def qa() -> dict:
    return json.loads((LEXICAL / "lexical_qa.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def tokens() -> list[MorphologyToken]:
    return list(read_jsonl(LEXICAL / "tokens.jsonl", MorphologyToken))


@pytest.fixture(scope="module")
def mentions() -> list[MentionAssertion]:
    return list(read_jsonl(LEXICAL / "mentions.jsonl", MentionAssertion))


# --- Alignment -------------------------------------------------------------------


def test_every_mantra_carries_morphology(qa):
    alignment = qa["alignment"]
    assert alignment["mantras_expected"] == 10_552
    assert alignment["mantras_with_morphology"] == 10_552
    assert alignment["unaligned_records"] == 0
    assert alignment["duplicate_token_keys"] == 0
    assert alignment["passage_mismatches"] == 0


def test_no_token_lacks_a_lemma(qa):
    parse = qa["morphology_parse"]
    assert parse["stanzas_seen"] == parse["stanzas_with_annotation"] == 10_552
    assert parse["tokens_without_lemma"] == 0
    assert parse["unparsable_stanza_ids"] == 0
    assert parse["unparsable_token_ids"] == 0


def test_qa_has_no_errors(qa):
    assert qa["errors"] == 0
    assert qa["status"] in {"PASSED", "PASSED_WITH_WARNINGS"}


def test_token_keys_are_unique_and_sequences_contiguous(tokens):
    keys = {token.token_key for token in tokens}
    assert len(keys) == len(tokens)
    by_passage: dict[str, list[int]] = defaultdict(list)
    for token in tokens:
        by_passage[token.passage_key].append(token.sequence)
    for passage_key, sequences in by_passage.items():
        assert sorted(sequences) == list(range(1, len(sequences) + 1)), passage_key


def test_tokens_reference_the_annotation_layer_not_the_canonical_text(tokens, manifest):
    assert manifest["canonical_text_version_id"] == "GRETIL.RV.AUFRECHT"
    assert manifest["morphology_annotation_layer_id"] == "VEDAWEB.ZURICH"
    sample = tokens[0]
    assert sample.annotation_layer_id == "VEDAWEB.ZURICH"
    assert "VEDAWEB-ZURICH" in sample.token_key
    # The mantra's own key is untouched by the annotation layer.
    assert sample.passage_key.startswith("VG:RV:SAK:M")
    assert "VEDAWEB" not in sample.passage_key


# --- Mentions --------------------------------------------------------------------


def test_every_mention_is_lemma_id_matched(mentions):
    methods = {item.method for mention in mentions for item in mention.evidence}
    assert methods == {MentionMethod.LEMMA_ID_EXACT}


def test_every_mention_carries_evidence_that_exists(mentions, tokens):
    token_keys = {token.token_key for token in tokens}
    for mention in mentions:
        assert mention.evidence
        assert mention.occurrence_count == len(mention.evidence)
        assert mention.predicate is LexicalPredicate.MENTIONS_ENTITY
        assert mention.provenance_class is LexicalProvenanceClass.DETERMINISTIC_DERIVED
        for item in mention.evidence:
            assert item.token_key in token_keys


def test_mentions_are_devata_only(mentions):
    assert {mention.entity_type.value for mention in mentions} == {"DEVATA"}
    assert all(mention.object_key.startswith("VG:DEVATA:") for mention in mentions)


def test_one_edge_per_mantra_entity_pair(mentions):
    pairs = [(mention.subject_key, mention.object_key) for mention in mentions]
    assert len(pairs) == len(set(pairs))


def test_some_mantras_mention_an_entity_more_than_once(mentions):
    repeated = [mention for mention in mentions if mention.occurrence_count > 1]
    assert repeated, "multi-occurrence evidence should exist in a corpus this size"
    for mention in repeated:
        sequences = [item.sequence for item in mention.evidence]
        assert sequences == sorted(sequences)
        assert len(set(sequences)) == len(sequences)


def test_ambiguous_tokens_produce_no_edges():
    ambiguous = list(read_jsonl(LEXICAL / "ambiguous_mentions.jsonl", AmbiguousMention))
    mentions = list(read_jsonl(LEXICAL / "mentions.jsonl", MentionAssertion))
    evidence_tokens = {item.token_key for mention in mentions for item in mention.evidence}
    for item in ambiguous:
        assert item.token_key not in evidence_tokens
        assert item.status.value.startswith("AMBIGUOUS")


def test_suppressed_lemmas_never_appear_as_evidence(mentions):
    """The DO_NOT_MATCH rules are the main precision guard; verify they held."""
    suppressed = {"ká-", "rátha-", "áśva-", "hári-", "áhi-", "śyená-", "púruṣa-"}
    lemmas = {item.lemma for mention in mentions for item in mention.evidence}
    assert not (lemmas & suppressed)


def test_mention_precision_is_measured_and_high(mentions, tokens):
    """Grammatical gender is independent of how the aliases were chosen."""
    by_key = {token.token_key: token for token in tokens}
    per_entity: dict[str, list[str]] = defaultdict(list)
    for mention in mentions:
        for item in mention.evidence:
            per_entity[mention.object_key].append(
                by_key[item.token_key].morphological_features.get("gender", "-")
            )
    total = sum(len(values) for values in per_entity.values())
    off = 0
    for genders in per_entity.values():
        expected = max(set(genders), key=genders.count)
        off += sum(1 for gender in genders if gender != expected)
    assert total > 0
    assert off / total < 0.02, f"off-gender rate {off}/{total} exceeds 2%"


# --- Components ------------------------------------------------------------------


def test_components_are_human_reviewed_only():
    components = list(read_jsonl(LEXICAL / "devata_components.jsonl", ComponentAssertion))
    assert components
    for component in components:
        assert component.provenance_class is LexicalProvenanceClass.HUMAN_REVIEWED
        assert component.review_status.value == "ACCEPTED"
        assert component.subject_key != component.object_key


def test_no_group_deity_was_expanded():
    components = list(read_jsonl(LEXICAL / "devata_components.jsonl", ComponentAssertion))
    expanded = {component.subject_key for component in components}
    assert "VG:DEVATA:VISVEDEVAH" not in expanded
    assert "VG:DEVATA:ADITYAH" not in expanded


# --- Parallels -------------------------------------------------------------------


def test_parallel_pairs_are_canonically_ordered():
    parallels = list(read_jsonl(LEXICAL / "mantra_parallels.jsonl", MantraParallel))
    assert parallels
    seen = set()
    for parallel in parallels:
        assert parallel.subject_key < parallel.object_key
        key = (parallel.subject_key, parallel.object_key, parallel.predicate)
        assert key not in seen
        seen.add(key)


def test_exact_parallels_record_the_level_they_matched_at():
    parallels = [
        item
        for item in read_jsonl(LEXICAL / "mantra_parallels.jsonl", MantraParallel)
        if item.predicate is LexicalPredicate.EXACT_PARALLEL_OF
    ]
    assert parallels
    for parallel in parallels:
        assert parallel.methods
        assert parallel.strongest_method is not None
        assert parallel.strongest_method in parallel.methods


def test_exact_groups_are_consistent():
    groups = list(read_jsonl(LEXICAL / "exact_parallel_groups.jsonl", ExactParallelGroup))
    assert groups
    for group in groups:
        assert group.size == len(group.member_keys) >= 2
        assert group.member_keys == sorted(group.member_keys)
        assert len(group.member_citations) == group.size


def test_parallel_engine_did_not_compare_every_pair(qa):
    engine = qa["parallel_engine"]
    all_pairs = 10_552 * 10_551 // 2
    assert engine["candidate_pairs_generated"] < all_pairs * 0.01
    # No recall was silently capped by the bucket limit.
    assert engine["oversized_buckets_skipped"] == 0


def test_accepted_near_parallels_carry_metrics():
    accepted = [
        item
        for item in read_jsonl(LEXICAL / "mantra_parallels.jsonl", MantraParallel)
        if item.predicate is LexicalPredicate.PARALLEL_TO
    ]
    for parallel in accepted:
        assert parallel.metrics is not None
        assert parallel.status.value == "HIGH_CONFIDENCE_NEAR_PARALLEL"
        assert parallel.metrics.ordered_token_similarity >= 0.80
        assert parallel.metrics.token_jaccard >= 0.70


# --- Analytics -------------------------------------------------------------------


def test_assignment_and_mention_rank_differently(stats):
    assigned = [row["entity_key"] for row in stats["top_assigned_devatas"]]
    mentioned = [row["entity_key"] for row in stats["top_mentioned_devatas"]]
    assert assigned != mentioned, "the two metrics must not be silently the same list"


def test_entities_assigned_but_never_mentioned_are_visible(stats):
    rows = {row["entity_key"]: row for row in stats["top_assigned_devatas"]}
    group = rows.get("VG:DEVATA:VISVEDEVAH")
    assert group is not None
    assert group["mantra_assignment_count"] > 0
    assert group["mantra_mention_count"] == 0


def test_stats_warn_against_one_combined_number(stats):
    assert "most used god" in stats["metric_definitions"]["warning"]


def test_co_occurrence_is_ordered_and_labelled():
    rows = list(read_jsonl(LEXICAL / "entity_co_occurrence.jsonl", EntityCoOccurrence))
    assert rows
    for row in rows:
        assert row.left_entity_key < row.right_entity_key
        assert row.unit == "MANTRA"
        assert row.method == "LEXICAL_MENTION_CO_OCCURRENCE"


# --- Manifest and reproducibility -------------------------------------------------


def test_manifest_pins_every_input(manifest):
    assert manifest["version"].endswith("deterministic-lexical-1.0.0-rc1")
    assert len(manifest["corpus_manifest_sha256"]) == 64
    assert len(manifest["knowledge_manifest_sha256"]) == 64
    assert manifest["morphology_commit_sha"] == "d3eb8af7324338161520d2d35eae8f7e985a19a5"
    assert manifest["morphology_license"] == "CC BY 4.0"
    assert len(manifest["morphology_artifact_ids"]) == 10
    assert len(manifest["morphology_artifact_hashes"]) == 10
    assert set(manifest["lexical_registry_hashes"]) == {
        "lexical_aliases.yaml",
        "devata_components.yaml",
    }
    for key in ("mention_policy_version", "parallel_policy_version", "token_id_policy_version"):
        assert manifest[key]
    assert len(manifest["component_mapping_sha256"]) == 64


def test_manifest_whitelists_only_the_approved_predicates(manifest):
    assert manifest["predicate_whitelist"] == [
        "MENTIONS_ENTITY",
        "EXACT_PARALLEL_OF",
        "PARALLEL_TO",
        "HAS_COMPONENT",
    ]


def test_manifest_hashes_match_the_files_on_disk(manifest):
    from vedagraph.storage.manifest import file_sha256

    for entry in manifest["generated_files"]:
        path = LEXICAL / str(entry["path"])
        assert path.exists(), path
        assert file_sha256(path) == entry["sha256"], path


@pytest.mark.skipif(
    not ARTIFACT_INDEX.exists(), reason="pinned morphology snapshots are not present"
)
def test_rebuild_is_byte_identical(tmp_path):
    """Two builds from the same inputs must produce the same bytes."""
    artifacts = load_morphology_artifacts(ARTIFACT_INDEX)
    result = build_lexical_layer(corpus_dir=CORPUS, knowledge_dir=KNOWLEDGE, artifacts=artifacts)
    rebuilt = write_lexical_layer(
        result,
        output_dir=tmp_path / "rebuild",
        corpus_dir=CORPUS,
        knowledge_dir=KNOWLEDGE,
        artifacts=artifacts,
        built_at=BUILT_AT,
    )
    committed = json.loads((LEXICAL / "manifest.json").read_text(encoding="utf-8"))
    rebuilt_files = {
        str(entry["path"]): entry["sha256"]
        for entry in rebuilt.model_dump(mode="json")["generated_files"]
    }
    committed_files = {
        str(entry["path"]): entry["sha256"] for entry in committed["generated_files"]
    }
    assert rebuilt_files == committed_files


def test_qa_issues_are_informational_only():
    from vedagraph.models import QAIssue

    issues = list(read_jsonl(LEXICAL / "qa_issues.jsonl", QAIssue))
    assert not [issue for issue in issues if issue.severity is QASeverity.ERROR]
