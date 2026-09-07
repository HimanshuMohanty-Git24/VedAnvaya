# Four-Veda Canonical Sanskrit Blocker Closure

**Run:** `FOUR_VEDA_CANONICAL_SANSKRIT_BLOCKER_CLOSURE` · **Date:** 2026-09-07
**Branch:** `semantic-pilot-v1` · **Starting commit:** `e0b5ebd` · **Starting tree:** clean
**Registry:** [`data/source_registry/four_veda_canonical_sanskrit_blockers.yaml`](../../data/source_registry/four_veda_canonical_sanskrit_blockers.yaml)

---

## FINAL DECISION

> ## `FOUR_VEDA_CANONICAL_SANSKRIT_BLOCKERS_PARTIALLY_CLOSED`

Two of three blockers advanced materially; one remains open on a genuine external dependency.

| Veda | Verdict |
|---|---|
| **Śukla Yajurveda** (`VG:WORK:YV:VSM`) | **`YAJURVEDA_PRIMARY_TEXT_BLOCKER_CLOSED_WITH_REVIEW_ITEM`** |
| **Sāmaveda** (`VG:WORK:SV:KAU`) | **`SAMAVEDA_CANONICAL_IDENTITY_BLOCKER_REMAINS`** |
| **Atharvaveda** (`VG:WORK:AV:SAU`) | **`ATHARVAVEDA_PRIMARY_SOURCE_PD_TRANSCRIPTION_PATH_VALIDATED`** |

**Why not `CLOSED_WITH_AV_TRANSCRIPTION_WORKLOAD`.** That outcome requires *YV closed **and** SV
identity/source closed **and** AV PD path validated*. YV and AV hold; **SV does not**. No printed
edition could be identified behind the Sanskrit Wikisource Kauthuma transcription after four
independent search routes, so canonical identity cannot be frozen. Selecting the more favourable
label would mean freezing an identity on an unidentified edition — exactly what the standing
instruction forbids.

**Full SV/YV/AV canonical ingestion is NOT authorised.** See §9 for the exact blockers.

---

## 1. What each Veda actually achieved

### Yajurveda — coverage closed, role deliberately not upgraded

| | Before | After |
|---|---|---|
| Accented layer | 1,958 / 1,975 | **1,975 / 1,975** |
| Missing addresses | 17 | **0** |
| Parser | `v1`, accent-presence inference | **`wikisource-sa-vsm-v2`**, declared ordinal headers |
| VSM 16.37 | second reading **dropped** | **both readings preserved** (`SECOND_READING` / `NEEDS_REVIEW`) |
| Dedicated tests | **0** | **7** |

Address classification: **`PRIMARY_TEXT_AVAILABLE` 1,974** · **`PHILOLOGICAL_REVIEW_REQUIRED` 1**
(VSM 16.37) · `SOURCE_TEXT_MISSING` 0 · `PARSER_FAILURE` 0.

Verified independently **twice** — by the coordinator and again by the QA reviewer — each
re-parsing all 40 pinned snapshots. Deterministic rebuild: identical digest across three separate
OS processes, hashing records, failures, collisions and interventions.

**The role stays `EXTRACTED_FROM_CONTAINER`, and this is a permanent answer rather than a
deferral.** Rights clearance for the upgrade was given *in advance* and is not in doubt — role and
rights are orthogonal. The fidelity gate ruled against on three grounds, the third decisive because
it survives every available fix: the enum makes *boundary provenance* the discriminator, and even
after fixing all 9 parser-attributable cases, **27 units would still have no source-declared
boundary**. A layer-level `PRIMARY_TEXT` would make interpretive segmentation canonical for those
27. The correct resolution is **per-record boundary provenance**, specified for the next run.

### Sāmaveda — count closed, identity genuinely blocked

The 1,868 vs 1,875 gap is now **accounted for exactly**, re-derived independently:

```
structural tuples     = 1868
RN instances          = 1871   (= 1868 + 9 collision surplus - 6 zero-RN)
distinct RNs          = 1870   (= 1871 - 1 duplicate, RN 1181)
1875 - 1870           =    5   <- absent RNs [1035, 1133, 1179, 1211, 1592]
1870 - 1868           =    2   <- net structural residue
TOTAL                 =    7   OK
```

The honest framing is **5 individually identifiable absent RNs + a 2 net residue** — not seven
nameable verses. The residue decomposes into three competing mechanisms, and an earlier per-item
table that named two verses as "the 2" was a category error, since corrected.

**Edition identity remains unresolved and this is the binding blocker.** Four independent routes
were exhausted (top-level page, edit histories from 2011, targeted web search, category page → HTTP
404). No preface, no bibliography, no edition citation, and zero edit summaries referencing a
printed book. Two candidates surfaced; neither confirmable. This is an **established negative**, not
an unexamined gap — a real advance even though the state label is unchanged.

