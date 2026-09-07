# Atharvaveda Śaunaka transcription protocol — BSB/MDZ Roth & Whitney 1856

`bsb-1856-devanagari-v1`

Governing rule: **RIGHTS-13**. Read it in `data/registry/rights.yaml` before transcribing.

---

## 1. Why the transcription is a SOURCE, not a build output

Every other layer in VedaGraph is a deterministic function of a pinned artifact: delete
`data/canonical/**` and a rebuild reproduces it byte for byte. **A transcription is not.**
It is produced by a reader looking at an image, and two readers — or the same reader
twice — may differ. Treating it as a build output would make "deterministic rebuild" a
claim the pipeline cannot honour, and would silently overwrite verified readings on every
run.

So the transcription is captured **once**, into a tracked directory, and becomes the
pinned input that later builds are deterministic against:

```
data/transcriptions/atharvaveda_bsb_1856/leaf_NNNNN.jsonl    tracked, one file per leaf
```

`data/raw/**`, `data/derived/**` and `data/canonical/**` are gitignored; this directory
deliberately is not. This also satisfies the release requirement that human/model workflow
metadata be separable from deterministic canonical bytes: workflow fields live here, and
the canonical build reads only the text and the coordinate.

---

## 2. The firewall — RIGHTS-13, restated operationally

The redistribution basis for this text is that it derives **solely** from a public-domain
1856 print. Any reading that enters from elsewhere collapses that basis. The rule names an
LLM assistant as the **most likely** breach path for this project specifically, because
the agents operating it hold GRETIL and TITUS text in training and will complete an
unclear akṣara helpfully and silently.

**FORBIDDEN, without exception:**

- Consulting GRETIL, TITUS, VedaWeb, the Orlandi 1991 lineage, or any digital Atharvaveda.
- Filling an unclear akṣara from memory, from a recognised Rigveda parallel, from another
  edition, or by asking any model "what does this say?".
- Silently completing a passage that retains `[?]`.
- "Smoothing" a reading because it looks ungrammatical. If the page prints it, transcribe it.

Kāṇḍa 20 is largely Rigvedic. Recognising a mantra as an RV parallel is **itself a
non-independent source**. Recognition is not permitted to influence a single akṣara.

**PERMITTED:**

- Reading the page image, including re-reading it at higher zoom.
- A second independent reader looking at the same image.
- Another rights-compatible public-domain witness.

**REQUIRED when a character is genuinely unclear:** write `[?]` in place of the character,
set `transcription_status` to `TRANSCRIPTION_UNCERTAIN`, and move on. An unresolved `[?]`
ships as `PHILOLOGICAL_REVIEW_REQUIRED`. That is a correct outcome, not a failure.

### The residual risk this protocol does NOT eliminate

A model transcribing Devanagari from an image is not performing pure optical recognition;
its output is shaped by language priors learned from a corpus that includes the encumbered
digital Atharvaveda. RIGHTS-13 names exactly this channel. Reading the page rather than
answering from recall is the control, and two-stage independent verification against the
image is the check — but neither reduces the residual influence to a provable zero.

This limitation is recorded on the TextVersion and in the blocker registry rather than
being treated as discharged. It is the reason no transcribed unit is promoted past
`VERIFIED_WITH_ORTHOGRAPHIC_NOTE` on model evidence alone where the two stages disagreed.

---

## 3. The source page, as it is actually printed

Verified across sampled leaves n30 (printed p.16) and n300 (printed p.286):

- **Leaf ↔ printed page:** `printed_page = canvas_index - 14`. Front matter is n1–n14;
  the text starts at n15 = printed page 1.
- **Running head:** `॥ अथर्ववेदे K । S ॥` where `K` is the kāṇḍa and `S` the sūkta or
  sūkta range on that page, in Devanagari digits. The printed page number sits in the
  outer margin — left on verso, right on recto.
- **Sūkta opening:** a bracketed Devanagari numeral in the **outer** margin, e.g. `॥ ५ ॥` —
  right on recto, left on verso, as is the printed page number. An earlier version of this
  document said "left margin"; that is true of verso pages only and is wrong for half the
  volume. Page 1 carries no running head at all.
