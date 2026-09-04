# Source policy and D1 research notes

Research reviewed on 2026-09-04. Claims below describe observed source behavior, not permanent
guarantees. Adapters must consume snapshots, and live integration checks are opt-in.

## Vedic Heritage Portal / IGNCA

- Observed format: server-rendered HTML with accented Devanagari, Mandala/Sukta navigation,
  traditional metadata headings, translation/commentary links, and Sukta-level MP4 references.
- RV 1.1 exposes nine numbered mantras, the Rishi `Madhucchandas Vaishvamitra`, Devata `Agni`,
  Chandas `Gayatri`, and `RIGSS_01_001.mp4`.
- Structure: Rigveda Shakala is exposed as Mandala → Sukta → Mantra; Mandala 1 discovery lists
  Suktas 001–191.
- Samaveda finding: Kauthuma is divided into Purvarcika and Uttararcika. The pages expose nested
  Kanda/Adhyaya/Prapathaka/Ardha groupings and local plus parenthesized numbering. Uttararcika
  also includes split labels such as `05(a)` and `05(b)`. A single running ID would lose edition
  structure, so Samaveda identity remains open.
- Rights: the [copyright policy](https://vedicheritage.gov.in/copyright-policy/) requires written
  permission for partial or full reproduction. Bulk ingestion is prohibited pending permission.
- Strategy: bounded verification, hierarchy/metadata QA, and external audio discovery only.

## GRETIL

- Observed format: direct TEI-conformant XML plus generated HTML and plain text.
- Reviewed file: [`sa_Rgveda-edAufrecht.xml`](https://gretil.sub.uni-goettingen.de/gretil/corpustei/sa_Rgveda-edAufrecht.xml),
  approximately 5 MB, names Van Nooten/Holland data entry, Eichler conversion/revision, and the
  1877 Aufrecht edition in `sourceDesc`.
- TEI structure: `div type="maṇḍala"` → `div type="sūkta"` → `lg xml:id="RV_1.001.01"` →
  metrical `l` elements. The reviewed snapshot SHA-256 is
  `14197d9c1dcced64900ef971d9f4dc5b46aa8750780f5599453c9739d6a29edd`.
- Actual editorial markup: 175,308 standalone `orig` elements hold combining Vedic accent marks;
  this file contains zero `choice`, `reg`, `sic`, and `corr` elements. The generic TEI-header prose
  describes a `choice/orig/reg` convention not used by this artifact. `ORIGINAL` retains standalone
  `orig`; `REGULARIZED` omits them; adapters never concatenate alternative branches.
- Structure counts computed from this artifact: 10,552 `lg` records overall; Mandala 1 has 191
  Suktas and 2,006 `lg` records with no discovered Sukta gaps.
- Rights: this specific file declares CC BY-NC-SA 4.0. Licensing varies by file and must be read
  from each TEI `publicationStmt/availability` before ingestion.
- Strategy: preserve this as an artifact-specific candidate text, with header bibliography,
  transformation identity, and selection policy. The canonical base-edition decision remains
  deferred pending a VedaWeb artifact comparison and distribution-policy review.

## VedSearch

- Observed format: HTML application pages at stable-looking paths such as
  [`/rigved/1/1/1`](https://vedsearch.org/rigved/1/1/1), with Sanskrit, Hindi, and English.
- Numbering/quality: navigation uses `1.1.1`, but displayed corpus assertions conflict internally:
  the homepage shows Atharvaveda as both 5,977 and 5,987, and another page asserts a different
  Rigveda count. These values are evidence for `SourceAssertion`, never canonical counts.
- Audio: a playlist route exists, but D1 did not establish media identifiers, granularity, API
  stability, provenance, or reuse permission.
- Rights: no reusable content license was located during D1. Status remains `UNKNOWN`.
- Strategy: no parser activation until numbering, endpoint stability, translator attribution, and
  terms are resolved. English content is never treated as the universal translation.

## Wikisource historical translations

- The [Griffith Rigveda work page](https://en.wikisource.org/wiki/The_Hymns_of_the_Rigveda)
  identifies the second edition (Benares, 1896) and marks the work and translation public domain.
- Hymn pages use scan-backed `.ws-poem-stanza` markup, providing clean verse segmentation for the
  RV 1.1 pilot. Other Book 1 pages use a legacy numbered `.verse pre` representation. Both are
  parsed only when the source exposes a complete explicit 1..N stanza sequence (the first modern
  stanza may have an implicit 1 followed by explicit 2..N). MediaWiki API snapshots now preserve
  page title, page ID, revision ID, revision timestamp, canonical URL, and retrieval provenance.
- Wikisource site UI/text is CC BY-SA while the underlying work is public domain; distinguish the
  transcription/revision layer from the historical work.
- Samaveda Griffith, White Yajurveda Griffith, and Whitney/Lanman Atharvaveda are registered
  provisionally. Exact scans, editions, revision IDs, and recension alignment must be selected
  before ingestion.

## Unresolved questions

1. Obtain written VHP permission or keep all VHP content reference-only.
2. Decide whether CC BY-NC-SA GRETIL records may appear in the intended distribution and how
   share-alike applies to releases.
3. Select a precise Rigveda base electronic edition and document variants against VHP.
4. Research Kauthuma edition hierarchies and alternate citations before defining Samaveda keys.
5. Establish translator/source/rights provenance for VedSearch Hindi and English.
6. Verify media ownership, granularity, and stable IDs before any audio download.

## D2 additional candidate: VedaWeb

VedaWeb publishes versioned Rigveda TEI data by book and states that each source file carries a
specific Creative Commons licence in its TEI header. It is a serious candidate for a richer or more
permissive base/parallel edition, but the exact Book 1 header, surface-text lineage, accent model,
and licence scope have not yet received artifact-level review. It is therefore documented but not
essential to the D2 sample.
