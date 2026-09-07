# Atharvaveda-Saṃhitā (Śaunaka) — Representative Pilot

**Work:** `VG:WORK:AV:SAU` · **Abbreviation:** AVS · **Recension:** Śaunaka (AVŚ)
**Hierarchy:** Kāṇḍa → Sūkta → Mantra (`identity_status: FINAL`, unchanged by this pilot)
**Build:** `data/canonical/atharvaveda_pilot_v1/` · **Config:** `data/builds/atharvaveda_pilot_v1.yaml`
**Executable:** `scripts/build_atharvaveda_pilot.py` · **Adapter:** `src/vedagraph/ingest/adapters/atharvaveda_gretil.py`
**Date:** 2026-09-07

---

## 1. What this pilot proves

| Capability | Evidence |
|---|---|
| Source acquisition | `PoliteFetcher` wrote two immutable hashed snapshots to `data/raw/gretil_avs/2026-09-07/`; rebuild reuses them from cache and never refetches |
| Recension verification | `assert_saunaka_recension()` requires two independent witnesses in the artifact itself before any parse (§4) |
| Parsing | 11,395 pada-level tokens → 5,843 units across all 20 kāṇḍas, 22 distinct locator shapes handled, 0 unparsed tokens (verified: the adapter regex matches all 11,395 tokens in the file) |
| Hierarchy | 10 kāṇḍa `SECTION` + 11 sūkta `HYMN` + 153 mantra `MANTRA` passages, all parents resolving |
| Identity | frozen `avs_kanda_identity` / `avs_sukta_identity` / `avs_mantra_identity`; every `entity_id` re-derived from its URN and verified |
| Sanskrit preservation | accented source stored verbatim; 153/153 `PRIMARY_TEXT` records test positive for accents; derived surfaces stored separately |
| Translation alignment | 115 independent `Translation` records, every one resolved through the translation's **printed** book.hymn.stanza label, never by sequence position (§9) |
| Provenance | verbatim licence sentence, edition basis and input credits read out of the artifact into `ARTIFACT_PROVENANCE` assertions; `Source` and `SourceArtifact` records read from `data/registry` and their pinned checksums cross-checked against the bytes actually read |
| Deterministic rebuild | **byte-identical across two processes, all 14 output files including `manifest.json`** (§8) |

---

## 2. Source selected, and the one honest caveat

**Primary Sanskrit:** GRETIL `avs_acu.htm` — *Atharvaveda-Saṃhitā, Śaunaka recension, ACCENTED TEXT*.

Chosen because it is the only accented, complete, machine-readable, structurally addressable
AVŚ text found whose recension can be proved from the artifact. Its edition basis, quoted
from the file:

> Based on the ed.: Gli inni dell' Atharvaveda (Saunaka), trasliterazione a cura di Chatia
> Orlandi, Pisa 1991, collated with the ed. R. Roth and W.D. Whitney: Atharva Veda Sanhita,
> Berlin 1856.
> Input by Vladimir Petr and Petr Vavrousek. TITUS redaction by Jost Gippert (31 January
> 1997). Text of Books 11-20 improved by Arlo Griffiths, Leiden 18 May 2000 and Philipp
> Kubisch, Bonn 13 March 2007. Revised by Arlo Griffiths, August 2009.

**Caveat, stated up front:** the artifact's own rights sentence is

> THIS GRETIL TEXT FILE IS FOR REFERENCE PURPOSES ONLY! COPYRIGHT AND TERMS OF USAGE AS FOR
> SOURCE FILE.

This is **not** a permissive licence. Every `TextVersion` in the pilot therefore carries
`rights_status: REFERENCE_ONLY`, and redistribution of the Sanskrit text is **not**
established. The clause is a *pointer*, and following it leads to TITUS — and behind TITUS to
**Orlandi, Pisa 1991, a modern transliteration still in copyright**. So a TITUS permission is
necessary but not sufficient. See `docs/reports/ATHARVAVEDA_SOURCE_RESEARCH.md` §10.

**Parallel Sanskrit:** GRETIL `avs___u.htm`, the *unaccented* sibling. Used for the
deterministic comparison in §7. It is **not** an independent witness — see §7.

**English translation:** VedaWeb 2.0 resource `696f42266f50da42570ad040` — Whitney &
Lanman (1905), per-stanza, `PUBLIC_DOMAIN`. See §9.

