# RV 1.65–1.70: a merged-pair translation bound one verse at a time

**This is not a gap. It is wrong data, shipped in Product V1 and served today.**

Repair artifact: `data/staging/rv_coordinate_repair/` (`repair_table.jsonl`,
`verification.json`). Owner decision A classifies this as **AUDIO_COORDINATE_REPAIR**, not
a coverage fill — see the scope note below, because the layer affected is the translation
layer, not audio.

## The diagnosis, corrected

This document first reported that Griffith's unit *k* belongs to our verse *2k − 1* — a
one-place shift. That was incomplete, and the fuller reading changes the repair.

**Griffith renders each *pair* of our Śākala verses as one merged English unit.** Unit *k*
covers our verses *2k − 1* **and** *2k*, together. Reading unit 1 of RV 1.65 makes it plain;
both halves are present in one sentence:

> "ONE-MINDED, wise, they tracked thee **like a thief lurking in dark cave with a stolen
> cow**: Thee claiming worship, bearing it to Gods: **there nigh to thee sate all the Holy
> Ones**."

- "like a thief lurking in dark cave" renders our verse 1, `paśvā na tāyuṁ guhā catantaṁ`.
- "sate all the Holy Ones" renders our verse 2, `sajoṣā dhīrāḥ padair anu gmann upa tvā
  sīdan`.

The import bound unit *k* to our verse *k*. So the defect is in which verses each unit is
attached to, plus a scope that is never declared.

## Why the distinction matters

Under a one-place shift, 30 verses have no translation and need acquiring. Under a
merged-pair binding, **every one of the 61 verses is already covered by some unit**, and
nothing needs acquiring at all. The work is entirely re-binding and declaring scope.

Agent 3 reached the same conclusion from the source side and rejected all 30 rather than
staging them: *"Griffith's edition divides this hymn into 5 verses where the canonical
Śākala spine has 10, so no printed unit addresses this verse."* No unit addresses a single
verse, because no unit is about a single verse.

## The eight required steps, per verse

`repair_table.jsonl` carries one row per verse across all six hymns — 61 rows — with
columns for each step: the verse, its current attachment, the source coordinate, the old
mapping, the corrected mapping, and its classification.

| Classification | Verses | Meaning |
|---|--:|---|
| `CORRECT_UNIT_UNDECLARED_SCOPE` | 6 | Verse 1 of each hymn. The right unit, but the unit also covers verse 2 and never says so. |
| `MISATTACHED` | **25** | Carries a unit that renders different verses entirely. |
| `UNBOUND_BUT_COVERED` | 30 | No attachment, though a unit does cover it. |
| **Total** | **61** | |

The six "correct" rows are correct only in the weak sense that the unit does cover the
verse. None of the 61 currently declares that its translation is pair-scope.

## Step 7 — the corrected mapping is verified, not assumed

`verification.json`. For each of RV 1.65's ten verses, a distinctive English phrase and a
distinctive Sanskrit fragment were chosen **by hand**, then tested: does the English appear
in the unit the corrected mapping predicts, and the Sanskrit in the verse it is said to
render?

**10 of 10 verified.** Chosen by hand deliberately — an automatic alignment here would risk
the same class of error as the defect under repair.

| Verse | Predicted unit | English anchor | Sanskrit anchor |
|---|--:|---|---|
| 1.65.1 | 1 | "like a thief lurking in dark cave" | `tāyuṁ` |
| 1.65.2 | 1 | "sate all the Holy Ones" | `sīdan` |
| 1.65.3 | 2 | "The Gods approached the ways of holy Law" | `vratā` |
| 1.65.4 | 2 | "waters feed with praise the growing Babe" | `āpaḥ` |
| 1.65.5 | 3 | "like a fruit-bearing hill" | `girir` |
| 1.65.6 | 3 | "rushing like Sindhu" | `sindhur` |
| 1.65.7 | 4 | "Kin as a brother to his sister floods" | `bhrāte` |
| 1.65.8 | 4 | "shears the hair of earth" | `vātajūto` |
| 1.65.9 | 5 | "Like a swan sitting in the floods" | `haṁso` |
| 1.65.10 | 5 | "A Sage like Soma, sprung from Law" | `ṛtaprajātaḥ` |

## Scope note: the affected layer is translations, not audio

Owner decision A describes misattached *recordings* and 30 absent *tracks* in this span.
Measured, the audio here is clean:

| Check | Result |
|---|---|
| Audio records in RV 1.65–1.70 | **61 of 61** |
| `mapping_confidence` | `EXACT` on all 61 |
| `text_verified` | `true` on all 61 |

There are no absent recordings and no misattached recordings in this span. The Rigvedic
audio gap of 150 lies entirely elsewhere: 70 `source_has_no_audio` plus 80
`no_source_verse`, the latter being RV 8.49.1–8.59.7, the Vālakhilya, which the incumbent
source does not publish at all.

The ordering principle in decision A is right and is honoured: **repair before recovery**.
It applies to the translation layer.

## Why three safeguards passed

1. **The totals balanced.** 31 units in, 31 rows out. No count check could see it.
2. **Every key resolved.** All 31 canonical keys exist and are Rigvedic, so the staging
   validator's graph checks pass — as they should. The keys are real; they are the wrong
   ones.
3. **It presented as a coverage gap.** The 30 unbound verses appeared as "30 of the
   Rigveda's 50 missing translations", which is how this campaign's own baseline recorded
   them. The unbound verses were the visible symptom, and reading them as a gap hid the
   defect behind them.

## The repair, in order

1. Re-bind unit *k* to verses *2k − 1* and *2k*, with a declared `PAIR_SCOPE` and per-verse
   verification of the kind in `verification.json` — not by applying the formula blindly.
   RV 1.70's 11 verses against 6 units means the last unit covers one verse, not two, so the
   mapping is not uniformly a doubling.
2. Declare the scope on every affected row. A pair-scope rendering presented as a
   verse-scope translation is the defect, independent of which verse it sits on.
3. Add an import invariant that fails when a hymn's translated count is a near-half of its
   verse count.
4. Check the other three Vedas for the same edition property. Agent 3's QA found 3
   `merged_verses_undeclared` defects in its sample, so merged units are not unique to these
   six hymns — only this instance of the binding error has been measured.

**Do not import anything into this span until the re-binding is verified.** Filling these
hymns first would leave every verse carrying text and 25 carrying the wrong text.

## Registry

`GAP-TRANSLATION-006`, `IMPLEMENTATION_GAP`, owner lead. Its closure test is that every one
of the 61 rows reads correctly against its own verse's Sanskrit and declares its scope —
not that the hymns are full.
