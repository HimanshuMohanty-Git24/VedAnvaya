# Sāmaveda referent integrity repair

| Field | Value |
|---|---|
| **Run** | `SAMAVEDA_REFERENT_INTEGRITY_REPAIR` |
| **Date** | 2026-09-07 |
| **Starting commit** | `5896856` (branch `semantic-pilot-v1`) |
| **Work** | `VG:WORK:SV:KAU` — Sāmaveda, Kauthuma recension, arcika (verse) text only |
| **Verdict** | `SAMAVEDA_REFERENT_INTEGRITY_REPAIRED_WITH_BOUNDED_REVIEW` |
| **Identity** | `identity_status: FINAL`; `coverage_status: INCOMPLETE_BOUNDED` |
| **Machine-readable** | `data/derived/samaveda_referent_audit.jsonl`, `data/derived/samaveda_referent_bindings.jsonl`, `data/derived/samaveda_cross_witness_structure.json`, `data/source_registry/samaveda_referent_migrations.jsonl`, `tests/fixtures/identity/sv_referent_baseline.jsonl` |

---

## 0. The result in one paragraph

The previous run recorded seven welded addresses, nine surplus markers and a phantom
thirteenth verse, and correctly refused to freeze. **Every one of those figures was
forensics on the wrong corpus.** They were measured on the GRETIL artifact, which is
`PERMISSION_REQUIRED`, was adjudicated unusable, and was never going to be the canonical
source — while only **29 verses, 1.55%**, of the *selected* witness were pinned, and all
three pinned pages sat in the one region of the corpus with zero defects. This run fetched
the remaining arcika corpus (**106 pages**), rebuilt segmentation from source evidence,
replaced the identity scheme, and added the invariant whose absence made the whole defect
class invisible. Result: **1,844 canonical keys, zero addresses absorbing more than one
printed verse, zero source occurrences claimed by two keys**, and a build that now *fails*
when a key changes what it denotes. What remains is a **coverage** gap of 31 verses with a
named cause per verse, not a referent ambiguity.

**The adversarial pass found a real weld in the first repaired build and it is recorded
here rather than quietly fixed**, because the lesson is the same one the run began with.
Running number 713 *is* printed in the selected witness — as `…चर्षणीनां ७१३ ॥`, a
verse-terminal marker with **no opening separator at all** — and the first repaired lifter
read that line as an ordinary pāda and welded verse 713 onto verse 714. The claim "the
selected witness does not print 713" had already been written into four files. **An
"absent from the source" figure is a claim about the parser until every dialect the source
uses has been enumerated.** See §3 family 6 and §11.

---

## 1. Why the old audit could not have found the real defect

The audit surface was wrong in three separate ways, and each one mattered.

| Problem | Consequence |
|---|---|
| The defect set was measured on the **rejected** witness | Seven welded addresses and the phantom V13 are properties of GRETIL's label field, not of the Kauthuma tradition. Repairing them was never going to produce a canonical corpus |
| Only **1.55%** of the selected witness was pinned | And it was the *defect-free* 1.55%. The count ledger says so itself: `overlap_with_the_16_defect_running_numbers: 0`, `verdict: CROSS_CHECK_NOT_AVAILABLE_FOR_THE_GAP_REGION` |
| The selected witness's adapter was **more** broken than the rejected one's | See §2. It was never exercised at scale, so its defect was latent rather than measured |

**MEASURED, and it is the honest indictment of the old parser:** run against the full
106-page corpus, the superseded double-daṇḍa-only marker regex lifts **1,195 of 1,875**
verse markers — 63.7% — and reports nothing wrong. Twenty-two whole pages yield **zero**
verses. `unparsed_remainder` is returned as a list that nothing in `qa/checks.py` reads.

---

## 2. The primary defect was not any of the recorded ones

`SamavedaWikisourceAdapter.parse_at_address` took the five-level address **from the
caller** and wrote the samhita **running number** (1..1875) straight into the
identity-bearing verse slot:

```python
hierarchy={"arcika": arcika, ..., "verse": verse.verse}   # verse.verse is 1..1875
```

