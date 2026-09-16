# Project status

Updated: 2026-09-16 (translation bulk integration)

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

## RIGVEDA DETERMINISTIC LEXICAL & CROSS-MANTRA LAYER

The second knowledge-engineering layer. It answers a different question from the first:
not *what the tradition assigns to a mantra*, but *what words the mantra actually
contains*. Still no Neo4j, no embeddings, no GraphRAG, no LLM.

- **Morphology source selected and pinned: `PRIMARY_MORPHOLOGY_SELECTED`.** The University
  of Zurich morphosyntactic annotation (`VEDAWEB.ZURICH`), CC BY 4.0, at the already-pinned
  commit `d3eb8af7…`. It is an annotation layer inside book TEI artifacts this repository
  had already registered and hashed, so no new source, licence or fetch was introduced.
  Surveyed against `sanskrit-texts/rigveda`, which is not rejected as a source and remains
  the recommended route for a future verb-argument layer. Evidence:
  [`RIGVEDA_MORPHOLOGY_SOURCE.md`](architecture/RIGVEDA_MORPHOLOGY_SOURCE.md),
  [`RIGVEDA_MORPHOLOGY_DECISION.md`](architecture/RIGVEDA_MORPHOLOGY_DECISION.md).
- **Token layer is total and structurally aligned.** 164,758 tokens across
  **10,552/10,552 mantras (100%)**; 0 tokens without a lemma, 0 unaligned records, 0
  duplicate token keys, 0 passage mismatches, 0 unparsable ids. Alignment reads the
  stanza's own `xml:id`, so nothing is placed by comparing text and no edition mapping
  table was needed.
- **Token identity names the annotation layer; mantra identity does not.**
  `VG:TOKEN:VEDAWEB-ZURICH:RV:SAK:M01:S001:V001:PA:T001`, UUIDv5 from a canonical URN.
  Adopting a second morphology source adds new token ids and changes no mantra id.
- **Canonical Sanskrit untouched.** `GRETIL.RV.AUFRECHT` remains primary; the annotation's
  reading is preserved separately as `surface_form`.
- **8,961 `MENTIONS_ENTITY` edges** over 6,560 mantras, 9,364 token occurrences — **all of
  them `LEMMA_ID_EXACT`**, matched on the annotation's own Grassmann-linked lemma
  identifiers. No substring, surface or fuzzy match created a single edge.
- **Precision measured independently: 0.01%** detectable false positives (1 off-gender of
  9,364), using the annotation's grammatical gender, which played no part in choosing the
  aliases. Stratified review sample of 228 rows.
  [`RIGVEDA_LEXICAL_MENTION_REVIEW.md`](reports/RIGVEDA_LEXICAL_MENTION_REVIEW.md).
- **`DO_NOT_MATCH` is why precision holds.** 22 evidenced suppressions stop Anukramaṇī
  Devatā labels that are ordinary nouns — `kaḥ` (interrogative pronoun, 468 occurrences),
  `rathaḥ` ("chariot", 471), `hariḥ` (271) — from fabricating ~2,000 false mentions.
- **Ambiguity fails closed.** 711 tokens matched a registered alias and produced **no
  edge**, reported rather than guessed: `sárasvant-` (Sarasvatī/Sarasvant share one stem),
  `áp-`, `yamá-`, `mr̥tyú-`, `vená-`, `dadhikrā́-`.
- **Assignment is not mention, and the numbers prove it.** `pavamānaḥ somaḥ` is assigned to
  1,087 mantras and mentioned in 0; `viśvedevāḥ` 805 and 0; `mitraḥ` 10 and 320; `pṛthivī`
  4 and 319. Three counts are computed separately and the stats file carries a written
  warning that none of them means "the most used god".
