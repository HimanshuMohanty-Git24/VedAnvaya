"""Corpus manifest construction from generated artifacts."""

from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from vedagraph.models import CorpusManifest, ManifestFile
from vedagraph.models.enums import QAStatus


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(
    *,
    root: Path,
    version: str,
    works: list[str],
    passage_count: int,
    source_snapshot_ids: list[str],
    generated: dict[Path, int],
    qa_status: QAStatus,
    built_at: datetime | None = None,
    source_artifact_ids: list[str] | None = None,
    raw_snapshot_hashes: dict[str, str] | None = None,
    build_config_sha256: str | None = None,
    parser_versions: dict[str, str] | None = None,
    reconciliation_policy_version: str | None = None,
    software_git_commit: str | None = None,
    software_version: str | None = None,
    qa_policy_version: str | None = None,
    comparison_version: str | None = None,
    component_manifest_hashes: dict[str, str] | None = None,
    build_config_hashes: dict[str, str] | None = None,
    revision_manifest_sha256: str | None = None,
    generated_content_sha256: str | None = None,
    rights_summary: dict[str, str] | None = None,
) -> CorpusManifest:
    files = [
        ManifestFile(
            path=path.relative_to(root).as_posix(),
            record_count=count,
            sha256=file_sha256(path),
        )
        for path, count in sorted(generated.items(), key=lambda item: item[0].as_posix())
    ]
    return CorpusManifest(
        version=version,
        built_at=built_at or datetime.now(UTC),
        works=sorted(works),
        passage_count=passage_count,
        source_snapshot_ids=sorted(source_snapshot_ids),
        source_artifact_ids=sorted(source_artifact_ids or []),
        raw_snapshot_hashes=dict(sorted((raw_snapshot_hashes or {}).items())),
        build_config_sha256=build_config_sha256,
        parser_versions=dict(sorted((parser_versions or {}).items())),
        reconciliation_policy_version=reconciliation_policy_version,
        software_git_commit=software_git_commit,
        software_version=software_version,
        qa_policy_version=qa_policy_version,
        comparison_version=comparison_version,
        component_manifest_hashes=dict(sorted((component_manifest_hashes or {}).items())),
        build_config_hashes=dict(sorted((build_config_hashes or {}).items())),
        revision_manifest_sha256=revision_manifest_sha256,
        generated_content_sha256=generated_content_sha256,
        rights_summary=dict(sorted((rights_summary or {}).items())),
        generated_files=files,
        record_counts={item.path: item.record_count for item in files},
        qa_status=qa_status,
    )