Full candidate matrix with verbatim rights evidence for all eight investigated sources plus
three explicit non-candidates: `data/source_registry/atharvaveda_sources.yaml`.
Adjudication narrative: `docs/reports/ATHARVAVEDA_SOURCE_RESEARCH.md`.

---

## 3. Computed structure (whole artifact, not the sample)

Machine-readable: `docs/manifests/atharvaveda_pilot_structure_v1.json`.
Every number below is **computed from the snapshot**, not taken from a reference work.

**Totals: 20 kāṇḍas · 731 sūktas · 5,839 distinct mantras · 11,395 padas.**

| Kāṇḍa | Sūktas | Sūkta gaps | Units | Padas | Single-pada units | Anuvāka `{N}` markers | Units with alternate citation |
|---:|---:|---|---:|---:|---:|---:|---:|
| 1 | 35 | none | 153 | 307 | 0 | 0 | 0 |
| 2 | 36 | none | 206 | 378 | 42 | 0 | 0 |
| 3 | 31 | none | 230 | 472 | 0 | 4 | 0 |
| 4 | 40 | none | 324 | 658 | 0 | 0 | 0 |
| 5 | 31 | none | 376 | 741 | 35 | 0 | 0 |
| 6 | 142 | none | 454 | 909 | 6 | 0 | 0 |
| 7 | 118 | none | 286 | 575 | 1 | 0 | 0 |
| 8 | 10 | none | 259 | 529 | 16 | 29 | 0 |
| 9 | 10 | none | 302 | 528 | 88 | 28 | 0 |
| 10 | 10 | none | 350 | 746 | 2 | 34 | 0 |
| 11 | 10 | none | 313 | 688 | 39 | 30 | 214 |
| 12 | 5 | none | 304 | 545 | 78 | 30 | 0 |
| 13 | 4 | none | 188 | 345 | 56 | 20 | 0 |
| 14 | 2 | none | 139 | 280 | 0 | 14 | 0 |
| 15 | 18 | none | 141 | 218 | 98 | 0 | 47 |
| 16 | 9 | none | 93 | 147 | 66 | 0 | 0 |
| 17 | 1 | none | 30 | 76 | 0 | 3 | 0 |
| 18 | 4 | none | 283 | 547 | 21 | 28 | 0 |
| 19 | 72 | none | 453 | 862 | 69 | 0 | 0 |
| 20 | 143 | none | 959 | 1844 | 85 | 0 | 0 |
| **Σ** | **731** | — | **5,843** | **11,395** | **702** | **220** | **261** |

`Units` exceeds `distinct mantras` by 4 because of the locator collisions in §6.
No kāṇḍa has a sūkta-numbering gap: sūkta numbering is 1..N contiguous in all twenty books.

### Reconciliation against stated counts

`extract_header_metadata()` searches the artifact preamble for any total and returns
**`stated_total_counts: ()`** — the artifact asserts no kāṇḍa, sūkta or mantra total
anywhere. There is therefore **no source-stated total to reconcile against for this
artifact**, and that absence is itself recorded (as `stated_total_counts_found: []` inside
the `ARTIFACT_PROVENANCE` assertion) rather than being papered over.

Against the count usually printed in reference literature (**730 hymns / ~5,977 verses**):

* **Sūktas: computed 731 vs cited 730 — a real +1 divergence, not a parser error.** The
  per-kāṇḈa distribution (35, 36, 31, 40, 31, 142, 118, 10, 10, 10, 10, 5, 4, 2, 18, 9, 1,
  4, 72, 143) sums to exactly 731 and each book is internally contiguous, so there is no
  spurious or missing hymn to find. The divergence lives in which *edition* is being
  counted, not in the parse.
* **Mantras: computed 5,839 vs cited ~5,977 — a −138 divergence.** This is reported as data.
  The plausible mechanism is visible in the artifact itself: in the paryāya books one
  Roth/Whitney verse can equal several verses of another edition (AVŚ 15.2.1 is *eight*
  Vishva Bandhu verses — §5), so a verse total is edition-relative. **This has not been
  proved and is not asserted.** Establishing it needs a second complete edition with its
  own printed totals, which this pilot did not have.

Neither divergence was "fixed". Nothing was renumbered, inserted or dropped to make a
total match.

