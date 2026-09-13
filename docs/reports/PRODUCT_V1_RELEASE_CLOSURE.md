# Product V1 — release closure

Responsive QA, performance baseline and visual polish for the local release, plus the
backlog items this closure opened. Figures here are measured, not estimated; where
something could not be measured, this says so rather than reporting a pass.

---

## 1. Surfaces checked

The brief for this closure asked for "12 required surfaces". No such list exists in this
repository. The checked-in route list (`docs/reports/FRONTEND_PRODUCT_V1_PLAN.md`) names
22 route families, and `/ask` was added after it was written. Rather than guess which
twelve were meant, every route family was swept — 26 concrete URLs, including one
instance of each parameterised route.

`/` · `/vedas` · `/vedas/rigveda` · `/vedas/samaveda` · `/vedas/atharvaveda` ·
`/vedas/yajurveda` · `/passage/{key}` · `/reuse/{key}` · `/search` · `/devatas` ·
`/devatas/{id}` · `/entities` · `/entities/{type}` · `/entities/{type}/{id}` · `/rituals` ·
`/rituals/{id}` · `/formulas` · `/formula-families/{id}` · `/connections` · `/explore` ·
`/explore/atharvaveda` · `/material-culture` · `/insights` · `/limits` · `/graph` · `/ask`

Matrix: 26 routes × 3 viewports (1440 / 1024 / 390) × 2 themes = **156 measurements**.

---

## 2. Responsive QA (§33)

Each measurement recorded page-level overflow, per-element overflow with a check for
whether a scrollable ancestor exists, controls below the WCAG 2.5.8 floor, sticky and
fixed elements, heading count, and text contrast against the background actually painted
behind it.

### After the fixes in this closure

| Check | Result across 156 measurements |
|---|---|
| Page-level horizontal overflow | **0** |
| Clipped content (overflow with no scrollable ancestor) | **0** |
| Controls below the 24px AA floor | **0** |
| Text failing its contrast requirement | **0** |
| Load or render errors | **0** |

Three elements overflow their viewport by design and were confirmed to sit inside
`overflow-x: auto` regions rather than being clipped: `.connection-matrix` and
`.material-table` inside `.matrix-wrap`, and the reader's `.tab-list`.

### Interactive states

Checked separately, since a static sweep only sees a loaded page.

| State | Result |
|---|---|
| Empty state (`/search?q=…` matching nothing) | Correct copy — "Nothing matched …", and explicitly says the texts may still use the idea under another word rather than implying corpus absence. No layout defect at any width. |
| Dialog (graph evidence drawer) | Opens from a relationship row, fits the viewport (560px at 1440, full-width at 390), does not overflow, receives focus, closes on Escape. |
| Keyboard focus | Visible at every stop. The Ask textarea suppresses its own outline and indicates focus on its wrapper (`--line` → `--accent`), consistent with `.search-field` and the graph toolbar. |
| Sticky / fixed | `.site-header` and `.skip-link` on every route; `.sticky-aside` / `.reader-aside` where applicable. No overlap defects. |
| Long Sanskrit, provenance labels | Reader page renders accented IAST without overflow at 390px; source and recension labels intact. |

### Defects found and fixed

| Defect | Where | Fix |
|---|---|---|
| Expand buttons 19×19px | Every `/vedas/{veda}` hierarchy | 44px floor on `.tree-row` controls and labels |
| Seek slider 22px tall; speed select and play button under floor | Reader audio player | 44px on `.recitation-seek`, `.recitation-speed select`, `.recitation-play` |
| Graph search input 23.5px — the page's only entry point | `/graph` | Pill carries a 44px min-height; input stretches to fill it |
| Six of eight legend colours below 4.5:1 at 12.6px | `/graph` | Darkened along their own hue; node colours untouched |
| Retrieval-mode explanation truncated inside the option text | `/ask` | Note moved beside the control, wired as its accessible description |
| `10,502 / 10,552` translations rounded to "100%" | `/vedas` | Reads 99.5% |
| Pending copy claimed Ask "normally takes three to ten seconds" | `/ask` | Claim dropped; measured range is 29.7–248.7s |

Two of the six legend colours (`group-person`, `group-wording`) render nothing at the
default graph root. Reading only the rendered chips would have certified colours that were
never on screen, so the regression test builds a chip of every class rather than sampling
what one neighbourhood happens to draw.

### Deliberately not changed

`--faint` and `--muted` have converged in the light theme (`#5f6b70` vs `#5b686d`) as the
cost of meeting AA; the tokens are now near-identical and the hierarchy they once carried
rests on size, weight and letter-spacing instead. Consolidating them is a design-system
decision, not a release fix — **`UI_BL_01`**.

