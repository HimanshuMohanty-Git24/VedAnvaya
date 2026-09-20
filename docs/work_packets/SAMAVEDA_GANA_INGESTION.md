# Work Packet: Sāmaveda Gāna Ingestion

**Proposed work:** a NEW `work_id` for the Kauthuma **gāna** collections. It does not exist yet and
this packet does not create it.
**Not:** `VG:WORK:SV:KAU`. That work is the **ārcika** only — 1,844 canonical verse keys over
1,875 printed verse-terminal markers, sourced from 106 Wikisource pages.
**For:** a future agent assigned the gāna phase.
**Produced by:** Agent B3, 2026-09-07, measurement run only. Nothing was ingested, snapshotted,
modelled or downloaded.

**This packet does not solve the problem. It measures the body of work and hands it off.**

---

## 0. The one-line reason this exists

`VG:WORK:SV:KAU` holds the ārcika. The gāna is a **parallel and larger** body that this work_id does
not cover and cannot address. **Any claim that VedaGraph "has the Sāmaveda" while holding only the
ārcika is FALSE** — this is already recorded verbatim as a SCOPE LIMIT in `data/registry/works.yaml`
under `VG:WORK:SV:KAU`, and this packet is the measured backing for it.

---

## 1. Scope: what the gāna corpus is

The ārcika is a collection of **verse texts** (`ṛc`). The gāna is the collection of **melodies**
(`sāman`) those verses are sung to, written out as fully-texted chants with stobha syllables,
repetitions, insertions and the Devanāgarī-Extended svara notation. One ārcika verse yields many
sāmans; the gāna books are therefore *larger* than the verse skeleton they sing.

Recorded scale, carried consistently across `works.yaml`, `docs/FOUR_VEDA_STRUCTURAL_MODEL.md`,
`docs/FOUR_VEDA_RIGHTS_MATRIX.md` and the count ledger: **roughly 2,639 gānas against 1,875 ārcika
verses.** The count ledger records the independent corroboration for the 2,639 figure (a 2013
Kannada essay on `सम्भाषणम्:सामवेदः/राणायनीया` giving `ṛk = 1875, sāma = 2639`). This packet did
**not** re-derive 2,639 and does not attempt to; deriving a gāna count requires parsing gāna page
content, which is out of scope here. What it does establish is that **pages are not gānas** — see
§3.4 — so 2,639 cannot be read off the page inventory.

**Why this is not a decoration on the verse skeleton.** The registry already states the reason in
three places: *the sung dimension is the reason the Sāmaveda is a distinct Veda rather than a
Rigveda excerpt.* The ārcika's verse text is largely shared with the Rigveda (this project has not
measured the overlap and no figure for it is recorded here — do not quote one). What the Sāmaveda
uniquely transmits is the **melodic realisation**, and that is exactly the layer `VG:WORK:SV:KAU`
does not contain. It is also the layer with **no competing digital source**: the GRETIL Kauthuma text has
ZERO gāna content, and everywhere else the gāna is PDF-only or absent. Sanskrit Wikisource is the
only route.

---

## 2. Why the gāna needs its OWN `work_id`

Four independent reasons, each sufficient on its own:

1. **Different citation space.** An ārcika address is `collection / prapāṭhaka / ardha / daśati /
   verse`. A gāna address is nothing like it — the ūha and ūhya books are organised by **ritual
   occasion** (`ekāha`, `ahīna`, `sattra`, `dvādaśāha`/`daśarātra`, `saṃvatsara`, `kṣudra`,
   `prāyaścitta`), not by prapāṭhaka. Measured level-5 node vocabulary is in §3.3. Forcing gāna
   coordinates into `SV_COLLECTION_LEVELS` would require inventing levels the witness does not
   declare — precisely the defect the current Sāmaveda key was rebuilt to remove.
2. **Different unit of identity.** The ārcika's canonical unit is a verse. The gāna's canonical unit
   is a *sāman* (a named melody), which is neither a verse nor a container of verses.
   Many-to-many: one verse sings under many sāmans; one sāman may carry several verses.
