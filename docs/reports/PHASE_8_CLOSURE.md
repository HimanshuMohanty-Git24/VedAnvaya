# Phase 8 closure — Visualization Lab and the editorial institution pages

## 1–4. Run

| | |
| --- | --- |
| Starting commit | `2398b81` |
| Ending commit | recorded in the commit that carries this report |
| Elapsed | ~2h from the first API probe (2026-09-14 23:13) to the closing gate (2026-09-15 01:10) |
| Agents | One. No subagents were used. |

Neo4j and the product API were live throughout and every figure below was read from the
running service.

## 5–6. The Lab

**Route:** `/visualizations`, reached from a primary navigation slot labelled **Visualize** —
the slot `components/navigation.ts` had been holding empty for exactly this surface. `/lab`
redirects to it permanently.

**Seven plates**, one route each at `/visualizations/[plate]`. The index also carries two
**declared omissions**: figures that were planned and refused, printed beside the ones that
shipped so the index does not read as the set of things the corpus supports.

## 7–11. Plate by plate

Every plate answers the five questions of the visualization standard as typed fields on
`PlateLabel`, so a plate cannot be written without answering them, and the answers are
rendered as a wall label at reading size rather than as a collapsed disclosure.

### Four corpora, side by side — `/visualizations/four-corpora`

- **Question.** How are the four Vedas structurally different?
- **Data.** `/works`, `/audio/stats`, `/insights/cross-veda`, plus the committed provenance
  dataset for each collection's own division names.
- **Interaction.** A scale control — counts, or per 1,000 verses against a stated denominator
  that differs by row. Both states have an address.
- **Handoff.** The four collections, the transmission plate, the sources page, the limits page.
- **Caveat.** Six properties on six scales, never summed. Two of the six are not counts at all
  and are set as prose rather than invented as a quantity.

### Named, and dedicated to — `/visualizations/deities`

- **Question.** Which deities shape each Veda, and are they the deities the hymns are given to?
- **Data.** `/devatas` for the ranking, `/insights/devatas/{id}` for each of the top twelve.
- **Interaction.** A certainty control: the default excludes AMBIGUOUS, and the exploratory
  view says in a boxed note how many ambiguous mentions it has added and that the totals are
  upper bounds.
- **Handoff.** Each deity row links to its record; Ask opens with the leading deity as context.
- **Caveat.** Naming spans four collections, dedication spans one. Both columns count verses
  and share one scale; what they do not share is scope. The mention layer is two instruments —
  a manual Rigvedic lemma annotation and surface matching elsewhere — and the plate says so.

### What the collections share — `/visualizations/transmission`

- **Question.** Where does Rigvedic material reappear in the Samaveda?
- **Data.** `/insights/cross-veda` for the 6 × 8 matrix, `/insights/formula-diffusion` for the
  reuse witnesses, `/search` to resolve both ends of each pair to a canonical key.
- **Interaction.** Hover titles on every non-numeric cell; both ends of every reuse pair click
  through to the verse.
- **Handoff.** The connections index, the formulas plate, the Samaveda, the method page.
- **Caveat.** All 48 cells are drawn and each carries its own status. 25 are measured; the
  other 23 print one of four marks saying which kind of non-measurement they are.

### How a wording travels — `/visualizations/formulas`

- **Question.** How do fixed phrases move between the four collections?
- **Data.** `/insights/formula-diffusion` — the complete span census over all 720 families.
- **Interaction.** Each family's representative wording is a filtered search.
- **Handoff.** The family index, the transmission plate, search, the method page.
- **Caveat.** Families are normalised string matches. Shared diction is a shared idiom, not a
  demonstrated line of transmission.

### What people asked for — `/visualizations/human-concerns`

- **Question.** What human concerns does the Atharvaveda address, and how do the other three
  compare?
- **Data.** `/insights/atharvaveda/concerns`, plus `/entities/condition` to make both panels'
  rows clickable rather than leaving one a dead end.
- **Interaction.** Every row links to its condition record.
- **Handoff.** The Atharvaveda lens, all 26 conditions, the collection itself, the limits page.
- **Caveat.** Afflictions and threats are two panels on two scales and there is no view in
  which they form one list. Counts are Sanskrit lexical minima, never diagnoses.

### The rite, as far as it is modelled — `/visualizations/ritual`

