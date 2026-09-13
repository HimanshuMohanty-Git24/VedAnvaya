# VedAnvaya: frontend revamp plan

**Status:** Phase 1 (research and audit) in progress.
**Scope:** the frontend only. The FastAPI service, the Neo4j projection, the ontology and the
Ask pipeline are frozen and are not to be modified.

---

## 1. Design read

Reading this as: **a research-institution product site for scholars, students and curious
readers, with a manuscript-modernist editorial language, leaning toward a hand-authored CSS
token layer expressed through Tailwind v4 `@theme`, Fraunces / Inter / Noto Devanagari, and
deliberately restrained motion.**

It is not a landing page and it is not a dashboard. It is closer to a museum's collection
site: a small number of marketing surfaces wrapped around a large research instrument.

### Dials

| Dial | Marketing surfaces | Research surfaces | Why |
|---|---|---|---|
| `DESIGN_VARIANCE` | 7 | 5 | Editorial asymmetry on the homepage and About. The reader and the graph are instruments people scan repeatedly, and a surprising layout costs them every visit. |
| `MOTION_INTENSITY` | 4 | 3, plus the graph | The brief asks for calm in static, alive on interaction. 4 buys entry transitions and hover physics, not scroll hijack. The graph is exempt: its motion is the interaction, not decoration. |
| `VISUAL_DENSITY` | 3 | 6 | An archive breathes. A critical apparatus does not. |

Two dial sets, applied by surface, is itself the design position: the marketing pages are
an invitation, the research pages are a tool, and pretending they want the same density is
how scholarly products end up feeling like brochures.

### Overrides taken against the taste skill, with justification

The taste skill fires three hard bans that collide with the supplied brand. Each has an
explicit override path in the skill itself, and each is taken deliberately.

1. **Fraunces.** Banned as an LLM-default display serif. Override path: *"the brand brief
   literally names a serif font."* The brand board is a real artifact and it names Fraunces
   in its typography panel. The aesthetic family is also genuinely manuscript and heritage,
   which is the skill's other stated condition. **Taken.**
2. **The ivory and rubric palette.** `#F4F0E7` sits squarely in the skill's banned
   warm-paper family and `#B64A2E` in its banned clay and oxblood family. Override path:
   *"the brand brief explicitly names those colors."* It does, to the hex. The deeper point
   is that the ban targets premium-consumer briefs where warm paper is a mood borrowed to
   signal craft. Here the paper is denotative: the corpus is a manuscript tradition, ivory
   is the material, and rubric red is the actual colour of actual rubrication. **Taken.**
3. **Inter.** Discouraged as a default UI sans. Named by the brand board. **Taken.**

Everything else in the skill is honoured, in particular: zero em-dashes and en-dashes in
user-facing copy, eyebrow rationing at one per three sections, the card and shadow
discipline, the layout-repetition ban, the theme lock, and the full interactive-state
matrix.

The skill also declares dense product UI out of its scope. Its landing-page composition
rules therefore govern the homepage, About, Sources, the footer and the navigation; its
accessibility, motion, dark-mode and anti-tell rules govern every surface without exception.

---

## 2. What the audit established

### 2.1 The product underneath is strong and must not be damaged

The API is unusually rich and unusually honest. It does not merely return counts; it returns
typed absence. `NOT_BUILT`, `NO_LEXICAL_MATCH`, `NOT_ESTABLISHED_FOR_PAIR`,
`CLASS_NOT_CROSS_VEDA` and `INSUFFICIENT_EVIDENCE` are distinct states with distinct
meanings, and every aggregate carries scope statements and caveats naming what it cannot
settle. That is the product's actual competitive advantage and the design has to carry it
rather than flatten it into a pretty number.

Design consequence, stated once and applied everywhere: **a figure never appears without its
status.** Absence is drawn, not omitted.

### 2.2 The constraints that shape the design

| Constraint | Measured | Design consequence |
|---|---|---|
| No whole-graph endpoint | `/graph/neighborhood/{id}` is bounded per node, depth capped at 2, `limit_per_type` capped at 50 | The World View cannot stream the graph at runtime. It is precomputed at build time into a static JSON. Zero backend change. |
| Graph scale | ~100,780 nodes, ~242,147 relationships; Agni holds 5,459 edges | A world view of passages is meaningless. The world view is the **entity** graph: 1,350 entities outside formulas and metres, plus deities. Roughly 1,500 to 2,800 nodes, which is renderable and readable. |
| Script split | RV and AV are IAST only. SV and YV are Devanagari only. `text.devanagari: "NOT_BUILT"` | "Sanskrit first" cannot mean "Devanagari first". Devanagari carries the brand and section framing. A derived transliteration is under evaluation and, if shipped, is labelled derived. |
| Samaveda | ārcika only, zero translations, zero audio | The SV is the product's most honest hole and the design should show it rather than hide it. It is the strongest single argument for typed absence. |
| Audio | 16,834 recordings, RV 10,402 / AV 4,680 / YV 1,752 / **SV 0** | A recitation coverage visualization writes itself, and its most interesting cell is empty. |
| Review status | Nothing is `HUMAN_REVIEWED`; 613 edges are `MODEL_ADJUDICATED` | The evidence UI must never imply human verification. |
| Ask latency | Proxy ceiling deliberately set to 345s against a 330s worst-case backend bound | The Ask progress UI has to stay legible for minutes, not seconds. |

### 2.3 The frontend as it stands