`identity_status: RESEARCH_REQUIRED` and `key_pattern: null` **stand**.

### Atharvaveda — moved the furthest

The public-domain route is **acquired and verified**, not merely identified:

**Roth, R. & Whitney, W. D.** *Atharva Veda Sanhita. Erster Band. Text.* Berlin: Ferd. Dümmler's
Verlagsbuchhandlung, 1856. 458 pp., Devanagari. *("No more published" — the promised notes volume
was never completed; the text volume is complete.)*

Acquired from **BSB/MDZ**, `urn:nbn:de:bvb:12-bsb10219750-9`, copy `4 A.or. 2840-1`, now registered
as source `BSB_MDZ`. Coverage verified **visually** across three sampled leaves:

| Leaf | Printed page | Content | SHA-256 |
|---|---|---|---|
| `n30` | १६ | AVŚ 2.4.5–6, 2.5, 2.6.1–3 | `179d816c50bab170…` |
| `n300` | २८७ | AVŚ 12.5 prose paryāya | `d331c2d0a7211c1d…` |
| `n420` | ४०७ | AVŚ 20.35.16, 20.36.1–11 | `47a3f2a923377920…` |

Text is accented and legible at 600 PPI, anudātta and udātta individually resolvable; a
transcription sample was produced from the image alone. **Kāṇḍa 20 is present** — confirmed from
body text, which matters because it is ~16% of the Veda and precisely the portion Whitney's
translation omits. *Unabridged* still rests on the preface, since leaf `n420` sits only 25.2% into
that kāṇḍa.

---

## 2. Two claims falsified during the run

Recording these because the reasoning errors generalise.

**(a) The coordinator's AVŚ 12.5 claim — falsified.** Leaf `n300` shows the prose paryāya carrying
two concurrent numbering systems (running clause numbers `॥२८॥…` plus parenthesised group numbers
`(२७)(२८)`). This was claimed as the generator of the 5,839→~5,977 divergence. The QA reviewer
corroborated the *observation* from the artifact and then killed the *inference* with a magnitude
test:

```
units inside group-bearing suktas : 2174     number of groups : 220
if prose counted by group         : 3889     (delta -1954)
delta actually needed             :  +138
```

Grouping moves the total **down ~1,954**; the gap needs **up 138**. Wrong direction, off by an
order of magnitude. Paryāya grouping **merges**; the gap requires **splitting**. What survives is
the weaker, sound claim: granularity conventions demonstrably vary in the source, concentrated in
prose books. **The count divergences remain unresolved.**

**(b) v1's "second readings" — largely manufactured.** `U+0966 ०` falls inside the YV adapter's
Devanagari word class, so v1 tokenised the commentator sigla `उ०`/`म०`/`मा०` as ordinal words and
parsed Uvaṭa's and Mahīdhara's **prose** as mūla. The v1 inline rule matched 39 accented lines, **34
of them siglum-initial false positives**; v2 matches 1, the genuine one. Earlier reports of ~31
"disappeared second readings" were describing the removal of false detections, not data loss.

---

## 3. A systemic registry defect found and fixed

`four_veda_source_matrix.yaml` carries a `corrections_applied:` block. **A correction recorded there
did not mean it had been applied to the data rows.** Audited: of nine corrections, **only CORR-8 had
ever been applied** — and it is the only one whose subject lives outside the matrix row block.

The file was therefore contradicting itself wherever a consumer read a *row* instead of a *summary*:

| Header/summary said | Row said |
|---|---|
| SV English = `GAP` | `selection: SELECTED` |
| SV primary = cleared | `selection: DEFERRED` |
| SV audio = 474 files, mirrorable | `DEFERRED`, `mirror_local: false` |
| YV edition = 1929 Nirṇaya Sāgara | `edition: UNIDENTIFIED` |
| TITUS = `PERMISSION_REQUIRED` | `rights_status: RESEARCH_ONLY` |

Applied this run: **CORR-1, 2, 3, 4, 5** (+ CORR-8 verified). **CORR-6** deliberately deferred — its
`now:` value `CONTESTED` is outside the declared `yes|no|conditional` domain and `direct_link` is a
*derived* field, so applying it literally would break the derivation rule; the recommended in-domain
resolution is recorded. **CORR-7** partially applied — the missing piece is an absent *row*, not a
wrong field, and concerns english_translation rather than canonical Sanskrit.

Corrections now carry an **`applied_to_rows:`** flag. The blocker registry's own transition log is
explicitly secondary to its `dimensions` maps for the same reason.

