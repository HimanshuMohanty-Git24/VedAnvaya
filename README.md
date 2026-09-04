# VedaGraph

VedaGraph is a provenance-aware, versioned data foundation for a future multilingual,
multimodal knowledge graph of the four Vedas. The canonical corpus—not a graph database—is the
source of truth.

> Text is immutable. Metadata is provenanced. Deterministic facts are separated from
> interpretation. LLM output never becomes canonical source data.

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

## Explicitly not implemented

There is no Neo4j driver, Cypher, GraphRAG, embedding pipeline, frontend, LLM API, semantic
extraction, mass corpus crawl, or audio download. The RV 1.1 pilot is infrastructure validation,
not a publication-ready text edition.

The deterministic predicate whitelist is exactly `HAS_RISHI`, `HAS_DEVATA`, `HAS_CHANDAS`
(traditional metadata) plus `MENTIONS_ENTITY`, `EXACT_PARALLEL_OF`, `PARALLEL_TO` and
`HAS_COMPONENT` (lexical and cross-mantra). `SYMBOLIZES`, `EXPRESSES`, `RELATED_TO` and `THEME`
belong to a later interpretive layer that does not exist.

No Ṛṣi genealogy edges exist either: the pinned Anukramaṇī has no family, gotra or ancestor
field, and the lineage visible in a name like `vaiśvāmitro madhucchandāḥ` is Sanskrit grammar
rather than data. The honest output is no edges, and that is what was produced.

## Install

Requirements: Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync --extra dev
uv run vedagraph --help
```

Copy `.env.example` to `.env` only when local overrides are needed. Provide a contact email before
running repeat source retrieval. Never commit `.env`.

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

## Next milestone

The Rigveda deterministic lexical and cross-mantra layer is built:
`RIGVEDA_DETERMINISTIC_LEXICAL_READY_WITH_LIMITATIONS`. Alignment, token identity, precision,
reproducibility and QA all pass. The limitations are deliberate: mention coverage is partial
(40 accepted aliases of 214 Devatā entities), Ṛṣi lexical mentions await a source that can
decompose patronymic labels, and Ṛṣi genealogy has no sufficient deterministic source at all.
Mention policy v2 added feature-conditioned aliases and a lemma-identity rule, taking the
detectable false-positive rate from 0.34% to 0.01% and recovering Sarasvatī and Sarasvant
from one shared annotated lemma.

The **semantic candidate layer** is built and tested offline, and the 508-mantra
Codex-direct pilot is complete:
`RIGVEDA_SEMANTIC_PILOT_COMPLETE_AWAITING_HUMAN_GOLD`. A closed ontology of 17 node types and
14 predicates, a deterministic evidence packet, strict Structured Outputs against
`gpt-5.6-luna`, a structural validator that rejects fabricated citations, and a per-predicate
acceptance policy that auto-accepts nothing until a hand-annotated gold set has measured it.
Its output is candidate assertions only, and it never alters the canonical corpus, the
traditional metadata, the lexical mentions or the deterministic parallels. The 120-mantra
gold subset remains unannotated, so no predicate is unlocked and no semantic assertion is
accepted. Decision:
[ADR-014](docs/decisions/ADR-014-llm-output-is-candidate-only.md). Only after that comes
Neo4j as a derived database, then GraphRAG.

Progress and blockers are maintained in [`docs/STATUS.md`](docs/STATUS.md); the generated build
summaries are [`RIGVEDA_FULL_BUILD.md`](docs/reports/RIGVEDA_FULL_BUILD.md),
[`RIGVEDA_DETERMINISTIC_KNOWLEDGE_BUILD.md`](docs/reports/RIGVEDA_DETERMINISTIC_KNOWLEDGE_BUILD.md)
and [`RIGVEDA_DETERMINISTIC_LEXICAL_BUILD.md`](docs/reports/RIGVEDA_DETERMINISTIC_LEXICAL_BUILD.md).
