# Post-V1 Data Completeness Campaign — STATUS

**Resume from this file. Rewrite it whole; never splice sections in.**
Guard: `python scripts/validate_status_report.py`

- Branch `phase-data-completeness-v2` · start commit `d6e93a9` · tag `vedanvaya-v1.0.0` FROZEN
- Last rewritten 2026-09-16, at the close of Wave 4

## Where the campaign is

**Wave 4 is complete and its verdict is `VEDANVAYA_DATA_COMPLETENESS_NOT_COMPLETE`, with
`RELEASE_CANDIDATE = NO`.** The full report is
[`WAVE4_ADVERSARIAL_QA.md`](WAVE4_ADVERSARIAL_QA.md); read that before doing anything.

The campaign was not finished, and the reason no gate could have shown it: the gap registry
had **no closed state** — 84 of 85 entries `OPEN`, no closure vocabulary, no field to hold
one, and 67 entries carrying an unmeasured hypothesis with all 14 addressing diagnostics
`NOT_RUN`. Every entry now terminates in exactly one status, measured.

| registry | entries |
|---|---:|
| data-completeness closures | 37 |
| separately tracked execution blockers | 8 |
| **still implementation-fixable** | **40** |

| gate | result |
|---|---|
| `graph_quality_scorecard.py` | **11 of 11**, three of them added in Wave 4 |
| `dependency_state.py --status` | `CURRENT=6 STALE_INPUT=0`, no unexplained stale |
| perturbation test | exactly the two declared consumers moved; byte-exact restore |
| `pytest tests/unit` | **1,205 passed**, 41 skipped |
| `pytest tests/api` | **1,385 passed** |
| `pytest tests/domain` | **217 passed**, 31 skipped |
| `pytest tests/api/ask tests/product` · `tests/llm` | **388** · **91 passed** |
| `pnpm test` · typecheck · lint | **434 passed** · clean · clean |

## Canonical graph

| | Product V1 | After Wave 3 | Now |
|---|---:|---:|---:|
| Nodes | 108,779 | 116,825 | **116,838** |
| Relationships | 265,295 | 281,290 | **281,257** |
| Public nodes (`NOT n:Internal`) | — | 44,324 | **39,664** |
| Public `:Chandas` | — | 575 | **547** |

Core corpus invariant, asserted every run: RV 10,552 · SV 1,844 · YV 1,975 · AV 5,839 =
20,210. Every Wave 4 migration (M10, M11, M12) is additive — property and label writes only,
0 node delta, 0 relationship delta.

Backup: `D:\vedanvaya-backups\round4-pre-m9-20260916T124347\neo4j.dump`
sha256 `50f27ea8…c0543`. **Take a fresh dump before the next destructive mutation** — M10, M11
and M12 landed after this one, and they are additive, so restoring it would lose them.

## The finding that decides the verdict

`GAP-TRANSLATION-002` records *"Closed via the Wayback Machine, 944 of 961."* The graph holds
4,878 of 5,839 Atharvavedic translations — exactly the pre-closure figure. All **2,254**
accepted rows in `data/staging/translation/rows.jsonl` target mantras that exist, and **none
carries a translation**. 1,242 of them are Samavedic, against an entry that records the
Samaveda as source-blocked; it is not, and the rows are keyed to this corpus's own canonical
keys.

Acquired, staged, never imported, and recorded as closed. The gate is shut behind
`OWNER_DECISION_A_RV_SPAN` and `OWNER_DECISION_C_FORCED_ADDRESSES` with Gate B `UNKNOWN` and
Gate C `NOT_RUN`. Same pattern for audio and Samaveda music behind
`OWNER_DECISION_E_AUDIO_GATE`. All five are `BLOCKED_OWNER_DECISION_REQUIRED` — counted apart
from the closures, never as one.

## Wave 4 — eleven defects fixed at their generators

1. The chandas builder still emitted 33 bracket fragments as metre names — and **swapped
   `sys.stdout` at import time, so pytest could not import it**, which is why its documented
   residual shipped. 39 tests now pin 19 malformed strings refused and 16 real metre names
   with `3-av.`/`6-p.` qualifiers surviving.
2. 28 retired metre identities were public in the world export → M10.
3. The orphan gate swept one label family and reported 0 while those 28 sat edgeless.
4. `/api/v1/entities/{type}` bypassed the product filter: 575 chandas served against 547.
5. A live API caveat denied the Atharvaveda's whole deity-ascription layer (5,385 edges).
6. The Rigveda's scope statement claimed a Padapatha we do not hold.
7. 214 `:Devata` nodes told Ask the Atharvaveda has no attribution layer — and
   `ask/evidence.py` reads that property as an absence qualifier → M11.
8. 256 `EXACT_PARALLEL_OF` edges served a null `match_level` while carrying it under
   `strongest_method` → M12. 252 renamed, 4 typed absent; enrichment's 750 unmoved.
9. 15 declared predicates had no endpoint signature, so the gate's universe omitted them. Now
   90 of 90.
10. `SHARES_FORMULA_WITH` was declared deliberately empty while holding 6,148 edges, and the
    ontology reference published that. New gate: `falsely_declared_unpopulated`.
11. 8 predicates fell into the Focus view's "Other", including a rite's 3,121 procedural steps.

### The chain that mattered most

M10 fixed the graph, the export dropped the 28, and
`frontend/public/world/world.labels.json` — the file a browser downloads — still carried all
28. Three causes: both world consumers declared the same *intermediate* as their output, so
the Lab stage was judged on a file its own build never touches; `build-world.mjs` joined the
constellation partition **by position** with no length check, reading 35,370 assignments onto
35,648 nodes; and `world.predicates.json` was in no consumer's hash. All fixed, bundle
rebuilt, 0 of 28 remain in any shipped artifact.

