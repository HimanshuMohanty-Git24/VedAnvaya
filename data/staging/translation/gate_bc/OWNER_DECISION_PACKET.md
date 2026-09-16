# Translation Gate B/C — Owner Decision Packet

**Task:** post-Wave-4 remediation round 2. Structural Gate B and adversarial Gate C over the
entire staged-but-not-imported translation population, to enable two owner decisions.

**No translation was imported.** Every graph interaction in this analysis was a read. The
canonical census, the core corpus invariant and a content digest over all 17,283 live
translation attachments are byte-identical to the values recorded before the work started.

| | |
|---|---|
| Branch | `phase-data-completeness-v2` |
| HEAD at start | `8e07086` |
| Staged rows assessed | **2,254 of 2,254 (100%)** |
| Graph census | 116,838 nodes / 281,257 relationships — **unchanged** |
| Translation attachment digest | `a9c93bf9620f015491de278b6c0d65dae61aa8f393f5f8a1b2ddd3b2f21e163f` — **unchanged** |
| Packet id | see `packet_manifest.json` → `packet.packet_sha256` |

The packet hash lives in `packet_manifest.json` and not in this line, because a document
cannot contain its own hash: writing it here would change it. The manifest carries a sha256
for every file in the packet plus one rolled-up id over the sorted list, so this document is
covered by it like any other file. Re-run `scripts/gate_bc_final_verification.py` to recompute.

---

## The two decisions, in one line each

**Decision A (RV span) — CLOSE the span part.** The hazard it protects against no longer
exists. All 30 verses are covered by a `MANTRA_RANGE`, no staged row targets the span, and
the M13 readback is clean. What remains inside its old boundary is a different question and
should be re-filed.

**Decision C (forced addresses) — APPROVE a safe subset of 36, keep 3 withheld.** The rows'
own claim that the source prints no usable label is wrong for most of them: the pinned
snapshot prints a correct legible label for 18 and uniquely brackets the canonical slot for
19 more.

**But read section H before approving any import.** Of the 1,144 rows that are safe *on
evidence*, only **882 can be represented truthfully by the product as it stands**.

---

## A. Population

Independently enumerated from `rows.jsonl`, not inherited from the manifest. The manifest's
own count agreed: 2,254.

| Veda | Rows | Source |
|---|---|---|
| SV | 1,242 | 1,069 Griffith Samaveda 1893 · 173 reused RV rendering |
| AV | 944 | 923 Griffith Atharvaveda 1895 · 21 reused RV rendering |
| YV | 51 | 51 Griffith White Yajurveda 1899 (local pinned snapshot) |
| RV | 17 | 17 Griffith Rigveda 1896 |

| Alignment asserted | Rows | | Confidence | Rows |
|---|---|---|---|---|
| `EXACT_MANTRA_ALIGNMENT` | 2,186 | | `EXACT` | 1,252 |
| `RANGE_ALIGNMENT` | 68 | | `VERIFIED_SEGMENT` | 262 |
| | | | `PROBABLE` | 740 |

**740 rows are withheld by the campaign's own central predicate** —
`NOT_IMPORTABLE = {PROBABLE, UNVERIFIED}`, imported from
`scripts/validate_staging_artifact.py` rather than re-declared here so the packet cannot
soften it.

### Owner gate, as staged versus as measured

Every one of the four translation gaps is currently gated on
`OWNER_DECISION_A_RV_SPAN + OWNER_DECISION_C_FORCED_ADDRESSES`. That is a mis-gating, and it
is the single most consequential structural finding in this packet: **every forced address in
the artifact is Yajurvedic (51 rows) and the RV span question concerns 30 Rigvedic verses.**
Between them those two decisions are blocking 1,242 Samavedic and 944 Atharvavedic rows on
questions that do not touch either corpus.

---

## B. Gate B — structural validity

Run over 100% of rows. **38 named checks, every one at full coverage** — no check silently
skipped a row shape it did not recognise.

| Verdict | Rows | Population |
|---|---|---|
| **B_PASS** | **1,187** | AV 923 · reuse 194 · SV 49 · RV 13 · YV 8 |
| `B_FAIL_POLICY` | 740 | SV 735 · RV 4 · YV 1 |
| `B_FAIL_SOURCE_COORDINATE` | 285 | SV Uttarārcika |
| `B_NEEDS_INDEPENDENT_CONTENT_CONTROL` | 31 | YV forced addresses |
| `B_FAIL_PROVENANCE` | 11 | YV adhyāya 12 |

