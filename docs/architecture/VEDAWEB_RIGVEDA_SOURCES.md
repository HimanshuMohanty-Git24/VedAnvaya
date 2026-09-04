# VedaWeb Rigveda source versions

Reviewed: 2026-09-04

VedaWeb publishes its data at
[`VedaWebProject/vedaweb-data`](https://github.com/VedaWebProject/vedaweb-data). This
review is of the repository, not of the web application, and it is pinned to one commit.

## Pinned artifacts

| Field | Value |
| --- | --- |
| Repository | `https://github.com/VedaWebProject/vedaweb-data` |
| Commit | `d3eb8af7324338161520d2d35eae8f7e985a19a5` (2025-06-13) |
| Default branch | `main` (never built against directly) |

| Artifact ID | Path | Size | Git blob | SHA-256 |
| --- | --- | --- | --- | --- |
| `VEDAWEB.RV.CORPUS.TEI.D3EB8AF` | `rigveda/TEI/vedaweb_corpus.tei` | 111,892 B | `741738f7d476ff08f8a0ec17096834e65bf257c2` | `7ba145d9…97a15b` |
| `VEDAWEB.RV.BOOK01.TEI.D3EB8AF` | `rigveda/TEI/rv_book_01.tei` | 43,847,826 B | `e2321eab20f3ff9c73f466347f8e6ca20ad1079c` | `c5c18d89…2bc984c` |

Full checksums live in `data/registry/source_artifacts.yaml`.

`vedaweb_corpus.tei` is a `teiCorpus` header carrying **no Rigveda text**. It is the
authority for provenance and rights: every incorporated source has its own `biblFull`
entry with its own responsibility statements, its own upstream bibliography and its own
Creative Commons licence. `rv_book_01.tei` contains the text and points at that header.

## Corpus model

`rv_book_01.tei` is Mandala 1 only: **191 hymns and 2,006 stanzas**, matching the GRETIL
TEI Mandala 1 counts exactly and matching VHP's navigation count of 191 Suktas. Its
citation system is `b<book:02>_h<hymn:03>_<stanza:02>`.

Each `<div type="stanza">` carries parallel `<lg source="...">` blocks. They are not
renderings of one text; they are **separate editions with separate lineage and separate
licences**, plus annotation and translation layers:

| `@source` | Kind | Coverage in Book 1 |
| --- | --- | --- |
| `strata` (`@type`) | Metrical stratum annotation | 2,006 |
| `zurich` | Sanskrit, with per-token morphology | 2,006 |
| `lubotsky` | Sanskrit, concordance-derived | 2,006 |
| `vnh` | Sanskrit, metrically restored | 2,006 |
| `aufrecht` | Sanskrit, transmitted Samhita | 2,006 |
| `padapatha` | Padapatha | 2,006 |
| `eichler` | Sanskrit, Devanagari | 2,006 |
| `geldner`, `grassmann`, `otto` | German translations | 2,006 / 2,006 / 9 |
| `griffith`, `macdonell`, `mueller`, `oldenberg` | English translations | 2,006 / 105 / 202 / 436 |
| `renou` | French translation | 1,574 |
| `elizarenkova` | Russian translation | 2,006 |

The Sanskrit adapter reads only the six Sanskrit `@source` values and refuses any other
name; translation layers can never enter a Sanskrit text record by accident.

## Version catalogue

The machine-readable form of this table is `data/registry/text_versions.yaml`. Rights
fields there are extracted from the TEI header, not retyped.

### `VEDAWEB.AUFRECHT`

| Field | Value |
| --- | --- |
| Human title | Rigveda-Samhita (Aufrecht lineage, VedaWeb rendering) |
| Text type | Transmitted Samhita transcription |
| Samhita / Padapatha / restored | Samhita |
| Recension | Shakala (structural identification; not stated in the header) |
| Underlying edition | Theodor Aufrecht, *Die Hymnen des Rigveda*, Bonn, 1877 |
| Electronic lineage | Van Nooten and Holland data entry → Eichler conversion → Grünendahl GRETIL normalization → Mehner TEI conversion → **GRETIL `sa_Rgveda-edAufrecht.xml`** → modified for VedaWeb by Gunkel and Ryan |
| Accents | Accented; udatta marked with U+0301 |
| Metrical restoration | No |
| Orthographic normalization | Re-transcribed from GRETIL IAST into ISO 15919; hemistich line split |
| Licence | CC BY-NC-SA 4.0 |
| Restrictions | GRETIL good-faith notice preserved |
| VedaGraph role | `PARALLEL_TEXT` |

The VedaWeb header's own `<ptr>` names
`http://gretil.sub.uni-goettingen.de/gretil/corpustei/sa_Rgveda-edAufrecht.xml` as the
source. **This is the same file VedaGraph already registers as
`GRETIL.RV.AUFRECHT.TEI.2019`.** It is a downstream rendering, not an independent witness,
so adopting it as primary would add a transformation layer without adding evidence.

### `VEDAWEB.EICHLER`

| Field | Value |
| --- | --- |
| Human title | Rigveda-Samhita, Devanagari (Detlef Eichler) |
| Text type | Transmitted Samhita transcription in Devanagari |
| Recension | Shakala (structural identification) |
| Underlying edition | **Not stated in the TEI header** |
| Electronic lineage | `http://www.detlef108.de/RV-D-UTF8.html`, downloaded 2020-11-22 |
| Accents | Accented Devanagari, U+0951/U+0952 |
| Metrical restoration | No |
| Licence | CC BY-NC-SA 4.0 |
| VedaGraph role | `PARALLEL_TEXT`, and the only candidate for a future Devanagari display derivative |

The only accented Devanagari layer in the corpus. It cannot yet be string-compared against
the Latin versions, and its header names no printed edition, so it is not a primary-text
candidate in this session.

### `VEDAWEB.LUBOTSKY`

| Field | Value |
| --- | --- |
| Human title | A Rgvedic Word Concordance (Lubotsky) text layer |
| Text type | Concordance-derived pada text |
| Underlying edition | A. Lubotsky, *A Rgvedic Word Concordance*, 1997 |
| Electronic lineage | Author file shared with Gunkel and Ryan on 2010-03-29 |
| Accents | Accented, U+0301 |
| Orthographic normalization | Pada-segmented; carries concordance markers inside words; **sandhi is partly undone** (`pūrvebhiḥ` where the Samhita text reads `pūrvebhir`) |
| Licence | CC BY-NC-SA 4.0 |
| VedaGraph role | `COMPARISON_ONLY` |

### `VEDAWEB.VNH`

See [Van Nooten and Holland](#van-nooten-and-holland) below.

### `VEDAWEB.ZURICH`

| Field | Value |
| --- | --- |
| Human title | Rigveda - University of Zurich linguistic version |
| Text type | Linguistically annotated normalized text with token morphology |
| Underlying edition | University of Zurich Rigveda database, revised 2020, 2023, 2024 |
| Electronic lineage | Universität Zürich; modified by Halfmann, Korobzow, Casaretto, Fischer, Coenen |
| Accents | Accented, U+0301 |
| Orthographic normalization | Uses U+1E43 for anusvara where `aufrecht` and `vnh` use U+1E41; **partly unsandhied and elision-resolved** (`agne` for `gne`, `sutāḥ` for `sutā`) |
| Licence | **CC BY 4.0** — the only layer with a different licence |
| VedaGraph role | `LINGUISTIC_ANNOTATION` |

### `VEDAWEB.PADAPATHA`

| Field | Value |
| --- | --- |
| Human title | Rigvedasamhita, Padapatha |
| Text type | Padapatha |
| Underlying edition | Not stated in the TEI header |
| Electronic lineage | Sansknet Project data entry → GRETIL `sa_RgvedasaMhitApadapATha.xml` (2020-07-31) → modified for VedaWeb by Gunkel and Ryan |
| Accents | Unaccented (0 of 240 sampled mantras carry tone marks) |
| Orthographic normalization | Word-segmented with hyphen compound boundaries; uses `l` + U+0325 where other layers use U+1E37 |
| Licence | CC BY-NC-SA 4.0 |
| VedaGraph role | `PADAPATHA` |

Padapatha is a different textual object, not a variant reading. It must never be
reconciled against Samhita text.

## Van Nooten and Holland

The `vnh` layer's `<availability>` records, verbatim, that the online text derives from

> Barend A. van Nooten and Gary B. Holland, *Rig Veda: A Metrically Restored Text*,
> Harvard University Press, 1994

through the UT Austin Linguistics Research Center edition of Karen Thomson and Jonathan
Slocum, itself based on the diskette issued with the printed book. The header preserves
the diskette notice:

> Copyright with the authors and Harvard Oriental Series. The electronic text may be used
> for research but not for commercial purposes.

VedaGraph keeps both that notice and VedaWeb's own CC BY-NC-SA 4.0 declaration. They point
the same way (non-commercial), so no contradiction has to be resolved.

Findings from the pinned data, over the 240-mantra stratified sample:

- **It is accented.** Udatta with U+0301, in the same notation as the other VedaWeb Latin
  layers.
- **It is metrically restored, not transmitted.** Against `VEDAWEB.AUFRECHT` — the same
  file, the same transcription conventions, so notation cancels out — 78 of 240 mantras
  are byte-identical and **162 differ**. Roughly two thirds of the sample carries an
  editorial departure from the transmitted Samhita reading.
- **The restorations are systematic, not errors.** They restore the poetic form, chiefly by
  resolving semivowels and hiatus that the transmitted text contracts.
- **Its own editors say so.** The header states the edition exists because readers "may
  lack access to the out-of-print Harvard edition and be unaware of the deficiencies of the
  ancient saṃhitā text which formed the basis for Theodor Aufrecht's nineteenth-century
  transliterated edition." That is a philological position about the transmitted text.
  VedaGraph does not adjudicate it; it records that the two objects are different.

Conclusion: `VEDAWEB.VNH` is **philologically valuable and must not be the primary displayed
Samhita**. Displaying a restored text as *the* Rigveda would present an editorial
reconstruction as the received text. It is retained as `METRICALLY_RESTORED`, a first-class
parallel version.

## Aufrecht and GRETIL

Three provenance layers must not be collapsed:

1. **The nineteenth-century publication.** Theodor Aufrecht, *Die Hymnen des Rigveda*, Bonn,
   1877, volumes 1–2. A printed transliterated edition of the received Shakala Samhita.
2. **The modern electronic transformation.** Data entry by Barend A. Van Nooten and Gary B.
   Holland; conversion and revision by Detlef Eichler; contribution to GRETIL by Eichler;
   initial GRETIL normalization by Reinhold Grünendahl. The header states that apparent
   errors were silently corrected during this process.
3. **The current GRETIL TEI file.** `sa_Rgveda-edAufrecht.xml`, TEI normalization and
   conversion by Maximilian Mehner, published 2019-10-03, SHA-256
   `14197d9c1dcced64900ef971d9f4dc5b46aa8750780f5599453c9739d6a29edd`, registered as
   `GRETIL.RV.AUFRECHT.TEI.2019`.

Note that the same two people did the data entry for both the Aufrecht e-text and the 1994
metrically restored edition. The two textual objects are still different: the file GRETIL
distributes is an Aufrecht-lineage transmitted text, not the restored text.

Technical properties of the current file, all fixture-tested:

- **Accent encoding.** Anudatta U+0331 and svarita U+030D, with udatta unmarked — the
  traditional printed convention, and the opposite of VedaWeb's linguistic convention.
- **`orig`/`reg` behaviour.** 175,308 *standalone* `orig` elements carry the accent marks.
  The file contains no `choice`, `reg`, `sic` or `corr` elements at all, contrary to the
  generic prose in its own header. `ORIGINAL` selection retains standalone `orig`;
  `REGULARIZED` omits it. Branches are selected, never concatenated (ADR-007).
- **Transliteration.** IAST with GRETIL conventions: U+1E3B for the retroflex lateral,
  geminate `cch`, and an in-word decimal digit marking the independent svarita (`i1tthā`).
- **Structure.** 10,552 `lg` records for the whole Rigveda; 191 Suktas and 2,006 `lg`
  records in Mandala 1. Citation system `RV_<mandala>.<sukta>.<verse>`.
- **Known limitations.** The header does not state the recension, so Shakala identification
  is a reviewed structural inference cross-checked against VHP and VedaWeb, not quoted
  metadata. The silent error correction is undocumented at the reading level.
- **Licence.** CC BY-NC-SA 4.0, verbatim in the file, alongside the GRETIL good-faith
  removal notice. Both are preserved.
- **Parser compatibility.** Already parsed deterministically by `gretil-rigveda-tei-v2`,
  with byte-identical rebuilds.

## Rights are per version, never per host

`VedaWeb = CC BY` and `VedaWeb = CC BY-NC-SA` are both wrong. The repository has no
repository-wide licence, and `rv_book_01.tei` mixes layers under two different licences.
Consequently:

- `data/registry/sources.yaml` records `VEDAWEB` rights as `UNKNOWN` **by design**, with a
  note pointing at the per-version registry.
- Both VedaWeb artifacts carry `rights_status: UNKNOWN` at file level for the same reason.
- `data/registry/text_versions.yaml` holds, per version: `normalized_rights`,
  `license_uri`, `verbatim_license`, `upstream_rights_notes`, and where applicable
  `source_specific_restrictions`.

Summary of what the header actually declares:

| Version | Licence | Extra upstream notice |
| --- | --- | --- |
| `aufrecht` | CC BY-NC-SA 4.0 | GRETIL good-faith removal notice |
| `eichler` | CC BY-NC-SA 4.0 | — |
| `lubotsky` | CC BY-NC-SA 4.0 | Author file shared privately in 2010 |
| `padapatha` | CC BY-NC-SA 4.0 | GRETIL good-faith removal notice |
| `vnh` | CC BY-NC-SA 4.0 | Harvard Oriental Series diskette notice: research, not commercial |
| `zurich` | **CC BY 4.0** | — |
| `addressees`, `strata`, `stanza_properties` | **CC BY 4.0** | — |
| translation layers | CC BY-NC-SA 4.0 | per-translation bibliography |

A corpus that combines any CC BY-NC-SA layer with the CC BY layers is, as a whole, bound by
the stricter non-commercial and share-alike terms. This is a factual observation about the
declared terms, not legal advice.

## Comparison results

Full data: [`docs/reports/rv_m1_text_comparison_report.md`](../reports/rv_m1_text_comparison_report.md).

Over a 240-mantra stratified sample of Mandala 1, with `GRETIL.RV.AUFRECHT` as baseline:

| Compared version | Accent-only | Segmentation | Metrical restoration | Unclassified |
| --- | --- | --- | --- | --- |
| `VEDAWEB.AUFRECHT` | 226 | 0 | 0 | 14 |
| `VEDAWEB.EICHLER` | 0 | 0 | 0 | 240 (different script) |
| `VEDAWEB.LUBOTSKY` | 4 | 0 | 0 | 236 |
| `VEDAWEB.PADAPATHA` | 0 | 1 | 0 | 239 |
| `VEDAWEB.VNH` | 76 | 0 | 164 | 0 |
| `VEDAWEB.ZURICH` | 166 | 1 | 0 | 73 |
| `VEDAWEB.AUFRECHT` vs `VEDAWEB.VNH` | 0 (78 identical) | 0 | 162 | 0 |

Reading of these numbers:

- GRETIL and VedaWeb's `aufrecht` agree on the letters of **226 of 240** mantras once the
  two accent notations are removed. They are the same text in two notations, as the
  lineage predicts.
- The 14 residual cases are two known classes plus a small tail: VedaWeb restores a
  contracted vowel where GRETIL writes the independent-svarita numeral
  (`juhvāsyaḥ` / `juhvāāsyaḥ`), and a handful of visarga differences (`naḥ` / `na`).
  None is an error in either file; all need a reader, so they stay `UNCLASSIFIED`.
- `VEDAWEB.EICHLER` is Devanagari. The comparator refuses to compare across scripts rather
  than pretend, so all 240 are `UNCLASSIFIED` with that stated basis.
- `VEDAWEB.LUBOTSKY` and `VEDAWEB.ZURICH` differ systematically because they undo sandhi
  and resolve elision. That is what their roles say they are for.
