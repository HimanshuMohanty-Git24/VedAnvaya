# VedaGraph Product V1 — Scope

**Version:** 1.0.0 · **Status:** local release · **Graph:** 108,779 nodes / 265,295 relationships (frozen)

This document exists to stop scope drift. Every claim VedaGraph makes is bounded by what is
written here, and the boundaries are not guessable from the product's own vocabulary: three
of the four Samhitas are partial in ways their traditional names do not reveal.

Read this before treating any count in the product as a statement about "the Vedas".

---

## 1. What the corpus is

Four Samhitas, **one recension each**. Nothing else.

| Veda | Recension held | Extent | Not held |
|---|---|---|---|
| **Rigveda** | **Śākala** | Complete: 10 maṇḍalas, 1,028 sūktas, 10,552 mantras | Āśvalāyana recension |
| **Samaveda** | **Kauthuma** | **Ārcika only** — 1,844 verses across four collections | **The gāna corpus** (roughly 2,639 gānas); Jaiminīya and Rāṇāyanīya recensions |
| **Yajurveda** | **Vājasaneyi Mādhyandina** (Śukla) | 40 adhyāyas, 1,975 mantras | **The entire Kṛṣṇa Yajurveda** (Taittirīya, Maitrāyaṇī, Kaṭha, Kapiṣṭhala); Vājasaneyi-Kāṇva recension |
| **Atharvaveda** | **Śaunaka** | 20 kāṇḍas, 731 sūktas, 5,839 mantras — held as a **working private corpus** | **Paippalāda recension** |

**No Brāhmaṇa, no Āraṇyaka, no Upaniṣad.** Every `Work` node states its own
`excluded_corpora`, and `GET /api/v1/works` returns them.

### The Samavedic exception is the one that matters most

The Samaveda is *defined* by its melodic realisation, and this corpus contains none of it.
The ārcika is the verse text; the gāna is the sung form, and it is the **larger** body. A
Samavedic figure here is therefore not a Samavedic total, and the corpus manifest says so in
its own words: *"Never describe this dataset as the complete Samaveda."*

The product renders `Samaveda Samhita` as the traditional name and
`Kauthuma ārcika only (gāna corpus NOT included)` as the display label. The traditional name
is also true; it is simply not a description of what is held. There is no field a client can
read that returns the traditional name as the display name.

---

## 2. What the knowledge layers cover

The annotation layers **do not cover the four corpora evenly, and the pattern is not
guessable.** This is the single most common way to misread this graph: a zero in one Veda
usually means the layer never reached that corpus, not that the text is silent.

| Layer | Reaches |
|---|---|
| Deity ascription (traditional, Anukramaṇī) | Rigveda only |
| Agentive semantic assertions | Rigveda only |
| Deity ascription *descriptors* | Atharvaveda only |
| Metre (chandas) | Rigveda, Atharvaveda |
| Seers (ṛṣi) | Three corpora, by two incompatible instruments |
| Translations | Rigveda 10,502 of 10,552 passages · Atharvaveda 4,878 · Yajurveda 1,903 · **Samaveda 0** |

The Rigvedic translation figure counts passages carrying any translation. Of those, 10,344
are exact mantra alignments to Griffith 1896 (98.03%) and 158 are recorded as uncertain; 52
mantras have none. No gap is ever filled from another translator, and the Samavedic zero is
measured and real.

Every endpoint that returns a per-Veda number carries a `coverage` block naming the Vedas
the layer measurably reaches and the Vedas where a zero is about the layer. Where evidence
exists but cannot support a claim, the response says `INSUFFICIENT_EVIDENCE`; where the
layer was never built, it says `NOT_BUILT`. **These two are not degrees of the same thing**
and neither is a zero.

---

## 3. What the audio covers

Audio is a **product content layer**, not knowledge. It lives in
`data/product/audio_catalog.jsonl`, keyed by canonical passage identity, and it is
**outside the frozen graph and the frozen ontology**.

