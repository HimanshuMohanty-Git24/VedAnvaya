# Rigveda Sanskrit base-edition adjudication

Reviewed: 2026-09-04. Supersedes the 2026-09-04 deferred assessment.

The question this document answers: **which Sanskrit textual representation should VedaGraph
use as its primary Rigveda Saṃhitā transcription, and which should be preserved as parallel
scholarly versions?**

Evidence comes from an artifact-level review of the pinned sources
([`VEDAWEB_RIGVEDA_SOURCES.md`](VEDAWEB_RIGVEDA_SOURCES.md)) and a deterministic comparison
over a 240-mantra stratified Mandala 1 sample
([`rv_m1_text_comparison_report.md`](../reports/rv_m1_text_comparison_report.md)).

## Candidates

| Version | Artifact | Kind |
| --- | --- | --- |
| `GRETIL.RV.AUFRECHT` | `GRETIL.RV.AUFRECHT.TEI.2019` | Transmitted Saṃhitā, IAST, accented |
| `VEDAWEB.AUFRECHT` | `VEDAWEB.RV.BOOK01.TEI.D3EB8AF` | Same lineage, ISO 15919, accented |
| `VEDAWEB.EICHLER` | `VEDAWEB.RV.BOOK01.TEI.D3EB8AF` | Transmitted Saṃhitā, Devanagari, accented |
| `VEDAWEB.VNH` | `VEDAWEB.RV.BOOK01.TEI.D3EB8AF` | Metrically restored |
| `VEDAWEB.LUBOTSKY` | `VEDAWEB.RV.BOOK01.TEI.D3EB8AF` | Concordance-derived |
| `VEDAWEB.ZURICH` | `VEDAWEB.RV.BOOK01.TEI.D3EB8AF` | Annotated, normalized |
| `VEDAWEB.PADAPATHA` | `VEDAWEB.RV.BOOK01.TEI.D3EB8AF` | Padapāṭha |
| VHP web pages | `VHP.RV.SHAKALA.MANDALA1.WEB` | Devanagari, permission required |

Unversioned mirrors and convenience datasets were not evaluated: availability alone
establishes neither edition lineage nor redistribution rights.

## Adjudication matrix

No composite score is given. The dimensions are not commensurable, and adding them would
manufacture a false precision — a version can be perfect on rights and useless as a reader
text. Each cell states a fact and its source.

### Śākala alignment

| Version | Assessment |
| --- | --- |
| `GRETIL.RV.AUFRECHT` | 10,552 verses total; 191 Suktas and 2,006 verses in Mandala 1. Header does not name the recension; Śākala is a reviewed structural inference. |
| `VEDAWEB.*` | 191 hymns and 2,006 stanzas in Book 1, matching GRETIL exactly. Header does not name the recension. |
| VHP | Explicitly labels the text Śākala Saṃhitā and exposes 191 Suktas. |

Three independent sources agree on the Mandala 1 structure, and the only one that *states*
the recension is the one that cannot be redistributed. The identification is therefore
strong but remains an inference in the two usable sources.

### Transmitted-Saṃhitā suitability

| Version | Assessment |
| --- | --- |
| `GRETIL.RV.AUFRECHT` | Transmitted text of an Aufrecht-lineage edition. Suitable. |
| `VEDAWEB.AUFRECHT` | Same, one transformation further downstream. Suitable. |
| `VEDAWEB.EICHLER` | Transmitted Devanagari, but no printed edition is named. Suitable in kind, unverified in lineage. |
| `VEDAWEB.VNH` | **Not transmitted.** 162 of 240 sampled mantras depart from the transmitted reading. |
| `VEDAWEB.LUBOTSKY` | Sandhi partly undone; concordance markers inside words. Not a reading text. |
| `VEDAWEB.ZURICH` | Partly unsandhied and elision-resolved for annotation. Not a reading text. |
| `VEDAWEB.PADAPATHA` | A different textual object entirely. |

### Accent fidelity

| Version | Assessment |
| --- | --- |
| `GRETIL.RV.AUFRECHT` | Fully accented, traditional notation: anudātta U+0331, svarita U+030D, udātta unmarked. 240/240 sampled mantras accented. |
| `VEDAWEB.AUFRECHT` / `VNH` / `LUBOTSKY` / `ZURICH` | Fully accented, linguistic notation: udātta U+0301, independent svarita U+0300. 240/240. |
| `VEDAWEB.EICHLER` | Fully accented Devanagari, U+0951/U+0952. 240/240. |
| `VEDAWEB.PADAPATHA` | **Unaccented.** 0/240. |

