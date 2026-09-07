# FULL_SV_YV_AV_CANONICAL_INGESTION

Run: `FULL_SV_YV_AV_CANONICAL_INGESTION`
Starting commit: `db1e00f`
Branch: `semantic-pilot-v1`
Date: 2026-09-07
Gate entered under: `FOUR_VEDA_CANONICAL_SANSKRIT_BLOCKERS_CLOSED_WITH_AV_TRANSCRIPTION_WORKLOAD`

This is the first production-scale ingestion after canonical Sanskrit blocker closure. Two
canonical corpora were produced and gated; the third was attempted, measured, and refused.

---

## 0. Starting checkpoint — verified before any write

| Check | Result |
|---|---|
| Branch `semantic-pilot-v1` | yes |
| Working tree clean | yes |
| Sāmaveda referent-integrity repair commit present | `db1e00f` |
| Sāmaveda `identity_status` | `FINAL` |
| Sāmaveda referent drift gate exists and passes | 1,844 / 1,844 `UNCHANGED_REFERENT` |
| Yajurveda blocker | `CLOSED_WITH_REVIEW_ITEM` |
| Atharvaveda PD transcription route | `PD_TRANSCRIPTION_PATH_VALIDATED` |
| Rigveda corpus byte-identical | 193 files, 0 changed, 0 added, 0 removed |
| Baseline test suite | 731 passed, 2 deselected |

---

## 1. What was missing and had to be built first

Two gaps blocked any canonical build, and neither was an administrative detail.

**There was no work-agnostic builder.** `vedagraph.build` reads `config.mandala` and mints
identity through `rv_*_identity`; it is the sealed Rigveda builder and cannot build any
other work. `WorkBuildConfig` declared the shared shape (ADR-018) and had nothing behind
it. `src/vedagraph/release.py` is that core: fail-closed TextVersion selection, the
referent gate wired into the release path, deterministic emission of thirteen record
families, cross-work collision auditing, and orphan-provenance detection.

**Selection failed open.** `build.py` resolves rights with
`rights_by_version.get(id, RightsStatus.UNKNOWN)`. For the Sāmaveda that was concrete, not
theoretical: the Kauthuma adapter stamps `WIKISOURCE_SA.SV.KAU.ARCIKA_MULA` on every row,
that id was unregistered, and the only registered Sāmaveda version was
`GRETIL.SV.KAUTHUMA` — whose licence forbids modification outright. A build that fell
through would have published a corpus derived from an artifact that prohibits the
derivation. `select_primary_text_version` now raises, and refuses a named fallback set by
id so the refusal is a property a test asserts directly.

---

## 2. Sāmaveda — Kauthuma ARCIKA canonical corpus

> **ARCIKA ONLY.** The gāna collections — roughly 2,639 gānas against 1,875 ārcika verses —
> are a parallel and larger body this `work_id` cannot address. `SAMAVEDA_GANA_CORPUS` is
> **not** implied. "Complete Sāmaveda" is never a correct description of this release.

**Selected TextVersion:** `WIKISOURCE_SA.SV.KAU.ARCIKA_MULA` → artifact
`WIKISOURCE_SA.SV.KAU.SAMHITA.DEVANAGARI`, role `PRIMARY_TEXT`, rights `CC_BY_SA`.
Registered this run; the id was **read out of the adapter**, not invented.

**No-GRETIL-fallback proof:** `test_the_build_refuses_to_fall_back_to_gretil_when_the_wikisource_layer_is_absent`
injects a registry with the Sāmaveda entry removed, asserts `GRETIL.SV.KAUTHUMA` is still
present so a fallback is genuinely available, then asserts the build raises
`TextVersionSelectionError`. A companion proves all three Pandey-lineage ids are refused
**by name** before rights or role are even consulted.

| Figure | Value |
|---|---|
| Source occurrences | 1,874 |
| Distinct printed markers | 1,873 |
| Canonical keys | **1,844** (CHANDA 585, ARANYA 55, MAHANAMNYA 10, UTTARA 1,194) |
| Passages emitted | 2,342 (1,844 verses + 498 containers) |
| Withheld | 30 occurrences / 29 distinct printed verses |
| Pūrvārcika group | 650 — exact |

