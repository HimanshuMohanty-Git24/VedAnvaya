# Rigveda Lexical Mention Policy

Policy version: `rigveda-lexical-mention-policy-v1`
Applies to: `MENTIONS_ENTITY` in `data/knowledge/rigveda_lexical_v1`.

---

## The distinction this policy exists to protect

```
Mantra
├── HAS_RISHI / HAS_DEVATA / HAS_CHANDAS  → traditional metadata
│     the Anukramaṇī assigns this entity to this mantra.
│     Provenance: SOURCE_EXPLICIT. Built by the knowledge layer.
│
└── MENTIONS_ENTITY                        → lexical evidence
      the Sanskrit text of this mantra contains a word whose annotated
      lemma resolves to this entity.
      Provenance: DETERMINISTIC_DERIVED. Built by the lexical layer.
```

A mantra assigned to Agni need not mention Agni. A mantra mentioning Agni need not
be assigned to Agni. Both are recorded, in separate files, with separate predicates
and separate provenance classes. They are never merged, and no query should treat
one as evidence for the other.

The measured divergence is large, which is the point: `mitraḥ` is assigned to 10
mantras and lexically mentioned in 320; `pavamānaḥ somaḥ` is assigned to 1,087 and
mentioned in none.

---

## Matching

### The only permitted paths

1. **`LEMMA_ID_EXACT`** — the token and a reviewed alias share the annotation
   layer's own stable Grassmann-linked lemma identifier (`lemma_agni_79`). No
   string is compared.
2. **`LEMMA_NORMALIZED_EXACT`** — the token's lemma and the alias lemma have the
   same comparison key. Available only for aliases that declare no lemma id.

In the v1 build, **all 9,322 mention token occurrences came from
`LEMMA_ID_EXACT`.** The string path contributed nothing.

### What is forbidden

**No substring matching.** Nothing in the pipeline asks whether an alias occurs
inside a mantra's text. Sandhi, compounding and short names make that test produce
false positives at a rate no downstream filter repairs. Matching starts from an
annotated token, never from scanning text.

**No fuzzy matching may create an edge.** Similarity has exactly one destination:
`LexicalAliasCandidate` records for human review. The proposal rules are exact
after normalization (`IDENTITY`, `NOMINATIVE_VISARGA`) and even those only propose.
No candidate becomes an alias without a person moving it into the registry.

**No compound splitting.** A dvandva produces a mention only when the annotation
layer itself supplies it as a single lexical entry with its own lemma id — as it
does for `indrāgní-`, `mitrā́váruṇa-`, `dyā́vāpr̥thivī́-`. Splitting a compound
ourselves to manufacture component mentions is not permitted. Decomposition is a
separate, human-reviewed question answered by `HAS_COMPONENT`.

**No surface-form matching.** Every token in this annotation layer carries a lemma,
so surface matching would add risk and no recall. It is not implemented.

---

## The lexical alias registry

`data/registry/lexical_aliases.yaml`. A lexical alias is a reviewed statement that
one lemma may evidence a mention of one entity.

**A lexical alias is not an entity alias.** `anukramani_aliases.yaml` answers
"which Anukramaṇī spelling names this entity". Being listed there does not make a
string a lexical alias, and no code promotes one to the other. `ALTERNATE_NAME` and
`EPITHET` entries in the entity registry produce no mentions.

### Types

| type | may produce a mention | meaning |
|---|---|---|
| `CANONICAL_LEMMA` | yes | the lemma is the entity's proper name |
| `ORTHOGRAPHIC_VARIANT` | yes | same word, different spelling |
| `KNOWN_LEMMA_VARIANT` | yes | reviewed stem/nominative or stem-class relation |
| `INFLECTIONAL_SOURCE_FORM` | yes | the source lists an inflected form as its lemma |
| `EPITHET_REVIEWED` | yes | an epithet a reviewer accepted as naming the entity |
| `COMPOSITE_NAME` | yes | a dvandva the annotation supplies as one lexical entry |
| `DO_NOT_MATCH` | **never** | explicit suppression |

An alias produces a mention only if its type is mention-bearing **and** its
`review_status` is `ACCEPTED`. A `DO_NOT_MATCH` rule suppresses whatever its review
status would otherwise allow.

### `DO_NOT_MATCH` is why precision is high

The Anukramaṇī registers Devatā entities under labels that are ordinary Vedic
nouns: `kaḥ` (the interrogative pronoun, 468 occurrences), `rathaḥ` ("chariot",
471), `harīḥ` ("bay steed", 271), `aśvaḥ` ("horse", 238). Matching those lemmas
would fabricate roughly 2,000 false mentions.

22 suppression rules, each with its evidence, prevent that. They are the single
largest contributor to the layer's precision.

---

## Fail-closed ambiguity

If a lemma reaches more than one accepted entity, **no edge is created**, however
frequent the lemma. The token is written to `ambiguous_mentions.jsonl` with status
`AMBIGUOUS_LEXICAL_ENTITY` and the competing entity keys, so the absence is visible
rather than silent.

`AMBIGUOUS_SOURCE_LEMMA` covers the case where the annotators themselves assigned
a token several lexical entries and only some reach a canonical entity. That is the
source's uncertainty, not ours to settle.

786 tokens were deliberately left unresolved in v1. The largest groups:

- `sárasvant-` — the annotation lemmatises every Sarasvatī form under the vant-stem
  that also covers the masculine Sarasvant. Separable by the annotation's own
  gender feature, but v1 has no feature-conditioned alias mechanism, so no edge is
  created. This is the highest-value deferred item.
- `áp-` — both the ordinary noun "water" and the deified Āpaḥ, inseparable
  lexically.
- `yamá-`, `mr̥tyú-`, `vená-`, `sī́tā-` — deity and appellative share one entry.
- `dadhikrā́-` — the entity registry holds two Devatā entries for one lemma.

---

## Scope of v1: Devatā only

Lexical mention extraction is attempted for `DEVATA` entities only.

**Ṛṣi is deferred, for a source reason rather than a difficulty reason.** The
canonical Ṛṣi registry stores the Anukramaṇī's own labels, which are
patronymic-plus-name phrases: `VG:RISHI:RAHUGANO-GOTAMAH` ("rāhūgaṇo gotamaḥ"),
`VG:RISHI:SAUNAKO-GRTSAMADAH`, `VG:RISHI:MAITRAVARUNIRVASISTHAH`. The annotation
layer supplies bare lemmas (`gótama-`, `gŕ̥tsamada-`, `vásiṣṭha-`). Reaching a single
canonical Ṛṣi from a bare lemma would mean decomposing those labels by name
grammar — which is exactly the inference forbidden for Ṛṣi structure. Rather than
break that rule for mentions, the layer creates none. See ADR-013.

Restricting to Devatā also removes the Devatā/Ṛṣi homonym problem for `agniḥ`,
`indraḥ` and `aditiḥ`, which are registered under both families. Those Ṛṣi entities
are simply not candidates, so nothing is silently merged.

**Chandas is excluded on principle, not scope.** A metre name occurring in the
text does not mean the mantra "mentions its metre". Chandas relationships remain
metadata.

---

## Evidence

Every assertion carries the tokens that produced it:

```json
{
  "subject_key": "VG:RV:SAK:M01:S001:V001",
  "predicate": "MENTIONS_ENTITY",
  "object_key": "VG:DEVATA:AGNIH",
  "occurrence_count": 1,
  "evidence": [{
    "token_key": "VG:TOKEN:VEDAWEB-ZURICH:RV:SAK:M01:S001:V001:PA:T001",
    "sequence": 1, "pada": "a",
    "surface": "agním", "lemma": "agní-",
    "alias_key": "VG:DEVATA:AGNIH|VEDAWEB.ZURICH|agni",
    "method": "LEMMA_ID_EXACT"
  }],
  "provenance_class": "DETERMINISTIC_DERIVED"
}
```

A mantra naming one entity several times produces **one edge with several evidence
tokens**, carrying `occurrence_count` and each token's sequence and pāda. The graph
stays simple; the textual record stays complete; a reader can be shown the exact
word.

---

## Measured precision

Full method and sample in
[RIGVEDA_LEXICAL_MENTION_REVIEW.md](../reports/RIGVEDA_LEXICAL_MENTION_REVIEW.md).

The aliases were chosen on lexical grounds, so the annotation's **grammatical
gender** — which played no part in that choice — is independent evidence. A token
whose gender disagrees with the deity's is a candidate false positive.

| measure | value |
|---|---|
| mention token occurrences | 9,322 |
| off-gender occurrences (upper bound on detectable false positives) | 32 |
| **detectable false-positive rate** | **0.34%** |
| stratified review sample | 228 rows |
| tokens deliberately left ambiguous | 786 |

Per-entity, the riskiest accepted aliases behave as predicted:

| entity | occurrences | off-gender | rate |
|---|---|---|---|
| `VG:DEVATA:SURYAH` | 404 | 23 | 5.69% |
| `VG:DEVATA:MITRAVARUNAU` | 92 | 1 | 1.09% |
| `VG:DEVATA:MITRAH` | 328 | 3 | 0.91% |
| `VG:DEVATA:ADITIH` | 174 | 1 | 0.57% |
| `VG:DEVATA:ASVINAU` | 444 | 1 | 0.23% |
| `VG:DEVATA:INDRAH` | 2,438 | 2 | 0.08% |
| `VG:DEVATA:AGNIH` | 1,724 | 0 | 0.00% |

`mitrá-` was flagged in the registry as the highest-risk accepted alias before the
audit ran; the audit found 3 neuter occurrences ("alliance") out of 328. Sūrya's
23 feminine occurrences are `sūryā́-`, the Sun's daughter of RV 10.85 — arguably a
distinct entity rather than an error, and recorded as the one entity worth
splitting first.

This is an upper bound on the classes gender can detect. It cannot detect an error
where deity and appellative share a gender, which is why the `DO_NOT_MATCH` rules
carry the cases where that would apply.

---

## Precision over recall

The layer covers 6,531 of 10,552 mantras. 4,021 mantras have no recognised mention.
That number is not a defect to be closed by loosening the policy. It reflects:

- 38 accepted aliases out of 214 registered Devatā entities;
- 22 deliberate suppressions;
- 11 unreviewed aliases producing nothing;
- Ṛṣi mentions not attempted at all.

If precision falls in a later review, the correct response is to **restrict the
unsafe alias classes, not to expand coverage.**