3. **Different cardinality.** ~2,639 gānas against 1,844 ārcika keys. Adding them under one work_id
   would make the majority of that work's passages not be what the work's `key_pattern`,
   `hierarchy` and `citation_pattern` describe.
4. **Different rights profile in one respect that matters.** The text layer is the same
   CC BY-SA 4.0 Wikisource transcription, but the **audio** aligns to gāna pages, not to ārcika
   passages (§4). The audio artifact is currently registered against `VG:WORK:SV:KAU` and, measured,
   **472 of its 475 files reference no ārcika page at all**. That row is misfiled today.

### 2.1 What is UNDECIDED about gāna identity — open questions, not answers

**Do not treat any of these as settled. This packet deliberately decides none of them.**

- **Q1. What is the canonical unit?** The named sāman? The (sāman × ārcika-verse) pair? The gāna
  page? Each gives a different corpus size and a different collision profile.
- **Q2. Is `sāman name` a stable identifier?** Measured evidence says be careful: the audio file set
  alone contains `आकूपारम्(परित्यं)`, `आकूपारम्(पुरोजितीवो)` and `आकूपारम्(प्रसुन्वाना)` — the same
  sāman name disambiguated only by an incipit in parentheses. A bare name is not unique.
- **Q3. Is the incipit-in-parentheses convention part of the name or part of the address?** The
  witness uses it in both page titles and file names, but not uniformly.
- **Q4. Four books or five?** The recorded split says `uhya/rahasya` is one thing. The witness
  disagrees: `ऊह्यगानम्` is an 87-page subtree and `रहस्यगानम्` is a **separate single page**
  (pageid 93478, 454,392 bytes, no children). Whether these are two names for one book, or one book
  and one alternate whole-book transcription, is UNRESOLVED — see §3.2.
- **Q5. How is the ūha's ritual-occasion axis modelled?** `parvan → viṃśa/daśati → sāman` is the
  measured shape in ūhagāna, and `parvan → daśati → sāman` in ūhyagāna. Whether `parvan` is a
  container level or a ritual annotation is undecided.
- **Q6. Grāmageya's split prapāṭhakas.** The page tree carries `प्रपाठकः ०३क` / `०३ख` and
  `प्रपाठकः १२क` / `१२ख` — a transcriber's pagination split, not a traditional level. Whether the
  canonical address has 17 prapāṭhakas or 19 nodes is a *source-artefact* question, and the answer
  must NOT be read off the page tree.
- **Q7. `महानाम्न्यार्चिकः` appears INSIDE the āraṇyakageya subtree** (under `परिशिष्टः`). An
  ārcika collection name inside the gāna tree. Cross-boundary; unexplained; do not assume it is a
  mistake.
- **Q8. How does a gāna passage BIND to an ārcika passage?** The link is the reason to build this at
  all, and it is a derived, reviewable relation — never source data. It must not be asserted from
  name-matching alone (see Q2).
- **Q9. Does the gāna work get its own `SamavedaCollection`-style named-collection enum, or reuse
  and extend the existing one?** Reusing it would put gāna books into an enum whose docstring is
  explicitly about the *verse* collections.

---

## 3. Measured inventory

All figures below were **measured on 2026-09-07** by `scripts/inventory_samaveda_gana.py` against
the live MediaWiki APIs. Figures labelled *recorded* come from
`data/registry/source_artifacts.yaml` and are reproduced for comparison only.

### 3.1 Wikisource page inventory

Enumeration basis, stated so the set is reproducible: **every namespace-0 page on
`sa.wikisource.org` whose title begins `सामवेदः/कौथुमीया/संहिता/`**, via `list=allpages`, plus the
parent page `सामवेदः/कौथुमीया/संहिता` (pageid 11933, 5,711 bytes, references no files).

| Section | Recorded | **Measured** | Δ |
|---|---:|---:|---|
| Kauthuma Saṃhitā pages, total | 840 | **840** (839 subtree + 1 parent) | **0 — confirmed** |
| ārcika (pūrvārcika 74 + uttarārcika 32) | 106 | **106** | **0 — confirmed** |
| grāmageya | 190 | **190** | 0 |
| āraṇyakageya | 86 | **86** | 0 |
| ūhagāna | 362 | **362** | 0 |
| ūhyagāna | 87 | **87** | 0 |
| *recorded gāna subtotal* | *725* | *725* | 0 |
| **rahasyagāna** | *(not listed separately)* | **1** | **+1, NAMED NOT RECONCILED** |
| **gāna total** | 725 | **726** | **+1** |
| ancillary (4 sūcī indexes, `छन्दःपदम्`, `स्तोभपदम्`, `सस्वरा पूर्णा`) | *(not listed)* | **7** | — |

