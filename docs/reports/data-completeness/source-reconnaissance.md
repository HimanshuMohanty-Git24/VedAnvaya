# Source Reconnaissance — Post-V1 Data Completeness Campaign

**Wave**: SOURCE RECONNAISSANCE (campaign section 7)
**Branch**: `phase-data-completeness-v2` · **Baseline commit**: `d6e93a9`
**Date**: 2026-09-15
**Machine-readable companion**: `data/staging/source_recon/source_map.json` — 67 source records
**Scope**: reconnaissance only. No corpus was bulk-downloaded. Neo4j was not touched.

---

## 0. What this wave actually changed

Four things, and they reshape the campaign's shape more than they lengthen its shopping list.

**The Atharvaveda translation gap is one object.** 958 of the 961 missing AV translations are
kāṇḍa 20. The other three are `AVS 3.9.4`, `5.12.11` and `10.8.30`. That was measured locally,
not guessed: joining `translations.jsonl` (4,878 rows, every one `source_id: VEDAWEB`) against
the 5,839 `MANTRA` passages in `data/canonical/atharvaveda_saunaka_digital_working_v1/` leaves
kāṇḍas 1–19 at 100% except those three strays, and kāṇḍa 20 at 0.0%. Both incumbent AV sources
omit kāṇḍa 20 for the *same* reason — Whitney called it "in the main a pure mass of excerpts
from the Rigveda" and left it out, and DCS's Atharvaveda directory likewise stops at kāṇḍa 19.
One acquisition closes 99.7% of the gap.

**Non-Rigvedic Devatā is mostly not a sourcing problem.** The AV devatā source is already on
disk: 1,254 gapless `Page:`-namespace snapshots of Whitney & Lanman's printed
Bṛhatsarvānukramaṇī brackets, pinned 2026-09-09, with a 55 KB builder already written — and its
*chandas* half is already ingested, which is where the baseline's 4,082 AV chandas came from.
The YV devatā source is also already snapshotted: Kātyāyana's Sarvānukramaṇa-sūtra, deliberately
not machine-resolved because it is continuous sūtra prose that says *liṅgokta* ("deity stated by
the characteristic mark") where a parser wants a name. Only the Samaveda had no located source
at all — and now it does.

**Roughly half the AV and YV audio gap may be a mapping defect rather than absence.**
`data/product/audio_discovery_report.json` records 495 AV verses and 33 YV verses as
`text_mismatch`: VedSearch *has* audio at that coordinate, but the recited text did not match
ours. That is the signature of a numbering divergence, and the audio module already corrects
exactly one of those — the Mandala-8 Valakhilya permutation, where a naive key-for-key mapping
would have attached the wrong recitation to 55 hymns. Diagnosing 528 verses is cheaper than
finding a recording for them.

**The Samaveda's attribution and notation live on the *gāna* pages, not the *ārcika* pages.**
This one was measured by sampling, and the negative half of the measurement matters most:
16 ārcika pages on Sanskrit Wikisource carry 184 verse markers and **zero**
ṛṣi/chandas/devatā triads. The gāna pages carry the triads — *and* the notation in real
Unicode, *and* the Commons audio file, *and* the performance metadata, *and* the running ārcika
number as a link, *and* the Rigveda cross-reference. Six layers on one revision-pinnable page.

Everything else below follows from those four, plus a set of dead ends that are worth as much
as the finds.

---

## 1. Translations — 2,927 missing

### 1.1 AV Śaunaka — 961 missing, and it is all kāṇḍa 20

| kāṇḍa | mantras | missing |
|---|--:|--:|
| 1–2, 4, 6–9, 11–19 | 4,050 | 0 |
| 3 | 230 | 1 (`AVS 3.9.4`) |
| 5 | 376 | 1 (`AVS 5.12.11`) |
| 10 | 350 | 1 (`AVS 10.8.30`) |
| **20** | **958** | **958 (100%)** |

**Verdict: CLOSABLE, with one caveat about reachability.**

Griffith's *Hymns of the Atharvaveda* (1895–96) is the only public per-hymn English translation
found that covers kāṇḍa 20. It is on sacred-texts.com at `/hin/av/av{BB}{HHH}.htm`, which is the
*same host and the same page-walk* that `scripts/fetch_griffith_yajurveda.py` already used to
snapshot 40 pages of the White Yajurveda into `data/raw/sacred_texts/2026-09-07/wyv/`.

The caveat is that **sacred-texts.com returned HTTP 403 to every probe from this environment
today** — four URLs, plain curl and full browser headers. It was reachable from this repo on
2026-09-07. So the route is proven and the host is not currently answering. Wave 1's first step
here is a reachability check, not a fetch plan.

Fallback: archive.org scans of Griffith's two volumes (`in.ernet.dli.2015.56848`,
`in.ernet.dli.2015.284068`, `dli.csl.4712`, `dli.csl.4617`). Volume 2 carries books 8–20. PD by
age, no `licenseurl` on any of them, and the cost is OCR plus a verse-boundary parser — which
can reuse the source-stated verse-count gate that `scripts/build_atharvaveda_anukramani.py`
already implements.

One discipline point. Kāṇḍa 20 is ~96% Rigvedic excerpt and our RV has 10,502 translations. The
temptation to copy them across will be strong and the result will read plausibly. If it is done
at all it must be a typed cross-reference, never a translation row.

**Dead end**: English Wikisource's "Hymns of the Atharva-Veda" is 21 pages — Book 1 and a Book 2
stub. Verified by `list=allpages`. **Not a closer**: Bloomfield's SBE 42 is a thematic selection,
not a complete translation, though it is valuable elsewhere.

### 1.2 SV Kauthuma Ārcika — 1,844 missing, every verse

**Verdict: ONE COMPLETE PUBLIC TRANSLATION EXISTS, AND IT IS THE WRONG RECENSION.**

Griffith's *Hymns of the Sāmaveda* covers all 1,875 verses of his base text. His own preface says
verbatim "I have followed Benfey's text", and the same preface identifies Benfey's edition as
**Rāṇāyanīya**. The same preface also corrects a common assumption: Satyavrata Sāmaśramī's
Bibliotheca Indica edition is Rāṇāyanīya too, so the archive.org DLI scans of it are not a
Kauthuma witness either.

Three offsets compound, and they must be handled in this order:

1. **Cross-recension.** Rāṇāyanīya text against a Kauthuma spine. `ADR-010` requires this to be
   reviewed explicitly, not absorbed.
