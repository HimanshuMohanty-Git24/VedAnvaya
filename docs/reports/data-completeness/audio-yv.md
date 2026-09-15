# Yajurveda audio — Agent 6, Wave 1

**Status: `PARTIALLY_CLOSED`. 25 of the 223 closed at `EXACT`. 8 staged `UNVERIFIED`. 190
blocked — on rights and granularity, not on availability, which corrects Wave 0.**

Artifact: `data/staging/audio_yv/` — 33 rows, 12 sources, 201 rejected candidates, 4 proof
records. Validator: `PASS`, every check at 100% coverage, `--graph` included.

Neo4j was read-only throughout. Nothing outside `data/staging/audio_yv/` and this file was
written.

---

## The honest summary, first

Most of the 223 cannot be closed, and that was always the likely outcome. What changed is *why*.
Two of Wave 0's conclusions about this domain were wrong, and both were wrong in a way that
mattered:

1. **The 33 `text_mismatch` are not "the signature of a numbering divergence".** There is no
   numbering divergence in the Yajurveda at all. They were two defects in our own matcher, one of
   which is severe and cross-cutting. 25 of the 33 closed deterministically, with no acquisition
   and no new source.
2. **Mādhyandina audio is not unavailable.** IGNCA's Mādhyandina set is live today — I fetched
   HTTP 200 and 14–48 MB per adhyāya, 2026-09-15. Reconnaissance probed a withdrawn `.mp3`
   directory, correctly found it 404, and concluded "genuine external unavailability" and
   "recitation would have to be commissioned". The material is online, is the right recension,
   and is held by a named institution. The blocker is **permission plus granularity**.

The first of those is worth more than any acquisition available in this domain, and the second
changes the remedy for the remaining 198 from *commission a reciter* to *ask IGNCA and verify
segment boundaries*.

---

## The 223, by reason, before anything was acquired

The brief asked for this breakdown first. It is unambiguous, because the source holds all 1,975
Yajurvedic coordinates:

| reason | count | meaning |
|---|--:|---|
| never searched | **0** | every one of the 1,975 was assessed |
| verse absent at source | **0** | `source_verses` = `our_verses` = 1,975 |
| found, no audio attached | **190** | the row exists, `audio.sanskrit` is absent |
| found, rejected on text mismatch | **33** | audio exists; our matcher refused the pair |

`1,752 + 190 + 33 = 1,975`, exactly. Reproduced from `data/derived/vedsearch_harvest.json`
against the live graph before touching anything, and it matches
`data/product/audio_discovery_report.json` figure for figure.

So the whole 223 is *found-and-rejected*. Nothing was unsearched, and nothing is missing from the
source's coordinate space. That is a good starting position and it is why the 33 were worth
attacking first.

---

## The 33 `text_mismatch`: a mapping defect, decisively

Full evidence in `data/staging/audio_yv/proofs/instrument-defects.md`. In brief.

### The offset hypothesis is false

Each of the 33 was scored against **all 1,975** source rows, not just its own coordinate. For
**30 of the 33** the coordinate-aligned row is also the single best match in the entire corpus,
with the runner-up at or below 0.64. There is no displacement to correct. The coordinates were
right the whole time; the text check was broken.

### Defect 1 — our text writes visarga as an ASCII colon

`skeleton()` keeps visarga as the base letter `h` but drops `:` as a non-letter.

- our stored YV text containing an ASCII colon: **893 of 1,975**
- the source's YV text containing an ASCII colon: **0 of 1,975**
- colons in our text *not* preceded by a Devanagari or Vedic character: **0** — so it is a
  visarga glyph on every occurrence, never punctuation

Folding it took the 33 from 0 clearing threshold to 13, landing at 0.99+ rather than creeping
over the line.

### Defect 2 — `difflib` autojunk, and this is the big one

```python
# src/vedagraph/product/audio/vedsearch.py
return difflib.SequenceMatcher(None, left, right).ratio()
```

`autojunk` defaults to `True`: on a sequence of 200+ elements it discards any element appearing
in more than 1% of it. A verse skeleton is 200–1,100 characters over a ~30-letter alphabet, so
**every letter is discarded**. For long verses the returned ratio is noise.

The specimen: `VG:YV:VSM:A05:V023`. Ours and the source's skeletons are both 269 characters and
differ in five places where one edition writes `valaga` and the other `balaga`. The shipped
comparator scored that **0.2342** — lower than the 0.462 the module's own docstring records as
the *maximum* for deliberately mispaired verses. With `autojunk=False`: **0.9777**.

