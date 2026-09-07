# Four-Veda QA report

Owner: Agent F (corpus QA / normalization). Consolidated QA verdict for the Rigveda
reference corpus and the three new-Veda pilots.

**Reading rule for this document.** Every result below was produced by actually running the
gate against the build on disk. A gate that could not be run says `NOT_RUN` and gives the
reason. A gate is never marked `PASSED` on the strength of a build being absent, empty, or
plausible. Machine-readable output: `data/qa/four_veda_gate_results.json`.

## 1. Verdict

| Veda | Build | Passages | Gate verdict | `validate_corpus` |
| --- | --- | --- | --- | --- |
| Rigveda | `data/canonical/rigveda_full_v1` | 11,590 | **PASS** (7/7) | PASSED_WITH_WARNINGS, 8 issues |
| Samaveda | `data/canonical/samaveda_pilot_v1` | 139 | **PASS** (6/7, 1 N/A) | PASSED_WITH_WARNINGS, 26 issues, **0 ERRORs** |
| Yajurveda | `data/canonical/yajurveda_pilot_v1` | 140 | **PASS** (7/7) | **PASSED, 0 issues** |
| Atharvaveda | `data/canonical/atharvaveda_pilot_v1` | 174 | **PASS** (7/7) | FAILED, 14 issues (13 ERRORs, one cause) |

All three pilots landed and all three were actually gated. Nothing in this report is a
vacuous pass.

The single remaining ERROR cause anywhere in the four builds is one unregistered source id in
the Atharvaveda pilot (§5.4).

### 1.1 What the cross-Veda gate actually caught

Recorded because the point of a shared gate is to catch what a single-Veda owner cannot see
from inside their own build.

- **The shared validator was unrunnable for three of the four Vedas.** `validate_corpus`
  raised `KeyError: 'mandala'` on any non-Rigvedic mantra (§3.1a). Agent C reports the fixed
  validator landed before its run, and **Vājasaneyi (2-level Adhyāya→Mantra) passed through it
  with 0 issues — the first non-Rigvedic corpus through that validator.**
- **Two real defects in the Samaveda pilot that its owner had missed**, both found by the gate
  and both since fixed by Agent B (§5.2): an ārcika `parent_key` pointing at a `work_id`
  instead of being null, and missing `sources.jsonl` / `source_artifacts.jsonl`. The first is
  notable because Agent B's own gate scored it PASS — it admitted `work_id` into its
  known-keys set, so only a cross-Veda comparison against the RV/YV/AV convention exposed it.
- **A missing provenance file in the Atharvaveda pilot** (§5.4), fixed by Agent D: 760 of its
  761 issues cleared in one move.
- **A sealed-artifact regression in the frozen semantic layer** (§12.1), caused by
  `vedagraph schema export` and escalated to Agent A, who recovered the exact sealed bytes
  from a dangling git blob.
- **Two defects in this agent's own files**, found by measuring rather than by assuming
  (§4 of the normalization policy): udātta was invisible to `has_vedic_accents()` after
  transliteration, and the search surface was not idempotent for upper-case input.
- **One false-error regression this agent introduced and then caught in itself** (§3.1d): a
  parent rule that reported 11 of 102 real Samaveda verses as broken.

## 2. The gate as implemented

Ten gates. `check id -> what it proves`:

| Gate | Proves | Implementation |
| --- | --- | --- |
| G01 `unique_structural_ids` | No two passages share a `canonical_key`, `canonical_urn`, `entity_id` or `canonical_citation`. Identity is injective. | gate runner + `unique_canonical_keys`, `unique_uuids`, `unique_canonical_citations` in `qa/checks.py` |
| G02 `uuid_determinism` | Every stored `entity_id` equals `uuid5(VedaGraph namespace, canonical_urn)`. Identity is *derived*, not assigned, so it cannot drift silently. | **new** `stable_uuid_deterministic` check in `qa/checks.py` + independent recomputation in the runner |
| G03 `parent_ref_integrity` | Every non-null `parent_key` resolves to a passage in the same build. The tree has no dangling edges. | `valid_parents` |
| G04 `sequence_continuity` | `sequence_in_parent` is contiguous within each parent and never duplicated. Gaps are **reported, never filled**. | `sequence_gaps`, `unique_sequences_in_parent` |
| G05 `source_count_reconciliation` | Record counts reconcile against the source's own stated counts. | §6 — **partly NOT_RUN, honestly** |
| G06 `unicode_nfc_stability` | `text_nfc` is NFC-stable, `text_nfc == NFC(text_original)`, and normalization is idempotent. | gate runner over every `TextVersion` |
| G07 `accent_preservation` | A record that **declares** accents actually carries tone marks; `text_original` is never replaced by a derived form. | gate runner, keyed on `TextVersion.accented` |
| G08 `jsonl_schema_valid` | Every line of every JSONL validates against its Pydantic model. | `storage.jsonl.read_jsonl` per file |
| G09 `normalization_determinism` | Same input produces the same output across runs **and across processes**. | §7 |
| G10 `rebuild_byte_identical` | Re-running the build produces byte-identical output. | §8 — independently re-run by this agent |
| G11 `registry_checksum_agreement` | Every artifact a release claims is declared by the source registry; where both state a checksum they agree; and the pinned bytes are still on disk and intact. | **new** `verify_registry_checksums` + `verify_content_addressed_snapshots` in `qa/checks.py` |
| G11b `checksum_scope_agreement` | A pinned checksum names a snapshot of the *right thing* — matching some snapshot is not verification. | **new** `verify_checksum_scope` in `qa/checks.py` |
| G12 `snapshot_namespace_resolves` | A raw-storage namespace resolves, through the build's own machine-readable assertions, to a source the release actually declares. | **new** `verify_snapshot_namespaces` in `qa/checks.py` |
| G13 `manifest_snapshots_reconcile` | Every snapshot a manifest names exists on disk and hashes correctly, **and** the manifest does not under-report snapshots the build read. | **new** `verify_manifest_snapshots` in `qa/checks.py` |
| G14 `text_version_registered` | Every `text_version_id` a release uses is declared in `data/registry/text_versions.yaml`, where rights and lineage attach. | **new** `verify_text_version_registration` in `qa/checks.py` |
| G15 `text_role_matches_registry` | A record's `text_role` equals the registry's role for that version id — `TextRole` is a permission statement, not the build's to choose. | **new** `verify_text_role_matches_registry` in `qa/checks.py` |

Two structural checks were added or rewritten in `qa/checks.py` and are worth naming
separately, because they did not exist before:

- `stable_uuid_deterministic` — **there was no UUID determinism check at all.** An identity
  drift caused by a change to `identity.py` or the URN scheme could have shipped unnoticed.
- `declared_work_hierarchy` — asserts that a passage's `hierarchy` keys are exactly the first
  N lower-cased levels declared for its work in `data/registry/works.yaml`, that the leaf
  level carries `MANTRA`, and that non-leaf levels do not. This is what makes the gate
  work-agnostic, and it catches a build drifting from its declared structure.

## 3. Rigveda-shaped assumptions found, and what changed

Grep across the QA and build layers for hardcoded `mandala`/`sukta` returned 45 hits in 10
modules. The QA layer's three were fixed. The rest are recorded, and ownership is stated
rather than assumed.

### 3.1 Fixed in `src/vedagraph/qa/checks.py` (this agent's file)

**(a) A hard crash, not a failed check.** `validate_corpus` did this for every `MANTRA`,
ungated on discovery records existing:

```python
mantra_sukta_key = (int(passage.hierarchy["mandala"]), int(passage.hierarchy["sukta"]))
```

