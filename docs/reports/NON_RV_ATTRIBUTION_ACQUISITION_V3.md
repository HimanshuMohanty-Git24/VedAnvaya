# Non-Rigvedic Attribution Acquisition — Knowledge Model V3

**Agent G** — cross-Veda attribution and metadata acquisition.
**Date:** 2026-09-09. **Scope:** Devata / Rishi / Chandas for Samaveda, Yajurveda, Atharvaveda.
**Status of this document:** research and recommendation only. Nothing was built, no registry was
written, the graph was not touched.

**Policy note, recorded because it changes three verdicts.** The project owner has ruled that this
is a private local research project, that licensing analysis is out of scope, and that
redistribution rights must not block source use. Provenance still matters. Three sources that prior
reports rejected *solely* on rights grounds are therefore re-opened below and assessed on their
merits: the GRETIL Samaveda TEI, `vedicheritage.gov.in`, and Vishva Bandhu's 1970
*Atharvaveda Ṛṣi-Devatā-Chando-Anukramaṇikā*. Every other rejection in this document rests on
edition identity, numbering alignment, transcription quality or scope — not on rights.

---

## 0. Verdicts

| Veda | Verdict | Expected passage coverage | Route |
|---|---|---|---|
| **Yajurveda** (VSM Mādhyandina) | **PARTIALLY_ATTAINABLE — and already paid for** | **`HAS_RISHI` on 1,960 of 1,975 mantras (99.24%)**, *already built and sitting on disk unused*. `HAS_DEVATA` / `HAS_CHANDAS`: 0 mechanically, source on disk but prose-only | Wire up `data/canonical/yajurveda_vsm_v1/traditional_metadata.jsonl` |
| **Atharvaveda** (Śaunaka) | **PARTIALLY_ATTAINABLE** | **588 of 731 hymns → 4,881 of 5,839 mantras (83.6%)** rishi + devata + chandas at hymn scope, plus per-verse chandas exceptions. Kāṇḍa 20 (143 hymns / 958 mantras) unreachable from this source | Whitney's Anukramaṇī brackets, harvested from the **en.wikisource `Page:` namespace** (not mainspace) |
| **Samaveda** (Kauthuma ārcika) | **BLOCKED** | **≈15 verses (0.8%)** from the only source-stated triads that exist. No route to meaningful coverage | — |

**Single highest-value acquisition:** none — the single highest-value action is not an acquisition
at all. It is **wiring up the Yajurveda rishi assertions that already exist on disk** and are read
by nothing. That is 2,240 assertions covering 99.24% of the VSM, at zero acquisition cost and zero
inference. See §1.1.

**Is anything already on disk unexploited?** Yes, and it is the largest finding in this report. See
§1.

---

## 1. Phase 1 — what is already local

### 1.1 UNEXPLOITED: the Yajurveda rishi layer is built, on disk, and read by nothing

`data/canonical/yajurveda_vsm_v1/traditional_metadata.jsonl` — **2,240 rows, every one a
`HAS_RISHI` assertion**, measured:

| Property | Value |
|---|---|
| Assertions | 2,240 |
| Distinct passages covered | **1,960 of 1,975 VSM mantras = 99.24%** |
| Distinct rishi value strings | 249 |
| `scope_type` | `SINGLE_MANTRA` on all 2,240 |
| `source_id` | `WIKISOURCE_SA` |
| `status` | `UNREVIEWED` on all 2,240 |
| Source artifact | `WIKISOURCE_SA.YV.VSM.RISHISUCI` = `शुक्लयजुर्वेदः/ऋषिसूची` |
| Pinned snapshot on disk | `data/raw/wikisource_sa/2026-09-07/2151af3f369e21c2792b0bc7d43efce3c2242e568ad1c5725fe40fd35c743caa.php` |
| Provenance sidecar | 2,240 matching `TRADITIONAL_METADATA_PROVENANCE` rows in `source_assertions.jsonl`, each carrying the printed index line, the line number, the stated scope and `entity_resolution_method` |

The 15 uncovered mantras are `VG:YV:VSM:A27:V029` and 14 addresses in `A33`.

**Why it is not in the graph.** The attribution edge producer is hard-wired to the Rigveda:

- `src/vedagraph/graph/entities.py:86` — `iter_rishi_devata_chandas_rels()` reads exactly one path,
  `data/knowledge/rigveda_deterministic_v1/knowledge_assertions.jsonl`.
- `src/vedagraph/enrich/corpus.py:114` — `_resolved_metadata()` reads the same single path, and its
  docstring states *"Only the Rigveda has any -- the other three sources carry no anukramani at
  all."* **That statement is false for the Yajurveda** and is the reason the layer was never read.
- `scripts/build_neo4j_projection.py` contains no reference to `traditional_metadata` or to any of
  the three predicates.

So `data/enrichment/vedagraph_enrichment_v1/analytics.json` correctly reports
`coverage.per_veda.YV.with_traditional_metadata = 0` — the graph really has none — while 2,240
source-stated assertions sit two directories away. This is the "verify projections against a live
store" failure mode in a new place: the corpus release and the graph disagree, and only the graph
was ever measured.

**The blocker registry already anticipated this.** `four_veda_canonical_sanskrit_blockers.yaml`
records `projected_rishi_assertions_at_full_scale: 2106` for `VG:WORK:YV:VSM` and marks the
`metadata_schema` dimension `OPEN_ENGINEERING`, explicitly noting it does not gate the Sanskrit
layer. The full build then produced 2,240. The blocker is a schema/wiring blocker, not a data
blocker.

**One real cost, quantified, so it is not discovered later.** The 249 rishi strings are Devanagari
and deliberately unresolved (`entity_resolution_method = VERBATIM_SOURCE_STRING_NOT_RESOLVED`). The
existing `data/registry/rishis.yaml` holds 367 entities with IAST `preferred_label` only. Measured
with the repo's own `DevanagariToIAST`:

- **13 of 249 distinct strings (5.2%) resolve exactly**, covering 218 of 2,240 assertions (9.7%).
- The 236 that do not resolve fail for a *systematic* reason, not a spelling one: the RV registry
  stores the Sarvānukramaṇī's full patronymic compounds (`rāhūgaṇo gotamaḥ`, `aucathyo dīrghatamāḥ`,
  `gāthino viśvāmitraḥ`) while the YV ऋषिसूची gives bare names (`गोतमः`, `दीर्घतमा`,
  `विश्वामित्रः`). Asserting they are the same person is a philological judgement.