106 + 726 + 7 = 839, + 1 parent = 840. **The recorded four-book split is confirmed exactly.** The
single difference is `रहस्यगानम्`, which the recorded split folds into "uhya/rahasya" but which the
witness carries as a distinct node. **Reported, not reconciled** — see Q4.

### 3.2 Redirects: 66 of the 733 non-ārcika pages are NOT content

This is new and it is load-bearing for any future page-count estimate.

| Book | Pages | Redirects | **Content pages** |
|---|---:|---:|---:|
| grāmageya | 190 | 14 | **176** |
| āraṇyakageya | 86 | 24 | **62** |
| ūhagāna | 362 | 5 | **357** |
| ūhyagāna | 87 | 21 | **66** |
| rahasyagāna | 1 | 0 | **1** |
| **gāna total** | **726** | **64** | **662** |
| ancillary | 7 | 2 | 5 |

**Anyone quoting "725 gāna pages" as the size of the ingestion job is over by 64.** The real content
surface is **662 pages / 3,402,720 bytes of wikitext**, of which the single `रहस्यगानम्` page is
454,392 bytes (13%) — one page holding what is elsewhere a whole book.

### 3.3 The gāna page tree has no uniform coordinate

Title depth (slash-separated segments) per book, measured:

| Book | depth 4 | 5 | 6 | 7 |
|---|---:|---:|---:|---:|
| grāmageya | 1 | 32 | 157 | 0 |
| āraṇyakageya | 1 | 12 | 13 | 60 |
| ūhagāna | 1 | 8 | 49 | 304 |
| ūhyagāna | 1 | 7 | 15 | 64 |

Level-5 node vocabulary (the level immediately under the book):

- **grāmageya** — 17 prapāṭhakas, but expressed as 19 nodes because of the `०३क/०३ख` and `१२क/१२ख`
  splits, plus a stray 182-byte `प्रपाठकः ०३`, plus orphan `साम NNN` pages sitting at book level
  instead of under a prapāṭhaka.
- **āraṇyakageya** — 21 distinct nodes: prapāṭhakas 1–6 (with `२.१`/`२.२` split and `षष्ठःप्रपाठकः`
  spelled out *alongside* `प्रपाठकः ६`), a `परिशिष्टः` appendix, and loose `अर्कपर्व`,
  `द्वन्द्वपर्व`, `शुक्रियपर्व`, `वाचोव्रतपर्व`, `साम NN` nodes.
- **ūhagāna** — 7 parvans: `दशरात्रपर्व` 237, `संवत्सरपर्व` 29, `एकाहपर्व` 27, `अहीनपर्व` 25,
  `सत्रपर्व` 19, `क्षुद्रपर्व` 15, `प्रायश्चित्तपर्व` 8 (+ 1 index page).
- **ūhyagāna** — the same 7 parvans: `दशरात्रपर्व` 48, `संवत्सरपर्व` 19, `अहीनपर्व` 6,
  `एकाहपर्व` 5, `प्रायश्चित्तपर्व` 3, `सत्रपर्व` 3, `क्षुद्रपर्व` 2.

**This is the same hazard the ārcika already hit and already documented:** the registry note on the
ārcika warns that "the dotted address is NOT a uniform coordinate: slot 3 means prapathaka under
1.1.x, dasati under 1.2.x and ardha under 2.x.y." The gāna tree is worse — depth varies 4→7 within
a single book, and the ūha books use a ritual-occasion axis the grāma/āraṇyaka books do not have.
**Do not derive a gāna coordinate from the page path.**

### 3.4 Pages are not gānas

662 content pages against a recorded ~2,639 gānas is roughly **4 gānas per page**, and the
distribution is extremely uneven (one page carries an entire book). A gāna count can only come from
parsing page *content*, which this run deliberately did not do.

