# 05. UX, content and information architecture

**Agent:** 5 (UX / content / IA). **Phase:** 1, research and audit.
**Product:** VedAnvaya (वेदान्वय), "The Vedas, connected." Rebrand of VedaGraph.
**Scope:** writing and structure. No code, no API change, no ontology change.

Every figure in this document was read from the running API at `http://127.0.0.1:8000` or
computed from a response, and the endpoint is named beside it. Nothing is estimated.

**Copy law for every string below.** No em-dash and no en-dash appears anywhere in this
document, including in the prose that is not itself product copy, so that a grep for those
two characters over this file returns nothing and stays a usable check. Banned filler:
elevate, seamless, unleash, next-gen, revolutionize, unlock, dive into, journey, harness,
empower, curated experience. Banned tells: "quietly trusted by", "field notes", version
labels, locale strips, scroll cues, numbered section eyebrows.

---

## 0. The figures this copy is allowed to use

Read live, 2026-09-13. Re-read before shipping if the graph is rebuilt.

| Figure | Value | Endpoint |
|---|---|---|
| Samhitas held | 4, one recension each | `/api/v1/works` |
| Verses addressed | 20,210 | `/api/v1/stats` `corpus.mantras.total` |
| Rigveda Sakala | 10,552, 100% addressed, 10,502 translated (99.5%) | `/api/v1/works` |
| Atharvaveda Saunaka | 5,839, 4,878 translated (83.5%) | `/api/v1/works` |
| Yajurveda Vajasaneyi Madhyandina | 1,975, 1,903 translated (96.4%) | `/api/v1/works` |
| Samaveda Kauthuma arcika | 1,844, **0 translated** | `/api/v1/works` |
| Translations, all corpora | 17,283 | `/api/v1/stats` |
| Recitations | 16,834 (RV 10,402 / AV 4,680 / YV 1,752 / **SV 0**) | `/api/v1/audio/stats` |
| Resolved deities | 184 | `/api/v1/stats` `deities.resolved_deities` |
| Anukramani devata ascriptions | 214 | `/api/v1/stats` |
| Seers | 616, in 87 families | `/api/v1/stats` `seers` |
| Non-seer addressees in the seer slot | 113 | `/api/v1/stats` |
| Metres | 575 | `/api/v1/stats` |
| Formula families | 720; 107 reach all four | `/api/v1/insights/formula-diffusion` |
| Cross-Veda relatedness edges built | 8,412 | `/api/v1/insights/capabilities` |
| Directed reuse, RV to SV only | 1,684 | `/api/v1/insights/cross-veda` |
| Entity types | 31 | `/api/v1/entities` |
| Entities outside formulas, families and metres | 1,350 (computed by summing `/api/v1/entities` minus formula 4,825, formula_family 720, chandas 575) | `/api/v1/entities` |
| Recorded limits catalogued | 7 | `/api/v1/insights/capabilities` |
| Modelled rites | 8 | `/api/v1/stats` |
| Human concerns | 7; afflictions 26 | `/api/v1/insights/atharvaveda/concerns` |
| Interpretive claims | 6, permanently candidate | `/api/v1/stats` |
| Script split | 16,391 RV and AV in IAST only; 3,819 SV and YV in Devanagari only; no passage has both | reader `text.caveats` |
| Strongest review state | model-adjudicated, 613 edges; nothing human-reviewed | `docs/reports/V3_2_FINAL_100_QUESTION_BENCHMARK.md` Q98 |
| Ask benchmark | 60 questions: 36 supported-correct, 8 partial, 16 correctly refused, 0 misleading, 0 hallucinated, 279 citations | `PRODUCT_V1_SCOPE.md` section 5 |

**One figure is deliberately not usable.** The graph's own relationship count is withheld by
the API, which states why: most edges are one annotation layer's projection of a container
label onto the passages inside it, so a headline built from them measures the build and not
the corpus. **No surface may print a relationship total.** Node and edge totals appear in
`README.md` and `PRODUCT_V1_SCOPE.md` as engineering record. They stay there.

Citation prefixes, verified against `/api/v1/search`: `RV 1.1.1`, `AVS 1.1.1`, `VSM 1.1`,
`SV ARANYA 3.4`. `VS 1.1` resolves to nothing. Any copy that shows an example citation must
use the four forms above.

---

## 1. Information architecture

### 1.1 The problem with the proposed set

The proposed primary nav is Ask / Vedas / Explore / Connections / Visualize / Graph, with
Deities / Entities / About in overflow. Six slots, and four of them (Explore, Connections,
Visualize, Graph) are browse abstractions. A reader cannot tell from the labels alone which
of those four holds the cross-Veda matrix and which holds the node-link view.

It also drops **Limits** and **Evidence** out of the header entirely. Those two pages are
the product's argument. A nav that hides them while promoting three browse modes is a nav
that describes a graph database and not this product.

### 1.2 Recommended final IA

**Primary nav, six items, in this order.**

| Slot | Label | Route | Why it earns a slot |
|---|---|---|---|
| 1 | Ask | `/ask` | The one verb a first-time reader already has. It must be first and it must be a peer of reading, not the headline. |
| 2 | Vedas | `/vedas` | The corpus. The product is a reader before it is anything else. |
| 3 | Explore | `/explore` | The single door to every entity surface: deities, seers, rites, things, concerns. Absorbs the ambiguity so the other slots do not have to. |
| 4 | Connections | `/connections` | The only cross-corpus surface, and the brand word. Distinct from Graph because it is about text travelling, not about nodes. |
| 5 | Graph | `/graph` | The signature instrument. World view at the root, focused neighbourhood at `?node=`. |
| 6 | Visualize | `/visualize` | New. The visualization lab. Earns a slot because it is the only surface where absence is drawn to scale rather than written. |

**Overflow, under a "More" disclosure present at every width, in this order.**

| Label | Route | Note |
|---|---|---|
| Limits | `/limits` | First, deliberately. |
| Evidence | `/evidence` | Re-parented from `/insights`. See 1.4. |
| Deities | `/devatas` | Also reachable from Explore. |
| Entities | `/entities` | Also reachable from Explore. |
| Sources | `/sources` | New. |
| About | `/about` | New. |

**Search** stays where it is: a persistent affordance in the header actions with its `/` key
hint, not a nav item. It is a tool, not a destination.

### 1.3 Why Limits sits in overflow and not in the primary six

Stated as a principle, because it will be challenged.

> The primary nav answers "what can I do here". The overflow answers "where else can I go".
> Limits is not a destination a reader navigates to cold. It is a claim the product has to
> make at the point of every figure, and it already does: `Caveat`, `KnowledgeStatus` and
> `CaveatList` carry it in place on every surface that shows a number.

Limits therefore gets four guaranteed placements instead of one: first in the overflow,
first in the footer's first column, a full homepage section with a primary call to action,
and an in-place link from every caveat that states a boundary. That is more prominence than
a sixth nav slot would buy, and it puts the claim next to the number it qualifies.

### 1.4 Every existing route, with its disposition

`frontend/src/app`, complete.

