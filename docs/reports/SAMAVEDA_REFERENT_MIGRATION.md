# Sāmaveda Referent Migration Ledger — Every Canonical Key Changes

**Run:** `SAMAVEDA_REFERENT_INTEGRITY_REPAIR` · **Date:** 2026-09-07
**Starting commit:** `5896856` · **Work:** `VG:WORK:SV:KAU` (Kauthuma, ārcika corpus only)
**Ledger:** `data/source_registry/samaveda_referent_migrations.jsonl` — **144 entries**
**Verdict:** `EVERY_SAMAVEDA_KEY_REASSIGNED_BEFORE_FREEZE` — 137 reassignments, 6 referent
corrections, 1 spurious passage retired. **Not backwards compatible, and not described as such.**

No encumbered Sanskrit is reproduced anywhere in this document — keys, URNs, printed running
numbers and character counts only.

---

## 0. Verdict

### `EVERY_SAMAVEDA_KEY_REASSIGNED_BEFORE_FREEZE`

- **Every** Sāmaveda canonical key changes in this run, because the key **shape** changed.
- **Nothing was externally frozen.** `key_pattern` was `null` and `identity_status` was
  `RESEARCH_REQUIRED` for the entire life of the superseded scheme, no Sāmaveda release was ever
  published, and the only materialized rows sat in a **gitignored** pilot build.
- **Pre-freeze is the correct time to fix identity.** After a freeze this same change would be a
  breaking migration with external consumers; before one it is free.
- **But a null `key_pattern` did NOT function as a safety mechanism** — see §4.
- **No other work is touched.** Rigveda, Yajurveda and Atharvaveda identity are unchanged.

| Migration class | Count | What it records |
|---|---|---|
| `KEY_REASSIGNED_BEFORE_FREEZE` | **137** | The key string changed; the referent did not |
| `REFERENT_CORRECTED` | **6** | The key denoted a weld of several printed verses; it now denotes one |
| `PASSAGE_REMOVED_AS_SPURIOUS` | **1** | The key identified a verse that does not exist |
| **Total** | **144** | |

**MEASURED** by re-reading the ledger: all 144 entries carry
`work_id: VG:WORK:SV:KAU`, `recorded_by_run: SAMAVEDA_REFERENT_INTEGRITY_REPAIR` and
`externally_frozen_before_change: false`. No entry has any other value for any of the three.

---

## 1. Why every key changes

The superseded keys were `VG:SV:KAU:A{arcika}:P{..}:R{..}:D{..}:V{..}`. Four independent changes
to the shape mean **not one** old key survives:

1. **The ārcika ordinal became a collection name.** `A1` → `CHANDA`, `A2` → `ARANYA`,
   `A3` → `MAHANAMNYA`, `A4` → `UTTARA`. The ordinal had no stable denotation across witnesses —
   slot-1 value `2` means Āraṇyārcika in the Pandey lineage and Uttarārcika in all six independent
   witnesses, a 1,225-verse collision. See `docs/reports/SAMAVEDA_ARCIKA_ARITY_DECISION.md`.
2. **The ardha level was dropped from the collections that do not declare one.** `CHANDA` and
   `ARANYA` and `MAHANAMNYA` lose their `R` slot entirely; only `UTTARA` keeps it, where the daśati
   resets inside each ardha and it is load-bearing.
3. **The literal `0` that encoded an absent level is gone.** A level a collection does not declare
   is now **omitted**, and `identity._sv_levels` **refuses** a value for it rather than coercing
   it. Writing `0` made the rejected edition's flattening choice part of canonical identity.
4. **Every slot is padded to two digits.** The old scheme left the ārcika and ardha slots
   unpadded, so `A10` sorted before `A2` and the verse slot was two digits at `V01` and three at
   `V100`.

### Old-to-new mapping

| Old top slot | New collection | Verses | Levels the new key carries |
|---|---|---|---|
| `A1` | `CHANDA` | 585 | prapāṭhaka, daśati |
| `A2` | `ARANYA` | 55 | daśati |
| `A3` | `MAHANAMNYA` | 10 | *(none)* |
| `A4` | `UTTARA` | 1,225 | prapāṭhaka, ardha, daśati |

Recorded in code as `OLD_ARCIKA_TO_COLLECTION` in
`scripts/build_samaveda_referent_migrations.py:37`.