---

## 4. Recension verification — how Śaunaka was proved, not assumed

GRETIL hosts **both** recensions, and they are different files:

* Śaunaka → `1_sanskr/1_veda/1_sam/avs_acu.htm`, `avs___u.htm` (legacy HTML)
* Paippalāda → `corpustei/sa_paippalAdasaMhitA.xml` (TEI) — **never opened by this adapter**

`assert_saunaka_recension()` runs before every parse and requires **two independent
witnesses inside the artifact**:

1. **Document title.** Must contain both *atharvaveda* and *saunaka*, and must not contain
   *paippalada*. Actual value: `Atharvaveda-Samhita, Saunaka recension, ACCENTED TEXT`.
2. **Body locators.** Every one of the 11,395 locators is prefixed `AVŚ_` (with the palatal
   sibilant) — e.g. `(AVŚ_1,1.1a)`. The recension marker is in the data, per verse, not just
   in a header that could belong to a swapped file.

A snapshot failing either check raises `RecensionMismatchError` rather than being ingested.

### Per-artifact accent status (established, not assumed)

| Artifact | Declares | Verified |
|---|---|---|
| `avs_acu.htm` | `ACCENTED TEXT` | **5,843 / 5,843 units** test positive under `has_vedic_accents()` |
| `avs___u.htm` | `UNACCENTED TEXT` | **0 / 5,843 units** test positive |

Accents are **combining Latin marks, not Devanagari svaras**. There is no U+0951/U+0952 and
no Vedic Extensions codepoint anywhere in these files:

* udātta = U+0301 combining acute, svarita = U+0300 combining grave
* they stack on letters that are themselves built from combining marks — vocalic r is
  `r` + U+0325 ring below, so *long vocalic r with udātta* is four codepoints in one grapheme
* pluti is written as an **inline digit `3`** (`ā́sī3d`, AVŚ 12.5.50)

---

## 5. Two numbering systems, captured as data

The artifact carries the Vishva Bandhu (Hoshiarpur 1960–64) numbering alongside the
Roth/Whitney numbering, quoted from its own preamble:

> NOTE ON REFERENCES IN BOOKS 11-20: The basic numbering of Books 11-20 follows the ed.
> Roth/Whitney. Numbering in [...] follows the ed. by Vishva Bandhu: Atharvaveda (Saunaka),
> with the Pada-Patha and Sayanacarya's commentary, Hoshiarpur 1960-1964.

Three bracket positions occur, each meaning something different, and each is rendered
differently rather than through one guess:

| Locator | Meaning | Emitted alternate `Citation` |
|---|---|---|
| `11,4[6].1a` | the **sūkta** differs | `AVS 11.6.1` |
| `11,3.32[4.1]a` | sūkta **and** mantra differ | `AVS 11.4.1` |
| `15,2.1[2.1]a` … `[2.8]g` | one Roth/Whitney verse = **eight** Vishva Bandhu verses | `AVS 15.2.1-8` |
| `15,5.1[5.1]` … `[5.2-3]` | endpoint is itself a range | `AVS 15.5.1-3` |
| `20,96.22[-]a` | explicit **absence** in the other edition | none — an `ALTERNATE_NUMBERING_ABSENT` assertion instead |

261 units carry an alternate citation (214 in kāṇḍa 11, 47 in kāṇḍa 15). The source's own
trailing `[8]` markers are kept **separately** (`alternate_unit_markers`) as a second,
independent witness to the same numbering rather than merged into the first.

---

## 6. Parser failures and source defects — specific and honest

Nothing below was silently repaired.

### 6.1 Four locator collisions (two verses claiming one number)

| Collision | What the source prints | Verdict | Handling |
|---|---|---|---|
| `AVŚ 9,6.48` ×2 | occ1 marker `‖48‖`; occ2 marker `‖49‖`, and 9.6.49 is otherwise absent | **source typo**: occ2 is verse 49 | occ1 canonical, occ2 preserved whole |
| `AVŚ 12,5.53` ×2 | occ1 is the sūkta's *first* verse but prints `‖1‖`; occ2 prints `‖53‖` | **source typo**: occ1 is verse 1 | occ2 canonical (its marker agrees), occ1 preserved whole |
| `AVŚ 13,4.26` ×2 | occ1 is the sūkta's *first* verse but prints `‖1‖`; occ2 prints `‖26‖` | **source typo**: occ1 is verse 1 | occ2 canonical, occ1 preserved whole |
| `AVŚ 20,96.22` ×2 | `22[-]` and `[-]22`, **both** printing `‖22‖` | **genuine edition divergence** (ADR-010), not a typo | occ1 canonical, occ2 preserved whole |

