"""Write the deterministic knowledge layer to disk and pin it to its corpus.

Output is byte-stable: records are sorted before writing, JSON keys are sorted, and the
build timestamp is injected rather than read from the clock. A knowledge manifest always
names the exact corpus manifest, source artifacts, registries and policy versions it was
produced from.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import orjson

from vedagraph import __version__
from vedagraph.ingest.adapters.anukramani import PARSER_VERSION
from vedagraph.knowledge.build import (
    KNOWLEDGE_LAYER_VERSION,
    PREDICATE_WHITELIST,
    QA_POLICY_VERSION,
    KnowledgeBuildResult,
)
from vedagraph.knowledge.normalize import NORMALIZATION_POLICY_VERSION
from vedagraph.knowledge.registry import ALIAS_FILE, REGISTRY_FILES, RESOLUTION_POLICY_VERSION
from vedagraph.models.enums import KnowledgeEntityType
from vedagraph.models.knowledge import KnowledgeManifest, KnowledgeStats
from vedagraph.storage.jsonl import write_jsonl
from vedagraph.storage.manifest import file_sha256

ENTITY_FILES = {
    KnowledgeEntityType.RISHI: ("entities_rishis.jsonl", "unresolved_rishis.jsonl"),
    KnowledgeEntityType.DEVATA: ("entities_devatas.jsonl", "unresolved_devatas.jsonl"),
    KnowledgeEntityType.CHANDAS: ("entities_chandas.jsonl", "unresolved_chandas.jsonl"),
}

SOURCE_REPOSITORY_URL = "https://github.com/mahesh-ak/WSC2023"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        orjson.dumps(payload, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS) + b"\n"
    )


def write_knowledge_layer(
    result: KnowledgeBuildResult,
    stats: KnowledgeStats,
    *,
    output_dir: Path,
    corpus_dir: Path,
    artifacts: list[dict[str, object]],
    built_at: datetime,
    registry_root: Path = Path("data/registry"),
    version: str = KNOWLEDGE_LAYER_VERSION,
) -> KnowledgeManifest:
    output_dir.mkdir(parents=True, exist_ok=True)
    generated: dict[Path, int] = {}

    generated[output_dir / "anukramani_staging.jsonl"] = write_jsonl(
        output_dir / "anukramani_staging.jsonl", result.staging
    )
    generated[output_dir / "metadata_source_assertions.jsonl"] = write_jsonl(
        output_dir / "metadata_source_assertions.jsonl", result.source_assertions
    )
    generated[output_dir / "knowledge_assertions.jsonl"] = write_jsonl(
        output_dir / "knowledge_assertions.jsonl", result.assertions
    )
    for entity_type, (entity_file, unresolved_file) in ENTITY_FILES.items():
        generated[output_dir / entity_file] = write_jsonl(
            output_dir / entity_file, result.entities[entity_type]
        )
        generated[output_dir / unresolved_file] = write_jsonl(
            output_dir / unresolved_file,
            [label for label in result.unresolved if label.entity_type is entity_type],
        )
    generated[output_dir / "qa_issues.jsonl"] = write_jsonl(
        output_dir / "qa_issues.jsonl", result.qa_issues
    )

    _write_json(
        output_dir / "knowledge_qa.json",
        {
            "qa_policy_version": QA_POLICY_VERSION,
            "status": result.qa_status.value,
            "errors": sum(1 for issue in result.qa_issues if issue.severity.value == "ERROR"),
            "warnings": sum(1 for issue in result.qa_issues if issue.severity.value == "WARNING"),
            "checks": sorted({issue.check_id for issue in result.qa_issues}),
            "alignment": {
                "dataset_rows": result.alignment.dataset_rows,
                "aligned_rows": result.alignment.aligned_rows,
                "unaligned_rows": sorted(result.alignment.unaligned_rows),
                "duplicate_rows": sorted(result.alignment.duplicate_rows),
                "verse_count_mismatches": sorted(result.alignment.verse_count_mismatches),
                "missing_corpus_suktas": sorted(result.alignment.missing_corpus_suktas),
            },
        },
    )
    generated[output_dir / "knowledge_qa.json"] = 1
    _write_json(output_dir / "knowledge_stats.json", stats.model_dump(mode="json"))
    generated[output_dir / "knowledge_stats.json"] = 1

    corpus_manifest_path = corpus_dir / "manifest.json"
    corpus_manifest = json.loads(corpus_manifest_path.read_text(encoding="utf-8"))
    manifest = KnowledgeManifest(
        version=version,
        built_at=built_at,
        corpus_dataset_id=corpus_dir.name,
        corpus_version=str(corpus_manifest["version"]),
        corpus_manifest_sha256=file_sha256(corpus_manifest_path),
        corpus_passage_count=int(corpus_manifest["passage_count"]),
        source_id="WSC2023",
        source_repository_url=SOURCE_REPOSITORY_URL,
        source_commit_sha=_commit_sha(artifacts),
        source_artifact_ids=sorted(str(item["artifact_id"]) for item in artifacts),
        source_artifact_hashes={
            str(item["artifact_id"]): str(item["sha256"])
            for item in sorted(artifacts, key=lambda entry: str(entry["artifact_id"]))
        },
        snapshot_ids=sorted(str(item["snapshot_id"]) for item in artifacts),
        registry_hashes={
            name: file_sha256(registry_root / name)
            for name in sorted([*REGISTRY_FILES.values(), ALIAS_FILE])
        },
        normalization_policy_version=NORMALIZATION_POLICY_VERSION,
        resolution_policy_version=RESOLUTION_POLICY_VERSION,
        parser_version=PARSER_VERSION,
        qa_policy_version=QA_POLICY_VERSION,
        predicate_whitelist=list(PREDICATE_WHITELIST),
        assertion_counts={
            "metadata_source_assertions": len(result.source_assertions),
            "knowledge_assertions": len(result.assertions),
            **{
                f"knowledge_assertions_{predicate.value}": sum(
                    1 for item in result.assertions if item.predicate is predicate
                )
                for predicate in PREDICATE_WHITELIST
            },
        },
        unresolved_counts={
            entity_type.value: sum(
                1 for label in result.unresolved if label.entity_type is entity_type
            )
            for entity_type in KnowledgeEntityType
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


def _commit_sha(artifacts: list[dict[str, object]]) -> str:
    shas = {str(item["url"]).split("/WSC2023/")[1].split("/")[0] for item in artifacts}
    if len(shas) != 1:
        raise ValueError("pinned artifacts must all come from one commit")
    return shas.pop()
