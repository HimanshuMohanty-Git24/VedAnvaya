# FULL INGESTION — INDEPENDENT RIGHTS VERIFICATION

**Verifier:** Agent E (rights / provenance authority), independent verification pass
**Date:** 2026-09-07
**Scope:** `data/canonical/samaveda_arcika_v1/`, `data/canonical/yajurveda_vsm_v1/`,
`data/transcriptions/atharvaveda_bsb_1856/`, the artifacts and TextVersions registered by the
`FULL_SV_YV_AV_CANONICAL_INGESTION` run, and the aggregate four-Veda position.
**Governing policy:** `data/registry/rights.yaml`, rules RIGHTS-1 … RIGHTS-13.
**Posture:** adversarial. This pass looked for defects, not for confirmation.

---

## VERDICTS

| Work | Verdict | Operative constraint |
|---|---|---|
| Sāmaveda (`samaveda_arcika_v1`) | **RIGHTS_BLOCKED** *for publication as a text corpus* | `independence_codepoint_reverification` is undischarged and the release IS a bulk text release (1,844 populated `text_nfc` rows). Internal retention, derivation and a text-free structural/identity release are cleared. |
| Yajurveda (`yajurveda_vsm_v1`) | **RIGHTS_VERIFIED_WITH_CONDITIONS** | Chain is clean; four expression defects listed below must be fixed before the bytes leave the machine. |
| Atharvaveda — BSB route (`BSB.AV.SAUNAKA.ROTH_WHITNEY.1856.SCAN` + `VEDAGRAPH.AVS.ROTH_WHITNEY_1856.TRANSCRIPTION`) | **RIGHTS_VERIFIED_WITH_CONDITIONS** | Cleanest chain of title in the repository. Conditions are about what the 16 "release-eligible" units may be *called*, not about the right to publish them. |
| Atharvaveda — as it currently enters the aggregate (`atharvaveda_pilot_v1`) | **RIGHTS_BLOCKED** | 459 `REFERENCE_ONLY` GRETIL/Orlandi-lineage text records. `redistribute_derived: no`. |
| Aggregate four-Veda manifest | **RIGHTS_BLOCKED** as a single adapted work; permissible only as a Collection, and not even as a Collection until the AV member is repointed. | See §4. |

---

## 1. SĀMAVEDA — `data/canonical/samaveda_arcika_v1/`

### 1.1 What is clean

Verified mechanically, not read off the report:

- **Every one of 1,844 `text_versions.jsonl` rows** carries `rights_status: CC_BY_SA`,
  `text_version_id: WIKISOURCE_SA.SV.KAU.ARCIKA_MULA`,
  `source_artifact_id: WIKISOURCE_SA.SV.KAU.SAMHITA.DEVANAGARI`, `source_id: WIKISOURCE_SA`.
  Zero rows with any other value. Consistent with the registry, where both the artifact
  (`source_artifacts.yaml`) and the TextVersion (`text_versions.yaml`, `normalized_rights: CC_BY_SA`)
  agree.
- **Nothing in the release resolves to `GRETIL.SV.KAUTHUMA`.** All 1,844 `referent_bindings.jsonl`
  rows and all 69 `source_assertions.jsonl` rows bind to the Wikisource artifact. The only
  occurrences of the strings `GRETIL`, `TITUS` and `Pandey` anywhere in the release are inside
  narrative `notes` fields on `works.jsonl`, `sources.jsonl` and `source_artifacts.jsonl` —
  prose about the rejected witness, never a resolvable field value. The `SV-TEXTVERSION` hard
  precondition (fail-open to `GRETIL.SV.KAUTHUMA` at `PERMISSION_REQUIRED`) is genuinely closed.
- Audio 0, translations 0, traditional_metadata 0 — nothing ingested without a licence.

### 1.2 The share-alike / URI obligation — PARTIALLY DISCHARGED, and misplaced

CC BY-SA 4.0 §3(a)(1)(A) requires retention of creator identification (i), a licence notice (iv)
and **a URI or hyperlink to the Licensed Material (iii)**. The registry itself states the revid is
what discharges (iii) "because the source is mutable".

Measured:

| Element | Present? | Where |
|---|---|---|
| Creator identification | yes | `sources.jsonl` → `rights.holder = "Wikisource contributors, collectively"` |
| Licence URI | yes | `sources.jsonl`, `source_artifacts.jsonl` |
| **Revision id** | **yes, 100 %** | `referent_bindings.jsonl` → `source_revision_id`, 1,844/1,844 populated, 87 distinct |
| Revision id in the **text-bearing** file | **no, 0 %** | `text_versions.jsonl` carries no revid, no page title, no URI |
| Human-readable attribution notice | **no** | no `LICENSE`, `NOTICE`, `ATTRIBUTION` or `README` file exists in the release directory |
| Licence URI in `manifest.json` | **no** | `rights_summary` carries bare status strings only |

**The defect.** Every element exists *somewhere*, but no element that discharges (iii) exists in
`text_versions.jsonl` — the one file a redistributor would actually take. Worse, SV's
`source_locator` is a VedaGraph-internal shorthand (`"WS CHANDA.P1.D3 RN33"`) that does not name
the Wikisource page at all. (Contrast YV, whose locator is the real page title
`शुक्लयजुर्वेदः/अध्यायः ०१#1.1`.) A recipient of `samaveda_arcika_v1/text_versions.jsonl` alone
cannot construct the URI, cannot name the creator, and cannot find the licence.

