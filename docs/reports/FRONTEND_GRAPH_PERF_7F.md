# Frontend graph performance — Phase 7F closure

Measured after the Knowledge World rebuild, against `FRONTEND_GRAPH_PERF_BASELINE.md` (taken at
`75e5efb`, immediately before it). Same machine, same GPU, same production-build-and-`next start`
arrangement. Read the caveats: two of these rows are **not** comparable to the baseline's, and it
is said where.

## Environment

| | |
|---|---|
| OS / CPU / GPU | Windows 11, 12th Gen Intel Core i5-1240P, Intel Iris Xe |
| GL renderer | `ANGLE (Intel, Intel(R) Iris(R) Xe Graphics (0x000046A6) Direct3D11 vs_5_0 ps_5_0, D3D11)` |
| Software rasteriser | no — verified hardware, so 3D figures are real and not a floor |
| Browser | Microsoft Edge (installed channel). Playwright's own Chromium could not be downloaded in this environment. |
| Server | `next start` on a clean `pnpm build`, port 3100 |

## The curated Focus, against the whole adjacency

Indra, degree 7,347, is the decisive case: the redesign's premise was that drawing a hub's whole
adjacency is what makes Focus expensive.

| | before (75e5efb) | after | |
|---|---|---|---|
| nodes submitted | 35,370 | **41** | the curated set, plus the root |
| edges submitted | 31,347 | **68** | 40 spokes and 28 bounded neighbour-to-neighbour lines |
| relationship labels shown | 8 phrases | 10 phrases + 8 names, 0 overlapping | at the desktop cap |
| frame interval, idle | 16.7 ms (60 fps) | **16.7 ms (60 fps)** | vsync-capped in both, so this row cannot show the gain |
| frame interval, orbiting | 16.7 ms, max 66.4 | **16.7 ms, max 17.3** | the tail is what moved: 66.4 → 17.3 ms |
| hover pick | 0.0 median / 0.7 p95 | **0.0 median / 0.1 p95 / 0.4 max** | |
| selection | 12.1 ms synchronous | **0.3 ms** | |
| JS heap | 27.5 MB | 32.1 MB | higher: the curation, the local field and the label layout are all new allocations |

The frame *interval* cannot improve past vsync, which the baseline says plainly and which is why
it recorded a separate forced-render draw cost. The comparable claim here is the **maximum**: an
orbit's worst frame went from 66.4 ms — a visible hitch — to 17.3 ms, which is one frame.

### World, both renderers

| | before | after |
|---|---|---|
| World 3D, idle / orbiting | 16.7 / 16.7 ms | 16.7 / 16.7 ms, max 17.0 |
| World 3D hover pick | — | 0.1 median, 0.8 p95, 2.1 max |
| **World 2D, frame median** | **49.9 ms (20 fps)** | **16.7 ms (60 fps)** |
| Focus 2D, frame median | 16.7 ms | 16.7 ms, max 17.3 |

World 2D was the slowest thing the baseline measured, in the renderer that exists for weak
devices: `draw()` ran unconditionally after the sleep guard, so the guard stopped the simulation
and never the draw. It now holds 60.

## Relationship labels

Paired measurement at the same camera, 0 labels against 16:

```
cap  0 (1 placed)   median 16.7 ms   p95 16.9   max 17.0
cap 16 (16 placed)  median 16.7 ms   p95 16.9   max 17.1
paired delta 0.000 ms over 15 placed labels  =>  0 ms per label per frame
```

Shown against attempted, with overlap counted at every cap:

| cap | shown | phrases | names | overlapping pairs |
|---|---|---|---|---|
| 2 | 2 | 1 | 1 | **0** |
| 4 | 4 | 3 | 1 | **0** |
| 5 | 5 | 3 | 2 | **0** |
| 6 | 6 | 4 | 2 | **0** |
| 10 | 10 | 8 | 2 | **0** |
| 16 | 16 | 8 | 8 | **0** |
| 24 | 23 | 8 | 15 | **0** |

The baseline's caution stands and is worth repeating: with a forced synchronous style flush the
per-label cost becomes 0.6 ms at sixteen, a fortyfold cliff. Nothing introduces one today.

## Homepage teaser

**These figures are not comparable to the baseline's absolute values.** The baseline's harness ran
its own `requestAnimationFrame` loop in the page to sample frame intervals — it reports 301 rAF
callbacks per 5 s in *every* state including its static-route floor — and that loop is most of its
~105 ms floor. `scripts/bench-home.mjs` runs no such loop. The rows below are comparable to each
other; the cross-document comparison worth making is the *shape*, not the magnitude.

