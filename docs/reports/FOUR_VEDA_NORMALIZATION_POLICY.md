# Four-Veda normalization and Unicode policy

Owner: Agent F (corpus QA / normalization). Scope: `src/vedagraph/normalize/unicode.py`,
`src/vedagraph/transliteration/*`.

Every number in this document was produced by running the code against real source bytes or
real canonical records. Nothing here is inferred from the shape of the code. Where a claim
could not be measured it is marked NOT MEASURED rather than asserted.

## 1. The governing rule

**Stored source text is never replaced by a normalized form.** Normalization produces
*derived surfaces*. `TextVersion.text_original` and `TextVersion.text_nfc` are separate
fields precisely so that the original is recoverable, and `ComparisonForm.SOURCE_ORIGINAL`
is the identity function — verified by test, not by inspection.

Consequences that follow from this and are enforced:

- A comparison surface may be lossy. Stored text may not.
- Accent stripping, editorial-mark stripping, transcription folding and case folding all
  exist *only* on derived surfaces.
- `DevanagariToIAST` output is derived data. It is never canonical text.

## 2. What was measured, and against what

Real source bytes, not invented strings:

| Artifact | Bytes | Script | Vedic tone marks present |
| --- | --- | --- | --- |
| `avs_acu.htm` (GRETIL Atharvaveda, accented) | 1,114,524 | Latin | U+0301 ×87,065, U+0300 ×1,293, U+0325 ×5,163 |
| `avs___u.htm` (GRETIL Atharvaveda, unaccented) | 1,024,198 | Latin | none (U+0301 ×18,190 is the letter ś) |
| `sv_plain.txt` (Samaveda) | 254,124 | Latin | none |
| `sv_tei.xml` (Samaveda TEI) | 272,261 | Latin | none |
| `titus_vs001.htm` (Yajurveda TITUS) | 82,539 | Latin | U+0301 ×589, U+0300 ×19 |
| `weber.txt` (Yajurveda Weber) | 3,226,953 | Devanagari | U+0951 ×385, U+0952 ×238 |
| `data/raw/wikisource_sa_vsm/.../bc41fb48….php` (VSM adhyāya 1) | 286,651 | Devanagari | U+0951 ×371, U+0952 ×474, U+1CEA ×54, U+1CED ×54, U+A8F3 ×33 |
| `data/raw/wikisource_sa_vsm/.../32b097a0….php` (VSM adhyāya 16) | 212,778 | Devanagari | U+0951 ×574, U+0952 ×785, U+1CEA ×32, U+1CED ×32, U+A8F3 ×25 |

Real canonical records: 21,936 `TextVersion` rows across all four builds
(Rigveda 21,104 · Atharvaveda 459 · Yajurveda 271 · Samaveda 102).

## 3. NFC policy and the idempotency proof

Policy: `text_nfc` is exactly `unicodedata.normalize("NFC", text_original)`. Nothing else is
applied — no case change, no mark removal, no whitespace change.

Measured over all 21,936 canonical text records:

```
Rigveda      records= 21104  text_nfc not NFC-stable=0  normalization not idempotent=0  text_nfc != NFC(text_original)=0
Samaveda     records=   102  text_nfc not NFC-stable=0  normalization not idempotent=0  text_nfc != NFC(text_original)=0
Yajurveda    records=   271  text_nfc not NFC-stable=0  normalization not idempotent=0  text_nfc != NFC(text_original)=0
Atharvaveda  records=   459  text_nfc not NFC-stable=0  normalization not idempotent=0  text_nfc != NFC(text_original)=0
```

Idempotency over every derived surface, per record, all four builds:

```
Rigveda      records= 21104 non_idempotent=0
Samaveda     records=   102 non_idempotent=0
Yajurveda    records=   271 non_idempotent=0
Atharvaveda  records=   459 non_idempotent=0
```

