# Rigveda Lexical Mention Policy

Policy version: `rigveda-lexical-mention-policy-v2`
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

In the v1 build, **all 9,364 mention token occurrences came from
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

711 tokens are left unresolved, and **each now carries a typed linguistic reason** rather
than a queue state. `data/staging/final_closure_sprint/agent3/lexical_nonresolution_typed.jsonl`
holds one row per token; `scripts/build_lexical_nonresolution_reasons.py` regenerates it.

**The feature-conditioned alias deferral is closed and this paragraph used to be wrong
about it.** An earlier revision named `sárasvant-` as the largest group and the
highest-value deferred item, on the grounds that "v1 has no feature-conditioned alias
mechanism". The mechanism exists: `lexical_aliases.jsonl` carries `allowed_case`,
`allowed_gender`, `allowed_number`, `allowed_pos` and `forbidden_features`, and seven
aliases use it — `áditi-`, `aśvín-`, `mitrá-`, `sárasvant-`, `sūryā́-` and `sū́rya-`.
`sárasvant-` is resolved by it: its 75 tokens split 70 `F` / 5 `M` on the annotation's own
gender feature, and two `ACCEPTED` gender-conditioned aliases send the feminine to
Sarasvatī and the masculine to Sarasvant. It appears **0 times** in
`ambiguous_mentions.jsonl` and is not part of the 711.

Measured against the annotation, **none of the ten residual lemmas is separable by any
annotated feature**: `áp-` is `F.PL` in 540 of 547 tokens whether it means water or the
goddesses, `yamá-` is `M.SG` for both the god and the twin, and so on. The mechanism is not
the obstruction here; the lexicon is.

The three typed reasons, and what each means:

| reason | tokens | lemmas |
|---|--:|---|
| `LEXEME_COVERS_DEITY_AND_APPELLATIVE` | 625 | `áp-` 547, `yamá-` 60, `mr̥tyú-` 16, `sī́tā-` 2 |
| `DEVATA_OR_RISHI_UNDECIDABLE` | 74 | `átri-` 46, `vená-` 19, `viśvā́mitra-` 7, `vāmádeva-` 1, `venā́-` 1 |
| `REGISTRY_HOLDS_TWO_ENTITIES_FOR_ONE_LEMMA` | 12 | `dadhikrā́-` 12 |

`DEVATA_OR_RISHI_UNDECIDABLE` is the same question ADR-013 defers for Ṛṣi lexical mention
and closes with it, not separately. `REGISTRY_HOLDS_TWO_ENTITIES_FOR_ONE_LEMMA` closes by
adjudicating our own registry rather than by reading the text.

**79 of the 711 are corroborated and still get no edge.** Each sits in a mantra whose
Anukramaṇī dedication is the very deity its alias proposes. That is recorded per row as
`anukramani_corroborated` and it is deliberately not treated as a resolution: a hymn
dedicated to the Waters is exactly where the ordinary noun "water" is most likely in its
ordinary sense, so the agreement is expected under both readings and discriminates neither.
The flag turns an undifferentiated 711 into a bounded, evidenced review queue; it does not
create a mention.

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

## Policy v2: two rules the audit forced

**A shared lemma id is necessary but not sufficient.** The annotators file a derived
stem under the base word's Grassmann entry: `índratama-` "most Indra-like" carries
`lemma_indra_1708`, `tákṣya-` "to be fashioned" carries `lemma_tArkzya_3741`. Matching
on the id alone therefore admits words that are not the name. Every match now also
requires the token's lemma *string* to be the alias's lemma, compared on the same
folded surface and split on the annotation's `~` alternants. This is not configurable
and no alias may opt out of it. Failure is `SUPPRESSED_LEMMA_MISMATCH`.

**An alias may state which readings of its lemma name the entity.** Optional
`allowed_pos`, `allowed_gender`, `allowed_number`, `allowed_case` and
`forbidden_features` are enforced against the annotation's own features. Constraints
are declared only where a lemma really is shared and the features really do separate
the readings; most aliases declare none, and an empty list means *unconstrained*, never
*nothing allowed*. A token carrying no value for a constrained feature fails closed.
Failure is `SUPPRESSED_FEATURE_CONSTRAINT`.

