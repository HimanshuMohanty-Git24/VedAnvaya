# Four-Veda Canonical Sanskrit Blocker Registry

**Compiled:** 2026-09-07 · **Checkpoint:** `dc7d202` (feat: establish four-Veda ingestion
architecture and remaining corpus pilots)
**Last updated:** 2026-09-07 from `dc160d7` by `SAMAVEDA_CANONICAL_IDENTITY_FINAL_CLOSURE`,
which rewrote §2 (SV). That run closed the Sāmaveda source-edition question and then found it
was **not** the binding constraint; two new SV dimensions carry the real blocker
(`referent_integrity`, `arcika_arity`). §1 (YV) and §3 (AV) are unchanged and were not reopened.
**Machine-readable mirror:** `data/source_registry/four_veda_canonical_sanskrit_blockers.yaml`
(moved from the originally-scoped `data/qa/` path, which is gitignored build-output space —
see the note in the YAML file)
**Purpose:** consolidate the current, evidence-backed state of the three open canonical-Sanskrit
blockers (YV, SV, AV) so the next session — `FOUR_VEDA_CANONICAL_SANSKRIT_BLOCKER_CLOSURE` — can
start from a single registry instead of re-deriving state from `FOUR_VEDA_SOURCE_ADJUDICATION.md`,
`FOUR_VEDA_RIGHTS_MATRIX.md`, `FOUR_VEDA_STRUCTURAL_MODEL.md` and the three pilot reports.

This document does not resolve anything. It restates what those documents already established, in
one place, with an explicit state vocabulary. Rigveda is out of scope: its Sanskrit layer is
`READY_WITH_LIMITATIONS` and its semantic layer is frozen at V3.2 pending human gold — see
[`docs/STATUS.md`](STATUS.md).

---

## 0. Blocker states

A blocker may carry **multiple simultaneous dimension states** — rights, engineering, source
identity and philological review are never collapsed into one value. The vocabulary is closed at
six members:

| State | Meaning |
|---|---|
| `OPEN_RESEARCH` | The fact needed is not yet known; more investigation (not engineering) would change the answer. |
| `OPEN_ENGINEERING` | The fact is known; a coding/parsing task remains to realize it in the corpus. |
| `OPEN_RIGHTS` | Redistribution/derivation permission is not established for the needed artifact. |
| `OPEN_PHILOLOGICAL_REVIEW` | A human editorial/variant-selection judgement is required (e.g. choosing between two attested readings). |
| `RESOLVED` | The dimension is closed and evidenced. |
| `DEFERRED_NONBLOCKING` | Known gap, explicitly not required for this closure (e.g. gāna coverage, Hindi translation). |

Per the adjudication reports' own closing method: a dimension is `OPEN_RESEARCH` only if new
*research* would change the label; if only a new *source* or a *different chain of title* would
change it, the correct label is `RESOLVED` for identity/rights-investigation purposes even when the
practical outcome is negative — the negative answer is itself the resolved state of that dimension.
Where this registry marks something `OPEN_RIGHTS` it means an unresolved *permission*, not an
unresolved *investigation*.

---

## 1. YV — Śukla Yajurveda / Vājasaneyi Mādhyandina (`VG:WORK:YV:VSM`)

**Verified repository facts** (`docs/FOUR_VEDA_SOURCE_ADJUDICATION.md` §3.3,
`docs/FOUR_VEDA_RIGHTS_MATRIX.md` §3.3, `docs/pilots/YAJURVEDA_PILOT.md`,
`data/registry/works.yaml`):

| Fact | Status |
|---|---|
| 40 adhyāyas, 1,975 mantra addresses | **CONFIRMED** — computed from the full-artifact scan the pilot's adapter already runs (`YAJURVEDA_PILOT.md` "Scale-up readiness") |
| Hierarchy `Adhyaya -> Mantra`, two levels, no Sukta | **CONFIRMED**, `identity_status: FINAL` in `works.yaml` |
| Sanskrit Wikisource artifact rights-clear | **CONFIRMED** — `CC_BY_SA`, both layers, `FOUR_VEDA_RIGHTS_MATRIX.md` §3.3 |
| Edition identified: Paṇaśīkara / Nirṇaya Sāgara Press / 1929 | **CONFIRMED** — found on a sibling preface page, not the per-adhyāya header (`FOUR_VEDA_SOURCE_ADJUDICATION.md` §3.3, CORR-4) |
| Faithful layer incomplete | **CONFIRMED** — `WIKISOURCE_SA.YV.VSM.UNACCENTED`, 1,836/1,975, `PARALLEL_TEXT` |
| Complete layer cannot be labelled `PRIMARY_TEXT` | **CONFIRMED** — `WIKISOURCE_SA.YV.VSM.ACCENTED`, 1,958/1,975, `TextRole.EXTRACTED_FROM_CONTAINER`; role governed by `data/registry/text_versions.yaml` via `load_text_versions()` |
| VSM 16.37 variant requires explicit review | **CONFIRMED** — page prints `स्रुत्याय` / `सत्याय` twice; current build keeps the first and records `SECOND_READING_DROPPED` as `NEEDS_REVIEW` |
| Ordinal-header reconstruction is a possible technical path | **CONFIRMED, NOT ATTEMPTED** — 271 ordinal-header lines measured against 293 accented records across 6 sampled adhyāyas; adapter currently infers mūla start from accent-presence only |
| ~2,106 machine-readable ṛṣi assertions at full scale | **PROJECTED, NOT YET BUILT** — pilot has 203 across 4 sampled adhyāyas; full-40 figure is a stated extrapolation in `YAJURVEDA_PILOT.md`, not a completed run |
| No devatā/chandas claims invented | **CONFIRMED as policy** — Sarvānukramaṇa-sūtra states many yajus have no metre at all; schema does not yet carry a nullable-with-reason-code chandas field for YV |

