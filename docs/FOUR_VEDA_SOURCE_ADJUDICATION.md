# Four-Veda Source Adjudication

**Owner:** Agent E (rights / provenance / source archivist) — single writer
**Compiled:** 2026-09-07 · all retrieval dates 2026-09-07 unless stated
**Machine-readable source of truth:** `data/source_registry/four_veda_source_matrix.yaml`
**Companions:** `docs/FOUR_VEDA_RIGHTS_MATRIX.md` · `docs/FOUR_VEDA_AUDIO_SOURCE_INVENTORY.md` ·
`docs/reports/FOUR_VEDA_SNAPSHOT_PROVENANCE.md`

This is the human-readable adjudication: what was investigated, what was chosen, what was rejected, and
why. Every source was assessed against **all seven roles** — primary Sanskrit, parallel Sanskrit, English
translation, Hindi translation, traditional metadata, audio, verification/reference — for **all four
Vedas**. 41 source-role rows, 15 sources, 46 registered artifacts.

---

## 1. Headline verdict

| Veda | Primary Sanskrit | Parallel | English | Hindi | Trad. metadata | Audio |
|---|---|---|---|---|---|---|
| **Rigveda** Śākala | **CLEAR** (NC+SA) | CLEAR | **CLEAR** | GAP | **CLEAR** (Apache) | reference-only |
| **Sāmaveda** Kauthuma | **CLEAR** (SA) — edition unnamed | CLEAR (same) | **GAP** | GAP | GAP | **MIRRORABLE** |
| **Śukla YV** Mādhyandina | rights **CLEAR** (SA), but **no usable primary layer** — see §3.3 | DEFERRED | **CLEAR** | GAP | **CLEAR** (SA) | reference-only |
| **Atharvaveda** Śaunaka | **BLOCKED** | DEFERRED | **PARTIAL** (84%) | GAP | GAP | reference-only |

- **Primary Sanskrit is rights-clear for three of four Vedas.** Atharvaveda alone is blocked.
- **But a *usable* primary text layer exists for only one — Rigveda.** Rights clarity and usability are
  different questions; see §3.3 and correction CORR-9.
- **Hindi is clear for none** — and that is a copyright fact, not a sourcing failure.
- **Audio is mirrorable for exactly one Veda** (Sāmaveda, 474 Commons files). Everything else is
  reference-only.
- **Nothing is commercially licensable** except the Rigveda's traditional metadata (Apache-2.0) and an
  unused CC BY Yajurveda fragment.

**The shape that matters: clarity is per-Veda AND per-role, never per-Veda alone.** Atharvaveda can be
given an English layer before it can be given a canonical Sanskrit one. Sāmaveda is the inverse — its
Sanskrit is clear and its English is a gap. Any readiness statement of the form "Veda X is ready" is
malformed.

---

## 2. What the governing rule actually bought us

> **Rights attach to each source file or asset, not merely to a host website.**
> — `data/registry/rights.yaml`, RIGHTS-1

This was existing policy. The audit's finding is that it is **load-bearing, not decorative**: it changed
verdicts in *both* directions, and it caught one of my own errors.

**GRETIL is the worked example.** One repository, three Vedas, three outcomes:

| Veda | File | Artifact licence | Verdict |
|---|---|---|---|
| Rigveda | `sa_Rgveda-edAufrecht.xml` | CC BY-NC-SA 4.0, no contradicting header | **usable** |
| Sāmaveda | `sa_sAmavedasaMhitA.xml` | CC BY-NC-SA 4.0 **contradicted inside the same file** | `PERMISSION_REQUIRED` |
| Atharvaveda | `avs___u.htm`, `avs_acu.htm` | **no CC licence**; "REFERENCE PURPOSES ONLY" | `REFERENCE_ONLY` |

GRETIL publishes **no site licence at all** — Agent D grepped the full 1,033,721-byte index for
*licence*, *license*, *copyright*, *terms of use*, *Creative Commons* and *public domain* and found
**zero** occurrences. Anyone reasoning "GRETIL's Rigveda is CC BY-NC-SA, therefore GRETIL is
CC BY-NC-SA" would have been wrong about two Vedas out of three.

Full treatment of the five distinct artifact-vs-repository patterns, including the *inverse* cases where
site level is legitimately operative, is in `docs/FOUR_VEDA_RIGHTS_MATRIX.md` §2.

