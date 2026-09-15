# Proof: every candidate rejected for recension, and what identified it

All measurements 2026-09-15, taken from each item's own `archive.org/metadata/` document rather
than from its description prose.

## The finding: five items, one master

Reconnaissance flagged `IISHAShuklaYajurVeda` as the recension trap and identified it by
**runtime fingerprint** — 37.51 h matching the Veda Prasar Samiti Kāṇva product. A fingerprint
is suggestive but not an identification, and the brief required that I *positively establish*
recension rather than assume it. Measuring the whole family does establish it.

| item | mp3 | total hours | file naming | licence |
|---|--:|--:|---|---|
| `suklayajurveda_202107` | 54 | **37.34** | `Suklayajurveda Part 001…054.mp3` | PD Mark 1.0 |
| `IISHAShuklaYajurVeda` | 55 | **37.51** | `INTRODUCTION TO YAJURVEDA` + `SYV001…SYV054` | **none** |
| `IISH_SHUKLA_YAJUR_VEDA` | 55 | **37.86** | `INTRODUCTION TO YAJURVEDA` + `SYV001…SYV054` | **none** |
| `SHUKLA-YAJUR-VEDAM` | 55 | **36.47** | `శుక్లయజుర్వేదం_పార్ట్_00…_54_` | CC BY-NC-ND 4.0 |
| `shukla-yajur-veda_recitation` | 80 | **36.96** | mixed; terminates `Part_53/Part_54-Shukla_Yajur_Veda.mp3` | **none** |

Five items. **One master: 54 numbered parts, ~37 hours.** The variation is re-encoding and the
occasional added introduction or per-adhyāya recut.

**What identifies the master.** `suklayajurveda_202107` names its creator outright:
**"Veda Prasara Samithi"**. `docs/FOUR_VEDA_AUDIO_SOURCE_INVENTORY.md` §records that item
confirmed **Kāṇva** against Veda Prasar Samiti's own archived recension table — verbatim,
*"SHUKLA YAJUR VEDA .. Kanva Sakha"*. `shukla-yajur-veda_recitation` is recorded in the same
document as self-titled `(Kanva)`.

So the chain is: named creator → that creator's own recension table → Kāṇva. That is a positive
identification, not an inference from duration.

**A second, independent check.** A 54-part division divides neither of the Mādhyandina
structures: not 40 adhyāyas, not 1,975 mantras, not 303 anuvākas. Nothing in the Mādhyandina
Saṃhitā has 54 of anything. Whatever these recordings are cut along, it is not our text's
articulation.

**Verdict on all five: `WRONG_RECENSION_KANVA`.** Rejected. None is used for any row, at any
confidence. Three of the five additionally carry no licence at all, and the fourth is ND, which
would forbid the per-mantra segmentation this gap needs even if the recension were right.

## `shukla-yajur-vedaH-kANva-samhitA-vedamu`

Honestly self-labelled Kāṇva in its own identifier. Recorded not as a candidate but as the
reference specimen behind the working rule this domain runs on:

> Any "Shukla Yajurveda" audio item that does not say **Mādhyandina** is this master until
> proved otherwise.

## What positively establishes Mādhyandina for the rows that were accepted

VedSearch names no recension anywhere — not on its pages, not in its API. So the recension on
all 33 staged rows is established, not claimed, from four things:

1. **Structure.** The source publishes the Yajurveda as 40 chapters holding exactly **1,975**
   verses. vedapeetha.org: *"The Mādhyandina Śākhā contains 40 Adhyāyas, 303 Anuvākas and 1975
   verses."* This repository's Vājasaneyi-Mādhyandina corpus is 40 adhyāyas / 1,975 mantras.
   `docs/FOUR_VEDA_AUDIO_SOURCE_INVENTORY.md` records Kāṇva at **~2,086** mantras. A
   1,975-verse structure cannot be Kāṇva.
2. **A sub-structural check.** IGNCA's own page "Yajurveda, Madhyandina Samhita, Adhyaya 01"
   enumerates mantras **1–31**; this corpus's adhyāya 1 holds exactly **31**. The agreement is
   not just at the total, it holds at the first division.
3. **Per-mantra text identity.** Over all 1,975 coordinate-aligned pairs the
   orthography-insensitive skeleton similarity has median **1.0000** and 5th percentile
   **0.9862**; 1,949 of 1,975 are at or above 0.97. Against 800 deliberately mispaired verses
   the same instrument gives median 0.2514 and a **maximum of 0.5690**. The populations do not
   approach each other.
4. **Per row, recorded on the row.** Every accepted row carries its own
   `payload.text_match_score`; the lowest accepted is 0.9777.

That is what "Mādhyandina specifically" means on these rows. Not "Śukla". Not "Yajurveda".

## Not searched, deliberately

Kṛṣṇa-Yajurvedic recitation — Taittirīya, Maitrāyaṇī, Kaṭha, Kapiṣṭhala — was not pursued as a
candidate at all. It is abundant and it is forbidden. Recording the omission so it reads as a
decision rather than a gap in the search. The one place it surfaced anyway was vedapeetha.org,
which has audio for Taittirīya and none for Mādhyandina; that is logged as
`NO_AUDIO_ON_SOURCE`, not as a near miss.