Whether NFC is a no-op depends on the artifact and is worth recording, because a no-op NFC
is not evidence that normalization is unnecessary — it is evidence that the artifact was
already normalized:

```
avs_acu.htm            NFC changes text: True   NFC idempotent: True
avs___u.htm            NFC changes text: False  NFC idempotent: True
sv_plain.txt           NFC changes text: False  NFC idempotent: True
weber.txt              NFC changes text: True   NFC idempotent: True
VSM adhyaya 1 and 16   NFC changes text: False  NFC idempotent: True
```

## 4. Determinism across runs and processes

`data/qa/four_veda_normalization_determinism_run1.tsv` and `…run2.tsv` are the SHA-256 of
every derived surface for 9 inputs × 11 normalization stages, produced by two separate OS
processes (pids 22180 and 11716) with `PYTHONHASHSEED` deliberately **unset**, so that any
accidental dependence on set or dict iteration order would show up as a differing digest.

```
diff run1 run2 (excluding the pid banner)  ->  no differences
```

The two files are committed as the reproducibility artifact. Re-running the probe on an
unchanged tree must reproduce them byte for byte.

## 5. How accents are preserved

`strip_vedic_accents` removes tone marks only. Measured on real bytes, the count of
non-combining letters is unchanged by stripping:

| Artifact | Letters before | Letters after |
| --- | --- | --- |
| `avs_acu.htm` | 580,872 | 580,872 |
| `avs___u.htm` | 580,564 | 580,564 |
| `sv_plain.txt` | 140,094 | 140,094 |
| `weber.txt` | 549,566 | 549,566 |
| VSM adhyāya 1 | 51,360 | 51,360 |
| VSM adhyāya 16 | 37,957 | 37,957 |

### 5.1 The U+0301 disambiguation is load-bearing and it works

U+0301 is both the VedaWeb udātta *and* the second component of `ś`. `_strip_cluster`
resolves this without guessing: on a vowel base a tone-set mark is an accent; on a consonant
base carrying exactly one such mark, the mark is the letter.

The two GRETIL Atharvaveda artifacts are a natural controlled experiment, since they are the
same text with and without accents:

```
avs_acu.htm  (accented)    has_vedic_accents -> True    (U+0301 ×87,065, U+0300 ×1,293)
avs___u.htm  (unaccented)  has_vedic_accents -> False   (U+0301 ×18,190, all of them ś)
```

The same code returns True for the accented file and False for the unaccented one. Agent B
independently confirmed the same result on the Samaveda artifact's 1,751 `ś` characters.

### 5.2 Vedic Extensions: category decides, and that is correct

`VEDIC_ACCENT_CODEPOINTS` spans U+1CD0–U+1CFF wholesale, but `strip_vedic_accents` only ever
removes *combining* characters. Measured on VSM adhyāya 1:

```
U+1CEA VEDIC ANUSVARA BAHIRGOMUKHA  category=Lo (letter)   54 of 54 SURVIVE stripping
U+1CED VEDIC SIGN TIRYAK            category=Mn (combining) 54 -> 0, stripped
```

This is the right outcome: U+1CEA is a letter and removing it would delete text, not an
accent. It is asserted by test so a future refactor cannot quietly start deleting it.

### 5.3 Accent-preservation gate (G07) is gated on declaration, not on equality

The obvious rule — "if `text_original == text_nfc` for accented text, accents were stripped"
— is wrong, and Agents B and D both flagged it before it was ever run. For an unaccented
source `text_original == text_nfc` is *faithful preservation*. G07 therefore keys on
`TextVersion.accented`, and asks whether a record that **declares** accents actually carries
tone marks. Results: Rigveda 21,104/21,104 declared-accented and 0 lost; Atharvaveda 153
declared and 0 lost; Yajurveda 135 declared and 0 lost; Samaveda 0 declared, so the gate
reports NOT_APPLICABLE rather than a vacuous pass.

## 6. IAST derivation: when it is deterministic and when it must be omitted