---

## 3. Per-Veda adjudication

### 3.1 Rigveda — Śākala (`VG:WORK:RV:SAK`)

**The best-covered Veda, and the only one whose primary text is a named scholarly edition.**

| Role | Selected | Status | Why |
|---|---|---|---|
| Primary Sanskrit | GRETIL Aufrecht TEI 2019 | `CC_BY_NC_SA` | Only candidate with an explicit artifact licence, **no** contradicting upstream header, a named critical edition (Aufrecht 1877), accented TEI, and a hash-verified snapshot. 10,552 verse records. |
| Parallel Sanskrit | VedaWeb, commit `d3eb8af7…` | per-version | Six Sanskrit versions in one file under **two different CC licences** — the reason `text_versions.yaml` exists. |
| English | Wikisource Griffith 1896 | `PUBLIC_DOMAIN` | PD by age; 1,245 pages snapshotted with per-page provenance. |
| Traditional metadata | WSC2023 Anukramaṇī | `APACHE_2_0` | **The only commercial-safe component in the entire corpus.** |
| Verification | VHP | `PERMISSION_REQUIRED` | Authoritative cross-check; never ingested. |

**Rejected:** VedSearch — no licence establishable, undisclosed edition, aggregator not edition.
**Deferred:** GRETIL padapāṭha TEI (redundant; VedaWeb already covers it rights-resolved — and per
RIGHTS-1 its licence *cannot* be inferred from the Aufrecht file even though both are GRETIL Rigveda
files); Sanskrit Library RV (rights fine, bytes unreachable).

**Standing constraint:** CC BY-NC-SA is viral and permanently forecloses commercial licensing of any
output incorporating the Aufrecht text.

### 3.2 Sāmaveda — Kauthuma (`VG:WORK:SV:KAU`)

**Both verdicts moved during this audit, in opposite directions.**

**The Pandey lineage — one defect, three hosts.** Every *scholarly* digital Kauthuma text descends from
the same 1998/1999 Anshuman Pandey data entry, whose own header states:

> "Copyright (C) 1998 Anshuman Pandey / This document may only be used for academic and scholarly
> purposes. **No modification of this document is in any way authorized.** Any publication or other use
> of this document requires written consent of the editor."

GRETIL and The Sanskrit Library have **each** stamped CC BY-NC-SA over it. Their agreement is **not
corroboration — it is the same defect twice.** I verified the Pandey notice appears directly on TITUS's
`svk001.htm` too, so it is three hosts, one root. Our pipeline parses, normalizes, re-keys and
republishes — that is *both modification and publication*, so the prohibition binds.

**What cleared it: a different lineage, not a better licence.** Agent B proved Sanskrit Wikisource
independent **textually** rather than by provenance argument — at running verses 1–2, GRETIL misplaces a
pāda between verses while Wikisource has both whole, and the two use different numbering systems. *A
text cannot inherit from a source it does not share an error with.*

| Role | Outcome | Status |
|---|---|---|
| Primary Sanskrit | **SELECTED** — Sanskrit Wikisource, 840 pages | `CC_BY_SA` |
| Primary Sanskrit | REJECTED — GRETIL TEI 2020 | `PERMISSION_REQUIRED` |
| English | **GAP** — see below | — |
| Traditional metadata | GAP | — |
| Audio | **SELECTED — Wikimedia Commons, 474 files, MIRRORABLE** | `CC_BY_SA` + `CC0` |

**The English translation is a GAP, and this correction is instructive.** The registered Wikisource
Griffith Sāmaveda **contains no verse text** — 934 words, `TextQuality|25%`, 33 chapter links of which
zero resolve. **Every rights check on it passed**: PD banner, clear date, long-dead author. What no
rights check catches is that there is nothing behind the banner. *Rights clearance is not content
verification.*

Worse, the only *complete* Griffith Sāmaveda (sacred-texts.com) is the **Rāṇāyanīya** recension —
Griffith's preface says "I have followed Benfey's text" and Benfey is Rāṇāyanīya; his Part II has six
Books where the Kauthuma Uttarārcika has nine prapāṭhakas. Aligning it to a Kauthuma text would be
**silently wrong**, not approximate. The same preface also establishes that Sāmaśramī's *Bibliotheca
Indica* edition is Rāṇāyanīya, so the archive.org DLI Sāmaśramī scans are not a Kauthuma witness either.