| Route | Disposition | Notes |
|---|---|---|
| `/` | Keep and restyle | New narrative, section 2 of this document. |
| `/ask` | Keep and restyle | Copy in section 6. |
| `/vedas` | Keep and restyle | Ledger treatment, per-Veda boundary stays. |
| `/vedas/[veda]` | Keep and restyle | Native hierarchy browser. |
| `/passage/[key]` | Keep and restyle | Priority surface. Content model in section 5. |
| `/reuse/[key]` | Keep and restyle | Side-by-side comparison. Reached from the passage page and from Connections. |
| `/search` | Keep and restyle | Add surface-coverage disclosure, section 10. |
| `/explore` | Keep and restyle | Becomes the parent of every entity surface. Add Deities and Entities as lens cards so the nav overflow is not the only route. |
| `/explore/atharvaveda` | **Re-parent** to `/explore/human-concerns` | See 1.5. |
| `/devatas` | Keep as-is | URL unchanged. |
| `/devatas/[id]` | Keep as-is | |
| `/entities` | Keep as-is | |
| `/entities/[type]` | Keep as-is | |
| `/entities/[type]/[id]` | Keep as-is | |
| `/rituals` | Keep and restyle | Linked from Explore only. |
| `/rituals/[id]` | Keep and restyle | |
| `/material-culture` | Keep and restyle | Linked from Explore only. |
| `/formulas` | Keep and restyle | Linked from Connections and Explore. |
| `/formula-families/[id]` | Keep and restyle | |
| `/connections` | Keep and restyle | Promoted to primary nav. |
| `/graph` | Keep and restyle | Gains the world view at the root. `?node=` unchanged. |
| `/insights` | **Re-parent** to `/evidence` | See 1.4.1. |
| `/limits` | Keep and restyle | |
| `layout.tsx` | Keep and restyle | New header, new footer, new metadata. |
| `loading.tsx` | Keep and restyle | Copy in section 10. |
| `error.tsx` | Keep and restyle | Copy in section 10. |
| `not-found.tsx` | Keep and restyle | Copy in section 10, with the broken hairline. |

**Added routes:** `/visualize`, `/visualize/[id]`, `/about`, `/sources`, and a `/explore/human-concerns`
target. Nothing else.

#### 1.4.1 `/insights` moves to `/evidence`

The page is already labelled "Evidence" in `PRIMARY_NAV` and `SECONDARY_NAV`. The URL says
"insights", which is the one marketing word that survived into the routing table, and it
misdescribes the page: the page separates measured data from derived measures from recorded
interpretation, which is the opposite of an insight feed.

```
# next.config: permanent, both directions of the trailing slash
{ source: "/insights", destination: "/evidence", permanent: true }
```

The API path `/api/v1/insights/...` is unaffected and must not be touched.

### 1.5 `/explore/atharvaveda` moves to `/explore/human-concerns`

This is the only re-parent with a content argument behind it. The route is named for a Veda,
but `/api/v1/insights/atharvaveda/concerns` returns `by_veda` figures across all four
corpora: "overcoming rivals (sapatna)" is 87 in AV and also 7 in YV, 6 in RV and 1 in SV.
A reader who lands on a URL named `atharvaveda` and reads a four-Veda table has been told
something false by the address bar.

```
{ source: "/explore/atharvaveda", destination: "/explore/human-concerns", permanent: true }
```

The page keeps its Atharvavedic emphasis in the copy, because the concentration is real and
measured. Only the address stops claiming exclusivity.

### 1.6 Redirect ledger

Two permanent redirects. No existing URL breaks.

| From | To | Status |
|---|---|---|
| `/insights` | `/evidence` | 308 |
| `/explore/atharvaveda` | `/explore/human-concerns` | 308 |

---

## 2. Homepage, section by section

Ten sections. Layout families are named so that no two neighbours repeat, and so the
"no more than two consecutive image-and-text splits" rule can be checked by reading the
family column alone.

**Layout families used:** A asymmetric hero, D full-bleed ledger table, E image-and-text
split, J inline coverage bars, H live embedded instrument, K full-bleed single visual,
I two-up contrast pair, F stacked editorial statement, G index list. Nine distinct families
across ten sections. Family E appears twice, at S3 and S6, never adjacent.

**Kicker budget: three allowed, two used.** S2 and S5. The third is deliberately not spent;
the reader page takes मन्त्र instead, where the word names the actual unit on screen.

---

### S1. Hero

**Family:** A, asymmetric hero. Type block left, live neighbourhood vignette right, set off
the column grid so it does not read as a two-column split.
**Kicker:** none.
**Text elements:** three, plus two calls to action.

**Brand line (element 1, Devanagari):**

> वेदान्वय

**Headline (element 2, two lines exactly):**

> Four Samhitas, one corpus,
> and the evidence behind every connection.

**Subtext (element 3, 18 words):**

> Read any verse with its recitation, follow a deity across the four collections, and see what is missing.

**Primary call to action:** Read the Vedas → `/vedas`
**Secondary call to action:** Open the graph → `/graph`

Ask is not a hero call to action. It gets S8. A product that opens with a question box is an
answer machine, and this one is not.

**Data:** `/api/v1/graph/neighborhood/VG:DEVATA:INDRAH?depth=1&limit_per_type=3` for the
vignette. If it fails, the vignette renders its own quiet absence (section 10) and the hero
type is unaffected.

---

### S2. What is actually held

**Family:** D, full-bleed ledger table. Four rows, editorial rules, no cards.
**Kicker:** श्रुति / THE VEDAS

> Justification for the Devanagari: śruti is the tradition's own collective name for exactly
> these four collections, and this is the one section that says which recension of each is
> present. The word is doing denotative work: it names the object of the table.

**Headline:**

> Four Samhitas, one recension each.

**Body:**

> Three of the four are partial in ways their traditional names do not reveal. The table
> says which part, in every row, before it says how much.

**Table columns:** Collection / Recension held / Verses / Translated / Recited / Not held

| Collection | Recension held | Verses | Translated | Recited | Not held |
|---|---|---:|---:|---:|---|
| Rigveda | Sakala | 10,552 | 10,502 | 10,402 | The Ashvalayana recension. No Brahmana, Aranyaka or Upanisad. |
| Samaveda | Kauthuma, arcika only | 1,844 | 0 | 0 | The gana collections, which are the larger body. Jaiminiya and Ranayaniya. |
| Yajurveda | Shukla, Vajasaneyi Madhyandina | 1,975 | 1,903 | 1,752 | The whole of the Krishna Yajurveda. The Kanva recension. |
| Atharvaveda | Saunaka | 5,839 | 4,878 | 4,680 | The Paippalada recension. |

**Closing line under the table:**

> The Yajurveda row is the one most likely to mislead, because "the Yajurveda" ordinarily
> means both the White and the Black. The Black is not held at all.

**Call to action:** Read the Vedas → `/vedas`
**Data:** `/api/v1/works` for the first five columns, `/api/v1/audio/stats` for Recited,
`excluded_corpora` and `scope_honest_label` for Not held.

---

### S3. Reading a verse

**Family:** E, image-and-text split. A real reader frame on the left at three quarter scale,
copy on the right.
**Kicker:** none.

**Headline:**

> A verse, and everything standing behind it.

**Body:**

> The Sanskrit, the recitation, the translation where one exists, the seer and the deity the
> apparatus assigns, the words the verse actually contains, and the wording it shares with
> another collection. Each of those comes from a named layer, and each says how it was
> established. An assignment from the traditional index is never shown as a statement the
> Sanskrit makes.

**Call to action:** Open this passage → `/passage/VG:RV:SAK:M01:S001:V001`
**Data:** `/api/v1/passages/{key}/reader` and `/api/v1/passages/{key}/audio` for the frame.
The frame is a real render, not an illustration.

---

### S4. Recitation

**Family:** J, inline coverage bars. Four horizontal bars, the fourth drawn as a typed
absence rather than a zero-length bar.
**Kicker:** none.

**Headline:**

> 16,834 verses, each with its own recitation.

**Body:**

> One recording per verse, from VedSearch. A recording is attached only when two things
> agree: our canonical key lands in the source's numbering, and the text that source says
> the recording recites matches this corpus's own text for that key. Where they disagree the
> mapping is refused and recorded as a gap. That check caught a real one. VedSearch numbers
> Rigvedic Mandala 8 in Griffith's order, so a key-for-key mapping would have attached the
> wrong recitation to 55 hymns.

**The bars.** Rigveda 10,402 of 10,552. Atharvaveda 4,680 of 5,839. Yajurveda 1,752 of
1,975. Samaveda: no bar. In its place, this label, at the same weight as the other three:

> **Samaveda: no recording exists.** The source publishes Samavedic verse text and no
> Samavedic audio, and no other source located offers Kauthuma arcika recitation mapped to
> individual verses. This is the Veda defined by its sung realisation. The gap is in what has
> been published anywhere, not a choice made here.

**Call to action:** none. This section ends on the absence.
**Data:** `/api/v1/audio/stats` for the three bars, `/api/v1/works/VG:WORK:SV:KAU/audio` for
the Samavedic label, which returns `NOT_BUILT` with that caveat already written.

---

### S5. Wording that travels

**Family:** H, live embedded instrument. The cross-Veda pair matrix, rendered live, six
pairs by six relationship classes, with `NOT_BUILT` and `NOT_ESTABLISHED_FOR_PAIR` drawn as
distinct states.
**Kicker:** अन्वय / CONNECTIONS

> Justification for the Devanagari: anvaya is the second half of the product's own name, and
> in the grammatical tradition it names the construal that makes a verse readable as
> connected sense. This is the section about construing four collections as one corpus. It is
> the single most load-bearing Devanagari word on the site.

**Headline:**

> The same wording stands in more than one collection.

**Body:**

> 8,412 cross-corpus connections are built, and they are five different kinds, never one
> similarity score: exact parallel, near parallel, variant, shared formula, shared entity
> vocabulary. Two cells in this matrix are empty on purpose. Directed reuse was established
> for the Rigveda and Samaveda pair only, which is a fact about what was built. Non-lexical
> resemblance was never built at all, which is why that row reads as unbuilt and not as zero.

**Call to action:** Open connections → `/connections`
**Data:** `/api/v1/insights/cross-veda` for `pairs` and `relationship_classes`.

---

### S6. The graph

**Family:** E, image-and-text split, reversed from S3. Live focused neighbourhood left, copy
right. Not adjacent to S3.
**Kicker:** none.

**Headline:**

> Select any line and it explains itself.

**Body:**

> Every relationship carries what it is, how it was established, which passage carries it,
> and what it does not establish. Nothing in this graph is human-reviewed. The strongest
> review state anywhere in it is model-adjudicated, on 613 edges, and the interface says so
> rather than letting a tidy edge imply a verified one.

**Call to action:** Open the graph → `/graph`
**Data:** `/api/v1/graph/neighborhood/{id}` and `/api/v1/graph/relationships/{id}` for the
selected edge.

---

### S7. Drawn to scale

**Family:** K, full-bleed single visual. One large chart edge to edge, minimal type over it.
**Kicker:** none.

**Headline:**

> Coverage, drawn including the parts that are empty.

**Body:**

> Every visualization here answers one stated question and draws its own absence. A cell with
> no evidence is not left blank and is not filled with a zero. It is drawn as the kind of
> absence it is: a layer never built, evidence that cannot settle the claim, or a real answer
> over part of the corpus.

**Call to action:** Open the visualizations → `/visualize`
**Data:** whichever single visualization the lab nominates as its lead. Recommended lead:
translation and recitation coverage across the four corpora, because it is the one chart in
which the Samavedic column is empty twice, for two different reasons.

---

### S8. Ask

**Family:** I, two-up contrast pair. Two panels of equal weight, side by side.
**Kicker:** none.

**Headline:**

> Ask a question. Check the answer.

**Left panel heading:** What it does

> Retrieval runs first, over a fixed catalogue of channels, and the model sees only what
> retrieval returned. Every factual sentence carries a citation you can open: the retrieved
> item, its Sanskrit, its translation and its canonical citation.

**Right panel heading:** What it refuses to do

> A question this build cannot answer returns insufficient evidence and names the dimension
> it could not reach. It does not guess, and it does not turn a gap in the graph into a
> confident denial about the Vedas. Over 60 graded questions: 36 answered and supported, 8
> partial, 16 correctly refused, 0 misleading, 0 hallucinated.

**Call to action:** Ask a question → `/ask`
**Data:** `/api/v1/ask/health` to decide whether the call to action is live or carries the
not-configured note. Benchmark figures are fixed copy from `PRODUCT_V1_SCOPE.md` section 5
and are not fetched.

---

### S9. Absence

**Family:** F, stacked editorial statement. One centred measure, large quiet type, no
visual, generous space above and below.
**Kicker:** none.

**Headline:**

> When there is nothing to show, we say whose nothing it is.

**Body, three lines, set as three separate lines:**

> **Not built.** The layer does not exist here. The silence is ours.
> **Insufficient evidence.** Evidence exists and cannot support the claim. This is not a zero.
> **Partial.** A real answer over part of the corpus, one collection, or one kind of evidence.

**Closing line:**

> Seven limits are catalogued with the measurement behind each one and a better question to
> ask instead. The catalogue is not exhaustive, and it says so: a question absent from it is
> not thereby answerable.

**Call to action:** See what is not held → `/limits`
**Data:** `/api/v1/insights/capabilities`. The count of seven is `limits.length`.

---

### S10. Where to start

**Family:** G, index list. Dense, ruled, contents-page feel. Six rows.
**Kicker:** none.

**Headline:**

> Where to start.

**Rows.** Each row is a link with a title and a one-line note.

| Title | Note | Destination |
|---|---|---|
| The first verse of the Rigveda | Sanskrit, recitation, translation, and where each came from | `/passage/VG:RV:SAK:M01:S001:V001` |
| Indra across the four collections | Named in 3,566 verses. The apparatus assigns him in one collection only | `/devatas/VG:DEVATA:INDRAH` |
| Soma, as a deity and as a substance | One word, two records, both linked, neither merged | `/devatas/VG:DEVATA:SOMAH` |
| Rigvedic wording in the Samaveda | 1,684 directed reuse edges, the only pair for which reuse was established | `/connections` |
| What the Atharvaveda addresses | Fever, consumption, rivals, household life. Counts are lexical minima, never diagnoses | `/explore/human-concerns` |
| A formula through four collections | 107 formula families reach all four | `/formulas` |

**Closing line under the list:**

> Built by one person, over the sources named on the sources page.
> [About this project](/about) · [See the sources](/sources)

**Data:** the Indra figure from `/api/v1/insights/devatas/VG:DEVATA:INDRAH` `named_total`.
The 1,684 from `/api/v1/insights/cross-veda`. The 107 from
`/api/v1/insights/formula-diffusion` `coverage.measured.reaching_all_four`.

---

### 2.1 Homepage layout sequence, checkable

| # | Section | Family | Kicker |
|---|---|---|---|
| S1 | Hero | A asymmetric hero | none |
| S2 | What is actually held | D ledger table | श्रुति / THE VEDAS |
| S3 | Reading a verse | E split | none |
| S4 | Recitation | J coverage bars | none |
| S5 | Wording that travels | H live instrument | अन्वय / CONNECTIONS |
| S6 | The graph | E split | none |
| S7 | Drawn to scale | K full-bleed visual | none |
| S8 | Ask | I two-up pair | none |
| S9 | Absence | F stacked statement | none |
| S10 | Where to start | G index list | none |

Distinct families: 9. Maximum consecutive splits: 1. Kickers: 2 of a budget of 3.

---

## 3. Call to action language

One label per intent, site-wide. A label never serves two intents, and an intent never has
two labels.

**Rules.** Sentence case. Imperative. No trailing punctuation. No "Learn more", "Click
here", "Discover", "Get started", "Explore more". A label names the object it opens, so it
can be read out of context by a screen reader without its surrounding card.

