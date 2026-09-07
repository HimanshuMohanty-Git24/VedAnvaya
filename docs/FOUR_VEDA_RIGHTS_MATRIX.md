# Four-Veda Rights Matrix

**Owner:** Agent E (rights / provenance / source archivist) — single writer
**Compiled:** 2026-09-07
**Machine-readable source of truth:** `data/source_registry/four_veda_source_matrix.yaml`
**Vocabulary and operational semantics:** `data/registry/rights.yaml`

This document states, per selected source per Veda, exactly what VedaGraph **is** and **is not**
permitted to do, and shows the evidence behind each decision. Every permissive status below is backed
by verbatim licence text, a URL, and a retrieval date. Where evidence was absent, the answer is
`UNKNOWN` and the posture is no-redistribution.

---

## 1. The governing rule, and why it earned its keep

> **Rights attach to each source file or asset, not merely to a host website.**
> — `data/registry/rights.yaml`, policy rule RIGHTS-1

This was already project policy before this audit. The audit's main result is that the policy is not
defensive boilerplate — **it changed three verdicts.** Had we inferred rights per host, we would have
wrongly ingested two Vedas and wrongly rejected one.

Two corollaries did the heavy lifting:

- **RIGHTS-3 — on conflict, the more restrictive statement controls.** A downstream aggregator cannot
  grant rights it does not hold.
- **RIGHTS-9 — chain of title is followed to its root, not to the nearest licence.** If any link in the
  chain forbids modification or is still in copyright, the defect propagates downstream regardless of
  what the final publisher asserts.

**One consequence deserves stating plainly, because it drives most of what follows.** The VedaGraph
pipeline parses, NFC-normalizes, structurally re-keys and republishes text as JSONL. In copyright terms
that is **both modification and publication**. A licence forbidding *modification* therefore blocks the
normal pipeline entirely — not merely the raw-redistribution step. "We only publish derived data" is
not a defence.

---

## 2. Artifact-level vs repository-level rights

The requested section, with concrete divergences from our own source set. There are **five distinct
patterns**, and they do not reduce to "always trust the artifact".

### 2.1 GRETIL — one repository, three Vedas, three different outcomes

This is the headline case. Same host, same directory tree, radically different rights.

| Veda | File | Artifact licence | Verdict |
|---|---|---|---|
| Rigveda | `sa_Rgveda-edAufrecht.xml` | CC BY-NC-SA 4.0, **no** contradicting header | `CC_BY_NC_SA` — usable |
| Samaveda | `sa_sAmavedasaMhitA.xml` | CC BY-NC-SA 4.0 **contradicted inside the same file** | `PERMISSION_REQUIRED` |
| Atharvaveda | `avs___u.htm`, `avs_acu.htm` | **No CC licence at all**; "REFERENCE PURPOSES ONLY" | `REFERENCE_ONLY` |

GRETIL publishes **no corpus-wide licence**, and its own availability note disclaims title:

> "This e-text was provided to GRETIL in good faith that no copyright rights have been infringed. If
> anyone wishes to assert copyright over this file, please contact the GRETIL management […] The file
> will be immediately removed pending resolution of the claim."
> — `sa_Rgveda-edAufrecht.xml` and `sa_sAmavedasaMhitA.xml` TEI headers, retrieved 2026-09-04 / 2026-09-07

**Anyone who reasoned "GRETIL's Rigveda is CC BY-NC-SA, therefore GRETIL is CC BY-NC-SA" would have
been wrong about two of the three Vedas.** That is the whole argument for RIGHTS-1 in one table.

### 2.2 The Samaveda file contradicts itself — divergence *inside* one artifact

The strongest single finding. `sa_sAmavedasaMhitA.xml` asserts, in
`teiHeader/fileDesc/publicationStmt/availability/licence`:

> "Distributed under a Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License."

The **same `fileDesc`**, in `notesStmt/note[@type="legacyheader"]`, asserts:

> "Copyright (C) 1998 Anshuman Pandey / This document may only be used for academic and scholarly
> purposes. **No modification of this document is in any way authorized.** Any publication or other use
> of this document requires written consent of the editor."

These are irreconcilable: CC BY-NC-SA permits adaptation under share-alike; the contributor statement
forbids modification outright. Reading the **parent** artifact settles it — `samavedu.htm`, which the
TEI itself names as its upstream, states:

> "THIS GRETIL TEXT FILE IS FOR REFERENCE PURPOSES ONLY! COPYRIGHT AND TERMS OF USAGE AS FOR SOURCE FILE."

So the CC licence on the child is an artifact of GRETIL's 2020 mass conversion applying a blanket
licence to files whose upstreams never granted it. **Verdict: `PERMISSION_REQUIRED`.** Reached
independently by Agent B and Agent E.

### 2.3 The Sanskrit Library — identical licence text, three different verdicts

The most instructive case, because it isolates the variable. All four Sanskrit Library Veda records
carry **character-for-character identical** licence text:

> "Copyright (C) 2010 The Sanskrit Library" … "All rights reserved other than those granted under the
> Creative Commons Attribution Non-Commercial Share Alike license available in full at
> http://creativecommons.org/licenses/by-nc-sa/3.0/legalcode […] Permission is granted to build upon
> this work non-commercially, as long as credit is explicitly acknowledged exactly as described herein
> and derivative work is distributed under the same license."
> — retrieved 2026-09-07 from `vs.html`, `svk.html`, `avs.html`

Yet the correct verdicts differ, because each record names a **different source chain**:

| Record | Root of chain | Root status | Verdict |
|---|---|---|---|
| `vs.html` (Yajurveda) | Albrecht Weber, Berlin **1849** | Public domain by age | **`CC_BY_NC_SA` — accepted** |
| `svk.html` (Samaveda) | Anshuman Pandey **1999** | Forbids modification | `UNKNOWN` |
| `avs.html` (Atharvaveda) | Chatia Orlandi, Pisa: Giardini, **1991** | Still in copyright | `UNKNOWN` |

**The licence label is not the deciding fact; the root of the chain is.** Accepting the Samaveda and
Atharvaveda records at face value would have laundered an upstream restriction.

### 2.4 Two re-publishers agreeing is *the same defect twice*, not corroboration

GRETIL and The Sanskrit Library have **each** applied a CC BY-NC-SA licence over the same encumbered
Anshuman Pandey Samaveda text. Their agreement looks like independent confirmation and is not — it is
one defect, counted twice. Every scholarly digital Kauthuma text located traces to that single data
entry, which is why Samaveda has neither a usable primary text nor any independent parallel witness.
**No amount of source-shopping fixes a defect at the root of the chain. Only a different chain does.**

### 2.5 The inverse cases — when repository level is legitimately operative

RIGHTS-1 is often misread as "always distrust the site licence". Three counter-examples from our own
set show the real test is the **direction of the inference** and **who holds the rights**:

| Source | Situation | Why site/repo level is legitimate here |
|---|---|---|
| **WSC2023** | Apache-2.0 at repo level; data files carry **no** header | The repo owners **authored the data**, so they hold the rights they grant, and nothing contradicts it. Established by inspecting the actual files, not assumed. |
| ~~**TITUS**~~ | ~~Terms exist only project-wide~~ | **THIS ROW WAS WRONG — see §2.8.** Every TITUS text page carries its own stricter per-page notice. The site page is the *more permissive* of the two. |
| **Sanskrit Wikisource** | CC BY-SA 4.0 site-wide; no per-page banner | The underlying Vedic text is **ancient and uncopyrightable**, so the community transcription is the *only* copyrightable contribution — and a Wikimedia project licenses contributions site-wide by construction. |

And the true inverse of GRETIL: **The Sanskrit Library has no site licence at all.** Both
`sanskritlibrary.org/copyright.html` and `/terms.html` return **HTTP 404** (verified 2026-09-07). The
artifact level is the *only* level at which a licence exists. A source can be rights-clear per artifact
while having no site licence whatsoever.

### 2.8 The case I got wrong — TITUS, and why the direction of error matters

