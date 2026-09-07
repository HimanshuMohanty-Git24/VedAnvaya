# Samaveda Kauthuma Pilot

**Dataset**: `samaveda_pilot_v1`
**Work**: `VG:WORK:SV:KAU` — Samaveda Samhita, Kauthuma recension
**Build config**: `data/builds/samaveda_pilot_v1.yaml`
**Output**: `data/canonical/samaveda_pilot_v1/`
**Manifest**: `docs/manifests/samaveda_pilot_v1.json`
**Source research**: `docs/reports/SAMAVEDA_SOURCE_RESEARCH.md`

> **Samaveda identity is UNDECLARED.** `data/registry/works.yaml` carries `key_pattern: null`
> and `identity_status: RESEARCH_REQUIRED`. The keys in this pilot are **candidate keys**
> produced by `identity.sv_mantra_identity`, which is landed but explicitly **not frozen**.
> Nothing here should be described as canonical or provisional-canonical identity.

---

## 1. What this pilot proves

| Capability | Result |
|---|---|
| Source acquisition | Snapshotted via the repo's `PoliteFetcher`; hash-verified before parsing |
| Parsing | 3714 verse lines → 1868 verse keys from a TEI file with **no structural markup** |
| Hierarchy | 5 levels, **variable depth**, absent levels encoded `0` |
| IDs | 139 passages, all keys/URNs/UUIDs unique and recomputable |
| Sanskrit preservation | `text_original` verbatim; verbatim source lines retained separately |
| Translation alignment | **Deliberately not attempted** — see §7 |
| Provenance | Snapshot sha256, artifact id, source id, per-line evidence, registry-resolved sources |
| Deterministic rebuild | **Byte-identical over 3 consecutive runs** |

---

## 2. Run it

> **RETIRED 2026-09-07 by `SAMAVEDA_REFERENT_INTEGRITY_REPAIR`.**
> `scripts/build_samaveda_pilot.py` has been **deleted**, and this section is kept only so
> the rest of this document reads as the historical record it now is. The script minted
> canonical `Passage`, `TextVersion` and `Citation` identity from the GRETIL artifact,
> which is `PERMISSION_REQUIRED` and was adjudicated unusable as canonical primary, using
> the retired `A{arcika}` key with zero-filled absent levels. It had also stopped running
> at HEAD. Leaving it was the worse option: repairing its call signature would have
> re-materialized encumbered rows under a dead scheme.
>
> Its replacements, both of which read the **selected** witness:
>
> ```sh
> ./.venv/Scripts/python.exe scripts/build_samaveda_referent_audit.py [--baseline]
> ./.venv/Scripts/python.exe scripts/build_samaveda_referent_migrations.py
> ./.venv/Scripts/python.exe scripts/compare_samaveda_sources.py   # structure only
> ```
>
> The GRETIL artifact retains its granted roles — `hierarchy`, `reference_system`,
> `edition_comparison` — and `compare_samaveda_sources.py` exercises exactly those,
> reading reference labels and printed running numbers and no Sanskrit text. It can no
> longer mint identity at all: `SamavedaVerse.verse_key` now returns a `GRETIL-SV …`
> structural locator.

The build read only the config, the hash-verified snapshot, and the registries. It fetched
nothing, took its timestamp from the config rather than the clock, and repaired no defect.

---

## 3. Output

| File | Records | Notes |
|---|---|---|
| `works.jsonl` | 1 | Read from `data/registry/works.yaml` verbatim |
| `sources.jsonl` | 1 | Read from the registry; build **fails** if a referenced source is absent |
| `source_artifacts.jsonl` | 1 | `GRETIL.SV.KAUTHUMA.TEI.2020`, rights `PERMISSION_REQUIRED` |
| `passages.jsonl` | **139** | 102 `MANTRA` + 37 `STRUCTURAL_CONTAINER` |
| `text_versions.jsonl` | 102 | IAST, `PRIMARY_TEXT`, with `content_sha256` |
| `citations.jsonl` | 208 | 102 canonical structural + 106 non-canonical `SV_RUNNING_VERSE` |
| `source_assertions.jsonl` | 242 | verbatim source lines, parse defects, computed-structure claim |
| `text_comparisons.jsonl` | 29 | GRETIL vs Sanskrit Wikisource |
| `translations.jsonl` | **0** | Empty on purpose — §7 |

---

## 4. Structural region sampling

**102 mantra passages** — within the 50–150 target. The sample was **not** taken from the
first prapāṭhaka and assumed to generalise; every one of the 20 selected
`(arcika, prapathaka, ardha, dasati)` units is declared in the build config with a stated
rationale, and units were chosen partly *because* they contain known defects.