### Worked examples, MEASURED from the ledger

| Old key | New key | Old URN | New URN |
|---|---|---|---|
| `VG:SV:KAU:A1` | `VG:SV:KAU:CHANDA` | `urn:…:arcika:1` | `urn:…:chanda` |
| `VG:SV:KAU:A4:P01:R1:D06:V03` | `VG:SV:KAU:UTTARA:P01:R01:D06:V03` | — | — |

Note the entity UUID changes too: `VG:SV:KAU:A1` was
`64f93593-b584-5e4d-bf1a-e1c979d84d13`, `VG:SV:KAU:CHANDA` is
`cd92b6cc-7eb1-5685-a9bb-1c7edaecea81`. **The UUID is `uuid5` over the URN, so a URN change is a
UUID change.** There is no path by which an old identifier resolves to a new row.

---

## 2. How the ledger was generated

`scripts/build_samaveda_referent_migrations.py`, 313 lines. Its output is written to
`data/source_registry/` rather than `data/derived/` for a stated reason: **`data/derived/**` is
gitignored, and a migration ledger that is not committed cannot license anything.** Verified —
`git check-ignore` reports the ledger path is **not** ignored, while
`data/derived/samaveda_cross_witness_structure.json` and
`data/canonical/samaveda_pilot_v1/passages.jsonl` **are**.

The script emits four groups, in this order:

| # | Group | Rows | Method |
|---|---|---|---|
| 1 | **The scheme-level record** | 1 | One `KEY_REASSIGNED_BEFORE_FREEZE` entry with no `old_canonical_key`, carrying the reason and the 1,867/1,867 evidence **once** rather than repeating it 139 times |
| 2 | **The spurious passage** | 1 | One `PASSAGE_REMOVED_AS_SPURIOUS` entry for the phantom thirteenth verse (§7) |
| 3 | **Per-key rows for everything the pilot materialized** | 139 | Reads `data/canonical/samaveda_pilot_v1/passages.jsonl`; regex-splits each old key (`_OLD_MANTRA` / `_OLD_CONTAINER`); maps the ārcika ordinal to a collection; re-mints the new key/URN/UUID by **calling `sv_mantra_identity` / `sv_container_identity` directly** rather than string-rewriting |
| 4 | **Welded keys the pilot never materialized** | 3 | Iterates `WELDED_KEYS`, skipping any already emitted, so the ledger records the **whole defect family** rather than only the sampled part |

**Arithmetic, MEASURED and closing exactly:**

```text
144 total
  =   1 scheme-level record          (KEY_REASSIGNED_BEFORE_FREEZE, no old key)
  +   1 spurious passage             (PASSAGE_REMOVED_AS_SPURIOUS)
  + 136 materialized non-welded keys (KEY_REASSIGNED_BEFORE_FREEZE)
  +   3 materialized welded keys     (REFERENT_CORRECTED)
  +   3 unmaterialized welded keys   (REFERENT_CORRECTED)

137 KEY_REASSIGNED_BEFORE_FREEZE = 136 per-key + 1 scheme-level
139 pilot rows                   = 136 non-welded + 3 welded
  6 REFERENT_CORRECTED           = 3 materialized + 3 not
```

**Coverage check, MEASURED:** every one of the 139 pilot `canonical_key` values appears as an
`old_canonical_key` in the ledger — the set difference is empty in that direction. The four
`old_canonical_key` values **not** in the pilot are the phantom key and the three unmaterialized
welds, which is exactly the intended asymmetry.

**New keys by collection, MEASURED:** `CHANDA` 49, `ARANYA` 11, `MAHANAMNYA` 11, `UTTARA` 71 =
142. The two rows with no `new_canonical_key` are the scheme-level record and the retired phantom.

Two properties of the generation method are worth naming, because they are what make the ledger
trustworthy rather than decorative:

- **New keys are minted by the frozen identity functions, not by string substitution.** A new key
  in the ledger that the frozen contract would refuse cannot exist, because the contract minted it.
- **The old-key regexes accept the shape the old scheme actually emitted**, including the unpadded
  `R{ardha}` slot and the literal `0`. `new_container` explicitly drops any level the old scheme
  wrote as `0`, and drops every level *below* the first such — that is the `seen_none` loop at
  `build_samaveda_referent_migrations.py:139`.

