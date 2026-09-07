# Work Packet: Atharvaveda Primary-Source Closure

**Work:** `VG:WORK:AV:SAU` (Atharvaveda, Śaunaka)
**For:** a future Opus agent assigned to `FOUR_VEDA_CANONICAL_SANSKRIT_BLOCKER_CLOSURE`, Agent D lane.
**This packet does not solve the problem.** It states what is already known, cites the evidence,
and lists what remains. This is the one Veda where the primary blocker is legal acquisition, not
engineering — most of the engineering work is already proven and reusable.

---

## Current verified state

- **Parser works**, proven against the full artifact, not a sample: 11,395 pāda-level tokens →
  5,843 units across all 20 kāṇḍas, 22 distinct locator shapes handled, **0 unparsed tokens**
  (verified: the adapter regex matches all 11,395 tokens in the file). Byte-identical rebuild
  across two separate OS processes, all 14 output files.
- **20 kāṇḍas** — `identity_status: FINAL`, hierarchy `Kanda -> Sukta -> Mantra`.
- **731 sūktas**, computed from the artifact — a real **+1** divergence against the commonly
  cited 730. Every kāṇḍa's sūkta numbering is internally contiguous with no gaps; the divergence
  is attributed to which edition is being counted, not to a parsing defect.
- **Current source-derived mantra count: 5,839 distinct mantras** (11,395 pādas; `Units` count
  of 5,843 exceeds distinct mantras by 4 due to locator collisions, see below). This diverges
  from the commonly cited ~5,977 by −138; the plausible mechanism (one Roth/Whitney verse can
  equal several Vishva Bandhu verses — AVŚ 15.2.1 is *eight* Vishva Bandhu verses) is stated but
  **not proved**, pending a second complete edition with its own printed totals.
- **The Orlandi/TITUS/GRETIL/VedaWeb lineage cannot currently be used as redistributable
  canonical Sanskrit.** The key structural finding: TITUS, GRETIL's `avs_*.htm` files, and
  VedaWeb's AVS Sanskrit layer are **all the same Petr/Vavroušek text** — one licensing
  dependency wearing three hosting hats, not three independent sources. GRETIL self-declares
  `REFERENCE PURPOSES ONLY`; TITUS explicitly forbids republication; the shared root is
  **Orlandi, Pisa: Giardini, 1991**, a modern edition still in copyright.
- **Paippalāda must never be substituted for Śaunaka**, and this is enforced in code, not just
  policy: `assert_saunaka_recension()` runs before every parse and requires two independent
  in-artifact witnesses — the document title (must contain "atharvaveda" and "saunaka", must not
  contain "paippalada") and **every one of the 11,395 body locators** being prefixed `AVŚ_`
  (palatal sibilant). A snapshot failing either check raises `RecensionMismatchError`. GRETIL's
  Paippalāda TEI (`sa_paippalAdasaMhitA.xml`) is a recorded trap and is never opened by this
  adapter.
- **Roth & Whitney, Berlin 1856 is the only identified clean route** — public domain by age. No
  transcription or OCR of it has been attempted; this is explicitly out of scope for this
  preflight and remains out of scope until a future session decides to pursue it.
- **Permission from the TITUS Project is the alternative route**, and is ranked the
  **highest-value single rights action for this Veda** in
  `docs/FOUR_VEDA_SOURCE_ADJUDICATION.md` §7: because TITUS, GRETIL and VedaWeb all share one
  text, one written permission unlocks all three simultaneously. Not yet sought.
- **The existing encumbered digital text is used only to the extent already recorded** — every
  `TextVersion` produced by the pilot carries `rights_status: REFERENCE_ONLY`. The pilot exists
  to prove the parsing/recension-verification/translation-alignment machinery works, explicitly
  **not** to seed a text that could later be mistaken for an independently-sourced PD
  transcription. This distinction must be preserved by any future work on this Veda.
- English translation (Whitney/Lanman 1905 via VedaWeb) is a separate, already-resolved layer:
  `PUBLIC_DOMAIN`, 115/153 sampled mantras aligned by printed citation label (never sequence
  position), Kāṇḍa 20 (958 stanzas, ~16% of the Veda) is untranslated in the source itself — a
  gap in the Whitney tradition, not fixable by source-switching.
- A separate `/private/` TITUS resource returns the AVS plaintext with **HTTP 200 and no
  authentication**, despite being `robots.txt`-disallowed and labelled "TITUS Members only".
  Recorded explicitly as **still a restriction** — an unenforced restriction is still a
  restriction, and this must never be ingested.

## Exact blocker

**Can we obtain/build a legally clean, provenance-explicit Śaunaka primary Sanskrit layer
without laundering the modern Orlandi-derived digital text?**

Blocked on acquisition. The recension-verification and parsing machinery is proven and directly
reusable against a new source; no engineering work stands between "clean source acquired" and
"canonical Śaunaka primary text built."

## Evidence already in the repository

- `docs/FOUR_VEDA_SOURCE_ADJUDICATION.md` §3.4 — full adjudication, the shared-text finding, the
  two recorded traps (Paippalāda filename, `/private/` plaintext).
- `docs/FOUR_VEDA_RIGHTS_MATRIX.md` §3.4 — rights decision table, the "pointer, not a grant"
  argument.
