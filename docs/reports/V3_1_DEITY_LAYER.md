# The deity layer at V3.1: referent certainty, the ambiguity contract, profiles, composition

**Agent.** `AGENT_C_DEITY`. **Runtime.** `CLAUDE_CODE_DIRECT`, `claude-opus-5`.
**Branch.** `semantic-pilot-v1`, from `d456cce`.
**Write partition.** `MENTIONS_DEVATA` edge properties, `Devata`, `DeityGroup`, `DeityAxis`,
`Epithet`, `COMPOSED_OF`, `HAS_AXIS`, `HAS_EPITHET`, plus the one new type in §7.
No human has reviewed any artifact described here.

---

## 1. Headline

| | before | after |
|---|---|---|
| `DEITY_CERTAIN` | 8,340 | **8,340** (unchanged, deliberately) |
| `DEITY_PROBABLE` | — (did not exist) | **2,019** |
| `DEITY_AMBIGUOUS` | 8,825 | **6,806** |
| total | 17,165 | **17,165** |
| ambiguous share of the layer | **51.4%** | **39.6%** |
| default-scope share of the layer | 48.6% | **60.3%** |

Measured against the 391 asserted, scorable rows of
`data/gold/theonym_mention_gold_v1.jsonl` joined to the live graph:

| tier | edges | gold n | precision | 95% Wilson |
|---|---|---|---|---|
| `DEITY_CERTAIN` | 8,340 | 139 | 0.9712 | 0.9283–0.9888 |
| **`DEITY_PROBABLE`** | **2,019** | **55** | **0.9818** | **0.9039–0.9968** |
| `DEITY_AMBIGUOUS` | 6,806 | 197 | 0.6142 | 0.5447–0.6794 |
| **default scope (C+P)** | **10,359** | **194** | **0.9742** | 0.9411–0.9889 |
| unfiltered, for comparison | 17,165 | 391 | 0.7928 | 0.7499–0.8301 |

**`PROBABLE` measures level with `CERTAIN` and that is reported, not hidden.** On 55 rows
the two intervals overlap almost completely and the sample cannot distinguish 0.97 from
0.98. The tier is still ranked below `CERTAIN` because it is named for the *kind* of
evidence behind it — an unobserved case label, or a second source's ascription rather than
the word itself — and that ordering is a priori, not fitted. See §3 for what the gold set
does and does not support.

**Worst alias in the `PROBABLE` bucket: `sūrya` for `VG:DEVATA:SURYAH`, 0.6667 (2/3),
Wilson 0.21–0.94, 71 live edges.** Named in full in §4.

---

## 2. The split: what promotes a row, and what was refused

Implemented as `vedagraph.domain.theonyms.refine_referent_certainty`, a pure function of
properties already on the edge. Nothing re-derives the mention layer and nothing consults a
new source: V3 measured detection at 0.9949 on *which word* and the failure is *which
sense*, so this is consumption semantics over existing evidence.

**The rule.** A row is promoted only on an **independent positive indication that the
personal referent is meant** — never on lemma or string identity, which is the very
evidence that produced the ambiguity.

| rule | evidence | live edges | gold precision |
|---|---|---|---|
| `R1_anukramani_corroboration` | `attribution_support = true`: the Anukramaṇī independently ascribes this passage to this deity | 907 | 1.0000 (8/8) |
| `R2_address_morphology` | `morphological_roles` contains `VOCATIVE`/`VOC`: a vocative is an address, and one addresses a being | 808 | 0.9737 (37/38) |
| `R3_dedication_morphology` | `morphological_roles` contains `DATIVE`/`DAT`: the beneficiary of an offering, and a substance is not a beneficiary | 304 | 1.0000 (9/9) |
| `compound_internal_hold` | veto: `COMPOUND_INITIAL`/`COMPOUND_FINAL` outranks R1–R3, because a compound need not denote its members | 383 held | 0.5789 (11/19) |
| `identity_only` | held at `AMBIGUOUS` | 6,423 | 0.6180 (110/178) |
| `certain` | passed through untouched | 8,340 | 0.9712 (135/139) |

The compound veto only changes the outcome of **6** edges (377 of the 383 were heading to
`AMBIGUOUS` anyway), so it is a near-free guard against a named error class rather than a
load-bearing rule.

### Signals considered and refused, with the measurement that refused them

| candidate | gold precision | why refused |
|---|---|---|
| `NOMINATIVE` role | 0.8571 (24/28) | not an indication of *personhood* — a nominative Soma is exactly "the soma flows" |
| `SANDHI_FUSED` role | 0.8000 (20/25) | same |
| `extraction_path = rv-lemma-annotation` | **0.5745 (27/47)** | **the weakest signal measured** — see below |
| registry `precision_estimate` per form | — | measures *detection*, not sense: `āpaḥ` carries 0.97 and the gold scores that deity's sense at 0.2500 |
| form-level `referent_certainty` | — | uniformly `DEITY_AMBIGUOUS` for every homonym deity; carries no information the deity level does not |

**The brief's own hypothesis was disproven by measurement and is worth stating plainly.**
The task expected `rv-lemma-annotation` to be "far stronger than surface token matches".
Inside the ambiguous bucket it is the *weakest* signal available, at 0.5745 against the
surface path's 0.7092. The mechanism: `_grade` had already taken every Rigvedic vocative
into `CERTAIN`, so what remains on the annotated path is pure oblique-case homonym
residue, while the surface path still had its vocative-labelled forms in the bucket.
Promoting the annotated path as a class would have been the intuitive move and would have
landed 4,384 edges at 0.57.

---

## 3. `DEITY_CERTAIN` was a proxy for "is Rigvedic" — measured per deity