---

## 3. Migration-class vocabulary and what each licenses

From `src/vedagraph/referent.py`. `MigrationClass` defines six classes; two frozensets decide what
each one licenses.

| Class | In `_CORRECTION_CLASSES`? | In `_REMOVAL_CLASSES`? | Licenses |
|---|---|---|---|
| `REFERENT_CORRECTED` | **yes** | no | An existing key's referent changing |
| `PASSAGE_SPLIT` | **yes** | no | An existing key's referent changing |
| `PASSAGE_MERGED` | **yes** | no | An existing key's referent changing |
| `SOURCE_NUMBERING_CORRECTION` | **yes** | no | An existing key's referent changing |
| `KEY_REASSIGNED_BEFORE_FREEZE` | **yes** | **yes** | **Both** — a referent change *and* a key's disappearance |
| `PASSAGE_REMOVED_AS_SPURIOUS` | no | **yes** | A key's disappearance only |

`compare_referents` classifies every canonical key across two builds into five verdicts:

| Verdict | Condition | Blocks release? |
|---|---|---|
| `UNCHANGED_REFERENT` | `comparison_sha256` identical (a `text_sha256`-only change is reported here as a **re-encoding**, not a re-pointing) | no |
| `NEWLY_DISCOVERED_PASSAGE` | key absent from the previous build | no |
| `INTENTIONAL_REFERENT_CORRECTION` | `comparison_sha256` changed **and** a migration in `_CORRECTION_CLASSES` covers the key | no |
| `REMOVED_INVALID_PASSAGE` | key disappeared **and** a migration in `_REMOVAL_CLASSES` covers it | no |
| **`REFERENT_DRIFT`** | `comparison_sha256` changed, **or** the key disappeared, with **no covering migration** | **YES** |

**`ReferentDelta.blocks_release` is true for `REFERENT_DRIFT` and nothing else, and
`assert_no_referent_drift` raises `ReferentDriftError`. A referent drift with no covering
migration FAILS THE BUILD.** The raised message says so in terms:

> *"N canonical key(s) changed their textual referent with no recorded migration. This is a
> breaking change even though the UUIDs are unchanged."*

Two design constraints, both stated in the module and both load-bearing:

- **The fingerprint is a guard, never an identity input.** `PassageReferentBinding.text_sha256` is
  never passed to `uuid_for_urn`, canonical keys never mention a source, and replacing a
  `TextVersion` cannot change a key.
- **`KEY_REASSIGNED_BEFORE_FREEZE` is the only class in BOTH sets.** That is deliberate and it is
  also the widest licence in the vocabulary: it covers a referent change *and* a disappearance.
  It is the correct class for a whole-scheme reshape, and it should be the last time it is used
  for this work, because the freeze is what removes its justification.

**Committed baseline:** `tests/fixtures/identity/sv_referent_baseline.jsonl`, **1,844 rows**
(MEASURED), one per minted key. `write_baseline` stores a `ReferentFingerprint` — key, locator,
`text_sha256`, `comparison_sha256`, printed verse marker — rather than a whole
`PassageReferentBinding`, because the parser version, snapshot digest, revision id and structural
coordinates are all reproducible from the build and storing them per key would make the baseline
the largest tracked file in the repository while adding nothing the comparison reads.

---

## 4. Nothing was externally frozen — and the null key was not a safety mechanism

**MEASURED:** all 144 entries carry `externally_frozen_before_change: false`.

The justification, verified against the repository:

| Claim | Evidence |
|---|---|
| `key_pattern` was `null` throughout the superseded scheme's life | `git show HEAD:data/registry/works.yaml` line 20: `key_pattern: null` |
| `identity_status` was `RESEARCH_REQUIRED` throughout | same file, line 21 |
| No Sāmaveda release was ever published | no release artifact exists for `VG:WORK:SV:KAU` |
| The only materialized rows were in a gitignored pilot | `git check-ignore` → `.gitignore:17:data/canonical/**` matches `data/canonical/samaveda_pilot_v1/passages.jsonl` |
| The pilot is regenerated from pinned snapshots | `data/raw/wikisource_sa/2026-09-07/`, per-page sha256 and revid |