**B1 target identity: 2,254 of 2,254 resolve**, all `:Mantra`, correct Veda, correct
recension, correct `work_id`, `CANONICAL`, no `:Internal` proxy. All 1,178 cited Rigvedic
reference keys resolve too.

**B2 — the real coordinate defect (285 rows).** The Samavedic Uttarārcika locators omit the
*dasati* level. `"Part 2 Book 1 Chapter 1 verse 2"` addresses **22 different canonical keys**.
The verse number in the locator tracks the canonical key rather than the source, so the
locator is a lossy rendering of the target and cannot corroborate it. The only source-side
anchor left is `griffith_unit_index`, a running ordinal that no third party can re-find.

**B6 — provenance is wildly uneven between sources.**

| Source | Rows | Distinct URLs | Byte hash | In page proofs |
|---|---|---|---|---|
| Griffith AV 1895 | 923 | 146 | **923/923** | **923/923** |
| Griffith RV 1896 | 17 | 8 | 17/17 | 17/17 |
| Griffith WYV 1899 | 51 | 16 | 39/51 | n/a (local snapshot on disk) |
| **Griffith SV 1893** | **1,069** | **1** | **0/1,069** | **0** |
| Reused RV rendering | 194 | — | — | verifiable against the live graph |

`proofs/source_pages.json` records 163 pages: 147 Atharvavedic, 16 Rigvedic, **zero
Samavedic**. All 1,069 Samavedic rows cite one index URL (`.../hin/sv.htm`) with no content
hash. There is no artifact on disk and no proof in the packet showing those 1,069 English
strings were read from Griffith's Samaveda.

### Systemic defect found — and why it cannot be fixed the prescribed way

The manifest declares `code_commit: 381ba0e`. **At that commit no file in the repository
emits `griffith_unit_index`, `english_control_similarity`, `sanskrit_similarity`, or the
`translation-completion-v1` algorithm.** The generator that produced all 2,254 rows was never
committed.

The campaign's remedy for a systemic generator defect is: fix the generator, add BAD→FAIL
tests, regenerate the entire affected population, rerun both gates. **Steps 1 and 3 are not
executable.** No population in this artifact can be regenerated, and no code fix can clear
one. Every claim therefore had to be verified against independent evidence — the live graph,
the archived page proofs, and the on-disk Yajurvedic snapshot — rather than by inspecting the
adapter. Where that independent evidence does not exist, as for the Samavedic text, the claim
is simply unverifiable.

### The load-bearing claim, recomputed rather than trusted

528 rows rest entirely on `sanskrit_similarity = 1.0` — "this verse's Sanskrit is
surface-identical to that Rigveda verse's". Recomputed from the graph's own stored text
versions:

**526 of 528 reproduce as character-identical. Exactly 2 are false.** Both are Samavedic
readings that omit the particle `ām̐` the Rigveda has (`kalaśeṣvā antaḥ` vs `kalaśeṣv āṃ
antaḥ`), so the reuse of that Rigvedic rendering is not justified by textual identity.

This measurement crosses a script boundary — the Kauthuma Saṁhitā is unaccented Devanagari,
the Rigveda is accent-marked IAST — so the packet states exactly what was folded: Devanagari
transliterated to IAST; udātta (U+030D, and the acute where it sits on a vowel), anudātta
(U+0331), grave, and the svarita digits removed; four spellings of one nasal unified (ṁ, ṃ,
m̐, combining tilde); two romanisations of vocalic r/l unified. **Vowel length, retroflexion,
aspiration, visarga and the palatal sibilant are all preserved**, and there are controlled
fixtures proving ś≠s, ṣ≠s, ṭ≠t, ḍ≠d, ṇ≠n, ā≠a, ṛ≠r and agni≠agne do not merge.

Getting that fold right took six corrections and two of the attempts were wrong in opposite
directions. Both are recorded in the test file, because each would have corrupted the
headline number: stripping every acute merged `viśva` into `visva` and would have
manufactured identity; protecting it scored two character-identical verses at 0.0 and would
have failed every true row.

---

## C. Gate C — adversarial falsification

Run over the 1,187 Gate B passes, with every deterministic check also run over the withheld
populations.

