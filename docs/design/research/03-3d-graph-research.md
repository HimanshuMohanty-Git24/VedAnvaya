# 3D Knowledge Graph Technology Research — VedAnvaya

**Agent 3 · researched 2026-09-13 · every version, date and licence below was read from the
npm registry, the GitHub API or library source on that day, not from memory.**

---

## 0. The finding that changes the question

The brief frames this as "how do we render 100,780 nodes and 242,147 relationships in a
browser". Two measurements in this repository say that is the wrong question, and getting
this wrong would cost weeks.

**First: the live API can never hand us a big graph.** `GraphService` caps a neighbourhood
at `NEIGHBOURHOOD_NODE_BUDGET = 400` nodes
(`src/vedagraph/api/services/graph_service.py:395`), `NEIGHBOURHOOD_MAX_DEPTH = 2` (`:390`),
`MAX_NEIGHBOURS_PER_TYPE = 50` (`src/vedagraph/api/config.py:33`), and paths are bounded at
`PATH_MAX_DEPTH` with a `HUB_DEGREE_CEILING = 200` on waypoint ranking (`:375`). So the
**focused view and the path view are 400-node and ~10-node problems.** Cytoscape already
renders them. Nothing in this report is needed to make them work; 3D there is a *design*
choice, not a performance one.

**Second: the graph is not 100k interesting nodes — it is about 1,060.** From the V3
baseline audit (`docs/reports/KNOWLEDGE_MODEL_V3_BASELINE_AUDIT.md:84-100`), the populated
node labels are:

| stratum | labels | nodes |
|---|---|---|
| infrastructure (never drawn) | `Internal` 62,483 · `TextVersion` 44,276 · `Translation` 17,283 · `QAIssue` 915 | — |
| text | `Passage` 22,537 · `Mantra` 20,210 | ~22.5k |
| lexical (internal) | `Lemma` 10,031 | 10k |
| diction | `Formula` 4,825 (+ `FormulaFamily`) | ~4.8k |
| **the entity layer** | `Rishi` 367 · `Devata` 214 · `Concept` 163 · `DerivedMetric` 79 · `Chandas` 34 · `DeityAxis` 22 · `Object` 19 · `Epithet` 13 · `NaturalPhenomenon` 13 · `Plant` 13 · `Animal` 12 · `Condition` 12 · `PhilosophicalConcept` 11 · `Place` 10 · `Substance` 10 · `River` 7 · `InterpretiveClaim` 6 · `Action` 5 · `Metal` 5 · `RitualRole` 5 · `Tribe` 5 · `Crop` 5 · `CosmicEntity` 4 · `HumanConcern` 4 · `Ritual` 4 · `SocialRite` 4 · `Work` 4 · `Quality` 3 · `State` 3 · `Weapon` 3 · `DeityGroup` 2 · `Offering` 2 | **≈ 1,060** |

And the edges that connect *entities to each other* — the ones a World View draws — are
tiny: `HAS_AXIS` 289, `DEVATA_ASSOCIATED_WITH` 140, `BROADER_THAN` 57, `PRAISES` 38,
`COMPOSED_OF` 28, `HAS_EPITHET` 13, `MEMBER_OF` 13 and so on
(`KNOWLEDGE_MODEL_V3_BASELINE_AUDIT.md:104-121`). The 240k figure is almost entirely
`ABOUT_CONCEPT` 47,542, `MENTIONS_ENTITY` 37,675, `HAS_TEXT_VERSION` 44,276, `USES_FORMULA`
22,686, `CONTAINS` 22,537 — **passage-to-thing edges and containment**, i.e. exactly the
edges the path endpoint already excludes by name because "they connect nearly everything to
nearly everything, so a path through them is true and meaningless"
(`src/vedagraph/api/routes/graph.py`, `_PATH_DESCRIPTION`).

So the honest statement of the problem is:

> A World View of the **entity layer** is a ~1,060-node / ~600-edge scene. That is a *small*
> 3D scene — it holds 60 fps on a phone with no instancing at all. The hard engineering only
> appears if we also choose to show the 22,537-passage stratum, and that must be a
> deliberate second LOD tier, not an assumption.

Everything below is written against that: **build for 1k–6k nodes with headroom to 30k**,
not for 100k. Building the 100k machine first is the expensive mistake.

One correction to the brief: the README states the frozen graph at **108,779 nodes /
265,295 relationships** (`README.md:71`); 100,780 / 242,147 is the V2/V3 *baseline audit*
snapshot. Both are cited above where each is the source. Neither changes the conclusion.

---

## 1. Verified package facts

Read from `registry.npmjs.org` and the GitHub API on **2026-09-13**.

| package | latest | published | licence | constraints that matter |
|---|---|---|---|---|
| `three` | **0.186.0** | 2026-09-08 | MIT | ESM, `"type": "module"` |
| `@react-three/fiber` | **9.7.0** | 2026-07-31 | MIT | `react: >=19 <19.3`, `react-dom: >=19 <19.3`, `three: >=0.156` |
| `@react-three/drei` | **10.7.8** | 2026-08-05 | MIT | `react: ^19`, `@react-three/fiber: ^9.0.0`, `three: >=0.159` |
| `camera-controls` | 3.1.2 | 2025-11-17 | MIT | drei dependency |
| `troika-three-text` | 0.52.5 | 2026-07-24 | MIT | drei dependency; powers drei `<Text>` |
| `three-mesh-bvh` | 0.9.15 | 2026-09-09 | MIT | drei dependency; powers drei `<Bvh>` |
| `react-force-graph-3d` | 1.29.1 | 2026-02-04 | MIT | `peerDependencies: { react: "*" }` — **no React version is asserted at all** |
| `react-kapsule` | 2.6.0 | 2026-06-17 | MIT | `react: >=16.13.1` |
| `3d-force-graph` | 1.80.0 | 2026-04-05 | MIT | **`three` is a hard `dependency` at `>=0.179 <1`**, not a peer |
| `three-forcegraph` | 1.43.4 | 2026-04-16 | MIT | `peerDependencies: { three: ">=0.118.3" }` — correct, peer not dep |
| `sigma` | 3.0.3 | 2026-04-30 | MIT | deps: `events`, `graphology-utils` only |
| `graphology` | 0.26.0 | 2025-01-26 | MIT | |
| `graphology-layout-forceatlas2` | 0.10.1 | **2022-10-17** | MIT | **2D only** (`x`,`y`); ships `/worker` + `/webworker` |
| `d3-force-3d` | 3.0.6 | 2025-04-09 | MIT | `numDimensions: 1｜2｜3`; `d3-octree` Barnes-Hut |
| `ngraph.forcelayout` | 3.3.1 | **2022-10-04** | BSD-3-Clause | `{dimensions: 3}` and higher; quadtree/octree |
| `ngraph.graph` | 20.1.2 | 2026-02-14 | BSD-3-Clause | |
| `@cosmograph/cosmos` | 3.4.1 | — | **CC-BY-NC-4.0** | **non-commercial only** |
| `deck.gl` | 9.4.0 | 2026-09-05 | MIT | |
| `@deck.gl-community/graph-layers` | 9.4.1 | 2026-09-08 | MIT | README body is literally `TBD` |
| `three-text` (countertype) | 0.6.5 | 2026-07-04 | MIT | **self-declared alpha**; `harfbuzzjs` dep |
| `cytoscape` (shipping today) | 3.34.3 | — | MIT | |

Repository health (GitHub API, same day):

| repo | last push | stars | open issues | archived |
|---|---|---|---|---|
| `pmndrs/react-three-fiber` | 9.7.x stable; **10.0 is alpha** as of Sep 2026 | — | — | no |
| `protectwise/troika` | 2026-07-24 (`v0.53.0`) | 1,969 | 92 | no |
| `vasturiano/react-force-graph` | 2026-02-04 | 3,297 | **218** | no |
| `visgl/deck.gl-community` | 2026-09-11 | 101 | 53 | no |
| `yomotsu/camera-controls` | 2026-09-09 | 2,424 | — | no |

### Bundle cost

Two sources: bundlephobia (min / gzip of the public entry) where it answered, and raw
published dist bytes from jsDelivr where it rate-limited. Raw dist bytes are **not** gzip —
divide by roughly 3.2 for a realistic gzip estimate.

| package | minified | gzip | note |
|---|---|---|---|
| `three@0.186.0` | 719.0 KB | **180.6 KB** | full-namespace import. A graph scene tree-shakes to roughly 150 KB gz — `WebGLRenderer` is the bulk and is indivisible, so tree-shaking saves far less than people assume. |
| `@react-three/fiber@9.7.0` | 159.5 KB | **50.6 KB** | 10 transitive deps (zustand, its-fine, scheduler, buffer, base64-js, …) |
| `@react-three/drei@10.7.8` | 1,575.6 KB | **488.2 KB** | the **whole barrel**. `sideEffects: false`, so named imports do tree-shake — but the barrel drags `@mediapipe/tasks-vision`, `hls.js`, `three-stdlib`, `troika-three-text`, `three-mesh-bvh`. Import narrowly and verify with a bundle analyser; do not take 488 KB on faith either way. |
| `react-force-graph-3d@1.29.1` | entry `.mjs` is 7 KB; published UMD **1,285 KB min** | ~400 KB | the UMD is the honest all-in figure: it bundles `three`, `three-forcegraph`, `three-render-objects`, `d3-force-3d`, `ngraph.*`, `d3-scale-chromatic`, `tinycolor2` |
| `3d-force-graph@1.80.0` | 1,283 KB min (UMD) | ~400 KB | same closure |
| `three-forcegraph@1.43.4` | 108 KB min / 61 KB ESM | ~35 KB | **excludes three** (correct peer dep) |
| `sigma@3.0.3` | 183 KB min / 128 KB ESM | ~48 KB | + `graphology` ~20 KB gz |
| `cytoscape@3.34.3` | 425 KB min | ~130 KB | **already paid today** |
| `troika-three-text@0.52.5` | 89 KB min | ~32 KB | + a 36 KB `typr.factory.js` fetched into a worker at runtime |
| `three-text@0.6.5` | — | — | npm tarball unpacks to **52.7 MB**; runtime additionally needs a self-hosted `hb.wasm` |

