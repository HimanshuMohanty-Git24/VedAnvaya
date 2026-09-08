# Atharvaveda working corpus — full digital ingestion

**Work:** Atharvaveda Saṃhitā, Śaunaka recension (`VG:WORK:AV:SAU`)
**Corpus:** `ATHARVAVEDA_SAUNAKA_DIGITAL_WORKING_V1`
**Status:** `WORKING_PRIVATE`
**Build:** `data/canonical/atharvaveda_saunaka_digital_working_v1/`
**Config:** `data/builds/atharvaveda_saunaka_digital_working_v1.yaml`
**Executable:** `scripts/build_atharvaveda_working_v1.py`
**Adapter:** `src/vedagraph/ingest/adapters/atharvaveda_gretil.py`

---

## 0. What this corpus is, and what it is not

It **is** the complete Śaunaka Atharvaveda, keyed and QA'd, for VedaGraph product
development on a private build.

It is **not** an independent transcription of Roth & Whitney, Berlin 1856, and no record in
it may be described as one. The actual lineage is:

```
Orlandi 1991 (Pisa), transliteration, collated with Roth/Whitney 1856
  -> TITUS redaction (Gippert 1997; books 11-20 improved by Griffiths 2000
     and Kubisch 2007, revised by Griffiths 2009)
  -> GRETIL legacy-HTML re-host (avs_acu.htm, avs___u.htm)
  -> this build
```

Roth/Whitney 1856 is a **collation basis inside that lineage**, not the text this corpus was
read from.

The image-based independent-transcription project (`scripts/build_atharvaveda_canonical.py`,
`data/canonical/atharvaveda_saunaka_1856_*`) is **cancelled**. Its outputs are stale. This
build neither reads nor regenerates them, and supersedes them as the AV *working* corpus
only — it does not supersede them as a scholarly edition, because it makes no
scholarly-edition claim.

**Rights, unchanged and still binding.** The GRETIL/TITUS Sanskrit artifacts are
`REFERENCE_ONLY`; the upstream TITUS clause forbids republication and the root of the chain
(Orlandi 1991) is still in copyright. The Whitney & Lanman 1905 translation layer is public
domain in the US. This corpus may be read, keyed and compared against locally. Publishing
it, or anything derived from its Sanskrit layer, is **not** authorised by this build.

---

## 1. Digital Śaunaka candidates already in the repository

Twelve candidates were already investigated and recorded in
`data/source_registry/atharvaveda_sources.yaml` (verification date 2026-09-07). No new
source research was performed for this build; the existing evidence was ranked and acted on.

| Candidate | Role | Recension | Script | Accents | Machine-readable | Outcome |
|---|---|---|---|---|---|---|
| `GRETIL_AVS` (`avs_acu.htm`) | Primary Sanskrit | Śaunaka, proved per-locator | Latin (TITUS) | **Accented, verified** | legacy HTML, one pada per line | **SELECTED — primary** |
| `GRETIL_AVS` (`avs___u.htm`) | Parallel Sanskrit | Śaunaka | Latin | Unaccented, verified | same | **SELECTED — parallel witness** |
| `VEDAWEB_AVS` (Whitney/Lanman 1905) | English translation | Śaunaka | — | — | JSON API, alias-addressable | **SELECTED — translation** |
| `TITUS_AVS` | Sanskrit upstream | Śaunaka | Latin | Accented | restricted plain text | Not selected: GRETIL is the same text, retrievable |
| `WIKISOURCE_AVS_SA` | Sanskrit | Śaunaka | Devanagari | **None** (no U+0951/U+0952) | MediaWiki API | Not selected: unaccented |
| `VHP_AVS`, `THEVYASA_AVS`, `VEDAMU_AVS`, `ARCHIVE_ORG_AV_202107`, `VEDAVANI_HF` | Sanskrit / mixed | varies, some unverified | varies | varies | varies | Not selected |
| `WIKISOURCE_WHITNEY_AV`, `SACRED_TEXTS_GRIFFITH_AV` | English translation | — | — | — | yes | Not selected as primary translation |
| `GRETIL_AVP`, `VEDAWEB_AVP` | **Paippalāda** | *not Śaunaka* | — | — | — | **Explicit non-candidates** |

Ranking criteria, in the order the brief specifies: (1) correct Śaunaka recension,
(2) completeness, (3) machine readability, (4) accent preservation, (5) structural
parseability, (6) deterministic reproducibility.