| Verdict | Rows |
|---|---|
| **C_PASS** | **922** |
| `C_WITHHOLD_REUSED_RENDERING_POLICY` | 194 |
| `C_FAIL_ARCHIVE_EVIDENCE` | 49 |
| `C_WITHHOLD_AMBIGUOUS` | 22 |
| `C_FAIL_DUPLICATE_GENERATION` | 0 |

**C1 off-by-one, two axes.** The target axis is only evaluable where a canonical neighbour
already carries English, which is 49 of 2,254 — the staged rows sit precisely in the regions
that have no translations. **A zero from a 2%-coverage check is a coverage statement, not
evidence**, so a second axis was run along the cited Rigvedic control: **1,069 of 1,069
evaluated, and in every case the claimed control outscores both its neighbours.** No
off-by-one found, and that zero means something. 1,036 of 1,069 declared control scores
reproduce within 0.05; the 33 that do not are tokenisation differences of ≤0.20 in which the
claimed control still beats every rival by a wide margin.

**C2 M13 pattern search — found in the Samaveda.** The Samavedic addressing carries the same
class of defect as RV 1.65–1.70: a source-local running ordinal standing in for a canonical
coordinate, with a printed locator that cannot re-find the unit. 1,069 rows carry the index,
800 have an ambiguous locator, 548 have an independent per-row control. Classified systemic;
not patchable per-row; not regenerable. The Atharvavedic, Rigvedic and Yajurvedic
populations are clean of the pattern.

**C4 Samaveda — quantified.** Griffith's Samaveda is the **Rāṇāyanīya** recension; this
corpus is **Kauthuma**. The staging agent's own residual proof states this and refuses a
positional join, measuring the drift from offset 0 to −81. Of 1,242 Samavedic rows:

| | Rows | Disposition |
|---|---|---|
| Direct Samaveda translation of *this* recension | **0** | none exists; nine avenues searched |
| Griffith Samaveda, tier 3 | 735 | `PROBABLE`, withheld by central policy |
| Griffith Samaveda, tier 2 | 334 | 285 ambiguous locator, 49 no archive proof |
| **Reused Rigvedic rendering** | **173** | identity verified, reuse disclosed |
| Unresolved | 602 | in `rejected.jsonl`, not staged |

**Not one of the 1,242 is an independent Samavedic translation.** Even on the most permissive
reading, an approved import gives the Samaveda 173 of 1,844 — all of it another corpus's
English.

**C5 Atharvaveda / Wayback — the strongest evidence in the artifact.** Wave 4 found registry
text claiming "closed via the Wayback Machine, 944 of 961" against a graph holding none. The
underlying acquisition is nevertheless sound: 923 of 923 rows name a page content hash, every
one is present in `proofs/source_pages.json`, and all 147 captured pages returned HTTP 200 on
immutable timestamped URLs. 873 of 923 pass Gate C. The 49 `C_FAIL_ARCHIVE_EVIDENCE` rows are
Samavedic, not Atharvavedic.

**C6 duplication — 0 defects, after two wrong tests of my own.** My first test flagged "same
literal, different parent" and reported 230; my second asked whether the two targets' Sanskrit
matched and reported 43. Both were measuring the corpus behaving as the corpus does — the
Vedas repeat whole verses, and Griffith printed a *separate* rendering for each occurrence in
each volume. The sound test is whether **one printed source unit** was emitted onto several
targets. On that test: 68 rows share a unit, and all 68 are the declared `MANTRA_RANGE` rows.
**No unexplained duplication, and no canonical key is claimed twice.**

**C7 cross-corpus contamination.** 194 rows take Griffith's Rigvedic English and attach it to
a Samavedic or Atharvavedic verse. Every one is **truthfully disclosed** in its own
`mapping_method` ("Cross-corpus reuse, not a Samaveda translation") and every one has its
`work_edition` correctly set to the Rigveda volume. 192 have verified textual identity; 2 do
not and are refused.

One inconsistency to note without overstating it: in 432 of those pairs the graph's own
parallel layer asserts `VARIANT_OF` or `REUSES_TEXT_FROM` while the row claims textual
identity. My recomputation sides with the row — the stored texts really are
character-identical — so this is a defect in the parallel layer's relation typing, not a
translation blocker. It is worth a separate look.

### Two defects Gate B passed and only the adversarial pass caught