**Baseline for the decision:** `three` + R3F is ~**200 KB gzip** before a single graph
library. Cytoscape, shipping today, is ~130 KB gzip. So 3D is roughly **+70 KB gzip net** if
it *replaces* Cytoscape, or **+200 KB** if it runs alongside it.

---

## 2. Library comparison and verdicts

### 2.1 Recommendation table

| library | verdict | why | bundle |
|---|---|---|---|
| **`three@0.186`** | **ADOPT** | The only realistic WebGL substrate. Active (published 5 days before this research). Pin the exact version. | ~150–180 KB gz |
| **`@react-three/fiber@9.7`** | **ADOPT** | React 19 support is *asserted in the manifest*, not inferred: `peerDependencies.react = ">=19 <19.3"`. The app is on `react@19.2.8` — inside the range. v9 is the React-19 compatibility line and it bundles its own reconciler to reach it. | 50.6 KB gz |
| **`@react-three/drei@10.7.8`** | **ADOPT, NARROWLY** | `peerDependencies`: `react: ^19`, `@react-three/fiber: ^9.0.0`. Take `CameraControls`, `Html`, `Bounds`, `AdaptiveDpr`, `PerformanceMonitor`, `Instances`. **Do not take `<Text>`** — see §2.4. | import-dependent; barrel is 488 KB gz |
| **`react-force-graph-3d@1.29.1`** | **REJECT** | Three independent reasons below. | ~400 KB gz all-in |
| **`three-forcegraph@1.43.4`** | **REJECT for us, but the honest runner-up** | Correct `three` peer dep, small (35 KB gz), maintained (2026-04-16), and usable inside R3F as `<primitive object={fg} />` without the React wrapper. Rejected because it owns the scene graph, the picking and the label strategy — and the label strategy is the thing we cannot delegate (§2.4). | ~35 KB gz + three |
| **`d3-force-3d@3.0.6`** | **ADOPT (layout)** | The only maintained true-3D force layout with a familiar API. `numDimensions: 3`, Barnes-Hut via `d3-octree`, pure JS so it runs in a worker unchanged, `alphaTarget`/`restart` give live reheat on drag. | ~15 KB gz |
| `ngraph.forcelayout@3.3.1` | **REJECT** | Genuinely 3D (`{dimensions: 3}`) and fast, but last published **2022-10-04** and it forces the `ngraph.graph` data structure on us. No advantage over d3-force-3d that justifies a four-year-old dependency. | ~10 KB gz |
| `graphology` + `graphology-layout-forceatlas2` | **REJECT for the 3D view** | ForceAtlas2 is **2D only** — the README requires `x` and `y` node attributes and has no z. `barnesHutOptimize` defaults to **`false`**, i.e. O(n²) unless you opt in (a real footgun). Layout package last published 2022-10-17. Keep in mind only if we ever ship a 2D sigma view. | ~25 KB gz |
| `sigma@3.0.3` | **REJECT as the primary, KEEP as the 2D fallback candidate** | Excellent WebGL **2D** renderer, MIT, active (2026-04-30), small (~48 KB gz). But it is a *different* answer, not a better 3D one, and it would be a second full rewrite of a view Cytoscape already renders at our scale. See §2.5. | ~48 KB gz + graphology |
| `@cosmograph/cosmos@3.4.1` | **REJECT — LICENCE BLOCKER** | **CC-BY-NC-4.0.** Cosmograph's own licensing page states it is "free for any non-commercial usage" and that commercial use requires a separate proprietary licence. VedAnvaya is a product. Do not evaluate further until someone buys a licence. | n/a |
| `deck.gl@9.4` + `@deck.gl-community/graph-layers@9.4.1` | **REJECT** | deck.gl core is superb and active, but it is a **2.5D geospatial** stack: layers render into an orthographic/`OrbitView` plane, not a real perspective 3D graph. `graph-layers` is a *community* module — 101 stars, 53 open issues, and its README body is the literal string `TBD`. Adopting an undocumented community module for the product's signature view is not a defensible risk. | 150 KB+ gz |
| `troika-three-text@0.52.5` | **REJECT for Devanagari** | See §2.4. Fine for Latin/IAST only. | ~32 KB gz |
| `three-text@0.6.5` | **DO NOT ADOPT YET** | Real HarfBuzz, therefore real Indic shaping — the right idea. But the README says: "three-text is in alpha release and the API may break rapidly. This warning will likely last until summer of 2026." Tarball unpacks to 52.7 MB and you must self-host `hb.wasm`. Revisit in six months. | unmeasured |
| **HTML/Canvas2D label overlay** | **ADOPT** | The only label technique that is *guaranteed* correct for Devanagari, because it is the browser's own shaper. | 0 KB |

### 2.2 Why `react-force-graph-3d` is rejected — three specific reasons

It is *maintained* (published 2026-02-04, 3,297 stars), so "unmaintained" is not the charge.
The charges are concrete:

1. **It asserts no React version.** `peerDependencies: { react: "*" }`. That is not a claim
   of React 19 support; it is the absence of a claim. Its React binding is
   `react-kapsule@2.6.0`, whose peer is `react: ">=16.13.1"`. Reading the source
   (`vasturiano/react-kapsule/src/index.js`): no `findDOMNode` (which React 19 removed), so
   it will not hard-crash — but it **calls imperative setters during render**:

   ```js
   // react-kapsule/src/index.js — this runs in the render body, not an effect
   Object.keys(omit(props, [...methodNames, ...initPropNames]))
     .filter(p => prevPropsRef.current[p] !== props[p])
     .forEach(p => _call(p, props[p]));
   prevPropsRef.current = props;
   ```

   Mutating an external instance during render is precisely what React 19's StrictMode
   double-render and concurrent rendering are designed to punish. It also carries a
   hand-rolled `useEffectOnce` "Handle R18 strict mode double mount at init" shim. This is
   a library working *around* React's model, not with it — under `next dev` with
   `reactStrictMode` on (Next's default, and our `next.config.ts` does not disable it) this
   is exactly where intermittent, hard-to-reproduce bugs live.

2. **`3d-force-graph` declares `three` as a hard `dependency`, not a peer** (`">=0.179 <1"`).
   Under pnpm that resolves independently of our own `three`. If our `three` and theirs ever
   resolve to different versions you get **two THREE namespaces in one page**: every
   `instanceof Mesh` check fails, materials from one cannot be used by the other, and the
   bundle carries three twice (~360 KB gz). Mitigable with a pnpm `overrides` pin, but it is
   a permanent maintenance tax we would be volunteering for.

3. **It owns the loop we need to own.** Picking, labels, LOD, camera choreography and the
   simulation are all inside the kapsule. Every requirement in this brief — GPU picking,
   Devanagari labels, distance-based culling, a camera that frames a node plus its
   first-degree neighbours — is a fight with the abstraction rather than a feature of it.

Verdict: **write ~300 lines of R3F ourselves** and keep every one of those levers. At 1,060
nodes that is genuinely less work than bending a black box.

### 2.3 `deck.gl` specifically

deck.gl's model is layers of instanced geometry projected through a `View`. For a
node-link graph you would use `OrbitView` + `ScatterplotLayer`/`PointCloudLayer` +
`LineLayer`. It works, and deck.gl's picking is already GPU-based and excellent (this is
the one place deck.gl is clearly ahead of a hand-rolled R3F scene). But:

- It is not a React-renderer for a *3D scene*; you get a layer list, not a scene graph. The
  "physical" feel the brief asks for in §5 — mass, springs, a dragged node perturbing its
  neighbours — is not something deck.gl's layer model helps with.
- `@deck.gl-community/graph-layers` is the module that would do the graph-specific work and
  its documentation does not exist (`README.md` body = `TBD`). 101 stars, 53 open issues.
- Bundle is comparable to three+R3F with none of the ecosystem (no drei, no camera-controls,
  no troika, no three-mesh-bvh).

**Reject**, unless the product later wants a *geographic* view (Vedic rivers, places) — at
which point deck.gl becomes the obvious and correct choice for that specific view.

### 2.4 Devanagari — the decisive finding

This is the most important technical finding in the report, and it goes against the
default advice everyone gives.

**`troika-three-text` does not implement Indic shaping, and its README does not say so.**
The README claims it "handles proper kerning, ligature glyph substitution, right-to-left /
bidirectional layout, joined scripts like Arabic" — which reads as "complex scripts are
handled". The issue tracker says otherwise. `protectwise/troika` issue **#303**,
*"troika-three-text: Indic shaping"*, opened **2024-01-30**, **still open**, **zero
comments**, body in full:

> Indic scripts have complex shaping rules which are not yet implemented:
> https://github.com/n8willis/opentype-shaping-documents/blob/master/opentype-shaping-indic-general.md

That is nineteen months open with no activity, on a repo that is otherwise actively
maintained (`v0.53.0`, 2026-07-24). The cause is architectural: troika parses fonts with
**Typr** and applies GSUB/GPOS features directly. That is enough for Latin kerning and for
Arabic joining (which is a contextual-substitution problem). Indic is not a substitution
problem — it needs a **reordering** pass: reph movement, matra repositioning around the
base consonant, half-form and conjunct formation. That pass is not in the codebase.

Concretely, rendering `अग्नि` or `इन्द्रः` through troika will place the *i*-matra on the
wrong side of its consonant cluster and will not form the `ग्न` conjunct. It will not throw.
It will render confidently wrong Sanskrit — which for a digital-humanities product about the
Vedas is the worst possible failure mode, and exactly the class of error this repository's
own QA discipline exists to prevent.

**This also rules out `drei`'s `<Text>`**, which *is* troika-three-text. Anyone reaching for
the obvious "use drei Text" will ship broken Devanagari.

The alternatives, honestly graded:

| option | Devanagari correct? | cost | verdict |
|---|---|---|---|
| `troika-three-text` / drei `<Text>` | **No** (issue #303) | 32 KB gz, GPU-cheap, SDF, batched | **Latin/IAST only** |
| `three-text@0.6.5` (countertype) | **Probably yes** — `harfbuzzjs` is a direct dependency and HarfBuzz implements the full Indic shaping model | alpha API, 52.7 MB tarball, self-hosted `hb.wasm` | **not yet**; re-evaluate ~2027 Q1, and gate adoption on a visual test with real conjuncts |
| drei `<Html>` (real DOM per label) | **Yes** — the browser's shaper | expensive: one DOM node per label, layout+composite per frame; `occlude` mode raycasts | **yes, but only for ≤ ~30 labels at a time** |
| **Canvas2D overlay, drawn from projected positions** | **Yes** — `CanvasRenderingContext2D.fillText` goes through the same platform shaper as the DOM (HarfBuzz in Chromium/Gecko, CoreText in WebKit) | one extra 2D canvas, one `fillText` per visible label per frame; hundreds are fine | **primary recommendation** |

**Recommended label architecture:** a transparent `<canvas>` overlaid on the WebGL canvas,
same size, `pointer-events: none`. Each frame (or each *settled* frame — see §4.5) project
the visible nodes to NDC, cull by distance and by a screen-space occupancy grid, and
`fillText` the survivors. This is correct for Devanagari *and* IAST *and* English, costs
nothing in bundle size, and gives full control over halos, ellipsis and z-ordering. Promote
to a real DOM element only for the hovered/selected node, where you want selectable text,
a link and a11y.

### 2.5 Is 2D-with-great-perf a better answer than mediocre 3D?

Asked squarely, and it deserves a squarely honest answer: **for the focused view, yes —
and we already have it.** Cytoscape at 400 nodes is not a performance problem and is more
*readable* than 3D (no occlusion, no depth ambiguity, labels never overlap in depth).
Swapping it for sigma would buy perf we do not need and cost a rewrite.

3D earns its place in exactly one view: **the World View**, where the value is not
readability of individual edges but the *experience* of a corpus with shape — a
constellation you fly through. That is a legitimate, non-decorative reason, and it is why
the recommendation below keeps 2D for the focused view and puts 3D only where it pays.

---

## 3. React 19 + Next 16 integration reality

### 3.1 Version compatibility, verified rather than assumed

- `@react-three/fiber@9.7.0` declares `react: ">=19 <19.3"` and `react-dom: ">=19 <19.3"`.
  The app is on `react@19.2.8` / `react-dom@19.2.8` — **in range**.
- Note the **upper** bound. `react@19.3` will fall outside R3F 9.7's peer range. Pin React
  to `19.2.x` and treat a React minor bump as an R3F-coupled change, not a routine one.
- `@react-three/drei@10.7.8` declares `react: "^19"` and `@react-three/fiber: "^9.0.0"`. In
  range.
- **R3F v8 does not support React 19** — correct, as the brief states. v9 is the React 19
  compatibility release and bundles its own copy of the reconciler to achieve it.
- **Do not use R3F v10.** A `10.0.0` alpha line has been running through September 2026 and
  its issue tracker in August 2026 shows Turbopack-specific breakage
  (`pmndrs/react-three-fiber#3846`: the `/webgpu` entry threw
  `Cannot read properties of undefined (reading 'REVISION')` under Turbopack because of an
  Inspector import cycle; fixed in `#3855`) plus renderer-lifecycle bugs (`#3850`, `#3847`).
  Those are fixed, but they are the signature of an alpha. Ship on `9.7.x`.

### 3.2 The StrictMode story — and one widely-cited claim that is false

There is a prominent issue, `pmndrs/react-three-fiber#3598`, *"GPU not utilized when using
React 19 StrictMode (works fine when StrictMode is removed)"*. It is **closed and it was a
false alarm**: the maintainer asked whether the *perf overlay* was breaking under
StrictMode, and the reporter's follow-up confirmed "Hardware and GPU is running as expected
but perf doesn't play well with strict mode". It was re-filed against
`utsuboco/r3f-perf#67`. **Do not disable StrictMode on the strength of that issue.** The
tool was measuring itself.

The *real* StrictMode hazards, which are ours to avoid:

- **v9 now inherits StrictMode from the parent `react-dom` root.** In v8 a `<StrictMode>` in
  the DOM tree did not reach inside `<Canvas>`; in v9 it does. Our `next.config.ts` does not
  set `reactStrictMode`, so Next's default (`true`) applies and **the canvas subtree will be
  double-invoked in dev**. Any `useMemo` that allocates a `BufferGeometry`, `Texture` or
  `WebGLRenderTarget` will allocate twice. Allocate GPU resources in `useEffect`/`useLayoutEffect`
  with a matching `dispose()` in cleanup, never in `useMemo` or render.
- **Never call `loseContext()` in a cleanup.** `canvas.getContext('webgl2')` returns the
  *same* context object for a given canvas element; killing it on unmount poisons the
  StrictMode remount that reuses that element. Let R3F own the renderer's lifecycle; dispose
  only the geometries, materials and render targets *you* created.
- **The v9 type migration is a real edit.** `CanvasProps` replaces `Canvas Props`; the
  hardcoded `MeshProps`-style exports are gone in favour of `ThreeElements['mesh']`; the
  global JSX-namespace augmentation is replaced by module augmentation:

  ```ts
  declare module '@react-three/fiber' {
    interface ThreeElements {
      vedaNodes: ThreeElement<typeof VedaNodes>
    }
  }
  ```

### 3.3 SSR / RSC boundaries

Our pages are Server Components that render `"use client"` islands (`graph-explorer.tsx`,
`graph-canvas.tsx`). The 3D view must follow the same shape, with one extra hop:

- `next/dynamic(..., { ssr: false })` **cannot be called from a Server Component** in Next
  15/16 — it throws. So: `page.tsx` (server) → `world-view.tsx` (`"use client"`) →
  `dynamic(() => import('./world-scene'), { ssr: false })`.
- Even a `"use client"` component is server-rendered for its initial HTML. `three` touches
  `document`/`window` at import time in places, so `ssr: false` is the mechanism that keeps
  it off the server, not a performance nicety.
- Give the dynamic import a `loading:` that renders the **2D/tabular fallback markup at the
  right size** — that way the SSR'd HTML is meaningful, layout does not shift, and the
  no-WebGL path (§7) is the same code.

### 3.4 Canvas resize — the one that wastes an afternoon

R3F sizes itself with `react-use-measure` (a declared dependency) over a `ResizeObserver` on
the parent element. The failure is always the same: the parent has `height: 100%` inside a
flex or grid ancestor with no *definite* height, the observer reports `0`, the canvas is
`0px` tall and the scene is invisible with no error. Give the canvas wrapper an explicit
block size or `position: relative` + an absolutely-positioned inset-0 child. Verify by
asserting the observed size in a Playwright check, on the settled DOM — the repo already
learned that lesson about measuring transitions too early.

### 3.5 Web Workers under Turbopack

Next 16 uses Turbopack for `next dev` and `next build` by default. It detects the exact
expression

```ts
new Worker(new URL('./simulation.worker.ts', import.meta.url), { type: 'module' })
```

and emits the worker as its own hashed chunk, the same way webpack 5 does. A plain string
path will 404 in a production build. Next 16.2 additionally improved Web Worker origin
handling for WASM in workers. Constraints:

- The `new URL(...)` must be **literal and inline** in the constructor call. Hoisting it to
  a variable defeats the static analysis.
- Keep the worker module free of anything that imports `three` or React — it should import
  only `d3-force-3d`. That keeps the worker chunk around 15 KB.

### 3.6 SharedArrayBuffer — recommend against, for a project-specific reason

`SharedArrayBuffer` requires cross-origin isolation: `Cross-Origin-Opener-Policy:
same-origin` **and** `Cross-Origin-Embedder-Policy: require-corp` (or `credentialless`),
set via `headers()` in `next.config.ts`, and verified at runtime with
`window.crossOriginIsolated`.

That is a **page-wide contract**, and this product has a cross-origin subresource that
matters: recitation audio streams from **vedsearch.org** (`API_ROOT =
"https://vedsearch.org/api"` in `src/vedagraph/product/audio/vedsearch.py`, and the player
plays `track.playback.stream_url`). Under `require-corp`, that audio is blocked unless
vedsearch.org sends `Cross-Origin-Resource-Policy: cross-origin` — which we do not control.
`credentialless` would probably survive it, but "probably" plus uneven Safari support is not
a trade worth making to save a memcpy.

**Recommendation: transferable `ArrayBuffer` ping-pong, not `SharedArrayBuffer`.** At 1,060
nodes a position buffer is `1060 × 3 × 4 = 12.7 KB`; at 30,000 nodes it is 360 KB. A
transfer is a pointer hand-off, not a copy — it is free. Cross-origin isolation buys us
nothing here and risks the audio layer.

### 3.7 HMR and WebGL context exhaustion

Chrome enforces a limit of roughly **16 live WebGL contexts** per page and evicts the oldest
when you exceed it; Firefox allows 16 total and 8 per principal on mobile. Two ways to hit
that:

- **HMR leaks.** Turbopack Fast Refresh re-executes module scope. A module-level
  `new WebGLRenderer()` or a module-level singleton scene leaks a context per edit until the
  cap evicts your live canvas and it goes blank — usually blamed on the graph data. Keep all
  GPU objects inside the component tree or refs.
- **Many small canvases.** One `<Canvas>` per card (a mini-graph on each deity page) is one
  context each. Use drei's `<View>` (`src/web/View.tsx`) to render several viewports through
  a **single** context with scissor rectangles.

---

## 4. Performance techniques, concretely

Sizing throughout: **tier 1 = ~1,060 entity nodes / ~600 entity-entity edges**, **tier 2 =
~6,000 with formulas**, **tier 3 (optional) = ~30,000 with the passage stratum**.

### 4.1 InstancedMesh for nodes

One `InstancedMesh` per *material family*, not per node type. With an icosahedron at detail
1 (80 triangles) and 30,000 instances you are at 2.4M triangles — fine on a laptop, marginal
on a phone; at detail 0 (20 triangles) it is 600k, fine everywhere. Per-instance colour via
`instanceColor` (`setColorAt`), per-instance scale via the matrix.

The mechanics that bite:

- `instanceColor` is `null` until the **first** `setColorAt` call, after which the material
  compiles a different shader. Call `setColorAt(0, c)` once at construction so the shader
  variant is stable, and set `instanceColor.needsUpdate = true` after each batch.
- `instanceMatrix.setUsage(THREE.DynamicDrawUsage)` when positions come from a live
  simulation, or the driver re-uploads a static buffer every frame.
- Encode *semantic group* as colour **and** as scale, exactly as `graph-canvas.tsx` already
  does with shape + colour ("Colour is never the only difference"). Shape variety in a single
  InstancedMesh means multiple instanced meshes — acceptable at 11 groups, and it preserves
  the existing accessibility contract.

### 4.2 Frustum culling with InstancedMesh — the gotcha, from the source

Read from `three@r186` `src/objects/InstancedMesh.js`:

```js
computeBoundingSphere() {
  // ...
  this.boundingSphere.makeEmpty();
  for ( let i = 0; i < count; i ++ ) {
    this.getMatrixAt( i, _instanceLocalMatrix );
    _sphere.copy( geometry.boundingSphere ).applyMatrix4( _instanceLocalMatrix );
    this.boundingSphere.union( _sphere );      // <-- union of ALL instances
  }
}
```

So the bounding sphere is the union over every instance: **the whole InstancedMesh is culled
as a single object**. Frustum culling gives you nothing at graph scale — zoom into one deity
and you still submit all 30,000 instances.

Worse, the sphere is *stale* unless you recompute it. If the simulation moves nodes outward
past the sphere they will pop out of existence at the edges of the view; if it contracts them
the sphere stays huge and culling never fires. Two correct responses:

1. `nodes.frustumCulled = false` and accept that you always submit the whole buffer (right
   answer up to ~50k instances — the GPU does not care).
2. Call `computeBoundingSphere()` when the simulation **settles** (not per frame — it is
   O(n) with a matrix decompose each), and only then.

If per-instance culling ever becomes necessary, the established technique is to **sort the
instance buffer** so visible instances are contiguous and then set `mesh.count` to the
visible prefix. Do not build that until a profile demands it.

### 4.3 Edges: `LineSegments` vs fat lines vs instanced quads

| technique | cost for 240k edges | quality | verdict |
|---|---|---|---|
| `LineSegments` + `LineBasicMaterial` | one draw call, 480k vertices, ~5.7 MB of `Float32Array` | **1 device pixel wide, always** — `linewidth` is ignored on every WebGL platform (the ANGLE/core-profile restriction). Hairlines that vanish on HiDPI. | the scalable option, and it looks thin and cheap |
| `Line2` / `LineSegments2` + `LineMaterial` (`three/addons/lines/`) | instanced quads: **8 floats of start/end per segment plus a 6-vertex quad each**; ~4× the memory and a fragment-heavy shader | real width, joins, dashes, world-or-screen units | beautiful; budget it at **≤ ~5,000 segments** |
| hand-rolled instanced quads (billboarded) | same order as `Line2`, but you control the shader (e.g. fade by distance, encode predicate as colour, taper by confidence) | full control | the right answer **if** we want confidence-weighted edges |

**For our real numbers this is not a hard call.** The World View draws ~600 entity-entity
edges: use `LineSegments2`, get proper width, done. The 240k-edge case only arises in tier 3
and the correct answer there is not a rendering technique — it is **not drawing them** (§4.6).

One number worth stating plainly: 240,000 `LineSegments` positions is 480,000 vertices ×
3 floats × 4 bytes = **5.76 MB** of vertex buffer, uploaded once. That is fine as *memory*.
It is the *visual* that fails — 240k hairlines is a grey rectangle, not a graph.

### 4.4 Picking: GPU picking, not raycasting — proven from the source

`InstancedMesh.raycast` in `three@r186` is **O(count)** with a full mesh raycast per instance:

```js
raycast( raycaster, intersects ) {
  // one early-out against the whole-mesh bounding sphere, then:
  for ( let instanceId = 0; instanceId < raycastTimes; instanceId ++ ) {
    this.getMatrixAt( instanceId, _instanceLocalMatrix );
    _instanceWorldMatrix.multiplyMatrices( matrixWorld, _instanceLocalMatrix );
    _mesh.matrixWorld = _instanceWorldMatrix;
    _mesh.raycast( raycaster, _instanceIntersects );   // full triangle test
  }
}
```

The only early-out is the union bounding sphere from §4.2 — which, being the union, almost
always contains the ray. So a pointer-move over 10,000 instances of an 80-triangle sphere is
~800,000 triangle intersections **per pointer event**, on the main thread. At 60 Hz pointer
events that is not a budget, it is a freeze.

Thresholds:

- **≤ 2,000 nodes**: raycasting is fine. Add drei `<Bvh>` (three-mesh-bvh 0.9.15) and R3F's
  `raycaster={{ firstHitOnly: true }}` and stop thinking about it.
- **> 2,000 nodes, or any hover-highlight**: **GPU picking**. Render the node instances to a
  1×1 scissored render target with a shader that writes the instance id as RGB, then
  `readRenderTargetPixelsAsync` — which exists in r186 and whose own doc comment says
  "It is recommended to use this version of `readRenderTargetPixels()` whenever possible",
  because the synchronous version stalls the pipeline waiting for the GPU.

Full sketch in §9.3. Cost is one extra 1×1 draw of the node buffer per *throttled* pointer
move (not per frame), which at 30k instances is sub-millisecond.

### 4.5 Labels: cost and quality, with Devanagari as the constraint

Restating §2.4 as an engineering table:

| technique | per-label cost | Devanagari | notes |
|---|---|---|---|
| troika SDF (`drei <Text>`) | ~0; batched, GPU-resident | **broken** (troika #303) | usable only for Latin/IAST |
| sprite atlas (pre-rendered glyph sheet) | one instanced quad | correct **only if you rasterise with Canvas2D**, which shapes properly | viable but you are building a text engine |
| drei `<Html>` | a real DOM node: layout + composite per frame; `occlude` raycasts, `transform` adds a CSS 3D matrix per frame | **correct** | budget **≤ ~30 concurrently** |
| **Canvas2D overlay from projected positions** | one `fillText` per visible label per drawn frame | **correct** | **recommended**; hundreds are cheap |

The Canvas2D overlay also solves label *placement*, which SDF-in-3D does badly: you have
screen-space coordinates, so you can run a simple occupancy grid (bucket the screen into
~40×16 px cells, first-come-wins) and get non-overlapping labels — which is what
`graph-canvas.tsx` approximates today with `min-zoomed-font-size` and `hide-label`.

Draw the overlay only when something changed: `useFrame` sets a dirty flag on camera move or
simulation tick, and the overlay redraws on dirty. A settled, un-touched World View then
costs zero label work.

### 4.6 Level of detail

Four independent knobs, in the order they should be reached for:

1. **Stratum LOD (the big one).** Tier 1 draws the ~1,060 entities. The 22,537 passages are
   not drawn as nodes at all — they are aggregated into **meta-nodes**: one node per
   (Maṇḍala) or per (Veda × Maṇḍala), sized by mantra count, with an edge weight equal to the
   number of underlying `MENTIONS_*` edges. That turns 47,542 `ABOUT_CONCEPT` edges into a few
   hundred weighted edges and is *more* informative, not less. It also fits the repo's
   discipline: a meta-node with `n = 1,604` states its own aggregation, whereas 50 sampled
   `MENTIONS_DEVATA` edges out of 3,566 is "a false picture of a deity's prominence" — the
   exact phrase in the neighbourhood endpoint's own description.
2. **Distance-based label culling.** Label only nodes within a camera-distance threshold
   *and* above a degree threshold, then cap at ~120 labels by screen-space occupancy.
3. **Edge thinning.** Below a zoom threshold, draw only edges whose weight/confidence is in
   the top decile. Fade rather than pop (`opacity` on a per-instance attribute).
4. **Geometry LOD.** `IcosahedronGeometry(r, 1)` near, `(r, 0)` far — or simply use a
   billboarded instanced quad with a circular alpha mask, which at graph scale is
   indistinguishable and four vertices.

### 4.7 The simulation in a Web Worker

Design: the worker owns `d3-force-3d`; the main thread owns rendering and never touches the
simulation's arrays.

- **Transferables, not SharedArrayBuffer** (§3.6). Ping-pong two `Float32Array(n*3)` buffers:
  the worker posts buffer A with `[A.buffer]` as transfer list, the main thread copies it
  into `instanceMatrix` and posts it back. Neither side ever allocates after startup.
- **Post at ~30 Hz, not per tick.** d3-force ticks faster than you need; batching to a
  `setInterval`-driven post halves the message traffic and looks identical.
- **Interaction messages go worker-ward**: `pin` (set `fx/fy/fz`), `release`, `reheat`
  (`alphaTarget(0.3).restart()`), `settle` (`alphaTarget(0)`).
- The worker chunk must import only `d3-force-3d`. Keep `three` and React out of it.

Protocol in §9.2.

---

## 5. Camera choreography

### 5.1 `CameraControls` over `OrbitControls`

Use drei's `<CameraControls>` (wrapping `camera-controls@3.1.2`, MIT, pushed 2026-09-09). It
is strictly better than `OrbitControls` for this product, verified against the source:

- **Every transition returns a `Promise<void>`** — `rotateTo`, `dollyTo`, `setLookAt`,
  `fitToSphere`, `fitToBox` all take an `enableTransition` flag and resolve on arrival. That
  makes "fly to the node, *then* open the evidence drawer" a plain `await`, not a timer.
- **Real damping via `smoothTime`** (default `0.25`) and a separate `draggingSmoothTime`
  (`0.125`) — critically-damped smoothing, not OrbitControls' exponential
  `dampingFactor` decay. It settles; it does not creep.
- **`fitToSphere(sphereOrObject, enableTransition)`** and **`fitToBox`** do the framing maths
  for us, including the FOV/aspect term that everyone gets wrong on first attempt.
- Events we need: `onRest` (fires when the camera settles — the right trigger for "redraw
  labels at full quality"), `onControlStart`/`onControlEnd`, `onTransitionStart`.
- `setOrbitPoint(x,y,z)` moves the orbit centre without a camera jump — this is how "click a
  node, now orbit around *it*" should be implemented.

`OrbitControls` remains the right choice only if we want a minimal dependency and no
transitions. We want transitions.

### 5.2 Framing a node and its first-degree neighbours

The correct framing is not "look at the node" — it is "fit the sphere that contains the node
and its neighbours, with the selected node biased toward screen centre". Algorithm:

1. Collect the selected node's position plus its first-degree neighbour positions.
2. Build a `Sphere` from those points: `new THREE.Box3().setFromPoints(pts).getBoundingSphere(new THREE.Sphere())`.
3. Inflate the radius by the largest node radius plus a padding factor (`× 1.35` reads well).
4. `controls.fitToSphere(sphere, true)`.
5. Optionally `controls.setFocalOffset(0, 0, 0, true)` first, because `fitToSphere` resets it
   anyway and doing it explicitly avoids a visible two-stage move.

If you must compute the distance yourself (for instance to clamp it):

```
vFOV = camera.fov * Math.PI / 180
hFOV = 2 * Math.atan(Math.tan(vFOV / 2) * camera.aspect)
distance = radius / Math.sin(Math.min(vFOV, hFOV) / 2)
```

Using `min(vFOV, hFOV)` is the part people miss — on a portrait phone the horizontal FOV is
the binding constraint and a vertical-only calculation crops the subgraph.

### 5.3 Easing along a curve

For a "tour" (e.g. walking the hops of a path result), do **not** chain `setLookAt` calls —
the joins are visible. Build a `CatmullRomCurve3` through the waypoints and drive it with
`controls.setLookAt(...)` per frame from a single eased parameter `t`, or use
`controls.lerpLookAt(a…, b…, t)` between two states. A `t` driven by
`easeInOutCubic` over 900–1400 ms reads as intentional; anything under 500 ms reads as a cut.

Respect `prefers-reduced-motion` by setting `enableTransition = false` throughout, which
turns every one of these into an instant, still-correct jump.

---

## 6. Graph physics that feels physical

### 6.1 Which library keeps the simulation alive

| library | live/interactive | 3D | verdict |
|---|---|---|---|
| `d3-force-3d` | **yes** — `alphaTarget()` + `restart()` is the documented reheat-on-drag idiom | yes (`numDimensions: 3`) | **use this** |
| `ngraph.forcelayout` | yes (`step()` loop) | yes (`{dimensions: 3}`) | fine, but 2022 |
| `graphology-layout-forceatlas2` | worker variant runs continuously | **no, 2D only** | not for this |
| `@cosmograph/cosmos` | yes, GPU | 2D | licence blocker |
| `three-forcegraph` | yes, wraps d3-force-3d | yes | you get d3-force-3d anyway, without the wrapper |

### 6.2 Parameters for a degree range of 1–5,459

The hub problem is not visual, it is numerical. `forceManyBody` with a uniform strength
means Agni (5,459 edges) is pulled on by 5,459 springs while a `Weapon` node has one. The
hub sinks to the centre and drags everything with it; the periphery smears. Concrete
settings:

```ts
const maxDeg = 5459;
const norm = (d: number) => Math.log1p(d) / Math.log1p(maxDeg);   // 0..1

sim
  // Repulsion: Barnes-Hut. distanceMax matters more than strength at this range --
  // without it, every node repels every other and hubs dominate the whole field.
  .force('charge', forceManyBody()
    .strength((n) => -30 - 170 * norm(n.degree))   // -30 leaf .. -200 hub
    .theta(0.9)                                     // 0.9 over the default 0.9/0.8: speed
    .distanceMin(2)                                 // stops singularities on coincident nodes
    .distanceMax(300))                              // the single most important knob

  // Springs: weak on hub-incident edges, or the hub collapses its whole neighbourhood.
  .force('link', forceLink(edges).id(d => d.id)
    .distance((e) => 40 + 60 * norm(Math.min(e.source.degree, e.target.degree)))
    .strength((e) => 1 / (1 + Math.max(e.source.degree, e.target.degree) ** 0.5)))

  // Mass proportional to degree: heavy hubs move slowly and act as anchors.
  // d3-force has no mass, so emulate it by damping the hub's velocity each tick.
  .force('mass', (alpha) => {
    for (const n of nodes) {
      const damp = 1 - 0.9 * norm(n.degree);
      n.vx *= damp; n.vy *= damp; n.vz *= damp;
    }
  })

  // Cluster attraction: pull each node toward its semantic group's centroid.
  .force('cluster', clusterForce(groupCentroids, 0.06))

  .force('centre', forceCenter(0, 0, 0).strength(0.02))
  .alphaDecay(0.0228)        // default: settles in ~300 ticks
  .velocityDecay(0.4);
```

- `distanceMax` is the knob that actually fixes hubs. Without it `forceManyBody` is global
  and a 5,459-degree node warps the entire layout. With it, a hub only shapes its
  neighbourhood.
- **Emulated mass** is necessary because d3-force explicitly "assumes … a constant unit mass
  *m* = 1 for all particles" (its own README). Damping velocity per-node is the cheapest
  faithful approximation.
- **Cluster attraction by semantic group** should reuse the existing `semanticGroup()`
  function from `frontend/src/components/graph-canvas.tsx` verbatim. Those 11 groups are
  already the product's ontology-facing vocabulary; inventing a second clustering would let
  the two disagree — the same failure the attribution-axis note in this repo's memory
  records.
- **Dragging**: set `fx/fy/fz` on pointer-down, `alphaTarget(0.3).restart()`, clear
  `fx/fy/fz` and `alphaTarget(0)` on pointer-up. Neighbours perturb for free — that *is* the
  "physical" feel, and it needs no extra code.

### 6.3 Precompute vs live

Both, at different tiers:

- **World View: precompute and freeze**, then run a low-amplitude live simulation only while
  the user drags. A 1,060-node layout takes ~300 ticks ≈ 80 ms in a worker, so you *could*
  compute it live — but a precomputed layout is **stable across sessions**, which matters
  enormously for a map people are meant to learn. A deity that is in the same place every
  visit becomes navigable. Ship the frozen positions in the artifact (§8.1) and reheat only
  on interaction.
- **Focused view: live**, always. It is ≤ 400 nodes, it changes on every expansion, and the
  settling animation *is* the affordance that tells the reader new material arrived.

---

## 7. Fallbacks

### 7.1 WebGL detection

Use `three/addons/capabilities/WebGL.js` — `WebGL.isWebGL2Available()` — which is exactly:

```js
const canvas = document.createElement('canvas');
return !!(window.WebGL2RenderingContext && canvas.getContext('webgl2'));
```

Run it **before** dynamically importing the scene chunk, so a machine without WebGL2 never
downloads 200 KB of three. Also register `webglcontextlost` on the canvas and render the
fallback on loss — context loss is routine on laptops that switch GPUs, not exceptional.

### 7.2 `prefers-reduced-motion`

`graph-canvas.tsx` already gates its Cytoscape layout animation on
`window.matchMedia('(prefers-reduced-motion: reduce)')`. Extend the same gate:

- camera transitions → `enableTransition = false` (instant, still correct);
- simulation → run it to convergence **off-screen** (worker, no rendering), then draw the
  settled layout once. No drifting nodes, no orbit idle;
- disable any idle/auto-rotate entirely.

### 7.3 Mobile GPU limits

- **Context budget**: ~16 per page in Chrome, 16 total / 8 per principal on Firefox mobile.
  One canvas, drei `<View>` for multiple viewports.
- **`maxTextureSize`** is reported in privacy-tiered buckets (2048 / 8192 / 32768) rather
  than the true GPU value. If we ever build a glyph atlas, cap it at **2048** and page.
- **DPR**: cap at 2 and use drei `<AdaptiveDpr pixelated />` plus `<PerformanceMonitor>` to
  step DPR down when frame time degrades. A phone at DPR 3 is rendering 9× the fragments of
  DPR 1 for no perceptible gain on a graph.
- **Fragment cost dominates on mobile.** Prefer instanced billboard quads with an alpha
  circle over real sphere geometry, and avoid any post-processing.

### 7.4 The 2D / tabular fallback

It must be the **same information**, not a consolation. We already have the pieces:

1. Cytoscape 2D neighbourhood (`graph-canvas.tsx`) — the existing, accessible view.
2. The node/edge **list panel** that `graph-explorer.tsx` already renders beside the graph,
   which the canvas's own `aria-label` points to: *"A textual list of the same nodes is in
   the panel beside this graph."*

For the World View the fallback is a **grouped, sortable table**: one section per semantic
group, rows sorted by degree, each row linking to the focused view. That is genuinely more
useful than the 3D view for a screen-reader user or anyone who knows what they are looking
for — so it should be a *first-class toggle* in the UI, not a hidden degraded mode.

---

## 8. Recommended architecture for VedAnvaya

### 8.1 World View — "the constellation"

**What it renders:** the ~1,060-node entity layer, plus optional meta-nodes for the passage
stratum. Never the raw 22,537 passages.

**Where the data comes from — the hard part.** There is no whole-graph endpoint, and there
should not be one: every existing graph endpoint is deliberately bounded and every bound is
disclosed in its own response. Adding an unbounded dump would break that contract.

The right answer is a **build-time artifact**, produced by a new `vedagraph` CLI command that
talks to Neo4j directly (the CLI already has a Neo4j session — `src/vedagraph/cli/app.py`),
not by the API:

```
vedagraph export world-view --out frontend/public/world/v1/
```

emitting:

| file | contents | approx size |
|---|---|---|
| `meta.json` | schema version, graph identity/hash, node & edge counts, the semantic-group legend, and an explicit statement of **what was excluded and why** | ~4 KB |
| `nodes.bin` | `Float32Array` positions `[x,y,z]×n` (precomputed, frozen layout) | 12.7 KB @ 1,060 |
| `attrs.bin` | `Uint8Array` group index, `Uint16Array` degree, `Float32Array` radius | ~8 KB |
| `labels.json` | id, display label (Devanagari + IAST + English), type, href | ~120 KB |
| `edges.bin` | `Uint16Array`/`Uint32Array` source/target index pairs + `Uint8Array` predicate index | ~5 KB @ 600 |

Total well under 200 KB, served as static files with a long cache and a versioned path. The
graph is **frozen** (`README.md:71`), so a build-time artifact is not a staleness risk — it
is the correct representation of a frozen thing. `meta.json` must carry the graph identity so
a drifted artifact is detectable rather than silently wrong; and per this repo's own
discipline, the file must *state its exclusions in the row*, not only in a caveat block —
a viewer that shows 1,060 of 108,779 nodes without saying so lets the reader infer a false
whole.

**How it renders:**

- one `<Canvas>` (`dpr={[1, 2]}`, `gl={{ antialias: true, powerPreference: 'high-performance' }}`);
- one `InstancedMesh` per semantic group (11 of them, ~100 instances each) — instancing is
  not strictly needed at this size but it makes the tier-3 path a data change, not a rewrite;
- `LineSegments2` for the ~600 entity-entity edges, real width, coloured by predicate;
- **Canvas2D label overlay** (§4.5) — correct Devanagari, occupancy-gridded, redrawn on dirty;
- **GPU picking** (§4.4) — already built at 1,060 nodes so it never needs retrofitting;
- `<CameraControls>` with `smoothTime = 0.25`;
- worker simulation, **idle by default** (positions come from the artifact), reheated only
  while dragging.

**Tier 3, if and when it is wanted:** add `passages.bin` with the meta-node aggregation, flip
the instanced meshes to 30k instances, turn on edge thinning and distance label culling. No
architectural change.

### 8.2 Focused view — keep it 2D

`GET /graph/neighborhood/{id}` returns ≤ 400 nodes. **Keep Cytoscape.** It is shipping, it is
readable, it has the group shapes and the *Why* panel wired, and it has no performance
problem. Swapping it for 3D would trade readability for novelty and cost a rewrite of
`graph-canvas.tsx`'s entire styling contract.

The *connection* between the two views is where the effort belongs: selecting a node in the
World View should fly the camera to it (§9.4), then deep-link into the existing focused view.

If a 3D focused view is wanted later as an *option*, it reuses the exact same components
with the artifact swapped for live API data — which is why the renderer should take
`Float32Array`s, not `GraphNode[]`.

### 8.3 Path view — 2D, and deliberately so

Paths are ≤ 4 hops with a written explanation per hop. The product value is entirely in the
explanations. Render it as a **horizontal chain** — nodes as cards, each hop annotated with
its `why` string, `hub_mediated` flagged inline. 3D would actively hurt: a path is a linear
object and depth only occludes it.

The one 3D touch worth having: when the path view is open *and* the World View is visible,
highlight the path's nodes and edges in the 3D scene and fly the camera along a
`CatmullRomCurve3` through the waypoints (§5.3). That is choreography in service of the
content rather than decoration.

---

## 9. Code sketches

Real, compiling-shaped TypeScript. Assumes `three@0.186`, `@react-three/fiber@9.7`,
`@react-three/drei@10.7.8`, `d3-force-3d@3`.

### 9.1 The instanced node renderer

```tsx
// frontend/src/components/world/instanced-nodes.tsx
'use client';

import { useFrame, type ThreeEvent } from '@react-three/fiber';
import { useLayoutEffect, useMemo, useRef } from 'react';
import {
  Color,
  DynamicDrawUsage,
  IcosahedronGeometry,
  InstancedMesh,
  MeshLambertMaterial,
  Matrix4,
  Quaternion,
  Vector3,
} from 'three';

/** One flat, GPU-shaped view of the graph. Never an array of objects. */
export type NodeBuffers = {
  /** [x,y,z] * count, mutated in place by the worker hand-off. */
  positions: Float32Array;
  /** World-space radius per node, derived from degree. */
  radii: Float32Array;
  /** Index into the semantic-group palette. */
  groups: Uint8Array;
  count: number;
};

const IDENTITY_Q = new Quaternion();
const _m = new Matrix4();
const _p = new Vector3();
const _s = new Vector3();
const _c = new Color();

export function InstancedNodes({
  buffers,
  palette,
  selected,
  onPick,
}: {
  buffers: NodeBuffers;
  /** One hex per semantic group, same 11 groups as graph-canvas.tsx. */
  palette: readonly string[];
  selected: number | null;
  onPick?: (index: number, event: ThreeEvent<PointerEvent>) => void;
}) {
  const ref = useRef<InstancedMesh>(null);

  // Detail 0 = 20 triangles. Shared across every instance; allocated once.
  const geometry = useMemo(() => new IcosahedronGeometry(1, 1), []);
  const material = useMemo(
    () => new MeshLambertMaterial({ toneMapped: false }),
    [],
  );

  // Allocate GPU resources in an effect, not in render: StrictMode double-invokes
  // render, and R3F v9 inherits StrictMode from the react-dom root.
  useLayoutEffect(() => {
    return () => {
      geometry.dispose();
      material.dispose();
    };
  }, [geometry, material]);

  // Colour is static per node; write it once so the instanceColor shader variant
  // is compiled up front rather than on the first hover.
  useLayoutEffect(() => {
    const mesh = ref.current;
    if (!mesh) return;
    for (let i = 0; i < buffers.count; i++) {
      _c.set(palette[buffers.groups[i]] ?? palette[palette.length - 1]);
      mesh.setColorAt(i, _c);
    }
    if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
    mesh.instanceMatrix.setUsage(DynamicDrawUsage);
    // The union bounding sphere is meaningless for culling (three r186
    // InstancedMesh.computeBoundingSphere unions every instance), so culling is
    // off and the whole buffer is submitted. Correct up to ~50k instances.
    mesh.frustumCulled = false;
  }, [buffers, palette]);

  useFrame(() => {
    const mesh = ref.current;
    if (!mesh) return;
    const { positions, radii, count } = buffers;
    for (let i = 0; i < count; i++) {
      const r = radii[i] * (i === selected ? 1.45 : 1);
      _p.set(positions[i * 3], positions[i * 3 + 1], positions[i * 3 + 2]);
      _s.setScalar(r);
      mesh.setMatrixAt(i, _m.compose(_p, IDENTITY_Q, _s));
    }
    mesh.instanceMatrix.needsUpdate = true;
  });

  return (
    <instancedMesh
      ref={ref}
      // args are [geometry, material, count] and count cannot grow later --
      // allocate the ceiling, then drive `count` to hide the tail.
      args={[geometry, material, buffers.count]}
      onPointerDown={(e) => {
        if (e.instanceId != null) onPick?.(e.instanceId, e);
      }}
    />
  );
}
```

> Note the `onPointerDown` above is R3F's *raycast* path. It is acceptable for **click**
> (one event, user-initiated). For **hover** at this scale use the GPU picker in §9.3 and set
> `raycast={() => null}` on the mesh so R3F never walks 1,060 instances on pointer-move.

### 9.2 The worker simulation protocol

```ts
// frontend/src/components/world/simulation-protocol.ts
/** Main thread -> worker. */
export type SimRequest =
  | {
      type: 'init';
      /** Node degrees drive charge strength, spring length and emulated mass. */
      degrees: Uint16Array;
      /** Semantic group index per node, used for cluster attraction. */
      groups: Uint8Array;
      /** Flat [source, target] index pairs. */
      edges: Uint32Array;
      /** Precomputed starting positions from the artifact, [x,y,z] * n. */
      positions: Float32Array;
      maxDegree: number;
    }
  | { type: 'pin'; index: number; x: number; y: number; z: number }
  | { type: 'release'; index: number }
  | { type: 'reheat'; alphaTarget: number }
  | { type: 'settle' }
  /** Hand a recycled buffer back so the worker never allocates mid-flight. */
  | { type: 'recycle'; positions: Float32Array }
  | { type: 'dispose' };

/** Worker -> main thread. */
export type SimResponse =
  | { type: 'ready'; nodeCount: number }
  | { type: 'tick'; positions: Float32Array; alpha: number }
  | { type: 'settled'; positions: Float32Array }
  | { type: 'error'; message: string };
```

```ts
// frontend/src/components/world/simulation.worker.ts
/// <reference lib="webworker" />
import {
  forceCenter,
  forceLink,
  forceManyBody,
  forceSimulation,
  type Simulation,
} from 'd3-force-3d';
import type { SimRequest, SimResponse } from './simulation-protocol';

type SimNode = { index: number; degree: number; group: number;
  x: number; y: number; z: number; vx: number; vy: number; vz: number;
  fx?: number | null; fy?: number | null; fz?: number | null };

let sim: Simulation<SimNode, undefined> | null = null;
let nodes: SimNode[] = [];
/** Two buffers, ping-ponged. We own neither while one is in flight. */
const spare: Float32Array[] = [];
let postTimer: ReturnType<typeof setInterval> | null = null;

const post = (message: SimResponse, transfer: Transferable[] = []) =>
  (self as unknown as Worker).postMessage(message, transfer);

function drain(kind: 'tick' | 'settled') {
  const buf = spare.pop();
  if (!buf) return; // both buffers in flight; skip this frame rather than allocate
  for (let i = 0; i < nodes.length; i++) {
    buf[i * 3] = nodes[i].x;
    buf[i * 3 + 1] = nodes[i].y;
    buf[i * 3 + 2] = nodes[i].z;
  }
  post({ type: kind, positions: buf, alpha: sim?.alpha() ?? 0 } as SimResponse, [buf.buffer]);
}

self.onmessage = (event: MessageEvent<SimRequest>) => {
  const message = event.data;
  switch (message.type) {
    case 'init': {
      const n = message.degrees.length;
      const maxDeg = Math.max(1, message.maxDegree);
      const norm = (d: number) => Math.log1p(d) / Math.log1p(maxDeg);

      nodes = Array.from({ length: n }, (_, i) => ({
        index: i,
        degree: message.degrees[i],
        group: message.groups[i],
        x: message.positions[i * 3],
        y: message.positions[i * 3 + 1],
        z: message.positions[i * 3 + 2],
        vx: 0, vy: 0, vz: 0,
      }));

      const links = [];
      for (let e = 0; e < message.edges.length; e += 2) {
        links.push({ source: message.edges[e], target: message.edges[e + 1] });
      }

      spare.push(new Float32Array(n * 3), new Float32Array(n * 3));

      sim = forceSimulation(nodes, 3)
        .force('charge', forceManyBody<SimNode>()
          .strength((d) => -30 - 170 * norm(d.degree))
          .theta(0.9)
          .distanceMin(2)
          .distanceMax(300))
        .force('link', forceLink(links)
          .id((d: SimNode) => d.index)
          .distance((l: { source: SimNode; target: SimNode }) =>
            40 + 60 * norm(Math.min(l.source.degree, l.target.degree)))
          .strength((l: { source: SimNode; target: SimNode }) =>
            1 / (1 + Math.sqrt(Math.max(l.source.degree, l.target.degree)))))
        // d3-force assumes unit mass for every particle (its own README says so),
        // so emulate mass by damping a high-degree node's velocity each tick.
        .force('mass', () => {
          for (const node of nodes) {
            const damp = 1 - 0.9 * norm(node.degree);
            node.vx *= damp; node.vy *= damp; node.vz *= damp;
          }
        })
        .force('centre', forceCenter(0, 0, 0).strength(0.02))
        .velocityDecay(0.4)
        .alphaTarget(0)
        .stop();

      // Tick freely; post at ~30 Hz. d3 ticks faster than any display needs.
      postTimer = setInterval(() => {
        if (!sim) return;
        for (let k = 0; k < 2; k++) sim.tick();
        drain(sim.alpha() <= sim.alphaMin() ? 'settled' : 'tick');
      }, 33);

      post({ type: 'ready', nodeCount: n });
      break;
    }
    case 'pin': {
      const node = nodes[message.index];
      if (node) { node.fx = message.x; node.fy = message.y; node.fz = message.z; }
      sim?.alphaTarget(0.3).restart();
      break;
    }
    case 'release': {
      const node = nodes[message.index];
      if (node) { node.fx = null; node.fy = null; node.fz = null; }
      sim?.alphaTarget(0);
      break;
    }
    case 'reheat': sim?.alphaTarget(message.alphaTarget).restart(); break;
    case 'settle': sim?.alphaTarget(0); break;
    case 'recycle': spare.push(message.positions); break;
    case 'dispose': {
      if (postTimer) clearInterval(postTimer);
      sim?.stop();
      sim = null; nodes = []; spare.length = 0;
      break;
    }
  }
};
```

```ts
// frontend/src/components/world/use-simulation.ts
'use client';
import { useEffect, useRef } from 'react';
import type { SimRequest, SimResponse } from './simulation-protocol';

export function useSimulation(onTick: (positions: Float32Array) => void) {
  const workerRef = useRef<Worker | null>(null);

  useEffect(() => {
    // The `new URL(...)` must be literal and inline: Turbopack (Next 16's default
    // bundler) statically detects exactly this shape and emits the worker as its own
    // chunk. A string path resolves to a 404 in a production build.
    const worker = new Worker(new URL('./simulation.worker.ts', import.meta.url), {
      type: 'module',
    });
    workerRef.current = worker;

    worker.onmessage = (event: MessageEvent<SimResponse>) => {
      const message = event.data;
      if (message.type === 'tick' || message.type === 'settled') {
        onTick(message.positions);
        // Hand the buffer straight back, transferring ownership again.
        worker.postMessage(
          { type: 'recycle', positions: message.positions } satisfies SimRequest,
          [message.positions.buffer],
        );
      }
    };

    return () => {
      worker.postMessage({ type: 'dispose' } satisfies SimRequest);
      worker.terminate();
      workerRef.current = null;
    };
  }, [onTick]);

  return workerRef;
}
```

### 9.3 GPU picking

```ts
// frontend/src/components/world/gpu-picker.ts
import {
  Camera,
  Color,
  InstancedBufferAttribute,
  InstancedMesh,
  MeshBasicMaterial,
  NearestFilter,
  Scene,
  UnsignedByteType,
  WebGLRenderTarget,
  WebGLRenderer,
} from 'three';

/**
 * Renders the node instances into a 1x1 scissored target whose fragment colour is the
 * instance id, then reads that pixel back.
 *
 * Why not raycast: three r186's InstancedMesh.raycast loops over every instance and
 * runs a full mesh raycast on each, with only the *union* bounding sphere as an
 * early-out -- so hover over 10k instances is ~800k triangle tests per pointer event
 * on the main thread.
 */
export class GpuPicker {
  private readonly target: WebGLRenderTarget;
  private readonly pixel = new Uint8Array(4);
  private readonly pickScene = new Scene();
  private readonly clearColour = new Color(0xffffff); // id 0xFFFFFF == "nothing"
  private busy = false;

  constructor(
    private readonly renderer: WebGLRenderer,
    private readonly source: InstancedMesh,
  ) {
    this.target = new WebGLRenderTarget(1, 1, {
      type: UnsignedByteType,
      minFilter: NearestFilter,
      magFilter: NearestFilter,
      depthBuffer: true,
    });

    // A parallel instanced mesh sharing the SAME geometry and instanceMatrix, with a
    // material that writes gl_InstanceID as RGB. Sharing instanceMatrix means the
    // picking pass never needs its own update.
    const material = new MeshBasicMaterial({ toneMapped: false });
    material.onBeforeCompile = (shader) => {
      shader.vertexShader = shader.vertexShader
        .replace('#include <common>', '#include <common>\n varying vec3 vPickId;')
        .replace(
          '#include <begin_vertex>',
          `#include <begin_vertex>
           float id = float(gl_InstanceID);
           vPickId = vec3(
             mod(id, 256.0),
             mod(floor(id / 256.0), 256.0),
             floor(id / 65536.0)
           ) / 255.0;`,
        );
      shader.fragmentShader = shader.fragmentShader
        .replace('#include <common>', '#include <common>\n varying vec3 vPickId;')
        .replace(
          '#include <dithering_fragment>',
          'gl_FragColor = vec4(vPickId, 1.0);',
        );
    };

    const proxy = new InstancedMesh(source.geometry, material, source.count);
    proxy.instanceMatrix = source.instanceMatrix;
    proxy.frustumCulled = false;
    this.pickScene.add(proxy);
  }

  /**
   * @param x,y  Pointer position in CSS pixels, relative to the canvas.
   * @returns the instance id under the pointer, or null.
   */
  async pick(x: number, y: number, camera: Camera): Promise<number | null> {
    if (this.busy) return null;          // drop, do not queue: pointermove outruns the GPU
    this.busy = true;
    try {
      const dpr = this.renderer.getPixelRatio();
      const size = this.renderer.getSize(new (await import('three')).Vector2());

      // Shift the projection so the single pixel we render is the one under the pointer.
      const pickCamera = camera.clone() as typeof camera & { setViewOffset?: Function };
      pickCamera.setViewOffset?.(
        size.width * dpr, size.height * dpr,
        Math.floor(x * dpr), Math.floor(y * dpr),
        1, 1,
      );

      const previousTarget = this.renderer.getRenderTarget();
      const previousClear = this.renderer.getClearColor(new Color());
      this.renderer.setRenderTarget(this.target);
      this.renderer.setClearColor(this.clearColour, 1);
      this.renderer.clear();
      this.renderer.render(this.pickScene, pickCamera);
      this.renderer.setRenderTarget(previousTarget);
      this.renderer.setClearColor(previousClear, 1);

      // Async read: the sync readRenderTargetPixels stalls the pipeline waiting on the
      // GPU. three r186's own doc comment recommends the async form "whenever possible".
      await this.renderer.readRenderTargetPixelsAsync(this.target, 0, 0, 1, 1, this.pixel);

      const id = this.pixel[0] + this.pixel[1] * 256 + this.pixel[2] * 65536;
      return id === 0xffffff ? null : id;
    } finally {
      this.busy = false;
    }
  }

  dispose() {
    this.target.dispose();
    this.pickScene.clear();
  }
}
```

Wire it to a **throttled** `pointermove` (rAF-coalesced), and set `raycast={() => null}` on
the visible `InstancedMesh` so R3F's own event system never walks the instances.

### 9.4 Camera fly-to, and framing a node with its neighbours

```tsx
// frontend/src/components/world/use-fly-to.ts
'use client';
import type CameraControlsImpl from 'camera-controls';
import { useCallback, type RefObject } from 'react';
import { Box3, Sphere, Vector3 } from 'three';

const _box = new Box3();
const _point = new Vector3();

export function useFlyTo(
  controls: RefObject<CameraControlsImpl | null>,
  positions: Float32Array,
  radii: Float32Array,
  /** index -> first-degree neighbour indices, built once from edges.bin. */
  adjacency: readonly (readonly number[])[],
) {
  const reduceMotion =
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /** Frame the node plus its first-degree neighbours. Resolves when the camera rests. */
  const flyToNeighbourhood = useCallback(
    async (index: number, padding = 1.35): Promise<void> => {
      const controller = controls.current;
      if (!controller) return;

      const members = [index, ...(adjacency[index] ?? [])];
      _box.makeEmpty();
      let maxRadius = 0;
      for (const i of members) {
        _point.set(positions[i * 3], positions[i * 3 + 1], positions[i * 3 + 2]);
        _box.expandByPoint(_point);
        maxRadius = Math.max(maxRadius, radii[i]);
      }

      const sphere = _box.getBoundingSphere(new Sphere());
      // Inflate so the outermost node's own geometry is not clipped by the frame.
      sphere.radius = (sphere.radius + maxRadius) * padding;

      // Orbit around the selected node rather than the subgraph centroid: it is what
      // the reader clicked, so it is what the camera should pivot on.
      controller.setOrbitPoint(
        positions[index * 3], positions[index * 3 + 1], positions[index * 3 + 2],
      );

      // fitToSphere does the FOV/aspect maths, including the horizontal term that a
      // vertical-only distance calculation gets wrong on a portrait phone.
      await controller.fitToSphere(sphere, !reduceMotion);
    },
    [controls, positions, radii, adjacency, reduceMotion],
  );

  /** Single node, close in. */
  const flyToNode = useCallback(
    async (index: number, distance = 90): Promise<void> => {
      const controller = controls.current;
      if (!controller) return;
      const [x, y, z] = [
        positions[index * 3], positions[index * 3 + 1], positions[index * 3 + 2],
      ];
      // Approach along the current view direction so the move reads as a dolly,
      // not a teleport to an arbitrary side of the node.
      const from = controller.camera.position.clone().sub(new Vector3(x, y, z));
      if (from.lengthSq() < 1e-6) from.set(0, 0, 1);
      from.normalize().multiplyScalar(distance);
      await controller.setLookAt(
        x + from.x, y + from.y, z + from.z, x, y, z, !reduceMotion,
      );
    },
    [controls, positions, reduceMotion],
  );

  return { flyToNode, flyToNeighbourhood };
}
```

```tsx
// Mounting it: one Canvas, CameraControls with real damping.
<Canvas
  dpr={[1, 2]}
  camera={{ fov: 55, near: 1, far: 8000, position: [0, 0, 900] }}
  gl={{ antialias: true, powerPreference: 'high-performance' }}
  // R3F's own raycaster never needs to walk the instances: picking is on the GPU.
  raycaster={{ firstHitOnly: true }}
>
  <CameraControls
    ref={controlsRef}
    makeDefault
    smoothTime={0.25}
    draggingSmoothTime={0.125}
    minDistance={40}
    maxDistance={3000}
    onRest={() => setLabelQuality('full')}
    onControlStart={() => setLabelQuality('cheap')}
  />
  <ambientLight intensity={0.8} />
  <directionalLight position={[300, 400, 500]} intensity={1.1} />
  <InstancedNodes buffers={buffers} palette={PALETTE} selected={selected} />
  <GraphEdges buffers={edgeBuffers} />
  <AdaptiveDpr pixelated />
</Canvas>
```

---

## 10. Risks and mitigations

| # | risk | likelihood | impact | mitigation |
|---|---|---|---|---|
| **R1** | **Devanagari is rendered with a WebGL text library and comes out wrong.** troika (and therefore drei `<Text>`) has no Indic shaping — issue #303, open since 2024-01-30 — and it fails *silently*: matras misplaced, conjuncts unformed, no error. | **High** if nobody is told; it is the default choice | **Severe** — a Vedic product displaying malformed Sanskrit | Canvas2D/DOM overlay for all Devanagari (§4.5). Add a Playwright visual check that renders a known conjunct (`अग्नि`, `इन्द्रः`) and compares against a DOM-rendered reference. Put a comment at the import site forbidding drei `<Text>` for Sanskrit. |
| **R2** | **The World View is built from the live API and is therefore impossible or wrong.** The neighbourhood endpoint caps at 400 nodes and discloses truncation for a reason; stitching many calls into a "whole graph" would silently violate its bounds. | Medium | High — weeks of work, then a dishonest picture | Build-time artifact from a new `vedagraph export world-view` CLI command reading Neo4j directly (§8.1). Never widen an API bound to feed a view. |
| **R3** | **A World View showing ~1,060 of 108,779 nodes reads as "the whole graph".** This is this repository's own recurring failure: a query returning only positive rows lets the reader infer a false zero. | **High** — it is the default reading of any "world" map | High — a credibility failure, the kind this product's QA discipline exists to catch | `meta.json` states the exclusions and the UI renders them **in the view**, not in a footnote: a persistent legend saying which strata are drawn, which are aggregated into meta-nodes, and which are omitted, with counts. |
| **R4** | **Hover picking freezes the main thread.** `InstancedMesh.raycast` is O(count) with a full triangle test per instance and only a union-sphere early-out. | High if raycasting is used above ~2k nodes | High — the view feels broken | GPU picking from day one (§9.3), `raycast={() => null}` on the visible mesh, rAF-coalesced pointermove, drop-not-queue while a read is in flight. |
| **R5** | **Two copies of `three` in the bundle.** Any dependency that declares `three` as a hard `dependency` (`3d-force-graph` does: `">=0.179 <1"`) can resolve its own copy — every `instanceof` check across the boundary then fails and the bundle carries three twice (~360 KB gz). | Medium (certain if `react-force-graph-3d` is adopted) | High — silent, baffling runtime failures | Do not adopt `3d-force-graph`/`react-force-graph-3d`. Pin `three` exactly and add a pnpm `overrides` entry. Add a CI assertion that `pnpm why three` reports exactly one version. |
| **R6** | **`react@19.3` lands and breaks R3F.** R3F 9.7's peer is `>=19 <19.3` — an *upper* bound most people never read. | Medium over a year | Medium — dev-time breakage, install failures | Pin `react`/`react-dom` to `19.2.x` exactly (they already are). Treat a React minor as an R3F-coupled upgrade with its own test pass. Do not move to R3F v10 while it is alpha. |
| **R7** | **WebGL context exhaustion.** ~16 contexts per page in Chrome; HMR leaks one per edit if a renderer or scene lives at module scope, and one `<Canvas>` per card burns the budget fast. | Medium | Medium — blank canvases, blamed on data | One `<Canvas>`; drei `<View>` for multiple viewports; all GPU objects inside refs/effects with disposal in cleanup; handle `webglcontextlost` by rendering the 2D fallback. |
| **R8** | **Cross-origin isolation for `SharedArrayBuffer` breaks the recitation audio.** COEP `require-corp` blocks cross-origin subresources that do not send CORP, and the audio streams from vedsearch.org, which we do not control. | Medium if SAB is pursued | High — silently kills a shipped feature | Use transferable `ArrayBuffer` ping-pong, not `SharedArrayBuffer` (§3.6). At 1,060–30,000 nodes the buffer is 12.7–360 KB and a transfer is a pointer hand-off. |
| **R9** | **Worker 404s in production.** Turbopack only detects the literal inline `new Worker(new URL('./x.worker.ts', import.meta.url))` shape; a hoisted URL or a string path builds clean and fails at runtime. | Medium | Medium — dev works, prod does not | Keep the expression literal and inline; add a Playwright smoke test that asserts the worker posts `ready` against a **production** build, not `next dev`. |
| **R10** | **The drei barrel lands 488 KB gzip in the client bundle.** It tree-shakes in principle (`sideEffects: false`) but drags `@mediapipe/tasks-vision`, `hls.js`, `three-stdlib`, troika and three-mesh-bvh if it does not. | Medium | Medium — a 700 KB route | Import narrowly; add a bundle-size budget assertion for the world-view route to CI and let it fail the build, rather than trusting the tree-shaker. |
| **R11** | **Degree-1..5,459 blows up the layout.** Uniform `forceManyBody` lets Agni dominate the entire field; the periphery smears and the map is unreadable. | High if defaults are used | Medium — the view looks wrong rather than breaks | `distanceMax(300)`, log-normalised charge strength, degree-scaled spring strength, emulated mass by velocity damping (§6.2). Precompute and **freeze** the World View layout so it is stable across sessions and can be inspected before it ships. |
| **R12** | **StrictMode double-allocation leaks GPU memory in dev**, and an over-eager cleanup that calls `loseContext()` poisons the StrictMode remount (the same canvas element returns the same dead context). | Medium | Low–Medium — dev-only, but wastes days | Allocate in `useLayoutEffect` with disposal in cleanup, never in `useMemo`. Never call `loseContext()` in a cleanup. Leave `reactStrictMode` on: the false alarm in R3F #3598 (an r3f-perf artifact) is not a reason to disable it. |

---

## Appendix A — sources

Read on 2026-09-13.

- npm registry manifests: `three`, `@react-three/fiber`, `@react-three/drei`,
  `react-force-graph-3d`, `react-kapsule`, `3d-force-graph`, `three-forcegraph`, `sigma`,
  `graphology`, `graphology-layout-forceatlas2`, `d3-force-3d`, `ngraph.forcelayout`,
  `ngraph.graph`, `troika-three-text`, `three-text`, `@cosmograph/cosmos`, `deck.gl`,
  `@deck.gl-community/graph-layers`, `camera-controls`, `three-mesh-bvh`.
- `protectwise/troika` issue [#303 "troika-three-text: Indic shaping"](https://github.com/protectwise/troika/issues/303) — open, 2024-01-30, zero comments.
- `pmndrs/react-three-fiber` issue [#3598](https://github.com/pmndrs/react-three-fiber/issues/3598) — closed; cause was `utsuboco/r3f-perf`, not R3F.
- `pmndrs/react-three-fiber` [v9 migration guide](https://r3f.docs.pmnd.rs/tutorials/v9-migration-guide).
- `three@r186` source: `src/objects/InstancedMesh.js` (`computeBoundingSphere`, `raycast`),
  `src/renderers/WebGLRenderer.js` (`readRenderTargetPixelsAsync`),
  `examples/jsm/capabilities/WebGL.js`, `examples/jsm/lines/`.
- `yomotsu/camera-controls` source: `src/CameraControls.ts` (`fitToSphere`, `fitToBox`,
  `setLookAt`, `lerpLookAt`, `setOrbitPoint`, `smoothTime`, `draggingSmoothTime`).
- `vasturiano/react-kapsule` source: `src/index.js`.
- [Cosmograph licensing](https://cosmograph.app/licensing/) — CC-BY-NC-4.0.
- [Turbopack: What's New in Next.js 16.2 / 16.3](https://nextjs.org/blog/next-16-3-turbopack) — Web Worker chunking.
- [MDN: Cross-Origin-Embedder-Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Cross-Origin-Embedder-Policy).
- This repository: `src/vedagraph/api/services/graph_service.py`,
  `src/vedagraph/api/config.py`, `src/vedagraph/api/routes/graph.py`,
  `src/vedagraph/product/audio/vedsearch.py`,
  `docs/reports/KNOWLEDGE_MODEL_V3_BASELINE_AUDIT.md`, `README.md`,
  `frontend/src/components/graph-canvas.tsx`, `frontend/next.config.ts`,
  `frontend/package.json`.
