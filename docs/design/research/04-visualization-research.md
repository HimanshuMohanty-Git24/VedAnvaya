# 04 — Visualization / Discovery Research

**Project:** VedAnvaya (VedaGraph product surface)
**Agent:** 4 — Visualization / Discovery Research
**Date:** 2026-09-13
**Baseline commit:** `5c268d1`
**Status:** RESEARCH. Nothing here is authorised for implementation; §5 lists what the API
must gain first.

**Verification convention.** Figures marked **(measured)** were computed or probed during
this research — palette contrast and colour-blindness distances by a local script (§7.8),
bundle sizes by local esbuild + gzip, endpoint behaviour by live HTTP. Figures marked
*(unverified)* could not be confirmed at a primary source and must not be quoted as fact.

---

## 0. The constraint that governs every decision below

This project's distinguishing property is not its size. It is that **it refuses to let an
empty cell mean "the corpus is silent."** The API already types absence in a vocabulary
most charting libraries cannot express:

| Type | Where it lives | Values |
|---|---|---|
| `KnowledgeStatus` | every response | `SUPPORTED`, `PARTIAL`, `INSUFFICIENT_EVIDENCE`, `NOT_BUILT` |
| `CrossVedaCellStatus` | `/insights/cross-veda` cells | `MEASURED`, `MEASURED_ZERO`, `NOT_ESTABLISHED_FOR_PAIR`, `INTRA_VEDA_ONLY`, `LAYER_ABSENT`, `INCONSISTENT` |
| `MetalEvidenceStatus` | `/insights/metals` cells | `LEXICAL_MATCH_MINIMUM`, `NO_LEXICAL_MATCH` |
| `EvidenceBasis` | every edge | `SOURCE_STATED`, `CONTAINER_INHERITED`, `DETERMINISTIC_DERIVED`, `MODEL_EXTRACTION`, `MODEL_ADJUDICATED`, `TEXTUAL_MENTION`, `UNKNOWN` |
| `EvidenceSurface` | every edge | `SANSKRIT`, `STRUCTURAL`, `SOURCE_METADATA`, `MIXED`, `TRANSLATION`, `SHARED_REGISTRY_ENTITIES`, `UNKNOWN` |
| `AttributionPrecision` | attribution edges | `PER_PASSAGE`, `CONTAINER_INHERITED`, `TEXTUAL_MENTION`, `NOT_AN_ATTRIBUTION`, `UNKNOWN` |
| `ConfidenceBasis` | every edge | `PIPELINE_CONSTANT`, `VARIES_WITHIN_PREDICATE`, `ABSENT` |
| `ReferentCertaintyCounts` | deity mentions | `CERTAIN` / `PROBABLE` / `AMBIGUOUS`, always all three |

Four consequences, and they are not negotiable:

1. **A chart that renders `null` as `0` is a defect in this product, not a rounding
   choice.** `CountedByVeda` fields are `int | None` and the docstring says *"A null means
   not established; it never means zero."* `Paginated._empty_must_explain_itself` already
   *raises* on an empty `SUPPORTED` page. The visual layer needs the same contract; §4
   supplies it.
2. **Every value channel needs more than three states.** Bar length, arc angle, area and
   cell fill give you "big / small / zero". This data needs "big / small / measured-zero /
   not-measured / layer-absent / inconsistent".
3. **Colour alone cannot carry it. (measured)** The two statuses most important to
   distinguish, `NOT_BUILT` and `UNKNOWN`, are both necessarily neutral greys — neither is a
   *value*, so neither may take a series hue — and they sit at ΔE_OKLab **0.020–0.033** from
   each other, 3–15× below the working discriminability threshold, *before* colour-blindness
   is considered. Absence must be carried by **texture and glyph**.
4. **Make absence loud, not quiet.** The instinct to grey missing data down is
   empirically wrong. Song & Szafir, *"Where's My Data? Evaluating Visualizations with
   Missing Data"* (IEEE VIS 2018, https://cmci.colorado.edu/visualab/papers/song_VIS_2018.pdf)
   crossed three treatments — **highlight**, **downplay**, **annotation** — across bar and
   line charts and found that **highlighting missing/imputed values produced the highest
   perceived confidence and perceived data quality.** Downplaying did not.

---

## 1. What the API can actually serve

Read off `src/vedagraph/api/routes/*.py` and `src/vedagraph/api/models/*.py`. Nothing below
is inferred from a brief; every row was read from the code.

### 1.1 Corpus shape

| Corpus | Mantras | Native entry level |
|---|---|---|
| Rigveda (Śākala) | 10,552 | Mandala → Sukta → Mantra (10 → 1,028 → 10,552) |
| Atharvaveda (Śaunaka) | 5,839 | Kanda → Sukta → Mantra (20 kandas) |
| Yajurveda (Śukla, Vājasaneyi-Mādhyandina) | 1,975 | Adhyaya → Mantra (40 adhyayas) |
| Samaveda (Kauthuma ārcika **only**) | 1,844 | Collection → … → Mantra (4 **named** collections) |
| **Total** | **20,210** | Graph: 108,779 nodes / 265,295 relationships, frozen |

Three facts here break naive hierarchy visualizations:

- **The four works enter the tree at four different levels** — 10 Mandalas, 20 Kandas,
  40 Adhyayas, 4 Samavedic Collections (`WorkRoot` docstring). One sunburst rooted at "the
  Vedas" therefore has a first ring whose four sectors are *not the same kind of thing*.
- **The Samavedic `collection` level is a NAME, not an ordinal** (`ARANYA`, `CHANDA`,
  `MAHANAMNYA`, `UTTARA`). `HierarchyLevel.value_kind` is `ORDINAL` or `NAME`, and the
  docstring records that *"a client that assumed integers throughout would fail on 1,844
  verses."*
- **The Samavedic `kanda` division does not nest.** From
  `docs/FOUR_VEDA_STRUCTURAL_MODEL.md`: its colophons *"cut across prapathaka and ardha
  boundaries. A non-nesting division cannot be a hierarchy level without lying about the
  tree."* Partition layouts (icicle / sunburst / treemap) **assume a strict tree**. This
  division must never be a ring.

### 1.2 Endpoints, by what they can feed

| Endpoint | Returns | Feeds |
|---|---|---|
| `GET /works/{id}` | `hierarchy[]`, `passage_counts_by_type`, **`knowledge_layers[]`**, **`attribution_splits[]`**, `translation_coverage`, `text_scripts` | **V1 Layer Availability Matrix** |
| `GET /works/{id}/root`, `GET /passages/{key}/children` | `Paginated[PassageSummary]` with `sequence_in_parent` | **V7 Corpus Icicle** |
| `GET /insights/cross-veda` | 6 pairs × 8 classes = **48 cells, each typed**, plus `MatrixShape.cells_by_status` | **V2 Cross-Veda Reuse Matrix** |
| `GET /insights/formula-diffusion` | `span_census[]` (families by `vedas_reached`), `widest_families[]` (`occurrences_per_veda`), `reuse_witnesses[]` | **V4 Diffusion Alluvial** |
| `GET /insights/metals` | metal × 4 Veda grid, `matched_mantras: int\|None`, `per_1000_mantras`, `corpus_mantras`, `source_witness`, `declared_gaps[]`, `ordering_inverts` | **V3 Evidence Grid** |
| `GET /insights/material-culture` | `VedaCountRow[]` — raw **and** per-1,000 **and** denominators | **V3 Evidence Grid** |
| `GET /insights/rituals`, `/insights/atharvaveda/concerns` | same row shape, `PARTIAL` by construction | V3, faceted |
| `GET /insights/capabilities` | `CapabilityLimit[]`: `verdict`, `why`, `what_this_is_not`, `measurements[]`, `what_would_change_it` | **V8 Limits Map** |
| `GET /insights/civilization` | three sections typed `MEASURED` / `DERIVED` / `INTERPRETED` | V8, V9 |
| `GET /devatas/{id}` | `named_by_veda`, `ascribed_total`, `ascribed_scope`, `certainty` (3 tiers), `mention_surplus` | **V5 Named-vs-Ascribed** |
| `GET /devatas/{id}/passages` | `citation`, `veda`, `basis` (`MENTION`/`ASCRIPTION`), `referent_certainty`, `attribution_precision` | **V6 Invocation Landscape** (blocked, §5.1) |
| `GET /devatas/{id}/network` | `DevataNetworkEdge[]` with **`lift`**, `rv_passage_count`, `non_rv_passage_count`, `per_veda_counts`, `quality_tier` | **V10 Co-occurrence Arc** |
| `GET /graph/relationships/{id}` | `why`, `trust_tier`, `review_status`, `evidence_passages[]` | **V9 Provenance Ribbon** |
| `GET /graph/path?from=&to=` | `hops[]` each with `explanation`, **`hub_mediated: bool`** | **V11 Explained Path Ladder** |
| `GET /graph/neighborhood/{id}` | `NeighbourhoodView` + **`NeighbourhoodBounds`** (`total_degree`, `truncated_types[]`) | existing Cytoscape + **Truncation Gauge** |
| `GET /audio/stats`, `GET /works/{id}/audio` | `by_availability`, `mapped_scope_count` **vs** `playable_scope_count` | **V12 Recitation Coverage Strip** |
| `GET /passages/{key}/parallels` | `relation_kind` (5 kinds), `is_textual_parallelism`, 7 nullable metrics, `match_level`, `veda_pair` | V4 drill-down |

### 1.3 Hard limits the design must respect

1. **`MAX_PAGE_SIZE = 200`** (`src/vedagraph/api/config.py`). Every collection endpoint is
   capped. This is the single biggest visualization blocker in the product (§5.1).
2. **Three machine-readable `cost_class` bands on every insight response**: `POINT_READ`
   (inside the median latency target), `AGGREGATE` (grouped counts, *exempt* from the
   median), `CENSUS` (*no* latency target). `/insights/civilization` is the one `CENSUS`.
   A chart backed by a `CENSUS` must never sit above the fold behind a spinner.
3. **`experimental.proxyTimeout: 345_000`** in `frontend/next.config.ts`, set for
   `POST /ask`. It does not excuse a slow chart; `PERF_BACKLOG_01` is already open on
   full-ladder Sanskrit search >300 ms.
4. **No per-book aggregate exists.** `named_by_veda` is per-*Veda* only. A deity × mandala
   heatmap **cannot be served today**.
5. **No deity × metre aggregate exists.** `DevataProfile.top_chandas` is a bare
   `list[str]` with no counts. A deity × metre matrix **cannot be served today**.
6. **No embeddings exist anywhere in the graph.** Verified: `insight_service.py:426` —
   *"No non-lexical resemblance measure exists anywhere in this graph: no embedding, no
   vector index, no asserted resemblance."* This kills the UMAP/t-SNE "semantic
   constellation" outright (§3.1).
7. **Nothing in this graph is human-reviewed.** `MODEL_ADJUDICATED` is the strongest state.
   A trust-tier ramp must therefore have **no "verified" green at the top**.
8. **`confidence` is often a pipeline constant.** `ConfidenceBasis.PIPELINE_CONSTANT` means
   *"every edge of this predicate carries the same value, so it ranks nothing."* Mapping it
   to opacity would draw a ranking that does not exist.

### 1.4 Frontend baseline

`frontend/package.json`: **Next 16.3.4, React 19.2.8, Tailwind 4, TypeScript 5**, pnpm 10.34.5.
The only visualization dependency is **`cytoscape@3.34.3`**, used by `graph-canvas.tsx`
(383 lines) and `graph-explorer.tsx`. `motion@13` for animation; Radix for dialog/tabs.

A grep for `<svg` across `frontend/src/components/*.tsx` returns **two** hits, both in
`site-header.tsx`. **There is today no data visualization in this product other than the
node-link graph.** Everything else is tables and prose — and those tables are doing real
work. Nothing below should replace a table that already reads correctly; each item earns
its place by answering a question a table answers badly.

### 1.5 The strategic finding: the analytic layer for Vedic corpora does not exist

