# Four-Veda Canonical Sanskrit Blocker Registry

**Compiled:** 2026-09-07 · **Checkpoint:** `dc7d202` (feat: establish four-Veda ingestion
architecture and remaining corpus pilots)
**Machine-readable mirror:** `data/source_registry/four_veda_canonical_sanskrit_blockers.yaml`
(moved from the originally-scoped `data/qa/` path, which is gitignored build-output space —
see the note in the YAML file)
**Purpose:** consolidate the current, evidence-backed state of the three open canonical-Sanskrit
blockers (YV, SV, AV) so the next session — `FOUR_VEDA_CANONICAL_SANSKRIT_BLOCKER_CLOSURE` — can
start from a single registry instead of re-deriving state from `FOUR_VEDA_SOURCE_ADJUDICATION.md`,
`FOUR_VEDA_RIGHTS_MATRIX.md`, `FOUR_VEDA_STRUCTURAL_MODEL.md` and the three pilot reports.

This document does not resolve anything. It restates what those documents already established, in
one place, with an explicit state vocabulary. Rigveda is out of scope: its Sanskrit layer is
`READY_WITH_LIMITATIONS` and its semantic layer is frozen at V3.2 pending human gold — see
[`docs/STATUS.md`](STATUS.md).

---

## 0. Blocker states

A blocker may carry **multiple simultaneous dimension states** — rights, engineering, source
identity and philological review are never collapsed into one value. The vocabulary is closed at
six members:

| State | Meaning |
|---|---|
| `OPEN_RESEARCH` | The fact needed is not yet known; more investigation (not engineering) would change the answer. |
| `OPEN_ENGINEERING` | The fact is known; a coding/parsing task remains to realize it in the corpus. |
| `OPEN_RIGHTS` | Redistribution/derivation permission is not established for the needed artifact. |
| `OPEN_PHILOLOGICAL_REVIEW` | A human editorial/variant-selection judgement is required (e.g. choosing between two attested readings). |
| `RESOLVED` | The dimension is closed and evidenced. |
| `DEFERRED_NONBLOCKING` | Known gap, explicitly not required for this closure (e.g. gāna coverage, Hindi translation). |

Per the adjudication reports' own closing method: a dimension is `OPEN_RESEARCH` only if new
*research* would change the label; if only a new *source* or a *different chain of title* would
change it, the correct label is `RESOLVED` for identity/rights-investigation purposes even when the
practical outcome is negative — the negative answer is itself the resolved state of that dimension.
Where this registry marks something `OPEN_RIGHTS` it means an unresolved *permission*, not an
unresolved *investigation*.

---

## 1. YV — Śukla Yajurveda / Vājasaneyi Mādhyandina (`VG:WORK:YV:VSM`)

**Verified repository facts** (`docs/FOUR_VEDA_SOURCE_ADJUDICATION.md` §3.3,
`docs/FOUR_VEDA_RIGHTS_MATRIX.md` §3.3, `docs/pilots/YAJURVEDA_PILOT.md`,
`data/registry/works.yaml`):