| Intent | Label | Replaces |
|---|---|---|
| Go to the corpus browser | **Read the Vedas** | "Explore the Vedas" |
| Open one collection's structure | **Open this collection** | "Open collection" |
| Open a single verse in the reader | **Open this passage** | "Open passage", "Open this record" |
| Go to the previous or next verse | **Previous verse** / **Next verse** | "Previous" / "Next" |
| Play a verse's recitation | **Play recitation** | new |
| Leave the site for an upstream source | **Open at the source** | "Open the original source", "Open the recording at its source" |
| Copy a text block | **Copy** | unchanged |
| Open the graph at large | **Open the graph** | "Open the knowledge graph" |
| Show one item inside the graph | **Show this in the graph** | "Open in the graph", "Open this family in the graph", "Open this work in the graph" |
| Expand one node's neighbours | **Expand this node** | unchanged |
| Collapse one node's neighbours | **Collapse this node** | unchanged |
| Re-centre the graph on a node | **Centre on this node** | "Open {label}" |
| Explain one relationship | **Why this connection** | new |
| Open the visualization lab | **Open the visualizations** | new |
| Open one visualization | **Open this visualization** | new |
| Start a new question | **Ask a question** | new |
| Ask about the thing on screen | **Ask about this** | "Ask about this mantra", "Ask about {deity}" |
| Open a cited item from an answer | **Open the citation** | new |
| Show the evidence an answer used | **See what was retrieved** | new |
| Go to the cross-Veda surface | **Open connections** | "Explore connections", "Open the cross-Veda explorer" |
| Compare two parallel passages | **Compare the two texts** | "Compare the two texts side by side" |
| Open a deity or entity profile | **Open this profile** | "Open full profile", "Open the deity atlas" |
| Open a curated lens | **Open this lens** | unchanged |
| Search the corpus | **Search the corpus** | unchanged |
| Go to the limits catalogue | **See what is not held** | "See every recorded limit", "What this atlas cannot answer", "See what this product cannot answer" |
| Go to the evidence page | **See the evidence** | "Evidence and interpretation", "See how evidence and interpretation are separated", "See how that separation works" |
| Go to the sources page | **See the sources** | new |
| Go to the about page | **About this project** | new |
| Lengthen a truncated list | **Show more** | new |
| Shorten an expanded list | **Show fewer** | new |
| Retry a failed load | **Try again** | unchanged |
| Return to the homepage | **Return home** | unchanged |

**Twelve labels are retired by this table.** The largest single cleanup is the four variants
of "open in the graph" collapsing to one, and the four variants of the limits link collapsing
to one.

---

## 4. Navigation copy

`PRIMARY_NAV` and the overflow, with the one-line descriptions used in the mobile drawer.
Descriptions are for the drawer only. The desktop bar shows labels alone.

### 4.1 Primary

```ts
export const PRIMARY_NAV: NavItem[] = [
    { href: "/ask",         label: "Ask",         description: "Put a research question to the corpus and check the answer" },
    { href: "/vedas",       label: "Vedas",       description: "Read each collection in its own hierarchy" },
    { href: "/explore",     label: "Explore",     description: "Deities, seers, rites, things and human concerns" },
    { href: "/connections", label: "Connections", description: "Wording that stands in more than one collection" },
    { href: "/graph",       label: "Graph",       description: "The entity network, with every relationship explained" },
    { href: "/visualize",   label: "Visualize",   description: "Coverage and reach, drawn including what is empty" },
];
```

### 4.2 Overflow

```ts
export const OVERFLOW_NAV: NavItem[] = [
    { href: "/limits",   label: "Limits",   description: "What this build cannot answer, and the measurement behind each limit" },
    { href: "/evidence", label: "Evidence", description: "Measured data, derived measures and recorded interpretation, kept apart" },
    { href: "/devatas",  label: "Deities",  description: "Who is invoked, where, and on whose authority" },
    { href: "/entities", label: "Entities", description: "People, places, things and ideas the texts name" },
    { href: "/sources",  label: "Sources",  description: "Every text, translation and recording, with its licence" },
    { href: "/about",    label: "About",    description: "Why this exists, and who built it" },
];
```

### 4.3 Header and drawer chrome

| Element | Copy |
|---|---|
| Wordmark link `aria-label` | `VedAnvaya, home` |
| Search action label | `Search` with the `/` key hint |
| Overflow trigger | `More` |
| Overflow trigger `aria-label` | `More sections` |
| Mobile trigger `aria-label` | `Open navigation` |
| Mobile drawer title | `Go to` |
| Mobile drawer close `aria-label` | `Close navigation` |
| Skip link | `Skip to content` |
| Theme toggle `aria-label` | `Switch to dark theme` / `Switch to light theme` |

The mobile drawer lists Search first, then the six primary items, then a rule, then the six
overflow items. The rule needs no heading.

---

## 5. Reader and passage page content model

Two columns. The main column is the text and what is directly attached to it. The rail is
the apparatus and the provenance. Nothing in the rail may look like the verse.

### 5.1 Main column, in order

| # | Block | Label copy |
|---|---|---|
| 1 | Location breadcrumb | Work name, then each native level with its own label: `Mandala 1`, `Sukta 1`, `Mantra 1`. The level name is the corpus's own, never "chapter" or "section". |
| 2 | Citation header | Collection chip plus the canonical citation as the page heading, plus the passage's knowledge status. |
| 3 | Sanskrit | Script label, then the text. See 5.3 for the exact script labels. Copy control sits on the label line. |
| 4 | Script disclosure | One line, always present. See 5.3. |
| 5 | Recitation | Player, or a typed absence. See 5.4. |
| 6 | Translation | Heading `Translation`. Translator, year, edition under the quotation. Where none exists, the typed absence in 5.5. |
| 7 | Other witnesses | Collapsed. Summary reads `Other witnesses of this text` with the count. |
| 8 | Cross-Veda callout | Only when a cross-corpus parallel exists. See 5.6. |
| 9 | Adjacent passages | `Previous verse` and `Next verse`. At a boundary, the corpus's own note replaces the missing side. |
| 10 | Page footnotes | The reader's own caveats, verbatim from the API, under a rule. |

### 5.2 Contextual rail, in order

| # | Block | Heading | Sub-label |
|---|---|---|---|
| 1 | Apparatus ascription | **Ascribed by the traditional index** | Each row carries `Stated for this verse` or `Inherited from the hymn`. |
| 2 | Named in the verse | **Named inside this verse** | `From the word the verse uses` |
| 3 | Ideas, acts and things | **Ideas, acts and things** | `Matched on a registered Sanskrit form` |
| 4 | Shared wording | **Shared wording** | `Exact parallel`, `Near parallel`, `Variant`, `Shared formula` |
| 5 | Shared vocabulary | **Shared vocabulary** | `Both passages name the same registered entities. This is not textual reuse.` |
| 6 | Provenance | **Where this text comes from** | Witness id, source, licence, and the edition where one is recorded. |
| 7 | Method | **How these attributions were established** | Per predicate, in one sentence each. |
| 8 | Graph entry | **Show this in the graph** | `{n} curated connections from this verse` |
| 9 | Ask entry | **Ask about this** | none |

**The rail's one hard rule.** Blocks 1 and 2 must never be summed or shown as one figure.
The API says why, and the copy repeats it once, under block 2:

> An ascription is what the traditional index assigns to a hymn. A naming is a word the verse
> actually uses. 15,177 of the 17,889 seer ascriptions in this corpus are a hymn's label
> projected onto each of its verses, so the two counts answer different questions and a
> blended total would compare a statement of the text against a projection of this build.

### 5.3 The script split, presented honestly

This is the disclosure most likely to be softened in review, so the copy is fixed here.

**Script label on a Rigvedic or Atharvavedic verse:**

> Romanised Sanskrit (IAST), accented

**Script label on a Samavedic or Yajurvedic verse:**

> Devanagari, accented

**Script disclosure line, always present, directly under the text block.** Two variants, one
per side of the split.

For RV and AV:

> This verse is held in romanised transliteration only. There is no Devanagari for it in this
> corpus, and none has been generated from the transliteration.

For SV and YV:

> This verse is held in Devanagari only. There is no romanised transliteration for it in this
> corpus, and none has been generated from the Devanagari.

**The full explanation, in the page footnotes, verbatim from the API's own caveat:**