Withheld by reason: `STRUCTURAL_AMBIGUITY` 21, `REFERENT_UNRESOLVED` 9, plus
`SOURCE_NOT_PRINTED` 2 (running numbers 1179, 1315) and `SOURCE_MARKER_ANOMALY` 2.

**Five equations, all balancing, and the build refuses to release if any fails:**

```
1875 = 1873 distinct printed markers + 2 the selected witness does not print
1875 = 1844 minted keys + 29 withheld printed verses + 2 unprinted
1874 candidate occurrences = 1873 distinct printed markers + 1 repeated marker occurrence
1844 minted keys = 1844 distinct printed markers among them (one printed verse each)
1844 minted keys = 585 CHANDA + 55 ARANYA + 10 MAHANAMNYA + 1194 UTTARA
```

The last two exist because the first two balance *automatically* whenever released and
withheld markers partition the printed set — on their own they would survive a released
key that lost its marker, or two keys sharing one. That is the shape of a weld.

**Referent drift:** `UNCHANGED_REFERENT` 1,844, `REFERENT_DRIFT` 0. All 144 ledger rows
belong to `SAMAVEDA_REFERENT_INTEGRITY_REPAIR`, so under run-scoping **zero migrations
license anything in this run** — which is correct and is the point of the scoping.

**Withheld-resolution attempt: 0 resolved, and the reason matters.** Every group was
re-examined against the corroborating witness. Nothing was minted. In the process the
audit's stated *reason* was found to be backwards for three of the four groups: at
`UTTARA:P4:R2:D14`, `P5:R1:D17` and `P5:R2:D5` the **selected** witness prints the daśati
heading and the **second** witness merges or skips it. Only `P4:R1:D22` matches the
originally recorded shape. The withholding is unchanged and remains correct — an
unadjudicated disagreement is not a licence to mint from either witness — but the note
naming the selected witness as defective has been corrected in `works.yaml` and in the
audit script, which now states the measured disagreement instead of an unmeasured cause.

**Accent, measured:** **zero** of the 1,865 minted verse occurrences carry any Vedic accent
or Devanagari-Extended saman mark. The whole pinned corpus holds 1,163 extension
codepoints, but 1,158 sit on **one page** and none falls inside a parsed verse. The
artifact record's claim that this artifact carries "real saman notation" is true of the
artifact and false of every released verse; the new TextVersion records `UNACCENTED` with
the measurement.

**Determinism:** byte-identical across two independent rebuilds.
**Translations:** 0. **Audio:** 0.

---

## 3. Yajurveda — Vājasaneyi Mādhyandina canonical corpus

| Figure | Value |
|---|---|
| Passages | **2,015** (40 adhyāya + 1,975 mantra) |
| Mantra addresses | **1,975 / 1,975** |
| Source-declared units | **1,942** |
| Inference-derived (`EXTRACTED_FROM_CONTAINER` boundary) | **33** |
| Variant-bearing units | **1** (VSM 16.37) |
| Review items | **38** |
| `PRIMARY_TEXT` layer exists | **NO** |

**The role was not upgraded.** The registry registers the accented layer as
`EXTRACTED_FROM_CONTAINER` and the unaccented as `PARALLEL_TEXT`; both are read from the
registry and stamped verbatim. `allowed_roles` is passed explicitly at the selection call
site so the concession is visible where it is made. This work has no primary-text layer,
and that is an honest source property.

**A registry figure was corrected.** It recorded "1939 of 1975 … 36 fall back". There are
exactly 36 `ORDINAL_HEADER_ABSENT` **events**, but three fire on accented commentary prose
that never becomes a record, so the **unit** split is 1,942 / 33. Both numbers are true of
different populations; neither is a correction of the other. Per-record
`ACCENTED_BOUNDARY_PROVENANCE` is now emitted for all 1,975 accented units — the
resolution the registry specified and left unimplemented.

**VSM 16.37:** both printed readings survive. The first is the record; the second is
preserved untruncated as `EDITORIAL_INTERVENTION_SECOND_READING` at `NEEDS_REVIEW`. No
winner chosen, passage identity stays one occurrence, and the other 1,974 addresses are
not blocked by it.