2. **Structural.** Griffith's Book/Chapter/Decade against our keys, which are `CHANDA` 585,
   Uttarārcika `1`/`2`/`3` at 497/518/179, `ARANYA` 55 and `MAHANAMNYA` 10. His Part II has six
   Books where the Kauthuma Uttarārcika has nine prapāṭhakas.
3. **Arithmetic.** 1,875 source verses against our 1,844 — a 31-verse delta, measured locally.

The only defensible join key is the **running ārcika number**, and it has to be reconciled
against that 31-verse delta *per verse*. Get it wrong and the wrong English attaches to roughly
every verse after the first discrepancy, silently. This is the single largest correctness risk
the campaign faces.

**The highest-leverage artifact here is not the translation.** It is Benfey 1848
(`bub_gb_0C_oEB7TkVgC`, 291 pp, PD by age), which carries Griffith's own base **Sanskrit** beside
its numbering. Aligning Benfey's Sanskrit to our Kauthuma Sanskrit verse-by-verse converts the
Griffith join from an assumption into a checkable claim — the same move that made the VedSearch
audio mapping safe. Do that before ingesting Griffith.

**Dead ends, all verified**: English Wikisource has one page (still "preface only, zero verses",
17 months on) — and note that `data/registry/sources.yaml` still lists `WIKISOURCE_GRIFFITH_SV`
as `BOUNDED_PILOT_ALLOWED`, which promises coverage that source does not have. Devi Chand's
complete translation is in copyright with an explicit no-reproduction notice; the Scribd copies
are unauthorised. Stevenson 1842 is Rāṇāyanīya and Pūrvārcika-only.

### 1.3 YV Mādhyandina — 72 missing, and probably not a source gap

The 72 are scattered but concentrated: **25 of 117 in adhyāya 12**, **13 of 65 in adhyāya 23**,
and 1–4 in each of thirteen other adhyāyas. That distribution matches Griffith's own editorial
habits rather than a source lacuna: he cross-references instead of re-translating mantras
repeated from earlier adhyāyas, and he suppressed or Latinised parts of the aśvamedha dialogue in
adhyāya 23.

**Verdict: DIAGNOSE LOCALLY BEFORE SOURCING.** The snapshots for adhyāyas 12 and 23 are already
in `data/raw/sacred_texts/2026-09-07/wyv/`. The fix may be an editorial decision — render
Griffith's cross-reference, or record the absence with a reason code — rather than an
acquisition. Spending Wave 1 capacity on a new YV translation before reading two local files
would be wasted.

### 1.4 RV Śākala — 50 missing

Not investigated as a coverage problem, because 50 of 10,552 is inside the noise of the
incumbent source. What *did* turn up is a far better disagreement layer — see §6.

---

## 2. Audio — 3,376 missing

The measured shape of the gap, from `data/product/audio_discovery_report.json`:

| Veda | ours | mapped | no audio at source | verse absent at source | text mismatch |
|---|--:|--:|--:|--:|--:|
| RV | 10,552 | 10,402 | 70 | 80 | — |
| SV | 1,844 | **0** | — | 1,844 | — |
| YV | 1,975 | 1,752 | 190 | — | 33 |
| AV | 5,839 | 4,680 | 244 | 420 | **495** |

### 2.1 SV audio — 1,844 missing

**Straight verdict: NO usable public source exists for per-verse Kauthuma ārcika recitation.**
And that is a different statement from "no Samavedic recording exists", because a great deal of
Samavedic *gāna* recording exists and it is not the same object.

VedSearch holds 1,865 SV verses of *text* and **zero** with audio. The four candidates that
exist are each blocked, and each for a different reason worth recording:

| Candidate | What it is | Why it fails |
|---|---|---|
| Wikimedia Commons, 475 files, 19.14 h | **Gāna** audio, CC BY-SA 4.0 / CC0, verified per file | Only **6** of 475 files are referenced from ārcika pages. It is a melody layer, not verse recitation. |
| IISH, 64 clips, ~45 h | The whole gāna corpus, with **timestamps** | No rights statement of any kind, and `recension_unverified`. Also gāna, not ārcika. |
| Vedic Heritage (IGNCA), 158 files | Kauthuma, per the portal's own labelling | `PERMISSION_REQUIRED`; route already removed from this product by prior decision. |
| vedamu.org | Kauthuma, labelled by a competent operator | "open to listen, and not to download", in the operator's own words. Also `ECONNREFUSED` today. |

Two traps sit right next to these. `archive.org/details/sAmavedaH-kauThuma-shAkhA` has a title
that reads like exactly what the gap needs; its description says "vedamu copy of…" and its
filenames use vedamu's `{id}${name}` scheme, so it is an unauthorised mirror of a
reference-only source, and it holds 49 files of Ūha- and Ūhya-gāna rather than the ārcika.
`archive.org/details/sAmaveda-kauthuma-ignca` is a partial (87-file, two disjoint groups) mirror
of the closed IGNCA set.

**One cheap open question remains.** `shaivam.org/audio-gallery/sama-veda/` advertises "Complete
Sama Veda - Kauthuma Shakha chanting … free download" and returns HTTP 403 to automated requests
(both WebFetch and a browser-UA curl). No bypass was attempted. A human opening that page in a
browser would settle in one minute whether it is ārcika saṃhitā-pāṭha or gāna, and how it is
divided. That is the best value-per-minute item in this domain.

### 2.2 YV Mādhyandina audio — 223 missing

**Straight verdict: NO usable public source exists, and the one that would have been ideal is
confirmed dead today.**

`vedicheritage.gov.in/Yajurveda_MP3/SYMS_CHAP_{01,07,40}.mp3` all returned **HTTP 404** in this
wave. `YAJURVEDA_SOURCE_RESEARCH.md` recorded all 40 as 404 and broken since at least 2025-04;
that is still true 17 months later. No reciter was ever credited on the portal, so even a
permission request would have no resolvable consent chain. Do not re-probe.

What remains, and the trap that dominates it:

- `mAdhyandina-shAkhA-vedamu` — correct recension, adhyāyas **1–27 of 40**, five monolithic
  files, no rights metadata. No usable alignment granularity.
- **`IISHAShuklaYajurVeda`** — 55 MP3, **37.51 hours**. This is the recension trap in its purest
  form. `YAJURVEDA_SOURCE_RESEARCH.md` established that the circulating 37 h 20 m "Śukla
  Yajurveda" set is the Veda Prasar Samiti **Kāṇva** product, *proved by exactly that runtime*. A
  37.51 h match is a fingerprint. The item says only "Shukla Yajur Veda", names no reciter,
  carries no licence, and its 55 clips do not divide into 40 Mādhyandina adhyāyas. Marked
  `recension_unverified` with an active suspicion of Kāṇva; the check that settles it is to
  listen to the opening of `SYV001.mp3` against our canonical VSM 1.1, since VSM 1.1 and VSK
  1.1.1 differ.
