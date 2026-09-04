# Project status

Updated: 2026-09-04 (Rigveda deterministic knowledge layer)

## DONE

- Git repository, Python 3.12/uv package, src layout, task runner, environment example, and CI.
- Typed work/source/rights registries and fixed UUIDv5 identity protocol.
- Pydantic models and generated JSON Schemas for canonical records.
- Immutable content-addressed raw snapshots with polite cached HTTP retrieval.
- Source adapter boundary plus VHP RV 1.1, GRETIL TEI, Wikisource, and VedaWeb TEI parsing.
- Lossless NFC/comparison normalization and replaceable Devanagari-to-IAST adapter.
- Deterministic validated JSONL, release manifest, field-specific reconciliation hooks, and QA.
- Bounded live RV 1.1 pilot: 9 mantras, 9 Sanskrit text versions, 9 translations, 3 traditional
  metadata assertions, and 1 external-only audio/video reference; QA passed.
- Offline tests, Ruff, mypy strict mode, CLI smoke test, and manual JSONL inspection.
- Source, schema, rights, architecture, and ADR documentation.
- File-level source-artifact registry with the exact GRETIL Rigveda TEI checksum, edition lineage,
  contributors, transformation, citation system, and verbatim CC BY-NC-SA 4.0 statement.
- Policy-driven TEI editorial selection. The inspected file's 175,308 standalone `orig` accent
  nodes are preserved under `ORIGINAL`; fixture `choice/orig/reg` and `sic/corr` variants never
  concatenate.
- Deterministic Mandala 1 discovery: GRETIL and VHP each expose Suktas 1–191 and agree exactly;
  GRETIL contains 2,006 Mandala 1 and 10,552 full-Rigveda `lg` records. The pinned VedaWeb Book 1
  TEI independently contains 191 hymns and 2,006 stanzas, a third agreeing witness.
- Versioned `rv_mandala_1_sample_v2` build config and bounded Suktas 1, 22, 50, 164, and 191:
  5 Suktas, 111 mantras, 111 accented GRETIL text versions, 111 Griffith translations, reviewed
  source assertions, VHP traditional metadata references, and 5 external-only media references.
- Persistent source-specific staging and source-assertion JSONL, conflict inspection, explicit
  structural/textual statistics, stronger hierarchy QA, and generated data-driven Markdown report.
- MediaWiki API page ID, revision ID, revision timestamp, page title, canonical URL, and explicit
  source-numbered alignment for both current poem markup and legacy numbered preformatted pages.
- Reproducible config-driven builds with injected time, explicit ordering, config/snapshot/artifact/
  parser/reconciliation lineage, deterministic IDs, and generated-file hashes.
- **VedaWeb registered at artifact and version level**, pinned to commit
  `d3eb8af7324338161520d2d35eae8f7e985a19a5` with per-file SHA-256, Git blob SHA and byte size.
  `SourceArtifact` now refuses a repository-hosted artifact that names no commit.
- **Per-version rights**, not per-host: `data/registry/text_versions.yaml` records seven Sanskrit
  text versions with `normalized_rights`, `license_uri`, `verbatim_license`, preserved
  `upstream_rights_notes`, and source-specific restrictions. The VedaWeb Book 1 TEI mixes
  CC BY 4.0 and CC BY-NC-SA 4.0 layers, so its file-level status is deliberately `UNKNOWN`.
- **Accent-aware comparison stack**: five named comparison surfaces, a documented IAST/ISO 15919
  transcription fold, and cluster-level accent stripping that distinguishes a tone mark from a
  letter built out of the same combining mark (`ś`, `ḻ`, accented vocalic `r̥`).
- **Deterministic text-version comparator** with a strict classification ladder,
  `vedagraph text compare` and `vedagraph text compare-sample`, a version-controlled stratified
  240-mantra Mandala 1 sample, and a generated report.
- **Primary Sanskrit text selected** and expressed in build configuration, with a test proving
  passage identity cannot depend on it. `TextVersion` carries `text_role` and `text_version_id`.