**Two coverage facts that must not be buried.** The GRETIL text has **zero gāna content** (verified:
"gana" 0, "gramageya" 0, "aranyageya" 0, "uhya" 0). And the scale is inverted from intuition — the
Kauthuma gāna corpus is roughly **2,639 gānas against 1,875 arcika verses**. *The sung dimension is the
larger artifact, and it is why Sāmaveda is a distinct Veda rather than a Rigveda excerpt.* **A claim to
"have the Sāmaveda" while holding only the arcika would be false.** Only Sanskrit Wikisource carries the
gāna as reusable text (725 pages).

**Remaining blocker:** the **edition** bar, not rights and not independence. The precise statement is
*"no witness combines an identified printed edition with redistribution rights."*

### 3.3 Śukla Yajurveda — Vājasaneyi, Mādhyandina (`VG:WORK:YV:VSM`)

**Went from apparently worst-covered to second-best during the audit.**

**GRETIL does not host this Veda at all.** Not "unknown" — *absent*. Agent C grepped all 6,327 index
anchors (zero hits) and probed eight plausible filenames (all 404). GRETIL's own index says, verbatim:

> "Vajasaneyi-Samhita (input by …)" / "Restricted download / proprietary format from TITUS" /
> "Converted file(s) not available at present"

Its only YV saṃhitā is **Maitrāyaṇī = Kṛṣṇa Yajurveda**, the wrong Veda. Recorded as
`NO_ARTIFACT_EXISTS`, because an unrecorded absence gets retried.

| Role | Selected | Status | Why |
|---|---|---|---|
| Primary Sanskrit | Sanskrit Wikisource — **artifact only; no usable layer** | `CC_BY_SA` | Artifact is **40/40 adhyāyas, 1975/1975 mantras** (computed), accented Devanāgarī, revision-pinned, **edition named** — but see the layer split below |
| English | Griffith 1899, `in.ernet.dli.2015.215626` | `PUBLIC_DOMAIN` | Resolves a standing placeholder |
| Traditional metadata | Wikisource sarvānukramaṇī + ṛṣisūcī | `CC_BY_SA` | Fills a role previously recorded as an outright GAP |

**The edition-identity correction is the methodological lesson.** I recorded the edition as
*unidentified* because the per-adhyāya headers carry empty `year`/`notes` fields — which is true.
Agent C found the wiki's **separate preface page** reproduces the printed title page verbatim:
**Vāsudeva Śarmā Paṇaśīkara, 2nd edn, Nirṇaya Sāgara Press, Bombay, Śaka 1850 = CE 1929**, with Uvaṭa's
*Mantrabhāṣya* and Mahīdhara's *Vedadīpa*. **Edition identity may live on a sibling page rather than in
the artifact header**, so an empty header is not proof the edition is unknown — *unlike* the GRETIL
Sāmaveda TEI, whose `sourceDesc/bibl` is affirmatively empty with no sibling page to rescue it. Those
two cases look identical and are not.

**Rights layering, both layers clean:** the 1929 print is PD by age; the transcription is CC BY-SA 4.0.
**No encumbered link anywhere in the chain** — which is exactly what distinguishes this Veda from
Sāmaveda (Pandey) and Atharvaveda (Orlandi).

### **This Veda has no usable primary text layer — correction CORR-9, and it was my error**

Surfaced by Agent C as a direct consequence of my own ruling that the accented layer is
`EXTRACTED_FROM_CONTAINER`. The rights-clear, complete artifact decomposes into two text layers and
**neither can serve as primary**:

| Layer | Coverage | Faithful? | Role |
|---|---|---|---|
| `WIKISOURCE_SA.YV.VSM.UNACCENTED` | **1,836 / 1,975** mantras | yes — direct transcription | `PARALLEL_TEXT` |
| `WIKISOURCE_SA.YV.VSM.ACCENTED` | 1,958 / 1,975 | **no** — extraction-derived | `EXTRACTED_FROM_CONTAINER` |

**No layer is both faithful and complete**, and `EXTRACTED_FROM_CONTAINER` must never be selected as
`primary_sanskrit`.

