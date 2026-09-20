# Building the corpus

The engineering record: how the four Saṃhitās were assembled from pinned sources, what each
knowledge layer is built from, what was deliberately left out at each stage, and the CLI that
does the work.

This document describes **provenance and rebuild**, not product behaviour. Nothing in
[`README.md`](../README.md) depends on reading it, and nothing here is needed to *run*
VedAnvaya — for that, see [`LOCAL_SETUP.md`](../LOCAL_SETUP.md).

> **The graph is frozen.** These commands describe how it was produced. Running them against
> a populated store is not part of ordinary local setup, and the product never migrates Neo4j
> itself.

---

## Contents

- [Corpus-building environment](#corpus-building-environment)
- [Dataset architecture](#dataset-architecture)
- [The Rigveda build](#the-rigveda-build)
- [The deterministic knowledge layer](#the-deterministic-knowledge-layer)
- [The deterministic lexical and cross-mantra layer](#the-deterministic-lexical-and-cross-mantra-layer)
- [Which Sanskrit text is canonical](#which-sanskrit-text-is-canonical)
- [The recitation catalogue](#the-recitation-catalogue)
- [Configuring Ask VedAnvaya](#configuring-ask-vedanvaya)
- [Source and rights policy](#source-and-rights-policy)
- [The CLI](#the-cli)
- [Development, testing and quality](#development-testing-and-quality)

---

## Corpus-building environment

The same install as the product's quick start; this section and the CLI below concern
rebuilding the corpus from sources rather than running the product.

```bash
uv sync --extra dev
uv run vedagraph --help
```

Provide a contact email in `.env` before running repeat source retrieval, so fetches identify
themselves. Never commit `.env`.

---

## Dataset architecture

```text
source → immutable raw snapshot → staging → normalization → source assertion
       → field-specific reconciliation → QA → canonical JSONL + manifest
```

Registries are versioned under [`data/registry/`](../data/registry/). Raw, staged, canonical,
derived and QA artifacts are reproducible and ignored by Git, because individual assets can
carry different rights. See [`DATA_ARCHITECTURE.md`](architecture/DATA_ARCHITECTURE.md),
[`CORPUS_SCHEMA.md`](architecture/CORPUS_SCHEMA.md) and [`ID_SPEC.md`](architecture/ID_SPEC.md).

Corpus counts always come from actual canonical `MANTRA` passage records. Website totals are
stored only as attributable assertions.

The foundation everything else sits on:

- typed work, source, rights, text, translation, assertion, citation, audio, QA and manifest
  models;
- permanent canonical URNs and deterministic UUIDv5 identities;
- conservative cached HTTP retrieval into content-addressed immutable snapshots;
- an adapter boundary from source snapshots to staging records;
- Unicode NFC and explicit accent-preserving / accentless / search comparison profiles;
- a replaceable deterministic Devanāgarī → IAST transliteration wrapper;
- validated deterministic JSONL and generated JSON Schema;
- field-specific reconciliation policies that retain conflicting claims;
- cross-record QA and reproducible release manifests;
- an exact source-artifact registry and policy-driven GRETIL TEI editorial selection;
- MediaWiki page/revision provenance and explicit translation-alignment quality;
- commit-pinned VedaWeb TEI artifacts and a per-version Sanskrit text registry;
- accent-aware comparison surfaces and a deterministic text-version comparator;
- a declared primary Sanskrit text that lives in build configuration, not in code;
- a fail-closed parser for range-scoped traditional metadata.

---

## The Rigveda build

The complete Ṛgveda Śākala Saṃhitā: 10 maṇḍalas, 1,028 sūktas, 10,552 mantra occurrences,
with primary and parallel Sanskrit on every mantra and Griffith's 1896 translation aligned
wherever the source supports it.

- primary (`GRETIL.RV.AUFRECHT`) and parallel (`VEDAWEB.AUFRECHT`) Sanskrit attached to the
  same passage at 100% coverage;
- a `PRIMARY_PARALLEL_TEXT_DIVERGENCE` QA policy that classifies all 10,552 pairs with zero
  structural errors;
- Griffith aligned to 98.03% of mantras, with the gaps left honest;
- **ten independently gated maṇḍala builds** composed by one `rv_full_v1.yaml`, so a broken
  unit cannot hide inside aggregate statistics;
- edition-order divergences recorded as data (`vedagraph.editions`) rather than as parser
  conditionals — Griffith prints RV 8.49–8.59 at the end of his Book 8;
- reproducible (byte-identical) full-corpus rebuilds and a 50-mantra stratified lineage check.

Snapshot pinning is one maṇḍala at a time and polite (1 req/s); the build itself is offline
and reads only cached snapshots.

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

Generated build summaries:
[`RIGVEDA_FULL_BUILD.md`](reports/RIGVEDA_FULL_BUILD.md) and
[`RIGVEDA_FULL_TEXT_COMPARISON.md`](reports/RIGVEDA_FULL_TEXT_COMPARISON.md).

The other three corpora are built by the same machinery under their own work configurations;
see [`ADR-018`](decisions/ADR-018-per-work-build-configuration.md) and the pilots in
[`docs/pilots/`](pilots/).

---

## The deterministic knowledge layer

The Ṛgveda carries traditional metadata as a **separate, rebuildable knowledge layer** over
the finished corpus, built from the commit-pinned digital Anukramaṇī of Akavarapu and
Bhattacharya (2023) — 1,028 rows aligned to 1,028 canonical sūktas with zero unaligned rows,
4,577 scoped source assertions, and **31,650 deterministic `HAS_RISHI` / `HAS_DEVATA` /
`HAS_CHANDAS` edges** over 367 Ṛṣi, 214 Devatā and 34 Chandas canonical entities. Devatā
coverage is 100% of the 10,552 mantras. No LLM, embedding or classifier is involved; the
source repository's own devatā classifier and word vectors are deliberately not ingested.

A raw string never becomes a graph entity directly:

```text
raw source label → source assertion → normalized label → reviewed registry lookup
                 → canonical entity → deterministic relationship
```

Two rules the layer will not bend. **Similarity is never identity**: `aśvaḥ` and `aśvāḥ`
share an ASCII fold and stay two entities, and the only unions are six evidenced entries in
[`data/registry/anukramani_aliases.yaml`](../data/registry/anukramani_aliases.yaml). **An
assignment is not a textual mention**: `HAS_DEVATA: agniḥ` records what the traditional index
assigns, not what the Sanskrit says; literal occurrence is the later `MENTIONS_ENTITY` phase.

```bash
# Pin the ten Anukramani artifacts (once), regenerate the registries, build, and report
uv run python scripts/fetch_wsc2023_anukramani.py
uv run python scripts/build_anukramani_registries.py
uv run python scripts/build_rigveda_knowledge.py
uv run python scripts/generate_knowledge_reports.py

# Ask deterministic questions, with provenance and without a language model
uv run vedagraph knowledge stats
uv run vedagraph knowledge entities --entity-type CHANDAS
uv run vedagraph knowledge mantras VG:DEVATA:AGNIH --predicate HAS_DEVATA
```

Evidence: [`RIGVEDA_ANUKRAMANI_SOURCE.md`](architecture/RIGVEDA_ANUKRAMANI_SOURCE.md),
[`RIGVEDA_DETERMINISTIC_KNOWLEDGE_BUILD.md`](reports/RIGVEDA_DETERMINISTIC_KNOWLEDGE_BUILD.md),
[`RIGVEDA_METADATA_SOURCE_COMPARISON.md`](reports/RIGVEDA_METADATA_SOURCE_COMPARISON.md),
[ADR-011](decisions/ADR-011-deterministic-knowledge-layer.md) and
[ADR-012](decisions/ADR-012-entity-resolution-is-registry-data.md).

---

## The deterministic lexical and cross-mantra layer

The second knowledge layer answers a different question from the first: not what the
tradition *assigns* to a mantra, but what words the mantra actually *contains*.

It is built on the University of Zurich morphosyntactic annotation (`VEDAWEB.ZURICH`,
CC BY 4.0) — over a decade of hand annotation, corrected against Grassmann's dictionary —
which is already present in the book TEI artifacts this repository had pinned and hashed for
the corpus build. Selecting it introduced no new source, licence or download.

- **164,758 annotated tokens over 10,552 / 10,552 mantras (100%)**, aligned by the stanza's
  own `xml:id` rather than by comparing text: 0 unaligned, 0 duplicates, 0 mismatches.
- **8,961 `MENTIONS_ENTITY` edges**, every one matched on the annotation's stable
  Grassmann-linked lemma identifier. Measured precision: **0.01%** detectable false positives,
  audited against grammatical gender, which played no part in choosing aliases.
- **256 exact mantra parallels** in 389 groups across five separately recorded representation
  levels, plus 69 reviewed near parallels — found by scoring **0.27%** of all 55.7 million
  pairs, with recall verified by brute-forcing a whole maṇḍala.
- **28 `HAS_COMPONENT` edges** from human-reviewed composite Devatā decompositions only.

The rules this layer will not bend:

**No substring matching, ever.** `if alias in mantra_text` is not implemented anywhere.
Matching starts from an annotated token and its lemma identifier, so sandhi, compounding and
short names cannot produce a false positive — the failure mode is structurally absent, not
filtered out afterwards.

**Fuzzy matching may only produce candidates.** It writes `LexicalAliasCandidate` records for
a human. It cannot write an alias, and it cannot write an edge.

**Ambiguity fails closed.** A lemma reaching two entities produces nothing, however frequent.
711 tokens were deliberately left unresolved rather than guessed — including every occurrence
of Sarasvatī, whose stem the annotation shares with the masculine Sarasvant.

**A group deity is not the set of its members.** `viśvedevāḥ` and `ādityāḥ` have their
non-decomposition recorded as a reviewed decision, not left as an oversight.

**Assignment and mention are counted separately, and rank differently.** `pavamānaḥ somaḥ` is
assigned to 1,087 mantras and mentioned in none; `mitraḥ` is assigned to 10 and mentioned in
320. The statistics file carries a written warning that none of the three counts means "the
most used god".

```bash
make lexical
```

Evidence: [`RIGVEDA_MORPHOLOGY_SOURCE.md`](architecture/RIGVEDA_MORPHOLOGY_SOURCE.md),
[`RIGVEDA_MORPHOLOGY_DECISION.md`](architecture/RIGVEDA_MORPHOLOGY_DECISION.md),
[`RIGVEDA_LEXICAL_MENTION_POLICY.md`](architecture/RIGVEDA_LEXICAL_MENTION_POLICY.md),
[`RIGVEDA_RISHI_STRUCTURE_FINDINGS.md`](architecture/RIGVEDA_RISHI_STRUCTURE_FINDINGS.md),
[`RIGVEDA_DETERMINISTIC_LEXICAL_BUILD.md`](reports/RIGVEDA_DETERMINISTIC_LEXICAL_BUILD.md),
[`RIGVEDA_LEXICAL_MENTION_REVIEW.md`](reports/RIGVEDA_LEXICAL_MENTION_REVIEW.md),
[`RIGVEDA_PARALLEL_REVIEW.md`](reports/RIGVEDA_PARALLEL_REVIEW.md) and
[ADR-013](decisions/ADR-013-lexical-mention-is-not-traditional-assignment.md).

---

## Which Sanskrit text is canonical

`GRETIL.RV.AUFRECHT` is the primary displayed Saṃhitā for the Rigveda. The metrically
restored van Nooten and Holland text, the Padapāṭha and four further representations are
preserved with declared roles rather than merged or discarded. The choice is build
configuration, and passage identity cannot depend on it.

The evidence is in [`RIGVEDA_BASE_EDITION.md`](architecture/RIGVEDA_BASE_EDITION.md) and
[`rv_m1_text_comparison_report.md`](reports/rv_m1_text_comparison_report.md).

---

## The recitation catalogue

Audio is a **product content layer**, not knowledge. It lives in
`data/product/audio_catalog.jsonl`, keyed by canonical passage identity, entirely outside
the frozen graph and ontology. The source is [VedSearch](https://vedsearch.org/), which
publishes one recording per verse.

**Every mapping is verified, not assumed.** A record exists only when the coordinate
transform places our key in the source's numbering *and* the text the source says that
recording recites matches this corpus's own text. That matters concretely: VedSearch numbers
Rigvedic maṇḍala 8 in Griffith's order, so a key-for-key mapping would attach the wrong
recitation to 55 hymns. The transform corrects it and the text check proves it. Where the
text does not match, the mapping is **refused** and recorded as a gap.

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

Coverage, recension safety and the four stated limitations are in
[`PRODUCT_V1_SCOPE.md` §3–§4](../PRODUCT_V1_SCOPE.md) and
[ADR-005](decisions/ADR-005-audio.md).

---

## Configuring Ask VedAnvaya

The LLM provider is an **environment choice, with no code change**. Set three variables in
`.env`:

```bash
VEDAGRAPH_LLM_PROVIDER=gemini     # or openai, anthropic, groq, openrouter, xai, openai_compatible
VEDAGRAPH_LLM_MODEL=gemini-2.5-flash
VEDAGRAPH_LLM_API_KEY=...
```

`openai_compatible` additionally needs `VEDAGRAPH_LLM_BASE_URL`, which covers any
OpenAI-shaped endpoint. Install the adapters with `uv sync --extra ask`. Gemini needs no
vendor SDK — its adapter speaks the public REST contract over `httpx`. No credential is ever
returned by the API or written to a log. See [`.env.example`](../.env.example) for every
variable and which are optional.

**What a citation means.** Retrieval runs first and the model sees only what retrieval found,
so every factual claim carries a citation into the graph and an unanswerable question returns
`INSUFFICIENT_EVIDENCE` rather than a confident denial. A citation is evidence that *the graph
records something*, not that the tradition asserts it.

---

## Source and rights policy

No website is authoritative for every field, and no host-level license is assumed to cover
every file. Rights attach to a specific artifact, and where one artifact carries several
editions they attach to each version: the VedaWeb Book 1 TEI mixes CC BY 4.0 and
CC BY-NC-SA 4.0 layers, so its file-level status is deliberately `UNKNOWN` and the real terms
live in [`data/registry/text_versions.yaml`](../data/registry/text_versions.yaml), extracted
from the TEI header rather than retyped.

VHP currently requires written permission for reproduction and is verification/reference-only.
The reviewed GRETIL Rigveda TEI file declares CC BY-NC-SA 4.0, but other files need
independent review. The underlying 1896 Griffith translation is public domain; its changing
Wikisource transcription still receives snapshot/revision provenance.

Read [`SOURCE_POLICY.md`](architecture/SOURCE_POLICY.md),
[`RIGHTS_POLICY.md`](architecture/RIGHTS_POLICY.md) and
[`VEDAWEB_RIGVEDA_SOURCES.md`](architecture/VEDAWEB_RIGVEDA_SOURCES.md) before ingestion or
redistribution. Repository code licensing is settled independently of corpus licensing; see
[`LICENSE_SCOPE.md`](../LICENSE_SCOPE.md).

---

## The CLI

```bash
# Inspect provenance and ingestion restrictions
uv run vedagraph source list
uv run vedagraph source artifacts

# Fetch exactly one registered-source URL into data/raw (cached by default)
uv run vedagraph source fetch VHP https://vedicheritage.gov.in/example

# Parse a snapshot to staging without writing canonical data
uv run vedagraph ingest parse VHP path/to/snapshot.html
uv run vedagraph ingest stage --config data/builds/rv_mandala_1.yaml

# Build a bounded scope
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
```

> [!WARNING]
> `vedagraph schema export` has destroyed the sealed schema once. Check the diff before
> committing its output.

Full maṇḍala 1, end to end (idempotent):

```bash
uv run python scripts/fetch_wikisource_mandala1.py
uv run python scripts/build_rv_mandala_1_full_config.py
uv run vedagraph corpus build --config data/builds/rv_mandala_1_full_v1.yaml
uv run vedagraph text compare-sample --config data/builds/rv_m1_full_text_comparison.yaml
uv run python scripts/generate_mandala1_reports.py
```

---

## Development, testing and quality

```bash
make check          # ruff format --check, ruff check, mypy, pytest
make api            # the API alone, with reload
```

```bash
cd frontend
pnpm test           # unit tests (vitest)
pnpm typecheck
pnpm lint
pnpm audit          # design-system gates: tokens, contrast, class collisions, z-index, motion
pnpm build
pnpm test:e2e       # Playwright
```

Use `pnpm run <script>` rather than `npx <tool>`: when `node_modules/.bin` is incomplete,
`npx` silently fetches and runs a different package of the same name instead of failing.

Backend tests are offline by default. Tests needing a live graph are marked `neo4j` and
**skip** rather than fail when it is absent, so the suite stays green on a machine with no
database. Checks that can only be made against a populated graph live in scripts instead:
`scripts/check_live_invariants.py`, `scripts/graph_quality_scorecard.py` and
`scripts/audio/validate_catalog.py`.

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest -m "not live"
```

CI performs the same locked, secret-free checks and never crawls sources.

Regenerate the frontend's API types after changing a response model:

```bash
pnpm exec openapi-typescript http://127.0.0.1:8000/openapi.json -o src/lib/api-schema.ts
```

Progress and blockers are maintained in [`docs/STATUS.md`](STATUS.md). The most recent
measured state of the whole system is
[`VEDANVAYA_FINAL_RELEASE_CERTIFICATION.md`](reports/VEDANVAYA_FINAL_RELEASE_CERTIFICATION.md),
which also lists the limitations open at release.
