"""Export versioned JSON Schemas from the authoritative Pydantic models."""

import json
from pathlib import Path

from pydantic import BaseModel

from vedagraph.models import (
    AnukramaniStagingRecord,
    AudioRecording,
    AudioSegment,
    CorpusBuildConfig,
    KnowledgeAssertion,
    KnowledgeEntity,
    KnowledgeManifest,
    MetadataSourceAssertion,
    Passage,
    Source,
    SourceArtifact,
    SourceAssertion,
    SuktaDiscoveryRecord,
    TextVersion,
    TraditionalMetadataAssertion,
    Translation,
)
from vedagraph.models.lexical import (
    ComponentAssertion,
    LexicalAlias,
    LexicalManifest,
    MantraParallel,
    MentionAssertion,
    MorphologyToken,
)

SCHEMA_MODELS: dict[str, type[BaseModel]] = {
    "passage.schema.json": Passage,
    "text_version.schema.json": TextVersion,
    "translation.schema.json": Translation,
    "traditional_metadata.schema.json": TraditionalMetadataAssertion,
    "source.schema.json": Source,
    "source_artifact.schema.json": SourceArtifact,
    "source_assertion.schema.json": SourceAssertion,
    "audio_recording.schema.json": AudioRecording,
    "audio_segment.schema.json": AudioSegment,
    "sukta_discovery.schema.json": SuktaDiscoveryRecord,
    "corpus_build_config.schema.json": CorpusBuildConfig,
    "anukramani_staging.schema.json": AnukramaniStagingRecord,
    "metadata_source_assertion.schema.json": MetadataSourceAssertion,
    "knowledge_entity.schema.json": KnowledgeEntity,
    "knowledge_assertion.schema.json": KnowledgeAssertion,
    "knowledge_manifest.schema.json": KnowledgeManifest,
    "morphology_token.schema.json": MorphologyToken,
    "lexical_alias.schema.json": LexicalAlias,
    "mention_assertion.schema.json": MentionAssertion,
    "mantra_parallel.schema.json": MantraParallel,
    "component_assertion.schema.json": ComponentAssertion,
    "lexical_manifest.schema.json": LexicalManifest,
}


def export_schemas(directory: Path = Path("schemas")) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for filename, model in SCHEMA_MODELS.items():
        path = directory / filename
        path.write_text(
            json.dumps(model.model_json_schema(), ensure_ascii=False, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        paths.append(path)
    return paths
