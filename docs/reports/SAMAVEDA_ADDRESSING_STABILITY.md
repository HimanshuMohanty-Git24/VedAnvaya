# Sāmaveda Addressing Stability — Is the Kauthuma Address Edition-Independent?

**Run:** `SAMAVEDA_CANONICAL_IDENTITY_FINAL_CLOSURE` · **Date:** 2026-09-07
**Starting commit:** `dc160d7` · **Work:** `VG:WORK:SV:KAU` (Kauthuma, arcika corpus only)
**Investigated by:** Agent C2 · **Printed-edition evidence:** Agent B
**Question:** is `Arcika → Prapāṭhaka → Ardha → Daśati → Verse` specific to the unidentified
edition that Sanskrit Wikisource transcribed, or a stable Kauthuma reference convention
corroborated independently of it?

This document is about **ADDRESSING, not textual reuse.** No encumbered Sanskrit is reproduced
anywhere in it — level names, counts, addresses and running numbers only.

---

## 0. Verdict

### `ADDRESSING_IS_EDITION_INDEPENDENT`

Scoped precisely, because the scope *is* the finding:

- The **ordered level list** `Arcika → Prapāṭhaka → Ardha → Daśati → Verse` and the **container
  boundaries** it names are corroborated across three textually independent lineages, four
  independent scholarly descriptions, **and an identified printed edition** — to the individual
  verse.
- **The dependency runs the opposite way from the one the session brief anticipated.** Wikisource
  is the witness that *least* resembles the declared 5-tuple. The addressing does not depend on
  the Wikisource edition.

### But the verdict does NOT license freezing the candidate key

The level *list* is edition-independent. The **numeric instantiation of slot 1 is not.** Freezing
`A{arcika}:P{prapathaka:02d}:R{ardha}:D{dasati:02d}:V{verse:02d}` today would freeze **Pandey
arcika arity**, which every non-Pandey witness contradicts, and two hard tuple collisions were
found (§4).

---

## 1. Witness comparison matrix

| Witness | Independent of Pandey? | # arcikas | Level vocabulary | Variable depth | Absence marked how | 4th-level semantics | Example address |
|---|---|---|---|---|---|---|---|
| **GRETIL TEI** (body ¶1; sha256 `91c28c03…92456`) | **NO** — root of the lineage; `respStmt` "data entry / Anshuman Pandey" | **4** flat siblings: 1 Pūrv-chandas (RN 1–585), 2 Āraṇya (586–640), 3 Mahānāmnya (641–650), 4 Uttar (651–1875) | ārcika \| prapāṭhaka \| ardha \| daśati \| verse \| line | yes, fixed-arity 5 slots | literal `0` | daśati; **1–10 continuous across the prapāṭhaka** in Pūrv (ardha 1 = d1–5, ardha 2 = d6–10); **resets per ardha** in Uttar | `1 1 1 0101a` |
| **Sanskrit Wikisource** (840 pp. under `…/कौथुमीया/संहिता`, enumerated live 2026-09-07) | **YES** | **2** top-level (Pūrv 74 pp., Uttar 32 pp.); Chandas / Āraṇya / Mahānāmnya are the **three sub-segments of Pūrvārcika** | arcika, prapāṭhaka, **ardha** (`…अर्द्धः`, 22 pp.), daśati (title word), **sūkta** (body word) | yes, by **path-relative arity 2–4**, not slots | by **omitting the level** | **daśati** in Pūrv; **sūkta** in Uttar — `दशति` occurs **0 times** across all 22 Uttar ardha pages | `1.1.1.1`, `1.2.1`, `2.1.1` |
| **Sāmaśramī print, Bibliotheca Indica 1874–78** (§3) | **YES** — identified printed edition | not determined from the scan | **all five levels printed in colophons** | — | — | `दशति` printed, 29 hits | `इति पञ्चम-दशति ॥` |
| **TITUS** (`svkx.htm`, fetched 2026-09-07) | **NO** — Pandey lineage | **4** | SV > SVK > Arcika > Prapāṭhaka > **Ardha-Prapāṭhaka** > Daśati > Ṛca > Pāda | yes, 8 levels | n/a | daśati | n/a |
| **Griffith 1895** (Benfey) — **RĀṆĀYANĪYA, not Kauthuma** | **YES** — a century pre-Pandey | **2** ("Part I" / "PART SECOND") | PART / BOOK / **CHAPTER** / **DECADE** / verse | yes | omits the block entirely | **DECADE** in Part I; no 4th-level label in Part Second | `Part I, Book III, Chapter II, Decade IV` |
| **Vedapeetha** (`vedapeetha.org/pages/kauthuma-samhita`) | YES | **2** | prapāṭhaka, **ardha-prapāṭhaka**, daśati | — | — | "**59 Daśatis** or decades" in Pūrv; Uttar = 9 prapāṭhakas "**with 22 ardha-s**" | — |
| **Caland / Kashikar** (Pañcaviṃśa-Brāhmaṇa intro) | YES | **3** | prapāṭhaka, ardha ("halves"), daśati, parvan | — | — | Uttar: 9 prapāṭhaka "each divided in two (**the last four in three**) halves"; no named 4th level | cites by edition and page |
| **Wikipedia / Vedic Heritage Portal (GoI)** | YES | **2**; Āraṇya = 65 mantras **inside** Pūrv, last 10 = Mahānāmnī | Āgneya 114 / Aindra 352 / Pavamāna 119 / Āraṇya 65 = **650**; Uttar **1225**; total **1875** | — | — | not named | none given |
| **B. R. Sharma, HOS 57** (printed critical Kauthuma edition, 2001/02) | YES | **2** — vol 1 Pūrvārcika, vol 2 Uttarārcika, vol 3 indexes | — | — | — | — | — |

