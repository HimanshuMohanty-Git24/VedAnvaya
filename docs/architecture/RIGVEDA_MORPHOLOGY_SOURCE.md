# Rigveda Morphological Annotation Sources

Survey of the structured Rigveda morphological datasets VedaGraph could build a
deterministic lexical layer on. The decision made from this survey is recorded
separately in [RIGVEDA_MORPHOLOGY_DECISION.md](RIGVEDA_MORPHOLOGY_DECISION.md).

Two candidates were examined. They are not alternatives of equal shape: one is an
annotation layer inside an edition this repository already pins, the other is a
standalone research release that would be a new source.

---

## Candidate A — VedaWeb / University of Zurich morphosyntactic annotation

### Dataset and artifact

| field | value |
|---|---|
| repository | <https://github.com/VedaWebProject/vedaweb-data> |
| commit | `d3eb8af7324338161520d2d35eae8f7e985a19a5` |
| artifacts | `rigveda/TEI/rv_book_01.tei` … `rv_book_10.tei` (10 files) |
| VedaGraph artifact ids | `VEDAWEB.RV.BOOK01.TEI.D3EB8AF` … `VEDAWEB.RV.BOOK10.TEI.D3EB8AF` |
| text version id | `VEDAWEB.ZURICH` |
| pinned index | `data/derived/vedaweb_morphology_artifacts.json` (per-book SHA256) |
| licence | CC BY 4.0 (`https://creativecommons.org/licenses/by/4.0/`) |
| publisher | Cologne Center for eHumanities, University of Cologne |

The annotation is **not a separate download**. It is the `<lg source="zurich">`
layer inside book TEI files this repository already pinned, hashed and registered
during the corpus build. Selecting it adds no new source, no new licence and no
new fetch.

### Provenance

Read verbatim from the `sourceDesc` of `vedaweb_corpus.tei`:

- Prof. Dr. Paul Widmer and Dr. Salvatore Scarlata (Institut für Vergleichende
  Sprachwissenschaft, Universität Zürich) supplied VedaWeb with a FileMaker
  database, later transformed in Cologne into an Excel file.
- That database held Lubotsky's text of the Rigveda, **"morphosytactically
  annotated over the course of more than 10 years at the University of Zurich"**.
- It also carried, per token, a reference to an entry in **Grassmann's dictionary
  of the Rigveda** where one existed.
- Jakob Halfmann and Natalie Korobzow (Cologne) made recorded 2020 modifications:
  disambiguating case, gender and number for nouns and pronouns; number, person,
  mood, tense and voice for verbs; case, gender, number, tense and voice for
  participles — all *"according to the Grassmann dictionary"*.
- Further contributors named in the `respStmt`: Antje Casaretto (Freiburg),
  Anna Fischer (Wuppertal), Pascal Coenen (Würzburg). Dated 2020, 2023, 2024.

**Manual vs automatic.** The annotation is manual scholarly work throughout: a
decade of hand annotation plus a documented hand disambiguation pass against a
printed dictionary. No tagger, classifier or statistical model is involved.

### Verse and token coverage (measured, not claimed)

| measure | value |
|---|---|
| stanzas in the ten book TEIs | 10,552 |
| stanzas carrying `zurich_info` token annotation | **10,552 (100%)** |
| annotated tokens | **164,758** |
| tokens with no lemma | **0** |
| distinct lemmas | 9,785 |
| distinct Grassmann-linked lemma identifiers | 9,736 |
| tokens with more than one lemma identifier | 6,992 (4.2%) |
| stanza ids that failed to parse | 0 |
| token ids that failed to parse | 0 |

### Lemma representation

Each token carries `gra_lemma`: a string plus a `correction` attribute holding one
or more **stable lemma identifiers** keyed to Grassmann, e.g.

```
surface   agním
gra_lemma agní-        correction="#lemma_agni_79"
gra_gramm nominal stem
```

Nominal stems end in `-`, verbal roots are written `√jan¹-`. Where the annotators
could not choose between two lexical entries the token carries both, e.g.
`dyú- ~ div-` with `correction="#lemma_div_4231 #lemma_dyu_4513"`. That ambiguity
is preserved, not collapsed.

The stable identifier matters more than the string: it lets entity matching happen
without any string comparison at all.

### Morphological fields

`gra_gramm` (part of speech), one of: `nominal stem` (86,858), `root` (32,029),
`invariable` (25,875), `pronoun` (19,996).

