# Rigveda Śākala Corpus

## Source editions

Primary Sanskrit is `GRETIL.RV.AUFRECHT`; parallel Sanskrit is the commit-pinned `VEDAWEB.AUFRECHT`; English is Griffith 1896 through pinned Wikisource revisions.

## Rights

GRETIL and VedaWeb Aufrecht are CC BY-NC-SA 4.0; Griffith 1896 is public domain. VHP remains permission-required and reference-only.

## Structure

| Unit | External expectation | Discovered | Canonical |
| --- | ---: | ---: | ---: |
| Mandalas | 10 | 10 | 10 |
| Suktas | 1,028 | 1028 | 1028 |
| Mantras | 10,552 | 10552 | 10552 |

## Sanskrit coverage

Primary: 10552/10552 (100.00%). Parallel: 10552/10552 (100.00%).

## Parallel text comparison

ACCENT_ONLY: 9746, SANDHI_OR_SEGMENTATION: 35, UNCLASSIFIED: 771

## English coverage

| Mandala | Total | Exact | Range | Hymn-only | Uncertain | Missing |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 2006 | 1926 | 0 | 0 | 41 | 39 |
| 2 | 429 | 429 | 0 | 0 | 0 | 0 |
| 3 | 617 | 617 | 0 | 0 | 0 | 0 |
| 4 | 589 | 589 | 0 | 0 | 0 | 0 |
| 5 | 727 | 702 | 0 | 0 | 23 | 2 |
| 6 | 765 | 765 | 0 | 0 | 0 | 0 |
| 7 | 841 | 841 | 0 | 0 | 0 | 0 |
| 8 | 1716 | 1682 | 0 | 0 | 33 | 1 |
| 9 | 1108 | 1107 | 0 | 0 | 0 | 1 |
| 10 | 1754 | 1686 | 0 | 0 | 59 | 9 |

## Metadata coverage

Traditional Rishi, Devata, and Chandas coverage remains intentionally partial and concentrated in the reviewed Mandala 1 sample.

## Media coverage

External-only references: 5; no media was downloaded, rehosted, or newly aligned.

## Per-Mandala coverage matrix

| Mandala | Suktas | Mantras | Primary | Parallel | Griffith exact | Rishi | Devata | Chandas | Audio/ref | Warnings | Errors |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 191 | 2006 | 100.00% | 100.00% | 96.01% | 2.62% | 1.05% | 1.05% | 2.62% | 178 | 0 |
| 2 | 43 | 429 | 100.00% | 100.00% | 100.00% | 0.00% | 0.00% | 0.00% | 0.00% | 31 | 0 |
| 3 | 62 | 617 | 100.00% | 100.00% | 100.00% | 0.00% | 0.00% | 0.00% | 0.00% | 51 | 0 |
| 4 | 58 | 589 | 100.00% | 100.00% | 100.00% | 0.00% | 0.00% | 0.00% | 0.00% | 45 | 0 |
| 5 | 87 | 727 | 100.00% | 100.00% | 96.56% | 0.00% | 0.00% | 0.00% | 0.00% | 58 | 0 |
| 6 | 75 | 765 | 100.00% | 100.00% | 100.00% | 0.00% | 0.00% | 0.00% | 0.00% | 73 | 0 |
| 7 | 104 | 841 | 100.00% | 100.00% | 100.00% | 0.00% | 0.00% | 0.00% | 0.00% | 87 | 0 |
| 8 | 103 | 1716 | 100.00% | 100.00% | 98.02% | 0.00% | 0.00% | 0.00% | 0.00% | 103 | 0 |
| 9 | 114 | 1108 | 100.00% | 100.00% | 99.91% | 0.00% | 0.00% | 0.00% | 0.00% | 40 | 0 |
| 10 | 191 | 1754 | 100.00% | 100.00% | 96.12% | 0.00% | 0.00% | 0.00% | 0.00% | 170 | 0 |

## QA findings

Status: `PASSED_WITH_WARNINGS`.

- `deferred_metadata_range`: 6
- `duplicate_translation_for_passage`: 2
- `primary_parallel_text_divergence`: 806
- `translation_alignment_uncertain`: 10
- `translation_coverage_incomplete`: 17
- `translation_page_parse_failed`: 1

## Known anomalies

Translation gaps and uncertain alignments are retained honestly. Non-structural primary/parallel residuals are warnings; structural mismatches are errors. The specific anomalies found while building this corpus:

- **Valakhilya placement (Book 8).** Griffith prints RV 8.49-8.59 at the end of his Book 8 as Hymns 93-103, while Aufrecht numbers them inline. The mapping lives in `vedagraph.editions`, not in a parser conditional; without it, 220 mantras would have carried the wrong English text.
- **Griffith's untranslated passages.** RV 1.179 has no translated stanzas at all (Griffith relegated it to an appendix, partly in Latin); RV 10.61.5-9 and RV 10.86.16-17 are likewise absent from the source page. These are gaps, never filled from another translator.
- **Wikisource transcription slips.** RV 5.44 numbers a stanza `11` twice and RV 5.55 skips stanza 8; RV 10.48 and RV 10.132 skip one each. The affected Suktas are marked `UNCERTAIN_ALIGNMENT` rather than silently renumbered.
- **Three Wikisource page layouts.** Stanzas appear as `.ws-poem` markup, as `<div class="verse"><pre>`, and as plain body text (e.g. RV 5.65). All three are parsed by one numbering grammar.
- **Accent encodings differ by design.** GRETIL marks accent with combining diacritics below the line, VedaWeb with acute/grave above it, so almost no pair is byte-identical. This is representation, not textual variance.

## Reproducibility

The full corpus is assembled in deterministic canonical order from the ten validated Mandala outputs; runtime timestamps come from version-controlled configuration, never from the clock. Rebuilding all ten Mandalas from the pinned snapshots and re-assembling reproduces every canonical file byte-for-byte, manifest included. There is no separate single-pass whole-corpus builder to compare against: the corpus is defined as the assembly of its Mandala units, so the two cannot disagree by construction.

## Performance

`scripts/build_rigveda_full.py` writes per-stage timings and record counts to `data/derived/rigveda_build_performance.json`. A full run from pinned snapshots (stage, build, and gate all ten Mandalas, then assemble) takes roughly 100 seconds and produces about 45 MB of canonical JSONL. Each Mandala reads its own VedaWeb book file, so no source is re-parsed per Mandala and no source index is needed.

## Lineage

Every primary and parallel TextVersion names a registered SourceArtifact; every Griffith record carries page/revision provenance where the source page was parseable.

## Remaining limitations

Traditional metadata and media are incomplete by policy. Griffith coverage is not filled with another translator. Śākala identification remains the documented structural inference of the project.

## Next phase

After readiness is confirmed, the next engineering phase is the Rigveda deterministic knowledge layer. It is not implemented by this build.