---

## 2. Agreements

Counted exactly, so the corroboration cannot be inflated again.

1. **Prapāṭhaka counts: Pūrvārcika 6, Uttarārcika 9.** GRETIL, Wikisource, Vedapeetha,
   Caland/Kashikar, Griffith (Books I–VI / I–IX). **5 witnesses, 3 lineages.**
2. **The Uttarārcika ardha lattice is `[2,2,2,2,2,3,3,3,3]` = 22 ardhas.** GRETIL (label
   extraction), Wikisource (22 `…अर्द्धः` pages, exactly 2 under `2.1`–`2.5` and 3 under
   `2.6`–`2.9`), Griffith (Part Second Books I–V × 2 chapters, VI–IX × 3 = 22), Vedapeetha, and
   Caland/Kashikar. **5 witnesses, 3 lineages, exact 9-value fingerprint.**
3. **All 21 fetchable Uttarārcika ardha CLOSING boundaries agree to the verse** between GRETIL and
   Wikisource: 712, 774, 829, 885, 954, 1115, 1174, 1252, 1346, 1378, 1434, 1488, 1534, 1572,
   1616, 1656, 1710, 1764, 1815, 1848, 1875. **21/21, zero disagreements.**
4. **The Pūrvārcika ardha→daśati lattice is `(5,5)(5,5)(5,5)(5,5)(5,5)(5,4)`.** GRETIL and
   Griffith match **11/12 cells**; the sole mismatch is prapāṭhaka/Book 3 ardha/Chapter 1, where
   *both* witnesses independently carry a one-off defect. Corrected, 12/12.
5. **59 daśatis in the Pūrvārcika chandas portion.** GRETIL (59 distinct prapāṭhaka/daśati pairs),
   Wikisource (59 four-number daśati pages), Griffith (58 decades + the 1 defective slot),
   Vedapeetha. **4 witnesses, 3 lineages.**
6. **Daśati boundaries match to the verse.** `1.1.1.1` → RN 1–10 = GRETIL `(1,1,d1)`; `1.1.1.5` →
   45–54 = `(1,1,d5)`; `1.2.1` → 586–594 = `(2,0,d1)`; live `1.1.2.6` → 145–154 = `(1,2,d6)`.
   **4/4.**
7. **Daśati size is non-uniform, 6–14 verses.** GRETIL measured (min 6, max 14); Vedapeetha
   independently: "though a Daśati should normally be a collection of 10 mantra-s, many of them
   have anywhere from 6 to 14 mantra-s." **Exact range match.**
8. **The Mahānāmnya has no daśati subdivision.** GRETIL (`daśati = 0`), Wikisource (a single
   unnumbered page), Caland/Kashikar ("an appendix"). **3 witnesses.**
9. **Verse totals 585 + 55 + 10 + 1225 = 1875; Pūrvārcika = 650.** GRETIL measured, Wikipedia,
   Vedic Heritage Portal, Vedapeetha.
10. **`line` / pāda is a sub-verse label, not an identity level.** GRETIL 6th slot (`a`/`c`/`e`);
    TITUS 8th level `Pāda`. Correctly excluded from identity.