This was raised mid-session by the independent benchmark diagnosis
(`V3_1_MISLEADING_DIAGNOSIS.md`, fix 1 in §C2) and it is confirmed exactly.

`_grade` returns `CERTAIN` outside the Rigveda **only** when the deity's name is not also a
common noun, and only the Rigveda has the annotation that can settle a homonym. So of the
2,440 non-Rigvedic `DEITY_CERTAIN` edges, **zero** belong to any of the ten deities the
diagnosis names. They belong entirely to the seventeen non-homonym deities:

```
INDRAH 1261 · BRHASPATIH 197 · VARUNAH 197 · PITARAH 168 · MARUTAH 159 · VISNUH 127
ADITIH 75 · TVASTA 73 · INDRAGNI 64 · MITRAVARUNAU 60 · BRAHMANASPATIH 22
PARJANYAH 15 · MRTYUH 9 · INDRAVAYU 6 · VISVEDEVAH 5 · APAM-NAPAT 1 · ARANYANI 1
AGNIH 0 · SOMAH 0 · SURYAH 0 · MITRAH 0 · SAVITA 0 · USAH 0 · VAYUH 0 · APAH 0
PRTHIVI 0 · VAK 0
```

The non-RV `CERTAIN` edges are therefore **real, not an artifact** — they are exactly the
deities whose names cannot be misread — and the aggregate hid the per-deity zeros, as
warned. `CERTAIN` was widened by **nothing**: it is 8,340 before and after.

### The ten named deities, per Veda, `CERTAIN / PROBABLE / AMBIGUOUS`

| deity | RV | SV | YV | AV | non-RV default scope: before → after |
|---|---|---|---|---|---|
| Agni | 831/528/245 | 0/**82**/105 | 0/**97**/179 | 0/**170**/306 | 0 → **349** |
| Soma | 240/22/688 | 0/**97**/116 | 0/**36**/109 | 0/**26**/178 | 0 → **159** |
| Sūrya | 21/28/329 | 0/**14**/41 | 0/**21**/69 | 0/**51**/125 | 0 → **86** |
| Mitra | 37/29/254 | 0/**5**/22 | 0/**5**/26 | 0/**10**/40 | 0 → **20** |
| Savitṛ | 23/61/91 | 0/**1**/10 | 0/**14**/107 | 0/**13**/99 | 0 → **28** |
| Uṣas | 69/68/216 | 0/**2**/18 | 0/0/14 | 0/**3**/28 | 0 → **5** (YV still zero) |
| Vāyu | 43/28/61 | 0/**7**/8 | 0/**15**/30 | 0/**10**/37 | 0 → **32** |
| Pṛthivī | 18/6/295 | 0/0/26 | 0/**18**/103 | 0/**19**/227 | 0 → **37** (SV still zero) |
| Āpaḥ | 18/25/482 | 0/0/27 | 0/0/29 | 0/0/180 | 0 → **0** |
| Vāc | 0/3/124 | 0/0/25 | 0/0/47 | 0/0/103 | 0 → **0** |

**Eight of the ten are fixed in all three unannotated corpora.** Uṣas gains SV and AV but
not YV; Pṛthivī gains YV and AV but not SV. **Āpaḥ and Vāc are not fixed and must not be.**
Gold scores Āpaḥ at 0.2500 and Vāc at **0.0000 on ten asserted rows** — for those two, a
zero in the default scope is the *correct* result, and inflating `CERTAIN` to make the
table look complete would have been the one move this session exists to prevent.

### The residual is typed, not printed as a zero

`vedagraph.domain.theonyms.mention_verdict` returns one of three states, and every profile
carries it per Veda as `profile_mention_verdict_by_veda`:

- **`ATTESTED`** — the default scope has evidence; return the count.
- **`INSUFFICIENT_EVIDENCE`** — the deity is named in this slice and no mention reaches the
  default scope. A statement about the *evidence*, never rendered as `0`. The ambiguous
  count travels beside it so a caller can see how much is withheld and ask for
  exploratory mode.
- **`NOT_IN_LAYER`** — no mention at any tier. Still not "absent from the corpus": the
  layer's measured recall is 0.8857.

**21 (deity, Veda) cells corpus-wide are `INSUFFICIENT_EVIDENCE`.** In full, so nobody has
to rediscover them:

```
APAH AV 180 · VAK AV 103 · PURUSAH AV 60 · VAK YV 47 · NIRRTIH AV 39 · APAH YV 29
APAH SV 27 · PRTHIVI SV 26 · VAK SV 25 · PURUSAH YV 15 · USAH YV 14 · YAMAH SV 12
PAVAMANAH-SOMAH AV 11 · ADITYAH SV 7 · DYAVAPRTHIVYAU SV 6 · PURUSAH SV 4
SARASVATI SV 3 · VISVAKARMA SV 2 · AHIH SV 1 · AHIH YV 1 · RATRIH SV 1
```
(the figure is the ambiguous-only mention count in that cell)

---

## 4. Per-alias audit — the worst alias, named

This graph has been embarrassed by an audit that sampled rows and reported 97%+ while one
alias was 82.9% wrong, so the average is not the finding.

**`PROBABLE` bucket, every alias with any gold support, worst first:**

| deity | alias | precision | n | 95% Wilson | live edges |
|---|---|---|---|---|---|
| **SURYAH** | **`sūrya`** | **0.6667** | **3** | **0.21–0.94** | **71** |
| AGNIH | `agne` | 1.0000 | 10 | 0.72–1.00 | 273 |
| SOMAH | `soma` | 1.0000 | 6 | 0.61–1.00 | 142 |
| PAVAMANAH-SOMAH | `pavamāna` | 1.0000 | 5 | 0.57–1.00 | 38 |
| AGNIH | `agna` | 1.0000 | 4 | 0.51–1.00 | 43 |

