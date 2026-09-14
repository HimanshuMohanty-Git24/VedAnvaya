# Frontend graph performance baseline

Measured at `75e5efb`, immediately before the Phase 7F FOCUS redesign. Raw data, per-repetition
values, spreads and eighteen documented methods are in
[`FRONTEND_GRAPH_PERF_BASELINE_75e5efb.json`](./FRONTEND_GRAPH_PERF_BASELINE_75e5efb.json).

This is the project's first committed frontend performance baseline. It exists because every row
in it is a diff target for an "after" run, and because a measurement held only in a session's
scratch directory is a measurement nobody can check.

## Provenance, and its limits

Every figure comes from `next start` serving a `.next` built from a tree git reported clean at
`75e5efb`. `next start` does not recompile, so later source edits could not reach the served
bundle. The figures are valid for that build and no other.

The tree was then edited by nine agents sharing one `.next`, and a rebuild replaced it under the
running server partway through. Runs attempted after that point were discarded rather than
reported. Anything that could not be measured is listed in the JSON's `couldNotMeasure` block
with the reason, rather than estimated.

**An "after" run needs an uncontended tree.** A shared build directory across a parallel wave
makes any timing unrepeatable.

## The finding that matters most

The redesign's premise was that drawing a hub's whole adjacency is what makes FOCUS expensive.
It is not. Decomposed by toggling `Object3D.visible` per scene object with the camera unmoved,
thirty `gl.finish()`-fenced renders each, three repetitions, on Indra FOCUS 3D:

| object | ms | share, net of floor |
|---|---|---|
| whole scene | 5.9 | |
| empty scene (floor) | 0.6 | |
| node cloud, 35,370 points | 0.7 | 2% |
| **world backbone, 24,000 lines** | **4.7** | **77%** |
| selection overlay, 7,347 lines | 1.8 | 23% |

Cutting a hub's 7,347 edges to a curated few dozen recovers roughly **1.2 ms of 5.3**. The
curation is still the right change: it is the fix for the legibility complaint that prompted the
phase, and that was always its purpose. But the frame-time win lives in `applyEdgeRange()`, which
holds the full `WORLD_EDGE_BUDGET` of 24,000 whether or not a subject is selected.

Pinned closer, at 700 units, the split widens to 23.9 against 6.1.

## Three hypotheses tested and rejected

Recorded so that a later optimisation does not chase them.

**Selection cost does not scale with degree.** `select()` costs 1.8 ms at degree 1 and 3.0 ms at
degree 7,347. The floor is the full-graph alpha rewrite — 185,693 edges at 0.7 ms, 35,370 nodes
at 0.5 ms — plus 1.48 MB of `edgeAlpha` re-uploaded to the GPU on every selection regardless of
what was selected. That upload is the target, not the neighbour count.

**The label pipeline does not thrash layout.** CDP `LayoutCount` is 2 per 2 s; the per-frame
writes are `transform` and `opacity`.

**Indra is not the worst 3D case.** Indra FOCUS draws at 5.9 ms. Sarasvati, at degree 298, draws
at **8.2 ms with 7,049 fewer lines**, because `focusNode` frames a smaller neighbourhood closer
and every line then spans more of the viewport. The scene is fill-rate bound: screen coverage is
the variable, not edge count. A stress test chosen by degree alone picks the wrong subject.

## Headline rows

3D frame interval is vsync-capped at 16.7 ms in every case on this GPU, so `drawCost` is the
comparable figure and frame time cannot show an improvement.

| | nodes | edges | draw ms | task ms/2s | heap MB |
|---|---|---|---|---|---|
| WORLD 3D | 35,370 | 24,000 | 3.1 | 115 | 26.2 |
| Indra FOCUS 3D | 35,370 | 31,347 | 5.8 | 227 | 27.5 |
| Sarasvati FOCUS 3D | 35,370 | 24,298 | 7.8 | 222 | 30.9 |

| | nodes | edges | repaints/s | strokes/repaint | frame med ms |
|---|---|---|---|---|---|
| **WORLD 2D** | 2,600 | 5,200 | 22.7 | 5,472 | **49.9** |
| Indra FOCUS 2D | 84 | 487 | 60.0 | 488 | 16.7 |
| Sarasvati FOCUS 2D | 87 | 560 | 60.0 | 561 | 16.7 |