**Resolution rule** (deterministic, applied identically every run): keep the occurrence whose
own in-text `‖N‖` marker agrees with its locator, if exactly one does; otherwise keep the
first in file order. The loser becomes a `NON_CANONICAL_DUPLICATE_OCCURRENCE` assertion
**carrying its complete Sanskrit text**. No verse number is ever invented; no byte is dropped.

Consequence, accepted rather than hidden: `canonical_key VG:AV:SAU:K20:S096:V022` cannot
represent both verses of the 20.96.22 pair. One of the two is not reachable by canonical key
in this build. That is a real limitation of a 3-integer key against an edition that prints
two verses under one number, and it should be resolved by a human editor, not by the parser.

### 6.2 Thirteen label/marker disagreements — and the kāṇḍa-7 cluster is now SOLVED

The parsed locator and the source's own printed verse marker disagree at thirteen places:

`7.6.3`(‖1‖) `7.6.4`(‖2‖) `7.45.2`(‖1‖) `7.54.2`(‖1‖) `7.55.1`(‖2‖) `7.68.3`(‖1‖)
`7.72.3`(‖1‖) `7.76.5`(‖1‖) `7.76.6`(‖2‖) `9.6.48`occ2(‖49‖) `12.5.53`occ1(‖1‖)
`13.4.26`occ1(‖1‖) `13.4.22`(‖2‖)

**The nine kāṇḍa-7 cases are not typos. They are the Berlin-versus-Bombay hymn division,
and this is now proved from Whitney's own statement.** Whitney/Lanman write (HOS 7, p. 389):

> "It should here be mentioned that the Bombay edition, following the Major Anukramani,
> counts hymns 6, 45, 68, 72, and 76 each as two hymns. From vii. 6. 3 to the end of the
> book, accordingly, Whitney gives a double numeration of the hymns … As against the
> former, the latter involves a plus of one from vii. 6. 3 to vii. 45. 1; a plus of two from
> vii. 45. 2 to vii. 68. 2; a plus of three from vii. 68. 3 to vii. 72. 2; a plus of four
> from vii. 72. 3 to vii. 76. 4; and a plus of five from vii. 76. 5 to the end. Finally it
> may be noted that vii. 54. 2 is reckoned (forwards) to vii. 55…"

Whitney names exactly six renumbering points: **7.6.3, 7.45.2, 7.68.3, 7.72.3, 7.76.5** and
**7.54.2**. The parser, which knew nothing of this passage, flagged a disagreement at
**all six, with zero misses**:

| Whitney's stated split point | flagged by parser? | printed marker |
|---|---|---|
| 7.6.3 | yes | ‖1‖ |
| 7.45.2 | yes | ‖1‖ |
| 7.54.2 | yes | ‖1‖ |
| 7.68.3 | yes | ‖1‖ |
| 7.72.3 | yes | ‖1‖ |
| 7.76.5 | yes | ‖1‖ |

**6/6 matched, 0 Whitney points missed.** The three extra flags — 7.6.4, 7.55.1, 7.76.6 —
are each the *second* verse after a split, carrying ‖2‖ where the restarted count continues.
And all nine fall inside the six hymns Whitney names (6, 45, 54, 55, 68, 72, 76).

**What this means for interpretation, and it is not a small thing.** The in-text `‖N‖`
marker is *not* simply "the source's own verse number". In kāṇḍa 7 it is **a different
edition's** verse number — the Bombay / Major-Anukramaṇī count, restarting at each split
hymn — sitting inside a file whose locators carry the Berlin count. Any tool that treated
the marker as an authority and "corrected" the locators would silently convert kāṇḍa 7 to
Bombay numbering. The adapter promotes neither witness and stores both.

