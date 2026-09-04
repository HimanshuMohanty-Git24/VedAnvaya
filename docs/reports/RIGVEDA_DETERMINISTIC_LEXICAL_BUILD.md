# Rigveda Deterministic Lexical Layer — Build Report

Manifest version: `vedagraph-rigveda-knowledge-deterministic-lexical-1.0.0-rc1`
Built: 2026-09-04 (timestamp injected; the build reads no clock)
Output: `data/knowledge/rigveda_lexical_v1` (reproducible, excluded from Git)

Reproduce with:

```bash
make lexical
```

---

## What this layer adds

Four predicates, on top of the traditional knowledge layer, which is unchanged:

| predicate | provenance | count |
|---|---|---|
| `MENTIONS_ENTITY` | `DETERMINISTIC_DERIVED` | 8,961 |
| `EXACT_PARALLEL_OF` | `DETERMINISTIC_DERIVED` | 256 |
| `PARALLEL_TO` | `DETERMINISTIC_DERIVED` | 69 |
| `HAS_COMPONENT` | `HUMAN_REVIEWED` | 28 |

`HAS_RISHI`, `HAS_DEVATA` and `HAS_CHANDAS` are untouched: 31,650 edges, same hashes.

No language model, embedding, classifier or network call was involved. Every input is
commit-pinned and hashed.

---

## Inputs

| input | pinned as |
|---|---|
| canonical corpus | `rigveda_full_v1`, manifest SHA256 in `manifest.json` |
| traditional knowledge layer | `rigveda_deterministic_v1`, manifest SHA256 recorded |
| morphology | `VEDAWEB.ZURICH` @ `d3eb8af7324338161520d2d35eae8f7e985a19a5`, CC BY 4.0 |
| morphology artifacts | 10 book TEI snapshots, per-file SHA256 in `data/derived/vedaweb_morphology_artifacts.json` |
| lexical alias registry | `data/registry/lexical_aliases.yaml`, SHA256 recorded |
| component registry | `data/registry/devata_components.yaml`, SHA256 recorded |

Source survey: [RIGVEDA_MORPHOLOGY_SOURCE.md](../architecture/RIGVEDA_MORPHOLOGY_SOURCE.md).
Decision: [RIGVEDA_MORPHOLOGY_DECISION.md](../architecture/RIGVEDA_MORPHOLOGY_DECISION.md).

---

## Token layer

| measure | value |
|---|---|
| mantras expected | 10,552 |
| **mantras with morphology** | **10,552 (100.00%)** |
| annotated tokens | 164,758 |
| tokens with a lemma | 164,758 (100.00%) |
| distinct lemmas | 9,785 |
| unaligned morphology records | **0** |
| duplicate token mappings | **0** |
| passage mismatches | **0** |
| stanza ids that failed to parse | **0** |
| token ids that failed to parse | **0** |

Alignment is structural: the stanza `xml:id` `b02_h001_01` states its Mandala, Sūkta and
mantra, so no token is placed by comparing text. No edition mapping table was needed.

Token identity is derived by UUIDv5 from a canonical URN and names the annotation layer,
because tokenization is a property of an edition:

```
VG:TOKEN:VEDAWEB-ZURICH:RV:SAK:M01:S001:V001:PA:T001
```

The mantra's own id is unaffected by which morphology source is chosen.

**The canonical Sanskrit was not modified.** `GRETIL.RV.AUFRECHT` remains the primary
text; the annotation's reading is stored separately as `surface_form`.

---

## Lexical aliases

| category | count |
|---|---|
| registry rows | 71 |
| accepted, mention-bearing | 38 |
| `DO_NOT_MATCH` suppressions | 22 |
| registered but `NEEDS_REVIEW` (produce nothing) | 11 |
| machine-proposed candidates still awaiting review | 0 |

Every row carries evidence and a review status. `DO_NOT_MATCH` is the single largest
contributor to precision: it suppresses `ká-` (interrogative pronoun, 468 occurrences),
`rátha-` ("chariot", 471), `hári-` ("bay steed", 271) and 19 others whose Anukramaṇī
labels happen to name a Devatā entity.

Full policy: [RIGVEDA_LEXICAL_MENTION_POLICY.md](../architecture/RIGVEDA_LEXICAL_MENTION_POLICY.md).

---

## MENTIONS_ENTITY

