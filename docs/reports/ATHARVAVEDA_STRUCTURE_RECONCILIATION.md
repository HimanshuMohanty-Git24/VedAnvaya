# Atharvaveda structure, reconciled against the 1856 print

**Work:** Atharvaveda Saṃhitā, Śaunaka recension (`VG:WORK:AV:SAU`)
**Source:** Roth & Whitney, *Atharva-Veda Sanhita*, Erster Band: Text, Berlin:
Dümmler 1856. BSB/MDZ `bsb10219750`, artifact
`BSB.AV.SAUNAKA.ROTH_WHITNEY.1856.SCAN`, snapshot `2026-09-07`, 478 IIIF
leaves at width 4000.
**Derivation:** every coordinate below was read off the running head printed
on the leaf image itself. No digital Atharvaveda text was consulted at any
point — not GRETIL, not TITUS, not VedaWeb, not the Orlandi-derived figures,
and not the repository's own GRETIL-derived `atharvaveda_pilot_v1`.

## What the print physically contains

| | Leaves |
|---|---|
| Front matter (`n1`–`n14`) | 14 |
| Numbered text (`n15` = printed p. 1 … `n472` = printed p. 458) | 458 |
| Back matter (`n473`–`n478`) | 6 |
| **Total canvases** | **478** |

Leaf-to-page mapping is `printed_page = canvas_index − 14`, verified at three
independent points: `n15` = p. 1, `n30` = p. 16, `n300` = p. 286.

Back matter is a two-page Dümmler publisher's advertisement (`n473`–`n474`),
blank flyleaves and the rear pastedown (`n475`–`n477`), and the rear cover
board (`n478`). None of it is Saṃhitā text.

## Kāṇḍa count: 20

Established twice from the print, not from expectation.

1. The running head's kāṇḍa number changes 20 times across the 458 text leaves.
2. The printed colophons agree at every boundary spot-checked. `n27` (p. 13)
   prints `॥ द्वितीयः प्रपाठकः ॥ ॥ प्रथमं काण्डं समाप्तम् ॥`; `n118` (p. 104)
   prints `॥ षष्ठोऽनुवाकः ॥ ॥ द्वादशः प्रपाठकः ॥ ॥ पञ्चमं काण्डं समाप्तम् ॥`.

The text closes on `n472` (p. 458) with three colophons:

```text
॥ नवमोऽनुवाकः ॥
॥ [?]स्तकाण्डं नाम विंशं काण्डं समाप्तम् ॥
॥ अथर्ववेदसंहिता च संपूर्णा ॥
```

The first akṣara of the second line is not legible with confidence in this
fount and is left `[?]` rather than completed from memory. The rest of that
line states that the twentieth kāṇḍa is complete, and the third states that
the Saṃhitā is complete. That is the print certifying its own extent.

## Per-kāṇḍa extent

| Kāṇḍa | Canvases | Printed pages | Leaves | Highest sūkta in the heads |
|---:|---|---|---:|---:|
| 1 | n15–n27 | 1–13 | 13 | 35 |
| 2 | n28–n43 | 14–29 | 16 | 36 |
| 3 | n44–n63 | 30–49 | 20 | 31 |
| 4 | n64–n90 | 50–76 | 27 | 40 |
| 5 | n91–n118 | 77–104 | 28 | 31 |
| 6 | n119–n158 | 105–144 | 40 | 142 |
| 7 | n159–n185 | 145–171 | 27 | 118 |
| 8 | n186–n207 | 172–193 | 22 | 10 |
| 9 | n208–n228 | 194–214 | 21 | 10 |
| 10 | n229–n255 | 215–241 | 27 | 10 |
| 11 | n256–n280 | 242–266 | 25 | 10 |
| 12 | n281–n302 | 267–288 | 22 | 5 |
| 13 | n303–n315 | 289–301 | 13 | 4 |
| 14 | n316–n327 | 302–313 | 12 | 2 |
| 15 | n328–n337 | 314–323 | 10 | 18 |
| 16 | n338–n342 | 324–328 | 5 | 9 |
| 17 | n343–n345 | 329–331 | 3 | 1 |
| 18 | n346–n366 | 332–352 | 21 | 4 |
| 19 | n367–n404 | 353–390 | 38 | 72 |
| 20 | n405–n472 | 391–458 | 68 | 143 |
| | | | **458** | **731** |

