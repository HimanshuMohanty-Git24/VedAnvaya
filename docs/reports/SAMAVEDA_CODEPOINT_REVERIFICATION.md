# Sāmaveda codepoint re-verification

**Date:** 2026-09-07  
**Branch:** `semantic-pilot-v1`  
**Starting commit:** `87411a0bd8c93bb26dc86d8f3452067e5f6f18fd`  
**Scope:** `VG:WORK:SV:KAU`, Kauthuma **ārcika only**. The gāna collections are not included.

## Verdict

`SAMAVEDA_CODEPOINT_REVERIFICATION_PASSED`

The 1,844 released canonical Sanskrit records reproduce the selected, pinned Sanskrit
Wikisource witness at codepoint level under the committed `ORIGINAL` policy: source text is
stored as `text_original`, and `text_nfc` is its NFC-only derivative. No identity decision was
reopened and no source reading was corrected.

This verdict is specifically the publication gate requested here: **canonical release text
versus the selected Wikisource source**. It does not upgrade the separate historical claim
about Wikisource's independence of descent from the Pandey lineage. That claim remains at the
committed grade `NOT_A_VERBATIM_COPY` / full independence unestablished.

## Inputs and policy

- Build configuration: `data/builds/samaveda_arcika_v1.yaml`
- Canonical text: `data/canonical/samaveda_arcika_v1/text_versions.jsonl`
- Referent evidence: `data/canonical/samaveda_arcika_v1/referent_bindings.jsonl`
- Selected source snapshots: `data/raw/wikisource_sa/2026-09-07/*.php`
- Selected artifact: `WIKISOURCE_SA.SV.KAU.SAMHITA.DEVANAGARI`
- Selected text version: `WIKISOURCE_SA.SV.KAU.ARCIKA_MULA`
- Parser: `wikisource-sa-samaveda-arcika-v2`
- Text policy: `ORIGINAL` — NFC is the only stored normalization; source defects and source
  spelling are not silently repaired.

The checked page set contained 106 ārcika pages. Its recomputed set digest was:

```text
5810a16a3ce00020c660ccdb519ae238d6a52a13ff00d3f227b11440e738f2b7
```

This exactly matched the digest pinned in `samaveda_arcika_v1.yaml`.

## Corpus-wide codepoint checks

The audit freshly loaded and parsed all 106 pinned pages, rebuilt the referent audit rows, paired
each released row with its source occurrence, and compared the resulting source text against the
tracked canonical JSONL.

| Check | Result |
|---|---:|
| Pinned Wikisource pages loaded | 106 |
| Released source occurrences | 1,844 |
| Canonical Sanskrit records | 1,844 |
| `text_original == source occurrence` codepoint-for-codepoint | 1,844 / 1,844 |
| `content_sha256 == sha256(source UTF-8) == referent text_sha256` | 1,844 / 1,844 |
| `text_nfc == NFC(source occurrence)` | 1,844 / 1,844 |
| Exact source sequence found in cleaned pinned page wikitext | 1,844 / 1,844 |
| Source-sequence failures | 0 |
| Page-set digest mismatch | 0 |

The source-sequence check removed MediaWiki apparatus/markup using the committed page cleaner
and collapsed whitespace, but performed no Sanskrit spelling, punctuation, accent, or character
substitution. It then required every released `text_original` string to occur as an exact
codepoint sequence in its identified pinned page.

## Commands executed

The committed Sāmaveda release and referent suites were run together:

```powershell
.\.venv\Scripts\python.exe -m pytest `
  tests/unit/test_samaveda_canonical_release.py `
  tests/unit/test_samaveda_referent_integrity.py -q
```

Result: **74 passed**.

Two independent temporary-root builds were compared file by file:

```powershell
.\.venv\Scripts\python.exe -c `
  "from scripts.build_samaveda_canonical import verify_determinism; print(verify_determinism())"
