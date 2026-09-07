# Stale Four-Veda Claims Audit

**Compiled:** 2026-09-07 · **Checkpoint:** `dc7d202`
**Scope:** documentation statements that contradict the latest adjudication
(`docs/FOUR_VEDA_RIGHTS_MATRIX.md`, `docs/FOUR_VEDA_SOURCE_ADJUDICATION.md`,
`docs/FOUR_VEDA_STRUCTURAL_MODEL.md`), found by search rather than by rewriting documentation.

**Per the governing instruction for this session: nothing below was fixed except where leaving it
unchanged would cause the next coding agent to execute incorrect work.** In every case found, the
authoritative newer document already states the correction and already names the stale document
as needing an update by its owner (see `FOUR_VEDA_STRUCTURAL_MODEL.md` §7 item 2), so this audit
records rather than duplicates that flag.

---

## Findings

| # | File | Stale claim | Current verified replacement | Severity | Owner | Must fix before full ingestion? |
|---|---|---|---|---|---|---|
| 1 | [`docs/architecture/ID_SPEC.md`](../architecture/ID_SPEC.md) lines 31–32 | "Samaveda Kauthuma: intentionally unresolved until an edition and complete structural mapping are selected. A single running number is not an adequate identity." | The hierarchy **is** resolved and corroborated (`Arcika, Prapathaka, Ardha, Dasati, Verse`, 5 levels, variable depth). Only the **key** (identity commitment) remains unresolved, and for a narrower, now-stated reason: no witness combines an identified printed edition with redistribution rights. `identity_status: RESEARCH_REQUIRED` in `data/registry/works.yaml`, not "intentionally unresolved" in the open-ended sense this line implies. | MEDIUM | shared-contract single writer (`identity.py`, `schema.py`) | Yes — a reader of `ID_SPEC.md` alone would not know the hierarchy is settled and would risk re-deriving it or treating the blocker as broader than it is. |
| 2 | [`docs/architecture/SOURCE_POLICY.md`](../architecture/SOURCE_POLICY.md) lines 14–17 | "Samaveda finding: Kauthuma is divided into Purvarcika and Uttararcika. The pages expose nested Kanda/Adhyaya/Prapathaka/Ardha groupings and local plus parenthesized numbering. … Samaveda identity remains open." | **Superseded, explicitly, by name.** `data/registry/works.yaml` and `docs/FOUR_VEDA_STRUCTURAL_MODEL.md` §2/§5 item 2 state this exact `Kanda/Adhyaya/Prapathaka/Ardha` guess is wrong: there is **no** `Adhyaya` and **no** `Khanda` identity level; the correct fourth level is **Dasati**; there are **four** arcikas (Purvarcika, Aranya, Mahanamnya, Uttararcika), not two. A test asserts the superseded names cannot creep back into code. | HIGH | shared-contract single writer | **Yes.** This is a wrong hierarchy vocabulary, not merely an incomplete one — a coding agent implementing against this line would write container levels that the identity functions and the committed registry note explicitly reject. |
| 3 | [`docs/STATUS.md`](../STATUS.md) — entire "BLOCKED" section (line ~284–290) and the rest of the document | Predates all four-Veda work: no mention of the rights matrix, source adjudication, structural model, or any of the three pilots. The one Samaveda line present ("Samaveda Kauthuma canonical identity awaits edition-level hierarchy/citation research") is still directionally true but does not reflect that the Sanskrit-source rights question is now `RESOLVED` (Wikisource) and the blocker is narrowly the edition bar — nor does it mention Yajurveda or Atharvaveda progress at all. | LOW-MEDIUM (omission, not a false statement) | `docs/STATUS.md` owner | No — `STATUS.md` is a running project log, not a spec; a coding agent working the four-Veda closure would consult `docs/FOUR_VEDA_*` and the pilot docs directly, which are current. Recorded so `STATUS.md`'s next update includes the four-Veda section rather than this audit being mistaken for "nothing was missed." |

## Examples checked and found NOT stale

Recorded so a future session does not re-check the same list without cause (per the example
categories named in the session brief):

