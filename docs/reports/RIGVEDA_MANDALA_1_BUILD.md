# Rigveda Mandala 1 Corpus

Generated from the reproducible `rv_mandala_1_full_v1` build
(`data/builds/rv_mandala_1_full_v1.yaml`, config SHA-256
`abbc1a87c0c5fb0ddb3e827cd61a68ec105da18b16f5dce2051b3c41d6be40c6`). Every figure below comes from the canonical
JSONL output or the QA report; nothing is hand-counted. No bulk Sanskrit or English
corpus text is reproduced in this document.

## Structure

- Suktas: 191 / 191
- Mantras: 2006 / 2,006 (independent GRETIL/VHP/VedaWeb structural expectation)

## Sanskrit coverage

- Primary (`GRETIL.RV.AUFRECHT`): 2006/2006
  (100.0%)
- Parallel (`VEDAWEB.AUFRECHT`): 2006/2006
  (100.0%)

## Parallel text coverage

Every mantra with a GRETIL primary reading also carries a VedaWeb `AUFRECHT`
parallel reading pinned to VedaWeb commit `d3eb8af7324338161520d2d35eae8f7e985a19a5`,
compared deterministically per mantra (`primary_parallel_text_divergence` QA policy).

## English coverage

- Exact mantra-level Griffith alignment: 1926/2006 (96.0%)
- Missing, across 10 Suktas ([53, 65, 66, 67, 68, 69, 70, 73, 91, 179]): 39
- See `docs/reports/rv_m1_translation_coverage_report.md` for the per-Sukta breakdown.

## Traditional metadata coverage (VHP; intentionally partial, see docs/STATUS.md)

- Suktas with any traditional metadata: 5/191
- Rishi assertions: 5 Suktas
- Devata assertions: 2 Suktas
- Chandas assertions: 2 Suktas
- No new bulk VHP ingestion happened this session; coverage is unchanged from the
  5-Sukta reviewed sample (Suktas 1, 22, 50, 164, 191).

## Audio/media coverage

- Suktas with an external audio reference: 5/191 (VHP reference-only,
  same 5 Suktas as traditional metadata; no download, no new discovery this session)

## Source versions

- Primary Sanskrit: `GRETIL.RV.AUFRECHT` (`GRETIL.RV.AUFRECHT.TEI.2019`)
- Parallel Sanskrit: `VEDAWEB.AUFRECHT` (`VEDAWEB.RV.BOOK01.TEI.D3EB8AF`, commit-pinned)
- Translation: Griffith 1896, via Wikisource, page/revision-pinned per Sukta
- Traditional metadata/media: VHP, reference-only, 5 Suktas

## Rights

- GRETIL primary text: CC BY-NC-SA 4.0 (declared in the TEI header, verbatim preserved)
- VedaWeb `AUFRECHT` parallel text: CC BY-NC-SA 4.0 (per-version,
  `data/registry/text_versions.yaml`)
- Griffith translation: public domain (1896); Wikisource transcription/revision layer
  tracked separately
- VHP: permission-required; reference-only, nothing redistributed

## QA

- Status: PASSED_WITH_WARNINGS
- Total findings: 184
- By severity: {'WARNING': 184}
- By check: {'deferred_metadata_range': 6, 'duplicate_translation_for_passage': 1, 'primary_parallel_text_divergence': 164, 'translation_alignment_uncertain': 3, 'translation_coverage_incomplete': 9, 'translation_page_parse_failed': 1}
- Structural errors: 0

## Text divergences

164 of 2006 mantras
show a residual primary/parallel divergence beyond known accent-notation differences
(`primary_parallel_text_divergence`, all WARNING severity in this build — no
ERROR-level structural misalignment). This matches the proportion already recorded
in the 240-mantra stratified sample (`docs/reports/rv_m1_text_comparison_report.md`);
see `docs/reports/rv_m1_full_text_comparison_report.md` for the full-corpus classification.

## Translation anomalies

- RV 1.179: no parseable Wikisource stanza markup on the pinned revision
  (`translation_page_parse_failed`).
- 3 Suktas parsed a real but
  unconfirmed stanza sequence (`translation_alignment_uncertain`): the detected
  stanza count did not exactly match a confirmed 1..N verse-number sequence.
- 9 Suktas (including some of
  the above) parsed with internally consistent 1..N numbering but fewer stanzas than
  the Sukta's real mantra count (`translation_coverage_incomplete`) — "exact" only
  means self-consistent, not complete; the shortfall is missing, not guessed. See
  `docs/reports/rv_m1_translation_coverage_report.md` for the exact Sukta list.
- The remaining Suktas parsed with a complete `EXACT_MANTRA_ALIGNMENT`.

## Reproducibility

Two builds from the identical pinned config produced byte-identical
`passages.jsonl`, `text_versions.jsonl`, `translations.jsonl`, `traditional_metadata.jsonl`,
`citations.jsonl`, `source_assertions.jsonl`, `discoveries.jsonl`, and `qa_issues.jsonl`.
`build_timestamp` in the config is the only externalized non-derived value; nothing else
depends on wall-clock time, retrieval order, or dict iteration order.

## Known limitations

1. Traditional metadata (Rishi/Devata/Chandas) and audio references cover only the 5
   Suktas already reviewed under the pilot; VHP bulk ingestion remains prohibited
   without written permission.
2. 39 mantras across 10 Suktas ([53, 65, 66, 67, 68, 69, 70, 73, 91, 179])
   have no Griffith translation on the pinned Wikisource revisions; genuinely missing,
   not fabricated.
3. Śākala recension identification remains a structural inference in both
   redistributable sources (GRETIL, VedaWeb), as already documented in
   `docs/architecture/RIGVEDA_BASE_EDITION.md`.
4. 164 mantras carry an unresolved primary/parallel textual divergence beyond
   notation; recorded as QA WARNINGs, not resolved by this build.

## Readiness for next stage

`READY_WITH_LIMITATIONS`. Structure, identity, primary/parallel Sanskrit, translation
alignment, QA, and reproducibility all pass with zero structural errors. Traditional
metadata and audio remain intentionally partial by rights policy, not by omission.