`DevanagariToIAST` is deterministic — every mapping below reproduced identically on repeat
calls. What it does with the svara marks, measured:

| Devanagari | Emits | In the tone-mark set? |
| --- | --- | --- |
| U+0951 udātta | U+032D combining circumflex below | yes, **after the fix in §6.1** |
| U+0952 anudātta | U+0331 combining macron below | yes |
| U+0953, U+0954 | passed through unchanged | yes (U+0951–U+0954 range) |
| U+1CEA, U+1CED | passed through unchanged, **not transliterated** | U+1CED yes, U+1CEA is a letter |
| U+A8F3 candrabindu virāma | `m` + U+0310 | no — and correctly not, it is a nasal, not a tone |

**Omit rather than guess.** U+1CEA and U+1CED pass through as raw Devanagari inside an
otherwise-Latin string. That output is *not* IAST and must not be labelled as such. A
`transliteration_scheme` of `IAST` should be withheld for any text containing Vedic
Extensions characters until the transliterator covers them.

### 6.1 DEFECT FOUND AND FIXED: udātta was invisible after transliteration

`indic-transliteration` renders udātta as U+032D, which was **absent** from
`VEDIC_ACCENT_CODEPOINTS` while anudātta's U+0331 was present. Measured consequences before
the fix:

```
अग्निम॑ -> 'agnima' + U+032D    has_vedic_accents = False   <-- denied an accent that was there
अग्निम॒ -> 'agnima' + U+0331    has_vedic_accents = True

accented vs unaccented, same mantra, compared on ACCENT_STRIPPED_COMPARISON:
   as Devanagari       -> equal      (correct)
   after transliteration -> NOT equal  (wrong)
```

This mattered specifically because Yajurveda, Samaveda and Atharvaveda are all
Devanagari-primary, and a false `accented=False` would have been written into records.

Fix: U+032D added to the tone-mark set. **Safety measured before landing** — 0 of the 21,936
canonical text records contain U+032D, so the change cannot alter stored data or any existing
comparison; and the Rigveda comparison distribution is unchanged (0 of 10,552 mantras shift
category). Both accents now behave alike, and both are pinned by test.

### 6.2 DEFECT FOUND AND FIXED: the search surface was not idempotent

`fold_transcription` ran *before* `casefold()`, but every spelling in
`TRANSCRIPTION_EQUIVALENCES` is lower case. An upper-case variant therefore survived the
fold and folded only if the surface was normalized a second time:

```
before: SEARCH_NORMALIZED and profile_SEARCH  ->  idempotent = False on both GRETIL Atharvaveda artifacts
        'R̥'  folds only on the second pass, so 'R̥' and 'r̥' compared UNEQUAL on the search surface
after : idempotent = True on all 9 probe inputs x 11 stages
```

Fix: casefold before folding. **Safety measured before landing** — the surface changes for
**0 of 21,936** canonical text records (only 6 records contain any upper-case character at
all, all Samaveda, and none of them change).

Residual, documented and not fixed: the `("cch", "ch")` rule is a plain `str.replace` and so
is non-idempotent on a run of three or more `c` (`'ccch' -> 'cch' -> 'ch'`). No canonical
record contains `ccch`; this is recorded rather than repaired because repairing it means
changing a fold that the Rigveda comparison depends on.

## 7. Cross-script support: what the layer actually does today

Verified by reading and running the code, not assumed.

| Input scheme | Supported? | Evidence |
| --- | --- | --- |
| Devanagari → IAST | Yes, deterministic | `DevanagariToIAST`, backed by `indic-transliteration`; svara handling per §6 |
| IAST (Latin) input | Accepted as text; folded against ISO 15919 | `TRANSCRIPTION_EQUIVALENCES`, 11 rules |
| ISO 15919 (Latin) input | Accepted; folded against IAST | same table |
| Harvard-Kyoto | **NOT SUPPORTED** | no HK scheme referenced anywhere in `normalize/` or `transliteration/` |
| SLP1 | **NOT SUPPORTED** | no SLP1 scheme referenced; `indic-transliteration` could do it but nothing wires it |
| Devanagari ↔ Devanagari folding | **Supported for anusvāra and the visarga colon** — see §8 | 5 Devanagari rules added to the fold, plus a script-gated source-convention step |