I originally classified TITUS `RESEARCH_ONLY` from its project-wide page
(https://titus.uni-frankfurt.de/texte/texte2.htm) alone:

> "Those texts that can be downloaded via http can be used freely for scholarly purposes, provided that
> they are quoted as sources and the name(s) of the editor(s) and the date of last changes are indicated
> in publications. The texts must not be used for any kind of commercial usage."

**Every TITUS Veda text page carries its own, stricter notice.** Verbatim, independently verified by
fetching `vs001.htm`, `svk001.htm` and `avs001.htm` on 2026-09-07:

> "Copyright TITUS Project, Frankfurt a/M, 2.11.2013. **No parts of this document may be republished in
> any form** without prior permission by the copyright holder."

(The Atharvaveda pages carry the same clause dated 4.3.2015 and additionally name the edition.)

**Corrected verdict: `PERMISSION_REQUIRED`, not `RESEARCH_ONLY`.** Under RIGHTS-3 the more restrictive
statement controls.

**Two things make this worth documenting rather than quietly fixing.**

First, it is a failure of **precisely the rule this document exists to enforce**. I read *a* licence
page and treated it as *the* licence. RIGHTS-1 says read the artifact.

Second, **the direction of the error is the instructive part.** In the GRETIL cases the site had no
licence and the artifact was restrictive, so the natural failure mode was over-restriction. Here the
**site page was more permissive than the artifact**, so reading only the site produced an error *in our
own favour* — the most dangerous kind, because nothing downstream would have complained. A
too-restrictive misreading blocks a build and gets noticed; a too-permissive one ships.

**Generalised:** "I checked the licence" is not a claim about a *site*. It is a claim about a *file*.

### 2.9 Where the licence field and the rights reality invert

`svk001.htm` carries **both** the TITUS notice **and** `"Copyright (C) 1998, 1999 Anshuman Pandey"`.
That is direct artifact-level confirmation that the TITUS Sāmaveda shares the encumbered Pandey lineage
— previously *inferred* from The Sanskrit Library's citation of its sources, now **read off the artifact
itself**. Three re-publishers (GRETIL, TITUS, Sanskrit Library), one root defect.

### 2.6 Wikisource — PD work vs CC BY-SA transcription layer

On the English Wikisource translation pages, artifact and site licences genuinely diverge:

- **Artifact level:** "This work was published before January 1, 1931, and is in the public domain
  worldwide because the author died at least 100 years ago." (PD-old banner)
- **Site level:** "Text is available under the Creative Commons Attribution-ShareAlike License;
  additional terms may apply." (Wikimedia footer)

We rely on the **PD status of the translation text** and deliberately do *not* depend on the
transcription layer's creative content. Hence per-page revision provenance is mandatory: the hosted
transcription can change independently of the immutable print edition.

**Note the deliberate asymmetry with §2.5.** On the *English* pages we rely on the artifact-level PD
banner and ignore the site CC BY-SA. On the *Sanskrit* pages we rely on the site CC BY-SA. Same
platform, opposite operative levels — decided by *what is actually copyrightable in each case*. On the
English pages that is a modern translation; on the Sanskrit pages it is only the transcription.

### 2.7 Absence of a licence field is not a grant

`archive.org/metadata/in.ernet.dli.2015.215626` (Griffith, *The Texts of the White Yajurveda*, 1899)
returns **no `licenseurl`, no `rights`, and no `possible-copyright-status`** — the set of
licence-bearing keys is literally empty (verified 2026-09-07).

The `PUBLIC_DOMAIN` classification therefore rests on the **underlying work**: Ralph T. H. Griffith
lived 1826–1906 and the translation was published 1899, so it is public domain by age in both the US
and India. Had we relied on the host's silence we would have had no basis at all. A secondary
Google/Harvard scan (`textswhiteyajur00grifgoog`) does carry
`possible-copyright-status: NOT_IN_COPYRIGHT` / `copyright-region: US` — note the hedge "possible" and
the US-only scope, which makes it corroboration rather than the basis. That item is also a **1987
Munshiram Manoharlal reprint** scan, and a modern reprint can carry its own typographic rights, so the
1899 original is preferred.

---

## 3. Decision table — what VedaGraph may and may not do

Resolved from `data/registry/rights.yaml` `operational_semantics` for each recorded status.
`copy_local` = retain an immutable raw snapshot. `derive` = publish parsed/normalized derivatives.

### 3.1 Rigveda — Śākala (`VG:WORK:RV:SAK`)

| Role | Source | Status | copy_local | redistribute | derive | mirror | link |
|---|---|---|---|---|---|---|---|
| Primary Sanskrit | GRETIL Aufrecht TEI | `CC_BY_NC_SA` | yes | cond. | cond. | cond. | yes |
| Parallel Sanskrit | VedaWeb (per-version) | `UNKNOWN` at source | yes | cond. | cond. | cond. | yes |
| English | Wikisource Griffith 1896 | `PUBLIC_DOMAIN` | yes | **yes** | **yes** | **yes** | yes |
| Traditional metadata | WSC2023 Anukramaṇī | `APACHE_2_0` | yes | **yes** | **yes** | **yes** | yes |
| Verification | VHP | `PERMISSION_REQUIRED` | cond. | **no** | **no** | **no** | yes |
| Aggregator | VedSearch | `UNKNOWN` | **no** | **no** | **no** | **no** | yes |

**May:** ingest and derive the Aufrecht text non-commercially under share-alike; freely use Griffith and
WSC2023.
**May not:** license any output containing the Aufrecht or VedaWeb text commercially; republish VHP page
text or media; bulk-ingest VedSearch.
**Standing constraint:** CC BY-NC-SA is viral and permanently forecloses commercial licensing of any
output incorporating it. WSC2023 is the only commercial-safe Rigveda component.

### 3.2 Sāmaveda — Kauthuma (`VG:WORK:SV:KAU`)

| Role | Source | Status | copy_local | redistribute | derive | mirror | link |
|---|---|---|---|---|---|---|---|
| Primary Sanskrit | GRETIL TEI 2020 | `PERMISSION_REQUIRED` | cond. | **no** | **no** | **no** | yes |
| Primary (parent) | GRETIL `samavedu.htm` | `REFERENCE_ONLY` | cond. | **no** | **no** | **no** | yes |
| Primary (candidate) | Sanskrit Wikisource | `CC_BY_SA` | yes | yes | cond. | yes | yes |
| Primary (deferred) | Sanskrit Library `svk.html` | `UNKNOWN` | **no** | **no** | **no** | **no** | yes |
| Primary (rejected) | TITUS `svk.htm` | `PERMISSION_REQUIRED` | cond. | **no** | **no** | **no** | yes |
| English | Wikisource Griffith 1895 | `PUBLIC_DOMAIN` **but EMPTY** | — | — | — | — | yes |
| English (complete) | sacred-texts Griffith | `PUBLIC_DOMAIN`, **RĀṆĀYANĪYA** | yes | yes | yes | yes | yes |
| **Audio** | **Wikimedia Commons, 474 ogg** | **`CC_BY_SA` + `CC0`** | **yes** | **yes** | cond. | **yes** | yes |
| Verification | VHP | `PERMISSION_REQUIRED` | cond. | **no** | **no** | **no** | yes |

**UPDATED — both verdicts for this Veda moved, in opposite directions.**

**May:** ingest, derive from and redistribute the **Sanskrit Wikisource** Kauthuma text under
attribution and share-alike; mirror the **474 Wikimedia Commons** sāman/gāna audio files carrying
per-file licences.
**May not:** ingest, modify or republish any Pandey-derived Kauthuma text — which is *every scholarly*
digital Kauthuma text located (GRETIL, TITUS, Sanskrit Library).

**Primary Sanskrit is CLEARED for ingestion, NOT yet for bulk release.** Sanskrit Wikisource is
CC BY-SA 4.0, and uniquely it **carries the gāna** (725 pages). Its arcika portion — the only part
`VG:WORK:SV:KAU` covers — is **106 pages**; the frequently quoted "840 Kauthuma pages" is the arcika
*plus* the out-of-scope gāna and must never be cited as this work's coverage.

> **CORRECTED 2026-09-07 by `SAMAVEDA_REFERENT_INTEGRITY_REPAIR`.** This paragraph previously said
> Wikisource "was proved independent of the Pandey lineage **textually**" and cited *"a text cannot
> inherit from a source it does not share an error with."* The grade of record is
> **`NOT_A_VERBATIM_COPY`**, not proven, and the evidence has moved against the stronger claim.
>
> The maxim is invalid as a universal — it excludes only verbatim **uncorrected** inheritance, not
> copy-then-correct — and it rested on **one** locus (the verse 1–2 pāda bleed) whose defect is
> conspicuous enough to be exactly what a copyist repairs. Parsing the full corpus then found **three
> loci pointing the other way**: running number 1179 is typeset as a second 1181 in **both** lineages
> at the same place, and single-daṇḍa verse terminators appear at 1133 and 1592 in **both**. Either
> common descent or a shared print antecedent; not adjudicated here.
>
> The better independence evidence is the wholesale difference in numbering system — running
> whole-saṃhitā versus daśati-local — not the pāda.
>
> **Consequence, and it is narrow.** Independence is *not* load-bearing for identity, which is
> mechanically source-blind; Sāmaveda identity is `FINAL`. It **is** load-bearing for text
> redistribution, because the redistribution basis is CC BY-SA on the *transcription*: if the
> transcription were a derivative of the Pandey text, that basis collapses (RIGHTS-9). **Re-verify at
> codepoint level at more than two loci, outside the Pūrvārcika defect-free region, before any bulk
> text release.** Tracked as `independence_codepoint_reverification`.

**English translation is now a GAP, not the one clear role.** Two independent failures:
1. The registered Wikisource Griffith Sāmaveda **contains no verse text** — 934 words,
   `{{TextQuality|25%}}`, 33 chapter links of which **zero resolve**. Every rights check on it passed.
   *A clean licence on an empty artifact is still an empty artifact.*
2. The only *complete* Griffith Sāmaveda (sacred-texts.com) is the **RĀṆĀYANĪYA** recension. Griffith's
   preface states verbatim *"I have followed Benfey's text"*, and Benfey is Rāṇāyanīya; his Part II has
   six Books where the Kauthuma Uttarārcika has nine prapāṭhakas. Aligning it to a Kauthuma text would
   be **silently wrong**, not approximate. The same preface establishes that Sāmaśramī's *Bibliotheca
   Indica* edition is also Rāṇāyanīya — so the archive.org DLI Sāmaśramī scans are **not** a Kauthuma
   witness either.

**Remaining blocker: the EDITION bar, not rights and not independence.** The precise statement is *"no
witness combines an identified printed edition with redistribution rights."*

**Coverage limitation, and it is larger than it sounds.** The GRETIL text has **zero gāna content**
(verified: "gana" 0, "gramageya" 0, "aranyageya" 0, "uhya" 0). The Kauthuma gāna corpus is roughly
**2,639 gānas against 1,875 arcika verses** — *the sung dimension is the larger artifact*, and it is why
Sāmaveda is a distinct Veda rather than a Rigveda excerpt. **A claim to "have the Sāmaveda" while
holding only the arcika would be false.**

### 3.3 Śukla Yajurveda — Vājasaneyi, Mādhyandina (`VG:WORK:YV:VSM`)

| Role | Source | Status | copy_local | redistribute | derive | mirror | link |
|---|---|---|---|---|---|---|---|
| Primary Sanskrit (artifact) | Sanskrit Wikisource | `CC_BY_SA` | yes | **yes** | cond. | **yes** | yes |
| — layer, faithful but 1836/1975 | `…VSM.UNACCENTED` (`PARALLEL_TEXT`) | `CC_BY_SA` | yes | **yes** | cond. | **yes** | yes |
| — layer, 1958/1975 but inferred | `…VSM.ACCENTED` (`EXTRACTED_FROM_CONTAINER`) | `CC_BY_SA` | yes | **yes** | cond. | **yes** | yes |
| Primary (rejected) | TITUS `vs.htm` | `PERMISSION_REQUIRED` | cond. | **no** | **no** | **no** | yes |
| Primary (deferred) | DCS CoNLL-U | `CC_BY` | yes | **yes** | **yes** | **yes** | yes |
| Primary (deferred) | Sanskrit Library `vs.html` | `CC_BY_NC_SA` | yes | cond. | cond. | cond. | yes |
| Primary | GRETIL | **ABSENT** | — | — | — | — | — |
| English | Griffith 1899, archive.org | `PUBLIC_DOMAIN` | yes | **yes** | **yes** | **yes** | yes |
| Traditional metadata | Sanskrit Wikisource | `CC_BY_SA` | yes | **yes** | cond. | **yes** | yes |
| Verification | VHP | `PERMISSION_REQUIRED` | cond. | **no** | **no** | **no** | yes |

**May:** ingest, derive from and redistribute the Sanskrit Wikisource Mādhyandina text and its
sarvānukramaṇī / ṛṣisūcī, under attribution and share-alike; use Griffith 1899 freely.
**May not:** redistribute the TITUS text or bulk-release derivatives of it; use any of it commercially
if the Sanskrit Library CC BY-NC-SA copy is later adopted.
**Note:** GRETIL hosts **no** Vājasaneyi Saṃhitā at all — verified by exhaustive search of the
1,033,721-byte GRETIL index (2026-09-07), zero occurrences of Vājasaneyi/Yajurveda/`vs_`/`vajas`/`yaju`.
Its `maitrs_*` files are **Maitrāyaṇī Saṃhitā = Kṛṣṇa Yajurveda**, a different Veda.
**Non-rights blocker:** the Wikisource printed edition is **unidentified** (empty `year`/`notes` header
fields) and transcription accuracy is unverified. Rights are solved; edition provenance is not.

### 3.4 Atharvaveda — Śaunaka (`VG:WORK:AV:SAU`)

| Role | Source | Status | copy_local | redistribute | derive | mirror | link |
|---|---|---|---|---|---|---|---|
| Primary Sanskrit | GRETIL `avs___u` / `avs_acu` | `REFERENCE_ONLY` | cond. | **no** | **no** | **no** | yes |
| Primary (deferred) | Sanskrit Library `avs.html` | `UNKNOWN` | **no** | **no** | **no** | **no** | yes |
| Primary (rejected) | TITUS `avs.htm` | `PERMISSION_REQUIRED` | cond. | **no** | **no** | **no** | yes |
| Sanskrit (VedaWeb) | VedaWeb AVS Sanskrit | `PERMISSION_REQUIRED` | cond. | **no** | **no** | **no** | yes |
| Wrong recension | GRETIL `sa_paippalAdasaMhitA.xml` | `UNKNOWN` | **no** | **no** | **no** | **no** | yes |
| English | Wikisource Whitney/Lanman 1905 | `PUBLIC_DOMAIN` | yes | **yes** | **yes** | **yes** | yes |
| Verification | VHP | `PERMISSION_REQUIRED` | cond. | **no** | **no** | **no** | yes |

**May:** use the Whitney/Lanman 1905 translation and its commentary freely.
**May not:** ingest or republish the GRETIL Śaunaka text — it self-declares reference-only.
**Blocker:** the digital Śaunaka text derives from **Orlandi, Pisa: Giardini, 1991**, a modern edition
still in copyright. GRETIL's "COPYRIGHT AND TERMS OF USAGE AS FOR SOURCE FILE" is a **pointer, not a
grant**; followed, it lands on TITUS (scholarly, attributed, strictly non-commercial) and behind that
on Orlandi.
**Only identified clean route:** **Roth & Whitney, Berlin 1856** is public domain by age. A fresh
transcription or OCR from an 1856 scan bypasses the Orlandi encumbrance entirely and would yield a
Śaunaka text VedaGraph could actually redistribute.
**Trap recorded:** GRETIL *does* have an Atharvaveda TEI — `sa_paippalAdasaMhitA.xml` — but it is the
**Paippalāda** recension, textually distinct from Śaunaka. Rejected on recension *before* rights were
reached. A filename search finds it and it looks like the answer. It is not.

### 3.5 Hindi translation — all four Vedas

| Role | Status | Every permission |
|---|---|---|
| Hindi translation, all four Vedas | `UNKNOWN` | **no** (link only) |

No Hindi candidate was adjudicated for any Veda. This is a **copyright** problem, not merely a sourcing
one. Under Indian copyright law the term is the author's life **plus 60 years**, so Śrīpād Dāmodar
Sātavalekar (died 1968) remains in copyright **until the end of 2028**. A Hindi translation must **not**
be treated as public domain by analogy with Griffith. Do not ingest a Hindi translation on the
assumption that "old Indian religious text" implies public domain.

---

## 4. Audio — summary of the rights position

Full detail in `docs/FOUR_VEDA_AUDIO_SOURCE_INVENTORY.md`. Governing rule RIGHTS-6: **audio carries its
own rights and never inherits them from the text source.** A recitation is a separate copyrightable
performance and usually a separate sound-recording copyright.

**One exception now exists: 474 Wikimedia Commons Sāmaveda files are mirrorable** (458 CC BY-SA 4.0,
16 CC0, verified per file). Those 16 files are the first and only CC0 material in the registry. For the
other three Vedas nothing is cleared for mirroring. The headline restricted items:

- **The only authentic Mādhyandina audio is VHP** — `PERMISSION_REQUIRED`, therefore `REFERENCE_ONLY`.
  Do not mirror.
- **Playability is not permission.** `lp_the-four-vedas-the-oral-traditions-of-hymn_various` is
  © 1968/69 Asch Records (verbatim in the OCR'd liner notes), now Smithsonian Folkways, still
  commercially sold. Its files return HTTP 200. It is `PERMISSION_REQUIRED` / prohibited.
- **CC Public Domain Mark 1.0 must be rejected at face value.** PD Mark is an *assertion by whoever
  applied it* that a work is already out of copyright — not a licence grant. Applied by third-party
  uploaders to post-2000 studio recordings of living reciters, it is not credible.
- **A licence from someone without standing is not a licence.** The 54-part IISH / Veda Prasar Samiti
  master is mirrored across five archive.org items carrying three mutually contradictory licence tags,
  **none from the rights holder** — the master is still sold as CDs by Veda Prasar Samiti.

---

## 5. Per-Veda verdicts

| Veda | Primary Sanskrit | Parallel | English | Hindi | Trad. metadata | Audio |
|---|---|---|---|---|---|---|
| **Rigveda** Śākala | **CLEAR** (NC+SA) | CLEAR | **CLEAR** | GAP | **CLEAR** (Apache) | REFERENCE_ONLY |
| **Sāmaveda** Kauthuma | **CLEAR** (SA); edition unnamed | CLEAR (same) | **GAP** | GAP | GAP | **MIRRORABLE** |
| **Śukla YV** Mādhyandina | rights **CLEAR** (SA), edition **named**, but **NO usable primary layer** | DEFERRED | **CLEAR** | GAP | **CLEAR** (SA) | REFERENCE_ONLY |
| **Atharvaveda** Śaunaka | **BLOCKED** (Orlandi 1991 / TITUS) | DEFERRED | **PARTIAL** — 84%, Kāṇḍa 20 untranslated | GAP | GAP | REFERENCE_ONLY |

**Primary Sanskrit is rights-clear for three of four Vedas. English is clear for two, partial for one,
and a GAP for one. Hindi is clear for none. Audio is mirrorable for exactly one.**

**But rights clarity is not usability, and only Rigveda has a usable primary text layer.** Śukla
Yajurveda is rights-clear with a complete artifact and *still* has no layer that is both faithful and
complete — its two layers split into faithful-but-incomplete (1,836/1,975) and complete-but-inferred
(1,958/1,975, `EXTRACTED_FROM_CONTAINER`). That was my error, corrected as CORR-9: I used rights clarity
as a proxy for role suitability, which is the same conflation I had warned Agent D against in the
opposite direction. **Rights clarity, artifact completeness, and the existence of a usable primary layer
are three independent properties.**

**Hindi has one viable route, previously missed.** Dayānanda Sarasvatī died **1883**, so his bhāṣya has
been public domain since **1944**, and it *is* on the Mādhyandina. By contrast Sātavalekar (d. 1968) is
in copyright in India until **2029** and Rāmnāth Vedālaṅkār (d. 2013) until **2074**. Also note an
eGangotri **CC0** scanning stamp sits over Sātavalekar — a scanning institution cannot dedicate someone
else's live copyright. The Dayānanda route is OCR-only with accents destroyed, so it is a real option
but not a cheap one.

Partial clarity per Veda **per role** is the real shape of this corpus, and Atharvaveda is the sharpest
illustration: its English layer can be built before its canonical Sanskrit layer can. That is a normal
outcome, not an anomaly.

**A closing observation about method.** Two verdicts improved during this audit — Śukla Yajurveda from
worst-covered to second-best, and Sāmaveda from blocked-outright to blocked-pending-verification.
Neither improvement came from finding a more permissive licence. Both came from finding a source with a
**different lineage**. Where the defect is at the root of a chain, only a different chain fixes it.