1. **`VG:YV:VSM:A21:V045`** stages `"Let the Hotar worship Indra, etc., as in 44 mutatis
   mutandis."` as the verse's English. That is Griffith's editorial cross-reference, not a
   translation. It is prose, long enough, and free of markup, so every structural check
   passed it. **Importing it would assert a pointer as the verse's meaning.**

2. **22 rows declare `language: "en"` and carry Latin.** Griffith renders sexually explicit
   passages into Latin by Victorian convention — the Kuntāpa hymns of AV 20.126 and 20.136,
   and RV 1.179 and 10.61. The text is genuinely his and public domain, but it is not English,
   and the declaration is false.

---

## D. Owner Decision A — RV span

### Recommendation: **CLOSE** the span; re-file the residual

**1. What did it originally protect?** The 50 untranslated Sakala mantras, and specifically
the risk recorded in GAP-TRANSLATION-004: "Griffith renders each pair of our Sakala verses as
one merged unit, so unit k covers verses 2k−1 and 2k. The import bound unit k to verse k."

**2. What is now mechanically resolved?** All of it.

- 30 Rigvedic verses in RV 1.65–1.70 carry no translation edge of their own.
- **30 of 30 are covered by a `MANTRA_RANGE` attached to their paired odd verse.**
- 0 are genuinely missing a translation.
- **0 staged rows target the span at all.**
- The span holds 30 `MANTRA_RANGE` translations plus 1 `MANTRA` — hymn 70's unpaired 11th
  verse, correctly typed 1:1 because Griffith printed it alone.
- M13's readback is clean: 31 rows, 25 moved, 6 already correct, 0 unresolved, 0 findings.

**These are canonical verses covered by a multi-verse translation span, not missing
translations.** That distinction is the entire substance of Decision A, and it now falls on
the resolved side.

**3 & 4. What remains, and why.** 20 verses outside the span, none involving the paired spine:

| Reason absent | Count | Detail |
|---|---|---|
| Another staged source exists but is withheld | 17 | 8 safe · 5 Griffith's Latin · 4 `PROBABLE` |
| No source unit exists at all | **3** | RV 8.93.29, 10.86.16, 10.86.17 |
| One unit spans several verses | 0 | (all inside the span, already resolved) |

**5. Disposition: `CLOSED_DERIVED` on the span, `REPLACED_BY_SCOPE_DECISION` for the
residual.** Nothing about the paired spine remains for an owner to approve or refuse. Keeping
one gate over both would force the owner to re-decide a resolved coordinate question in order
to reach an unrelated editorial one — whether to publish Griffith's Latin — and a scope
statement about three verses for which no source has been found.

The status is **proposed, not written.** Retiring Decision A also unblocks three other gaps
that cite it, and that is a scope change the owner should see before it happens.

---

## E. Owner Decision C — forced addresses

### Recommendation: **MIXED** — approve 36, keep 3 withheld

**First, a defect in the withholding mechanism.** All 31 rows flagged
`address_forced_without_content_control: true` are staged `mapping_confidence: EXACT`, and the
central `NOT_IMPORTABLE` set is `{PROBABLE, UNVERIFIED}`. **The central policy does not
withhold a single one of them.** The predicate keys on confidence; forcing is orthogonal to
it. Only the owner gate — a human convention — stands between these rows and an import. Gate B
now carries `B_NEEDS_INDEPENDENT_CONTENT_CONTROL` as a separate category so the withholding is
mechanical, and there is a regression test pinning the gap.

**The independent verification.** The Griffith White Yajurveda snapshot is on disk: 45 pages,
each named by the sha256 of its own bytes, and 39 of the 51 rows name the hash of the page they
were read from. Each row's literal was located in those bytes by content and the printed label
around it read directly — which tests the rows' own claim about the source.

**The claim is wrong for most of them.**

| Source-local determination | Rows | Is it independent content control? |
|---|---|---|
| Source prints the correct label, legibly | **18** | Yes — the address was *read*, not forced |
| Printed neighbours bracket the slot uniquely | **19** | Yes — source-local context, not position |
| Order and count only | 1 | No |
| Literal not locatable in the snapshot | 1 | No |

The bracketing case, verified in raw source bytes. Griffith's adhyāya 6 prints:

```
23 These waters teem with sacred food…      ← VS 6.23, correct
24 I set you down in Agni's seat…           ← VS 6.24
23 Thee for the heart, thee for the mind…   ← VS 6.25, MISPRINTED as 23
26 Descend, O Waters…                       ← VS 6.26
```

