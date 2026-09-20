# Recension evidence, and the traps checked

Every row in this artifact carries `recension_verified: true`. This is what that rests on,
and what was checked to make sure it is not resting on "it is Samavedic, so it is ours".

## Kauthuma, positively

1. **Page-title path.** Every notation and gana page used here sits under
   `sa.wikisource.org` title prefix `samavedah/kauthumiya/samhita/` -- the source names the
   school in the address, not in prose that could be paraphrased away.
2. **The arrangement, read off the accented page's own headers.** `sasvara purna` runs
   `purvarcikah/chanda arcikah 1.1.1 ...` through `uttararcikah/navamaprapathakah`: two
   arcikas, nine Uttararcika prapathakas. That is the Kauthuma arrangement. Benfey's
   Ranayaniya has six books, and Griffith follows Benfey; neither could produce these
   headers.
3. **Textual agreement with the Kauthuma text this project already holds.** 1,136 verses
   of the accented page are byte-identical, under a declared normalisation, to the arcika
   text at `VG:WORK:SV:KAU`, **and** the pairing is order-consistent under a
   longest-common-subsequence alignment. This is the strongest of the three, because it is
   a measurement against our own spine rather than a label on someone else's page.
4. **Book names.** The four gana books are the Kauthuma four: `gramageyah`,
   `aranyakageyah`, `uhaganam`, `uhyaganam`.

## Traps checked mechanically, not trusted

- `recension.no_foreign_recension_inside_kauthuma`, 1,132 records evaluated, 0 hits, over
  every gana unit key, structural path and performance filename for: `jaimin`,
  the Devanagari for Jaiminiya, `ranayan`, the Devanagari for Ranayaniya, `benfey`,
  `griffith`, `stevenson`, `samasram`.
- **Wayne Howard 1988** decodes the **Jaiminiya** notation. It is not cited anywhere in
  this artifact and was not used to interpret a single mark. The notation here is recorded
  as **data** -- codepoints, counts and the raw string -- and is deliberately NOT
  interpreted into pitches, because the Kauthuma-school counterpart (van der Hoogt 1929)
  was not located digitally in Wave 0 and is not on disk.
- **`jaiminiya-arseya`** sits beside the Kauthuma Arseya in archive.org search results. No
  Arseya material of either school is used here; the sole index consulted was the gana
  subtree itself.
- **`Samved.xlsx`** was not opened. It is a verified trap (890 rows against a promised
  1,875; 985 numbers absent across 89 disjoint runs; private-use-area font hacks).
- **`sv-kauthuma-saswara.pdf`** was not fetched. Verified 404 in Wave 0 and not re-probed.
  Note that the accented text this artifact does use is a DIFFERENT artifact: a
  sa.wikisource page, already inside our own page inventory as an `ANCILLARY` row, which
  no prior pass had opened.

## What is NOT recension-verified, and is therefore not used

`IISHSamaVeda` states no recension anywhere on the item. Kerala Samavedic tradition is
substantially Jaiminiya, so "probably Kauthuma" is an inference from the Iyer parvan names,
not a statement by the source. No byte of it was fetched and no row points into it.
