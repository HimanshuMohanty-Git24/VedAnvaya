# Four-Veda cross-source comparison framework

Owner: Agent F. Scope: verification of `src/vedagraph/compare/` against non-Rigvedic
hierarchies, the category vocabulary mapping, and the real classification distributions.

Every distribution in this document is a measured run over real records. Where a comparison
could not be run it says NOT RUN and why.

## 1. Neither source is ever overwritten — confirmed by reading the code

The comparison layer emits `TextComparison` records and nothing else. Confirmed by
inspection of all three modules:

- `compare/text.py` — `classify()` returns a tuple; `compare_readings()` and
  `compare_missing()` construct and return a `TextComparison`. No assignment to any input,
  no file write.
- `compare/run.py` — reads pinned snapshots, verifies each snapshot's SHA-256 against the
  config and **raises** on mismatch (`_verify_inputs`), then returns a `ComparisonResult`.
- `compare/report.py` — the only writer, and it writes a Markdown report to its own path.

`TextComparison` has no field that could carry a corrected reading: it carries the two
`version_id`s, a category, a classification basis, similarity and difference counts. There is
no "preferred reading" and no "resolved text". A comparison can therefore never be mistaken
for an edition.

Corollary worth stating: `LEXICAL_VARIANT` is never assigned automatically. It is reserved
for human review, so the comparator cannot silently assert a substantive textual claim.

## 2. Category vocabulary mapping

The session brief asks for EXACT / ACCENT_ONLY / ORTHOGRAPHIC / SANDHI / TOKENIZATION /
STRUCTURAL / SUBSTANTIVE / UNCLASSIFIED. `TextComparisonCategory` already exists in
`models/enums.py`. Mapping the brief onto the existing enum rather than churning a shared
contract:

| Brief vocabulary | Existing enum member | Notes |
| --- | --- | --- |
| EXACT | `IDENTICAL` | byte-identical source text |
| — | `UNICODE_ONLY` | finer than the brief: equal after NFC alone. Kept; it distinguishes an encoding difference from an orthographic one |
| ACCENT_ONLY | `ACCENT_ONLY` | equal once tone marks are removed |
| ORTHOGRAPHIC | `ORTHOGRAPHIC` | also absorbs the transcription-fold rung (IAST vs ISO 15919) |
| SANDHI | `SANDHI_OR_SEGMENTATION` | identical letter sequence, different word division |
| TOKENIZATION | `SANDHI_OR_SEGMENTATION` (partly) and `STRUCTURAL_VARIANT` (partly) | **genuine partial gap — see §2.1** |
| STRUCTURAL | `STRUCTURAL_VARIANT` | same tokens, different order |
| SUBSTANTIVE | `LEXICAL_VARIANT` | never auto-assigned; human review only |
| UNCLASSIFIED | `UNCLASSIFIED` | no deterministic rule applied |
| — | `METRICAL_RESTORATION` | follows *declared* provenance, not analysis |
| — | `MISSING` | a version has no reading for an aligned passage |

### 2.1 The one genuine gap: TOKENIZATION