| Fact | Status |
|---|---|
| 40 adhyāyas, 1,975 mantra addresses | **CONFIRMED** — computed from the full-artifact scan the pilot's adapter already runs (`YAJURVEDA_PILOT.md` "Scale-up readiness") |
| Hierarchy `Adhyaya -> Mantra`, two levels, no Sukta | **CONFIRMED**, `identity_status: FINAL` in `works.yaml` |
| Sanskrit Wikisource artifact rights-clear | **CONFIRMED** — `CC_BY_SA`, both layers, `FOUR_VEDA_RIGHTS_MATRIX.md` §3.3 |
| Edition identified: Paṇaśīkara / Nirṇaya Sāgara Press / 1929 | **CONFIRMED** — found on a sibling preface page, not the per-adhyāya header (`FOUR_VEDA_SOURCE_ADJUDICATION.md` §3.3, CORR-4) |
| Faithful layer incomplete | **CONFIRMED** — `WIKISOURCE_SA.YV.VSM.UNACCENTED`, 1,836/1,975, `PARALLEL_TEXT` |
| Complete layer cannot be labelled `PRIMARY_TEXT` | **CONFIRMED** — `WIKISOURCE_SA.YV.VSM.ACCENTED`, 1,958/1,975, `TextRole.EXTRACTED_FROM_CONTAINER`; role governed by `data/registry/text_versions.yaml` via `load_text_versions()` |
| VSM 16.37 variant requires explicit review | **CONFIRMED** — page prints `स्रुत्याय` / `सत्याय` twice; current build keeps the first and records `SECOND_READING_DROPPED` as `NEEDS_REVIEW` |
| Ordinal-header reconstruction is a possible technical path | **CONFIRMED, NOT ATTEMPTED** — 271 ordinal-header lines measured against 293 accented records across 6 sampled adhyāyas; adapter currently infers mūla start from accent-presence only |
| ~2,106 machine-readable ṛṣi assertions at full scale | **PROJECTED, NOT YET BUILT** — pilot has 203 across 4 sampled adhyāyas; full-40 figure is a stated extrapolation in `YAJURVEDA_PILOT.md`, not a completed run |
| No devatā/chandas claims invented | **CONFIRMED as policy** — Sarvānukramaṇa-sūtra states many yajus have no metre at all; schema does not yet carry a nullable-with-reason-code chandas field for YV |

**Primary blocker question:** *Can we deterministically produce a faithful 1,975/1,975
`PRIMARY_TEXT` layer from the already-approved artifact without making philological guesses?*

| Dimension | State | Note |
|---|---|---|
| Rights | `RESOLVED` | Both layers CC BY-SA 4.0; no encumbered link in the chain (`FOUR_VEDA_SOURCE_ADJUDICATION.md` §3.3) |
| Source identity | `RESOLVED` | Edition named (1929 Nirṇaya Sāgara), artifact complete |
| Engineering | `OPEN_ENGINEERING` | Reimplement the accented-layer adapter to read the declared ordinal headers (with accent-presence as confirmation, not sole signal); would likely also recover the 17 mantras the accented layer currently lacks |
| Philological review | `OPEN_PHILOLOGICAL_REVIEW` | VSM 16.37 variant selection (`स्रुत्याय` vs `सत्याय`) must be a human decision, not unilateral |
| Metadata schema | `OPEN_ENGINEERING` | Nullable `chandas` with `anādiṣṭa`-vs-unknown reason code, and a YV-specific devatā union type, do not exist yet |

**Answer as of this checkpoint:** *not yet* — the artifact and rights are sufficient, but the
existing adapter implementation does not produce a layer that is both faithful and complete, and
one variant decision requires human review before any full-40 run.

---

## 2. SV — Sāmaveda / Kauthuma (`VG:WORK:SV:KAU`)

**Verified repository facts** (`docs/FOUR_VEDA_SOURCE_ADJUDICATION.md` §3.2,
`docs/FOUR_VEDA_RIGHTS_MATRIX.md` §3.2, `docs/FOUR_VEDA_STRUCTURAL_MODEL.md` §2/§7,
`docs/pilots/SAMAVEDA_PILOT.md`, `data/registry/works.yaml`):

