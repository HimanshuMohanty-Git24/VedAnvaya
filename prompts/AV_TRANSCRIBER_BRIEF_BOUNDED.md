# Atharvaveda 1856 page transcription — bounded protocol

This is the same task as `AV_TRANSCRIBER_BRIEF.md` under a work budget. Read
that brief for the rules on units, accents, the fount, and the independence
firewall — all of them still bind. This file changes only *how much looking*
you are allowed to do.

## Why there is a budget

The unbounded protocol resolves accent placement by cropping individual
words and re-reading them. It is accurate and it is far too slow to reach
458 leaves. This protocol exists to find out how much of that accuracy
survives when the looking is bounded — so transcribe as well as you can
inside the budget, and be honest in the record when the budget is what
stopped you. A `[?]` that means "I was not allowed to look again" is a
useful measurement. A guess dressed as a reading is not.

## The budget

- Read the leaf's band images **once**, all in a single message.
- You may crop and re-read at most **three** regions of the page afterwards,
  for the three places where re-reading buys you the most. Use
  `scripts/crop_atharvaveda_leaf.py` only if you need a band re-rendered;
  otherwise crop with a short inline Python snippet against the band PNGs.
- Do not zoom word by word. Do not re-read a region you have already
  resolved.
- Then write the output file. Aim to finish in about **12 tool calls total**.

## What to do with what you cannot resolve

Mark it `[?]` and count it in `unclear_count`. If you can read the syllable
but not its accent, transcribe the syllable without an accent mark and say
so in `structural_marker` — for example `accent not resolved on pada c
within the bounded protocol`. Do not infer an accent from the metre, from
the word, or from what the accent usually is on that word. That inference is
the contamination this whole pipeline is built to keep out, and it is
undetectable downstream once written.

## Output

Exactly as in the main brief: one JSONL file at the `<OUTFILE>` you are
given, one line per unit, same keys, same order, UTF-8, written with the
Write tool.

## Report back

At most 5 lines: units transcribed, total accent marks recorded, how many
`[?]` you left, and — importantly — whether the budget or the page was what
limited you.
