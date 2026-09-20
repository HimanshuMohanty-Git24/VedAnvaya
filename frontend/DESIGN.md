# VedAnvaya — the design system

**Status:** locked. This file is the contract the frontend is written against, and the
place to change a rule before changing a surface.

---

## 1. The position

### Manuscript Modernism

A contemporary South Asian scholarly reading room. The product is a living critical edition
of four Saṃhitās and it should look like one: paper, ink, rubric, rules, generous margins,
and a great deal of nothing. What carries structure here is what carries it on a folio —
ruling, space, and a change of size — and not what carries it on a dashboard.

It is deliberately none of these: generic SaaS, an AI startup, a meditation product, a
temple site, a "themed" Indian site, a museum template, or an Awwwards motion piece.

### The Apparatus Is Alive

The second half of the position, and the one that decides what may move. A critical
apparatus is usually the dead part of an edition — set small, at the foot, consulted rarely.
Here it is the product. Every figure carries its status, every relation carries its kind,
every absence carries its type, and the reader can reach all of it. Making that *alive*
means the apparatus responds: a citation binds to the evidence it cites, a verse's margin
annotates the block beside it, a route draws itself as a chain, a bar arrives at its
measured value.

Alive is not busy. See the motion law.

---

## 2. Indic grounding

This section is careful on purpose. Some of what follows is a reference to a documented
South Asian manuscript practice; the rest is this product's own interpretation. They are
separated, because conflating them would be the same error the product refuses everywhere
else — presenting an interpretation as an attested fact.

### Historical manuscript reference

These are practices attested in South Asian manuscript traditions. They are the source of
the design's structural vocabulary.

| Practice | What it is | Where it is documented in this codebase |
|---|---|---|
| **Rubrication** | Red ink marking headings, section divisions, daṇḍas and invocations in Sanskrit codices. Red is *functional* in a Sanskrit manuscript rather than decorative. | `tokens.css`, the rubric ramp; and the licence — and the limit — on how the accent is used |
| **The pothī leaf** | A wide horizontal writing field with generous space on every side, bound by a cord through the leaf. | `reader.css`, the folio block |
| **Marginal annotation** | A commentator's or a scribe's hand in the outer margin, annotating the block it sits against. | `components/reader/folio.tsx` |
| **Ruled framing** | A leaf is ruled before it is written; the frame is on the page, not around the words. | `.va-verse`, which has a rule and a corner mark and no border |
| **The colophon** | Closing metadata: what this is, who made it, where it sits. | the shelfmark at the foot of the reader |
| **Foliation** | A leaf's address within the collection. | the reader's breadcrumb, in each corpus's own vocabulary |
| **Svara notation** | The Sāmavedic sung numerals written above the syllables; the Vedic accent marks of the Ṛgvedic and Yajurvedic traditions. | `lib/accent-trace.ts`, which reads them and refuses to interpret them |

### VedAnvaya's own interpretation

These are this product's decisions. None of them is a claim about what a Vedic manuscript
looked like, and none should be cited as one.

- **The colour names are material metaphors, not pigment history.** `#F4F0E7` is called
  manuscript ivory because it is the tone of aged writing support in the family of
  bhūrja-patra and palm leaf; it is not a measurement of any leaf. `#B64A2E` is called
  rubric red because red ink has the job described above; it is not a reconstruction of
  cinnabar or of any specific mineral. `#B49A62` is called aged gold and stands for the
  gold-and-orpiment family of manuscript ornament. `#26364A` is indigo. Verdigris is used
  where the product needed a fifth epistemic tone and is a derived value, not an anchor.
  **No claim is made that any of these pigments is universally "Vedic",** and the Vedic
  Saṃhitās were transmitted orally for centuries before they were written at all.
- **The registration mark in the reader's margin** is the cord-hole geometry borrowed as
  registration. A pothī's cord passes through the *leaf*; drawing a hole through the verse
  would make the text bend around a fiction. It is drawn on the rule line in the margin, and
  it is drawn once per page.
- **The Anvaya Thread** is a brand mark, not a manuscript device. `anvaya` is the
  grammarian's term for the prose reordering that makes a verse's syntax explicit, which is
  the right name for this product's one idea; the flare-and-diamond drawing is contemporary.
- **Devanagari as section framing** on the homepage and in the scope register is
  typographic identity, not quotation. It never stands in for a text the reader could read.

### What is refused

