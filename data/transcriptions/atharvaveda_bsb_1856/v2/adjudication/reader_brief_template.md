# Independent Reader Brief — VedaGraph Atharvaveda accent gold

You are an independent paleographic reader. Your only job is to read ONE printed line
of a scanned 1856 Devanagari book and record what accent marks you see and which
aksara each one belongs to. You are one of three readers working on this line in
isolation. You will not see the other readers' work and must not look for it.

## Source (the only permitted evidence)

Roth & Whitney, *Atharva Veda Sanhita*, Berlin 1856.
Bayerische Staatsbibliothek / MDZ scan `bsb10219750`, canvas **430**, printed
line index **5** (0-based, counting inked lines from the top of the text block,
including any running head).

Crops, rendered at approximately 1:1 with the native 2024 px scan:

- seg1: `C:\Users\HKM49\AppData\Local\Temp\claude\d--VedaGraph\2f4bcbd5-e27f-4a76-bfb4-a4540840593b\scratchpad\av_gate\crops\leaf_00430_line05_seg1.png`
- seg2: `C:\Users\HKM49\AppData\Local\Temp\claude\d--VedaGraph\2f4bcbd5-e27f-4a76-bfb4-a4540840593b\scratchpad\av_gate\crops\leaf_00430_line05_seg2.png`

## Geometry — so you can report one global coordinate

The full line is **3216 px** wide in leaf-block coordinates.
seg1 covers block-x `0 .. 1655`. seg2 covers block-x `1560 .. 3215`.
They overlap by **96 px**. Each segment was then rescaled to 1568 px wide,
a factor of **0.9469**.

To convert what you measure in a rendered crop to global line-x:

    seg1:  global = seg1_x / 0.9469
    seg2:  global = 1560 + (seg2_x / 0.9469)

Report every accent x position in GLOBAL line-x.

## What this print does with accent

Established from this same scan in earlier sessions — not from any external text.

- **anudatta** (U+0952): a short broad **flat dash** sitting in the gutter **below**
  the glyph body of its own line. Roughly 20-45 px wide, 5-18 px tall in block
  coordinates; distinctly wider than tall.
- **svarita** (U+0951): a narrow **upright stroke** standing clear **above** the
  sirorekha (headline). Roughly 6-16 px wide, 20-45 px tall; distinctly taller
  than wide.

These are the only two accent marks in this print. There is no udatta mark.

## The central trap: line attribution

The anudatta bars of the line **above** yours sit in the gutter between that line and
yours, and are routinely mistaken either for svarita of your line or for your own
bars. Separate the bands before you attribute anything: project row ink and locate
your line's sirorekha, its glyph bodies, and its own bar band. The line above's bar
band sits roughly one full line-pitch too high. **Report the y bands you measured.**

## Known false positives — reject these by shape, not by position

- vocalic-ṛ descenders (as under कृ, पृ): curved **hooks**, 21-33 px tall, not
  straight dashes.
- a final halanta / virama tail.
- i / ī / e / o / au matras above the headline: wide curved shapes, 50-68 px across,
  not narrow strokes.
- anusvara: a round dot about as wide as it is tall, not an upright stroke.
- u / ū matra descenders belonging to the line above: they run continuously into that
  line with no white gap.
- a danda or double-danda slice passing through a band and leaving it at both ends.

## Fount note

The standalone **अ** in this 1856 fount reads like ऋ or श्र to a modern eye. Read it
as अ.

## Forbidden — a breach invalidates the whole calibration

- Do **not** consult GRETIL, TITUS, VedaWeb, Orlandi, Whitney's translation, any
  digital or printed Atharvaveda text, or any web resource. Do not search the web.
- Do **not** read, run, or import any of: `scripts/extract_atharvaveda_accents.py`,
  `src/vedagraph/ingest/av_accent_binder.py`, `scripts/run_av_calibration.py`,
  or anything under `data/transcriptions/atharvaveda_bsb_1856/`. You must not learn
  what the automatic detector found, and you must not see another reader's probe.
- Do **not** reconstruct the line from memory of the Atharvaveda and then fit marks
  to that reconstruction. Read the ink. If your memory suggests a reading the ink
  does not support, follow the ink and say so in your notes.

## Permitted

- Viewing the two crops above (use the Read tool on the PNG paths).
- Rendering your own finer crops of the SAME line for more magnification:

      python scripts/crop_atharvaveda_line.py 430 <your_own_outdir> --line 5 --segments 4

- Measuring the source image directly with PIL — row and column ink profiles,
  connected-component extents, blob sizes. Measuring the scan is reading the source.
  `scripts/crop_atharvaveda_leaf.py` (`find_text_block`, `leaf_path`) and
  `scripts/crop_atharvaveda_line.py` (`find_lines`, `VERTICAL_PAD`) are permitted
  helpers: they only locate the line, they say nothing about accent.

## Deliverable

Do the reading, then return **exactly one JSON object** as the final content of your
report, fenced in a ```json block, with these keys:

```
{
  "reader": "{reader}",
  "canvas_index": 430,
  "line_index": 5,
  "text_devanagari": "<the full line in Devanagari, with U+0952 / U+0951 placed
       immediately after the aksara that carries the mark; keep word spacing as
       printed; include the terminal danda(s) and verse numeral if present>",
  "anudatta_count": <int>,
  "svarita_count": <int>,
  "accent_count": <int, = anudatta + svarita>,
  "unclear_count": <int, aksaras you could not read with confidence>,
  "y_bands": "<the row bands you measured: line-above bar band, your svarita band,
       your sirorekha, your body, your own bar band, and the next line's>",
  "carriers": [
    {"x_global": <int, mark centre>, "type": "anudatta"|"svarita",
      "word": "<the word it falls in>", "aksara": "<the aksara cluster it sits on>",
      "word_index": <int, 0-based word position in the line>,
      "aksara_index": <int, 0-based aksara position inside that word>}
  ],
  "boundary_interpretation": "<how you decided word boundaries — where the sirorekha
       breaks — and for every mark that sits near a boundary between two aksaras or
       two words, which side you assigned it to and why>",
  "notes": "<magnification used; every false positive you rejected and the shape
       reason; anything you could not resolve>"
}
```

Keep `text_devanagari` clean Devanagari — do not put `[?]` inside it. Record
uncertainty in `unclear_count` and `notes` instead.

Accuracy matters far more than speed. If a mark is genuinely ambiguous, say so
rather than guessing silently.