| Fact | Status |
|---|---|
| Parser works | **CONFIRMED** — pilot: 3,714 verse lines → 1,868 verse keys from a TEI with no structural markup; 12/12 own gates PASS, byte-identical rebuild over 3 runs |
| Hierarchy discovery works | **CONFIRMED** — 5 levels (`Arcika, Prapathaka, Ardha, Dasati, Verse`), variable depth (1–5), absent levels encoded `0`; corroborated by 2 independent textual witnesses (Sanskrit Wikisource, Griffith 1895/Benfey) + 1 independent addressing scheme (TITUS, text non-independent) |
| Dasati correction exists | **CONFIRMED** — supersedes the earlier VHP-derived guess `[Arcika, Prapathaka, Ardha, Adhyaya, Khanda, Mantra]`; the fourth level is `Dasati`, there is no `Adhyaya`/`Khanda` identity level (`works.yaml` note, `FOUR_VEDA_STRUCTURAL_MODEL.md` §2, §5.2) |
| Canonical identity/key not final | **CONFIRMED** — `identity_status: RESEARCH_REQUIRED`, `key_pattern: null`; `sv_mantra_identity`/`sv_container_identity` produce **candidate** keys only, explicitly not frozen |
| Wikisource rights position better than Pandey/GRETIL/TITUS lineage | **CONFIRMED** — Sanskrit Wikisource (`CC_BY_SA`, 840 pages) proved textually independent of the Pandey 1998/99 e-text that GRETIL, TITUS and Sanskrit Library all republish under contradictory or self-negating licences |
| Edition identity/provenance remains the key issue | **CONFIRMED** — the blocker is no longer "no witness exists"; it is that no witness combines an **identified printed edition** with **redistribution rights**. Wikisource clears rights, not edition; GRETIL clears neither |
| Structural count discrepancy ~1,868 vs 1,875 | **CONFIRMED, UNRECONCILED** — 1,868 computed verse keys vs the edition's own printed running-number claim of 1,875; a 7-verse gap, partly explained (one line lost to `UNPARSEABLE_REFERENCE_LABEL`, one verse index of 0 fails closed) but not fully accounted for |
| Gāna must not be forgotten | **CONFIRMED as explicit scope limit, not yet addressed** — `VG:WORK:SV:KAU` addresses the arcika (verse) text only; ~2,639 gānas vs 1,875 arcika verses is a **larger**, parallel body requiring its own future `work_id`. Sanskrit Wikisource carries all four gāna books as reusable text |
| Audio inventory contains a mirrorable Commons path | **CONFIRMED** — 474 Wikimedia Commons files (458 `CC_BY_SA`, 16 `CC0`), verified per file; the **only** mirrorable audio across all four Vedas |

**Primary blocker question:** *Can we establish a redistributable, edition-defensible Kauthuma
canonical witness and freeze stable passage identity?*

| Dimension | State | Note |
|---|---|---|
| Rights | `RESOLVED` (for primary Sanskrit + audio) | Wikisource `CC_BY_SA` cleared by proven textual independence; 474 Commons audio files cleared per-file |
| Source/edition identity | `OPEN_RESEARCH` | Wikisource is a community transcription with no single named printed edition; needs either a traced printed edition or a different acquisition route (written consent from the Pandey rights holder, or a fresh PD transcription) |
| Structural count | `OPEN_RESEARCH` | 1,868 vs 1,875 gap not fully explained; needs a second complete edition or closer source inspection, not more engineering |
| Engineering | `RESOLVED` (parser/hierarchy) | Parser and hierarchy discovery already work against the selected GRETIL structure and are corroborated independently; **not yet re-pointed at Wikisource as the rights-clear primary source** — that re-pointing is `OPEN_ENGINEERING` |
| English translation | `DEFERRED_NONBLOCKING` for this closure, but recorded — a GAP, not a blocker for Sanskrit identity (Wikisource Griffith is empty; sacred-texts Griffith is the wrong recension, Rāṇāyanīya) |
| Gāna coverage | `DEFERRED_NONBLOCKING` — explicit future `work_id`, not required to close the arcika canonical-Sanskrit question |

**Answer as of this checkpoint:** rights are solved and hierarchy is corroborated; the remaining
blocker is edition identity for the count-reconciled witness, which is a research question, not an
engineering or rights one.

---

## 3. AV — Atharvaveda / Śaunaka (`VG:WORK:AV:SAU`)

**Verified repository facts** (`docs/FOUR_VEDA_SOURCE_ADJUDICATION.md` §3.4,
`docs/FOUR_VEDA_RIGHTS_MATRIX.md` §3.4, `docs/pilots/ATHARVAVEDA_PILOT.md`,
`data/registry/works.yaml`):