| Region | Units | Mantras |
|---|---|---|
| `PURVARCIKA_EARLY` | (1,1,1,1), (1,1,1,5) | |
| `PURVARCIKA_MIDDLE` | (1,3,2,8) | |
| `PURVARCIKA_LATE` | (1,6,2,9) | 38 total in ārcika 1 |
| `ARANYA_ARCIKA` | (2,0,0,1) | 9 |
| `MAHANAMNYA_ARCIKA` | (3,0,0,0) | 10 |
| `UTTARARCIKA_EARLY` | (4,1,1,1), (4,1,1,2), (4,1,1,6), (4,1,1,12) | |
| `UTTARARCIKA_MIDDLE` | (4,4,1,1..3), (4,5,1,18), (4,5,2,6), (4,5,2,10), (4,6,2,16) | |
| `UTTARARCIKA_LATE` | (4,9,3,1), (4,9,3,5), (4,9,3,9) | 45 total in ārcika 4 |

All **8** regions and all **4** ārcikas are covered, including both label notations and the
CONCAT/SPACED boundary at (4,6,2,16).

---

## 5. Variable depth, demonstrated

A level the source writes as `0` gets **no container node**; a verse's parent is the deepest
level that actually exists. Measured from the output:

```
1 level:   4 passages        parent of an ārcika-1 mantra: VG:SV:KAU:A1:P01:R1:D01
2 levels:  7 passages        parent of an ārcika-2 mantra: VG:SV:KAU:A2:P00:R0:D01
3 levels:  8 passages        parent of an ārcika-3 mantra: VG:SV:KAU:A3
4 levels: 18 passages
5 levels: 102 passages
```

Ārcika 2 skips prapāṭhaka and ardha; ārcika 3 skips three levels and hangs its verses
directly off the ārcika. The four depth-1 ārcikas carry `parent_key: null`, matching the
Rigveda's depth-1 Maṇḍalas.

Note the key retains the zeros (`A2:P00:R0:D01`) so the address stays positionally
parseable, while the *parent chain* reflects the real tree. Those are two different facts and
the build does not conflate them.

`sequence_in_parent` is the verse's position among its siblings computed over the **whole
1868-verse corpus**, not over the sample, so the value is stable regardless of what a build
samples. A sampled pilot therefore shows gaps by construction, and those gaps are true source
positions — 12 of 38 parents, declared.

---

## 6. Text handling

- **`text_original`** is the verse's source lines joined, with whitespace collapsed to a
  single space. Every other character survives untouched, including the danda punctuation and
  GRETIL's in-word numeric pluta digit (`nyā3triṇam`) — the *only* suprasegmental information
  in the artifact.
- **The running-number apparatus (`.. 1875`) is removed** from `text_original` by a single
  deterministic rule and re-recorded as a non-canonical `Citation`. It is edition apparatus,
  not text, and leaving it in would corrupt every downstream comparison and search.
- **Nothing is lost**: every verse's exact physical source lines are retained verbatim in
  `source_assertions.jsonl` under `SOURCE_LINE_VERBATIM`, with the label notation that matched.
- **`text_nfc`** is the derived NFC surface. `text_original` is never replaced by it.
- **Accents**: the artifact has **none**. Zero occurrences of U+0951–U+0954, the whole
  U+1CD0–U+1CFF Vedic Extensions block, U+030D and U+0331. Its upstream states verbatim:
  *"Unless indicated otherwise, accents have been dropped in order to facilitate word
  search."* So `text_original == text_nfc` on every record, and that is **faithful
  preservation of an unaccented source, not stripping**. `accented` is `false` everywhere.
- **IAST** is the *source* form (`xml:lang="sa-Latn"`), recorded as
  `transliteration_scheme: IAST`. No Devanagari is generated: that would be a derived
  representation requiring a reverse transliterator this agent does not own.

---

## 7. Why `translations.jsonl` is empty

There is **no rights-clear machine-readable English translation aligned to Kauthuma**:

- English Wikisource has a **preface and 23 red links** — zero verse text.
- Griffith's own preface says **"I have followed Benfey's text"**, and Benfey's edition is
  **Rāṇāyanīya**, a different recension. Griffith's Part II also has six Books where the
  Kauthuma Uttarārcika has nine prapāṭhakas.

Aligning by sequence number would be exactly the `ADR-010` error. Leaving it unaligned is the
correct outcome, not an omission.

---

## 8. Declared source defects

Recorded as `SourceAssertion` with status `NEEDS_REVIEW`, **never repaired**. In this pilot's
sample:

| Code | Count |
|---|---|
| `DUPLICATE_LINE_LABEL` | 13 |
| `ZERO_VERSE_INDEX` | 4 |
| `TRANSLITERATION_RESIDUE` | 3 |
| `UNEXPECTED_UPPERCASE` | 3 |
| `UNPARSEABLE_REFERENCE_LABEL` | 1 |
| `CANONICAL_IDENTITY_REFUSED` | 1 |

### 8.1 One record is deliberately refused identity

