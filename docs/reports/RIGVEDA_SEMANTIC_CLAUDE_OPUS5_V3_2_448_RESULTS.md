# Rigveda semantic V3.2 — Claude Opus 5 448 candidate run: results

> **NO HUMAN GOLD EXISTS.**
> **MODEL SELF-AGREEMENT IS NOT ACCURACY.**
> **CLAUDE OPUS 5 MODEL REVIEW IS NOT HUMAN GOLD.**
> **ALL SEMANTIC OUTPUTS REMAIN CANDIDATE KNOWLEDGE.**
> **50/448 PASSAGES LACK TRANSLATION ANCHOR COVERAGE UNDER THE CURRENT SEMANTIC CONTRACT.**

Run: `vedagraph-rigveda-semantic-claude-opus5-v3.2-448-new-v1`
Provenance bucket: `CLAUDE_OPUS5_MAX_MULTI_AGENT_CANDIDATE_EXTRACTION`
Model requested: `claude-opus-5` · Runtime: `CLAUDE_CODE_DIRECT` · Reasoning: `high`
Provider build metadata: `UNAVAILABLE` · Independent runtime attestation: `UNAVAILABLE`
Output seal: `cd45b1752cae62dd7d364d571235aa0db3c58ace8be829369dc9c013274465ec`

**Every number in this document is descriptive.** None is precision, recall, accuracy, or
agreement with a reference, because no reference exists. Prevalence is not correctness.

---

## 1. Two denominators

50 of the 448 EvidencePackets carry no translation text. The frozen binding contract
requires every assertion to anchor its `RELATION` — and where applicable `TARGET` /
`OUTCOME` — evidence to character spans of the packet translation. A packet without one
cannot emit an assertion in any of the fourteen families. Those 50 are
`STRUCTURAL_NO_TRANSLATION_ANCHOR`, **not** model omissions.

| Denominator | N | Use |
|---|---|---|
| All selected | **448** | operational metrics |
| Translation-bearing | **398** | **primary model-behaviour metrics** |
| Translationless | **50** | structural exclusion |

---

## 2. TRANSLATION_ANCHOR_COVERAGE

| Measure | Value |
|---|---|
| translation-bearing | **398** |
| translationless | **50** |
| percentage translationless | **11.16%** |
| assertion-capable under current contract | **398** |
| structurally no-claim under current contract | **50** |
| translationless that returned no-claim | **50 / 50 (100%)** |
| translationless that emitted assertions | **0** |
| **`TRANSLATABLE_PASSAGES_RETURNING_NO_CLAIM`** | **0** |

The correspondence is exact in both directions. No author fabricated a Sanskrit-only
anchor to bypass the contract, and **no translation-bearing passage was declined**. There
are therefore zero informative no-claims to investigate: every no-claim in this run is
structural.

Concentration: 38 of the 50 are in Mandala 1; M02, M03, M04, M06 and M07 have none.

---

## 3. Headline aggregates

| Metric | Value |
|---|---|
| total assertions | **2,459** |
| assertions / 448 (operational) | **5.4888** |
| assertions / 398 (model behaviour) | **6.1784** |
| no-claim count overall | 50 |
| no-claim rate overall (448) | **0.1116** |
| no-claim count, translation-bearing | **0** |
| no-claim rate, translation-bearing (398) | **0.0000** |
| no-claim count, translationless | 50 |
| structural no-translation count | 50 |
| EXPLICIT | 2,253 (91.6%) |
| STRONG_INFERENCE | 206 (8.4%) |
| INTERPRETIVE | 0 (prohibited by policy) |

---

## 4. Predicate distribution (N = 398 translation-bearing)

All fourteen families reported, including zeros.