`GRETIL_AVS` accented is the only candidate that satisfies all six. It is the sole
**accented** complete Śaunaka witness that is retrievable and parseable; every other
accented candidate in the matrix descends from the same Orlandi/TITUS root anyway, so
choosing a different one would change the rights position not at all and the text barely.
The recension is proved from the artifact by two independent witnesses — the document title
("Atharvaveda-Samhita, Saunaka recension") and all 11,395 body locators being prefixed
`AVŚ_` — so a swapped snapshot fails loudly rather than being ingested as AVS.

---

## 2. Working text versions

Three already-registered `text_version_id`s are reused. **No identity, key, URN or UUID rule
was redesigned for this build.**

| `text_version_id` | Role | Artifact | Accented | Rights |
|---|---|---|---|---|
| `GRETIL.AVS.SAUNAKA.ACCENTED` | `PRIMARY_TEXT` | `GRETIL.AV.SAUNAKA.ACCENTED.HTML` | yes | `REFERENCE_ONLY` |
| `GRETIL.AVS.SAUNAKA.UNACCENTED` | `PARALLEL_TEXT` | `GRETIL.AV.SAUNAKA.UNACCENTED.HTML` | no | `REFERENCE_ONLY` |
| `VEDAGRAPH.AVS.SEARCH_NORMALIZED` | `SEARCH_DERIVATIVE` | derived from the accented text | no | `REFERENCE_ONLY` |

The search surface is **derived** and is never written back over the accented text. Accents,
the pāda divider `|`, the edition's own verse marker `||18||`, the anuvāka marker `{12}` and
the alternate-unit marker `[8]` all survive verbatim in `text_original`.

---

## 3. Structure, computed from the snapshot

Every figure below was counted from the bytes this build read. The reference-literature
values are recorded beside them for comparison and were **never** used to pad, truncate or
correct a computed count.

| | Computed | Reference literature | Agrees |
|---|---|---|---|
| Kāṇḍas | **20** | 20 | yes |
| Sūktas | **731** | 731 | yes |
| Mantras (distinct) | **5,839** | ~5,839 | yes |
| Parsed units | 5,843 | — | 4 duplicate-locator occurrences, all retained |
| Pādas | 11,395 | — | — |

Sūktas per kāṇḍa: 35, 36, 31, 40, 31, 142, 118, 10, 10, 10, 10, 5, 4, 2, 18, 9, 1, 4, 72,
143.

Other digital witnesses in the same lineage give different totals — VedaWeb 5,842 stanza
locations, the TITUS restricted plain text 5,919 verse markers, reference works usually
~5,977. Those are real editorial decisions, not parser noise, and none is reconciled here.
See `FOUR_DIFFERENT_VERSE_COUNTS_IN_ONE_TEXTUAL_LINEAGE` in
`data/source_registry/atharvaveda_sources.yaml`.

## 4. Coverage

| Layer | Records | Coverage |
|---|---|---|
| Passages | 6,590 | 20 SECTION + 731 HYMN + 5,839 MANTRA |
| Sanskrit accented (`PRIMARY_TEXT`) | 5,839 | **100.00%** of mantras |
| Sanskrit unaccented (`PARALLEL_TEXT`) | 5,839 | 100.00% |
| Search-normalized (`SEARCH_DERIVATIVE`) | 5,839 | 100.00% |
| **Accent coverage on the primary layer** | 5,839 | **100.00%** |
| Empty Sanskrit passages | **0** | — |
| Provenance on every text record | 17,517 / 17,517 | **100.00%** |
| Canonical citations (`AVS_ROTH_WHITNEY_1856`) | 5,839 | 100.00% of mantras |
| Alternate citations (`AVS_VISHVA_BANDHU_1960`) | 261 | non-canonical |
| English translations (Whitney & Lanman 1905) | 4,878 | 83.54% of mantras |
| Traditional metadata (ṛṣi / devatā / chandas) | **0 / 0 / 0** | see §8 |
| Audio | 0 | out of scope |

Cross-artifact comparison of the accented against the unaccented witness classifies all
5,839 readings as `ACCENT_ONLY` — the two GRETIL files agree on every character except
accent marks, which is the expected result and a real check that neither was misparsed.

## 5. Identity

Unchanged rules: canonical key → canonical URN → deterministic UUIDv5 over the URN. Identity
is **never** derived from a text hash.