- **28 `HAS_COMPONENT` edges**, provenance `HUMAN_REVIEWED`, from 14 `ACCEPTED` rows in
  `devata_components.yaml`. `viśvedevāḥ`, `ādityāḥ` and `marutaḥ` are recorded `REJECTED`:
  a group deity is not the set of its members and a plural ending is not componenthood.
  `dyāvāpṛthivyau` is held because no canonical Dyaus entity exists.
- **Ṛṣi family structure: `NO SUFFICIENT DETERMINISTIC SOURCE FOUND`.** The pinned
  Anukramaṇī has one seer field and no family, gotra or ancestor column; the lineage in
  `vaiśvāmitro madhucchandāḥ` is name grammar, not data. No genealogy edges created. The
  same finding scopes mentions to Devatā only.
  [`RIGVEDA_RISHI_STRUCTURE_FINDINGS.md`](architecture/RIGVEDA_RISHI_STRUCTURE_FINDINGS.md).
- **256 exact parallel pairs** in 389 groups across five separately recorded representation
  levels, largest group 14 mantras (the Viśvāmitra refrain spanning Mandalas 3 and 10),
  28 cross-Mandala groups. `LEMMA_SEQUENCE_EXACT` (250) is *below* `TOKEN_EXACT` (252)
  because GRETIL and the Lubotsky-based annotation genuinely disagree on two pairs —
  visible only because the levels are never collapsed.
- **No O(n²) pass.** MinHash banding scored 148,092 pairs, **0.27%** of all 55,687,476.
  Recall was measured, not assumed: brute-forcing all 613,278 Mandala 9 pairs, the banding
  recovered 3/3 policy-accepted and 74/74 candidate-tier pairs. 0 buckets skipped.
- **69 accepted `PARALLEL_TO`**, 792 candidates kept for review. Thresholds were set from
  the observed distribution, require every metric to clear, and exclude short mantras.
  [`RIGVEDA_PARALLEL_REVIEW.md`](reports/RIGVEDA_PARALLEL_REVIEW.md).
- **279 co-occurrence pairs** with explicit `unit: MANTRA` and method. No `RELATED_TO` or
  `CO_OCCURS_WITH` edge derived from them.
- **Reproducible and byte-identical**, asserted by a test that rebuilds the whole layer and
  compares every output hash. Full build 176 s: morphology parse 38 s, mentions 6 s,
  parallels 130 s.
- **Manifest `vedagraph-rigveda-knowledge-deterministic-lexical-1.0.0-rc1`** pins the corpus
  manifest, the knowledge manifest, the morphology commit and ten artifact hashes, the
  entity and lexical registry hashes, the component mapping hash, four policy versions and
  every output file hash.
- QA: **0 errors, 0 warnings**; one `INFO` recording 11 deliberately unreviewed aliases.
- Reports: [`RIGVEDA_DETERMINISTIC_LEXICAL_BUILD.md`](reports/RIGVEDA_DETERMINISTIC_LEXICAL_BUILD.md).
  Policy: [`RIGVEDA_LEXICAL_MENTION_POLICY.md`](architecture/RIGVEDA_LEXICAL_MENTION_POLICY.md).
  Decision: [ADR-013](decisions/ADR-013-lexical-mention-is-not-traditional-assignment.md).

### Lexical layer readiness

**RIGVEDA_DETERMINISTIC_LEXICAL_READY_WITH_LIMITATIONS**

