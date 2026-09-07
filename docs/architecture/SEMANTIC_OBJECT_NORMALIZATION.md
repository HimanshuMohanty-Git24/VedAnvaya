# Semantic object normalization

Status: implemented as an offline candidate/comparison layer in v1. No predicate is
unlocked, no assertion is accepted, and no legacy extraction is rewritten.

Versions:

- semantic-object schema: `rigveda-semantic-object-v1`
- structured comparison policy: `rigveda-semantic-object-comparison-v1`
- future explicitness policy: `rigveda-semantic-explicitness-v2`

## Problem

The v1/v2 assertion shape gives a relation either a canonical entity key or a generated
semantic-entity candidate. For non-canonical targets, comparison eventually reduces the
candidate to a label. The historical silver comparator therefore treats folded string
equality as exact and shared words as partial agreement. That is reproducible, but it is
not semantic identity.

These are distinct failure classes:

- The same canonical entity may have different display spellings. `agniḥ`, `Agni`, and
  another source spelling agree only when both resolve to `VG:DEVATA:AGNIH`; spelling
  resemblance does not perform that resolution.
- The same requested outcome can be phrased differently, such as “protection and
  wealth” and “wealth, safety, and assistance”. Those examples are not declared
  equivalent. They must be decomposed into evidenced outcome occurrences before their
  components can be compared.
- The same action may be worded as “destroying enemies” or “slaying hostile foes”. The
  action head and participants must be compared separately. `destroy` and `slay` are not
  automatically synonyms.
- An offering occurrence, the ritual action of offering, and the physical substance
  offered are different object kinds even if all three labels contain “Soma”.
- “Sacrifice”, “Soma pressing”, “libation”, and “purification” can denote different
  ritual-event granularities. Shared ritual vocabulary is not identity.
- “Seat”, “dwelling”, “station”, “world”, or “mansion” may be spatial descriptions rather
  than geographic places. Uncertain cases remain `OPAQUE_SPATIAL_REFERENT` or review.
- A natural phenomenon and a deity are not interchangeable. A reference to dawn as a
  phenomenon is not automatically the canonical Devatā `VG:DEVATA:USAH`.
- `SOMA` and `PAVAMANA SOMA` remain distinct where deterministic registry identity or
  the evidence supports the distinction. Normalization does not erase that granularity.
- A model may package several relation objects into one label while another emits one
  object per assertion. Comparison must be order-independent but must not split opaque
  legacy prose by guesswork.

The generated label is retained for display and audit. It is an annotation, not an
identifier and not sufficient evidence for a graph merge.

## Occurrence before concept

The extraction unit is an occurrence-level `SemanticObjectCandidate`:

```text
evidenced occurrence
        ↓
candidate normalization
        ↓ human review / future registry work
canonical semantic concept (optional, later)
```

A mantra requesting “protection” creates a requested-outcome occurrence. It does not
mint a global `PROTECTION` concept. Candidate IDs identify that occurrence within a
pinned extraction artifact and deliberately do not imply that two candidates mean the
same thing.

## Object kinds

The object vocabulary is separate from the older reusable `SemanticNodeType` vocabulary:

| Kind | Meaning |
|---|---|
| `CANONICAL_ENTITY_REF` | Deterministically resolved existing entity key |
| `SEMANTIC_ENTITY_REF` | Non-canonical entity-like occurrence |
| `EVENT` | Structured action occurrence with optional roles |
| `REQUESTED_OUTCOME` | One desired result occurrence |
| `RITUAL_EVENT` | Ritual/action type occurrence |
| `OFFERING_REF` | Thing in its role as an offering |
| `SUBSTANCE_REF` | Physical substance occurrence |
| `NATURAL_PHENOMENON_REF` | Phenomenon, not deity identity |
| `PLACE_REF` | Explicit place or spatial referent judged to be a place |
| `STATE_REF`, `QUALITY_REF`, `CONCEPT_REF` | Expressed state, quality, or concept |
| `ACTION_REF` | Review-only action label when event structure is unavailable |
| `OPAQUE_REFERENT` | EVIDENCED referent whose kind/identity is unresolved |
| `OPAQUE_SPATIAL_REFERENT` | Spatial expression not safely promoted to `PLACE_REF` |
| `ONTOLOGY_GAP_REF` | Supported referent for which the object ontology lacks a type |

The ontology-gap record exposes `PERSON_LIKE_REFERENT_UNMODELED`,
`PATRON_ROLE_UNMODELED`, `ANCESTOR_ROLE_UNMODELED`, and
`KINSHIP_ROLE_UNMODELED`. None is mapped to `COSMIC_ENTITY` and none adds a new canonical
ontology type.

Normalization statuses are `CANONICAL_REF`, `NORMALIZED_CANDIDATE`, `NEEDS_REVIEW`,
`AMBIGUOUS`, `ONTOLOGY_GAP`, and `UNRESOLVED_LEGACY_OBJECT`. “Normalized candidate” means
the occurrence has typed, concise structure; it does not mean canonically accepted.

## Predicate-specific targets

The predicate vocabulary remains the locked v1 vocabulary. The object policy changes:

| Predicate | Preferred target | Boundary |
|---|---|---|
| `INVOKES`, `PRAISES` | `CANONICAL_ENTITY_REF` | Use opaque/review if deterministic resolution fails; praise is not part of the object label |
| `DESCRIBES` | canonical or semantic entity occurrence | Property/action detail belongs in additional structure, not an expanded entity label |
| `REQUESTS` | `REQUESTED_OUTCOME` | One independently supported outcome per assertion |
| `DESCRIBES_ACTION` | `EVENT` | Action head and evidenced participants are separate fields |
| `INVOLVES_RITUAL` | `RITUAL_EVENT` | Ritual event, not offered material |
| `INVOLVES_OFFERING` | `OFFERING_REF` | Offering role, not ritual performance or substance identity |
| `INVOLVES_SUBSTANCE` | `SUBSTANCE_REF` | Preserve deterministic lexical/canonical distinctions including Soma/Pavamana |
| `REFERS_TO_NATURAL_PHENOMENON` | `NATURAL_PHENOMENON_REF` | Devatā assignment alone is never evidence |
| `REFERS_TO_PLACE` | `PLACE_REF` | Use `OPAQUE_SPATIAL_REFERENT` when the place boundary is unclear |
| `EXPRESSES` | state, quality, or concept occurrence | Do not copy a sentence fragment as identity |
| `HAS_THEME` | review-only concept occurrence | No additional operationalization in this version |
| `ASSOCIATED_WITH`, `CONTRASTS_WITH` | review-only | Remain conservative and never auto-accepted |

### Requests with several outcomes

Future v3 output splits genuinely independent outcomes. “Grant protection and wealth”
therefore yields two `REQUESTS` assertions with separate evidence-anchored occurrence
objects. Assertion-set comparison is order-independent, so the reverse order agrees.
Qualifiers that change an outcome stay with that outcome. Legacy coordinated prose is
not automatically split: unless migration can preserve its structure without semantic
judgment, it is `UNRESOLVED_LEGACY_OBJECT`.

### Action events

An `EVENT` contains an `action_head`, optional canonical `actor_entity_id` and
`patient_entity_id`, optional typed participants, qualifiers, and evidence. Missing roles
remain absent. For example, an evidenced Indra/Vṛtra event may carry actor Indra, action
head `slay`, and patient Vṛtra. If a second object says `destroy` with the same roles,
the shared participants support `PARTIAL_OBJECT_OVERLAP`; the policy does not equate the
action heads.

## Evidence anchoring

Every non-canonical object carries one or more `SemanticEvidenceAnchor` records. An
anchor names the source passage plus at least one deterministic reference:

- translation record ID and optional half-open character offsets;
- Sanskrit token IDs;
- passage IDs;
- another deterministic evidence ID, such as a lexical-mention or traditional-metadata
  assertion ID.

Offsets are optional because the legacy extraction artifacts cite whole translation
records. Absence of an offset never licenses generated prose to become evidence.

## Deterministic IDs

`VG:SEMOBJ:<20 hex>` is a SHA-256-derived occurrence ID over:

- source run ID;
- mantra ID;
- locked predicate;
- sorted evidence signature;
- assertion ordinal;
- legacy local object ID, when migrating.

The same pinned artifact produces the same ID. Changing the run, evidence, predicate, or
ordinal produces another occurrence. The hash is not a canonical semantic identifier.

## Assertion signature

The normalized assertion signature is:

```text
subject_id
+ locked predicate
+ typed object signature
+ deterministic evidence signature
```

The object signature contains the object kind, canonical entity ID when present,
normalized head, order-insensitive qualifiers, beneficiary/target roles, and structured
event fields. It explicitly excludes `display_label`. The evidence signature is the
sorted set of typed deterministic references, including any translation offsets.

Consequently, the signature is not `subject + predicate + normalized string`.

## Comparison policy

The structured comparator reports:

- `EXACT_CANONICAL_ENTITY` when canonical keys are identical;
- `EXACT_NORMALIZED_OBJECT` when all typed occurrence fields agree;
- `COMPATIBLE_OBJECT` for non-conflicting structure with the same typed head;
- `PARTIAL_OBJECT_OVERLAP` for shared event/object fields without equivalence;
- `GRANULARITY_DIFFERENCE` when one structured object is a strict detail subset;
- `PREDICATE_DIFFERENCE` when an object alignment crosses predicates;
- `OBJECT_TYPE_DIFFERENCE` across boundaries such as ritual/offering/substance or
  Devatā/phenomenon;
- `CONFLICTING_OBJECT`, `UNRESOLVED`, or `EXPERT_REQUIRED` otherwise;
- left-only, right-only, and no-claim rows for complete diagnostics.

Exact normalized label equality is retained only as `label_equality_signal`. It cannot
produce exactness for an unresolved object. Fuzzy scores and embeddings are not used.
Different labels do not alone prove disagreement, and identical labels do not override
different kinds or canonical IDs.

## Legacy migration

V1, v2, and Sol files remain immutable. Offline migration reads stored payloads and
copies local labels into display fields, maps predicates/node types to object kinds,
preserves canonical entity IDs, and converts existing evidence references. It does not
invent event participants, split ambiguous coordinated phrases, resolve synonyms, or
rewrite sentence-length labels. Such objects are marked `UNRESOLVED_LEGACY_OBJECT`.

Both the historical string/signature metrics and the new structured diagnostics are
reported. Neither is accuracy because no human gold exists.

## Explicitness for future v3

`EXPLICIT` means that both relation and target are directly supportable from supplied
Sanskrit or translation evidence. A supplied translation is evidence, not an automatic
inference step. `STRONG_INFERENCE` requires exactly one limited, named inferential step.
Anything requiring broad thematic, theological, symbolic, or narrative interpretation
is not emitted in semantic v1/v3 candidate output. Legacy explicitness values are audited
but never relabelled.

## Safety invariants

- `unlocked_predicates = []`.
- No model-model agreement accepts an assertion.
- No model output becomes human gold.
- No object normalization writes into corpus, traditional, lexical, or morphology data.
- No similarity rule establishes identity.
- Natural phenomenon and canonical Devatā identities remain separate.
- Ritual event, offering role, and substance remain separate.