**A related scope gap:** the stale-claim audit certified "YV edition unidentified" as appearing
nowhere current. It was wrong — the claim was live in the machine-readable registry. That audit
grepped **`docs/` only**, and this project's operative claims live in `data/` YAML.

---

## 4. Rights outcomes

Adjudicated by the rights authority; applied by the coordinator.

| Veda | Verdict |
|---|---|
| YV | **CONFIRMED.** CC BY-SA 4.0 both layers; edition PD by age; share-alike live. Role upgrade pre-approved on rights grounds (declined on fidelity grounds) |
| SV | **CONFIRMED** (rights) / **CONDITIONALLY_CONFIRMED** (identity). Independence from the Pandey lineage proved *textually* |
| AV | **CONFIRMED**, conditional on RIGHTS-13 — now landed |

**`RIGHTS-13` (new).** *An independence firewall covers every channel by which an encumbered text
can reach a fresh transcription, including channels that leave no artifact.* Named channels:
transcriber recall, a colleague's correction, another edition on the desk, IME/autocomplete, **and
an LLM assistant** — identified as the *most likely* breach path for this project specifically,
because VedaGraph is operated by agents holding GRETIL/TITUS text in training that will complete an
unclear akṣara helpfully and silently if asked. Discovered when the coordinator recognised AVŚ
20.36.1 as the Rigveda parallel RV 6.19.1 while reading leaf `n420`; Kāṇḍa 20 is largely Rigvedic,
so the temptation recurs across a large fraction of its 959 units. Scope is **all four Vedas**.

**`RIGHTS-10`, sixth instance and a new sub-type.** The archive.org copy is tagged `CC BY 3.0` by an
uploader, but every sampled leaf carries a **"Digitized by Google"** watermark — a Google Books
re-upload where the tagger is not even the digitiser. Void for want of standing twice over.
Instances 1–5 were all *permissive-tag-over-restrictive-print* and are caught by reading the print;
this one is caught **only by inspecting a page margin**, which is why it survived a full research
pass and surfaced only when actual images were opened.

**Two corrections to the coordinator's own reasoning**, both adopted:

1. PD status derives from **1856 + Roth d. 1895 / Whitney d. 1894** (RIGHTS-7), **not** from BSB's
   stamp — no digitiser has standing to establish PD. What BSB uniquely supplies is standing to
   **disclaim the scan-layer right** (UrhG §72). A party without standing to *grant* may still
   *waive* what it could itself assert. The DDB non-commercial tag is structurally without standing
   (aggregator downstream of BSB, RIGHTS-9) — not a metadata glitch.
2. Licensing a transcription of PD text as CC BY-SA would be **copyfraud**, the same thing RIGHTS-10
   condemns in others. Output licence must **split**: transcribed text **CC0/PD**, only VedaGraph's
   structural apparatus under a VedaGraph licence. CC0 composes upward inside CC BY-SA, so no
   conflict with live YV/SV share-alike obligations.

---

## 5. Adversarial QA verdicts

| Veda | Verdict |
|---|---|
| YV | **PARTIALLY_CONFIRMED** — every headline claim reproduced; held short by the role ruling, 9 of 36 fallbacks being parser-attributable, and (at ruling time) zero dedicated tests |
| SV | **PARTIALLY_CONFIRMED** — aggregate gap closed exactly; itemisation defects corrected; running-number finding confirmed **and cross-source corroborated** |
| AV | **PARTIALLY_CONFIRMED** — verdict correct and appropriately scoped; 12.5 generalisation falsified; "unabridged" qualified; exit gate reconciled |

Two QA findings were themselves **stale** and withdrawn after verification against live code and
data: a YV `G11` provenance failure (the dotted artifact ids it named no longer exist; the
underscore-form ids are registered, and the loader raises on an unregistered id) and 13 AV
`validate_corpus` errors from `source_id="VEDAGRAPH"` (live output has 177 assertions — 175 GRETIL,
2 VEDAWEB, zero VEDAGRAPH). Both described a prior session's defects, since fixed.

**A cross-source corroboration worth keeping.** Sanskrit Wikisource labels Sāmaveda verses with the
edition's **running numbers**, not daśati-local indices — daśati 5 yields 45–54, Āraṇya 1.2.1 yields
586–594 — and GRETIL independently gives exactly `[45..54]` and `[586..594]`, agreeing also on
non-uniform daśati sizes. Since those two lineages are *proved* textually independent, this is
genuine corroboration rather than the same-defect-twice pattern. Any Wikisource re-point must
convert running → local explicitly and must never use page position.

---

## 6. Gate results

