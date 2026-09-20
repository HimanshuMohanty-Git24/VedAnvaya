# Samaveda audio and musical data — Agent 5, Wave 1

Staging artifact: `data/staging/samaveda_music/`. Validator: **PASS**, every check evaluating
every eligible row, with `--graph`.

The product had **no melodic dimension of any kind**. It now has two, typed separately, over
1,219 canonical keys — and it still has **zero** verse-scoped Samavedic audio, which is the
honest answer and not a failure to look.

## The short version

| | before | after |
|---|--:|--:|
| Commons gāna files with a real content checksum | 0 of 475 | **475 of 475** |
| Ārcika verses carrying svara notation | 0 | **1,136** of 1,844 |
| Gāna Works with an identity | 0 | **4** |
| Gāna units with an identity | 0 | **657** |
| `MUSICALIZED_AS` ārcika → gāna edges | 0 | **495**, over 332 verses |
| Ārcika verses with **verse-scoped** audio | 0 | **0**, now a *verified* zero over 1,844 assessed |
| Files listened to | 0 | **0** |

Counts balance: `candidates_considered 2,195 = accepted 1,471 + rejected 16 + unresolved 708`,
plus `verified_zero 1,844` for the audio dimension.

---

## Job A — audio

### The 475 files are now actually ours

Every one of the 475 Commons Ogg files was streamed, hashed and discarded: 808,529,118 bytes,
19.114 h measured. `sha256_of_bytes` was `null` on all 475 rows of
`data/source_registry/samaveda_gana_audio_inventory.jsonl`; it is now a real digest on all 475.

The distinction someone was careful to preserve — `sha1_is_not_sha256: true` — is preserved and
put to work. I computed **both** digests over the same byte stream, so the SHA-1 is a *proof of
custody*: 475 of 475 agree with the SHA-1 MediaWiki reports, which means the bytes I hashed are
provably the bytes Commons describes. `sha1_is_not_sha256` stays `true` on every row; the SHA-1
is recorded as `commons_reported_sha1` and `sha1_of_bytes`, never in a SHA-256 field.

Three further checks, none of which needed a source to be trusted:

- **Byte size** agrees with the inventory on 475 of 475.
- **Duration measured from the container** — the Ogg identification header's sample rate and the
  final page's granule position — agrees with the API-reported duration within 0.1 s on 474 of
  474 readable files. This is an independent measurement, not a re-copy of the API's number.
  One file, `और्णायवोत्तरम्(परिप्रियादि) Aurnayavottaram.ogg`, puts its Vorbis identification
  header past the first 4 KB, so its rate was not read and its measured duration is recorded as
  `null` rather than assumed. Its granulepos of 4,506,624 over 44,100 Hz reproduces the API's
  102.191 s exactly, but that is corroboration and is labelled as such.
- **475 distinct SHA-256 values** — no file is a byte-duplicate of another.

The corpus is not as uniform as "475 Ogg files" suggests: 456 stereo/44.1 kHz, 9 mono/44.1 kHz,
5 stereo/32 kHz, 4 stereo/96 kHz, and the 1 file whose header was not reachable — 475 exactly.
Two uploaders, 319 and 156 files.

A first attempt at 4 concurrent streams drew **HTTP 429 on 462 of 475** after 13 successes. The
rate limit is not the documented one (`x-ratelimit-limit: 600000;w=60`); it is a burst/concurrency
limiter. Sequential fetching with a 0.25 s pause and exponential backoff completed 475/475 with
zero failures. Worth recording because the failure mode is silent if a fetcher does not retry on
a non-200.

### Ārcika verse audio: zero, and the zero is typed

`proofs/arcika-verse-audio-absence.json` records the assessed population (1,844, broken out per
collection) and the disposition of each candidate. Reconnaissance's verdict holds, and I can now
say *why* more precisely than "6 of 475 touch ārcika pages":

**All 6 sit on a container page, never on a verse.** Four `आज्यस्तोत्रम्` files (121–399 s) are
transcluded on `उत्तरार्चिकः/2.1 प्रथमप्रपाठकः/2.1.1 प्रथमोऽर्द्धः`; `धेनुसाम` (81 s) on
`छन्द आर्चिकः/1.1.5.9 नवमी दशतिः`; `प्रवद्भार्गवम्` (223 s) on `1.1.6.7 सप्तमी दशतिः`. These are
sāman performances placed on an ardha or a dasati holding many verses, and no source states a
boundary inside any of them. Attaching one to a verse is the case campaign rule 4 forbids.