## Blocking

1. **Four owner decisions.** A and C release 2,254 staged translations; E governs 954 audio
   rows and 1,471 Samavedic notation rows. Gate B and Gate C have not been run for any of
   those four domains, so the decision needs those first.
2. **40 implementation-fixable registry entries**, each with a measured basis in
   `data/gap_registry.json`. Largest clusters: entity coverage 8, quality 5, ritual 5, product
   surface 5, semantics 4, morphology 3.
3. **`ASK_FORMAL_REGRADE_BLOCKED_EXTERNAL_QUOTA`** unless the appended run record in
   `WAVE4_ADVERSARIAL_QA.md` §L1 says otherwise. `misleading = 0` is not claimed without a
   fresh 60/60 at the final commit. Partial runs are never combined.
4. **1,021 audio rows, 20 heard.** *(This item updated 2026-09-18; the rest of this file is
   still Wave 4's.)* The owner listened to 20 rows of the seeded 100-row sample at
   `data/staging/wave4/audio_owner_sample_manifest.json` and accepted them: `AUDIO_OWNER_SAMPLE
   = ACCEPTED`, 20 reviewed, 20 verified, 0 uncertain, 0 rejected (OWNER_DECISIONS.md §43).
   That is **sample-level owner review, not exhaustive manual review** — 1,001 of the 1,021
   queue rows are `NOT_INDIVIDUALLY_HEARD`, 0 queue rows were promoted, and
   `OWNER_DECISION_E_AUDIO_GATE` (§14) still blocks GAP-AUDIO-002, -003 and -004.
5. **`GAP-TRANSLATION-006`** — 25 of 31 shipped translations in RV 1.65–1.70 sit on the wrong
   verse. Wrong data on a public surface, not missing data. Fix this before the rest of item 2.

## Registry

`data/gap_registry.json`, 85 entries, audited by
`scripts/wave4_registry_closure_audit.py --write`. Every entry carries `status`,
`closure_basis`, and where applicable `closure_measure`, `closure_measured_value`,
`closure_citation`, `closure_owner_decision`, `closure_blocked_evidence`.

Two guards against the cheap way to empty a registry: `CLOSED_SCOPE_DECISION` requires a
citation naming where the decision is written down, and `BLOCKED_EXTERNAL_SOURCE_UNAVAILABLE`
requires all five owner-specified fields. Either missing and the entry is downgraded and
counted as not terminated. `tests/unit/test_registry_closure.py` asserts the closure set and
the blocker set stay disjoint, so "closed" cannot quietly start including "waiting".

## Artifacts

| what | where |
|---|---|
| Wave 4 report | `docs/reports/data-completeness/WAVE4_ADVERSARIAL_QA.md` |
| baseline, measured not inherited | `data/staging/wave4/baseline.json` |
| registry closure audit | `data/staging/wave4/registry_closure_audit.json` |
| rebuild reproducibility | `data/staging/wave4/rebuild_reproducibility.json` |
| dependency perturbation receipt | `data/staging/wave4/dependency_perturbation.json` |
| boundary and seeded sampling | `data/staging/wave4/boundary_sampling.json` |
| audio harness QA | `data/staging/wave4/audio_harness_qa.json` |
| 100-row owner listening sample | `data/staging/wave4/audio_owner_sample_manifest.json` |
| M10 / M11 / M12 receipts | `data/staging/integration/m1{0,1,2}_receipt.json` |
| dependency ledger and status | `data/staging/integration/dependency_{ledger,status}.json` |

## Next

There is no next wave to run without an owner decision. The four decisions in **Blocking**
item 1 are the whole of what stands between the staged material and the graph, and the 40
entries in item 2 are ordinary implementation work with a measured basis each.

## Environment

- Neo4j 5.26 community in Docker (`vedagraph-neo4j`), bolt on 7687, GDS reinstalls on start
  (~1 min before the first query answers)
- `pytest tests/api` and `pytest tests/unit` **must be run as separate invocations**. Together
  they raise `ValueError: I/O operation on closed file` — a builder swapping `sys.stdout` at
  import time detaches pytest's capture. One such builder was fixed in Wave 4; assume others.
- `PYTHONIOENCODING=utf-8` on every script that prints Devanagari or IAST
- `MSYS_NO_PATHCONV=1` for Docker paths under Git Bash; heredocs break on apostrophes, so
  prefer the Write tool or `python - <<'PYEOF'`
- Frontend: `pnpm` via the cmd shims, never `npx <tool>`; never share one `.next` between
  parallel agents

## Rules a resuming session must not break

- Never make counts agree by weakening a check. Never let graph-observed schema declare itself
  valid. Never let a readback derive its expectation from the already-mutated graph.
- Never infer identity from normalization alone. Never convert a normalization into an
  identity — M12's 4 refused edges are what that rule looks like in practice.
- Never fabricate missing source data. Never promote model-assisted evidence to
  source-explicit. Never interpret confidence as a calibrated probability.
- Never call metadata, waveform inspection or ASR an audible review, and never simulate
  listening. Audio sources are usable only if publicly reachable without authentication and
  without bypassing any access control.
- Back up before a destructive canonical mutation. Additive migrations still need a receipt
  carrying the before/after census and the core corpus invariant.
- A gate that cannot fail is a defect. Prove a new gate BAD → FAIL and GOOD → PASS before
  trusting it, and read declarations rather than restating them — four of Wave 4's own errors
  were restatements.
