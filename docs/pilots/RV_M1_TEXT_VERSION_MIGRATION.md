# Migration: declaring a primary Sanskrit text version

Applied: 2026-09-04 to `rv_mandala_1_sample_v2` (5 Suktas, 111 mantras).

The sample was rebuilt after the primary-text decision to confirm that declaring a base
edition changes provenance and nothing else. It was **not** re-fetched and **not** extended;
the same pinned snapshots produced it.

## What changed in the build

`data/builds/rv_mandala_1.yaml` gained `primary_sanskrit` and six `parallel_sanskrit`
entries. `TextVersion` gained `text_role` and `text_version_id`, both populated from that
configuration rather than from parser code.

## Output diff, by file SHA-256

| File | Before | After | Verdict |
| --- | --- | --- | --- |
| `passages.jsonl` | `a9cfefb4…` | `a9cfefb4…` | unchanged |
| `citations.jsonl` | `b2bab5a0…` | `b2bab5a0…` | unchanged |
| `translations.jsonl` | `dff0aa56…` | `dff0aa56…` | unchanged |
| `traditional_metadata.jsonl` | `39389958…` | `39389958…` | unchanged |
| `discoveries.jsonl` | `cd7a65f8…` | `cd7a65f8…` | unchanged |
| `audio_recordings.jsonl` | `cb18b20d…` | `cb18b20d…` | unchanged |
| `qa_issues.jsonl` | `4ff4eac2…` | `4ff4eac2…` | unchanged |
| `works.jsonl` | `477cde9b…` | `477cde9b…` | unchanged |
| `source_assertions.jsonl` | `ec609701…` | `ec609701…` | unchanged |
| `text_versions.jsonl` | `4c36de38…` | changed | **intended** |
| `sources.jsonl` | `9835157b…` | changed | **intended** |
| `source_artifacts.jsonl` | `ae74e7f9…` | changed | **intended** |

## Verification

- **IDs unchanged.** All 111 `text_id` and `passage_id` values are identical, in the same
  order. Passage UUIDs are byte-identical.
- **Passage counts unchanged.** 5 Suktas, 111 mantras, 111 Sanskrit text versions.
- **Text unchanged.** Every `text_original` is identical.
- **Translations unchanged.** 111 Griffith translations, file byte-identical.
- **Metadata unchanged.** `traditional_metadata.jsonl` is byte-identical. The range parser
  wrote 15 candidate records to `data/derived/metadata_candidates/`, which is not canonical
  output and is not committed. Nothing was promoted.
- **Provenance updated.** `text_versions.jsonl` differs only by the two added fields:
  `text_role: PRIMARY_TEXT` and `text_version_id: GRETIL.RV.AUFRECHT`. No shared field
  changed value.
- **Registries updated.** `sources.jsonl` gained `VEDAWEB`; `source_artifacts.jsonl` gained
  the two pinned VedaWeb TEI artifacts and the repository-pinning fields.
- **QA unchanged.** 0 errors, 6 warnings, 1 informational finding — the same seven records
  as before.
- **Reproducible.** Two consecutive builds produce byte-identical JSONL and manifest.

## Not done in this migration

Full Mandala 1 ingestion. The sample was rebuilt to validate the change; the remaining 186
Suktas were not fetched. See [`STATUS.md`](../STATUS.md) for the readiness assessment and
the VHP constraint that bounds it.