`morphosyntax`, as a `leipzig_glossing_rules` feature structure: `case`, `gender`,
`number`, `person`, `mood`, `tense`, `voice`.

### Sanskrit form representation

ISO 15919 in Latin script, accented (udātta marked U+0301). Note this differs from
the canonical GRETIL/Aufrecht text, which is IAST with U+0331/U+030D. The two are
comparable only through the repository's existing `fold_transcription` profile, and
the annotation surface is stored separately from the canonical text rather than
replacing it.

### Relation to VedaWeb

It *is* a VedaWeb layer. VedaWeb ships it alongside the aufrecht, lubotsky, vnh,
eichler and padapatha Sanskrit layers in the same stanza, each with its own licence
declared in the corpus header. VedaGraph already reads the aufrecht layer from these
same files as parallel Sanskrit.

### Compatibility with canonical passage ids

Exact and structural. Every stanza's `xml:id` states its position directly:

```
b02_h001_01            -> Mandala 2, Sukta 1, mantra 1
b02_h001_01_zur_d_05   -> ... pada d, token 5
```

This maps onto `VG:RV:SAK:M02:S001:V001` by parsing integers, with no text
comparison, no fuzzy alignment and no edition mapping table. Measured result:
10,552 / 10,552 mantras aligned, 0 unaligned records, 0 duplicate mappings, 0
passage mismatches.

The pāda letter in the token id is a bonus: pāda-level parallels become possible
later without re-identifying anything.

---

## Candidate B — sanskrit-texts/rigveda (Hellwig / Hettrich merged annotation)

### Dataset and artifact

| field | value |
|---|---|
| repository | <https://github.com/sanskrit-texts/rigveda> |
| directories | `morpho-lexical/`, `verb-argument/`, `merged/` |
| licence | CC BY 4.0 |
| commit | not pinned by VedaGraph (not selected) |

### Provenance

Per the repository README, three separately credited steps:

1. H. Hettrich (Würzburg) created the **verb-argument annotation**.
2. O. Hellwig (Düsseldorf) created the **morpho-lexical annotation**, performed
   independently of (1).
3. The two were merged in a project at the Department of Computational
   Linguistics, Saarbrücken.

The README does not derive the annotation from VedaWeb, Zurich or Lubotsky, and
presents it as original work by the credited scholars.

### What it offers that Candidate A does not

An independent **verb-argument / syntactic-role** layer. Nothing in Candidate A
covers argument structure. For a future layer asking *who does what to whom*, this
is the obvious source, and its independence from Zurich also makes it a genuine
cross-check on lemma decisions rather than a second opinion from the same tradition.

### Why it was not assessed further for this phase

Assessment stopped once Candidate A was measured, because the remaining questions
(exact artifact paths, per-file hashes, token counts, citation-alignment behaviour)
only matter for a source that is going to be built from. Selecting Candidate B
would require registering a new source, a new rights record, a new fetcher and a
new alignment audit — all of which are warranted for the verb-argument layer it
uniquely provides, and none of which are warranted to obtain lemmas that
Candidate A already supplies at 100% coverage with exact structural alignment.

Its manual-vs-automatic split is also not stated field by field in the README.
Hellwig's Vedic morpho-lexical work is widely built with computational assistance;
whether and where that applies here would need to be established before the layer
could be called curated, and that investigation belongs with the phase that
actually adopts it.

---

## Side-by-side

| criterion | A: VedaWeb / Zurich | B: sanskrit-texts/rigveda |
|---|---|---|
| full Rigveda coverage | verified 10,552/10,552 | claimed complete, unverified here |
| lemma quality | manual, 10+ years, Grassmann-checked | credited scholars, method not stated per field |
| stable lemma identifiers | yes (Grassmann-linked) | not established |
| verse alignment | structural, from stanza `xml:id` | not established |
| licence | CC BY 4.0 | CC BY 4.0 |
| already pinned in this repo | **yes**, commit `d3eb8af` | no |
| new source registration needed | no | yes |
| token-level provenance | per token, to a named annotation layer | not established |
| pāda-level addressing | yes, in the token id | not established |
| verb-argument / syntax | **no** | **yes** |

---

## Sources

- [VedaWebProject/vedaweb-data](https://github.com/VedaWebProject/vedaweb-data)
  — TEI corpus and per-layer licence declarations, read from the pinned snapshot
  `vedaweb_corpus.tei` at commit `d3eb8af`.
- [sanskrit-texts/rigveda](https://github.com/sanskrit-texts/rigveda) — README
  provenance and licence statement.