> No passage in this corpus carries both scripts. 16,391 Rigvedic and Atharvavedic verses are
> held in romanised transliteration and 3,819 Samavedic and Yajurvedic verses in Devanagari.
> A missing script is a property of what was ingested for that corpus and not of the text,
> which is why it is reported as an unbuilt layer and not as an empty field.

**What the copy must not do.** It must not say "not available", which reads as a temporary
outage. It must not offer a toggle between scripts, because there is nothing to toggle to. If
a derived transliteration ever ships, it is labelled `Derived from the Devanagari, not a
witness` and it is never the primary text.

### 5.4 Recitation block

**With a recording:**

Player, then a single disclosure line:

> One recording of this verse, from VedSearch. The text this recording recites was compared
> against this corpus's own text for this verse and matched. The source names no reciter.

Control: **Play recitation**. Link: **Open at the source**.

**With no recording, Samavedic:**

> No Samavedic recitation is catalogued. The source that supplies the other three collections
> publishes Samavedic verse text and no Samavedic audio, and no other source located offers
> Kauthuma arcika recitation mapped to individual verses.

**With no recording, any other collection:**

> No recording is mapped to this verse. Either the source does not carry it, or the recited
> text did not match this corpus's text and the mapping was refused. An empty player is never
> evidence that the verse is unrecited.

No disabled player is rendered in either case. A control that cannot act is not shown.

### 5.5 Translation absence

**Samavedic:**

> No translation is released for the Samaveda. None of its 1,844 verses carries one, so this
> is an unbuilt layer for the whole collection and says nothing about this verse.

**Any other collection:**

> No released translation covers this verse in this build. The verse is held. Its translation
> layer is not, and no gap is ever filled from another translator.

### 5.6 Cross-Veda callout

> **This wording also stands in the {collection}.**
> Compare the two texts with the evidence for the connection.

Control: **Compare the two texts** → `/reuse/{key}`.

---

## 6. Ask experience copy

### 6.1 Page heading

**Title:** Ask VedAnvaya

**Description:**

> A research instrument, not a chat model. Your question is classified, the names in it are
> resolved against the graph, a fixed catalogue of retrieval channels runs, and the answer is
> written from what those channels returned and nothing else.

### 6.2 Empty state

Shown before the first question, above the composer.

> **Ask something the corpus can answer, and check the answer against the evidence.**
>
> Retrieval runs before anything is written, so an answer is only ever a reading of what the
> graph returned. If the channels return nothing, you get the empty result and the list of
> channels that were searched, not a paragraph composed from general knowledge.

**Composer placeholder:**

> How does Indra appear across the four Samhitas?

**Scope control label:** `Collections` with options `All four`, `Rigveda`, `Samaveda`,
`Yajurveda`, `Atharvaveda`.
**Mode control label:** `Retrieval` with the existing mode options.
**Submit control:** **Ask a question**. While pending, the control is disabled and the
progress model below takes over.

### 6.3 Six suggested starting questions

Every one of these was verified by replaying the deterministic retrieval stack
(`planner.plan` then `resolver.resolve_entities` then `retriever.retrieve` then
`evidence.build_evidence_packet`) against the live graph, with no language model involved.
The evidence count is the number of items that reached the packet.

| Suggested question | Intents resolved | Channels that returned | Evidence items |
|---|---|---|---:|
| How are Agni and Soma connected? | GRAPH_CONNECTION, ENTITY_PROFILE | entity profile, per-Veda, passages, ascriptions, graph paths, derived metrics | **22** |
| How does Indra appear across the four Samhitas? | CROSS_VEDA, ENTITY_PROFILE | entity profile, per-Veda, passages, ascriptions, derived metrics, lexical presence | **14** |
| How does Soma appear as a deity and as a substance? | ENTITY_PROFILE | as above | **14** |
| Does RV 9.1.1 have a parallel in the Samaveda? | PASSAGE_LOOKUP, FORMULA, TEXTUAL_REUSE | passage by key, parallels, formula families, lexical presence | **11** |
| What metre is ascribed to RV 3.62.10, and how was that established? | PASSAGE_LOOKUP | passage by key, parallels | **7** |
| What does the Atharvaveda record about takman, the fever? | HUMAN_CONCERN | entity profile, per-Veda, passages | **6** |

**Questions tested and rejected, recorded so they are not re-proposed.**

| Rejected question | Why |
|---|---|
| Which metals does this corpus name, and in which Vedas? | Retrieval resolves nothing. "metals" and "corpus" are both unresolved, no channel runs, 0 evidence items, and the response is insufficient evidence. `/api/v1/insights/metals` answers it beautifully. Ask does not. Link the insight, do not suggest the question. |
| Where does Rigvedic wording reappear in the Samaveda? | Resolves to a fabricated-looking subject, "the deities indicated by the wording", and returns 1 item. Wrong shape. The passage-scoped form at RV 9.1.1 is the one that works. |
| What is RV 10.129.1 about? | 1 evidence item. The passage renders beautifully in the reader and thinly in Ask. |
| Who is the seer of RV 1.1, and how was that attribution established? | 1 evidence item. The rail on the passage page answers it far better. |
| What does VS 1.1 say? | `VS 1.1` is not a citation this corpus recognises. The Yajurvedic prefix is `VSM`. |

**The pattern worth writing into the design.** Ask's retrieval is entity-driven and
passage-driven. A question that names a registered entity or a canonical citation retrieves
well. A question that names a category ("metals", "rivers", "rites") retrieves nothing, even
where a dedicated insight endpoint answers it completely. The suggestion list must therefore
never be generated from the insight catalogue, and the empty state for a category question
should point at the insight surface by name.

### 6.4 Progress stages

Four stages. The proxy ceiling clears a 330 second worst case, so this copy has to stay
legible for minutes and must not imply streaming.

| Stage | Label | Note under the label |
|---|---|---|
| 1 | Reading the question | Working out what kind of question this is |
| 2 | Resolving the names | Matching every name against the registered entities |
| 3 | Retrieving evidence | Running the selected channels over the graph |
| 4 | Writing from the evidence | Composing prose from the retrieved items only |

**The honesty line under the stages, always shown:**

> The response is not streamed, so these stages are timed estimates and not live telemetry.
> A long wait is the synthesis step, not a stalled page.

### 6.5 Answer page labels

| Element | Label | Supporting line |
|---|---|---|
| The prose | **Answer** | none |
| Support, strong | **Strong support** | Several retrieved items carry the claims in this answer. |
| Support, moderate | **Moderate support** | The claims are cited, on a narrow evidence base. |
| Support, limited | **Limited support** | Cited, and thin. Read the evidence before relying on it. |
| Support, none | **Insufficient evidence** | The graph's evidence does not settle this. That is about this build's coverage, not about the Vedic corpus. |
| Citation marker | inline numeric marker | Opening it reveals the retrieved item, its Sanskrit, its translation and its canonical citation. |
| Evidence list | **What was retrieved** | Every item the model was allowed to see. Nothing else was available to it. |
| Channels that ran and returned nothing | **Searched and empty** | These channels ran and returned nothing. They were searched; they are not unexamined. |
| Names that did not resolve | **Not recognised as an entity** | These names matched no registered entity, so no entity channel ran for them. |
| Interpretation present | **Contains interpretation** | Part of this answer rests on a recorded reading rather than on a textual statement. Interpretation is labelled in place. |
| Follow-up questions | **Ask next** | none |
| Scope caveats | **Scope of this answer** | none |
| Backend not configured | **Ask is not configured** | No synthesis backend is set for this install. Browsing, search, the graph, cross-Veda comparison and recitation are unaffected. |
| Backend unreachable | **The synthesis backend could not be reached** | No answer was composed. The evidence retrieved for this question is listed below and is unaffected. |

The last row is not hypothetical. It is the state the live install returns today, and the
evidence list beneath it is the reason the page still has value in that state.

### 6.6 What this is not

Placed under the answer, at the foot of every result, and on the empty state.

