# Product V1 — audio listening check (complete, 2026-09-13)

Every mapping in `data/product/audio_catalog.jsonl` is `EXACT`, `text_verified`, and
`MANTRA`-scoped. That verification is **textual**: it compares the text VedSearch states a
recording recites against this corpus's text for the same key. It does not establish that
the audio file at that URL contains that recitation.

That distinction is the whole reason this sheet exists, and it still holds. The automated
audit (`scripts/audio/audit_mappings.py`) re-derives coordinates and re-reads text; a
browser run can confirm the `playing` event fires and bytes arrive. Neither is an auditory
test, and neither should ever be reported as one.

**The auditory test has now been carried out.** On 2026-09-13 Himanshu played all ten rows
below and compared each recitation against the Sanskrit rendered on its own reader page.
All ten matched. Nothing was silent, clipped, truncated, or a different verse. The per-row
record is in [Recording the result](#recording-the-result).

The statement this sheet was created to make possible can therefore now be made: the audio
mapping is verified textually **and** confirmed auditorily.

`HUMAN_AUDIO_CHECK = PASSED`

## Why this specific sample

The Rigveda rows are chosen at the one boundary where a mapping error would be silent
rather than loud. VedSearch numbers Mandala 8 in Griffith's order, which places the eleven
Vālakhilya hymns at the end of the book; this corpus follows inline Aufrecht ordering. The
transform is `vedagraph.editions.griffith_page`. Below the gap the two orders agree, so a
broken transform still sounds right. Above it they differ by eleven hymns, so a broken
transform plays a plausible Rigvedic verse that is simply the wrong one.

The remaining rows are not there for coverage arithmetic. They are verses a listener with
no Sanskrit can still place by ear — the Gāyatrī, the Nāsadīya, the Puruṣa Sūkta — because
a check that depends on the listener parsing unfamiliar Vedic is a check that will be
recorded as "sounded fine". If a genuinely random draw is wanted instead,
`python scripts/audio/audit_mappings.py --sample 8` prints one; it seeds from `--seed` and
is reproducible.

## What to listen to

Open each reader page, press play, and compare what you hear against the Sanskrit shown on
that same page. The **Listen for** column is this corpus's own text for that key, with the
inline pitch accents dropped for legibility — it is what the reader page renders, not an
independent edition. The stream URL is given so a failure can be attributed to the mapping
or to the upstream file.

| # | Veda | Reader page | VedSearch ref | Listen for |
|---|---|---|---|---|
| 1 | RV | `/passage/VG%3ARV%3ASAK%3AM01%3AS001%3AV001` | `1.1.1` | `agnim īḻe purohitaṁ yajñasya devam ṛtvijam` — the control. If this is wrong, nothing below is interpretable. |
| 2 | RV | `/passage/VG%3ARV%3ASAK%3AM08%3AS048%3AV001` | `8.48.1` | `svādor abhakṣi vayasaḥ sumedhāḥ`. Below the Vālakhilya gap, so the reference is **unshifted**. Confirms the transform is not applied where it must not be. |
| 3 | RV | `/passage/VG%3ARV%3ASAK%3AM08%3AS071%3AV001` | `8.60.1` | **The critical check.** `tvaṁ no agne mahobhiḥ pāhi viśvasyā arāteḥ`. Hearing `agna ā yāhy agnibhir hotāraṁ tvā vṛṇīmahe` instead means the permutation was **not** applied — that is this corpus's 8.60.1, which a key-for-key mapping would have played here. |
| 4 | RV | `/passage/VG%3ARV%3ASAK%3AM08%3AS060%3AV001` | `8.49.1` | The other side of the same shift: `agna ā yāhy agnibhir hotāraṁ tvā vṛṇīmahe`. Rows 3 and 4 fail in opposite directions, so an inverted transform cannot pass both. |
| 5 | RV | `/passage/VG%3ARV%3ASAK%3AM03%3AS062%3AV010` | `3.62.10` | The Gāyatrī: `tat savitur vareṇyam bhargo devasya dhīmahi dhiyo yo naḥ pracodayāt`. Outside Mandala 8, so no permutation applies. |
| 6 | RV | `/passage/VG%3ARV%3ASAK%3AM10%3AS129%3AV001` | `10.129.1` | The Nāsadīya: `nāsad āsīn no sad āsīt tadānīṁ`. Outside Mandala 8. |
| 7 | AV | `/passage/VG%3AAV%3ASAU%3AK01%3AS001%3AV001` | `1.1.1` | `ye triṣaptāḥ pariyanti viśvā rūpāṇi bibhrataḥ`. No permutation applies to the Atharvaveda. |
| 8 | AV | `/passage/VG%3AAV%3ASAU%3AK10%3AS008%3AV001` | `10.8.1` | `yo bhūtaṃ ca bhavyaṃ ca sarvaṃ yaś cādhitiṣṭhati`. Deep in the Śaunaka recension, where an off-by-one in kāṇḍa or sūkta would show. |
| 9 | YV | `/passage/VG%3AYV%3AVSM%3AA01%3AV001` | `1.1.1` | `iṣe tvorje tvā vāyava stha`. Vājasaneyi Mādhyandina, adhyāya 1. |
| 10 | YV | `/passage/VG%3AYV%3AVSM%3AA31%3AV001` | `31.1.1` | The Puruṣa Sūkta: `sahasraśīrṣā puruṣaḥ sahasrākṣaḥ sahasrapāt`. The Yajurvedic keys carry no sūkta level, so this also checks that an `A31:V001` key reaches `31.1.1` and not `31.1`. |

Stream URLs, if needed directly:

```
http://127.0.0.1:8000/api/v1/audio/VEDSEARCH:RV:1.1.1/stream
http://127.0.0.1:8000/api/v1/audio/VEDSEARCH:RV:8.48.1/stream
http://127.0.0.1:8000/api/v1/audio/VEDSEARCH:RV:8.60.1/stream
http://127.0.0.1:8000/api/v1/audio/VEDSEARCH:RV:8.49.1/stream
http://127.0.0.1:8000/api/v1/audio/VEDSEARCH:RV:3.62.10/stream
http://127.0.0.1:8000/api/v1/audio/VEDSEARCH:RV:10.129.1/stream
http://127.0.0.1:8000/api/v1/audio/VEDSEARCH:AV:1.1.1/stream
http://127.0.0.1:8000/api/v1/audio/VEDSEARCH:AV:10.8.1/stream
http://127.0.0.1:8000/api/v1/audio/VEDSEARCH:YV:1.1.1/stream
http://127.0.0.1:8000/api/v1/audio/VEDSEARCH:YV:31.1.1/stream
```

## Correction, 2026-09-13

Row 3 previously told the listener to expect `agna ā yāhy agnibhir hotāraṁ tvā vṛṇīmahe`
at `VG:RV:SAK:M08:S071:V001`. **That was wrong, and wrong in the worst available
direction**: it is the text of this corpus's 8.60.1, which is exactly what the *broken*
key-for-key mapping would have played there. A human following the old sheet would have
heard the correct recitation, judged it a mismatch, and — per the instruction below —
stopped and re-derived a transform that was already right.

The text was re-read from the graph and from the source on 2026-09-13:

| Claim | Checked how | Result |
|---|---|---|
| corpus `VG:RV:SAK:M08:S071:V001` | `Passage`→`TextVersion{text_role:'PRIMARY_TEXT'}` | `tvaṁ no agne mahobhiḥ pāhi viśvasyā arāteḥ` |
| VedSearch `RV 8.60.1` `audio_text` | `VedSearchClient.audio_document` | `त्वं नो॑ अग्ने॒ महो॑भिः पा॒हि विश्व॑स्या॒ अरा॑तेः` — the same verse |
| corpus `VG:RV:SAK:M08:S060:V001` | as above | `agna ā yāhy agnibhir hotāraṁ tvā vṛṇīmahe` |
| VedSearch `RV 8.49.1` `audio_text` | as above | `अग्न॒ आ या॑ह्य॒ग्निभि॒र्होता॑रं त्वा वृणीमहे` — the same verse |
| `griffith_page(8, ·)` | direct call | `48→48`, `60→49`, `71→60`, `103→92` |

The mapping is correct; the sheet's expectation was not. This is why the **Listen for**
column is now derived from the stored text rather than written out from an edition.

## Confirmed on paper first, 2026-09-13

Before anyone listened, every row's **Listen for** value was re-derived and checked against
the file the source actually serves, so that the listening session spent its attention on
the one question paper cannot answer and on nothing else:

| Checked | Result |
|---|---|
| Ten rows: catalogue record, VedSearch ref, corpus text vs. the served file's `audio_text` | 10/10 agree, similarity 0.997–1.000 |
| Ten rows: the filename the source returns | names the requested coordinate in all ten |
| Ten `/stream` URLs | 200 `audio/mpeg`, `ID3` framing, 9.1–41.9 s decoded |
| `griffith_page(8, ·)` | `48→48`, `60→49`, `71→60`, `103→92`, and `49–59 → 93–103` |
| `audit_mappings.py --sample 40` | 127 confirmed, 0 wrong, 0 unreachable |
| `/passages/VG:RV:SAK:M08:S071:V001/audio` | serves `VEDSEARCH:RV:8.60.1`, MANTRA, EXACT |

Every expectation in the table above was therefore confirmed on paper before playback, so
a disagreement heard afterwards would have been real evidence rather than a sheet error.
None was heard.

An earlier agent session the same day had been asked to close this gate and declined to.
The machine's audio output was fine — three sound devices OK, all ten streams fetched and
decoded — but the session had no human in it, and ten `HEARD_MATCH` rows written from a
`playing` event would have turned this gate into a formality. The paper work above is what
that session did instead of guessing.

**Before comparing this sheet against the release spec.** The spec asks for four Rigvedic
samples at the Vālakhilya boundary; this sheet has three — rows 2, 3 and 4. Row 1 is
`RV 1.1.1`, a control outside Mandala 8, and says so. The two remaining boundary cases,
`8.92 → 8.81` and `8.103 → 8.92`, are in `audit_mappings.py`'s `ALWAYS_AUDIT` and are
re-checked textually on every run. Adding them here as rows 11 and 12 would be reasonable;
reporting a fourth boundary row this sheet does not contain would not.

## Recording the result

**Rows 3 and 4 decided the check**, and both were heard. They fail in opposite directions:
row 3 (`VG:RV:SAK:M08:S071:V001`) must play VedSearch `8.60.1`, and row 4
(`VG:RV:SAK:M08:S060:V001`) must play VedSearch `8.49.1` — which is the text a naive
key-for-key mapping would have played at row 3. A dropped permutation fails row 3; an
inverted one fails row 4; neither can pass both. Both matched their on-page Sanskrit, so the
Vālakhilya permutation is now confirmed in audio as well as in text.

The standing instruction, had either disagreed, was: **stop**, do not adjust the catalogue
to fit what was heard, and re-derive `griffith_page` first — a single wrong transform moves
all 55 hymns above the gap, and a per-row correction would hide that. It was not needed, and
the caution behind it stands for any future re-check: the last time this sheet disagreed
with the product, the sheet was the thing at fault.

Each row is recorded as `HEARD_MATCH`, `HEARD_MISMATCH` or `NOT_PLAYED`, with the date and
who listened.

| # | Passage | Result | Date | Listener |
|---|---|---|---|---|
| 1 | RV 1.1.1 | `HEARD_MATCH` | 2026-09-13 | Himanshu |
| 2 | RV 8.48.1 | `HEARD_MATCH` | 2026-09-13 | Himanshu |
| 3 | RV 8.71.1 | `HEARD_MATCH` | 2026-09-13 | Himanshu |
| 4 | RV 8.60.1 | `HEARD_MATCH` | 2026-09-13 | Himanshu |
| 5 | RV 3.62.10 | `HEARD_MATCH` | 2026-09-13 | Himanshu |
| 6 | RV 10.129.1 | `HEARD_MATCH` | 2026-09-13 | Himanshu |
| 7 | AV 1.1.1 | `HEARD_MATCH` | 2026-09-13 | Himanshu |
| 8 | AV 10.8.1 | `HEARD_MATCH` | 2026-09-13 | Himanshu |
| 9 | YV 1.1.1 | `HEARD_MATCH` | 2026-09-13 | Himanshu |
| 10 | YV 31.1.1 | `HEARD_MATCH` | 2026-09-13 | Himanshu |

Ten of ten. The Mandala 8 rows were confirmed by ear in both directions — `RV 8.48.1`
unshifted at VedSearch `8.48.1`, `RV 8.60.1` at `8.49.1`, `RV 8.71.1` at `8.60.1` — and
row 9 was confirmed to open `iṣe tvorje tvā vāyava stha…`. No mismatched, corrupted, silent
or obviously wrong recording was observed.

The honest statement is now: the audio mapping is verified textually **and** confirmed
auditorily, on the ten-row sample described above. That sample is the Vālakhilya boundary
plus eight rows a listener can place by ear; it is not a claim about all 16,834 catalogued
recordings, which remain textually verified only.

`HUMAN_AUDIO_CHECK = PASSED`
