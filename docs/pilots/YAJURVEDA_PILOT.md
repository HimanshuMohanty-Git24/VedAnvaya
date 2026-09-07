# Vājasaneyi Saṃhitā pilot — `yajurveda_pilot_v1`

**Work:** `VG:WORK:YV:VSM` (Śukla Yajurveda, Mādhyandina) · **Built:** 2026-09-07
**Output:** `data/canonical/yajurveda_pilot_v1/` · **Config:** `data/builds/yajurveda_pilot_v1.yaml`
**Run:** `python scripts/build_yajurveda_pilot.py`

## What the pilot proves

| Requirement | Result |
|---|---|
| Source acquisition | 44 hashed snapshots in `data/raw/wikisource_sa/2026-09-07/` via `PoliteFetcher` |
| Parsing | Two independent text layers extracted from one artifact |
| Hierarchy | **Adhyāya → Mantra**, two levels, no invented sūkta level |
| IDs | `identity.vsm_adhyaya_identity` / `vsm_mantra_identity` used verbatim |
| Sanskrit preservation | 135 accented records; `text_original` altered by NFC and nothing else |
| Translation alignment | **Not attempted** — no lawful structured translation exists (declared, not skipped) |
| Provenance | Per-adhyāya `revid`, `pageid`, revision timestamp, redirect flag, canonical URL |
| Deterministic rebuild | **Byte-identical, verified by running the build twice and diffing** |

## Counts achieved

**136 mantra passages + 4 adhyāya passages = 140 passages.** Sampled adhyāyas **1, 16, 31, 40**.

| Adhyāya | Mantras | Accented | Unaccented | Character sampled for |
|--:|--:|--:|--:|---|
| 1 | 31 | 30 | 31 | early ritual formulae; accented layer *lacks mantra 22* → gap handling |
| 16 | 66 | 66 | 66 | Śatarudrīya, largest sampled; mantra 37 printed twice → collision handling |
| 31 | 22 | 22 | 22 | Puruṣa/Viṣṇu sūkta — metrical ṛc, not prose yajus |
| 40 | 17 | 17 | 17 | Īśāvāsya Upaniṣad; **every** label carries a Kāṇva cross-reference |

Other records: 271 `text_versions`, 153 `citations` (136 canonical + 17 alternate),
203 `traditional_metadata` (ṛṣi), 135 `text_comparisons`, 4 `source_assertions`,
2 `source_artifacts`, 1 `source`. `translations`, `audio_recordings`, `audio_segments`
are **written empty on purpose**, not omitted.

Sampling deliberately stresses the parser rather than flattering it. Ingesting adhyāya 1
alone would have produced a parser that silently drops adhyāya 40 entirely.

## Parser design decisions worth knowing

**Redirect resolution is mandatory.** Page titles are requested zero-padded in Devanagari
digits (`अध्यायः ०१`), but adhyāyas **2, 3 and 6** live at *unpadded* titles and the padded
form is a redirect. Every request sets `redirects=1` and the adhyāya number is read from the
title the wiki actually served, never from the one requested.

**Mantra numbers always come from a label the source wrote.** The unaccented layer labels
`<adhyāya>.<mantra>`; the accented layer closes each mantra with its number in Devanagari
digits between daṇḍas. Nothing is numbered by file position, so a missing mantra leaves a
gap instead of shifting every later mantra by one.

**Adhyāya 40's labels carry a braced annotation** — `40.1 {ईशावा.उप. काण्व1}`. A bare
`\d+\.\d+` label rule drops all 17 mantras in silence. The annotation is captured as a
non-canonical `Citation` with system `SOURCE_CROSS_REFERENCE`.

**Commentator sigla separate the text from the commentary on it.** The accented mantras sit
inside the Uvaṭa–Mahīdhara commentary, and a commentary *paragraph* also contains tone marks
and also ends with the same numbered daṇḍa marker. Runs opening with `उ०` / `म०` / `मा०` are
therefore excluded. Without this the accented layer collected each mantra two or three times:
the rule removed **460 spurious records** across the 40 adhyāyas (2,295 → 1,960). `मा०` was
found by investigating a residual duplicate at VSM 19.48, not assumed.

**A leading scribal invocation is stripped**, narrowly: a known formula (`हरिः ॐ`), at the
very start, closed by a daṇḍa. Exactly one pilot record (VSM 1.1) is affected.

## Honest parser failures

**4 in the pilot** (3 in adhyāya 1, 1 in adhyāya 40), all one class: *"accented run ended
without a numbered terminal marker"*. These are commentary passages containing tone marks
that never reach a mantra-number marker. They are reported, not repaired, and they do not
corrupt any record — the affected mantra simply has no accented reading.

