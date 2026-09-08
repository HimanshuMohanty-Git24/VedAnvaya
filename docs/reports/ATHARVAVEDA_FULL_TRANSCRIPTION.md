# Atharvaveda transcription — full status report

**Work:** Atharvaveda Saṃhitā, Śaunaka recension (`VG:WORK:AV:SAU`)  
**Source:** Roth & Whitney, *Atharva-Veda Sanhita*, Erster Band: Text, Berlin:
Dümmler 1856. BSB/MDZ `bsb10219750`, artifact
`BSB.AV.SAUNAKA.ROTH_WHITNEY.1856.SCAN`, snapshot `2026-09-07`, 478 IIIF
leaves at width 4000.  
**Policy:** `bsb-1856-devanagari-v2`  
**As of:** 2026-09-08

---

## Scope

The 1856 print contains 478 canvases: 14 front matter, 458 numbered text
leaves (`n15` = printed p. 1 through `n472` = printed p. 458), and 6 back
matter. Only the 458 text leaves carry Saṃhitā text and are in scope for
transcription. Back matter is a publisher advertisement; it is catalogued but
not transcribed.

The structural reconciliation (see `ATHARVAVEDA_STRUCTURE_RECONCILIATION.md`)
established: 20 kāṇḍas, 731 sūktas (tight lower bound from running heads), and
a mantra count that cannot be determined without completing the full
transcription.

---

## Infrastructure built this phase

### Rendering

`scripts/crop_atharvaveda_leaf.py` (committed in `b8a2b62`) produces
accent-legible landscape bands from the 4000px IIIF leaf images. The root
cause of the v1 corpus failure was rendering: the 1856 Devanagari fount's
accent marks fall on akṣara boundaries when a whole leaf is downsampled to
the reader's 1568px long-edge cap, making them unassignable. Cropping to
landscape bands restores the cap to each band's width, making accent marks
unambiguously attached to their akṣara. All 458 text leaves were
pre-rendered to `scratch_av_crops/` with 0 rendering failures (1,036 PNG
files, ~708 MB).

### Reconciliation

`scripts/reconcile_atharvaveda_v2.py` grades any R1+R2 pair with the
following statuses:

| Status | Meaning |
|---|---|
| `VERIFIED_EXACT` | Identical codepoints, accents included |
| `VERIFIED_WITH_ORTHOGRAPHIC_NOTE` | Identical skeleton, accent layer absent from both |
| `ACCENT_UNCERTAIN` | Skeleton matches, accent placement differs or one reader dropped it |
| `CHARACTER_UNCERTAIN` | ≤25% skeleton divergence |
| `BOUNDARY_UNCERTAIN` | >25% skeleton divergence |
| `STRUCTURAL_REVIEW_REQUIRED` | One reader saw the unit, one did not |

Only `VERIFIED_EXACT` and `VERIFIED_WITH_ORTHOGRAPHIC_NOTE` are
release-eligible. The critical policy change from v1: agreement on a reading
that drops the accent layer produces `VERIFIED_WITH_ORTHOGRAPHIC_NOTE`, not
`VERIFIED_EXACT`. This is the exact failure mode the v1 corpus suffered (333
of 360 units, 50% agreement rate measuring the wrong thing).

### Build

`scripts/build_atharvaveda_canonical.py` (committed in `7c234ae`) builds
canonical records from reconciled data only. It:

- enforces the `ARTIFACT_ID = "BSB.AV.SAUNAKA.ROTH_WHITNEY.1856.SCAN"`
  provenance chain
- runs `assert_no_contamination()` against every text version before release
- writes non-released units to `data/transcriptions/atharvaveda_bsb_1856/v2/uncertainty_backlog.jsonl`
- uses a fixed `BUILD_TIMESTAMP` (`2026-09-08T00:00:00Z`) for deterministic builds

### Tests

`tests/unit/test_atharvaveda_transcription.py`: 31 tests, all passing. The
critical protected invariant: `test_agreement_on_an_unaccented_reading_is_not_verified_exact`.

### Policy documents

- `docs/policy/AV_TRANSCRIPTION_POLICY_V2.md`: policy `bsb-1856-devanagari-v2`
- `docs/policy/VEDIC_ACCENT_CONVENTION.md`: convention A frozen across all
  Devanagari corpora; YV structural proof documented; Unicode "UDATTA" naming
  trap warned

---

## OCR route: rejected