**Ṛṣi metadata: 2,240 assertions, up from 2,185, covering all 40 adhyāyas.** The initial
build left **adhyāya 25 with zero coverage**. Root cause, in
`yajurveda_apparatus.py`: the ṛṣi index separates spec members with a comma, but four
lines drop one and leave two members touching (`२७-३१ ३६`, `२३ २७`), and one line ends in
a bare `*` placeholder. A comma-only split read those as one unreadable member and
discarded the **whole line** — and adhyāya 25 is stated on exactly two such lines. The
split now also breaks on whitespace, with dash-adjacent whitespace collapsed first so
`३८ -६०` stays one range (a naive whitespace split lost that line, which the fix
caught and repaired). Unparsed lines: 5 → 2.

The two that remain unparsed are genuinely ambiguous and stay that way: they state mantra
numbers with **no adhyāya**. Reading them by sort position gives adhyāya 14 for
`वसिष्ठः १४, १८, २०, ४४, ७०, ७१, ७६, ८८`, but adhyāya 14 has 31 mantras and the line names
88 — so the inference is refuted by the data and the line is left unread rather than
guessed.

The prior projection of 2,106 was treated as a claim to check, not as truth. The
difference is +134 and is **not** reconciled to a rule, because `2106` has no derivation
anywhere in the tree to diff against. The decomposition any recount must reconcile against
is recorded: 2,240 rows over 1,905 distinct addresses, 248 distinct ṛṣi names, 0 rows
outside the corpus, 70 released addresses silent.

**Devatā / Chandas: 0 and 0**, invented nowhere, emitted as explicit gaps. The
Sarvānukramaṇī is continuous sūtra prose and remains deliberately un-machine-resolved.

**Referent baseline created and gate wired.** No committed baseline existed for this work,
so the drift gate could not run at all. `tests/fixtures/identity/vsm_referent_baseline.jsonl`
now holds 1,975 rows with 1,975 distinct locators, and the build gates against it:
`UNCHANGED_REFERENT` 1,975, `REFERENT_DRIFT` 0.

**A boundary-provenance defect was found by adversarial review and fixed.** The attribution
joined `ORDINAL_HEADER_ABSENT` failures to records by `text.startswith(failure.line)` with a
monotonic cursor. In adhyāya 11 the relevant fallback belongs to VSM 11.28, whose printed
header lacks its terminal daṇḍa — but VSM 11.9 opens with the *same 63-character formula*
and sits earlier, so the greedy earliest match claimed it. The shipped release marked 11.9
inference-derived and 11.28 source-declared: both backwards, on the exact pair the
function's docstring claimed to resolve. Aggregate counts were unaffected, so a count-only
test stayed green over two wrong records. The adapter now records the source line each
accented run opened on, and the join is by line number. A line number is an identity; a
text prefix is a guess that happens to be usually right. Verified after the fix: 11.9
source-declared, 11.28 inference-derived, and 1,942 + 33 = 1,975 with 33 + 3 unattributed
= 36 events.

### English — Griffith 1899, acquired and aligned

**1,903 / 1,975 (96.4%)**, from `GRIFFITH.YV.1899.SACREDTEXTS`, registered this run. It is
the first machine-readable Griffith Yajurveda located: the archive.org item is page images
and Wikisource has no Yajurveda English at all.

| Alignment outcome | Count |
|---|---|
| `EXACT` | 1,889 |
| `STRUCTURAL_DIVERGENCE` | 14 |
| `SOURCE_GAP` | 72 |
| `AMBIGUOUS` | 37 |
| `UNRESOLVED` | 24 |

`1889 + 14 + 72 = 1975`; the further 61 are units that bind to no canonical key and are
carried with their full text rather than dropped.

**The mapping was proven, not assumed.** Every unit's address is the number Griffith
*prints*; position decides only which lines group together. Two witnesses per book (the
printed `BOOK THE <ORDINAL>` heading and the URL) must agree or the build raises. In 38 of
40 books the last printed verse number equals the canonical mantra count exactly. A test
feeds units printing 3, 2, 1 in that document order and asserts the first takes mantra 3;
another shuffles all 40 books and asserts byte-identical output.

**Three findings that would otherwise have produced silently wrong data:**

