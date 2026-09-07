# Rigveda semantic V3.2 — freeze decision

> **NO HUMAN GOLD EXISTS.**
> **MODEL SELF-AGREEMENT IS NOT ACCURACY.**
> **CLAUDE OPUS 5 MODEL REVIEW IS NOT HUMAN GOLD.**
> **ALL SEMANTIC OUTPUTS REMAIN CANDIDATE KNOWLEDGE.**
> **50/448 PASSAGES LACK TRANSLATION ANCHOR COVERAGE UNDER THE CURRENT SEMANTIC CONTRACT.**

Date: 2026-09-07
Evidence run: `vedagraph-rigveda-semantic-claude-opus5-v3.2-448-new-v1`
Output seal: `cd45b1752cae62dd7d364d571235aa0db3c58ace8be829369dc9c013274465ec`
Provenance bucket: `CLAUDE_OPUS5_MAX_MULTI_AGENT_CANDIDATE_EXTRACTION`

---

## Decision

```
RIGVEDA_SEMANTIC_V3_2_FREEZE_WITH_REVIEW_BACKLOG
```

```
RIGVEDA_SEMANTIC_TUNING_PHASE = CLOSED
```

```
NEXT_PROJECT_PHASE = START_SAMAVEDA_CORPUS_INGESTION
```

---

## Why this outcome and not the others

### Not `RIGVEDA_SEMANTIC_EXECUTION_INTEGRITY_FAILED`

Every execution gate passed. 448/448 passages hold exactly one terminal validated response;
receipt, packet-hash, evidence, span, binding, ontology/type, provenance-mismatch,
heuristic-contamination, duplicate-final and cross-passage-duplicate-ID counters are all
**zero**. 446 of 448 succeeded on first attempt. No validator was ever weakened.

### Not `RIGVEDA_SEMANTIC_V3_2_POLICY_REVISION_REQUIRED`

This outcome is reserved for a *systemic* extraction-policy problem. The specific failure
modes that would justify it were all measured and all absent:

| Failure mode | Observed |
|---|---|
| fabricated evidence | **0** (30-case deep audit, 232 assertions) |
| systematically wrong entity binding | **0** (471 canonical assertions, 0 target failures, 0 contradictions) |
| large agent-specific regimes | **none** — 1.11× normalised density ratio, 0.00 no-claim spread |
| broad-predicate explosion | **none** — 21 assertions, 0.85% of output; `HAS_THEME` unused |
| many unsupported assertions | **0 UNSUPPORTED** on the highest-risk subset |
| corrupted provenance | **none** — recorded honestly, incl. a new runtime value |
| silent candidate promotion | **none** — `canonical_promotion: false`, `unlocked_predicates: []` |

V3.2 was written to close one specific hole: the v3.1 wording admitted two coherent
readings of *when* a supported relation must be emitted, and two runs occupied different
emission regimes (1.73× density, 0.47 no-claim gap). Under six independent Claude agent
groups over 398 assertion-capable passages, that axis did not vary **at all**: every group
emitted on every translation-bearing passage it held, and cross-agent replication agreed on
the emit/omit decision 12/12. **The V3.2 revision achieved what it was written to achieve.**

### Not plain `RIGVEDA_SEMANTIC_V3_2_CANDIDATE_LAYER_FREEZE`

Every listed criterion for the plain freeze is in fact met. It is not chosen because a real,
bounded review backlog exists, and calling this a clean freeze would misrepresent that.
Nothing in the backlog is an architecture blocker; all of it is reviewable semantic
judgement. Naming it in the decision is the difference between a freeze that is honest and
one that is merely convenient.

---

## The review backlog this freeze carries