The unit's own label is a genuine duplicate misprint, but it sits between printed 24 and
printed 26, and there is exactly one canonical slot there. That is the source identifying its
own target — not sequence position, not the address having been forced by code, not
translation similarity, and not coverage becoming nicer.

**Row-level result** (full table in `forced_address_decision_table.json`):

| Recommendation | Rows | Of the 31 flagged | Of the 8 pre-controlled |
|---|---|---|---|
| `SAFE_TO_IMPORT` | **36** | 28 | 8 |
| `KEEP_WITHHELD` | **2** | 2 | 0 |
| `SOURCE_ERROR` | **1** | 1 | 0 |

- **`VG:YV:VSM:A20:V085`** — `KEEP_WITHHELD`. The printed label is the mis-set glyph `S5`,
  which could be 55 or 85; the neighbours do not bracket it uniquely.
- **`VG:YV:VSM:A36:V024`** — `KEEP_WITHHELD`. The literal could not be located in the pinned
  bytes by the parse. Manual inspection finds it printed as `21` immediately after printed
  `23`, so it is probably recoverable, but it is not machine-verified and stays out.
- **`VG:YV:VSM:A21:V045`** — `SOURCE_ERROR`. The address *is* uniquely bracketed, but the
  literal is the editorial cross-reference. Right address, wrong content.

The 8 pre-controlled rows carry **two** independent controls each: the printed source label or
bracket, *and* a Rigvedic English parallel control at 0.92–1.00. They are the strongest rows
in the artifact.

**One caveat the owner should weigh.** The control established here is *addressing* control:
the source's own coordinate for the unit. No one has verified that Griffith's English at that
label faithfully renders the Sanskrit. That is true of all 17,283 translations already in the
graph — every one is `MACHINE_ALIGNED` — so it is not a new exposure, but it is not semantic
verification either.

**Decision C's population is therefore 3, not 31.** The remaining judgement is whether a
printed-neighbour bracket counts as independent content control. I recommend it does; it is
the owner's call, which is why this is not written as decided.

---

## F. Importable translation matrix

| Final class | Rows | Veda | Alignment | Independent semantic evidence? |
|---|---|---|---|---|
| `SAFE_IMPORT_SOURCE_EXPLICIT` | **846** | AV 838 · RV 8 | MANTRA | **Yes** |
| `WITHHOLD_PROVENANCE` | 800 | SV 784 · YV 12 · RV 4 | — | no |
| `WITHHOLD_AMBIGUOUS_ALIGNMENT` | 307 | SV 285 · AV 17 · RV 5 | — | no |
| `SAFE_IMPORT_REUSED_RENDERING_WITH_DISCLOSURE` | **194** | SV 173 · AV 21 | MANTRA | **No** — one witness, not two |
| `SAFE_IMPORT_MULTI_VERSE_RANGE` | **68** | AV 68 | MANTRA_RANGE | **Yes**, for its span |
| `SAFE_IMPORT_DETERMINISTIC_VERIFIED_ALIGNMENT` | **36** | YV 36 | MANTRA | **Yes** |
| `WITHHOLD_FORCED_ADDRESS_UNVERIFIED` | 2 | YV 2 | — | no |
| `REJECT_NON_TRANSLATION_LITERAL` | 1 | YV 1 | — | no |
| `REJECT_WRONG_TARGET` | 0 | — | — | — |
| `WITHHOLD_CROSS_CORPUS_POLICY` | 0 | — | — | — |
| `CONFLICT_EXISTING_CANONICAL_TRANSLATION` | 0 | — | — | — |

**Safe on evidence: 1,144. Withheld or rejected: 1,110.** Total 2,254.

The 194 reused renderings must never be counted as independent semantic evidence for the
Samaveda or Atharvaveda: they are Griffith reading the *Rigveda*. Treating them as
corroboration would double-count one witness — which is what owner principle 9 forbids.

---

## G. Import dry run — **PLAN ONLY, NOT EXECUTED**

If the owner approves every evidence-safe class:

| | |
|---|---|
| `:Translation` nodes created | 1,144 |
| `HAS_TRANSLATION` edges created | 1,144 |
| Distinct target passages | 1,144 (exactly 1 row per target) |
| Translations updated | **0** |
| Conflicts | **0** |
| `:Mantra` nodes created or deleted | **0** — the core corpus cannot move |
| Predicted census | 117,982 nodes / 282,401 relationships |