**Tally for the level list and container boundaries:** 1 source lineage (Pandey, via
GRETIL/TITUS/sanskritdocuments = **ONE** witness) + 2 independent textual lineages (Wikisource;
Griffith/Benfey, a different recension) + 1 identified printed edition (Sāmaśramī) + 4 independent
secondary descriptions.

---

## 3. The printed-edition corroboration — the durable win of this session

Agent B located a **scan-backed** Sāmaveda project on Sanskrit Wikisource that all four prior
search routes missed, because the `अनुक्रमणिका:` (Index) namespace had never been probed. Its
printed edition is fully identified:

> Sāmaveda-saṃhitā, with the commentary of Sāyaṇa (`टीका=सायणभाष्यसहितम्`), ed. Satyavrata
> Sāmaśramī Bhaṭṭācārya. Calcutta: Asiatic Society of Bengal (Bibliotheca Indica). 5 volumes,
> 1874–1878. Vols 1–3 on Wikimedia Commons; vols 4–5 on archive.org.

All five levels were read **directly off the printed colophons** via the `पृष्ठम्:` OCR:

| Level | Printed evidence (volume, page) |
|---|---|
| **Ārcika** | `इति छन्दस्यार्चिके प्रथमः प्रपाठकः ॥ १ ॥` — vol 1 p. 260; `छन्दस्यार्चिके द्वितीयस्यार्धः प्रपाठकः` — p. 342 |
| **Prapāṭhaka** | same colophons; `इति ग्रामेगेये नवमः प्रपाठकः` p. 758; `अष्टमः प्रपाठकः` p. 675 |
| **Ardha** | `इति चतुर्थस्यार्धः प्रपाठकः` p. 693; `नवमस्यार्ध प्रपाठकः` p. 709; `द्वितीयस्यार्धः प्रपाठकः` p. 342; vol 3 p. 123 |
| **Daśati** | `इति पञ्चम-दशति ॥` pp. 260, 342, 424, 693; `दशति` = 29 hits across the scans |
| **Verse** | `॥ <n> ॥` throughout |

**The five-level address is therefore attested by an identified printed edition and no longer rests
only on a hand-keyed wiki text plus an encumbered 1998 e-text.** This holds *independently of the
recension question* below.

### Two negatives that came with it, both useful

1. **The continuous 1..1875 running number is NOT corroborated by the print.** The edition prints
   `॥ <local verse no.> ॥ <second number>` where the second number **resets per section** (p. 316
   → १४/१५ where p. 260 → ९६). `insource:"१८७५"` returns 0 hits. The running number is attested
   only by the wiki text and GRETIL — which independently vindicates Refusal 3 in
   `docs/FOUR_VEDA_STRUCTURAL_MODEL.md`.
2. **Two further addressing systems are printed in parallel**, and any alignment work must expect
   them:
   - adhyāya / khaṇḍa / sūkta **running heads** — vol 3 p. 67 reads
     `[७ अ० ४ ख० ०२ सू० १,२] उत्तरार्चिकः`;
   - a printed **Sāmaveda↔Ṛgveda concordance** — vol 1 p. 710 reads
     `११४ उत्तरार्चिकस्य २,२,९,८,१ = ऋग्वेदस्य ३८६, २०५८`.

### Why this does NOT clear the ADR-017 bar

`ADR-017` requires a witness combining an **identified printed edition** with **redistribution
rights**. Rights are clean (§6). The **recension is not established.**

Griffith 1895 preface, verified verbatim: *"In 1848 Professor Benfey of Göttingen brought out an
excellent edition of the **Rāṇāyanīya recension**… and Pandit Satyavrata Sāmaśramī of Calcutta
published in 1874-78 in the Bibliotheca Indica a meritorious edition of the Sanhita **according to
the same recension**."*

So a primary source assigns Sāmaśramī to **Rāṇāyanīya**. A stobha-spelling discriminator run
against the scan OCR points the other way (`हाउ` 7 hits / `हावु` 0), but it derives from a
wiki-tier source and 1874 Devanagari OCR is poor — suggestive, not probative. A division-scheme
discriminator is **void**: the two published accounts contradict each other and the edition carries
both systems simultaneously.

**An identified edition of uncertain recension does not satisfy "identified printed edition of the
Kauthuma saṃhitā."** The blocker is now sharp and cheap: obtain vol 1 pp. 1–9 (title page and the
editor own prefatory statement) from archive.org `in.ernet.dli.2015.487112` and have a specialist
read the recension off it. That is one page-range fetch plus a qualified reader — a named external
dependency, not a research campaign.