**Primary blocker question:** *Can we deterministically produce a faithful 1,975/1,975
`PRIMARY_TEXT` layer from the already-approved artifact without making philological guesses?*

| Dimension | State | Note |
|---|---|---|
| Rights | `RESOLVED` | Both layers CC BY-SA 4.0; no encumbered link in the chain (`FOUR_VEDA_SOURCE_ADJUDICATION.md` §3.3) |
| Source identity | `RESOLVED` | Edition named (1929 Nirṇaya Sāgara), artifact complete |
| Engineering | **`RESOLVED`** (was `OPEN_ENGINEERING`) | Adapter reimplemented as `wikisource-sa-vsm-v2`, reading declared ordinal headers as the primary signal. **1,958 → 1,975 / 1,975**, zero missing. Reproduced independently *twice* (coordinator + QA), each re-parsing all 40 pinned snapshots. Deterministic rebuild identical across three OS processes |
| **Boundary provenance** | **`OPEN_ENGINEERING`** (new dimension) | **1,939 of 1,975 units are header-declared; 36 fall back to accent-presence inference** — reported, not silent. Root-caused: **9 parser** (8 where the header exists but the source omits its trailing daṇḍa; 1 state-machine reset), **27 source** (22 header consumed by the preceding mūla, 3 no header within six lines) |
| Philological review | `OPEN_PHILOLOGICAL_REVIEW` | VSM 16.37 (`स्रुत्याय` vs `सत्याय`) still requires a recorded **human** decision. **Handling improved: both readings now preserved** — v1 dropped the second, v2 keeps it in full as `SECOND_READING` / `NEEDS_REVIEW`. A *preserved* variant is not a *resolved* variant |
| Metadata schema | `OPEN_ENGINEERING` | Nullable `chandas` with `anādiṣṭa`-vs-unknown reason code, and a YV-specific devatā union type, do not exist yet. Untouched by this run |

**Answer as of the closure run:** **yes for coverage** — a faithful 1,975/1,975 layer is produced
deterministically from the approved artifact, with no invented Sanskrit and no silent variant
selection.

### The `text_role` decision, and why it is permanent rather than deferred

`WIKISOURCE_SA.YV.VSM.ACCENTED` **stays `EXTRACTED_FROM_CONTAINER`.** The rights authority cleared
the upgrade *in advance* and correctly held that it carries zero rights consequence, then deferred
to the fidelity gate. The fidelity gate ruled against it on three independent grounds:

1. **The header-reading condition is literally unmet** — 8 declared ordinal headers demonstrably
   exist in the source and are still not read. Proved, not inferred: in **8 of 8** cases the ordinal
   word names exactly the mantra number the run resolved to (अष्टाविंशी→28, षट्षष्टी→66,
   अष्टषष्टी→68, सप्तचत्वारिंशी→47, एकविंशी→21, षोडशी→16, एकचत्वारिंशी→41, द्विचत्वारिंशी→42).
2. **Both `NEEDS_REVIEW` assertions remain open**, and VSM 16.37 is unmeetable by any agent.
3. **The enum's own definition forbids it, and this ground survives every available fix.**
   `EXTRACTED_FROM_CONTAINER` makes *boundary provenance* the discriminator: a layer whose unit
   boundaries are "an editorial judgement rather than a boundary the source declared" must never be
   selected as primary. Even after fixing all 9 parser cases, **27 units would still have no
   source-declared header** — the source simply does not declare one there. A layer-level
   `PRIMARY_TEXT` would make interpretive segmentation canonical for those 27.