| Predicate | Assertions | Passages | % of 398 | Avg / participating |
|---|---|---|---|---|
| DESCRIBES | 734 | 331 | 83.2% | 2.22 |
| DESCRIBES_ACTION | 553 | 273 | 68.6% | 2.03 |
| REQUESTS | 395 | 201 | 50.5% | 1.97 |
| INVOKES | 211 | 177 | 44.5% | 1.19 |
| REFERS_TO_PLACE | 122 | 106 | 26.6% | 1.15 |
| INVOLVES_SUBSTANCE | 117 | 102 | 25.6% | 1.15 |
| REFERS_TO_NATURAL_PHENOMENON | 100 | 76 | 19.1% | 1.32 |
| INVOLVES_RITUAL | 78 | 76 | 19.1% | 1.03 |
| PRAISES | 55 | 46 | 11.6% | 1.20 |
| INVOLVES_OFFERING | 46 | 46 | 11.6% | 1.00 |
| EXPRESSES | 27 | 26 | 6.5% | 1.04 |
| ASSOCIATED_WITH | 17 | 13 | 3.3% | 1.31 |
| CONTRASTS_WITH | 4 | 4 | 1.0% | 1.00 |
| **HAS_THEME** | **0** | **0** | **0.0%** | — |

No forbidden predicate (`SYMBOLIZES`, `REPRESENTS`, `IS_GOD_OF`, `MEANS`, `CAUSES`) was
emitted, and none was smuggled inside `ASSOCIATED_WITH`.

**Systemic-problem checks.** No predicate dominates: the most frequent, `DESCRIBES`,
appears in 83% of passages but averages only 2.22 per passage. There is no broad-predicate
explosion — the three review-sensitive families total 21 assertions, 0.85% of output.
`HAS_THEME` was never used, which is the conservative direction. `REQUESTS` splitting
averages 1.97 per participating passage, well short of the oversplitting failure mode.

---

## 5. Object-kind distribution (N = 398)

| Object kind | Assertions | Passages | % of assertions |
|---|---|---|---|
| EVENT | 554 | 273 | 22.5% |
| CANONICAL_ENTITY_REF | 471 | 186 | 19.2% |
| REQUESTED_OUTCOME | 395 | 201 | 16.1% |
| OPAQUE_REFERENT | 279 | 145 | 11.4% |
| SEMANTIC_ENTITY_REF | 182 | 113 | 7.4% |
| SUBSTANCE_REF | 117 | 102 | 4.8% |
| NATURAL_PHENOMENON_REF | 100 | 76 | 4.1% |
| OPAQUE_SPATIAL_REFERENT | 95 | 87 | 3.9% |
| ONTOLOGY_GAP_REF | 86 | 57 | 3.5% |
| RITUAL_EVENT | 78 | 76 | 3.2% |
| OFFERING_REF | 46 | 46 | 1.9% |
| PLACE_REF | 27 | 23 | 1.1% |
| STATE_REF | 16 | 16 | 0.7% |
| CONCEPT_REF | 10 | 9 | 0.4% |
| QUALITY_REF | 2 | 2 | 0.1% |
| ACTION_REF | 1 | 1 | 0.04% |

374 opaque referents (15.2%) is a substantial share. That is the policy working as
designed: where no supplied key resolves a referent, an opaque object is preferred to a
forced canonical identity.

---

## 6. Mandala distribution

| Mandala | Selected | Bearing | None | Assertions | / bearing | No-claim | NC rate (bearing) |
|---|---|---|---|---|---|---|---|
| M01 | 82 | 44 | 38 | 279 | 6.34 | 38 | 0.00 |
| M02 | 14 | 14 | 0 | 99 | 7.07 | 0 | 0.00 |
| M03 | 17 | 17 | 0 | 115 | 6.76 | 0 | 0.00 |
| M04 | 18 | 18 | 0 | 125 | 6.94 | 0 | 0.00 |
| M05 | 25 | 23 | 2 | 146 | 6.35 | 2 | 0.00 |
| M06 | 25 | 25 | 0 | 159 | 6.36 | 0 | 0.00 |
| M07 | 35 | 35 | 0 | 223 | 6.37 | 0 | 0.00 |
| M08 | 53 | 52 | 1 | 276 | 5.31 | 1 | 0.00 |
| M09 | 70 | 69 | 1 | 408 | 5.91 | 1 | 0.00 |
| M10 | 109 | 101 | 8 | 629 | 6.23 | 8 | 0.00 |