- **Book 12** prints 118 labels against 117 canonical mantras, with one verse printed twice
  (at 97 and again at 102). Printed 98–118 correspond to canonical 97–117, so a naive
  printed-number map would have put the **wrong translation on 21 keys**. Which copy is
  spurious is not decidable from the print — dropping either satisfies the arithmetic — so
  no shift was applied and those keys are reported as gaps.
- **VSM 23.20–31** are absent and the page says so, replacing them with two rows of dots.
  An unguarded span inference would have invented 12 translations the source states are not
  there.
- **Book 20.84–86** prints `84`, an unreadable `S5`, then `85`, where the unit printed 85
  actually carries VSM 20.86. All three refused rather than asserted.

Griffith's footnotes are absent from this digitisation by the digitiser's own statement, so
that layer remains a genuine gap.

**Determinism:** byte-identical across two independent rebuilds, with translations enabled.

---

## 4. Atharvaveda — refused, on measured evidence

The Atharvaveda workstream produced **complete production infrastructure and no releasable
canonical Sanskrit**, and the reason is a measurement rather than a shortfall of effort.

### What was completed

- **All 478 leaves acquired** from BSB/MDZ (`bsb10219750`), 269,381,024 bytes, 478 distinct
  sha256, via `scripts/fetch_atharvaveda_bsb_scan.py`.
- **The artifact gap closed.** `source_id BSB_MDZ` was registered and acquisition was
  `RESOLVED`, but **no artifact row existed** — and rights resolve through artifacts, so no
  build could bind an Atharvaveda row to the public-domain route at all. Registered:
  `BSB.AV.SAUNAKA.ROTH_WHITNEY.1856.SCAN` (PUBLIC_DOMAIN, aggregate checksum
  `478cdf54…ba75` over the leaves in canvas order) and
  `VEDAGRAPH.AVS.ROTH_WHITNEY_1856.TRANSCRIPTION` (**CC0**, `PRIMARY_TEXT`), with the split
  licence stated: transcribed text CC0, only VedaGraph apparatus under a VedaGraph licence.
- **A tracked per-leaf manifest**, `data/source_registry/atharvaveda_bsb_leaf_manifest.jsonl`,
  478 rows. `data/raw/**` is gitignored, so without this a transcription citing "printed
  page 287" would be an unverifiable claim.
- **Structure derived from the 1856 source itself**, by reading the running head of every
  text leaf: **20 kāṇḍas, 731 sūktas**, both matching the previously observed figures, with
  the derivation completed before the comparison was written. The kāṇḍa count is
  independently corroborated by the volume's own closing colophon on printed p.458. Text
  occupies n15–n472 = printed 1–458; `printed_page = canvas_index − 14` holds for all 458.
  One printed error found: p.145 heads `७ । १-६` where the body runs 1–5.
  **The mantra total is not derived and 5,839 remains unreconciled** — a running head names
  sūktas, never a mantra count, so mantra totals require reading every verse terminal,
  which *is* the transcription workload. Recorded as `null`, not estimated.
- **Kāṇḍa 1 read twice, end to end.** Its printed colophon on p.13 states **35 sūktas,
  153 mantras** — the first mantra count in this edition confirmed from the print itself
  rather than carried over from the digital lineage.
- **A written transcription protocol** (`docs/work_packets/ATHARVAVEDA_TRANSCRIPTION_PROTOCOL.md`)
  and a two-stage reconciliation harness in which no reader may certify itself.

### The measurement, and the mistake I made reading it

Transcription was attempted at production settings. Measured over **227 units read
independently twice** (26 leaves, kāṇḍas 1–2):

| Result | Count |
|---|---|
| `VERIFIED_EXACT` (codepoint agreement) | 123 — rate **0.542** |
| Agree on letters; differ in accent, punctuation, numerals or spacing | 42 |
| Differ in the **letters themselves** | 62 |
| Units carrying any Vedic accent mark (of 313 total) | 14 |

An example of a letter-level disagreement, AVS 2.19.1: one reader read `द्वेषि`, the other
`द्वेष्टि`.