| measure | value |
|---|---|
| assertions | 8,961 |
| token occurrences | 9,322 |
| mantras with at least one mention | 6,531 (61.9%) |
| mantras with no recognised mention | 4,021 |
| tokens deliberately left ambiguous | 786 |
| match method | `LEMMA_ID_EXACT` — 9,322 of 9,322 |

**Every edge came from a stable Grassmann-linked lemma identifier.** No substring match,
no surface match and no fuzzy match contributed anything.

### Measured precision

The aliases were chosen on lexical grounds, so grammatical gender — which played no part
in that choice — is independent evidence.

| measure | value |
|---|---|
| off-gender occurrences | 32 / 9,322 |
| **detectable false-positive rate** | **0.34%** |
| stratified review sample | 228 rows |

Detail: [RIGVEDA_LEXICAL_MENTION_REVIEW.md](RIGVEDA_LEXICAL_MENTION_REVIEW.md).

### Traditional assignment vs lexical mention

The two diverge substantially, which is the point of separating them:

| entity | assigned | mentioned | both |
|---|---|---|---|
| `indraḥ` | 2,869 | 2,308 | 1,745 |
| `agniḥ` | 1,988 | 1,604 | 1,265 |
| `pavamānaḥ somaḥ` | 1,087 | 0 | 0 |
| `viśvedevāḥ` | 805 | 0 | 0 |
| `marutaḥ` | 428 | 401 | 207 |
| `varuṇaḥ` | 99 | 392 | 66 |
| `mitraḥ` | 10 | 320 | 10 |
| `pṛthivī` | 4 | 319 | 2 |

`pavamānaḥ somaḥ` is a two-word Anukramaṇī label with no single annotated lemma; those
mantras mention `somaḥ`, which the registry holds as a different entity. `mitraḥ` and
`varuṇaḥ` are usually *assigned* as the pair `mitrāvaruṇau` but *named* individually.

---

## Composite Devatā components

| status | rows |
|---|---|
| `ACCEPTED` → 28 `HAS_COMPONENT` edges | 14 |
| `NEEDS_REVIEW` (produce nothing) | 2 |
| `REJECTED` (recorded decisions) | 3 |

Accepted decompositions are dvandvas whose members are both separately registered
Devatās: `mitrāvaruṇau`, `indrāgnī`, `indrābṛhaspatī`, `indrāvāyū`, `indrāsomau`,
`somārudrau`, `somāvaruṇau`, `agnīṣomau`, `agnīndrau`, `indrāpūṣaṇau`, `somāpūṣaṇau`,
`indrābrahmaṇaspatī`, and the two hyphen-joined source labels `agniḥ-marutaḥ` and
`indraḥ-marutaḥ`.

`viśvedevāḥ`, `ādityāḥ` and `marutaḥ` are recorded `REJECTED`: a group deity is not
shorthand for the set of its members, and a plural ending is not evidence of
componenthood. `dyāvāpṛthivyau` is held at `NEEDS_REVIEW` because no canonical Dyaus
entity exists — half a decomposition is not a decomposition.

---

## Ṛṣi family structure

**`NO SUFFICIENT DETERMINISTIC SOURCE FOUND`.** No genealogy edges were created.

The pinned Anukramaṇī has exactly one seer field and no family, gotra, patronymic or
ancestor column. The lineage visible in labels such as `vaiśvāmitro madhucchandāḥ` is
carried by Sanskrit name grammar, not by data, and converting it into edges is the
inference this phase forbids.

The same finding scopes `MENTIONS_ENTITY` to Devatā only. See
[RIGVEDA_RISHI_STRUCTURE_FINDINGS.md](../architecture/RIGVEDA_RISHI_STRUCTURE_FINDINGS.md).

---

## Parallels

| measure | value |
|---|---|
| exact pairs | 256, in 389 groups across five levels |
| largest exact group | 14 mantras |
| cross-Mandala exact groups | 28 of 77 |
| candidate pairs scored | 148,092 (**0.27%** of all 55,687,476 pairs) |
| accepted `PARALLEL_TO` | 69 |
| candidates kept for review | 792 |
| oversized buckets skipped | 0 |

The largest group is the Viśvāmitra refrain shared by RV 3.30.22, 3.31.22, 3.32.17,
3.34.11, 3.35.11, 3.36.11, 3.38.10, 3.39.9, 3.43.8, 3.48.5, 3.49.5, 3.50.5, 10.89.18 and
10.104.11 — a known Rigvedic repetition, recovered without being looked for.