| Fact | Status |
|---|---|
| Parser works | **CONFIRMED** — 11,395 pāda-level tokens → 5,843 units across all 20 kāṇḍas, 0 unparsed tokens, byte-identical rebuild across two processes |
| 20 kāṇḍas | **CONFIRMED**, `identity_status: FINAL` |
| 731 sūktas | **CONFIRMED, computed from the artifact** — a real +1 divergence against the commonly cited 730, traced to edition-counting, not a parser defect |
| Current source-derived mantra count | **CONFIRMED, computed: 5,839 distinct mantras** (11,395 pādas; `Units` 5,843 exceeds distinct mantras by 4 locator collisions) — divergence against the commonly cited ~5,977 is reported, not resolved, and attributed to edition-relative verse totals (e.g. one Roth/Whitney verse = 8 Vishva Bandhu verses at 15.2.1) |
| Orlandi/TITUS/GRETIL/VedaWeb lineage cannot currently be used as redistributable canonical Sanskrit | **CONFIRMED** — all three hosting surfaces (TITUS, GRETIL `avs_*`, VedaWeb AVS Sanskrit) are proved to be **the same Petr/Vavroušek text**, i.e. one licensing dependency, not three; GRETIL is `REFERENCE_ONLY`, TITUS is `PERMISSION_REQUIRED`, root is Orlandi 1991 (still in copyright) |
| Paippalāda must never be substituted for Śaunaka | **CONFIRMED as enforced control** — `assert_saunaka_recension()` requires two independent in-artifact witnesses (document title + all 11,395 `AVŚ_`-prefixed locators) before any parse; GRETIL's Paippalāda TEI is never opened by this adapter |
| Roth & Whitney 1856 is the identified PD route | **CONFIRMED, NOT YET ACQUIRED** — public domain by age; no transcription or OCR has been performed (explicitly out of scope for this preflight and for the closure session per the source-adjudication ranking) |
| Permission from the rights holder is an alternative route | **CONFIRMED, NOT YET SOUGHT** — highest-ranked action in `FOUR_VEDA_SOURCE_ADJUDICATION.md` §7: one written permission to the TITUS Project would unlock TITUS + GRETIL + VedaWeb simultaneously |
| Existing encumbered digital text may be used only to the extent already recorded, never as a laundering base | **CONFIRMED as standing constraint** — every `TextVersion` in the pilot carries `rights_status: REFERENCE_ONLY`; the pilot exists to prove parsing/structure/translation-alignment machinery, not to seed a "clean" transcription |

**Primary blocker question:** *Can we obtain/build a legally clean, provenance-explicit Śaunaka
primary Sanskrit layer without laundering the modern Orlandi-derived digital text?*

| Dimension | State | Note |
|---|---|---|
| Rights | `OPEN_RIGHTS` | No clean primary Sanskrit source exists today; the encumbered lineage is reference-only |
| Source identity / recension | `RESOLVED` | Śaunaka proved from the artifact itself (title + all locators), Paippalāda excluded structurally |
| Engineering (parsing/hierarchy/translation alignment) | `RESOLVED` | Parser, identity functions, and citation-label-based translation alignment (never sequence-based) all proven against the full artifact |
| Structural count reconciliation | `OPEN_RESEARCH` | 731 vs 730 sūktas and 5,839 vs ~5,977 mantras both reported, neither proved against a second complete edition |
| Acquisition of a clean route | `OPEN_RESEARCH` **and** `OPEN_RIGHTS` | Two independent unblock paths exist (Roth & Whitney 1856 PD transcription; TITUS Project written permission) — neither attempted; choosing/pursuing one is external research and correspondence, not engineering |

**Answer as of this checkpoint:** blocked on acquisition of a legally clean source. The engineering
and recension-verification machinery is proven and reusable the moment a clean source artifact is
obtained by either identified route.

---

## 4. Exit criteria

### YV exit criteria

- [ ] 1,975/1,975 primary Sanskrit passages carrying `TextRole.PRIMARY_TEXT`, **or** explicit,
  registry-recorded evidence that this cannot be produced from currently-approved sources
- [ ] Source-faithful extraction: no silent variant selection — VSM 16.37 resolved by recorded
  human review, not left as a silent first-occurrence pick
