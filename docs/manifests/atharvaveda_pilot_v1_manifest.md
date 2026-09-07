# Atharvaveda Pilot v1 — Release Manifest

Machine-readable manifest: `data/canonical/atharvaveda_pilot_v1/manifest.json`  
Machine-readable whole-artifact structure: `docs/manifests/atharvaveda_pilot_structure_v1.json`  
Build config: `data/builds/atharvaveda_pilot_v1.yaml`  
Source evidence: `data/source_registry/atharvaveda_sources.yaml`

- **work_id** `VG:WORK:AV:SAU`
- **version** `0.1.0-avs-pilot.1`
- **built_at** `2026-09-07T04:37:06.617010Z` (pinned to newest snapshot retrieval, not wall clock)
- **passage_count (mantras)** 153
- **qa_status** `PASSED_WITH_WARNINGS`
- **software_git_commit** `4da5bd789ceb1f55651598320f5331c5c92675d4`
- **build_config_sha256** `8e50b12401eb5b28b3095d430a9e302fb7620f4a0e444da8b6cede52605bd376`
- **parser_versions** {'GRETIL': 'gretil-avs-saunaka-legacy-html-v1'}
- **comparison_version** `text-compare-v1`
- **rights_summary** {'GRETIL.AV.SAUNAKA.ACCENTED.HTML': 'REFERENCE_ONLY', 'GRETIL.AV.SAUNAKA.UNACCENTED.HTML': 'REFERENCE_ONLY'}

## Pinned source snapshots (immutable, hashed)

| artifact_id | sha256 | snapshot_id |
|---|---|---|
| `GRETIL.AV.SAUNAKA.ACCENTED.HTML` | `cd89bd1e29e6158d7c3c7bcb607b8e4eed4c7556c8c2027dec039f56736adddb` | `GRETIL_AVS:cd89bd1e29e6158d7c3c7bcb607b8e4eed4c7556c8c2027dec039f56736adddb` |
| `GRETIL.AV.SAUNAKA.UNACCENTED.HTML` | `7e3f74f313d1b4348bf9e1f60a80e03bb72709994b85585a4f854a51bf57272c` | `GRETIL_AVS:7e3f74f313d1b4348bf9e1f60a80e03bb72709994b85585a4f854a51bf57272c` |

Translation-layer snapshots (VedaWeb, fetched through PoliteFetcher):

- `VEDAWEB_AVS:0a922cbe83e8ecf8e83b27210d167c20b98d9aee237ccdee14d2d5b3909f0bc5`
- `VEDAWEB_AVS:19591257ab941154c9e6febf33b2d87c02eb8248bd6f36e6dfd15313017cda1d`
- `VEDAWEB_AVS:37b0d1ec7715d61c10744c877ee57ffa0c5a750d88804b0cec73273aeb045fb1`
- ... 23 snapshots in total; full list in `data/staged/atharvaveda_translation_stage.json`

## Generated files

| path | records | sha256 |
|---|---:|---|
| `audio_recordings.jsonl` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `audio_segments.jsonl` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `citations.jsonl` | 157 | `c8fafc3d85a3b17a95e15540afaecea2a76cee91cb9feb6b14b892327d0ff890` |
| `passages.jsonl` | 174 | `cf2d847d07df51647a8f3ec99de4c9b28a93d5f6fd0c6dbfb3e9e199009c60b4` |
| `qa_issues.jsonl` | 2 | `a46d076f2919e6e49636ba66e6a94b5a0547af55a00592424a5b3dae159e7551` |
| `source_artifacts.jsonl` | 3 | `0b9a9c8027449238f3f1bd4101897b630bf810126c25d0cefe9f65209e168c87` |
| `source_assertions.jsonl` | 177 | `e52cc02b96ea5f274f52fd73ed8265deb3ff4393d483d46653c165e6d4b54dab` |
| `sources.jsonl` | 2 | `81160791d28c556bf84b2f77ca03d1fa3dc1d3f09b8a9bc172b6e3fb6f62a2ef` |
| `text_comparisons.jsonl` | 153 | `1e8d1444d1a88374009d1ff0d07f006ee43a8b021edbd03c431392e875d1e397` |
| `text_versions.jsonl` | 459 | `afbdcb617c0f3828e1791a0c04d58f814e021114330573b8cdfaf8fe4391170d` |
| `traditional_metadata.jsonl` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `translations.jsonl` | 115 | `43d0d0cc900cba4905441b17224965d6d838008aeb1b1121a946f095b5f7d81c` |
| `works.jsonl` | 1 | `17e7ca77a3bf6672c09e105d06ec162686e564dcfbac3ea73d1a9deba52dfe40` |
| `manifest.json` | — | `0af8568cc8c5627e0912c652af20b35edf1caa733376ec182a1de13830faa2a6` |

