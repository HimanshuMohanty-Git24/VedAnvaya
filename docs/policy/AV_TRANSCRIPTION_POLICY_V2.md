# Atharvaveda 1856 transcription policy `bsb-1856-devanagari-v2`

Source of truth: Roth & Whitney, *Atharva-Veda Sanhita*, Erster Band: Text,
Berlin: Dümmler, 1856. BSB/MDZ `bsb10219750`, snapshot `2026-09-07`,
4000px IIIF renderings. **The page image is authoritative.**

## What supersedes v1

`bsb-1856-devanagari-v1` transcribed the consonant-vowel skeleton only. The
1856 print marks Vedic accent on nearly every line, so v1 output silently
dropped a real feature of the page on 333 of 360 units, and two readers who
both dropped it agreed with each other while both being wrong. v2 makes the
accent layer part of the transcription, and renders the page in
accent-legible bands (`scripts/crop_atharvaveda_leaf.py`) rather than as a
downsampled whole leaf.

## Accent convention of the source

The print uses the convention standard for European Vedic editions of the
period, the same one used for the Rigveda:

| Printed mark | Meaning | Stored codepoint |
|---|---|---|
| horizontal bar **below** the syllable | anudātta | `U+0952` ॒ |
| vertical stroke **above** the syllable | svarita | `U+0951` ॑ |
| no mark | udātta (and unaccented) | nothing |

Udātta is **not** marked in this print, so an unmarked syllable is not
evidence of an unaccented syllable. Absence is stored as absence; it is
never inferred to be a mark and never inferred to be its lack.

## Rules

1. Reproduce exactly what is printed, including accent marks, daṇḍas, and
   the numerals inside `॥ ॥`. The printed numerals are Devanagari digits.
2. The print abbreviates repeated pādas with `॰` (`U+0970`). Keep the
   abbreviation as printed. **Never expand it** — the expansion is an
   editorial act and its content is not on the page.
3. Anything genuinely unreadable is `[?]`, and the unit's status becomes
   `CHARACTER_UNCERTAIN`. Do not guess a plausible word.
4. Never consult, recall, or reconstruct from any other edition of the
   Atharvaveda. GRETIL, TITUS, VedaWeb and Orlandi-derived text are
   prohibited as correction sources under the independence firewall.
   A reading that comes from memory of another edition rather than from
   these pixels is contamination even when it is right.
5. Store source accents as printed. Normalization is derived downstream and
   never overwrites `text_devanagari`.

## Statuses

- `VERIFIED_EXACT` — two independent readings agree codepoint for codepoint.
- `VERIFIED_WITH_ORTHOGRAPHIC_NOTE` — readings differ only in a documented
  orthographic equivalence.
- `ACCENT_UNCERTAIN` — readings agree on syllables, differ on accent.
- `CHARACTER_UNCERTAIN` — readings differ on a character.
- `BOUNDARY_UNCERTAIN` — readings differ on where the unit ends.
- `STRUCTURAL_REVIEW_REQUIRED` — readers disagree on how many units the page
  prints, or on their numbering.
- `SOURCE_AMBIGUOUS` — the page itself does not resolve the reading.
- `PHILOLOGICAL_REVIEW_REQUIRED` — needs a human Vedicist.

Only `VERIFIED_EXACT` and `VERIFIED_WITH_ORTHOGRAPHIC_NOTE` are release
eligible. A merged reading synthesised from two disagreeing readings has no
traceable source and is never produced.