WORLD 2D holds 20 fps at rest, and is the slowest thing measured — in the renderer that exists
for weak devices. `draw()` is called unconditionally after the sleep guard, so the guard stops the
simulation and never the draw.

**Selection latency, Indra, from WORLD 3D:** 12.1 ms synchronous, first frame 14.1, panel
committed 32.6, settled 192.2. Hover pick 0.0 median, 0.7 p95.

**Relationship labels, per frame:** 0 labels 0.006 ms, 5 → 0.006, 10 → 0.010, 16 → **0.014**.
That is roughly eight times *cheaper* than the +0.109 ms recorded in an earlier commit message,
which could not be reproduced from anything committed. With a forced synchronous style flush it
becomes 0.6 ms at sixteen — a fortyfold cliff if anything ever introduces one.

**Homepage:** LCP 252 ms, FCP 232, CLS 0. Main thread 204 ms/5 s visible, 122 offscreen — and the
floor for a route with no WebGL at all is 105, so "offscreen approximately zero" is unreachable
against `TaskDuration`. On `ScriptDuration` the same states read 61.6 visible, 15.3 offscreen,
13.3 floor: offscreen is about 2 ms above floor and effectively already there. Report the metric
that answers the question.

**Mobile, 390x844, CPU throttled 4x:** `probeCapability` returns `FULL_3D`, so a phone opens in
3D. FOCUS 3D median 33.2 ms, p95 83.2, max 133.5. FOCUS 2D spends **72-77% of the throttled main
thread at rest**. The GPU was not throttled — Chromium offers no lever — so the 3D figures are
optimistic.

## Hidden-renderer invariant: holds

Instrumented with three's own monotonic `info.render.frame` counter over 4 s windows.

| probe | spatial frames/s | planar repaints/s | geometries | frame counter |
|---|---|---|---|---|
| cold deep-link `renderer=2d` | 0 | 60.25 | **0** | 0 → 0 |
| switched 3d→2d in the UI | 0 | 60.0 | 3 | 403 → 403 |
| `renderer=3d` active | 60.0 | 0 | 3 | 162 → 402 |

Stronger than "stopped drawing": on a cold 2D deep link `geometries` is 0, so the paused engine
never uploaded its buffers. And the counter is continuous across the UI switch (402 → 403 → 553),
which proves the same renderer instance persists — so "kept, not drawn" holds as well.

## Build

`pnpm build` exits 0 in 158 s, of which TypeScript is 2.2 minutes.

**Next 16.3.4 with Turbopack no longer prints the per-route First Load JS table.** The figures
below were derived from each prerendered route's on-disk script references, uncompressed; quote
them with that method attached, because a reader will otherwise assume they came off the build.

| | script references | note |
|---|---|---|
| `/graph` | 1,244.5 KB | |
| `/` | 639.6 KB | gets three.js after hydration via `next/dynamic` |
| shared baseline | 619.9 KB | |
| three.js chunk | 584.8 KB | 145.2 KB over the wire, referenced only by `/graph` |

Measured transfer on `/graph`: scripts 322.4 KB wire against 1,154.3 KB decoded; world artifacts
812.9 KB wire against 4,377.5 KB decoded; **fonts 352 KB, more than the JavaScript**.

## Known residuals recorded here

- **`world.bin` is served uncompressed.** 2,493,613 bytes, no `Content-Encoding`, because the
  built-in compression skips `application/octet-stream` — while `world.labels.json` beside it
  compresses by 78%. gzip -9 reaches 966 KB, brotli 808 KB. Its `Cache-Control: max-age=0` is
  fixed in `next.config.ts`; the compression needs either build-time pre-compression or the edge,
  and is a deployment decision rather than a config line.
- **`EngineStats.drawnNodes` is a constant** (`manifest.counts.nodes`) and is rendered to readers.
  A redesign that draws forty nodes will still report 35,370.
- **`scripts/bench-world.mjs` defaults to SwiftShader unless `--gpu`**, and `capability.ts` maps a
  software renderer to FLAT and forces the planar view. The default invocation therefore cannot
  reach the 3D view. Any before/after run must pass `--gpu`.
- **A cold `renderer=2d` deep link may wait on the 3D view's entire load**, including the 1.9 MB
  label file, before the planar view first paints. Found by reading; the timing is unmeasured.