> **A correction to this session own reasoning, recorded so it is not repeated.** The coordinator
> hypothesised that the repository Benfey-equals-Rāṇāyanīya attribution might be defective, since
> Benfey is sometimes described as Kauthuma. Checking the primary source refuted the hypothesis.
> **The repository reported Griffith accurately and that record must not be "corrected" into
> error.**

---

## 4. Divergences

| # | Divergence | Severity | Threatens identity, or display only? |
|---|---|---|---|
| **D1** | **Arcika arity: 4 (Pandey/GRETIL/TITUS) vs 2 (Wikisource, Griffith, Wikipedia, Vedic Heritage, Vedapeetha, B. R. Sharma HOS) vs 3 (Caland/Kashikar).** All witnesses hold the *same four blocks in the same order*; they disagree on how to bracket them, and therefore on what number slot 1 takes. | **CRITICAL** | **Threatens identity.** Slot 1 is the top of the key, so it mis-addresses 1,280 of 1,875 verses. |
| **D2** | **The "exactly four arcikas" claim has ZERO independent corroboration.** The repository credits TITUS — but TITUS is Pandey lineage, which the same documents concede elsewhere. Every non-Pandey witness contradicts it. | **CRITICAL** | **Threatens identity**, and it is the same overstatement pattern the repository was already burned by, one layer deeper. |
| **D3** | **The Wikisource address is not a positional tuple.** Numbers count siblings within the parent; the level *name* is carried lexically in the title. Slot 3 means prapāṭhaka under `1.1.x`, daśati under `1.2.x`, ardha under `2.x.y` — three meanings in one witness. | HIGH | **Threatens identity** if a parser reads Wikisource addresses positionally. `parse_at_address` correctly refuses to. |
| **D4** | **Fourth-level NAME is contested:** `daśati` (Pandey lineage) vs `sūkta` (Wikisource body — `दशति` × 0, `सूक्त` on 9 of 22 pages; Vedapeetha: "instead of Daśati-s, there are Sūkta-s") vs `khaṇḍa` (VHP-lineage secondary literature) vs unnamed (Caland/Kashikar, Griffith). In the **Pūrvārcika** all witnesses say daśati/decade. | HIGH | Mostly **vocabulary**, but it qualifies the standing claim that `Khaṇḍa` "remains wrong": `Khaṇḍa` is an attested *alternative name* for the **Uttarārcika** 4th level, wrong only for the Pūrvārcika. See §7 — this is the thinnest evidence in the report. |
| **D5** | **GRETIL splits one daśati across two ardha values.** At Pūrvārcika prapāṭhaka 3, daśati 6 verse 1 is labelled ardha 1 (`1 3 1 0601a/c`) and verses 2–10 ardha 2 (`1 3 2 0602…0610`). Unique in the file. Collapsing ardha yields a clean single daśati (RN 243–252, n=10). | HIGH | **Threatens identity — but only because ardha is in the key.** Same defect family as the known `0101a` pāda mislabel. |
| **D6** | **The Griffith DECADE claim is cited to the wrong artifact.** The pinned `data/raw/wikisource_griffith_sv/…7fe81ea….php` contains `Decad`/`ecade` **× 0** — it is a preface plus a table of red links. The DECADE evidence actually comes from the unsnapshotted `sacred-texts.com/hin/sv.htm`. | MODERATE | **Provenance defect, not a structural one.** The claim is TRUE — re-verified from the Wayback capture the repository itself cites — but it is attributed to an artifact that does not contain it. |
| **D7** | **`source_artifacts.yaml` states Griffith Part II has SIX Books where Kauthuma has NINE prapāṭhakas.** Measured: Griffith has **15 BOOK headings = 6 (Part I) + 9 (Part Second)**. Part *Second* has NINE, matching Kauthuma exactly. The same record `citation_system` field says `BOOK I-IX`, contradicting its own `notes`. | MODERATE | **Threatens a conclusion, not the identity.** This wrong count is the sole *structural* corroboration offered for the recension-mismatch verdict. That verdict still stands on the Griffith preface, but this supporting number is wrong and is withdrawn. |
| **D8** | **Griffith omits the Āraṇyārcika and Mahānāmnya entirely.** Part I = 59 decades ≈ 585 verses. | LOW | **Coverage.** Reduces Griffith reach; contradicts no one. |
| **D9** | **Secondary sources disagree whether daśati is numbered within the ardha or within the prapāṭhaka.** GRETIL numbers 1–10 across the prapāṭhaka (measured). One Vedapeetha passage says "Each Ardha has 10 Dashati-s", arithmetically impossible against 59 total. | LOW–MODERATE | **Citation-format ambiguity** — exactly what makes an unqualified 5-tuple risky in the wild. |
| **D10** | **Wikisource verse markup is inconsistent**: some pages use `॥` (U+0965), others `।।` (two U+0964). | LOW | **Transcription quality**, not structure. |
| **D11** | **No independent witness uses a normalised numeric citation form at all.** Caland/Kashikar cite by edition and page. No attested standard `SV 1.1.1.1` / `SV I.1.1.1` usage was found in any primary or scholarly source reached. | MODERATE | Bears on how a frozen key should be *presented*, not on whether it is stable. |