- **Fail-closed traditional-metadata range parser** with candidate scopes including half-verse and
  pāda spans, `vedagraph metadata review-ranges`, and a human-review report in two forms: a
  committed copy that withholds VHP source strings, and a full local copy under `data/derived/`.
  Nothing is promoted.

## COMPLETE RIGVEDA ŚĀKALA CORPUS

Built as ten independently gated Mandala units, then assembled into `rigveda_full_v1`.

| Unit | External expectation | Discovered (GRETIL) | Canonical |
| --- | ---: | ---: | ---: |
| Mandalas | 10 | 10 | 10 |
| Suktas | 1,028 | 1,028 | 1,028 |
| Mantras | 10,552 | 10,552 | 10,552 |

- **Primary Sanskrit `GRETIL.RV.AUFRECHT`: 10,552/10,552 (100%).**
- **Parallel Sanskrit `VEDAWEB.AUFRECHT`: 10,552/10,552 (100%).**
- **Griffith 1896: 10,344 exact mantra alignments (98.03%)**, 158 uncertain, 52 missing. No gap is
  filled from another translator.
- Primary/parallel comparison over all 10,552 pairs: 9,746 `ACCENT_ONLY`, 35
  `SANDHI_OR_SEGMENTATION`, 771 `UNCLASSIFIED`. **Zero structural variants, zero missing readings.**
- QA: **842 WARNINGs, 0 ERRORs.** Mandala 1's 164 residuals reproduce exactly and are frozen by a
  fixture.
- Reproducibility: rebuilding all ten Mandalas and re-assembling reproduces every canonical file
  byte-for-byte, manifest included.
- Lineage: 50 stratified mantras (5 per Mandala) traced passage → primary/parallel `TextVersion` →
  registered `SourceArtifact` → snapshot checksum, and passage → `Translation` → pinned Wikisource
  revision. 50/50 passed.
- Performance: full stage + build + gate of ten Mandalas plus assembly ≈100s, ~45 MB canonical
  JSONL. Each Mandala reads its own VedaWeb book file, so no source index was needed.
- Manifest `vedagraph-rigveda-shakala-1.0.0-rc1` pins 1,257 snapshots, 13 source artifacts, ten
  build-config hashes, ten component-manifest hashes, and the Griffith revision-manifest hash.

### Source anomalies found and fixed generically

- **Valakhilya placement.** Griffith prints RV 8.49–8.59 at the end of his Book 8 as Hymns 93–103;
  Aufrecht numbers them inline. Without this mapping, 220 Mandala 8 mantras carried the *wrong*
  English text — a misalignment, not a gap. The rule lives in `vedagraph.editions` as an
  edition-order fact with a permutation test, not as a parser conditional.
- **A third Wikisource page layout.** The oldest transcriptions (e.g. RV 5.65) carry stanzas as
  plain body text, with neither `.ws-poem` markup nor `.verse pre`. One numbering grammar now
  covers all three layouts; this recovered RV 5.65 entirely.
