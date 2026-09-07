# Samaveda (Kauthuma) Source Research

**Work**: `VG:WORK:SV:KAU` — Samaveda Samhita, Kauthuma recension
**Author**: Agent B (Samaveda specialist)
**Date**: 2026-09-07
**Machine-readable companion**: `data/source_registry/samaveda_sources.yaml`
**Pilot**: `docs/pilots/SAMAVEDA_PILOT.md`

**Readiness verdict: `SOURCE_STACK_APPROVED_WITH_LIMITATIONS`** — see [§9](#9-readiness-verdict).

---

## 0. Method

Every rights statement quoted below was read from the artifact or page **actually fetched**,
at the URL recorded, on the date recorded. No artifact's rights were inferred from its host
repository's general terms. Every structural count marked *computed* was derived by parsing
a hashed snapshot; counts marked *claimed* are the source's own assertion. Where the two
disagree, both are reported and the gap is left open.

Two negative results were reached by fetching rather than by assumption, and are recorded
so nobody re-researches them: VedaWeb has no Samaveda, and English Wikisource has no
Samaveda verse text.

---

## 1. Candidate sources

| # | Source | Format | Script | Accents | Structure | Coverage | Artifact rights | Mirrorable |
|---|---|---|---|---|---|---|---|---|
| 1 | **GRETIL** `sa_sAmavedasaMhitA.xml` | TEI XML | Latin/IAST | **NONE** | reference label per line; **no TEI markup** | arcika only, 1868 computed vs 1875 claimed | **PERMISSION_REQUIRED** (internal conflict) | No |
| 2 | GRETIL `samavedu.htm` (upstream of #1) | HTML | Latin/IAST | NONE | same | same | **REFERENCE_ONLY** (self-declared) | No |
| 3 | **Sanskrit Wikisource** `सामवेदः/कौथुमीया/संहिता` | MediaWiki | **Devanagari** | **PARTIAL** (saman notation on gana pages) | encoded in page-title path | **both arcikas + all four gana books**, 840 pages | **CC BY-SA 4.0** | **Yes** |
| 4 | sanskritdocuments `sv-kauthuma.itx` | ITRANS text | ITRANS | NONE | same label system as #1 | 1875 verses, arcika only | **RESEARCH_ONLY** | No |
| 5 | TITUS `ved/sv/svk/` | HTML | Latin | — | **8-level addressing** | Kauthuma | **PERMISSION_REQUIRED** | No |
| 6 | sacred-texts `/hin/sv.htm` (Griffith 1895) | HTML | — | n/a (English) | BOOK / CHAPTER / DECADE | complete translation | **PUBLIC_DOMAIN** (by age) | Yes |
| 7 | English Wikisource "Hymns of the Samaveda" | HTML | — | n/a | — | **preface only, zero verses** | PUBLIC_DOMAIN | n/a |
| 8 | Vedic Heritage Portal (IGNCA) | HTML + MP3 + PDF | Devanagari headings only | — | kanda / adhyaya / prapathaka / ardha | **no verse text**; 158 audio files | **PERMISSION_REQUIRED** | No |
| 9 | VedaWeb | JSON API | — | — | — | **no Samaveda at all** | n/a | n/a |
| 10 | archive.org DLI (Samasrami, Bibliotheca Indica) | Scan + OCR | Devanagari | — | — | 5 volumes | **UNSTATED** | No |
| 11 | Wikimedia Commons `.ogg` (via #3) | OGG | — | audio | page-level | 474 files | **CC BY-SA 4.0 / CC0** (per-file verified) | **Yes** |
| 12 | vedicreserve (Maharishi) | PDF | — | — | — | 1 file, 823 KB | none found | No |

### 1.1 Verbatim rights evidence

**GRETIL Samaveda TEI — an *intra-artifact* conflict.** Its `publicationStmt/availability`
declares:

> Distributed under a Creative Commons Attribution-NonCommercial-ShareAlike 4.0
> International License.

…and, in the same `availability` block:

> This e-text was provided to GRETIL in good faith that no copyright rights have been
> infringed. If anyone wishes to assert copyright over this file, please contact the GRETIL
> management at gretil(at)sub(dot)uni-goettingen(dot)de. The file will be immediately
> removed pending resolution of the claim.

But the **same `fileDesc`**, in `notesStmt/note[@type="legacyheader"]`, carries:

> Copyright (C) 1998 Anshuman Pandey
> This document may only be used for academic and scholarly purposes. No
> modification of this document is in any way authorized. Any publication
> or other use of this document requires written consent of the editor.

**Adjudication: the restrictive statement governs.** GRETIL's own text concedes it merely
*assumes* non-infringement and offers to remove the file on claim — it does not warrant the
rights it purports to license. Everything VedaGraph does to this text (TEI parse, NFC
normalization, structural re-keying, JSONL republication) is both *modification* and
*publication*, which the contributor's notice forbids without written consent.

Three independent lines of corroboration:

1. The file's **own upstream**, `samavedu.htm`, which the TEI names as its source,
   self-declares:
   > THIS GRETIL TEXT FILE IS FOR REFERENCE PURPOSES ONLY!
   > COPYRIGHT AND TERMS OF USAGE AS FOR SOURCE FILE.
   A licence cannot be created by a 2020 format conversion that its 1998 upstream never granted.
2. The **same author's** Samaveda text is published on archive.org
   (`shastras-vedas-sama-veda-kauthuma-samhita`, creator "Anshuman Pandey") under
   **CC BY-NC-ND 4.0** — and *ND forbids derivatives outright*.
3. GRETIL's Rigveda file (`sa_Rgveda-edAufrecht.xml`) carries CC BY-NC-SA **and no
   legacyheader note at all**. The divergence is real and file-specific, which is exactly
   why per-artifact review exists.

**Vedic Heritage Portal** (`/copyright-policy/`):
> The contents of this website can not be reproduced partially or fully, without written
> permission from Indira Gandhi National Center for the Arts or the contributor (with
> intimate to IGNCA). If referred to as a part of another publication, the source must be
> appropriately acknowledged. The contents of this website can not be used in any
> misleading or objectionable context.

And, unusually strict, `/hyper-linking-policy/`:
> Prior permission is required before hyperlinks are directed from any website/portal to this site.

**sanskritdocuments** (read from the `.itx` header itself, not the site terms):
> % This text is prepared by volunteers and is to be used for personal study
> % and research. The file is not to be copied or reposted for promotion of
> % any website or individuals or for commercial purpose without permission.
> % Please help to maintain respect for volunteer spirit.

**TITUS**:
> Copyright TITUS Project , Frankfurt a/M, 1.11.2013. No parts of this document may be
> republished in any form without prior permission by the copyright holder.

**Sanskrit Wikisource** (page footer as fetched):
> पाठः क्रियेटिव कॉमन्स ऐट्रिब्यूशन/शेयर-अलाइक अभिज्ञापत्रस्य अन्तर्गततया उपलब्धः अस्ति

**sacred-texts.com** — the only rights signal is a site-wide `<meta name="copyright"
content="Public Domain and Creative Commons">`. That is generic, not per-artifact; it is
recorded but carries no weight. Griffith 1895 is public domain by age independently.

---

## 2. Selected sources

| Role | Selection | Reason |
|---|---|---|
| **Recommended primary Sanskrit** | **Sanskrit Wikisource** (#3) | The only candidate that is *simultaneously* redistributable (CC BY-SA 4.0), in Devanagari, carrying real saman notation, covering the **gana** at all, and textually **correct where GRETIL is provably corrupt**. |
| **Pilot primary Sanskrit** | GRETIL TEI (#1) | Chosen **only** because it is a single self-describing file that declares its own reference system — that is what made the hierarchy adjudication possible. **Not** recommended as canonical primary. |
| **Parallel Sanskrit** | Sanskrit Wikisource (#3) | Genuinely independent lineage; see [§5](#5-cross-source-comparison). |
| **Citation authority** | TITUS (#5) | Most granular addressing found. Cited, never copied. |
| **Collation check** | sanskritdocuments (#4) | Same reference system as GRETIL, so a third witness to the *label system* — but shares Pandey lineage, so **not** independent evidence of textual correctness. |
| **English translation** | sacred-texts Griffith (#6) | Complete and public domain. **Not aligned** — see below. |
| **Hindi translation** | **NONE FOUND** | No rights-clear machine-readable Hindi Samaveda located. |
| **Audio reference** | VHP (#8) reference-only; **Commons (#11) for mirroring** | Only #11 permits local mirroring, verified per file. |

### 2.1 Why the English translation is *not* aligned

Griffith states in his own preface, verbatim: **"I have followed Benfey's text"**. The same
preface identifies Benfey's edition as being of the **Rāṇāyanīya** recension, not Kauthuma:

> A translation, by Dr. Stevenson, of the Ranayaniya recension … in 1848 Professor Benfey
> of Göttingen brought out an excellent edition of the same text … and in 1874-78 Pandit
> Satyavrata Samasrami of Calcutta published in the Bibliotheca Indica a most meritorious
> edition of the Sanhita according to the same recension.

Two consequences. First, aligning Griffith to a **Kauthuma** Sanskrit text is a
*cross-recension* alignment and requires explicit review per `ADR-010`. Second — and this
corrects a common assumption — **Samasrami's Bibliotheca Indica edition is Rāṇāyanīya too**,
so the archive.org DLI scans of it are not a Kauthuma witness.

Griffith's own division also diverges structurally: his Part II has **six** Books where the
Kauthuma Uttarārcika has **nine** prapāṭhakas. `translations.jsonl` in the pilot is therefore
**deliberately empty**. Leaving it unaligned is the correct outcome, not an omission.

---

## 3. Confirmed canonical hierarchy

The selected GRETIL artifact **declares its own reference system** in the first paragraph of
its TEI body:

```
REFERENCE SYSTEM:
ārcika | prapāṭhaka | ardha | daśati | verse | line
1 1 1 01 01 a
```

followed immediately by `sāmaveda saṃhitā / kauthuma śākhā`.

**This supersedes the earlier registry guess of `[Arcika, Prapathaka, Ardha, Adhyaya,
Khanda, Mantra]`.** The fourth level is **Daśati**, not Adhyāya or Khaṇḍa. `line` (values
`a`, `c`, `e`) is a **sub-verse pāda label** and is deliberately excluded from identity.

Identity therefore uses **five** levels: `arcika · prapathaka · ardha · dasati · verse`.

### 3.1 Computed counts

All figures below were computed from the parsed snapshot, never assumed:

| Ārcika | Name | Prapāṭhaka | Ardha | Verses | Running range |
|---|---|---|---|---|---|
| 1 | Pūrvārcika (chanda ārcika) | 1–6 | 1–2 each | **585** | 1–585 |
| 2 | Āraṇya ārcika | **0 (absent)** | **0 (absent)** | **55** | 586–640 |
| 3 | Mahānāmnya ārcika | **0 (absent)** | **0 (absent)**, daśati also 0 | **10** | 641–650 |
| 4 | Uttarārcika | 1–9 | 1–2 for pr. 1–5; **1–3** for pr. 6–9 | **1218** | 651–1875 |
| | **Total** | | | **1868 computed** | vs **1875 claimed** |

Verse lines: **3714**. Line-label distribution: `a` 1878, `c` 1815, `e` 21.
Label notations: **CONCAT** (`1 1 1 0101a`) 2265 lines, **SPACED** (`4 1 1 01 01a`) 1449 lines
— *both occur inside ārcika 4*.

### 3.2 Depth is genuinely not uniform

This is the load-bearing finding. **The edition encodes an absent level as a literal `0`.**
The Āraṇya ārcika has no prapāṭhaka and no ardha; the Mahānāmnya ārcika additionally has no
daśati. A positivity check on those three levels rejects **65 real verses**. `identity.py`
therefore applies `_non_negative` rather than `_positive` to `prapathaka`/`ardha`/`dasati`,
while `arcika` and `verse` stay positive.

### 3.3 The fourth slot has no fixed cardinality

Same slot name, different unit:

- **Pūrvārcika**: a true decad, numbered **1–10 continuously across the ardha pair**
  (ardha 1 = daśati 1–5, ardha 2 = daśati 6–10).
- **Uttarārcika**: **resets to 1 inside each ardha** and holds only two or three verses —
  it functions as a *sūkta*.
- **Āraṇya ārcika**: daśati 1 contains **9** verses, not 10 (computed).

Nothing anywhere may assume ten verses per daśati.

### 3.4 A running number exists, and must not be identity

The source prints a running verse number at the end of each verse, spanning **1–1875**, and
closes `.. iti sāmavedasaṃhitā samāptā..`. It is **defective**: 1871 printed, 1870 distinct,
**5 absent** (1035, 1133, 1179, 1211, 1592), **1 duplicated** (1181), and it runs *backwards*
once at 1181→1180. It is carried as a **non-canonical `Citation`** (`SV_RUNNING_VERSE`),
never as a key.

### 3.5 Kaṇḍa is not a tree level

The Pūrvārcika also carries a named **kaṇḍa** division (āgneya, aindra, saumya-pāvamāna,
āraṇya) whose colophons **cut across** prapāṭhaka/ardha boundaries — `.. ityāgneya parvaṃ
kāṇḍam ..` falls mid-way through `dvitīya prapāṭhakaḥ . prathamo 'rdhaḥ`. A non-nesting
division cannot be a tree level; it is an **alternate Citation system**.

Separately, **VHP's Kauthuma pages use "adhyāya"** alongside prapāṭhaka/ardha — this is
where the original registry guess came from. Adhyāya is a real Kauthuma division, but it is
not the fourth level of the *selected edition's* reference system, so it too belongs in
`Citation`.

### 3.6 Independent corroboration (four witnesses, not one file)

| Witness | Lineage | What it confirms |
|---|---|---|
| GRETIL TEI | Pandey 1998 | Declares the system verbatim |
| sanskritdocuments `.itx` | **Pandey 1998** (same) | Same label system — corroborates the *notation*, not the text |
| **TITUS** | **Pandey 1998/99 text + Gippert addressing** — see correction below | 8-level addressing: SV → SVK → **Ārcika (1–4)** → **Prapāṭhaka (1–6)** → **Ardha** → **Daśati** → **Ṛca** → **Pāda**. Confirms the level *vocabulary* and that there are exactly four ārcikas — but **not** the text. |
| **Griffith 1895** | Benfey / independent | Structures his English as BOOK / CHAPTER / **DECADE**, 1–10 verses per decade. An 1895 translator independently using the daśati as the fourth level. |
| **Sanskrit Wikisource** | community / **independent, proven** | Page tree `prapāṭhaka → daśati 1–10` with **no ardha level**, and Āraṇya with **no prapāṭhaka** |

#### Correction (2026-09-07, after Agent E's TITUS check)

An earlier draft of this report claimed **"four independent witnesses"**. That was
**overstated**, and the correction matters because it is exactly the "same defect twice"
trap Agent A originally warned about.

TITUS's Samaveda page states, verbatim (fetched from
`https://titus.uni-frankfurt.de/texte/etcs/ind/aind/ved/sv/svk/svk001.htm`, 2026-09-07):

> edited by Anshuman Pandey
> apandey@u.washington.edu
> TITUS version by Jost Gippert ,
> Copyright (C) 1998, 1999 Anshuman Pandey

So TITUS is a **third re-publication of the same Pandey e-text**, not an independent
textual witness. The Pandey root is now read *off the artifact* at **three** re-publishers
(GRETIL, sanskritdocuments, TITUS) rather than inferred at two.

The honest tally is therefore:

| Class | Witnesses |
|---|---|
| **Independent textual witnesses** | **2** — Sanskrit Wikisource (independence *proven* by textual disagreement: it corrects Pandey's pāda misplacement) and Griffith 1895 via Benfey (Rāṇāyanīya; predates Pandey by a century) |
| Independent *addressing* evidence | **1** — TITUS's 8-level scheme is Gippert's own editorial analysis layered on Pandey's text, so it corroborates the level **vocabulary** but not the text |
| Same-text re-publications | **3** — GRETIL, sanskritdocuments, TITUS (one text) |

**The hierarchy conclusion is unchanged**: it rests on the selected source's own declaration
plus two genuinely independent witnesses plus one independent addressing scheme, and the
level names agree across all of them. But the *strength* of the corroboration is lower than
first stated, and nothing in this report should be read as four independent confirmations.

### 3.7 What I could NOT compute

- **The 7-verse gap** between the computed 1868 keys and the claimed 1875. It is driven by
  the label defects in §4, but closing it requires a scholarly edition, not a parser.
- **The underlying printed edition** of the GRETIL artifact. `<sourceDesc><bibl></bibl>` is
  **empty**. Its `refsDecl` is unfilled boilerplate with empty `<label></label>` elements
  that claims references live in `xml:id` attributes — and the body has **no `xml:id` at
  all**. So the artifact cannot say which Kauthuma edition it is.
- **The gāna dimension.** Not in this artifact at all.
- **VHP's audio file-naming semantics** (see §7).

### 3.8 Identity status

**Samaveda identity is UNDECLARED.** `data/registry/works.yaml` carries
`key_pattern: null` and `identity_status: RESEARCH_REQUIRED`, because the evidencing
artifact's rights are contested and its printed edition is unidentified.
`identity.sv_mantra_identity` and `sv_container_identity` are landed but **explicitly not
frozen**. The keys in the pilot are **candidate keys, not canonical ones.**

The blocker has, however, changed shape. It is no longer *"no independent witness exists"* —
Sanskrit Wikisource is one, and it disagrees with the Pandey lineage textually. It is now:
**no witness combines an identified printed edition with redistribution rights.**

---

## 4. Source defects found (recorded, never repaired)

Computed over the whole artifact:

| Code | Count | What it is |
|---|---|---|
| `DUPLICATE_LINE_LABEL` | 22 | Verse-numbering collisions; 12 distinct verse keys affected |
| `ZERO_VERSE_INDEX` | 6 lines / **1 verse** | `4 6 2 1600a` — verse index 0, which the reference system does not define |
| `TRANSLITERATION_RESIDUE` | 6 | GRETIL's IAST conversion failed for vocalic long ṛ, leaving raw ITRANS `R^` (e.g. `jaritR^īṇām`) |
| `UNEXPECTED_UPPERCASE` | 3 | Stray capital in otherwise lowercase IAST (`Oṃ`) |
| `UNPARSEABLE_REFERENCE_LABEL` | 1 | `rm 4 4 1 02 02c pavante vāre avyaye .. 1035` — stray `rm ` prefix. **This is why running number 1035 is missing**; the line's text is *not* ingested. |

Plus one stray bare `.` line, and the running-number defects in §3.4.

**The most consequential defect is textual, not cosmetic.** At running verses 1–2 the
mislabel (verse 2's a-pāda tagged `0101a` instead of `0102a`) **moves a pāda between
verses**:

```
running 1  GRETIL:     agna ā yāhi vītaye gṛṇāno havyadātaye . ni hotā satsi barhiṣi tvamagne yajñānāṃ hotā viśveṣāṃ hitaḥ .
running 1  WIKISOURCE: agna ā yāhi vītaye gṛṇāno havyadātaye | ni hotā satsi barhiṣi
running 2  GRETIL:     devebhirmānuṣe jane
running 2  WIKISOURCE: tvamagne yajñānāṃ hotā viśveṣāṃ hitaḥ | devebhirmānuṣe jane
```

GRETIL bleeds the pāda **into** verse 1 and **strips** it from verse 2. Wikisource has both
verses whole. This is a corrupted text, discovered only by cross-source comparison, and it is
the decisive engineering reason not to make GRETIL the canonical primary.

---

## 5. Cross-source comparison

Run with the existing `src/vedagraph/compare/text.py` machinery and the existing
`TextComparisonCategory` vocabulary. Output: `data/canonical/samaveda_pilot_v1/text_comparisons.jsonl`.
Script: `scripts/compare_samaveda_sources.py`.

`classify()` correctly **refuses** cross-script comparison, so the Devanagari side is
transliterated to IAST with the repository's `DevanagariToIAST` and the resulting reading is
declared `COMPARISON_ONLY` — a derived surface used to classify a difference, never stored
text. **Neither source is modified.**

### 5.1 The alignment trap, and how it was avoided

The two sources index verses on **different systems**:

- **GRETIL** numbers a verse *locally inside its daśati* (`1 1 1 0501a` → verse 1)
- **Wikisource** labels the same verse with the *running whole-Saṃhitā number* (45)

A first run aligned by printed verse number and produced **19 spurious `MISSING` rows out of
29** — every daśati except the first, where the two systems coincide. Rather than invent a
per-unit offset (which would have silently assumed ten verses per daśati), the join was moved
onto the **running verse number that both sources supply independently**. That is a
*source-provided* alignment, not a derived one. Result: **0 MISSING, 0 numbering divergences**.

### 5.2 Classification distribution (29 aligned verses)

| Category | Count |
|---|---|
| `ORTHOGRAPHIC` | 17 |
| `SANDHI_OR_SEGMENTATION` | 1 |
| `UNCLASSIFIED` | 11 |
| `MISSING` | 0 |

Similarity: min 0.5000, **mean 0.9626**, max 1.0000.

The two lowest-similarity rows are precisely the §4 defect (running 1 at 15/10 tokens,
running 2 at 2/7 tokens). Several of the remaining `UNCLASSIFIED` rows appear to be pure
danda-notation differences (`|` vs `.`); this has been reported to Agent F, who owns the
comparator, as a possible short-circuit in the refinement ladder on transliterated input. It
has **not** been patched here.

---

## 6. Traditional metadata

**Status: `PARTIAL_AND_INSUFFICIENT`.**

**Do not infer.** Rigvedic Anukramaṇī rules must **not** be transferred to Samaveda, and
missing rishi/chandas/devata values must **not** be filled in by an LLM. Samaveda verses are
largely borrowed from the Rigveda, which makes LLM-guessed attribution both especially
plausible and especially wrong.

| Source | Form | Machine-readable | Coverage | Rights |
|---|---|---|---|---|
| GRETIL TEI | Inline triads `asitaḥ kāśyapo devalo vā. gāyatrī. pavamānaḥ somaḥ.` = ṛṣi. chandas. devatā. | Partially | **Only ~24 triads.** 31 of 395 Uttarārcika paragraphs have any head line; Pūrvārcika has **none**. Separators alternate `.` and `,`. | PERMISSION_REQUIRED |
| Sanskrit Wikisource | Triads `वसिष्ठः । त्रिष्टुप् । पवमानः सोमः`, plus gāna performance metadata `दी० ८ । प० ६ । मा० ७` | Partially | Better covered | **CC BY-SA** |
| VHP | Devanagari structural headings only | **No** | kaṇḍa/adhyāya/prapāṭhaka/ardha names | PERMISSION_REQUIRED |

**No verified Samaveda Anukramaṇī was located anywhere.**

### 6.1 Safe resolution method

1. Extract triads **verbatim** into `CandidateMetadataAssertion` records with a
   `parse_status` and **no** canonical entity id.
2. Attach each to the daśati or verse **the source itself places it against**; never widen a
   triad to a scope the source did not state.
3. Require **human review** before any promotion to `TraditionalMetadataAssertion`, because
   Samaveda scope conventions are not the Rigveda's.
4. Where a Samaveda verse is a known Rigveda borrowing, the Rigvedic ṛṣi/devatā/chandas may
   be **cited as a cross-reference** but must **never** be asserted as the Samaveda verse's
   own traditional metadata. Sanskrit Wikisource supplies **explicit Rigveda
   cross-references on 363 pages**, which makes this tractable without guessing.

---

## 7. Audio inventory

Samaveda is the chant Veda, so this matters most here. **Default posture: `REFERENCE_ONLY`.
Nothing was downloaded** — only metadata, file listings and rights statements were retrieved.
Publicly playable is not mirrorable.

| Item | Vedic Heritage Portal (IGNCA) | archive.org IGNCA mirror | **Wikimedia Commons** |
|---|---|---|---|
| Recension | Kauthuma | Kauthuma | Kauthuma |
| Scope | **158 files**: Pūrvārcika 85 + 85 intros under `/Samaveda_MP3/`; Uttarārcika 73 under `/Samveda_Kautham_mp3/` organised by **gāna** (Ūha_Gāna 49, Rahasya_Gāna 24). Rāṇāyanīya and Jaiminīya pages: **0 files**. | **PARTIAL** — 38 recitation + 49 intros = 87 files, 8.23 h. Only two disjoint groups; nothing for groups 01/02/03/05. | 474 `.ogg` from 444 Saṃhitā pages |
| Recitation type | `VEDIC_RECITATION` | `VEDIC_RECITATION` | `VEDIC_RECITATION` (sāman/gāna) |
| Reciter | **NOT PUBLISHED** — credits exist only as spoken content inside the separate `_intro` tracks | Not published | Not per file; uploaders "Seet…" (317), "Puranastudy" (157), Credit "Own work" |
| Format / duration | MP3; large whole-section files (`SAMKP_01_01_01_001.mp3` = 18,355,977 B); per-file duration not published; Last-Modified 2024-02-28 | VBR MP3; 29,645 s total | OGG Vorbis |
| Alignment granularity | **FILE_LEVEL at best** | FILE_LEVEL at best | **PAGE_LEVEL, source-provided** |
| Rights | **PERMISSION_REQUIRED** (verbatim in §1.1) | **UNKNOWN** — no `licenseurl`, no `rights`; description is only "Courtsey : IGNCA and Indian taxpayers", an acknowledgement not a grant | **CC BY-SA 4.0 / CC0**, checked **per file**: 458 CC BY-SA 4.0, 16 CC0, 0 missing |
| Local mirroring | **NO** | **NO** | **YES**, with attribution + share-alike |
| Direct linking | **NO** — even deep-linking nominally requires prior permission | — | Yes |
| Storage policy | `EXTERNAL_REFERENCE` | `EXTERNAL_REFERENCE` | `OBJECT_STORAGE` |

The archive.org item is a **partial mirror of the VHP set**, not an independent recording —
its filenames use the identical `SAMKP_` scheme. The VHP copyright policy therefore governs
it regardless of what a third-party re-uploader asserts.

**File-naming status: `UNRESOLVED`.** `SAMKP_{f1}_{f2}_{f3}_{running}.mp3` field semantics
are **not** deterministically decodable. Observed sequences (`01_01_01_001..005` then
`01_01_02_006..010`, and separately `06_01_001` with only *three* numeric fields) are
consistent with roughly one file per daśati, but the field count is inconsistent and VHP
publishes no key. **Alignment must be adjudicated against VHP's own on-page Devanagari
headings before any audio-to-passage mapping is asserted.** No mapping is asserted here.

**Recommendation**: use Commons (#11) as the mirrorable audio source — rights verified per
file and alignment source-provided — while treating VHP as the higher-authority
reference-only link-out.

---

## 8. The gāna gap

A Samaveda without the gāna is **musically incomplete**, and most text candidates omit it
entirely.

- **GRETIL has no gāna anywhere.** Body string counts: `gāna` 0, `grāmageya` 0,
  `āraṇyageya` 0, `ūhya` 0. The few `ūha`/`stobha` hits are ordinary word-forms inside
  mantras. No stobha syllables, no parvan divisions.
- **sanskritdocuments** has the gāna only as four PDFs (grāmageya 1198 gānas/579 pp;
  āraṇyakagāna 296/177; ūhagāna 936/515; ūhya-rahasyagāna 209/148).
- **Sanskrit Wikisource is the only source found carrying the gāna as reusable text**:
  grāmageya 190 pages, āraṇyakageya 86, ūhagāna 362, ūhyagāna 87 — **725 pages**.

Roughly **2,639 gānas against 1,875 ārcika verses**: the sung dimension is not a decoration
on the verse skeleton, it is the larger artifact and the reason the Samaveda is a distinct
Veda rather than a Rigveda excerpt. **Any claim that VedaGraph "has the Samaveda" while
holding only the ārcika is false.**

Gāna collections are **not** part of the ārcika citation and have **no slot** in
`sv_mantra_identity`. If ingested they need their own `work_id`.

---

## 9. Readiness verdict

### `SOURCE_STACK_APPROVED_WITH_LIMITATIONS`

**Not `SOURCE_ADJUDICATION_INCOMPLETE`**, because the thing that was actually
research-required *is* now resolved with evidence: the canonical hierarchy is confirmed from
the selected source's own declaration and corroborated by **two genuinely independent
witnesses plus one independent addressing scheme** — Sanskrit Wikisource's page tree,
Griffith's 1895 "DECADE", and TITUS's 8-level addressing (see the correction in §3.6: TITUS
and sanskritdocuments share GRETIL's Pandey text, so they are not independent *textual*
witnesses). A working adapter, a 102-passage pilot across all eight
structural regions, a byte-identical rebuild, and a deterministic cross-source comparison all
exist and run.

**Not `SOURCE_STACK_APPROVED_FOR_FULL_INGESTION`**, because of five limitations that are
each disqualifying for a *full* ingestion:

1. **The pilot's primary source may not be bulk-ingested.** Rights are contested at artifact
   level and the restrictive statement governs. Full ingestion of GRETIL is **blocked**
   pending written permission or a different source.
2. **The pilot's primary source is textually defective**, proven by comparison — not merely
   mislabelled but carrying a pāda in the wrong verse.
3. **No source combines an identified printed edition with redistribution rights.** The
   rights-clean option (Sanskrit Wikisource) is a community transcription with no named
   edition; every option with scholarly standing is reference-only.
4. **No accented machine-readable ārcika text is obtainable.** The only advertised one
   (`sv-kauthuma-saswara.pdf`/`.itx`) is a dead 404.
5. **The gāna dimension is absent** from every candidate except Sanskrit Wikisource, and no
   `work_id` exists for it.

**Recommended next step**, in order: (a) build a Sanskrit Wikisource ingestion at scale,
since it is the only rights-clean, gāna-covering, Devanagari option; (b) use the running
verse number as the cross-source join key, as validated here; (c) seek written IGNCA
permission for the VHP audio, and use Commons audio in the meantime; (d) commission or locate
a scholarly Kauthuma collation to close the 7-verse gap and identify an edition, which is the
one remaining precondition for freezing SV identity.

**Do not freeze the SV key against the GRETIL artifact.** Agent A's position is correct: a
hierarchy is an observation, a key is a commitment.

---

## 10. Reproducibility

Every byte of text in this research came from a hashed snapshot written by
`src/vedagraph/ingest/fetcher/http.py`. **No Sanskrit was written from memory.**

| Snapshot | sha256 | Bytes |
|---|---|---|
| GRETIL `sa_sAmavedasaMhitA.xml` | `91c28c0394e94dccc9bad12a08224fbcde0a1194402b610df26647621ed92456` | 272,261 |
| GRETIL `samavedu.htm` | `8b7b45f2b0ec48511f8063e80b9e24a5f10b9a554f6c52020f0108ebc8abe059` | 326,420 |
| Wikisource Pūrvārcika 1.1.1.1 (rev 274559) | `1b3005b62194531bb233fbaddfd9fe2da8f46114d69ed19cc043663cc4c87c76` | 2,435 |
| Wikisource Pūrvārcika 1.1.1.5 (rev 401781) | `3ffa60f176d76e6b59c87bdbaa32d0a260f9aeb1674b0ddfb9566cc3e4535ed4` | 3,104 |
| Wikisource Āraṇya 1.2.1 (rev 323308) | `eeffe2eeff9ab43463b4d942fe1040eb013a7e975dbb12f8c7b9db55be72d80d` | 2,681 |
| EN Wikisource preface (rights evidence) | `7fe81ea645c56d75e01429409a208f4295f79fe6dadb877aebaf783b987ef490` | 5,798 |

Snapshots live under `data/raw/gretil/2026-09-07/`, `data/raw/wikisource_sa/2026-09-07/`, and
`data/raw/wikisource_griffith_sv/2026-09-07/`, each with a sidecar
`*.metadata.json` recording retrieval URL, timestamp, HTTP status and content type.

To reproduce:

```sh
./.venv/Scripts/python.exe scripts/build_samaveda_pilot.py data/builds/samaveda_pilot_v1.yaml
./.venv/Scripts/python.exe scripts/compare_samaveda_sources.py
```

The build verifies the snapshot hash before parsing and **fails closed** on mismatch. It
takes its timestamp from the config, not the clock. Run it twice: the JSONL is byte-identical
(verified over three consecutive runs).