The remaining four cases (9.6.48, 12.5.53, 13.4.26, 13.4.22) are genuine defects, not this
phenomenon: they are single mislabelled verses inside otherwise consistent sūktas (§6.1).
Note `13.4.22` in particular — there the *locator* is right and the *marker* is wrong, the
opposite of `13.4.26`. So neither witness can be promoted to arbiter anywhere, and the
adapter promotes neither: both are stored on every unit and a
`SOURCE_INTERNAL_NUMBERING_DISAGREEMENT` assertion is emitted.

### 6.3 One corrupt pada letter

`(AVŚ_8,5.11ḍ)` — pada letter is `ḍ` (retroflex d) where `c` is clearly meant. Unrecognised
pada letters are ranked "always advances" so this typo stays inside verse 11 instead of
splitting it into two verses. Corrupt letter preserved verbatim in `pada_labels`.

### 6.4 Forty-six units carry no verse marker at all

Reported, not synthesised.

### 6.5 What the parser cannot do

* **Anuvāka boundaries are only partial.** 220 `{N}` markers exist and are captured, but they
  appear in only 11 of 20 kāṇḍas (3, 8–14, 17, 18). Kāṇḍas 1, 2, 4–7, 15, 16, 19, 20 carry
  none, so a complete anuvāka layer **cannot** be built from this artifact. Not attempted.
* **No padapāṭha, no metre, no accent-position analysis** — the artifact contains none.
* **IAST is not exactly derivable.** The transliteration is a TITUS/GRETIL convention
  (`r̥` with ring below, `ḷ` for intervocalic ḍ, inline `3` for pluti), recorded as
  `transliteration_scheme: GRETIL_TITUS_LATIN_AVS`. It is *not* relabelled IAST, and no
  lossy conversion to IAST was performed.

---

## 7. Cross-source comparison (D5)

`compare_readings()` from `src/vedagraph/compare/text.py`, over the 153 sampled mantras,
accented artifact vs unaccented artifact:

| `TextComparisonCategory` | Count | Share |
|---|---:|---:|
| `ACCENT_ONLY` | **153** | 100.0% |
| everything else | 0 | 0% |

**This result is weaker evidence than it looks, and saying so is the point.** A 100%
`ACCENT_ONLY` distribution with a perfect 1:1 locator alignment (both artifacts yield exactly
5,843 units in exactly the same order) shows that the unaccented file is a **mechanical
accent-strip of the accented file**, not an independent witness. Corroborating evidence: the
unaccented file's own preamble reads `WḌ. Whitney` where the accented file reads
`W.D. Whitney` — the accent-removal transform corrupted `.D` into `Ḍ` in the header prose.

So this comparison validates the *comparison machinery* and the *accent-handling* on real AVŚ
bytes. It does **not** provide cross-edition corroboration of the AVŚ text. That still
requires a genuinely independent edition.

`compare.run.run_comparison()` itself could not be used: its `TextComparisonConfig` has a
required `mandala: int` field and `load_readings()` dispatches only on `source_id in {GRETIL,
VEDAWEB}`, so it is Rigveda-shaped. Extending it means editing shared comparison
infrastructure this agent does not own. `compare_readings()` and the `TextComparison` model
were reused unchanged.

---

## 8. QA results (actual)

### Byte-identical rebuild — **CONFIRMED**

Two builds run in two separate OS processes; output directory diffed file by file:

```
diff -r --brief run1 data/canonical/atharvaveda_pilot_v1  ->  no differences
```

Full per-file hash table: `docs/manifests/atharvaveda_pilot_v1_manifest.md`.
Headline figures: `passages.jsonl` 174, `text_versions.jsonl` 459, `citations.jsonl` 157,
`source_assertions.jsonl` 177, `translations.jsonl` 115, `text_comparisons.jsonl` 153,
`sources.jsonl` 2, `source_artifacts.jsonl` 3, `qa_issues.jsonl` 2, `works.jsonl` 1,
`traditional_metadata.jsonl` 0, `audio_recordings.jsonl` 0, `audio_segments.jsonl` 0.
`manifest.json` sha256 `0af8568cc8c5627e0912c652af20b35edf1caa733376ec182a1de13830faa2a6`.

`manifest.json` is byte-stable because `built_at` is pinned to the newest snapshot retrieval
timestamp, not to wall-clock time. Determinism was re-verified after each functional
change made during the build (translations added, unaligned-translation reporting added,
`Source`/`SourceArtifact` records added, lint reformat); it held every time.

### Gate results