| Check | Result |
|---|---|
| Duplicate canonical keys | **0** |
| Duplicate canonical URNs | **0** |
| Duplicate UUIDs | **0** |
| entity_id not equal to uuid5(namespace, canonical_urn) | **0** |
| Missing structural parents | **0** |
| Non-`AVŚ_` locators (recension mixing) | **0** |
| Deterministic record ordering | passages emitted in structural order |

Cross-Veda, over all four released works (22,537 passages: RV 11,590 · AV 6,590 · SV 2,342 ·
YV 2,015), from `data/builds/four_veda_corpus_completeness.json`:

```
cross_work_canonical_key_collisions : {}
cross_work_canonical_urn_collisions : {}
cross_work_entity_id_collisions     : {}
intra_work_duplicate_keys           : {}
clean                               : true
```

Source-assertion provenance across all four works: 33,113 assertions examined, **0 orphan
claims**.

## 6. Structural QA — every anomaly, none suppressed

`qa_status = PASSED_WITH_WARNINGS`; 9 findings (6 WARNING, 3 INFO), **0 ERROR**. The shared
cross-Veda gate `vedagraph.qa.validate_corpus` also ran on this corpus and returned 1
WARNING (the 9.6 gap below) — no longer the `KeyError` the pilot recorded.

| Finding | Detail |
|---|---|
| `av_duplicate_locator_triples` | 4: `9.6.48`, `12.5.53`, `13.4.26`, `20.96.22`. The edition prints two different units under one number. The unit whose printed verse marker agrees with its locator is canonical; the other is retained **verbatim, with its full Sanskrit**, as a `NON_CANONICAL_DUPLICATE_OCCURRENCE` assertion. Nothing renumbered, nothing discarded. |
| `av_mantra_number_gaps` | 3 sūktas: `9.6` missing 49, `12.5` missing 1, `13.4` missing 1. These are gaps in the **edition's own numbering** — 13.4's first verse is printed as 26 while its in-text marker says 1. Reported, never filled. |
| `av_sukta_number_gaps` | none — sūkta numbering is contiguous in all 20 kāṇḍas. |
| `av_label_marker_disagreement` | 10 units where the locator and the printed verse marker disagree: `7.6.3`, `7.6.4`, `7.45.2`, `7.54.2`, `7.55.1`, `7.68.3`, `7.72.3`, `7.76.5`, `7.76.6`, `13.4.22`. Both witnesses kept; neither treated as authoritative. |
| `no_silently_missing_records` | 5,843 parsed units vs 5,839 canonical mantras; the 4-unit surplus is exactly the duplicate occurrences above. Nothing vanished. |
| `av_prose_paryaya_not_classified` | 699 single-pāda units, concentrated in kāṇḍas 15 (98), 9 (87), 20 (85), 12 (77), 19 (69), 16 (66). |
| `av_traditional_metadata_absent` | ṛṣi 0, devatā 0, chandas 0. |

### Prose and paryāya

The source marks **no** unit as prose and **no** unit as verse. This corpus therefore asserts
no metrical classification anywhere. `single_pada_unit` is recorded as a fact about the
printed line count and is explicitly **not** a prose claim. The paryāya material of kāṇḍas
15 and 16 (and 8.10, 9.6, 11.3, 12.5, 13.4, 18.4) is stored as ordinary passages on the
edition's own numbering; no record was forced into a fake mantra and none was invented to
fill a slot. Classifying it is open backlog.

### Kāṇḍa 19 and kāṇḍa 20

| | Sūktas | Mantras | Sanskrit | English |
|---|---|---|---|---|
| Kāṇḍa 19 (supplementary) | 72 | 453 | 453 (100%) | 453 (100%) |
| Kāṇḍa 20 (Rigvedic in character) | 143 | 958 | 958 (100%) | **0** |

Kāṇḍa 20 overlaps the Rigveda extensively. **It was not deduplicated against
`VG:WORK:RV:SAK` and not one of its 958 mantras was sourced from the Rigveda** — every
kāṇḍa 20 `text_versions` record cites a GRETIL AVS artifact and nothing else. A Rigvedic
parallel is a candidate for the derived parallels layer only, never the source of an AVS
mantra. This is asserted and machine-checkable as
`KANDA_20_TEXT_READ_ONLY_FROM_THIS_ARTIFACT`.

## 7. Translation alignment

