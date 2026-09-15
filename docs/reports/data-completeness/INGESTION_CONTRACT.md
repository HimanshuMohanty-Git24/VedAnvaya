# Staging → Canonical Ingestion Contract

Campaign section 17. This is the contract every specialist agent's output must satisfy
before the lead will import it. An artifact that does not satisfy it is not imported —
not rejected on taste, but because the campaign cannot verify what it cannot replay.

## The division of write surfaces

| Who | May write | May never write |
|---|---|---|
| Specialist agent | `data/staging/<domain>/`, `docs/reports/data-completeness/<domain>.md` | the canonical Neo4j graph, any existing repo file, another agent's staging directory |
| Lead | everything, including canonical imports | Product V1 history, the `vedanvaya-v1.0.0` tag |

Specialists run read-only Cypher (`MATCH`/`RETURN`). `CREATE`, `MERGE`, `SET` and `DELETE`
against the canonical database are the lead's alone, and only through a checked-in,
idempotent import. There is to be no one-off Cypher mutation in this campaign.

## Every staging domain looks like this

```
data/staging/<domain>/
  manifest.json          required — described below
  rows.jsonl             the payload, one JSON object per line
  sources.jsonl          one record per external source the payload draws on
  rejected.jsonl         candidates considered and NOT accepted, with the reason
  proofs/                negative-result evidence, where the domain needs it
```

`rejected.jsonl` is not optional bookkeeping. A domain that accepted 900 of 1,000
candidates and cannot say what happened to the other 100 has not been audited, and the
100 are exactly where the wrong-recension and wrong-verse errors hide.

## manifest.json

```json
{
  "domain": "translation",
  "agent": 3,
  "schema_version": "1.0",
  "algorithm_version": "<domain pipeline version>",
  "created_at": "<ISO8601 UTC>",
  "code_commit": "<git rev-parse HEAD at generation time>",
  "config_hash": "<sha256 of the effective config>",
  "source_snapshot_ids": ["<source_id from sources.jsonl>"],
  "files": [{"path": "rows.jsonl", "sha256": "<hex>", "rows": 0, "bytes": 0}],
  "counts": {
    "candidates_considered": 0,
    "accepted": 0,
    "rejected": 0,
    "verified_zero": 0,
    "not_applicable": 0,
    "unresolved": 0
  },
  "closes_gaps": ["GAP-TRANSLATION-001"],
  "qa": {
    "sampled": 0,
    "sample_method": "random|adversarial|both",
    "defects_found": 0,
    "human_reviewed": 0
  }
}
```

`candidates_considered` must equal `accepted + rejected + unresolved`. The lead checks
this arithmetic, and a manifest that does not balance is a manifest that lost rows.

## Every row carries its own provenance

No row may rely on the manifest alone for where it came from, because rows get filtered,
merged and re-exported, and a row separated from its manifest must still be auditable.

```json
{
  "canonical_key": "VG:RV:SAK:M01:S001:V001",
  "payload": { "<domain-specific>": "..." },
  "evidence_layer": "SOURCE_EXPLICIT|DETERMINISTIC_DERIVED|SEMANTIC_MODEL_EXTRACTION|INTERPRETIVE_CLAIM",
  "source_id": "<matches sources.jsonl>",
  "source_locator": "page / section / track / line — precise enough to re-find by hand",
  "source_url": "...",
  "quality_class": "PRIMARY_DIGITAL_EDITION|SCHOLARLY_EDITION|TRADITIONAL_INDEX|INSTITUTIONAL_ARCHIVE|PUBLIC_SCAN|COMMUNITY_ARCHIVE|MODEL_ASSISTED_DERIVATION",
  "mapping_method": "how this row's key was established",
  "mapping_confidence": "EXACT|VERIFIED_SEGMENT|PROBABLE|UNVERIFIED",
  "recension_verified": true,
  "recension_evidence": "what establishes the recension — not which Veda, which recension"
}
```

`UNVERIFIED` rows are staged but not imported. They are the queue for verification work,
not a lower grade of fact.

## Identity

The UUIDv5 namespace `7c8cde94-2bc0-50e2-8819-568ae65a3ec4` and the helpers in
`src/vedagraph/identity.py` are the only way new identities are minted. Existing canonical
keys, URNs and UUIDs are immutable: no row may propose changing one, and nothing moves to
a content-hash identity. New supplementary works get deterministic URNs of the same shape.
No random IDs reach canonical data, ever.

## Validation the lead runs before import

1. Manifest schema, file checksums, and the `candidates_considered` arithmetic.
2. Every `canonical_key` resolves to an existing node, and its `veda` matches what the row
   claims. A key that does not resolve is a mapping bug, and it is the common one.
3. No duplicate `(canonical_key, domain, source_id)` triples.
4. Every `source_id` appears in `sources.jsonl`.
5. Enum fields are closed: an unrecognised `evidence_layer`, `quality_class` or
   `mapping_confidence` raises rather than defaulting. A value silently coerced to a
   default is how an attribution axis gets three disagreeing writers.
6. Dimension deltas reconciled against the recorded baseline — rows sent versus rows
   landed, per dimension, per Veda.

## Import

Idempotent, resumable, and read back. The existing `scripts/load_enrichment_neo4j.py` is
the pattern to follow: it re-reads every count out of the database after writing, because
a `MERGE` can collapse two rows into one and a `MATCH` can find no endpoint, and neither
failure appears offline. Rows-sent versus rows-landed is diffed per dimension every time.

Rollback is the snapshot recorded in `STATUS.md`, plus a per-import record of exactly which
node and relationship ids were written.

## What may not be silently done

- Turning `NOT ASSESSED` into `VERIFIED ZERO`.
- Writing `0` where the population is unknown. Use `null`, and say why in the row.
- Mapping another recension's material onto the one we hold.
- Attaching a long recording to an exact mantra without verified boundaries.
- Attributing a model-assisted rendering to a historical translator.
- Asserting a scholarly disagreement that no two attributed sources actually hold.
- Adding an untyped `RELATED_TO`-style edge.