So the honest answer to *"will this become `PRIMARY_TEXT` once the regex is fixed?"* is **no**, not
"not yet". **The recommended resolution is per-record, not per-layer:** carry boundary provenance on
each record (header-declared vs inference-derived), keeping the layer role permanently accurate —
the mūla genuinely *is* quoted inside the Uvaṭa–Mahīdhara bhāṣya — while letting a consumer select
the header-declared units with full confidence.

**A validated fix for 8 of the 9 parser cases is recorded so it is not re-derived.** Naive fixes
were measured and are unsafe: making the daṇḍa optional *with* the v2 lookbehind breaks **280**
working headers; *without* it admits **339** false lines including `अध्यायः ३` and bare mantra
fragments. The safe form is two-pass and self-calibrating — harvest ordinal vocabulary from
daṇḍa-bearing matches (490 strings), then accept a daṇḍa-less line only if its exact text is in that
vocabulary. Tested end-to-end: **8 accepted, 8/8 targets covered, zero false positives.**

### A v1 defect that inverts an earlier belief

`U+0966 ०` falls inside the adapter's Devanagari word class, so v1 tokenised the commentator sigla
`उ०` / `म०` / `मा०` as ordinal words and parsed Uvaṭa's and Mahīdhara's **prose** as mūla. Measured:
the v1 inline rule matched 39 accented lines, **34 of them siglum-initial false positives**; the v2
rule matches 1 — the genuine one. The "second readings" v1 reported were therefore largely
*manufactured out of commentary*, not variant readings in the print. Now pinned by regression tests
in `tests/unit/test_yajurveda_primary_text.py`.

---

## 2. SV — Sāmaveda / Kauthuma (`VG:WORK:SV:KAU`)

**Verified repository facts** (`docs/FOUR_VEDA_SOURCE_ADJUDICATION.md` §3.2,
`docs/FOUR_VEDA_RIGHTS_MATRIX.md` §3.2, `docs/FOUR_VEDA_STRUCTURAL_MODEL.md` §2/§7,
`docs/pilots/SAMAVEDA_PILOT.md`, `data/registry/works.yaml`):

| Fact | Status |
|---|---|
| Parser works | **CONFIRMED** — pilot: 3,714 verse lines → 1,868 verse keys from a TEI with no structural markup; 12/12 own gates PASS, byte-identical rebuild over 3 runs |
| Hierarchy discovery works | **CONFIRMED** — 5 levels (`Arcika, Prapathaka, Ardha, Dasati, Verse`), variable depth (1–5), absent levels encoded `0`; corroborated by 2 independent textual witnesses (Sanskrit Wikisource, Griffith 1895/Benfey) + 1 independent addressing scheme (TITUS, text non-independent) |
| Dasati correction exists | **CONFIRMED** — supersedes the earlier VHP-derived guess `[Arcika, Prapathaka, Ardha, Adhyaya, Khanda, Mantra]`; the fourth level is `Dasati`, there is no `Adhyaya`/`Khanda` identity level (`works.yaml` note, `FOUR_VEDA_STRUCTURAL_MODEL.md` §2, §5.2) |
| ~~Canonical identity/key not final~~ | **SUPERSEDED 2026-09-07 by `SAMAVEDA_REFERENT_INTEGRITY_REPAIR`.** `identity_status: FINAL`, `key_pattern` declared. The key **names** the four collections instead of numbering them: `VG:SV:KAU:{CHANDA\|ARANYA\|MAHANAMNYA\|UTTARA}[:P..][:R..][:D..]:V..`. Coverage is tracked separately and is `INCOMPLETE_BOUNDED` (1,844 of 1,875) |
| Wikisource rights position better than Pandey/GRETIL/TITUS lineage | **CONFIRMED on rights, with the independence grade corrected** — Sanskrit Wikisource is `CC_BY_SA`. Its independence from the Pandey 1998/99 e-text is graded `NOT_A_VERBATIM_COPY`, **not** "proven": the claim rests on one locus, and this run found the *opposite* signal at three further loci — running number 1179 typeset as a second 1181, and single-daṇḍa terminators at 1133 and 1592, all present in **both** lineages. Not load-bearing for identity; **is** load-bearing for text redistribution. **Never cite "840 pages" as this work's coverage** — 725 of them are gāna and out of scope; the arcika corpus is **106** pages |
| ~~Edition identity/provenance remains the key issue~~ | **SUPERSEDED 2026-09-07.** It was *not* the key issue. Edition identity is settled as an established negative and shown **not** to gate Passage identity at all — a category error, since nothing edition-valued reaches a UUID and no RV/YV/AV entry names an edition either. The key issues are **referent integrity** and **arcika arity**, both discovered in the final closure run. The "no witness combines an identified printed edition with redistribution rights" framing remains true as a statement about *witnesses*, and is the ADR-017 bar; it is simply not what blocks the key |
| Structural count discrepancy ~1,868 vs 1,875 | **RECONCILED EXACTLY** (2026-09-07) — `UNRESOLVED_COUNT_RESIDUE = 0`. The source prints **exactly 1,875** verse-terminal markers, so `1875 = 1868 distinct addresses − 2 markerless + 9 surplus`. Four counts are all correct of four different things: printed markers **1875**, markers the adapter can lift **1871**, distinct addresses **1868**, canonical keys minted **1866**. Verdict: **100% apparatus, 0% text** |
| Gāna must not be forgotten | **CONFIRMED as explicit scope limit, not yet addressed** — `VG:WORK:SV:KAU` addresses the arcika (verse) text only; ~2,639 gānas vs 1,875 arcika verses is a **larger**, parallel body requiring its own future `work_id`. Sanskrit Wikisource carries all four gāna books as reusable text |
| Audio inventory contains a mirrorable Commons path | **CONFIRMED** — 474 Wikimedia Commons files (458 `CC_BY_SA`, 16 `CC0`), verified per file; the **only** mirrorable audio across all four Vedas |

