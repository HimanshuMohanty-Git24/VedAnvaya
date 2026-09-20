# Proof: exhaustive search for per-mantra Mādhyandina audio

Section 10 requires, for any blocked verdict: at least three independent source avenues, the
exact queries, the traditions checked, the nearest available recording, and why mapping it was
rejected. All probes 2026-09-15.

## Avenue 1 — IGNCA / Vedic Heritage Portal (Government of India, Ministry of Culture)

Live, correct recension, per adhyāya. Rejected on rights and granularity.
Full probe log: `proofs/ignca-madhyandina-live.md`.

## Avenue 2 — archive.org, exhaustive over `mediatype:audio`

Not a keyword browse: four queries against the advanced-search API, restricted to audio, so the
result is a count of the whole population rather than a page of hits.

| query | `numFound` |
|---|--:|
| `(madhyandina) AND mediatype:audio` | **1** |
| `(madhyandin) AND mediatype:audio` | **0** |
| `(vajasaneyi) AND mediatype:audio` | 12 — **all** LibriVox Upaniṣad readings in English, zero Saṃhitā recitation |
| `(shukla yajur) AND mediatype:audio` | 13 |

**The single Mādhyandina audio item in all of archive.org is
`mAdhyandina-shAkhA-vedamu`.** Measured from its own metadata: 5 MP3, 8.82 h, named
`Adhyay(1-7)`, `(8-12)`, `(13-17)`, `(18-22)`, `(23-27)`. Rejected on three independent
grounds:

1. **Coverage** stops at adhyāya 27 of 40. Of the 190 no-audio gap verses, 60 sit in adhyāyas
   29, 32, 33, 34 and 35 and are outside it entirely.
2. **Granularity** — ~1.8 h monolithic blocks spanning five adhyāyas each, with no cue index, no
   timestamps, no per-mantra marker. A mantra boundary derived from that would be guessed.
3. **Rights** — no `licenseurl`, and the item's own description reads `vedamu copy of
   mAdhyandina-shAkhA`. It is a third-party mirror of vedamu.org, which publishes its audio
   "open to listen, and not to download". A mirror does not create a licence.

This is the **nearest available recording** in the correct recension, and the three reasons above
are why mapping it was rejected.

The other 12 `shukla yajur` audio items are dealt with in `proofs/recension-rejections.md`.

## Avenue 3 — VedSearch, the incumbent per-mantra source

VedSearch is the only source anywhere in this survey that publishes Yajurvedic recitation
**one file per mantra**, which is why it supplies all 1,777 mapped rows. It is not a partial
coordinate set: it holds all 1,975 verses of text. 190 of those rows simply carry no
`audio.sanskrit` attachment.

Re-probed live today, not taken from the 2026-09-12 harvest: a random sample of **40 of the
190**, seed 20260915. Every one returned `row present, audio.sanskrit still absent`.
**0 of 40 flipped.** The 190 are current absences, not stale flags.

Per-row detail is in `rejected.jsonl` under `reprobe_result`.

## Avenue 4 — vedapeetha.org

`vedapeetha.org/pages/vajasneyi-samhita-madhyandina` — fetched today. Descriptive text about the
recension; **no audio, no media link, no reciter, no licence**. The site does host audio, under
**Taittirīya Saṃhitā** — Kṛṣṇa-Yajurveda, explicitly forbidden for this gap. This is the
recension trap in its mildest form: the right title, audio elsewhere on the site, wrong Veda.

Retained as a **source of recension evidence** rather than of audio. It states:

> "The Mādhyandina Śākhā contains 40 Adhyāyas, 303 Anuvākas and 1975 verses."

## Avenue 5 — vedamu.org direct

`https://vedamu.org/` — curl reports HTTP code **000**, zero bytes: the connection fails. This
matches reconnaissance's `ECONNREFUSED`. Recorded as unreachable *today* rather than gone. It is
the upstream of avenue 2's single Mādhyandina item and publishes reference-only terms in any
case, so reachability would not change the verdict.

## Web searches run, verbatim

1. `Vajasaneyi Madhyandina Samhita audio recitation per mantra download free`
2. `"Madhyandina" Shukla Yajurveda chanting mp3 archive.org adhyaya complete`
3. `Madhyandina Vajasaneyi Samhita individual mantra audio api per verse recitation website`

Every audio-bearing lead these returned is disposed of above or in
`proofs/recension-rejections.md`. Search 2's top hit, `archive.org/details/SuklaYajurved`, is
titled "shukla yajur ved (MADHYANDINIYA SAMHITA)" with the creator field abused to read
"40 adhyaya" — and holds **zero media files**. It is a book scan in
`booksbylanguage_sanskrit`. Recorded because that title is precisely the trap this domain is
full of.

## Traditions and recensions checked, and what was refused

| Tradition / recension | Status |
|---|---|
| Śukla YV, **Vājasaneyi-Mādhyandina** | the target. Two sources exist: IGNCA (per adhyāya, permission-required) and vedamu via archive.org (adhyāyas 1–27, unlicensed, monolithic). Neither gives a verifiable per-mantra boundary. |
| Śukla YV, **Kāṇva** | abundant — at least five archive.org items, all one ~37 h master. **Refused**: different recension. See `proofs/recension-rejections.md`. |
| **Kṛṣṇa** YV / Taittirīya | abundant, including on vedapeetha. **Refused**: forbidden outright by the brief; a different Veda's text. |
| Maitrāyaṇī, Kaṭha, Kapiṣṭhala | not searched as audio candidates — Kṛṣṇa-Yajurvedic, so refused by the same rule before cost is incurred. Recorded so the omission is deliberate rather than accidental. |

## Verdict

Per-mantra Mādhyandina audio for the residual 198 is **not obtainable under this campaign's
rules today** — but the reason is **rights and granularity, not absence**. The material exists,
is the right recension and is online. That is not
`BLOCKED_EXTERNAL_SOURCE_UNAVAILABLE`.

The cheapest route to the remaining 198 is not a source hunt at all: it is a permission request
to IGNCA for the 40 Mādhyandina files, followed by a verified segmentation pass against the
per-adhyāya mantra text IGNCA itself publishes. That is a decision for a human, not for Wave 1.