So they are staged at the scope the source itself chose — **3 rows at
`GANA_PERFORMANCE_AT_ARCIKA_CONTAINER_SCOPE`**, carrying 6 files, with
`start_seconds: null`, `end_seconds: null`, `verse_boundaries_stated_by_source: false` and
`is_arcika_verse_recitation: false`. The container keys were derived from each page title's own
dotted coordinate (`2.1.1` → `UTTARA:P01:R01`) and required to resolve to a held Passage.

The other three candidates are unchanged and re-verified where cheap: IISH has **no `licenseurl`
and no `rights` field** on its archive.org item (re-checked this pass); IGNCA is
permission-required and already removed; vedamu is "open to listen, and not to download".
`shaivam.org/audio-gallery/sama-veda/` stays **UNRESOLVED** at HTTP 403 — still the best
value-per-minute human check in this domain, and still not attempted by any bypass.

### `MUSICALIZED_AS` — a relation between two works, on two agreeing signals

495 edges over 332 ārcika verses, one row per verse. The join is never a trusted number:

1. the gāna page prints the ārcika running number as a `sa.wikisource.org/s/…` short link, **and**
2. the ārcika verse text this project already holds for that number appears verbatim on that
   gāna page under a declared normalisation.

Both had to hold. 11 citations were **refused** because the number resolved but the text did not
appear. The worked case: the Grāmageya `गायत्रम्` page cites `१४६२`; running 1462 is
`VG:SV:KAU:UTTARA:P06:R03:D10:V01`; our stored text is
`तत्सवितुर्वरेण्यं भर्गो देवस्य धीमहि । धियो यो नः प्रचोदयात्`, character-identical to the mūla
verse printed on that page; and the short link independently resolves to the Uttarārcika
`2.6.3 तृतीयोऽर्द्धः` page, which is `P06:R03`. Two axes, both agreeing.

The payload says what the edge means and what it does not:
`is_this_verse_recitation: false`, and *"a relation between TWO DISTINCT WORKS: this ārcika verse
is the yoni of those gānas. It is not 'this verse's recitation', and a gāna is not a rendering of
this verse's words."* The distribution is musically sensible rather than one-to-one: 258 verses
have one gāna, 44 have two, and one has twelve.

### The cue index: found, read, and it produced nothing

This is the one place where a reconnaissance find is both confirmed *and* downgraded, so
`proofs/cue-index.md` carries the evidence for both.

I fetched a page of `sAmagAnam` volume 01 as a 4959×7009 JP2 and looked at it. **The cue index is
real, legible, and richer than described**: the left margin carries the IISH clip number over an
mm.ss offset written as a fraction (`1/9.38`, `1/10.10`, `1/10.45`, `1/11.14`, `1/11.42`,
`1/12.42`), the right margin the gāna running number (12–18), and the body the ārcika/gāna
ordinal (`(6.1)`, `(6.2)`, `(7.1)`…). That is a three-way index: ārcika verse ↔ gāna number ↔
clip + offset.

It yielded **0 `VERIFIED_SEGMENT` rows**, for four independently sufficient reasons:

1. **It is handwritten and there is no text layer.** `pypdf` extracts 0 characters from every page
   of volumes 01, 09 and 10. archive.org's `_djvu.txt` derivative is Malayalam OCR of handwriting:
   a timestamp sweep over volume 01's 30,535 characters returns 25 hits including `4.൧8`, `1:74`
   — `1:74` is not a time. Harvesting it would have produced **invented timestamps that look
   extracted**, which is the exact prohibition.
2. **The target recording has no rights statement**, re-verified.
3. **The index is bounded at 24 of 64 clips by the compiler's own statement**, permanently: Ūha
   and Ūhya "are not prepared here, and there is no plan to post them." Those two books are 421
   of my 657 units, so the cue index can never reach 64% of them.
4. `sAmagAnam` is **CC BY-NC-ND 4.0**, one-way incompatible with the CC BY-SA corpus beside it.

A seven-row pilot transcription of that one page is recorded in the proof, typed as a pilot and
promoted nowhere. It passes its own consistency check: offsets strictly increasing, all inside
`SV001.mp3`'s 2,648.04 s.

**And it is an anchor index, not a segment map** — checked on a second page rather than assumed
from the first. Volume 01 is 40 pages for GG 1–180. Page 11 holds five gānas (`(35.1)`–`(36.1)`,
running numbers 56–60) and carries **exactly one** cue, `1/33.05`; the other four have none.
Against 6 cues for 7 gānas on page 3, the density is neither one-per-gāna nor stable. So even a
complete transcription would leave most gānas without a timestamp, and filling the gaps means
interpolating between anchors — which is inventing a boundary, and is refused. The two pages do
corroborate each other: 12.42 and 33.05 are both clip 1 and in order, so clip 1 alone spans
roughly GG 12–60, consistent with the volume filenames summing to 15h53 over ~24 clips.