**Primary blocker question:** *Can we establish a redistributable, edition-defensible Kauthuma
canonical witness and freeze stable passage identity?*

| Dimension | State | Note |
|---|---|---|
| Rights | `RESOLVED` for ingestion and identity | Wikisource `CC_BY_SA`, read authoritatively from the MediaWiki `rightsinfo` endpoint; 474 Commons audio files cleared per-file. **Not** cleared by "proven textual independence" — that grade was `NOT_A_VERBATIM_COPY` and three shared-defect loci now point the other way, so **bulk text release** additionally needs the codepoint re-check below |
| Source/edition identity | **`RESOLVED`** (was `OPEN_RESEARCH`) | **`RESOLVED` = the investigation is closed and the answer is NEGATIVE.** No edition was identified, and there is **none to find**: the pinned corpus is *positively* shown to be hand-keyed — not scan-backed (0 templates, 0 `पृष्ठम्:` links), no front matter anywhere across all **908** enumerated titles, **0 links to any Sāmaveda scan across 840+ pages**, and contributor testimony of `टंकणम्` ("typing"). **Both candidates refuted** — `बन्सल` returns **0 hits wiki-wide**. A prior route was a **false negative by construction**: it probed `चर्चा:`, the *Hindi* talk prefix, on a wiki that uses `सम्भाषणम्:` |
| **Printed-edition recension** | **`OPEN_RESEARCH`** (NEW) | A 5-volume PD edition was **located** — Sāmaśramī, Bibliotheca Indica, 1874–78, with Sāyaṇa's bhāṣya — via the `अनुक्रमणिका:` namespace no prior route probed. Does **not** close the blocker: unproofread raw OCR, vols 4–5 not on Commons, **recension not established** (Griffith's preface assigns it to Rāṇāyanīya). **Exact action:** fetch vol 1 pp. 1–9 from `in.ernet.dli.2015.487112` and have a specialist read the title page |
| **Addressing edition-independence** | **`RESOLVED`** (NEW, positively) | **All five levels are printed in the colophons of an identified edition.** `इति चतुर्थस्यार्धः प्रपाठकः` (vol 1 p. 693) settles **ardha** as printed, not editorial. Uttarārcika ardha fingerprint `[2,2,2,2,2,3,3,3,3]` from 5 witnesses / 3 lineages; **21/21** ardha closing boundaries identical GRETIL vs Wikisource. Wikisource's omission of ardha in the Pūrvārcika is an **economy, not a denial** — it drops exactly the derivable copy |
| Structural count | `RESOLVED`, mechanism **corrected** | Gap accounted for exactly; `UNRESOLVED_COUNT_RESIDUE = 0`. **The recorded mechanism was refuted:** the source prints **exactly 1,875** markers, so `1875 = 1868 − 2 markerless + 9 surplus`. Only **1179** is genuinely unprinted (typeset as 1181); **1035, 1133, 1211 and 1592 ARE printed** and lost to regex strictness. The old "5 + 2" split becomes 2/5 then 1/6 under tolerant regexes — **only the 7 is invariant** |
| **Referent integrity** | **`RESOLVED`** (was `OPEN_ENGINEERING`) | Repaired and **gated**. The whole previous defect set — 7 welded addresses, 9 surplus markers, the phantom `A4:P04:R2:D01:V13` — was forensics on the **rejected** witness. The real defect on the canonical path was worse: `parse_at_address` took the address from the *caller* and wrote the samhita **running** number into the identity-bearing verse slot. The repair makes the class **unrepresentable** rather than patching instances. Measured on the full selected corpus: **1,844 keys, 0 collisions, 0 splits** |
| **Arcika arity** | **`RESOLVED`** (was `OPEN_PHILOLOGICAL_REVIEW`) | **Dissolved as an identity question, not adjudicated.** It was binding only because the top slot was a bare **ordinal**. The key now **names** the four collections, whose extents 585/55/10/1225 **no witness disputes**. Cross-witness: collection assignment agrees **1,867 / 1,867, zero disagreements**. The philological question (are Chanda/Āraṇya/Mahānāmnya siblings of Uttara or children of a Pūrvārcika; does "Pūrvārcika" reach 585 or 650?) is **still open and is now a documentation matter** — answering it renumbers nothing |
| Engineering (parser/hierarchy) | `RESOLVED` | Rewritten. Six source-syntax families the old parser could not read are now handled **by syntax class**, not by verse id |
| Engineering (re-point to Wikisource) | **`RESOLVED`** (was `OPEN_ENGINEERING`) | Done. **106 arcika pages** fetched and pinned with per-page `sha256` + `revid`; the selected witness is now the primary and the rejected artifact can no longer mint identity at all |
| **Arcika coverage completeness** | **`OPEN_ENGINEERING`** (NEW) | **31 of 1,875 verses carry no key** — a *coverage* gap, not an ambiguity. 2 running numbers the witness does not print (**1179**, 1315); 9 verses in one daśati whose printed run is non-contiguous; 21 verses in **4** Uttarārcika daśati groups where the witness omits a daśati heading. The **whole** affected daśati is withheld in every case, so filling it later **adds** keys without renumbering any |
| **Independence codepoint re-verification** | **`OPEN_RESEARCH`** (NEW) | Gates public **release** of the Sanskrit, not ingestion or identity. Required by the sole rights authority at **> 2 loci** at codepoint level before any bulk text release, outside the Pūrvārcika defect-free zone |
| English translation | `DEFERRED_NONBLOCKING` | A GAP, not a blocker for Sanskrit identity: Wikisource Griffith is empty, and sacred-texts Griffith is the wrong recension (Rāṇāyanīya) |
| Gāna coverage | `DEFERRED_NONBLOCKING` | Explicit future `work_id`, not required to close the arcika question. Gāna sections **interleave** with arcika text on the same pages and are excluded **by notation** (the Devanāgarī Extended combining svara marks), never by position |