There is exactly one `Transliterator` implementation. The `Transliterator` protocol
(`source_script`, `target_scheme`, `transliterate`) is the seam where HK and SLP1 would be
added; neither exists today and neither should be claimed.

## 8. FIXED: the fold was Latin-only; Devanagari folding now implemented

Reported by Agent C, verified directly here. `TRANSCRIPTION_EQUIVALENCES` contains **0 rules
touching Devanagari out of 11**, so Devanagari-versus-Devanagari comparison has no
normalization to work with. Agent C's Yajurveda cross-layer run: **UNCLASSIFIED 132,
SANDHI_OR_SEGMENTATION 2, ACCENT_ONLY 1** out of 135. The comparator is behaving correctly —
it declines rather than guesses — but the causes are mechanical, not philological:

1. **The same nasal, two encodings.** Unaccented layer writes U+A8F3 (×76); accented layer
   writes U+1CEA + U+0902 + U+1CED (×70). Verified here: neither folds onto the other, and
   because U+1CEA is category `Lo` it survives accent stripping, so the two can never match.
   ```
   U+A8F3                fold -> U+A8F3           (unchanged)
   U+1CEA U+0902 U+1CED  fold -> U+1CEA U+0902     (only U+1CED stripped)
   equal on SEARCH surface? False
   ```
2. **Visarga typed as ASCII colon.** The accented layer types visarga as U+003A — 82
   occurrences in VSM adhyāya 1, 115 in adhyāya 16, ~1,538 work-wide per Agent C. `:` is in
   `SEPARATOR_MARKS`, so it becomes a space, while a real `ः` U+0903 survives. Verified: the
   two can never compare equal.
3. Genuine sandhi/segmentation differences on top of (1) and (2), which are legitimately
   `SANDHI_OR_SEGMENTATION`.

Agent C also documented **four** mutually incompatible encodings for the same VSM nasal across
sources (TITUS U+0310, Vedic Heritage U+1CEA, Sanskrit Library SLP1 `M` with the distinction
lost, DCS absent).

### 8.1 What was implemented

Both mechanisms are now folded. Unlike the lateral series in §9, these are **safe** to fold:
every spelling below denotes the anusvāra in Devanagari and no source uses any of them for a
different sound, so the notation-dependence that made §9 unfixable does not arise.

**The nasal** — five rules appended to `TRANSCRIPTION_EQUIVALENCES`, longest first, all onto
the same `_ANUSVARA` sentinel the Latin spellings (`ṁ`, `ṃ`, `m̐`) already use, so a Devanagari
and a Latin reading of one nasal are now comparable:

```
U+1CEA U+0902 U+1CED  ->  anusvara sentinel      (accent-preserving arrival form)
U+1CEA U+0902         ->  anusvara sentinel      (accent-stripped arrival form)
U+1CEA                ->  anusvara sentinel
U+A8F3                ->  anusvara sentinel
U+0902                ->  anusvara sentinel
```

Two arrival forms are needed because U+1CED is a combining mark inside the Vedic Extensions
range and is therefore already removed by `strip_vedic_accents`, while U+1CEA is category `Lo`
and survives (§5.2). So the accented spelling reaches the fold in full on an accent-preserving
surface and as `U+1CEA U+0902` on an accent-stripped one.

**ASCII colon for visarga — a source convention, recorded as such.** The accented Vājasaneyi
layer *types visarga as an ASCII colon*: 124 occurrences against 321 genuine U+0903 in the
Yajurveda pilot, while the unaccented layer uses U+0903 throughout. This is an editorial
convention of the source, not a typo, and it requires explicit folding.