The last running head in the book is `॥ अथर्ववेदे २० । १४३ ॥`.

## Comparison with the previously observed 731 / 5,839

The instruction was not to force equality with the Orlandi-derived figures.
Nothing was adjusted toward them. Here is what the print gives on its own.

| Figure | From the 1856 print | Previously observed | Difference |
|---|---|---|---|
| Kāṇḍas | 20 | 20 | 0 |
| Sūktas | 731 | 731 | 0 |
| Mantras / stanzas | **not derivable from this evidence** | 5,839 | **cannot be stated** |

The sūkta agreement is a genuine independent convergence: 731 here is the
sum of the twenty per-kāṇḍa maxima in the table above, obtained by reading
running heads, with no knowledge of the comparison figure used in deriving
it.

**The mantra total is open, and cannot be closed by this evidence.** A
running head names the kāṇḍa and the sūkta(s) appearing on that page. It
never names a mantra count. Mantra totals exist only in the verse-terminal
numerals `॥ १ ॥`, `॥ २ ॥` … printed inside the text block, so obtaining them
requires transcribing the text of every leaf. Until the full transcription
is complete, any Atharvaveda mantra total in this repository is a figure
carried over from another edition, not a reading of this print, and it is
recorded as such rather than reported as reconciled.

## Two caveats on the 731

**It is formally a lower bound.** `highest_sukta_seen` is the largest sūkta
number a head names in that kāṇḍa. A sūkta that opened and closed without
the head being updated would leave no trace in this evidence. In practice
the final leaf of every kāṇḍa was legible and its head named the kāṇḍa's
last sūkta, so each bound is tight against the printed heads — but the
evidence is head evidence, and the distinction is kept rather than rounded
away.

**One head disagrees with its own page.** `n159` (p. 145) prints the head
`७ । १-६`, while the leaf's own marginal sūkta markers run 1–5, with sūkta 5
continuing onto `n160`, whose head prints `७ । ५-९`. The head is one sūkta
too high. This is the only head/body disagreement in the book.
`header_literal` keeps the printed head; `sukta_first` / `sukta_last` carry
the body reading. Nothing is silently corrected in either direction.

Internal consistency was checked across all 458 text leaves: head ranges are
monotone within each kāṇḍa, no sūkta number in `1..highest` is skipped by the
heads in any kāṇḍa, and no head starts more than one sūkta above the previous
head's last sūkta. The `n159`/`n160` pair is the only place where two
consecutive heads overlap by more than one sūkta.

**One leaf carries no head at all.** `n15`, the first page of the text, prints
none. Its coordinates were read from the body, which opens `॥ ओम् ॥` with
marginal sūkta markers `॥ १ ॥` and `॥ २ ॥`.

## Passage identity

Atharvaveda identity is FINAL and is preserved unchanged. The build uses the
existing `avs_kanda_identity`, `avs_sukta_identity` and `avs_mantra_identity`
functions, so a mantra that occurs at the same structural coordinate keeps
the key, URN and UUID it already had. Nothing is renumbered because the 1856
edition presents a sūkta differently from another edition.

The print exposed **no** identity contradiction. The `n159` head anomaly is a
disagreement between a page's head and its own margin, not between two
structural occurrences, and it resolves to a single unambiguous body reading.

## Prose and Book 20

Kāṇḍas 15 and 16, and the paryāya sections elsewhere, are prose rather than
metrical verse; their units are numbered paryāya sentences and are carried
with `paryaya` populated alongside `mantra`. Kāṇḍa 20 is the largest in the
book at 68 leaves and 143 sūktas, and it abbreviates repeated pādas heavily
with the circle `॰` (`U+0970`). The transcription policy keeps every such
abbreviation exactly as printed and never expands one, because the expansion
is an editorial act whose content is not on the page.