Normalised density spans 5.31 (M08) to 7.07 (M02) — a 1.33× range across ten Mandalas of
very different content. Described, not diagnosed: this is not evidence of a semantic
failure, and M02's higher figure rests on only 14 passages.

---

## 7. Duplicate QA

Two signatures, because they answer different questions. A **true** structural duplicate
requires the same predicate, object kind, entity, normalized head **and both evidence
spans** — the same claim from the same wording.

| Check | Count |
|---|---|
| exact duplicate groups | **0** |
| exact duplicate redundant assertions | **0** |
| duplicate canonical relation | **0** |
| duplicate REQUESTED_OUTCOME | **0** |
| duplicate substance relation | **0** |
| duplicate offering relation | **0** |
| duplicate place relation | **0** |
| duplicate predicate+object (other) | **0** |
| *same predicate+object, different evidence — groups* | *144* |
| *same predicate+object, different evidence — assertions* | *276* |

**There are zero structural duplicates.** The 144 groups are assertions about the same
object anchored to *different* wording, which V3.2 Rule 6 explicitly permits when distinct
typed roles or independently supported qualifiers are expressed. They are carried into the
review queue as an over-splitting signal, weighted low, and nothing was modified.

---

## 8. REQUESTS QA

| Measure | Value |
|---|---|
| total REQUESTS | 395 |
| passages containing REQUESTS | 201 |
| average per REQUESTS passage | 1.97 |
| maximum in one passage | 6 |
| passages with ≥ 2 | 109 |
| passages with ≥ 3 | 53 |
| passages with ≥ 5 | 10 |
| duplicate normalized outcomes | **0** |
| outcome anchor failures | **0** |
| high-split review candidates | 10 |

Every REQUESTS assertion carries its own `OUTCOME` anchor. A high split count is a review
candidate, never automatically invalid: the deep audit classified 52 of 61 reviewed
REQUESTS as `DIRECTLY_SUPPORTED` and the remaining 9 as granularity- or
predicate-ambiguous, with **zero unsupported**.

---

## 9. DESCRIBES / DESCRIBES_ACTION QA

| Measure | Value |
|---|---|
| DESCRIBES total | 734 |
| DESCRIBES_ACTION total | 553 |
| passages DESCRIBES only | 97 |
| passages ACTION only | 39 |
| passages with both | 234 |
| exact evidence-span overlap cases | **0** |
| partial span overlap (likely redundant) | **0** |
| distinct independently-supported cases | 234 |
| unresolved cases | **0** |
| action-head problems | **0** |
| relation-binding failures | **0** |

Rule 4 held cleanly. In all 234 passages carrying both predicates, no `DESCRIBES` shares
even a partially overlapping relation span with a `DESCRIBES_ACTION`. Every
`DESCRIBES_ACTION` object is a well-formed `EVENT` with a non-empty `action_head`.

---

## 10. Broad-predicate audit

All 21 broad-predicate assertions were enumerated with passage, object, both anchors and
explicitness in the manifest. Risk classification is engineering-only.

| Predicate | Count | Risk LOW | MEDIUM | HIGH |
|---|---|---|---|---|
| ASSOCIATED_WITH | 17 | 9 | 6 | 0 |
| CONTRASTS_WITH | 4 | 2 | 0 | 2 |
| HAS_THEME | **0** | — | — | — |
| **Total** | **21** (0.85% of assertions) | 11 | 8 | 2 |

The two HIGH cases are both `CONTRASTS_WITH` at `STRONG_INFERENCE`
(`RV 10.37.2`, `RV 10.46.5`). Both are in the review queue. Neither was removed.

There is no broad-predicate explosion and no `ASSOCIATED_WITH` synonym pile. Under model
review, 12 of 17 `ASSOCIATED_WITH` were `DIRECTLY_SUPPORTED` and 5 `PREDICATE_AMBIGUOUS`;
none unsupported.

---

## 11. Canonical target QA

| Measure | Value |
|---|---|
| canonical assertion count | 471 |
| canonical passages | 186 |
| unique canonical IDs | 26 |
| target failures | **0** |
| fabricated mentions | **0** |
| fabricated target anchor text | **0** |
| possible contradictions | **0** |
| blocker | **false** |

