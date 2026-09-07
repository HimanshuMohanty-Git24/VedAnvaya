# Rigveda semantic V3.2 — Claude Opus 5 multi-agent stability

> **NO HUMAN GOLD EXISTS.**
> **MODEL SELF-AGREEMENT IS NOT ACCURACY.**
> **CLAUDE OPUS 5 MODEL REVIEW IS NOT HUMAN GOLD.**
> **ALL SEMANTIC OUTPUTS REMAIN CANDIDATE KNOWLEDGE.**
> **50/448 PASSAGES LACK TRANSLATION ANCHOR COVERAGE UNDER THE CURRENT SEMANTIC CONTRACT.**

Run: `vedagraph-rigveda-semantic-claude-opus5-v3.2-448-new-v1`
Seal: `cd45b1752cae62dd7d364d571235aa0db3c58ace8be829369dc9c013274465ec`
Assignment manifest: `cbc4321d…` · Partition hash: `f6b8db0afa4906c0b1f554076a4f947b8ed6285f6ceeb785dd0b5165244f84b6`

---

## 1. Why this audit exists

The V3.2 policy revision exists because of a regime split. Two genuine v3.1 runs processed
the same sixty EvidencePackets under a byte-identical contract and occupied different
*emission regimes*: one emitted 57 assertions at a no-claim rate of 0.167, the other 33 at
0.633. Both were internally consistent. That is a property of a run, not of any assertion,
and no per-assertion check can see it.

This run authored 448 passages across six agent groups. The question is whether semantic
behaviour tracks the **agent boundary**. If it does, the candidate layer is not reusable,
because output would depend on which agent happened to draw a passage.

---

## 2. Normalisation, and why it is not optional

Groups do not hold equal translation coverage, and a group holding more translationless
packets would look conservative on raw numbers for a reason that has nothing to do with the
agent. Both raw and normalised statistics are therefore reported, and the **normalised**
figures are the ones the verdict rests on.

| Group | Assigned | Translation-bearing | Translationless | Translationless share |
|---|---|---|---|---|
| A | 75 | 66 | 9 | 12.0% |
| B | 75 | 68 | 7 | 9.3% |
| C | 75 | 67 | 8 | 10.7% |
| D | 75 | 65 | 10 | 13.3% |
| E | 74 | 67 | 7 | 9.5% |
| F | 74 | 65 | 9 | 12.2% |

The round-robin partition (`sorted(passage_ids)[i] -> GROUP[i % 6]`) balanced coverage
without being asked to: 65–68 translation-bearing per group. Contiguous blocks were
rejected deliberately — they would have handed one group most of Mandala 9 and turned any
per-group difference into a difference between Mandalas.

---

## 3. Per-agent distribution — raw and normalised

| Group | Assertions | / assigned (raw) | / bearing (normalised) | No-claim rate (all) | **No-claim rate (bearing)** | Canonical-ref rate |
|---|---|---|---|---|---|---|
| A | 392 | 5.227 | **5.939** | 0.1200 | **0.0000** | 0.1913 |
| B | 415 | 5.533 | **6.103** | 0.0933 | **0.0000** | 0.1880 |
| C | 408 | 5.440 | **6.090** | 0.1067 | **0.0000** | 0.1789 |
| D | 395 | 5.267 | **6.077** | 0.1333 | **0.0000** | 0.1696 |
| E | 442 | 5.973 | **6.597** | 0.0946 | **0.0000** | 0.2240 |
| F | 407 | 5.500 | **6.262** | 0.1216 | **0.0000** | 0.1941 |

Note how the raw column misleads and the normalised column corrects it. Group D looks like
the most conservative group on raw density (5.267, lowest) and has the highest raw
no-claim rate (0.1333) — but it simply drew the most translationless packets (10). On the
normalised measure it sits mid-pack at 6.077. **Diagnosing D as conservative from raw
counts would have been wrong**, which is exactly why the spec requires both.

---

## 4. Spread and verdict

| Measure | Min | Max | Spread / ratio |
|---|---|---|---|
| normalised density (assertions / bearing passage) | 5.939 (A) | 6.597 (E) | **ratio 1.111×** |
| no-claim rate, translation-bearing | 0.0000 | 0.0000 | **spread 0.0000** |
| canonical-reference rate | 0.1696 (D) | 0.2240 (E) | spread 0.0544 |

