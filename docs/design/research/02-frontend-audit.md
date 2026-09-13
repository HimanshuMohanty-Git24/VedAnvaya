# 02 — Frontend Architecture / Design System Audit

**Subject:** `D:\VedaGraph\frontend` — the Next.js reading and exploration surface.
**Purpose:** establish ground truth before the VedaGraph → **VedAnvaya** rebrand and the design-system rebuild.
**Method:** read-only. Every file under `src/` and `tests/`, and every config file, was read in full. No source file was modified.
**Audited at:** clean tree, `5c268d1`.

**Stack as installed:** Next.js 16.3.4 (App Router) · React 19.2.8 · TypeScript 5 (strict) · Tailwind CSS **4.3.3** via `@tailwindcss/postcss` · `motion` 13 · `next-themes` 0.4.6 · `@radix-ui/react-dialog` 1.1.23 · `@radix-ui/react-tabs` 1.1.21 · `@phosphor-icons/react` 2.1.10 · `cytoscape` 3.34.3 · `clsx` 2.1.1 · Playwright 1.63 + Vitest 5 · pnpm 10.34.5.

---

## 0. Headline findings

1. **`src/app/globals.css` is 6,407 lines / 119,594 bytes** with 952 rule blocks and 388 distinct class tokens. It *is* the design system. No CSS modules, no component-scoped CSS, no `@apply`, no CSS-in-JS.
2. **Tailwind is installed, imported, and used for nothing.** `@import "tailwindcss"` (`globals.css:1`) and a three-line `@theme inline` block (`globals.css:67–71`) are the entire Tailwind surface. **Zero** Tailwind utility classes appear in any `.tsx` file. The import pays for Preflight, which `globals.css:74–146` then partly re-does by hand.
3. **The token layer is 31 custom properties**, of which 29 are colour/shadow. There is **no** spacing token, type token, motion token, or z-index token. Everything else is a literal.
4. **`motion` v13 is a declared dependency that is never imported.** No `from "motion"` anywhere in `src/`.
5. **The test suite is almost entirely copy-and-class coupled.** 61 distinct literal CSS class selectors and ~185 literal copy strings carry the e2e suite; there is **not one `data-testid` in the repository**. See §7.
6. **"VedaGraph" appears 44× in `frontend/`** — 12 user-facing copy, 2 SEO metadata, 5 test assertions, 6 `VEDAGRAPH_API_URL` env var, rest comments/generated prose. **No API path contains the brand.** See §8.
7. **Dark mode is hand-designed, not inverted** (`globals.css:39–65`, plus a dark-only graph-legend colour table at `2888–2911`). This is a genuine asset that should survive the rebuild.
8. **Two parallel, disagreeing colour tables exist for the graph**: `GROUP_STYLE` node fills in `src/components/graph-canvas.tsx:90–133`, and *different* legend-text hexes in `globals.css:2853–2911`. Both are hard-coded outside the token layer.

---

# PART ONE — THE AUDIT

## 1. `src/app/globals.css` — complete anatomy

### 1.1 File shape

| Measure | Value |
| --- | --- |
| Lines | 6,407 |
| Bytes | 119,594 |
| Rule blocks | 952 |
| Distinct class tokens | 388 |
| `font-size` declarations | 353 |
| `padding*` declarations | 183 |
| `border: 1px solid var(--line)` | 73 |
| `background: var(--surface)` | 65 |
| hover `border-color: var(--accent)` | 36 |
| `text-transform: uppercase` | 62 |
| `!important` | 16 |
| `@media` blocks | 9 |
| `@keyframes` | 3 |
| Custom properties defined | 31 |

Section order, from the file's own banners:

| Lines | Section |
| --- | --- |
| 1–71 | Import, `:root`, `.dark`, `@theme inline` |
| 74–224 | Reset, base elements, `.sr-only`, `.shell`, `.page`, Sanskrit/reading type, skip link |
| 222–322 | Buttons and chips |
| 324–470 | Header and footer |
| 472–700 | Home (hero, metric strip, section, veda grid, discovery, evidence pitch) |
| 702–740 | Page heading |
| 742–980 | Knowledge status, caveats, interpretation frame |
| 982–1044 | Empty states, skeleton |
| 1046–1180 | Measure charts, ranked facts |
| 1182–1256 | Tabs |
| 1258–1730 | Reader / passage |
| 1732–1820 | Structure browser |
| 1822–1960 | Work and collection pages |
| 1962–2230 | Search |
| 2232–2405 | Index lists, kind tabs, condition chips |
| 2407–2700 | Profiles (deity / entity / seer) |
| 2702–3148 | Graph |
| 3150–3350 | Evidence drawer |
| 3352–3700 | Cross-Veda and comparison |
| 3702–4130 | Atharvaveda, rituals, formulas |
| 4132–4528 | Insights, limits, lenses, gaps |
| 4530–4578 | Mobile navigation |
| 4580–4790 | Responsive, reduced motion, print |
| 4792–4980 | Overflow-containment patches, tab-strip fade, matrix scroll shadows |
| 4982–5100 | Derived measures, selected relationships |
| 5102–6196 | Ask VedaGraph |
| 6198–6407 | Recitation player, late one-off patches |

The last ~1,600 lines are visibly accretive: `.tree-level-label` / `.tree-more` (`4793–4820`) sit *after* the responsive block they belong before; `.header-inner`, `.matrix-wrap` and `.limit-measurements` are each re-declared at top level after their original definitions (§1.6); `.panel-note-faint` and `.panel h3 svg` (`6392–6407`) are appended past the recitation section they do not belong to.

### 1.2 Custom-property inventory (light vs dark)

**Surfaces**

| Token | Line | Light | Dark | Line |
| --- | --- | --- | --- | --- |
| `--bg` | 9 | `#f4f5f2` | `#10161a` | 40 |
| `--surface` | 10 | `#fbfcf9` | `#171f23` | 41 |
| `--surface-sunk` | 11 | `#edefea` | `#131a1e` | 42 |
| `--surface-strong` | 12 | `#e6e9e3` | `#1f292d` | 43 |

**Ink**

| Token | Line | Light | Dark | Line | Uses |
| --- | --- | --- | --- | --- | --- |
| `--ink` | 13 | `#172025` | `#e8eeec` | 44 | 29 |
| `--ink-soft` | 14 | `#3d484c` | `#c6d1ce` | 45 | 24 |
| `--muted` | 15 | `#5b686d` | `#9fadab` | 46 | 118 |
| `--faint` | 16 | `#5f6b70` | `#9ba9a6` | 47 | 106 |

> `--muted` `#5b686d` and `--faint` `#5f6b70` differ by 4/11/3 in RGB — **visually indistinguishable**. Two tokens are carrying one value across 224 declarations. The distinction is intended and not realised.

**Hairlines**

| Token | Line | Light | Dark | Line | Uses |
| --- | --- | --- | --- | --- | --- |
| `--line` | 17 | `#d5dbd5` | `#2c383c` | 48 | 107 |
| `--line-strong` | 18 | `#bec6bf` | `#3c494d` | 49 | 28 |

**Accent**

| Token | Line | Light | Dark | Line | Uses |
| --- | --- | --- | --- | --- | --- |
| `--accent` | 19 | `#b04728` | `#e58163` | 50 | 111 |
| `--accent-ink` | 20 | `#fff8f3` | `#1c0e09` | 51 | 2 |
| `--accent-soft` | 21 | `#f3ded5` | `#3b241d` | 52 | 9 |

**Semantic tones**

| Token | Line | Light | Dark | Line | Uses |
| --- | --- | --- | --- | --- | --- |
| `--tone-supported` | 22 | `#2f6b55` | `#86c4a8` | 53 | 8 |
| `--tone-supported-bg` | 23 | `#e4efe9` | `#1a2c26` | 54 | 4 |
| `--tone-partial` | 24 | `#8a5a16` | `#d9ab6b` | 55 | 31 |
| `--tone-partial-bg` | 25 | `#f5ebdb` | `#2e2618` | 56 | 10 |
| `--tone-insufficient` | 26 | `#99452b` | `#e29175` | 57 | 25 |
| `--tone-insufficient-bg` | 27 | `#f6e2db` | `#33201a` | 58 | 9 |
| `--tone-not-built` | 28 | `#4f5b62` | `#9aa8ae` | 59 | 7 |
| `--tone-not-built-bg` | 29 | `#e6eaec` | `#1e262a` | 60 | 4 |
| `--tone-unknown` | 30 | `#5b686d` | `#9fadab` | 61 | 2 |
| `--tone-unknown-bg` | 31 | `#e9ecea` | `#1c2427` | 62 | 2 |

> Two defects here. `--tone-unknown` is **byte-identical** to `--muted` in both themes (a redundant token). And `--tone-insufficient` `#99452b` sits in the same hue family as `--accent` `#b04728` — **the error state and the brand accent are the same colour**. That is the single largest semantic problem in the palette: on `.search-error`, `.graph-message` and `.ask-error` the "something went wrong" red is indistinguishable from the "this is a link" red.

**Shadow**

| Token | Line | Light | Dark | Line | Uses |
| --- | --- | --- | --- | --- | --- |
| `--shadow-sm` | 32 | `0 1px 2px rgb(35 47 43 / .05)` | `0 1px 2px rgb(0 0 0 / .3)` | 63 | 2 |
| `--shadow` | 33 | `0 18px 46px -24px rgb(35 47 43 / .35)` | `0 22px 52px -26px rgb(0 0 0 / .75)` | 64 | **1** |

`--shadow` is used exactly once (`3171`, the evidence drawer); `--shadow-sm` twice (`5237` ask composer, `5526` ask answer). **There is effectively no elevation system** — depth is expressed entirely through hairlines and surface tints, which is a deliberate and good choice that should be named as such.

**Radius / layout**

| Token | Line | Value | Uses |
| --- | --- | --- | --- |
| `--radius` | 34 | `14px` | 24 |
| `--radius-sm` | 35 | `9px` | 60 |
| `--measure` | 36 | `68ch` | 10 |

**Tailwind bridge** — `@theme inline` (`67–71`): `--color-background: var(--bg)`, `--color-foreground: var(--ink)`, `--font-sans: var(--font-ui)`. Generates `bg-background`, `text-foreground`, `font-sans`. **None of the three is used anywhere in `src/`.**

**Absent entirely:** no `--space-*`, `--text-*`, `--leading-*`, `--tracking-*`, `--duration-*`, `--ease-*`, `--z-*`. Every such value is a literal in a rule.

### 1.3 Variables consumed but defined outside `globals.css`

| Variable | Defined at | CSS uses |
| --- | --- | --- |
| `--font-ui` | `src/app/layout.tsx:9` — `Geist({ variable: "--font-ui" })` | 28 |
| `--font-reading` | `src/app/layout.tsx:10` — `Newsreader({ variable: "--font-reading" })` | 28 |
| `--font-devanagari` | `src/app/layout.tsx:12` — `Noto_Sans_Devanagari({ variable: "--font-devanagari" })` | 3 |
| `--depth` | inline style at `src/components/structure-browser.tsx:65, 97, 116` | 4 |

The three font variables are injected onto `<html>` by `next/font` (`layout.tsx:28`). **The stylesheet depends on three variables invisible to anyone reading it alone.** Every use is written defensively (`var(--font-reading), Georgia, serif`), which papers over it but also means a broken variable degrades silently rather than loudly.

> The shipped typefaces are **Geist / Newsreader / Noto Sans Devanagari** — *not* the Fraunces / Inter / Noto Serif Devanagari target in the brief. All three are `next/font/google`, `display: "swap"`.

### 1.4 Class-selector inventory by surface

388 distinct class tokens across 952 blocks. Grouped, with approximate line spans.

| Surface | ≈ lines | Principal selectors |
| --- | --- | --- |
| **Reset / base** | 74–200 (~127) | `*`, `html`, `body`, `h1–h4`, `p`, `a`, `button/input/select/textarea`, `ul/ol/dl/dd`, `li`, `table`, `::selection`, `:focus-visible`, `.sr-only` |
| **Layout / shell** | 164–182 (~19) | `.shell`, `.page`, `.muted`, `.mono` |
| **Reading type** | 184–219 (~36) | `.sanskrit`, `.devanagari`, `.skip-link`, `.skip-link:focus` |
| **Buttons / chips** | 222–322 (~101) | `.button`, `.button.primary`, `.button.secondary`, `.button:disabled`, `.icon-button`, `.text-link`, `.chip-row`, `.chip-row a/span`, `.chip-row.is-static span` |
| **Header / nav** | 324–443 (~120) | `.site-header`, `.header-inner`, `.brand`, `.brand-mark`, `.desktop-nav`, `.desktop-nav a[aria-current]`, `.header-actions`, `.search-action`, `.search-action kbd`, `.theme-toggle`, `.theme-icon-light/-dark`, `.mobile-nav-trigger` |
| **Footer** | 445–470 (~26) | `.site-footer`, `.site-footer .shell`, `.footer-brand`, `.site-footer nav` |
| **Hero / home** | 476–700 (~225) | `.hero`, `.hero-kicker`, `.hero-lede`, `.hero-actions`, `.hero-visual`, `.metric-strip`, `.metric`, `.section`, `.section-heading`, `.section-heading.small`, `.veda-grid`, `.veda-card`, `.veda-card-top`, `.veda-code`, `.veda-count`, `.scope-warning`, `.discovery-layout`, `.discovery-list`, `.discovery-link`, `.evidence-pitch` |
| **Page heading** | 702–740 (~39) | `.page-heading`, `.back-link` |
| **Status / caveats** | 742–980 (~239) | `.knowledge-status` (+ `.is-compact`, `.tone-*` ×4), `.caveat` (+ `.is-collapsible`), `.caveat-boundary`, `.caveat-list`, `.caveat-text`, `.interpretation-frame`, `.interpretation-tag`, `.counterclaim`, `.panel-note` |
| **Empty states** | 982–1044 (~63) | `.empty-state`, `.empty-state.is-inline`, `.empty-hint`, `.not-found-code`, `.skeleton`, `@keyframes shimmer` |
| **Measures / charts** | 1046–1180 (~135) | `.measure`, `.measure-scope`, `.measure-table`, `.measure-track`, `.measure-bar`, `.row-muted`, `.row-excluded`, `.measure-value`, `.measure-null`, `.measure-notes`, `.measure-caveat`, `.ranked-facts`, `.ranked-definition` |
| **Tabs** | 1182–1256 (~75) | `.tab-list`, `.tab-trigger`, `.tab-trigger[data-state=active]`, `.tab-badge`, `.tab-panel`; plus `.tabs` / `.tabs::after` at 4926–4948 |
| **Reader / passage** | 1258–1730 (~473) | `.reader-page`, `.reader-breadcrumbs`, `.crumb-level`, `.reader-layout`, `.reading-column`, `.citation-line`, `.veda-chip`, `.mantra-block`, `.text-meta`, `.copy-button`, `.witness-block`, `.translation-section`, `.reuse-callout`, `.reader-nav`, `.reader-edge`, `.reader-aside`, `.reader-footnotes`, `.reference-list`, `.certainty-chip` (+ `.band-*` ×3), `.entity-chip-list`, `.entity-chip`, `.parallel-list`, `.parallel-row`, `.parallel-kind`, `.provenance-list`, `.basis-list`, `.provenance`, `.graph-entry` |
| **Structure browser** | 1732–1820 (~89) | `.structure-browser`, `.structure-top`, `.tree-row`, `.tree-loading`; plus `.tree-level-label`, `.tree-more` at 4793–4820 |
| **Work / collection** | 1822–1960 (~139) | `.content-grid`, `.sticky-aside`, `.panel`, `.panel-links`, `.collection-metrics`, `.work-list`, `.work-row`, `.work-code`, `.work-facts` |
| **Search** | 1962–2230 (~269) | `.search-page`, `.search-experience`, `.search-field`, `.filter-bank`, `.filter-row`, `.filter-selects`, `.search-prompts`, `.search-results-wrap` (+ `.is-stale`), `.results-meta`, `.refreshing`, `.search-results`, `.result-row`, `.result-skeleton`, `.result-type`, `.result-veda`, `.search-error`, `.search-caveats` |
| **Index lists** | 2232–2405 (~174) | `.entity-index`, `.entity-index-row`, `.certainty-mini`, `.entity-group`, `.type-grid`, `.kind-tabs`, `.condition-kind` (+ `.kind-*` ×6) |
| **Profiles** | 2407–2700 (~294) | `.profile-page`, `.profile-hero`, `.profile-iast`, `.alias-line`, `.alias-label`, `.axis-list`, `.profile-actions`, `.profile-grid`, `.profile-main`, `.profile-sections`, `.certainty-split` (+ `.is-ambiguous`), `.formula-chip-list`, `.formula-chip`, `.passage-columns`, `.citation-list`, `.related-section`, `.related-grid`, `.entity-detail-meta`, `.seer-panel`, `.seer-facts`, `.seer-associations` |
| **Graph** | 2702–3148 (~447) | `.graph-page`, `.graph-explorer`, `.graph-toolbar`, `.graph-options`, `.graph-legend`, `.legend-chip` (+ 8 `[data-shape]`, 11 `.group-*`, 6 `.dark .group-*`), `.graph-workspace`, `.graph-stage`, `.graph-canvas`, `.graph-frame` (+ `.compact`, `.is-empty`), `.graph-caption`, `.graph-busy`, `.graph-spinner`, `@keyframes spin`, `.graph-bounds`, `.graph-message`, `.graph-detail`, `.node-type`, `.graph-detail-actions`, `.graph-detail-empty`, `.truncated-types`, `.graph-node-list` |
| **Evidence drawer** | 3150–3350 (~201) | `.dialog-overlay`, `.evidence-drawer`, `.evidence-content`, `.evidence-loading`, `.evidence-triple`, `.why-answer`, `.evidence-metadata`, `.evidence-spans`, `.evidence-passages`, `.evidence-technical` |
| **Comparison / cross-Veda** | 3352–3700 (~349) | `.matrix-section`, `.reuse-section`, `.span-census`, `.matrix-wrap`, `.connection-matrix`, `.material-table`, `.cell`, `.cell-reason`, `.cell-kind`, `.cell-total`, `.connections-explainer`, `.reuse-list`, `.reuse-row`, `.census-grid`, `.comparison-stack`, `.comparison`, `.comparison-banner`, `.comparison-grid`, `.comparison-column`, `.comparison-head`, `.comparison-translation`, `.matched-surface`, `.comparison-evidence`, `.transmission-note` |
| **AV / rituals / formulas** | 3702–4130 (~429) | `.av-block`, `.av-section-title`, `.av-rows`, `.av-row`, `.evidence-rows`, `.concern-strip`, `.ritual-grid`, `.ritual-shape`, `.ritual-steps-section`, `.ritual-children`, `.passage-rail`, `.occurrence-section`, `.family-tree`, `.evidence-summary`, `.ritual-map`, `.ritual-row`, `.ritual-steps`, `.citation-rail`, `.formula-list`, `.formula-stats`, `.family-branches`, `.occurrence-columns` |
| **Insights / limits** | 4132–4528 (~397) | `.insight-section`, `.insight-interpretive_claim`, `.data-row-grid`, `.metric-row-grid`, `.claim-list`, `.lens-grid`, `.lens-card`, `.lens-icon`, `.lens-cta`, `.limits-page`, `.limit-list`, `.limit-card`, `.verdict` (+ `.verdict-*` ×2), `.limit-body`, `.limit-measurements`, `.limit-alternative`, `.limits-footer`, `.declared-gaps`, `.gap-card`, `.gap-witness` |
| **Mobile nav** | 4530–4578 (~49) | `.mobile-nav-panel`, `.mobile-nav-top`, `.mobile-nav-links` |
| **Responsive / motion / print** | 4580–4790 (~211) | 4 media blocks + `prefers-reduced-motion` + `print` |
| **Overflow patches** | 4822–4980 (~159) | `min-width:0` group, `.limit-measurements` re-decl., `overflow-wrap:anywhere` group, `.header-inner` re-decl., `.translation-section h2`, `.tabs::after`, `.matrix-wrap` re-decl. |
| **Derived measures** | 4982–5100 (~119) | `.derived-grid`, `.derived-metric`, `.derived-headline`, `.derived-values`, `.derived-reading`, `.derived-scope`, `.selected-relationships` |
| **Ask** | 5102–6196 (~1,095) | `.ask-page`, `.ask-contract`, `.ask-experience`, `.ask-unavailable`, `.ask-error`, `.ask-hint`, `.ask-context`, `.ask-composer`, `.ask-textarea-wrap` (+ `.is-over`), `.ask-controls`, `.ask-selects`, `.ask-mode-note`, `.ask-submit-row`, `.ask-counter` (+ `.is-near`/`.is-over`), `.ask-submit-hint`, `.ask-clear`, `.ask-examples`, `.ask-chip-row`, `.ask-pending`, `.ask-phases`, `@keyframes ask-pulse`, `.ask-pending-note`, `.ask-answer`, `.ask-answer-head`, `.ask-badges`, `.ask-support` (+ `.tone-*` ×4), `.ask-status-note`, `.ask-interpretive`, `.ask-prose`, `.ask-cite-group`, `.ask-cite`, `.ask-answer-actions`, `.ask-provenance`, `.ask-caveats`, `.ask-entity-list`, `.ask-entity`, `.ask-unresolved`, `.ask-related`, `.ask-retrieval`, `.ask-retrieval-body`, `.ask-retrieval-block`, `.ask-tag-row`, `.ask-empty-note`, `.ask-figures`, `.ask-evidence-group`, `.ask-evidence-item`, `.ask-evidence-head`, `.ask-evidence-id`, `.ask-evidence-fact/-relation/-meta`, `.ask-evidence-claim`, `.ask-qualifier`, `.ask-evidence-footer`, `.ask-about-quiet` |
| **Recitation** | 6198–6390 (~193) | `.recitation` (+ `.is-external`), `.recitation-media`, `-scope`, `-transport`, `-play`, `-seek`, `-time`, `-speed`, `-loading`, `-failed`, `-source-link`, `-provenance`, `-note` |
| **Trailing patches** | 6392–6407 (~16) | `.panel-note-faint`, `.panel h3 svg` |

