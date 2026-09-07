# Work Packet: Yajurveda Primary-Text Closure

**Work:** `VG:WORK:YV:VSM` (Śukla Yajurveda, Vājasaneyi Mādhyandina)
**For:** a future Opus agent assigned to `FOUR_VEDA_CANONICAL_SANSKRIT_BLOCKER_CLOSURE`, Agent B lane.
**This packet does not solve the problem.** It states what is already known, cites the evidence,
and lists what remains.

---

## Current verified state

- Rights are **CLEAR**: Sanskrit Wikisource Mādhyandina text, `CC_BY_SA` (both layers), no
  encumbered link in the chain of title.
- Edition is **named**: Vāsudeva Śarmā Paṇaśīkara, 2nd edn, Nirṇaya Sāgara Press, Bombay, Śaka
  1850 = CE 1929, with Uvaṭa's *Mantrabhāṣya* and Mahīdhara's *Vedadīpa*. Found on a **sibling
  preface page**, not the per-adhyāya header — an empty header is not proof of an unidentified
  edition (contrast the Sāmaveda GRETIL TEI, whose emptiness has no rescuing sibling page).
- Hierarchy is **FINAL**: `Adhyaya -> Mantra`, two levels, no Sukta. `identity_status: FINAL` in
  `data/registry/works.yaml`.
- The artifact decomposes into **two text layers, neither of which is both faithful and
  complete**:
  - `WIKISOURCE_SA.YV.VSM.UNACCENTED` — 1,836/1,975 mantras, faithful direct transcription,
    `TextRole.PARALLEL_TEXT`.
  - `WIKISOURCE_SA.YV.VSM.ACCENTED` — 1,958/1,975 mantras, **extraction-derived**
    (`TextRole.EXTRACTED_FROM_CONTAINER`). The adapter infers the mūla boundary from
    accent-presence, not from the edition's own ordinal headers.
- The 1929 edition **does** use a standard mūla–bhāṣya layout with explicit ordinal headers
  ("तत्र प्रथमा।" etc.). Measured across 6 sampled adhyāyas: 271 ordinal-header lines against
  293 accented records. This was proved by test, not assumed — see
  `docs/pilots/YAJURVEDA_PILOT.md` "This work has NO PRIMARY_TEXT layer".
- A known variant exists at VSM 16.37: the page prints the mantra **twice**
  (`स्रुत्याय` / `सत्याय`). The current build keeps the first occurrence and records the drop as
  `SourceAssertion` status `NEEDS_REVIEW` (`SECOND_READING_DROPPED`).
- `data/registry/text_versions.yaml` (via `load_text_versions()`) is the single source of truth
  for `TextRole`; the build no longer chooses a role in code. An unregistered text-version id
  falls back to `COMPARISON_ONLY`.
- Traditional metadata: 203 `HAS_RISHI` assertions in the pilot (4 sampled adhyāyas), all
  `UNREVIEWED`; a full-40-adhyāya run is projected (not yet built) at **~2,106** assertions,
  stated in `docs/pilots/YAJURVEDA_PILOT.md` "Scale-up readiness".
- `HAS_DEVATA` and `HAS_CHANDAS` are asserted for **nothing**, deliberately: the
  *Sarvānukramaṇa-sūtra* states many yajus have no metre at all, and its devatā co-domain
  includes ritual implements, so Rigveda-derived assumptions may not be transferred.

## Exact blocker

**Can we deterministically produce a faithful 1,975/1,975 `PRIMARY_TEXT` layer from the
already-approved artifact without making philological guesses?**

Not yet — both existing layers fail one of the two conditions, and one of the two named
interventions (VSM 16.37) is a genuine editorial choice that must not be made unilaterally.

## Evidence already in the repository

- `docs/FOUR_VEDA_SOURCE_ADJUDICATION.md` §3.3 — full adjudication, corrections CORR-4/CORR-9.
- `docs/FOUR_VEDA_RIGHTS_MATRIX.md` §3.3 — rights decision table.
- `docs/FOUR_VEDA_STRUCTURAL_MODEL.md` §5 item 11 — the governing principle: "a role describes
  the layer AS PRODUCED, not the structure the source could support."
- `docs/pilots/YAJURVEDA_PILOT.md` — full pilot report, parser design decisions, QA results,
  the "NO PRIMARY_TEXT layer" finding in detail, and "Scale-up readiness".