> **What this is not.**
> A citation is evidence that this graph records something. It is not evidence that the
> tradition asserts it, and it is not a second opinion from a scholar. Nothing in this graph
> is human-reviewed. The model is never given audio. Where retrieval found an interpretation
> rather than a textual statement, the answer says so. An answer here is a reading of
> retrieved evidence, and the evidence is listed so you can disagree with the reading.

---

## 7. About Himanshu

Route `/about`. Single column, reading measure, no photograph required, no statistics band.

**Page title:** About this project

**Opening:**

> VedAnvaya was built by one person, Himanshu Mohanty, over a corpus that has been read for
> three thousand years and digitised for about thirty.

**Body:**

> I am a developer. I work on backend systems, on machine learning and natural language
> processing, and on the kind of generative AI that is currently being asked to answer
> questions it has no business answering. My training is in computer science engineering. My
> interest in the Vedas is older than my interest in any of that, and it is the ordinary
> kind: I wanted to read them, and I kept running into the same wall.
>
> The wall is not that the texts are hard, though they are. It is that almost every digital
> route into them quietly loses the thing that makes them legible. A site gives you a
> translation with no Sanskrit. Another gives you Sanskrit with no indication of which
> edition. A third gives you a confident summary of what a hymn means and no way to find out
> who thought so. By the time you have an answer you have no idea what you are holding.
>
> So this started as a reading tool for myself and became an argument about evidence.
>
> **Why a graph.** These four collections are not four books that happen to sit on the same
> shelf. A Samavedic verse is very often a Rigvedic verse, rearranged for singing. A
> Yajurvedic formula recurs across collections with a word changed. A deity is named in one
> place and assigned in another, and those are different facts about the same word. A
> relational table forces you to pick one of those relationships as the primary one. A graph
> does not. It lets a verse be a member of its hymn, a reuse of another verse, an instance of
> a formula family, a container of named entities, and the subject of a traditional
> ascription, all at once, with each of those edges carrying its own provenance. That is not
> a technical preference. It is the only shape that does not force a false choice.
>
> **Why evidence.** The moment you connect four corpora, you can produce a number for almost
> anything, and almost every one of those numbers is misleading if you do not say how it was
> made. Take one from this build. Indra is named in roughly 218 of every thousand Rigvedic
> verses and roughly 220 of every thousand Samavedic ones. That looks like a finding about
> the two collections. It is mostly a finding about the Samaveda being drawn from the
> Rigveda. Or take the traditional ascriptions: the apparatus that assigns a deity to a hymn
> exists for the Rigveda and does not exist for the other three. A chart of ascriptions across
> four collections therefore shows three empty columns, and a reader will see three silent
> corpora when what is actually missing is three sets of index. Every number in this product
> carries the layer that produced it, the corpora that layer reaches, and what it does not
> establish, because that is the difference between a research tool and a generator of
> plausible facts.
>
> **Why Sanskrit and why recitation.** The Vedas were transmitted by voice for longer than
> they have been written, and the transmission preserved pitch accent with a precision that
> written editions struggle to represent. That is not a piece of colour. It is the reason the
> text survived intact, and it is why the accented Sanskrit is the primary object on every
> page here and the translation sits beneath it. 16,834 verses carry their own recitation,
> and every one of those mappings was verified by comparing the text the source says the
> recording recites against this corpus's own text. The Samaveda, the one collection defined
> by how it is sung, has none, because none has been published in a form that maps to
> individual verses. That empty row is the most honest thing on the site.
>
> **Why this is not an answer machine.** There is a natural-language interface here, and it
> is deliberately the least prominent thing in the product. It runs retrieval first, shows the
> model only what retrieval returned, cites every factual sentence into the graph, and
> refuses rather than guesses. In sixty graded questions it refused sixteen. I count that as
> the feature. A system that answers everything about the Vedas is not knowledgeable, it is
> unfalsifiable, and there is already enough of that.
>
> Nothing in this graph has been reviewed by a human expert. The strongest review state
> anywhere in it is that a model re-read an edge and accepted it, and that covers 613 edges out
> of everything here. It says so on the pages where it matters. If a Vedicist reads a claim
> here and finds it wrong, the provenance chain is complete enough that the error can be
> traced to the layer that produced it. That is the standard I built to.

**Project principles.** Presented as a list, drawn from how the product actually behaves.

> **Text is immutable. Metadata is provenanced.** A verse is never edited to fit a pipeline.
> Everything said about it carries where it came from.
>
> **Similarity is never identity.** `asvah` and `asvah` share an ASCII fold and stay two
> entities. The only unions are six evidenced entries in a reviewed registry.
>
> **An assignment is not a mention.** What the traditional index assigns to a hymn and what
> the Sanskrit of a verse actually says are recorded separately, counted separately, and
> never summed.
>
> **Ambiguity fails closed.** A word that could mean two entities produces nothing. 711
> annotated tokens were left unresolved rather than guessed, including every occurrence of
> Sarasvati, whose stem the annotation shares with a masculine name.
>
> **No substring matching, anywhere.** Matching begins from an annotated token and its lemma
> identifier, so sandhi and compounding cannot manufacture a false positive. The failure mode
> is structurally absent rather than filtered afterwards.
>
> **Model output is never canonical.** A language model can propose a candidate for a human
> to review. It cannot write an alias and it cannot write an edge.
>
> **A zero must say whose zero it is.** Not built, insufficient evidence and partial are three
> different states and none of them is a count of nothing.
>
> **Coverage may be incomplete. A mapping may not be wrong.** No recording was ever attached
> to a verse to improve a percentage. 495 Atharvavedic mappings were refused because the
> recited text did not match.
>
> **Rights attach to the file, not the website.** One repository supplied three collections
> under three different licences, and treating the site as the unit would have been wrong
> about two of them.

**Closing:**

> If you find something here that is wrong, it is a defect and I want to know. If you find
> something here that is missing, check the limits page first: it may be missing on purpose,
> and if so it will say why.

**Blocker, named rather than worked around.** There is no GitHub handle, no repository URL
and no contact address anywhere in this repository. `git remote -v` is empty and `README.md`
links to no personal account. The only contact string present is the commit author email in
`git log`, which is a personal address and must not be published without Himanshu's explicit
say-so. **This page therefore ships with no external links.** If a handle or a contact route
is wanted, it has to be supplied; it will not be inferred.

---

## 8. Sources and acknowledgements

Route `/sources`. Checked against `docs/FOUR_VEDA_RIGHTS_MATRIX.md`,
`docs/FOUR_VEDA_AUDIO_SOURCE_INVENTORY.md`, and the live reader payloads for one verse of
each collection, which is where the witness ids, source ids and rights statuses below come
from.

**Page title:** Sources and rights

**Opening:**

> VedAnvaya integrates and normalizes material published by scholarly projects, libraries and
> volunteer transcribers. Nothing here is original text. Every layer below names the artifact
> it came from and the terms that artifact carries, because a licence attaches to a file and
> not to the website that hosts it. That rule is not a formality: one repository supplied
> three of these collections under three different sets of terms.

### 8.1 Sanskrit text

| Collection | Witness | Published by | Terms | Script |
|---|---|---|---|---|
| Rigveda, primary | `GRETIL.RV.AUFRECHT` | GRETIL, Göttingen | CC BY-NC-SA 4.0 | Romanised, accented |
| Rigveda, parallel witness | `VEDAWEB.AUFRECHT` | VedaWeb, University of Cologne | Recorded per text version. The container file mixes licence layers, so its file-level status is deliberately recorded as unknown. | Romanised, accented |
| Atharvaveda Saunaka | `GRETIL.AVS.SAUNAKA.ACCENTED` | GRETIL | Reference only. See the note below. | Romanised, accented |
| Yajurveda, Vajasaneyi Madhyandina | `WIKISOURCE_SA.YV.VSM.ACCENTED` | Sanskrit Wikisource | CC BY-SA | Devanagari, accented |
| Samaveda, Kauthuma arcika | `WIKISOURCE_SA.SV.KAU.ARCIKA_MULA` | Sanskrit Wikisource | CC BY-SA | Devanagari |