`sv_mantra_identity` applied only `_positive(arcika, verse)` — no upper bound, no per-unit
cardinality bound — so page `1.1.1.5`, which prints running numbers 45–54, minted
`…:D05:V45` … `…:D05:V54` for ten verses that **do not exist**. Not collisions: *phantoms*.
Nothing collided, so no uniqueness gate could fire.

Two properties made this maximally dangerous:

1. **In daśati 1 the running number equals the local index.** Measured: unit
   `(1,1,1,1)` is running 1–10. The bug is invisible in exactly the unit a first test
   would choose.
2. **No converter existed anywhere in the repository.** The docstring instructed callers
   to convert; the only caller did not run at all (`TypeError: parse() got an unexpected
   keyword argument 'arcika'`).

**The repair is not a bounds check.** `parse_at_address` is removed. The address is now
*derived*, so a caller cannot supply a wrong one.

---

## 3. Seven source-syntax families the old parser could not read

Every one is handled by **syntax class**, never by verse id. This matters: the count
ledger's own closing note warns that a check comparing a minted count against a lifted
count "measures the adapter against itself and inherits every lifting defect as a phantom
report."

| # | Family | Example as the source spells it | Effect of not handling it |
|---|---|---|---|
| 1 | Two ASCII pipes as verse terminator | `… शंसिषं \|\| ३५ \|\|` | 30 markers lost; whole HTML-table pages read as empty |
| 2 | Two single daṇḍas (U+0964 ×2) | `… वीरयाशवः ।। १०३४ ।।` | **621 markers lost** — the single largest loss |
| 3 | Unterminated marker, opening separator only | `… बृहस्पतिम्॥ ९१` | 6 markers lost; page `1.1.1.10` yielded zero verses |
| 4 | Mixed single-open / double-close | `… रेभो वनुष्यते मति । ११३३ ॥` | 2 markers lost, at running numbers **1133 and 1592** |
| 5 | HTML-table dialect with a **declared local index and pada label** in a second cell | `… \|\| ३५ \|\| <td> १अ <BR> १छ्` | Not merely lost — this is the one place in the corpus where the local verse index is *printed* rather than derived, so it is lifted and used to **check** the derivation |
| 6 | **No opening separator at all** | `… चर्षणीनां ७१३ ॥` | **1 marker lost, and it was a WELD, not a gap.** Read as an ordinary pāda line, so verse 713's text was appended to verse 714 and `UTTARA:P01:R02:D01:V01` denoted two printed verse units. Found by the adversarial pass, not by the repair |
| 7 | Daśati heading written **parenthesised** rather than bare | `(१)` instead of `१` | Read one whole ardha (page `2.4.2`, 58 verses) as having *no daśati structure at all* |

**Family 4 is evidence, not just a bug.** Running numbers 1133 and 1592 are printed with a
single daṇḍa in **both** lineages, and the count ledger independently recorded exactly
those two values as GRETIL's single-daṇḍa cases. See §8.

**Gāna is excluded by notation, not by position.** The arcika text and the gāna (song)
text are *interleaved on the same pages*. Gāna is a separate work (Refusal 5) with its own
numbering, and its lines are written in the Sāmaveda svara notation using the Devanāgarī
Extended combining marks U+A8E0–U+A8F1. Detecting them by notation is what keeps a gāna
verse number out of the arcika running series — 64 gāna lines excluded, and without that
filter the corpus reports a spurious duplicate of running number 3 and a marker with no
text. *Recorded finding:* `normalize.VEDIC_ACCENT_CODEPOINTS` does **not** cover
U+A8E0–U+A8F1, so `has_vedic_accents` returns `False` for accented Sāmaveda gāna. Not
changed here — that constant is shared by all four Vedas and altering it is a contract
change, not a Sāmaveda repair.

---

## 4. Segmentation derived from source evidence

### 4.1 The address comes from the page title, read per collection

The dotted number in a page title is **not** a uniform coordinate. Slot 3 means
*prapāṭhaka* under `1.1.x`, *daśati* under `1.2.x`, and *ardha* under `2.x.y` — three
meanings in one witness. A positional read therefore mis-keys, and this is the mechanism
behind the previously recorded Collision A. `classify_page` reads the collection segment
first and then validates the dotted address against the arity **that collection declares**,
refusing anything else:

| Collection | Title segment | Declared address | Leaf page is |
|---|---|---|---|
| `CHANDA` | `छन्द आर्चिकः` | `1.1.{prapāṭhaka}.{daśati}` | a daśati page |
| `ARANYA` | `अथारण्यार्चिकः` | `1.2.{daśati}` | a daśati page; **no prapāṭhaka level exists** |
| `MAHANAMNYA` | `महानाम्न्यार्चिकः` | *(none)* | the collection page itself, carrying all 10 verses |
| `UTTARA` | *(under* `उत्तरार्चिकः`*)* | `2.{prapāṭhaka}.{ardha}` | an **ardha** page; daśati is printed *inside* |

### 4.2 The local verse index is derived from printed arithmetic, and fails closed

The selected witness prints only the **running** number. Within one daśati those numbers
form a contiguous ascending run, so

```
local_index = running − first_running_of_the_dasati + 1
```

This is an arithmetic fact about numbers the source *prints*. **Document order is never
consulted**, so reordering a page cannot move a referent — which is what makes this a
derivation rather than positional identity. Where the run is **not** contiguous the
arithmetic does not close, and the derivation is **refused for the whole daśati**. A
positional fallback would silently renumber every verse after the break; that is precisely
the failure this design exists to prevent.

Where the source prints the index itself (family 5), the printed value wins and a
disagreement with the derived value is recorded as a defect.

---

## 5. The referent audit

`data/derived/samaveda_referent_audit.jsonl` — **one row per candidate verse occurrence**,
1,874 rows. Each row carries the source coordinates, the printed marker and its dialect,
the source locator, the line span, the pāda count, any source-declared index and pāda
labels, seven boolean anomaly flags, the resolved local index, the referent class, the
minted identity (or `null`), both text fingerprints, and the cross-witness corroboration
verdict.

### Referent cardinality classes

| Class | Count | Meaning |
|---|---:|---|
| `ONE_TO_ONE` | **1,844** | One canonical identity ↔ one source verse occurrence |
| `SOURCE_NUMBERING_ANOMALY` | 21 | The second witness contradicts this daśati's partition; identity **withheld** |
| `UNRESOLVED_REFERENT` | 9 | The daśati's printed run is non-contiguous; identity **withheld** |
| `MERGED_MULTIPLE_VERSES` | **0** | — |
| `SPLIT_SINGLE_VERSE` | **0** | — |
| `MARKERLESS_VERSE` | **0** | — |
| `DUPLICATED_MARKER` | 0 after resolution | Running number 1181 is printed twice; its daśati is withheld as a whole |
| `STRUCTURAL_COLLISION` | **0** | — |

### Headline measurements

| Measurement | Value |
|---|---:|
| Arcika pages pinned | 106 (87 leaf, 19 index) |
| Candidate verse occurrences | 1,874 |
| Distinct printed verse markers | **1,873** |
| Markers not printed by the selected witness | 2 — `1179`, `1315` |
| Markers not printed by **either** witness | 1 — `1179` |
| Duplicated markers | 1 — `1181` |
| Canonical keys minted | **1,844** |
| Distinct canonical keys | **1,844** (injective) |
| **Addresses absorbing more than one printed verse** | **0** |
| **Source occurrences claimed by two keys** | **0** |
| Spurious verse keys | **0** |
| Verses carrying a leftover marker numeral in their text | **0** (the weld detector) |
| Gāna lines excluded by notation | 64 |
| Apparatus segments discarded after a terminal marker | 65 |

### The count equation

```
1875  =  1873 distinct printed markers  +  2 the selected witness does not print
1875  =   650 Purvarcika group (COMPLETE)  +  1225 Uttararcika (1223 printed + 2 absent)
1875  =  1844 minted keys  +  29 withheld printed verses  +  2 unprinted verses
```

The 1,874 candidate *occurrences* are the 1,873 distinct markers plus one duplicate of
`1181`; 30 occurrences are withheld, covering 29 distinct printed verses. Of the two
unprinted values, `1179` falls inside an already-withheld group and `1315` does not.

**The Pūrvārcika group reproduces the traditional 650 exactly**, from the selected witness
alone, as `585 + 55 + 10` — three collections whose extents no witness disputes, with no
gap and no surplus. This is the strongest single corroboration in the repair.