Next.js 16.3.4 App Router, React 19.2.8, TypeScript, Tailwind v4 present but barely used,
`motion` v13, `next-themes`, Radix dialog and tabs, Phosphor icons, Cytoscape for the 2D
graph, Playwright and Vitest. 18,432 lines of TypeScript across `src`, of which 9,377 are
the generated OpenAPI schema.

`src/app/globals.css` is 6,407 lines of hand-written semantic CSS over a home-rolled token
layer. The current palette is a cool grey-green (`#f4f5f2` on `#172025`), not the brand's
warm ivory on carbon. Fonts are Geist, Newsreader and Noto Sans Devanagari, none of which
are the brand's.

What is genuinely good and will be preserved: the route structure, the data-fetching layer,
the epistemic vocabulary in the components (`Caveat`, `DerivedMetric`, `Measure`, `Status`),
and the test suite's intent.

What is being replaced: the entire token layer, the typography, the header and navigation,
the homepage, the reader composition, the graph, and every surface's visual grammar.

---

## 3. Architecture decisions

### D1. CSS: keep semantic classes, replace the token layer, express tokens through Tailwind v4 `@theme`

Rejected: a full utility-first rewrite. It would invalidate every Playwright selector at
once, and semantic classes are genuinely correct here because the design objects are real
domain objects. A `.mantra` is a thing this product has, not a coincidence of utilities.

Adopted: one token file as the single source of truth, surfaced both as CSS custom
properties and as Tailwind theme values, so a utility and a semantic rule cannot disagree
about what rubric red is. Surfaces are then rewritten one at a time behind a stable app
shell, and the app stays runnable at every commit.

### D2. World graph: precomputed at build time, served as a static asset

A script walks the public API, expands the entity population, records the edges, runs the
layout offline, and writes a versioned JSON plus a manifest into `public/`. This keeps the
backend untouched, makes the world view load instantly rather than after 1,500 round trips,
and makes the rendered graph reproducible and reviewable.

### D3. 3D: pending Agent 3's verdict

Prior, to be confirmed or overturned by evidence: React Three Fiber v9 with a
hand-written instanced-node renderer and a worker-driven force simulation, rather than
`react-force-graph-3d`, whose React wrapper and three-forcegraph dependency need checking
against React 19. The decision will be recorded here with the evidence that settled it.

### D4. Brand marks are authored as SVG React components, not shipped as PNG

The supplied logo, thread, cadence and corner ornament are geometric line art. As PNG they
cannot take the ink colour in dark mode, they cost between 56 KB and 168 KB each, and they
blur under scaling. As components they take `currentColor`, cost under 2 KB, stay crisp, and
can be animated.

This is a deliberate exception to the taste skill's discouragement of hand-rolled decorative
SVG. The skill's concern is agents inventing decoration. Nothing here is invented: each mark
is traced from the supplied artwork and fitted, and the fit error is recorded. The emblem's
two edge curves are fitted to a maximum deviation of 0.35 and 0.78 units on a 240-unit
width, which is 0.14% and 0.33%.

### D5. Textures are rebalanced onto the brand paper before encoding

Measured, the supplied textures' paper ranges from `#EBDEC8` to `#F1E4CE` against a declared
ivory of `#F4F0E7`. Laid on the page untouched, every texture shows a seam at its edge.
`scripts/build_brand_assets.py` white-balances each plate onto the brand tone and encodes
AVIF and WebP at three widths: 15.4 MB of PNG becomes 1,287 KB across every width and
format, with the largest single file at 82 KB.

---

## 4. Phases

Each phase ends with a clean working tree and a commit. The application runs at every step.

| Phase | Contents | Gate |
|---|---|---|
| 1 | Research, audit, asset pipeline, this plan | Six research reports written; assets encoded |
| 2 | Token layer, typography, app shell, navigation, footer, brand marks | App runs on the new shell; contrast passes; existing tests pass or are deliberately updated |
| 3 | Homepage | Screenshot review in light and dark at four widths |
| 4 | Reader, Vedas, Explore, Deities, Entities | Reader is the priority surface |
| 5 | Ask | Progress model legible for a multi-minute wait |
| 6 | Graph architecture, world-graph precompute | Graph data builds and is bounded |
| 7 | World View and focused graph | Frame budget met; WebGL fallback works |
| 8 | Visualization Lab | Every visualization answers a stated question and draws absence |
| 9 | About, Sources | Copy reviewed against the rights matrix |
| 10 | Mobile, accessibility, performance | Axe clean; Lighthouse budgets met |
| 11 | Polish against the taste skill | Pre-flight matrix run per surface |
| 12 | Full regression | Playwright and Vitest green; visual sweep |

---

## 5. Open questions carried into implementation

1. Does `@indic-transliteration/sanscript` preserve the Vedic accent marks? If it drops
   them, a derived Devanagari rendering either ships with an explicit disclosure or does not
   ship. Agent 7 is testing this empirically. **Blocking for the reader design.**
2. Does any WebGL text library shape Devanagari conjuncts correctly? If not, graph labels
   are HTML overlays, which constrains the label budget. Agent 3 is checking. **Blocking for
   the world view design.**
3. Can the audio player's contour be driven by the verse's own recorded pitch accents rather
   than being decorative? The IAST text carries anudātta and svarita as combining marks, so
   this looks feasible and would make the ornament semantic rather than applied. **Not
   blocking. Evaluate in Phase 4.**