Thresholds, calibrated against the v3.1 split that motivated V3.2 (1.73× density, 0.47
no-claim gap):

- `CLEAR_AGENT_REGIME_DIVERGENCE` — normalised density ratio ≥ 1.5× **or** bearing no-claim spread ≥ 0.25
- `POSSIBLE_AGENT_REGIME_DIVERGENCE` — ratio ≥ 1.25× **or** spread ≥ 0.12
- otherwise `NO_AGENT_REGIME_DIVERGENCE`

Observed: **1.111× and 0.0000.**

### Verdict

```
NO_AGENT_REGIME_DIVERGENCE
```

Every group emitted on every translation-bearing passage it held. The no-claim decision —
the exact axis on which v3.1 fractured — showed **zero** variation across six independent
agent groups and 398 passages. Density varies by 11% end to end, an ordinary sampling
spread across ~66-passage partitions of heterogeneous material, not a regime.

For scale: the v3.1 regime split was a 1.73× density ratio with a 0.47 no-claim gap.
V3.2 under six Claude agent groups produced 1.11× and 0.00.

---

## 5. Predicate prevalence by group

Read as a shape comparison, not a scoreboard.

| Predicate | A | B | C | D | E | F |
|---|---|---|---|---|---|---|
| DESCRIBES | 123 | 120 | 120 | 118 | 116 | 137 |
| DESCRIBES_ACTION | 81 | 84 | 101 | 100 | 97 | 90 |
| REQUESTS | 64 | 75 | 64 | 58 | 78 | 56 |
| INVOKES | 27 | 37 | 34 | 35 | 41 | 37 |
| REFERS_TO_PLACE | 22 | 24 | 21 | 15 | 24 | 16 |
| INVOLVES_SUBSTANCE | 18 | 15 | 19 | 21 | 19 | 25 |
| REFERS_TO_NATURAL_PHENOMENON | 15 | 17 | 14 | 21 | 16 | 17 |
| INVOLVES_RITUAL | 9 | 15 | 12 | 13 | 20 | 9 |
| PRAISES | 16 | 8 | 9 | 6 | 11 | 5 |
| INVOLVES_OFFERING | 10 | 10 | 7 | 4 | 7 | 8 |
| EXPRESSES | 6 | 4 | 4 | 3 | 6 | 4 |
| ASSOCIATED_WITH | 1 | 4 | 3 | 0 | 6 | 3 |
| CONTRASTS_WITH | 0 | 2 | 0 | 1 | 1 | 0 |
| HAS_THEME | 0 | 0 | 0 | 0 | 0 | 0 |
| **group total** | **392** | **415** | **408** | **395** | **442** | **407** |

Every group uses all eleven substantive families. The only zeros are in the two rarest
review-sensitive predicates — `ASSOCIATED_WITH` (D: 0) and `CONTRASTS_WITH` (A, C, F: 0) —
where the whole-run totals are 17 and 4, so a zero in a ~66-passage partition is expected
sampling, not a regime. `HAS_THEME` is unused by all six, which is uniform conservatism
rather than divergence.

The larger families are tight across groups: `DESCRIBES` 116–137, `DESCRIBES_ACTION`
81–101, `REQUESTS` 56–78, `INVOKES` 27–41. No group shows a distinct object-kind regime
either; canonical-reference rate spans 0.170–0.224.

---

## 6. Cross-agent calibration — 12 replicas

Per-group aggregates can only show that groups behave similarly *in bulk*. They cannot show
whether two agents handed the **same** passage would agree. That requires replication, and
the budget for it is exactly 12 extra semantic tasks.

Selection was made **after** the seal, deterministically and stratified — two per group;
within a group, the translation-bearing passages ranked by `sha256(passage_id)`, lowest two
taken. **No output was consulted**, so no passage was chosen for looking right or wrong.
Translationless passages were excluded: replicating one would measure the binding contract,
not the author. Every replica was assigned to the *next* group cyclically, guaranteeing a
different author, in a context explicitly forbidden from reading the original.