A Vajasaneyi mantra's hierarchy is `{"adhyaya": N, "mantra": M}`. There is no `"mandala"`
key, so `validate_corpus` raised `KeyError: 'mandala'` and **the entire gate was unrunnable
for any non-Rigvedic work.** Reproduced on a minimal synthetic 2-level corpus before the fix
(`CRASH: KeyError: 'mandala'`); independently confirmed by Agents C and D against their real
builds. Fixed by guarding on the keys actually present, so the Rigveda-shaped reconciliation
no-ops off-Rigveda instead of raising. **Proof it is fixed: `validate_corpus` now COMPLETES
on all four builds, and Yajurveda returns status PASSED with 0 issues.**

**(b) A false error on every mantra of a 2-level work.** `valid_parents` hardcoded the
Rigveda's three-level chain — `MANTRA` must have a `HYMN` parent, `HYMN` must have a `SECTION`
parent. Vajasaneyi has no sūkta level, so its mantras legitimately have a `SECTION` parent and
every one of them was reported "mantra must be attached to a Sukta/HYMN parent". Replaced with
`_check_structural_position`, which derives the legal chain from the work's declared hierarchy
depth. Rigveda's `SECTION -> HYMN -> MANTRA` still validates, and the existing test that pins
a wrongly-parented mantra still fails it.

**(c) `valid_hierarchy` rejected a legitimate value.** The check errored on any hierarchy
value `< 1`. Samaveda encodes "this division has no such level" as a literal `0` — the Araṇya
and Mahānāmnya arcikas have no prapāṭhaka or ardha — which would have produced false ERRORs on
65 real verses. Now: negative is still an ERROR; `0` is reported as INFO
`"hierarchy level(s) [...] are declared absent (value 0) by the source"`. Surfaced so it can
never pass silently, and not rejected. Yields 20 INFO on the Samaveda pilot and 0 false errors.

**(d) A false error I introduced myself, then fixed.** My first work-agnostic parent rule
required a parent exactly one level up. That reported **11 of the Samaveda pilot's 102
verses** as broken, because with prapāṭhaka/ardha/dasati absent those verses hang directly off
the arcika and there is no intervening container to point at. Measured that all 11 skipped
only declared-absent (`0`) levels, then relaxed the rule to permit a higher parent when every
level in between is declared absent — while still erroring when a real level is skipped.
`valid_parents` on the Samaveda pilot went 19 -> 8, and the residual 8 were a genuine defect
(§5.2). Recorded because a check that emits false errors is a broken check, and this one was
mine.

### 3.2 Recorded, not fixed — ownership stated

| Module | Hits | Owner / status |
| --- | --- | --- |
| `compare/run.py` | 5 | Comparison layer. Rigveda-only config model — cannot express a 2-level or 5-level comparison at all. Full analysis in `FOUR_VEDA_CROSS_SOURCE_COMPARISON.md` §3.2. **Principal portability defect.** |
| `build.py` | 12 | Rigveda build pipeline; also emits 4 QA check ids that `validate_corpus` does not (§4.2). |
| `full_corpus.py` | 6 | Rigveda full-corpus assembly. |
| `knowledge/build.py` | 4 | Rigveda knowledge layer. |
| `ingest/adapters/gretil.py`, `vedaweb.py` | 9 | Rigveda adapters — correctly Rigveda-shaped; B/C/D have their own adapters. |
| `corpus.py` | 1 | Rigveda pilot path. |

`SuktaDiscoveryRecord` remains structurally Rigveda-only (it has required
`mandala_number`/`sukta_number`). Agent A has landed `SectionDiscoveryRecord` as the
work-agnostic successor. **The count-reconciliation path was deliberately not generalised onto
it** — no build emits `SectionDiscoveryRecord` yet, so wiring it in would create a check that
never runs and reports a vacuous pass. Recorded as the correct next step instead.

## 4. Rigveda compatibility verdict

Agent A landed changes to `enums.py`, `models/core.py`, `identity.py`, `schema.py` and
`works.yaml` during this session. This is the regression check.

### 4.1 Real numbers

| Measure | Baseline (pre-change) | After | Verdict |
| --- | --- | --- | --- |
| Baseline captured at | git HEAD `4da5bd7`, 2026-09-07T04:29:04Z | — | `data/qa/four_veda_rigveda_baseline.json` |
| File SHA-256, all 16 files in `rigveda_full_v1` | recorded | **16 unchanged, 0 changed, 0 missing** | **PASS** |
| Passages validating | 11,590 | 11,590, 0 invalid | **PASS** |
| Composition | 10 SECTION + 1,028 HYMN + 10,552 MANTRA | identical | **PASS** |
| Mantras | 10,552 | **10,552** | **PASS** |
| UUID sample match rate | — | **11,590 / 11,590 = 100%**, 0 mismatches | **PASS** |
| Namespace UUID | `7c8cde94-2bc0-50e2-8819-568ae65a3ec4` | unchanged | **PASS** |
| `validate_corpus` issues | 8 committed | 8 fresh; `only_fresh = {}`, `only_lost = {}` | **PASS** |
| Comparison distribution | ACCENT_ONLY 9,746 / SANDHI 35 / UNCLASSIFIED 771 | identical after every change | **PASS** |

The UUID check covered **all 11,590 passages**, not the ≥500 sample asked for. Per level:
SECTION 10/10, HYMN 1,028/1,028, MANTRA 10,552/10,552.

### 4.2 On the 834 "missing" issues — not a regression

The committed `qa_issues.jsonl` holds 842 issues; a fresh `validate_corpus` produces 8. The
difference is not loss. Four check ids — `primary_parallel_text_divergence` (806),
`translation_coverage_incomplete` (17), `translation_alignment_uncertain` (10),
`translation_page_parse_failed` (1) — are emitted by **`build.py`**, not by
`validate_corpus`; confirmed by grep. The committed file is the union of build-stage and
validation-stage issues. Set-differenced against the committed file restricted to
`validate_corpus`'s own check ids, `only_fresh` and `only_committed` are both empty.

### 4.3 Layers still loading

All confirmed by Agent A and cross-checked against my file fingerprint: works 1, citations
10,552, text_versions 21,104, translations 10,502, traditional_metadata 9, sources 8,
source_artifacts 14, source_assertions 22,143, audio_recordings 5, audio_segments 0,
discoveries 2,247, qa_issues 842 — all 0 invalid. Knowledge layer 0 invalid (rishis 367,
devatas 214, chandas 34, assertions 31,650, anukramani 1,028, metadata_source_assertions
4,577). Lexical layer 0 invalid (aliases 73, parallels 325, components 28). `manifest.json`
validates against `CorpusManifest`.

**Verdict: no Rigveda regression.** Canonical Rigveda data is byte-identical to the
pre-change baseline; identity, counts, validation output and comparison distribution are all
unchanged.

### 4.4 Baseline reconciliation

The brief gave a baseline of "~189 passed, 1 skipped". That figure is wrong. Agent A measured
592 passed / 2 skipped; I collect **594 tests**, which matches 592 + 2. We are on the same
tree and the briefed number is not reconcilable with it. Test results are reported in §9
against the 594-test tree.

## 5. Per-Veda gate results