Both rules are properties of the annotation record. Neither consults the mantra's
meaning, its neighbours, its translation or its traditional metadata — that boundary is
unchanged from v1, and everything on the far side of it belongs to the semantic layer.

---

## Measured precision

Full method and sample in
[RIGVEDA_LEXICAL_MENTION_REVIEW.md](../reports/RIGVEDA_LEXICAL_MENTION_REVIEW.md).

The aliases were chosen on lexical grounds, so the annotation's **grammatical
gender** — which played no part in that choice — is independent evidence. A token
whose gender disagrees with the deity's is a candidate false positive.

| measure | value |
|---|---|
| mention token occurrences | 9,364 |
| off-gender occurrences (upper bound on detectable false positives) | 1 |
| **detectable false-positive rate** | **0.01%** |
| stratified review sample | 228 rows |
| tokens deliberately left ambiguous | 711 |

### What v2 removed

The v1 audit found 32 detectable false-positive occurrences. Every one whose class a
deterministic feature could separate is now excluded by a registry rule, not by
judgement about what a verse is about:

| entity | v1 | v2 | what the 32 actually were | rule |
|---|---|---|---|---|
| `VG:DEVATA:SURYAH` | 404 | 381 | 23 × `sūryā́-`, the Sun's daughter of RV 10.85 | gender + lemma string |
| `VG:DEVATA:MITRAH` | 328 | 325 | 3 × neuter `mitrá-` "alliance" | gender |
| `VG:DEVATA:INDRAH` | 2,438 | 2,435 | 3 × `índratama-` / `índravātatama-`, superlatives | lemma string |
| `VG:DEVATA:ADITIH` | 174 | 173 | 1 × masculine `áditi-` "unbound" | gender |
| `VG:DEVATA:ASVINAU` | 444 | 443 | 1 × neuter `aśvína-` "horse-team" | gender |
| `VG:DEVATA:TARKSYAH` | 3 | 2 | 1 × `tákṣyā`, gerundive of √takṣ | lemma string |
| `VG:DEVATA:DRAVINODAH` | 24 | 23 | 1 × adjective `draviṇodá-` | lemma string |
| `VG:DEVATA:MITRAVARUNAU` | 92 | 92 | 1 × `mitrā́váruṇau` tagged NOM DU **N** | **kept** |

Two of those classes gender could not have found. `índratama-` is a superlative that
agrees with whatever it qualifies, so it is masculine as often as feminine; the audit
caught two of its three occurrences by luck of agreement. `tákṣyā` was never reachable
by the gender audit at all. Both are excluded by the lemma-string rule instead, which
is why that rule is a default and not an opt-in.

The one remaining off-gender occurrence is kept deliberately. There is no neuter
appellative `mitrāvaruṇa-` for RV 10.93.6 to be, so gender supplies no discriminant
there; it is an annotation gender-tag anomaly, and suppressing it would be a guess
dressed as a rule. It is recorded in the registry notes rather than removed.

### What v2 recovered

`sárasvant-` is one annotated entry covering two deities, split 70 feminine / 5
masculine with no third reading. v1 deferred it for want of the mechanism, not for want
of evidence, and produced nothing. v2 accepts both readings under feature-conditioned
aliases: **+70** occurrences to `VG:DEVATA:SARASVATI`, **+5** to `VG:DEVATA:SARASVAN`.

The 23 `sūryā́-` occurrences were **not** reassigned. Removing them from Sūrya is
deterministic; deciding which entity they belong to is a registry merge question — the
nearest registered entity is the Anukramaṇī's compound label `sāvitrī sūryā` — and that
is not a lexical decision. They are held as a `NEEDS_REVIEW` alias producing no edges,
so the gap is visible rather than silent.

This is an upper bound on the classes gender can detect. It cannot detect an error
where deity and appellative share a gender, which is why the `DO_NOT_MATCH` rules
carry the cases where that would apply.

---

## Precision over recall

The layer covers 6,560 of 10,552 mantras. 3,992 mantras have no recognised mention.
That number is not a defect to be closed by loosening the policy. It reflects:

- 40 accepted aliases out of 214 registered Devatā entities;
- 22 deliberate suppressions;
- 11 unreviewed aliases producing nothing;
- Ṛṣi mentions not attempted at all.

If precision falls in a later review, the correct response is to **restrict the
unsafe alias classes, not to expand coverage.**
