# The digital Rigvedic Anukramaṇī as a VedaGraph source

This document records what the WSC2023 Anukramaṇī dataset actually is, from inspecting
the files rather than from reading the repository's README. It is the reference for
`data/registry/sources.yaml` (`WSC2023`) and the ten `WSC2023.RV.ANUKRAMANI.M*`
artifacts.

## Dataset identity

| Field | Value |
| --- | --- |
| Repository | <https://github.com/mahesh-ak/WSC2023> |
| Pinned commit | `05b5987d6d8d6ec7228926eb68d6a21117c9b1f2` |
| Ingested paths | `Anukramani/Mandala_1.txt` … `Anukramani/Mandala_10.txt` |
| Format | UTF-8 plain text, CRLF line endings, NFC |
| Script | Latin, IAST |
| Rows | 1,028 data rows (one per Sūkta) plus one header per file |
| Declared verses | 10,552 |
| Repository licence | Apache-2.0 (`LICENSE`, repository level) |

Per-file record counts, SHA-256 checksums, Git blob SHAs and byte sizes are pinned in
`data/registry/source_artifacts.yaml`. Snapshots are content-addressed under
`data/raw/wsc2023/` and are gitignored like every other raw artifact.

## Academic citation

> Akavarapu, V. S. D. S. Mahesh, and Arnab Bhattacharya. 2023. "Creation of a Digital Rig
> Vedic Index (Anukramani) for Computational Linguistic Tasks." In *Proceedings of the
> Computational Sanskrit & Digital Humanities: Selected papers presented at the 18th World
> Sanskrit Conference*, edited by Amba Kulkarni and Oliver Hellwig, 89–96. Canberra,
> Australia (Online mode): Association for Computational Linguistics.
> <https://aclanthology.org/2023.wsc-csdh.6/>

## Underlying traditional source

The paper states that the widely found Anukramaṇī is Kātyāyana's *Sarvānukramaṇī*, citing
Macdonell's edition, and that its details are considered accurate to a good extent. The
authors also consulted the Maharishi International University Vedic Reserve materials
during annotation.

Four distinct things must not be conflated, and VedaGraph keeps them apart:

| Layer | What it is | VedaGraph treatment |
| --- | --- | --- |
| `TRADITIONAL_SOURCE` | The Sarvānukramaṇī itself, in Sanskrit prose | Cited, not ingested |
| `DIGITAL_TRANSCRIPTION` | The authors' manual annotation of that prose into rows | **Ingested** as source assertions |
| `MODERN_EDITORIAL_NORMALIZATION` | The authors' own label decisions (see below) | Recorded, never undone silently |
| `ML_CLASSIFICATION_LABEL` | Output of the repository's devatā classifiers | **Never ingested** |

The repository also ships `dcs_w2v.vec` (23 MB of word vectors) and links to RoBERTa
classifier checkpoints on Hugging Face. None of these is traditional metadata. None is
fetched, tracked, or read by any VedaGraph code path; `scripts/fetch_wsc2023_anukramani.py`
retrieves the ten Anukramaṇī files and nothing else.

## Digitization and annotation methodology

The paper is explicit that the original Anukramaṇī is natural-language Sanskrit prose and
that turning it into an index "requires manual annotation ... which would, in turn,
require a gold standard". This dataset is that manual annotation. It is therefore a
*digitization with editorial judgement*, not a mechanical transcription — which is why
VedaGraph treats it as one attributable source rather than as ground truth, and why the
VHP sample is retained as an independent cross-check.

The paper gives a worked example (RV 1.27), showing the Sanskrit prose and the row it
becomes:

```text
27.13.ājīgartiḥ śunaḥśepaḥ.(1-12)agniḥ,(13)devāḥ.(1-12)gāyatrī,(13)triṣṭup
```

## Verse numbering and record format

Each file begins with the header `hymn.verses.seer.divinity.meter`. Each data row is:

```text
<hymn>.<verse count>.<seer>.<divinity>.<meter>
```

- Fields are separated by `.`; entries within a field by `,`.
- An entry may carry a leading parenthesised verse scope: `(4-6)`, `(13)`, `(11-12,15-16)`.
- A field with no parenthesis states one claim for the whole hymn.
- Hymn numbers are Śākala/Aufrecht numbering, contiguous from 1 within each Maṇḍala.
- Mandala 1: 191, 2: 43, 3: 62, 4: 58, 5: 87, 6: 75, 7: 104, 8: 103, 9: 114, 10: 191.

Every one of the 1,028 rows aligns to a VedaGraph Sūkta, and every declared verse count
equals the corpus mantra count for that Sūkta. The dataset is thus an independent
structural witness to the 1,028 / 10,552 shape as well as a metadata source.

## Devatā representation

212 distinct labels appear in the divinity field (214 canonical Devatā entities once the
three labels of the malformed RV 8.31 row are counted; see *Known limitations*). The
paper states 216 classification labels, a number produced after its own class grouping —
VedaGraph reports what the files contain.

The authors deliberately do **not** decompose group and dual labels:

> In these cases, we make no attempt to present these labels as a mixture of the
> compositional devatās. Rather, we present them as they are. For example, a dual like
> Mitrāvaruṇau is not decomposed into Mitra and Varuṇa, but is treated as a single label
> only.

VedaGraph preserves this exactly. `mitrāvaruṇau` is one canonical entity
`VG:DEVATA:MITRAVARUNAU`; no `HAS_COMPONENT` edge to Mitra or Varuṇa is created. Nine
labels join components with hyphens (`iḻā-sarasvatī-mahī`, `agniḥ-marutaḥ`); those are
flagged `is_composite` with their surface parts recorded, and still not decomposed.

## Ṛṣi representation

368 distinct labels appear in the seer field. Labels are typically *patronymic +
personal name* in sandhi (`vaiśvāmitro madhucchandāḥ`, `kāṇvo medhātithiḥ`). The paper
notes that a verse generally has a single ṛṣi but can rarely have several; the dataset
confirms this, and VedaGraph models it as multiple `HAS_RISHI` edges from one mantra
rather than as a single property.

`madhucchandāḥ` and `vaiśvāmitro madhucchandāḥ` are **not** flattened together. Family
designation, patronymic and personal name are all inside one source string; separating
them is a later, separately evidenced phase.

## Chandas representation

38 distinct labels appear in the meter field, reduced to 34 canonical entities by four
reviewed aliases. The paper states that a hymn has a unique chandas by definition, but
the files do carry five verses with two different meter labels; those are preserved as
two assertions and reported, not resolved.

## Multiple-label behaviour

- Several entries per field are normal, each with its own verse scope.
- A verse set such as `(11-12,15-16)` is expanded into two spans, never widened into
  `11-16`.
- A verse may receive two labels of the same predicate. 31 mantras carry two Ṛṣis,
  6 carry two Devatās, 5 carry two Chandas.

## Normalization the authors already performed

Stated in the paper, and therefore inherited rather than introduced by VedaGraph:

- devatās that are "fundamentally the same" are grouped — *Rakṣoghna Agni* is labelled
  simply *Agni*;
- `Soma` and `Pavamāna Soma` are **deliberately left unmerged**, because the Pavamāna
  hymns invoke Soma's purifying nature specifically. VedaGraph keeps them as two
  entities (`VG:DEVATA:SOMAH`, `VG:DEVATA:PAVAMANAH-SOMAH`);
- Dānastuti hymns are labelled `dānastutiḥ` without the patron's name.

## Known limitations

Found by inspection of the pinned files, all reported as QA findings rather than fixed:

1. **RV 8.31 has no seer field.** The row carries four dot-separated fields instead of
   five. The parser marks it `PARTIALLY_PARSED`, names the missing field, and invents no
   ṛṣi. Its 18 mantras are the entire `HAS_RISHI` coverage gap.
2. **RV 5.52 has a descending meter span `7-5`.** The parser fails closed on it, so those
   verses receive no chandas.
3. **Nine hymns have meter scopes that do not cover every verse.** 34 mantras carry no
   `HAS_CHANDAS` assertion in total, RV 5.52 included.
4. **Six spelling variants.** Four meter spellings, one seer spelling and one devatā
   spelling differ from a much more frequent form by one diacritic or vowel. Each is
   united only by an explicit entry in `data/registry/anukramani_aliases.yaml` carrying
   its evidence; none is merged by string similarity.
5. **`aśvaḥ` and `aśvāḥ` collide under the ASCII fold but are not the same.** The
   singular is the Horse of RV 1.162, the plural the chariot horses of RV 6.75.7. They
   keep separate entities and collision-broken keys.
6. **The dataset is an annotation, not the Sarvānukramaṇī itself.** Where it disagrees
   with VHP, neither source wins; see
   [`RIGVEDA_METADATA_SOURCE_COMPARISON.md`](../reports/RIGVEDA_METADATA_SOURCE_COMPARISON.md).

## Rights

The repository carries a repository-level Apache-2.0 `LICENSE`. The Anukramaṇī data files
carry **no artifact-level licence statement of their own**, and there is no `NOTICE`
file; the repository-level grant is what applies, and it is recorded per artifact after
inspecting the exact files rather than assumed from the host.

Project policy is unchanged by this: raw snapshots stay gitignored, while the derived
entity registries, aggregate reports, schemas and code are committed. Attribution to
Akavarapu and Bhattacharya (2023) travels with every artifact record and every generated
report.

## Role in VedaGraph

`WSC2023` is the traditional-metadata source for the Rigveda deterministic knowledge
layer, supplying `HAS_RISHI`, `HAS_DEVATA` and `HAS_CHANDAS`. It is not a text source: it
supplies no Sanskrit, and the adapter refuses to produce text staging records. It is also
a secondary structural witness, since its per-hymn verse counts are checked against the
corpus and a disagreement fails the build.

VHP remains the independent cross-check for received metadata; VedaWeb's hymn addressee
remains a different concept and is never ingested as `HAS_DEVATA`.