**The Atharvavedic note, written in full because it is the one a reader most deserves:**

> The Atharvavedic Sanskrit is held as a working private corpus. Its digital lineage runs back
> to a modern printed edition that is still in copyright, and the file we read declares itself
> reference-only. It is displayed here for reading and it is not offered for redistribution,
> bulk export or reuse. The clean route to a redistributable Saunaka text is a fresh
> transcription from the 1856 Roth and Whitney edition, which is public domain by age. That
> work has not been done.

### 8.2 Translations

| Collection | Translator | Edition | Terms | Coverage |
|---|---|---|---|---|
| Rigveda | Ralph T. H. Griffith | The Hymns of the Rigveda, second edition, 1896 | Public domain | 10,502 of 10,552 |
| Atharvaveda | William Dwight Whitney, revised and edited by Charles Rockwell Lanman | Atharva-Veda Samhita, Harvard Oriental Series 7 and 8, 1905 | Public domain | 4,878 of 5,839 |
| Yajurveda | Ralph T. H. Griffith | The Texts of the White Yajurveda, Benares, 1899 | Public domain | 1,903 of 1,975 |
| Samaveda | none | | | **0 of 1,844** |

> No gap in any translation layer is ever filled from a second translator. The Samavedic zero
> is measured and real: the only complete Griffith Samaveda in circulation follows a different
> recension from the one held here, and aligning it would be silently wrong rather than
> approximately right.

### 8.3 Traditional metadata and annotation

| Layer | Source | Terms | Reaches |
|---|---|---|---|
| Seer, deity and metre ascriptions | The digital Anukramani of Akavarapu and Bhattacharya, 2023 | Apache 2.0 | Rigveda |
| Morphosyntactic annotation | VedaWeb, University of Zurich annotation layer | CC BY 4.0 | Rigveda |

> The Zurich annotation is over a decade of hand annotation corrected against Grassmann's
> dictionary. It is what allows a named entity to be matched from a lemma rather than from a
> string, which is why this product does no substring matching anywhere.

### 8.4 Recitation

> **16,834 recordings, from VedSearch (vedsearch.org).** One recording per verse.
>
> VedSearch publishes no licence, so this layer is treated as link-only. Nothing is mirrored
> and nothing is redistributed. A recording is fetched from its source at the moment you press
> play, decoded, and streamed through this product's own route only because the source serves
> audio as base64 inside JSON, which no browser can play. Nothing is stored unless a local
> cache is deliberately built. Every player links back to the source page for the verse.
>
> The source names no reciter anywhere we reached, so no performer is credited here rather
> than one being invented.
>
> Audio carries its own rights and never inherits them from the text. That rule is why this
> layer is the most conservatively handled thing in the product, and why several recitation
> collections that are technically downloadable are not used at all: a file returning a
> successful response is not a grant of permission.

### 8.5 Acknowledgements

> This product exists because other people did the slow work first, and most of them were not
> paid for it: the GRETIL project at Göttingen, the VedaWeb project at Cologne and the
> University of Zurich annotators behind it, the Sanskrit Wikisource transcribers, the editors
> of the digital Anukramani, the Wikisource volunteers who typed Griffith, and VedSearch for
> publishing verse-level recitation at all.
>
> The scholarly editions underneath, Aufrecht, Whitney and Lanman, Griffith, and the printed
> witnesses behind the Wikisource transcriptions, are the actual foundation. Digitisation is
> visible; the century of editing under it is not.

### 8.6 Licensing of this product

> Text and corpus licensing and source-code licensing are separate questions and neither has
> been settled. There is no licence file in this repository yet. Until there is, treat
> everything here as available for reading and not for redistribution, and read each source's
> own terms above before reusing any of it.

---

## 9. Footer

Four columns on desktop, stacked on mobile. No newsletter, no social row, no badges.

**Column 1, the brand block.**

> **वेदान्वय VedAnvaya**
> The Vedas, connected.
>
> Four Samhitas, one recension each. Every figure on this site describes what this build
> holds, never what the Vedas contain.

**Column 2, Read.**

- Read the Vedas → `/vedas`
- Search the corpus → `/search`
- Open connections → `/connections`
- Open the graph → `/graph`
- Open the visualizations → `/visualize`

**Column 3, Understand.**

- See what is not held → `/limits`
- See the evidence → `/evidence`
- See the sources → `/sources`
- Ask a question → `/ask`

**Column 4, About.**

- About this project → `/about`
- Deities → `/devatas`
- Entities → `/entities`

**Closing line, full width, under a hairline.**

> Built by Himanshu Mohanty. Text from the sources named above. Nothing here is
> human-reviewed, and the pages say so where it matters.

The closing line carries no year, no copyright symbol and no version. A copyright assertion
over material this product does not own would be the one wrong note in the whole footer.

---

## 10. Every empty, loading, error and not-found state

**The concept: the missing thread.** The brand mark is a continuous hairline. Absence is that
same hairline with a visible break in it. The break is drawn at the same weight as the line,
never in a warning colour, and never with an icon that means danger. A gap in this product is
an ordinary fact, and it is drawn as one.

The break has three widths, and they are used consistently:

| Break | Meaning | Where |
|---|---|---|
| Hairline break, narrow | The layer exists and returned nothing for this input | Empty lists, no search results, no parallels |
| Hairline break, wide | The layer was never built for this corpus | Samavedic translation, Samavedic audio, unbuilt relationship classes |
| Hairline severed, ends offset | The service or the request failed | Errors, service unavailable, 404 |

### 10.1 Loading

Skeletons, never a spinner, never a percentage. One accessible label:

> `aria-label`: Loading

For the Ask composer only, the four-stage progress model in 6.4 replaces the skeleton.

For anything that can exceed three seconds, a single line under the skeleton:

> Still reading the graph.

### 10.2 Not found, 404

Artwork: the hairline with its break, centred, wide break.

> **404**
>
> ### This thread does not run through here
>
> The identifier may be wrong, or the thing it names may sit outside the four Samhitas this
> build holds. That is a limit of this corpus and not a statement about the Vedas.

**Primary:** Search the corpus → `/search`
**Secondary:** See what is not held → `/limits`

### 10.3 Application error

> ### Something interrupted this view
>
> This page could not be rendered. No corpus data has been changed and the rest of the site is
> unaffected.

**Primary:** Try again
**Secondary:** Return home

### 10.4 The knowledge service is unreachable

> ### The corpus service is not answering
>
> The interface is ready and the knowledge service did not respond. No corpus data has been
> changed. Start the local API and reload this page.

**Secondary:** Return home

### 10.5 One request failed

> ### This view could not be loaded
>
> {message from the API}. The rest of the page is unaffected.

**Secondary:** Search the corpus

### 10.6 Empty results

| Situation | Copy |
|---|---|
| Search returned nothing | **Nothing matched "{query}"** No canonical key, citation, registered entity label, Sanskrit form or translation phrase in this corpus matched that query. The texts may still use the idea under another word. |
| Search read only some surfaces | **Some surfaces were not read.** This search read {n} of the available surfaces and stopped, because the surfaces it skipped could not have outranked what is already on this page. That is a proof, not a sample, and not a statement that the corpus lacks those matches. |
| A list is genuinely empty | **Nothing is recorded here** The layer that would fill this list ran and returned nothing for this input. That is not evidence of absence in the text. |
| A layer was never built for this corpus | **This layer was never built for the {collection}** A zero here would read as a fact about the text. It is a fact about what was ingested. |
| Evidence exists and cannot decide | **The evidence cannot settle this** Evidence was found and it does not support the claim either way. This is not a zero. |
| Partial answer | **A real answer over part of the corpus** What follows covers {scope}. It is not a statement about the four collections together. |
| No parallels for a verse | **No parallel is recorded for this verse** The parallel layer ran and found nothing at or above the accepted threshold. Near matches below the threshold are not shown, because a near match presented as a parallel is worse than no result. |
| No recording | see 5.4 | |
| No translation | see 5.5 | |
| Graph node has no neighbours | **Nothing is connected to this node** No curated relationship reaches this node. That is a property of the curation, not of the text. |
| Ask has no backend | **Ask is not configured** No synthesis backend is set for this install. Browsing, search, the graph, cross-Veda comparison and recitation are unaffected. |