- [ ] Deterministic rebuild (byte-identical), as already demonstrated by the pilot
- [ ] Passage IDs stable across the pilot → full-corpus transition (already tested by
  `test_passage_identity_is_stable_when_the_build_scope_grows` pattern used for Rigveda; an
  equivalent test is required for YV before scale-up)

### SV exit criteria

- [ ] Canonical witness/source decision recorded in `data/registry/works.yaml`
  (`identity_status` moves off `RESEARCH_REQUIRED`)
- [ ] Recension Kauthuma re-confirmed against whichever witness is finally selected
- [ ] Edition/provenance decision: a named printed edition, or an explicit registry statement that
  none exists and the identity is being frozen on the transcription alone with that risk recorded
- [ ] 1,868/1,875 discrepancy explained (not necessarily closed to zero, but the 7-verse gap
  accounted for by cause, the way the current 2-of-7 partial explanation already is)
- [ ] Stable identity/key frozen: `key_pattern` populated, `identity_status: FINAL`
- [ ] Arcika/gāna coverage distinction stated explicitly in any release note — no claim to "have
  the Sāmaveda" while holding only the arcika
- [ ] Deterministic rebuild maintained after any source re-pointing

### AV exit criteria

- [ ] Śaunaka source confirmed for whatever new artifact is introduced (via
  `assert_saunaka_recension()` or equivalent two-witness check)
- [ ] Redistributable, or otherwise project-approved, rights for the primary Sanskrit layer
- [ ] Source lineage independently traceable to a clean root (Roth & Whitney 1856, or a
  permissioned Orlandi/TITUS lineage) — explicitly not a "cleaned" derivative of the encumbered
  digital text
- [ ] Structural reconciliation: 731-sūkta and 5,839-mantra figures reconciled against or explained
  relative to a second complete edition, or explicitly left open with cause stated
- [ ] Deterministic passage identity preserved (existing `FINAL` hierarchy unchanged)
- [ ] Deterministic rebuild maintained

---

## 5. Cross-references

- Rights ground truth: [`FOUR_VEDA_RIGHTS_MATRIX.md`](FOUR_VEDA_RIGHTS_MATRIX.md)
- Source adjudication narrative: [`FOUR_VEDA_SOURCE_ADJUDICATION.md`](FOUR_VEDA_SOURCE_ADJUDICATION.md)
- Structural/identity model: [`FOUR_VEDA_STRUCTURAL_MODEL.md`](FOUR_VEDA_STRUCTURAL_MODEL.md),
  [ADR-017](decisions/ADR-017-four-veda-structural-model.md)
- Audio: [`FOUR_VEDA_AUDIO_SOURCE_INVENTORY.md`](FOUR_VEDA_AUDIO_SOURCE_INVENTORY.md)
- Pilots: [`YAJURVEDA_PILOT.md`](pilots/YAJURVEDA_PILOT.md), [`SAMAVEDA_PILOT.md`](pilots/SAMAVEDA_PILOT.md),
  [`ATHARVAVEDA_PILOT.md`](pilots/ATHARVAVEDA_PILOT.md)
- Work packets: [`work_packets/YAJURVEDA_PRIMARY_TEXT_CLOSURE.md`](work_packets/YAJURVEDA_PRIMARY_TEXT_CLOSURE.md),
  [`work_packets/SAMAVEDA_IDENTITY_SOURCE_CLOSURE.md`](work_packets/SAMAVEDA_IDENTITY_SOURCE_CLOSURE.md),
  [`work_packets/ATHARVAVEDA_PRIMARY_SOURCE_CLOSURE.md`](work_packets/ATHARVAVEDA_PRIMARY_SOURCE_CLOSURE.md)
- Orchestration for the closure session: [`work_packets/CANONICAL_SANSKRIT_CLOSURE_ORCHESTRATION.md`](work_packets/CANONICAL_SANSKRIT_CLOSURE_ORCHESTRATION.md)
- Stale-claim audit: [`qa/STALE_FOUR_VEDA_CLAIMS.md`](qa/STALE_FOUR_VEDA_CLAIMS.md)