- `docs/FOUR_VEDA_STRUCTURAL_MODEL.md` §2 (Atharvaveda section) — hierarchy is `FINAL` and
  unaffected by this closure; confirms Atharvaveda's Sukta genuinely is hymn-shaped, a real
  finding not a default mapping.
- `docs/pilots/ATHARVAVEDA_PILOT.md` — full pilot: recension verification (§4), two numbering
  systems as data (§5), parser failures (§6, including the six-renumbering-point Whitney-quote
  validation with 6/6 matched), translation alignment (§9), QA (§8).
- `docs/reports/ATHARVAVEDA_SOURCE_RESEARCH.md` — full candidate matrix, 8 investigated sources
  plus 3 non-candidates.
- `data/source_registry/atharvaveda_sources.yaml` — registered sources/artifacts.
- `data/registry/works.yaml` `VG:WORK:AV:SAU` entry — `identity_status: FINAL`.

## Files likely relevant

- `src/vedagraph/ingest/adapters/atharvaveda_gretil.py` (current adapter; recension check,
  parsing, translation alignment all live here — directly reusable against a new source with a
  different snapshot)
- `scripts/build_atharvaveda_pilot.py`, `scripts/fetch_atharvaveda_translation.py`
- `data/builds/atharvaveda_pilot_v1.yaml`
- `data/raw/gretil_avs/2026-09-07/`, `data/raw/vedaweb_avs/2026-09-07/` (existing hashed
  snapshots — reference-only, must not be treated as a laundering base for a "clean"
  transcription)
- `docs/manifests/atharvaveda_pilot_structure_v1.json` (computed structural totals)

## Questions requiring external research

- Is there an accessible public-domain scan of Roth & Whitney, Berlin 1856 (e.g. via
  archive.org, HathiTrust, or a library digitization project) suitable as a transcription or OCR
  source? This has not been searched for in this or any prior session.
- Would the TITUS Project actually grant permission if asked, and on what terms (attribution
  only? non-commercial only? full redistribution?) — this determines whether pursuing permission
  or pursuing a fresh 1856 transcription is the faster path.
- Is there a way to independently verify the 731-vs-730 sūkta and 5,839-vs-~5,977 mantra
  divergences against a second complete, citable edition (e.g. a printed Vishva Bandhu edition
  index) without touching the encumbered digital text?
- What is the actual rights holder for the Orlandi 1991 edition (Chatia Orlandi / Giardini
  publisher / an estate), in case a direct-permission route to the root rather than to TITUS is
  more tractable?

## Engineering tasks likely required

Only once a clean source is acquired by either route:

1. Register the new source/artifact in `data/registry/sources.yaml` /
   `data/registry/source_artifacts.yaml` with full rights evidence (verbatim licence or PD
   justification, retrieval date, chain-of-title notes) — do not construct local records under
   invented ids (a defect already found and fixed for this Veda's pilot: the earlier
   `GRETIL_AVS`/`VEDAWEB_AVS` local `Source` construction was overruled by the rights authority
   for exactly this reason).
2. Adapt `atharvaveda_gretil.py` (or fork it) to the new source's markup/locator conventions,
   keeping `assert_saunaka_recension()`'s two-witness check as a hard gate.
3. Re-run structural discovery against the new source and compare its computed sūkta/mantra
   counts against the existing 731/5,839 figures — do not silently adopt whichever count is
   more convenient; record both explicitly if they still diverge.
4. Update `rights_status` on the new `TextVersion` away from `REFERENCE_ONLY` only once the
   acquisition route's rights are actually established (PD-by-age proof, or a written
   permission), not preemptively.

## Explicit forbidden shortcuts

- Do not use the existing GRETIL/TITUS/VedaWeb `REFERENCE_ONLY` text as the hidden basis for a
  supposedly independent public-domain transcription. Any new artifact's provenance must trace
  cleanly to its own acquisition (a fresh 1856 scan, or a permissioned copy), not to a "cleaned
  up" version of the reference-only text.
- Do not substitute the Paippalāda recension for Śaunaka under any circumstance; keep
  `assert_saunaka_recension()`'s two-witness gate on any new source.
- Do not treat GRETIL's "COPYRIGHT AND TERMS OF USAGE AS FOR SOURCE FILE" as a grant — it is a
  pointer that resolves to a still-restrictive chain.
- Do not ingest the TITUS `/private/` AVS plaintext; an unenforced access restriction is still a
  restriction.
- Do not "fix" the 731-vs-730 or 5,839-vs-~5,977 divergence by renumbering, inserting, or
  dropping units to match a cited total.

## Exit criteria

- Śaunaka source confirmed via two independent in-artifact witnesses for whatever new artifact
  is introduced.
- Redistributable, or otherwise project-approved, rights for the primary Sanskrit layer.
- Source lineage independent of the Orlandi/TITUS/GRETIL/VedaWeb encumbered chain — traceable to
  its own clean acquisition.
- Structural counts (731 sūktas, 5,839 mantras) reconciled against, or explicitly explained
  relative to, a second complete edition.
- Deterministic passage identity preserved (`identity_status: FINAL`, hierarchy unchanged).
- Deterministic rebuild maintained.