**The error was mine and it is the exact mistake I had been warning others about, run backwards.** I told
Agent D that role is not a proxy for permission — then used *rights clarity* as a proxy for *role
suitability*. Same conflation, mirrored direction. **Rights clarity, artifact completeness, and the
existence of a usable primary layer are three independent properties.** This Veda has the first two
without the third, and a single `SELECTED` verdict cannot express that.

Agent C fixed its build at the root rather than by constant: the builder now reads `text_role` from
`load_text_versions()` instead of choosing one in code, unregistered ids fall back to `COMPARISON_ONLY`
(most restrictive, never permissive), its config field was renamed `primary_text_version` →
`leading_text_version` to stop implying a role it never had, and its report states
`has_primary_text_layer: NO`.

**Upgrade path, scoped but not attempted:** a hybrid parser using accent-presence *confirmed by* the
ordinal headers Agent C proved exist would likely make the accented layer faithful and recover the 17
missing mantras — but doing it properly requires resolving the VSM 16.37 variant (`स्रुत्याय` vs
`सत्याय`), which is a philological decision that should not be made unilaterally. Agent C correctly
declined to half-implement it.

**Rejected:** TITUS (`PERMISSION_REQUIRED`, see §4) — *technically the best text found*: complete,
accented, per-pāda anchors, named edition (Weber). Rejected purely on rights. **Deferred:** Sanskrit
Library `vs.html` (`CC_BY_NC_SA`, best chain of title in the whole set — root is Weber 1849, PD by age —
but bytes unreachable); DCS (**CC BY 4.0**, the most permissive licence found anywhere, but only
adhyāyas 1–15 of 40 and **zero accents** — rights are not the binding constraint, coverage is).

### 3.4 Atharvaveda — Śaunaka (`VG:WORK:AV:SAU`)

**The one Veda whose primary Sanskrit remains blocked — for a different legal reason than Sāmaveda.**

The digital Śaunaka text derives from **Orlandi, Pisa: Giardini, 1991** — a modern edition **still in
copyright** — collated with the PD Roth/Whitney 1856. GRETIL's files self-declare:

> "THIS GRETIL TEXT FILE IS FOR REFERENCE PURPOSES ONLY! COPYRIGHT AND TERMS OF USAGE AS FOR SOURCE FILE."

That clause is a **pointer, not a grant**, and following it resolves to TITUS's express prohibition:

> "This text is part of the TITUS edition of Atharva-Veda-Samhita (Saunaka). Copyright TITUS Project,
> Frankfurt a/M, 4.3.2015. **No parts of this document may be republished in any form** without prior
> permission by the copyright holder."

**The key structural finding (Agent D): TITUS, GRETIL's `avs_*.htm`, and VedaWeb's AVS Sanskrit layer
are all the same Petr/Vavroušek text.** They are **one licensing dependency wearing three hats**, not
three sources to compare — so there is no independent Śaunaka witness among them, and **one** written
permission to the TITUS Project would unlock all three. That is the highest-value single rights action
for this Veda.

| Role | Outcome | Status |
|---|---|---|
| Primary Sanskrit | **BLOCKED** — GRETIL / TITUS / VedaWeb-Sanskrit | `REFERENCE_ONLY` / `PERMISSION_REQUIRED` |
| English | **SELECTED, INCOMPLETE** — Whitney/Lanman 1905 via VedaWeb | `PUBLIC_DOMAIN` |
| Parallel Sanskrit | DEFERRED — Roth & Whitney, Berlin 1856 | `UNKNOWN` |

**Coverage limitation on the translation, material and honest:** 4,881 of 5,842 stanzas. **Kāṇḍa 20 —
all 958 stanzas, ~16% of the Veda — is not translated**, and en.wikisource has *the same gap* (its Book
XX page is 278 bytes with no hymn subpages). **The gap belongs to the digitised Whitney tradition, not
to either host; no source-switching closes it.**

**Only identified clean route to the Sanskrit:** fresh transcription from **Roth & Whitney, Berlin
1856**, PD by age, bypassing Orlandi entirely.

**Two traps recorded so they are not re-walked:**
1. GRETIL *does* have an Atharvaveda TEI — `sa_paippalAdasaMhitA.xml` — but it is the **Paippalāda**
   recension, textually distinct from Śaunaka. Rejected on recension *before* rights were reached. A
   filename search finds it and it looks like the answer.