- `shukla-yajur-vedaH-kANva-samhitA-vedamu` — **honestly labelled Kāṇva**, and recorded for that
  reason. The working rule that falls out: *any "Shukla Yajurveda" audio item that does not say
  Mādhyandina should be assumed to be this master until proved otherwise.*

Per-mantra Mādhyandina audio would have to be commissioned. That conclusion is unchanged from
the prior report and is now re-verified.

### 2.3 AV Śaunaka audio — 1,159 missing

**Straight verdict: a partial source exists, and about 43% of the gap is probably ours, not the
source's.**

The 495 `text_mismatch` verses are the story. A mismatch means VedSearch *had* audio at that
coordinate and the recited text did not match. Wave 1 should test for an AV hymn-division offset
before treating those as missing — kāṇḍa 7's Berlin-vs-Bombay split (already solved and proved
from Whitney HOS 7 p. 389 in prior work) and the kāṇḍa 19/20 boundary are the places to look.

For the genuine remainder, **Vedavani** (`huggingface.co/datasets/sanganaka/Vedavani-Dataset`,
Apache-2.0) is the one mirrorable AVŚ audio corpus: 9,997 AV samples, per-mantra or
per-hemistich segmented with Devanagari transcripts, kāṇḍas 1–13 explicitly named. Its limit is
structural rather than legal: it carries **no kāṇḍa.sūkta.mantra key**, so alignment must be
done by text matching and must be a reviewable derived layer, never asserted as source data.
Recension is Śaunaka by text match, not by publisher statement.

**Definitive negative, carried forward**: AVŚ pada-, krama-, jaṭā- and ghana-pāṭha recordings do
not exist, in the words of the only institution that would have them. Any `patha_type` other
than `SAMHITA` is currently unfillable for the AV.

### 2.4 RV audio — 150 missing, and the best new lead of the wave

**VedaWeb now serves a per-stanza Rigveda recitation with a named reciter and an institutional
custody chain** — resource `68b177c068287f35c35d7705`, `resourceType: audio`, at **stanza**
level. Its citation and description name Pt. D. P. Kinjawadekar (Pune, 1983), collected by the
Danish indologist Guni Hesting Kirchheiner (d. 2007), held and released for research by the
**National Library of Denmark** (`loar.kb.dk/handle/1902/8015`), segmented by VedaWeb.

That is unique in this entire catalogue: every other audio candidate has an unnamed reciter. And
the per-stanza segmentation is *source-provided by an academic project*, which is a stronger
alignment guarantee than anything else here.

**What is not verified: how many of the 10,552 stanzas actually carry a segment.** The resource
exists; its fill rate was not measured. Two checks before planning against it — the fill rate,
and whether its stanza keys are Aufrecht-inline for the Valakhilya. Pāṭha type is not stated, so
saṃhitā-pāṭha must not be assumed.

---

## 3. Attribution

### 3.1 Non-RV Devatā — the headline verdict

**Straight verdict: a usable public source exists for the Atharvaveda and the Samaveda. For the
Yajurveda the correct source exists, is already local, and is not mechanically resolvable.**

**AV — already on disk. This is an ingestion task, not an acquisition task.**
`data/raw/wikisource_whitney_avs/anukramani_page_manifest.jsonl` holds 1,254 pinned
`Page:`-namespace snapshots (verified gapless across both HOS volumes by `list=allpages`), and
`scripts/build_atharvaveda_anukramani.py` exists at 55,262 bytes. The brackets state ṛṣi, devatā
and metre at **hymn** scope, with per-verse metre exceptions after the colon. The chandas half is
already ingested — that is the baseline's 4,082. The devatā half is not, and the reason is a
modelling decision, not a missing file: `HAS_DEVATA` is a mantra-level edge and the source
speaks at hymn scope. That is the same type-level attribution-axis question already settled once
for the Rigveda, and it should be settled once here too.

Three properties of the source that must survive into the model: the prose books xv and xvi and
the paryāya hymns carry **metre only**, no ṛṣi and no devatā, and that is a property of the
tradition, not a transcription defect — it must be left as a typed gap. The bracket states each
hymn's verse count as a Sanskrit numeral word, which gives a free source-stated join gate. And
**kāṇḍa 20 is absent at source**, so no amount of fetching reaches its 143 hymns.

**SV — a real source, at the wrong scope.** Two artifacts, and they are complementary:

- The **Ārṣeya Brāhmaṇa** of the Kauthuma school, with Sāyaṇa's commentary, on Sanskrit
  Wikisource in 14 pages (CC BY-SA 4.0), organised as Grāmageya in 5 chapters plus Āraṇyaka
  ch. 6 in 4 subdivisions, plus **three alphabetical indices of sāman names** (a–aḥ, ka–ma,
  ya–ha). This directly corrects `SAMAVEDA_SOURCE_RESEARCH.md`'s "No verified Samaveda
  Anukramaṇī was located anywhere" — the Ārṣeya *is* the Kauthuma index of sāmans and their
  seers. Public scans with named editors also exist (`sbll_arseya-brahmana-with-commnenrary-of-sayana…`,
  `cWMF_arseya-brahmana-with-vedartha-prakasha…`, and the **Ārṣeya-pradīpa** of Bhaṭṭa Bhāskara
  Adhvarīndra), which is the route to naming an edition — the one precondition
  `SAMAVEDA_SOURCE_RESEARCH.md` identifies for freezing SV identity. Beware the adjacent
  `jaiminiya-arseya` items, which are the wrong recension.
- The **gāna pages** on Sanskrit Wikisource, which carry the triads inline, e.g.
  `( परमेष्ठी प्रजापतिः, गायत्री, सविता ।)` for the sāman *Gāyatram*, or
  `॥काशीतम् कापीतं वा सुमन्दं वा । पारावतो (पारावतिर्वा ) गायत्र्यग्निः ॥`.

Three hard things, all specific. **Scope**: the triads attach to a *sāman*, not to an ārcika
verse; asserting a sāman's devatā as its yoni-verse's devatā is a widening, and the prior report
already forbids widening a triad beyond the scope the source states. **Sandhi**: the fields are
printed compounded (`गायत्र्यग्निः` = *gāyatrī* + *agniḥ*), so a delimiter split is not enough.
**Join**: the gāna page states the running ārcika number as a link (`[…/s/3kh ९४३]`), which is
the join key to our 1,844-mantra spine — a genuine gift, and it still has to be reconciled
against the 1,844-vs-1,875 delta.