**Across all 40 adhyāyas: 21 failures** (20 of that class, 1 label-shaped line that did not
match the label rule). Ṛṣi index: **9 of 419 lines unparsed**, and the reasons are specific —
missing commas between ranges (`११.२३, २४, २७-३१ ३६`), an `*` placeholder standing in for
adhyāya 25's data, and two continuation lines that give mantra numbers with **no adhyāya**
(`वसिष्ठः १४, १८, २०, …`). The double-hyphen range form (`२.१--१६`) *was* fixed, safely,
because a dash is only ever a range separator in that index. The ambiguous continuation
lines were **not** guessed at — which is why adhyāya 25 has no ṛṣi coverage.

**Known imperfection, not fixed:** the accented records retain their trailing `।। N ।।`
marker, since it is the source's own text. It is neutralised on derived comparison surfaces.

## Layer divergence is data

The two layers disagree and **neither is complete**; they were never merged. In the pilot,
adhyāya 1 mantra 22 exists only in the unaccented layer. Across the whole work the
unaccented layer is truncated in adhyāyas 3, 7 and 19 and the accented layer is short by one
in 6 and 23; the **union is exactly 1975 with no gaps**. Only the structural inventory is
unioned — no text is blended. See ADR-010.

VSM 16.37 is printed **twice** in the accented layer with a variant reading
(`स्रुत्याय` / `सत्याय`). The first reading is kept and the collision is recorded in the
build report. This is a genuine textual variant, not a parser artifact.

## Traditional metadata — and what is deliberately absent

203 `HAS_RISHI` assertions across the four adhyāyas, from the edition-supplied ṛṣi index.
Each carries the verbatim source line, its line number, and whether the source stated it as
a single mantra or a range — so a range-derived claim can never later be mistaken for a
per-mantra statement. All are `UNREVIEWED`.

**`HAS_DEVATA` and `HAS_CHANDAS` are asserted for nothing, on purpose.** The Śukla YV
*Sarvānukramaṇa-sūtra* states that many yajus **have no metre at all**
(`yajuṣām aniyatākṣaratvād ekeṣāṃ chando na vidyate`), and its devatā co-domain includes
ritual implements (cart, branch, pot, potsherd) as *pratimābhūta*. So neither field may be
carried over from Rigvedic practice, and the apparatus that does state them is continuous
sūtra prose that no machine — and emphatically no LLM — may resolve. Schema changes are
needed first: a nullable `chandas` with a reason code distinguishing *asserted-absent*
(`anādiṣṭa`) from *unknown*, and a YV-specific `devatā` union type.

## QA results — actual, not assumed

```
G10 rebuild byte-identical:              PASS  (built twice, every file diffed)
generated_content_sha256 identical:      PASS
vedagraph.qa.validate_corpus:            returned 0 issues
G01 unique canonical_key/entity_id/citation/urn:  PASS
G02 uuid5(NAMESPACE, canonical_urn) == entity_id: PASS
G03 parent_key resolves within build:    PASS
G03b mantra parent is the Adhyaya SECTION:PASS
G04 sequence_in_parent contiguous 1..N:  PASS
G06 text_nfc NFC-stable:                 PASS
G06b content_sha256 matches text_nfc:    PASS
G07 accented readings retain tone marks: PASS (135 accented records)
G07b text_original preserved (NFC only): PASS (0 altered)
mantras all carry Sanskrit text:         PASS
citations/metadata target a passage:     PASS
```

`validate_corpus` returned **0 issues**. Worth recording *why* that is notable: at the time
this pilot was written that function hard-coded the Rigvedic 3-level hierarchy and would
have raised `KeyError: 'mandala'` on any 2-level work. Agent F landed a work-agnostic fix
(deriving legal parent types from `works.yaml`) before this run, and the VSM build is the
first non-Rigvedic corpus to pass it. The pilot additionally runs its own work-agnostic
checks so it is genuinely verified rather than merely unvalidated.

## Cross-source comparison

135 comparisons via the existing `compare/text.py` and `TextComparisonCategory`, unmodified:
**`UNCLASSIFIED` 116 · `SANDHI_OR_SEGMENTATION` 13 · `ACCENT_ONLY` 6.**

First measured as 132 / 2 / 1. The difference is a real fix, not a re-run: I diagnosed that
`normalize/unicode.py::TRANSCRIPTION_EQUIVALENCES` folded only **Latin** IAST/ISO-15919
variants, so nothing folded the layers' incompatible nasal spellings (**U+A8F3** 77× vs
**U+1CEA+U+0902+U+1CED**, where U+1CEA is category Lo and therefore survives accent
stripping) or the accented layer's **124 ASCII colons standing for visarga** (~1,538 across
the whole work). Agent F, who owns `normalize/`, added Devanagari nasal and visarga folds;
both now fold equal, and `UNCLASSIFIED` fell to 116. **I did not patch `normalize/`.**