```

Result:

```text
(True, {})
```

The corpus-wide verification was a read-only Python audit which:

1. called `load_pages()` and `build_rows()` over the pinned snapshots;
2. paired the 1,844 released rows with their `VerseOccurrence` objects;
3. keyed canonical `text_versions.jsonl` records by passage UUID;
4. compared `text_original`, NFC, and the raw UTF-8 SHA-256 values;
5. checked exact string containment in each cleaned pinned page; and
6. recomputed `pinned_set_digest(pages)` against the build configuration.

Its result was:

```text
pages=106
released_units=1844
canonical_records=1844
exact_codepoint_equal=1844
content_sha256_equal=1844
nfc_equal=1844
exact_sequence_in_cleaned_pinned_page=1844
containment_failures=[]
digest_match=True
```

## Boundary of the conclusion

This check establishes engineering fidelity to the selected, revision-pinned Wikisource
artifact. It does not establish human scholarly accuracy against an unidentified printed
edition, does not claim that the ārcika is complete (the release retains its bounded withheld
backlog), and does not cover the larger gāna corpus.

The separate lineage/descent question recorded in
`SAMAVEDA_REFERENT_INTEGRITY_REPAIR.md` was not used as a textual correction channel and is not
silently converted into a stronger claim by this result.

---

## Independent re-verification (second reader)

The checks above were re-run from scratch by a reader who treated this report as an
unverified claim rather than as a result. The verdict stands, and three of the report's
statements above are narrower than they read.

### Confirmed

- Selected artifact established **before** measuring, from the build config and then
  independently from the data itself: `WIKISOURCE_SA.SV.KAU.SAMHITA.DEVANAGARI`, text
  version `WIKISOURCE_SA.SV.KAU.ARCIKA_MULA`. All 1,844 `text_versions.jsonl` rows and all
  1,844 `referent_bindings.jsonl` rows carry that artifact; `source_artifacts.jsonl` contains
  that artifact and no other. No GRETIL, TITUS or SANSKRITLIB text is present.
- Set digest recomputed twice by two different routes — through `pinned_set_digest(load_pages())`
  and through an independent raw filesystem scan — both giving
  `5810a16a3ce00020c660ccdb519ae238d6a52a13ff00d3f227b11440e738f2b7`, matching the pin. Every
  file's bytes hash to its own filename. The 44 non-ārcika files in the snapshot directory are
  Śukla Yajurveda and are correctly excluded.
- Codepoint mismatches 0/1,844. NFC-derivation mismatches 0. `content_sha256` vs source 0.
  `content_sha256` vs binding `text_sha256` 0. Empty text 0. Missing or mismatched
  `source_locator` 0. Records not tracing to the selected artifact 0.
- Determinism: `verify_determinism()` returned `(True, {})`, and a full rebuild reproduced all
  14 released files plus `samaveda_arcika_v1_coverage.json` byte-identically.

This is the artifact the release actually selected. The audit was scoped to it deliberately,
because a previous session's Sāmaveda forensics measured a *rejected* witness instead of the
selected one and certified the wrong thing.

### Corrections to the statements above

1. **The test result was reported as current when it was historical.** `74 passed` holds at
   committed HEAD `87411a0`. In the working tree at the time of re-verification the suite did
   not run at all: 7 failed, 44 passed, 23 errors, caused by an unrelated uncommitted edit that
   left a plain YAML scalar containing `": "` in the Atharvaveda `underlying_edition` field of
   `data/registry/text_versions.yaml`. That edit has since been quoted and the suite runs again.
   A report that says "the tests pass" should say which tree it means.
2. **"Tracked canonical JSONL" is wrong.** `data/canonical/**` is gitignored. The release is
   untracked, so nothing about it is protected by git history. This is the same hazard already
   recorded for the sealed schema.
3. **One row overstates what it checked.** *Exact source sequence found in cleaned pinned page
   wikitext, 1,844/1,844* runs after markup removal **and whitespace collapse**, which can make
   two source tokens separated by a link and a blank line become adjacent. Against raw wikitext
   with whitespace collapse only, 24 of 1,844 fail.

### New finding: apparatus lifted into four released verses

Four of those 24 are not artifacts of the check. They are printed apparatus welded onto the
front of a released verse by the parser:

| Unit | Apparatus lifted into the verse |
|---|---|
| `WS CHANDA.P1.D8 RN76` | leading `द्र.` |
| `WS ARANYA.D1 RN589` | leading `(आरण्यकगानम्) द्र. आर्षेयब्राह्मणम् भाष्यम्` |
| `WS CHANDA.P4.D5 RN337` | `(आरण्यकगानम्)` |
| `WS CHANDA.P2.D7 RN161` | `(आरण्यकम्)` |

None of the four carries a `qa_issues` row. Every codepoint in them does come from the pinned
page, so this is not a codepoint-reproduction failure and does not overturn
`SAMAVEDA_CODEPOINT_REVERIFICATION_PASSED` — the gate asks whether the release reproduces the
selected source, and it does. But these four verses reproduce *more of the page than the verse*,
and the containment check as written is structurally incapable of seeing it, because collapsing
whitespace is exactly what hides it.

Recorded as backlog `SV-APPARATUS-LIFT-01`, four units, in
`data/source_registry/four_veda_backlog.jsonl` (`data/qa/**` is gitignored, so a backlog
written there would not survive a clone). It does not block Sāmaveda publication; it does mean the
ārcika ships with a known, enumerated, four-unit defect rather than a clean bill.
