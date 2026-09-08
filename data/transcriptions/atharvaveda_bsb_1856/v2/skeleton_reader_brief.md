# Independent Reader Brief — VedaGraph Atharvaveda Sanskrit skeleton

You are an independent paleographic reader. Your job is to read the Sanskrit
**skeleton** of one printed leaf of a scanned 1856 Devanagari book and record what
is printed on it, unit by unit.

You are one of two readers working on this leaf in isolation. You will not see the
other reader's work and must not look for it. Do not try to find out what any
previous reading of this leaf said.

## Source — the only permitted evidence

Roth & Whitney, *Atharva-Veda Saṃhitā*, Erster Band: Text. Berlin: Dümmler, 1856.
Bayerische Staatsbibliothek / MDZ scan `bsb10219750`.

Artifact id: `BSB.AV.SAUNAKA.ROTH_WHITNEY.1856.SCAN`

Your images are listed in the packet JSON given to you in the task. They are the
leaf's text block downsampled to the resolution of the real IIIF master and split
into a top and a bottom half, with a small vertical overlap. **This is native
resolution.** The stored 4000px leaf is a server-side upscale; enlarging further
adds no detail, only interpolation.

The crop keeps the leaf margins, so the **printed page number** and the **marginal
sūkta numeral** are inside your images. Use them.

## What to transcribe: the skeleton, not the accent

This print marks Vedic accent: **anudātta** as a short flat dash *below* the glyph
body, and **svarita** as a narrow upright stroke *above* the headline (śirorekhā).
Udātta is unmarked.

**Do not transcribe the accent marks.** A separate pipeline reads them
geometrically. Your `text_devanagari` must contain **no** U+0951, U+0952, or any
Vedic Extensions codepoint (U+1CD0–U+1CFF).

But you must *recognise* accent marks, because the single largest error in this
fount is mistaking one for part of a letter:

- A **svarita** stroke standing above the headline over a consonant looks almost
  exactly like a **repha** (र्, the `r` hook of a conjunct). It is not one.
  `दश॑वृक्ष` is easily misread as `दर्शवृक्ष`. A repha in this fount is a small
  hooked comma that leans; a svarita is a straight upright tick clear of the
  headline. When in doubt, check whether the neighbouring aksaras of the same line
  carry the same mark at the same height — a whole row of them is the accent band,
  not a row of rephas.
- An **anudātta** dash under a glyph is not a vowel sign, not a virāma tail, and
  not part of the letter above it. Note also that the dashes sitting in the gutter
  *above* your line belong to the line above it.

## Do transcribe, faithfully

- every aksara of the printed text, in printed order
- **avagraha** (ऽ) where printed
- **anusvāra** (ं) and **candrabindu** (ँ) as printed — these are not accent marks
- **visarga** (ः)
- **virāma / halanta** where printed
- **daṇḍa** (।) and **double daṇḍa** (॥) exactly as printed
- Devanagari **numerals** as printed (mantra numbers, page numbers, the detached
  pluti/kampa numerals such as the `३` in `तन्वे३ शं`)
- word spacing as printed

## Fount traps in this specific 1856 type

- The standalone **अ** reads like **ऋ** or **श्र** to a modern eye. It is **अ**.
  `अथो` will look like `ऋथो`; `अधि` like `ऋधि`. Read them as अ.
- **ग्र** ligature: `ग्राह्या` can look like `याह्या`. Look for the ग body.
- **भ** and **म** are close in this fount; so are **व** and **ब**.
- Long **ऽ** avagraha and a comma-like blemish are distinguishable by baseline
  position: avagraha sits on the line, foxing does not.
- Bleed-through from the facing page is visible as faint grey ghost text. It is
  **not** ink on your leaf. Ignore it.

## Unit of record

One record per **mantra / stanza** as the page numbers them: the text up to and
including its terminal `॥ n ॥`. In the prose **paryāya** books, one record per
printed numbered paryāya unit.