| Condition | State |
| --- | --- |
| Morphology source selected, pinned, rights documented | PASS |
| Alignment to 10,552 canonical mantras | PASS — 10,552/10,552, 0 unaligned |
| Token ids deterministic and stable | PASS |
| Canonical Sanskrit unmodified | PASS |
| No substring matching | PASS — all edges `LEMMA_ID_EXACT` |
| No fuzzy automatic resolution | PASS — candidates only |
| Mention precision | PASS — 0.01% detectable false positives |
| Ambiguity fails closed | PASS — 711 tokens, 0 edges |
| `HAS_COMPONENT` reviewed-only | PASS |
| Exact parallels, canonical pair ordering | PASS |
| Parallel engine sub-quadratic with measured recall | PASS — 0.27% of pairs, 100% recall on M9 |
| Assignment vs mention kept separate | PASS |
| Deterministic byte-identical rebuild | PASS |
| No LLM, embedding, or classifier | PASS |
| Structural errors | PASS — 0 QA errors |
| Mention coverage | PARTIAL — 6,560/10,552 mantras; 40 aliases of 214 Devatās |
| Sarasvatī mentions | DEFERRED — needs feature-conditioned matching |
| Ṛṣi lexical mentions | DEFERRED — no deterministic source for label decomposition |
| Ṛṣi family / genealogy edges | NOT IMPLEMENTED — no sufficient source |
| Pāda-level parallels | DEFERRED by design; schema permits, not implemented |

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

---

# SEMANTIC CANDIDATE LAYER

Deterministic checkpoint this layer is built on: **`98be4d0`**
(`Rigveda deterministic lexical and cross-mantra knowledge layer v1`). The three
deterministic layers were verified clean at that commit — ruff, mypy strict, 254 tests,
byte-identical lexical rebuild — before any semantic work began, and none of them is
written to by anything in this section.

Status: **`RIGVEDA_SEMANTIC_PILOT_COMPLETE_AWAITING_HUMAN_GOLD`** — the 508-mantra
Codex-direct pilot completed; full-corpus extraction remains unauthorized.

Decision: [ADR-014](decisions/ADR-014-llm-output-is-candidate-only.md).
Reports: [RIGVEDA_SEMANTIC_PILOT.md](reports/RIGVEDA_SEMANTIC_PILOT.md),
[RIGVEDA_SEMANTIC_PILOT_CODEX_LUNA.md](reports/RIGVEDA_SEMANTIC_PILOT_CODEX_LUNA.md),
[RIGVEDA_SEMANTIC_ONTOLOGY.md](reports/RIGVEDA_SEMANTIC_ONTOLOGY.md),
[RIGVEDA_SEMANTIC_EVAL.md](reports/RIGVEDA_SEMANTIC_EVAL.md),
[RIGVEDA_SEMANTIC_COST.md](reports/RIGVEDA_SEMANTIC_COST.md).

## Lexical hardening, policy v2

The v1 audit found 32 detectable false-positive occurrences. Every class a deterministic
feature can separate is now excluded by a registry rule:

| | v1 | v2 |
|---|---:|---:|
| mention assertions | 8,961 | 9,000 |
| token occurrences | 9,322 | 9,364 |
| mantras with a mention | 6,531 | 6,560 |
| accepted aliases | 38 | 40 |
| tokens left ambiguous | 786 | 711 |
| **detectable off-gender occurrences** | **32** | **1** |
| **detectable false-positive rate** | **0.34%** | **0.01%** |

Two new rules, both properties of the annotation record and neither contextual:

- **Lemma identity is required, always.** A shared Grassmann lemma id is necessary but not
  sufficient: `índratama-` and `tákṣya-` are filed under the base word's id. Five occurrences
  removed, two of which the gender audit could never have found.
- **An alias may declare morphology constraints.** `allowed_pos` / `allowed_gender` /
  `allowed_number` / `allowed_case` / `forbidden_features`, enforced fail-closed. 28
  occurrences removed; **75 recovered**, because `sárasvant-` splits 70 F / 5 M and now
  reaches Sarasvatī and Sarasvant as separate entities instead of producing nothing.

One off-gender occurrence remains, kept deliberately: RV 10.93.6 `mitrā́váruṇau` is tagged
neuter dual and there is no neuter appellative for it to be, so gender supplies no
discriminant. It is an annotation gender-tag anomaly, recorded in the registry notes.
The 23 `sūryā́-` occurrences were removed from Sūrya but **not** reassigned: which entity
they belong to is a registry merge question, held as a `NEEDS_REVIEW` alias producing no
edges so the gap stays visible.