| Gate | Result |
|---|---|
| Test suite | **681 passed, 1 skipped, 0 failed** (skip = pre-existing missing `openai`) |
| New YV tests | **7 added, 7 passing** — `-k "yajurveda or vsm"` now selects 9 (was 2) |
| Ruff | **All checks passed** |
| mypy `--strict` | **Success, 101 source files** — was 3 pre-existing errors, now 0 |
| Rigveda regression | **PASS** — 6/6, identity fixtures frozen |
| Deterministic rebuild | **PASS** — YV identical across 3 OS processes |

**One mypy error was a live runtime bug, not a typing nit.** `SourceAdapter.to_staging_records()`
calls `self.parse(path, snapshot_id=...)` generically, and `SamavedaWikisourceAdapter.parse()` had
added four *required* keyword arguments — so calling it would raise `TypeError`. Fixed by renaming
the coordinate-taking method to `parse_at_address()` and giving `parse()` a contract-conforming
signature that raises with an explanatory message. This matters because the SV recommendation is to
re-point the build onto that very adapter.

---

## 7. Scope discipline — what was deliberately NOT done

- **VSM 16.37 not resolved.** A genuine choice between two attested printed readings; reserved for
  recorded human review. Both readings preserved.
- **SV identity not frozen.** No edition found, so no freeze — the downstream desire for a stable ID
  is not evidence.
- **AV transcription not performed.** ~5,839 mantras is bounded labour, not research; a pilot
  proves the path, not the corpus.
- **No Rigveda semantic work, no full-corpus extraction, no Neo4j, no GraphRAG, no frontend.**
- **No sealed semantic artifacts mutated.**

**Vocabulary kept distinct throughout**, since collapsing these is the failure mode the brief names:
*source found* ≠ *source rights clear* ≠ *edition identified* ≠ *parser works* ≠ *primary text
complete* ≠ *canonical identity final* ≠ *full corpus ingested*. Concretely: AV rights and
acquisition are `RESOLVED` while `transcription_labour` is a **separate open dimension**, added
precisely so "rights clear + source acquired" cannot be read as "corpus complete".

---

## 8. Remaining engineering workload

| Veda | Work | Kind |
|---|---|---|
| YV | Per-record boundary provenance (header-declared vs inferred) | Engineering, specified |
| YV | Two-pass ordinal-vocabulary fix for 8 of 9 parser cases — **validated, 0 false positives** | Engineering, specified |
| YV | Nullable `chandas` + YV devatā union type | Schema |
| SV | Running→local index conversion; 840-page fetch **pinning per-page revision ids** | Engineering |
| SV | Adapter must read **declared** boundaries — the Wikisource text is printed with Sāyaṇa's commentary and will otherwise reproduce the YV container problem | Engineering, forewarned |
| AV | Full transcription under RIGHTS-13, ~60–120 person-hours | Labour |

## 9. Unresolved external dependencies

1. **SV printed edition identity** — the single blocking fact. Four routes exhausted; requires a new
   source or chain of title. **This is what prevents full ingestion authorisation.**
2. **VSM 16.37** — human philological decision. Non-blocking for the other 1,974 addresses.
3. **AV 731 vs 730 sūktas and 5,839 vs ~5,977 mantras** — require a second complete edition.
   Non-blocking for the primary text; counts are recorded as data.
4. **A human must confirm scan legibility** before committing to full AV transcription. The
   coordinator's three-leaf sample is evidence, not sign-off.

**`NEXT_PROJECT_PHASE` is NOT `FULL_SV_YV_AV_CANONICAL_INGESTION`.** Sāmaveda cannot be canonically
ingested while `key_pattern` is null and `identity_status` is `RESEARCH_REQUIRED`; Atharvaveda has
no transcribed Sanskrit yet. Yajurveda's Sanskrit layer *is* ingestion-ready at 1,975/1,975 with
stable identity — but its accented layer must not be selected as `primary_sanskrit`, since it
remains `EXTRACTED_FROM_CONTAINER` by deliberate decision.

---

## 10. Cross-references

- Per-Veda reports: [YV](YAJURVEDA_PRIMARY_TEXT_CLOSURE.md) · [SV](SAMAVEDA_IDENTITY_SOURCE_CLOSURE.md) · [AV](ATHARVAVEDA_PRIMARY_SOURCE_CLOSURE.md)
- Blocker registry: [`four_veda_canonical_sanskrit_blockers.yaml`](../../data/source_registry/four_veda_canonical_sanskrit_blockers.yaml) · [human mirror](../FOUR_VEDA_CANONICAL_SANSKRIT_BLOCKERS.md)
- Rights: [`rights.yaml`](../../data/registry/rights.yaml) (RIGHTS-10 §6, RIGHTS-13) · [`four_veda_source_matrix.yaml`](../../data/source_registry/four_veda_source_matrix.yaml)
- Stale-claim audit: [`STALE_FOUR_VEDA_CLAIMS.md`](../qa/STALE_FOUR_VEDA_CLAIMS.md)