Legend: `PASSED` · `PASSED_WITH_GAPS` (gaps found and reported, never filled) ·
`NOT_APPLICABLE` (the gate's precondition is genuinely absent) · `NOT_RUN` · `FAILED`.

| Gate | Rigveda | Samaveda | Yajurveda | Atharvaveda |
| --- | --- | --- | --- | --- |
| G01 unique_structural_ids | PASSED | PASSED | PASSED | PASSED |
| G02 uuid_determinism | PASSED 11,590/11,590 | PASSED 139/139 | PASSED 140/140 | PASSED 174/174 |
| G03 parent_ref_integrity | PASSED | PASSED (was FAILED, fixed) | PASSED | PASSED |
| G04 sequence_continuity | PASSED 1,038 parents, 0 gaps | PASSED_WITH_GAPS 37 parents, 12 with gaps | PASSED 4 parents, 0 gaps | PASSED_WITH_GAPS 21 parents, 6 with gaps |
| G05 source_count_reconciliation | PASSED (2,247 discoveries) | NOT_RUN — see §6 | NOT_RUN — see §6 | NOT_RUN — see §6 |
| G06 unicode_nfc_stability | PASSED 21,104 texts | PASSED 102 texts | PASSED 271 texts | PASSED 459 texts |
| G07 accent_preservation | PASSED 21,104 declared, 0 lost | NOT_APPLICABLE 0 of 102 declare accents | PASSED 135 declared, 0 lost | PASSED 153 declared, 0 lost |
| G08 jsonl_schema_valid | PASSED 10 files | PASSED 6 files | PASSED 9 files | PASSED 10 files |
| G09 normalization_determinism | PASSED | PASSED | PASSED | PASSED |
| G10 rebuild_byte_identical | NOT_RUN — see §8 | PASSED 9 files | PASSED 12 files | PASSED 14 files |
| G11 registry_checksum_agreement | PASSED_WITH_WARNINGS 14 artifacts, 2 unverifiable | PASSED 1/1 | PASSED_WITH_WARNINGS (was FAILED — Agent C fixed it) | PASSED_WITH_WARNINGS 3 artifacts, 1 unverifiable |
| G11b checksum_scope_agreement | PARTIAL 12 of 14 verified | PASSED | PARTIAL 1 of 2 verified (was FAILED — wrong-scope pin, since removed) | PASSED |
| G12 snapshot_namespace_resolves | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | PASSED 2 namespaces |
| G13 manifest_snapshots_reconcile | PASSED_WITH_WARNINGS 7 unlisted | PASSED_WITH_WARNINGS 2 unlisted | PASSED_WITH_WARNINGS **42 of 47 unlisted** | PASSED 25/25 |
| G14 text_version_registered | PASSED | PASSED (was FAILED) | PASSED (was FAILED) | PASSED (was FAILED) |
| G15 text_role_matches_registry | PASSED | PASSED | PASSED | PASSED |
| `validate_corpus` | COMPLETED, 8 issues | COMPLETED, 26 issues, 0 ERRORs | **COMPLETED, 0 issues** | COMPLETED, 14 issues |

### 5.1 Rigveda

Zero gaps across 1,038 parents and zero duplicate sequences over 11,590 passages. The 8
`validate_corpus` issues are all WARNINGs and all pre-existing: 6 `deferred_metadata_range`
(per-mantra ranges deliberately kept as source assertions) and 2
`duplicate_translation_for_passage`.

### 5.2 Samaveda — 5 levels with genuinely absent middle levels

Two defects found, both reported to Agent B, **both fixed and re-verified**:

- **SV-1** (caused G03 FAILED, 8 `valid_parents` ERRORs): the four arcika containers
  `VG:SV:KAU:A1..A4` set `parent_key = "VG:WORK:SV:KAU"` — a `work_id`, not a passage
  `canonical_key`. Measured that Rigveda (10), Yajurveda (4) and Atharvaveda (10) all use
  `parent_key = null` at depth 1, so Samaveda was the sole divergence. Agent B's own gate had
  scored this PASS because it admitted `work_id` into its known-keys set. Now `null`.
- **SV-2** (344 of 378 issues): `sources.jsonl` and `source_artifacts.jsonl` were absent
  entirely while 102 text records pointed at source id `GRETIL`. Now emitted, read from the
  registries, and the builder **raises** if a referenced id is unregistered — so a dangling
  provenance pointer is now a build failure rather than a QA finding.

After the fixes: 378 -> **26 issues, 0 ERRORs**. The 20 INFO are the declared-absent-zero
records working as designed; the 6 WARNINGs are declared sample gaps.

G04 note: 12 of 37 parents show gaps, and this is **correct**. Agent B computes
`sequence_in_parent` over the whole 1,868-verse corpus rather than within the sampled build,
so a sampled pilot shows gaps by construction and those gaps are the true source positions. A
corpus-stable sequence is the better property and the gate reports it as gaps rather than
failing it.

G07 is `NOT_APPLICABLE`, not PASSED: the artifact is IAST-romanized with zero tone marks
anywhere (verified — 0 occurrences of U+0951–U+0954, the whole U+1CD0–U+1CFF block, U+030D and
U+0331), and its upstream says accents were dropped. `text_original == text_nfc` here is
faithful preservation, not stripping. Reporting PASSED would have been a vacuous pass.

> **CORRECTION, 2026-09-07, by the `SAMAVEDA_CANONICAL_IDENTITY_FINAL_CLOSURE` run.** This
> paragraph previously read: *"Samaveda identity is **PROVISIONAL**, not FINAL: `key_pattern` is
> now set and `identity_status` moved `RESEARCH_REQUIRED -> PROVISIONAL` …"*
> **That claim was never true.** `git log --all -S PROVISIONAL -- data/registry/works.yaml`
> returns nothing: no such state has existed in any commit. It was not a stale record of a
> change later reverted — it was false when written, and it survived because
> `docs/qa/STALE_FOUR_VEDA_CLAIMS.md` **certified the absence of exactly this claim** while it
> was live in this file, inside that audit's own declared scope.

Samaveda identity is **`RESEARCH_REQUIRED`**, and `key_pattern` is **`null`** — the values in
`data/registry/works.yaml`, asserted by `tests/unit/test_registry.py`. `sv_mantra_identity` and
`sv_container_identity` produce **candidate** keys only, and this report should be read that way.

Identity remains unfrozen, but **not** for the reason this paragraph used to give. The
source-edition question was settled in the 2026-09-07 closure run and shown *not* to be the
binding constraint; the real blockers are **referent integrity** (7 collided addresses, 1 phantom
canonical key) and **arcika arity**. See
[`SAMAVEDA_CANONICAL_IDENTITY_FINAL_CLOSURE.md`](SAMAVEDA_CANONICAL_IDENTITY_FINAL_CLOSURE.md).

### 5.3 Yajurveda — 2 levels, the decisive case

**`validate_corpus` returns 0 issues.** This is the strongest single result in this report:
before the fix in §3.1(a) it raised `KeyError: 'mandala'` and could not produce a verdict at
all. Vajasaneyi is the first non-Rigvedic corpus to pass the shared gate, and it does so
cleanly — 140 passages, 4 parents, 0 gaps, 0 duplicate sequences, 271 text records all
NFC-stable, 135 accented records with 0 lost tone marks.

Agent C's build script calls `validate_corpus` first and prints whatever it actually does,
including the exception if it raises. That was written when the gate would still have crashed
and is worth keeping as a second opinion.

### 5.4 Atharvaveda — the one remaining ERROR cause

761 -> **14 issues** after Agent D emitted `sources.jsonl` (2 records) and
`source_artifacts.jsonl` (3 records), each pinned to a snapshot SHA-256 with its verbatim
licence.

The residual 13 ERRORs have a single cause, isolated precisely: 13 `source_assertions`
declare `source_id = "VEDAGRAPH"` — VedaGraph's own derived observations — and there is no
`Source` record for `VEDAGRAPH` in the build.

```
Source records present:            ['GRETIL_AVS', 'VEDAWEB_AVS']
source_ids used by assertions:     {'GRETIL_AVS': 172, 'VEDAGRAPH': 13, 'VEDAWEB_AVS': 1}
UNRESOLVED:                        ['VEDAGRAPH']
```

This is a real defect, not a false positive: an assertion about the corpus still has to point
at a declared source, even when the asserter is VedaGraph itself. Fix is either to register a
`VEDAGRAPH` self-source or to carry these as a record type that does not require one. Left as
FAILED rather than waived.

The 6 parents with gaps are Agent D's four declared source divergences (AVS 9.6.49, 12.5.1,
13.4.1, and the 20.96.22 edition split). **None were filled.** One is independently
corroborated: VedaWeb's Whitney layer numbers AVS 13.4 as stanzas 1..56 *including* a verse 1,
while the GRETIL artifact mislabels that verse as 26 — a second editor of the same lineage
confirming the gap, independent of the artifact's own marker.

