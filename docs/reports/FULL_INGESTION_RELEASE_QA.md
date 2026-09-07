# FULL INGESTION RELEASE QA — adversarial review

**Reviewer role:** Agent F, release QA. The brief was to *attempt to reject* each release.
Every gate below was attacked with a working exploit, not read. "Held" means an exploit was
built, run, and refused; "did not hold" means the exploit built a release.

**Scope of this review**

| Release | Path | Headline claim | Verdict |
|---|---|---|---|
| Samaveda Kauthuma arcika | `data/canonical/samaveda_arcika_v1/` | 1,844 canonical keys, 2,342 passages | **RELEASE_APPROVED_WITH_BACKLOG** |
| Shukla Yajurveda VSM | `data/canonical/yajurveda_vsm_v1/` | 1,975 mantras, 2,015 passages | **RELEASE_REJECTED** |

Nothing in the repository was modified by this review except this file. Every mutation was
applied in memory or against a copied config, and every build was emitted into a temporary
directory that was deleted afterwards.

Method note: at the start of the review the working tree reproduced both releases **byte for
byte**, so the artifacts audited here are the artifacts the builders produce (see Attack 10).
A registry edit landed mid-session and made the committed Samaveda `source_artifacts.jsonl`
and manifest stale; no corpus content moved, and the consequence is recorded as **SV-4** in
section 7.

---

## 1. Verdicts and blocking defects

### Samaveda — RELEASE_APPROVED_WITH_BACKLOG

No referent, identity, coverage, rights or determinism gate could be defeated. Two defects
are recorded; neither corrupts the corpus, both should be fixed before the next release.

### Yajurveda — RELEASE_REJECTED

One blocking defect: **two records carry an inverted `ACCENTED_BOUNDARY_PROVENANCE`
attribution**, and one of them is published at `AssertionStatus.ACCEPTED`. Per-record
boundary provenance is the deliverable this release exists to provide — the config, the
builder docstring and `reports/layer_statistics.json` all present it as "the per-record
resolution the text-version registry asked for and left unimplemented". The aggregate
figures (1,942 / 33 / 36) are correct; the attribution behind them is not. Fix is small and
mechanical (defect **YV-1**).

---

## 2. Defect register

### YV-1 — BLOCKING. `ACCENTED_BOUNDARY_PROVENANCE` inverted for VSM 11.9 and VSM 11.28

**Where:** `scripts/build_yajurveda_canonical.py::boundary_provenance` (lines ~355–385).

**Shipped state:**

```
VG:YV:VSM:A11:V009  INFERRED_ACCENT_PRESENCE_FALLBACK  status=NEEDS_REVIEW   <- WRONG
VG:YV:VSM:A11:V028  SOURCE_DECLARED_ORDINAL_HEADER     status=ACCEPTED       <- WRONG
```

**Ground truth, read out of the pinned snapshot for अध्यायः ११:**

```
line 430   ORD   नवमी।                                       <- ordinal header IS present
line 431   ACC   देवस्य त्वा सवितुः प्रसवेऽश्विनोर्बाहुभ्यां पूष्णो हस्ताभ्याम् ।
line 432   ACC   ... ।। ९ ।।                                  <- VSM 11.9, boundary DECLARED

line 533         अष्टाविंशी                                   <- header printed WITHOUT its danda
line 534   ACC   देवस्य त्वा सवितुः प्रसवेऽश्विनोर्बाहुभ्यां पूष्णो हस्ताभ्याम् ।   <- ORDINAL_HEADER_ABSENT logged here
line 537   ACC   ... ।। २८ ।।                                 <- VSM 11.28, boundary INFERRED
```

`_ORDINAL_HEADER` requires a terminal danda (`^(?:तत्र\s+)?…\s*।\s*$`). Line 533 has none, so
the run beginning at line 534 fell back to accent presence and logged the adhyaya's only
`ORDINAL_HEADER_ABSENT` failure, with `line = stripped[:120]` — which for line 534 is the
63-character formula `देवस्य त्वा सवितुः प्रसवेऽश्विनोर्बाहुभ्यां पूष्णो हस्ताभ्याम् ।`.

`boundary_provenance` joins failures to records by `texts[i].startswith(failure.line)` with a
monotonic cursor. VSM 11.9 and VSM 11.28 both *open* with that formula (they diverge after it:
11.9 is 208 chars, 11.28 is 293). At this failure the cursor is still 0, so both candidates are
reachable and the greedy earliest pick lands on 11.9.

**The builder's own docstring asserts the property it does not have:**

> "…it resolves the case that a naive prefix match cannot: VSM 11.9 and 11.28 open with the
> same 120 characters, so an unordered match is ambiguous between them while an ordered one
> is not."

Ordering buys nothing when the cursor has not yet advanced past the earlier candidate. The
docstring names the exact pair the code gets wrong.