| Collection | Occurrences | Distinct markers | Keys minted | Traditional |
|---|---:|---:|---:|---:|
| `CHANDA` | 585 | 585 | **585** | 585 |
| `ARANYA` | 55 | 55 | **55** | 55 |
| `MAHANAMNYA` | 10 | 10 | **10** | 10 |
| *Pūrvārcika group* | *650* | *650* | ***650*** | ***650*** |
| `UTTARA` | 1,224 | 1,223 | 1,194 | 1,225 |

---

## 6. Cross-witness structural validation

`scripts/compare_samaveda_sources.py` (rewritten; it did not run at HEAD) compares
**addresses only**. No encumbered Sanskrit is read, stored or printed: reference labels and
printed running numbers only. That use is affirmatively granted — the artifact carries
`verification_roles: [hierarchy, reference_system, edition_comparison]` while its
`bulk_ingestion_status` remains `PROHIBITED_PENDING_RIGHTS_RESOLUTION`.

The join key is the printed running number, and it is **not injective on either side** — 
1181 sits on two addresses in both lineages — so ambiguous values are excluded from the
agreement rate rather than silently first-won.

| Axis | Compared | Agree | Disagree |
|---|---:|---:|---:|
| **Collection** | 1,867 | **1,867** | **0** |
| `CHANDA` prapāṭhaka / daśati / verse | 585 | 585 / 585 / 585 | 0 / 0 / 0 |
| `ARANYA` daśati / verse | 55 | 55 / 55 | 0 / 0 |
| `MAHANAMNYA` verse | 10 | 10 | 0 |
| `UTTARA` prapāṭhaka | 1,217 | **1,217** | 0 |
| `UTTARA` ardha | 1,217 | **1,217** | 0 |
| `UTTARA` daśati | 1,217 | 1,201 | **16** |
| `UTTARA` verse | 1,217 | 1,187 | 30 |

**Zero collection disagreements over 1,867 comparisons is the measurement that closes the
arity blocker.** The two lineages disagree about how to *number* the top level and agree
completely about what *belongs* to each collection.

**The 30 verse disagreements are the old defect being corrected, not a new one.** Running
number 666 is GRETIL verse 3 and Wikisource verse 1 — that is the welded address
`(4,1,1,6,3)` which absorbed 666, 667 and 668. The selected witness prints them at three
distinct addresses.

**Complementary coverage, and it is exact.** Only in GRETIL: `1315`. Only in
Wikisource: `1035`, `1133`, `1211`, `1592` — **exactly** the four values the count ledger
recorded as "printed in GRETIL but lost to adapter regex strictness." The repaired parser
recovers all four from the other lineage. Missing from **both**: `1179` alone, which
independently confirms the ledger's identification of it as the single genuinely unattested
value in the corpus.

**A corroboration coverage gap that is not a defect, recorded so it is not mistaken for
one.** Those same four values are the four released keys whose corroboration verdict is
*not comparable* rather than *agreed*: the join key is the printed running number, and the
second witness prints none for them, so there is nothing to join on. Checked by hand, all
four agree coordinate-for-coordinate including the verse index — the second witness's
unnumbered verses at `(4,4,1,2,2)`, `(4,4,2,2,6)`, `(4,5,1,6,2)` and `(4,7,3,10,3)` are
exact matches. A join-key limitation, not an unverified address.

**And 67 further occurrences have their verse index marked not comparable**, across 13
second-witness daśati units whose own local numbering is broken — a verse carrying two or
three running numbers, none at all, or an index of `0`. Their container addresses are still
compared. Comparing a verse index against a demonstrably broken local numbering withheld 25
keys the selected witness gets right, which is a different failure from the one this gate
exists to catch, so the soundness of the witness's unit is checked before its testimony on
that level is used.

---

## 7. What the 16 daśati disagreements are, and why identity is withheld

All 16 fall on four Uttarārcika ardha pages. Worked example, page `2.4.1`:

```
254  DASATI  >>> 22 <<<
255  MARK [1107]   256  MARK [1108]   257  MARK [1109]
258  MARK [1110]   259  MARK [1111]   260  MARK [1112]
263  MARK [1113]   264  MARK [1114]   265  MARK [1115]
```