G01 passing is a meaningful result here: Agent D kept one AVS 20.96.22 under the canonical key
and recorded the other as an explicit divergence, so a genuine edition-order collision did not
become a duplicate key.

### 5.5 G11 and G12: two provenance gates the structural gates were blind to

Both added late in the session — G11 on Agent D's suggestion, G12 because Agent D made the
necessary data machine-readable. **G11 immediately found a real defect that all seven
structural gates missed.**

**G11 — Yajurveda FAILED.** The release claims two artifacts the source registry does not
declare:

```
WIKISOURCE.SA.VSM.MADHYANDINA.WIKITEXT   not in data/registry/source_artifacts.yaml
WIKISOURCE.SA.VSM.RISHI.INDEX            not in data/registry/source_artifacts.yaml
2 of 2 artifacts carry no checksum_sha256, in either the release or the registry
```

Yajurveda passes all seven structural gates, returns `validate_corpus` 0 issues, and its 44
raw snapshots are byte-intact — yet its provenance is unverifiable, because nothing
adjudicated the rights of the ids it names. This is exactly the failure mode Agent D
predicted: *a release whose provenance is a fiction while every one of the other gates
passes.*

The registry does hold those artifacts under different ids — note the separator,
`WIKISOURCE_SA` versus the release's `WIKISOURCE.SA`. Almost certainly
`WIKISOURCE_SA.YV.VSM.SAMHITA.DEVANAGARI` and `WIKISOURCE_SA.YV.VSM.RISHISUCI`. Reported to
Agent C, with the mapping to be confirmed by Agent E, who owns the registry.

**This is the third instance of one shared assumption**, which is why it belongs here as a
pattern and not as three unrelated defects: Samaveda shipped no `sources.jsonl` at all;
Atharvaveda first shipped locally-invented ids `GRETIL_AVS`/`VEDAWEB_AVS`, which Agent E
overruled because those files are further *artifacts* of the already-registered `GRETIL` and
`VEDAWEB` and inventing a source put the rights at the wrong level; Yajurveda names
unregistered ids. The settled answer is **reference `data/registry` via
`load_source_artifacts()`, construct nothing locally.** Agent D's evidence for why this is not
pedantry is concrete: VedaWeb's AVS Sanskrit resource carries the TITUS no-republication
clause while its Whitney resource returns a null licence — same host, opposite verdicts.

**G11's three legs, none subsuming another.** Agent E drew the distinction that matters:
verifying bytes against their *own* recorded digest passes happily on a snapshot that is
internally consistent but which the registry points at wrongly. G11 therefore checks (a) the
id is registered, (b) release and registry checksums agree, and (c) where the snapshot is
retained content-addressed, those exact bytes are on disk and hash correctly. A snapshot not
retained locally is reported INFO — unverifiable, not failed — because not retaining it is a
legitimate choice. Result: all 15 checksummed artifacts across the four releases had their
pinned bytes found and intact.

Separately, `verify_content_addressed_snapshots` over `data/raw`: **1,347 content-addressed
snapshots checked, 0 corrupt.**

A hole closed in this agent's own check: the case where *exactly one* side states a checksum
was being silently skipped. There are no such artifacts today (measured: 0), but an implicit
branch would have let a future one-sided checksum pass unnoticed — which is the failure this
gate exists to prevent. It now reports a WARNING and is pinned by test.

**G12 — Atharvaveda PASSED, the other three NOT_APPLICABLE.** `ingest/fetcher/http.py` derives
three things from a single argument — the raw directory, the `snapshot_id` prefix, and the
`source_id` written into the metadata sidecar — so a build cannot get a per-Veda raw directory
without also changing its recorded provenance. Agent D therefore keeps
`data/raw/gretil_avs/` with `snapshot_id` prefix `GRETIL_AVS` while the records correctly say
`GRETIL`, and published the mapping as `SNAPSHOT_NAMESPACE_RESOLVES_TO_SOURCE` assertions.

G12 resolves the join through those assertions rather than asserting bare equality (which
would fail on a legitimate namespace) or tolerating a suffix (which would also accept a typo).
The other three releases declare no namespace remapping, so they report NOT_APPLICABLE — not a
vacuous pass. The underlying fetcher coupling is filed as a contract request; no agent in this
session owns that file.

### 5.6 Four more provenance gates, and the pattern they exposed

G11 was added on Agent D's suggestion; G11b, G13 and G14 followed from peer review of G11
itself. Together they found defects in **all three pilots** that the seven structural gates
and `validate_corpus` all passed. This is the strongest evidence in the report that structural
correctness and provenance correctness are different properties.

**Yajurveda's G11 failure is FIXED, and the root cause was worse than the symptom.** Agent C
confirmed the id mapping (`WIKISOURCE.SA.*` to `WIKISOURCE_SA.*`) and found that the builder
had been *constructing* `Source` and `SourceArtifact` records locally, `rights_status`
included — asserting rights at a level the rights authority never adjudicated, which is
exactly the shape Agent E overruled Agent D for. The builder now calls `load_sources()` /
`load_source_artifacts()` and **raises** on an unknown id. All 44 snapshots were re-fetched
under the registered source id and **every sha256 came back identical**, confirming the bytes
were never the problem — only the id contract was. G11 for Yajurveda: **FAILED / 2 ERRORs to
PASSED_WITH_WARNINGS.**

**G11b — Agent C's critique of my own check, and it was correct.** *Matching some snapshot is
not verification.* The registry pins `WIKISOURCE_SA.YV.VSM.SAMHITA.DEVANAGARI` to the sha256
of the work's **preface and table of contents**, not its samhita text. Those bytes exist, are
intact, and hash correctly — so my byte-level leg passed while verifying nothing about scope.
I implemented C's suggested rule by resolving the pinned checksum back to its snapshot's own
`retrieval_url` and reducing both sides to page identity:

```
WIKISOURCE_SA.YV.VSM.SAMHITA.DEVANAGARI
  declared page : the samhita
  pinned bytes  : the same work's preface + table of contents
  -> ERROR: the checksum matches a real snapshot of the wrong thing
```

The reduction matters: a human wiki URL and its `api.php` equivalent name the same page and
must not be flagged. Measured over the real tree — **26 artifacts agree, 1 is the genuine
preface mispin, 1 is a same-page-different-access case the reduction correctly does not
flag.** Without that reduction the second case would have been a false positive. The registry
fix is Agent E's; reported.