The residual 116 are editorial, not encoding: the unaccented layer word-splits with avagraha
where the accented layer reads sandhi-joined, so the two layers are not token-alignable
without a deliberate mapping and the comparator rightly declines. Two source defects recorded
and not silently cleaned: one U+F15C private-use character, one U+00AC not-sign.

## Reproducibility statement

The build is a pure function of (a) the hashed snapshots under
`data/raw/wikisource_sa/2026-09-07/`, and (b) `data/builds/yajurveda_pilot_v1.yaml`.
Nothing is fetched at build time. Every snapshot's sha256 is re-verified against its
recorded metadata on load, and the build aborts if any snapshot has drifted. The manifest
records `build_config_sha256`, `raw_snapshot_hashes`, `parser_versions`,
`comparison_version`, `software_git_commit` and `generated_content_sha256`.
`build_timestamp` is pinned in the config, so `built_at` does not vary between runs — which
is what makes the byte-identical rebuild meaningful rather than accidental.

To reproduce from nothing:

```bash
python scripts/fetch_yajurveda_wikisource.py   # 40 adhyayas + 4 apparatus pages, idempotent
python scripts/build_yajurveda_pilot.py        # build twice, diff, QA
```

Re-fetching will produce *new* snapshots if Wikisource pages have since been edited (the
snapshots carry `revid`, so drift is detectable rather than silent). Rebuilding from the
existing snapshots is byte-stable indefinitely.

## This work has NO PRIMARY_TEXT layer — and that is the finding

Agent E flagged that the accented layer might not deserve `PRIMARY_TEXT`. I tested it
rather than defending the default, and the outcome is more interesting than either
starting position.

**What I proved:** the accented layer is a *structural* mūla layer, not fragments lifted
from prose. The 1929 Nirṇaya Sāgara edition uses the standard mūla–bhāṣya layout:

```
तत्र प्रथमा।                      <- ordinal header: "there, the first"
इ॒षे त्वो॒र्जे त्वा॑ … ।। १।।        <- the full accented mula, closed by its OWN number
उ० … / म० …                       <- Uvata's and Mahidhara's bhasya
द्वितीया ।                        <- the second
```

Measured across adhyāyas 1, 3, 16, 19, 31, 40: **271 ordinal-header lines against 293
accented records**. The VSM 16.37 duplicate is itself headed `सप्तत्रिंशी।`, "the
thirty-seventh". Agent E accepted this and recorded it in the registry.

**Why the role is still `EXTRACTED_FROM_CONTAINER`, and Agent E was right:** the role
describes the layer *as produced*, not the structure the source could support. My
implementation does **not** read the declared ordinal boundary — it infers the mūla start
from accent-presence. And the decisive argument is my own evidence, not E's: the two
`NEEDS_REVIEW` interventions below include a **variant selection** at VSM 16.37, where the
page prints two attested readings and the layer keeps one. A layer that picks between
attested readings is a critical decision, however small. My structural finding was right;
my implementation is weaker than my finding; the role tracks the implementation.

**The consequence, which the build now reports rather than hides:**

| | |
|---|---|
| `WIKISOURCE_SA.YV.VSM.UNACCENTED` | `PARALLEL_TEXT` — faithful transcription, but **incomplete: 1,836 of 1,975 mantras** |
| `WIKISOURCE_SA.YV.VSM.ACCENTED` | `EXTRACTED_FROM_CONTAINER` — complete (1,958) but extraction-derived |

**So no layer of this work is both faithful and complete, and none is registered
`PRIMARY_TEXT`.** `report.primary_text_status` states `has_primary_text_layer: NO` and the
verification script prints it. The config field was renamed `primary_text_version` →
`leading_text_version` precisely so it stops implying a role it never had: "leading"
selects which layer drives comparison and coverage and confers no canonical status.
`TextRole.EXTRACTED_FROM_CONTAINER` says such a layer "must never be selected as
primary_sanskrit", and this build formerly did exactly that.

**Roles are no longer chosen here.** They are read from
`data/registry/text_versions.yaml` via `load_text_versions()`, with an unregistered id
falling back to `COMPARISON_ONLY` — the most restrictive sensible role, never a permissive
one. Choosing a `TextRole` in build code is the same defect as constructing a
`SourceArtifact` locally: `TextRole` is a permission statement, so it belongs to the
provenance authority.

**Upgrade path**, per Agent E and recorded as reviewable rather than final: reimplement the
adapter to read the ordinal headers (a hybrid — accent-presence with header confirmation —
would likely also fix the 17 mantras currently lacking an accented reading) and resolve the
two interventions. `PRIMARY_TEXT` then becomes correct.

