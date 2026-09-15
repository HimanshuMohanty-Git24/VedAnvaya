# The sAmagAnam cue index: located, read, and NOT extracted

Reconnaissance's most valuable single find was that the `sAmagAnam` PDFs print, per gana,
an audio clip number and an mm:ss timestamp into the IISH recording -- the only
source-provided timing artifact found anywhere in Wave 0, for any Veda.

**It is real. I looked at it.** And it yields zero rows in this artifact. Both halves of
that sentence matter, so both are evidenced here.

## What it actually looks like

Locator, exact, re-findable by hand:
`archive.org/download/sAmagAnam/sAmagAnam_01_Agneyam_GrameyaGaanam_1-180_1hr_51min_PR_Iyer_jp2.zip`
-> inner file `..._jp2/sAmagAnam_01_Agneyam_GrameyaGaanam_1-180_1hr_51min_PR_Iyer_0002.jp2`
(4959 x 7009 px; the page is hand-headed `AAGNEYAM GG / A1.1`, `Page 3`).

The page is ruled notebook paper, handwritten in Malayalam script, and carries **three**
coordinate columns at once:

| where | what | example on this page |
|---|---|---|
| left margin, written as a fraction | IISH **clip number** over **mm.ss** | `1/9.38`, `1/10.10`, `1/10.45`, `1/11.14`, `1/11.42`, `1/12.42` |
| inline, in parentheses | arcika verse and gana ordinal | `(6.1)`, `(6.2)`, `(7.1)`, `(7.2)`, `(8.1)`, `(8.2)`, `(9.1)` |
| right margin | **gana running number** | `12`, `13`, `14`, `15`, `16`, `17`, `18` |

So it is not merely a timestamp list. It is a three-way index: arcika verse <-> gana
running number <-> clip + offset. That is exactly the join the campaign wants.

A pilot transcription of that one page, by eye, recorded here as a PILOT and promoted
nowhere:

| clip | mm.ss | gana running no. | arcika/gana ordinal |
|--:|--:|--:|--:|
| 1 | 9.38 | 12 | 6.1 |
| 1 | 10.10 | 13 | 6.2 |
| 1 | 10.45 | 14 | 7.1 |
| 1 | 11.14 | 15 | 7.2 |
| 1 | 11.42 | 16 | 8.1 |
| (none printed) | -- | 17 | 8.2 |
| 1 | 12.42 | 18 | 9.1 |

Internal consistency check that the transcription passes: the offsets are strictly
increasing, and all of them fall inside `SV001.mp3`, whose archive.org-reported length is
2648.04 s = 44:08.

## It is an ANCHOR index, not a segment map -- measured on a second page

This is the part that changes what the index is worth, so it was checked on a second page
deeper into the same volume rather than assumed from the first.

Volume 01 is **40 pages** covering GG 1-180, about 4.5 ganas per page. Page 11
(`AAGNEYAM GG / A1.4`, i.e. adhyaya 1 fourth khanda) holds five ganas -- `(35.1)` through
`(36.1)`, right-margin running numbers 56-60 -- and carries **exactly one** left-margin
cue: `1/33.05`. The other four ganas on that page have no cue at all; `(36.1)` has a bare
tick mark instead.

So the density is not one cue per gana and it is not even stable: 6 cues for 7 ganas on
page 3, **1 cue for 5 ganas on page 11**. The timestamps mark selected anchor points in
the recording, and a complete human transcription of every margin column would therefore
still NOT yield a timestamp for every gana. Any downstream segment map built from this
would have to interpolate between anchors -- which is inventing a boundary, and is
refused.

Corroboration that the two pages belong to one continuous reading: 12.42 on page 3 and
33.05 on page 11 are both clip 1 and in order, so clip 1 alone spans roughly GG 12-60.
That is consistent with the volume filenames, which sum to 10h24 for the five Grameyagaana
volumes plus 5h29 for the five Aranyakagaana volumes -- 15h53 against about 24 clips of
~44 min each.

## Why it produced zero rows

Four reasons, each independently sufficient.

1. **No text layer, and the OCR is noise.** `pypdf` extracts 0 characters from every page
   of every volume (checked on volumes 01, 09 and 10; volume 10 page 1 reports
   `text_len=0, images=43`). archive.org's own `_djvu.txt` derivative exists but is
   Malayalam OCR of handwriting: a `\d{1,2}[:.]\d{2}` sweep over volume 01's 30,535
   characters returns 25 "timestamps" of which the sample includes `4.a8`, `aa.21`,
   `1:74` -- `1:74` is not a time. Harvesting that file would have produced invented
   timestamps that look extracted.

2. **The target recording has no rights statement.** Re-verified in this pass:
   `archive.org/metadata/IISHSamaVeda` returns **no `licenseurl` and no `rights` field**.
   `opensource_audio` and `community` are archive.org collections, not a licence grant. A
   segment map is only useful pointing at a recording the product may cite and cache; this
   one cannot be asserted as licensed.

3. **The index is bounded at 24 of 64 clips by the source's own statement**, and
   permanently: "By clip number 24, audios of Grama gaanam (GG) and Aranyaka gaanam (AG)
   are completed. The remaining 40 audio clips are for Uha gaanam and Uhya gaanam. Uha
   gaanam and Uhya gaanam text is really massive actually intimidating and error prone.
   Those are not prepared here, and there is no plan to post them." Uha + Uhya are 421 of
   the 657 gana units in this artifact, so the cue index can never reach 64% of them.

4. **`sAmagAnam` is CC BY-NC-ND 4.0**, which is one-way incompatible with the CC BY-SA
   corpus it would sit beside. Reading factual cue numbers out of it is fact extraction
   rather than a derivative work, so this is the weakest of the four reasons -- but it is
   a live constraint on any republication of the notation itself.

## What would close it

A human transcription pass over the margin columns of volumes 01-10, followed by the
recension check reconnaissance already specified (the Gayatram on RV 3.62.10 against the
Kauthuma notation at the printed offset). The cost is real but now bounded: volume 01 is 40
pages for 180 ganas, so the ten volumes are on the order of 330 pages of two handwritten
margin columns -- a transcription task, not a parser. (The 1,419-page figure in
reconnaissance belongs to the separate typeset PPN PDFs, not to this scanned set.)

But note what it would and would not buy, given the anchor density measured above: a
complete transcription yields **anchor** offsets for a minority of ganas inside clips 1-24,
covering Gramageya and Aranyakageya only, pointing into a recording with no rights
statement. It is worth doing to make the corpus navigable. It is NOT a per-gana segment
map and must not be presented as one.

`FOUR_VEDA_SNAPSHOT_PROVENANCE.md` F5 -- "No timing or cue artifacts exist for any audio"
-- **is stale and should be amended**, not rediscovered: a cue artifact exists, is located
to the page, and its structure is documented above. What is true is the narrower statement
that no cue artifact is *machine-readable*.