What is **not** verified: the per-sāman triad fill rate across all 726 gāna pages. Sampling
found triads on 4 of 6 substantive pages. Do not plan capacity on that ratio.

**YV — the correct source is local and is a philology problem.** Kātyāyana's
Sarvānukramaṇa-sūtra is snapshotted and was deliberately not machine-resolved. Its own opening
sūtra imposes three constraints that must shape the schema *before* any ingest:

1. `chandas` is legitimately **asserted-absent** for many yajus — *yajuṣāṃ aniyatākṣaratvād
   ekeṣāṃ chando na vidyate*. Absent is not unknown, and it needs a reason code.
2. The YV devatā co-domain **includes ritual implements** as *pratimābhūta* — cart, branch, pot,
   yoke-pin, potsherd, mortar. A shared RV/YV devatā enum would be a modelling error.
3. `ṛṣi` is **ritual-block-scoped** with *vivasvān* as the saṃhitā-wide default, so `ṛṣi` needs a
   scope field. (The existing YV ṛṣi layer, 2,106 assertions from the Wikisource `ऋषिसूची`, is
   done — 1,960 of 1,975 in the baseline. Nothing to acquire there.)

The tradition also keeps its own register of non-assignments, *anādiṣṭa-devatādayaḥ*. The
pipeline must reproduce those gaps, not fill them. No LLM was used on this source and none may
be.

The one **unchecked** YV lead worth a page-look: printed Indian editions commonly head each
mantra with ऋषिः / देवता / छन्दः / स्वरः. Weber's 1852 critical edition
(`in.ernet.dli.2015.345056`, Mādhyandina **and** Kāṇva with Mahīdhara) and the Uvaṭa+Mahīdhara
editions (`suklayajurveda`, which advertises an *index of mantras*; the Pansikar/Nirnaya Sagar
1929 printing) are the candidates. Whether any of them prints the apparatus per mantra was not
verified, and two page inspections would settle it. If one does, it is the fastest route to YV
devatā and chandas — with the caveat that a printed edition's headings are an *editorial*
apparatus, not the Sarvānukramaṇī itself, and the two can disagree; whichever is used must be
recorded as the attributing authority.

### 3.2 Chandas

SV: the most promising lead is a page nobody has read. `सामवेदः/कौथुमीया/संहिता/छन्दःपदम्`
exists — a chandas index — alongside `स्तोभपदम्` (a stobha index), `सस्वरा पूर्णा`
("complete with accents") and four `गानस्य सूची` catalogue pages. **Eleven pages, titles
verified by enumeration, contents entirely unread.** Reading them is the cheapest high-value
check left in the SV domain.

YV: as above — legitimately absent for many mantras, and needs a reason code before ingest.

AV: 4,082 of 5,839 already from Whitney's brackets. The residue is kāṇḍa 20 (absent at source)
plus the prose books, which carry metre only and should already be filled.

### 3.3 SV Rishi

Same two sources as devatā, same sāman-scope caveat. 244 distinct ṛṣis are *claimed* by one
artifact (see the warning in §7).

### 3.4 Reference sets for attribution

VedaWeb carries `Hymn Properties by Geldner (1951-1957)` whose `itemProps` are `addressee` and
`group`, grouped in the UI as "Hymn Addressee" — i.e. **Geldner's independent scholarly devatā
assignment for the Rigveda**. Our RV devatā layer is already complete (10,552/10,552), which
makes this a *validation set* rather than a coverage source, and the obvious place a disagreement
between the anukramaṇī tradition and modern philology would surface. **No non-RV analogue of this
exists.** Not in VedaWeb, and none was found anywhere.

---

## 4. Morphology and semantic roles

**Straight verdict: closable for AV, partly closable for YV, and impossible to acquire for SV.**

### 4.1 The Digital Corpus of Sanskrit is the answer, and its coverage was measured exactly

DCS (`CC BY 4.0`, verbatim from `dcs/data/conllu/readme.md`) publishes 271 corpora as CoNLL-U
with lemma, UPOS, XPOS, full morphological features, `HEAD`/`DEPREL` where the chapter is in the
Vedic Treebank, plus `LemmaId`, `Unsandhied`, `Annotator` and `WordSem` (semantic-concept ids).
Its readme also states the quality claim and its limit: "The analysis of each string has been
verified by one annotator."

Crucially, **DCS labels its own recensions**: `Atharvaveda (Śaunaka)` and
`Atharvaveda (Paippalāda)` are separate directories, `Vājasaneyisaṃhitā (Mādhyandina)` names its
śākhā, and the Śatapatha is cited internally as `ŚBM`.

**AVŚ — kāṇḍas 1–18 complete, kāṇḍa 20 absent.** The file list had to be read via the git
`trees` API, because the `contents` API caps at 1,000 entries and the directory holds 1,038 —
which would have silently hidden kāṇḍas 16–19. Hymn counts per kāṇḍa, tallied from filenames:
K1 35, K2 36, K3 31, K4 40, K5 31, K6 142, K7 118, K8 10, K9 10, K10 10, K11 10, K12 5, K13 4,
K14 2, K15 18, K16 9, K17 1, K18 4, K19 **3**. Against the true AVŚ hymn counts that is complete
for kāṇḍas 1–18 and only 3 of 72 hymns in kāṇḍa 19 — **4,428 of our 5,839 mantras (75.8%)**.

**VSM Mādhyandina — adhyāyas 1–15 of 40 only.** 29 files. The prior report's conclusion is
confirmed and still current.

**Samaveda — absent.** No Samaveda Saṃhitā entry in the 271-corpus list.

**The mapping risk is positional.** DCS files are keyed at **hymn** level
(`## chapter: AVŚ, 1, 1`) and carry **no verse number inside**; verses appear as ordered
`sent_id` blocks. Verified by inspecting one file: the first two sentences of AVŚ 1.1 are
mantras 1 and 2 in order. That works — and one hemistich split or merged sentence shifts
everything after it inside that hymn. Alignment must be gated per hymn on the sentence count
matching our mantra count, which is the same gate the AV anukramaṇī builder already implements.

### 4.2 The named trap: the annotated Atharvaveda on VedaWeb is Paippalāda

Reading all 41 VedaWeb resources gives an exact asymmetry:

- **`avp`** (Atharvaveda Paippalāda) has a `textAnnotation` resource — Zurich Edition, Zehnder
  et al. / Hellwig et al. 2024, **CC BY 4.0** — plus two plainText editions (Zurich CC BY 4.0,
  Würzburger/Kim 2025 CC BY-SA 4.0).
- **`avs`** (Atharvaveda Śaunaka) has **no annotation resource at all** — only TITUS Sanskrit
  (which carries the "No parts of this document may be republished" clause), the Whitney
  translation, and hymn titles.

So the most inviting AV annotation available, under the most permissive licence, is the wrong
śākhā. AVP numbering is not AVS numbering, and the two recensions share much material in
different order with different readings — a join would produce plausible-looking, systematically
wrong morphology. **For AVŚ morphology the source is DCS, not VedaWeb.**

### 4.3 SV morphology cannot be acquired

Three independent, comprehensive resources, all negative: DCS's 271 corpora, UD_Sanskrit-Vedic's
57 texts (only `SVidhB`, the Sāmavidhāna Brāhmaṇa) and VedaWeb's 7 texts. It would have to be
produced — and the standing rule against LLM-guessed Vedic attribution applies with particular
force, because SV verses are largely Rigvedic borrowings, which makes a wrong answer *especially*
plausible and especially hard to detect.

---

## 5. Samavedic music

**Straight verdict on notation: YES, a usable public source exists — and only one of the
candidates is machine-readable.**

This is the domain where reconnaissance paid best. The layers exist, separately, as the campaign
requires, and one source even states the principle: *"Samagana … are lines for chanting with
musical notes. These lines have no relation with the lines of saamaveda Samhita. Saamagaanam is
not singing of the samhita."*

| Layer | Source | Coverage (verified) | Format | Rights |
|---|---|---|---|---|
| **Notation, Unicode** | sa.wikisource gāna pages | 726 pages: Ūhagāna 362, Grāmageya 190, Ūhyagāna 87, Āraṇyakageya 86 | MediaWiki with **real Unicode Vedic Extensions** | CC BY-SA 4.0 |
| **Notation, scan** | `sAmagAnam` (P. R. Iyer) | GG 1–1198 in 5 vols + ĀG 1–290 + Mahānāmnī in 5 vols. **Ūha and Ūhya NOT present** | PDF, handwritten, **Malayalam script** | CC BY-NC-ND 4.0 |
| **Notation, typeset** | sanskritdocuments 4 PDFs | All four books; 2,639 gānas claimed; 1,419 pp | PDF | **© January 2025, PPN** |
| **Performance** | Wikimedia Commons | 475 files, 19.14 h, on 447 of 726 gāna pages | OGG | 459 CC BY-SA 4.0 / 16 CC0, per file |
| **Performance** | IISH, `IISHSamaVeda` | 64 clips, whole gāna corpus by the compiler's account | MP3/OGG | **none stated** |
| **Notation images** | Commons, via the gāna pages | e.g. `ग्रामगेयं १ Gramageyam 1.jpg` | JPEG page scans | per file, unchecked |

The Wikisource route is the primary one, and the reason is narrow and decisive: its notation is
in **proper Unicode** (`ओ꣢ऽ३म् । त꣡त्सवितुर्वरे꣯णियोम्`, U+A8Cx/U+A8Ex combining marks), not a
private-use font hack. Every PDF candidate is a scan or a legacy encoding. Its weakness is that
it is an unsourced community transcription, which is why the Iyer scans and the PPN PDFs matter
as collation witnesses rather than as the primary.

**And there is a text-to-audio cue index.** The `sAmagAnam` PDFs print, per gāna, the audio clip
number and an **mm:ss timestamp** into the IISH recording — the volume filenames even carry
their durations (`…GrameyaGaanam_1-180_1hr_51min_PR_Iyer.pdf`). That is the only source-provided
timing artifact found anywhere in this wave, for any Veda, which means
`FOUR_VEDA_SNAPSHOT_PROVENANCE.md` finding **F5 — "No timing or cue artifacts exist for any
audio" — is now stale for the Samavedic gāna** and should be amended rather than rediscovered.

Two cautions. The IISH recording is `recension_unverified`: probably Kauthuma, on the strength of
the Iyer parvan names and the companion Saṃhitā item's explicit "Kauthuma Samhita", but **Kerala
Samavedic tradition is substantially Jaiminīya** and nothing on `iish.org` or the archive.org
item states a recension. The check that settles it: compare a saman whose Kauthuma and Jaiminīya
renderings differ in stobha sequence — the Gāyatram on RV 3.62.10 is the standard test case —
against the Kauthuma notation in `sAmagAnam` vol. 01 at the timestamp that volume prints.
Second: gāna needs its own `work_id`. `SAMAVEDA_SOURCE_RESEARCH.md` records that it has no slot
in `sv_mantra_identity`, and at ~2,639 gānas against 1,844 ārcika verses the sung dimension is
the *larger* artifact, not a decoration on the verse skeleton.

**Named dead end in the scholarship, not the sources**: Wayne Howard's 1988 *Decipherment of the
musical notation of the Jaiminīyas* is the standard authority on Samavedic notation decipherment —
and it is about the **Jaiminīya** notation. Van der Hoogt 1929 (*The Vedic Chant Studied in its
Textual and Melodic Form*) is the Kauthuma-school counterpart; no digital copy was located.

---

## 6. Ritual — supplementary evidence corpora

**Straight verdict: richly served, and DCS plus VedaWeb do most of it under permissive
licences.** Every one of these needs its own `work_id`; none shares a key with the four
Saṃhitās.

**Start with VedaWeb's Śatapatha.** Text slug `sb`, four levels (Book/Chapter/Paragraph/
Sentence), seven resources: TITUS Sanskrit, Casaretto et al. 2021 Sanskrit, Hettrich 1988,
**Eggeling's translation 1882–1900**, Casaretto et al. 2026 annotations, and **DCS/Hellwig 2025
annotations**. Eggeling's citation string on VedaWeb names the recension verbatim —
"according to the text of the Mādhyandina School" — which is the recension that matches our VSM.
Sanskrit *and* English *and* morphology on one addressing scheme, from an API this repo already
knows how to fetch reproducibly.

**Then DCS for the bulk.** Measured coverage, as (files, bytes, citation range):

