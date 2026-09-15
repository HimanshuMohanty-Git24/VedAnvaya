# Phase 9 release baseline

**Starting commit:** `24be1f3`
**Release branch:** `phase-9-final-release`
**Captured:** 2026-09-15 (Windows / PowerShell)

## Product inventory

- Frontend route families: home; Vedas and their hierarchy; passages; search; deities and
  entities; Ask; Knowledge World; Visualization Lab; About; Sources & Methodology; limits and
  evidence surfaces. `/lab` permanently redirects to `/visualizations`; `/methodology`
  permanently redirects to `/sources`.
- API health at baseline: `200`, service `vedagraph-api`, API version `1.0.0`.
- Frozen graph census: **108,779 nodes**, **265,295 relationships**, four works.
- Audio catalog: **16,834** text-verified mantra recordings.
- Production identity assets present: favicon, apple touch icon, 192/512px icons, web manifest
  and a 1200×630 OpenGraph image.
- Existing graph performance baseline: home JavaScript 639.6 KB; graph JavaScript 1,310.0 KB;
  `world.bin` 2,435.5 KB uncompressed. Immutable cache and `Vary: Accept-Encoding` are set.

## Startup and deployment assumptions

Run `powershell -ExecutionPolicy Bypass -File scripts\doctor.ps1`, then
`powershell -ExecutionPolicy Bypass -File scripts\start-product.ps1`. A local Neo4j graph is a
prerequisite; Ask is optional and configured only through environment variables. Frontend
production metadata requires `VEDANVAYA_SITE_URL` to be the deployed HTTPS origin.

## Existing release backlog triage

| Class | Item | Phase 9 disposition |
|---|---|---|
| P1 | Graph route prefetch brings renderer assets onto ordinary pages | Fixed: every visible `/graph` navigation entry now opts out of automatic prefetch |
| P1 | Owner wording on About | Fix |
| P1 | SEO/share metadata, sitemap and robots foundations | Fix |
| P2 | Precompressed `world.bin` delivery | Deployment concern; retain immutable cache and document |
| P2 | Ask provider latency (`PERF_BACKLOG_01`) | Provider-bound; no architecture change |
| P2 | Source-page length on mobile | Preserve direct methodological prose; existing contents navigation remains |
| P2 | Metres not drawn; formula-family handoff; GPU mobile measurement limitation | Product V2 / measurement backlog |

## Known pre-release test posture

The standard frontend suite uses installed Edge because Playwright browser binaries were not
available in the environment. Live Ask tests are opt-in and excluded from the normal release
gate to avoid provider spend. The backend default suite excludes live and paid-provider tests.

## Phase 9 verification record

- `pnpm lint`, `pnpm typecheck`, `pnpm test` and `pnpm run audit` pass. The frontend unit suite
  reports **434 passing tests**. `pnpm build` completes and emits the `robots.txt` and
  `sitemap.xml` routes.
- Full browser QA passes: **236 passing and 2 opt-in-live skips** across desktop Edge and a
  390×844 mobile viewport. It covers reader, audio, graph Focus/World/2D/Path, every Lab plate,
  keyboard navigation, offline/error states, reduced motion, contrast and responsive behavior.
- The production artifact contains the current home title, canonical URL, `index, follow` robots
  directive and shared 1200×630 OpenGraph card. Development intentionally emits `noindex,
  nofollow` and disallows crawling.
- `python -m pytest -m "not live and not api"` passes: **3,091 passed, 39 skipped, 35
  deselected** in 23:59. The skips are optional 1856-scan fixtures not present in this checkout;
  live/provider tests remain deliberately out of the standard gate.
- `python -m mypy` passes for **224 source files**. Audio catalog validation passes all checks.
  Four representative provenance hosts returned HTTP 200. No tracked `.env` file or real
  credential pattern was found; the two regex matches are intentional test sentinels.

## Remaining non-blocking items

- `ruff check .` has eight existing, unrelated style findings in
  `scripts/build_brand_assets.py` and `scripts/export_graph_world.py`; they are not modified in
  this release closure to avoid a broad mechanical rewrite.
- `world.bin` precompression remains a deployment P2. The graph is no longer automatically
  prefetched from visible editorial navigation, but server-side compressed-asset delivery still
  needs host-level configuration before a later performance pass.

## Release decision

**GO — ship candidate.** Product V1 is graph- and ontology-frozen, startup checks are ready,
all release-critical application tests pass, and the remaining items are documented P2 or
pre-existing tooling debt. No deployment or tag is created by this phase.
