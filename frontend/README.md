# VedaGraph frontend

The reading and exploration surface for the VedaGraph corpus: four Vedic Samhitas
presented as one connected atlas.

## Architectural rule

**This application talks only to the VedaGraph FastAPI service.** It never opens a
Neo4j connection, never embeds Cypher, never reads graph files, and never
reimplements ontology logic. Where the API states a coverage status, a certainty
band or a caveat, the UI translates that wording for a reader — it does not infer
one. If a screen needs something the API genuinely lacks, that is recorded as an
API gap rather than worked around in the client.

## Running it

```bash
pnpm install
cp .env.example .env.local      # points at the local FastAPI service
pnpm dev                        # http://localhost:3000
```

The API must be running:

```bash
# from the repository root
.venv/Scripts/python -m uvicorn vedagraph.api.app:app --host 127.0.0.1 --port 8000
```

`VEDAGRAPH_API_URL` is read on the server, both for server-rendered requests and
for the `/backend/*` rewrite that interactive components use. No secret and no
API base URL is inlined into client code.

## Scripts

| Command | What it does |
| --- | --- |
| `pnpm dev` | Development server |
| `pnpm build` / `pnpm start` | Production build and server |
| `pnpm lint` | ESLint, including the React compiler rules |
| `pnpm typecheck` | `tsc --noEmit` |
| `pnpm test` | Vitest unit and component tests |
| `pnpm test:e2e` | Playwright product journeys, desktop and mobile |
| `node tests/visual-qa.mjs` | Screenshots at 1440 / 1024 / 390 plus an overflow report |

`pnpm exec openapi-typescript http://127.0.0.1:8000/openapi.json -o src/lib/api-schema.ts`
regenerates the typed API surface. Every response type in `src/lib/api.ts` is
derived from that file rather than hand-written.

## Layout

```
src/lib/api.ts          typed client, non-throwing loader, shared identifiers
src/lib/knowledge.ts    the one place backend vocabulary becomes reader-facing words
src/components/         shared surfaces: status, caveats, charts, graph, evidence
src/app/                routes
tests/unit              vocabulary and semantics
tests/component         knowledge UI behaviour
tests/e2e               product journeys and the mandatory regressions
```

### Two rules worth knowing before editing

1. **Never render an absence as a zero.** `KnowledgeStatus` and `MeasureChart`
   exist so that a null arrives on screen as "no lexical match" or "insufficient
   evidence", with the reason attached. A bar is only drawn for a real count.
2. **Route params arrive percent-encoded.** Anything read from `params` must pass
   through `routeId()` before being re-encoded into an API path, or the request
   double-encodes and 404s.

## Browsers for Playwright

The suite runs against the Chromium-based browser installed on the machine
(`channel: "msedge"`) because Playwright's own Chromium download was unreachable
from this environment. After a successful `pnpm exec playwright install chromium`,
run with `PLAYWRIGHT_CHANNEL=chromium` to use the pinned build instead.