## Whole-artifact computed structure (all 20 kāṇḍas, not just the sample)

- parsed units: **5843**
- distinct (kāṇḍa, sūkta, mantra) triples: **5839**
- pada-level tokens: **11395**
- kāṇḍas: **20** · sūktas: **731**
- anuvāka `{N}` markers: **220** (present in only 11 of 20 kāṇḍas)
- single-pada units: **702**
- units carrying an alternate (Vishva Bandhu) citation: **261**
- units with no in-text verse marker: **46**
- label/marker disagreements: **13**
- locator collisions: **4** — AVS 12.5.53, AVS 13.4.26, AVS 20.96.22, AVS 9.6.48
- accented artifact: 5843/5843 units accent-positive
- unaccented artifact: 0/5843 units accent-positive
- artifact-to-artifact locator alignment identical: **True**

| kāṇḍa | sūktas | units | padas | single-pada | anuvāka marks | alt citations |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 35 | 153 | 307 | 0 | 0 | 0 |
| 2 | 36 | 206 | 378 | 42 | 0 | 0 |
| 3 | 31 | 230 | 472 | 0 | 4 | 0 |
| 4 | 40 | 324 | 658 | 0 | 0 | 0 |
| 5 | 31 | 376 | 741 | 35 | 0 | 0 |
| 6 | 142 | 454 | 909 | 6 | 0 | 0 |
| 7 | 118 | 286 | 575 | 1 | 0 | 0 |
| 8 | 10 | 259 | 529 | 16 | 29 | 0 |
| 9 | 10 | 302 | 528 | 88 | 28 | 0 |
| 10 | 10 | 350 | 746 | 2 | 34 | 0 |
| 11 | 10 | 313 | 688 | 39 | 30 | 214 |
| 12 | 5 | 304 | 545 | 78 | 30 | 0 |
| 13 | 4 | 188 | 345 | 56 | 20 | 0 |
| 14 | 2 | 139 | 280 | 0 | 14 | 0 |
| 15 | 18 | 141 | 218 | 98 | 0 | 47 |
| 16 | 9 | 93 | 147 | 66 | 0 | 0 |
| 17 | 1 | 30 | 76 | 0 | 3 | 0 |
| 18 | 4 | 283 | 547 | 21 | 28 | 0 |
| 19 | 72 | 453 | 862 | 69 | 0 | 0 |
| 20 | 143 | 959 | 1844 | 85 | 0 | 0 |

## Sample actually built

| sūkta | mantras | Whitney translations |
|---|---:|---:|
| AVS 1.1 | 4 | 4 |
| AVS 4.1 | 7 | 7 |
| AVS 6.1 | 3 | 3 |
| AVS 7.6 | 4 | 4 |
| AVS 8.5 | 22 | 22 |
| AVS 13.4 | 55 | 56 |
| AVS 15.2 | 4 | 4 |
| AVS 16.1 | 13 | 13 |
| AVS 19.1 | 3 | 3 |
| AVS 20.96 | 24 | 0 |
| AVS 20.127 | 14 | 0 |
| **total** | **153** | **116** |

## Record counts by type

| collection | records |
|---|---:|
| `audio_recordings.jsonl` | 0 |
| `audio_segments.jsonl` | 0 |
| `citations.jsonl` | 157 |
| `passages.jsonl` | 174 |
| `qa_issues.jsonl` | 2 |
| `source_artifacts.jsonl` | 3 |
| `source_assertions.jsonl` | 177 |
| `sources.jsonl` | 2 |
| `text_comparisons.jsonl` | 153 |
| `text_versions.jsonl` | 459 |
| `traditional_metadata.jsonl` | 0 |
| `translations.jsonl` | 115 |
| `works.jsonl` | 1 |

## Rights posture of this release

| layer | rights_status | basis |
|---|---|---|
| all 459 Sanskrit `TextVersion` records | `REFERENCE_ONLY` | the GRETIL artifact's own words: "THIS GRETIL TEXT FILE IS FOR REFERENCE PURPOSES ONLY! COPYRIGHT AND TERMS OF USAGE AS FOR SOURCE FILE." |
| 115 `Translation` records | `PUBLIC_DOMAIN` | Whitney & Lanman, Harvard Oriental Series 7–8, 1905; US public domain; corroborated by English Wikisource `{{PD/US|1941}}` |
| 0 `TraditionalMetadataAssertion` records | — | no sourced machine-readable AVŚ metadata adjudicated; absence recorded as `TRADITIONAL_METADATA_UNAVAILABLE` |
| 0 `AudioRecording` records | — | nothing mirrored; every AVŚ audio source found is `PERMISSION_REQUIRED` |

**This release must not be redistributed as-is.** The Sanskrit layer is `REFERENCE_ONLY`
pending written permission from the TITUS Project.