**Fix, concretely:** carry `source_revision_id` onto `text_versions.jsonl` rows (the value already
exists per row in `referent_bindings.jsonl`, joinable on `passage_id`/`entity_id`), and add a
`LICENSE`/`NOTICE` file to the release directory naming Sanskrit Wikisource contributors, the
CC BY-SA 4.0 URI, and the `https://sa.wikisource.org/w/index.php?oldid=<revid>` reconstruction
rule. Both are mechanical.

### 1.3 `independence_codepoint_reverification` — NOT DISCHARGED. This blocks the text release.

The registry requires: *"re-verify at codepoint level at MORE THAN TWO loci, outside the Purvarcika
defect-free region, BEFORE any bulk text release."* Dimension state is `OPEN_RESEARCH`.

**Has this run discharged it? No — and the run moved the evidence in the wrong direction.**

What the run actually produced (per `source_artifacts.yaml` notes on
`WIKISOURCE_SA.SV.KAU.SAMHITA.DEVANAGARI`) is three loci outside the Purvarcika where the selected
witness and the Pandey lineage **share a defect**: running number 1179 typeset as a second 1181 in
both, and single-danda verse terminators at 1133 and 1592 in both. Those are three loci in the
right region, but they are:

1. **structural/punctuational observations, not codepoint-level text comparison** — no
   aksara-by-aksara diff was performed at any locus; and
2. **evidence against independence, not for it.** The requirement asks for evidence that the
   witnesses do not share descent. Three shared defects is the opposite finding.