**G13 — Agent D scoped this from a bug that made 92 percent of its own provenance invisible.**
A build listed 2 of the 25 snapshots it had actually read, and every gate passed, including
D's own, because nothing compared the manifest against the raw tree. G13 checks both
directions, and the reverse direction is the one that catches under-reporting:

```
Yajurveda    data/raw/wikisource_sa holds 47 snapshots; manifest lists 41     ->  6 unlisted
             (was 5 listed / 42 unlisted before Agent C closed the gap)
Rigveda      gretil 3/1, vedaweb 11/10, wikisource_griffith_rv 1245/1241      ->  7 unlisted
Samaveda     gretil 3/1                                                       ->  2 unlisted
Atharvaveda  25 listed, 25 present                                            -> PASSED
```

G13 found a real defect in Yajurveda beyond the count: its headline structural claim
(40 adhyāyas, 1,975 mantras) was computed by the adapter but lived only in a report, so the
release could not verify its own most important number. Agent C now reads all 40 adhyāya
snapshots and emits 41 work-scoped reconciliation assertions; `source_snapshot_ids` went
**5 to 41**. Atharvaveda passing is Agent D having fixed the same class on its own build.

**The reverse leg can never reach parity, and Agent C proved why rather than assuming.** Of
the 6 snapshots still unlisted under `data/raw/wikisource_sa/`, **3 are Agent B's Samaveda
fetches** — Samaveda and Yajurveda share the source id `WIKISOURCE_SA`, so one raw directory
holds two Vedas' traffic. A raw directory is genuinely shared and no single manifest can cover
it, which is why this leg is a WARNING and not an ERROR.

That made a bare count actively misleading, so the check now **shows its working**: it reports
the retrieval URL of every unlisted snapshot where a sidecar exists. Verified against the real
tree — 3 of the 6 URLs decode to `सामवेद…` (Samaveda), making the cross-traffic visibly
attributable instead of indistinguishable from under-reporting. Agent C's suggestion to filter
by plausible readability was the alternative; showing evidence was preferred over a heuristic
that could hide a genuine omission.

**G14 — Agent C found a fourth instance of the same assumption, one level below G11.**
`TextVersionDescriptor`'s own docstring states that rights, lineage and permitted VedaGraph
role attach to the version descriptor. `data/registry/text_versions.yaml` declares 7
descriptors and **all 7 are Rigvedic**, so every version id in all three new-Veda pilots is
unregistered:

```
Samaveda      GRETIL.SV.KAUTHUMA                  102 records
Yajurveda     WIKISOURCE_SA.YV.VSM.ACCENTED       135 records
              WIKISOURCE_SA.YV.VSM.UNACCENTED     136 records   (renamed from ...SAMHITA)
Atharvaveda   GRETIL.AVS.SAUNAKA.ACCENTED         153 records
              GRETIL.AVS.SAUNAKA.UNACCENTED       153 records
              VEDAGRAPH.AVS.SEARCH_NORMALIZED     153 records
Rigveda       none - all ids registered
```

**832 records across three Vedas carried a rights-bearing version id nobody had adjudicated.** **Now FIXED**: Agent E grew `text_versions.yaml` from 7 descriptors to 13, registering all six, and G14 passes for all four Vedas — verified as real registration rather than a silent skip by confirming every id still present in every release now resolves. (Yajurveda also renamed `…VSM.SAMHITA` to `…VSM.UNACCENTED` in the process.) A
record with no `text_version_id` is skipped rather than guessed about: not every text is a
distinguishable *version*, and inventing an id there would be the same mistake in the opposite
direction.


**A second latent hole in my own check, caught the same way.** When the wrong-scope checksum
in §5.6 was later **removed** rather than corrected, `verify_checksum_scope` lost its input
and reported PASSED — a skip wearing a pass. That is the exact failure this report's own
reading rule forbids. Fixed: every artifact whose scope could not be checked is now reported
as INFO, and the gate distinguishes four outcomes rather than two — `PASSED` (all verified),
`PARTIAL` (some unverifiable), `NOT_VERIFIED` (none verifiable), `FAILED` (a real mismatch).
The honest current state is therefore **PARTIAL** for Rigveda (12 of 14 artifacts' scope
verified) and **PARTIAL** for Yajurveda (1 of 2), not PASSED. Pinned by test.

Worth stating as a general lesson from three instances in one session: the one-sided-checksum
branch, this scope skip, and the earlier `KeyError` crash were all cases where *absence of a
signal* was being read as *absence of a problem*. A gate has to make "I could not check this"
structurally different from "I checked this and it was fine".

**The pattern.** This is one underspecified contract surfacing in four places — Samaveda
shipping no `sources.jsonl`; Atharvaveda inventing `GRETIL_AVS`/`VEDAWEB_AVS` source ids;
Yajurveda naming unregistered artifact ids while locally constructing rights; and all three
naming unregistered version ids. Agent D's framing is the one worth recording: three agents
hitting one assumption with three different surface presentations is evidence the contract was
underspecified, not that three agents were careless. The settled answer is **reference
`data/registry`, construct nothing locally, and fail the build on an unknown id.**

**A latent hole in my own check went live within the session.** I closed the
one-sided-checksum branch when there were **0** instances. There are now **3** — two in
Yajurveda (release-only and registry-only) and one in Atharvaveda, the last because Agent D
handed Agent E a hash that E pinned before D's release stated it. Had the branch stayed
implicit, all three would have passed silently.


### 5.7 G15, and a corpus fact worth recording

**G15 `text_role_matches_registry`.** Agent E raised a live disagreement, relayed by Agent A:
a pilot emitted `PRIMARY_TEXT` for a layer the registry had deliberately registered as
`EXTRACTED_FROM_CONTAINER`. `TextRole` is a permission statement — it says what VedaGraph may
do with a reading — so choosing one in build code is the same defect class as constructing a
`SourceArtifact` locally.

Agent A reported that the check *would currently fire*. By the time it was implemented and
measured, it did not: Agent C had already fixed it at the root, reading roles from
`load_text_versions()` with an unregistered id falling back to `COMPARISON_ONLY` — the most
restrictive option, never a permissive one. Measured result: **0 disagreements across 21,936
text records and 13 registered descriptors.**

Kept as a standing check anyway, and the distinction from the `SectionDiscoveryRecord`
reconciliation left unwired in §3.2 is deliberate: that one has **no records at all**, so
wiring it would report a vacuous pass, whereas this one has 21,936 real inputs. A green result
here is a measurement, and it guards a regression that has already happened once.

**A corpus fact that fell out of the role ruling: the Vājasaneyi Saṃhitā has no
`PRIMARY_TEXT` layer.** This is not a defect in the build, it is a property of the available
sources, and it belongs in a QA report because a downstream consumer will otherwise assume one
exists:

| Layer | Registered role | Limitation |
| --- | --- | --- |
| `WIKISOURCE_SA.YV.VSM.UNACCENTED` | `PARALLEL_TEXT` | faithful but **incomplete — 1,836 of 1,975 mantras** |
| `WIKISOURCE_SA.YV.VSM.ACCENTED` | `EXTRACTED_FROM_CONTAINER` | complete (1,958) but extraction-derived |

No layer is both faithful and complete. The decisive evidence was Agent C's own `NEEDS_REVIEW`
assertion that VSM 16.37 prints two attested readings while the layer keeps one — a critical
decision no structural argument reaches. Agent C's build now reports
`has_primary_text_layer: NO` and renamed its config field `primary_text_version` to
`leading_text_version` so it stops implying a role it never had.