- ~~**"Samaveda already having frozen canonical IDs"** — not found anywhere. Every reference
  correctly states `RESEARCH_REQUIRED` / candidate-only.~~
  **THIS ENTRY WAS WRONG. Corrected 2026-09-07 by the
  `SAMAVEDA_CANONICAL_IDENTITY_FINAL_CLOSURE` run.** The claim *was* being asserted as current,
  in [`docs/reports/FOUR_VEDA_QA_REPORT.md`](../reports/FOUR_VEDA_QA_REPORT.md) §5.2:
  *"Samaveda identity is **PROVISIONAL**, not FINAL: `key_pattern` is now set and
  `identity_status` moved `RESEARCH_REQUIRED -> PROVISIONAL`."*
  Worse than stale — **it was never true.** `git log --all -S PROVISIONAL -- data/registry/works.yaml`
  returns nothing: no such state has existed in any commit. Now corrected in place, with the
  correction recorded above the replacement text rather than by silent deletion.
  **Why this audit missed it — a second, distinct scope gap.** The earlier miss recorded below
  was a *file-type* gap: the audit searched `docs/` and not the YAML registries. This one is
  different and more uncomfortable: `docs/reports/FOUR_VEDA_QA_REPORT.md` **is** a `docs/`
  markdown file, squarely inside the declared scope. The miss came from searching for the claim
  in the vocabulary the *auditor* expected ("frozen", "FINAL") rather than the vocabulary the
  defect actually used (`PROVISIONAL`). **A closed-vocabulary field must be audited by
  enumerating every value the field can take, not by grepping for the value you expect to find
  wrongly asserted.** The correct probe is a search for each member of the `identity_status`
  vocabulary — and note that `identity_status` is not an enum in the schema, so its value space
  is unbounded, which is itself a defect recorded in the closure report.
- **"GRETIL containing Vājasaneyi"** — not claimed anywhere current; in fact
  `FOUR_VEDA_SOURCE_ADJUDICATION.md` §3.3 explicitly documents the opposite (`NO_ARTIFACT_EXISTS`,
  verified by exhaustive index search), and flags GRETIL's `maitrs_*` files as the
  easily-confused-for-it Kṛṣṇa Yajurveda.
- ~~**"Yajurveda edition unidentified"** — was true in an earlier state but is corrected
  (CORR-4) everywhere it now appears; no doc found still asserting it as current.~~
  **THIS ENTRY WAS WRONG. Corrected 2026-09-07 by the
  `FOUR_VEDA_CANONICAL_SANSKRIT_BLOCKER_CLOSURE` run.** The claim *was* still being asserted as
  current, in `data/source_registry/four_veda_source_matrix.yaml`, in three places on the
  `WIKISOURCE_SA` / `primary_sanskrit` / Śukla Yajurveda row: `edition: "UNIDENTIFIED. The page
  header carries EMPTY year, notes, author and translator fields."`, `blocking_item: "EDITION
  IDENTITY, not rights. The printed edition is unidentified…"`, and a `reason:` field asserting
  the artifact "carries the same edition-identity defect that independently disqualified the
  GRETIL Samaveda TEI" — the exact claim CORR-4 reversed. All three are now fixed.
  **Why this audit missed it — a scope gap worth fixing, not a slip.** Per the method note below,
  this audit grepped **`docs/` only**. The stale claim lived in `data/`, in the *machine-readable
  registry* — which is the more authoritative surface of the two, and the one a build actually
  reads. An audit scoped to prose cannot certify a repository whose operative claims are in YAML.
  **The deeper pattern, found by the same run:** `four_veda_source_matrix.yaml` has a
  `corrections_applied:` block, and a correction being *recorded* there did **not** mean it had
  been *applied* to the data rows. CORR-1 (TITUS `RESEARCH_ONLY` → `PERMISSION_REQUIRED`) and
  CORR-4 (this entry) were **both** recorded-but-unapplied. So this audit's "no doc found
  asserting it" was doubly defeated: it read the wrong surface, and on that surface the audit
  trail disagreed with the data it described. Corrections now carry an `applied_to_rows:` flag.
- **"Yajurveda traditional metadata unavailable"** — not current; the pilot has 203 `HAS_RISHI`
  assertions and traditional metadata is `CLEAR (SA)` per the rights matrix. No stale instance
  found.
- **"Atharvaveda current digital Sanskrit being redistributable"** — not claimed; every current
  doc states `REFERENCE_ONLY` / `PERMISSION_REQUIRED` and the pilot's own `TextVersion` records
  carry `rights_status: REFERENCE_ONLY`.
- **"Paippalāda being treated as Śaunaka"** — not found; actively guarded against in code
  (`assert_saunaka_recension()`) and named as a recorded trap in three separate documents.
- **"All audio being reference-only"** — not current; `docs/FOUR_VEDA_RIGHTS_MATRIX.md` §4 and
  §5 explicitly carve out the 474-file Sāmaveda Commons exception. `docs/STATUS.md` line 369's
  "Media remains reference-only" is scoped to the *Rigveda* Mandala-1 sample specifically and is
  still accurate for that scope — not a stale four-Veda claim.
- **"All three remaining Vedas being equally blocked"** — not found stated anywhere; every
  current document (rights matrix, source adjudication, structural model) is explicit that
  clarity is per-Veda **and** per-role, with a stated headline table showing three different
  Sanskrit-rights outcomes and three different structural-identity outcomes.

## Method note

This audit searched for the exact stale-claim shapes named in the session brief plus the two
superseded claims that `FOUR_VEDA_STRUCTURAL_MODEL.md` had already self-reported (§7 item 2), via
targeted grep across `docs/`, not a full read of every file. It is not a general documentation
audit and should not be read as certifying the rest of `docs/` current.