Every serious candidate preserves accent. The two notations are equally faithful; they are
not interchangeable as strings, which is why the comparison stack has an explicit
accent-stripped surface.

### Completeness

| Version | Assessment |
| --- | --- |
| `GRETIL.RV.AUFRECHT` | Whole Rigveda in one file, 10,552 verses. |
| `VEDAWEB.*` | Whole Rigveda across ten per-book files; every Sanskrit layer covers 100% of the 10,552 stanzas per the project's own coverage report. |
| VHP | Complete but page-by-page and permission-bound. |

### Machine readability

| Version | Assessment |
| --- | --- |
| `GRETIL.RV.AUFRECHT` | 5 MB TEI, one file, parsed deterministically by `gretil-rigveda-tei-v2`. Accent handling is unusual (standalone `orig` nodes) but fixture-tested. |
| `VEDAWEB.*` | 43 MB TEI for Book 1 alone; needs streaming. Cleanly structured, one `lg` per version per stanza. Parsed by `vedaweb-rigveda-tei-v1`. |
| VHP | HTML scraping of one page per Sukta. |

### Stable numbering

| Version | Assessment |
| --- | --- |
| `GRETIL.RV.AUFRECHT` | `RV_<mandala>.<sukta>.<verse>` on `lg/@xml:id`. |
| `VEDAWEB.*` | `b<book:02>_h<hymn:03>_<stanza:02>` on `div/@xml:id`. |
| Both | Map onto the VedaGraph citation hierarchy without ambiguity, and agree with each other on all 2,006 Mandala 1 stanzas. |

### Edition provenance

| Version | Assessment |
| --- | --- |
| `GRETIL.RV.AUFRECHT` | Three layers documented: Aufrecht 1877 → Van Nooten/Holland data entry, Eichler conversion, Grünendahl normalization → Mehner TEI 2019. Header admits silent correction of apparent errors. |
| `VEDAWEB.AUFRECHT` | The above **plus** a fourth layer: Gunkel and Ryan modification and re-transcription. |
| `VEDAWEB.EICHLER` | One web source, no printed edition named. Weakest provenance of the accented candidates. |
| `VEDAWEB.VNH` | Fully documented back to the 1970 UT electronic text and the 1994 printed book. |

### Rights clarity

| Version | Assessment |
| --- | --- |
| `GRETIL.RV.AUFRECHT` | CC BY-NC-SA 4.0 verbatim in the file, plus the GRETIL good-faith removal notice. Both persisted. No unknown state. |
| `VEDAWEB.AUFRECHT` / `EICHLER` / `LUBOTSKY` / `PADAPATHA` / `VNH` | CC BY-NC-SA 4.0 declared per version in the corpus TEI header. `VNH` additionally carries the Harvard Oriental Series research-not-commercial notice. |
| `VEDAWEB.ZURICH` | CC BY 4.0. |
| VHP | Written permission required. Disqualifying for redistribution. |

### Reproducibility

| Version | Assessment |
| --- | --- |
| `GRETIL.RV.AUFRECHT` | Content-addressed snapshot, checksum in the registry, byte-identical rebuilds proven. Upstream is a plain HTTP file with no version handle beyond its publication date. |
| `VEDAWEB.*` | Content-addressed snapshot **plus** a Git commit SHA and blob SHA. Strictly better: upstream changes are detectable, and a specific historical state is retrievable. |
| VHP | Live pages, no version handle. |

### Scholarly usefulness

`VEDAWEB.VNH`, `VEDAWEB.LUBOTSKY` and `VEDAWEB.ZURICH` are the most useful for research and
the least suitable for display. `VEDAWEB.PADAPATHA` is indispensable for word analysis and
is not a Saṃhitā variant at all. The Aufrecht-lineage texts are the least interesting
scholarly objects and the most appropriate received text.

### Reader suitability

| Version | Assessment |
| --- | --- |
| `GRETIL.RV.AUFRECHT` | Latin script. Faithful, but not what most readers of the Rigveda expect to see. |
| `VEDAWEB.EICHLER` | Devanagari, accented — the best reader text on offer, with the weakest lineage documentation and no cross-script comparison yet. |
| `VEDAWEB.VNH` / `LUBOTSKY` / `ZURICH` | Carry editorial or analytical marks that a reader would misread as the text. |

## Recommended VedaGraph role for each version