Nine verses under one heading. The second witness declares 1107–1109 as daśati 22,
1110–1112 as daśati **23**, and 1113–1115 as daśati **24**. Headings 23 and 24 are simply
**absent** from the page — verified by reading it, not inferred.

**A group-size heuristic was tried and rejected.** Uttarārcika daśatis are mostly 2–3
verses (350 of 398 groups), so a size outlier looks like a reliable signal. It is not:
measured against the second witness, groups of 6, 7, 10 and 12 verses are **genuine and
corroborated** (e.g. page `2.4.1` daśatis 3 and 4 each hold 10 and both agree). The
heuristic flags 2 groups and misses most real cases. Cross-witness comparison is the only
sound detector, and this is recorded so the heuristic is not shipped later.

**The whole affected daśati is withheld, not just the disagreeing verses.** If a heading is
missing the group's partition is wrong throughout, so partial minting would leave keys whose
local index shifts the moment the heading is supplied.

| Withheld group | Verses | Printed markers | Class | Cause |
|---|---:|---|---|---|
| `UTTARA:P4:R1:D22` | 9 | 1107–1115 | `SOURCE_NUMBERING_ANOMALY` | headings 23 and 24 absent |
| `UTTARA:P4:R2:D14` | 3 | 1172–1174 | `SOURCE_NUMBERING_ANOMALY` | heading absent; second witness reads daśati 13 |
| `UTTARA:P5:R1:D17` | 3 | 1241–1243 | `SOURCE_NUMBERING_ANOMALY` | heading absent; second witness reads daśati 16 |
| `UTTARA:P5:R2:D5` | 6 | 1280–1285 | `SOURCE_NUMBERING_ANOMALY` | heading absent — and this is the **displaced line block** the count ledger recorded on the other lineage at exactly running numbers 1282–1285 |
| `UTTARA:P5:R1:D2` | 9 | 1178, **1180, 1181, 1181**, 1182–1186 | `UNRESOLVED_REFERENT` | printed run non-contiguous: `1179` is typeset as a second `1181` |

Total withheld: **30 occurrences** — 21 for a contradicted partition, 9 for a non-contiguous
run. Corroboration tally over all 1,874 rows: **1,845 corroborated, 16 contradicted, 13 not
comparable** (the second witness does not print those numbers).

**Corroboration is a gate, not a minting input.** The adapter itself never consults the
second witness, so the canonical path has no dependency on an encumbered artifact. When the
artifact is absent the audit runs and reports `corroboration: NOT PERFORMED` — and a freeze
requires it to have been performed.

---

## 8. A finding that cuts against the independence claim

Recorded rather than buried, because it is the most consequential thing found this run
that the run was not looking for.

The Wikisource text carries, at the same loci, defects the count ledger attributes to the
GRETIL artifact:

| Locus | Defect | GRETIL | Wikisource |
|---|---|---|---|
| RN 1179 | typeset as a second `1181`, producing `1178, 1181, 1180, 1181, …` | yes | **yes** |
| RN 1133 | single daṇḍa where a double belongs | yes | **yes** |
| RN 1592 | single daṇḍa where a double belongs | yes | **yes** |

The project's independence claim rests on **one** locus (the verse-1/verse-2 pāda bleed at
running numbers 1–2) and is already graded `NOT_A_VERBATIM_COPY` rather than proven. Here
are **three loci pointing the other way**. Two readings are open — common descent, or a
defect inherited from a shared print antecedent — and **this run does not adjudicate
between them**.

Consequence, and it is narrow: independence is *not* load-bearing for identity, because
identity is mechanically source-blind. It *is* load-bearing for **text redistribution**,
because the redistribution basis is CC BY-SA on the *transcription*. The sole rights
authority requires re-verification at codepoint level at **more than two loci** before any
bulk text release. This is now tracked as
`independence_codepoint_reverification: OPEN_RESEARCH`, and the 106-page fetch makes it
cheap. It must be done **outside** the Pūrvārcika defect-free zone.

---

## 9. The referent-integrity invariant

### What was missing

The only identity gate in the repository is `stable_uuid_deterministic`, and its inputs are
the URN it is comparing against and a compile-time namespace constant:

```python
recomputed = str(uuid_for_urn(passage.canonical_urn))
if recomputed != str(passage.entity_id):
    issues.append(...)
```

It asserts a self-consistency property **of the key** and is structurally incapable of
saying anything about the text behind it. `Passage` carries no text field. `qa/checks.py`
references `text_original` exactly once, as a UTF-8 encodability assert. `TextVersion` does
carry a `content_sha256`, but it is derived at write time and **no check reads it**.

So a moved referent under a stable key was reported as a **success** by every gate in the
build. Worked example, fully measured on the old build: key
`VG:SV:KAU:A4:P01:R1:D06:V03` held 197 characters welded from running numbers 666, 667 and
668; after the declared repair it holds 66 characters, running 668 alone. Key, URN and UUID
**byte-identical**. Every gate green in both states. Renumbering is at least visible in a
diff; this was not.

### What now exists

`models.PassageReferentBinding` — one record per released key:

| Field | Role |
|---|---|
| `canonical_key`, `canonical_urn`, `entity_id`, `work_id` | the identity being bound |
| `structural_coordinates` | the address, per the collection's declared shape |
| `source_id`, `source_artifact_id`, `source_locator` | which artifact and where in it |
| `source_revision_id`, `source_snapshot_sha256` | the exact mutable-wiki revision, pinned |
| `source_verse_marker` | the source's own printed number, as **evidence**, never identity |
| `text_sha256` | digest of the source bytes as spelled |
| `comparison_sha256` | digest of a **normalization-independent** surface |
| `segmentation_policy_version`, `parser_version` | what produced the segmentation |

**The fingerprint is a GUARD, not identity.** It is never an input to `uuid_for_urn`;
canonical keys name no source; replacing a TextVersion, re-fetching the artifact or
normalising the script cannot change a key. Passage identity remains source-independent and
TextVersions remain source-specific — the existing architecture is preserved exactly. What
the binding adds is the ability to *detect*, at build time, that the occurrence behind an
unchanged key has changed.

The two digests are separate on purpose: a change to `text_sha256` alone is a
**re-encoding**; a change to `comparison_sha256` is a **different verse**.

### The drift gate

`vedagraph.referent.compare_referents` classifies every key across two builds:

| Verdict | Trigger | Blocks release |
|---|---|---|
| `UNCHANGED_REFERENT` | comparison digest identical | no |
| `INTENTIONAL_REFERENT_CORRECTION` | digest changed **and** a recorded migration covers the key | no |
| `REFERENT_DRIFT` | digest changed with **no** covering migration | **YES** |
| `REMOVED_INVALID_PASSAGE` | key gone **and** a retirement migration covers it | no |
| `REFERENT_DRIFT` | key gone with no retirement migration | **YES** |
| `NEWLY_DISCOVERED_PASSAGE` | key absent from the previous build | no |

`assert_no_referent_drift` raises `ReferentDriftError`. Filling a coverage gap is additive
and never drift; silently re-pointing a key is always drift.

**The baseline is committed at `tests/fixtures/identity/sv_referent_baseline.jsonl`** — 
1,844 rows, 550 KB. It is *not* under `data/derived/`, because `data/derived/**` is
gitignored and a baseline written there would silently not be a baseline. This is the same
untracked-artifact hazard the repository has already recorded twice. The baseline stores
only the four fields the comparison reads, plus the printed marker as evidence; storing
whole bindings would have made it the largest tracked file in the repository by 2×.

---

## 10. What remains open

| Item | State | Why it is not an identity blocker |
|---|---|---|
| **31 verses carry no key** | `arcika_coverage_completeness: OPEN_ENGINEERING` | A coverage gap, not an ambiguity. No minted key can denote a different verse. Because the *whole* affected daśati is withheld, supplying the missing structure **adds** keys without renumbering any existing one |
| **Codepoint independence re-verification** | `independence_codepoint_reverification: OPEN_RESEARCH` | Gates public **release** of the Sanskrit, not ingestion or identity |
| **No `WIKISOURCE_SA.SV.KAU.*` text_version registered** | Registry gap | The adapter's default `text_version_id` resolves against nothing, so a build would bind rows to the encumbered `GRETIL.SV.KAUTHUMA` at `PERMISSION_REQUIRED`. Must be created before a canonical build |
| **"Pūrvārcika" extent: 585 or 650** | Philological, open | Answering it changes the container spine and renumbers **no key** — which is exactly the property the ordinal scheme lacked |
| **Printed-edition recension** | `OPEN_RESEARCH` | Established as not required to freeze Passage identity |
| **Gāna** | `DEFERRED_NONBLOCKING` | ~2,639 gānas against 1,875 arcika verses; needs its own `work_id`. No claim to "have the Sāmaveda" is warranted while holding only the arcika |