Per-Veda primary-text availability, for the record: Rigveda **yes**
(`GRETIL.RV.AUFRECHT`); Samaveda **yes** (`GRETIL.SV.KAUTHUMA`); Atharvaveda **yes**
(`GRETIL.AVS.SAUNAKA.ACCENTED`); Yajurveda **NO**.

## 6. G05 source-count reconciliation — mostly NOT_RUN, and why

`PASSED` for Rigveda: 2,247 `SuktaDiscoveryRecord`s reconcile GRETIL's stated per-sūkta mantra
counts against the ingested counts, via `expected_vs_canonical_mantra_count`.

`NOT_RUN` for all three pilots. This is a gate gap, not a pass, and the reason is the same in
each case: **none of the three artifacts states a total of its own to reconcile against.** All
three agents computed counts and exposed them machine-readably, and all three declined to
reconcile against a textbook figure, which is the right call:

| Veda | Artifact-stated total | Computed | Divergence |
| --- | --- | --- | --- |
| Samaveda | 1,875 (terminal running number) | 1,868 distinct structural keys from 3,714 lines | 7 unreconciled; running number itself defective — 1,871 printed, 1,870 distinct, 5 absent, 1 duplicated, runs backwards once |
| Yajurveda | none | 40 adhyāyas, 1,975 mantras (union of both layers) | TITUS 1,974; Vedic Heritage 1,974 — recorded as divergence, not error |
| Atharvaveda | none — verified programmatically, `stated_total_counts` returns empty | 20 kāṇḍas, 731 sūktas, 5,839 distinct triples | **four** counts in one lineage: 5,839/5,843, VedaWeb 5,842, TITUS 5,919, literature ~5,977 |

Generalising the reconciliation onto `SectionDiscoveryRecord` is the correct fix and is
deliberately not done yet (§3.2): no build emits those records, so the check would report a
vacuous pass. When a pilot ships them, that is the moment.

## 7. G09 normalization determinism — PASSED, measured

`data/qa/four_veda_normalization_determinism_run{1,2}.tsv` hold the SHA-256 of every derived
surface for 9 inputs × 11 stages, produced by two **separate OS processes** (pids 22180 and
11716) with `PYTHONHASHSEED` deliberately unset so that any dependence on set or dict
iteration order would surface as a differing digest.

```
diff run1 run2 (excluding the pid banner)  ->  no differences
```

Per-record idempotency over every derived surface, all four builds: **0 non-idempotent of
21,936 records.** Two genuine non-idempotency defects were found on whole-file input and one
was fixed; see `FOUR_VEDA_NORMALIZATION_POLICY.md` §6.2.

## 8. G10 byte-identical rebuild — actual results

Independently re-run by this agent, not taken on report. Method: hash every file in the build
directory, re-run the owning agent's build script in a fresh process, re-hash, diff.

| Veda | Result | Files | Command |
| --- | --- | --- | --- |
| Samaveda | **PASSED — byte-identical** | 9 | `scripts/build_samaveda_pilot.py data/builds/samaveda_pilot_v1.yaml` |
| Yajurveda | **PASSED — byte-identical** | 12 | `scripts/build_yajurveda_pilot.py` |
| Atharvaveda | **PASSED — byte-identical** | 14 | `scripts/build_atharvaveda_pilot.py` |
| Rigveda | **NOT_RUN** | — | full-corpus rebuild not attempted in this session; the 16-file SHA-256 fingerprint in §4.1 is unchanged, which is a weaker claim than a rebuild |

Honesty note on method: the first Atharvaveda attempt was invoked with a config argument the
script does not accept, exited 2, and produced **no rebuild at all** — at which point the hash
diff was trivially empty. Reporting that as PASSED would have been exactly the vacuous pass
this gate exists to prevent. It was re-run correctly (exit 0) and only then compared.

**Line-ending caveat, checked rather than assumed.** This repo has mixed CRLF/LF, which can
make a byte-identical check fail spuriously. All 16 Rigveda data files are pure LF (0 CRLF
lines) and no rebuild diff was attributable to line-ending drift. Separately,
`src/vedagraph/qa/checks.py` is uniformly CRLF, so every edit to it was applied by
normalizing to LF, editing, and restoring CRLF; `git diff --stat` after each edit confirmed a
surgical change (final: 182 insertions, 19 deletions on a 480-line file) rather than a
whole-file reformat.

**Method note, because Agent C correctly asked.** These rebuilds were run **across
invocations**, not twice inside one process: the build script was launched as a separate OS
process and the directory hashed before and after. That matters, because Agent C hit a drift
class that within-process rebuilding cannot see — `ruff format` re-flowed an
implicitly-concatenated string literal in a builder, and that string ends up inside a record
field, so `generated_content_sha256` moved between invocations while a within-run rebuild
stayed byte-identical. A gate that rebuilds twice in one process has that blind spot; this one
does not.

**A real caveat from Agent B worth recording:** an earlier pair of Samaveda runs *did* differ
on `passages.jsonl`, and the cause was not the builder — Agent A landed `native_labels` and
`structural_path` on `Passage` between the two runs. A mid-flight contract change is
indistinguishable from a determinism failure in this gate. Any G10 failure should be checked
against concurrent contract activity before being called non-determinism.

## 9. Test suite

See §12. Baseline reconciliation is in §4.4.

One transient result must be discounted explicitly. A full-suite run launched while Agent A
was mid-edit reported 11 failed / 581 passed / 2 skipped, including 5 failures in
`tests/unit/test_qa.py`. Re-running those same files immediately afterwards on the settled
tree gave **44/44 passed** (`test_qa.py`, `test_four_veda_contracts.py`, `test_registry.py`,
`test_models.py`). The 11 failures were an artifact of reading partially-written shared
contract files, not a regression. The clean number is reported in §12.

A related environment hazard, diagnosed rather than worked around: scripts run from the shared
session scratchpad intermittently failed with
`ImportError: cannot import name 'AnyHttpUrl' from 'pydantic'`. Cause: the scratchpad is
shared by all agents in this session and contained another agent's `struct.py`, which shadows
the standard library `struct` module for any script whose `sys.path[0]` is that directory.
Not a repo defect. Fixed by working from an isolated subdirectory.

## 10. Open defects, by owner