Per Veda: AV 927 · SV 173 · YV 36 · RV 8. By alignment level: 1,076 `MANTRA`, 68
`MANTRA_RANGE`.

### Predicted coverage — four figures that must not be summed

| Veda | Today | Dedicated own-corpus | Multi-verse range | Reused cross-corpus | Still no edge |
|---|---|---|---|---|---|
| RV | 10,502 / 10,552 | 10,322 | 30 | 0 | 42 *(30 of them range-covered)* |
| SV | **0 / 1,844** | **0** | 0 | **173** | 1,671 |
| YV | 1,903 / 1,975 | 1,939 | 0 | 0 | 36 |
| AV | 4,878 / 5,839 | 5,716 | 68 | 21 | 34 |

A verse with Griffith's rendering of its own corpus, a verse sharing one rendering with its
neighbour, and a verse showing another corpus's English are three different claims. Collapsing
them into one percentage has already been graded MISLEADING in this project. **The Samaveda's
"173" is entirely Rigvedic English.**

---

## H. Product readiness — read this before approving

| Distinction | Graph | API | Frontend | Verdict |
|---|---|---|---|---|
| `MANTRA` | yes | yes | yes | **REPRESENTABLE** |
| `MANTRA_RANGE` | yes | yes | **no** | **blocked** — data-only |
| Reused cross-corpus rendering | **no** | **no** | **no** | **NOT REPRESENTABLE** |
| Latin substitution | yes | yes | **no** | **blocked** — field is wrong first |

`AlignmentLevel.MANTRA_RANGE` exists, `TranslationView` exposes `alignment_level`, and the
service projects it — so the distinction is fully expressible over the API today. **But the
passage reader never reads it**, so a rendering covering two verses displays exactly like a
dedicated one, and `TranslationCoverage` cannot separate the two.

A reused rendering has **no representation at all**. Nothing on `:Translation` names the verse
whose rendering it is. An imported Samavedic row would show Griffith's Rigvedic English under
the heading "Translation", with `work_edition: "The Hymns of the Rigveda"` as the only clue,
and Ask would cite it as evidence about the Samaveda.

**Therefore, of the 1,144 evidence-safe rows:**

- **882 are approvable and representable now** — 846 source-explicit + 36 Yajurvedic verified
- **262 are `BLOCKED_PRODUCT_SEMANTICS`** — 194 reused renderings + 68 multi-verse ranges

### A live product defect this review found, not caused by this task

The reader's empty state says *"No released translation covers this passage in the current
build. The verse is held; its translation layer is not."*

**That is already false for 30 verses.** The even verses of RV 1.65–1.70 *are* covered, by the
`MANTRA_RANGE` on their paired odd sibling. M13 typed the data correctly and the product does
not yet read the type. The same is true of `GAP-TRANSLATION-004`'s `closure_measure`, which
counts edges and so can never reach zero while Griffith's merged units are represented
honestly.

Fixing the reader and the coverage model before importing the 68 Atharvavedic ranges would
stop a 30-verse defect becoming a 98-verse one.

---

## I. Registry consequences

**0 closures proposed. 0 statuses mutated.** A gap is not closed by the existence of staging.

| Item | Current | Proposed | Why it cannot close |
|---|---|---|---|
| GAP-TRANSLATION-001 (SV) | `BLOCKED_OWNER_DECISION_REQUIRED` | `STILL_IMPLEMENTATION_FIXABLE` | reaches 173/1,844, all of it Rigvedic English; its own test requires a Kauthuma-aligned `source_id` for every SV translation, false for all 173 |
| GAP-TRANSLATION-002 (AV) | `BLOCKED_OWNER_DECISION_REQUIRED` | `STILL_IMPLEMENTATION_FIXABLE` | reaches 5,805/5,839; test requires zero remaining |
| GAP-TRANSLATION-003 (YV) | `BLOCKED_OWNER_DECISION_REQUIRED` | `STILL_IMPLEMENTATION_FIXABLE` | reaches 1,939/1,975; test requires zero |
| GAP-TRANSLATION-004 (RV) | `BLOCKED_OWNER_DECISION_REQUIRED` | `STILL_IMPLEMENTATION_FIXABLE` | coordinate defect **is** repaired, but the measure counts edges and would still return 42 |
| OWNER_DECISION_A_RV_SPAN | OPEN | **`CLOSED_DERIVED`** on the span | mechanically determined; no owner judgement needed |
| OWNER_DECISION_C_FORCED_ADDRESSES | OPEN | **NARROWED, 31 → 3** | needs owner judgement on one question |