---

## 3. Performance (§35)

Measured against the **production build** (`next start`), not the dev server. Four samples
per route: the first is cold, the warm figure is the median of the rest.

### Routes — no regression

All 34 endpoints returned 200.

| Layer | Warm range | Slowest |
|---|---|---|
| 26 product routes | 3.2 – 69.3 ms | `/graph` 69.3 ms |
| 8 API routes | 2.4 – 261.7 ms | `/api/v1/stats` 261.7 ms |

Cold first-render ranges 25–709 ms and is a one-time cost per route per server start.
This is consistent with the previously recorded baseline (slowest non-Ask ≈234 ms) and
shows no regression from the changes in this closure.

#### One latency test fails in the full suite and only there

`TestLivePerformance::test_median_latency[neighbourhood depth 2 (aggregate-class)]` holds
`/api/v1/graph/neighborhood/{INDRA}?depth=2` to a 400 ms median. Observed:

| Condition | Result |
|---|---|
| Full suite, product running | 850 ms — **fail** |
| Full suite, product stopped | 817 ms — **fail** |
| Full suite, earlier run today | pass |
| Isolated, 8 consecutive runs | pass, 8/8 |
| Isolated, with coverage enabled | pass |
| Live API server, 4 samples | **186.6 ms cold, 183.3 ms warm** |

The endpoint a reader actually reaches is comfortably inside the budget; only the
in-process `TestClient` measurement taken partway through a full run is not, and a median
of five requests at 817 ms means at least three of the five were slow, so it is not one
cold cache miss. The same test failed in the session before this one, at 802 ms, and no
file under `src/` was changed by this closure — `git diff --name-only 6c28190..HEAD -- src/`
is empty — so this is pre-existing and cannot be a regression from the work here.

It was **not** made to pass. Raising the budget or adding a warm-up would convert a
measurement into a formality, and the honest state is that this gate is red. Recorded as
**`TEST_BL_01`**.

### Ask — the wait is entirely the provider

Measured on the reader's real path (browser → Next rewrite → API) and directly against the
API, two repeats of three questions each.

All 12 requests returned 200.

| | Min | Median | Max |
|---|---|---|---|
| End-to-end, all 12 | 29.7 s | 106.4 s | 248.7 s |
| End-to-end, over the rewrite (n=6) | — | 141.5 s | 248.7 s |
| End-to-end, direct to the API (n=6) | — | 60.3 s | 113.3 s |
| `planner_ms` | 0.0 | 0.0 | 0.0 |
| `retrieval_ms` | **78 ms** | — | **1,141 ms** |
| `synthesis_ms` | 29,531 ms | — | 248,000 ms |

Retrieval — everything VedaGraph itself does — is at most 1.2 seconds, and the planner is
deterministic rather than a model call. **Between 98.75% and 99.91% of every measured wait
was the LLM provider**, currently a free-tier 550B model on OpenRouter. There is no
VedaGraph-side latency problem to optimise, so no optimisation was attempted. The provider
is env-configurable and this is **`PERF_BACKLOG_01`** (below).

There is no first-token measurement because the route does not stream; a single JSON
document means headers and body complete within milliseconds of each other. Streaming is
already `ASK_BL_04`.

#### The proxy ceiling was the release-blocking part

All six requests over the rewrite returned 200 — but **four of the six took longer than the
120 s ceiling that was configured before this closure** (132.1 s, 151.0 s, 180.3 s,
248.7 s). Under that ceiling Next would have cut the socket and answered 500, and the UI
would have rendered "The VedaGraph knowledge service could not be reached" for a backend
that was answering correctly, on two thirds of the sample.

That those four now return 200 is also the proof the new ceiling is live: `next start`
reads `next.config.ts` at startup, and no request over 120 s could have completed
otherwise. The backend's own worst case is 330 s — `(3 + 1) × 60 s` of attempts plus
`3 × 30 s` of capped backoff — and `tests/product/test_ask_proxy_ceiling.py` derives that
bound from the settings so the two halves cannot drift apart unnoticed.

### Audio start

Ten attempts across the five spot-check verses, production build.

| Layer | Result |
|---|---|
| API lookup (`/passages/{key}/audio`) | 12 – 42 ms, median 18 ms |
| Click → `playing`, upstream already fetched | 42 – 70 ms |
| Click → `playing`, first fetch from VedSearch | 1,619 – 2,499 ms |
| Attempts reaching `playing` | 10 / 10 |

