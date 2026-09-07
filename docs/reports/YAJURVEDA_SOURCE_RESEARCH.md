# Śukla Yajurveda source research — Vājasaneyi Saṃhitā, Mādhyandina

**Work:** `VG:WORK:YV:VSM` · **Recension required:** Mādhyandina · **Researched:** 2026-09-07
**Machine-readable companion:** `data/source_registry/yajurveda_sources.yaml`

> **Method note carried forward.** Two false negatives in this survey (DCS, and the Sanskrit
> Library's retrievable endpoint) came from ASCII keyword matching against diacritic-bearing
> Sanskrit names — `saṃhitā` uses U+1E43 and does not match a literal `samhita`. Any future
> corpus discovery over Sanskrit filenames must use Unicode-normalised or
> transliteration-agnostic matching. Both claims were corrected before this report was final.

---

## 0. The finding that reshapes the phase

**GRETIL — the source the whole Rigveda pipeline is built on — has no Vājasaneyi Saṃhitā
at all.** Not in Mādhyandina, not in Kāṇva. Its index lists the title and then nothing:

```html
<h5 id="orge9aa8e6">White Yajurveda</h5>
<li>Vajasaneyi-Samhita (input by &#x2026;) <span id="VajSam"></span>
<ul class="org-ul">
<li>Restricted download / proprietary format from <a href="http://titus.uni-frankfurt.de/indexe.htm">TITUS</a></li>
<li>Converted file(s) not available at present</li>
</ul></li>
```

Verified rather than assumed: all 6,327 anchors of `gretil.html` were grepped (zero
matches for `vajas`/`vAjas`/`yaju`/`sukla`), and eight plausible filenames under
`corpustei/` and `1_veda/1_sam/` were probed directly — all HTTP 404. Directory listings
return 403, so `gretil.html` is the only enumeration. The only YV *saṃhitā* GRETIL holds
is the **Maitrāyaṇī** — which is Krishna YV, the wrong recension for this work.

So the Rigveda ingestion pattern does not generalise here, and a different source stack
was required.

---

## 1. Candidates investigated

| Candidate | Recension | Format | Accents | Complete | Rights | Verdict |
|---|---|---|---|---|---|---|
| **Sanskrit Wikisource** `शुक्लयजुर्वेदः` | **Mādhyandina**, declared in-artifact | MediaWiki wikitext via JSON API | **Yes** (U+0951/0952 + Vedic Extensions) | **40/40 adhyāyas, 1975/1975 mantras** | **CC BY-SA 4.0** | **SELECTED** |
| TITUS `yvw/vs/` | **Mādhyandina**, declared | Structured HTML, per-pāda anchors | Yes | 40 adhyāyas but **VS 2.32 missing** → 1974 | **All rights reserved** | REJECTED (rights) |
| Sanskrit Library TEI | Mādhyandina (from TITUS) | **TEI XML** — best format | Yes | Catalogued only | CC BY-NC-SA 3.0 | DEFERRED (no retrieval URL) |
| Vedic Heritage Portal | Mādhyandina | HTML + Bloomfield concordance | Yes | 40 adhyāyas; adh 23 = 64 | **Reproduction prohibited** | REFERENCE_ONLY |
| Griffith 1899 (`textswhiteyajur01grifgoog`) | Mādhyandina (by apparatus) | **OCR only** | n/a (English) | Complete | PUBLIC_DOMAIN (`NOT_IN_COPYRIGHT`, orig. E.J. Lazarus 1899) | RESOLVED but not ingested |
| Weber 1852 (archive.org) | Both M and K | OCR of scan | print only | Complete | PUBLIC_DOMAIN | REFERENCE_ONLY |
| sanskritdocuments.org | Mādhyandina (partial) | ITRANS/HTML | **highest fidelity** | ~2% coverage | No CC licence | Test fixture only |
| **DCS** (Digital Corpus of Sanskrit) | **Mādhyandina**, declared in directory name | **CoNLL-U**, UD morphology, `Unsandhied` padapāṭha forms, `IsMantra` flags | **None** | **15 of 40 adhyāyas** (VSM 1–15) | **CC BY 4.0** — the only clean licence in the survey | PARTIAL — see below |
| Sanskrit Library JSON endpoint | Mādhyandina (from TITUS) | JSON, SLP1 ASCII accents (`/` udātta ×28,770, `\` svarita ×602) | Yes, as ASCII | 1,974 — **inherits TITUS's VS 2.32 omission**; no adhyāya/mantra numbers served | CC BY-NC-SA over an all-rights-reserved upstream | REJECTED (invalid licence chain, undocumented) |
| `bhavykhatri/DharmicData` (GitHub) | Mādhyandina | JSON, accented Devanagari | Yes | 40 adhyāyas, 2 mantras short (adh 13, 15) | **ODbL-1.0 — invalid**; README names Vedic Heritage (all-rights-reserved) as its source | REJECTED (licence not the uploader's to grant) |
| VedaWeb | — | JSON API | — | **No Yajurveda saṃhitā** | no licence stated | OUT OF SCOPE |
| SARIT · Vedavid · Muktabodha | — | — | — | **No VS** | — | Negative |

Verbatim rights text for every row lives in `data/source_registry/yajurveda_sources.yaml`
under each candidate's `license_evidence`. Two quotations matter most:

**TITUS**, on every page — the reason the technically best source is unusable:
> Copyright TITUS Project, Frankfurt a/M, 2.11.2013. No parts of this document may be
> republished in any form without prior permission by the copyright holder.

**Sanskrit Wikisource**, from the wiki's own API (`meta=siteinfo&siprop=rightsinfo`),
not from a scraped footer:
> `{"url": "https://creativecommons.org/licenses/by-sa/4.0/deed.sa", "text": "Creative Commons Attribution-Share Alike 4.0"}`

The adhyāya pages carry **no licence statement of their own** — checked, and recorded as
an absence. The site licence governs because the artifact genuinely *is* user-contributed
MediaWiki content under the Wikimedia Terms of Use, not by analogy with a sibling file.

---

## 2. Selected source stack

* **Leading Sanskrit — accented:** `WIKISOURCE_SA.YV.VSM.ACCENTED`, registered
  `EXTRACTED_FROM_CONTAINER`. **This work has no `PRIMARY_TEXT` layer.** The 1929 edition
  does use the standard mūla–bhāṣya layout (ordinal header → full accented mūla with its own
  number → bhāṣya), which I proved and Agent E accepted — but my parser infers that boundary
  from accent-presence rather than reading the header, and the layer contains one
  variant-selection judgement (VSM 16.37). So the role tracks the implementation, not the
  source's potential. The faithful layer is incomplete (1,836/1,975) and the complete layer
  is extraction-derived, so no layer is both. See `docs/pilots/YAJURVEDA_PILOT.md`. Fully accented Devanagari
  quoted inside the Uvaṭa–Mahīdhara commentary block, each mantra closed by its own number
  in Devanagari digits between daṇḍas.
* **Parallel Sanskrit — unaccented:** `WIKISOURCE_SA.YV.VSM.UNACCENTED`. The saṃhitā block,
  mantras labelled `<adhyāya>.<mantra>`.
* **Traditional metadata:** `शुक्लयजुर्वेदः/ऋषिसूची` (per-mantra ṛṣi index, parsed) and
  `शुक्लयजुर्वेदः/सर्वानुक्रमणी` (Sarvānukramaṇa-sūtra, carried as evidence, **not** machine-resolved).
* **English translation:** none ingested. Named blocker, §7.
* **Hindi translation:** none available under a usable licence. Named blocker, §7.

The accented layer is primary because it preserves tone marks *and* is materially more
complete. This is a build decision recorded in `data/builds/yajurveda_pilot_v1.yaml`, not
a parser constant: passage identity derives from the citation hierarchy alone, so swapping
the two cannot move a single mantra UUID.

### The edition is identified

The selected source is **not** an anonymous community text. Its preface page reproduces the
printed title page verbatim (snapshot
`data/raw/wikisource_sa/2026-09-07/cb13ec2ee19ba027…php`):

> पणशीकरोपाह्वविद्वद्वरलक्ष्मणशर्मतनुजनुषा वासुदेवशर्मणा विद्वत्साहाय्येन संशोधिता । (द्वितीयावृत्तिः।)
> सा चेयं मुम्बय्यां पाण्डुरङ्ग जावजीश्रेष्ठिना स्वीये निर्णयसागराख्यमुद्रणयन्त्रालये … प्राकाश्यं नीता ।
> **शाकः १८५०, सनः १९२९.**

That is: *Vājasaneyi-Mādhyandina Śukla-Yajurveda-Saṃhitā*, with Uvaṭa's *Mantrabhāṣya* and
Mahīdhara's *Vedadīpa*, ed. **Vāsudeva Śarma Paṇaśīkara**, 2nd edn, Pāṇḍuraṅga Jāvajī /
**Nirṇaya Sāgara Press, Bombay, Śaka 1850 = CE 1929**. The 1929 print is out of copyright
by age; the transcription of it is CC BY-SA 4.0.

Authority tier stays `COMMUNITY_TRANSCRIPTION` because the *transcription* is
community-made. The residual risk is transcription fidelity, not unknown provenance.

---

## 3. Recension verification — how Mādhyandina was proved

Recension was established **from the artifacts themselves**, never from a catalogue label.
This mattered: most audio and several text sources labelled "Shukla Yajurveda" are in fact
**Kāṇva**.

1. **DECISIVE** — the commentary block of adhyāya 1 opens:
   `श्रीमद्वाजसनेयिमाध्यन्दिन शुक्लयजुर्वेदसंहिता।` — "Śrīmad-Vājasaneyi-**Mādhyandina**
   Śukla-Yajurveda-Saṃhitā".
2. **CORROBORATING** — the Sarvānukramaṇī page, line 2: `माध्यन्दिनीये वाजसनेयके यजुर्…`
   — "in the **Mādhyandinīya** Vājasaneyaka Yajur[veda]".
3. **CORROBORATING** — every adhyāya-40 mantra label carries a *Kāṇva* cross-reference,
   e.g. `40.1 {ईशावा.उप. काण्व1}`. Giving the Kāṇva equivalent only makes sense if the base
   text is not Kāṇva. Adhyāya 40 has exactly **17** mantras, the Mādhyandina figure.
4. **INDEPENDENT** — TITUS, consulted as an external reference only, states
   `Vājasaneyi-Saṃhitā / Mādhyandina-Recension`, and its adhyāya 1 ends at verse 31 and
   adhyāya 40 at verse 17 — both matching the computed counts.

Griffith's Mādhyandina base is **corroborated, not decisive**: his preface says only that
his base edition contained both recensions. The evidence is his Book XL having 17 verses in
Mādhyandina order. Recorded that way rather than as an authorial claim.

---

## 4. Structure and COMPUTED counts

Confirmed hierarchy: **Adhyāya → Mantra**, two levels. There is no sūkta level and none
was invented. Counts below are **computed by the adapter from all 40 snapshotted pages**,
never quoted from memory.

**40 adhyāyas · 1975 mantras.**

Per adhyāya (accented layer max / unaccented layer max):

| Adh | acc | sam | Adh | acc | sam | Adh | acc | sam | Adh | acc | sam |
|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
|1|31|31|11|83|83|21|61|61|31|22|22|
|2|34|34|12|117|117|22|34|34|32|16|16|
|3|63|**43**|13|58|58|23|**64**|65|33|97|97|
|4|37|37|14|31|31|24|40|40|34|58|58|
|5|43|43|15|65|65|25|47|47|35|22|22|
|6|**36**|37|16|66|66|26|26|26|36|24|24|
|7|48|**15**|17|99|99|27|45|45|37|21|21|
|8|63|63|18|77|77|28|46|46|38|28|28|
|9|40|40|19|95|**17**|29|60|60|39|13|13|
|10|34|34|20|90|90|30|22|22|40|17|17|

Σ accented maxima = **1973** · Σ unaccented maxima = **1844** · **union = 1975, no gaps**.

### Reconciliation, reported as data

* The two layers **disagree**, and neither alone is complete. The unaccented block is badly
  truncated in adhyāyas **3** (43/63), **7** (15/48) and **19** (17/95), with single-mantra
  gaps in 4, 10, 12, 13, 18, 39. The accented layer is short by one in **6** and **23**.
  Their union is exactly 1975. The layers were **not merged** into one text; only the
  structural inventory is unioned. Per ADR-010 this divergence is data.
* **TITUS yields 1974** — VS 2.32 is absent there but present on Wikisource.
* **Vedic Heritage yields 1974** — its adhyāya 23 has 64, against 65 on Wikisource, TITUS
  and Griffith.
* No source was edited to agree with another.
* **Unresolved and flagged:** one secondary source cites 1951 *kaṇḍikās* in 303 *anuvākas*.
  That is an anuvāka-based counting system, not a contradiction of the mantra count.

### Alternate citation systems recorded

Adhyāya 40's braced annotations are captured as non-canonical `Citation` records with
system `SOURCE_CROSS_REFERENCE` (17 of them in the pilot) — the Īśāvāsya Upaniṣad numbering
in the **Kāṇva** recension. Ritual-section labels from the root TOC (e.g. adhyāya 16 =
*Rudra*, 31 = *Puruṣa/Viṣṇu sūkta*, 40 = *Īśāvāsya Upaniṣad*) are viniyoga-type metadata.
Note a divergence recorded rather than resolved: the TOC calls adhyāya 31
*puruṣasūktādhyāyaḥ* while the page itself heads it *viṣṇu sūktam*.

---

## 5. Traditional metadata

**The premise that Yajurveda records viniyoga *instead of* ṛṣi/devatā/chandas is false.**
Śukla YV has its own *Sarvānukramaṇa-sūtra* ascribed to Kātyāyana — a **different work**
from the Rigvedic Sarvānukramaṇī (the name is a school attribution; the same "Kātyāyana"
is credited with the Śrautasūtra, the Prātiśākhya and the Vārttikas — do not merge these).
Its opening sūtra declares its own fields *and its own limits*:

> …**ṛṣi-devata-chandāṃsy anukramiṣyāmo**, **yajuṣāṃ aniyatākṣaratvād ekeṣāṃ chando na
> vidyate**… devatā … *anaḥ-śākhā-ukhā-śamyā-…-udūkhalādayaś ca pratimābhūtāḥ*…

Three consequences that forbid carrying Rigvedic practice across:

1. **`chandas` is legitimately ASSERTED-ABSENT for many mantras** — "because the yajus have
   no fixed syllable count, for some of them no metre exists." Absent ≠ unknown. Where a
   metre *is* given for a yajus it follows **Piṅgala's syllable-count** scheme, not RV metrics.
2. **The YV `devatā` co-domain includes ritual implements** — cart, branch, pot, yoke-pin,
   potsherd, mortar — as *pratimābhūta*, "standing as representations". A shared RV/YV
   devatā enum would be a modelling error.
3. **`ṛṣi` is ritual-block-scoped**, with *vivasvān* stated as the default for the whole
   saṃhitā and refined *pratikarma-vibhāgena brāhmaṇānusāreṇa* — by ritual act, following
   the Brāhmaṇa. So `ṛṣi` needs a scope (corpus default / ritual block / mantra).

**viniyoga is explicitly deferred to the Kātyāyana Śrautasūtra** (`viniyogaḥ kalpakāroktaḥ`)
and is not in the anukramaṇī at all.

The tradition also keeps its own register of non-assignments, titled
*anādiṣṭa-devatādayaḥ* — "deities etc. **not specified**". The pipeline must reproduce
those gaps, not fill them.

### What is machine-readable, and the safe resolution method

**Newly found, and better than the OCR route:** both the **ṛṣi index** and the
**Sarvānukramaṇa-sūtra** exist as transcribed text on Sanskrit Wikisource under
**CC BY-SA 4.0**. Secondary literature and a parallel search both concluded no keyed
e-text of the VS anukramaṇī exists anywhere; that is now false.

* **`/ऋषिसūची` — parsed and ingested.** 419 lines of `<ṛṣi> <adhyāya>.<ranges>`, e.g.
  `अत्रिः ८.१५–२२, २४-३० ।`. Yields **2,106 per-mantra ṛṣi assertions, 248 distinct ṛṣis,
  covering 39 of 40 adhyāyas**. Every assertion carries the source line and records whether
  the source stated it as a single mantra or a range, so a range-derived claim can never be
  mistaken for a per-mantra statement. **9 lines fail to parse** and are reported, not
  guessed — see §6.
* **`/सर्वानुक्रमणी` — snapshotted as evidence, deliberately NOT machine-resolved.** It is
  continuous sūtra prose grouped by anuvāka, with *liṅgokta* ("deity stated by the
  characteristic mark") standing in for many deities. Resolving it to per-mantra claims
  requires expert philological reading. **No LLM was used and none may be.**
* **`devatā` and `chandas` are NOT asserted for any mantra in this pilot.** Deliberate. The
  only correct source is the Sarvānukramaṇī, which is not mechanically resolvable, and
  inferring either field from mantra wording or RV parallels would be systematically wrong
  in hard-to-detect ways.
* **A Tier-1 route to viniyoga exists with zero inference:** GRETIL's keyed Bloomfield
  *Vedic Concordance* has 8,475 entries citing `VS.`, of which **3,861 also cite Śatapatha
  Brāhmaṇa** and **1,148 also cite Kātyāyana Śrautasūtra**. That is a verbatim
  mantra → ritual-act mapping requiring no matching or judgement. Not built in this pilot;
  recommended as the next metadata increment. Note GRETIL's own statement on that file is
  restrictive: *"THIS GRETIL TEXT FILE IS FOR REFERENCE PURPOSES ONLY! COPYRIGHT AND TERMS
  OF USAGE AS FOR SOURCE FILE."*
* **Schema decisions needed before any devatā/chandas ingest** (requests for Agent A):
  `chandas` nullable **with a reason code** (`asserted_absent` / `anādiṣṭa` vs `unknown`);
  a YV `devatā` union type (deity | implement | substance | ritual act) separate from the RV
  deity set; `ṛṣi` scope + provenance flag.

---

## 6. Audio inventory — a decisive negative

**No source offers per-mantra-aligned Śukla-Mādhyandina audio under a licence permitting
local mirroring.** The three properties — Mādhyandina, per-mantra alignment, clear rights —
never co-occur. Nothing was downloaded; existence was checked by HEAD requests only. Full
inventory forwarded to Agent E, which owns the consolidated cross-Veda audio table.

| Item | Recension | Scope | Rights | Mirror? |
|---|---|---|---|---|
| `vedicheritage.gov.in/…/SYMS_CHAP_01–40.mp3` | **Mādhyandina** | all 40 adhyāyas | PERMISSION_REQUIRED | **No** — and **all 40 URLs 404**, broken since ≥ 2025-04 |
| `mAdhyandina-shAkhA-vedamu` (archive.org) | **Mādhyandina** | **adhyāyas 1–27 of 40**, five monolithic files | **No rights metadata at all** | No — REFERENCE_ONLY |
| `suklayajurveda_202107` (archive.org) | **KĀṆVA** (proved: 37 h 20 m matches the Veda Prasar Samiti Kāṇva product exactly) | complete, 54 files | Public Domain Mark 1.0 | Yes — but **wrong recension** |
| `shukla-yajur-veda_recitation` | Kāṇva (same master, re-segmented) | complete | no licence | No |
| IGNCA workshop vols (`dni.ncaa.IGNCA-AC_1032/1040`) | **UNVERIFIED** | 2 cassette sides each | CC BY-NC 4.0 *applied by a third party*, conflicting with IGNCA policy | Conflicted |
| Celextel / JioSaavn / YouTube | Kāṇva or unverified | — | All rights reserved / ToS | No — EXTERNAL_REFERENCE_ONLY |

Notes carried as `UNVERIFIED` rather than assumed: **pāṭha type**. A ~3× runtime anomaly
(37 h vs 10.2 h for the same text) across the circulating sets means samhitā-pāṭha cannot be
assumed. **No reciter is credited anywhere** on the government portal, so even a permission
request has an unresolvable consent chain.

Per-mantra Yajurveda audio *does* exist on the Vedic Heritage portal — but only for
**Krishna** YV ghana-pāṭha, and prohibited. **Vedavani**, the only time-aligned Vedic ASR
corpus (54 h), covers **Rigveda and Atharvaveda only**.

**Recommendation:** report the dead Mādhyandina links to IGNCA. If restored *under
permission*, that is the ideal source. Otherwise per-mantra Mādhyandina audio would have to
be commissioned from a pāṭhaśālā with an explicit licence.

---

## 7. Named blockers — not worked around

1. **No lawful *traditional* padapāṭha covering the whole work.** The only scholarly
   padapāṭha (Yudhiṣṭhira Mīmāṃsaka) is a 1996 edition in copyright in India until **2081**;
   an archive.org duplicate carries an uploader-asserted CC0 the uploader had no standing to
   grant. Wikisource has padapāṭha only inside Dayānanda's bhāṣya, ~290 of 1975 mantras.
   **Partial mitigation, found late and verified:** **DCS** holds `Vājasaneyisaṃhitā
   (Mādhyandina)` (text_id 523) as CoNLL-U with Universal-Dependencies morphology and
   `Unsandhied` word forms plus `IsMantra` flags, licensed **CC BY 4.0** — verbatim from
   `dcs/data/conllu/readme.md`: *"The data in this directory are licensed under the Creative
   Commons BY 4.0 (CC BY 4.0) license."* But it covers only **adhyāyas 1–15 of 40**, carries
   **zero accents**, and its `Unsandhied` forms are a *modern morphological analysis*, not the
   traditional padapāṭha — a different kind of object that must not be labelled as one.
   Use `http://www.sanskrit-linguistics.org/dcs/`; `dcs.uni-heidelberg.de` no longer resolves.
   **Consequence: a Yajurveda lexical layer is possible for adhyāyas 1–15 only, from a
   CC BY 4.0 morphological source, and there is no traditional padapāṭha for any of the work.**
2. **No structured English translation.** Griffith 1899 is PD but OCR-only. Preferred item
   is **`textswhiteyajur01grifgoog`** — `date: 1899`, `publisher: "E.J. Lazarus and co.,
   1899"` (the original Benares publisher), `possible-copyright-status: NOT_IN_COPYRIGHT`,
   DjVuTXT 867,776 bytes. *Revised from my first resolution* after Agent E correctly
   objected that `textswhiteyajur00grifgoog` is a scan of the **1987 Munshiram Manoharlal
   reprint** (`date: 1987`), and a modern reprint can carry its own typographic rights.
   Note E's own alternative, `in.ernet.dli.2015.215626`, is the right edition year but
   carries **no rights field at all**, so it is PD by age rather than by assertion;
   `…01grifgoog` satisfies both constraints. All three are recorded.
   en.wikisource has no transcription and its `Yajurveda` title **redirects to Keith's
   Taittirīya — Krishna YV, a recension trap**; sacred-texts.com is Cloudflare-blocked
   (403). No translation records were created.
3. **No usable Hindi translation.** Most post-1930 Hindi renderings remain copyright-live in
   India; Sātavaḷekar is PD in the US but not in India until 2029. None exists as structured
   per-mantra data.
4. **The best-format source is unpublished.** Sanskrit Library's TEI edition is catalogued
   with no retrieval URL and would impose CC BY-NC-SA.
5. **Devanagari comparison folding was absent** from `normalize/unicode.py`. **Now fixed by
   Agent F** in response to this finding — see §8 for the before/after numbers.
6. **CC BY-SA is share-alike.** Any distributed artifact embedding this text inherits the
   obligation. Agent E's decision, not mine.
7. **Every "open" licence claimed on a VS artifact except Wikisource's and DCS's is
   downstream-asserted and upstream-contradicted.** DharmicData's ODbL sits over an IGNCA
   scrape; Sanskrit Library's CC BY-NC-SA sits over TITUS's "no parts may be republished";
   an eGangotri CC0 scanning stamp sits over Sātavaḷekar's copyright (live in India to
   **2029**); archive.org carries a 2007 Chowkhamba edition tagged CC0. Treat a licence tag
   on a re-upload as evidence of nothing without an upstream chain.

---

## 8. Cross-source comparison result

135 mantras compared across the two text layers using the existing `compare/text.py` and
the existing `TextComparisonCategory` enum, unmodified. Distribution:

| Category | n (after Agent F's fold) | n (as first measured) |
|---|--:|--:|
| `UNCLASSIFIED` | **116** | 132 |
| `SANDHI_OR_SEGMENTATION` | **13** | 2 |
| `ACCENT_ONLY` | **6** | 1 |

**The gap I reported here has since been closed, and these are the post-fix numbers.**
Original diagnosis, kept because it is the evidence that drove the fix:
`normalize/unicode.py::TRANSCRIPTION_EQUIVALENCES` folded **only Latin IAST/ISO-15919**
variants, with **no Devanagari-side folding at all**, so two mechanical mismatches made
every Devanagari-vs-Devanagari comparison fall through to `UNCLASSIFIED`:

* the two layers spell one nasal incompatibly — **U+A8F3** (77× in the pilot) in the
  unaccented layer versus **U+1CEA + U+0902 + U+1CED** in the accented layer. U+1CED is
  stripped as an accent but **U+1CEA is category Lo — a letter** — so it survived and could
  never match U+A8F3;
* the accented layer types **visarga as ASCII colon U+003A** (124× in the pilot subset,
  ~1,538× across the whole work). `:` is in `SEPARATOR_MARKS`, so it became a space while a
  real `ः` survived.

Agent F, who owns `normalize/`, added Devanagari nasal and visarga folds onto the same
sentinels the Latin rules already use — so a Devanagari and a Latin reading of one nasal are
now comparable, which matters for Samaveda and Atharvaveda too. Verified after the change:
visarga-vs-ASCII-colon and U+A8F3-vs-U+1CEA now fold equal. `UNCLASSIFIED` fell 132 → 116
and the two informative categories rose. **I did not patch `normalize/` myself.**

The residual 116 are dominated by a genuine editorial difference, not an encoding one: the
unaccented layer word-splits with avagraha (`कर्मणऽ आ प्यायध्वम्`) where the accented layer
reads sandhi-joined (`कर्म॑ण॒ आप्या॑यध्वम्`). The two layers digitise the same 1929 print but
present it under different segmentation conventions, so they are not token-alignable without
a deliberate mapping — and the comparator correctly declines rather than guessing.

**Four incompatible accent encodings are now documented for the same VS nasal** (VS 1.1):
TITUS `m̐` U+0310 · Vedic Heritage and DharmicData `ᳪ` U+1CEA · Sanskrit Library `M` (SLP1,
distinction lost) · DCS absent entirely. Any future multi-source VS ingestion needs an
explicit, declared normalization decision per source — **not** a merge, and not a single
global code-point table.

**This blocks Samaveda and Atharvaveda equally**, since all three remaining Vedas are
Devanagari-primary. Reported to Agent F, who owns `normalize/` and `compare/`. **Not patched
here.** Two source defects also recorded and not silently cleaned: one **U+F15C**
private-use character and one **U+00AC** not-sign in the Wikisource text.

---

## 9. Verdict

**`SOURCE_STACK_APPROVED_WITH_LIMITATIONS`**

Cross-reference: Agent E's rights matrix records this Veda as
`RIGHTS_SUFFICIENT_BUT_NO_USABLE_PRIMARY_TEXT_LAYER`. The two verdicts agree; mine is
scoped to the adjudication and the pilot, E's to the rights matrix.

### The governing limitation, stated first

**This work has no usable primary text layer.** The artifact is rights-clear and complete,
but it decomposes into two layers and *neither qualifies*:

| Layer | Coverage | Faithful? | Registered role |
|---|--:|---|---|
| `WIKISOURCE_SA.YV.VSM.UNACCENTED` | 1,836 / 1,975 | yes | `PARALLEL_TEXT` |
| `WIKISOURCE_SA.YV.VSM.ACCENTED` | 1,958 / 1,975 | **no** — extraction-derived | `EXTRACTED_FROM_CONTAINER` |

`TextRole.EXTRACTED_FROM_CONTAINER` states that such a layer must never be selected as
`primary_sanskrit`, because doing so would make an interpretive segmentation canonical.

An earlier revision of this section claimed "nothing here blocks full-corpus Sanskrit
ingestion" and that the limitations were "about adjacent layers". **That was wrong**, and it
was wrong in the direction that overstates readiness. Rights clarity and artifact
completeness are not evidence of a usable primary layer — they are three independent
properties, and I had all the facts for this one before I drew the conclusion. The
retraction is left in place rather than deleted: a deleted error teaches nobody, and naming
*which direction* it erred tells a future reader which way to be suspicious.

Worth recording how it survived, because it is a distinct and easily repeated failure:
**a conclusion does not re-derive itself when its premises change.** Five surrounding
sections were updated as the role ruling landed, and editing premises feels like doing the
work — which is exactly why the stale conclusion sat untouched through all of it. Agent E
made the identical mistake on the matrix cell those same updates falsified.

### What full ingestion would and would not yield

**Would:** 1,975 provenanced mantra passages over 40 adhyāyas, identity from a FINAL model,
two independently stored text layers, CC BY-SA rights resolvable to the artifact, ~2,106
per-mantra ṛṣi assertions, and a byte-identical deterministic rebuild.

**Would not:** any canonical Sanskrit reading. Downstream work that needs one — the lexical
layer, semantic extraction, alignment — cannot proceed on this Veda until the primary-layer
gap closes.

**Bounded path to closing it** (Agent E has recorded it as reviewable, not final):
reimplement the accented layer to read the source-declared ordinal headers I demonstrated
exist, using a hybrid of accent-presence plus header confirmation, which would likely also
recover the 17 mantras currently lacking an accented reading; then resolve the two
`NEEDS_REVIEW` editorial interventions, of which VSM 16.37 is a genuine philological
decision requiring a human. `PRIMARY_TEXT` then becomes correct.

### Approved because

The recension is proved from the artifacts themselves; the printed edition is identified
(Nirṇaya Sāgara 1929, ed. Paṇaśīkara); the licence was read from the wiki's own API and
adjudicated by the rights authority; adhyāya and mantra counts are computed from every
snapshot and reproducible from the release; Vedic accents are preserved and never
overwritten; the adapter runs cleanly over all 40 adhyāyas; the 136-passage pilot rebuilds
byte-identically and passes every QA gate including the four registry/provenance gates; and
the traditional-metadata layer is real, provenanced, and free of inference.

### Why this is not `SOURCE_ADJUDICATION_INCOMPLETE` — an auditable test, not a judgement

A verdict label describes **the state of our knowledge, not the desirability of the
answer**. The test, so a reader can check this label rather than trust it:

> **If new research would change the label, it is incomplete. If only a new source would
> change it, it is complete and negative.**

This case is the second kind. Nothing here is unknown: every candidate was assessed with
verbatim artifact-level rights evidence, the recension was proved from the artifacts rather
than from filenames or catalogue labels, counts were computed from every snapshot, and
rights and roles are adjudicated and registered. More research would not move the answer —
only a better source would (a complete direct transcription, or written permission from the
TITUS Project, whose text is a named scholarly edition and would become the preferred
primary).

Labelling this `SOURCE_ADJUDICATION_INCOMPLETE` would therefore assert that we do not know
something we did establish. That is dishonest in the less obvious direction: not
overstating readiness, but **understating what was determined**, and inviting a reader to
think further research might change the answer. It would not. The honest description is
*adjudicated, and the answer is partly negative*.

This is the same principle as treating `UNKNOWN` rights as a legitimate terminal answer
rather than a placeholder to be optimistically resolved, applied to verdicts instead of
statuses. Ruling confirmed by Agent E, the rights authority.

### Also limited by

**(a)** no English or Hindi translation layer without OCR; **(b)** no lawful padapāṭha, so
the Rigveda's lexical layer has no counterpart (DCS gives CC BY-4.0 morphology for adhyāyas
1–15 only, unaccented, and is not a traditional padapāṭha); **(c)** neither `devatā` nor
`chandas` can be asserted until the Sarvānukramaṇī is expert-parsed, and both need schema
changes first; **(d)** cross-layer classification is mostly `UNCLASSIFIED` — not for encoding
reasons, which Agent F fixed, but because the two layers use different sandhi/segmentation
conventions and are not token-alignable without a deliberate mapping; **(e)** the
transcription is community-made, so a human spot-check against the 1929 print is advisable;
**(f)** audio is a hard negative.