- **Mantra terminal:** `॥ N ॥` in Devanagari digits at the end of each mantra.
- **Prose / paryāya sūktas** (e.g. kāṇḍa 12.5, printed p.286) run continuously with
  paryāya markers `(१)`, `(२)`, mantra terminals `॥ १ ॥` inline, and a bracketed running
  count `(२४)` closing each paryāya. Transcribe the mantra units; record the paryāya
  number in `paryaya`.
- **Anuvāka colophon:** `॥ प्रथमोऽनुवाकः ॥` etc. Record in `structural_marker`, do not
  transcribe as a mantra.
- **Typeface:** an 1856 Berlin Devanagari fount. `अ` has an unfamiliar shape that can read
  as `ऋ`/`श्र` to an eye used to modern type.
- **Accent, and the honest state of it.** The page prints anudātta as a detached line below
  and svarita as a free-standing vertical above. **Acquire at width 4000, never 2000**: at
  2000 the marks sit on akṣara boundaries and cannot be assigned at all, and a first pass of
  this run was re-read at 4000 with **4 substantive changes in 86 units (~4.7%)**.
  But 4000 does NOT make accent solved. A reader working line by line at up to 7× zoom on
  the 4000px scan reports the marks are now stem-aligned yet still not reliably assignable
  to a specific akṣara, and omitted them rather than guess — which is what this protocol
  requires. **A dedicated accent pass is separate scoped work.** A partially-correct accent
  layer is worse than none, because it looks complete.

---

## 4. Record schema

One JSON object per line, one file per leaf, sorted by `(kanda, sukta, mantra)`.

| field | type | meaning |
|---|---|---|
| `schema_version` | str | `"1.0.0"` |
| `transcription_policy` | str | `"bsb-1856-devanagari-v1"` |
| `mdz_image_id` | str | e.g. `bsb10219750_00030` — resolves in the leaf manifest |
| `canvas_index` | int | IIIF canvas |
| `printed_page` | int | as printed in the margin; `null` if the page prints none |
| `kanda` / `sukta` / `mantra` | int | from the printed header and printed numerals |
| `paryaya` | int \| null | prose sūktas only |
| `text_devanagari` | str | exactly what the page prints, `[?]` for unclear |
| `unclear_count` | int | number of `[?]` marks |
| `structural_marker` | str \| null | colophon or heading printed with this unit |
| `transcription_status` | enum | see below |
| `transcriber` | str | worker id |
| `verifier` | str \| null | independent verifier id |
| `adjudicator` | str \| null | stage-3 id |
| `notes` | str \| null | observations; never a reading from elsewhere |

### `transcription_status`

| value | meaning |
|---|---|
| `VERIFIED_EXACT` | two independent readings agree codepoint for codepoint |
| `VERIFIED_WITH_ORTHOGRAPHIC_NOTE` | agree on the reading; differ only in accent/orthographic detail, noted |
| `SOURCE_AMBIGUOUS` | the page itself is ambiguous or defective |
| `TRANSCRIPTION_UNCERTAIN` | contains `[?]`, or the two stages disagreed on an akṣara |
| `PHILOLOGICAL_REVIEW_REQUIRED` | unresolved after stage 3 |

Only `VERIFIED_EXACT` and `VERIFIED_WITH_ORTHOGRAPHIC_NOTE` are release-eligible as
primary text. Everything else is released with its status attached and counted separately.

---

## 5. Stages

1. **Transcriber** reads the leaf image and writes the records.
2. **Verifier** independently reads the *same* leaf image — without seeing stage 1's text —
   and writes its own records. A harness compares them.
3. **Adjudicator** is invoked only where stages 1 and 2 disagree, re-reads the image at
   higher zoom, and sets the final status.

Disagreement is data. It is recorded, never averaged away.

---

## 6. Structure is derived from this source, not imported

Kāṇḍa / sūkta / mantra counts come from what these leaves print. Previously observed
digital counts (20 kāṇḍas, 731 sūktas, 5,839 mantras) are a **comparison target**, not a
target to hit. Nothing is renumbered, inserted or dropped to make a total match, and the
divergence is reported as a finding.

Existing Atharvaveda passage identity is FINAL and is not renumbered. Where this edition
presents structure differently, the edition's presentation is recorded as mapping data.