Recall was measured rather than assumed: all 613,278 pairs of Mandala 9 were brute-forced
and compared with what the banding proposed. The banding recovered 3/3 pairs the policy
would accept and 74/74 pairs worth keeping as candidates.

`LEMMA_SEQUENCE_EXACT` (250) is lower than `TOKEN_EXACT` (252) because the token and lemma
sequences come from the Zurich annotation (Lubotsky base text) while the source levels come
from GRETIL/Aufrecht. Two editions genuinely disagree on two pairs, and keeping the levels
separate is what made that visible.

Detail: [RIGVEDA_PARALLEL_REVIEW.md](RIGVEDA_PARALLEL_REVIEW.md).

---

## Co-occurrence

279 entity pairs, unit `MANTRA`, method `LEXICAL_MENTION_CO_OCCURRENCE`. Top pairs:
`indraḥ`+`somaḥ` (360), `mitraḥ`+`varuṇaḥ` (228), `agniḥ`+`indraḥ` (90).

This is an observation, not a relationship. No `RELATED_TO` or `CO_OCCURS_WITH` edge is
created from it.

## Mentions by Mandala

| Mandala | mantras | with mentions | edges | token occurrences |
|---|---|---|---|---|
| 1 | 2,006 | 1,290 | 1,744 | 1,809 |
| 2 | 429 | 295 | 410 | 417 |
| 3 | 617 | 453 | 617 | 645 |
| 4 | 589 | 366 | 511 | 527 |
| 5 | 727 | 504 | 701 | 724 |
| 6 | 765 | 501 | 651 | 696 |
| 7 | 841 | 587 | 847 | 866 |
| 8 | 1,716 | 982 | 1,269 | 1,335 |
| 9 | 1,108 | 559 | 796 | 809 |
| 10 | 1,754 | 994 | 1,415 | 1,494 |

Mandala 9's lower density is expected: it is the Soma Pavamāna book, whose mantras are
*assigned* to `pavamānaḥ somaḥ` but lexically name `sóma-`.

---

## Performance

Full build, single process, no parallelism:

| stage | seconds |
|---|---|
| morphology parse (10 book TEIs, 164,758 tokens) | 38.5 |
| token build and alignment | 0.8 |
| mention extraction | 5.7 |
| component loading | 0.0 |
| parallels (exact + candidate generation + scoring) | 130.1 |
| analytics | 0.7 |
| **total** | **175.8** |

Peak memory is bounded by holding all tokens in memory (~165k records). The morphology
parser streams each TEI with `iterparse` and clears as it goes rather than loading a
40 MB document.

No O(n²) pass exists. Brute-forcing one Mandala took 405 s; brute-forcing the corpus
would take roughly an hour.

---

## Quality gates

| gate | result |
|---|---|
| `ruff format --check` | clean |
| `ruff check` | clean |
| `mypy --strict` | clean |
| `pytest` | all passing |
| QA errors | **0** |
| QA warnings | **0** |
| reproducibility | rebuild is byte-identical (asserted in tests) |

The one QA issue raised is `LEXICAL_ALIAS_UNREVIEWED` at severity `INFO`: 11 registered
aliases are deliberately not `ACCEPTED` and produce nothing.

---

## Known limitations

Carried deliberately, each with a recorded reason:

1. **Sarasvatī produces no mentions.** The annotation lemmatises every Sarasvatī form
   under the vant-stem `sárasvant-`, shared with the masculine Sarasvant. They are
   separable by the annotation's own gender feature, but v1 has no feature-conditioned
   alias mechanism. Highest-value item to fix.
2. **No Ṛṣi mentions**, for the source reason above.
3. **786 tokens left ambiguous** — `áp-`, `yamá-`, `mr̥tyú-`, `vená-`, `dadhikrā́-`.
4. **38 accepted aliases of 214 Devatā entities.** Coverage is partial by design.
5. **`sū́rya-` carries 23 feminine occurrences** (`sūryā́-`, RV 10.85), arguably a
   distinct entity. The clearest candidate for an entity split.
6. **Near parallels are pairwise only.** No transitive clustering into parallel families.
7. **Pāda-level parallels are not implemented**, though the schema and token pāda tags
   make them possible without re-identifying anything.