The verse at `(4,6,2,16,0)` has a **verse index of 0**, which the reference system does not
define. `sv_mantra_identity` **fails closed** and raises, so no key is minted. The record is
present in `source_assertions.jsonl` with its verbatim source lines and absent from
`passages.jsonl`. Expect the mantra count to be one short of the sampled verse count. It was
**not renumbered to reach 1875**.

### 8.2 Parser failures, stated plainly

- **One source line is not ingested at all**: `rm 4 4 1 02 02c pavante vāre avyaye .. 1035`.
  The stray `rm ` prefix means it matches neither declared notation. It is reported as
  `UNPARSEABLE_REFERENCE_LABEL` and **its text is lost to the corpus**. This is also the
  reason running number 1035 is absent.
- **12 verse keys absorb more than one verse's lines** because the source reuses a line label
  within a verse. The consequence is visible in the output: `SV 1.1.1.1.1` carries 15 tokens
  where the parallel source has 10. The parser does not split them, because deciding where
  the boundary belongs is an editorial judgement.
- **Count reconciliation is open**: 1868 computed keys against the source's own 1875 claim, a
  **7-verse gap**, recorded in the manifest and in the `COMPUTED_STRUCTURE` assertion rather
  than closed by guessing.

---

## 9. QA results

### 9.1 Own gate run — 12/12 PASS

| Gate | Result |
|---|---|
| `G01` unique structural ids | PASS — 0 duplicate keys / entity_ids / URNs |
| `G02a` uuid from urn | PASS — 0 mismatches, uuid5 recomputed over all 139 |
| `G02b` identity function roundtrip | PASS — key/URN/UUID re-derived from `hierarchy` via `identity.py` |
| `G02c` content_sha256 | PASS — 0 mismatches, recomputed |
| `G03` parent ref integrity | PASS — 0 unresolved `parent_key` |
| `G04` sequence continuity | 12/38 parents non-contiguous — **declared**, see §5 |
| `G04b` no duplicate sequence in parent | PASS — 0 |
| `G05` source count reconciliation | 1875 claimed vs 1868 computed from 3714 lines; **unreconciled 7** |
| `G06` unicode NFC stability | PASS — 0 non-NFC, 0 non-idempotent |
| `G07` accent preservation | PASS — 0 tone codepoints, `accented` false everywhere; 4 records retain in-word numeric svara |
| `G07b` verbatim source lines present | PASS — 0 text versions unbacked |
| `G08` jsonl schema valid | PASS — all lines validate |

### 9.2 Repo validator (`qa.checks.validate_corpus`)

**26 issues, 0 ERRORs**: 20 `valid_hierarchy` INFO (the declared-absent zeros, surfaced by
design) and 6 `sequence_gaps` WARNING (the declared sample gaps).

### 9.3 Rebuild byte-identical — **PASS, measured**

Three consecutive runs; sha256 identical on every file.

An **earlier** pair of runs *did* differ on `passages.jsonl`. The cause was not the builder:
Agent A landed `native_labels`/`structural_path` on `Passage` between the two runs, and the
builder populates those fields conditionally on the model version. Worth recording, because a
mid-flight contract change is indistinguishable from a determinism failure at the hash level.

### 9.4 Defects found by Agent F and fixed

- **SV-1** — the four ārcika containers pointed `parent_key` at the `work_id`, which is not a
  `Passage` key. Now `null`, matching Rigveda. The local G03 had been too lenient (it accepted
  `work_id` as a known key); the cross-check caught what the self-check missed.
- **SV-2** — `sources.jsonl` and `source_artifacts.jsonl` were absent, leaving 344 dangling
  provenance pointers. Both are now emitted, **read from the registries** and with the build
  **raising** if a referenced id is not registered.

---

## 10. Files written by this pilot

**Adapters** (new)
- `src/vedagraph/ingest/adapters/samaveda_gretil.py`
- `src/vedagraph/ingest/adapters/samaveda_wikisource.py`

**Scripts** (new)
- `scripts/build_samaveda_pilot.py`
- `scripts/compare_samaveda_sources.py`

**Config / registry** (new)
- `data/builds/samaveda_pilot_v1.yaml`
- `data/source_registry/samaveda_sources.yaml`

**Output** (new)
- `data/canonical/samaveda_pilot_v1/*.jsonl`
- `docs/manifests/samaveda_pilot_v1.json`

**Snapshots** (new, immutable)
- `data/raw/gretil/2026-09-07/` (2 files + metadata)
- `data/raw/wikisource_sa/2026-09-07/` (3 files + metadata)
- `data/raw/wikisource_griffith_sv/2026-09-07/` (1 file + metadata)

**Docs** (new)
- `docs/reports/SAMAVEDA_SOURCE_RESEARCH.md`
- `docs/pilots/SAMAVEDA_PILOT.md`

No file owned by another agent was modified.
