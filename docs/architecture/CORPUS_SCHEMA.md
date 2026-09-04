# Corpus schema

Pydantic v2 models in `src/vedagraph/models` are authoritative. JSON Schemas in `schemas/` are
generated views and are refreshed with `vedagraph schema export`.

## Canonical files

| File | Model | Purpose |
| --- | --- | --- |
| `works.jsonl` | `Work` | recension and hierarchy registry |
| `passages.jsonl` | `Passage` | structural and textual identities |
| `text_versions.jsonl` | `TextVersion` | immutable source strings and normalized forms |
| `translations.jsonl` | `Translation` | translator/edition-specific translations |
| `traditional_metadata.jsonl` | `TraditionalMetadataAssertion` | scoped Rishi, Devata, and Chandas claims |
| `sources.jsonl` | `Source` | source provenance and rights |
| `source_artifacts.jsonl` | `SourceArtifact` | exact file/transformation and edition lineage |
| `source_assertions.jsonl` | `SourceAssertion` | generic, potentially conflicting claims |
| `discoveries.jsonl` | `SuktaDiscoveryRecord` | source-specific structural discovery |
| `citations.jsonl` | `Citation` | canonical and alternate labels |
| `audio_recordings.jsonl` | `AudioRecording` | recording or external-media identity |
| `audio_segments.jsonl` | `AudioSegment` | optional passage timestamps |
| `qa_issues.jsonl` | `QAIssue` | release validation findings |

No passage embeds translations, audio, flat metadata, or interpretations. References use UUIDs;
human keys remain available for review and diffs. Every persisted model rejects unknown fields and
carries `schema_version`.

Source-specific staging persists independently as GRETIL text, Wikisource translation/revision,
VHP metadata, discovery, and source-assertion JSONL. `TranslationAlignment` distinguishes exact
mantra, hymn, range, and uncertain alignment. Translation records may retain MediaWiki page and
revision provenance.

Traditional metadata scope is explicit: whole passage, one mantra, or inclusive mantra range.
Range applicability is never inferred merely because several deities appear in a hymn heading.

Audio may be locally stored, object-stored, or an external reference. Unknown rights default to
no download/rehosting. Sukta-level recordings are valid without fabricated mantra timestamps.
