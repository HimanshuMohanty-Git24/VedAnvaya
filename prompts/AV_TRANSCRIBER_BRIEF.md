# Atharvaveda 1856 page transcription — worker brief

You are transcribing pages of a printed book from its scan. Read
`docs/policy/AV_TRANSCRIPTION_POLICY_V2.md` first; it is short and binding.

## Independence firewall — read this before anything else

You must transcribe **only what you can see in the supplied images**. Do not
consult GRETIL, TITUS, VedaWeb, sacred-texts, any file under `data/raw/`, any
other Atharvaveda edition, or your own memory of the Atharvaveda text. If a
line is hard, look harder at the pixels or mark it uncertain. Producing the
"right" reading from memory instead of from the page is a firewall breach
and is worse than an honest `[?]`, because it destroys the evidence that two
independent readings are independent.

Do not read any other agent's transcription of these pages, and do not read
anything under `data/transcriptions/`.

## Procedure, per leaf

1. Render the bands:
   `python scripts/crop_atharvaveda_leaf.py <CANVAS> <OUTDIR>`
   (run from the repo root; `<OUTDIR>` is given to you).
2. Read **every** band image with the Read tool, in order. Read them all in a
   single message.
3. Transcribe every text unit the page prints.

## What a unit is

One numbered mantra, i.e. the text running up to and including its
`॥ <numeral> ॥` terminal. A mantra that begins on this leaf and is not
terminated on it is still a unit: transcribe the part that is printed here
and set `"spans_canvases": "starts"`. A mantra whose terminal appears here
but whose start was on the previous leaf gets `"spans_canvases": "ends"`.

In the prose kāṇḍas (15, 16, and the paryāya sections) the unit is the
numbered paryāya sentence; put its number in `mantra` and the paryāya number
in `paryaya`.

## The fount, and the one error this book actually produces

This is an 1856 Berlin Devanagari fount, and its `अ` does not look like a
modern `अ`. To an eye trained on modern type it reads as `ऋ` or `श्र`. This
is the dominant transcription error on these pages, and it is dominant
because it is invisible from the inside: the wrong reading looks like a
word. When a line seems to begin with `ऋ` or `श्र`, look again — in this
fount that shape is nearly always `अ`.

## Transcribe exactly

- Accent marks are part of the text. Subscript bar → `U+0952` (॒), placed
  after the syllable it sits under. Superscript stroke → `U+0951` (॑),
  placed after the syllable it sits over. Unmarked syllables get nothing.
  Nearly every line of this book carries accents; a line you transcribe with
  none is far more likely to be your omission than the printer's.
- Keep the abbreviation circle `॰` (`U+0970`) exactly where printed. Never
  expand an abbreviated pāda.
- Keep printed daṇḍas `।` `॥` and Devanagari numerals as printed.
- Genuinely illegible character → `[?]`.

## Output

Write one JSONL file, `<OUTFILE>`, given to you. One line per unit, keys in
this exact order, no extra keys:

`{"canvas_index": int, "mdz_image_id": "bsb10219750_000NN", "printed_page": int|null, "kanda": int|null, "sukta": int|null, "mantra": int|null, "paryaya": int|null, "text_devanagari": "...", "accent_marks_present": bool, "unclear_count": int, "spans_canvases": null|"starts"|"ends", "structural_marker": "...", "reader": "<READER>", "transcription_policy": "bsb-1856-devanagari-v2"}`

- `structural_marker`: the running head verbatim, the printed page number,
  marginal sūkta numerals, and any colophon printed on the leaf. This is
  free text; be specific about where on the leaf each thing sits.
- `printed_page` / `kanda` / `sukta`: read them off this page (running head,
  margin). If the page does not print one, use `null`.
- Write the file with the Write tool. Use UTF-8. Do not append to an
  existing file; create it fresh.

## Report back

Reply with **at most 6 lines**: leaf(s) done, unit count per leaf, whether
accents were present and reproduced, and anything on the page you could not
resolve. Do not paste transcribed text into your reply.