Selection hash `ab46c9d04bc114b68a3a4fcaa62f72e1f6552bdaaf16b924ce3de7d467a8132f`.

| Passage | Orig → Replica | Class | Orig | Repl | Jaccard | Canonical same |
|---|---|---|---|---|---|---|
| RV 1.43.6 | E → F | EVIDENCE_VARIANCE | 2 | 2 | 1.00 | yes |
| RV 1.62.8 | C → D | PREDICATE_BOUNDARY | 8 | 7 | 0.80 | yes |
| RV 2.11.19 | A → B | OBJECT_GRANULARITY | 5 | 4 | 1.00 | yes |
| RV 5.42.18 | A → B | EVIDENCE_VARIANCE | 7 | 7 | 1.00 | yes |
| RV 6.28.5 | E → F | **SAME** | 5 | 5 | 1.00 | yes |
| RV 7.56.25 | B → C | PREDICATE_BOUNDARY | 12 | 11 | 0.50 | yes |
| RV 8.6.37 | C → D | PREDICATE_BOUNDARY | 6 | 5 | 0.67 | yes |
| RV 8.26.8 | D → E | PREDICATE_BOUNDARY | 5 | 5 | 0.80 | yes |
| RV 9.64.13 | F → A | PREDICATE_BOUNDARY | 6 | 5 | 0.80 | yes |
| RV 9.97.12 | F → A | PREDICATE_BOUNDARY | 8 | 7 | 0.75 | yes |
| RV 9.99.6 | D → E | EVIDENCE_VARIANCE | 6 | 6 | 1.00 | yes |
| RV 10.10.14 | B → C | CANONICAL_TARGET_VARIANCE | 7 | 6 | 0.67 | **no** |

| Agreement | Value |
|---|---|
| no-claim agreement | **12 / 12 (100%)** |
| canonical-target agreement | **11 / 12 (91.7%)** |
| mean predicate-presence Jaccard | **0.832** |
| predicate-presence exact agreement | 5 / 12 |
| typed-object agreement | 5 / 12 |
| exact assertion-set agreement | 1 / 12 |
| mean density, original → replica | 6.42 → 5.83 |
| mean absolute assertion delta | **0.58 (≈9%)** |
| **POSSIBLE_UNSUPPORTED_EXTRACTION** | **0** |
| UNRESOLVED | **0** |

### What the one canonical variance actually is

`RV 10.10.14` is the Yama–Yamī dialogue. The original emitted an `INVOKES` assertion
targeting `VG:DEVATA:YAMI`; the replica emitted **no canonical target at all**. This is an
**omission, not a mis-binding** — the replica did not bind a conflicting entity. Across all
twelve replicas there are **zero contradictory canonical bindings**, which is the property
that would actually block a freeze.

### Reading the numbers honestly

Exact assertion-set agreement of 1/12 is *not* a failure signal, and reporting it as one
would be wrong. Determinism was never required — §26 of the operating spec says so
explicitly, and a healthy candidate generator is permitted to vary locally, choose slightly
different evidence spans, and disagree on granularity.

What matters is *where* the variation lands:

- **Stable:** the emit/omit decision (12/12), canonical binding (11/12, and the miss is an
  omission), density (±9%), and the absence of any unsupported extraction (0/12).
- **Variable:** which predicate family carries a supported relation (6 cases), and which
  wording anchors it (3 cases).

Predicate-boundary and evidence-span choice are exactly the axes the V3.2 policy leaves to
judgement. The axis V3.2 was written to fix — whether to emit at all — did not vary once.

---

## 7. Conclusion

Semantic behaviour does **not** track the agent boundary in this run.

- Six independent agent groups, 448 isolated one-passage contexts.
- Normalised density ratio 1.11×; translation-bearing no-claim spread 0.00.
- No group-specific predicate or object-kind regime.
- Cross-agent replication agrees on every emit/omit decision and shows no contradictory
  canonical binding.

`NO_AGENT_REGIME_DIVERGENCE`

This replaces the need for an expensive full duplicate run: the per-group evidence is
in-bulk, the replication evidence is per-passage, and they agree.