`FOUR_VEDA_SNAPSHOT_PROVENANCE.md` **F5 — "No timing or cue artifacts exist for any audio" — is
stale and should be amended, not rediscovered.** The accurate narrower statement is that no cue
artifact is *machine-readable*. The closure cost is now known: a human transcription pass over two
margin columns across ten volumes, not a parser.

---

## Job B — the melodic layer

### The Unicode claim: the substance holds, the block name does not

Reconnaissance's table reads *"real Unicode Vedic Extensions, not a font hack."* Measured over
667 pinned pages and 1,750,419 characters:

| | count | verdict |
|---|--:|---|
| Private-use-area codepoints | **14** (0.0008%) | *"not a font hack"* — **CONFIRMED** |
| Devanagari Extended `U+A8E0–A8F1` cantillation marks | **106,094** (98.1%) | |
| Vedic Extensions tone marks `U+1CD0`, `U+1CD2` | **2,066** (1.9%) | *"Vedic Extensions"* — **WRONG** |

**A regex scoped to the Vedic Extensions block would have found 2,066 tone marks and missed
106,094 — 2% of the notation.** The marks are `U+A8E1/E2/E3` (combining digits one/two/three, 26,740 / 34,922 / 21,533),
`U+A8EF` (combining letter RA, 19,205), `U+A8E4/E5`, `U+A8EA–EE`, `U+A8F0/F1`, plus `U+1CD0`
VEDIC TONE KARSHANA (601) and `U+1CD2` VEDIC TONE PRENKHA (1,465). This project's own
`data/canonical/samaveda_arcika_v1/source_artifacts.jsonl` already recorded the right block
("Devanagari Extended U+A8E1–U+A8E5"); the reconnaissance table drifted from it.

The brief's two named traps were tested rather than assumed, and a third was found:

- **`U+1CEA` / `U+1CEC` are anusvāra, not tone.** Both are **excluded** from the tone class.
  Occurrences in this corpus: **0** — so the trap does not fire, but it cannot fire later either.
- **`U+0301` is both udātta and IAST `ś`.** Occurrences: **0**, as expected in a Devanagari
  witness. Excluded anyway, and checked on all 1,136 notation rows.
- **New: `U+A8F2` and `U+A8F3` sit inside Devanagari Extended right beside the svara marks and are
  not tone at all.** They are SPACING candrabindu *letters*, category `Lo` — the Samavedic nasal
  `ꣳ`. They occur 162 and 1,722 times. Counting the block would inflate the tone count by 1,884
  and, worse, *stripping* them would corrupt the text. `U+1CF2` VEDIC SIGN ARDHAVISARGA (134,
  also `Lo`) is the same hazard in the other block.
- **Counting combining marks alone also *understates* the notation.** A large part of Kauthuma
  notation is written inline as ordinary digits after an avagraha — `प्रचो꣢ऽ१२१२`, the figure
  1‑2‑1‑2 — using `U+0967…U+096F`, which are not combining marks at all. 17,928 such runs exist in
  the corpus. The same "codepoint instead of meaning" failure, in the opposite direction.

Full census with names, categories and per-codepoint counts:
`proofs/notation-codepoint-census.json`.

Two smaller corrections to the reconnaissance figures, both downward: the gāna subtree is **662
non-redirect pages, not 726** — 64 of the 726 are redirects — and of those, 5 are book index pages
or the Rahasyagāna monolith, leaving **657 gāna units**.

### The accented ārcika text nobody had opened

The largest find of this pass was already inside our own registry, flagged `ANCILLARY` and never
read: `सामवेदः/कौथुमीया/संहिता/सस्वरा पूर्णा` ("the complete accented text"), 213,906 characters,
**42,940 svara marks**, organised by exactly the coordinate path our canonical keys use
(`पूर्वार्चिकः/छन्द आर्चिकः/1.1.1 प्रथमप्रपाठकः/1.1.1.1 प्रथमा दशतिः` … through
`उत्तरार्चिकः/नवमप्रपाठकः/तृतीयोऽर्द्धः`), CC BY-SA 4.0, in real Unicode.

This is the **Samavedic numeric svara notation over the ārcika verses** — the melodic dimension of
the text we actually hold, not a decoration on the gāna. **1,136 of 1,844 verses** now carry it
(`CHANDA` 471/585, `UTTARA` 631/1,194, `ARANYA` 31/55, `MAHANAMNYA` 3/10), 25,542 marks in total.