## Semantic pipeline

| | value |
|---|---|
| pilot mantras selected | 508 of 10,552 (deterministic, hash-ordered, all 10 Maṇḍalas) |
| gold subset selected | 120 |
| **gold subset annotated** | **0** |
| **Codex-direct extractions run** | **508** |
| **candidate assertions** | **425**, all `NEEDS_REVIEW` |
| **no-claim mantras** | **224** |
| **validation rejected** | **0** |
| **auto-accepted** | **0** |
| semantic node types | 17 |
| predicates allowed | 14 (7 LOW, 7 MEDIUM, 0 HIGH) |
| predicates refused by name | 5, each with a recorded reason |
| **predicates unlocked for auto-acceptance** | **0** |
| semantic entities in the registry | 0 — nothing is seeded |
| offline tests | 323 passed (2 API/live deselected) |

## Remaining gate

1. **The gold subset is unannotated.** 120 rows marked `UNANNOTATED` in
   `data/gold/rigveda_semantic_gold_v1.jsonl`. It must be written by a person — see
   [RIGVEDA_SEMANTIC_GOLD_PROTOCOL.md](architecture/RIGVEDA_SEMANTIC_GOLD_PROTOCOL.md).
   An LLM-authored gold set would measure agreement between two model passes, which is
   not precision and is worse than no measurement because it looks like one.

Until this is resolved, `unlocked_predicates` is empty and every clean candidate routes
to review. Full-corpus extraction is not authorised.

## Direct-run cost

The pilot made **0 API calls** and incurred **$0 direct API cost**. No API cost or
full-corpus projection is reported for this run.

---

# GRAPH ENRICHMENT V1

Built on **`fc6076a`** (`feat: add the Neo4j graph projection layer for all four Vedas`).

Status: **`VEDAGRAPH_GRAPH_ENRICHMENT_V1_READY`**.
Report: [GRAPH_ENRICHMENT_V1.md](reports/GRAPH_ENRICHMENT_V1.md).
Adversarial QA: [GRAPH_ENRICHMENT_V1_ADVERSARIAL_QA.md](reports/GRAPH_ENRICHMENT_V1_ADVERSARIAL_QA.md).

The graph is now a discovery graph rather than a corpus graph: 100,584 nodes and 212,336
relationships, up from 94,753 and 134,065.

| layer | result |
|---|---|
| cross-Veda identical pairs | 1,538 (750 EXACT_PARALLEL_OF, 788 VARIANT_OF) |
| cross-Veda near parallels | 3,049 |
| directed reuse (SV from RV) | 1,684 |
| Formula nodes / occurrences | 4,825 / 22,686; 236 formulas in all four Vedas |
| Concept nodes / assertions | 89 / 47,542 |
| semantic candidates | 736, all LLM_EXTRACTED / CANDIDATE |
| QAIssue nodes | 915 (RV 842, SV 39, YV 25, AV 9) |

## Graph backlog, closed

- **The two colliding `translation_id`s** were an upstream Wikisource typo: the Griffith
  pages for RV 1.91 and RV 5.44 each print one verse number twice. Corrected by an overlay
  in `data/registry/upstream_corrections.yaml` applied at projection time, because
  `data/canonical/rigveda_full_v1/translations.jsonl` is inside the sealed semantic freeze.
  The live graph now holds all 17,283 translations, and RV 1.91.18 and RV 5.44.14 have
  English for the first time.
- **neo4j stays in `infra/requirements-graph.txt`.** Re-verified empirically this session:
  adding it to `pyproject.toml` fails the freeze guard test.
- **QA issues are projected** for all four Vedas, not the Atharvaveda alone.

## What is NOT resolved

- The 736 semantic candidates are candidates. None may be accepted without human review.
- The concept ontology has measured gaps — Prajāpati, Bhaga, the Vasus, sleep, marriage,
  fear, Aśvamedha — enumerated with citations in the report.