- `docs/reports/YAJURVEDA_SOURCE_RESEARCH.md` — named blockers for translation, padapāṭha-backed
  lexical layer, devatā/chandas, and audio (each separately, not part of this packet's scope).
- `data/registry/works.yaml` — `VG:WORK:YV:VSM` entry, `identity_status: FINAL`.
- `data/registry/text_versions.yaml` — registered roles for both text-version ids.
- `data/builds/yajurveda_pilot_v1.yaml` — pilot build config; field `leading_text_version`
  (renamed from `primary_text_version`) selects the comparison-driving layer without implying
  canonical status.
- `src/vedagraph/ingest/adapters/yajurveda_pilot.py` — current adapter implementation.

## Files likely relevant

- `src/vedagraph/ingest/adapters/yajurveda_pilot.py` (accented-layer extraction logic)
- `data/registry/text_versions.yaml`, `data/registry/works.yaml`
- `data/raw/wikisource_sa/2026-09-07/` (44 hashed snapshots — do not refetch unless pages have
  changed; snapshot hashes are pinned in the build config)
- `docs/pilots/YAJURVEDA_PILOT.md` (update after any implementation change)
- `data/canonical/yajurveda_pilot_v1/` (pilot output; a full-40 run would produce a new,
  separately versioned output directory, not overwrite this one)

## Questions requiring external research

- None strictly required to attempt the ordinal-header reimplementation — the header text is
  already present in the pinned snapshots. External research would only be needed if the
  ordinal-header approach still leaves a coverage gap after implementation.

## Engineering tasks likely required

1. Reimplement the accented-layer adapter to locate mūla boundaries from the declared ordinal
   headers (e.g. "तत्र प्रथमा।", "द्वितीया।", …), using accent-presence as a **confirming**
   signal rather than the sole boundary signal.
2. Re-run the full-40-adhyāya scan (already exercised for count reconciliation) and measure
   whether coverage reaches 1,975/1,975 on the reimplemented layer.
3. Update `TextRole` for the accented layer in `data/registry/text_versions.yaml` **only if**
   the reimplementation and its own measured accuracy support `PRIMARY_TEXT` — do not flip the
   registry value ahead of the implementation evidence, per the structural model's governing
   principle (role describes the layer as produced).
4. Add a stability test analogous to Rigveda's
   `test_passage_identity_is_stable_when_the_build_scope_grows` before any full-40 run is
   treated as canonical.
5. Design (schema-level) a nullable `chandas` field with an `anādiṣṭa`-vs-unknown reason code
   and a YV-specific `devatā` union type — flagged as a prerequisite for asserting YV
   `HAS_DEVATA`/`HAS_CHANDAS` at all, not part of the primary-text question itself but noted
   here because it blocks the next layer immediately after this one closes.

## Explicit forbidden shortcuts

- Do not resolve the VSM 16.37 variant unilaterally. It requires a recorded human philological
  decision (see `docs/FOUR_VEDA_STRUCTURAL_MODEL.md` §5 item 11).
- Do not select a `TextRole` in build code. Roles come from `data/registry/text_versions.yaml`
  via `load_text_versions()`; an unregistered id must fall back to `COMPARISON_ONLY`, never to a
  permissive default.
- Do not invent `HAS_DEVATA` or `HAS_CHANDAS` values by analogy with Rigveda.
- Do not treat the projected ~2,106 ṛṣi-assertion figure as already built; it is an
  extrapolation from a 4-of-40-adhyāya sample.
- Do not construct local `Source`/`SourceArtifact` records under invented ids — a prior
  regression on this exact pilot (the only one of the four Veda pilots to fail Agent F's G11
  registry-checksum gate) shows this asserts an unadjudicated rights claim. Use
  `load_sources()` / `load_source_artifacts()` and fail closed on an unregistered id.

## Exit criteria

- 1,975/1,975 primary Sanskrit passages carrying `TextRole.PRIMARY_TEXT`, **or** an explicit,
  registry-recorded statement that this cannot be produced from currently-approved sources and
  why.
- Source-faithful extraction with no silent variant selection.
- Deterministic rebuild (byte-identical), maintained.
- Passage IDs stable across the pilot-to-full-corpus scale-up (tested, not assumed).