The join deserves scrutiny, because the obvious approach is wrong. The page prints verse numbers,
and they are **not** running numbers: they reach 585 (the Pūrvārcika extent) and restart, and
using them would have produced **419 disagreements** against the running number. Content alone is
also insufficient: 1,844 stored verses normalise to only 1,644 distinct strings, because the
Samaveda repeats verses across the arcikas, so ~200 verses are text-ambiguous.

What was used instead is **two constraints at once**: a longest-common-subsequence alignment of
the page's verse sequence against the 1..1875 running sequence, keeping only pairs that are both
**text-identical** (tone marks stripped, punctuation and digits dropped, `U+A8F2/F3` folded to
anusvāra, word-final `म्`/`न्` folded to anusvāra) **and order-consistent**. The page's own
numerals were not used to join at all.

The **708 that did not align are staged as `UNRESOLVED`, not rejected**, each with its own reason,
and the distinction is reported rather than smeared: for **599** a line exists within 0.90
similarity, so it is a *witness disagreement* — real sandhi, pluti (`ऽऽ`), `असृक्षते` against
`असृक्षत`, `रथमेंद्रं` against `रथमिंद्रं`, or an editorial bracket glued onto the line — and it
needs philology, not another source. For **109** no line comes close, so the accented witness
plausibly does not carry the verse. Forcing either group to match would be the "looks similar"
collapse section 1 forbids.