- **Question.** What does the corpus say about ritual, and how much of it has been modelled?
- **Data.** `/insights/rituals`.
- **Interaction.** Each rite links to its record.
- **Handoff.** The eight rites, the object registry, the material-culture plate, the limits.
- **Caveat.** The coverage statement is rendered above the content and an E2E test asserts
  that ordering. Three step edges across eight rites, so no rite has a recoverable sequence.

### What the corpus handles — `/visualizations/material-culture`

- **Question.** What things do the Vedas name, and where?
- **Data.** `/insights/material-culture`, `/insights/metals`.
- **Interaction.** A category control across the five categories the endpoint serves.
- **Handoff.** Every row links to its entity; every metal links to its record.
- **Caveat.** The `ayas` cell is empty and known to be wrong. It is drawn in the caution tone
  with an exclamation mark and the endpoint's own reason printed above the grid, rather than
  quietly corrected.

## 12–15. About — `/about`

Strong. Seven sections, written in the first person, with every figure read from the API
rather than typed in.

- **Project story.** VedaGraph → VedAnvaya, in the order the layers were actually built:
  provenance registry, canonical keys, traditional apparatus, lexical mentions, relationships,
  then the product layers. Records that the ontology was rebuilt three times and frozen once,
  and that the internal `VG:` identifiers deliberately keep the old name.
- **Builder section.** Himanshu Mohanty, in the first person, as a personal project with no
  institutional affiliation. States plainly what he is not — "I am not a Sanskritist and I have
  not represented myself as one anywhere on this site" — and invites correction.
- **What VedAnvaya is not.** Its own section with six entries: not a replacement for reading,
  not philology, not a commentary, not a teacher, not a claim about history, not finished.

## 16–22. Sources and method — `/sources`

One canonical route. `/methodology` redirects to it, because a reader who wants to know where
a verse came from and a reader who wants to know what PROBABLE means are the same reader two
minutes apart.

| Section | Result |
| --- | --- |
| Corpus scope | Four Samhitas with recension, verse count, translation count and full exclusion list per work, read live from `/works`. Names the Yajurvedic exclusion as the one most likely to mislead and the Samavedic one as the largest. |
| Evidence layers | Four, each with an editorial name *and* the technical name that appears in API responses, so a reader who meets `SOURCE_EXPLICIT` in a payload recognises it. |
| Attribution vs mention | Its own section, with a worked example read live from `/insights/devatas/VG:DEVATA:INDRAH` — named total, ascribed total, ascribed scope, and the split between per-verse and container-inherited ascription. |
| Uncertainty | CERTAIN / PROBABLE / AMBIGUOUS defined, with the default stated, plus a subsection on why `NOT_BUILT` and `INSUFFICIENT_EVIDENCE` are different from a measured zero. |
| Ask | Question → registry resolution → retrieval → evidence packet → synthesis → citation validation, with **the model is not the database** set in bold and the provider dependency named as a real limitation. |
| Audio | External layer, streamed and never republished; exact / structural / external-only mappings distinguished; a wrong-recension mapping is rejected rather than approximated. |

## 23. Source inventory

**9 sources and 33 files**, grouped into five layers by what each contributes: the Sanskrit
text, translations, the traditional apparatus, recitation, and sources consulted for
comparison only.

Nothing on the page is hand-written. `scripts/build_frontend_provenance.py` reads
`sources.yaml`, `source_artifacts.yaml` and `works.yaml`, derives which canonical build each
work shipped from out of the registry's own rights line, and refuses to write if a declared
artifact, source or evidence path does not exist — or if a shipped canonical build carries an
artifact no declaration covers. `--check` fails on drift.

One decision worth naming: the terms shown are the **file's**, not the site's. The registry
records GRETIL as UNKNOWN and explains why; the Rigvedic file it serves declares CC BY-NC-SA
in its own TEI header. Both are carried and the page says when they diverge.

## 24–26. Navigation, footer, homepage

- **Navigation.** Visualize fills the sixth primary slot. Sources was relabelled to "Sources
  and method". The bar is now full: a seventh item costs a second line at 1024px.
- **Footer.** Visualizations added to Follow; Sources and method promoted in Check.
- **Homepage.** Two restrained paths, no redesign: one entry appended to the existing
  "Where to start" contents list, and the closing sentence's existing mention of "the sources
  page" turned into the link it was already promising.

Six links to `/about` and `/sources` existed before this phase — in the navigation, the
footer, the homepage close and the 404 page — and all six were 404s. They resolve now.

## 27–29. Visual QA