Source: **[VedSearch](https://vedsearch.org/)**, which publishes **one recording per verse**.

| Veda | Recordings | Of a corpus of | Share | Recording level |
|---|---|---|---|---|
| Rigveda Śākala | **10,402** | 10,552 verses | 98.6% | **one verse each** |
| Atharvaveda Śaunaka | **4,680** | 5,839 verses | 80.2% | **one verse each** |
| Yajurveda Mādhyandina | **1,752** | 1,975 verses | 88.7% | **one verse each** |
| Samaveda Kauthuma | **0** | 1,844 verses | — | none published |

**16,834 recordings, every one mapped to a single verse and text-verified.**

### Every mapping is checked, not assumed

A recording is catalogued only when **two independent things agree**:

1. the coordinate transform places our canonical key in the source's numbering, **and**
2. the text the source states that recording recites **matches this corpus's own text** for
   that key.

That second check is why this layer can be trusted, and it is not theoretical. VedSearch
numbers Rigvedic **Mandala 8 in Griffith's order**, with the eleven Vālakhilya hymns moved
to the end of the book, while this corpus numbers them inline at 8.49–8.59 after Aufrecht.
A key-for-key mapping therefore attaches the wrong recitation to **55 hymns**: VedSearch's
8.60 is this corpus's 8.71. The transform corrects it (`vedagraph.editions.griffith_page`,
an edition fact this repository already established and tested) and the text check proves
the correction landed — **0 text mismatches across all 10,402 Rigvedic recordings.**

Text comparison is orthography-insensitive by design, because the two editions genuinely
differ on the leading ॐ, a trailing verse numeral, sandhi word-splitting, final anusvāra,
visarga, avagraha and gemination — none of which distinguishes one verse from another. The
similarity threshold is **calibrated, not guessed**: over all 1,975 Yajurvedic verses,
correctly aligned pairs score a median of **0.995**, while 400 deliberately mispaired
verses reach a maximum of **0.462**. The threshold sits at 0.90, roughly twice the worst
wrong pair.

### Four limitations, stated plainly

1. **The Samaveda has no audio at all.** The source publishes Samavedic verse text but no
   Sanskrit audio for it, and no other source located offers Kauthuma ārcika audio mapped
   to individual verses. This is the Veda for which recitation matters most, and its
   absence is a gap in what has been published anywhere — not a choice this product made.
   The Samaveda page says so rather than rendering a silent zero.

2. **The eleven Vālakhilya hymns (RV 8.49–8.59) have no recording.** The source does not
   publish them at all. Those 80 verses offer no player.

3. **Coverage is incomplete and per-Veda uneven, and every gap is accounted for.**

   | | Atharvaveda | Yajurveda | Rigveda |
   |---|---:|---:|---:|
   | Verses in this corpus | 5,839 | 1,975 | 10,552 |
   | Mapped and text-verified | **4,680** | **1,752** | **10,402** |
   | Source marks no Sanskrit audio | 244 | 190 | 70 |
   | Recited text did not match — **refused** | 495 | 33 | 0 |
   | Verse absent from the source entirely | 420 | 0 | 80 |

   Each column sums exactly to the corpus total. A refusal is recorded as a gap, never as
   a mapping: the Atharvavedic 495 are verses where the two editions' readings diverge
   beyond the similarity threshold, and attaching a recording there would have bought
   coverage with accuracy. The Atharvavedic 420 and the Rigvedic 80 are verses the source
   does not carry — the Rigvedic 80 being the Vālakhilya.

4. **Gāna is labelled, never substituted.** `AudioType.SAMAGANA` exists so that a Samavedic
   *sung* performance can never be catalogued as ārcika recitation. Nothing in the current
   catalog is gāna, and nothing is attached to a Samavedic verse.

**Coverage may be incomplete; a mapping may not be wrong.** No recording is ever attached
to a passage to improve a percentage.

### Playback and provenance

The source serves audio as **base64 inside a JSON document**, which no browser can play, so
the product's own streaming route fetches it, decodes it and serves real bytes with HTTP
Range support — addressed by catalog id, with **no parameter anywhere that accepts a URL**,
so it cannot be used as an open proxy. Nothing is stored by default; a small in-memory
window keeps seeking responsive, and `scripts/audio/cache_audio.py --veda RV` will
pre-download a corpus for offline use if wanted (gitignored, roughly 45 KB per verse).

Every record carries where it came from, what it claims to be, what it was mapped to, and
how certain that is. All 16,834 are `EXACT` **and** `text_verified`; the reader's
disclosure states in prose that the recited text was confirmed against this corpus. The
source names no reciter anywhere reached, so `performer` is null and the UI says *not
stated by the source* rather than inventing a tradition.

