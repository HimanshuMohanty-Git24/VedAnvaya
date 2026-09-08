# Atharvaveda canonical release — state as of 2026-09-08

**Work:** Atharvaveda Saṃhitā, Śaunaka recension (`VG:WORK:AV:SAU`)  
**Artifact:** `BSB.AV.SAUNAKA.ROTH_WHITNEY.1856.SCAN`  
**Text version:** `VEDAGRAPH.AVS.ROTH_WHITNEY_1856.TRANSCRIPTION`  
**Build script:** `scripts/build_atharvaveda_canonical.py`  
**Parser version:** `bsb-1856-devanagari-v2`  
**Build timestamp:** `2026-09-08T00:00:00Z` (fixed, not clock-derived)

---

## Release gate: BLOCKED

The canonical AV release is in **calibration phase**, and calibration did not
clear. The full two-pass transcription of the 458 text leaves has not been
attempted, because the two-reader method does not currently produce
release-eligible text: on the one completed pair (leaf n15) **zero of eight
units were release-eligible**, the readers agreeing on unit boundaries and on
91.9% of skeleton characters but on only 11.4% of accent-mark positions. See
`ATHARVAVEDA_TRANSCRIPTION_QA.md` §1.

No `data/canonical/atharvaveda_bsb_1856_v1/` release directory exists from the
v2 pipeline, and none should be produced until that is resolved.

The `atharvaveda_pilot_v1` directory under `data/canonical/` is the rejected
v1 corpus. The v1 corpus used the `VEDAGRAPH.AVS.SEARCH_NORMALIZED` text
version, which is GRETIL-derived and fails the contamination firewall. It is
not used for any release computation and must not be cited as a v2 result.

---

## What the build script enforces

`scripts/build_atharvaveda_canonical.py` cannot produce a release unless:

1. **Source integrity:** the source artifact is
   `BSB.AV.SAUNAKA.ROTH_WHITNEY.1856.SCAN` and the source ID is `BSB_MDZ`.
2. **Contamination firewall:** `assert_no_contamination()` scans every text
   version for the prohibited markers `GRETIL`, `TITUS`, `VEDAWEB`,
   `ORLANDI`, `SACRED_TEXTS`. Any hit raises an error and aborts the build.
3. **Release eligibility:** only units with `release_eligible = True` in the
   reconciled JSONL become `Passage` records. Units with status
   `ACCENT_UNCERTAIN`, `CHARACTER_UNCERTAIN`, `BOUNDARY_UNCERTAIN`, or
   `STRUCTURAL_REVIEW_REQUIRED` are written to the uncertainty backlog at
   `data/transcriptions/atharvaveda_bsb_1856/v2/uncertainty_backlog.jsonl`.
4. **No merged readings:** a unit with two disagreeing readings produces no
   `text_devanagari` field in the reconciled JSONL and is therefore never
   released as text. Both original readings are preserved for audit.
5. **Deterministic build:** the build timestamp is fixed
   (`2026-09-08T00:00:00Z`), not read from the clock.

---

## Structural identity

The build uses the existing `avs_kanda_identity`, `avs_sukta_identity`, and
`avs_mantra_identity` functions. A mantra that occurs at the same structural
coordinate (kāṇḍa, sūkta, mantra) keeps the key, URN, and UUID it already
held. Nothing is renumbered because the 1856 edition presents a sūkta
differently from a previous edition.

The structural reconciliation (see `ATHARVAVEDA_STRUCTURE_RECONCILIATION.md`)
confirmed: 20 kāṇḍas, 731 sūktas (lower bound from running heads), mantra
total open. The build will produce as many records as the reconciled
transcription releases; it does not pad to an expected total.

---

## Source locators

Every released `Passage` will carry a `source_locator` of the form:

```
BSB/MDZ bsb10219750 canvas n32 (printed p. 18); policy bsb-1856-devanagari-v2
```

100% BSB/MDZ traceability is enforced at the build level: `source_locator()`
in the build script always names the canvas index and printed page.

---

## Uncertainty backlog

The build script writes every non-released unit to
`data/transcriptions/atharvaveda_bsb_1856/v2/uncertainty_backlog.jsonl`.
Each line is a JSON object with the unit's structural key, its
`transcription_status`, and both reader readings. This file is the machine-
readable record of what the release does not contain and why.

---

## Four-Veda release gate assessment

| Veda | Release state | Gate |
|---|---|---|
| Ṛgveda | `rigveda_full_v1`, 448 units in semantic pilot, tuning closed | SEALED |
| Sāmaveda | `samaveda_arcika_v1`, codepoint re-verification passed; 4 apparatus-lift units in backlog (`SV-APPARATUS-LIFT-01`) | CONDITIONAL |
| Yajurveda | `yajurveda_vsm_v1`; YV accent convention = convention A (same as AV), side gate passed | SEALED |
| Atharvaveda | v2 infrastructure complete; calibration phase in progress; full 458-leaf corpus not yet transcribed | **BLOCKED** |

**The four-Veda gate does not pass at this time.**

`ALL_FOUR_VEDA_CANONICAL_CORPORA_READY_FOR_FREEZE` cannot be output until
the full AV two-pass transcription completes, the reconciler grades all 458
leaves, and the build script produces a release with no prohibited-source
contamination. The estimated work remaining is approximately 916 bounded-
protocol leaf-passes at ~70k tokens each ≈ 64M tokens across multiple
sessions.

The gate will pass when:

1. The two-reader method clears its own fidelity gate — currently it does not,
   and no acceptance threshold has been set. Setting that threshold is a
   project-owner decision and depends on the accent-layer question in
   `ATHARVAVEDA_TRANSCRIPTION_QA.md` §6.2.
2. The 458 text leaves are transcribed twice and reconciled under the agreed
   method.
3. `data/canonical/atharvaveda_bsb_1856_v1/` (or equivalent) exists and is
   committed — which also requires resolving `SV-UNTRACKED-RELEASE-01`, since
   `data/canonical/**` is currently gitignored.
4. `assert_no_contamination()` clears with exit 0.
5. Adversarial release QA runs against the built corpus and passes.

Note that a non-empty `uncertainty_backlog.jsonl` is expected and is not a
failure signal; an *empty* one on a corpus this difficult would itself warrant
suspicion.
