# Product V1 — audio listening check (outstanding, human)

Every mapping in `data/product/audio_catalog.jsonl` is `EXACT`, `text_verified`, and
`MANTRA`-scoped. That verification is **textual**: it compares the text VedSearch states a
recording recites against this corpus's text for the same key. It does not establish that
the audio file at that URL contains that recitation.

Nothing in this repository has listened to a recording. The automated audit
(`scripts/audio/audit_mappings.py`) re-derives coordinates and re-reads text; a browser
run can confirm the `playing` event fires and bytes arrive. Neither is an auditory test,
and neither should be reported as one.

This check is therefore **open** and requires a human with working audio.

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

## Recording the result

Rows 3 and 4 decide the check. If both recitations match their on-page Sanskrit, the
Vālakhilya permutation is confirmed in audio as well as in text, and the mapping may be
described as heard. If either does not match, **stop**: do not adjust the catalogue to fit
what was heard. Re-derive `griffith_page` first, because a single wrong transform moves all
55 hymns above the gap, and a per-row correction would hide that. Confirm against the table
above before concluding the transform is wrong — the last time this sheet disagreed with the
product, the sheet was the thing at fault.

Record each row as `HEARD_MATCH`, `HEARD_MISMATCH` or `NOT_PLAYED`, with the date and who
listened.

| # | Result | Date | Listener |
|---|---|---|---|
| 1 | — | — | — |
| 2 | — | — | — |
| 3 | — | — | — |
| 4 | — | — | — |
| 5 | — | — | — |
| 6 | — | — | — |
| 7 | — | — | — |
| 8 | — | — | — |
| 9 | — | — | — |
| 10 | — | — | — |

Until a human records a result here, the honest statement is: the audio mapping is
verified textually and unverified auditorily.

`HUMAN_AUDIO_CHECK = OUTSTANDING`