The old `works.yaml` note stated the position explicitly: *"key_pattern nevertheless stays null and
identity_status stays RESEARCH_REQUIRED. The hierarchy is an observation; the key is a commitment,
and the commitment cannot yet be made… It is a candidate, not a declaration, and nothing may treat
it as canonical."*

**Pre-freeze is the correct time to fix identity.** Had the arity blocker been worked around
instead of named — had `A{arcika}` been frozen because the level *list* was corroborated — this
same repair would have arrived after publication, with 1,280 mis-addressed verses in the wild and
no way to distinguish a corrected key from a moved one.

> ### But the null key was not functioning as a safety mechanism, and this is the finding
>
> **A null `key_pattern` and an `identity_status` of `RESEARCH_REQUIRED` did not prevent 139 rows
> being materialized at `status: CANONICAL`.**
>
> **MEASURED** in `data/canonical/samaveda_pilot_v1/passages.jsonl`: 139 passages —
> **102 `MANTRA` + 37 `STRUCTURAL_CONTAINER`** — and `Counter({'CANONICAL': 139})`. Every single
> row carried the status `CANONICAL` while the registry said the key was a candidate that nothing
> may treat as canonical.
>
> The registry declared a *policy*. The build wrote *rows*. Nothing connected the two. The
> superseded candidate key was implemented in `sv_mantra_identity` and callable, so any code path
> that called it produced a `CANONICAL` passage regardless of what `works.yaml` said about it.
>
> **The lesson is narrow and mechanical: a policy field is not a gate.** `vedagraph.referent` is
> the first mechanism in this work that actually refuses something — it compares a build against a
> committed baseline and raises. The null `key_pattern` refused nothing. Both statements can be
> true at once, and both are: the reassignment is licensed because nothing external consumed the
> keys, *and* the reason nothing external consumed them was luck of scheduling rather than a
> control.

---

## 5. The 137 `KEY_REASSIGNED_BEFORE_FREEZE` entries

**136 per-key rows plus 1 scheme-level row.** Each per-key row carries:

- `reason`: *"Key shape change only; the address denotes the same verse."*
- `evidence`: *"The old and new addresses agree on collection, prapāṭhaka, ardha and daśati under
  the recorded ārcika-to-collection mapping; only the spelling of the key changed."*
- `downstream_impact`: *"Key string, URN and UUID change; the textual referent does not."*

**The referent is unchanged; the identifier is not.** That is still a breaking change for any
consumer holding the old string — the old key resolves to nothing — but it is not a change in what
the text *is*. The distinction matters because it is exactly what the drift gate exists to
separate, and conflating them is what let a moved referent pass as a success in the previous build.

The **scheme-level row** exists so the justification is stated once. Its evidence field is the
cross-witness measurement: *"collection assignment agrees between the two lineages for 1,867 of
1,867 comparable printed verse numbers, 0 disagreements. The four collection extents
585/55/10/1225 are agreed by every witness, while the extent of the grouping name 'Purvarcika' is
itself disputed (585 or 650)."* It has no `old_canonical_key` and no `new_canonical_key`, because
it describes the reshape rather than any one key.

---

## 6. The 6 `REFERENT_CORRECTED` entries — the welded addresses

These are the entries where **the key meant something else**, not merely where it was spelled
differently. Each old key held a **concatenative** weld: every matching source line was appended
and `verse_text()` joined all of them, so the address held neither the first nor the last
constituent but a composite of several printed verses.