It **cannot** be a `TRANSCRIPTION_EQUIVALENCES` rule, because `:` is in `SEPARATOR_MARKS` and
`strip_editorial_marks` turns it into a space before `fold_transcription` ever sees it. It also
must not be applied globally — in a Latin text a colon is ordinary punctuation. It is therefore
implemented as `fold_devanagari_source_conventions()`, **gated on the text actually containing
Devanagari**, and applied after NFC but before editorial stripping.

### 8.2 Safety, measured before landing

```
canonical text records containing Devanagari:   RV 0 of 21,104   SV 0 of 102
                                                AV 0 of 459      YV 271 of 271
canonical text records containing ASCII colon:  RV 0   SV 0   AV 0   YV 124 occurrences
Rigveda comparison distribution after the change: ACCENT_ONLY 9,746 / SANDHI 35 /
                                                  UNCLASSIFIED 771  -- unchanged, 0 of 10,552 shift
```

Only Yajurveda has any Devanagari at all, and the three Latin corpora contain no ASCII colon in
their text, so the change is a **no-op by construction** for every non-Devanagari record.

`SOURCE_ORIGINAL` and `NFC` return before the convention fold, verified:

```
comparison_form('क:', SOURCE_ORIGINAL) -> 'क:'      unchanged
comparison_form('क:', NFC)             -> 'क:'      unchanged
comparison_form('a: b', SEARCH)        -> 'a b'     Latin colon still editorial, not visarga
```

Stored `text_original` is untouched. This is a derived fold, as required.

### 8.3 Measured effect on Yajurveda

Re-running the cross-layer comparison over the pilot's 136 aligned pairs, before and after:

| Category | Before | After |
| --- | --- | --- |
| `UNCLASSIFIED` | 132 | **116** |
| `SANDHI_OR_SEGMENTATION` | 2 | **13** |
| `ACCENT_ONLY` | 1 | **6** |
| `MISSING` | 1 | 1 |

16 pairs became classifiable. This is a real improvement and it is also **not a fix for the
remaining 116**, which is stated plainly rather than claimed away. The residual was
characterised rather than assumed:

- **114 of 116 differ in token count** on the search surface — these are word-division
  differences, not encoding differences.
- **46 of 116 carry avagraha (U+093D) on one side only** (78 occurrences in the accented layer
  against 181 in the unaccented). Avagraha is a real orthographic sign, not editorial
  apparatus, so it is deliberately *not* in `SEPARATOR_MARKS` and deliberately not folded away.
- Inspection of the residual confirms genuine textual divergence, e.g. VSM 1.1 where the
  accented layer reads `त्वोर्जे` against the unaccented layer's `त्वा ऊर्जे` — a sandhi
  difference, and exactly the philological judgement the comparator is right to refuse.

So the Latin-only-fold defect is closed, and what remains at 116 is largely genuine
segmentation and sandhi variation plus the avagraha asymmetry — recorded as the next
investigation, not as a normalization gap.

## 9. KNOWN LOSSINESS carried on purpose: the lateral series

`TRANSCRIPTION_EQUIVALENCES` folds vocalic *l* together with retroflex *l*. Agent D correctly
reported this as merging a vowel with a consonant, and correctly reported that the code's
stated justification — "the Rigveda has no vocalic l" — is false.

The justification was false. **The behaviour is nevertheless right**, for a stronger reason
found by measuring all 10,552 Rigveda mantras. Each version carries exactly 671 laterals:

| Version | l + ring below | l + dot below (U+1E37) | l + line below (U+1E3B) |
| --- | --- | --- | --- |
| GRETIL (IAST) | 0 | 3 | 668 |
| VedaWeb (ISO 15919) | 2 | 669 | 0 |

The 668↔669 and 3↔2 correspondence shows **U+1E37 is the vocalic l in GRETIL and the
retroflex l in VedaWeb** — the same code point, opposite phonemic class. No global
code-point-to-sentinel table can be correct for both.