| Check | Result |
|---|---|
| unique structural IDs (`canonical_key`, `canonical_urn`, `entity_id`) | **PASS** — 174/174 unique on all three |
| UUID determinism (`uuid5(NS, canonical_urn) == entity_id`) | **PASS** — 174/174, recomputed independently |
| parent reference integrity | **PASS** — every non-null `parent_key` resolves |
| duplicate passage IDs | **PASS** — none |
| Unicode NFC stability + idempotence | **PASS** — 459/459 text records |
| accent preservation | **PASS** — 153/153 `PRIMARY_TEXT` accented; 0 search-derivative records retain accents |
| citation coverage | **PASS** — every mantra carries its canonical citation |
| JSONL schema validity | **PASS** — all files round-trip through their Pydantic models |
| rebuild byte-identical | **PASS** |
| **sequence continuity** | **WARNING (real gap, not filled)** — `VG:AV:SAU:K13:S004` has 55 mantras with highest number 56; **verse 1 is missing** because the source mislabels it 26 (§6.1) |
| no silently missing records | **INFO** — 155 parsed units vs 153 canonical mantras; the 2 surplus retained as explicit divergence assertions |
| source count reconciliation | **NO SOURCE-STATED TOTAL EXISTS** (§3); computed counts exposed machine-readably instead |

### Shared cross-Veda gate

`vedagraph.qa.checks.validate_corpus` **ran without crashing** on AVS records — Agent F's
`hierarchy["mandala"]` KeyError has been fixed in the working tree.

First run returned **760 errors**, all of one real defect that Agent F correctly diagnosed:
`sources.jsonl` was empty, so every one of the 459 `TextVersion` and 301 other provenance
pointers dangled.

The first fix constructed `Source` rows locally for invented ids `GRETIL_AVS` and
`VEDAWEB_AVS`. **That was overruled by the rights authority, correctly.** These files are
further *artifacts* of `GRETIL` and `VEDAWEB`, both already registered — inventing sources
would assert four hosts where there are two, and would break the rights logic, since the whole
purpose of the artifact layer is that rights differ per *file* within one host. This pilot's
own evidence proves the point: VedaWeb's AVŚ **Sanskrit** resource reproduces the TITUS
no-republication clause while its **Whitney** resource returns a null licence — same host,
same Veda, same API, opposite verdicts.

The build now reads both collections from `data/registry` via `load_sources()` and
`load_source_artifacts()`, constructs neither locally, and additionally **cross-checks the
registry's pinned `checksum_sha256` against the bytes actually read** — so a registry edit
that repointed an artifact at different bytes fails the build instead of producing a release
whose provenance is a fiction. Registered ids in use: `GRETIL.AV.SAUNAKA.ACCENTED.HTML`,
`GRETIL.AV.SAUNAKA.UNACCENTED.HTML`, `VEDAWEB.AVS.WHITNEY_LANMAN_1905.PLAINTEXT.L2`.
Raw snapshot directories keep the local namespaces `gretil_avs/` and `vedaweb_avs/`
deliberately, so Atharvaveda snapshots do not mix into the Rigveda's `data/raw/gretil/`; a
raw directory is storage layout, the registry `source_id` is the contract.

### The snapshot-to-rights join, and how it is closed from this side

That split has a real cost, and it is a contract defect rather than a choice.
`ingest/fetcher/http.py` derives **three** things from one argument — the raw directory
(line 159), the `snapshot_id` prefix (line 168) and the `source_id` written into the metadata
sidecar (line 169). So a caller cannot namespace the *directory* without also writing a
non-registry value into the *recorded provenance*. All 25 snapshot sidecars for this build
therefore record `GRETIL_AVS` or `VEDAWEB_AVS`, neither of which resolves against
`data/registry/sources.yaml` — meaning a snapshot-to-rights join over the raw tree silently
finds nothing.

That file is not owned by this agent and has not been patched; the fetcher change (accept a
separate storage namespace) is filed as a contract request. But the *join* is closed from the
release side, today, by emitting the mapping as data rather than leaving it in a code comment:

| assertion | namespace | resolves to | raw directory | snapshots |
|---|---|---|---|---|
| `SNAPSHOT_NAMESPACE_RESOLVES_TO_SOURCE` | `GRETIL_AVS` | `GRETIL` | `data/raw/gretil_avs/` | 2 |
| `SNAPSHOT_NAMESPACE_RESOLVES_TO_SOURCE` | `VEDAWEB_AVS` | `VEDAWEB` | `data/raw/vedaweb_avs/` | 23 |