| Old key | New key | Printed markers | Materialized in pilot? | What the repaired key now denotes |
|---|---|---|---|---|
| `VG:SV:KAU:A4:P01:R1:D06:V03` | `VG:SV:KAU:UTTARA:P01:R01:D06:V03` | **666, 667, 668** | **yes** | Printed verse **668** alone. The old key held a **197-character** weld against a **66-character** constituent (constituent lengths 64 / 64 / 66). The selected witness prints 666/667/668 as three separate verses at V01/V02/V03 of the same daśati. Mechanism: `verse_index_field_stuck_at_03`. |
| `VG:SV:KAU:A4:P05:R2:D06:V03` | `VG:SV:KAU:UTTARA:P05:R02:D06:V03` | **1282, 1288** | **yes** | Printed verse **1288** alone. A displaced line block in the rejected witness put two printed verses on one address; the selected witness prints them at distinct addresses. |
| `VG:SV:KAU:A4:P05:R2:D10:V01` | `VG:SV:KAU:UTTARA:P05:R02:D10:V01` | **1307, 1308, 1309** | **yes** | Printed verse **1307** alone. The rejected witness's verse-index field stuck at `01`, absorbing three printed verses onto one address; the selected witness prints V01/V02/V03. |
| `VG:SV:KAU:A4:P05:R2:D07:V04` | `VG:SV:KAU:UTTARA:P05:R02:D07:V04` | **1283, 1295** | no | Printed verse **1295** alone. Displaced line block. |
| `VG:SV:KAU:A4:P05:R2:D08:V05` | `VG:SV:KAU:UTTARA:P05:R02:D08:V05` | **1284, 1302** | no | Printed verse **1302** alone. Displaced line block. |
| `VG:SV:KAU:A4:P08:R2:D08:V02` | `VG:SV:KAU:UTTARA:P08:R02:D08:V02` | **1679, 1680** | no | Printed verse **1680** alone. Pāda label off by one in the rejected witness. |

**VERIFIED against `data/canonical/samaveda_pilot_v1/passages.jsonl`:** exactly **three** of the
six were materialized — `A4:P01:R1:D06:V03`, `A4:P05:R2:D06:V03`, `A4:P05:R2:D10:V01`. The other
three were minted only when the full rejected corpus was parsed and never reached a build output.
The claim holds as stated.

`downstream_impact` for the three materialized rows: *"Referent narrowed: text previously
reachable under this key is now reachable under sibling keys. Any consumer holding the old key
held a composite of several verses."* For the three unmaterialized rows: *"Never materialized in a
build output."*

### 6.1 Two reconciliations against `samaveda_count_ledger.yaml`, reported rather than smoothed

**Contradiction 1 — the count ledger records SEVEN collided addresses, the migration ledger
records SIX corrections.** Both are right.

**MEASURED:** `collided_addresses` in `data/source_registry/samaveda_count_ledger.yaml` has 7
entries. One of them — markers `[1421, 1422]`, mechanism `verse_index_field_stuck_at_00`, address
`(4,6,2,16,00)` — has **`key: null`**. Verse index `00` is undefined by the declared reference
system, so `sv_mantra_identity` **failed closed and no key was ever minted for it**
(`canonical_key_assignable: false`). A weld with no key has no key to migrate.

```text
7 collided addresses − 1 with no canonical key = 6 migratable = 6 REFERENT_CORRECTED
```

The blocker registry's phrase "seven welded addresses" and this ledger's six entries describe the
same defect family at two different granularities. Neither figure is wrong; quoting either without
the other is.

**Contradiction 2 — the count ledger says `referents_that_move_under_an_unchanged_uuid: 5`, and
there are 6 corrections.** Also both right, and this one is more interesting.

**MEASURED:** of the 7 collided addresses, `referent_moves: true` on **5**. The exception among the
keyed six is `A4:P05:R2:D10:V01`, which carries `referent_moves: false` — because it welded 1307,
1308, 1309 onto a `V01` address whose **head** verse is 1307, and after repair `V01` still denotes
1307. The *first* verse did not move.

But the **text under the key changed**: it went from a three-verse composite to a single verse, so
its `comparison_sha256` changes and `compare_referents` classifies it as a change, not as
`UNCHANGED_REFERENT`. Classifying it `REFERENT_CORRECTED` is therefore correct under the gate's own
definition even though the denoted head verse is stable.

**The two numbers measure different things.** `referents_that_move_under_an_unchanged_uuid: 5`
counts keys whose *denoted verse* changed — the forensic question. The 6 `REFERENT_CORRECTED`
entries count keys whose *text under the key* changed — the gate question. **A key can hold the
same head verse and still be wrong**, and only the second count catches that. If anything the
discrepancy argues that the gate's definition is the better one: it is strictly wider, and the
extra case it catches is a genuine defect.

---

## 7. The 1 `PASSAGE_REMOVED_AS_SPURIOUS` entry

**`VG:SV:KAU:A4:P04:R2:D01:V13`** — a key that identified a verse that does not exist.

**The defect.** Daśati `(4,4,2,1)` prints twelve verse numbers, **1116…1127**. But two pāda labels
of **ONE** verse — `'12a'` and `'13c'` — landed in different verse buckets, so **thirteen addresses
were minted for twelve verses** and printed verse **1127 was split across two keys**.