## Editorial interventions are recorded, not implicit## Editorial interventions are recorded, not implicit

Two places where this parser departs from the source bytes. Both are now emitted as
`SourceAssertion` records with `status: NEEDS_REVIEW`, because an intervention described
only in a docstring is not reviewable and not reversible:

| Passage | Kind | Removed |
|---|---|---|
| VSM 1.1 | `LEADING_INVOCATION_REMOVED` | `हरिः ॐ ।` — front matter of the printed page |
| VSM 16.37 | `SECOND_READING_DROPPED` | the `सत्याय` reading |

The second is the one that matters: the page prints VSM 16.37 twice, with `स्रुत्याय` and
`सत्याय`. Keeping the first is a **variant-selection judgement, not a mechanical dedup**, and
it is flagged for review rather than presented as a parse result.

## Provenance identifiers come from the registry

A defect worth recording rather than quietly fixing. Earlier revisions of this pilot
constructed their own `Source` and `SourceArtifact` records, under ids
`WIKISOURCE_SA_VSM` / `WIKISOURCE.SA.VSM.*` that exist nowhere in `data/registry/`. Agent F's
G11 registry-checksum gate failed the build on it — the only one of the four Veda pilots to
fail — and it was the third instance of one shared assumption across Agents B, C and D.

It is not cosmetic. A locally-invented artifact id asserts **rights** at a level the rights
authority never adjudicated, and Agent D's evidence shows why that is dangerous: on one host,
VedaWeb, the AVS Sanskrit resource carries TITUS's no-republication clause while the Whitney
resource returns a null licence — same site, opposite verdicts. Rights attach to the artifact,
so an unregistered artifact id is an unadjudicated rights claim.

Fixed by referencing rather than constructing: the builder calls `load_sources()` and
`load_source_artifacts()` and **raises** on an unknown id. Registered ids in use are
`WIKISOURCE_SA` (source), `WIKISOURCE_SA.YV.VSM.SAMHITA.DEVANAGARI` and
`WIKISOURCE_SA.YV.VSM.RISHISUCI`. Text-version ids are `WIKISOURCE_SA.YV.VSM.ACCENTED` and `WIKISOURCE_SA.YV.VSM.UNACCENTED` — renamed from `…SAMHITA` on Agent E's collision-hazard objection, since a text-version id differing from an artifact id by one dotted segment is a footgun of exactly the class that produced the checksum defect. Snapshots were re-fetched under the registered source id
into `data/raw/wikisource_sa/`; all 44 returned **identical sha256s**, confirming the bytes
were never the problem — only the identifiers. G11 is now 0 ERROR / 1 WARNING.

The build also re-verifies each registry checksum against the bytes it read, and **names the
page** the checksum belongs to. That check found a second defect, in the registry rather than
here: the checksum recorded for the saṃhitā artifact is the hash of the **preface page**, a
real snapshot of the wrong thing. My own first version of the check said only "matches a
snapshot" and would have missed it. Reported to Agent E with the correct hashes.

## Deliberate divergence from the shared contract

This config does **not** validate against `schemas/corpus_build_config.schema.json`.
`CorpusBuildConfig` requires `mandala` and `selected_suktas`, which do not exist in a
2-level work; Agent A has ruled it Rigveda-specific and is landing a generic
`WorkBuildConfig`. The field names here (`section_level`, `selected_sections`,
`mantra_level`) already mirror it, so the migration is mechanical. The pilot therefore uses
its own loader in `src/vedagraph/ingest/adapters/yajurveda_pilot.py` rather than
`vedagraph.build`, and emits no `SuktaDiscoveryRecord` (that model cannot represent a work
with no sūkta level).

## Scale-up readiness

The adapter already runs cleanly over all 40 adhyāyas — the build reads every one for the
count reconciliation, so the full-corpus figures in this document are produced by the same
code path an ingestion would use. Full ingestion needs only
`selected_sections: [1..40]`, and would yield **1,975 mantra passages** and roughly **2,106
ṛṣi assertions**. No new parsing work is required.

**But it would yield no canonical Sanskrit reading**, because neither layer is registered
`PRIMARY_TEXT` (see above). That is the governing gap, not an adjacent one: downstream work
needing a canonical text — lexical layer, semantic extraction, alignment — is blocked on
this Veda until it closes. The bounded path is the ordinal-header reimplementation plus
resolution of the two `NEEDS_REVIEW` interventions.

Also not ready, each a named blocker in `docs/reports/YAJURVEDA_SOURCE_RESEARCH.md` rather
than a workaround: the translation layer, the padapāṭha-backed lexical layer,
`devatā`/`chandas`, and audio.