---

## 11. What the adversarial pass broke, and what that cost

The first repaired build was submitted to a hostile review with an explicit instruction to
assume it was wrong. It returned **`DO_NOT_FREEZE`** with a verified blocking case, and it
was right. This section records what it found, because three of the four defects were in
the *gate* — the thing added to catch exactly this class of problem.

### 11.1 The blocking case: one dropped boundary

`… चर्षणीनां ७१३ ॥` — a verse-terminal marker with no opening separator. Exactly one such
line exists in the 106-page corpus. The repaired lifter read it as a pāda and welded verse
713 onto verse 714, so `VG:SV:KAU:UTTARA:P01:R02:D01:V01` denoted **two** printed verse
units, and repairing it would have moved that key and `:V02` onto different occurrences.

Three gates were blind to it, each independently:

1. **The audit asserted the property it was measuring.**
   `source_verse_units_represented = 1 if running_number is not None else 0`, with the
   comment "one printed marker terminates exactly one verse unit in this corpus" — which is
   precisely the claim the audit exists to test. Now derived from `stray_numerals()`: a
   free-standing numeral left inside verse text *is* a boundary the lifter missed, and it
   catches this case with no second witness at all.
2. **Corroboration compared three of the four levels.** It checked prapāṭhaka, ardha and
   daśati and never the **verse index** — the identity-bearing leaf, which the second
   witness also declares. Comparing three of four and reporting "corroborated" is worse
   than not comparing, because it produces a confident record.
3. **The comparison surface strips digits.** `SEARCH_NORMALIZED` deletes all numerals, so
   the stray `७१३` sitting inside the stored text vanished before hashing.

### 11.2 The gate had a hole big enough to drive the corpus through

Two findings that matter more than the marker, because they were design errors rather than
a missed dialect.

**Text is not sufficient to identify an occurrence in this corpus, and the Sāmaveda is the
reason.** The Uttarārcika repeats Pūrvārcika verses verbatim in gāna context. Measured over
the released set: only **1,658 distinct `comparison_sha256` across 1,844 keys** — 184
equivalence classes covering **369 keys (20%)** share a digest, and 173 of those classes
share a byte-identical raw digest too. A gate comparing digests alone accepted a wholesale
rewrite of **every** `source_locator` as 1,844 unchanged referents, and accepted two
genuinely different occurrences swapping keys. `_same_occurrence` now compares the locator
and the printed marker as well — both were already stored in the baseline and simply never
read.

**An append-only ledger had become a standing licence to drift.**
`KEY_REASSIGNED_BEFORE_FREEZE` was counted as a *correction* class and both the old and new
key names were registered, so the 137 shape-change rows of this very run pre-licensed
referent change on **105 already-released keys** and removal on **99** — permanently, from a
committed file. Fixed three ways: that class is no longer a correction (a reassignment
retires the old key and the new one is simply new), removal licences key off the old name
only, and `compare_referents` takes a `licensing_run` so a row recorded for one release
cannot license the next.

### 11.3 A text-contamination defect, caught with the fix still free

The re-attack found `clean_wikitext`'s tag list omitted `table|tr|td`. The row and cell
splitters that *do* handle them are used only when reading the declared local index, never
on the body path. So on the two table-dialect pages, **20 released verses carried raw
`<tr>/<td>/</tr>` in their stored text and 18 of them also carried the previous table
row's pāda label**:

```
VG:SV:KAU:CHANDA:P01:D04:V02  (RN36)
  १छ् </tr> <tr><td> पाहि नो अग्न एकया पाह्यू३त द्वितीयया | पाहि गीर्भिस्...
```