**Why it was invisible.** From the count ledger's own `invisible_because` field: *"The two pāda
labels land in DIFFERENT verse buckets, so `DUPLICATE_LINE_LABEL` never fires. The corpus-wide
shortage (−9) and this local surplus (+1) cancel in the total, which is why a 1868-vs-1875 check
cannot see either."* Two independent detectors both missed it: the duplicate-label check because
the labels were not duplicates, and the total-count check because the errors cancelled.

**Confirmed by an independent witness, not by internal arithmetic.** The selected witness prints
**exactly twelve** verses in the corresponding daśati, and the repaired build mints **twelve** keys
there. That is the load-bearing distinction: the previous run's diagnosis rested on counting pāda
labels within the rejected artifact, which is the same source arguing with itself. A second
lineage printing twelve is external corroboration.

**It was never materialized in any build output** — MEASURED, the key is absent from
`data/canonical/samaveda_pilot_v1/passages.jsonl`. It was minted only when the full rejected
corpus was parsed.

**It is now UNREPRESENTABLE, not merely unused.** The daśati-local verse index is derived from the
source's own printed running-number arithmetic — rank within the daśati's contiguous ascending run
— so **no daśati-local index above the printed verse count can be produced.** The derivation
**fails closed** when the arithmetic does not close. A `V13` inside a twelve-verse daśati is not
something the repaired build declines to emit; it is something it cannot express.

The distinction matters. The previous scheme's `retraction_requires` field named the cost of the
old approach: *"Deleting a minted canonical key. Per ID_SPEC that demands a versioned migration
and an explicit mapping — which is precisely what freezing is meant to make unnecessary."* Making
the defect class unrepresentable is the alternative to patching its instances one at a time.

---

## 8. This is NOT backwards compatible

Stated plainly, and stated the same way the generating script and the model docstring state it.

`ReferentMigration`'s docstring: *"Nothing here is described as backwards compatible: if the
referent changed, the key means something else, and that is a breaking change even when the UUID
is unchanged."*

Three cases, all breaking, for different reasons:

| Case | Rows | Why it breaks |
|---|---|---|
| Key string changed, referent unchanged | 136 | The old key resolves to **nothing**. Not a rename with an alias — there is no alias. |
| Key string changed **and** referent changed | 6 | The key **means something else**. A consumer holding the old key held a composite of several printed verses; the new key holds one. |
| Key retired | 1 | The key denoted a verse that never existed. |

**"The UUID is unchanged" is not a defence, and here the UUID changed anyway.** The UUID is
`uuid5` over the canonical URN, and every URN changed, so every UUID changed. But the point
generalises past this run: a byte-identical UUID over a **moved referent** was reported as a
success by every gate in the previous build. `vedagraph.referent` exists precisely because UUID
determinism proves the URN hashes consistently and says nothing about what the URN addresses.

---

## 9. Downstream impact

**None outside this work.**

| Scope | Impact |
|---|---|
| `VG:WORK:SV:KAU` | **Total.** Every canonical key, URN and UUID changes. 1,844 keys in the new baseline. |
| `VG:WORK:RV:SAK` (Rigveda) | **Unchanged.** Not referenced by any ledger entry. |
| `VG:WORK:YV:VSM` (Yajurveda) | **Unchanged.** `identity_status: FINAL`, `key_pattern` untouched. |
| `VG:WORK:AV:SAU` (Atharvaveda) | **Unchanged.** |
| Any other `work_id` | **Unchanged.** MEASURED: all 144 ledger entries carry `work_id: VG:WORK:SV:KAU`; no other value appears. |

The scheme-level entry states the consumer position: *"Every Samaveda canonical key, URN and UUID
changes. Nothing downstream consumed them: `identity_status` was `RESEARCH_REQUIRED` and
`key_pattern` was `null` throughout, no Samaveda release was ever published, and the only
materialized rows are in a gitignored pilot build that is regenerated from pinned snapshots. No
other work is affected."*

---

## 10. Post-migration state