**Answer as of the referent-integrity repair (2026-09-07):
`SAMAVEDA_REFERENT_INTEGRITY_REPAIRED_WITH_BOUNDED_REVIEW`.**
`identity_status: FINAL`; `key_pattern` and `urn_pattern` declared; the referent-integrity
gate is enabled; `coverage_status: INCOMPLETE_BOUNDED`.

**What actually closed the blocker was auditing the right corpus.** The previous run measured
the defect set on the GRETIL artifact — which is `PERMISSION_REQUIRED` and was never going to be
the canonical source — while only **29 verses (1.55%)** of the *selected* witness were pinned,
all three pinned pages sitting in the one region with **zero** defects. This run fetched the
rest: **106 pages**, 74 Pūrvārcika + 32 Uttarārcika.

**Two design decisions carry the repair.**

1. **The top slot is a name, not an ordinal.** Slot-1 value `2` meant Āraṇyārcika in the Pandey
   lineage and Uttarārcika in all six independent witnesses — a **1,225-verse** collision. Every
   witness holds the *same four blocks in the same order with the same extents*, so naming them
   records exactly what is agreed and leaves the bracketing to the container spine. The four
   **sub**-collections are named rather than the two top-level groupings because the extent of
   the name "Pūrvārcika" is *itself* disputed (585 in Caland and Vedapeetha, 650 elsewhere).
2. **A level a collection does not declare is omitted, never written as `0`.** Writing `0` made
   the rejected edition's flattening choice part of canonical identity, and made "the text has
   no ardha here" indistinguishable from "the edition declined to number it". `ardha` is
   therefore present only in the Uttarārcika, where it is load-bearing because daśati **resets**
   inside each ardha; it is absent from the Chanda key even though a printed edition asserts it
   there, because admitting a redundant level would make the print's competing convention
   *ambiguously representable* instead of unrepresentable.

**A binding invariant now exists that did not before.** `models.PassageReferentBinding` records,
per released key, the source artifact, locator, revision, snapshot digest, printed verse marker,
raw text SHA-256 and a normalization-independent comparison SHA-256. `vedagraph.referent` fails
the build when a key changes what it denotes without a recorded migration. The baseline is
**committed** at `tests/fixtures/identity/sv_referent_baseline.jsonl` because `data/derived/**`
is gitignored — a baseline written there would silently not be a baseline. The fingerprint is a
**guard, never an identity input**: keys stay source-independent and replacing a TextVersion
cannot change one.

**One finding that cuts against the independence claim, recorded rather than buried.** Running
number 1179 is typeset as a second 1181 in **both** lineages at the same locus, and so are
single-daṇḍa terminators at 1133 and 1592. Either common descent or a shared print antecedent;
this run does not adjudicate. It is direct evidence for the codepoint re-verification item.