Three repetitions of a 5,000 ms window, median (min–max):

| | before (different instrument) | after |
|---|---|---|
| LCP | 252 ms (220–268) | **200 ms (196–372)** |
| FCP | 232 ms | **200 ms** |
| CLS | 0 | **0** |
| TaskDuration, visible | 204 ms (136–255) | 245 ms (225–273) |
| TaskDuration, **offscreen** | 122 ms (115–123) | **5.9 ms (5.8–6.4)** |
| TaskDuration, floor | 105 ms (73–134) | 89 ms (83–90), `/vedas/rigveda` |
| ScriptDuration, visible | 61.6 ms | 99.6 ms |
| ScriptDuration, **offscreen** | 15.3 ms | **1.1 ms** |
| frames drawn, visible | — | 150 per 5 s (a 30 fps cap) |
| frames drawn, **offscreen** | — | **0**, and the engine reports paused |
| reduced motion, 3 s idle | 89 frames | **0 frames**, and it parks |

Read carefully, three things happened:

- **Offscreen is now approximately zero on either metric** — 5.9 ms of task time and 1.1 ms of
  script time per 5 s, with *zero* frames drawn. The loop cancels its `requestAnimationFrame`
  rather than waking to read a flag, which is the only version of this that the frame counter can
  distinguish.
- **Reduced motion parks too.** This was found in this phase's own measurement, not by a test: the
  end-to-end assertion for that setting checks that nothing *moves*, and nothing did, while the
  renderer redrew an identical picture 30 times a second. A pointer wakes it and it sleeps again
  600 ms after the pointer leaves.
- **Visible cost rose**, by about 40 ms of task time and 38 ms of script time per 5 s against a
  floor that is itself 16 ms lower. The teaser is doing more: it classifies gestures, holds a local
  selection, fetches the relationship vocabulary on first hover and places four names. It is
  within the baseline's own measured range (136–255 ms) but above its median. Named as a residual
  rather than explained away — a decomposition would need an instrument that can attribute task
  time to the hero rather than to the page.

## Bundle

Per-route JavaScript, summed from the on-disk uncompressed size of every `/_next/static/**.js`
referenced by each prerendered route, which is how the baseline derived it.

| route | before | after |
|---|---|---|
| `/` | 639.6 KB | **639.6 KB** — byte-identical |
| `/graph` | 1,244.5 KB | 1,310.0 KB (+65.5, +5.3%) |
| `/vedas/[veda]` | 623.6 KB | 623.6 KB |

The homepage did not grow at all. `/graph` grew by 5.3% for `focus.ts`, `focus-layout.ts`,
`local-physics.ts`, `transition.ts` and `gesture.ts`.

## Artifact transfer

Unchanged, and the residual recorded in `next.config.ts` still stands: `world.bin` is served
uncompressed because Next skips `application/octet-stream`.

| file | transfer | time |
|---|---|---|
| `world.bin` | 2,435.5 KB | 71–77 ms |
| `world.labels.json` | 413.3 KB | 60–86 ms |
| `world.json` | 6.2 KB | 5.5 ms |
| `world.predicates.json` | 5.3 KB | 3.4 ms |

Immutable caching and `Vary: Accept-Encoding` are set; gzip -9 would take `world.bin` to 966 KB
and brotli to 808 KB, and neither is reachable through Next's own compression.

## Colour, measured from pixels

`tests/e2e/graph-palette.spec.ts` predicts each fragment of Indra's orb from the CSS tokens plus
the renderer's declared depth cues — linear fill, key mix, fog mix, sRGB encode, encoded-space
blend — and compares it against a screenshot.

| | light | dark |
|---|---|---|
| fog at the Focus framing | 0.0478 towards the page | 0.2472 |
| key light | 0.18 towards black, unlit side | 0.18 towards white, lit side |
| best pixel, shadowed band | `#ad5f45` against `#ad5f45` | `#b7685b` against `#b7685b` |
| best pixel, lit band | `#b56246` against `#b56246` | `#bd827a` against `#bd827a` |
| 25th percentile, worst band | ΔE00 0.28 | ΔE00 0.42 |
| an unencoded write would read | ΔE00 20.7 | ΔE00 21.0 |

The defect this guards — a shader writing linear values into an sRGB framebuffer — would read
about fifty times the tolerance. There is no flat patch on a curated orb to sample: it is a shaded
hemisphere, it is fogged, and its own spoke fan is drawn over the middle of it.