Twenty-three further aliases score 1.0000 on 1–2 rows each and are **unmeasured, not
vindicated**: at n≤2 the Wilson lower bound is 0.34 or worse.

**The worst alias is the one the layer's own docstring predicted.**
`theonyms.py::_grade` records that the share of a form's tokens which are pre-consonantal,
and therefore certainly vocative rather than a sandhi-reduced nominative, "runs from
effectively 100% for `agne` down to **47% for `sūrya`**". The single false positive in the
entire `PROBABLE` gold slice is `TMG-0427`, SV UTTARA 1.2.16.2, `ayaṃ sūrya ivopadṛg`
"this one, like the sun in appearance" — where, as the gold row's own reasoning states,
"the recorded role `VOCATIVE` is wrong: `sūrya iva` is sandhi-reduced NOMINATIVE `sūryaḥ`
+ `iva`". The per-alias audit and the module's own warning point at the same 71 edges.

**This is the layer's largest single unresolved exposure and it is not closed.** Closing it
needs the per-form pre-consonantal share, which is measured in the docstring but is not a
property of any edge or registry row, so it cannot be filtered on. Spec in §8, item 4.

**`AMBIGUOUS` bucket, worst aliases (n≥3) — what the default correctly keeps out:**
`RUDRAH/rudrā` 0.0000 (3) · `SOMAH/somaṃṃ` 0.0000 (3) · `VAK/vāco` 0.0000 (3) ·
`APAH/apā́m` 0.2000 (5) · `SOMAH/sómasya` 0.3333 (3) · `PRTHIVI/pṛthivyā́` 0.4000 (5).

---

## 5. The seven ordinary-noun deities

| deity | total | C | P | A | gold on C | gold on P | gold on A |
|---|---|---|---|---|---|---|---|
| Agni | 2,543 | 831 | **877** | 835 | 9/9 | **18/18** | 17/19 |
| Soma | 1,512 | 240 | **181** | 1,091 | 7/7 | **8/8** | 9/22 |
| Āpaḥ | 761 | 18 | 25 | 718 | — | — | 4/16 |
| Pṛthivī | 712 | 18 | 43 | 651 | 1/1 | — | 8/14 |
| Vāc | 302 | **0** | **3** | 299 | — | — | **0/10** |
| Sarasvatī | 213 | 18 | 47 | 148 | 1/1 | 3/3 | 5/5 |
| Sūrya | 699 | 21 | 114 | 564 | — | 3/4 | 10/14 |

- **Agni** is the clean win: 877 edges promoted, 18/18 on gold, and the wrong zeros for
  SV/YV/AV are gone. Benchmark **Q46** and **Q88** turn on this row.
- **Soma** promotes 181 at 8/8 and leaves 1,091 ambiguous at 0.4091 — the Jamison–Brereton
  "Soma"/"soma" distinction, correctly still undecided where nothing decides it. **Q45**,
  **Q87**.
- **Āpaḥ** promotes 25 (all Rigvedic, all by Anukramaṇī corroboration) and **nothing
  outside the Rigveda**: no non-RV Āpaḥ edge carries an address or dedication role. Given
  0.2500 measured, `INSUFFICIENT_EVIDENCE` is the right answer, not a count.
- **Pṛthivī** promotes 43; SV remains `INSUFFICIENT_EVIDENCE` on 26 mentions.
- **Vāc** — the gold set's largest single finding — is contained: **3 of 302** edges reach
  the default scope, and all three are Rigvedic. On the ten gold rows, the default scope
  admits **none**, which a test pins (`test_the_default_policy_excludes_the_vak_bucket`).
  **Q89** stays PARTIAL: the field now decides for 3 rows and declines for 299, which is
  the honest state, not a solved one.
- **Sarasvatī** promotes 47 at 3/3, and gold scores the whole `GEOGRAPHIC_HOMONYM` class
  **9/9**. See §6 on **Q85**.
- **Sūrya** promotes 114 and carries the worst alias.

---

## 6. Benchmark questions in this partition

| Q | state | what this work does |
|---|---|---|
| **45, 87** | addressed | three-way certainty driven by context (role + independent ascription), not by extraction path; per-deity accuracy published below and in §5. `theonym_ambiguous` retirement is **not** mine — it is on `MENTIONS_ENTITY`, outside the partition; spec in §8. |
| **46, 88** | addressed | the two-value field is now three-valued; Agni's SV/YV/AV zeros are gone (§3). A `RITUAL_MEDIUM` sense value is **not** delivered and is not derivable from edge evidence — reported unstarted. |
| **43, 70** | hazard removed | the cautious path no longer re-zeroes Rudra outside the RV: Rudra now has SV/YV/AV `PROBABLE` 51 edges, verdict `ATTESTED` in all four Vedas. |
| **86** | **resolved for the named failure** | see below. |
| **85** | **partly refuted, partly outside partition** | see below. |
| **38** | unblocked, not closed | `is_composite` and `component_count` are now correct on all 214 nodes (§7), which is the exclusion predicate Q38 needs. Excluding composites from the leaderboard is a query change — §8. |
| **3** | addressed | `profile_top_concepts_strict` is now landed beside `profile_top_concepts`, computed over `attribution_precision = PER_PASSAGE` only, so the reader can see both bases. |
| **92** | not started | `Devata`↔`Object` lift needs `DomainEntity`, which is outside the write partition. Spec in §8. |
| **52** | not started | per-occurrence axes; the action layer is RV-only, so it cannot be done honestly yet. |
| **26** | partly | the certainty side is done; routing `sarasvatī` to both senses is `MENTIONS_ENTITY`/`DomainEntity`. |

