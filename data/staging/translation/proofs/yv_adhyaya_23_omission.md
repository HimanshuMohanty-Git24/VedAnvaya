# VS 23.20-31: a genuine printed omission, proved from the print itself

Twelve of the Yajurveda's 72 missing translations are `VG:YV:VSM:A23:V020` through `V031`.
They are rejected, and this is the evidence — including the one piece that turns "absent" into
"deliberately omitted", which is a different claim and a stronger one.

## 1. The shape of the hole

Re-parsing the pinned 2026-09-07 snapshot of `wyvbk23.htm` gives **53 printed units against 65
canonical mantras**, and the printed labels run:

```text
~ 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 32 33 34 ... 57 68 59 60 61 62 63 64 65
```

The jump is 19 → 32. Twelve slots, no units. (The stray `68` between 57 and 59 is a separate,
recovered OCR corruption of `58`; it is accepted in `rows.jsonl`.)

## 2. Griffith printed the omission, he did not merely skip it

The unit labelled 19 ends like this, verbatim from the snapshot:

```text
Thee we invoke, troop-lord of troops, Thee we invoke, the loved ones' lord.
Thee, lord of treasures, we invoke. My precious wealth! . . . . . . . . . . . . . . . . . . . . . .
```

That row of dots is the printed omission mark. The preceding unit, labelled 18, ends with the
`Amba! Ambika! Ambalika!` line — i.e. the print stops exactly where the asvamedha dialogue's
explicit section begins. This is the translator declining to render, not a transcription loss,
and not a cross-reference. The shipped pipeline's own `PRINTED_OMISSION` verdict for these
twelve is therefore correct on the page rather than by inference.

## 3. Avenues checked for the text elsewhere

| Avenue | Query / probe | Result |
|---|---|---|
| sacred-texts.com live | `hin/wyv/wyvbk23.htm` | host returns 403 behind a Cloudflare challenge; and the pinned snapshot of the same page is what shows the omission |
| archive.org `WhiteYajurVeda` (Griffith 1899 scan) | fetched `..._djvu.txt` via `/stream/`, 1.04 MB of OCR; searched `TWENTY-THIRD`, `Ganiki`, `Mahishi`, `Kumarika`, `embrace` | the scan is the **same edition**, so it carries the same omission; none of the dialogue's catchwords appear anywhere in the OCR |
| en.wikisource `Yajurveda` | — | **a redirect to Keith's Taittiriya Samhita**, a different Veda and a different recension. Not a VSM witness at all (Wave 0 trap, re-confirmed) |
| Keith, *Taittiriya Samhita* (public, complete) | — | Krishna Yajurveda. The asvamedha dialogue stands at TS 7.4.19, not in the Vajasaneyi arrangement. Using it would be a cross-recension substitution of a *different samhita*, which section 1 forbids outright |
| Eggeling, *Satapatha Brahmana* XIII (SBE 44, public) | — | a Brahmana that discusses the rite; it is not a translation of the Samhita mantras and cannot be addressed to a VSM mantra key |
| Modern VSM translations (Devi Chand; Tulsi Ram; Ravi Prakash Arya / Surendra Pratap eds.) | web search | in copyright and/or commercially published; two of them are *edited* Griffith, so they inherit rather than repair the omission |

## 4. Verdict

`SOURCE_PRINTED_OMISSION`, on the strength of the printed ellipsis rather than on absence.

Closing these twelve needs either a public-domain translation of the Vajasaneyi Madhyandina
asvamedha section that no avenue above produced, or a typed
`MODEL_ASSISTED_LITERAL_TRANSLATION` at `quality_class: MODEL_ASSISTED_DERIVATION` attributed
to no translator. The second is available on the campaign's own tier 4 and was not taken here
because it is an owner decision for an explicit passage, not a data-completeness detail.
