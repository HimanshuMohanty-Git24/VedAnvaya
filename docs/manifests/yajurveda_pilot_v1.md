# Manifest — `yajurveda_pilot_v1`

Vājasaneyi Saṃhitā (Śukla Yajurveda, Mādhyandina) representative pilot.
Machine-readable manifest: `data/canonical/yajurveda_pilot_v1/manifest.json`.

| Field | Value |
|---|---|
| dataset | VedaGraph Canonical Corpus |
| version | `0.1.0-pilot.1` |
| work | `VG:WORK:YV:VSM` |
| built_at | `2026-09-07T00:00:00+05:30` (**pinned in config**, so rebuilds do not drift) |
| passage_count | 140 (4 adhyāya + 136 mantra) |
| qa_status | `PASSED_WITH_WARNINGS` |
| software_git_commit | `4da5bd789ceb1f55651598320f5331c5c92675d4` |
| build_config_sha256 | `d76229c16b564204502b32cc737f7c6fdcca955feaa82d0822bc96828d83cfda` |
| generated_content_sha256 | `04250c32be0f134d45721928b69b5ed913327482491a064a76e30a4a9a920028` |
| reconciliation_policy_version | `yajurveda-pilot-v1` |
| comparison_version | `text-compare-v1` |
| rights_summary | `WIKISOURCE_SA: CC_BY_SA` (read from the registry, not asserted here) |

## Parser versions

| Component | Version |
|---|---|
| `wikisource-sa-vsm` | `wikisource-sa-vsm-v1` |
| `wikisource-sa-vsm-apparatus` | `wikisource-sa-vsm-apparatus-v1` |
| builder | `yajurveda-pilot-v1` |

## Generated files

| Records | sha256 (first 16) | File |
|--:|---|---|
| 140 | `4ace14c13fed2a4d` | `passages.jsonl` |
| 271 | `9a535a8a64979ef2` | `text_versions.jsonl` |
| 203 | `97a933f023d33492` | `traditional_metadata.jsonl` |
| 153 | `8d59bf70c3bd3b45` | `citations.jsonl` |
| 135 | `2801820cf470434b` | `text_comparisons.jsonl` |
| 6 | (see below) | `source_assertions.jsonl` — 4 revision records + **2 `NEEDS_REVIEW` editorial interventions** |
| 2 | (registry-sourced) | `source_artifacts.jsonl` |
| 1 | (registry-sourced) | `sources.jsonl` |
| 0 | `e3b0c44298fc1c14` | `translations.jsonl` — **empty on purpose** |
| 0 | `e3b0c44298fc1c14` | `audio_recordings.jsonl` — **empty on purpose** |
| 0 | `e3b0c44298fc1c14` | `audio_segments.jsonl` — **empty on purpose** |

The three empty files are written, not omitted, so their emptiness is an asserted fact with
a hash rather than a missing artifact. `translations` is empty because no lawful structured
translation of the Mādhyandina VS exists; `audio_*` because no Śukla-Mādhyandina audio is
mirrorable. Both are named blockers in `docs/reports/YAJURVEDA_SOURCE_RESEARCH.md`.

## Source artifacts

**Loaded from `data/registry/source_artifacts.yaml`, not constructed by this build.**

| artifact_id | Rights | Notes |
|---|---|---|
| `WIKISOURCE_SA.YV.VSM.SAMHITA.DEVANAGARI` | `CC_BY_SA` | Nirṇaya Sāgara Press, Bombay, Śaka 1850 = CE 1929, ed. Vāsudeva Śarma Paṇaśīkara, with Uvaṭa + Mahīdhara |
| `WIKISOURCE_SA.YV.VSM.RISHISUCI` | `CC_BY_SA` | Edition-supplied per-mantra ṛṣi index |

Source is `WIKISOURCE_SA`, also loaded from the registry. Earlier revisions of this pilot
emitted locally-invented ids (`WIKISOURCE.SA.VSM.*`, source `WIKISOURCE_SA_VSM`) and thereby
asserted provenance — and rights — under identifiers the rights authority had never declared.
Agent F's G11 gate caught it. The builder now calls `load_sources()` /
`load_source_artifacts()` and **raises** on an unknown id rather than constructing one.

### Registry checksum verification

The build re-checks each registry checksum against the bytes it actually read, and names the
page a checksum belongs to rather than accepting "matches some snapshot":

| artifact | finding |
|---|---|
| `…SAMHITA.DEVANAGARI` | `NO_CHECKSUM_DECLARED` — **correct and intended.** This is a 40-page artifact, so no single checksum is meaningful; byte verification is per snapshot in `raw_snapshot_hashes`. Agent E removed the previously recorded `cb13ec2e…`, which was the hash of the **preface page** — a real snapshot of the wrong thing, found by this build's scope check. |
| `…RISHISUCI` | **`OK_MATCHES_ITS_OWN_SCOPE`** — Agent E pinned `2151af3f…`, and this build independently confirms it resolves to `शुक्लयजुर्वेदः/ऋषिसूची` rather than merely hashing correctly. |

G11 status: **0 ERROR, 1 WARNING** (was FAILED with 2 ERRORs). The one warning is the
*justified* absence on the multi-page artifact, per Agent E's registry convention rule 2 —
which rejected an ordered-concatenation hash because it would silently encode a page
ordering and normalization choice nothing else in the pipeline declares.

