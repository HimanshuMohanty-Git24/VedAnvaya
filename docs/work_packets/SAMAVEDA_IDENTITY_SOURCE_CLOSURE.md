# Work Packet: Samaveda Identity & Source Closure

**Work:** `VG:WORK:SV:KAU` (Sāmaveda, Kauthuma)
**For:** a future Opus agent assigned to `FOUR_VEDA_CANONICAL_SANSKRIT_BLOCKER_CLOSURE`, Agent C lane.
**This packet does not solve the problem.** It states what is already known, cites the evidence,
and lists what remains.

---

## Current verified state

- **Parser works.** `docs/pilots/SAMAVEDA_PILOT.md`: 3,714 verse lines parsed into 1,868 verse
  keys from a TEI file with **no structural markup** (labels only). 12/12 own QA gates PASS.
  Byte-identical rebuild confirmed across 3 consecutive runs.
- **Hierarchy discovery works** and is corroborated, not assumed: 5 levels
  (`Arcika, Prapathaka, Ardha, Dasati, Verse`), variable depth (1 to 5 levels deep depending on
  arcika), absent levels encoded as literal `0` rather than omitted. Corroborated by:
  1. The selected source's own declared reference system (`arcika | prapathaka | ardha | dasati
     | verse | line`), read from the artifact body.
  2. **Two independent textual witnesses**: Sanskrit Wikisource (which *corrects* a GRETIL
     pāda-mislabelling — proof of independence, not argument for it) and Griffith 1895
     (translating Benfey/Rāṇāyanīya, predates Pandey by a century, independently uses "decade"
     as the fourth level).
  3. **One independent addressing scheme**: TITUS's 8-level Kauthuma address — vocabulary and
     arcika-count corroboration only; its **text** is not independent (same Pandey 1998/99
     e-text).
- **The Dasati correction exists and is committed.** `data/registry/works.yaml` supersedes the
  earlier VHP-derived guess `[Arcika, Prapathaka, Ardha, Adhyaya, Khanda, Mantra]`. There is no
  `Adhyaya` and no `Khanda` identity level. A test asserts the superseded names cannot creep
  back in.
- **Canonical identity/key is NOT final.** `identity_status: RESEARCH_REQUIRED`,
  `key_pattern: null`. `sv_mantra_identity` / `sv_container_identity` exist and are used by the
  pilot, but produce **candidate** keys/URNs only — explicitly not frozen, carrying a NOT FROZEN
  docstring warning.
- **Wikisource's rights position is substantially better than the Pandey lineage.** GRETIL,
  TITUS and Sanskrit Library all republish the same 1998/99 Anshuman Pandey e-text, whose own
  header forbids modification outright; their agreement is "the same defect twice, not
  corroboration." Sanskrit Wikisource (840 pages, `CC_BY_SA` 4.0) is proved textually
  independent — it corrects a GRETIL pāda-mislabelling at running verses 1–2 that a derivative
  copy could not have fixed.
- **Edition identity/provenance is the remaining key issue.** Wikisource clears the rights bar
  but is a community transcription with **no single named printed edition**. GRETIL clears
  neither bar (rights: `PERMISSION_REQUIRED`; edition: `sourceDesc/bibl` affirmatively empty,
  with no rescuing sibling page — contrast Yajurveda).
- **Structural count discrepancy: 1,868 computed vs 1,875 claimed by the edition's own running
  numbers.** Partial explanation exists (one line lost entirely to a stray `rm ` prefix that
  matches no declared notation — `UNPARSEABLE_REFERENCE_LABEL`, also explaining why running
  number 1035 is absent; one verse index of `0` fails closed by design at `(4,6,2,16,0)`), but
  the full 7-verse gap is not accounted for.
- **Gāna must not be forgotten.** `VG:WORK:SV:KAU` addresses the arcika (verse) text **only**.
  The Kauthuma gāna corpus is estimated at **~2,639 gānas against 1,875 arcika verses** — the
  sung dimension is the **larger** artifact, and is why Sāmaveda is a distinct Veda rather than
  a Rigveda excerpt. Sanskrit Wikisource carries all four gāna books as reusable text; this is
  real future work, not hypothetical, and needs its own `work_id`.
- **Audio inventory contains a mirrorable Commons path.** 474 Wikimedia Commons sāman/gāna
  files, verified per-file: 458 `CC_BY_SA` 4.0, 16 `CC0`. This is the **only** mirrorable audio
  across all four Vedas.
- English translation is a confirmed **GAP**, not resolved and not part of this packet's
  identity question: registered Wikisource Griffith Sāmaveda has no verse text (934 words,
  zero resolving chapter links); the only complete Griffith Sāmaveda (sacred-texts.com) is the
  wrong recension (Rāṇāyanīya, following Benfey).

## Exact blocker

**Can we establish a redistributable, edition-defensible Kauthuma canonical witness and freeze
stable passage identity?**

Not yet — rights are solved (Wikisource) and hierarchy is corroborated, but no witness combines
an identified printed edition with redistribution rights, and the 1,868/1,875 count gap is
unreconciled.

## Evidence already in the repository

- `docs/FOUR_VEDA_SOURCE_ADJUDICATION.md` §3.2 — full adjudication, the Pandey-lineage argument,
  CORR-2/CORR-3.
- `docs/FOUR_VEDA_RIGHTS_MATRIX.md` §2.2–2.4, §3.2 — the self-contradicting-artifact case study
  and decision table.
- `docs/FOUR_VEDA_STRUCTURAL_MODEL.md` §2 (Samaveda section), §7.1 — the exact, narrowed
  statement of what remains open.
- `docs/pilots/SAMAVEDA_PILOT.md` — full pilot report: structural sampling, declared source
  defects (§8), QA (§9).
- `docs/reports/SAMAVEDA_SOURCE_RESEARCH.md` — source-candidate research narrative.
- `data/registry/works.yaml` `VG:WORK:SV:KAU` entry — carries the single most complete written
  account of the hierarchy finding, including the exact candidate key/URN forms.
- `data/source_registry/samaveda_sources.yaml` — registered sources/artifacts for the pilot.
- `docs/FOUR_VEDA_AUDIO_SOURCE_INVENTORY.md` — full audio adjudication, the 474-file mirrorable
  set.

## Files likely relevant

- `src/vedagraph/ingest/adapters/samaveda_gretil.py`,
  `src/vedagraph/ingest/adapters/samaveda_wikisource.py`
- `scripts/build_samaveda_pilot.py`, `scripts/compare_samaveda_sources.py`
- `data/builds/samaveda_pilot_v1.yaml`
- `data/registry/works.yaml` (the `VG:WORK:SV:KAU` entry — `key_pattern` and `identity_status`
  are the fields that change on closure)
- `src/vedagraph/identity.py` (`sv_mantra_identity`, `sv_container_identity` — currently
  candidate-only, carry NOT FROZEN docstrings)
- `data/raw/gretil/2026-09-07/`, `data/raw/wikisource_sa/2026-09-07/`,
  `data/raw/wikisource_griffith_sv/2026-09-07/` (existing hashed snapshots)

## Questions requiring external research

- Does the Sanskrit Wikisource Kauthuma transcription trace to an identifiable printed edition
  on a sibling page, apparatus note, or edit-history discussion (the way the Yajurveda edition
  was found on a preface page rather than a per-adhyāya header)? This has not yet been searched
  for Sāmaveda specifically.
- Is there a public-domain-by-age printed Kauthuma edition (pre-1930, non-Rāṇāyanīya) whose
  verse count could adjudicate the 1,868-vs-1,875 discrepancy independently of Pandey and of
  Wikisource?
- Would written consent from the Pandey-lineage rights holder (if locatable) be a realistic
  route, given the Sanskrit Library and GRETIL both already treat the text as CC-licensable
  despite the upstream prohibition?
- The two "defeated automated inspection" gāna leads named in
  `FOUR_VEDA_SOURCE_ADJUDICATION.md` §7 action 6 (shaivam.org, vedamu.org) — out of scope for
  identity closure, but worth flagging if a research pass is being scoped anyway.

## Engineering tasks likely required

1. Re-point the primary-Sanskrit build path at Sanskrit Wikisource rather than the GRETIL TEI
   (parser/hierarchy logic is proven; the adapter for Wikisource Kauthuma pages needs to be
   built or extended — check whether `samaveda_wikisource.py` already covers this before writing
   a new adapter).
2. Re-run structural discovery against the Wikisource artifact and re-verify the 5-level
   hierarchy and depth-variability findings hold on the new source (they were corroborated
   against it already at the textual-independence level, but a full structural build has not
   been run against Wikisource as primary).
3. Investigate the 1,868/1,875 gap on whichever source is finally selected: characterize each of
   the 7 missing verses individually (one is already known — the `rm `-prefixed line; one more
   is the `(4,6,2,16,0)` fail-closed case) rather than treating the gap as a single unexplained
   number.
4. Only after an edition decision: populate `key_pattern` in `data/registry/works.yaml` and flip
   `identity_status` to `FINAL`, then unfreeze `sv_mantra_identity`/`sv_container_identity` from
   candidate to canonical (remove the NOT FROZEN docstring warnings).
5. Mirror the 474 Wikimedia Commons audio files as a separate, already-cleared workstream — not
   gated on the identity decision above, but should not be silently skipped once identity closes
   since it is the one clearly actionable "yes" in this Veda's rights picture.

## Explicit forbidden shortcuts

- Do not treat GRETIL, TITUS and Sanskrit Library agreeing on a Pandey-lineage text as
  corroboration — it is the same defect counted three times.
- Do not freeze `key_pattern` before an edition decision is made; the hierarchy is settled, the
  key is not, and the distinction is deliberate (an observation vs. a permanent commitment).
- Do not fill the 1,868/1,875 gap by renumbering or inserting inferred verses.
- Do not claim "the Sāmaveda" is covered while holding only the arcika text — the gāna scope
  limit must be stated in any release note.
- Do not align an English translation to this work by sequence position (the `ADR-010` error);
  the sacred-texts Griffith is a different recension (Rāṇāyanīya) and must not be used as if it
  were Kauthuma.
- Do not construct local `Source`/`SourceArtifact` records under invented ids; use the registry
  loaders and fail closed on an unregistered id (see the SV-2 defect already found and fixed in
  the pilot).

## Exit criteria

- Canonical witness/source decision recorded in `data/registry/works.yaml`.
- Recension Kauthuma re-confirmed against the selected witness.
- Edition/provenance decision recorded — a named printed edition, or an explicit registry
  statement that none exists and identity is being frozen on the transcription alone, with that
  risk stated.
- 1,868/1,875 discrepancy explained (verse-by-verse where possible).
- Stable identity/key frozen (`identity_status: FINAL`).
- Arcika vs. gāna coverage distinction stated explicitly wherever this Veda's coverage is
  described.
- Deterministic rebuild maintained after any source re-pointing.
