# GAP-AUDIO-004's recorded root cause is wrong, in both halves

The gap registry, `data/gap_registry.json`, records for `GAP-AUDIO-004`:

> **root_cause**: "The audio source numbers Mandala 8 by a different edition convention, and
> the Griffith permutation needed to map the Valakhilya insertion was never applied. Mapping
> naively would give 55 hymns of Mandala 8 the wrong recitation."
>
> **source_dependency**: "NONE for the Valakhilya set - the recordings exist at the source
> under a different numbering."

Both statements are disproven. They matter because together they say the gap is a bug we own
and can fix for free, which would have sent Wave 1 looking for a transform that is already
there instead of for a source that was genuinely needed.

## The permutation is applied, and it is correct

`src/vedagraph/product/audio/vedsearch.py::vedsearch_coordinates` routes every Rigvedic
sukta number through `vedagraph.editions.griffith_page` before it is used:

```
return VerseCoordinates("RV", mandala, griffith_page(mandala, sukta), verse)
```

`src/vedagraph/editions.py` implements the Valakhilya offset with the constants
`_VALAKHILYA_FIRST = 49`, `_VALAKHILYA_LAST = 59`, `_VALAKHILYA_PAGE_OFFSET = 44`.

The shipped catalogue says so on its own rows. Every one of the 16,834 records in
`data/product/audio_catalog.jsonl` carries this `mapping_method`:

> "Mapped from the canonical key to the source's own verse coordinates -- for the Rigveda
> through the Valakhilya edition permutation, since the source numbers Mandala 8 in
> Griffith's order -- and then confirmed by comparing the text the source states this
> recording recites against this corpus's text for the same key."

And it demonstrably works on the far side of the insertion. `data/product/audio_mapping_audit.json`
records the transform's own output on five Mandala 8 samples:

| our key | source item |
|---|---|
| `VG:RV:SAK:M08:S048:V001` | 8.48.1 |
| `VG:RV:SAK:M08:S060:V001` | 8.49.1 |
| `VG:RV:SAK:M08:S071:V001` | 8.60.1 |
| `VG:RV:SAK:M08:S092:V001` | 8.81.1 |
| `VG:RV:SAK:M08:S103:V001` | 8.92.1 |

Our 8.60 to 8.103 land on the source's 8.49 to 8.92, which is the -11 shift, and all five
were text-confirmed. The 55 hymns the registry warns about are already mapped correctly.

## The recordings do not exist at the source under any numbering

VedSearch does not publish the Valakhilya at all. Three independent measurements:

1. **Arithmetic.** `data/product/audio_discovery_report.json` records `source_verses` 10,472
   against `our_verses` 10,552. The difference is 80, which is exactly the eleven Valakhilya
   hymns: 10+10+10+10+8+8+5+5+4+3+7.
2. **Structure, from the local harvest.** `data/derived/vedsearch_harvest.json` (harvested
   2026-09-12) holds 10,472 Rigvedic rows across chapters 1 to 10 and no others. Indexed by
   the source's own `chapter_number` / `sukt_number` / `shlok_number` fields, its Mandala 8
   contains 92 hymns, numbered 1 to 92 with none missing. There is no eleven-hymn appendix
   anywhere, and no twelfth chapter. The source publishes the 1,017-hymn presentation of the
   Sakala Rigveda, in which the Valakhilya is omitted rather than appended.
3. **Live, today.** `POST https://vedsearch.org/api/v1/rigved/shlok/search/by/chapter` with
   `{"chapter_number": 8, "sukt_number": 93, "language": "sanskrit"}` returned, on
   2026-09-15:

   ```json
   {"data":{"shloks":[],"total_shloks":"0","bookmark":"nil"}}
   ```

   The same request with `sukt_number` 92 returns rows. So hymn 93 is absent, not
   unharvested, and `griffith_page`'s target for our 8.49 does not exist.

## The correction

`griffith_page` maps our 8.49 to the source's 8.93. Griffith's own edition does print the
Valakhilya as book 8 hymns 93 to 103, so the transform is right about Griffith. VedSearch is
not Griffith: it drops the eleven hymns instead of moving them. The transform therefore has
no target, and returns a coordinate the source has never carried.

That is a **source dependency**, not an implementation defect. The 80 verses needed an
acquisition, and got one: the VedaWeb delivery of the Kirchheiner-Kinjawadekar recording
carries all 80 at stanza level, with the Valakhilya inline at 8.49-8.59.

## What should be amended

- `GAP-AUDIO-004.root_cause`: the permutation is applied; the source omits the hymns.
- `GAP-AUDIO-004.source_dependency`: not `NONE`; a new source was required and found.
- `GAP-AUDIO-004.closure_test`: its listening requirement stands and is **not** met by this
  artifact. See `proofs/listening-review-not-performed.md`.
