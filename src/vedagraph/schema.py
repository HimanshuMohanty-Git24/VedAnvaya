"""Export versioned JSON Schemas from the authoritative Pydantic models."""

import json
from pathlib import Path

from pydantic import BaseModel

from vedagraph.models import (
    AnukramaniStagingRecord,
    AudioRecording,
    AudioSegment,
    Citation,
    CorpusBuildConfig,
    KnowledgeAssertion,
    KnowledgeEntity,
    KnowledgeManifest,
    MetadataSourceAssertion,
    Passage,
    QAIssue,
    SectionDiscoveryRecord,
    Source,
    SourceArtifact,
    SourceAssertion,
    SuktaDiscoveryRecord,
    TextVersion,
    TraditionalMetadataAssertion,
    Translation,
    Work,
    WorkBuildConfig,
)
from vedagraph.models.lexical import (
    ComponentAssertion,
    LexicalAlias,
    LexicalManifest,
    MantraParallel,
    MentionAssertion,
    MorphologyToken,
)
from vedagraph.models.normalization import (
    ExplicitnessReview,
    SemanticAssertionSignature,
    SemanticNormalizationManifest,
    SemanticObjectCandidate,
    StructuredSemanticAssertion,
    StructuredSemanticComparison,
)
from vedagraph.models.semantic import (
    AdjudicationRecord,
    EvidencePacket,
    GoldAnnotation,
    GoldEntityAnnotation,
    GoldEvidenceReference,
    GoldReviewMetadata,
    OntologyGap,
    SemanticAssertionCandidate,
    SemanticEntityCandidate,
    SemanticRunManifest,
    SemanticValidationResult,
)
from vedagraph.models.silver import (
    SilverBenchmarkManifest,
    SilverComparison,
    SilverEvidenceReference,
    SilverSemanticAnnotation,
    SilverSemanticAssertion,
    SilverSemanticEntity,
)

SCHEMA_MODELS: dict[str, type[BaseModel]] = {
    "work.schema.json": Work,
    "passage.schema.json": Passage,
    "citation.schema.json": Citation,
    "qa_issue.schema.json": QAIssue,
    "text_version.schema.json": TextVersion,
    "translation.schema.json": Translation,
    "traditional_metadata.schema.json": TraditionalMetadataAssertion,
    "source.schema.json": Source,
    "source_artifact.schema.json": SourceArtifact,
    "source_assertion.schema.json": SourceAssertion,
    "audio_recording.schema.json": AudioRecording,
    "audio_segment.schema.json": AudioSegment,
    "sukta_discovery.schema.json": SuktaDiscoveryRecord,
    "section_discovery.schema.json": SectionDiscoveryRecord,
    "corpus_build_config.schema.json": CorpusBuildConfig,
    "work_build_config.schema.json": WorkBuildConfig,
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
    "semantic_evidence_packet.schema.json": EvidencePacket,
    "semantic_entity_candidate.schema.json": SemanticEntityCandidate,
    "semantic_assertion_candidate.schema.json": SemanticAssertionCandidate,
    "semantic_validation_result.schema.json": SemanticValidationResult,
    "semantic_gold_annotation.schema.json": GoldAnnotation,
    "semantic_gold_evidence_reference.schema.json": GoldEvidenceReference,
    "semantic_gold_entity_annotation.schema.json": GoldEntityAnnotation,
    "semantic_gold_review_metadata.schema.json": GoldReviewMetadata,
    "semantic_ontology_gap.schema.json": OntologyGap,
    "semantic_gold_adjudication.schema.json": AdjudicationRecord,
    "semantic_run_manifest.schema.json": SemanticRunManifest,
    "silver_semantic_evidence_reference.schema.json": SilverEvidenceReference,
    "silver_semantic_entity.schema.json": SilverSemanticEntity,
    "silver_semantic_assertion.schema.json": SilverSemanticAssertion,
    "silver_semantic_annotation.schema.json": SilverSemanticAnnotation,
    "silver_semantic_comparison.schema.json": SilverComparison,
    "silver_semantic_manifest.schema.json": SilverBenchmarkManifest,
    "semantic_object_candidate.schema.json": SemanticObjectCandidate,
    "semantic_assertion_signature.schema.json": SemanticAssertionSignature,
    "structured_semantic_assertion.schema.json": StructuredSemanticAssertion,
    "structured_semantic_comparison.schema.json": StructuredSemanticComparison,
    "semantic_explicitness_review.schema.json": ExplicitnessReview,
    # DELIBERATELY NOT EXPORTED: "semantic_extraction_v3.schema.json".
    # That file is a sealed execution input whose sha256 is pinned in
    # data/semantic/vedagraph-rigveda-semantic-claude-opus5-v3.2-448-new-v1/input_freeze.json.
    # It is hand-narrowed and is NOT a faithful export of SemanticExtractionV3: the model's
    # Explicitness enum admits INTERPRETIVE, which the sealed schema must not contain and
    # which normalization.py refuses at runtime instead. Listing it here caused
    # `vedagraph schema export` to overwrite a frozen artifact and break the input freeze.
    # Regenerating it requires an explicit re-seal decision by the semantic-layer owner.
    "semantic_normalization_manifest.schema.json": SemanticNormalizationManifest,
}


def export_schemas(directory: Path = Path("schemas")) -> list[Path]:
    """Regenerate JSON Schemas, rewriting only files whose content actually changed.

    Two properties matter here, and both were learned the hard way.

    First, line endings are preserved per file. ``Path.write_text`` translates newlines
    to CRLF on Windows, and this repository's committed schemas are genuinely mixed --
    some LF, some CRLF, with no ``.gitattributes`` and ``core.autocrlf=false``. A plain
    ``write_text`` therefore rewrote every LF schema on every export. Several of those
    files have their sha256 pinned in the semantic layer's freeze records, so a pure
    line-ending rewrite broke frozen-hash assertions while changing no content at all --
    the most confusing possible failure, because the schema stayed byte-identical modulo
    the line endings.

    Second, a file whose rendered content equals what is already on disk is not touched,
    so ``schema export`` is idempotent at the byte level and safe to run at any time.
    """
    directory.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for filename, model in SCHEMA_MODELS.items():
        path = directory / filename
        body = (
            json.dumps(model.model_json_schema(), ensure_ascii=False, indent=2, sort_keys=True)
            + "\n"
        )
        existing = path.read_bytes() if path.exists() else b""
        newline = "\r\n" if b"\r\n" in existing else "\n"
        rendered = body.replace("\n", newline).encode("utf-8")
        if rendered != existing:
            path.write_bytes(rendered)
        paths.append(path)
    return paths