## 4. Recension safety

Cross-recension audio would be the worst failure this layer could produce: a Taittirīya
recitation presented as Mādhyandina, or a Jaiminīya sāman as Kauthuma, is not a coverage
gap but a false claim about the text. It is prevented structurally rather than caught in
review.

- **Derivation runs outward from our own canonical keys.** Candidate coordinates are
  computed from keys already in the graph through a fixed per-Veda transform. Nothing is
  crawled and no source index is followed, so a foreign-recension recording is not
  something that gets rejected — it is something the discovery tool cannot construct.
- **`AudioRecord` accepts exactly one recension per Veda** (`RV/SAK`, `SV/KAU`, `YV/VSM`,
  `AV/SAU`) and **raises** on any other. Taittirīya cannot be catalogued as Mādhyandina;
  Paippalāda cannot pass as Śaunaka; Jaiminīya cannot pass as Kauthuma.
- **A key is never mapped for the wrong Veda.** The transform checks the key's own Veda
  segment, not just its shape. Without that, `VG:RV:SAK:M01:S001` — five segments, the
  shape of a Yajurvedic mantra key — mapped to Yajurvedic adhyāya 1 verse 1.
- **The recited text is compared.** This is the check that catches a renumbering nobody has
  noticed, and it is what found the Mandala 8 offset described above.
- **`scripts/audio/validate_catalog.py`** re-checks all 16,834 records against the live
  graph on demand: that every key exists, that its Veda matches, that its node type is
  legal for the claimed scope, that no two verses share a recording, and that no `EXACT`
  mapping lacks its text verification. 17 checks, each phrased as the defect it prevents.
- **`scripts/audio/audit_mappings.py`** confirms mappings by a second, independent route:
  it asks the *audio* endpoint what the file itself recites and compares that against this
  corpus, rather than re-reading the listing the catalog was built from. Its sample always
  includes the five Mandala 8 keys where a permutation error would hide. Last run: **31 of
  31 confirmed, 0 wrong**, median similarity 1.000.

## 5. Ask VedaGraph: what a citation means

Ask VedaGraph is **evidence-grounded and textual**. Retrieval runs first and the model sees
only what retrieval found, so:

- every factual claim carries a citation into the graph;
- an unanswerable question returns `INSUFFICIENT_EVIDENCE` rather than a confident denial;
- a citation points at a passage or an assertion **that exists**, and invented citations are
  measured at zero;
- the synthesis backend is a configuration choice, and no credential is ever returned.

**A citation is evidence that the graph records something, not that the tradition asserts
it.** Interpretive claims are labelled as interpretation and are never presented as
deterministic fact.

The model is **never given audio**. Audio is not part of Ask's evidence in Product V1.

Final benchmark over 60 questions: 36 supported-correct, 8 partial, 16 correctly refused,
**0 misleading, 0 hallucinated**, 279 citations, 0 invented citations surviving.

---

## 6. What Product V1 deliberately does not do

- No accounts, authentication or subscriptions.
- No vector database and no embedding retrieval.
- No multimodal reasoning; Ask is text and graph only, and is never given audio.
- No redistribution of third-party audio. Recordings are fetched from their source per
  request and nothing is stored unless the cache tool is run deliberately.
- **No audio sub-verse.** Recordings are one per verse, which is the finest granularity any
  source publishes; there is no word- or pāda-level timing and none was invented.
- No Samavedic audio, because none is published (see §3).
- No Brāhmaṇa, Āraṇyaka or Upaniṣad ingestion.
- No second recension of any Veda.

---

## 7. Absence semantics, in one paragraph

If VedaGraph shows you nothing, ask **whose** nothing it is. `NOT_BUILT` means the layer
does not exist here and the silence is ours. `INSUFFICIENT_EVIDENCE` means evidence exists
and cannot support the claim — it is **not** a zero and must never be rendered as one.
`PARTIAL` means a real answer over part of the corpus, one Veda, or one evidence mode. An
empty audio panel means no recording is mapped, which is never evidence that no recitation
exists. The product is built so that none of these can be reached by accident: an empty
first page claiming `SUPPORTED` raises rather than renders.