Whitney & Lanman 1905, via VedaWeb resource `696f42266f50da42570ad040`. Staged by walking
the VedaWeb location tree over all 731 sūktas and attaching every stanza **by its own
printed alias triple, never by sequence position** (ADR-010). Staging reported 731 sūktas
walked, 4,881 verses, 0 kāṇḍa-alias misses, 0 sūkta-alias misses, 0 truncated pages,
0 unresolved stanza labels, across 875 immutable snapshots.

| | Count |
|---|---|
| **ALIGNED** | **4,878** |
| **MISSING** | **961** |
| **AMBIGUOUS** | **0** |
| **STRUCTURAL_DIVERGENCE** | **3** |

*Missing* = 958 of kāṇḍa 20 (Whitney deliberately excluded book 20, calling it "in the main
a pure mass of excerpts from the Rig-Veda") plus `3.9.4`, `5.12.11` and `10.8.30`, which the
Whitney layer does not carry.

*Structural divergence* = 3 verses the translation's edition numbers but this corpus does
not: `9.6.49`, `12.5.1`, `13.4.1`. Each produced a `TRANSLATION_HAS_NO_CANONICAL_PASSAGE`
assertion carrying the full English text, and **none was re-attached to a neighbouring
mantra**. These are the mirror image of the three numbering gaps in §6: VedaWeb silently
repaired the same TITUS defects the parser detected independently, which is genuine
cross-source corroboration that the defects are real.

Every translation record is `EXACT_MANTRA_ALIGNMENT`; zero are approximate, so the
AMBIGUOUS count is 0 by construction rather than by assumption.

## 8. Traditional metadata

**Zero records. Deliberately.** The artifact carries pāda text and numbering only — no ṛṣi,
devatā or chandas field appears anywhere in it, verified over the whole file. That absence
is recorded as the assertion `ARTIFACT_SUPPLIES_NO_TRADITIONAL_METADATA`.

It is not licence to infer AV metadata from Rigvedic Anukramaṇī rules, which do not
transfer, and not licence to generate it with a language model. The wider finding stands: a
rights-clear, machine-readable, **per-mantra** ṛṣi/devatā/chandas source for AVS does not
exist — what exists is public-domain-but-per-*hymn* (Whitney's Anukramaṇī brackets, 588
hymns, books I–XIX) or per-mantra-but-copyrighted (Vishva Bandhu).

## 9. Determinism

Two builds in **independent processes** from the same immutable snapshots:

```
diff -r --brief run1 run2  ->  no differences
DETERMINISTIC: byte-identical across two independent processes
```

`built_at` is pinned to the newest snapshot retrieval timestamp, not the wall clock, so
`manifest.json` is byte-identical too.

| File | SHA-256 |
|---|---|
| `manifest.json` | `49619dc5ce338382075b13f2446a9c033e6124368e1abc80e813e742ff5cbbf6` |
| `passages.jsonl` | `a6026dfd2b0184c0920bd5dcf7d9ad56e406067d4838adb2801ad6107a07fb7c` |
| `text_versions.jsonl` | `97712ddeaeb3032a7e41b22696f4a2e3b1f8f2bde6b5981d6936cca435bc3a48` |
| `translations.jsonl` | `1b85ace9603e274b492c2a82426310488549220e12a3174737d9eab3562c3d13` |
| `citations.jsonl` | `b24b2b666ea18f211df5fe50f6ef63e6b559455759031cb1d94329eaff5cd2ad` |
| `source_assertions.jsonl` | `ea41a566c9ffe9da6a92122b15e496f179251673b935e7700fe76c9ac2ba8944` |
| `text_comparisons.jsonl` | `5a152da5e7ce53208e0f6d381157b543a364d5b420ce291f3d6d275bc3217df7` |
| `qa_issues.jsonl` | `aab188694d6655ed566f5625edec7582a759394ceab29c9ad72d80a4b76187e0` |
| `sources.jsonl` | `81160791d28c556bf84b2f77ca03d1fa3dc1d3f09b8a9bc172b6e3fb6f62a2ef` |
| `source_artifacts.jsonl` | `b140973ad7d390cc744fdaed764603ffc05570b13526f28badd1ceb890ed79d3` |
| `works.jsonl` | `c028b32482de5d4b2e6ebcbcf5be541c04aabd885d4a6461080c1846f161d7bc` |
| `traditional_metadata.jsonl`, `audio_recordings.jsonl`, `audio_segments.jsonl` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (empty) |

Pinned inputs:

| Artifact | SHA-256 |
|---|---|
| `GRETIL.AV.SAUNAKA.ACCENTED.HTML` | `cd89bd1e29e6158d7c3c7bcb607b8e4eed4c7556c8c2027dec039f56736adddb` |
| `GRETIL.AV.SAUNAKA.UNACCENTED.HTML` | `7e3f74f313d1b4348bf9e1f60a80e03bb72709994b85585a4f854a51bf57272c` |

The registry's pinned `checksum_sha256` is cross-checked against the bytes actually read, so
a registry edit repointing an artifact at different bytes fails the build.

## 10. Tests and static analysis

| | Result |
|---|---|
| Full `pytest` | **1,028 passed, 41 skipped, 0 failed** (589s) |
| `ruff check .` | **All checks passed** |
| `mypy` (strict, `packages=["vedagraph"]`) | **Success: no issues found in 107 source files** |

The 41 skips are the cancelled scan pipeline's tests (`test_av_reproducibility`,
`test_av_accent_binder`, `test_atharvaveda_transcription`), which skip themselves with
"1856 scan not present in this checkout" — correct, the 478-leaf cache was removed — plus
one `openai`-dependent semantic test and the manual live-crawl placeholder.