Om as decoration. Lotus and mandala motifs. The saffron-gradient aesthetic. Tricolour
gimmicks. Sanskrit set as texture. Stock "Indian spirituality" imagery of any kind. These
are not absent by oversight; a product about four specific recensions has no business
reaching for the generic iconography of a civilisation.

---

## 3. Colour

Five brand anchors, two derived epistemic tones, one dark paper. The full ramp and every
measured contrast ratio are in `src/styles/tokens.css` and `src/styles/theme.css`; this is
the list of **roles**.

| Role | Light | What it is for |
|---|---|---|
| `--va-surface-page` | `#F4F0E7` | The paper. Everything sits on it. |
| `--va-text-primary` | `#171815` | Lamp-black ink. 15.68:1. |
| `--va-accent-base` | `#B64A2E` | Rubric. Division marks, the one accent, the drawn thread. |
| `--va-gold-500` | `#B49A62` | Editorial rules and the partial/caution family. |
| `--va-indigo-700` | `#26364A` | Structural and inverse surfaces. |

**The epistemic tones are not decoration.** They carry the distinction the whole product
exists to draw, and they are named for the claim rather than for an API enum:

- `--va-tone-evidenced` — a source states it.
- `--va-tone-partial` — the layer reaches this only in part.
- `--va-tone-insufficient` — the evidence cannot settle it.
- `--va-tone-unbuilt` — the layer does not exist here.

Three rules govern them:

1. **No colour is the only channel.** Every epistemic state is also a word, and usually a
   shape. `Reach` draws four different marks for four claims; the connection matrix prints
   `NEVER MEASURED` and `NOT A PAIR RELATION` in full; a struck mark and a dotted mark differ
   in greyscale.
2. **The accent and the error tone must not be confused.** They share a hue, so the error
   tone is two steps darker *and* required to carry a dashed edge. Depth plus shape, not a
   sixth hue fighting the palette.
3. **Every ratio is measured against the surface the token is painted on**, and against
   every surface it can be painted on. `pnpm audit:contrast` fails on a drifted pair; 352
   checks pass today.

---

## 4. Typography

| Face | Sets | Why |
|---|---|---|
| Fraunces | English display | Named by the brand board. **Never Sanskrit:** it has no GPOS `mark` table, so a macron lands at the glyph origin. |
| Inter | UI | Named by the brand board. |
| Charis SIL, self-hosted | IAST | The only face measured to carry U+0331, U+030D, U+0301, U+0325 and U+0310 correctly. The CDN serves none of them for any Latin face, which is why this one is self-hosted. |
| Noto Serif Devanagari | Devanagari | Covers every Vedic mark this corpus uses. |

**Font-weight 700 is not in the system.** Headings take their weight from size, family and
colour. Three weights exist: 400, 500, 600.

### Sanskrit rules, which are not negotiable

- `letter-spacing: 0`, always. Tracking cuts visible gaps in the śirorekhā.
- `font-variant-ligatures: normal`. Disabling ligatures destroys conjuncts.
- `line-height: 2.05` for verse. Anudātta sits below the baseline and svarita above the
  headline and both can land on one akṣara.
- No justification and no hyphenation. Neither has a correct Devanagari implementation, and
  a hyphen inside a conjunct is an error rather than a break.
- Devanagari takes a narrower measure than Latin: `--va-measure-deva: 42ch` against `66ch`.
- A Devanagari label beside Latin is set at `1.18em`, because its body height is a smaller
  share of its em.

These are set once, in `src/styles/base.css`, so no surface has to remember them.

---

## 5. Spacing and the hairline dialect

**Depth is a hairline and space. It is almost never a shadow.** Three of the four elevation
steps are `none`; the two that are not are the modal overlay and one floating control.

Space is a twelve-step 4px scale. Measure is a token, not a guess: `46ch` tight, `66ch`
default, `84ch` wide, `42ch` Devanagari.

### When a container is allowed

A bordered, filled container is reserved for something that genuinely **is** a container:

- the evidence drawer
- the recitation player
- a scope or information panel (`Caveat`, `InterpretationFrame`)
- an interactive control group

Everything else is a **register**: ruled rows, ranged metadata, no enclosure. The rule that
decides it is whether the box is holding an object or merely drawing a boundary around some
text. See `src/styles/register.css`.

### The register

One dialect for every list of things this product holds.

