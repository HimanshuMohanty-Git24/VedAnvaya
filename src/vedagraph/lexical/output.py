"""Write the lexical layer to disk and pin it to everything it was built from.

Output is byte-stable: records are sorted before writing, JSON keys are sorted, and the
build timestamp is injected rather than read from the clock. The manifest names the exact
corpus manifest, knowledge manifest, morphology artifacts, registries and policy versions
a run used, so a later reader can tell whether two builds are comparable.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

import orjson
from pydantic import BaseModel

from vedagraph import __version__
from vedagraph.lexical.aliases import LEXICAL_ALIAS_FILE, MENTION_POLICY_VERSION
from vedagraph.lexical.build import (
    CANONICAL_TEXT_VERSION_ID,
    LEXICAL_LAYER_VERSION,
    LEXICAL_QA_POLICY_VERSION,
    TOKEN_ID_POLICY_VERSION,
    LexicalBuildResult,
)
from vedagraph.lexical.components import COMPONENT_FILE
from vedagraph.lexical.morphology import (
    ANNOTATION_LAYER_ID,
    ANNOTATION_LICENSE,
    MORPHOLOGY_COMMIT_SHA,
    MORPHOLOGY_PARSER_VERSION,
    MORPHOLOGY_REPOSITORY_URL,
    MORPHOLOGY_SOURCE_ID,
    MorphologyArtifact,
)
from vedagraph.lexical.parallels import PARALLEL_POLICY_VERSION
from vedagraph.models.enums import LexicalPredicate
from vedagraph.models.lexical import LexicalManifest
from vedagraph.storage.jsonl import write_jsonl
from vedagraph.storage.manifest import file_sha256

ENTITY_REGISTRY_FILES = ("devatas.yaml", "rishis.yaml", "chandas.yaml", "anukramani_aliases.yaml")
LEXICAL_REGISTRY_FILES = (LEXICAL_ALIAS_FILE, COMPONENT_FILE)

PREDICATE_WHITELIST: tuple[LexicalPredicate, ...] = (
    LexicalPredicate.MENTIONS_ENTITY,
    LexicalPredicate.EXACT_PARALLEL_OF,
    LexicalPredicate.PARALLEL_TO,
    LexicalPredicate.HAS_COMPONENT,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        orjson.dumps(payload, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS) + b"\n"
    )


def write_lexical_layer(
    result: LexicalBuildResult,
    *,
    output_dir: Path,
    corpus_dir: Path,
    knowledge_dir: Path,
    artifacts: list[MorphologyArtifact],
    built_at: datetime,
    registry_root: Path = Path("data/registry"),
    version: str = LEXICAL_LAYER_VERSION,
) -> LexicalManifest:
    output_dir.mkdir(parents=True, exist_ok=True)
    generated: dict[Path, int] = {}

    files: dict[str, Sequence[BaseModel]] = {
        "tokens.jsonl": result.tokens,
        "lemmas.jsonl": result.lemmas,
        "lexical_aliases.jsonl": result.aliases,
        "lexical_alias_candidates.jsonl": result.alias_candidates,
        "mentions.jsonl": result.mentions,
        "ambiguous_mentions.jsonl": result.ambiguous,
        "devata_components.jsonl": result.components,
        "mantra_parallels.jsonl": result.parallels,
        "parallel_candidates.jsonl": result.parallel_candidates,
        "exact_parallel_groups.jsonl": result.exact_groups,
        "entity_co_occurrence.jsonl": result.co_occurrences,
        "qa_issues.jsonl": result.qa_issues,
    }
    for name, records in files.items():
        generated[output_dir / name] = write_jsonl(output_dir / name, records)

    _write_json(output_dir / "lexical_stats.json", result.stats.model_dump(mode="json"))
    generated[output_dir / "lexical_stats.json"] = 1

    _write_json(
        output_dir / "lexical_qa.json",
        {
            "qa_policy_version": LEXICAL_QA_POLICY_VERSION,
            "status": result.qa_status.value,
            "errors": sum(1 for issue in result.qa_issues if issue.severity.value == "ERROR"),
            "warnings": sum(1 for issue in result.qa_issues if issue.severity.value == "WARNING"),
            "checks": sorted({issue.check_id for issue in result.qa_issues}),
            "alignment": {
                "mantras_expected": result.alignment.mantras_expected,
                "mantras_with_morphology": result.alignment.mantras_with_morphology,
                "tokens": result.alignment.tokens,
                "unaligned_records": len(result.alignment.unaligned_records),
                "duplicate_token_keys": len(result.alignment.duplicate_token_keys),
                "passage_mismatches": len(result.alignment.passage_mismatches),
            },
            "morphology_parse": {
                "stanzas_seen": result.parse_report.stanzas_seen,
                "stanzas_with_annotation": result.parse_report.stanzas_with_annotation,
                "unparsable_stanza_ids": len(result.parse_report.unparsable_stanza_ids),
                "unparsable_token_ids": len(result.parse_report.unparsable_token_ids),
                "tokens_without_lemma": len(result.parse_report.tokens_without_lemma),
            },
            "parallel_engine": {
                "candidate_pairs_generated": result.parallel_report.candidate_pairs_generated,
                "oversized_buckets_skipped": result.parallel_report.oversized_buckets_skipped,
                "largest_bucket": result.parallel_report.largest_bucket,
                "exact_pairs_by_method": result.parallel_report.exact_pairs,
            },
        },
    )
    generated[output_dir / "lexical_qa.json"] = 1

    corpus_manifest_path = corpus_dir / "manifest.json"
    corpus_manifest = json.loads(corpus_manifest_path.read_text(encoding="utf-8"))
    knowledge_manifest_path = knowledge_dir / "manifest.json"
    knowledge_manifest = json.loads(knowledge_manifest_path.read_text(encoding="utf-8"))

    manifest = LexicalManifest(
        version=version,
        built_at=built_at,
        corpus_dataset_id=corpus_dir.name,
        corpus_version=str(corpus_manifest["version"]),
        corpus_manifest_sha256=file_sha256(corpus_manifest_path),
        corpus_passage_count=int(corpus_manifest["passage_count"]),
        knowledge_manifest_sha256=file_sha256(knowledge_manifest_path),
        knowledge_layer_version=str(knowledge_manifest["version"]),
        morphology_source_id=MORPHOLOGY_SOURCE_ID,
        morphology_repository_url=MORPHOLOGY_REPOSITORY_URL,
        morphology_commit_sha=MORPHOLOGY_COMMIT_SHA,
        morphology_annotation_layer_id=ANNOTATION_LAYER_ID,
        morphology_license=ANNOTATION_LICENSE,
        morphology_artifact_ids=sorted(item.artifact_id for item in artifacts),
        morphology_artifact_hashes={
            item.artifact_id: item.sha256
            for item in sorted(artifacts, key=lambda entry: entry.artifact_id)
        },
        morphology_snapshot_ids=sorted(item.snapshot_id for item in artifacts),
        entity_registry_hashes={
            name: file_sha256(registry_root / name) for name in sorted(ENTITY_REGISTRY_FILES)
        },
        lexical_registry_hashes={
            name: file_sha256(registry_root / name) for name in sorted(LEXICAL_REGISTRY_FILES)
        },
        canonical_text_version_id=CANONICAL_TEXT_VERSION_ID,
        morphology_parser_version=MORPHOLOGY_PARSER_VERSION,
        token_id_policy_version=TOKEN_ID_POLICY_VERSION,
        mention_policy_version=MENTION_POLICY_VERSION,
        parallel_policy_version=PARALLEL_POLICY_VERSION,
        component_mapping_sha256=file_sha256(registry_root / COMPONENT_FILE),
        predicate_whitelist=list(PREDICATE_WHITELIST),
        record_counts={
            path.name: count for path, count in sorted(generated.items(), key=lambda i: i[0].name)
        },
        qa_status=result.qa_status,
        generated_files=[
            {
                "path": path.relative_to(output_dir).as_posix(),
                "record_count": count,
                "sha256": file_sha256(path),
            }
            for path, count in sorted(generated.items(), key=lambda item: item[0].as_posix())
        ],
        software_version=__version__,
    )
    _write_json(output_dir / "manifest.json", manifest.model_dump(mode="json"))
    return manifest