### Regression: the other three Vedas

Every released corpus re-verified file-by-file against its own manifest:

| Release | Files verified | Passages | QA | Mismatches |
|---|---|---|---|---|
| `rigveda_full_v1` | 15 | 10,552 | PASSED_WITH_WARNINGS | none |
| `samaveda_arcika_v1` | 13 | 2,342 | PASSED_WITH_WARNINGS | none |
| `yajurveda_vsm_v1` | 13 | 2,015 | PASSED_WITH_WARNINGS | none |
| `atharvaveda_saunaka_digital_working_v1` | 13 | 5,839 | PASSED_WITH_WARNINGS | none |

No RV, SV or YV record was read, rewritten or renumbered by this session.

## 11. Decisions

**`ATHARVAVEDA_WORKING_CORPUS_READY` — yes.**

Complete (20 / 731 / 5,839), 100% Sanskrit coverage, 100% accent coverage, zero empty
passages, zero duplicate keys/URNs/UUIDs, zero cross-Veda collisions, 100% provenance,
deterministic, and every anomaly named rather than hidden.

**`VEDAGRAPH_FOUR_VEDA_WORKING_DATA_FOUNDATION_READY = true`.**

Four works released, none on a pilot fallback, 22,537 passages and 20,210 mantras with a
clean cross-work identity audit.

This is a **development** dataset. It is not a four-Veda scholarly critical edition and is
not claimed to be one.

## 12. Backlog (bounded, none blocking)

1. **Kāṇḍa 20 has no English.** 958 mantras. Closable: Griffith covers all 20 kāṇḍas
   per-verse on the same Berlin numbering spine and sacred-texts.com permits mirroring the
   body text (`SACRED_TEXTS_GRIFFITH_AV`). Not fetched here.
2. **3 mantras with no Whitney translation** — `3.9.4`, `5.12.11`, `10.8.30`.
3. **3 translation/structure divergences** — `9.6.49`, `12.5.1`, `13.4.1`; both witnesses
   retained, neither resolved.
4. **4 duplicate-locator triples** — `9.6.48`, `12.5.53`, `13.4.26`, `20.96.22`.
5. **10 label-vs-marker disagreements**, concentrated in kāṇḍa 7.
6. **Prose/paryāya unclassified** — 699 single-pāda units; the source supports no metrical
   claim either way.
7. **No traditional metadata** — and no rights-clear per-mantra source for it exists.
8. **Four irreconcilable verse counts** in one textual lineage (5,839 / 5,842 / 5,919 /
   ~5,977). Not reconciled, and not reconcilable from these artifacts alone.
9. **Sanskrit layer is `REFERENCE_ONLY` and unpublishable.** The only identified route to a
   rights-clear Śaunaka Sanskrit text is one derived solely from Roth/Whitney 1856 with no
   Orlandi collation. No such artifact was found.
10. **No audio.** Out of scope by decision.

## 13. Next phase

`NEXT_PROJECT_PHASE = NEO4J_KNOWLEDGE_GRAPH_FOUNDATION`. Not started in this session.