**Limitation.** `playing` establishes that the element began playback of decoded audio. It
does not establish that a human would hear the right recitation, and a headless browser has
no audio output. See §5.

Reported duration was checked separately after an earlier probe showed 728s for a 42s clip:
across six trials on the production build every verse reported one stable duration
(15.18 s / 41.84 s / 15.36 s), with a single `durationchange` matching `loadedmetadata`.
The earlier reading was an artifact of sampling the element before its stream resolved. No
defect, no change.

---

## 4. Visual polish (§32)

Restrained, and confined to the shared stylesheet rather than per-page CSS. No new design
language, no animation, no dependency, no layout rewrite.

- Touch targets raised to a single 44px floor across hierarchy, audio and graph controls.
- `--faint` darkened in light and lightened in dark so supporting text clears AA on every
  surface it is actually painted on.
- Legend colours brought to AA along their existing hues.
- `.formula-stats` no longer renders a status badge at metric scale — it uses the shared
  `.knowledge-status` typography, so a badge means the same thing on every surface.
- Ask's mode note given a real place in the layout instead of being cut off inside a
  `<select>`.

Left alone deliberately: page structure, the reading typography, the graph's node palette,
the card system, and every surface the sweep found clean.

---

## 5. Audio listening — still open

Textual verification is complete and strong: 16,834 catalogued recordings, all `EXACT`,
`text_verified`, `MANTRA`-scoped; 17/17 catalogue checks pass; 127 mappings independently
re-derived with 0 wrong and 0 unreachable.

**Nothing has been listened to.** See
[PRODUCT_V1_AUDIO_LISTENING_CHECK.md](PRODUCT_V1_AUDIO_LISTENING_CHECK.md) for the sample,
which is loaded at the Vālakhilya boundary where a mapping error is silent rather than
loud. The mapping for the critical case is confirmed on paper —
`VG:RV:SAK:M08:S071:V001` → VedSearch `8.60.1`, and `VG:RV:SAK:M08:S048:V001` → `8.48.1`
unshifted — but confirmed on paper is not confirmed by ear.

---

## 6. Backlog opened or carried by this closure

| Id | Item |
|---|---|
| `PERF_BACKLOG_01` | **Ask latency is provider-bound: 29.7–248.7s end-to-end, of which ≤1.2s is VedaGraph.** Not a retrieval or graph problem. Addressed by choosing a faster provider (Groq is already supported and configured by env alone), by `ASK_BL_04` streaming so the reader sees progress, or by lowering `VEDAGRAPH_LLM_MAX_RETRIES`. If either LLM setting changes, `frontend/next.config.ts`'s `proxyTimeout` must still exceed `(retries + 1) × timeout + retries × 30s`; `tests/product/test_ask_proxy_ceiling.py` enforces this. |
| `UI_BL_01` | **`--faint` and `--muted` have converged in the light theme.** Meeting AA left the two tokens near-identical. Either consolidate them or re-establish the step on a surface that can carry it. |
| `TEST_BL_01` | **`TestLivePerformance` depth-2 median fails inside the full suite and nowhere else** — 817–850 ms in a full run, 8/8 pass isolated, 183–210 ms against the live API server. Pre-existing; it failed at 802 ms before this closure and no `src/` file changed here. Diagnose why the in-process `TestClient` path degrades partway through a run before touching the budget. Do not raise the number to clear it. |

`ASK_BL_11` (ruff format drift) is **closed** by this closure. `TEST_BL_01` is why the
backend suite gate is red and why this closure does not promote the release label. `ASK_BL_08`, `ASK_BL_13`,
`ASK_BL_01`, `ASK_BL_03`, `ASK_BL_04`, `ASK_BL_05`, `ASK_BL_07`, `ASK_BL_09`, `ASK_BL_10`
and `ASK_BL_12` remain post-V1 and were not touched.

---

## 7. Method note

Three findings in this closure were measurement artifacts, not defects, and each was
withdrawn only after being checked against the running product:

1. **Dark-theme contrast failures on `/` and `/ask`.** Several surfaces transition
   `background` over 0.16s. Sampling straight after the theme class flips reads the
   half-way colour. With the transition settled, both pages are clean.
2. **The Ask textarea having no focus indicator.** The indicator is on the wrapper via
   `:focus-within`, not on the focused element, and the same transition delay applied.
3. **A 728s duration on a 42s recitation.** Not reproducible over six production trials.

A fourth, `--faint` failing on `--surface-strong`, was a token-pair assertion for a pairing
that does not occur in the DOM. The regression test now measures the background actually
painted behind the text, which is why it caught the graph legend — a real failure no
token-pair list would have named.