| Corpus | files | bytes | range | note |
|---|--:|--:|---|---|
| Śatapathabrāhmaṇa | 361 | 27.5 MB | ŚBM 1,1,1 → 13,8,4 | kāṇḍas 1–13 of 14 |
| Kātyāyanaśrautasūtra | 148 | 3.1 MB | KātyŚS 1,1 → 21,4 | the Śukla-YV śrautasūtra |
| Gopathabrāhmaṇa | 425 | 7.4 MB | GB 1,1,1 → 2,6,16 | complete |
| Kauśikasūtra | 242 | 5.0 MB | KauśS 1,1 → 14,5 | essentially complete |
| Vaitānasūtra | 74 | 2.3 MB | VaitS 1,1 → 8,5 | complete |
| Jaiminīyabrāhmaṇa | 519 | 9.3 MB | — | Jaiminīya recension |
| Pañcaviṃśabrāhmaṇa | 338 | 8.4 MB | PB 1,1 → 15,9 | **partial** (of 25 prapāṭhakas) |
| Drāhyāyaṇaśrautasūtra | 96 | 2.3 MB | DrāhŚS 1,1 → 15,4 | Sāmavedic |
| Sāmavidhānabrāhmaṇa | 46 | 1.3 MB | SVidhB 1,1 → 3,9 | complete |
| Ṣaḍviṃśabrāhmaṇa | 48 | 1.0 MB | ṢB 1,1 → 6,12 | |
| **Lāṭyāyanaśrautasūtra** | **2** | 33 KB | LāṭŚS 1,1–1,2 | **essentially absent** |

Plus, in the same dump: `Kauśikasūtradārilabhāṣya` and `Kauśikasūtrakeśavapaddhati` (two AV
ritual *commentaries*), `Atharvavedapariśiṣṭa`, `Aitareyabrāhmaṇa`, `Kauṣītakibrāhmaṇa`,
`Taittirīyabrāhmaṇa`, `Taittirīyāraṇyaka`, `Nirukta`, and roughly twenty Gṛhyasūtras and
fourteen Śrautasūtras. The Atharvavedic ritual apparatus is the best-served of all — Kauśika
plus Vaitāna plus Gopatha plus two commentaries.

**The named hole**: the **Kauthuma** śrautasūtra. Lāṭyāyana has two files in DCS. Drāhyāyaṇa
(the Rāṇāyanīya counterpart) is well covered, and it is not the same work.

**The join table is Bloomfield's Vedic Concordance**, and it is the highest-leverage single
artifact in this domain. Prior repo work measured, against GRETIL's *keyed* electronic version:
8,475 entries citing `VS.`, of which **3,861 also cite Śatapatha Brāhmaṇa** and **1,148 also
cite Kātyāyana Śrautasūtra**. That is a verbatim mantra→ritual-act mapping requiring no matching
and no judgement — a ready-made bridge from our VSM spine to the Śatapatha paragraphs VedaWeb
serves. Rights force a choice of the familiar shape: the convenient keyed artifact carries
GRETIL's "THIS GRETIL TEXT FILE IS FOR REFERENCE PURPOSES ONLY!", and the PD-by-age 1906 scans
(`in.ernet.dli.2015.15782`, `india.history.resource.88751`) are the OCR-cost alternative.

**A second, independent bridge exists and is gold-annotated.** UD_Sanskrit-Vedic flags
`IsMantra=True` on 14,548 tokens, concentrated exactly where it should be: BaudhŚS 2,062,
VaitS 1,331, ĀpŚS 1,319, PārGS 1,041, HirGS 974. That is a machine-readable marker of *quoted
mantra inside ritual prose*, human-validated.

**English for the rest**: Caland's *Pañcaviṃśa Brāhmaṇa* (1931, `pancavimsa-brahmana`) is the
Sāmavedic ritual authority and the thing that would make the gāna layer *intelligible* rather
than merely present — the Pañcaviṃśa is where sāmans get their ritual employment and where many
sāman names are explained. Note it goes further than the available morphology (DCS's PB stops at
15,9). Oldenberg's *Gṛhya-sūtras* SBE 29/30 (`grihyasutrasrule02olde`) supply English for six of
the Gṛhyasūtras whose Sanskrit DCS holds. Thite's and Ranade's Kātyāyana Śrautasūtra
translations exist but are modern with uploader-asserted CC0 — cite, do not ingest.

---

## 7. Scholarly disagreement

**Straight verdict: solved for the Rigveda by a single API; thin everywhere else.**

VedaWeb 2.0 carries, **at stanza level**, fifteen distinct text and translation resources for the
Rigveda: Aufrecht 1955, Eichler 2017, Elizarenkova 1989–99, Geldner 1951–57, Geraldes et al.
2023, Grassmann 1876–77, Griffith 1889–91, Lubotsky Padapāṭha 1997, MacDonell 1922, Müller 1891,
Oldenberg 1897, Otto 1948, Renou 1955–69, Van Nooten & Holland 1994, and the Zurich version of
Scarlata & Widmer 2017 — plus metrical data, Arnold/Oldenberg stanza properties and Geldner hymn
properties. **Each resource carries its own citation string**, which is the page/section locator
the campaign asks for.

Two rights warnings. This is **not one rights object**: Geldner, Renou, Elizarenkova and Otto
are modern works still in copyright, hosted under VedaWeb's own arrangements, and the API exposes
no licence field for them. Griffith, Grassmann, Müller, Oldenberg, MacDonell and Aufrecht are PD
by age. Take those first. And the mapping check that must not be skipped: our corpus numbers the
Valakhilya **inline** at 8.49–8.59 after Aufrecht; VedaWeb is Aufrecht-based so it should agree,
and this is the exact axis on which VedSearch differed and cost 55 hymns of Mandala 8.

**The main PD rival VedaWeb does not supply is Wilson**, whose six-volume *Rig-Veda Sanhita*
follows Sāyaṇa. Where Wilson and Griffith diverge, the divergence is usually
traditional-commentary against philological reading — a genuinely informative disagreement rather
than noise.

Beyond the Rigveda it thins out fast. For the AV: Whitney (incumbent), Griffith (needed anyway
for kāṇḍa 20), Bloomfield SBE 42 (thematic, with ritual extracts), and a Śaunakīya AV with
Sāyaṇa-bhāṣya *and* a Hindi translation (`yuek_shaunakiya-atharva-veda-samhita-with-sayana-bhashya…`)
whose authenticity is disputed — presence is not authenticity. For the SV: Griffith, Stevenson
1842, Benfey 1848 and Sāmaśramī's Bibliotheca Indica with Sāyaṇa — **all four Rāṇāyanīya**, all
citable, none assertable as Kauthuma. For the YV: Weber 1852 and the Uvaṭa/Mahīdhara editions.

