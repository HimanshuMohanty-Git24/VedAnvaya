# VedaGraph — Frontend Product V1

Starting commit: `f39377a`. The knowledge system is frozen; this phase builds the
first human surface on top of the FastAPI Product V1 boundary and changes nothing
behind it.

## Architectural boundary

The frontend talks only to FastAPI. No Neo4j driver, no Cypher, no graph files, no
reimplementation of ontology logic, no client-side inference of caveats or
certainty. `VEDAGRAPH_API_URL` is read on the server; interactive components reach
the same service through a same-origin `/backend/*` rewrite so no API base URL is
inlined into client code.

## Stack

| Choice | Why |
| --- | --- |
| Next.js App Router, React, TypeScript | Server-render the reading surfaces; keep the graph renderer off routes that do not use it. |
| Plain CSS design system over Tailwind's reset | One stylesheet owns the atlas language: warm paper, ink, hairlines, one accent. Utility soup would have made the knowledge-status vocabulary harder to keep consistent. |
| Radix primitives (dialog, tabs) | Accessible drawer and tab semantics without adopting a whole component theme. |
| `openapi-typescript` | Every response type is derived from the live OpenAPI schema rather than hand-copied. |
| **Cytoscape.js** | See below. |

### Graph library

Evaluated Cytoscape.js, React Flow and Sigma.js against what this explorer needs:
mixed semantic node types with distinct shapes, readable edge labels, incremental
expansion and collapse, force layout over a few hundred nodes, and selection of
both nodes and edges.

Cytoscape.js was chosen. React Flow is built for authored diagrams and node-based
editors, so an organic force layout over an arbitrary neighbourhood is against its
grain. Sigma.js scales to far larger graphs than this product draws, but its
styling model is thinner and edge-level interaction is more work. Cytoscape gives
a declarative stylesheet keyed on data attributes — which is exactly how the
semantic-type styling and the "unresolved devata slot" distinction are expressed —
plus first-class edge tap handling for the evidence panel. It is loaded through a
dynamic `import()` so it never ships to the reader or search routes.

## API capability → UI surface

| API | Surface |
| --- | --- |
| `/stats`, `/works` | Home metrics, four-Veda cards, `/vedas` |
| `/works/{id}/root`, `/passages/{key}/children` | Native structural browser per collection |
| `/passages/{key}/reader` | The mantra reader |
| `/passages/{key}/parallels` | Reader "Connections" tab and `/reuse/{key}` |
| `/search` | Global search with type, collection and language filters |
| `/devatas`, `/devatas/{id}` | Deity atlas and profile |
| `/devatas/{id}/passages` | Named-in versus dedicated-to passage columns |
| `/insights/devatas/{id}` | Attribution split, derived measures |
| `/entities`, `/entities/{type}`, `/entities/{type}/{id}` | Entity index, typed lists, profiles, seer panel |
| `/rituals`, `/rituals/{id}` | Ritual explorer |
| `/formula-families/{id}` | Formula family tree and occurrences |
| `/insights/cross-veda`, `/insights/formula-diffusion` | `/connections` |
| `/insights/atharvaveda/concerns` | `/explore/atharvaveda` |
| `/insights/material-culture`, `/insights/metals` | `/material-culture` |
| `/insights/civilization` | `/insights` — data, derived, interpretation kept apart |
| `/insights/capabilities` | `/limits` |
| `/graph/neighborhood/{id}`, `/graph/relationships/{id}` | `/graph` and the evidence drawer |

## Truthfulness rules the UI enforces

- A null is never drawn as a zero. `MeasureChart` renders an explained status
  instead of a zero-length bar.
- `NO_LEXICAL_MATCH` reads as a fact about the matcher; `INSUFFICIENT_EVIDENCE`
  never reads as an absence; `NOT_BUILT` never reads as a finding.
- Deity analytics default to certain plus probable. Ambiguous mentions are stated
  separately and never folded into a headline number.
- A `DEVATA`-typed node is only drawn as a deity when the backend resolved it as
  one; the ascription slot also holds human patrons.
- Afflictions, threats and named causes are three different things on every
  surface that shows conditions.
- Internal bookkeeping types never reach the graph explorer; reified ascription
  and assertion records are drawn as "Evidence record", not as subject matter.
- Interpretation is visually distinct from measured data, and trust tiers are
  translated before they reach a reader.

## Routes

`/` · `/vedas` · `/vedas/{veda}` · `/passage/{key}` · `/reuse/{key}` · `/search` ·
`/devatas` · `/devatas/{id}` · `/entities` · `/entities/{type}` ·
`/entities/{type}/{id}` · `/rituals` · `/rituals/{id}` · `/formulas` ·
`/formula-families/{id}` · `/connections` · `/explore` · `/explore/atharvaveda` ·
`/material-culture` · `/insights` · `/limits` · `/graph`

Navigation is laid out so an "Ask VedaGraph" entry point can be added beside
Search without a restructure. No chat, LLM call or GraphRAG surface exists yet.