**Distribution note.** Ask alone is **17 %** of the stylesheet (1,095 lines) for one route. The reader (473) + graph (447) + comparison (349) together are another 20 %. Roughly **60 % of the file is single-route CSS** that would collapse under a real primitive set.

### 1.5 Hard-coded values that bypass the tokens

**Hex colours outside `:root` / `.dark`** — 12, all in the graph legend:

| Line | Declaration | Note |
| --- | --- | --- |
| 2855 | `.legend-chip.group-passage { color: #847053 }` | light |
| 2859 | `.legend-chip.group-person { color: #5a768a }` | light |
| 2863 | `.legend-chip.group-idea { color: #5c7a70 }` | light |
| 2867 | `.legend-chip.group-rite { color: #846a94 }` | light |
| 2871 | `.legend-chip.group-thing { color: #787464 }` | light |
| 2875 | `.legend-chip.group-wording { color: #4b7886 }` | light |
| 2890 | `.dark .legend-chip.group-passage { color: #c7ab7e }` | dark |
| 2894 | `.dark .legend-chip.group-person { color: #86a6bb }` | dark |
| 2898 | `.dark .legend-chip.group-idea { color: #8fb3a6 }` | dark |
| 2902 | `.dark .legend-chip.group-rite { color: #ab8ec0 }` | dark |
| 2906 | `.dark .legend-chip.group-thing { color: #a5a08c }` | dark |
| 2910 | `.dark .legend-chip.group-wording { color: #77a9b8 }` | dark |

The comment at `2849–2851` explains why: these are the node hues *darkened for 4.5:1 on `--surface`*. The node hues themselves live in TypeScript:

| File:line | Values |
| --- | --- |
| `src/components/graph-canvas.tsx:95` | `deity` `#bd4f32` / `#e07858` |
| `:96–102` | `unresolved-deity` `#b59a8f` / `#9b807a` |
| `:103–109` | `passage` `#9b8462` / `#c7ab7e` |
| `:110` | `person` `#607d92` / `#86a6bb` |
| `:111` | `idea` `#6c8f83` / `#8fb3a6` |
| `:112` | `rite` `#8a6f9b` / `#ab8ec0` |
| `:113` | `thing` `#7d7969` / `#a5a08c` |
| `:114` | `wording` `#4f7f8f` / `#77a9b8` |
| `:118–124` | `derived` `#8d8d8d` / `#a8a8a8` |
| `:125–131` | `record` `#8c9490` / `#9faaa5` |
| `:132` | `other` `#8c9490` / `#9faaa5` |

Plus four more in `buildStyle`, `graph-canvas.tsx:136–139`: `ink` `#d5dedb`/`#465155`, `halo` `#182023`/`#f4f5f2`, `line` `#4a5659`/`#b9c2bd`, `accent` `#e07858`/`#bd4f32`. `halo` light `#f4f5f2` is a copy of `--bg`; `accent` is a *near* copy of `--accent` `#b04728` but not equal. **Eleven graph colours are defined twice in two languages, and the two definitions disagree by design with no link between them.**

**`rgb()` literals outside the token block:**

| Line | Declaration |
| --- | --- |
| 3157 | `.dialog-overlay { background: rgb(12 18 20 / 0.42) }` — **not theme-aware**; the same scrim in light and dark |
| 4956–4957 | `.matrix-wrap` scroll-shadow gradients `rgb(0 0 0 / 0.09)` ×2 — invisible in dark mode |

**Non-token pixel literals worth naming:**

| Line | Value | Context |
| --- | --- | --- |
| 79 | `font-size: 15px` | the **only** px font size; the root of the whole rem scale, and it is not a token |
| 166 | `width: min(100% - 48px, 1320px)` | container width + gutter, untokenised |
| 330 | `height: 66px` | header height |
| 1484, 1841 | `top: 92px` | sticky offset — a hand-computed `66px + 26px`, duplicated |
| 2929 | `height: min(70vh, 640px)` | graph canvas |
| 3167 | `width: min(100%, 560px)` | evidence drawer |
| 4534 | `width: min(100%, 360px)` | mobile nav panel |
| 2914 | `350px` / 4582 `300px` | graph detail rail |
| 1922 | `grid-template-columns: 62px …` | work row |
| 2146 | `118px` | search result row |
| 4044 | `130px` | formula list |
| 951, 1683, 3226, 3324, 3952 | `160px`, `130px`, `150px`, `140px`, `170px` | five different definition-list label columns, all one-offs |
| 4935–4936 | `width: 34px; height: 41px` | tab-strip fade; `41px` is a magic number tied to the tab height |

**Radius literals bypassing `--radius*`:** `5px` (×4: `409`, `2019`, `5652`, `5999`), `4px` (×2: `154`, `5348`), `9px` (`349` — a literal copy of `--radius-sm`), `12px` (`4288`), `11px` (`669`), `3px` (`2887`), `2px` (`2880`), `1px` (`2885`), `3px / 50%` (`2896`), `50%` (×4).

### 1.6 Duplicated and fragmented rules

**True top-level duplicates** (not media-query overrides):

| Selector | First | Second | Effect |
| --- | --- | --- | --- |
| `.header-inner` | 337 | **4906** | second adds `min-width: 0` only |
| `.matrix-wrap` | 3372 | **4951** | second adds scroll-shadow backgrounds; a reader of 3372 does not know |
| `.limit-measurements` | 4431 | **4837** | second sets `display: block; overflow-x: auto` — **it re-types a `<table>` as a block**, silently defeating the `th/td` rules 6 lines above |
| `.reader-aside` | 1482 | 4790 | second is inside the `min-width: 0` group |
| `.panel-note` | 974 | 4902 | second is inside the `overflow-wrap: anywhere` group |
| `.ask-evidence-meta` | 6023 (group) | 6034 | adjacent override of its own group's `font-size` |

**Media-query overrides** (legitimate but numerous — 60+ selectors re-declared): `.shell`, `.page`, `.section`, `.hero`, `.veda-grid`, `.metric-strip`, `.discovery-layout`, `.reader-layout`, `.content-grid`, `.profile-grid`, `.graph-workspace` (×3 breakpoints), `.work-row`, `.entity-index-row`, `.result-row`, `.reuse-row`, `.ritual-row`, `.comparison-grid`, `.filter-selects`, `.certainty-mini`, `.profile-hero`, `.profile-actions`, `.graph-canvas`, `.graph-bounds`, `.graph-detail`, `.graph-toolbar form`, `.evidence-drawer`, `.mobile-nav-panel`, `.site-footer .shell`, `.measure-table th[scope=row]`, `.desktop-nav`, `.mobile-nav-trigger`, `.brand`, `.sticky-aside`, `.reading-column`, `.reader-nav`, `.citation-list a`, `.formula-list a`, `.evidence-triple i`, `.limit-measurements td`, `.interpretation-frame dl div`, `.search-field input`, `.result-type`, `.result-skeleton`, `.lens-card:hover`, `.tabs::after`, `.recitation-transport`, `.recitation-seek`, `.recitation-provenance dl/dt`, and the whole `.ask-*` block re-declared at 6125–6196.

**The dominant copy-paste idiom** — an uppercase micro-heading, repeated **21 times** verbatim:

```css
font-family: var(--font-ui), sans-serif;
font-size: 0.7–0.8rem;          /* 7 distinct values used */
font-weight: 600;
letter-spacing: 0.08–0.1em;     /* 4 distinct values used */
text-transform: uppercase;
color: var(--faint);
```

Occurrences: `1050` `.measure figcaption h3` · `1143` `.ranked-facts h3` · `1244` `.tab-panel h2` · `1867` `.panel h3` · `2570` `.passage-columns h3, .occurrence-columns h3` · `2658` `.seer-panel h2` · `2674` `.seer-facts h3, .seer-associations h3` · `3101` `.truncated-types h3` · `3241` `.why-answer h3, .evidence-content section h3` · `3410` `.connection-matrix thead th, .material-table thead th` · `3653` `.matched-surface h3, .comparison-evidence h3` · `3959` `.ritual-row h3` · `4093` `.family-branches h3` · `4431` `.limit-body h3` · `5017` `.selected-relationships h3` · `5125` `.ask-contract h2` · `5399` `.ask-examples h2, .ask-related h3, .ask-caveats h3, .ask-entities h3` · `5544` `.ask-answer-head h2` · `5849` `.ask-retrieval-block h4` · `5952` `.ask-evidence-group h3` · `4917` `.translation-section h2`.

**That is one primitive — `Eyebrow` / `SectionLabel` — duplicated 21 times with 7 sizes and 4 tracking values, applied to `h2`, `h3` and `h4` interchangeably.** It is the clearest single win in the rebuild.

**The card idiom** — `border: 1px solid var(--line)` (73×) + `background: var(--surface)` (65×) + `border-radius: var(--radius|--radius-sm)` (84×) + hover `border-color: var(--accent)` (36×). At least 30 distinct selectors express the same card.

**The uppercase-micro-meta idiom** — `font-size: 0.68–0.72rem; letter-spacing: .06–.09em; text-transform: uppercase; color: var(--faint)` on a `<span>` or `<dt>` — appears ~25 more times outside the heading list above (`.veda-code`, `.crumb-level`, `.veda-chip`, `.result-type`, `.node-type`, `.reuse-row span`, `.related-grid span`, `.entity-chip span`, `.reference-list span`, `.evidence-triple a span`, `.comparison-evidence dt`, `.evidence-summary dt`, `.lens-card dt`, `.metric-row-grid span`, `.gap-card span`, `.limit-alternative strong`, `.alias-label`, `.filter-selects label`, `.filter-bank legend`, `.graph-options label`, `.ask-selects span`, `.ask-context > span`, `.ask-evidence-claim > span`, `.derived-metric header span`, `.tree-level-label`, `.citation-rail span`, `.parallel-kind`, `.formula-list > a > span`, `.condition-kind`, `.verdict`, `.certainty-chip`).

### 1.7 Dead selectors (defined in CSS, referenced nowhere in `src/`)

Only two are genuinely dead:

| Selector | Line | Evidence |
| --- | --- | --- |
| `.metric-row-grid` | 4219, 4224, 4247, 4252, 4258 (5 blocks) | no `metric-row` anywhere in `src/` |
| `.caveat-boundary` | 902, 906 (2 blocks) | `src/components/status.tsx:56,66` builds `caveat-${tone}` where `tone: "neutral" \| "boundary"` (`status.tsx:51`) — so `.caveat-boundary` *is* reachable, but **`.caveat-neutral` is never defined**, and no caller passes `tone="boundary"` except `src/app/vedas/[veda]/page.tsx:116`. **Reachable, barely.** |

The following look dead to a naive grep but are constructed dynamically — **all live**:

| Family | Built at |
| --- | --- |
| `.tone-supported/-partial/-insufficient/-not-built/-unknown` | `status.tsx:30`, `ask-answer.tsx:21`, `connections/page.tsx:95` |
| `.band-certain/-probable/-ambiguous` | `passage-knowledge.tsx:87` |
| `.group-*` (11) | `graph-explorer.tsx:363, 415` |
| `.kind-*` (6) | `entities/[type]/page.tsx:102`, `entities/[type]/[id]/page.tsx:73`, `explore/atharvaveda/page.tsx:31,125,151` |
| `.verdict-not_answerable/-partially_answerable` | `limits/page.tsx:62` |
| `.insight-interpretive_claim` | `insights/page.tsx:64` |
| `.row-muted/-excluded` | `measure.tsx:50` (`row-${row.tone}`, union `"primary"\|"muted"\|"excluded"` at `measure.tsx:11`) |

> `.row-primary` is produced by `measure.tsx:50` but **never defined in CSS**. It is a no-op class in the DOM. Symmetrically `.caveat-neutral` is produced by `status.tsx:56,66` and never defined.

**Near-dead:** `.counterclaim` (`968`) — grep finds no usage; `.gap-witness` (`4521`) — one usage; `.reader-page`, `.reader-footnotes`, `.reader-edge`, `.entity-group`, `.claim-list`, `.span-census`, `.family-tree`, `.passage-rail`, `.ritual-children`, `.evidence-rows.is-threat` each have exactly one call site. `.graph-frame` and `.graph-stage` are two names for the same visual object (`2933` vs `2921`) differing only in that `.graph-frame` takes `.compact`/`.is-empty`.

### 1.8 Classes used in TSX but not defined in CSS

| Class | Used at | Status |
| --- | --- | --- |
| `hero-copy` | `src/app/page.tsx:105` | **undefined** — a bare `<div>` inside `.hero` grid |
| `veda-card-bottom` | `src/app/page.tsx:182` | **undefined** — relies on `.veda-card`'s `justify-content: space-between` |
| `aside-status` | `src/app/vedas/[veda]/page.tsx:130` | **undefined** |
| `is-resolved` | `src/components/ask/ask-answer.tsx:136, 144` | **undefined** — the visual distinction it implies (resolved vs unresolved entity) is carried by `.ask-unresolved li` instead |
| `row-primary` | `src/components/measure.tsx:50` | **undefined** (see §1.7) |
| `caveat-neutral` | `src/components/status.tsx:56, 66` | **undefined** (see §1.7) |
| `notation`, `musical-notation` | — | asserted **absent** by `tests/e2e/journeys.spec.ts:263`; defined nowhere; a guard against a feature that does not exist |

These six are semantically meaningful hooks that were written as if they styled something. A rebuild should either give them meaning or delete them — and note that `is-resolved` in particular reads as a *state contract* that is silently unimplemented.

### 1.9 Responsive model

**Desktop-first, `max-width` throughout.** Nine media blocks:

| Line | Query | Contents |
| --- | --- | --- |
| 4580 | `max-width: 1180px` | `.graph-workspace` rail 350 → 300px. **Only rule at this breakpoint.** |
| 4586 | `max-width: 1080px` | the real tablet breakpoint — 13 selectors: hero → 1col, discovery → 1col, veda grid → 2col, reader/content/profile grids → 1col, sticky asides → static, graph workspace → 1col, **`.desktop-nav { display:none }` + `.mobile-nav-trigger { display:inline-flex }`** |
| 4643 | `max-width: 760px` | the phone breakpoint — 24 selectors |
| 4770 | `prefers-reduced-motion: reduce` | global animation/transition kill + `.veda-card:hover`/`.lens-card:hover` transform reset |
| 4786 | `print` | hides header, footer, `.graph-frame`, `.reader-aside` |
| 4842 | `max-width: 760px` | **second** phone block — 10 more selectors (limit table, formula list, 3-col grid rows, citation list, reader nav, evidence triple) |
| 4943 | `min-width: 761px` | the **only** min-width query in the file — hides `.tabs::after` |
| 6125 | `max-width: 760px` | **third** phone block — 12 Ask selectors |
| 6370 | `max-width: 760px` | **fourth** phone block — 3 recitation selectors |

**Assessment.**

- **Two real breakpoints** (1080, 760) plus one single-rule breakpoint (1180) and one inverted guard (761). The 1180 and 761 queries are patches, not a system.
- **`760` / `761` is an off-by-one pair.** At exactly 760.5px CSS pixels (a fractional viewport, reachable on zoomed desktop) neither query matches and `.tabs::after` renders where it should not. Minor, but symptomatic.
- **The phone breakpoint is split across four non-adjacent blocks** at lines 4643, 4842, 6125 and 6370. Reading "what happens at 390px" requires four separate reads of the file. This is the single worst maintainability property of the responsive layer.
- **Mobile-first is not used anywhere.** Every layout is written desktop-wide first and then collapsed. That is why the four phone blocks are needed and why they keep growing.
- **No container queries**, despite `.graph-detail`, `.panel`, `.veda-card`, `.comparison-column` and `.ask-retrieval-block` all being components whose layout depends on their *container*, not the viewport.
- **Where it breaks.** (a) Between 761px and 1080px the site is in a two-column desktop layout with a **hidden primary nav** — `.desktop-nav` disappears at 1080 but `.reader-layout` / `.content-grid` / `.profile-grid` also collapse at the same breakpoint, so the tablet band gets mobile navigation with a desktop-width single column and a `68ch` measure that is much narrower than the container. (b) `.graph-workspace` is the only thing that acknowledges 1180, so between 1081 and 1180 the graph detail rail is 350px against a stage that is already cramped. (c) `.metric-strip` goes 4-col → 2-col at 760 with no 3-col step, so at 780px four metrics share ~730px at `padding: 22px 4px`. (d) The overflow-containment block at 4822–4838 is an admission that the grid layout leaks: 12 selectors need an explicit `min-width: 0` and `.limit-measurements` needs `display: block; overflow-x: auto` to stop a table pushing the page sideways.
- **Positive:** `tests/visual-qa.mjs` screenshots 24 surfaces at 1440/1024/390 and reports any element whose right edge exceeds `documentElement.clientWidth + 1`. That harness is the reason the overflow patches exist and it should be kept and wired to an exit code (it currently always exits 0 — `visual-qa.mjs:124–128`).

### 1.10 Type scale

353 `font-size` declarations. Distinct values, by frequency:

| Value | Count | | Value | Count |
| --- | --- | --- | --- | --- |
| `0.78rem` | 31 | | `1.02rem` | 8 |
| `0.72rem` | 22 | | `0.79rem` | 8 |
| `0.74rem` | 21 | | `1rem` | 7 |
| `0.86rem` | 20 | | `0.83rem` | 7 |
| `0.76rem` | 20 | | `0.92rem` | 6 |
| `0.8rem` | 19 | | `1.3rem` | 5 |
| `0.84rem` | 19 | | `1.7rem`,`1.2rem`,`1.28rem`,`1.12rem`,`0.94rem`,`0.87rem` | 3 each |
| `0.88rem` | 18 | | `1.5rem`,`1.16rem`,`1.15rem`,`1.06rem`,`0.66rem` | 2 each |
| `0.7rem` | 18 | | `3rem`,`1.6rem`,`1.55rem`,`1.45rem`,`1.4rem`,`1.36rem`,`1.34rem`,`1.32rem`,`1.25rem`,`1.24rem`,`1.22rem`,`1.18rem`,`1.14rem`,`1.1rem`,`1.08rem`,`1.05rem`,`1.04rem`,`0.95rem`,`0.73rem` | 1 each |
| `0.68rem` | 18 | | `0.84em` | 1 |
| `0.82rem` | 16 | | `15px` | 1 (`body`, line 79) |
| `0.85rem` | 13 | | `0.7rem !important` | 1 |
| `0.75rem` | 10 | | 8 `clamp()` expressions | 1 each |
| `0.9rem` | 9 | | | |

**Assessment: there is no scale.** There are **57 distinct font sizes** in a 6,407-line stylesheet. Between `0.66rem` and `0.95rem` alone there are **19 distinct values**, spaced as little as `0.01rem` (0.15px at a 15px root) apart — `0.78`/`0.79`, `0.82`/`0.83`/`0.84`/`0.85`/`0.86`, `0.87`/`0.88`. Those differences are not perceptible; they are the residue of tuning individual rules in isolation.

The eight fluid headings are individually reasonable but mutually unrelated:

| Line | Selector | clamp |
| --- | --- | --- |
| 189 | `.sanskrit` | `clamp(1.18rem, 0.95rem + 0.9vw, 1.65rem)` |
| 494 | `.hero h1` | `clamp(2.5rem, 1.6rem + 3.1vw, 4.05rem)` |
| 526 | `.metric strong` | `clamp(1.5rem, 1.1rem + 1.2vw, 2.1rem)` |
| 550 | `.section-heading h2` | `clamp(1.65rem, 1.3rem + 1.1vw, 2.3rem)` |
| 690 | `.evidence-pitch h2` | `clamp(1.6rem, 1.3rem + 1vw, 2.2rem)` |
| 715 | `.page-heading h1` | `clamp(2rem, 1.5rem + 1.8vw, 2.9rem)` |
| 1319 | `.citation-line h1` | `clamp(2rem, 1.6rem + 1.6vw, 2.85rem)` |
| 2431 | `.profile-hero h1` | `clamp(2.2rem, 1.7rem + 2vw, 3.3rem)` |

Three different h1 clamps (`.hero h1`, `.page-heading h1`, `.citation-line h1`, `.profile-hero h1` — four) for what a reader experiences as one level.

**Line height:** 13 distinct values — `1.5` (15), `1.55` (11), `1.6` (9), `1.62` (5), `1.66` (2), and singletons `1.04`, `1.18`, `1.32`, `1.7`, `1.72`, `1.8`, `1.95`, `2.1`. Body is `1.6` (line 80); headings `1.18` (line 94). `1.5`/`1.55`/`1.6`/`1.62` are four values doing one job.

**Weight:** only three — `500` (39), `600` (28), `400` (2). Newsreader and Geist are both loaded at default weights. **There is no bold.** `h1–h4` are `font-weight: 500` (line 92). This is a deliberate editorial choice and is worth preserving as an explicit rule.

**Tracking:** 16 distinct values. `0.08em` (22), `0.09em` (17), `0.1em` (14) — three values for the same uppercase-eyebrow effect; then `0.06em` (3), `0.02em` (3), `0.14em` (2), `0.07em` (2), `0.05em` (2), `0` (2), and singletons `0.16em`, `0.11em`, `0.04em`, `0.004em`, `-0.01em`, `-0.014em`, `0.06em !important`.

**`text-transform: uppercase` appears 62 times.** Uppercase is doing an enormous amount of hierarchical work and is entirely unnamed.

### 1.11 Spacing

**`gap`** — 33 distinct values, of which 28 are single scalars:
`1px`(4) `2px`(6) `3px`(1) `4px`(6) `5px`(8) `6px`(19) `7px`(13) `8px`(24) `9px`(9) `10px`(24) `11px`(4) `12px`(28) `13px`(3) `14px`(27) `15px`(1) `16px`(17) `18px`(14) `20px`(9) `22px`(7) `24px`(2) `26px`(5) `28px`(5) `30px`(3) `34px`(2) `40px`(4) `46px`(1) `48px`(1) `52px`(1) `56px`(2) `62px`(1), plus five two-axis pairs.

