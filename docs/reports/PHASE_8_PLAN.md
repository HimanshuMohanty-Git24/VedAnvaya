# Phase 8 — Visualization Lab and the editorial institution pages

Starting commit: `2398b81`. Working tree clean. Neo4j and the product API were both live
during the audit, so every figure below was read from the running service rather than from a
document about it.

The Knowledge World is frozen. Nothing in this plan opens the renderers, the ontology, the
graph state model or the Ask architecture.

## 1. What the audit found

### Six links that already promise pages which do not exist

`components/navigation.ts` puts `/sources` and `/about` in the secondary navigation,
`shell/site-footer.tsx` puts both in the Check column, `app/page.tsx` closes the homepage with
"Built by one person over the sources named on the sources page … About this project", and
`not-found.tsx` offers "About the project" as the way out of a 404. All six links 404 today.

The navigation file also says, in a comment, that the sixth primary slot "is reserved for
Visualize and is held empty until that surface exists, because a navigation item is a promise
that something is there." This phase is the surface that comment was waiting for.

That decides two naming questions without further argument: the Lab is reached from a primary
slot labelled **Visualize**, and the methodology page lives at **`/sources`**, which is where
five existing links already point.

### The API already carries almost everything a visualization needs

| Endpoint | Cost | Warm latency | Carries |
| --- | --- | --- | --- |
| `/works` | point | 81 ms | 4 works, mantra and translated-mantra counts, `excluded_corpora` |
| `/stats` | aggregate | 187 ms | corpus totals, deity population by structure, seer population, cross-Veda edge classes |
| `/insights/cross-veda` | aggregate | 220 ms | 6 corpus pairs x 8 relationship classes, **every cell typed**, 48 of 48 returned |
| `/insights/formula-diffusion` | aggregate | 33 ms | span census, 720 families, widest families with per-Veda occurrences, RV/SV reuse witnesses |
| `/insights/atharvaveda/concerns` | aggregate | 40 ms | 7 concerns, 26 afflictions, 30 protection targets typed AFFLICTION / THREAT / PATHOGEN_OR_CAUSE, 5 social rites |
| `/insights/rituals` | aggregate | 56 ms | 8 modelled rites, 14 curated implements, and a `coverage_view` that states the layer's own thinness |
| `/insights/material-culture` | aggregate | 91 ms | 40 rows across 6 categories, per-Veda and per-1,000 |
| `/insights/metals` | aggregate | — | 7 metals x 4 corpora, 28 cells, plus one **declared gap** that is knowingly wrong (ayas) |
| `/insights/devatas/{id}` | point | 66 ms | one deity: `named_by_veda` across four corpora, `per_1000_by_veda`, `ascribed_total`, `ascribed_scope` |
| `/insights/capabilities` | aggregate | — | the recorded limits, already rendered by `/limits` |
| `/audio/stats` | point | — | 16,834 recitations, `mapped_scope_keys_by_veda`, SV zero |

Nothing here needs a new backend query. The one new endpoint this phase considered — a bulk
deity-by-Veda table — is not needed: twelve point reads at 66 ms resolve in parallel inside one
server render.

### What is already built, and must not be rebuilt

`/explore` is an index of five **lenses**, each a browsable list surface: `/devatas`,
`/rituals`, `/explore/atharvaveda`, `/material-culture`, `/connections`. `/insights` separates
DATA, DERIVED_METRIC and INTERPRETIVE_CLAIM. `/limits` renders the capability catalogue.

So the Lab is not another list of lenses. **A lens is a way to browse; a plate is a single
comparative figure that answers one question.** Every plate links out to the lens that holds
the underlying rows, and the Lab index says so in as many words.

### Components and conventions to reuse rather than reinvent

- `components/measure.tsx` — `MeasureChart`, already "a bar chart that is also a table", with a
  null drawn as `KnowledgeStatus` rather than a zero-length bar. The Lab's visual grammar
  starts here.
- `components/status.tsx` — `KnowledgeStatus`, `Caveat`, `CaveatList`, `InterpretationFrame`.
- `components/ask/ask-about-button.tsx` — the contextual handoff into Ask.
- `lib/knowledge.ts` — `conditionLabel` / `conditionNote` already keep AFFLICTION, THREAT and
  PATHOGEN_OR_CAUSE apart; `parallelKindCopy` already refuses to collapse five relationship
  classes into "similarity".
- `lib/api.ts` — `load()`, the non-throwing server fetch, and the generated `api-schema.ts`.
- Page chrome: `.va-page` / `.va-page-head` from `styles/corpus.css`, which is the rebuilt
  surface vocabulary. The legacy `.shell.page` chrome is not used for new work.