**GAP-TRANSLATION-004's `closure_measure` should change.** It counts `DISTINCT m` with a
`HAS_TRANSLATION` edge. A verse covered by a sibling's `MANTRA_RANGE` is a covered verse with
no edge, so the measure understates coverage by exactly the 30 verses M13 fixed. This is the
registry's version of the reader's empty-state defect.

### Two decisions that should be split out

Both are currently buried inside A and C, neither of which is about them:

- **`OWNER_DECISION_D_REUSED_RENDERING_POLICY`** — 194 rows (SV 173, AV 21). May Griffith's
  Rigvedic rendering be published as the English for a verse whose Sanskrit is verified
  character-identical, disclosed as reuse and never counted as independent evidence? This is
  the largest question in the artifact and it is genuinely editorial.
- **`OWNER_DECISION_F_LATIN_SUBSTITUTION`** — 22 rows (AV 17, RV 5). Publish Griffith's Latin
  with `language` corrected to `la` and a disclosure, leave the verses uncovered, or
  commission an English rendering?

And A and C should stop gating the corpora they do not concern: A gates four gaps and
concerns 30 Rigvedic verses; C gates three gaps and concerns 39 Yajurvedic rows.

---

## J. Verification

| Check | Result |
|---|---|
| Gate tests BAD→FAIL / GOOD→PASS | **72 passed** (`tests/unit/test_translation_gate_bc.py`) |
| Mutation-proofed | 3 mutations of the fold each produced targeted failures |
| Gate B check coverage | 38 checks, **all at 100%**, none vacuous |
| Gate C check coverage | reported per check; the 2%-coverage axis is labelled as such |
| Canonical census | 116,838 / 281,257 — **unchanged** |
| Core corpus | RV 10,552 · SV 1,844 · YV 1,975 · AV 5,839 — **unchanged**, matches invariant |
| Translation attachment digest | `a9c93bf9…e163f` — **unchanged** |
| Live coverage | RV 10,502 · SV 0 · YV 1,903 · AV 4,878 — **unchanged** |
| `tests/unit` | 1,277 passed / 41 skipped *(1,205 + 72 new)* |
| `tests/api` | 1,400 passed |
| Pre-existing formula failure | `assert 1064 == 1103` — **identical**, 37 others pass |
| Git tree | clean of everything but this packet |

The formula failure is `GAP-FORMULA-003` and was deliberately not touched. No scope leak is
possible: this task read the graph and wrote only files under
`data/staging/translation/gate_bc/`, `scripts/gate_bc_*` and one new test file.

### Controlled fixtures

Every required adversarial scenario has a BAD case that fails and a GOOD case that passes:
the M13 positional mapping bug, a forced address without content control, hymn-level text
posing as mantra-level, a `MANTRA_RANGE` missing one covered key, cross-Veda reuse presented
as independent, an archive citation with no content hash, one source unit emitted twice, a
target from the wrong Veda, a `PROBABLE` row bypassing policy, a side file bypassing policy,
and a printed page number leaking in as a verse label. Six fold cases pin the notation
inventory, and four of the fixtures exist because an earlier version of *my own* analysis was
wrong in exactly that way.

---

## Recommended sequence

1. **Close** Decision A on the span. Re-file the residual as scope, not a gate.
2. **Approve** the 36 Yajurvedic forced addresses; hold 3.
3. **Import the 882 representable rows** — 846 Atharvavedic/Rigvedic source-explicit plus the
   36 Yajurvedic. Read back and compare against this packet's digest.
4. **Fix the reader and `TranslationCoverage`** to honour `alignment_level`, and correct
   `GAP-TRANSLATION-004`'s `closure_measure`. This closes a live 30-verse defect.
5. *Then* decide D (reused renderings, 194) and F (Latin, 22), and import only after the
   disclosure surface exists.
6. Leave the Samavedic 1,069 withheld. The route out is Benfey 1848, which carries Griffith's
   own base Sanskrit and would make the 735 `PROBABLE` rows decidable.
7. Commit the generator, or record that this artifact is unreproducible by design.

**OWNER_DECISION_PACKET_READY**