**Named trap**: Keith's *Veda of the Black Yajus School* is **Taittirīya**, i.e. Kṛṣṇa
Yajurveda — and `en.wikisource`'s `Yajurveda` title *redirects to it*. It is legitimate as a
cross-recension comparison witness for shared mantras (which Bloomfield's concordance would
identify) and illegitimate as a VSM translation. A search for "Yajurveda translation" lands here
first.

---

## 8. Quality reference sets

**Straight verdict: one real external set exists, and the project's own gold is entirely
Rigvedic.**

**UD_Sanskrit-Vedic** (`CC BY-SA 4.0`) is the find. The 2020 LREC paper says "4,000 sentences
with 27,000 words"; the current repository, measured across all three splits in this wave, holds
**27,182 sentences / 206,440 words across 57 Vedic texts**, human-validated, with
`citation_text` labelling the recension in every sentence header — and it distinguishes **AVŚ
from AVP**, which is precisely the discrimination that matters.

| text | sentences | words |
|---|--:|--:|
| ṚV | 4,352 | 34,045 |
| **AVŚ** | **2,175** | **14,534** |
| AB | 2,018 | 15,664 |
| ŚBM | 1,239 | 8,205 |
| MS | 785 | 4,429 |
| PB | 689 | 3,923 |
| **VSM** | **622** | **3,195** |
| AVP *(the trap)* | 416 | 2,929 |
| KātyŚS | 363 | 2,518 |
| VaitS | 344 | 3,390 |
| DrāhŚS | 153 | 1,433 |
| — no Samaveda Saṃhitā at any count — | — | — |

Alongside it: **DCS** (single-annotator human verification, and `WordSem` semantic-concept ids —
a lead for the semantic-role layer), **Vedavani** (per-mantra ASR segments with Devanagari
transcripts, Apache-2.0), and **VedaWeb's** RV annotation layer (Casaretto et al. 2023–2026),
metrical data and Geldner hymn addressees.

Locally, `data/gold/` holds `rigveda_semantic_gold_v1.jsonl`, `theonym_mention_gold_v1.jsonl`
and `ask_benchmark_v1.jsonl` — **all Rigveda-only**. There is no local gold set for any non-RV
Veda in any dimension. The non-RV reference-set gap can only be filled externally, and
UD_Sanskrit-Vedic is the one candidate that fills part of it.

---

## 9. Dead ends and named traps — read this before Wave 1 plans anything

**Recension traps.** Ranked by how convincing they look.

1. **`IISHAShuklaYajurVeda`** — 55 clips, **37.51 h**, titled only "Shukla Yajur Veda". The
   runtime is the fingerprint of the Veda Prasar Samiti **Kāṇva** master. Right Veda, right
   sub-Veda, almost certainly wrong śākhā.
2. **VedaWeb's `avp` annotation layer** — the only annotated Atharvaveda on the platform, under
   **CC BY 4.0**, and it is **Paippalāda**. `avs` has no annotation at all.
3. **Keith's Taittirīya Saṃhitā** — Kṛṣṇa Yajurveda, and `en.wikisource`'s `Yajurveda` title
   redirects to it.
4. **Griffith / Stevenson / Benfey / Sāmaśramī for the Samaveda** — all four **Rāṇāyanīya**, on
   Griffith's own written testimony.
5. **Wayne Howard 1988** — the standard authority on Samavedic notation decipherment, and it is
   about the **Jaiminīya** notation.
6. **`jaiminiya-arseya` archive.org items** — sit immediately beside the Kauthuma Ārṣeya in
   search results.
7. **`shukla-yajur-vedaH-kANva-samhitA-vedamu`** — honestly labelled Kāṇva, and the working rule
   it yields: *any "Shukla Yajurveda" audio that does not say Mādhyandina should be assumed to be
   this master until proved otherwise.*

**Verified dead ends.**

- `en.wikisource` "The Sama Veda" — **1 page**. Still preface-only.
- `en.wikisource` "Hymns of the Atharva-Veda" — **21 pages**, Book 1 only.
- `vedicheritage.gov.in/.../SYMS_CHAP_*.mp3` — **404 today**, all of them. Do not re-probe.
- `sanskritdocuments.org/doc_veda/sv-kauthuma-saswara.pdf` — **still 404**.
- **`Samved.xlsx`** — the most attractive-looking SV attribution artifact in existence, and a
  broken export. Its header row promises exactly the gap: सामवेद-१८७५ / ऋषि-२४४ / छन्द-५० /
  देवता-५७ / स्वर-८. The file delivers **890 rows** carrying running numbers 1–1842 with **985
  of 1,875 absent** in 89 disjoint runs, **627 of 890 rows (70%)** with verse text spilled into
  the ṛṣi/devatā columns, **9** distinct chandas against the promised 50, and private-use-area
  codepoints (U+F186…) in place of Unicode Vedic accents. The signal is real — something
  upstream holds a complete Kauthuma table with a per-verse *musical note* — but the distributed
  file must not be ingested.
- **`Samved_Unicode_1875.pdf`** — 233 pp, text layer present and **legacy-font mojibake**
  ("साधवेड संहहटा" for "सामवेद संहिता"). Its closing pages reveal a **devotional/revelatory**
  provenance, so its attribution values cannot be classed as a traditional index at all.
- **Devi Chand's Samaveda** — in copyright, explicit no-reproduction notice.
- **Sanskrit Library's VSM TEI** — catalogued with no retrieval URL.
- `archive.org/details/sAmavedaH-kauThuma-shAkhA` and `sAmaveda-kauthuma-ignca` — unauthorised
  or partial mirrors of reference-only sources.

**Unreachable today** (record, do not assume permanence): **sacred-texts.com** returns HTTP 403
to everything, having supplied 1,903 YV translations from snapshots taken 2026-09-07;
**vedamu.org** refuses the connection (`ECONNREFUSED 182.76.20.140:443`); **shaivam.org** returns
403 to automated requests. No bypass was attempted on any of them. Any plan that assumes those
hosts must carry a reachability check as its first step.

---

## 10. Prior conclusions that are now stale

Three, and each is specific enough to check in a minute.

1. **`SAMAVEDA_SOURCE_RESEARCH.md`: "No verified Samaveda Anukramaṇī was located anywhere."**
   The Kauthuma **Ārṣeya Brāhmaṇa** with Sāyaṇa's commentary is on Sanskrit Wikisource in 14
   pages under CC BY-SA 4.0, with three alphabetical sāman indices, and exists in several public
   scans with named editors including the Ārṣeya-pradīpa of Bhaṭṭa Bhāskara. The caveat that made
   the original statement plausible still holds and is now the *mapping* risk: it indexes sāmans,
   not ārcika verses.