### 3.5 Audio inventory

Enumeration basis: **every file transcluded on any page of the Kauthuma Saṃhitā subtree**
(`prop=images`, `imlimit=max`, continuation-merged), filtered to `.ogg`, then resolved against the
Commons `imageinfo` API. The page-reference route — not a Commons category — is the basis, because
it is the route that *produces* the PAGE_LEVEL alignment the artifact record claims.

| Fact | Recorded | **Measured** | Δ |
|---|---:|---:|---|
| distinct `.ogg` | 474 | **475** | **+1** |
| referencing Saṃhitā pages | 444 | **450** | **+6** |
| CC BY-SA 4.0 | 458 | **459** | **+1** |
| CC0 1.0 | 16 | **16** | 0 |
| missing a licence | 0 | **0** | 0 |
| uploader `Seetharaman G.K.` | 317 ("Seet…") | **319** | **+2** |
| uploader `Puranastudy` | 157 | **156** | **−1** |
| Credit | "Own work" | **"Own work" on all 475** | 0 |
| reciters named per file | no | **no — `Artist` is the uploader account, not a reciter** | 0 |

**Differences are named, not reconciled.** The registry figures carry `retrieval_date: 2026-09-07`,
the same day as this measurement, so same-day wiki drift cannot be assumed as the explanation. The
uploader split moving in *opposite* directions (+2 / −1) is not consistent with a pure net addition
of one file, and is the strongest signal that the two enumerations were not scoped identically.
Recording both, adjudicating neither.

Further measured facts not previously recorded:

- **472 of the 475 files reference at least one gāna page. Exactly 3 reference only an ārcika page**
  — `आज्यस्तोत्रम्` II, III and IV, all three from
  `.../उत्तरार्चिकः/2.1 प्रथमप्रपाठकः/2.1.1 प्रथमोऽर्द्धः`. A fourth (`आज्यस्तोत्रम् (प्रथम)`)
  straddles grāmageya and uttarārcika.
- **7 files are referenced from more than one page** (up to 4). A file→passage mapping is therefore
  *not* a function; it is many-to-many.
- **447 of the 662 gāna content pages carry audio (67.5%). 215 do not.** By book:
  grāmageya 97/176, āraṇyakageya 40/62, ūhagāna 264/357, ūhyagāna 46/66, rahasyagāna **0/1**.
  **The audio does not cover the corpus.**
- Total **808,529,118 bytes (~771 MiB), 19.14 hours** of Ogg Vorbis, `application/ogg`, mediatype
  `AUDIO`, across 475 files.
- Upload years: 2018 ×1, 2019 ×11, **2020 ×255, 2021 ×182**, 2022 ×9, 2023 ×1, 2024 ×16.
- All 16 CC0 files were uploaded by `Seetharaman G.K.`; `Puranastudy` uploaded no CC0.
- Commons category cross-check (`.ogg` members only, secondary evidence only):
  `Category:Audio files of Samaveda` 441, `Category:Uhaganam` 270, `Category:Gramageya` 97,
  `Category:Uhyaganam` 46, `Category:Samaveda` 12. **The categories do not span the set** — 441 <
  475 — which is why they were not used as the enumeration basis.

### 3.6 The collection-level digest the artifact record is missing

The record for `COMMONS.SV.KAU.SAMAN.AUDIO` says *"not yet snapshotted by Agent E, so no
collection-level checksum is recorded."* One is now available:

```
collection_digest_sha256 = 4001c9d4fe41ac11879f0b850f2bbc36e9733047b56967b7586ba78f724eed41
```

**Definition, stated so it is reproducible and so it cannot be mistaken for something it is not:**
sha256 over the UTF-8 encoding of `f"{file_name}\t{sha1}\n"` for every file in the collection,
ordered by `(file_name, sha1)`, where `file_name` is the Commons title with the `File:` prefix
removed. Files with no Commons `sha1` contribute an empty digest field rather than being dropped, so
a disappearance changes the digest instead of hiding.