### Q86 — resolved for the named failure, with two honest residuals

`DEVATA_ASSOCIATED_WITH` reported "fire (agni)" with **five** personifications: `Agni`,
`Agni Jātavedas`, `Agni Pavamāna`, `Agni the slayer of demons`, `the self of Agni`. The
cause is not a bug: the Anukramaṇī's devatā slot records the *qualified* label a hymn uses,
the registry correctly pins each distinct slot value as its own entity because `entity_key`
is pinned identity, and nothing then said four of the five are one god. A count of
personifications was counting labels.

`data/registry/devata_variants.yaml` states the label relation for each; `EPITHET_VARIANT_OF`
projects it, `TIER_C`/`L3_LLM_EXTRACTED`, 6 edges. Measured after:

| phenomenon | labels | distinct bases |
|---|---|---|
| fire (agni) | 5 | **1** |
| soma juice (soma) | 3 | **2** |
| speech (vāc) | 3 | **2** |

With composites additionally excluded by `structure = 'INDIVIDUAL'` (the query change in
§8), fire → 1, earth → 1, speech → 1, dawn → 1, soma → 2, sun → 3.

**Three rows are `REFUSED` and create nothing, and the refusals are the point.**
`sāvitrī sūryā` is Sūryā the daughter of Savitṛ, a feminine figure who marries the Aśvins —
her label differs from `sūryaḥ` in *gender*, not by a qualifier, so identifying them would
be a claim about mythology that a shared substring invited. `ahirbudhnyaḥ`, the serpent of
the deep, is a distinct figure. `pavamānaḥ` alone is refused **on the evidence rule, not on
the reading**: it almost certainly means Soma, but the label contains no form of `somaḥ`,
and `theonym_forms.yaml` records that the same form means wind, breath and an abstract
purifier in the Atharvaveda. Residual: "soma" therefore still shows 2 bases and "sun" 3.
Number variants (`gauḥ`/`gāvaḥ`, `aśvaḥ`/`aśvāḥ`/`vājinaḥ`) are recorded `NOT_IN_SCOPE`:
whether a deified plural collective is the same devatā as its singular is a decision this
work does not make. `the bow` / `the arrows` / `the quiver` are **not** duplicates at all —
the diagnosis groups them with the epithet cases, and a bow is not an epithet of a quiver.

### Q85 — the diagnosis's reading is not supported by the only measurement in the repository

The diagnosis grades Q85 MISLEADING on the ground that a researcher reads "Sarasvatī is
essentially always the goddess and essentially never the river". That reading may be
**correct for this corpus**, and there is a measurement: the gold set's
`GEOGRAPHIC_HOMONYM` class — which is Sarasvatī and nothing else — scores **1.0000 on 9
rows, precision and recall both**, and the gold report states the mechanism: "the feared
river-versus-goddess confusion did not appear once, because in this corpus `sarasvatī` is
almost always accompanied by `devī` or a vocative". After the split, 65 of 213 Sarasvatī
edges are in the default scope and 3/3 of the promoted gold rows are the goddess.

So the defect in Q85 is **not** that the deity reading is wrong. It is (a) that the river
node is starved because the mention layer never routes a token to both senses, which is
`MENTIONS_ENTITY`/`DomainEntity` and outside this partition, and (b) that no accuracy
figure travels in the row. This report supplies (b) as a citable figure. **I am not
"fixing" Q85 by inflating the river against the only evidence available.** If a reviewer
wants the river routed, that is `AGENT_D`'s generic-noun flag plus a mention-layer
precedence change, and it should be done against a gold sample of hydronym occurrences that
does not yet exist.

---

## 7. Composition: `is_composite`, and the two named cases

### The MITRAVARUNAU contradiction — there are two, and only one was open

**(a) Registry-level, already resolved before this session.** `devatas.yaml` says
`mitrāvaruṇau` is "a dual that is deliberately not decomposed into Mitra and Varuṇa";
`devata_components.yaml` carries an `ACCEPTED` row decomposing it. The V2 taxonomy overlay
found this, recorded it verbatim in its `curation_note`, and resolved it by following the
component file "because that file is the reviewed authority for componenthood". Verified
live: that resolution is in the graph.

**(b) Live and open: the flag contradicted the edges.** 14 `Devata` nodes carry
`COMPOSED_OF` edges, and **every one of them carried `is_composite = false`. So did the
other 200: 0 of 214 deities were flagged composite while 14 were decomposed.** The graph
simultaneously stated that `VG:DEVATA:MITRAVARUNAU` *is* Mitra and Varuṇa and that it is
not a compound, and "which deities are compounds?" returned nothing at all.

The cause is that `is_composite` comes from `is_composite_label`, a deliberate label-shape
heuristic that looks for the editors' hyphen and documents that it will *not* recognise a
dual such as `mitrāvaruṇau` because that needs morphology. Right for a label heuristic,
wrong as the property's final value — a reviewed decomposition is exactly the evidence the
heuristic said it was waiting for.

`v3_loader.reconcile_devata_composition` derives the flag from the reviewed edges.
**After: 14 true, 200 false, 0 contradictions, `component_count` on all 214.** `false` is
written explicitly, because the registry records `VISVEDEVAH` as `REJECTED` and
`DYAVAPRTHIVYAU` as `NEEDS_REVIEW`, and an absent property would make a decision look like
an oversight.