| Version | Role | Why |
| --- | --- | --- |
| `GRETIL.RV.AUFRECHT` | **`PRIMARY_TEXT`** | Transmitted Saṃhitā, fully accented, complete, deterministically parsed, byte-reproducible, rights fully documented, and the **upstream** of the only comparable alternative. |
| `VEDAWEB.AUFRECHT` | `PARALLEL_TEXT` | Same lineage in a different transcription and accent notation. Its value is as an independent rendering for QA, not as a second witness. |
| `VEDAWEB.EICHLER` | `PARALLEL_TEXT` | Accented Devanagari; the candidate for a future display derivative once cross-script comparison exists and its lineage is established. |
| `VEDAWEB.VNH` | `METRICALLY_RESTORED` | Editorial reconstruction, valuable and clearly labelled. Never the displayed Saṃhitā. |
| `VEDAWEB.PADAPATHA` | `PADAPATHA` | A different textual object; never reconciled against Saṃhitā text. |
| `VEDAWEB.LUBOTSKY` | `COMPARISON_ONLY` | Concordance-derived, partly unsandhied, carries editorial markers. |
| `VEDAWEB.ZURICH` | `LINGUISTIC_ANNOTATION` | Normalized carrier for morphology; CC BY 4.0. |
| VHP Devanagari | `REFERENCE_ONLY` | Verification, hierarchy and traditional metadata only. Permission required for anything more. |

## Why GRETIL rather than VedaWeb's rendering of the same text

The two are the same textual lineage, and the comparison shows it: 226 of 240 sampled
mantras agree letter for letter once the two accent notations are removed. Given that,
preferring the downstream copy would add a re-transcription step, a re-notation step and a
second project's editorial decisions between VedaGraph and the edition, for no additional
evidence.

The one real advantage VedaWeb has is version pinning: a Git commit is a better handle than
a plain HTTP file. That is worth having, and it is exactly why `VEDAWEB.AUFRECHT` is kept as
a parallel version. It is not worth inserting a transformation layer under the primary text.

## Why not simply pick the metrically restored text

Because "philologically useful" and "canonical display text" are different questions.
`VEDAWEB.VNH` departs from the transmitted reading in about two thirds of the sampled
mantras, by design and by its editors' explicit intent. Presenting it as the Rigveda would
show a reconstruction as the received text. It is kept, labelled, and comparable.

## Rights position

The primary source is CC BY-NC-SA 4.0 with the licence text and the upstream notice both
persisted in the registry. VedaGraph's intended use is non-commercial research and
education. Generated corpus output stays out of Git. No primary-source component is in an
`UNKNOWN` rights state.

The two file-level `UNKNOWN` markers on the VedaWeb artifacts are deliberate and are not a
gap: those files genuinely have no single licence, and the real terms are recorded one
level down, per version.

A corpus that mixes any CC BY-NC-SA layer with the CC BY layers is bound as a whole by the
stricter non-commercial and share-alike terms. This is a reading of the declared terms, not
legal advice, and no legal conclusion is asserted anywhere in this repository.

## Limitations of this decision

- Śākala identification for both usable sources remains a structural inference.
- The GRETIL header's admitted silent correction of apparent errors is undocumented at the
  reading level, so individual corrections cannot be audited.
- 14 of 240 sampled mantras show a difference between GRETIL and VedaWeb's rendering of the
  same lineage that no deterministic rule explains. They are recorded, not resolved.
- `VEDAWEB.EICHLER` has not been compared against anything, because cross-script comparison
  needs a reviewed transliteration step that does not exist yet.
- The choice is reversible by configuration and cannot change passage identity, which is
  what makes committing to it now safe.

## DECISION: PRIMARY SELECTED

For VedaGraph Rigveda v1, `GRETIL.RV.AUFRECHT` (artifact `GRETIL.RV.AUFRECHT.TEI.2019`,
SHA-256 `14197d9c1dcced64900ef971d9f4dc5b46aa8750780f5599453c9739d6a29edd`) is the primary
displayed Saṃhitā representation, because it is a complete, fully accented, deterministically
parsed transmitted Saṃhitā whose rights are explicitly documented, and because the only
comparable alternative is derived from it.

`VEDAWEB.VNH` is preserved as a metrically restored scholarly parallel.
`VEDAWEB.PADAPATHA` is preserved as Padapāṭha. `VEDAWEB.AUFRECHT` and `VEDAWEB.EICHLER` are
preserved as parallel Saṃhitā representations. `VEDAWEB.LUBOTSKY` and `VEDAWEB.ZURICH` are
preserved for comparison and linguistic annotation. Every record retains exact source,
artifact, version and licence provenance.

The selection lives in `data/builds/rv_mandala_1.yaml` under `primary_sanskrit`. See
[ADR-008](../decisions/ADR-008-primary-sanskrit-text.md).