Full detail:
[`SAMAVEDA_REFERENT_INTEGRITY_REPAIR.md`](reports/SAMAVEDA_REFERENT_INTEGRITY_REPAIR.md) ·
[`SAMAVEDA_ARCIKA_ARITY_DECISION.md`](reports/SAMAVEDA_ARCIKA_ARITY_DECISION.md) ·
[`SAMAVEDA_FINAL_IDENTITY.md`](reports/SAMAVEDA_FINAL_IDENTITY.md) ·
[`SAMAVEDA_REFERENT_MIGRATION.md`](reports/SAMAVEDA_REFERENT_MIGRATION.md)

**Still true and carried forward:** the Wikisource Sāmaveda is printed **with Sāyaṇa's
commentary**. The repaired adapter reads *declared* boundaries and strips `<ref>`, templates and
apparatus rather than inferring mūla, but the `text_role` decision belongs in the registry and
the container hazard is real. Sāyaṇa is 14th century, so this is a **role** hazard, not a rights
one.

---

## 3. AV — Atharvaveda / Śaunaka (`VG:WORK:AV:SAU`)

**Verified repository facts** (`docs/FOUR_VEDA_SOURCE_ADJUDICATION.md` §3.4,
`docs/FOUR_VEDA_RIGHTS_MATRIX.md` §3.4, `docs/pilots/ATHARVAVEDA_PILOT.md`,
`data/registry/works.yaml`):

| Fact | Status |
|---|---|
| Parser works | **CONFIRMED** — 11,395 pāda-level tokens → 5,843 units across all 20 kāṇḍas, 0 unparsed tokens, byte-identical rebuild across two processes |
| 20 kāṇḍas | **CONFIRMED**, `identity_status: FINAL` |
| 731 sūktas | **CONFIRMED, computed from the artifact** — a real +1 divergence against the commonly cited 730, traced to edition-counting, not a parser defect |
| Current source-derived mantra count | **CONFIRMED, computed: 5,839 distinct mantras** (11,395 pādas; `Units` 5,843 exceeds distinct mantras by 4 locator collisions) — divergence against the commonly cited ~5,977 is reported, not resolved, and attributed to edition-relative verse totals (e.g. one Roth/Whitney verse = 8 Vishva Bandhu verses at 15.2.1) |
| Orlandi/TITUS/GRETIL/VedaWeb lineage cannot currently be used as redistributable canonical Sanskrit | **CONFIRMED** — all three hosting surfaces (TITUS, GRETIL `avs_*`, VedaWeb AVS Sanskrit) are proved to be **the same Petr/Vavroušek text**, i.e. one licensing dependency, not three; GRETIL is `REFERENCE_ONLY`, TITUS is `PERMISSION_REQUIRED`, root is Orlandi 1991 (still in copyright) |
| Paippalāda must never be substituted for Śaunaka | **CONFIRMED as enforced control** — `assert_saunaka_recension()` requires two independent in-artifact witnesses (document title + all 11,395 `AVŚ_`-prefixed locators) before any parse; GRETIL's Paippalāda TEI is never opened by this adapter |
| Roth & Whitney 1856 is the identified PD route | **CONFIRMED, NOT YET ACQUIRED** — public domain by age; no transcription or OCR has been performed (explicitly out of scope for this preflight and for the closure session per the source-adjudication ranking) |
| Permission from the rights holder is an alternative route | **CONFIRMED, NOT YET SOUGHT** — highest-ranked action in `FOUR_VEDA_SOURCE_ADJUDICATION.md` §7: one written permission to the TITUS Project would unlock TITUS + GRETIL + VedaWeb simultaneously |
| Existing encumbered digital text may be used only to the extent already recorded, never as a laundering base | **CONFIRMED as standing constraint** — every `TextVersion` in the pilot carries `rights_status: REFERENCE_ONLY`; the pilot exists to prove parsing/structure/translation-alignment machinery, not to seed a "clean" transcription |

**Primary blocker question:** *Can we obtain/build a legally clean, provenance-explicit Śaunaka
primary Sanskrit layer without laundering the modern Orlandi-derived digital text?*