- A row is a ruled line. Hairlines separate; nothing encloses.
- Metadata is **ranged**, in tabular figures, at the right margin — never badged.
- The strongest object in the row is its name, in the reading face at reading size.
- A figure never appears without its unit.
- A figure that does not exist prints **which kind of absence it is**, never a blank and
  never a dash.
- A count may drive a hairline share rule against a stated ceiling. It may not drive the
  size of the row.

---

## 6. Motion

### The law

> **NO MOTION MAY ASSERT WHAT THE DATA DOES NOT.**

### Three verbs, and nothing else moves

| Verb | What it means | Shipped in |
|---|---|---|
| **RESOLVE** | Something arrives at its measured value. Zero to the figure the service returned, once, no overshoot. | register share rules, Lab bars, the formula census |
| **DRAW** | A line extends where a real structural or evidentiary relation exists. | section rules, the brand thread, the Ask evidence binding, the register's hover mark |
| **ADVANCE** | A marker moves along an existing track, driven by real progress. | the accent trace playhead, the homepage archive register |

**Absence remains still.** A `NONE FOUND` row, a `NEVER MEASURED` cell and a
`NOT A PAIR RELATION` cell do not animate, because motion would lend them a liveliness the
claim does not have.

### Consequences

- No overshoot and no bounce anywhere. A spring would draw a value 8% above the measured one
  for 120ms, and that is a false figure on screen.
- Nothing loops and nothing runs on a timer. The three indefinite animations in the product
  are pending-state indicators bound to an open request, and they are named in
  `scripts/audit-motion.mjs`. Anything else fails the build.
- Scroll-driven motion uses a view progress timeline behind `@supports (animation-timeline:
  view())`, so it runs off the main thread and stops when the reader stops. The fallback is
  the finished state.
- **A scroll-driven subject inside a scroller takes a *named* timeline.** `view()` is
  anonymous and resolves against the element's nearest ancestor scroll container, not
  against the page — and a box is a scroll container on both axes the moment either one is
  `auto`, `scroll` or `hidden`. The archive register shipped with its track inside a
  horizontally scrollable frame, so its timeline was the frame's block axis, which cannot
  move: the animation was attached, running, and pinned at 49.97% at every scroll position
  on the page. It read as static, and no gate saw it, because nothing about it was missing.
  Where the subject is not a direct child of the document scroller, declare
  `view-timeline-name` on an ancestor that is, and reference it. `tests/e2e/manual-qa.spec.ts`
  asserts the register's timeline by name and measures the distance it travels.
- **Restraint is a distance, not an easing.** A scroll-driven translate is bounded by the
  scroll its range covers. The register may cross at most one lateral pixel per pixel the
  reader scrolls; uncapped it would have dragged 4,197px of citations through one screen,
  which is a marquee with the timer taken out.
- **Dropping a lateral offset on `:focus-within` breaks the pointer.** A press focuses the
  link, so the offset fell away between mousedown and mouseup and the target left the
  cursor; the click never completed. `:focus-visible` gives the keyboard reader the still
  row they need without moving what a pointer is aiming at.
- No animation library. Every primitive is CSS; the two that need a real progress value take
  it through one custom property.

Everything above is in `src/styles/thread.css`, which also honours
`prefers-reduced-motion: reduce` once, for all of it, by landing each primitive on its **end
state** — never on a shorter version of itself and never on zero.

---

## 7. The reader

The signature surface, and the one the rest of the system is calibrated against.

- **The verse is the protagonist.** No border, no fill, no radius. A rule above with a
  rubric mark at its head, and a rule below.
- **The folio margin** carries the apparatus of the block beside it: witness, printing
  source, graph reach, translation provenance, matching method. Three columns at ≥84rem —
  text, margin, apparatus rail — folding to a ruled strip beneath the block below that.
- **A margin note is anchored at the level the evidence exists at, and no finer.** This
  corpus records witnesses, translations and formula reach per *verse*. There is no
  line-level alignment in the store, so there is none in the interface: a note is a grid
  sibling of one block and cannot be positioned against a line even by accident.
- **The collation** sets a second witness beside the primary on request. Both texts verbatim.
  **No diff is computed and nothing is normalised** — the accents are combining marks, a diff
  over code points reports every accented syllable as a difference, and a diff over
  normalised text would have to decide that accentuation is noise.
- **The shelfmark** is the canonical key, set in mono at the foot, labelled as an archival
  identifier. It never replaces the human citation.