This never surfaced because `verse_matches()` short-circuits on exact skeleton equality, so most
true pairs never reach the comparator. Only pairs with a real orthographic difference take the
fuzzy path — exactly the population autojunk destroys. The calibration recorded in the module
("median 0.995, p5 0.973") was computed with the same broken comparator and looked healthy
because the median rides on the short-circuit.

### Recalibration, and the regression check

Threshold unchanged at 0.90.

| population | n | median | p5 / p99 | extreme |
|---|--:|--:|--:|--:|
| coordinate-aligned | 1,975 | **1.0000** | p5 0.9862 | min 0.2769 |
| deliberately mispaired | 800 | 0.2514 | p99 0.4125 | **max 0.5690** |

Worst wrong pair 0.5690 against a 0.90 threshold: the populations do not approach each other.
And, the check that decides whether a fix is a fix:

- verses that mapped under the shipped matcher and no longer map: **0**
- newly mapped: **25**

Strictly additive.

### Outcome

**`text_mismatch` for the Yajurveda: 33 → 8.** 25 closed at `EXACT`, all at 0.9777–1.0000 —
word-for-word identical text, not a marginal pass.

---

## The 8 that remain, each with its own reason

Audio exists at all eight coordinates: I fetched real, decoding MP3 for every one. They are
staged `UNVERIFIED`, which stages them and does not import them, and that is the correct
outcome.

| key | score | reason |
|---|--:|---|
| `A03:V042` | 0.8022 | source's text field repeats the second hemistich |
| `A07:V003` | 0.2769 | **our** text has swallowed a Sanskrit commentary |
| `A09:V006` | 0.5254 | same two hemistichs, inverted order |
| `A19:V003` | 0.6744 | source repeats the verse, with a variant between the two statements |
| `A23:V030` | 0.8114 | source dittography, and 23.1.31 scores higher than 23.1.30 — the source's own boundary is in doubt |
| `A25:V047` | 0.7895 | source's field is truncated mid-verse |
| `A33:V056` | 0.6220 | source's field holds only the ṛc, ours the ṛc plus its yajus continuation |
| `A33:V082` | 0.7714 | source dittography |

Six of the eight are defects in the *source's printed text field*, not in its audio. The
recording is probably right in most of them. But "probably right" is not a mapping, and what
settles each one is a human listening — which nobody has done, so no row claims it.

`A07:V003` is ours and needs naming plainly: our stored mantra text is 1,138 skeleton letters
against the source's 184, and the excess is running commentary — `iti pāṭhaḥ`, `iti śrutiḥ`,
`iti śeṣaḥ`. The `wikisource-sa-vsm` extraction spilled bhāṣya into the mantra.
`FOUR_VEDA_CANONICAL_SANSKRIT_BLOCKERS.md` records 36 of 1,975 boundaries falling back to
accent-presence inference; this looks like one of them. It is a text-layer defect that surfaced
through audio, and it is outside an audio agent's write surface. Referred to the lead.

`A33:V056` carries a warning worth keeping: our text for that key matches source row **7.1.8 at
0.9956**, because VSM 33 recycles material from earlier adhyāyas. A text-only search would have
confidently attached adhyāya 7's recording to a mantra in adhyāya 33. It was not mapped there and
must not be.

---

## Is IGNCA still 404 today?

**The path reconnaissance probed: yes, and it was right.** `SYMS_CHAP_{01,07,12,20,40}` under
`/Yajurveda_MP3/`, both `.mp3` and `.mp4`, all HTTP 404 on 2026-09-15, each returning the
portal's 179,454-byte HTML error page.

**A different path on the same portal: no, and this is the correction.**
`/Shukla_Yajurveda_Madhyandin_MP3/SYMS_CHAP_{NN}.mp4` is live today.

| file | status | Content-Length | Last-Modified |
|---|---|--:|---|
| `SYMS_CHAP_01.mp4` | 200 | 42,989,877 | 28 Feb 2024 |
| `SYMS_CHAP_02.mp4` | 200 | 39,296,671 | 28 Feb 2024 |
| `SYMS_CHAP_08.mp4` | 200 | 48,470,612 | 28 Feb 2024 |
| `SYMS_CHAP_26.mp4` | 200 | 20,369,487 | 28 Feb 2024 |
| `SYMS_CHAP_35.mp4` | 200 | 13,993,056 | 28 Feb 2024 |
| `SYMS_CHAP_41.mp4` | 404 | — | — |

`CHAP_41` → 404, so the boundary is exactly 40 adhyāyas — the Mādhyandina count. The directory
name says `Madhyandin`. This path was recorded in
`docs/FOUR_VEDA_AUDIO_SOURCE_INVENTORY.md` §4.4 and was not carried forward into
reconnaissance's §2.2, which is how the wrong conclusion was reached from a correct probe.