2. **`SAMAVEDA_SOURCE_RESEARCH.md` limitation 4: "No accented machine-readable ārcika text is
   obtainable. The only advertised one … is a dead 404."** The 404 filename
   (`sv-kauthuma-saswara.pdf`) is still 404 — re-verified. But `samaveda_kauthuma.pdf`, described
   on the *same* index page as "Samaveda Samhita (Kauthuma Shakha - Saswara)", is **live at
   1,314,334 bytes**. And a svara-bearing Kauthuma ārcika exists as **26 scanned volumes keyed by
   running verse number** (`samaveda-malayalam-…-PR-Iyer`, CC BY-NC-ND 4.0), explicitly described
   as "Kauthuma Samhita in Malayalam handwritten manuscripts with Samaveda svaras", with volumes
   named for the five Pūrvārcika kāṇḍas and then Uttarārchikam A01–A09 — the Kauthuma
   nine-prapāṭhaka division, not Griffith's six books. Neither is machine-readable yet. Both make
   the blanket negative wrong.

3. **VedaWeb is no longer "Rigveda, plus an AVS translation".** `GET /api/platform` returns
   **seven** texts: `rv`, `ab` (Aitareya Brāhmaṇa), `jb` (Jaiminīya Brāhmaṇa), `ms` (Maitrāyaṇī
   Saṃhitā), `sb` (Śatapatha Brāhmaṇa), `avs`, `avp`. Still no Samaveda and no Vājasaneyi
   Saṃhitā.

And one finding to amend rather than rediscover: **`FOUR_VEDA_SNAPSHOT_PROVENANCE.md` F5 — "No
timing or cue artifacts exist for any audio"** — is now stale for the Samavedic gāna, where the
`sAmagAnam` PDFs carry per-gāna clip numbers and mm:ss timestamps into the IISH recording.

---

## 11. Verdict table

| Gap | Usable public source? | Best candidate | Confidence |
|---|---|---|---|
| AV translation (kāṇḍa 20) | **YES** | Griffith AV, sacred-texts; archive.org scans as fallback | MEDIUM — content yes, host 403 today |
| YV translation (72) | **PROBABLY NOT NEEDED** | diagnose Griffith's own cross-references locally first | HIGH on the measurement |
| **SV translation** | **YES, WRONG RECENSION** | Griffith SV (Rāṇāyanīya) behind a Benfey-validated running-number join | MEDIUM available / LOW safe |
| RV translation (50) | not investigated as coverage | VedaWeb's 15-resource stack | — |
| RV audio (150) | **PROMISING, UNMEASURED** | VedaWeb / Kirchheiner–Kinjawadekar 1983, per stanza, named reciter | MEDIUM — fill rate unknown |
| **SV audio** | **NO** for ārcika verse recitation; **YES** for gāna | Commons 475 files (gāna, rights-clean) | HIGH on the negative |
| **YV Mādhyandina audio** | **NO** | nothing; IGNCA set confirmed 404 today | HIGH |
| **AV Śaunaka audio** | **PARTIAL** | Vedavani (Apache-2.0, no AVŚ keys); ~43% of the gap may be a mapping defect | MEDIUM |
| **Non-RV Devatā** | **YES for AV (already local) and SV; NO mechanical route for YV** | Whitney brackets (on disk); Ārṣeya + gāna triads; Kātyāyana needs philology | HIGH / MEDIUM / HIGH-negative |
| SV/YV chandas | **LIKELY** | `छन्दःपदम्` (unread); YV legitimately absent for many mantras | LOW / HIGH |
| SV ṛṣi | **YES, at sāman scope** | Ārṣeya Brāhmaṇa + gāna triads | MEDIUM |
| AV morphology | **YES** | DCS AVŚ, kāṇḍas 1–18 complete, CC BY 4.0 | HIGH |
| YV morphology | **PARTIAL** | DCS VSM, adhyāyas 1–15 of 40 | HIGH |
| **SV morphology** | **NO** | absent from DCS, UD and VedaWeb alike | HIGH on the negative |
| **Samavedic notation** | **YES** | sa.wikisource gāna pages — the only Unicode one | HIGH on format, MEDIUM on completeness |
| Samavedic performance | **YES** | Commons 475 files + IISH 64 clips with timestamps | HIGH / MEDIUM |
| Ritual | **YES, richly** | VedaWeb Śatapatha + DCS ritual corpora + Bloomfield as the join | HIGH |
| Scholarly disagreement | **YES for RV, thin elsewhere** | VedaWeb's 15 resources + Wilson | HIGH / MEDIUM |
| Quality reference sets | **PARTIAL** | UD_Sanskrit-Vedic (AVŚ 2,175, VSM 622, no SV) | HIGH |

---

## 12. What Wave 1 should do first, and it is mostly not acquisition

Six items, ordered by value per hour, and the first four cost almost nothing.

1. **Read eleven Wikisource pages.** `छन्दःपदम्`, `स्तोभपदम्`, `सस्वरा पूर्णा`, `रहस्यगानम्` and
   the four `गानस्य सूची` catalogues. They may carry SV chandas and an accented ārcika. Titles
   verified, contents unread.
2. **Read two local snapshots.** `wyvbk12` and `wyvbk23` in
   `data/raw/sacred_texts/2026-09-07/wyv/`, to settle whether the 72 missing YV translations are
   Griffith's cross-references.
3. **Diagnose the 495 AV and 33 YV `text_mismatch` verses** as a possible numbering offset before
   treating them as missing audio.
4. **Measure the VedaWeb RV audio resource's per-stanza fill rate**, and check its Valakhilya
   numbering.
5. **Re-probe sacred-texts.com.** Everything in the AV kāṇḍa-20 plan and the YV fallback depends
   on it.
6. **Then acquire**: DCS AVŚ kāṇḍas 1–18 (morphology, CC BY 4.0, clean); the Whitney devatā
   ingest (already on disk, needs a scope decision); Benfey 1848 to validate the Griffith SV
   join; VedaWeb's Śatapatha stack for the ritual layer.

Two decisions belong to a human, not to Wave 1's execution, and both are scope questions rather
than data questions: whether a hymn-scope AV devatā may become a mantra-level `HAS_DEVATA` edge,
and whether a sāman-scope SV triad may become a verse-level attribution. Both have a correct
answer and neither has an obvious one.
