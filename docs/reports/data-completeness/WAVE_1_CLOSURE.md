# Wave 1 — closure

All six specialists returned. Every artifact passes
`scripts/validate_staging_artifact.py --graph` at 100% evaluation coverage on every check.

**Nothing has been imported.** The canonical graph is unchanged at 108,779 nodes and
265,295 relationships, re-counted after all six agents finished. Every figure below is
*stageable*, not *live*. The distinction is the whole point of the staging contract, and
the numbers must not be quoted as product coverage until Wave 3 imports them and reads the
counts back out of the database.

## Translation — 1,514 of the 2,927 gap now stageable

| Veda | Gap | Importable | PROBABLE (staged, not importable) | Refused, with reason | Residual |
|---|--:|--:|--:|--:|--:|
| RV Śākala | 50 | 13 | 4 | 33 | 37 |
| SV Kauthuma | 1,844 | 507 | 735 | 602 | 1,337 |
| YV Mādhyandina | 72 | 50 | 1 | 21 | 22 |
| AV Śaunaka | 961 | 944 | 0 | 17 | 17 |
| **Total** | **2,927** | **1,514** | **740** | **673** | **1,413** |

If imported, translation coverage would move from 17,283 to 18,797 of 20,210 — 85.5% to
93.0%.

## Audio — 939 stageable at EXACT

| Veda | Before | Stageable | After, if imported | Of total |
|---|--:|--:|--:|--:|
| RV | 10,402 | +150 | 10,552 | **100%** |
| SV | 0 | +0 | 0 | 0% — a verified zero |
| YV | 1,752 | +25 | 1,777 | 90.0% |
| AV | 4,680 | +764 | 5,444 | 93.2% |
| **Total** | **16,834** | **+939** | **17,773** | **87.9%** from 83.3% |

No `VERIFIED_SEGMENT` mapping was needed in any domain, and **no timestamp is asserted
anywhere in Wave 1**. Every accepted row is a whole-file or whole-stanza mapping.

## Attribution and the Samavedic melodic layer

- Unmodelled dedication 5,498 → 5,465; metre gap 5,610 → 5,493.
- The Atharvaveda gained 83 verse-level source-explicit deity rows and 383 metre rows.
- A melodic layer now exists where none did: 1,136 of 1,844 Samavedic verses notated, four
  gāna Works proposed, 475 recordings fetched and genuinely checksummed.

## Three gaps were not gaps

The most valuable thing Wave 1 produced is not coverage. It is that three of the four audio
gaps, and half the Yajurvedic translation gap, were defects on our side of the line —
closable with no acquisition at all.

| Domain | What it actually was |
|---|---|
| YV audio | Our comparator. 25 of 33 refusals recovered by fixing it. |
| AV audio | Our coordinates. VedSearch divides the corpus into 754 sūktas against our 731, so past the first split in a kāṇḍa we addressed the wrong verse. 740 of 915 refusals closed. |
| YV translation | Our stage file's gap labels were digit-confusion OCR of printed verse numbers. The text was present throughout. 39 of 72. |
| RV audio | Neither. A genuine source dependency the registry had recorded as an unapplied transform. |

In each case the refusal had been correct and the *address* was wrong — which is the
failure a coverage count cannot see, because a wrong address resolves just as cleanly as a
right one.

## One defect is worse than any gap

`RV_1_65_TO_1_70_MISALIGNMENT.md`. Twenty-five translations shipped in Product V1 are
attached to the wrong verse, because Griffith merges verse pairs in those six hymns and the
import bound his units one-for-one. Three safeguards each passed: the totals balanced,
every key resolved, and the 30 unbound verses presented as a coverage gap — which is how
this campaign's own baseline recorded them.

Realignment must precede importing the absent verses. Filling the hymns first would leave
every verse carrying text and 25 carrying the wrong text.

## Corrections to Wave 0

Wave 0's reconnaissance was good and four of its conclusions were wrong. Recording them so
the source map is not trusted past its evidence:

1. **IGNCA Mādhyandina audio is published**, not 404. The probed path is dead;
   `Shukla_Yajurveda_Madhyandin_MP3/SYMS_CHAP_NN.mp4` answers 206 for adhyāyas 1–40 and 404
   at 41. The blocker is rights and granularity, not availability.
2. **Griffith's Sāmaveda Part II has nine Books**, matching the nine prapāṭhakas, not six.
   And the 1,875-against-1,844 delta is **our** spine's, not his.
3. **Samavedic notation is 98.1% Devanagari Extended**, only 1.9% Vedic Extensions. A regex
   on the named block finds 2% of it. Our own `source_artifacts.jsonl` was already right.
4. **Vedavani covers all 20 kāṇḍas and is not keyless** — its filenames carry kāṇḍa plus a
   running index, and its CSVs carry a Devanagari transcript. Its real limit is granularity:
   773 of 9,997 transcripts are a whole mantra.

And one of the lead's own relays was wrong: the comparator defects were passed to the
Atharvaveda agent as the likely cause of its 495 mismatches. They cost that Veda exactly
one verse. The agent measured rather than inheriting — Atharvavedic skeletons have a median
of 80 characters and only 30 of 5,839 exceed difflib's 200-element trigger — and then found
a larger, different cause. A relayed prediction should be labelled as one, and this one was.

## Registry prescriptions that are wrong

Three registry entries prescribe the wrong remedy. Wave 1 measured each:

- `GAP-AUDIO-002` says re-run with accent- and sandhi-insensitive matching. `skeleton()`
  already was, and re-running changes 1 of 495. Its claim that the 420 `no_source_verse`
  need another source is also wrong — 385 were in VedSearch all along.
- `GAP-AUDIO-004` says the Griffith permutation was never applied and
  `source_dependency: NONE`. Both halves are wrong.

A gap registry is a hypothesis about a cause, and Wave 1 shows the hypotheses need
measuring before they are worked. Closing a gap against a wrong prescription is how a
campaign spends a week acquiring material it already had.

## Open items for the lead, in the order they matter

1. **Realign RV 1.65–1.70 before importing anything into those hymns.**
2. **Decide the playback mode.** The Rigvedic 150 come from a source permitting
   non-commercial use but requiring a written agreement to republish, so
   `local_copy_permitted` is false and they are staged `REMOTE_DIRECT` while the existing
   16,834 are all `PROXIED_STREAM`. Range requests are supported (verified: 206 with
   `accept-ranges: bytes`), so seeking works, but caching is blocked.
3. **Rule on 31 forced Yajurvedic addresses.** They have no independent content control and
   rest on interpolation plus a 1,889-row regression guard. Typed EXACT and flagged
   `address_forced_without_content_control`. Excluding them makes that recovery 19, not 50.
4. **Give the Samaveda a home for its running Saṃhitā number** before importing
   `MUSICALIZED_AS`, or the 495 edges cannot be re-derived from the graph.
5. **Investigate the LOAR deposit.** 224 cassettes, all four Vedas, six oral traditions,
   named reciters including two for the Samaveda. Wave 0 partly closed the Samaveda audio
   gap on "every candidate has an unnamed reciter". Whether it is ārcika saṃhitā-pāṭha
   rather than gāna is **not established** — the agent that found it attached no claim, and
   neither does this.
6. **197 Atharvavedic mantras are reachable** — each has a contiguous run of 2–3 Vedavani
   files whose concatenation is letter-identical to the mantra. What blocks them is one
   `media_url` per record, a model decision. Closing them takes the Atharvaveda to 96.6%.

## What Wave 1 did not do

- **Nobody listened to anything.** 0 of 150, 0 of 771, 0 of 475, 0 of 25. Section 22 is not
  satisfied in any audio domain and no artifact claims otherwise.
- **The Samaveda still has no ārcika verse audio.** 0 of 1,844, recorded as a verified zero
  over an assessed population rather than as an unknown.
- **No canonical write occurred.**