| Property | Value | Source |
|---|---|---|
| `identity_status` | `FINAL` | `data/registry/works.yaml` |
| `coverage_status` | `INCOMPLETE_BOUNDED` | same |
| `key_pattern` | `VG:SV:KAU:{collection}[:P{prapathaka:02d}][:R{ardha:02d}][:D{dasati:02d}]:V{verse:02d}` | same |
| Minted canonical keys | **1,844** of the traditional 1,875 | `tests/fixtures/identity/sv_referent_baseline.jsonl`, MEASURED 1,844 rows |
| Per-collection minted | CHANDA 585, ARANYA 55, MAHANAMNYA 10, UTTARA 1,194 | blockers registry `per_collection_minted` |
| Pūrvārcika group | **650 exactly**, as 585 + 55 + 10 | `purvarcika_group_exact: true` |
| Addresses absorbing more than one printed verse | **0** | `surplus_markers_absorbed: 0` |
| Source occurrences claimed by two keys | **0** | `one_referent_two_key_splits: 0` |
| Referents that move under an unchanged UUID | **0** | `referents_that_move_under_an_unchanged_uuid: 0` |
| Phantom canonical keys | **`[]`** | `phantom_canonical_keys: []` |
| Drift gate | `vedagraph.referent.assert_no_referent_drift` | `src/vedagraph/referent.py:275` |
| Baseline is git-tracked | **yes** | `referent_drift_baseline_is_git_tracked: true` |

The 32-key coverage gap is a **coverage** matter, not an identity ambiguity, and it is bounded:
`1875 = 1844 minted + 21 uncorroborated daśati partition + 9 non-contiguous run + 2 unprinted
outside those groups`. In every case **the whole affected daśati is withheld**, so supplying the
missing structure later **adds** keys without renumbering one. Tracked as
`arcika_coverage_completeness: OPEN_ENGINEERING`.

---

## 11. Provenance of every figure in this report

| Claim | Label | Re-derivable from |
|---|---|---|
| 144 entries; 137 / 6 / 1 class split | **MEASURED** | `data/source_registry/samaveda_referent_migrations.jsonl` |
| All 144 carry `externally_frozen_before_change: false`, one `work_id`, one run | **MEASURED** | same |
| 137 = 136 per-key + 1 scheme-level; new keys by collection 49/11/11/71 | **MEASURED** | same |
| Every pilot key is covered; the 4 extra old keys are the phantom + 3 unmaterialized welds | **MEASURED** | same, joined against the pilot |
| 139 pilot passages; 102 MANTRA + 37 STRUCTURAL_CONTAINER; all `CANONICAL` | **MEASURED** | `data/canonical/samaveda_pilot_v1/passages.jsonl` (gitignored, regenerable) |
| Exactly 3 of the 6 welded keys were materialized | **MEASURED** | same |
| Phantom key absent from the pilot | **MEASURED** | same |
| 197-character weld, constituents 64/64/66; markers and mechanisms for all 7 welds | **MEASURED** | `data/source_registry/samaveda_count_ledger.yaml`, `collided_addresses` |
| 7 welds vs 6 corrections; `referent_moves` true on 5 | **MEASURED** | same |
| Baseline 1,844 rows | **MEASURED** | `tests/fixtures/identity/sv_referent_baseline.jsonl` |
| `_CORRECTION_CLASSES` / `_REMOVAL_CLASSES` membership; drift fails the build | **MEASURED** | `src/vedagraph/referent.py:60–74`, `:275–289` |
| Old `key_pattern: null` / `identity_status: RESEARCH_REQUIRED` | **MEASURED** | `git show HEAD:data/registry/works.yaml` lines 20–21 |
| Pilot directory is gitignored; the ledger is not | **MEASURED** | `git check-ignore -v` |
| Old and new UUIDs for `VG:SV:KAU:A1` → `:CHANDA` | **MEASURED** | ledger row 3 |
| 1,867/1,867 collection agreement | **MEASURED** | `data/derived/samaveda_cross_witness_structure.json` |
| Per-collection minted, coverage equation, `phantom_canonical_keys: []` | **MEASURED** | `data/source_registry/four_veda_canonical_sanskrit_blockers.yaml`, `known_facts` |
| "No Sāmaveda release was ever published" | **INFERRED** from the absence of a release artifact | negative evidence; an absence over a surface, and this repository has twice been misled by exactly that form of argument. It is corroborated by `identity_status: RESEARCH_REQUIRED` and by the pilot being the only materialized build, but it is not a positive measurement. |
