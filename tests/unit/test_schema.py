from vedagraph.models import Passage, SourceArtifact


def test_passage_json_schema_requires_identity_fields() -> None:
    schema = Passage.model_json_schema()
    required = set(schema["required"])
    assert {"entity_id", "canonical_key", "canonical_urn", "hierarchy"} <= required
    assert schema["additionalProperties"] is False


def test_source_artifact_schema_requires_exact_file_identity() -> None:
    required = set(SourceArtifact.model_json_schema()["required"])
    assert {"artifact_id", "source_id", "url", "filename", "rights_status"} <= required