### Every assertion cites a registered source

An earlier revision attributed 13 assertions to a `VEDAGRAPH` pseudo-source: 11
`PILOT_SAMPLE_RATIONALE` plus two policy statements. Agent F flagged them as the last
ERROR-class issue across all four Veda builds, and it was a real defect — but the fix was not
to register `VEDAGRAPH`. `AuthorityTier` offers only `PRIMARY_TRADITIONAL`,
`SCHOLARLY_EDITION`, `HISTORICAL_TRANSLATION`, `AGGREGATOR` and `COMMUNITY_TRANSCRIPTION`,
none of which describes this project. **That is the model saying a build decision is not a
source assertion**, and forcing a registry row would have repeated the invented-source
mistake in a new place.

Resolved instead by putting each statement where it is true:

* The 11 `PILOT_SAMPLE_RATIONALE` records **duplicated**
  `data/builds/atharvaveda_pilot_v1.yaml` (`suktas[].rationale`, all 11 present), which is
  already hashed into the manifest as `build_config_sha256`. Dropped from the release; the
  information is preserved and provenanced, just no longer in a record type that
  misdescribes it.
* `TRADITIONAL_METADATA_UNAVAILABLE` → **`ARTIFACT_SUPPLIES_NO_TRADITIONAL_METADATA`**,
  attributed to `GRETIL` and the accented artifact. Restated as a verifiable fact about that
  file — it carries no ṛṣi, devatā or chandas field anywhere — while the wider
  "no rights-clear per-mantra source exists" finding points at the registry gap.
* `CROSS_WORK_PARALLEL_POLICY` → **`KANDA_20_TEXT_READ_ONLY_FROM_THIS_ARTIFACT`**, likewise
  attributed to the artifact, and now carrying *computed* evidence: 38 kāṇḍa-20 mantras,
  sūktas [96, 127], `deduplicated_against_rigveda: false`,
  `records_sourced_from_rigveda: 0`.

The policy framing itself still exists, under `policies:` in the build config.

**And a guard so it cannot regress:** the build now raises `ValueError` if any assertion
cites a `source_id` absent from `data/registry/sources.yaml`. Agent F asked the right
question — whether my local gate resolved assertion `source_id`s at all. It did not, which is
exactly why our issue counts differed (1 versus 14). It does now, and as a hard failure
rather than a warning.

`source_assertions` 188 → 177, all citing `GRETIL` (175) or `VEDAWEB` (2).

Each assertion lists the exact `snapshot_id`s it covers and states explicitly that the
namespace is storage layout and **not** a rights claim — rights attach to the artifact ids in
`source_artifacts.jsonl`. The manifest also now records all **25** snapshot ids (previously
only the 2 Sanskrit ones) and all **3** artifact ids.

**After the fix the shared gate returns 1 issue**, and it is one that should stay:
`sequence_gaps` (WARNING) for sūkta gaps under `VG:AV:SAU:K20`, which is legitimate because
the sample takes only sūktas 96 and 127 of 143.

One gap in the shared gate worth flagging: it did **not** report the real *mantra*-level gap
at `K13:S004`. Its `sequence_gaps` check appears to look at hymn-under-section only. The
local gate caught it.

Agent F independently re-ran its own gate suite on this release and reported
G01 unique_structural_ids PASSED, G02 uuid_determinism PASSED (174/174),
G03 parent_ref_integrity PASSED, G04 sequence_continuity PASSED_WITH_GAPS
(21 parents, 6 with gaps, 0 duplicate sequences), G06 unicode_nfc_stability PASSED,
G07 accent_preservation PASSED, G08 jsonl_schema_valid PASSED.

---

## 9. Translations — 115 records, aligned by printed citation

Source: VedaWeb 2.0 resource `696f42266f50da42570ad040`, "Whitney & Lanman (1905)",
`plainText` at level 2 (Stanza), 4,881 stanza contents. Staged by
`scripts/fetch_atharvaveda_translation.py` into
`data/staged/atharvaveda_translation_stage.json`.