**Blast radius.** Exactly one mis-attribution in the corpus. Verified by replaying the cursor
walk over all 40 adhyayas: of the 33 attributed fallbacks, 32 have exactly one prefix candidate
and are correct; only the adhyaya-11 event has two. Aggregate counts are unaffected (one unit
is inference-derived either way), so `layer_statistics`, the four-number report and
`test_boundary_provenance_is_carried_per_record` (which only checks counts and statuses) all
stay green.

**Fix.** Stop joining by text prefix. Carry the run's start line number out of
`_parse_accented_layer` alongside each accented record (a parallel `list[int]`, or a field on
`StagingTextRecord`), and join `ParseFailure.line_number` to it exactly. That removes the
heuristic and makes the ambiguity impossible rather than resolved-by-luck. As an interim, among
the prefix candidates pick the one whose run start line is the smallest value `>= failure.line_number`.

**Regression test to add.** Assert `provenance[28] == INFERENCE_DERIVED` and
`provenance[9] == SOURCE_DECLARED` for adhyaya 11 by name, not by count.

---

### YV-2 — MEDIUM. A parallel layer may be relabelled `PRIMARY_TEXT` and the release then contradicts itself

**Where:** `scripts/build_yajurveda_canonical.py::assemble` — `allowed_roles` is enforced only
for the *leading* layer at the `select_primary_text_version` call site. Parallel layer roles come
from `registry_text_roles()` and are stamped verbatim with no check.

**Exploit (run, succeeded):** register `WIKISOURCE_SA.YV.VSM.UNACCENTED` as `PRIMARY_TEXT`. The
build completes and emits:

```
emitted roles: {('...ACCENTED','EXTRACTED_FROM_CONTAINER'): 1975,
                ('...UNACCENTED','PRIMARY_TEXT'): 1836}
report has_primary_text_layer: YES
YV-NO-PRIMARY-TEXT-LAYER QA issue still emitted:      1
NO_PRIMARY_TEXT_LAYER work-level assertion emitted:   1  (status ACCEPTED)
```

The release then ships 1,836 `PRIMARY_TEXT` rows *and* a QA issue reading "this work has no
layer registered PRIMARY_TEXT" *and* an `ACCEPTED` SourceAssertion with predicate
`NO_PRIMARY_TEXT_LAYER`. Both of those records are hardcoded in `_gap_issues` and
`_work_level_assertions`; neither is derived from the roles actually read.

**Fix.** Either raise when `TextRole.PRIMARY_TEXT in set(roles.values())`, or derive the QA issue
and the work-level assertion from the computed `has_primary_text_layer` so they cannot state
something the same release refutes. The first is preferable: this work's whole position is that
no layer of it is primary.

---

### YV-3 — MEDIUM. Overlapping layer ids silently swap the accented text for the unaccented text

**Where:** `scripts/build_yajurveda_canonical.py::assemble`

```python
by_version = {
    config.primary_text_version: accented,
    **{version: unaccented for version in config.parallel_text_versions},
}
```

If `parallel_text_versions` contains the primary id, the dict spread overwrites it.

**Exploit (run, succeeded):** add `WIKISOURCE_SA.YV.VSM.ACCENTED` to `parallel_text_versions`.
Result: 1,836 rows labelled `WIKISOURCE_SA.YV.VSM.ACCENTED` / `EXTRACTED_FROM_CONTAINER`
carrying the **unaccented** text, 139 addresses silently lose their accented layer, and
`text_versions` drops from 3,811 to 3,672. Referent bindings read `accented` directly, so the
drift gate stays green and nothing fires.

**Fix.** In `VsmReleaseConfig.load`, raise when
`config.primary_text_version in config.parallel_text_versions`. One line.

---

### YV-4 — BACKLOG. The build never verifies its own "second reading preserved in full" claim

**Where:** `assemble` derives `variant_bearing` from `parse.accented_collisions` and emits a QA
issue whose text asserts "every later reading is preserved in full as an
`EDITORIAL_INTERVENTION_SECOND_READING` assertion". Nothing checks that such an assertion exists,
is non-empty, or matches the collision count.

**Exploits (all run, all succeeded, all built clean):**

| Mutation | Result |
|---|---|
| Strip every `SECOND_READING` intervention | build clean; `variant_bearing_units = 1`, SECOND_READING assertions = **0**, QA issue still claims full preservation |
| Truncate `intervention.removed` to 20 chars + `...` | build clean, no warning |
| Empty `intervention.removed` | build clean, no warning |
| Clear `accented_collisions`, keep the intervention | build clean; `variant_bearing_units = 0` while a SECOND_READING assertion exists |

Exposure today is low: the adapter increments `seen[mantra]` and appends the intervention in the
same branch, so the two are structurally coupled, and
`test_vsm_16_37_keeps_both_printed_readings` verifies the *shipped* artifact. This is a missing
build gate, not a shipped error.

**Fix.** In `assemble`, for every `(mantra, n)` in `parse.accented_collisions` assert there are
exactly `n - 1` `SECOND_READING` interventions for that mantra, each with non-empty `removed`.

---