**Therefore: do not merge YV rishi strings into the RV rishi registry.** Land them as YV-scoped
Rishi nodes carrying the verbatim source string, and defer cross-Veda identity to recorded human
review. A blanket alias merge here is precisely the class of defect that per-row sampling cannot
see — the error would be concentrated in a handful of high-frequency aliases (`प्रजापतिः` alone is
197 assertions).

### 1.2 The Yajurveda devatā/chandas source is also on disk — and is genuinely not mechanical

`शुक्लयजुर्वेदः/सर्वानुक्रमणी` is snapshotted at
`data/raw/wikisource_sa/2026-09-07/91203256234de6dbe6fa626c911a9bb674aebe0a6688acd2ba2a5388c0208e28.php`
— 140,184 bytes, 168 numbered sūtra markers. It is the **Mādhyandina Vājasaneyi** Sarvānukramaṇa-sūtra,
and it names its own recension in its opening line, so recension compatibility is exact and stated.
Its preamble declares the fields and their limits verbatim:

> …माध्यन्दिनीये वाजसनेयके यजुर्वेदाम्नाये … **ऋषिदैवतच्छन्दांस्यनुक्रमिष्यामो** —
> **यजुषामनियताक्षरत्वादेकेषां छन्दो न विद्यते** — द्रष्टारो ऋषयः, परमेष्ठ्यादयो देवता,
> **अनःशाखोखाशम्यो­पवेषकपालेध्मोलूखलादयश्च प्रतिमाभूताः**, छन्दांसि गायत्र्यादीनि …

Three properties follow, and all three are already correctly recorded in the corpus's
`TRADITIONAL_METADATA_SCOPE` assertion:

1. `chandas` is **legitimately asserted-absent** for many yajus ("because the yajus have no fixed
   syllable count, for some of them no metre exists"). Absent ≠ unknown, and the schema must be able
   to say which.
2. The YV `devatā` co-domain **includes ritual implements** — cart, branch, ukhā pot, yoke-pin,
   potsherd, firewood, mortar — as *pratimābhūta*. A shared RV/YV devatā enum is a modelling error.
3. `ṛṣi` is **ritual-block-scoped**, with *vivasvān* as the saṃhitā-wide default refined
   *pratikarma-vibhāgena brāhmaṇānusāreṇa*.

**Alignment.** The text addresses mantras by **pratīka (incipit)**, not by number:
`इषेत्वादि खंब्रह्मान्तं विवस्वानपश्यत्` … `इषेत्वा शाखा` … `अनुष्टुब्` … `ऊर्जेत्वा वायवे
वायव्यं`. Pratīka alignment against our 1,975 accented mantras is a real deterministic method — it
is how the RV Sarvānukramaṇī is used — but the surrounding text is continuous sūtra prose with
*liṅgokta* ("deity indicated by the characteristic mark") standing in for many deities, and the
tradition keeps its own register of non-assignments (*anādiṣṭa-devatādayaḥ*) which the pipeline must
reproduce rather than fill. This needs expert philological reading, not a parser. Prior reports'
refusal to machine-resolve it is upheld.

### 1.3 Verified negatives — checked, not assumed

| Candidate on disk | What I measured | Verdict |
|---|---|---|
| **Griffith, White Yajurveda** (`data/raw/sacred_texts/2026-09-07/wyv/`, all 40 books, 45 files) | Across all 40 books: `the Rishi is` **0**, `the deity is` **0**, `the metre is` **0**, `anukraman` **0**. Every `Deity`/`Rishi`/`metre` hit is *translated mantra text* — VSM 14 literally enumerates metres and deities as agnicayana bricks. The 3 `addressed to` hits are sacred-texts.com's own modern JS page summaries, not Griffith. | **The brief's premise that "Griffith 1899 prints deity ascriptions in places" is refuted for the White Yajurveda.** No attribution apparatus. |
| **YV adhyāya pages** on sa.wikisource (40 pages, e.g. `अध्यायः १४` with 22 देवता + 202 छन्द hits) | All hits are inside **Mahīdhara's Vedadīpa bhāṣya** (interleaved with Pāṇini sūtra citations, e.g. `(पा. २ । ४ । ७६)`) or inside the accented mantra text. No structured per-mantra attribution field anywhere. | Not a structured source. Corroborates §1.2. |
| **GRETIL AVS accented** `avs_acu.htm` | `devatā` 1 hit, in mantra text. Matches the corpus's own `ARTIFACT_SUPPLIES_NO_TRADITIONAL_METADATA` assertion. | Confirmed barren. |
| **GRETIL AVS *unaccented*** `avs___u.htm` — *this one was never audited; the absence assertion names only the accented artifact* | `ṛṣi` 35, `devatā` 34, `devata` 2, `chandas` 1. **I read every context: all are inside mantra text** (`taṃ brahmāṇaṃ tam ṛṣiṃ`, `yena devā devatām agra āyan`). | Also barren. The absence assertion is correct for both artifacts, and is now verified on the one it did not name. |
| **GRETIL Samaveda TEI** (`sa_sAmavedasaMhitA.xml`, the corpus's `structure_evidence_sha256` witness) | Prior report estimated "~24 triads". **Measured: 5.** Paragraph-initial head lines over all 479 `<p>` elements: `asitaḥ kāśyapo devalo vā. gāyatrī. pavamānaḥ somaḥ.`, `kaśyapo mārīcaḥ. gāyatrī. pavamānaḥ somaḥ.`, `irīmbiṭhiḥ kāṇvaḥ. gāyatrī. indraḥ.`, `viśvāmitro gāthinaḥ. gāyatrī. indrāgnī.`, `amahīyurāṅgirasaḥ. gāyatrī. pavamānaḥ somaḥ.` All 5 in the Uttarārcika; Pūrvārcika has none. | Rights no longer block it; **arithmetic does.** At dasati scope, ≈15 of 1,844 verses = 0.8%. |
| **SV pages** on sa.wikisource (106 ārcika pages on disk) | Prior report claimed Wikisource triads are "better covered". **On the ārcika pages we hold: 31 chandas tokens on 13 pages, all inside Jaiminīya Brāhmaṇa commentary prose; 0 gāna notation marks.** The claimed triads are on the **gāna** pages (725 of the 840), which `VG:WORK:SV:KAU` explicitly does not cover. | Correction to prior research. Not available at ārcika scope. |
| **SV → RV cross-references** on sa.wikisource | Prior report claimed "explicit Rigveda cross-references on 363 pages". **On the 106 ārcika pages on disk: 33 references on 9 pages** (form `ऋ. [[ऋग्वेदः सूक्तं ९.९६\|९.९६.१७]]`). Editorial annotations, not systematic. | 33 verses, not a route. |
| **VHP** (`data/raw/vhp/`, 5 RV pages) | The `Devata`/`Chanda` hits are **navigation menu chrome**, not data. (Incidentally: VHP's menu confirms it hosts the Ārṣeya and Devatādhyāya Brāhmaṇas — relevant to §2.3.) | No attribution payload in the snapshot. |
| **`data/raw/vedaweb_avs/`** (1,770 files) | `anukr` **0 files**. The AVS module carries text and structure only. | No attribution. |
| **`data/canonical/*/traditional_metadata.jsonl`** for SV and AV | **0 bytes each.** RV release carries 9 rows (raw VHP strings); the 31,646 resolved RV assertions live in `data/knowledge/rigveda_deterministic_v1/`. | Empty as documented. |
| **`data/derived/metadata_candidates/candidates.jsonl`** | 15 KB, Rigveda Mandala 1 range-review only. | Not cross-Veda. |
| **GRETIL index** (fetched live) | No anukramaṇī, ārṣeya, samavidhāna or index apparatus listed for SV, YV or AV. | Confirms prior research. |

### 1.4 On-disk summary, per Veda

| Veda | Devata | Rishi | Chandas |
|---|---|---|---|
| **YV** | 0 (source present, prose-only) | **1,960 / 1,975 mantras — BUILT, ON DISK, UNREAD** | 0 (source present, prose-only) |
| **SV** | ≈5 dasati-scoped triads (≈15 verses) | ≈5 dasati-scoped triads (≈15 verses) | ≈5 dasati-scoped triads (≈15 verses) |
| **AV** | 0 | 0 | 0 |

---

## 2. Phase 2 — external acquisition

### 2.1 Atharvaveda — Whitney's Anukramaṇī brackets, en.wikisource. **RECOMMENDED**

**What it is.** Whitney & Lanman, *Atharva-Veda Saṁhitā* (HOS 7–8, 1905), transcribed on English
Wikisource with ProofreadPage. Whitney prints, as a bracketed header under each hymn title, an
excerpt of the **Bṛhatsarvānukramaṇī** — the Atharvaveda's own index — giving rishi (with the
rishi's *kāma*), devatā, verse count, and a default chandas with per-verse exceptions.

**Recension compatibility.** Śaunaka, Berlin/Roth–Whitney numbering — **the same spine as our
primary artifact.** This is the one thing that matters most and it is exact.

**A correction to prior research, and the reason this route is better than previously described.**
`ATHARVAVEDA_SOURCE_RESEARCH.md` recommends harvesting from **588 mainspace hymn pages**. I
enumerated them via `list=allpages`: **there are 448, not 588.**

| Kāṇḍa | Our hymns | Whitney mainspace pages | Missing |
|---|---:|---:|---:|
| 1–6, 8–14, 17–19 | 448 | 448 | 0 |
| **7** | 118 | **5** | **113** |
| **15** | 18 | **0** | **18** |
| **16** | 9 | **0** | **9** |
| **20** | 143 | **0** | **143** |
| **Total** | **731** | **448** | **283** |

Mainspace-only coverage is therefore 448 hymns / **4,371 of 5,839 mantras (74.9%)**, not the implied
~83%.

**But the content is not missing — only the wrapper pages are.** The `Page:` namespace is
**complete and gapless**: `Index:Atharva-Veda samhita.djvu` has pages 1–648 with **zero gaps**, and
`Index:Atharva-Veda samhita volume 2.djvu` has 1–606 with **zero gaps**. I verified the brackets for
the three "missing" books directly:

- Book VII — `Page:Atharva-Veda samhita.djvu/619`, `pagequality level=3`, running header
  `449|TRANSLATION AND NOTES. BOOK VII.|-vii. 83`:
  `[Çunaḥçepa.—caturṛcam. vāruṇam. ānuṣṭubham: 2. pathyāpan̄kti; 3, 4. triṣṭubh (4. bṛhatīgarbkā).]`
- Book XV — `Page:Atharva-Veda samhita volume 2.djvu/329`, `level=3`, header `785|…BOOK XV.|-xv. 12`:
  `[ekādaçaka. 1. 3-p. gāyatrī; 2. prājāpatyā bṛhatī; 3, 4. bhurik prājāpatyā ’nuṣṭubh (4. sāmnī); 5, 6, 9, 10. āsurī gāyatrī; 8. virāḍ gāyatrī; 7, 11. 3-p. prājāpatyā triṣṭubh.]`
- Book XVI — `Page:…volume 2.djvu/345`, `level=3`, header `801|…BOOK XVI.|-xvi. 8` (mid-hymn page; no
  bracket on that leaf, as expected).

**So harvest from the `Page:` namespace (1,254 pages), not from mainspace.** That lifts coverage to
the full **588 hymns of books I–XIX = 4,881 of 5,839 mantras (83.6%)**. Note that book XV's bracket
carries per-verse **chandas only, no rishi or devatā** — the prose books are structurally different
and must not be padded to look uniform.

**Numbering and alignment — three worked examples, all fetched live and verified.**

| # | Whitney bracket (verbatim, as fetched) | Maps onto our keys | Result |
|---|---|---|---|
| 1 | **AVS 1.1** `[Atharvan.—vācaspatyam. caturṛcam. ānuṣṭubham: 4. 4-p. virāḍ urobṛhatī.]` | `VG:AV:SAU:K01:S001` ← rishi *Atharvan*, devatā *vācaspatya*, chandas *ānuṣṭubh*; `…:S001:V004` ← chandas *4-p. virāḍ urobṛhatī* | **MAPS.** `caturṛcam` = 4 verses; our AVS 1.1 has exactly 4 mantras. The stated verse count is a free alignment gate. |
| 2 | **AVS 19.53** `[Bhṛgu.—daçakam. mantroktasarvātmakakāladevatyam. ānuṣṭubham: 1-4. triṣṭubh; 5. nicṛt purastādbṛhatī.]` | `VG:AV:SAU:K19:S053` ← rishi *Bhṛgu*, devatā *Kāla*; `…:V001`–`V004` ← *triṣṭubh*; `…:V005` ← *nicṛt purastādbṛhatī*; hymn default *ānuṣṭubh* for V006–V010 | **MAPS.** `daçakam` = 10 verses. Requires the `ç → ś` HOS-orthography normalisation pass. Devatā is a compound descriptor (`mantrokta-sarvātmaka-kāla-devatya`), not a bare deity name — parse to *Kāla* and keep the raw string. |
| 3 | **AVS 12.5** `[Paryāya I.—ṣaṭ. 1. prājāpatyā ’nuṣṭubh; …]` `[Paryāya II.—pañca. 7. sāmnī triṣṭubh; 8, 9. ārcy anuṣṭubh (8. bhurij); 10. uṣṇih; 11. ārcī nicṛt pan̄kti.]` `[Paryāya III.—ṣoḍaça. 12. virāḍ viṣamā gāyatrī; …27. ārcy uṣṇih.]` | `VG:AV:SAU:K12:S005:V001…V027…` — verse numbers run **continuously within the hymn**, exactly as our keys do | **MAPS, with one residual.** Whitney's own conspectus gives hymn 12.5 **73** paragraphs; our corpus holds **72** mantras under `K12:S005`. A 1-unit discrepancy to adjudicate, not a systemic break. |

**This resolves the prior report's fatal objection #3.** That objection ("the numbering does not
join in books 7–13") was raised against **sa.wikisource**, which splits paryāya-sūktas across
separate pages (kāṇḍa 12: 11 pages for 5 hymns). Whitney does the opposite — he states plainly that
hymn 12.5 "is made up of 7 *paryāyas*, which, if they be counted separately, make the hymns number
11 instead of 5" and **keeps 5**. Our corpus has K12 = 5 hymns. **Whitney's bracketing is ours;
sa.wikisource's is not.** No hand-built mapping table is required for the Whitney route.

| | |
|---|---|
| Scope | **Hymn-level** for rishi and devatā; **per-verse** for chandas exceptions |
| Coverage if ingested | 588 hymns / **4,881 mantras (83.6%)**; kāṇḍa 20 excluded at source |
| Effort | Medium. 1,254 `Page:` fetches, `<section begin="hymnNN">` segmentation, bracket parse, `ç→ś` + `n̄→ṅ` normalisation, pinned `oldid` per page, verse-count gate against our own mantra counts |
| Confidence the mapping is defensible | **High.** Same recension, same numbering spine, same hymn bracketing, source-stated verse counts as a built-in check |
| Residuals to record, not paper over | Kāṇḍa 20 absent (Whitney excluded it deliberately); book XV brackets carry no rishi/devatā; `pagequality` is 3 (Proofread) not 4 (Validated) on the pages I sampled; the AVS 12.5 73-vs-72 count |

### 2.2 Atharvaveda — kāṇḍa 20 and the other candidates

| Candidate | Assessment |
|---|---|
| **Vishva Bandhu, *Atharvaveda Ṛṣi-Devatā-Chando-Anukramaṇikā*, Hoshiarpur 1970** — *rights-blocked in prior research; now re-opened* | **The only true per-mantra AV source.** Śaunaka, and Vishva Bandhu's numbering is already the corpus's secondary citation system (`AVS_VISHVA_BANDHU_1960`, 261 citations on disk), so alignment is partly solved. **But it exists only as page scans**, and prior work measured Devanagari OCR on this material as badly corrupted. Effort is a full transcription project, not a fetch. Assess again only if the AV needs per-mantra rather than per-hymn devatā. |
| **Bṛhatsarvānukramaṇī**, 1922 Lahore ed. (`archive.org`) | Genuine forward per-sūkta table with pratīka, verse count, rishi, devatā, per-verse metre, plus Hindi footnotes reconciling divisions against the Pañcapaṭalikā, Kauśika and Vaitāna Sūtras. Note it counts **759** hymns including *khilāni* against our 731 — a real bracketing difference. Blocked on OCR quality. |
| **sa.wikisource AV per-sūkta headers** (773 pages, *not on disk*) | Measured coverage is high (99.6% rishi / 97.1% devatā / 91.3% chandas over 756 pages) **and it covers kāṇḍa 20 and the prose books**, which Whitney does not. Rights are fine. Two non-rights defects stand: **no cited edition anywhere** (so a 5.3% internal self-disagreement rate is unadjudicable — ~10 flat name conflicts at AV 2.3, 2.24, 6.36, 6.99, 7.21, 9.8, 16.1, 16.2, 19.9, 20.2), and **its hymn bracketing is not ours** in books 7–13. **Candidate-only, never gold.** Its real value is as the *only* route to kāṇḍa 20 attribution. |
| **`vedicheritage.gov.in` per-sūkta rishi/devatā/metre** — *rights-blocked in prior research; now re-opened* | Highest-authority Indian government source, with scanned page images that would adjudicate the sa.wikisource conflicts. My local VHP snapshot contains only navigation chrome, so payload and granularity are **unverified**; the live per-sūkta pages need a probe before any estimate. Worth one bounded investigation. |
| **Pañcapaṭalikā, Śaunakīya Caturādhyāyikā** | No e-text exists. Print-only. |

### 2.3 Samaveda — the apparatus exists, and it cannot be joined

This is the substantive new finding for the Samaveda, and it is a negative one.

`SAMAVEDA_SOURCE_RESEARCH.md` concluded "No verified Samaveda Anukramaṇī was located anywhere."
That is true of an *anukramaṇī proper*, but it misses the Kauthuma school's two actual attribution
texts, both published and both long out of copyright:

- **Ārṣeya Brāhmaṇa** (Kauthuma; ed. A. C. Burnell, 1876). Described in the literature as
  "essentially an anukramaṇikā — a mere list of the names of the **sāmans** occurring in the first
  two **gānas**." This is the Samaveda's rishi apparatus.
- **Devatādhyāya Brāhmaṇa** (ed. A. C. Burnell, Mangalore 1873). "Deals with the **deities** to
  which the **sāmans** are addressed." This is the Samaveda's devatā apparatus.

**Why they cannot be used.** Both are keyed to **sāman names within the gāna collections**. Our
`VG:WORK:SV:KAU` covers the **ārcika (verse) text only** and says so explicitly in `works.jsonl`:
*"The Kauthuma gāna collections — roughly 2,639 gānas … are a PARALLEL AND LARGER body that this
work_id does not cover and cannot address."* Joining Ārṣeya/Devatādhyāya to our keys is a three-hop
traversal — ārcika verse → sāman → gāna address → brāhmaṇa entry — and **we hold none of the middle
hops.**

The join key does exist in principle and I measured it: **142 sāman-name annotations on 20 of the
106 ārcika pages on disk** (`वारवन्तीयं`, `ऋषभोरैवतम्`, `गौरीवितम्`, `वैरूपम्`, `कार्णश्रवसम्`,
`मधुश्चुन्निधनम्` …). At 142 annotations over 1,844 verses that is **7.7% of a bridge**, and the
bridge is to a source we would still have to acquire and transcribe. Separately, these annotations
would support a genuinely Samavedic `HAS_SAMAN` predicate, which is a better use of them than
attribution.

**Other SV candidates, assessed:**

| Candidate | Verdict |
|---|---|
| **GRETIL Samaveda TEI** — *rights-blocked in prior research; now re-opened* | **5 triads measured** (§1.3). Rights were never the real problem; coverage is. ≈15 of 1,844 verses. |
| **Samasrami / Sāyaṇa *Sāmavedasaṁhitā***, Asiatic Society Bibliotheca Indica, 5 vols 1874–78 — scan-backed on sa.wikisource, flagged as a new lead in `four_veda_canonical_sanskrit_blockers.yaml` | **Checked directly, and it does not deliver.** `अनुक्रमणिका:सामवेदसंहिता भागः १.pdf` has 798 transcribed `Page:` pages; vol 3 has 132; "Vol-II" has 2. I sampled three pages spread across vol 1 (`/२११`, `/३२५`, `/४४`): **all at `pagequality level="1"` = *Not proofread*, i.e. raw uncorrected OCR**, and badly corrupted (`अपेनपर्वतस्य २ १ र १ र १ २ पा२२ीत्`). No `ऋषिः`/`देवता`/`छन्दः` triad apparatus in any sample — Sāyaṇa's SV bhāṣya in this edition is continuous commentary, not a triad header. Not usable. |
| **Rāṇāyanīya / Jaiminīya anukramaṇīs** | **Recension-incompatible by construction.** Our corpus is Kauthuma ārcika. Not pursued. |
| **`vedicheritage.gov.in` Samaveda** | Fetched: the Samaveda samhita page presents structural divisions only. No per-verse metadata fields documented. Also hosts the Ārṣeya and Devatādhyāya Brāhmaṇas — same gāna-keying problem. |

**Samaveda verdict: BLOCKED.** Not for want of a source, and not for want of rights. The
Samaveda's own attribution apparatus is addressed to a body of text this work_id does not contain.
Closing this would mean first acquiring and keying the gāna collections — a larger project than the
ārcika itself, and one that needs its own `work_id`.

### 2.4 Yajurveda — external candidates beyond §1.1/§1.2

| Candidate | Assessment |
|---|---|
| **Mahīdhara *Vedadīpa* / Uvaṭa commentary headers** | Mahīdhara's bhāṣya is already on disk, interleaved in the 40 sa.wikisource adhyāya pages. It states devatā **in running prose** (`अस्य मन्त्रस्य देवता…`), not in a header field — measured in §1.3. Not mechanically resolvable. |
| **A published VS anukramaṇī separate from the Sarvānukramaṇa-sūtra** | Prior research and my own GRETIL index fetch both find none. The Sarvānukramaṇa-sūtra in §1.2 *is* the source. |
| **`vedicheritage.gov.in` Yajurveda** | Unverified, same bounded probe as §2.2. Note prior research found all 40 VHP Mādhyandina audio URLs returning 404 since ≥2025-04, so the section may be degraded. |
| **Bloomfield *Vedic Concordance*** (GRETIL, keyed) | 8,475 entries citing `VS.`, of which 3,861 also cite Śatapatha Brāhmaṇa and 1,148 also cite Kātyāyana Śrautasūtra. This is **viniyoga** (ritual application), a verbatim mantra→ritual-act mapping needing no judgement. **Not Devata/Rishi/Chandas** — but it is the highest-value *non*-attribution metadata increment available for the YV, and the Sarvānukramaṇa-sūtra itself defers viniyoga to the Śrautasūtra (`viniyogaḥ kalpakāroktaḥ`). Recommend it be tracked separately rather than counted against the attribution blocker. |

---

## 3. The "transfer RV attribution along textual-reuse edges" question

**Verdict: DO NOT DO IT for SV, YV or AV kāṇḍa 1–19. Do not do it for AV kāṇḍa 20 either, but for a
weaker reason — see below.**

### 3.1 What it would actually yield, measured

Computed from `data/enrichment/vedagraph_enrichment_v1/cross_veda_parallels.jsonl` (6,271 edges)
against the 10,552 RV passages carrying attribution:

| Target | Mantras | With **any** RV parallel | Via `EXACT_PARALLEL_OF` / `REUSES_TEXT_FROM` | Devatā gained | Rishi gained | Chandas gained | Multi-valued / conflicting |
|---|---:|---:|---:|---:|---:|---:|---|
| **SV** | 1,844 | 1,662 (**90.1%**) | 1,662 | 1,662 | 1,662 | 1,658 | devatā 1, **rishi 14**, chandas 1 |
| **YV** | 1,975 | 648 (32.8%) | 24 | 24 → 648 (all preds) | 24 → 648 | 24 → 647 | devatā 6, rishi 8 |
| **AV total** | 5,839 | 1,285 (22.0%) | 533 | 533 | 533 | 533 | devatā 1, **rishi 13** |
| — AV K1–19 | 4,881 | 509 (10.4%) | — | — | — | — | — |
| — **AV K20** | 958 | **776 (81.0%)** | 429 exact | 429 | 429 | 429 | — |

Note the brief's premise that "the SV borrows ~95% of its verses from the RV" is close but not
exact at the pipeline level: **90.1%** of our ārcika verses carry an RV parallel edge. So the
transfer route *is* technically the highest-yield option on the table for the Samaveda — 1,662
verses, versus ≈15 from any source-stated route. That is precisely why it needs a clear refusal.

### 3.2 Why it is refused

**1. It is not the same claim.** The RV Sarvānukramaṇī asserts that *Madhucchandas Vaiśvāmitra saw
RV 1.1, addressed to Agni, in the gāyatrī metre*. It asserts nothing whatsoever about the Samaveda.
Copying that triple onto `VG:SV:KAU:…` does not record a Samavedic tradition — it records a
Rigvedic one at the wrong address. The Samavedic tradition's own answer to "whose is this sāman"
is in the Ārṣeya Brāhmaṇa and it is frequently a **different name**, because the Samavedic question
is about the *sāman*, not the *ṛc*.

**2. Chandas is actively wrong for the Samaveda.** The Samaveda's defining property is that the
verse is *sung*. Transferring `gāyatrī` from the RV parent asserts a syllabic structure for a unit
whose Samavedic identity is a melody. Doing this at 1,658 verses would make VedaGraph
systematically misdescribe the one Veda whose distinctness is its metre-transcending chant. For the
Yajurveda it is worse: its own Sarvānukramaṇa-sūtra states that *many yajus have no metre at all*,
so transferred chandas would overwrite a source-stated **absence** with a foreign **presence** —
converting an honest finding into a false one.

**3. Devatā domains are incompatible.** The YV devatā co-domain includes ritual implements as
*pratimābhūta* (§1.2). The AV's includes compound descriptors like
`mantroktasarvātmakakāladevatya` (§2.1) and non-answers like `मन्त्रोक्त` ("whatever the mantra
names"). These are not the RV deity set. A transferred RV devatā is a category substitution.

**4. It would mislead a researcher, and the graph gives them no way to tell.** After a transfer the
Samaveda would show 90.1% attribution coverage against the Atharvaveda's 83.6% — and the Samaveda's
would be borrowed while the Atharvaveda's would be its own Bṛhatsarvānukramaṇī. Every downstream
aggregate — the `rishi_devata_top` lift tables, `devata_chandas_top`, any "which deity dominates
which Veda" question — would silently be answering a Rigvedic question four times over. This is the
failure mode the caller's own hard rule names: it would improve the coverage number and degrade the
knowledge.

**5. Provenance class cannot rescue it.** The four classes available are
`SOURCE_STATED` / `CONTAINER_INHERITED` / `TEXTUAL_MENTION` / `MODEL_INFERRED`.

- `SOURCE_STATED` — **false.** No source states this of the SV/YV/AV passage.
- `CONTAINER_INHERITED` — **false, and the most tempting error.** That class means a value inherited
  from an *ancestor container in the same work* (hymn → its verses). A parallel edge to a different
  Veda is not a container relation.
- `TEXTUAL_MENTION` — **false.** Nothing is mentioned in the passage text.
- `MODEL_INFERRED` — **the only honest fit, and it is a lie in a different direction.** The
  inference is deterministic string matching, not a model, so this class would misdescribe the
  method while correctly signalling "not asserted."

The transfer needs a fifth class that does not exist — something like
`PARALLEL_INHERITED_FROM_OTHER_WORK`, carrying the source passage key, the parallel predicate, the
match level, and the fact that the *originating* work's tradition made the claim. **Recommendation:
do not add that class to make the transfer possible.** Add instead the thing that is actually true
and already computed.

### 3.3 What to do instead — and it is genuinely useful

The 6,271 cross-Veda parallel edges **already exist in the graph** and already carry match level,
scores and per-side evidence quotes. A researcher asking "what is the traditional attribution of
this Samaveda verse?" can be answered correctly today by a **two-hop query**, with no new data and
no new assertions:

> `MATCH (sv:Mantra)-[p:REUSES_TEXT_FROM|EXACT_PARALLEL_OF]->(rv:Mantra)-[:HAS_DEVATA]->(d:Devata)`

That returns the Rigvedic ascription of the parallel verse, and the shape of the answer makes the
borrowing visible instead of hiding it. It is strictly more informative than a transferred edge,
because it names *which* RV verse and *how strong* the parallel is — including the 14 SV verses
whose RV parallels **disagree with each other about the rishi**, which a transfer would have to
silently collapse.

Two concrete deliverables that capture the value honestly:

1. **Ship the two-hop traversal as a named query** in `src/vedagraph/graph/insight_queries.py`
   (`rigvedic_ascription_of_parallel`), returning `(target, rv_source, predicate, match_level,
   devata, rishi, chandas)` with a `borrowed_from_rigveda: true` flag on every row.
2. **Do not let it count toward attribution coverage.** `analytics.json` must keep reporting
   `with_traditional_metadata = 0` for the Samaveda until the Samaveda's own tradition speaks.

### 3.4 AV kāṇḍa 20 — the one case worth stating carefully

Kāṇḍa 20 is the strongest case *for* transfer and I still decline it. Whitney excluded K20 from his
translation on the ground that it is "in the main a pure mass of excerpts from the Rigveda," and our
own edges agree: **776 of 958 K20 mantras (81.0%) have an RV parallel, 429 of them exact.** So here
the tradition itself says the material is Rigvedic.

But "this text is excerpted from the Rigveda" and "the Bṛhatsarvānukramaṇī ascribes this
Atharvavedic hymn to this rishi" are still different assertions, and the AV's own index *does* cover
kāṇḍa 20 — the sa.wikisource apparatus is measurably **best** covered there (124 of 143 hymns for
chandas). The right answer for K20 is therefore **acquire the real thing** (§2.2, route 3), not
transfer. Until then K20 stays at 0 and the two-hop query serves it.

---

## 4. Phase 3 — ranked acquisition plan

| # | Action | Veda | Coverage gain | Provenance class | Effort | Risk |
|---|---|---|---|---|---|---|
| **1** | **Wire the existing YV rishi layer into the enrichment + graph path.** Generalise `entities.py:iter_rishi_devata_chandas_rels` and `enrich/corpus.py:_resolved_metadata` to read each corpus's `traditional_metadata.jsonl` alongside the RV knowledge layer. Land 249 YV-scoped Rishi nodes from verbatim strings; **do not merge with RV rishis.** Fix the false docstring at `enrich/corpus.py:114`. | YV | **1,960 / 1,975 mantras (99.24%) `HAS_RISHI`** | **`SOURCE_STATED`** — the edition's own ऋषिसूची, with the printed line retained per assertion | **Low.** No acquisition. Two read paths + node minting. | **Low.** One real decision: keep YV and RV rishi namespaces separate. Rows are `UNREVIEWED` and must project as such. |
| **2** | **Harvest Whitney's Anukramaṇī brackets from the en.wikisource `Page:` namespace** (1,254 pages, pinned `oldid` each). Parse rishi / *kāma* / devatā / verse-count / default chandas / per-verse exceptions. Gate every hymn on the source-stated verse count vs our own mantra count. Normalise `ç→ś`, `n̄→ṅ`; keep the raw bracket string on every assertion. | AV | **588 hymns → 4,881 / 5,839 mantras (83.6%)** rishi + devatā + chandas, plus per-verse chandas exceptions | **`SOURCE_STATED`** at hymn scope; **`CONTAINER_INHERITED`** where a hymn-scope value is projected onto its mantras — **these must not be collapsed**; per-verse chandas exceptions are `SOURCE_STATED` at mantra scope | **Medium.** 1,254 fetches; a bracket grammar; orthography pass; a `chandas_absent` reason code for book XV-type brackets that carry no rishi/devatā. | **Medium-low.** Alignment is verified on 3 worked examples and gated by stated verse counts. Known residuals: K20 absent; AVS 12.5 counts 73 vs our 72; `pagequality` 3 not 4. |
| **3** | **Bounded probe of `vedicheritage.gov.in`** per-sūkta/per-mantra pages for AV, YV and SV: what fields, what granularity, what numbering. One session, report only, no bulk fetch. | AV, YV, SV | Unknown — **this is the point of the probe** | TBD | **Low.** | **Low.** Now unblocked by the rights ruling. Prior work found VHP link rot in the YV audio section, so expect degradation. |
| **4** | **Ship the two-hop parallel-ascription query** and hold `with_traditional_metadata` at 0 for SV/AV-K20. | SV, AV K20, YV | 0 attribution assertions — **by design** | none minted | **Low.** | **Low.** This is the honest answer to 19 blocked questions for the Samaveda: it answers them *as borrowing questions*, which is what they are. |
| **5** | **sa.wikisource AV headers as `CandidateMetadataAssertion` only** — the sole route to kāṇḍa 20. Requires: pinned `oldid`; raw string kept; `AssertionStatus.UNREVIEWED`; provenance `UNSOURCED_WIKISOURCE`; a hand-built books 7–13 numbering map; and the ~10 known name conflicts queued for adjudication. **Never promote to gold without an external authority (item 3).** | AV K20 | up to 143 hymns / 958 mantras, **as candidates** | must be a **candidate** record, not a `TraditionalMetadataAssertion`; would be `SOURCE_STATED`-shaped but with **no citable edition**, which is why it stays a candidate | **Medium.** | **High on provenance** — 5.3% measured internal self-disagreement with nothing to adjudicate against. Do item 3 first. |
| **6** | **Expert philological reading of the YV Sarvānukramaṇa-sūtra** (already on disk, sha `91203256234d…`). Pratīka-align to our 1,975 mantras. Requires the schema work first: nullable `chandas` with an `asserted_absent` / `anādiṣṭa` / `unknown` reason code, and a YV devatā union type (deity \| implement \| substance \| ritual act) distinct from the RV deity set. | YV | up to 1,975 mantras devatā + chandas, minus the source's own stated absences | **`SOURCE_STATED`**, recension-exact (the text names *māādhyandinīya vājasaneyaka*) | **High.** Human expert, not a parser. No LLM. | **Low on correctness, high on cost.** The right long-term answer for the YV. |
| **7** | **Re-OCR the 1922 Bṛhatsarvānukramaṇī** and/or **transcribe Vishva Bandhu 1970** for per-mantra AV devatā. | AV | per-**mantra** upgrade over item 2's per-hymn values; K20 included | `SOURCE_STATED` at mantra scope | **Very high.** Devanagari OCR of degraded scans. | Note the 1922 edition counts 759 hymns incl. *khilāni* vs our 731 — resolve bracketing before ingest. |

**Not recommended, explicitly:** transferring RV attribution to any Veda along parallel edges (§3);
adding a provenance class to make that transfer expressible; merging YV/AV rishi strings into
`data/registry/rishis.yaml` without recorded human review; inferring any of it with a language
model.

---

## 5. What I fetched

Everything below was fetched live during this session and saved **only** under
`…/scratchpad/agentG/samples/`. Nothing entered `data/`.

| Target | oldid / revid | Bytes | Response sha256 |
|---|---|---:|---|
| `Atharva-Veda Samhita/Book I/Hymn 1` (wikitext) | 4606225 | 307 | `5cf9f5757be3af6b2308bc9695e36858919e76a9fa22bbf650b5b1f9b50e7c01` |
| `Atharva-Veda Samhita/Book I/Hymn 1` (rendered) | 4606225 | 7,249 | `cb87fa92ae4ae9c11f4dd96640f07e3f79b579bc9179bd45ef39d228aa50a885` |
| `Atharva-Veda Samhita/Book XII/Hymn 1` (wikitext) | 6912107 | 319 | `63e5aa04e1045491be4bec0cf95f9b01a606f70bd8ed97277dcd2116c65d3093` |
| `Atharva-Veda Samhita/Book XII/Hymn 5` (rendered) | 6899954 | 18,990 | `bfbeef075101273074b8de0fbfd61dbffa7f3732913f3116f2c116e4ab99bffe` |
| `Atharva-Veda Samhita/Book XIX/Hymn 53` (wikitext) | 8964162 | 357 | `bb1b6b083e410ef74d71b318bc46b31fc3988ffd316050883001f72c79825451` |
| `Atharva-Veda Samhita/Book XIX/Hymn 53` (rendered) | 8964162 | 9,850 | `298cab6d997cc6c0c2fad506f8a42da2066f112bd9007a039aeedeb9e2dbd0c5` |
| `Page:Atharva-Veda samhita.djvu/171` | 7996371 | 2,717 | `75d8e8b44dcf3b1bb55f39d97214be74a3ebee2bac977978114a22e1427d442f` |
| `Page:Atharva-Veda samhita.djvu/506` | 7506246 | 3,485 | `85eaa0889f9dfeddc5d0bfac2b7c8b238ac14a8a467af713bff8604e8861e32b` |
| `Page:Atharva-Veda samhita.djvu/507` | 7506248 | 3,849 | `a03cb409ccd0efd042576689ababc76df3858186abaee659248b6dacbe45b751` |
| `Page:Atharva-Veda samhita.djvu/619` (Book VII) | 7532005 | 3,805 | `045f7976f450eb786e058847a630dc7f03f83af6c69000aaeb78863f961017b1` |
| `Page:Atharva-Veda samhita volume 2.djvu/204` | 7996339 | 3,870 | `4f3c6fb2eee3b8c6b92c1b189d0a938ee8a83c734e1d2061b44fc57f8c81d873` |
| `Page:Atharva-Veda samhita volume 2.djvu/329` (Book XV) | 7631471 | 2,995 | `962151af465034b4eae2a35dad3975f53b4c697dd9f41b23d9a7ec100d2c21df` |
| `Page:Atharva-Veda samhita volume 2.djvu/345` (Book XVI) | 7639151 | 2,911 | `6dafd8888a999c352017915ee04e9d2792b3fe940ef3d4bca7173261dc1aa1c6` |
| `पृष्ठम्:सामवेदसंहिता भागः १.pdf/४४` | 134516 | 1,560 | `f10c89e67c7511be3f92ad9193974fa81b2c7792e2201fdae2f0cf2a9142ea92` |
| `पृष्ठम्:सामवेदसंहिता भागः १.pdf/२११` | 136886 | 758 | `bf4fbad0843332147453cb616114824b5716e522d52cfa94de602e4a5f4fac7c` |
| `पृष्ठम्:सामवेदसंहिता भागः १.pdf/३२५` | 137631 | 750 | `7864764b657e0547ce9e724c2b8f618a9e4eaa91d3a2ece26a2a71d88245d3cc` |

Also queried, results not persisted as files: `list=allpages` over
`Atharva-Veda Samhita/Book*` (ns 0, 830 titles), over both AV `Index:` prefixes (ns 104, 648 + 606
titles), and over sa.wikisource ns 106/104 for the Samasrami Samaveda; plus `gretil.html` and
`vedicheritage.gov.in/samhitas/samaveda-samhitas/`.

---

## 6. Corrections to prior reports

Recorded so the next pass does not re-derive them.

1. **`src/vedagraph/enrich/corpus.py:114`** states *"Only the Rigveda has any -- the other three
   sources carry no anukramani at all."* **False.** The Yajurveda has 2,240 source-stated rishi
   assertions on disk. This docstring is the proximate cause of the gap.
2. **`ATHARVAVEDA_SOURCE_RESEARCH.md` §6.2** recommends harvesting Whitney from "588 hymn pages" in
   mainspace. **There are 448.** The remaining 140 (K7: 113, K15: 18, K16: 9) exist only in the
   `Page:` namespace, which is complete and gapless. Harvest from `Page:`.
3. **`ATHARVAVEDA_SOURCE_RESEARCH.md` §6.1 finding #3** ("the numbering does not join") is a valid
   objection to **sa.wikisource** and **not** to Whitney. Whitney keeps K12 at 5 hymns, as we do.
4. **`SAMAVEDA_SOURCE_RESEARCH.md` §6** estimates "~24 triads" in the GRETIL SV TEI. **Measured: 5.**
5. **`SAMAVEDA_SOURCE_RESEARCH.md` §6** describes Sanskrit Wikisource SV triads as "better
   covered." On the 106 **ārcika** pages we hold there are **none** — 31 chandas tokens, all inside
   Jaiminīya Brāhmaṇa prose, and 0 gāna notation marks. The triads are on the gāna pages, which are
   out of scope for `VG:WORK:SV:KAU`.
6. **`SAMAVEDA_SOURCE_RESEARCH.md` §6.1** claims "explicit Rigveda cross-references on 363 pages."
   On the 106 ārcika pages on disk: **33 references on 9 pages.**
7. **`SAMAVEDA_SOURCE_RESEARCH.md` §6** states "No verified Samaveda Anukramaṇī was located
   anywhere." Narrowly true, but it misses the **Ārṣeya Brāhmaṇa** (rishis) and **Devatādhyāya
   Brāhmaṇa** (deities), both published by Burnell in the 1870s. They are unusable for a different
   and more informative reason: they are keyed to sāmans in the gānas (§2.3).
8. **The brief's premise** that "Griffith 1899 prints deity ascriptions in places" for the
   Yajurveda is **refuted** over all 40 books on disk (§1.3).
9. **`ATHARVAVEDA_SOURCE_RESEARCH.md`** records `ARTIFACT_SUPPLIES_NO_TRADITIONAL_METADATA` against
   the **accented** GRETIL AVS artifact only. I verified the **unaccented** artifact independently:
   also barren, all 71 keyword hits are mantra text. The assertion's conclusion holds for both.
10. **The Samasrami/Sāyaṇa Samaveda** lead in `four_veda_canonical_sanskrit_blockers.yaml`
    (`printed_edition_recension_determination: OPEN_RESEARCH`) is scan-backed and rights-clean but
    its sa.wikisource transcription is at `pagequality level="1"` (**not proofread, raw OCR**) and
    carries no triad apparatus in any of three sampled pages. It does not solve attribution.