| # | Defect | Owner | Status |
| --- | --- | --- | --- |
| 1 | 13 Atharvaveda `source_assertions` reference unregistered source id `VEDAGRAPH` | Agent D / Agent E | **OPEN** — only ERROR cause left |
| 2 | `TRANSCRIPTION_EQUIVALENCES` has 0 of 11 rules touching Devanagari; causes 132/135 Yajurveda UNCLASSIFIED. Needs a notation-aware fold taking a scheme argument | Agent F (needs contract change) | **OPEN, documented** |
| 3 | `compare/run.py` config model is Rigveda-only; cannot express a 2-level or 5-level comparison | comparison layer | **OPEN, documented** |
| 4 | Count reconciliation not generalised onto `SectionDiscoveryRecord` | Agent F | **DEFERRED on purpose** — no build emits them; would be a vacuous pass |
| 5 | Lateral fold merges vocalic l with retroflex l on the search surface | Agent F | **WON'T FIX** — proved unfixable by a global table; measured and documented |
| 6 | `("cch","ch")` fold is non-idempotent for runs of 3+ `c` | Agent F | **documented**; no canonical record affected |
| 7 | `entity_type` no longer identifies which level a Samaveda passage occupies | Agent A | raised for the structural-model doc |
| 8 | Whether `0` or an omitted key is the canonical representation of an absent level | Agent A | raised; gate currently accepts `0` and surfaces it as INFO |
| 10 | ~~Yajurveda claims 2 unregistered artifact ids~~ | Agent C | **FIXED** — builder now loads from the registry and raises on unknown ids; all 44 snapshots re-fetched with identical hashes |
| 13 | Registry pinned the preface page's sha256 for the Yajurveda samhita artifact — a real snapshot of the wrong scope (§5.6) | Agent E | **PARTLY CLOSED** — the bad checksum was removed rather than corrected, so the artifact is now unverifiable (G11b PARTIAL) rather than wrong. A correct checksum is still needed |
| 14 | ~~832 records declare unregistered rights-bearing `text_version_id`s~~ | Agent E | **FIXED** — registry grown 7 to 13 descriptors; G14 passes on all four, verified as real registration not a skip |
| 15 | Manifests under-report snapshots actually read: Yajurveda lists 5 of 47, Rigveda 7 unlisted, Samaveda 2 (§5.6) | B / C, and Rigveda's own build | **OPEN** — found by G13 |
| 16 | 2 Yajurveda + 1 Atharvaveda artifacts state a checksum on exactly one side (release or registry, not both) | Agent E + C/D | **OPEN**, reported as WARNING |
| 17 | ~~`vedagraph schema export` translates line endings, breaking frozen-hash claims with zero content change~~ | Agent A | **FIXED** — exporter now preserves each file's EOL and skips no-op writes; proven idempotent over two consecutive exports, 0 drift across 28 schemas |
| 18 | `schema export` output is not platform-independent: it now matches whatever EOL the existing file uses, so a generator whose output is hashed can still differ across platforms. A `.gitattributes` pinning `schemas/*.json` is the proper fix and is deliberately deferred as repo-wide (§12.3) | coordinator | **OPEN** |
| 11 | `ingest/fetcher/http.py` derives raw directory, `snapshot_id` prefix and recorded `source_id` from one argument, so per-Veda raw storage cannot be had without corrupting recorded provenance | unowned — contract request | **OPEN**, worked around by G12 |
| 12 | 3 artifacts across Rigveda and Atharvaveda declare no checksum in either the release or the registry, so their bytes cannot be verified | Agent E | **OPEN**, reported as WARNING not waived |
| 9 | **Comparison output is versioned against the comparator but not against the normalizer.** `comparison_version` stayed `text-compare-v1` while this session's Devanagari fold changed `text_comparisons.jsonl` content and `generated_content_sha256`. Any future `normalize/` change silently moves comparison hashes with no version string moving. Wants a `normalization_version` alongside `comparison_version` | Agent A (`models/core.py` field) | **OPEN** — found by Agent C, confirmed here |

Fixed during the session: Samaveda SV-1 and SV-2 (Agent B), Atharvaveda empty `sources.jsonl`
(Agent D), the `validate_corpus` crash and the three Rigveda-shaped QA assumptions plus my own
false-error regression (Agent F), the udātta U+032D accent gap, the search-surface
non-idempotency, and the Latin-only fold (Agent F), and the sealed semantic schema recovered
from a dangling blob (Agent A).

The Devanagari fold result was **independently reproduced by Agent C** on the Vājasaneyi pilot
— UNCLASSIFIED 132 → 116, SANDHI_OR_SEGMENTATION 2 → 13, ACCENT_ONLY 1 → 6, with both
individual folds (visarga-vs-colon, and the two anusvāra spellings) verified directly rather
than inferred from the aggregate, and nothing moving the wrong way. Agent C also confirms the
residual 116 are editorial rather than encoding: the two Wikisource layers digitise the same
1929 Nirṇaya Sāgara print under different segmentation conventions, so `UNCLASSIFIED` is the
correct answer and a sandhi-aware alignment — not more normalization — is what the residual
would need.

## 11. Reproducibility

```
# the whole gate, all four builds, machine-readable
PYTHONIOENCODING=utf-8 ./.venv/Scripts/python.exe <run_all>
#   -> data/qa/four_veda_gate_results.json

# Rigveda baseline fingerprint (captured at git HEAD 4da5bd7 before contract changes landed)
#   -> data/qa/four_veda_rigveda_baseline.json      16 files, sha256 + byte + line counts

# cross-process normalization determinism (run twice, diff)
#   -> data/qa/four_veda_normalization_determinism_run{1,2}.tsv

# regression tests
./.venv/Scripts/python.exe -m pytest tests/unit/test_four_veda_qa_gate.py -q     # 28 passed

# byte-identical rebuilds (§8)
./.venv/Scripts/python.exe scripts/build_samaveda_pilot.py data/builds/samaveda_pilot_v1.yaml
./.venv/Scripts/python.exe scripts/build_yajurveda_pilot.py
./.venv/Scripts/python.exe scripts/build_atharvaveda_pilot.py
```

Environment: `./.venv/Scripts/python.exe`, Python 3.12.1, win32, pydantic 2.13.5.
Namespace UUID `7c8cde94-2bc0-50e2-8819-568ae65a3ec4` — permanent.
`PYTHONHASHSEED` is intentionally left unset in the determinism probe.

## 12. Test suite result

Final run on the settled tree:

```
681 passed, 2 skipped in 147.01s      (0 failed)
```

The suite is **green**, including this agent's 57 new gate tests. It briefly showed
`1 failed, 673 passed` mid-session from pure line-ending drift in a schema this agent does
not own; that is diagnosed in §12.3 and has since been restored. It was never four-Veda
fallout and never a content change.

The 2 skips are expected and pre-existing (live-VHP crawl, `openai` not installed). The suite
is **green**, including this agent's 28 new gate tests. Agent A's pre-change green baseline
was 592 passed / 2 skipped / 0 failed; the tree has since grown by Agent A's contract tests
and this agent's 28.

The briefed baseline of "~189 passed, 1 skipped" was wrong and is not reconcilable with any
measurement of this tree; the coordinator has since retracted it.

Targeted regression suites for this work:

```
tests/unit/test_four_veda_qa_gate.py                                      28 passed
tests/unit/test_qa.py                                                      6 passed
+ test_four_veda_contracts.py + test_registry.py + test_models.py         72 passed total
ruff check   (E,F,I,B,UP,RUF)  on all three changed files                 All checks passed
ruff format --check            on all three changed files                already formatted
```

### 12.1 A sealed-artifact regression, caught, escalated, and repaired

Recorded in full because the underlying provenance defects survive the repair.

**What happened.** During this session a full-suite run showed 4 failures, all resolving to
one file: `schemas/semantic_extraction_v3.schema.json` had drifted from the hash sealed by the
frozen v3.2 448-mantra run.

```
sealed  sha256  26e554c4714bee14835534e27df02aca13d3fd1c3c7d0cb951e5984dc32820f2
drifted sha256  4eb239128f80013c8cfff210448a38a21d5b33cceedba9e2eea95e7c55907923
observable      $defs.Explicitness.enum had become ['EXPLICIT','STRONG_INFERENCE','INTERPRETIVE'];
                the v3 execution schema is specified to refuse INTERPRETIVE
```

**Cause, as established by Agent A.** `"semantic_extraction_v3.schema.json"` was an entry in
`SCHEMA_MODELS`, and `export_schemas()` writes every entry unconditionally, so
`vedagraph schema export` — run three times while landing the four-Veda contracts — overwrote
the hand-narrowed sealed artifact with a faithful export of the current model, readmitting
`INTERPRETIVE`. It did **not** pre-date the session: Agent A's pre-change baseline was 592
passed / 2 skipped / **0 failed**.