| Item | Size | Nature |
|---|---|---|
| risk-ranked review candidates | 168 found, **75 written**, **93 dropped beyond the cap** | ordinary review |
| `WEAK_SUPPORT` assertions | 2 | single-step over-reach, both documented |
| `PREDICATE_AMBIGUOUS` (audited subset) | 17 / 232 | predicate-boundary judgement |
| `OBJECT_GRANULARITY_AMBIGUOUS` (audited subset) | 10 / 232 | mostly REQUESTS splitting |
| `SUPPORTED_BUT_REDUNDANT` (audited subset) | 6 / 232 | redundancy, not error |
| same predicate+object on different evidence | 144 groups / 276 assertions | possible over-splitting; **0 true duplicates** |
| ontology gaps | 86, all `TRUE_SCHEMA_GAP` | genuine schema question |
| translation-anchor coverage | **50 / 448 passages** | corpus-layer gap, not policy |

The 93 dropped queue entries are stated explicitly rather than silently truncated.

### Two items that are architecture questions, not review items

1. **`STRUCTURAL_NO_TRANSLATION_ANCHOR` — 50/448 (11.16%).** The binding contract requires
   character anchors in the packet translation, so a packet without a translation cannot
   emit any assertion in any family. All 50 returned no-claim; none fabricated a
   Sanskrit-only anchor. Raising coverage requires either more translation ingestion or a
   Sanskrit-token binding mode. **Neither is attempted here**, and the schema was not
   changed mid-run to paper over it.

2. **Person-like referents are unmodelled.** All 86 ontology gaps are one shape: patrons,
   ancestors, kin. That is a coherent input to a future ontology version, not a defect. The
   ontology was **not** expanded.

---

## What this freeze does and does not mean

**It means:**

- The Rigveda semantic **candidate-generation methodology** is operationally sound and is
  frozen at V3.2. No further large Rigveda semantic tuning run is required.
- The frozen V3.2 prompt, payload schema, predicate ontology and typed-object schema are
  reused byte-identically and remain unchanged.
- Semantic outputs can be regenerated at any time from the sealed inputs.

**It does not mean:**

- Rigveda remains **canonical** at the corpus, deterministic-knowledge and lexical layers
  only. Semantic assertions are **not** canonical.
- Semantic assertions remain **candidate-only**: `CANDIDATE / NEEDS_REVIEW`.
- **No predicate is unlocked to canonical truth.** `unlocked_predicates: []`.
- **No candidate is promoted.** `canonical_promotion: false`.
- **No human gold exists.** `human_gold_status: UNANNOTATED`. Nothing in this run has been
  scored against a reference, because there is no reference.
- Claude Opus 5 model review is **not** human gold. The 99.14% figure is a
  `MODEL_ADJUDICATED_ENGINEERING_SUPPORT_RATE` and may never be called precision.
- Qualified scholar review may be added later. The review backlog is kept **separate** from
  the sealed candidate layer so that adding it changes no existing artefact.

---

## Scope-extension conclusion

The frozen V3.2 prompt declares in its own front matter:

- `execution_scope: BOUNDED_60_STABILITY_ONLY`
- `execution_status: NOT_APPROVED_FOR_508_OR_FULL_CORPUS`

The prompt was **not modified** and its sha256 remains
`e4fdcd5d519d47e94a4c41b57180c81e94cb5034f40fd876dcecd4a8e6da73a1`. Editing the front
matter would have destroyed the one property this pilot exists to test.

On the evidence of this run, the extension is recorded as validated at this sample size, in
a separate governance artefact
(`docs/manifests/rigveda_semantic_v3_2_candidate_scope_approval.json`):

```
V3_2_CANDIDATE_SCOPE_EXTENSION_VALIDATED_AT_448_SAMPLE
```

This approval covers **candidate generation at the 448 sample scale**. It does **not**
approve the full 10,552-mantra corpus, and no full-corpus run is authorised or required.

---

## Next phase

Rigveda is the reference implementation, not the whole project. It now has a canonical
corpus, a deterministic traditional-knowledge layer, a lexical layer, and a frozen,
audited semantic **candidate** architecture.

```
NEXT_PROJECT_PHASE = START_SAMAVEDA_CORPUS_INGESTION
```

Samaveda ingestion was **not** started in this run.