| Dimension | State | Note |
|---|---|---|
| Rights | **`RESOLVED`** (was `OPEN_RIGHTS`) | For the **PD route only**. PD derives from the *work* — 1856, Whitney d. 1894, Roth d. 1895 (RIGHTS-7) — and from no digitiser's stamp. The Orlandi/TITUS/GRETIL/VedaWeb lineage remains `REFERENCE_ONLY` and is **not** unlocked by this |
| Source identity / recension | `RESOLVED` | Śaunaka proved from the artifact itself (title + all locators), Paippalāda excluded structurally |
| Engineering (parsing/hierarchy/translation alignment) | `RESOLVED` | Parser, identity functions, and citation-label-based translation alignment (never sequence-based) all proven against the full artifact |
| Structural count reconciliation | `OPEN_RESEARCH` | 731 vs 730 sūktas and 5,839 vs ~5,977 mantras both still unresolved. A candidate mechanism was raised **and falsified** in the closure run — see below. Does **not** gate the primary text |
| Acquisition of a clean route | **`RESOLVED`** (was `OPEN_RESEARCH` + `OPEN_RIGHTS`) | Scan **acquired and visually verified**, not merely identified. BSB/MDZ `urn:nbn:de:bvb:12-bsb10219750-9`, registered as source `BSB_MDZ` |
| Transcription labour | **`OPEN_ENGINEERING`** (new dimension) | A resolved source is **not** a corpus. No Sanskrit transcribed yet. ~60–120 person-hours, driven mainly by accent reproduction |

**Answer as of the closure run:** **no longer blocked on acquisition.** Roth & Whitney,
*Atharva Veda Sanhita, Erster Band. Text.*, Berlin: Ferd. Dümmler's, 1856, 458 pp., is in hand via
BSB/MDZ. Coverage was verified **visually** across three sampled leaves (printed pp. 16, 287, 407),
the text is accented and legible at 600 PPI, and a transcription sample was produced from the image
alone. What remains is bounded transcription **labour** under a stated protocol.

**Why the new `transcription_labour` dimension exists.** The old dimension set could not express the
state this Veda actually reached. Rights and acquisition both moved to `RESOLVED`, and calling the
Veda READY on that basis alone would be exactly the substitution this registry forbids:
**SOURCE RIGHTS CLEAR is not PRIMARY TEXT COMPLETE.**

**Three constraints attach, all binding on any future transcription:**

1. **RIGHTS-13** (landed this run) extends the independence firewall to channels that leave no
   artifact — transcriber recall, a parallel edition on the desk, autocomplete, **and an LLM
   assistant**. The last is identified as the *most likely* breach path, because this project is
   operated by agents holding GRETIL/TITUS text in training that will complete an unclear akṣara
   helpfully and silently if asked. Protocol: transcribe what is on the page, mark unclear
   characters `[?]`, resolve only by re-reading the same scan / a second PD witness / a second
   human, and ship unresolved `[?]` as `PHILOLOGICAL_REVIEW_REQUIRED`.
2. **Output licence must be split** — transcribed text **CC0/PD**, only VedaGraph's structural
   apparatus under a VedaGraph licence. Asserting CC BY-SA over a faithful transcription of a PD
   work would be the same copyfraud RIGHTS-10 condemns in others.
3. **Acquire from BSB, not archive.org.** The archive.org copy's `CC BY 3.0` tag is **void for want
   of standing** — every sampled leaf carries a *"Digitized by Google"* watermark, so the tagger is
   not even the digitiser (sixth instance of RIGHTS-10, and a new sub-type catchable only by
   inspecting a page margin). BSB's *"Kein Urheberrechtsschutz"* is **not** the basis for PD status;
   it is a **disclaimer of the scan-layer right** (UrhG §72), BSB being the one party with standing
   to waive it. The DDB non-commercial tag is structurally without standing (aggregator, RIGHTS-9).

**Scope limits, stated so they are not lost.** Kāṇḍa 20 is confirmed **present** by observation;
*unabridged* still rests on the edition's preface, since leaf n420 sits only 25.2% into that kāṇḍa.
And the AVŚ 12.5 prose dual-numbering observation — real, and independently corroborated from the
artifact — was **wrongly generalised** into a cause of the 5,839/~5,977 gap: counting by paryāya
group moves the total *down* ~1,954 while the gap needs *up* 138. Grouping merges; the gap needs
splitting. The count divergences remain open.

---

## 4. Exit criteria

### YV exit criteria

- [ ] 1,975/1,975 primary Sanskrit passages carrying `TextRole.PRIMARY_TEXT`, **or** explicit,
  registry-recorded evidence that this cannot be produced from currently-approved sources
- [ ] Source-faithful extraction: no silent variant selection — VSM 16.37 resolved by recorded
  human review, not left as a silent first-occurrence pick
- [ ] Deterministic rebuild (byte-identical), as already demonstrated by the pilot
- [ ] Passage IDs stable across the pilot → full-corpus transition (already tested by
  `test_passage_identity_is_stable_when_the_build_scope_grows` pattern used for Rigveda; an
  equivalent test is required for YV before scale-up)

### SV exit criteria

Rewritten 2026-09-07 by `SAMAVEDA_REFERENT_INTEGRITY_REPAIR`. The previous list was the
**pre-closure** one and had already been superseded in the machine-readable registry; it
still asked for "a named printed edition" after that requirement was shown to be a category
error, and still described the count gap as "the current 2-of-7 partial explanation".