---

## 5. Collision search result: **YES — two collisions found, one airtight**

The brief asked whether any known Kauthuma witness assigns a **different passage to the same
coordinates**. It does.

### Collision A — hard, verified against live artifacts on both sides

Coordinate tuple **`(1, 1, 2, 6)`**:

| Witness | Reading | Running verses |
|---|---|---|
| **Wikisource** `1.1.2.6` (revid 313271) | Pūrvārcika / chandas / **prapāṭhaka 2** / daśati 6 | **145–154** (10 verses) |
| **GRETIL** label `1 1 2 06` | arcika 1 / **prapāṭhaka 1** / **ardha 2** / daśati 6 | **55–62** (8 verses) |

**Disjoint. Zero overlap.** The two schemes align in the `1.1.1.x` branch only by the coincidence
that chandas = 1, prapāṭhaka = 1 and ardha = 1 are all `1`. The moment the Wikisource slot-2
prapāṭhaka exceeds 1, the tuples decouple.

### Collision B — the top slot, largest blast radius

Coordinate **slot 1, value `2`**:

| Witness group | Reading | Running verses |
|---|---|---|
| GRETIL / TITUS | **Āraṇyārcika** | 586–640 (55 verses) |
| Wikisource / Griffith / Wikipedia / Vedic Heritage / Vedapeetha / B. R. Sharma HOS | **Uttarārcika** | 651–1875 (**1,225 verses**) |

Disjoint. And at 3-number granularity: Wikisource `1.2.1` = RN 586–594; GRETIL `1 2 1` = RN
97–144. **Same literal address string, disjoint passages.**

### What was searched

The complete GRETIL label lattice (3,299 label lines → 36 arcika/prapāṭhaka/ardha containers, 250
daśati cells, per-cell running-number ranges); the complete Wikisource page tree (840 titles,
live-enumerated, decomposed by path depth and dotted-address arity); all 22 Wikisource Uttarārcika
ardha pages fetched and range-compared; 4 Wikisource daśati pages range-compared; the full
112-label Griffith Part/Book/Chapter/Decade sequence; and 6 independent scholarly or institutional
structural descriptions.

---

## 6. The Ardha verdict — asked as the weakest link, answered as the strongest

**Ardha is a genuine, stable Kauthuma structural level — not an editorial convenience.** It is the
**best**-corroborated of the four container levels and it survived the hardest available test.

- **Independent lexical attestation.** Wikisource names it in its own page titles (`…अर्द्धः`, 22
  pages) with no Pandey involvement. TITUS calls it `Ardha-Prapāṭhaka`; Vedapeetha uses the same
  compound. Griffith renders it `CHAPTER`. **And the Sāmaśramī print names it in its colophons**
  (`इति चतुर्थस्यार्धः प्रपाठकः`), so it is printed, not inferred.
- **Independent cardinality fingerprint.** `[2,2,2,2,2,3,3,3,3]` for the Uttarārcika, from **five
  witnesses across three lineages**, two of which independently single out "the last four" as
  having three.
- **Independent boundary agreement to the verse.** **21/21** Uttarārcika ardha closing running
  numbers identical between GRETIL and Wikisource.
- **It is load-bearing in the Uttarārcika** — the fourth level resets inside each ardha, so ardha
  is *not* derivable there:

```text
A4 P1: ardhas=[1, 2]    dasati overlap=[1..22]
A4 P6: ardhas=[1, 2, 3] dasati overlap=[1..11]
A1 P1: ardhas=[1, 2]    dasati overlap=NONE (continuous)
```

- **It is redundant in the Pūrvārcika** — daśati numbers 1–10 continuously across the prapāṭhaka,
  so `ardha = 1 if dasati <= 5 else 2`, derivable with zero information loss.