- **Genuine source gaps stay gaps.** RV 1.179 (Griffith's appendix), RV 10.61.5–9 and
  RV 10.86.16–17 (untranslated in the source), and single-stanza transcription slips in RV 5.44,
  5.55, 10.48 and 10.132 are reported as WARNINGs and never fabricated or renumbered.

## RIGVEDA DETERMINISTIC KNOWLEDGE LAYER

The first knowledge-engineering layer over the finished corpus. Traditional Ṛṣi, Devatā and
Chandas metadata, from the commit-pinned digital Anukramaṇī of Akavarapu and Bhattacharya
(2023). No Neo4j, no embeddings, no GraphRAG, no LLM, and none of that source repository's
classifier or word-vector artifacts.

- **Source pinned at artifact level.** `WSC2023` registered as a source; ten
  `WSC2023.RV.ANUKRAMANI.M*` artifacts pinned by commit `05b5987d…`, per-file SHA-256, Git
  blob SHA and byte size. Repository-level Apache-2.0 recorded after inspecting the exact
  files; the data files carry no artifact-level licence of their own. Evidence:
  [`RIGVEDA_ANUKRAMANI_SOURCE.md`](architecture/RIGVEDA_ANUKRAMANI_SOURCE.md).
- **Alignment is total and independently checked.** All 1,028 dataset rows align to a
  canonical Sūkta; 0 unaligned, 0 duplicate mappings, 0 out-of-range citations, and every
  row's declared verse count equals the corpus mantra count. The dataset is therefore a
  fourth independent witness to the 1,028 / 10,552 shape.
- **Staged, never shortcut.** 1,028 staging rows → 4,577 scoped source assertions →
  31,650 deterministic mantra→entity edges. Every edge names its source assertion, pinned
  artifact and snapshot; no edge exists without one.
- **Canonical entity registries**, committed and pinned: 367 Ṛṣis, 214 Devatās, 34 Chandas.
  `entity_key` is data, not a recomputed value. Entity URNs live under
  `urn:vedagraph:entity:`; the passage UUID namespace is untouched.
- **Coverage.** `HAS_DEVATA` 10,552/10,552 (100%); `HAS_RISHI` 10,534 (99.83%);
  `HAS_CHANDAS` 10,518 (99.68%). Multiple assignments are modelled as multiple edges:
  31 mantras carry two Ṛṣis, 6 two Devatās, 5 two Chandas.
- **Nothing is merged on similarity.** Six spelling variants are united only by evidenced
  entries in `anukramani_aliases.yaml`. `aśvaḥ` and `aśvāḥ` collide under the ASCII fold and
  stay two entities with collision-broken keys. Fuzzy comparison produces review candidates
  and nothing else.
- **Composites preserved.** Nine hyphen-joined Devatā labels keep their surface parts
  recorded and are not decomposed; `mitrāvaruṇau` and `indrāgnī` stay single entities, as
  the source authors intended. `HAS_COMPONENT` is a documented future phase, unimplemented.
- **Assignment is not mention.** `HAS_DEVATA: agniḥ` records a traditional assignment, not
  an occurrence of the word in the Sanskrit. `MENTIONS_ENTITY` belongs to the later
  deterministic lexical phase.
- **QA `PASSED_WITH_WARNINGS`: 0 errors, 4 warnings.** Two source anomalies found by
  inspection and reported rather than repaired — RV 8.31 carries no seer field (18 mantras,
  the whole `HAS_RISHI` gap) and RV 5.52 has a descending meter span `7-5`. 34 mantras carry
  no chandas because nine hymns' meter scopes do not cover every verse.
- **Reproducible.** Two builds from the same corpus, artifacts and registries produce
  byte-identical output including the manifest; the registry generator is idempotent too.
  Full build ≈2 s.
- **Manifest `vedagraph-rigveda-knowledge-deterministic-1.0.0-rc1`** pins the corpus manifest
  SHA-256 and version, the source commit, ten artifact hashes, ten snapshot ids, four registry
  file hashes, four policy versions and every output file hash.
- **Cross-checks recorded, never resolved.** VHP's five reviewed Sūktas: 3 `AGREE_EXACT`,
  4 `LABEL_DIFFERENCE` (a naming-order convention, compared on a declared stem-token surface
  and not merged), 2 `SOURCE_CONFLICT` at RV 1.191. Neither source overrides the other.
  VedaWeb's 1,028 hymn addressees are surveyed as a different concept and never ingested as
  `HAS_DEVATA`.
- Reports: [`RIGVEDA_DETERMINISTIC_KNOWLEDGE_BUILD.md`](reports/RIGVEDA_DETERMINISTIC_KNOWLEDGE_BUILD.md),
  [`RIGVEDA_DEVATA_REGISTRY.md`](reports/RIGVEDA_DEVATA_REGISTRY.md),
  [`RIGVEDA_RISHI_REGISTRY.md`](reports/RIGVEDA_RISHI_REGISTRY.md),
  [`RIGVEDA_CHANDAS_REGISTRY.md`](reports/RIGVEDA_CHANDAS_REGISTRY.md),
  [`RIGVEDA_METADATA_SOURCE_COMPARISON.md`](reports/RIGVEDA_METADATA_SOURCE_COMPARISON.md).
- Decisions: [ADR-011](decisions/ADR-011-deterministic-knowledge-layer.md),
  [ADR-012](decisions/ADR-012-entity-resolution-is-registry-data.md).

### Knowledge layer readiness

**RIGVEDA_DETERMINISTIC_KNOWLEDGE_READY_WITH_LIMITATIONS**

| Condition | State |
| --- | --- |
| Anukramaṇī artifacts pinned and rights documented | PASS |
| Alignment to 10,552 canonical mantras | PASS — 1,028/1,028 rows, 0 unaligned |
| Source-assertion layer separate from resolution | PASS |
| Entity identity stable and namespace-safe | PASS |
| No fuzzy auto-merge | PASS |
| Composite labels preserved | PASS |
| Multiple Ṛṣi/Devatā per mantra | PASS |
| Provenance on every edge | PASS |
| Deterministic byte-identical rebuild | PASS |
| No LLM, embedding, or classifier | PASS |
| Structural errors | PASS — 0 QA errors |
| Metadata coverage | PARTIAL — 18 mantras without a Ṛṣi, 34 without Chandas, from source gaps |
| Composite decomposition | DEFERRED by design |
| VHP disagreement | RECORDED, awaiting human review |

## IN PROGRESS

- Cross-script comparison of `VEDAWEB.EICHLER` against the Latin versions, which needs a reviewed
  transliteration step before a Devanagari display derivative can be justified.
- Human review of the 15 candidate traditional-metadata scopes; 9 are parser-clean, 6 are the
  known deferred strings and none is safe to promote unreviewed.

## BLOCKED

- VHP redistribution and bulk ingestion require written permission. This bounds traditional
  metadata coverage for full Mandala 1, not Sanskrit or translation coverage.
- Samaveda Kauthuma canonical identity awaits edition-level hierarchy/citation research.
- VedSearch content licensing, translator attribution, API stability, and numbering remain unknown.
- GRETIL reuse must be approved per file; the reviewed Rigveda TEI is CC BY-NC-SA 4.0.

## RESOLVED PREVIOUS SESSION

- **The Rigveda Sanskrit base is no longer unresolved.** `GRETIL.RV.AUFRECHT` is the primary
  displayed Saṃhitā. `VEDAWEB.VNH` is a metrically restored parallel, `VEDAWEB.PADAPATHA` is
  Padapāṭha, and the remaining VedaWeb layers hold parallel, comparison and annotation roles.
  Evidence: [`RIGVEDA_BASE_EDITION.md`](architecture/RIGVEDA_BASE_EDITION.md).
- **Rights for the primary source are explicitly documented**, per version, with upstream notices
  preserved verbatim. No primary-source component is in an `UNKNOWN` rights state.

## RESOLVED IN THE MANDALA 1 SESSION

- **All 191 Suktas / 2,006 mantras built and canonical**, from `data/builds/rv_mandala_1_full_v1.yaml`.
  GRETIL discovery, VHP discovery, and canonical ingestion all agree on 2,006; the
  `expected_vs_canonical_mantra_count` QA check would fail the build (ERROR) if they ever
  diverged, per Sukta. Old 5-Sukta sample passage identities (key/URN/UUID/parent/citation)
  are provably stable when the build scope grows — see
  `test_passage_identity_is_stable_when_the_build_scope_grows`.
- **`VEDAWEB.AUFRECHT` is now a real parallel-text layer in the canonical build**, not just a
  documented role: every mantra with a GRETIL primary reading also carries a VedaWeb `AUFRECHT`
  `TextVersion` on the *same* passage. The other five VedaWeb layers stay documented-but-unbuilt
  in `candidate_text_versions`.
- **New QA policy `PRIMARY_PARALLEL_TEXT_DIVERGENCE`**: every mantra's primary/parallel pair is
  classified; accent/Unicode/orthographic equivalence passes silently, a residual difference is a
  WARNING, and a missing/structurally different reading would be an ERROR. 164/2,006 mantras carry
  a WARNING-level residual divergence (matches the 240-sample report's proportion); zero ERRORs.
- **Griffith translation ingested for all 191 Suktas**: 1,968/2,006 mantras exact mantra-level
  alignment. One Sukta (RV 1.179) has no parseable stanza markup on its pinned revision; a handful
  more have internally consistent but incomplete numbering. Both are QA WARNINGs
  (`translation_page_parse_failed`, `translation_alignment_uncertain`,
  `translation_coverage_incomplete`), never fabricated. Fixed a real Wikisource-adapter gap along
  the way: the legacy `.verse pre` numbering regex required a trailing period that several Suktas'
  pages (1.3–1.7) don't have.
- **Traditional metadata and audio stay exactly the 5-Sukta reviewed sample**, per policy — no new
  bulk VHP ingestion this session.
- **Reports**: `docs/reports/RIGVEDA_MANDALA_1_BUILD.md` (full build summary),
  `rv_m1_full_text_comparison_report.md` (full-corpus primary/parallel classification, 2,006
  aligned mantras), `rv_m1_translation_coverage_report.md`, `rv_m1_coverage_matrix_summary.md`
  (aggregate of the gitignored 191-row per-Sukta matrix). All generated from real canonical output.
- **Reproducibility**: two independent full builds produced byte-identical canonical JSONL.
- **20-mantra stratified lineage spot-check** (`scripts/verify_lineage.py`) traces
  passage → primary `TextVersion` → registered `SourceArtifact` → raw snapshot checksum, and
  passage → `Translation` → Wikisource page/revision; 20/20 passed.

## RIGVEDA CORPUS READINESS

**RIGVEDA_CORPUS_READY_WITH_LIMITATIONS**

| Condition | State |
| --- | --- |
| Identity | PASS |
| Structure (10 / 1,028 / 10,552) | PASS — expected = discovered = canonical |
| Deterministic parser | PASS |
| Sanskrit primary-text strategy | PASS |
| Parallel Sanskrit built into canonical output | PASS |
| Source version pinned | PASS |
| Text provenance | PASS |
| Rights status explicitly documented | PASS |
| Translation alignment (all 1,028 Suktas) | PASS |
| Metadata range handling | REVIEW-ONLY, without loss |
| Reproducible build | PASS — byte-identical full-corpus rebuilds |
| No structural errors | PASS — 0 QA errors across 10,552 mantras |
| Build performance | PASS — full corpus ≈100s, no O(n²) blowup observed |

Limitations that make this `READY_WITH_LIMITATIONS` rather than `READY`:

1. **Traditional metadata cannot reach full coverage.** VHP is the only source for received
   Rishi/Devata/Chandas, and its bulk ingestion is prohibited without written permission. The
   corpus carries Sanskrit and translation for all 1,028 Suktas but traditional metadata for only
   the 5 already snapshotted — 0.49% of Suktas. This is an explicit phase boundary, not an
   oversight.
2. **Range-scoped metadata stays review-only.** Candidates exist for all 15 strings; none is
   promoted. Nothing is lost: the raw strings remain source assertions and QA still warns.
3. **Śākala identification remains a structural inference** in both redistributable sources.
4. **806 of 10,552 mantras** show a residual primary/parallel divergence beyond notation, recorded
   as QA WARNINGs, not resolved. Mandala 1's 164 are frozen as a regression baseline.
5. **Griffith coverage is 98.03%, honestly reported.** 52 mantras have no English at all and 158
   sit in Suktas whose source numbering could not be confirmed. Wilson is not substituted.
6. **Media remains reference-only.** Five external audio/video references from the Mandala 1
   sample; nothing downloaded, rehosted, or newly aligned.

## NEXT

- **Deterministic lexical and cross-mantra knowledge**: literal entity-name occurrence
  (`MENTIONS_ENTITY`) via canonical alias matching, exact and near mantra parallels,
  source-backed Ṛṣi family relationships, reviewed Devatā composition (`HAS_COMPONENT`), and
  deterministic graph statistics. Only after that: semantic extraction, then Neo4j, then GraphRAG.
- Have a reader review the three entity registries, starting with the suspected-duplicate and
  composite tables in the generated registry reports, and the RV 1.191 VHP source conflicts.
- Have a reader work through `rv_m1_metadata_range_review.md` and mark the promotable candidates.
- Decide whether to seek VHP permission or to accept partial traditional-metadata coverage.
- Consider a periodic re-check of RV 1.179 on Wikisource in case the page markup changes; revision
  pinning means this build will not silently pick up a fix.
