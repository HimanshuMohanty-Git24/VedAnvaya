# ADR-013: A lexical mention is not a traditional assignment

Status: Accepted
Date: 2026-09-04
Supersedes: nothing. Extends ADR-011 (deterministic knowledge layer) and
ADR-012 (entity resolution is registry data).

## Context

The traditional knowledge layer records what the Anukramaṇī *assigns* to a mantra:
`HAS_RISHI`, `HAS_DEVATA`, `HAS_CHANDAS`. This phase adds what the Sanskrit text
itself *contains*: `MENTIONS_ENTITY`.

The two look similar enough to merge, and merging them would be a serious error.
"Agni is the Devatā of RV 1.1.1" is a statement by the tradition about the hymn's
addressee. "RV 1.1.1 contains the word `agním`" is a statement about the text. They
have different truth conditions, different provenance, and — as measured — they
diverge substantially in practice.

The temptation to merge is concrete rather than hypothetical. A user asking "which
deity is most important in the Rigveda" wants one number, and there are at least
three defensible answers that rank differently.

## Decision

### 1. The two predicates never mix

`MENTIONS_ENTITY` is a distinct predicate, in a distinct file, with provenance
class `DETERMINISTIC_DERIVED`. `HAS_DEVATA` keeps `SOURCE_EXPLICIT` and is not
modified, re-derived or reconciled by this layer. Neither is evidence for the
other. No code path converts one into the other.

### 2. Three counts, never one

Analytics computes `mantra_assignment_count`, `mantra_mention_count` and
`token_occurrence_count` separately, and the stats file carries a written warning
that none of them means "the most used god". The measured divergence justifies the
separation rather than merely permitting it:

| entity | assigned | mentioned |
|---|---|---|
| `pavamānaḥ somaḥ` | 1,087 | 0 |
| `viśvedevāḥ` | 805 | 0 |
| `mitraḥ` | 10 | 320 |
| `pṛthivī` | 4 | 319 |

### 3. Mentions rest on annotated lemmas, never on scanning text

Matching starts from a token of the pinned morphology layer and its Grassmann-linked
lemma identifier. Substring matching is prohibited outright; fuzzy matching may
produce review candidates and never an edge. This is stated in full in
[RIGVEDA_LEXICAL_MENTION_POLICY.md](../architecture/RIGVEDA_LEXICAL_MENTION_POLICY.md).

### 4. Ambiguity fails closed

A lemma reaching two accepted entities produces no edge and an
`AMBIGUOUS_LEXICAL_ENTITY` record, regardless of how frequent it is. 711 tokens
were left unresolved on these grounds in v1.

### 5. Ṛṣi lexical mentions are deferred

The canonical Ṛṣi registry stores the Anukramaṇī's patronymic-plus-name labels
(`VG:RISHI:RAHUGANO-GOTAMAH`) while the morphology supplies bare lemmas
(`gótama-`). Linking them requires decomposing a proper name by grammar, which
[RIGVEDA_RISHI_STRUCTURE_FINDINGS.md](../architecture/RIGVEDA_RISHI_STRUCTURE_FINDINGS.md)
declines to do without a source. Rather than break that rule in a second place, v1
creates no Ṛṣi mentions.

A side effect is desirable: the Devatā/Ṛṣi homonyms `agniḥ`, `indraḥ` and `aditiḥ`
cannot collide, because the Ṛṣi entities are not candidates at all.

### 6. Token identity names the annotation layer; mantra identity does not

```
VG:TOKEN:VEDAWEB-ZURICH:RV:SAK:M01:S001:V001:PA:T001
```

Tokenization is a property of an edition. A different morphology source would
segment some mantras differently, so its tokens get their own layer segment and
their own UUIDv5 namespace path. Adopting a second morphology source must **not**
change `VG:RV:SAK:M01:S001:V001`, whose identity depends on the canonical corpus
alone.

### 7. Morphology is annotation, not text

`GRETIL.RV.AUFRECHT` remains the canonical Sanskrit. The annotation's own reading
is stored as `surface_form` beside it, never in place of it. Where the two
disagree, both are kept: two mantra pairs are identical in the canonical text but
not in the annotation's token sequence, and the parallel engine reports that as
two different facts rather than choosing one.

### 8. Composition is reviewed, never inferred

`HAS_COMPONENT` comes only from `ACCEPTED` rows in `devata_components.yaml`, with
provenance `HUMAN_REVIEWED`. Composition is never inferred from a hyphen, a dual
or plural ending, or a substring. A group deity is never expanded into the set of
its supposed members: `viśvedevāḥ` and `ādityāḥ` are explicitly recorded as
`REJECTED` so that the absence is a decision rather than an oversight.

### 9. Co-occurrence is an observation, not a relationship

Counts of two entities being mentioned in the same mantra are stored with an
explicit `unit` and `method`. No `RELATED_TO` edge is derived from them, and
`CO_OCCURS_WITH` is not created in this phase.

## Consequences

**Good.** The graph can answer "which deity does the tradition assign most often"
and "which deity does the text name most often" as different questions with
different answers. Every mention carries the token that produced it, so a reader
can be shown the exact word in the exact pāda. Precision is measurable
independently, and was measured: 0.34% detectable false positives.

**Accepted costs.** Coverage is partial by design — 6,531 of 10,552 mantras carry a
mention, 38 aliases are accepted out of 214 registered Devatā entities, and Ṛṣi
mentions are absent entirely. Sarasvatī, one of the most significant deities,
produces no mentions at all because the annotation lemmatises her under a stem
shared with the masculine Sarasvant and v1 has no feature-conditioned matching.

These are the right costs. Recall can be raised later by review; precision lost to
a bad automatic merge cannot be recovered, because nothing downstream would know
which edges to distrust.

**If precision falls in a later audit, restrict the unsafe alias classes. Do not
expand coverage to compensate.**