**The rate moved four times as the sample grew, and every earlier figure is withdrawn:**
0.00 on 22 units (one leaf), 0.26 on 46, 0.485 on 167, 0.505 on 204, 0.542 on 227. I recorded the first
in a sentence that *also* said 22 units were "enough to refuse promotion and NOT enough to
characterise the error rate" — and then stated the rate anyway. That is the one-locus
overgeneralisation this repository has corrected four times, committed once more by the run
correcting the others, and then repeated at 46 and again at 167. **The monotone climb is
itself the finding:** at every sample size the measurement has been pessimistic and has not
converged across five successive sample sizes, so 0.542 is a floor from two kāṇḍas, not a corpus rate.

**The zero-accent result had a different cause than I first recorded, and the correction
matters more than the number.** Both readers initially recorded no accent at all, which
read as a capability failure. It was an **acquisition** failure. A reader stated the reason
precisely: at the width-2000 derivative this run first fetched, the accent marks of this
fount *"sit on akṣara boundaries and cannot be assigned to a specific akṣara without
guessing"* — so they declined to record them, which is exactly what RIGHTS-13 requires.
Re-fetched at width 4000 the marks are stem-aligned and legible, the volume has been
re-acquired at that width, and the fetch script now pins it. The IIIF `full` size returns
only 2025px, so 4000 must be requested explicitly.

**Resolution mattered — and my own reading of how much is corrected here.** From one crop of
leaf n17 I judged the accents "unambiguously attached to their akṣara". A reader working the
same 4000px scan line by line at up to 7× zoom disagrees: stem-aligned, yes, but still not
reliably assignable to a specific akṣara, so they omitted accent rather than guess — which is
what the protocol requires. **Accent remains unsolved even at 4000px** and needs a dedicated
pass; a partially-correct accent layer would be worse than none, because it looks complete.
What the re-fetch *did* prove is that resolution changes the base text: re-reading seven
leaves at 4000px produced **4 substantive changes in 86 units, about 4.7%** — including
`उपासान्` → `उपास्मान्` and `यद्गावः` → `यन्नावः` — and resolved both outstanding `[?]` marks.

So what this records is an exact-agreement rate of 0.542 on a small sample **at the wrong
resolution**, with the defect fixed — the whole volume re-acquired at width 4000, 478
leaves, 676,021,671 bytes, aggregate `4008cdca…17b6` — and the measurement **not yet
repeated at the right one**. It is not yet evidence about what model transcription can do
from an adequate image.

**What is true independent of resolution:** a failure both readers share is invisible to a
two-reader check, because agreement is its only signal. The zero-accent result was caught
by a separate `accent_fidelity_gap` measurement, not by the status vocabulary — which is
why that measurement is retained.

**What did not move:** the source is legible, its structure was derived from it
independently, and rights are clear. Nothing here weakens the acquisition or the artifact.
The registry's estimate of 60–120 person-hours *for a Vedic Sanskrit scholar* stands
untested either way.

**A defect in this run's own tooling was found by the same measurement.** The reconciler
labelled units "differ only in accent marking" on the strength of equality under
`ACCENT_STRIPPED_COMPARISON` — a surface that also strips editorial marks, digits and
whitespace. With zero accents present in either reading, that label was not merely
unverified but false. It now tests accent equality on its own first, and reports the
broader surface as what it is. An `accent_fidelity_gap` figure was added, because
accent loss is invisible to a status vocabulary built on agreement.

### New blocker dimensions

| Dimension | State |
|---|---|
| `production_artifact_registration` | `RESOLVED` |
| `transcription_channel_independence` | `OPEN_RIGHTS` |
| `transcription_fidelity_measured` | `OPEN_RESEARCH` |

---

## 5. Cross-Veda audit

| Check | Result |
|---|---|
| Canonical key / URN / UUID uniqueness across RV, SV, YV, AV | **0 collisions** over 16,121 passages |
| Orphan provenance claims | **0** over 26,693 assertions |
| Rigveda regression | byte-identical, 193 files |

**Licence composition — gates the aggregate release, not the ingestion.** SV and YV are
CC BY-SA 4.0; the Rigveda primary is CC BY-NC-SA 4.0, which is not BY-SA-compatible; the
Atharvaveda transcription is CC0. Under CC BY-SA 4.0 §3(b)(1) a combined four-Veda release
is **not licensable as a single adapted work**. An aggregate manifest may enumerate
separately-licensed datasets; it may not present them as one work.

---

## 6. Coverage, counted from the records