**A third finding, new: `COMPOSED_OF` is not projected from the reviewed authority.** It is
projected from a *second copy* of the same data — the `composed_of` field of
`data/domain/vedagraph_domain_v2/devata_taxonomy.yaml`, maintained by hand. Two files
holding one fact means a row can be added to the authority and never reach the graph with
every loader reporting success. The reconciler now diffs the two and reports
`registry_only` / `graph_only` / `component_set_differs` in its load report. It deliberately
does **not** MERGE from the registry: creating the edge there would make it a *third*
decomposition authority, and there are already two too many.

### INDRAVARUNAU — staged with its evidence, not forged

`devata_components.yaml` had **no row at all** for `VG:DEVATA:INDRAVARUNAU`, and the V2
overlay had already recorded that as prose: "a notable gap rather than an oversight … its
policy forbids inferring a decomposition from a dual ending, so `composed_of` is empty and
the missing row is reported instead of quietly filled in".

A row now exists. Its evidence is this file's **own stated criterion for the dvandva
block** — not the dual ending — checked against the graph:

1. `indrāvaruṇau` is the nominative dual of the devatā-dvandva `indrā́váruṇa-`.
2. Both members exist as separately registered canonical Devatā entities.
3. The Anukramaṇī separately assigns the pair **and** each member: 70 mantras to the pair,
   2,869 to Indra, 99 to Varuṇa.
4. The pair is the seventeenth most frequently assigned devatā in the corpus.

**It is staged `NEEDS_REVIEW` and creates no edge, and that is deliberate.** `ACCEPTED` in
this file carries `provenance_class: HUMAN_REVIEWED` — `models/lexical.py` raises on a
`ComponentAssertion` that claims otherwise — and this row was assembled by a model run.
Marking it `ACCEPTED` would forge the one property the whole file exists to guarantee. What
is resolved is the **evidence**, not the review. A reviewer who agrees flips one field and
adds the same two components to the taxonomy overlay's `composed_of`; nothing else changes.

### Left undecomposed, and why

**24 `PAIR` and 33 `GROUP` deities have no `COMPOSED_OF` edge.** Nothing was added for any
of them. Three classes:

- **Recorded refusals** — `VISVEDEVAH` (`REJECTED`: a collective, not an abbreviation for
  every registered deity), `ADITYAH` (`REJECTED`: membership varies between passages and no
  source in this repository fixes the list), `MARUTAH` (`REJECTED`: a plural is not a
  compound).
- **Recorded holds** — `DYAVAPRTHIVYAU` (`NEEDS_REVIEW`: Dyaus is not a registered entity,
  and "half a decomposition is not a decomposition"), `USASANAKTA` (`NEEDS_REVIEW`:
  equating the compound's `náktā-` with the registry's `rātriḥ` is an identification across
  two words, not a decomposition).
- **Silent** — the rest, e.g. `INDRAVISNU`, `INDROSASAU`, `INDRAPARVATAU`, `SOMARKAU`,
  `DYAVABHUMI`, `PRTHIVYANTARIKSE`, `VAK-APAH`, `DAMPATI`, `SUNASIRAU`, `INDRASYASVAU`,
  `SARAMEYAU-SVANAU`, `ULUKHALAMUSALE`.

**A dual compound is not automatically decomposable because its name looks like two names
joined**, and `INDRASYASVAU` is the standing counterexample: it is "Indra's horses", a
genitive plus a noun, not a dvandva of Indra and a horse. Applying the criterion to the
silent set requires per-name segmentation, which is itself interpretation, so the set is
reported and left alone. Doing it properly means one staged row per case with its four
checks recorded, as INDRAVARUNAU now is.

---

## 8. The default ambiguity policy, as a contract

Stated in code as `vedagraph.domain.theonyms.referent_tiers_for_mode` and the three
frozensets beside it. An unknown mode **raises** rather than falling back to the widest
set, because a typo silently widening a filter is how an ambiguous row reaches a user as a
fact.

| mode | tiers | measured precision | share of layer | when |
|---|---|---|---|---|
| `strict` | `CERTAIN` | 0.9712 | 48.6% | one wrong row costs more than a missing one — **but read §3 first: this mode returns wrong zeros for every homonym deity outside the Rigveda, and that is a property of the tier, not of the corpus** |
| **`default`** | `CERTAIN` + `PROBABLE` | **0.9742** | **60.3%** | **the product default for all deity analytics** |
| `exploratory` | all three | 0.7928 | 100% | candidate generation only, never an answer presented as fact |

Four binding clauses:

1. **Every deity answer reports three figures, never one.** `certain_mentions`,
   `probable_mentions`, `ambiguous_mentions`, and they sum to the mention count. Landed as
   `profile_mentions_certain` / `_probable` / `_ambiguous`, per Veda in
   `profile_mentions_by_veda_certainty`, and pinned by
   `test_every_asserted_gold_row_lands_in_exactly_one_tier`.
2. **A zero in the default scope is never printed as a count.** It is
   `INSUFFICIENT_EVIDENCE` when mentions exist at any tier and `NOT_IN_LAYER` when they do
   not. 21 cells are currently `INSUFFICIENT_EVIDENCE` (§3).
3. **Precision is quoted as the Wilson lower bound, not the point estimate.**
   `PROBABLE` is a **0.90 lower bound** on 55 rows, not "0.98". Pinned by
   `test_probable_is_not_claimed_more_precisely_than_the_gold_set_supports`.
4. **Per-alias, not per-average.** Pinned by
   `test_the_probable_bucket_is_audited_per_alias_not_on_average`, and the worst alias is
   named in §4 rather than averaged away.

### What the gold set cannot support, stated