The brief's TOKENIZATION is not cleanly representable. Today a pure word-boundary difference
lands in `SANDHI_OR_SEGMENTATION` (via the "identical letter sequence, different
segmentation" rung), which conflates two different phenomena: *sandhi* is a phonological
change at a junction, whereas *tokenization* is an editor's whitespace or avagraha choice
with no phonological content.

Agent C's Yajurveda data is a concrete instance: the unaccented layer word-splits with
avagraha (`कर्मणऽ आ प्यायध्वम्`) where the accented layer reads sandhi-joined
(`कर्म॑ण॒ आप्या॑यध्वम्`). Those are arguably two categories, not one.

**Not requested from Agent A.** Reason: the enum is a shared contract and the distinction is
not currently *derivable* — separating tokenization from sandhi requires knowing whether the
junction changed phonologically, which is exactly the philological judgement the comparator
refuses to make. Adding a member that nothing can populate deterministically would create a
category that is either always empty or filled by guessing. Recorded as a documented
limitation instead. If a deterministic rule is found later, `TOKENIZATION` is the right
addition and the mapping above is where it belongs.

## 3. Does `compare/` work for a 2-level and a variable-depth hierarchy?

Split answer, because the layer has two halves with very different portability.

### 3.1 `compare/text.py` — work-agnostic. VERIFIED.

`classify()`, `compare_readings()` and `compare_missing()` operate on strings plus a
`passage_key` and a citation label. Nothing in them reads `hierarchy`, assumes a depth, or
mentions a Veda. They were run unmodified against:

- Rigveda, 3 levels — 10,552 mantras (§4.1)
- Yajurveda, 2 levels — 135 comparisons by Agent C, and 153 records in the pilot
- Samaveda, 5 levels with absent middles — 29 comparisons by Agent B
- Atharvaveda, 3 levels — 153 comparisons in the pilot

All four produced `TextComparison` records with no modification to the comparator. **The
classification engine generalises.**

### 3.2 `compare/run.py` — Rigveda-only. NOT PORTABLE. Defect recorded.

`TextComparisonConfig` and `load_readings()` are hard-bound to the Rigveda:

| Location | Rigveda assumption |
| --- | --- |
| `TextComparisonConfig.mandala: int = Field(ge=1)` | a required scalar `mandala` field |
| `TextComparisonConfig.selected_suktas: list[int]` | a required `sukta` list |
| `load_readings()` | returns `{(sukta, mantra): …}` — a fixed 2-tuple key |
| `load_readings()` | `record.hierarchy["mandala"]`, `["sukta"]`, `["mantra"]` unguarded |
| `run_comparison()` | `rv_mantra_key(config.mandala, sukta, mantra)` |
| `run_comparison()` | citation hardcoded as `f"RV {mandala}.{sukta}.{mantra}"` |
| `load_readings()` | dispatches only on `GRETIL` and `VEDAWEB`, raising for anything else |

A 2-level Vajasaneyi config cannot be expressed at all: there is no `sukta` to select and
`mandala` is required. A 5-level Samaveda config cannot be expressed either. This is why
**all three new-Veda comparisons were produced by the owning agents' own runners** calling
`compare/text.py` directly, rather than through `vedagraph text compare-sample`.

Not fixed here: `compare/run.py` is not in this agent's exclusive ownership, and generalising
its config model is a contract change (it would need a work-agnostic address tuple and a
pluggable reader registry). Recorded as the principal portability defect in the comparison
layer.

## 4. Real classification distributions

### 4.1 Rigveda — measured here, all 10,552 mantras

`GRETIL.RV.AUFRECHT` vs `VEDAWEB.AUFRECHT`, both readings present for every mantra:

| Category | Count | Share |
| --- | --- | --- |
| `ACCENT_ONLY` | 9,746 | 92.4% |
| `UNCLASSIFIED` | 771 | 7.3% |
| `SANDHI_OR_SEGMENTATION` | 35 | 0.3% |
| **Total** | **10,552** | |

`ACCENT_ONLY` dominating is the expected and correct result: the two editions use
incompatible accent notations (GRETIL marks anudātta U+0331 and svarita U+030D; VedaWeb marks
udātta U+0301), so accent-stripped comparison is the only sound basis for judging identity.
92.4% of the Rigveda is letter-for-letter identical across the two editions.

This distribution is unchanged by every normalization change made in this session — verified
after each one, 0 of 10,552 mantras shifting category.

### 4.2 Yajurveda — 2 levels, measured by Agent C

Accented layer vs unaccented layer, 136 aligned pairs. Agent C's original run exposed a
defect in the normalization layer rather than a property of the texts, so both the before and
after are recorded:

| Category | Before Devanagari folding | After |
| --- | --- | --- |
| `UNCLASSIFIED` | 132 | **116** |
| `SANDHI_OR_SEGMENTATION` | 2 | **13** |
| `ACCENT_ONLY` | 1 | **6** |
| `MISSING` | 1 | 1 |

Both layers are Devanagari, and at the time of Agent C's run **0 of the 11 fold rules touched
Devanagari at all**, so there was no normalization available to bring them together. The two
causes were verified independently and are now fixed
(`FOUR_VEDA_NORMALIZATION_POLICY.md` §8): the same nasal encoded as U+A8F3 versus
U+1CEA+U+0902+U+1CED, and visarga typed as ASCII colon U+003A. 16 pairs became classifiable.

The remaining 116 are **not** a folding gap, and this was characterised rather than assumed:
114 of 116 differ in token count on the search surface, 46 of 116 carry avagraha (U+093D) on
one side only, and inspection shows genuine sandhi divergence (VSM 1.1 reads `त्वोर्जे` in one
layer against `त्वा ऊर्जे` in the other). The comparator declining these is correct
behaviour.

### 4.3 Samaveda — 5 levels with absent middles, measured by Agent B

GRETIL IAST vs Sanskrit Wikisource Devanagari, 29 aligned verses, mean similarity 0.9626:

| Category | Count |
| --- | --- |
| `ORTHOGRAPHIC` | 17 |
| `UNCLASSIFIED` | 11 |
| `SANDHI_OR_SEGMENTATION` | 1 |

This is a **cross-script** comparison. `classify()` refuses cross-script input outright — it
returns `UNCLASSIFIED` with the basis "the two readings are in different scripts; a reviewed
transliteration step must run before these versions can be compared as strings". Agent B
therefore transliterated the Devanagari side with `DevanagariToIAST` and declared the result
`COMPARISON_ONLY`. That is the correct discipline: the derived transliteration is used for
comparison and never stored as canonical text.

Agent B's observation on the 11 UNCLASSIFIED is worth recording and is only partly a
comparator artifact:
- Several are pure daṇḍa-notation differences (Wikisource `|`, GRETIL `.`). Both are in
  `SEPARATOR_MARKS` and collapse to a space, so these *should* be reachable by the existing
  `ORTHOGRAPHIC` rung; that they are not suggests the ladder short-circuits earlier on
  transliterated input. Worth investigation; not investigated here.
- At least two (running numbers 1 and 2) are a **genuine textual finding**: GRETIL is
  provably corrupt there, its mislabel moving a pāda between verses, while Wikisource is
  correct. A future rung must not smooth these away.

Note also that §6.1 of the normalization policy — the udātta U+032D fix — directly improves
cross-script comparison of accented Devanagari, since an accented and an unaccented reading
now compare equal after transliteration where before they did not. Agent B's Samaveda source
carries no tone marks, so that fix does not change these 29 numbers.

### 4.4 Atharvaveda — 3 levels, measured by Agent D

Accented GRETIL vs unaccented GRETIL, 153 comparisons: **`ACCENT_ONLY` 153 / 153.**

The cleanest result of the four, and for a structural reason: both sides are the same
notation from the same publisher, so the fold is symmetric and the only difference is the
accents. This is also the case that confirms the lateral-fold lossiness documented in
policy §9 does *not* corrupt Atharvaveda comparison.

### 4.5 Summary

| Veda | Levels | Comparisons | Dominant category | Comparator verdict |
| --- | --- | --- | --- | --- |
| Rigveda | 3 | 10,552 | `ACCENT_ONLY` 92.4% | works |
| Yajurveda | 2 | 135 | `UNCLASSIFIED` 97.8% | works, but blocked by the Latin-only fold |
| Samaveda | 5 (variable) | 29 | `ORTHOGRAPHIC` 58.6% | works, via a declared transliteration step |
| Atharvaveda | 3 | 153 | `ACCENT_ONLY` 100% | works |

## 5. Cross-script handling: the rule that is actually enforced

`classify()` compares `_has_devanagari(left)` against `_has_devanagari(right)` and returns
`UNCLASSIFIED` when they differ, with an explicit basis string demanding a reviewed
transliteration step first. This is correct and is the single most important safety property
of the layer: it makes a script mismatch a *refusal* rather than a similarity score close to
zero, which a downstream consumer could have mistaken for a textual difference.

The consequence for the three new Vedas — all Devanagari-primary — is that any comparison
against a Latin edition requires a declared transliteration step, and per policy §6 that
transliteration is incomplete for Vedic Extensions. Both facts must travel with any
cross-script distribution.

## 6. Open defects in the comparison layer

1. **`compare/run.py` is Rigveda-only** (§3.2). Blocks `vedagraph text compare-sample` for
   three Vedas. Needs a work-agnostic address tuple and a pluggable reader registry.
2. ~~The fold is Latin-only~~ — **FIXED** (policy §8). Devanagari anusvāra folding and a
   script-gated ASCII-colon-for-visarga step took Yajurveda from 132 to 116 UNCLASSIFIED with
   zero effect on the other three corpora. **New open item:** the avagraha (U+093D) asymmetry
   behind 46 of the 116 residual cases — avagraha is a real orthographic sign, so folding it
   away is a philological judgement and was not made.
3. **The ladder may short-circuit on transliterated input** (§4.3). Agent B's daṇḍa cases
   look reachable by an existing rung. Unverified; worth a bounded investigation.
4. **`TOKENIZATION` has no deterministic rule** (§2.1). Documented, not added.

## 7. Reproducing the Rigveda distribution

```
PYTHONIOENCODING=utf-8 ./.venv/Scripts/python.exe <fold_impact probe>
#   loads data/canonical/rigveda_full_v1/{passages,text_versions}.jsonl
#   runs compare.text.classify() over both text_version_ids per mantra
#   -> ACCENT_ONLY 9746 / SANDHI_OR_SEGMENTATION 35 / UNCLASSIFIED 771, total 10552
```

The per-Veda pilot distributions are reproduced by each owning agent's build script; the
committed `text_comparisons.jsonl` in each pilot directory is the artifact of record.