Captured and inspected at **1440 light, 1440 dark, 1024, and 390**, for the Lab index, all
seven plates, both scale states of the flagship, About and Sources. No overflow and no load
failure at any width in either theme.

Four visual defects were found by inspection and fixed:

1. **`.va-plate` collided with the homepage's featured-verse plate** (`display: grid;
   place-items: center; overflow: clip`). Every plate was laid out inside a centring grid that
   sized its children to max-content and then clipped them; at 390px the page head was 666px
   wide with its right third cut off, and nothing reported a scrollbar because the clip
   absorbed it.
2. **`.va-bars` collided with the homepage's recitation bars** (`display: grid`), which
   replaced `display: table` on the Lab's ranked tables: a 632px table drawing 290px rows, with
   every bar scaled against the wrong width.
3. **The ranked table's header row collapsed**, rendering "Deity" and "Verses" as
   "DeityVerses", because the track width was a `td` rule only.
4. **A measured zero drew a hairline tick**, so the Samaveda's "0 translations" read as
   "almost none" beside the Rigveda's 10,502.

Both collisions are now impossible to reintroduce silently: `scripts/audit-class-collisions.mjs`
fails the `pnpm audit` gate on any `va-` class given a different `display`, `position` or
`overflow` in two stylesheets. It was verified by reintroducing both collisions and confirming
it fails, then removing them and confirming it passes — its first implementation skipped every
second rule and caught neither.

## 30. Accessibility

- Every chart **is** a table: real caption, real row headers, real reading order. The bar is
  drawn inside the cell that already holds the number.
- **No categorical palette anywhere.** A collection is identified by its position in the row
  and by its row header, never by colour, so every figure survives greyscale and dark mode
  without a legend. The one mark whose segments touch separates them by hatch density.
- Every figure carries a visible text description and is `aria-labelledby` its own heading.
- One `h1` per page and no skipped heading level on the Lab, a plate, About and Sources — all
  four asserted in E2E.
- Every control is a link, so each state of a figure has an address and is keyboard-reachable
  with no custom handling.
- The wide matrix lives in a focusable scroll region rather than overflowing the page.

## 31–33. Performance

Median of three cold loads at 1440×900, against `/graph/world` as the ceiling:

| route | ttfb | lcp | dcl | script | prefetch | html |
| --- | --- | --- | --- | --- | --- | --- |
| Lab index | 4 ms | 180 ms | 58 ms | 510 K | 710 K | 53 K |
| Four corpora | 16 ms | 192 ms | 95 ms | 510 K | 710 K | 69 K |
| Deities | 16 ms | 192 ms | 64 ms | 510 K | 710 K | 109 K |
| Transmission | 20 ms | 208 ms | 61 ms | 510 K | 710 K | 88 K |
| About | 3 ms | 168 ms | 58 ms | 510 K | 710 K | 60 K |
| Sources | 8 ms | 188 ms | 53 ms | 510 K | 713 K | 135 K |
| **Knowledge World** | 4 ms | 212 ms | 64 ms | **1,200 K** | 20 K | 33 K |

Every editorial route loads **the same chunks as every other editorial route and nothing
more**; the Knowledge World loads three that none of them does. The 710 K prefetch column is
Next fetching the Graph nav link's route after `load`, at low priority — pre-existing on every
page of the site and off the critical path. Splitting the budget at the load event is what
makes these numbers mean anything: totalling both reported 1,220 K for every route including
About, which is a benchmark that cannot fail.

The Lab ships no client JavaScript of its own. Every control is a link, every reveal is a
`<details>`, and an E2E test asserts that no request matching `three`, `chart` or `d3-` is made
on a plate.

## 34–38. Gates

| Gate | Result |
| --- | --- |
| Unit and component | 434 passed, 21 files. 45 new across three files. |
| E2E | 236 passed, 2 skipped, 0 failed. 61 new across two specs, desktop and 390px. |
| Lint | clean |
| Typecheck | clean |
| Build | clean, 34 routes |
| Token and contrast audit | 352 checks, 0 failing |
| Class collision audit | new; 188 names, 0 collisions |
| `build_frontend_provenance.py --check` | up to date |
| ruff / mypy on the generator | clean |

## 39–40. Mutations

**Neo4j mutations: 0.** Every call made in this phase was an HTTP GET against the read-only
product API. No Cypher was run and no ingestion or projection script was invoked. `/stats` at
the close returns exactly the figures it returned at the open: 22,537 passages, 20,210 mantras,
17,283 translations, 4 works, 184 deities, 616 seers, 575 chandas, 720 formula families, 8
rituals, 6 interpretive claims.

**Ontology mutations: 0.** No registry, schema or domain model was edited. The generator reads
three registry files and writes one JSON under `frontend/public/`.

## 41–42. Adversarial findings

**First pass — 9 findings, all fixed.**

1. `.va-plate` class collision with the homepage (layout, silent).
2. `.va-bars` class collision with the homepage (layout, silent).
3. Ranked table header row collapsed.
4. A measured zero drawn as a visible tick.
5. The two deity columns scaled independently, drawing 3,566 and 2,869 as identical bars.
6. `/sources` claimed "about a third of the pantheon" has an ambiguity problem — a figure
   nothing in the build supports. Replaced with the example that does.
7. The material-culture plate claimed six categories; the endpoint serves five plus an `all`
   pseudo-category. Its summary also named chariots, which is an `OBJECT` and not in any
   category the plate can show.
8. `/sources` said "two sources are consulted and not reproduced" and then described one of
   them wrongly. Now named from the data.
9. The ritual plate claimed the six smaller rites account for "under sixty verses between
   them"; the real figure is 77.

**Second pass — 3 findings, all fixed.**

10. Hand-typed figures in five takeaway paragraphs (a "99.5%", a "more than five times", an
    "every concern", a "roughly ten times"). All are now computed from the same response the
    bars are drawn from, including the sentence that has to change shape when two lists of
    collections turn out to be the same list.
11. The Lab index headline and its metadata counted the catalogue by hand. Both now derive
    from `PLATES.length`.
12. `1 deities` in the ritual rows.

**Third pass — 2 findings in the instruments themselves, both fixed.**

13. The class-collision audit skipped every second CSS rule and reported clean on both of the
    collisions it was written for.
14. The performance harness reported an LCP of 0 ms for every route, because LCP entries are
    only delivered to a `PerformanceObserver`.

**Final adversarial pass: 0 open findings.**

One residual is recorded rather than fixed: the visual-QA harness now skips nodes inside a
deliberate horizontal scroller, which is correct for the cross-corpus matrix and means a
genuine overflow *inside* a scroll region would not be reported. The E2E suite measures that
region's width directly instead.

## 43–44. Tree

Working tree clean at the closing commit. Eight files modified, eighteen added; no file
outside this phase's scope was reformatted.

## 45. Decision

**VEDANVAYA_EDITORIAL_PRODUCT_COMPLETE**

Against the stated conditions: the Lab is coherent and indexed as an atlas rather than a
gallery; seven visualizations ship, each answering a real question and each stating what it
does not show; About and Sources-and-method are both substantial and both close links the
product had been making and not keeping; every source claim is generated from repository
provenance and fails the build if it drifts; the surfaces are responsive at 1440, 1024 and 390
in both themes with zero overflow; the accessibility floor is met by construction rather than
by retrofit; there are no open critical visual findings; E2E, lint, typecheck, build and both
audits are green; and nothing was written to Neo4j or to the ontology.

## 46. Bounded backlog

1. **`/sources` is 19,082px tall at 390.** It is a reference document with a contents list, so
   this is a defensible shape, but the section list is the only navigation once a reader is
   inside it.
2. **The transmission plate costs 28 citation lookups** — two per reuse pair — behind a 60 s
   revalidate, measured at 20 ms TTFB warm and ~760 ms cold. A batch citation-resolution
   endpoint would remove it.
3. **Metres are not drawn.** The metre-to-passage layer does not reach outside the Rigveda in a
   form these surfaces can read. Recorded as a declared omission on the Lab index rather than
   as a backlog item hidden in a document.
4. **The formula families link to a filtered search**, not to their own family record. The
   diffusion endpoint returns a representative wording and no family id, and resolving 720
   families by label would cost four paginated requests.
5. **The About page's institutional-affiliation sentence is an assumption**, not a fact read
   from anywhere. It says the project is personal and unaffiliated, which the repository
   supports but does not state.
6. **`prefetch` ships 710 K on every page**, Three.js included, because the Graph nav link is
   always in the viewport. Pre-existing, off the critical path, and a `prefetch={false}` on one
   nav item away from being 20 K.

## 47. Next phase

`VEDANVAYA_FINAL_PRODUCT_POLISH_SEO_AND_RELEASE`