> **The Wikisource omission of ardha in the Pūrvārcika is therefore an ECONOMY, not a denial.** It
> drops exactly the copy that is redundant and keeps exactly the copy that is not. That is
> independent structural **confirmation**, not divergence — and it corrects a reading, raised
> during this session, that treated the omission as contested evidence.

**Two sharp caveats for the key, both real.**

1. A level named "half" **takes the value 3** in Uttarārcika prapāṭhakas 6–9. The name is
   traditional; the arity is not two.
2. Putting ardha in the identity key is what **creates** the D5 defect. Ardha is a real level of
   the *text*; it is a **liability in the Pūrvārcika branch of the key** and a **necessity in the
   Uttarārcika branch**.

---

## 7. Direct answer, and honest uncertainty

**Does the addressing depend on the Wikisource edition? No.** Wikisource does not use the 5-tuple
at all — it uses a path-relative, variable-arity, lexically-typed address with only two top-level
arcikas. Every level the project declared is nonetheless attested in the Wikisource own
vocabulary, and its boundaries match GRETIL to the verse in 21/21 Uttarārcika ardhas, 4/4 tested
daśatis and 11/12 Pūrvārcika cells. Griffith 1895 — a century pre-Pandey, in a *different
recension* — reproduces the same lattice with the identical `[2,2,2,2,2,3,3,3,3]` fingerprint. The
Sāmaśramī print names all five levels in its colophons. A scheme reproduced by an 1895 Rāṇāyanīya
translator, an 1874 Bibliotheca Indica print, a modern community transcription, a Government of
India portal, a Sāmavedic tradition site and Caland/Kashikar is **not one edition invention**.

**The scheme that IS edition-specific is the one the project adopted.**
`hierarchy: [Arcika, Prapathaka, Ardha, Dasati, Verse]` with fixed 5-slot arity, `0` for absence,
and **four flat sibling arcikas** is the *Pandey* encoding.
`ADDRESSING_DEPENDS_ON_UNIDENTIFIED_WIKISOURCE_EDITION` was the wrong worry. The live risk is
**`ARITY_DEPENDS_ON_THE_PANDEY_E-TEXT`**.

### Stated uncertainty

- **D4 (`khaṇḍa` / `sūkta` naming) is the thinnest evidence here.** The `sūkta` and `khaṇḍa`
  glosses come from web-search summaries that a direct fetch of those pages did **not** reproduce
  verbatim. **Treat D4 as needing a verbatim re-check before any documentation edit.** The
  *direction* is solid — Wikisource never says daśati in the Uttarārcika, a zero-count measured
  across all 22 pages.
- **The TITUS 8-level string is unconfirmed.** `svkx.htm` yielded levels 1–3 and "Four Arcikas …
  1, 2, 3, 4" but not the full 8-level quotation the project records, and not the
  `Copyright (C) 1998, 1999 Anshuman Pandey` line (the frame carries a 2013 TITUS copyright
  instead). Presumably on a deeper text frame, deliberately not opened. Changes nothing — TITUS is
  citation-authority-only and Pandey-lineage either way.
- **The fourth-level per-ardha cardinality in the Uttarārcika is NOT independently confirmed.**
  Only its *existence* (numbered sub-groups inside each ardha) and its ~3-verse size are. The
  failure is instrumental: the Wikisource first group numeral shares a line with an opening tag,
  so a line-anchored regex undercounts by exactly 1; applying `+1` produces exact matches for 11
  of 22 ardhas, and the remaining 11 use uncharacterised markup.
- **Griffith is a Rāṇāyanīya witness, not a Kauthuma one** — re-verified verbatim from the pinned
  artifact. His agreement is a *sister recension* addressing convention. That is arguably
  **stronger** evidence of scheme stability than a same-recension witness would be, but it must
  never be counted as a Kauthuma textual witness. The project states this correctly.
- **Griffith Part I Book III Chapter I is missing `DECADE III`** in the sacred-texts
  transcription; whether that is Griffith, the transcription, or HTML stripping is undetermined.
  The GRETIL *sole* ardha defect also lands at prapāṭhaka 3 / ardha 1, in the opposite direction.
  The coincidence is flagged and nothing is claimed from it.

**Corroboration counted exactly, so it cannot be inflated again:**

- **Level list and container boundaries** — 1 source lineage (Pandey = ONE witness) + 2
  independent textual lineages + 1 identified printed edition + 4 independent secondary
  descriptions.
- **"Exactly four arcikas"** — **1 witness (Pandey), 0 independent corroborations, 6 independent
  contradictions.**