**One rule binding all of these.** An empty result may never be rendered with the same
treatment as a zero figure. A zero is a measurement. An empty result is the absence of one.
If a component cannot tell which it is holding, it renders the typed status from the API and
nothing else.

---

## 11. Contextual onboarding

Three pieces of first-use copy. Each is dismissible, each remembers dismissal locally, and
none of them blocks interaction.

### 11.1 The graph, first visit

Shown once, as a panel beside the canvas, not as a modal over it.

> **Reading this graph**
>
> It is curated for reading and it is not a database browser. You are looking at one node and
> what reaches it, not at the whole corpus.
>
> **Expand one node at a time.** Expanding everything produces a picture of the layout
> algorithm, not of the corpus.
> **Select a line, not just a circle.** A relationship is the thing that carries evidence.
> Selecting one tells you what it is, how it was established, which passage carries it, and
> what it does not establish.
> **Nothing here is human-reviewed.** The strongest review state in this graph is that a model
> re-read an edge and accepted it. A tidy edge is not a verified one.

**Control:** `Got it`

### 11.2 The visualization lab, first visit

> **Reading these visualizations**
>
> Each one answers a single stated question, and each draws its own absence.
>
> **An empty cell is typed, not blank.** It will say whether the layer was never built, or
> evidence exists and cannot decide, or the answer covers part of the corpus.
> **Normalise before you compare.** The four collections differ in size by a factor of nearly
> six. A raw total will always rank the Rigveda first and will tell you nothing.
> **A layer that reaches one collection cannot be charted across four.** Where that is the
> case, the chart shows one column and says why, rather than three empty ones.

**Control:** `Got it`

### 11.3 Graph help, available from the canvas at any time

Opened by a `?` control. Headed `About this view`.

> **What is on screen.** One node and the nodes that reach it, bounded per relationship type
> so a hub cannot flood the canvas. Depth is capped at two.
>
> **What the colours mean.** Colour groups entity kind, and the legend chips filter. Filtering
> hides nodes from the view. It does not remove them from the evidence behind an edge.
>
> **Why this connection.** Select any line. The panel gives the relationship, the method that
> established it, the tier of trust it carries, the passage or assertion that carries it, and
> the claim it does not support.
>
> **Expanding and collapsing.** Expand this node adds that node's neighbours. Collapse this
> node removes what expanding added. Centre on this node makes it the root and reloads from
> the graph.
>
> **What is not here.** No community structure, no clustering and no centrality ranking exists
> in this graph. None was computed, so none is shown. A layout that looks like a cluster is a
> property of the force simulation.
>
> **Keyboard.** Arrow keys move the selection. Enter opens the selected item. Escape clears
> the selection and closes this panel.

---

## 12. Metadata

### 12.1 Template and defaults

```ts
export const metadata: Metadata = {
    metadataBase: new URL(siteUrl),
    title: {
        default: "VedAnvaya: the Vedas, connected",
        template: "%s | VedAnvaya",
    },
    description:
        "Read the four Vedic Samhitas as one connected corpus. Accented Sanskrit, recitation, translation where one exists, deities, seers and shared wording, with the evidence and the limits attached to every figure.",
    applicationName: "VedAnvaya",
    authors: [{ name: "Himanshu Mohanty" }],
};
```

The description is 42 words and states the object, the surfaces and the discipline, in that
order. It contains no adjective that cannot be checked.

### 12.2 Per-route titles

Titles are the object, not a sales line. The template supplies the brand.

| Route | Title |
|---|---|
| `/` | (uses the default, no template) |
| `/ask` | Ask VedAnvaya |
| `/vedas` | The four Samhitas |
| `/vedas/[veda]` | `{Collection name}` |
| `/passage/[key]` | `{canonical citation}` |
| `/reuse/[key]` | Shared wording at `{canonical citation}` |
| `/search` | Search the corpus |
| `/explore` | Ways into the corpus |
| `/explore/human-concerns` | Human concerns |
| `/devatas` | Deities |
| `/devatas/[id]` | `{deity name}` |
| `/entities` | Entities |
| `/entities/[type]` | `{type name}` |
| `/entities/[type]/[id]` | `{entity name}` |
| `/rituals` | Modelled rites |
| `/material-culture` | Material culture |
| `/formulas` | Formula families |
| `/connections` | Across the four collections |
| `/graph` | The knowledge graph |
| `/visualize` | Visualizations |
| `/evidence` | Evidence and interpretation |
| `/limits` | What is not held |
| `/sources` | Sources and rights |
| `/about` | About this project |

### 12.3 OpenGraph, homepage

```
og:type        website
og:site_name   VedAnvaya
og:title       VedAnvaya: the Vedas, connected
og:description Four Samhitas, one recension each, read as one corpus. 20,210 verses, 16,834
               recitations, and the evidence behind every connection. Where a layer was never
               built, it says so instead of showing a zero.
og:image       /og/home.png
og:image:alt   The VedAnvaya wordmark in Devanagari and roman over a hairline that breaks
               once and continues.
twitter:card   summary_large_image
```

The description is 41 words. The third sentence is the one doing the work and it must not be
cut for length: it is the only thing in the card that distinguishes this product from a
search index.

### 12.4 OpenGraph, a passage page

Generated per passage, from the reader payload.

```
og:type        article
og:site_name   VedAnvaya
og:title       {canonical_citation}, {work_display_label}
               e.g. "RV 1.1.1, Rigveda Samhita"
og:description {first translation, trimmed to 160 characters at a word boundary}
               e.g. "I laud Agni, the chosen Priest, God, minister of sacrifice, The Hotar,
               lavishest of wealth. Translated by Ralph T. H. Griffith, 1896."
og:image       /og/passage?key={canonical_key}
og:image:alt   {canonical_citation} in {Romanised Sanskrit | Devanagari}, with its collection
               and its translator.
twitter:card   summary_large_image
```

**Two rules for the passage card, both of which are honesty rules rather than style rules.**

1. **Where no translation exists, the description must not fall back to the Sanskrit as
   though it were a gloss.** It uses the typed absence instead:
   `No translation is released for the Samaveda. This verse is held in Devanagari, from the
   Kauthuma arcika.`
2. **The translator is always named in the description.** A translation shared without its
   translator is the exact failure this product exists to correct, and a social card is the
   place where that loss is most likely and least noticed.

---

## 13. Open questions carried out of this document

1. **No contact route exists.** No GitHub handle, no repository URL, no contact address is
   present in the repository. The About page ships with no external links until one is
   supplied. Do not infer one from the commit author email.
2. **The visualization lab's lead chart is nominated, not chosen.** Section S7 recommends
   translation and recitation coverage as the homepage's full-bleed visual. Agent 4 owns the
   lab and may have a stronger candidate. The section spec holds either way.
3. **`Visualize` as a nav label is American spelling against British spelling elsewhere in
   the product** ("normalised", "romanised", "neighbourhood"). The brief fixes the label. The
   inconsistency is real and should be settled once, across every surface, before Phase 2
   writes the token layer. Recommendation: keep `Visualize` as the label, because it is the
   brand-side decision, and keep the British forms in body copy, because the API's own caveat
   text uses them and that text is rendered verbatim.
4. **Ask retrieves entities, not categories.** Section 6.3 documents this with evidence. If a
   category channel is ever added, the suggestion list should be revisited, and the rejected
   questions in 6.3 are the regression set to test it against.
