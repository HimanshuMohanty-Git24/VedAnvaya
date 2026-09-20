# The five avenues behind every negative in this domain

Each of the 191 rows in `rejected.jsonl` has a per-mantra record in
`no_public_recording.jsonl` naming all five. This file is the shared narrative so the
per-mantra records can stay short, and so the *search* is auditable and not only its result.

## 1. VedSearch — exhausted by text, not by coordinate

The original run asked one question per mantra: does the source's verse *at our coordinate*
recite our text. This artifact asked a different one: does **any** of the source's 5,916
Atharvavedic rows recite our text. Every mantra in the gap was reduced to its letters and
compared against all 5,916, with no coordinate assumption. That is what found the hymn
division, and it is also what makes the negatives strong: a mantra rejected here is one whose
text is not recited anywhere in the source's whole Atharvaveda, or is recited only where the
source publishes no audio.

Snapshot: `data/derived/vedsearch_harvest.json`, harvested 2026-09-12. 5,671 of 5,916 rows
carry a Sanskrit audio flag.

**The flag was re-probed live on 2026-09-15, because a stale flag would turn a real recording
into a fabricated absence.** 14 verses whose harvested flag was false were fetched from
`/api/v1/attachment/audio/atharved/{id}/sanskrit`: 14 of 14 returned no audio payload. The
flag is current.

## 2. Vedavani — exhausted by transcript, at two granularities

`huggingface.co/datasets/sanganaka/Vedavani-Dataset`, Apache-2.0, ACL 2025,
arXiv:2506.00145. 9,997 Atharvavedic samples, 17.77 h, kāṇḍas 1–20, a Devanagari transcript
per file. Searched twice:

- **whole-file**: every one of the 9,997 transcripts compared for letter identity with the
  mantra. 773 transcripts, covering 766 distinct mantras, are letter-identical to a whole
  mantra; 46 of those were in this gap and survived all seven acceptance conditions.
- **contiguous run**: within the mantra's kāṇḍa, the samples' transcripts were concatenated in
  index order and searched for the mantra's letters aligned to sample boundaries. This is what
  separates a real negative from a deferral: 197 gap mantras *are* recited, across 2 or 3
  files, and are recorded as `unresolved` with `open_route:
  STITCH_CONSECUTIVE_VEDAVANI_SAMPLES` rather than as absences.

A mantra rejected here failed both.

## 3. Internet Archive — enumerated, then probed

`advancedsearch.php?q=(atharva OR atharvaveda) AND mediatype:audio` returned **48** items.
Nine were probed through `archive.org/metadata/{id}`, file by file, with durations:

| item | audio files | hours | finest granularity |
|---|--:|--:|---|
| `paippalAda-shAkhA` | 54 | 90.59 | per kāṇḍa — **and Paippalāda** |
| `AtharvaVedam` | 44 | 59.58 | per kāṇḍa ("Kandam 01"–"Kandam 21") |
| `Atharvaveda-shaunaka-shAkhA` | 22 | 38.94 | ~2 h per file |
| `atharvaveda_202107` | 28 | 19.20 | ~40 min per part |
| `IISH_Atharva_Veda` | 28 | 19.20 | the same master, same durations |
| `atharvaved-tune` | 21 | 18.64 | per kāṇḍa |
| `atharvaveda1` / `atharvaveda2` | 20 | 15.49 | ~46 min per file |
| `AtharvaVeda1-40` + three siblings | 189 | 13.74+ | ~10 min per track, no index |
| `atharvavedamshaunaka` | 0 | — | text, not audio |

**Not one publishes a per-mantra file, a printed timestamp, a cue index or a chapter index.**
The finest Śaunaka granularity in public is one file per kāṇḍa. Attaching any of them to a
mantra would require inventing a boundary, which the campaign forbids and which this artifact
does not do anywhere.

## 4. Wikimedia Commons — verified absent

`action=query&list=search&srsearch=Atharvaveda filetype:audio&srnamespace=6` → 80 results.
`srsearch=atharva veda recitation` → 68 results. Inspected: every hit is Samavedic gāna,
Rigvedic śastra recitation, or a dictionary pronunciation of the word "Veda" in Dutch, German
or Czech. There is no Atharvavedic recitation on Commons.

## 5. Vedic Heritage Portal (IGNCA) — prior decision, not re-probed

`vedicheritage.gov.in/samhitas/atharvaveda-samhitas/shaunaka-samhita/`. Assessed earlier in
this repository as `PERMISSION_REQUIRED`, with no credited reciter and therefore no resolvable
consent chain, and the route was removed from this product by that decision. Deliberately not
re-probed: the blocker is a rights question that a fresh HTTP request cannot answer.

## What the negatives actually claim

Not "no recording of this mantra exists". The claim each proof record makes is:

> no public recording of this mantra is **attachable at `MANTRA` scope with verified
> boundaries**.

For roughly two thirds of the 191 — the kāṇḍa 15 and 16 prose in particular, where our 141
and 93 units face the source's 219 and 103 — the recitation is very probably inside one of the
public per-kāṇḍa files. What is missing is a boundary anyone states. That is a different fact
from absence, and it is stated as the different fact it is.