`data/builds/four_veda_corpus_completeness.json`. Every figure is counted from emitted
JSONL; a layer a release does not emit is `0` with the release named, and a work with no
release is `present: false`, which is a different state from zero coverage.

| Work | Release | Mantras | Sanskrit primary | Parallel | English | Hindi | Ṛṣi | Devatā | Chandas | Audio |
|---|---|---|---|---|---|---|---|---|---|---|
| RV Śākala | `rigveda_full_v1` | 10,552 | 10,552 | 10,552 | 10,500 | 0 | 10,534¹ | 10,552¹ | 10,518¹ | 0 |
| SV Kauthuma (ārcika) | `samaveda_arcika_v1` | 1,844 | 1,844 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| YV Vājasaneyi | `yajurveda_vsm_v1` | 1,975 | 0² | 1,836 | 1,903 | 0 | 1,960 | 0 | 0 | 0 |
| AV Śaunaka | *pilot only* | 153 | 153³ | 153 | 115 | 0 | 0 | 0 | 0 | 0 |

¹ From the separate deterministic knowledge layer (`rigveda_deterministic_v1`, 31,650
assertions), **not** the corpus release, which carries 9 rows. Reported beside the corpus
figure rather than merged into it. Reading only `traditional_metadata.jsonl` reports the
Rigveda as having zero traditional metadata, which is false — that is the exact error this
report exists to avoid.

² Zero is correct and is the point. All 1,975 Sanskrit units are
`EXTRACTED_FROM_CONTAINER`; this work has **no `PRIMARY_TEXT` layer**, and the report
counts the two roles separately rather than summing them. An earlier version of this
report folded them together and printed `sanskrit_primary_coverage: 1975` for the one work
whose defining property is that it has no primary layer — a number that contradicted the
record it summarised. The union is reported as `sanskrit_any_canonical_layer_coverage`.

³ The surviving pilot, sourced from the **REFERENCE_ONLY** GRETIL lineage. It is not a
release and is not promoted.

**Aggregate: 16,121 passages, 14,524 mantras across four works.**

---

## 7. Independent verdicts

### Agent E — rights authority

| Work | Verdict |
|---|---|
| Sāmaveda | `RIGHTS_BLOCKED` for **text publication**; cleared for internal use and a text-free identity release |
| Yajurveda | `RIGHTS_VERIFIED_WITH_CONDITIONS` |
| Atharvaveda | `RIGHTS_VERIFIED_WITH_CONDITIONS` for the BSB route; `RIGHTS_BLOCKED` for what would actually ship |
| Aggregate | `RIGHTS_BLOCKED` as a single adapted work; permitted as a Collection |

The Sāmaveda block is **not** a defect in the release. Every one of its 1,844 text rows is
`CC_BY_SA` bound to the Wikisource layer and nothing resolves to `GRETIL.SV.KAUTHUMA` — the
fail-open selection hole is genuinely closed. The block is the still-open
`independence_codepoint_reverification`: the selected witness's edition is `UNIDENTIFIED`
and its upstream print rights `UNRESOLVED`, so if the transcription descends from the
Pandey e-text ("No modification … is in any way authorized") the release is an unlicensed
derivative under RIGHTS-3 and RIGHTS-9. This run moved the evidence the *wrong way*: the
three loci found outside the Pūrvārcika (1179, 1133, 1592) are **shared defects**, which is
evidence against independence, and they are structural observations rather than codepoint
diffs. The closing evidence is obtainable without a firewall breach — the GRETIL TEI is
already on disk as a private verification snapshot, which `PERMISSION_REQUIRED` expressly
permits, and RIGHTS-13 does not apply because no transcription is involved. The diff was
not performed in this run and is the top rights work item.

Also fixed on Agent E's findings: `VEDAVANI.AV.SAUNAKA.WAV.HF` downgraded `APACHE_2_0` →
`UNKNOWN` (a HuggingFace card value sitting in the operative field while the record's own
notes called the chain "RESIDUAL RISK, not a clean chain" — RIGHTS-10 and RIGHTS-9), and
the `CC0` policy entry corrected from "Currently unused", which was the **third** recorded
stale-absence claim in this repository.