### YV-5 — BACKLOG. ~8 of the 33 "inference-derived" units have a printed header missing only its danda

Scanning the line immediately preceding each of the 36 `ORDINAL_HEADER_ABSENT` events: 8 are
preceded by a short, unaccented, danda-less Devanagari ordinal word that is plainly the printed
header the regex rejected.

```
adhyaya  4  line 287   षोडशी
adhyaya 11  line 534   अष्टाविंशी          <- the YV-1 case
adhyaya 11  line 752   षट्षष्टी
adhyaya 11  line 762   अष्टषष्टी
adhyaya 16  line 499   सप्तचत्वारिंशी
adhyaya 21  line 365   एकविंशी
adhyaya 34  line 481   एकचत्वारिंशी
adhyaya 34  line 486   द्विचत्वारिंशी
```

The 1,942 / 33 split is arithmetically real, and the error runs in the conservative direction
(it *understates* source-declared coverage). But `INFERRED_ACCENT_PRESENCE_FALLBACK` reads as
"the source did not declare this boundary", which is not what happened in these eight cases. The
evidence field should distinguish "no header printed" from "header printed without its terminal
danda", or the report should say the count is an upper bound.

---

### YV-6 — BACKLOG (cross-release report). `four_veda_corpus_completeness.json` reports the Yajurveda as having 1,975 mantras of primary Sanskrit coverage

`scripts/build_four_veda_completeness.py:114`

```python
primary_roles = {"PRIMARY_TEXT", "EXTRACTED_FROM_CONTAINER"}
sanskrit_primary = covered(
    texts, "passage_id", lambda row: str(row.get("text_role")) in primary_roles
)
```

For the one work whose entire release position is "there is no PRIMARY_TEXT layer here", the
four-Veda report prints `"sanskrit_primary_coverage": 1975`. The adjacent
`text_records_by_role` and `sanskrit_source_faithful_fallback_coverage` fields do disclose it, but
a downstream reader keying on the field *name* is misled. Rename to
`sanskrit_leading_layer_coverage`, or split into two fields.

---

### SV-1 — MEDIUM. `qa_issues.jsonl` ships 39 rows under 37 distinct `issue_id`

```
qa rows: 39   distinct issue_id: 37   dupes: 2
```

Both collisions trace to the corpus's one known marker anomaly: running number 1181 is printed
twice, so its two candidate occurrences share one `source_locator`,
`WS UTTARA.P5.R1.D2 RN1181`, and `stable_issue_id(check_id, subject=locator, message)` is
therefore not injective over occurrences.

```
20d9f7fc-fa03-57bf-a17e-9c2a23951ea7  REFERENT_UNRESOLVED    x2  rows NOT identical (notes differ)
297067dc-d2a6-5b06-bd97-5ff3d088847e  SOURCE_MARKER_ANOMALY  x2  rows byte-identical
```

The first pair is the one that matters: **two distinct findings are published under one
identifier**, so one of the 30 withheld occurrences is not individually addressable — against
this release's own stated principle that "a coverage gap with no queryable record is
indistinguishable from an oversight". The existing test
`test_every_withheld_occurrence_carries_a_reason` does not catch it because it only asserts that
each withheld locator appears somewhere in the issue set, and both occurrences share a locator.

The Yajurveda builder guards this with `_assert_unique("qa issue_id", …)`; the Samaveda builder
has no equivalent for any family.

**Fix.** Add an occurrence discriminator to the `stable_issue_id` subject —
`f"{row.source_locator}#{row.source_line_span[0]}"` is already on `AuditRow` and is unique — and
add an id-uniqueness assertion over every emitted family, mirroring `_assert_unique`.

**Not a referent hazard today:** `source_locator` *is* unique over the 1,844 **released**
occurrences (verified: 1,844 distinct locators, `duplicate_referents` empty), because both
RN1181 occurrences are withheld. If a future segmentation released them,
`gate_referents` would fire correctly.

---

### SV-2 — MEDIUM (governance). The Samaveda build ignores most of its own config

`data/builds/samaveda_arcika_v1.yaml` describes itself as "the auditable statement of intent",
and `manifest.json` pins its sha256. The builder validates it against `WorkBuildConfig` and then
reads only six attributes:

```
build_timestamp, dataset_id, output_location, reconciliation_policy_version,
release_version, sources
```

`primary_sanskrit` (text_version / artifact / role / selection_policy), `work_id`,
`section_level`, `mantra_level`, `text_selection_policy`, `parallel_sanskrit`,
`candidate_text_versions` and the per-source `role` / `source_artifact_id` / `parser_version`
are never compared with what the build does. `TEXT_VERSION_ID`, `ARTIFACT_ID`, `WORK_ID` and
`FORBIDDEN_TEXT_VERSION_IDS` are module constants.

**Exploits (each run against a copied config; all built successfully):**