As a by-product this locates a source for **`GAP-MORPHOLOGY-006`** ("the Samaveda has no accented
and no search-normalised text") and closes reconnaissance's stale claim #2 that no accented
machine-readable ārcika text is available. That dimension is not my write surface, so it is
reported and not written.

### Four Works, and the fifth that was refused

| Work | key | units | inline notation | scan images | performances | text-verified yoni | marks |
|---|---|--:|--:|--:|--:|--:|--:|
| Grāmageyagāna | `VG:WORK:SV:KAU:GANA:GRAMAGEYA` | 175 | 38 | 149 | 97 | 123 | 2,852 |
| Āraṇyageyagāna | `…:ARANYAKAGEYA` | 61 | 10 | 52 | 40 | 36 | 1,055 |
| Ūhagāna | `…:UHAGANA` | 356 | 23 | 296 | 264 | 273 | 2,311 |
| Ūhyagāna | `…:UHYAGANA` | 65 | 15 | 58 | 46 | 53 | 9,502 |

Each is a separate Work identity with its own URN, its own UUIDv5 from
`7c8cde94-2bc0-50e2-8819-568ae65a3ec4`, and its own scope statement saying it is **gāna only**,
shares no key with `VG:WORK:SV:KAU`, and must never be substituted for ārcika recitation. All four
are marked `PROPOSED_FOR_LEAD_ADJUDICATION` — I mint deterministic identities; the lead decides
whether they import. Every UUID was recomputed from its URN as a check (1,136 of 1,136 agree
across works, units and performances).

**The honest shape of the notation layer is uneven, and the table says so rather than averaging
it away.** Only **86 of 657** units carry inline Unicode notation. **555** carry a JPEG page scan
instead, which is an image and not data. And the Ūhyagāna's 9,502 marks are concentrated in three
monolithic parvan pages rather than spread over its units — a per-unit average would have hidden
that completely.

**The Rahasyagāna was deliberately not modelled.** One monolithic page with 26,240 notation marks.
Tradition treats Rahasyagāna as a second *name* for the Ūhyagāna, but this witness presents both
as separate subtrees. Folding it into `UHYAGANA` and minting it as a fifth Work each assert
something no evidence here settles, so neither was done: it is in `rejected.jsonl` at disposition
`UNRESOLVED` with the reasoning, for adjudication.

**The notation is data, not an interpretation.** Codepoints, counts, and the raw string. No mark
was translated into a pitch, because the Kauthuma-school decipherment authority (van der Hoogt
1929) is not held and **Wayne Howard 1988 is the Jaiminīya** — it was deliberately not applied.

---

## QA

11,193 record-evaluations across 12 checks, 0 defects. `proofs/qa-report.json`.

The row-level checks are **exhaustive, not sampled** — every one of the 1,136 notation rows
re-derives to our own stored text, every one of the 495 `MUSICALIZED_AS` edges is re-verified —
with a seeded random sample of 60 (`seed 20260915`) and an adversarial sample of the **40 shortest
verses**, where text containment is likeliest to match by accident, on top. The shortest verse
used is 37 normalised characters against a floor of 25.

Results are **stratified by ārcika collection, gāna book and licence**, not just totalled, because
this project has already paid for the lesson that two random samples can both read 97% while one
alias is 82.9% wrong.

The `MUSICALIZED_AS` join was re-derived from the **live graph's own stored ārcika text** (495/495),
and the graph's text was checked against the canonical file this build read (1,844/1,844), so the
re-derivation is not circular.

**Listening review: 0 files.** Section 22's 100% listening review is *not* satisfied and is not
claimed. `proofs/listening-review.json` states the reviewed population as 0, the population that
would need review as 475, and enumerates what was verified instead — bytes, container, licence,
source placement — with the population and method for each. **No listening sheet was produced**,
deliberately: a prior session in this project shipped one whose decisive row quoted what a *broken*
mapping would play, which is what happens when a sheet is written from expectation. There is also
nothing to compare against — for 421 of 657 units the only notation witness is a page scan.

---

## Gaps

| gap | status | evidence |
|---|---|---|
| `GAP-SAMAVEDA_MUSIC-002` — no melodic layer of any kind | **closure candidate** | A melodic layer exists in two typed forms: 1,136 ārcika notation rows and 657 gāna units with notation. `MUSICALIZED_AS` has 495 edges to import. Its closure test asks for a melodic node label and a non-zero `MUSICALIZED_AS` — both are now importable. |
| `GAP-AUDIO-001` — SV audio 0 of 1,844 | **advanced on the second branch of its own closure test** | That test allows *either* verified per-verse boundaries *or* "a gāna-scoped audio layer explicitly labelled gāna while the ārcika row still reports a typed absence with the 474-file inventory cited". That is exactly what this is: 475 checksummed gāna performances, and a typed zero with its assessed population of 1,844. The per-verse branch stays closed. |
| `GAP-SAMAVEDA_MUSIC-001` — gāna corpus excluded from `VG:WORK:SV:KAU` | **advanced** | Its closure test requires a new work identifier. Four exist, with their own scope statements; `VG:WORK:SV:KAU`'s figures and exclusion list are untouched. 657 of ~2,639 traditional gānas, so still bounded. |
| `GAP-MORPHOLOGY-006` — no accented SV text | **source located, not written** | `सस्वरा पूर्णा`, 1,136 verses joined. Not my write surface. |

---

## Blockers and dead ends, named

**Blockers for the lead:**

1. **The running Saṃhitā number — the only join key between the ārcika and the gāna corpus — is
   absent from Neo4j.** It exists for all 1,844 verses in
   `data/canonical/samaveda_arcika_v1/citations.jsonl`, but there is **no `Citation` label in the
   graph** and SV `TextVersion`s carry **no `source_locator`**. Measured, not assumed. After
   import the `MUSICALIZED_AS` edges cannot be re-derived from the graph alone, and the next agent
   to attempt a gāna join will rediscover this.
2. **`MUSICALIZED_AS` is declared `Passage → Passage` with the gloss "this Rigvedic verse is sung
   as this Samavedic melody."** My edges are SV ārcika → SV gāna. The endpoint signature fits once
   gāna units are Passages of their new Works; the *gloss* is RV-specific and needs widening, or
   the ontology reference will disagree with its own data.
3. **Four Work identities await adjudication**, and the Rahasyagāna question with them.

**Dead ends, all verified in this pass:**

- `sAmagAnam` OCR text layer — Malayalam handwriting OCR, unusable; its "timestamps" include `1:74`.
- `sAmagAnam` cue index beyond clip 24 — will never exist, by the compiler's own statement.
- `IISHSamaVeda` — no `licenseurl`, no `rights` field, no recension statement. Not fetched.
- `shaivam.org/audio-gallery/sama-veda/` — HTTP 403, unresolved, no bypass attempted.
- Commons at 4 concurrent streams — HTTP 429 on 462 of 475. Fetch sequentially with backoff.
- `Samved.xlsx` — not opened. Verified trap.
- `sv-kauthuma-saswara.pdf` — not fetched. Verified 404 in Wave 0.
- Wayne Howard 1988 — Jaiminīya. Not applied to a single mark.
- van der Hoogt 1929, the Kauthuma counterpart — still no digital copy located.
- Griffith / Stevenson / Benfey / Sāmaśramī — Rāṇāyanīya. Not used.
- Volume 01 of `sAmagAnam` as a whole PDF — 37 MB, two download attempts timed out against
  archive.org. The single-page JP2-inside-ZIP route
  (`/download/<item>/<file>_jp2.zip/<file>_jp2%2F<file>_NNNN.jp2`, with redirects followed) works
  and is how the cue index was finally read. Worth knowing.

**Not done, and not claimable as done:** zero minutes of audio were heard; the notation is not
interpreted into pitch; 708 ārcika verses have no notation and 421 gāna units have no
machine-readable notation.