Every `CANONICAL_ENTITY_REF` names an entity supplied as a lexical mention in its own
packet; every `INVOKES` / `PRAISES` / `DESCRIBES` canonical assertion carries a distinct
`TARGET` anchor naming exactly that entity; no target anchor equals its relation anchor;
no anchor text is absent from the translation.

314 of 471 canonical references coincide with the passage's traditional Devatā assignment.
**This is descriptive only.** A traditional Devatā assignment is not semantic gold and was
never used to accept or reject an assertion. The remaining 157 are references to entities
other than the traditional Devatā, which is expected and correct.

**No canonical binding blocker exists.**

---

## 12. Ontology gap QA

| Measure | Value |
|---|---|
| ontology gap objects | 86 (in 57 passages) |
| anchor invalid | **0** |
| ontology expanded | **false** |
| opaque referents (separate) | 374 |

By code: `PERSON_LIKE_REFERENT_UNMODELED` 62, `ANCESTOR_ROLE_UNMODELED` 17,
`KINSHIP_ROLE_UNMODELED` 6, `PATRON_ROLE_UNMODELED` 1.

By classification: **`TRUE_SCHEMA_GAP` 86 / 86.** No gap was raised where a supplied
canonical mention could have resolved the referent, none was extraction overreach, and
none required an expert to classify as a gap. The ontology was **not** expanded.

This is a coherent, single-shaped finding: the gap is human/person-like referents —
patrons, ancestors, kin — which the current node-type vocabulary deliberately does not
model. It is a genuine schema question for a future ontology version, not a defect.

---

## 13. Parallel diagnostic (post-seal only)

Run only after the seal, using the deterministic exact/near-parallel infrastructure.

| Measure | Value |
|---|---|
| pairs evaluated | 8 (3 exact, 5 near) |
| cross-group pairs | 6 |
| SAME | 0 |
| PARTIAL | 1 |
| PREDICATE_DIFFERENCE | 4 |
| OBJECT_GRANULARITY | 3 |
| DIFFERENT | **0** |

**Statistical power is LOW** and this is stated rather than glossed: the 448 selection was
not drawn to maximise parallel coverage, so only 8 pairs have both members inside it. No
pair was fully divergent; every pair shared substantial structure. Equality was never
forced — parallel verses may legitimately be read differently, and parallel similarity is
diagnostic, never truth.

---

## 14. Cross-agent calibration (12 replicas, maximum permitted)

Selected **after** the seal, deterministically and stratified (two per author group; within
a group, the translation-bearing passages ranked by `sha256(passage_id)`, lowest two
taken). Selection did not look at any output. Every replica was authored by a **different**
group than the original, in an isolated context forbidden from reading the original.

Selection hash `ab46c9d04bc114b68a3a4fcaa62f72e1f6552bdaaf16b924ce3de7d467a8132f`.
Extra semantic tasks used: **12** (the stated maximum). Replicas never replace originals
and were never imported into the sealed run.

| Agreement measure | Value |
|---|---|
| no-claim agreement | **12 / 12 (100%)** |
| canonical-target agreement | **11 / 12 (91.7%)** |
| predicate-presence agreement (exact) | 5 / 12 |
| mean predicate-presence Jaccard | **0.832** |
| typed-object agreement | 5 / 12 |
| exact assertion-set agreement | 1 / 12 |
| mean assertions, original | 6.42 |
| mean assertions, replica | 5.83 |
| mean absolute assertion delta | **0.58** (≈9%) |

Disagreement classification:

| Class | Count |
|---|---|
| PREDICATE_BOUNDARY | 6 |
| EVIDENCE_VARIANCE | 3 |
| SAME | 1 |
| OBJECT_GRANULARITY | 1 |
| CANONICAL_TARGET_VARIANCE | 1 |
| **POSSIBLE_UNSUPPORTED_EXTRACTION** | **0** |
| UNRESOLVED | 0 |

**This is model self-agreement, not accuracy.**