| Doctored config | Outcome |
|---|---|
| `primary_sanskrit.text_version: GRETIL.SV.KAUTHUMA`, `artifact: GRETIL.SV.KAUTHUMA.TEI.2020` | built; emitted `WIKISOURCE_SA.SV.KAU.ARCIKA_MULA` |
| `work_id: VG:WORK:RV:SAK` | built; emitted `VG:WORK:SV:KAU` |
| `section_level: Mandala`, `mantra_level: Rc` | built; emitted Collection/Verse |
| `primary_sanskrit.role: COMPARISON_ONLY` | built; emitted `PRIMARY_TEXT` |
| removed the declared `GRETIL` corroboration source entry | built (the snapshot-on-disk check is not the config check) |
| re-pinned `snapshot_sha256` | **refused** — the one config field that is enforced |

The direction of harm is not that a forbidden layer gets used; the constants win, and they are
correct. The harm is that the manifest's `build_config_sha256` can pin a document that
contradicts the release, and a reviewer auditing the YAML would be auditing fiction. The
Yajurveda builder does not have this problem — it drives selection from the config and checks
`payload["work_id"] != WORK_ID`.

**Fix.** At the top of `build()`, assert config/constant agreement for
`work_id`, `primary_sanskrit.text_version`, `primary_sanskrit.artifact`,
`primary_sanskrit.role`, `section_level`, `mantra_level`, and that `config.sources` declares
both `WIKISOURCE_SA` and `GRETIL` with the roles the build assumes.

---

### SV-3 / shared — BACKLOG. `UNCHANGED_REFERENT` conflates "identical" with "re-encoded", and the release reports only the merged count

`_same_occurrence` compares `comparison_sha256`, `source_locator` and `source_verse_marker`. A
change to `text_sha256` alone is classified `UNCHANGED_REFERENT` with the re-encoding noted in
`ReferentDelta.detail` — but `referent_verdict_counts` collapses to verdict names, and
`samaveda_arcika_v1_coverage.json` publishes only
`{"UNCHANGED_REFERENT": 1844, …}`. A release that re-encoded every stored verse would report
identically to one that changed nothing.

Measured behaviour of the `SEARCH_NORMALIZED` comparison surface:

| change to the stored text | `text_sha256` moves | `comparison_sha256` moves | drift gate |
|---|---|---|---|
| extra whitespace | yes | no | silent |
| danda removed | yes | no | silent |
| udatta added | yes | no | silent |
| Devanagari digits appended | yes | no | silent |
| avagraha added | yes | yes | **fires** |
| one akshara changed | yes | yes | **fires** |

Folding accents and whitespace is the right call and is documented. The gap is reporting: add a
`re_encoded` count beside the verdict counts so a byte change to released text is visible in the
coverage report rather than only in a discarded in-memory `detail` string. (Current state:
0 re-encoded — baseline and release fingerprints are identical in all five fields for all
1,844 SV and all 1,975 YV rows.)

---

## 3. Attack log — Samaveda

### Attack 1 — referent drift

Two harnesses. The first mutates `AuditRow`s before assembly (exercising the whole build); the
second mutates `PassageReferentBinding`s after assembly, to isolate the drift gate from the
row/occurrence pairing guard that otherwise fires first.

| # | Attack | Result |
|---|---|---|
| 1a | change one released key's `source_locator` only | **REFUSED** — `ReleaseIntegrityError`, row/occurrence pairing diverged |
| 2a | same, applied to the binding only (reaches the gate) | **REFUSED** — `ReferentDriftError`, 1 key |
| 2b | change one key's `source_verse_marker` only | **REFUSED** — `ReferentDriftError`, 1 key |
| 1b / 2c | change `text_sha256` only, comparison surface unchanged | **passed** — classified `UNCHANGED_REFERENT` (documented; see SV-3) |
| 1b2 | key made to carry another verse's text (both digests move) | **REFUSED** — `ReferentDriftError`, 1 key |
| 1c | swap two keys' texts | **REFUSED** — `ReferentDriftError`, 2 keys |
| 1c2 / 2d | full referent swap (locator + marker + both digests) | **REFUSED** — pairing guard, then `ReferentDriftError`, 2 keys |
| 1d | retire a released key | **REFUSED** — `ReleaseIntegrityError`, sibling sequence no longer 1..n |
| 2f | drop one binding | **REFUSED** — "1844 released keys but 1843 referent bindings" |
| 1e | mint a key for a withheld occurrence | **REFUSED** — sibling sequence `[99]` not 1..1 |
| 1f / 2g | weld two keys onto one occurrence | **REFUSED** — pairing guard / `duplicate_referents` |
| 4c | hand a released key's identity to a withheld occurrence, retire the original (key set unchanged) | **REFUSED** — `ReferentDriftError` |

The last one is the interesting negative: it defeats the released-key-set equality check by
construction, and the drift gate catches it anyway.

**Migration licensing is genuinely scoped.** The committed ledger holds 144 rows, all
`recorded_by_run = SAMAVEDA_REFERENT_INTEGRITY_REPAIR`; `LICENSING_RUN` is
`FULL_SV_YV_AV_CANONICAL_INGESTION`, so `migrations_licensing_this_run = 0`. Not one of the 137
`KEY_REASSIGNED_BEFORE_FREEZE` rows can license a change here.