**VedaWeb** (University of Cologne / CCeH, https://vedaweb.uni-koeln.de/rigveda) is the
closest peer in the world, and it is substantially larger than the published literature
records. Its live API (verified 2026-09-13 against
`https://vedaweb.uni-koeln.de/api/openapi.json`, title "VedaWeb", v0.54.1b0) serves **seven
texts** — Rigveda, Aitareya Brāhmaṇa, Jaiminīya Brāhmaṇa, Maitrāyaṇī Saṁhitā, Śatapatha
Brāhmaṇa, Atharvaveda Śaunaka, Atharvaveda Paippalāda — across **41 registered aligned
resources**: nine Rigvedic editions (Aufrecht, van Nooten & Holland, Lubotsky's Padapāṭha,
the Zurich version, Eichler, Müller, Oldenberg, Grassmann), seven translations (Geldner,
Griffith, Renou, Elizarenkova, MacDonell, Otto), metrical data, per-stanza recitation audio,
live dictionary lookups into the Cologne Digital Sanskrit Dictionaries, and — most relevant
to us — **`locationMetadata` resources titled "Hymn Properties by Geldner (1951–1957)" and
"Stanza Properties by Arnold (1905) and Oldenberg (1888)"**, i.e. addressee, hymn group,
stratum and maṇḍala section modelled as first-class, citable, per-location layers with named
scholarly provenance. Hellwig's Digital Corpus of Sanskrit annotations are ingested as a
resource. The current stack is **FastAPI + Vue 3 + MongoDB** under the *Tekst* platform
(https://github.com/VedaWebProject/Tekst).

**And across its API surface, its resource inventory, its legacy repository and its project
papers, VedaWeb publishes no network, arc, matrix, dispersion or frequency visualization of
any kind.** It is a superbly engineered *aligned-layer reading and search* platform. The
analytic layer it leaves open is exactly the one this document scopes. That is the strategic
case for building anything here at all — and it is also a warning that the reading view, not
the chart, is the primary interface for a Vedic corpus. **Visualization is for the questions
the aligned-layer reader cannot answer.**

---

## 2. Ranked shortlist — the twelve to build

Ranking criterion, in order: (1) does it answer a question a scholar actually has;
(2) can our API serve it **today**; (3) does the form encode absence natively rather than
by bolt-on; (4) is it cheap in bundle and latency.

---

### V1 — The Layer Availability Matrix · *"What do we know about what?"* — **BUILD FIRST**

**Scholarly question.** *For which of the four Samhitas does each knowledge layer exist, and
how far into each does it reach?* This must be answerable **before** any other chart in the
product can be read honestly. The pattern is not guessable: deity ascription is Rigveda-only;
the agentive assertion layer is Rigveda-only; deity ascription *descriptors* are
Atharvaveda-only; metre reaches RV and AV; seers reach three corpora **by two incompatible
instruments**; the Samaveda has no seer layer, no metre layer and zero translations.

**Data.** `GET /works/{id}` → `knowledge_layers[]` (`LayerAvailability`: `layer`, `relation`,
`status`, `passages`, `edges`, `share_of_mantras`, `note`). Four `POINT_READ` calls,
cacheable indefinitely — the graph is frozen. **Servable today, unmodified.**

**Form.** A small matrix. Rows = layer (~8). Columns = the four Samhitas. Each cell is a
*status glyph* plus a horizontal share-of-mantras bar. Not a heatmap: the quantity
(`share_of_mantras`) and the epistemic state (`status`) are different variables and must use
different channels.

```
                     RIGVEDA        SAMAVEDA       YAJURVEDA      ATHARVAVEDA
                     10,552         1,844          1,975          5,839
DEVATA_ASCRIPTION  ▓▓▓▓▓▓▓░░ 79%   ╱╱╱╱╱╱╱╱╱ ∅   ╱╱╱╱╱╱╱╱╱ ∅    ╱╱╱╱╱╱╱╱╱ ∅
DEVATA_MENTION     ▓▓▓▓▓░░░░ 54%   ▓▓░░░░░░░ 18%  ▓▓▓░░░░░░ 31%  ▓▓▓▓░░░░░ 42%
HAS_RISHI          ▓▓▓▓▓▓▓▓▒ 92%◗  ╱╱╱╱╱╱╱╱╱ ∅   ▓▓▓▓▓▓▓▓▓ 99%◗ ▓▓▓▓▓▓▓▓▓ 87%◗
HAS_CHANDAS        ▓▓▓▓▓▓▓▓▓ 97%   ╱╱╱╱╱╱╱╱╱ ∅   ╱╱╱╱╱╱╱╱╱ ∅    ▓▓▓▓▓▓▓░░ 74%
TRANSLATION        ▓▓▓▓▓▓▓▓▒ 98%   ▁▁▁▁▁▁▁▁▁ 0   ▓▓▓░░░░░░ ··   ▓▓▓▓▓░░░░ ··
AGENTIVE_ASSERTION ▓▓░░░░░░░ 21%   ╱╱╱╱╱╱╱╱╱ ∅   ╱╱╱╱╱╱╱╱╱ ∅    ╱╱╱╱╱╱╱╱╱ ∅

   ▓ measured   ╱ NOT_BUILT (layer absent here)   ▁ MEASURED ZERO
   ◗ PARTIAL — hover for the instrument split     ∅ no layer   ·· not established
```

**Interactions.** Hover a cell → the layer's own `note`, verbatim, plus `passages`/`edges`.
Click a `◗` cell → the `AttributionSplit` for that (work, layer): source-stated vs
container-inherited, **never summed**. Click a `╱` cell → the `NOT_BUILT` explanation and,
where one exists, the `what_would_change_it` string from `/insights/capabilities`.

**Absence encoding.** Four treatments, none of which depends on hue, so all survive greyscale
and all three dichromacies: `▓` solid = measured · `▁` flat baseline rule = measured zero
(the Samavedic translation count is a *real* 0 from 1,844 verses) · `╱` 45° hatch =
`NOT_BUILT` · `··` stipple = `INSUFFICIENT_EVIDENCE` / null.

**Failure modes.** (a) Rendering `share_of_mantras` as a colour ramp merges quantity with
status and reintroduces the ambiguity the matrix exists to remove. (b) Sorting rows by
coverage buries `NOT_BUILT` rows at the bottom where they read as "minor"; sort by layer name
or a fixed editorial order. (c) Omitting the column denominators (10,552 / 1,844 / 1,975 /
5,839) invites comparison of raw counts across corpora 5.7× apart.

**Library.** None. CSS Grid + inline SVG. ~2 kB of app code.

---

### V2 — The Cross-Veda Reuse Matrix · *"Which corpora share text, and how?"*

**Scholarly question.** *Between which pairs of Samhitas does material recur, and under which
kind of resemblance claim?* The Samaveda's dependence on the Rigveda is the textbook fact;
what is genuinely informative is everything that is **not** there.

**Data.** `GET /insights/cross-veda`. Exactly 6 corpus pairs × 8 relationship classes =
**48 cells**, enumerated from constants (`_CROSS_VEDA_CLASSES` + `_UNBUILT_CROSS_VEDA_ROWS`)
rather than discovered from the data, and `MatrixShape.cells_expected` lets the client
*assert* it received all 48. Every cell carries one of six statuses, plus
`related_edges_on_pair` and a per-cell `note`. **Servable today. This is the best-specified
visualization surface in the product.**

**Form.** An 8 × 6 matrix. **Not** a chord diagram (§3.2). This follows Sefaria's
architecture, not Harrison's: aggregate to the pair, drill to the witnesses.

```
                          RV↔SV   RV↔YV   RV↔AV   SV↔YV   SV↔AV   YV↔AV
EXACT_PARALLEL_OF         [ 750]  [  12]  [  46]  [▁  0]  [   3]  [  31]
NEAR_PARALLEL_OF          [ ... ]  ...
REUSES_TEXT_FROM          [1684]  [▪ 0 ]  [▪ 0 ]  [▪ 0 ]  [▪ 0 ]  [▪ 0 ]
VARIANT_OF                 ...
PARALLEL_TO                ...
SHARES_ENTITY_VOCAB…       ...
SEMANTIC_RESEMBLANCE      ╱╱╱╱╱  ╱╱╱╱╱  ╱╱╱╱╱  ╱╱╱╱╱  ╱╱╱╱╱  ╱╱╱╱╱   ← NOT_BUILT, all six
SEMANTIC_ASSERTION        ╱╱╱╱╱  ╱╱╱╱╱  ╱╱╱╱╱  ╱╱╱╱╱  ╱╱╱╱╱  ╱╱╱╱╱   ← RV-only layer

  [n] MEASURED   ▪0 NOT_ESTABLISHED_FOR_PAIR — ghost shows related_edges_on_pair
  ▁0  MEASURED_ZERO   ⊂ INTRA_VEDA_ONLY   ╱ LAYER_ABSENT   ⚠ INCONSISTENT
       48 of 48 cells returned ✓   legend chips carry cells_by_status counts
```

**Interactions.** Hover → the cell's own `note`, verbatim. Click a `MEASURED` cell → paged
witnesses via `/passages/{key}/parallels`. A **completeness assertion** runs client-side: if
`cells_returned !== cells_expected`, the component renders an error, not a partial grid.

**Absence encoding.** All six statuses are distinct *marks*, not six colours. The decisive
one is `NOT_ESTABLISHED_FOR_PAIR`: the cell shows a hollow mark **and a ghosted
`related_edges_on_pair` figure**, so a reader who sees no directed reuse between AV and RV
simultaneously sees the parallels that make "the AV does not reuse the RV" impossible to
conclude. The two `NOT_BUILT` rows are present at full height and never collapsed — omitting
them *"would leave a reader with a table of five built classes and no way to know that the
two questions people most want answered across corpora were never built."*

**Failure modes.** (a) Summing a pair's cells into one "relatedness" number — the classes
assert different things; `CrossVedaPairRow.measured_edges_total` is documented as *"Not a
strength score."* (b) Any ordinal colour ramp over cell counts, which would put a 1,684-edge
cell and a 3-edge cell on one scale and make absent cells look like a low end of it.
(c) Dropping the two `NOT_BUILT` rows "because they're empty".

**Library.** None. CSS Grid + SVG glyphs. ~3 kB.

---

### V3 — The Evidence Grid · *"Where is X attested, and does normalising change the answer?"*

**Scholarly question.** *In which corpora is a metal / crop / animal / river / affliction
attested, and at what rate once corpus size is controlled for?* The Rigveda is 5.7× the
Yajurveda by mantra count, so a raw count partly ranks corpus size.

**Data.** `GET /insights/metals` (7 metals × 4) and `GET /insights/material-culture` (crops
5, animals 15, rivers 8, tribes 5, metals 7, curated ritual implements). Each row carries raw
`by_veda`, `per_1000_by_veda`, the denominators, an `evidence_status`, and — critically —
`ordering_inverts: bool` with an `ordering_note`. **Servable today**, `AGGREGATE`.

**Form.** A matrix with a **paired cell**: raw count as a small bar, per-1,000 as a tick on a
shared scale. A row whose `ordering_inverts` is true gets a marginal `⇄` and its
`ordering_note` on hover.

```
                RIGVEDA        SAMAVEDA       YAJURVEDA      ATHARVAVEDA
 ayas  (iron?)  ██▏  47│ 4.5   ▏     2│ 1.1   ╱╱ NO MATCH ⊙  ████ 61│10.4    ⇄
 hiraṇya (gold) ████ 88│ 8.3   █▏    9│ 4.9   █▏     8│ 4.1  ██▏  31│ 5.3
 sīsa  (lead)   ▁     0        ▁     0        ▁     0        ▏     3│ 0.5
                 │ raw          per 1,000 mantras ┘   ⊙ = source_witness exists (VSM 18.13)
     every figure is a Sanskrit lexical-match MINIMUM — a lower bound, stated in the legend
```

**Interactions.** Toggle raw ⇄ normalised (both always visible; the toggle only changes which
drives row *order*, and switching it animates the reorder so the inversion is *seen*). Click
`⊙` → the `DeclaredLexicalGap` row: locator, what else that verse is measured to name, and
the frozen reason the alias was not registered.

**Absence encoding.** Three states, three marks. `▁` flat rule = measured zero.
`╱ NO MATCH` = `NO_LEXICAL_MATCH`, with `matched_mantras` **null, never 0**. `⊙` = the cell
is a known matcher limitation and a witness exists.

**Failure modes.** (a) Showing only the normalised figure — the raw count is the one a reader
intuits, and hiding it hides the inversion. (b) Showing only rows with matches; the zero and
no-match rows are the finding. (c) A sequential colour ramp: `NO_LEXICAL_MATCH` would land at
the pale end, adjacent to "few" — the exact false-zero this product exists to prevent.

**Library.** None.

---

### V4 — The Diffusion Alluvial · *"How far does shared wording travel?"*

**Scholarly question.** *How many formula families are confined to one Samhita, how many reach
two, three, four — and which are the widest?* And, separately and directedly: *which Samavedic
verses are measured to reuse which Rigvedic ones?*

**Data.** `GET /insights/formula-diffusion`: `span_census[]` (`vedas_reached`, `cross_veda`,
`families`, `memberships`, `occurrences`), `widest_families[]` (`occurrences_per_veda`),
`reuse_witnesses[]`. **Servable today**, `AGGREGATE`.

**Form.** Two stacked panels, deliberately separated because they make different claims.

*Panel A — span census (undirected).* A four-band alluvial: left stratum = families grouped
by `vedas_reached` ∈ {1,2,3,4}; right stratum = the four corpora; ribbon width =
`occurrences`. Single-Veda families are **included**, because the docstring is explicit that
they *"are the baseline the cross-Veda ones should be read against rather than a separate
finding."*

*Panel B — directed reuse.* A single arrowed band SV ← RV carrying 1,684 witnesses, and
**five empty slots** for the other pairs, each marked `NOT_ESTABLISHED_FOR_PAIR` with its
`related_edges_on_pair` ghost figure.

```
  A. SHARED WORDING (undirected — co-presence, not transmission)
   reaches 1 ████████████████████████▏        ┐
   reaches 2 ███████▏                          ├──▶ RV  SV  YV  AV
   reaches 3 ██▏                               │
   reaches 4 ▊                                 ┘   no arrowheads. no left-to-right time.
  B. DIRECTED REUSE (REUSES_TEXT_FROM — the only directed class)
   RV ──1,684──▶ SV       RV⇢YV ▪    RV⇢AV ▪    SV⇢YV ▪    SV⇢AV ▪    YV⇢AV ▪
                          └ ▪ = not established for this pair; other classes carry n edges here
```

**Ribbon width must use a saturating scale.** Sefaria's explorer solved exactly this and left
the archaeology in a comment — their original `count / 10` blew out on heavy pairs, and the
shipped function is:

```js
MAX_WIDTH * (1 - 1 / (1 + 0.00003 * count * count))   // capped 70px, floored 1px
```

Our dynamic range is comparable (1,684 against single-digit cells), so a linear map will
produce one visible ribbon and five invisible ones. Adopt a saturating curve and **print the
count as a number beside the ribbon** — thickness is the weakest magnitude channel available.

**Absence encoding.** The five empty directed slots are **drawn at full width as outlines**,
not omitted. This is the lesson in `CrossVedaMatrixResponse`: building the table from the
pairs the data happens to contain is *"how five of `REUSES_TEXT_FROM`'s six pairs disappear
from a table and a reader concludes that only the Samaveda reuses Rigvedic text."*

**Failure modes.** (a) **The dominant one: a Sankey implies flow.** A formula family is *"a
property of shared diction and not of demonstrated transmission."* Panel A must not use
arrowheads, must not read left-to-right as chronology, and must be captioned as co-presence.
Only Panel B is directed. (b) Sankey node ordering is a layout artefact and readers infer
meaning from vertical position; pin the corpus order.

**Library.** `d3-sankey` **for layout only** — **2.82 kB gzip (measured)**, pure computation,
SSR-safe. Render the paths yourself. Do not adopt a Sankey *component*: every one of them
ships its own colour scale and tooltip.

---

### V5 — Named vs Ascribed · *"Do the hymns dedicated to a god actually name it?"*

**Scholarly question.** A genuinely original surface, and one this graph is uniquely
positioned to serve. The Anukramaṇī *ascribes* a hymn to a deity; the verses themselves *name*
deities. These diverge in both directions and neither is the corrected version of the other.

**Data.** `GET /devatas/{id}` → `named_by_veda` (`CountedByVeda`, nullable per corpus),
`named_total`, `ascribed_total`, `ascribed_scope` (RV only), `mention_surplus`, `certainty`
(all three referent tiers). **Servable today**, one deity at a time.

**Form.** A dumbbell / slope chart, one row per deity, **two axes that are never summed**.

```
                 ascribed (RV only, n=10,558)    named (all four corpora, n=17,165)
   Indra          ●─────────────────────────────────────────────○   surplus +2,973
   Agni           ●──────────────────────────────────○               surplus  +214
   Soma                     ●─────────────────────────────────────○  surplus +1,512
   Mitra          ●──○                                                surplus    −4
                  │  ascription band SHADED: Rigveda only. No SV/YV/AV ascription exists.
   certainty split on every "named" endpoint:  ▮certain ▮probable ░ambiguous (excluded by default)
```

**Interactions.** Toggle the ambiguity tier included in "named" — and **watch the value move**.
`ReferentCertaintyCounts` exists precisely because *"a deity whose name is an ordinary noun is
flattered or penalised by that choice."* Soma returns 421 rows under the default tiers while
1,091 `DEITY_AMBIGUOUS` mentions are filtered out; the reader must be able to see that the
number is a quarter of the layer.

**Absence encoding.** The ascription axis is drawn **on a shaded ground labelled "Rigveda
only"**, so an SV/YV/AV deity with zero ascriptions reads as *out of scope*, not as
*unascribed*. A null in `named_by_veda` renders as a hollow tick with `?`, never as a point at
zero; the `note` on `CountedByVeda` surfaces on hover.

**Failure modes.** (a) One bar labelled "passages" that sums the two — wrong by construction.
(b) A diverging bar centred on `mention_surplus` alone, which hides the magnitudes and makes 5
vs 9 look like 1,000 vs 4,000. (c) Ranking by `named_total` without exposing which certainty
tiers are in the total.

**Library.** None.

---

### V6 — The Invocation Landscape · *"Where in the linear text does a deity appear?"* — **BLOCKED**

**Scholarly question.** *Is this deity spread evenly through the corpus, or concentrated in one
mandala / one stratum?* This is the classic **lexical dispersion plot** of corpus linguistics —
NLTK's `dispersion_plot` (https://www.nltk.org/api/nltk.draw.dispersion_plot.html), and Voyant's
**Bubblelines** — applied to the annotation layer rather than to word tokens. It is the
highest-value *discovery* visualization here: clustering is immediately visible and immediately
interpretable, and dispersion is a question no table answers well. Note that dispersion is a
*different* measure from frequency (cf. Juilland's D, Rosengren's S, Gries's DP), and it is the
one a philologist actually asks.

**Data.** `GET /devatas/{id}/passages` → `DevataPassageRef` with `citation`, `veda`, `basis`,
`referent_certainty`. Position in the linear text is derivable by parsing the citation
(`RV 1.1.1`, `AVS 5.7.5`, `VSM 21.46`) — no new field needed.

**BLOCKED by `MAX_PAGE_SIZE = 200`.** Indra's mention layer runs to thousands of rows; one
landscape would take ~18 sequential round-trips. See §5.1.

**Form.** Four horizontal strips, one per Samhita, each scaled to its own length, with a tick
per attesting verse. Two tracks per strip: mention (all four corpora) above, ascription (RV
only) below.

```
 RIGVEDA  |▌ ▌▌  ▌ ▌▌▌▌▌ ▌▌   ▌▌▌▌▌▌▌▌▌▌ ▌▌▌  ▌ ▌▌▌▌▌   ▌▌ ▌▌▌  ▌▌▌▌▌▌▌▌▌ ▌ ▌ |
          |M1   |M2  |M3  |M4 |M5      |M6   |M7   |M8      |M9        |M10 |
  ascr.   |▬▬▬   ▬▬     ▬▬▬▬▬▬▬                 ▬▬▬▬▬▬▬▬       ▬▬▬▬▬▬▬▬▬▬▬  |
 SAMAVEDA |▌  ▌     ▌        ▌   |   (1,844 verses — strip scaled to length, not to RV)
 YAJURVEDA|  ▌ ▌▌         ▌      |
 ATHARVA. |▌▌  ▌▌▌ ▌   ▌▌▌▌  ▌▌▌▌▌▌   ▌ ▌  ▌▌   ▌|
           ░░░░░░░░ ascription track absent for SV/YV/AV — hatched, not empty
   maṇḍala order is NOT a timeline. Caption says so.
```

**Interactions.** Brush a region → the verses in it. Toggle certainty tier and watch ticks
appear/disappear. Overlay a second deity (max two) using two series colours from §7.

**Absence encoding.** Each strip is drawn to **full corpus length whether or not any verse in
it attests** — an empty Samavedic strip is visibly an empty *1,844-verse* strip, not a missing
row. The ascription track for SV/YV/AV is **hatched across its whole length**
(`LAYER_ABSENT`), categorically different from a mention track that is drawn and happens to be
sparse.

**Failure modes.** (a) Scaling all four strips to a common pixel width, making the Samaveda
look as long as the Rigveda. (b) Anti-aliasing: at 10,552 verses in ~900 px, one verse is
0.085 px — ticks need a minimum width and additive opacity, or dense regions saturate and
sparse ones vanish. (c) **Binning hides burstiness within a bin.** Voyant's Bubblelines bins
into 50 segments by default and therefore cannot distinguish 10 occurrences spread through a
segment from 10 in one line. Prefer exact ticks at RV scale; bin only if performance forces
it, and then say so. (d) **Do not summarise a distribution into a position.** TextArc placed
each word at the *centroid* of its occurrences, and a word heavy in maṇḍalas 1 and 10 lands in
the middle, indistinguishable from an evenly-spread word. Voyant's TextualArc inherited the
same flaw. The dispersion strip exists precisely to avoid it.

**Library.** None (canvas for the RV strip if tick count demands it).

---

### V7 — The Corpus Icicle · *"How is each Samhita shaped?"*

**Scholarly question.** *How unevenly is the corpus distributed across its own divisions?*
Also the primary **navigation** control.

**Data.** `GET /works/{id}/root`, then `GET /passages/{key}/children`. `POINT_READ` each.
**Servable today** for two levels; the third (verse) level is 20,210 leaves and loads on
demand only.

**Form.** A **horizontal icicle / partition**, not a sunburst. Icicle because the labels are
Sanskrit and must be legible horizontally; because width comparison along a common baseline is
a position-on-common-scale judgement rather than an angle judgement; and because four corpora
stack as four rows without competing for a shared centre.

```
 RIGVEDA   ├─M1────────────┤├M2──┤├M3─┤├M4┤├M5──┤├M6──┤├M7──┤├M8────┤├M9────┤├M10───────┤
 SAMAVEDA  ├─ARANYA─┤├─CHANDA──────────────┤├MAHANAMNYA┤├─UTTARA──────────┤  ← NAMES, not ordinals
 YAJURVEDA ├1┤├2┤├3┤├4┤├5┤ … 40 adhyayas — ONE level only; the missing hymn tier is
           drawn as an explicit "no level here" band, not as a truncated three-level tree
 ATHARVAVE.├─K1──┤├K2──┤├K3─┤ … 20 kandas
           (the Samavedic kanda division is NOT a level here: it does not nest)
```

**Absence encoding.** A `HierarchyLevel.passage_count` of `null` renders as a hatched segment
of *unknown* width with an explicit "not established" label — not as a zero-width gap.

**Failure modes.** (a) **A sunburst is the wrong choice**: with four roots at four different
levels the inner ring is incoherent, Sanskrit labels do not fit radially, and angle comparison
is measurably worse than length. (b) Rendering to leaf level by default — 20,210 leaves at
~1 px each is a texture, not a chart, and 20,210 DOM nodes. (c) Showing the Samavedic kanda as
a row: it cuts across prapathaka and ardha boundaries, and a partition layout would silently
misrepresent it. It is an alternate `Citation` system and belongs in a citation switcher.

**Library.** `d3-hierarchy`'s `partition()` — **4.67 kB gzip selective-import (measured)**,
pure computation, SSR-safe. Or ~40 lines of cumulative-sum arithmetic, since the tree is at
most three levels deep.

---

### V8 — The Limits Map · *"What can this product not answer?"*

**Scholarly question.** *What is outside this instrument's reach, and what would put it
inside?* Served so a client *"can discover the boundary instead of finding it by getting an
empty list back from a plausible question."*

**Data.** `GET /insights/capabilities` → `CapabilityLimit[]` with `verdict`
(`NOT_ANSWERABLE` / `PARTIAL_ONLY`), `why`, `what_this_is_not`, `measurements[]` (each with a
required `means` string), `safe_alternative`, `what_would_change_it`. **Servable today.**

**Form.** Deliberately **not a chart**. A structured card grid ranked by verdict, each card
carrying its measurement inline — the measurements are heterogeneous (one is a count of zero
community assignments, another a coverage share) and plotting them on a common axis would be
false precision. The only visual element is a small bar per `CapabilityMeasurement` where the
value is a count with a denominator, and a plain "0 — and this is the point" rule where it is
zero.

**Why it ranks 8th and not 15th.** Every other product in this space hides its limits in a
methodology page nobody opens. Making the boundary a first-class, navigable, *measured*
surface is the most distinctive thing VedAnvaya can ship, and it costs almost nothing. The
nearest prior art is the IPCC's calibrated-uncertainty vocabulary (§4.5) and Viral Texts'
practice of calling its output *"speculative bibliographies"* in the product label itself.

**Failure modes.** Rendering `NOT_ANSWERABLE` as a sub-grade of `PARTIAL_ONLY` on a shared
severity ramp. They are different kinds: one says the dimension is absent from the graph, the
other says a real but incomplete answer exists.

**Library.** None.

---

### V9 — The Provenance Ribbon · *"Why does the graph believe this?"*

**Scholarly question.** *On what evidence does this assertion rest — and was it read off the
Sanskrit or off a 19th-century English translation?* `EvidenceSurface.TRANSLATION` covers
2,725 relationships and 2,459 nodes, and *"a reader who cannot see that is reading Whitney and
Griffith as if they were the Samhita."*

**Data.** `GET /graph/relationships/{id}` → `RelationshipExplanation` (`why`, `trust_tier`,
`derivation`, `review_status`, `evidence_passages[]`) plus the edge's `EvidenceView`.
**Servable today**, `POINT_READ`.

**Form.** A four-band horizontal ribbon under the claim, read left to right as a provenance
chain. Each band is a labelled chip, not a colour-only swatch.

```
  «Sukta 1.1 is ascribed to Agni»
  ┌──────────────┬─────────────────────┬──────────────────┬───────────────────┐
  │ DERIVATION   │ SURFACE             │ PRECISION        │ REVIEW            │
  │ SOURCE_STATED│ SOURCE_METADATA     │ CONTAINER_       │ no review record  │
  │              │                     │ INHERITED ⚠      │ exists            │
  └──────────────┴─────────────────────┴──────────────────┴───────────────────┘
    tier TIER_A · confidence: PIPELINE_CONSTANT (0.9) — ranks nothing, shown as a stamp
    ⚠ this is a hymn label projected onto this verse; the source does not state it of this verse
    witnesses ▸ RV 1.1 (Anukramaṇī)
```

**Absence encoding.** `confidence` renders as a **stamp, not a bar**, whenever
`ConfidenceBasis` is `PIPELINE_CONSTANT`, with the words "ranks nothing" beside it; where the
basis is `ABSENT` the field is omitted, not shown as 0. `review_status` always renders the
plain-language string, and the top of the trust ramp is `MODEL_ADJUDICATED` — **no green
"verified" state, because no edge in this graph carries one.**

**Failure modes.** (a) A 0–1 confidence bar. (b) A tier ramp coloured red→amber→green, which
asserts a validated top. (c) Collapsing `EvidenceBasis` and `EvidenceSurface` into one
"provenance" chip — they are different axes, and the codebase records that conflating them
*"mapped every attribution edge in the corpus to `UNKNOWN`."*

**Library.** None.

---

### V10 — The Co-occurrence Arc · *"Which gods are invoked together?"*

**Scholarly question.** *Which deities are named together more often than chance, and is that
pattern Rigvedic or corpus-wide?*

**Data.** `GET /devatas/{id}/network` → `co_occurring[]` with `lift`, `passage_count`,
`rv_passage_count`, `non_rv_passage_count`, `per_veda_counts`, `quality_tier`, plus
`shared_rishi_deities[]` and `dimension_status[]`. **Servable today** — but **egocentric
only**: there is no all-pairs deity co-occurrence endpoint.

**Form.** A **one-sided arc diagram**, not a chord (§3.2). Subject deity pinned left;
co-deities on a vertical axis ordered by `lift`; bar length = `passage_count`; each row split
into RV and non-RV components, because *"the two halves of the mention layer were produced by
different instruments — manual annotation for the Rigveda, adjudicated surface matching
elsewhere."*

```
            lift   passages (▮ RV manual  ▯ non-RV adjudicated)
  INDRA ╮
        ├── Varuṇa    3.4   ▮▮▮▮▮▮▮▮▯▯
        ├── Agni      2.1   ▮▮▮▮▮▮▯▯▯▯▯▯
        ├── Soma      1.8   ▮▮▮▮▯▯▯
        ├── Vāyu      1.1   ▮▮▯
        ╰── Mitra     0.6   ▮▯            ← below 1.0: together LESS than baseline
     ┄┄┄┄┄┄┄┄ baseline lift = 1.0 ┄┄┄┄┄┄┄┄
     dimension_status: 1 label dropped (resolved to a non-deity) — see note
```

**Interactions.** Switch to the `shared_rishi_deities` dimension — a *different* relation, so
a separate view, never an overlay. Click a bar → example citations.

**Absence encoding.** `dimension_status[]` renders as a persistent footer: *"Every dimension
above whose empty value is NOT an assertion of absence."* Indra's frozen `profile_co_devatas`
property is `['Vasukra']` — a human patron — and the population contract drops it; the chart
must say a label was dropped, not silently show one fewer bar. A `null` lift renders with no
horizontal position and an explicit "lift not computed" tag.

**Failure modes.** (a) A chord diagram (§3.2). (b) Treating `type: "DEVATA"` as "is a god":
**30 of the 214 Anukramaṇī devata-slot entries are not deities** — 22 human patrons and seers,
7 labels naming a gift rather than a recipient, and one dog — and eight carry real traversable
degree. Read `is_deity`, not `type`. (c) Sorting by `passage_count` rather than `lift`
reproduces the frequency ranking and finds nothing.

**Library.** None; `d3-shape` (4.47 kB measured) only if the curves get fussy.

---

### V11 — The Explained Path Ladder · *"How are these two things connected?"*

**Data.** `GET /graph/path?from=&to=` → `PathView` with per-hop `explanation` and
**`hub_mediated: bool`**. **Servable today.**

**Form.** A vertical ladder, one rung per hop, each carrying its `explanation`. Not a
node-link fragment — the explanation *is* the content, and a graph rendering subordinates
prose to geometry.

```
  FROM  Concept: ṛta
   │  ① ─ MENTIONS ──────────────▶  RV 1.23.5
   │     "this verse's text contains an attested inflection of the headword;
   │      it is not a claim that the verse is about ṛta."
   │  ② ─ HAS_DEVATA_ASCRIPTION ─▶  Varuṇa
   │     "the Anukramaṇī ascribes the containing sukta to Varuṇa; this is a
   │      hymn label projected onto this verse (CONTAINER_INHERITED)."
  TO    Devata: Varuṇa
  ┌──────────────────────────────────────────────────────────────────┐
  │ ⚠ HUB-MEDIATED. This route passes through a node of degree 4,195. │
  │   A route of this kind is true and says nothing about the pair.   │
  └──────────────────────────────────────────────────────────────────┘
```

**Absence encoding.** When no hub-free route exists, the hub-mediated one is returned
**labelled with the offending node's degree**, *"rather than suppressed into an empty answer
that a reader would take for 'unconnected'."* Render that banner above the ladder, not as a
footnote.

**Failure mode.** Rendering a hub-mediated path identically to a hub-free one. Two Rigvedic
verses are nearly always connected within three hops through tristubh (4,195 edges) or Indra
(6,539); an unlabelled path is a machine for generating spurious findings.

**Library.** None.

---

### V12 — The Recitation Coverage Strip · *"Which verses can I actually hear?"*

**Data.** `GET /audio/stats` and `GET /works/{id}/audio` (`mapped_scope_count` **vs**
`playable_scope_count`). **Servable today.**

**Form.** Four stacked strips with **three** segments each, never two:

```
  RIGVEDA     ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▒▒░░   10,402 / 10,552
              └ playable ──────────────────────┘└mapped └ none
                                                 not served (11 Valakhilya hymns)
  ATHARVAVEDA ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░          4,680 / 5,839
  YAJURVEDA   ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░            1,752 / 1,975
  SAMAVEDA    ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░              0 / 1,844
              └ "No recitation of the Kauthuma ārcika is published anywhere.
                 This is an absence in the world, not a gap in our catalogue."
```

**Absence encoding.** The middle segment exists because *"the portal maps all 1,028 Rigvedic
suktas and serves 1,017 of them, having never published the eleven Valakhilya hymns. A surface
that rendered only `mapped_scope_count` would promise a recitation for eleven passages that
offer no player."* The Samavedic zero is a **measured zero with a stated cause**, carried
inline.

**Failure modes.** (a) A two-segment "covered / not covered" bar — it over-promises by 11
Rigvedic hymns. (b) Omitting the Samaveda row because it is empty. (c) Reporting
`total_records` as coverage without `by_availability`.

**Library.** None.

---

### A cross-cutting hazard: interface prominence becomes data

Liz Shayne's Gephi study of the Sefaria link graph found Genesis 1:1 to be the top-degree node
— and argued it is top-degree **partly because it is what the interface shows you first**
(https://lizshayne.wordpress.com/2014/06/17/sefaria_in_gephi/). Her conclusion about the whole
corpus is worth quoting in our own limits page: the graph is *"not exactly a reflection of over
2,000 years of Jewish literature as such, but a reflection of how far Sefaria has come in
crowdsourcing."*

Our graph is frozen and not crowdsourced, so the feedback loop is weaker — but it is not
absent. Whichever sukta the landing page shows, whichever deity the Invocation Landscape
defaults to, will be the one readers explore, cite and report defects in. **Vary the default,
or state it.**

---

## 3. What NOT to build, and why

### 3.1 Semantic constellations / UMAP / t-SNE scatter — **REJECT**

**It cannot be fed.** No embeddings exist. `insight_service.py:426`: *"No non-lexical
resemblance measure exists anywhere in this graph: no embedding, no vector index, no asserted
resemblance."* The `SEMANTIC_RESEMBLANCE` row of the cross-Veda matrix is `NOT_BUILT` for this
reason, and `/insights/capabilities` publishes it as a limit.

**It should not be built even if they existed.** A UMAP scatter presents *model-derived
proximity* with the visual authority of *measured position*. Inter-cluster distances are not
meaningful, cluster sizes are not meaningful, and the layout is hyperparameter-dependent and
non-deterministic across runs (Wattenberg, Viégas & Johnson, *"How to Use t-SNE Effectively"*,
Distill 2016, https://distill.pub/2016/misread-tsne/; Chari & Pachter, *"The specious art of
single-cell genomics"*, PLOS Comput Biol 2023,
https://doi.org/10.1371/journal.pcbi.1011288). In a product whose premise is that a model
guess must never wear the clothes of a measurement, a plot where *distance itself is the
model's opinion* is the most off-brand item on the candidate list.

A second, sharper objection applies to any layout: Jacomy et al.'s own ForceAtlas2 paper
(*PLOS ONE* 2014, https://pmc.ncbi.nlm.nih.gov/articles/PMC4051631/) states the algorithm *"is
not deterministic"*. **A scholarly figure that redraws differently on re-run cannot be cited.**
That alone disqualifies stochastic layouts from a citable research product.

If semantics are ever built, the honest surface is a **ranked, cited list with a stated
method** — not a map. Record as `VIZ_REJECT_01`.

### 3.2 Chord diagram of deity co-occurrence — **REJECT**

(a) **It cannot be fed**: chord needs a full symmetric N×N matrix; `/devatas/{id}/network` is
egocentric. (b) **Arc thickness cannot express `null`** — a ribbon is present or absent, and
"absent" is the state this product must never render ambiguously. (c) **A chord asserts a
closed system**: the ring implies the deities shown are the deities that exist, when the
population contract has filtered 30 non-deities out and `dimension_status` records further
drops.

Note that **Sefaria — the best peer for this data shape — deliberately did not use a chord
either.** Its Link Explorer is a *bipartite two-rail layout* with cubic Bézier diagonals
(`d3.svg.diagonal()`), older corpus on a top rail, newer below, so **direction is carried by
spatial convention and needs no arrowheads**. For "Rigveda ↔ Samaveda" that is a strictly
better default than a circle, and V2/V4 adopt the underlying principle (aggregate, then
drill).

### 3.3 Word cloud — **REJECT**

Area is the least accurate channel for magnitude; ranking is destroyed by word length;
rotation destroys comparability; and there is no way to distinguish "not searched for" from
"did not occur". Voyant's own documentation concedes that in Cirrus *"the colour of words and
their absolute position are not significant"* — **two of three visual channels carrying no
data**. Jacob Harris, *"Word clouds considered harmful"* (Nieman Lab, 2011,
https://www.niemanlab.org/2011/10/word-clouds-considered-harmful/) is the standard reference:
they are *"the mullets of the Internet"* and *"a lazy way to inject a graphic and superficial
analysis into a story."*

### 3.4 Whole-graph force-directed hairball — **REJECT**

108,779 nodes. The bounded Cytoscape neighbourhood already exists, already carries
`NeighbourhoodBounds`, and is the correct scope. Two citations to hand: Scott Weingart,
*"Demystifying Networks"* (JDH 1(1),
http://journalofdigitalhumanities.org/1-1/demystifying-networks-by-scott-weingart/) — *"networks
could conceivably be used on any project, [but] that doesn't necessarily mean they should be"*;
and Tiago Peixoto, *"Untangling the hairball using statistical inference"*
(https://skewed.de/lab/posts/hairball/) — networks are not low-dimensional objects, so
projecting one into 2D is *"a rather violent act"*, and the remedy is **to infer groups and
draw the groups**. Which is what V2 does.

### 3.5 Treemap of the corpus — **REJECT**

A treemap encodes quantity by area and **discards order**. The corpus is *ordered* — its most
important structural property — and the icicle preserves it at no cost.

### 3.6 Animated "growth of the corpus over time" — **REJECT**

No date property on any node. A temporal animation would have to invent a stratigraphy (Family
Books "early", Mandala 10 "late") — a contested scholarly position this graph does not hold and
must not assert through motion.

### 3.7 Three-stage Sankey: deity → ritual → concept — **REJECT**

The ritual layer is `PARTIAL` **by construction** and the registry holds **8 rituals**. A
three-stage flow diagram implies a complete pipeline from god to rite to idea. It would be the
most impressive-looking and least defensible thing in the product.

### 3.8 Geographic map of rivers, places, tribes — **REJECT**

8 rivers, 11 places, 5 tribes, **no coordinates anywhere in the graph**. Placing Sarasvatī on a
basemap asserts an identification among the most contested in Indology, which this graph does
not make. Cf. ORBIS (https://orbis.stanford.edu/), which *is* a graph and is deliberately never
drawn as a node-link diagram — but which has 678 georeferenced places and a defensible cost
metric. We have neither.

### 3.9 Radial egocentric sunburst for one mantra — **REJECT (redundant)**

`/graph/neighborhood/{id}` is already rendered by the Cytoscape explorer with a *Why* panel and
bounds disclosure. A radial restyle of the same payload is decoration.

### 3.10 UpSet plot — **REJECT, and record why**

The technique is correct and well-founded: Lex, Gehlenborg, Strobelt, Vuillemot & Pfister,
*"UpSet: Visualization of Intersecting Sets"*, IEEE InfoVis 2014,
https://doi.org/10.1109/TVCG.2014.2346248 · https://upset.app/ — **IEEE InfoVis 10-Year Test of
Time Award, 2024**. It beats Venn/Euler decisively past ~4 sets by re-encoding intersection
size from *region area* (a poor channel) to *aligned bar length* (the best one).

**But we have exactly four sets**, and the question "which formulas are shared between which
collections" is already answered more directly by V2 (all six pairs, typed) and by V4's
`span_census`, whose `vedas_reached` ∈ {1,2,3,4} **is** the UpSet degree axis, already
aggregated server-side. Building one would add a second visual grammar to restate four rows.

The implementation is separately disqualified. **`@upsetjs/react@1.11.0`** is (a) licensed
**AGPL-3.0 or commercial** — *"If you are using UpSet.js for a commercial project … you would
need to get a commercial license"*; (b) last released **2022-04-09**; and (c) **emits a
non-deterministic root class name across renders (measured: `root-upset-dhyjy35zh` then
`root-upset-126zvvk1f` for identical input)**, which is a guaranteed Next.js hydration
mismatch. An UpSet plot is a bar chart plus a dot matrix; at eight recensions, hand-roll it on
`d3-scale` for 0 additional kB.

### 3.11 Build this instead: the Truncation Gauge — **BUILD (40 px, on the existing canvas)**

Not a new chart. `NeighbourhoodBounds` carries `total_degree` and `truncated_types[]`, and the
docstring is blunt: *"a client that plots 50 edges without knowing that 3,516 were dropped
draws a false picture of a deity's prominence."* Render `returned_edges / total_degree` as a
filled arc plus the truncated predicate list. Cheapest integrity win in this document.

---

## 4. Encoding absence, zero, and uncertainty

### 4.1 The five states, and the mark for each

Colour is the **last** channel assigned, never the only one. Each state gets a *texture* and a
*glyph* that survive greyscale and all three dichromacies.

| State | Meaning | Mark | Fill | Glyph |
|---|---|---|---|---|
| **Measured, n > 0** | the figure is real | solid | series colour | — |
| **Measured zero** | counted, and it is zero | flat baseline rule at the axis | series colour, 1 px | `0` |
| **Insufficient evidence** | evidence exists, cannot support the claim | stipple (2 px dot grid) | `nodata-fill` | `?` |
| **Not built** | the layer does not exist here | 45° hatch, 3 px pitch | `nodata-fill` | `∅` |
| **Partial** | real answer over part of the scope | solid with a dashed cap edge | series colour | `◗` |
| **Inconsistent** | the graph contradicts itself | cross-hatch | `rubric` | `⚠` |

Two justifications for texture over colour:

- **Bertin's framework** (*Sémiologie graphique*, 1967; Berg trans. 1983) classes visual
  variables by perceptual level. **Only position and size are *quantitative*; value
  (lightness) is *ordered* but not quantitative; hue is *selective* and *associative* but
  **not ordered***. Texture/grain is selective. That is the formal statement of why hue cannot
  carry a degree and why absence — a categorical, non-ordered state — belongs on a selective
  channel that is not already committed to series identity.
- **A pale colour at the low end of a sequential ramp reads as "a little."** That is the exact
  false inference this product exists to prevent, and it is why no-data must sit *outside* every
  ramp (§4.2).

### 4.2 "No data" is a colour you reserve, per scheme — not a global grey

The strongest prior art is Paul Tol's colour-scheme technical note (SRON/EPS/TN/09-002,
https://sronpersonalpages.nl/~pault/), because he is the only palette author who **reserves a
specific hex for bad data in every scheme he publishes** — and, crucially, *the value differs
per scheme*:

| Tol scheme | Bad-data colour |
|---|---|
| muted, light | `#DDDDDD` — *"Pale grey is meant for bad data in maps."* |
| bright, vibrant | `#BBBBBB` |
| sunset, nightfall, banded | `#FFFFFF` — *"designed for situations where bad data have to be shown white"* |
| **BuRd, PRGn (diverging)** | **`#FFEE99`** |
| YlOrBr, incandescent | `#888888` |
| iridescent | `#999999` |
| discrete rainbow | `#777777` |
| smooth rainbow | `#666666` |

Read the mechanism: for a blue↔red diverging ramp a grey would read as a legitimate mid-scale
value, so the bad-data colour becomes a pale yellow that is nowhere in the ramp. Tol states the
design rule for the diverging case: the bad-data colour must be *"meant for bad data, without
drawing attention away from good data with a large deviation from zero."*

**The rule we adopt: `nodata-fill` must be outside the lightness path and the hue path of
whatever palette it sits beside — chosen per palette, not once.** ColorBrewer independently
converges on the same instinct: Set1, Set2, Dark2, Accent, Pastel1 and Pastel2 all terminate in
a neutral grey (`#999999`, `#B3B3B3`, `#666666`, `#CCCCCC`, `#F2F2F2`) — the de facto
"other / unclassified" slot.

A real collision risk to watch, flagged by Lisa Charlotte Muth at Datawrapper: grey is already
doing enormous work — *"axes, gridlines, colour key labels, axis ticks, axis labels, regions
without data in choropleth maps, the base map in symbol maps, and less important text."* If
grey is your gridline colour it cannot *also* be a semantically distinct no-data fill without a
second channel. Hence hatch.

### 4.3 Uncertainty: the empirical ranking, and a correction

The result to build on is **MacEachren, Roth, O'Brien, Li, Swingley & Gahegan, "Visual
Semiotics & Uncertainty Visualization: An Empirical Study"** (IEEE TVCG 18(12):2496–2505, 2012,
https://doi.org/10.1109/TVCG.2012.279), which ranked visual variables for intuitiveness as
uncertainty signifiers across two studies (n=72 for the ranking task):

| Tier | Visual variables |
|---|---|
| **Good** | **fuzziness, location, value (lightness)** |
| **Acceptable** | arrangement, size, transparency |
| **Unacceptable** | **saturation, hue, orientation, shape** |

**Two corrections to the folk wisdom, and they change our design.** *Location* ranks in the top
tier, not the bottom. And **saturation ranks in the bottom tier, alongside hue** — which means
the near-universal intervention "desaturate the uncertain thing" is empirically the *weakest*
intuitive signifier available. Therefore:

- **Do** use lightness (value) and fuzziness — a softened mark edge — for lower-trust tiers.
- **Do** use texture for the categorical absence states.
- **Do not** use hue to carry confidence; it is measurably poor and is fully committed to
  series identity.
- **Do not** rely on desaturation *as a signifier*. It may still be used mechanically (below),
  but it will not be *read* as uncertainty on its own.

### 4.4 Value-Suppressing Uncertainty Palettes — the right tool, for the right reason

**Correll, Moritz & Heer, "Value-Suppressing Uncertainty Palettes"**, CHI 2018,
https://doi.org/10.1145/3173574.3174216 · paper https://idl.uw.edu/papers/uncertainty-palettes ·
library and live demo **https://idl.uw.edu/vsup/** (`npm: vsup`; note the older
`uwdata.github.io/vsup` URL now redirects).

The construction is a **non-uniform budget of distinguishable outputs**. Instead of crossing an
N-step value scale with an M-step uncertainty scale into a uniform N×M bivariate grid, a VSUP
quantizes the plane with a *tree*: at low uncertainty the value axis subdivides into many bins;
as uncertainty rises, sibling bins merge, so progressively fewer distinct colours survive and
they converge toward a desaturated neutral. The legend is an arc — wide at the certain end,
narrowing to a point. **The reader physically cannot read a precise value off an uncertain
region, because the encoding no longer affords it.** Evaluation: *"compared to traditional
bivariate maps, VSUPs encourage people to more heavily weight uncertainty information in
decision-making tasks."*

Note how this reconciles with §4.3: a VSUP is **not** relying on saturation being intuitively
read as uncertainty. It is *removing discriminability*. Different mechanism, and it survives
the MacEachren finding.

**Where this applies here.** Wherever a graded trust tier sits alongside a magnitude — V3's
evidence grid, V10's lift — drive suppression from `TIER_A..TIER_D`. Its precondition is an
*ordered* uncertainty variable: `TIER_A..TIER_D` qualifies; **`KnowledgeStatus` does not**, since
its four values are not degrees of one thing (its own docstring says so).

Two further findings honoured:
- **Correll & Gleicher, "Error Bars Considered Harmful"** (InfoVis 2014,
  https://doi.org/10.1109/TVCG.2014.2346298) — error bars are ambiguous (their survey found
  ~48% unlabelled as to SD/SE/CI), asymmetrically read, and impose a binary in/out cliff on a
  continuous density. Where an interval must be shown, prefer a gradient or violin; **in this
  product, prefer naming the tier over drawing an interval we cannot calibrate.**
- **Sketchy rendering** (Wood, Isenberg, Isenberg, Dykes, Boukhelifa & Slingsby, InfoVis 2012,
  https://doi.org/10.1109/TVCG.2012.262) establishes sketchiness as a *quantifiable, orderable*
  visual variable. **Tempting and rejected**: it also shifts perceived provisionality of the
  whole graphic, and this product's register is a scholarly atlas. A sketchy stroke would read
  as "draft", not "uncertain". Recorded so it is not re-litigated.
- Worth citing in the design rationale: **Hullman, "Why Authors Don't Visualize Uncertainty"**
  (IEEE TVCG 2020, https://doi.org/10.1109/TVCG.2019.2934287) — surveying 90 authors,
  *"a clear contradiction arises between authors' acknowledgment of the value of depicting
  uncertainty and the norm of omitting direct depiction of uncertainty."* We are choosing not
  to be that norm.

### 4.5 Explicit null rows, and how to spell an absence

**Eurostat's convention is the best-specified prior art and maps directly onto our needs.** It
separates the *value* from the *reason*:

| Code | Meaning |
|---|---|
| `0` | a real zero |
| **`0n`** | **less than half the final digit shown, and different from a real zero** |
| `:` | not available — *replaces* the value; the cell is neither empty nor zero |
| `:c` | not available **because confidential** |
| `m` | missing — the value **cannot exist** |
| `e` / `i` / `p` / `u` | estimated / imputed / provisional / low reliability (`Obs_status`, restructured 2025-01-27) |

`0n` is the gem: a dedicated encoding for "positive but below display resolution", which is the
state our lexical-match minima are constantly in. And the `:c` composite — *absent* **plus**
*reason for absence* — is exactly the structure of our `CrossVedaCellStatus`.

**IPCC AR6** supplies the two-axis vocabulary for provenance (https://www.ipcc.ch/report/ar6/syr/):
*confidence* is qualitative (very low → very high, derived from a published evidence × agreement
matrix) and is **deliberately not assigned probabilistically**; *likelihood* is the separate,
quantitative scale (*virtually certain* 99–100%, *very likely* 90–100%, *likely* 66–100%, and so
on). Calibrated terms are set in *italics* so a defined term is visibly not prose. The lesson:
**keep "how much do we trust the evidence base" and "how confident are we in this number" on
different axes and refuse to collapse them** — which is precisely what `EvidenceBasis`,
`EvidenceSurface` and `ConfidenceBasis` already do, and what V9 must render.

Two more patterns worth stealing:
- **Our World in Data** attaches the source line to the **chart artefact itself**, not to
  surrounding prose, so it survives screenshotting and embedding.
- **Viral Texts** names its clusters by extent — *"38 reprints from 1870-09-24 to
  1871-02-03"* — rather than inventing a title, and calls its output *"speculative
  bibliographies"* in the product label. Our formula families face the same
  identity problem and should be named the same way.

### 4.6 Zero on a log scale, and the false-zero test

`log(0)` is undefined, so a log axis **cannot represent zero** and most libraries silently
*drop* the point — the worst possible failure here, because a dropped zero and a dropped null
render identically as nothing. If a log axis is ever needed, use **symlog** (linear within
±`linthresh`, log outside; note the visible kink and that `linthresh` is an arbitrary parameter
that changes the story) or **asinh** (`sign(x)·log(1+|x|)`, continuous, parameterless).
For area-encoded marks use `sqrt`, which handles zero natively.

**The deeper problem is upstream of any axis.** Three states collapse into one visual outcome:

1. **Structural zero** — the category exists, count is genuinely 0.
2. **Missing** — the category exists, we do not know the count.
3. **Not in the result set** — the category never appeared, because the query projected only
   positive rows.

State 3 is dangerous because it is invisible *at the data layer*: there is no row to render.
**The only robust fix is to left-join against the full domain before plotting** — enumerate the
category universe independently, join counts in, and materialise explicit rows for absences.
This is why `/insights/cross-veda` enumerates 48 cells from constants rather than from the data,
and why `MatrixShape.cells_expected` exists. McNutt, Kindlmann & Correll, *"Surfacing
Visualization Mirages"* (CHI 2020, https://doi.org/10.1145/3313831.3376420, Best Paper Honorable
Mention) locate this failure at the **data-transformation** stage: *"mirages can be generated at
every stage of the visual analytics process."* No amount of colour design fixes it.

**Therefore, a mandatory per-component test.** Before any chart ships, one question must be
answered in its unit test:

> *If the underlying query returned only positive rows, would this chart show a zero?*

If yes, the chart is wrong. Concretely: feed the component a payload where one Veda's value is
`null`, and assert that **no bar, tick, arc or cell is drawn at the zero position**, and that
the absence mark and its `note` appear in the accessible name. This is the visual layer's half
of the contract `Paginated._empty_must_explain_itself` enforces on the API side.

---

## 5. Blockers — what the API must gain first

### 5.1 `VIZ_BLOCKER_01` — dispersion data cannot be fetched (blocks V6)

`MAX_PAGE_SIZE = 200` caps `/devatas/{id}/passages`. An Invocation Landscape for a major deity
needs every attesting citation. Proposed: a new `AGGREGATE`-class endpoint

```
GET /devatas/{id}/dispersion?basis=mention|ascription&certainty=…
→ { by_veda: { RV: { positions: [int], denominator: 10552, status, note }, … },
    coverage: CoverageView, caveats: [...] }
```

returning **integer positions only** (no passage payloads), which keeps the response small and
removes the 18 round-trips. It must carry `CoverageView` so an empty `positions` array for the
Samaveda is distinguishable from an absent layer.

### 5.2 `VIZ_BLOCKER_02` — no per-book aggregate (blocks deity × mandala)

A deity × mandala heatmap is a genuine scholarly ask — the Family Books hypothesis lives there
— and cannot be served. Needed: a per-container count endpoint at the level named by
`HierarchyLevel`. **Until it exists, do not build one from client-side aggregation of paged
rows: the page cap would silently truncate it, and a truncated heatmap is indistinguishable
from a sparse one.**

### 5.3 `VIZ_BLOCKER_03` — no deity × metre aggregate

`DevataProfile.top_chandas` is a `list[str]` with no counts. Low priority: the metre layer
reaches only RV and AV, so the matrix would be two-thirds hatched — honest, but thin.

### 5.4 Non-blocker, and the largest free win available

Every insight response carries `cost_class`, and **the graph is frozen**. Therefore
`AGGREGATE` and `CENSUS` responses can be baked at build time. **V1–V4, V8 and V12 should be
statically generated as React Server Components and ship zero fetch latency and zero client
JavaScript.** This is the single largest performance lever in the document and it costs
nothing.

---

## 6. Library verdict

### 6.1 The governing observation

Of the twelve visualizations above, **nine need no charting library at all.** They are matrices,
strips, ladders and ribbons — layouts CSS Grid and hand-written SVG do better than any library,
because each needs a custom mark vocabulary (hatch, stipple, ghost figure, status glyph) that no
library exposes. The three that need *computation* need **layout maths only**.

That points at one conclusion: **take D3's pure-computation submodules, render with React inside
Server Components, and adopt no chart component library.**

### 6.2 Measured sizes

All figures **(measured)** locally with esbuild (`bundle, minify, format=esm, target=es2022,
react/react-dom external, NODE_ENV=production`) then gzip -9. Bundlephobia proved unreliable
during this research — it reported `plotly.js@4.1.0` at 10 kB gzip against a real 1,319 kB, and
reported `@nivo/core` gzip *larger* than minified.

**Selective import matters enormously.** `d3-scale-chromatic` is **3.28 kB** for two schemes and
**11.34 kB** for `import * as` — a 3.5× penalty. Same for `d3-scale` (9.11 vs 16.87).

| D3 submodule | selective | `import * as` | pure compute? |
|---|---|---|---|
| `d3-array` | **2.55** | 6.00 | yes |
| `d3-chord` | **2.19** | 2.32 | yes |
| `d3-hierarchy` | **4.67** | 5.88 | yes |
| `d3-sankey` | **2.82** | 3.00 | yes |
| `d3-scale` | **9.11** | 16.87 | yes |
| `d3-shape` | **4.47** | 8.64 | yes (returns path strings) |
| `d3-interpolate` | **4.32** | 7.16 | yes |
| `d3-scale-chromatic` | **3.28** | 11.34 | yes |
| `d3-selection` | 3.81 | — | **no — DOM** |
| `d3` meta-package | — | **92.0** | mixed |

### 6.3 Verdict table

| Library | gzip (measured) | SSR | React 19 | Best for | Verdict |
|---|---|---|---|---|---|
| **d3 modular** (scale/shape/array/hierarchy/sankey/chord) | **19.48** for all six | ✅ **RSC-native, 0 kB shipped** | n/a | every chart here; full token control | **ADOPT** |
| `d3` meta-package | 92.0 | ✅ | n/a | nothing | **REJECT** |
| `d3-selection` / `d3-transition` | 3.81 / ~7 | ❌ DOM | fights React | imperative DOM | **REJECT** |
| **visx** `group` / `heatmap` / `network` | **0.82 / 1.41 / 1.25** | ✅ RSC-safe | ✅ **v4.0.0, 2026-06-11, peer `^18\|\|^19`** | ~1 kB React SVG wrappers, **zero d3 deps** | **ADOPT (narrow)** |
| visx `scale` / `axis` | 12.52 / 17.19 | ✅ | ✅ | — | **USE NARROWLY** — worse value than raw `d3-scale` |
| visx `chord` / `hierarchy` | 2.80 / 6.08 | ✅ | ✅ | — | **AVOID** — still depend on **d3-chord v1 / d3-hierarchy v1**, duplicating your v3 install |
| **Observable Plot** | **134.19** | ⚠ needs JSDOM **or a vendored, unexported `Document`** | works (not a React lib) | exploration | **USE NARROWLY (dev only)** |
| **ECharts** tree-shaken + SSR | **172.2** floor; **client runtime 0.76** | ✅ **`renderToSVGString()`, no DOM** | ✅ | sankey, parallel coords, themeRiver, big canvas | **USE NARROWLY** — reserve as an escape hatch |
| ECharts full, client | 382.9 | ✅ | ✅ | — | **REJECT** |
| **Nivo** | **72.0** first chart, **171.0** for nine | ⚠ SSR yes, **RSC no** (`createContext` in core) | ✅ peer `^19` | fast dashboards | **REJECT** |
| **Vega-Lite + Vega** | **271.7** (compile) / 187.3 (vega) | ✅ headless → SVG, no DOM | ✅ | declarative specs, faceting — **build-time only** | **USE NARROWLY** |
| `react-vega` in the client | **297.2** | — | ✅ | — | **REJECT** |
| **deck.gl** (`react` + `layers`) | **222.0** | ❌ WebGL | ⚠ open bug with React 19.2 `<Activity>` ([#9983](https://github.com/visgl/deck.gl/issues/9983)) | >500k points, geospatial | **REJECT** |
| **Recharts v3** | 106.8–162.1 | ❌ **BROKEN** | ✅ | — | **REJECT** — see below |
| **Chart.js** | 49.1 / 70.2 | ❌ canvas | ✅ | simple canvas charts | **REJECT** — canvas kills text selection + a11y |
| **uPlot** | 23.2 | ❌ needs DOM | n/a | dense time series | **REJECT** — no time axis exists |
| **Plotly.js** | **1,318.7** full / 394.4 basic | partial | ✅ | scientific/3D | **REJECT** |
| **regl-scatterplot** | **76.5** | ❌ WebGL | n/a | million-point scatter | **USE NARROWLY** (>20k points only) |
| **deepscatter** | — | ❌ | n/a | — | **REJECT** — **CC BY-NC-SA 4.0, non-commercial**; last release 2024-03 |
| **Cosmograph** | 163.8 | ❌ WebGL | ❌ **peers cap at React 18** | — | **REJECT** — **CC-BY-NC-4.0, non-commercial** |
| **graphology** | **12.8** | ✅ Node-safe | n/a | graph metrics on the server | **ADOPT IF NEEDED** |
| **sigma.js** | +25.1 | ❌ **throws on `import`** in Node (`WebGL2RenderingContext is not defined`) | n/a | large interactive graph | **USE NARROWLY** (`ssr:false` island) |
| **@dagrejs/dagre** | **16.83** | ✅ Node-safe | n/a | layered DAG layout | **ADOPT IF NEEDED** |
| **elkjs** | **440.70** | ✅ Node-safe | n/a | high-quality DAG layout | **USE NARROWLY** — build-time only; **EPL-2.0/GPL-3.0 needs legal review** |
| **@viz-js/viz** | **488.58** | ✅ Node-safe | n/a | Graphviz DOT | **USE NARROWLY** — build-time only |
| **UpSet.js** | 19.09 | ⚠ renders, **non-deterministic** | ⚠ peer `>=17` | — | **REJECT** — AGPL/commercial, stale, hydration mismatch (§3.10) |
| **`cytoscape`** (incumbent) | ~120 | ❌ | in use | bounded node-link | **KEEP, DO NOT EXTEND** |

### 6.4 Three findings that contradict common advice

1. **Recharts v3 does not server-render at all. (measured)** `renderToStaticMarkup` of a
   `LineChart` with axes and a line produces exactly **127 bytes** — a bare
   `<div class="recharts-wrapper">` with no `<svg>`, no `<path>`. `BarChart` is identical, with
   no `<rect>`. Upstream [#5997](https://github.com/recharts/recharts/issues/5997) is **still
   open** (filed 2025-06-24, labelled `server-side-rendering`), and
   [#6139](https://github.com/recharts/recharts/issues/6139) was closed as a duplicate noting
   that v2.15.4 emitted ~5,186 characters of SVG where v3 emits ~127, with the advice that
   *"SSR users should remain on Recharts 2.15.4."* The widespread "Recharts is SVG so it SSRs
   fine" claim is false for v3.
2. **Observable Plot's documented React pattern does not work as written.** The official guide
   uses `Plot.plot({...}).toHyperScript()`, but `toHyperScript` **does not exist on a JSDOM
   element (measured)** — it exists only on elements created by Observable's own minimal virtual
   `Document`, **which the package does not export**. The docs say *"For brevity, the virtual
   `Document` implementation is not shown."* You must vendor an undocumented class. Observable's
   own caveat: *"Server-side rendering is only practical for simple plots of small data."*
3. **visx v4 still ships d3 v1 for two packages** despite release notes claiming a d3 upgrade:
   `@visx/chord` depends on `d3-chord@^1.0.4` and `@visx/hierarchy` on `d3-hierarchy@^1.1.4`,
   each installing a 2018-era copy beside your v3. Separately, `@visx/text`'s `getStringWidth`
   returns `null` when `typeof document === 'undefined'`, so wrapped axis labels lay out
   differently on server and client — a hydration-mismatch risk.

Two more worth knowing: **`d3-sankey@0.12.3` was last published 2019-09-02** and its deps
(`d3-array: "1 - 2"`, `d3-shape: "^1.2.0"`) put a second, ancient `d3-array@2.12.1` in the tree.
Bundle impact after tree-shaking is negligible; lockfile hygiene impact is not. And **ECharts is
the only library here that ships a genuine SSR story end-to-end** — `renderToSVGString()` in
bare Node, plus a **764-byte gzipped** client runtime that restores hover, legend toggling and
entry animation against server-rendered SVG without shipping ECharts.

### 6.5 Which libraries fight a design-token palette

Measured by rendering with no colour props and extracting hex values:

| Library | Bakes in | Severity |
|---|---|---|
| **Observable Plot** | `#4269d0 #efb118 #ff725c` **and injects a `<style>` element** with generated class names | **worst** — fights colour *and* CSS |
| **ECharts** | `#5070dd #b6d634 #505372`, axis greys `#dbdee4 #54555a` | high — needs `registerTheme` |
| **UpSet.js** | `#000000 #cccccc #ffa500 #d3d3d3` | high |
| **Nivo** | `colors:{scheme:"nivo"}`, `borderColor:"white"`, derived `["darker",0.8]` modifiers | medium — the derived modifiers compute *off* your tokens rather than *from* them |
| `d3-scale-chromatic` | opt-in only | **none** |
| **visx** | emits nothing | **none** |
| **raw d3 + JSX** | emits nothing | **none** |

The last row matters more than any size figure: with hand-rolled SVG you write
`fill="var(--viz-1)"` and **dark mode is free**. Every library above computes colours in
JavaScript, so switching theme means re-rendering the chart.

### 6.6 The minimum viable stack

```js
import {hierarchy, partition}                        from "d3-hierarchy";  // icicle
import {sankey, sankeyLinkHorizontal, sankeyJustify}  from "d3-sankey";     // alluvial
import {chord, chordDirected, ribbon}                 from "d3-chord";      // (if ever needed)
import {arc, line, linkHorizontal, curveMonotoneX}    from "d3-shape";      // arcs, curves
import {scaleLinear, scaleBand, scalePoint,
        scaleSequential, scaleOrdinal, scaleLog}      from "d3-scale";
import {extent, max, rollup, group, bin, ascending,
        quantile, sum}                                from "d3-array";
```

> **19.48 kB gzip / 17.26 kB brotli (measured)** — and **inside a React Server Component that
> is 0 kB shipped to the browser.**

Heatmap/matrix, dispersion strip, arc diagram and an UpSet plot need **no layout library at
all** — they are `scaleBand`/`scaleLinear`/`scalePoint` plus `<rect>`, `<circle>`, `<path>`.

If a chart must be client-interactive (tooltips, brushing, hit-testing), ship only the scales:

```js
import {scaleLinear, scaleBand, scalePoint} from "d3-scale";
import {bisector, extent}                   from "d3-array";
```
> **8.96 kB gzip (measured).** Recompute scales client-side from the same data; never ship a
> layout engine.

**Total realistic budget: ~20 kB server-side (0 kB shipped) + ~9 kB client where interactive.**
Compare Nivo 171, ECharts tree-shaken 172–220, Plot 134, react-vega 297.

Add only if forced: `regl-scatterplot` (+76.5, `ssr:false`) above ~20k points;
`graphology` (12.8, Node-safe) + `sigma` (+25.1, `ssr:false` island) for a large interactive
graph. **Skip `d3-scale-chromatic` entirely** — it would cost 3.28 kB to fight your own tokens;
define ramps as CSS custom properties instead.

---

## 7. The colour system

All figures below are **computed (measured)**, not asserted, by a dependency-free script
implementing WCAG relative luminance, the Machado/Oliveira/Fernandes (2009) CVD matrices at
severity 1.0, and OKLab/OKLCH per Ottosson (https://bottosson.github.io/posts/oklab/) with
chroma reduction for sRGB gamut mapping. See §7.8.

### 7.1 The two grounds, and what the brand accents do on them

| Colour | Hex | OKLab L | vs ivory `#F4F0E7` | vs carbon `#171815` |
|---|---|---|---|---|
| ivory (light ground) | `#F4F0E7` | 0.956 | — | **15.68 : 1** |
| carbon (dark ground) | `#171815` | 0.207 | 15.68 : 1 | — |
| rubric-red (brand) | `#B64A2E` | 0.548 | 4.61 : 1 ✅ text | 3.40 : 1 ⚠ non-text only |
| aged-gold (brand) | `#B49A62` | 0.697 | **2.39 : 1 ❌ fails 3:1** | 6.57 : 1 ✅ |
| indigo-ink (brand) | `#26364A` | 0.328 | 10.80 : 1 ✅ | **1.45 : 1 ❌ invisible** |

**Finding 1: none of the three brand accents is usable on both grounds as given.** Aged-gold
fails WCAG 2.2 SC 1.4.11's 3:1 non-text minimum on ivory; indigo-ink is effectively invisible on
carbon. This is not a defect in the brand — they are *UI* accents (links, rules, focus rings,
selected state) and they do that job well. It demonstrates that **the data palette must be a
separate system**, which is what both IBM Carbon and Adobe Spectrum do.

### 7.2 Carbon vs Spectrum — and the measurement that adjudicates between them

There are two published, **contradictory** positions from two major design systems:

- **IBM Carbon ships two palettes, mapped slot-for-slot.** Light theme takes the *dark* end of
  each hue ramp (Purple 70 `#6929c4`, Cyan 50 `#1192e8`, Teal 70 `#005d5d`…); dark theme takes
  the *light* end of the same hues (Purple 60 `#8a3ffc`, Cyan 40 `#33b1ff`, Teal 60 `#007d79`…).
  Hue is preserved; the tone step flips. Only `Red 50 #fa4d56` is shared across both.
  (https://carbondesignsystem.com/data-visualization/color-palettes/)
- **Adobe Spectrum ships ONE palette and refuses to change it.** Its 16 categorical colours are
  aliases onto a **`static`** scale, defined in a single CSS rule whose selector covers all four
  themes — byte-identical in light and dark — so **series identity never changes when the user
  flips the theme**. (https://spectrum.adobe.com/page/color-for-data-visualization/)

**Our measurement decides it.** Mapping neutral OKLab lightness to contrast on both grounds:

| OKLab L | vs ivory | vs carbon |
|---|---|---|
| 0.40 | 8.04 | 1.95 |
| 0.52 | 4.83 | 3.25 |
| **0.56** | **4.11** | **3.81** |
| **0.60** | **3.47** | **4.51** |
| 0.64 | 2.96 | 5.30 |
| 0.72 | 2.19 | 7.15 |

- ≥ 3:1 on ivory requires **L ≤ ~0.62**.
- ≥ 3:1 on carbon requires **L ≥ ~0.545**.
- The overlap is **L ∈ [0.545, 0.62]** — a band **0.075 wide**.

**Finding 2: at 3:1 on both grounds, the shared band admits essentially one lightness.** A
five-series static palette confined to it would have to carry *all* its separation in hue, which
§7.3 shows is the worst available choice. **Spectrum's static approach is therefore not
available to us at this contrast floor; Carbon's dual-palette approach is forced by the
arithmetic, not chosen by taste.** We keep Spectrum's *intent* — series identity — by holding
hue and chroma constant across themes and varying only lightness.

Tol independently corroborates the difficulty: *"The criterion cannot be met using more than one
print-friendly websmart colour plus white and black… The largest minimum contrast ratio in a set
of two is 2.8 and in a set with three such colours 2.1."* Note also that Tol's own *dark* scheme
guarantees 4.5:1 **against white, not black** — every scheme in his note is designed for paper.

An ivory ground makes this harder, not easier, and there is precedent: the Financial Times'
pink ground *"reduces the limits of lightness our colors can have: They always need to be darker
than this already darker-than-white background"* (Datawrapper,
https://www.datawrapper.de/blog/colors-for-data-vis-style-guides).

### 7.3 Why the palette is a lightness ladder, not a hue wheel

Measured over 60,000+ candidate palettes, scoring **minimum pairwise OKLab distance across
normal vision and all three dichromacies simultaneously**:

| Construction | min ΔE_OKLab | verdict |
|---|---|---|
| 6 hues at **constant** lightness (L = 0.52) | **0.017** | catastrophic |
| Okabe-Ito, 8 colours as published | 0.082 (tritan) | weak — and 5 of 8 fail 3:1 on ivory |
| Paul Tol *Muted*, 9 colours | **0.055** (deutan, rose/teal) | fails |
| 6 brand hues, hand-tuned ladder | 0.017–0.037 | fails (indigo/violet, rubric/green) |
| **5 hues, optimised lightness ladder** | **0.101 – 0.145** | **passes** |

**Finding 3: under a simultaneous protan + deutan + tritan constraint, lightness is the only
reliable categorical channel.** Every high-scoring palette the search found was a lightness
ladder over few hues; every equal-lightness palette collapsed. This restates Okabe-Ito's own
design logic — its published guidance is to *"use warm and cool colors alternatively [and] when
using two warm colors or two cool colors, put distinct differences in brightness or
saturation"* — with numbers.

**Finding 4: five is the cap.** Every attempt at six lost ≥25% of worst-case separation. This
agrees with the published guidance: **Adobe Spectrum** says *"Use up to 6 categorical colors —
categorical colors become more difficult to comprehend starting at 6 colors, and extremely
difficult to understand at 12,"* and recommends *"alternative visual encoding, such as
position"* beyond that; the **UK Government Analysis Function** is stricter still — *"Limit the
number of different colours you use; ideally an absolute maximum of four."* Beyond five series,
a second channel (shape, texture, direct labelling) is mandatory, not optional.

Note on ancestry: Okabe-Ito and Tol are both excellent and both **white-background** designs.
Okabe-Ito's yellow `#F0E442` scores **1.16:1 on ivory (measured)** — invisible — and its black
`#000000` scores **1.18:1 on carbon**, so the palette loses a member on a dark ground and its
internal luminance balance inverts between themes. Cite them as ancestry; do not ship them
unmodified.

### 7.4 The categorical series — LOCKED

Five series. **Hue and chroma are shared between themes** so the two palettes are one system;
**lightness is tuned per ground**. Named for the register of the product, not for their hues, so
a series can be re-hued without renaming.

| Series | Hue° | **Light (on ivory)** | contrast | **Dark (on carbon)** | contrast |
|---|---|---|---|---|---|
| `--viz-1` rubric | 33 | **`#6A1000`** | 10.95 : 1 | **`#D7644D`** | 4.94 : 1 |
| `--viz-2` gold | 80 | **`#896101`** | 4.89 : 1 | **`#F0B135`** | 9.38 : 1 |
| `--viz-3` indigo | 252 | **`#002E59`** | 12.03 : 1 | **`#B0D5FF`** | 11.72 : 1 |
| `--viz-4` verdigris | 192 | **`#005957`** | 7.19 : 1 | **`#2D918E`** | 4.71 : 1 |
| `--viz-5` violet | 300 | **`#9372C8`** | 3.37 : 1 | **`#B191EA`** | 6.88 : 1 |

Every swatch clears WCAG 2.2 SC 1.4.11 (3:1, non-text) on its own ground; four of five clear
4.5:1 in each theme.

**Colour-blindness separation — min pairwise ΔE_OKLab over all pairs (measured):**

| | normal | protanopia | deuteranopia | tritanopia |
|---|---|---|---|---|
| Light | 0.145 | 0.132 | **0.112** | 0.127 |
| Dark | 0.171 | **0.101** | 0.127 | 0.134 |

Worst pairs: indigo/verdigris (light, deutan) and rubric/verdigris (dark, protan); both clear
the 0.10 working threshold. Hues are brand-adjacent by construction — `--viz-1` at hue 33
against rubric-red's 35.6, `--viz-2` at 80 against aged-gold's 85.5, `--viz-3` at 252 against
indigo-ink's 254.4. The palette reads as the brand desaturated into a manuscript register.

**Fixed sub-palettes** for the common small cases, taken in order:
- 2 series: `--viz-3`, `--viz-1`
- 3 series: `--viz-3`, `--viz-1`, `--viz-2`
- **Focus pair** (one series matters, the rest is context — the pattern the UK Analysis Function
  publishes as `#12436D` + `#BFBFBF`): `--viz-3` + `--viz-ghost`.

### 7.5 Neutrals and the absence tokens

| Token | Light | Dark | Use |
|---|---|---|---|
| `--viz-ground` | `#F4F0E7` | `#171815` | plot background |
| `--viz-grid` | `#DDD8CB` | `#2E2F2B` | gridlines, 1 px |
| `--viz-axis` | `#4A463D` (8.26:1) | `#B9B7AD` (8.86:1) | axis lines, tick labels |
| `--viz-ghost` | `#B6B0A2` | `#54554E` | `related_edges_on_pair`, truncated remainder, focus-pair context |
| **`--viz-nodata-fill`** | `#DAD5C8` | `#2A2B27` | ground for hatch/stipple — **outside every ramp** |
| **`--viz-nodata-ink`** | `#7A7466` (4.09:1) | `#8E8C82` (5.28:1) | hatch strokes, `∅` and `?` glyphs |

`--viz-nodata-fill` is deliberately near `--viz-grid`: it must read as *substrate*, not as a
value. Its legibility comes from the hatch geometry and the glyph, not from a colour
distinction — which is precisely why it can never be mistaken for a low value on a ramp.
It is the warm-ground analogue of Tol's `#DDDDDD`.

### 7.6 Sequential and status ramps

**Sequential** (magnitude, e.g. share-of-mantras): a single-hue OKLCH ramp per series at fixed
hue and chroma, stepping lightness only — five stops — and the ramp **never includes**
`--viz-nodata-fill`. Where a perceptually-uniform multi-hue ramp is genuinely needed, use
**cividis** (Nuñez, Anderton & Renslow, PLOS ONE 13(7):e0199239, 2018,
https://doi.org/10.1371/journal.pone.0199239) rather than viridis: cividis was built by
simulating viridis under complete deuteranopia and re-optimising so hue change is perceptually
uniform *in CVD colourspace*, giving CVD and non-CVD viewers nearly identical readings.

**Never use viridis — or any ramp — for categorical data.** Viridis is a continuous,
monotonic-luminance ramp, so sampling N colours from it produces a set that is *ordered*
(readers infer rank where none exists) and *unequally separated* (neighbours differ mainly in
lightness and become unnameable past ~5). Spectrum states both directions of the rule: *"Using
[categorical colors] for sequences… makes it more difficult for users to understand,"* and
conversely *"Using [sequential] colors for dimensions can undermine the numeric association."*
And never use a rainbow: Borland & Taylor, *"Rainbow Color Map (Still) Considered Harmful"*
(IEEE CG&A 27(2):14–17, 2007) — it *confuses* (no perceptual ordering), *obscures*
(non-monotonic luminance flattens detail in the yellow and cyan plateaus), and *actively
misleads* (band boundaries read as data discontinuities that do not exist). Kenneth Moreland's
practical successor guidance is at https://www.kennethmoreland.com/color-advice/.

**Status — and the measurement that settles it.** Encoding the four `KnowledgeStatus` values by
colour was tested and **fails (measured)**:

| pair | normal | protan | deutan | tritan |
|---|---|---|---|---|
| `NOT_BUILT` vs `UNKNOWN` (light) | **0.033** | 0.021 | 0.030 | 0.038 |
| `NOT_BUILT` vs `UNKNOWN` (dark) | **0.020** | 0.008 | 0.014 | 0.025 |

Both are neutral greys by necessity — neither is a *value*, so neither may take a series hue —
and they are therefore indistinguishable by colour even for normal vision, 3–15× below the
working threshold.

**Finding 5: `KnowledgeStatus` must be encoded by texture and glyph (§4.1), with colour only
reinforcing. The distinction the entire product is built on is the one distinction colour cannot
carry.**

### 7.7 Contrast standards applied

- **WCAG 2.2 SC 1.4.3 (AA)**: 4.5:1 normal text, 3:1 large text.
- **WCAG 2.2 SC 1.4.11 Non-text Contrast (AA)**: **3:1** against adjacent colours for UI
  components *and* "graphical objects"; the Understanding document names *"lines in line graphs
  and slices in pie charts"* explicitly. **The exemption for "essential" presentation names
  heatmaps** — so a continuous sequential ramp may fall outside it, but a categorical series
  palette may not. Every figure in §7.4 is measured against this.
- **APCA** (Somers, https://apcacontrast.com), the WCAG 3 draft method, is worth adopting as a
  second check specifically because it is **polarity-aware**: it returns a signed Lc (positive =
  dark-on-light, negative = light-on-dark), where WCAG 2.x's ratio is symmetric and therefore
  systematically overrates light-on-dark. That is exactly the failure mode of a palette that
  passes on ivory and looks washed out on carbon. Bronze thresholds: Lc 90 preferred body text,
  Lc 75 minimum body text, Lc 60 large/secondary, **Lc 45 ≈ the non-text/UI floor**, Lc 15 the
  point of invisibility. *(APCA↔WCAG ratio equivalences are approximate and contested — do not
  publish a conversion table.)*

### 7.8 Reproducing and re-checking these numbers

The checker is ~90 lines of dependency-free Python: sRGB → linear → WCAG relative luminance;
Machado et al. (2009) CVD matrices at severity 1.0; OKLab forward/inverse with chroma reduction
for gamut mapping; minimum pairwise ΔE across normal + three dichromacies. **It should be
committed beside the tokens so a palette change re-runs the assertion rather than re-arguing
it** — the discipline the API already applies in `tests/api/test_evidence_vocabulary.py`.

Second opinions: **Viz Palette** (Elijah Meeks & Susie Lu,
https://projects.susielu.com/viz-palette) is the best tool for this specific job, because it
flags both *perceptually* similar colours **and** colours whose **names** are too similar;
**Chrome DevTools → Rendering → Emulate vision deficiencies** (backed by the same Machado 2009
model, scriptable in CI via Puppeteer `page.emulateVisionDeficiency()`); **Color Oracle**;
**Sim Daltonism**. For CI thresholds, the **WebAIM contrast checker has a JSON API** — append
`&api` to a permalink. Avoid Coblis's default simulation: it uses the HCIRN function, which
DaltonLens's review (https://daltonlens.org/opensource-cvd-simulation/) shows to be inaccurate
relative to Viénot 1999 / Brettel 1997 / Machado 2009.

If the palette is ever regenerated rather than hand-tuned, the objective to optimise is
**Colorgorical**'s (Gramazio, Laidlaw & Schloss, IEEE TVCG 23(1):521–530, 2017,
http://vrl.cs.brown.edu/color): perceptual distance (CIEDE2000) **plus name difference** — two
colours can be ΔE-distant and still both be "blue", which is what breaks legends — plus name
uniqueness and pair preference. **Huetone** (https://huetone.ardov.me) is the interactive
OKLCH+APCA version of the same workflow.

---

## 8. Prior art

Liveness verified 2026-09-13 where marked.

### 8.1 Sefaria — the closest living peer, and not a chord diagram

- Link Explorer: **https://www.sefaria.org/explore** ✅ · deep links follow
  `/explore-{TopCat}-and-{BottomCat}`, CamelCase, e.g. `/explore-Tanakh-and-Bavli` ✅
- Source: **https://github.com/Sefaria/Sefaria-Project**, `static/js/explore.js` ·
  category config in `reader/views.py`
- Aggregate API: `GET /api/counts/links/{topCat}/{bottomCat}` ✅ live
- Precise API: `GET /api/links/bare/{book}/{category}` ✅ live
- Developer docs: https://developers.sefaria.org/ · Linker v3 docs `/docs/linker-v3`

**It is widely mis-described as a chord or arc diagram. It is not.** From the source: a
**bipartite two-rail layout** — older corpus on a top rail (`topOffsetY = 80`), newer on a
bottom rail (`bottomOffsetY = 580`) — with links drawn as cubic Bézier **`d3.svg.diagonal()`**
paths between the rails, never rail-to-itself. Rectangle width encodes book length; each book
gets its own `d3.svg.axis()` revealed on focus, with a `d3.svg.brush()` acting as a verse-range
filter. Colour is `d3.scale.category10()` over *categories*, with a UI toggle flipping whether a
link is coloured by its top-rail or bottom-rail book. **Direction is carried by spatial
convention, so no arrowheads are needed.** Built on **D3 v3 from CDN**, as a separate webpack
entry bolted onto a Django template — not a React component.

**The aggregation strategy is the lesson.** Two tiers of level-of-detail, not filtering:

| Pairing (live) | book-pair marks drawn | underlying links |
|---|---:|---:|
| Tanakh × Bavli | 1,016 | 24,203 |
| Tanakh × Midrash Rabbah | 368 | 26,994 |
| Bavli × Mishneh Torah | 1,965 | 32,501 |
| Bavli × Shulchan Arukh | 144 | 19,042 |
| **all seven views** | **4,578** | **124,073** |

Seven views cover ~124,000 links and **never draw more than ~2,000 marks at once.** Clicking a
book hides the aggregates and fetches precise segment-level links for that book alone, memoised
client-side. **This is exactly V2's architecture: aggregate to the pair and the class, assert
the cell count, drill to witnesses.**

**Also steal:** the saturating width function (§V4); deep-linkable, fully deterministic state
(`/explore-Tanakh-and-Bavli` is citable — Sefaria's explorer is not a stochastic layout, and
that is not an accident); `dataSource` recorded **per topic-link**, i.e. provenance on the edge;
and the special-casing of "The Twelve" so twelve tiny books remain clickable — we will need the
same for short mandalas and the Vālakhilya.

**What Sefaria does not do, and where we must go further:** its link set is homogeneous and
human-curated, so it never needs to distinguish a source-stated link from an inferred one. Our
`CrossVedaCellStatus` has six values where Sefaria has one. **That difference is the product.**

**Criticisms.** Liz Shayne's Gephi analysis
(https://lizshayne.wordpress.com/2014/06/17/sefaria_in_gephi/) is the sharpest, and it comes
from inside the community: the graph is *"a reflection of how far Sefaria has come in
crowdsourcing"*; 87% of nodes in her snapshot were Bible, Rashi or Gemara; the full force-directed
render was *"almost impossible to read"* and she fell back to an in-degree × out-degree scatter;
and direction is real but the aggregate hides it — Gemara pages are high out-degree, biblical
verses high in-degree, while the API returns one symmetric count per pair. Sequential adjacency
("this verse follows that verse") is absent from the link model entirely.

### 8.2 Bible cross-reference visualizations — the cautionary peer

- Chris Harrison & Christoph Römhild, *Visualizing the Bible*:
  **https://www.chrisharrison.net/index.php/visualizations/BibleViz** ✅
- OpenBible.info cross references (~340,000, CC-BY):
  **https://www.openbible.info/labs/cross-references/** ✅

Harrison's piece plots **63,779 arcs** over a bar chart of all 1,189 KJV chapters, coloured by
distance between chapters, "creating a rainbow-like effect." The decisive citation is **the
authors' own statement on the page: they *"set our sights on something more beautiful than
functional."*** That forecloses the "it was meant to be analytical" defence, and it is why §3.2
rejects arcs-at-scale for our reuse data.

Two substantive critiques worth carrying:
1. **Colour is spent on nothing anyone needs.** Arc distance is already encoded by the arc; the
   rainbow has no perceptual order and is applied across 63,779 overlapping marks. See Borland
   & Taylor 2007 (§7.6).
2. **The data-model critique, from a sympathetic remake**
   (https://viz.bible/remaking-an-influential-cross-reference-visualization/): the underlying
   source is R.A. Torrey's *Treasury of Scripture Knowledge*, which indexes **topically, not by
   direct textual reference** — so Revelation lacks the Old Testament links a reader would
   expect. **The picture is a picture of a 19th-century index's editorial policy, and nothing on
   the chart says so.** The remaker also independently reinvented Sefaria's aggregation, rolling
   verse-level links up to chapter level to make it tractable, and swapped distance-colour for
   book-colour to make highlighting legible.

OpenBible's dataset is genuinely more useful than its picture, precisely because it carries a
**vote/rank field per reference** — an explicit quality signal, the same move as our trust
tiers.

### 8.3 Corpus-linguistic forms worth borrowing

- **Lexical dispersion plot** — NLTK `nltk.draw.dispersion_plot`
  (https://www.nltk.org/api/nltk.draw.dispersion_plot.html); popularised in *Natural Language
  Processing with Python* ch. 1. Direct ancestor of V6. *(I could not pin a first publication of
  the plot form itself; describe it as descending from concordance and dispersion measurement in
  corpus linguistics rather than naming an inventor.)*
- **Voyant Tools** — https://voyant-tools.org/ (⚠ **returned HTTP 502 on 2026-09-13**; working
  mirrors include https://libvoyant.unm.edu/). Sinclair & Rockwell, first released 2003;
  companion volume *Hermeneutica* (MIT Press, 2016). The tools that matter here:
  **Bubblelines** (one line per document, divided into 50 segments by default, bubble size =
  term frequency per segment — the closest existing implementation of V6), **Trends** (relative
  frequency over ordered segments), **MicroSearch** (vertical blocks, height = document size,
  occurrences as marks), **Contexts/KWIC**, **Phrases** (repeating n-grams — the closest Voyant
  tool to formulaic diction), **Correlations** (term pairs with Pearson's r), **Mandala**
  (search terms as rim "magnets", each document pulled toward each in proportion to relative
  frequency — a genuinely transferable form for "which hymns pull toward Agni vs Indra vs
  both"), **Collocates Graph** and **RezoViz** (the two network views, and the hairball risk
  inside Voyant), **TextualArc** (inherits TextArc's centroid flaw), and **Cirrus** (the word
  cloud, rejected in §3.3). There is **no tool named "Links."**
  - Voyant's most admirable habit, and one to copy: **it ships the caveat inside the panel that
    produces the number** — its own docs state that WordTree branches are *"not necessarily
    based on frequency"*, that Topics truncates at the first 1,000 words per document, and that
    Dreamscape's location sequences *"may or may not signify anything at all."*
  - The standing critique is reproducibility: Herrmann et al., *"Tool criticism in practice"*,
    DHQ 17(2), 2023 (https://dhq.digitalhumanities.org/vol/17/2/000687/000687.html) —
    *"unreflective adoption of technology in the shape of tools can compromise the plausibility
    and the reproducibility of the results."* Voyant's silent defaults (50 segments, 10 trend
    bins, ±2-word collocate span, unstated stopword list) determine results.
- **TextArc**, W. Bradford Paley, SIGGRAPH 2002 Art Gallery. **textarc.org no longer resolves
  (DNS failure, verified 2026-09-13) — do not cite it as live.** Surviving records:
  https://history.siggraph.org/artwork/w-bradford-paley-textarc/ ; living D3 reimplementation at
  **http://vallandingham.me/textarc/**. The whole text drawn around an ellipse; each distinct
  word placed at the *average position* of its occurrences, with rays on hover. Its failure is
  instructive for V6: **the centroid is a lossy statistic** — a word heavy in chapters 1 and 12
  lands in the middle, indistinguishable from an evenly-spread word. It also died with its Java
  applet and its domain, which is the standing warning about single-author DH tooling. Paley's
  artist statement is the exact opposite of Harrison's and worth quoting: he chooses colour,
  shape and motion as *"transparent filters"*, wanting viewers to notice *"how plain the filter
  is; the beauty must be in the subject."*
- **Google Ngram Viewer** (https://books.google.com/ngrams) and its definitive critique:
  **Pechenick, Danforth & Dodds, "Characterizing the Google Books Corpus: Strong Limits to
  Inferences of Socio-Cultural and Linguistic Evolution"**, PLOS ONE 10(10):e0137041, 2015,
  https://doi.org/10.1371/journal.pone.0137041. Two findings to carry: the corpus is *"in
  effect a library, containing one of each book,"* so *"a single, prolific author is thereby
  able to noticeably insert new phrases into the Google Books lexicon, whether the author is
  widely read or not"*; and scientific texts take an increasing share through the 20th century,
  so apparent cultural trends are corpus-composition drift. **A normalised frequency line looks
  identical whether the denominator changed or the phenomenon did** — which is why every
  per-Veda figure in this product carries its denominator and its layer coverage.
- **Bookworm** (Ben Schmidt / HathiTrust, https://bookworm.htrc.illinois.edu/) — frequency over
  time **faceted by metadata**, i.e. it lets you decompose a trend by corpus composition, which
  is exactly what Ngram forbids.

### 8.4 Text-reuse projects — the direct methodological peers

- **Viral Texts** (Cordell & Smith, Northeastern) — https://viraltexts.org/ ✅ ·
  clusters https://clusters.viraltexts.org ✅ · networks
  http://networks.viraltexts.org/1836to1899/index.html. Reprinting in 19th-c newspapers.
  The primary product is a **cluster-centric search interface**, not a picture; clusters are
  labelled by extent — *"38 reprints from 1870-09-24 to 1871-02-03"* — because most such texts
  had no headline or byline. And the project calls its output **"speculative bibliographies"**,
  naming its own uncertainty in the product label.
- **Passim** (David A. Smith) — https://github.com/dasmiq/passim ✅ · tutorial:
  Romanello & Hengchen, *Programming Historian*,
  https://programminghistorian.org/en/lessons/detecting-text-reuse-with-passim. Two-stage:
  character n-gram seeding (default n=25, `--maxDF 100` drops boilerplate-like terms) then
  character-level alignment. Output records carry `cluster`, `size`, `begin`/`end`, **`src`
  (the inferred source passage — it takes a position on directionality)**, and `pboiler` (a
  boilerplate score). It accepts a `locs` field for citation-scheme references, which is
  directly relevant if Vedic passage identity must survive alignment. **Passim ships no
  visualizer**; the community's first plot is always the **cluster-size distribution**, which is
  heavy-tailed. The cluster is the unit of visualization.
- **Tesserae** (University at Buffalo) — https://tesserae.caset.buffalo.edu/ ✅ ; Coffee et al.,
  *"Modeling the Scholars: Detecting Intertextuality through Enhanced Word-Level N-Gram
  Matching"*, DSH/LLC 30(4):503, 2015. **The form is a ranked table, not a picture**, and the
  scoring is the part to copy: score is a function of **the frequency of each matching word in
  its own text** and **the token distance between the two rarest matching words**, summed across
  source and target, log-transformed. Rarer words score higher; tighter clustering scores
  higher. Two features, fully explainable to a philologist. Honest evaluation, from the SCS
  review: it recovers ~2/3 of parallels recorded by commentators on Latin epic and adds about a
  third more, but *"identifies many parallels which seem not meaningful"*, cannot distinguish
  homographs, and *"does not replace the human eye… or even fairly obvious allusions that do not
  depend on close verbal correspondence."*

### 8.5 Sanskrit / Vedic platforms

- **VedaWeb** — https://vedaweb.uni-koeln.de/rigveda ✅ · live OpenAPI
  https://vedaweb.uni-koeln.de/api/openapi.json ✅ (v0.54.1b0) · platform *Tekst*
  https://github.com/VedaWebProject/Tekst · data
  https://github.com/VedaWebProject/vedaweb-data. See §1.5 — seven texts, 41 aligned resources,
  FastAPI + Vue + MongoDB, and **no analytic visualization of any kind.** Note also that
  `/api/texts` and `/api/resources` **require a browser User-Agent** (403 otherwise). Its
  legacy caveat still holds in spirit: *"The VedaWeb application exposes some API endpoints which
  are (at the time) limited to what the application itself needs to run."*
- **Digital Corpus of Sanskrit** (Oliver Hellwig) —
  http://www.sanskrit-linguistics.org/dcs/. Sandhi-split, morphologically and lexically tagged;
  a Universal Dependencies syntactic layer and a WordNet-linked Sembank. **Its annotations are
  ingested into VedaWeb as a named resource** — the two projects are joined.
- **Vedic Treebank** (Hellwig, Scarlata, Ackermann, Widmer; LREC 2020) —
  https://su-lab.unipv.it/tasf/index.php/vedic-treebank/. Universal Dependencies, R̥gveda to the
  early Upaniṣads. **They wrote no visualizer**: the treebank is explicitly *"queried with
  processing and visualization tools provided by Universal Dependencies, such as Tred, Udapi and
  CoNLL-U viewer."* Conform to a standard, inherit its tooling.
- **Samsādhanī** (Amba Kulkarni, University of Hyderabad) — https://sanskrit.uohyd.ac.in/ ✅ ·
  code https://github.com/samsaadhanii/scl. A dependency parser for Sanskrit verse built on
  **Pāṇinian kāraka** relations rather than UD, with *anvaya* (prose word-order) reconstruction —
  necessary because Sanskrit verse word order is free and the sentence must be reassembled before
  it can be drawn.
- **GRETIL** — https://gretil.sub.uni-goettingen.de/gretil.html ✅ (source lineage of this
  project's own `GRETIL.RV.AUFRECHT`) · **TITUS** —
  https://titus.uni-frankfurt.de/texte/texte2.htm ✅. TITUS editions are ingested into VedaWeb
  as named, dated plainText layers — the clean model for reusing an older archive: cite it as a
  layer rather than silently absorbing it.
- **Quranic Arabic Corpus** (Kais Dukes, Leeds) — https://corpus.quran.com/ · syntax docs
  https://corpus.quran.com/documentation/syntax.jsp. 77,430 words; morphology, POS and a
  **syntactic dependency treebank rendered as arc graphs** — and the framework is *"the
  traditional Arabic grammar of iʿrāb"*, not an imported Western scheme. **Two independent
  religious-text computing traditions (this and Samsādhanī) arrived at the same answer: formalise
  the indigenous grammatical apparatus, then draw it.** Its ontology is ~300 concepts for a 77k
  word corpus, admitted only if proper nouns or sharply-bounded classes — a useful external data
  point on resisting ontological sprawl. Canonical text: **Tanzil**, https://tanzil.net/, CC-BY —
  note the pattern that *the canonical text project and the corpus project are separate, and the
  permissive, stable download belongs to the text.*

### 8.6 Methodological references

- **UpSet**: Lex, Gehlenborg, Strobelt, Vuillemot & Pfister, IEEE InfoVis 2014,
  https://doi.org/10.1109/TVCG.2014.2346248 · https://upset.app/ · InfoVis 10-Year Test of Time
  Award 2024. Evaluated and rejected, §3.10.
- **Radial Sets**: Alsallakh, Aigner, Miksch & Hauser, IEEE InfoVis 2013 — sets around a circle,
  bars binned by element *degree*. Worth noting because "how many formula families reach exactly
  *n* Vedas" is a **degree distribution**, a different question from an intersection inventory —
  and `span_census` already answers it. Survey: Alsallakh, Micallef, Aigner, Hauser, Miksch &
  Rodgers, *"The State-of-the-Art of Set Visualization"*, Computer Graphics Forum 35(1), 2016.
  *(There is no InfoVis-canonical technique called "SetVis"; cite the CGF survey instead.)*
- **The hairball critique**: Weingart, *"Demystifying Networks"*, JDH 1(1),
  http://journalofdigitalhumanities.org/1-1/demystifying-networks-by-scott-weingart/ ·
  Peixoto, *"Untangling the hairball using statistical inference"*, https://skewed.de/lab/posts/hairball/
- **Moretti**, *Network Theory, Plot Analysis* (Stanford Literary Lab Pamphlet 2, 2011,
  https://litlab.stanford.edu/LiteraryLabPamphlet2.pdf) — and the standing objection that the
  edge definition does unstated work. **Beveridge & Shan, "Network of Thrones"** (*Math Horizons*
  23(4), 2016, https://mathbeveridge.github.io/files/NetworkofThrones.pdf) is the cleanest
  demonstration: an edge whenever two names occur within **15 words**, arbitrary and *disclosed*.
- **Six Degrees of Francis Bacon** — http://www.sixdegreesoffrancisbacon.com/ ; Warren et al.,
  DHQ 10(3), 2016, https://www.digitalhumanities.org/dhq/vol/10/3/000244/000244.html. ~13,000
  people, 200,000+ statistically inferred relationships, corrected by expert crowdsourcing, with
  per-edge provenance and a **radial ego view** as the primary interface rather than a global
  graph. The closest structural model for our situation.
- **DraCor** — https://dracor.org/. Their framing term is **"Programmable Corpora"**: the corpus
  ships an API, and the Shiny app and ezlinavis are third-party *clients*. **Our visualization
  should be a client of our own API, not a feature of the backend** — which is already the
  architecture.
- **ORBIS** — https://orbis.stanford.edu/. 678 nodes, 1,104 links, edges weighted by **cost in
  time and money rather than distance**, and **never drawn as a node-link diagram**. The
  transferable thesis: the obvious edge weight may not be the meaningful one.
- **Palladio** — https://hdlab.stanford.edu/palladio/ · **Nodegoat** — https://nodegoat.net/ ·
  **Gephi / ForceAtlas2** — Jacomy et al., PLOS ONE 2014,
  https://pmc.ncbi.nlm.nih.gov/articles/PMC4051631/ (authors' own note: *not deterministic*).
- **Ted Underwood**, *Distant Horizons* (Chicago, 2019) — and the sceptical counter-position,
  **Nan Z. Da, "The Computational Case against Computational Literary Studies"**, *Critical
  Inquiry* 45(3), 2019, https://www.journals.uchicago.edu/doi/abs/10.1086/702594, with the open
  forum of responses at critinq.wordpress.com.
- Colour and uncertainty references are cited inline in §4 and §7.

---

## 9. Summary of recommendations

**Build, in this order:** V1 Layer Availability Matrix → V2 Cross-Veda Reuse Matrix →
V3 Evidence Grid → the Truncation Gauge (§3.11) → V12 Recitation Coverage Strip →
V4 Diffusion Alluvial → V5 Named-vs-Ascribed → V7 Corpus Icicle → V9 Provenance Ribbon →
V11 Path Ladder → V8 Limits Map → V10 Co-occurrence Arc. **V6 Invocation Landscape** is the
highest-value discovery surface and is blocked on `VIZ_BLOCKER_01`; unblocking it is the single
best API investment for this phase.

**Do not build:** UMAP/t-SNE constellations (no embeddings exist; the form launders model
opinion as measurement; stochastic layouts cannot be cited), chord diagrams, word clouds,
whole-graph hairballs, treemaps, temporal animations, deity→ritual→concept Sankeys, geographic
maps, UpSet plots, or a radial restyle of the existing neighbourhood view. Reasons in §3.

**Libraries:** selective-import `d3-hierarchy`, `d3-sankey`, `d3-scale`, `d3-shape`, `d3-array`,
`d3-chord` — **19.48 kB gzip measured, and 0 kB shipped from a React Server Component.** Render
every mark in React/SVG with `fill="var(--viz-n)"`, which makes dark mode free and keeps full
token control. Optionally add `@visx/group`, `@visx/heatmap`, `@visx/network` (~3.5 kB, no d3
deps, RSC-safe). Adopt no chart component library: each of the twelve needs a custom mark
vocabulary (hatch, stipple, ghost figure, status glyph) none of them exposes. Use Observable
Plot for exploration and ship none of it; keep ECharts' `renderToSVGString()` + 764-byte client
in reserve as an escape hatch. Six of the twelve should be statically generated at build time —
the graph is frozen.

**Colour:** a five-series, per-theme, OKLCH-tuned categorical palette (§7.4), hue-anchored to
the brand, every swatch ≥3:1 against its own ground and ≥0.10 minimum ΔE_OKLab across normal
vision and all three dichromacies. Five is the measured cap; Spectrum says six, the UK Analysis
Function says four. A single static palette is **not available at this contrast floor** —
measured, the shared lightness band is 0.075 wide — so Carbon's dual-palette approach is forced
by arithmetic, and we preserve series identity by sharing hue and chroma across themes.
**`KnowledgeStatus` is carried by texture and glyph, never by colour**: `NOT_BUILT` and
`UNKNOWN` are separated by ΔE 0.02–0.03, which is to say not at all.

**The one rule that outranks every other:** no chart ships without a test proving it renders
`null` differently from `0`.