The `PROBABLE` bucket rests on **55 gold rows**, which gives a Wilson interval of
0.9039–0.9968 — nine points wide. That supports "at least 0.90" and does **not** support
distinguishing `PROBABLE` from `CERTAIN`, or certifying any single alias. Per rule, `R1`
has 8 rows and `R3` has 9: both measure 1.0000 and neither can be claimed above 0.68 and
0.70 respectively. **To claim `PROBABLE ≥ 0.95` at 95% confidence would need roughly 120
`PROBABLE` rows at the observed rate; to certify `sūrya` alone at ≥ 0.90 would need about
30 rows on that one alias against the 3 that exist.** The gold set was frozen before this
split existed and was not stratified for it. Also note the annotator is
`MODEL_ADJUDICATED`, `claude-opus-5` — the same model family that wrote this rule — so
these figures are not independent of the rule in the way a human gold set would be. That
limitation is inherited, not introduced, and it is the reason the certainty claims above
are lower bounds.

---

## 9. Top-20 profiles

### Selection, and why it is the union of two rankings

`top_devatas` orders by `HAS_DEVATA`, and that layer is Rigveda-only, so on its own it
builds a Rigvedic top twenty and calls it a four-Veda one. `top_devatas_by_mention` (new)
orders by the mention layer at the default certainty tiers, spans four Vedas, and matches
what a default deity query returns. **The two disagree, and the disagreement is a finding:**

- **In the mention top 20 only:** `PITARAH`, `ADITIH`, `VISNUH`, `TVASTA`, `MITRAH`,
  `RUDRAH` — heavily named, lightly ascribed.
- **In the attribution top 20 only:** `PAVAMANAH-SOMAH` (1,087 attributions, 39 default
  mentions), `VISVEDEVAH` (805 / 5), `RBHAVAH`, `PUSA`, `INDRAVARUNAU` (70 / 0),
  `DANASTUTIH` (50 / 0).

Taking the union means no deity is excluded by an artefact of which layer was consulted.
**26 profiles landed** (20 by mention ∪ 20 by attribution), `sent=26 landed=26`.

### Per-deity field completeness

16 fields checked: 3 attribution counts, `top_rishis`, `top_chandas`, `top_concepts`,
`top_concepts_strict`, `co_devatas`, `co_mentioned`, `top_actions`,
`top_requested_actions`, `top_objects`, `formula_count`, `mentions_total`, `axes`,
`aliases_iast`.