**It is still rejected**, on two grounds neither of which is availability:

1. **Rights.** IGNCA's position is `PERMISSION_REQUIRED`, and the inventory records a deliberate
   anti-download measure in the portal's player. Publicly playable is not permitted; this project
   already removed the Vedic Heritage route once for exactly that reason.
2. **Granularity.** One file per adhyāya, 14–48 MB, no timestamp file, no cue index, no
   per-mantra marker. The gap is 198 individual mantras. Section 10 permits `VERIFIED_SEGMENT`
   only where a boundary rests on real evidence; here there is none, and a guessed boundary is
   forbidden.

So: `BLOCKED_RIGHTS_AND_GRANULARITY`, **not** `BLOCKED_EXTERNAL_SOURCE_UNAVAILABLE`. The remedy
is one permission request plus a verified segmentation pass, not a commissioned reciter. That
distinction is the practical value of re-probing.

---

## Every candidate rejected for recension, and what identified it

Full detail in `proofs/recension-rejections.md`. The headline is that reconnaissance's runtime
fingerprint was right but under-argued, and measuring the whole family turns a suspicion into an
identification.

| item | mp3 | hours | naming | licence |
|---|--:|--:|---|---|
| `suklayajurveda_202107` | 54 | 37.34 | `Suklayajurveda Part 001…054` | PD Mark 1.0 |
| `IISHAShuklaYajurVeda` | 55 | 37.51 | `INTRODUCTION` + `SYV001…054` | **none** |
| `IISH_SHUKLA_YAJUR_VEDA` | 55 | 37.86 | `INTRODUCTION` + `SYV001…054` | **none** |
| `SHUKLA-YAJUR-VEDAM` | 55 | 36.47 | Telugu `_part_00…54` | CC BY-NC-ND 4.0 |
| `shukla-yajur-veda_recitation` | 80 | 36.96 | ends `Part_53/54-Shukla_Yajur_Veda` | **none** |

**Five items, one master: 54 numbered parts, ~37 hours.** What identifies it is not the runtime
but the creator field — `suklayajurveda_202107` names **"Veda Prasara Samithi"**, and
`FOUR_VEDA_AUDIO_SOURCE_INVENTORY.md` records that master confirmed **Kāṇva** against Veda
Prasar Samiti's own archived recension table, verbatim *"SHUKLA YAJUR VEDA .. Kanva Sakha"*.
A second, independent check: 54 parts divides neither 40 adhyāyas nor 1,975 mantras nor 303
anuvākas. Nothing Mādhyandina has 54 of anything.

**All five rejected `WRONG_RECENSION_KANVA`. None used for any row at any confidence.**

Also rejected:

- `shukla-yajur-vedaH-kANva-samhitA-vedamu` — self-labelled Kāṇva; kept as the reference
  specimen behind the rule *any "Shukla Yajurveda" that does not say Mādhyandina is this master
  until proved otherwise*.
- `mAdhyandina-shAkhA-vedamu` — **correct recension**, and the nearest available recording.
  5 MP3, 8.82 h, `Adhyay(1-7)`…`(23-27)`. Rejected three times over: coverage stops at adhyāya
  27, so 60 of the 190 are outside it; ~1.8 h monolithic blocks with no index, so no verifiable
  boundary; and no licence, its own description reading `vedamu copy of mAdhyandina-shAkhA` —
  a mirror of a source that publishes "open to listen, and not to download". A mirror does not
  create a licence.
- `SuklaYajurved` — titled "shukla yajur ved (MADHYANDINIYA SAMHITA)", creator field abused to
  read "40 adhyaya", first hit in search, and it holds **zero media files**. It is a book scan.
  Recorded because that title is the exact shape of trap this domain is full of.
- `vedapeetha.org` Mādhyandina page — no audio at all; the site's audio is under **Taittirīya**,
  which is Kṛṣṇa-Yajurveda and forbidden. Retained instead as recension evidence: it states
  *"The Mādhyandina Śākhā contains 40 Adhyāyas, 303 Anuvākas and 1975 verses."*
- `vedamu.org` direct — HTTP 000, connection fails. Unreachable today, recorded as such rather
  than as gone.

Kṛṣṇa-Yajurvedic audio was not pursued at all: abundant and forbidden. Recorded so the omission
reads as a decision.

### What establishes Mādhyandina for the rows that *were* accepted

VedSearch names no recension anywhere, so it had to be established rather than read off a label:

1. 40 chapters, exactly **1,975** verses — matching vedapeetha's Mādhyandina figure and this
   corpus, against Kāṇva's ~2,086 recorded in the inventory. A 1,975-verse structure cannot be
   Kāṇva.
2. IGNCA's own "Madhyandina Samhita, Adhyaya 01" page enumerates mantras **1–31**; our adhyāya 1
   holds exactly **31**. The agreement holds at the first division, not only at the total.
3. Per-mantra text identity against our Mādhyandina corpus: median 1.0000, p5 0.9862 across all
   1,975, against a mispaired maximum of 0.5690.
4. Each row carries its own `text_match_score`; the lowest accepted is 0.9777.

---

## What closed, and at what confidence

| | count | confidence | importable |
|---|--:|---|---|
| closed by the instrument fix | **25** | `EXACT` | yes |
| staged with a typed blocker | **8** | `UNVERIFIED` | no, by design |
| blocked, no audio at source | **190** | — | no |

**Yajurveda audio goes from 1,752 of 1,975 (88.7%) to 1,777 (90.0%)** if the 25 import. Every
one of the residual 198 carries a typed reason, which satisfies the second clause of
`GAP-AUDIO-003`'s closure test.

No row is a segment; no `VERIFIED_SEGMENT` was needed or claimed, because the source publishes
one file per mantra. No timestamp was invented and no neighbouring verse's recording was
attached to anything.

---

## QA — the reviewed population, exactly

`sampled: 93`, `sample_method: both`, `defects_found: 2`, `human_reviewed: 0`.

- **25 of 25 accepted rows (100%)**: real audio fetched from the live API. All 25 decoded as
  MP3, 88–288 KB. 25 distinct recordings; no recording shared between two keys.
- **Adversarial proportionality check.** 60 control rows the shipped pipeline had already
  accepted were fetched to establish a bytes-per-text-letter band: **414.8 – 978.6**, median
  527.4. All 25 accepted rows fall inside it, at **418.9 – 853.1**. For scale, a whole adhyāya
  at the control rate would be ~2,852 KB; the largest accepted file is **281 KB**. So none of
  the 25 is a long recording attached to a single mantra — the specific failure mode the brief
  forbids.
- **8 of 8 residue coordinates** fetched: all carry real MP3, so their blocker is text
  verification, not absence.
- **40 of the 190** no-audio rows re-probed live on 2026-09-15 rather than trusted from the
  2026-09-12 harvest: **0 flipped**.
- **Adversarial offset test**: all 33 scored against all 1,975 source rows. Disproved the
  hypothesis it was testing.

The 2 `defects_found` are the two instrument defects. **Zero defects were found in the 33 rows
themselves.**

What is *not* verified, stated so no reader infers it: no row carries `duration_seconds`,
because none was decoded — it is null, not zero. **No human has heard any of these 33
recordings.** The 25 `EXACT` rows rest on the source's own statement of what each file recites,
matched against our text. That is the same two-safeguard basis as the 1,752 rows already in the
catalogue, and no stronger.

---

## Blockers to name rather than work around

1. **190 verses: `BLOCKED_RIGHTS_AND_GRANULARITY`.** VedSearch, the only per-mantra Yajurvedic
   source anywhere in this survey, has no recording for them — re-verified live today on a
   40-row sample. Mādhyandina audio covering them exists at IGNCA and is online, but it is
   permission-required and published per adhyāya. Proof: `proofs/exhaustive-search-record.md`,
   five independent avenues with the exact queries.
2. **8 verses: awaiting a listener.** Audio fetched and confirmed present; the text check cannot
   be completed from the source's own printed field. Ten minutes of human listening closes most
   of these, and nothing automated will.
3. **`VG:YV:VSM:A07:V003`'s mantra text is wrong in the graph** — commentary spilled into the
   mantra. Text layer, not audio. Cannot be fixed from this write surface.
4. **The AV's 495 `text_mismatch` were produced by the same two defects.** The autojunk defect is
   length-dependent and Atharvavedic mantras are long. Rerunning the AV alignment with these two
   corrections costs one script invocation and should precede any AV audio acquisition. This is a
   **prediction, not a measurement** — I did not run the AV, because it is not my write surface.

## Two things a human must decide

- Whether to request IGNCA's permission for the 40 Mādhyandina files. It is the only route to
  the 190 that does not involve commissioning a reciter, and the assets are confirmed live.
- Whether the two instrument defects get fixed in
  `src/vedagraph/product/audio/vedsearch.py` — which is not my write surface, so the corrected
  instrument lives only in this artifact's `algorithm_version` and in the proof record. Until it
  is fixed in the module, any re-run of `discover_vedsearch.py` will reproduce the old 33.