The preface page is now registered in its own right as `WIKISOURCE_SA.YV.VSM.PREFACE`,
where `cb13ec2e…` **is** in scope. It is load-bearing: the entire edition-identity claim for
Śukla Yajurveda rests on that one page.

### Unregistered text_version_ids — one level below G11

`data/registry/text_versions.yaml` declares 7 descriptors, **all Rigvedic**. So the two
text_version_ids this build uses are not registered:
`WIKISOURCE_SA.YV.VSM.ACCENTED` and `WIKISOURCE_SA.YV.VSM.UNACCENTED`.

`TextVersionDescriptor` carries rights and permitted role, so an unregistered
text_version_id is an unadjudicated rights claim in exactly the way an unregistered
artifact_id is — and **G11 does not check this level**. The ids are therefore *proposed*,
reported by the build (`report.unregistered_text_versions`) and printed by
`scripts/build_yajurveda_pilot.py`, with registration requested from Agent E rather than
assumed. The build does not fail on them because the descriptors do not exist to load yet.

## Input snapshots

All under `data/raw/wikisource_sa/2026-09-07/`. Each is one MediaWiki
`action=query&prop=revisions&rvslots=main` response, so it carries `pageid`, `revid` and
revision timestamp alongside the wikitext — the snapshot is self-dating. Content-addressed
filenames make re-fetching idempotent, and each sha256 is re-verified on load; the build
aborts on drift.

| Scope | snapshot sha256 |
|---|---|
| Adhyāya 1 | `bc41fb4829dc53152c0091a2a1dbd7905cb93aeb428dd6169f4e3189726d27b1` |
| Adhyāya 16 | `32b097a018f3b1b180f9a9a4d190b05195cf161f8ddec27581ca3f1431a8ffe0` |
| Adhyāya 31 | `9f4124f52611c8a9310858681b1643ef4403128cb3a1d43d888cfc5085865be4` |
| Adhyāya 40 | `c3d67b62d30aeec443f3f1fd4b69b3f3616782684852175f14debbaa3b610061` |
| Ṛṣi index | `2151af3f369e21c2792b0bc7d43efce3c2242e568ad1c5725fe40fd35c743caa` |

Also snapshotted and retained as evidence, though not consumed by this build: all 40
adhyāya pages (the full-corpus counts were computed from them), the root TOC, the
Sarvānukramaṇī, and the preface page carrying the printed edition's title page
(`cb13ec2ee19ba0279bfaee40077647336a78c34e3607f7aaad64d91a3e86e1bf`).

## Comparison distribution

`UNCLASSIFIED` 116 · `SANDHI_OR_SEGMENTATION` 13 · `ACCENT_ONLY` 6, over 135 comparisons of
the accented layer against the unaccented one. These are post-fix numbers: Agent F added
Devanagari nasal and visarga folding to `normalize/unicode.py` in response to this pilot's
diagnosis, which moved 16 comparisons out of `UNCLASSIFIED`. `comparison_version` remains
`text-compare-v1` because `compare/text.py` itself is unchanged — only the normalization it
calls improved, so this hash will shift again if `normalize/` changes. That is intended:
the manifest is meant to detect exactly that.

## Work-level count reconciliation is now IN the release

Agent F's G13 manifest-vs-raw check surfaced a real gap: the headline figure of **1,975
mantras over 40 adhyāyas** was computed by the adapter but recorded only in a report, so
the release could not verify its own most important number. The build now reads **all 40**
adhyāya snapshots (`reconciliation_sections` in the config, deliberately separate from the
4-adhyāya `selected_sections`) and emits `structure_reconciliation.jsonl` — 41 work-scoped
`SourceAssertion` records, one per adhyāya plus a work total:

```
adhyaya_count 40 · total_mantras 1975 · sum_of_accented_layer 1958
sum_of_unaccented_layer 1836 · adhyayas_with_gaps 0
```

Those 40 snapshots are now listed in the manifest, so `source_snapshot_ids` went from 5 to
**41** and the count is reproducible from the release.

Six snapshots under `data/raw/wikisource_sa/` remain unlisted, and the breakdown matters:
**three are mine and legitimately not consumed** by this build (root TOC, Sarvānukramaṇī,
preface — held as evidence), and **three are Agent B's Sāmaveda fetches**, which land in
the same directory because Samaveda also uses source id `WIKISOURCE_SA`. So a raw
directory is genuinely shared across agents and G13 can never reach parity — which is
exactly why F made it a WARNING rather than an ERROR.

## Known deviations

* **Not schema-validated against `corpus_build_config.schema.json`.** `CorpusBuildConfig`
  requires `mandala` and `selected_suktas`; VSM has neither. Field names mirror the incoming
  `WorkBuildConfig`. Disclosed, not accidental.
* **No `SuktaDiscoveryRecord` emitted.** That model requires `sukta_number` and
  `mandala_number`; VSM has no sūkta level. Migrating to `SectionDiscoveryRecord` is pending.
* **`component_manifest_hashes` and `build_config_hashes` are empty** — this is a single-unit
  build with no components.