Open conditions not closed here: the 1929 Yajurveda print's PD status is asserted in prose
but Paṇaśīkara's death date is recorded nowhere (RIGHTS-8, India is life+60); the 2,240
traditional-metadata rows carry no `rights_status`; neither release carries a
`LICENSE`/`NOTICE` file; and `manifest.build_config_hashes` is `{}` in both, so nothing
pins the registry files a build read.

### Agent F — adversarial release QA

| Release | Verdict |
|---|---|
| `samaveda_arcika_v1` | `RELEASE_APPROVED_WITH_BACKLOG` |
| `yajurveda_vsm_v1` | `RELEASE_REJECTED` → **defect fixed, see §3**; re-run required to re-verdict |

**Gates that held under attack.** All 12 Sāmaveda referent-drift variants, including a full
referent swap and a swap *inside* a byte-identical-text equivalence class; all 6 routes to
`GRETIL.SV.KAUTHUMA` refused; all 16 coordinate-collision attempts; all 6 coverage-equation
injections. Decisively for the repeated-text concern: **zero** baseline rows share
`(locator, marker, comparison_sha256)`, so two keys in a shared-digest class cannot swap
undetected. On the Yajurveda side the accented layer could not be emitted `PRIMARY_TEXT` by
any route, VSM 16.37 kept both readings untruncated under one occurrence, and the 2,240 ṛṣi
assertions were independently re-expanded across 346 range lines with zero mismatches and
zero off-corpus targets.

**Fixed in this run from Agent F's findings:** the boundary-provenance inversion (§3); the
Sāmaveda `qa_issues.jsonl` shipping 39 rows under 37 ids, where both RN1181 occurrences
shared a locator and one withheld occurrence was therefore unaddressable — issue ids are
now discriminated by source line span, giving 39/39; and the completeness report's
`sanskrit_primary_coverage: 1975` for a work with no primary layer.

**Left as backlog:** the builds do not verify parallel-layer roles, do not detect a config
naming one text version in two slots, and do not assert their own "second reading preserved
in full" claim. Each is a missing guard rather than a wrong record.

---

## 8. Release decisions

| Decision | Value |
|---|---|
| Sāmaveda | **`SAMAVEDA_ARCIKA_CORPUS_READY_WITH_BACKLOG`** |
| Yajurveda | **`YAJURVEDA_CORPUS_READY_WITH_BACKLOG`** |
| Atharvaveda | **`ATHARVAVEDA_CORPUS_NOT_READY`** |
| Overall | **`FOUR_VEDA_CORPUS_FOUNDATION_INCOMPLETE`** |

**Sāmaveda — ready with backlog.** 1,844 canonical keys, five coverage equations balancing,
zero referent drift, byte-identical rebuilds, fail-closed selection proven by test. The
backlog is real and bounded: 31 verses withheld with explicit reasons, and
`independence_codepoint_reverification` open, which gates **bulk text redistribution** and
not identity or ingestion.

**Yajurveda — ready with backlog.** 1,975 / 1,975 addresses, 96.4% English, 2,240 ṛṣi
assertions across all 40 adhyāyas, zero drift, byte-identical. The blocking QA defect is
fixed. Backlog: VSM 16.37 needs a recorded human decision, Devatā and Chandas are absent
for want of an approved source, 72 mantras have no English, and the missing build guards
above.

**Atharvaveda — not ready, and "with backlog" would be an overclaim.** Rights, artifact
registration, acquisition, structural derivation and the transcription pipeline are all
production-grade. The corpus is not: no canonical Sanskrit is released, and the only
Atharvaveda records that exist are a 153-mantra pilot built from the `REFERENCE_ONLY`
Orlandi lineage, which may not be redistributed in derived form. A corpus that is ~97%
absent is not ready with a backlog.

**Overall — foundation incomplete.** Three of four works have a production release and the
fourth has none. Choosing either `READY_FOR_FREEZE` value would require calling a
one-work-in-four gap a backlog item.

**`NEXT_PROJECT_PHASE` is NOT `FOUR_VEDA_CANONICAL_DATA_FREEZE`.** Freezing now would freeze
an Atharvaveda that does not exist. The next phase is the Atharvaveda transcription itself,
now unblocked on rights, artifact, structure and tooling, and re-measured at the correct
image resolution.