The run correctly retracted the earlier overclaim ("INDEPENDENCE FROM THE PANDEY LINEAGE IS NOW
PROVEN TEXTUALLY") and correctly demoted the grade to `NOT_A_VERBATIM_COPY`. That retraction is
good practice. It is not closure.

**Why this is load-bearing and not bookkeeping.** The SV redistribution basis is CC BY-SA on the
*transcription layer*, justified on the ground that the Vedic text is ancient so the transcription
is the only copyrightable contribution. If the Wikisource transcription is in fact derived from
the Pandey text — *"Copyright (C) 1998 Anshuman Pandey … No modification of this document is in any
way authorized"* — then under **RIGHTS-3** the more restrictive statement controls and under
**RIGHTS-9** the defect propagates to every downstream re-publisher regardless of what Wikisource
asserts. Wikisource would be an aggregator granting rights it does not hold, and
`samaveda_arcika_v1` would be an unlicensed derivative of a text that forbids modification. The
VedaGraph pipeline NFC-normalizes, re-keys and republishes as JSONL — that is modification *and*
publication, both forbidden.

This is aggravated by two facts already on the record: `source_edition: UNIDENTIFIED` and
`upstream_print_rights_status: UNRESOLVED` on the artifact itself. The chain is not followed to a
root; it stops at the transcription layer.

**What a release MAY do until this closes:**
- retain the corpus locally and derive from it internally;
- publish the *identity layer* — canonical keys, URNs, structural coordinates, counts,
  `referent_bindings` minus `text_sha256`/`comparison_sha256` — because none of that is expressive
  content of the transcription;
- publish citations, page-title/revid provenance, and QA findings.

**What it MAY NOT do:** publish `text_versions.jsonl`, `passages.jsonl` text payloads, or any
artifact from which the 1,844 mantra strings are recoverable. That is the bulk text release the
blocker names.

**What evidence would close it, and whether it is obtainable without a firewall breach — yes, it
is.** The GRETIL Kauthuma TEI is already on disk as a private verification snapshot
(`data/raw/gretil/2026-09-07/91c28c0394e9….xml`, from
`gretil.sub.uni-goettingen.de/gretil/corpustei/sa_sAmavedasaMhitA.xml`). Under
`operational_semantics.PERMISSION_REQUIRED`, `copy_local` is expressly permitted as *"a bounded,
non-published verification snapshot retained privately"* — which is exactly what this is, and a
rights investigation is exactly what it is for. **RIGHTS-13 does not bar this**: RIGHTS-13 governs
*fresh transcription*, and no transcription is involved. Nothing needs to be fetched.

The closing evidence is therefore:

1. An alignment between the two witnesses. This is the actual work, and it is non-trivial: the
   GRETIL TEI is romanised, held in 479 `<p>` elements with no `n=` attributes and no `SV_k,p.d.v`
   reference labels of any kind (verified — zero matches for either pattern), while the release is
   Devanagari keyed by running whole-Samhita number. The alignment must be reconstructed, and its
   fragility is itself part of why the numbering-system difference is the stronger independence
   argument.
2. **A codepoint-level diff at ≥ 3 loci outside the Purvarcika**, reporting per-locus: identical /
   differs-in-accent-only / differs-in-aksara. Loci must be chosen adversarially — passages where a
   copyist would have had no reason to correct — not the three already known to be shared.
3. The output must be a **verdict and a statistic only**. The GRETIL text must never be written into
   any VedaGraph artifact, never be quoted in a committed report, and never be used to repair a
   Wikisource reading. A repair would convert the investigation into the contamination it exists to
   exclude.
4. A finding of *"differs in aksara at ≥ 3 independent loci"* closes the dimension toward
   independence. A finding of *"identical at codepoint level"* closes it the other way and forces
   the SV corpus to `REFERENCE_ONLY` under RIGHTS-3.

**This pass did not perform (2).** It confirmed the snapshot is present and the act is permitted,
and stopped at the alignment, which is the coordinator's work item, not a verifier's.

### 1.4 Lesser SV defects

- `manifest.json → rights_summary` mixes namespaces: it keys on both
  `WIKISOURCE_SA.SV.KAU.ARCIKA_MULA` (a **TextVersion** id) and
  `WIKISOURCE_SA.SV.KAU.SAMHITA.DEVANAGARI` (a **source artifact** id) as if they were the same
  kind of thing. Both resolve to `CC_BY_SA`, so no substantive exposure — but RIGHTS-2 exists
  precisely to stop rights levels being collapsed, and this collapses two.
- `rights_summary.share_alike` reads: *"CC BY-SA 4.0 … is ONE-WAY INCOMPATIBLE with CC0; do not
  merge this layer into a single licensed blob with a CC0 layer."* **The direction stated is
  wrong.** CC0 imposes no conditions, so CC0 material composes freely *into* a BY-SA work; the AV
  TextVersion record says exactly this and is correct. The real hazard is the one the SV note does
  not state: merging CC0 AV text into a BY-SA blob strips the AV text's CC0 status downstream. The
  caution is right, the reason given is not, and the two registry statements now contradict each
  other. Under RIGHTS-3 the more restrictive (SV's) would control and would needlessly forbid a
  permitted combination.

---

## 2. YAJURVEDA — `data/canonical/yajurveda_vsm_v1/`

### 2.1 What is clean

- 3,811 `text_versions.jsonl` rows, **all** `CC_BY_SA`: 1,975 `WIKISOURCE_SA.YV.VSM.ACCENTED`
  (`EXTRACTED_FROM_CONTAINER`) + 1,836 `WIKISOURCE_SA.YV.VSM.UNACCENTED` (`PARALLEL_TEXT`), all
  bound to `WIKISOURCE_SA.YV.VSM.SAMHITA.DEVANAGARI`. No other value appears.
- `source_revision_id` populated on 1,975/1,975 `referent_bindings.jsonl` rows, 40 distinct revids,
  and `source_locator` carries the **real Wikisource page title**. YV discharges CC BY-SA
  §3(a)(1)(A)(iii) better than SV does.
- **Translations: 0 rows — confirmed a reported gap, not an unlicensed ingestion.** The
  completeness build records `translation_records_by_language: {}` under the stated counting rule
  *"a layer a release does not emit is 0 with the release named"*, and the run report states
  "Translations: 0. Audio: 0." Two rights-clear PD translations exist in the registry
  (`GRIFFITH.YV.1899.ARCHIVE`, `PUBLIC_DOMAIN`) and were deliberately not ingested. Correct and
  conservative.
- The 1929 Nirnaya Sagara / Panasikara edition is not itself redistributed; only the Wikisource
  transcription of it is. Uvata's *Mantrabhasya* and Mahidhara's *Vedadipa* are pre-modern and
  uncopyrightable.

### 2.2 Defect — the 1929 print's PD status is asserted, never evidenced (RIGHTS-4 / RIGHTS-8)

`WIKISOURCE_SA.YV.VSM.SAMHITA.DEVANAGARI` asserts in prose: *"the 1929 print is PUBLIC DOMAIN by
age"*. The `WIKISOURCE_SA.YV.VSM.ACCENTED` TextVersion repeats it. Against that:

- The artifact row has **no `upstream_print_rights_status` field at all**. The SV row has one
  (`UNRESOLVED`) and the BSB row has one (`PUBLIC_DOMAIN_BY_AGE`). YV — the only one of the three
  that names a specific in-scope modern printed edition — is the one that omits the field. A
  machine chain-of-title check over the registry returns nothing for this row.
- **No death date for Vasudeva Sarma Panasikara is recorded anywhere in the repository.** A
  full-repo enumeration of recorded death dates returns Whitney 1894, Roth 1895, Aufrecht 1907,
  Griffith 1906, Satavalekar 1968, Vishva Bandhu 1973 — and nothing for Panasikara. RIGHTS-8 is
  explicit that where an item is classified PUBLIC_DOMAIN *"the justification must be the underlying
  work publication date **and** the author death date, recorded explicitly."* Here the publication
  date is recorded and the death date is not. The BSB record does this correctly ("Whitney d. 1894,
  Roth d. 1895"); the YV record does not.
- This matters and is not a formality. India's term is life + 60. If Panasikara died after 1965 the
  1929 edition's editorial layer is still in copyright in India, the Wikisource transcription is an
  infringing derivative, and under RIGHTS-3/RIGHTS-9 the whole YV release drops. The registry's own
  boast that *"there is no encumbered link anywhere in this chain"* currently rests on an
  unrecorded fact.

**Fix:** record Panasikara's death date with a source, or restate the PD basis on a ground that does
not need one (e.g. that the mantra text and the two pre-modern commentaries are the entirety of the
reproduced content and no post-1929 editorial matter is transcribed), and populate
`upstream_print_rights_status`.

### 2.3 Defect — the traditional-metadata layer is rights-silent, and its artifact is absent from `rights_summary`

`traditional_metadata.jsonl` carries **2,240 rows**, and:

- **no `rights_status` field on any row**, and no `source_artifact_id` — only
  `source_id: WIKISOURCE_SA` and a `source_locator`;
- the contributing artifact, `WIKISOURCE_SA.YV.VSM.RISHISUCI`, **does not appear in
  `manifest.json → rights_summary` at all**, even though it *is* listed in `source_artifact_ids`
  and is the source of 2,241 `source_assertions` and all 2,240 metadata rows.

`rights_summary` for YV is `{WIKISOURCE_SA, WIKISOURCE_SA.YV.VSM.ACCENTED,
WIKISOURCE_SA.YV.VSM.UNACCENTED}` — a source_id and two TextVersion ids. **It names neither of the
release's two declared source artifacts.** Substantively everything is CC BY-SA and the rows *are*
traceable (the metadata `source_locator` joins to `source_assertions.source_artifact_id =
WIKISOURCE_SA.YV.VSM.RISHISUCI`), so this is an expression defect rather than an exposure. But it
means a reader of the manifest cannot determine the licence of the rishi apparatus, which is
2,240 of the release's rows.

**Are the emitted traditional-metadata rows rights-correct?** Substantively yes — CC BY-SA via
`RISHISUCI`, whose own registry record is properly evidenced (single-page artifact, checksum
independently re-verified, page title parsed from the payload to confirm scope). Formally no — they
are rights-silent and their artifact is unlisted.

### 2.4 Defect — no share-alike notice in the YV manifest

SV's `rights_summary` carries an explicit `share_alike` clause. YV's carries none, and no
`translations`/`audio` scope note either. YV is under an identical live CC BY-SA obligation. The
`source_specific_restrictions` on both YV TextVersions state it correctly in the registry; it never
reaches the release.

### 2.5 Minor

`referent_bindings.jsonl` for YV lacks `source_snapshot_sha256`, which SV carries. Byte-level
re-verification of a YV binding therefore requires the manifest rather than the row.

---

## 3. ATHARVAVEDA

### 3.1 `BSB.AV.SAUNAKA.ROTH_WHITNEY.1856.SCAN` — verified, and it is the best record in the repository

Independently checked, not accepted:

- **Aggregate checksum reproduces exactly.** Recomputing sha256 over the newline-joined
  `"<mdz_image_id>:<sha256>"` line of all 478 leaves in canvas order, with trailing newline, yields
  `478cdf546d65409ab3ea3726fbf92911fc95f756072fcb679bcf2ed9f771ba75` — byte-identical to the
  registered value. The two obvious alternative encodings do not match, so the construction is
  pinned, not coincidental.
- **Leaf manifest is 478 rows and git-tracked**, correctly noted as necessary because
  `data/raw/**` is gitignored.
- **Every transcription record's `mdz_image_id` resolves**, across all of `stage1/`, `stage2/` and
  `reconciled/`: 5 distinct leaves (`_00015`, `_00016`, `_00017`, `_00018`, `_00036`), zero
  unresolved, and each record's `canvas_index` and `printed_page` agree with the manifest.
- **All five leaf files re-hash to their manifest `sha256` and match `byte_size`.**
- **Zero provenance contamination.** A case-insensitive scan of every transcription file for
  `gretil|titus|vedaweb|orlandi|pandey|whitney_lanman|sacred.texts` returns **nothing**. The
  artifact channel is clean.
- The RIGHTS-10 reasoning is right and is the sixth-instance analysis applied correctly: PD rests on
  age (1856; Whitney d. 1894, Roth d. 1895), *not* on BSB's tag; BSB's *"Kein Urheberrechtsschutz"*
  is relied on only as a waiver of the thin UrhG §72 *Lichtbildschutz* over its own digitisation,
  which is the one right BSB has standing to waive. Choosing BSB over the archive.org Google-scan
  re-upload tagged CC BY 3.0 by a non-digitiser is exactly correct.

### 3.2 The split licence is correctly expressed — verified, no copyfraud

`VEDAGRAPH.AVS.ROTH_WHITNEY_1856.TRANSCRIPTION` carries `normalized_rights: CC0`,
`license_uri: https://creativecommons.org/publicdomain/zero/1.0/`, and
`source_specific_restrictions` stating that **the transcribed text is CC0/PD and only VedaGraph
structural apparatus — keying, JSONL schema, alignment, SourceAssertions — carries a VedaGraph
licence**, with the explicit reasoning that asserting copyright over a faithful transcription of a
PD work *"would be the same copyfraud RIGHTS-10 condemns in other parties."*

That is correct and it is the right way round. No CC BY-SA is asserted anywhere over the
transcribed text. The `electronic_lineage` array names five links ending in *"NO DIGITAL
ATHARVAVEDA IS IN THIS CHAIN. The Orlandi 1991 lineage (GRETIL, TITUS, VedaWeb AVS Sanskrit) was
not consulted at any stage and is not an upstream of this layer."* **Verified consistent with the
data.**

### 3.3 `transcription_channel_independence` (OPEN_RIGHTS) — the characterisation is HONEST, and marginally UNDER-states

Asked whether the stated residual risk over- or under-states: **it under-states, in two specific and
fixable ways. It does not over-state anywhere.**

The prose is unusually good. It refuses to declare the dimension discharged; it names the
correlated-error mode a two-reader check cannot detect by construction; it says the residual is
unquantified; it states what would close it (human verification of a statistically meaningful
sample, or a second rights-compatible PD witness) and that neither is available in an automated
run; and it explicitly warns that the one-leaf, 22-unit sample must not later be cited as a
corpus-wide error rate. The sibling dimension `transcription_fidelity_measured` reports the adverse
result rather than burying it. That is the correct standard.

**Independent corroboration of the adverse finding.** I opened leaf `bsb10219750_00036` (printed
p. 22) directly. **The printed page carries Vedic accent marking on essentially every word** —
anudātta underscores and svarita strokes are plainly visible throughout. The reconciliation summary
reports `units_carrying_any_vedic_accent: 0` across **all 61 units**, and
`accent_fidelity_gap: 61`. Both readers dropped a printed feature of the page, unanimously. That is
a real, measured, 100 % fidelity failure on a feature the source prints, and the registry reports it
correctly.

**Where it under-states:**

1. **The measurement is scoped to leaf n36 (22 units), but 39 of the 61 units were never
   double-read at all.** `stage1/` contains only `leaf_00036`; leaves 15–17 exist in `stage2/`
   only. Those 39 units are `PHILOLOGICAL_REVIEW_REQUIRED` and correctly `release_eligible: false`
   — but they sit in a directory named `reconciled/` with a populated `text_devanagari`, and the
   two-reader control was never applied to them. The dimension text should say the control has been
   *exercised* on one leaf, not merely *measured* on one leaf.
2. **`unclear_marks_total: 0` across 61 units is itself a signal the dimension does not read.**
   RIGHTS-13's operational test is *"Where a character is genuinely unclear, mark it `[?]` and move
   on."* The artifact record states the 1856 Berlin fount's `a` is *"easily misread as `r`/`sr`"*
   and calls this *"the dominant transcription error risk."* Sixty-one units read from that fount
   with **zero** `[?]` marks means the readers never once declined to resolve — which is precisely
   the "helpfully and silently completes" behaviour RIGHTS-13 names. Zero unclear marks is not
   evidence of clarity; it is evidence the escape hatch was not used. This should be tracked as a
   metric with a non-zero expectation.

**One positive independence signal, obtained mechanically.** I ran a codepoint similarity of all 61
reconciled units (and both stage readings) against the locally-held GRETIL unaccented AVS
(`avs___u.htm`), transliterating Devanagari→IAST and stripping diacritics, punctuation and
numerals. Output was restricted to ratios; no GRETIL text was read into context or written anywhere.
Result: **144 comparisons, zero identical, mean ratio 0.55, max 0.80.** The transcription is
demonstrably not a copy of the GRETIL text. Stronger still, the readings **preserve the print's `०`
pratīka-abbreviation marker** in the repetitive AVS 2.19–2.23 sequence rather than expanding it —
our units are ~32 characters where GRETIL's are ~58. A model answering from recall would have
expanded the abbreviation; reading the page produces the abbreviation. That is meaningful evidence
*for* optical reading. It does not close the dimension — RIGHTS-13's whole point is that a
non-verbatim recall-shaped output is undetectable after the fact — but it is worth recording as the
first affirmative evidence on this question.

### 3.4 Defect — 16 units are flagged `release_eligible: true` while the registry says fidelity is unproven

`reconciliation_summary.json` declares `release_eligible_units: 16`, and 16 reconciled rows carry
`release_eligible: true` at `VERIFIED_WITH_ORTHOGRAPHIC_NOTE`. Meanwhile
`transcription_fidelity_measured` is `OPEN_RESEARCH` and its text says the measurement is *"enough
to refuse promotion."* The prose refuses promotion; the data grants it.

Inspecting the 16: **the entire disagreement between the two readers across leaf 36 is one
systematic whitespace difference** — `यो३` versus `यो ३`, repeated. That is a formatting convention
difference between two readers, not two independent readings converging. Calling it an
"orthographic note" while a 100 % accent loss goes unmarked at row level inverts the severity: the
label attaches to a space and is silent about the missing feature.

This is a rights question, not only a philological one. If the 16 units ship as CC0 "faithful
transcription of a public-domain work", the claim of faithfulness is the basis on which no new
copyright arises and no encumbered derivative exists. A unit that is measurably unfaithful to the
page in a systematic way weakens exactly that claim.

**Fix:** set `release_eligible: false` until accent is reproduced or the layer is explicitly
redefined and labelled as an accent-stripped reading; and surface `accent_present: false` per row,
not only in the summary.

### 3.5 Defect — `text_devanagari` is populated on rows whose own record says no reading was selected

Six `TRANSCRIPTION_UNCERTAIN` rows carry
`reconciliation_detail: "the two independent readings differ beyond accentuation; both are
preserved and neither is selected"` — and a populated `text_devanagari` equal to `stage1_text`.
On AVS 2.19.1 that means the emitted field carries `…स्मान्द्वेषि…` where the other reader read
`…स्मान्द्वेष्टि…`. Whichever is right, the record asserts that nothing was selected while the
field asserts a selection. A consumer reading `text_devanagari` without checking
`transcription_status` gets a reading the pipeline says it did not make. `release_eligible: false`
bounds the blast radius; the field should be `null`.

### 3.6 BLOCKER — the AV that actually enters the aggregate is the encumbered pilot

`data/builds/four_veda_corpus_completeness.json` records for `VG:WORK:AV:SAU`:

```
release_dir: atharvaveda_pilot_v1
rights_statuses_present: {"REFERENCE_ONLY": 459}
rights_restricted_text_records: 459
mantra_count: 153
```

`data/canonical/atharvaveda_pilot_v1/text_versions.jsonl` is 459 rows across
`GRETIL.AVS.SAUNAKA.ACCENTED` (153), `GRETIL.AVS.SAUNAKA.UNACCENTED` (153) and
`VEDAGRAPH.AVS.SEARCH_NORMALIZED` (153) — all `REFERENCE_ONLY`, all bound to the GRETIL AV
artifacts, i.e. **the Orlandi 1991 lineage the BSB route exists to escape.** For `REFERENCE_ONLY`,
`redistribute: no` and `redistribute_derived: no`.

The 61 BSB transcription units are **not in the aggregate at all.** So the four-Veda headline
figure ("`works_released: 4`, `mantras_all_works: 14524`") counts 153 encumbered AV mantras and
zero clean ones. The completeness file is honest at row level — it reports
`rights_restricted_text_records: 459` in plain sight, which is good engineering — but the
`aggregate` block and the run report's line *"Aggregate: 16,121 passages, 14,524 mantras across four
works"* carry no such qualification.

**Related release-tree hazard.** `data/canonical/` is not rights-partitioned. Alongside the two new
releases it holds `samaveda_pilot_v1` (**102 `PERMISSION_REQUIRED` `GRETIL.SV.KAUTHUMA` text
rows** — the Pandey text that forbids modification outright) and `atharvaveda_pilot_v1` (459
`REFERENCE_ONLY` rows). Anyone who archives `data/canonical/` as "the corpus" ships both. The
gitignore keeps them out of the repository; nothing keeps them out of a tarball. A
`PUBLISHABLE`/`NEVER_PUBLISH` marker per release directory, checked by whatever produces a
distribution, is the mechanical fix.

---

## 4. CROSS-VEDA LICENCE COMPATIBILITY — the registry's position is CORRECT

**Verified against the licence texts and against the release data.**

| Layer | Class | Verified from |
|---|---|---|
| SV `samaveda_arcika_v1` | CC BY-SA 4.0 | 1,844/1,844 rows `CC_BY_SA` |
| YV `yajurveda_vsm_v1` | CC BY-SA 4.0 | 3,811/3,811 rows `CC_BY_SA` |
| RV `rigveda_full_v1` Sanskrit | CC BY-NC-SA 4.0 | 21,104/21,104 rows `CC_BY_NC_SA` (`GRETIL.RV.AUFRECHT` 10,552 + `VEDAWEB.AUFRECHT` 10,552) |
| RV translations | PUBLIC_DOMAIN | 10,502 rows, Griffith 1896 |
| AV transcription | CC0 1.0 | `VEDAGRAPH.AVS.ROTH_WHITNEY_1856.TRANSCRIPTION` |

**Why a single adapted work is impossible.** CC BY-SA 4.0 §3(b)(1) requires that the Adapter's
Licence be a CC licence *with the same License Elements*, this version or later, or a listed BY-SA
Compatible Licence. BY-SA's elements are `BY, SA`. BY-NC-SA's are `BY, NC, SA` — not the same, and
BY-NC-SA is not on the ShareAlike compatibility list (which currently contains only GPLv3 and FAL).
Symmetrically, CC BY-NC-SA 4.0 §3(b)(1) requires *its* adapter's licence to carry `BY, NC, SA`.
A single merged four-Veda work would have to be simultaneously BY-SA (to satisfy SV/YV) and
BY-NC-SA (to satisfy RV). Those are mutually exclusive. **The registry's statement is right.**

CC0 is not the problem: it imposes no conditions and composes into anything. The only consequence
of merging the AV layer into a BY-SA or BY-NC-SA blob is that the AV text loses its CC0 status for
recipients of that blob — which is a reason to keep it separate, but not an incompatibility. See
§1.4: the SV manifest currently states this backwards.

### What an aggregate four-Veda manifest MAY be

A **Collection** in the CC 4.0 sense. CC BY-SA 4.0 expressly contemplates this: material included
in a Collection is not thereby Adapted Material, and *"the Licensed Material remains separately
licensed."* Concretely, the manifest MAY:

- enumerate four datasets, each with its own directory, its own licence declaration, its own
  attribution block and its own URI/revid provenance;
- carry cross-Veda **identity** data — canonical keys, URNs, per-work counts, collision audits (the
  `cross_veda_identity_audit` block is exactly this shape and is rights-neutral, because a
  content-addressed key is not expressive content of any source);
- carry cross-Veda **structural** metadata — hierarchy, container counts, coverage figures;
- state the compatibility finding itself, prominently.

### What it MAY NOT be

- a single licence declaration over the whole set;
- a merged corpus file, a single text table, or any interleaved text artifact spanning the BY-SA
  and BY-NC-SA layers;
- a unified knowledge graph, search index, embedding set or semantic layer built **jointly** across
  the SV/YV (BY-SA) and RV (BY-NC-SA) texts — such an artifact is Adapted Material of both and
  cannot be licensed;
- anything commercially licensed that touches the RV layer (NC is permanent for anything
  incorporating it);
- an aggregate that presents the four works as one corpus with one provenance story.

### And, gating it today

Even as a Collection, the aggregate **cannot ship now**, for two reasons independent of licence
compatibility:

1. its AV member is `atharvaveda_pilot_v1`, 459 `REFERENCE_ONLY` records, `redistribute_derived:
   no` (§3.6);
2. its SV member is blocked on `independence_codepoint_reverification` (§1.3).

The YV member and the RV member could ship today as separately-licensed datasets, subject to the
YV conditions in §2 and NC on the RV.

---

## 5. WHAT NOBODY ASKED ABOUT

### 5.1 A permissive status inferred from a host — `VEDAVANI.AV.SAUNAKA.WAV.HF` (APACHE_2_0)

Registered `APACHE_2_0` on the strength of a HuggingFace `cardData` licence field. Its own notes
then say: *"the Atharvaveda_Part_NNN filenames match the archive.org Veda Prasara Samithi upload
exactly, so at least part of the source audio is almost certainly that recording. An Apache-2.0
grant asserted by the DATASET AUTHORS over third-party recordings is not a verified chain of title
… So this is RESIDUAL RISK, not a clean chain."*

That is a textbook RIGHTS-10 fact pattern: a re-publisher's licence tag over third-party content,
by a party without standing. RIGHTS-10: such a tag *"is an ASSERTION about someone else's
copyright, never a grant of it."* RIGHTS-9: the defect propagates from the root regardless of what
the final publisher asserts. RIGHTS-6: audio never inherits, default posture `REFERENCE_ONLY`.
RIGHTS-4: permissive is never inferred, only evidenced — and the evidence here is the assertion of
the party whose standing the record itself doubts.

**The operative field and the prose disagree, and the permissive value is in the operative field.**
Correct disposition is `UNKNOWN` (or `PERMISSION_REQUIRED`) with `APACHE_2_0` recorded as the
*asserted* licence in `license_statement_verbatim`. No release currently emits audio, so there is no
live exposure — this is a registry defect that will become an exposure the first time an audio
layer is built.

### 5.2 An artifact whose `rights_status` contradicts its own record — `COMMONS.SV.KAU.SAMAN.AUDIO`

`rights_status: CC_BY_SA`, single value. Its own `license_statement_verbatim` says the set is
**458 files CC BY-SA 4.0 and 16 files CC0**, and its own notes say *"the two licences are not
uniform, so the 16 CC0 files and the 458 CC BY-SA 4.0 files must retain their own terms rather than
be flattened to one collection licence."* The row performs precisely the flattening its notes
forbid. The direction is conservative (CC0 → BY-SA over-restricts), so there is no exposure — but
it wrongly encumbers 16 files that are free, and it is the exact
`rights_status`-vs-`license_statement_verbatim` disagreement this section was asked to find. Needs
either per-file rights or a split into two artifact rows.

**Off-by-one in the licensed-file count.** Counted directly from
`data/source_registry/samaveda_gana_audio_inventory.jsonl`: **475 rows = 459 `CC BY-SA 4.0` + 16
`CC0`**, zero unlicensed. The artifact row's verbatim says **458** CC BY-SA, twice. The figure in
`rights.yaml`'s CC0 entry (459) is the correct one; the artifact row is wrong by one and should be
corrected to match the measured inventory.

Per-file verification via the Commons `imageinfo/extmetadata` API is otherwise exemplary and
correctly *not* inferred from Commons' general terms — Commons has no site-wide content licence, so
a host-level inference there would have been a genuine RIGHTS-1 breach.

### 5.3 `UNKNOWN` in a shipped release — `rigveda_full_v1/source_artifacts.jsonl`

**11 of 14 artifact rows in the RV release carry `rights_status: UNKNOWN`** (all
`VEDAWEB.RV.*.TEI.D3EB8AF`), while **21,104 text rows in the same release assert `CC_BY_NC_SA`.**

On investigation this is *not* an optimistic upgrade: the artifact note explains *"rights_status is
UNKNOWN at file level because the file mixes CC BY 4.0 and CC BY-NC-SA 4.0 layers. Use the
per-version rights in text_versions.yaml"*, and every VedaWeb TextVersion in the registry does
carry a verbatim licence statement (`VEDAWEB.AUFRECHT` = CC BY-NC-SA, `VEDAWEB.ZURICH` = CC BY,
etc.). Only `VEDAWEB.AUFRECHT` is in the release, and flattening the mixed file to the more
restrictive class is the correct direction under RIGHTS-3. **Substantively sound.**

**But the release is not self-resolving.** `operational_semantics.UNKNOWN` is
`redistribute: no, redistribute_derived: no`. A downstream consumer applying the release's own
artifact table mechanically must conclude those 11 artifacts cannot be redistributed at all — and
the note directing them to `text_versions.yaml` points at a **registry file that is not in the
release**. The artifact-level `license_statement_verbatim` is *"For more information regarding
sources and their licences, please see: vedaweb_corpus.tei#vedaweb_header"* — a pointer, not a
statement, which is not the primary evidence RIGHTS-4 requires.

Compounding it, `rigveda_full_v1/manifest.json → rights_summary` keys on `GRETIL.RV.AUFRECHT`,
`GRIFFITH.RV.1896`, `VEDAWEB.AUFRECHT`, `VHP` — **not one of which is a `source_artifact_id`**, and
maps `VEDAWEB.AUFRECHT` to the permissive-ish `CC_BY_NC_SA` while every VedaWeb *artifact* in the
same manifest is `UNKNOWN`. Read the manifest and you see a licensed dataset; read the artifact
table and you see eleven artifacts you may not redistribute.

**Fix:** introduce an explicit `MIXED_SEE_TEXT_VERSIONS` disposition, or set the artifact rows to
the most restrictive class actually present, and ship the resolved per-version rights inside the
release.

### 5.4 Latent counter bug — `EXTERNAL_REFERENCE_ONLY` is not counted as restricted

`scripts/build_four_veda_completeness.py:172` computes `rights_restricted_text_records` over
`{REFERENCE_ONLY, PERMISSION_REQUIRED, RESEARCH_ONLY, UNKNOWN}`. **`EXTERNAL_REFERENCE_ONLY` is
missing** — the strictest usable class in the vocabulary (`copy_local: no`). No row currently uses
it, so there is no live defect; the first one that does will be silently counted as unrestricted.
The same counter treats `CC_BY_NC_SA` as unrestricted, which is defensible for a
"may-not-redistribute" metric but understates the RV position, where NC is a permanent commercial
bar.

### 5.5 Stale statement in the governing policy file — CLOSED DURING THIS PASS

`data/registry/rights.yaml` read: *"No VedaGraph artifact currently qualifies for CC0: it is
documented and available, but unused."* That became false when
`VEDAGRAPH.AVS.ROTH_WHITNEY_1856.TRANSCRIPTION` was dedicated CC0 and was already false for the 16
CC0 files inside `COMMONS.SV.KAU.SAMAN.AUDIO`.

**Corrected on disk by the coordinator while this verification was in progress.** The header now
records it as the third instance of a stale absence claim, and the `CC0` entry enumerates both
uses. Re-read and confirmed accurate. The new entry also states the composition direction
correctly — *"CC0 composes upward into a CC BY-SA artifact; the reverse does not hold"* — which
**independently corroborates §1.4**: the SV release manifest's `share_alike` note states the
opposite and is now in direct conflict with the governing policy file. §1.4 stands and should be
fixed against `rights.yaml`, not the other way round.

### 5.6 Missing retrieval date on a permissive status

`GRIFFITH.RV.1896.WIKISOURCE` is `PUBLIC_DOMAIN` with no `retrieval_date`. RIGHTS-4 requires
verbatim statement + URL + retrieval date for every permissive status. Pre-existing, low severity,
one field.

---

## 6. ACTION LIST

**Blocking a Sāmaveda text release**
1. Perform the codepoint-level independence diff at ≥ 3 adversarially-chosen loci outside the
   Purvarcika, against the already-held private GRETIL snapshot. Publish the verdict, never the
   text. (§1.3)

**Blocking an aggregate release**
2. Repoint the AV member of `four_veda_corpus_completeness.json` off `atharvaveda_pilot_v1`, or
   mark the aggregate as containing non-redistributable records. (§3.6)
3. Rights-partition `data/canonical/` so `samaveda_pilot_v1` (102 `PERMISSION_REQUIRED` rows) and
   `atharvaveda_pilot_v1` (459 `REFERENCE_ONLY`) cannot be swept into a distribution. (§3.6)

**Conditions on the Yajurveda release**
4. Record Panasikara's death date, or restate the 1929 PD basis without needing one; populate
   `upstream_print_rights_status`. (§2.2)
5. Add `WIKISOURCE_SA.YV.VSM.RISHISUCI` to `rights_summary`; give `traditional_metadata.jsonl` rows
   a `rights_status` and a `source_artifact_id`. (§2.3)
6. Add the share-alike notice to the YV manifest. (§2.4)

**Attribution hygiene, both CC BY-SA releases**
7. Carry `source_revision_id` onto `text_versions.jsonl`; add a `LICENSE`/`NOTICE` file to each
   release directory. (§1.2)

**Atharvaveda transcription**
8. Set `release_eligible: false` on the 16 accent-stripped units, or relabel the layer honestly.
   (§3.4)
9. Null `text_devanagari` on the 6 rows whose record says no reading was selected. (§3.5)
10. Track `unclear_marks_total` as a metric with a non-zero expectation; zero is a warning sign,
    not a pass. (§3.3)

**Registry**
11. `VEDAVANI.AV.SAUNAKA.WAV.HF` → `UNKNOWN`, Apache assertion moved to
    `license_statement_verbatim`. (§5.1)
12. Split or per-file the `COMMONS.SV.KAU.SAMAN.AUDIO` rights, and correct its "458 CC BY-SA"
    verbatim to the measured **459**. (§5.2)
13. Resolve the RV `UNKNOWN` artifact rows inside the release. (§5.3)
14. Add `EXTERNAL_REFERENCE_ONLY` to the restricted set in
    `scripts/build_four_veda_completeness.py`. (§5.4)
15. Fix the SV manifest's inverted CC0/BY-SA compatibility statement. (§1.4)