### Attack 2 — wrong TextVersion fallback

Only two Samaveda versions are registered: `WIKISOURCE_SA.SV.KAU.ARCIKA_MULA` (CC_BY_SA) and
`GRETIL.SV.KAUTHUMA` (PERMISSION_REQUIRED). Every route to the second was tried.

| Injected registry | Result |
|---|---|
| selected version removed | **REFUSED** — not registered; no fallback attempted |
| selected version renamed | **REFUSED** — same |
| GRETIL relabelled `PRIMARY_TEXT` + `CC_BY_SA` + given the correct `artifact_id`, real one removed | **REFUSED** — lookup is by id; GRETIL is never reached |
| GRETIL squatting on the selected id (artifact still GRETIL's) | **REFUSED** — pinned-artifact mismatch |
| selected version downgraded to `PERMISSION_REQUIRED` | **REFUSED** — rights |
| selected version's role set to `COMPARISON_ONLY` | **REFUSED** — role |

Fails closed on every path. It cannot bind rows to `GRETIL.SV.KAUTHUMA`.

### Attack 3 — collection ambiguity

`sv_mantra_identity` / `sv_container_identity` were attacked with every shape that could
reintroduce the contested ordinal or the old flattened five-slot address.

| Input | Result |
|---|---|
| `CHANDA` + `ardha` | refused — collection declares no ardha |
| `ARANYA` + `prapathaka` | refused |
| `MAHANAMNYA` + `dasati` | refused |
| `UTTARA` without `ardha` | refused — declared level is required |
| `CHANDA` + `ardha=0` (the migration hazard) | refused |
| `dasati=0`, `verse=0`, `prapathaka=-1` | refused — positive integers only |
| `dasati=100`, `verse=100`, `prapathaka=1000` | refused — exceeds the fixed key width |
| collection `"2"`, `"UTTARARCIKA"`, `"uttara"` | refused — not a `SamavedaCollection` |
| container with a gap (`ardha`+`dasati`, no `prapathaka`) | refused — outermost-first without gaps |

Over the shipped key space: every level slot is exactly 2 digits wide (`P`, `R`, `D`, `V`), the
file is in lexicographic order and lexicographic order equals coordinate order, and no key is
used as both a container and a mantra. No coordinate collision is constructible.

### Attack 4 — withheld-key mishandling

Shipped accounting, recomputed:

```
1,874 candidate occurrences = 1,844 released + 30 withheld
1,875 = 1,873 distinct printed markers + 2 unprinted [1179, 1315]
1,875 = 1,844 minted + 29 withheld printed verses + 2 unprinted
30 withheld occurrences over 29 distinct markers (1181 is printed twice)
withheld_by_reason: REFERENT_UNRESOLVED 9, STRUCTURAL_AMBIGUITY 21  (= 30)
released markers that are also withheld: none
released keys with no printed marker: 0
accented released occurrences: 0
```

The 29 withheld running numbers named in `qa_issues.jsonl` are exactly the 29 in
`samaveda_arcika_v1_coverage.json`. No withheld verse is silently released.

**Do the five equations constrain anything?** Analytically, `released_vs_traditional` and
`printed_vs_traditional` are near-redundant given `released_keys_vs_distinct_released_markers`
— which the code's own comment says. That fourth equation is the one carrying the weight, and it
is real. Empirically:

| Injected defect | Equations broken |
|---|---|
| a released key loses its printed marker | 3 |
| a released key carries marker 1900 (outside 1..1875) | 2 |
| two released keys share one printed marker | 2 |
| a withheld marker is also claimed by a released key | 2 |
| markers above 1870 blanked | 3 |
| a released row carries an unknown collection string | 1 (`minted_by_collection`) |

Every one raised `CoverageError` and published nothing. The equations are not decorative.

### Attack 5 — repeated-text digest false equivalence

Confirmed the premise: 1,651 distinct `comparison_sha256` over 1,844 keys; **192** equivalence
classes covering **385** keys; **174** of those classes (349 keys) share a byte-identical
`text_sha256` too. The figures in the `_same_occurrence` docstring are correct.

The decisive measurement: **zero** baseline rows share the triple
`(source_locator, source_verse_marker, comparison_sha256)`. Locators are unique (1,844 distinct)
and markers are unique (1,844 distinct, none null). The comparison key is therefore injective
over the corpus, and two keys in one digest class **cannot** swap referents undetected.

Demonstrated: swapping `source_locator` + `source_verse_marker` between two keys whose text is
byte-identical (`VG:SV:KAU:ARANYA:D01:V08` / `VG:SV:KAU:UTTARA:P01:R01:D08:V03`) — a swap that a
text-only comparator would see as two unchanged keys — raised `ReferentDriftError` on both.

---

## 4. Attack log — Yajurveda

### Attack 6 — accidental relabelling of `EXTRACTED_FROM_CONTAINER`

Roles are genuinely read from `data/registry/text_versions.yaml` and stamped verbatim; nothing
is hardcoded in the text-emission path. Shipped: `EXTRACTED_FROM_CONTAINER` 1,975,
`PARALLEL_TEXT` 1,836, `PRIMARY_TEXT` **0**.

| Attack | Result |
|---|---|
| registry relabels ACCENTED as `PRIMARY_TEXT` | **REFUSED** — `allowed_roles=(EXTRACTED_FROM_CONTAINER,)` |
| config promotes UNACCENTED to leading layer | **REFUSED** — role `PARALLEL_TEXT` not allowed |
| config names an unregistered layer | **REFUSED** — not registered, no fallback |
| config names a forbidden layer (`TITUS.YV.VSM.ACCENTED`) | **REFUSED** — by id |
| config pins the wrong artifact | **REFUSED** — artifact mismatch |
| registry relabels the **parallel** layer as `PRIMARY_TEXT` | **did not hold** → **YV-2** |
| config lists ACCENTED in both slots | **did not hold** → **YV-3** |

The accented layer cannot be emitted as `PRIMARY_TEXT`. The gate is real. Its perimeter is one
layer too small.

### Attack 7 — VSM 16.37 silent selection

Both printed readings survive in the shipped release, and the second is untruncated:

```
released ACCENTED   126 chars   नम॒: स्रुत्या॑य च॒ पथ्या॑य च॒ …   (srutyaya)
SECOND_READING      104 chars   नमः स॒त्याय च पथ्याय च …          (satyaya)
                    ends "।। ३७ ।।", carries the source's own terminal marker
                    status NEEDS_REVIEW, declared_status NEEDS_REVIEW
```

Passage identity: one passage `VG:YV:VSM:A16:V037`, one referent binding, one canonical citation
`VSM 16.37`. `variant_bearing_addresses == ["VSM 16.37"]`, one
`YV-VARIANT-READING-UNRESOLVED` QA issue. **No winner is chosen and the address is not split.**
Gate held on the artifact.

Four attempts to drop or damage the second reading at build level all built clean — see
**YV-4**. The shipped bytes are correct; the build has no gate proving they will stay correct.

### Attack 8 — metadata scope

Recomputed from the pinned rsi-index snapshot, independently of the builder:

```
2,240 assertions, all HAS_RISHI, all SINGLE_MANTRA scope
0 rows target a passage outside the corpus (0 off-corpus, 0 non-mantra targets)
0 index rows name an adhyaya outside 1..40
1,960 of 1,975 addresses covered; 276 addresses carry more than one rsi
1,795 from a printed range + 445 from a single label = 2,240
every metadata row has exactly one TRADITIONAL_METADATA_PROVENANCE twin (2,240 = 2,240)
```

**Ranges re-expanded independently.** I re-parsed all 346 range-bearing index lines from their
own `source_line` text with my own Devanagari numeral and range grammar, and compared the
resulting `(adhyaya, mantra)` sets against the adapter's: **0 mismatches**.

**Devata and Chandas are genuinely absent, not quietly invented.** Zero rows of either predicate
in `traditional_metadata.jsonl`; the only occurrence of those words anywhere in
`source_assertions.jsonl` is the single `TRADITIONAL_METADATA_SCOPE` assertion that names them as
*not asserted*, with the reason. Two `INFO` QA issues state the same. The Sarvanukramasutra's
samhita-wide `vivasvan` default is correctly **not** applied.

Honest gap, correctly reported: two index lines are unreadable and their assignments are lost —
`प्रस्कण्वः १५, ३१-३३, ३६ ।` (line 197) and `वसिष्ठः १४, १८, २०, ४४, ७०, ७१, ७६, ८८ ।` (line 293).
Both are continuation lines with no adhyaya token. Each gets a `YV-RISHI-INDEX-LINE-UNPARSED`
warning. The recomputed 2,240 is reported against the prior 2,106 projection as a difference of
+134, with the projection explicitly labelled a claim rather than truth.

### Attack 9 — boundary provenance honesty

**The arithmetic is real.** Re-derived over all 40 adhyayas from the pinned snapshots:

```
ORDINAL_HEADER_ABSENT events              36
attributed to a record (inference-derived) 33
unattributed (accented commentary prose)    3   <- reported, not forced onto a neighbour
36 == 33 + 3                            TRUE
1,942 + 33 == 1,975 addresses           TRUE
ACCENTED_BOUNDARY_PROVENANCE rows        1,975 over 1,975 distinct subjects
1,942 SOURCE_DECLARED   -> all ACCEPTED
   33 INFERRED          -> all NEEDS_REVIEW
```

The three unattributed fallbacks are genuine accented commentary runs (adhyaya 1 lines 243/270,
adhyaya 40 line 201). My cruder forward-scan heuristic wanted to force them onto VSM 1.1 and
40.40; the build correctly refuses to, and reports them as `YV-BOUNDARY-FALLBACK-UNATTRIBUTED`.
The build is the more conservative of the two.

**The per-record attribution is not.** Re-deriving each fallback's owning mantra by scanning
forward from the failure's source line to the next numbered terminal marker disagrees with the
build on exactly one record — see **YV-1**. Replaying the cursor walk confirms 32 of 33
attributions have a unique prefix candidate and are correct; the adhyaya-11 event has two
candidates and picks the wrong one.

Also see **YV-5**: 8 of the 36 events are a header printed without its danda, so "the source did
not declare this boundary" overstates the case in those eight.

---

## 5. Attack log — both releases

### Attack 10 — determinism

Each release was built twice into fresh temporary directories and every emitted byte compared,
then compared again against the committed tree.

```
SV determinism (two independent rebuilds)     BYTE-IDENTICAL
SV rebuild vs committed data/canonical/...    IDENTICAL
SV coverage report rebuild vs committed       IDENTICAL (3a38424b…)
YV determinism (two independent rebuilds)     BYTE-IDENTICAL   (includes reports/)
YV rebuild vs committed data/canonical/...    IDENTICAL
```

No clock is read on either path. `built_at` comes from the config in both cases
(`2026-09-07T00:00:00Z` for SV, `2026-09-07T00:00:00+05:30` for YV — the offset is written
literally in the YAML, not derived from the host timezone, so it is portable). The only
`datetime.now(UTC)` in `storage/manifest.py` is the `built_at or …` default, which neither
builder reaches. All temporary directories were removed.

### Attack 11 — cross-Veda collisions

Verified independently of `scripts/build_four_veda_completeness.py`, by reading all four
`passages.jsonl` directly:

```
                 RV      SV      YV     AV     total
passages      11,590   2,342   2,015    174   16,121
mantras       10,552   1,844   1,975    153   14,524

canonical_key collisions across works : 0
canonical_urn collisions across works : 0
entity_id     collisions across works : 0
same, across datasets rather than works: 0 / 0 / 0
intra-release duplicate keys           : 0 in every release
```

These match the committed `four_veda_corpus_completeness.json` exactly
(`passages_examined: 16121`, `clean: true`, `mantras_all_works: 14524`). The report's identity
audit is verified, not trusted. Its coverage vocabulary has one problem — **YV-6**.

### Attack 12 — orphan provenance

Every `SourceAssertion`, `TextVersion`, `Citation` and `TraditionalMetadataAssertion` was
resolved against the `sources.jsonl` / `source_artifacts.jsonl` the same release emits.

```
             assertions  unknown source_id  unknown artifact_id  empty locator
SV                   69                  0                    0              0
YV                4,304                  0                    0              0
RV               22,143                  0                    0              0
AV                  177                  0                    0              0
text_versions / citations / traditional_metadata: 0 bad rows in every release
```

### Attack 13 — passage integrity

```
                                              SV      YV
passages                                   2,342   2,015
distinct canonical_key / urn / entity_id    2,342   2,015
uuid5(NAMESPACE, canonical_urn) != entity_id    0       0
unresolvable parent_key                         0       0
sibling sets not contiguous 1..n                0       0
native_labels count != hierarchy levels         0       0
structural_path length != hierarchy levels      0       0
mantras with no referent binding                0       0
bindings whose key is not a released mantra     0       0
duplicate binding locators                      0       0
```

Roots are the 4 Samaveda collections and the 40 Yajurveda adhyayas, as expected. `native_labels`
names exactly the hierarchy levels present in each passage, per collection shape
(`MAHANAMNYA` correctly carries `[Collection, Verse]` with no zero-filled slots).

Family-level id uniqueness across the two releases:

```
                          SV                        YV
passages entity_id        2342/2342                 2015/2015
text_versions text_id     1844/1844                 3811/3811
citations citation_id     3688/3688                 1992/1992
source_assertions         69/69                     4304/4304
traditional_metadata      —                         2240/2240
qa_issues issue_id        39 rows / 37 distinct     25/25
```

The single non-unique family is Samaveda `qa_issues` — **SV-1**.

Out of scope but noted while walking all four releases: `atharvaveda_pilot_v1` has 7
non-contiguous sibling sets (e.g. kanda children numbered `[1,4,6,7,8,13,15,16,19,20]`, and
`VG:AV:SAU:K07` with a single child at sequence 6). That is a sample pilot, not a target of this
review, but it will fail the same `_assert_parent_integrity` rule the Samaveda enforces if the
pilot is ever promoted.

---

## 6. Verdicts

### `RELEASE_APPROVED_WITH_BACKLOG` — Samaveda `samaveda_arcika_v1`

Every referent, identity, coverage, rights, provenance and determinism gate resisted a working
exploit. The corpus is byte-reproducible, its 1,844 keys are the committed baseline's keys, its
1,844 bindings are fingerprint-identical to the baseline, the 30 withheld occurrences and 2
unprinted numbers are individually named with reasons from a closed vocabulary, and no key
denotes more than one occurrence or fewer than one.

Ship, and fix:

- **SV-1** (medium) — two colliding `qa_issue_id`s; one withheld occurrence is not individually
  addressable. Add an occurrence discriminator and an `_assert_unique` sweep.
- **SV-2** (medium) — the build ignores `primary_sanskrit`, `work_id` and the level vocabulary in
  its own config while pinning that config's digest in the manifest. Add config/constant
  agreement assertions.
- **SV-3** (backlog) — publish a `re_encoded` count beside the referent verdict counts.

### `RELEASE_REJECTED` — Yajurveda `yajurveda_vsm_v1`

Blocked on **YV-1**: `VG:YV:VSM:A11:V009` is published as `INFERRED_ACCENT_PRESENCE_FALLBACK` /
`NEEDS_REVIEW` when its ordinal header `नवमी।` is printed at line 430, and
`VG:YV:VSM:A11:V028` is published as `SOURCE_DECLARED_ORDINAL_HEADER` / **`ACCEPTED`** when its
header `अष्टाविंशी` at line 533 lacks the terminal danda the parser requires and its boundary
came from the accent-presence fallback. The attribution is inverted, one of the two is asserted
as settled, and `boundary_provenance`'s docstring claims to resolve exactly this pair. Everything
else about this release is in good order — the arithmetic reconciles, the rsi expansion is
independently reproducible to the row, VSM 16.37 keeps both readings untruncated under one
identity, and the accented layer cannot be relabelled `PRIMARY_TEXT`.

Fix **YV-1**, rebuild, re-pin `tests/fixtures/identity/vsm_referent_baseline.jsonl` if and only
if the referent fingerprints move (they should not — this is a provenance field, not a binding
field), add the named regression test, and this becomes an approval.

Also fix before or with it:

- **YV-2** (medium) — a parallel layer relabelled `PRIMARY_TEXT` builds clean and the release
  then ships records contradicting its own data.
- **YV-3** (medium) — overlapping layer ids silently swap accented text for unaccented text with
  no gate.
- **YV-4** (backlog) — the "second reading preserved in full" claim is unverified by the build.
- **YV-5** (backlog) — ~8 of 33 inference-derived units have a printed header missing only its
  danda; say so.
- **YV-6** (backlog, cross-release) — `four_veda_corpus_completeness.json` calls 1,975
  `EXTRACTED_FROM_CONTAINER` records "sanskrit_primary_coverage".

---

## 7. Late finding — the committed Samaveda release went stale during this review

**SV-4 — MEDIUM. `data/canonical/samaveda_arcika_v1/` no longer reproduces from the current registry.**

Attack 10 was run twice, at the start and at the end of the review. The first run reported
`SV rebuild vs committed: IDENTICAL`. The second reported:

```
SV determinism (two rebuilds)   BYTE-IDENTICAL
SV rebuild vs committed         DIFFERS
  manifest.json           rebuild=008bcc89f964  committed=3b42157f7d72
  source_artifacts.jsonl  rebuild=4d418d568e0a  committed=3ab0a72ca171
SV coverage report              DIFFERS  (c3d3fb08… vs committed 3a38424b…)
YV rebuild vs committed         IDENTICAL   (unaffected)
```

Cause: `data/registry/source_artifacts.yaml` was edited during the session — the
`provenance_notes` prose of `WIKISOURCE_SA.SV.KAU.SAMHITA.DEVANAGARI` (and of the recitation
artifact) was substantially extended. The Samaveda build copies the registry `SourceArtifact`
row verbatim into `source_artifacts.jsonl`, so the release embeds that prose.

Scoped precisely — **no corpus content moved**:

```
passages.jsonl          SAME     text_versions.jsonl     SAME
referent_bindings.jsonl SAME     citations.jsonl         SAME
qa_issues.jsonl         SAME     source_assertions.jsonl SAME
sources.jsonl           SAME     works.jsonl             SAME
source_artifacts.jsonl  DIFFERS  -> only field: provenance_notes
manifest generated_content_sha256: committed 57a81d6a…  rebuild 05b9b94c…
```

Two things follow.

1. **Action required before shipping:** rerun `scripts/build_samaveda_canonical.py` so the
   tracked release, its manifest and `data/builds/samaveda_arcika_v1_coverage.json` match the
   registry they quote. Everything above in this report was verified against the corpus content,
   which is unchanged, so re-verification is not needed — but the release as committed right now
   is not the release the builder produces.

2. **Gate gap:** nothing detects this. `manifest.build_config_sha256` pins only
   `data/builds/samaveda_arcika_v1.yaml`; the registry files the release copies rows out of
   (`works.yaml`, `sources.yaml`, `source_artifacts.yaml`, `text_versions.yaml`) are not pinned
   anywhere in the manifest. A release can therefore drift from the registry it embeds with every
   digest in the manifest still internally consistent. `CorpusManifest` already has a
   `build_config_hashes: dict[str, str]` field, presently `{}` in both releases — pinning the four
   registry files there, in both builders, closes it for the cost of four `sha256` calls.