| deity | C | P | A | attrib. | filled | verdict RV/SV/YV/AV | genuinely absent |
|---|---|---|---|---|---|---|---|
| Indra | 3566 | 0 | 0 | 2869 | 16/16 | A/A/A/A | — |
| Agni | 831 | 877 | 835 | 1988 | 15/16 | A/A/A/A | co_devatas |
| Varuṇa | 589 | 0 | 0 | 99 | 15/16 | A/A/A/A | co_devatas |
| the Maruts | 560 | 0 | 0 | 428 | 16/16 | A/A/A/A | — |
| the Fathers | 461 | 0 | 0 | 18 | 15/16 | A/A/A/A | co_devatas |
| the Aśvins | 319 | 115 | 192 | 631 | 15/16 | A/A/A/A | co_devatas |
| Soma | 240 | 181 | 1091 | 80 | 15/16 | A/A/A/A | co_devatas |
| Bṛhaspati | 318 | 0 | 0 | 74 | 15/16 | A/A/A/A | co_devatas |
| Aditi | 239 | 0 | 0 | 3 | 13/16 | A/A/A/A | attributed_inherited, co_devatas, formula_count |
| Viṣṇu | 225 | 0 | 0 | 31 | 15/16 | A/A/A/A | co_devatas |
| Indra and Agni | 157 | 0 | 0 | 117 | 15/16 | A/A/A/A | co_devatas |
| Mitra and Varuṇa | 152 | 0 | 0 | 184 | 16/16 | A/A/A/A | — |
| Uṣas | 69 | 73 | 276 | 182 | 15/16 | A/A/**I**/A | co_devatas |
| Tvaṣṭṛ | 138 | 0 | 0 | 13 | 14/16 | A/A/A/A | attributed_inherited, co_devatas |
| Sūrya | 21 | 114 | 564 | 63 | 16/16 | A/A/A/A | — |
| Savitṛ | 23 | 89 | 307 | 82 | 15/16 | A/A/A/A | co_devatas |
| Vāyu | 43 | 60 | 136 | 53 | 15/16 | A/A/A/A | co_devatas |
| Mitra | 37 | 49 | 342 | 10 | 15/16 | A/A/A/A | co_devatas |
| Rudra | 33 | 51 | 132 | 38 | 15/16 | A/A/A/A | co_devatas |
| the Ādityas | 50 | 31 | 143 | 100 | 16/16 | A/**I**/A/A | — |
| Pūṣan | 32 | 42 | 141 | 77 | 15/16 | A/A/A/A | co_devatas |
| the Ṛbhus | 33 | 33 | 34 | 96 | 15/16 | A/A/A/A | co_devatas |
| Soma Pavamāna | 0 | 39 | 67 | 1087 | 13/16 | **-**/A/A/**I** | co_devatas, top_actions, top_requested_actions |
| the All-Gods | 5 | 0 | 0 | 805 | 11/16 | -/-/A/- | co_devatas, co_mentioned, actions ×2, aliases_iast |
| praise of a patron's gift | 0 | 0 | 0 | 50 | 9/16 | -/-/-/- | co_devatas, co_mentioned, actions ×2, top_objects, mentions_total, aliases_iast |
| Indra and Varuṇa | 0 | 0 | 0 | 70 | 10/16 | -/-/-/- | co_devatas, co_mentioned, actions ×2, top_objects, mentions_total |

**Against the target of 20/20 useful: 22 of the 26 are at 14/16 or better and all 22 are
`ATTESTED` in at least three Vedas.** Four are not, and each hole has a named structural
cause rather than a gap in that deity's record:

- **`co_devatas` is empty for 21 of 26.** It counts passages carrying *two* `HAS_DEVATA`
  edges, and the Anukramaṇī normally assigns one devatā per passage. This is why
  `co_mentioned` was added: four-Veda, from `CO_OCCURS_WITH`, and populated for 24 of 26.
  A profile that offered only `co_devatas` showed Agni with no companions at all.
- **`VISVEDEVAH`, `DANASTUTIH`, `INDRAVARUNAU`** have no theonym-registry entry, so they
  have no mention layer and no aliases: `NOT_IN_LAYER`, correctly, and `top_objects` and
  `co_mentioned` are computed over mentions so they are empty by construction. These three
  reach the set only through the attribution ranking. They are honest holes, not failures —
  but a reader should know that the graph cannot currently say anything about the
  seventeenth most-ascribed devatā outside the Anukramaṇī.
- **`PAVAMANAH-SOMAH`** has 1,087 attributions and no action assertions: the agentive layer
  is RV-only and this deity's `CERTAIN` mentions are 0 in the Rigveda (its forms are
  licensed for the SV substring pass, not the RV annotation).
- **`attributed_inherited = 0`** for Aditi and Tvaṣṭṛ is a real value, not a hole: every one
  of their attributions is stated of the mantra itself.

`profile_absent_dimensions` is landed on every node, so the holes are queryable rather than
being a table in a report.

### A profile defect found and fixed

`compute_profile` counted mentions over `MENTIONS_ENTITY`→`:Devata`. V3's
`retire_superseded_devata_mentions` deleted **every one of those edges** — there are 0 left.
So the loop ran, matched nothing, and left `mentions` empty **while the profile reported
success and landed**. Every deity profile computed after that retirement silently claimed
the deity was mentioned nowhere, and because
`data/domain/vedagraph_domain_v2/devata_profiles.jsonl` holds the *pre*-retirement values
(`"mentions": {"RV": 2305}` for Indra), the artifact looked right and could no longer be
reproduced. Now reads `MENTIONS_DEVATA`, four Vedas, split three ways.

Second, smaller: `load_profiles` computed `landed` as "every `Devata` in the graph carrying
a profile", not "the keys sent". That total already exceeded `sent` before the loader ran,
so it could land nothing and still report `complete`. Now counted over the keys sent.

---

## 10. Verification

| check | result |
|---|---|
| `MENTIONS_DEVATA` total against the measured baseline | 17,165 → **17,165**, unchanged |
| rows sent vs landed, `theonyms` | 17,165 / 17,165 |
| rows sent vs landed, `devata_variants` | 6 / 6 (+6 relationships graph-wide, exactly) |
| rows sent vs landed, `devata_composition` | 214 / 214 |
| rows sent vs landed, `devata_profiles` | 26 / 26 |
| edges carrying a `referent_certainty` outside the three tiers, **or** a null `referent_basis` | **0** |
| edges retaining the superseded two-way-only value | **0** — the three tiers sum to 17,165 exactly, per Veda and in total |
| grading-metadata invariant (`quality_tier`, `grade_basis`, `score`, `trust`, `evidence`, `evidence_count`, `attribution_precision`, `veda`, `extraction_path`, `knowledge_layer` all present) | **0 edges missing any field** — 100% still holds |
| unlabelled `MATCH` in any mutation | **none**: every write matches `(:Devata)` / `(:Passage)` explicitly, and every new edge type is registered in `ontology.py`'s endpoint map |
| `is_composite` against `COMPOSED_OF` | 14 / 14, **0 contradictions** (was 0 / 14) |
| node and relationship totals | properties-only steps left 108,777 / 264,193 unchanged; the variant step added exactly 6 relationships |
| `ruff format`, `ruff check`, `mypy --strict` | pass on every file changed |
| targeted tests | `tests/domain/test_deity_referent_tiers.py` 15 passed; `tests/domain/test_domain_layer.py` 58 passed, 9 live-gated skips |
| full re-run of the whole deity chain | idempotent: 108,776 nodes / 266,347 relationships identical before and after, all five steps `sent == landed`, tier counts unmoved |

**Four failures in `tests/domain/` at the time of writing are not mine, named so nobody
spends time on them twice.** `test_being_and_nonbeing.py` (2) fails on
`VG:CONCEPT:HOTR-PRIEST: node_type 'RITUAL_ROLE' is not an allowed entity type` — a
concurrent agent retyped that concept in `concepts.yaml` and has not yet added
`RITUAL_ROLE` to `enrich/concepts.py`'s allowed set.
`test_domain_layer.py::test_every_query_states_its_limits` and
`::test_queries_cover_a_substantial_share_of_the_killer_questions` fail on
`entity_vocabulary_overlap_candidates`, whose `question` string now ends in a parenthetical
rather than a `?`. Both files pass in isolation against my changes; I ran
`test_domain_layer.py` alone before those edits landed and it was 58 passed / 9 skipped.

**One thing to know about the repo-wide format check.** `ruff format --check .` reports
**51 files would be reformatted at `ruff 0.16.6`, at `HEAD` and before any change of
mine** — the committed tree was formatted by a different ruff version. I therefore did
**not** run `ruff format` across `domain/loader.py`: doing so produced a 172-line diff of
unrelated churn in a file other agents are editing, and I reverted it and re-applied only
my own 70 lines. Every file I touched passes `ruff check` and `mypy --strict`. The
formatter-version drift is pre-existing and is the integrator's call.

---

## 11. Spec for the integrator — changes wanted in `src/vedagraph/domain/queries.py`

I did not edit the query module. Everything below is available as an import from
`vedagraph.domain.theonyms` or as a landed `Devata` property.

**1. Replace every hard-coded certainty string with the policy constants.**
`queries.py` lines 363, 388, 492, 512–514, 545 and the caveat at 123–126 all name
`'DEITY_CERTAIN'` / `'DEITY_AMBIGUOUS'` literally, and the caveat quotes stale numbers
("8,485 of 16,261"). Import instead:

```python
from vedagraph.domain.theonyms import (
    AMBIGUOUS,
    CERTAIN,
    PROBABLE,
    DEFAULT_REFERENT_TIERS,
    EXPLORATORY_REFERENT_TIERS,
    STRICT_REFERENT_TIERS,
    referent_tiers_for_mode,
    mention_verdict,
)
```

**2. Default every deity query to `DEFAULT_REFERENT_TIERS`, and take a `mode` parameter.**

```cypher
MATCH (p:Passage)-[m:MENTIONS_DEVATA]->(dv:Devata)
WHERE m.referent_certainty IN $tiers      // referent_tiers_for_mode(mode)
```
`queries.py:545` currently hard-filters `= 'DEITY_CERTAIN'`. **Change it to
`IN $tiers`** — as it stands it is the strict mode, and §3 shows strict mode returns wrong
zeros for every homonym deity outside the Rigveda. This is the single highest-value line in
the module.

**3. Every deity-facing query must return three counts and a verdict, never one count.**

```cypher
RETURN dv.entity_key AS deity, m.veda AS veda,
       count(CASE WHEN m.referent_certainty = 'DEITY_CERTAIN'   THEN 1 END) AS certain_mentions,
       count(CASE WHEN m.referent_certainty = 'DEITY_PROBABLE'  THEN 1 END) AS probable_mentions,
       count(CASE WHEN m.referent_certainty = 'DEITY_AMBIGUOUS' THEN 1 END) AS ambiguous_mentions
```
then map through `mention_verdict(certain, probable, ambiguous)` and emit
`INSUFFICIENT_EVIDENCE` / `NOT_IN_LAYER` in place of a `0`. The precomputed form is on the
node: `profile_mention_verdict_by_veda`, `profile_mentions_by_veda_certainty`,
`profile_mentions_certain/_probable/_ambiguous`, `profile_mentions_default_scope`.

**4. Attach a `PROBABLE`-bucket caveat naming the alias, and consider excluding it.**
Suggested wording, replacing the flag at `queries.py:123`:

> `DEITY_PROBABLE` is 2,019 of 17,165 edges at a measured Wilson lower bound of 0.90 on 55
> gold rows. Its worst alias is `sūrya` for `VG:DEVATA:SURYAH` at 2/3 on 71 live edges,
> where a `VOCATIVE` role can be a sandhi-reduced nominative; a caller who needs Sūrya
> specifically should read `referent_basis` and treat `R2_address_morphology` on `sūrya` as
> undecided.

`referent_basis` is on every edge, so an exclusion is one predicate:
`NOT (m.referent_basis = 'R2_address_morphology' AND 'sūrya' IN m.matched_forms)`.
I have **not** applied that — the sample is 3 rows and the module's docstring puts the
form's pre-consonantal share at 47%, so an exclusion is defensible but not measured. Your
call.

**5. Exclude composites from any per-deity leaderboard (Q38).**
`deity_widest_range` is topped by `Agni, Mitra-Varuna, Ratri and Savitr` with 4 axes and 0
attributions. Both predicates now exist and are correct on all 214 nodes:

```cypher
WHERE dv.is_composite = false AND dv.structure = 'INDIVIDUAL'
```

**6. Resolve epithet variants before counting personifications (Q86).**

```cypher
MATCH (dv:Devata)-[:DEVATA_ASSOCIATED_WITH]->(c)
OPTIONAL MATCH (dv)-[:EPITHET_VARIANT_OF]->(base:Devata)
WITH c, coalesce(base, dv) AS resolved
WHERE resolved.structure = 'INDIVIDUAL'
RETURN coalesce(c.display_label, c.concept_id) AS phenomenon,
       count(DISTINCT resolved) AS personifications,
       collect(DISTINCT resolved.display_label) AS deities
```
Takes fire from 5 to 1. Filter `r.relation <> 'PART_OF_DEITY'` if you want epithets only.

**7. Return both concept rankings, or neither (Q3).** `profile_top_concepts` (inherited) and
`profile_top_concepts_strict` (`attribution_precision = PER_PASSAGE`) are both landed.
Returning one without its basis in the field name is the trap the diagnosis names.

**8. Retire `MENTIONS_ENTITY.theonym_ambiguous` (Q45).** It is a strictly worse duplicate —
sandhi-inconsistent (`somam` true / `somaṃ` false) and never calibrated — and it is on
`MENTIONS_ENTITY`, outside my partition. Whoever owns that edge should drop the property
rather than leave two rival sense fields that disagree.

---

## 12. Not started, and why

- **Q92** (`Devata`↔`Object` lift): needs `DomainEntity`, outside the write partition. The
  machinery is a second application of `cooccurrence.rebuild` and is genuinely small.
- **Q52** (per-occurrence axes): the action layer is RV-only (all 4,865 assertions), so a
  cross-divisional divergence statistic cannot be computed honestly yet.
- **Q46's `RITUAL_MEDIUM` sense value**: not derivable from any property on these edges. It
  needs a per-occurrence sense assignment, which needs annotation.
- **Q85's river routing**: outside the partition, and §6 argues the premise needs checking
  before anyone acts on it.
- **The silent PAIR/GROUP set** (§7): reported, not decomposed.