- No charting dependency is installed and none is being added. Every plate is native SVG or
  CSS grid.

### What the data cannot support, and which visualizations therefore die

- **Metres.** `/entities/chandas` gives 575 metres with a `passage_count` but no per-Veda
  split, and the detail view for anuṣṭup returns `rv: 783` with null for the other three. The
  metre-to-passage layer does not reach outside the Rigveda in a form this surface can read,
  and `stats` warns that the RV and AV metre vocabularies are disjoint sets, so a single
  ranked bar chart of metre names would be a chart of the Rigveda labelled as the corpus.
  Section 16 of the brief says build this only if it is cheap. It is not. **Not shipped**, and
  named as not shipped on the Lab index.
- **Deity communities.** `/insights/capabilities` records this as NOT_ANSWERABLE with zero
  nodes carrying a partition. No plate will imply one.

## 2. Capability → surface

| Capability already in the API | Editorial surface | Plate |
| --- | --- | --- |
| `/works` + `/stats` + `/audio/stats` | Lab | **Four corpora, side by side** — aligned small multiples, never summed |
| `/devatas` + `/insights/devatas/{id}` x12 | Lab | **Named, and dedicated** — mention vs ascription, two scopes, never one bar |
| `/insights/cross-veda` + `formula-diffusion.reuse_witnesses` | Lab | **What the collections share** — typed pair/class matrix, then real RV→SV witnesses |
| `/insights/formula-diffusion` | Lab | **How a wording travels** — span census + widest families, per-Veda occurrence strips |
| `/insights/atharvaveda/concerns` | Lab | **What people asked for** — afflictions and threats on separate axes |
| `/insights/rituals` | Lab | **The rite, as far as it is modelled** — coverage stated before content |
| `/insights/material-culture` + `/insights/metals` | Lab | **What the corpus handles** — with the ayas declared gap kept visible |
| registries in `data/registry/` | `/sources` | source inventory, grouped by what each contributes |
| `/works` scope statements, `/insights/capabilities` | `/sources` | corpus scope, known limitations |
| repository history and the builder's own account | `/about` | project story, builder section, what this is not |

Seven plates. Six are required by the brief; material culture is the seventh and is cheap
because the endpoint is already paginated and typed.

## 3. Routes

- `/visualizations` — the Lab index. Primary nav slot six, labelled **Visualize**.
- `/visualizations/[plate]` — one plate per route, so each is independently lazy and each has
  its own metadata and its own share card.
- `/lab` — redirect to `/visualizations`.
- `/about` — the project, the builder, and what this is not.
- `/sources` — sources **and** method, one canonical page. `/methodology` redirects to it.

## 4. The standard every plate must meet before it ships

Section 6 of the brief, restated as a checklist the code can be read against. A plate that
cannot answer all five is cut, not softened:

1. what is measured
2. what one mark represents
3. what corpus scope is included
4. what is excluded
5. what the reader must not infer

Each plate carries a headline, one explanatory paragraph, a method note, a takeaway, and an
evidence handoff — a link to the passage, entity, filtered lens or Ask context that the datum
came from. No plate is allowed to be a dead end.

## 5. Provenance data for `/sources`

The graph carries `source_id`, `witness_id` and `rights_status` per text surface and per
translation, but there is no endpoint that lists the sources themselves. The registries do:
`data/registry/sources.yaml` (18 sources), `source_artifacts.yaml` (53 artifacts with
checksums, retrieval dates and verbatim licence statements) and `text_versions.yaml` (15 loaded
text versions).

A Python generator reads those three files and writes
`frontend/public/data/provenance.json`, which the page reads from disk the same way the
homepage reads `public/data/home-world.json`. No source name is written by hand. A test
asserts the shipped JSON still matches the registries, so a registry edit that is not
regenerated fails rather than drifts.

## 6. Order of work

1. Provenance generator and its contract test.
2. Lab shell: route, index, plate chrome, stylesheet.
3. Plates, in brief order, each with its data contract test.
4. `/about`.
5. `/sources`.
6. Navigation, footer, homepage path, redirects, metadata.
7. Tests: component, contract, E2E, responsive.
8. Visual QA at 1440 light, 1440 dark, 390.
9. Copy pass.
10. Adversarial pass, then the gate.

## 7. Explicitly not in this phase

No homepage, reader, Ask or Knowledge World redesign. No ontology or Neo4j write of any kind —
the API is read-only and nothing here calls anything else. No new corpus source, no enrichment
pass, no second visualization engine, no accounts, no analytics, no SEO campaign, no release
closure.
