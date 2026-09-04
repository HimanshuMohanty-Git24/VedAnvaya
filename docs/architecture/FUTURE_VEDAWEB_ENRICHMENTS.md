# Future VedaWeb enrichments

Reviewed: 2026-09-04. **Nothing in this document is ingested.** It records what the pinned
VedaWeb repository contains beyond the Sanskrit text, so a later session can decide
deliberately rather than discover it by accident.

Everything below is at commit `d3eb8af7324338161520d2d35eae8f7e985a19a5`.

## The distinction that governs all of it

VedaGraph keeps two kinds of statement apart, permanently:

**Canonical and traditional knowledge** is what the tradition itself transmits: the text,
its hierarchy, its recension, and the received Rishi / Devata / Chandas assignments. It is
attributed to a traditional source and is not derived by anyone's analysis.

**Modern linguistic annotation** is what a scholar computed, tagged, or inferred:
morphology, lemma identity, metrical stratum, addressee headings, strata dating. It is
attributed to a named researcher and a named publication, and it can be revised.

They are not competing versions of the same claim. Mixing them would let a modern
hypothesis inherit the authority of transmitted tradition. Every enrichment below is in
the second category and must enter the graph as a separately predicated, separately
attributed statement.

## Available resources

### Linguistic annotation, inside the Book TEI

The `zurich` layer carries per-token feature structures: surface form, Grassmann lemma with
a correction pointer, part of speech, and Leipzig-glossing morphosyntax (case, gender,
number, person, mood, tense, voice, degree). Licence CC BY 4.0.

`rigveda/info/leipzig_mapping.json` and `rigveda/info/codes_abbreviations.csv` decode the
tag vocabulary. `rigveda/info/matched_lemmata.json` (8.5 MB) and
`rigveda/info/revised_grassmann_mapping.csv` plus `grassmann_enum.json` carry the lemma
inventory and its mapping to Grassmann's dictionary.

Possible later uses: lemma frequency, morphological search, deterministic corpus
statistics, and a lexical layer for linguistic retrieval.

### Metrical stratum

Every stanza carries an `lg type="strata"` block with per-pada labels. Compiled by Dieter
Gunkel and Kevin M. Ryan from E. V. Arnold, *Vedic Metre in its Historical Development*,
1905. Licence CC BY 4.0. `rigveda/info/strata.json` (2.6 MB) holds the same data outside
the TEI.

Possible later use: metre analysis, relative-chronology views. This is a scholarly dating
hypothesis and must be labelled as one.

### Stanza properties

`rigveda/info/stanza_properties.json` flags stanzas discussed by Grassmann, Oldenberg
(Prolegomena and Noten), Arnold, Wüst and Witzel. Compiled by Gunkel and Salvatore
Scarlata. Licence CC BY 4.0.

Possible later use: pointing a reader at the passages the philological literature argues
about. It is a bibliography index, not a claim about the text.

### Addressees — read the section below before using

`rigveda/info/addressees.json` gives, per hymn, a German heading and its English rendering,
plus a hymn-group label. Compiled by Daniel Kölligan. Licence CC BY 4.0.

### Translations

Nine translation sets as CSV under `rigveda/translations/`: Geldner, Grassmann and Otto
(German); Griffith, Macdonell, Müller and Oldenberg (English); Renou (French);
Elizarenkova (Russian). Per-translation licences and bibliography are in the corpus TEI
header; all nine are CC BY-NC-SA 4.0. `rigveda/info/translation_version_stanza_coverage.md`
gives exact coverage and names every missing stanza.

Note that VedaWeb's Griffith is a different electronic transcription from the Wikisource
Griffith that VedaGraph already ingests, and it cites the 1890 printing where Wikisource
cites the 1896 second edition. They are two artifacts of one translation and must not be
merged.

### Concordances to external resources

`rigveda/external-resources/` holds CSV concordances to Delbrück (1888), Ludwig (2 volumes)
and Oldenberg (2 volumes). `rigveda/info/rv_locations.json` / `.tsv` carries stanza
location data.

Possible later use: citation resolution and cross-referencing to printed scholarship.

### Source spreadsheets

`rigveda/versions/zurich.xlsx` (12.6 MB) and `vedaweb_zurich.xlsx` (10.9 MB) are the
upstream annotation tables the TEI was generated from, plus per-version CSVs for
`aufrecht`, `eichler`, `lubotsky`, `padapatha` and `vnh`. The TEI is preferred: it is
already aligned to stanza IDs and already carries the licence header.

## Addressee is not Devata

VedaWeb's `addressees.json` and the `div type="addressee"` blocks in the TEI are **not** the
traditional devatā assignment, and equating them would corrupt both.

What the data actually is: the corpus TEI header records that the addressee compilation was
made by Daniel Kölligan with the source given as Karl Friedrich Geldner, *Der Rig-Veda*,
Harvard University Press, 1951. The entries are Geldner's German hymn headings with an
English rendering — for RV 1.1, `["An Agni", "Agni"]`, alongside a hymn-group label
`["1. Gruppe: Lieder des Madhucchandas", "1. group: hymns of Madhucchandas"]`.

So it is a modern translator's hymn heading, at hymn granularity, in German, from a 1951
publication.

The traditional devatā, as VHP records it, is a different thing: it is transmitted, it is
in Sanskrit, and it is frequently assigned per mantra or per half-verse, with alternatives
(`X, or Y`) and exceptions. RV 1.164 alone assigns more than a dozen deities across its 52
mantras, including two half-verse splits.

When these do reach the graph they get separate predicates, never one merged field:

- `TRADITIONALLY_ASSIGNED_DEVATA` — transmitted assignment, attributed to a traditional
  source, scoped to whatever span the source actually names.
- `MODERN_SCHOLARLY_ADDRESSEE` — a named scholar's heading, attributed to that scholar and
  that publication, at the granularity the scholar used.
- `TEXTUAL_ADDRESSEE` — reserved for an addressee derived from the wording of the mantra
  itself, for example a vocative. **No source in scope supplies this today**, so the
  predicate stays unused rather than being filled from one of the other two.

Where they agree, that agreement is a finding worth recording. Where they disagree, both
survive with their attribution, exactly as ADR-003 requires of any conflicting claim.

## What would have to be true before ingesting any of this

1. The Sanskrit primary-text decision is settled and stable, so annotation has something
   fixed to attach to.
2. A predicate vocabulary exists that keeps traditional and modern statements apart.
3. Per-resource rights are registered the way text versions now are, including the CC BY
   layers, which are more permissive than the corpus as a whole and must not silently
   relicense it.
4. A Vedic entity registry exists, so lemma and deity strings can be resolved instead of
   stored as free text.
5. Token-level annotation has a place in the schema. It is an order of magnitude more
   records than the text, and it does not belong in `text_versions.jsonl`.