- [x] Canonical witness/source decision recorded in `data/registry/works.yaml` —
  Sanskrit Wikisource is the primary; the rejected artifact can no longer mint identity
- [x] Recension Kauthuma re-confirmed against the selected witness (page tree is
  `सामवेदः/कौथुमीया/संहिता/…` throughout)
- [x] Edition/provenance decision recorded as an **established negative**: no printed
  antecedent exists to name, and identity is frozen on the transcription with that risk
  recorded. Not a blocker — nothing edition-valued reaches a UUID
- [x] Count reconciled on the **selected** witness:
  `1875 = 1873 distinct printed markers + 2 the witness does not print`, residue 0
- [x] Stable identity/key frozen: `key_pattern` and `urn_pattern` populated,
  `identity_status: FINAL`
- [x] **Referent integrity gated** — `PassageReferentBinding` + a committed drift baseline;
  a build fails when a key changes what it denotes without a recorded migration
- [x] Zero two-referent/one-key collisions and zero one-referent/two-key splits, measured
- [x] Migration ledger committed for every retired key
  (`data/source_registry/samaveda_referent_migrations.jsonl`, 144 entries)
- [x] Deterministic rebuild maintained after the source re-pointing
- [x] Arcika/gāna coverage distinction stated explicitly — no claim to "have the Sāmaveda"
  while holding only the arcika; gāna needs its own `work_id`
- [ ] **A `WIKISOURCE_SA.SV.KAU.*` text_version registered**, so the frozen key is not bound
  to the encumbered GRETIL lineage in the only registry a build resolves rights through
- [ ] **Coverage completed**: the 31 unaddressed verses (4 Uttarārcika daśati partitions,
  one non-contiguous run, 2 unprinted running numbers)
- [ ] **Independence re-verified at codepoint level at > 2 loci** before any bulk text
  release — gates release, not identity

### AV exit criteria

- [ ] Śaunaka source confirmed for whatever new artifact is introduced (via
  `assert_saunaka_recension()` or equivalent two-witness check)
- [ ] Redistributable, or otherwise project-approved, rights for the primary Sanskrit layer
- [ ] Source lineage independently traceable to a clean root (Roth & Whitney 1856, or a
  permissioned Orlandi/TITUS lineage) — explicitly not a "cleaned" derivative of the encumbered
  digital text
- [ ] Structural reconciliation: 731-sūkta and 5,839-mantra figures reconciled against or explained
  relative to a second complete edition, or explicitly left open with cause stated
- [ ] Deterministic passage identity preserved (existing `FINAL` hierarchy unchanged)
- [ ] Deterministic rebuild maintained

---

## 5. Cross-references

- Rights ground truth: [`FOUR_VEDA_RIGHTS_MATRIX.md`](FOUR_VEDA_RIGHTS_MATRIX.md)
- Source adjudication narrative: [`FOUR_VEDA_SOURCE_ADJUDICATION.md`](FOUR_VEDA_SOURCE_ADJUDICATION.md)
- Structural/identity model: [`FOUR_VEDA_STRUCTURAL_MODEL.md`](FOUR_VEDA_STRUCTURAL_MODEL.md),
  [ADR-017](decisions/ADR-017-four-veda-structural-model.md)
- Audio: [`FOUR_VEDA_AUDIO_SOURCE_INVENTORY.md`](FOUR_VEDA_AUDIO_SOURCE_INVENTORY.md)
- Pilots: [`YAJURVEDA_PILOT.md`](pilots/YAJURVEDA_PILOT.md), [`SAMAVEDA_PILOT.md`](pilots/SAMAVEDA_PILOT.md),
  [`ATHARVAVEDA_PILOT.md`](pilots/ATHARVAVEDA_PILOT.md)
- Work packets: [`work_packets/YAJURVEDA_PRIMARY_TEXT_CLOSURE.md`](work_packets/YAJURVEDA_PRIMARY_TEXT_CLOSURE.md),
  [`work_packets/SAMAVEDA_IDENTITY_SOURCE_CLOSURE.md`](work_packets/SAMAVEDA_IDENTITY_SOURCE_CLOSURE.md),
  [`work_packets/ATHARVAVEDA_PRIMARY_SOURCE_CLOSURE.md`](work_packets/ATHARVAVEDA_PRIMARY_SOURCE_CLOSURE.md)
- Orchestration for the closure session: [`work_packets/CANONICAL_SANSKRIT_CLOSURE_ORCHESTRATION.md`](work_packets/CANONICAL_SANSKRIT_CLOSURE_ORCHESTRATION.md)
- Stale-claim audit: [`qa/STALE_FOUR_VEDA_CLAIMS.md`](qa/STALE_FOUR_VEDA_CLAIMS.md)