2. TITUS hosts a plain-text AVS under `/private/` labelled "TITUS Members only". It currently returns
   **HTTP 200 with no authentication**, and `/private/` is `Disallow`ed in `robots.txt`. **An unenforced
   restriction is still a restriction.** Must not be ingested.

**Recension discipline done properly:** both GRETIL AV files were proved Śaunaka from the *artifact*,
not the filename — via the document title *and* all 11,395 body locators being prefixed `AVS_` with the
palatal sibilant. Computed coverage: 20 kāṇḍas, 731 sūktas, 5,839 mantras, 11,395 pādas.

---

## 4. Corrections applied, including one of my own errors

Recorded openly. Machine-readable under `corrections_applied` in the matrix.

| # | Subject | Was | Now |
|---|---|---|---|
| CORR-1 | **TITUS, all 3 Vedas** | `RESEARCH_ONLY` | `PERMISSION_REQUIRED` |
| CORR-2 | Sāmaveda English | SELECTED | **GAP** |
| CORR-3 | Sāmaveda primary Sanskrit | DEFERRED | **SELECTED** |
| CORR-4 | Śukla YV edition | unidentified | **named (1929)** |
| CORR-5 | Audio, all 4 | 0 mirrorable | **474 files mirrorable** |
| CORR-6 | VHP direct linking | permitted | **contested** |

**CORR-1 was my mistake, and it is the one worth dwelling on.** I classified TITUS from its project-wide
page (`texte2.htm`) alone, which grants free scholarly use. **Every TITUS text page carries a stricter
per-page notice** forbidding republication in any form. Agent C found it; I then verified it myself by
fetching `vs001.htm`, `svk001.htm` and `avs001.htm` before amending.

This is a failure of **exactly the rule I was enforcing on everyone else**. Note the direction: the
**site** page was the *more permissive* of the two, so relying on it was not merely incomplete — it was
wrong in our own favour. *Checking "a" licence page is not the same as checking THE artifact.*

**CORR-6 is a new constraint affecting all four Vedas.** Two live IGNCA pages contradict each other,
both footer-dated 2026-08-27:

> **Terms & Conditions:** "We do not object to linking directly to the information that is hosted on this
> portal and **no prior permission is required** for the same."
> **Hyper linking Policy:** "**Prior permission is required** before hyperlinks are directed from any
> website/portal to this site."

Found independently by Agents B, D and my own research. Consequence: **for VHP even the link-only
fallback is not clean**, which is unusual and matters because VHP is the verification source for all
four Vedas. Framing is separately prohibited. Needs IGNCA in writing.

---

## 5. Hindi — a copyright wall, not a sourcing gap

`UNKNOWN` for all four Vedas. Under Indian copyright law the term is **life + 60 years**:

| Translator | Died | In copyright until | Note |
|---|---|---|---|
| **Dayānanda Sarasvatī** | 1883 | **PD since 1944** | **The one safely-PD Hindi option**; his bhāṣya *is* on the Mādhyandina |
| Śrīpād Dāmodar Sātavalekar | 1968 | **1 Jan 2029** | Commonly cited; **not** PD |
| Rāmnāth Vedālaṅkār | 2013 | 2074 | |

Also recorded: "Devi Chand" is **English**, not Hindi. And an eGangotri **CC0** scanning stamp sits over
Sātavalekar — a scanning institution cannot dedicate someone else's live copyright.

**A Hindi translation must not be treated as public domain by analogy with Griffith.** The one viable
route (Dayānanda) is OCR-only with accents destroyed, so it is a real option but not a cheap one.

---

## 6. Rejected and deferred — reasons, not dismissals

**Rejected on rights:** GRETIL Sāmaveda TEI · GRETIL Atharvaveda HTML · TITUS (all three Vedas) ·
VedaWeb AVS Sanskrit · VedSearch.
**Rejected on recension** (before rights): GRETIL Paippalāda · sacred-texts Griffith Sāmaveda
(Rāṇāyanīya) · Sāmaśramī *Bibliotheca Indica* (Rāṇāyanīya) · all Kāṇva Yajurveda audio.
**Rejected on coverage** (rights were fine): Wikisource Griffith Sāmaveda (no verse text) · DCS
(15/40 adhyāyas, no accents).
**Deferred on acquisition** (rights resolved, bytes unreachable): Sanskrit Library, all four Vedas.
**Deferred on chain of title:** Sanskrit Library Sāmaveda (Pandey root) and Atharvaveda (Orlandi root).
**Off-limits:** TITUS `/private/` AVS plaintext.

