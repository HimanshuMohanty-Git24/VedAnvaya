# Data architecture

VedaGraph treats the versioned corpus as the source of truth. Databases, indexes, graph
projections, embeddings, interfaces, and LLM-derived interpretations are downstream views.

```text
SOURCE
  ↓ explicit, polite retrieval
IMMUTABLE RAW SNAPSHOT + RETRIEVAL METADATA
  ↓ source adapter
STAGING RECORD
  ↓ lossless normalization
SOURCE ASSERTION
  ↓ field-specific reconciliation
QA
  ↓ only after required checks pass
CANONICAL JSONL + RELEASE MANIFEST
```

There is deliberately no direct source-to-Neo4j path.

## Storage zones

- `data/registry`: reviewed work, source, and rights configuration; version controlled.
- `data/raw`: immutable, content-addressed responses plus sidecar metadata; not committed.
- `data/staged`: parser outputs tied to a snapshot; reproducible and replaceable.
- `data/canonical`: reconciled records; generated from registry, snapshots, and code.
- `data/derived`: transliteration, search forms, and future computed facts.
- `data/qa`: machine-readable release validation.

Generated data is ignored by Git in D1 because source permissions are heterogeneous. Releases
must publish only assets whose individual rights permit distribution.

## Invariants

1. `text_original` is never edited; `text_nfc` is a separate field.
2. IDs derive only from stable canonical URNs, never labels or source URLs.
3. Translations, audio, and traditional metadata are independent attributable records.
4. Conflicting assertions coexist. Reconciliation changes status, not history.
5. Counts are computed from canonical `MANTRA` passage records.
6. LLM output cannot enter canonical models in this phase.

## Deterministic build protocol

A versioned build config declares the work/scope, exact snapshots and SHA-256 hashes, source
artifacts, parser versions, text-selection policy, reconciliation policy, output location, and an
injected build timestamp. Manifests hash the config and generated files. Runtime clock time is not
part of deterministic output.

Ordering is explicit and semantic: Work → Mandala → Sukta → Mantra, followed by passage-target
order for text versions, translations, metadata, citations, and media. Assertions sort by subject,
predicate, source, and stable UUID. Discovery sorts by Sukta then source. Filesystem, XML traversal,
mapping insertion, and HTTP retrieval order never define canonical ordering.

## D2 implementation boundary

The D2 build discovers all 191 Mandala 1 Suktas from two structures and builds only the reviewed
five-Sukta sample. GRETIL, VHP, VedSearch, and Wikisource remain adapter-bounded; broad crawling,
Neo4j, GraphRAG, embeddings, and semantic extraction are intentionally absent.