- **The accent trace** draws the accent marks the edition prints — above the line, below the
  line — and nothing else. It is not pitch, not melody, not timing, not phonetics, and it
  fails closed rather than guess.

---

## 8. Dark mode

Warm, not blue. `#131410` is carbon ink pulled down, so the product at night is the same
manuscript rather than a different product.

Every token has a dark value and every ratio is measured in both themes. Three rules:

1. **A photograph of paper is dropped, not inverted.** The archive-plate texture behind an
   entity header is a picture of a light surface; in dark mode it is removed.
2. **A texture that survives is a different encoding**, not the light one at low opacity.
3. **The epistemic tones lighten rather than desaturate**, so the four states stay as far
   apart at night as they are by day.

Every feature added in this phase was built and checked in both themes.

---

## 9. Responsive

Three shapes, not a fluid squeeze.

- **≥84rem** — the folio's three columns; the graph's rail beside the stage.
- **62–84rem** — text plus apparatus rail; the folio margin folds to a ruled strip beneath
  its block. It is not moved into the rail: the rail holds what the tradition ascribes to the
  verse, and a note about which edition printed the text is not that.
- **<62rem** — one column, stacked, the apparatus after the reading column in the DOM as
  well as on the screen.

Reference width for the narrow shape is **390px**, not a preset's 412. Touch targets are
44px under `pointer: coarse`. A wide table lives in a labelled horizontal scroller rather
than forcing the page to overflow.

---

## 10. Accessibility

Non-negotiable, and several of these are enforced rather than intended.

- `prefers-reduced-motion: reduce` lands every primitive on its end state.
- Every binding works from the keyboard. The Ask evidence binding is on `focus` as well as
  `hover`, and the citation markers are already in the tab order.
- Focus is always visible: 2px, offset 3px, in the rubric.
- No meaning is carried by motion alone.
- No meaning is carried by colour alone.
- Every unit travels with its figure in the accessible name, even where the column head
  carries it visually.
- A decorative mark is `aria-hidden` and its claim is a visually hidden word.
- Autoplay motion is prohibited and the prohibition is a build gate.

---

## 11. Anti-patterns

Refused, with the reason. These are not stylistic preferences; each one would make the
product state something it cannot support.

| Refused | Why |
|---|---|
| Om as decoration, lotus/mandala defaults, saffron gradients, tricolour gimmicks, decorative Sanskrit, stock "Indian spirituality" | Generic iconography for a product about four specific recensions |
| Glassmorphism | Depth here is a hairline; a frosted panel is a shadow with extra cost |
| Floating particles | Decoration over real subjects. Refused explicitly on the graph canvas |
| Autoplay marquee | Motion with no referent, unreadable at its own speed, never stops. Gated by `audit-motion.mjs` |
| Parallax paper | Asserts depth the page does not have |
| Count-up statistics | Counts upward through numbers that were never measured. Every intermediate value is false |
| Similarity-score visualisation | The product measures eight typed relation kinds and refuses to merge them into one score. A drawing that merged them would undo that |
| Scroll-jacking | Takes the reading rate away from the reader |
| A bare dash for a missing figure | Untyped absence. Four different claims collapsed into one glyph |
| A raw numeric `z-index` | An unverifiable claim about what sits above what. Gated by `audit-z-index.mjs` |
| A class name defined in two stylesheets | The sheets are unlayered, so a name is a global. Gated by `audit-class-owner.mjs` |

---

## 12. The gates

The system is enforced, not documented and hoped for. `pnpm run audit` runs all of them.

| Gate | Refuses |
|---|---|
| `audit-tokens.mjs` | A token read behind a fallback that is never declared |
| `audit-contrast.mjs` | A pair below its threshold on any surface it can be painted on |
| `audit-graph-contrast.mjs` | A graph fill whose *composited* ratio fails |
| `audit-class-collisions.mjs` | Two sheets giving one class a different box |
| `audit-class-owner.mjs` | Two sheets defining one class at all |
| `audit-completeness-fallback.mjs` | A shipped figure drifting from the service |
| `audit-z-index.mjs` | A numeric `z-index` outside the token scale |
| `audit-motion.mjs` | An infinite animation, a `<marquee>`, or a timer that writes a transform |

A gate that has never rejected anything has not been shown to work. Each of the three added
in this phase was verified by reintroducing the defect it exists to catch.