**`padding` scalars** (183 declarations):
`1px`(8) `2px`(9) `3px`(1) `4px`(9) `5px`(12) `6px`(12) `7px`(12) `8px`(12) `9px`(6) `10px`(19) `11px`(16) `12px`(20) `13px`(15) `14px`(27) `15px`(19) `16px`(33) `17px`(1) `18px`(25) `20px`(22) `22px`(12) `24px`(12) `26px`(8) `28px`(6) `36px`(1) `40px`(2) `44px`(2) `46px`(1) `48px`(1) `54px`(1) `56px`(1) `62px`(1) `64px`(2) `72px`(1) `76px`(1) `90px`(1) `96px`(1).

**Assessment: there is no scale — there is a continuum.** Every integer from 1 to 20 except 19 is used. `13px`, `15px`, `17px`, `11px`, `9px` and `7px` are all present in quantity, which means the values were chosen per-rule by eye rather than drawn from a set. A 4px or 8px grid would collapse these ~36 padding values and ~30 gap values to about 10 steps each.

The only *structural* spacing constants are `.shell` gutter `48px` → `32px` (`166`, `4645`), `.page` block padding `44px 96px` → `28px 64px` (`171`, `4649`), `.section` block padding `72px` → `46px` (`545`, `4654`), and the sticky offset `92px` (`1484`, `1841`).

### 1.12 Motion

**Transitions** — 13 declarations, 5 distinct durations, 1 easing:

| Line | Selector | Declaration |
| --- | --- | --- |
| 232–235 | `.button` | `background .18s ease, border-color .18s ease, color .18s ease` |
| 273–275 | `.icon-button` | `border-color .18s ease, color .18s ease` |
| 376–378 | `.desktop-nav a` | `color .16s ease, background .16s ease` |
| 585–587 | `.veda-card` | `border-color .2s ease, transform .2s ease` |
| 662 | `.discovery-link` | `background .16s ease` |
| 2117 | `.search-results-wrap` | `opacity .2s ease` |
| 4296–4298 | `.lens-card` | `border-color .2s ease, transform .2s ease` |
| 5259 | `.ask-textarea-wrap` | `border-color .15s ease` |
| 5428–5430 | `.ask-chip-row button` | `border-color .15s ease, color .15s ease` |
| 5657–5659 | `.ask-cite` | `background .12s ease, color .12s ease` |
| 6241 | `.recitation-play` | `background 120ms ease, border-color 120ms ease` |

Durations: `0.12s`, `0.15s`, `0.16s`, `0.18s`, `0.2s`, `120ms`. **Six durations for what are three interaction classes** (chip/link hover, card hover, field focus). `120ms` and `0.12s` are the same number written two ways. Easing is `ease` in 20 of 21 cases (`ease-in-out` once, for `ask-pulse`), i.e. the browser default cubic-bezier(0.25,0.1,0.25,1) — **no custom easing exists**.

**The 36 `:hover { border-color: var(--accent) }` rules are mostly untransitioned** — only `.veda-card` and `.lens-card` declare a `border-color` transition. Card hovers therefore snap while button hovers ease. Inconsistent and unnoticed.

**Keyframes** — 3:

| Line | Name | Used by | Params |
| --- | --- | --- | --- |
| 1036 | `shimmer` | `.skeleton` (1033) | `1.5s linear infinite`, 220 % background-position sweep |
| 2996 | `spin` | `.graph-spinner` (2993) | `0.8s linear infinite` |
| 5484 | `ask-pulse` | `.ask-phases li[data-state=active] i` (5476) | `1.1s ease-in-out infinite`, opacity 1 → 0.35 |

**JS-driven motion** (outside CSS, therefore outside the reduced-motion block):

| File:line | Motion |
| --- | --- |
| `graph-canvas.tsx:344–346` | cose layout `animate: !matchMedia("(prefers-reduced-motion: reduce)").matches` — **correctly guarded** |
| `graph-canvas.tsx:347` | `animationDuration: 460` |
| `graph-canvas.tsx:361` | `cy.animate({ fit: …, duration: 320 })` — **NOT guarded** |
| `ask-experience.tsx:126–128` | `scrollIntoView({ behavior: "smooth" })` — **NOT guarded** |
| `ask-evidence-drawer.tsx:70` | `scrollIntoView({ block: "center", behavior: "smooth" })` — **NOT guarded** |