**Classified as contamination, not a weld, and the distinction was checked rather than
assumed.** Every one of those 20 verses has exactly two real pādas, matching the second
witness's two lines for all ten verses on each page, and `local_index` equals both the
printed label and the second witness's verse index. No verse text was lost, absorbed or
duplicated; the addresses were correct throughout. It did not breach the freeze bar.

**It was still worth fixing before committing, and this is the more interesting point.**
The leaked label survives `SEARCH_NORMALIZED` — digits are stripped, the letter `छ्` is
not — so those 20 keys would have pinned a *contaminated* `comparison_sha256` into the
committed baseline. A later markup cleanup would then change the digest while the locator
and marker held, which under the repaired `_same_occurrence` is **20 `REFERENT_DRIFT`
findings requiring 20 migration rows for what is purely a cleanup**. The gate would have
been correct and the ledger would have been polluted. Cost to fix now: one regex, one
apparatus rule for label-only lines, and a rebuild.

The weld detector was also wrong in both directions in turn, which is recorded because the
sequence is instructive. Whitespace-bounded, it missed every leftover numeral adjacent to
punctuation — which is the shape a marker actually takes, a numeral beside a daṇḍa.
Rewritten with `\w` boundaries, it then reported all 20 of the corpus's in-word numeric
svarita as leftover markers, because a svarita digit is flanked by Devanagari **combining
marks** and `\w` does not match those. The rule is now "neither neighbour is a letter *or*
a mark", pinned in both directions.

### 11.4 Claims that were overstated and are now qualified

- *"HTML order is never consulted, so a reordering of the page cannot move a referent."*
  Half true, and the half that is false covers 1,194 keys. The **verse index** is order-free
  — arithmetic over printed numbers, sorted by value, verified stable under permutation with
  three seeds. The **daśati** of an Uttarārcika verse is the nearest preceding printed
  numeral *in document order*, because that is how the source declares it. A property of the
  source's layout, not a parser choice, but a real dependency and now recorded as one.
- *"The selected witness does not print 713."* Written into four files before it was
  checked against every dialect the source uses.
- **A group-size heuristic for detecting missing daśati headings was measured and
  rejected.** Uttarārcika daśatis of 6, 7, 10 and 12 verses are genuine and
  cross-witness-corroborated, so the outlier rule caught 2 of 5 real cases. Recorded so it
  is not shipped later.

### 11.5 What survived unbroken

The key *shape* withstood every structural attack: **2,085,583** identifiers minted across
all four works with **0** collisions in key, URN or UUID space; prefix-free; lexicographic
order equal to coordinate order; one key length per collection with ≥76 headroom before the
fixed width would need to change; deterministic across four separate OS processes; valid
parent chain on all released keys; and the four collection shapes handled from three levels
below the collection down to none. **The blocker was never the scheme.**

### 11.6 One honest gap that remains in the gate

`compare_referents` and `assert_no_referent_drift` are called from the test suite and from
nowhere else. There is no canonical Sāmaveda build path to wire them into yet — the pilot
that used to produce one has been retired because it minted identity from the encumbered
artifact — so wiring the gate into a build that does not exist would be speculative. The
gate, the committed baseline and the ledger are in place; connecting them to the first real
build is the next phase's work, and is listed in §10.

---

## 12. Cross-references

- [`SAMAVEDA_ARCIKA_ARITY_DECISION.md`](SAMAVEDA_ARCIKA_ARITY_DECISION.md) — how the arity blocker was dissolved, and the level classification
- [`SAMAVEDA_FINAL_IDENTITY.md`](SAMAVEDA_FINAL_IDENTITY.md) — the frozen key, URN and UUID policy, and the freeze attack
- [`SAMAVEDA_REFERENT_MIGRATION.md`](SAMAVEDA_REFERENT_MIGRATION.md) — the 144-entry migration ledger
- [`SAMAVEDA_COUNT_RECONCILIATION.md`](SAMAVEDA_COUNT_RECONCILIATION.md) — superseded on the corpus it measures; retained as the record of a now-unrepresentable defect family
- `data/source_registry/samaveda_count_ledger.yaml` — forensics on the **rejected** witness; its four-number ladder does not describe the canonical corpus