**It is a digest OF THE API'S METADATA, NOT OF THE AUDIO BYTES.** The per-file `sha1` values it is
built from are the MediaWiki API's own digests. `checksum_sha256` in `source_artifacts.yaml` means
sha256-of-bytes. **These are different algorithms over different inputs and must not be conflated.**
Every row of the audio inventory carries `"sha1_is_not_sha256": true` and
`"sha256_of_bytes": null` so no downstream reader can make that mistake silently. The digest is fit
for change-detection over the collection; it is not fit as a byte-integrity checksum.

---

## 4. Rights

### 4.1 Text

The gāna pages are the **same artifact and the same licence** as the ārcika pages:
`WIKISOURCE_SA.SV.KAU.SAMHITA.DEVANAGARI`, CC BY-SA 4.0, taken from the MediaWiki
`action=query&meta=siteinfo&siprop=rightsinfo` endpoint rather than a scraped footer. **No new
rights investigation is needed for the gāna text.** Two carried-over constraints:

- CC BY-SA 3(a)(1)(A)(iii) URI retention: the source is mutable, so every snapshot must pin its own
  `revid` and `sha256`. The page inventory already records the current `revid` for all 733 rows.
- The open blocker dimension `independence_codepoint_reverification` on the ārcika applies here too:
  the redistribution basis is CC BY-SA **on the transcription**, so the Pandey-lineage independence
  question must be re-verified at codepoint level before any bulk text release. Note the gāna is
  *easier* here, not harder — **GRETIL has zero gāna content**, so there is no Pandey-lineage text to
  have descended from for this layer.

### 4.2 Audio — the CC BY-SA / CC0 split and what it obliges

Measured: **459 CC BY-SA 4.0, 16 CC0 1.0, 0 missing.** These are **per-file** licences, read
individually from `extmetadata`, not inferred from Commons' general terms.

- **The collection must NOT be flattened to one licence.** 16 files carry a CC0 dedication and 459
  carry share-alike. Applying one blanket licence to the collection would be wrong in both
  directions: it would strip the CC0 files of their public-domain status, or it would misrepresent
  the CC BY-SA files as unencumbered.
- **Per-file attribution is obligatory on the 459.** `AttributionRequired: true`, `UsageTerms:
  "Creative Commons Attribution-Share Alike 4.0"`. The attributable party is the **uploader account**
  (`Seetharaman G.K.`, `Puranastudy`) with Credit `Own work`. **Reciters are not named anywhere**, so
  attribution can name the uploader and must not invent a performer.