Note how rarely "no licence" was the operative reason. **Recension mismatch and empty coverage rejected
as many candidates as rights did** — and both are invisible to a rights check.

---

## 7. Actions ranked by value

1. **Write to IGNCA (VHP).** Single rights holder for the best-aligned audio across **all four**
   recensions, the only authentic Mādhyandina audio, and the only accented-Devanāgarī AVS text. **One
   grant unlocks both text and audio.** Also ask them to resolve the linking contradiction (CORR-6).
2. **Write to the TITUS Project.** One permission unlocks the accented AVS in its cleanest
   machine-readable form across TITUS, GRETIL and VedaWeb simultaneously, and would additionally make
   TITUS's Mādhyandina text — technically the best Yajurveda text found — the preferred primary, since
   it is a *named scholarly edition* where our selected Wikisource artifact is a community
   transcription.
3. **Email The Sanskrit Library.** Their Vājasaneyi record has the **best chain of title in the entire
   four-Veda set** (root: Weber 1849, PD) under CC BY-NC-SA 3.0. The *only* blocker is that the bytes
   are not exposed. **The one deferral a single email could convert into a selection.**
4. **Write to Sriranga Digital.** Converting an existing informal, screenshot-documented permission into
   a real licence would unlock a complete, per-sūkta, 1,028-file Rigveda Śākala audio corpus with named
   reciters and a known pāṭham.
5. **Validate transcription fidelity** of both selected Wikisource texts against their printed editions.
   Rights are solved; **fidelity is now the open question**, and authority tier is
   `COMMUNITY_TRANSCRIPTION`.
6. **Chase two Sāmaveda gāna leads manually** (shaivam.org, vedamu.org) — both defeated automated
   inspection, and Kauthuma gāna is the scarcest material in the landscape.
7. **Reconcile snapshot `source_id` values** — 71 snapshots use unregistered ad-hoc ids. See
   `docs/reports/FOUR_VEDA_SNAPSHOT_PROVENANCE.md` §F1.

---

## 8. Closing observation on method

Two verdicts improved during this audit and one degraded. **Not one of those changes came from finding a
more permissive licence.**

- Sāmaveda's primary text cleared because a source with a **different lineage** appeared. Where a defect
  sits at the *root* of a chain, only a different chain fixes it — shopping hosts replicates the defect
  and calls it corroboration.
- Śukla Yajurveda's edition was identified because someone read a **different page** of the same source.
- Sāmaveda's English degraded because someone checked whether the **content existed** at all.

The rights field is where a rights investigation *begins*. In the audio survey the correlation actually
**inverts**: the unlicensed majority is at least honestly silent, while the licensed minority is the
dangerous part — 47 NC-ND items that look usable but forbid the only operation we need, and 21 Public
Domain Mark items that look free and are 2020 studio recordings tagged by people who never owned them.

**`UNKNOWN` was the correct terminal answer more often than any permissive class.** That is not a
failure of the survey. It is the survey working.

### A note on how to read the verdicts in this document

**A verdict label describes the state of our KNOWLEDGE, not the desirability of the answer.** This
matters because several verdicts here are negative, and there is a standing temptation to relabel a
negative finding as an incomplete one — which sounds more modest and is actually less honest.

Śukla Yajurveda is the worked example. Its source stack is **fully adjudicated**: every candidate was
assessed with verbatim artifact-level rights evidence, the recension was proved from the artifacts
rather than filenames, counts were computed from every snapshot, and rights and roles are adjudicated
and registered. **Nothing about it is unknown.** What is missing is a *property of the sources* — no
layer that is both faithful and complete — not a missing piece of assessment. So the correct label is
"adjudicated, and the answer is partly negative", never "not yet adjudicated".

Calling that state *incomplete* would assert that we do not know something we in fact established, which
**understates the work and mislabels a finding as a gap**. It is the same principle as
`data/registry/rights.yaml`'s treatment of `UNKNOWN` — a legitimate terminal answer, not a placeholder
to be optimistically resolved — applied one level up, to verdicts instead of statuses.

The practical test: if new *research* would change the label, it is incomplete. If only a new *source*
would change it, it is complete and negative. Every negative verdict in this document is the second
kind.