For each unit state where it sits, **read off the page, not from memory**:

- `kanda` — the kāṇḍa. The running head is centred at the top and reads
  `॥ अथर्ववेदे <kāṇḍa> । <sūkta list> ॥`. The first numeral is the kāṇḍa.
- `sukta` — the sūkta. Sūkta starts are marked by a numeral in the **margin**
  (e.g. `॥ ९ ॥`), and the running head lists the sūktas the page covers.
- `mantra` — the numeral printed at the end of the unit.
- If the page genuinely does not print what you need to fix a coordinate, record
  `null` for that coordinate. **Do not infer it and do not guess it.** A `null` is
  handled correctly downstream; a wrong number is not.
- If a unit begins on this leaf and is completed on the next (or vice versa),
  transcribe only the part printed on **this** leaf and say so in `notes`, setting
  `spans_canvases` to the other canvas index.

Do not include the running head or the printed page number as a text unit. Record
them in `structural_marker` instead.

## Uncertainty

If you cannot resolve a character, put `[?]` at that position in
`text_devanagari` and increment `unclear_count`. Do not silently guess. A unit
containing `[?]` is routed to review rather than released, which is the correct
outcome — an invented character that two readers happen to share is the one
failure this whole process exists to prevent.

## Forbidden — a breach invalidates the run

- Do **not** consult GRETIL, TITUS, VedaWeb, Orlandi, the Paippalāda recension,
  Whitney's translation, any digital or printed Atharvaveda text, or any web
  resource. Do not search the web.
- Do **not** read anything under `data/transcriptions/atharvaveda_bsb_1856/`, and
  do not read `scripts/reconcile_atharvaveda_v2.py`,
  `scripts/build_atharvaveda_canonical.py`, or any other reader's output.
- Do **not** reconstruct the text from your memory of the Atharvaveda and then fit
  the ink to it. Read the ink. Where your memory of the received text disagrees
  with what is printed, **follow the print** and say so in `notes`. This edition
  has its own readings and its own errors, and reproducing them is the point.

## Permitted

- Viewing your packet images with the Read tool.
- Re-cropping the **same** leaf yourself for more magnification:
  `python scripts/av_reader_packet.py <canvas> <your_own_outdir> --mode lines`
  or `python scripts/crop_atharvaveda_line.py <canvas> <outdir> --line N --segments 2`.
  Remember this adds no information beyond native resolution; it only makes the
  type appear larger.
- Measuring the image with PIL.

## Deliverable

Write your readings to the JSONL file path given in your task, **one JSON object
per line**, in printed order, with these keys exactly:

```
{"canvas_index": <int>, "mdz_image_id": "bsb10219750_000NN",
 "printed_page": <int or null>, "kanda": <int or null>, "sukta": <int or null>,
 "mantra": <int or null>, "paryaya": <int or null>,
 "text_devanagari": "<the printed unit, accent-free>",
 "unclear_count": <int>, "spans_canvases": <int or null>,
 "structural_marker": "<running head, page number, marginal numerals as printed>",
 "notes": "<what you could not resolve; where the print differs from the received text>",
 "reader": "<R1 or R2, as given in your task>",
 "reader_kind": "MODEL_VISUAL_READ",
 "reader_identity": "<model id and agent label, as given in your task>",
 "run_id": "<as given in your task>",
 "transcription_policy": "bsb-1856-devanagari-v2"}
```

`reader_kind` is `MODEL_VISUAL_READ` because you are a model reading a scan. Never
write `HUMAN_REVIEWED` or `HUMAN_VISUAL_READ`; those are reserved for a real
person and asserting one of them here would make the release provenance false.

Text must be NFC-normalised Devanagari. Accuracy matters far more than speed or
coverage. A leaf that is blank, a title page, a plate, or otherwise carries no
Sanskrit text is a valid result: write no records and say so in your report.
