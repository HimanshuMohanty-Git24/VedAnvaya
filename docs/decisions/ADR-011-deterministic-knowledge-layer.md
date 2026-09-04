# ADR-011: The deterministic knowledge layer is a separate rebuildable layer

Status: Accepted

Traditional Ṛṣi/Devatā/Chandas metadata does not live inside the canonical corpus JSONL
and does not live in a graph database. It is a third layer:

```text
Rigveda canonical corpus  +  pinned Anukramaṇī artifacts  +  reviewed entity registries
                              ↓
                    deterministic knowledge layer (JSONL + manifest)
                              ↓
                    future Neo4j importer, future GraphRAG
```

Neo4j will be a derived database, never the source of truth. Nothing in this layer is
written directly to a graph, and the layer is fully rebuildable from pinned inputs.

A knowledge manifest always names the exact corpus manifest hash, corpus version, source
commit, per-artifact SHA-256, registry file hashes and policy versions it was built from.
A knowledge layer that cannot name the corpus it enriches is not a knowledge layer.

Predicates are whitelisted to `HAS_RISHI`, `HAS_DEVATA` and `HAS_CHANDAS`. Semantic
predicates (`SYMBOLIZES`, `EXPRESSES`, `RELATED_TO`, `THEME`) belong to a later
interpretive layer, and literal name occurrence (`MENTIONS_ENTITY`) belongs to a later
deterministic lexical phase. Neither exists yet.

**An assignment is not a textual mention.** `HAS_DEVATA: agniḥ` states that the
traditional index assigns Agni to that mantra. It makes no claim about the words in the
Sanskrit. Conflating the two would silently turn a metadata count into a text statistic.

Scope is preserved. Where the source scopes a claim to numbered verses, the assertion is
`SOURCE_EXPLICIT`; where the source states one claim for a whole hymn, the expansion to
that hymn's mantras is marked `SOURCE_DERIVED_SCOPE`, so a hymn-level statement can never
be mistaken for a verse-level one. The raw sūkta-level source assertion is kept either
way, and the digitized Anukramaṇī can be reconstructed exactly from it.

## Composite Devatā decomposition is designed but not implemented

The source authors state that they present group and dual labels as they are, and VedaGraph
preserves that. A future phase may add composition relations:

```text
VG:DEVATA:MITRAVARUNAU  ──HAS_COMPONENT──▶  VG:DEVATA:MITRA
                        ──HAS_COMPONENT──▶  VG:DEVATA:VARUNA
VG:DEVATA:INDRAGNI      ──HAS_COMPONENT──▶  VG:DEVATA:INDRAH
                        ──HAS_COMPONENT──▶  VG:DEVATA:AGNIH
VG:DEVATA:VISVEDEVAH    ── group entity, no component list
```

Three conditions must hold before any such edge is created, and none holds today:

1. the component entity exists in the registry in its own right;
2. an explicit reviewed mapping states the decomposition, with evidence;
3. the mapping is committed data, like every other identification in this layer.

Morphology is not evidence. `mitrāvaruṇau` looks like a dual to a reader who knows Sanskrit;
deriving that automatically is interpretation, so the nine hyphen-joined labels are flagged
`is_composite` with their surface parts recorded, and nothing further is asserted. No language
model participates in this, now or later.

## Where semantic extraction begins

| Deterministic — this layer and the next | Interpretive — a later, separate layer |
| --- | --- |
| `HAS_RISHI`, `HAS_DEVATA`, `HAS_CHANDAS` | `EXPRESSES`, `SYMBOLIZES`, `RELATED_TO` |
| `MENTIONS_ENTITY` from literal alias matching | `THEME`, `PHILOSOPHICAL_CONCEPT` |
| Exact and near mantra parallels | `RITUAL_ASSOCIATION` |
| Reviewed `HAS_COMPONENT` | Anything requiring a reading of the text |
| Frequency and graph statistics | |

The boundary is not a matter of confidence but of kind: everything on the left is recoverable
from a pinned artifact by a rule a reader can check, and everything on the right is not.
Interpretive output never becomes canonical source data (ADR-006) and will live in its own layer
with its own manifest.