The single `CANONICAL_TARGET_VARIANCE` (RV 10.10.14, the Yama–Yamī dialogue) is an
**omission, not a mis-binding**: the original emitted an `INVOKES` assertion targeting
`VG:DEVATA:YAMI`; the replica emitted no canonical target at all. The replica did not bind
a *conflicting* entity. Across all 12 replicas there are **zero contradictory canonical
bindings**.

The profile is a stable emission regime with local variation confined to predicate-boundary
and evidence-span choice — precisely the behaviour a healthy candidate generator is allowed
to have. Exact determinism was neither required nor observed.

---

## 15. Bounded deep audit (30 highest-risk cases)

30 highest-risk **translation-bearing** passages from the risk-ranked review queue, one
isolated reviewer per passage, packet read before output, reviewers instructed that the
authored output is the thing under review and not evidence for itself.

**This is Claude Opus 5 model review. It is NOT human gold. The proportion below may only
be called a `MODEL_ADJUDICATED_ENGINEERING_SUPPORT_RATE` — never precision.**

| Category | Count | Share |
|---|---|---|
| DIRECTLY_SUPPORTED | 197 | 84.9% |
| PREDICATE_AMBIGUOUS | 17 | 7.3% |
| OBJECT_GRANULARITY_AMBIGUOUS | 10 | 4.3% |
| SUPPORTED_BUT_REDUNDANT | 6 | 2.6% |
| WEAK_SUPPORT | 2 | 0.9% |
| **UNSUPPORTED** | **0** | **0.0%** |
| **EXPERT_REQUIRED** | **0** | **0.0%** |

| Flag | Count |
|---|---|
| fabricated evidence | **0** |
| wrong entity binding | **0** |

- passages reviewed: 30 · assertions reviewed: 232 · failed reviews: 0
- supported-or-ambiguous: **230 / 232 = 99.14%**

This ran on the *highest-risk* subset, not a random sample, which makes the absence of
unsupported extraction a stronger signal than the same result on an average slice.

The two `WEAK_SUPPORT` cases are both single-step over-reach, and both are recorded:

1. `RV 10.165.5` — `INVOLVES_RITUAL`: the packet names verses as an *instrument* of
   driving a bird away and never states an act of utterance, so reaching a
   `RITUAL_EVENT` of "recitation" requires an inferred recitation act.
2. `RV 8.43.32` — `REFERS_TO_NATURAL_PHENOMENON`: the darkness *is* named in the packet,
   but the assertion's only anchor is the verb already anchoring the `DESCRIBES_ACTION`,
   so the phenomenon relation is reachable only by stepping from that verb.

Both remain in the run, unmodified, and both are in the review backlog.

---

## 16. Review queue

- risk-ranked candidates found: **168**
- written to queue: **75** (the stated maximum)
- dropped beyond limit: **93** — stated explicitly rather than silently truncated
- path: `docs/manifests/rigveda_semantic_claude_opus5_v3_2_448_review_queue.jsonl`

Trigger counts across the written queue:

| Trigger | Passages |
|---|---|
| REPEATED_OBJECT_DIFFERENT_EVIDENCE | 139 |
| UNUSUALLY_DENSE | 29 |
| BROAD_PREDICATE | 17 |
| REQUESTS_HEAVY_SPLIT | 10 |
| RETRY_HEAVY | 2 |
| TRANSLATION_BEARING_NO_CLAIM | **0** |
| CANONICAL_TARGET_CONCERN | **0** |
| EXACT_DUPLICATE | **0** |
| DESCRIBES_ACTION_OVERLAP | **0** |
| ONTOLOGY_GAP (needing resolution) | **0** |

Every entry is `MODEL_REVIEW_CANDIDATE` with `human_gold: false`. The queue is a review
backlog, not a defect list: the four highest-severity triggers all have zero occurrences.

---

## 17. Status

| Property | Value |
|---|---|
| candidate status | `CANDIDATE / NEEDS_REVIEW` |
| human gold status | `UNANNOTATED` |
| unlocked predicates | `[]` (none) |
| canonical promotion | `false` |
| historical sources opened before seal | `false` |
| model self-agreement treated as accuracy | `false` |

Nothing in this run promotes any candidate to canonical knowledge, unlocks any predicate,
or creates any human gold.