**Repaired.** Agent A recovered the exact sealed bytes from a **dangling git blob**
(`f11810eb09aa3ef3fbb1d1b107542b59cdc2460e`, 14,042 bytes), found by sha256-hashing all 725
git objects — bytes that `git show` and `git checkout` both fail to produce because the file
is untracked. Independently verified here after the restore: on-disk sha256 is
`26e554c4…`, matching `input_freeze.json`; `$defs.Explicitness.enum` is back to
`['EXPLICIT','STRONG_INFERENCE']`; the suite is green. The 448-run byte-identity claim is
intact.

**Correction to this report's own earlier reading.** An earlier revision recorded the drift as
possibly pre-existing and the sealed bytes as apparently unrecoverable. Both were wrong. The
`4eb23912…` measurement was accurate for the moment it was taken (before the restore); the
inference drawn from it was not. Two things misled it: `schema.py:119` now carries a comment
saying the file is deliberately not exported, which is the *fix* Agent A added after
diagnosing the problem rather than evidence that the export path was innocent; and
`INTERPRETIVE` is absent from `src/vedagraph/models/semantic.py` but present in the
`Explicitness` enum in `src/vedagraph/semantic/ontology.py` — two different artifacts sharing
a name.

**Not caused by this agent's changes, which was checked rather than assumed.** The only source
files changed here are `src/vedagraph/qa/checks.py` and `src/vedagraph/normalize/unicode.py`.
Neither appeared in any of the four tracebacks. `src/vedagraph/semantic/*` is frozen and was
not touched.

### 12.1.1 Two inherited provenance defects that outlive the repair

These are the durable findings and they are not four-Veda fallout.

1. **A sealed artifact was never version-controlled.** The sha256 of
   `schemas/semantic_extraction_v3.schema.json` is asserted in `input_freeze.json`,
   `output_seal.json` and all 448 response files, yet the file is untracked by git. Its
   survival through this incident depended entirely on a dangling blob that `git gc` would
   eventually have collected. **Recommend committing it.** An artifact whose hash is load-
   bearing in 450 places must be under version control.
2. **`SCHEMA_MODELS` presented a hand-narrowed file as a generated export.** It cannot be one:
   the model's `Explicitness` admits `INTERPRETIVE` and `normalization.py` refuses it at
   runtime instead of narrowing the type, so the sealed schema could never be a faithful
   export of its own model. Listing it made `vedagraph schema export` a **destructive
   command** for anyone who ran it. Agent A has removed the entry and verified the export now
   leaves that file's sha256 untouched (50 schemas exported, not 51).

A useful technique worth recording: `git cat-file --batch-all-objects --batch-check` plus a
content re-hash recovers bytes that `git checkout` and `git show` cannot, because a file that
was ever `git add`ed leaves a blob behind even if it was never committed and is now untracked.

### 12.3 The one failure is line-ending drift, not content drift

`tests/unit/test_semantic_full_run.py::test_the_preserved_v3_1_draft_freeze_detects_the_v3_2_contract_change`
fails because its drift list gained one unexpected entry,
`schemas/semantic_evidence_packet.schema.json`.

**The content did not change. Only the line endings did.**

```
HEAD          9,011 bytes  373 lines  LF
working tree  9,384 bytes  373 lines  CRLF
9,384 - 9,011 = 373 = exactly one extra CR per line
EOL-normalized sha256, both sides: a9de6e8086074ab2c13a0df9fef23ae2...   IDENTICAL
```

The frozen-hash test compares raw sha256, so a pure CRLF rewrite is indistinguishable from
real drift to it. This is precisely the failure mode this agent was warned to diagnose
explicitly rather than report as a determinism failure, and it is worth stating plainly: a
byte-identical-rebuild check on a mixed-line-ending repo can fail while nothing has changed.

**It is systemic, not a one-off.** Checking the whole `schemas/` directory rather than only
the failing file:

```
EOL-DRIFT-ONLY, content identical, HEAD=LF -> working tree=CRLF:
  semantic_assertion_candidate.schema.json
  semantic_entity_candidate.schema.json
  semantic_evidence_packet.schema.json
  semantic_run_manifest.schema.json
  semantic_validation_result.schema.json

REAL content changes (expected - Agent A's four-Veda contract additions):
  audio_recording, corpus_build_config, passage, source, source_artifact,
  text_version, translation
```

Only `semantic_evidence_packet` happens to sit in that particular freeze list, which is why
exactly one test failed rather than five. The other four are latent.

**Root cause.** `vedagraph schema export` translated line endings on write, so the command
was destructive to frozen-hash claims *even when it changed nothing*. There is no
`.gitattributes` in the repo and `core.autocrlf` is `false`, so nothing normalized it.
Combined with the `SCHEMA_MODELS` defect in §12.1.1, `schema export` broke the frozen layer
twice by two independent mechanisms.

**A correction to this report's own recommendation.** The fix suggested here was to write with
`newline="\n"`, following `compare/report.py::write_report`. Agent A checked all 28 tracked
schemas and showed that would have been **wrong for this repo**: the 5 drifted files are LF at
HEAD, but the other 23 are **CRLF at HEAD**, so forcing LF would have traded 5 files of drift
for 23 — the same defect in the opposite direction. The suggestion was right in general and
wrong here, and the difference is only visible if you check the committed state rather than
assume one convention.

**FIXED at the root by Agent A**, with two properties rather than a one-off restore: the
exporter now detects each file's existing EOL convention and renders to match, and it does not
write at all when the rendered content already equals what is on disk — so `schema export` is
idempotent at the byte level. Proven by running it twice consecutively and re-auditing all 28
schemas: **0 EOL-drift-only files.** Verified here independently: all 5 files are now
byte-identical to HEAD, and the sealed v3 schema still hashes to `26e554c4…20f2`.

Agent A deliberately did **not** add a `.gitattributes`, on the grounds that it is a repo-wide
file outside its write set which would reclassify the 23 CRLF-at-HEAD schemas and affect files
other agents are mid-flight on. That judgement looks right, and the residual concern is worth
naming: a generator whose output is hashed should produce identical bytes on every platform,
and this one now produces whatever the existing file used. That is cross-platform determinism,
a real but separate issue from the drift that was fixed.

**Not caused by this agent, checked rather than assumed.** The only source files changed here
are `src/vedagraph/qa/checks.py` and `src/vedagraph/normalize/unicode.py`, and neither appears
in any freeze list under `data/semantic/`. Both are line-ending-stable against HEAD:
`checks.py` uniformly CRLF as it was, `unicode.py` uniformly LF as it was, verified after
every edit.

**Recovery is a one-liner and was deliberately left to Agent A**, who owns `schemas/`:

```
git checkout -- schemas/semantic_assertion_candidate.schema.json \
                schemas/semantic_entity_candidate.schema.json \
                schemas/semantic_evidence_packet.schema.json \
                schemas/semantic_run_manifest.schema.json \
                schemas/semantic_validation_result.schema.json
```

Two agents writing the same files is a worse failure than one stale report line, so this was
reported rather than fixed.

### 12.2 Note on the QA artifacts

`data/qa/**` is gitignored (`.gitignore:19`). The four-Veda QA outputs
(`four_veda_gate_results.json`, `four_veda_rigveda_baseline.json`,
`four_veda_normalization_determinism_run{1,2}.tsv`) therefore live in the working tree only
and are not version-controlled. They are regenerable by the commands in §11, but the Rigveda
*baseline* fingerprint is not — it was captured at git HEAD `4da5bd7` before the contract
changes landed and cannot be recreated after the fact. It should be preserved or committed
deliberately if it is to serve as a future regression anchor.