- **Share-alike is viral** (`rights.yaml` → `CC_BY_SA.conditions`: *"Derived artifacts must
  themselves be released under CC BY-SA. This is viral: mixing CC BY-SA text into an aggregate
  output constrains the licence of that output."*). Any VedaGraph artifact that embeds or adapts
  these files inherits CC BY-SA.
- **These 16 files remain the registry's only CC0 material.** `data/registry/rights.yaml` still
  carries the stale comment that CC0 is *"documented and available, but unused"* and
  *"Currently unused."* That is no longer true — see §7.

### 4.3 The four-Veda release is NOT licensable as a single adapted work

This is a recorded consequence, not a new opinion. From `data/registry/rights.yaml`:

- `CC_BY_SA` — *"Derived artifacts must themselves be released under CC BY-SA."*
- `CC_BY_NC_SA` — *"Derived artifacts must be released under CC BY-NC-SA. Permanently forecloses
  commercial licensing of any output that incorporates this text."*

And from the per-Veda matrix: the **Rigveda primary** (GRETIL Aufrecht TEI) is `CC_BY_NC_SA`, while
the **Sāmaveda and Śukla Yajurveda primaries** (Sanskrit Wikisource) are `CC_BY_SA`. Two viral
share-alike conditions demanding two *different*, mutually non-interoperable target licences cannot
both be satisfied by one output. **A combined four-Veda corpus therefore cannot be released as a
single adapted work.** The gāna phase does not change this and does not fix it; the practical
consequence is that gāna outputs must be released as a **separately licensed CC BY-SA artifact**,
never merged into a single blob with the Rigveda text layer.

### 4.4 Mirroring the audio bytes: PERMITTED, and DEFERRED here — with the reason

Mirroring is **permitted** by the registry (`CC_BY_SA.mirror_public: yes`, `CC0.mirror_public: yes`),
conditional on per-file attribution and share-alike. It was **not done in this run, and the reason is
not caution — it is that there is nowhere to put the result:**

> These 475 files align to **gāna pages**. No gāna `work_id` exists, and therefore **no gāna Passage
> exists**. A byte-level mirror produced today would yield 475 audio records whose `passage` target
> is null. That is not a partially-built layer; it is 771 MiB of orphan blobs plus an alignment table
> pointing at nothing, which the referent-binding gate exists to prevent.

Consequences of the deferral, stated plainly:

- **No sha256-of-bytes exists for any file.** It cannot: sha256 requires the bytes. The Commons
  `sha1` recorded per row is the closest available substitute and is explicitly not the same thing.
- **No local byte-level mirror exists**, so `checksum_sha256` on `COMMONS.SV.KAU.SAMAN.AUDIO` must
  stay absent. The collection digest in §3.6 closes the *"no collection-level checksum is recorded"*
  gap without pretending to close the byte-integrity gap.
- Mirroring is the **first task of the future phase after** a gāna passage spine exists — §8, task 8.

### 4.5 Alignment granularity: PAGE_LEVEL. Full stop.

The artifact record's claim is confirmed by measurement: alignment is **PAGE_LEVEL and
SOURCE_PROVIDED** — each file is transcluded on a specific Wikisource page. Every row of the audio
inventory carries `"alignment_granularity": "PAGE_LEVEL"`.

**There are no mantra-level timestamps and none were invented.** The Commons API exposes a file
`duration` (recorded, and summing to 19.14 h) and nothing finer. There is no cue sheet, no
segmentation, no per-sāman offset. **A future phase must not synthesise timings and call them
source data.** Compare `VEDAVANI.AV.SAUNAKA.WAV.HF`, where per-mantra granularity *is* real but the
registry still requires the AVS mapping to be a REVIEWABLE DERIVED layer — the same discipline
applies here, one level coarser.

**Authority caveat, carried forward unchanged:** recitation authority is LOWER than IGNCA/VHP's.
These are community contributions, `Own work`, reciters unnamed. The choice between authority (VHP,
`PERMISSION_REQUIRED`, unmirrorable) and usability (this, mirrorable) is a **curation decision, not
a rights decision**, and must be made deliberately.

---

## 5. What is already reusable

The gāna phase does not start from zero. These exist, are proven on the ārcika, and transfer:

1. **The pinned-snapshot machinery.** `data/raw/wikisource_sa/2026-09-07/` holds 106 ārcika pages,
   each content-addressed by sha256 with a metadata sidecar recording `retrieval_url`,
   `http_status`, `retrieved_at`, `snapshot_id` and `source_id`. The `action=parse&prop=wikitext|revid`
   call pattern, the `WIKISOURCE_SA` registered `source_id`, and the CC BY-SA revid-retention
   discipline all apply unchanged to the 662 gāna content pages. **This is a volume change, not a
   method change.**
2. **The referent-binding gate** (`src/vedagraph/referent.py`). This is the mechanism that actually
   prevents the failure mode this corpus is prone to — a canonical key silently coming to denote a
   different occurrence. Its own docstring records why: *"a null key_pattern did NOT prevent 139
   passages being materialized at status CANONICAL"*; what stops that is the gate, not a missing
   declaration. Any gāna key must be gated from the first build, not retrofitted.
3. **The identity module's collection-NAMING approach** (`src/vedagraph/identity.py`,
   `SamavedaCollection` / `SV_COLLECTION_LEVELS`). The transferable insight is the *method*, not the
   enum: **name the collection instead of numbering it**, because a bare ordinal is not referent-
   stable when witnesses disagree about the top level's arity; and **omit a level a collection does
   not declare rather than writing a literal `0`**, because writing `0` makes an edition's
   flattening choice part of canonical identity. Both apply directly to the gāna, whose books
   declare *different* intermediate levels from each other (§3.3).
4. **The Sāmaveda count-reconciliation method** (`data/source_registry/samaveda_count_ledger.yaml`,
   `docs/reports/SAMAVEDA_COUNT_RECONCILIATION.md`). The 1875-vs-1868 reconciliation is the template
   for the eventual gāna-count reconciliation against the recorded ~2,639.
