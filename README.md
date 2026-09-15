# VedAnvaya

**The Vedas, connected.** VedAnvaya is a reading and research interface for the four Vedic
Samhitas, with the evidence and the limits attached to every answer. Read verse by verse with
recitation audio, explore deities and seers as a graph, trace wording reused across Vedas,
and ask questions in English that are answered only from what the graph can actually support.

> Text is immutable. Metadata is provenanced. Deterministic facts are separated from
> interpretation. LLM output never becomes canonical source data.

**Version 1.0.0 — Product V1, for local use.** Scope, coverage and limitations are stated
in [`PRODUCT_V1_SCOPE.md`](PRODUCT_V1_SCOPE.md). Read that before treating any count here
as a statement about "the Vedas": the corpus is four Saṃhitās in one recension each, and
three of the four are partial in ways their traditional names do not reveal.

---

## Quick start

You need **Python 3.12+**, [**uv**](https://docs.astral.sh/uv/), **Node 20+**, **pnpm**, and
a **Neo4j** holding the built graph.

```powershell
uv sync --extra dev                 # Python environment
cd frontend; pnpm install; cd ..    # frontend dependencies
copy .env.example .env              # then set NEO4J_PASSWORD

powershell -ExecutionPolicy Bypass -File scripts\doctor.ps1          # check everything
powershell -ExecutionPolicy Bypass -File scripts\start-product.ps1   # run it
```

Then open **<http://localhost:3000>**. The API is on <http://127.0.0.1:8000>, with
interactive docs at `/docs`. Stop it with `scripts\stop-product.ps1`.

`doctor.ps1` checks the Python environment, the frontend install, Neo4j connectivity *and
whether the corpus is actually loaded*, the LLM configuration, the audio catalog and the
ports — and names whichever one is wrong. It never prints a secret value; where a
credential matters it reports only that it is set and how long it is.

### Starting without everything

The product degrades rather than failing. **No LLM key** — browsing, search, the graph,
cross-Veda comparison and audio all work, and Ask VedAnvaya reports `NOT_CONFIGURED`
instead of taking the product down. **No audio catalog** — the reader omits the player and
nothing else changes. **Neo4j down** — the API still starts and answers `/health`, and
knowledge routes return 503 with a body that names no hostname.

Neo4j itself is never started or migrated by these scripts. It is managed outside this
repository (see [`infra/docker-compose.neo4j.yml`](infra/docker-compose.neo4j.yml)) and the
graph is treated as frozen.

---

## What you get

| Surface | What it does |
|---|---|
| **Reader** | Any verse of the four Saṃhitās, with accented Sanskrit, alternate witnesses, translation where one exists, and its own recitation audio |
| **Structure browser** | Navigate each Veda's native hierarchy — maṇḍala/sūkta, kāṇḍa/sūkta, adhyāya, Samavedic collections |
| **Deities and entities** | Profiles for deities, seers, rituals, conditions, places, substances and more, each with graded evidence |
| **Interactive graph** | Cytoscape neighbourhoods with a *Why* panel that explains any edge from its stored evidence |
| **Cross-Veda** | Wording that recurs across Vedas, and formula families with their occurrences |
| **Search** | One ladder across Sanskrit text, translations, dictionary headwords and entity names |
| **Ask VedAnvaya** | Evidence-grounded question answering: retrieval first, every claim cited, `INSUFFICIENT_EVIDENCE` instead of a confident guess |

### The corpus

Four Saṃhitās, one recension each: **Rigveda Śākala** (10,552 mantras), **Samaveda Kauthuma
ārcika** (1,844 — the gāna corpus is *not* held), **Śukla Yajurveda Vājasaneyi-Mādhyandina**
(1,975), **Atharvaveda Śaunaka** (5,839). No separate Brāhmaṇa, Āraṇyaka or Upaniṣad corpus is
included. The Samaveda's `ARANYA` section is a structural division of the modeled Kauthuma Ārcika,
not an independent Āraṇyaka corpus. The graph is
**108,779 nodes / 265,295 relationships**, and it is frozen.

### Absence means something specific

This is the discipline the whole product is built around. `NOT_BUILT` means a layer does
not exist here and the silence is ours. `INSUFFICIENT_EVIDENCE` means evidence exists and
cannot support the claim — it is **not** a zero. `PARTIAL` means a real answer over part of
the corpus. An empty list that claimed `SUPPORTED` raises rather than renders.

---

## Recitation audio

**16,834 recordings, one per verse**, from [VedSearch](https://vedsearch.org/): Rigveda
10,402 of 10,552 · Atharvaveda 4,680 of 5,839 · Yajurveda 1,752 of 1,975 · **Samaveda 0**
(none is published anywhere — see the scope document).

Audio is a **product content layer**, not knowledge. It lives in
`data/product/audio_catalog.jsonl` keyed by canonical passage identity, entirely outside the
frozen graph and ontology.

**Every mapping is verified, not assumed.** A record exists only when the coordinate
transform places our key in the source's numbering *and* the text the source says that
recording recites matches this corpus's own text. That matters concretely: VedSearch numbers
Rigvedic Mandala 8 in Griffith's order, so a key-for-key mapping would attach the wrong
recitation to 55 hymns. The transform corrects it and the text check proves it — 0 text
mismatches across 10,402 Rigvedic recordings. Where the text does not match, the mapping is
**refused** and recorded as a gap.

```bash
# Rebuild the catalog (harvest once, then align offline against the graph)
python scripts/audio/harvest_vedsearch.py
python scripts/audio/discover_vedsearch.py --verify-audio 30

# 17 checks against the live graph: dangling keys, wrong Veda, wrong scope, unverified EXACT
python scripts/audio/validate_catalog.py

# Independent confirmation: ask each audio file what IT recites and compare with our text
python scripts/audio/audit_mappings.py

# Optional: pre-download a Veda for offline playback (gitignored, ~45 KB per verse)
python scripts/audio/cache_audio.py --veda RV
```

The source serves audio as base64 inside JSON, which no browser can play, so the API's own
streaming route decodes it and serves real bytes with HTTP Range support. It is addressed by
catalog id and takes **no URL parameter**, so it cannot be used as an open proxy. Nothing is
stored unless the cache tool is run.

---

## Configuring Ask VedAnvaya

The LLM provider is an **environment choice, with no code change**. Set two variables in
`.env`:

```bash
VEDAGRAPH_LLM_PROVIDER=gemini     # or openai, anthropic, groq, openrouter, xai, openai_compatible
VEDAGRAPH_LLM_MODEL=gemini-2.5-flash
VEDAGRAPH_LLM_API_KEY=...
```

`openai_compatible` additionally needs `VEDAGRAPH_LLM_BASE_URL`, which covers any
OpenAI-shaped endpoint. Installing the adapters: `uv sync --extra ask`. Gemini needs no
vendor SDK — its adapter speaks the public REST contract over `httpx`. No credential is ever
returned by the API or written to a log. See `.env.example` for every variable and which are
optional.

**What a citation means.** Retrieval runs first and the model sees only what retrieval
found, so every factual claim carries a citation into the graph and an unanswerable question
returns `INSUFFICIENT_EVIDENCE` rather than a confident denial. A citation is evidence that
*the graph records something*, not that the tradition asserts it. Final benchmark over 60
questions: 36 supported-correct, 8 partial, 16 correctly refused, **0 misleading, 0
hallucinated**, 279 citations, 0 invented citations surviving.

---

## Development

```bash
make check          # ruff format --check, ruff check, mypy, pytest
make api            # the API alone, with reload

cd frontend
pnpm test           # unit tests
pnpm typecheck
pnpm lint
pnpm build
pnpm test:e2e       # Playwright
```

Backend tests are offline by default. Tests needing a live graph are marked `neo4j` and
**skip** rather than fail when it is absent, so the suite stays green on a machine with no
database. Checks that can only be made against a populated graph live in scripts instead:
`scripts/check_live_invariants.py` and `scripts/audio/validate_catalog.py`.

Regenerate the frontend's API types after changing a response model:

```bash
pnpm exec openapi-typescript http://127.0.0.1:8000/openapi.json -o src/lib/api-schema.ts
```

---

## Documentation

- [`PRODUCT_V1_SCOPE.md`](PRODUCT_V1_SCOPE.md) — **start here.** Corpus, coverage, audio and
  Ask semantics, and every limitation, in one place.
- [`docs/STATUS.md`](docs/STATUS.md) — build history and current state.
- [`docs/architecture/`](docs/architecture/) — data architecture, corpus schema, identity
  spec, source and rights policy.
- [`docs/decisions/`](docs/decisions/) — ADRs, including
  [ADR-014](docs/decisions/ADR-014-llm-output-is-candidate-only.md) on LLM output being
  candidate-only.

---

## How it was built

The sections below are the engineering record: how the corpus was assembled, what was
pinned, and what was deliberately left out at each stage. They describe provenance rather
than product behaviour, and the product above does not depend on reading them.

## Current implementation

Phase D0 + D1 is complete, and **the complete Ṛgveda Śākala Saṃhitā is built**: 10 Mandalas,
1,028 Suktas, 10,552 mantra occurrences, with primary and parallel Sanskrit on every mantra and
Griffith's 1896 translation aligned wherever the source supports it. See
[`docs/reports/RIGVEDA_FULL_BUILD.md`](docs/reports/RIGVEDA_FULL_BUILD.md) for the generated
build summary and [`RIGVEDA_FULL_TEXT_COMPARISON.md`](docs/reports/RIGVEDA_FULL_TEXT_COMPARISON.md)
for the primary/parallel classification. Everything from the D1 foundation still applies:

- typed work, source, rights, text, translation, assertion, citation, audio, QA, and manifest models;
- permanent canonical URNs and deterministic UUIDv5 identities;
- conservative cached HTTP retrieval into content-addressed immutable snapshots;
- adapter boundary from source snapshots to staging records;
- Unicode NFC and explicit accent-preserving/accentless/search comparison profiles;
- replaceable deterministic Devanagari → IAST transliteration wrapper;
- validated deterministic JSONL and generated JSON Schema;
- field-specific reconciliation policies that retain conflicting claims;
- cross-record QA and reproducible release manifests;
- exact source-artifact registry and policy-driven GRETIL TEI editorial selection;
- deterministic three-source discovery of all 191 Mandala 1 Suktas;
- persisted staging/assertions and a reproducible five-Sukta, 111-mantra sample;
- MediaWiki page/revision provenance and explicit translation-alignment quality;
- commit-pinned VedaWeb TEI artifacts and a per-version Sanskrit text registry;
- accent-aware comparison surfaces and a deterministic text-version comparator;
- a declared primary Sanskrit text that lives in build configuration, not in code;
- a fail-closed parser for range-scoped traditional metadata;
- **the complete Rigveda**: 1,028 Suktas / 10,552 mantras, primary (`GRETIL.RV.AUFRECHT`) and
  parallel (`VEDAWEB.AUFRECHT`) Sanskrit attached to the same passage at 100% coverage, a
  `PRIMARY_PARALLEL_TEXT_DIVERGENCE` QA policy that classifies all 10,552 pairs with zero
  structural errors, and Griffith aligned to 98.03% of mantras with the gaps left honest;
- **ten independently gated Mandala builds** composed by one `rv_full_v1.yaml`, so a broken unit
  cannot hide inside aggregate statistics;
- edition-order divergences recorded as data (`vedagraph.editions`) rather than parser conditionals
  — Griffith prints RV 8.49–8.59 at the end of his Book 8;
- reproducible (byte-identical) full-corpus rebuilds and a 50-mantra stratified lineage check.

## Deterministic knowledge layer

The Ṛgveda now carries traditional metadata as a **separate, rebuildable knowledge layer** over
the finished corpus, built from the commit-pinned digital Anukramaṇī of Akavarapu and
Bhattacharya (2023) — 1,028 rows aligned to 1,028 canonical Sūktas with zero unaligned rows,
4,577 scoped source assertions, and **31,650 deterministic `HAS_RISHI` / `HAS_DEVATA` /
`HAS_CHANDAS` edges** over 367 Ṛṣi, 214 Devatā and 34 Chandas canonical entities. Devatā coverage
is 100% of the 10,552 mantras. No LLM, embedding, or classifier is involved; the source
repository's own devatā classifier and word vectors are deliberately not ingested.

A raw string never becomes a graph entity directly:

```text
raw source label → source assertion → normalized label → reviewed registry lookup
                 → canonical entity → deterministic relationship
```

Two rules the layer will not bend. **Similarity is never identity**: `aśvaḥ` and `aśvāḥ` share an
ASCII fold and stay two entities, and the only unions are six evidenced entries in
`data/registry/anukramani_aliases.yaml`. **An assignment is not a textual mention**:
`HAS_DEVATA: agniḥ` records what the traditional index assigns, not what the Sanskrit says;
literal occurrence is a later `MENTIONS_ENTITY` phase.

```bash
# Pin the ten Anukramaṇī artifacts (once), regenerate the registries, build, and report
uv run python scripts/fetch_wsc2023_anukramani.py
uv run python scripts/build_anukramani_registries.py
uv run python scripts/build_rigveda_knowledge.py
uv run python scripts/generate_knowledge_reports.py

# Ask deterministic questions, with provenance and without a language model
uv run vedagraph knowledge stats
uv run vedagraph knowledge entities --entity-type CHANDAS
uv run vedagraph knowledge mantras VG:DEVATA:AGNIH --predicate HAS_DEVATA
```

Evidence: [`RIGVEDA_ANUKRAMANI_SOURCE.md`](docs/architecture/RIGVEDA_ANUKRAMANI_SOURCE.md),
[`RIGVEDA_DETERMINISTIC_KNOWLEDGE_BUILD.md`](docs/reports/RIGVEDA_DETERMINISTIC_KNOWLEDGE_BUILD.md),
[`RIGVEDA_METADATA_SOURCE_COMPARISON.md`](docs/reports/RIGVEDA_METADATA_SOURCE_COMPARISON.md),
[ADR-011](docs/decisions/ADR-011-deterministic-knowledge-layer.md) and
[ADR-012](docs/decisions/ADR-012-entity-resolution-is-registry-data.md).

## Deterministic lexical and cross-mantra layer

The second knowledge layer answers a different question from the first: not what the
tradition *assigns* to a mantra, but what words the mantra actually *contains*.

It is built on the University of Zurich morphosyntactic annotation (`VEDAWEB.ZURICH`,
CC BY 4.0) — over a decade of hand annotation, corrected against Grassmann's dictionary —
which is already present in the book TEI artifacts this repository had pinned and hashed
for the corpus build. Selecting it introduced no new source, licence or download.

- **164,758 annotated tokens over 10,552/10,552 mantras (100%)**, aligned by the stanza's
  own `xml:id` rather than by comparing text: 0 unaligned, 0 duplicates, 0 mismatches.
- **8,961 `MENTIONS_ENTITY` edges**, every one matched on the annotation's stable
  Grassmann-linked lemma identifier. Measured precision: **0.01%** detectable false
  positives, audited against grammatical gender, which played no part in choosing aliases.
- **256 exact mantra parallels** in 389 groups across five separately recorded
  representation levels, plus 69 reviewed near parallels — found by scoring **0.27%** of
  all 55.7 million pairs, with recall verified by brute-forcing a whole Mandala.
- **28 `HAS_COMPONENT` edges** from human-reviewed composite Devatā decompositions only.

The rules this layer will not bend:

**No substring matching, ever.** `if alias in mantra_text` is not implemented anywhere.
Matching starts from an annotated token and its lemma identifier, so sandhi, compounding
and short names cannot produce a false positive — the failure mode is structurally absent,
not filtered out afterwards.

**Fuzzy matching may only produce candidates.** It writes `LexicalAliasCandidate` records
for a human. It cannot write an alias, and it cannot write an edge.

**Ambiguity fails closed.** A lemma reaching two entities produces nothing, however
frequent. 711 tokens were deliberately left unresolved rather than guessed — including
every occurrence of Sarasvatī, whose stem the annotation shares with the masculine
Sarasvant.

**A group deity is not the set of its members.** `viśvedevāḥ` and `ādityāḥ` have their
non-decomposition recorded as a reviewed decision, not left as an oversight.

**Assignment and mention are counted separately, and rank differently.** `pavamānaḥ somaḥ`
is assigned to 1,087 mantras and mentioned in none; `mitraḥ` is assigned to 10 and
mentioned in 320. The statistics file carries a written warning that none of the three
counts means "the most used god".

```bash
make lexical
```

Evidence: [`RIGVEDA_MORPHOLOGY_SOURCE.md`](docs/architecture/RIGVEDA_MORPHOLOGY_SOURCE.md),
[`RIGVEDA_MORPHOLOGY_DECISION.md`](docs/architecture/RIGVEDA_MORPHOLOGY_DECISION.md),
[`RIGVEDA_LEXICAL_MENTION_POLICY.md`](docs/architecture/RIGVEDA_LEXICAL_MENTION_POLICY.md),
[`RIGVEDA_RISHI_STRUCTURE_FINDINGS.md`](docs/architecture/RIGVEDA_RISHI_STRUCTURE_FINDINGS.md),
[`RIGVEDA_DETERMINISTIC_LEXICAL_BUILD.md`](docs/reports/RIGVEDA_DETERMINISTIC_LEXICAL_BUILD.md),
[`RIGVEDA_LEXICAL_MENTION_REVIEW.md`](docs/reports/RIGVEDA_LEXICAL_MENTION_REVIEW.md),
[`RIGVEDA_PARALLEL_REVIEW.md`](docs/reports/RIGVEDA_PARALLEL_REVIEW.md) and
[ADR-013](docs/decisions/ADR-013-lexical-mention-is-not-traditional-assignment.md).

## Corpus-building environment

The same install as the Quick start above; this section and the CLI below concern rebuilding
the corpus from sources rather than running the product.

```bash
uv sync --extra dev
uv run vedagraph --help
```

Provide a contact email in `.env` before running repeat source retrieval, so fetches identify
themselves. Never commit `.env`.

## CLI

```bash
# Inspect provenance and ingestion restrictions
uv run vedagraph source list
uv run vedagraph source artifacts

# Fetch exactly one registered-source URL into data/raw (cached by default)
uv run vedagraph source fetch VHP https://vedicheritage.gov.in/example

# Parse a snapshot to staging without writing canonical data
uv run vedagraph ingest parse VHP path/to/snapshot.html
uv run vedagraph ingest stage --config data/builds/rv_mandala_1.yaml

# Build the only live-enabled D1 scope (two pages, no media)
uv run vedagraph corpus build --scope RV.1.1
uv run vedagraph discover rigveda --mandala 1 --config data/builds/rv_mandala_1.yaml
uv run vedagraph corpus build --config data/builds/rv_mandala_1.yaml

# Compare editions of the same mantra, and run the stratified sample
uv run vedagraph source text-versions
uv run vedagraph text compare RV.1.1.1 --versions GRETIL.RV.AUFRECHT,VEDAWEB.VNH
uv run vedagraph text compare-sample --config data/builds/rv_m1_text_comparison.yaml

# Extract reviewable scopes from traditional-metadata range strings; promotes nothing
uv run vedagraph metadata review-ranges

# Compute counts from records and show QA
uv run vedagraph corpus stats
uv run vedagraph corpus validate
uv run vedagraph corpus lineage
uv run vedagraph assertions conflicts

# Regenerate schemas
uv run vedagraph schema export

# Full Mandala 1: pin remaining Wikisource snapshots, assemble the build config,
# build, and generate the coverage/translation/build-summary reports (idempotent)
uv run python scripts/fetch_wikisource_mandala1.py
uv run python scripts/build_rv_mandala_1_full_config.py
uv run vedagraph corpus build --config data/builds/rv_mandala_1_full_v1.yaml
uv run vedagraph text compare-sample --config data/builds/rv_m1_full_text_comparison.yaml
uv run python scripts/generate_mandala1_reports.py
```

Building the whole Rigveda. Snapshot pinning is one Mandala at a time and polite (1 req/s); the
build itself is offline and reads only cached snapshots.

```bash
# One-time: pin the VedaWeb books and the Griffith pages, then write the eleven configs
uv run python scripts/fetch_vedaweb_rigveda.py
for m in 2 3 4 5 6 7 8 9 10; do uv run python scripts/fetch_wikisource_rigveda.py --mandala $m; done
uv run python scripts/build_rigveda_configs.py --all

# Stage, build and gate each Mandala in turn, then assemble; stops on the first failing gate
uv run python scripts/build_rigveda_full.py

# Inspect the result
uv run python scripts/verify_lineage.py --per-mandala 5
uv run python scripts/inspect_passages.py --citation "RV 10.129.1"
```

The pilot reuses existing verified snapshots. It does not repeatedly hit source sites during parser
development.

## Dataset architecture

```text
source → immutable raw snapshot → staging → normalization → source assertion
       → field-specific reconciliation → QA → canonical JSONL + manifest
```

Registries are versioned under `data/registry`. Raw, staged, canonical, derived, and QA artifacts
are reproducible and ignored by Git because individual assets can have different rights. See
[`DATA_ARCHITECTURE.md`](docs/architecture/DATA_ARCHITECTURE.md),
[`CORPUS_SCHEMA.md`](docs/architecture/CORPUS_SCHEMA.md), and
[`ID_SPEC.md`](docs/architecture/ID_SPEC.md).

Corpus counts always come from actual canonical `MANTRA` passage records. Website totals are
stored only as attributable assertions.

## Source and rights policy

No website is authoritative for every field, and no host-level license is assumed to cover every
file. Rights attach to a specific artifact, and where one artifact carries several editions they
attach to each version: the VedaWeb Book 1 TEI mixes CC BY 4.0 and CC BY-NC-SA 4.0 layers, so its
file-level status is deliberately `UNKNOWN` and the real terms live in
`data/registry/text_versions.yaml`, extracted from the TEI header rather than retyped.

VHP currently requires written permission for reproduction and is verification/reference-only.
The reviewed GRETIL Rigveda TEI file declares CC BY-NC-SA 4.0, but other files need independent
review. The underlying 1896 Griffith translation is public domain; its changing Wikisource
transcription still receives snapshot/revision provenance.

Read [`SOURCE_POLICY.md`](docs/architecture/SOURCE_POLICY.md),
[`RIGHTS_POLICY.md`](docs/architecture/RIGHTS_POLICY.md) and
[`VEDAWEB_RIGVEDA_SOURCES.md`](docs/architecture/VEDAWEB_RIGVEDA_SOURCES.md) before ingestion or
redistribution.

Repository source-code licensing is also undecided, so no `LICENSE` is included. Code and corpus
licensing must be selected independently.

## Which Sanskrit text is canonical

`GRETIL.RV.AUFRECHT` is the primary displayed Saṃhitā for v1. The metrically restored
van Nooten and Holland text, the Padapāṭha, and four further representations are preserved with
declared roles rather than merged or discarded. The choice is build configuration, and passage
identity cannot depend on it.

The evidence is in [`RIGVEDA_BASE_EDITION.md`](docs/architecture/RIGVEDA_BASE_EDITION.md) and
[`rv_m1_text_comparison_report.md`](docs/reports/rv_m1_text_comparison_report.md).

## Testing and quality

All default tests are offline. Reduced fixtures model source markup; live checks are marked `live`
and excluded from CI.

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest -m "not live"
# or
make check
```

CI performs the same locked, secret-free checks and never crawls sources.

Progress and blockers are maintained in [`docs/STATUS.md`](docs/STATUS.md); the generated build
summaries are [`RIGVEDA_FULL_BUILD.md`](docs/reports/RIGVEDA_FULL_BUILD.md),
[`RIGVEDA_DETERMINISTIC_KNOWLEDGE_BUILD.md`](docs/reports/RIGVEDA_DETERMINISTIC_KNOWLEDGE_BUILD.md)
and [`RIGVEDA_DETERMINISTIC_LEXICAL_BUILD.md`](docs/reports/RIGVEDA_DETERMINISTIC_LEXICAL_BUILD.md).