Tesseract produced 0 Devanagari codepoints from 317 characters on leaf 32
band 1. The 1856 Berlin fount is too far from modern Devanagari to route
through any available OCR engine. The result is recorded in
`data/transcriptions/atharvaveda_bsb_1856/v2/method_calibration_ocr.json`.

---

## Throughput constraint — the structural blocker

Two protocols were calibrated on a stratified sample:

### Full protocol (R1/leaf_00032)
- 128 tool calls, ~216k tokens per leaf-pass
- 13 units, 199 accent marks, 1 `[?]`
- Full corpus: 458 × 2 passes × 216k ≈ **197M tokens** (vs ~14.8M/session)

### Bounded protocol (B1: leaves 32 and 430)
- 12 tool calls, ~70k tokens per leaf-pass
- Leaf 32: 13 units, 172 accent marks, 0 `[?]`
- Leaf 430: 15 units, 163 accent marks, 2 `[?]`
- Both workers noted: **budget, not the page, was the limit**
- Full corpus: 458 × 2 passes × 70k ≈ **64M tokens** (vs ~14.8M/session)

The constraint is structural, not an optimisation problem. Even the bounded
protocol requires approximately **4.3 sessions** of the current session
budget per pass, or **8.6 sessions** for the full two-pass protocol. The
correct response is to document this precisely and continue the transcription
across multiple sessions using the validated method and pre-rendered leaves.

---

## Calibration data: what was transcribed

| File | Reader | Protocol | Units | Accent marks | `[?]` |
|---|---|---|---|---|---|
| `R1/leaf_00015.jsonl` | R1 | Full | 8 | 107 | 1 |
| `R2/leaf_00015.jsonl` | R2 | Bounded | 8 | 78 | 0 |
| `R1/leaf_00032.jsonl` | R1 | Full | 13 | 199 | 1 |
| `B1/leaf_00032.jsonl` | B1 | Bounded | 13 | 172 | 0 |
| `B1/leaf_00430.jsonl` | B1 | Bounded | 15 | 163 | 2 |

Leaf n15 is the one completed two-reader pair. Its reconciliation produced **0
release-eligible units**: unit boundaries agreed exactly, skeletons agreed to
91.9%, and the two readers placed only 19 of R1's 107 accent marks
identically. See `ATHARVAVEDA_TRANSCRIPTION_QA.md` for the full measurement,
the confound in the pairing, and the resulting decision packet.

---

## Production plan: on hold

**No method has been selected, and production transcription must not begin.**

The calibration measured two independent readings of leaf n15 and found **zero
release-eligible units**: the readers agreed on unit boundaries exactly and on
the consonant-vowel skeleton to 91.9%, but agreed on the position and type of
only 11.4% of the accent marks between them. The band-rendering fix made the
accent marks visible without making them assignable to the same syllable by two
readers. Full detail and the resulting decision packet are in
`ATHARVAVEDA_TRANSCRIPTION_QA.md`.

Throughput therefore stopped being the binding constraint. Choosing the cheaper
protocol is meaningless while neither protocol yields releasable text, and a
full run at ~64M tokens against an unfit method is the most expensive mistake
available here.

**Before production can start:**

1. A clean inter-reader baseline with both readers on the *same* protocol — the
   current pair is R1 (full) against R2 (bounded) and is confounded.
2. A project-owner decision on the accent layer: release the skeleton with
   accents withheld, raise accent fidelity with a targeted method and
   re-measure, or publish accents as an explicitly uncertain separate layer.

**When it does start:** each session runs a batch of R1 reads and a separate
batch of R2 reads for a contiguous leaf range, then
`scripts/reconcile_atharvaveda_v2.py` to grade the pairs and populate the
uncertainty backlog. All 458 leaves are pre-rendered in `scratch_av_crops/`.

**Remaining:** 458 leaves × 2 passes = 916 leaf-passes, minus the calibration
reads already landed.

**Independence:** the firewall (no cross-reader reads, no consulting any other
AV edition) is enforced structurally — R1 and R2 passes run in separate agents
that have never seen each other's files.

---

## Traceability

Every released unit will carry:
- `canvas_index`: the BSB/MDZ leaf number
- `mdz_image_id`: e.g., `bsb10219750_00032`
- `printed_page`: the printed page number (canvas − 14)
- `kanda`, `sukta`, `mantra`: read from the page itself
- `transcription_policy`: `bsb-1856-devanagari-v2`

100% BSB/MDZ traceability is enforced at the schema level.