5. **The two inventories written by this run** —
   `data/source_registry/samaveda_gana_page_inventory.jsonl` (733 rows, every non-ārcika Saṃhitā page
   with pageid, current revid, byte size, book and redirect flag) and
   `data/source_registry/samaveda_gana_audio_inventory.jsonl` (475 rows). The page inventory is
   directly usable as the fetch worklist.
6. **The script** `scripts/inventory_samaveda_gana.py` — re-runnable, `ruff` clean, `mypy --strict`
   clean, no bytes downloaded, POST-batched (Devanāgarī titles overrun the URI length limit at 50
   per GET; the script POSTs instead).

---

## 6. Explicit non-goals for this phase

This packet's phase produced measurements only. The following were **deliberately not done** and
must not be inferred from anything above:

- **No gāna `work_id` was created**, proposed in concrete form, or reserved.
- **No gāna identity scheme, key pattern, hierarchy or URN was designed.** §2.1 lists open questions
  and answers none of them.
- **No gāna text was ingested, snapshotted, parsed or transcribed.** All 733 page rows carry
  `"content_snapshotted": false`.
- **No audio bytes were downloaded.** No sha256-of-bytes exists; none is claimed.
- **No mantra-level or timestamp alignment was produced.** PAGE_LEVEL is the ceiling of what the
  source provides.
- **No gāna count was derived.** ~2,639 is a *recorded* figure carried forward, not re-measured.
- **The 474/444/458 vs 475/450/459 differences were NOT reconciled**, only named.
- **No registry file was edited.** Requests are in §7 for the registry owner to action.

---

## 7. Registry updates requested (NOT made by this packet)

For the registry owner. Each is a factual correction or addition backed by a measurement above.

1. **`data/registry/source_artifacts.yaml` → `COMMONS.SV.KAU.SAMAN.AUDIO`**
   - Add `collection_digest_sha256: 4001c9d4fe41ac11879f0b850f2bbc36e9733047b56967b7586ba78f724eed41`
     **in a field distinct from `checksum_sha256`**, with the §3.6 definition inline and the explicit
     statement that it digests API metadata, not bytes. `checksum_sha256` must remain absent.
   - Amend `provenance_notes`: replace "474 distinct .ogg referenced from 444 Kauthuma Samhita pages"
     with the measured 475 / 450, keeping the recorded figures and the unreconciled delta visible
     rather than overwriting them. Same for the licence split (458 → 459 CC BY-SA; CC0 stays 16) and
     the uploader split (317/157 → 319/156).
   - Record that **472 of 475 files reference a gāna page and only 3 reference an ārcika page alone**,
     and that 7 files are multi-page — so the file→passage relation is many-to-many.
   - Record **447 of 662 gāna content pages carry audio; 215 do not.** The set is not complete
     coverage.
   - **`work_id` is wrong today.** The row is filed under `VG:WORK:SV:KAU`, which is ārcika-only,
     while 99.4% of its files reference gāna pages. Re-point it when the gāna work_id exists;
     until then add an explicit note that the filing is provisional.
   - Add measured totals: 808,529,118 bytes, 19.14 hours, all `application/ogg`.

2. **`data/registry/source_artifacts.yaml` → `WIKISOURCE_SA.SV.KAU.SAMHITA.DEVANAGARI`**
   - The 840 / 106 / 725 (190/86/362/87) figures are **confirmed exactly** — worth recording as
     independently re-measured on 2026-09-07.
   - Add the one difference: **`रहस्यगानम्` is a 726th non-ārcika page**, a separate single page
     (pageid 93478, 454,392 bytes), not a subtree of `ऊह्यगानम्`. The recorded "uhya/rahasya"
     conflation should be flagged as unadjudicated.
   - Add the **64 redirects** finding: the gāna surface is **662 content pages**, not 725/726.

3. **`data/registry/rights.yaml` → `CC0` entry.** The comment at the head of the file and the
   `conditions` text both still say CC0 is *"Currently unused."* **It is used** — 16 Commons Sāmaveda
   `.ogg` files carry CC0 1.0. This is the second stale-claim of exactly the kind the memory note
   *"Stale-claim audits falsely certified absence twice"* warns about, and it should be corrected.