- 1,103 of 4,825 formulas are strict substrings of another surviving formula.
- The avagraha residual in `vedagraph.normalize` needs a notation-aware fold.
- The Rigveda semantic V3.2 layer is untouched and remains sealed and blocked on human gold.

## NEXT

`NEXT_PROJECT_PHASE = FASTAPI_SEARCH_AND_GRAPH_API`. Every enrichment edge already carries
the full provenance envelope the API needs to answer "why are these connected?" from the
edge alone.

## Translation bulk integration (2026-09-16)

1,132 `Translation` nodes and 1,132 `HAS_TRANSLATION` edges imported from the 2,254-row
Gate B/C packet, in one migration. Census 116,838 / 281,257 -> 117,970 / 282,389; the four
corpora unchanged at RV 10,552 / SV 1,844 / YV 1,975 / AV 5,839; the content digest of all
17,283 pre-existing translations byte-identical before and after.

**Coverage is four populations per corpus, not one percentage.** `translated` narrowed to
mean a verse's own rendering, which is why the Rigvedic figure reads 10,479 where it read
10,502: the 30 anchors of the RV 1.65-1.70 spans left it, because Griffith renders each
pair of dvipada verses as one unit and none of the 60 verses those cover has a translation
aligned to it alone.

| corpus | own English | range-covered | reused rendering | non-English | uncovered |
|---|---|---|---|---|---|
| Rigveda 10,552 | 10,479 | 60 | 0 | 6 | 7 |
| Samaveda 1,844 | **0** | 0 | 173 | 0 | 1,671 |
| Yajurveda 1,975 | 1,939 | 0 | 0 | 0 | 36 |
| Atharvaveda 5,839 | 5,715 | 68 | 21 | 18 | 17 |

The five columns partition each corpus exactly, and the Samavedic zero is the one to read
carefully: 173 of its verses now show Griffith's Rigvedic English on text verified
character-identical, disclosed as a reused rendering. That is translation assistance and
not a Samavedic translation, so it is counted in no Samavedic translation figure anywhere
in the product.

Imported this round, by class: 844 source-explicit, 34 multi-verse print units covering 68
verses, 194 reused renderings, 36 independently verified Yajurvedic forced addresses, 24
Latin. 1,166 staged rows produced 1,132 nodes because 34 print units were staged once per
covered verse, and importing a node per row would have created the duplicated 1:1
translations the owner decision forbade.

Withheld: 740 rows on `mapping_confidence = PROBABLE`, 285 on an unresolved source
coordinate, 60 on provenance, 2 forced addresses withheld by name, 1 rejected as an
editorial cross-reference rather than a translation.

## What is NOT resolved by the translation round

- **No translation gap closed.** GAP-TRANSLATION-001, -002, -003 and -004 all moved a long
  way and none of their closure tests passes: 1,671 Samavedic, 17 Atharvavedic, 36
  Yajurvedic and 7 Rigvedic verses are reached by no rendering of any kind. Improved
  coverage is not closure, and the Samavedic case is why the distinction is kept.
- **The owner decision quoted 22 Latin rows and the measured population is 24.** AV 20.136.1
  and RV 10.61.6 carry Latin literals and had been classified source-explicit English. Both
  were verified against the pinned source pages -- sacred-texts heads its AV 20.136 page
  "Erotica" and prints verses 1-16 in Latin -- and both are imported as `language: la`.
- **Two consumers are stale and blocked, both for reasons outside this round.** The semantic
  resemblance layer needs re-derivation from the post-import snapshot per owner ruling, and
  the Ask benchmark re-grade is blocked on LLM quota.
- **GAP-FORMULA-003 is unchanged**, deliberately: `formulas_strictly_contained_in_another`
  measures 1,064 against an expected 1,103, exactly as before the import.