Splitting the sentinel was implemented, measured, and **reverted**: it regressed
RV 10.157.2 (`cīkḷpāti`) from `ACCENT_ONLY` to `UNCLASSIFIED`, where both sources in fact
agree and merely spell the same vocalic l differently. Final state: behaviour unchanged from
`HEAD` (verified — 0 of 10,552 mantras shift category), with the false justification replaced
by these measured counts and an explicit lossiness note naming Agent D's 15 Atharvaveda
vocalic-l cases.

Impact bound: Atharvaveda-internal comparison is accented-GRETIL against unaccented-GRETIL —
one notation on both sides — so the fold is symmetric there and does not corrupt those
comparisons. The residual cost is that the derived **search** surface cannot distinguish
vocalic from retroflex l.

## 10. Other measured lossiness on derived surfaces

All of these affect derived surfaces only; `text_original` is untouched in every case.

- **Pluti / independent svarita digits.** GRETIL writes these as an in-word digit
  (`nya3trinam`, `aasii3d`). `DELETED_MARKS` removes digits, so pluti is lost on the search
  surface. Reported by both Agent B and Agent D. Accepted for a search surface; noted because
  it is the *only* accent-like information in the Samaveda artifact and it must survive in
  `text_original` — verified that it does.
- **Digits are ambiguous in the source line.** The trailing running number (`.. 1875`) is
  digits on the same physical line as in-word pluti digits. Anything counting digits must not
  conflate apparatus with text. Agent B strips the running number into a `Citation`.
- **Editorial apparatus inside text lines.** Agent D's Atharvaveda keeps `|`, `||18||`,
  `{11}`, `[6-7]` inside `text_original` losslessly. `text_original` is therefore not a clean
  metrical string, by design.
- **Private-use and stray characters in real sources.** VSM adhyāya 1 contains one U+F15C
  (private use, category `Co`) and one U+00AC NOT SIGN. Neither is cleaned by the normalizer
  and neither should be; they are source defects and Agent C records them as such.

## 11. Contract issues raised, not decided here

1. **Notation-aware folding** — still the right long-term shape, but no longer blocking.
   §8 closed the two concrete Devanagari cases with a safe global fold plus a script-gated
   step, because those spellings are *not* notation-dependent. A scheme argument remains the
   correct fix for genuinely notation-dependent code points, of which §9's U+1E37 is the
   proven example. The 116 residual Yajurveda cases (§8.3) are segmentation and avagraha
   asymmetry, not folding gaps.
2. **Hierarchy value `0` as "level absent"** — Samaveda encodes an absent level as a literal
   zero. `qa/checks.py` now reports this as INFO rather than rejecting it, but whether `0` or
   an omitted key is the canonical representation is an Agent A contract decision. Omitting
   the key would break a prefix model; `0` keeps the key set complete. Current handling
   accepts `0` and surfaces it.
3. **`transliteration_scheme` should be withheld, not guessed**, for text containing Vedic
   Extensions (§6). No code currently enforces that.

## 12. Reproducing every number above

```
# real-source census, accent behaviour, lossiness
PYTHONIOENCODING=utf-8 ./.venv/Scripts/python.exe <probe>          # §2, §5
# cross-process determinism (run twice, diff)
PYTHONIOENCODING=utf-8 ./.venv/Scripts/python.exe <determinism>    # §4
#   -> data/qa/four_veda_normalization_determinism_run{1,2}.tsv
# per-record NFC and idempotency over all four builds
#   -> data/qa/four_veda_gate_results.json  (gates G06, G07)
# normalization regression tests
./.venv/Scripts/python.exe -m pytest tests/unit/test_four_veda_qa_gate.py -q   # 28 passed
```

The probe scripts are working files, not deliverables; the artifacts they produce
(`data/qa/four_veda_*`) are committed and are what a reviewer should check against.