**`prefers-reduced-motion` handling** (`4770–4784`):

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: .01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: .01ms !important;
    scroll-behavior: auto !important;
  }
  .veda-card:hover, .lens-card:hover { transform: none; }
}
```

**Verdict: honoured for CSS, breached for JS.** The block correctly neutralises all CSS transitions and animations and resets the two `translateY(-2px)` hovers. But `scroll-behavior: auto !important` **cannot** override an explicit `behavior: "smooth"` argument to `scrollIntoView` — the JS option wins over the CSS property. So a reduced-motion reader who clicks a citation chip in Ask still gets a smooth scroll (`ask-experience.tsx:127`, `ask-evidence-drawer.tsx:70`), and a "fit to view" click still gets a 320 ms animated camera move (`graph-canvas.tsx:361`). Three concrete violations.

Also: `html { scroll-behavior: smooth }` at `globals.css:76` is applied globally and *is* reset by the block — that one is fine.

### 1.13 z-index

Six values, no ladder, no tokens:

| Line | Selector | z-index |
| --- | --- | --- |
| 208 | `.skip-link` | `100` |
| 330 | `.site-header` | `40` |
| 3156 | `.dialog-overlay` | `60` |
| 3166 | `.evidence-drawer` | `61` |
| 3179 | `.evidence-drawer header` | `1` (local) |
| 4533 | `.mobile-nav-panel` | `61` |

`.skip-link` at 100 correctly outranks everything. The 60/61 pair is a Radix portal stacking pair. `40` for the header is arbitrary. Sticky elements (`.reader-aside`, `.sticky-aside`, both `position: sticky; top: 92px`) declare **no** z-index, which works only because the header is `sticky` too and earlier in source order.

### 1.14 `!important` — 16 occurrences

| Line | Declaration | Why it exists |
| --- | --- | --- |
| 1068 | `.measure-scope { color: var(--tone-partial) !important }` | overrides `.measure figcaption p` |
| 1535, 1538 | `.certainty-chip { display: inline-block !important; letter-spacing: .06em !important }` | overrides `.reference-list span` / `.entity-chip span` |
| 1544, 1550, 1556 | `.certainty-chip.band-* { color: … !important }` | same |
| 2372 | `.condition-kind { font-size: .7rem !important }` | overrides `.entity-index-row > div:first-child > span` |
| 2380, 2386, 2393, 2401 | `.condition-kind.kind-* { color: … !important }` | same |
| 4525 | `.gap-witness { color: var(--muted) !important }` | overrides `.gap-card span` |
| 4774–4777 | reduced-motion block ×4 | legitimate |

**Twelve of sixteen exist because a chip is being placed inside a container that already styles bare `span`s.** That is a direct consequence of styling by element selector (`.entity-chip span`, `.gap-card span`, `.reference-list span`) instead of by class. A primitive-based rebuild removes all twelve.

### 1.15 Tailwind: imported, paid for, unused

`postcss.config.mjs` loads only `@tailwindcss/postcss`. `globals.css:1` is `@import "tailwindcss"`, which in v4 pulls in **Preflight**, the **default `@theme`** (all 22 namespaces, ~300 colour variables, the full type/spacing/radius/shadow/ease scales), and the utilities engine.

The app then:

- re-implements part of Preflight by hand — `* { box-sizing }` (74), `ul,ol,dl,dd { margin:0; padding:0 }` (128), `li { list-style:none }` (134), `table { border-collapse: collapse }` (138), `button,input,select,textarea { font: inherit; color: inherit }` (114);
- declares three theme variables it never consumes (`67–71`);
- uses **zero** utility classes.

It also does **not** declare `@custom-variant dark (&:where(.dark, .dark *))`. In Tailwind v4 the built-in `dark:` variant keys on `prefers-color-scheme`, while `next-themes` is configured with `attribute="class"` (`theme-provider.tsx:8`). **If anyone writes a single `dark:` utility today it will ignore the user's explicit theme choice.** That is a live trap for the rebuild.

Net effect: Tailwind currently contributes Preflight and a handful of unused variables, at the cost of a build-step dependency and a second, invisible reset. Either commit to it (§15) or drop it — the present state is the worst of both.

---

## 2. Component tree

### 2.1 Route inventory (`src/app/`) — all Server Components unless noted

| File | Kind | Renders | Owned classes | Key imports | Reuse |
| --- | --- | --- | --- | --- | --- |
| `layout.tsx` | Server | `<html>`/`<body>`, skip link, `SiteHeader`, `<main id="main">`, footer | `.skip-link`, `.site-footer`, `.shell`, `.footer-brand` | `next/font/google` ×3, `SiteHeader`, `SECONDARY_NAV`, `ThemeProvider` | root |
| `page.tsx` (home) | Server | hero + metric strip + veda grid + discovery list + evidence pitch | `.hero`, `.hero-copy`*, `.hero-kicker`, `.hero-lede`, `.hero-actions`, `.hero-visual`, `.metric-strip`, `.metric`, `.section`, `.section-heading`, `.veda-grid`, `.veda-card`, `.veda-card-top`, `.veda-code`, `.veda-card-bottom`*, `.veda-count`, `.scope-warning`, `.discovery-layout`, `.discovery-list`, `.discovery-link`, `.evidence-pitch` | `ServiceUnavailable`, `HomeNetwork`, `Caveat`, `load` | single-use |
| `loading.tsx` | Server | three `.skeleton` divs | — | — | route-level |
| `error.tsx` | **Client** | `.empty-state` + retry button | — | — | route-level |
| `not-found.tsx` | Server | `.empty-state`, `.not-found-code` | `.not-found-code` | `Link` | route-level |
| `ask/page.tsx` | Server | `PageHeading` + `.ask-contract` + `AskExperience` | `.ask-page`, `.ask-contract` | `AskExperience`, `PageHeading` | single-use |
| `search/page.tsx` | Server (25 ln) | `PageHeading` + `SearchExperience` | `.search-page` | `SearchExperience`, `PageHeading` | single-use |
| `graph/page.tsx` | Server (38 ln) | `PageHeading` + `GraphExplorer`; `revalidate: 0` | `.graph-page` | `GraphExplorer` | single-use |
| `vedas/page.tsx` | Server | work list | `.work-list`, `.work-row`, `.work-code`, `.work-facts` | `PageHeading`, `Caveat`, `KnowledgeStatus` | single-use |
| `vedas/[veda]/page.tsx` | Server | `.content-grid` + `StructureBrowser` + 3 `.panel` asides; `generateStaticParams` | `.content-grid`, `.collection-metrics`, `.sticky-aside`, `.panel`, `.panel-links`, `.aside-status`*, `.chip-row` | `StructureBrowser`, `VedaAudioPanel`, `Caveat`, `CaveatList`, `KnowledgeStatus` | single-use |
| `passage/[key]/page.tsx` | Server | the reader: breadcrumbs, `.citation-line`, `.mantra-block`, `RecitationPlayer`, witnesses, translations, `.reader-aside`, `PassageKnowledge` | `.reader-page`, `.reader-breadcrumbs`, `.reader-layout`, `.reading-column`, `.citation-line`, `.veda-chip`, `.mantra-block`, `.text-meta`, `.witness-block`, `.translation-section`, `.reuse-callout`, `.reader-nav`, `.reader-aside` | `CopyButton`, `PassageKnowledge`, `RecitationPlayer`, `AskAboutButton`, `KnowledgeStatus` | single-use |
| `reuse/[key]/page.tsx` | Server | `ParallelComparison` stack | `.comparison-stack`, `.transmission-note` | `ParallelComparison`, `PageHeading`, `Caveat` | single-use |
| `devatas/page.tsx` | Server | deity index | `.entity-index`, `.entity-index-row`, `.certainty-mini` | `PageHeading`, `Caveat`, `CaveatList` | single-use |
| `devatas/[id]/page.tsx` | Server (largest page) | `.profile-hero` + `.profile-grid` + 8 sections + `DerivedMetricCard` | `.profile-page`, `.profile-hero`, `.profile-iast`, `.alias-line`, `.axis-list`, `.profile-actions`, `.profile-grid`, `.profile-main`, `.profile-sections`, `.certainty-split`, `.passage-columns`, `.citation-list`, `.related-section`, `.related-grid`, `.derived-grid` | `DerivedMetricCard`, `MeasureChart`, `RankedFacts`, `AskAboutButton`, `KnowledgeStatus`, `Caveat`, `CaveatList` | single-use |
| `entities/page.tsx` | Server | `.type-grid` inventory | `.type-grid`, `.entity-group` | `PageHeading`, `Caveat` | single-use |
| `entities/[type]/page.tsx` | Server | `.kind-tabs` + `.entity-index` | `.kind-tabs`, `.condition-kind` | `PageHeading`, `NothingHere`, `Caveat` | single-use |
| `entities/[type]/[id]/page.tsx` | Server | entity profile + `SeerPanel` | `.page-heading` (hand-rolled `PageHeader` at :205), `.profile-grid`, `.entity-detail-meta` | `SeerPanel`, `MeasureChart`, `KnowledgeStatus` | single-use |
| `rituals/page.tsx` | Server | `.ritual-grid` | `.ritual-grid` | `PageHeading`, `Caveat` | single-use |
| `rituals/[id]/page.tsx` | Server | `.ritual-map`, `.ritual-steps`, `.citation-rail` | `.ritual-shape`, `.ritual-map`, `.ritual-row`, `.ritual-steps-section`, `.ritual-steps`, `.ritual-children`, `.passage-rail`, `.citation-rail` | `PageHeading`, `Caveat`, `KnowledgeStatus` | single-use |
| `formulas/page.tsx` | Server | `.formula-stats` + `.formula-list` | `.formula-stats`, `.formula-list` | `PageHeading`, `Caveat` | single-use |
| `formula-families/[id]/page.tsx` | Server | `.family-branches`, `.occurrence-columns`, `.evidence-summary` | `.family-tree`, `.family-branches`, `.occurrence-section`, `.occurrence-columns`, `.evidence-summary`, `.formula-chip-list`, `.formula-chip` | `PageHeading`, `CaveatList` | single-use |
| `connections/page.tsx` | Server | `.connection-matrix` table + `.reuse-list` + `.census-grid` | `.matrix-section`, `.matrix-wrap`, `.connection-matrix`, `.cell`, `.cell-reason`, `.cell-kind`, `.cell-total`, `.connections-explainer`, `.reuse-section`, `.reuse-list`, `.reuse-row`, `.span-census`, `.census-grid` | `PageHeading`, `Caveat`, `KnowledgeStatus` | single-use |
| `explore/page.tsx` | Server | `.lens-grid` | `.lens-grid`, `.lens-card`, `.lens-icon`, `.lens-cta` | `PageHeading`, `Caveat` | single-use |
| `explore/atharvaveda/page.tsx` | Server | `.av-block` ×4, `.concern-strip` | `.av-block`, `.av-section-title`, `.av-rows`, `.av-row`, `.evidence-rows`, `.concern-strip`, `.condition-kind` | `PageHeading`, `Caveat`, `CaveatList` | single-use |
| `insights/page.tsx` | Server | `.insight-section` ×N + `DerivedMetricCard` | `.insight-section`, `.data-row-grid`, `.claim-list` | `DerivedMetricCard`, `PageHeading`, `Caveat` | single-use |
| `limits/page.tsx` | Server | `.limit-card` ×N | `.limits-page`, `.limit-list`, `.limit-card`, `.verdict`, `.limit-body`, `.limit-measurements`, `.limit-alternative`, `.limits-footer` | `PageHeading`, `Caveat` | single-use |
| `material-culture/page.tsx` | Server | `.kind-tabs` + `.material-table` + `.gap-card` | `.material-table`, `.declared-gaps`, `.gap-card`, `.gap-witness` | `PageHeading`, `MeasureChart`, `Caveat` | single-use |

`*` = class used in TSX, undefined in CSS (§1.8).

**Every route is a Server Component except `error.tsx`.** There are no route-level `dynamic`/`revalidate` exports other than the inline `{ revalidate: 0 }` at `graph/page.tsx:20`.

### 2.2 Shared components (`src/components/`)

| File | Lines | Client? | What it is | Owned classes | Imports | Reuse |
| --- | --- | --- | --- | --- | --- | --- |
| `navigation.ts` | 20 | n/a | `PRIMARY_NAV` (7 items) + `SECONDARY_NAV` (2) | — | — | 3 consumers |
| `site-header.tsx` | 41 | Server | sticky header: brand SVG, `NavLinks`, search action, `ThemeToggle`, `MobileNav` | `.site-header`, `.header-inner`, `.brand`, `.brand-mark`, `.header-actions`, `.search-action` | `MobileNav`, `NavLinks`, `ThemeToggle` | root only |
| `nav-links.tsx` | 25 | **Client** | desktop nav, `usePathname` for `aria-current` | `.desktop-nav` | `PRIMARY_NAV` | 1 |
| `mobile-nav.tsx` | 49 | **Client** | Radix Dialog drawer | `.mobile-nav-trigger`, `.mobile-nav-panel`, `.mobile-nav-top`, `.mobile-nav-links`, `.dialog-overlay`, `.icon-button` | Radix Dialog, both NAVs | 1 |
| `theme-provider.tsx` | 16 | **Client** | `next-themes` wrapper | — | `next-themes` | root only |
| `theme-toggle.tsx` | 24 | **Client** | icon button, both icons always rendered, CSS picks | `.theme-toggle`, `.theme-icon-light/-dark`, `.icon-button` | `useTheme` | 1 |
| `page-heading.tsx` | 27 | Server | back link + h1 + lede | `.page-heading`, `.back-link` | `Link` | **20 routes, 39 refs** — the most-reused component |
| `empty-state.tsx` | 79 | Server | `ServiceUnavailable`, `RequestFailed`, `LoadFailure`, `NothingHere`, `NoSearchResults` | `.empty-state`, `.is-inline`, `.empty-hint` | `Link`, 4 icons | **22 files, 54 refs** |
| `status.tsx` | 125 | Server | `KnowledgeStatus`, `Caveat`, `CaveatList`, `InterpretationFrame` | `.knowledge-status`, `.caveat`, `.caveat-list`, `.interpretation-frame`, `.interpretation-tag` | `statusCopy`, 5 icons, `clsx` | **`KnowledgeStatus` 21 files / 72 refs; `Caveat` 22/99; `CaveatList` 19/41** |
| `measure.tsx` | 125 | Server | `MeasureChart` (figure + table + bars), `RankedFacts` | `.measure`, `.measure-table`, `.measure-track`, `.measure-bar`, `.measure-value`, `.measure-null`, `.measure-notes`, `.measure-caveat`, `.measure-scope`, `.ranked-facts` | `KnowledgeStatus`, `clsx` | 5 files / 11 + 3/12 |
| `tabs.tsx` | 39 | **Client** | Radix Tabs wrapper | `.tabs`, `.tab-list`, `.tab-trigger`, `.tab-badge`, `.tab-panel` | Radix Tabs | **1 consumer** (`passage-knowledge`) |
| `copy-button.tsx` | 19 | **Client** | clipboard button, 1.8 s "Copied" | `.copy-button` | 2 icons | 2 consumers |
| `derived-metric.tsx` | 53 | Server | one derived measure card | `.derived-metric`, `.derived-headline`, `.derived-values`, `.derived-reading`, `.derived-scope`, `.mono` | — | 2 consumers |
| `seer-panel.tsx` | 171 | Server | seer apparatus panel | `.seer-panel`, `.seer-facts`, `.seer-associations`, `.provenance`, `.provenance-list`, `.chip-row`, `.panel` | `MeasureChart`, `RankedFacts`, `KnowledgeStatus` | 1 |
| `veda-audio-panel.tsx` | 151 | Server | recitation coverage panel | `.panel`, `.panel-note`, `.panel-note-faint` | 1 icon | 1 |
| `passage-knowledge.tsx` | 304 | Server | the reader's 4-tab sidebar (Context/Entities/Connections/Evidence) | `.reference-list`, `.entity-chip-list`, `.entity-chip`, `.parallel-list`, `.parallel-row`, `.parallel-kind`, `.provenance-list`, `.basis-list`, `.provenance`, `.certainty-chip`, `.panel-note` | `Tabs`/`TabPanel`, `KnowledgeStatus`, `Caveat` | 1 |
| `parallel-comparison.tsx` | 191 | Server | two-column verse comparison | `.comparison`, `.comparison-banner`, `.comparison-grid`, `.comparison-column`, `.comparison-head`, `.comparison-translation`, `.matched-surface`, `.comparison-evidence`, `.veda-chip` | `CopyButton`, `KnowledgeStatus` | 1 |
| `structure-browser.tsx` | 167 | **Client** | lazy-expanding passage tree; `--depth` inline var | `.structure-browser`, `.structure-top`, `.tree-row`, `.branch-label`, `.tree-loading`, `.tree-level-label`, `.tree-more` | 3 icons | 1 |
| `search-experience.tsx` | 320 | **Client** | debounced search + filters + results + `/` shortcut | `.search-experience`, `.search-field`, `.filter-bank`, `.filter-row`, `.filter-selects`, `.search-prompts`, `.search-results-wrap`, `.results-meta`, `.refreshing`, `.search-results`, `.result-row`, `.result-skeleton`, `.result-type`, `.result-veda`, `.search-error`, `.search-caveats` | `NoSearchResults`, `entityHref`, `statusCopy` | 1 |
| `graph-canvas.tsx` | 383 | **Client** | Cytoscape mount; exports `semanticGroup`, `GROUP_STYLE`, `SemanticGroup` | `.graph-canvas` | lazy `cytoscape`, `knowledge.ts` | 2 consumers |
| `graph-explorer.tsx` | 564 | **Client** | full graph UI: toolbar, legend, stage, detail rail, node list | `.graph-explorer`, `.graph-toolbar`, `.graph-options`, `.graph-legend`, `.legend-chip`, `.graph-workspace`, `.graph-stage`, `.graph-busy`, `.graph-spinner`, `.graph-bounds`, `.graph-message`, `.graph-detail`, `.node-type`, `.graph-detail-actions`, `.graph-detail-empty`, `.truncated-types`, `.graph-node-list`, `.selected-relationships` | `EvidenceDrawer`, `GraphCanvas`, `KnowledgeStatus`, `useRouter`, `useTheme` | 1 |
| `home-network.tsx` | 29 | **Client** | compact graph for the hero | `.graph-frame`, `.compact`, `.graph-caption` | `GraphCanvas`, `useTheme` | 1 |
| `evidence-drawer.tsx` | 228 | **Client** | "why are these connected?" Radix drawer | `.evidence-drawer`, `.evidence-content`, `.evidence-loading`, `.evidence-triple`, `.why-answer`, `.evidence-metadata`, `.evidence-spans`, `.evidence-passages`, `.evidence-technical`, `.caveat-text`, `.dialog-overlay` | Radix Dialog, `knowledge.ts`, `KnowledgeStatus` | 1 |
| `recitation-player.tsx` | 307 | **Client** | audio/video transport + provenance disclosure | `.recitation` (+13 children) | 5 icons | 1 |
| `ask/ask-about-button.tsx` | 37 | Server | contextual link into `/ask` | `.ask-about-quiet` or `.button {variant}` | 1 icon | 3 consumers |
| `ask/ask-experience.tsx` | 406 | **Client** | the Ask orchestrator: health, composer, phases, error, answer, drawer | `.ask-experience`, `.ask-unavailable`, `.ask-hint`, `.ask-context`, `.ask-composer`, `.ask-textarea-wrap`, `.ask-controls`, `.ask-selects`, `.ask-mode-note`, `.ask-submit-row`, `.ask-counter`, `.ask-submit-hint`, `.ask-clear`, `.ask-examples`, `.ask-chip-row`, `.ask-pending`, `.ask-phases`, `.ask-pending-note`, `.ask-error` | `ask.ts`, `ask-citations.ts`, `AskAnswer`, `AskEvidenceDrawer` | 1 |
| `ask/ask-answer.tsx` | 299 | **Client** | the answer article: badges, prose+citations, caveats, entities, retrieval `<details>` | `.ask-answer`, `.ask-answer-head`, `.ask-badges`, `.ask-support`, `.ask-status-note`, `.ask-interpretive`, `.ask-prose`, `.ask-cite-group`, `.ask-cite`, `.ask-answer-actions`, `.ask-provenance`, `.ask-caveats`, `.ask-entity-list`, `.ask-entity`, `.ask-unresolved`, `.ask-related`, `.ask-retrieval`, `.ask-retrieval-body`, `.ask-retrieval-block`, `.ask-tag-row`, `.ask-empty-note`, `.ask-figures` | `ask.ts`, `ask-citations.ts`, `entityHref`, `KnowledgeStatus` | 1 |
| `ask/ask-evidence-drawer.tsx` | 229 | **Client** | grouped evidence drawer; exports `evidenceDomId` | `.evidence-drawer`, `.evidence-content`, `.ask-evidence-group`, `.ask-evidence-item`, `.ask-evidence-head`, `.ask-evidence-id`, `.ask-evidence-fact/-relation/-meta`, `.ask-evidence-claim`, `.ask-qualifier`, `.ask-evidence-footer` | Radix Dialog, `ask.ts`, `KnowledgeStatus` | 1 |

### 2.3 Dependency picture

```
layout.tsx (Server)
├── ThemeProvider ──── next-themes                     [client boundary #1]
├── SiteHeader (Server)
│   ├── NavLinks ───── usePathname                     [client boundary #2]
│   ├── ThemeToggle ── useTheme                        [client boundary #3]
│   └── MobileNav ──── Radix Dialog                    [client boundary #4]
├── <main> {route}
└── footer ─────────── SECONDARY_NAV

SHARED LEAVES (used by ≥2 routes)
  PageHeading    → 20 routes
  empty-state.*  → 22 files
  status.*       → KnowledgeStatus 21 · Caveat 22 · CaveatList 19
  measure.*      → MeasureChart 5 · RankedFacts 3
  AskAboutButton → 3
  CopyButton     → 2
  DerivedMetricCard → 2
  GraphCanvas    → 2  (graph-explorer, home-network)

SINGLE-USE ISLANDS (1 consumer each)
  SearchExperience   → /search
  GraphExplorer      → /graph  ├─ GraphCanvas ─ cytoscape (lazy import)
                               └─ EvidenceDrawer ─ Radix Dialog
  StructureBrowser   → /vedas/[veda]
  VedaAudioPanel     → /vedas/[veda]
  RecitationPlayer   → /passage/[key]
  PassageKnowledge   → /passage/[key] ── Tabs/TabPanel ─ Radix Tabs
  ParallelComparison → /reuse/[key] ── CopyButton
  SeerPanel          → /entities/[type]/[id] ── MeasureChart, RankedFacts
  HomeNetwork        → /
  AskExperience      → /ask
       ├── AskAnswer
       └── AskEvidenceDrawer ─ Radix Dialog
```

**Observations.**

- **Four client boundaries in the shell.** `ThemeProvider` wraps *everything* including the whole server tree as `children`, which is correct (children stay server-rendered). `NavLinks`, `ThemeToggle` and `MobileNav` are three separate small boundaries rather than one — good granularity.
- **The shared layer is thin and semantic, not visual.** `PageHeading`, `KnowledgeStatus`, `Caveat`, `MeasureChart`, `EmptyState` are the only cross-route components, and every one of them exists to enforce an *epistemic* rule (never render an absence as a zero), not a visual one. **There is no visual primitive layer at all** — no `Card`, `Stack`, `Grid`, `Chip`, `Eyebrow`, `Table`, `Disclosure`. That vacuum is exactly what the 6,407 lines of CSS are filling.
- **`Tabs` is a generic wrapper with one consumer.** Either promote it or inline it.
- **`graph-canvas.tsx` exports domain logic (`semanticGroup`, `GROUP_STYLE`) from a rendering module.** `tests/unit/graph-semantics.test.ts` imports from it, which means a pure-logic test pulls in a Cytoscape-typed module. That belongs in `lib/`.
- **`entities/[type]/[id]/page.tsx:205–225` hand-rolls a `PageHeader`** that duplicates `PageHeading` plus a `.profile-iast` line, instead of extending the shared component. Same for `devatas/[id]/page.tsx:110–130`.

---

## 3. Data layer

### 3.1 `src/lib/api.ts` (152 lines) — the server-side client

**Type surface (`:5–46`).** 42 type aliases, every one derived from `components["schemas"]` in `api-schema.ts` (`:1–3`). Nothing is hand-written. This is the correct pattern and should not change.

**Base URL (`:58`).** `export const API_BASE = process.env.VEDAGRAPH_API_URL ?? "http://127.0.0.1:8000"`. Server-only; never inlined into client code (enforced by the `/backend/*` rewrite for client fetches).

**Error type (`:48–56`).** `class ApiError extends Error` carrying `status`.

**Three fixed messages (`:60–62`):**
- `NOT_FOUND` = "This atlas entry is not held in the current corpus."
- `UNAVAILABLE` = "The **VedaGraph** knowledge service did not respond." ← brand string
- `REFUSED` = "The knowledge service could not answer this request."

**`apiGet<T>` (`:64–88`).**
- Builds `${API_BASE}/api/v1${path}`.
- Abort: if no external `signal`, creates its own `AbortController` with `options.timeoutMs ?? 15_000` (`:68–71`). **If a caller passes `signal`, the timeout is silently disabled** (`controller` is `null`, so no `setTimeout` is scheduled). That is a real hazard: an externally-signalled request has no upper bound.
- Cache: `next: { revalidate: options.revalidate ?? 60 }` (`:75`) — **60-second ISR on every request by default.**
- `Accept: application/json` only. No auth, no custom headers.
- 404 → `ApiError(NOT_FOUND, 404)`; any other non-2xx → `ApiError(REFUSED, status)`; any throw (including abort) → `ApiError(UNAVAILABLE, 503)` (`:82–84`). **An `AbortError` from a caller-supplied signal is therefore reported as a 503 service outage**, which is the same false-outage class of bug the `next.config.ts` comment warns about.

**`load<T>` (`:96–106`).** Non-throwing wrapper returning a discriminated union `Loaded<T> = {ok:true,data} | {ok:false,status,message}`. Every server component uses this so a failure never forces JSX inside a `try`. **This is the single best piece of architecture in the data layer.**

**`firstFailure(...)` (`:109–112`).** Returns the first non-ok result.

**Identifier helpers.** `encoded` (`:114`) = `encodeURIComponent`. `routeId` (`:123–129`) = defensive `decodeURIComponent` — required because Next hands dynamic params still percent-encoded (documented at `:118–122` and in `README.md`).

**Static maps.** `workIds` (`:131`), `workSlugs` (`:138`), `vedaOrder` (`:145`), `vedaNames` (`:147`).

### 3.2 `src/lib/api-schema.ts` (9,377 lines) — generated, do not edit

Produced by `openapi-typescript` from the served `/openapi.json` (regeneration command in `README.md`). Exports `interface paths` (**43 path entries**) and `components["schemas"]` (**264 schema objects**). No runtime code — it is `.d.ts`-shaped TypeScript with JSDoc carried over from the FastAPI docstrings.

Notable: it **does** contain `AskRequest` (`:1301`), `AskResponse` (`:1321`), `/api/v1/ask` (`:9236`, `:9246`) and `/api/v1/ask/health`. **This contradicts the comment at `src/lib/ask.ts:4–7`**, which states the Ask routes "were added after the last generation" and justifies hand-writing the types. That comment is stale; the Ask types could now be derived like everything else. Flag for the rebuild.

Brand strings inside the generated file (`:1181`, `:1183`, `:1222`, `:2162`, `:2998`, `:3126`) are backend docstrings — they will change only when the backend changes and must **not** be hand-edited.

### 3.3 `src/lib/knowledge.ts` (339 lines) — the vocabulary layer

The single place backend enum values become reader-facing English. Exports:

- `INTERNAL_GRAPH_TYPES` (`:8–22`) — 12 bookkeeping node types hidden from every graph view.
- `normalizeType` (`:24`), `isPublicGraphNode` (`:28`), `isRenderedAsDeity` (`:36`), `isNonDeityDevataSlot` (`:40`), `humanizePredicate` (`:44`), `titleCase` (`:49`).
- `StatusTone` union (`:53`) — `supported | partial | insufficient | not-built | unknown` — **the only thing that binds CSS `.tone-*` classes to data.**
- `statusCopy` (`:65–146`) — 12 named statuses + 2 fallbacks, each `{label, description, tone}`.
- `evidenceBasisCopy` (`:149+`), `trustTierCopy`, `attributionCopy`, `certaintyCopy`, `certaintyBand`, `conditionKindCopy`, `matchLevelCopy`, `relationKindCopy`, `entityTypeLabel`, `entityHref`, `defaultDeityTotal` (all asserted by `tests/unit/knowledge.test.ts`).

`entityHref` is the routing table: `DEVATA` → `/devatas/{id}`, `PASSAGE`/`MANTRA` → `/passage/{key}`, `RITUAL` → `/rituals/{id}`, `FORMULA_FAMILY` → `/formula-families/{id}`, everything else → `/entities/{type}/{id}` (pinned by `knowledge.test.ts:163–169`).

### 3.4 `src/lib/ask.ts` (337 lines) — hand-written Ask contract + vocabulary

Types `AskMode`, `AskVedaScope`, `SupportLevel`, `EvidenceItemType` (10 members), `AskRequest`, `AskCitation`, `AskEvidenceItem`, `AskEntityMention`, `AskRetrievalSummary`, `AskResponse`, `AskHealth`, `ApiErrorBody`; class `AskError` with `code`, `status`, `hint` and an `unavailable` getter keyed on `code === "ASK_UNAVAILABLE"` (`:127`).

`postAsk` (`:138–164`) — browser `fetch("/backend/ask", { method: "POST" })`. **No timeout and no default `AbortSignal`** — the bound is the Next rewrite's `proxyTimeout: 345_000` (`next.config.ts:21`) and whatever signal the caller supplies. Failure path parses a JSON error body defensively (`:154` `.catch(() => null)`), because a proxy can answer HTML.

`fetchAskHealth` (`:167–177`) — GET `/backend/ask/health`; **a 503 body is parsed, not thrown**, because readiness is itself the answer.

Constants: `ASK_QUESTION_LIMIT = 2000` (`:179`), `ASK_VEDA_SCOPES` (5), `ASK_MODES` (5), `ASK_EXAMPLES` (5). Vocabulary: `supportLevelCopy`, `EVIDENCE_TYPE_ORDER` (10, in reading order), `evidenceTypeCopy`, `matchRankCopy`, `channelLabel`, `formatMs`.

### 3.5 `src/lib/ask-citations.ts` (95 lines) — inline `[E1]` parser

Two regexes: `CITATION_GROUP = /\[([^[\]]{0,120}?)\]/g` (`:17`) and `ID_IN_GROUP = /\bE(\d+)\b/g` (`:20`). Exports `parseAnswerSegments`, `parseAnswer`, `extractCitedIds`. The header comment (`:1–14`) records that this deliberately mirrors `vedagraph.api.ask.citation.extract_cited_ids` two-stage-for-two-stage, so a grouped `[E6, E7, E8, E9]` the backend verified is not rendered as literal text. Pure functions, no I/O — and the only fully rebrand-safe module in the codebase.

### 3.6 Caching / revalidation strategy

| Path | Mechanism | Value |
| --- | --- | --- |
| Server components | `next: { revalidate }` in `apiGet` | **60 s** default (`api.ts:75`) |
| `/graph` | explicit override | **0** — always fresh (`graph/page.tsx:20`) |
| Client `/backend/*` fetches | none | browser default; **no `cache:` or `next:` option anywhere** |
| Search | in-memory `Map` keyed on the query string | `search-experience.tsx:73, 110` — per-mount, never evicted |
| Graph | in-memory `Map` of nodes/edges | `graph-explorer.tsx:55–67` (`ingest`) — accumulates, never evicted |

**Only two revalidation values exist: 60 and 0.** There is no per-resource policy — `/stats` and a passage's Sanskrit text are cached identically, though one changes per build and the other effectively never.

### 3.7 Complete list of backend endpoints the frontend calls

**Server-side, via `load<T>()` → `${VEDAGRAPH_API_URL}/api/v1<path>`:**

| # | Path | Response type | Called from |
| --- | --- | --- | --- |
| 1 | `/stats` | `Stats` | `page.tsx:79` |
| 2 | `/works` | `WorksResponse` | `page.tsx:80`, `vedas/page.tsx:28`, `vedas/[veda]/page.tsx:62` |
| 3 | `/works/{work_id}/root?limit=60` | `WorkRoot` | `vedas/[veda]/page.tsx:63` |
| 4 | `/works/{work_id}/audio?limit=1` | `WorkAudio` | `vedas/[veda]/page.tsx:86` |
| 5 | `/passages/{key}/reader` | `Reader` | `passage/[key]/page.tsx:32, 43`; `reuse/[key]/page.tsx:31, 52` |
| 6 | `/passages/{key}/parallels?limit=25` | `ParallelsResponse` | `passage/[key]/page.tsx:53` |
| 7 | `/passages/{key}/parallels?filter=cross_veda&limit=20` | `ParallelsResponse` | `reuse/[key]/page.tsx:32` |
| 8 | `/passages/{key}/audio` | `PassageAudio` | `passage/[key]/page.tsx:54` |
| 9 | `/search?q=&type=&limit=` | `SearchResponse` | `connections/page.tsx:24` |
| 10 | `/devatas?limit=60` / `?limit=8` | `DevatasResponse` | `devatas/page.tsx:16`; `vedas/[veda]/page.tsx:83` |
| 11 | `/devatas/{id}` | `DevataProfile` | `devatas/[id]/page.tsx:43, 54` |
| 12 | `/devatas/{id}/passages?basis=mention&limit=8` | `DevataPassagePage` | `devatas/[id]/page.tsx:67` |
| 13 | `/devatas/{id}/passages?basis=ascription&limit=8` | `DevataPassagePage` | `devatas/[id]/page.tsx:68` |
| 14 | `/entities` | `EntityInventory` | `entities/page.tsx:64` |
| 15 | `/entities/{type}?{query}` | `EntityListResponse` | `entities/[type]/page.tsx:46` |
| 16 | `/entities/formula_family?limit=60` | `EntityListResponse` | `formulas/page.tsx:16` |
| 17 | `/entities/{type}/{id}` | `EntityProfile` | `entities/[type]/[id]/page.tsx:25, 39` |
| 18 | `/rituals?limit=25` | `RitualsResponse` | `rituals/page.tsx:15` |
| 19 | `/rituals/{id}` | `RitualProfile` | `rituals/[id]/page.tsx:16, 27` |
| 20 | `/formula-families/{id}` | `FormulaFamily` | `formula-families/[id]/page.tsx:17, 25` |
| 21 | `/graph/neighborhood/{node_id}?depth=1&limit_per_type=3` | `GraphData` | `page.tsx:82` |
| 22 | `/graph/neighborhood/{node_id}?depth=1&limit_per_type=8` | `GraphData` | `graph/page.tsx:19` (`revalidate: 0`) |
| 23 | `/insights/cross-veda` | `CrossVeda` | `connections/page.tsx:33` |
| 24 | `/insights/formula-diffusion?limit=8` / `?limit=6` | `FormulaDiffusion` | `connections/page.tsx:34`; `formulas/page.tsx:17` |
| 25 | `/insights/devatas/{id}` | `DevataInsight` | `devatas/[id]/page.tsx:66` |
| 26 | `/insights/material-culture?category=&limit=40` | `MaterialCulture` | `material-culture/page.tsx:34` |
| 27 | `/insights/metals` | `Metals` | `material-culture/page.tsx:36` |
| 28 | `/insights/atharvaveda/concerns?limit=20` | `AvConcerns` | `explore/atharvaveda/page.tsx:66` |
| 29 | `/insights/civilization?limit=16` | `Civilization` | `insights/page.tsx:31` |
| 30 | `/insights/capabilities` | `Capabilities` | `limits/page.tsx:25` |

**Client-side, via the `/backend/:path*` rewrite → `${VEDAGRAPH_API_URL}/api/v1/:path*` (`next.config.ts:22–25`):**

| # | Request | Shape | Called from |
| --- | --- | --- | --- |
| 31 | `GET /backend/search?{q,limit,type,veda,language}` | `SearchResponse` | `search-experience.tsx:105` |
| 32 | `GET /backend/search?q=&limit=1` | `SearchResponse` | `graph-explorer.tsx:229` |
| 33 | `GET /backend/graph/neighborhood/{id}?depth&limit_per_type[&trust_tier]` | `GraphData` | `graph-explorer.tsx:106` |
| 34 | `GET /backend/graph/relationships/{id}` | `RelationshipExplanation` | `graph-explorer.tsx:205` |
| 35 | `GET /backend/passages/{key}/children?limit=60&offset=N` | `ChildrenResponse` (locally typed, `structure-browser.tsx:17–21`) | `structure-browser.tsx:39` |
| 36 | `POST /backend/ask` | `AskRequest` → `AskResponse` | `ask.ts:141` |
| 37 | `GET /backend/ask/health` | `AskHealth` | `ask.ts:169` |

**37 distinct call sites over 30 server-side and 7 client-side endpoint shapes.** The `api-schema.ts` `paths` interface exposes 43 paths, so the frontend exercises roughly 70 % of the API. Unused: `/health`, `/ready`, `/works/{work_id}`, `/passages/{key}`, `/passages/{key}/parent`, `/passages/{key}/siblings`, `/audio/stats`, `/audio/{id}`, `/audio/{id}/stream` (used indirectly as a media `src`), `/devatas/{id}/network`, `/formulas/{id}`, `/graph/path`, `/insights/rituals`.

**None of these 37 paths contains the string "vedagraph".** The rebrand touches only the `VEDAGRAPH_API_URL` env var name and the `/backend` proxy prefix — neither of which is brand-bearing in the URL itself.

---

## 4. Repeated UI idioms → design-system primitives

Ranked by evidence. "Occurrences" counts distinct call sites in `src/`.

| # | Idiom | Evidence | Proposed primitive |
| --- | --- | --- | --- |
| 1 | **Card** — 1px `--line` border + `--surface` fill + radius + optional accent hover | 73 `border: 1px solid var(--line)`, 65 `background: var(--surface)`, 84 `border-radius: var(--radius*)`, 36 accent hovers; ≥30 distinct selectors (`.veda-card`, `.panel`, `.lens-card`, `.limit-card`, `.gap-card`, `.entity-chip`, `.formula-chip`, `.reference-list a`, `.related-grid a`, `.type-grid a`, `.av-row`, `.ritual-grid a`, `.parallel-row`, `.result-row`, `.entity-index-row`, `.reuse-row`, `.graph-entry`, `.citation-list a`, `.evidence-triple`, `.evidence-passages a`, `.ask-evidence-item`, `.derived-metric`, `.insight-section`, `.census-grid article`, `.evidence-rows article`, `.data-row-grid article`, `.certainty-split > div`, `.collection-metrics div`, `.family-branches > div`, `.comparison`) | `<Card variant="raised\|sunk\|outline\|dashed" interactive?>` |
| 2 | **Eyebrow / SectionLabel** — uppercase micro-heading | **21 verbatim copies** (list in §1.6) + ~30 more `<span>`/`<dt>` variants | `<Eyebrow as="h2\|h3\|span" tone="faint\|accent">` |
| 3 | **Page heading + kicker + lede** | `PageHeading` in **20 routes / 39 refs**; plus 3 hand-rolled variants (`page.tsx:105–111` hero, `devatas/[id]:110–130`, `entities/[type]/[id]:205–225`) | extend `PageHeading` with `kicker`, `iast`, `actions`, `status` slots |
| 4 | **Caveat / callout** | `Caveat` in **22 files / 99 refs**; `CaveatList` 19/41; plus `.caveat-text` (evidence drawer ×2), `.ask-caveats`, `.transmission-note`, `.limit-alternative`, `.scope-warning`, `.measure-caveat`, `.panel-note`, `.ask-empty-note` | `<Callout tone="neutral\|boundary\|interpretive\|warning" collapsible?>` — one component, 8 CSS blocks retire |
| 5 | **Status badge** | `KnowledgeStatus` in **21 files / 72 refs**; plus `.ask-support` (4 tones), `.verdict` (2), `.condition-kind` (6), `.certainty-chip` (3), `.legend-chip` (11), `.parallel-kind`, `.tab-badge`, `.veda-chip`, `.result-type`, `.node-type`, `.crumb-level` | `<Badge tone shape>` + keep `KnowledgeStatus` as the *semantic* wrapper over it |
| 6 | **Section with heading + lede** | `.section-heading` 5 files / 14 refs; `.av-section-title`, `.insight-section header`, `.comparison-banner`, `.structure-top`, `.limit-card header`, `.gap-card header`, `.derived-metric header`, `.evidence-drawer header` — 9 more variants of "eyebrow + h2 + lede + right-aligned meta" | `<SectionHeader eyebrow title lede meta>` |
| 7 | **Card grid** | `.veda-grid`(4col), `.type-grid`(auto-fill 212), `.ritual-grid`(280), `.lens-grid`(auto-fit 300), `.av-rows`(300), `.evidence-rows`(280), `.census-grid`(180), `.derived-grid`(290), `.formula-chip-list`(260), `.family-branches`(260), `.related-grid`(200), `.data-row-grid`(240), `.passage-columns`(260), `.occurrence-columns`(220), `.seer-facts`(230), `.seer-associations`(220), `.profile-sections`(280), `.limit-body`(280), `.comparison-evidence dl`(230), `.evidence-summary dl`(240) — **20 grids, 13 distinct min-widths** | `<CardGrid min="sm\|md\|lg">` — 3 sizes, not 13 |
| 8 | **Entity chip / pill** | `.chip-row` 7 files / 9 refs; `.ask-entity`, `.axis-list span`, `.ranked-facts li`, `.legend-chip`, `.kind-tabs a`, `.filter-row button`, `.ask-chip-row button`, `.truncated-types li`, `.ask-unresolved li`, `.ask-tag-row span` — 11 pill families, all `border-radius: 999px` | `<Chip interactive? tone? count?>` |
| 9 | **Definition list / provenance block** | 11 `<dl>` call sites; CSS: `.provenance-list`(130px), `.evidence-metadata`(150px), `.evidence-technical div`(140px), `.interpretation-frame dl div`(160px), `.ritual-row`(170px), `.recitation-provenance dl`(9rem), `.derived-values`, `.ask-figures`, `.comparison-evidence dl`, `.evidence-summary dl`, `.lens-card dl` — **6 different label-column widths** | `<DescriptionList label-width="sm\|md">` + `<ProvenanceDisclosure>` |
| 10 | **Disclosure (`<details>`)** | 13 call sites; CSS: `.caveat.is-collapsible`, `.caveat-list`, `.witness-block`, `.provenance`, `.evidence-technical`, `.search-caveats`, `.graph-node-list`, `.ask-retrieval`, `.recitation-provenance`, `.derived-metric details`, `.comparison-evidence details` — **11 near-identical summary styles** | `<Disclosure summary count? tone?>` |
| 11 | **Evidence drawer** | **Two full implementations**: `evidence-drawer.tsx` (228 ln) and `ask/ask-evidence-drawer.tsx` (229 ln), sharing `.evidence-drawer` / `.evidence-content` / `.dialog-overlay` but duplicating header, close button, loading and empty states | `<Drawer side="right" title eyebrow>` shell + two content bodies |
| 12 | **Table** | 4 `<table>` — `.connection-matrix` (`connections:67`), `.material-table` (`material-culture:75`), `.limit-measurements` (`limits:83`), `.measure-table` (`measure.tsx:44`). Three distinct cell paddings (`12px 14px`, `9px 12px`, `6px 14px 6px 0`), two scroll strategies (`.matrix-wrap` shadows vs `display:block; overflow-x:auto`) | `<DataTable>` + `<ScrollShadow>` |
| 13 | **Metric strip / figure** | `.metric-strip`(4), `.collection-metrics`(3), `.certainty-split`(3), `.formula-stats`(flex), `.census-grid`, `.data-row-grid`, `.derived-headline` — 7 ways to show "big number + label + caveat" | `<MetricStrip>` / `<Metric value label note>` |
| 14 | **Empty state** | `empty-state.tsx` exports 5 variants used in **22 files / 54 refs** — already a primitive, just needs a token-driven skin |
| 15 | **Measure wrapper (`--measure: 68ch`)** | 10 CSS uses + 6 hand-written char widths: `52ch` (`.site-footer p`), `46ch` (`.hero-lede`, `.graph-bounds`), `54ch` (`.empty-state p`), `62ch` (`.knowledge-status`, `.profile-hero p`, `.connections-explainer p`), `66ch` (`.reading-column`), `72ch` (`.entity-index-row p`), `84ch` (`.caveat`), `40ch` (`.reader-edge`), `30ch` (`.ask-mode-note`), `20ch` (`.evidence-pitch h2`) — **11 distinct measures** | `<Prose measure="tight\|default\|wide">` on a 3-step scale |
| 16 | **Tabs** | `tabs.tsx`, **1 consumer**. `.kind-tabs` (`entities/[type]:71`, `material-culture:56`) is a second, link-based tab idiom with its own CSS | unify into `<Tabs>` with `as="button" \| "link"` |
| 17 | **Breadcrumb** | `.reader-breadcrumbs` — **1 call site** (`passage/[key]`). `.back-link` (3 call sites) is the degenerate form | `<Breadcrumbs>` + keep `backHref` on `PageHeading` |
| 18 | **Sanskrit text block** | `.sanskrit` in 7 files / 14 refs, always with `lang="sa"`; `.devanagari` modifier; `.sanskrit` re-skinned inside `.ask-evidence-item` (`globals.css:5999`) | `<Sanskrit script="iast\|devanagari" size="reader\|inline">` |
| 19 | **Audio player** | `recitation-player.tsx`, 1 consumer, 14 CSS classes, 193 CSS lines | keep as a single component; extract `<Transport>` if a second player appears |
| 20 | **Sticky aside** | `.reader-aside` and `.sticky-aside` — **two names, identical rules** (`position:sticky; top:92px; flex column`), `1482` vs `1839` | one `<StickyRail>` |
| 21 | **Skeleton** | `.skeleton` used at `loading.tsx:4–6`, `ask-experience.tsx:364–366`, `evidence-drawer.tsx:57–59`, `search-experience.tsx:311–314` — always with inline `style={{width,height}}` (16 inline styles total) | `<Skeleton w h>` |

**The 21 idioms above account for the overwhelming majority of the 6,407 lines.** A primitive set of roughly 18 components plus a token file should replace ~4,000 of them.

---

## 5. Accessibility audit (static)

**Inventory.** 100 `aria-hidden`, 35 `aria-label`, 6 `aria-describedby`, 3 `aria-labelledby`, 3 `aria-current`, 2 `aria-pressed`, 2 `aria-live`, 1 each `aria-valuetext` / `aria-invalid` / `aria-expanded` / `aria-busy`. Roles: `status` ×6, `alert` ×6, `search` ×1, `presentation` ×1, `img` ×1, `group` ×1. `tabIndex` ×1. **Zero `<img>` elements and no `next/image`** — all imagery is inline SVG icons (Phosphor) or the brand mark, so there is no alt-text surface at all.

### 5.1 What is right

| Item | Evidence |
| --- | --- |
| Skip link, first in `<body>`, focus-revealed | `layout.tsx:32–34`; `globals.css:204–219` (`transform: translateY(-160%)` → `0` on `:focus`) |
| `<main id="main">` landmark | `layout.tsx:36` |
| `<header>`/`<footer>`/`<nav>` landmarks, all `nav`s labelled | `site-header.tsx:9`, `layout.tsx:37, 47`, `nav-links.tsx:10` (`aria-label="Primary"`), `mobile-nav.tsx:29` (`"Mobile"`), `entities/[type]:71` (`"Condition kind"`), `material-culture:56` (`"Material category"`) |
| Global `:focus-visible` ring | `globals.css:151–155` — `outline: 2px solid var(--accent); outline-offset: 3px` |
| Every icon is `aria-hidden` | 100 occurrences; icons never carry meaning alone |
| `lang="sa"` on every Sanskrit run | 17 sites incl. `passage/[key]:113, 153`, `parallel-comparison:45, 133`, `ask-evidence-drawer:166`, `evidence-drawer:136` |
| Charts are real tables with `<caption class="sr-only">` and `th[scope=row]` | `measure.tsx:44–51` |
| Bars are `aria-hidden`, values are text | `measure.tsx:64` |
| Graph canvas has a role and a stated text alternative | `graph-canvas.tsx:376–380` — `role="img"` + aria-label naming node/deity/edge counts and pointing at the node list |
| Node list is the keyboard path into the graph | `graph-explorer.tsx:539–551` (`<details>` + buttons) |
| Edges are keyboard-reachable once a node is selected | `graph-explorer.tsx:481–504` (`.selected-relationships` buttons call `explain(edge)`) |
| Live regions for async state | `search-experience.tsx:209` (`.sr-only` `role="status"`), `ask-experience.tsx:279` (`aria-live="polite"` counter), `:341` (`role="status" aria-live="polite"` pending) |
| `role="alert"` on genuine errors only | `error.tsx:11`, `empty-state.tsx:11, 28`, `search-experience.tsx:218`, `graph-explorer.tsx:375`, `ask-experience.tsx:371` |
| Audio controls fully named | `recitation-player.tsx:138–143` (`aria-label` naming the track + `aria-describedby` the scope note), `:161–162` (`aria-label` + `aria-valuetext`), `:177` (`.sr-only` "Playback speed") |
| Touch targets explicitly forced where they were failing | `globals.css:1782–1783` (`.tree-row button` 44×44), `1794–1797` (`.tree-row a` min-height 44), `2733–2737` (`.graph-toolbar form` min-height 44, with a comment recording the 23.5px measurement), `6236–6238` (`.recitation-play` 44×44), `6252` (`.recitation-seek` height 44), `6266` (`.recitation-speed select` min-height 44) |
| `aria-pressed` for toggle semantics | `graph-explorer.tsx:364` (legend), `search-experience.tsx:174` (type filters) |
| `aria-current="page"` for nav state | `nav-links.tsx:17`; CSS `globals.css:387`, `2352` |
| Colour is never the only signal | `status.tsx:31–32` emit `data-status`/`data-tone`; `GROUP_STYLE` gives every graph group a distinct **shape** as well as a colour (`graph-canvas.tsx:90–133`), and `.legend-chip i[data-shape=…]` renders it (`globals.css:2822–2846`) |

### 5.2 Defects

| # | Severity | Defect | Evidence |
| --- | --- | --- | --- |
| A1 | **High** | **Dangling `aria-describedby`.** `evidence-drawer.tsx:44` sets `aria-describedby="evidence-why"`, but `<p id="evidence-why">` is rendered only in the `!loading && data` branch (`:98`). While loading, and when `data` is null, the dialog points at a non-existent id. | `evidence-drawer.tsx:44` vs `:55–70` vs `:98` |
| A2 | **High** | **The `/` shortcut is advertised globally and implemented on one route.** `site-header.tsx:33` renders `<kbd>/</kbd>` in the header on every page; the handler exists only in `search-experience.tsx:78–88`, which mounts only on `/search` (`search/page.tsx:22`). On 24 of 25 routes the hint is false. | `site-header.tsx:33`; `search-experience.tsx:78–88` |
| A3 | **Medium** | **The `/` handler does not exclude `contentEditable` or open dialogs.** It checks only `tagName !== "INPUT" && !== "TEXTAREA"` (`:81`). With the mobile nav or an evidence drawer open, pressing `/` calls `inputRef.current?.focus()` on an element outside the Radix focus trap; Radix pulls focus back, producing a focus fight. | `search-experience.tsx:79–85` |
| A4 | **Medium** | **Sub-24px touch targets** (WCAG 2.5.8 AA). `.ask-cite` — `padding: 0 6px`, `font-size: .68rem`, `line-height: 1.5` ⇒ **≈16px** tall (`globals.css:5641–5661`). `.ask-clear` — `padding: 2px 8px`, `font-size: .72rem` ⇒ **≈22px** (`globals.css:5364–5373`). `.ask-cite` may claim the inline-in-a-sentence exception; `.ask-clear` is a standalone button and does not. | `globals.css:5641`, `5364`; rendered at `ask-answer.tsx:88`, `ask-experience.tsx:303–311` |
| A5 | **Low** | **`.icon-button` is 36×36** — clears 2.5.8 (24px) but fails 2.5.5 AAA (44px). Used for the mobile-nav trigger, theme toggle, drawer close and two graph controls. | `globals.css:262–272` |
| A6 | **Medium** | **`prefers-reduced-motion` is breached by three JS animations** (§1.12): `ask-experience.tsx:127` and `ask-evidence-drawer.tsx:70` pass `behavior: "smooth"` explicitly, which CSS `scroll-behavior: auto !important` cannot override; `graph-canvas.tsx:361` animates a 320 ms camera fit unguarded. Only `graph-canvas.tsx:344–346` checks the media query. | as listed |
| A7 | **Medium** | **The `:focus-visible` rule sets `border-radius: 4px` on the focused element itself** (`globals.css:154`), not just the outline. Today every pill/card class (`.button` 222, `.icon-button` 262, `.chip-row a` 305 …) is declared *after* line 151 and wins on source order, so nothing breaks — but this is an **order-dependent accident**. Moving the focus rule later, or adding a radius rule before it, silently squares off every focused pill. | `globals.css:151–155` |
| A8 | **Medium** | **`MobileNav` has a `Dialog.Title` but no `Dialog.Description` and no `aria-describedby`** — Radix logs a console warning and screen readers get no description. | `mobile-nav.tsx:22–28` |
| A9 | **Low** | **The passage tree is not a tree widget.** `structure-browser.tsx:65` renders `<li class="tree-row">` with nested `<ul>`, using `aria-expanded` on a button but no `role="tree"`/`treeitem"`, no roving tabindex, no arrow-key navigation. Every row is a separate tab stop; a 60-child mandala is 120 tab stops. Not a trap, but very slow. | `structure-browser.tsx:64–135` |
| A10 | **Low** | **`.legend-chip[aria-pressed="false"]` conveys "hidden" with `opacity: .42` + `line-through`** (`globals.css:2794–2797`). `aria-pressed` carries it for AT, and `line-through` is non-colour, so this passes — but at 0.42 opacity on `--surface` the text drops well below 4.5:1 for sighted users. | `globals.css:2794` |
| A11 | **Low** | **Heading order.** All 25 routes have exactly one `<h1>` (asserted by `journeys.spec.ts:444–455` for 7 of them, `audio-a11y.spec.ts:62` for the reader). Two routes reach `<h3>` before any `<h2>` in *source* order but not in *DOM* order: `vedas/[veda]/page.tsx` places `.content-grid > div` (containing `StructureBrowser`'s `<h2>` at `structure-browser.tsx:149`) before `<aside class="sticky-aside">` (whose `.panel h3`s are at `:129, :144, :159`), so the rendered order is h1→h2→h3. Correct, but only by layout accident — a column reorder would break it. | `vedas/[veda]/page.tsx:98–178` |
| A12 | **Low** | **`.ask-retrieval-block h4`** (`ask-answer.tsx:199, 212, 225, 249, 275`) sits inside a `<details>` whose `<summary>` is not a heading, so the h4s are orphaned two levels below the `<h2 id="ask-answer-heading">` at `:47` with no h3 between. | `ask-answer.tsx:191–296` |
| A13 | **Low** | **`role="img"` on a live-updating Cytoscape container.** `graph-canvas.tsx:376` gives the div `role="img"` with a count-bearing label. Because the label changes as the user expands the graph, but the element is not a live region, AT users get a stale description until they re-navigate to it. | `graph-canvas.tsx:376–380` |
| A14 | **Info** | **`.dialog-overlay` scrim is not theme-aware** — `rgb(12 18 20 / 0.42)` (`globals.css:3157`) is the same in dark mode, where it barely darkens an already-dark page, weakening the modal signal. | `globals.css:3157` |
| A15 | **Info** | **No keyboard trap exists.** All three Radix Dialogs (`mobile-nav`, `evidence-drawer`, `ask-evidence-drawer`) use `Dialog.Portal` + `Dialog.Content` and inherit Radix's focus trap, Escape handling and focus restore. `ask-evidence-drawer.tsx:60–74` deliberately waits a frame so its `scrollIntoView` + `focus({preventScroll:true})` beats Radix's own autofocus — a correct and well-commented interaction. The `<li tabIndex={-1}>` at `:151` is the only programmatic focus target and is not in the tab order. **Verified clean.** |
| A16 | **Info** | **Contrast is machine-checked in CI.** `tests/e2e/release-closure.spec.ts:89–135` walks every element under `<main>`, resolves the nearest opaque painted ancestor, and requires 4.5:1 (3:1 for large text) in **both themes** at three viewports; `:143–196` additionally injects all 8 graph-legend groups and requires ≥4.495:1. This is a genuinely strong guard and **must be preserved through the rebrand**. |

---

## 6. Theme implementation

### 6.1 Wiring

| Layer | File:line | Detail |
| --- | --- | --- |
| Provider | `src/components/theme-provider.tsx:7–12` | `<NextThemesProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>` |
| Mount point | `src/app/layout.tsx:31` | wraps the skip link, header, `<main>{children}</main>` and footer — i.e. **the first element inside `<body>`** |
| Hydration guard | `src/app/layout.tsx:27` | `suppressHydrationWarning` on `<html>` |
| Toggle | `src/components/theme-toggle.tsx:11–23` | `useTheme()`; `onClick` → `setTheme(resolvedTheme === "dark" ? "light" : "dark")` |
| Icon strategy | `theme-toggle.tsx:20–21` + `globals.css:423–434` | **both** icons always rendered; CSS shows one — `.theme-toggle .theme-icon-dark { display: none }` / `.dark .theme-toggle .theme-icon-light { display: none }` |
| Token switch | `globals.css:39–65` | `.dark { … }` redefines 29 properties |
| Graph theming | `graph-canvas.tsx:135–139`, `home-network.tsx:15`, `graph-explorer.tsx:386` | `dark={resolvedTheme === "dark"}` prop → `buildStyle(dark, compact)` re-runs on change (`graph-canvas.tsx:302–304`) |
| Test contract | `tests/e2e/release-closure.spec.ts:79–82` | `document.documentElement.classList.toggle("dark", d)` — the `dark` class name is a **hard test contract** |
| Test mock | `tests/setup.ts:26–29` | `next-themes` mocked with `resolvedTheme: "light"` |

### 6.2 FOUC

`next-themes` 0.4.6 renders a memoised `<script suppressHydrationWarning dangerouslySetInnerHTML>` (verified in `node_modules/next-themes/dist/index.mjs`) that reads `localStorage`, resolves `system` against `matchMedia`, and writes the class onto `document.documentElement` **synchronously**.

Because `ThemeProvider` is the outermost child of `<body>` (`layout.tsx:30–31`), that inline script is the **first node in `<body>`** and executes before any visible content is parsed. In practice **there is no FOUC**: the `.dark` class lands on `<html>` before the first paint.

Two caveats worth recording:

1. **The guard is one position later than ideal.** A `<head>`-level script would be unambiguously before any layout. Today it depends on the provider remaining the first child of `<body>` — a refactor that moves the provider below the header re-introduces a flash.
2. **`resolvedTheme` is `undefined` on the first client render.** `theme-toggle.tsx:17` evaluates `resolvedTheme === "dark" ? "light" : "dark"` — a click before `useTheme` resolves sets `"dark"` regardless of the current theme. Narrow window, real bug.

The `theme-icon-light` / `theme-icon-dark` CSS-swap strategy (documented at `theme-toggle.tsx:6–10`) is a good pattern: it avoids the usual `mounted` flag and keeps the first paint stable. Keep it.

### 6.3 Is dark mode *designed* or inverted?

**Designed.** Evidence:

- All 29 tokens get individually chosen dark values, not algorithmic inversions. `--bg` goes `#f4f5f2` → `#10161a` (a blue-black, not the inverse of a green-white); `--accent` goes `#b04728` → `#e58163` (**lightened and desaturated**, the correct move for a warm accent on dark, not inverted to a cyan).
- Tone backgrounds are *darkened tints of the tone hue*, not inverted: `--tone-supported-bg` `#e4efe9` → `#1a2c26`.
- **A second, dark-only colour table exists for the graph legend** (`globals.css:2888–2911`) with six hand-picked hues, because the light values were darkened for contrast on `--surface` and the same trick does not work in reverse.
- `GROUP_STYLE` carries an explicit `light`/`dark` pair per group (`graph-canvas.tsx:90–133`), and `buildStyle` (`:135–139`) swaps `ink`/`halo`/`line`/`accent` too.
- Contrast is verified in **both** themes by `release-closure.spec.ts:64–67`.

**Weaknesses.** (a) `.dialog-overlay` is not themed (§5, A14). (b) `.matrix-wrap` scroll shadows use `rgb(0 0 0 / .09)` (`globals.css:4956–4957`) — invisible on a dark surface. (c) `--shadow` dark is `rgb(0 0 0 / .75)` at 52px blur, which on a near-black background reads as nothing; dark elevation should come from a lighter surface, not a darker shadow. (d) There is **no** `color-scheme` declaration in `globals.css`; `next-themes` sets it on `documentElement.style` via `enableColorScheme` (default true), so native form controls and scrollbars do follow — but it is invisible to a CSS reader.

---

## 7. Tests — what breaks when we rename, restructure, and re-word

**Totals:** 46 `describe`s, 135 `test`/`it` statements, **148 runtime cases** (one `it.each` ×6, one `for`-generated ×3 viewports). Vitest: 68 cases. Playwright: 80 cases.

**The central fact: there is not one `data-testid` in the repository.** 61 distinct literal CSS class selectors and ~185 literal user-facing copy strings carry the suite. The only rebrand-safe hooks that exist today are four data attributes: `data-status` / `data-tone` (`status.tsx:31–32`), `data-knowledge-kind` (`status.tsx:117`, `ask-answer.tsx:57`), `data-certainty` (asserted at `passage-knowledge.test.tsx:33–34`), plus `data-evidence-id` / `data-cited` (`ask-evidence-drawer.tsx:150, 152`) and `data-shape` / `data-state` on chips and tabs.

### 7.1 Per-file inventory

| File | Cases | What it covers |
| --- | --- | --- |
| `tests/component/knowledge-ui.test.tsx` | 12 | `KnowledgeStatus` data attributes + copy; `Caveat` open/collapsed; `InterpretationFrame` `data-knowledge-kind`; `MeasureChart` scope copy, null-not-zero, **exactly one `.measure-bar`**, table roles; `SeerPanel` missing-family / non-seer / never-summed |
| `tests/component/passage-knowledge.test.tsx` | 11 | 4 tab names; `[data-certainty]` ambiguous vs certain; inherited vs stated attribution; phenomenon/deity separation via `.closest("a")`; shared-wording vs shared-vocabulary via `h2` + `parentElement`; unbuilt audio; evidence drawer plain-language-first; **`TIER_B` must live only inside `details.evidence-technical`** (direct-child combinator); no-passage-attached; no-review; null-explanation |
| `tests/unit/ask-citations.test.ts` | 14 | pure parser: single/grouped/semicolon/"and"/adjacent markers, bracketed prose, embedded capital-E words, dedup, paragraph split, empty answer, `extractCitedIds` order and agreement |
| `tests/unit/graph-semantics.test.ts` | 6 | deity vs unresolved-devata; no human in the deity group; every group has a distinct shape and `light !== dark`; reified records never drawn as subject matter (+ legend copy `"Evidence record"`); derived (+ `"Derived metric"`); 12 entity types never fall to `"other"` |
| `tests/unit/knowledge.test.ts` | 25 | **the canonical copy-lock** — exact wording of every status, tier, basis, attribution, condition-kind, match-level and relation-kind label; `defaultDeityTotal === 1708`; `entityHref` routing table; internal-node hiding |
| `tests/e2e/journeys.spec.ts` | 35 | 10 named journeys + 4 knowledge-status regressions + 3 seer/entity + 4 a11y + 4 search-behaviour |
| `tests/e2e/mobile.spec.ts` | 8 | Pixel 7 only: reader, tabs, deity charts, nav drawer, graph, search, recitation at 390px, absent recitation |
| `tests/e2e/audio.spec.ts` | 14 | live-catalog recitation copy, play/seek/speed naming, provenance, Valakhilya boundary, absent-is-not-error, Veda coverage figures |
| `tests/e2e/audio-a11y.spec.ts` | 7 | every control named, `role="region"`, non-colour state, no media focus trap, visible focus ring, keyboard disclosure, one h1 |
| `tests/e2e/release-closure.spec.ts` | 14 | ×3 viewports: 44px hierarchy controls, Ask mode description, shared badge typography, audio targets + **full-page contrast in both themes**; ×1: all 8 legend groups AA; ×1: 99.5 % not rounded to 100 % |
| `tests/e2e/ask-live.spec.ts` | 1 | **skipped unless `ASK_LIVE=1`** — full Ask journey against a live LLM |
| `tests/e2e/ask-live-mobile.spec.ts` | 1 | **skipped unless `ASK_LIVE=1`** — same at 390px |
| `tests/visual-qa.mjs` | 0 | script: 24 surfaces × 3 viewports = 72 screenshots + overflow report; **always exits 0** |

### 7.2 The riskiest tests, ranked

**Tier 1 — will break on the brand rename alone (5 assertions).**

| File:line | Assertion |
| --- | --- |
| `tests/e2e/journeys.spec.ts:325` | `getByRole("link", { name: "VedaGraph, home" })` ← `site-header.tsx:11` |
| `tests/e2e/ask-live.spec.ts:29` | `getByRole("heading", { name: "Ask VedaGraph", level: 1 })` |
| `tests/e2e/ask-live.spec.ts:37` | `getByRole("button", { name: "Ask VedaGraph" })` |
| `tests/e2e/ask-live-mobile.spec.ts:22` | heading `"Ask VedaGraph"` |
| `tests/e2e/ask-live-mobile.spec.ts:36` | button `"Ask VedaGraph"` |

Plus `playwright.config.ts:50, 57` pass `VEDAGRAPH_API_URL` — **must not be renamed.**

**Tier 2 — the `VG:` identifier prefix (~45 literals).** `VG` is the VedaGraph abbreviation and is embedded in every canonical key the tests navigate to: `journeys.spec.ts:4–10, 77, 117, 389`; `mobile.spec.ts:3–4, 117`; `audio.spec.ts:13, 17, 19, 21`; `release-closure.spec.ts:3`; `unit/knowledge.test.ts:163–169`; `fixtures/reader.ts` ×16; `visual-qa.mjs:35, 37–43, 47`. **This is a graph-data identifier, not a product name. Do not rename it** — but record the decision explicitly, because it is the most tempting and most destructive thing to "fix" during a rebrand.

**Tier 3 — the class-rename blast radius.** 27 of 35 `journeys` cases, all 8 `mobile` cases, 9 of 14 `audio` cases, 4 of 7 `audio-a11y` cases, both `ask-live` cases, and 3 of the `release-closure` bodies are class-coupled. The 61 selectors:

`.knowledge-status` · `details.caveat` · `.measure-bar` · `details.evidence-technical` · `.evidence-content` · `.search-results` · `.sanskrit` · `.result-row` · `.result-type` · `.citation-list` · `.graph-canvas` · `.graph-legend` · `.legend-chip` · `group-deity…group-other` (8) · `.graph-node-list` · `.selected-relationships` · `.node-type` · `.graph-bounds` · `.av-block` · `.av-row` · `.condition-kind` · `.entity-index-row` · `.formula-list` · `.occurrence-columns` · `a.reuse-row` · `.comparison` · `.comparison-column` · `svg.notation` · `.musical-notation` · `.ritual-grid` · `.citation-rail` · `.limit-card` · `.verdict` · `.cell-reason` · `.gap-card` · `.empty-state` · `.search-error` · `figure.measure` · `.certainty-split` · `.is-ambiguous` · `.measure-null` · `.sticky-aside` · `.search-prompts` · `section.recitation` · `.recitation-media` · `.recitation-play` · `.recitation-seek` · `.recitation-speed` · `.panel` · `.formula-stats` · `.dark` · `.ask-pending` · `.ask-answer` · `.ask-prose` · `.ask-badges` · `button.ask-cite` · `.evidence-drawer` · `.ask-answer-actions` · `.ask-related`.

Non-class structural pins: `#main` (`journeys:432`), `#ask-mode-note` (`release-closure:33`), `main` (`release-closure:113`), `body *` (`visual-qa:58`), `h1` (`journeys:439, 455`), `option:checked` (`release-closure:28`), `tbody tr` (`journeys:393`), `h3` (`journeys:237`), `h2` (`passage-knowledge:71`).

**Tier 4 — silent-pass hazards (worse than breakage).** Six *negative* assertions pass vacuously after a rename, so coverage disappears without a red test:

| File:line | Assertion | Failure mode |
| --- | --- | --- |
| `journeys.spec.ts:263` | `svg.notation, .musical-notation` → count 0 | classes don't exist at all; guard is already inert |
| `journeys.spec.ts:320` | `getByText(/Insufficient evidence/i)` → count 0 | copy change makes it vacuous |
| `journeys.spec.ts:471` | `.search-error` → count 0 | class rename makes it vacuous |
| `mobile.spec.ts:119` | `section.recitation` → count 0 | class rename |
| `audio.spec.ts:118, 126` | `section.recitation` → count 0 | class rename |
| `audio.spec.ts:128` | button `/^Play /` → count 0 | copy change |

**Tier 5 — a test that can never fail.** `journeys.spec.ts:359` asserts `toContainText(/Certain and probable mentions are included|/)`. **The trailing empty alternative makes the regex match the empty string.** This assertion is dead today and should be fixed independently of the rebrand.

**Tier 6 — DOM-restructure pins.** The most brittle:

| File:line | Pin |
| --- | --- |
| `knowledge-ui.test.tsx:101` | **exactly one** `.measure-bar` in the whole container |
| `passage-knowledge.test.tsx:116` | `.evidence-content > *:not(.evidence-technical)` — direct-child combinator across two classes |
| `passage-knowledge.test.tsx:70–72` | `getByText("Shared vocabulary", {selector:"h2"}).parentElement` — heading tag **and** parent |
| `passage-knowledge.test.tsx:60` | `.closest("a")` — the label must be inside an anchor |
| `journeys.spec.ts:251–253` | `.comparison-column` `toHaveCount(2)` — exact sibling count |
| `journeys.spec.ts:393` | `figure.measure tbody tr` — table markup required |
| `journeys.spec.ts:408` | `.sticky-aside > *` direct children |
| `journeys.spec.ts:455` | `h1` count **exactly 1** on 7 routes |
| `audio.spec.ts:93–100` | **vertical order**: `.sanskrit`.y < `section.recitation`.y |
| `audio-a11y.spec.ts:11` | control count **> 3** inside `section.recitation` |
| `release-closure.spec.ts:28` | `mode.locator("option:checked")` — native `<select>` required |
| `release-closure.spec.ts:161–167` | injects synthetic children into `.graph-legend` |

**Tier 7 — copy locks.** `tests/unit/knowledge.test.ts` is 17 `it`s of exact reader-facing wording; `tests/component/*` is ~60 more; `journeys.spec.ts` alone asserts ~95 literal strings. Effectively **every e2e test except the pure-overflow probes is copy-coupled.**

**Tier 8 — hard-coded corpus figures that drift with the data build, not the code:** `audio.spec.ts:138` `/of 10,552 verses/`; `release-closure.spec.ts:204` `"10,502 translated (99.5%)"`; `knowledge.test.ts:92` `defaultDeityTotal === 1708`.

### 7.3 What is safe

| Safe | Why |
| --- | --- |
| `tests/unit/ask-citations.test.ts` — all 14 | pure string parsing, zero product coupling |
| `tests/unit/graph-semantics.test.ts` — 4 of 6 | pure grouping logic (`:5, :11, :19, :44`); `:31` and `:39` assert legend copy |
| `tests/unit/knowledge.test.ts` — 6 of 20 | `:44, :64, :71, :79, :85, :90` are logic-only |
| `tests/setup.ts` | module mocks only |
| `vitest.config.ts` | no coupling |
| The overflow probes | `mobile.spec.ts:14–17, 38–41, 69–72, 82–85, 97–100`; `ask-live-mobile.spec.ts:24–29`; `release-closure.spec.ts:19–21, 35` — pure `scrollWidth − clientWidth` |
| The contrast engine | `release-closure.spec.ts:89–135, 169–195` — pure computed-style maths (though its *selectors* are class-coupled) |
| `[data-status]`, `[data-tone]`, `[data-knowledge-kind]`, `[data-certainty]` assertions | the only rebrand-safe hooks that exist |

### 7.4 Live dependencies

All 80 Playwright cases need **two** running Next production servers (`playwright.config.ts:44–59`: `pnpm start` on `PORT` and `PORT+1`, the second pointed at dead port 9 so the offline journey exercises the real server-rendered failure path). The following additionally need a live, populated FastAPI backend: `journeys.spec.ts:75–87` (in-page `fetch` to `/backend/graph/*`), every hard-coded corpus figure, and the specific records `VG:DEVATA:ASAMATIH`, `VG:RV:SAK:M08:S071:V001`, `VG:RV:SAK:M08:S049:V001`, `VG:SV:KAU:ARANYA:D01:V01`. `audio.spec.ts` asserts the third-party source name `"VedSearch"` at `:75, :156` and `audio-a11y.spec.ts:59` — deliberately, per the header comment at `audio.spec.ts:3–11`. Only `ask-live*.spec.ts` spends LLM quota, and both are gated behind `ASK_LIVE=1`.

### 7.5 Recommendation before any rename lands

1. **Add `data-component` / `data-part` attributes to every primitive as it is built**, and migrate the 61 class selectors to them *before* renaming any class. This is the single highest-value pre-rebrand task.
2. **Fix `journeys.spec.ts:359`** (the vacuous regex) and delete `journeys.spec.ts:263` (asserts the absence of classes that never existed).
3. **Convert the six negative assertions** (Tier 4) to positive ones, or pair each with a positive control, so a rename fails loudly.
4. **Extract the ~185 copy literals into a shared `tests/copy.ts`** so a wording change is a one-file edit.
5. **Give `visual-qa.mjs` an exit code** so the overflow report can gate the rebuild.
6. **Record explicitly that `VG:` and `VEDAGRAPH_API_URL` are out of scope for the rename.**

---

## 8. Every occurrence of "VedaGraph" / "vedagraph" in `frontend/`

44 occurrences across 20 files (excluding `node_modules`, `.next`, `test-results`, `.tmp`, `pnpm-lock.yaml`, `tsconfig.tsbuildinfo`).

### 8.1 User-facing copy — **RENAME** (12)

| File:line | Text | Surface |
| --- | --- | --- |
| `src/components/site-header.tsx:11` | `aria-label="VedaGraph, home"` | brand link accessible name — **asserted by `journeys.spec.ts:325`** |
| `src/components/site-header.tsx:26` | `<span>VedaGraph</span>` | visible wordmark in the header |
| `src/app/layout.tsx:40` | `<span className="footer-brand">VedaGraph</span>` | footer wordmark |
| `src/components/mobile-nav.tsx:24` | `<Dialog.Title>Explore VedaGraph</Dialog.Title>` | mobile drawer title |
| `src/app/ask/page.tsx:27` | `title="Ask VedaGraph"` | `/ask` `<h1>` — **asserted by `ask-live.spec.ts:29`, `ask-live-mobile.spec.ts:22`** |
| `src/app/ask/page.tsx:22` | `` `What does VedaGraph record about ${entity}?` `` | seeded question text in the composer |
| `src/components/ask/ask-experience.tsx:292` | `{pending ? "Asking…" : "Ask VedaGraph"}` | submit button — **asserted by `ask-live.spec.ts:37`, `ask-live-mobile.spec.ts:36`** |
| `src/components/ask/ask-answer.tsx:108` | `Retrieved from the VedaGraph graph, synthesised by …` | provenance line under the answer |
| `src/components/ask/ask-answer.tsx:156` | `<b>Not found in VedaGraph.</b>` | unresolved-entities note |
| `src/components/empty-state.tsx:6` | `"The interface is ready, but the VedaGraph knowledge service did not respond."` | `ServiceUnavailable` default message |
| `src/lib/api.ts:61` | `const UNAVAILABLE = "The VedaGraph knowledge service did not respond."` | server-fetch failure copy |
| `src/lib/ask.ts:132` | `const UNREACHABLE = "The VedaGraph knowledge service could not be reached."` | Ask network-failure copy |

### 8.2 Metadata / SEO — **RENAME** (2, but 3 strings)

| File:line | Value |
| --- | --- |
| `src/app/layout.tsx:18` | `title: { default: "VedaGraph — a digital atlas of the Vedas", template: "%s \| VedaGraph" }` — **two** brand strings; **no test asserts either**, so this will rename silently |
| `src/app/ask/page.tsx:5` | `title: "Ask VedaGraph"` — route metadata |

### 8.3 Test assertions — **UPDATE WITH THE COPY** (5)

`tests/e2e/journeys.spec.ts:325` · `tests/e2e/ask-live.spec.ts:29, 37` · `tests/e2e/ask-live-mobile.spec.ts:22, 36`. Detail in §7.2 Tier 1.

### 8.4 Environment variable names — **DO NOT RENAME** (6 sites, 1 name)

| File:line | Occurrence |
| --- | --- |
| `.env.example:3` | `VEDAGRAPH_API_URL=http://127.0.0.1:8000` |
| `next.config.ts:23` | `process.env.VEDAGRAPH_API_URL ?? "http://127.0.0.1:8000"` |
| `src/lib/api.ts:58` | `process.env.VEDAGRAPH_API_URL ?? "http://127.0.0.1:8000"` |
| `playwright.config.ts:50` | `env: { VEDAGRAPH_API_URL: … }` |
| `playwright.config.ts:57` | `env: { VEDAGRAPH_API_URL: "http://127.0.0.1:9" }` |
| `README.md:30` | prose describing `VEDAGRAPH_API_URL` |

Plus two backend env vars named only in a comment: `next.config.ts:12–13` — `VEDAGRAPH_LLM_TIMEOUT_SECONDS`, `VEDAGRAPH_LLM_MAX_RETRIES`. **These belong to the Python service. Renaming them here breaks deployment and the Playwright harness.**

### 8.5 API paths — **NONE**

**No API path contains the brand string.** Server calls go to `${VEDAGRAPH_API_URL}/api/v1/...`; client calls go to `/backend/...`. The brand appears only in the *env var name*, never in a URL. §3.7 lists all 37 call sites; none is affected.

### 8.6 Code identifiers — **NONE**

There is no `VedaGraph`-named class, function, type, component, file or directory in `src/`. The only brand-derived *identifier* is the **`VG:` canonical-key prefix** (e.g. `VG:DEVATA:INDRAH`), which is graph data owned by the backend. In `frontend/` it appears in `src/app/page.tsx:40, 46, 58, 82`, `src/lib/api.ts:132–135`, and ~45 places in `tests/`. **Out of scope for the rename.**

### 8.7 Comments and generated prose — **LEAVE OR UPDATE FREELY**

| File:line | Nature |
| --- | --- |
| `src/app/globals.css:4` | `VedaGraph design system` — banner comment |
| `src/app/globals.css:5109` | `Ask VedaGraph` — section banner comment |
| `src/lib/ask.ts:2` | `The Ask VedaGraph contract, …` — docblock |
| `src/lib/ask.ts:6` | `The shapes below track vedagraph.api.ask.models` — **backend module path**, keep |
| `src/lib/ask-citations.ts:4` | `mirrors vedagraph.api.ask.citation.extract_cited_ids` — **backend module path**, keep |
| `src/lib/api-schema.ts:1181, 1183, 1222, 2162, 2998, 3126` | **generated** from backend docstrings — never hand-edit; regenerate after the backend renames |
| `README.md:1, 3, 8, 27` | `# VedaGraph frontend`, prose, `uvicorn vedagraph.api.app:app` — the uvicorn path is a **backend module path**, keep |
| `.env.example:1` | comment describing the API |
| `next.config.ts:12–13` | comment naming backend env vars |

### 8.8 Rename checklist

| Action | Count | Sites |
| --- | --- | --- |
| **Rename** (user-facing copy) | 12 | §8.1 |
| **Rename** (metadata) | 3 strings / 2 sites | §8.2 |
| **Rename** (docs/comments, optional) | ~9 | §8.7, excluding backend module paths |
| **Update in lockstep with copy** (tests) | 5 | §8.3 |
| **DO NOT rename** (env var) | 6 sites + 2 comment mentions | §8.4 |
| **DO NOT rename** (`VG:` prefix) | ~55 across `src/` + `tests/` | §8.6 |
| **DO NOT hand-edit** (generated) | 6 | `src/lib/api-schema.ts` |
| **Backend module paths in comments** | 4 | `ask.ts:6`, `ask-citations.ts:4`, `README.md:27`, plus `api-schema.ts` prose |

**One trap to note.** `src/app/layout.tsx:18` sets both the default `<title>` and the `%s | VedaGraph` template, and **no test asserts either**. The `<title>` of every page in the product is currently unprotected. Add a metadata assertion as part of the rebrand so the next rename cannot half-land.

---

# PART TWO — PROPOSED VedAnvaya DESIGN-TOKEN ARCHITECTURE

## 9. Naming scheme

Three tiers. A component may only ever reference tier 3.

| Tier | Shape | Example | Rule |
| --- | --- | --- | --- |
| **1 — Primitive** | `--va-<family>-<step>` | `--va-ivory-100`, `--va-rubric-500` | Raw, theme-independent values. **Never referenced by a component.** Declared once, outside `.dark`. |
| **2 — Alias** | `--va-<role>` | `--va-surface-page`, `--va-text-primary` | Maps a role to a primitive. **Redefined under `.dark`.** This is the only tier the theme switches. |
| **3 — Component** | `--va-<component>-<part>` | `--va-card-border`, `--va-chip-bg` | Optional. Only introduce one where a component genuinely needs an override point; otherwise a component uses a tier-2 alias directly. |

**Prefix.** Every token carries `--va-`. Reasons: (a) it makes the audit trivial — `grep -c '\-\-va-'` is the adoption metric during migration; (b) it cannot collide with Tailwind's own `--color-*` / `--text-*` / `--spacing-*` namespaces, which matters because §15 recommends keeping Tailwind's default theme partly enabled; (c) it lets the old and new systems coexist in one file for the whole migration (§16).

**Role vocabulary (tier 2), fixed:**

```
surface-{page,raised,sunk,strong,inverse}
text-{primary,secondary,tertiary,inverse,on-accent}
line-{hairline,strong,focus}
accent-{base,hover,soft,on}
tone-{evidenced,partial,insufficient,unbuilt,neutral}          ← foreground
tone-{evidenced,partial,insufficient,unbuilt,neutral}-surface  ← background
```

**Two renames carried from the audit, deliberately:**

- `supported` → **`evidenced`**. `statusCopy` (`knowledge.ts:67`) already maps the backend's `SUPPORTED` to the label "Supported"; the *token* should say what the colour means visually (this is backed by evidence) rather than echo an API enum. Keeps the CSS honest if the backend enum changes.
- `not-built` → **`unbuilt`**. The hyphen inside a hyphenated token (`--tone-not-built-bg`) is the reason the current names read badly.

**What disappears:** `--muted` / `--faint` collapse into `text-secondary` / `text-tertiary` with values that are **actually distinguishable** (the current pair differs by 4/11/3 in RGB — §1.2). `--tone-unknown` disappears entirely; it was byte-identical to `--muted`.

---

## 10. Colour tokens

Built from the five brand anchors: **manuscript-ivory `#F4F0E7`**, **carbon-ink `#171815`**, **rubric-red `#B64A2E`**, **aged-gold `#B49A62`**, **indigo-ink `#26364A`**.

Two derived families are needed because the five anchors cannot carry five semantic states: **verdigris** (a muted green for "evidenced", pulled toward the ivory's warmth so it does not read as a dashboard green) and **slate** (a neutral grey-green for "unbuilt", desaturated from indigo).

Every value below was contrast-checked against the surfaces it is actually used on. Ratios are stated.

### 10.1 Tier 1 — primitives (theme-independent)

**Ivory (paper)**

| Token | Value | Role |
| --- | --- | --- |
| `--va-ivory-50` | `#FBF9F4` | raised card |
| `--va-ivory-100` | `#F4F0E7` | **brand anchor** — page |
| `--va-ivory-200` | `#EBE5D8` | sunk |
| `--va-ivory-300` | `#DFD7C6` | strong / active |
| `--va-ivory-400` | `#CFC5AF` | strong hairline |
| `--va-ivory-line` | `#E3DCCC` | hairline |

**Carbon (ink)**

| Token | Value | Role |
| --- | --- | --- |
| `--va-carbon-900` | `#171815` | **brand anchor** — primary text |
| `--va-carbon-700` | `#3A3B36` | strong secondary |
| `--va-carbon-500` | `#5C5E56` | secondary text |
| `--va-carbon-400` | `#676960` | tertiary text |
| `--va-carbon-300` | `#8A8C82` | disabled / decorative only |

**Rubric (accent)**

| Token | Value | Role |
| --- | --- | --- |
| `--va-rubric-700` | `#8E3720` | pressed |
| `--va-rubric-600` | `#A14026` | hover / small text on paper |
| `--va-rubric-500` | `#B64A2E` | **brand anchor** — accent |
| `--va-rubric-400` | `#C9694F` | dark-theme accent |
| `--va-rubric-300` | `#DFA08C` | dark-theme accent text |
| `--va-rubric-100` | `#F2DFD8` | accent-soft (light) |
| `--va-rubric-950` | `#2E1C16` | accent-soft (dark) |

**Gold (aged-gold — the *partial / caution* family)**

| Token | Value | Role |
| --- | --- | --- |
| `--va-gold-700` | `#74602F` | partial text (light) |
| `--va-gold-500` | `#B49A62` | **brand anchor** — rules, ornament, metric emphasis |
| `--va-gold-400` | `#C9B486` | partial text (dark) |
| `--va-gold-100` | `#EFE6D1` | partial surface (light) |
| `--va-gold-950` | `#2A2418` | partial surface (dark) |

**Indigo (indigo-ink — the *structural / secondary* family)**

| Token | Value | Role |
| --- | --- | --- |
| `--va-indigo-800` | `#1A2632` | dark page |
| `--va-indigo-700` | `#26364A` | **brand anchor** — inverse surface, headings on ivory |
| `--va-indigo-600` | `#35495F` | |
| `--va-indigo-300` | `#8BA3BE` | dark-theme secondary accent |
| `--va-indigo-100` | `#DCE4EC` | |
| `--va-indigo-950` | `#1B242E` | dark neutral surface |

**Verdigris (derived — *evidenced*)**

| Token | Value |
| --- | --- |
| `--va-verdigris-700` | `#2E5E4B` |
| `--va-verdigris-300` | `#7FB39C` |
| `--va-verdigris-100` | `#DFEAE2` |
| `--va-verdigris-950` | `#1B2A24` |

**Slate (derived — *unbuilt / neutral*)**

| Token | Value |
| --- | --- |
| `--va-slate-700` | `#4C5660` |
| `--va-slate-300` | `#9BA6B0` |
| `--va-slate-100` | `#E4E7EA` |
| `--va-slate-950` | `#1E242A` |

**Dark paper (carbon-derived, warm-black — *not* the indigo)**

| Token | Value | Role |
| --- | --- | --- |
| `--va-night-900` | `#0F100C` | sunk |
| `--va-night-800` | `#131410` | page |
| `--va-night-700` | `#1C1D17` | raised card |
| `--va-night-600` | `#26271F` | strong |
| `--va-night-line` | `#2E3028` | hairline |
| `--va-night-line-strong` | `#40423A` | strong hairline |

> Dark mode keeps the **warm** axis of the brand rather than flipping to the cool indigo. `#131410` is carbon-ink pulled down, not a blue-black. That preserves the manuscript metaphor and is the one decision most likely to be second-guessed — record it.

### 10.2 Tier 2 — aliases, light and dark

| Alias | Light | Dark | Contrast on its page bg |
| --- | --- | --- | --- |
| `--va-surface-page` | `ivory-100 #F4F0E7` | `night-800 #131410` | — |
| `--va-surface-raised` | `ivory-50 #FBF9F4` | `night-700 #1C1D17` | — |
| `--va-surface-sunk` | `ivory-200 #EBE5D8` | `night-900 #0F100C` | — |
| `--va-surface-strong` | `ivory-300 #DFD7C6` | `night-600 #26271F` | — |
| `--va-surface-inverse` | `indigo-700 #26364A` | `ivory-100 #F4F0E7` | — |
| `--va-text-primary` | `carbon-900 #171815` | `ivory-100 #F4F0E7` | **15.68** / **16.26** AAA |
| `--va-text-secondary` | `carbon-500 #5C5E56` | `#B0AFA3` | **5.79** / **7.68** (on raised) AA/AAA |
| `--va-text-tertiary` | `carbon-400 #676960` | `#9C9B90` | **4.90** / **6.61** AA |
| `--va-text-inverse` | `ivory-50 #FBF9F4` | `carbon-900 #171815` | **11.68** on indigo-700 AAA |
| `--va-text-on-accent` | `ivory-50 #FBF9F4` | `carbon-900 #171815` | **4.98** / **4.77** AA |
| `--va-line-hairline` | `ivory-line #E3DCCC` | `night-line #2E3028` | — |
| `--va-line-strong` | `ivory-400 #CFC5AF` | `night-line-strong #40423A` | — |
| `--va-line-focus` | `rubric-500 #B64A2E` | `rubric-400 #C9694F` | — |
| `--va-accent-base` | `rubric-500 #B64A2E` | `rubric-400 #C9694F` | **4.61** / **4.95** AA |
| `--va-accent-text` | `rubric-600 #A14026` | `rubric-300 #DFA08C` | **5.64** / **8.41** AA/AAA |
| `--va-accent-hover` | `rubric-600 #A14026` | `rubric-300 #DFA08C` | — |
| `--va-accent-soft` | `rubric-100 #F2DFD8` | `rubric-950 #2E1C16` | — |
| `--va-tone-evidenced` | `verdigris-700 #2E5E4B` | `verdigris-300 #7FB39C` | **6.55** / **7.78** AA/AAA |
| `--va-tone-evidenced-surface` | `verdigris-100 #DFEAE2` | `verdigris-950 #1B2A24` | pair **6.03** / **6.29** AA |
| `--va-tone-partial` | `gold-700 #74602F` | `gold-400 #C9B486` | **5.34** / **9.12** AA/AAA |
| `--va-tone-partial-surface` | `gold-100 #EFE6D1` | `gold-950 #2A2418` | pair **4.89** / **7.59** AA |
| `--va-tone-insufficient` | `rubric-700 #8E3720` | `rubric-300 #DFA08C` | see note |
| `--va-tone-insufficient-surface` | `rubric-100 #F2DFD8` | `rubric-950 #2E1C16` | pair **4.98** / **7.38** AA |
| `--va-tone-unbuilt` | `slate-700 #4C5660` | `slate-300 #9BA6B0` | AA on both papers |
| `--va-tone-unbuilt-surface` | `slate-100 #E4E7EA` | `slate-950 #1E242A` | AA |
| `--va-tone-neutral` | = `--va-text-secondary` | = `--va-text-secondary` | alias, not a new value |
| `--va-tone-neutral-surface` | `ivory-200 #EBE5D8` | `night-900 #0F100C` | — |
| `--va-scrim` | `color-mix(in srgb, carbon-900 42%, transparent)` | `color-mix(in srgb, #000 62%, transparent)` | **theme-aware**, fixes §5 A14 |

**The insufficient/accent collision, resolved.** §1.2 recorded that today `--tone-insufficient #99452b` and `--accent #b04728` are the same hue, so an error and a link look alike. The fix here is **shape and depth, not hue**: `--va-tone-insufficient` is `rubric-700` (two steps darker than the accent) **and** every insufficient surface is required to carry a **dashed** border (`--va-border-style-insufficient: dashed`), which the current design already does in places (`.certainty-chip.band-ambiguous`, `.evidence-rows.is-threat`, `.gap-card`). Making that a token-level rule rather than an ad-hoc one means the error state is distinguishable without inventing a sixth hue that would fight the manuscript palette.

### 10.3 Graph colour — one table, not two

§1.5 recorded eleven graph colours defined twice (TypeScript node fills vs CSS legend text) with different values and no link. Fix by making the **CSS the single source** and reading it from TS:

```css
/* one entry per semantic group; -fill is the node, -text is the legible legend */
--va-group-deity-fill:    #B64A2E;   --va-group-deity-text:    #A14026;
--va-group-passage-fill:  #9B8462;   --va-group-passage-text:  #7E6A4E;  /* 4.92 AA */
--va-group-person-fill:   #607D92;   --va-group-person-text:   #4E6A7E;  /* 5.41 AA */
--va-group-idea-fill:     #6C8F83;   --va-group-idea-text:     #4F6E63;  /* 5.33 AA */
--va-group-rite-fill:     #8A6F9B;   --va-group-rite-text:     #745A84;  /* 5.64 AA */
--va-group-thing-fill:    #7D7969;   --va-group-thing-text:    #6C6959;  /* 5.25 AA */
--va-group-wording-fill:  #4F7F8F;   --va-group-wording-text:  #416A76;  /* 5.63 AA */
--va-group-record-fill:   #8C9490;   --va-group-record-text:   var(--va-text-secondary);
--va-group-derived-fill:  #8D8D8D;   --va-group-derived-text:  var(--va-text-secondary);
--va-group-unresolved-fill: #B59A8F; --va-group-unresolved-text: var(--va-text-secondary);
--va-group-other-fill:    #8C9490;   --va-group-other-text:    var(--va-text-secondary);
```

Dark overrides (all ≥6.3:1 on `night-700`): passage `#C9B08A` (8.13), person `#8AA8BE` (6.81), idea `#8DB5A6` (7.51), rite `#AE94C2` (6.31), thing `#A9A48F` (6.78), wording `#7FAFBE` (7.09).

`graph-canvas.tsx` then reads the fills with `getComputedStyle(document.documentElement).getPropertyValue('--va-group-…-fill')` inside `buildStyle`, instead of holding `GROUP_STYLE.light/.dark`. `GROUP_STYLE` keeps `label`, `shape` and `size` — the parts that are genuinely structural and are asserted by `tests/unit/graph-semantics.test.ts:19–29` (`light !== dark` must become a check against the CSS values, or be dropped in favour of a shape check, which the same test already makes).

---

## 11. Type scale

**Families.** Three, as specified, each with an explicit fallback chain and a Devanagari companion.

| Token | Stack | Use |
| --- | --- | --- |
| `--va-font-display` | `var(--font-fraunces), "Iowan Old Style", Georgia, serif` | h1–h3, pull quotes, metric numerals, Sanskrit transliteration |
| `--va-font-ui` | `var(--font-inter), system-ui, -apple-system, "Segoe UI", sans-serif` | everything else |
| `--va-font-deva-serif` | `var(--font-noto-serif-deva), var(--font-fraunces), serif` | Devanagari **reading** text, paired with display |
| `--va-font-deva-sans` | `var(--font-noto-sans-deva), var(--font-inter), sans-serif` | Devanagari in UI chrome (labels, chips) |
| `--va-font-mono` | `ui-monospace, "SF Mono", Menlo, monospace` | canonical keys, ids |

**Load them the same way the current build does** — `next/font/google` in `layout.tsx`, `display: "swap"`, `variable: "--font-fraunces"` etc. Fraunces needs `axes: ["SOFT","WONK","opsz"]` if the optical-size axis is wanted; at minimum pin `weight: ["400","500","600"]` to avoid shipping the full variable range.

> **Fraunces has no Devanagari coverage and Noto Serif Devanagari has no Latin numerals worth using.** The two must be paired per-element, never in one stack, or the `.sanskrit` block will silently fall back for Latin punctuation. That is why there are four font tokens, not three.

**Size scale — 9 steps, fluid only at the top.** Root stays `16px` (not the current `15px`, which is the unlabelled origin of every `rem` in the file).

| Token | Value | ≈px @16 | Use | Replaces |
| --- | --- | --- | --- | --- |
| `--va-text-2xs` | `0.6875rem` | 11 | eyebrow, chip count, `<kbd>` | `.66`–`.70rem` (38 decls) |
| `--va-text-xs` | `0.75rem` | 12 | metadata, `<cite>`, table head | `.72`–`.76rem` (63 decls) |
| `--va-text-sm` | `0.8125rem` | 13 | secondary body, notes, captions | `.78`–`.83rem` (81 decls) |
| `--va-text-base` | `0.875rem` | 14 | UI body, card body | `.84`–`.88rem` (70 decls) |
| `--va-text-md` | `1rem` | 16 | prose body, form fields | `.90`–`1.02rem` (30 decls) |
| `--va-text-lg` | `1.125rem` | 18 | lede, translation blockquote | `1.04`–`1.15rem` (11 decls) |
| `--va-text-xl` | `1.375rem` | 22 | h3, card title, panel title | `1.16`–`1.36rem` (16 decls) |
| `--va-text-2xl` | `clamp(1.5rem, 1.25rem + 1.1vw, 2rem)` | 24–32 | h2, section heading | 4 clamps + `1.4`–`1.7rem` |
| `--va-text-3xl` | `clamp(2rem, 1.55rem + 2.2vw, 3rem)` | 32–48 | h1 | **all four** h1 clamps |
| `--va-text-display` | `clamp(2.5rem, 1.8rem + 3.4vw, 4rem)` | 40–64 | home hero only | `.hero h1` clamp |

**Nine steps replace 57.** The two fluid steps replace eight unrelated `clamp()` expressions; note that `--va-text-2xl` and `--va-text-3xl` share a ratio so h1 and h2 stay in proportion at every width, which the current four independent h1 clamps do not.

**Reading sizes are separate**, because Sanskrit and translation need their own optical treatment:

| Token | Value | Use |
| --- | --- | --- |
| `--va-text-sanskrit` | `clamp(1.25rem, 1rem + 1vw, 1.75rem)` | `.sanskrit` primary |
| `--va-text-sanskrit-inline` | `1.0625rem` | Sanskrit inside evidence rows |
| `--va-text-reading` | `1.1875rem` | translation blockquote |

**Line height — 5 steps, replacing 13:**

| Token | Value | Use |
| --- | --- | --- |
| `--va-leading-flat` | `1.1` | display + h1 |
| `--va-leading-tight` | `1.25` | h2, h3 |
| `--va-leading-snug` | `1.45` | dense UI, chips, table cells |
| `--va-leading-normal` | `1.6` | UI body, secondary text |
| `--va-leading-prose` | `1.75` | translation, Ask prose |
| `--va-leading-deva` | `2.05` | Devanagari only (matras need it) |

**Weight — 4 steps. The "no bold" rule survives and becomes explicit:**

| Token | Value | Use |
| --- | --- | --- |
| `--va-weight-regular` | `400` | body |
| `--va-weight-medium` | `500` | emphasis, `<strong>`, headings |
| `--va-weight-semibold` | `600` | eyebrows and micro-headings **only** |
| `--va-weight-display` | `500` | Fraunces headings |

> Document the rule: **`700` is not in the system.** Headings get weight from size, family and colour, not from bold. That is the single most characteristic property of the current design and the easiest to lose in a rebuild.

**Tracking — 4 steps, replacing 16:**

| Token | Value | Use |
| --- | --- | --- |
| `--va-tracking-display` | `-0.02em` | display + h1 |
| `--va-tracking-tight` | `-0.01em` | h2, h3 |
| `--va-tracking-normal` | `0` | body |
| `--va-tracking-eyebrow` | `0.09em` | **the one uppercase value** — replaces `.08`/`.09`/`.10em` (53 decls) |
| `--va-tracking-wide` | `0.14em` | veda codes, the two widest labels |

**Uppercase is a named decision.** It appears 62 times today. Give it one token pairing — `--va-text-2xs` + `--va-weight-semibold` + `--va-tracking-eyebrow` + `--va-text-tertiary` — expose it as a single `Eyebrow` primitive, and forbid ad-hoc uppercase elsewhere.

---

## 12. Space, radii, borders, elevation

### 12.1 Spacing — 4px base, 12 steps

Replaces ~36 padding values and ~30 gap values.

| Token | Value | px | Typical use |
| --- | --- | --- | --- |
| `--va-space-3xs` | `0.125rem` | 2 | icon nudge, chip inner |
| `--va-space-2xs` | `0.25rem` | 4 | tight stack |
| `--va-space-xs` | `0.375rem` | 6 | chip row gap |
| `--va-space-sm` | `0.5rem` | 8 | list gap, inline gap |
| `--va-space-md` | `0.75rem` | 12 | card inner gap, small padding |
| `--va-space-lg` | `1rem` | 16 | **default** card padding, grid gap |
| `--va-space-xl` | `1.5rem` | 24 | card padding (roomy), section inner |
| `--va-space-2xl` | `2rem` | 32 | stack between blocks |
| `--va-space-3xl` | `2.5rem` | 40 | page block gap |
| `--va-space-4xl` | `3.5rem` | 56 | section block padding (mobile) |
| `--va-space-5xl` | `4.5rem` | 72 | section block padding (desktop) |
| `--va-space-6xl` | `6rem` | 96 | page bottom |

**Layout constants get names too** — these are the hand-computed magic numbers from §1.5:

| Token | Value | Replaces |
| --- | --- | --- |
| `--va-shell-max` | `82.5rem` (1320px) | `globals.css:166` |
| `--va-shell-gutter` | `2rem` / `1rem` @ sm | `48px` / `32px` |
| `--va-header-height` | `4rem` (64px) | `66px` (`:330`) |
| `--va-sticky-offset` | `calc(var(--va-header-height) + var(--va-space-lg))` | the duplicated `92px` at `:1484`, `:1841` |

**Measure — 3 steps, replacing 11:**

| Token | Value | Use |
| --- | --- | --- |
| `--va-measure-tight` | `46ch` | ledes, hero copy, asides |
| `--va-measure` | `66ch` | default prose, reading column |
| `--va-measure-wide` | `84ch` | caveats, wide notes |

### 12.2 Radii — 5 steps

| Token | Value | Use |
| --- | --- | --- |
| `--va-radius-xs` | `4px` | `<kbd>`, citation chip, inline code |
| `--va-radius-sm` | `8px` | inner surfaces, list rows, small cards |
| `--va-radius-md` | `12px` | cards, panels, drawers |
| `--va-radius-lg` | `18px` | hero visual, feature cards |
| `--va-radius-pill` | `999px` | buttons, chips, badges |

`--va-radius-sm` at 8px and `--va-radius-md` at 12px replace the current `9px`/`14px` (and the stray literals `5px`, `11px`, `12px`, `9px` from §1.5). Moving to an even scale matters because it makes nested radii computable: an inner element inside a `--va-radius-md` card should be `--va-radius-sm`, and 12 − 4 = 8 holds.

### 12.3 Borders and hairlines — the load-bearing decision

The present design expresses **all** depth through 1px hairlines (73 `border: 1px solid var(--line)`), with essentially no shadow. Keep that, and name it so it cannot drift:

| Token | Value | Meaning |
| --- | --- | --- |
| `--va-border-width` | `1px` | the only border width in the system |
| `--va-border-width-accent` | `3px` | the left rule on callouts and quotes |
| `--va-border-hairline` | `var(--va-border-width) solid var(--va-line-hairline)` | default container edge |
| `--va-border-strong` | `var(--va-border-width) solid var(--va-line-strong)` | inputs, active surfaces |
| `--va-border-dashed` | `var(--va-border-width) dashed var(--va-line-strong)` | **"not established"** — a *semantic* border |
| `--va-border-dotted` | `var(--va-border-width) dotted var(--va-line-strong)` | **"derived, not stated"** |

**The dashed and dotted borders are semantic tokens, not decorative ones.** Today `.certainty-split .is-ambiguous` (`globals.css:2531`), `.evidence-rows.is-threat` (`:3798`), `.gap-card` (`:4496`), `.parallel-list.is-muted` (`:2313`), `.derived-metric` (dotted, `:4997`), `.truncated-types` (`:3094`), `.ask-unresolved` (`:5751`) and `.ask-evidence-item[data-cited=false]` (`:5989`) all encode "this is weaker evidence" through border style. That is a genuine, non-colour-dependent accessibility feature and it is currently invisible in the token layer. Name it, and require every insufficient/interpretive surface to use it.

**Rules (horizontal separators)** get their own token so they can be gold rather than grey — the one place aged-gold earns its keep as an ornamental rule in an editorial layout:

| Token | Value |
| --- | --- |
| `--va-rule-quiet` | `1px solid var(--va-line-hairline)` |
| `--va-rule-feature` | `1px solid color-mix(in srgb, var(--va-gold-500) 45%, transparent)` |

### 12.4 Elevation — 4 steps, three of which are not shadows

| Token | Light | Dark | Meaning |
| --- | --- | --- | --- |
| `--va-elevation-flat` | `none` | `none` | on the page |
| `--va-elevation-raised` | `none` + `--va-surface-raised` + hairline | same | a card — **surface + hairline, no shadow** |
| `--va-elevation-floating` | `0 1px 2px color-mix(in srgb, var(--va-carbon-900) 6%, transparent)` | `0 1px 2px rgb(0 0 0 / .4)` | composer, answer |
| `--va-elevation-overlay` | `0 18px 46px -24px color-mix(in srgb, var(--va-carbon-900) 34%, transparent)` | `0 0 0 1px var(--va-night-line-strong), 0 24px 56px -28px rgb(0 0 0 / .8)` | drawers, dialogs |

Note the dark `overlay` value adds a **1px light ring** rather than relying on a darker shadow — §6.3 (c) recorded that a 52px black blur on a near-black page reads as nothing.

---

## 13. Motion

**Durations — 4 steps, replacing 6 ad-hoc values:**

| Token | Value | Use |
| --- | --- | --- |
| `--va-duration-instant` | `100ms` | colour-only change (chip, citation marker) |
| `--va-duration-fast` | `160ms` | hover, focus ring, border colour |
| `--va-duration-base` | `240ms` | small position/opacity change, disclosure |
| `--va-duration-slow` | `400ms` | drawer slide, graph layout settle |

**Easings — 4, replacing "browser default everywhere":**

| Token | Value | Use |
| --- | --- | --- |
| `--va-ease-standard` | `cubic-bezier(0.2, 0, 0, 1)` | default — fast out, settles |
| `--va-ease-enter` | `cubic-bezier(0.05, 0.7, 0.1, 1)` | things arriving (drawer in, answer in) |
| `--va-ease-exit` | `cubic-bezier(0.3, 0, 0.8, 0.15)` | things leaving |
| `--va-ease-linear` | `linear` | spinners, shimmer only |

**Composites**, so a component never assembles its own:

```css
--va-transition-colors: color var(--va-duration-fast) var(--va-ease-standard),
                        background-color var(--va-duration-fast) var(--va-ease-standard),
                        border-color var(--va-duration-fast) var(--va-ease-standard);
--va-transition-transform: transform var(--va-duration-base) var(--va-ease-standard);
--va-transition-opacity: opacity var(--va-duration-base) var(--va-ease-standard);
```

This fixes the §1.12 inconsistency where 36 accent-border hovers were untransitioned while 13 others were: every interactive primitive gets `--va-transition-colors`, once.

**Reduced motion must be enforced in JS, not only CSS.** The CSS block stays as-is, and a shared helper is added:

```ts
// src/lib/motion.ts
export const prefersReducedMotion = () =>
  typeof window !== "undefined" &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

export const scrollBehavior = (): ScrollBehavior =>
  prefersReducedMotion() ? "auto" : "smooth";
```

Applied at the three unguarded sites from §5 A6: `ask-experience.tsx:127`, `ask-evidence-drawer.tsx:70`, `graph-canvas.tsx:361`. `graph-canvas.tsx:344–346` already does this inline and should use the helper.

**Keyframes keep their names** (`shimmer`, `spin`, `ask-pulse`) but take tokenised durations: `--va-duration-shimmer: 1.5s`, `--va-duration-spin: 800ms`, `--va-duration-pulse: 1100ms`.

---

## 14. Z-index ladder

Six named rungs, 100 apart, replacing `1/40/60/61/100`:

| Token | Value | Occupant |
| --- | --- | --- |
| `--va-z-base` | `0` | page content |
| `--va-z-raised` | `10` | sticky rails, `.reader-aside`, `.sticky-aside` (currently **unset** — see §1.13) |
| `--va-z-sticky` | `100` | `.site-header` |
| `--va-z-overlay` | `200` | dialog scrim |
| `--va-z-modal` | `210` | drawer / dialog content |
| `--va-z-toast` | `300` | reserved — nothing uses it yet |
| `--va-z-skip` | `400` | the skip link, which must outrank everything |

Rule: **no component may write a numeric `z-index`.** The only permitted local value is `z-index: 1` inside an already-stacked context (e.g. the sticky drawer header at `globals.css:3179`), and that should become `--va-z-local: 1`.

---

## 15. Tailwind v4 `@theme` — how it actually works, and the recommendation

### 15.1 Verified behaviour (Tailwind 4.3.3, as installed)

Confirmed against `node_modules/tailwindcss/` in this repo:

- **Directives supported:** `@theme`, `@utility`, `@custom-variant`, `@variant`, `@apply`, `@import`, `@layer`, `@source`, `@plugin`, `@config`, `@reference`.
- **`@theme` options:** `inline`, `static`, `reference`, `default` — all four are recognised by the engine.
- **Default namespaces present in `theme.css`:** `--color-*`, `--font-*`, `--text-*`, `--tracking-*`, `--leading-*`, `--spacing-*`, `--radius-*`, `--shadow-*`, `--inset-shadow-*`, `--drop-shadow-*`, `--blur-*`, `--perspective-*`, `--aspect-*`, `--ease-*`, `--animate-*`, `--breakpoint-*`, `--container-*`, `--default-*`, `--max-*`.

**`@theme` vs `@theme inline` — the distinction that matters here.**

`@theme` emits the variable into `:root` **and** makes the generated utility *reference* it:

```css
@theme { --color-accent: var(--va-accent-base); }
/* → :root { --color-accent: var(--va-accent-base) }
   → .text-accent { color: var(--color-accent) }        ← indirection kept */
```

`@theme inline` emits the variable **and** inlines its *value* into the utility:

```css
@theme inline { --color-accent: var(--va-accent-base); }
/* → .text-accent { color: var(--va-accent-base) }      ← resolved at build */
```

**For a class-switched dark theme, `inline` is the correct and the only safe form.** With plain `@theme`, `.text-accent` resolves `--color-accent` *at the `:root` where it was declared*, so a `.dark` redefinition of `--va-accent-base` does not reach it reliably; with `inline`, the utility literally says `var(--va-accent-base)` and picks up whichever value is in scope at the element. The existing file already got this right at `globals.css:67` (`@theme inline`) — that three-line block is the one piece of Tailwind wiring worth keeping and extending.

**`@theme static`** forces emission of every variable even when unused — useful for tokens read from JavaScript (which the graph will do, §10.3), because tree-shaking would otherwise drop `--va-group-*-fill`.

**`@theme reference`** registers values for utility generation *without* emitting any CSS variable — the right choice for tokens that exist only so a utility name resolves.

**Namespace override:** `--color-*: initial;` inside `@theme` removes Tailwind's entire default palette (all ~300 variables) and leaves only what is declared after it. `--*: initial;` empties the whole default theme.

**Dark variant:** in v4 the built-in `dark:` variant keys on `prefers-color-scheme`. To make it key on the class that `next-themes` writes, this line is **mandatory** and is currently **absent**:

```css
@custom-variant dark (&:where(.dark, .dark *));
```

Without it, any `dark:` utility ignores the user's explicit theme choice (§1.15). This is a live trap for the rebuild.

### 15.2 Recommendation: **hybrid — semantic components, utility escape hatch. Do not go utility-first.**

**Recommended architecture**

```
src/styles/
  tokens.css        @theme static  — tier 1 primitives + @custom-variant dark
  theme.css         @theme inline  — tier 2 aliases, :root + .dark
  base.css          @layer base    — reset deltas, element defaults, focus, Sanskrit
  primitives.css    @layer components — ~18 primitives, token-only, no literals
  app.css           @import the four above, after @import "tailwindcss"
```

**Reasons to keep semantic classes as the primary mechanism:**

1. **The test suite is the deciding constraint.** 61 literal class selectors across 80 Playwright cases (§7.2) assert on `.veda-card`, `.sanskrit`, `figure.measure`, `section.recitation`, `.ask-prose`. Utility-first deletes every one of those hooks at once and turns a rebrand into a simultaneous test rewrite. A semantic class layer lets classes be renamed **one primitive at a time**, each with its own test update.
2. **Contrast is CI-enforced against computed styles.** `release-closure.spec.ts:89–135` walks the DOM and resolves the nearest opaque painted ancestor in both themes. That works identically under either approach — but the *fix* for a failure is a one-line token edit under semantic classes, versus hunting utility strings across 29 TSX files.
3. **This is an editorial reading surface, not a product dashboard.** `.sanskrit` needs `font-family` + fluid `font-size` + `line-height: 1.95` + `letter-spacing: 0.004em` + `overflow-wrap: break-word` + `hyphens: none` + `lang="sa"`. As utilities that is eight classes repeated at 14 call sites; as a primitive it is one component and one rule. Roughly 60 % of the current stylesheet is this kind of typographic rule.
4. **The semantic classes already encode epistemics.** `.tone-insufficient`, `.band-ambiguous`, `.condition-kind.kind-threat`, `[data-cited="false"]` are not styling decisions — they are the product's honesty contract, driven from `knowledge.ts`. Dissolving them into utilities scatters that contract across TSX and makes "does every insufficient surface use a dashed border?" ungreppable.
5. **`@theme inline` gives the tokens to Tailwind for free.** Declaring the tier-2 aliases in `@theme inline` means `bg-surface-raised`, `text-tertiary`, `border-hairline`, `p-lg`, `gap-md`, `rounded-md`, `text-xl`, `duration-fast`, `ease-standard` all exist as utilities **without writing them**. That is the escape hatch: layout one-offs, spacing tweaks and prototypes use utilities; anything that recurs is promoted to a primitive.

**Reasons not to go pure utility-first here:** the 353 `font-size` declarations and 183 padding declarations are mostly *typographic composition*, not layout; utilities would inflate the TSX by roughly 3–4 classes per element across ~29 route files with no reduction in total complexity, while destroying every test hook and every greppable semantic rule in one commit.

**Reasons not to stay pure-semantic either:** the 20 near-identical card grids (§4 #7) and the ~30 one-off layout wrappers are exactly what utilities are good at. Keeping them as bespoke CSS is how the file reached 6,407 lines.

**The rule to write down:** *a class earns a name when it carries meaning (a card, a caveat, a status, a Sanskrit block) or recurs three or more times. Everything else is a utility.*

**Concrete skeleton:**

```css
/* app.css */
@import "tailwindcss";
@import "./tokens.css";
@import "./theme.css";
@import "./base.css";
@import "./primitives.css";

/* tokens.css */
@custom-variant dark (&:where(.dark, .dark *));

@theme static {
  --color-*: initial;              /* drop Tailwind's 300 default colours */
  --va-ivory-100: #F4F0E7;
  --va-carbon-900: #171815;
  --va-rubric-500: #B64A2E;
  --va-gold-500:   #B49A62;
  --va-indigo-700: #26364A;
  /* …all tier-1 primitives, plus --va-group-*-fill for the graph */
}

/* theme.css */
:root {
  --va-surface-page:  var(--va-ivory-100);
  --va-text-primary:  var(--va-carbon-900);
  --va-accent-base:   var(--va-rubric-500);
  /* …all tier-2 aliases */
}
.dark {
  --va-surface-page:  var(--va-night-800);
  --va-text-primary:  var(--va-ivory-100);
  --va-accent-base:   var(--va-rubric-400);
}

@theme inline {
  /* expose tier 2 to Tailwind; `inline` so .dark reaches the utilities */
  --color-page:     var(--va-surface-page);
  --color-raised:   var(--va-surface-raised);
  --color-ink:      var(--va-text-primary);
  --color-ink-2:    var(--va-text-secondary);
  --color-ink-3:    var(--va-text-tertiary);
  --color-accent:   var(--va-accent-base);
  --color-hairline: var(--va-line-hairline);
  --spacing-lg:     var(--va-space-lg);
  --radius-md:      var(--va-radius-md);
  --text-xl:        var(--va-text-xl);
  --ease-standard:  var(--va-ease-standard);
  --font-display:   var(--va-font-display);
  --font-ui:        var(--va-font-ui);
}
```

One caveat to verify on first build: `--color-*: initial` also removes `--color-black`/`--color-white`/`--color-transparent`, which Preflight and a few utilities assume. Re-declare those three explicitly.

---

## 16. Migration strategy

**Governing constraint: the app must build, serve and pass `pnpm test` at the end of every step.** The audit found three things that make that achievable — `globals.css` is a single file with no import graph; every component already reads tokens through `var()`; and there is a machine contrast check plus an overflow harness that can both act as gates.

### Step 0 — Instrument before touching anything

*No visual change. This step exists so every later step has a red/green signal.*

1. Add `data-component` / `data-part` attributes to the 20 most-asserted elements and **migrate the 61 literal class selectors in `tests/` to them** (§7.5 item 1). `.sanskrit` → `[data-component="sanskrit"]`, `figure.measure` → `[data-component="measure"]`, `section.recitation` → `[data-component="recitation"]`, and so on.
2. Fix the vacuous regex at `journeys.spec.ts:359` and delete the inert guard at `:263`.
3. Convert the six negative assertions (§7.2 Tier 4) to positive form.
4. Give `tests/visual-qa.mjs` a non-zero exit code when `findings.length > 0`, and wire it into CI at 1440/1024/390.
5. Add one metadata test asserting the `<title>` of `/` and `/ask` (§8.8).

**Gate:** `pnpm test`, `pnpm test:e2e`, `node tests/visual-qa.mjs` all green. Commit.

### Step 1 — Land the token layer beside the old one

*No visual change.*

1. Create `src/styles/tokens.css`, `theme.css` with the full tier-1 and tier-2 sets from §10–§14. Add `@custom-variant dark`.
2. `@import` them from `globals.css` at line 2, **after** `@import "tailwindcss"`.
3. Do **not** delete `:root`/`.dark` (lines 8–65). Instead, redefine the 31 old tokens in terms of the new ones:
   ```css
   :root { --bg: var(--va-surface-page); --ink: var(--va-text-primary); … }
   .dark { /* nothing — the aliases already switch */ }
   ```
4. The whole app now renders from the new palette through the old names.

**Gate:** contrast test in both themes at three viewports; visual-qa overflow report; a manual screenshot diff. **Expect and review deliberate colour shifts** — this is the step where the product visually becomes VedAnvaya. Everything after it is mechanical.

### Step 2 — Fonts

1. Swap `layout.tsx:9–15` to Fraunces / Inter / Noto Serif Devanagari / Noto Sans Devanagari, keeping `display: "swap"` and adding the two Devanagari variables.
2. Point `--va-font-*` at them.
3. Set `html { font-size: 16px }` (up from the unlabelled `15px` at `globals.css:79`) and **scale the old rem values in one mechanical pass** (`× 0.9375`) so nothing visually jumps — or accept the 6.7 % uplift deliberately and re-run the overflow report.

**Gate:** `release-closure.spec.ts:38` asserts `.knowledge-status strong` has the same computed `font-size` on two different pages — it will still pass. The 44×44 target tests at `:9` and `:51` are the real risk; re-run at all three viewports.

### Step 3 — Primitives, one at a time, in dependency order

For each primitive: build the component with token-only CSS in `primitives.css`, swap call sites, delete the superseded blocks from `globals.css`, run the gates, commit.

| Order | Primitive | Retires from `globals.css` | Call sites |
| --- | --- | --- | --- |
| 1 | `Eyebrow` | 21 verbatim blocks (§1.6) | ~50 |
| 2 | `Card` | ~30 card selectors | ~30 |
| 3 | `Stack` / `Cluster` / `CardGrid` | 20 grid definitions (§4 #7) | ~40 |
| 4 | `Chip` / `Badge` | 11 pill families | ~25 |
| 5 | `Callout` (absorbs `Caveat`) | `.caveat*`, `.caveat-text`, `.ask-caveats`, `.transmission-note`, `.limit-alternative`, `.scope-warning`, `.panel-note` | 99 `Caveat` refs |
| 6 | `Disclosure` | 11 `<details>` skins | 13 |
| 7 | `DescriptionList` / `ProvenanceBlock` | 6 label-column widths | 11 |
| 8 | `SectionHeader` | `.section-heading` + 9 variants | ~20 |
| 9 | `Prose` / `Sanskrit` | `.sanskrit`, `.devanagari`, `.ask-prose`, `.translation-section`, 11 `ch` measures | ~25 |
| 10 | `DataTable` + `ScrollShadow` | 4 table skins + `.matrix-wrap` | 4 |
| 11 | `Drawer` | duplicated drawer chrome in two components | 2 |
| 12 | `Metric` / `MetricStrip` | 7 big-number treatments | ~10 |
| 13 | `Skeleton` | 16 inline `style` objects | 4 files |
| 14 | `StickyRail` | `.reader-aside` + `.sticky-aside` (identical) | 3 |

**Rule for every step:** the primitive's CSS may contain **no literal colour, size, space, radius, duration or z-index**. A literal is a missing token; add the token instead.

### Step 4 — Responsive rewrite, per primitive

As each primitive lands, convert its rules to **mobile-first `min-width`** and **delete its entries from the four scattered `max-width: 760px` blocks** (§1.9). The four blocks shrink to nothing rather than being rewritten in one risky pass. Introduce container queries for `.graph-detail`, `.panel`, `.veda-card`, `.comparison-column` and `.ask-retrieval-block`, which depend on their container and not the viewport.

Breakpoint tokens, replacing the 1180/1080/760/761 set:

| Token | Value |
| --- | --- |
| `--va-bp-sm` | `40rem` (640) |
| `--va-bp-md` | `48rem` (768) |
| `--va-bp-lg` | `64rem` (1024) |
| `--va-bp-xl` | `80rem` (1280) |

**Gate after every conversion:** `node tests/visual-qa.mjs` — 72 screenshots plus overflow, now exit-coded.

### Step 5 — Graph colour unification

Move `GROUP_STYLE.light/.dark` (`graph-canvas.tsx:90–133`) and the 12 hard-coded legend hexes (`globals.css:2853–2911`) to the `--va-group-*` tokens of §10.3. `buildStyle` reads them via `getComputedStyle`. `GROUP_STYLE` keeps `label`, `shape`, `size`.

**Gate:** `release-closure.spec.ts:143–196` injects all 8 groups and requires ≥4.495:1 in both themes — it will catch any regression immediately. `tests/unit/graph-semantics.test.ts:25–27` asserts `light !== dark` on the style object; that assertion must move to the shape check it already makes alongside, or be re-pointed at the CSS values.

### Step 6 — The brand rename

Only now, with the visual system settled:

1. The 12 copy strings (§8.1) and 3 metadata strings (§8.2), in one commit.
2. The 5 test assertions (§8.3) in the **same** commit.
3. Leave `VEDAGRAPH_API_URL` (§8.4) and the `VG:` prefix (§8.6) alone; add a comment at `src/lib/api.ts:58` and `next.config.ts:23` recording *why*.
4. Regenerate `src/lib/api-schema.ts` only after the backend renames its docstrings.

### Step 7 — Delete what is left

1. Remove the dead `.metric-row-grid` (5 blocks) and resolve `.caveat-boundary` / `.caveat-neutral` / `.row-primary` / `.is-resolved` / `hero-copy` / `veda-card-bottom` / `aside-status` (§1.7, §1.8) — each either gets a rule or gets deleted.
2. Remove the 12 hand-written Preflight duplicates (`globals.css:74–146`) now that Tailwind's Preflight is the single reset.
3. Remove the 12 non-reduced-motion `!important`s (§1.14) — they exist only because chips sat inside element-selector containers, which the primitives have removed.
4. Drop the unused `motion` dependency from `package.json`, or adopt it deliberately for the drawer transitions.
5. Delete `globals.css` when it reaches zero rules. **That is the completion criterion.**

### Rollback and parallelism

Every step is independently revertable because the token layer is additive (Step 1 leaves the old names working) and each primitive is a separate commit with its own gates. Steps 3.1–3.14 are independent of each other and can be parallelised across contributors. The only hard ordering constraints are: **0 before everything** (it creates the test hooks), **1 before 2–5** (tokens must exist), and **6 after 1–5** (do not mix a copy rename into a visual diff — that is how a rebrand half-lands and nobody can tell which change broke what).

### Definition of done

| Check | Target |
| --- | --- |
| `src/app/globals.css` | deleted |
| Literal colour/size/space values in `src/styles/primitives.css` | 0 |
| Distinct font sizes | 9 + 3 reading |
| Distinct spacing values | 12 |
| Distinct durations | 4 |
| `z-index` numerals outside the ladder | 0 |
| `!important` outside `prefers-reduced-motion` | 0 |
| Class selectors asserted in `tests/` | 0 (all `data-component`) |
| Contrast failures, both themes, 3 viewports | 0 |
| `visual-qa.mjs` overflow findings | 0, exit-coded |
| Unguarded JS motion | 0 |
| "VedaGraph" in user-facing copy or metadata | 0 |
| `VEDAGRAPH_API_URL` / `VG:` occurrences | unchanged |

---

*End of audit. Read-only: no source file under `D:\VedaGraph\frontend` was modified.*

---

## Appendix A — Concurrent additions not covered by this audit

While this audit was in progress, a parallel workstream added untracked files under
`frontend/public/brand/` (texture and mark assets: `field-*`, `footer-*`, `hero-*`,
`inquiry-*` in `.avif`/`.webp` at 960/1120/1280/1920) and an empty
`frontend/src/components/brand/` directory. **These were not present at the start of this
audit and are not analysed above.** Every count, line number and inventory in this document
describes the tree at `5c268d1` plus `globals.css` as read. Re-check §2 (component tree) and
§4 (idioms) against `src/components/brand/` once that work lands.