4. **`data/registry/works.yaml` → `VG:WORK:SV:KAU` SCOPE LIMIT note.** No change to its substance —
   it is correct and this packet backs it. Optionally add a pointer to
   `docs/work_packets/SAMAVEDA_GANA_INGESTION.md` and to the two inventory files.

5. **No new `work_id` is requested yet.** Creating one is task 1 of §8 and needs Q1–Q9 answered
   first.

---

## 8. Ordered task list for the future run

Strictly ordered. Each task's output is the next task's input.

1. **Adjudicate Q1–Q9 (§2.1) on evidence, and write the ruling down before writing code.** Priority
   order: Q1 (canonical unit) → Q4 (four books or five) → Q2/Q3 (sāman-name stability) → Q5/Q6
   (level vocabulary) → Q7 (mahānāmnya cross-boundary) → Q9 (enum reuse) → Q8 (ārcika binding).
   Q8 last: it is a *derived relation* and must not constrain identity.
2. **Register the gāna `work_id` in `data/registry/works.yaml`** with
   `identity_status: RESEARCH_REQUIRED` and `key_pattern: null`, and — learning the recorded lesson —
   **stand up the referent-binding gate at the same moment**, because a null `key_pattern` has
   already been shown not to prevent premature CANONICAL materialisation.
3. **Snapshot the 662 gāna content pages** using the existing `data/raw/wikisource_sa/` machinery and
   the `WIKISOURCE_SA` source_id, one sha256 + revid per page. Drive it from
   `samaveda_gana_page_inventory.jsonl`, **skipping the 64 redirect rows** and re-checking `revid`
   against the inventory to detect drift since 2026-09-07. Budget ~3.4 MB of wikitext.
4. **Decide `रहस्यगानम्` before parsing it.** 454 KB on one page is either a fifth book or a
   duplicate of `ऊह्यगानम्`; parsing it under the wrong assumption either doubles or halves the
   corpus.
5. **Parse and count.** Produce a measured gāna count and reconcile against the recorded ~2,639
   using the method already proven in `SAMAVEDA_COUNT_RECONCILIATION.md`. Expect the answer to be
   *near* 2,639 and to require an explicit equation, not a coincidence.
6. **Freeze gāna identity** only after step 5 balances, then materialise passages behind the gate.
7. **Re-point `COMMONS.SV.KAU.SAMAN.AUDIO`** at the new work_id and bind the 475 files to gāna
   passages at **PAGE_LEVEL**, many-to-many, with the 3 ārcika-only files handled as the exception
   they are.
8. **Only now, mirror the audio bytes.** ~771 MiB, 475 files. Compute a real
   `checksum_sha256` per file, verify each against the Commons `sha1` recorded in
   `samaveda_gana_audio_inventory.jsonl`, and preserve **per-file** licence, licence URL, usage terms
   and uploader attribution — 459 CC BY-SA 4.0 and 16 CC0, never flattened.
9. **Record the coverage gap honestly**: 215 of 662 gāna content pages have no audio, and
   rahasyagāna has none at all. State it as a measured gap, not a TODO.
10. **Update `docs/FOUR_VEDA_RIGHTS_MATRIX.md` §3.2** to carry a gāna row, and restate the §4.3
    conclusion — the combined four-Veda corpus is not licensable as one adapted work — wherever a
    release is described.

---

## 9. Reproducing this packet's figures

```bash
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/inventory_samaveda_gana.py
```

Writes both JSONL files and prints every measurement quoted above, including the collection digest.
~27 API requests total (11 Wikisource, 16 Commons), 0.4 s apart, User-Agent
`VedaGraph/1.0 (research; +https://github.com/HimanshuMohanty-Git24/VedAnvaya)`.
**No audio bytes are fetched.** Rows are sorted (by `file_name`; by `page_title`), keys are
sorted, line endings are LF.

The digest is stable across runs because it depends only on `(file_name, sha1)` — it was reproduced
identically on two independent runs on 2026-09-07. **If it changes, Commons changed**, which is the
point of recording it.