**Alignment method.** Every verse is resolved through
`GET /api/locations?textSlug=avs&alias={kāṇḍa}.{sūkta}.{mantra}` — and VedaWeb's aliases
*are* the printed book.hymn.stanza labels (`1.1.1`, `1,1,1`, `01.001.01`). So the join is on
the translation edition's own printed numbers. **Nothing is aligned by sequence position.**
Whitney's numbering is known to diverge from the Śaunaka Saṃhitā numbering, and a `zip()`
over two lists would have produced records that look complete and are wrong — the exact
failure ADR-010 exists to prevent.

| | count |
|---|---:|
| sampled mantras | 153 |
| Whitney translations attached | **115** |
| no translation because the source does not translate kāṇḍa 20 | 38 |
| staged translations with **no canonical passage to attach to** | 1 |

**Rights.** `PUBLIC_DOMAIN`. Underlying work is Harvard Oriental Series 7–8, 1905 —
published before 1931, US public domain, longest-living author Lanman d. 1941; independently
corroborated by English Wikisource's `{{PD/US|1941}}` on the same edition. The VedaWeb
digital layer declares `"license": null` and carries **no** restrictive statement, only a
citation request. Note the contrast: VedaWeb's AVŚ **Sanskrit** resource does reproduce the
TITUS "no parts … republished" clause verbatim — that clause attaches to the Sanskrit text,
and this build does not use that resource.

### The one unaligned translation is a finding, not a rounding error

`AVS 13.4.1` exists in VedaWeb's translation layer but has **no canonical passage in this
build**, because the GRETIL artifact has no 13.4.1 — it mislabels that verse 26 (§6.1). No
`Translation` record was emitted and the verse was **not** re-attached to a neighbouring
mantra; it is recorded as a `TRANSLATION_HAS_NO_CANONICAL_PASSAGE` assertion carrying its
full text.

This is genuine **cross-source corroboration** of the §6.1 defect. VedaWeb documents its own
edit "Transformation and revision of TITUS verse count", and its AVŚ 13.4 has 56 stanzas
numbered 1..56 *including* a verse 1. So two independent lines of evidence agree that the
GRETIL locator is wrong: the artifact's own `‖1‖` marker, and a second editor of the same
lineage who renumbered it. The pilot still does not "fix" it, because fixing it means
choosing an edition, and that is an editorial act.

**And the two records line up on the same verse, which closes the loop.** The non-canonical
occurrence retained from the GRETIL artifact reads:

> `sá eti savitā́ svàr divás pr̥ṣṭhé 'vacā́kaśat ||1||`

and the unaligned Whitney translation of `13.4.1` reads:

> "He goes [as] impeller (Savitar) to the heaven (''svàr''), looking down upon the back of
> the sky."

Same verse, from two artifacts that were parsed independently and joined on nothing. Neither
record was edited to make them agree; they agree because the mislabelled verse really is
13.4.1. Both are preserved verbatim, and the canonical layer still refuses to assert it.

It also means VedaWeb's **5,842** stanza locations are not the same count as this artifact's
**5,839** distinct mantras — a fourth figure alongside TITUS's 5,919 verse markers and the
~5,977 usually cited. See the gaps section of `data/source_registry/atharvaveda_sources.yaml`.

## 9b. Traditional metadata and audio — status

* **Traditional metadata: 0 records**, with an explicit
  `TRADITIONAL_METADATA_UNAVAILABLE` assertion recording the absence and forbidding both
  LLM generation and transfer of Rigvedic Anukramaṇī rules.
* **Audio: 0 records.** Nothing was mirrored. Every AVŚ audio source found is
  `PERMISSION_REQUIRED`. Inventory is in `docs/reports/ATHARVAVEDA_SOURCE_RESEARCH.md`.

---

## 10. Reproducibility

```bash
./.venv/Scripts/python.exe scripts/build_atharvaveda_pilot.py
```

Deterministic given the two pinned snapshots. To reproduce from zero, delete
`data/raw/gretil_avs/` and re-run; `PoliteFetcher` refetches, and the build is identical iff
the upstream bytes are unchanged (verify against the two sha256 values in
`data/builds/atharvaveda_pilot_v1.yaml`). If GRETIL's bytes change, the snapshot hash changes,
the manifest changes, and the divergence is visible instead of silent.

The pilot writes nothing outside `data/canonical/atharvaveda_pilot_v1/` and depends on no
mutable network state at build time.
