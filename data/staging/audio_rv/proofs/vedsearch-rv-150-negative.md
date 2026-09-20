# Why the incumbent cannot supply these 150, and what else was searched

The 750 rows of `rejected.jsonl` rest on this. It is written up because the campaign has
twice certified an absence against the wrong surface, and because "the source does not have
it" is the claim most worth being able to re-run.

## The gap, derived rather than quoted

Read-only from the canonical store and the shipped catalogue:

- `MATCH (m:Passage:Mantra {veda:'RV'}) RETURN m.canonical_key` → **10,552** keys.
- `data/product/audio_catalog.jsonl`, rows with `veda == "RV"` → **10,402** distinct
  `scope_key`.
- Difference → **150** keys, which decompose into exactly two clusters and nothing else:

| cluster | keys |
|---|--:|
| RV 8.49.1 - 8.59.7, the eleven Valakhilya hymns | 80 |
| RV 1.117.6; 1.145.4-5; 2.23.19; 3.8.5; 6.75.4-19; 7.67.7-10; 8.13.10-33; 9.97.51-58; 9.98.1-12; 10.56.7 | 70 |

70 + 80 = 150. `data/product/audio_discovery_report.json` records the same split from the
other side: `source_has_no_audio` 70, `no_source_verse` 80, and **no `text_mismatch` key for
the Rigveda at all**.

That last absence is the answer to the question this agent was sent to ask first. For the
Atharvaveda, 495 of 1,159 are `text_mismatch` — found, then refused on text, and therefore
recoverable by a better matcher. The Rigveda has **zero**. Nothing in the 150 is a mapping
defect a matcher could recover, and nothing in it is a numbering fix. All 150 needed a source.

## The 80: the source does not publish the Valakhilya

Three measurements, in `proofs/gap-audio-004-root-cause-corrected.md`. In short: VedSearch's
Rigveda holds 10,472 verses in 10 chapters with 92 hymns in Mandala 8, which is the
1,017-hymn presentation; a live probe of chapter 8 sukta 93 on 2026-09-15 returns
`total_shloks "0"`; and 10,552 - 10,472 = 80 = the Valakhilya stanza counts summed.

## The 70: the source says there is no recitation, and it is not alone

Each of these 70 verses **is present** at VedSearch as text. Its own metadata says there is no
Sanskrit recitation: the harvested row carries `audio.sanskrit = false`. Re-derived from
`data/derived/vedsearch_harvest.json` by indexing all 10,472 rows on the source's own
`chapter_number` / `sukt_number` / `shlok_number` fields, the set of Rigvedic rows with that
flag false is **exactly these 70 coordinates and no others**. There is no third category to
look in.

Then the useful part. An independent Internet Archive parayana recording,
`rig-veda_recitation_202009` — different uploader, different master, 54 tracks — labels its own
tracks with hymn ranges and marks where it breaks off:

```
Rigveda-Track  8 - M1_S129 to M1_S145(incomplete).mp3
Rigveda-Track 27 - M6_S53  to M6_S75(incomplete).mp3
Rigveda-Track 30 - M7_S41  to M7_S67 (incomplete).mp3
Rigveda-Track 33 - M8_S4(partial) to M8_S13(incomplete).mp3
Rigveda-Track 43 - M9_S86(partial) to M9_S97(incomplete).mp3
Rigveda-Track 44 - M9_S99  to M10_S5.mp3          <- M9_S98 skipped entirely
```

Its incomplete hymns are 1.145, 6.75, 7.67, 8.13 and 9.97, and it omits 9.98. Those are
**66 of the 70** verses VedSearch flags. Two independent circulating recordings break off at
the same six places.

So the 70 are a lacuna in the parayana material that reaches this product, not a harvesting
failure at VedSearch. The four that do not line up are 1.117.6, 2.23.19, 3.8.5 and 10.56.7 —
isolated single verses inside hymns both sources otherwise carry.

All 70 are present in the Kirchheiner collection, which is the argument for preferring an
institutional deposit over a circulating copy.

## Avenues searched, and why each was declined

Six sources were evaluated for every one of the 150 keys. Full per-key dispositions are in
`rejected.jsonl` with a `reason_code`; the source-level verdicts are in `sources.jsonl`.

| source | what it offers | disposition |
|---|---|---|
| **VedaWeb 2.0 / Kirchheiner-Kinjawadekar 1983** | one Ogg file per stanza, 10,552 of 10,552 | **ACCEPTED**, all 150 |
| VedSearch | one file per verse, 10,472 rows | rejected: 70 flagged no-audio, 80 absent from its edition |
| Royal Danish Library LOAR deposit | the master behind the accepted source | rejected as a *direct* route: cassette-side files, no per-stanza boundary. Same recording, unsegmented |
| `archive.org/details/Rg-veda-shakala-auro1` | 1,028 files, one per hymn, Valakhilya included | rejected: one file is one whole hymn, no cue index, no rights statement |
| `archive.org/details/rig-veda_recitation_202009` | 54 tracks of ~44 min, hymn ranges | rejected: multi-hymn tracks, self-declared approximate ends, no cue index. Mandala 8 stops at hymn 92 |
| `archive.org/details/RigvedaChanting` (Veda Prasara Samiti) | 55 tracks of ~44 min, Public Domain Mark 1.0 | rejected: no locator below "Part NNN" at all. The only rights-clean candidate and the least mappable |

Also checked and not pursued: **Vedic Heritage / IGNCA**, whose route was withdrawn from this
product by prior decision and whose files were re-confirmed 404 in Wave 0.

The one real near-miss is `Rg-veda-shakala-auro1`. It is the only public per-hymn Rigveda
recitation found that carries the Valakhilya, and its 1,028 files reproduce the Sakala
per-mandala hymn counts 191/43/62/58/87/75/104/103/114/191 exactly, so it is an independent
structural witness that the Valakhilya belongs inline. It is declined only on granularity:
attaching a ten-stanza hymn file to one mantra is presenting a whole hymn as one mantra. The
item publishes no cue sheet, no chapter marks and no timestamps, and the `.afpk` files beside
the audio are Internet Archive fingerprint peaks rather than cue indexes, so no stanza
boundary could be established by evidence. It is recorded as the fallback if the accepted
source ever goes dark.

## What no verse needed

No verse in this domain required a proof of genuine absence: all 150 closed at `EXACT` against
a source that carries them. Nothing here claims completeness by giving up early, and nothing
was attached without a verified boundary — the boundary on every accepted row is the file
boundary, and no timestamp is asserted anywhere in the artifact.
